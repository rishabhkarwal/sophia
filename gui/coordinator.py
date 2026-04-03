import multiprocessing
import os
import random
import time

from concurrent.futures import ProcessPoolExecutor

from gui.config import Config
from gui.types import GameAssignment, GameUpdate, GameResult
from gui.worker import play_game, _init_worker
from gui.display import Terminal


class ParallelTournament:
    def __init__(self, config: Config, headless=False):
        self.config = config
        self.headless = headless
        self.manager = multiprocessing.Manager()
        self.update_queue = self.manager.Queue()
        self.results: list[GameResult] = []
        self.game_states: dict[int, GameUpdate] = {}
        self.display = None if headless else Terminal(config)
        self.start_time = 0.0

    def run(self):
        cfg = self.config
        assignments = self._build_assignments()
        self.start_time = time.time()

        print(f'\n  Engine Tournament')
        print(f'  {cfg.engine_1_name} vs {cfg.engine_2_name}')
        print(f'  {cfg.total_games} games | {cfg.time_control}+{cfg.increment} | {cfg.workers} workers\n')

        ctx = multiprocessing.get_context('spawn')

        try:
            with ProcessPoolExecutor(
                max_workers=cfg.workers,
                mp_context=ctx,
                initializer=_init_worker,
                initargs=(self.update_queue,)
            ) as pool:
                futures = {}
                for a in assignments:
                    f = pool.submit(play_game, a)
                    futures[f] = a

                while futures:
                    self._drain_queue()

                    done = [f for f in futures if f.done()]
                    for f in done:
                        try:
                            result = f.result()
                        except Exception as e:
                            a = futures[f]
                            result = GameResult(
                                game_id=a.game_id,
                                white_name=a.engine_1_name if a.white_is_engine_1 else a.engine_2_name,
                                black_name=a.engine_2_name if a.white_is_engine_1 else a.engine_1_name,
                                result='*', termination='Worker Crash',
                                pgn_string='', moves=0,
                                time_control=f'{a.time_control}+{a.increment}',
                                error=str(e)
                            )
                        self.results.append(result)
                        self._write_pgn(result)

                        if self.headless:
                            tag = f'{result.termination}'
                            if result.error: tag += f' ({result.error})'
                            print(f'  Game {result.game_id}: {result.white_name} vs {result.black_name} -> {result.result} ({tag}, {result.moves} moves)')

                        del futures[f]

                    if self.display:
                        elapsed = time.time() - self.start_time
                        self.display.refresh(self.game_states, self.results,
                                             self.config.total_games, elapsed)

                    time.sleep(0.1)

        except KeyboardInterrupt:
            print('\n\n  Tournament interrupted.\n')

        self._print_summary()

    def _build_assignments(self):
        cfg = self.config
        openings = self._load_openings()
        assignments = []

        for i in range(cfg.total_games):
            pair_idx = i // 2
            fen = openings[pair_idx % len(openings)] if openings else None
            white_is_engine_1 = (i % 2 == 0)

            assignments.append(GameAssignment(
                game_id=i + 1,
                engine_1_path=cfg.engine_1_path,
                engine_2_path=cfg.engine_2_path,
                engine_1_name=cfg.engine_1_name,
                engine_2_name=cfg.engine_2_name,
                time_control=cfg.time_control,
                increment=cfg.increment,
                white_is_engine_1=white_is_engine_1,
                starting_fen=fen
            ))

        return assignments

    def _load_openings(self):
        path = self.config.openings_file

        default = os.path.join(os.path.dirname(__file__), 'assets', 'openings.txt')
        if path is None and os.path.exists(default):
            path = default

        if path is None or not os.path.exists(path):
            return None

        with open(path, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]

        random.shuffle(lines)
        return lines if lines else None

    def _drain_queue(self):
        while True:
            try:
                update = self.update_queue.get_nowait()
                self.game_states[update.game_id] = update
            except Exception:
                break

    def _write_pgn(self, result: GameResult):
        if not result.pgn_string or result.error:
            return
        try:
            with open(self.config.pgn_path, 'a', encoding='utf-8') as f:
                f.write(result.pgn_string + '\n')
        except Exception:
            pass

    def _print_summary(self):
        if not self.results:
            print('  No games completed.\n')
            return

        cfg = self.config
        elapsed = time.time() - self.start_time

        stats = {}
        for name in [cfg.engine_1_name, cfg.engine_2_name]:
            stats[name] = {'score': 0.0, 'wins': 0, 'draws': 0, 'losses': 0}

        for r in self.results:
            if r.result == '1-0':
                stats[r.white_name]['score'] += 1.0
                stats[r.white_name]['wins'] += 1
                stats[r.black_name]['losses'] += 1
            elif r.result == '0-1':
                stats[r.black_name]['score'] += 1.0
                stats[r.black_name]['wins'] += 1
                stats[r.white_name]['losses'] += 1
            elif '1/2' in r.result:
                stats[r.white_name]['score'] += 0.5
                stats[r.white_name]['draws'] += 1
                stats[r.black_name]['score'] += 0.5
                stats[r.black_name]['draws'] += 1

        errors = sum(1 for r in self.results if r.error)

        print(f'\n  {"=" * 50}')
        print(f'  Results ({len(self.results)}/{cfg.total_games} games, {elapsed:.0f}s)')
        print(f'  {"=" * 50}')

        ranking = sorted(stats.items(), key=lambda x: x[1]['score'], reverse=True)
        for name, s in ranking:
            print(f'  {name:20s}  {s["score"]:5.1f}/{len(self.results):>3}  '
                  f'(W:{s["wins"]} D:{s["draws"]} L:{s["losses"]})')

        if errors:
            print(f'\n  {errors} game(s) had errors')

        print(f'  {"=" * 50}\n')

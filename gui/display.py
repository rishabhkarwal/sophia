import sys

from gui.config import Config
from gui.types import GameUpdate, GameResult


class Colours:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    WHITE = '\033[97m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    GREY = '\033[90m'
    ORANGE = '\033[38;5;208m'


class Terminal:
    def __init__(self, config: Config):
        self.config = config
        self.prev_lines = 0

    def refresh(self, game_states: dict[int, GameUpdate], results: list[GameResult],
                total_games: int, elapsed: float):
        lines = []

        completed = len(results)
        active = sum(1 for g in game_states.values() if g.status == 'playing')

        # header
        elapsed_str = self._format_elapsed(elapsed)
        lines.append('')
        lines.append(f'  {Colours.BOLD}{Colours.CYAN}Engine Tournament{Colours.RESET}'
                     f'  {Colours.DIM}{elapsed_str}{Colours.RESET}')
        lines.append(f'  {Colours.DIM}{self.config.engine_1_name} vs {self.config.engine_2_name}'
                     f'  |  {self.config.time_control}+{self.config.increment}'
                     f'  |  {self.config.workers} workers{Colours.RESET}')
        lines.append('')

        # progress bar
        pct = completed / total_games if total_games > 0 else 0
        bar_w = 40
        filled = int(bar_w * pct)
        bar = f'{"█" * filled}{"░" * (bar_w - filled)}'
        lines.append(f'  {Colours.ORANGE}{bar}{Colours.RESET}'
                     f'  {completed}/{total_games} complete'
                     f'  {Colours.DIM}|{Colours.RESET}  {active} running')
        lines.append('')

        # active games
        active_updates = sorted(
            [g for g in game_states.values() if g.status == 'playing'],
            key=lambda g: g.game_id
        )
        for g in active_updates:
            w_clock = self._format_clock(g.w_time)
            b_clock = self._format_clock(g.b_time)
            lines.append(
                f'  {Colours.GREEN}▶{Colours.RESET}'
                f'  {Colours.DIM}#{g.game_id:02d}{Colours.RESET}'
                f'  {Colours.WHITE}Move {g.move_number:>3}{Colours.RESET}'
                f'  {g.white_name} {Colours.DIM}vs{Colours.RESET} {g.black_name}'
                f'  {Colours.CYAN}{w_clock}{Colours.RESET}'
                f' / {Colours.CYAN}{b_clock}{Colours.RESET}'
            )

        # recent completed (last 8)
        completed_results = sorted(results, key=lambda r: r.game_id, reverse=True)[:8]
        if completed_results:
            lines.append('')
            for r in completed_results:
                if r.error:
                    result_col = Colours.RED
                    result_str = f'*  {r.termination}'
                elif r.result == '1/2-1/2':
                    result_col = Colours.YELLOW
                    result_str = f'½-½  {r.termination}'
                else:
                    result_col = Colours.WHITE
                    result_str = f'{r.result}  {r.termination}'

                lines.append(
                    f'  {Colours.DIM}✓  #{r.game_id:02d}{Colours.RESET}'
                    f'  {result_col}{result_str}{Colours.RESET}'
                    f'  {Colours.DIM}{r.white_name} vs {r.black_name}'
                    f'  ({r.moves} moves){Colours.RESET}'
                )

        # score tally
        stats = {}
        for name in [self.config.engine_1_name, self.config.engine_2_name]:
            stats[name] = {'score': 0.0, 'wins': 0, 'draws': 0, 'losses': 0}

        for r in results:
            if r.result == '1-0':
                stats[r.white_name]['score'] += 1.0
                stats[r.white_name]['wins'] += 1
                stats[r.black_name]['losses'] += 1
            elif r.result == '0-1':
                stats[r.black_name]['score'] += 1.0
                stats[r.black_name]['wins'] += 1
                stats[r.white_name]['losses'] += 1
            elif '1/2' in r.result:
                for name in [r.white_name, r.black_name]:
                    stats[name]['score'] += 0.5
                    stats[name]['draws'] += 1

        if results:
            lines.append('')
            lines.append(f'  {Colours.BOLD}Score{Colours.RESET}')
            for name, s in stats.items():
                lines.append(
                    f'  {name:20s}'
                    f'  {s["score"]:5.1f}/{completed}'
                    f'  {Colours.GREEN}W:{s["wins"]}{Colours.RESET}'
                    f'  {Colours.YELLOW}D:{s["draws"]}{Colours.RESET}'
                    f'  {Colours.RED}L:{s["losses"]}{Colours.RESET}'
                )

        lines.append('')

        # clear previous output and write new
        output = '\033[H\033[J' + '\n'.join(lines)
        sys.stdout.write(output)
        sys.stdout.flush()
        self.prev_lines = len(lines)

    def _format_clock(self, seconds):
        seconds = max(0, seconds)
        if seconds >= 60:
            m = int(seconds // 60)
            s = int(seconds % 60)
            return f'{m}:{s:02d}'
        else:
            return f'{seconds:.1f}s'

    def _format_elapsed(self, seconds):
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f'{m}m {s:02d}s'

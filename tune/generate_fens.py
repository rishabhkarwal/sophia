"""
generate a FEN dataset for texel tuning via self-play

outputs "fen | result" per line, result = 1.0/0.5/0.0 (white/draw/black)
games start from random openings at depth 4, head/tail positions excluded

usage:
    venv/bin/python tune/generate_fens.py [output_file] [num_games] [num_workers]
"""

import sys
import os
import random
import multiprocessing

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'sophia'))

import chess

from engine.board.fen_parser import load_from_fen
from engine.board.move_exec import make_move
from engine.moves.generator import get_legal_moves
from engine.moves.legality import is_in_check
from engine.core.move import move_to_uci
from engine.search.search import SearchEngine

OUTPUT_FILE  = sys.argv[1] if len(sys.argv) > 1 else 'tune/fens.txt'
NUM_GAMES    = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
NUM_WORKERS  = int(sys.argv[3]) if len(sys.argv) > 3 else max(1, multiprocessing.cpu_count() - 1)
OPENINGS_FILE = os.path.join(ROOT, 'gui', 'assets', 'openings.txt')
SEARCH_DEPTH = 4
MIN_MOVE     = 4
TAIL_SKIP    = 8


def play_game(engine, opening_fen):
    full_fen = opening_fen + ' 0 1'
    state = load_from_fen(full_fen)
    board = chess.Board(full_fen)
    positions = []
    move_count = 0

    while True:
        moves = get_legal_moves(state)
        if not moves:
            if is_in_check(state, state.is_white):
                result = 0.0 if state.is_white else 1.0
            else:
                result = 0.5
            break

        if state.halfmove_clock >= 100 or move_count > 300:
            result = 0.5
            break

        move = engine.get_best_move(state, 999_999_999, SEARCH_DEPTH, None, False)
        if isinstance(move, str):  # syzygy hit returns a uci string, not an int move
            move = next((m for m in moves if move_to_uci(m) == move), None)
        if move is None:
            move = random.choice(moves)

        uci = move_to_uci(move)
        pc_move = chess.Move.from_uci(uci)
        if pc_move not in board.legal_moves:
            return []

        positions.append((board.fen(), move_count))
        board.push(pc_move)
        make_move(state, move)
        move_count += 1

    total = len(positions)
    return [
        (fen, result)
        for fen, idx in positions
        if idx >= MIN_MOVE and idx < total - TAIL_SKIP
    ]


def worker(args):
    worker_id, num_games, tmp_path = args
    random.seed(os.getpid() * 7919 + worker_id)
    # silence the engine's UCI output — search.py prints `info depth ...` via
    # send_command and `aspiration ...` via send_info_string, each flushing to
    # stdout per iteration. Both flood the log and stall on the write.
    import engine.search.search as _search  # silence UCI output flooding the log
    _search.send_command = lambda *a, **k: None
    _search.send_info_string = lambda *a, **k: None
    engine = SearchEngine()
    with open(OPENINGS_FILE) as f:
        openings = [line.strip() for line in f if line.strip()]

    written = 0
    errors = 0
    with open(tmp_path, 'w') as f:
        for game_num in range(num_games):
            engine.tt.clear()
            engine.ordering.clear()
            try:
                game_positions = play_game(engine, random.choice(openings))
            except Exception:
                # never let one bad game kill the worker (and thus the whole pool)
                errors += 1
                continue
            for fen, result in game_positions:
                f.write(f'{fen} | {result}\n')
                written += 1
            if (game_num + 1) % 50 == 0:
                print(f'  worker {worker_id}: {game_num + 1}/{num_games} games, '
                      f'{written} positions, {errors} skipped', flush=True)
    return written


def main():
    if os.path.exists(OUTPUT_FILE):
        print(f'output already exists, refusing to overwrite labelled data: {OUTPUT_FILE}')
        sys.exit(1)

    os.makedirs(os.path.dirname(OUTPUT_FILE) or '.', exist_ok=True)

    games_per_worker = NUM_GAMES // NUM_WORKERS
    remainder = NUM_GAMES % NUM_WORKERS

    tasks = []
    tmp_files = []
    for i in range(NUM_WORKERS):
        n = games_per_worker + (1 if i < remainder else 0)
        tmp = f'{OUTPUT_FILE}.cython.{os.getpid()}.part{i}'
        if os.path.exists(tmp):
            print(f'temporary output already exists, refusing to overwrite: {tmp}')
            sys.exit(1)
        tmp_files.append(tmp)
        tasks.append((i, n, tmp))

    print(f'generating {NUM_GAMES} games with {NUM_WORKERS} workers at depth {SEARCH_DEPTH}...')

    if NUM_WORKERS == 1:
        written = worker(tasks[0])
    else:
        with multiprocessing.Pool(NUM_WORKERS) as pool:
            results = pool.map(worker, tasks)
        written = sum(results)

    with open(OUTPUT_FILE, 'w') as out:
        for tmp in tmp_files:
            if os.path.exists(tmp):
                with open(tmp) as f:
                    out.write(f.read())

    print(f'done: {written} positions written to {OUTPUT_FILE}')
    print(f'kept worker part files: {", ".join(tmp_files)}')


if __name__ == '__main__':
    main()

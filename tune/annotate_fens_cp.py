"""
annotate a FEN dataset with stockfish HCE centipawn scores

uses SF classical eval (NNUE disabled) — labels are in the same space as sophia's
linear eval, so regression converges faster than WDL
positions with ≤5 pieces or |score| > 2000cp are dropped

usage:
    python tune/annotate_fens_cp.py [input_fens] [output_fens] [depth] [workers]
"""

import sys
import os
import multiprocessing
import time

import chess
import chess.engine

STOCKFISH_PATH = '/usr/games/stockfish'
DEFAULT_DEPTH  = 14
HASH_MB        = 64    # per SF instance — small since HCE needs no NNUE hash
CP_CLIP        = 2000  # drop positions with |score| > this

INPUT_FILE  = sys.argv[1] if len(sys.argv) > 1 else 'tune/fens_sf_all.txt'
OUTPUT_FILE = sys.argv[2] if len(sys.argv) > 2 else 'tune/fens_cp.txt'
DEPTH       = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_DEPTH
NUM_WORKERS = int(sys.argv[4]) if len(sys.argv) > 4 else multiprocessing.cpu_count()


def annotate_chunk(args):
    worker_id, fens, tmp_path = args
    t0 = time.monotonic()

    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    engine.configure({
        'Hash': HASH_MB,
        'Threads': 1,
        'Use NNUE': False,
    })

    written = 0
    skipped = 0
    with open(tmp_path, 'w') as f:
        for i, fen in enumerate(fens):
            try:
                board = chess.Board(fen)
            except ValueError:
                skipped += 1
                continue

            if len(board.piece_map()) <= 5:
                skipped += 1
                continue

            try:
                info = engine.analyse(board, chess.engine.Limit(depth=DEPTH))
            except chess.engine.EngineError:
                skipped += 1
                continue

            score = info.get('score')
            if score is None:
                skipped += 1
                continue

            pov = score.white()
            if pov.is_mate():
                skipped += 1
                continue

            cp = pov.score()
            if cp is None or abs(cp) > CP_CLIP:
                skipped += 1
                continue

            f.write(f'{fen} | {cp}\n')
            written += 1

            if (i + 1) % 1000 == 0:
                elapsed = time.monotonic() - t0
                rate = (i + 1) / elapsed
                eta = (len(fens) - i - 1) / rate
                print(f'  worker {worker_id}: {i + 1}/{len(fens)}, '
                      f'{rate:.0f}/s, ETA {eta/60:.1f}m', flush=True)

    engine.quit()

    elapsed = time.monotonic() - t0
    print(f'  worker {worker_id} done: {written} written, {skipped} skipped '
          f'in {elapsed:.0f}s ({written/elapsed:.0f}/s)', flush=True)
    return written


def main():
    if not os.path.exists(INPUT_FILE):
        print(f'input not found: {INPUT_FILE}')
        sys.exit(1)
    if os.path.exists(OUTPUT_FILE):
        print(f'output already exists, refusing to overwrite labelled data: {OUTPUT_FILE}')
        sys.exit(1)

    print(f'reading {INPUT_FILE}...', flush=True)
    fens = []
    with open(INPUT_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            fen = line.split(' | ')[0].strip()
            fens.append(fen)

    seen = set()
    unique_fens = []
    for fen in fens:
        if fen not in seen:
            seen.add(fen)
            unique_fens.append(fen)

    dropped = len(fens) - len(unique_fens)
    print(f'{len(unique_fens):,} unique positions ({dropped:,} duplicates removed)')
    print(f'annotating with Stockfish HCE (no NNUE) at depth {DEPTH}, {NUM_WORKERS} workers\n', flush=True)

    chunk_size = (len(unique_fens) + NUM_WORKERS - 1) // NUM_WORKERS
    tasks = []
    tmp_files = []
    for i in range(NUM_WORKERS):
        chunk = unique_fens[i * chunk_size:(i + 1) * chunk_size]
        if not chunk:
            break
        tmp = f'{OUTPUT_FILE}.cython.{os.getpid()}.part{i}'
        if os.path.exists(tmp):
            print(f'temporary output already exists, refusing to overwrite: {tmp}')
            sys.exit(1)
        tmp_files.append(tmp)
        tasks.append((i, chunk, tmp))

    t_start = time.monotonic()
    if len(tasks) == 1:
        results = [annotate_chunk(tasks[0])]
    else:
        with multiprocessing.Pool(len(tasks)) as pool:
            results = pool.map(annotate_chunk, tasks)
    written = sum(results)

    os.makedirs(os.path.dirname(OUTPUT_FILE) or '.', exist_ok=True)
    with open(OUTPUT_FILE, 'w') as out:
        for tmp in tmp_files:
            if os.path.exists(tmp):
                with open(tmp) as f:
                    out.write(f.read())

    elapsed = time.monotonic() - t_start
    rate = written / elapsed if elapsed > 0 else 0
    print(f'\nDone: {written:,} positions -> {OUTPUT_FILE}  ({elapsed:.0f}s, {rate:.0f}/s)')
    print(f'kept worker part files: {", ".join(tmp_files)}')
    print(f'run CP Texel:  venv/bin/python tune/texel_tune_cp.py {OUTPUT_FILE} 200000 40 4')


if __name__ == '__main__':
    main()

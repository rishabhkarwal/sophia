"""
parallel CP-regression texel tuner

minimises MSE between sophia's eval (centipawns) and Stockfish HCE centipawn
labels — direct regression in CP space rather than sigmoid/WDL space

loss per position:
    (sophia_eval_white_cp - sf_hce_cp)^2

labels are normalised by SF_SCALE so both sides use the same pawn-unit:
sophia PAWN_VALUE vs SF HCE internal pawn. fitted automatically via ternary
search on K_SCALE (analogous to Texel K)

same parallel architecture as texel_tune_mp.py — persistent worker processes
own fixed dataset slices, main process broadcasts params, workers return partial
sums. coordinate descent stays sequential

    venv/bin/python tune/texel_tune_cp.py [fens_cp_file] [max_positions] [max_passes] [workers]

fens_cp_file must be output of annotate_fens_cp.py (format: 'fen | cp_int')
"""

import json
import math
import os
import sys
import multiprocessing as mp

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'sophia'))

from texel_tune import (
    SCALAR_PARAMS, FLOAT_PARAMS, PSQT_NAMES, PSQT_DELTA,
    apply_all, apply_scalars, apply_psqt,
)
import texel_tune as _serial
import engine.core.parameters as _params
from engine.board.fen_parser import load_from_fen
from engine.moves.legality import is_in_check

CP_PARAMS_OUT = os.path.join('tune', 'best_params_cython_cp.json')
CP_PARAMETERS_OUT = os.path.join('tune', 'best_parameters_cython_cp.py')
_OUTPUT_CP_PARAMS_PATH = CP_PARAMS_OUT
_OUTPUT_CP_PARAMETERS_PATH = CP_PARAMETERS_OUT


def load_dataset_cp(fens_file, cap):
    raw = []
    with open(fens_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(' | ')
            if len(parts) != 2:
                continue
            fen = parts[0].strip()
            try:
                cp = float(parts[1].strip())
            except ValueError:
                continue
            raw.append((fen, cp))

    positions = []
    dropped_check = 0
    for fen, cp in raw:
        state = load_from_fen(fen)
        if is_in_check(state, state.is_white):
            dropped_check += 1
            continue
        positions.append((fen, cp))

    if cap and len(positions) > cap:
        stride = len(positions) / cap
        positions = [positions[int(i * stride)] for i in range(cap)]

    print(f'loaded {len(raw)} positions, dropped {dropped_check} in-check, '
          f'using {len(positions)}', flush=True)
    return positions



def _worker_loop(conn, fens_slice):
    global _W_EVAL_CACHE
    import engine.search.evaluation as _e
    from engine.board.fen_parser import load_from_fen
    from engine.search.evaluation import calculate_initial_score
    from engine.search.evaluation import evaluate

    states = []
    for fen, label in fens_slice:
        st = load_from_fen(fen)
        states.append((st, label))

    def raw_white_eval(st):
        st.mg_score, st.eg_score, st.phase = calculate_initial_score(st)
        score = evaluate(st)
        return score if st.is_white else -score

    _W_EVAL_CACHE = None

    conn.send('ready')
    while True:
        msg = conn.recv()
        if msg is None:
            break
        cmd = msg[0]

        if cmd == 'MSE':
            _, scalars, floats, psqt, scale = msg
            apply_scalars(scalars, floats)
            apply_psqt(psqt)
            _e.init_eval_tables()
            total = 0.0
            for st, label in states:
                s = raw_white_eval(st) * scale
                d = s - label
                total += d * d
            conn.send((total, len(states)))

        elif cmd == 'CACHE_EVALS':
            _, scalars, floats, psqt = msg
            apply_scalars(scalars, floats)
            apply_psqt(psqt)
            _e.init_eval_tables()
            _W_EVAL_CACHE = [(raw_white_eval(st), label) for st, label in states]
            conn.send(len(_W_EVAL_CACHE))

        elif cmd == 'MSE_SCALE':
            _, scale = msg
            total = 0.0
            for s_raw, label in _W_EVAL_CACHE:
                d = s_raw * scale - label
                total += d * d
            conn.send((total, len(_W_EVAL_CACHE)))


class Pool:
    def __init__(self, positions, n_workers):
        self.workers = []
        n = len(positions)
        chunk = (n + n_workers - 1) // n_workers
        for i in range(n_workers):
            sl = positions[i * chunk:(i + 1) * chunk]
            if not sl:
                continue
            parent, child = mp.Pipe()
            p = mp.Process(target=_worker_loop, args=(child, sl), daemon=True)
            p.start()
            self.workers.append((p, parent))
        for _, conn in self.workers:
            assert conn.recv() == 'ready'

    def mse(self, scalars, floats, psqt, scale):
        for _, conn in self.workers:
            conn.send(('MSE', scalars, floats, psqt, scale))
        total = 0.0
        count = 0
        for _, conn in self.workers:
            t, c = conn.recv()
            total += t
            count += c
        return total / count

    def fit_scale(self, scalars, floats, psqt):
        for _, conn in self.workers:
            conn.send(('CACHE_EVALS', scalars, floats, psqt))
        for _, conn in self.workers:
            conn.recv()

        def mse_for_scale(scale):
            for _, conn in self.workers:
                conn.send(('MSE_SCALE', scale))
            total = 0.0
            count = 0
            for _, conn in self.workers:
                t, c = conn.recv()
                total += t
                count += c
            return total / count

        lo, hi = 0.1, 5.0
        for _ in range(50):
            m1 = lo + (hi - lo) / 3
            m2 = hi - (hi - lo) / 3
            if mse_for_scale(m1) < mse_for_scale(m2):
                hi = m2
            else:
                lo = m1
        scale = (lo + hi) / 2
        return scale, mse_for_scale(scale)

    def close(self):
        for _, conn in self.workers:
            try:
                conn.send(None)
            except Exception:
                pass


def save_best_cp(scalars, floats, psqt, scale, best_mse):
    os.makedirs(os.path.dirname(_OUTPUT_CP_PARAMS_PATH) or '.', exist_ok=True)
    os.makedirs(os.path.dirname(_OUTPUT_CP_PARAMETERS_PATH) or '.', exist_ok=True)
    params = {
        'params': scalars,
        'phase_thresholds': floats,
        'psqt': psqt,
        'scale': scale,
        'mse': best_mse,
    }
    with open(_OUTPUT_CP_PARAMS_PATH, 'w') as f:
        json.dump(params, f, indent=2)
    lines = [
        '# Auto-generated by texel_tune_cp.py - SF HCE CP regression\n',
        f'# MSE = {best_mse:.6f}  scale = {scale:.4f}\n\n',
        'from engine.core.constants import PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING\n\n',
    ]
    lines.append(f'MG_VALUES = {{PAWN: {scalars["mg_pawn"]}, KNIGHT: {scalars["mg_knight"]}, ')
    lines.append(f'BISHOP: {scalars["mg_bishop"]}, ROOK: {scalars["mg_rook"]}, ')
    lines.append(f'QUEEN: {scalars["mg_queen"]}, KING: 0}}\n')
    lines.append(f'EG_VALUES = {{PAWN: {scalars["eg_pawn"]}, KNIGHT: {scalars["eg_knight"]}, ')
    lines.append(f'BISHOP: {scalars["eg_bishop"]}, ROOK: {scalars["eg_rook"]}, ')
    lines.append(f'QUEEN: {scalars["eg_queen"]}, KING: 0}}\n\n')
    for name, const_name in _serial.SCALAR_TO_CONST.items():
        lines.append(f'{const_name} = {repr(scalars[name])}\n')
    for name, const_name in _serial.FLOAT_TO_CONST.items():
        lines.append(f'{const_name} = {repr(floats[name])}\n')
    lines.append('\n')
    lines.append('PASSED_PAWN_BONUS = [0, ')
    lines.append(', '.join(str(scalars[f'passed_pawn_rank{i}']) for i in range(2, 8)))
    lines.append(', 0]\n\n')
    for name in PSQT_NAMES:
        lines.extend(_serial._format_list(name.upper(), psqt[name]))
    lines.append('PSQTs = {\n')
    lines.append('    PAWN:   (MG_PAWN,   EG_PAWN),\n')
    lines.append('    KNIGHT: (MG_KNIGHT, EG_KNIGHT),\n')
    lines.append('    BISHOP: (MG_BISHOP, EG_BISHOP),\n')
    lines.append('    ROOK:   (MG_ROOK,   EG_ROOK),\n')
    lines.append('    QUEEN:  (MG_QUEEN,  EG_QUEEN),\n')
    lines.append('    KING:   (MG_KING,   EG_KING),\n')
    lines.append('}\n')
    with open(_OUTPUT_CP_PARAMETERS_PATH, 'w') as f:
        f.writelines(lines)
    print(f'  saved: {_OUTPUT_CP_PARAMS_PATH}  {_OUTPUT_CP_PARAMETERS_PATH}  (MSE={best_mse:.6f})', flush=True)


def coordinate_descent_cp(pool, positions, scalars, floats, psqt, scale, max_passes):
    apply_all(scalars, floats, psqt)
    best = pool.mse(scalars, floats, psqt, scale)
    print(f'start MSE = {best:.2f} (scale={scale:.4f})', flush=True)
    save_best_cp(scalars, floats, psqt, scale, best)

    int_steps = [8, 4, 2, 1]
    float_steps = [0.04, 0.02, 0.01]

    for p in range(max_passes):
        istep = int_steps[min(p, len(int_steps) - 1)]
        fstep = float_steps[min(p, len(float_steps) - 1)]
        improved = 0

        for name, default, lo, hi in SCALAR_PARAMS:
            for delta in (istep, -istep):
                v = scalars[name] + delta
                if v < lo or v > hi:
                    continue
                old = scalars[name]
                scalars[name] = v
                m = pool.mse(scalars, floats, psqt, scale)
                if m < best - 1e-6:
                    best = m
                    improved += 1
                    break
                scalars[name] = old

        for name, default, lo, hi in FLOAT_PARAMS:
            for delta in (fstep, -fstep):
                v = round(floats[name] + delta, 4)
                if v < lo or v > hi:
                    continue
                old = floats[name]
                floats[name] = v
                m = pool.mse(scalars, floats, psqt, scale)
                if m < best - 1e-6:
                    best = m
                    improved += 1
                    break
                floats[name] = old

        for name in PSQT_NAMES:
            base = _serial._BASELINE_PSQT[name]
            arr = psqt[name]
            for sq in range(64):
                losq = base[sq] - PSQT_DELTA
                hisq = base[sq] + PSQT_DELTA
                for delta in (istep, -istep):
                    v = arr[sq] + delta
                    if v < losq or v > hisq:
                        continue
                    old = arr[sq]
                    arr[sq] = v
                    m = pool.mse(scalars, floats, psqt, scale)
                    if m < best - 1e-6:
                        best = m
                        improved += 1
                        break
                    arr[sq] = old

        scale, _ = pool.fit_scale(scalars, floats, psqt)
        best = pool.mse(scalars, floats, psqt, scale)
        save_best_cp(scalars, floats, psqt, scale, best)
        print(f'pass {p+1}/{max_passes}: MSE={best:.2f} scale={scale:.4f} '
              f'improvements={improved} (istep={istep})', flush=True)

        if improved == 0 and istep == 1:
            print('converged (no improvement at step 1)', flush=True)
            break

    return best, scale


def main():
    fens_file  = sys.argv[1] if len(sys.argv) > 1 else 'tune/fens_cp.txt'
    cap        = int(sys.argv[2]) if len(sys.argv) > 2 else 200000
    max_passes = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    n_workers  = int(sys.argv[4]) if len(sys.argv) > 4 else mp.cpu_count()
    out_prefix = sys.argv[5] if len(sys.argv) > 5 else None

    if out_prefix:
        global _OUTPUT_CP_PARAMS_PATH, _OUTPUT_CP_PARAMETERS_PATH
        _OUTPUT_CP_PARAMS_PATH = f'{out_prefix}.json'
        _OUTPUT_CP_PARAMETERS_PATH = f'{out_prefix}.py'

    if not os.path.exists(fens_file):
        print(f'fen file not found: {fens_file}')
        sys.exit(1)

    _serial._BASELINE_PSQT = {name: list(getattr(_params, name.upper())) for name in PSQT_NAMES}

    print(f'loading dataset (cap={cap:,})...', flush=True)
    positions = load_dataset_cp(fens_file, cap)
    print(f'loaded {len(positions):,} positions', flush=True)

    scalars = {name: d for name, d, lo, hi in SCALAR_PARAMS}
    floats  = {name: d for name, d, lo, hi in FLOAT_PARAMS}
    psqt    = {name: list(_serial._BASELINE_PSQT[name]) for name in PSQT_NAMES}

    apply_all(scalars, floats, psqt)

    print(f'starting {n_workers} workers...', flush=True)
    pool = Pool(positions, n_workers)

    scale, start_mse = pool.fit_scale(scalars, floats, psqt)
    print(f'fitted scale = {scale:.4f} (MSE={start_mse:.2f})', flush=True)

    n_params = len(SCALAR_PARAMS) + len(FLOAT_PARAMS) + len(PSQT_NAMES) * 64
    print(f'cp coordinate descent: {n_params} params, {len(positions)} positions, '
          f'{max_passes} passes, {len(pool.workers)} workers\n', flush=True)

    best, scale = coordinate_descent_cp(pool, positions, scalars, floats, psqt, scale, max_passes)
    pool.close()
    print(f'\nbest MSE: {best:.2f}  scale={scale:.4f}')
    save_best_cp(scalars, floats, psqt, scale, best)


if __name__ == '__main__':
    main()

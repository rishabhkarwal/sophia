"""
parallel texel tuner — multiprocess MSE evaluation over the position set

same coordinate descent as texel_tune.py, but the MSE evaluation (the hot loop
over all positions) is split across N persistent worker processes. each worker
owns a fixed slice of the dataset; the main process broadcasts the current
parameter vector and each worker returns a partial (sum_sq, count). the descent
itself stays sequential (Gauss-Seidel — correct), only the per-evaluation
position loop is parallelised

at startup it asserts the parallel MSE equals the single-process MSE to within
1e-9 on the loaded data, so a protocol bug can't silently corrupt the tune

    venv/bin/python tune/texel_tune_mp.py [fens_file] [max_positions] [max_passes] [workers]
    venv/bin/python tune/texel_tune_mp.py --smoke [fens_file]

falls back to the serial path automatically if the self-check fails
"""

import math
import os
import sys
import multiprocessing as mp

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'sophia'))

from texel_tune import (
    SCALAR_PARAMS, FLOAT_PARAMS, PSQT_NAMES, PSQT_DELTA,
    apply_all, apply_scalars, apply_psqt, load_dataset, save_best, make_eval_fn, mse,
)
import texel_tune as _serial
import engine.core.parameters as _params


_W_EVAL_CACHE = None   # cached raw white-evals for fit_k


def _worker_loop(conn, fens_slice):
    # Parse each FEN to a State once. evaluate() depends on params only via the
    # incremental mg_score/eg_score/phase (recomputed by calculate_initial_score)
    # — everything else in the State is param-independent (bitboards, passed-pawn
    # masks, geometry). So we re-score the cached states each MSE call and skip
    # the expensive FEN string parse. Verified identical to fresh-parse eval.
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

    conn.send('ready')
    while True:
        msg = conn.recv()
        if msg is None:
            break
        cmd = msg[0]

        if cmd == 'MSE':
            _, scalars, floats, psqt, K = msg
            apply_scalars(scalars, floats)
            apply_psqt(psqt)
            _e.init_eval_tables()
            inv_k = 1.0 / K
            total = 0.0
            for st, label in states:
                s = raw_white_eval(st)
                sig = 1.0 / (1.0 + math.exp(-s * inv_k))
                d = sig - label
                total += d * d
            conn.send((total, len(states)))

        elif cmd == 'CACHE_EVALS':
            _, scalars, floats, psqt = msg
            apply_scalars(scalars, floats)
            apply_psqt(psqt)
            _e.init_eval_tables()
            _W_EVAL_CACHE = [(raw_white_eval(st), label) for st, label in states]
            conn.send(len(_W_EVAL_CACHE))

        elif cmd == 'MSE_K':
            _, K = msg
            inv_k = 1.0 / K
            total = 0.0
            for s, label in _W_EVAL_CACHE:
                sig = 1.0 / (1.0 + math.exp(-s * inv_k))
                d = sig - label
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

    def mse(self, scalars, floats, psqt, K):
        for _, conn in self.workers:
            conn.send(('MSE', scalars, floats, psqt, K))
        total = 0.0
        count = 0
        for _, conn in self.workers:
            t, c = conn.recv()
            total += t
            count += c
        return total / count

    def fit_k(self, scalars, floats, psqt):
        for _, conn in self.workers:
            conn.send(('CACHE_EVALS', scalars, floats, psqt))
        for _, conn in self.workers:
            conn.recv()

        def mse_for_k(K):
            for _, conn in self.workers:
                conn.send(('MSE_K', K))
            total = 0.0
            count = 0
            for _, conn in self.workers:
                t, c = conn.recv()
                total += t
                count += c
            return total / count

        lo, hi = 50.0, 800.0
        for _ in range(40):
            m1 = lo + (hi - lo) / 3
            m2 = hi - (hi - lo) / 3
            if mse_for_k(m1) < mse_for_k(m2):
                hi = m2
            else:
                lo = m1
        K = (lo + hi) / 2
        return K, mse_for_k(K)

    def close(self):
        for _, conn in self.workers:
            try:
                conn.send(None)
            except Exception:
                pass



def coordinate_descent_mp(pool, positions, scalars, floats, psqt, K, max_passes):
    apply_all(scalars, floats, psqt)
    best = pool.mse(scalars, floats, psqt, K)
    print(f'start MSE = {best:.6f} (K={K:.1f})', flush=True)
    save_best(scalars, floats, psqt, K, best)

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
                m = pool.mse(scalars, floats, psqt, K)
                if m < best - 1e-9:
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
                m = pool.mse(scalars, floats, psqt, K)
                if m < best - 1e-9:
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
                    m = pool.mse(scalars, floats, psqt, K)
                    if m < best - 1e-9:
                        best = m
                        improved += 1
                        break
                    arr[sq] = old

        K, _ = pool.fit_k(scalars, floats, psqt)
        best = pool.mse(scalars, floats, psqt, K)
        save_best(scalars, floats, psqt, K, best)
        print(f'pass {p+1}/{max_passes}: MSE={best:.6f} K={K:.1f} '
              f'improvements={improved} (istep={istep})', flush=True)

        if improved == 0 and istep == 1:
            print('converged (no improvement at step 1)', flush=True)
            break

    return best, K


def main():
    smoke = len(sys.argv) > 1 and sys.argv[1] == '--smoke'
    if smoke:
        fens_file  = sys.argv[2] if len(sys.argv) > 2 else 'tune/fens_sf_all.txt'
        cap        = 1000
        max_passes = 1
        n_workers  = 2
        _serial.configure_outputs(
            os.path.join('tune', 'smoke_params_cython_wdl.json'),
            os.path.join('tune', 'smoke_parameters_cython_wdl.py'),
        )
    else:
        fens_file   = sys.argv[1] if len(sys.argv) > 1 else 'tune/fens_sf_all.txt'
        cap         = int(sys.argv[2]) if len(sys.argv) > 2 else 60000
        max_passes  = int(sys.argv[3]) if len(sys.argv) > 3 else 8
        n_workers   = int(sys.argv[4]) if len(sys.argv) > 4 else mp.cpu_count()
        out_prefix  = sys.argv[5] if len(sys.argv) > 5 else None
        warm_start  = sys.argv[6] if len(sys.argv) > 6 else None
        if out_prefix:
            _serial.configure_outputs(
                f'{out_prefix}.json',
                f'{out_prefix}.py',
            )

    if not os.path.exists(fens_file):
        print(f'fen file not found: {fens_file}')
        sys.exit(1)

    _serial._BASELINE_PSQT = {name: list(getattr(_params, name.upper())) for name in PSQT_NAMES}

    positions = load_dataset(fens_file, cap)

    scalars = {name: d for name, d, lo, hi in SCALAR_PARAMS}
    floats  = {name: d for name, d, lo, hi in FLOAT_PARAMS}
    psqt    = {name: list(_serial._BASELINE_PSQT[name]) for name in PSQT_NAMES}

    if warm_start and os.path.exists(warm_start):
        import json as _json
        with open(warm_start) as _f:
            _ws = _json.load(_f)
        for k, v in _ws.get('params', {}).items():
            if k in scalars:
                scalars[k] = v
            elif k in floats:
                floats[k] = float(v)
        for k, v in _ws.get('phase_thresholds', {}).items():
            if k in floats:
                floats[k] = float(v)
        for k, v in _ws.get('psqt', {}).items():
            if k in psqt:
                psqt[k] = list(v)
        print(f'warm start from {warm_start}', flush=True)

    apply_all(scalars, floats, psqt)

    print(f'starting {n_workers} workers...', flush=True)
    pool = Pool(positions, n_workers)

    # ── self-check: parallel MSE must equal serial MSE on the same params ──
    white_eval = make_eval_fn()
    apply_all(scalars, floats, psqt)
    serial_val = mse(positions, white_eval, 300.0)
    par_val = pool.mse(scalars, floats, psqt, 300.0)
    if abs(serial_val - par_val) > 1e-9:
        print(f'self-check failed: serial={serial_val:.10f} parallel={par_val:.10f}', flush=True)
        print('falling back to serial texel_tune', flush=True)
        pool.close()
        K, _ = _serial.fit_k(positions, white_eval)
        best, K = _serial.coordinate_descent(positions, scalars, floats, psqt, K, max_passes)
        print(f'\nbest MSE: {best:.6f} (K={K:.1f})')
        return
    print(f'self-check OK (MSE={serial_val:.6f} matches parallel to 1e-9)', flush=True)

    K, k_mse = pool.fit_k(scalars, floats, psqt)
    print(f'fitted K = {K:.1f} (MSE={k_mse:.6f})', flush=True)

    n_params = len(SCALAR_PARAMS) + len(FLOAT_PARAMS) + len(PSQT_NAMES) * 64
    print(f'parallel coordinate descent: {n_params} params, {len(positions)} positions, '
          f'{max_passes} passes, {len(pool.workers)} workers\n', flush=True)

    best, K = coordinate_descent_mp(pool, positions, scalars, floats, psqt, K, max_passes)
    pool.close()
    print(f'\nbest MSE: {best:.6f} (K={K:.1f})')
    save_best(scalars, floats, psqt, K, best)
    print(f'saved: {_serial._OUTPUT_PARAMS_PATH} + {_serial._OUTPUT_PARAMETERS_PATH}')


if __name__ == '__main__':
    main()

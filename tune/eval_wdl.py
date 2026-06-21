"""evaluate a candidate's WDL texel MSE on one or more FEN datasets"""

import argparse
import json
import os
import sys
import multiprocessing as mp


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    parser.add_argument("--params")
    parser.add_argument("--cap", type=int, default=0)
    parser.add_argument("--workers", type=int, default=mp.cpu_count())
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--fit-k")
    group.add_argument("--k", type=float)
    group.add_argument("--k-from")
    parser.add_argument("--json-out")
    return parser.parse_args()


args = parse_args()

if args.params:
    os.environ["SOPHIA_TUNE_PARAMS"] = args.params

import texel_tune as _texel
from texel_tune_mp import Pool
import engine.core.parameters as _params


def read_k(path):
    with open(path) as f:
        data = json.load(f)
    if "K" not in data:
        print(f"K missing from {path}", file=sys.stderr)
        sys.exit(1)
    return float(data["K"])


def make_vectors():
    _texel._BASELINE_PSQT = {name: list(getattr(_params, name.upper())) for name in _texel.PSQT_NAMES}
    scalars = {name: d for name, d, lo, hi in _texel.SCALAR_PARAMS}
    floats = {name: d for name, d, lo, hi in _texel.FLOAT_PARAMS}
    psqt = {name: list(_texel._BASELINE_PSQT[name]) for name in _texel.PSQT_NAMES}
    _texel.apply_all(scalars, floats, psqt)
    return scalars, floats, psqt


def load_positions(path, cache):
    if path not in cache:
        cache[path] = _texel.load_dataset(path, args.cap)
    return cache[path]


def with_pool(positions, scalars, floats, psqt, action):
    workers = min(args.workers, len(positions))
    if workers <= 0:
        print("no positions loaded", file=sys.stderr)
        sys.exit(1)
    pool = Pool(positions, workers)
    result = action(pool)
    pool.close()
    return result


def fit_k(path, cache, scalars, floats, psqt):
    positions = load_positions(path, cache)

    def action(pool):
        return pool.fit_k(scalars, floats, psqt)

    return with_pool(positions, scalars, floats, psqt, action)


def score_file(path, K, cache, scalars, floats, psqt):
    positions = load_positions(path, cache)

    def action(pool):
        return pool.mse(scalars, floats, psqt, K)

    mse_val = with_pool(positions, scalars, floats, psqt, action)
    return {
        "file": path,
        "positions": len(positions),
        "K": K,
        "mse": mse_val,
    }


def main():
    scalars, floats, psqt = make_vectors()
    cache = {}

    if args.k is not None:
        K = args.k
        k_source = "argument"
    elif args.k_from:
        K = read_k(args.k_from)
        k_source = args.k_from
    elif args.fit_k:
        K, fit_mse = fit_k(args.fit_k, cache, scalars, floats, psqt)
        k_source = args.fit_k
        print(f"fit K on {args.fit_k}: K={K:.6f} MSE={fit_mse:.9f}", flush=True)
    else:
        K = None
        k_source = "per-file fit"

    print(f"params: {args.params or 'current'}")
    print(f"K source: {k_source}")

    results = []
    for path in args.files:
        if K is None:
            file_K, fit_mse = fit_k(path, cache, scalars, floats, psqt)
            result = {"file": path, "positions": len(cache[path]), "K": file_K, "mse": fit_mse}
        else:
            result = score_file(path, K, cache, scalars, floats, psqt)
        results.append(result)
        print(f"{path}: positions={result['positions']:,} K={result['K']:.6f} MSE={result['mse']:.9f}", flush=True)

    if args.json_out:
        report = {
            "params": args.params,
            "cap": args.cap,
            "workers": args.workers,
            "K_source": k_source,
            "results": results,
        }
        os.makedirs(os.path.dirname(args.json_out) or ".", exist_ok=True)
        with open(args.json_out, "w") as f:
            json.dump(report, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()

"""evaluate a candidate's CP-regression MSE on one or more FEN datasets"""

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
    group.add_argument("--fit-scale")
    group.add_argument("--scale", type=float)
    group.add_argument("--scale-from")
    parser.add_argument("--json-out")
    return parser.parse_args()


args = parse_args()

if args.params:
    os.environ["SOPHIA_TUNE_PARAMS"] = args.params

import texel_tune as _texel
import texel_tune_cp as _cp
import engine.core.parameters as _params


def read_scale(path):
    with open(path) as f:
        data = json.load(f)
    if "scale" not in data:
        print(f"scale missing from {path}", file=sys.stderr)
        sys.exit(1)
    return float(data["scale"])


def make_vectors():
    _texel._BASELINE_PSQT = {name: list(getattr(_params, name.upper())) for name in _texel.PSQT_NAMES}
    scalars = {name: d for name, d, lo, hi in _texel.SCALAR_PARAMS}
    floats = {name: d for name, d, lo, hi in _texel.FLOAT_PARAMS}
    psqt = {name: list(_texel._BASELINE_PSQT[name]) for name in _texel.PSQT_NAMES}
    _texel.apply_all(scalars, floats, psqt)
    return scalars, floats, psqt


def load_positions(path, cache):
    if path not in cache:
        cap = args.cap if args.cap else 10 ** 18
        cache[path] = _cp.load_dataset_cp(path, cap)
        print(f"loaded {len(cache[path]):,} positions from {path}", flush=True)
    return cache[path]


def with_pool(positions, action):
    workers = min(args.workers, len(positions))
    if workers <= 0:
        print("no positions loaded", file=sys.stderr)
        sys.exit(1)
    pool = _cp.Pool(positions, workers)
    result = action(pool)
    pool.close()
    return result


def fit_scale(path, cache, scalars, floats, psqt):
    positions = load_positions(path, cache)

    def action(pool):
        return pool.fit_scale(scalars, floats, psqt)

    return with_pool(positions, action)


def score_file(path, scale, cache, scalars, floats, psqt):
    positions = load_positions(path, cache)

    def action(pool):
        return pool.mse(scalars, floats, psqt, scale)

    mse_val = with_pool(positions, action)
    return {
        "file": path,
        "positions": len(positions),
        "scale": scale,
        "mse": mse_val,
    }


def main():
    scalars, floats, psqt = make_vectors()
    cache = {}

    if args.scale is not None:
        scale = args.scale
        scale_source = "argument"
    elif args.scale_from:
        scale = read_scale(args.scale_from)
        scale_source = args.scale_from
    elif args.fit_scale:
        scale, fit_mse = fit_scale(args.fit_scale, cache, scalars, floats, psqt)
        scale_source = args.fit_scale
        print(f"fit scale on {args.fit_scale}: scale={scale:.6f} MSE={fit_mse:.3f}", flush=True)
    else:
        scale = None
        scale_source = "per-file fit"

    print(f"params: {args.params or 'current'}")
    print(f"scale source: {scale_source}")

    results = []
    for path in args.files:
        if scale is None:
            file_scale, fit_mse = fit_scale(path, cache, scalars, floats, psqt)
            result = {"file": path, "positions": len(cache[path]), "scale": file_scale, "mse": fit_mse}
        else:
            result = score_file(path, scale, cache, scalars, floats, psqt)
        results.append(result)
        print(f"{path}: positions={result['positions']:,} scale={result['scale']:.6f} MSE={result['mse']:.3f}", flush=True)

    if args.json_out:
        report = {
            "params": args.params,
            "cap": args.cap,
            "workers": args.workers,
            "scale_source": scale_source,
            "results": results,
        }
        os.makedirs(os.path.dirname(args.json_out) or ".", exist_ok=True)
        with open(args.json_out, "w") as f:
            json.dump(report, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()

"""split a FEN dataset into deterministic 80/10/10 train/valid/test splits"""

import argparse
import hashlib
import json
import os
import sys


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--out-prefix")
    parser.add_argument("--train", type=float, default=0.80)
    parser.add_argument("--valid", type=float, default=0.10)
    parser.add_argument("--test", type=float, default=0.10)
    parser.add_argument("--block-size", type=int, default=256)
    parser.add_argument("--salt", default="sophia-tune-v1")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def ratio_bounds(train, valid, test):
    total = train + valid + test
    if total <= 0: raise ValueError("split ratios must sum to a positive value")
    train /= total
    valid /= total
    return train, train + valid


def split_name(out_prefix, name):
    return f"{out_prefix}.{name}.txt"


def block_fraction(salt, block_idx):
    key = f"{salt}:{block_idx}".encode()
    raw = hashlib.sha256(key).digest()[:8]
    return int.from_bytes(raw, "big") / float(1 << 64)


def choose_split(frac, train_bound, valid_bound):
    if frac < train_bound: return "train"
    if frac < valid_bound: return "valid"
    return "test"


def check_outputs(paths, overwrite):
    if overwrite: return
    existing = [path for path in paths if os.path.exists(path)]
    if existing:
        print("refusing to overwrite existing split files:", file=sys.stderr)
        for path in existing:
            print(f"  {path}", file=sys.stderr)
        sys.exit(1)


def main():
    args = parse_args()
    if args.block_size <= 0: raise ValueError("--block-size must be positive")
    if not os.path.exists(args.input):
        print(f"input not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if args.out_prefix:
        out_prefix = args.out_prefix
    else:
        stem = os.path.splitext(os.path.basename(args.input))[0]
        out_prefix = os.path.join(os.path.dirname(args.input), "splits", stem)

    os.makedirs(os.path.dirname(out_prefix) or ".", exist_ok=True)
    paths = {
        "train": split_name(out_prefix, "train"),
        "valid": split_name(out_prefix, "valid"),
        "test": split_name(out_prefix, "test"),
    }
    manifest_path = f"{out_prefix}.manifest.json"
    check_outputs(list(paths.values()) + [manifest_path], args.overwrite)

    train_bound, valid_bound = ratio_bounds(args.train, args.valid, args.test)
    counts = {"train": 0, "valid": 0, "test": 0}

    handles = {name: open(path, "w") for name, path in paths.items()}
    with open(args.input) as f:
        for line_idx, line in enumerate(f):
            block_idx = line_idx // args.block_size
            frac = block_fraction(args.salt, block_idx)
            name = choose_split(frac, train_bound, valid_bound)
            handles[name].write(line)
            counts[name] += 1
    for handle in handles.values():
        handle.close()

    manifest = {
        "input": args.input,
        "out_prefix": out_prefix,
        "ratios": {"train": args.train, "valid": args.valid, "test": args.test},
        "block_size": args.block_size,
        "salt": args.salt,
        "counts": counts,
        "paths": paths,
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    total = sum(counts.values())
    print(f"split {total:,} lines from {args.input}")
    for name in ["train", "valid", "test"]:
        pct = 100.0 * counts[name] / total if total else 0.0
        print(f"{name}: {counts[name]:,} ({pct:.2f}%) -> {paths[name]}")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()

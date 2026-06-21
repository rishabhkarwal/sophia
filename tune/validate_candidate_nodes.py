"""validate an eval candidate against baseline using fixed-node game matches"""

import argparse
import json
import logging
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tune.search_tune as _match

logging.getLogger("chess.engine").setLevel(logging.CRITICAL)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate")
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--parallel", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260621)
    parser.add_argument("--out")
    return parser.parse_args()


def default_out(candidate):
    stem = Path(candidate).stem
    return ROOT / "tune" / "reports" / f"{stem}_nodes_match.json"


def main():
    args = parse_args()
    candidate = Path(args.candidate).resolve()
    if not candidate.exists():
        print(f"candidate not found: {candidate}", file=sys.stderr)
        sys.exit(1)

    random.seed(args.seed)
    with open(candidate) as f:
        params = json.load(f)

    openings = _match.load_openings()
    score, played = _match.run_match(params, args.games, args.parallel, openings)
    report = {
        "candidate": str(candidate),
        "games": played,
        "score": score,
        "score_fraction": score / played,
        "nodes_per_move": _match.NODES_PER_MOVE,
        "parallel": args.parallel,
        "seed": args.seed,
    }

    out_path = Path(args.out).resolve() if args.out else default_out(candidate)
    os.makedirs(out_path.parent, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    print(json.dumps(report, indent=2))
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()

"""run the engine on a set of positions and collect debug counter output"""

import argparse
import contextlib
import io
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAIR_NAMES = {
    "nmp": ("attempts", "cutoffs"),
    "rfp": ("attempts", "cutoffs"),
    "snmp": ("attempts", "cutoffs"),
    "razor": ("attempts", "cutoffs"),
    "see": ("prunes", "tests"),
    "qsee": ("prunes", "tests"),
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("fens_file")
    parser.add_argument("--params")
    parser.add_argument("--out", default="tune/reports/debug_counters.jsonl")
    parser.add_argument("--depth", type=int, default=5)
    parser.add_argument("--nodes", type=int, default=0)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--stride", type=int, default=1)
    return parser.parse_args()


def load_fens(path, limit, stride):
    fens = []
    with open(path) as f:
        for line_idx, line in enumerate(f):
            if stride > 1 and line_idx % stride != 0:
                continue
            line = line.strip()
            if not line:
                continue
            fen = line.split(" | ", 1)[0].strip()
            fens.append(fen)
            if limit and len(fens) >= limit:
                break
    return fens


def parse_kv_pairs(text):
    values = {}
    for key, value in re.findall(r"([a-zA-Z_]+)=([^ ]+)", text):
        if "/" in value:
            parts = value.split("(", 1)[0].split("/")
            if len(parts) == 2 and parts[0].lstrip("-").isdigit() and parts[1].lstrip("-").isdigit():
                left_name, right_name = PAIR_NAMES.get(key, ("left", "right"))
                values[f"{key}_{left_name}"] = int(parts[0])
                values[f"{key}_{right_name}"] = int(parts[1])
                continue
        compact = re.match(r"(-?\d+)\(([^)]*)\)$", value)
        if compact:
            values[key] = int(compact.group(1))
            values[f"{key}_note"] = compact.group(2)
            continue
        if value.lstrip("-").isdigit():
            values[key] = int(value)
            continue
        values[key] = value
    tt_shallow = re.search(r"tt_shallow=(\d+)\(of (\d+)\)", text)
    if tt_shallow:
        values["tt_shallow"] = int(tt_shallow.group(1))
        values["tt_total"] = int(tt_shallow.group(2))
    lmr = re.search(r"lmr=(\d+)\(re=(\d+),", text)
    if lmr:
        values["lmr"] = int(lmr.group(1))
        values["lmr_researches"] = int(lmr.group(2))
    iid = re.search(r"iid=(\d+)\(tt_hit=([^)]+)\)", text)
    if iid:
        values["iid"] = int(iid.group(1))
        values["iid_tt_hit"] = iid.group(2)
    asp = re.search(r"asp=lo:(\d+)/hi:(\d+)/both:(\d+)", text)
    if asp:
        values["asp_fail_low"] = int(asp.group(1))
        values["asp_fail_high"] = int(asp.group(2))
        values["asp_fail_both"] = int(asp.group(3))
    cutoff_src = re.search(r"cutoff_src=tt:(\d+)/killer:(\d+)/cap:(\d+)/quiet:(\d+)", text)
    if cutoff_src:
        values["cutoff_tt"] = int(cutoff_src.group(1))
        values["cutoff_killer"] = int(cutoff_src.group(2))
        values["cutoff_cap"] = int(cutoff_src.group(3))
        values["cutoff_quiet"] = int(cutoff_src.group(4))
    cutoff_idx = re.search(r"cutoff_idx=avg([0-9.]+)\(1st=(\d+)/(\d+)\)", text)
    if cutoff_idx:
        values["cutoff_idx_avg"] = float(cutoff_idx.group(1))
        values["cutoff_idx_first"] = int(cutoff_idx.group(2))
        values["cutoff_idx_total"] = int(cutoff_idx.group(3))
    syzygy = re.search(r"syzygy=(\d+)\(hit=([^)]+)\)", text)
    if syzygy:
        values["syzygy"] = int(syzygy.group(1))
        values["syzygy_hit"] = syzygy.group(2)
    draws = re.search(r"draws=rep:(\d+)\+50mv:(\d+)\+insuf:(\d+)", text)
    if draws:
        values["draw_rep"] = int(draws.group(1))
        values["draw_50mv"] = int(draws.group(2))
        values["draw_insuf"] = int(draws.group(3))
    return values


def parse_output(output):
    depths = {}
    bestmove = None
    for line in output.splitlines():
        if line.startswith("bestmove "):
            bestmove = line.split()[1]
            continue
        depth = re.search(r"\[dbg [^ ]+ d(\d+)\]", line)
        if depth:
            depth_key = depth.group(1)
            entry = depths.setdefault(depth_key, {})
            if "[dbg prune" in line:
                entry["prune"] = parse_kv_pairs(line)
            elif "[dbg search" in line:
                entry["search"] = parse_kv_pairs(line)
            elif "[dbg q/order" in line:
                entry["q_order"] = parse_kv_pairs(line)
            continue
        if line.startswith("info "):
            parts = line.split()
            if "depth" not in parts:
                continue
            depth_key = parts[parts.index("depth") + 1]
            entry = depths.setdefault(depth_key, {})
            info = entry.setdefault("info", {})
            for key in ("score", "nodes", "nps", "time"):
                if key not in parts:
                    continue
                idx = parts.index(key) + 1
                if idx >= len(parts):
                    continue
                value = parts[idx]
                if key == "score" and value in ("cp", "mate") and idx + 1 < len(parts):
                    score = parts[idx + 1]
                    if score.lstrip("-").isdigit():
                        info[f"score_{value}"] = int(score)
                    continue
                if value.lstrip("-").isdigit():
                    info[key] = int(value)
                else:
                    info[key] = value
            continue
    return bestmove, depths


def search_fen(fen, depth, nodes):
    from engine.board.fen_parser import load_from_fen
    from engine.core.constants import INFINITE_TIME
    import engine.core.constants as _const
    from engine.search.search import SearchEngine

    state = load_from_fen(fen)
    _const.DEBUG = True
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        engine = SearchEngine()
        best_move = engine.get_best_move(
            state,
            INFINITE_TIME,
            depth if depth else None,
            nodes if nodes else None,
            False,
        )
    output = buf.getvalue()
    bestmove, depths = parse_output(output)
    if bestmove is None and best_move is not None:
        try:
            from engine.core.move import move_to_uci
            bestmove = move_to_uci(best_move)
        except Exception:
            bestmove = str(best_move)
    return bestmove, depths, output


def main():
    args = parse_args()
    if args.params:
        os.environ["SOPHIA_TUNE_PARAMS"] = str(Path(args.params).resolve())
    sys.path.insert(0, str(ROOT / "sophia"))

    fens = load_fens(args.fens_file, args.limit, args.stride)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as out:
        for idx, fen in enumerate(fens):
            try:
                bestmove, depths, raw = search_fen(fen, args.depth, args.nodes)
                row = {
                    "index": idx,
                    "fen": fen,
                    "params": args.params,
                    "depth": args.depth,
                    "nodes": args.nodes,
                    "bestmove": bestmove,
                    "counters": depths,
                }
            except Exception as exc:
                row = {
                    "index": idx,
                    "fen": fen,
                    "params": args.params,
                    "depth": args.depth,
                    "nodes": args.nodes,
                    "error": repr(exc),
                }
            out.write(json.dumps(row) + "\n")
            print(f"{idx + 1}/{len(fens)} {fen[:32]}...", flush=True)
    print(f"saved: {args.out}")


if __name__ == "__main__":
    main()

"""aggregate debug counter JSON files and print a summary table"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    parser.add_argument("--depth", type=int, default=0)
    return parser.parse_args()


def number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        match = re.match(r"-?\d+(?:\.\d+)?", value)
        if match:
            return float(match.group(0))
    return None


def load_rows(path):
    rows = []
    try:
        with open(path) as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    print(f"skip {path}: {exc}", file=sys.stderr)
    except OSError as exc:
        print(f"skip {path}: {exc}", file=sys.stderr)
    return rows


def select_entry(row, depth):
    counters = row.get("counters", {})
    if not counters:
        return None
    if depth:
        return counters.get(str(depth))
    depth_keys = [int(key) for key in counters if key.isdigit()]
    if not depth_keys:
        return None
    return counters.get(str(max(depth_keys)))


def add_section(agg, section):
    for key, value in section.items():
        value = number(value)
        if value is None:
            continue
        agg[key] += value


def aliases(agg, *names):
    for name in names:
        if name in agg:
            return agg[name]
    return 0


def pct(num, den):
    if not den:
        return ""
    return f"{100.0 * num / den:.1f}"


def fmt_int(value):
    return f"{int(value):,}"


def fmt_pair(cutoffs, attempts):
    if not attempts:
        return ""
    return f"{int(cutoffs):,}/{int(attempts):,} {pct(cutoffs, attempts)}%"


def aggregate(path, rows, depth, base_moves):
    agg = defaultdict(float)
    positions = 0
    errors = 0
    same_moves = 0
    comparable_moves = 0

    for row in rows:
        if row.get("error"):
            errors += 1
            continue
        entry = select_entry(row, depth)
        if entry is None:
            errors += 1
            continue

        positions += 1
        fen = row.get("fen")
        if fen in base_moves:
            comparable_moves += 1
            if row.get("bestmove") == base_moves[fen]:
                same_moves += 1

        for section in ("info", "prune", "search", "q_order"):
            values = entry.get(section, {})
            if isinstance(values, dict):
                add_section(agg, values)

    agg["positions"] = positions
    agg["errors"] = errors
    agg["same_moves"] = same_moves
    agg["comparable_moves"] = comparable_moves
    return {
        "report": Path(path).stem.replace("debug_", ""),
        "agg": agg,
    }


def print_table(title, headers, rows):
    print(title)
    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    print("  ".join(headers[idx].ljust(widths[idx]) for idx in range(len(headers))))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(row[idx].rjust(widths[idx]) if idx else row[idx].ljust(widths[idx]) for idx in range(len(row))))


def main():
    args = parse_args()
    reports = [(path, load_rows(path)) for path in args.files]
    if not reports:
        return

    base_moves = {
        row.get("fen"): row.get("bestmove")
        for row in reports[0][1]
        if row.get("fen") and row.get("bestmove")
    }
    summaries = [aggregate(path, rows, args.depth, base_moves) for path, rows in reports]

    prune_rows = []
    order_rows = []
    for summary in summaries:
        agg = summary["agg"]
        positions = agg["positions"]
        comparable = agg["comparable_moves"]
        same = pct(agg["same_moves"], comparable) if comparable else ""
        nodes = agg.get("nodes", 0)
        qnodes = agg.get("qnodes", 0)
        q_ratio = pct(qnodes, nodes) if nodes else ""
        rfp = fmt_pair(agg.get("rfp_cutoffs", 0), agg.get("rfp_attempts", 0))
        snmp = fmt_pair(agg.get("snmp_cutoffs", 0), agg.get("snmp_attempts", 0))
        nmp = fmt_pair(agg.get("nmp_cutoffs", 0), agg.get("nmp_attempts", 0))
        lmr = agg.get("lmr", 0)
        lmr_re = agg.get("lmr_researches", 0)
        tt_cut = agg.get("tt_exact", 0) + agg.get("tt_bound_cut", 0)

        see_prunes = aliases(agg, "see_prunes", "see_left", "see_attempts")
        see_tests = aliases(agg, "see_tests", "see_right", "see_cutoffs")
        qsee_prunes = aliases(agg, "qsee_prunes", "qsee_left", "qsee_attempts")
        qsee_tests = aliases(agg, "qsee_tests", "qsee_right", "qsee_cutoffs")
        asp_fail = agg.get("asp_fail_low", 0) + agg.get("asp_fail_high", 0) + agg.get("asp_fail_both", 0)

        prune_rows.append([
            summary["report"],
            fmt_int(positions),
            same,
            fmt_int(nodes),
            fmt_int(qnodes),
            q_ratio,
            rfp,
            snmp,
            nmp,
            fmt_int(agg.get("futility", 0)),
            fmt_int(agg.get("lmp", 0)),
            fmt_int(lmr),
            pct(lmr_re, lmr),
            fmt_int(tt_cut),
        ])
        order_rows.append([
            summary["report"],
            fmt_pair(see_prunes, see_tests),
            fmt_pair(qsee_prunes, qsee_tests),
            fmt_int(agg.get("cutoff_tt", 0)),
            fmt_int(agg.get("cutoff_killer", 0)),
            fmt_int(agg.get("cutoff_cap", 0)),
            fmt_int(agg.get("cutoff_quiet", 0)),
            fmt_int(asp_fail),
            fmt_int(agg.get("syzygy", 0)),
            fmt_int(agg["errors"]),
        ])

    print_table(
        "Prune/search counters",
        ["report", "pos", "same%", "nodes", "qnodes", "q/n%", "rfp", "snmp", "nmp", "fut", "lmp", "lmr", "re%", "tt_cut"],
        prune_rows,
    )
    print()
    print_table(
        "Order/qsearch counters",
        ["report", "see", "qsee", "tt", "killer", "cap", "quiet", "asp", "syzygy", "errors"],
        order_rows,
    )


if __name__ == "__main__":
    main()

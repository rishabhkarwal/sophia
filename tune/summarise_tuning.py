"""summarise all tuning reports in tune/reports/ into a comparison table"""

import argparse
import json
import sys
from pathlib import Path


SPLIT_NAMES = ("train", "valid", "test")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("reports_dir", nargs="?", default=Path(__file__).resolve().parent / "reports")
    return parser.parse_args()


def report_name(path):
    return path.stem


def split_name(path):
    stem = Path(path).stem
    for name in SPLIT_NAMES:
        if stem.endswith(name):
            return name
    return stem


def load_reports(reports_dir):
    reports = []
    for path in sorted(Path(reports_dir).glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            print(f"skip {path}: {exc}", file=sys.stderr)
            continue
        reports.append((path, data))
    return reports


def result_mses(data):
    mses = {}
    for result in data.get("results", []):
        name = split_name(result.get("file", ""))
        mse = result.get("mse")
        if mse is not None:
            mses[name] = mse
    return mses


def first_result_value(data, key):
    for result in data.get("results", []):
        if key in result:
            return result[key]
    return None


def sort_value(row):
    for key in ("test", "valid", "train"):
        value = row.get(key)
        if value is not None:
            return value
    return float("inf")


def metric_rows(reports, kind):
    rows = []
    for path, data in reports:
        results = data.get("results")
        if not isinstance(results, list):
            continue
        if kind == "wdl":
            if first_result_value(data, "K") is None:
                continue
            extra_key = "K"
            extra = first_result_value(data, "K")
        else:
            if first_result_value(data, "scale") is None or "filtered" not in path.stem:
                continue
            extra_key = "scale"
            extra = first_result_value(data, "scale")

        row = {"report": report_name(path), extra_key: extra}
        row.update(result_mses(data))
        rows.append(row)
    return sorted(rows, key=lambda row: (sort_value(row), row["report"]))


def node_rows(reports):
    rows = []
    for path, data in reports:
        if "nodes_per_move" not in data:
            continue
        if "score_fraction" in data:
            candidate = data.get("candidate", "")
            rows.append({
                "report": report_name(path),
                "candidate": Path(candidate).stem if candidate else "",
                "opponent": "baseline",
                "games": data.get("games"),
                "score": data.get("score"),
                "score%": data.get("score_fraction", 0.0) * 100.0,
                "nodes": data.get("nodes_per_move"),
            })
        elif "score_fraction_for_a" in data:
            candidate_a = data.get("candidate_a", "")
            candidate_b = data.get("candidate_b", "")
            rows.append({
                "report": report_name(path),
                "candidate": Path(candidate_a).stem if candidate_a else "",
                "opponent": Path(candidate_b).stem if candidate_b else "",
                "games": data.get("games"),
                "score": data.get("score_for_a"),
                "score%": data.get("score_fraction_for_a", 0.0) * 100.0,
                "nodes": data.get("nodes_per_move"),
            })
    return sorted(rows, key=lambda row: (row.get("score%", 0.0), row["report"]), reverse=True)


def fmt_mse(value, decimals):
    if value is None:
        return ""
    return f"{value:.{decimals}f}"


def fmt_float(value, decimals):
    if value is None:
        return ""
    return f"{value:.{decimals}f}"


def fmt_int(value):
    if value is None:
        return ""
    return f"{value:,}"


def print_table(title, headers, rows):
    print(title)
    if not rows:
        print("  none")
        return

    widths = [len(header) for header in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    header_line = "  ".join(headers[i].ljust(widths[i]) for i in range(len(headers)))
    rule = "  ".join("-" * widths[i] for i in range(len(headers)))
    print(header_line)
    print(rule)
    for row in rows:
        print("  ".join(row[i].rjust(widths[i]) if i else row[i].ljust(widths[i]) for i in range(len(row))))


def print_metric_table(title, rows, extra_key, mse_decimals):
    table_rows = []
    for row in rows:
        table_rows.append([
            row["report"],
            fmt_mse(row.get("train"), mse_decimals),
            fmt_mse(row.get("valid"), mse_decimals),
            fmt_mse(row.get("test"), mse_decimals),
            fmt_float(row.get(extra_key), 6),
        ])
    print_table(title, ["report", "train", "valid", "test", extra_key], table_rows)


def print_node_table(rows):
    table_rows = []
    for row in rows:
        table_rows.append([
            row["report"],
            row["candidate"],
            row["opponent"],
            fmt_int(row.get("games")),
            fmt_float(row.get("score"), 1),
            fmt_float(row.get("score%"), 1),
            fmt_int(row.get("nodes")),
        ])
    print_table("Node matches", ["report", "candidate", "opponent", "games", "score", "score%", "nodes"], table_rows)


def main():
    args = parse_args()
    reports = load_reports(args.reports_dir)

    print_metric_table("WDL MSE", metric_rows(reports, "wdl"), "K", 6)
    print()
    print_metric_table("Filtered CP MSE", metric_rows(reports, "cp"), "scale", 2)

    nodes = node_rows(reports)
    if nodes:
        print()
        print_node_table(nodes)


if __name__ == "__main__":
    main()

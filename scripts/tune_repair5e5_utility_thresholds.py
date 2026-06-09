"""Tune Repair5E.5 cross-fold utility risk thresholds."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_WIDE_CSV = "outputs/tables/phase5p5_repair5e5_crossfold_utility_wide.csv"
DEFAULT_SWEEP_CSV = "outputs/tables/phase5p5_repair5e5_threshold_sweep.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5e5_threshold_sweep_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5e5_threshold_sweep_summary.json"

NONADDITIVE_RULES = [
    "block_heavy",
    "block_light",
    "commit_heavy",
    "decay_090",
    "decay_095",
    "wait_heavy",
    "wait_light",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(path: str | Path, root: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def finite(value: Any, default: float = math.nan) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def mean(values: list[float]) -> float | None:
    clean = [value for value in values if math.isfinite(value)]
    return statistics.mean(clean) if clean else None


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def feature_vector(row: dict[str, str]) -> list[float]:
    return [finite(value, 0.0) for value in str(row.get("feature_values", "")).split(";") if value != ""]


def add_neighbor_distances(rows: list[dict[str, str]]) -> None:
    by_bucket: dict[tuple[str, str, str, str], list[tuple[int, list[float]]]] = defaultdict(list)
    for index, row in enumerate(rows):
        rule = row.get("best_nonadditive_rule", "additive_ltm")
        if rule == "additive_ltm":
            continue
        key = (row.get("fold_id", ""), row.get("map", ""), row.get("agents", ""), rule)
        by_bucket[key].append((index, feature_vector(row)))
    for key_rows in by_bucket.values():
        for index, values in key_rows:
            best = math.inf
            for other_index, other_values in key_rows:
                if index == other_index:
                    continue
                used = min(len(values), len(other_values))
                if used == 0:
                    continue
                distance = math.sqrt(sum((values[pos] - other_values[pos]) ** 2 for pos in range(used)) / used)
                best = min(best, distance)
            rows[index]["nearest_neighbor_distance"] = str(best if math.isfinite(best) else 0.0)
    for row in rows:
        row.setdefault("nearest_neighbor_distance", "0.0")


def selected_rule(row: dict[str, str], params: dict[str, Any]) -> str:
    rule = row.get("best_nonadditive_rule", "additive_ltm")
    if rule == "additive_ltm" or rule not in NONADDITIVE_RULES:
        return "additive_ltm"
    if rule == "commit_heavy" and not params["allow_commit_heavy"]:
        return "additive_ltm"
    margin = finite(row.get("predicted_margin_ratio"), 0.0)
    support = finite(row.get(f"{rule}_support_instances"), 0.0)
    risk = finite(row.get(f"{rule}_false_positive_risk"), 1.0)
    agreement = finite(row.get(f"{rule}_fold_agreement"), 0.0)
    distance = finite(row.get("nearest_neighbor_distance"), 0.0)
    iteration = finite(row.get("iteration"), 0.0)
    risk_cap = params["rule_risk_caps"].get(rule, params["max_rule_risk"])
    if margin < params["min_predicted_margin"]:
        return "additive_ltm"
    if support < params["min_support_count"]:
        return "additive_ltm"
    if risk > risk_cap:
        return "additive_ltm"
    if agreement < params["min_fold_agreement"]:
        return "additive_ltm"
    if distance > params["max_neighbor_distance"]:
        return "additive_ltm"
    if iteration > params["non_additive_budget"]:
        return "additive_ltm"
    return rule


def evaluate(rows: list[dict[str, str]], params: dict[str, Any], *, epsilon_ratio: float) -> dict[str, Any]:
    deltas: list[float] = []
    success_deltas: list[float] = []
    selected: list[tuple[dict[str, str], str, float]] = []
    group_deltas: dict[tuple[str, int], list[float]] = defaultdict(list)
    group_nonadditive: Counter[tuple[str, int]] = Counter()
    rule_counts: Counter[str] = Counter()
    for row in rows:
        rule = selected_rule(row, params)
        if rule == "additive_ltm":
            delta = 0.0
            success_delta = 0.0
        else:
            delta = finite(row.get(f"{rule}_utility_delta_ratio"), 0.0)
            success_delta = finite(row.get(f"{rule}_success_delta_vs_ltm"), 0.0)
            selected.append((row, rule, delta))
            group_nonadditive[(row.get("map", ""), int(finite(row.get("agents"), 0.0)))] += 1
            rule_counts[rule] += 1
        deltas.append(delta)
        success_deltas.append(success_delta)
        group_deltas[(row.get("map", ""), int(finite(row.get("agents"), 0.0)))].append(delta)
    better = sum(1 for value in deltas if value < -epsilon_ratio)
    worse = sum(1 for value in deltas if value > epsilon_ratio)
    equal = len(deltas) - better - worse
    ratio_worse_groups = sum(1 for values in group_deltas.values() if (mean(values) or 0.0) > epsilon_ratio)
    success_worse_groups = sum(
        1
        for key in group_deltas
        if any(success_deltas[index] < 0.0 for index, row in enumerate(rows) if (row.get("map", ""), int(finite(row.get("agents"), 0.0))) == key)
    )
    zero_nonadditive_groups = sum(1 for key in group_deltas if group_nonadditive[key] == 0)
    return {
        "rows": len(rows),
        "selected_nonadditive_rows": len(selected),
        "better": better,
        "equal": equal,
        "worse": worse,
        "mean_delta_ratio_vs_ltm": mean(deltas),
        "ratio_worse_than_ltm_groups": ratio_worse_groups,
        "success_worse_than_ltm_groups": success_worse_groups,
        "zero_nonadditive_groups": zero_nonadditive_groups,
        "total_groups": len(group_deltas),
        "selected_rule_distribution": dict(sorted(rule_counts.items())),
    }


def pass_criteria(stats: dict[str, Any]) -> bool:
    return (
        int(stats["success_worse_than_ltm_groups"]) == 0
        and int(stats["ratio_worse_than_ltm_groups"]) <= 1
        and stats["mean_delta_ratio_vs_ltm"] is not None
        and float(stats["mean_delta_ratio_vs_ltm"]) < 0.0
        and int(stats["better"]) > int(stats["worse"])
        and int(stats["zero_nonadditive_groups"]) < int(stats["total_groups"])
    )


def score_sweep(row: dict[str, Any]) -> tuple[int, int, float, int, int, float]:
    return (
        1 if row.get("passes_primary_goal") else 0,
        int(row.get("better", 0)) - int(row.get("worse", 0)),
        -float(row.get("mean_delta_ratio_vs_ltm") or 0.0),
        -int(row.get("ratio_worse_than_ltm_groups", 999)),
        int(row.get("selected_nonadditive_rows", 0)),
        float(row.get("max_neighbor_distance") or 0.0),
    )


def shuffled_diagnostic(rows: list[dict[str, str]], params: dict[str, Any], *, epsilon_ratio: float) -> dict[str, Any]:
    shifted = [dict(row) for row in rows]
    labels = [row.get("best_nonadditive_rule", "additive_ltm") for row in shifted]
    if len(labels) > 1:
        rotated = labels[1:] + labels[:1]
        for row, label in zip(shifted, rotated):
            row["best_nonadditive_rule"] = label
    return evaluate(shifted, params, epsilon_ratio=epsilon_ratio)


def sweep(rows: list[dict[str, str]], epsilon_ratio: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    add_neighbor_distances(rows)
    sweep_rows: list[dict[str, Any]] = []
    for min_margin in [0.001, 0.0015, 0.002, 0.003, 0.005]:
        for min_support in [4, 8, 12, 16]:
            for max_distance in [0.25, 0.75, 1.5, 3.0, 1.0e9]:
                for min_agreement in [1, 2, 3, 4]:
                    for max_risk in [0.0, 0.1, 0.25]:
                        for budget in [1, 2, 3, 99]:
                            for allow_commit in [False, True]:
                                params = {
                                    "min_predicted_margin": min_margin,
                                    "min_support_count": min_support,
                                    "max_neighbor_distance": max_distance,
                                    "min_fold_agreement": min_agreement,
                                    "max_rule_risk": max_risk,
                                    "rule_risk_caps": {
                                        "commit_heavy": 0.0 if not allow_commit else min(max_risk, 0.1),
                                    },
                                    "non_additive_budget": budget,
                                    "allow_commit_heavy": allow_commit,
                                }
                                stats = evaluate(rows, params, epsilon_ratio=epsilon_ratio)
                                out = {
                                    **params,
                                    "rule_risk_caps": json.dumps(params["rule_risk_caps"], sort_keys=True),
                                    "allow_commit_heavy": allow_commit,
                                    **stats,
                                }
                                out["passes_primary_goal"] = pass_criteria(stats)
                                sweep_rows.append(out)
    selected = max(sweep_rows, key=score_sweep) if sweep_rows else {}
    selected_params = {
        "min_predicted_margin": float(selected.get("min_predicted_margin", 0.003)),
        "min_support_count": int(selected.get("min_support_count", 12)),
        "max_neighbor_distance": float(selected.get("max_neighbor_distance", 1.0e9)),
        "min_fold_agreement": int(selected.get("min_fold_agreement", 1)),
        "max_rule_risk": float(selected.get("max_rule_risk", 0.1)),
        "rule_risk_caps": json.loads(str(selected.get("rule_risk_caps", "{}"))),
        "non_additive_budget": int(selected.get("non_additive_budget", 99)),
        "allow_commit_heavy": bool(selected.get("allow_commit_heavy", False)),
    }
    return sweep_rows, {"selected_row": selected, "selected_thresholds": selected_params}


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    selected = summary.get("selected_row", {})
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E.5 Threshold Sweep\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write(f"- sweep_rows: `{summary['sweep_rows']}`\n")
        handle.write(f"- selected_passes_primary_goal: `{selected.get('passes_primary_goal')}`\n")
        handle.write(f"- selected better/equal/worse: `{selected.get('better')}` / `{selected.get('equal')}` / `{selected.get('worse')}`\n")
        handle.write(f"- selected mean_delta_ratio_vs_ltm: `{selected.get('mean_delta_ratio_vs_ltm')}`\n\n")
        handle.write("## Selected Thresholds\n\n")
        handle.write(json.dumps(summary.get("selected_thresholds", {}), indent=2, sort_keys=True))
        handle.write("\n\n## Shuffled Diagnostic\n\n")
        handle.write(json.dumps(summary.get("shuffled_label_diagnostic", {}), indent=2, sort_keys=True))
        handle.write("\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wide-csv", type=Path, default=Path(DEFAULT_WIDE_CSV))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_SWEEP_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--epsilon-ratio", type=float, default=0.001)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    wide_csv = resolve_path(args.wide_csv, root)
    output_csv = resolve_path(args.output_csv, root)
    report = resolve_path(args.report, root)
    summary_json = resolve_path(args.summary_json, root)
    rows = read_csv(wide_csv)
    sweep_rows, selected = sweep(rows, float(args.epsilon_ratio))
    write_csv(output_csv, sweep_rows)
    shuffled = shuffled_diagnostic(rows, selected["selected_thresholds"], epsilon_ratio=float(args.epsilon_ratio))
    summary = {
        "schema_version": "phase5p5_repair5e5_threshold_sweep_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "epsilon_ratio": float(args.epsilon_ratio),
        "input_wide_csv": rel(wide_csv, root),
        "output_csv": rel(output_csv, root),
        "sweep_rows": len(sweep_rows),
        **selected,
        "shuffled_label_diagnostic": shuffled,
        "shuffled_label_matches_real": (
            shuffled.get("better") == selected["selected_row"].get("better")
            and shuffled.get("worse") == selected["selected_row"].get("worse")
            and abs(float(shuffled.get("mean_delta_ratio_vs_ltm") or 0.0) - float(selected["selected_row"].get("mean_delta_ratio_vs_ltm") or 0.0)) < 1.0e-12
        ),
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    print(json.dumps({"summary_json": rel(summary_json, root), "output_csv": rel(output_csv, root)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

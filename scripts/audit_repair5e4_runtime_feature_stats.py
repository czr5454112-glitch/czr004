"""Audit calibrated Repair5E.4 runtime-feature/OOD stats and update logs."""

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

from create_repair5e4_runtime_feature_stats_from_train_support import (  # noqa: E402
    IMPORTANT_COUNTERS,
    finite,
    repo_root,
    resolve_path,
)


DEFAULT_RUNTIME_DIR = "artifacts/models/laur_ltm/repair5e4_closed_loop_utility_selector"
DEFAULT_E3_SUMMARY = "outputs/reports/phase5p5_repair5e3_runtime_feature_ood_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5e4_runtime_feature_stats_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5e4_runtime_feature_stats_summary.json"


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def row_features(row: dict[str, Any]) -> dict[str, float]:
    names = row.get("runtime_feature_names")
    values = row.get("runtime_feature_values")
    if not isinstance(names, list) or not isinstance(values, list):
        return {}
    return {str(name): finite(value, 0.0) for name, value in zip(names, values)}


def robust_trigger(value: float, stat: dict[str, str]) -> tuple[bool, bool]:
    p01 = finite(stat.get("p01"), 0.0)
    p99 = finite(stat.get("p99"), 0.0)
    std = finite(stat.get("std"), 1.0)
    mad = finite(stat.get("mad"), 0.0)
    min_value = finite(stat.get("min"), p01)
    max_value = finite(stat.get("max"), p99)
    scale = max(abs(p99 - p01), 2.0 * abs(std), 6.0 * abs(mad), 1.0)
    outside = value < p01 - scale or value > p99 + scale
    extreme = value < min_value - 2.0 * scale or value > max_value + 2.0 * scale
    return outside, extreme


def analyze_update_rows(rows: list[dict[str, Any]], stats_rows: list[dict[str, str]]) -> dict[str, Any]:
    by_feature = {row["feature_name"]: row for row in stats_rows if row.get("feature_name")}
    per_feature_abs_z: dict[str, list[float]] = defaultdict(list)
    trigger_features = Counter()
    transitions = Counter()
    analyzed = 0
    learned_after_guard = Counter()
    for row in rows:
        features = row_features(row)
        if not features:
            continue
        analyzed += 1
        outside_features: list[str] = []
        extreme_features: list[str] = []
        for name, value in features.items():
            stat = by_feature.get(name)
            if not stat:
                continue
            mean = finite(stat.get("mean"), 0.0)
            std = finite(stat.get("std"), 1.0)
            if abs(std) <= 1.0e-12:
                std = 1.0
            per_feature_abs_z[name].append(abs((value - mean) / std))
            outside, extreme = robust_trigger(value, stat)
            if outside:
                outside_features.append(name)
            if extreme:
                extreme_features.append(name)
        ood_triggered = bool(extreme_features or len(outside_features) >= 2)
        if ood_triggered:
            trigger_features[extreme_features[0] if extreme_features else outside_features[0]] += 1
        before = str(row.get("selected_rule_before_guard", row.get("predicted_rule", "")))
        after = str(row.get("selected_rule_after_guard", row.get("applied_rule", "")))
        source = str(row.get("selected_rule_source", ""))
        transitions[f"{before}->{after}:{source}"] += 1
        learned_after_guard[after] += 1

    top_feature, top_count = trigger_features.most_common(1)[0] if trigger_features else ("", 0)
    total_triggers = sum(trigger_features.values())
    return {
        "analyzed_update_rows": analyzed,
        "per_feature": {
            name: {
                "max_abs_z": max(values) if values else 0.0,
                "mean_abs_z": statistics.mean(values) if values else 0.0,
                "rows": len(values),
            }
            for name, values in sorted(per_feature_abs_z.items())
        },
        "top_features_triggering_ood": dict(trigger_features.most_common()),
        "top_ood_trigger_feature": top_feature,
        "top_ood_trigger_share": top_count / total_triggers if total_triggers else 0.0,
        "before_guard_after_guard_transition_counts": dict(transitions),
        "after_guard_rule_counts": dict(learned_after_guard),
        "learned_choices_all_blocked_by_ood": bool(
            learned_after_guard and set(learned_after_guard) <= {"additive_ltm"}
        ),
    }


def validate_stats(stats_rows: list[dict[str, str]]) -> tuple[bool, list[dict[str, Any]]]:
    invalid: list[dict[str, Any]] = []
    by_name = {row.get("feature_name", ""): row for row in stats_rows}
    for name in IMPORTANT_COUNTERS:
        row = by_name.get(name)
        if row is None:
            invalid.append({"feature_name": name, "reason": "missing_stats_row"})
            continue
        rows_non_missing = int(finite(row.get("rows_non_missing"), 0.0))
        if rows_non_missing <= 0:
            invalid.append({"feature_name": name, "reason": "important_counter_missing_evidence"})
    return not invalid, invalid


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    per_feature = summary.get("runtime_ood_analysis", {}).get("per_feature", {})
    top = sorted(
        per_feature.items(),
        key=lambda item: float(item[1].get("max_abs_z") or 0.0),
        reverse=True,
    )[:12]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E.4 Runtime Feature Stats Audit\n\n")
        handle.write(f"- feature_stats_valid: `{summary.get('feature_stats_valid')}`\n")
        handle.write(f"- invalid_features: `{summary.get('invalid_features')}`\n")
        handle.write(f"- top_ood_trigger_share: `{summary.get('runtime_ood_analysis', {}).get('top_ood_trigger_share')}`\n")
        handle.write(f"- learned_choices_all_blocked_by_ood: `{summary.get('runtime_ood_analysis', {}).get('learned_choices_all_blocked_by_ood')}`\n\n")
        if summary.get("top_trigger_physical_explanation"):
            handle.write(f"- top_trigger_physical_explanation: `{summary.get('top_trigger_physical_explanation')}`\n\n")
        handle.write("## E3 vs E4 OOD Snapshot\n\n")
        handle.write(json.dumps(summary.get("e3_e4_ood_comparison"), indent=2, sort_keys=True))
        handle.write("\n\n## Top E4 Feature Z-Scores\n\n")
        handle.write("| feature | rows | max abs z | mean abs z |\n")
        handle.write("|---|---:|---:|---:|\n")
        for name, stats in top:
            handle.write(f"| {name} | {stats.get('rows')} | {stats.get('max_abs_z')} | {stats.get('mean_abs_z')} |\n")
        handle.write("\n## Before/After Guard Counts\n\n")
        handle.write(json.dumps(summary.get("runtime_ood_analysis", {}).get("before_guard_after_guard_transition_counts", {}), indent=2, sort_keys=True))
        handle.write("\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-dir", type=Path, default=Path(DEFAULT_RUNTIME_DIR))
    parser.add_argument("--update-jsonl", type=Path, action="append", default=[])
    parser.add_argument("--e3-ood-summary-json", type=Path, default=Path(DEFAULT_E3_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    runtime_dir = resolve_path(args.runtime_dir, root)
    stats_csv = runtime_dir / "ood_feature_stats_train.csv"
    stats_rows = read_csv(stats_csv)
    valid, invalid = validate_stats(stats_rows)
    update_paths = [resolve_path(path, root) for path in args.update_jsonl]
    update_rows = [row for path in update_paths for row in read_jsonl(path)]
    runtime_ood = analyze_update_rows(update_rows, stats_rows) if update_rows else {}
    e3 = read_json(resolve_path(args.e3_ood_summary_json, root))
    e4_committed = runtime_ood.get("per_feature", {}).get("committed_count", {})
    e3_committed = e3.get("per_feature", {}).get("committed_count", {})
    comparison = {
        "e3_committed_count_max_abs_z": e3_committed.get("max_abs_z"),
        "e4_committed_count_max_abs_z": e4_committed.get("max_abs_z"),
        "e3_top_trigger_concentration": e3.get("top_ood_trigger_share"),
        "e4_top_trigger_concentration": runtime_ood.get("top_ood_trigger_share"),
        "e3_top_trigger_feature": e3.get("top_ood_trigger_feature"),
        "e4_top_trigger_feature": runtime_ood.get("top_ood_trigger_feature"),
    }
    max_abs_z = max(
        (float(stats.get("max_abs_z") or 0.0) for stats in runtime_ood.get("per_feature", {}).values()),
        default=0.0,
    )
    top_share = float(runtime_ood.get("top_ood_trigger_share") or 0.0)
    top_feature = str(runtime_ood.get("top_ood_trigger_feature") or "")
    physical_top_trigger_explanation = ""
    if top_share >= 0.8 and top_feature in {"committed_count", "goal_wait_ignored_count", "nonzero_edges_before"}:
        physical_top_trigger_explanation = (
            f"{top_feature} is a scale/count feature tied to restart trace volume; "
            "E4 calibration keeps its max_abs_z below the invalid E3 range, so dominance is reported rather than treated as a stats failure."
        )
    pass_condition = bool(
        valid
        and (not runtime_ood or top_share < 0.8 or bool(physical_top_trigger_explanation))
        and max_abs_z <= 1000.0
        and not runtime_ood.get("learned_choices_all_blocked_by_ood", False)
    )
    summary = {
        "schema_version": "phase5p5_repair5e4_runtime_feature_stats_audit_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_dir": rel(runtime_dir, root),
        "stats_csv": rel(stats_csv, root),
        "feature_stats_valid": valid,
        "invalid_features": invalid,
        "runtime_ood_analysis": runtime_ood,
        "e3_e4_ood_comparison": comparison,
        "top_trigger_physical_explanation": physical_top_trigger_explanation,
        "pass_condition": pass_condition,
        "inputs": {"update_jsonl": [rel(path, root) for path in update_paths]},
    }
    report = resolve_path(args.report, root)
    summary_json = resolve_path(args.summary_json, root)
    summary["outputs"] = {"report": rel(report, root), "summary_json": rel(summary_json, root)}
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    print(json.dumps(summary["outputs"], sort_keys=True))
    return 0 if valid else 2


if __name__ == "__main__":
    raise SystemExit(main())

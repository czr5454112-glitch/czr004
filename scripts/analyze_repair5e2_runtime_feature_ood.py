"""Analyze true runtime-feature OOD evidence for Repair5E.2."""

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


DEFAULT_UPDATE_JSONL = "outputs/logs/phase5p5_repair5e2_runtime_feature_ood/phase5p5_repair5e2_runtime_feature_ood_laur_updates.jsonl"
DEFAULT_RUNTIME_DIR = "artifacts/models/laur_ltm/repair5d_composite_distilled"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5e2_runtime_feature_ood_report.md"
DEFAULT_SUMMARY_JSON = "outputs/reports/phase5p5_repair5e2_runtime_feature_ood_summary.json"
DEFAULT_ROWS_CSV = "outputs/tables/phase5p5_repair5e2_runtime_feature_ood_rows.csv"

REQUIRED_UPDATE_LOG_FIELDS = [
    "runtime_feature_names",
    "runtime_feature_values",
    "feature_max_abs_z",
    "feature_mean_abs_z",
    "feature_outside_3sigma_count",
    "feature_outside_5sigma_count",
    "ood_guard_triggered",
    "ood_z_threshold",
    "selected_rule_before_guard",
    "selected_rule_after_guard",
    "selected_rule_source",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(path: str | Path, root: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def finite(value: Any, default: float = math.nan) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def mean(values: list[float]) -> float | None:
    finite_values = [float(value) for value in values if math.isfinite(float(value))]
    return statistics.mean(finite_values) if finite_values else None


def stdev(values: list[float]) -> float | None:
    finite_values = [float(value) for value in values if math.isfinite(float(value))]
    return statistics.pstdev(finite_values) if len(finite_values) > 1 else None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def read_vector_csv(path: Path) -> list[float]:
    if not path.exists():
        return []
    out: list[float] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            out.extend(finite(cell, 0.0) for cell in row if str(cell).strip())
    return out


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def runtime_stats(runtime_dir: Path) -> tuple[list[str], list[float], list[float]]:
    names = [
        line.strip()
        for line in (runtime_dir / "features.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return names, read_vector_csv(runtime_dir / "mean.csv"), read_vector_csv(runtime_dir / "std.csv")


def row_features(row: dict[str, Any]) -> dict[str, float]:
    names = row.get("runtime_feature_names")
    values = row.get("runtime_feature_values")
    if not isinstance(names, list) or not isinstance(values, list):
        return {}
    return {str(name): finite(value, 0.0) for name, value in zip(names, values)}


def analyze_rows(
    update_rows: list[dict[str, Any]],
    *,
    runtime_dir: Path,
    methods: set[str] | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    feature_names, means, stds = runtime_stats(runtime_dir)
    detail_rows: list[dict[str, Any]] = []
    per_feature_abs: dict[str, list[float]] = defaultdict(list)
    per_feature_raw: dict[str, list[float]] = defaultdict(list)
    missing_fields = Counter()
    top_ood_features = Counter()
    rule_transitions = Counter()
    trigger_groups: dict[tuple[str, int, int], list[bool]] = defaultdict(list)

    for row in update_rows:
        method = str(row.get("method", ""))
        if methods is not None and method not in methods:
            continue
        for field in REQUIRED_UPDATE_LOG_FIELDS:
            if field not in row:
                missing_fields[field] += 1
        values_by_name = row_features(row)
        if not values_by_name:
            continue

        zscores: dict[str, float] = {}
        for index, name in enumerate(feature_names):
            value = values_by_name.get(name)
            if value is None:
                continue
            center = means[index] if index < len(means) else 0.0
            scale = stds[index] if index < len(stds) and abs(stds[index]) > 1.0e-12 else 1.0
            z = (value - center) / scale
            zscores[name] = z
            per_feature_abs[name].append(abs(z))
            per_feature_raw[name].append(value)
        if zscores:
            top_feature, top_z = max(zscores.items(), key=lambda item: abs(item[1]))
        else:
            top_feature, top_z = "", 0.0
        ood_triggered = bool(row.get("ood_guard_triggered"))
        if ood_triggered:
            top_ood_features[top_feature] += 1
        before = str(row.get("selected_rule_before_guard", row.get("predicted_rule", "")))
        after = str(row.get("selected_rule_after_guard", row.get("applied_rule", "")))
        rule_transitions[(before, after, str(row.get("selected_rule_source", "")))] += 1
        trigger_groups[
            (
                str(row.get("map", "")),
                int(finite(row.get("agents"), 0.0)),
                int(finite(row.get("iteration"), 0.0)),
            )
        ].append(ood_triggered)
        detail_rows.append(
            {
                "method": method,
                "map": row.get("map"),
                "agents": row.get("agents"),
                "seed": row.get("seed"),
                "scen": row.get("scen"),
                "iteration": row.get("iteration"),
                "selected_rule_before_guard": before,
                "selected_rule_after_guard": after,
                "selected_rule_source": row.get("selected_rule_source", ""),
                "ood_guard_triggered": ood_triggered,
                "ood_z_threshold": row.get("ood_z_threshold"),
                "logged_feature_max_abs_z": row.get("feature_max_abs_z"),
                "logged_feature_mean_abs_z": row.get("feature_mean_abs_z"),
                "computed_feature_max_abs_z": max((abs(value) for value in zscores.values()), default=0.0),
                "computed_feature_mean_abs_z": mean([abs(value) for value in zscores.values()]) or 0.0,
                "feature_outside_3sigma_count": sum(1 for value in zscores.values() if abs(value) > 3.0),
                "feature_outside_5sigma_count": sum(1 for value in zscores.values() if abs(value) > 5.0),
                "top_feature_by_abs_z": top_feature,
                "top_feature_abs_z": abs(top_z),
            }
        )

    per_feature = {
        name: {
            "max_abs_z": max(values) if values else None,
            "mean_abs_z": mean(values),
            "raw_mean": mean(per_feature_raw.get(name, [])),
            "raw_std": stdev(per_feature_raw.get(name, [])),
            "rows": len(values),
        }
        for name, values in sorted(per_feature_abs.items())
    }
    trigger_rate_by_group = [
        {
            "map": key[0],
            "agents": key[1],
            "iteration": key[2],
            "rows": len(values),
            "ood_trigger_rate": sum(1 for value in values if value) / len(values) if values else 0.0,
        }
        for key, values in sorted(trigger_groups.items())
    ]
    total_ood = sum(top_ood_features.values())
    entropy_ood = top_ood_features.get("entropy_edge_usage", 0)
    summary = {
        "schema_version": "phase5p5_repair5e2_runtime_feature_ood_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_dir": str(runtime_dir),
        "methods": sorted(methods) if methods is not None else "all",
        "update_rows": len(update_rows),
        "analyzed_rows": len(detail_rows),
        "rows_with_full_runtime_features": sum(1 for row in detail_rows if row["computed_feature_max_abs_z"] is not None),
        "missing_required_field_counts": dict(sorted(missing_fields.items())),
        "per_feature": per_feature,
        "top_features_triggering_ood": dict(top_ood_features.most_common()),
        "entropy_edge_usage_ood_trigger_share": entropy_ood / total_ood if total_ood else 0.0,
        "one_feature_dominates_ood": (entropy_ood / total_ood >= 0.8) if total_ood else False,
        "rule_before_after_source_counts": {
            f"{before}->{after}:{source}": count
            for (before, after, source), count in sorted(rule_transitions.items())
        },
        "ood_trigger_rate_by_map_agents_iteration": trigger_rate_by_group,
        "notes": [
            "Feature z-scores are recomputed from runtime_feature_names/runtime_feature_values and the runtime model stats.",
            "If one feature dominates OOD triggers, Repair5E.2 must avoid treating that feature as a universal veto.",
        ],
    }
    return summary, detail_rows


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    per_feature = summary.get("per_feature", {})
    top_features = sorted(
        per_feature.items(),
        key=lambda item: float(item[1].get("max_abs_z") or 0.0),
        reverse=True,
    )[:12]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E.2 Runtime Feature OOD Report\n\n")
        handle.write("- diagnostic-only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n\n")
        handle.write(f"- analyzed rows: `{summary.get('analyzed_rows')}`\n")
        handle.write(f"- rows with full runtime features: `{summary.get('rows_with_full_runtime_features')}`\n")
        handle.write(f"- missing required fields: `{summary.get('missing_required_field_counts')}`\n")
        handle.write(f"- top OOD trigger features: `{summary.get('top_features_triggering_ood')}`\n")
        handle.write(f"- entropy_edge_usage OOD trigger share: `{summary.get('entropy_edge_usage_ood_trigger_share')}`\n")
        handle.write(f"- one feature dominates OOD: `{summary.get('one_feature_dominates_ood')}`\n\n")
        handle.write("## Top Feature Z-Scores\n\n")
        handle.write("| feature | rows | max abs z | mean abs z | raw mean | raw std |\n")
        handle.write("|---|---:|---:|---:|---:|---:|\n")
        for name, stats in top_features:
            handle.write(
                f"| {name} | {stats.get('rows')} | {stats.get('max_abs_z')} | "
                f"{stats.get('mean_abs_z')} | {stats.get('raw_mean')} | {stats.get('raw_std')} |\n"
            )
        handle.write("\n## Rule Before/After Guard\n\n")
        handle.write(json.dumps(summary.get("rule_before_after_source_counts"), indent=2, sort_keys=True))
        handle.write("\n\n## OOD Trigger Rate By Map/Agents/Iteration\n\n")
        handle.write("| map | agents | iteration | rows | trigger rate |\n")
        handle.write("|---|---:|---:|---:|---:|\n")
        for row in summary.get("ood_trigger_rate_by_map_agents_iteration", []):
            handle.write(
                f"| {row['map']} | {row['agents']} | {row['iteration']} | "
                f"{row['rows']} | {row['ood_trigger_rate']} |\n"
            )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-jsonl", type=Path, default=Path(DEFAULT_UPDATE_JSONL))
    parser.add_argument("--runtime-dir", type=Path, default=Path(DEFAULT_RUNTIME_DIR))
    parser.add_argument("--method", action="append", help="Filter to one or more method aliases.")
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--rows-csv", type=Path, default=Path(DEFAULT_ROWS_CSV))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    update_jsonl = resolve_path(args.update_jsonl, root)
    runtime_dir = resolve_path(args.runtime_dir, root)
    report = resolve_path(args.report, root)
    summary_json = resolve_path(args.summary_json, root)
    rows_csv = resolve_path(args.rows_csv, root)
    methods = set(args.method) if args.method else None
    summary, rows = analyze_rows(read_jsonl(update_jsonl), runtime_dir=runtime_dir, methods=methods)
    summary["inputs"] = {
        "update_jsonl": str(update_jsonl),
        "runtime_dir": str(runtime_dir),
    }
    summary["outputs"] = {
        "report": str(report),
        "summary_json": str(summary_json),
        "rows_csv": str(rows_csv),
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    write_csv(
        rows_csv,
        rows,
        [
            "method",
            "map",
            "agents",
            "seed",
            "scen",
            "iteration",
            "selected_rule_before_guard",
            "selected_rule_after_guard",
            "selected_rule_source",
            "ood_guard_triggered",
            "ood_z_threshold",
            "logged_feature_max_abs_z",
            "logged_feature_mean_abs_z",
            "computed_feature_max_abs_z",
            "computed_feature_mean_abs_z",
            "feature_outside_3sigma_count",
            "feature_outside_5sigma_count",
            "top_feature_by_abs_z",
            "top_feature_abs_z",
        ],
    )
    print(json.dumps(summary["outputs"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

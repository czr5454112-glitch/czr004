"""Create calibrated Repair5E.4 runtime-feature/OOD stats from train support."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5e4_train_support"
DEFAULT_SOURCE_RUNTIME = "artifacts/models/laur_ltm/repair5d_composite_distilled"
DEFAULT_OUTPUT_RUNTIME = "artifacts/models/laur_ltm/repair5e4_closed_loop_utility_selector"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5e4_runtime_feature_stats_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5e4_runtime_feature_stats_summary.json"

IMPORTANT_COUNTERS = [
    "committed_count",
    "blocked_count",
    "wait_event_count",
    "goal_wait_ignored_count",
    "blocked_per_committed",
    "wait_per_committed",
    "blocked_per_agent",
    "committed_per_agent",
    "nonzero_edges_before",
    "max_raw_before",
    "entropy_edge_usage",
    "weight_entropy",
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


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite(value: Any, default: float = math.nan) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def discover_update_paths(log_dir: Path) -> list[Path]:
    if not log_dir.exists():
        return []
    return sorted(path for path in log_dir.glob("*_laur_updates.jsonl") if path.is_file())


def read_feature_names(runtime_dir: Path) -> list[str]:
    path = runtime_dir / "features.txt"
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def row_features(row: dict[str, Any]) -> dict[str, float]:
    names = row.get("runtime_feature_names")
    values = row.get("runtime_feature_values")
    if not isinstance(names, list) or not isinstance(values, list):
        return {}
    return {
        str(name): finite(value, 0.0)
        for name, value in zip(names, values)
        if math.isfinite(finite(value))
    }


def quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[int(pos)]
    weight = pos - lo
    return ordered[lo] * (1.0 - weight) + ordered[hi] * weight


def collect_stats(rows: list[dict[str, Any]], feature_names: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    values_by_feature: dict[str, list[float]] = defaultdict(list)
    rows_with_features = 0
    for row in rows:
        features = row_features(row)
        if not features:
            continue
        rows_with_features += 1
        for name in feature_names:
            value = features.get(name)
            if value is not None and math.isfinite(value):
                values_by_feature[name].append(value)

    invalid_features: list[dict[str, Any]] = []
    stats_rows: list[dict[str, Any]] = []
    for name in feature_names:
        values = values_by_feature.get(name, [])
        rows_non_missing = len(values)
        if values:
            mean = statistics.mean(values)
            std = statistics.pstdev(values) if len(values) > 1 else 0.0
            median = quantile(values, 0.5)
            mad = statistics.median([abs(value - median) for value in values]) if values else 0.0
            observed_constant = max(values) - min(values) <= 1.0e-12
            std_was_floored = abs(std) <= 1.0e-12
            if std_was_floored:
                std = 1.0
            row = {
                "feature_name": name,
                "mean": mean,
                "std": std,
                "median": median,
                "mad": mad,
                "p01": quantile(values, 0.01),
                "p05": quantile(values, 0.05),
                "p95": quantile(values, 0.95),
                "p99": quantile(values, 0.99),
                "min": min(values),
                "max": max(values),
                "rows_non_missing": rows_non_missing,
                "rows_nonzero": sum(1 for value in values if abs(value) > 1.0e-12),
                "required": True,
                "observed_constant": observed_constant,
                "std_was_floored": std_was_floored,
                "std_floor_reason": "constant_observed" if std_was_floored else "",
            }
        else:
            row = {
                "feature_name": name,
                "mean": 0.0,
                "std": 1.0,
                "median": 0.0,
                "mad": 0.0,
                "p01": 0.0,
                "p05": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "min": 0.0,
                "max": 0.0,
                "rows_non_missing": 0,
                "rows_nonzero": 0,
                "required": True,
                "observed_constant": False,
                "std_was_floored": True,
                "std_floor_reason": "missing_evidence_invalid",
            }
        if name in IMPORTANT_COUNTERS and int(row["rows_non_missing"]) == 0:
            invalid_features.append({"feature_name": name, "reason": "important_counter_missing_evidence"})
        stats_rows.append(row)

    summary = {
        "rows_total": len(rows),
        "rows_with_runtime_features": rows_with_features,
        "feature_count": len(feature_names),
        "invalid_features": invalid_features,
        "feature_stats_valid": not invalid_features and rows_with_features > 0,
        "important_counter_rows": {
            name: next((row["rows_non_missing"] for row in stats_rows if row["feature_name"] == name), 0)
            for name in IMPORTANT_COUNTERS
        },
    }
    return stats_rows, summary


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, summary: dict[str, Any], stats_rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    important = [row for row in stats_rows if row["feature_name"] in IMPORTANT_COUNTERS]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E.4 Runtime Feature Stats\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write(f"- feature_stats_valid: `{summary['feature_stats_valid']}`\n")
        handle.write(f"- rows_with_runtime_features: `{summary['rows_with_runtime_features']}`\n")
        handle.write(f"- invalid_features: `{summary['invalid_features']}`\n\n")
        handle.write("## Important Runtime Counters\n\n")
        handle.write("| feature | rows | mean | std | p01 | p99 | min | max | nonzero |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in important:
            handle.write(
                f"| {row['feature_name']} | {row['rows_non_missing']} | {row['mean']} | {row['std']} | "
                f"{row['p01']} | {row['p99']} | {row['min']} | {row['max']} | {row['rows_nonzero']} |\n"
            )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-dir", type=Path, default=Path(DEFAULT_LOG_DIR))
    parser.add_argument("--train-update-jsonl", type=Path, action="append", default=[])
    parser.add_argument("--source-runtime-dir", type=Path, default=Path(DEFAULT_SOURCE_RUNTIME))
    parser.add_argument("--output-runtime-dir", type=Path, default=Path(DEFAULT_OUTPUT_RUNTIME))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    log_dir = resolve_path(args.log_dir, root)
    source_runtime = resolve_path(args.source_runtime_dir, root)
    output_runtime = resolve_path(args.output_runtime_dir, root)
    report = resolve_path(args.report, root)
    summary_json = resolve_path(args.summary_json, root)
    update_paths = [resolve_path(path, root) for path in args.train_update_jsonl] or discover_update_paths(log_dir)
    rows = [row for path in update_paths for row in read_jsonl(path)]
    feature_names = read_feature_names(source_runtime)
    stats_rows, summary = collect_stats(rows, feature_names)

    fields = [
        "feature_name",
        "mean",
        "std",
        "median",
        "mad",
        "p01",
        "p05",
        "p95",
        "p99",
        "min",
        "max",
        "rows_non_missing",
        "rows_nonzero",
        "required",
        "observed_constant",
        "std_was_floored",
        "std_floor_reason",
    ]
    output_runtime.mkdir(parents=True, exist_ok=True)
    stats_csv = output_runtime / "ood_feature_stats_train.csv"
    override_csv = output_runtime / "ood_feature_stats_override.csv"
    write_csv(stats_csv, stats_rows, fields)
    write_csv(override_csv, stats_rows, ["feature_name", "mean", "std"])
    feature_stats_json = output_runtime / "laur_mlp_v1_feature_stats.json"
    feature_stats_json.write_text(
        json.dumps(
            {
                "schema_version": "phase5p5_repair5e4_runtime_feature_stats_v1",
                "created_at": datetime.now().isoformat(),
                "diagnostic_only": True,
                "phase5p5_allowed": False,
                "phase6_allowed": False,
                "stat_source": "repair5e4_train_support_update_logs",
                "feature_stats_valid": summary["feature_stats_valid"],
                "features": stats_rows,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    summary.update(
        {
            "schema_version": "phase5p5_repair5e4_runtime_feature_stats_v1",
            "created_at": datetime.now().isoformat(),
            "diagnostic_only": True,
            "phase5p5_allowed": False,
            "phase6_allowed": False,
            "inputs": {
                "train_update_jsonl": [rel(path, root) for path in update_paths],
                "source_runtime_dir": rel(source_runtime, root),
            },
            "outputs": {
                "runtime_dir": rel(output_runtime, root),
                "ood_feature_stats_train_csv": rel(stats_csv, root),
                "ood_feature_stats_override_csv": rel(override_csv, root),
                "feature_stats_json": rel(feature_stats_json, root),
                "report": rel(report, root),
                "summary_json": rel(summary_json, root),
            },
            "file_hashes": {
                "train_update_jsonl": {rel(path, root): sha256_file(path) for path in update_paths},
                "ood_feature_stats_train_csv": sha256_file(stats_csv),
                "ood_feature_stats_override_csv": sha256_file(override_csv),
            },
            "guard_logic": {
                "missing_required_feature": "defer_to_additive",
                "invalid_feature_stats": "artifact_creation_fails",
                "robust_ood_rule": "multiple calibrated features outside robust thresholds, or one feature beyond extreme bounds",
            },
        }
    )
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary, stats_rows)
    print(json.dumps(summary["outputs"], sort_keys=True))
    return 0 if summary["feature_stats_valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

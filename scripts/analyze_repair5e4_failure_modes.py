"""Autopsy Repair5E.4 false positives and missed oracle/static headroom."""

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


DEFAULT_PAIRED_CSV = "outputs/tables/phase5p5_repair5e4_preflight_paired.csv"
DEFAULT_UPDATE_JSONL = "outputs/logs/phase5p5_repair5e4_preflight/phase5p5_repair5e4_preflight_laur_updates.jsonl"
DEFAULT_UTILITY_CSV = "outputs/tables/phase5p5_repair5e4_closed_loop_rule_utility_train.csv"
DEFAULT_ABLATION_JSON = "outputs/reports/phase5p5_repair5e4_ablation_summary.json"
DEFAULT_SELECTOR_CSV = "artifacts/models/laur_ltm/repair5e4_closed_loop_utility_selector/repair5e4_utility_selector.csv"
DEFAULT_RUNTIME_DIR = "artifacts/models/laur_ltm/repair5e4_closed_loop_utility_selector"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5e5_e4_failure_autopsy_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5e5_e4_failure_autopsy_summary.json"
DEFAULT_FALSE_POSITIVE_CSV = "outputs/tables/phase5p5_repair5e5_false_positive_contexts.csv"
DEFAULT_FALSE_NEGATIVE_CSV = "outputs/tables/phase5p5_repair5e5_false_negative_oracle_contexts.csv"

E4 = "repair5e4_closed_loop_utility_selector"
ORACLE = "oracle_teacher_forced_best_safe_update_static_proxy"
NONADDITIVE_RULES = {
    "block_heavy",
    "block_light",
    "commit_heavy",
    "decay_090",
    "decay_095",
    "wait_heavy",
    "wait_light",
}


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
    clean = [value for value in values if math.isfinite(value)]
    return statistics.mean(clean) if clean else None


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def scenario_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (
        str(row.get("map", "")),
        int(finite(row.get("agents"), 0.0)),
        int(finite(row.get("seed", row.get("instance_id")), 0.0)),
        str(row.get("scen", "")),
    )


def paired_by_method(rows: list[dict[str, str]]) -> dict[str, dict[tuple[str, int, int, str], dict[str, str]]]:
    out: dict[str, dict[tuple[str, int, int, str], dict[str, str]]] = defaultdict(dict)
    for row in rows:
        out[str(row.get("contender_method", ""))][scenario_key(row)] = row
    return out


def runtime_feature_vector(row: dict[str, Any], feature_names: list[str]) -> list[float]:
    names = [str(name) for name in row.get("runtime_feature_names", [])]
    values = [finite(value, 0.0) for value in row.get("runtime_feature_values", [])]
    by_name = {name: value for name, value in zip(names, values)}
    return [by_name.get(name, 0.0) for name in feature_names]


def read_feature_stats(runtime_dir: Path) -> tuple[list[str], list[float]]:
    names_path = runtime_dir / "features.txt"
    std_path = runtime_dir / "std.csv"
    names = [line.strip() for line in names_path.read_text(encoding="utf-8").splitlines() if line.strip()] if names_path.exists() else []
    std = []
    if std_path.exists():
        text = std_path.read_text(encoding="utf-8").strip()
        std = [finite(value, 1.0) for value in text.replace("\n", ",").split(",") if value.strip()]
    if len(std) < len(names):
        std.extend([1.0] * (len(names) - len(std)))
    return names, std


def selector_neighbors(selector_csv: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv(selector_csv):
        rows.append(
            {
                "rule_id": row.get("rule_id", ""),
                "feature_values": [finite(value, 0.0) for value in row.get("feature_values", "").split(";") if value != ""],
            }
        )
    return rows


def nearest_distance(values: list[float], std: list[float], neighbors: list[dict[str, Any]]) -> float | None:
    best = math.inf
    for neighbor in neighbors:
        other = neighbor["feature_values"]
        used = min(len(values), len(other))
        if used <= 0:
            continue
        total = 0.0
        for index in range(used):
            scale = std[index] if index < len(std) and abs(std[index]) > 1.0e-12 else 1.0
            total += ((values[index] - other[index]) / scale) ** 2
        best = min(best, math.sqrt(total / used))
    return best if math.isfinite(best) else None


def analyze(
    *,
    paired_rows: list[dict[str, str]],
    update_rows: list[dict[str, Any]],
    utility_rows: list[dict[str, str]],
    ablation_summary: dict[str, Any],
    selector_csv: Path,
    runtime_dir: Path,
    epsilon_ratio: float,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    paired = paired_by_method(paired_rows)
    e4_pairs = paired.get(E4, {})
    oracle_pairs = paired.get(ORACLE, {})
    e4_updates = [row for row in update_rows if str(row.get("method", "")) == E4]
    by_case_updates: dict[tuple[str, int, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in e4_updates:
        by_case_updates[scenario_key(row)].append(row)

    feature_names, feature_std = read_feature_stats(runtime_dir)
    neighbors = selector_neighbors(selector_csv)
    selected_rule_distribution: Counter[tuple[str, int, int, str]] = Counter()
    selected_by_case: dict[tuple[str, int, int, str], Counter[str]] = defaultdict(Counter)
    context_diagnostics: dict[tuple[str, int, int, str], dict[str, Any]] = {}
    for key, rows in by_case_updates.items():
        margins = [finite(row.get("predicted_margin_ratio"), 0.0) for row in rows]
        supports = [finite(row.get("nearest_support_count"), 0.0) for row in rows]
        distances = []
        for row in rows:
            applied = str(row.get("applied_rule", ""))
            if applied in NONADDITIVE_RULES:
                selected_rule_distribution[(key[0], key[1], int(finite(row.get("iteration"), 0.0)), applied)] += 1
                selected_by_case[key][applied] += 1
            if feature_names and neighbors:
                distance = nearest_distance(runtime_feature_vector(row, feature_names), feature_std, neighbors)
                if distance is not None:
                    distances.append(distance)
        context_diagnostics[key] = {
            "max_predicted_margin": max(margins) if margins else 0.0,
            "mean_predicted_margin": mean(margins) or 0.0,
            "max_support_count": max(supports) if supports else 0.0,
            "mean_support_count": mean(supports) or 0.0,
            "min_neighbor_distance": min(distances) if distances else None,
            "nonadditive_selected_rules": dict(selected_by_case[key]),
            "nonadditive_update_count": sum(selected_by_case[key].values()),
        }

    false_positive_rows: list[dict[str, Any]] = []
    false_negative_rows: list[dict[str, Any]] = []
    for key, pair in sorted(e4_pairs.items()):
        delta = finite(pair.get("delta_ratio"), 0.0)
        diag = context_diagnostics.get(key, {})
        selected_rules = diag.get("nonadditive_selected_rules", {})
        if delta > epsilon_ratio and selected_rules:
            false_positive_rows.append(
                {
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "scen": key[3],
                    "realized_delta_ratio": delta,
                    "selected_rules": json.dumps(selected_rules, sort_keys=True),
                    **diag,
                }
            )
    for key, pair in sorted(oracle_pairs.items()):
        oracle_delta = finite(pair.get("delta_ratio"), 0.0)
        e4_delta = finite(e4_pairs.get(key, {}).get("delta_ratio"), 0.0)
        diag = context_diagnostics.get(key, {})
        if oracle_delta < -epsilon_ratio and int(diag.get("nonadditive_update_count") or 0) == 0:
            false_negative_rows.append(
                {
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "scen": key[3],
                    "oracle_delta_ratio": oracle_delta,
                    "e4_delta_ratio": e4_delta,
                    **diag,
                }
            )

    realized_by_case = {key: finite(row.get("delta_ratio"), 0.0) for key, row in e4_pairs.items()}
    margin_pairs = []
    support_pairs = []
    distance_pairs = []
    for key, diag in context_diagnostics.items():
        if key not in realized_by_case:
            continue
        realized = realized_by_case[key]
        margin_pairs.append((float(diag.get("max_predicted_margin") or 0.0), realized))
        support_pairs.append((float(diag.get("max_support_count") or 0.0), realized))
        distance = diag.get("min_neighbor_distance")
        if distance is not None:
            distance_pairs.append((float(distance), realized))

    rule_precision: dict[str, Any] = {}
    for rule in ["block_heavy", "decay_090"]:
        selected_cases = [key for key, counts in selected_by_case.items() if counts.get(rule, 0) > 0]
        better = sum(1 for key in selected_cases if realized_by_case.get(key, 0.0) < -epsilon_ratio)
        worse = sum(1 for key in selected_cases if realized_by_case.get(key, 0.0) > epsilon_ratio)
        support_positives = sum(1 for row in utility_rows if row.get("label_rule") == rule)
        rule_precision[rule] = {
            "selected_cases": len(selected_cases),
            "selected_better_cases": better,
            "selected_worse_cases": worse,
            "precision_better": better / len(selected_cases) if selected_cases else None,
            "train_positive_contexts": support_positives,
        }

    random_100_false_positive_rows = [
        row for row in false_positive_rows if row["map"] == "random-32-32-20" and int(row["agents"]) == 100
    ]
    maze_warehouse_false_negative_rows = [
        row for row in false_negative_rows if row["map"] in {"maze-32-32-4", "warehouse-10-20-10-2-1"}
    ]
    ablation_stats = ablation_summary.get("paired_method_stats", {}) if ablation_summary else {}
    summary = {
        "schema_version": "phase5p5_repair5e5_e4_failure_autopsy_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "e4_cases": len(e4_pairs),
        "e4_update_rows": len(e4_updates),
        "false_positive_contexts": len(false_positive_rows),
        "false_negative_oracle_contexts": len(false_negative_rows),
        "selected_rule_distribution_by_map_agents_iteration": {
            f"{key[0]}:{key[1]}:iter_{key[2]}:{key[3]}": value
            for key, value in sorted(selected_rule_distribution.items())
        },
        "predicted_margin_vs_realized_delta": bucket_pairs(margin_pairs),
        "support_count_vs_realized_delta": bucket_pairs(support_pairs),
        "neighbor_distance_vs_realized_delta": bucket_pairs(distance_pairs),
        "rule_precision_recall_proxy": rule_precision,
        "random_32_32_20_agents100_false_positive_contexts": len(random_100_false_positive_rows),
        "random_32_32_20_agents100_is_main_false_positive_source": len(random_100_false_positive_rows)
        >= max(1, len(false_positive_rows) // 2),
        "maze_warehouse_false_negative_contexts": len(maze_warehouse_false_negative_rows),
        "maze_warehouse_false_negative_source_due_to_no_positive_train_support": bool(
            maze_warehouse_false_negative_rows
            and not any(row.get("map") in {"maze-32-32-4", "warehouse-10-20-10-2-1"} and row.get("label_rule") != "additive_ltm" for row in utility_rows)
        ),
        "ablation_repair5e4": ablation_stats.get(E4, {}),
        "ablation_shuffled": ablation_stats.get("repair5e4_closed_loop_utility_selector_shuffled_labels_diagnostic", {}),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    return summary, false_positive_rows, false_negative_rows


def bucket_pairs(pairs: list[tuple[float, float]]) -> dict[str, Any]:
    if not pairs:
        return {"rows": 0}
    ordered = sorted(pairs, key=lambda item: item[0])
    buckets: dict[str, list[float]] = defaultdict(list)
    for x_value, y_value in ordered:
        if x_value <= 0.0:
            bucket = "0"
        elif x_value <= 0.001:
            bucket = "(0,0.001]"
        elif x_value <= 0.002:
            bucket = "(0.001,0.002]"
        elif x_value <= 0.005:
            bucket = "(0.002,0.005]"
        else:
            bucket = ">0.005"
        buckets[bucket].append(y_value)
    return {
        "rows": len(pairs),
        "buckets": {
            key: {
                "rows": len(values),
                "mean_realized_delta_ratio": mean(values),
                "worse": sum(1 for value in values if value > 0.001),
                "better": sum(1 for value in values if value < -0.001),
            }
            for key, values in sorted(buckets.items())
        },
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E.5 E4 Failure Autopsy\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write(f"- e4_cases: `{summary['e4_cases']}`\n")
        handle.write(f"- false_positive_contexts: `{summary['false_positive_contexts']}`\n")
        handle.write(f"- false_negative_oracle_contexts: `{summary['false_negative_oracle_contexts']}`\n")
        handle.write(f"- random-32-32-20:100 main false-positive source: `{summary['random_32_32_20_agents100_is_main_false_positive_source']}`\n")
        handle.write(f"- maze/warehouse false-negative contexts: `{summary['maze_warehouse_false_negative_contexts']}`\n\n")
        handle.write("## Rule Precision/Recall Proxy\n\n")
        handle.write(json.dumps(summary["rule_precision_recall_proxy"], indent=2, sort_keys=True))
        handle.write("\n\n## Margin Vs Realized Delta\n\n")
        handle.write(json.dumps(summary["predicted_margin_vs_realized_delta"], indent=2, sort_keys=True))
        handle.write("\n\n## Support Count Vs Realized Delta\n\n")
        handle.write(json.dumps(summary["support_count_vs_realized_delta"], indent=2, sort_keys=True))
        handle.write("\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED_CSV))
    parser.add_argument("--update-jsonl", type=Path, default=Path(DEFAULT_UPDATE_JSONL))
    parser.add_argument("--utility-csv", type=Path, default=Path(DEFAULT_UTILITY_CSV))
    parser.add_argument("--ablation-summary-json", type=Path, default=Path(DEFAULT_ABLATION_JSON))
    parser.add_argument("--selector-csv", type=Path, default=Path(DEFAULT_SELECTOR_CSV))
    parser.add_argument("--runtime-dir", type=Path, default=Path(DEFAULT_RUNTIME_DIR))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--false-positive-csv", type=Path, default=Path(DEFAULT_FALSE_POSITIVE_CSV))
    parser.add_argument("--false-negative-csv", type=Path, default=Path(DEFAULT_FALSE_NEGATIVE_CSV))
    parser.add_argument("--epsilon-ratio", type=float, default=0.001)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    paired_csv = resolve_path(args.paired_csv, root)
    update_jsonl = resolve_path(args.update_jsonl, root)
    utility_csv = resolve_path(args.utility_csv, root)
    ablation_summary_json = resolve_path(args.ablation_summary_json, root)
    selector_csv = resolve_path(args.selector_csv, root)
    runtime_dir = resolve_path(args.runtime_dir, root)
    report = resolve_path(args.report, root)
    summary_json = resolve_path(args.summary_json, root)
    false_positive_csv = resolve_path(args.false_positive_csv, root)
    false_negative_csv = resolve_path(args.false_negative_csv, root)
    summary, false_positives, false_negatives = analyze(
        paired_rows=read_csv(paired_csv),
        update_rows=read_jsonl(update_jsonl),
        utility_rows=read_csv(utility_csv),
        ablation_summary=read_json(ablation_summary_json),
        selector_csv=selector_csv,
        runtime_dir=runtime_dir,
        epsilon_ratio=float(args.epsilon_ratio),
    )
    write_csv(false_positive_csv, false_positives)
    write_csv(false_negative_csv, false_negatives)
    summary.update(
        {
            "inputs": {
                "paired_csv": str(paired_csv),
                "update_jsonl": str(update_jsonl),
                "utility_csv": str(utility_csv),
                "ablation_summary_json": str(ablation_summary_json),
                "selector_csv": str(selector_csv),
            },
            "outputs": {
                "false_positive_csv": str(false_positive_csv),
                "false_negative_csv": str(false_negative_csv),
            },
        }
    )
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    print(json.dumps({"summary_json": str(summary_json), "report": str(report)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

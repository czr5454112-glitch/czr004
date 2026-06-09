"""Analyze Repair5E Case-B composite/reranker transfer failure.

This script is diagnostic-only. It compares the pushed Repair5E closed-loop
preflight rows, quantifies the Repair5D distill bridge rule collapse, and
adds a proxy OOD analysis against the distill runtime feature statistics.
It never changes solver semantics and never grants Phase5.5 or Phase6.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "src"))


DEFAULT_RAW_JSONL = "outputs/logs/phase5p5_repair5e_preflight/phase5p5_repair5e_preflight.jsonl"
DEFAULT_UPDATE_JSONL = "outputs/logs/phase5p5_repair5e_preflight/phase5p5_repair5e_preflight_laur_updates.jsonl"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5e_preflight_summary.csv"
DEFAULT_PAIRED_CSV = "outputs/tables/phase5p5_repair5e_preflight_paired.csv"
DEFAULT_DISTILL_DECISIONS_CSV = "outputs/tables/phase5p5_repair5d_composite_distill_decisions.csv"
DEFAULT_DISTILL_SUMMARY_JSON = "outputs/reports/phase5p5_repair5d_composite_distill_summary.json"
DEFAULT_DISTILL_RUNTIME_DIR = "artifacts/models/laur_ltm/repair5d_composite_distilled"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5e_caseb_transfer_analysis.md"
DEFAULT_SUMMARY_JSON = "outputs/reports/phase5p5_repair5e_caseb_transfer_analysis.json"
DEFAULT_ALIGNMENT_CSV = "outputs/tables/phase5p5_repair5e_caseb_decision_alignment.csv"
DEFAULT_RULE_OUTCOMES_CSV = "outputs/tables/phase5p5_repair5e_caseb_rule_outcomes.csv"

MAP_PATHS = {
    "random-32-32-20": "external/lacam2/scripts/map/random-32-32-20.map",
    "maze-32-32-4": "external/lacam2/scripts/map/maze-32-32-4.map",
    "warehouse-10-20-10-2-1": "external/lacam2/scripts/map/warehouse-10-20-10-2-1.map",
}

REPAIR5D = "repair5d_composite_diagnostic_distilled"
REPAIR3 = "repair3_safe_runtime"
LTM = "lacam_star_ltm"
ORACLE = "oracle_teacher_forced_best_safe_update_static_proxy"
EPS = 1.0e-12


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(path: str | Path | None, root: Path) -> Path | None:
    if path is None:
        return None
    value = Path(path)
    return value if value.is_absolute() else root / value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def finite(value: Any, default: float = 0.0) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def optional_float(value: Any) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def mean(values: list[float]) -> float | None:
    finite_values = [float(value) for value in values if math.isfinite(float(value))]
    return statistics.mean(finite_values) if finite_values else None


def safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def key_for(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (
        str(row.get("map", "")),
        int(finite(row.get("agents"), 0.0)),
        int(finite(row.get("seed"), 0.0)),
        str(row.get("scen", "")),
    )


def group_key_for(row: dict[str, Any]) -> tuple[str, int]:
    return (str(row.get("map", "")), int(finite(row.get("agents"), 0.0)))


def parse_rules(value: Any) -> dict[str, int]:
    if isinstance(value, dict):
        return {str(k): int(v) for k, v in value.items()}
    if not value:
        return {}
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(k): int(v) for k, v in payload.items()}


def read_vector_csv(path: Path) -> list[float]:
    if not path.exists():
        return []
    out: list[float] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle):
            out.extend(finite(cell) for cell in row if str(cell).strip())
    return out


def distribution_from_summary(summary_rows: list[dict[str, Any]], method: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in summary_rows:
        if str(row.get("method")) != method:
            continue
        counts.update(parse_rules(row.get("selected_rules")))
    return dict(sorted(counts.items()))


def normalize_distribution(counts: dict[str, int], keys: list[str]) -> list[float]:
    total = sum(max(0, int(counts.get(key, 0))) for key in keys)
    if total <= 0:
        return [0.0 for _ in keys]
    return [max(0, int(counts.get(key, 0))) / total for key in keys]


def kl_divergence(p: list[float], q: list[float]) -> float:
    out = 0.0
    for left, right in zip(p, q):
        if left <= 0.0:
            continue
        out += left * math.log(left / max(right, 1.0e-12))
    return out


def js_divergence(left: dict[str, int], right: dict[str, int]) -> float:
    keys = sorted(set(left) | set(right))
    if not keys:
        return 0.0
    p = normalize_distribution(left, keys)
    q = normalize_distribution(right, keys)
    midpoint = [(a + b) / 2.0 for a, b in zip(p, q)]
    return 0.5 * kl_divergence(p, midpoint) + 0.5 * kl_divergence(q, midpoint)


def pearson(xs: list[float], ys: list[float]) -> float | None:
    pairs = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 2:
        return None
    x_values = [x for x, _ in pairs]
    y_values = [y for _, y in pairs]
    mean_x = statistics.mean(x_values)
    mean_y = statistics.mean(y_values)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in x_values))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in y_values))
    if denom_x <= EPS or denom_y <= EPS:
        return None
    return numerator / (denom_x * denom_y)


def map_stats(root: Path, map_name: str) -> dict[str, float]:
    path = resolve_path(MAP_PATHS.get(map_name), root)
    if path is None or not path.exists():
        return {}
    width = 0
    height = 0
    grid: list[str] = []
    in_map = False
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("height"):
                height = int(line.split()[1])
            elif line.startswith("width"):
                width = int(line.split()[1])
            elif line == "map":
                in_map = True
            elif in_map:
                grid.append(line)
    free_cells = sum(1 for line in grid for char in line if char != "@")
    total_cells = max(1, width * height)
    return {
        "map_width": float(width),
        "map_height": float(height),
        "free_cells": float(free_cells),
        "obstacle_ratio": (total_cells - free_cells) / total_cells,
    }


def synthesize_oracle_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if str(row.get("method", "")).startswith("oracle_probe_static_"):
            grouped[key_for(row)].append(row)

    def score(row: dict[str, Any]) -> tuple[int, float, float, float]:
        success_rank = 0 if bool(row.get("success")) else 1
        ratio = optional_float(row.get("sum_of_loss_ratio"))
        expanded = optional_float(row.get("expanded_nodes"))
        ttfs = optional_float(row.get("time_to_first_solution_ms"))
        return (
            success_rank,
            ratio if ratio is not None else float("inf"),
            expanded if expanded is not None else float("inf"),
            ttfs if ttfs is not None else float("inf"),
        )

    out: list[dict[str, Any]] = []
    for candidates in grouped.values():
        best = min(candidates, key=score)
        row = dict(best)
        source = str(row.get("method", ""))
        row["method"] = ORACLE
        row["oracle_proxy_source_method"] = source
        row["oracle_proxy_source_rule"] = source.replace("oracle_probe_static_", "")
        out.append(row)
    return out


def build_alignment_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    report_rows = [row for row in rows if not str(row.get("method", "")).startswith("oracle_probe_static_")]
    report_rows.extend(synthesize_oracle_rows(rows))
    by_key: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in report_rows:
        by_key[key_for(row)][str(row.get("method"))] = row

    out: list[dict[str, Any]] = []
    for key, methods in sorted(by_key.items()):
        ltm = methods.get(LTM)
        if not ltm:
            continue
        base_ratio = optional_float(ltm.get("sum_of_loss_ratio"))
        base_expanded = optional_float(ltm.get("expanded_nodes"))
        base_ttfs = optional_float(ltm.get("time_to_first_solution_ms"))

        def metric(method: str, column: str) -> Any:
            row = methods.get(method, {})
            return row.get(column)

        def delta(method: str, column: str, base: float | None) -> float | None:
            value = optional_float(metric(method, column))
            return value - base if value is not None and base is not None else None

        repair3_rules = parse_rules(metric(REPAIR3, "laur_selected_rules"))
        repair5d_rules = parse_rules(metric(REPAIR5D, "laur_selected_rules"))
        oracle_rules = parse_rules(metric(ORACLE, "laur_selected_rules"))
        repair5d_delta = delta(REPAIR5D, "sum_of_loss_ratio", base_ratio)
        repair3_delta = delta(REPAIR3, "sum_of_loss_ratio", base_ratio)
        oracle_delta = delta(ORACLE, "sum_of_loss_ratio", base_ratio)
        out.append(
            {
                "map": key[0],
                "agents": key[1],
                "seed": key[2],
                "scen": key[3],
                "ltm_ratio": base_ratio,
                "ltm_expanded": base_expanded,
                "ltm_ttfs_ms": base_ttfs,
                "repair3_ratio": optional_float(metric(REPAIR3, "sum_of_loss_ratio")),
                "repair3_delta_ratio_vs_ltm": repair3_delta,
                "repair3_expanded_delta_vs_ltm": delta(REPAIR3, "expanded_nodes", base_expanded),
                "repair3_ttfs_delta_vs_ltm": delta(REPAIR3, "time_to_first_solution_ms", base_ttfs),
                "repair3_selected_rules": json.dumps(repair3_rules, sort_keys=True),
                "repair5d_ratio": optional_float(metric(REPAIR5D, "sum_of_loss_ratio")),
                "repair5d_delta_ratio_vs_ltm": repair5d_delta,
                "repair5d_expanded_delta_vs_ltm": delta(REPAIR5D, "expanded_nodes", base_expanded),
                "repair5d_ttfs_delta_vs_ltm": delta(REPAIR5D, "time_to_first_solution_ms", base_ttfs),
                "repair5d_selected_rules": json.dumps(repair5d_rules, sort_keys=True),
                "repair5d_fallback_count": optional_float(metric(REPAIR5D, "laur_additive_fallback_count")),
                "oracle_ratio": optional_float(metric(ORACLE, "sum_of_loss_ratio")),
                "oracle_delta_ratio_vs_ltm": oracle_delta,
                "oracle_expanded_delta_vs_ltm": delta(ORACLE, "expanded_nodes", base_expanded),
                "oracle_ttfs_delta_vs_ltm": delta(ORACLE, "time_to_first_solution_ms", base_ttfs),
                "oracle_source_rule": metric(ORACLE, "oracle_proxy_source_rule"),
                "oracle_selected_rules": json.dumps(oracle_rules, sort_keys=True),
                "repair5d_worse_than_ltm": bool(repair5d_delta is not None and repair5d_delta > EPS),
                "repair3_wins_repair5d_loses": bool(
                    repair3_delta is not None
                    and repair5d_delta is not None
                    and repair3_delta <= 0.0
                    and repair5d_delta > EPS
                ),
                "both_nonadditive_different_rules": bool(
                    repair3_rules
                    and repair5d_rules
                    and set(repair3_rules) != set(repair5d_rules)
                ),
                "repair5d_commit_heavy_count": int(repair5d_rules.get("commit_heavy", 0)),
                "repair3_block_light_count": int(repair3_rules.get("block_light", 0)),
            }
        )
    return out


def build_rule_outcomes(alignment_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    accum: dict[tuple[str, str], dict[str, Any]] = {}
    method_specs = [
        (REPAIR3, "repair3_selected_rules", "repair3_delta_ratio_vs_ltm"),
        (REPAIR5D, "repair5d_selected_rules", "repair5d_delta_ratio_vs_ltm"),
        (ORACLE, "oracle_selected_rules", "oracle_delta_ratio_vs_ltm"),
    ]
    for row in alignment_rows:
        for method, rules_key, delta_key in method_specs:
            rules = parse_rules(row.get(rules_key))
            if not rules:
                continue
            delta = optional_float(row.get(delta_key))
            for rule, count in rules.items():
                key = (method, rule)
                item = accum.setdefault(
                    key,
                    {
                        "method": method,
                        "rule": rule,
                        "scenario_rows": 0,
                        "weighted_update_count": 0,
                        "weighted_delta_sum": 0.0,
                        "better_scenarios": 0,
                        "equal_scenarios": 0,
                        "worse_scenarios": 0,
                    },
                )
                item["scenario_rows"] += 1
                item["weighted_update_count"] += int(count)
                if delta is not None:
                    item["weighted_delta_sum"] += float(delta) * int(count)
                    if delta < -EPS:
                        item["better_scenarios"] += 1
                    elif delta > EPS:
                        item["worse_scenarios"] += 1
                    else:
                        item["equal_scenarios"] += 1
    out: list[dict[str, Any]] = []
    for item in accum.values():
        updates = int(item["weighted_update_count"])
        next_item = dict(item)
        next_item["mean_delta_ratio_vs_ltm_weighted"] = (
            item["weighted_delta_sum"] / updates if updates else None
        )
        del next_item["weighted_delta_sum"]
        out.append(next_item)
    return sorted(out, key=lambda row: (str(row["method"]), str(row["rule"])))


def distill_offline_distributions(distill_summary: dict[str, Any], decisions: list[dict[str, Any]]) -> dict[str, Any]:
    validation = distill_summary.get("metrics", {}).get("validation", {})
    target = validation.get("target_rule_distribution")
    predicted = validation.get("predicted_rule_distribution")
    if not isinstance(target, dict) or not isinstance(predicted, dict):
        validation_rows = [row for row in decisions if row.get("split") == "validation"]
        target = dict(sorted(Counter(str(row.get("selected_rule", "")) for row in validation_rows).items()))
        predicted = {}
    return {
        "validation_target_rule_distribution": target or {},
        "validation_predicted_rule_distribution": predicted or {},
        "validation_rule_top1": validation.get("rule_top1"),
        "validation_predicted_non_additive_rate": validation.get("predicted_non_additive_rate"),
        "validation_target_selected_harmful_rate": validation.get("target_selected_harmful_rate"),
        "validation_sample_count": validation.get("sample_count"),
    }


def reconstruct_feature_values(update: dict[str, Any], stats: dict[str, float], feature_names: list[str]) -> tuple[list[float], list[str]]:
    agents = finite(update.get("agents"))
    free_cells = finite(stats.get("free_cells"))
    committed = finite(update.get("committed_count"))
    blocked = finite(update.get("blocked_count"))
    values = {
        "agents": agents,
        "free_cells": free_cells,
        "density": safe_ratio(agents, free_cells),
        "map_width": finite(stats.get("map_width")),
        "map_height": finite(stats.get("map_height")),
        "obstacle_ratio": finite(stats.get("obstacle_ratio")),
        "iteration": finite(update.get("iteration")),
        "node_budget": finite(update.get("node_budget")),
        "elapsed_ms": finite(update.get("elapsed_ms")),
        "time_remaining_sec": finite(update.get("time_remaining_sec")),
        "max_iterations": finite(update.get("max_iterations"), 4.0),
        "has_solution_before": 1.0 if bool(update.get("has_incumbent_before")) else 0.0,
        "best_ratio_before": finite(update.get("best_ratio_before")),
        "improved_last_iteration": 1.0 if bool(update.get("improved_last_iteration")) else 0.0,
        "returned_solutions_count_so_far": finite(update.get("returned_solutions_count_so_far")),
        "committed_count": committed,
        "blocked_count": blocked,
        "wait_event_count": finite(update.get("wait_event_count")),
        "goal_wait_ignored_count": finite(update.get("goal_wait_ignored_count")),
        "blocked_per_committed": safe_ratio(blocked, committed),
        "wait_per_committed": safe_ratio(finite(update.get("wait_event_count")), committed),
        "blocked_per_agent": safe_ratio(blocked, agents),
        "committed_per_agent": safe_ratio(committed, agents),
        "nonzero_edges_before": finite(update.get("nonzero_edges_before")),
        "max_raw_before": finite(update.get("max_raw_before")),
        "mean_topk_raw_before": finite(update.get("mean_topk_raw_before")),
        "max_weight_before": finite(update.get("max_weight_before")),
        "topk_raw_delta_mean": finite(update.get("topk_raw_delta_mean")),
        "topk_raw_delta_max": finite(update.get("topk_raw_delta_max")),
        "new_nonzero_edges_count": finite(update.get("new_nonzero_edges_count")),
        "topk_blocked_edge_concentration": finite(update.get("topk_blocked_edge_concentration")),
        "entropy_edge_usage": finite(update.get("entropy_edge_usage")),
        "local_degree_mean_topk": finite(update.get("local_degree_mean_topk")),
        "current_additive_max_normalized_weight": finite(update.get("current_additive_max_normalized_weight")),
        "weight_entropy": finite(update.get("weight_entropy")),
        "saturated_edge_count": finite(update.get("saturated_edge_count")),
    }
    directly_logged = set(update.get("runtime_feature_names", []))
    if directly_logged and isinstance(update.get("runtime_feature_values"), list):
        for name, value in zip(update.get("runtime_feature_names", []), update.get("runtime_feature_values", [])):
            values[str(name)] = finite(value)
    imputed = [
        name
        for name in feature_names
        if name not in directly_logged
        and name
        not in {
            "agents",
            "free_cells",
            "density",
            "map_width",
            "map_height",
            "obstacle_ratio",
            "iteration",
            "has_solution_before",
            "best_ratio_before",
            "returned_solutions_count_so_far",
        }
    ]
    return [finite(values.get(name)) for name in feature_names], imputed


def zscore_rows(
    *,
    root: Path,
    updates: list[dict[str, Any]],
    paired_rows: list[dict[str, Any]],
    feature_names: list[str],
    mean_values: list[float],
    std_values: list[float],
) -> dict[str, Any]:
    scenario_delta = {
        key_for(row): optional_float(row.get("delta_ratio"))
        for row in paired_rows
        if str(row.get("contender_method")) == REPAIR5D
    }
    map_cache = {name: map_stats(root, name) for name in MAP_PATHS}
    ood_records: list[dict[str, Any]] = []
    full_feature_rows = 0
    imputed_feature_counts: Counter[str] = Counter()
    for update in updates:
        if str(update.get("method")) != REPAIR5D:
            continue
        if not bool(update.get("has_incumbent_before")):
            continue
        feature_values, imputed = reconstruct_feature_values(
            update,
            map_cache.get(str(update.get("map")), {}),
            feature_names,
        )
        if update.get("runtime_feature_names"):
            full_feature_rows += 1
        imputed_feature_counts.update(imputed)
        zscores: list[float] = []
        for index, value in enumerate(feature_values):
            stdev = std_values[index] if index < len(std_values) and abs(std_values[index]) > EPS else 1.0
            center = mean_values[index] if index < len(mean_values) else 0.0
            zscores.append((value - center) / stdev)
        abs_z = [abs(value) for value in zscores]
        key = key_for(update)
        delta = scenario_delta.get(key)
        ood_records.append(
            {
                "map": key[0],
                "agents": key[1],
                "seed": key[2],
                "scen": key[3],
                "iteration": int(finite(update.get("iteration"))),
                "applied_rule": str(update.get("applied_rule", "")),
                "predicted_rule": str(update.get("predicted_rule", "")),
                "decision_status": str(update.get("decision_status", "")),
                "fallback_reason": str(update.get("fallback_reason", "")),
                "max_abs_z": max(abs_z) if abs_z else 0.0,
                "mean_abs_z": mean(abs_z) or 0.0,
                "outside_3sigma_count": sum(1 for value in abs_z if value > 3.0),
                "outside_5sigma_count": sum(1 for value in abs_z if value > 5.0),
                "repair5d_delta_ratio_vs_ltm": delta,
                "top_feature_by_abs_z": feature_names[abs_z.index(max(abs_z))] if abs_z else "",
            }
        )
    max_values = [float(row["max_abs_z"]) for row in ood_records]
    outside_3 = [int(row["outside_3sigma_count"]) for row in ood_records]
    outside_5 = [int(row["outside_5sigma_count"]) for row in ood_records]
    deltas = [finite(row.get("repair5d_delta_ratio_vs_ltm"), float("nan")) for row in ood_records]
    bad = [row for row in ood_records if optional_float(row.get("repair5d_delta_ratio_vs_ltm")) is not None and float(row["repair5d_delta_ratio_vs_ltm"]) > EPS]
    nonbad = [row for row in ood_records if optional_float(row.get("repair5d_delta_ratio_vs_ltm")) is not None and float(row["repair5d_delta_ratio_vs_ltm"]) <= EPS]
    return {
        "feature_source": "full_runtime_feature_vector" if full_feature_rows else "proxy_reconstruction_from_update_log_and_map_static_features",
        "full_feature_rows": full_feature_rows,
        "rows": len(ood_records),
        "mean_max_abs_z": mean(max_values),
        "max_abs_z": max(max_values) if max_values else None,
        "mean_abs_z_outside_3sigma_count": mean([float(value) for value in outside_3]),
        "mean_abs_z_outside_5sigma_count": mean([float(value) for value in outside_5]),
        "percent_updates_any_outside_3sigma": safe_ratio(sum(1 for value in outside_3 if value > 0), len(outside_3)),
        "percent_updates_any_outside_5sigma": safe_ratio(sum(1 for value in outside_5 if value > 0), len(outside_5)),
        "mean_max_abs_z_bad_delta_rows": mean([float(row["max_abs_z"]) for row in bad]),
        "mean_max_abs_z_nonbad_delta_rows": mean([float(row["max_abs_z"]) for row in nonbad]),
        "pearson_max_abs_z_vs_delta": pearson(max_values, deltas),
        "top_features_by_abs_z": dict(Counter(str(row["top_feature_by_abs_z"]) for row in ood_records).most_common(10)),
        "imputed_feature_counts": dict(sorted(imputed_feature_counts.items())),
        "note": (
            "The pushed Repair5E update log did not include full runtime feature vectors; "
            "OOD values are proxy diagnostics unless full_feature_rows is nonzero."
        ),
    }


def paired_method_stats(paired_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in paired_rows:
        grouped[str(row.get("contender_method"))].append(row)
    out: dict[str, dict[str, Any]] = {}
    for method, rows in sorted(grouped.items()):
        deltas = [float(value) for value in (optional_float(row.get("delta_ratio")) for row in rows) if value is not None]
        out[method] = {
            "rows": len(rows),
            "better": sum(1 for value in deltas if value < -EPS),
            "equal": sum(1 for value in deltas if abs(value) <= EPS),
            "worse": sum(1 for value in deltas if value > EPS),
            "mean_delta_ratio_vs_ltm": mean(deltas),
        }
    return out


def compare_repair3_repair5d(alignment_rows: list[dict[str, Any]]) -> dict[str, Any]:
    repair3_wins_repair5d_loses = [row for row in alignment_rows if row.get("repair3_wins_repair5d_loses")]
    different_nonadd = [row for row in alignment_rows if row.get("both_nonadditive_different_rules")]
    commit_vs_block = [
        row
        for row in alignment_rows
        if int(row.get("repair5d_commit_heavy_count") or 0) > 0
        and int(row.get("repair3_block_light_count") or 0) > 0
    ]
    return {
        "repair3_wins_and_repair5d_loses_rows": len(repair3_wins_repair5d_loses),
        "both_nonadditive_different_rule_rows": len(different_nonadd),
        "repair5d_commit_heavy_vs_repair3_block_light_rows": len(commit_vs_block),
        "examples": [
            {
                "map": row["map"],
                "agents": row["agents"],
                "seed": row["seed"],
                "repair3_delta": row["repair3_delta_ratio_vs_ltm"],
                "repair5d_delta": row["repair5d_delta_ratio_vs_ltm"],
                "repair3_rules": row["repair3_selected_rules"],
                "repair5d_rules": row["repair5d_selected_rules"],
            }
            for row in repair3_wins_repair5d_loses[:8]
        ],
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stats = summary["paired_method_stats"]
    rule_shift = summary["rule_distribution_shift"]
    ood = summary["feature_ood_diagnostics"]
    compare = summary["repair3_vs_repair5d"]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E Case-B Transfer Analysis\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S').strip()}\n\n")
        handle.write("Diagnostic-only. Phase5.5 allowed: `false`. Phase6 allowed: `false`.\n\n")
        handle.write("## Paired Outcome\n\n")
        handle.write("| method | rows | better | equal | worse | mean delta ratio vs LTM |\n")
        handle.write("|---|---:|---:|---:|---:|---:|\n")
        for method in [REPAIR3, REPAIR5D, ORACLE]:
            row = stats.get(method, {})
            handle.write(
                f"| {method} | {row.get('rows')} | {row.get('better')} | "
                f"{row.get('equal')} | {row.get('worse')} | {row.get('mean_delta_ratio_vs_ltm')} |\n"
            )
        handle.write("\n## Rule Transfer Shift\n\n")
        handle.write(f"- offline validation predicted distribution: `{rule_shift['offline_validation_predicted']}`\n")
        handle.write(f"- Repair5D closed-loop distribution: `{rule_shift['repair5d_closed_loop']}`\n")
        handle.write(f"- oracle/static closed-loop distribution: `{rule_shift['oracle_closed_loop']}`\n")
        handle.write(f"- JS divergence Repair5D closed-loop vs offline predicted: `{rule_shift['js_repair5d_closed_loop_vs_offline_predicted']}`\n")
        handle.write(f"- JS divergence Repair5D closed-loop vs oracle closed-loop: `{rule_shift['js_repair5d_closed_loop_vs_oracle']}`\n")
        handle.write(f"- Repair5D closed-loop commit_heavy share: `{rule_shift['repair5d_commit_heavy_share']}`\n\n")
        handle.write("## Worse-Than-LTM Repair5D Rows\n\n")
        handle.write(f"- rows: `{len(summary['repair5d_worse_than_ltm_rows'])}`\n")
        for row in summary["repair5d_worse_than_ltm_rows"][:8]:
            handle.write(
                f"- `{row['map']}` a{row['agents']} seed {row['seed']}: "
                f"delta={row['repair5d_delta_ratio_vs_ltm']}, rules={row['repair5d_selected_rules']}\n"
            )
        handle.write("\n## Feature OOD\n\n")
        handle.write(f"- source: `{ood.get('feature_source')}`\n")
        handle.write(f"- rows: `{ood.get('rows')}`\n")
        handle.write(f"- mean max |z|: `{ood.get('mean_max_abs_z')}`\n")
        handle.write(f"- max |z|: `{ood.get('max_abs_z')}`\n")
        handle.write(f"- any outside 3 sigma: `{ood.get('percent_updates_any_outside_3sigma')}`\n")
        handle.write(f"- any outside 5 sigma: `{ood.get('percent_updates_any_outside_5sigma')}`\n")
        handle.write(f"- top features by max |z|: `{ood.get('top_features_by_abs_z')}`\n")
        handle.write(f"- note: {ood.get('note')}\n\n")
        handle.write("## Repair3 vs Repair5D\n\n")
        handle.write(f"- Repair3 wins while Repair5D loses rows: `{compare['repair3_wins_and_repair5d_loses_rows']}`\n")
        handle.write(f"- non-additive but different rule rows: `{compare['both_nonadditive_different_rule_rows']}`\n")
        handle.write(f"- Repair5D commit_heavy vs Repair3 block_light rows: `{compare['repair5d_commit_heavy_vs_repair3_block_light_rows']}`\n\n")
        handle.write("## Recommendation\n\n")
        handle.write(f"- selected repair: `{summary['recommended_repair']['selected_option']}`\n")
        handle.write(f"- reason: `{summary['recommended_repair']['reason']}`\n")
        handle.write("\nNo Phase5.5 or Phase6 claim is made from this analysis.\n")


def build_summary(
    *,
    root: Path,
    raw_rows: list[dict[str, Any]],
    update_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
    paired: list[dict[str, Any]],
    distill_decisions: list[dict[str, Any]],
    distill_summary: dict[str, Any],
    runtime_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    alignment = build_alignment_rows(raw_rows)
    rule_outcomes = build_rule_outcomes(alignment)
    offline = distill_offline_distributions(distill_summary, distill_decisions)
    repair5d_dist = distribution_from_summary(summary_rows, REPAIR5D)
    oracle_dist = distribution_from_summary(summary_rows, ORACLE)
    repair3_dist = distribution_from_summary(summary_rows, REPAIR3)
    offline_pred = {str(k): int(v) for k, v in offline["validation_predicted_rule_distribution"].items()}
    repair5d_total = sum(repair5d_dist.values())
    repair5d_commit_share = safe_ratio(repair5d_dist.get("commit_heavy", 0), repair5d_total)

    feature_names = [line.strip() for line in (runtime_dir / "features.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
    mean_values = read_vector_csv(runtime_dir / "mean.csv")
    std_values = read_vector_csv(runtime_dir / "std.csv")
    ood = zscore_rows(
        root=root,
        updates=update_rows,
        paired_rows=paired,
        feature_names=feature_names,
        mean_values=mean_values,
        std_values=std_values,
    )
    worse_rows = [row for row in alignment if row.get("repair5d_worse_than_ltm")]
    recommendation = {
        "selected_option": "Option 3: OOD/defer guard around the existing Repair5D distill bridge",
        "reason": (
            "Repair5D closed-loop choices collapse toward commit_heavy while the oracle/static proxy is diverse; "
            "the available OOD proxy also shows large z-score excursions, so a diagnostic defer guard is the least-stacked targeted repair."
        ),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    summary = {
        "schema_version": "phase5p5_repair5e_caseb_transfer_analysis_v1",
        "created_at": datetime.now().isoformat(),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "inputs": {
            "raw_rows": len(raw_rows),
            "update_rows": len(update_rows),
            "summary_rows": len(summary_rows),
            "paired_rows": len(paired),
            "distill_decision_rows": len(distill_decisions),
            "runtime_dir": str(runtime_dir),
        },
        "paired_method_stats": paired_method_stats(paired),
        "distill_offline_validation": offline,
        "rule_distribution_shift": {
            "offline_validation_predicted": offline_pred,
            "offline_validation_target": offline["validation_target_rule_distribution"],
            "repair3_closed_loop": repair3_dist,
            "repair5d_closed_loop": repair5d_dist,
            "oracle_closed_loop": oracle_dist,
            "repair5d_commit_heavy_share": repair5d_commit_share,
            "js_repair5d_closed_loop_vs_offline_predicted": js_divergence(repair5d_dist, offline_pred),
            "js_repair5d_closed_loop_vs_oracle": js_divergence(repair5d_dist, oracle_dist),
            "js_repair3_closed_loop_vs_repair5d": js_divergence(repair3_dist, repair5d_dist),
        },
        "repair5d_worse_than_ltm_rows": worse_rows,
        "feature_ood_diagnostics": ood,
        "repair3_vs_repair5d": compare_repair3_repair5d(alignment),
        "recommended_repair": recommendation,
        "boundaries": [
            "no Phase5.5 claim",
            "no Phase6 claim",
            "no solver semantic change",
            "LAUR learned UpdateLTM route only",
        ],
    }
    return summary, alignment, rule_outcomes


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-jsonl", type=Path, default=Path(DEFAULT_RAW_JSONL))
    parser.add_argument("--update-jsonl", type=Path, default=Path(DEFAULT_UPDATE_JSONL))
    parser.add_argument("--summary-csv", type=Path, default=Path(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED_CSV))
    parser.add_argument("--distill-decisions-csv", type=Path, default=Path(DEFAULT_DISTILL_DECISIONS_CSV))
    parser.add_argument("--distill-summary-json", type=Path, default=Path(DEFAULT_DISTILL_SUMMARY_JSON))
    parser.add_argument("--runtime-dir", type=Path, default=Path(DEFAULT_DISTILL_RUNTIME_DIR))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--alignment-csv", type=Path, default=Path(DEFAULT_ALIGNMENT_CSV))
    parser.add_argument("--rule-outcomes-csv", type=Path, default=Path(DEFAULT_RULE_OUTCOMES_CSV))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    raw_jsonl = resolve_path(args.raw_jsonl, root)
    update_jsonl = resolve_path(args.update_jsonl, root)
    summary_csv = resolve_path(args.summary_csv, root)
    paired_csv = resolve_path(args.paired_csv, root)
    distill_decisions_csv = resolve_path(args.distill_decisions_csv, root)
    distill_summary_json = resolve_path(args.distill_summary_json, root)
    runtime_dir = resolve_path(args.runtime_dir, root)
    report = resolve_path(args.report, root)
    summary_json = resolve_path(args.summary_json, root)
    alignment_csv = resolve_path(args.alignment_csv, root)
    rule_outcomes_csv = resolve_path(args.rule_outcomes_csv, root)
    if None in (
        raw_jsonl,
        update_jsonl,
        summary_csv,
        paired_csv,
        distill_decisions_csv,
        distill_summary_json,
        runtime_dir,
        report,
        summary_json,
        alignment_csv,
        rule_outcomes_csv,
    ):
        raise ValueError("all paths are required")
    assert raw_jsonl and update_jsonl and summary_csv and paired_csv and distill_decisions_csv
    assert distill_summary_json and runtime_dir and report and summary_json and alignment_csv and rule_outcomes_csv

    summary, alignment, rule_outcomes = build_summary(
        root=root,
        raw_rows=read_jsonl(raw_jsonl),
        update_rows=read_jsonl(update_jsonl),
        summary_rows=read_csv(summary_csv),
        paired=read_csv(paired_csv),
        distill_decisions=read_csv(distill_decisions_csv),
        distill_summary=read_json(distill_summary_json),
        runtime_dir=runtime_dir,
    )
    write_csv(
        alignment_csv,
        alignment,
        [
            "map",
            "agents",
            "seed",
            "scen",
            "ltm_ratio",
            "ltm_expanded",
            "ltm_ttfs_ms",
            "repair3_ratio",
            "repair3_delta_ratio_vs_ltm",
            "repair3_expanded_delta_vs_ltm",
            "repair3_ttfs_delta_vs_ltm",
            "repair3_selected_rules",
            "repair5d_ratio",
            "repair5d_delta_ratio_vs_ltm",
            "repair5d_expanded_delta_vs_ltm",
            "repair5d_ttfs_delta_vs_ltm",
            "repair5d_selected_rules",
            "repair5d_fallback_count",
            "oracle_ratio",
            "oracle_delta_ratio_vs_ltm",
            "oracle_expanded_delta_vs_ltm",
            "oracle_ttfs_delta_vs_ltm",
            "oracle_source_rule",
            "oracle_selected_rules",
            "repair5d_worse_than_ltm",
            "repair3_wins_repair5d_loses",
            "both_nonadditive_different_rules",
            "repair5d_commit_heavy_count",
            "repair3_block_light_count",
        ],
    )
    write_csv(
        rule_outcomes_csv,
        rule_outcomes,
        [
            "method",
            "rule",
            "scenario_rows",
            "weighted_update_count",
            "mean_delta_ratio_vs_ltm_weighted",
            "better_scenarios",
            "equal_scenarios",
            "worse_scenarios",
        ],
    )
    summary["outputs"] = {
        "report": str(report),
        "summary_json": str(summary_json),
        "alignment_csv": str(alignment_csv),
        "rule_outcomes_csv": str(rule_outcomes_csv),
    }
    write_json(summary_json, summary)
    write_report(report, summary)
    print(json.dumps(summary["outputs"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

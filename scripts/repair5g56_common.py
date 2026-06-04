"""Shared helpers for Repair5G.5.6 budget-stable G6 diagnostics."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from repair5g54_common import boolish, score_from_label
from repair5g55_common import (
    G55_ADDITIVE_CANDIDATE,
    G55_AGENT_COUNTS,
    G55_BASE_CANDIDATES,
    G55_MAPS,
    G55_STATIC_CANDIDATE,
    context_id_for,
    feature_values_from_checkpoint,
    group_by_context,
    load_json,
    normalized_context_key,
    oracle_rows_from_labels,
    read_csv_rows,
    read_jsonl,
    repo_root,
    resolve,
    validate_g55_instance_ids,
    write_csv_rows,
    write_json,
    write_text,
)


G56_MAPS = list(G55_MAPS)
G56_AGENT_COUNTS = list(G55_AGENT_COUNTS)
G56_DEFAULT_INSTANCE_IDS = list(range(146, 166))
G56_SUPPORT_INSTANCE_IDS = list(range(146, 156))
G56_DEV_INSTANCE_IDS = list(range(156, 166))
G56_BASE_CANDIDATES = list(G55_BASE_CANDIDATES)
G56_STATIC_CANDIDATE = G55_STATIC_CANDIDATE
G56_ADDITIVE_CANDIDATE = G55_ADDITIVE_CANDIDATE
G56_CONTEXT_TARGET = 120
G56_STABILITY_CONTEXT_TARGET = 30
G56_EPSILON_MARGIN = 1.0e-4
G56_HARMFUL_MARGIN = 0.02

G56_REQUIRED_CLOSED_STATUS = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "aaai_ready": False,
    "ids_166_205_untouched": True,
}

G56_AUDIT_ONLY_FEATURES = {
    "cost_min",
    "cost_max",
    "cost_span",
    "cost_bounds_respected",
}

G56_PERF_SAFE_FEATURES = {
    "agents",
    "map_width",
    "map_height",
    "obstacle_ratio",
    "free_cells",
    "density",
    "ltm_iterations",
    "returned_solutions_count_so_far",
    "has_incumbent_before",
    "best_ratio_before",
    "improved_last_iteration",
    "committed_count",
    "blocked_count",
    "wait_event_count",
    "progress_committed_count",
    "nonprogress_committed_count",
    "blocked_per_committed",
    "wait_per_committed",
    "blocked_per_agent",
    "committed_per_agent",
    "progress_ratio",
    "c_update_count",
    "f_update_count",
    "c_nonzero_edges",
    "f_nonzero_edges",
    "c_flow_update_ratio",
}

G56_FORBIDDEN_TARGET_FEATURES = {
    "candidate_id",
    "resolved_candidate_id",
    "oracle_candidate_id",
    "oracle_score",
    "probe_sum_of_loss_ratio",
    "probe_sum_of_loss",
    "probe_solution_found",
    "probe_feasible",
    "delta_vs_static",
    "delta_vs_additive",
    "final_full_run_outcome",
    "future_solution_outcome",
    "action",
    "actions",
    "priority",
    "restart",
    "restart_node",
    "h_i",
    "heuristic",
}


def number_or_nan(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return math.nan
    return numeric if math.isfinite(numeric) else math.nan


def finite_number(value: Any, default: float = math.inf) -> float:
    numeric = number_or_nan(value)
    return numeric if math.isfinite(numeric) else default


def dedupe_rows(rows: Iterable[dict[str, Any]], keys: Iterable[str]) -> list[dict[str, Any]]:
    key_names = list(keys)
    out: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        key = tuple(row.get(name, "") for name in key_names)
        out[key] = row
    return list(out.values())


def read_jsonl_many(paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        rows.extend(read_jsonl(path))
    return rows


def validate_observed_rows(rows: Iterable[dict[str, Any]], *, label: str) -> bool:
    seeds = []
    for row in rows:
        seed = row.get("seed", "")
        if seed == "":
            continue
        try:
            seeds.append(int(float(seed)))
        except (TypeError, ValueError):
            continue
    try:
        validate_g55_instance_ids(seeds, label=label)
    except SystemExit:
        return False
    return True


def labels_from_probe_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    labels = []
    for row in rows:
        labels.append(
            {
                "context_id": context_id_for(row),
                "map": row.get("map", ""),
                "agents": row.get("agents", ""),
                "seed": row.get("seed", ""),
                "iteration": row.get("iteration", ""),
                "candidate_id": row.get("candidate_id", ""),
                "resolved_candidate_id": row.get("resolved_candidate_id", row.get("candidate_id", "")),
                "candidate_recognized": row.get("candidate_recognized", ""),
                "short_budget_ms": row.get("short_budget_ms", ""),
                "probe_solution_found": row.get("probe_solution_found", ""),
                "probe_feasible": row.get("probe_feasible", ""),
                "probe_sum_of_loss": row.get("probe_sum_of_loss", ""),
                "probe_lower_bound": row.get("probe_lower_bound", ""),
                "probe_sum_of_loss_ratio": row.get("probe_sum_of_loss_ratio", ""),
                "probe_runtime_ms": row.get("probe_runtime_ms", ""),
                "probe_expanded_nodes": row.get("probe_expanded_nodes", ""),
                "probe_low_level_pibt_calls": row.get("probe_low_level_pibt_calls", ""),
                "delta_vs_additive_in_same_context": row.get("delta_vs_additive_in_same_context", ""),
                "delta_vs_static_in_same_context": row.get("delta_vs_static_in_same_context", ""),
                "is_best_candidate_in_context": row.get("is_best_candidate_in_context", ""),
                "oracle_gap_vs_static": row.get("oracle_gap_vs_static", ""),
                "traffic_before_hash_full": row.get("traffic_before_hash_full", ""),
                "trace_event_count": row.get("trace_event_count", ""),
                "feature_leakage_safe": row.get("forbidden_feature_audit_passed", True),
            }
        )
    return labels


def checkpoint_feature_rows(checkpoints: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for checkpoint in checkpoints:
        features = feature_values_from_checkpoint(checkpoint)
        rows.append(
            {
                "context_id": context_id_for(checkpoint),
                "map": checkpoint.get("map", ""),
                "agents": checkpoint.get("agents", ""),
                "seed": checkpoint.get("seed", ""),
                "iteration": checkpoint.get("iteration", ""),
                "traffic_before_hash_full": checkpoint.get("traffic_before_hash_full", ""),
                "trace_event_count": checkpoint.get("trace_event_count", ""),
                **features,
            }
        )
    return rows


def context_rows_from_labels_and_oracle(
    labels: list[dict[str, Any]],
    oracle_rows: list[dict[str, Any]],
    checkpoints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    checkpoint_by_context = {context_id_for(row): feature_values_from_checkpoint(row) for row in checkpoints}
    oracle_by_context = {str(row.get("context_id", "")): row for row in oracle_rows}
    rows = []
    for context_id, group in sorted(group_by_context(labels).items()):
        first = group[0]
        features = checkpoint_by_context.get(context_id, {})
        rows.append(
            {
                "context_id": context_id,
                "map": first.get("map", ""),
                "agents": first.get("agents", ""),
                "seed": first.get("seed", ""),
                "iteration": first.get("iteration", ""),
                "traffic_before_hash_full": first.get("traffic_before_hash_full", ""),
                "trace_event_count": first.get("trace_event_count", ""),
                "candidate_rows": len(group),
                "candidate_ids": ",".join(sorted({str(row.get("candidate_id", "")) for row in group})),
                "oracle_candidate_id": oracle_by_context.get(context_id, {}).get("oracle_candidate_id", ""),
                "oracle_gap_over_static": oracle_by_context.get(context_id, {}).get("oracle_gap_over_static", ""),
                "oracle_gap_over_additive": oracle_by_context.get(context_id, {}).get("oracle_gap_over_additive", ""),
                **features,
            }
        )
    return rows


def iteration_counts(context_rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in context_rows:
        counts[str(int(finite_number(row.get("iteration"), 0.0)))] += 1
    return dict(sorted(counts.items(), key=lambda item: int(item[0])))


def later_iteration_reason(context_rows: list[dict[str, Any]], checkpoints: list[dict[str, Any]]) -> str:
    if any(finite_number(row.get("iteration"), 0.0) > 0 for row in context_rows):
        return ""
    if not checkpoints:
        return "checkpoint callback not retaining later traffic"
    checkpoint_iters = [finite_number(row.get("iteration"), math.nan) for row in checkpoints]
    if not any(math.isfinite(value) and value > 0 for value in checkpoint_iters):
        return "not enough iterations or time-budget stops"
    return "runner max_contexts bug or probe callback not retaining later traffic"


def static_additive_rows(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    static = next((row for row in rows if row.get("candidate_id") == G56_STATIC_CANDIDATE), {})
    additive = next((row for row in rows if row.get("candidate_id") == G56_ADDITIVE_CANDIDATE), {})
    return static, additive


def best_label_row(rows: list[dict[str, Any]]) -> tuple[float, dict[str, Any]]:
    finite = [(score_from_label(row), row) for row in rows]
    finite = [(score, row) for score, row in finite if math.isfinite(score)]
    if not finite:
        return math.inf, {}
    return min(finite, key=lambda item: (item[0], str(item[1].get("candidate_id", ""))))


def normalized_context_key_text(row_or_key: dict[str, Any] | tuple[str, int, int, int, str]) -> str:
    if isinstance(row_or_key, tuple):
        key = row_or_key
    else:
        key = normalized_context_key(row_or_key)
    return f"{key[0]}|a{key[1]}|s{key[2]}|it{key[3]}|{key[4]}"


def json_dumps_compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


__all__ = [
    "G56_ADDITIVE_CANDIDATE",
    "G56_AGENT_COUNTS",
    "G56_AUDIT_ONLY_FEATURES",
    "G56_BASE_CANDIDATES",
    "G56_CONTEXT_TARGET",
    "G56_DEFAULT_INSTANCE_IDS",
    "G56_DEV_INSTANCE_IDS",
    "G56_EPSILON_MARGIN",
    "G56_FORBIDDEN_TARGET_FEATURES",
    "G56_HARMFUL_MARGIN",
    "G56_MAPS",
    "G56_PERF_SAFE_FEATURES",
    "G56_REQUIRED_CLOSED_STATUS",
    "G56_STABILITY_CONTEXT_TARGET",
    "G56_STATIC_CANDIDATE",
    "G56_SUPPORT_INSTANCE_IDS",
    "best_label_row",
    "boolish",
    "checkpoint_feature_rows",
    "context_rows_from_labels_and_oracle",
    "dedupe_rows",
    "finite_number",
    "group_by_context",
    "iteration_counts",
    "json_dumps_compact",
    "labels_from_probe_rows",
    "later_iteration_reason",
    "load_json",
    "normalized_context_key",
    "normalized_context_key_text",
    "number_or_nan",
    "oracle_rows_from_labels",
    "read_csv_rows",
    "read_jsonl_many",
    "repo_root",
    "resolve",
    "score_from_label",
    "static_additive_rows",
    "validate_g55_instance_ids",
    "validate_observed_rows",
    "write_csv_rows",
    "write_json",
    "write_text",
]

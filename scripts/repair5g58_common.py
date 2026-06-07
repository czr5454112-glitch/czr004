"""Shared helpers for Repair5G.5.8 targeted confidence expansion."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable

from repair5g56_common import normalized_context_key, read_jsonl_many  # noqa: F401
from repair5g57_common import (  # noqa: F401
    G56_ADDITIVE_CANDIDATE,
    G56_AUDIT_ONLY_FEATURES,
    G56_FORBIDDEN_TARGET_FEATURES,
    G56_PERF_SAFE_FEATURES,
    G56_STATIC_CANDIDATE,
    boolish,
    budget_key,
    budget_summary_value,
    context_key_from_row,
    count_by,
    finite_number,
    format_optional_float,
    group_by_context,
    is_true,
    json_dumps_compact,
    labels_by_normalized_key,
    labels_scores_by_context_candidate,
    load_json,
    map_agent_key,
    maybe_float,
    normalized_context_key_text,
    number_or_nan,
    read_csv_rows,
    repo_root,
    resolve,
    score_from_label,
    summarize_budget_rows,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


G58_STRESS_BUDGET_MS = 250.0
G58_BONUS_BUDGET_MS = 500.0
G58_PRIMARY_BUDGET_MS = 1000.0
G58_SENTINEL_BUDGET_MS = 2000.0
G58_PRIMARY_BUDGETS_MS = [G58_PRIMARY_BUDGET_MS, G58_SENTINEL_BUDGET_MS]
G58_OPTIONAL_BUDGETS_MS = [G58_STRESS_BUDGET_MS, G58_BONUS_BUDGET_MS]
G58_MARGIN_THRESHOLDS = [0.0025, 0.005, 0.01]
G58_DEFAULT_MARGIN_THRESHOLD = 0.005

G58_STATIC_ABSTAIN_CLASSES = {"stable_static", "abstain_to_static"}
G58_TRAINING_CLASSES = {
    "stable_high_confidence_nonstatic",
    "stable_static",
    "abstain_to_static",
}
G58_ABSTAIN_BANK_CLASSES = {"no_solution_abstain", "longer_budget_needed"}

G58_CLOSED_STATUS = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "aaai_ready": False,
    "runtime_claim_allowed": False,
}


def context_id_for_key(row: dict[str, Any], fallback_key: str) -> str:
    value = str(row.get("context_id", ""))
    return value if value else fallback_key


def confidence_weight(context: dict[str, Any], label_class: str, margin: float) -> float:
    if label_class not in G58_TRAINING_CLASSES:
        return 0.0
    budgets = context.get("budgets", {})
    primary = budgets.get(G58_PRIMARY_BUDGET_MS)
    sentinel = budgets.get(G58_SENTINEL_BUDGET_MS)
    bonus = budgets.get(G58_BONUS_BUDGET_MS)
    stress = budgets.get(G58_STRESS_BUDGET_MS)
    base = 1.0 + min(4.0, max(0.0, margin) * 100.0)
    if bonus and primary and sentinel:
        bonus_oracle = budget_summary_value(bonus, "oracle_candidate_id")
        if bonus_oracle and bonus_oracle == budget_summary_value(primary, "oracle_candidate_id") == budget_summary_value(sentinel, "oracle_candidate_id"):
            base += 0.25
    if stress and primary:
        stress_oracle = budget_summary_value(stress, "oracle_candidate_id")
        if stress_oracle and stress_oracle == budget_summary_value(primary, "oracle_candidate_id"):
            base += 0.10
    return round(min(5.0, base), 6)


def classify_context(context: dict[str, Any], *, margin_threshold: float) -> tuple[str, str, bool, float, str]:
    budgets = context.get("budgets", {})
    primary = budgets.get(G58_PRIMARY_BUDGET_MS)
    sentinel = budgets.get(G58_SENTINEL_BUDGET_MS)
    if not primary or not sentinel:
        return "exclude_from_training", "", False, 0.0, "missing primary 1000 ms or sentinel 2000 ms budget"

    primary_oracle = str(budget_summary_value(primary, "oracle_candidate_id"))
    sentinel_oracle = str(budget_summary_value(sentinel, "oracle_candidate_id"))
    primary_finite = int(budget_summary_value(primary, "finite_candidate_count", 0) or 0)
    sentinel_finite = int(budget_summary_value(sentinel, "finite_candidate_count", 0) or 0)
    primary_static_score = finite_number(primary.get("static_score"), math.inf)
    sentinel_static_score = finite_number(sentinel.get("static_score"), math.inf)
    primary_oracle_score = finite_number(primary.get("oracle_score"), math.inf)
    sentinel_oracle_score = finite_number(sentinel.get("oracle_score"), math.inf)
    primary_margin = finite_number(primary.get("margin_vs_static"), math.nan)
    sentinel_margin = finite_number(sentinel.get("margin_vs_static"), math.nan)
    static_feasible_both = math.isfinite(primary_static_score) and math.isfinite(sentinel_static_score)

    if primary_finite == 0 and sentinel_finite == 0:
        return "no_solution_abstain", G56_STATIC_CANDIDATE, False, 0.0, "no candidate feasible at 1000/2000 ms"
    if primary_finite == 0 and sentinel_finite > 0:
        return "longer_budget_needed", G56_STATIC_CANDIDATE, False, 0.0, "2000 ms finds feasible candidates where 1000 ms does not"
    if primary_finite != sentinel_finite:
        return "budget_sensitive_exclude", G56_STATIC_CANDIDATE, False, 0.0, "candidate feasibility changes between 1000 and 2000 ms"
    if primary_finite <= 0:
        return "exclude_from_training", "", False, 0.0, "unclassifiable feasibility state"

    same_oracle = bool(primary_oracle and sentinel_oracle and primary_oracle == sentinel_oracle)
    primary_static_regret = primary_static_score - primary_oracle_score if math.isfinite(primary_static_score) and math.isfinite(primary_oracle_score) else math.inf
    sentinel_static_regret = sentinel_static_score - sentinel_oracle_score if math.isfinite(sentinel_static_score) and math.isfinite(sentinel_oracle_score) else math.inf
    max_static_regret = max(primary_static_regret, sentinel_static_regret)

    if same_oracle:
        if primary_oracle != G56_STATIC_CANDIDATE and primary_margin <= -margin_threshold and sentinel_margin <= -margin_threshold:
            margin = min(abs(primary_margin), abs(sentinel_margin))
            return "stable_high_confidence_nonstatic", primary_oracle, True, margin, "1000/2000 agree on high-margin nonstatic oracle"
        return "stable_static", G56_STATIC_CANDIDATE, True, max(0.0, margin_threshold - max_static_regret), "1000/2000 agree or nonstatic margin is too small"

    if static_feasible_both and max_static_regret <= margin_threshold:
        return "abstain_to_static", G56_STATIC_CANDIDATE, True, max(0.0, margin_threshold - max_static_regret), "1000/2000 oracle identity disagrees but static is near-oracle"
    return "budget_sensitive_exclude", G56_STATIC_CANDIDATE, False, 0.0, "1000/2000 oracle identity disagrees with nontrivial static regret"


def contexts_from_probe_jsonl(paths: Iterable[Path]) -> dict[str, dict[str, Any]]:
    rows = read_jsonl_many(paths)
    grouped: dict[tuple[str, float], list[dict[str, Any]]] = {}
    metadata: dict[str, dict[str, Any]] = {}
    for row in rows:
        budget = budget_key(row.get("short_budget_ms"))
        if not math.isfinite(budget):
            continue
        key = normalized_context_key_text(normalized_context_key(row))
        grouped.setdefault((key, budget), []).append(row)
        metadata.setdefault(
            key,
            {
                "context_id": context_id_for_key(row, key),
                "normalized_context_key": key,
                "map": row.get("map", ""),
                "agents": row.get("agents", ""),
                "seed": row.get("seed", ""),
                "iteration": row.get("iteration", ""),
                "traffic_before_hash_full": row.get("traffic_before_hash_full", ""),
            },
        )
    contexts: dict[str, dict[str, Any]] = {}
    for (key, budget), group in grouped.items():
        context = contexts.setdefault(key, {**metadata.get(key, {}), "budgets": {}})
        context["budgets"][budget] = summarize_budget_rows(group)
    return contexts


def gate_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    training = [row for row in rows if is_true(row.get("training_eligible"))]
    high = [row for row in rows if row.get("label_class") == "stable_high_confidence_nonstatic"]
    static_or_abstain = [row for row in rows if row.get("label_class") in G58_STATIC_ABSTAIN_CLASSES]
    no_solution_or_budget = [row for row in rows if row.get("label_class") in G58_ABSTAIN_BANK_CLASSES]
    return {
        "training_eligible_contexts": len(training),
        "stable_high_confidence_nonstatic_count": len(high),
        "stable_static_or_abstain_count": len(static_or_abstain),
        "no_solution_or_budget_abstain_count": len(no_solution_or_budget),
    }


__all__ = [
    "G56_ADDITIVE_CANDIDATE",
    "G56_AUDIT_ONLY_FEATURES",
    "G56_FORBIDDEN_TARGET_FEATURES",
    "G56_PERF_SAFE_FEATURES",
    "G56_STATIC_CANDIDATE",
    "G58_ABSTAIN_BANK_CLASSES",
    "G58_BONUS_BUDGET_MS",
    "G58_CLOSED_STATUS",
    "G58_DEFAULT_MARGIN_THRESHOLD",
    "G58_MARGIN_THRESHOLDS",
    "G58_OPTIONAL_BUDGETS_MS",
    "G58_PRIMARY_BUDGET_MS",
    "G58_PRIMARY_BUDGETS_MS",
    "G58_SENTINEL_BUDGET_MS",
    "G58_STATIC_ABSTAIN_CLASSES",
    "G58_STRESS_BUDGET_MS",
    "G58_TRAINING_CLASSES",
    "boolish",
    "budget_key",
    "budget_summary_value",
    "classify_context",
    "confidence_weight",
    "context_key_from_row",
    "contexts_from_probe_jsonl",
    "count_by",
    "finite_number",
    "format_optional_float",
    "gate_counts",
    "group_by_context",
    "is_true",
    "json_dumps_compact",
    "labels_by_normalized_key",
    "labels_scores_by_context_candidate",
    "load_json",
    "map_agent_key",
    "maybe_float",
    "normalized_context_key",
    "normalized_context_key_text",
    "number_or_nan",
    "read_csv_rows",
    "read_jsonl_many",
    "repo_root",
    "resolve",
    "score_from_label",
    "validate_observed_rows",
    "write_csv_rows",
    "write_json",
    "write_text",
]

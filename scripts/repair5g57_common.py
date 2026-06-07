"""Shared helpers for Repair5G.5.7 budget-aware label confidence diagnostics."""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from repair5g56_common import (  # noqa: F401
    G56_ADDITIVE_CANDIDATE,
    G56_AUDIT_ONLY_FEATURES,
    G56_FORBIDDEN_TARGET_FEATURES,
    G56_PERF_SAFE_FEATURES,
    G56_STATIC_CANDIDATE,
    boolish,
    finite_number,
    group_by_context,
    json_dumps_compact,
    load_json,
    normalized_context_key,
    normalized_context_key_text,
    number_or_nan,
    read_csv_rows,
    repo_root,
    resolve,
    score_from_label,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


G57_STRESS_BUDGET_MS = 250.0
G57_MID_BUDGET_MS = 500.0
G57_PRIMARY_BUDGET_MS = 1000.0
G57_SENTINEL_BUDGET_MS = 2000.0
G57_BUDGETS_MS = [
    G57_STRESS_BUDGET_MS,
    G57_MID_BUDGET_MS,
    G57_PRIMARY_BUDGET_MS,
    G57_SENTINEL_BUDGET_MS,
]
G57_MARGIN_THRESHOLDS = [0.0025, 0.005, 0.01]
G57_DEFAULT_MARGIN_THRESHOLD = 0.005
G57_STATIC_ABSTAIN_CLASSES = {"stable_static", "abstain_to_static"}
G57_TRAINING_CLASSES = {
    "stable_high_confidence_nonstatic",
    "stable_static",
    "abstain_to_static",
}
G57_REQUIRED_CLOSED_STATUS = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "aaai_ready": False,
    "runtime_claim_allowed": False,
    "ids_166_205_untouched": True,
}


def budget_key(value: Any) -> float:
    numeric = finite_number(value, math.nan)
    if not math.isfinite(numeric):
        return math.nan
    return float(round(numeric))


def is_finite_score(value: Any) -> bool:
    numeric = number_or_nan(value)
    return math.isfinite(numeric)


def context_key_from_row(row: dict[str, Any]) -> str:
    key = str(row.get("normalized_context_key", ""))
    if key:
        return key
    return normalized_context_key_text(row)


def map_agent_key(row: dict[str, Any]) -> str:
    return f"{row.get('map', '')}|a{int(float(row.get('agents') or 0))}"


def row_seed(row: dict[str, Any]) -> int:
    try:
        return int(float(row.get("seed") or 0))
    except (TypeError, ValueError):
        return 0


def is_true(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def maybe_float(value: Any) -> float | None:
    numeric = number_or_nan(value)
    return numeric if math.isfinite(numeric) else None


def score_for_rank_row(row: dict[str, Any]) -> float:
    return finite_number(row.get("probe_sum_of_loss_ratio"), math.inf)


def sign_for_scores(oracle_score: float, static_score: float) -> str:
    if not math.isfinite(oracle_score) or not math.isfinite(static_score):
        return "unmeasured"
    return "oracle_beats_static" if oracle_score < static_score - 1.0e-12 else "static_ties_or_beats"


def _candidate_sort_item(item: tuple[str, float]) -> tuple[float, str]:
    candidate_id, score = item
    return (score if math.isfinite(score) else math.inf, candidate_id)


def summarize_budget_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_scores: dict[str, float] = {}
    metadata_by_candidate: dict[str, dict[str, Any]] = {}
    for row in rows:
        candidate = str(row.get("candidate_id", ""))
        if not candidate:
            continue
        score = score_for_rank_row(row)
        old_score = candidate_scores.get(candidate, math.inf)
        if score < old_score or candidate not in candidate_scores:
            candidate_scores[candidate] = score
            metadata_by_candidate[candidate] = row
    ranked = sorted(candidate_scores.items(), key=_candidate_sort_item)
    finite_ranked = [(candidate, score) for candidate, score in ranked if math.isfinite(score)]
    oracle_candidate = finite_ranked[0][0] if finite_ranked else ""
    oracle_score = finite_ranked[0][1] if finite_ranked else math.inf
    static_score = candidate_scores.get(G56_STATIC_CANDIDATE, math.inf)
    additive_score = candidate_scores.get(G56_ADDITIVE_CANDIDATE, math.inf)
    return {
        "candidate_scores": candidate_scores,
        "candidate_rows": metadata_by_candidate,
        "candidate_count": len(candidate_scores),
        "finite_candidate_count": len(finite_ranked),
        "feasible_candidate_ids": [candidate for candidate, _score in finite_ranked],
        "oracle_candidate_id": oracle_candidate,
        "oracle_score": oracle_score,
        "static_score": static_score,
        "additive_score": additive_score,
        "margin_vs_static": oracle_score - static_score if math.isfinite(oracle_score) and math.isfinite(static_score) else math.nan,
        "static_regret_to_oracle": static_score - oracle_score if math.isfinite(oracle_score) and math.isfinite(static_score) else math.nan,
        "static_vs_oracle_sign": sign_for_scores(oracle_score, static_score),
        "top1": tuple(candidate for candidate, _score in ranked[:1]),
        "top2": tuple(candidate for candidate, _score in ranked[:2]),
        "top3": tuple(candidate for candidate, _score in ranked[:3]),
    }


def load_budget_rank_contexts(rank_csv: Path) -> dict[str, dict[str, Any]]:
    rows = read_csv_rows(rank_csv)
    grouped: dict[tuple[str, float], list[dict[str, Any]]] = defaultdict(list)
    metadata: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = context_key_from_row(row)
        budget = budget_key(row.get("short_budget_ms"))
        if not key or not math.isfinite(budget):
            continue
        grouped[(key, budget)].append(row)
        metadata.setdefault(
            key,
            {
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


def labels_by_normalized_key(labels: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out = {}
    for row in labels:
        key = context_key_from_row(row)
        if key and key not in out:
            out[key] = row
    return out


def labels_scores_by_context_candidate(labels: Iterable[dict[str, Any]]) -> dict[str, dict[str, float]]:
    scores: dict[str, dict[str, float]] = defaultdict(dict)
    for row in labels:
        context_id = str(row.get("context_id", ""))
        candidate_id = str(row.get("candidate_id", ""))
        if not context_id or not candidate_id:
            continue
        scores[context_id][candidate_id] = score_from_label(row)
    return scores


def budget_summary_value(budget: dict[str, Any] | None, field: str, default: Any = "") -> Any:
    if not budget:
        return default
    value = budget.get(field, default)
    if isinstance(value, float) and not math.isfinite(value):
        return default
    return value


def format_optional_float(value: Any) -> str | float:
    numeric = number_or_nan(value)
    return numeric if math.isfinite(numeric) else ""


def count_by(rows: Iterable[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row.get(field, ""))] += 1
    return dict(sorted(counts.items()))


def default_threshold_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if abs(finite_number(row.get("margin_threshold"), math.nan) - G57_DEFAULT_MARGIN_THRESHOLD) < 1.0e-12
    ]


__all__ = [
    "G56_ADDITIVE_CANDIDATE",
    "G56_AUDIT_ONLY_FEATURES",
    "G56_FORBIDDEN_TARGET_FEATURES",
    "G56_PERF_SAFE_FEATURES",
    "G56_STATIC_CANDIDATE",
    "G57_BUDGETS_MS",
    "G57_DEFAULT_MARGIN_THRESHOLD",
    "G57_MARGIN_THRESHOLDS",
    "G57_MID_BUDGET_MS",
    "G57_PRIMARY_BUDGET_MS",
    "G57_REQUIRED_CLOSED_STATUS",
    "G57_SENTINEL_BUDGET_MS",
    "G57_STATIC_ABSTAIN_CLASSES",
    "G57_STRESS_BUDGET_MS",
    "G57_TRAINING_CLASSES",
    "boolish",
    "budget_key",
    "budget_summary_value",
    "context_key_from_row",
    "count_by",
    "default_threshold_rows",
    "finite_number",
    "format_optional_float",
    "group_by_context",
    "is_finite_score",
    "is_true",
    "json_dumps_compact",
    "labels_by_normalized_key",
    "labels_scores_by_context_candidate",
    "load_budget_rank_contexts",
    "load_json",
    "map_agent_key",
    "maybe_float",
    "normalized_context_key_text",
    "number_or_nan",
    "read_csv_rows",
    "repo_root",
    "resolve",
    "row_seed",
    "score_from_label",
    "sign_for_scores",
    "validate_observed_rows",
    "write_csv_rows",
    "write_json",
    "write_text",
]

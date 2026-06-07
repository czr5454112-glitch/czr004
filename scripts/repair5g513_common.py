"""Shared helpers for Repair5G.5.13 hard-control diagnostics."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Iterable

from repair5g512_common import (
    ADDITIVE_CANDIDATE,
    DEFAULT_MARGIN,
    SLOW_DECAY_HIGH_SHIELD_CANDIDATE,
    STATIC_FLOW_SHIELD_CANDIDATE,
    finite_number,
    mean,
)


G513_CLOSED_CLAIMS = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "aaai_ready": False,
    "runtime_claim_allowed": False,
    "learned_runtime_policy_validated": False,
}


def grouped_contexts(rows: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("normalized_context_key", ""))].append(row)
    return dict(grouped)


def map_agent_key(row: dict[str, Any]) -> str:
    return f"{row.get('map', '')}|a{row.get('agents', '')}"


def row_key(row: dict[str, Any]) -> str:
    return f"{row.get('normalized_context_key', '')}|{row.get('candidate_id', '')}"


def by_candidate(group: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("candidate_id", "")): row for row in group}


def select_candidate(group: list[dict[str, Any]], candidate_id: str) -> dict[str, Any]:
    options = by_candidate(group)
    return options.get(candidate_id) or options.get(STATIC_FLOW_SHIELD_CANDIDATE) or group[0]


def oracle_candidate(group: list[dict[str, Any]]) -> dict[str, Any]:
    return min(
        group,
        key=lambda row: (
            finite_number(row.get("rank_primary"), math.inf),
            finite_number(row.get("oracle_regret_primary"), math.inf),
            str(row.get("candidate_id", "")),
        ),
    )


def selected_row_metrics(row: dict[str, Any]) -> dict[str, float]:
    delta_static = finite_number(row.get("mean_delta_vs_static_primary"), math.inf)
    return {
        "mean_delta_vs_static": delta_static,
        "mean_delta_vs_additive": finite_number(row.get("mean_delta_vs_additive_primary"), math.inf),
        "harmful_vs_static": 1.0 if delta_static >= DEFAULT_MARGIN else 0.0,
        "coverage": 0.0 if str(row.get("candidate_id", "")) == STATIC_FLOW_SHIELD_CANDIDATE else 1.0,
        "regret_to_oracle": finite_number(row.get("oracle_regret_primary"), math.inf),
    }


def summarize_selected(policy: str, selected: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = [selected_row_metrics(row) for row in selected]
    return {
        "row_type": "policy_summary",
        "policy": policy,
        "contexts": len(selected),
        "mean_delta_vs_static": mean(metric["mean_delta_vs_static"] for metric in metrics),
        "mean_delta_vs_additive": mean(metric["mean_delta_vs_additive"] for metric in metrics),
        "harmful_vs_static_rate": mean(metric["harmful_vs_static"] for metric in metrics),
        "coverage": mean(metric["coverage"] for metric in metrics),
        "fallback_rate": 1.0 - mean(metric["coverage"] for metric in metrics),
        "regret_to_oracle": mean(metric["regret_to_oracle"] for metric in metrics),
    }


def context_decision_row(policy: str, selected: dict[str, Any], reason: str = "") -> dict[str, Any]:
    metrics = selected_row_metrics(selected)
    return {
        "row_type": "context_decision",
        "policy": policy,
        "normalized_context_key": selected.get("normalized_context_key", ""),
        "map": selected.get("map", ""),
        "agents": selected.get("agents", ""),
        "seed": selected.get("seed", ""),
        "selected_candidate_id": selected.get("candidate_id", ""),
        "oracle_candidate_for_context": selected.get("oracle_candidate_for_context", ""),
        "selection_reason": reason,
        "mean_delta_vs_static": metrics["mean_delta_vs_static"],
        "mean_delta_vs_additive": metrics["mean_delta_vs_additive"],
        "harmful_vs_static": metrics["harmful_vs_static"],
        "coverage": metrics["coverage"],
        "regret_to_oracle": metrics["regret_to_oracle"],
    }


def candidate_train_stats(train_rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in train_rows:
        grouped[str(row.get("candidate_id", ""))].append(
            finite_number(row.get("mean_delta_vs_static_primary"), math.inf)
        )
    out = {}
    for candidate, values in grouped.items():
        finite = [value for value in values if math.isfinite(value)]
        harmful = [value >= DEFAULT_MARGIN for value in finite]
        out[candidate] = {
            "mean_delta_vs_static": mean(finite),
            "harmful_vs_static_rate": sum(harmful) / len(harmful) if harmful else math.inf,
            "rows": float(len(finite)),
        }
    return out


def map_agent_candidate_train_stats(
    train_rows: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, float]]]:
    grouped: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in train_rows:
        grouped[map_agent_key(row)][str(row.get("candidate_id", ""))].append(
            finite_number(row.get("mean_delta_vs_static_primary"), math.inf)
        )
    out: dict[str, dict[str, dict[str, float]]] = {}
    for key, by_candidate_rows in grouped.items():
        out[key] = {}
        for candidate, values in by_candidate_rows.items():
            finite = [value for value in values if math.isfinite(value)]
            harmful = [value >= DEFAULT_MARGIN for value in finite]
            out[key][candidate] = {
                "mean_delta_vs_static": mean(finite),
                "harmful_vs_static_rate": sum(harmful) / len(harmful) if harmful else math.inf,
                "rows": float(len(finite)),
            }
    return out


def is_safe_train_candidate(stats: dict[str, float], *, max_harmful_rate: float = 0.05) -> bool:
    return (
        stats.get("mean_delta_vs_static", math.inf) <= -DEFAULT_MARGIN
        and stats.get("harmful_vs_static_rate", math.inf) <= max_harmful_rate
    )


def best_safe_nonstatic_candidate(stats: dict[str, dict[str, float]]) -> str:
    candidates = [
        (value["mean_delta_vs_static"], candidate)
        for candidate, value in stats.items()
        if candidate not in {STATIC_FLOW_SHIELD_CANDIDATE, ADDITIVE_CANDIDATE}
        and is_safe_train_candidate(value)
    ]
    return min(candidates)[1] if candidates else STATIC_FLOW_SHIELD_CANDIDATE


def selected_for_fixed_candidate(rows: list[dict[str, Any]], candidate_id: str) -> list[dict[str, Any]]:
    return [
        select_candidate(group, candidate_id)
        for _, group in sorted(grouped_contexts(rows).items())
    ]


def selected_for_oracle(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [oracle_candidate(group) for _, group in sorted(grouped_contexts(rows).items())]


def selected_for_safe_slow_decay_gate(
    train_rows: list[dict[str, Any]], eval_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    train_stats = map_agent_candidate_train_stats(train_rows)
    choices = {}
    for key, values in train_stats.items():
        slow_stats = values.get(SLOW_DECAY_HIGH_SHIELD_CANDIDATE, {})
        choices[key] = (
            SLOW_DECAY_HIGH_SHIELD_CANDIDATE
            if is_safe_train_candidate(slow_stats)
            else STATIC_FLOW_SHIELD_CANDIDATE
        )
    selected = []
    for _, group in sorted(grouped_contexts(eval_rows).items()):
        selected.append(select_candidate(group, choices.get(map_agent_key(group[0]), STATIC_FLOW_SHIELD_CANDIDATE)))
    return selected, choices


def selected_for_safe_map_agent_gate(
    train_rows: list[dict[str, Any]], eval_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    choices = {
        key: best_safe_nonstatic_candidate(values)
        for key, values in map_agent_candidate_train_stats(train_rows).items()
    }
    selected = []
    for _, group in sorted(grouped_contexts(eval_rows).items()):
        selected.append(select_candidate(group, choices.get(map_agent_key(group[0]), STATIC_FLOW_SHIELD_CANDIDATE)))
    return selected, choices

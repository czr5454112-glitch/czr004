"""Shared helpers for Repair5G.5.15 rich interaction diagnostics."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Any, Iterable

from repair5g512_common import (
    DEFAULT_MARGIN,
    STATIC_FLOW_SHIELD_CANDIDATE,
    finite_number,
    leakage_scan,
    mean,
    observed_id_flags,
)
from repair5g513_common import (
    context_decision_row,
    grouped_contexts,
    select_candidate,
    selected_for_oracle,
    summarize_selected,
)


G515_CLOSED_CLAIMS = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "aaai_ready": False,
    "runtime_claim_allowed": False,
    "learned_runtime_policy_validated": False,
}

RISK_LAMBDAS = [0.05, 0.10, 0.20]

DEFAULT_V4_MATRIX = "outputs/tables/phase5p5_repair5g514_candidate_feature_matrix_v4.csv"
DEFAULT_V5_MATRIX = "outputs/tables/phase5p5_repair5g515_candidate_feature_matrix_v5.csv"
DEFAULT_V5_SUMMARY = "outputs/reports/phase5p5_repair5g515_candidate_feature_matrix_v5_summary.json"
DEFAULT_TWO_STAGE_MODEL = "outputs/reports/phase5p5_repair5g515_two_stage_safety_ranker_model.json"
DEFAULT_PAIRWISE_MODEL = "outputs/reports/phase5p5_repair5g515_pairwise_context_ranker_model.json"
DEFAULT_EVAL_CONTEXTS = "outputs/tables/phase5p5_repair5g515_calibrated_interaction_ranker_context_decisions.csv"
DEFAULT_EVAL_SUMMARY = "outputs/reports/phase5p5_repair5g515_calibrated_interaction_rankers_summary.json"

REQUIRED_G514_ARTIFACTS = [
    "outputs/reports/phase5p5_repair5g514_decision.md",
    "outputs/reports/phase5p5_repair5g514_decision_summary.json",
    "outputs/reports/phase5p5_repair5g514_candidate_ranker_v4_eval_summary.json",
    "outputs/reports/phase5p5_repair5g514_rich_context_features_summary.json",
    "outputs/reports/phase5p5_repair5g514_candidate_feature_matrix_v4_summary.json",
    "outputs/reports/phase5p5_repair5g514_static_abstention_boundary_targets_summary.json",
    "outputs/tables/phase5p5_repair5g514_candidate_feature_matrix_v4.csv",
    "outputs/tables/phase5p5_repair5g514_candidate_ranker_v4_context_decisions.csv",
    "outputs/tables/phase5p5_repair5g514_rich_context_features_by_context.csv",
]

REQUIRED_RICH_INTERACTIONS = [
    (
        "feature_rich_blocked_per_committed",
        "feature_candidate_alpha_cong_blocked",
        "feature_interaction_rich_blocked_per_committed_x_alpha_cong_blocked",
    ),
    (
        "feature_rich_blocked_per_agent",
        "feature_candidate_alpha_cong_blocked",
        "feature_interaction_rich_blocked_per_agent_x_alpha_cong_blocked",
    ),
    (
        "feature_rich_wait_per_committed",
        "feature_candidate_alpha_flow_wait_or_nonprogress",
        "feature_interaction_rich_wait_per_committed_x_alpha_flow_wait_or_nonprogress",
    ),
    (
        "feature_rich_wait_event_count",
        "feature_candidate_alpha_flow_wait_or_nonprogress",
        "feature_interaction_rich_wait_event_count_x_alpha_flow_wait_or_nonprogress",
    ),
    (
        "feature_rich_progress_ratio",
        "feature_candidate_alpha_flow_progress",
        "feature_interaction_rich_progress_ratio_x_alpha_flow_progress",
    ),
    (
        "feature_rich_committed_per_agent",
        "feature_candidate_alpha_cong_committed",
        "feature_interaction_rich_committed_per_agent_x_alpha_cong_committed",
    ),
    (
        "feature_rich_c_flow_update_ratio",
        "feature_candidate_flow_shield_beta",
        "feature_interaction_rich_c_flow_update_ratio_x_flow_shield_beta",
    ),
    (
        "feature_rich_c_flow_update_ratio",
        "feature_candidate_max_flow_shield",
        "feature_interaction_rich_c_flow_update_ratio_x_max_flow_shield",
    ),
    (
        "feature_rich_c_update_count",
        "feature_candidate_rho_cong",
        "feature_interaction_rich_c_update_count_x_rho_cong",
    ),
    (
        "feature_rich_f_update_count",
        "feature_candidate_rho_flow",
        "feature_interaction_rich_f_update_count_x_rho_flow",
    ),
    (
        "feature_rich_cost_span",
        "feature_candidate_flow_shield_beta",
        "feature_interaction_rich_cost_span_x_flow_shield_beta",
    ),
    (
        "feature_rich_cost_span",
        "feature_candidate_max_flow_shield",
        "feature_interaction_rich_cost_span_x_max_flow_shield",
    ),
    (
        "feature_rich_cost_max",
        "feature_candidate_max_flow_shield",
        "feature_interaction_rich_cost_max_x_max_flow_shield",
    ),
]


def risk_suffixes(lam: float) -> list[str]:
    return sorted({str(lam).replace(".", "p"), f"{lam:.2f}".replace(".", "p")})


def add_risk_adjusted(row: dict[str, Any]) -> dict[str, Any]:
    mean_delta = finite_number(row.get("mean_delta_vs_static"), math.inf)
    harmful = finite_number(row.get("harmful_vs_static_rate"), math.inf)
    for lam in RISK_LAMBDAS:
        value = mean_delta + lam * harmful if math.isfinite(mean_delta) and math.isfinite(harmful) else math.inf
        for suffix in risk_suffixes(lam):
            row[f"risk_adjusted_utility_lambda_{suffix}"] = value
    return row


def policy_summary(policy: str, selected: list[dict[str, Any]]) -> dict[str, Any]:
    return add_risk_adjusted(summarize_selected(policy, selected))


def metric_value(row: dict[str, Any], metric: str) -> float:
    return finite_number(row.get(metric), math.inf)


def feature_columns(rows: list[dict[str, Any]]) -> list[str]:
    return [name for name in rows[0] if name.startswith("feature_")] if rows else []


def g515_new_feature(name: str) -> bool:
    return (
        name.startswith("feature_interaction_rich_")
        or name.startswith("feature_interaction_centered_")
        or name.startswith("feature_interaction_train_z_")
        or name.startswith("feature_rich_log1p_")
        or name.startswith("feature_rich_capped_")
        or name.startswith("feature_rich_train_z_")
    )


def v4_reproduced_features(rows: list[dict[str, Any]]) -> list[str]:
    return [name for name in feature_columns(rows) if not g515_new_feature(name)]


def no_rich_features(rows: list[dict[str, Any]]) -> list[str]:
    return [
        name
        for name in feature_columns(rows)
        if not name.startswith("feature_rich_")
        and not name.startswith("feature_interaction_rich_")
        and not name.startswith("feature_interaction_centered_rich_")
        and not name.startswith("feature_interaction_train_z_rich_")
    ]


def no_rich_interaction_features(rows: list[dict[str, Any]]) -> list[str]:
    return [
        name
        for name in feature_columns(rows)
        if not name.startswith("feature_interaction_rich_")
        and not name.startswith("feature_interaction_centered_rich_")
        and not name.startswith("feature_interaction_train_z_rich_")
    ]


def context_only_rich_features(rows: list[dict[str, Any]]) -> list[str]:
    return [name for name in feature_columns(rows) if name.startswith("feature_map_") or name.startswith("feature_rich_")]


def rank_feature_names(rows: list[dict[str, Any]]) -> list[str]:
    return [
        name
        for name in feature_columns(rows)
        if name.startswith("feature_candidate_")
        or name.startswith("feature_interaction_")
    ]


def interaction_feature_names(rows: list[dict[str, Any]]) -> list[str]:
    return [name for name in feature_columns(rows) if name.startswith("feature_interaction_")]


def rich_interaction_feature_names(rows: list[dict[str, Any]]) -> list[str]:
    return [
        name
        for name in feature_columns(rows)
        if name.startswith("feature_interaction_rich_")
        or name.startswith("feature_interaction_centered_rich_")
        or name.startswith("feature_interaction_train_z_rich_")
    ]


def feature_varies_within_any_context(rows: list[dict[str, Any]], feature: str) -> bool:
    for group in grouped_contexts(rows).values():
        values = {finite_number(row.get(feature), math.nan) for row in group}
        finite = {value for value in values if math.isfinite(value)}
        if len(finite) > 1:
            return True
    return False


def count_candidate_varying(rows: list[dict[str, Any]], features: Iterable[str]) -> int:
    return sum(1 for feature in features if feature_varies_within_any_context(rows, feature))


def selected_row_metrics(row: dict[str, Any]) -> dict[str, float]:
    delta_static = finite_number(row.get("mean_delta_vs_static_primary"), math.inf)
    return {
        "mean_delta_vs_static": delta_static,
        "mean_delta_vs_additive": finite_number(row.get("mean_delta_vs_additive_primary"), math.inf),
        "harmful_vs_static": 1.0 if delta_static >= DEFAULT_MARGIN else 0.0,
        "coverage": 0.0 if str(row.get("candidate_id", "")) == STATIC_FLOW_SHIELD_CANDIDATE else 1.0,
        "regret_to_oracle": finite_number(row.get("oracle_regret_primary"), math.inf),
    }


def context_row(
    policy: str,
    selected: dict[str, Any],
    reason: str,
    *,
    eval_scope: str,
    fold_seed: str | int | None = None,
    predicted_best_delta: Any = "",
    predicted_best_harmful_risk: Any = "",
    predicted_margin: Any = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = context_decision_row(policy, selected, reason)
    row.update(
        {
            "eval_scope": eval_scope,
            "fold_seed": "" if fold_seed is None else fold_seed,
            "predicted_best_delta": predicted_best_delta,
            "predicted_best_harmful_risk": predicted_best_harmful_risk,
            "predicted_margin": predicted_margin,
        }
    )
    if extra:
        row.update(extra)
    return row


def static_or_first(group: list[dict[str, Any]]) -> dict[str, Any]:
    return select_candidate(group, STATIC_FLOW_SHIELD_CANDIDATE)


def oracle_or_first(group: list[dict[str, Any]]) -> dict[str, Any]:
    return selected_for_oracle(group)[0]


def rows_by_seed(rows: list[dict[str, Any]]) -> list[int]:
    return sorted({int(finite_number(row.get("seed"), -1)) for row in rows if finite_number(row.get("seed"), math.nan) >= 0})


def rows_with_seed(rows: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    return [row for row in rows if int(finite_number(row.get("seed"), -1)) == seed]


def rows_without_seed(rows: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    return [row for row in rows if int(finite_number(row.get("seed"), -1)) != seed]


def grouped_candidate_count_ok(rows: list[dict[str, Any]], expected: int = 14) -> bool:
    return all(len(group) == expected for group in grouped_contexts(rows).values())


def bootstrap_rows(policy_selected: dict[str, list[dict[str, Any]]], *, samples: int, seed: int = 20260607) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    out: list[dict[str, Any]] = []
    metrics = [
        "mean_delta_vs_static",
        "harmful_vs_static_rate",
        "coverage",
        "regret_to_oracle",
        "risk_adjusted_utility_lambda_0p05",
        "risk_adjusted_utility_lambda_0p10",
        "risk_adjusted_utility_lambda_0p20",
    ]
    for policy, selected in sorted(policy_selected.items()):
        if not selected:
            continue
        by_metric: dict[str, list[float]] = {metric: [] for metric in metrics}
        for _ in range(samples):
            sample = [selected[rng.randrange(len(selected))] for _ in selected]
            summary = policy_summary(policy, sample)
            for metric in metrics:
                by_metric[metric].append(finite_number(summary.get(metric), math.nan))
        for metric, values in by_metric.items():
            finite = sorted(value for value in values if math.isfinite(value))
            low = finite[int(0.025 * (len(finite) - 1))] if finite else math.nan
            high = finite[int(0.975 * (len(finite) - 1))] if finite else math.nan
            out.append(
                {
                    "row_type": "bootstrap_ci",
                    "policy": policy,
                    "metric": metric,
                    "estimate": mean(values),
                    "ci_low": low,
                    "ci_high": high,
                    "samples": samples,
                }
            )
    return out


def harmful_group_rows(policy_selected: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for policy, selected in sorted(policy_selected.items()):
        for field in ["seed", "map_agent"]:
            grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in selected:
                key = str(row.get("seed", "")) if field == "seed" else f"{row.get('map', '')}|a{row.get('agents', '')}"
                grouped[key].append(row)
            for key, values in sorted(grouped.items()):
                harmful = [
                    1.0 if finite_number(row.get("mean_delta_vs_static_primary"), math.inf) >= DEFAULT_MARGIN else 0.0
                    for row in values
                ]
                out.append(
                    {
                        "row_type": "harmful_count",
                        "policy": policy,
                        "group_type": field,
                        "group_key": key,
                        "contexts": len(values),
                        "harmful_contexts": int(sum(harmful)),
                        "harmful_vs_static_rate": mean(harmful),
                    }
                )
    return out


def calibration_rows(context_rows: list[dict[str, Any]], *, policies: Iterable[str]) -> list[dict[str, Any]]:
    bins = [(0.0, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.50), (0.50, 1.01)]
    out: list[dict[str, Any]] = []
    wanted = set(policies)
    for policy in sorted(wanted):
        rows = [row for row in context_rows if row.get("policy") == policy and row.get("eval_scope") == "oof"]
        for low, high in bins:
            bucket = [
                row
                for row in rows
                if low <= max(0.0, min(1.0, finite_number(row.get("predicted_best_harmful_risk"), math.nan))) < high
            ]
            actual = [finite_number(row.get("harmful_vs_static"), math.nan) for row in bucket]
            preds = [max(0.0, min(1.0, finite_number(row.get("predicted_best_harmful_risk"), math.nan))) for row in bucket]
            out.append(
                {
                    "row_type": "risk_calibration_bucket",
                    "policy": policy,
                    "risk_bucket_low": low,
                    "risk_bucket_high": high,
                    "contexts": len(bucket),
                    "mean_predicted_harmful_risk": mean(preds),
                    "actual_harmful_rate": mean(actual),
                }
            )
    return out


def add_scope_to_summaries(scope: str, summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in summaries:
        item = dict(row)
        item["eval_scope"] = scope
        out.append(item)
    return out


def summary_by_policy(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("policy", "")): row for row in rows}


def risk_metric_name(lam: float) -> str:
    return f"risk_adjusted_utility_lambda_{f'{lam:.2f}'.replace('.', 'p')}"


def better_risk(lhs: dict[str, Any], rhs: dict[str, Any], lam: float) -> bool:
    return finite_number(lhs.get(risk_metric_name(lam)), math.inf) < finite_number(rhs.get(risk_metric_name(lam)), math.inf)


def best_interaction_policy(summaries: dict[str, dict[str, Any]]) -> str:
    candidates = ["two_stage_safety_ranker", "pairwise_context_ranker"]
    available = [policy for policy in candidates if policy in summaries]
    if not available:
        return ""
    return min(available, key=lambda policy: (finite_number(summaries[policy].get(risk_metric_name(0.10)), math.inf), policy))


def gate_flags_for_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    feature_names = feature_columns(rows)
    leak = leakage_scan(feature_names)
    flags = observed_id_flags(rows)
    return {
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        **flags,
        "grouped_14_candidate_rows_per_context": grouped_candidate_count_ok(rows),
    }

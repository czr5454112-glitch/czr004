"""Shared helpers for Repair5G.5.20 opportunity-gated policy diagnostics."""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from repair5g519_common import (
    ADDITIVE_CANDIDATE,
    DEFAULT_MARGIN,
    G519_AUTOPSY_SUMMARY,
    G519_CONTEXT_DECISIONS_CSV,
    G519_DECISION_SUMMARY,
    G519_EVAL_CSV,
    G519_FEATURE_MATRIX_CSV,
    G519_TARGETS_CSV,
    G519_TARGET_BUDGET_AUDIT_CSV,
    RISK_LAMBDAS,
    SEED,
    STATIC_FLOW_SHIELD_CANDIDATE,
    as_jsonable,
    boolish,
    candidate_param_feature_columns,
    candidate_params,
    candidate_train_stats,
    context_feature_columns,
    csv_number,
    enforce_reserved_guard_rejects_166,
    family_for_candidate,
    feature_columns,
    finite_number,
    fit_ridge,
    forbidden_feature_scan,
    map_agent_key,
    map_family,
    map_family_key,
    matrix,
    mean,
    nearest_old_candidate,
    no_rich_interaction_feature_columns,
    numeric_candidate_param_dict,
    observed_id_flags,
    old14_candidate_ids,
    oracle_new22_row,
    oracle_old14_row,
    predict_ridge,
    random_feature_matrix,
    read_json_file,
    read_rows,
    repo_root,
    resolve,
    rows_by_context,
    sample_weights,
    select_candidate,
    selected_for_fixed,
    suffix_for_lambda,
    write_json_file,
    write_rows,
    write_text_file,
)
from repair5g512_common import leakage_scan, observed_id_guard


G520_CLOSED_CLAIMS = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "aaai_ready": False,
    "runtime_claim_allowed": False,
    "learned_runtime_policy_validated": False,
}

G520_PLAN_MD = "czr004_repair5g520_opportunity_gated_new_candidate_policy_plan.md"

G520_VERIFY_REPORT = "outputs/reports/phase5p5_repair5g520_g519_artifact_verification.md"
G520_VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g520_g519_artifact_verification_summary.json"

G520_TARGET_SEMANTICS_AUDIT_CSV = "outputs/tables/phase5p5_repair5g520_target_semantics_audit.csv"
G520_TARGET_SEMANTICS_AUDIT_REPORT = "outputs/reports/phase5p5_repair5g520_target_semantics_audit.md"
G520_TARGET_SEMANTICS_AUDIT_SUMMARY = "outputs/reports/phase5p5_repair5g520_target_semantics_audit_summary.json"

G520_TARGETS_CSV = "outputs/tables/phase5p5_repair5g520_corrected_candidate_targets_v9.csv"
G520_TARGETS_REPORT = "outputs/reports/phase5p5_repair5g520_corrected_candidate_targets_v9.md"
G520_TARGETS_SUMMARY = "outputs/reports/phase5p5_repair5g520_corrected_candidate_targets_v9_summary.json"

G520_FEATURE_MATRIX_CSV = "outputs/tables/phase5p5_repair5g520_opportunity_feature_matrix_v9.csv"
G520_FEATURE_MATRIX_REPORT = "outputs/reports/phase5p5_repair5g520_opportunity_feature_matrix_v9.md"
G520_FEATURE_MATRIX_SUMMARY = "outputs/reports/phase5p5_repair5g520_opportunity_feature_matrix_v9_summary.json"

G520_POLICY_EVAL_CSV = "outputs/tables/phase5p5_repair5g520_opportunity_gated_policy_eval.csv"
G520_POLICY_CONTEXT_DECISIONS_CSV = "outputs/tables/phase5p5_repair5g520_opportunity_gated_context_decisions.csv"
G520_POLICY_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g520_opportunity_gated_policy_bootstrap.csv"
G520_POLICY_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g520_opportunity_gated_policy_calibration.csv"
G520_POLICY_DIAGNOSTICS_CSV = "outputs/tables/phase5p5_repair5g520_opportunity_gated_policy_group_diagnostics.csv"
G520_POLICY_REPORT = "outputs/reports/phase5p5_repair5g520_opportunity_gated_policy_eval.md"
G520_POLICY_SUMMARY = "outputs/reports/phase5p5_repair5g520_opportunity_gated_policy_eval_summary.json"

G520_AUTOPSY_CSV = "outputs/tables/phase5p5_repair5g520_new_candidate_policy_autopsy.csv"
G520_AUTOPSY_REPORT = "outputs/reports/phase5p5_repair5g520_new_candidate_policy_autopsy.md"
G520_AUTOPSY_SUMMARY = "outputs/reports/phase5p5_repair5g520_new_candidate_policy_autopsy_summary.json"

G520_SECOND_WAVE_CONTEXTS_CSV = "outputs/tables/phase5p5_repair5g520_second_wave_lattice_target_contexts.csv"
G520_SECOND_WAVE_REPORT = "outputs/reports/phase5p5_repair5g520_second_wave_lattice_plan.md"
G520_SECOND_WAVE_SUMMARY = "outputs/reports/phase5p5_repair5g520_second_wave_lattice_plan_summary.json"

G520_DECISION_REPORT = "outputs/reports/phase5p5_repair5g520_decision.md"
G520_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g520_decision_summary.json"

G519_REQUIRED_ARTIFACTS = [
    G519_DECISION_SUMMARY,
    G519_TARGETS_CSV,
    G519_FEATURE_MATRIX_CSV,
    G519_EVAL_CSV,
    G519_CONTEXT_DECISIONS_CSV,
    G519_AUTOPSY_SUMMARY,
]

PRIMARY_POLICY_EXCLUSIONS = {
    "oracle_new22_upper_bound",
    "oracle_old14_upper_bound",
    "random_feature_model",
    "shuffled_label_model",
    "new_label_shuffled_control",
}


def row_key(row: dict[str, Any]) -> str:
    return f"{row.get('normalized_context_key', '')}|{row.get('candidate_id', '')}"


def context_candidate_budget_key(row: dict[str, Any]) -> tuple[str, str, int]:
    return (
        str(row.get("normalized_context_key", "")),
        str(row.get("candidate_id", "")),
        int(finite_number(row.get("short_budget_ms"), -1)),
    )


def g520_perf_feature_columns(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return []
    return [
        name
        for name in rows[0]
        if name.startswith("feature_")
        and not name.startswith("feature_audit_")
        and "surrogate" not in name.lower()
    ]


def g520_ranker_feature_columns(rows: list[dict[str, Any]]) -> list[str]:
    return [
        name
        for name in g520_perf_feature_columns(rows)
        if name.startswith("feature_candidate_")
        or name.startswith("feature_interaction_")
        or name.startswith("feature_centered_")
        or name.startswith("feature_specialist_")
        or name.startswith("feature_nearest_old_")
        or name.startswith("feature_family_local_")
    ]


def no_new_source_feature_columns(rows: list[dict[str, Any]]) -> list[str]:
    blocked = ("g518_new", "is_new", "source_old14", "source_g518", "specialist")
    return [
        name
        for name in g520_perf_feature_columns(rows)
        if not any(term in name.lower() for term in blocked)
    ]


def numeric_target(row: dict[str, Any], field: str, default: float = 0.25) -> float:
    value = finite_number(row.get(field), math.nan)
    return value if math.isfinite(value) else default


def corrected_delta(row: dict[str, Any]) -> float:
    return finite_number(row.get("solution_quality_delta_vs_static"), math.inf)


def solution_harmful(row: dict[str, Any]) -> bool:
    return boolish(row.get("solution_quality_harmful_vs_static"))


def no_solution_risk(row: dict[str, Any]) -> bool:
    return boolish(row.get("no_solution_or_infeasible")) or boolish(row.get("budget_nonfinite"))


def total_harmful(row: dict[str, Any]) -> bool:
    return solution_harmful(row) or no_solution_risk(row)


def helpful(row: dict[str, Any]) -> bool:
    value = corrected_delta(row)
    return math.isfinite(value) and value <= -DEFAULT_MARGIN and not no_solution_risk(row)


def safe_mean(values: Iterable[float]) -> float:
    return mean(values)


def policy_metric_row_corrected(policy: str, selected: list[dict[str, Any]], *, eval_scope: str) -> dict[str, Any]:
    contexts = len(selected)
    deltas = [corrected_delta(row) for row in selected]
    finite_deltas = [value for value in deltas if math.isfinite(value)]
    solution_harms = [1.0 if solution_harmful(row) else 0.0 for row in selected]
    no_solution = [1.0 if no_solution_risk(row) else 0.0 for row in selected]
    total_harms = [1.0 if total_harmful(row) else 0.0 for row in selected]
    helpfuls = [1.0 if helpful(row) else 0.0 for row in selected]
    nonstatic = [
        0.0 if str(row.get("candidate_id", "")) == STATIC_FLOW_SHIELD_CANDIDATE else 1.0
        for row in selected
    ]
    new_flags = [1.0 if boolish(row.get("is_new_candidate")) else 0.0 for row in selected]
    new_help = [1.0 for row in selected if boolish(row.get("is_new_candidate")) and helpful(row)]
    new_harm = [1.0 for row in selected if boolish(row.get("is_new_candidate")) and total_harmful(row)]
    new_opp_contexts = [row for row in selected if boolish(row.get("new_opportunity_context"))]
    new_opp_capture = [
        1.0
        for row in selected
        if boolish(row.get("new_opportunity_context")) and boolish(row.get("is_new_candidate"))
    ]
    old14_regrets = [finite_number(row.get("old14_oracle_regret_primary"), math.inf) for row in selected]
    new22_regrets = [finite_number(row.get("new22_oracle_regret_primary"), math.inf) for row in selected]
    row = {
        "row_type": "policy_summary",
        "eval_scope": eval_scope,
        "policy": policy,
        "contexts": contexts,
        "mean_delta_vs_static": safe_mean(deltas),
        "mean_solution_quality_delta_vs_static": safe_mean(finite_deltas),
        "solution_quality_harmful_rate": safe_mean(solution_harms),
        "no_solution_rate": safe_mean(no_solution),
        "total_harmful_rate": safe_mean(total_harms),
        "false_positive_count": int(sum(total_harms)),
        "solution_quality_false_positive_count": int(sum(solution_harms)),
        "no_solution_count": int(sum(no_solution)),
        "helpful_vs_static_rate": safe_mean(helpfuls),
        "coverage": safe_mean(nonstatic),
        "fallback_rate": 1.0 - safe_mean(nonstatic),
        "new_candidate_selection_rate": safe_mean(new_flags),
        "new_candidate_selection_count": int(sum(new_flags)),
        "new_candidate_helpful_selection_count": int(sum(new_help)),
        "new_candidate_harmful_selection_count": int(sum(new_harm)),
        "new_candidate_selection_harmful_rate": len(new_harm) / int(sum(new_flags)) if int(sum(new_flags)) else 0.0,
        "new_candidate_opportunity_contexts": len(new_opp_contexts),
        "new_candidate_opportunity_capture_count": int(sum(new_opp_capture)),
        "new_candidate_opportunity_capture_rate": (
            int(sum(new_opp_capture)) / len(new_opp_contexts) if new_opp_contexts else 0.0
        ),
        "oracle_regret_vs_old14": safe_mean(old14_regrets),
        "oracle_regret_vs_new22": safe_mean(new22_regrets),
        "finite_delta_contexts": len(finite_deltas),
    }
    for lam in RISK_LAMBDAS:
        suffix = suffix_for_lambda(lam)
        row[f"risk_adjusted_utility_lambda_{suffix}"] = (
            finite_number(row["mean_solution_quality_delta_vs_static"], 0.0)
            + lam * finite_number(row["total_harmful_rate"], math.inf)
        )
        row[f"solution_quality_utility_lambda_{suffix}"] = (
            finite_number(row["mean_solution_quality_delta_vs_static"], 0.0)
            + lam * finite_number(row["solution_quality_harmful_rate"], math.inf)
        )
    return row


def context_decision_row_corrected(
    policy: str,
    selected: dict[str, Any],
    *,
    eval_scope: str,
    fold_id: str = "",
    selection_reason: str = "",
    predicted_delta: Any = "",
    predicted_risk: Any = "",
    predicted_new_opportunity_prob: Any = "",
    predicted_margin: Any = "",
    predicted_best_candidate_id: str = "",
) -> dict[str, Any]:
    return {
        "row_type": "context_decision",
        "eval_scope": eval_scope,
        "fold_id": fold_id,
        "policy": policy,
        "normalized_context_key": selected.get("normalized_context_key", ""),
        "map": selected.get("map", ""),
        "agents": selected.get("agents", ""),
        "seed": selected.get("seed", ""),
        "iteration": selected.get("iteration", ""),
        "traffic_before_hash_full": selected.get("traffic_before_hash_full", ""),
        "selected_candidate_id": selected.get("candidate_id", ""),
        "selected_candidate_family": selected.get("candidate_family", ""),
        "selected_candidate_source": selected.get("candidate_source", ""),
        "is_new_candidate": selected.get("is_new_candidate", ""),
        "selection_reason": selection_reason,
        "predicted_delta": predicted_delta,
        "predicted_harmful_risk": predicted_risk,
        "predicted_new_opportunity_prob": predicted_new_opportunity_prob,
        "predicted_margin": predicted_margin,
        "predicted_best_candidate_id": predicted_best_candidate_id,
        "solution_quality_delta_vs_static": selected.get("solution_quality_delta_vs_static", ""),
        "solution_quality_harmful_vs_static": selected.get("solution_quality_harmful_vs_static", ""),
        "no_solution_or_infeasible": selected.get("no_solution_or_infeasible", ""),
        "budget_nonfinite": selected.get("budget_nonfinite", ""),
        "total_harmful": selected.get("harmful_total", ""),
        "helpful_vs_static_corrected": selected.get("helpful_vs_static_corrected", ""),
        "old14_oracle_regret_primary": selected.get("old14_oracle_regret_primary", ""),
        "new22_oracle_regret_primary": selected.get("new22_oracle_regret_primary", ""),
        "oracle_candidate_old14_for_context": selected.get("oracle_candidate_old14_for_context", ""),
        "oracle_candidate_new22_for_context": selected.get("oracle_candidate_new22_for_context", ""),
        "oracle_new_candidate_for_context": selected.get("oracle_new_candidate_for_context", ""),
        "new_candidate_best_gap_vs_old14": selected.get("new_candidate_best_gap_vs_old14", ""),
        "new_opportunity_context": selected.get("new_opportunity_context", ""),
        "new_opportunity_candidate": selected.get("new_opportunity_candidate", ""),
        "safe_new_candidate_positive": selected.get("safe_new_candidate_positive", ""),
    }


def best_primary_policy(summary_rows: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [
        row
        for row in summary_rows
        if row.get("row_type") == "policy_summary"
        and row.get("eval_scope") == "seed_oof"
        and str(row.get("policy", "")) not in PRIMARY_POLICY_EXCLUSIONS
    ]
    return min(
        candidates,
        key=lambda row: (
            finite_number(row.get("risk_adjusted_utility_lambda_0p10"), math.inf),
            finite_number(row.get("total_harmful_rate"), math.inf),
            -finite_number(row.get("new_candidate_opportunity_capture_rate"), 0.0),
            str(row.get("policy", "")),
        ),
    ) if candidates else {}


def bootstrap_rows_corrected(policy_selected: dict[str, list[dict[str, Any]]], *, samples: int = 300, seed: int = SEED) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    metrics = [
        "mean_solution_quality_delta_vs_static",
        "solution_quality_harmful_rate",
        "no_solution_rate",
        "total_harmful_rate",
        "new_candidate_selection_rate",
        "new_candidate_opportunity_capture_rate",
        "oracle_regret_vs_new22",
        "risk_adjusted_utility_lambda_0p10",
    ]
    out: list[dict[str, Any]] = []
    for policy, rows in sorted(policy_selected.items()):
        if not rows:
            continue
        values_by_metric = {metric: [] for metric in metrics}
        for _ in range(samples):
            sample = [rows[rng.randrange(len(rows))] for _ in rows]
            summary = policy_metric_row_corrected(policy, sample, eval_scope="bootstrap")
            for metric in metrics:
                values_by_metric[metric].append(finite_number(summary.get(metric), math.nan))
        for metric, values in values_by_metric.items():
            finite = sorted(value for value in values if math.isfinite(value))
            low_index = int(max(0, min(len(finite) - 1, math.floor((len(finite) - 1) * 0.025)))) if finite else 0
            high_index = int(max(0, min(len(finite) - 1, math.ceil((len(finite) - 1) * 0.975)))) if finite else 0
            out.append(
                {
                    "row_type": "bootstrap_ci",
                    "policy": policy,
                    "metric": metric,
                    "estimate": safe_mean(values),
                    "ci_low": finite[low_index] if finite else "",
                    "ci_high": finite[high_index] if finite else "",
                    "samples": samples,
                }
            )
    return out


def calibration_rows_corrected(context_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bins = [(0.0, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.50), (0.50, 1.01)]
    out: list[dict[str, Any]] = []
    policies = sorted({str(row.get("policy", "")) for row in context_rows if row.get("eval_scope") == "seed_oof"})
    for policy in policies:
        rows = [row for row in context_rows if row.get("policy") == policy and row.get("eval_scope") == "seed_oof"]
        for low, high in bins:
            bucket = [
                row
                for row in rows
                if low <= max(0.0, min(1.0, finite_number(row.get("predicted_harmful_risk"), math.nan))) < high
            ]
            preds = [max(0.0, min(1.0, finite_number(row.get("predicted_harmful_risk"), math.nan))) for row in bucket]
            actual = [1.0 if boolish(row.get("total_harmful")) else 0.0 for row in bucket]
            out.append(
                {
                    "row_type": "total_harm_calibration_bucket",
                    "policy": policy,
                    "risk_bucket_low": low,
                    "risk_bucket_high": high,
                    "contexts": len(bucket),
                    "mean_predicted_total_harmful_risk": safe_mean(preds),
                    "actual_total_harmful_rate": safe_mean(actual),
                    "ece_abs_error": abs(safe_mean(preds) - safe_mean(actual)) if bucket else "",
                }
            )
    return out


def group_diagnostic_rows(policy_selected: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for policy, rows in sorted(policy_selected.items()):
        for group_type in ["map_agent", "map_family", "candidate_family"]:
            grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in rows:
                if group_type == "map_agent":
                    key = map_agent_key(row)
                elif group_type == "map_family":
                    key = map_family_key(row)
                else:
                    key = str(row.get("candidate_family", ""))
                grouped[key].append(row)
            for key, group in sorted(grouped.items()):
                metric = policy_metric_row_corrected(policy, group, eval_scope=f"group_{group_type}")
                metric["row_type"] = "group_summary"
                metric["group_type"] = group_type
                metric["group_key"] = key
                out.append(metric)
    return out


def compact_counter(rows: Iterable[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field, "")) for row in rows).items()))


__all__ = [
    name
    for name in globals()
    if name.startswith("G520_")
    or name.startswith("G519_")
    or name.isupper()
    or name
    in {
        "ADDITIVE_CANDIDATE",
        "DEFAULT_MARGIN",
        "PRIMARY_POLICY_EXCLUSIONS",
        "RISK_LAMBDAS",
        "SEED",
        "STATIC_FLOW_SHIELD_CANDIDATE",
        "as_jsonable",
        "best_primary_policy",
        "boolish",
        "bootstrap_rows_corrected",
        "calibration_rows_corrected",
        "candidate_param_feature_columns",
        "candidate_params",
        "candidate_train_stats",
        "compact_counter",
        "context_candidate_budget_key",
        "context_decision_row_corrected",
        "context_feature_columns",
        "corrected_delta",
        "csv_number",
        "enforce_reserved_guard_rejects_166",
        "family_for_candidate",
        "feature_columns",
        "finite_number",
        "fit_ridge",
        "forbidden_feature_scan",
        "g520_perf_feature_columns",
        "g520_ranker_feature_columns",
        "group_diagnostic_rows",
        "helpful",
        "leakage_scan",
        "map_agent_key",
        "map_family",
        "map_family_key",
        "matrix",
        "mean",
        "nearest_old_candidate",
        "no_new_source_feature_columns",
        "no_rich_interaction_feature_columns",
        "no_solution_risk",
        "numeric_candidate_param_dict",
        "numeric_target",
        "observed_id_flags",
        "observed_id_guard",
        "old14_candidate_ids",
        "oracle_new22_row",
        "oracle_old14_row",
        "policy_metric_row_corrected",
        "predict_ridge",
        "random_feature_matrix",
        "read_json_file",
        "read_rows",
        "repo_root",
        "resolve",
        "row_key",
        "rows_by_context",
        "safe_mean",
        "sample_weights",
        "select_candidate",
        "selected_for_fixed",
        "solution_harmful",
        "suffix_for_lambda",
        "total_harmful",
        "write_json_file",
        "write_rows",
        "write_text_file",
    }
]

"""Shared helpers for Repair5G.5.16 error-driven safety-bound diagnostics."""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from repair5g512_common import (  # noqa: E402
    ADDITIVE_CANDIDATE,
    DEFAULT_MARGIN,
    SLOW_DECAY_HIGH_SHIELD_CANDIDATE,
    STATIC_FLOW_SHIELD_CANDIDATE,
    finite_number,
    mean,
    read_csv_rows,
    read_json,
    repo_root,
    resolve,
)
from repair5g513_common import grouped_contexts, select_candidate  # noqa: E402
from repair5g515_common import context_row, feature_columns, policy_summary  # noqa: E402
from train_repair5g512_candidate_regret_ranker import fit_ridge, matrix, predict_model, row_key, weights  # noqa: E402


G516_CLOSED_CLAIMS = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "aaai_ready": False,
    "runtime_claim_allowed": False,
    "learned_runtime_policy_validated": False,
}

DEFAULT_G515_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g515_decision_summary.json"
DEFAULT_G515_V5_MATRIX = "outputs/tables/phase5p5_repair5g515_candidate_feature_matrix_v5.csv"
DEFAULT_G515_CONTEXT_DECISIONS = "outputs/tables/phase5p5_repair5g515_calibrated_interaction_ranker_context_decisions.csv"
DEFAULT_G515_EVAL_SUMMARY = "outputs/reports/phase5p5_repair5g515_calibrated_interaction_rankers_summary.json"
DEFAULT_G515_FALSE_POSITIVE_SUMMARY = "outputs/reports/phase5p5_repair5g515_false_positive_autopsy_summary.json"
DEFAULT_G515_SAFETY_SUMMARY = "outputs/reports/phase5p5_repair5g515_static_abstention_safety_update_summary.json"
DEFAULT_G515_V5_SUMMARY = "outputs/reports/phase5p5_repair5g515_candidate_feature_matrix_v5_summary.json"

DEFAULT_G516_ERROR_BANK = "outputs/tables/phase5p5_repair5g516_error_bank.csv"
DEFAULT_G516_ERROR_BANK_SUMMARY = "outputs/reports/phase5p5_repair5g516_error_bank_summary.json"
DEFAULT_G516_LATTICE = "outputs/tables/phase5p5_repair5g516_targeted_repair_lattice.csv"
DEFAULT_G516_LATTICE_SUMMARY = "outputs/reports/phase5p5_repair5g516_targeted_repair_lattice_summary.json"
DEFAULT_G516_PROBE_PLAN = "outputs/tables/phase5p5_repair5g516_local_targeted_probe_plan.csv"
DEFAULT_G516_PROBE_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g516_local_targeted_probe_plan_summary.json"
DEFAULT_G516_V6_MATRIX = "outputs/tables/phase5p5_repair5g516_candidate_feature_matrix_v6.csv"
DEFAULT_G516_V6_SUMMARY = "outputs/reports/phase5p5_repair5g516_candidate_feature_matrix_v6_summary.json"
DEFAULT_G516_MODEL = "outputs/reports/phase5p5_repair5g516_pessimistic_safety_bound_ranker_model.json"
DEFAULT_G516_EVAL_CONTEXTS = "outputs/tables/phase5p5_repair5g516_pessimistic_ranker_context_decisions.csv"
DEFAULT_G516_EVAL_SUMMARY = "outputs/reports/phase5p5_repair5g516_pessimistic_rankers_summary.json"

ERROR_FEATURE_COLUMNS = {
    "harmful_false_positive": "feature_error_bank_harmful_fp_context",
    "missed_helpful_fallback": "feature_error_bank_missed_helpful_context",
    "static_near_oracle": "feature_error_bank_static_boundary_context",
    "high_uncertainty": "feature_error_bank_high_uncertainty_context",
}

PROMOTION_HARMFUL_LIMIT = 0.03333333333333333
SEED = 20260608


VARIANT_CONFIGS: dict[str, dict[str, Any]] = {
    "ultra_safe_bound": {
        "residual_quantile": 0.95,
        "risk_threshold": PROMOTION_HARMFUL_LIMIT,
        "delta_margin": 0.010,
        "pairwise_margin_threshold": 0.005,
        "block_high_uncertainty": True,
        "high_uncertainty_risk_threshold": 0.020,
        "high_uncertainty_margin_threshold": 0.015,
        "static_boundary_override_delta": 0.020,
        "static_boundary_override_margin": 0.010,
        "diagnostic_only": False,
    },
    "balanced_bound": {
        "residual_quantile": 0.90,
        "risk_threshold": 0.050,
        "delta_margin": DEFAULT_MARGIN,
        "pairwise_margin_threshold": 0.002,
        "block_high_uncertainty": True,
        "high_uncertainty_risk_threshold": PROMOTION_HARMFUL_LIMIT,
        "high_uncertainty_margin_threshold": 0.010,
        "static_boundary_override_delta": 0.015,
        "static_boundary_override_margin": 0.006,
        "diagnostic_only": False,
    },
    "opportunity_diagnostic_not_for_promotion": {
        "residual_quantile": 0.80,
        "risk_threshold": 0.100,
        "delta_margin": DEFAULT_MARGIN,
        "pairwise_margin_threshold": 0.0,
        "block_high_uncertainty": False,
        "high_uncertainty_risk_threshold": 0.100,
        "high_uncertainty_margin_threshold": 0.0,
        "static_boundary_override_delta": DEFAULT_MARGIN,
        "static_boundary_override_margin": 0.0,
        "diagnostic_only": True,
    },
}


def maybe_read_json(path: str | Path) -> dict[str, Any]:
    target = resolve(path, repo_root())
    return read_json(target) if target.exists() else {}


def maybe_read_csv(path: str | Path) -> list[dict[str, Any]]:
    target = resolve(path, repo_root())
    return read_csv_rows(target) if target.exists() else []


def g516_feature_names(rows: list[dict[str, Any]], *, include_error_bank: bool = True) -> list[str]:
    names = feature_columns(rows)
    if include_error_bank:
        return names
    return [name for name in names if not name.startswith("feature_error_bank_")]


def strip_g516_error_features(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {key: value for key, value in row.items() if not key.startswith("feature_error_bank_")}
        for row in rows
    ]


def quantile(values: Iterable[float], q: float) -> float:
    finite = sorted(value for value in values if math.isfinite(value))
    if not finite:
        return 0.0
    if q <= 0:
        return finite[0]
    if q >= 1:
        return finite[-1]
    index = int(math.ceil(q * len(finite))) - 1
    return finite[max(0, min(index, len(finite) - 1))]


def risk_adjusted_metric(row: dict[str, Any], suffix: str = "0p10") -> float:
    return finite_number(row.get(f"risk_adjusted_utility_lambda_{suffix}"), math.inf)


def fit_pessimistic_model(
    train_rows: list[dict[str, Any]],
    *,
    feature_names: list[str],
    ridge_alpha: float,
    model_type: str,
) -> dict[str, Any]:
    X = matrix(train_rows, feature_names)
    y_delta = np.array([finite_number(row.get("mean_delta_vs_static_primary"), math.nan) for row in train_rows], dtype=float)
    y_risk = np.array(
        [1.0 if finite_number(row.get("mean_delta_vs_static_primary"), math.inf) >= DEFAULT_MARGIN else 0.0 for row in train_rows],
        dtype=float,
    )
    w = weights(train_rows)
    delta_model = fit_ridge(X, y_delta, w, ridge_alpha)
    risk_model = fit_ridge(X, y_risk, w, ridge_alpha)
    pred_delta = predict_model(delta_model, X)
    pred_risk = np.clip(predict_model(risk_model, X), 0.0, 1.0)
    delta_abs_resid = [abs(float(actual - pred)) for actual, pred in zip(y_delta, pred_delta) if math.isfinite(actual)]
    risk_upper_resid = [
        max(0.0, float(actual - pred))
        for actual, pred in zip(y_risk, pred_risk)
        if math.isfinite(actual)
    ]
    quantiles = sorted({0.0, 0.80, 0.90, 0.95})
    return {
        "schema_version": "phase5p5_repair5g516_pessimistic_safety_bound_ranker_model_v1",
        "model_type": model_type,
        "feature_names": feature_names,
        "ridge_alpha": ridge_alpha,
        "delta_model": delta_model,
        "risk_model": risk_model,
        "delta_abs_residual_quantiles": {str(q): quantile(delta_abs_resid, q) for q in quantiles},
        "risk_upper_residual_quantiles": {str(q): quantile(risk_upper_resid, q) for q in quantiles},
        "train_rows": len(train_rows),
        "seed": SEED,
        **G516_CLOSED_CLAIMS,
    }


def predict_components(rows: list[dict[str, Any]], model: dict[str, Any]) -> dict[str, dict[str, float]]:
    X = matrix(rows, list(model["feature_names"]))
    pred_delta = predict_model(model["delta_model"], X)
    pred_risk = np.clip(predict_model(model["risk_model"], X), 0.0, 1.0)
    return {
        row_key(row): {"predicted_delta": float(delta), "predicted_risk": float(risk)}
        for row, delta, risk in zip(rows, pred_delta, pred_risk)
    }


def _quantile_key(value: float) -> str:
    return str(float(value))


def bound_scores_for_row(row: dict[str, Any], pred: dict[str, dict[str, float]], model: dict[str, Any], config: dict[str, Any]) -> dict[str, float]:
    q = float(config["residual_quantile"])
    key = _quantile_key(q)
    parts = pred[row_key(row)]
    delta_resid = finite_number(model.get("delta_abs_residual_quantiles", {}).get(key), 0.0)
    risk_resid = finite_number(model.get("risk_upper_residual_quantiles", {}).get(key), 0.0)
    return {
        "predicted_delta": parts["predicted_delta"],
        "predicted_risk": parts["predicted_risk"],
        "delta_pessimistic_bound": parts["predicted_delta"] + delta_resid,
        "risk_upper_bound": min(1.0, max(0.0, parts["predicted_risk"] + risk_resid)),
    }


def is_error_flag(row: dict[str, Any], column: str) -> bool:
    return finite_number(row.get(column), 0.0) > 0.5


def select_pessimistic_policy(
    rows: list[dict[str, Any]],
    model: dict[str, Any],
    *,
    policy: str,
    config: dict[str, Any],
    eval_scope: str,
    fold_seed: int | str | None = None,
    ignore_error_bank_gates: bool = False,
    use_bounds: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pred = predict_components(rows, model)
    selected: list[dict[str, Any]] = []
    context_rows: list[dict[str, Any]] = []
    local_config = dict(config)
    if not use_bounds:
        local_config["residual_quantile"] = 0.0
    for _, group in sorted(grouped_contexts(rows).items()):
        static = select_candidate(group, STATIC_FLOW_SHIELD_CANDIDATE)
        scored = []
        for row in group:
            scores = bound_scores_for_row(row, pred, model, local_config)
            scored.append((row, scores))
        ranked = sorted(
            scored,
            key=lambda item: (
                item[1]["delta_pessimistic_bound"],
                item[1]["risk_upper_bound"],
                str(item[0].get("candidate_id", "")),
            ),
        )
        best, best_scores = ranked[0]
        second_bound = ranked[1][1]["delta_pessimistic_bound"] if len(ranked) > 1 else math.inf
        margin = second_bound - best_scores["delta_pessimistic_bound"]
        high_uncertainty = (not ignore_error_bank_gates) and is_error_flag(best, ERROR_FEATURE_COLUMNS["high_uncertainty"])
        static_boundary = (not ignore_error_bank_gates) and is_error_flag(best, ERROR_FEATURE_COLUMNS["static_near_oracle"])
        high_uncertainty_ok = (
            not high_uncertainty
            or not local_config.get("block_high_uncertainty", False)
            or (
                best_scores["risk_upper_bound"] <= local_config["high_uncertainty_risk_threshold"]
                and margin >= local_config["high_uncertainty_margin_threshold"]
            )
        )
        static_boundary_ok = (
            not static_boundary
            or (
                best_scores["delta_pessimistic_bound"] <= -local_config["static_boundary_override_delta"]
                and margin >= local_config["static_boundary_override_margin"]
            )
        )
        allowed = (
            str(best.get("candidate_id", "")) != STATIC_FLOW_SHIELD_CANDIDATE
            and best_scores["risk_upper_bound"] <= local_config["risk_threshold"]
            and best_scores["delta_pessimistic_bound"] <= -local_config["delta_margin"]
            and margin >= local_config["pairwise_margin_threshold"]
            and high_uncertainty_ok
            and static_boundary_ok
        )
        choice = best if allowed else static
        if allowed:
            reason = "selected_pessimistic_bound_best"
        elif str(best.get("candidate_id", "")) == STATIC_FLOW_SHIELD_CANDIDATE:
            reason = "fallback_static_ranked_best"
        elif not static_boundary_ok:
            reason = "fallback_static_boundary_block"
        elif not high_uncertainty_ok:
            reason = "fallback_high_uncertainty_bound_block"
        elif best_scores["risk_upper_bound"] > local_config["risk_threshold"]:
            reason = "fallback_risk_upper_bound"
        elif best_scores["delta_pessimistic_bound"] > -local_config["delta_margin"]:
            reason = "fallback_delta_bound_margin"
        else:
            reason = "fallback_pairwise_margin"
        selected.append(choice)
        context_rows.append(
            context_row(
                policy,
                choice,
                reason,
                eval_scope=eval_scope,
                fold_seed=fold_seed,
                predicted_best_delta=best_scores["predicted_delta"],
                predicted_best_harmful_risk=best_scores["predicted_risk"],
                predicted_margin=margin,
                extra={
                    "predicted_best_candidate_id": best.get("candidate_id", ""),
                    "delta_pessimistic_bound": best_scores["delta_pessimistic_bound"],
                    "risk_upper_bound": best_scores["risk_upper_bound"],
                    "bound_residual_quantile": local_config["residual_quantile"],
                    "high_uncertainty_context": high_uncertainty,
                    "static_boundary_context": static_boundary,
                    "diagnostic_only": bool(local_config.get("diagnostic_only", False)),
                },
            )
        )
    return selected, context_rows


def selected_diagnostic_counts(selected: list[dict[str, Any]], universe_rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups = grouped_contexts(universe_rows)
    false_positive_count = 0
    missed_helpful_count = 0
    static_near_contexts = 0
    static_near_nonstatic_selected = 0
    for row in selected:
        key = str(row.get("normalized_context_key", ""))
        group = groups.get(key, [])
        if not group:
            continue
        selected_id = str(row.get("candidate_id", ""))
        selected_delta = finite_number(row.get("mean_delta_vs_static_primary"), math.inf)
        if selected_id != STATIC_FLOW_SHIELD_CANDIDATE and selected_delta >= DEFAULT_MARGIN:
            false_positive_count += 1
        oracle_id = str(row.get("oracle_candidate_for_context", ""))
        oracle = select_candidate(group, oracle_id)
        oracle_delta = finite_number(oracle.get("mean_delta_vs_static_primary"), math.inf)
        if selected_id == STATIC_FLOW_SHIELD_CANDIDATE and oracle_id != STATIC_FLOW_SHIELD_CANDIDATE and oracle_delta <= -DEFAULT_MARGIN:
            missed_helpful_count += 1
        static = select_candidate(group, STATIC_FLOW_SHIELD_CANDIDATE)
        if finite_number(static.get("oracle_regret_primary"), math.inf) <= DEFAULT_MARGIN:
            static_near_contexts += 1
            if selected_id != STATIC_FLOW_SHIELD_CANDIDATE:
                static_near_nonstatic_selected += 1
    return {
        "false_positive_count": false_positive_count,
        "missed_helpful_count": missed_helpful_count,
        "static_near_oracle_contexts": static_near_contexts,
        "static_near_oracle_nonstatic_selected": static_near_nonstatic_selected,
    }


def policy_summary_extended(policy: str, selected: list[dict[str, Any]], universe_rows: list[dict[str, Any]]) -> dict[str, Any]:
    row = policy_summary(policy, selected)
    row.update(selected_diagnostic_counts(selected, universe_rows))
    return row


def add_scope_to_extended_summaries(scope: str, summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in summaries:
        item = dict(row)
        item["eval_scope"] = scope
        out.append(item)
    return out


def harmful_candidate_rows(policy_selected: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for policy, selected in sorted(policy_selected.items()):
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in selected:
            grouped[str(row.get("candidate_id", ""))].append(row)
        for candidate, values in sorted(grouped.items()):
            harmful = [
                1.0 if finite_number(row.get("mean_delta_vs_static_primary"), math.inf) >= DEFAULT_MARGIN else 0.0
                for row in values
            ]
            out.append(
                {
                    "row_type": "harmful_count",
                    "policy": policy,
                    "group_type": "candidate",
                    "group_key": candidate,
                    "contexts": len(values),
                    "harmful_contexts": int(sum(harmful)),
                    "harmful_vs_static_rate": mean(harmful),
                }
            )
    return out


def rename_policy_selected(
    selected: dict[str, list[dict[str, Any]]],
    context_rows: list[dict[str, Any]],
    rename: dict[str, str],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    out_selected: dict[str, list[dict[str, Any]]] = {}
    for policy, rows in selected.items():
        out_selected[rename.get(policy, policy)] = rows
    out_contexts = []
    for row in context_rows:
        item = dict(row)
        item["policy"] = rename.get(str(row.get("policy", "")), str(row.get("policy", "")))
        out_contexts.append(item)
    return out_selected, out_contexts


def simple_selected_for_candidate(rows: list[dict[str, Any]], candidate_id: str) -> list[dict[str, Any]]:
    return [select_candidate(group, candidate_id) for _, group in sorted(grouped_contexts(rows).items())]


def current_candidate_ids(rows: list[dict[str, Any]]) -> list[str]:
    return sorted({str(row.get("candidate_id", "")) for row in rows if row.get("candidate_id")})


def map_agent_key(row: dict[str, Any]) -> str:
    return f"{row.get('map', '')}|a{row.get('agents', '')}"


def context_prefix(row: dict[str, Any]) -> str:
    return f"{row.get('map', '')}|a{row.get('agents', '')}|s{row.get('seed', '')}"


def safe_int(value: Any, default: int = -1) -> int:
    numeric = finite_number(value, math.nan)
    return int(numeric) if math.isfinite(numeric) else default

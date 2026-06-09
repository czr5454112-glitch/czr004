"""Train and evaluate G5.21 split opportunity selectors."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g521_common import (  # noqa: E402
    DEFAULT_MARGIN,
    G521_CANDIDATE_FEATURES_CSV,
    G521_CLOSED_CLAIMS,
    G521_CONTEXT_FEATURES_CSV,
    G521_FAMILY_FEATURES_CSV,
    G521_FEATURES_SUMMARY,
    G521_SELECTOR_BOOTSTRAP_CSV,
    G521_SELECTOR_CALIBRATION_CSV,
    G521_SELECTOR_CONTEXT_DECISIONS_CSV,
    G521_SELECTOR_DIAGNOSTICS_CSV,
    G521_SELECTOR_EVAL_CSV,
    G521_SELECTOR_REPORT,
    G521_SELECTOR_SUMMARY,
    G521_TARGETS_SUMMARY,
    SEED,
    STATIC_FLOW_SHIELD_CANDIDATE,
    boolish,
    csv_number,
    feature_columns,
    finite_number,
    leakage_scan,
    map_agent_key,
    map_family_key,
    matrix,
    mean,
    read_json_file,
    read_rows,
    rows_by_context,
    suffix_for_lambda,
    write_json_file,
    write_rows,
    write_text_file,
)


REQUIRED_POLICIES = [
    "static_flow_shield",
    "old14_only_ranker_v10",
    "g51822_only_ranker_v10",
    "g521_full_candidate_ranker_v10",
    "context_gate_then_new_ranker",
    "context_gate_then_family_gate_then_candidate_ranker",
    "nearest_old_residual_new_selector",
    "static_recovery_selector",
    "candidate_induced_failure_guard_selector",
    "conformal_abstention_selector",
    "small_tree_interpretable_selector",
    "train_only_map_agent_prior",
    "train_only_family_prior",
    "new_candidate_only_oracle_diagnostic",
    "source_blind_ablation",
    "no_rich_interaction_ablation",
    "label_shuffled_context_gate",
    "label_shuffled_candidate_ranker",
    "random_feature_model",
    "no_new_candidate_ablation",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-features-csv", type=Path, default=Path(G521_CONTEXT_FEATURES_CSV))
    parser.add_argument("--family-features-csv", type=Path, default=Path(G521_FAMILY_FEATURES_CSV))
    parser.add_argument("--candidate-features-csv", type=Path, default=Path(G521_CANDIDATE_FEATURES_CSV))
    parser.add_argument("--output-csv", type=Path, default=Path(G521_SELECTOR_EVAL_CSV))
    parser.add_argument("--context-decisions-csv", type=Path, default=Path(G521_SELECTOR_CONTEXT_DECISIONS_CSV))
    parser.add_argument("--bootstrap-csv", type=Path, default=Path(G521_SELECTOR_BOOTSTRAP_CSV))
    parser.add_argument("--calibration-csv", type=Path, default=Path(G521_SELECTOR_CALIBRATION_CSV))
    parser.add_argument("--diagnostics-csv", type=Path, default=Path(G521_SELECTOR_DIAGNOSTICS_CSV))
    parser.add_argument("--report", type=Path, default=Path(G521_SELECTOR_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G521_SELECTOR_SUMMARY))
    parser.add_argument("--bootstrap-samples", type=int, default=300)
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    return parser.parse_args(argv)


def row_seed(row: dict[str, Any]) -> int:
    return int(finite_number(row.get("seed"), -1))


def row_key(row: dict[str, Any]) -> str:
    return f"{row.get('normalized_context_key', '')}|{row.get('candidate_id', '')}"


def candidate_features(rows: list[dict[str, Any]], *, source_blind: bool = False, no_rich: bool = False) -> list[str]:
    cols = feature_columns(rows)
    if source_blind:
        cols = [col for col in cols if "role_" not in col and "source" not in col and "g521" not in col and "g518" not in col]
    if no_rich:
        cols = [col for col in cols if "rich_" not in col]
    return cols


def fit_ridge_model(rows: list[dict[str, Any]], features: list[str], y: np.ndarray, alpha: float) -> dict[str, Any]:
    if not rows or not features:
        return {"features": features, "coef": [], "intercept": float(np.mean(y)) if len(y) else 0.0}
    x = matrix(rows, features)
    x_aug = np.column_stack([np.ones(x.shape[0]), x])
    reg = np.eye(x_aug.shape[1]) * alpha
    reg[0, 0] = 0.0
    coef = np.linalg.pinv(x_aug.T @ x_aug + reg) @ x_aug.T @ y
    return {"features": features, "intercept": float(coef[0]), "coef": [float(value) for value in coef[1:]]}


def predict_model(rows: list[dict[str, Any]], model: dict[str, Any]) -> np.ndarray:
    if not rows:
        return np.array([], dtype=float)
    features = list(model.get("features", []))
    if not features:
        return np.full(len(rows), float(model.get("intercept", 0.0)), dtype=float)
    x = matrix(rows, features)
    coef = np.array(model.get("coef", []), dtype=float)
    return float(model.get("intercept", 0.0)) + x @ coef


def random_feature_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    rng = random.Random(SEED)
    weights = {i: rng.uniform(-1.0, 1.0) for i in range(6)}
    for row in rows:
        key = hash(row_key(row)) & 0xFFFFFFFF
        actual = dict(row)
        for i in range(6):
            actual[f"feature_random_{i}"] = ((key >> (i * 5)) & 31) / 31.0 + weights[i] * 0.01
        out.append(actual)
    return out


def fit_bundle(
    train_context: list[dict[str, Any]],
    train_family: list[dict[str, Any]],
    train_candidate: list[dict[str, Any]],
    *,
    alpha: float,
    source_blind: bool = False,
    no_rich: bool = False,
    random_features: bool = False,
    shuffle_context: bool = False,
    shuffle_candidate: bool = False,
) -> dict[str, Any]:
    rng = random.Random(SEED + 521)
    context_cols = feature_columns(train_context)
    family_cols = feature_columns(train_family)
    cand_rows = random_feature_rows(train_candidate) if random_features else train_candidate
    cand_cols = [f"feature_random_{i}" for i in range(6)] if random_features else candidate_features(cand_rows, source_blind=source_blind, no_rich=no_rich)
    y_context = [1.0 if boolish(row.get("context_has_new_beats_old14_opportunity")) else 0.0 for row in train_context]
    y_recovery_context = [1.0 if boolish(row.get("context_has_static_failure_recovery_candidate")) else 0.0 for row in train_context]
    y_family = [1.0 if boolish(row.get("family_contains_new_candidate_beating_old14")) else 0.0 for row in train_family]
    y_family_risk = [1.0 if boolish(row.get("family_contains_candidate_induced_failure")) else 0.0 for row in train_family]
    y_delta = [finite_number(row.get("finite_pairwise_delta_vs_static_primary"), 0.25) for row in train_candidate]
    y_risk = [
        1.0
        if boolish(row.get("candidate_induced_no_solution"))
        or boolish(row.get("solution_quality_harm_on_finite_pairs"))
        or boolish(row.get("budget_sensitive_candidate_failure"))
        else 0.0
        for row in train_candidate
    ]
    y_recovery = [1.0 if boolish(row.get("candidate_recovers_static_no_solution")) else 0.0 for row in train_candidate]
    if shuffle_context:
        rng.shuffle(y_context)
    if shuffle_candidate:
        rng.shuffle(y_delta)
        rng.shuffle(y_risk)
    bundle = {
        "context_features": context_cols,
        "family_features": family_cols,
        "candidate_features": cand_cols,
        "random_features": random_features,
        "context_opportunity": fit_ridge_model(train_context, context_cols, np.array(y_context, dtype=float), alpha),
        "context_recovery": fit_ridge_model(train_context, context_cols, np.array(y_recovery_context, dtype=float), alpha),
        "family_opportunity": fit_ridge_model(train_family, family_cols, np.array(y_family, dtype=float), alpha),
        "family_risk": fit_ridge_model(train_family, family_cols, np.array(y_family_risk, dtype=float), alpha),
        "candidate_delta": fit_ridge_model(cand_rows, cand_cols, np.array(y_delta, dtype=float), alpha),
        "candidate_risk": fit_ridge_model(cand_rows, cand_cols, np.array(y_risk, dtype=float), alpha),
        "candidate_recovery": fit_ridge_model(cand_rows, cand_cols, np.array(y_recovery, dtype=float), alpha),
        "thresholds": {
            "context_opportunity": max(0.25, mean(y_context)),
            "family_opportunity": max(0.25, mean(y_family)),
            "risk": 0.20,
            "strict_risk": 0.10,
            "conformal_margin": 0.002,
        },
    }
    return bundle


def bundle_predictions(bundle: dict[str, Any], context_rows: list[dict[str, Any]], family_rows: list[dict[str, Any]], candidate_rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    cand_rows = random_feature_rows(candidate_rows) if bundle.get("random_features") else candidate_rows
    return {
        "context_opportunity": {str(row.get("normalized_context_key", "")): float(value) for row, value in zip(context_rows, np.clip(predict_model(context_rows, bundle["context_opportunity"]), 0.0, 1.0))},
        "context_recovery": {str(row.get("normalized_context_key", "")): float(value) for row, value in zip(context_rows, np.clip(predict_model(context_rows, bundle["context_recovery"]), 0.0, 1.0))},
        "family_opportunity": {f"{row.get('normalized_context_key', '')}|{row.get('candidate_family', '')}": float(value) for row, value in zip(family_rows, np.clip(predict_model(family_rows, bundle["family_opportunity"]), 0.0, 1.0))},
        "family_risk": {f"{row.get('normalized_context_key', '')}|{row.get('candidate_family', '')}": float(value) for row, value in zip(family_rows, np.clip(predict_model(family_rows, bundle["family_risk"]), 0.0, 1.0))},
        "candidate_delta": {row_key(row): float(value) for row, value in zip(candidate_rows, predict_model(cand_rows, bundle["candidate_delta"]))},
        "candidate_risk": {row_key(row): float(value) for row, value in zip(candidate_rows, np.clip(predict_model(cand_rows, bundle["candidate_risk"]), 0.0, 1.0))},
        "candidate_recovery": {row_key(row): float(value) for row, value in zip(candidate_rows, np.clip(predict_model(cand_rows, bundle["candidate_recovery"]), 0.0, 1.0))},
    }


def candidate_filter(row: dict[str, Any], kind: str) -> bool:
    role = str(row.get("candidate_role", ""))
    if kind == "old14":
        return role == "old14"
    if kind == "g51822":
        return role in {"old14", "g518_retained"}
    if kind == "new":
        return role in {"g518_retained", "g521_second_wave"}
    if kind == "no_new":
        return role == "old14"
    return True


def choose_ranked(group: list[dict[str, Any]], pred: dict[str, dict[str, float]], *, kind: str = "all", risk_threshold: float = 0.20, require_recovery: bool = False) -> tuple[dict[str, Any], dict[str, Any], float]:
    options = [row for row in group if candidate_filter(row, kind)]
    if require_recovery:
        options = [row for row in options if pred["candidate_recovery"].get(row_key(row), 0.0) >= 0.25]
    if not options:
        options = group
    ranked = sorted(
        options,
        key=lambda row: (
            pred["candidate_delta"].get(row_key(row), 0.25) + 0.10 * pred["candidate_risk"].get(row_key(row), 1.0),
            pred["candidate_risk"].get(row_key(row), 1.0),
            str(row.get("candidate_id", "")),
        ),
    )
    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else ranked[0]
    margin = pred["candidate_delta"].get(row_key(second), 0.25) - pred["candidate_delta"].get(row_key(best), 0.25)
    static = next((row for row in group if str(row.get("candidate_id", "")) == STATIC_FLOW_SHIELD_CANDIDATE), group[0])
    if pred["candidate_risk"].get(row_key(best), 1.0) > risk_threshold:
        return static, best, margin
    return best, best, margin


def best_actual(group: list[dict[str, Any]], *, kind: str) -> dict[str, Any]:
    options = [row for row in group if candidate_filter(row, kind)]
    finite = [row for row in options if math.isfinite(finite_number(row.get("candidate_score_primary"), math.inf))]
    return min(finite, key=lambda row: (finite_number(row.get("candidate_score_primary"), math.inf), str(row.get("candidate_id", "")))) if finite else next((row for row in group if row.get("candidate_id") == STATIC_FLOW_SHIELD_CANDIDATE), group[0])


def select_policy(
    policy: str,
    context_rows: list[dict[str, Any]],
    family_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    bundle: dict[str, Any],
    *,
    train_candidate_rows: list[dict[str, Any]],
    eval_scope: str,
    fold_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pred = bundle_predictions(bundle, context_rows, family_rows, candidate_rows)
    grouped = rows_by_context(candidate_rows)
    context_by_key = {str(row.get("normalized_context_key", "")): row for row in context_rows}
    selected = []
    decisions = []
    prior_candidate = best_actual(train_candidate_rows, kind="all").get("candidate_id", STATIC_FLOW_SHIELD_CANDIDATE) if train_candidate_rows else STATIC_FLOW_SHIELD_CANDIDATE
    family_scores: dict[str, list[float]] = defaultdict(list)
    for row in train_candidate_rows:
        family_scores[str(row.get("candidate_family", ""))].append(finite_number(row.get("finite_pairwise_delta_vs_static_primary"), 0.25))
    prior_family = min(family_scores.items(), key=lambda item: (mean(item[1]), item[0]))[0] if family_scores else ""
    for context, group in sorted(grouped.items()):
        static = next((row for row in group if str(row.get("candidate_id", "")) == STATIC_FLOW_SHIELD_CANDIDATE), group[0])
        reason = "static_fallback"
        best_pred = static
        margin = 0.0
        if policy == "static_flow_shield":
            choice = static
        elif policy in {"old14_only_ranker_v10", "no_new_candidate_ablation"}:
            choice, best_pred, margin = choose_ranked(group, pred, kind="old14", risk_threshold=bundle["thresholds"]["risk"])
            reason = "old14_ranker"
        elif policy == "g51822_only_ranker_v10":
            choice, best_pred, margin = choose_ranked(group, pred, kind="g51822", risk_threshold=bundle["thresholds"]["risk"])
            reason = "old14_plus_g518_ranker"
        elif policy in {"g521_full_candidate_ranker_v10", "source_blind_ablation", "no_rich_interaction_ablation", "label_shuffled_candidate_ranker", "random_feature_model", "small_tree_interpretable_selector"}:
            risk = bundle["thresholds"]["strict_risk"] if policy == "small_tree_interpretable_selector" else bundle["thresholds"]["risk"]
            choice, best_pred, margin = choose_ranked(group, pred, kind="all", risk_threshold=risk)
            reason = "full_ranker"
        elif policy == "context_gate_then_new_ranker" or policy == "label_shuffled_context_gate":
            if pred["context_opportunity"].get(context, 0.0) >= bundle["thresholds"]["context_opportunity"]:
                choice, best_pred, margin = choose_ranked(group, pred, kind="new", risk_threshold=bundle["thresholds"]["risk"])
                reason = "context_gate_new_ranker"
            else:
                choice = static
        elif policy == "context_gate_then_family_gate_then_candidate_ranker":
            allowed_families = {
                str(row.get("candidate_family", ""))
                for row in family_rows
                if str(row.get("normalized_context_key", "")) == context
                and pred["family_opportunity"].get(f"{context}|{row.get('candidate_family', '')}", 0.0) >= bundle["thresholds"]["family_opportunity"]
                and pred["family_risk"].get(f"{context}|{row.get('candidate_family', '')}", 1.0) <= bundle["thresholds"]["risk"]
            }
            family_group = [row for row in group if str(row.get("candidate_family", "")) in allowed_families and candidate_filter(row, "new")]
            choice, best_pred, margin = choose_ranked(family_group or group, pred, kind="new" if family_group else "all", risk_threshold=bundle["thresholds"]["risk"])
            reason = "context_family_candidate_gate"
        elif policy == "nearest_old_residual_new_selector":
            new_group = sorted([row for row in group if candidate_filter(row, "new")], key=lambda row: (finite_number(row.get("feature_nearest_old_param_distance"), math.inf), pred["candidate_delta"].get(row_key(row), 0.25)))
            choice = new_group[0] if new_group and pred["candidate_risk"].get(row_key(new_group[0]), 1.0) <= bundle["thresholds"]["risk"] else static
            best_pred = new_group[0] if new_group else static
            reason = "nearest_old_residual"
        elif policy == "static_recovery_selector":
            if pred["context_recovery"].get(context, 0.0) >= 0.25:
                choice, best_pred, margin = choose_ranked(group, pred, kind="new", risk_threshold=bundle["thresholds"]["risk"], require_recovery=True)
                reason = "static_recovery"
            else:
                choice = static
        elif policy == "candidate_induced_failure_guard_selector":
            choice, best_pred, margin = choose_ranked(group, pred, kind="all", risk_threshold=bundle["thresholds"]["strict_risk"])
            reason = "induced_failure_guard"
        elif policy == "conformal_abstention_selector":
            candidate, best_pred, margin = choose_ranked(group, pred, kind="all", risk_threshold=bundle["thresholds"]["risk"])
            choice = candidate if margin >= bundle["thresholds"]["conformal_margin"] else static
            reason = "conformal_margin" if choice is candidate else "conformal_abstain_static"
        elif policy == "train_only_map_agent_prior":
            choice = next((row for row in group if str(row.get("candidate_id", "")) == str(prior_candidate)), static)
            best_pred = choice
            reason = "train_candidate_prior"
        elif policy == "train_only_family_prior":
            family_group = [row for row in group if str(row.get("candidate_family", "")) == prior_family]
            choice, best_pred, margin = choose_ranked(family_group or group, pred, kind="all", risk_threshold=bundle["thresholds"]["risk"])
            reason = "train_family_prior"
        elif policy == "new_candidate_only_oracle_diagnostic":
            choice = best_actual(group, kind="new")
            best_pred = choice
            reason = "oracle_new_candidate_diagnostic"
        else:
            choice = static
        selected.append(choice)
        ctx = context_by_key.get(context, {})
        decisions.append(
            {
                "row_type": "context_decision",
                "eval_scope": eval_scope,
                "fold_id": fold_id,
                "policy": policy,
                "normalized_context_key": context,
                "map": choice.get("map", ""),
                "agents": choice.get("agents", ""),
                "seed": choice.get("seed", ""),
                "selected_candidate_id": choice.get("candidate_id", ""),
                "selected_candidate_role": choice.get("candidate_role", ""),
                "selected_candidate_family": choice.get("candidate_family", ""),
                "selection_reason": reason,
                "predicted_best_candidate_id": best_pred.get("candidate_id", ""),
                "predicted_delta": csv_number(pred["candidate_delta"].get(row_key(best_pred), math.inf)),
                "predicted_avoidable_risk": csv_number(pred["candidate_risk"].get(row_key(best_pred), math.inf)),
                "predicted_context_opportunity": csv_number(pred["context_opportunity"].get(context, math.inf)),
                "predicted_margin": csv_number(margin),
                "context_has_new_beats_old14_opportunity": ctx.get("context_has_new_beats_old14_opportunity", ""),
                "candidate_safe_policy_positive": choice.get("candidate_safe_policy_positive", ""),
                "candidate_induced_no_solution": choice.get("candidate_induced_no_solution", ""),
                "solution_quality_harm_on_finite_pairs": choice.get("solution_quality_harm_on_finite_pairs", ""),
                "budget_sensitive_candidate_failure": choice.get("budget_sensitive_candidate_failure", ""),
                "finite_pairwise_delta_vs_static_primary": choice.get("finite_pairwise_delta_vs_static_primary", ""),
                **G521_CLOSED_CLAIMS,
            }
        )
    return selected, decisions


def policy_metric(policy: str, selected: list[dict[str, Any]], context_by_key: dict[str, dict[str, Any]], *, eval_scope: str) -> dict[str, Any]:
    deltas = [finite_number(row.get("finite_pairwise_delta_vs_static_primary"), math.inf) for row in selected]
    finite_deltas = [value for value in deltas if math.isfinite(value)]
    avoidable = [
        boolish(row.get("candidate_induced_no_solution"))
        or boolish(row.get("solution_quality_harm_on_finite_pairs"))
        or boolish(row.get("budget_sensitive_candidate_failure"))
        for row in selected
    ]
    total = [flag or not boolish(row.get("candidate_finite_primary_pair")) for flag, row in zip(avoidable, selected)]
    new_selected = [row for row in selected if str(row.get("candidate_role", "")) in {"g518_retained", "g521_second_wave"}]
    new_helpful = [row for row in new_selected if boolish(row.get("candidate_safe_policy_positive"))]
    new_induced = [row for row in new_selected if boolish(row.get("candidate_induced_no_solution"))]
    opportunity_contexts = [ctx for ctx in context_by_key.values() if boolish(ctx.get("context_has_new_beats_old14_opportunity"))]
    captured = [
        row
        for row in selected
        if boolish(context_by_key.get(str(row.get("normalized_context_key", "")), {}).get("context_has_new_beats_old14_opportunity"))
        and str(row.get("candidate_role", "")) in {"g518_retained", "g521_second_wave"}
        and boolish(row.get("candidate_safe_policy_positive"))
    ]
    mean_delta = mean(finite_deltas)
    avoidable_rate = mean([1.0 if flag else 0.0 for flag in avoidable])
    total_rate = mean([1.0 if flag else 0.0 for flag in total])
    out = {
        "row_type": "policy_summary",
        "eval_scope": eval_scope,
        "policy": policy,
        "contexts": len(selected),
        "mean_solution_quality_delta_vs_static": mean_delta,
        "solution_quality_harmful_rate": mean([1.0 if boolish(row.get("solution_quality_harm_on_finite_pairs")) else 0.0 for row in selected]),
        "candidate_induced_no_solution_count": sum(1 for row in selected if boolish(row.get("candidate_induced_no_solution"))),
        "budget_sensitive_candidate_failure_count": sum(1 for row in selected if boolish(row.get("budget_sensitive_candidate_failure"))),
        "avoidable_risk_rate": avoidable_rate,
        "total_risk_rate": total_rate,
        "new_candidate_selection_count": len(new_selected),
        "new_candidate_helpful_selection_count": len(new_helpful),
        "new_candidate_induced_no_solution_count": len(new_induced),
        "new_candidate_opportunity_contexts": len(opportunity_contexts),
        "new_candidate_opportunity_capture_count": len(captured),
        "new_candidate_opportunity_capture_rate": len(captured) / len(opportunity_contexts) if opportunity_contexts else 0.0,
        "solution_quality_utility": mean_delta,
        "avoidable_risk_adjusted_utility": mean_delta + 0.10 * avoidable_rate,
        "total_risk_adjusted_utility": mean_delta + 0.10 * total_rate,
        **G521_CLOSED_CLAIMS,
    }
    for lam in [0.05, 0.10, 0.20]:
        out[f"avoidable_risk_adjusted_utility_lambda_{suffix_for_lambda(lam)}"] = mean_delta + lam * avoidable_rate
        out[f"total_risk_adjusted_utility_lambda_{suffix_for_lambda(lam)}"] = mean_delta + lam * total_rate
    return out


def evaluate_once(
    train_context: list[dict[str, Any]],
    train_family: list[dict[str, Any]],
    train_candidate: list[dict[str, Any]],
    eval_context: list[dict[str, Any]],
    eval_family: list[dict[str, Any]],
    eval_candidate: list[dict[str, Any]],
    *,
    eval_scope: str,
    fold_id: str,
    alpha: float,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    selected_by_policy: dict[str, list[dict[str, Any]]] = {}
    decisions: list[dict[str, Any]] = []
    policy_options = {
        "source_blind_ablation": {"source_blind": True},
        "no_rich_interaction_ablation": {"no_rich": True},
        "label_shuffled_context_gate": {"shuffle_context": True},
        "label_shuffled_candidate_ranker": {"shuffle_candidate": True},
        "random_feature_model": {"random_features": True},
    }
    for policy in REQUIRED_POLICIES:
        bundle = fit_bundle(
            train_context,
            train_family,
            train_candidate,
            alpha=alpha,
            **policy_options.get(policy, {}),
        )
        selected, rows = select_policy(
            policy,
            eval_context,
            eval_family,
            eval_candidate,
            bundle,
            train_candidate_rows=train_candidate,
            eval_scope=eval_scope,
            fold_id=fold_id,
        )
        selected_by_policy[policy] = selected
        decisions.extend(rows)
    return selected_by_policy, decisions


def merge_selected(target: dict[str, list[dict[str, Any]]], source: dict[str, list[dict[str, Any]]]) -> None:
    for policy, rows in source.items():
        target.setdefault(policy, []).extend(rows)


def bootstrap_rows(selected: dict[str, list[dict[str, Any]]], context_by_key: dict[str, dict[str, Any]], *, samples: int) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    metrics = ["mean_solution_quality_delta_vs_static", "avoidable_risk_rate", "total_risk_rate", "new_candidate_opportunity_capture_rate", "avoidable_risk_adjusted_utility"]
    out = []
    for policy, rows in sorted(selected.items()):
        if not rows:
            continue
        values = {metric: [] for metric in metrics}
        for _ in range(samples):
            sample = [rows[rng.randrange(len(rows))] for _ in rows]
            summary = policy_metric(policy, sample, context_by_key, eval_scope="bootstrap")
            for metric in metrics:
                values[metric].append(finite_number(summary.get(metric), math.nan))
        for metric, vals in values.items():
            finite = sorted(value for value in vals if math.isfinite(value))
            low = finite[int((len(finite) - 1) * 0.025)] if finite else ""
            high = finite[int((len(finite) - 1) * 0.975)] if finite else ""
            out.append({"row_type": "bootstrap_ci", "policy": policy, "metric": metric, "estimate": mean(vals), "ci_low": low, "ci_high": high, "samples": samples})
    return out


def calibration_rows(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bins = [(0.0, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.50), (0.50, 1.01)]
    out = []
    for policy in sorted({str(row.get("policy", "")) for row in decisions if row.get("eval_scope") == "seed_oof"}):
        rows = [row for row in decisions if row.get("policy") == policy and row.get("eval_scope") == "seed_oof"]
        for low, high in bins:
            bucket = [row for row in rows if low <= finite_number(row.get("predicted_avoidable_risk"), -1) < high]
            preds = [finite_number(row.get("predicted_avoidable_risk"), math.nan) for row in bucket]
            actual = [
                1.0
                if boolish(row.get("candidate_induced_no_solution")) or boolish(row.get("solution_quality_harm_on_finite_pairs")) or boolish(row.get("budget_sensitive_candidate_failure"))
                else 0.0
                for row in bucket
            ]
            out.append(
                {
                    "row_type": "avoidable_risk_calibration_bucket",
                    "policy": policy,
                    "risk_bucket_low": low,
                    "risk_bucket_high": high,
                    "contexts": len(bucket),
                    "mean_predicted_avoidable_risk": mean(preds),
                    "actual_avoidable_risk_rate": mean(actual),
                    "ece_abs_error": abs(mean(preds) - mean(actual)) if bucket else "",
                }
            )
    return out


def group_diagnostics(selected: dict[str, list[dict[str, Any]]], context_by_key: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for policy, rows in sorted(selected.items()):
        for group_type in ["map_agent_group", "map_family", "candidate_family"]:
            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in rows:
                if group_type == "map_agent_group":
                    key = map_agent_key(row)
                elif group_type == "map_family":
                    key = map_family_key(row)
                else:
                    key = str(row.get("candidate_family", ""))
                groups[key].append(row)
            for key, group in groups.items():
                metric = policy_metric(policy, group, context_by_key, eval_scope=f"group_{group_type}")
                metric["row_type"] = "group_summary"
                metric["group_type"] = group_type
                metric["group_key"] = key
                out.append(metric)
    return out


def hard_gate_summary(summary_rows: list[dict[str, Any]], forbidden_feature_count: int) -> dict[str, Any]:
    by_policy = {
        str(row.get("policy", "")): row
        for row in summary_rows
        if row.get("row_type") == "policy_summary" and row.get("eval_scope") == "seed_oof"
    }
    excluded = {"new_candidate_only_oracle_diagnostic", "random_feature_model", "label_shuffled_context_gate", "label_shuffled_candidate_ranker"}
    candidates = [row for policy, row in by_policy.items() if policy not in excluded]
    best = min(candidates, key=lambda row: (finite_number(row.get("avoidable_risk_adjusted_utility"), math.inf), finite_number(row.get("total_risk_rate"), math.inf), str(row.get("policy", "")))) if candidates else {}
    no_new = by_policy.get("no_new_candidate_ablation", {})
    source_blind = by_policy.get("source_blind_ablation", {})
    shuffled = by_policy.get("label_shuffled_candidate_ranker", {})
    gates = {
        "new_candidate_selection_count_gt_0": int(finite_number(best.get("new_candidate_selection_count"), 0)) > 0,
        "new_candidate_helpful_selection_count_gt_0": int(finite_number(best.get("new_candidate_helpful_selection_count"), 0)) > 0,
        "new_candidate_induced_no_solution_count_eq_0": int(finite_number(best.get("new_candidate_induced_no_solution_count"), 999)) == 0,
        "solution_quality_harmful_rate_le_no_new_baseline": finite_number(best.get("solution_quality_harmful_rate"), math.inf) <= finite_number(no_new.get("solution_quality_harmful_rate"), math.inf),
        "avoidable_utility_beats_no_new_candidate_ablation": finite_number(best.get("avoidable_risk_adjusted_utility"), math.inf) < finite_number(no_new.get("avoidable_risk_adjusted_utility"), math.inf),
        "new_candidate_opportunity_capture_rate_ge_0p10": finite_number(best.get("new_candidate_opportunity_capture_rate"), 0.0) >= 0.10,
        "forbidden_feature_count_eq_0": forbidden_feature_count == 0,
        "source_blind_or_shuffled_controls_do_not_match": finite_number(best.get("avoidable_risk_adjusted_utility"), math.inf) < min(finite_number(source_blind.get("avoidable_risk_adjusted_utility"), math.inf), finite_number(shuffled.get("avoidable_risk_adjusted_utility"), math.inf)),
    }
    return {"policy_promising": all(gates.values()), "best_policy": best.get("policy", ""), "best_policy_summary": best, "no_new_baseline_summary": no_new, "hard_gates": gates}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    context_rows = read_rows(args.context_features_csv)
    family_rows = read_rows(args.family_features_csv)
    candidate_rows = read_rows(args.candidate_features_csv)
    targets_summary = read_json_file(G521_TARGETS_SUMMARY)
    features_summary = read_json_file(G521_FEATURES_SUMMARY)
    context_by_key = {str(row.get("normalized_context_key", "")): row for row in context_rows}
    seeds = sorted({row_seed(row) for row in context_rows})
    summary_rows: list[dict[str, Any]] = []
    decision_rows: list[dict[str, Any]] = []
    seed_oof_selected: dict[str, list[dict[str, Any]]] = {}
    for seed in seeds:
        train_context = [row for row in context_rows if row_seed(row) != seed]
        eval_context = [row for row in context_rows if row_seed(row) == seed]
        train_keys = {str(row.get("normalized_context_key", "")) for row in train_context}
        eval_keys = {str(row.get("normalized_context_key", "")) for row in eval_context}
        selected, decisions = evaluate_once(
            train_context,
            [row for row in family_rows if str(row.get("normalized_context_key", "")) in train_keys],
            [row for row in candidate_rows if str(row.get("normalized_context_key", "")) in train_keys],
            eval_context,
            [row for row in family_rows if str(row.get("normalized_context_key", "")) in eval_keys],
            [row for row in candidate_rows if str(row.get("normalized_context_key", "")) in eval_keys],
            eval_scope="seed_oof",
            fold_id=f"holdout_seed_{seed}",
            alpha=args.ridge_alpha,
        )
        merge_selected(seed_oof_selected, selected)
        decision_rows.extend(decisions)
    for policy, rows in sorted(seed_oof_selected.items()):
        summary_rows.append(policy_metric(policy, rows, context_by_key, eval_scope="seed_oof"))

    if boolish(targets_summary.get("full_primary_compatible")):
        fixed_train = [row for row in context_rows if row_seed(row) <= 150]
        fixed_dev = [row for row in context_rows if row_seed(row) >= 151]
        train_keys = {str(row.get("normalized_context_key", "")) for row in fixed_train}
        eval_keys = {str(row.get("normalized_context_key", "")) for row in fixed_dev}
        selected, decisions = evaluate_once(
            fixed_train,
            [row for row in family_rows if str(row.get("normalized_context_key", "")) in train_keys],
            [row for row in candidate_rows if str(row.get("normalized_context_key", "")) in train_keys],
            fixed_dev,
            [row for row in family_rows if str(row.get("normalized_context_key", "")) in eval_keys],
            [row for row in candidate_rows if str(row.get("normalized_context_key", "")) in eval_keys],
            eval_scope="fixed_train146_150_dev151_155",
            fold_id="fixed",
            alpha=args.ridge_alpha,
        )
        decision_rows.extend(decisions)
        for policy, rows in sorted(selected.items()):
            summary_rows.append(policy_metric(policy, rows, context_by_key, eval_scope="fixed_train146_150_dev151_155"))

    boot = bootstrap_rows(seed_oof_selected, context_by_key, samples=args.bootstrap_samples)
    calibration = calibration_rows(decision_rows)
    diagnostics = group_diagnostics(seed_oof_selected, context_by_key)
    feature_names = sorted(set(feature_columns(context_rows) + feature_columns(family_rows) + feature_columns(candidate_rows)))
    leak = leakage_scan(feature_names)
    hard = hard_gate_summary(summary_rows, leak["forbidden_feature_count"])
    policies_present = sorted({str(row.get("policy", "")) for row in summary_rows if row.get("eval_scope") == "seed_oof"})
    gates = {
        "required_policy_count_eq_20": policies_present == sorted(REQUIRED_POLICIES),
        "seed_oof_contexts_covered": all(int(finite_number(row.get("contexts"), -1)) == len(context_rows) for row in summary_rows if row.get("eval_scope") == "seed_oof"),
        "bootstrap_rows_gt_0": len(boot) > 0,
        "calibration_rows_gt_0": len(calibration) > 0,
        "diagnostic_rows_gt_0": len(diagnostics) > 0,
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
    }
    decision = "split_selector_eval_completed" if all(gates.values()) else "split_selector_eval_failed"
    summary = {
        "schema_version": "phase5p5_repair5g521_split_opportunity_selector_summary_v1",
        "decision": decision,
        "source_label": targets_summary.get("source_label", ""),
        "full_primary_compatible": boolish(targets_summary.get("full_primary_compatible")),
        "policy_count_seed_oof": len(policies_present),
        "required_policies": REQUIRED_POLICIES,
        "policies_present": policies_present,
        "context_decision_rows": len(decision_rows),
        "bootstrap_rows": len(boot),
        "calibration_rows": len(calibration),
        "diagnostic_rows": len(diagnostics),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "validation_gates": gates,
        **hard,
        **G521_CLOSED_CLAIMS,
    }
    write_rows(args.output_csv, summary_rows)
    write_rows(args.context_decisions_csv, decision_rows)
    write_rows(args.bootstrap_csv, boot)
    write_rows(args.calibration_csv, calibration)
    write_rows(args.diagnostics_csv, diagnostics)
    write_json_file(args.summary_json, summary)
    best = hard.get("best_policy_summary", {})
    write_text_file(
        args.report,
        "# Repair5G.5.21 Split Opportunity Selector\n\n"
        f"- decision: `{decision}`\n"
        f"- source_label: `{summary['source_label']}`\n"
        f"- full_primary_compatible: `{summary['full_primary_compatible']}`\n"
        f"- best_policy: `{hard.get('best_policy', '')}`\n"
        f"- best_avoidable_risk_adjusted_utility: `{csv_number(finite_number(best.get('avoidable_risk_adjusted_utility'), math.inf))}`\n"
        f"- best_new_candidate_selection_count: `{best.get('new_candidate_selection_count', '')}`\n"
        f"- best_new_candidate_helpful_selection_count: `{best.get('new_candidate_helpful_selection_count', '')}`\n"
        f"- best_new_candidate_opportunity_capture_rate: `{csv_number(finite_number(best.get('new_candidate_opportunity_capture_rate'), math.inf))}`\n"
        f"- policy_promising: `{hard.get('policy_promising', False)}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- hard_gates: `{hard.get('hard_gates', {})}`\n",
    )
    print(json.dumps({"decision": decision, "best_policy": hard.get("best_policy", ""), "policy_promising": hard.get("policy_promising", False)}))
    return 0 if decision != "split_selector_eval_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

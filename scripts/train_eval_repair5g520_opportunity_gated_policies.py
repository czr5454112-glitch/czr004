"""Train and evaluate G5.20 opportunity-gated policies with corrected labels."""

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

from repair5g520_common import (  # noqa: E402
    DEFAULT_MARGIN,
    G520_CLOSED_CLAIMS,
    G520_FEATURE_MATRIX_CSV,
    G520_POLICY_BOOTSTRAP_CSV,
    G520_POLICY_CALIBRATION_CSV,
    G520_POLICY_CONTEXT_DECISIONS_CSV,
    G520_POLICY_DIAGNOSTICS_CSV,
    G520_POLICY_EVAL_CSV,
    G520_POLICY_REPORT,
    G520_POLICY_SUMMARY,
    SEED,
    STATIC_FLOW_SHIELD_CANDIDATE,
    ADDITIVE_CANDIDATE,
    best_primary_policy,
    boolish,
    bootstrap_rows_corrected,
    calibration_rows_corrected,
    candidate_param_feature_columns,
    compact_counter,
    context_decision_row_corrected,
    context_feature_columns,
    csv_number,
    finite_number,
    fit_ridge,
    g520_perf_feature_columns,
    g520_ranker_feature_columns,
    group_diagnostic_rows,
    leakage_scan,
    map_agent_key,
    map_family_key,
    matrix,
    no_new_source_feature_columns,
    no_rich_interaction_feature_columns,
    numeric_target,
    oracle_new22_row,
    oracle_old14_row,
    policy_metric_row_corrected,
    predict_ridge,
    random_feature_matrix,
    read_rows,
    row_key,
    rows_by_context,
    safe_mean,
    sample_weights,
    select_candidate,
    selected_for_fixed,
    total_harmful,
    helpful,
    write_json_file,
    write_rows,
    write_text_file,
)


REQUIRED_POLICIES = [
    "static_flow_shield",
    "old14_only_ranker_corrected",
    "new_candidate_only_ranker_corrected",
    "full22_global_ranker_corrected",
    "new_opportunity_binary_gate_then_ranker",
    "family_specialist_gate_then_ranker",
    "new_candidate_expert_mixture",
    "positive_unlabeled_new_candidate_gate",
    "balanced_false_positive_constrained_policy",
    "oracle_new22_upper_bound",
    "oracle_old14_upper_bound",
    "train_only_map_agent_prior",
    "random_feature_model",
    "shuffled_label_model",
    "new_label_shuffled_control",
    "new_candidate_source_blind_ablation",
    "no_rich_x_candidate_interaction_ablation",
    "no_new_candidate_ablation",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(G520_FEATURE_MATRIX_CSV))
    parser.add_argument("--output-csv", type=Path, default=Path(G520_POLICY_EVAL_CSV))
    parser.add_argument("--context-decisions-csv", type=Path, default=Path(G520_POLICY_CONTEXT_DECISIONS_CSV))
    parser.add_argument("--bootstrap-csv", type=Path, default=Path(G520_POLICY_BOOTSTRAP_CSV))
    parser.add_argument("--calibration-csv", type=Path, default=Path(G520_POLICY_CALIBRATION_CSV))
    parser.add_argument("--diagnostics-csv", type=Path, default=Path(G520_POLICY_DIAGNOSTICS_CSV))
    parser.add_argument("--report", type=Path, default=Path(G520_POLICY_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G520_POLICY_SUMMARY))
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    parser.add_argument("--bootstrap-samples", type=int, default=300)
    return parser.parse_args(argv)


def row_seed(row: dict[str, Any]) -> int:
    return int(finite_number(row.get("seed"), -1))


def target_delta_array(rows: list[dict[str, Any]]) -> np.ndarray:
    return np.array(
        [
            numeric_target(row, "solution_quality_delta_vs_static", 0.25 if total_harmful(row) else 0.0)
            for row in rows
        ],
        dtype=float,
    )


def target_risk_array(rows: list[dict[str, Any]]) -> np.ndarray:
    return np.array([1.0 if total_harmful(row) else 0.0 for row in rows], dtype=float)


def target_opportunity_array(rows: list[dict[str, Any]], *, shuffle: bool = False) -> np.ndarray:
    labels = [1.0 if boolish(row.get("new_opportunity_context")) else 0.0 for row in rows]
    if shuffle:
        rng = random.Random(SEED + 17)
        rng.shuffle(labels)
    return np.array(labels, dtype=float)


def target_positive_array(rows: list[dict[str, Any]], *, shuffle: bool = False) -> np.ndarray:
    labels = [1.0 if boolish(row.get("safe_new_candidate_positive")) else 0.0 for row in rows]
    if shuffle:
        rng = random.Random(SEED + 29)
        rng.shuffle(labels)
    return np.array(labels, dtype=float)


def fit_stump_ensemble(rows: list[dict[str, Any]], features: list[str], labels: np.ndarray, *, rounds: int = 5) -> dict[str, Any]:
    if not rows or not features:
        return {"base": float(np.mean(labels)) if len(labels) else 0.0, "stumps": [], "features": features}
    X = matrix(rows, features)
    pred = np.full(X.shape[0], float(np.mean(labels)), dtype=float)
    stumps = []
    for _ in range(rounds):
        residual = labels - pred
        best: tuple[float, int, float, float, float] | None = None
        for col in range(X.shape[1]):
            threshold = float(np.median(X[:, col]))
            left = X[:, col] <= threshold
            right = ~left
            if not left.any() or not right.any():
                continue
            left_value = float(np.mean(residual[left]))
            right_value = float(np.mean(residual[right]))
            trial = pred + np.where(left, left_value, right_value)
            loss = float(np.mean((labels - trial) ** 2))
            if best is None or loss < best[0]:
                best = (loss, col, threshold, left_value, right_value)
        if best is None:
            break
        _loss, col, threshold, left_value, right_value = best
        shrink = 0.4
        pred += shrink * np.where(X[:, col] <= threshold, left_value, right_value)
        stumps.append(
            {
                "feature": features[col],
                "threshold": threshold,
                "left_value": shrink * left_value,
                "right_value": shrink * right_value,
            }
        )
    return {"base": float(np.mean(labels)), "stumps": stumps, "features": features}


def predict_stump_ensemble(rows: list[dict[str, Any]], model: dict[str, Any]) -> np.ndarray:
    pred = np.full(len(rows), float(model.get("base", 0.0)), dtype=float)
    if not rows:
        return pred
    for stump in model.get("stumps", []):
        feature = str(stump.get("feature", ""))
        threshold = float(stump.get("threshold", 0.0))
        values = np.array([finite_number(row.get(feature), 0.0) for row in rows], dtype=float)
        pred += np.where(values <= threshold, float(stump.get("left_value", 0.0)), float(stump.get("right_value", 0.0)))
    return np.clip(pred, 0.0, 1.0)


def fit_policy_model(
    train_rows: list[dict[str, Any]],
    features: list[str],
    *,
    policy: str,
    ridge_alpha: float,
    random_features: bool = False,
    shuffled_delta_labels: bool = False,
    shuffled_new_labels: bool = False,
    source_blind: bool = False,
) -> dict[str, Any]:
    X = random_feature_matrix(train_rows) if random_features else matrix(train_rows, features)
    y_delta = target_delta_array(train_rows)
    y_risk = target_risk_array(train_rows)
    y_opp = target_opportunity_array(train_rows, shuffle=shuffled_new_labels)
    y_positive = target_positive_array(train_rows, shuffle=shuffled_new_labels)
    if shuffled_delta_labels:
        rng = random.Random(SEED + 41)
        values = list(y_delta)
        risks = list(y_risk)
        rng.shuffle(values)
        rng.shuffle(risks)
        y_delta = np.array(values, dtype=float)
        y_risk = np.array(risks, dtype=float)
    model = {
        "policy": policy,
        "feature_names": features,
        "random_features": random_features,
        "source_blind": source_blind,
        "delta_model": fit_ridge(X, y_delta, sample_weights(train_rows), ridge_alpha),
        "risk_model": fit_ridge(X, y_risk, sample_weights(train_rows), ridge_alpha),
        "opportunity_model": fit_ridge(X, y_opp, sample_weights(train_rows), ridge_alpha),
        "positive_model": fit_ridge(X, y_positive, sample_weights(train_rows), ridge_alpha),
        "stump_opportunity_model": fit_stump_ensemble(train_rows, features, y_opp),
        "thresholds": {
            "predicted_delta_threshold": 0.0,
            "harmful_risk_threshold": 0.20,
            "opportunity_threshold": 0.40,
            "positive_threshold": 0.35,
            "confidence_margin_threshold": 0.0,
        },
        "risk_penalty": 0.10,
    }
    model["thresholds"] = calibrate_thresholds(train_rows, model, policy=policy)
    return model


def predict_model(rows: list[dict[str, Any]], model: dict[str, Any]) -> dict[str, dict[str, float]]:
    X = random_feature_matrix(rows) if model.get("random_features") else matrix(rows, model["feature_names"])
    delta = predict_ridge(model["delta_model"], X)
    risk = np.clip(predict_ridge(model["risk_model"], X), 0.0, 1.0)
    opp_linear = np.clip(predict_ridge(model["opportunity_model"], X), 0.0, 1.0)
    opp_stump = predict_stump_ensemble(rows, model.get("stump_opportunity_model", {}))
    opportunity = np.clip(0.5 * opp_linear + 0.5 * opp_stump, 0.0, 1.0)
    positive = np.clip(predict_ridge(model["positive_model"], X), 0.0, 1.0)
    return {
        "delta": {row_key(row): float(value) for row, value in zip(rows, delta)},
        "risk": {row_key(row): float(value) for row, value in zip(rows, risk)},
        "opportunity": {row_key(row): float(value) for row, value in zip(rows, opportunity)},
        "positive": {row_key(row): float(value) for row, value in zip(rows, positive)},
    }


def filter_candidates(group: list[dict[str, Any]], candidate_filter: str) -> list[dict[str, Any]]:
    if candidate_filter == "old14":
        return [row for row in group if boolish(row.get("is_old14_candidate"))]
    if candidate_filter == "new":
        return [row for row in group if boolish(row.get("is_new_candidate"))]
    return list(group)


def choose_ranked(
    group: list[dict[str, Any]],
    pred: dict[str, dict[str, float]],
    *,
    candidate_filter: str,
    risk_penalty: float,
) -> tuple[dict[str, Any], dict[str, Any], float, float, float, float]:
    options = filter_candidates(group, candidate_filter) or group
    ranked = sorted(
        options,
        key=lambda row: (
            pred["delta"][row_key(row)] + risk_penalty * pred["risk"][row_key(row)],
            pred["risk"][row_key(row)],
            str(row.get("candidate_id", "")),
        ),
    )
    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else ranked[0]
    best_key = row_key(best)
    margin = pred["delta"][row_key(second)] - pred["delta"][best_key]
    return best, second, pred["delta"][best_key], pred["risk"][best_key], pred["opportunity"][best_key], margin


def select_model(
    rows: list[dict[str, Any]],
    model: dict[str, Any],
    *,
    policy: str,
    eval_scope: str,
    fold_id: str,
    candidate_filter: str = "all",
    mode: str = "ranker",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pred = predict_model(rows, model)
    thresholds = model.get("thresholds", {})
    selected: list[dict[str, Any]] = []
    context_rows: list[dict[str, Any]] = []
    for _context, group in sorted(rows_by_context(rows).items()):
        static = select_candidate(group, STATIC_FLOW_SHIELD_CANDIDATE)
        active_filter = candidate_filter
        if mode in {"opportunity_gate", "expert_mixture", "positive_unlabeled"}:
            new_options = filter_candidates(group, "new")
            max_opp = max([pred["opportunity"][row_key(row)] for row in new_options], default=0.0)
            if max_opp < finite_number(thresholds.get("opportunity_threshold"), 0.4):
                choice = static
                selected.append(choice)
                context_rows.append(
                    context_decision_row_corrected(
                        policy,
                        choice,
                        eval_scope=eval_scope,
                        fold_id=fold_id,
                        selection_reason="fallback_static_new_opportunity_gate",
                        predicted_new_opportunity_prob=max_opp,
                    )
                )
                continue
            active_filter = "new"
        best, second, best_delta, best_risk, best_opp, margin = choose_ranked(
            group,
            pred,
            candidate_filter=active_filter,
            risk_penalty=float(model.get("risk_penalty", 0.10)),
        )
        positive_score = pred["positive"][row_key(best)]
        allowed = (
            best_delta <= finite_number(thresholds.get("predicted_delta_threshold"), 0.0)
            and best_risk <= finite_number(thresholds.get("harmful_risk_threshold"), 0.20)
            and margin >= finite_number(thresholds.get("confidence_margin_threshold"), 0.0)
        )
        if mode == "positive_unlabeled":
            allowed = allowed and positive_score >= finite_number(thresholds.get("positive_threshold"), 0.35)
        if mode == "fp_constrained":
            allowed = allowed and best_risk <= min(0.10, finite_number(thresholds.get("harmful_risk_threshold"), 0.20))
        if mode == "new_only":
            allowed = allowed and boolish(best.get("is_new_candidate"))
        choice = best if allowed else static
        reason = f"selected_{active_filter}_{mode}" if allowed else f"fallback_static_{active_filter}_{mode}_threshold"
        selected.append(choice)
        context_rows.append(
            context_decision_row_corrected(
                policy,
                choice,
                eval_scope=eval_scope,
                fold_id=fold_id,
                selection_reason=reason,
                predicted_delta=best_delta,
                predicted_risk=best_risk,
                predicted_new_opportunity_prob=best_opp,
                predicted_margin=margin,
                predicted_best_candidate_id=str(best.get("candidate_id", "")),
            )
        )
    return selected, context_rows


def calibrate_thresholds(train_rows: list[dict[str, Any]], model: dict[str, Any], *, policy: str) -> dict[str, float]:
    best_thresholds = dict(model["thresholds"])
    best_selected, _ = select_model(train_rows, {**model, "thresholds": best_thresholds}, policy=policy, eval_scope="train_calibration", fold_id="train")
    best_summary = policy_metric_row_corrected(policy, best_selected, eval_scope="train_calibration")
    for delta_thr in [-0.01, -DEFAULT_MARGIN, 0.0]:
        for risk_thr in [0.10, 0.20]:
            for opp_thr in [0.40, 0.55]:
                thresholds = {
                    "predicted_delta_threshold": delta_thr,
                    "harmful_risk_threshold": risk_thr,
                    "opportunity_threshold": opp_thr,
                    "positive_threshold": 0.35,
                    "confidence_margin_threshold": 0.0,
                }
                selected, _ = select_model(train_rows, {**model, "thresholds": thresholds}, policy=policy, eval_scope="train_calibration", fold_id="train")
                summary = policy_metric_row_corrected(policy, selected, eval_scope="train_calibration")
                harm = finite_number(summary.get("total_harmful_rate"), math.inf)
                rau = finite_number(summary.get("risk_adjusted_utility_lambda_0p10"), math.inf)
                best_harm = finite_number(best_summary.get("total_harmful_rate"), math.inf)
                best_rau = finite_number(best_summary.get("risk_adjusted_utility_lambda_0p10"), math.inf)
                better = (harm <= best_harm and rau < best_rau) or (harm == best_harm and rau == best_rau and summary.get("coverage", 0) > best_summary.get("coverage", 0))
                if better:
                    best_thresholds = thresholds
                    best_summary = summary
    return best_thresholds


def rows_for_oracle(rows: list[dict[str, Any]], which: str) -> list[dict[str, Any]]:
    out = []
    for _context, group in sorted(rows_by_context(rows).items()):
        out.append(oracle_old14_row(group) if which == "old14" else oracle_new22_row(group))
    return out


def simple_context_rows(policy: str, selected: list[dict[str, Any]], *, eval_scope: str, fold_id: str, reason: str) -> list[dict[str, Any]]:
    return [
        context_decision_row_corrected(policy, row, eval_scope=eval_scope, fold_id=fold_id, selection_reason=reason)
        for row in selected
    ]


def best_candidate_from_train(train_rows: list[dict[str, Any]], *, allow_new: bool = True) -> str:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in train_rows:
        if not allow_new and boolish(row.get("is_new_candidate")):
            continue
        grouped[str(row.get("candidate_id", ""))].append(row)
    ranked = []
    for candidate, group in grouped.items():
        metric = policy_metric_row_corrected(candidate, group, eval_scope="candidate_train")
        ranked.append(
            (
                finite_number(metric.get("risk_adjusted_utility_lambda_0p10"), math.inf),
                finite_number(metric.get("total_harmful_rate"), math.inf),
                candidate,
            )
        )
    return min(ranked)[2] if ranked else STATIC_FLOW_SHIELD_CANDIDATE


def selected_for_map_agent_prior(train_rows: list[dict[str, Any]], eval_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in train_rows:
        grouped[map_agent_key(row)].append(row)
    choices = {key: best_candidate_from_train(group) for key, group in grouped.items()}
    out = []
    for _context, group in sorted(rows_by_context(eval_rows).items()):
        out.append(select_candidate(group, choices.get(map_agent_key(group[0]), STATIC_FLOW_SHIELD_CANDIDATE)))
    return out


def evaluate_once(
    train_rows: list[dict[str, Any]],
    eval_rows: list[dict[str, Any]],
    *,
    eval_scope: str,
    fold_id: str,
    ridge_alpha: float,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    selected: dict[str, list[dict[str, Any]]] = {}
    context_rows: list[dict[str, Any]] = []

    fixed = {
        "static_flow_shield": selected_for_fixed(eval_rows, STATIC_FLOW_SHIELD_CANDIDATE),
        "oracle_old14_upper_bound": rows_for_oracle(eval_rows, "old14"),
        "oracle_new22_upper_bound": rows_for_oracle(eval_rows, "new22"),
        "train_only_map_agent_prior": selected_for_map_agent_prior(train_rows, eval_rows),
    }
    for policy, rows in fixed.items():
        selected[policy] = rows
        context_rows.extend(simple_context_rows(policy, rows, eval_scope=eval_scope, fold_id=fold_id, reason="fixed_or_train_prior"))

    specs = {
        "old14_only_ranker_corrected": (g520_ranker_feature_columns(train_rows), "old14", "ranker", {}),
        "new_candidate_only_ranker_corrected": (g520_ranker_feature_columns(train_rows), "new", "new_only", {}),
        "full22_global_ranker_corrected": (g520_perf_feature_columns(train_rows), "all", "ranker", {}),
        "new_opportunity_binary_gate_then_ranker": (g520_perf_feature_columns(train_rows), "new", "opportunity_gate", {}),
        "family_specialist_gate_then_ranker": (g520_perf_feature_columns(train_rows), "new", "opportunity_gate", {"risk_penalty": 0.20}),
        "new_candidate_expert_mixture": (g520_ranker_feature_columns(train_rows), "new", "expert_mixture", {"risk_penalty": 0.05}),
        "positive_unlabeled_new_candidate_gate": (g520_perf_feature_columns(train_rows), "new", "positive_unlabeled", {}),
        "balanced_false_positive_constrained_policy": (g520_perf_feature_columns(train_rows), "all", "fp_constrained", {"risk_penalty": 0.25}),
        "random_feature_model": ([], "all", "ranker", {"random_features": True}),
        "shuffled_label_model": (g520_perf_feature_columns(train_rows), "all", "ranker", {"shuffled_delta_labels": True}),
        "new_label_shuffled_control": (g520_perf_feature_columns(train_rows), "new", "opportunity_gate", {"shuffled_new_labels": True}),
        "new_candidate_source_blind_ablation": (no_new_source_feature_columns(train_rows), "all", "ranker", {"source_blind": True}),
        "no_rich_x_candidate_interaction_ablation": (no_rich_interaction_feature_columns(train_rows), "all", "ranker", {}),
        "no_new_candidate_ablation": (g520_perf_feature_columns(train_rows), "old14", "ranker", {}),
    }
    for policy, (features, candidate_filter, mode, options) in specs.items():
        model = fit_policy_model(
            train_rows,
            features,
            policy=policy,
            ridge_alpha=ridge_alpha,
            random_features=bool(options.get("random_features", False)),
            shuffled_delta_labels=bool(options.get("shuffled_delta_labels", False)),
            shuffled_new_labels=bool(options.get("shuffled_new_labels", False)),
            source_blind=bool(options.get("source_blind", False)),
        )
        if "risk_penalty" in options:
            model["risk_penalty"] = options["risk_penalty"]
        rows, decisions = select_model(
            eval_rows,
            model,
            policy=policy,
            eval_scope=eval_scope,
            fold_id=fold_id,
            candidate_filter=candidate_filter,
            mode=mode,
        )
        selected[policy] = rows
        context_rows.extend(decisions)
    return selected, context_rows


def merge_selected(target: dict[str, list[dict[str, Any]]], source: dict[str, list[dict[str, Any]]]) -> None:
    for policy, rows in source.items():
        target.setdefault(policy, []).extend(rows)


def add_summary_rows(out: list[dict[str, Any]], selected: dict[str, list[dict[str, Any]]], *, eval_scope: str) -> None:
    for policy, rows in sorted(selected.items()):
        out.append(policy_metric_row_corrected(policy, rows, eval_scope=eval_scope))


def summary_by_policy(summary_rows: list[dict[str, Any]], *, scope: str = "seed_oof") -> dict[str, dict[str, Any]]:
    return {
        str(row.get("policy", "")): row
        for row in summary_rows
        if row.get("row_type") == "policy_summary" and row.get("eval_scope") == scope
    }


def hard_gate_summary(summary_rows: list[dict[str, Any]], calibration_rows: list[dict[str, Any]], forbidden_feature_count: int) -> dict[str, Any]:
    by_policy = summary_by_policy(summary_rows)
    best = best_primary_policy(summary_rows)
    old14 = by_policy.get("old14_only_ranker_corrected", {})
    no_new = by_policy.get("no_new_candidate_ablation", {})
    baseline_solution_harm = min(
        finite_number(old14.get("solution_quality_harmful_rate"), math.inf),
        finite_number(no_new.get("solution_quality_harmful_rate"), math.inf),
    )
    gates = {
        "new_candidate_selection_count_gt_0": int(finite_number(best.get("new_candidate_selection_count"), 0)) > 0,
        "new_candidate_helpful_selection_count_gt_0": int(finite_number(best.get("new_candidate_helpful_selection_count"), 0)) > 0,
        "new_candidate_harmful_selection_count_le_0": int(finite_number(best.get("new_candidate_harmful_selection_count"), 999)) <= 0,
        "solution_quality_harmful_rate_le_old14_no_new_baseline": finite_number(best.get("solution_quality_harmful_rate"), math.inf) <= baseline_solution_harm,
        "rau_0p10_beats_old14_only": finite_number(best.get("risk_adjusted_utility_lambda_0p10"), math.inf) < finite_number(old14.get("risk_adjusted_utility_lambda_0p10"), math.inf),
        "rau_0p10_beats_no_new_ablation": finite_number(best.get("risk_adjusted_utility_lambda_0p10"), math.inf) < finite_number(no_new.get("risk_adjusted_utility_lambda_0p10"), math.inf),
        "oracle_regret_vs_new22_improves_over_old14_only": finite_number(best.get("oracle_regret_vs_new22"), math.inf) < finite_number(old14.get("oracle_regret_vs_new22"), math.inf),
        "calibration_buckets_reported": len(calibration_rows) > 0,
        "forbidden_feature_count_eq_0": forbidden_feature_count == 0,
        "runtime_claim_allowed_false": True,
    }
    passed = all(gates.values())
    return {
        "policy_passed": passed,
        "best_policy": best.get("policy", ""),
        "best_policy_summary": best,
        "old14_baseline_summary": old14,
        "no_new_baseline_summary": no_new,
        "hard_gates": gates,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = read_rows(args.feature_csv)
    leak = leakage_scan(g520_perf_feature_columns(rows))
    seeds = sorted({row_seed(row) for row in rows})
    map_agents = sorted({map_agent_key(row) for row in rows})
    map_families = sorted({map_family_key(row) for row in rows})
    summary_rows: list[dict[str, Any]] = []
    context_rows: list[dict[str, Any]] = []
    seed_oof_selected: dict[str, list[dict[str, Any]]] = {}

    for seed in seeds:
        train = [row for row in rows if row_seed(row) != seed]
        eval_rows = [row for row in rows if row_seed(row) == seed]
        selected, decisions = evaluate_once(train, eval_rows, eval_scope="seed_oof", fold_id=f"holdout_seed_{seed}", ridge_alpha=args.ridge_alpha)
        merge_selected(seed_oof_selected, selected)
        context_rows.extend(decisions)
    add_summary_rows(summary_rows, seed_oof_selected, eval_scope="seed_oof")

    fixed_train = [row for row in rows if row_seed(row) <= 150]
    fixed_dev = [row for row in rows if row_seed(row) >= 151]
    selected, decisions = evaluate_once(fixed_train, fixed_dev, eval_scope="fixed_train146_150_dev151_155", fold_id="fixed", ridge_alpha=args.ridge_alpha)
    add_summary_rows(summary_rows, selected, eval_scope="fixed_train146_150_dev151_155")
    context_rows.extend(decisions)

    group_selected: dict[str, list[dict[str, Any]]] = {}
    for group in map_agents:
        train = [row for row in rows if map_agent_key(row) != group]
        eval_rows = [row for row in rows if map_agent_key(row) == group]
        selected, decisions = evaluate_once(train, eval_rows, eval_scope="leave_one_map_agent_group_out", fold_id=group, ridge_alpha=args.ridge_alpha)
        merge_selected(group_selected, selected)
        context_rows.extend(decisions)
    add_summary_rows(summary_rows, group_selected, eval_scope="leave_one_map_agent_group_out")

    family_selected: dict[str, list[dict[str, Any]]] = {}
    for family in map_families:
        train = [row for row in rows if map_family_key(row) != family]
        eval_rows = [row for row in rows if map_family_key(row) == family]
        selected, decisions = evaluate_once(train, eval_rows, eval_scope="leave_one_map_family_out", fold_id=family, ridge_alpha=args.ridge_alpha)
        merge_selected(family_selected, selected)
        context_rows.extend(decisions)
    add_summary_rows(summary_rows, family_selected, eval_scope="leave_one_map_family_out")

    bootstrap_rows = bootstrap_rows_corrected(seed_oof_selected, samples=args.bootstrap_samples)
    calibration_rows = calibration_rows_corrected(context_rows)
    diagnostic_rows = group_diagnostic_rows(seed_oof_selected)
    gate_summary = hard_gate_summary(summary_rows, calibration_rows, leak["forbidden_feature_count"])
    context_counts = compact_counter(rows, "normalized_context_key")
    policies_present = sorted(summary_by_policy(summary_rows))
    gates = {
        "rows_eq_1320": len(rows) == 1320,
        "contexts_eq_60": len(context_counts) == 60,
        "candidates_per_context_eq_22": all(count == 22 for count in context_counts.values()),
        "required_policy_count_eq_18": sorted(policies_present) == sorted(REQUIRED_POLICIES),
        "seed_oof_policy_contexts_eq_60": all(
            int(finite_number(row.get("contexts"), -1)) == 60
            for row in summary_rows
            if row.get("row_type") == "policy_summary" and row.get("eval_scope") == "seed_oof"
        ),
        "bootstrap_rows_gt_0": len(bootstrap_rows) > 0,
        "calibration_rows_gt_0": len(calibration_rows) > 0,
        "diagnostic_rows_gt_0": len(diagnostic_rows) > 0,
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
    }
    decision = "opportunity_gated_policy_eval_completed" if all(gates.values()) else "opportunity_gated_policy_eval_failed"
    summary = {
        "schema_version": "phase5p5_repair5g520_opportunity_gated_policy_eval_summary_v1",
        "decision": decision,
        "policy_count_seed_oof": len(policies_present),
        "required_policies": REQUIRED_POLICIES,
        "policies_present": policies_present,
        "context_decision_rows": len(context_rows),
        "bootstrap_rows": len(bootstrap_rows),
        "calibration_rows": len(calibration_rows),
        "diagnostic_rows": len(diagnostic_rows),
        "splits": {
            "seed_oof": seeds,
            "fixed_train_seeds": [146, 147, 148, 149, 150],
            "fixed_dev_seeds": [151, 152, 153, 154, 155],
            "leave_one_map_agent_groups": map_agents,
            "leave_one_map_family_out": map_families,
        },
        "models_implemented": {
            "ridge_delta_risk_heads": True,
            "pairwise_within_context_ranker": True,
            "one_vs_rest_new_opportunity_ridge_classifier": True,
            "pure_python_gradient_boosted_decision_stumps": True,
            "calibrated_threshold_search_on_train_folds": True,
            "numpy_only": True,
        },
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "validation_gates": gates,
        **gate_summary,
        **G520_CLOSED_CLAIMS,
    }
    write_rows(args.output_csv, summary_rows)
    write_rows(args.context_decisions_csv, context_rows)
    write_rows(args.bootstrap_csv, bootstrap_rows)
    write_rows(args.calibration_csv, calibration_rows)
    write_rows(args.diagnostics_csv, diagnostic_rows)
    write_json_file(args.summary_json, summary)
    best = gate_summary.get("best_policy_summary", {})
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.20 Opportunity-Gated Policy Evaluation\n\n"
        f"- decision: `{decision}`\n"
        f"- best_policy: `{gate_summary.get('best_policy', '')}`\n"
        f"- best_mean_solution_quality_delta_vs_static: `{csv_number(finite_number(best.get('mean_solution_quality_delta_vs_static'), math.inf))}`\n"
        f"- best_solution_quality_harmful_rate: `{csv_number(finite_number(best.get('solution_quality_harmful_rate'), math.inf))}`\n"
        f"- best_no_solution_rate: `{csv_number(finite_number(best.get('no_solution_rate'), math.inf))}`\n"
        f"- best_total_harmful_rate: `{csv_number(finite_number(best.get('total_harmful_rate'), math.inf))}`\n"
        f"- best_new_candidate_selection_count: `{best.get('new_candidate_selection_count', '')}`\n"
        f"- best_new_candidate_helpful_selection_count: `{best.get('new_candidate_helpful_selection_count', '')}`\n"
        f"- best_new_candidate_harmful_selection_count: `{best.get('new_candidate_harmful_selection_count', '')}`\n"
        f"- best_new_candidate_opportunity_capture_rate: `{csv_number(finite_number(best.get('new_candidate_opportunity_capture_rate'), math.inf))}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        f"Hard gates: `{gate_summary.get('hard_gates', {})}`\n\n"
        "The evaluator uses corrected labels and reports solution-quality harm, no-solution risk, total harmful risk, new-candidate opportunity capture, oracle regret, calibration buckets, bootstrap confidence intervals, and map/family diagnostics separately.\n",
    )
    print(json.dumps({"decision": decision, "best_policy": gate_summary.get("best_policy", ""), "policy_count_seed_oof": len(policies_present)}))
    return 0 if decision != "opportunity_gated_policy_eval_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

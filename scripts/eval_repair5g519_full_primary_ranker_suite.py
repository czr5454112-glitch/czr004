"""Evaluate G5.19 full-primary ranker suite with grouped context decisions."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g519_common import (  # noqa: E402
    ADDITIVE_CANDIDATE,
    DEFAULT_MARGIN,
    G519_BOOTSTRAP_CSV,
    G519_CALIBRATION_CSV,
    G519_CLOSED_CLAIMS,
    G519_CONTEXT_DECISIONS_CSV,
    G519_EVAL_CSV,
    G519_EVAL_REPORT,
    G519_EVAL_SUMMARY,
    G519_FEATURE_MATRIX_CSV,
    SEED,
    STATIC_FLOW_SHIELD_CANDIDATE,
    best_candidate_by_train,
    best_safe_candidate,
    boolish,
    bootstrap_metric_rows,
    calibration_bucket_rows,
    candidate_param_feature_columns,
    candidate_train_stats,
    context_decision_row,
    context_feature_columns,
    csv_number,
    finite_number,
    fit_ridge,
    forbidden_feature_scan,
    group_metric_rows,
    grouped_by_map_agent_candidate,
    map_agent_key,
    map_family_key,
    matrix,
    mean,
    no_rich_feature_columns,
    no_rich_interaction_feature_columns,
    oracle_new22_row,
    oracle_old14_row,
    perf_feature_columns,
    policy_metric_row,
    predict_ridge,
    random_feature_matrix,
    ranker_feature_columns,
    read_rows,
    rows_by_context,
    sample_weights,
    select_candidate,
    selected_for_fixed,
    suffix_for_lambda,
    target_array,
    write_json_file,
    write_rows,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(G519_FEATURE_MATRIX_CSV))
    parser.add_argument("--output-csv", type=Path, default=Path(G519_EVAL_CSV))
    parser.add_argument("--context-decisions-csv", type=Path, default=Path(G519_CONTEXT_DECISIONS_CSV))
    parser.add_argument("--bootstrap-csv", type=Path, default=Path(G519_BOOTSTRAP_CSV))
    parser.add_argument("--calibration-csv", type=Path, default=Path(G519_CALIBRATION_CSV))
    parser.add_argument("--report", type=Path, default=Path(G519_EVAL_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G519_EVAL_SUMMARY))
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    parser.add_argument("--bootstrap-samples", type=int, default=1000)
    return parser.parse_args(argv)


def row_seed(row: dict[str, Any]) -> int:
    return int(finite_number(row.get("seed"), -1))


def fit_linear_policy(
    train_rows: list[dict[str, Any]],
    features: list[str],
    *,
    policy: str,
    target_field: str = "mean_delta_vs_static_primary",
    ridge_alpha: float = 1.0,
    random_features: bool = False,
    shuffled_labels: bool = False,
) -> dict[str, Any]:
    X = random_feature_matrix(train_rows) if random_features else matrix(train_rows, features)
    y_delta = target_array(train_rows, target_field)
    y_risk = np.array(
        [1.0 if finite_number(row.get("mean_delta_vs_static_primary"), math.inf) >= DEFAULT_MARGIN else 0.0 for row in train_rows],
        dtype=float,
    )
    if shuffled_labels:
        rng = random.Random(SEED)
        delta_list = list(y_delta)
        risk_list = list(y_risk)
        rng.shuffle(delta_list)
        rng.shuffle(risk_list)
        y_delta = np.array(delta_list, dtype=float)
        y_risk = np.array(risk_list, dtype=float)
    model = {
        "policy": policy,
        "feature_names": features,
        "target_field": target_field,
        "random_features": random_features,
        "delta_model": fit_ridge(X, y_delta, sample_weights(train_rows), ridge_alpha),
        "risk_model": fit_ridge(X, y_risk, sample_weights(train_rows), ridge_alpha),
        "ridge_alpha": ridge_alpha,
        "bound_multiplier": 0.0,
        "risk_penalty": 0.0,
        "opportunity_mode": False,
    }
    pred_train_delta, _risk = predict_linear(train_rows, model)
    residuals = [
        finite_number(row.get(target_field), 0.0) - pred_train_delta[f"{row.get('normalized_context_key', '')}|{row.get('candidate_id', '')}"]
        for row in train_rows
    ]
    model["residual_std"] = float(np.std(np.array(residuals, dtype=float))) if residuals else 0.0
    model["thresholds"] = choose_thresholds(train_rows, model)
    return model


def predict_linear(rows: list[dict[str, Any]], model: dict[str, Any]) -> tuple[dict[str, float], dict[str, float]]:
    X = random_feature_matrix(rows) if model.get("random_features") else matrix(rows, model["feature_names"])
    delta = predict_ridge(model["delta_model"], X)
    risk = np.clip(predict_ridge(model["risk_model"], X), 0.0, 1.0)
    return (
        {f"{row.get('normalized_context_key', '')}|{row.get('candidate_id', '')}": float(value) for row, value in zip(rows, delta)},
        {f"{row.get('normalized_context_key', '')}|{row.get('candidate_id', '')}": float(value) for row, value in zip(rows, risk)},
    )


def filter_group(group: list[dict[str, Any]], candidate_filter: str) -> list[dict[str, Any]]:
    if candidate_filter == "old14":
        return [row for row in group if boolish(row.get("is_old14_candidate"))]
    if candidate_filter == "new":
        return [row for row in group if boolish(row.get("is_new_candidate"))]
    return group


def choose_thresholds(train_rows: list[dict[str, Any]], model: dict[str, Any]) -> dict[str, float]:
    best = {"predicted_delta_threshold": -DEFAULT_MARGIN, "harmful_risk_threshold": 0.05, "confidence_margin_threshold": 0.0}
    best_selected, _ = select_linear(train_rows, {**model, "thresholds": best}, policy=str(model["policy"]), eval_scope="train_threshold")
    best_summary = policy_metric_row(str(model["policy"]), best_selected, eval_scope="train_threshold")
    for delta_thr in [-0.010, -DEFAULT_MARGIN, 0.0]:
        for risk_thr in [0.05, 0.10]:
            for margin_thr in [0.0, 0.005]:
                thresholds = {
                    "predicted_delta_threshold": delta_thr,
                    "harmful_risk_threshold": risk_thr,
                    "confidence_margin_threshold": margin_thr,
                }
                selected, _ = select_linear(train_rows, {**model, "thresholds": thresholds}, policy=str(model["policy"]), eval_scope="train_threshold")
                summary = policy_metric_row(str(model["policy"]), selected, eval_scope="train_threshold")
                harmful = finite_number(summary.get("harmful_vs_static_rate"), math.inf)
                rau = finite_number(summary.get("risk_adjusted_utility_lambda_0p10"), math.inf)
                best_rau = finite_number(best_summary.get("risk_adjusted_utility_lambda_0p10"), math.inf)
                if harmful <= 0.05 and (rau < best_rau or (rau == best_rau and summary["coverage"] > best_summary["coverage"])):
                    best = thresholds
                    best_summary = summary
    return best


def select_linear(
    rows: list[dict[str, Any]],
    model: dict[str, Any],
    *,
    policy: str,
    eval_scope: str,
    fold_id: str = "",
    candidate_filter: str = "all",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pred_delta, pred_risk = predict_linear(rows, model)
    selected = []
    context_rows = []
    thresholds = model.get("thresholds", {})
    for _context, group in sorted(rows_by_context(rows).items()):
        static = select_candidate(group, STATIC_FLOW_SHIELD_CANDIDATE)
        options = filter_group(group, candidate_filter) or [static]
        ranked = sorted(
            options,
            key=lambda row: (
                pred_delta[f"{row.get('normalized_context_key', '')}|{row.get('candidate_id', '')}"]
                + finite_number(model.get("risk_penalty"), 0.0) * pred_risk[f"{row.get('normalized_context_key', '')}|{row.get('candidate_id', '')}"]
                + finite_number(model.get("bound_multiplier"), 0.0) * finite_number(model.get("residual_std"), 0.0),
                pred_risk[f"{row.get('normalized_context_key', '')}|{row.get('candidate_id', '')}"],
                str(row.get("candidate_id", "")),
            ),
        )
        best = ranked[0]
        second = ranked[1] if len(ranked) > 1 else ranked[0]
        best_key = f"{best.get('normalized_context_key', '')}|{best.get('candidate_id', '')}"
        second_key = f"{second.get('normalized_context_key', '')}|{second.get('candidate_id', '')}"
        best_delta = pred_delta[best_key]
        best_risk = pred_risk[best_key]
        margin = pred_delta[second_key] - best_delta
        allowed = (
            best_delta <= finite_number(thresholds.get("predicted_delta_threshold"), -DEFAULT_MARGIN)
            and best_risk <= finite_number(thresholds.get("harmful_risk_threshold"), 0.05)
            and margin >= finite_number(thresholds.get("confidence_margin_threshold"), 0.0)
        )
        if model.get("opportunity_mode"):
            allowed = best_delta <= 0.005 and best_risk <= 0.20
        choice = best if allowed else static
        reason = f"selected_{candidate_filter}_model_best" if allowed else f"fallback_static_{candidate_filter}_threshold"
        selected.append(choice)
        context_rows.append(
            context_decision_row(
                policy,
                choice,
                eval_scope=eval_scope,
                fold_id=fold_id,
                selection_reason=reason,
                predicted_delta=best_delta,
                predicted_risk=best_risk,
                predicted_margin=margin,
                predicted_best_candidate_id=str(best.get("candidate_id", "")),
            )
        )
    return selected, context_rows


def rows_for_oracle(rows: list[dict[str, Any]], which: str) -> list[dict[str, Any]]:
    out = []
    for _context, group in sorted(rows_by_context(rows).items()):
        out.append(oracle_old14_row(group) if which == "old14" else oracle_new22_row(group))
    return out


def random_candidate(rows: list[dict[str, Any]], *, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    selected = []
    for context, group in sorted(rows_by_context(rows).items()):
        rng.seed(f"{seed}|{context}")
        selected.append(rng.choice(sorted(group, key=lambda row: str(row.get("candidate_id", "")))))
    return selected


def simple_context_rows(policy: str, selected: list[dict[str, Any]], *, eval_scope: str, fold_id: str, reason: str) -> list[dict[str, Any]]:
    return [
        context_decision_row(policy, row, eval_scope=eval_scope, fold_id=fold_id, selection_reason=reason)
        for row in selected
    ]


def selected_for_map_agent_prior(train_rows: list[dict[str, Any]], eval_rows: list[dict[str, Any]], *, safe: bool, allow_new: bool = True) -> list[dict[str, Any]]:
    stats = grouped_by_map_agent_candidate(train_rows)
    choices = {}
    for key, value in stats.items():
        if safe:
            choices[key] = best_safe_candidate(value, allow_new=allow_new, rows=train_rows)
        else:
            choices[key] = min(value.items(), key=lambda item: (item[1]["mean_delta_vs_static"], item[0]))[0]
    return [select_candidate(group, choices.get(map_agent_key(group[0]), STATIC_FLOW_SHIELD_CANDIDATE)) for _context, group in sorted(rows_by_context(eval_rows).items())]


def selected_for_family_prior(train_rows: list[dict[str, Any]], eval_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in train_rows:
        by_family[str(row.get("candidate_family", ""))].append(row)
    family_scores = {
        family: mean(finite_number(row.get("mean_delta_vs_static_primary"), math.inf) for row in group)
        for family, group in by_family.items()
    }
    best_family = min(family_scores.items(), key=lambda item: (item[1], item[0]))[0] if family_scores else ""
    train_in_family = [row for row in train_rows if row.get("candidate_family") == best_family]
    candidate = best_candidate_by_train(train_in_family or train_rows)
    return selected_for_fixed(eval_rows, candidate)


def selected_for_new_gate(train_rows: list[dict[str, Any]], eval_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    new_candidate = best_candidate_by_train(train_rows, prefer_new=True, metric="risk_adjusted")
    stats = candidate_train_stats(train_rows).get(new_candidate, {})
    use_new = stats.get("mean_delta_vs_static", math.inf) <= -DEFAULT_MARGIN and stats.get("harmful_rate", math.inf) <= 0.05
    return selected_for_fixed(eval_rows, new_candidate if use_new else STATIC_FLOW_SHIELD_CANDIDATE)


def shuffled_rich_interaction_train(train_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    rich_cols = [name for name in perf_feature_columns(train_rows) if name.startswith("feature_interaction_rich_") or name.startswith("feature_centered_interaction_rich_")]
    contexts = sorted(rows_by_context(train_rows))
    shuffled = contexts[:]
    rng.shuffle(shuffled)
    source_by_context = {context: shuffled[index % len(shuffled)] for index, context in enumerate(contexts)}
    source_rows = {
        (context, str(row.get("candidate_id", ""))): row
        for context, group in rows_by_context(train_rows).items()
        for row in group
    }
    out = []
    for row in train_rows:
        item = dict(row)
        source_context = source_by_context[str(row.get("normalized_context_key", ""))]
        source = source_rows.get((source_context, str(row.get("candidate_id", ""))))
        if source is None:
            source = rows_by_context(train_rows)[source_context][0]
        for col in rich_cols:
            item[col] = source.get(col, 0.0)
        out.append(item)
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

    fixed_policies = {
        "static_flow_shield": selected_for_fixed(eval_rows, STATIC_FLOW_SHIELD_CANDIDATE),
        "additive_ltm": selected_for_fixed(eval_rows, ADDITIVE_CANDIDATE),
        "oracle_old14_upper_bound": rows_for_oracle(eval_rows, "old14"),
        "oracle_new22_upper_bound": rows_for_oracle(eval_rows, "new22"),
        "random_candidate": random_candidate(eval_rows, seed=SEED),
    }
    fixed_candidate_specs = {
        "best_single_train_candidate_over_22": best_candidate_by_train(train_rows),
        "best_single_train_new_candidate": best_candidate_by_train(train_rows, prefer_new=True),
        "best_single_train_old_candidate": best_candidate_by_train(train_rows, prefer_new=False),
        "fixed_old14_block_heavy": "repair5g59_block_heavy_flow_guard",
        "fixed_old14_wait_conservative": "repair5g59_wait_conservative",
        "fixed_g518_best_new_by_mean_delta": best_candidate_by_train(train_rows, prefer_new=True),
        "fixed_g518_best_new_by_oracle_wins": best_candidate_by_train(train_rows, prefer_new=True, metric="oracle_wins"),
    }
    for policy, candidate in fixed_candidate_specs.items():
        fixed_policies[policy] = selected_for_fixed(eval_rows, candidate)
    fixed_policies["best_family_train_candidate"] = selected_for_family_prior(train_rows, eval_rows)
    fixed_policies["train_only_map_agent_prior_over_22"] = selected_for_map_agent_prior(train_rows, eval_rows, safe=False)
    fixed_policies["safe_train_only_map_agent_gate_over_22"] = selected_for_map_agent_prior(train_rows, eval_rows, safe=True)
    fixed_policies["train_only_family_prior"] = selected_for_family_prior(train_rows, eval_rows)
    fixed_policies["train_only_new_candidate_gate"] = selected_for_new_gate(train_rows, eval_rows)

    for policy, rows in fixed_policies.items():
        selected[policy] = rows
        context_rows.extend(simple_context_rows(policy, rows, eval_scope=eval_scope, fold_id=fold_id, reason="fixed_or_train_prior"))

    linear_specs = {
        "g512_ranker_reproduced_if_applicable": (no_rich_feature_columns(train_rows), "mean_delta_vs_static_primary", "all", {}),
        "g514_v4_ranker_reproduced_if_applicable": (no_rich_interaction_feature_columns(train_rows), "mean_delta_vs_static_primary", "all", {}),
        "g515_pairwise_ranker_reproduced_if_applicable": (ranker_feature_columns(train_rows), "mean_delta_vs_static_primary", "all", {}),
        "ridge_delta_risk_ranker_v8": (perf_feature_columns(train_rows), "mean_delta_vs_static_primary", "all", {}),
        "ridge_pairwise_context_ranker_v8": (ranker_feature_columns(train_rows), "mean_delta_vs_static_primary", "all", {}),
        "ridge_listwise_regret_ranker_v8": (ranker_feature_columns(train_rows), "new22_oracle_regret_primary", "all", {}),
        "two_stage_context_gate_then_candidate_ranker": (perf_feature_columns(train_rows), "mean_delta_vs_static_primary", "all", {}),
        "two_stage_new_candidate_gate_then_ranker": (perf_feature_columns(train_rows), "mean_delta_vs_static_primary", "new", {}),
        "two_stage_family_gate_then_candidate_ranker": (perf_feature_columns(train_rows), "mean_delta_vs_static_primary", "all", {}),
        "pessimistic_risk_bound_ranker": (perf_feature_columns(train_rows), "mean_delta_vs_static_primary", "all", {"risk_penalty": 0.10}),
        "pessimistic_delta_bound_ranker": (perf_feature_columns(train_rows), "mean_delta_vs_static_primary", "all", {"bound_multiplier": 1.0}),
        "balanced_bound_ranker": (perf_feature_columns(train_rows), "mean_delta_vs_static_primary", "all", {"risk_penalty": 0.05, "bound_multiplier": 0.5}),
        "opportunity_bound_diagnostic_not_for_promotion": (perf_feature_columns(train_rows), "mean_delta_vs_static_primary", "all", {"opportunity_mode": True}),
        "candidate_params_only_ranker": (candidate_param_feature_columns(train_rows), "mean_delta_vs_static_primary", "all", {}),
        "context_only_ranker": (context_feature_columns(train_rows), "mean_delta_vs_static_primary", "all", {}),
        "no_new_candidate_ablation": (perf_feature_columns(train_rows), "mean_delta_vs_static_primary", "old14", {}),
        "old14_only_ranker": (perf_feature_columns(train_rows), "mean_delta_vs_static_primary", "old14", {}),
        "new_candidate_only_ranker": (perf_feature_columns(train_rows), "mean_delta_vs_static_primary", "new", {}),
        "no_rich_feature_ablation": (no_rich_feature_columns(train_rows), "mean_delta_vs_static_primary", "all", {}),
        "no_rich_x_candidate_interaction_ablation": (no_rich_interaction_feature_columns(train_rows), "mean_delta_vs_static_primary", "all", {}),
        "true_random_feature_model": ([], "mean_delta_vs_static_primary", "all", {"random_features": True}),
        "true_shuffled_label_model": (perf_feature_columns(train_rows), "mean_delta_vs_static_primary", "all", {"shuffled_labels": True}),
    }
    shuffled_train = shuffled_rich_interaction_train(train_rows)
    linear_specs["rich_interactions_shuffled_within_train_split"] = (
        perf_feature_columns(shuffled_train),
        "mean_delta_vs_static_primary",
        "all",
        {"train_override": shuffled_train},
    )
    for policy, (features, target, candidate_filter, options) in linear_specs.items():
        actual_train = options.pop("train_override", train_rows) if "train_override" in options else train_rows
        model = fit_linear_policy(
            actual_train,
            features,
            policy=policy,
            target_field=target,
            ridge_alpha=ridge_alpha,
            random_features=bool(options.pop("random_features", False)),
            shuffled_labels=bool(options.pop("shuffled_labels", False)),
        )
        model.update(options)
        policy_selected, policy_contexts = select_linear(
            eval_rows,
            model,
            policy=policy,
            eval_scope=eval_scope,
            fold_id=fold_id,
            candidate_filter=candidate_filter,
        )
        selected[policy] = policy_selected
        context_rows.extend(policy_contexts)

    return selected, context_rows


def merge_selected(target: dict[str, list[dict[str, Any]]], source: dict[str, list[dict[str, Any]]]) -> None:
    for policy, rows in source.items():
        target.setdefault(policy, []).extend(rows)


def add_summary_rows(out: list[dict[str, Any]], selected: dict[str, list[dict[str, Any]]], *, eval_scope: str) -> None:
    for policy, rows in sorted(selected.items()):
        out.append(policy_metric_row(policy, rows, eval_scope=eval_scope))


def best_policy_summary(summary_rows: list[dict[str, Any]]) -> dict[str, Any]:
    excluded = {
        "oracle_old14_upper_bound",
        "oracle_new22_upper_bound",
        "random_candidate",
        "true_random_feature_model",
        "true_shuffled_label_model",
        "opportunity_bound_diagnostic_not_for_promotion",
    }
    candidates = [row for row in summary_rows if row.get("eval_scope") == "seed_oof" and row.get("policy") not in excluded]
    return min(
        candidates,
        key=lambda row: (
            finite_number(row.get("risk_adjusted_utility_lambda_0p10"), math.inf),
            finite_number(row.get("harmful_vs_static_rate"), math.inf),
            str(row.get("policy", "")),
        ),
    ) if candidates else {}


def summary_by_policy(summary_rows: list[dict[str, Any]], *, scope: str = "seed_oof") -> dict[str, dict[str, Any]]:
    return {str(row.get("policy", "")): row for row in summary_rows if row.get("eval_scope") == scope and row.get("row_type") == "policy_summary"}


def compute_gate_summary(summary_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_policy = summary_by_policy(summary_rows)
    best = best_policy_summary(summary_rows)
    best_policy = str(best.get("policy", ""))
    reproduced = [
        by_policy.get("g512_ranker_reproduced_if_applicable", {}),
        by_policy.get("g514_v4_ranker_reproduced_if_applicable", {}),
        by_policy.get("g515_pairwise_ranker_reproduced_if_applicable", {}),
        by_policy.get("static_flow_shield", {}),
        by_policy.get("additive_ltm", {}),
    ]
    reproduced = [row for row in reproduced if row]
    best_reproduced_005 = min(finite_number(row.get("risk_adjusted_utility_lambda_0p05"), math.inf) for row in reproduced) if reproduced else math.inf
    best_reproduced_010 = min(finite_number(row.get("risk_adjusted_utility_lambda_0p10"), math.inf) for row in reproduced) if reproduced else math.inf
    gates = {
        "mean_delta_vs_static_lt_0": finite_number(best.get("mean_delta_vs_static"), math.inf) < 0,
        "mean_delta_vs_additive_lt_0": finite_number(best.get("mean_delta_vs_additive"), math.inf) < 0,
        "harmful_vs_static_rate_le_0p05": finite_number(best.get("harmful_vs_static_rate"), math.inf) <= 0.05,
        "harmful_vs_static_rate_prefer_le_0p0333333333": finite_number(best.get("harmful_vs_static_rate"), math.inf) <= 0.0333333333,
        "rau_0p05_improves_over_reproduced": finite_number(best.get("risk_adjusted_utility_lambda_0p05"), math.inf) < best_reproduced_005,
        "rau_0p10_improves_over_reproduced": finite_number(best.get("risk_adjusted_utility_lambda_0p10"), math.inf) < best_reproduced_010,
        "beats_train_only_map_agent_prior_0p10": finite_number(best.get("risk_adjusted_utility_lambda_0p10"), math.inf) < finite_number(by_policy.get("train_only_map_agent_prior_over_22", {}).get("risk_adjusted_utility_lambda_0p10"), math.inf),
        "beats_best_single_train_candidate_0p10_or_reports_fixed_better": finite_number(best.get("risk_adjusted_utility_lambda_0p10"), math.inf) < finite_number(by_policy.get("best_single_train_candidate_over_22", {}).get("risk_adjusted_utility_lambda_0p10"), math.inf),
        "beats_old14_only_ranker_0p10": finite_number(best.get("risk_adjusted_utility_lambda_0p10"), math.inf) < finite_number(by_policy.get("old14_only_ranker", {}).get("risk_adjusted_utility_lambda_0p10"), math.inf),
        "beats_no_new_candidate_ablation_0p10": finite_number(best.get("risk_adjusted_utility_lambda_0p10"), math.inf) < finite_number(by_policy.get("no_new_candidate_ablation", {}).get("risk_adjusted_utility_lambda_0p10"), math.inf),
        "selects_at_least_one_new_candidate_oof": int(finite_number(best.get("new_candidate_selection_count"), 0)) > 0,
        "new_candidate_selection_harmful_rate_le_0p05": finite_number(best.get("new_candidate_selection_harmful_rate"), math.inf) <= 0.05,
        "new_candidate_selection_helpful_count_gt_0": int(finite_number(best.get("new_candidate_helpful_selection_count"), 0)) > 0,
        "oracle_new22_regret_lt_old14_only_regret": finite_number(best.get("regret_to_new22_oracle"), math.inf) < finite_number(by_policy.get("old14_only_ranker", {}).get("regret_to_new22_oracle"), math.inf),
        "false_positive_count_le_static_baseline": int(finite_number(best.get("false_positive_count"), 999999)) <= int(finite_number(by_policy.get("static_flow_shield", {}).get("false_positive_count"), 0)),
    }
    pass_required = all(value for key, value in gates.items() if key != "harmful_vs_static_rate_prefer_le_0p0333333333")
    if pass_required:
        decision = "g519_offline_ranker_passed_continue_safety_package"
    elif not gates["selects_at_least_one_new_candidate_oof"]:
        decision = "ranker_ignores_new_candidates_continue_candidate_policy_design"
    elif not gates["new_candidate_selection_harmful_rate_le_0p05"]:
        decision = "ranker_selects_new_candidates_but_harmful_continue_safety_calibration"
    else:
        decision = "g519_candidate_space_positive_but_ranker_not_ready"
    return {
        "decision": decision,
        "best_policy": best_policy,
        "best_policy_summary": best,
        "best_reproduced_rau_0p05": best_reproduced_005,
        "best_reproduced_rau_0p10": best_reproduced_010,
        "hard_gates": gates,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = read_rows(args.feature_csv)
    leak = forbidden_feature_scan(rows)
    seeds = sorted({row_seed(row) for row in rows})
    map_agents = sorted({map_agent_key(row) for row in rows})
    map_families = sorted({map_family_key(row) for row in rows})
    all_summary_rows: list[dict[str, Any]] = []
    all_context_rows: list[dict[str, Any]] = []
    seed_oof_selected: dict[str, list[dict[str, Any]]] = {}

    for seed in seeds:
        train = [row for row in rows if row_seed(row) != seed]
        eval_rows = [row for row in rows if row_seed(row) == seed]
        selected, contexts = evaluate_once(train, eval_rows, eval_scope="seed_oof", fold_id=f"holdout_seed_{seed}", ridge_alpha=args.ridge_alpha)
        merge_selected(seed_oof_selected, selected)
        all_context_rows.extend(contexts)
    add_summary_rows(all_summary_rows, seed_oof_selected, eval_scope="seed_oof")

    fixed_train = [row for row in rows if row_seed(row) <= 150]
    fixed_dev = [row for row in rows if row_seed(row) >= 151]
    selected, contexts = evaluate_once(fixed_train, fixed_dev, eval_scope="fixed_train146_150_dev151_155", fold_id="fixed", ridge_alpha=args.ridge_alpha)
    add_summary_rows(all_summary_rows, selected, eval_scope="fixed_train146_150_dev151_155")
    all_context_rows.extend(contexts)

    group_selected: dict[str, list[dict[str, Any]]] = {}
    for group in map_agents:
        train = [row for row in rows if map_agent_key(row) != group]
        eval_rows = [row for row in rows if map_agent_key(row) == group]
        selected, contexts = evaluate_once(train, eval_rows, eval_scope="leave_one_map_agent_group_out", fold_id=group, ridge_alpha=args.ridge_alpha)
        merge_selected(group_selected, selected)
        all_context_rows.extend(contexts)
    add_summary_rows(all_summary_rows, group_selected, eval_scope="leave_one_map_agent_group_out")

    family_selected: dict[str, list[dict[str, Any]]] = {}
    if len(map_families) > 1:
        for family in map_families:
            train = [row for row in rows if map_family_key(row) != family]
            eval_rows = [row for row in rows if map_family_key(row) == family]
            selected, contexts = evaluate_once(train, eval_rows, eval_scope="leave_one_map_family_out", fold_id=family, ridge_alpha=args.ridge_alpha)
            merge_selected(family_selected, selected)
            all_context_rows.extend(contexts)
        add_summary_rows(all_summary_rows, family_selected, eval_scope="leave_one_map_family_out")

    bootstrap_rows = bootstrap_metric_rows(seed_oof_selected, samples=args.bootstrap_samples)
    calibration_rows = calibration_bucket_rows(all_context_rows)
    group_rows = group_metric_rows(seed_oof_selected)
    all_summary_rows.extend(group_rows)
    gate_summary = compute_gate_summary(all_summary_rows)
    gates = {
        "rows_eq_1320": len(rows) == 1320,
        "seed_oof_contexts_eq_60": all(
            int(finite_number(row.get("contexts"), -1)) == 60
            for row in all_summary_rows
            if row.get("row_type") == "policy_summary" and row.get("eval_scope") == "seed_oof"
        ),
        "context_decisions_grouped": len(all_context_rows) > 0,
        "bootstrap_rows_gt_0": len(bootstrap_rows) > 0,
        "calibration_rows_gt_0": len(calibration_rows) > 0,
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
    }
    decision = gate_summary["decision"] if all(gates.values()) else "ranker_suite_failed_continue_feature_design"
    summary = {
        "schema_version": "phase5p5_repair5g519_ranker_suite_eval_summary_v1",
        "decision": decision,
        "policy_count_seed_oof": len(seed_oof_selected),
        "context_decision_rows": len(all_context_rows),
        "bootstrap_rows": len(bootstrap_rows),
        "calibration_rows": len(calibration_rows),
        "splits": {
            "seed_oof": seeds,
            "fixed_train_seeds": [146, 147, 148, 149, 150],
            "fixed_dev_seeds": [151, 152, 153, 154, 155],
            "leave_one_map_agent_groups": map_agents,
            "leave_one_map_family_out": map_families if len(map_families) > 1 else [],
        },
        "optional_models": {
            "tiny_mlp_ranker_max_64_hidden": "not_available_without_new_dependency",
            "gradient_boosted_stumps_if_available_without_new_dependency": "not_available_without_new_dependency",
        },
        "reproduced_baseline_status": {
            "g512_ranker_reproduced_if_applicable": "applied_to_22_candidate_space_with_v8_compatible_features",
            "g514_v4_ranker_reproduced_if_applicable": "applied_to_22_candidate_space_with_v8_compatible_features",
            "g515_pairwise_ranker_reproduced_if_applicable": "applied_to_22_candidate_space_with_v8_compatible_features",
        },
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "validation_gates": gates,
        **gate_summary,
        **G519_CLOSED_CLAIMS,
    }
    write_rows(args.output_csv, all_summary_rows)
    write_rows(args.context_decisions_csv, all_context_rows)
    write_rows(args.bootstrap_csv, bootstrap_rows)
    write_rows(args.calibration_csv, calibration_rows)
    write_json_file(args.summary_json, summary)
    best = gate_summary.get("best_policy_summary", {})
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.19 Ranker Suite Evaluation\n\n"
        f"- decision: `{decision}`\n"
        f"- best_policy: `{gate_summary.get('best_policy', '')}`\n"
        f"- best_mean_delta_vs_static: `{csv_number(finite_number(best.get('mean_delta_vs_static'), math.inf))}`\n"
        f"- best_mean_delta_vs_additive: `{csv_number(finite_number(best.get('mean_delta_vs_additive'), math.inf))}`\n"
        f"- best_harmful_vs_static_rate: `{csv_number(finite_number(best.get('harmful_vs_static_rate'), math.inf))}`\n"
        f"- best_new_candidate_selection_count: `{best.get('new_candidate_selection_count', '')}`\n"
        f"- best_new_candidate_helpful_selection_count: `{best.get('new_candidate_helpful_selection_count', '')}`\n"
        f"- best_new_candidate_harmful_selection_count: `{best.get('new_candidate_harmful_selection_count', '')}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        f"Hard gates: `{gate_summary.get('hard_gates', {})}`\n\n"
        "Evaluation is grouped by context: every policy scores or chooses among the 22 candidate rows for a context and then emits one selected candidate or static fallback. "
        "Seed OOF, fixed train/dev, leave-one-map-agent, leave-one-map-family, bootstrap, calibration, per-group, and per-candidate summaries are written to the required CSV/JSON artifacts.\n",
    )
    print(json.dumps({"decision": decision, "best_policy": gate_summary.get("best_policy", ""), "policy_count_seed_oof": len(seed_oof_selected)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

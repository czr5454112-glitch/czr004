"""Evaluate G5.12 against Repair5G.5.13 hard-control baselines."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from eval_repair5g512_candidate_regret_ranker import decisions_for_model, select_model_policy  # noqa: E402
from repair5g512_common import (  # noqa: E402
    ADDITIVE_CANDIDATE,
    CLOSED_CLAIMS,
    DEFAULT_MARGIN,
    SLOW_DECAY_HIGH_SHIELD_CANDIDATE,
    STATIC_FLOW_SHIELD_CANDIDATE,
    count_by,
    finite_number,
    leakage_scan,
    mean,
    observed_id_flags,
    read_csv_rows,
    read_json,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)
from repair5g513_common import (  # noqa: E402
    G513_CLOSED_CLAIMS,
    candidate_train_stats,
    context_decision_row,
    grouped_contexts,
    map_agent_key,
    selected_for_fixed_candidate,
    selected_for_oracle,
    selected_for_safe_map_agent_gate,
    selected_for_safe_slow_decay_gate,
    summarize_selected,
)
from train_repair5g512_candidate_regret_ranker import (  # noqa: E402
    fit_ridge,
    matrix,
    predict_model,
    random_feature_matrix,
    row_key,
    target,
    weights,
)


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g512_candidate_feature_matrix_v3.csv"
DEFAULT_MODEL = "outputs/reports/phase5p5_repair5g512_candidate_ranker_model.json"
DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g513_hard_control_eval.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g513_hard_control_eval.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g513_hard_control_eval_summary.json"
SEED = 20260607


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--model-json", type=Path, default=Path(DEFAULT_MODEL))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    return parser.parse_args(argv)


def row_metrics(row: dict[str, Any]) -> dict[str, float]:
    delta_static = finite_number(row.get("mean_delta_vs_static_primary"), math.inf)
    return {
        "mean_delta_vs_static": delta_static,
        "mean_delta_vs_additive": finite_number(row.get("mean_delta_vs_additive_primary"), math.inf),
        "harmful_vs_static": 1.0 if delta_static >= DEFAULT_MARGIN else 0.0,
        "coverage": 0.0 if str(row.get("candidate_id", "")) == STATIC_FLOW_SHIELD_CANDIDATE else 1.0,
        "regret_to_oracle": finite_number(row.get("oracle_regret_primary"), math.inf),
    }


def threshold_policy_metrics(
    rows: list[dict[str, Any]], pred_delta_values: np.ndarray, pred_risk_values: np.ndarray, thresholds: dict[str, float]
) -> dict[str, float]:
    pred_delta = {row_key(row): float(value) for row, value in zip(rows, pred_delta_values)}
    pred_risk = {row_key(row): float(max(0.0, min(1.0, value))) for row, value in zip(rows, pred_risk_values)}
    selected = []
    for group in grouped_contexts(rows).values():
        selected_row, _, _, _, _ = select_model_policy(
            group,
            {str(row.get("candidate_id", "")): pred_delta[row_key(row)] for row in group},
            {str(row.get("candidate_id", "")): pred_risk[row_key(row)] for row in group},
            thresholds,
        )
        selected.append(selected_row)
    metrics = [row_metrics(row) for row in selected]
    return {
        "contexts": float(len(selected)),
        "mean_delta_vs_static": mean(metric["mean_delta_vs_static"] for metric in metrics),
        "mean_delta_vs_additive": mean(metric["mean_delta_vs_additive"] for metric in metrics),
        "harmful_vs_static_rate": mean(metric["harmful_vs_static"] for metric in metrics),
        "coverage": mean(metric["coverage"] for metric in metrics),
        "fallback_rate": 1.0 - mean(metric["coverage"] for metric in metrics),
    }


def choose_thresholds_for_subset(
    train_rows: list[dict[str, Any]], pred_delta: np.ndarray, pred_risk: np.ndarray
) -> tuple[dict[str, float], dict[str, float]]:
    best_thresholds = {
        "predicted_delta_threshold": -DEFAULT_MARGIN,
        "harmful_risk_threshold": 0.05,
        "confidence_margin_threshold": 0.0,
    }
    best_metrics = threshold_policy_metrics(train_rows, pred_delta, pred_risk, best_thresholds)
    for delta_threshold in [-0.020, -0.010, -DEFAULT_MARGIN, 0.0]:
        for risk_threshold in [0.03, 0.05, 0.075, 0.10]:
            for confidence_margin in [0.0, 0.001, 0.005, 0.010]:
                thresholds = {
                    "predicted_delta_threshold": delta_threshold,
                    "harmful_risk_threshold": risk_threshold,
                    "confidence_margin_threshold": confidence_margin,
                }
                metrics = threshold_policy_metrics(train_rows, pred_delta, pred_risk, thresholds)
                if (
                    metrics["harmful_vs_static_rate"] <= 0.05
                    and metrics["mean_delta_vs_static"] < best_metrics["mean_delta_vs_static"]
                ):
                    best_thresholds = thresholds
                    best_metrics = metrics
    return best_thresholds, best_metrics


def fit_subset_model(
    train_rows: list[dict[str, Any]], feature_names: list[str], *, ridge_alpha: float
) -> dict[str, Any]:
    X_train = matrix(train_rows, feature_names)
    y_delta = target(train_rows, "mean_delta_vs_static_primary")
    y_risk = np.array(
        [
            1.0 if finite_number(row.get("mean_delta_vs_static_primary"), math.inf) >= DEFAULT_MARGIN else 0.0
            for row in train_rows
        ],
        dtype=float,
    )
    w = weights(train_rows)
    delta_model = fit_ridge(X_train, y_delta, w, ridge_alpha)
    risk_model = fit_ridge(X_train, y_risk, w, ridge_alpha)
    pred_delta = predict_model(delta_model, X_train)
    pred_risk = np.clip(predict_model(risk_model, X_train), 0.0, 1.0)
    thresholds, train_metrics = choose_thresholds_for_subset(train_rows, pred_delta, pred_risk)
    return {
        "feature_names": feature_names,
        "delta_model": delta_model,
        "risk_model": risk_model,
        "thresholds": thresholds,
        "train_policy_metrics": train_metrics,
    }


def decisions_for_subset_model(
    rows: list[dict[str, Any]], policy: str, model: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pred_delta_array = predict_model(model["delta_model"], matrix(rows, model["feature_names"]))
    pred_risk_array = np.clip(predict_model(model["risk_model"], matrix(rows, model["feature_names"])), 0.0, 1.0)
    pred_delta = {row_key(row): float(value) for row, value in zip(rows, pred_delta_array)}
    pred_risk = {row_key(row): float(value) for row, value in zip(rows, pred_risk_array)}
    selected = []
    context_rows = []
    for key, group in sorted(grouped_contexts(rows).items()):
        selected_row, reason, best_delta, best_risk, margin = select_model_policy(
            group,
            {str(row.get("candidate_id", "")): pred_delta[row_key(row)] for row in group},
            {str(row.get("candidate_id", "")): pred_risk[row_key(row)] for row in group},
            model["thresholds"],
        )
        selected.append(selected_row)
        row = context_decision_row(policy, selected_row, reason)
        row.update(
            {
                "predicted_best_delta": best_delta,
                "predicted_best_harmful_risk": best_risk,
                "predicted_margin": margin,
            }
        )
        context_rows.append(row)
    return selected, context_rows


def rows_for_selected(policy: str, selected: list[dict[str, Any]], reason: str) -> list[dict[str, Any]]:
    return [context_decision_row(policy, row, reason) for row in selected]


def feature_subsets(feature_names: list[str]) -> dict[str, list[str]]:
    return {
        "candidate_param_only_ranker": [
            name for name in feature_names if name.startswith("feature_candidate_")
        ],
        "no_map_family_feature_ablation": [
            name for name in feature_names if not name.startswith("feature_map_family_")
        ],
        "no_agent_feature_ablation": [
            name
            for name in feature_names
            if "agent" not in name
            and "agents" not in name
            and "per_agent" not in name
        ],
        "no_candidate_param_ablation": [
            name
            for name in feature_names
            if not name.startswith("feature_candidate_")
            and not name.startswith("feature_interaction_")
        ],
        "interaction_only_ablation": [
            name for name in feature_names if name.startswith("feature_interaction_")
        ],
    }


def random_candidate_selected(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    selected = []
    for _, group in sorted(grouped_contexts(rows).items()):
        selected.append(rng.choice(sorted(group, key=lambda row: str(row.get("candidate_id", "")))))
    return selected


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_csv, root))
    model = read_json(resolve(args.model_json, root))
    train_rows = [row for row in rows if row.get("split") == "train"]
    dev_rows = [row for row in rows if row.get("split") == "dev"]
    feature_names = [name for name in rows[0] if name.startswith("feature_")] if rows else []
    leak = leakage_scan(feature_names)

    policy_selected: dict[str, list[dict[str, Any]]] = {}
    context_rows: list[dict[str, Any]] = []
    selected_primary, primary_decisions, _, _ = decisions_for_model(dev_rows, model, "primary", model["thresholds"])
    policy_selected["g512_ranker"] = selected_primary
    for row in primary_decisions:
        selected = next(
            item
            for item in selected_primary
            if item.get("normalized_context_key") == row.get("normalized_context_key")
        )
        context = context_decision_row("g512_ranker", selected, str(row.get("selection_reason", "")))
        context.update(
            {
                "predicted_best_delta": row.get("predicted_best_delta", ""),
                "predicted_best_harmful_risk": row.get("predicted_best_harmful_risk", ""),
                "predicted_margin": row.get("predicted_margin", ""),
            }
        )
        context_rows.append(context)

    fixed_policies = {
        "static_flow_shield": STATIC_FLOW_SHIELD_CANDIDATE,
        "additive_ltm": ADDITIVE_CANDIDATE,
        "slow_decay_high_shield_fixed": SLOW_DECAY_HIGH_SHIELD_CANDIDATE,
    }
    for policy, candidate in fixed_policies.items():
        selected = selected_for_fixed_candidate(dev_rows, candidate)
        policy_selected[policy] = selected
        context_rows.extend(rows_for_selected(policy, selected, f"fixed_{candidate}"))

    safe_slow, safe_slow_choices = selected_for_safe_slow_decay_gate(train_rows, dev_rows)
    policy_selected["safe_slow_decay_train_gate"] = safe_slow
    context_rows.extend(rows_for_selected("safe_slow_decay_train_gate", safe_slow, "train_map_agent_safe_slow_decay_gate"))
    safe_map, safe_map_choices = selected_for_safe_map_agent_gate(train_rows, dev_rows)
    policy_selected["safe_train_only_map_agent_gate"] = safe_map
    context_rows.extend(rows_for_selected("safe_train_only_map_agent_gate", safe_map, "train_map_agent_best_safe_candidate_gate"))

    global_stats = {}
    for candidate, stats in sorted(candidate_train_stats(train_rows).items()):
        global_stats[candidate] = stats
    safe_global = [
        (stats["mean_delta_vs_static"], candidate)
        for candidate, stats in global_stats.items()
        if candidate not in {STATIC_FLOW_SHIELD_CANDIDATE, ADDITIVE_CANDIDATE}
        and stats["mean_delta_vs_static"] <= -DEFAULT_MARGIN
        and stats["harmful_vs_static_rate"] <= 0.05
    ]
    global_candidate = min(safe_global)[1] if safe_global else STATIC_FLOW_SHIELD_CANDIDATE
    selected = selected_for_fixed_candidate(dev_rows, global_candidate)
    policy_selected["candidate_only_mean_delta_prior"] = selected
    context_rows.extend(rows_for_selected("candidate_only_mean_delta_prior", selected, f"train_global_safe_candidate_{global_candidate}"))

    policy_selected["map_agent_only_gate"] = safe_map
    context_rows.extend(rows_for_selected("map_agent_only_gate", safe_map, "alias_train_map_agent_gate_no_candidate_features"))

    for policy, subset in feature_subsets(feature_names).items():
        subset_model = fit_subset_model(train_rows, subset, ridge_alpha=args.ridge_alpha)
        selected, subset_context_rows = decisions_for_subset_model(dev_rows, policy, subset_model)
        policy_selected[policy] = selected
        for row in subset_context_rows:
            row["feature_count"] = len(subset)
            row["train_thresholds_json"] = json.dumps(subset_model["thresholds"], sort_keys=True)
        context_rows.extend(subset_context_rows)

    selected_random_feature, _, _, _ = decisions_for_model(dev_rows, model, "random_feature", model["thresholds"])
    policy_selected["true_random_feature_model"] = selected_random_feature
    context_rows.extend(
        context_decision_row("true_random_feature_model", row, "g512_random_feature_control")
        for row in selected_random_feature
    )
    selected_shuffled_label, _, _, _ = decisions_for_model(dev_rows, model, "shuffled_label", model["thresholds"])
    policy_selected["true_shuffled_label_model"] = selected_shuffled_label
    context_rows.extend(
        context_decision_row("true_shuffled_label_model", row, "g512_shuffled_label_control")
        for row in selected_shuffled_label
    )
    oracle = selected_for_oracle(dev_rows)
    policy_selected["oracle_upper_bound"] = oracle
    context_rows.extend(rows_for_selected("oracle_upper_bound", oracle, "oracle_upper_bound"))
    random_selected = random_candidate_selected(dev_rows)
    policy_selected["random_candidate"] = random_selected
    context_rows.extend(rows_for_selected("random_candidate", random_selected, "deterministic_random_candidate_control"))

    policy_order = [
        "g512_ranker",
        "static_flow_shield",
        "additive_ltm",
        "slow_decay_high_shield_fixed",
        "safe_slow_decay_train_gate",
        "safe_train_only_map_agent_gate",
        "candidate_param_only_ranker",
        "candidate_only_mean_delta_prior",
        "map_agent_only_gate",
        "no_map_family_feature_ablation",
        "no_agent_feature_ablation",
        "no_candidate_param_ablation",
        "interaction_only_ablation",
        "true_random_feature_model",
        "true_shuffled_label_model",
        "random_candidate",
        "oracle_upper_bound",
    ]
    policy_summaries = [summarize_selected(policy, policy_selected[policy]) for policy in policy_order]
    summary_by_policy = {str(row["policy"]): row for row in policy_summaries}
    primary = summary_by_policy["g512_ranker"]

    def beats(policy: str) -> bool:
        return finite_number(primary.get("mean_delta_vs_static"), math.inf) < finite_number(
            summary_by_policy[policy].get("mean_delta_vs_static"), math.inf
        )

    gates = {
        "mean_delta_vs_static_lt_0": finite_number(primary.get("mean_delta_vs_static"), math.inf) < 0.0,
        "mean_delta_vs_additive_lt_0": finite_number(primary.get("mean_delta_vs_additive"), math.inf) < 0.0,
        "harmful_vs_static_rate_le_0p05": finite_number(primary.get("harmful_vs_static_rate"), math.inf) <= 0.05,
        "beats_safe_slow_decay_train_gate": beats("safe_slow_decay_train_gate"),
        "beats_safe_train_only_map_agent_gate": beats("safe_train_only_map_agent_gate"),
        "beats_candidate_param_only_ranker": beats("candidate_param_only_ranker"),
        "beats_candidate_only_mean_delta_prior": beats("candidate_only_mean_delta_prior"),
        "beats_map_agent_only_gate": beats("map_agent_only_gate"),
        "beats_true_random_feature_model": beats("true_random_feature_model"),
        "beats_true_shuffled_label_model": beats("true_shuffled_label_model"),
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
        "no_ids_166_205": observed_id_flags(dev_rows)["ids_166_205_untouched"],
        "runtime_claim_allowed_false": CLOSED_CLAIMS["runtime_claim_allowed"] is False,
    }
    if not gates["beats_safe_slow_decay_train_gate"] or not gates["beats_safe_train_only_map_agent_gate"]:
        decision = "candidate_ranker_signal_reduced_to_simple_prior_continue_rich_features"
    elif all(
        gates[name]
        for name in [
            "mean_delta_vs_static_lt_0",
            "mean_delta_vs_additive_lt_0",
            "harmful_vs_static_rate_le_0p05",
            "beats_candidate_param_only_ranker",
            "beats_map_agent_only_gate",
            "beats_true_random_feature_model",
            "beats_true_shuffled_label_model",
            "forbidden_feature_count_eq_0",
            "no_ids_166_205",
        ]
    ):
        decision = "hard_controlled_ranker_passed_continue_rich_safety_preflight"
    else:
        decision = "g512_hard_controls_failed_continue_rich_features"

    output_rows = policy_summaries + context_rows
    write_csv_rows(resolve(args.output_csv, root), output_rows)
    summary = {
        "schema_version": "phase5p5_repair5g513_hard_control_eval_summary_v1",
        "decision": decision,
        "dev_contexts": len({str(row.get("normalized_context_key", "")) for row in dev_rows}),
        "dev_rows": len(dev_rows),
        "train_rows": len(train_rows),
        "feature_count": len(feature_names),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "primary_policy": primary,
        "policy_summaries": policy_summaries,
        "safe_slow_decay_train_gate_choices": safe_slow_choices,
        "safe_train_only_map_agent_gate_choices": safe_map_choices,
        "candidate_only_mean_delta_prior_choice": global_candidate,
        "candidate_train_stats": global_stats,
        "gates": gates,
        **G513_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    policy_lines = "\n".join(
        f"- `{row['policy']}`: mean_delta_vs_static={finite_number(row.get('mean_delta_vs_static'), math.inf):.6f}, "
        f"harmful_rate={finite_number(row.get('harmful_vs_static_rate'), math.inf):.3f}, "
        f"coverage={finite_number(row.get('coverage'), math.inf):.3f}, "
        f"regret_to_oracle={finite_number(row.get('regret_to_oracle'), math.inf):.6f}"
        for row in policy_summaries
    )
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.13 Hard-Control Eval\n\n"
        f"- decision: `{decision}`\n"
        f"- dev_contexts: `{summary['dev_contexts']}`\n"
        f"- primary_policy: `{primary}`\n"
        f"- gates: `{gates}`\n"
        f"- safe_slow_decay_train_gate_choices: `{safe_slow_choices}`\n"
        f"- safe_train_only_map_agent_gate_choices: `{safe_map_choices}`\n"
        f"- runtime_claim_allowed: `false`\n\n"
        "## Policy Summaries\n\n"
        f"{policy_lines}\n\n"
        "All learned and prior controls are evaluated as grouped context decisions: score or select over all 14 candidates, choose a candidate only when the policy gate passes, otherwise fall back to static flow-shield. "
        "If the G5.12 ranker does not beat train-only safe priors, the result is reported as a simple-prior signal reduction rather than hidden as a pass.\n",
    )
    print(json.dumps({"decision": decision, "dev_contexts": summary["dev_contexts"], "primary_mean_delta": primary["mean_delta_vs_static"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

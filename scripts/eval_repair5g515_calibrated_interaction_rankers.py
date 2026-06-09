"""Evaluate G5.15 interaction rankers with seed-OOF calibration and controls."""

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

from eval_repair5g512_candidate_regret_ranker import select_model_policy  # noqa: E402
from repair5g512_common import (  # noqa: E402
    DEFAULT_MARGIN,
    SLOW_DECAY_HIGH_SHIELD_CANDIDATE,
    STATIC_FLOW_SHIELD_CANDIDATE,
    finite_number,
    leakage_scan,
    observed_id_flags,
    read_csv_rows,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)
from repair5g513_common import (  # noqa: E402
    context_decision_row,
    grouped_contexts,
    selected_for_fixed_candidate,
    selected_for_oracle,
    selected_for_safe_map_agent_gate,
    selected_for_safe_slow_decay_gate,
)
from repair5g515_common import (  # noqa: E402
    DEFAULT_EVAL_CONTEXTS,
    DEFAULT_EVAL_SUMMARY,
    DEFAULT_V5_MATRIX,
    G515_CLOSED_CLAIMS,
    add_scope_to_summaries,
    best_interaction_policy,
    bootstrap_rows,
    calibration_rows,
    context_only_rich_features,
    context_row,
    feature_columns,
    gate_flags_for_rows,
    grouped_candidate_count_ok,
    harmful_group_rows,
    no_rich_features,
    no_rich_interaction_features,
    policy_summary,
    rich_interaction_feature_names,
    risk_metric_name,
    rows_by_seed,
    rows_with_seed,
    rows_without_seed,
    summary_by_policy,
    v4_reproduced_features,
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
from train_repair5g515_pairwise_context_ranker import fit_pairwise_model, select_pairwise  # noqa: E402
from train_repair5g515_two_stage_safety_ranker import fit_two_stage_model, select_two_stage  # noqa: E402


DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g515_calibrated_interaction_rankers_eval.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g515_calibrated_interaction_rankers.md"
SEED = 20260607


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_V5_MATRIX))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--context-decisions-csv", type=Path, default=Path(DEFAULT_EVAL_CONTEXTS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_EVAL_SUMMARY))
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    parser.add_argument("--bootstrap-samples", type=int, default=1000)
    return parser.parse_args(argv)


def candidate_param_features(rows: list[dict[str, Any]]) -> list[str]:
    return [name for name in feature_columns(rows) if name.startswith("feature_candidate_")]


def linear_matrix(rows: list[dict[str, Any]], model: dict[str, Any]) -> np.ndarray:
    if model.get("random_features"):
        return random_feature_matrix(rows)
    return matrix(rows, model["feature_names"])


def fit_linear_policy(
    train_rows: list[dict[str, Any]],
    feature_names: list[str],
    *,
    policy: str,
    ridge_alpha: float,
    random_features: bool = False,
    shuffled_labels: bool = False,
) -> dict[str, Any]:
    X = random_feature_matrix(train_rows) if random_features else matrix(train_rows, feature_names)
    y_delta = target(train_rows, "mean_delta_vs_static_primary")
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
    w = weights(train_rows)
    model = {
        "policy": policy,
        "feature_names": feature_names,
        "random_features": random_features,
        "delta_model": fit_ridge(X, y_delta, w, ridge_alpha),
        "risk_model": fit_ridge(X, y_risk, w, ridge_alpha),
        "ridge_alpha": ridge_alpha,
    }
    model["thresholds"] = choose_linear_thresholds(train_rows, model)
    return model


def predict_linear(rows: list[dict[str, Any]], model: dict[str, Any]) -> tuple[dict[str, float], dict[str, float]]:
    X = linear_matrix(rows, model)
    delta = predict_model(model["delta_model"], X)
    risk = np.clip(predict_model(model["risk_model"], X), 0.0, 1.0)
    return (
        {row_key(row): float(value) for row, value in zip(rows, delta)},
        {row_key(row): float(value) for row, value in zip(rows, risk)},
    )


def select_linear(
    rows: list[dict[str, Any]],
    model: dict[str, Any],
    *,
    policy: str,
    eval_scope: str,
    fold_seed: int | str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pred_delta, pred_risk = predict_linear(rows, model)
    selected: list[dict[str, Any]] = []
    context_rows: list[dict[str, Any]] = []
    for key, group in sorted(grouped_contexts(rows).items()):
        selected_row, reason, best_delta, best_risk, margin = select_model_policy(
            group,
            {str(row.get("candidate_id", "")): pred_delta[row_key(row)] for row in group},
            {str(row.get("candidate_id", "")): pred_risk[row_key(row)] for row in group},
            model["thresholds"],
        )
        selected.append(selected_row)
        best = min(group, key=lambda row: (pred_delta[row_key(row)], pred_risk[row_key(row)], str(row.get("candidate_id", ""))))
        context_rows.append(
            context_row(
                policy,
                selected_row,
                reason,
                eval_scope=eval_scope,
                fold_seed=fold_seed,
                predicted_best_delta=best_delta,
                predicted_best_harmful_risk=best_risk,
                predicted_margin=margin,
                extra={"predicted_best_candidate_id": best.get("candidate_id", "")},
            )
        )
    return selected, context_rows


def choose_linear_thresholds(train_rows: list[dict[str, Any]], model: dict[str, Any]) -> dict[str, float]:
    best = {
        "predicted_delta_threshold": -DEFAULT_MARGIN,
        "harmful_risk_threshold": 0.05,
        "confidence_margin_threshold": 0.0,
    }
    best_summary = policy_summary(model["policy"], select_linear(train_rows, {**model, "thresholds": best}, policy=model["policy"], eval_scope="train")[0])
    for delta_thr in [-0.020, -0.010, -DEFAULT_MARGIN, 0.0]:
        for risk_thr in [0.05, 0.075, 0.10]:
            for margin_thr in [0.0, 0.005]:
                thresholds = {
                    "predicted_delta_threshold": delta_thr,
                    "harmful_risk_threshold": risk_thr,
                    "confidence_margin_threshold": margin_thr,
                }
                selected, _ = select_linear(train_rows, {**model, "thresholds": thresholds}, policy=model["policy"], eval_scope="train")
                summary = policy_summary(model["policy"], selected)
                harmful = finite_number(summary.get("harmful_vs_static_rate"), math.inf)
                rau = finite_number(summary.get("risk_adjusted_utility_lambda_0p10"), math.inf)
                best_rau = finite_number(best_summary.get("risk_adjusted_utility_lambda_0p10"), math.inf)
                if harmful <= 0.05 and (rau < best_rau or (rau == best_rau and summary["coverage"] > best_summary["coverage"])):
                    best = thresholds
                    best_summary = summary
    return best


def shuffled_train_rows_by_context(train_rows: list[dict[str, Any]], columns: list[str], *, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    grouped = grouped_contexts(train_rows)
    contexts = sorted(grouped)
    shuffled_contexts = contexts[:]
    rng.shuffle(shuffled_contexts)
    source_for_context = {context: shuffled_contexts[index % len(shuffled_contexts)] for index, context in enumerate(contexts)}
    source_by_context_candidate = {
        (context, str(row.get("candidate_id", ""))): row
        for context, group in grouped.items()
        for row in group
    }
    out: list[dict[str, Any]] = []
    for row in train_rows:
        item = dict(row)
        source_context = source_for_context[str(row.get("normalized_context_key", ""))]
        source = source_by_context_candidate.get((source_context, str(row.get("candidate_id", ""))))
        if source is None:
            source = grouped[source_context][0]
        for column in columns:
            item[column] = source.get(column, 0.0)
        out.append(item)
    return out


def random_candidate_selected(rows: list[dict[str, Any]], *, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    return [rng.choice(sorted(group, key=lambda row: str(row.get("candidate_id", "")))) for _, group in sorted(grouped_contexts(rows).items())]


def add_simple_context_rows(policy: str, selected: list[dict[str, Any]], *, reason: str, eval_scope: str, fold_seed: int | str | None) -> list[dict[str, Any]]:
    out = []
    for row in selected:
        item = context_decision_row(policy, row, reason)
        item.update(
            {
                "eval_scope": eval_scope,
                "fold_seed": "" if fold_seed is None else fold_seed,
                "predicted_best_delta": "",
                "predicted_best_harmful_risk": "",
                "predicted_margin": "",
            }
        )
        out.append(item)
    return out


def merge_selected(target: dict[str, list[dict[str, Any]]], source: dict[str, list[dict[str, Any]]]) -> None:
    for policy, rows in source.items():
        target.setdefault(policy, []).extend(rows)


def evaluate_once(
    train_rows: list[dict[str, Any]],
    eval_rows: list[dict[str, Any]],
    *,
    eval_scope: str,
    fold_seed: int | str | None,
    ridge_alpha: float,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    selected: dict[str, list[dict[str, Any]]] = {}
    contexts: list[dict[str, Any]] = []

    two_stage_model = fit_two_stage_model(train_rows, ridge_alpha=ridge_alpha)
    two_stage_selected, two_stage_contexts = select_two_stage(
        eval_rows, two_stage_model, policy="two_stage_safety_ranker", eval_scope=eval_scope, fold_seed=fold_seed
    )
    selected["two_stage_safety_ranker"] = two_stage_selected
    contexts.extend(two_stage_contexts)

    pairwise_model = fit_pairwise_model(train_rows, ridge_alpha=ridge_alpha)
    pairwise_selected, pairwise_contexts = select_pairwise(
        eval_rows, pairwise_model, policy="pairwise_context_ranker", eval_scope=eval_scope, fold_seed=fold_seed
    )
    selected["pairwise_context_ranker"] = pairwise_selected
    contexts.extend(pairwise_contexts)

    feature_sets = {
        "v4_g514_ranker_reproduced": v4_reproduced_features(train_rows),
        "v3_g512_ranker_reproduced": no_rich_features(train_rows),
        "no_rich_feature_ablation": no_rich_features(train_rows),
        "no_rich_interaction_ablation": no_rich_interaction_features(train_rows),
        "context_only_rich_ablation": context_only_rich_features(train_rows),
        "candidate_param_only_ranker": candidate_param_features(train_rows),
    }
    for policy, features in feature_sets.items():
        model = fit_linear_policy(train_rows, features, policy=policy, ridge_alpha=ridge_alpha)
        policy_selected, policy_contexts = select_linear(eval_rows, model, policy=policy, eval_scope=eval_scope, fold_seed=fold_seed)
        selected[policy] = policy_selected
        contexts.extend(policy_contexts)

    shuffled_cols = rich_interaction_feature_names(train_rows)
    shuffled_train = shuffled_train_rows_by_context(train_rows, shuffled_cols, seed=SEED)
    shuffled_model = fit_linear_policy(
        shuffled_train,
        feature_columns(shuffled_train),
        policy="rich_interactions_shuffled_within_train_split",
        ridge_alpha=ridge_alpha,
    )
    shuffled_selected, shuffled_contexts = select_linear(
        eval_rows,
        shuffled_model,
        policy="rich_interactions_shuffled_within_train_split",
        eval_scope=eval_scope,
        fold_seed=fold_seed,
    )
    selected["rich_interactions_shuffled_within_train_split"] = shuffled_selected
    contexts.extend(shuffled_contexts)

    random_model = fit_linear_policy(
        train_rows,
        [],
        policy="true_random_feature_model",
        ridge_alpha=ridge_alpha,
        random_features=True,
    )
    random_feature_selected, random_feature_contexts = select_linear(
        eval_rows,
        random_model,
        policy="true_random_feature_model",
        eval_scope=eval_scope,
        fold_seed=fold_seed,
    )
    selected["true_random_feature_model"] = random_feature_selected
    contexts.extend(random_feature_contexts)

    shuffled_label_model = fit_linear_policy(
        train_rows,
        feature_columns(train_rows),
        policy="true_shuffled_label_model",
        ridge_alpha=ridge_alpha,
        shuffled_labels=True,
    )
    shuffled_label_selected, shuffled_label_contexts = select_linear(
        eval_rows,
        shuffled_label_model,
        policy="true_shuffled_label_model",
        eval_scope=eval_scope,
        fold_seed=fold_seed,
    )
    selected["true_shuffled_label_model"] = shuffled_label_selected
    contexts.extend(shuffled_label_contexts)

    safe_slow, _ = selected_for_safe_slow_decay_gate(train_rows, eval_rows)
    selected["safe_slow_decay_train_gate"] = safe_slow
    contexts.extend(add_simple_context_rows("safe_slow_decay_train_gate", safe_slow, reason="fold_train_safe_slow_decay_gate", eval_scope=eval_scope, fold_seed=fold_seed))
    safe_map, _ = selected_for_safe_map_agent_gate(train_rows, eval_rows)
    selected["safe_train_only_map_agent_gate"] = safe_map
    selected["map_agent_only_gate"] = safe_map
    contexts.extend(add_simple_context_rows("safe_train_only_map_agent_gate", safe_map, reason="fold_train_safe_map_agent_gate", eval_scope=eval_scope, fold_seed=fold_seed))
    contexts.extend(add_simple_context_rows("map_agent_only_gate", safe_map, reason="alias_safe_map_agent_gate", eval_scope=eval_scope, fold_seed=fold_seed))
    fixed_slow = selected_for_fixed_candidate(eval_rows, SLOW_DECAY_HIGH_SHIELD_CANDIDATE)
    selected["fixed_slow_decay_high_shield"] = fixed_slow
    contexts.extend(add_simple_context_rows("fixed_slow_decay_high_shield", fixed_slow, reason="fixed_slow_decay_high_shield", eval_scope=eval_scope, fold_seed=fold_seed))
    random_selected = random_candidate_selected(eval_rows, seed=SEED + int(finite_number(fold_seed, 0.0)))
    selected["random_candidate"] = random_selected
    contexts.extend(add_simple_context_rows("random_candidate", random_selected, reason="deterministic_random_candidate", eval_scope=eval_scope, fold_seed=fold_seed))
    oracle = selected_for_oracle(eval_rows)
    selected["oracle_upper_bound"] = oracle
    contexts.extend(add_simple_context_rows("oracle_upper_bound", oracle, reason="oracle_upper_bound", eval_scope=eval_scope, fold_seed=fold_seed))
    return selected, contexts


def summarize_selected_map(selected: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    order = [
        "two_stage_safety_ranker",
        "pairwise_context_ranker",
        "v3_g512_ranker_reproduced",
        "v4_g514_ranker_reproduced",
        "no_rich_feature_ablation",
        "no_rich_interaction_ablation",
        "context_only_rich_ablation",
        "rich_interactions_shuffled_within_train_split",
        "candidate_param_only_ranker",
        "map_agent_only_gate",
        "safe_slow_decay_train_gate",
        "safe_train_only_map_agent_gate",
        "fixed_slow_decay_high_shield",
        "random_candidate",
        "true_random_feature_model",
        "true_shuffled_label_model",
        "oracle_upper_bound",
    ]
    return [policy_summary(policy, selected[policy]) for policy in order if policy in selected]


def decision_from_gates(gates: dict[str, bool]) -> str:
    if all(
        gates[key]
        for key in [
            "harmful_vs_static_rate_le_0p05",
            "risk_adjusted_improves_over_v3_lambda_0p05",
            "risk_adjusted_improves_over_v3_lambda_0p10",
            "risk_adjusted_improves_over_v4_lambda_0p05",
            "risk_adjusted_improves_over_v4_lambda_0p10",
            "risk_adjusted_beats_safe_slow_decay_train_gate",
            "risk_adjusted_beats_safe_train_only_map_agent_gate",
            "beats_rich_interactions_shuffled_control",
            "forbidden_feature_count_eq_0",
            "no_ids_166_205",
            "runtime_claim_allowed_false",
        ]
    ):
        return "interaction_ranker_passed_continue_safety_boundary_expansion"
    if not gates["harmful_vs_static_rate_le_0p05"]:
        return "interaction_ranker_harmful_failed_continue_calibration"
    if not gates["risk_adjusted_improves_over_v4_lambda_0p10"]:
        return "interaction_ranker_no_better_than_v4_continue_feature_design"
    if not gates["beats_rich_interactions_shuffled_control"]:
        return "interaction_signal_reduced_to_shuffled_control_continue_probe_or_lattice"
    return "calibration_failed_continue_safety_gate"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_csv, root))
    flags = gate_flags_for_rows(rows)
    oof_selected: dict[str, list[dict[str, Any]]] = {}
    context_rows: list[dict[str, Any]] = []
    for seed in rows_by_seed(rows):
        train_rows = rows_without_seed(rows, seed)
        eval_rows = rows_with_seed(rows, seed)
        fold_selected, fold_contexts = evaluate_once(
            train_rows,
            eval_rows,
            eval_scope="oof",
            fold_seed=seed,
            ridge_alpha=args.ridge_alpha,
        )
        merge_selected(oof_selected, fold_selected)
        context_rows.extend(fold_contexts)

    dev_train = [row for row in rows if row.get("split") == "train"]
    dev_eval = [row for row in rows if row.get("split") == "dev"]
    dev_selected, dev_contexts = evaluate_once(
        dev_train,
        dev_eval,
        eval_scope="fixed_151_155_dev",
        fold_seed="151_155",
        ridge_alpha=args.ridge_alpha,
    )
    context_rows.extend(dev_contexts)

    oof_summaries = summarize_selected_map(oof_selected)
    dev_summaries = summarize_selected_map(dev_selected)
    oof_by_policy = summary_by_policy(oof_summaries)
    primary_policy = best_interaction_policy(oof_by_policy)
    primary = oof_by_policy.get(primary_policy, {})
    leak = leakage_scan(feature_columns(rows))
    feature_flags = observed_id_flags(rows)

    def better_than(policy: str, lam: float) -> bool:
        if policy not in oof_by_policy or not primary:
            return False
        return finite_number(primary.get(risk_metric_name(lam)), math.inf) < finite_number(oof_by_policy[policy].get(risk_metric_name(lam)), math.inf)

    gates = {
        "harmful_vs_static_rate_le_0p05": finite_number(primary.get("harmful_vs_static_rate"), math.inf) <= 0.05,
        "harmful_vs_static_rate_le_0p033": finite_number(primary.get("harmful_vs_static_rate"), math.inf) <= 0.03333333333333333,
        "risk_adjusted_improves_over_v3_lambda_0p05": better_than("v3_g512_ranker_reproduced", 0.05),
        "risk_adjusted_improves_over_v3_lambda_0p10": better_than("v3_g512_ranker_reproduced", 0.10),
        "risk_adjusted_improves_over_v4_lambda_0p05": better_than("v4_g514_ranker_reproduced", 0.05),
        "risk_adjusted_improves_over_v4_lambda_0p10": better_than("v4_g514_ranker_reproduced", 0.10),
        "risk_adjusted_beats_safe_slow_decay_train_gate": better_than("safe_slow_decay_train_gate", 0.10),
        "risk_adjusted_beats_safe_train_only_map_agent_gate": better_than("safe_train_only_map_agent_gate", 0.10),
        "beats_rich_interactions_shuffled_control": better_than("rich_interactions_shuffled_within_train_split", 0.10),
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
        "no_ids_166_205": feature_flags["ids_166_205_untouched"],
        "runtime_claim_allowed_false": G515_CLOSED_CLAIMS["runtime_claim_allowed"] is False,
    }
    decision = decision_from_gates(gates)
    bootstrap = bootstrap_rows(oof_selected, samples=args.bootstrap_samples)
    calibration = calibration_rows(context_rows, policies=["two_stage_safety_ranker", "pairwise_context_ranker"])
    harmful_groups = harmful_group_rows(oof_selected)
    eval_rows_out = (
        add_scope_to_summaries("oof", oof_summaries)
        + add_scope_to_summaries("fixed_151_155_dev", dev_summaries)
        + bootstrap
        + calibration
        + harmful_groups
    )
    write_csv_rows(resolve(args.output_csv, root), eval_rows_out)
    write_csv_rows(resolve(args.context_decisions_csv, root), context_rows)
    summary = {
        "schema_version": "phase5p5_repair5g515_calibrated_interaction_rankers_summary_v1",
        "decision": decision,
        "primary_policy_name": primary_policy,
        "primary_policy": primary,
        "oof_contexts": len(grouped_contexts(rows)),
        "oof_rows": len(rows),
        "fixed_dev_contexts": len(grouped_contexts(dev_eval)),
        "fixed_dev_rows": len(dev_eval),
        "oof_policy_summaries": oof_summaries,
        "fixed_dev_policy_summaries": dev_summaries,
        "bootstrap_confidence_intervals_reported": True,
        "calibration_buckets_reported": True,
        "per_seed_harmful_counts_reported": True,
        "per_map_agent_harmful_counts_reported": True,
        "grouped_oof_sanity": {
            "exactly_14_candidate_rows_per_context": grouped_candidate_count_ok(rows),
            "seed_oof_folds": rows_by_seed(rows),
        },
        "feature_gates": flags,
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "gates": gates,
        **G515_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    policy_lines = "\n".join(
        f"- `{row['policy']}`: mean_delta_vs_static={finite_number(row.get('mean_delta_vs_static'), math.inf):.6f}, "
        f"harmful_rate={finite_number(row.get('harmful_vs_static_rate'), math.inf):.3f}, "
        f"coverage={finite_number(row.get('coverage'), math.inf):.3f}, "
        f"rau_0.10={finite_number(row.get('risk_adjusted_utility_lambda_0p10'), math.inf):.6f}"
        for row in oof_summaries
    )
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.15 Calibrated Interaction Ranker Evaluation\n\n"
        f"- decision: `{decision}`\n"
        f"- primary_policy_name: `{primary_policy}`\n"
        f"- primary_policy: `{primary}`\n"
        f"- oof_contexts: `{summary['oof_contexts']}`\n"
        f"- fixed_dev_contexts: `{summary['fixed_dev_contexts']}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- gates: `{gates}`\n"
        "- leave_one_seed_out_oof: `reported for seeds 146..155`\n"
        "- fixed_151_155_dev: `reported as diagnostic`\n"
        "- bootstrap_confidence_intervals: `reported`\n"
        "- calibration_buckets: `reported`\n"
        "- per_seed_and_map_agent_harmful_counts: `reported`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "## OOF Policy Summaries\n\n"
        f"{policy_lines}\n\n"
        "All learned thresholds are selected only on each fold-train split before evaluating the held-out seed. "
        "This remains a table-only offline diagnostic; no runtime policy is validated or exported.\n",
    )
    print(json.dumps({"decision": decision, "primary_policy_name": primary_policy, "primary_harmful": primary.get("harmful_vs_static_rate", "")}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

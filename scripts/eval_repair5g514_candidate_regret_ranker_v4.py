"""Evaluate the G5.14 v4 ranker against hard controls and ablations."""

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
    context_decision_row,
    grouped_contexts,
    map_agent_key,
    selected_for_fixed_candidate,
    selected_for_oracle,
    selected_for_safe_map_agent_gate,
    selected_for_safe_slow_decay_gate,
    summarize_selected,
)
from repair5g514_common import (  # noqa: E402
    DEFAULT_V4_MATRIX,
    DEFAULT_V4_MODEL,
    G514_CLOSED_CLAIMS,
    RISK_LAMBDAS,
    risk_adjusted_summary,
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
from train_repair5g514_candidate_regret_ranker_v4 import DEFAULT_V4_MODEL as MODEL_PATH  # noqa: E402


DEFAULT_G512_MODEL = "outputs/reports/phase5p5_repair5g512_candidate_ranker_model.json"
DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g514_candidate_ranker_v4_eval.csv"
DEFAULT_CONTEXT_CSV = "outputs/tables/phase5p5_repair5g514_candidate_ranker_v4_context_decisions.csv"
DEFAULT_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g514_candidate_ranker_v4_bootstrap.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g514_candidate_ranker_v4_eval.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g514_candidate_ranker_v4_eval_summary.json"
SEED = 20260607


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_V4_MATRIX))
    parser.add_argument("--model-json", type=Path, default=Path(DEFAULT_V4_MODEL))
    parser.add_argument("--g512-model-json", type=Path, default=Path(DEFAULT_G512_MODEL))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--context-decisions-csv", type=Path, default=Path(DEFAULT_CONTEXT_CSV))
    parser.add_argument("--bootstrap-csv", type=Path, default=Path(DEFAULT_BOOTSTRAP_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    parser.add_argument("--bootstrap-samples", type=int, default=1000)
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


def summarize_policy(policy: str, selected: list[dict[str, Any]]) -> dict[str, Any]:
    row = summarize_selected(policy, selected)
    row.update(risk_adjusted_summary(row))
    return row


def fit_subset_model(train_rows: list[dict[str, Any]], feature_names: list[str], ridge_alpha: float) -> dict[str, Any]:
    X_train = matrix(train_rows, feature_names)
    y_delta = target(train_rows, "mean_delta_vs_static_primary")
    y_risk = np.array(
        [1.0 if finite_number(row.get("mean_delta_vs_static_primary"), math.inf) >= DEFAULT_MARGIN else 0.0 for row in train_rows],
        dtype=float,
    )
    w = weights(train_rows)
    delta_model = fit_ridge(X_train, y_delta, w, ridge_alpha)
    risk_model = fit_ridge(X_train, y_risk, w, ridge_alpha)
    thresholds = {
        "predicted_delta_threshold": -DEFAULT_MARGIN,
        "harmful_risk_threshold": 0.05,
        "confidence_margin_threshold": 0.0,
    }
    return {"feature_names": feature_names, "delta_model": delta_model, "risk_model": risk_model, "thresholds": thresholds}


def decisions_for_subset(rows: list[dict[str, Any]], policy: str, model: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
        out = context_decision_row(policy, selected_row, reason)
        out.update(
            {
                "predicted_best_delta": best_delta,
                "predicted_best_harmful_risk": best_risk,
                "predicted_margin": margin,
            }
        )
        context_rows.append(out)
    return selected, context_rows


def shuffled_rich_train_rows(train_rows: list[dict[str, Any]], rich_features: list[str]) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    contexts = sorted({str(row.get("normalized_context_key", "")) for row in train_rows})
    shuffled = contexts[:]
    rng.shuffle(shuffled)
    source_by_context = {context: shuffled[index % len(shuffled)] for index, context in enumerate(contexts)}
    first_by_context = {str(row.get("normalized_context_key", "")): row for row in train_rows}
    out = []
    for row in train_rows:
        item = dict(row)
        source = first_by_context[source_by_context[str(row.get("normalized_context_key", ""))]]
        for feature in rich_features:
            item[feature] = source.get(feature, 0.0)
        out.append(item)
    return out


def random_candidate_selected(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    return [rng.choice(sorted(group, key=lambda row: str(row.get("candidate_id", "")))) for _, group in sorted(grouped_contexts(rows).items())]


def bootstrap_rows(policy_selected: dict[str, list[dict[str, Any]]], samples: int) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    out = []
    for policy, selected in sorted(policy_selected.items()):
        if not selected:
            continue
        metrics_by_sample: dict[str, list[float]] = {
            "mean_delta_vs_static": [],
            "harmful_vs_static_rate": [],
            "coverage": [],
            "regret_to_oracle": [],
            **{f"risk_adjusted_utility_lambda_{str(lam).replace('.', 'p')}": [] for lam in RISK_LAMBDAS},
        }
        for _ in range(samples):
            sample = [selected[rng.randrange(len(selected))] for _ in selected]
            metric_rows = [row_metrics(row) for row in sample]
            mean_delta = mean(metric["mean_delta_vs_static"] for metric in metric_rows)
            harmful = mean(metric["harmful_vs_static"] for metric in metric_rows)
            coverage = mean(metric["coverage"] for metric in metric_rows)
            regret = mean(metric["regret_to_oracle"] for metric in metric_rows)
            metrics_by_sample["mean_delta_vs_static"].append(mean_delta)
            metrics_by_sample["harmful_vs_static_rate"].append(harmful)
            metrics_by_sample["coverage"].append(coverage)
            metrics_by_sample["regret_to_oracle"].append(regret)
            for lam in RISK_LAMBDAS:
                metrics_by_sample[f"risk_adjusted_utility_lambda_{str(lam).replace('.', 'p')}"].append(mean_delta + lam * harmful)
        for metric, values in metrics_by_sample.items():
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


def add_context_rows(policy: str, selected: list[dict[str, Any]], reason: str) -> list[dict[str, Any]]:
    return [context_decision_row(policy, row, reason) for row in selected]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_csv, root))
    model = read_json(resolve(args.model_json, root))
    g512_model = read_json(resolve(args.g512_model_json, root))
    train_rows = [row for row in rows if row.get("split") == "train"]
    dev_rows = [row for row in rows if row.get("split") == "dev"]
    feature_names = [name for name in rows[0] if name.startswith("feature_")] if rows else []
    rich_features = [name for name in feature_names if name.startswith("feature_rich_")]
    leak = leakage_scan(feature_names)

    policy_selected: dict[str, list[dict[str, Any]]] = {}
    context_rows: list[dict[str, Any]] = []

    v4_selected, v4_decisions, _, _ = decisions_for_model(dev_rows, model, "primary", model["thresholds"])
    policy_selected["v4_ranker"] = v4_selected
    for row in v4_decisions:
        selected = next(item for item in v4_selected if item.get("normalized_context_key") == row.get("normalized_context_key"))
        context = context_decision_row("v4_ranker", selected, str(row.get("selection_reason", "")))
        context.update(
            {
                "predicted_best_delta": row.get("predicted_best_delta", ""),
                "predicted_best_harmful_risk": row.get("predicted_best_harmful_risk", ""),
                "predicted_margin": row.get("predicted_margin", ""),
            }
        )
        context_rows.append(context)

    g512_selected, _, _, _ = decisions_for_model(dev_rows, g512_model, "primary", g512_model["thresholds"])
    policy_selected["v3_g512_ranker_reproduced"] = g512_selected
    context_rows.extend(add_context_rows("v3_g512_ranker_reproduced", g512_selected, "g512_model_on_v4_rows"))

    for policy, candidate in {
        "static_flow_shield": STATIC_FLOW_SHIELD_CANDIDATE,
        "additive_ltm": ADDITIVE_CANDIDATE,
        "slow_decay_high_shield_fixed": SLOW_DECAY_HIGH_SHIELD_CANDIDATE,
    }.items():
        selected = selected_for_fixed_candidate(dev_rows, candidate)
        policy_selected[policy] = selected
        context_rows.extend(add_context_rows(policy, selected, f"fixed_{candidate}"))

    safe_slow, safe_slow_choices = selected_for_safe_slow_decay_gate(train_rows, dev_rows)
    policy_selected["safe_slow_decay_train_gate"] = safe_slow
    context_rows.extend(add_context_rows("safe_slow_decay_train_gate", safe_slow, "train_map_agent_safe_slow_decay_gate"))
    safe_map, safe_map_choices = selected_for_safe_map_agent_gate(train_rows, dev_rows)
    policy_selected["safe_train_only_map_agent_gate"] = safe_map
    policy_selected["map_agent_only_gate"] = safe_map
    context_rows.extend(add_context_rows("safe_train_only_map_agent_gate", safe_map, "train_map_agent_best_safe_candidate_gate"))
    context_rows.extend(add_context_rows("map_agent_only_gate", safe_map, "alias_train_map_agent_gate_no_candidate_features"))

    global_stats: dict[str, list[float]] = {}
    for row in train_rows:
        global_stats.setdefault(str(row.get("candidate_id", "")), []).append(finite_number(row.get("mean_delta_vs_static_primary"), math.inf))
    safe_global = [
        (mean(values), candidate)
        for candidate, values in global_stats.items()
        if candidate not in {STATIC_FLOW_SHIELD_CANDIDATE, ADDITIVE_CANDIDATE}
        and mean(values) <= -DEFAULT_MARGIN
        and mean(1.0 if value >= DEFAULT_MARGIN else 0.0 for value in values) <= 0.05
    ]
    global_candidate = min(safe_global)[1] if safe_global else STATIC_FLOW_SHIELD_CANDIDATE
    selected = selected_for_fixed_candidate(dev_rows, global_candidate)
    policy_selected["candidate_only_mean_delta_prior"] = selected
    context_rows.extend(add_context_rows("candidate_only_mean_delta_prior", selected, f"train_global_safe_candidate_{global_candidate}"))

    subset_specs = {
        "candidate_param_only_ranker": [name for name in feature_names if name.startswith("feature_candidate_")],
        "no_rich_feature_ablation": [name for name in feature_names if not name.startswith("feature_rich_")],
        "rich_only_ranker": rich_features,
    }
    for policy, subset in subset_specs.items():
        subset_model = fit_subset_model(train_rows, subset, args.ridge_alpha)
        selected, subset_context = decisions_for_subset(dev_rows, policy, subset_model)
        policy_selected[policy] = selected
        for row in subset_context:
            row["feature_count"] = len(subset)
        context_rows.extend(subset_context)

    shuffled_train = shuffled_rich_train_rows(train_rows, rich_features)
    shuffled_model = fit_subset_model(shuffled_train, feature_names, args.ridge_alpha)
    selected, shuffled_context = decisions_for_subset(dev_rows, "rich_shuffled_within_train_split_control", shuffled_model)
    policy_selected["rich_shuffled_within_train_split_control"] = selected
    context_rows.extend(shuffled_context)

    selected_random_feature, _, _, _ = decisions_for_model(dev_rows, model, "random_feature", model["thresholds"])
    policy_selected["true_random_feature_model"] = selected_random_feature
    context_rows.extend(add_context_rows("true_random_feature_model", selected_random_feature, "v4_random_feature_control"))
    selected_shuffled_label, _, _, _ = decisions_for_model(dev_rows, model, "shuffled_label", model["thresholds"])
    policy_selected["true_shuffled_label_model"] = selected_shuffled_label
    context_rows.extend(add_context_rows("true_shuffled_label_model", selected_shuffled_label, "v4_shuffled_label_control"))
    oracle = selected_for_oracle(dev_rows)
    policy_selected["oracle_upper_bound"] = oracle
    context_rows.extend(add_context_rows("oracle_upper_bound", oracle, "oracle_upper_bound"))
    random_selected = random_candidate_selected(dev_rows)
    policy_selected["random_candidate"] = random_selected
    context_rows.extend(add_context_rows("random_candidate", random_selected, "deterministic_random_candidate_control"))

    policy_order = [
        "v4_ranker",
        "v3_g512_ranker_reproduced",
        "static_flow_shield",
        "additive_ltm",
        "slow_decay_high_shield_fixed",
        "safe_slow_decay_train_gate",
        "safe_train_only_map_agent_gate",
        "map_agent_only_gate",
        "candidate_param_only_ranker",
        "candidate_only_mean_delta_prior",
        "no_rich_feature_ablation",
        "rich_only_ranker",
        "rich_shuffled_within_train_split_control",
        "true_random_feature_model",
        "true_shuffled_label_model",
        "random_candidate",
        "oracle_upper_bound",
    ]
    policy_summaries = [summarize_policy(policy, policy_selected[policy]) for policy in policy_order]
    summary_by_policy = {str(row["policy"]): row for row in policy_summaries}
    primary = summary_by_policy["v4_ranker"]

    def risk_value(policy: str, lam: float) -> float:
        key = f"risk_adjusted_utility_lambda_{str(lam).replace('.', 'p')}"
        return finite_number(summary_by_policy[policy].get(key), math.inf)

    def beats_risk(policy: str) -> bool:
        return any(risk_value("v4_ranker", lam) < risk_value(policy, lam) for lam in RISK_LAMBDAS)

    gates = {
        "mean_delta_vs_static_lt_0": finite_number(primary.get("mean_delta_vs_static"), math.inf) < 0.0,
        "mean_delta_vs_additive_lt_0": finite_number(primary.get("mean_delta_vs_additive"), math.inf) < 0.0,
        "harmful_vs_static_rate_le_0p05": finite_number(primary.get("harmful_vs_static_rate"), math.inf) <= 0.05,
        "risk_adjusted_improves_over_v3_g512": beats_risk("v3_g512_ranker_reproduced"),
        "risk_adjusted_beats_safe_slow_decay_train_gate": beats_risk("safe_slow_decay_train_gate"),
        "risk_adjusted_beats_safe_train_only_map_agent_gate": beats_risk("safe_train_only_map_agent_gate"),
        "beats_candidate_param_only_ranker": finite_number(primary.get("mean_delta_vs_static"), math.inf) < finite_number(summary_by_policy["candidate_param_only_ranker"].get("mean_delta_vs_static"), math.inf),
        "beats_no_rich_feature_ablation": finite_number(primary.get("mean_delta_vs_static"), math.inf) < finite_number(summary_by_policy["no_rich_feature_ablation"].get("mean_delta_vs_static"), math.inf),
        "beats_true_random_feature_model": finite_number(primary.get("mean_delta_vs_static"), math.inf) < finite_number(summary_by_policy["true_random_feature_model"].get("mean_delta_vs_static"), math.inf),
        "beats_true_shuffled_label_model": finite_number(primary.get("mean_delta_vs_static"), math.inf) < finite_number(summary_by_policy["true_shuffled_label_model"].get("mean_delta_vs_static"), math.inf),
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
        "no_ids_166_205": observed_id_flags(dev_rows)["ids_166_205_untouched"],
        "runtime_claim_allowed_false": G514_CLOSED_CLAIMS["runtime_claim_allowed"] is False,
    }
    if all(
        gates[name]
        for name in [
            "risk_adjusted_improves_over_v3_g512",
            "risk_adjusted_beats_safe_slow_decay_train_gate",
            "risk_adjusted_beats_safe_train_only_map_agent_gate",
            "harmful_vs_static_rate_le_0p05",
            "forbidden_feature_count_eq_0",
            "runtime_claim_allowed_false",
        ]
    ):
        decision = "rich_trace_v4_ranker_passed_continue_safety_boundary_expansion"
    elif not gates["risk_adjusted_improves_over_v3_g512"]:
        decision = "rich_trace_features_insufficient_continue_probe_or_lattice"
    elif not gates["risk_adjusted_beats_safe_train_only_map_agent_gate"]:
        decision = "candidate_ranker_still_simple_prior_continue_feature_design"
    else:
        decision = "rich_trace_features_insufficient_continue_probe_or_lattice"

    bootstrap = bootstrap_rows(policy_selected, args.bootstrap_samples)
    write_csv_rows(resolve(args.output_csv, root), policy_summaries + bootstrap)
    write_csv_rows(resolve(args.context_decisions_csv, root), context_rows)
    write_csv_rows(resolve(args.bootstrap_csv, root), bootstrap)
    summary = {
        "schema_version": "phase5p5_repair5g514_candidate_ranker_v4_eval_summary_v1",
        "decision": decision,
        "dev_contexts": len({str(row.get("normalized_context_key", "")) for row in dev_rows}),
        "dev_rows": len(dev_rows),
        "train_rows": len(train_rows),
        "feature_count": len(feature_names),
        "rich_feature_count": len(rich_features),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "thresholds": model["thresholds"],
        "primary_policy": primary,
        "policy_summaries": policy_summaries,
        "safe_slow_decay_train_gate_choices": safe_slow_choices,
        "safe_train_only_map_agent_gate_choices": safe_map_choices,
        "candidate_only_mean_delta_prior_choice": global_candidate,
        "gates": gates,
        "risk_lambdas": RISK_LAMBDAS,
        **G514_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    policy_lines = "\n".join(
        f"- `{row['policy']}`: mean_delta_vs_static={finite_number(row.get('mean_delta_vs_static'), math.inf):.6f}, "
        f"harmful_rate={finite_number(row.get('harmful_vs_static_rate'), math.inf):.3f}, "
        f"coverage={finite_number(row.get('coverage'), math.inf):.3f}, "
        f"rau_0.10={finite_number(row.get('risk_adjusted_utility_lambda_0p1'), math.inf):.6f}"
        for row in policy_summaries
    )
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.14 Candidate Ranker V4 Eval\n\n"
        f"- decision: `{decision}`\n"
        f"- dev_contexts: `{summary['dev_contexts']}`\n"
        f"- primary_policy: `{primary}`\n"
        f"- gates: `{gates}`\n"
        f"- risk_lambdas: `{RISK_LAMBDAS}`\n"
        "- bootstrap_confidence_intervals: `reported`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "## Policy Summaries\n\n"
        f"{policy_lines}\n\n"
        "All policies are evaluated as grouped context decisions over the 14 candidate UpdateLTM parameter rows. "
        "The v4 success decision is only available if risk-adjusted utility improves over the reproduced G5.12/G5.13 ranker and beats the safe train-only hard controls while keeping harmful rate at or below 0.05.\n",
    )
    print(json.dumps({"decision": decision, "primary_mean_delta": primary["mean_delta_vs_static"], "primary_harmful": primary["harmful_vs_static_rate"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

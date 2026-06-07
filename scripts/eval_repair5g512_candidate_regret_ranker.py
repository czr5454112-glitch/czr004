"""Evaluate the G5.12 candidate ranker by grouped context decisions."""

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

from repair5g512_common import (  # noqa: E402
    ADDITIVE_CANDIDATE,
    CLOSED_CLAIMS,
    DEFAULT_MARGIN,
    SLOW_DECAY_HIGH_SHIELD_CANDIDATE,
    STATIC_FLOW_SHIELD_CANDIDATE,
    finite_number,
    mean,
    read_csv_rows,
    read_json,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)
from train_repair5g512_candidate_regret_ranker import matrix, predict_model, random_feature_matrix, row_key  # noqa: E402


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g512_candidate_feature_matrix_v3.csv"
DEFAULT_MODEL = "outputs/reports/phase5p5_repair5g512_candidate_ranker_model.json"
DEFAULT_EVAL_CSV = "outputs/tables/phase5p5_repair5g512_candidate_ranker_eval.csv"
DEFAULT_CONTEXT_CSV = "outputs/tables/phase5p5_repair5g512_candidate_ranker_context_decisions.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g512_candidate_ranker_eval.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g512_candidate_ranker_eval_summary.json"
SEED = 20260607


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--model-json", type=Path, default=Path(DEFAULT_MODEL))
    parser.add_argument("--eval-csv", type=Path, default=Path(DEFAULT_EVAL_CSV))
    parser.add_argument("--context-decisions-csv", type=Path, default=Path(DEFAULT_CONTEXT_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def grouped_contexts(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("normalized_context_key", ""))].append(row)
    return dict(grouped)


def by_candidate(group: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("candidate_id", "")): row for row in group}


def select_candidate(group: list[dict[str, Any]], candidate: str) -> dict[str, Any]:
    options = by_candidate(group)
    return options.get(candidate) or options.get(STATIC_FLOW_SHIELD_CANDIDATE) or group[0]


def oracle_candidate(group: list[dict[str, Any]]) -> dict[str, Any]:
    return min(group, key=lambda row: (finite_number(row.get("rank_primary"), math.inf), str(row.get("candidate_id", ""))))


def select_model_policy(group: list[dict[str, Any]], pred_delta: dict[str, float], pred_risk: dict[str, float], thresholds: dict[str, float]) -> tuple[dict[str, Any], str, float, float, float]:
    static = select_candidate(group, STATIC_FLOW_SHIELD_CANDIDATE)
    ranked = sorted(
        group,
        key=lambda row: (pred_delta.get(str(row.get("candidate_id", "")), math.inf), pred_risk.get(str(row.get("candidate_id", "")), 1.0), str(row.get("candidate_id", ""))),
    )
    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else ranked[0]
    best_id = str(best.get("candidate_id", ""))
    second_id = str(second.get("candidate_id", ""))
    best_delta = pred_delta.get(best_id, math.inf)
    best_risk = max(0.0, min(1.0, pred_risk.get(best_id, 1.0)))
    margin = pred_delta.get(second_id, math.inf) - best_delta
    if best_delta <= thresholds["predicted_delta_threshold"] and best_risk <= thresholds["harmful_risk_threshold"] and margin >= thresholds["confidence_margin_threshold"]:
        return best, "selected_predicted_best", best_delta, best_risk, margin
    return static, "fallback_static", best_delta, best_risk, margin


def row_metrics(row: dict[str, Any]) -> dict[str, float]:
    delta_static = finite_number(row.get("mean_delta_vs_static_primary"), math.inf)
    return {
        "mean_delta_vs_static": delta_static,
        "mean_delta_vs_additive": finite_number(row.get("mean_delta_vs_additive_primary"), math.inf),
        "harmful_vs_static": 1.0 if delta_static >= DEFAULT_MARGIN else 0.0,
        "fallback": 1.0 if str(row.get("candidate_id", "")) == STATIC_FLOW_SHIELD_CANDIDATE else 0.0,
    }


def summarize_policy(policy: str, selected: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = [row_metrics(row) for row in selected]
    return {
        "row_type": "policy_summary",
        "policy": policy,
        "contexts": len(selected),
        "mean_delta_vs_static": mean(metric["mean_delta_vs_static"] for metric in metrics),
        "mean_delta_vs_additive": mean(metric["mean_delta_vs_additive"] for metric in metrics),
        "harmful_vs_static_rate": mean(metric["harmful_vs_static"] for metric in metrics),
        "coverage": 1.0 - mean(metric["fallback"] for metric in metrics),
        "fallback_rate": mean(metric["fallback"] for metric in metrics),
    }


def model_predictions(rows: list[dict[str, Any]], model: dict[str, Any], flavor: str) -> tuple[np.ndarray, np.ndarray]:
    if flavor == "primary":
        X = matrix(rows, model["feature_names"])
        return predict_model(model["delta_model"], X), np.clip(predict_model(model["risk_model"], X), 0.0, 1.0)
    if flavor == "random_feature":
        X = random_feature_matrix(rows)
        return predict_model(model["random_delta_model"], X), np.clip(predict_model(model["random_risk_model"], X), 0.0, 1.0)
    if flavor == "shuffled_label":
        X = matrix(rows, model["feature_names"])
        return predict_model(model["shuffled_label_delta_model"], X), np.clip(predict_model(model["shuffled_label_risk_model"], X), 0.0, 1.0)
    raise ValueError(flavor)


def decisions_for_model(rows: list[dict[str, Any]], model: dict[str, Any], flavor: str, thresholds: dict[str, float]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, float], dict[str, float]]:
    pred_delta_array, pred_risk_array = model_predictions(rows, model, flavor)
    pred_delta = {row_key(row): float(value) for row, value in zip(rows, pred_delta_array)}
    pred_risk = {row_key(row): float(value) for row, value in zip(rows, pred_risk_array)}
    decisions = []
    selected = []
    for key, group in sorted(grouped_contexts(rows).items()):
        selected_row, reason, best_delta, best_risk, margin = select_model_policy(
            group,
            {str(row.get("candidate_id", "")): pred_delta[row_key(row)] for row in group},
            {str(row.get("candidate_id", "")): pred_risk[row_key(row)] for row in group},
            thresholds,
        )
        selected.append(selected_row)
        decisions.append(
            {
                "normalized_context_key": key,
                "map": selected_row.get("map", ""),
                "agents": selected_row.get("agents", ""),
                "seed": selected_row.get("seed", ""),
                "selected_candidate_id": selected_row.get("candidate_id", ""),
                "oracle_candidate_for_context": selected_row.get("oracle_candidate_for_context", ""),
                "selection_reason": reason,
                "predicted_best_delta": best_delta,
                "predicted_best_harmful_risk": best_risk,
                "predicted_margin": margin,
                "actual_mean_delta_vs_static": selected_row.get("mean_delta_vs_static_primary", ""),
                "actual_mean_delta_vs_additive": selected_row.get("mean_delta_vs_additive_primary", ""),
                "actual_harmful_vs_static": finite_number(selected_row.get("mean_delta_vs_static_primary"), math.inf) >= DEFAULT_MARGIN,
            }
        )
    return selected, decisions, pred_delta, pred_risk


def baseline_selected(rows: list[dict[str, Any]], policy: str, model: dict[str, Any]) -> list[dict[str, Any]]:
    groups = grouped_contexts(rows)
    rng = random.Random(SEED)
    out = []
    priors = model["priors"]
    for key, group in sorted(groups.items()):
        if policy == "static_flow_shield":
            out.append(select_candidate(group, STATIC_FLOW_SHIELD_CANDIDATE))
        elif policy == "additive_ltm":
            out.append(select_candidate(group, ADDITIVE_CANDIDATE))
        elif policy == "slow_decay_high_shield_fixed":
            out.append(select_candidate(group, SLOW_DECAY_HIGH_SHIELD_CANDIDATE))
        elif policy == "best_single_train_candidate":
            out.append(select_candidate(group, priors["best_single_train_candidate"]))
        elif policy == "train_only_majority_candidate":
            out.append(select_candidate(group, priors["train_only_majority_candidate"]))
        elif policy == "train_only_map_agent_prior":
            first = group[0]
            candidate = priors["train_only_map_agent_prior"].get(f"{first.get('map', '')}|a{first.get('agents', '')}", priors["best_single_train_candidate"])
            out.append(select_candidate(group, candidate))
        elif policy == "random_candidate":
            out.append(rng.choice(sorted(group, key=lambda row: str(row.get("candidate_id", "")))))
        elif policy == "oracle_upper_bound":
            out.append(oracle_candidate(group))
        else:
            raise ValueError(policy)
    return out


def coverage_risk_rows(rows: list[dict[str, Any]], model: dict[str, Any], pred_delta: dict[str, float], pred_risk: dict[str, float]) -> list[dict[str, Any]]:
    out = []
    for risk_threshold in [0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 1.00]:
        thresholds = {
            "predicted_delta_threshold": -DEFAULT_MARGIN,
            "harmful_risk_threshold": risk_threshold,
            "confidence_margin_threshold": 0.0,
        }
        selected = []
        for group in grouped_contexts(rows).values():
            selected_row, _, _, _, _ = select_model_policy(
                group,
                {str(row.get("candidate_id", "")): pred_delta[row_key(row)] for row in group},
                {str(row.get("candidate_id", "")): pred_risk[row_key(row)] for row in group},
                thresholds,
            )
            selected.append(selected_row)
        metrics = summarize_policy("g512_ranker_curve", selected)
        metrics.update({"row_type": "coverage_risk_curve", "risk_threshold": risk_threshold})
        out.append(metrics)
    return out


def calibration_rows(rows: list[dict[str, Any]], pred_risk: dict[str, float]) -> list[dict[str, Any]]:
    bins = [(0.0, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.50), (0.50, 1.01)]
    out = []
    for low, high in bins:
        bucket = [
            row
            for row in rows
            if low <= max(0.0, min(1.0, pred_risk[row_key(row)])) < high
        ]
        actual = [1.0 if finite_number(row.get("mean_delta_vs_static_primary"), math.inf) >= DEFAULT_MARGIN else 0.0 for row in bucket]
        out.append(
            {
                "row_type": "risk_calibration_bucket",
                "policy": "g512_ranker",
                "risk_bucket_low": low,
                "risk_bucket_high": high,
                "rows": len(bucket),
                "mean_predicted_harmful_risk": mean(max(0.0, min(1.0, pred_risk[row_key(row)])) for row in bucket),
                "actual_harmful_rate": mean(actual),
            }
        )
    return out


def beats(lhs: dict[str, Any], rhs: dict[str, Any]) -> bool:
    return finite_number(lhs.get("mean_delta_vs_static"), math.inf) < finite_number(rhs.get("mean_delta_vs_static"), math.inf)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_csv, root))
    model = read_json(resolve(args.model_json, root))
    dev_rows = [row for row in rows if row.get("split") == "dev"]
    thresholds = model["thresholds"]
    selected_primary, context_decisions, pred_delta, pred_risk = decisions_for_model(dev_rows, model, "primary", thresholds)
    selected_random_feature, _, _, _ = decisions_for_model(dev_rows, model, "random_feature", thresholds)
    selected_shuffled_label, _, _, _ = decisions_for_model(dev_rows, model, "shuffled_label", thresholds)

    policy_summaries = [summarize_policy("g512_ranker", selected_primary)]
    for policy in [
        "static_flow_shield",
        "additive_ltm",
        "slow_decay_high_shield_fixed",
        "best_single_train_candidate",
        "train_only_majority_candidate",
        "train_only_map_agent_prior",
        "random_candidate",
        "oracle_upper_bound",
    ]:
        policy_summaries.append(summarize_policy(policy, baseline_selected(dev_rows, policy, model)))
    policy_summaries.append(summarize_policy("true_random_feature_model", selected_random_feature))
    policy_summaries.append(summarize_policy("true_shuffled_label_model", selected_shuffled_label))
    summary_by_policy = {str(row["policy"]): row for row in policy_summaries}
    curve_rows = coverage_risk_rows(dev_rows, model, pred_delta, pred_risk)
    calibration = calibration_rows(dev_rows, pred_risk)
    write_csv_rows(resolve(args.eval_csv, root), policy_summaries + curve_rows + calibration)
    write_csv_rows(resolve(args.context_decisions_csv, root), context_decisions)

    primary = summary_by_policy["g512_ranker"]
    gates = {
        "mean_delta_vs_static_lt_0": finite_number(primary.get("mean_delta_vs_static"), math.inf) < 0.0,
        "mean_delta_vs_additive_lt_0": finite_number(primary.get("mean_delta_vs_additive"), math.inf) < 0.0,
        "harmful_vs_static_rate_le_0p10": finite_number(primary.get("harmful_vs_static_rate"), math.inf) <= 0.10,
        "harmful_vs_static_rate_le_0p05": finite_number(primary.get("harmful_vs_static_rate"), math.inf) <= 0.05,
        "beats_true_random_feature_model": beats(primary, summary_by_policy["true_random_feature_model"]),
        "beats_true_shuffled_label_model": beats(primary, summary_by_policy["true_shuffled_label_model"]),
        "beats_train_only_map_agent_prior": beats(primary, summary_by_policy["train_only_map_agent_prior"]),
        "beats_slow_decay_high_shield_fixed": beats(primary, summary_by_policy["slow_decay_high_shield_fixed"]),
        "beats_best_single_train_candidate": beats(primary, summary_by_policy["best_single_train_candidate"]),
        "no_ids_166_205": all(not (166 <= int(finite_number(row.get("seed"), 0.0)) <= 205) for row in dev_rows),
        "runtime_claim_allowed_false": False is CLOSED_CLAIMS["runtime_claim_allowed"],
    }
    pass_gates = (
        gates["mean_delta_vs_static_lt_0"]
        and gates["mean_delta_vs_additive_lt_0"]
        and gates["harmful_vs_static_rate_le_0p10"]
        and gates["beats_true_random_feature_model"]
        and gates["beats_true_shuffled_label_model"]
        and gates["beats_train_only_map_agent_prior"]
    )
    decision = "candidate_ranker_passed_continue_static_abstention_safety_package" if pass_gates else "candidate_ranker_failed_continue_features_or_lattice"
    summary = {
        "schema_version": "phase5p5_repair5g512_candidate_ranker_eval_summary_v1",
        "decision": decision,
        "dev_contexts": len({str(row.get("normalized_context_key", "")) for row in dev_rows}),
        "dev_rows": len(dev_rows),
        "thresholds": thresholds,
        "policy_summaries": policy_summaries,
        "primary_policy": primary,
        "coverage_risk_curve_reported": True,
        "calibration_reported": True,
        "failures_reported": {
            "beats_best_single_train_candidate": gates["beats_best_single_train_candidate"],
            "beats_train_only_map_agent_prior": gates["beats_train_only_map_agent_prior"],
            "beats_slow_decay_high_shield_fixed": gates["beats_slow_decay_high_shield_fixed"],
        },
        "gates": gates,
        **CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    policy_lines = "\n".join(
        f"- `{row['policy']}`: mean_delta_vs_static={finite_number(row.get('mean_delta_vs_static'), math.inf):.6f}, "
        f"harmful_rate={finite_number(row.get('harmful_vs_static_rate'), math.inf):.3f}, coverage={finite_number(row.get('coverage'), math.inf):.3f}"
        for row in policy_summaries
    )
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.12 Candidate Ranker Eval\n\n"
        f"- decision: `{decision}`\n"
        f"- dev_contexts: `{summary['dev_contexts']}`\n"
        f"- thresholds: `{thresholds}`\n"
        f"- primary_policy: `{primary}`\n"
        f"- gates: `{gates}`\n"
        "- coverage_risk_curve_reported: `true`\n"
        "- calibration_reported: `true`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "## Policy Summaries\n\n"
        f"{policy_lines}\n\n"
        "Evaluation is grouped by context: all 14 candidates are scored, the policy either selects one candidate or falls back to static flow-shield, and the selected candidate is compared against static, additive, fixed-candidate, prior, random, shuffled-label, random-feature, and oracle baselines. "
        "This remains an offline diagnostic, not a learned runtime-policy validation.\n",
    )
    print(json.dumps({"decision": decision, "dev_contexts": summary["dev_contexts"], "mean_delta_vs_static": primary["mean_delta_vs_static"]}))
    return 0 if decision != "candidate_ranker_failed_continue_features_or_lattice" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

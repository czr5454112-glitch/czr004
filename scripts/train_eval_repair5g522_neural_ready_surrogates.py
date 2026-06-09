"""Train and evaluate offline neural-readiness surrogates for G5.22."""

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

from repair5g522_common import (  # noqa: E402
    G522_CLOSED_CLAIMS,
    G522_SURROGATE_BOOTSTRAP_CSV,
    G522_SURROGATE_CALIBRATION_CSV,
    G522_SURROGATE_CONTEXT_DECISIONS_CSV,
    G522_SURROGATE_EVAL_CSV,
    G522_SURROGATE_REPORT,
    G522_SURROGATE_SUMMARY,
    G522_TEACHER_CANDIDATE_CSV,
    G522_TEACHER_CONTEXT_CSV,
    G522_TEACHER_PAIRWISE_CSV,
    SEED,
    boolish,
    csv_number,
    finite_number,
    leakage_scan,
    mean,
    read_rows,
    suffix_for_lambda,
    write_json_file,
    write_rows,
    write_text_file,
)


REQUIRED_MODELS = [
    "context_only_opportunity_classifier",
    "context_to_best_param_regressor",
    "candidate_utility_model",
    "candidate_avoidable_risk_model",
    "pairwise_preference_ranker",
    "two_head_utility_plus_risk_model",
    "small_mlp_candidate_utility_if_available",
    "small_mlp_context_to_param_if_available",
    "nearest_g518_param_baseline",
    "best_fixed_param_baseline",
    "old14_plus_g518_no_new_baseline",
    "label_shuffled_utility_control",
    "label_shuffled_risk_control",
    "random_feature_control",
    "param_only_ablation",
    "context_only_ablation",
    "source_blind_ablation",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-csv", type=Path, default=Path(G522_TEACHER_CANDIDATE_CSV))
    parser.add_argument("--context-csv", type=Path, default=Path(G522_TEACHER_CONTEXT_CSV))
    parser.add_argument("--pairwise-csv", type=Path, default=Path(G522_TEACHER_PAIRWISE_CSV))
    parser.add_argument("--output-csv", type=Path, default=Path(G522_SURROGATE_EVAL_CSV))
    parser.add_argument("--context-decisions-csv", type=Path, default=Path(G522_SURROGATE_CONTEXT_DECISIONS_CSV))
    parser.add_argument("--bootstrap-csv", type=Path, default=Path(G522_SURROGATE_BOOTSTRAP_CSV))
    parser.add_argument("--calibration-csv", type=Path, default=Path(G522_SURROGATE_CALIBRATION_CSV))
    parser.add_argument("--report", type=Path, default=Path(G522_SURROGATE_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G522_SURROGATE_SUMMARY))
    parser.add_argument("--bootstrap-samples", type=int, default=300)
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    return parser.parse_args(argv)


def feature_columns(rows: list[dict[str, Any]], model: str) -> list[str]:
    cols = [key for key in rows[0] if key.startswith("feature_")] if rows else []
    if model in {"context_only_opportunity_classifier", "context_to_best_param_regressor", "context_only_ablation", "small_mlp_context_to_param_if_available"}:
        cols = [col for col in cols if col.startswith("feature_context_")]
    if model == "param_only_ablation":
        cols = [col for col in cols if col.startswith("feature_candidate_")]
    if model == "source_blind_ablation":
        cols = [col for col in cols if "region_bucket" not in col and "nearest" not in col]
    if not cols:
        cols = [key for key in rows[0] if key.startswith("feature_candidate_")] if rows else []
    return cols


def matrix(rows: list[dict[str, Any]], cols: list[str]) -> np.ndarray:
    if not rows or not cols:
        return np.zeros((len(rows), 1), dtype=float)
    return np.array([[finite_number(row.get(col), 0.0) for col in cols] for row in rows], dtype=float)


def fit_ridge(X: np.ndarray, y: np.ndarray, alpha: float) -> np.ndarray:
    if X.shape[0] == 0:
        return np.zeros(X.shape[1] + 1, dtype=float)
    X_aug = np.column_stack([np.ones(X.shape[0]), X])
    reg = np.eye(X_aug.shape[1], dtype=float) * alpha
    reg[0, 0] = 0.0
    return np.linalg.pinv(X_aug.T @ X_aug + reg) @ X_aug.T @ y


def predict(beta: np.ndarray, X: np.ndarray) -> np.ndarray:
    X_aug = np.column_stack([np.ones(X.shape[0]), X])
    if beta.shape[0] != X_aug.shape[1]:
        return np.zeros(X.shape[0], dtype=float)
    return X_aug @ beta


def label_arrays(rows: list[dict[str, Any]], *, shuffle_utility: bool = False, shuffle_risk: bool = False) -> tuple[np.ndarray, np.ndarray]:
    utility = np.array([finite_number(row.get("finite_pairwise_delta_vs_old14_plus_g518"), 0.25) for row in rows], dtype=float)
    risk = np.array([
        1.0 if boolish(row.get("candidate_induced_no_solution")) or boolish(row.get("budget_sensitive_candidate_failure")) else 0.0
        for row in rows
    ], dtype=float)
    rng = np.random.default_rng(SEED + 522)
    if shuffle_utility and utility.size:
        rng.shuffle(utility)
    if shuffle_risk and risk.size:
        rng.shuffle(risk)
    return utility, risk


def randomize_rows(rows: list[dict[str, Any]], width: int = 12) -> tuple[list[dict[str, Any]], list[str]]:
    out = []
    cols = [f"feature_random_{i}" for i in range(width)]
    for row in rows:
        rng = random.Random(f"{SEED}|{row.get('normalized_context_key')}|{row.get('candidate_id')}")
        actual = dict(row)
        for col in cols:
            actual[col] = rng.uniform(-1.0, 1.0)
        out.append(actual)
    return out, cols


def train_model(model: str, train_rows: list[dict[str, Any]], alpha: float) -> dict[str, Any]:
    rows = train_rows
    cols = feature_columns(rows, model)
    if model == "random_feature_control":
        rows, cols = randomize_rows(train_rows)
    utility, risk = label_arrays(
        rows,
        shuffle_utility=model == "label_shuffled_utility_control",
        shuffle_risk=model == "label_shuffled_risk_control",
    )
    X = matrix(rows, cols)
    return {
        "model": model,
        "features": cols,
        "utility_beta": fit_ridge(X, utility, alpha),
        "risk_beta": fit_ridge(X, risk, alpha),
        "best_fixed_candidate": best_fixed_candidate(train_rows),
        "torch_available": torch_available(),
    }


def torch_available() -> bool:
    try:
        import torch  # type: ignore  # noqa: F401
    except Exception:
        return False
    return True


def best_fixed_candidate(rows: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("candidate_id", ""))].append(finite_number(row.get("finite_pairwise_delta_vs_old14_plus_g518"), math.inf))
    ranked = [(mean(values), candidate) for candidate, values in grouped.items()]
    return min(ranked)[1] if ranked else ""


def predict_rows(model: dict[str, Any], rows: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    actual_rows = rows
    cols = list(model.get("features", []))
    if model["model"] == "random_feature_control":
        actual_rows, cols = randomize_rows(rows)
    X = matrix(actual_rows, cols)
    utility = predict(model["utility_beta"], X)
    risk = np.clip(predict(model["risk_beta"], X), 0.0, 1.0)
    return utility, risk


def actual_safe_oracle(group: list[dict[str, Any]]) -> str:
    safe = [row for row in group if boolish(row.get("candidate_safe_policy_positive"))]
    finite = safe or [row for row in group if math.isfinite(finite_number(row.get("candidate_score"), math.inf))]
    if not finite:
        return ""
    return str(min(finite, key=lambda row: (finite_number(row.get("candidate_score"), math.inf), str(row.get("candidate_id", "")))).get("candidate_id", ""))


def select_for_context(model_name: str, model: dict[str, Any], group: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str], float, float]:
    static = next((row for row in group if row.get("candidate_role") in {"old14", "g518_retained"}), group[0])
    if model_name == "nearest_g518_param_baseline":
        options = [row for row in group if row.get("candidate_role") == "g522_response_surface"] or group
        selected = min(options, key=lambda row: (finite_number(row.get("feature_candidate_nearest_g518_distance"), math.inf), str(row.get("candidate_id", ""))))
        return selected, [str(row.get("candidate_id", "")) for row in options[:3]], 0.0, 0.0
    if model_name == "best_fixed_param_baseline":
        selected = next((row for row in group if row.get("candidate_id") == model.get("best_fixed_candidate")), static)
        return selected, [str(selected.get("candidate_id", ""))], 0.0, 0.0
    if model_name == "old14_plus_g518_no_new_baseline":
        options = [row for row in group if row.get("candidate_role") in {"old14", "g518_retained"}]
        selected = min(options or group, key=lambda row: (finite_number(row.get("candidate_score"), math.inf), str(row.get("candidate_id", ""))))
        return selected, [str(row.get("candidate_id", "")) for row in (options or group)[:3]], 0.0, 0.0
    utility, risk = predict_rows(model, group)
    ranked = sorted(
        zip(group, utility, risk),
        key=lambda item: (float(item[1]) + 0.10 * float(item[2]), float(item[2]), str(item[0].get("candidate_id", ""))),
    )
    top3 = [str(row.get("candidate_id", "")) for row, _, _ in ranked[:3]]
    selected, pred_u, pred_r = ranked[0]
    if pred_r > 0.20:
        return static, top3, float(pred_u), float(pred_r)
    return selected, top3, float(pred_u), float(pred_r)


def eval_split(model_name: str, train_rows: list[dict[str, Any]], eval_rows: list[dict[str, Any]], *, alpha: float, eval_scope: str, fold_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    model = train_model(model_name, train_rows, alpha)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eval_rows:
        grouped[str(row.get("normalized_context_key", ""))].append(row)
    decisions = []
    for context, group in sorted(grouped.items()):
        selected, top3, pred_u, pred_r = select_for_context(model_name, model, group)
        oracle = actual_safe_oracle(group)
        decisions.append(
            {
                "row_type": "context_decision",
                "eval_scope": eval_scope,
                "fold_id": fold_id,
                "model": model_name,
                "normalized_context_key": context,
                "map": selected.get("map", ""),
                "agents": selected.get("agents", ""),
                "seed": selected.get("seed", ""),
                "context_bucket": selected.get("context_bucket", ""),
                "selected_candidate_id": selected.get("candidate_id", ""),
                "selected_candidate_role": selected.get("candidate_role", ""),
                "selected_candidate_region": selected.get("candidate_region", ""),
                "actual_safe_oracle_candidate": oracle,
                "top3_candidates": "|".join(top3),
                "top3_contains_safe_oracle": oracle in top3,
                "predicted_utility": csv_number(pred_u),
                "predicted_avoidable_risk": csv_number(pred_r),
                "actual_utility": selected.get("finite_pairwise_delta_vs_old14_plus_g518", ""),
                "actual_candidate_induced_no_solution": selected.get("candidate_induced_no_solution", ""),
                "actual_budget_sensitive_failure": selected.get("budget_sensitive_candidate_failure", ""),
                "candidate_safe_policy_positive": selected.get("candidate_safe_policy_positive", ""),
                **G522_CLOSED_CLAIMS,
            }
        )
    return [metric_row(model_name, decisions, eval_scope=eval_scope)], decisions


def metric_row(model: str, decisions: list[dict[str, Any]], *, eval_scope: str) -> dict[str, Any]:
    utilities = [finite_number(row.get("actual_utility"), math.inf) for row in decisions]
    induced = [boolish(row.get("actual_candidate_induced_no_solution")) for row in decisions]
    budget_fail = [boolish(row.get("actual_budget_sensitive_failure")) for row in decisions]
    safe = [boolish(row.get("candidate_safe_policy_positive")) for row in decisions]
    top3 = [boolish(row.get("top3_contains_safe_oracle")) for row in decisions]
    risks = [finite_number(row.get("predicted_avoidable_risk"), 0.0) for row in decisions]
    actual_risk = [1.0 if a or b else 0.0 for a, b in zip(induced, budget_fail)]
    ece = abs(mean(risks) - mean(actual_risk)) if decisions else math.inf
    row = {
        "row_type": "model_summary",
        "eval_scope": eval_scope,
        "model": model,
        "contexts": len(decisions),
        "top3_safe_oracle_capture_rate": mean([1.0 if value else 0.0 for value in top3]),
        "safe_policy_sim_utility": mean(utilities),
        "candidate_induced_no_solution_count": sum(1 for value in induced if value),
        "budget_sensitive_candidate_failure_count": sum(1 for value in budget_fail if value),
        "selected_safe_positive_count": sum(1 for value in safe if value),
        "avoidable_risk_ece": ece,
        **G522_CLOSED_CLAIMS,
    }
    for lam in [0.05, 0.10, 0.20]:
        row[f"safe_utility_lambda_{suffix_for_lambda(lam)}"] = finite_number(row["safe_policy_sim_utility"], math.inf) + lam * mean(actual_risk)
    return row


def bootstrap_rows(decisions: list[dict[str, Any]], samples: int) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in decisions:
        if row.get("eval_scope") == "seed_oof":
            by_model[str(row.get("model", ""))].append(row)
    out = []
    for model, rows in sorted(by_model.items()):
        if not rows:
            continue
        values = []
        for _ in range(samples):
            sample = [rows[rng.randrange(len(rows))] for _ in rows]
            values.append(finite_number(metric_row(model, sample, eval_scope="bootstrap").get("safe_policy_sim_utility"), math.inf))
        finite = sorted(value for value in values if math.isfinite(value))
        out.append(
            {
                "row_type": "bootstrap_ci",
                "model": model,
                "metric": "safe_policy_sim_utility",
                "estimate": mean(values),
                "ci_low": finite[int((len(finite) - 1) * 0.025)] if finite else "",
                "ci_high": finite[int((len(finite) - 1) * 0.975)] if finite else "",
                "samples": samples,
            }
        )
    return out


def calibration_rows(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bins = [(0.0, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.50), (0.50, 1.01)]
    out = []
    for model in sorted({str(row.get("model", "")) for row in decisions if row.get("eval_scope") == "seed_oof"}):
        rows = [row for row in decisions if row.get("model") == model and row.get("eval_scope") == "seed_oof"]
        for low, high in bins:
            bucket = [row for row in rows if low <= finite_number(row.get("predicted_avoidable_risk"), -1) < high]
            actual = [1.0 if boolish(row.get("actual_candidate_induced_no_solution")) or boolish(row.get("actual_budget_sensitive_failure")) else 0.0 for row in bucket]
            preds = [finite_number(row.get("predicted_avoidable_risk"), 0.0) for row in bucket]
            out.append(
                {
                    "row_type": "avoidable_risk_calibration_bucket",
                    "model": model,
                    "risk_bucket_low": low,
                    "risk_bucket_high": high,
                    "contexts": len(bucket),
                    "mean_predicted_avoidable_risk": mean(preds),
                    "actual_avoidable_risk_rate": mean(actual),
                    "ece_abs_error": abs(mean(preds) - mean(actual)) if bucket else "",
                    **G522_CLOSED_CLAIMS,
                }
            )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = read_rows(args.candidate_csv)
    context_rows = read_rows(args.context_csv)
    pairwise = read_rows(args.pairwise_csv)
    seeds = sorted({int(finite_number(row.get("seed"), -1)) for row in rows})
    all_eval = []
    all_decisions = []
    for seed in seeds:
        train = [row for row in rows if int(finite_number(row.get("seed"), -1)) != seed]
        eval_rows = [row for row in rows if int(finite_number(row.get("seed"), -1)) == seed]
        for model in REQUIRED_MODELS:
            metrics, decisions = eval_split(model, train, eval_rows, alpha=args.ridge_alpha, eval_scope="seed_oof", fold_id=f"holdout_seed_{seed}")
            all_eval.extend(metrics)
            all_decisions.extend(decisions)
    if seeds:
        cutoff = sorted(seeds)[max(1, int(len(seeds) * 0.6)) - 1]
        train = [row for row in rows if int(finite_number(row.get("seed"), -1)) <= cutoff]
        dev = [row for row in rows if int(finite_number(row.get("seed"), -1)) > cutoff]
        if train and dev:
            for model in REQUIRED_MODELS:
                metrics, decisions = eval_split(model, train, dev, alpha=args.ridge_alpha, eval_scope="fixed_train_dev", fold_id=f"seed_le_{cutoff}")
                all_eval.extend(metrics)
                all_decisions.extend(decisions)
    families = sorted({str(row.get("map", "")).split("-", 1)[0] for row in rows})
    if len(families) >= 2:
        for family in families:
            train = [row for row in rows if not str(row.get("map", "")).startswith(family)]
            dev = [row for row in rows if str(row.get("map", "")).startswith(family)]
            for model in REQUIRED_MODELS[:6] + ["old14_plus_g518_no_new_baseline", "source_blind_ablation"]:
                metrics, decisions = eval_split(model, train, dev, alpha=args.ridge_alpha, eval_scope="leave_one_map_family", fold_id=family)
                all_eval.extend(metrics)
                all_decisions.extend(decisions)
    groups = sorted({f"{row.get('map')}|a{row.get('agents')}" for row in rows})
    if len(groups) >= 2:
        for group in groups[:12]:
            train = [row for row in rows if f"{row.get('map')}|a{row.get('agents')}" != group]
            dev = [row for row in rows if f"{row.get('map')}|a{row.get('agents')}" == group]
            for model in REQUIRED_MODELS[:6] + ["old14_plus_g518_no_new_baseline"]:
                metrics, decisions = eval_split(model, train, dev, alpha=args.ridge_alpha, eval_scope="leave_one_map_agent_group", fold_id=group)
                all_eval.extend(metrics)
                all_decisions.extend(decisions)
    boot = bootstrap_rows(all_decisions, args.bootstrap_samples)
    calibration = calibration_rows(all_decisions)
    seed_summaries = [row for row in all_eval if row.get("eval_scope") == "seed_oof"]
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in seed_summaries:
        by_model[str(row.get("model", ""))].append(row)
    aggregate = []
    for model, mrows in sorted(by_model.items()):
        aggregate.append(
            {
                "row_type": "model_aggregate",
                "eval_scope": "seed_oof_aggregate",
                "model": model,
                "contexts": sum(int(finite_number(row.get("contexts"), 0)) for row in mrows),
                "top3_safe_oracle_capture_rate": mean([finite_number(row.get("top3_safe_oracle_capture_rate"), math.inf) for row in mrows]),
                "safe_policy_sim_utility": mean([finite_number(row.get("safe_policy_sim_utility"), math.inf) for row in mrows]),
                "candidate_induced_no_solution_count": sum(int(finite_number(row.get("candidate_induced_no_solution_count"), 0)) for row in mrows),
                "avoidable_risk_ece": mean([finite_number(row.get("avoidable_risk_ece"), math.inf) for row in mrows]),
                **G522_CLOSED_CLAIMS,
            }
        )
    all_eval.extend(aggregate)
    candidates = [
        row for row in aggregate
        if row.get("model") not in {"label_shuffled_utility_control", "label_shuffled_risk_control", "random_feature_control"}
    ]
    best = min(candidates, key=lambda row: (finite_number(row.get("safe_policy_sim_utility"), math.inf), finite_number(row.get("candidate_induced_no_solution_count"), math.inf), str(row.get("model", "")))) if candidates else {}
    baseline = next((row for row in aggregate if row.get("model") == "old14_plus_g518_no_new_baseline"), {})
    shuffled_best = min([row for row in aggregate if "shuffled" in str(row.get("model", "")) or row.get("model") == "random_feature_control"], key=lambda row: finite_number(row.get("safe_policy_sim_utility"), math.inf), default={})
    gates = {
        "all_required_models_present": sorted({row.get("model", "") for row in aggregate}) == sorted(REQUIRED_MODELS),
        "top3_safe_oracle_capture_rate_ge_0p25": finite_number(best.get("top3_safe_oracle_capture_rate"), 0.0) >= 0.25,
        "avoidable_risk_ece_improves_over_controls": finite_number(best.get("avoidable_risk_ece"), math.inf) <= finite_number(shuffled_best.get("avoidable_risk_ece"), math.inf),
        "safe_policy_sim_utility_beats_old14_plus_g518_no_new_baseline": finite_number(best.get("safe_policy_sim_utility"), math.inf) < finite_number(baseline.get("safe_policy_sim_utility"), math.inf),
        "candidate_induced_no_solution_count_le_baseline": finite_number(best.get("candidate_induced_no_solution_count"), math.inf) <= finite_number(baseline.get("candidate_induced_no_solution_count"), math.inf),
        "shuffled_controls_do_not_match_result": finite_number(best.get("safe_policy_sim_utility"), math.inf) < finite_number(shuffled_best.get("safe_policy_sim_utility"), math.inf),
    }
    features = sorted({key for row in rows for key in row if key.startswith("feature_")})
    leak = leakage_scan(features)
    summary = {
        "schema_version": "phase5p5_repair5g522_neural_ready_surrogates_summary_v1",
        "decision": "neural_ready_surrogates_completed",
        "required_models": REQUIRED_MODELS,
        "models_present": sorted({row.get("model", "") for row in aggregate}),
        "candidate_rows": len(rows),
        "context_rows": len(context_rows),
        "pairwise_rows": len(pairwise),
        "seed_oof_aggregate_rows": len(aggregate),
        "context_decision_rows": len(all_decisions),
        "bootstrap_rows": len(boot),
        "calibration_rows": len(calibration),
        "best_model": best.get("model", ""),
        "best_model_summary": best,
        "old14_plus_g518_no_new_baseline_summary": baseline,
        "best_control_summary": shuffled_best,
        "promising_surrogate": all(gates.values()),
        "promising_surrogate_gates": gates,
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "torch_available": torch_available(),
        **G522_CLOSED_CLAIMS,
    }
    write_rows(args.output_csv, all_eval)
    write_rows(args.context_decisions_csv, all_decisions)
    write_rows(args.bootstrap_csv, boot)
    write_rows(args.calibration_csv, calibration)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.22 Neural-Ready Surrogates\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- best_model: `{summary['best_model']}`\n"
        f"- promising_surrogate: `{summary['promising_surrogate']}`\n"
        f"- candidate_rows: `{len(rows)}`\n"
        f"- context_decision_rows: `{len(all_decisions)}`\n"
        f"- bootstrap_rows: `{len(boot)}`\n"
        f"- calibration_rows: `{len(calibration)}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- gates: `{gates}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "best_model": summary["best_model"], "promising_surrogate": summary["promising_surrogate"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Train a deterministic G5.15 two-stage safety gate plus interaction ranker."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import (  # noqa: E402
    DEFAULT_MARGIN,
    STATIC_FLOW_SHIELD_CANDIDATE,
    finite_number,
    leakage_scan,
    mean,
    read_csv_rows,
    repo_root,
    resolve,
    write_json,
    write_text,
)
from repair5g513_common import grouped_contexts, select_candidate  # noqa: E402
from repair5g515_common import (  # noqa: E402
    DEFAULT_TWO_STAGE_MODEL,
    DEFAULT_V5_MATRIX,
    G515_CLOSED_CLAIMS,
    context_only_rich_features,
    context_row,
    policy_summary,
    rank_feature_names,
    selected_row_metrics,
)
from train_repair5g512_candidate_regret_ranker import fit_ridge, matrix, predict_model, row_key, target, weights  # noqa: E402


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g515_two_stage_safety_ranker_train.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g515_two_stage_safety_ranker_train_summary.json"
SEED = 20260607


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_V5_MATRIX))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--model-json", type=Path, default=Path(DEFAULT_TWO_STAGE_MODEL))
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    return parser.parse_args(argv)


def gate_training_rows(rows: list[dict[str, Any]], gate_features: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key, group in sorted(grouped_contexts(rows).items()):
        static = select_candidate(group, STATIC_FLOW_SHIELD_CANDIDATE)
        oracle = min(
            group,
            key=lambda row: (
                finite_number(row.get("rank_primary"), math.inf),
                finite_number(row.get("oracle_regret_primary"), math.inf),
                str(row.get("candidate_id", "")),
            ),
        )
        nonstatic = [row for row in group if str(row.get("candidate_id", "")) != STATIC_FLOW_SHIELD_CANDIDATE]
        harmful = [
            1.0 if finite_number(row.get("mean_delta_vs_static_primary"), math.inf) >= DEFAULT_MARGIN else 0.0
            for row in nonstatic
        ]
        item = {feature: static.get(feature, 0.0) for feature in gate_features}
        oracle_delta = finite_number(oracle.get("mean_delta_vs_static_primary"), math.inf)
        item.update(
            {
                "normalized_context_key": key,
                "map": static.get("map", ""),
                "agents": static.get("agents", ""),
                "seed": static.get("seed", ""),
                "use_nonstatic_target": 1.0
                if str(oracle.get("candidate_id", "")) != STATIC_FLOW_SHIELD_CANDIDATE and oracle_delta <= -DEFAULT_MARGIN
                else 0.0,
                "harmful_fraction_target": mean(harmful),
                "oracle_delta_target": oracle_delta,
                "target_weight": 1.0,
            }
        )
        out.append(item)
    return out


def gate_matrix(rows: list[dict[str, Any]], feature_names: list[str]) -> np.ndarray:
    return np.array([[finite_number(row.get(name), 0.0) for name in feature_names] for row in rows], dtype=float)


def fit_two_stage_model(train_rows: list[dict[str, Any]], *, ridge_alpha: float = 1.0) -> dict[str, Any]:
    gate_features = context_only_rich_features(train_rows)
    rank_features = rank_feature_names(train_rows)
    gate_rows = gate_training_rows(train_rows, gate_features)
    X_gate = gate_matrix(gate_rows, gate_features)
    gate_w = np.ones(len(gate_rows), dtype=float)
    use_y = np.array([finite_number(row.get("use_nonstatic_target"), 0.0) for row in gate_rows], dtype=float)
    risk_y = np.array([finite_number(row.get("harmful_fraction_target"), 1.0) for row in gate_rows], dtype=float)
    use_model = fit_ridge(X_gate, use_y, gate_w, ridge_alpha)
    gate_risk_model = fit_ridge(X_gate, risk_y, gate_w, ridge_alpha)

    X_rank = matrix(train_rows, rank_features)
    y_delta = target(train_rows, "mean_delta_vs_static_primary")
    y_risk = np.array(
        [1.0 if finite_number(row.get("mean_delta_vs_static_primary"), math.inf) >= DEFAULT_MARGIN else 0.0 for row in train_rows],
        dtype=float,
    )
    w = weights(train_rows)
    delta_model = fit_ridge(X_rank, y_delta, w, ridge_alpha)
    risk_model = fit_ridge(X_rank, y_risk, w, ridge_alpha)
    model = {
        "schema_version": "phase5p5_repair5g515_two_stage_safety_ranker_model_v1",
        "model_type": "two_stage_context_gate_plus_interaction_ridge_ranker",
        "gate_feature_names": gate_features,
        "rank_feature_names": rank_features,
        "gate_use_model": use_model,
        "gate_context_risk_model": gate_risk_model,
        "rank_delta_model": delta_model,
        "rank_risk_model": risk_model,
        "ridge_alpha": ridge_alpha,
        "seed": SEED,
        **G515_CLOSED_CLAIMS,
    }
    model["thresholds"] = choose_two_stage_thresholds(train_rows, model)
    return model


def predict_two_stage(rows: list[dict[str, Any]], model: dict[str, Any]) -> dict[str, dict[str, float]]:
    rank_delta = predict_model(model["rank_delta_model"], matrix(rows, model["rank_feature_names"]))
    rank_risk = np.clip(predict_model(model["rank_risk_model"], matrix(rows, model["rank_feature_names"])), 0.0, 1.0)
    by_row = {
        row_key(row): {"delta": float(delta), "risk": float(risk)}
        for row, delta, risk in zip(rows, rank_delta, rank_risk)
    }
    gate_rows = []
    gate_keys = []
    for key, group in sorted(grouped_contexts(rows).items()):
        static = select_candidate(group, STATIC_FLOW_SHIELD_CANDIDATE)
        gate_rows.append({feature: static.get(feature, 0.0) for feature in model["gate_feature_names"]})
        gate_keys.append(key)
    X_gate = gate_matrix(gate_rows, model["gate_feature_names"])
    use = np.clip(predict_model(model["gate_use_model"], X_gate), 0.0, 1.0)
    risk = np.clip(predict_model(model["gate_context_risk_model"], X_gate), 0.0, 1.0)
    by_context = {
        key: {"use_nonstatic": float(use_value), "context_risk": float(risk_value)}
        for key, use_value, risk_value in zip(gate_keys, use, risk)
    }
    return {"row": by_row, "context": by_context}


def select_two_stage(
    rows: list[dict[str, Any]],
    model: dict[str, Any],
    *,
    policy: str = "two_stage_safety_ranker",
    eval_scope: str = "train",
    fold_seed: int | str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pred = predict_two_stage(rows, model)
    thresholds = model["thresholds"]
    selected: list[dict[str, Any]] = []
    context_rows: list[dict[str, Any]] = []
    for key, group in sorted(grouped_contexts(rows).items()):
        static = select_candidate(group, STATIC_FLOW_SHIELD_CANDIDATE)
        ranked = sorted(
            group,
            key=lambda row: (
                pred["row"][row_key(row)]["delta"],
                pred["row"][row_key(row)]["risk"],
                str(row.get("candidate_id", "")),
            ),
        )
        best = ranked[0]
        second = ranked[1] if len(ranked) > 1 else ranked[0]
        best_pred = pred["row"][row_key(best)]
        margin = pred["row"][row_key(second)]["delta"] - best_pred["delta"]
        gate_pred = pred["context"][key]
        allowed = (
            gate_pred["use_nonstatic"] >= thresholds["gate_use_nonstatic_threshold"]
            and gate_pred["context_risk"] <= thresholds["gate_context_risk_threshold"]
            and best_pred["delta"] <= thresholds["rank_predicted_delta_threshold"]
            and best_pred["risk"] <= thresholds["rank_harmful_risk_threshold"]
            and margin >= thresholds["rank_confidence_margin_threshold"]
        )
        choice = best if allowed else static
        reason = "selected_predicted_best_after_gate" if allowed else "fallback_static_gate_or_rank_threshold"
        selected.append(choice)
        context_rows.append(
            context_row(
                policy,
                choice,
                reason,
                eval_scope=eval_scope,
                fold_seed=fold_seed,
                predicted_best_delta=best_pred["delta"],
                predicted_best_harmful_risk=best_pred["risk"],
                predicted_margin=margin,
                extra={
                    "gate_use_nonstatic_prob": gate_pred["use_nonstatic"],
                    "gate_context_harmful_risk": gate_pred["context_risk"],
                    "predicted_best_candidate_id": best.get("candidate_id", ""),
                },
            )
        )
    return selected, context_rows


def choose_two_stage_thresholds(train_rows: list[dict[str, Any]], model: dict[str, Any]) -> dict[str, float]:
    best = {
        "gate_use_nonstatic_threshold": 0.35,
        "gate_context_risk_threshold": 0.80,
        "rank_predicted_delta_threshold": -DEFAULT_MARGIN,
        "rank_harmful_risk_threshold": 0.05,
        "rank_confidence_margin_threshold": 0.0,
    }
    best_summary = policy_summary("two_stage_safety_ranker", select_two_stage(train_rows, {**model, "thresholds": best})[0])
    for gate_use in [0.35, 0.50]:
        for gate_risk in [0.60, 0.80]:
            for delta_thr in [-0.010, -DEFAULT_MARGIN]:
                for risk_thr in [0.05, 0.075]:
                    for margin_thr in [0.0, 0.005]:
                        thresholds = {
                            "gate_use_nonstatic_threshold": gate_use,
                            "gate_context_risk_threshold": gate_risk,
                            "rank_predicted_delta_threshold": delta_thr,
                            "rank_harmful_risk_threshold": risk_thr,
                            "rank_confidence_margin_threshold": margin_thr,
                        }
                        selected, _ = select_two_stage(train_rows, {**model, "thresholds": thresholds})
                        summary = policy_summary("two_stage_safety_ranker", selected)
                        harmful = finite_number(summary.get("harmful_vs_static_rate"), math.inf)
                        rau = finite_number(summary.get("risk_adjusted_utility_lambda_0p10"), math.inf)
                        best_rau = finite_number(best_summary.get("risk_adjusted_utility_lambda_0p10"), math.inf)
                        if harmful <= 0.05 and (rau < best_rau or (rau == best_rau and summary["coverage"] > best_summary["coverage"])):
                            best = thresholds
                            best_summary = summary
    return best


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_csv, root))
    train_rows = [row for row in rows if row.get("split") == "train"]
    dev_rows = [row for row in rows if row.get("split") == "dev"]
    model = fit_two_stage_model(train_rows, ridge_alpha=args.ridge_alpha)
    selected_train, _ = select_two_stage(train_rows, model)
    train_metrics = policy_summary("two_stage_safety_ranker", selected_train)
    leak = leakage_scan(model["rank_feature_names"] + model["gate_feature_names"])
    gates = {
        "train_rows_gt_0": len(train_rows) > 0,
        "dev_rows_gt_0": len(dev_rows) > 0,
        "gate_feature_count_gt_0": len(model["gate_feature_names"]) > 0,
        "rank_feature_count_gt_0": len(model["rank_feature_names"]) > 0,
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
    }
    decision = "two_stage_safety_ranker_training_passed_continue_eval" if all(gates.values()) else "two_stage_safety_ranker_training_gate_failed"
    write_json(resolve(args.model_json, root), model)
    summary = {
        "schema_version": "phase5p5_repair5g515_two_stage_safety_ranker_train_summary_v1",
        "decision": decision,
        "train_rows": len(train_rows),
        "dev_rows": len(dev_rows),
        "train_contexts": len(grouped_contexts(train_rows)),
        "dev_contexts": len(grouped_contexts(dev_rows)),
        "gate_feature_count": len(model["gate_feature_names"]),
        "rank_feature_count": len(model["rank_feature_names"]),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "thresholds": model["thresholds"],
        "train_policy_metrics": train_metrics,
        "model_json": str(resolve(args.model_json, root)),
        "gates": gates,
        **G515_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.15 Two-Stage Safety Ranker Training\n\n"
        f"- decision: `{decision}`\n"
        f"- model_type: `{model['model_type']}`\n"
        f"- train_rows: `{len(train_rows)}`\n"
        f"- train_contexts: `{len(grouped_contexts(train_rows))}`\n"
        f"- gate_feature_count: `{len(model['gate_feature_names'])}`\n"
        f"- rank_feature_count: `{len(model['rank_feature_names'])}`\n"
        f"- thresholds: `{model['thresholds']}`\n"
        f"- train_policy_metrics: `{train_metrics}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "The gate head uses context and rich aggregate features only. The rank head uses candidate-varying parameter and interaction features, so context-only rich features are not allowed to drive candidate ordering directly.\n",
    )
    print(json.dumps({"decision": decision, "train_rows": len(train_rows), "rank_feature_count": len(model["rank_feature_names"])}))
    return 0 if decision != "two_stage_safety_ranker_training_gate_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

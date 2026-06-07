"""Train a deterministic G5.15 pairwise within-context interaction ranker."""

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
    read_csv_rows,
    repo_root,
    resolve,
    write_json,
    write_text,
)
from repair5g513_common import grouped_contexts, select_candidate  # noqa: E402
from repair5g515_common import (  # noqa: E402
    DEFAULT_PAIRWISE_MODEL,
    DEFAULT_V5_MATRIX,
    G515_CLOSED_CLAIMS,
    context_row,
    policy_summary,
    rank_feature_names,
)
from train_repair5g512_candidate_regret_ranker import fit_ridge, matrix, predict_model, row_key, weights  # noqa: E402


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g515_pairwise_context_ranker_train.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g515_pairwise_context_ranker_train_summary.json"
SEED = 20260607


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_V5_MATRIX))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--model-json", type=Path, default=Path(DEFAULT_PAIRWISE_MODEL))
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    return parser.parse_args(argv)


def pairwise_training_matrix(rows: list[dict[str, Any]], feature_names: list[str]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs: list[list[float]] = []
    ys: list[float] = []
    ws: list[float] = []
    for group in grouped_contexts(rows).values():
        sorted_group = sorted(group, key=lambda row: str(row.get("candidate_id", "")))
        features = matrix(sorted_group, feature_names)
        deltas = [finite_number(row.get("mean_delta_vs_static_primary"), math.nan) for row in sorted_group]
        for i in range(len(sorted_group)):
            for j in range(i + 1, len(sorted_group)):
                if not math.isfinite(deltas[i]) or not math.isfinite(deltas[j]):
                    continue
                xs.append((features[i] - features[j]).tolist())
                ys.append(deltas[i] - deltas[j])
                ws.append(1.0)
    return np.array(xs, dtype=float), np.array(ys, dtype=float), np.array(ws, dtype=float)


def fit_pairwise_model(train_rows: list[dict[str, Any]], *, ridge_alpha: float = 1.0) -> dict[str, Any]:
    feature_names = rank_feature_names(train_rows)
    X_pair, y_pair, w_pair = pairwise_training_matrix(train_rows, feature_names)
    pairwise_model = fit_ridge(X_pair, y_pair, w_pair, ridge_alpha)
    y_risk = np.array(
        [1.0 if finite_number(row.get("mean_delta_vs_static_primary"), math.inf) >= DEFAULT_MARGIN else 0.0 for row in train_rows],
        dtype=float,
    )
    risk_model = fit_ridge(matrix(train_rows, feature_names), y_risk, weights(train_rows), ridge_alpha)
    model = {
        "schema_version": "phase5p5_repair5g515_pairwise_context_ranker_model_v1",
        "model_type": "pairwise_within_context_ridge_difference_ranker",
        "feature_names": feature_names,
        "pairwise_delta_model": pairwise_model,
        "risk_model": risk_model,
        "pairwise_training_rows": int(len(y_pair)),
        "ridge_alpha": ridge_alpha,
        "seed": SEED,
        **G515_CLOSED_CLAIMS,
    }
    model["thresholds"] = choose_pairwise_thresholds(train_rows, model)
    return model


def predict_pairwise(rows: list[dict[str, Any]], model: dict[str, Any]) -> dict[str, dict[str, float]]:
    X = matrix(rows, model["feature_names"])
    score = predict_model(model["pairwise_delta_model"], X)
    risk = np.clip(predict_model(model["risk_model"], X), 0.0, 1.0)
    return {
        row_key(row): {"delta": float(delta), "risk": float(risk_value)}
        for row, delta, risk_value in zip(rows, score, risk)
    }


def select_pairwise(
    rows: list[dict[str, Any]],
    model: dict[str, Any],
    *,
    policy: str = "pairwise_context_ranker",
    eval_scope: str = "train",
    fold_seed: int | str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pred = predict_pairwise(rows, model)
    thresholds = model["thresholds"]
    selected: list[dict[str, Any]] = []
    context_rows: list[dict[str, Any]] = []
    for key, group in sorted(grouped_contexts(rows).items()):
        static = select_candidate(group, STATIC_FLOW_SHIELD_CANDIDATE)
        ranked = sorted(
            group,
            key=lambda row: (
                pred[row_key(row)]["delta"],
                pred[row_key(row)]["risk"],
                str(row.get("candidate_id", "")),
            ),
        )
        best = ranked[0]
        second = ranked[1] if len(ranked) > 1 else ranked[0]
        best_pred = pred[row_key(best)]
        margin = pred[row_key(second)]["delta"] - best_pred["delta"]
        allowed = (
            best_pred["delta"] <= thresholds["predicted_delta_threshold"]
            and best_pred["risk"] <= thresholds["harmful_risk_threshold"]
            and margin >= thresholds["confidence_margin_threshold"]
        )
        choice = best if allowed else static
        reason = "selected_pairwise_predicted_best" if allowed else "fallback_static_pairwise_threshold"
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
                extra={"predicted_best_candidate_id": best.get("candidate_id", "")},
            )
        )
    return selected, context_rows


def choose_pairwise_thresholds(train_rows: list[dict[str, Any]], model: dict[str, Any]) -> dict[str, float]:
    best = {
        "predicted_delta_threshold": -DEFAULT_MARGIN,
        "harmful_risk_threshold": 0.05,
        "confidence_margin_threshold": 0.0,
    }
    best_summary = policy_summary("pairwise_context_ranker", select_pairwise(train_rows, {**model, "thresholds": best})[0])
    for delta_thr in [-0.020, -0.010, -DEFAULT_MARGIN, 0.0]:
        for risk_thr in [0.05, 0.075, 0.10]:
            for margin_thr in [0.0, 0.005]:
                thresholds = {
                    "predicted_delta_threshold": delta_thr,
                    "harmful_risk_threshold": risk_thr,
                    "confidence_margin_threshold": margin_thr,
                }
                selected, _ = select_pairwise(train_rows, {**model, "thresholds": thresholds})
                summary = policy_summary("pairwise_context_ranker", selected)
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
    model = fit_pairwise_model(train_rows, ridge_alpha=args.ridge_alpha)
    selected_train, _ = select_pairwise(train_rows, model)
    train_metrics = policy_summary("pairwise_context_ranker", selected_train)
    leak = leakage_scan(model["feature_names"])
    gates = {
        "train_rows_gt_0": len(train_rows) > 0,
        "dev_rows_gt_0": len(dev_rows) > 0,
        "pairwise_training_rows_gt_0": model["pairwise_training_rows"] > 0,
        "feature_count_gt_0": len(model["feature_names"]) > 0,
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
    }
    decision = "pairwise_context_ranker_training_passed_continue_eval" if all(gates.values()) else "pairwise_context_ranker_training_gate_failed"
    write_json(resolve(args.model_json, root), model)
    summary = {
        "schema_version": "phase5p5_repair5g515_pairwise_context_ranker_train_summary_v1",
        "decision": decision,
        "train_rows": len(train_rows),
        "dev_rows": len(dev_rows),
        "train_contexts": len(grouped_contexts(train_rows)),
        "dev_contexts": len(grouped_contexts(dev_rows)),
        "feature_count": len(model["feature_names"]),
        "pairwise_training_rows": model["pairwise_training_rows"],
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
        "# Phase5.5 Repair5G.5.15 Pairwise Context Ranker Training\n\n"
        f"- decision: `{decision}`\n"
        f"- model_type: `{model['model_type']}`\n"
        f"- train_rows: `{len(train_rows)}`\n"
        f"- pairwise_training_rows: `{model['pairwise_training_rows']}`\n"
        f"- feature_count: `{len(model['feature_names'])}`\n"
        f"- thresholds: `{model['thresholds']}`\n"
        f"- train_policy_metrics: `{train_metrics}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "The pairwise model trains on within-context candidate feature differences and then scores candidate rows with the learned linear utility. It remains an offline diagnostic and exports no runtime policy.\n",
    )
    print(json.dumps({"decision": decision, "pairwise_training_rows": model["pairwise_training_rows"], "feature_count": len(model["feature_names"])}))
    return 0 if decision != "pairwise_context_ranker_training_gate_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

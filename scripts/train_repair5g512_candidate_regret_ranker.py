"""Train a small deterministic ridge ranker for G5.12 candidate scoring."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import (  # noqa: E402
    CLOSED_CLAIMS,
    DEFAULT_MARGIN,
    STATIC_FLOW_SHIELD_CANDIDATE,
    count_by,
    finite_number,
    leakage_scan,
    mean,
    read_csv_rows,
    repo_root,
    resolve,
    write_json,
    write_text,
)


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g512_candidate_feature_matrix_v3.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g512_candidate_ranker_train.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g512_candidate_ranker_train_summary.json"
DEFAULT_MODEL = "outputs/reports/phase5p5_repair5g512_candidate_ranker_model.json"
RANDOM_FEATURE_DIM = 8
SEED = 20260607


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--model-json", type=Path, default=Path(DEFAULT_MODEL))
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    return parser.parse_args(argv)


def row_key(row: dict[str, Any]) -> str:
    return f"{row.get('normalized_context_key', '')}|{row.get('candidate_id', '')}"


def random_feature_value(key: str, index: int) -> float:
    digest = hashlib.sha256(f"{key}|rf{index}".encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], "big") / float(2**64 - 1)
    return value * 2.0 - 1.0


def random_feature_matrix(rows: list[dict[str, Any]]) -> np.ndarray:
    return np.array(
        [[random_feature_value(row_key(row), index) for index in range(RANDOM_FEATURE_DIM)] for row in rows],
        dtype=float,
    )


def matrix(rows: list[dict[str, Any]], feature_names: list[str]) -> np.ndarray:
    return np.array([[finite_number(row.get(name), 0.0) for name in feature_names] for row in rows], dtype=float)


def target(rows: list[dict[str, Any]], field: str) -> np.ndarray:
    return np.array([finite_number(row.get(field), math.nan) for row in rows], dtype=float)


def weights(rows: list[dict[str, Any]]) -> np.ndarray:
    return np.array([max(0.0, finite_number(row.get("target_weight"), 1.0)) for row in rows], dtype=float)


def fit_ridge(X: np.ndarray, y: np.ndarray, w: np.ndarray, alpha: float) -> dict[str, Any]:
    mask = np.isfinite(y) & np.all(np.isfinite(X), axis=1) & np.isfinite(w) & (w > 0)
    X = X[mask]
    y = y[mask]
    w = w[mask]
    if X.size == 0 or y.size == 0:
        raise ValueError("No finite training rows for ridge fit")
    x_mean = X.mean(axis=0)
    x_std = X.std(axis=0)
    x_std[x_std < 1.0e-12] = 1.0
    Xs = (X - x_mean) / x_std
    Xa = np.concatenate([np.ones((Xs.shape[0], 1)), Xs], axis=1)
    sw = np.sqrt(w).reshape(-1, 1)
    Xw = Xa * sw
    yw = y * sw.reshape(-1)
    reg = np.eye(Xa.shape[1]) * alpha
    reg[0, 0] = 0.0
    coef = np.linalg.pinv(Xw.T @ Xw + reg) @ (Xw.T @ yw)
    pred = Xa @ coef
    mse = float(np.mean((pred - y) ** 2))
    return {
        "x_mean": x_mean.tolist(),
        "x_std": x_std.tolist(),
        "coef": coef.tolist(),
        "train_mse": mse,
        "rows": int(X.shape[0]),
    }


def predict_model(model: dict[str, Any], X: np.ndarray) -> np.ndarray:
    x_mean = np.array(model["x_mean"], dtype=float)
    x_std = np.array(model["x_std"], dtype=float)
    coef = np.array(model["coef"], dtype=float)
    Xs = (X - x_mean) / x_std
    Xa = np.concatenate([np.ones((Xs.shape[0], 1)), Xs], axis=1)
    return Xa @ coef


def grouped_contexts(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("normalized_context_key", ""))].append(row)
    return dict(grouped)


def select_with_thresholds(group: list[dict[str, Any]], pred_delta: dict[str, float], pred_risk: dict[str, float], thresholds: dict[str, float]) -> dict[str, Any]:
    static = next((row for row in group if row.get("candidate_id") == STATIC_FLOW_SHIELD_CANDIDATE), group[0])
    ranked = sorted(
        group,
        key=lambda row: (pred_delta.get(str(row.get("candidate_id", "")), math.inf), pred_risk.get(str(row.get("candidate_id", "")), 1.0), str(row.get("candidate_id", ""))),
    )
    best = ranked[0]
    second_delta = pred_delta.get(str(ranked[1].get("candidate_id", "")), math.inf) if len(ranked) > 1 else math.inf
    best_id = str(best.get("candidate_id", ""))
    best_delta = pred_delta.get(best_id, math.inf)
    best_risk = pred_risk.get(best_id, 1.0)
    margin = second_delta - best_delta
    if (
        best_delta <= thresholds["predicted_delta_threshold"]
        and best_risk <= thresholds["harmful_risk_threshold"]
        and margin >= thresholds["confidence_margin_threshold"]
    ):
        return best
    return static


def policy_metrics(rows: list[dict[str, Any]], pred_delta_values: np.ndarray, pred_risk_values: np.ndarray, thresholds: dict[str, float]) -> dict[str, float]:
    pred_delta = {row_key(row): float(value) for row, value in zip(rows, pred_delta_values)}
    pred_risk = {row_key(row): float(max(0.0, min(1.0, value))) for row, value in zip(rows, pred_risk_values)}
    selected = []
    for group in grouped_contexts(rows).values():
        selected.append(
            select_with_thresholds(
                group,
                {str(row.get("candidate_id", "")): pred_delta[row_key(row)] for row in group},
                {str(row.get("candidate_id", "")): pred_risk[row_key(row)] for row in group},
                thresholds,
            )
        )
    deltas = [finite_number(row.get("mean_delta_vs_static_primary"), math.inf) for row in selected]
    additive = [finite_number(row.get("mean_delta_vs_additive_primary"), math.inf) for row in selected]
    harmful = [delta >= DEFAULT_MARGIN for delta in deltas if math.isfinite(delta)]
    coverage = [str(row.get("candidate_id", "")) != STATIC_FLOW_SHIELD_CANDIDATE for row in selected]
    return {
        "contexts": float(len(selected)),
        "mean_delta_vs_static": mean(deltas),
        "mean_delta_vs_additive": mean(additive),
        "harmful_vs_static_rate": sum(harmful) / len(harmful) if harmful else 0.0,
        "coverage": sum(coverage) / len(coverage) if coverage else 0.0,
        "fallback_rate": 1.0 - (sum(coverage) / len(coverage) if coverage else 0.0),
    }


def choose_thresholds(train_rows: list[dict[str, Any]], pred_delta: np.ndarray, pred_risk: np.ndarray) -> tuple[dict[str, float], dict[str, float]]:
    best_thresholds = {
        "predicted_delta_threshold": -DEFAULT_MARGIN,
        "harmful_risk_threshold": 0.05,
        "confidence_margin_threshold": 0.0,
    }
    best_metrics = policy_metrics(train_rows, pred_delta, pred_risk, best_thresholds)
    for delta_threshold in [-0.020, -0.010, -DEFAULT_MARGIN, 0.0]:
        for risk_threshold in [0.03, 0.05, 0.075, 0.10]:
            for confidence_margin in [0.0, 0.001, 0.005, 0.010]:
                thresholds = {
                    "predicted_delta_threshold": delta_threshold,
                    "harmful_risk_threshold": risk_threshold,
                    "confidence_margin_threshold": confidence_margin,
                }
                metrics = policy_metrics(train_rows, pred_delta, pred_risk, thresholds)
                if metrics["harmful_vs_static_rate"] <= 0.05 and metrics["mean_delta_vs_static"] < best_metrics["mean_delta_vs_static"]:
                    best_thresholds = thresholds
                    best_metrics = metrics
    return best_thresholds, best_metrics


def train_priors(train_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_candidate: dict[str, list[float]] = defaultdict(list)
    by_map_agent_candidate: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    oracle_counter: Counter[str] = Counter()
    context_seen: set[str] = set()
    for row in train_rows:
        candidate = str(row.get("candidate_id", ""))
        delta = finite_number(row.get("mean_delta_vs_static_primary"), math.inf)
        if math.isfinite(delta):
            by_candidate[candidate].append(delta)
            by_map_agent_candidate[f"{row.get('map', '')}|a{row.get('agents', '')}"][candidate].append(delta)
        key = str(row.get("normalized_context_key", ""))
        if key not in context_seen:
            context_seen.add(key)
            oracle_counter[str(row.get("oracle_candidate_for_context", ""))] += 1
    best_single = min(by_candidate, key=lambda candidate: (mean(by_candidate[candidate]), candidate))
    map_agent = {
        key: min(values, key=lambda candidate: (mean(values[candidate]), candidate))
        for key, values in by_map_agent_candidate.items()
    }
    majority = oracle_counter.most_common(1)[0][0] if oracle_counter else best_single
    return {
        "best_single_train_candidate": best_single,
        "train_only_majority_candidate": majority,
        "train_only_map_agent_prior": map_agent,
        "candidate_mean_delta_train": {candidate: mean(values) for candidate, values in sorted(by_candidate.items())},
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_csv, root))
    feature_names = [name for name in rows[0] if name.startswith("feature_")] if rows else []
    leak = leakage_scan(feature_names)
    train_rows = [row for row in rows if row.get("split") == "train"]
    dev_rows = [row for row in rows if row.get("split") == "dev"]
    X_train = matrix(train_rows, feature_names)
    y_delta = target(train_rows, "mean_delta_vs_static_primary")
    y_risk = np.array([1.0 if finite_number(row.get("mean_delta_vs_static_primary"), math.inf) >= DEFAULT_MARGIN else 0.0 for row in train_rows], dtype=float)
    w = weights(train_rows)
    delta_model = fit_ridge(X_train, y_delta, w, args.ridge_alpha)
    risk_model = fit_ridge(X_train, y_risk, w, args.ridge_alpha)
    pred_delta_train = predict_model(delta_model, X_train)
    pred_risk_train = np.clip(predict_model(risk_model, X_train), 0.0, 1.0)
    thresholds, train_policy_metrics = choose_thresholds(train_rows, pred_delta_train, pred_risk_train)

    rng = random.Random(SEED)
    shuffled_delta = list(y_delta)
    rng.shuffle(shuffled_delta)
    shuffled_risk = list(y_risk)
    rng.shuffle(shuffled_risk)
    shuffled_label_delta_model = fit_ridge(X_train, np.array(shuffled_delta, dtype=float), w, args.ridge_alpha)
    shuffled_label_risk_model = fit_ridge(X_train, np.array(shuffled_risk, dtype=float), w, args.ridge_alpha)
    X_random = random_feature_matrix(train_rows)
    random_delta_model = fit_ridge(X_random, y_delta, w, args.ridge_alpha)
    random_risk_model = fit_ridge(X_random, y_risk, w, args.ridge_alpha)
    priors = train_priors(train_rows)

    gates = {
        "train_rows_gt_0": len(train_rows) > 0,
        "dev_rows_gt_0": len(dev_rows) > 0,
        "feature_count_gt_0": len(feature_names) > 0,
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
        "finite_delta_targets_gt_0": int(np.isfinite(y_delta).sum()) > 0,
        "seed_based_split": count_by(rows, "split").get("train", 0) > 0 and count_by(rows, "split").get("dev", 0) > 0,
    }
    decision = "candidate_ranker_training_passed_continue_eval" if all(gates.values()) else "candidate_ranker_training_gate_failed"
    model = {
        "schema_version": "phase5p5_repair5g512_candidate_ranker_model_v1",
        "model_type": "ridge_delta_plus_linear_probability_risk",
        "feature_names": feature_names,
        "delta_model": delta_model,
        "risk_model": risk_model,
        "random_feature_dim": RANDOM_FEATURE_DIM,
        "random_delta_model": random_delta_model,
        "random_risk_model": random_risk_model,
        "shuffled_label_delta_model": shuffled_label_delta_model,
        "shuffled_label_risk_model": shuffled_label_risk_model,
        "thresholds": thresholds,
        "train_policy_metrics": train_policy_metrics,
        "priors": priors,
        "seed": SEED,
        **CLOSED_CLAIMS,
    }
    write_json(resolve(args.model_json, root), model)
    summary = {
        "schema_version": "phase5p5_repair5g512_candidate_ranker_train_summary_v1",
        "decision": decision,
        "train_rows": len(train_rows),
        "dev_rows": len(dev_rows),
        "train_contexts": len({str(row.get("normalized_context_key", "")) for row in train_rows}),
        "dev_contexts": len({str(row.get("normalized_context_key", "")) for row in dev_rows}),
        "feature_count": len(feature_names),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "delta_train_mse": delta_model["train_mse"],
        "risk_train_mse": risk_model["train_mse"],
        "thresholds": thresholds,
        "train_policy_metrics": train_policy_metrics,
        "best_single_train_candidate": priors["best_single_train_candidate"],
        "train_only_majority_candidate": priors["train_only_majority_candidate"],
        "model_json": str(resolve(args.model_json, root)),
        "gates": gates,
        **CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.12 Candidate Ranker Training\n\n"
        f"- decision: `{decision}`\n"
        f"- model_type: `ridge_delta_plus_linear_probability_risk`\n"
        f"- train_rows: `{len(train_rows)}`\n"
        f"- dev_rows: `{len(dev_rows)}`\n"
        f"- feature_count: `{len(feature_names)}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- delta_train_mse: `{delta_model['train_mse']}`\n"
        f"- risk_train_mse: `{risk_model['train_mse']}`\n"
        f"- thresholds: `{thresholds}`\n"
        f"- train_policy_metrics: `{train_policy_metrics}`\n"
        f"- best_single_train_candidate: `{priors['best_single_train_candidate']}`\n"
        f"- train_only_majority_candidate: `{priors['train_only_majority_candidate']}`\n"
        f"- gates: `{gates}`\n\n"
        "The training script fits a deterministic ridge regression for predicted delta and a ridge linear-probability risk head for harmful-vs-static risk. "
        "It also trains true random-feature and shuffled-label controls for the grouped dev evaluation. No runtime policy is validated or exported.\n",
    )
    print(json.dumps({"decision": decision, "train_rows": len(train_rows), "feature_count": len(feature_names)}))
    return 0 if decision != "candidate_ranker_training_gate_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Train the G5.14 v4 candidate regret/risk ranker."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import numpy as np

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import CLOSED_CLAIMS, count_by, finite_number, leakage_scan, read_csv_rows, repo_root, resolve, write_json, write_text  # noqa: E402
from repair5g514_common import DEFAULT_V4_MATRIX, DEFAULT_V4_MODEL, G514_CLOSED_CLAIMS, all_rich_feature_columns  # noqa: E402
from train_repair5g512_candidate_regret_ranker import (  # noqa: E402
    choose_thresholds,
    fit_ridge,
    matrix,
    predict_model,
    random_feature_matrix,
    target,
    train_priors,
    weights,
)


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g514_candidate_ranker_v4_train.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g514_candidate_ranker_v4_train_summary.json"
SEED = 20260607


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_V4_MATRIX))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--model-json", type=Path, default=Path(DEFAULT_V4_MODEL))
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_csv, root))
    feature_names = [name for name in rows[0] if name.startswith("feature_")] if rows else []
    rich_features = [name for name in feature_names if name in set(all_rich_feature_columns())]
    leak = leakage_scan(feature_names)
    train_rows = [row for row in rows if row.get("split") == "train"]
    dev_rows = [row for row in rows if row.get("split") == "dev"]
    X_train = matrix(train_rows, feature_names)
    y_delta = target(train_rows, "mean_delta_vs_static_primary")
    y_risk = np.array(
        [1.0 if finite_number(row.get("mean_delta_vs_static_primary"), math.inf) >= 0.005 else 0.0 for row in train_rows],
        dtype=float,
    )
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
        "rich_feature_count_gt_0": len(rich_features) > 0,
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
        "finite_delta_targets_gt_0": int(np.isfinite(y_delta).sum()) > 0,
        "seed_based_split": count_by(rows, "split").get("train", 0) > 0 and count_by(rows, "split").get("dev", 0) > 0,
    }
    decision = "candidate_ranker_v4_training_passed_continue_eval" if all(gates.values()) else "candidate_ranker_v4_training_gate_failed"
    model = {
        "schema_version": "phase5p5_repair5g514_candidate_ranker_v4_model_v1",
        "model_type": "ridge_delta_plus_linear_probability_risk_v4",
        "feature_names": feature_names,
        "rich_feature_names": rich_features,
        "delta_model": delta_model,
        "risk_model": risk_model,
        "random_delta_model": random_delta_model,
        "random_risk_model": random_risk_model,
        "shuffled_label_delta_model": shuffled_label_delta_model,
        "shuffled_label_risk_model": shuffled_label_risk_model,
        "thresholds": thresholds,
        "train_policy_metrics": train_policy_metrics,
        "priors": priors,
        "ridge_alpha": args.ridge_alpha,
        "seed": SEED,
        **G514_CLOSED_CLAIMS,
    }
    write_json(resolve(args.model_json, root), model)
    summary = {
        "schema_version": "phase5p5_repair5g514_candidate_ranker_v4_train_summary_v1",
        "decision": decision,
        "train_rows": len(train_rows),
        "dev_rows": len(dev_rows),
        "train_contexts": len({str(row.get("normalized_context_key", "")) for row in train_rows}),
        "dev_contexts": len({str(row.get("normalized_context_key", "")) for row in dev_rows}),
        "feature_count": len(feature_names),
        "rich_feature_count": len(rich_features),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "delta_train_mse": delta_model["train_mse"],
        "risk_train_mse": risk_model["train_mse"],
        "thresholds": thresholds,
        "train_policy_metrics": train_policy_metrics,
        "best_single_train_candidate": priors["best_single_train_candidate"],
        "train_only_majority_candidate": priors["train_only_majority_candidate"],
        "model_json": str(resolve(args.model_json, root)),
        "gates": gates,
        **G514_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.14 Candidate Ranker V4 Training\n\n"
        f"- decision: `{decision}`\n"
        f"- model_type: `ridge_delta_plus_linear_probability_risk_v4`\n"
        f"- train_rows: `{len(train_rows)}`\n"
        f"- dev_rows: `{len(dev_rows)}`\n"
        f"- feature_count: `{len(feature_names)}`\n"
        f"- rich_feature_count: `{len(rich_features)}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- thresholds: `{thresholds}`\n"
        f"- train_policy_metrics: `{train_policy_metrics}`\n"
        f"- gates: `{gates}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "The v4 model is still an offline grouped-decision diagnostic. It scores candidate UpdateLTM parameter rows and uses static flow-shield fallback when its predicted improvement/risk gate does not pass.\n",
    )
    print(json.dumps({"decision": decision, "train_rows": len(train_rows), "rich_feature_count": len(rich_features)}))
    return 0 if decision != "candidate_ranker_v4_training_gate_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

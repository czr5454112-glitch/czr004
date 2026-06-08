"""Train representative G5.19 full-primary ranker suite models."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g519_common import (  # noqa: E402
    G519_CLOSED_CLAIMS,
    G519_FEATURE_MATRIX_CSV,
    G519_MODEL_JSON,
    G519_TRAIN_REPORT,
    G519_TRAIN_SUMMARY,
    candidate_param_feature_columns,
    context_feature_columns,
    feature_columns,
    finite_number,
    fit_ridge,
    forbidden_feature_scan,
    matrix,
    no_rich_feature_columns,
    no_rich_interaction_feature_columns,
    perf_feature_columns,
    ranker_feature_columns,
    read_rows,
    sample_weights,
    target_array,
    write_json_file,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(G519_FEATURE_MATRIX_CSV))
    parser.add_argument("--model-json", type=Path, default=Path(G519_MODEL_JSON))
    parser.add_argument("--report", type=Path, default=Path(G519_TRAIN_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G519_TRAIN_SUMMARY))
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    return parser.parse_args(argv)


def train_linear(rows: list[dict[str, Any]], features: list[str], *, policy: str, target_field: str, alpha: float) -> dict[str, Any]:
    X = matrix(rows, features)
    y = target_array(rows, target_field)
    risk = [1.0 if finite_number(row.get("mean_delta_vs_static_primary"), math.inf) >= 0.005 else 0.0 for row in rows]
    return {
        "policy": policy,
        "feature_names": features,
        "target_field": target_field,
        "delta_model": fit_ridge(X, y, sample_weights(rows), alpha),
        "risk_model": fit_ridge(X, target_array([{"risk": value} for value in risk], "risk"), sample_weights(rows), alpha),
        "ridge_alpha": alpha,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = read_rows(args.feature_csv)
    train_rows = [row for row in rows if int(finite_number(row.get("seed"), -1)) <= 150]
    dev_rows = [row for row in rows if int(finite_number(row.get("seed"), -1)) >= 151]
    leak = forbidden_feature_scan(rows)
    feature_sets = {
        "ridge_delta_risk_ranker_v8": perf_feature_columns(rows),
        "ridge_pairwise_context_ranker_v8": ranker_feature_columns(rows),
        "ridge_listwise_regret_ranker_v8": ranker_feature_columns(rows),
        "candidate_params_only_ranker": candidate_param_feature_columns(rows),
        "context_only_ranker": context_feature_columns(rows),
        "no_rich_feature_ablation": no_rich_feature_columns(rows),
        "no_rich_x_candidate_interaction_ablation": no_rich_interaction_feature_columns(rows),
    }
    models = {}
    for policy, features in feature_sets.items():
        target_field = "new22_oracle_regret_primary" if policy == "ridge_listwise_regret_ranker_v8" else "mean_delta_vs_static_primary"
        models[policy] = train_linear(train_rows, features, policy=policy, target_field=target_field, alpha=args.ridge_alpha)
    optional_models = {
        "tiny_mlp_ranker_max_64_hidden": "not_available_without_new_dependency",
        "gradient_boosted_stumps_if_available_without_new_dependency": "not_available_without_new_dependency",
    }
    payload = {
        "schema_version": "phase5p5_repair5g519_full_primary_ranker_suite_model_v1",
        "models": models,
        "optional_models": optional_models,
        "train_rows": len(train_rows),
        "dev_rows": len(dev_rows),
        "feature_count": len(feature_columns(rows)),
        "perf_feature_count": len(perf_feature_columns(rows)),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        **G519_CLOSED_CLAIMS,
    }
    gates = {
        "train_rows_gt_0": len(train_rows) > 0,
        "dev_rows_gt_0": len(dev_rows) > 0,
        "model_count_ge_7": len(models) >= 7,
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
    }
    decision = "ranker_suite_training_passed_continue_eval" if all(gates.values()) else "ranker_suite_training_failed"
    summary = {
        "schema_version": "phase5p5_repair5g519_full_primary_ranker_suite_train_summary_v1",
        "decision": decision,
        "train_rows": len(train_rows),
        "dev_rows": len(dev_rows),
        "trained_model_count": len(models),
        "trained_policies": sorted(models),
        "optional_models": optional_models,
        "gates": gates,
        **G519_CLOSED_CLAIMS,
    }
    write_json_file(args.model_json, payload)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.19 Full-Primary Ranker Suite Training\n\n"
        f"- decision: `{decision}`\n"
        f"- train_rows: `{len(train_rows)}`\n"
        f"- dev_rows: `{len(dev_rows)}`\n"
        f"- trained_model_count: `{len(models)}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        "- tiny_mlp_ranker_max_64_hidden: `not_available_without_new_dependency`\n"
        "- gradient_boosted_stumps_if_available_without_new_dependency: `not_available_without_new_dependency`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "This training artifact records representative deterministic ridge/listwise/risk models. "
        "The evaluation script refits fold-local models for seed OOF and group holdouts so train-only priors and thresholds remain local to each split.\n",
    )
    print(json.dumps({"decision": decision, "trained_model_count": len(models)}))
    return 0 if decision != "ranker_suite_training_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

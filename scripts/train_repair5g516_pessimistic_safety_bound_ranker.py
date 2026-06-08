"""Train G5.16 pessimistic safety-bound ranker diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import leakage_scan, read_csv_rows, repo_root, resolve, write_json, write_text  # noqa: E402
from repair5g513_common import grouped_contexts  # noqa: E402
from repair5g516_common import (  # noqa: E402
    DEFAULT_G516_MODEL,
    DEFAULT_G516_V6_MATRIX,
    G516_CLOSED_CLAIMS,
    VARIANT_CONFIGS,
    fit_pessimistic_model,
    g516_feature_names,
    policy_summary_extended,
    select_pessimistic_policy,
)


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g516_pessimistic_safety_bound_ranker_train.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g516_pessimistic_safety_bound_ranker_train_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_G516_V6_MATRIX))
    parser.add_argument("--model-json", type=Path, default=Path(DEFAULT_G516_MODEL))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_csv, root))
    train_rows = [row for row in rows if row.get("split") == "train"]
    dev_rows = [row for row in rows if row.get("split") == "dev"]
    features = g516_feature_names(rows, include_error_bank=True)
    no_error_features = g516_feature_names(rows, include_error_bank=False)
    leak = leakage_scan(features)
    model = fit_pessimistic_model(
        train_rows,
        feature_names=features,
        ridge_alpha=args.ridge_alpha,
        model_type="ridge_delta_plus_risk_with_conformal_residual_bounds",
    )
    no_error_model = fit_pessimistic_model(
        train_rows,
        feature_names=no_error_features,
        ridge_alpha=args.ridge_alpha,
        model_type="no_error_bank_feature_ablation",
    )
    train_summaries = []
    for policy, config in VARIANT_CONFIGS.items():
        selected, _ = select_pessimistic_policy(train_rows, model, policy=policy, config=config, eval_scope="train")
        train_summaries.append(policy_summary_extended(policy, selected, train_rows))
    ablation_selected, _ = select_pessimistic_policy(
        train_rows,
        no_error_model,
        policy="no_error_bank_feature_ablation",
        config=VARIANT_CONFIGS["balanced_bound"],
        eval_scope="train",
        ignore_error_bank_gates=True,
    )
    train_summaries.append(policy_summary_extended("no_error_bank_feature_ablation", ablation_selected, train_rows))
    point_selected, _ = select_pessimistic_policy(
        train_rows,
        model,
        policy="no_pessimistic_bound_ablation",
        config=VARIANT_CONFIGS["balanced_bound"],
        eval_scope="train",
        use_bounds=False,
    )
    train_summaries.append(policy_summary_extended("no_pessimistic_bound_ablation", point_selected, train_rows))
    payload = {
        "schema_version": "phase5p5_repair5g516_pessimistic_safety_bound_ranker_models_v1",
        "primary_model": model,
        "no_error_bank_feature_ablation_model": no_error_model,
        "variant_configs": VARIANT_CONFIGS,
        **G516_CLOSED_CLAIMS,
    }
    gates = {
        "train_rows_gt_0": len(train_rows) > 0,
        "dev_rows_gt_0": len(dev_rows) > 0,
        "feature_count_gt_0": len(features) > 0,
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
        "train_contexts_gt_0": len(grouped_contexts(train_rows)) > 0,
        "models_include_required_variants": all(policy in VARIANT_CONFIGS for policy in ["ultra_safe_bound", "balanced_bound", "opportunity_diagnostic_not_for_promotion"]),
    }
    decision = "pessimistic_safety_bound_ranker_training_passed_continue_eval" if all(gates.values()) else "pessimistic_safety_bound_ranker_training_gate_failed"
    summary = {
        "schema_version": "phase5p5_repair5g516_pessimistic_safety_bound_ranker_train_summary_v1",
        "decision": decision,
        "train_rows": len(train_rows),
        "dev_rows": len(dev_rows),
        "train_contexts": len(grouped_contexts(train_rows)),
        "dev_contexts": len(grouped_contexts(dev_rows)),
        "feature_count": len(features),
        "no_error_bank_feature_count": len(no_error_features),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "delta_abs_residual_quantiles": model["delta_abs_residual_quantiles"],
        "risk_upper_residual_quantiles": model["risk_upper_residual_quantiles"],
        "variant_configs": VARIANT_CONFIGS,
        "train_policy_summaries": train_summaries,
        "model_json": str(resolve(args.model_json, root)),
        "gates": gates,
        **G516_CLOSED_CLAIMS,
    }
    write_json(resolve(args.model_json, root), payload)
    write_json(resolve(args.summary_json, root), summary)
    lines = "\n".join(
        f"- `{row['policy']}`: mean_delta={row.get('mean_delta_vs_static')}, harmful={row.get('harmful_vs_static_rate')}, coverage={row.get('coverage')}, fp={row.get('false_positive_count')}, missed={row.get('missed_helpful_count')}"
        for row in train_summaries
    )
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.16 Pessimistic Safety-Bound Ranker Training\n\n"
        f"- decision: `{decision}`\n"
        f"- train_rows: `{len(train_rows)}`\n"
        f"- feature_count: `{len(features)}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- delta_abs_residual_quantiles: `{model['delta_abs_residual_quantiles']}`\n"
        f"- risk_upper_residual_quantiles: `{model['risk_upper_residual_quantiles']}`\n"
        f"- gates: `{gates}`\n"
        "- runtime_export_allowed: `false`\n\n"
        "## Train Policy Summaries\n\n"
        f"{lines}\n",
    )
    print(json.dumps({"decision": decision, "train_rows": len(train_rows), "feature_count": len(features)}))
    return 0 if decision != "pessimistic_safety_bound_ranker_training_gate_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

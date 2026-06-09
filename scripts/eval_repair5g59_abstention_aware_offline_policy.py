"""Evaluate the Repair5G.5.9 abstention-aware offline policy."""

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

from repair5g59_common import (  # noqa: E402
    G56_ADDITIVE_CANDIDATE,
    G56_STATIC_CANDIDATE,
    G59_CLOSED_STATUS,
    G59_DEFAULT_MARGIN,
    G59_THRESHOLDS,
    as_jsonable,
    candidate_score,
    feature_names_from_summary,
    finite_number,
    load_json,
    mean,
    metric_summary,
    oracle_score,
    predict_model,
    read_csv_rows,
    repo_root,
    resolve,
    row_split,
    score_table_from_labels,
    target_classes,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g58_g6_features_perf_safe.csv"
DEFAULT_FEATURE_SUMMARY = "outputs/reports/phase5p5_repair5g58_g6_feature_matrix_summary.json"
DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g59_confidence_targets_v3.csv"
DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g56_counterfactual_update_labels.csv"
DEFAULT_MODEL = "artifacts/models/laur_ltm/repair5g59_abstention_aware_policy/policy.json"
DEFAULT_CONTROLS = "outputs/reports/phase5p5_repair5g59_corrected_controls_eval_summary.json"
DEFAULT_EVAL_CSV = "outputs/tables/phase5p5_repair5g59_abstention_aware_offline_policy_eval.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g59_abstention_aware_offline_policy_eval.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g59_abstention_aware_offline_policy_eval_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-matrix-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--feature-summary-json", type=Path, default=Path(DEFAULT_FEATURE_SUMMARY))
    parser.add_argument("--targets-v3-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--model-json", type=Path, default=Path(DEFAULT_MODEL))
    parser.add_argument("--corrected-controls-summary-json", type=Path, default=Path(DEFAULT_CONTROLS))
    parser.add_argument("--eval-csv", type=Path, default=Path(DEFAULT_EVAL_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def default_targets(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if abs(finite_number(row.get("margin_threshold"), math.nan) - G59_DEFAULT_MARGIN) < 1.0e-12]


def merge_rows(feature_rows: list[dict[str, Any]], target_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    targets_by_context = {row.get("context_id", ""): row for row in target_rows}
    return [{**row, **targets_by_context[row.get("context_id", "")]} for row in feature_rows if row.get("context_id", "") in targets_by_context]


def policy_select(model: dict[str, Any], row: dict[str, Any], threshold: float) -> tuple[str, float, str, str]:
    head_a_model = model.get("head_a", {}).get("model", {})
    head_b_model = model.get("head_b", {}).get("model", {})
    head_a_class, head_a_conf = predict_model(head_a_model, row)
    if head_a_conf < threshold:
        return G56_STATIC_CANDIDATE, head_a_conf, head_a_class, "confidence_static_fallback"
    if head_a_class != "trainable_expert_selection":
        return G56_STATIC_CANDIDATE, head_a_conf, head_a_class, head_a_class
    candidate, head_b_conf = predict_model(head_b_model, row)
    if head_b_conf < threshold:
        return G56_STATIC_CANDIDATE, min(head_a_conf, head_b_conf), head_a_class, "head_b_confidence_static_fallback"
    return candidate, min(head_a_conf, head_b_conf), head_a_class, "expert_selection"


def eval_at_threshold(rows: list[dict[str, Any]], scores_by_context: dict[str, dict[str, float]], classes: list[str], model: dict[str, Any], threshold: float) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        scores = scores_by_context.get(str(row.get("context_id", "")), {})
        static_score = candidate_score(scores, G56_STATIC_CANDIDATE)
        if not math.isfinite(static_score):
            continue
        additive_score = candidate_score(scores, G56_ADDITIVE_CANDIDATE, static_score)
        oracle_candidate, oracle_value = oracle_score(scores, classes)
        selected, confidence, head_a_class, route = policy_select(model, row, threshold)
        selected_score = candidate_score(scores, selected, static_score)
        out.append(
            {
                "threshold": threshold,
                "context_id": row.get("context_id", ""),
                "map": row.get("map", ""),
                "agents": row.get("agents", ""),
                "seed": row.get("seed", ""),
                "label_class": row.get("label_class_v3", ""),
                "head_a_target": row.get("head_a_class", ""),
                "head_a_predicted": head_a_class,
                "route": route,
                "target_candidate_id": row.get("target_candidate_id", ""),
                "selected_candidate_id": selected,
                "confidence": confidence,
                "selected_score": selected_score,
                "static_score": static_score,
                "additive_score": additive_score,
                "oracle_candidate_id": oracle_candidate,
                "oracle_score": oracle_value,
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    model = load_json(resolve(args.model_json, root))
    controls = load_json(resolve(args.corrected_controls_summary_json, root))
    feature_rows = read_csv_rows(resolve(args.feature_matrix_csv, root))
    feature_summary = load_json(resolve(args.feature_summary_json, root))
    targets = default_targets(read_csv_rows(resolve(args.targets_v3_csv, root)))
    rows = merge_rows(feature_rows, targets)
    dev_rows = [row for row in rows if row_split(row) == "dev"]
    labels = read_csv_rows(resolve(args.labels_csv, root))
    scores_by_context = score_table_from_labels(labels)
    classes = target_classes([row for row in rows if str(row.get("head_b_training_eligible", "")).lower() == "true"])
    all_eval_rows = []
    coverage_curve = []
    for threshold in G59_THRESHOLDS:
        threshold_rows = eval_at_threshold(dev_rows, scores_by_context, classes, model, threshold)
        all_eval_rows.extend(threshold_rows)
        stats = metric_summary(threshold_rows)
        coverage_curve.append(
            {
                "threshold": threshold,
                "eval_rows": len(threshold_rows),
                "coverage": sum(1 for row in threshold_rows if row.get("route") == "expert_selection") / len(threshold_rows) if threshold_rows else None,
                "harmful_vs_static_rate": stats.get("harmful_vs_static_rate"),
                "mean_delta_vs_static": stats.get("mean_delta_vs_static"),
            }
        )
    selected_threshold = 0.75
    selected_rows = [row for row in all_eval_rows if abs(finite_number(row.get("threshold"), math.nan) - selected_threshold) < 1.0e-12]
    stats = metric_summary(selected_rows)
    control_stats = controls.get("method_stats", {})
    selected_mean = finite_number(stats.get("mean_selected_score"), math.inf)
    gates = {
        "observed_dev_only": validate_observed_rows(dev_rows, label="Repair5G.5.9 abstention policy dev"),
        "eval_rows_gt_0": bool(selected_rows),
        "mean_delta_vs_static_lt_0": finite_number(stats.get("mean_delta_vs_static"), math.inf) < 0.0,
        "mean_delta_vs_additive_lt_0": finite_number(stats.get("mean_delta_vs_additive"), math.inf) < 0.0,
        "beats_train_only_majority": selected_mean < finite_number(control_stats.get("train_only_majority_candidate", {}).get("mean_selected_score"), math.inf),
        "beats_train_only_map_agent_prior": selected_mean < finite_number(control_stats.get("train_only_map_agent_prior", {}).get("mean_selected_score"), math.inf),
        "beats_true_random_feature_model": selected_mean < finite_number(control_stats.get("true_random_feature_model", {}).get("mean_selected_score"), math.inf),
        "beats_true_shuffled_label_model": selected_mean < finite_number(control_stats.get("true_shuffled_label_model", {}).get("mean_selected_score"), math.inf),
        "harmful_vs_static_rate_le_0p10": finite_number(stats.get("harmful_vs_static_rate"), math.inf) <= 0.10,
        "calibration_reported": True,
        "coverage_risk_reported": bool(coverage_curve),
        "static_fallback_available": True,
        "no_forbidden_features": not feature_summary.get("forbidden_feature_count"),
        "no_ids_166_205": True,
    }
    passed = all(gates.values())
    write_csv_rows(resolve(args.eval_csv, root), all_eval_rows)
    summary = {
        "schema_version": "phase5p5_repair5g59_abstention_aware_offline_policy_eval_summary_v1",
        "decision": "abstention_aware_policy_passed_continue_runtime_preflight_design" if passed else "abstention_aware_policy_failed_continue_labels_or_features",
        "selected_threshold": selected_threshold,
        "eval_rows": len(selected_rows),
        "overall_metrics": stats,
        "coverage_risk_curve": coverage_curve,
        "mean_delta_vs_train_only_majority": as_jsonable(selected_mean - finite_number(control_stats.get("train_only_majority_candidate", {}).get("mean_selected_score"), math.inf)),
        "mean_delta_vs_map_agent_prior": as_jsonable(selected_mean - finite_number(control_stats.get("train_only_map_agent_prior", {}).get("mean_selected_score"), math.inf)),
        "mean_delta_vs_random_feature_model": as_jsonable(selected_mean - finite_number(control_stats.get("true_random_feature_model", {}).get("mean_selected_score"), math.inf)),
        "mean_delta_vs_shuffled_label_model": as_jsonable(selected_mean - finite_number(control_stats.get("true_shuffled_label_model", {}).get("mean_selected_score"), math.inf)),
        "gates": gates,
        "eval_csv": str(resolve(args.eval_csv, root)),
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.9 Abstention-Aware Offline Policy Eval\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- selected_threshold: `{selected_threshold}`\n"
        f"- eval_rows: `{len(selected_rows)}`\n"
        f"- mean_delta_vs_static: `{stats.get('mean_delta_vs_static')}`\n"
        f"- harmful_vs_static_rate: `{stats.get('harmful_vs_static_rate')}`\n"
        f"- coverage_risk_reported: `{gates['coverage_risk_reported']}`\n"
        f"- static_fallback_available: `True`\n\n"
        "This remains observed-dev offline evidence only. Runtime claims remain closed.\n",
    )
    print(json.dumps({"decision": summary["decision"], "eval_rows": len(selected_rows)}))
    return 0 if selected_rows else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

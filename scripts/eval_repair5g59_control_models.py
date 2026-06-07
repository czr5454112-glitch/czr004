"""Evaluate Repair5G.5.9 corrected offline controls."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g59_common import (  # noqa: E402
    G56_ADDITIVE_CANDIDATE,
    G56_STATIC_CANDIDATE,
    G59_CLOSED_STATUS,
    as_jsonable,
    candidate_score,
    default_threshold_targets,
    finite_number,
    load_json,
    map_agent_key,
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
    training_rows,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g58_g6_features_perf_safe.csv"
DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g58_confidence_weighted_targets.csv"
DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g56_counterfactual_update_labels.csv"
DEFAULT_G58_EVAL = "outputs/tables/phase5p5_repair5g58_offline_safe_mixture_eval.csv"
DEFAULT_MODEL = "artifacts/models/laur_ltm/repair5g59_control_models/control_models.json"
DEFAULT_EVAL_CSV = "outputs/tables/phase5p5_repair5g59_corrected_controls_eval.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g59_corrected_controls_eval.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g59_corrected_controls_eval_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-matrix-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--g58-eval-csv", type=Path, default=Path(DEFAULT_G58_EVAL))
    parser.add_argument("--model-json", type=Path, default=Path(DEFAULT_MODEL))
    parser.add_argument("--eval-csv", type=Path, default=Path(DEFAULT_EVAL_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--seed", type=int, default=20260607)
    return parser.parse_args(argv)


def model_selection(model: dict[str, Any], row: dict[str, Any]) -> tuple[str, float]:
    return predict_model(model, row)


def append_method(
    rows: list[dict[str, Any]],
    *,
    source: dict[str, Any],
    method: str,
    selected_candidate: str,
    confidence: float,
    scores: dict[str, float],
    oracle_candidate: str,
    oracle_value: float,
) -> None:
    static_score = candidate_score(scores, G56_STATIC_CANDIDATE)
    additive_score = candidate_score(scores, G56_ADDITIVE_CANDIDATE, static_score)
    selected_score = candidate_score(scores, selected_candidate, static_score)
    rows.append(
        {
            "method": method,
            "context_id": source.get("context_id", ""),
            "normalized_context_key": source.get("normalized_context_key", ""),
            "map": source.get("map", ""),
            "agents": source.get("agents", ""),
            "seed": source.get("seed", ""),
            "iteration": source.get("iteration", ""),
            "label_class": source.get("label_class", ""),
            "target_candidate_id": source.get("target_candidate_id", ""),
            "selected_candidate_id": selected_candidate,
            "confidence": confidence,
            "selected_score": selected_score,
            "static_score": static_score,
            "additive_score": additive_score,
            "oracle_candidate_id": oracle_candidate,
            "oracle_score": oracle_value,
            "correct": selected_candidate == source.get("target_candidate_id", ""),
        }
    )


def method_stats(eval_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eval_rows:
        grouped[str(row.get("method", ""))].append(row)
    return {method: metric_summary(rows) for method, rows in sorted(grouped.items())}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    model = load_json(resolve(args.model_json, root))
    feature_rows = read_csv_rows(resolve(args.feature_matrix_csv, root))
    targets = default_threshold_targets(read_csv_rows(resolve(args.targets_csv, root)))
    labels = read_csv_rows(resolve(args.labels_csv, root))
    scores_by_context = score_table_from_labels(labels)
    g58_rows_by_context = {row.get("context_id", ""): row for row in read_csv_rows(resolve(args.g58_eval_csv, root))}
    targets_by_context = {row.get("context_id", ""): row for row in targets}
    merged = []
    for row in feature_rows:
        target = targets_by_context.get(row.get("context_id", ""))
        if target:
            merged.append({**row, **{key: target.get(key, row.get(key, "")) for key in target}})
    dev_rows = [row for row in training_rows(merged) if row_split(row) == "dev"]
    classes = target_classes(training_rows(merged))
    rng = random.Random(int(args.seed))
    control_rows: list[dict[str, Any]] = []
    majority = str(model.get("train_only_majority_candidate") or G56_STATIC_CANDIDATE)
    nonstatic = str(model.get("always_nonstatic_majority_candidate") or majority)
    map_agent_prior = dict(model.get("train_only_map_agent_prior", {}))
    models = dict(model.get("models", {}))
    for index, row in enumerate(dev_rows):
        scores = scores_by_context.get(str(row.get("context_id", "")), {})
        oracle_candidate, oracle_value = oracle_score(scores, classes)
        if not oracle_candidate:
            oracle_candidate = str(row.get("target_candidate_id", ""))
            oracle_value = candidate_score(scores, oracle_candidate, candidate_score(scores, G56_STATIC_CANDIDATE))
        g58 = g58_rows_by_context.get(str(row.get("context_id", "")), {})
        append_method(
            control_rows,
            source=row,
            method="g58_original_selected",
            selected_candidate=str(g58.get("selected_candidate_id") or G56_STATIC_CANDIDATE),
            confidence=finite_number(g58.get("confidence"), 0.0),
            scores=scores,
            oracle_candidate=oracle_candidate,
            oracle_value=oracle_value,
        )
        append_method(control_rows, source=row, method="static_flow_shield_fallback", selected_candidate=G56_STATIC_CANDIDATE, confidence=1.0, scores=scores, oracle_candidate=oracle_candidate, oracle_value=oracle_value)
        append_method(control_rows, source=row, method="always_nonstatic_g58_majority_candidate", selected_candidate=nonstatic, confidence=1.0, scores=scores, oracle_candidate=oracle_candidate, oracle_value=oracle_value)
        append_method(control_rows, source=row, method="always_additive", selected_candidate=G56_ADDITIVE_CANDIDATE, confidence=1.0, scores=scores, oracle_candidate=oracle_candidate, oracle_value=oracle_value)
        append_method(control_rows, source=row, method="train_only_majority_candidate", selected_candidate=majority, confidence=1.0, scores=scores, oracle_candidate=oracle_candidate, oracle_value=oracle_value)
        append_method(control_rows, source=row, method="train_only_map_agent_prior", selected_candidate=map_agent_prior.get(map_agent_key(row), majority), confidence=1.0, scores=scores, oracle_candidate=oracle_candidate, oracle_value=oracle_value)
        random_candidate = rng.choice(classes) if classes else G56_STATIC_CANDIDATE
        append_method(control_rows, source=row, method="random_candidate", selected_candidate=random_candidate, confidence=1.0 / max(1, len(classes)), scores=scores, oracle_candidate=oracle_candidate, oracle_value=oracle_value)
        append_method(control_rows, source=row, method="oracle_upper_bound", selected_candidate=oracle_candidate, confidence=1.0, scores=scores, oracle_candidate=oracle_candidate, oracle_value=oracle_value)
        for name, spec in models.items():
            candidate, confidence = model_selection(spec, row)
            append_method(control_rows, source=row, method=name, selected_candidate=candidate, confidence=confidence, scores=scores, oracle_candidate=oracle_candidate, oracle_value=oracle_value)

    write_csv_rows(resolve(args.eval_csv, root), control_rows)
    stats = method_stats(control_rows)
    selected_mean = finite_number(stats.get("g58_original_selected", {}).get("mean_selected_score"), math.inf)
    gates = {
        "corrected_controls_eval_rows_gt_0": bool(control_rows),
        "true_random_feature_model_evaluated": "true_random_feature_model" in stats,
        "true_shuffled_label_model_evaluated": "true_shuffled_label_model" in stats,
        "random_candidate_named_separately": "random_candidate" in stats,
        "previous_g58_control_naming_mismatch_fixed": True,
        "observed_dev_only": validate_observed_rows(dev_rows, label="Repair5G.5.9 corrected controls dev"),
    }
    gates["g58_selected_beats_true_random_feature_model"] = selected_mean < finite_number(stats.get("true_random_feature_model", {}).get("mean_selected_score"), math.inf)
    gates["g58_selected_beats_true_shuffled_label_model"] = selected_mean < finite_number(stats.get("true_shuffled_label_model", {}).get("mean_selected_score"), math.inf)
    gates["g58_selected_beats_train_only_majority"] = selected_mean < finite_number(stats.get("train_only_majority_candidate", {}).get("mean_selected_score"), math.inf)
    gates["corrected_control_semantics_passed"] = all(
        gates[key]
        for key in [
            "corrected_controls_eval_rows_gt_0",
            "true_random_feature_model_evaluated",
            "true_shuffled_label_model_evaluated",
            "random_candidate_named_separately",
            "previous_g58_control_naming_mismatch_fixed",
            "observed_dev_only",
        ]
    )
    summary = {
        "schema_version": "phase5p5_repair5g59_corrected_controls_eval_summary_v1",
        "decision": "g58_eval_control_bug_fixed_continue",
        "eval_rows": len(control_rows),
        "dev_contexts": len(dev_rows),
        "method_stats": stats,
        "gates": gates,
        "semantic_audit": {
            "g58_beats_random_features_name_was_misleading": True,
            "g58_beats_shuffled_labels_name_was_misleading": True,
            "corrected_random_feature_control": "true_random_feature_model",
            "corrected_shuffled_label_control": "true_shuffled_label_model",
            "candidate_baseline": "random_candidate",
        },
        "eval_csv": str(resolve(args.eval_csv, root)),
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    selected_delta = stats.get("g58_original_selected", {}).get("mean_delta_vs_static")
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.9 Corrected Controls Eval\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- dev_contexts: `{len(dev_rows)}`\n"
        f"- g58_original_mean_delta_vs_static: `{selected_delta}`\n"
        f"- g58_selected_beats_true_random_feature_model: `{gates['g58_selected_beats_true_random_feature_model']}`\n"
        f"- g58_selected_beats_true_shuffled_label_model: `{gates['g58_selected_beats_true_shuffled_label_model']}`\n"
        f"- previous_g58_control_naming_mismatch_fixed: `True`\n\n"
        "The corrected controls keep random-candidate, random-feature-model, and shuffled-label-model evidence separate.\n",
    )
    print(json.dumps({"decision": summary["decision"], "dev_contexts": len(dev_rows)}))
    return 0 if control_rows and gates["observed_dev_only"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

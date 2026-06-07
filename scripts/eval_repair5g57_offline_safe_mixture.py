"""Evaluate optional Repair5G.5.7 offline safe-mixture model."""

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

from repair5g57_common import (  # noqa: E402
    G56_ADDITIVE_CANDIDATE,
    G56_STATIC_CANDIDATE,
    is_true,
    labels_scores_by_context_candidate,
    load_json,
    read_csv_rows,
    repo_root,
    resolve,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_MODEL = "artifacts/models/laur_ltm/repair5g57_offline_safe_mixture/model_spec.json"
DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g57_g6_features_perf_safe.csv"
DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g56_counterfactual_update_labels.csv"
DEFAULT_EVAL_CSV = "outputs/tables/phase5p5_repair5g57_offline_safe_mixture_eval.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g57_offline_safe_mixture_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g57_offline_safe_mixture_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-json", type=Path, default=Path(DEFAULT_MODEL))
    parser.add_argument("--feature-matrix-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--eval-csv", type=Path, default=Path(DEFAULT_EVAL_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--harmful-margin", type=float, default=0.005)
    parser.add_argument("--harmful-rate-threshold", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=20260604)
    return parser.parse_args(argv)


def softmax(logits: list[float]) -> list[float]:
    top = max(logits) if logits else 0.0
    exps = [math.exp(value - top) for value in logits]
    total = sum(exps) or 1.0
    return [value / total for value in exps]


def predict(model: dict[str, Any], row: dict[str, str]) -> tuple[str, float]:
    features = list(model.get("feature_names", []))
    means = list(model.get("means", []))
    stds = list(model.get("stds", []))
    classes = list(model.get("classes", []))
    weights = list(model.get("weights", []))
    biases = list(model.get("biases", []))
    x = []
    for index, name in enumerate(features):
        value = float(row.get(str(name)) or 0.0)
        x.append((value - float(means[index])) / (float(stds[index]) or 1.0))
    logits = []
    for c in range(len(classes)):
        logits.append(float(biases[c]) + sum(float(weights[c][j]) * x[j] for j in range(len(x))))
    probs = softmax(logits)
    if not classes:
        return G56_STATIC_CANDIDATE, 0.0
    best = max(range(len(classes)), key=lambda index: probs[index])
    return str(classes[best]), probs[best]


def score_candidate(scores: dict[str, float], candidate: str, fallback: float = math.inf) -> float:
    score = scores.get(candidate, fallback)
    return score if math.isfinite(score) else fallback


def mean(values: list[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return sum(finite) / len(finite) if finite else math.inf


def calibration_bin(confidence: float) -> str:
    if confidence < 0.5:
        return "lt_0p50"
    if confidence < 0.75:
        return "0p50_0p75"
    return "ge_0p75"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    model = load_json(resolve(args.model_json, root))
    if not model:
        write_csv_rows(
            resolve(args.eval_csv, root),
            [],
            fields=[
                "context_id",
                "normalized_context_key",
                "split",
                "label_class",
                "target_candidate_id",
                "predicted_candidate_id",
                "selected_candidate_id",
                "confidence",
                "selected_score",
                "static_score",
                "additive_score",
                "oracle_score",
                "random_control_candidate_id",
                "shuffled_control_candidate_id",
                "majority_candidate_id",
            ],
        )
        summary = {
            "schema_version": "phase5p5_repair5g57_offline_safe_mixture_summary_v1",
            "offline_eval_run": False,
            "offline_training_run": False,
            "decision": "blocked_no_trained_model",
            "eval_csv": str(resolve(args.eval_csv, root)),
            "phase5p5_allowed": False,
            "phase6_allowed": False,
            "aaai_ready": False,
            "runtime_claim_allowed": False,
        }
        write_json(resolve(args.summary_json, root), summary)
        write_text(resolve(args.report, root), "# Phase5.5 Repair5G.5.7 Offline Safe Mixture Eval\n\nNo trained model found; evaluation skipped.\n")
        print(json.dumps({"decision": summary["decision"], "offline_eval_run": False}))
        return 0

    random.seed(int(args.seed))
    features = [row for row in read_csv_rows(resolve(args.feature_matrix_csv, root)) if is_true(row.get("training_eligible"))]
    labels = read_csv_rows(resolve(args.labels_csv, root))
    scores_by_context = labels_scores_by_context_candidate(labels)
    classes = list(model.get("classes", []))
    eval_rows = []
    selected_scores = []
    static_scores = []
    additive_scores = []
    oracle_scores = []
    random_scores = []
    shuffled_scores = []
    majority_scores = []
    harmful = 0
    abstentions = 0
    nonstatic = 0
    calibration: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    class_counts: dict[str, int] = defaultdict(int)
    for row in features:
        class_counts[str(row.get("target_candidate_id", ""))] += 1
    majority = max(class_counts, key=class_counts.get, default=G56_STATIC_CANDIDATE)
    dev_rows = [row for row in features if int(float(row.get("seed") or 0)) > 155]
    for index, row in enumerate(dev_rows):
        context_id = str(row.get("context_id", ""))
        scores = scores_by_context.get(context_id, {})
        static_score = score_candidate(scores, G56_STATIC_CANDIDATE)
        additive_score = score_candidate(scores, G56_ADDITIVE_CANDIDATE, static_score)
        target = str(row.get("target_candidate_id", ""))
        oracle_score = score_candidate(scores, target, static_score)
        pred, confidence = predict(model, row)
        selected = pred if confidence >= float(model.get("abstention_threshold", 0.5)) else G56_STATIC_CANDIDATE
        if selected == G56_STATIC_CANDIDATE and pred != G56_STATIC_CANDIDATE:
            abstentions += 1
        if selected != G56_STATIC_CANDIDATE:
            nonstatic += 1
        selected_score = score_candidate(scores, selected, static_score)
        if math.isfinite(selected_score) and math.isfinite(static_score) and selected_score > static_score + float(args.harmful_margin):
            harmful += 1
        random_candidate = random.choice(classes) if classes else G56_STATIC_CANDIDATE
        shuffled_candidate = classes[(index + 1) % len(classes)] if classes else G56_STATIC_CANDIDATE
        random_score = score_candidate(scores, random_candidate, static_score)
        shuffled_score = score_candidate(scores, shuffled_candidate, static_score)
        majority_score = score_candidate(scores, majority, static_score)
        selected_scores.append(selected_score)
        static_scores.append(static_score)
        additive_scores.append(additive_score)
        oracle_scores.append(oracle_score)
        random_scores.append(random_score)
        shuffled_scores.append(shuffled_score)
        majority_scores.append(majority_score)
        bin_name = calibration_bin(confidence)
        calibration[bin_name][0] += int(selected == target)
        calibration[bin_name][1] += 1
        eval_rows.append(
            {
                "context_id": context_id,
                "normalized_context_key": row.get("normalized_context_key", ""),
                "split": "dev",
                "label_class": row.get("label_class", ""),
                "target_candidate_id": target,
                "predicted_candidate_id": pred,
                "selected_candidate_id": selected,
                "confidence": confidence,
                "selected_score": selected_score if math.isfinite(selected_score) else "",
                "static_score": static_score if math.isfinite(static_score) else "",
                "additive_score": additive_score if math.isfinite(additive_score) else "",
                "oracle_score": oracle_score if math.isfinite(oracle_score) else "",
                "random_control_candidate_id": random_candidate,
                "shuffled_control_candidate_id": shuffled_candidate,
                "majority_candidate_id": majority,
            }
        )
    write_csv_rows(resolve(args.eval_csv, root), eval_rows)
    mean_selected = mean(selected_scores)
    mean_static = mean(static_scores)
    mean_additive = mean(additive_scores)
    mean_oracle = mean(oracle_scores)
    mean_random = mean(random_scores)
    mean_shuffled = mean(shuffled_scores)
    mean_majority = mean(majority_scores)
    mean_delta_vs_static = mean_selected - mean_static if math.isfinite(mean_selected) and math.isfinite(mean_static) else math.inf
    mean_delta_vs_additive = mean_selected - mean_additive if math.isfinite(mean_selected) and math.isfinite(mean_additive) else math.inf
    oracle_regret = mean_selected - mean_oracle if math.isfinite(mean_selected) and math.isfinite(mean_oracle) else math.inf
    harmful_rate = harmful / len(eval_rows) if eval_rows else None
    abstention_rate = abstentions / len(eval_rows) if eval_rows else None
    nonstatic_rate = nonstatic / len(eval_rows) if eval_rows else None
    calibration_summary = {
        key: {"accuracy": wins / total if total else None, "count": total}
        for key, (wins, total) in sorted(calibration.items())
    }
    observed_dev_only = validate_observed_rows(dev_rows, label="Repair5G.5.7 offline eval dev")
    gates = {
        "offline_eval_rows_gt_0": bool(eval_rows),
        "offline_g6_mean_delta_vs_static_lt_0": math.isfinite(mean_delta_vs_static) and mean_delta_vs_static < 0.0,
        "harmful_vs_static_rate_bounded": harmful_rate is not None and harmful_rate <= float(args.harmful_rate_threshold),
        "beats_random_features": math.isfinite(mean_selected) and math.isfinite(mean_random) and mean_selected < mean_random,
        "beats_shuffled_labels": math.isfinite(mean_selected) and math.isfinite(mean_shuffled) and mean_selected < mean_shuffled,
        "beats_majority_expert": math.isfinite(mean_selected) and math.isfinite(mean_majority) and mean_selected < mean_majority,
        "static_fallback_available": G56_STATIC_CANDIDATE == model.get("default_fallback", G56_STATIC_CANDIDATE),
        "observed_dev_only": observed_dev_only,
        "calibration_reported": bool(calibration_summary),
    }
    gates["offline_g6_safe_mixture_eval_passed"] = all(gates.values())
    summary = {
        "schema_version": "phase5p5_repair5g57_offline_safe_mixture_summary_v1",
        "offline_eval_run": True,
        "offline_training_run": True,
        "eval_rows": len(eval_rows),
        "mean_selected_score": None if not math.isfinite(mean_selected) else mean_selected,
        "mean_static_score": None if not math.isfinite(mean_static) else mean_static,
        "mean_additive_score": None if not math.isfinite(mean_additive) else mean_additive,
        "mean_oracle_score": None if not math.isfinite(mean_oracle) else mean_oracle,
        "mean_delta_vs_static": None if not math.isfinite(mean_delta_vs_static) else mean_delta_vs_static,
        "mean_delta_vs_additive": None if not math.isfinite(mean_delta_vs_additive) else mean_delta_vs_additive,
        "oracle_regret": None if not math.isfinite(oracle_regret) else oracle_regret,
        "harmful_vs_static_rate": harmful_rate,
        "abstention_rate": abstention_rate,
        "nonstatic_selection_rate": nonstatic_rate,
        "mean_random_control_score": None if not math.isfinite(mean_random) else mean_random,
        "mean_shuffled_control_score": None if not math.isfinite(mean_shuffled) else mean_shuffled,
        "mean_majority_score": None if not math.isfinite(mean_majority) else mean_majority,
        "calibration_bins": calibration_summary,
        "eval_csv": str(resolve(args.eval_csv, root)),
        "gates": gates,
        "decision": "offline_g6_safe_mixture_passed_continue_runtime_preflight_design"
        if gates["offline_g6_safe_mixture_eval_passed"]
        else "offline_g6_safe_mixture_failed_continue_label_confidence_or_candidate_space",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "runtime_claim_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.7 Offline Safe Mixture Eval\n\n"
        f"- eval_rows: `{len(eval_rows)}`\n"
        f"- mean_delta_vs_static: `{summary['mean_delta_vs_static']}`\n"
        f"- mean_delta_vs_additive: `{summary['mean_delta_vs_additive']}`\n"
        f"- oracle_regret: `{summary['oracle_regret']}`\n"
        f"- harmful_vs_static_rate: `{summary['harmful_vs_static_rate']}`\n"
        f"- abstention_rate: `{summary['abstention_rate']}`\n"
        f"- nonstatic_selection_rate: `{summary['nonstatic_selection_rate']}`\n"
        f"- beats_random_features: `{gates['beats_random_features']}`\n"
        f"- beats_shuffled_labels: `{gates['beats_shuffled_labels']}`\n"
        f"- decision: `{summary['decision']}`\n\n"
        "This remains observed-ID offline diagnostic evidence only; runtime claims and fresh IDs remain closed.\n",
    )
    print(json.dumps({"decision": summary["decision"], "eval_rows": len(eval_rows)}))
    return 0 if gates["offline_eval_rows_gt_0"] and observed_dev_only else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

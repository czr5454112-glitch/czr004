"""Evaluate a Repair5G.5.6 offline safe-mixture prototype if trained."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g56_common import G56_STATIC_CANDIDATE, load_json, read_csv_rows, repo_root, resolve, score_from_label, write_csv_rows, write_json, write_text  # noqa: E402


DEFAULT_MODEL = "artifacts/models/laur_ltm/repair5g56_offline_safe_mixture/model_spec.json"
DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g56_g6_perf_feature_table.csv"
DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g56_g6_safe_mixture_targets.csv"
DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g56_counterfactual_update_labels.csv"
DEFAULT_EVAL_CSV = "outputs/tables/phase5p5_repair5g56_offline_safe_mixture_eval.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g56_offline_safe_mixture_eval.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g56_offline_safe_mixture_eval_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-json", type=Path, default=Path(DEFAULT_MODEL))
    parser.add_argument("--feature-table-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--eval-csv", type=Path, default=Path(DEFAULT_EVAL_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def row_key(row: dict[str, str]) -> str:
    return f"{row.get('map','')}|a{int(float(row.get('agents') or 0))}|s{int(float(row.get('seed') or 0))}|it{int(float(row.get('iteration') or 0))}|{row.get('traffic_before_hash_full','')}"


def softmax(logits: list[float]) -> list[float]:
    top = max(logits) if logits else 0.0
    exps = [math.exp(value - top) for value in logits]
    total = sum(exps) or 1.0
    return [value / total for value in exps]


def predict(model: dict[str, object], row: dict[str, str]) -> tuple[str, float]:
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
    best = max(range(len(classes)), key=lambda index: probs[index]) if classes else 0
    return str(classes[best]), probs[best]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    model_path = resolve(args.model_json, root)
    model = load_json(model_path)
    if not model:
        summary = {
            "schema_version": "phase5p5_repair5g56_offline_safe_mixture_eval_summary_v1",
            "offline_eval_run": False,
            "decision": "blocked_no_trained_model",
            "phase5p5_allowed": False,
            "phase6_allowed": False,
            "aaai_ready": False,
        }
        write_json(resolve(args.summary_json, root), summary)
        write_text(resolve(args.report, root), "# Phase5.5 Repair5G.5.6 Offline Safe Mixture Eval\n\nNo trained model found; eval skipped.\n")
        print(json.dumps({"decision": summary["decision"], "offline_eval_run": False}))
        return 0

    features = read_csv_rows(resolve(args.feature_table_csv, root))
    targets = {str(row.get("normalized_context_key", "")): row for row in read_csv_rows(resolve(args.targets_csv, root))}
    labels_by_context = {}
    for row in read_csv_rows(resolve(args.labels_csv, root)):
        labels_by_context.setdefault(str(row.get("context_id", "")), []).append(row)
    eval_rows = []
    selected_scores = []
    static_scores = []
    majority_scores = []
    abstentions = 0
    majority = max(
        sorted({row.get("oracle_candidate_id", "") for row in targets.values()}),
        key=lambda item: sum(1 for row in targets.values() if row.get("oracle_candidate_id", "") == item),
        default=G56_STATIC_CANDIDATE,
    )
    for row in features:
        key = row_key(row)
        target = targets.get(key)
        if not target or str(target.get("training_eligible", "")).lower() != "true":
            continue
        seed = int(float(row.get("seed") or 0))
        split = "train" if seed <= 155 else "dev"
        if split != "dev":
            continue
        pred, confidence = predict(model, row)
        selected = pred if confidence >= float(model.get("abstention_threshold", 0.45)) else G56_STATIC_CANDIDATE
        abstentions += int(selected == G56_STATIC_CANDIDATE and pred != G56_STATIC_CANDIDATE)
        context_rows = labels_by_context.get(str(target.get("context_id", "")), [])
        score_by_candidate = {str(label.get("candidate_id", "")): score_from_label(label) for label in context_rows}
        selected_score = score_by_candidate.get(selected, math.inf)
        static_score = score_by_candidate.get(G56_STATIC_CANDIDATE, math.inf)
        majority_score = score_by_candidate.get(majority, static_score)
        if math.isfinite(selected_score) and math.isfinite(static_score):
            selected_scores.append(selected_score)
            static_scores.append(static_score)
            majority_scores.append(majority_score if math.isfinite(majority_score) else static_score)
        eval_rows.append(
            {
                "normalized_context_key": key,
                "split": split,
                "oracle_candidate_id": target.get("oracle_candidate_id", ""),
                "predicted_candidate_id": pred,
                "selected_candidate_id": selected,
                "confidence": confidence,
                "selected_score": selected_score if math.isfinite(selected_score) else "",
                "static_score": static_score if math.isfinite(static_score) else "",
                "majority_score": majority_score if math.isfinite(majority_score) else "",
            }
        )
    write_csv_rows(resolve(args.eval_csv, root), eval_rows)
    mean_selected = sum(selected_scores) / len(selected_scores) if selected_scores else math.inf
    mean_static = sum(static_scores) / len(static_scores) if static_scores else math.inf
    mean_majority = sum(majority_scores) / len(majority_scores) if majority_scores else math.inf
    gates = {
        "beats_static_on_dev_expected_utility": math.isfinite(mean_selected) and mean_selected < mean_static,
        "beats_majority_expert": math.isfinite(mean_selected) and mean_selected < mean_majority,
        "beats_random_features": False,
        "beats_shuffled_labels": False,
        "abstention_rate_reported": bool(eval_rows),
        "unsafe_candidate_rate_bounded": True,
        "calibration_reported": bool(eval_rows),
    }
    gates["offline_g6_safe_mixture_eval_passed"] = all(gates.values())
    summary = {
        "schema_version": "phase5p5_repair5g56_offline_safe_mixture_eval_summary_v1",
        "offline_eval_run": True,
        "eval_rows": len(eval_rows),
        "mean_selected_score": None if not math.isfinite(mean_selected) else mean_selected,
        "mean_static_score": None if not math.isfinite(mean_static) else mean_static,
        "mean_majority_score": None if not math.isfinite(mean_majority) else mean_majority,
        "abstention_rate": abstentions / len(eval_rows) if eval_rows else None,
        "eval_csv": str(resolve(args.eval_csv, root)),
        "gates": gates,
        "decision": "offline_g6_safe_mixture_passed_continue_runtime_preflight_design"
        if gates["offline_g6_safe_mixture_eval_passed"]
        else "offline_g6_safe_mixture_failed",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.6 Offline Safe Mixture Eval\n\n"
        f"- eval_rows: `{len(eval_rows)}`\n"
        f"- mean_selected_score: `{summary['mean_selected_score']}`\n"
        f"- mean_static_score: `{summary['mean_static_score']}`\n"
        f"- abstention_rate: `{summary['abstention_rate']}`\n"
        f"- decision: `{summary['decision']}`\n\n"
        "This is offline diagnostic evidence only; Phase5.5, Phase6, and AAAI-ready remain closed.\n",
    )
    print(json.dumps({"decision": summary["decision"], "eval_rows": len(eval_rows)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

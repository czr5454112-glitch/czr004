"""Train an optional Repair5G.5.6 offline safe-mixture prototype if gates pass."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g56_common import load_json, read_csv_rows, repo_root, resolve, validate_observed_rows, write_json, write_text  # noqa: E402


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g56_g6_perf_feature_table.csv"
DEFAULT_SCHEMA = "outputs/reports/phase5p5_repair5g56_g6_feature_schema.json"
DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g56_g6_safe_mixture_targets.csv"
DEFAULT_MODEL_DIR = "artifacts/models/laur_ltm/repair5g56_offline_safe_mixture"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g56_offline_safe_mixture_train.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g56_offline_safe_mixture_summary.json"

DEFAULT_GATE_SUMMARIES = [
    "outputs/reports/phase5p5_repair5g56_counterfactual_label_completion_summary.json",
    "outputs/reports/phase5p5_repair5g56_warehouse_probe_failure_summary.json",
    "outputs/reports/phase5p5_repair5g56_probe_budget_stability_summary.json",
    "outputs/reports/phase5p5_repair5g56_perf_feature_allowlist_summary.json",
    "outputs/reports/phase5p5_repair5g56_g6_target_construction_summary.json",
]

REQUIRED_GATE_KEYS = [
    "counterfactual_label_completion_passed",
    "warehouse_probe_failure_analysis_passed",
    "probe_budget_stability_expanded_passed",
    "perf_feature_allowlist_passed",
    "g6_targets_ready",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-table-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--schema-json", type=Path, default=Path(DEFAULT_SCHEMA))
    parser.add_argument("--targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--gate-summary-json", nargs="+", type=Path, default=[Path(path) for path in DEFAULT_GATE_SUMMARIES])
    parser.add_argument("--model-dir", type=Path, default=Path(DEFAULT_MODEL_DIR))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=20260604)
    return parser.parse_args(argv)


def gate_status(paths: list[Path]) -> tuple[bool, dict[str, object]]:
    observed = {}
    for path in paths:
        summary = load_json(path)
        gates = summary.get("gates", {})
        for key in REQUIRED_GATE_KEYS:
            if key in gates:
                observed[key] = bool(gates.get(key))
    return all(observed.get(key, False) for key in REQUIRED_GATE_KEYS), observed


def row_key(row: dict[str, str]) -> str:
    return f"{row.get('map','')}|a{int(float(row.get('agents') or 0))}|s{int(float(row.get('seed') or 0))}|it{int(float(row.get('iteration') or 0))}|{row.get('traffic_before_hash_full','')}"


def softmax(logits: list[float]) -> list[float]:
    top = max(logits) if logits else 0.0
    exps = [math.exp(value - top) for value in logits]
    total = sum(exps) or 1.0
    return [value / total for value in exps]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    gate_paths = [resolve(path, root) for path in args.gate_summary_json]
    gates_passed, observed_gates = gate_status(gate_paths)
    model_dir = resolve(args.model_dir, root)
    model_dir.mkdir(parents=True, exist_ok=True)
    if not gates_passed:
        summary = {
            "schema_version": "phase5p5_repair5g56_offline_safe_mixture_summary_v1",
            "offline_training_run": False,
            "decision": "blocked_gates_failed_do_not_train",
            "observed_gates": observed_gates,
            "model_dir": str(model_dir),
            "phase5p5_allowed": False,
            "phase6_allowed": False,
            "aaai_ready": False,
        }
        write_json(resolve(args.summary_json, root), summary)
        write_text(
            resolve(args.report, root),
            "# Phase5.5 Repair5G.5.6 Offline Safe Mixture Train\n\n"
            f"- offline_training_run: `False`\n"
            f"- decision: `{summary['decision']}`\n"
            f"- observed_gates: `{json.dumps(observed_gates, sort_keys=True)}`\n\n"
            "P1-P5 gates did not all pass, so the optional G6 prototype was not trained.\n",
        )
        print(json.dumps({"decision": summary["decision"], "offline_training_run": False}))
        return 0

    features = read_csv_rows(resolve(args.feature_table_csv, root))
    targets = [row for row in read_csv_rows(resolve(args.targets_csv, root)) if str(row.get("training_eligible", "")).lower() == "true"]
    schema = load_json(resolve(args.schema_json, root))
    feature_names = list(schema.get("feature_sets", {}).get("perf_safe_only", []))
    target_by_key = {str(row.get("normalized_context_key", "")): row for row in targets}
    train_rows = []
    for row in features:
        key = row_key(row)
        target = target_by_key.get(key)
        if target:
            seed = int(float(row.get("seed") or 0))
            train_rows.append((row, target, "train" if seed <= 155 else "dev"))
    classes = sorted({target.get("oracle_candidate_id", "") for _row, target, _split in train_rows if target.get("oracle_candidate_id")})
    if not train_rows or len(classes) < 2 or not validate_observed_rows([row for row, _target, _split in train_rows], label="Repair5G.5.6 offline train"):
        summary = {
            "schema_version": "phase5p5_repair5g56_offline_safe_mixture_summary_v1",
            "offline_training_run": False,
            "decision": "insufficient_training_rows_or_classes",
            "training_rows": len(train_rows),
            "classes": classes,
            "phase5p5_allowed": False,
            "phase6_allowed": False,
            "aaai_ready": False,
        }
        write_json(resolve(args.summary_json, root), summary)
        write_text(resolve(args.report, root), "# Phase5.5 Repair5G.5.6 Offline Safe Mixture Train\n\nInsufficient eligible rows/classes; no model trained.\n")
        print(json.dumps({"decision": summary["decision"], "offline_training_run": False}))
        return 0

    random.seed(int(args.seed))
    xs = [[float(row.get(name) or 0.0) for name in feature_names] for row, _target, _split in train_rows]
    means = [sum(col) / len(col) for col in zip(*xs)] if feature_names else []
    stds = []
    for index, mean in enumerate(means):
        var = sum((x[index] - mean) ** 2 for x in xs) / max(1, len(xs))
        stds.append(math.sqrt(var) or 1.0)

    class_index = {name: index for index, name in enumerate(classes)}
    weights = [[0.0 for _ in feature_names] for _ in classes]
    biases = [0.0 for _ in classes]
    train_only = [(row, target) for row, target, split in train_rows if split == "train"] or [(row, target) for row, target, _split in train_rows]
    lr = float(args.learning_rate)
    for _epoch in range(int(args.epochs)):
        random.shuffle(train_only)
        for row, target in train_only:
            x = [
                ((float(row.get(name) or 0.0) - means[index]) / stds[index])
                for index, name in enumerate(feature_names)
            ]
            logits = [biases[c] + sum(weights[c][j] * x[j] for j in range(len(x))) for c in range(len(classes))]
            probs = softmax(logits)
            gold = class_index[str(target.get("oracle_candidate_id", ""))]
            for c in range(len(classes)):
                grad = probs[c] - (1.0 if c == gold else 0.0)
                biases[c] -= lr * grad
                for j in range(len(x)):
                    weights[c][j] -= lr * grad * x[j]

    model = {
        "schema_version": "phase5p5_repair5g56_offline_safe_mixture_model_v1",
        "model_type": "calibrated_multinomial_logistic_regression_sgd",
        "feature_set": "perf_safe_only",
        "feature_names": feature_names,
        "classes": classes,
        "means": means,
        "stds": stds,
        "weights": weights,
        "biases": biases,
        "default_fallback": "repair5g2_best_frozen_static_candidate",
        "abstention_threshold": 0.45,
    }
    model_path = model_dir / "model_spec.json"
    write_json(model_path, model)
    summary = {
        "schema_version": "phase5p5_repair5g56_offline_safe_mixture_summary_v1",
        "offline_training_run": True,
        "decision": "offline_model_trained_requires_eval",
        "training_rows": len(train_rows),
        "train_rows": len(train_only),
        "classes": classes,
        "model_path": str(model_path),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.6 Offline Safe Mixture Train\n\n"
        f"- offline_training_run: `True`\n"
        f"- model_type: `{model['model_type']}`\n"
        f"- training_rows: `{len(train_rows)}`\n"
        f"- classes: `{json.dumps(classes)}`\n\n"
        "This remains offline diagnostic training only; runtime promotion is still closed.\n",
    )
    print(json.dumps({"decision": summary["decision"], "training_rows": len(train_rows)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

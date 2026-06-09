"""Train optional Repair5G.5.8 offline safe-mixture model if gates pass."""

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

from repair5g58_common import (  # noqa: E402
    G56_STATIC_CANDIDATE,
    is_true,
    load_json,
    read_csv_rows,
    repo_root,
    resolve,
    validate_observed_rows,
    write_json,
    write_text,
)


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g58_g6_features_perf_safe.csv"
DEFAULT_MODEL_DIR = "artifacts/models/laur_ltm/repair5g58_offline_safe_mixture"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g58_offline_safe_mixture_train.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g58_offline_safe_mixture_train_summary.json"
DEFAULT_GATE_SUMMARIES = [
    "outputs/reports/phase5p5_repair5g58_primary_pair_confidence_expansion_summary.json",
    "outputs/reports/phase5p5_repair5g58_confidence_weighted_targets_summary.json",
    "outputs/reports/phase5p5_repair5g58_warehouse_abstention_policy_summary.json",
    "outputs/reports/phase5p5_repair5g58_g6_feature_matrix_summary.json",
]
REQUIRED_GATE_KEYS = [
    "primary_pair_confidence_expansion_passed",
    "confidence_training_gate_passed",
    "warehouse_abstention_policy_passed",
    "perf_safe_feature_matrix_passed",
]
METADATA_AND_TARGET = {
    "context_id",
    "normalized_context_key",
    "map",
    "agents",
    "seed",
    "iteration",
    "traffic_before_hash_full",
    "margin_threshold",
    "label_class",
    "target_candidate_id",
    "training_eligible",
    "train_weight",
    "stable_static_or_abstain",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-matrix-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--gate-summary-json", nargs="+", type=Path, default=[Path(path) for path in DEFAULT_GATE_SUMMARIES])
    parser.add_argument("--model-dir", type=Path, default=Path(DEFAULT_MODEL_DIR))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--epochs", type=int, default=160)
    parser.add_argument("--learning-rate", type=float, default=0.035)
    parser.add_argument("--seed", type=int, default=20260607)
    return parser.parse_args(argv)


def gate_status(paths: list[Path]) -> tuple[bool, dict[str, bool]]:
    observed: dict[str, bool] = {}
    for path in paths:
        summary = load_json(path)
        gates = summary.get("gates", {})
        for key in REQUIRED_GATE_KEYS:
            if key in gates:
                observed[key] = bool(gates.get(key))
    return all(observed.get(key, False) for key in REQUIRED_GATE_KEYS), observed


def feature_names_from_rows(rows: list[dict[str, str]]) -> list[str]:
    return sorted({key for row in rows for key in row if key not in METADATA_AND_TARGET})


def row_split(row: dict[str, str]) -> str:
    seed = int(float(row.get("seed") or 0))
    return "train" if seed <= 150 else "dev"


def softmax(logits: list[float]) -> list[float]:
    top = max(logits) if logits else 0.0
    exps = [math.exp(value - top) for value in logits]
    total = sum(exps) or 1.0
    return [value / total for value in exps]


def write_blocked(root: Path, args: argparse.Namespace, model_dir: Path, decision: str, observed_gates: dict[str, bool], extra: dict[str, object] | None = None) -> int:
    summary = {
        "schema_version": "phase5p5_repair5g58_offline_safe_mixture_train_summary_v1",
        "offline_training_run": False,
        "decision": decision,
        "observed_gates": observed_gates,
        "model_dir": str(model_dir),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "runtime_claim_allowed": False,
    }
    if extra:
        summary.update(extra)
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.8 Offline Safe Mixture Train\n\n"
        f"- offline_training_run: `False`\n"
        f"- decision: `{decision}`\n"
        f"- observed_gates: `{json.dumps(observed_gates, sort_keys=True)}`\n\n"
        "The optional offline G6 model was not trained because the gate package is not training-ready.\n",
    )
    print(json.dumps({"decision": decision, "offline_training_run": False}))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    gate_paths = [resolve(path, root) for path in args.gate_summary_json]
    gates_passed, observed_gates = gate_status(gate_paths)
    model_dir = resolve(args.model_dir, root)
    model_dir.mkdir(parents=True, exist_ok=True)
    if not gates_passed:
        return write_blocked(root, args, model_dir, "blocked_gates_failed_do_not_train", observed_gates)

    rows = [row for row in read_csv_rows(resolve(args.feature_matrix_csv, root)) if is_true(row.get("training_eligible"))]
    observed_ok = validate_observed_rows(rows, label="Repair5G.5.8 offline train")
    feature_names = feature_names_from_rows(rows)
    classes = sorted({str(row.get("target_candidate_id", "")) for row in rows if row.get("target_candidate_id")})
    train_rows = [row for row in rows if row_split(row) == "train"]
    dev_rows = [row for row in rows if row_split(row) == "dev"]
    if not rows or len(classes) < 2 or not feature_names or not observed_ok or not train_rows or not dev_rows:
        return write_blocked(
            root,
            args,
            model_dir,
            "insufficient_training_rows_features_classes_or_split",
            observed_gates,
            {
                "training_rows": len(rows),
                "train_rows": len(train_rows),
                "dev_rows": len(dev_rows),
                "feature_count": len(feature_names),
                "classes": classes,
                "observed_ids_only": observed_ok,
            },
        )

    random.seed(int(args.seed))
    xs = [[float(row.get(name) or 0.0) for name in feature_names] for row in rows]
    means = [sum(col) / len(col) for col in zip(*xs)]
    stds = []
    for index, mean in enumerate(means):
        var = sum((x[index] - mean) ** 2 for x in xs) / max(1, len(xs))
        stds.append(math.sqrt(var) or 1.0)
    class_index = {name: index for index, name in enumerate(classes)}
    weights = [[0.0 for _name in feature_names] for _class in classes]
    biases = [0.0 for _class in classes]
    lr = float(args.learning_rate)
    for _epoch in range(int(args.epochs)):
        random.shuffle(train_rows)
        for row in train_rows:
            x = [
                ((float(row.get(name) or 0.0) - means[index]) / stds[index])
                for index, name in enumerate(feature_names)
            ]
            logits = [biases[c] + sum(weights[c][j] * x[j] for j in range(len(x))) for c in range(len(classes))]
            probs = softmax(logits)
            gold = class_index[str(row.get("target_candidate_id", ""))]
            row_weight = float(row.get("train_weight") or 1.0)
            for c in range(len(classes)):
                grad = (probs[c] - (1.0 if c == gold else 0.0)) * row_weight
                biases[c] -= lr * grad
                for j in range(len(x)):
                    weights[c][j] -= lr * grad * x[j]

    model = {
        "schema_version": "phase5p5_repair5g58_offline_safe_mixture_model_v1",
        "model_type": "calibrated_multinomial_logistic_regression_sgd",
        "feature_set": "perf_safe_only",
        "feature_names": feature_names,
        "classes": classes,
        "means": means,
        "stds": stds,
        "weights": weights,
        "biases": biases,
        "default_fallback": G56_STATIC_CANDIDATE,
        "abstention_threshold": 0.50,
        "training_seed": int(args.seed),
        "split_policy": "train_seed_le_150_dev_seed_gt_150_observed_only",
    }
    model_path = model_dir / "model_spec.json"
    write_json(model_path, model)
    summary = {
        "schema_version": "phase5p5_repair5g58_offline_safe_mixture_train_summary_v1",
        "offline_training_run": True,
        "decision": "offline_model_trained_requires_eval",
        "training_rows": len(rows),
        "train_rows": len(train_rows),
        "dev_rows": len(dev_rows),
        "feature_count": len(feature_names),
        "classes": classes,
        "model_path": str(model_path),
        "observed_gates": observed_gates,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "runtime_claim_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.8 Offline Safe Mixture Train\n\n"
        f"- offline_training_run: `True`\n"
        f"- model_type: `{model['model_type']}`\n"
        f"- training_rows: `{len(rows)}`\n"
        f"- train_rows: `{len(train_rows)}`\n"
        f"- dev_rows: `{len(dev_rows)}`\n"
        f"- classes: `{json.dumps(classes)}`\n\n"
        "This is offline observed-ID diagnostic training only; runtime promotion remains closed.\n",
    )
    print(json.dumps({"decision": summary["decision"], "training_rows": len(rows)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

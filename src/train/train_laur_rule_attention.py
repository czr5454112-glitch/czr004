"""Train Phase4F Repair2 rule-conditioned LAU-LTM attention models."""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.token_dataset_laur import (  # noqa: E402
    read_jsonl,
    validate_token_update_dataset_row,
)
from czr004_teacher.token_features_laur import (  # noqa: E402
    EDGE_FEATURE_NAMES,
    EXECUTABLE_RULE_IDS,
    RULE_FAMILY_IDS,
    RULE_FEATURE_NAMES,
    TOKEN_DATASET_SCHEMA_VERSION,
    TRACE_FEATURE_NAMES,
)
from models.laur_rule_attention import (  # noqa: E402
    EDGE_TRACE_MODEL_NAME,
    MODEL_SCHEMA_VERSION,
    SET_MODEL_NAME,
    LAURuleAttentionModel,
)
from train.losses_laur_rule_attention import RuleAttentionLossWeights, laur_rule_attention_loss  # noqa: E402

try:
    import torch
except ImportError as exc:  # pragma: no cover - training is run in czr004 env
    raise RuntimeError("PyTorch is required for Phase4F Repair2 training") from exc


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path | None, root: Path) -> Path | None:
    if path is None:
        return None
    value = Path(path)
    return value if value.is_absolute() else root / value


def load_config(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read Phase4 LAUR configs") from exc
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def config_get(config: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = config
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def validate_rows(rows: list[dict[str, Any]]) -> None:
    errors: list[str] = []
    for index, row in enumerate(rows, 1):
        errors.extend(f"row {index}: {error}" for error in validate_token_update_dataset_row(row))
    if not rows:
        errors.append("dataset is empty")
    if errors:
        raise ValueError("Repair2 token dataset schema errors:\n" + "\n".join(errors[:30]))


def split_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["split"])].append(row)
    if "train" not in grouped:
        grouped["train"] = list(rows)
    if "validation" not in grouped:
        grouped["validation"] = list(rows)
    return dict(grouped)


def _stats_from_vectors(vectors: list[list[float]], dim: int) -> dict[str, list[float]]:
    if not vectors:
        return {"mean": [0.0] * dim, "std": [1.0] * dim}
    mean = [sum(row[col] for row in vectors) / len(vectors) for col in range(dim)]
    std: list[float] = []
    for col in range(dim):
        variance = sum((row[col] - mean[col]) ** 2 for row in vectors) / len(vectors)
        value = math.sqrt(max(variance, 0.0))
        std.append(value if value > 1e-12 else 1.0)
    return {"mean": mean, "std": std}


def feature_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    global_vectors = [[float(value) for value in row["global_features"]] for row in rows]
    edge_vectors = [[float(value) for value in token] for row in rows for token in row["edge_tokens"]]
    trace_vectors = [[float(value) for value in token] for row in rows for token in row["trace_tokens"]]
    rule_vectors = [[float(value) for value in token] for token in rows[0]["rule_tokens"]]
    return {
        "global": _stats_from_vectors(global_vectors, len(rows[0]["global_features"])),
        "edge": _stats_from_vectors(edge_vectors, len(EDGE_FEATURE_NAMES)),
        "trace": _stats_from_vectors(trace_vectors, len(TRACE_FEATURE_NAMES)),
        "rule": _stats_from_vectors(rule_vectors, len(RULE_FEATURE_NAMES)),
    }


def standardize(values: list[float], stats: dict[str, list[float]]) -> list[float]:
    return [
        (float(value) - float(stats["mean"][index])) / float(stats["std"][index])
        for index, value in enumerate(values)
    ]


def _pad_tokens(
    rows: list[dict[str, Any]],
    key: str,
    feature_count: int,
    stats: dict[str, list[float]],
    *,
    minimum_length: int = 1,
) -> tuple[list[list[list[float]]], list[list[int]]]:
    max_len = max(maximum for maximum in (len(row[key]) for row in rows)) if rows else 0
    max_len = max(int(minimum_length), max_len)
    padded: list[list[list[float]]] = []
    masks: list[list[int]] = []
    zero = [0.0] * feature_count
    for row in rows:
        tokens = [standardize([float(value) for value in token], stats) for token in row[key]]
        mask = [1] * len(tokens)
        while len(tokens) < max_len:
            tokens.append(list(zero))
            mask.append(0)
        padded.append(tokens)
        masks.append(mask)
    return padded, masks


def rows_to_batch(rows: list[dict[str, Any]], stats: dict[str, Any], device: torch.device) -> dict[str, Any]:
    edge_tokens, edge_mask = _pad_tokens(rows, "edge_tokens", len(EDGE_FEATURE_NAMES), stats["edge"])
    trace_tokens, trace_mask = _pad_tokens(rows, "trace_tokens", len(TRACE_FEATURE_NAMES), stats["trace"])
    global_features = [standardize([float(value) for value in row["global_features"]], stats["global"]) for row in rows]
    rule_tokens = [
        [standardize([float(value) for value in token], stats["rule"]) for token in row["rule_tokens"]]
        for row in rows
    ]
    return {
        "global_features": torch.tensor(global_features, dtype=torch.float32, device=device),
        "edge_tokens": torch.tensor(edge_tokens, dtype=torch.float32, device=device),
        "edge_mask": torch.tensor(edge_mask, dtype=torch.bool, device=device),
        "trace_tokens": torch.tensor(trace_tokens, dtype=torch.float32, device=device),
        "trace_mask": torch.tensor(trace_mask, dtype=torch.bool, device=device),
        "rule_tokens": torch.tensor(rule_tokens, dtype=torch.float32, device=device),
        "rule_target": torch.tensor(
            [int(row["target"]["best_rule_executable_index"]) for row in rows],
            dtype=torch.long,
            device=device,
        ),
        "family_target": torch.tensor(
            [int(row["target"]["rule_family_index"]) for row in rows],
            dtype=torch.long,
            device=device,
        ),
        "neutral_target": torch.tensor(
            [1.0 if row["target"]["is_neutral_label"] else 0.0 for row in rows],
            dtype=torch.float32,
            device=device,
        ),
        "soft_rule_target": torch.tensor(
            [[float(value) for value in row["soft_rule_target"]] for row in rows],
            dtype=torch.float32,
            device=device,
        ),
        "delta_target": torch.tensor(
            [[float(value) for value in row["rule_delta_vector"]] for row in rows],
            dtype=torch.float32,
            device=device,
        ),
        "harmful_target": torch.tensor(
            [[1.0 if value else 0.0 for value in row["rule_harmful_vector"]] for row in rows],
            dtype=torch.float32,
            device=device,
        ),
    }


def topk_indices(values: list[float], k: int) -> list[int]:
    return sorted(range(len(values)), key=lambda index: values[index], reverse=True)[:k]


def binary_metrics(labels: list[int], predictions: list[int]) -> dict[str, float]:
    tp = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 1)
    fp = sum(1 for label, pred in zip(labels, predictions) if label == 0 and pred == 1)
    fn = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 0)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def binary_auroc(labels: list[int], scores: list[float]) -> float | None:
    positives = [score for label, score in zip(labels, scores) if label == 1]
    negatives = [score for label, score in zip(labels, scores) if label == 0]
    if not positives or not negatives:
        return None
    wins = 0.0
    for pos in positives:
        for neg in negatives:
            if pos > neg:
                wins += 1.0
            elif pos == neg:
                wins += 0.5
    return wins / (len(positives) * len(negatives))


def safety_gated_topk(
    scores: list[float],
    harmful_probs: list[float],
    *,
    harmful_threshold: float,
    min_confidence: float,
    k: int,
) -> list[int]:
    additive_index = EXECUTABLE_RULE_IDS.index("additive_ltm")
    allowed = [
        index == additive_index or float(probability) < float(harmful_threshold)
        for index, probability in enumerate(harmful_probs)
    ]
    raw_top = topk_indices(scores, len(scores))
    if min_confidence > 0.0:
        probs = torch.softmax(torch.tensor(scores, dtype=torch.float32), dim=-1).tolist()
        if max(float(value) for value in probs) < float(min_confidence):
            return [additive_index]
    gated = [index for index in raw_top if allowed[index]]
    return gated[:k] if gated else [additive_index]


def evaluate_model(
    model: LAURuleAttentionModel,
    rows: list[dict[str, Any]],
    *,
    stats: dict[str, Any],
    device: torch.device,
    harmful_threshold: float,
    min_confidence: float = 0.0,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not rows:
        return {"sample_count": 0}, []
    model.eval()
    batch = rows_to_batch(rows, stats, device)
    with torch.no_grad():
        outputs = model(batch)
        scores = outputs["rule_score"].detach().cpu().tolist()
        harmful_probs = torch.sigmoid(outputs["harmful_logit"]).detach().cpu().tolist()

    records: list[dict[str, Any]] = []
    for row, row_scores, row_harmful_probs in zip(rows, scores, harmful_probs):
        top3 = safety_gated_topk(
            [float(value) for value in row_scores],
            [float(value) for value in row_harmful_probs],
            harmful_threshold=harmful_threshold,
            min_confidence=min_confidence,
            k=3,
        )
        pred_index = int(top3[0])
        target_index = int(row["target"]["best_rule_executable_index"])
        pred_rule = EXECUTABLE_RULE_IDS[pred_index]
        target_rule = EXECUTABLE_RULE_IDS[target_index]
        original_rule = str(row["target"]["rule_class_original"])
        original_match = pred_rule == original_rule or (
            original_rule == "neutral_additive" and pred_rule == "additive_ltm"
        )
        checkpoint_harmful_probability = max(float(value) for value in row_harmful_probs)
        checkpoint_harmful_label = int(bool(row["target"]["harmful_update"]))
        selected_delta = float(row["rule_delta_vector"][pred_index])
        records.append(
            {
                "split": row["split"],
                "run_id": row["run_id"],
                "checkpoint_id": row["checkpoint_id"],
                "map_name": row["map_name"],
                "agents": row["agents"],
                "seed": row["seed"],
                "iteration": row["iteration"],
                "target_rule_original": original_rule,
                "target_rule_executable": target_rule,
                "predicted_rule": pred_rule,
                "top1_correct": int(pred_index == target_index),
                "top3_correct": int(target_index in top3),
                "raw_original_top1_correct": int(original_match),
                "target_family": row["target"]["rule_family"],
                "predicted_family": row["target"]["rule_family_vocab"][
                    row["target"]["rule_family_vocab"].index(
                        "additive" if pred_rule == "additive_ltm" else pred_rule.split("_")[0]
                    )
                    if ("additive" if pred_rule == "additive_ltm" else pred_rule.split("_")[0])
                    in row["target"]["rule_family_vocab"]
                    else 0
                ],
                "family_top1_correct": int(
                    ("additive" if pred_rule == "additive_ltm" else pred_rule.split("_")[0])
                    == row["target"]["rule_family"]
                ),
                "harmful_update": checkpoint_harmful_label,
                "harmful_update_probability": checkpoint_harmful_probability,
                "harmful_prediction": int(checkpoint_harmful_probability >= float(harmful_threshold)),
                "selected_rule_harmful": int(bool(row["rule_harmful_vector"][pred_index])),
                "predicted_rule_delta_ratio_vs_additive": selected_delta,
                "target_delta_ratio_vs_additive": float(row["rule_delta_vector"][target_index]),
                "neutral": int(bool(row["target"]["is_neutral_label"])),
                "top3_rules": json.dumps([EXECUTABLE_RULE_IDS[index] for index in top3]),
                "predicted_score": float(row_scores[pred_index]),
            }
        )

    top1 = [int(row["top1_correct"]) for row in records]
    top3 = [int(row["top3_correct"]) for row in records]
    raw_top1 = [int(row["raw_original_top1_correct"]) for row in records]
    family_top1 = [int(row["family_top1_correct"]) for row in records]
    non_neutral = [row for row in records if not int(row["neutral"])]
    harmful_labels = [int(row["harmful_update"]) for row in records]
    harmful_preds = [int(row["harmful_prediction"]) for row in records]
    harmful_scores = [float(row["harmful_update_probability"]) for row in records]
    safety = binary_metrics(harmful_labels, harmful_preds)
    metrics = {
        "sample_count": len(records),
        "rule_top1_accuracy": sum(top1) / len(top1),
        "rule_top3_accuracy": sum(top3) / len(top3),
        "executable_rule_top1_accuracy": sum(top1) / len(top1),
        "executable_rule_top3_accuracy": sum(top3) / len(top3),
        "raw_original_top1_accuracy": sum(raw_top1) / len(raw_top1),
        "family_top1_accuracy": sum(family_top1) / len(family_top1),
        "non_neutral_rule_top1_accuracy": (
            sum(int(row["top1_correct"]) for row in non_neutral) / len(non_neutral)
            if non_neutral
            else None
        ),
        "harmful_update_precision": safety["precision"],
        "harmful_update_recall": safety["recall"],
        "harmful_update_f1": safety["f1"],
        "safety_auroc": binary_auroc(harmful_labels, harmful_scores),
        "predicted_rule_validation_mean_delta_ratio": sum(
            float(row["predicted_rule_delta_ratio_vs_additive"]) for row in records
        )
        / len(records),
        "selected_harmful_rule_rate": sum(int(row["selected_rule_harmful"]) for row in records) / len(records),
        "neutral_additive_rate": sum(1 for row in records if row["predicted_rule"] == "additive_ltm") / len(records),
        "label_distribution_original": dict(sorted(Counter(row["target_rule_original"] for row in records).items())),
        "label_distribution_executable": dict(sorted(Counter(row["target_rule_executable"] for row in records).items())),
        "predicted_rule_distribution": dict(sorted(Counter(row["predicted_rule"] for row in records).items())),
    }
    return metrics, records


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "split",
        "run_id",
        "checkpoint_id",
        "map_name",
        "agents",
        "seed",
        "iteration",
        "target_rule_original",
        "target_rule_executable",
        "predicted_rule",
        "top1_correct",
        "top3_correct",
        "raw_original_top1_correct",
        "target_family",
        "predicted_family",
        "family_top1_correct",
        "harmful_update",
        "harmful_update_probability",
        "harmful_prediction",
        "selected_rule_harmful",
        "predicted_rule_delta_ratio_vs_additive",
        "target_delta_ratio_vs_additive",
        "neutral",
        "top3_rules",
        "predicted_score",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in records:
            writer.writerow(row)


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def dirty_state(cwd: Path) -> str:
    tracked = git_value(["status", "--porcelain", "--untracked-files=no"], cwd)
    untracked = git_value(["status", "--porcelain", "--untracked-files=normal"], cwd)
    if tracked:
        return "tracked-dirty"
    if any(line.startswith("??") for line in untracked.splitlines()):
        return "tracked-clean_untracked-present"
    return "clean"


def phase4f_gate(validation: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "validation_top1": {
            "value": validation.get("rule_top1_accuracy"),
            "threshold": 0.35,
            "passed": validation.get("rule_top1_accuracy") is not None
            and float(validation["rule_top1_accuracy"]) >= 0.35,
        },
        "validation_top3": {
            "value": validation.get("rule_top3_accuracy"),
            "threshold": 0.70,
            "passed": validation.get("rule_top3_accuracy") is not None
            and float(validation["rule_top3_accuracy"]) >= 0.70,
        },
        "harmful_recall": {
            "value": validation.get("harmful_update_recall"),
            "threshold": 0.80,
            "passed": validation.get("harmful_update_recall") is not None
            and float(validation["harmful_update_recall"]) >= 0.80,
        },
        "harmful_precision": {
            "value": validation.get("harmful_update_precision"),
            "threshold": 0.30,
            "passed": validation.get("harmful_update_precision") is not None
            and float(validation["harmful_update_precision"]) >= 0.30,
        },
        "predicted_mean_delta": {
            "value": validation.get("predicted_rule_validation_mean_delta_ratio"),
            "threshold": 0.0,
            "passed": validation.get("predicted_rule_validation_mean_delta_ratio") is not None
            and float(validation["predicted_rule_validation_mean_delta_ratio"]) > 0.0,
        },
        "validation_non_neutral": {
            "value": None,
            "threshold": 50,
            "passed": False,
        },
    }
    checks["passed"] = all(bool(value["passed"]) for value in checks.values() if isinstance(value, dict))
    return checks


def write_report(path: Path, *, root: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    train = summary["metrics_by_split"].get("train", {})
    validation = summary["metrics_by_split"].get("validation", {})
    test = summary["metrics_by_split"].get("test", {})
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair2 Rule-Attention Train Report\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("## Code State\n\n")
        handle.write(f"- branch: `{git_value(['branch', '--show-current'], root)}`\n")
        handle.write(f"- commit: `{git_value(['rev-parse', '--short', 'HEAD'], root)}`\n")
        handle.write(f"- dirty: `{dirty_state(root)}`\n\n")
        handle.write("## Inputs\n\n")
        handle.write(f"- dataset: `{summary['dataset']}`\n")
        handle.write(f"- model_path: `{summary['model_path']}`\n")
        handle.write(f"- architecture: `{summary['architecture']}`\n")
        handle.write(f"- epochs: `{summary['epochs']}`\n")
        handle.write(f"- harmful_threshold: `{summary['harmful_threshold']}`\n\n")
        handle.write("## Metrics\n\n")
        handle.write("| split | samples | top1 | top3 | family top1 | harmful recall | harmful precision | mean selected delta | additive rate |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for name, metrics in (("train", train), ("validation", validation), ("test", test)):
            if not metrics:
                continue
            handle.write(
                f"| {name} | {metrics.get('sample_count')} | "
                f"{metrics.get('rule_top1_accuracy')} | {metrics.get('rule_top3_accuracy')} | "
                f"{metrics.get('family_top1_accuracy')} | {metrics.get('harmful_update_recall')} | "
                f"{metrics.get('harmful_update_precision')} | "
                f"{metrics.get('predicted_rule_validation_mean_delta_ratio')} | "
                f"{metrics.get('neutral_additive_rate')} |\n"
            )
        handle.write("\n## Phase4F Gate\n\n")
        gate = summary.get("phase4f_gate", {})
        for key, value in gate.items():
            if key == "passed" or not isinstance(value, dict):
                continue
            handle.write(
                f"- {key}: `{value.get('value')}` vs `{value.get('threshold')}` -> "
                f"{'pass' if value.get('passed') else 'fail'}\n"
            )
        handle.write(f"\nOverall: `{'pass' if gate.get('passed') else 'fail'}`\n\n")
        handle.write("## Boundary\n\n")
        handle.write(
            "This is an offline Phase4F repair experiment. It does not integrate a "
            "learned model into the C++ solver runtime and does not change the "
            "Phase4F performance gate.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--summary-csv", type=Path)
    parser.add_argument("--architecture", choices=[EDGE_TRACE_MODEL_NAME, SET_MODEL_NAME])
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--d-model", type=int)
    parser.add_argument("--nhead", type=int)
    parser.add_argument("--num-layers", type=int)
    parser.add_argument("--dropout", type=float)
    parser.add_argument("--learning-rate", type=float)
    parser.add_argument("--weight-decay", type=float)
    parser.add_argument("--harmful-threshold", type=float)
    parser.add_argument("--min-confidence", type=float)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    config_path = resolve_path(args.config, root)
    config = load_config(config_path)
    train_config = config_get(config, "repair2", "training", default={}) or {}

    dataset_path = resolve_path(args.dataset or config_get(config, "repair2", "dataset_jsonl"), root)
    output_dir = resolve_path(args.output_dir or config_get(config, "repair2", "model_output_dir"), root)
    report_path = resolve_path(args.report or config_get(config, "repair2", "train_report_md"), root)
    summary_json_path = resolve_path(args.summary_json or config_get(config, "repair2", "train_summary_json"), root)
    summary_csv_path = resolve_path(args.summary_csv or config_get(config, "repair2", "train_summary_csv"), root)
    if None in (dataset_path, output_dir, report_path, summary_json_path, summary_csv_path):
        raise ValueError("dataset/output/report/summary paths are required")
    assert dataset_path and output_dir and report_path and summary_json_path and summary_csv_path

    rows = read_jsonl(dataset_path)
    validate_rows(rows)
    if rows[0]["schema_version"] != TOKEN_DATASET_SCHEMA_VERSION:
        raise ValueError("expected phase4_laur_update_dataset_v2 rows")
    splits = split_rows(rows)
    train_rows = splits["train"]
    validation_rows = splits["validation"]
    stats = feature_stats(train_rows)

    seed = int(args.seed if args.seed is not None else train_config.get("seed", 71))
    torch.manual_seed(seed)
    if args.device == "auto" or (args.device is None and str(train_config.get("device", "auto")) == "auto"):
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device or train_config.get("device", "cpu"))

    architecture = str(args.architecture or train_config.get("architecture", EDGE_TRACE_MODEL_NAME))
    model = LAURuleAttentionModel(
        global_dim=len(rows[0]["global_features"]),
        edge_dim=len(EDGE_FEATURE_NAMES),
        trace_dim=len(TRACE_FEATURE_NAMES),
        rule_dim=len(RULE_FEATURE_NAMES),
        num_rules=len(EXECUTABLE_RULE_IDS),
        num_families=len(RULE_FAMILY_IDS),
        d_model=int(args.d_model or train_config.get("d_model", 96)),
        nhead=int(args.nhead or train_config.get("nhead", 4)),
        num_layers=int(args.num_layers or train_config.get("num_layers", 2)),
        dropout=float(args.dropout if args.dropout is not None else train_config.get("dropout", 0.1)),
        architecture=architecture,
    ).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(args.learning_rate or train_config.get("learning_rate", 0.002)),
        weight_decay=float(args.weight_decay if args.weight_decay is not None else train_config.get("weight_decay", 0.001)),
    )
    epochs = int(args.epochs or train_config.get("epochs", 300))
    harmful_threshold = float(
        args.harmful_threshold if args.harmful_threshold is not None else train_config.get("harmful_threshold", 0.10)
    )
    min_confidence = float(
        args.min_confidence if args.min_confidence is not None else train_config.get("min_confidence", 0.0)
    )
    loss_weights = RuleAttentionLossWeights(
        listwise_kl=float(train_config.get("listwise_kl", 1.0)),
        pairwise_margin=float(train_config.get("pairwise_margin", 0.35)),
        delta_regression=float(train_config.get("delta_regression", 0.4)),
        harmful_bce=float(train_config.get("harmful_bce", 0.35)),
        family_ce=float(train_config.get("family_ce", 0.1)),
        additive_regularization=float(train_config.get("additive_regularization", 0.02)),
    )
    train_batch = rows_to_batch(train_rows, stats, device)
    best_state = copy.deepcopy(model.state_dict())
    best_score = float("-inf")
    final_loss = 0.0
    additive_index = EXECUTABLE_RULE_IDS.index("additive_ltm")

    for _epoch in range(epochs):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        outputs = model(train_batch)
        losses = laur_rule_attention_loss(outputs, train_batch, additive_index=additive_index, weights=loss_weights)
        losses["total"].backward()
        optimizer.step()
        final_loss = float(losses["total"].detach().cpu())
        if (_epoch + 1) % max(1, epochs // 10) == 0 or _epoch == epochs - 1:
            validation_metrics, _ = evaluate_model(
                model,
                validation_rows,
                stats=stats,
                device=device,
                harmful_threshold=harmful_threshold,
                min_confidence=min_confidence,
            )
            score = (
                float(validation_metrics.get("rule_top1_accuracy") or 0.0)
                + 0.5 * float(validation_metrics.get("rule_top3_accuracy") or 0.0)
                + 0.05 * float(validation_metrics.get("harmful_update_recall") or 0.0)
                + 0.05 * float(validation_metrics.get("harmful_update_precision") or 0.0)
                + 0.1 * max(0.0, float(validation_metrics.get("predicted_rule_validation_mean_delta_ratio") or 0.0))
            )
            if score > best_score:
                best_score = score
                best_state = copy.deepcopy(model.state_dict())

    model.load_state_dict(best_state)
    model.eval()
    metrics_by_split: dict[str, dict[str, Any]] = {}
    all_records: list[dict[str, Any]] = []
    for split_name, split_values in sorted(splits.items()):
        metrics, records = evaluate_model(
            model,
            split_values,
            stats=stats,
            device=device,
            harmful_threshold=harmful_threshold,
            min_confidence=min_confidence,
        )
        metrics_by_split[split_name] = metrics
        all_records.extend(records)

    validation_non_neutral = sum(1 for row in validation_rows if not row["target"]["is_neutral_label"])
    gate = phase4f_gate(metrics_by_split.get("validation", {}))
    gate["validation_non_neutral"]["value"] = validation_non_neutral
    gate["validation_non_neutral"]["passed"] = validation_non_neutral >= 50
    gate["passed"] = all(bool(value["passed"]) for value in gate.values() if isinstance(value, dict))

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "laur_rule_attention_v2.pt"
    checkpoint = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "model_name": architecture,
        "model_state_dict": model.state_dict(),
        "model_args": {
            "global_dim": len(rows[0]["global_features"]),
            "edge_dim": len(EDGE_FEATURE_NAMES),
            "trace_dim": len(TRACE_FEATURE_NAMES),
            "rule_dim": len(RULE_FEATURE_NAMES),
            "num_rules": len(EXECUTABLE_RULE_IDS),
            "num_families": len(RULE_FAMILY_IDS),
            "d_model": int(args.d_model or train_config.get("d_model", 96)),
            "nhead": int(args.nhead or train_config.get("nhead", 4)),
            "num_layers": int(args.num_layers or train_config.get("num_layers", 2)),
            "dropout": float(args.dropout if args.dropout is not None else train_config.get("dropout", 0.1)),
            "architecture": architecture,
        },
        "feature_stats": stats,
        "global_feature_names": list(rows[0]["global_feature_names"]),
        "edge_feature_names": list(EDGE_FEATURE_NAMES),
        "trace_feature_names": list(TRACE_FEATURE_NAMES),
        "rule_feature_names": list(RULE_FEATURE_NAMES),
        "rule_vocab": list(EXECUTABLE_RULE_IDS),
        "rule_family_vocab": list(RULE_FAMILY_IDS),
        "harmful_threshold": harmful_threshold,
        "min_confidence": min_confidence,
    }
    torch.save(checkpoint, model_path)
    write_csv(summary_csv_path, all_records)
    summary = {
        "schema_version": "phase4f_repair2_rule_attention_train_summary_v1",
        "dataset": str(dataset_path),
        "output_dir": str(output_dir),
        "model_path": str(model_path),
        "architecture": architecture,
        "epochs": epochs,
        "seed": seed,
        "device": str(device),
        "final_loss": final_loss,
        "best_selection_score": best_score,
        "harmful_threshold": harmful_threshold,
        "min_confidence": min_confidence,
        "metrics_by_split": metrics_by_split,
        "phase4f_gate": gate,
    }
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report_path, root=root, summary=summary)
    print(json.dumps({"model_path": str(model_path), "summary_json": str(summary_json_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

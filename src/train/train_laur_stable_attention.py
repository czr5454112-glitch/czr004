"""Train Phase4F.4 LAU stable-target attention update-rule models."""

from __future__ import annotations

import argparse
import copy
import csv
import json
import math
import random
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.stable_attention_dataset_laur import (  # noqa: E402
    read_jsonl,
    validate_stable_attention_dataset_row,
)
from czr004_teacher.stable_attention_tokens_laur import (  # noqa: E402
    EDGE_FEATURE_NAMES,
    EDGE_TRACE_TRANSFORMER_NAME,
    EXECUTABLE_RULE_IDS,
    GLOBAL_FEATURE_NAMES,
    RULE_FAMILY_IDS,
    RULE_FEATURE_NAMES,
    SET_RULE_TRANSFORMER_NAME,
    TRACE_FEATURE_NAMES,
    executable_rule_id,
)
from models.laur_stable_attention import (  # noqa: E402
    MODEL_SCHEMA_VERSION,
    build_model,
    parameter_count,
)
from train.losses_laur_stable_attention import (  # noqa: E402
    StableAttentionLossWeights,
    laur_stable_attention_loss,
)

try:
    import torch
except ImportError as exc:  # pragma: no cover - training is run in czr004 env
    raise RuntimeError("PyTorch is required for Phase4F.4 stable-attention training") from exc


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path | None, root: Path, *, seed: int | None = None) -> Path | None:
    if path is None:
        return None
    text = str(path)
    if seed is not None:
        text = text.format(seed=seed)
    value = Path(text)
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


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def dirty_state(root: Path) -> str:
    status = git_value(["status", "--short"], root)
    if not status:
        return "clean"
    tracked = [line for line in status.splitlines() if not line.startswith("??")]
    untracked = [line for line in status.splitlines() if line.startswith("??")]
    if tracked and untracked:
        return "tracked-dirty_untracked-present"
    if tracked:
        return "tracked-dirty"
    return "untracked-present"


def validate_rows(rows: list[dict[str, Any]]) -> None:
    errors: list[str] = []
    for index, row in enumerate(rows, 1):
        errors.extend(f"row {index}: {error}" for error in validate_stable_attention_dataset_row(row))
    if not rows:
        errors.append("dataset is empty")
    if errors:
        raise ValueError("stable-attention dataset schema errors:\n" + "\n".join(errors[:30]))


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
    edge_vectors = [
        [float(value) for value in token]
        for row in rows
        for token, mask in zip(row["edge_tokens"], row["edge_mask"])
        if mask
    ]
    trace_vectors = [
        [float(value) for value in token]
        for row in rows
        for token, mask in zip(row["trace_tokens"], row["trace_mask"])
        if mask
    ]
    rule_vectors = [[float(value) for value in token] for token in rows[0]["rule_tokens"]]
    return {
        "global": _stats_from_vectors(global_vectors, len(GLOBAL_FEATURE_NAMES)),
        "edge": _stats_from_vectors(edge_vectors, len(EDGE_FEATURE_NAMES)),
        "trace": _stats_from_vectors(trace_vectors, len(TRACE_FEATURE_NAMES)),
        "rule": _stats_from_vectors(rule_vectors, len(RULE_FEATURE_NAMES)),
    }


def standardize(values: list[float], stats: dict[str, list[float]]) -> list[float]:
    return [
        (float(value) - float(stats["mean"][index])) / float(stats["std"][index])
        for index, value in enumerate(values)
    ]


def rows_to_batch(rows: list[dict[str, Any]], stats: dict[str, Any], device: torch.device) -> dict[str, Any]:
    return {
        "global_features": torch.tensor(
            [standardize([float(value) for value in row["global_features"]], stats["global"]) for row in rows],
            dtype=torch.float32,
            device=device,
        ),
        "edge_tokens": torch.tensor(
            [
                [standardize([float(value) for value in token], stats["edge"]) for token in row["edge_tokens"]]
                for row in rows
            ],
            dtype=torch.float32,
            device=device,
        ),
        "edge_mask": torch.tensor([row["edge_mask"] for row in rows], dtype=torch.bool, device=device),
        "trace_tokens": torch.tensor(
            [
                [standardize([float(value) for value in token], stats["trace"]) for token in row["trace_tokens"]]
                for row in rows
            ],
            dtype=torch.float32,
            device=device,
        ),
        "trace_mask": torch.tensor([row["trace_mask"] for row in rows], dtype=torch.bool, device=device),
        "rule_tokens": torch.tensor(
            [
                [standardize([float(value) for value in token], stats["rule"]) for token in row["rule_tokens"]]
                for row in rows
            ],
            dtype=torch.float32,
            device=device,
        ),
        "rule_target": torch.tensor(
            [int(row["target"]["rule_class_executable_index"]) for row in rows],
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
        "confidence_target": torch.tensor(
            [min(1.0, max(0.0, abs(float(row["target"]["best_minus_additive_margin"])) / 0.05)) for row in rows],
            dtype=torch.float32,
            device=device,
        ),
        "soft_rule_target_stable": torch.tensor(
            [[float(value) for value in row["soft_rule_target_stable"]] for row in rows],
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


def batched(rows: list[dict[str, Any]], batch_size: int, *, shuffle: bool = False) -> list[list[dict[str, Any]]]:
    values = list(rows)
    if shuffle:
        random.shuffle(values)
    size = max(1, int(batch_size))
    return [values[index : index + size] for index in range(0, len(values), size)]


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


def rank_values(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(order):
        end = index + 1
        while end < len(order) and values[order[end]] == values[order[index]]:
            end += 1
        average = (index + end - 1) / 2.0
        for pos in range(index, end):
            ranks[order[pos]] = average
        index = end
    return ranks


def pearson(first: list[float], second: list[float]) -> float | None:
    if len(first) != len(second) or len(first) < 2:
        return None
    mean_a = sum(first) / len(first)
    mean_b = sum(second) / len(second)
    num = sum((a - mean_a) * (b - mean_b) for a, b in zip(first, second))
    den_a = math.sqrt(sum((a - mean_a) ** 2 for a in first))
    den_b = math.sqrt(sum((b - mean_b) ** 2 for b in second))
    if den_a <= 0.0 or den_b <= 0.0:
        return None
    return num / (den_a * den_b)


def spearman(first: list[float], second: list[float]) -> float | None:
    return pearson(rank_values(first), rank_values(second))


def pairwise_accuracy(scores: list[float], deltas: list[float]) -> float | None:
    total = 0
    correct = 0
    for i in range(len(deltas)):
        for j in range(len(deltas)):
            if deltas[i] <= deltas[j]:
                continue
            total += 1
            if scores[i] > scores[j]:
                correct += 1
    return correct / total if total else None


def select_rule(
    q_delta: list[float],
    harmful_probs: list[float],
    *,
    safety_threshold: float,
    safety_penalty: float,
    confidence_margin: float,
) -> dict[str, Any]:
    additive_index = EXECUTABLE_RULE_IDS.index("additive_ltm")
    scores = [
        float(delta) - float(safety_penalty) * float(harmful)
        for delta, harmful in zip(q_delta, harmful_probs)
    ]
    safe = [
        index == additive_index or float(probability) < float(safety_threshold)
        for index, probability in enumerate(harmful_probs)
    ]
    safe_non_additive = [index for index, allowed in enumerate(safe) if allowed and index != additive_index]
    if not safe_non_additive:
        return {
            "selected_index": additive_index,
            "fallback_reason": "unsafe",
            "scores": scores,
        }
    safe_indices = [index for index, allowed in enumerate(safe) if allowed]
    best_safe = max(safe_indices, key=lambda index: scores[index])
    if scores[best_safe] - scores[additive_index] < float(confidence_margin):
        return {
            "selected_index": additive_index,
            "fallback_reason": "low_confidence",
            "scores": scores,
        }
    return {
        "selected_index": int(best_safe),
        "fallback_reason": "selected",
        "scores": scores,
    }


def evaluate_model(
    model: Any,
    rows: list[dict[str, Any]],
    *,
    stats: dict[str, Any],
    device: torch.device,
    batch_size: int,
    safety_threshold: float,
    safety_penalty: float,
    confidence_margin: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not rows:
        return {"sample_count": 0}, []
    model.eval()
    all_records: list[dict[str, Any]] = []
    with torch.no_grad():
        for batch_rows in batched(rows, batch_size):
            batch = rows_to_batch(batch_rows, stats, device)
            outputs = model(batch)
            q_values = outputs["q_delta"].detach().cpu().tolist()
            harmful_probs = torch.sigmoid(outputs["harmful_logit"]).detach().cpu().tolist()
            confidences = torch.sigmoid(outputs["confidence_logit"]).detach().cpu().tolist()
            for row, q_delta, harmful_prob, confidence in zip(batch_rows, q_values, harmful_probs, confidences):
                selection = select_rule(
                    [float(value) for value in q_delta],
                    [float(value) for value in harmful_prob],
                    safety_threshold=safety_threshold,
                    safety_penalty=safety_penalty,
                    confidence_margin=confidence_margin,
                )
                selected_index = int(selection["selected_index"])
                target_index = int(row["target"]["rule_class_executable_index"])
                original_index = EXECUTABLE_RULE_IDS.index(
                    executable_rule_id(row["target"]["rule_class_original"])
                )
                ranked = topk_indices(selection["scores"], len(EXECUTABLE_RULE_IDS))
                top3 = ranked[:3]
                deltas = [float(value) for value in row["rule_delta_vector"]]
                harmful_vector = [1 if value else 0 for value in row["rule_harmful_vector"]]
                all_records.append(
                    {
                        "split": row["split"],
                        "run_id": row["run_id"],
                        "checkpoint_id": row["checkpoint_id"],
                        "map_name": row["map_name"],
                        "agents": row["agents"],
                        "seed": row["seed"],
                        "iteration": row["iteration"],
                        "target_rule_stable": row["target"]["rule_class_stable"],
                        "target_rule_executable": EXECUTABLE_RULE_IDS[target_index],
                        "target_rule_original": row["target"]["rule_class_original"],
                        "predicted_rule": EXECUTABLE_RULE_IDS[selected_index],
                        "fallback_reason": selection["fallback_reason"],
                        "stable_top1": selected_index == target_index,
                        "stable_top3": target_index in top3,
                        "original_top1": selected_index == original_index,
                        "original_top3": original_index in top3,
                        "selected_delta": deltas[selected_index],
                        "additive_delta": deltas[0],
                        "selected_vs_additive_delta": deltas[selected_index] - deltas[0],
                        "target_delta": deltas[target_index],
                        "q_delta": json.dumps([float(value) for value in q_delta]),
                        "harmful_probs": json.dumps([float(value) for value in harmful_prob]),
                        "rule_scores": json.dumps([float(value) for value in selection["scores"]]),
                        "top3_rules": json.dumps([EXECUTABLE_RULE_IDS[index] for index in top3]),
                        "pairwise_ranking_accuracy": pairwise_accuracy([float(value) for value in q_delta], deltas),
                        "spearman_q_delta": spearman([float(value) for value in q_delta], deltas),
                        "max_confidence": max(float(value) for value in confidence),
                        "harmful_labels": json.dumps(harmful_vector),
                    }
                )
    labels: list[int] = []
    predictions: list[int] = []
    for record in all_records:
        harmful_probs = json.loads(record["harmful_probs"])
        harmful_labels = json.loads(record["harmful_labels"])
        labels.extend(int(value) for value in harmful_labels)
        predictions.extend(1 if float(value) >= float(safety_threshold) else 0 for value in harmful_probs)
    harmful = binary_metrics(labels, predictions)
    pairwise_values = [
        float(record["pairwise_ranking_accuracy"])
        for record in all_records
        if record["pairwise_ranking_accuracy"] is not None
    ]
    spearman_values = [
        float(record["spearman_q_delta"])
        for record in all_records
        if record["spearman_q_delta"] is not None
    ]
    fallback_counts = Counter(str(record["fallback_reason"]) for record in all_records)
    selected_counts = Counter(str(record["predicted_rule"]) for record in all_records)
    metrics = {
        "sample_count": len(all_records),
        "rule_top1_accuracy": sum(1 for record in all_records if record["stable_top1"]) / len(all_records),
        "rule_top3_accuracy": sum(1 for record in all_records if record["stable_top3"]) / len(all_records),
        "stable_target_top1_accuracy": sum(1 for record in all_records if record["stable_top1"]) / len(all_records),
        "stable_target_top3_accuracy": sum(1 for record in all_records if record["stable_top3"]) / len(all_records),
        "original_target_top1_accuracy": sum(1 for record in all_records if record["original_top1"]) / len(all_records),
        "original_target_top3_accuracy": sum(1 for record in all_records if record["original_top3"]) / len(all_records),
        "harmful_update_recall": harmful["recall"],
        "harmful_update_precision": harmful["precision"],
        "harmful_update_f1": harmful["f1"],
        "predicted_rule_validation_mean_delta_ratio": sum(float(record["selected_delta"]) for record in all_records) / len(all_records),
        "selected_vs_additive_delta_mean": sum(float(record["selected_vs_additive_delta"]) for record in all_records) / len(all_records),
        "fallback_rate": sum(1 for record in all_records if record["fallback_reason"] != "selected") / len(all_records),
        "unsafe_fallback_rate": fallback_counts.get("unsafe", 0) / len(all_records),
        "low_confidence_fallback_rate": fallback_counts.get("low_confidence", 0) / len(all_records),
        "pairwise_ranking_accuracy": sum(pairwise_values) / len(pairwise_values) if pairwise_values else None,
        "spearman_q_delta_mean": sum(spearman_values) / len(spearman_values) if spearman_values else None,
        "selected_rule_distribution": dict(sorted(selected_counts.items())),
        "fallback_reason_distribution": dict(sorted(fallback_counts.items())),
    }
    return metrics, all_records


def phase4f_gate(validation: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "validation_top1": {
            "value": validation.get("rule_top1_accuracy"),
            "threshold": 0.35,
            "passed": float(validation.get("rule_top1_accuracy") or 0.0) >= 0.35,
        },
        "validation_top3": {
            "value": validation.get("rule_top3_accuracy"),
            "threshold": 0.70,
            "passed": float(validation.get("rule_top3_accuracy") or 0.0) >= 0.70,
        },
        "harmful_recall": {
            "value": validation.get("harmful_update_recall"),
            "threshold": 0.80,
            "passed": float(validation.get("harmful_update_recall") or 0.0) >= 0.80,
        },
        "harmful_precision": {
            "value": validation.get("harmful_update_precision"),
            "threshold": 0.30,
            "passed": float(validation.get("harmful_update_precision") or 0.0) >= 0.30,
        },
        "mean_selected_delta": {
            "value": validation.get("predicted_rule_validation_mean_delta_ratio"),
            "threshold": "> 0.0",
            "passed": float(validation.get("predicted_rule_validation_mean_delta_ratio") or 0.0) > 0.0,
        },
        "validation_non_neutral": {
            "value": None,
            "threshold": 50,
            "passed": False,
        },
    }
    checks["passed"] = all(bool(value["passed"]) for value in checks.values() if isinstance(value, dict))
    return checks


def model_selection_score(validation: dict[str, Any], *, mode: str = "standard") -> float:
    top1 = float(validation.get("rule_top1_accuracy") or 0.0)
    top3 = float(validation.get("rule_top3_accuracy") or 0.0)
    recall = float(validation.get("harmful_update_recall") or 0.0)
    precision = float(validation.get("harmful_update_precision") or 0.0)
    delta = float(validation.get("predicted_rule_validation_mean_delta_ratio") or 0.0)
    if mode == "phase4f_gate":
        gate_terms = [
            min(top1 / 0.35, 1.0),
            min(top3 / 0.70, 1.0),
            min(recall / 0.80, 1.0),
            min(precision / 0.30, 1.0),
            1.0 if delta > 0.0 else max(-1.0, delta * 100.0),
        ]
        tie_break = 0.01 * (top1 + top3 + recall + precision) + max(-0.01, min(delta, 0.01))
        return float(sum(gate_terms) + tie_break)
    if mode != "standard":
        raise ValueError(f"unknown stable-attention model selection mode: {mode}")
    return float(top1 + 0.5 * top3 + 0.05 * recall + 0.05 * precision + 0.1 * max(0.0, delta))


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)


def write_report(path: Path, *, root: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    validation = summary["metrics_by_split"].get("validation", {})
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair4 Stable-Attention Train Report\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("## Code State\n\n")
        handle.write(f"- branch: `{git_value(['branch', '--show-current'], root)}`\n")
        handle.write(f"- commit: `{git_value(['rev-parse', '--short', 'HEAD'], root)}`\n")
        handle.write(f"- dirty: `{dirty_state(root)}`\n\n")
        handle.write("## Inputs\n\n")
        handle.write(f"- dataset: `{summary['dataset']}`\n")
        handle.write(f"- model_path: `{summary['model_path']}`\n")
        handle.write(f"- model_name: `{summary['model_name']}`\n")
        handle.write(f"- parameter_count: `{summary['parameter_count']}`\n")
        handle.write(f"- seed: `{summary['seed']}`\n")
        handle.write(f"- epochs: `{summary['epochs']}`\n")
        handle.write(f"- training_time_sec: `{summary['training_time_sec']}`\n\n")
        handle.write("## Validation Metrics\n\n")
        handle.write(f"- top1: `{validation.get('rule_top1_accuracy')}`\n")
        handle.write(f"- top3: `{validation.get('rule_top3_accuracy')}`\n")
        handle.write(f"- harmful recall: `{validation.get('harmful_update_recall')}`\n")
        handle.write(f"- harmful precision: `{validation.get('harmful_update_precision')}`\n")
        handle.write(f"- mean selected delta: `{validation.get('predicted_rule_validation_mean_delta_ratio')}`\n")
        handle.write(f"- fallback rate: `{validation.get('fallback_rate')}`\n\n")
        handle.write("## Phase4F Gate\n\n")
        for key, value in summary.get("phase4f_gate", {}).items():
            if key == "passed" or not isinstance(value, dict):
                continue
            handle.write(
                f"- {key}: `{value.get('value')}` vs `{value.get('threshold')}` -> "
                f"{'pass' if value.get('passed') else 'fail'}\n"
            )
        handle.write(f"\nOverall: `{'pass' if summary.get('phase4f_gate', {}).get('passed') else 'fail'}`\n\n")
        handle.write("## Boundary\n\n")
        handle.write(
            "This is an offline stable-target attention experiment. No Phase5.5 "
            "runtime export or C++ solver integration is implied by this report.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--summary-csv", type=Path)
    parser.add_argument("--model-name", choices=[SET_RULE_TRANSFORMER_NAME, EDGE_TRACE_TRANSFORMER_NAME])
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--d-model", type=int)
    parser.add_argument("--n-heads", type=int)
    parser.add_argument("--n-layers", type=int)
    parser.add_argument("--dropout", type=float)
    parser.add_argument("--learning-rate", type=float)
    parser.add_argument("--weight-decay", type=float)
    parser.add_argument("--safety-threshold", type=float)
    parser.add_argument("--safety-penalty", type=float)
    parser.add_argument("--confidence-margin", type=float)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    config_path = resolve_path(args.config, root)
    config = load_config(config_path)
    train_config = config_get(config, "stable_attention", "training", default={}) or {}
    model_config = config_get(config, "stable_attention", "model", default={}) or {}
    eval_config = config_get(config, "stable_attention", "eval", default={}) or {}
    loss_config = config_get(config, "stable_attention", "loss", default={}) or {}

    seed = int(args.seed if args.seed is not None else train_config.get("seed", 61))
    dataset_path = resolve_path(args.dataset or config_get(config, "stable_attention", "dataset_jsonl"), root)
    output_dir = resolve_path(args.output_dir or train_config.get("model_output_dir"), root, seed=seed)
    report_path = resolve_path(args.report or train_config.get("train_report_md"), root, seed=seed)
    summary_json_path = resolve_path(args.summary_json or train_config.get("train_summary_json"), root, seed=seed)
    summary_csv_path = resolve_path(args.summary_csv or train_config.get("train_summary_csv"), root, seed=seed)
    if None in (dataset_path, output_dir, report_path, summary_json_path, summary_csv_path):
        raise ValueError("dataset/output/report/summary paths are required")
    assert dataset_path and output_dir and report_path and summary_json_path and summary_csv_path

    rows = read_jsonl(dataset_path)
    validate_rows(rows)
    splits = split_rows(rows)
    train_rows = splits["train"]
    validation_rows = splits["validation"]
    stats = feature_stats(train_rows)
    random.seed(seed)
    torch.manual_seed(seed)
    if args.device == "auto" or (args.device is None and str(train_config.get("device", "auto")) == "auto"):
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device or train_config.get("device", "cpu"))

    model_name = str(args.model_name or model_config.get("name", SET_RULE_TRANSFORMER_NAME))
    model_args = {
        "global_dim": len(GLOBAL_FEATURE_NAMES),
        "edge_dim": len(EDGE_FEATURE_NAMES),
        "trace_dim": len(TRACE_FEATURE_NAMES),
        "rule_dim": len(RULE_FEATURE_NAMES),
        "num_rules": len(EXECUTABLE_RULE_IDS),
        "num_families": len(RULE_FAMILY_IDS),
        "d_model": int(args.d_model or model_config.get("d_model", 64)),
        "n_heads": int(args.n_heads or model_config.get("n_heads", 2)),
        "n_layers": int(args.n_layers or model_config.get("n_layers", 2)),
        "dropout": float(args.dropout if args.dropout is not None else model_config.get("dropout", 0.1)),
    }
    model = build_model(model_name, **model_args).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(args.learning_rate or train_config.get("learning_rate", 0.001)),
        weight_decay=float(args.weight_decay if args.weight_decay is not None else train_config.get("weight_decay", 0.0005)),
    )
    epochs = int(args.epochs or train_config.get("epochs", 250))
    batch_size = int(args.batch_size or train_config.get("batch_size", 128))
    eval_interval = int(train_config.get("eval_interval", max(1, epochs // 10)))
    selection_score_mode = str(train_config.get("selection_score_mode", "standard"))
    safety_threshold = float(args.safety_threshold if args.safety_threshold is not None else eval_config.get("safety_threshold", 0.10))
    safety_penalty = float(args.safety_penalty if args.safety_penalty is not None else eval_config.get("safety_penalty", 0.02))
    confidence_margin = float(args.confidence_margin if args.confidence_margin is not None else eval_config.get("confidence_margin", 0.002))
    harmful_pos_weight_config = loss_config.get("harmful_pos_weight", 1.0)
    harmful_pos_weight = 1.0
    if str(harmful_pos_weight_config).lower() == "auto":
        positives = sum(int(value) for row in train_rows for value in row["rule_harmful_vector"])
        total = len(train_rows) * len(EXECUTABLE_RULE_IDS)
        negatives = max(1, total - positives)
        harmful_pos_weight = negatives / max(1, positives)
    else:
        harmful_pos_weight = float(harmful_pos_weight_config)
    loss_weights = StableAttentionLossWeights(
        lambda_listwise=float(loss_config.get("lambda_listwise", 1.0)),
        lambda_pairwise=float(loss_config.get("lambda_pairwise", 0.5)),
        lambda_delta=float(loss_config.get("lambda_delta", 0.5)),
        lambda_safe=float(loss_config.get("lambda_safe", 2.0)),
        lambda_family=float(loss_config.get("lambda_family", 0.1)),
        lambda_conf=float(loss_config.get("lambda_conf", 0.1)),
        lambda_additive=float(loss_config.get("lambda_additive", 0.1)),
        pairwise_margin=float(loss_config.get("pairwise_margin", 0.005)),
        harmful_pos_weight=harmful_pos_weight,
    )
    additive_index = EXECUTABLE_RULE_IDS.index("additive_ltm")
    best_state = copy.deepcopy(model.state_dict())
    best_score = float("-inf")
    final_loss = 0.0
    started = time.perf_counter()
    for epoch in range(epochs):
        model.train()
        epoch_losses: list[float] = []
        for batch_rows in batched(train_rows, batch_size, shuffle=True):
            batch = rows_to_batch(batch_rows, stats, device)
            optimizer.zero_grad(set_to_none=True)
            losses = laur_stable_attention_loss(
                model(batch),
                batch,
                additive_index=additive_index,
                weights=loss_weights,
            )
            losses["total"].backward()
            optimizer.step()
            epoch_losses.append(float(losses["total"].detach().cpu()))
        final_loss = sum(epoch_losses) / len(epoch_losses) if epoch_losses else 0.0
        if (epoch + 1) % max(1, eval_interval) == 0 or epoch == epochs - 1:
            validation_metrics, _ = evaluate_model(
                model,
                validation_rows,
                stats=stats,
                device=device,
                batch_size=batch_size,
                safety_threshold=safety_threshold,
                safety_penalty=safety_penalty,
                confidence_margin=confidence_margin,
            )
            score = model_selection_score(validation_metrics, mode=selection_score_mode)
            if score > best_score:
                best_score = score
                best_state = copy.deepcopy(model.state_dict())
    training_time_sec = time.perf_counter() - started

    model.load_state_dict(best_state)
    metrics_by_split: dict[str, dict[str, Any]] = {}
    all_records: list[dict[str, Any]] = []
    for split_name, split_values in sorted(splits.items()):
        metrics, records = evaluate_model(
            model,
            split_values,
            stats=stats,
            device=device,
            batch_size=batch_size,
            safety_threshold=safety_threshold,
            safety_penalty=safety_penalty,
            confidence_margin=confidence_margin,
        )
        metrics_by_split[split_name] = metrics
        all_records.extend(records)
    validation_non_neutral = sum(1 for row in validation_rows if not row["target"]["is_neutral_label"])
    gate = phase4f_gate(metrics_by_split.get("validation", {}))
    gate["validation_non_neutral"]["value"] = validation_non_neutral
    gate["validation_non_neutral"]["passed"] = validation_non_neutral >= 50
    gate["passed"] = all(bool(value["passed"]) for value in gate.values() if isinstance(value, dict))

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "laur_stable_attention_v1.pt"
    checkpoint = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "model_name": model_name,
        "model_state_dict": model.state_dict(),
        "model_args": model_args,
        "feature_stats": stats,
        "global_feature_names": list(GLOBAL_FEATURE_NAMES),
        "edge_feature_names": list(EDGE_FEATURE_NAMES),
        "trace_feature_names": list(TRACE_FEATURE_NAMES),
        "rule_feature_names": list(RULE_FEATURE_NAMES),
        "rule_vocab": list(EXECUTABLE_RULE_IDS),
        "rule_family_vocab": list(RULE_FAMILY_IDS),
        "safety_threshold": safety_threshold,
        "safety_penalty": safety_penalty,
        "confidence_margin": confidence_margin,
        "selection_score_mode": selection_score_mode,
        "seed": seed,
    }
    torch.save(checkpoint, model_path)
    write_csv(summary_csv_path, all_records)
    summary = {
        "schema_version": "phase4f_repair4_stable_attention_train_summary_v1",
        "dataset": str(dataset_path),
        "output_dir": str(output_dir),
        "model_path": str(model_path),
        "model_name": model_name,
        "model_args": model_args,
        "parameter_count": parameter_count(model),
        "epochs": epochs,
        "batch_size": batch_size,
        "seed": seed,
        "device": str(device),
        "training_time_sec": training_time_sec,
        "final_loss": final_loss,
        "best_selection_score": best_score,
        "selection_score_mode": selection_score_mode,
        "harmful_pos_weight": harmful_pos_weight,
        "safety_threshold": safety_threshold,
        "safety_penalty": safety_penalty,
        "confidence_margin": confidence_margin,
        "metrics_by_split": metrics_by_split,
        "phase4f_gate": gate,
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
    }
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report_path, root=root, summary=summary)
    print(json.dumps({"model_path": str(model_path), "summary_json": str(summary_json_path), "report": str(report_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

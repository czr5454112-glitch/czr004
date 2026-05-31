"""Train Phase4F Repair5 attention-native LAUR update-rule models."""

from __future__ import annotations

import argparse
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

from czr004_teacher.attention_native_schema_laur import (  # noqa: E402
    DEFAULT_ANTI_ESCAPE_THRESHOLDS,
    validate_attention_native_row,
)
from czr004_teacher.stable_attention_dataset_laur import read_jsonl  # noqa: E402
from czr004_teacher.stable_attention_tokens_laur import (  # noqa: E402
    EDGE_FEATURE_NAMES,
    EXECUTABLE_RULE_IDS,
    GLOBAL_FEATURE_NAMES,
    RULE_FAMILY_IDS,
    RULE_FEATURE_NAMES,
    TRACE_FEATURE_NAMES,
)
from models.laur_attention_native import (  # noqa: E402
    EDGE_TRACE_TRANSFORMER_NAME,
    HIER_EDGE_TRACE_TRANSFORMER_NAME,
    MODEL_SCHEMA_VERSION,
    SET_RULE_TRANSFORMER_NAME,
    build_model,
    parameter_count,
)
from train.losses_laur_attention_native import (  # noqa: E402
    AttentionNativeLossWeights,
    laur_attention_native_loss,
)

try:
    import torch
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyTorch is required for Repair5 attention-native training") from exc


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
        raise RuntimeError("PyYAML is required to read Repair5 configs") from exc
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
        errors.extend(f"row {index}: {error}" for error in validate_attention_native_row(row))
    if not rows:
        errors.append("dataset is empty")
    if errors:
        raise ValueError("attention-native dataset schema errors:\n" + "\n".join(errors[:30]))


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
        "soft_utility_target": torch.tensor(
            [[float(value) for value in row["soft_utility_target"]] for row in rows],
            dtype=torch.float32,
            device=device,
        ),
        "utility_target": torch.tensor(
            [[float(value) for value in row["risk_adjusted_utility_vector"]] for row in rows],
            dtype=torch.float32,
            device=device,
        ),
        "harmful_target": torch.tensor(
            [[1.0 if value else 0.0 for value in row["probe_harmful_vector"]] for row in rows],
            dtype=torch.float32,
            device=device,
        ),
        "opportunity_target": torch.tensor(
            [1.0 if row["has_nonadditive_opportunity"] else 0.0 for row in rows],
            dtype=torch.float32,
            device=device,
        ),
        "defer_target": torch.tensor(
            [1.0 if row["decision_target"] == "defer_ltm" else 0.0 for row in rows],
            dtype=torch.float32,
            device=device,
        ),
        "rule_target": torch.tensor(
            [max(0, int(row["target"]["target_rule_index"])) for row in rows],
            dtype=torch.long,
            device=device,
        ),
        "family_target": torch.tensor(
            [max(0, int(row["target"]["rule_family_index"])) for row in rows],
            dtype=torch.long,
            device=device,
        ),
        "use_nonadditive_mask": torch.tensor(
            [1 if row["decision_target"] == "use_nonadditive" else 0 for row in rows],
            dtype=torch.bool,
            device=device,
        ),
        "pairwise_dominance": torch.tensor(
            [[[1.0 if value else 0.0 for value in line] for line in row["pairwise_dominance_matrix"]] for row in rows],
            dtype=torch.float32,
            device=device,
        ),
        "pairwise_observed": torch.tensor(
            [[[1.0 if value else 0.0 for value in line] for line in row["pairwise_observed_mask"]] for row in rows],
            dtype=torch.float32,
            device=device,
        ),
        "anti_escape_sample": torch.tensor(
            [1.0 if row["anti_escape_sample"] else 0.0 for row in rows],
            dtype=torch.float32,
            device=device,
        ),
        "high_margin_opportunity_mask": torch.tensor(
            [1.0 if row["has_high_margin_nonadditive_opportunity"] else 0.0 for row in rows],
            dtype=torch.float32,
            device=device,
        ),
        "anti_escape_candidate_mask": torch.tensor(
            [[1 if value else 0 for value in row["anti_escape_candidate_mask"]] for row in rows],
            dtype=torch.bool,
            device=device,
        ),
    }


def batched(rows: list[dict[str, Any]], batch_size: int, *, shuffle: bool = False) -> list[list[dict[str, Any]]]:
    values = list(rows)
    if shuffle:
        random.shuffle(values)
    size = max(1, int(batch_size))
    return [values[index : index + size] for index in range(0, len(values), size)]


def load_hardcase_checkpoint_ids(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    ids: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                item = json.loads(text)
            except json.JSONDecodeError:
                continue
            checkpoint = str(item.get("checkpoint_id", ""))
            if checkpoint:
                ids.add(checkpoint)
    return ids


def sample_epoch_rows(rows: list[dict[str, Any]], train_config: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    if not rows:
        return []
    sampler = str(train_config.get("sampler", "uniform")).strip().lower()
    hardcase_path = resolve_path(train_config.get("hardcase_index_jsonl") or train_config.get("hardcase_index"), root)
    hardcase_ids = load_hardcase_checkpoint_ids(hardcase_path)
    if sampler != "stratified" and not hardcase_ids:
        return list(rows)

    target_counts = Counter(str(row.get("target_rule", "")) for row in rows if row.get("target_rule"))
    max_target_count = max(target_counts.values()) if target_counts else 1
    defer_counts = Counter(str(row.get("defer_reason") or row.get("decision_target") or "") for row in rows)
    max_defer_count = max(defer_counts.values()) if defer_counts else 1
    high_margin_weight = float(train_config.get("high_margin_weight", 1.0))
    harmful_positive_weight = float(train_config.get("harmful_positive_weight", 1.0))
    rare_rule_weight = float(train_config.get("rare_rule_weight", 1.0))
    hardcase_replay_weight = float(train_config.get("hardcase_replay_weight", 1.0))
    balance_defer = bool(train_config.get("defer_reason_balance", False))
    weights: list[float] = []
    for row in rows:
        weight = 1.0
        if bool(row.get("has_high_margin_nonadditive_opportunity")):
            weight *= max(0.0, high_margin_weight)
        if any(bool(value) for value in row.get("probe_harmful_vector", [])):
            weight *= max(0.0, harmful_positive_weight)
        target_rule = str(row.get("target_rule", ""))
        if target_rule and target_counts.get(target_rule):
            rarity = max_target_count / max(1, target_counts[target_rule])
            weight *= 1.0 + max(0.0, rare_rule_weight - 1.0) * min(rarity, 5.0) / 5.0
        if balance_defer:
            reason = str(row.get("defer_reason") or row.get("decision_target") or "")
            weight *= max_defer_count / max(1, defer_counts.get(reason, 1))
        if str(row.get("checkpoint_id", "")) in hardcase_ids:
            weight *= max(0.0, hardcase_replay_weight)
        weights.append(max(weight, 1.0e-6))
    sample_count = int(train_config.get("sampler_epoch_size", len(rows)))
    return random.choices(rows, weights=weights, k=max(1, sample_count))


def loss_config_for_epoch(
    base_loss_config: dict[str, Any],
    curriculum_config: dict[str, Any],
    epoch: int,
) -> dict[str, Any]:
    merged = dict(base_loss_config)
    merged["_curriculum_stage"] = "base"
    if not isinstance(curriculum_config, dict):
        return merged
    stages = curriculum_config.get("stages", [])
    if not isinstance(stages, list):
        return merged
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        start_epoch = int(stage.get("from_epoch", stage.get("start_epoch", 1)))
        end_value = stage.get("until_epoch", stage.get("end_epoch"))
        end_epoch = int(end_value) if end_value is not None else None
        if int(epoch) < start_epoch:
            continue
        if end_epoch is not None and int(epoch) > end_epoch:
            continue
        loss_overrides = stage.get("loss", {})
        if isinstance(loss_overrides, dict):
            merged.update(loss_overrides)
        merged["_curriculum_stage"] = str(stage.get("name", f"stage_{start_epoch}"))
        return merged
    return merged


def make_loss_weights(
    loss_config: dict[str, Any],
    *,
    harmful_pos_weight: float,
    opportunity_pos_weight: float,
) -> AttentionNativeLossWeights:
    return AttentionNativeLossWeights(
        lambda_listwise=float(loss_config.get("lambda_listwise", 1.0)),
        lambda_pairwise=float(loss_config.get("lambda_pairwise", 1.0)),
        lambda_rule_ce=float(loss_config.get("lambda_rule_ce", 0.0)),
        lambda_rule_margin=float(loss_config.get("lambda_rule_margin", 0.0)),
        lambda_delta=float(loss_config.get("lambda_delta", 0.5)),
        lambda_harmful=float(loss_config.get("lambda_harmful", 2.0)),
        lambda_harmful_pairwise=float(loss_config.get("lambda_harmful_pairwise", 0.0)),
        lambda_high_margin_harmful=float(loss_config.get("lambda_high_margin_harmful", 0.0)),
        lambda_anti_candidate_safety=float(loss_config.get("lambda_anti_candidate_safety", 0.0)),
        lambda_opportunity=float(loss_config.get("lambda_opportunity", 1.0)),
        lambda_defer=float(loss_config.get("lambda_defer", 0.5)),
        lambda_anti_escape=float(loss_config.get("lambda_anti_escape", 2.0)),
        lambda_family=float(loss_config.get("lambda_family", 0.1)),
        anti_escape_score_margin=float(loss_config.get("anti_escape_score_margin", 0.005)),
        rule_margin=float(loss_config.get("rule_margin", 0.010)),
        rule_ce_high_margin_weight=float(loss_config.get("rule_ce_high_margin_weight", 1.0)),
        rule_margin_high_margin_weight=float(loss_config.get("rule_margin_high_margin_weight", 1.0)),
        harmful_pairwise_margin=float(loss_config.get("harmful_pairwise_margin", 0.25)),
        harmful_pos_weight=float(loss_config.get("harmful_pos_weight", harmful_pos_weight)),
        harmful_negative_weight=float(loss_config.get("harmful_negative_weight", 1.0)),
        harmful_focal_gamma=float(loss_config.get("harmful_focal_gamma", 0.0)),
        opportunity_pos_weight=float(loss_config.get("opportunity_pos_weight", opportunity_pos_weight)),
    )


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


def safety_threshold_for_index(safety_threshold: Any, index: int) -> float:
    if isinstance(safety_threshold, dict):
        rule_id = EXECUTABLE_RULE_IDS[int(index)]
        return float(safety_threshold.get(rule_id, safety_threshold.get(str(index), 0.5)))
    if isinstance(safety_threshold, (list, tuple)):
        if int(index) < len(safety_threshold):
            return float(safety_threshold[int(index)])
        return float(safety_threshold[-1])
    return float(safety_threshold)


def _selection_return(
    *,
    selected_decision: str,
    selected_index: int,
    fallback_reason: str,
    selection_stage: str,
    adjusted_scores: list[float],
    safety_threshold_by_rule: list[float],
    safety_mask: list[bool],
    best_safe_nonadditive_index: int | None,
    margin_vs_additive: float | None,
    margin_vs_defer: float,
) -> dict[str, Any]:
    return {
        "selected_decision": selected_decision,
        "selected_index": int(selected_index),
        "fallback_reason": fallback_reason,
        "defer_reason": fallback_reason if selected_decision == "defer_ltm" else "",
        "selection_stage": selection_stage,
        "scores": adjusted_scores,
        "safety_threshold_by_rule": safety_threshold_by_rule,
        "safety_mask": safety_mask,
        "best_safe_nonadditive_rule": (
            EXECUTABLE_RULE_IDS[int(best_safe_nonadditive_index)]
            if best_safe_nonadditive_index is not None
            else ""
        ),
        "best_safe_nonadditive_score": (
            float(adjusted_scores[int(best_safe_nonadditive_index)])
            if best_safe_nonadditive_index is not None
            else None
        ),
        "margin_vs_additive": margin_vs_additive,
        "margin_vs_defer": float(margin_vs_defer),
    }


def select_attention_native(
    rule_scores: list[float],
    harmful_probs: list[float],
    *,
    opportunity_prob: float,
    defer_prob: float,
    safety_threshold: Any,
    safety_penalty: float,
    opportunity_threshold: float,
    defer_threshold: float,
    confidence_margin: float,
) -> dict[str, Any]:
    additive_index = EXECUTABLE_RULE_IDS.index("additive_ltm")
    safety_threshold_by_rule = [
        safety_threshold_for_index(safety_threshold, index)
        for index in range(len(EXECUTABLE_RULE_IDS))
    ]
    safety_mask = [
        float(harmful_probs[index]) < safety_threshold_by_rule[index]
        for index in range(len(EXECUTABLE_RULE_IDS))
    ]
    adjusted = [
        float(score) - float(safety_penalty) * float(harmful)
        for score, harmful in zip(rule_scores, harmful_probs)
    ]
    safe_nonadditive = [
        index
        for index in range(len(EXECUTABLE_RULE_IDS))
        if index != additive_index
        and safety_mask[index]
    ]
    best_nonadditive = max(safe_nonadditive, key=lambda index: adjusted[index]) if safe_nonadditive else None
    margin_vs_additive = (
        float(adjusted[int(best_nonadditive)] - adjusted[additive_index])
        if best_nonadditive is not None
        else None
    )
    margin_vs_defer = float(opportunity_prob) - float(defer_prob)
    if float(opportunity_prob) < float(opportunity_threshold):
        return _selection_return(
            selected_decision="defer_ltm",
            selected_index=additive_index,
            fallback_reason="low_opportunity",
            selection_stage="defer_low_opportunity",
            adjusted_scores=adjusted,
            safety_threshold_by_rule=safety_threshold_by_rule,
            safety_mask=safety_mask,
            best_safe_nonadditive_index=best_nonadditive,
            margin_vs_additive=margin_vs_additive,
            margin_vs_defer=margin_vs_defer,
        )
    if float(defer_prob) >= float(defer_threshold):
        return _selection_return(
            selected_decision="defer_ltm",
            selected_index=additive_index,
            fallback_reason="defer_head",
            selection_stage="defer_head",
            adjusted_scores=adjusted,
            safety_threshold_by_rule=safety_threshold_by_rule,
            safety_mask=safety_mask,
            best_safe_nonadditive_index=best_nonadditive,
            margin_vs_additive=margin_vs_additive,
            margin_vs_defer=margin_vs_defer,
        )
    if not safe_nonadditive:
        return _selection_return(
            selected_decision="defer_ltm",
            selected_index=additive_index,
            fallback_reason="unsafe",
            selection_stage="defer_unsafe",
            adjusted_scores=adjusted,
            safety_threshold_by_rule=safety_threshold_by_rule,
            safety_mask=safety_mask,
            best_safe_nonadditive_index=best_nonadditive,
            margin_vs_additive=margin_vs_additive,
            margin_vs_defer=margin_vs_defer,
        )
    assert best_nonadditive is not None and margin_vs_additive is not None
    if margin_vs_additive < float(confidence_margin):
        return _selection_return(
            selected_decision="defer_ltm",
            selected_index=additive_index,
            fallback_reason="low_confidence",
            selection_stage="defer_insufficient_margin",
            adjusted_scores=adjusted,
            safety_threshold_by_rule=safety_threshold_by_rule,
            safety_mask=safety_mask,
            best_safe_nonadditive_index=best_nonadditive,
            margin_vs_additive=margin_vs_additive,
            margin_vs_defer=margin_vs_defer,
        )
    return _selection_return(
        selected_decision="use_nonadditive",
        selected_index=int(best_nonadditive),
        fallback_reason="selected",
        selection_stage="select_safe_nonadditive",
        adjusted_scores=adjusted,
        safety_threshold_by_rule=safety_threshold_by_rule,
        safety_mask=safety_mask,
        best_safe_nonadditive_index=best_nonadditive,
        margin_vs_additive=margin_vs_additive,
        margin_vs_defer=margin_vs_defer,
    )


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def attention_native_gate(validation: dict[str, Any]) -> dict[str, Any]:
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
            "value": validation.get("validation_non_neutral"),
            "threshold": 50,
            "passed": int(validation.get("validation_non_neutral") or 0) >= 50,
        },
    }
    checks["passed"] = all(bool(value["passed"]) for value in checks.values() if isinstance(value, dict))
    return checks


def anti_escape_metrics(records: list[dict[str, Any]], *, thresholds: dict[str, Any] | None = None) -> dict[str, Any]:
    opts = {**DEFAULT_ANTI_ESCAPE_THRESHOLDS, **(thresholds or {})}
    if not records:
        return {"passed": False, "reason": "no validation records"}
    opportunity = [record for record in records if bool(record["has_nonadditive_opportunity"])]
    high_margin = [record for record in records if bool(record["has_high_margin_nonadditive_opportunity"])]
    selected_nonadditive = [
        record
        for record in records
        if record["selected_decision"] != "defer_ltm" and record["predicted_rule"] != "additive_ltm"
    ]
    opportunity_nonadditive = [
        record
        for record in opportunity
        if record["selected_decision"] != "defer_ltm" and record["predicted_rule"] != "additive_ltm"
    ]
    captured_high_margin = [
        record
        for record in high_margin
        if record["selected_decision"] != "defer_ltm"
        and record["predicted_rule"] != "additive_ltm"
        and not bool(record["selected_rule_harmful"])
        and float(record["selected_vs_additive_delta"]) >= float(record["opportunity_margin"])
    ]
    additive_or_defer = [
        record
        for record in records
        if record["selected_decision"] == "defer_ltm" or record["predicted_rule"] == "additive_ltm"
    ]
    high_margin_escape = [
        record
        for record in high_margin
        if record["selected_decision"] == "defer_ltm" or record["predicted_rule"] == "additive_ltm"
    ]
    decision_distribution = Counter(str(record["selected_decision"]) for record in records)
    selected_distribution = Counter(str(record["predicted_rule"]) for record in records)
    metrics = {
        "validation_opportunity_count": len(opportunity),
        "validation_high_margin_opportunity_count": len(high_margin),
        "nonadditive_capture_rate": len(opportunity_nonadditive) / len(opportunity) if opportunity else 0.0,
        "high_margin_nonadditive_capture_rate": len(captured_high_margin) / len(high_margin) if high_margin else 0.0,
        "avoidable_additive_fallback_rate": len(high_margin_escape) / len(high_margin) if high_margin else 1.0,
        "avoidable_defer_rate": (
            sum(1 for record in high_margin if record["selected_decision"] == "defer_ltm") / len(high_margin)
            if high_margin
            else 1.0
        ),
        "avoidable_additive_or_defer_rate": len(high_margin_escape) / len(high_margin) if high_margin else 1.0,
        "anti_escape_mean_selected_vs_additive_delta": _mean(
            [float(record["selected_vs_additive_delta"]) for record in high_margin]
        )
        or 0.0,
        "global_additive_or_defer_rate": len(additive_or_defer) / len(records),
        "opportunity_additive_or_defer_rate": (
            sum(
                1
                for record in opportunity
                if record["selected_decision"] == "defer_ltm" or record["predicted_rule"] == "additive_ltm"
            )
            / len(opportunity)
            if opportunity
            else 1.0
        ),
        "opportunity_nonadditive_selection_rate": (
            len(opportunity_nonadditive) / len(opportunity) if opportunity else 0.0
        ),
        "global_nonadditive_selection_rate": len(selected_nonadditive) / len(records),
        "selected_rule_distribution": dict(sorted(selected_distribution.items())),
        "decision_distribution": dict(sorted(decision_distribution.items())),
        "thresholds": opts,
    }
    checks = {
        "high_margin_opportunity_count": {
            "value": metrics["validation_high_margin_opportunity_count"],
            "threshold": opts["min_validation_high_margin_opportunity_count"],
            "passed": metrics["validation_high_margin_opportunity_count"]
            >= int(opts["min_validation_high_margin_opportunity_count"]),
        },
        "high_margin_capture_rate": {
            "value": metrics["high_margin_nonadditive_capture_rate"],
            "threshold": opts["high_margin_nonadditive_capture_rate_min"],
            "passed": metrics["high_margin_nonadditive_capture_rate"]
            >= float(opts["high_margin_nonadditive_capture_rate_min"]),
        },
        "avoidable_additive_or_defer_rate": {
            "value": metrics["avoidable_additive_or_defer_rate"],
            "threshold": opts["avoidable_additive_or_defer_rate_max"],
            "passed": metrics["avoidable_additive_or_defer_rate"]
            <= float(opts["avoidable_additive_or_defer_rate_max"]),
        },
        "anti_escape_mean_delta": {
            "value": metrics["anti_escape_mean_selected_vs_additive_delta"],
            "threshold": opts["anti_escape_mean_selected_vs_additive_delta_min"],
            "passed": metrics["anti_escape_mean_selected_vs_additive_delta"]
            >= float(opts["anti_escape_mean_selected_vs_additive_delta_min"]),
        },
        "opportunity_nonadditive_selection_rate": {
            "value": metrics["opportunity_nonadditive_selection_rate"],
            "threshold": opts["opportunity_nonadditive_selection_rate_min"],
            "passed": metrics["opportunity_nonadditive_selection_rate"]
            >= float(opts["opportunity_nonadditive_selection_rate_min"]),
        },
        "global_additive_or_defer_rate": {
            "value": metrics["global_additive_or_defer_rate"],
            "threshold": opts["global_additive_or_defer_rate_max"],
            "passed": metrics["global_additive_or_defer_rate"]
            <= float(opts["global_additive_or_defer_rate_max"]),
        },
    }
    metrics["checks"] = checks
    if metrics["validation_high_margin_opportunity_count"] < int(opts["min_validation_high_margin_opportunity_count"]):
        metrics["passed"] = False
        metrics["inconclusive"] = True
        metrics["reason"] = "validation high-margin opportunity count below threshold"
    else:
        metrics["passed"] = all(bool(value["passed"]) for value in checks.values())
        metrics["inconclusive"] = False
        metrics["reason"] = "passed" if metrics["passed"] else "anti_escape_threshold_failed"
    return metrics


def evaluate_model(
    model: Any,
    rows: list[dict[str, Any]],
    *,
    stats: dict[str, Any],
    device: torch.device,
    batch_size: int,
    safety_threshold: Any,
    safety_penalty: float,
    opportunity_threshold: float,
    defer_threshold: float,
    confidence_margin: float,
    anti_escape_thresholds: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not rows:
        return {"sample_count": 0}, []
    additive_index = EXECUTABLE_RULE_IDS.index("additive_ltm")
    model.eval()
    all_records: list[dict[str, Any]] = []
    with torch.no_grad():
        for batch_rows in batched(rows, batch_size):
            batch = rows_to_batch(batch_rows, stats, device)
            outputs = model(batch)
            rule_scores = outputs["rule_score"].detach().cpu().tolist()
            harmful_probs = torch.sigmoid(outputs["harmful_logit"]).detach().cpu().tolist()
            opportunity_probs = torch.sigmoid(outputs["opportunity_logit"]).detach().cpu().tolist()
            defer_probs = torch.sigmoid(outputs["defer_logit"]).detach().cpu().tolist()
            for row, scores, harmful_prob, opportunity_prob, defer_prob in zip(
                batch_rows,
                rule_scores,
                harmful_probs,
                opportunity_probs,
                defer_probs,
            ):
                selection = select_attention_native(
                    [float(value) for value in scores],
                    [float(value) for value in harmful_prob],
                    opportunity_prob=float(opportunity_prob),
                    defer_prob=float(defer_prob),
                    safety_threshold=safety_threshold,
                    safety_penalty=safety_penalty,
                    opportunity_threshold=opportunity_threshold,
                    defer_threshold=defer_threshold,
                    confidence_margin=confidence_margin,
                )
                selected_index = int(selection["selected_index"])
                target_index = int(row["target"]["target_rule_index"])
                ranked = topk_indices(selection["scores"], len(EXECUTABLE_RULE_IDS))
                top3 = ranked[:3]
                deltas = [float(value) for value in row["probe_delta_vector"]]
                utilities = [float(value) for value in row["risk_adjusted_utility_vector"]]
                harmful_vector = [1 if value else 0 for value in row["probe_harmful_vector"]]
                use_nonadditive_target = row["decision_target"] == "use_nonadditive" and target_index >= 0
                all_records.append(
                    {
                        "split": row["split"],
                        "run_id": row["run_id"],
                        "checkpoint_id": row["checkpoint_id"],
                        "map_name": row["map_name"],
                        "agents": row["agents"],
                        "seed": row["seed"],
                        "iteration": row["iteration"],
                        "decision_target": row["decision_target"],
                        "selected_decision": selection["selected_decision"],
                        "target_rule": row["target_rule"],
                        "predicted_rule": EXECUTABLE_RULE_IDS[selected_index],
                        "fallback_reason": selection["fallback_reason"],
                        "defer_reason": selection["defer_reason"],
                        "selection_stage": selection["selection_stage"],
                        "attention_top1": bool(use_nonadditive_target and selected_index == target_index),
                        "attention_top3": bool(use_nonadditive_target and target_index in top3),
                        "decision_correct": row["decision_target"] == selection["selected_decision"],
                        "selected_delta": deltas[selected_index],
                        "additive_delta": deltas[additive_index],
                        "selected_vs_additive_delta": deltas[selected_index] - deltas[additive_index],
                        "selected_utility": utilities[selected_index],
                        "additive_utility": utilities[additive_index],
                        "selected_vs_additive_utility": utilities[selected_index] - utilities[additive_index],
                        "selected_rule_harmful": bool(harmful_vector[selected_index]),
                        "target_delta": deltas[target_index] if target_index >= 0 else 0.0,
                        "has_nonadditive_opportunity": bool(row["has_nonadditive_opportunity"]),
                        "has_high_margin_nonadditive_opportunity": bool(row["has_high_margin_nonadditive_opportunity"]),
                        "best_safe_nonadditive_advantage": float(row["best_safe_nonadditive_advantage"]),
                        "opportunity_margin": float(row["audit"]["label_params"].get("opportunity_margin", 0.010)),
                        "rule_scores": json.dumps([float(value) for value in selection["scores"]]),
                        "harmful_probs": json.dumps([float(value) for value in harmful_prob]),
                        "opportunity_prob": float(opportunity_prob),
                        "defer_prob": float(defer_prob),
                        "safety_threshold_by_rule": json.dumps(selection["safety_threshold_by_rule"]),
                        "safety_mask": json.dumps(selection["safety_mask"]),
                        "best_safe_nonadditive_rule": selection["best_safe_nonadditive_rule"],
                        "best_safe_nonadditive_score": selection["best_safe_nonadditive_score"],
                        "margin_vs_additive": selection["margin_vs_additive"],
                        "margin_vs_defer": selection["margin_vs_defer"],
                        "top3_rules": json.dumps([EXECUTABLE_RULE_IDS[index] for index in top3]),
                        "harmful_labels": json.dumps(harmful_vector),
                    }
                )
    labels: list[int] = []
    predictions: list[int] = []
    for record in all_records:
        harmful_probs = json.loads(record["harmful_probs"])
        harmful_labels = json.loads(record["harmful_labels"])
        labels.extend(int(value) for value in harmful_labels)
        predictions.extend(
            1 if float(value) >= safety_threshold_for_index(safety_threshold, index) else 0
            for index, value in enumerate(harmful_probs)
        )
    harmful = binary_metrics(labels, predictions)
    use_nonadditive_records = [
        record for record in all_records if record["decision_target"] == "use_nonadditive"
    ]
    selected_counts = Counter(str(record["predicted_rule"]) for record in all_records)
    decision_counts = Counter(str(record["selected_decision"]) for record in all_records)
    metrics = {
        "sample_count": len(all_records),
        "validation_non_neutral": len(use_nonadditive_records),
        "rule_top1_accuracy": _mean([1.0 if record["attention_top1"] else 0.0 for record in use_nonadditive_records]) or 0.0,
        "rule_top3_accuracy": _mean([1.0 if record["attention_top3"] else 0.0 for record in use_nonadditive_records]) or 0.0,
        "decision_accuracy": sum(1 for record in all_records if record["decision_correct"]) / len(all_records),
        "harmful_update_recall": harmful["recall"],
        "harmful_update_precision": harmful["precision"],
        "harmful_update_f1": harmful["f1"],
        "predicted_rule_validation_mean_delta_ratio": sum(float(record["selected_delta"]) for record in all_records) / len(all_records),
        "selected_vs_additive_delta_mean": sum(float(record["selected_vs_additive_delta"]) for record in all_records) / len(all_records),
        "selected_vs_additive_utility_mean": sum(float(record["selected_vs_additive_utility"]) for record in all_records) / len(all_records),
        "fallback_rate": sum(1 for record in all_records if record["fallback_reason"] != "selected") / len(all_records),
        "selected_rule_distribution": dict(sorted(selected_counts.items())),
        "decision_distribution": dict(sorted(decision_counts.items())),
        "target_decision_distribution": dict(sorted(Counter(str(record["decision_target"]) for record in all_records).items())),
        "opportunity_count": sum(1 for record in all_records if record["has_nonadditive_opportunity"]),
        "high_margin_opportunity_count": sum(1 for record in all_records if record["has_high_margin_nonadditive_opportunity"]),
    }
    metrics["attention_native_gate"] = attention_native_gate(metrics)
    metrics["anti_escape_gate"] = anti_escape_metrics(all_records, thresholds=anti_escape_thresholds)
    return metrics, all_records


def collect_harmful_rule_scores(
    model: Any,
    rows: list[dict[str, Any]],
    *,
    stats: dict[str, Any],
    device: torch.device,
    batch_size: int,
) -> list[dict[str, Any]]:
    model.eval()
    records: list[dict[str, Any]] = []
    with torch.no_grad():
        for batch_rows in batched(rows, batch_size):
            batch = rows_to_batch(batch_rows, stats, device)
            outputs = model(batch)
            harmful_probs = torch.sigmoid(outputs["harmful_logit"]).detach().cpu().tolist()
            for row, row_probs in zip(batch_rows, harmful_probs):
                labels = [1 if value else 0 for value in row["probe_harmful_vector"]]
                for index, (label, score) in enumerate(zip(labels, row_probs)):
                    records.append(
                        {
                            "rule_index": index,
                            "rule_id": EXECUTABLE_RULE_IDS[index],
                            "label": int(label),
                            "score": float(score),
                        }
                    )
    return records


def _binary_metrics_from_scores(records: list[dict[str, Any]], thresholds: list[float]) -> dict[str, float]:
    labels = [int(record["label"]) for record in records]
    predictions = [
        1 if float(record["score"]) >= float(thresholds[int(record["rule_index"])]) else 0
        for record in records
    ]
    return binary_metrics(labels, predictions)


def calibrate_rule_safety_thresholds_from_scores(
    records: list[dict[str, Any]],
    *,
    candidate_thresholds: list[float],
    min_recall: float = 0.80,
    min_precision: float = 0.30,
) -> dict[str, Any]:
    candidates = sorted({float(value) for value in candidate_thresholds}) or [0.5]
    thresholds = [0.5] * len(EXECUTABLE_RULE_IDS)
    per_rule: dict[str, Any] = {}
    for index, rule_id in enumerate(EXECUTABLE_RULE_IDS):
        rule_records = [record for record in records if int(record["rule_index"]) == index]
        positives = sum(int(record["label"]) for record in rule_records)
        if not rule_records or positives == 0:
            thresholds[index] = 1.01
            per_rule[rule_id] = {
                "threshold": thresholds[index],
                "positive_count": positives,
                "reason": "no_positive_train_labels",
                "precision": 0.0,
                "recall": 0.0,
            }
            continue
        scored: list[dict[str, Any]] = []
        for threshold in candidates:
            metrics = _binary_metrics_from_scores(rule_records, [threshold] * len(EXECUTABLE_RULE_IDS))
            scored.append({"threshold": threshold, **metrics})
        feasible = [
            item
            for item in scored
            if float(item["recall"]) >= float(min_recall)
            and float(item["precision"]) >= float(min_precision)
        ]
        if feasible:
            best = max(feasible, key=lambda item: (float(item["precision"]), float(item["recall"]), float(item["threshold"])))
            reason = "meets_rule_safety_targets"
        else:
            pool = [item for item in scored if float(item["recall"]) >= float(min_recall)] or scored
            best = max(pool, key=lambda item: (float(item["f1"]), float(item["recall"]), float(item["precision"])))
            reason = "best_available_rule_threshold"
        thresholds[index] = float(best["threshold"])
        per_rule[rule_id] = {
            "threshold": thresholds[index],
            "positive_count": positives,
            "reason": reason,
            "precision": float(best["precision"]),
            "recall": float(best["recall"]),
            "f1": float(best["f1"]),
        }
    aggregate = _binary_metrics_from_scores(records, thresholds)
    return {
        "schema_version": "phase4f_repair5_rule_safety_threshold_calibration_v1",
        "thresholds": thresholds,
        "threshold_by_rule": dict(zip(EXECUTABLE_RULE_IDS, thresholds)),
        "per_rule": per_rule,
        "train_metrics": aggregate,
        "candidate_thresholds": candidates,
        "min_recall": float(min_recall),
        "min_precision": float(min_precision),
    }


def calibrate_global_safety_threshold_from_scores(
    records: list[dict[str, Any]],
    *,
    candidate_thresholds: list[float],
    min_recall: float = 0.80,
    min_precision: float = 0.30,
) -> dict[str, Any]:
    candidates = sorted({float(value) for value in candidate_thresholds}) or [0.5]
    scored: list[dict[str, Any]] = []
    for threshold in candidates:
        metrics = _binary_metrics_from_scores(records, [threshold] * len(EXECUTABLE_RULE_IDS))
        scored.append({"threshold": threshold, **metrics})
    feasible = [
        item
        for item in scored
        if float(item["recall"]) >= float(min_recall)
        and float(item["precision"]) >= float(min_precision)
    ]
    if feasible:
        best = max(feasible, key=lambda item: (float(item["precision"]), float(item["recall"]), float(item["threshold"])))
        reason = "meets_global_safety_targets"
    else:
        pool = [item for item in scored if float(item["recall"]) >= float(min_recall)] or scored
        best = max(pool, key=lambda item: (float(item["f1"]), float(item["recall"]), float(item["precision"])))
        reason = "best_available_global_threshold"
    return {
        "schema_version": "phase4f_repair5_global_safety_threshold_calibration_v1",
        "threshold": float(best["threshold"]),
        "thresholds": [float(best["threshold"])] * len(EXECUTABLE_RULE_IDS),
        "train_metrics": {
            "precision": float(best["precision"]),
            "recall": float(best["recall"]),
            "f1": float(best["f1"]),
        },
        "reason": reason,
        "candidate_thresholds": candidates,
        "min_recall": float(min_recall),
        "min_precision": float(min_precision),
    }


def calibrate_safety_thresholds_from_scores(
    records: list[dict[str, Any]],
    *,
    candidate_thresholds: list[float],
    min_recall: float = 0.80,
    min_precision: float = 0.30,
    mode: str = "per_rule",
) -> dict[str, Any]:
    if str(mode) == "global":
        return calibrate_global_safety_threshold_from_scores(
            records,
            candidate_thresholds=candidate_thresholds,
            min_recall=min_recall,
            min_precision=min_precision,
        )
    return calibrate_rule_safety_thresholds_from_scores(
        records,
        candidate_thresholds=candidate_thresholds,
        min_recall=min_recall,
        min_precision=min_precision,
    )


def model_selection_score(validation: dict[str, Any]) -> float:
    gate = validation.get("attention_native_gate", {})
    anti = validation.get("anti_escape_gate", {})
    top1_ratio = min(float(validation.get("rule_top1_accuracy") or 0.0) / 0.35, 1.0)
    top3_ratio = min(float(validation.get("rule_top3_accuracy") or 0.0) / 0.70, 1.0)
    recall_ratio = min(float(validation.get("harmful_update_recall") or 0.0) / 0.80, 1.0)
    precision_ratio = min(float(validation.get("harmful_update_precision") or 0.0) / 0.30, 1.0)
    ranking_floor = min(top1_ratio, top3_ratio)
    safety_floor = min(recall_ratio, precision_ratio)
    anti_capture = min(float(anti.get("high_margin_nonadditive_capture_rate") or 0.0) / 0.40, 1.0)
    delta_score = max(-0.5, min(0.5, 100.0 * float(validation.get("selected_vs_additive_delta_mean") or 0.0)))
    gate_pass_count = sum(
        1
        for value in gate.values()
        if isinstance(value, dict) and bool(value.get("passed"))
    )
    return float(
        0.5 * gate_pass_count
        + 4.0 * safety_floor
        + 3.0 * ranking_floor
        + 1.0 * anti_capture
        + 0.5 * delta_score
        + (1.0 if gate.get("passed") else 0.0)
        + (1.0 if anti.get("passed") and safety_floor >= 0.95 and ranking_floor >= 0.95 else 0.0)
    )


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
    gate = validation.get("attention_native_gate", {})
    anti = validation.get("anti_escape_gate", {})
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair5 Attention-Native Train Report\n\n")
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
        handle.write(f"- epochs: `{summary['epochs']}`\n\n")
        handle.write("## Validation Metrics\n\n")
        handle.write(f"- attention top1: `{validation.get('rule_top1_accuracy')}`\n")
        handle.write(f"- attention top3: `{validation.get('rule_top3_accuracy')}`\n")
        handle.write(f"- decision accuracy: `{validation.get('decision_accuracy')}`\n")
        handle.write(f"- harmful recall: `{validation.get('harmful_update_recall')}`\n")
        handle.write(f"- harmful precision: `{validation.get('harmful_update_precision')}`\n")
        handle.write(f"- mean selected delta: `{validation.get('predicted_rule_validation_mean_delta_ratio')}`\n")
        handle.write(f"- selected-vs-additive delta: `{validation.get('selected_vs_additive_delta_mean')}`\n")
        handle.write(f"- selected rules: `{validation.get('selected_rule_distribution')}`\n")
        handle.write(f"- decisions: `{validation.get('decision_distribution')}`\n\n")
        handle.write("## Attention-Native Gate\n\n")
        for key, value in gate.items():
            if key == "passed" or not isinstance(value, dict):
                continue
            handle.write(
                f"- {key}: `{value.get('value')}` vs `{value.get('threshold')}` -> "
                f"{'pass' if value.get('passed') else 'fail'}\n"
            )
        handle.write(f"\nOverall: `{'pass' if gate.get('passed') else 'fail'}`\n\n")
        handle.write("## Anti-Escape Gate\n\n")
        for key, value in anti.get("checks", {}).items():
            handle.write(
                f"- {key}: `{value.get('value')}` vs `{value.get('threshold')}` -> "
                f"{'pass' if value.get('passed') else 'fail'}\n"
            )
        handle.write(f"\nOverall: `{'pass' if anti.get('passed') else 'fail'}`\n")
        handle.write(f"Reason: `{anti.get('reason')}`\n\n")
        handle.write("## Boundary\n\n")
        handle.write(
            "This is offline Repair5 evidence only. Phase5.5 runtime is forbidden until "
            "original Phase4F, attention-native, safety, anti-escape, and multi-seed gates all pass.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--model-output-dir", type=Path)
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--summary-csv", type=Path)
    parser.add_argument(
        "--model-name",
        choices=[SET_RULE_TRANSFORMER_NAME, EDGE_TRACE_TRANSFORMER_NAME, HIER_EDGE_TRACE_TRANSFORMER_NAME],
    )
    parser.add_argument("--seed", type=int)
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    config_path = resolve_path(args.config, root)
    config = load_config(config_path)
    native = config.get("attention_native", {}) if isinstance(config.get("attention_native"), dict) else {}
    train_config = config_get(config, "attention_native", "training", default={}) or {}
    model_config = config_get(config, "attention_native", "model", default={}) or {}
    eval_config = config_get(config, "attention_native", "eval", default={}) or {}
    loss_config = config_get(config, "attention_native", "loss", default={}) or {}
    curriculum_config = config_get(config, "attention_native", "curriculum", default={}) or {}
    gate_config = config.get("gate", {}) if isinstance(config.get("gate"), dict) else {}
    anti_thresholds = config.get("anti_escape", {}) if isinstance(config.get("anti_escape"), dict) else {}

    seed = int(args.seed if args.seed is not None else train_config.get("seed", 61))
    random.seed(seed)
    torch.manual_seed(seed)
    dataset_path = resolve_path(args.dataset or native.get("dataset_jsonl"), root)
    model_output_dir = resolve_path(args.model_output_dir or train_config.get("model_output_dir"), root, seed=seed)
    model_path = resolve_path(args.model_path or train_config.get("model_path"), root, seed=seed)
    report_path = resolve_path(args.report or train_config.get("train_report_md"), root, seed=seed)
    summary_json_path = resolve_path(args.summary_json or train_config.get("train_summary_json"), root, seed=seed)
    summary_csv_path = resolve_path(args.summary_csv or train_config.get("train_summary_csv"), root, seed=seed)
    if model_path is None and model_output_dir is not None:
        model_path = model_output_dir / "laur_attention_native_v1.pt"
    if None in (dataset_path, model_path, report_path, summary_json_path, summary_csv_path):
        raise ValueError("dataset/model/report/summary paths are required")
    assert dataset_path and model_path and report_path and summary_json_path and summary_csv_path

    rows = read_jsonl(dataset_path)
    validate_rows(rows)
    splits = split_rows(rows)
    train_rows = splits.get("train", [])
    stats = feature_stats(train_rows)
    device_name = args.device or train_config.get("device", "auto")
    if device_name == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(device_name)

    model_name = args.model_name or model_config.get("name", SET_RULE_TRANSFORMER_NAME)
    model_args = {
        "global_dim": len(GLOBAL_FEATURE_NAMES),
        "edge_dim": len(EDGE_FEATURE_NAMES),
        "trace_dim": len(TRACE_FEATURE_NAMES),
        "rule_dim": len(RULE_FEATURE_NAMES),
        "num_rules": len(EXECUTABLE_RULE_IDS),
        "num_families": len(RULE_FAMILY_IDS),
        "d_model": int(model_config.get("d_model", 64 if model_name == SET_RULE_TRANSFORMER_NAME else 96)),
        "n_heads": int(model_config.get("n_heads", 2 if model_name == SET_RULE_TRANSFORMER_NAME else 4)),
        "n_layers": int(model_config.get("n_layers", 2)),
        "dropout": float(model_config.get("dropout", 0.1)),
        "head_hidden_dim": int(model_config.get("head_hidden_dim", 0)),
        "head_dropout": float(model_config.get("head_dropout", model_config.get("dropout", 0.1))),
    }
    model = build_model(model_name, **model_args).to(device)
    epochs = int(args.epochs or train_config.get("epochs", 120))
    batch_size = int(args.batch_size or train_config.get("batch_size", 128))
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(train_config.get("learning_rate", 0.001)),
        weight_decay=float(train_config.get("weight_decay", 0.0005)),
    )
    positives = sum(int(value) for row in train_rows for value in row["probe_harmful_vector"])
    total_harm = len(train_rows) * len(EXECUTABLE_RULE_IDS)
    harmful_pos_weight = (total_harm - positives) / max(1, positives)
    opp_pos = sum(1 for row in train_rows if row["has_nonadditive_opportunity"])
    opportunity_pos_weight = (len(train_rows) - opp_pos) / max(1, opp_pos)
    additive_index = EXECUTABLE_RULE_IDS.index("additive_ltm")
    safety_threshold: Any = float(eval_config.get("safety_threshold", 0.10))
    best_score = -1.0e9
    best_state: dict[str, Any] | None = None
    history: list[dict[str, Any]] = []
    start = time.time()
    for epoch in range(1, epochs + 1):
        model.train()
        epoch_losses: Counter[str] = Counter()
        batch_count = 0
        epoch_loss_config = loss_config_for_epoch(loss_config, curriculum_config, epoch)
        loss_weights = make_loss_weights(
            epoch_loss_config,
            harmful_pos_weight=harmful_pos_weight,
            opportunity_pos_weight=opportunity_pos_weight,
        )
        epoch_rows = sample_epoch_rows(train_rows, train_config, root)
        for batch_rows in batched(epoch_rows, batch_size, shuffle=True):
            batch = rows_to_batch(batch_rows, stats, device)
            optimizer.zero_grad(set_to_none=True)
            outputs = model(batch)
            loss_parts = laur_attention_native_loss(
                outputs,
                batch,
                additive_index=additive_index,
                weights=loss_weights,
            )
            loss_parts["total"].backward()
            optimizer.step()
            batch_count += 1
            for key, value in loss_parts.items():
                epoch_losses[key] += float(value.detach().cpu())
        eval_interval = int(train_config.get("eval_interval", 20))
        if epoch == 1 or epoch == epochs or epoch % eval_interval == 0:
            eval_safety_threshold: Any = safety_threshold
            eval_safety_calibration = None
            if bool(train_config.get("model_selection_calibrate_safety", False)):
                calibration_grid = [
                    float(value)
                    for value in eval_config.get(
                        "safety_calibration_thresholds",
                        [0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80],
                    )
                ]
                eval_safety_calibration = calibrate_safety_thresholds_from_scores(
                    collect_harmful_rule_scores(model, train_rows, stats=stats, device=device, batch_size=batch_size),
                    candidate_thresholds=calibration_grid,
                    min_recall=float(gate_config.get("harmful_recall_min", 0.80)),
                    min_precision=float(gate_config.get("harmful_precision_min", 0.30)),
                    mode=str(eval_config.get("safety_calibration_mode", "per_rule")),
                )
                eval_safety_threshold = list(eval_safety_calibration["thresholds"])
            metrics, _records = evaluate_model(
                model,
                splits.get("validation", []),
                stats=stats,
                device=device,
                batch_size=batch_size,
                safety_threshold=eval_safety_threshold,
                safety_penalty=float(eval_config.get("safety_penalty", 0.02)),
                opportunity_threshold=float(eval_config.get("opportunity_threshold", 0.50)),
                defer_threshold=float(eval_config.get("defer_threshold", 0.50)),
                confidence_margin=float(eval_config.get("confidence_margin", 0.002)),
                anti_escape_thresholds=anti_thresholds,
            )
            score = model_selection_score(metrics)
            history.append(
                {
                    "epoch": epoch,
                    "score": score,
                    "loss": epoch_losses["total"] / max(1, batch_count),
                    "curriculum_stage": epoch_loss_config.get("_curriculum_stage", "base"),
                    "validation_top1": metrics.get("rule_top1_accuracy"),
                    "validation_top3": metrics.get("rule_top3_accuracy"),
                    "harmful_recall": metrics.get("harmful_update_recall"),
                    "harmful_precision": metrics.get("harmful_update_precision"),
                    "anti_escape_capture": metrics.get("anti_escape_gate", {}).get("high_margin_nonadditive_capture_rate"),
                    "anti_escape_passed": metrics.get("anti_escape_gate", {}).get("passed"),
                    "model_selection_calibrated_safety": bool(eval_safety_calibration is not None),
                }
            )
            print(json.dumps(history[-1], sort_keys=True), flush=True)
            if score > best_score:
                best_score = score
                best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    if best_state is not None:
        model.load_state_dict(best_state)

    safety_calibration = None
    effective_safety_threshold: Any = safety_threshold
    if bool(eval_config.get("calibrate_safety_thresholds", True)):
        calibration_grid = [
            float(value)
            for value in eval_config.get(
                "safety_calibration_thresholds",
                [0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80],
            )
        ]
        safety_calibration = calibrate_safety_thresholds_from_scores(
            collect_harmful_rule_scores(model, train_rows, stats=stats, device=device, batch_size=batch_size),
            candidate_thresholds=calibration_grid,
            min_recall=float(gate_config.get("harmful_recall_min", 0.80)),
            min_precision=float(gate_config.get("harmful_precision_min", 0.30)),
            mode=str(eval_config.get("safety_calibration_mode", "per_rule")),
        )
        effective_safety_threshold = list(safety_calibration["thresholds"])

    metrics_by_split: dict[str, dict[str, Any]] = {}
    all_records: list[dict[str, Any]] = []
    for split_name, split_values in sorted(splits.items()):
        metrics, records = evaluate_model(
            model,
            split_values,
            stats=stats,
            device=device,
            batch_size=batch_size,
            safety_threshold=effective_safety_threshold,
            safety_penalty=float(eval_config.get("safety_penalty", 0.02)),
            opportunity_threshold=float(eval_config.get("opportunity_threshold", 0.50)),
            defer_threshold=float(eval_config.get("defer_threshold", 0.50)),
            confidence_margin=float(eval_config.get("confidence_margin", 0.002)),
            anti_escape_thresholds=anti_thresholds,
        )
        metrics_by_split[split_name] = metrics
        all_records.extend(records)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "schema_version": MODEL_SCHEMA_VERSION,
            "model_name": model_name,
            "model_args": model_args,
            "model_state_dict": model.state_dict(),
            "feature_stats": stats,
            "rule_vocab": list(EXECUTABLE_RULE_IDS),
            "safety_threshold": safety_threshold,
            "effective_safety_threshold": effective_safety_threshold,
            "safety_calibration": safety_calibration,
            "selection": {
                "safety_penalty": float(eval_config.get("safety_penalty", 0.02)),
                "opportunity_threshold": float(eval_config.get("opportunity_threshold", 0.50)),
                "defer_threshold": float(eval_config.get("defer_threshold", 0.50)),
                "confidence_margin": float(eval_config.get("confidence_margin", 0.002)),
            },
        },
        model_path,
    )
    write_csv(summary_csv_path, all_records)
    summary = {
        "schema_version": "phase4f_repair5_attention_native_train_summary_v1",
        "dataset": str(dataset_path),
        "model_path": str(model_path),
        "model_name": model_name,
        "model_args": model_args,
        "parameter_count": parameter_count(model),
        "seed": seed,
        "epochs": epochs,
        "batch_size": batch_size,
        "device": str(device),
        "sampler": train_config.get("sampler", "uniform"),
        "curriculum": curriculum_config,
        "training_time_sec": time.time() - start,
        "history": history,
        "safety_calibration": safety_calibration,
        "effective_safety_threshold": effective_safety_threshold,
        "metrics_by_split": metrics_by_split,
        "phase4f_gate": metrics_by_split.get("validation", {}).get("attention_native_gate", {}),
        "anti_escape_gate": metrics_by_split.get("validation", {}).get("anti_escape_gate", {}),
        "runtime_allowed": False,
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
    }
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report_path, root=root, summary=summary)
    print(json.dumps({"summary_json": str(summary_json_path), "report": str(report_path), "model": str(model_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

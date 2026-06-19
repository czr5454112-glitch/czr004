"""Metrics for G5.58 local/server learnability evidence."""

from __future__ import annotations

from typing import Any

import numpy as np


def binary_accuracy(pred: np.ndarray, target: np.ndarray) -> float:
    return float(((pred >= 0.5) == (target >= 0.5)).mean()) if len(target) else 0.0


def ranking_accuracy(scores: np.ndarray, quality_delta: np.ndarray, margin: float = 1.0e-3) -> float:
    if len(scores) < 2:
        return 1.0
    good = 0
    total = 0
    for i in range(len(scores)):
        for j in range(i + 1, len(scores)):
            if abs(float(quality_delta[i]) - float(quality_delta[j])) < margin:
                continue
            total += 1
            good += int((scores[i] > scores[j]) == (quality_delta[i] < quality_delta[j]))
    return good / max(1, total)


def topk_safe_recall(scores: np.ndarray, safe: np.ndarray, k: int = 5) -> float:
    if safe.sum() == 0:
        return 1.0
    idx = np.argsort(-scores)[: min(k, len(scores))]
    return float(safe[idx].sum() / max(1, min(int(safe.sum()), k)))


def fallback_accuracy(predicted_fallback_prob: np.ndarray, fallback_required: np.ndarray, threshold: float = 0.5) -> float:
    pred = np.asarray(predicted_fallback_prob) >= threshold
    target = np.asarray(fallback_required).astype(bool)
    return float((pred == target).mean()) if target.size else 0.0


def generator_safe_set_hit_rate(generated_theta_ids: list[list[str]], safe_theta_ids: list[set[str]]) -> float:
    eligible = [(generated, safe) for generated, safe in zip(generated_theta_ids, safe_theta_ids) if safe]
    if not eligible:
        return 0.0
    hits = 0
    for generated, safe in eligible:
        hits += bool(set(map(str, generated)) & set(map(str, safe)))
    return hits / max(1, len(eligible))


def safe_recall_at_k(scores: np.ndarray, safe: np.ndarray, k: int = 5) -> float:
    scores = np.asarray(scores)
    safe = np.asarray(safe).astype(bool)
    if safe.size == 0 or safe.sum() == 0:
        return 0.0
    idx = np.argsort(-scores)[: min(k, len(scores))]
    return float(safe[idx].sum() / safe.sum())


def coverage_risk(rows: list[dict[str, Any]], thresholds: list[float]) -> list[dict[str, Any]]:
    out = []
    for threshold in thresholds:
        selected = [row for row in rows if float(row.get("model_confidence", row.get("confidence", 0.0))) >= threshold]
        regressions = sum(1 for row in selected if row.get("success_regression"))
        better = sum(1 for row in selected if float(row.get("quality_delta_vs_g556", 0.0)) < 0.0)
        worse = sum(1 for row in selected if float(row.get("quality_delta_vs_g556", 0.0)) > 0.0)
        out.append(
            {
                "threshold": threshold,
                "coverage": len(selected) / max(1, len(rows)),
                "success_regression_rate": regressions / max(1, len(selected)),
                "mean_quality_delta": float(np.mean([float(r.get("quality_delta_vs_g556", 0.0)) for r in selected])) if selected else 0.0,
                "better_count": better,
                "worse_count": worse,
            }
        )
    return out

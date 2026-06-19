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


def coverage_risk(rows: list[dict[str, Any]], thresholds: list[float]) -> list[dict[str, Any]]:
    out = []
    for threshold in thresholds:
        selected = [row for row in rows if float(row.get("confidence", 0.0)) >= threshold]
        regressions = sum(1 for row in selected if row.get("success_regression"))
        out.append(
            {
                "threshold": threshold,
                "coverage": len(selected) / max(1, len(rows)),
                "success_regression_rate": regressions / max(1, len(selected)),
                "mean_quality_delta": float(np.mean([float(r.get("quality_delta_vs_g556", 0.0)) for r in selected])) if selected else 0.0,
            }
        )
    return out

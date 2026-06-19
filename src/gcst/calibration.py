"""Simple calibration helpers."""

from __future__ import annotations

import numpy as np


def expected_calibration_error(prob: np.ndarray, target: np.ndarray, bins: int = 10) -> float:
    if len(prob) == 0:
        return 0.0
    prob = np.asarray(prob, dtype=float)
    target = np.asarray(target, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (prob >= lo) & (prob < hi if hi < 1 else prob <= hi)
        if not mask.any():
            continue
        ece += float(mask.mean()) * abs(float(prob[mask].mean()) - float(target[mask].mean()))
    return ece

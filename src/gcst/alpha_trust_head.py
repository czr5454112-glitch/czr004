"""Conservative alpha blending helpers for tail-risk response panels."""

from __future__ import annotations

from typing import Iterable

import numpy as np

from .theta_schema import BASELINE_G556, THETA_NUMERIC_COLUMNS, clamp_theta_row, mode_columns


def alpha_blend_theta(target: np.ndarray, alpha: float) -> dict[str, float | int]:
    target_arr = np.asarray(target, dtype=np.float32)
    theta = np.asarray(BASELINE_G556, dtype=np.float32) * (1.0 - float(alpha)) + target_arr * float(alpha)
    row = {col: float(theta[idx]) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)}
    row.update(mode_columns("flow_shield"))
    return clamp_theta_row(row)


def alpha_grid(alphas: Iterable[float]) -> list[float]:
    clean = sorted({round(float(alpha), 6) for alpha in alphas})
    return [alpha for alpha in clean if 0.0 <= alpha <= 1.0]

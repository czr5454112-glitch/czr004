"""Loss-geometry and oracle helpers for G5.64.

These utilities keep three ideas separate:
1. Set-valued positive supervision has a non-zero softmin floor.
2. Harmful rows are nearest-neighbor exclusions, not averaged-away negatives.
3. Per-context theta oracles must optimize directly in theta space with
   projection, not through a sigmoid parameterization that hides bounds issues.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Sequence

import numpy as np

from .label_v52_set import LabelV52Context
from .theta_schema import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS, clamp_numeric_theta


THETA_SPAN = np.maximum(THETA_HI - THETA_LO, 1.0e-6).astype(np.float32)


@dataclass(frozen=True)
class AdaptiveMargin:
    requested_margin: float
    feasible_margin: float
    nearest_positive_harmful_distance: float | None
    feasible: bool


def normalized_theta_distance_np(theta: np.ndarray, candidates: np.ndarray) -> np.ndarray:
    theta_arr = np.asarray(theta, dtype=np.float32).reshape(1, -1)
    cand = np.asarray(candidates, dtype=np.float32)
    if cand.size == 0:
        return np.zeros((0,), dtype=np.float32)
    if cand.ndim == 1:
        cand = cand.reshape(1, -1)
    return np.mean(np.abs((theta_arr - cand) / THETA_SPAN), axis=1).astype(np.float32)


def _weights(count: int, values: np.ndarray | None = None) -> np.ndarray:
    if values is None or values.size == 0:
        out = np.ones((count,), dtype=np.float32)
    else:
        out = np.asarray(values, dtype=np.float32).reshape(-1)
        if out.shape[0] != count:
            out = np.ones((count,), dtype=np.float32)
    total = float(out.sum())
    if total <= 0 or not math.isfinite(total):
        return np.ones((count,), dtype=np.float32) / max(1, count)
    return (out / total).astype(np.float32)


def positive_softmin_loss_np(
    theta: np.ndarray,
    positive_thetas: np.ndarray,
    weights: np.ndarray | None = None,
    tau: float = 0.05,
) -> float:
    positives = np.asarray(positive_thetas, dtype=np.float32)
    if positives.size == 0:
        return 0.0
    if positives.ndim == 1:
        positives = positives.reshape(1, -1)
    distances = normalized_theta_distance_np(theta, positives).astype(np.float64)
    w = _weights(len(distances), weights).astype(np.float64)
    scaled = np.log(np.maximum(w, 1.0e-12)) - distances / float(tau)
    m = float(np.max(scaled))
    return float(-float(tau) * (m + np.log(np.exp(scaled - m).sum())))


def positive_softmin_floor(
    positive_thetas: np.ndarray,
    weights: np.ndarray | None = None,
    tau: float = 0.05,
) -> float:
    positives = np.asarray(positive_thetas, dtype=np.float32)
    if positives.size == 0:
        return 0.0
    if positives.ndim == 1:
        positives = positives.reshape(1, -1)
    return min(positive_softmin_loss_np(theta, positives, weights, tau=tau) for theta in positives)


def floor_corrected_positive_loss_np(
    theta: np.ndarray,
    positive_thetas: np.ndarray,
    weights: np.ndarray | None = None,
    tau: float = 0.05,
) -> float:
    return positive_softmin_loss_np(theta, positive_thetas, weights, tau=tau) - positive_softmin_floor(
        positive_thetas,
        weights,
        tau=tau,
    )


def positive_wta_loss_np(theta: np.ndarray, positive_thetas: np.ndarray) -> float:
    distances = normalized_theta_distance_np(theta, positive_thetas)
    return float(distances.min()) if distances.size else 0.0


def nearest_harmful_repulsion_loss_np(theta: np.ndarray, harmful_thetas: np.ndarray, margin: float = 0.12) -> float:
    distances = normalized_theta_distance_np(theta, harmful_thetas)
    if not distances.size:
        return 0.0
    return float(max(0.0, float(margin) - float(distances.min())))


def adaptive_harmful_margin(
    positive_thetas: np.ndarray,
    harmful_thetas: np.ndarray,
    requested_margin: float = 0.12,
) -> AdaptiveMargin:
    positives = np.asarray(positive_thetas, dtype=np.float32)
    harmful = np.asarray(harmful_thetas, dtype=np.float32)
    if positives.size == 0 or harmful.size == 0:
        return AdaptiveMargin(float(requested_margin), float(requested_margin), None, True)
    if positives.ndim == 1:
        positives = positives.reshape(1, -1)
    if harmful.ndim == 1:
        harmful = harmful.reshape(1, -1)
    nearest = min(float(normalized_theta_distance_np(pos, harmful).min()) for pos in positives)
    feasible = nearest > 1.0e-8
    margin = min(float(requested_margin), max(0.0, nearest * 0.50))
    return AdaptiveMargin(float(requested_margin), margin, nearest, feasible)


def conflicting_theta_pairs(
    context: LabelV52Context,
    *,
    distance_threshold: float = 0.015,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    positives = context.positive_candidates
    harmful = context.harmful_candidates
    for pos in positives:
        distances = normalized_theta_distance_np(pos.theta, context.harmful_thetas)
        for idx, distance in enumerate(distances.tolist()):
            if float(distance) <= float(distance_threshold):
                bad = harmful[idx]
                rows.append(
                    {
                        "evaluation_uid": context.evaluation_uid,
                        "positive_row_uid": pos.row_uid,
                        "harmful_row_uid": bad.row_uid,
                        "positive_state": pos.row_state,
                        "harmful_state": bad.row_state,
                        "normalized_theta_distance": float(distance),
                        "positive_quality_delta_vs_g556": pos.quality_delta_vs_g556,
                        "harmful_quality_delta_vs_g556": bad.quality_delta_vs_g556,
                        "conflict_distance_threshold": float(distance_threshold),
                    }
                )
    return rows


def context_loss_geometry(
    context: LabelV52Context,
    *,
    tau: float = 0.05,
    requested_harmful_margin: float = 0.12,
    conflict_distance_threshold: float = 0.015,
) -> dict[str, Any]:
    positives = context.positive_thetas
    harmful = context.harmful_thetas
    baseline = context.baseline_theta
    adaptive = adaptive_harmful_margin(positives, harmful, requested_margin=requested_harmful_margin)
    conflicts = conflicting_theta_pairs(context, distance_threshold=conflict_distance_threshold)
    positive_floor = positive_softmin_floor(positives, context.positive_weights, tau=tau)
    baseline_softmin = positive_softmin_loss_np(baseline, positives, context.positive_weights, tau=tau)
    baseline_floor_corrected = baseline_softmin - positive_floor
    nearest_positive = normalized_theta_distance_np(baseline, positives)
    nearest_harmful = normalized_theta_distance_np(baseline, harmful)
    return {
        "evaluation_uid": context.evaluation_uid,
        "label_state": context.label_state,
        "positive_rows": len(context.positive_candidates),
        "safe_rows": len(context.safe_candidates),
        "harmful_rows": len(context.harmful_candidates),
        "censored_rows": len(context.censored_candidates),
        "softmin_tau": float(tau),
        "positive_softmin_floor": float(positive_floor),
        "baseline_positive_softmin_loss": float(baseline_softmin),
        "baseline_floor_corrected_positive_loss": float(baseline_floor_corrected),
        "baseline_wta_positive_loss": float(nearest_positive.min()) if nearest_positive.size else 0.0,
        "baseline_nearest_harmful_distance": float(nearest_harmful.min()) if nearest_harmful.size else None,
        "requested_harmful_margin": float(requested_harmful_margin),
        "adaptive_harmful_margin": float(adaptive.feasible_margin),
        "nearest_positive_harmful_distance": adaptive.nearest_positive_harmful_distance,
        "adaptive_margin_feasible": adaptive.feasible,
        "conflicting_theta_pair_count": len(conflicts),
        "has_conflicting_near_duplicate": bool(conflicts),
        "censored_rows_are_negative": False,
    }


def summarize_geometry_rows(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    conflict_contexts = [row for row in rows if int(row.get("conflicting_theta_pair_count", 0)) > 0]
    positive_rows = [row for row in rows if int(row.get("positive_rows", 0)) > 0]
    values = [float(row.get("baseline_floor_corrected_positive_loss", 0.0)) for row in positive_rows]
    return {
        "schema_version": "phase5p5_repair5g564_loss_geometry_summary_v1",
        "contexts": len(rows),
        "positive_contexts": len(positive_rows),
        "conflict_contexts": len(conflict_contexts),
        "conflict_context_rate": len(conflict_contexts) / max(1, len(rows)),
        "median_baseline_floor_corrected_positive_loss": float(np.median(values)) if values else 0.0,
        "max_baseline_floor_corrected_positive_loss": float(np.max(values)) if values else 0.0,
        "softmin_floor_computed": True,
        "censored_rows_are_negative": False,
    }


def repaired_context_loss_np(
    theta: np.ndarray,
    context: LabelV52Context,
    *,
    tau: float = 0.05,
    harmful_margin: float | None = None,
    trust_weight: float = 0.01,
) -> float:
    theta = clamp_numeric_theta(theta)
    total = 0.0
    if len(context.positive_candidates):
        total += max(0.0, floor_corrected_positive_loss_np(theta, context.positive_thetas, context.positive_weights, tau=tau))
    if len(context.harmful_candidates):
        margin = harmful_margin
        if margin is None:
            margin = adaptive_harmful_margin(context.positive_thetas, context.harmful_thetas).feasible_margin
        total += nearest_harmful_repulsion_loss_np(theta, context.harmful_thetas, margin=float(margin))
    if not len(context.positive_candidates):
        total += float(trust_weight) * float(normalized_theta_distance_np(theta, BASELINE_G556).mean())
    return float(total)


class ProjectedThetaOracle:
    """Small direct theta optimizer used by tests and per-context oracle scripts."""

    init_source = "g556"
    uses_sigmoid_parameterization = False
    weight_decay = 0.0

    def __init__(self, initial_theta: np.ndarray | None = None, *, lr: float = 0.05, device: str = "cpu") -> None:
        import torch

        start = BASELINE_G556 if initial_theta is None else np.asarray(initial_theta, dtype=np.float32)
        self.device = device
        self.theta = torch.nn.Parameter(torch.as_tensor(clamp_numeric_theta(start), dtype=torch.float32, device=device))
        self.optimizer = torch.optim.AdamW([self.theta], lr=float(lr), weight_decay=0.0)

    def project_(self) -> None:
        import torch

        lo = torch.as_tensor(THETA_LO, dtype=self.theta.dtype, device=self.theta.device)
        hi = torch.as_tensor(THETA_HI, dtype=self.theta.dtype, device=self.theta.device)
        with torch.no_grad():
            self.theta.clamp_(lo, hi)

    def step(self, loss_fn: Callable[[Any], Any]) -> float:
        self.optimizer.zero_grad(set_to_none=True)
        loss = loss_fn(self.theta)
        loss.backward()
        self.optimizer.step()
        self.project_()
        return float(loss.detach().cpu())

    def theta_numpy(self) -> np.ndarray:
        return self.theta.detach().cpu().numpy().astype(np.float32)


def theta_row(theta: np.ndarray, prefix: str = "") -> dict[str, float]:
    return {f"{prefix}{col}": float(value) for col, value in zip(THETA_NUMERIC_COLUMNS, theta)}

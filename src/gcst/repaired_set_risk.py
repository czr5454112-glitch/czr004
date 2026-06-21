"""Canonical repaired set-valued risk for G5.65.

The same configuration is used by parameter oracles, actors, controls,
scaling, retraining, and offline reports.  This replaces the G5.64 split where
the oracle optimized a repaired floor-corrected objective while the actor still
trained with the older raw set-valued loss.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Sequence

import numpy as np

from .label_v52_set import (
    CENSORED_UNKNOWN,
    HARMFUL_SUPPORTED,
    MIXED_FRONTIER,
    POSITIVE_SUPPORTED,
    SAFE_NONIMPROVING_SUPPORTED,
    LabelV52Context,
)
from .theta_schema import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS, clamp_numeric_theta


THETA_SPAN = np.maximum(THETA_HI - THETA_LO, 1.0e-6).astype(np.float32)


@dataclass(frozen=True)
class RepairedRiskConfig:
    schema_version: str = "phase5p5_repair5g565_repaired_set_risk_config_v1"
    positive_loss: str = "floor_corrected_softmin"  # floor_corrected_softmin | hard_wta | clustered_medoid_wta
    harmful_loss: str = "nearest_adaptive"  # nearest_adaptive | topk_cvar_adaptive
    tau: float = 0.05
    requested_harmful_margin: float = 0.12
    topk_harmful: int = 3
    cvar_quantile: float = 0.80
    censored_trust_weight: float = 0.01
    censored_support_margin: float = 0.35
    safe_nonimproving_trust_weight: float = 0.05
    safe_nonimproving_support_margin: float = 0.20
    cluster_distance: float = 0.025
    context_balance: str = "context_mean"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def sha256(self) -> str:
        text = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


DEFAULT_REPAIRED_RISK = RepairedRiskConfig()


def normalized_theta_distance_np(theta: np.ndarray, candidates: np.ndarray) -> np.ndarray:
    theta_arr = np.asarray(theta, dtype=np.float32).reshape(1, -1)
    cand = np.asarray(candidates, dtype=np.float32)
    if cand.size == 0:
        return np.zeros((0,), dtype=np.float32)
    if cand.ndim == 1:
        cand = cand.reshape(1, -1)
    return np.mean(np.abs((theta_arr - cand) / THETA_SPAN), axis=1).astype(np.float32)


def _weights(count: int, values: np.ndarray | None = None) -> np.ndarray:
    if values is None or np.asarray(values).size == 0:
        raw = np.ones((count,), dtype=np.float32)
    else:
        raw = np.asarray(values, dtype=np.float32).reshape(-1)
        if raw.shape[0] != count:
            raw = np.ones((count,), dtype=np.float32)
    total = float(raw.sum())
    if total <= 0.0 or not math.isfinite(total):
        return np.ones((count,), dtype=np.float32) / max(1, count)
    return (raw / total).astype(np.float32)


def positive_softmin_np(theta: np.ndarray, positive_thetas: np.ndarray, weights: np.ndarray | None, tau: float) -> float:
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


def positive_softmin_floor_np(positive_thetas: np.ndarray, weights: np.ndarray | None, tau: float) -> float:
    positives = np.asarray(positive_thetas, dtype=np.float32)
    if positives.size == 0:
        return 0.0
    if positives.ndim == 1:
        positives = positives.reshape(1, -1)
    return min(positive_softmin_np(theta, positives, weights, tau) for theta in positives)


def hard_wta_positive_np(theta: np.ndarray, positive_thetas: np.ndarray) -> float:
    distances = normalized_theta_distance_np(theta, positive_thetas)
    return float(distances.min()) if distances.size else 0.0


def clustered_medoid_indices_np(thetas: np.ndarray, *, distance_threshold: float = 0.025) -> list[int]:
    arr = np.asarray(thetas, dtype=np.float32)
    if arr.size == 0:
        return []
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    remaining = set(range(arr.shape[0]))
    medoids: list[int] = []
    while remaining:
        seed = min(remaining)
        distances = normalized_theta_distance_np(arr[seed], arr)
        cluster = sorted(idx for idx in remaining if float(distances[idx]) <= float(distance_threshold))
        if not cluster:
            cluster = [seed]
        sub = arr[cluster]
        costs = []
        for local_idx, theta in enumerate(sub):
            costs.append(float(normalized_theta_distance_np(theta, sub).mean()))
        medoids.append(cluster[int(np.argmin(costs))])
        remaining -= set(cluster)
    return medoids


def clustered_medoid_wta_np(theta: np.ndarray, positive_thetas: np.ndarray, *, distance_threshold: float) -> float:
    positives = np.asarray(positive_thetas, dtype=np.float32)
    if positives.size == 0:
        return 0.0
    if positives.ndim == 1:
        positives = positives.reshape(1, -1)
    medoids = positives[clustered_medoid_indices_np(positives, distance_threshold=distance_threshold)]
    return hard_wta_positive_np(theta, medoids)


def adaptive_margin_np(positive_thetas: np.ndarray, harmful_thetas: np.ndarray, requested_margin: float) -> tuple[float, float | None]:
    positives = np.asarray(positive_thetas, dtype=np.float32)
    harmful = np.asarray(harmful_thetas, dtype=np.float32)
    if positives.size == 0 or harmful.size == 0:
        return float(requested_margin), None
    if positives.ndim == 1:
        positives = positives.reshape(1, -1)
    if harmful.ndim == 1:
        harmful = harmful.reshape(1, -1)
    nearest = min(float(normalized_theta_distance_np(pos, harmful).min()) for pos in positives)
    return min(float(requested_margin), max(0.0, nearest * 0.50)), nearest


def harmful_hinge_np(theta: np.ndarray, positive_thetas: np.ndarray, harmful_thetas: np.ndarray, cfg: RepairedRiskConfig) -> tuple[float, dict[str, Any]]:
    harmful = np.asarray(harmful_thetas, dtype=np.float32)
    if harmful.size == 0:
        return 0.0, {"adaptive_harmful_margin": cfg.requested_harmful_margin, "nearest_harmful_distance": None}
    if harmful.ndim == 1:
        harmful = harmful.reshape(1, -1)
    margin, pos_harm_dist = adaptive_margin_np(positive_thetas, harmful, cfg.requested_harmful_margin)
    distances = normalized_theta_distance_np(theta, harmful)
    hinges = np.maximum(0.0, float(margin) - distances)
    if cfg.harmful_loss == "nearest_adaptive":
        loss = float(hinges.max())
    elif cfg.harmful_loss == "topk_cvar_adaptive":
        ordered = np.sort(hinges)[::-1]
        k = min(max(1, int(cfg.topk_harmful)), len(ordered))
        tail_n = max(k, int(math.ceil((1.0 - float(cfg.cvar_quantile)) * len(ordered))))
        loss = float(np.mean(ordered[:tail_n]))
    else:
        raise ValueError(f"unknown harmful_loss: {cfg.harmful_loss}")
    return loss, {
        "adaptive_harmful_margin": float(margin),
        "nearest_positive_harmful_distance": pos_harm_dist,
        "nearest_harmful_distance": float(distances.min()) if distances.size else None,
    }


def positive_loss_np(theta: np.ndarray, positive_thetas: np.ndarray, weights: np.ndarray | None, cfg: RepairedRiskConfig) -> float:
    positives = np.asarray(positive_thetas, dtype=np.float32)
    if positives.size == 0:
        return 0.0
    if cfg.positive_loss == "floor_corrected_softmin":
        raw = positive_softmin_np(theta, positives, weights, cfg.tau)
        floor = positive_softmin_floor_np(positives, weights, cfg.tau)
        return max(0.0, float(raw - floor))
    if cfg.positive_loss == "hard_wta":
        return hard_wta_positive_np(theta, positives)
    if cfg.positive_loss == "clustered_medoid_wta":
        return clustered_medoid_wta_np(theta, positives, distance_threshold=cfg.cluster_distance)
    raise ValueError(f"unknown positive_loss: {cfg.positive_loss}")


def context_loss_np(theta: np.ndarray, context: LabelV52Context, cfg: RepairedRiskConfig = DEFAULT_REPAIRED_RISK) -> tuple[float, dict[str, Any]]:
    theta = clamp_numeric_theta(theta)
    positive = 0.0
    harmful = 0.0
    support = 0.0
    trust = 0.0
    harm_terms: dict[str, Any] = {}
    if context.label_state in {POSITIVE_SUPPORTED, MIXED_FRONTIER}:
        positive = positive_loss_np(theta, context.positive_thetas, context.positive_weights, cfg)
    if context.label_state in {HARMFUL_SUPPORTED, MIXED_FRONTIER}:
        harmful, harm_terms = harmful_hinge_np(theta, context.positive_thetas, context.harmful_thetas, cfg)
    if context.label_state == CENSORED_UNKNOWN:
        if len(context.safe_candidates):
            nearest_safe = normalized_theta_distance_np(theta, context.safe_thetas)
            support = max(0.0, float(nearest_safe.min()) - float(cfg.censored_support_margin)) if nearest_safe.size else 0.0
        trust = float(cfg.censored_trust_weight) * float(normalized_theta_distance_np(theta, BASELINE_G556).mean())
    if context.label_state == SAFE_NONIMPROVING_SUPPORTED:
        nearest_safe = normalized_theta_distance_np(theta, context.safe_thetas)
        support = max(0.0, float(nearest_safe.min()) - float(cfg.safe_nonimproving_support_margin)) if nearest_safe.size else 0.0
        trust = float(cfg.safe_nonimproving_trust_weight) * float(normalized_theta_distance_np(theta, BASELINE_G556).mean())
    total = float(positive + harmful + support + trust)
    terms = {
        "total_repaired_risk": total,
        "positive_loss": float(positive),
        "harmful_loss": float(harmful),
        "support_loss": float(support),
        "trust_loss": float(trust),
        "loss_config_sha256": cfg.sha256,
        **harm_terms,
    }
    return total, terms


def loss_item_from_context(context: LabelV52Context) -> dict[str, Any]:
    return {
        "evaluation_uid": context.evaluation_uid,
        "label_state": context.label_state,
        "positive_thetas": context.positive_thetas,
        "harmful_thetas": context.harmful_thetas,
        "safe_thetas": context.safe_thetas,
        "positive_weights": context.positive_weights,
        "harmful_weights": context.harmful_weights,
    }


def _tensor_matrix(value: Any, theta, dim: int):
    import torch

    tensor = torch.as_tensor(value, dtype=theta.dtype, device=theta.device)
    if tensor.numel() == 0:
        return theta.new_zeros((0, dim))
    if tensor.ndim == 1:
        return tensor.view(1, -1)
    return tensor


def normalized_theta_distance_torch(theta, candidates):
    import torch

    if candidates.numel() == 0:
        return theta.new_zeros((0,))
    span = torch.as_tensor(THETA_SPAN, dtype=theta.dtype, device=theta.device)
    return torch.mean(torch.abs((theta.view(1, -1) - candidates) / span), dim=-1)


def _torch_softmin(theta, positives, weights, cfg: RepairedRiskConfig):
    import torch

    distances = normalized_theta_distance_torch(theta, positives)
    if weights is None or weights.numel() == 0:
        weights = torch.ones_like(distances)
    weights = weights.to(device=theta.device, dtype=theta.dtype)
    weights = weights / weights.sum().clamp_min(1.0e-12)
    return -float(cfg.tau) * torch.logsumexp(torch.log(weights.clamp_min(1.0e-12)) - distances / float(cfg.tau), dim=0)


def _torch_positive_floor(positives, weights, cfg: RepairedRiskConfig):
    import torch

    if positives.numel() == 0:
        return positives.sum() * 0.0
    losses = [_torch_softmin(pos, positives, weights, cfg) for pos in positives]
    return torch.stack(losses).min().detach()


def _torch_cluster_medoids(positives, cfg: RepairedRiskConfig):
    if positives.numel() == 0:
        return positives
    arr = positives.detach().cpu().numpy().astype(np.float32)
    idx = clustered_medoid_indices_np(arr, distance_threshold=cfg.cluster_distance)
    import torch

    return positives[torch.as_tensor(idx, dtype=torch.long, device=positives.device)]


def context_loss_torch(theta, item: dict[str, Any], cfg: RepairedRiskConfig = DEFAULT_REPAIRED_RISK):
    import torch

    dim = len(THETA_NUMERIC_COLUMNS)
    positives = _tensor_matrix(item.get("positive_thetas", []), theta, dim)
    harmful = _tensor_matrix(item.get("harmful_thetas", []), theta, dim)
    safe = _tensor_matrix(item.get("safe_thetas", []), theta, dim)
    pos_w = torch.as_tensor(item.get("positive_weights", []), dtype=theta.dtype, device=theta.device)
    label_state = str(item.get("label_state", ""))
    zero = theta.sum() * 0.0
    positive_loss = zero
    harmful_loss = zero
    support_loss = zero
    trust_loss = zero
    if label_state in {POSITIVE_SUPPORTED, MIXED_FRONTIER} and positives.numel() > 0:
        if cfg.positive_loss == "floor_corrected_softmin":
            positive_loss = torch.relu(_torch_softmin(theta, positives, pos_w, cfg) - _torch_positive_floor(positives, pos_w, cfg))
        elif cfg.positive_loss == "hard_wta":
            positive_loss = normalized_theta_distance_torch(theta, positives).min()
        elif cfg.positive_loss == "clustered_medoid_wta":
            medoids = _torch_cluster_medoids(positives, cfg)
            positive_loss = normalized_theta_distance_torch(theta, medoids).min()
        else:
            raise ValueError(f"unknown positive_loss: {cfg.positive_loss}")
    if label_state in {HARMFUL_SUPPORTED, MIXED_FRONTIER} and harmful.numel() > 0:
        margin, _nearest = adaptive_margin_np(
            positives.detach().cpu().numpy().astype(np.float32),
            harmful.detach().cpu().numpy().astype(np.float32),
            cfg.requested_harmful_margin,
        )
        hinges = torch.relu(float(margin) - normalized_theta_distance_torch(theta, harmful))
        if cfg.harmful_loss == "nearest_adaptive":
            harmful_loss = hinges.max()
        elif cfg.harmful_loss == "topk_cvar_adaptive":
            k = min(max(1, int(cfg.topk_harmful)), int(hinges.numel()))
            tail_n = max(k, int(math.ceil((1.0 - float(cfg.cvar_quantile)) * int(hinges.numel()))))
            harmful_loss = torch.topk(hinges, k=tail_n).values.mean()
        else:
            raise ValueError(f"unknown harmful_loss: {cfg.harmful_loss}")
    if label_state == CENSORED_UNKNOWN:
        if safe.numel() > 0:
            support_loss = torch.relu(normalized_theta_distance_torch(theta, safe).min() - float(cfg.censored_support_margin))
        anchor = torch.as_tensor(BASELINE_G556, dtype=theta.dtype, device=theta.device)
        trust_loss = float(cfg.censored_trust_weight) * normalized_theta_distance_torch(theta, anchor).mean()
    if label_state == SAFE_NONIMPROVING_SUPPORTED:
        if safe.numel() > 0:
            support_loss = torch.relu(normalized_theta_distance_torch(theta, safe).min() - float(cfg.safe_nonimproving_support_margin))
        anchor = torch.as_tensor(BASELINE_G556, dtype=theta.dtype, device=theta.device)
        trust_loss = float(cfg.safe_nonimproving_trust_weight) * normalized_theta_distance_torch(theta, anchor).mean()
    total = positive_loss + harmful_loss + support_loss + trust_loss
    return total, {
        "total_repaired_risk": total.detach(),
        "positive_loss": positive_loss.detach(),
        "harmful_loss": harmful_loss.detach(),
        "support_loss": support_loss.detach(),
        "trust_loss": trust_loss.detach(),
    }


def batch_context_loss_torch(theta_hat, items: Sequence[dict[str, Any]], cfg: RepairedRiskConfig = DEFAULT_REPAIRED_RISK):
    import torch

    losses = []
    totals: dict[str, float] = {}
    for idx, item in enumerate(items):
        loss, terms = context_loss_torch(theta_hat[idx], item, cfg)
        losses.append(loss)
        for key, value in terms.items():
            totals[key] = totals.get(key, 0.0) + float(value.detach().cpu())
    if not losses:
        return theta_hat.sum() * 0.0, {}
    return torch.stack(losses).mean(), {key: value / len(losses) for key, value in totals.items()}

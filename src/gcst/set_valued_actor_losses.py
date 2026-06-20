"""Set-valued actor objectives for G5.63."""

from __future__ import annotations

from typing import Any

import torch

from .actor_losses import anchor_loss, normalized_theta_distance
from .label_v52_set import (
    CENSORED_UNKNOWN,
    HARMFUL_SUPPORTED,
    MIXED_FRONTIER,
    POSITIVE_SUPPORTED,
    SAFE_NONIMPROVING_SUPPORTED,
)
from .theta_schema import BASELINE_G556


def _as_theta_matrix(values: torch.Tensor, theta_hat: torch.Tensor) -> torch.Tensor:
    if values.numel() == 0:
        return theta_hat.new_zeros((0, theta_hat.shape[-1]))
    if values.ndim == 1:
        return values.view(1, -1).to(device=theta_hat.device, dtype=theta_hat.dtype)
    return values.to(device=theta_hat.device, dtype=theta_hat.dtype)


def positive_set_softmin_loss(
    theta_hat: torch.Tensor,
    positive_thetas: torch.Tensor,
    weights: torch.Tensor | None = None,
    tau: float = 0.05,
) -> torch.Tensor:
    """Mode-seeking loss: close to any verified positive mode is good."""

    positives = _as_theta_matrix(positive_thetas, theta_hat)
    if positives.numel() == 0:
        return theta_hat.sum() * 0.0
    distances = normalized_theta_distance(theta_hat.view(1, -1), positives)
    if weights is None or weights.numel() == 0:
        weights = torch.ones_like(distances)
    weights = weights.to(device=theta_hat.device, dtype=theta_hat.dtype)
    weights = weights / weights.sum().clamp_min(1.0e-12)
    return -float(tau) * torch.logsumexp(torch.log(weights.clamp_min(1.0e-12)) - distances / float(tau), dim=0)


def harmful_repulsion_loss(
    theta_hat: torch.Tensor,
    harmful_thetas: torch.Tensor,
    weights: torch.Tensor | None = None,
    margin: float = 0.12,
) -> torch.Tensor:
    harmful = _as_theta_matrix(harmful_thetas, theta_hat)
    if harmful.numel() == 0:
        return theta_hat.sum() * 0.0
    distances = normalized_theta_distance(theta_hat.view(1, -1), harmful)
    per = torch.relu(float(margin) - distances)
    if weights is not None and weights.numel() > 0:
        w = weights.to(device=theta_hat.device, dtype=theta_hat.dtype)
        w = w / w.mean().clamp_min(1.0e-12)
        per = per * w
    return per.mean()


def support_distance_loss(theta_hat: torch.Tensor, support_thetas: torch.Tensor, margin: float = 0.25) -> torch.Tensor:
    support = _as_theta_matrix(support_thetas, theta_hat)
    if support.numel() == 0:
        return theta_hat.sum() * 0.0
    nearest = normalized_theta_distance(theta_hat.view(1, -1), support).min()
    return torch.relu(nearest - float(margin))


def trust_region_loss(theta_hat: torch.Tensor) -> torch.Tensor:
    anchor = torch.as_tensor(BASELINE_G556, dtype=theta_hat.dtype, device=theta_hat.device).view(1, -1)
    return normalized_theta_distance(theta_hat.view(1, -1), anchor).mean()


def set_valued_actor_loss(
    theta_hat: torch.Tensor,
    *,
    label_state: str,
    positive_thetas: torch.Tensor,
    harmful_thetas: torch.Tensor,
    safe_thetas: torch.Tensor | None = None,
    positive_weights: torch.Tensor | None = None,
    harmful_weights: torch.Tensor | None = None,
    tau: float = 0.05,
    harmful_margin: float = 0.12,
    censored_trust_weight: float = 0.05,
    safe_nonimproving_anchor_weight: float = 0.20,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    """Compose state-specific Label-v5.2 losses.

    Censored contexts receive only weak support/trust regularization.  They are
    never pushed away as negative examples and never hard-targeted to g556.
    """

    safe_thetas = positive_thetas if safe_thetas is None else safe_thetas
    zero = theta_hat.sum() * 0.0
    positive = zero
    harmful = zero
    support = zero
    trust = zero

    if label_state in {POSITIVE_SUPPORTED, MIXED_FRONTIER}:
        positive = positive_set_softmin_loss(theta_hat, positive_thetas, positive_weights, tau=tau)
    if label_state in {HARMFUL_SUPPORTED, MIXED_FRONTIER}:
        harmful = harmful_repulsion_loss(theta_hat, harmful_thetas, harmful_weights, margin=harmful_margin)
    if label_state == CENSORED_UNKNOWN:
        support = support_distance_loss(theta_hat, safe_thetas, margin=0.35)
        trust = trust_region_loss(theta_hat) * float(censored_trust_weight)
    if label_state == SAFE_NONIMPROVING_SUPPORTED:
        support = support_distance_loss(theta_hat, safe_thetas, margin=0.20)
        trust = anchor_loss(theta_hat.view(1, -1)) * float(safe_nonimproving_anchor_weight)
    if label_state == HARMFUL_SUPPORTED:
        trust = anchor_loss(theta_hat.view(1, -1)) * 0.10

    total = positive + harmful + support + trust
    return total, {
        "positive_set_loss": positive.detach(),
        "harmful_margin_loss": harmful.detach(),
        "censored_support_loss": support.detach(),
        "trust_loss": trust.detach(),
        "total_loss": total.detach(),
    }


def batch_set_valued_actor_loss(theta_hat: torch.Tensor, batch: list[dict[str, Any]]) -> tuple[torch.Tensor, dict[str, float]]:
    losses = []
    term_totals: dict[str, float] = {}
    for idx, item in enumerate(batch):
        pos = torch.as_tensor(item.get("positive_thetas"), dtype=theta_hat.dtype, device=theta_hat.device)
        harm = torch.as_tensor(item.get("harmful_thetas"), dtype=theta_hat.dtype, device=theta_hat.device)
        safe = torch.as_tensor(item.get("safe_thetas"), dtype=theta_hat.dtype, device=theta_hat.device)
        pos_w = torch.as_tensor(item.get("positive_weights", []), dtype=theta_hat.dtype, device=theta_hat.device)
        harm_w = torch.as_tensor(item.get("harmful_weights", []), dtype=theta_hat.dtype, device=theta_hat.device)
        loss, terms = set_valued_actor_loss(
            theta_hat[idx],
            label_state=str(item["label_state"]),
            positive_thetas=pos,
            harmful_thetas=harm,
            safe_thetas=safe,
            positive_weights=pos_w,
            harmful_weights=harm_w,
        )
        losses.append(loss)
        for key, value in terms.items():
            term_totals[key] = term_totals.get(key, 0.0) + float(value.cpu())
    if not losses:
        return theta_hat.sum() * 0.0, {}
    total = torch.stack(losses).mean()
    return total, {key: value / len(losses) for key, value in term_totals.items()}

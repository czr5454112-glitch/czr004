"""Direct actor losses for safe-set mode seeking."""

from __future__ import annotations

import torch

from .label_v4 import BASELINE_G556, THETA_HI, THETA_LO


def normalized_theta_distance(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    lo = torch.as_tensor(THETA_LO, dtype=a.dtype, device=a.device)
    hi = torch.as_tensor(THETA_HI, dtype=a.dtype, device=a.device)
    span = (hi - lo).clamp_min(1.0e-6)
    return torch.mean(torch.abs((a - b) / span), dim=-1)


def safe_set_softmin_loss(theta_hat: torch.Tensor, safe_thetas: torch.Tensor, weights: torch.Tensor | None = None, tau: float = 0.05) -> torch.Tensor:
    if safe_thetas.numel() == 0:
        anchor = torch.as_tensor(BASELINE_G556, dtype=theta_hat.dtype, device=theta_hat.device).view(1, -1)
        return normalized_theta_distance(theta_hat.view(1, -1), anchor).mean()
    distances = normalized_theta_distance(theta_hat.view(1, -1), safe_thetas)
    if weights is None:
        weights = torch.ones_like(distances) / max(1, distances.numel())
    weights = weights.to(theta_hat.device, theta_hat.dtype)
    weights = weights / weights.sum().clamp_min(1.0e-12)
    return -float(tau) * torch.logsumexp(torch.log(weights.clamp_min(1.0e-12)) - distances / float(tau), dim=0)


def anchor_loss(theta_hat: torch.Tensor) -> torch.Tensor:
    anchor = torch.as_tensor(BASELINE_G556, dtype=theta_hat.dtype, device=theta_hat.device).expand_as(theta_hat)
    return normalized_theta_distance(theta_hat, anchor).mean()


def bounds_loss(theta_hat: torch.Tensor) -> torch.Tensor:
    lo = torch.as_tensor(THETA_LO, dtype=theta_hat.dtype, device=theta_hat.device)
    hi = torch.as_tensor(THETA_HI, dtype=theta_hat.dtype, device=theta_hat.device)
    return (torch.relu(lo - theta_hat).mean() + torch.relu(theta_hat - hi).mean())

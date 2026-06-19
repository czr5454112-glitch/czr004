"""Training losses for the G5.58 learnability gates."""

from __future__ import annotations

import torch
from torch.nn import functional as F


def critic_loss(outputs: dict[str, torch.Tensor], labels: dict[str, torch.Tensor]) -> torch.Tensor:
    reg = F.binary_cross_entropy_with_logits(outputs["p_success_regression_logit"], labels["success_regression"].float())
    gain = F.binary_cross_entropy_with_logits(outputs["p_success_gain_logit"], labels["success_gain"].float())
    quality = F.smooth_l1_loss(outputs["expected_quality_delta"], labels["quality_delta"].float())
    material = F.binary_cross_entropy_with_logits(outputs["materialization_logit"], labels["theta_in_bounds"].float())
    q = outputs["quality_quantiles"]
    target = labels["quality_delta"].unsqueeze(-1).float()
    taus = torch.tensor([0.1, 0.5, 0.9], device=target.device).view(1, 3)
    diff = target - q
    pinball = torch.maximum(taus * diff, (taus - 1.0) * diff).mean()
    return 3.0 * reg + gain + quality + 0.2 * material + 0.2 * pinball


def generator_loss(proposals: torch.Tensor, target_theta: torch.Tensor, safe_mask: torch.Tensor) -> torch.Tensor:
    dist = torch.mean(torch.abs(proposals - target_theta.unsqueeze(1)), dim=-1)
    best = dist.min(dim=1).values
    safe_weight = safe_mask.float().clamp_min(0.25)
    diversity = torch.pdist(proposals.reshape(-1, proposals.size(-1))).mean() if proposals.numel() else proposals.new_tensor(0.0)
    return (best * safe_weight).mean() - 0.01 * diversity

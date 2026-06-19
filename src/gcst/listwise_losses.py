"""Pairwise and listwise losses for Label-v5 theta learning."""

from __future__ import annotations

import torch
from torch.nn import functional as F


def pairwise_margin_ranking_loss(scores: torch.Tensor, quality_delta: torch.Tensor, instance_index: torch.Tensor, margin: float = 0.02) -> torch.Tensor:
    losses: list[torch.Tensor] = []
    for instance in torch.unique(instance_index.long()):
        mask = instance_index.long() == instance
        s = scores[mask].flatten()
        q = quality_delta[mask].flatten()
        if s.numel() < 2:
            continue
        diff_q = q[:, None] - q[None, :]
        keep = torch.abs(diff_q) > margin
        if not bool(keep.any()):
            continue
        # Lower quality_delta is better, so score_i should exceed score_j when q_i < q_j.
        target = torch.sign(-diff_q[keep])
        diff_s = (s[:, None] - s[None, :])[keep]
        losses.append(F.margin_ranking_loss(diff_s, torch.zeros_like(diff_s), target, margin=margin))
    return torch.stack(losses).mean() if losses else scores.sum() * 0.0


def listnet_kl_loss(scores: torch.Tensor, target_probs: torch.Tensor, instance_index: torch.Tensor) -> torch.Tensor:
    losses: list[torch.Tensor] = []
    for instance in torch.unique(instance_index.long()):
        mask = instance_index.long() == instance
        logits = scores[mask].flatten()
        target = target_probs[mask].flatten()
        if logits.numel() == 0:
            continue
        if float(target.sum().detach().cpu()) <= 0.0:
            target = torch.ones_like(target) / max(1, target.numel())
        else:
            target = target / target.sum().clamp_min(1.0e-12)
        losses.append(F.kl_div(torch.log_softmax(logits, dim=0), target, reduction="sum"))
    return torch.stack(losses).mean() if losses else scores.sum() * 0.0


def context_balanced_weights(instance_index: torch.Tensor) -> torch.Tensor:
    idx = instance_index.long()
    weights = torch.zeros_like(idx, dtype=torch.float32)
    unique = torch.unique(idx)
    for instance in unique:
        mask = idx == instance
        weights[mask] = 1.0 / mask.sum().clamp_min(1)
    return weights / max(1, unique.numel())

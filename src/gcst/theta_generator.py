"""Multi-proposal bounded static theta generator."""

from __future__ import annotations

import torch
from torch import nn

from .label_v4 import BASELINE_G556, THETA_HI, THETA_LO


class MultiProposalThetaGenerator(nn.Module):
    def __init__(self, hidden_dim: int = 256, proposals: int = 8, theta_dim: int = 15) -> None:
        super().__init__()
        self.proposals = proposals
        self.theta_dim = theta_dim
        self.body = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim * 2),
            nn.GELU(),
            nn.Linear(hidden_dim * 2, hidden_dim * 2),
            nn.GELU(),
        )
        self.delta = nn.Linear(hidden_dim * 2, proposals * theta_dim)
        self.confidence = nn.Linear(hidden_dim * 2, proposals)
        self.fallback_logit = nn.Linear(hidden_dim * 2, 1)
        self.mode_logits = nn.Linear(hidden_dim * 2, proposals * 3)
        self.register_buffer("baseline", torch.tensor(BASELINE_G556, dtype=torch.float32))
        self.register_buffer("lo", torch.tensor(THETA_LO, dtype=torch.float32))
        self.register_buffer("hi", torch.tensor(THETA_HI, dtype=torch.float32))

    def forward(self, graph_emb: torch.Tensor, od_emb: torch.Tensor) -> dict[str, torch.Tensor]:
        h = self.body(torch.cat([graph_emb, od_emb], dim=-1))
        raw = self.delta(h).view(-1, self.proposals, self.theta_dim)
        scale = (self.hi - self.lo).view(1, 1, -1) * 0.35
        theta = self.baseline.view(1, 1, -1) + scale * torch.tanh(raw)
        theta = torch.max(torch.min(theta, self.hi.view(1, 1, -1)), self.lo.view(1, 1, -1))
        return {
            "theta": theta,
            "confidence": self.confidence(h),
            "fallback_logit": self.fallback_logit(h).squeeze(-1),
            "mode_logits": self.mode_logits(h).view(-1, self.proposals, 3),
        }

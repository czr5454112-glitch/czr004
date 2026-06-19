"""Candidate-conditioned critic for static theta proposals."""

from __future__ import annotations

import torch
from torch import nn


class ThetaCritic(nn.Module):
    def __init__(self, hidden_dim: int = 256, theta_dim: int = 15) -> None:
        super().__init__()
        self.theta_proj = nn.Sequential(nn.Linear(theta_dim, hidden_dim), nn.GELU(), nn.LayerNorm(hidden_dim))
        self.net = nn.Sequential(
            nn.Linear(hidden_dim * 3, hidden_dim * 3),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim * 3, hidden_dim * 2),
            nn.GELU(),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.GELU(),
        )
        self.p_regression = nn.Linear(hidden_dim, 1)
        self.p_gain = nn.Linear(hidden_dim, 1)
        self.quality = nn.Linear(hidden_dim, 1)
        self.quantiles = nn.Linear(hidden_dim, 3)
        self.uncertainty = nn.Linear(hidden_dim, 1)
        self.materialization = nn.Linear(hidden_dim, 1)

    def forward(self, graph_emb: torch.Tensor, od_emb: torch.Tensor, theta: torch.Tensor) -> dict[str, torch.Tensor]:
        h = self.net(torch.cat([graph_emb, od_emb, self.theta_proj(theta.float())], dim=-1))
        return {
            "p_success_regression_logit": self.p_regression(h).squeeze(-1),
            "p_success_gain_logit": self.p_gain(h).squeeze(-1),
            "expected_quality_delta": self.quality(h).squeeze(-1),
            "quality_quantiles": self.quantiles(h),
            "uncertainty": torch.nn.functional.softplus(self.uncertainty(h).squeeze(-1)),
            "materialization_logit": self.materialization(h).squeeze(-1),
        }

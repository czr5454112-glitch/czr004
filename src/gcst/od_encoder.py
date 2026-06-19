"""Agent start-goal set encoder."""

from __future__ import annotations

import torch
from torch import nn


class ODSetEncoder(nn.Module):
    def __init__(self, input_dim: int = 6, hidden_dim: int = 256, heads: int = 8, dropout: float = 0.1) -> None:
        super().__init__()
        self.in_proj = nn.Linear(input_dim, hidden_dim)
        self.blocks = nn.ModuleList(
            [
                nn.TransformerEncoderLayer(
                    d_model=hidden_dim,
                    nhead=heads,
                    dim_feedforward=hidden_dim * 2,
                    dropout=dropout,
                    activation="gelu",
                    batch_first=True,
                )
                for _ in range(2)
            ]
        )
        self.norm = nn.LayerNorm(hidden_dim)

    def forward(self, od_tokens: torch.Tensor, mask: torch.Tensor | None = None) -> torch.Tensor:
        x = self.in_proj(od_tokens.float())
        key_padding_mask = None
        if mask is not None:
            key_padding_mask = ~mask.bool()
        for block in self.blocks:
            x = block(x, src_key_padding_mask=key_padding_mask)
        if mask is None:
            pooled = x.mean(dim=1)
        else:
            denom = mask.float().sum(dim=1, keepdim=True).clamp_min(1.0)
            pooled = (x * mask.unsqueeze(-1).float()).sum(dim=1) / denom
        return self.norm(pooled)

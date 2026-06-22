"""Pure PyTorch edge-aware graph-attention encoder.

Global attention is applied inside each graph independently.  G5.58 pooled each
graph to a token and then ran a Transformer across the minibatch, which leaked
batch composition into per-instance predictions.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn


@dataclass
class GraphBatch:
    node_features: torch.Tensor
    edge_index: torch.Tensor
    edge_features: torch.Tensor
    batch_index: torch.Tensor
    num_graphs: int


def scatter_mean(values: torch.Tensor, index: torch.Tensor, dim_size: int) -> torch.Tensor:
    out = values.new_zeros((dim_size, values.size(-1)))
    count = values.new_zeros((dim_size, 1))
    out.index_add_(0, index, values)
    count.index_add_(0, index, torch.ones((values.size(0), 1), device=values.device, dtype=values.dtype))
    return out / count.clamp_min(1.0)


class EdgeAwareAttentionLayer(nn.Module):
    def __init__(self, hidden_dim: int, edge_dim: int, dropout: float = 0.1) -> None:
        super().__init__()
        self.edge_proj = nn.Linear(edge_dim, hidden_dim)
        self.msg = nn.Linear(hidden_dim * 2, hidden_dim)
        self.attn = nn.Linear(hidden_dim * 3, 1)
        self.norm = nn.LayerNorm(hidden_dim)
        self.drop = nn.Dropout(dropout)
        self.ff = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim),
        )

    def forward(self, h: torch.Tensor, edge_index: torch.Tensor, edge_features: torch.Tensor) -> torch.Tensor:
        if edge_index.numel() == 0:
            return self.norm(h + self.ff(h))
        src, dst = edge_index[0].long(), edge_index[1].long()
        e = self.edge_proj(edge_features)
        logits = self.attn(torch.cat([h[src], h[dst], e], dim=-1)).squeeze(-1)
        weights = torch.zeros_like(logits)
        for node in torch.unique(dst):
            mask = dst == node
            weights[mask] = torch.softmax(logits[mask], dim=0).to(dtype=weights.dtype)
        msg = self.msg(torch.cat([h[src], e], dim=-1)) * weights.unsqueeze(-1)
        agg = torch.zeros_like(h)
        agg.index_add_(0, dst, msg.to(dtype=agg.dtype))
        h = self.norm(h + self.drop(agg))
        return self.norm(h + self.drop(self.ff(h)))


class GraphGPSLiteEncoder(nn.Module):
    def __init__(
        self,
        node_dim: int,
        edge_dim: int,
        hidden_dim: int = 256,
        local_layers: int = 4,
        global_layers: int = 2,
        heads: int = 8,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.node_in = nn.Linear(node_dim, hidden_dim)
        self.local_layers = nn.ModuleList([EdgeAwareAttentionLayer(hidden_dim, edge_dim, dropout) for _ in range(local_layers)])
        self.global_layers = nn.ModuleList(
            [
                nn.TransformerEncoderLayer(
                    d_model=hidden_dim,
                    nhead=heads,
                    dim_feedforward=hidden_dim * 4,
                    dropout=dropout,
                    activation="gelu",
                    batch_first=True,
                )
                for _ in range(global_layers)
            ]
        )
        self.out_norm = nn.LayerNorm(hidden_dim)

    def forward(self, batch: GraphBatch) -> torch.Tensor:
        h = self.node_in(batch.node_features.float())
        for layer in self.local_layers:
            h = layer(h, batch.edge_index, batch.edge_features.float())
        batch_index = batch.batch_index.long()
        if self.global_layers:
            updated = h.clone()
            for graph_id in range(int(batch.num_graphs)):
                mask = batch_index == graph_id
                if not bool(mask.any()):
                    continue
                tokens = h[mask].unsqueeze(0)
                for layer in self.global_layers:
                    tokens = layer(tokens)
                updated[mask] = tokens.squeeze(0)
            h = updated
        pooled = scatter_mean(h, batch_index, batch.num_graphs)
        return self.out_norm(pooled)

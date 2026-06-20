"""Lightweight edge-aware attention actor for G5.63 experiments."""

from __future__ import annotations

from dataclasses import dataclass

from .goal_aware_actor import GOAL_AWARE_SCALAR_FEATURES
from .theta_schema import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS


@dataclass(frozen=True)
class LightEdgeAttentionConfig:
    node_dim: int = 9
    edge_dim: int = 9
    scalar_dim: int = len(GOAL_AWARE_SCALAR_FEATURES)
    hidden_dim: int = 64
    local_layers: int = 3
    heads: int = 4
    residual_scale: float = 0.30


class LightEdgeAttentionActor:
    """Sparse local graph actor retaining graph/OD/C0/F0/scalar inputs."""

    information_floor = ("graph_topology", "paired_od", "directed_c0", "directed_f0", "solver_budget", "ltm_iteration_budget")

    def __init__(self, config: LightEdgeAttentionConfig | None = None) -> None:
        import torch

        from .graph_encoder import GraphGPSLiteEncoder
        from .od_encoder import ODSetEncoder

        self.config = config or LightEdgeAttentionConfig()
        cfg = self.config
        self.graph_encoder = GraphGPSLiteEncoder(
            node_dim=cfg.node_dim,
            edge_dim=cfg.edge_dim,
            hidden_dim=cfg.hidden_dim,
            local_layers=cfg.local_layers,
            global_layers=0,
            heads=cfg.heads,
            dropout=0.0,
        )
        self.od_encoder = ODSetEncoder(input_dim=6, hidden_dim=cfg.hidden_dim, heads=cfg.heads, dropout=0.0)
        self.scalar_encoder = torch.nn.Sequential(
            torch.nn.Linear(cfg.scalar_dim, cfg.hidden_dim),
            torch.nn.LayerNorm(cfg.hidden_dim),
            torch.nn.SiLU(),
        )
        self.fusion = torch.nn.Sequential(
            torch.nn.Linear(cfg.hidden_dim * 3, cfg.hidden_dim),
            torch.nn.LayerNorm(cfg.hidden_dim),
            torch.nn.SiLU(),
        )
        self.theta_head = torch.nn.Linear(cfg.hidden_dim, len(THETA_NUMERIC_COLUMNS))
        self.trust_head = torch.nn.Linear(cfg.hidden_dim, len(THETA_NUMERIC_COLUMNS))

    def module(self):
        import torch

        cfg = self.config

        class _Module(torch.nn.Module):
            def __init__(self, outer: "LightEdgeAttentionActor") -> None:
                super().__init__()
                self.graph_encoder = outer.graph_encoder
                self.od_encoder = outer.od_encoder
                self.scalar_encoder = outer.scalar_encoder
                self.fusion = outer.fusion
                self.theta_head = outer.theta_head
                self.trust_head = outer.trust_head
                self.register_buffer("anchor", torch.as_tensor(BASELINE_G556, dtype=torch.float32))
                self.register_buffer("lo", torch.as_tensor(THETA_LO, dtype=torch.float32))
                self.register_buffer("hi", torch.as_tensor(THETA_HI, dtype=torch.float32))

            def forward(self, graph_batch, od_tokens, od_mask, scalar_x):
                graph_repr = self.graph_encoder(graph_batch)
                od_repr = self.od_encoder(od_tokens, od_mask)
                scalar_repr = self.scalar_encoder(scalar_x.float())
                fused = self.fusion(torch.cat([graph_repr, od_repr, scalar_repr], dim=-1))
                raw = torch.tanh(self.theta_head(fused))
                trust = torch.sigmoid(self.trust_head(fused))
                theta = self.anchor + trust * (self.hi - self.lo) * float(cfg.residual_scale) * raw
                return torch.clamp(theta, self.lo, self.hi)

        return _Module(self)


def parameter_count(module) -> int:
    return sum(int(param.numel()) for param in module.parameters())

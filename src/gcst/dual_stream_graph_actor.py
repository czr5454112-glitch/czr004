"""Richer G5.62 graph actors for real-label UpdateParams learning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .goal_aware_actor import GOAL_AWARE_SCALAR_FEATURES
from .theta_schema import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS


@dataclass(frozen=True)
class ActorArchitecture:
    variant_id: str
    variant_name: str
    scalar_only_control: bool = False
    use_cross_attention: bool = False
    safe_subspace: bool = False
    field_group_trust: bool = False


ARCHITECTURES = {
    "C0": ActorArchitecture("C0", "scalar_context_control", scalar_only_control=True),
    "A0": ActorArchitecture("A0", "f6_lite_goal_aware_graph_actor"),
    "A1": ActorArchitecture("A1", "dual_stream_c0_f0_graph_actor"),
    "A2": ActorArchitecture("A2", "od_graph_cross_attention_actor", use_cross_attention=True),
    "A3": ActorArchitecture("A3", "safe_residual_subspace_actor", use_cross_attention=True, safe_subspace=True),
    "A4": ActorArchitecture("A4", "field_group_trust_safe_subspace_actor", use_cross_attention=True, safe_subspace=True, field_group_trust=True),
}


def make_masked_graph_batch(graph_batch: Any, mode: str):
    from .graph_encoder import GraphBatch

    edge_features = graph_batch.edge_features.clone()
    if edge_features.size(-1) >= 9:
        if mode == "f0":
            mask = edge_features.new_zeros(edge_features.shape)
            mask[:, 5] = edge_features[:, 5]
            edge_features = mask
        elif mode == "c0":
            mask = edge_features.new_zeros(edge_features.shape)
            mask[:, 6] = edge_features[:, 6]
            mask[:, 7] = edge_features[:, 7]
            mask[:, 8] = edge_features[:, 8]
            edge_features = mask
        elif mode == "topology":
            edge_features[:, 5:9] = 0.0
    return GraphBatch(
        graph_batch.node_features,
        graph_batch.edge_index,
        edge_features,
        graph_batch.batch_index,
        graph_batch.num_graphs,
    )


class DualStreamGoalAwareActor:
    """One-forward, run-static theta actor with separate topology, C0 and F0 streams."""

    def __init__(
        self,
        node_dim: int = 9,
        edge_dim: int = 9,
        scalar_dim: int = len(GOAL_AWARE_SCALAR_FEATURES),
        hidden_dim: int = 96,
        residual_scale: float = 0.30,
        scalar_only_control: bool = False,
        use_cross_attention: bool = False,
        safe_subspace: bool = False,
        field_group_trust: bool = False,
    ) -> None:
        import torch

        from .graph_encoder import GraphGPSLiteEncoder
        from .od_encoder import ODSetEncoder

        self.node_dim = int(node_dim)
        self.edge_dim = int(edge_dim)
        self.scalar_dim = int(scalar_dim)
        self.hidden_dim = int(hidden_dim)
        self.residual_scale = float(residual_scale)
        self.scalar_only_control = bool(scalar_only_control)
        self.use_cross_attention = bool(use_cross_attention)
        self.safe_subspace = bool(safe_subspace)
        self.field_group_trust = bool(field_group_trust)
        self.theta_dim = len(THETA_NUMERIC_COLUMNS)
        self.anchor = torch.tensor(BASELINE_G556, dtype=torch.float32)
        self.lo = torch.tensor(THETA_LO, dtype=torch.float32)
        self.hi = torch.tensor(THETA_HI, dtype=torch.float32)
        self.span = self.hi - self.lo
        self.topology_encoder = GraphGPSLiteEncoder(node_dim=node_dim, edge_dim=edge_dim, hidden_dim=hidden_dim, local_layers=2, global_layers=1, heads=4, dropout=0.0)
        self.c0_encoder = GraphGPSLiteEncoder(node_dim=node_dim, edge_dim=edge_dim, hidden_dim=hidden_dim, local_layers=2, global_layers=1, heads=4, dropout=0.0)
        self.f0_encoder = GraphGPSLiteEncoder(node_dim=node_dim, edge_dim=edge_dim, hidden_dim=hidden_dim, local_layers=2, global_layers=1, heads=4, dropout=0.0)
        self.od_encoder = ODSetEncoder(input_dim=6, hidden_dim=hidden_dim, heads=4, dropout=0.0)
        self.od_token_proj = torch.nn.Linear(6, hidden_dim)
        self.cross_attn = torch.nn.MultiheadAttention(hidden_dim, num_heads=4, dropout=0.0, batch_first=True)
        self.scalar_encoder = torch.nn.Sequential(
            torch.nn.Linear(scalar_dim, hidden_dim),
            torch.nn.LayerNorm(hidden_dim),
            torch.nn.SiLU(),
            torch.nn.Linear(hidden_dim, hidden_dim),
            torch.nn.SiLU(),
        )
        self.fusion = torch.nn.Sequential(
            torch.nn.Linear(hidden_dim * 6, hidden_dim),
            torch.nn.LayerNorm(hidden_dim),
            torch.nn.SiLU(),
            torch.nn.Linear(hidden_dim, hidden_dim),
            torch.nn.SiLU(),
        )
        if safe_subspace:
            self.delta_head = torch.nn.Linear(hidden_dim, 6)
            basis = torch.zeros(6, self.theta_dim)
            groups = [
                [0, 1, 2],
                [3, 4],
                [5, 6],
                [7, 8],
                [9, 10],
                [11, 12, 13, 14],
            ]
            for group_idx, cols in enumerate(groups):
                for col in cols:
                    basis[group_idx, col] = 1.0 / max(1, len(cols))
            self.safe_basis = basis
        else:
            self.delta_head = torch.nn.Linear(hidden_dim, self.theta_dim)
            self.safe_basis = None
        self.trust_head = torch.nn.Linear(hidden_dim, 6 if field_group_trust else self.theta_dim)

    def module(self):
        import torch

        class _Module(torch.nn.Module):
            def __init__(self, outer: "DualStreamGoalAwareActor") -> None:
                super().__init__()
                self.topology_encoder = outer.topology_encoder
                self.c0_encoder = outer.c0_encoder
                self.f0_encoder = outer.f0_encoder
                self.od_encoder = outer.od_encoder
                self.od_token_proj = outer.od_token_proj
                self.cross_attn = outer.cross_attn
                self.scalar_encoder = outer.scalar_encoder
                self.fusion = outer.fusion
                self.delta_head = outer.delta_head
                self.trust_head = outer.trust_head
                self.scalar_only_control = outer.scalar_only_control
                self.use_cross_attention = outer.use_cross_attention
                self.safe_subspace = outer.safe_subspace
                self.field_group_trust = outer.field_group_trust
                self.hidden_dim = outer.hidden_dim
                self.register_buffer("anchor", outer.anchor)
                self.register_buffer("lo", outer.lo)
                self.register_buffer("hi", outer.hi)
                self.register_buffer("span", outer.span)
                if outer.safe_basis is not None:
                    self.register_buffer("safe_basis", outer.safe_basis)
                else:
                    self.safe_basis = None

            def _zero(self, scalar_x):
                return scalar_x.new_zeros((scalar_x.shape[0], self.hidden_dim))

            def _field_trust(self, trust):
                if not self.field_group_trust:
                    return trust
                groups = [
                    [0, 1, 2],
                    [3, 4],
                    [5, 6],
                    [7, 8],
                    [9, 10],
                    [11, 12, 13, 14],
                ]
                out = trust.new_zeros((trust.shape[0], len(THETA_NUMERIC_COLUMNS)))
                for idx, cols in enumerate(groups):
                    out[:, cols] = trust[:, idx : idx + 1]
                return out

            def forward(self, graph_batch, od_tokens, od_mask, scalar_x):
                scalar_repr = self.scalar_encoder(scalar_x.float())
                if self.scalar_only_control:
                    topo_repr = c0_repr = f0_repr = od_repr = cross_repr = self._zero(scalar_x)
                else:
                    topo_repr = self.topology_encoder(make_masked_graph_batch(graph_batch, "topology"))
                    c0_repr = self.c0_encoder(make_masked_graph_batch(graph_batch, "c0"))
                    f0_repr = self.f0_encoder(make_masked_graph_batch(graph_batch, "f0"))
                    od_repr = self.od_encoder(od_tokens, od_mask)
                    if self.use_cross_attention:
                        q = (topo_repr + c0_repr + f0_repr).unsqueeze(1)
                        kv = self.od_token_proj(od_tokens.float())
                        key_padding_mask = ~od_mask.bool()
                        cross_repr = self.cross_attn(q, kv, kv, key_padding_mask=key_padding_mask, need_weights=False)[0].squeeze(1)
                    else:
                        cross_repr = self._zero(scalar_x)
                fused = self.fusion(torch.cat([topo_repr, c0_repr, f0_repr, od_repr, cross_repr, scalar_repr], dim=-1))
                trust = torch.sigmoid(self.trust_head(fused))
                raw_delta = torch.tanh(self.delta_head(fused))
                if self.safe_subspace:
                    raw_delta = raw_delta @ self.safe_basis
                trust_full = self._field_trust(trust)
                delta = trust_full * self.span * 0.30 * raw_delta
                return torch.clamp(self.anchor + delta, self.lo, self.hi)

        return _Module(self)


def architecture_from_id(variant_id: str) -> ActorArchitecture:
    key = str(variant_id).upper()
    if key not in ARCHITECTURES:
        raise KeyError(f"unknown G5.62 actor architecture: {variant_id}")
    return ARCHITECTURES[key]

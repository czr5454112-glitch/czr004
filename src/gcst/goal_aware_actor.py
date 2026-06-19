"""Goal-aware dual-channel direct actor for Repair5G.5.61."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .graph_data import GraphData
from .theta_schema import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS


GOAL_AWARE_SCALAR_FEATURES = [
    "agent_count",
    "nominal_budget_ms",
    "base_time_limit_sec",
    "ltm_max_iterations",
    "agent_density",
    "path_found_rate",
    "nonzero_flow",
]


@dataclass
class GoalAwareActorInput:
    graph_batch: Any
    od_tokens: Any
    od_mask: Any
    scalar_features: Any


def _float(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        value = float(row.get(key, default))
    except Exception:
        return default
    return value if np.isfinite(value) else default


def scalar_features(row: dict[str, Any]) -> np.ndarray:
    nonzero = str(row.get("nonzero_flow", "")).strip().lower() in {"1", "true", "yes", "y"}
    values = [
        _float(row, "agent_count", _float(row, "agents", 0.0)),
        _float(row, "nominal_budget_ms", _float(row, "budget_ms", 0.0)) / 1000.0,
        _float(row, "base_time_limit_sec", 0.5),
        _float(row, "ltm_max_iterations", 2.0),
        _float(row, "agent_density", 0.0),
        _float(row, "path_found_rate", 0.0),
        float(nonzero),
    ]
    return np.asarray(values, dtype=np.float32)


def make_graph_batch(graphs: list[GraphData]):
    import torch

    from .graph_encoder import GraphBatch

    node_parts = []
    edge_parts = []
    edge_index_parts = []
    batch_index = []
    offset = 0
    for graph_idx, graph in enumerate(graphs):
        node_parts.append(torch.tensor(graph.node_features, dtype=torch.float32))
        if graph.edge_index.size:
            edge_index_parts.append(torch.tensor(graph.edge_index + offset, dtype=torch.long))
            edge_parts.append(torch.tensor(graph.edge_features, dtype=torch.float32))
        batch_index.extend([graph_idx] * len(graph.cells))
        offset += len(graph.cells)
    nodes = torch.cat(node_parts, dim=0) if node_parts else torch.zeros((0, 9), dtype=torch.float32)
    edges = torch.cat(edge_index_parts, dim=1) if edge_index_parts else torch.zeros((2, 0), dtype=torch.long)
    edge_features = torch.cat(edge_parts, dim=0) if edge_parts else torch.zeros((0, 9), dtype=torch.float32)
    return GraphBatch(nodes, edges, edge_features, torch.tensor(batch_index, dtype=torch.long), len(graphs))


def pad_od_tokens(assignments: list[dict[str, Any]], max_tokens: int | None = None):
    import torch

    max_len = max((int(np.asarray(a.get("od_tokens", np.zeros((0, 6)))).shape[0]) for a in assignments), default=0)
    if max_tokens is not None:
        max_len = min(max_len, max_tokens)
    max_len = max(max_len, 1)
    tokens = np.zeros((len(assignments), max_len, 6), dtype=np.float32)
    mask = np.zeros((len(assignments), max_len), dtype=bool)
    for idx, assignment in enumerate(assignments):
        od = np.asarray(assignment.get("od_tokens", np.zeros((0, 6), dtype=np.float32)), dtype=np.float32)
        take = min(max_len, od.shape[0])
        if take:
            tokens[idx, :take] = od[:take]
            mask[idx, :take] = True
    return torch.tensor(tokens, dtype=torch.float32), torch.tensor(mask, dtype=torch.bool)


class GoalAwareDualChannelActor:
    """One-forward actor consuming graph topology, paired OD, C0/F0 and budget."""

    def __init__(
        self,
        node_dim: int = 9,
        edge_dim: int = 9,
        scalar_dim: int = len(GOAL_AWARE_SCALAR_FEATURES),
        hidden_dim: int = 128,
        use_graph: bool = True,
        use_paired_od: bool = True,
        use_c0f0: bool = True,
        residual_scale: float = 0.30,
    ) -> None:
        import torch

        from .graph_encoder import GraphGPSLiteEncoder
        from .od_encoder import ODSetEncoder

        self.node_dim = int(node_dim)
        self.edge_dim = int(edge_dim)
        self.scalar_dim = int(scalar_dim)
        self.hidden_dim = int(hidden_dim)
        self.use_graph = bool(use_graph)
        self.use_paired_od = bool(use_paired_od)
        self.use_c0f0 = bool(use_c0f0)
        self.residual_scale = float(residual_scale)
        self.theta_dim = len(THETA_NUMERIC_COLUMNS)
        self.anchor = torch.tensor(BASELINE_G556, dtype=torch.float32)
        self.lo = torch.tensor(THETA_LO, dtype=torch.float32)
        self.hi = torch.tensor(THETA_HI, dtype=torch.float32)
        self.span = self.hi - self.lo
        self.graph_encoder = GraphGPSLiteEncoder(node_dim=node_dim, edge_dim=edge_dim, hidden_dim=hidden_dim, local_layers=2, global_layers=1, heads=4, dropout=0.0)
        self.od_encoder = ODSetEncoder(input_dim=6, hidden_dim=hidden_dim, heads=4, dropout=0.0)
        self.scalar_encoder = torch.nn.Sequential(
            torch.nn.Linear(scalar_dim, hidden_dim),
            torch.nn.LayerNorm(hidden_dim),
            torch.nn.SiLU(),
            torch.nn.Linear(hidden_dim, hidden_dim),
            torch.nn.SiLU(),
        )
        self.fusion = torch.nn.Sequential(
            torch.nn.Linear(hidden_dim * 3, hidden_dim),
            torch.nn.LayerNorm(hidden_dim),
            torch.nn.SiLU(),
            torch.nn.Linear(hidden_dim, hidden_dim),
            torch.nn.SiLU(),
        )
        self.delta_head = torch.nn.Linear(hidden_dim, self.theta_dim)
        self.trust_head = torch.nn.Linear(hidden_dim, self.theta_dim)

    def module(self):
        import torch

        from .graph_encoder import GraphBatch

        class _Module(torch.nn.Module):
            def __init__(self, outer: "GoalAwareDualChannelActor") -> None:
                super().__init__()
                self.graph_encoder = outer.graph_encoder
                self.od_encoder = outer.od_encoder
                self.scalar_encoder = outer.scalar_encoder
                self.fusion = outer.fusion
                self.delta_head = outer.delta_head
                self.trust_head = outer.trust_head
                self.use_graph = outer.use_graph
                self.use_paired_od = outer.use_paired_od
                self.use_c0f0 = outer.use_c0f0
                self.residual_scale = outer.residual_scale
                self.hidden_dim = outer.hidden_dim
                self.register_buffer("anchor", outer.anchor)
                self.register_buffer("lo", outer.lo)
                self.register_buffer("hi", outer.hi)
                self.register_buffer("span", outer.span)

            def _graph_branch(self, graph_batch):
                if self.use_c0f0:
                    return self.graph_encoder(graph_batch)
                edge_features = graph_batch.edge_features.clone()
                if edge_features.size(-1) >= 9:
                    edge_features[:, 5:9] = 0.0
                no_traffic = GraphBatch(
                    graph_batch.node_features,
                    graph_batch.edge_index,
                    edge_features,
                    graph_batch.batch_index,
                    graph_batch.num_graphs,
                )
                return self.graph_encoder(no_traffic)

            def forward(self, graph_batch, od_tokens, od_mask, scalar_x):
                batch_size = int(scalar_x.shape[0])
                if self.use_graph:
                    graph_repr = self._graph_branch(graph_batch)
                else:
                    graph_repr = scalar_x.new_zeros((batch_size, self.hidden_dim))
                if self.use_paired_od:
                    od_repr = self.od_encoder(od_tokens, od_mask)
                else:
                    od_repr = scalar_x.new_zeros((batch_size, self.hidden_dim))
                scalar_repr = self.scalar_encoder(scalar_x.float())
                fused = self.fusion(torch.cat([graph_repr, od_repr, scalar_repr], dim=-1))
                trust = torch.sigmoid(self.trust_head(fused))
                delta = trust * self.span * self.residual_scale * torch.tanh(self.delta_head(fused))
                return torch.clamp(self.anchor + delta, self.lo, self.hi)

        return _Module(self)

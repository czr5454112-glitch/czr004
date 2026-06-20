"""Training-only graph-conditioned solver outcome critic for G5.62."""

from __future__ import annotations

from .goal_aware_actor import GOAL_AWARE_SCALAR_FEATURES
from .theta_schema import THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS


class GraphOutcomeCritic:
    """Predict real solver outcome heads from graph/OD/C0/F0/scalars and theta."""

    def __init__(
        self,
        node_dim: int = 9,
        edge_dim: int = 9,
        scalar_dim: int = len(GOAL_AWARE_SCALAR_FEATURES),
        hidden_dim: int = 96,
    ) -> None:
        import torch

        from .graph_encoder import GraphGPSLiteEncoder
        from .od_encoder import ODSetEncoder

        self.node_dim = int(node_dim)
        self.edge_dim = int(edge_dim)
        self.scalar_dim = int(scalar_dim)
        self.hidden_dim = int(hidden_dim)
        self.theta_dim = len(THETA_NUMERIC_COLUMNS)
        self.theta_lo = torch.tensor(THETA_LO, dtype=torch.float32)
        self.theta_hi = torch.tensor(THETA_HI, dtype=torch.float32)
        self.topology_encoder = GraphGPSLiteEncoder(node_dim=node_dim, edge_dim=edge_dim, hidden_dim=hidden_dim, local_layers=2, global_layers=1, heads=4, dropout=0.0)
        self.c0_encoder = GraphGPSLiteEncoder(node_dim=node_dim, edge_dim=edge_dim, hidden_dim=hidden_dim, local_layers=2, global_layers=1, heads=4, dropout=0.0)
        self.f0_encoder = GraphGPSLiteEncoder(node_dim=node_dim, edge_dim=edge_dim, hidden_dim=hidden_dim, local_layers=2, global_layers=1, heads=4, dropout=0.0)
        self.od_encoder = ODSetEncoder(input_dim=6, hidden_dim=hidden_dim, heads=4, dropout=0.0)
        self.scalar_encoder = torch.nn.Sequential(
            torch.nn.Linear(scalar_dim, hidden_dim),
            torch.nn.LayerNorm(hidden_dim),
            torch.nn.SiLU(),
            torch.nn.Linear(hidden_dim, hidden_dim),
            torch.nn.SiLU(),
        )
        self.theta_encoder = torch.nn.Sequential(
            torch.nn.Linear(self.theta_dim, hidden_dim),
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
        self.regression_head = torch.nn.Linear(hidden_dim, 1)
        self.gain_head = torch.nn.Linear(hidden_dim, 1)
        self.quality_head = torch.nn.Linear(hidden_dim, 1)

    def module(self):
        import torch

        from .dual_stream_graph_actor import make_masked_graph_batch

        class _Module(torch.nn.Module):
            def __init__(self, outer: "GraphOutcomeCritic") -> None:
                super().__init__()
                self.topology_encoder = outer.topology_encoder
                self.c0_encoder = outer.c0_encoder
                self.f0_encoder = outer.f0_encoder
                self.od_encoder = outer.od_encoder
                self.scalar_encoder = outer.scalar_encoder
                self.theta_encoder = outer.theta_encoder
                self.fusion = outer.fusion
                self.regression_head = outer.regression_head
                self.gain_head = outer.gain_head
                self.quality_head = outer.quality_head
                self.register_buffer("theta_lo", outer.theta_lo)
                self.register_buffer("theta_hi", outer.theta_hi)

            def forward(self, graph_batch, od_tokens, od_mask, scalar_x, theta):
                span = (self.theta_hi - self.theta_lo).clamp_min(1.0e-6)
                theta_x = ((theta.float() - self.theta_lo) / span).clamp(0.0, 1.0)
                topo_repr = self.topology_encoder(make_masked_graph_batch(graph_batch, "topology"))
                c0_repr = self.c0_encoder(make_masked_graph_batch(graph_batch, "c0"))
                f0_repr = self.f0_encoder(make_masked_graph_batch(graph_batch, "f0"))
                od_repr = self.od_encoder(od_tokens, od_mask)
                scalar_repr = self.scalar_encoder(scalar_x.float())
                theta_repr = self.theta_encoder(theta_x)
                fused = self.fusion(torch.cat([topo_repr, c0_repr, f0_repr, od_repr, scalar_repr, theta_repr], dim=-1))
                return {
                    "success_regression_logit": self.regression_head(fused).squeeze(-1),
                    "success_gain_logit": self.gain_head(fused).squeeze(-1),
                    "quality_delta": self.quality_head(fused).squeeze(-1),
                }

        return _Module(self)

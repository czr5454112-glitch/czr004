"""DualTraffic-HGT-GCST hierarchical encoder."""

from __future__ import annotations

try:
    import torch
    from torch import nn
except Exception:  # pragma: no cover
    torch = None  # type: ignore
    nn = None  # type: ignore

from .graph_encoder import GraphBatch, GraphGPSLiteEncoder
from .od_encoder import ODSetEncoder
from .raster_encoder import RasterFlowEncoder


if nn is not None:

    class DualTrafficHGTEncoder(nn.Module):
        def __init__(self, node_dim: int = 9, edge_dim: int = 9, od_dim: int = 6, raster_channels: int = 8, hidden_dim: int = 192) -> None:
            super().__init__()
            self.graph = GraphGPSLiteEncoder(node_dim=node_dim, edge_dim=edge_dim, hidden_dim=hidden_dim, local_layers=3, global_layers=2)
            self.od = ODSetEncoder(input_dim=od_dim, hidden_dim=hidden_dim)
            self.raster = RasterFlowEncoder(in_channels=raster_channels, hidden_dim=hidden_dim)
            self.fuse = nn.Sequential(nn.Linear(hidden_dim * 3 + 4, hidden_dim), nn.GELU(), nn.LayerNorm(hidden_dim))

        def forward(self, graph_batch: GraphBatch, od_tokens: "torch.Tensor", od_mask: "torch.Tensor | None", raster: "torch.Tensor", budget_features: "torch.Tensor") -> "torch.Tensor":
            g = self.graph(graph_batch)
            o = self.od(od_tokens, od_mask)
            r = self.raster(raster)
            return self.fuse(torch.cat([g, o, r, budget_features.float()], dim=-1))

else:

    class DualTrafficHGTEncoder:  # pragma: no cover
        def __init__(self, *args, **kwargs) -> None:
            raise ImportError("torch is required for DualTrafficHGTEncoder")

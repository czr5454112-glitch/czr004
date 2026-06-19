"""Raster/flow branch for DualTraffic-HGT-GCST."""

from __future__ import annotations

try:
    import torch
    from torch import nn
except Exception:  # pragma: no cover
    torch = None  # type: ignore
    nn = None  # type: ignore


if nn is not None:

    class RasterFlowEncoder(nn.Module):
        def __init__(self, in_channels: int = 8, hidden_dim: int = 192) -> None:
            super().__init__()
            self.net = nn.Sequential(
                nn.Conv2d(in_channels, 64, kernel_size=3, padding=1),
                nn.GELU(),
                nn.Conv2d(64, 96, kernel_size=3, padding=1),
                nn.GELU(),
                nn.AdaptiveAvgPool2d((4, 4)),
                nn.Flatten(),
                nn.Linear(96 * 16, hidden_dim),
                nn.LayerNorm(hidden_dim),
            )

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            return self.net(x.float())

else:

    class RasterFlowEncoder:  # pragma: no cover
        def __init__(self, *args, **kwargs) -> None:
            raise ImportError("torch is required for RasterFlowEncoder")

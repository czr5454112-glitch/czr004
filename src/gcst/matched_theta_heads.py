"""Matched g556-anchored theta heads and controls for G5.65."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .leakage_free_features import PRE_SOLVER_SCALAR_FEATURES
from .theta_schema import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS


MATCHED_RESIDUAL_SCALE = 0.30


@dataclass(frozen=True)
class MatchedHeadConfig:
    residual_scale: float = MATCHED_RESIDUAL_SCALE
    init_delta_zero: bool = True
    anchor: str = "g556_c063174"
    theta_dim: int = len(THETA_NUMERIC_COLUMNS)


def initialize_linear_zero(layer: Any) -> None:
    import torch

    if isinstance(layer, torch.nn.Linear):
        torch.nn.init.zeros_(layer.weight)
        if layer.bias is not None:
            torch.nn.init.zeros_(layer.bias)


def zero_delta_heads(module: Any) -> None:
    """Zero final delta/theta heads so residual actors start exactly at g556."""

    for name in ["delta_head", "theta_head"]:
        layer = getattr(module, name, None)
        if layer is not None:
            initialize_linear_zero(layer)


def model_starts_at_g556(model: Any, *inputs: Any, atol: float = 1.0e-6) -> bool:
    import torch

    model.eval()
    with torch.no_grad():
        out = model(*inputs)
    target = torch.as_tensor(BASELINE_G556, dtype=out.dtype, device=out.device).view(1, -1).expand_as(out)
    return bool(torch.allclose(out, target, atol=atol, rtol=0.0))


class GlobalResidualTheta:
    """One learned global residual theta.  Control only, not production model."""

    model_kind = "B1_global_residual"
    residual_scale = MATCHED_RESIDUAL_SCALE

    def __init__(self) -> None:
        import torch

        self.delta = torch.nn.Parameter(torch.zeros(len(THETA_NUMERIC_COLUMNS), dtype=torch.float32))
        self.trust_logit = torch.nn.Parameter(torch.zeros(len(THETA_NUMERIC_COLUMNS), dtype=torch.float32))

    def module(self):
        import torch

        outer = self

        class _Module(torch.nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.delta = outer.delta
                self.trust_logit = outer.trust_logit
                self.register_buffer("anchor", torch.as_tensor(BASELINE_G556, dtype=torch.float32))
                self.register_buffer("lo", torch.as_tensor(THETA_LO, dtype=torch.float32))
                self.register_buffer("hi", torch.as_tensor(THETA_HI, dtype=torch.float32))
                self.residual_scale = MATCHED_RESIDUAL_SCALE

            def forward(self, batch_size_or_x=1):
                if hasattr(batch_size_or_x, "shape"):
                    batch_size = int(batch_size_or_x.shape[0])
                else:
                    batch_size = int(batch_size_or_x)
                trust = torch.sigmoid(self.trust_logit)
                theta = self.anchor + trust * (self.hi - self.lo) * self.residual_scale * torch.tanh(self.delta)
                return torch.clamp(theta, self.lo, self.hi).view(1, -1).expand(batch_size, -1)

        return _Module()


class ScalarResidualActor:
    """Leakage-free pre-solver scalar control with matched residual output."""

    model_kind = "B2_scalar_pre_solver_residual"
    residual_scale = MATCHED_RESIDUAL_SCALE

    def __init__(self, hidden_dim: int = 64, scalar_dim: int = len(PRE_SOLVER_SCALAR_FEATURES)) -> None:
        import torch

        self.hidden_dim = int(hidden_dim)
        self.scalar_dim = int(scalar_dim)
        self.body = torch.nn.Sequential(
            torch.nn.Linear(self.scalar_dim, self.hidden_dim),
            torch.nn.SiLU(),
            torch.nn.Linear(self.hidden_dim, self.hidden_dim),
            torch.nn.SiLU(),
        )
        self.delta_head = torch.nn.Linear(self.hidden_dim, len(THETA_NUMERIC_COLUMNS))
        self.trust_head = torch.nn.Linear(self.hidden_dim, len(THETA_NUMERIC_COLUMNS))
        initialize_linear_zero(self.delta_head)

    def module(self):
        import torch

        outer = self

        class _Module(torch.nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.body = outer.body
                self.delta_head = outer.delta_head
                self.trust_head = outer.trust_head
                self.register_buffer("anchor", torch.as_tensor(BASELINE_G556, dtype=torch.float32))
                self.register_buffer("lo", torch.as_tensor(THETA_LO, dtype=torch.float32))
                self.register_buffer("hi", torch.as_tensor(THETA_HI, dtype=torch.float32))
                self.residual_scale = MATCHED_RESIDUAL_SCALE

            def forward(self, scalar_x):
                h = self.body(scalar_x.float())
                trust = torch.sigmoid(self.trust_head(h))
                raw = torch.tanh(self.delta_head(h))
                theta = self.anchor + trust * (self.hi - self.lo) * self.residual_scale * raw
                return torch.clamp(theta, self.lo, self.hi)

        return _Module()


def matched_output_metadata(model_kind: str) -> dict[str, Any]:
    return {
        "model_kind": model_kind,
        "output_parameterization": "g556_anchor_trust_tanh_residual",
        "anchor": "g556_c063174",
        "residual_scale": MATCHED_RESIDUAL_SCALE,
        "theta_bounds_low": [float(v) for v in THETA_LO],
        "theta_bounds_high": [float(v) for v in THETA_HI],
        "theta_columns": list(THETA_NUMERIC_COLUMNS),
        "step_zero_outputs_g556": True,
    }


def theta_distance_to_g556(theta: np.ndarray) -> float:
    span = np.maximum(THETA_HI - THETA_LO, 1.0e-6)
    return float(np.mean(np.abs((np.asarray(theta, dtype=np.float32) - BASELINE_G556) / span)))

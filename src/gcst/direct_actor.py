"""Direct continuous GCST actor for Repair5G.5.60."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .label_v4 import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS
from .schemas_v51 import parse_bool

ACTOR_INSTANCE_FEATURES = [
    "agent_count",
    "nominal_budget_ms",
    "requested_agent_count",
    "physical_free_cell_count",
    "agent_density",
    "encoded_OD_token_count",
    "represented_agent_mass",
    "represented_flow_mass",
    "path_found_rate",
    "base_time_limit_sec",
    "ltm_max_iterations",
]
ACTOR_BOOL_FEATURES = ["nonzero_flow"]
ACTOR_FEATURE_SCHEMA = ACTOR_INSTANCE_FEATURES + ACTOR_BOOL_FEATURES


def _float(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        value = float(row.get(key, default))
    except Exception:
        return default
    return value if np.isfinite(value) else default


def actor_features(row: dict[str, Any]) -> np.ndarray:
    values = [_float(row, key) for key in ACTOR_INSTANCE_FEATURES]
    values.extend(float(parse_bool(row.get(key))) for key in ACTOR_BOOL_FEATURES)
    return np.asarray(values, dtype=np.float32)


def theta_vector_from_row(row: dict[str, Any]) -> np.ndarray:
    return np.asarray([_float(row, key, float(BASELINE_G556[idx])) for idx, key in enumerate(THETA_NUMERIC_COLUMNS)], dtype=np.float32)


@dataclass(frozen=True)
class ActorNormalizer:
    mean: np.ndarray
    std: np.ndarray

    @classmethod
    def fit(cls, x: np.ndarray) -> "ActorNormalizer":
        mean = x.mean(axis=0).astype(np.float32)
        std = x.std(axis=0).astype(np.float32)
        std[std < 1.0e-6] = 1.0
        return cls(mean=mean, std=std)

    def transform(self, x: np.ndarray) -> np.ndarray:
        return ((x - self.mean) / self.std).astype(np.float32)

    def as_json(self) -> dict[str, list[float]]:
        return {"mean": self.mean.astype(float).tolist(), "std": self.std.astype(float).tolist()}


class DirectGCSTActor:
    """One-forward bounded residual actor.

    The actor emits exactly one continuous theta per instance.  The residual is
    shrunk by a learned trust head and projected to the G556 bounds.
    """

    def __init__(self, input_dim: int, hidden_dim: int = 128, residual_scale: float = 0.35) -> None:
        import torch

        self.input_dim = int(input_dim)
        self.hidden_dim = int(hidden_dim)
        self.residual_scale = float(residual_scale)
        self.theta_dim = len(THETA_NUMERIC_COLUMNS)
        self.anchor = torch.tensor(BASELINE_G556, dtype=torch.float32)
        self.lo = torch.tensor(THETA_LO, dtype=torch.float32)
        self.hi = torch.tensor(THETA_HI, dtype=torch.float32)
        self.span = self.hi - self.lo
        self.encoder = torch.nn.Sequential(
            torch.nn.Linear(self.input_dim, hidden_dim),
            torch.nn.LayerNorm(hidden_dim),
            torch.nn.SiLU(),
            torch.nn.Linear(hidden_dim, hidden_dim),
            torch.nn.LayerNorm(hidden_dim),
            torch.nn.SiLU(),
            torch.nn.Linear(hidden_dim, hidden_dim),
            torch.nn.SiLU(),
        )
        self.delta_head = torch.nn.Linear(hidden_dim, self.theta_dim)
        self.trust_head = torch.nn.Linear(hidden_dim, self.theta_dim)

    def module(self):
        import torch

        class _Module(torch.nn.Module):
            def __init__(self, outer: "DirectGCSTActor") -> None:
                super().__init__()
                self.encoder = outer.encoder
                self.delta_head = outer.delta_head
                self.trust_head = outer.trust_head
                self.register_buffer("anchor", outer.anchor)
                self.register_buffer("lo", outer.lo)
                self.register_buffer("hi", outer.hi)
                self.register_buffer("span", outer.span)
                self.residual_scale = outer.residual_scale

            def forward(self, x):
                hidden = self.encoder(x)
                delta_raw = self.delta_head(hidden)
                trust = torch.sigmoid(self.trust_head(hidden))
                delta = trust * self.span * self.residual_scale * torch.tanh(delta_raw)
                return torch.clamp(self.anchor + delta, self.lo, self.hi)

        return _Module(self)


def project_theta(theta: np.ndarray) -> np.ndarray:
    return np.minimum(np.maximum(theta.astype(np.float32), THETA_LO), THETA_HI).astype(np.float32)

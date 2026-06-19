"""Training-time auxiliary solver-outcome critic for G5.60."""

from __future__ import annotations

from typing import Any

import numpy as np

from .direct_actor import ACTOR_FEATURE_SCHEMA, actor_features, theta_vector_from_row
from .label_v4 import THETA_NUMERIC_COLUMNS

AUX_CRITIC_FEATURE_SCHEMA = ACTOR_FEATURE_SCHEMA + THETA_NUMERIC_COLUMNS


def critic_features(row: dict[str, Any]) -> np.ndarray:
    return np.concatenate([actor_features(row), theta_vector_from_row(row)]).astype(np.float32)


class AuxiliaryOutcomeCritic:
    def __init__(self, input_dim: int, hidden_dim: int = 128) -> None:
        import torch

        self.module = torch.nn.Sequential(
            torch.nn.Linear(input_dim, hidden_dim),
            torch.nn.LayerNorm(hidden_dim),
            torch.nn.SiLU(),
            torch.nn.Linear(hidden_dim, hidden_dim),
            torch.nn.LayerNorm(hidden_dim),
            torch.nn.SiLU(),
            torch.nn.Linear(hidden_dim, 4),
        )


def split_heads(output):
    return {
        "risk_logit": output[:, 0],
        "gain_logit": output[:, 1],
        "quality": output[:, 2],
        "uncertainty": output[:, 3],
    }

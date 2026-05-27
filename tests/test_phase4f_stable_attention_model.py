from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

torch = pytest.importorskip("torch")

from models.laur_stable_attention import (  # noqa: E402
    EDGE_TRACE_TRANSFORMER_NAME,
    SET_RULE_TRANSFORMER_NAME,
    build_model,
)
from train.losses_laur_stable_attention import laur_stable_attention_loss  # noqa: E402


def _batch() -> dict:
    return {
        "global_features": torch.zeros(2, 5),
        "edge_tokens": torch.zeros(2, 4, 6),
        "edge_mask": torch.tensor([[1, 1, 0, 0], [1, 0, 0, 0]], dtype=torch.bool),
        "trace_tokens": torch.zeros(2, 3, 4),
        "trace_mask": torch.tensor([[1, 1, 0], [1, 0, 0]], dtype=torch.bool),
        "rule_tokens": torch.zeros(2, 8, 7),
        "rule_target": torch.tensor([0, 3]),
        "family_target": torch.tensor([0, 2]),
        "neutral_target": torch.tensor([1.0, 0.0]),
        "confidence_target": torch.tensor([0.1, 0.8]),
        "soft_rule_target_stable": torch.full((2, 8), 1.0 / 8.0),
        "delta_target": torch.zeros(2, 8),
        "harmful_target": torch.zeros(2, 8),
    }


def test_lau_set_rule_transformer_forward_and_loss_shapes() -> None:
    model = build_model(
        SET_RULE_TRANSFORMER_NAME,
        global_dim=5,
        edge_dim=6,
        trace_dim=4,
        rule_dim=7,
        num_rules=8,
        num_families=5,
        d_model=16,
        n_heads=4,
        n_layers=1,
        dropout=0.0,
    )
    batch = _batch()
    outputs = model(batch)
    assert outputs["q_delta"].shape == (2, 8)
    assert outputs["harmful_logit"].shape == (2, 8)
    assert outputs["family_logits"].shape == (2, 8, 5)
    assert outputs["confidence_logit"].shape == (2, 8)
    losses = laur_stable_attention_loss(outputs, batch, additive_index=0)
    assert torch.isfinite(losses["total"])


def test_lau_edge_trace_transformer_forward_shape() -> None:
    model = build_model(
        EDGE_TRACE_TRANSFORMER_NAME,
        global_dim=5,
        edge_dim=6,
        trace_dim=4,
        rule_dim=7,
        num_rules=8,
        num_families=5,
        d_model=16,
        n_heads=4,
        n_layers=1,
        dropout=0.0,
    )
    outputs = model(_batch())
    assert outputs["q_delta"].shape == (2, 8)

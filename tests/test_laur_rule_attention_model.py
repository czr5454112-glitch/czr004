from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

torch = pytest.importorskip("torch")

from models.laur_rule_attention import EDGE_TRACE_MODEL_NAME, LAURuleAttentionModel  # noqa: E402
from train.losses_laur_rule_attention import laur_rule_attention_loss  # noqa: E402


def test_laur_rule_attention_forward_and_loss_shapes() -> None:
    model = LAURuleAttentionModel(
        global_dim=5,
        edge_dim=4,
        trace_dim=3,
        rule_dim=6,
        num_rules=8,
        num_families=5,
        d_model=16,
        nhead=4,
        num_layers=1,
        dropout=0.0,
        architecture=EDGE_TRACE_MODEL_NAME,
    )
    batch = {
        "global_features": torch.zeros(2, 5),
        "edge_tokens": torch.zeros(2, 3, 4),
        "edge_mask": torch.tensor([[1, 1, 0], [1, 0, 0]], dtype=torch.bool),
        "trace_tokens": torch.zeros(2, 2, 3),
        "trace_mask": torch.tensor([[1, 0], [1, 1]], dtype=torch.bool),
        "rule_tokens": torch.zeros(2, 8, 6),
        "rule_target": torch.tensor([0, 3]),
        "family_target": torch.tensor([0, 3]),
        "neutral_target": torch.tensor([1.0, 0.0]),
        "soft_rule_target": torch.full((2, 8), 1.0 / 8.0),
        "delta_target": torch.zeros(2, 8),
        "harmful_target": torch.zeros(2, 8),
    }

    outputs = model(batch)

    assert outputs["rule_score"].shape == (2, 8)
    assert outputs["harmful_logit"].shape == (2, 8)
    assert outputs["family_logits"].shape == (2, 8, 5)
    losses = laur_rule_attention_loss(outputs, batch, additive_index=0)
    assert torch.isfinite(losses["total"])

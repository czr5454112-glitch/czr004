"""Shared G5.65 edge-attention actor constructors."""

from __future__ import annotations

from .light_edge_attention_actor import LightEdgeAttentionActor, LightEdgeAttentionConfig
from .matched_theta_heads import matched_output_metadata, zero_delta_heads


def make_shared_edge_attention_actor(*, hidden_dim: int = 64, local_layers: int = 2, residual_scale: float = 0.30):
    """Create the matched-initialized E1 actor used by G5.65."""

    model = LightEdgeAttentionActor(
        LightEdgeAttentionConfig(hidden_dim=hidden_dim, local_layers=local_layers, residual_scale=residual_scale)
    ).module()
    zero_delta_heads(model)
    return model


def shared_edge_attention_metadata() -> dict[str, object]:
    meta = matched_output_metadata("E1")
    meta.update(
        {
            "shared_edge_attention_actor": True,
            "starts_at_g556": True,
            "residual_anchor": "g556",
        }
    )
    return meta

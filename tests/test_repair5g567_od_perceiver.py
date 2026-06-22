from __future__ import annotations

import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5g567_strict_pipeline as g567  # noqa: E402
from gcst.dual_stream_graph_actor import DualStreamGoalAwareActor, architecture_from_id
from gcst.goal_aware_actor import GOAL_AWARE_SCALAR_FEATURES
from gcst.graph_encoder import EdgeAwareAttentionLayer, GraphBatch


def _model(hidden_dim: int = 64, latent_tokens: int = 16):
    arch = architecture_from_id("A5")
    return DualStreamGoalAwareActor(
        hidden_dim=hidden_dim,
        use_cross_attention=arch.use_cross_attention,
        safe_subspace=arch.safe_subspace,
        field_group_trust=arch.field_group_trust,
        od_perceiver=arch.od_perceiver,
        graph_local_layers=arch.graph_local_layers,
        graph_global_layers=arch.graph_global_layers,
        heads=arch.heads,
        latent_tokens=latent_tokens,
    ).module()


def _graph_batch(num_graphs: int = 1) -> GraphBatch:
    node_features = torch.zeros((2 * num_graphs, 9), dtype=torch.float32)
    batch_index = torch.arange(num_graphs, dtype=torch.long).repeat_interleave(2)
    return GraphBatch(
        node_features=node_features,
        edge_index=torch.zeros((2, 0), dtype=torch.long),
        edge_features=torch.zeros((0, 9), dtype=torch.float32),
        batch_index=batch_index,
        num_graphs=num_graphs,
    )


def test_a5_uses_od_perceiver_instead_of_full_od_self_attention() -> None:
    model = _model()

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("A5 should not use ODSetEncoder full token self-attention")

    model.od_encoder.forward = fail_if_called  # type: ignore[method-assign]
    od_tokens = torch.zeros((1, 3000, 6), dtype=torch.float32)
    od_mask = torch.ones((1, 3000), dtype=torch.bool)
    scalars = torch.zeros((1, len(GOAL_AWARE_SCALAR_FEATURES)), dtype=torch.float32)
    with torch.no_grad():
        theta = model(_graph_batch(), od_tokens, od_mask, scalars)
    assert theta.shape == (1, 15)


def test_a5_last_od_token_affects_output_gradient() -> None:
    torch.manual_seed(567)
    model = _model()
    od_tokens = torch.randn((1, 3000, 6), dtype=torch.float32) * 0.01
    od_tokens.requires_grad_(True)
    od_mask = torch.ones((1, 3000), dtype=torch.bool)
    scalars = torch.zeros((1, len(GOAL_AWARE_SCALAR_FEATURES)), dtype=torch.float32)
    theta = model(_graph_batch(), od_tokens, od_mask, scalars)
    theta.sum().backward()
    assert od_tokens.grad is not None
    assert float(od_tokens.grad[0, 2999].abs().sum()) > 0.0


def test_a5_is_permutation_invariant_over_valid_od_pairs() -> None:
    torch.manual_seed(568)
    model = _model()
    model.eval()
    od_tokens = torch.randn((1, 3000, 6), dtype=torch.float32) * 0.01
    od_mask = torch.ones((1, 3000), dtype=torch.bool)
    scalars = torch.zeros((1, len(GOAL_AWARE_SCALAR_FEATURES)), dtype=torch.float32)
    perm = torch.randperm(3000)
    with torch.no_grad():
        theta_a = model(_graph_batch(), od_tokens, od_mask, scalars)
        theta_b = model(_graph_batch(), od_tokens[:, perm], od_mask[:, perm], scalars)
    assert torch.allclose(theta_a, theta_b, atol=1.0e-5, rtol=1.0e-5)


def test_a5_ignores_masked_padding_tokens() -> None:
    torch.manual_seed(569)
    model = _model()
    model.eval()
    od_tokens = torch.randn((1, 3000, 6), dtype=torch.float32) * 0.01
    od_mask = torch.zeros((1, 3000), dtype=torch.bool)
    od_mask[:, :64] = True
    altered = od_tokens.clone()
    altered[:, 64:] = torch.randn_like(altered[:, 64:]) * 1000.0
    scalars = torch.zeros((1, len(GOAL_AWARE_SCALAR_FEATURES)), dtype=torch.float32)
    with torch.no_grad():
        theta_a = model(_graph_batch(), od_tokens, od_mask, scalars)
        theta_b = model(_graph_batch(), altered, od_mask, scalars)
    assert torch.allclose(theta_a, theta_b, atol=1.0e-6, rtol=1.0e-6)


def test_a5_production_config_mixed_agent_batch_forward_backward() -> None:
    torch.manual_seed(570)
    model = _model(hidden_dim=256, latent_tokens=96)
    lengths = [64, 1000, 3000]
    od_tokens = torch.zeros((3, 3000, 6), dtype=torch.float32)
    od_mask = torch.zeros((3, 3000), dtype=torch.bool)
    for row, length in enumerate(lengths):
        od_tokens[row, :length] = torch.randn((length, 6), dtype=torch.float32) * 0.01
        od_mask[row, :length] = True
    scalars = torch.zeros((3, len(GOAL_AWARE_SCALAR_FEATURES)), dtype=torch.float32)
    theta = model(_graph_batch(num_graphs=3), od_tokens, od_mask, scalars)
    assert theta.shape == (3, 15)
    theta.sum().backward()
    assert any(param.grad is not None for param in model.parameters())


def test_edge_attention_casts_autocast_softmax_weights_back_to_bf16(monkeypatch) -> None:
    original_softmax = torch.softmax

    def softmax_promoted_to_fp32(input, *args, **kwargs):
        return original_softmax(input.float(), *args, **kwargs)

    monkeypatch.setattr(torch, "softmax", softmax_promoted_to_fp32)
    layer = EdgeAwareAttentionLayer(8, 3, dropout=0.0).to(torch.bfloat16)
    h = torch.randn((3, 8), dtype=torch.bfloat16)
    edge_index = torch.tensor([[0, 1, 2, 0], [1, 2, 0, 2]], dtype=torch.long)
    edge_features = torch.randn((4, 3), dtype=torch.bfloat16)

    out = layer(h, edge_index, edge_features)

    assert out.dtype == torch.bfloat16
    assert out.shape == h.shape


def test_edge_attention_casts_autocast_messages_to_accumulator_dtype() -> None:
    layer = EdgeAwareAttentionLayer(8, 3, dropout=0.0)
    h = torch.randn((3, 8), dtype=torch.float32)
    edge_index = torch.tensor([[0, 1, 2, 0], [1, 2, 0, 2]], dtype=torch.long)
    edge_features = torch.randn((4, 3), dtype=torch.float32)

    with torch.autocast(device_type="cpu", dtype=torch.bfloat16):
        out = layer(h, edge_index, edge_features)

    assert out.dtype == torch.float32
    assert out.shape == h.shape


def test_large_scale_actor_variants_disable_full_node_global_attention() -> None:
    for variant_id in ["A5", "A6", "A7"]:
        arch = architecture_from_id(variant_id)
        assert arch.od_perceiver
        assert arch.graph_global_layers == 0


def test_load_model_for_payload_honors_attention_heads_alias() -> None:
    arch = architecture_from_id("A5")
    model = DualStreamGoalAwareActor(
        hidden_dim=64,
        use_cross_attention=arch.use_cross_attention,
        safe_subspace=arch.safe_subspace,
        field_group_trust=arch.field_group_trust,
        od_perceiver=arch.od_perceiver,
        graph_local_layers=arch.graph_local_layers,
        graph_global_layers=arch.graph_global_layers,
        heads=arch.heads,
        latent_tokens=16,
    ).module()
    payload = {
        "variant_id": "A5",
        "hidden_dim": 64,
        "use_cross_attention": True,
        "safe_subspace": True,
        "field_group_trust": True,
        "od_perceiver": True,
        "graph_local_layers": arch.graph_local_layers,
        "graph_global_layers": arch.graph_global_layers,
        "attention_heads": arch.heads,
        "latent_tokens": 16,
        "actor_state_dict": model.state_dict(),
    }
    loaded, kind = g567.load_model_for_payload(payload, Path("unit_a5_attention_heads_alias.pt"), "cpu")
    assert kind == "A5"
    assert loaded.od_latents.shape[0] == 16

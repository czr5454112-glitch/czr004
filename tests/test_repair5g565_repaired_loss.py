from __future__ import annotations

import importlib

import numpy as np
import pytest

from gcst.c0_f0_representation import representation_audit_row
from gcst.graph_data import GraphData
from gcst.graph_encoder import GraphBatch
from gcst.label_v52_set import CENSORED_UNKNOWN, context_from_rows
from gcst.matched_theta_heads import ScalarResidualActor, model_starts_at_g556
from gcst.repaired_set_risk import (
    DEFAULT_REPAIRED_RISK,
    RepairedRiskConfig,
    context_loss_np,
    context_loss_torch,
    loss_item_from_context,
)
from gcst.rich_training_g565 import make_model
from gcst.theta_schema import BASELINE_G556, THETA_NUMERIC_COLUMNS, clamp_numeric_theta


def row(uid: str, idx: int, *, safe: bool = True, comparable: bool = True, delta: float = 0.0, gain: bool = False, regression: bool = False, theta_shift: float = 0.0):
    out = {
        "g560_evaluation_uid": uid,
        "g560_instance_uid": f"inst_{uid}",
        "split": "train",
        "g560_physical_map_sha256": f"hash_{uid}",
        "map": "empty-8-8",
        "map_family": "empty",
        "agent_count": "8",
        "nominal_budget_ms": "500",
        "labelv51_development_safe": str(safe),
        "labelv51_comparable_quality": str(comparable),
        "quality_delta_vs_g556": str(delta),
        "labelv51_success_gain": str(gain),
        "labelv51_success_regression": str(regression),
        "candidate_uid": f"{uid}_{idx}",
    }
    for col_i, col in enumerate(THETA_NUMERIC_COLUMNS):
        out[col] = str(float(BASELINE_G556[col_i] + theta_shift))
    return out


@pytest.mark.skipif(importlib.util.find_spec("torch") is None, reason="torch unavailable")
def test_numpy_torch_loss_parity():
    import torch

    context = context_from_rows(
        "ctx",
        [
            row("ctx", 0, safe=True, comparable=True, delta=-0.2, gain=True, theta_shift=0.1),
            row("ctx", 1, safe=False, comparable=True, delta=0.3, theta_shift=0.3),
        ],
    )
    theta = clamp_numeric_theta(BASELINE_G556 + 0.05)
    np_loss, _ = context_loss_np(theta, context, DEFAULT_REPAIRED_RISK)
    torch_loss, _ = context_loss_torch(torch.tensor(theta, dtype=torch.float32), loss_item_from_context(context), DEFAULT_REPAIRED_RISK)
    assert float(torch_loss.detach().cpu()) == pytest.approx(np_loss, abs=1.0e-6)


def test_loss_config_hash_is_recorded_and_shared():
    cfg = RepairedRiskConfig(positive_loss="hard_wta", harmful_loss="topk_cvar_adaptive")
    assert cfg.sha256 == RepairedRiskConfig(positive_loss="hard_wta", harmful_loss="topk_cvar_adaptive").sha256
    assert cfg.sha256 != DEFAULT_REPAIRED_RISK.sha256


def test_floor_corrected_loss_at_mode():
    context = context_from_rows("ctx", [row("ctx", 0, safe=True, comparable=True, delta=-0.2, gain=True, theta_shift=0.1)])
    loss, terms = context_loss_np(context.positive_thetas[0], context, DEFAULT_REPAIRED_RISK)
    assert terms["positive_loss"] == pytest.approx(0.0, abs=1.0e-7)
    assert loss >= 0.0


def test_nearest_and_topk_harmful_loss_not_diluted():
    context = context_from_rows(
        "ctx",
        [
            row("ctx", 0, safe=True, comparable=True, delta=-0.2, gain=True, theta_shift=0.0),
            row("ctx", 1, safe=False, comparable=True, delta=0.4, theta_shift=0.0001),
            row("ctx", 2, safe=False, comparable=True, delta=0.4, theta_shift=0.5),
        ],
    )
    nearest_cfg = RepairedRiskConfig(harmful_loss="nearest_adaptive")
    topk_cfg = RepairedRiskConfig(harmful_loss="topk_cvar_adaptive", topk_harmful=1)
    theta = context.harmful_thetas[0]
    nearest, n_terms = context_loss_np(theta, context, nearest_cfg)
    topk, t_terms = context_loss_np(theta, context, topk_cfg)
    assert n_terms["harmful_loss"] > 0.0
    assert t_terms["harmful_loss"] > 0.0
    assert nearest == pytest.approx(topk, abs=1.0e-6)


@pytest.mark.skipif(importlib.util.find_spec("torch") is None, reason="torch unavailable")
def test_censored_context_has_no_harmful_gradient():
    import torch

    context = context_from_rows("c", [row("c", 0, safe=False, comparable=False)])
    assert context.label_state == CENSORED_UNKNOWN
    item = loss_item_from_context(context)
    item["harmful_thetas"] = np.stack([BASELINE_G556]).astype(np.float32)
    theta = torch.tensor(BASELINE_G556 + 0.02, dtype=torch.float32, requires_grad=True)
    loss, terms = context_loss_torch(theta, item, DEFAULT_REPAIRED_RISK)
    loss.backward()
    assert float(terms["harmful_loss"]) == pytest.approx(0.0)
    assert theta.grad is not None


@pytest.mark.skipif(importlib.util.find_spec("torch") is None, reason="torch unavailable")
def test_global_scalar_rich_start_at_g556():
    import torch

    scalar_x = torch.zeros((2, 7), dtype=torch.float32)
    b2 = ScalarResidualActor(hidden_dim=8).module()
    assert model_starts_at_g556(b2, scalar_x)
    graph = GraphBatch(
        node_features=torch.zeros((2, 9), dtype=torch.float32),
        edge_index=torch.tensor([[0, 1], [1, 0]], dtype=torch.long),
        edge_features=torch.zeros((2, 9), dtype=torch.float32),
        batch_index=torch.zeros((2,), dtype=torch.long),
        num_graphs=1,
    )
    od = torch.zeros((1, 2, 6), dtype=torch.float32)
    mask = torch.ones((1, 2), dtype=torch.bool)
    rich_scalar = torch.zeros((1, 7), dtype=torch.float32)
    for kind in ["E0", "E1", "E2"]:
        model = make_model(kind, hidden_dim=8, device="cpu")
        assert model_starts_at_g556(model, graph, od, mask, rich_scalar)


def test_c0_f0_are_not_aliases_and_hashes_are_separate():
    edge_features = np.zeros((2, 9), dtype=np.float32)
    edge_features[:, 5] = [1.0, 0.0]
    edge_features[:, 6] = [0.0, 1.0]
    graph = GraphData(
        topology_id="t",
        map_name="m",
        width=2,
        height=1,
        cells=[(0, 0), (1, 0)],
        node_features=np.zeros((2, 9), dtype=np.float32),
        edge_index=np.asarray([[0, 1], [1, 0]], dtype=np.int64),
        edge_features=edge_features,
        hashes={},
    )
    assignment = {"starts": [(0, 0)], "goals": [(1, 0)], "od_tokens": np.ones((1, 6), dtype=np.float32)}
    audit = representation_audit_row("ctx", graph, assignment)
    assert audit["c0_f0_hashes_equal"] is False
    assert audit["start_goal_mass_used"] is True


@pytest.mark.skipif(importlib.util.find_spec("torch") is None, reason="torch unavailable")
def test_edge_attention_segment_softmax_matches_naive():
    import torch

    from gcst.graph_encoder import EdgeAwareAttentionLayer

    torch.manual_seed(565)
    layer = EdgeAwareAttentionLayer(8, 3, dropout=0.0)
    h = torch.randn(7, 8)
    edge_index = torch.tensor([[0, 1, 2, 3, 4, 5, 0, 2, 6], [1, 1, 3, 3, 3, 6, 6, 6, 6]])
    edge_features = torch.randn(edge_index.size(1), 3)

    def naive_forward():
        src, dst = edge_index[0].long(), edge_index[1].long()
        e = layer.edge_proj(edge_features)
        logits = layer.attn(torch.cat([h[src], h[dst], e], dim=-1)).squeeze(-1)
        weights = torch.zeros_like(logits)
        for node in torch.unique(dst):
            mask = dst == node
            weights[mask] = torch.softmax(logits[mask], dim=0)
        msg = layer.msg(torch.cat([h[src], e], dim=-1)) * weights.unsqueeze(-1)
        agg = torch.zeros_like(h)
        agg.index_add_(0, dst, msg)
        out = layer.norm(h + layer.drop(agg))
        return layer.norm(out + layer.drop(layer.ff(out)))

    assert torch.allclose(layer(h, edge_index, edge_features), naive_forward(), atol=1.0e-6, rtol=1.0e-6)

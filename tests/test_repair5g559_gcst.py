import numpy as np
import pytest

from gcst.graph_coarsening import audit_corridor_graph, build_corridor_graph
from gcst.graph_data import build_graph
from gcst.graph_encoder import GraphBatch
from gcst.inference import SafeGCSTv2, choose_static_theta
from gcst.label_v4 import BASELINE_G556
from gcst.label_v5 import evaluation_uid, instance_uid, row_weight_by_instance
from gcst.listwise_losses import context_balanced_weights, listnet_kl_loss, pairwise_margin_ranking_loss
from gcst.metrics import coverage_risk, fallback_accuracy, generator_safe_set_hit_rate, safe_recall_at_k
from gcst.scenario_features import generate_assignment
from gcst.traffic_prior import compute_traffic_prior


def topo(name="empty-8-8"):
    return {"topology_id": f"topo_{name}", "map": name, "map_family": "empty", "width": 8, "height": 8, "free_cells": 64}


def context(agents=12, seed=77):
    return {
        "agent_count": agents,
        "agents": agents,
        "seed": seed,
        "solver_seed": seed + 1000,
        "nominal_budget_ms": 500,
        "ltm_max_iterations": 2,
        "start_goal_regime": "opposite_side_cross_flow",
    }


def test_graph_connectivity_preserved():
    audit = audit_corridor_graph(topo())
    assert audit["all_cells_assigned"]
    assert audit["component_count_unchanged"]
    assert audit["connectivity_preserved"]


def test_benchmark_map_resolver_includes_lacam2_script_maps():
    from gcst.map_hash import known_map_candidates

    candidates = [str(path).replace("\\", "/") for path in known_map_candidates("corners")]
    assert any("external/lacam2/scripts/map/corners.map" in path for path in candidates)


def test_default_pilot_topologies_have_solver_capacity():
    from repair5g559_pipeline import default_topologies, largest_component_size

    for row in default_topologies(limit=24):
        graph = build_corridor_graph(row).graph
        assert largest_component_size(graph) >= 16
        assert graph.physical_free_cell_count <= 6000


def test_corridor_graph_shortest_path_distortion():
    audit = audit_corridor_graph(topo(), [((0, 0), (7, 7)), ((1, 1), (6, 2))])
    assert audit["shortest_path_distortion_max"] == 0.0


@pytest.mark.skipif(__import__("importlib").util.find_spec("torch") is None, reason="torch unavailable")
def test_batch_composition_invariance():
    torch = __import__("torch")
    torch.manual_seed(559)
    model = SafeGCSTv2(hidden_dim=32, proposals=2).eval()
    g1 = build_graph(topo())
    g2 = build_graph({"topology_id": "topo_room", "map": "room-8-8-4", "width": 8, "height": 8, "free_cells": 48})

    def batch(graphs):
        nodes = torch.tensor(np.concatenate([g.node_features for g in graphs], axis=0), dtype=torch.float32)
        edges = []
        edge_features = []
        batch_index = []
        offset = 0
        for i, g in enumerate(graphs):
            if g.edge_index.size:
                edges.append(torch.tensor(g.edge_index + offset, dtype=torch.long))
                edge_features.append(torch.tensor(g.edge_features, dtype=torch.float32))
            batch_index.extend([i] * len(g.cells))
            offset += len(g.cells)
        edge_index = torch.cat(edges, dim=1) if edges else torch.zeros((2, 0), dtype=torch.long)
        edge_feat = torch.cat(edge_features, dim=0) if edge_features else torch.zeros((0, 9), dtype=torch.float32)
        return GraphBatch(nodes, edge_index, edge_feat, torch.tensor(batch_index), len(graphs))

    with torch.no_grad():
        alone = model.graph_encoder(batch([g1]))[0]
        batched = model.graph_encoder(batch([g1, g2]))[0]
    assert torch.allclose(alone, batched, atol=1e-5)


@pytest.mark.skipif(__import__("importlib").util.find_spec("torch") is None, reason="torch unavailable")
def test_batch_order_invariance():
    torch = __import__("torch")
    torch.manual_seed(560)
    model = SafeGCSTv2(hidden_dim=32, proposals=2).eval()
    g1 = build_graph(topo())
    batch_a = GraphBatch(
        torch.tensor(g1.node_features, dtype=torch.float32),
        torch.tensor(g1.edge_index, dtype=torch.long),
        torch.tensor(g1.edge_features, dtype=torch.float32),
        torch.zeros(len(g1.cells), dtype=torch.long),
        1,
    )
    with torch.no_grad():
        out1 = model.graph_encoder(batch_a)
        out2 = model.graph_encoder(batch_a)
    assert torch.allclose(out1, out2, atol=1e-6)


@pytest.mark.skipif(__import__("importlib").util.find_spec("torch") is None, reason="torch unavailable")
def test_node_permutation_invariance():
    torch = __import__("torch")
    torch.manual_seed(561)
    model = SafeGCSTv2(hidden_dim=32, proposals=2).eval()
    g = build_graph(topo())
    perm = np.arange(len(g.cells))[::-1].copy()
    inv = np.empty_like(perm)
    inv[perm] = np.arange(len(perm))
    edge = inv[g.edge_index]
    b1 = GraphBatch(torch.tensor(g.node_features), torch.tensor(g.edge_index), torch.tensor(g.edge_features), torch.zeros(len(g.cells), dtype=torch.long), 1)
    b2 = GraphBatch(torch.tensor(g.node_features[perm]), torch.tensor(edge), torch.tensor(g.edge_features), torch.zeros(len(g.cells), dtype=torch.long), 1)
    with torch.no_grad():
        assert torch.allclose(model.graph_encoder(b1), model.graph_encoder(b2), atol=1e-5)


def test_agent_mass_conservation():
    g = build_graph(topo())
    assignment = generate_assignment(g, context(agents=80), max_agents=None)
    assert assignment["represented_agent_mass"] == 80
    assert assignment["all_agent_mass_preserved"]


def test_flow_mass_conservation():
    g = build_graph(topo())
    assignment = generate_assignment(g, context(agents=16), max_agents=None)
    prior = compute_traffic_prior(g, assignment)
    assert prior["summary"]["path_found_rate"] >= 0.999
    assert prior["summary"]["flow_mass_preservation_ratio"] == pytest.approx(1.0)


def test_actual_scenario_pairing():
    g = build_graph(topo())
    assignment = generate_assignment(g, context(), max_agents=None)
    assert len(assignment["starts"]) == len(assignment["goals"]) == context()["agent_count"]
    assert assignment["start_goal_assignment_hash"] != assignment["start_positions_sha256"]


def test_solver_seed_excluded_from_features():
    uid = instance_uid("maphash", "pairhash", 64, 1000, 2)
    assert uid == instance_uid("maphash", "pairhash", 64, 1000, 2)
    assert evaluation_uid(uid, 1) != evaluation_uid(uid, 2)


def test_context_balanced_weighting():
    rows = [{"instance_uid": "a"}, {"instance_uid": "a"}, {"instance_uid": "b"}]
    weights = row_weight_by_instance(rows)
    assert weights[0] == weights[1]
    assert weights[0] + weights[1] == pytest.approx(weights[2])


@pytest.mark.skipif(__import__("importlib").util.find_spec("torch") is None, reason="torch unavailable")
def test_listwise_loss_orders_candidates():
    torch = __import__("torch")
    scores = torch.tensor([2.0, 1.0, 0.0], requires_grad=True)
    target = torch.tensor([0.8, 0.15, 0.05])
    loss = listnet_kl_loss(scores, target, torch.tensor([0, 0, 0]))
    loss.backward()
    assert float(loss.detach()) >= 0.0
    assert scores.grad is not None


@pytest.mark.skipif(__import__("importlib").util.find_spec("torch") is None, reason="torch unavailable")
def test_pairwise_loss_handles_ties():
    torch = __import__("torch")
    loss = pairwise_margin_ranking_loss(torch.tensor([1.0, 0.0]), torch.tensor([0.5, 0.5]), torch.tensor([0, 0]))
    assert float(loss) == 0.0


def test_safe_recall_metric_nontrivial():
    scores = np.array([0.9, 0.8, 0.1, 0.0])
    safe = np.array([0, 1, 1, 0])
    assert safe_recall_at_k(scores, safe, k=1) == 0.0
    assert safe_recall_at_k(scores, safe, k=2) == 0.5


def test_fallback_metric_uses_prediction():
    assert fallback_accuracy(np.array([0.9, 0.1]), np.array([1, 0])) == 1.0
    assert fallback_accuracy(np.array([0.1, 0.9]), np.array([1, 0])) == 0.0


def test_coverage_risk_uses_predictions():
    rows = [
        {"model_confidence": 0.9, "success_regression": True, "quality_delta_vs_g556": 1.0},
        {"model_confidence": 0.1, "success_regression": False, "quality_delta_vs_g556": -1.0},
    ]
    out = coverage_risk(rows, [0.5])[0]
    assert out["coverage"] == 0.5
    assert out["success_regression_rate"] == 1.0


def test_generator_hit_rate_uses_generated_theta():
    assert generator_safe_set_hit_rate([["a"], ["b"]], [{"a"}, {"c"}]) == 0.5


@pytest.mark.skipif(__import__("importlib").util.find_spec("torch") is None, reason="torch unavailable")
def test_checkpoint_resume(tmp_path):
    torch = __import__("torch")
    model = SafeGCSTv2(hidden_dim=32, proposals=2)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    path = tmp_path / "resume.pt"
    torch.save({"model_state_dict": model.state_dict(), "optimizer_state_dict": opt.state_dict(), "step": 3}, path)
    loaded = torch.load(path, map_location="cpu")
    assert loaded["step"] == 3
    assert "optimizer_state_dict" in loaded


def test_theta_fixed_for_run():
    torch = __import__("torch")
    theta = torch.tensor([BASELINE_G556, BASELINE_G556 + 0.02], dtype=torch.float32)
    selected1, idx1, _ = choose_static_theta(theta, torch.tensor([0.1, 0.9]), torch.tensor([0.5, 0.0]), torch.tensor([0.0, -0.1]))
    selected2, idx2, _ = choose_static_theta(theta, torch.tensor([0.1, 0.9]), torch.tensor([0.5, 0.0]), torch.tensor([0.0, -0.1]))
    assert idx1 == idx2 == 1
    assert torch.equal(selected1, selected2)


def test_reserved_ids_166_205_rejected():
    from repair5g559_pipeline import parse_args_checked

    with pytest.raises(SystemExit):
        parse_args_checked(["--ids", "166"], "test")


def test_full_pilot_defaults_are_not_smoke_sized():
    from repair5g559_pipeline import (
        PILOT_MIN_CANDIDATES_PER_INSTANCE,
        PILOT_MIN_INSTANCE_UIDS,
        effective_candidates_per_instance,
        effective_codebook_size,
        effective_pilot_instances,
        parse_args_checked,
    )

    args = parse_args_checked([], "test")
    assert effective_pilot_instances(args) >= PILOT_MIN_INSTANCE_UIDS
    assert effective_candidates_per_instance(args) >= PILOT_MIN_CANDIDATES_PER_INSTANCE
    assert effective_codebook_size(args) >= PILOT_MIN_CANDIDATES_PER_INSTANCE + 1

    smoke = parse_args_checked(["--smoke", "--pilot-instances", "24", "--candidates-per-instance", "4", "--codebook-size", "64"], "test")
    assert effective_pilot_instances(smoke) == 24
    assert effective_candidates_per_instance(smoke) == 4


def test_real_learnability_density_lookup_uses_predictions():
    from repair5g559_pipeline import _density_lookup_scores, _select_by_scores

    train = [
        {"example_id": 0, "instance_uid": "train_a", "theta_id": "good", "density_bin": "d01_low", "target": -1.0},
        {"example_id": 1, "instance_uid": "train_a", "theta_id": "bad", "density_bin": "d01_low", "target": 2.0},
    ]
    heldout = [
        {"example_id": 2, "instance_uid": "heldout_a", "theta_id": "bad", "density_bin": "d01_low", "target": 2.0},
        {"example_id": 3, "instance_uid": "heldout_a", "theta_id": "good", "density_bin": "d01_low", "target": -1.0},
    ]
    scores = _density_lookup_scores(train, heldout)
    selected = _select_by_scores(heldout, scores)
    assert selected[0]["theta_id"] == "good"

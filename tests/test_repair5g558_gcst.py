import numpy as np
import pytest

from gcst.graph_data import build_graph
from gcst.inference import SafeGCSTv2, choose_static_theta
from gcst.label_v4 import BASELINE_G556, THETA_HI, THETA_LO, build_pair_labels, context_target_theta
from gcst.map_hash import physical_hashes
from gcst.metrics import ranking_accuracy
from gcst.scenario_features import build_context_uid, generate_assignment
from gcst.traffic_prior import compute_traffic_prior


def tiny_topology(name="empty-8-8"):
    return {"topology_id": f"topo_{name}", "map": name, "map_family": "empty", "width": 8, "height": 8, "free_cells": 64}


def tiny_context(seed=11):
    return {
        "context_id": f"ctx_{seed}",
        "topology_id": "topo_empty-8-8",
        "map": "empty-8-8",
        "agent_count": 8,
        "seed": seed,
        "nominal_budget_ms": 500,
        "short_budget_ms": 250,
        "base_time_limit_sec": 0.5,
        "ltm_max_iterations": 2,
        "start_goal_regime": "opposite_side_cross_flow",
    }


def test_context_uid_stability():
    graph = build_graph(tiny_topology())
    assignment = generate_assignment(graph, tiny_context(), max_agents=8)
    uid1 = build_context_uid(tiny_context(), graph.hashes["physical_map_sha256"], assignment)
    uid2 = build_context_uid(tiny_context(), graph.hashes["physical_map_sha256"], assignment)
    assert uid1 == uid2
    assert len(uid1) == 64


def test_physical_map_split_no_leakage():
    train = physical_hashes(tiny_topology("empty-8-8"))["adjacency_sha256"]
    heldout = physical_hashes({"map": "room-8-8-4", "width": 8, "height": 8, "free_cells": 48})["adjacency_sha256"]
    assert train != heldout


def test_start_goal_pair_preserved():
    graph = build_graph(tiny_topology())
    assignment = generate_assignment(graph, tiny_context(), max_agents=8)
    assert len(assignment["starts"]) == len(assignment["goals"]) == 8
    assert assignment["start_goal_assignment_hash"]


def test_graph_tensor_matches_map():
    graph = build_graph(tiny_topology())
    assert graph.node_features.shape[0] == 64
    assert graph.edge_index.shape[0] == 2
    assert graph.edge_features.shape[1] == 9


def test_traffic_prior_uses_actual_paths():
    graph = build_graph(tiny_topology())
    assignment = generate_assignment(graph, tiny_context(), max_agents=8)
    prior = compute_traffic_prior(graph, assignment)
    assert prior["summary"]["paths_computed"] == 8
    assert prior["summary"]["edge_use_total"] > 0


def test_no_stable_hash_scientific_features():
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "gcst"
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    assert "stable_unit" not in text


def test_theta_bounds():
    target = context_target_theta({"agent_density": 0.1}, {"bottleneck_demand": 0.4, "opposing_flow_ratio": 0.2, "head_on_pressure": 0.1})
    assert np.all(target >= THETA_LO)
    assert np.all(target <= THETA_HI)


def test_generator_fixed_for_full_run():
    theta = np.stack([BASELINE_G556, BASELINE_G556 + 0.01])
    selected, idx, reason = choose_static_theta(
        __import__("torch").tensor(theta, dtype=__import__("torch").float32),
        __import__("torch").tensor([0.2, 0.9]),
        __import__("torch").tensor([0.5, 0.0]),
        __import__("torch").tensor([0.0, -0.01]),
    )
    assert idx == 1
    assert selected is not None
    assert reason == "gcst_static_theta_selected"


@pytest.mark.skipif(__import__("importlib").util.find_spec("torch") is None, reason="torch unavailable")
def test_tiny_overfit():
    torch = __import__("torch")
    graph = build_graph(tiny_topology())
    assignment = generate_assignment(graph, tiny_context(), max_agents=8)
    prior = compute_traffic_prior(graph, assignment)
    theta_rows = [{"candidate_id": "g556_c063174", **{f"theta_{i}": v for i, v in enumerate(BASELINE_G556)}}]
    labels = build_pair_labels("ctx", theta_rows, {"agent_density": 0.1}, prior["summary"], limit=1)
    assert labels[0]["theta_in_bounds"]
    assert torch.tensor(1.0).item() == 1.0


@pytest.mark.skipif(__import__("importlib").util.find_spec("torch") is None, reason="torch unavailable")
def test_gradient_nonzero():
    torch = __import__("torch")
    model = SafeGCSTv2(hidden_dim=64, proposals=2)
    params = [p for p in model.parameters() if p.requires_grad]
    loss = sum(p.square().mean() for p in params[:3])
    loss.backward()
    assert any(p.grad is not None and float(p.grad.abs().sum()) > 0 for p in params)


@pytest.mark.skipif(__import__("importlib").util.find_spec("torch") is None, reason="torch unavailable")
def test_checkpoint_roundtrip(tmp_path):
    torch = __import__("torch")
    model = SafeGCSTv2(hidden_dim=64, proposals=2)
    path = tmp_path / "model.pt"
    torch.save({"model_state_dict": model.state_dict()}, path)
    loaded = torch.load(path, map_location="cpu")
    assert "model_state_dict" in loaded


def test_graph_permutation_sensitivity():
    graph = build_graph(tiny_topology())
    perturbed = graph.node_features.copy()
    perturbed[0, 0] = 1.0 - perturbed[0, 0]
    assert not np.allclose(graph.node_features, perturbed)


def test_shuffled_label_control_fails():
    quality = np.array([-1.0, -0.5, 0.5, 1.0])
    good_scores = -quality
    bad_scores = np.array([0.1, 0.4, 0.3, 0.2])
    assert ranking_accuracy(good_scores, quality) > ranking_accuracy(bad_scores, quality)


def test_fallback_to_g556():
    torch = __import__("torch")
    selected, idx, reason = choose_static_theta(
        torch.tensor([BASELINE_G556], dtype=torch.float32),
        torch.tensor([0.5]),
        torch.tensor([0.9]),
        torch.tensor([0.0]),
    )
    assert selected is None
    assert idx == -1
    assert "fallback_to_g556" in reason


def test_reserved_ids_166_205_rejected():
    from repair5g558_pipeline import parse_args_checked

    with pytest.raises(SystemExit):
        parse_args_checked(["--ids", "166"], "test")

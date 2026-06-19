import numpy as np
import pytest

from gcst.graph_data import GraphData, build_graph
from gcst.goal_aware_actor import GoalAwareDualChannelActor, make_graph_batch, pad_od_tokens, scalar_features
from gcst.label_v4 import THETA_HI, THETA_LO
from gcst.scenario_features import generate_assignment
from gcst.schemas_v51 import PRIMARY_BASELINE
from gcst.theta_schema import BASELINE_G556, THETA_NUMERIC_COLUMNS, compare_theta_to_fingerprint, expected_cpp_params, mode_columns
from gcst.traffic_prior import compute_traffic_prior
from audit_repair5g561_replay_truth import audit_rows
from generate_repair5g561_valid_scenario_bank import build_assignment, split_rows
from run_repair5g561_materialization_contract import (
    attach_contract_audit,
    build_contract_vectors,
    build_plan_rows,
    default_contexts,
    stable_uid,
    summarize_contract,
)


def _fingerprint(theta):
    return "|".join(f"{key}={value}" for key, value in expected_cpp_params(theta).items())


def _theta_row(values=None):
    values = BASELINE_G556 if values is None else values
    row = {col: float(value) for col, value in zip(THETA_NUMERIC_COLUMNS, values)}
    row.update(mode_columns("flow_shield"))
    return row


def test_actor_bounds_equal_solver_bounds():
    assert float(THETA_LO[7]) == pytest.approx(0.90)
    assert float(THETA_LO[9]) == pytest.approx(0.50)
    assert float(THETA_LO[13]) == pytest.approx(0.25)
    assert float(THETA_HI[13]) == pytest.approx(1.00)
    assert float(THETA_HI[0]) == pytest.approx(1.50)


def test_fingerprint_check_is_role_independent():
    theta = _theta_row()
    ok, mismatches = compare_theta_to_fingerprint(_fingerprint(theta), theta)
    assert ok
    assert mismatches == []

    plan = [
        {
            "plan_row_id": "p0",
            "map": "empty-8-8",
            "agents": "8",
            "seed": "1",
            "budget_ms": "500",
            "horizon_id": "h0",
            "candidate_id": "actor_theta",
            "g560_instance_uid": "inst",
            "g560_evaluation_uid": "eval",
            "g560_physical_map_sha256": "maphash",
            **theta,
        },
        {
            "plan_row_id": "p1",
            "map": "empty-8-8",
            "agents": "8",
            "seed": "1",
            "budget_ms": "500",
            "horizon_id": "h0",
            "candidate_id": PRIMARY_BASELINE,
            "g560_instance_uid": "inst",
            "g560_evaluation_uid": "eval",
            "g560_physical_map_sha256": "maphash",
        },
    ]
    result = [
        {
            "map": "empty-8-8",
            "agents": "8",
            "seed": "1",
            "budget_ms": "500",
            "horizon_id": "h0",
            "role": "direct_actor_generated_theta",
            "candidate_id": "actor_theta",
            "candidate_recognized": "True",
            "solution_found": "True",
            "sum_of_loss_ratio": "1.0",
            "probe_runtime_ms": "1.0",
            "updateparams_fingerprint": _fingerprint(theta),
        },
        {
            "map": "empty-8-8",
            "agents": "8",
            "seed": "1",
            "budget_ms": "500",
            "horizon_id": "h0",
            "role": PRIMARY_BASELINE,
            "candidate_id": PRIMARY_BASELINE,
            "candidate_recognized": "True",
            "solution_found": "True",
            "sum_of_loss_ratio": "1.0",
            "probe_runtime_ms": "1.0",
            "updateparams_fingerprint": _fingerprint(theta),
        },
    ]
    audits, pairs, summary = audit_rows(plan, result, [{"candidate_id": "actor_theta", **theta}])
    actor = [row for row in audits if row["actor_row"]][0]
    assert actor["fulltheta_fingerprint_match_strict"] is True
    assert actor["materialization_class"] == "valid_exact_materialization"
    assert pairs[0]["fingerprint_match"] is True
    assert summary["exact_materialization_actor_rows"] == 1


@pytest.mark.skipif(__import__("importlib").util.find_spec("torch") is None, reason="torch unavailable")
def test_goal_aware_actor_uses_paired_od_and_traffic():
    import torch

    torch.manual_seed(561)
    graph = build_graph({"map": "empty-8-8", "map_family": "empty", "width": 8, "height": 8, "free_cells": 64})
    context = {"agent_count": 12, "agents": 12, "seed": 7, "nominal_budget_ms": 500, "base_time_limit_sec": 0.5, "ltm_max_iterations": 3, "start_goal_regime": "opposite_side_cross_flow"}
    assignment = generate_assignment(graph, context, max_agents=None)
    traffic = compute_traffic_prior(graph, assignment)
    graph_with_traffic = GraphData(
        topology_id=graph.topology_id,
        map_name=graph.map_name,
        width=graph.width,
        height=graph.height,
        cells=graph.cells,
        node_features=graph.node_features,
        edge_index=graph.edge_index,
        edge_features=traffic["edge_features"],
        hashes=graph.hashes,
        component_count=graph.component_count,
        physical_free_cell_count=graph.physical_free_cell_count,
    )
    actor = GoalAwareDualChannelActor(hidden_dim=32).module().eval()
    scalars = torch.tensor(np.stack([scalar_features({**context, **traffic["summary"], "agent_density": 12 / 64})]), dtype=torch.float32)
    od, mask = pad_od_tokens([assignment])
    with torch.no_grad():
        theta_full = actor(make_graph_batch([graph_with_traffic]), od, mask, scalars)

    shuffled = dict(assignment)
    shuffled["od_tokens"] = assignment["od_tokens"].copy()
    shuffled["od_tokens"][:, 2:4] = shuffled["od_tokens"][::-1, 2:4]
    od_changed, mask_changed = pad_od_tokens([shuffled])
    with torch.no_grad():
        theta_od_changed = actor(make_graph_batch([graph_with_traffic]), od_changed, mask_changed, scalars)
        theta_traffic_zeroed = actor(make_graph_batch([graph]), od, mask, scalars)

    assert not torch.allclose(theta_full, theta_od_changed, atol=1e-7)
    assert not torch.allclose(theta_full, theta_traffic_zeroed, atol=1e-7)


def test_g561_generated_assignment_is_component_aware_without_reuse():
    grid = [
        "................",
        "................",
        "....@@@@........",
        "....@@@@........",
        "................",
        "................",
    ]
    assignment = build_assignment(grid, width=16, height=6, agent_count=12, regime_name="opposite_side_cross_flow", seed=561)
    assert len(assignment["starts"]) == 12
    assert len(assignment["goals"]) == 12
    assert assignment["unique_start_count"] == 12
    assert assignment["unique_goal_count"] == 12
    assert len(assignment["assignment_sha256"]) == 64
    assert min(assignment["distances"]) >= 0


def test_g561_split_manifest_has_no_physical_hash_overlap():
    manifest = [
        {"physical_map_sha256": "hash-a", "map": "a0", "map_family": "empty"},
        {"physical_map_sha256": "hash-a", "map": "a1", "map_family": "empty"},
        {"physical_map_sha256": "hash-b", "map": "b0", "map_family": "room"},
        {"physical_map_sha256": "hash-c", "map": "c0", "map_family": "maze"},
    ]
    rows = split_rows(manifest)
    assert len(rows) == 3
    by_hash = {row["physical_map_sha256"]: row["split"] for row in rows}
    assert set(by_hash) == {"hash-a", "hash-b", "hash-c"}


def test_g561_contract_vectors_cover_required_families_without_actor_points():
    rows = build_contract_vectors(include_actor=False)
    families = {row["vector_family"] for row in rows}
    modes = {row["changed_field"] for row in rows if row["vector_family"] == "goal_mode"}
    assert len(rows) >= 64
    assert {
        "g556_anchor",
        "small_residual",
        "field_lower_bound",
        "field_upper_bound",
        "mixed_field_group_residual",
        "goal_mode",
        "random_valid_interior",
    }.issubset(families)
    assert {"flow_shield", "agent_progress", "none"}.issubset(modes)


def test_g561_contract_summary_requires_exact_materialization():
    vectors = build_contract_vectors(include_actor=False, vector_limit=3)
    plan, _registry = build_plan_rows(vectors, default_contexts(context_limit=1))
    for row in plan:
        row["g561_scenario_sha256"] = "scenario-hash"
        row["g561_identity_digest"] = stable_uid(
            "g561_contract_identity",
            row["plan_row_id"],
            row["g561_instance_uid"],
            row["g561_scenario_sha256"],
            row["candidate_id"],
            row["generated_theta_uid"],
        )
    results = [
        {
            "map": row["map"],
            "agents": row["agents"],
            "seed": row["seed"],
            "budget_ms": row["budget_ms"],
            "materialized_method": row["materialized_method"],
            "candidate_id": row["candidate_id"],
            "candidate_recognized": "True",
            "real_solver_execution": "True",
            "probe_materialized": "True",
            "updateparams_fingerprint": row["expected_updateparams_fingerprint"],
        }
        for row in plan
    ]
    audited = attach_contract_audit(results, plan)
    summary = summarize_contract(audited, plan)
    assert summary["candidate_recognized_rate"] == 1.0
    assert summary["fingerprint_exact_match_rate"] == 1.0
    assert summary["force_additive_false_rate"] == 1.0
    assert summary["dual_channel_enabled_rate"] == 1.0
    assert summary["identity_retention_rate"] == 1.0
    assert summary["gates"]["minimum_64_vectors_met"] is False

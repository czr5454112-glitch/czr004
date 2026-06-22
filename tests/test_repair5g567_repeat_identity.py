from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5g567_strict_pipeline as g567  # noqa: E402
from gcst.graph_data import GraphData  # noqa: E402


def _graph() -> GraphData:
    return GraphData(
        topology_id="tiny",
        map_name="tiny",
        width=2,
        height=1,
        cells=[(0, 0), (1, 0)],
        node_features=np.zeros((2, 9), dtype=np.float32),
        edge_index=np.zeros((2, 0), dtype=np.int64),
        edge_features=np.zeros((0, 9), dtype=np.float32),
        hashes={},
        component_count=1,
        physical_free_cell_count=2,
    )


def _context() -> g567.G567Context:
    assignment = {"starts": [(0, 0)], "goals": [(1, 0)]}
    graph = _graph()
    return g567.G567Context(
        dataset_row_id="ctx-1",
        evaluation_uid="eval-1",
        instance_uid="inst-1",
        split="CALIBRATION",
        map="tiny",
        map_family="empty",
        agents=8,
        seed=567,
        budget_ms=1000,
        base_time_limit_sec=1.0,
        ltm_max_iterations=3,
        horizon_id="budget1000_ltm3",
        scenario_path=Path("unused.scen"),
        replay_scenario_path=Path("unused.scen"),
        scenario_sha256="scenario-sha",
        physical_map_sha256="map-sha",
        assignment_sha256="assignment-sha",
        graph_with_traffic=graph,
        assignment=assignment,
        feature_row={"agent_count": 8, "budget_ms": 1000},
        budget_role="primary_exact",
        process_hard_timeout_sec=g567.process_hard_timeout_for_internal_budget(1.0),
    )


def _theta_row(ctx: g567.G567Context) -> dict[str, object]:
    row: dict[str, object] = {
        "context_id": ctx.dataset_row_id,
        "method": "unit_actor",
        "variant_id": "A5",
        "seed": "567",
        "model_path": "unit.pt",
    }
    row.update({col: g567.BASELINE_G556[idx] for idx, col in enumerate(g567.THETA_NUMERIC_COLUMNS)})
    return row


def test_repeat_plan_preserves_horizon_and_adds_replicate_identity() -> None:
    ctx = _context()
    plan, _registry = g567.build_plan_and_registry([ctx], [_theta_row(ctx)], "repeatability_single_worker", repeat_count=3)
    actor_rows = [row for row in plan if str(row.get("role", "")).startswith("generated_theta::")]
    assert len(actor_rows) == 3
    assert {row["horizon_id"] for row in actor_rows} == {ctx.horizon_id}
    assert {row["scientific_horizon_id"] for row in actor_rows} == {ctx.horizon_id}
    assert [row["replicate_id"] for row in actor_rows] == [0, 1, 2]
    assert len({row["plan_row_id"] for row in actor_rows}) == 3
    assert len({row["replicate_group_id"] for row in actor_rows}) == 1
    assert {row["solver_execution_id"] for row in actor_rows} == {
        "budget1000_ltm3|rep00",
        "budget1000_ltm3|rep01",
        "budget1000_ltm3|rep02",
    }


def test_three_tier_pairs_keep_replicates_as_rows_in_one_scientific_group() -> None:
    rows = []
    actor_method = "actor-A5"
    for rep in range(3):
        common = {
            "replay_phase": "repeatability_single_worker",
            "map": "tiny",
            "map_family": "empty",
            "agents": "8",
            "seed": "567",
            "budget_ms": "1000",
            "horizon_id": "budget1000_ltm3",
            "g567_dataset_row_id": "ctx-1",
            "g567_evaluation_uid": "eval-1",
            "replicate_id": str(rep),
            "solution_found": "true",
            "sum_of_loss_ratio": "1.0",
        }
        for method in [
            g567.ADDITIVE_SOLVER_ALIAS,
            g567.STATIC_FLOW_SOLVER_ALIAS,
            g567.G556_SOLVER_ALIAS,
            actor_method,
        ]:
            rows.append(
                {
                    **common,
                    "materialized_method": method,
                    "candidate_id": method,
                    "role": "generated_theta::actor" if method == actor_method else method,
                    "replicate_group_id": "rg-actor" if method == actor_method else f"rg-{method}",
                    "plan_row_id": f"plan-{method}-{rep}",
                }
            )
    pairs = g567.build_three_tier_pairs(rows, "repeatability_single_worker")
    assert len(pairs) == 3
    assert {row["horizon_id"] for row in pairs} == {"budget1000_ltm3"}
    assert {row["replicate_group_id"] for row in pairs} == {"rg-actor"}
    assert {row["replicate_id"] for row in pairs} == {"0", "1", "2"}

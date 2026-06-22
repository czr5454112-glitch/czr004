from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5g567_strict_pipeline as g567  # noqa: E402


def _plan_row() -> dict[str, object]:
    theta = g567.TIER_B_STATIC_FLOW.theta or {}
    return {
        "plan_row_id": "g567_direct_exact_test_00000001",
        "replay_phase": "unit_direct_exact",
        "context_id": "ctx-direct",
        "g567_dataset_row_id": "ctx-direct",
        "g567_instance_uid": "inst",
        "g567_evaluation_uid": "eval",
        "g567_identity_digest": "identity",
        "g567_scenario_sha256": "",
        "g567_physical_map_sha256": "",
        "g567_assignment_sha256": "",
        "split": "LABEL_TRAIN",
        "map": "random-32-32-20",
        "map_family": "random",
        "agents": 32,
        "seed": 1,
        "budget_ms": 30000,
        "horizon_id": "h30s",
        "scientific_horizon_id": "h30s",
        "role": "tierB_static_flow_shield",
        "candidate_id": g567.STATIC_FLOW_SOLVER_ALIAS,
        "materialized_method": g567.STATIC_FLOW_SOLVER_ALIAS,
        "sampling_policy": "static_flow",
        "expected_updateparams_fingerprint": g567.TIER_B_STATIC_FLOW.fingerprint,
        "replicate_id": 0,
        "replicate_group_id": "rep",
        "solver_internal_time_limit_sec": 30.0,
        "process_hard_timeout_sec": 60.0,
        "budget_role": "uniform_30s_all_agent_tiers_primary_exact",
        **theta,
    }


def test_direct_exact_enrichment_is_not_counterfactual_probe() -> None:
    plan = _plan_row()
    raw = {
        "method": "direct_alias",
        "success": True,
        "feasible": True,
        "sum_of_loss": 123,
        "lower_bound": 100,
        "sum_of_loss_ratio": 1.23,
        "runtime_ms": 250.0,
        "expanded_nodes": 42,
        "high_level_expansions": 7,
        "low_level_pibt_calls": 11,
        "repair5g_candidate_id": g567.STATIC_FLOW_SOLVER_ALIAS,
        "repair5g_update_mode": "dual_channel_static",
        "updateparams_hash": "hash",
        "updateparams_fingerprint": g567.TIER_B_STATIC_FLOW.fingerprint,
        "instance_load_ms": 1.0,
        "outer_solve_ms": 250.0,
        "counterfactual_probe_ms": 0.0,
    }
    rows = g567.enrich_direct_exact_rows(
        [raw],
        plan,
        row_prefix="unit",
        execution_mode="unit_direct_exact_solver_row",
        command_row={"process_hard_timeout_exceeded": False, "returncode_classification": "solver_no_solution_or_timeout"},
    )
    row = rows[0]
    assert row["exact_execution_mode"] == g567.DIRECT_EXACT_EXECUTION_MODE
    assert row["counts_as_counterfactual_probe_row"] is False
    assert row["counterfactual_probe_callback_enabled"] is False
    assert row["probe_materialized"] is False
    assert row["candidate_recognized"] is True
    assert row["solution_found"] is True
    assert row["updateparams_fingerprint_source"] == "solver_output"
    assert row["counterfactual_probe_ms"] == 0.0


def test_direct_exact_timeout_placeholder_is_infrastructure_only() -> None:
    rows = g567.enrich_direct_exact_rows(
        [],
        _plan_row(),
        row_prefix="unit",
        execution_mode="unit_direct_exact_solver_row",
        command_row={
            "process_hard_timeout_exceeded": True,
            "returncode_classification": "process_hard_timeout",
            "process_timeout_reason": "process_hard_timeout_sec_exceeded",
        },
    )
    row = rows[0]
    assert row["infrastructure_timeout"] is True
    assert row["scientific_result_valid"] is False
    assert row["excluded_from_scientific_labels"] is True
    assert row["solution_found"] == ""
    assert row["updateparams_fingerprint"] == ""
    assert row["updateparams_fingerprint_source"] == "missing_process_hard_timeout"

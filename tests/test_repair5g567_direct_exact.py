from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import repair5g5_common as g5  # noqa: E402
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


def test_direct_exact_registers_generated_gate3b_map_paths(tmp_path, monkeypatch) -> None:
    map_name = "maze_128_128_2"
    bank_maps = tmp_path / "scenario_bank" / "maps"
    bank_maps.mkdir(parents=True)
    map_path = bank_maps / f"{map_name}.map"
    map_path.write_text("type octile\nheight 2\nwidth 2\nmap\n..\n..\n", encoding="utf-8")
    scenario_dir = tmp_path / "replay_scenarios"
    result_csv = tmp_path / "results.csv"
    raw_csv = tmp_path / "raw.csv"
    log_dir = tmp_path / "logs"

    plan = _plan_row()
    plan.update(
        {
            "plan_row_id": "generated-map-plan",
            "map": map_name,
            "raw_map_path": str(map_path),
            "seed": 4567001,
        }
    )
    monkeypatch.setattr(g567, "TMP_ROOT", tmp_path / "scenario_bank")
    monkeypatch.delitem(g567.MAP_PATHS, map_name, raising=False)
    monkeypatch.delitem(g5.MAP_PATHS, map_name, raising=False)

    def fake_prepare_scenarios(**kwargs):
        target = g567.scenario_path(Path(kwargs["scenario_dir"]), map_name, int(plan["seed"]))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("version 1\n0 generated.map 2 2 0 0 1 1 2\n", encoding="utf-8")

    def fake_run_one_solver_task(**kwargs):
        assert kwargs["map_name"] == map_name
        assert map_name in g5.MAP_PATHS
        assert g567.resolve(g5.MAP_PATHS[map_name]).resolve() == map_path.resolve()
        return (
            [
                {
                    "success": True,
                    "feasible": True,
                    "sum_of_loss": 2,
                    "lower_bound": 2,
                    "sum_of_loss_ratio": 1.0,
                    "runtime_ms": 1.0,
                    "repair5g_candidate_id": g567.STATIC_FLOW_SOLVER_ALIAS,
                    "repair5g_update_mode": "dual_channel_static",
                    "updateparams_fingerprint": g567.TIER_B_STATIC_FLOW.fingerprint,
                }
            ],
            [],
            {"process_hard_timeout_exceeded": False, "returncode_classification": "solver_success"},
        )

    monkeypatch.setattr(g567.g549, "prepare_scenarios", fake_prepare_scenarios)
    monkeypatch.setattr(g567, "run_one_solver_task", fake_run_one_solver_task)

    try:
        rows = g567.run_direct_exact_plan(
            [plan],
            binary=tmp_path / "phase1a_batch",
            overwrite=True,
            max_workers=1,
            registry_path=tmp_path / "registry.csv",
            result_csv=result_csv,
            raw_csv=raw_csv,
            log_dir=log_dir,
            scenario_dir=scenario_dir,
            scenario_metadata=tmp_path / "scenario_metadata.json",
            manifest_prefix="unit",
            row_prefix="unit",
            execution_mode="unit_direct_exact_solver_row",
        )
    finally:
        g567.MAP_PATHS.pop(map_name, None)
        g5.MAP_PATHS.pop(map_name, None)

    assert rows
    assert rows[0]["map"] == map_name
    assert rows[0]["candidate_recognized"] is True


def test_direct_exact_row_weights_match_large_agent_tiers() -> None:
    assert g567.direct_exact_row_weight({"agents": 64}) == 1
    assert g567.direct_exact_row_weight({"agents": 256}) == 2
    assert g567.direct_exact_row_weight({"agents": 1000}) == 4
    assert g567.direct_exact_row_weight({"agents": 2500}) == 4
    assert g567.direct_exact_row_weight({"agents": 3000}) == 8
    assert g567.direct_exact_row_weight({"agents": 128, "map": "g567-tunnel-64x32-a-v1"}) == 4
    assert g567.direct_exact_row_weight({"agents": 256, "map": "g567-tunnel-64x32-a-v1"}) == 8
    assert g567.direct_exact_weight_reason({"agents": 256, "map": "g567-tunnel-64x32-a-v1"}) == "extreme_tail_256plus_serial_weight"


def test_direct_exact_shards_recover_without_rerunning_completed_rows(tmp_path, monkeypatch) -> None:
    scenario_dir = tmp_path / "replay_scenarios"
    result_csv = tmp_path / "results.csv"
    raw_csv = tmp_path / "raw.csv"
    log_dir = tmp_path / "logs"
    plans = []
    for idx in range(2):
        row = _plan_row()
        row.update(
            {
                "plan_row_id": f"shard-plan-{idx}",
                "context_id": f"ctx-{idx}",
                "g567_dataset_row_id": f"ctx-{idx}",
                "g567_evaluation_uid": f"eval-{idx}",
                "g567_identity_digest": f"identity-{idx}",
                "seed": idx + 1,
            }
        )
        plans.append(row)

    def fake_prepare_scenarios(**kwargs):
        for seed in kwargs["instance_ids"]:
            target = g567.scenario_path(Path(kwargs["scenario_dir"]), "random-32-32-20", int(seed))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("version 1\n0 random.map 32 32 0 0 1 1 2\n", encoding="utf-8")

    calls: list[str] = []

    def fake_run_one_solver_task(**kwargs):
        calls.append(str(kwargs["seed"]))
        return (
            [
                {
                    "success": True,
                    "feasible": True,
                    "sum_of_loss": 2,
                    "lower_bound": 2,
                    "sum_of_loss_ratio": 1.0,
                    "runtime_ms": 1.0,
                    "repair5g_candidate_id": g567.STATIC_FLOW_SOLVER_ALIAS,
                    "repair5g_update_mode": "dual_channel_static",
                    "updateparams_fingerprint": g567.TIER_B_STATIC_FLOW.fingerprint,
                }
            ],
            [],
            {"process_hard_timeout_exceeded": False, "returncode_classification": "solver_success"},
        )

    monkeypatch.setenv("G567_DIRECT_EXACT_SHARD_SIZE", "1")
    monkeypatch.setattr(g567.g549, "prepare_scenarios", fake_prepare_scenarios)
    monkeypatch.setattr(g567, "run_one_solver_task", fake_run_one_solver_task)

    rows = g567.run_direct_exact_plan(
        plans,
        binary=tmp_path / "phase1a_batch",
        overwrite=True,
        max_workers=1,
        registry_path=tmp_path / "registry.csv",
        result_csv=result_csv,
        raw_csv=raw_csv,
        log_dir=log_dir,
        scenario_dir=scenario_dir,
        scenario_metadata=tmp_path / "scenario_metadata.json",
        manifest_prefix="unit",
        row_prefix="unit",
        execution_mode="unit_direct_exact_solver_row",
    )

    assert len(rows) == 2
    assert calls == ["1", "2"]
    assert len(list((log_dir / "direct_exact_shards").glob("shard_*/shard.done.json"))) == 2
    result_csv.unlink()
    raw_csv.unlink()
    calls.clear()

    def fail_if_rerun(**kwargs):
        raise AssertionError("completed shard rows should have been recovered, not rerun")

    monkeypatch.setattr(g567, "run_one_solver_task", fail_if_rerun)
    recovered = g567.run_direct_exact_plan(
        plans,
        binary=tmp_path / "phase1a_batch",
        overwrite=False,
        max_workers=1,
        registry_path=tmp_path / "registry.csv",
        result_csv=result_csv,
        raw_csv=raw_csv,
        log_dir=log_dir,
        scenario_dir=scenario_dir,
        scenario_metadata=tmp_path / "scenario_metadata.json",
        manifest_prefix="unit",
        row_prefix="unit",
        execution_mode="unit_direct_exact_solver_row",
    )

    assert len(recovered) == 2
    assert calls == []
    assert result_csv.exists()

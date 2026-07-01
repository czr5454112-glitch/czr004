from __future__ import annotations

import random
import sys
import pickle
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5g567_gate3b_bounded_pilot as gate3b  # noqa: E402


def _fake_row(tier: int, idx: int, source: str) -> dict[str, object]:
    official = source == "canonical_public_benchmark_map" and idx % 2 == 0
    return {
        "g567_instance_uid": f"{source}-{tier}-{idx}",
        "agent_count": tier,
        "width": 128,
        "height": 128,
        "free_cells": max(4096, tier + 64),
        "map_family": "public" if source == "canonical_public_benchmark_map" else "synthetic",
        "map_source_type": source,
        "scenario_source_type": "movingai_official_random" if official else "czr004_synthetic_derived_scenario",
        "official_scenario": official,
        "physical_map_sha256": f"{source}-hash-{tier}-{idx}",
    }


def _fake_parent_rows(parent: str, source: str, family: str, repeats: int) -> list[dict[str, object]]:
    official = source == "canonical_public_benchmark_map"
    rows = []
    for tier in gate3b.REQUIRED_AGENT_TIERS:
        for repeat in range(repeats):
            rows.append(
                {
                    "g567_instance_uid": f"{parent}-{tier}-{repeat}",
                    "agent_count": tier,
                    "width": 128,
                    "height": 128,
                    "free_cells": max(4096, tier + 64),
                    "map_family": family,
                    "map_source_type": source,
                    "scenario_source_type": "movingai_official_random" if official else "czr004_synthetic_derived_scenario",
                    "official_scenario": official,
                    "physical_map_sha256": parent,
                }
            )
    return rows


def test_gate3b_split_selection_preserves_parent_hash_and_public_mix() -> None:
    rows = []
    for tier in gate3b.REQUIRED_AGENT_TIERS:
        for idx in range(4):
            rows.append(_fake_row(tier, idx, "canonical_public_benchmark_map"))
            rows.append(_fake_row(tier, idx, "synthetic_stress_map"))

    label_rows, cal_rows, dev_rows, meta = gate3b.select_gate3b_rows(
        rows,
        label_contexts=len(gate3b.REQUIRED_AGENT_TIERS) * 2,
        calibration_contexts=len(gate3b.REQUIRED_AGENT_TIERS),
        development_contexts=len(gate3b.REQUIRED_AGENT_TIERS),
        label_public_fraction_min=0.50,
        calibration_public_fraction_min=0.70,
        development_public_fraction_min=0.70,
        label_official_scenario_fraction_min=0.0,
        calibration_official_scenario_fraction_min=0.0,
        development_official_scenario_fraction_min=0.0,
        label_min_parent_maps=1,
        calibration_min_parent_maps=1,
        development_min_parent_maps=1,
        label_min_map_families=1,
        calibration_min_map_families=1,
        development_min_map_families=1,
        max_train_free_cells=24000,
        max_train_area=32000,
    )

    assert len(label_rows) == len(gate3b.REQUIRED_AGENT_TIERS) * 2
    assert len(cal_rows) == len(gate3b.REQUIRED_AGENT_TIERS)
    assert len(dev_rows) == len(gate3b.REQUIRED_AGENT_TIERS)
    assert meta["parent_map_split_leakage_count"] == 0
    assert meta["label_train_public_fraction"] >= 0.50
    assert meta["development_public_fraction"] >= 0.70
    assert set(gate3b.REQUIRED_AGENT_TIERS).issubset(set(meta["selected_agent_tiers"]))


def test_gate3b_split_selection_does_not_starve_label_public_capacity(monkeypatch) -> None:
    monkeypatch.setattr(gate3b, "REQUIRED_AGENT_TIERS", (8, 12, 16, 24))
    rows = []
    for parent_idx in range(14):
        rows.extend(
            _fake_parent_rows(
                f"public-parent-{parent_idx}",
                "canonical_public_benchmark_map",
                f"public-family-{parent_idx % 5}",
                repeats=8,
            )
        )
    for parent_idx in range(36):
        rows.extend(
            _fake_parent_rows(
                f"synthetic-parent-{parent_idx}",
                "synthetic_stress_map",
                f"synthetic-family-{parent_idx % 10}",
                repeats=2,
            )
        )

    label_rows, cal_rows, dev_rows, meta = gate3b.select_gate3b_rows(
        rows,
        label_contexts=160,
        calibration_contexts=80,
        development_contexts=80,
        label_public_fraction_min=0.50,
        calibration_public_fraction_min=0.70,
        development_public_fraction_min=0.70,
        label_official_scenario_fraction_min=0.20,
        calibration_official_scenario_fraction_min=0.30,
        development_official_scenario_fraction_min=0.30,
        label_min_parent_maps=8,
        calibration_min_parent_maps=4,
        development_min_parent_maps=4,
        label_min_map_families=5,
        calibration_min_map_families=4,
        development_min_map_families=4,
        max_train_free_cells=24000,
        max_train_area=32000,
        parent_concentration_cap_fraction=0.15,
        family_concentration_cap_fraction=0.40,
        milp_time_limit_sec=30.0,
    )

    assert len(label_rows) == 160
    assert len(cal_rows) == 80
    assert len(dev_rows) == 80
    assert meta["parent_map_split_leakage_count"] == 0
    assert meta["label_train_public_fraction"] >= 0.50
    assert meta["calibration_public_fraction"] >= 0.70
    assert meta["development_public_fraction"] >= 0.70


def test_gate3b_prepare_rows_rewrites_reused_large_agent_budget(tmp_path, monkeypatch) -> None:
    scen = tmp_path / "unit.scen"
    scen.write_text("version 1\n", encoding="utf-8")
    monkeypatch.setattr(gate3b.g567, "REPLAY_SCENARIO_DIR", tmp_path / "replay")
    stale_row = {
        "g567_instance_uid": "old",
        "g567_evaluation_uid": "old-eval",
        "map": "den312d",
        "map_family": "city",
        "solver_seed": 4567,
        "scenario_sha256": "scenario",
        "physical_map_sha256": "physical",
        "assignment_sha256": "assignment",
        "raw_scenario_path": str(scen),
        "scenario_source_type": "czr004_synthetic_derived_scenario",
        "nominal_budget_ms": 30000,
        "base_time_limit_sec": 30.0,
        "solver_internal_time_limit_sec": 30.0,
        "process_hard_timeout_sec": 60.0,
        "budget_role": "uniform_30s_all_agent_tiers_primary_exact",
    }
    rows = gate3b.prepare_rows(
        [
            {**stale_row, "agent_count": 1500},
            {**stale_row, "agent_count": 3000},
        ],
        split="LABEL_TRAIN",
        prefix="unit",
    )

    row_1500, row_3000 = rows
    assert row_1500["nominal_budget_ms"] == 40000
    assert row_1500["solver_internal_time_limit_sec"] == 40.0
    assert row_1500["process_hard_timeout_sec"] == 80.0
    assert row_1500["budget_role"] == "large_agent_40s_primary_exact"
    assert row_1500["horizon_id"] == "budget40000_ltm12"
    assert row_1500["g567_instance_uid"] != "old"
    assert row_3000["nominal_budget_ms"] == 60000
    assert row_3000["solver_internal_time_limit_sec"] == 60.0
    assert row_3000["process_hard_timeout_sec"] == 120.0
    assert row_3000["budget_role"] == "agent3000_60s_primary_exact"
    assert row_3000["horizon_id"] == "budget60000_ltm12"
    assert row_3000["g567_instance_uid"] != "old"


def test_gate3b_joint_allocator_is_deterministic_under_input_shuffle(monkeypatch) -> None:
    monkeypatch.setattr(gate3b, "REQUIRED_AGENT_TIERS", (8, 12, 16, 24))
    rows = []
    for parent_idx in range(14):
        rows.extend(
            _fake_parent_rows(
                f"public-parent-{parent_idx}",
                "canonical_public_benchmark_map",
                f"public-family-{parent_idx % 5}",
                repeats=4,
            )
        )
    for parent_idx in range(24):
        rows.extend(
            _fake_parent_rows(
                f"synthetic-parent-{parent_idx}",
                "synthetic_stress_map",
                f"synthetic-family-{parent_idx % 8}",
                repeats=2,
            )
        )

    shuffled = list(rows)
    random.Random(567).shuffle(shuffled)
    kwargs = dict(
        label_contexts=120,
        calibration_contexts=60,
        development_contexts=60,
        label_public_fraction_min=0.50,
        calibration_public_fraction_min=0.70,
        development_public_fraction_min=0.70,
        label_official_scenario_fraction_min=0.20,
        calibration_official_scenario_fraction_min=0.30,
        development_official_scenario_fraction_min=0.30,
        label_min_parent_maps=8,
        calibration_min_parent_maps=4,
        development_min_parent_maps=4,
        label_min_map_families=5,
        calibration_min_map_families=4,
        development_min_map_families=4,
        max_train_free_cells=24000,
        max_train_area=32000,
        parent_concentration_cap_fraction=0.20,
        family_concentration_cap_fraction=0.45,
        milp_time_limit_sec=30.0,
    )
    selected_a = gate3b.select_gate3b_rows(rows, **kwargs)
    selected_b = gate3b.select_gate3b_rows(shuffled, **kwargs)

    assert [[gate3b.row_uid(row) for row in split] for split in selected_a[:3]] == [
        [gate3b.row_uid(row) for row in split] for split in selected_b[:3]
    ]


def test_gate3b_joint_allocator_infeasible_pool_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(gate3b, "REQUIRED_AGENT_TIERS", (8, 12, 16, 24))
    rows = []
    for parent_idx in range(2):
        rows.extend(
            _fake_parent_rows(
                f"public-parent-{parent_idx}",
                "canonical_public_benchmark_map",
                f"public-family-{parent_idx}",
                repeats=1,
            )
        )
    for parent_idx in range(8):
        rows.extend(
            _fake_parent_rows(
                f"synthetic-parent-{parent_idx}",
                "synthetic_stress_map",
                f"synthetic-family-{parent_idx}",
                repeats=1,
            )
        )

    with pytest.raises(RuntimeError, match="gate3b_candidate_pool_joint_split_infeasible"):
        gate3b.select_gate3b_rows(
            rows,
            label_contexts=80,
            calibration_contexts=40,
            development_contexts=40,
            label_public_fraction_min=0.50,
            calibration_public_fraction_min=0.70,
            development_public_fraction_min=0.70,
            label_official_scenario_fraction_min=0.20,
            calibration_official_scenario_fraction_min=0.30,
            development_official_scenario_fraction_min=0.30,
            label_min_parent_maps=8,
            calibration_min_parent_maps=4,
            development_min_parent_maps=4,
            label_min_map_families=5,
            calibration_min_map_families=4,
            development_min_map_families=4,
            max_train_free_cells=24000,
            max_train_area=32000,
            parent_concentration_cap_fraction=0.20,
            family_concentration_cap_fraction=0.50,
            milp_time_limit_sec=30.0,
        )


def test_gate3b_pass_conditions_require_bounded_rows_and_no_blind() -> None:
    summary = {
        "source_state": {"decision": "g567_source_state_clean"},
        "public_benchmark_ingestion": {"ready": True},
        "label_train_contexts": 2000,
        "calibration_contexts": 500,
        "development_contexts": 500,
        "context_materialization": {
            "label_train": {"traffic_prior_versions": {"traffic_prior_v1_bfs": 2000}},
            "calibration": {"traffic_prior_versions": {"traffic_prior_v1_bfs": 500}},
            "development": {"traffic_prior_versions": {"traffic_prior_v1_bfs": 500}},
        },
        "total_solver_rows": 60000,
        "selected_agent_tiers": list(gate3b.REQUIRED_AGENT_TIERS),
        "label_train_public_fraction": 0.50,
        "calibration_public_fraction": 0.70,
        "development_public_fraction": 0.70,
        "label_train_official_scenario_fraction": 0.20,
        "calibration_official_scenario_fraction": 0.30,
        "development_official_scenario_fraction": 0.30,
        "selected_map_source_types": {"canonical_public_benchmark_map": 1, "synthetic_stress_map": 1},
        "parent_map_split_leakage_count": 0,
        "split_diversity": {
            "LABEL_TRAIN": {"parent_map_count": 32, "map_family_count": 10},
            "CALIBRATION": {"parent_map_count": 12, "map_family_count": 8},
            "DEVELOPMENT": {"parent_map_count": 16, "map_family_count": 8},
        },
        "label_replay": {"decision": "g567_three_tier_replay_materialized", "planned_executed_exact": True, "expected_baseline_rows_exact": True},
        "boundary_repeat": {"decision": "gate3b_no_boundary_repeats_required"},
        "development_replay": {"decision": "g567_three_tier_replay_materialized", "planned_executed_exact": True},
        "process_hard_timeout_rows": 0,
        "process_hard_timeout_rows_excluded_from_scientific_labels": 0,
        "unexcluded_process_hard_timeout_rows": 0,
        "critic_calibration": {"decision": "g567_distributional_critic_calibrated", "calibration_blockers": []},
        "critic_used_for_actor_training": True,
        "actor_training_rows": [{"cuda_bf16_training": True}, {"cuda_bf16_training": True}],
        "gpu_active_hours": 2.1,
        "primary_actor_selection": {"decision": "g567_one_primary_actor_selected"},
        "forbidden_actions": {"full_100k_generation_launched": False, "final_blind_panel_constructed_or_accessed": False},
        "final_blind_panel_constructed_or_accessed": False,
    }

    assert all(gate3b.gate3b_pass_conditions(summary).values())

    summary["total_solver_rows"] = 100001
    assert gate3b.gate3b_pass_conditions(summary)["solver_rows_50000_to_100000"] is False
    summary["total_solver_rows"] = 60000
    summary["final_blind_panel_constructed_or_accessed"] = True
    assert gate3b.gate3b_pass_conditions(summary)["no_final_blind_access"] is False


def test_gate3b_pass_conditions_accept_excluded_infra_timeouts() -> None:
    summary = {
        "source_state": {"decision": "g567_source_state_clean"},
        "public_benchmark_ingestion": {"ready": True},
        "label_train_contexts": 2000,
        "calibration_contexts": 500,
        "development_contexts": 500,
        "context_materialization": {
            "label_train": {"traffic_prior_versions": {"traffic_prior_v1_bfs": 2000}},
            "calibration": {"traffic_prior_versions": {"traffic_prior_v1_bfs": 500}},
            "development": {"traffic_prior_versions": {"traffic_prior_v1_bfs": 500}},
        },
        "total_solver_rows": 60000,
        "selected_agent_tiers": list(gate3b.REQUIRED_AGENT_TIERS),
        "label_train_public_fraction": 0.50,
        "calibration_public_fraction": 0.70,
        "development_public_fraction": 0.70,
        "label_train_official_scenario_fraction": 0.20,
        "calibration_official_scenario_fraction": 0.30,
        "development_official_scenario_fraction": 0.30,
        "selected_map_source_types": {"canonical_public_benchmark_map": 1, "synthetic_stress_map": 1},
        "parent_map_split_leakage_count": 0,
        "split_diversity": {
            "LABEL_TRAIN": {"parent_map_count": 32, "map_family_count": 10},
            "CALIBRATION": {"parent_map_count": 12, "map_family_count": 8},
            "DEVELOPMENT": {"parent_map_count": 16, "map_family_count": 8},
        },
        "label_replay": {
            "decision": "g567_three_tier_replay_materialized_with_infra_timeout_exclusions",
            "planned_executed_exact": True,
            "expected_baseline_rows_exact": True,
        },
        "boundary_repeat": {"decision": "gate3b_no_boundary_repeats_required"},
        "development_replay": {"decision": "g567_three_tier_replay_materialized", "planned_executed_exact": True},
        "process_hard_timeout_rows": 24,
        "process_hard_timeout_rows_excluded_from_scientific_labels": 24,
        "unexcluded_process_hard_timeout_rows": 0,
        "critic_calibration": {"decision": "g567_distributional_critic_calibrated", "calibration_blockers": []},
        "critic_used_for_actor_training": True,
        "actor_training_rows": [{"cuda_bf16_training": True}, {"cuda_bf16_training": True}],
        "gpu_active_hours": 2.1,
        "primary_actor_selection": {"decision": "g567_one_primary_actor_selected"},
        "forbidden_actions": {"full_100k_generation_launched": False, "final_blind_panel_constructed_or_accessed": False},
        "final_blind_panel_constructed_or_accessed": False,
    }

    assert gate3b.gate3b_pass_conditions(summary)["process_hard_timeouts_are_infra_excluded"] is True
    assert all(gate3b.gate3b_pass_conditions(summary).values())

    summary["critic_calibration"] = {
        "decision": "g567_distributional_critic_not_calibrated",
        "calibration_blockers": ["insufficient_tail_events_for_calibration"],
    }
    summary["critic_used_for_actor_training"] = False
    assert gate3b.gate3b_pass_conditions(summary)["critic_calibration_reported_and_safe_for_actor_training"] is True

    summary["critic_used_for_actor_training"] = True
    assert gate3b.gate3b_pass_conditions(summary)["critic_calibration_reported_and_safe_for_actor_training"] is False


def test_replay_summary_materializes_with_excluded_infra_timeout_rows() -> None:
    plan_rows = [
        {"candidate_id": gate3b.g567.ADDITIVE_SOLVER_ALIAS, "g567_dataset_row_id": "ctx-1"},
        {"candidate_id": gate3b.g567.STATIC_FLOW_SOLVER_ALIAS, "g567_dataset_row_id": "ctx-1"},
        {"candidate_id": gate3b.g567.G556_SOLVER_ALIAS, "g567_dataset_row_id": "ctx-1"},
        {"candidate_id": "theta-valid", "g567_dataset_row_id": "ctx-1"},
        {"candidate_id": "theta-nosol", "g567_dataset_row_id": "ctx-1"},
        {"candidate_id": "theta-timeout", "g567_dataset_row_id": "ctx-1"},
    ]
    rows = [
        {"materialized_method": gate3b.g567.ADDITIVE_SOLVER_ALIAS, "process_hard_timeout_exceeded": False},
        {"materialized_method": gate3b.g567.STATIC_FLOW_SOLVER_ALIAS, "process_hard_timeout_exceeded": False},
        {"materialized_method": gate3b.g567.G556_SOLVER_ALIAS, "process_hard_timeout_exceeded": False},
        {
            "materialized_method": "theta-valid",
            "is_actor_row": True,
            "fulltheta_fingerprint_match_strict": True,
            "candidate_recognized_bool": True,
            "scenario_sha256_match": True,
            "identity_retained": True,
            "process_hard_timeout_exceeded": False,
        },
        {
            "materialized_method": "theta-nosol",
            "is_actor_row": True,
            "fulltheta_fingerprint_match_strict": True,
            "candidate_recognized_bool": False,
            "scenario_sha256_match": True,
            "identity_retained": True,
            "process_hard_timeout_exceeded": False,
            "returncode_classification": "returncode2_no_solution_equivalent",
            "direct_exact_success": False,
        },
        {
            "materialized_method": "theta-timeout",
            "is_actor_row": True,
            "process_hard_timeout_exceeded": True,
            "infrastructure_timeout": True,
            "excluded_from_scientific_labels": True,
            "context_key": "ctx-1",
        },
    ]

    summary = gate3b.g567.summarize_pairs([], rows, plan_rows, "unit_phase", margin=0.05)

    assert summary["decision"] == "g567_three_tier_replay_materialized_with_infra_timeout_exclusions"
    assert summary["process_hard_timeout_rows"] == 1
    assert summary["process_hard_timeout_rows_excluded_from_scientific_labels"] == 1
    assert summary["unexcluded_process_hard_timeout_rows"] == 0
    assert summary["valid_actor_candidate_rows"] == 2
    assert summary["no_solution_fingerprint_backed_actor_rows"] == 1
    assert summary["valid_actor_recognized_or_no_solution_rate"] == 1.0


def test_label_train_topup_avoids_calibration_development_parent_hashes() -> None:
    selected_rows = [
        {**_fake_parent_rows("label-parent", "canonical_public_benchmark_map", "warehouse", 1)[0], "split": "LABEL_TRAIN"},
        {**_fake_parent_rows("cal-parent", "canonical_public_benchmark_map", "room", 1)[0], "split": "CALIBRATION"},
        {**_fake_parent_rows("dev-parent", "synthetic_stress_map", "maze", 1)[0], "split": "DEVELOPMENT"},
    ]
    candidate_rows = [
        *_fake_parent_rows("cal-parent", "canonical_public_benchmark_map", "room", 2),
        *_fake_parent_rows("dev-parent", "synthetic_stress_map", "maze", 2),
        *_fake_parent_rows("label-parent", "canonical_public_benchmark_map", "warehouse", 2),
        *_fake_parent_rows("fresh-parent", "canonical_public_benchmark_map", "empty", 2),
    ]

    chosen, meta = gate3b.select_label_train_topup_rows(
        candidate_rows,
        selected_rows,
        needed=1,
        max_train_free_cells=100000,
        max_train_area=100000,
    )

    assert len(chosen) == 1
    assert chosen[0]["physical_map_sha256"] == "label-parent"
    assert meta["reuses_label_parent_count"] == 1


def test_gate3b_materialization_reports_bfs_meta(monkeypatch) -> None:
    def fake_context_from_manifest_row(row: dict[str, object]) -> SimpleNamespace:
        return SimpleNamespace(feature_row={"traffic_prior_version": "traffic_prior_v1_bfs"})

    monkeypatch.setattr(gate3b.g567, "context_from_manifest_row", fake_context_from_manifest_row)
    contexts, meta = gate3b.materialize_contexts(
        [{"g567_dataset_row_id": "unit_00000"}],
        phase="unit",
        workers=1,
        progress_interval_sec=0.01,
    )

    assert len(contexts) == 1
    assert meta["workers"] == 1
    assert meta["routing_backend_contract"] == "bfs"
    assert meta["traffic_prior_versions"] == {"traffic_prior_v1_bfs": 1}


def test_gate3b_materialization_invalidates_stale_budget_cache(tmp_path, monkeypatch) -> None:
    stale_ctx = SimpleNamespace(
        base_time_limit_sec=30.0,
        process_hard_timeout_sec=60.0,
        budget_ms=30000,
        budget_role="uniform_30s_all_agent_tiers_primary_exact",
        feature_row={"traffic_prior_version": "traffic_prior_v1_bfs"},
    )
    cache_path = tmp_path / "contexts.pkl"
    with cache_path.open("wb") as handle:
        pickle.dump({"row_ids": ["ctx-3000"], "contexts": [stale_ctx]}, handle)

    def fake_materialize(payload):
        index, _row = payload
        return (
            index,
            SimpleNamespace(
                base_time_limit_sec=60.0,
                process_hard_timeout_sec=120.0,
                budget_ms=60000,
                budget_role="agent3000_60s_primary_exact",
                feature_row={"traffic_prior_version": "traffic_prior_v1_bfs"},
            ),
            "traffic_prior_v1_bfs",
        )

    monkeypatch.setattr(gate3b, "_materialize_one_context", fake_materialize)
    contexts, meta = gate3b.materialize_contexts(
        [
            {
                "g567_dataset_row_id": "ctx-3000",
                "base_time_limit_sec": 60.0,
                "process_hard_timeout_sec": 120.0,
                "nominal_budget_ms": 60000,
                "budget_role": "agent3000_60s_primary_exact",
            }
        ],
        phase="unit",
        workers=1,
        progress_interval_sec=0.01,
        cache_path=cache_path,
    )

    assert meta["resume_cache_hit"] is False
    assert contexts[0].base_time_limit_sec == 60.0
    assert contexts[0].process_hard_timeout_sec == 120.0


def test_inference_context_batches_respect_od_token_budget() -> None:
    contexts = [
        SimpleNamespace(assignment={"starts": list(range(1000))}),
        SimpleNamespace(assignment={"starts": list(range(2500))}),
        SimpleNamespace(assignment={"starts": list(range(3000))}),
        SimpleNamespace(assignment={"starts": list(range(64))}),
    ]

    batches = gate3b.g567.inference_context_batches(contexts, max_contexts=4, max_od_tokens=3000)

    assert [len(batch) for batch in batches] == [1, 1, 1, 1]
    assert all(sum(gate3b.g567.context_od_token_count(ctx) for ctx in batch) <= 3000 for batch in batches)


def test_actor_split_uses_calibration_without_parent_hash_leakage() -> None:
    examples = []
    for idx in range(6):
        split = "LABEL_TRAIN" if idx < 3 else "CALIBRATION"
        examples.append(
            gate3b.g567.ActorTrainExample(
                example_id=f"ex{idx}",
                evaluation_uid=f"uid{idx}",
                split=split,
                map_family="fam",
                physical_map_sha256=f"hash-{idx}",
                graph=None,
                assignment={"starts": []},
                feature_row={},
                target=np.zeros(len(gate3b.g567.THETA_NUMERIC_COLUMNS), dtype=np.float32),
                weight=1.0,
                positive_count=0,
                safe_count=1,
            )
        )

    train, valid = gate3b.g567.split_actor_examples(examples)
    audit = gate3b.g567.actor_split_audit(train, valid)

    assert {ex.split for ex in train} == {"LABEL_TRAIN"}
    assert {ex.split for ex in valid} == {"CALIBRATION"}
    assert audit["actor_train_validation_physical_map_overlap"] == 0


def test_completed_actor_training_summary_resumes_without_retraining(tmp_path: Path) -> None:
    gate3b.configure_isolated_outputs(tmp_path)
    gate3b.ensure_output_dirs()
    ckpt_567 = gate3b.g567.MODEL_DIR / "actor_seed567.pt"
    ckpt_568 = gate3b.g567.MODEL_DIR / "actor_seed568.pt"
    ckpt_567.write_bytes(b"seed567")
    ckpt_568.write_bytes(b"seed568")
    rows = [
        {
            "seed": 567,
            "model_path": str(ckpt_567),
            "cuda_bf16_training": True,
            "token_budget_batching": True,
            "gpu_active_hour_target_met": True,
            "gpu_active_hour_cap_respected": True,
            "gpu_active_hours": 2.0,
        },
        {
            "seed": 568,
            "model_path": str(ckpt_568),
            "cuda_bf16_training": True,
            "token_budget_batching": True,
            "gpu_active_hour_target_met": True,
            "gpu_active_hour_cap_respected": True,
            "gpu_active_hours": 2.0,
        },
    ]
    gate3b.g567.write_json(
        gate3b.g567.ACTOR_TRAINING_SUMMARY,
        {
            "decision": "gate3b_a5_actor_training_completed",
            "rows": rows,
            "gradient_rows": [{"seed": 567}, {"seed": 568}],
            "critic_used_for_actor_training": False,
        },
    )

    loaded = gate3b.load_completed_actor_training_summary(
        [567, 568],
        per_seed_min_gpu_hours=1.0,
        per_seed_max_gpu_hours=2.0,
        overwrite=False,
    )

    assert loaded is not None
    loaded_rows, gradient_rows, summary = loaded
    assert [row["seed"] for row in loaded_rows] == [567, 568]
    assert len(gradient_rows) == 2
    assert summary["gpu_active_hours"] == 4.0
    assert summary["resumed_from_completed_actor_training_summary"] is True
    assert (
        gate3b.load_completed_actor_training_summary(
            [567, 568],
            per_seed_min_gpu_hours=1.0,
            per_seed_max_gpu_hours=2.0,
            overwrite=True,
        )
        is None
    )


def test_gate3b_runner_finalizes_on_unexpected_shell_exit() -> None:
    script = (ROOT / "scripts/server_start_repair5g567_gate3b_bounded_pilot.sh").read_text(encoding="utf-8")
    assert "RUNNER_FINALIZED=0" in script
    assert 'trap on_exit EXIT' in script
    assert 'finalize "$rc" "runner_exit_trap"' in script
    assert 'RUNNER_SHELL_PID="$$"' in script
    assert 'PYTHON_PID="$!"' in script
    assert "heartbeat_loop &" in script
    assert "terminate_python_tree" in script
    assert 'pgrep -P "${PYTHON_PID}"' in script
    assert 'if [[ "${reason}" != "python_gate3b_exited" ]]' in script
    assert "runner_shell_pid" in script
    assert "python_orchestrator_pid" in script
    assert "completed_solver_rows" in script
    assert "os.getpid()" not in script
    assert script.index("trap on_exit EXIT") < script.index("python scripts/run_repair5g567_gate3b_bounded_pilot.py")


def test_gate3b_watchdog_records_external_runner_loss_without_restart() -> None:
    script = (ROOT / "scripts/watch_repair5g567_gate3b_bounded_pilot.sh").read_text(encoding="utf-8")
    assert "external_watchdog_detected_runner_process_tree_missing" in script
    assert "phase5p5_repair5g567_gate3b_bounded_pilot_runner_final_summary.json" in script
    assert "tmux new-session" not in script
    assert "server_start_repair5g567_full.sh" not in script

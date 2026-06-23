from __future__ import annotations

import random
import sys
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
        "critic_calibration": {"decision": "g567_distributional_critic_calibrated", "calibration_blockers": []},
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


def test_gate3b_runner_finalizes_on_unexpected_shell_exit() -> None:
    script = (ROOT / "scripts/server_start_repair5g567_gate3b_bounded_pilot.sh").read_text(encoding="utf-8")
    assert "RUNNER_FINALIZED=0" in script
    assert 'trap on_exit EXIT' in script
    assert 'finalize "$rc" "runner_exit_trap"' in script
    assert script.index("trap on_exit EXIT") < script.index("python scripts/run_repair5g567_gate3b_bounded_pilot.py")

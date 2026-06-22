from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5g567_gate3b_bounded_pilot as gate3b  # noqa: E402


def _fake_row(tier: int, idx: int, source: str) -> dict[str, object]:
    return {
        "g567_instance_uid": f"{source}-{tier}-{idx}",
        "agent_count": tier,
        "width": 128,
        "height": 128,
        "free_cells": max(4096, tier + 64),
        "map_family": "public" if source == "canonical_public_benchmark_map" else "synthetic",
        "map_source_type": source,
        "physical_map_sha256": f"{source}-hash-{tier}-{idx}",
    }


def test_gate3b_split_selection_preserves_parent_hash_and_public_mix() -> None:
    rows = []
    for tier in gate3b.REQUIRED_AGENT_TIERS:
        for idx in range(4):
            rows.append(_fake_row(tier, idx, "canonical_public_benchmark_map"))
            rows.append(_fake_row(tier, idx, "synthetic_stress_map"))

    label_rows, dev_rows, meta = gate3b.select_gate3b_rows(
        rows,
        label_contexts=len(gate3b.REQUIRED_AGENT_TIERS) * 2,
        development_contexts=len(gate3b.REQUIRED_AGENT_TIERS),
        label_public_fraction_min=0.50,
        development_public_fraction_min=0.70,
        max_train_free_cells=24000,
        max_train_area=32000,
    )

    assert len(label_rows) == len(gate3b.REQUIRED_AGENT_TIERS) * 2
    assert len(dev_rows) == len(gate3b.REQUIRED_AGENT_TIERS)
    assert meta["parent_map_split_leakage_count"] == 0
    assert meta["label_train_public_fraction"] >= 0.50
    assert meta["development_public_fraction"] >= 0.70
    assert set(gate3b.REQUIRED_AGENT_TIERS).issubset(set(meta["selected_agent_tiers"]))


def test_gate3b_pass_conditions_require_bounded_rows_and_no_blind() -> None:
    summary = {
        "source_state": {"decision": "g567_source_state_clean"},
        "public_benchmark_ingestion": {"ready": True},
        "label_train_contexts": 2000,
        "development_contexts": 500,
        "context_materialization": {
            "label_train": {"traffic_prior_versions": {"traffic_prior_v1_bfs": 2000}},
            "development": {"traffic_prior_versions": {"traffic_prior_v1_bfs": 500}},
        },
        "total_solver_rows": 60000,
        "selected_agent_tiers": list(gate3b.REQUIRED_AGENT_TIERS),
        "label_train_public_fraction": 0.50,
        "development_public_fraction": 0.70,
        "selected_map_source_types": {"canonical_public_benchmark_map": 1, "synthetic_stress_map": 1},
        "parent_map_split_leakage_count": 0,
        "label_replay": {"decision": "g567_three_tier_replay_materialized"},
        "development_replay": {"decision": "g567_three_tier_replay_materialized"},
        "process_hard_timeout_rows": 0,
        "critic_calibration": {"binary_calibration_by_target": {"success_regression_vs_additive": {}}},
        "actor_training_row": {"cuda_bf16_training": True, "gpu_active_hours": 2.1},
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

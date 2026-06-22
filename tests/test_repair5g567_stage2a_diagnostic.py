from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5g567_stage2a_train_diagnostic_a5 as stage2a  # noqa: E402


def test_stage2a_training_row_selection_filters_huge_public_maps() -> None:
    rows = [
        {
            "agent_count": "32",
            "free_cells": "96603",
            "width": "989",
            "height": "989",
            "map": "orz900d",
            "map_family": "game",
            "map_source_type": "canonical_public_benchmark_map",
            "g567_instance_uid": "huge",
        },
        {
            "agent_count": "32",
            "free_cells": "512",
            "width": "32",
            "height": "32",
            "map": "empty-32",
            "map_family": "empty",
            "map_source_type": "canonical_public_benchmark_map",
            "g567_instance_uid": "small",
        },
    ]

    selected = stage2a.select_training_rows(rows, context_count=1, tiers=[32], max_free_cells=12000, max_area=20000)

    assert selected[0]["g567_instance_uid"] == "small"


def test_stage2a_label_gate_rejects_hard_timeout_replay() -> None:
    summary = {
        "decision": "g567_three_tier_materialization_blocked_process_hard_timeout",
        "process_hard_timeout_rows": 1,
        "exact_materialization_rate": 1.0,
        "candidate_recognized_rate": 1.0,
        "scenario_hash_match_rate": 1.0,
        "identity_retention_rate": 1.0,
    }

    assert stage2a.replay_summary_passes_stage2a_label_gate(summary) is False


def test_stage2a_label_gate_accepts_exact_materialized_replay() -> None:
    summary = {
        "decision": "g567_three_tier_replay_materialized",
        "process_hard_timeout_rows": 0,
        "exact_materialization_rate": 1.0,
        "candidate_recognized_rate": 1.0,
        "scenario_hash_match_rate": 1.0,
        "identity_retention_rate": 1.0,
    }

    assert stage2a.replay_summary_passes_stage2a_label_gate(summary) is True

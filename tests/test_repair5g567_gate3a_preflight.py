from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5g567_gate3a_preflight as gate3a  # noqa: E402


def test_true_a5_checkpoint_audit_rejects_g556_registry_smoke_marker() -> None:
    audit = gate3a.true_a5_checkpoint_audit(
        {
            "artifact_type": "phase5p5_repair5g567_labelv54_direct_actor",
            "variant_id": "GATE2_G556_REGISTRY_SMOKE",
            "labelv54_training": True,
            "diagnostic_only": True,
            "cuda_bf16_training": True,
            "training_context_uids": ["ctx-1"],
            "training_dataset_sha256": "a" * 64,
            "source_commit": "b" * 40,
            "od_perceiver": True,
            "graph_global_layers": 0,
            "actor_state_dict": {"weight": object()},
        },
        Path("gate2_pilot_no_trained_checkpoint.pt"),
    )
    assert audit["decision"] == "not_true_a5_checkpoint"
    assert audit["forbidden_g556_or_untrained_smoke_marker"] is True


def test_true_a5_checkpoint_audit_accepts_trained_a5_payload() -> None:
    audit = gate3a.true_a5_checkpoint_audit(
        {
            "artifact_type": "phase5p5_repair5g567_labelv54_direct_actor",
            "variant_id": "A5",
            "labelv54_training": True,
            "diagnostic_only": True,
            "cuda_bf16_training": True,
            "training_context_uids": ["ctx-1", "ctx-2"],
            "training_dataset_sha256": "a" * 64,
            "source_commit": "b" * 40,
            "od_perceiver": True,
            "graph_global_layers": 0,
            "actor_state_dict": {"layer.weight": object()},
        },
        Path("phase5p5_repair5g567_a5_hierarchical_od_perceiver_actor_seed567.pt"),
    )
    assert audit["decision"] == "true_a5_checkpoint"
    assert audit["labelv54_training"] is True
    assert audit["diagnostic_only"] is True


def test_gate3a_pass_conditions_require_real_a5_inference_not_g556_smoke() -> None:
    contexts = [
        SimpleNamespace(split="GATE3A_PREFLIGHT", agents=agents, map_family=family)
        for agents in [32, 256, 1000, 3000]
        for family in ["large_empty", "large_maze", "large_warehouse", "large_room"] * 2
    ]
    replay_summary = {
        "decision": "g567_three_tier_replay_materialized",
        "exact_materialization_rate": 1.0,
        "candidate_recognized_rate": 1.0,
        "scenario_hash_match_rate": 1.0,
        "identity_retention_rate": 1.0,
        "process_hard_timeout_rows": 0,
    }
    selected_rows = [
        {"map_source_type": source, "scenario_source_type": scenario}
        for source, scenario in [
            ("canonical_public_benchmark_map", "czr004_derived_on_public_parent_map"),
            ("synthetic_stress_map", "czr004_synthetic_derived_scenario"),
        ]
        for _ in range(16)
    ]
    passing = gate3a.gate3a_pass_conditions(
        checkpoint_audit={"decision": "true_a5_checkpoint"},
        contexts=contexts,
        theta_rows=[{"variant_id": "A5", "method": f"a5_{idx}"} for idx, _ctx in enumerate(contexts)],
        replay_summary=replay_summary,
        source_state={"decision": "g567_source_state_clean"},
        forbidden_actions={"final_blind_panel_constructed_or_accessed": False},
        required_tiers=[32, 256, 1000, 3000],
        selected_rows=selected_rows,
    )
    assert all(passing.values())

    failing = gate3a.gate3a_pass_conditions(
        checkpoint_audit={"decision": "true_a5_checkpoint"},
        contexts=contexts,
        theta_rows=[{"variant_id": "GATE2_G556_REGISTRY_SMOKE", "method": "gate2_fulltheta_registry_g556_smoke"} for _ctx in contexts],
        replay_summary=replay_summary,
        source_state={"decision": "g567_source_state_clean"},
        forbidden_actions={"final_blind_panel_constructed_or_accessed": False},
        required_tiers=[32, 256, 1000, 3000],
        selected_rows=selected_rows,
    )
    assert failing["a5_inference_variant_only"] is False
    assert failing["no_g556_registry_smoke_theta"] is False

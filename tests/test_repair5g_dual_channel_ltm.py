from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_repair5g_dual_channel_oracle import ORACLE_METHOD, synthesize_oracle_rows  # noqa: E402
from create_repair5g_dual_channel_candidates import build_candidates  # noqa: E402
from create_repair5g1_agent_aware_dual_channel_candidates import (  # noqa: E402
    build_candidates as build_g1_candidates,
)
from run_repair5g_dual_channel_probe import synthesize_diagnostics  # noqa: E402


def test_repair5g_candidate_lattice_matches_g0_family() -> None:
    candidates = build_candidates()
    by_id = {candidate.candidate_id: candidate for candidate in candidates}

    assert list(by_id) == [
        "dcltm_additive_parity",
        "dcltm_c_only_locked_f4",
        "dcltm_c_only_best_f4_observed",
        "dcltm_flow_only_025",
        "dcltm_flow_only_050",
        "dcltm_block_wait_cong_flow025",
        "dcltm_block_wait_cong_flow050",
        "dcltm_goal_gated_wait_025",
        "dcltm_goal_gated_wait_050",
        "dcltm_balanced_decay",
    ]
    assert by_id["dcltm_additive_parity"].enable_dual_channel is False
    assert by_id["dcltm_additive_parity"].phase5p5_allowed is False
    assert by_id["dcltm_additive_parity"].phase6_allowed is False
    assert by_id["dcltm_flow_only_025"].lambda_cong == 0.0
    assert by_id["dcltm_flow_only_025"].lambda_flow == 0.25
    assert by_id["dcltm_goal_gated_wait_050"].alpha_cong_wait_progress < by_id[
        "dcltm_goal_gated_wait_050"
    ].alpha_cong_wait_nonprogress
    assert by_id["dcltm_balanced_decay"].rho_cong_decay == 0.95
    assert by_id["dcltm_balanced_decay"].rho_flow_decay == 0.95


def test_repair5g1_candidate_lattice_closes_c_equiv_and_agent_modes() -> None:
    candidates = build_g1_candidates()
    by_method = {candidate.runtime_method: candidate for candidate in candidates}

    assert 60 <= len(candidates) <= 140
    assert "repair5g_dual_c_equiv_additive" in by_method
    assert "repair5g_dual_c_equiv_c100_b100_w075_d090" in by_method
    assert "repair5g_dual_c_equiv_c125_b125_w075_d095" in by_method

    locked = by_method["repair5g_dual_c_equiv_c100_b100_w075_d090"]
    assert locked.alpha_cong_commit_progress == locked.alpha_cong_commit_nonprogress == 1.0
    assert locked.alpha_flow_commit_progress == 0.0
    assert locked.lambda_flow == 0.0

    components = {candidate.component for candidate in candidates}
    assert {"agent_progress_f", "flow_shield", "wait_gated", "global_f_small_lambda"} <= components
    assert any(candidate.goal_projection_mode == "agent_progress" for candidate in candidates)
    assert any(candidate.goal_projection_mode == "flow_shield" for candidate in candidates)
    assert all(candidate.phase5p5_allowed is False and candidate.phase6_allowed is False for candidate in candidates)


def test_repair5g_synthesizes_random_and_shuffled_diagnostics() -> None:
    candidates = [candidate for candidate in build_candidates() if candidate.enable_dual_channel][:2]
    rows = [
        {
            "map": "m",
            "agents": 50,
            "seed": 26,
            "scen": "case26.scen",
            "method": candidates[0].runtime_method,
            "success": True,
            "sum_of_loss_ratio": 1.2,
            "expanded_nodes": 10,
            "time_to_first_solution_ms": 1,
        },
        {
            "map": "m",
            "agents": 50,
            "seed": 26,
            "scen": "case26.scen",
            "method": candidates[1].runtime_method,
            "success": True,
            "sum_of_loss_ratio": 1.1,
            "expanded_nodes": 10,
            "time_to_first_solution_ms": 1,
        },
        {
            "map": "m",
            "agents": 50,
            "seed": 27,
            "scen": "case27.scen",
            "method": candidates[0].runtime_method,
            "success": True,
            "sum_of_loss_ratio": 1.0,
            "expanded_nodes": 10,
            "time_to_first_solution_ms": 1,
        },
        {
            "map": "m",
            "agents": 50,
            "seed": 27,
            "scen": "case27.scen",
            "method": candidates[1].runtime_method,
            "success": True,
            "sum_of_loss_ratio": 1.3,
            "expanded_nodes": 10,
            "time_to_first_solution_ms": 1,
        },
    ]

    synthetic = synthesize_diagnostics(rows, candidates)
    methods = [row["method"] for row in synthetic]

    assert methods.count("repair5g_random_dual_candidate_diagnostic") == 2
    assert methods.count("repair5g_shuffled_goal_progress_diagnostic") == 2


def test_repair5g_oracle_selects_best_candidate_by_case() -> None:
    candidate_methods = {
        "repair5g_dual_flow_only_025",
        "repair5g_dual_block_wait_cong_flow025",
    }
    rows = [
        {
            "map": "m",
            "agents": 50,
            "seed": 26,
            "scen": "case26.scen",
            "method": "lacam_star_ltm",
            "success": True,
            "sum_of_loss_ratio": 1.5,
        },
        {
            "map": "m",
            "agents": 50,
            "seed": 26,
            "scen": "case26.scen",
            "method": "repair5g_dual_flow_only_025",
            "success": True,
            "sum_of_loss_ratio": 1.4,
            "expanded_nodes": 20,
            "time_to_first_solution_ms": 1,
        },
        {
            "map": "m",
            "agents": 50,
            "seed": 26,
            "scen": "case26.scen",
            "method": "repair5g_dual_block_wait_cong_flow025",
            "success": True,
            "sum_of_loss_ratio": 1.2,
            "expanded_nodes": 30,
            "time_to_first_solution_ms": 1,
        },
    ]

    oracle_rows, by_case = synthesize_oracle_rows(rows, candidate_methods)

    assert oracle_rows[0]["method"] == ORACLE_METHOD
    assert oracle_rows[0]["repair5g_synthetic_source_method"] == "repair5g_dual_block_wait_cong_flow025"
    assert by_case[0]["oracle_delta_ratio_vs_ltm"] == -0.30000000000000004

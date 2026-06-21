from __future__ import annotations

from scripts.generate_repair5g565_context_expansion import expansion_gate
from scripts.run_repair5g565_alpha_response import effective_alpha_context_limit, summarize_exact_alpha
from scripts.run_repair5g565_fresh_solver_panel import summarize_pairs


def actor_row(**overrides):
    row = {
        "is_actor_row": True,
        "fulltheta_fingerprint_match_strict": True,
        "candidate_recognized_bool": True,
        "scenario_sha256_match": True,
        "identity_retained": True,
        "force_additive_false": True,
        "dual_channel_enabled": True,
    }
    row.update(overrides)
    return row


def test_fresh_transfer_requires_dual_channel_materialization():
    summary = summarize_pairs(
        [actor_row(force_additive_false=False)],
        [
            {
                "variant_id": "E1",
                "model_path": "good.pt",
                "success_regression": False,
                "success_gain": True,
                "quality_delta_vs_g556": -0.1,
                "split": "validation",
            }
        ],
        [{}],
    )
    assert summary["fresh_exact_materialization_passed"] is False
    assert summary["decision"] == "g565_fresh_solver_transfer_materialization_incomplete"


def test_fresh_transfer_support_is_checkpoint_granular():
    summary = summarize_pairs(
        [actor_row()],
        [
            {
                "variant_id": "E1",
                "model_path": "bad.pt",
                "success_regression": False,
                "success_gain": True,
                "quality_delta_vs_g556": 0.3,
                "split": "validation",
            },
            {
                "variant_id": "E1",
                "model_path": "good.pt",
                "success_regression": False,
                "success_gain": True,
                "quality_delta_vs_g556": -0.1,
                "split": "validation",
            },
        ],
        [{}],
    )
    assert summary["decision"] == "g565_fresh_solver_transfer_positive"
    assert summary["supporting_rich_variants"] == ["E1::good.pt"]
    assert summary["per_variant_transfer"]["E1::bad.pt"]["worse_count_vs_g556"] == 1


def test_alpha_frontier_is_checkpoint_granular():
    summary = summarize_exact_alpha(
        [actor_row()],
        [
            {
                "variant_id": "E1_ALPHA_0p5",
                "model_path": "bad.pt",
                "success_regression": False,
                "success_gain": True,
                "quality_delta_vs_g556": 0.2,
            },
            {
                "variant_id": "E1_ALPHA_0p5",
                "model_path": "good.pt",
                "success_regression": False,
                "success_gain": True,
                "quality_delta_vs_g556": -0.2,
            },
        ],
        [{}],
    )
    assert summary["alpha_exact_materialization_passed"] is True
    assert "E1_ALPHA_0p5::good.pt" in summary["safe_alpha_frontier"]
    assert "E1_ALPHA_0p5::bad.pt" not in summary["safe_alpha_frontier"]


def test_alpha_response_keeps_md_context_floor():
    assert effective_alpha_context_limit(256) == 800
    assert effective_alpha_context_limit(1000) == 1000


def test_context_expansion_requires_md_diversity():
    underdiverse = [
        {"physical_map_sha256": f"hash_{idx % 24}", "map_family": f"family_{idx % 8}", "agent_count": 32, "budget_ms": 1000}
        for idx in range(5000)
    ]
    gate = expansion_gate(underdiverse, 5000)
    assert gate["ready"] is False
    assert "insufficient_physical_map_hashes" in gate["block_reasons"]
    assert "insufficient_map_families" in gate["block_reasons"]
    assert "insufficient_agent_count_tiers" in gate["block_reasons"]
    assert "insufficient_budget_tiers" in gate["block_reasons"]

    diverse = [
        {"physical_map_sha256": f"hash_{idx % 32}", "map_family": f"family_{idx % 10}", "agent_count": [16, 32, 64, 128][idx % 4], "budget_ms": [500, 1000, 2000, 5000][idx % 4]}
        for idx in range(5000)
    ]
    assert expansion_gate(diverse, 5000)["ready"] is True

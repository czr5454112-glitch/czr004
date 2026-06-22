from __future__ import annotations

import math

import pytest

from gcst.theta_schema import compare_theta_to_fingerprint, parse_updateparams_fingerprint
from gcst.three_tier_baselines import (
    BASELINES,
    TIER_A_ADDITIVE,
    TIER_B_STATIC_FLOW,
    TIER_C_G556,
    baseline_by_alias,
    baseline_registry_rows,
    fingerprint_matches,
)


def _parsed(tier):
    return parse_updateparams_fingerprint(tier.fingerprint)


def test_tierA_additive_fingerprint() -> None:
    parsed = _parsed(TIER_A_ADDITIVE)
    assert parsed["force_additive"] == "1"
    assert parsed["enable_dual_channel"] == "0"
    ok, mismatches = fingerprint_matches(parsed, TIER_A_ADDITIVE)
    assert ok, mismatches


def test_tierB_alias_resolves_to_frozen_underlying() -> None:
    assert baseline_by_alias("repair5g2_best_frozen_static_candidate") is TIER_B_STATIC_FLOW
    assert baseline_by_alias("repair5g59_static_flow_shield") is TIER_B_STATIC_FLOW
    assert TIER_B_STATIC_FLOW.underlying_method == "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75"


def test_tierB_fingerprint_is_constant() -> None:
    parsed = _parsed(TIER_B_STATIC_FLOW)
    assert parsed["force_additive"] == "0"
    assert parsed["enable_dual_channel"] == "1"
    assert parsed["goal_projection_mode"] == "flow_shield"
    assert float(parsed["alpha_cong_commit_progress"]) == pytest.approx(1.25)
    assert float(parsed["alpha_cong_block"]) == pytest.approx(1.25)
    assert float(parsed["alpha_cong_wait_nonprogress"]) == pytest.approx(0.75)
    assert float(parsed["rho_cong_decay"]) == pytest.approx(0.95)
    assert float(parsed["flow_shield_beta"]) == pytest.approx(0.35)
    assert float(parsed["max_flow_shield"]) == pytest.approx(0.75)
    ok, mismatches = fingerprint_matches(parsed, TIER_B_STATIC_FLOW)
    assert ok, mismatches


def test_tierC_g556_fingerprint() -> None:
    parsed = _parsed(TIER_C_G556)
    assert parsed["force_additive"] == "0"
    assert parsed["enable_dual_channel"] == "1"
    assert parsed["goal_projection_mode"] == "flow_shield"
    ok, mismatches = compare_theta_to_fingerprint(TIER_C_G556.fingerprint, TIER_C_G556.theta, tolerance=1.0e-9)
    assert ok, mismatches


def test_baseline_registry_has_exactly_three_scientific_tiers() -> None:
    rows = baseline_registry_rows({"claim_closed": True})
    assert [row["tier"] for row in rows] == ["A", "B", "C"]
    assert [row["candidate_id"] for row in rows] == [
        "repair5g59_additive_fallback",
        "repair5g59_static_flow_shield",
        "g556_c063174",
    ]
    assert all(row["candidate_id"] == row["materialized_method"] == row["solver_alias"] for row in rows)
    assert {row["canonical_report_id"] for row in rows} == {
        "paper_additive_ltm",
        "static_flow_shield_hand",
        "g556_c063174",
    }
    assert len(BASELINES) == 3
    assert all(row["source_sha256"] for row in rows)
    assert all(math.isfinite(float(row.get("theta_max_edge_cost", 11.0))) for row in rows if row["tier"] != "A")


def test_baseline_identity_is_not_inferred_from_label() -> None:
    with pytest.raises(KeyError):
        baseline_by_alias("quality_delta_vs_additive")
    with pytest.raises(KeyError):
        baseline_by_alias("labelv51_development_safe")

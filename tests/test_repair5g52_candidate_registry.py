from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from repair5g_candidate_registry import build_registry  # noqa: E402


def test_g52_static_alias_hash_matches_target() -> None:
    frozen = {
        "selected_static_candidate": "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
        "selected_c_equiv_baseline": "repair5g_dual_c_equiv_c100_b100_w075_d100",
        "g1_top_diagnostic_candidate": "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
        "group_rules": [
            {
                "map": "random-32-32-20",
                "agents": 50,
                "candidate": "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
            }
        ],
    }
    rows = {row.method_name: row for row in build_registry(frozen, {})}

    alias = rows["repair5g2_best_frozen_static_candidate"]
    target = rows["repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75"]

    assert alias.is_alias
    assert alias.alias_target == target.method_name
    assert alias.updateparams_hash == target.updateparams_hash


def test_g52_flow_shield_params_are_goal_projected() -> None:
    rows = {row.method_name: row for row in build_registry({}, {})}
    row = rows["repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75"]

    assert row.enable_dual_channel
    assert row.goal_projection_mode == "flow_shield"
    assert row.flow_shield_beta == 0.35
    assert row.max_flow_shield == 0.75
    assert row.min_edge_cost == 1.0

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from repair5g51_common import selector_spec_payload  # noqa: E402


def test_g51_selector_spec_uses_concrete_alias_targets() -> None:
    spec = selector_spec_payload(
        selector_name="unit_safe",
        left_method="repair5g2_best_frozen_static_candidate",
        right_method="repair5g2_best_frozen_static_candidate",
        fallback_static="repair5g2_best_frozen_static_candidate",
        static_candidate="repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
        c_equiv_candidate="repair5g_dual_c_equiv_c100_b100_w075_d100",
    )

    assert spec["repair5g2_best_frozen_static_candidate"].startswith("repair5g1_shield_")
    assert spec["repair5g2_c_equiv_best_frozen_baseline"].startswith("repair5g_dual_c_equiv_")
    assert spec["candidate_aliases"]["repair5g2_best_frozen_static_candidate"].startswith("repair5g1_shield_")


def test_g51_decision_keeps_aaai_closed() -> None:
    summary = json.loads(
        (ROOT / "outputs/reports/phase5p5_repair5g51_decision_summary.json").read_text(encoding="utf-8")
    )

    assert summary["decision"] == "runtime_hook_bug_blocks_learning"
    assert summary["aaai_ready"] is False
    assert summary["phase5p5_allowed"] is False
    assert summary["phase6_allowed"] is False

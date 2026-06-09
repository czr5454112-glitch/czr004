from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_aaai_quality_policy_exists_and_keeps_repair5g5_closed() -> None:
    policy = (ROOT / "docs/aaai_quality_requirements.md").read_text(encoding="utf-8")
    selector = json.loads(
        (ROOT / "artifacts/models/laur_ltm/repair5g5_contextual_flow_shield_selector/selector_spec.json").read_text(
            encoding="utf-8"
        )
    )

    assert "Repair5G AAAI Quality Requirements" in policy
    assert "Phase5.5 and Phase6 remain closed" in policy
    assert selector["forbidden_final_ids"] == "166..205 primary learned-runtime holdout"
    assert selector["phase5p5_allowed"] is False
    assert selector["phase6_allowed"] is False
    assert selector["aaai_ready"] is False


def test_readiness_summary_never_marks_aaai_ready_without_final_gates() -> None:
    summary_path = ROOT / "outputs/reports/phase5p5_repair5g_aaai_readiness_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["aaai_ready"] is False
    assert summary["phase5p5_allowed"] is False
    assert summary["phase6_allowed"] is False

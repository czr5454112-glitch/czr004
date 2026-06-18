from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import update_repair5g557_docs_from_final as docs  # noqa: E402


def _decision(**updates: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "decision": "g557_blind_failed_keep_g556",
        "primary_baseline": "g556_c063174",
        "dynamic_policy": False,
        "checkpoint_policy": False,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
        "context_horizons": 20_000,
        "primary_row_level_examples_vs_g556": 3_000_000,
        "total_row_level_examples": 5_000_000,
        "stage1_solver_rows": 0,
        "stage2_solver_rows": 0,
        "blind_solver_rows": 0,
        "success_regressions_vs_g556": 0,
    }
    decision.update(updates)
    return decision


def test_require_static_guardrails_accepts_g556_closed_claims() -> None:
    docs.require_static_guardrails(_decision())


def test_require_static_guardrails_rejects_wrong_baseline() -> None:
    with pytest.raises(ValueError, match="primary_baseline"):
        docs.require_static_guardrails(_decision(primary_baseline="g554_c00051"))


def test_require_static_guardrails_rejects_open_phase6_claim() -> None:
    with pytest.raises(ValueError, match="phase6_allowed"):
        docs.require_static_guardrails(_decision(phase6_allowed=True))


def test_block_text_contains_final_evidence_and_closed_claims() -> None:
    block = docs.block_text(
        _decision(
            stage1_solver_rows=600_000,
            stage2_solver_rows=600_000,
            blind_solver_rows=720_000,
            quality_delta_vs_g556="-0.01",
            quality_delta_ci_upper_vs_g556="-0.001",
            better_count_vs_g556=12,
            worse_count_vs_g556=3,
        ),
        {"same_context_candidate_rows": 3_000_000},
        {"passed": True, "failed_count": 0},
        result_date="2026-06-19",
    )

    assert docs.BEGIN in block
    assert "## 2026-06-19 - G5.57 final result" in block
    assert "Final decision: `g557_blind_failed_keep_g556`" in block
    assert "primary row-level examples vs g556: `3,000,000`" in block
    assert "`phase6_allowed=false`" in block
    assert "quality delta vs g556: `-0.01`; CI upper `-0.001`" in block


def test_insert_after_heading_and_replace_marker_are_idempotent() -> None:
    block = docs.block_text(_decision(), {"same_context_candidate_rows": 3_000_000}, {})
    original = "# Doc\n\n## Anchor\n\nOld body.\n\n## Next\n\nLater.\n"

    updated = docs.insert_after_heading(original, "## Anchor", block)
    assert updated.count(docs.BEGIN) == 1
    assert updated.index(docs.BEGIN) < updated.index("## Next")

    replacement = block.replace("Final decision:", "Final decision updated:")
    updated_again = docs.insert_after_heading(updated, "## Anchor", replacement)
    assert updated_again.count(docs.BEGIN) == 1
    assert "Final decision updated:" in updated_again

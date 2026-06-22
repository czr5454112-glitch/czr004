from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5g567_strict_pipeline as g567  # noqa: E402


def test_source_state_gate_accepts_clean_expected_head() -> None:
    assert (
        g567.classify_source_state(
            inside_work_tree="true",
            head="abc123",
            expected_head="abc123",
            status_short="",
            submodule_status="",
            source_plan_sha256="f" * 64,
        )
        == []
    )


def test_source_state_gate_fails_closed_on_dirty_wrong_head_and_submodule_mismatch() -> None:
    failures = g567.classify_source_state(
        inside_work_tree="true",
        head="abc123",
        expected_head="def456",
        status_short=" M scripts/run_repair5g567_strict_pipeline.py",
        submodule_status="+abcdef external/lacam2 (heads/main)",
        source_plan_sha256="f" * 64,
    )
    assert "wrong_head" in failures
    assert "dirty_status" in failures
    assert "submodule_mismatch" in failures


def test_source_state_gate_fails_closed_on_missing_git_metadata_or_plan() -> None:
    failures = g567.classify_source_state(
        inside_work_tree="git_error:not a repository",
        head="git_error:not a repository",
        expected_head="",
        status_short="git_error:not a repository",
        submodule_status="git_error:not a repository",
        source_plan_sha256="",
    )
    assert "missing_or_invalid_git_metadata" in failures
    assert "missing_head" in failures
    assert "dirty_status_unavailable" in failures
    assert "submodule_status_unavailable" in failures
    assert "missing_source_plan" in failures

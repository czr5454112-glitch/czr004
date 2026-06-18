from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_repair5g557_final_artifacts as audit  # noqa: E402


def _base_decision(**updates: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "decision": "g557_blind_failed_keep_g556",
        "primary_baseline": "g556_c063174",
        "dynamic_policy": False,
        "checkpoint_policy": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "context_horizons": audit.MIN_CONTEXTS,
        "primary_row_level_examples_vs_g556": audit.MIN_PRIMARY_ROWS,
        "total_row_level_examples": audit.MIN_TOTAL_ROWS,
        "strict_blind_passed": False,
        "stage1_solver_rows": audit.MIN_STAGE1_ROWS,
        "stage2_solver_rows": audit.MIN_STAGE2_ROWS,
        "blind_solver_rows": audit.MIN_BLIND_ROWS,
    }
    decision.update(updates)
    return decision


def _stage1(**updates: object) -> dict[str, object]:
    row: dict[str, object] = {
        "stage1_solver_rows": audit.MIN_STAGE1_ROWS,
        "gate_passed": True,
        "success_regression_count_vs_g556_c063174": 0,
    }
    row.update(updates)
    return row


def _stage2(**updates: object) -> dict[str, object]:
    row: dict[str, object] = {
        "stage2_solver_rows": audit.MIN_STAGE2_ROWS,
        "gate_passed": True,
    }
    row.update(updates)
    return row


def _blind(**updates: object) -> dict[str, object]:
    row: dict[str, object] = {
        "blind_solver_rows": audit.MIN_BLIND_ROWS,
        "gate_passed": False,
    }
    row.update(updates)
    return row


def _fake_loader(
    decision: dict[str, object] | None = None,
    label: dict[str, object] | None = None,
    gcst: dict[str, object] | None = None,
    stage1: dict[str, object] | None = None,
    stage2: dict[str, object] | None = None,
    blind: dict[str, object] | None = None,
):
    final_decision = decision or _base_decision()
    label_summary = label or {"same_context_candidate_rows": audit.MIN_SAME_CONTEXT_ROWS}
    gcst_summary = gcst or {"offline_generator_gate_passed": True}
    stage1_summary = stage1 or _stage1()
    stage2_summary = stage2 or _stage2()
    blind_summary = blind or _blind()
    compact_manifest = {
        "selected_file_count": 3,
        "files": [
            {"path": "outputs/reports/phase5p5_repair5g557_decision_summary.json", "selected": True},
            {"path": "outputs/tables/phase5p5_repair5g557_claim_ledger.csv", "selected": True},
        ],
    }

    def load_json(rel_path: str) -> dict[str, object]:
        if rel_path == audit.DECISION_SUMMARY:
            return dict(final_decision)
        if rel_path == audit.LABEL_SUMMARY:
            return dict(label_summary)
        if rel_path == audit.GCST_SUMMARY:
            return dict(gcst_summary)
        if rel_path == audit.STAGE1_SUMMARY:
            return dict(stage1_summary)
        if rel_path == audit.STAGE2_SUMMARY:
            return dict(stage2_summary)
        if rel_path == audit.BLIND_SUMMARY:
            return dict(blind_summary)
        if rel_path == "outputs/reports/phase5p5_repair5g557_compact_bundle_manifest.json":
            return dict(compact_manifest)
        return {"decision": "synthetic_present"}

    return load_json


def test_audit_accepts_terminal_failure_with_closed_claims(monkeypatch) -> None:
    monkeypatch.setattr(audit, "load_json", _fake_loader())

    result = audit.audit()

    assert result["passed"] is True
    assert result["decision"] == "g557_blind_failed_keep_g556"


def test_audit_rejects_continue_topup_decision(monkeypatch) -> None:
    monkeypatch.setattr(
        audit,
        "load_json",
        _fake_loader(_base_decision(decision="g557_label_matrix_underpowered_continue_topup")),
    )

    result = audit.audit()

    failed = {check["name"] for check in result["checks"] if not check["passed"]}
    assert result["passed"] is False
    assert "decision_not_continue_topup" in failed


def test_audit_rejects_open_runtime_claim(monkeypatch) -> None:
    monkeypatch.setattr(audit, "load_json", _fake_loader(_base_decision(runtime_claim_allowed=True)))

    result = audit.audit()

    failed = {check["name"] for check in result["checks"] if not check["passed"]}
    assert result["passed"] is False
    assert "claim_closed:runtime_claim_allowed" in failed


def test_audit_strict_pass_requires_solver_rows_and_controls(monkeypatch) -> None:
    monkeypatch.setattr(
        audit,
        "load_json",
        _fake_loader(
            decision=_base_decision(
                decision="g557_gcst_strict_blind_passed_keep_claims_closed",
                strict_blind_passed=True,
                stage1_solver_rows=audit.MIN_STAGE1_ROWS,
                stage2_solver_rows=audit.MIN_STAGE2_ROWS,
                blind_solver_rows=audit.MIN_BLIND_ROWS,
                beats_map_family_lookup=True,
                beats_tabular_only_control=True,
                success_regressions_vs_g556=0,
            ),
            blind=_blind(gate_passed=True),
        ),
    )

    result = audit.audit(require_strict_pass=True)

    assert result["passed"] is True


def test_audit_rejects_stage2_failure_without_stage1_floor(monkeypatch) -> None:
    monkeypatch.setattr(
        audit,
        "load_json",
        _fake_loader(
            decision=_base_decision(decision="g557_stage2_heldout_failed_keep_g556"),
            stage1=_stage1(stage1_solver_rows=audit.MIN_STAGE1_ROWS - 1),
            stage2=_stage2(gate_passed=False),
        ),
    )

    result = audit.audit()

    failed = {check["name"] for check in result["checks"] if not check["passed"]}
    assert result["passed"] is False
    assert "stage1_rows_min" in failed


def test_audit_accepts_offline_exploratory_terminal_without_stage_replay(monkeypatch) -> None:
    monkeypatch.setattr(
        audit,
        "load_json",
        _fake_loader(
            decision=_base_decision(decision="g557_gcst_offline_not_better_than_controls_exploratory_only"),
            gcst={"offline_generator_gate_passed": False},
            stage1=_stage1(stage1_solver_rows=0, gate_passed=False),
            stage2=_stage2(stage2_solver_rows=0, gate_passed=False),
            blind=_blind(blind_solver_rows=0, gate_passed=False),
        ),
    )

    result = audit.audit()

    assert result["passed"] is True


def test_audit_rejects_selected_log_in_compact_manifest(monkeypatch) -> None:
    def load_json(rel_path: str) -> dict[str, object]:
        if rel_path == audit.DECISION_SUMMARY:
            return _base_decision()
        if rel_path == audit.LABEL_SUMMARY:
            return {"same_context_candidate_rows": audit.MIN_SAME_CONTEXT_ROWS}
        if rel_path == "outputs/reports/phase5p5_repair5g557_compact_bundle_manifest.json":
            return {
                "selected_file_count": 1,
                "files": [
                    {"path": "outputs/logs/phase5p5_repair5g557_label_matrix/label_matrix_results.csv", "selected": True}
                ],
            }
        return {"decision": "synthetic_present"}

    monkeypatch.setattr(audit, "load_json", load_json)

    result = audit.audit()

    failed = {check["name"] for check in result["checks"] if not check["passed"]}
    assert result["passed"] is False
    assert "compact_bundle_excludes_raw_large_artifacts" in failed

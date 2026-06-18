from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import audit_repair5g557_git_payload as payload  # noqa: E402


def test_allowed_payload_paths() -> None:
    assert payload.is_allowed_path("scripts/audit_repair5g557_git_payload.py")
    assert payload.is_allowed_path("tests/test_repair5g557_git_payload_audit.py")
    assert payload.is_allowed_path("outputs/reports/phase5p5_repair5g557_decision_summary.json")
    assert payload.is_allowed_path("outputs/tables/phase5p5_repair5g557_claim_ledger.csv")
    assert payload.is_allowed_path("artifacts/models/laur_ltm/repair5g557_gcst_generator_manifest.json")
    assert payload.is_allowed_path("deep-research-report.md")


def test_disallowed_payload_paths() -> None:
    assert not payload.is_allowed_path("outputs/reports/phase5p5_repair5g556_decision_summary.json")
    assert not payload.is_allowed_path("scripts/random_helper.py")
    assert not payload.is_allowed_path("tests/test_unrelated.py")


def test_forbidden_path_shapes_reject_logs_and_archives() -> None:
    assert payload.has_forbidden_path_shape("outputs/logs/phase5p5_repair5g557_label_matrix/results.csv")
    assert payload.has_forbidden_path_shape("outputs/server/phase5p5_repair5g557_bundles/bundle.tar.gz")
    assert payload.has_forbidden_path_shape("outputs/reports/phase5p5_repair5g557_bundle.tar.gz")
    assert payload.has_forbidden_path_shape("outputs/tables/raw/phase5p5_repair5g557.csv")
    assert payload.has_forbidden_path_shape("outputs/reports/phase5p5_repair5g557_decision_summary.json") is None


def test_normalize_path_rejects_path_traversal() -> None:
    try:
        payload.normalize_path("../escape.txt")
    except ValueError as exc:
        assert "unsafe staged path" in str(exc)
    else:
        raise AssertionError("path traversal was not rejected")


def test_secret_hits_detects_password_like_text(tmp_path: Path) -> None:
    path = tmp_path / "note.md"
    sample = "pass" + "word = " + '"' + "abcdefghijklmnopqrstuvwxyz" + '"' + "\n"
    path.write_text(sample, encoding="utf-8")

    hits = payload.secret_hits(path)

    assert hits


def test_audit_paths_accepts_expected_g557_file(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path
    path = root / "outputs/reports/phase5p5_repair5g557_decision_summary.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"decision":"synthetic"}\n', encoding="utf-8")
    monkeypatch.setattr(payload, "ROOT", root)

    result = payload.audit_paths([("A", "outputs/reports/phase5p5_repair5g557_decision_summary.json")])

    assert result["passed"] is True


def test_audit_paths_rejects_server_bundle(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path
    path = root / "outputs/server/phase5p5_repair5g557_bundles/bundle.tar.gz"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"bundle")
    monkeypatch.setattr(payload, "ROOT", root)

    result = payload.audit_paths([("A", "outputs/server/phase5p5_repair5g557_bundles/bundle.tar.gz")])

    failed = {(check["check"], check["path"]) for check in result["checks"] if not check["passed"]}
    assert result["passed"] is False
    assert ("allowed_path", "outputs/server/phase5p5_repair5g557_bundles/bundle.tar.gz") in failed
    assert ("forbidden_path_shape", "outputs/server/phase5p5_repair5g557_bundles/bundle.tar.gz") in failed

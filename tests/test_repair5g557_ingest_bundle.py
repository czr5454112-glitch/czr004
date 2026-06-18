from __future__ import annotations

import io
import json
import sys
import tarfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ingest_repair5g557_remote_bundle as ingest  # noqa: E402


def _write_tar(path: Path, members: dict[str, bytes]) -> None:
    with tarfile.open(path, "w:gz") as tar:
        for name, payload in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))


def _decision(**updates: object) -> dict[str, object]:
    decision: dict[str, object] = {
        "decision": "synthetic_g557_final",
        "primary_baseline": "g556_c063174",
        "dynamic_policy": False,
        "checkpoint_policy": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    decision.update(updates)
    return decision


def test_inspect_bundle_accepts_compact_g557_paths(tmp_path: Path) -> None:
    bundle = tmp_path / "compact.tar.gz"
    _write_tar(
        bundle,
        {
            "outputs/reports/phase5p5_repair5g557_decision_summary.json": json.dumps(_decision()).encode("utf-8"),
            "outputs/tables/phase5p5_repair5g557_claim_ledger.csv": b"claim,allowed\nphase6,false\n",
            "artifacts/models/laur_ltm/repair5g557_gcst_generator_manifest.json": b"{}\n",
        },
    )

    members = ingest.inspect_bundle(bundle, ingest.MAX_MEMBER_BYTES)

    assert [member.name for member in members] == [
        "outputs/reports/phase5p5_repair5g557_decision_summary.json",
        "outputs/tables/phase5p5_repair5g557_claim_ledger.csv",
        "artifacts/models/laur_ltm/repair5g557_gcst_generator_manifest.json",
    ]


def test_inspect_bundle_rejects_path_traversal(tmp_path: Path) -> None:
    bundle = tmp_path / "escape.tar.gz"
    _write_tar(bundle, {"../escape.txt": b"nope"})

    with pytest.raises(ValueError, match="unsafe tar member path"):
        ingest.inspect_bundle(bundle, ingest.MAX_MEMBER_BYTES)


def test_inspect_bundle_rejects_raw_logs(tmp_path: Path) -> None:
    bundle = tmp_path / "logs.tar.gz"
    _write_tar(bundle, {"outputs/logs/phase5p5_repair5g557_label_matrix/label_matrix_results.csv": b"raw"})

    with pytest.raises(ValueError, match="unexpected tar member"):
        ingest.inspect_bundle(bundle, ingest.MAX_MEMBER_BYTES)


def test_validate_decision_rejects_runtime_claims(tmp_path: Path) -> None:
    decision_path = tmp_path / "outputs/reports/phase5p5_repair5g557_decision_summary.json"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text(
        json.dumps(_decision(runtime_claim_allowed=True, aaai_ready=True)),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="runtime_claim_allowed"):
        ingest.validate_decision(tmp_path, allow_missing=False)


def test_validate_decision_accepts_static_g556_guardrails(tmp_path: Path) -> None:
    decision_path = tmp_path / "outputs/reports/phase5p5_repair5g557_decision_summary.json"
    decision_path.parent.mkdir(parents=True)
    decision_path.write_text(json.dumps(_decision(strict_blind_passed=False)), encoding="utf-8")

    result = ingest.validate_decision(tmp_path, allow_missing=False)

    assert result["decision_summary_present"] is True
    assert result["primary_baseline"] == "g556_c063174"
    assert result["strict_blind_passed"] is False

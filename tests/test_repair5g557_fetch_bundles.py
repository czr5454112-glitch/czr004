from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_repair5g557_remote_bundles as fetch  # noqa: E402


def test_parse_find_line_accepts_tab_separated_remote_bundle() -> None:
    bundle = fetch.parse_find_line(
        "compact",
        "1781760000.123456\t42\t/root/shared-nvme/czr004_g557_bundles/czr004_g557_compact_results_20260618_230000.tar.gz\n",
    )

    assert bundle is not None
    assert bundle.kind == "compact"
    assert bundle.size_bytes == 42
    assert bundle.remote_path.endswith("czr004_g557_compact_results_20260618_230000.tar.gz")


def test_parse_find_line_returns_none_for_missing_output() -> None:
    assert fetch.parse_find_line("compact", "") is None


def test_snapshot_kind_includes_caretaker_snapshots() -> None:
    patterns = fetch.KIND_PATTERNS["snapshot"]

    assert "czr004_g557_*_snapshot_*.tar.gz" in patterns
    assert "czr004_g557_*_caretaker_*.tar.gz" in patterns


def test_parse_find_line_rejects_unexpected_format() -> None:
    with pytest.raises(ValueError, match="unexpected find output"):
        fetch.parse_find_line("compact", "not enough columns")


def test_parse_sha256_text_accepts_sha256sum_format() -> None:
    digest = "a" * 64
    parsed_digest, parsed_name = fetch.parse_sha256_text(f"{digest}  bundle.tar.gz\n")

    assert parsed_digest == digest
    assert parsed_name == "bundle.tar.gz"


def test_parse_sha256_text_rejects_bad_digest() -> None:
    with pytest.raises(ValueError, match="invalid sha256 digest"):
        fetch.parse_sha256_text("notasha  bundle.tar.gz\n")


def test_verify_sha256_file(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle.tar.gz"
    payload = b"compact bundle bytes"
    bundle.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    sha_path = tmp_path / "bundle.tar.gz.sha256"
    sha_path.write_text(f"{digest}  bundle.tar.gz\n", encoding="utf-8")

    result = fetch.verify_sha256(bundle, sha_path)

    assert result["passed"] is True
    assert result["actual_sha256"] == digest

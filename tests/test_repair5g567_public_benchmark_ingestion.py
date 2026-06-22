from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5g567_public_benchmark_ingestion as ingest  # noqa: E402


def _write_map(path: Path, rows: list[str]) -> None:
    path.write_text(
        "\n".join(
            [
                "type octile",
                f"height {len(rows)}",
                f"width {len(rows[0])}",
                "map",
                *rows,
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_scen(path: Path, map_name: str, lines: list[str]) -> None:
    path.write_text("version 1\n" + "\n".join(lines) + "\n", encoding="utf-8")


def test_validate_scenario_prefix_detects_duplicate_start_and_unreachable_od(tmp_path: Path) -> None:
    map_path = tmp_path / "unit.map"
    scen_path = tmp_path / "unit-random-1.scen"
    _write_map(map_path, [".....", "@@@@@", "....."])
    _write_scen(
        scen_path,
        "unit.map",
        [
            "0 unit.map 5 3 0 0 4 2 1",
            "1 unit.map 5 3 0 0 3 2 1",
        ],
    )
    info = ingest.read_movingai_map(map_path)
    validation = ingest.validate_scenario_prefix(info, scen_path, 2)
    assert validation["validation_result"] == "fail"
    assert validation["duplicate_start_count"] == 1
    assert validation["od_unreachable_count"] == 2
    assert "duplicate_starts_in_prefix" in validation["validation_failures"]
    assert "od_unreachable_in_prefix" in validation["validation_failures"]


def test_parent_split_audit_blocks_same_parent_in_multiple_scientific_splits() -> None:
    rows = [
        {
            "parent_physical_map_sha256": "abc",
            "map_name": "unit",
            "source_category": "movingai_canonical",
            "panel": "M",
            "scientific_split": "LABEL_TRAIN",
        },
        {
            "parent_physical_map_sha256": "abc",
            "map_name": "unit",
            "source_category": "movingai_canonical",
            "panel": "M",
            "scientific_split": "BLIND",
        },
    ]
    audit_rows, failures = ingest.build_parent_split_audit(rows, [])
    assert failures == ["abc:parent_map_crosses_scientific_splits"]
    assert audit_rows[0]["validation_result"] == "fail"


def test_no_download_ingestion_writes_blocked_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ingest, "PUBLIC_INGESTION_MD", tmp_path / "ingestion.md")
    monkeypatch.setattr(ingest, "PUBLIC_INGESTION_SUMMARY", tmp_path / "ingestion.json")
    monkeypatch.setattr(ingest, "PUBLIC_MAP_REGISTRY", tmp_path / "maps.csv")
    monkeypatch.setattr(ingest, "PUBLIC_SCENARIO_REGISTRY", tmp_path / "scenarios.csv")
    monkeypatch.setattr(ingest, "PARENT_MAP_SPLIT_AUDIT", tmp_path / "split.csv")
    summary = ingest.ingest_public_benchmarks(benchmark_root=tmp_path / "bench", no_download=True, include_optional_sillm=False)
    assert summary["decision"] == "g567_public_benchmark_ingestion_blocked"
    assert summary["failure_count"] > 0
    assert summary["raw_archives_committed"] is False
    assert summary["final_blind_accessed"] is False
    assert (tmp_path / "ingestion.json").exists()
    assert (tmp_path / "maps.csv").exists()
    assert (tmp_path / "scenarios.csv").exists()

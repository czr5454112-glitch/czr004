from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5g567_strict_pipeline as g567  # noqa: E402


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


def test_valid_context_generation_defers_traffic_prior_materialization(monkeypatch, tmp_path: Path) -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("context validity generation must not compute full C0/F0 traffic prior")

    monkeypatch.setattr(g567.g561_bank, "compute_traffic_prior", fail_if_called)
    audit_rows, manifest_rows, meta = g567.make_generated_contexts(1, 567, tmp_path)
    assert meta["generated"] == 1
    assert audit_rows[0]["valid"] is True
    assert manifest_rows[0]["context_generation_stage"] == "stage_a_component_validity_only"
    assert manifest_rows[0]["feature_materialization_stage"] == "stage_b_deferred_c0_f0_traffic_prior"
    assert manifest_rows[0]["path_found_rate_source"] == "same_connected_component_no_path_materialization"
    assert manifest_rows[0]["distance_mode"] == "manhattan_lower_bound_no_path_materialization"
    scenario_lines = g567.resolve(manifest_rows[0]["raw_scenario_path"]).read_text(encoding="utf-8").splitlines()
    assert len(scenario_lines) - 1 == int(manifest_rows[0]["agent_count"])


def test_public_benchmark_discovery_requires_ready_ingestion(monkeypatch, tmp_path: Path) -> None:
    summary = tmp_path / "ingestion_summary.json"
    maps = tmp_path / "public_maps.csv"
    scenarios = tmp_path / "public_scenarios.csv"
    split = tmp_path / "split.csv"
    monkeypatch.setattr(g567, "PUBLIC_BENCHMARK_INGESTION_SUMMARY", summary)
    monkeypatch.setattr(g567, "PUBLIC_MAP_REGISTRY", maps)
    monkeypatch.setattr(g567, "PUBLIC_SCENARIO_REGISTRY", scenarios)
    monkeypatch.setattr(g567, "PARENT_MAP_SPLIT_AUDIT", split)

    map_path = tmp_path / "unit-public.map"
    _write_map(map_path, ["....", "....", "....", "...."])
    row = {
        "validation_result": "pass",
        "use_in_g567": "true",
        "map_source_type": "canonical_public_benchmark_map",
        "local_map_path": str(map_path),
        "physical_map_sha256": g567.sha256_file(map_path),
        "map_name": "unit-public",
        "map_family": "unit",
        "source_category": "movingai_canonical",
        "panel": "M",
    }
    g567.write_rows(maps, [row])
    g567.write_rows(scenarios, [])
    g567.write_rows(split, [])
    assert g567.discover_public_benchmark_map_specs() == []

    g567.write_json(summary, {"decision": "g567_public_benchmark_ingestion_blocked"})
    assert g567.discover_public_benchmark_map_specs() == []

    g567.write_json(summary, {"decision": "g567_public_benchmark_ingestion_ready"})
    specs = g567.discover_public_benchmark_map_specs()
    assert len(specs) == 1
    assert specs[0]["map"] == "unit_public"

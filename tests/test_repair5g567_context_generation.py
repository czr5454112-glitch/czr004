from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5g567_strict_pipeline as g567  # noqa: E402


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

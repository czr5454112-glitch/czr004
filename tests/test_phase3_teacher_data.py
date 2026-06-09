from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.schema import run_id_for, validate_edge_label, validate_manifest_row
from czr004_teacher.splits import DEFAULT_SPLIT_MAPS, audit_no_leakage, split_for, validate_split_maps


def edge_label(run_id: str = "run-1") -> dict:
    return {
        "schema_version": "phase3_edge_label_v1",
        "run_id": run_id,
        "source": "final_ltm_traffic_map",
        "method": "lacam_star_ltm",
        "map": "empty-32-32",
        "scen": "phase1a-generated-random/empty-32-32-random-1.scen",
        "agents": 100,
        "seed": 1,
        "time_limit_sec": 2,
        "objective": "sum_of_loss",
        "from_id": 1,
        "to_id": 2,
        "from_index": 33,
        "to_index": 34,
        "from_x": 1,
        "from_y": 1,
        "to_x": 2,
        "to_y": 1,
        "from_degree": 4,
        "to_degree": 4,
        "ltm_raw_count": 3,
        "ltm_normalized_weight": 7.5,
        "warm_start_target_weight": 7.5,
        "residual_reference_weight": 7.5,
        "residual_delta_target": 0,
        "traversal_cost": 8.5,
        "nonzero": True,
        "map_vertices": 1024,
    }


def manifest_row(run_id: str = "run-1", split: str = "train") -> dict:
    return {
        "schema_version": "phase3_teacher_manifest_v1",
        "run_id": run_id,
        "split": split,
        "primary_supervision": "online_residual",
        "warm_start_target": "ltm_normalized_edge_weight",
        "edge_label_schema_version": "phase3_edge_label_v1",
        "trace_schema_version": "phase3_pibt_trace_v1",
        "label_path": "artifacts/teacher/edge_labels/train/run-1.edge_labels.jsonl",
        "label_sha256": "a" * 64,
        "label_rows": 10,
        "method": "lacam_star_ltm",
        "map": "empty-32-32",
        "scen": "phase1a-generated-random/empty-32-32-random-1.scen",
        "agents": 100,
        "seed": 1,
        "time_limit_sec": 2,
        "objective": "sum_of_loss",
        "success": True,
        "feasible": True,
        "git_commit": "abc",
        "external_lacam2_commit": "def",
        "source_manifest": "configs/phase1a/manifest_plus_3000.jsonl",
    }


def test_phase3_edge_label_schema_validation() -> None:
    assert validate_edge_label(edge_label()) == []
    broken = edge_label()
    broken["traversal_cost"] = 9.0
    assert "traversal_cost must equal 1 + ltm_normalized_weight" in validate_edge_label(broken)


def test_phase3_manifest_schema_validation() -> None:
    assert validate_manifest_row(manifest_row()) == []
    broken = manifest_row()
    broken["primary_supervision"] = "pure_edge_regression"
    assert "primary_supervision must be online_residual" in validate_manifest_row(broken)


def test_phase3_map_holdout_split_has_no_overlap() -> None:
    assert validate_split_maps(DEFAULT_SPLIT_MAPS) == []
    assert split_for("empty-48-48") == "validation"
    assert split_for("maze-32-32-4") == "test"

    rows = [
        manifest_row("train-run", "train"),
        {
            **manifest_row("valid-run", "validation"),
            "map": "empty-48-48",
            "seed": 1,
        },
        {
            **manifest_row("test-run", "test"),
            "map": "maze-32-32-4",
            "seed": 1,
        },
    ]
    assert audit_no_leakage(rows) == []

    leaking = [manifest_row("run-a", "train"), {**manifest_row("run-b", "test"), "map": "empty-32-32"}]
    assert any("empty-32-32 leaks" in error for error in audit_no_leakage(leaking))


def test_phase3_run_id_is_stable_and_manifest_safe() -> None:
    first = run_id_for(
        map_name="empty-32-32",
        scen="phase1a-generated-random/empty-32-32-random-1.scen",
        agents=100,
        seed=1,
        time_limit_sec=2,
        source_manifest="configs/phase1a/manifest_plus_3000.jsonl",
    )
    second = run_id_for(
        map_name="empty-32-32",
        scen="phase1a-generated-random/empty-32-32-random-1.scen",
        agents=100,
        seed=1,
        time_limit_sec=2,
        source_manifest="configs\\phase1a\\manifest_plus_3000.jsonl",
    )
    assert first == second
    assert first.startswith("empty-32-32__a100__s1__")

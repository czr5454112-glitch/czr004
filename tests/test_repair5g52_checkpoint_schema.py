from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_repair5g52_checkpoint_replayability import main as analyze_main  # noqa: E402


def test_g52_checkpoint_replayability_schema_passes_for_minimal_row(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoints.jsonl"
    checkpoint.write_text(
        json.dumps(
            {
                "schema_version": "phase5p5_repair5g52_update_checkpoint_v1",
                "method": "repair5g52_runtime_always_static_exact",
                "map": "unit-map",
                "agents": 50,
                "seed": 146,
                "iteration": 0,
                "trace_event_count": 1,
                "trace_events": [{"kind": "committed", "agent_id": 0, "from_id": 1, "to_id": 2, "at_goal": False}],
                "traffic_before_hash": "abc",
                "traffic_before_edges": [{"from_id": 1, "to_id": 2, "c_raw": 1.0, "c_weight": 10.0, "f_raw": 0.0, "f_weight": 0.0}],
                "traffic_after_edges": [{"from_id": 1, "to_id": 2, "c_raw": 2.0, "c_weight": 10.0, "f_raw": 0.0, "f_weight": 0.0}],
                "feature_names": ["agents", "ltm_iterations"],
                "feature_values": [50.0, 0.0],
                "selected_candidate_params_hash": "hash",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rc = analyze_main(
        [
            "--checkpoint-jsonl",
            str(checkpoint),
            "--report",
            str(tmp_path / "report.md"),
            "--summary-json",
            str(tmp_path / "summary.json"),
            "--manifest-csv",
            str(tmp_path / "manifest.csv"),
        ]
    )

    assert rc == 0
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["gates"]["checkpoint_replayability_passed"]

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_repair5g56_perf_feature_allowlist import main as analyze_allowlist_main  # noqa: E402
from create_repair5g56_g6_perf_feature_table import main as create_feature_main  # noqa: E402


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_g56_perf_feature_allowlist_separates_cost_audit(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoints.jsonl"
    write_jsonl(
        checkpoint,
        [
            {
                "context_id": "random|a50|s146|it0|unit",
                "map": "random-32-32-20",
                "agents": 50,
                "seed": 146,
                "iteration": 0,
                "traffic_before_hash_full": "traffic",
                "trace_event_count": 8,
                "feature_names": [
                    "agents",
                    "ltm_iterations",
                    "committed_count",
                    "blocked_count",
                    "cost_min",
                    "cost_max",
                    "cost_span",
                    "cost_bounds_respected",
                ],
                "feature_values": [50, 0, 8, 2, 0, 10, 10, 1],
            }
        ],
    )
    rc = create_feature_main(
        [
            "--checkpoint-jsonl",
            str(checkpoint),
            "--feature-table-csv",
            str(tmp_path / "features.csv"),
            "--schema-json",
            str(tmp_path / "schema.json"),
            "--report",
            str(tmp_path / "feature.md"),
            "--summary-json",
            str(tmp_path / "feature.json"),
        ]
    )
    assert rc == 0
    rc = analyze_allowlist_main(
        [
            "--feature-table-csv",
            str(tmp_path / "features.csv"),
            "--schema-json",
            str(tmp_path / "schema.json"),
            "--report",
            str(tmp_path / "allowlist.md"),
            "--summary-json",
            str(tmp_path / "allowlist.json"),
        ]
    )
    assert rc == 0
    summary = json.loads((tmp_path / "allowlist.json").read_text(encoding="utf-8"))
    assert summary["gates"]["perf_feature_allowlist_passed"]
    assert "cost_span" not in summary["perf_safe_features"]
    assert "cost_span" in summary["audit_only_features"]

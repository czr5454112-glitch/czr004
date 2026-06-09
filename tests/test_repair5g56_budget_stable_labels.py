from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_repair5g56_counterfactual_label_completion import main as analyze_labels_main  # noqa: E402
from repair5g56_common import G56_BASE_CANDIDATES, validate_g55_instance_ids  # noqa: E402


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_g56_reserved_id_guard_rejects_166() -> None:
    with pytest.raises(SystemExit):
        validate_g55_instance_ids(["166"], label="unit")
    assert validate_g55_instance_ids(["146..148"], label="unit") == [146, 147, 148]


def test_g56_label_completion_passes_120_contexts_with_later_iterations(tmp_path: Path) -> None:
    probes: list[dict[str, object]] = []
    checkpoints: list[dict[str, object]] = []
    maps = ["random-32-32-20", "maze-32-32-4", "warehouse-10-20-10-2-1"]
    for map_name in maps:
        for agents in [50, 100]:
            for seed in range(146, 156):
                for iteration in [0, 1]:
                    context_id = f"{map_name}|a{agents}|s{seed}|it{iteration}|unit"
                    traffic_hash = f"traffic-{map_name}-{agents}-{seed}-{iteration}"
                    checkpoints.append(
                        {
                            "context_id": context_id,
                            "map": map_name,
                            "agents": agents,
                            "seed": seed,
                            "iteration": iteration,
                            "traffic_before_hash_full": traffic_hash,
                            "trace_event_count": 10,
                            "replayed_traffic_after_hash_match": True,
                            "replayed_update_stats_match": True,
                            "feature_names": ["agents", "ltm_iterations", "committed_count", "blocked_count"],
                            "feature_values": [agents, iteration, 10, 2],
                        }
                    )
                    for index, candidate in enumerate(G56_BASE_CANDIDATES):
                        score = 1.0 + index * 0.01
                        probes.append(
                            {
                                "context_id": context_id,
                                "map": map_name,
                                "agents": agents,
                                "seed": seed,
                                "iteration": iteration,
                                "candidate_id": candidate,
                                "resolved_candidate_id": candidate,
                                "short_budget_ms": 1000,
                                "probe_solution_found": True,
                                "probe_feasible": True,
                                "probe_sum_of_loss_ratio": score,
                                "traffic_before_hash_full": traffic_hash,
                                "trace_event_count": 10,
                                "forbidden_feature_audit_passed": True,
                            }
                        )
    probe_path = tmp_path / "probes.jsonl"
    checkpoint_path = tmp_path / "checkpoints.jsonl"
    write_jsonl(probe_path, probes)
    write_jsonl(checkpoint_path, checkpoints)
    rc = analyze_labels_main(
        [
            "--probe-jsonl",
            str(probe_path),
            "--checkpoint-jsonl",
            str(checkpoint_path),
            "--labels-csv",
            str(tmp_path / "labels.csv"),
            "--contexts-csv",
            str(tmp_path / "contexts.csv"),
            "--oracle-csv",
            str(tmp_path / "oracle.csv"),
            "--report",
            str(tmp_path / "report.md"),
            "--summary-json",
            str(tmp_path / "summary.json"),
        ]
    )
    assert rc == 0
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["context_count"] == 120
    assert summary["label_rows"] == 120 * len(G56_BASE_CANDIDATES)
    assert summary["gates"]["counterfactual_label_completion_passed"]
    assert summary["gates"]["later_iteration_context_count_gt_0"]

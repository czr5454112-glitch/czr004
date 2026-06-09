from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from create_repair5g56_g6_safe_mixture_targets import main as targets_main  # noqa: E402
from repair5g56_common import G56_BASE_CANDIDATES, G56_STATIC_CANDIDATE, normalized_context_key_text  # noqa: E402


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_g56_safe_mixture_targets_gate_training_ready(tmp_path: Path) -> None:
    labels: list[dict[str, object]] = []
    stable: list[dict[str, object]] = []
    for index in range(30):
        seed = 146 + (index % 10)
        row_base = {
            "context_id": f"random|a50|s{seed}|it{index}|unit",
            "map": "random-32-32-20",
            "agents": 50,
            "seed": seed,
            "iteration": index,
            "traffic_before_hash_full": f"traffic-{index}",
            "trace_event_count": 10,
        }
        stable.append({"normalized_context_key": normalized_context_key_text(row_base)})
        for candidate_index, candidate in enumerate(G56_BASE_CANDIDATES):
            score = 1.0 + candidate_index * 0.01
            if candidate == G56_STATIC_CANDIDATE:
                score = 1.0
            if candidate != G56_STATIC_CANDIDATE and index < 15 and candidate_index == 4:
                score = 0.90
            if candidate_index == len(G56_BASE_CANDIDATES) - 1:
                score = 1.10
            labels.append(
                {
                    **row_base,
                    "candidate_id": candidate,
                    "resolved_candidate_id": candidate,
                    "probe_solution_found": True,
                    "probe_feasible": True,
                    "probe_sum_of_loss_ratio": score,
                }
            )
    write_csv(tmp_path / "labels.csv", labels)
    write_csv(tmp_path / "stable.csv", stable)
    rc = targets_main(
        [
            "--labels-csv",
            str(tmp_path / "labels.csv"),
            "--stable-contexts-csv",
            str(tmp_path / "stable.csv"),
            "--targets-csv",
            str(tmp_path / "targets.csv"),
            "--report",
            str(tmp_path / "targets.md"),
            "--summary-json",
            str(tmp_path / "targets.json"),
        ]
    )
    assert rc == 0
    summary = json.loads((tmp_path / "targets.json").read_text(encoding="utf-8"))
    assert summary["gates"]["g6_targets_ready"]
    assert summary["training_eligible_contexts"] == 30
    assert summary["nonstatic_training_eligible_contexts"] > 0
    assert summary["static_fallback_contexts"] > 0

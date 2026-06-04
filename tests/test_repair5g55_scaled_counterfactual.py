from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_repair5g55_feature_leakage_and_availability import main as feature_audit_main  # noqa: E402
from analyze_repair5g55_probe_budget_stability import main as budget_main  # noqa: E402
from analyze_repair5g55_scaled_counterfactual_labels import main as labels_main  # noqa: E402
from create_repair5g55_g6_feature_table import main as feature_table_main  # noqa: E402
from repair5g55_common import G55_BASE_CANDIDATES, G55_CONTEXT_ALIAS, validate_g55_instance_ids  # noqa: E402


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_g55_reserved_id_guard_rejects_166() -> None:
    with pytest.raises(SystemExit):
        validate_g55_instance_ids(["166"])
    assert validate_g55_instance_ids(["146..148"]) == [146, 147, 148]


def _probe_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    maps = ["random-32-32-20", "maze-32-32-4", "warehouse-10-20-10-2-1"]
    agents_values = [50, 100]
    seed = 146
    for map_name in maps:
        for agents in agents_values:
            for offset in range(10):
                context_seed = seed + offset
                context_id = f"{map_name}|a{agents}|s{context_seed}|it0|{G55_CONTEXT_ALIAS}"
                for index, candidate in enumerate(G55_BASE_CANDIDATES):
                    score = 1.0 + index * 0.01
                    if candidate == "repair5g2_best_frozen_static_candidate":
                        score = 1.0
                    if candidate == "repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75" and offset % 2 == 0:
                        score = 0.95
                    rows.append(
                        {
                            "schema_version": "phase5p5_repair5g55_counterfactual_update_probe_v1",
                            "context_id": context_id,
                            "method": G55_CONTEXT_ALIAS,
                            "map": map_name,
                            "agents": agents,
                            "seed": context_seed,
                            "iteration": 0,
                            "candidate_id": candidate,
                            "resolved_candidate_id": candidate,
                            "candidate_recognized": True,
                            "updateparams_hash": f"hash-{index}",
                            "updateparams_fingerprint": f"fp-{index}",
                            "short_budget_ms": 1000,
                            "probe_solution_found": True,
                            "probe_feasible": True,
                            "probe_sum_of_loss": score * 100,
                            "probe_lower_bound": 100,
                            "probe_sum_of_loss_ratio": score,
                            "probe_runtime_ms": 10,
                            "probe_expanded_nodes": 1,
                            "probe_low_level_pibt_calls": 1,
                            "delta_vs_additive_in_same_context": score - 1.1,
                            "delta_vs_static_in_same_context": score - 1.0,
                            "is_best_candidate_in_context": score <= 0.95,
                            "oracle_gap_vs_static": -0.05 if offset % 2 == 0 else 0.0,
                            "traffic_before_hash_full": f"traffic-{map_name}-{agents}-{context_seed}",
                            "trace_event_count": 10 + offset,
                            "forbidden_feature_audit_passed": True,
                        }
                    )
    return rows


def _checkpoint_rows() -> list[dict[str, object]]:
    rows = []
    maps = ["random-32-32-20", "maze-32-32-4", "warehouse-10-20-10-2-1"]
    for map_name in maps:
        for agents in [50, 100]:
            for offset in range(10):
                seed = 146 + offset
                rows.append(
                    {
                        "schema_version": "phase5p5_repair5g55_update_checkpoint_v1",
                        "method": G55_CONTEXT_ALIAS,
                        "map": map_name,
                        "agents": agents,
                        "seed": seed,
                        "iteration": 0,
                        "trace_event_count": 10 + offset,
                        "traffic_before_hash_full": f"traffic-{map_name}-{agents}-{seed}",
                        "replayed_traffic_after_hash_match": True,
                        "replayed_update_stats_match": True,
                        "feature_names": [
                            "agents",
                            "ltm_iterations",
                            "returned_solutions_count_so_far",
                            "has_incumbent_before",
                            "best_ratio_before",
                            "committed_count",
                            "blocked_count",
                            "wait_event_count",
                            "progress_committed_count",
                            "nonprogress_committed_count",
                            "blocked_per_committed",
                            "wait_per_committed",
                            "blocked_per_agent",
                            "committed_per_agent",
                            "progress_ratio",
                            "c_update_count",
                            "f_update_count",
                            "cost_min",
                            "cost_max",
                            "cost_span",
                            "cost_bounds_respected",
                        ],
                        "feature_values": [
                            agents,
                            0,
                            1,
                            0,
                            0.0,
                            10,
                            2,
                            1,
                            8,
                            2,
                            0.2,
                            0.1,
                            2 / agents,
                            10 / agents,
                            0.8,
                            10,
                            8,
                            1,
                            11,
                            10,
                            1,
                        ],
                        "forbidden_feature_audit_passed": True,
                    }
                )
    return rows


def test_g55_label_and_feature_audits_pass_minimum_smoke(tmp_path: Path) -> None:
    probes = tmp_path / "probes.jsonl"
    checkpoints = tmp_path / "checkpoints.jsonl"
    write_jsonl(probes, _probe_rows())
    write_jsonl(checkpoints, _checkpoint_rows())
    rc = labels_main(
        [
            "--probe-jsonl",
            str(probes),
            "--checkpoint-jsonl",
            str(checkpoints),
            "--labels-csv",
            str(tmp_path / "labels.csv"),
            "--contexts-csv",
            str(tmp_path / "contexts.csv"),
            "--oracle-csv",
            str(tmp_path / "oracle.csv"),
            "--report",
            str(tmp_path / "labels.md"),
            "--summary-json",
            str(tmp_path / "labels.json"),
        ]
    )
    assert rc == 0
    summary = json.loads((tmp_path / "labels.json").read_text(encoding="utf-8"))
    assert summary["gates"]["scaled_counterfactual_label_smoke_passed"]
    assert summary["context_count"] == 60
    assert summary["label_rows"] == 60 * len(G55_BASE_CANDIDATES)

    rc = feature_table_main(
        [
            "--checkpoint-jsonl",
            str(checkpoints),
            "--feature-table-csv",
            str(tmp_path / "features.csv"),
            "--report",
            str(tmp_path / "features.md"),
            "--summary-json",
            str(tmp_path / "features.json"),
        ]
    )
    assert rc == 0
    rc = feature_audit_main(
        [
            "--feature-table-csv",
            str(tmp_path / "features.csv"),
            "--report",
            str(tmp_path / "feature_audit.md"),
            "--summary-json",
            str(tmp_path / "feature_audit.json"),
        ]
    )
    assert rc == 0
    audit = json.loads((tmp_path / "feature_audit.json").read_text(encoding="utf-8"))
    assert audit["gates"]["feature_audit_passed"]


def test_g55_budget_stability_marks_training_eligible_context(tmp_path: Path) -> None:
    rows = []
    for budget in [250, 500, 1000]:
        for candidate in G55_BASE_CANDIDATES:
            score = 1.0 if candidate == "repair5g2_best_frozen_static_candidate" else 1.1
            if candidate == "repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75":
                score = 0.9
            rows.append(
                {
                    "context_id": f"unit|a50|s146|it0|budget{budget}",
                    "map": "random-32-32-20",
                    "agents": 50,
                    "seed": 146,
                    "iteration": 0,
                    "traffic_before_hash_full": "same",
                    "short_budget_ms": budget,
                    "candidate_id": candidate,
                    "probe_solution_found": True,
                    "probe_feasible": True,
                    "probe_sum_of_loss_ratio": score,
                }
            )
    probes = tmp_path / "budget.jsonl"
    write_jsonl(probes, rows)
    rc = budget_main(
        [
            "--probe-jsonl",
            str(probes),
            "--rank-stability-csv",
            str(tmp_path / "budget.csv"),
            "--report",
            str(tmp_path / "budget.md"),
            "--summary-json",
            str(tmp_path / "budget_summary.json"),
        ]
    )
    assert rc == 0
    summary = json.loads((tmp_path / "budget_summary.json").read_text(encoding="utf-8"))
    assert summary["probe_budget_stability_measured"]
    assert summary["training_eligible_stable_contexts"] == 1

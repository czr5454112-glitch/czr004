from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_repair5g54_checkpoint_replayability import main as checkpoint_main  # noqa: E402
from analyze_repair5g54_counterfactual_labels import main as labels_main  # noqa: E402
from repair5g54_common import G54_CANDIDATES, parse_instance_id_tokens, validate_observed_instance_ids  # noqa: E402
from write_repair5g54_semantic_vs_budget_gate_policy import main as policy_main  # noqa: E402


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_g54_reserved_id_guard_rejects_166_and_ranges() -> None:
    with pytest.raises(SystemExit):
        validate_observed_instance_ids([166])
    with pytest.raises(SystemExit):
        validate_observed_instance_ids(parse_instance_id_tokens(["156..166"]))
    assert validate_observed_instance_ids(parse_instance_id_tokens(["146-148"])) == [146, 147, 148]


def test_g54_semantic_vs_budget_policy_allows_diagnostic_labels(tmp_path: Path) -> None:
    transform = tmp_path / "transform.json"
    hook = tmp_path / "hook.json"
    decision = tmp_path / "decision.json"
    write_json(
        transform,
        {
            "gates": {
                "update_transform_equivalence_passed": True,
                "params_hash_mismatch_count": 0,
                "traffic_after_hash_mismatch_count": 0,
                "cf_update_stat_mismatch_count": 0,
            }
        },
    )
    write_json(
        hook,
        {
            "gates": {
                "minimal_hook_static_matches_static": False,
                "minimal_hook_map_agent_matches_map_agent": False,
                "minimal_hook_failure_class": "minimal_hook_time_budget_sensitivity",
                "true_semantic_mismatch_count": 0,
            }
        },
    )
    write_json(
        decision,
        {
            "targeted_warehouse_100_5s": "passed",
            "targeted_warehouse_100_10s": "passed",
            "failure_class": "minimal_hook_time_budget_sensitivity",
        },
    )
    rc = policy_main(
        [
            "--transform-summary-json",
            str(transform),
            "--hook-summary-json",
            str(hook),
            "--g53-decision-summary-json",
            str(decision),
            "--report",
            str(tmp_path / "policy.md"),
            "--summary-json",
            str(tmp_path / "policy.json"),
        ]
    )
    assert rc == 0
    summary = json.loads((tmp_path / "policy.json").read_text(encoding="utf-8"))
    assert summary["checkpoint_labels"] == "diagnostic_reopened_observed_only"
    assert summary["gates"]["semantic_vs_budget_policy_passed"]


def test_g54_checkpoint_replayability_schema_passes_minimal_row(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoints.jsonl"
    checkpoint.write_text(
        json.dumps(
            {
                "schema_version": "phase5p5_repair5g54_update_checkpoint_v1",
                "method": "repair5g54_checkpoint_static_context",
                "map": "unit-map",
                "agents": 100,
                "seed": 146,
                "iteration": 0,
                "trace_event_count": 1,
                "trace_events": [{"kind": "committed", "agent_id": 0, "from_id": 1, "to_id": 2, "at_goal": False}],
                "traffic_before_hash_full": "before",
                "traffic_after_hash_full": "after",
                "replayed_traffic_after_hash_full": "after",
                "replayed_traffic_after_hash_match": True,
                "replayed_update_stats_match": True,
                "traffic_before_full_sparse_edges": [{"from_id": 1, "to_id": 2, "c_raw": 1.0, "c_normalized": 1.0, "f_raw": 0.0, "f_normalized": 0.0}],
                "traffic_after_full_sparse_edges": [{"from_id": 1, "to_id": 2, "c_raw": 2.0, "c_normalized": 1.0, "f_raw": 0.0, "f_normalized": 0.0}],
                "selected_candidate_params_hash": "hash",
                "forbidden_feature_audit_passed": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    rc = checkpoint_main(
        [
            "--checkpoint-jsonl",
            str(checkpoint),
            "--report",
            str(tmp_path / "checkpoint.md"),
            "--summary-json",
            str(tmp_path / "checkpoint.json"),
            "--manifest-csv",
            str(tmp_path / "manifest.csv"),
        ]
    )
    assert rc == 0
    summary = json.loads((tmp_path / "checkpoint.json").read_text(encoding="utf-8"))
    assert summary["gates"]["checkpoint_replayability_passed"]


def test_g54_counterfactual_label_schema_and_candidate_coverage(tmp_path: Path) -> None:
    probes = tmp_path / "probes.jsonl"
    lines = []
    for index, candidate in enumerate(G54_CANDIDATES):
        lines.append(
            json.dumps(
                {
                    "schema_version": "phase5p5_repair5g54_counterfactual_update_probe_v1",
                    "context_id": "unit|a100|s146|it0|static",
                    "map": "unit-map",
                    "agents": 100,
                    "seed": 146,
                    "iteration": 0,
                    "candidate_id": candidate,
                    "resolved_candidate_id": candidate,
                    "updateparams_hash": f"hash-{index}",
                    "updateparams_fingerprint": f"fp-{index}",
                    "probe_solution_found": True,
                    "probe_feasible": True,
                    "probe_sum_of_loss": 100 + index,
                    "probe_lower_bound": 100,
                    "probe_sum_of_loss_ratio": 1.0 + index * 0.01,
                    "probe_runtime_ms": 1.0,
                    "probe_expanded_nodes": 1,
                    "probe_low_level_pibt_calls": 1,
                    "delta_vs_additive_in_same_context": index * 0.01,
                    "delta_vs_static_in_same_context": 0.0 if candidate == "repair5g2_best_frozen_static_candidate" else index * 0.01,
                    "is_best_candidate_in_context": candidate == "additive_ltm",
                    "oracle_gap_vs_static": -0.01,
                    "traffic_before_hash_full": "before",
                    "trace_event_count": 1,
                    "forbidden_feature_audit_passed": True,
                }
            )
        )
    probes.write_text("\n".join(lines) + "\n", encoding="utf-8")
    replay = tmp_path / "replay.json"
    write_json(replay, {"gates": {"checkpoint_replayability_passed": True}})
    rc = labels_main(
        [
            "--probe-jsonl",
            str(probes),
            "--replayability-summary-json",
            str(replay),
            "--labels-csv",
            str(tmp_path / "labels.csv"),
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
    assert summary["gates"]["candidate_coverage_complete"]
    assert summary["gates"]["counterfactual_labels_passed"]

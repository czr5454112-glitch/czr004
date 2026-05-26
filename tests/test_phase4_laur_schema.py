from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.update_sequences import (  # noqa: E402
    audit_checkpoint_trace_join,
    audit_probe_labels,
    build_best_rule_labels,
    validate_checkpoint_row,
    validate_probe_row,
    validate_trace_event_row,
)


def checkpoint_row(checkpoint_id: str = "run-1__iter0", split: str = "train") -> dict:
    return {
        "schema_version": "phase4_laur_checkpoint_v1",
        "run_id": "run-1",
        "checkpoint_id": checkpoint_id,
        "split": split,
        "map_name": "random-32-32-10",
        "map_path": "external/lacam2/assets/random-32-32-10.map",
        "scen_path": "external/lacam2/assets/random-32-32-10-random-1.scen",
        "agents": 50,
        "seed": 1,
        "time_limit_sec": 3,
        "max_iterations": 4,
        "iteration": 0,
        "node_budget": 0,
        "sum_of_loss_this_iteration": None,
        "lower_bound_sol": 100,
        "sum_of_loss_ratio_this_iteration": None,
        "expanded_nodes_this_iteration": 10,
        "high_level_expansions_this_iteration": 10,
        "low_level_pibt_calls_this_iteration": 20,
        "trace_event_count": 3,
        "committed_count": 2,
        "blocked_count": 1,
        "wait_event_count": 1,
        "goal_wait_ignored_count": 1,
        "traffic_before_nonzero_edges": 0,
        "traffic_after_nonzero_edges": 1,
        "traffic_before_max_raw": 0,
        "traffic_after_max_raw": 2,
        "traffic_after_max_normalized": 10,
        "raw_before_topk": [],
        "raw_after_topk": [{"from_id": 1, "to_id": 2, "raw": 2}],
        "normalized_after_topk": [{"from_id": 1, "to_id": 2, "weight": 10}],
        "trace_path": "artifacts/teacher/laur/traces/run-1.jsonl",
        "traffic_snapshot_path": "artifacts/teacher/laur/checkpoints/run-1__iter0.json",
        "branch": "phase4-laur-ltm",
        "commit": "abc1234",
        "dirty": "tracked-dirty",
    }


def trace_rows(checkpoint_id: str = "run-1__iter0") -> list[dict]:
    base = {
        "schema_version": "phase4_laur_trace_event_v1",
        "run_id": "run-1",
        "checkpoint_id": checkpoint_id,
        "iteration": 0,
        "agent_id": 0,
        "map_name": "random-32-32-10",
        "agents": 50,
        "seed": 1,
        "propagated_to_id": None,
    }
    return [
        {
            **base,
            "event_index": 0,
            "kind": "committed",
            "from_id": 1,
            "to_id": 2,
            "at_goal": False,
            "is_wait": False,
            "propagation_kind": "none",
        },
        {
            **base,
            "event_index": 1,
            "kind": "blocked",
            "from_id": 2,
            "to_id": 2,
            "at_goal": False,
            "is_wait": True,
            "propagation_kind": "wait_propagated",
        },
        {
            **base,
            "event_index": 2,
            "kind": "committed",
            "from_id": 3,
            "to_id": 3,
            "at_goal": True,
            "is_wait": True,
            "propagation_kind": "goal_wait_ignored",
        },
    ]


def probe_row(
    checkpoint_id: str = "run-1__iter0",
    rule_id: str = "additive_ltm",
    ratio: float | None = 2.0,
    delta: float = 0.0,
    harmful: bool = False,
) -> dict:
    solved = ratio is not None
    return {
        "schema_version": "phase4_laur_update_label_v1",
        "run_id": "run-1",
        "checkpoint_id": checkpoint_id,
        "probe_id": f"{checkpoint_id}__rule_{rule_id}",
        "split": "train",
        "map_name": "random-32-32-10",
        "agents": 50,
        "seed": 1,
        "iteration": 0,
        "rule_id": rule_id,
        "rule_params": {
            "alpha_commit": 1.0,
            "alpha_block": 1.0,
            "alpha_wait": 1.0,
            "rho_decay": 1.0,
            "saturation_scale": 1.0,
            "contraflow_penalty": 0.0,
        },
        "probe_short_budget_sec": 1.0,
        "solution_found": solved,
        "feasible": solved,
        "sum_of_loss": 200 if solved else None,
        "lower_bound_sol": 100,
        "sum_of_loss_ratio": ratio,
        "time_to_first_solution_ms": None,
        "returned_solutions_count": 1 if solved else 0,
        "expanded_nodes": 10,
        "high_level_expansions": 10,
        "low_level_pibt_calls": 20,
        "runtime_ms": 5.0,
        "additive_solution_found": True,
        "additive_sum_of_loss": 200,
        "additive_sum_of_loss_ratio": 2.0,
        "delta_ratio_vs_additive": delta,
        "beats_additive": delta > 0,
        "harmful": harmful,
        "base_solution_found_this_iteration": True,
        "base_sum_of_loss_ratio_this_iteration": 2.0,
        "trace_event_count": 3,
        "branch": "phase4-laur-ltm",
        "commit": "abc1234",
        "dirty": "clean",
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def test_phase4_laur_checkpoint_and_trace_schema_validation() -> None:
    assert validate_checkpoint_row(checkpoint_row()) == []
    for row in trace_rows():
        assert validate_trace_event_row(row) == []

    broken_checkpoint = checkpoint_row()
    broken_checkpoint["traffic_after_max_normalized"] = 11
    assert "traffic_after_max_normalized must be within [0, 10]" in validate_checkpoint_row(broken_checkpoint)

    broken_trace = trace_rows()[0]
    broken_trace["is_wait"] = True
    assert "is_wait must equal from_id == to_id" in validate_trace_event_row(broken_trace)


def test_phase4_laur_checkpoint_trace_join_audit(tmp_path: Path) -> None:
    checkpoint_path = tmp_path / "checkpoints.jsonl"
    trace_path = tmp_path / "trace.jsonl"
    write_jsonl(checkpoint_path, [checkpoint_row()])
    write_jsonl(trace_path, trace_rows())

    audit = audit_checkpoint_trace_join(checkpoint_path, trace_path)
    assert audit["passed"] is True
    assert audit["checkpoint_rows"] == 1
    assert audit["trace_rows"] == 3

    mismatched = checkpoint_row()
    mismatched["trace_event_count"] = 2
    write_jsonl(checkpoint_path, [mismatched])
    audit = audit_checkpoint_trace_join(checkpoint_path, trace_path)
    assert audit["passed"] is False
    assert any("trace_event_count=2" in error for error in audit["join_errors"])


def test_phase4_laur_split_audit_uses_map_holdout_helper(tmp_path: Path) -> None:
    checkpoint_path = tmp_path / "checkpoints.jsonl"
    trace_path = tmp_path / "trace.jsonl"
    first = checkpoint_row("run-1__iter0", "train")
    second = {**checkpoint_row("run-2__iter0", "test"), "run_id": "run-2"}
    write_jsonl(checkpoint_path, [first, second])
    write_jsonl(trace_path, trace_rows("run-1__iter0"))

    audit = audit_checkpoint_trace_join(checkpoint_path, trace_path)
    assert audit["passed"] is False
    assert any("random-32-32-10 leaks" in error for error in audit["split_errors"])


def test_phase4_laur_probe_schema_and_best_rule_labels(tmp_path: Path) -> None:
    rows = [
        probe_row(),
        probe_row(rule_id="commit_heavy", ratio=1.8, delta=0.2),
        probe_row(rule_id="block_heavy", ratio=2.1, delta=-0.1, harmful=True),
        probe_row(rule_id="wait_light", ratio=2.0, delta=0.0),
    ]
    for row in rows:
        assert validate_probe_row(row) == []

    labels = build_best_rule_labels(rows, min_delta_ratio=0.005)
    assert labels[0]["label_rule_id"] == "commit_heavy"
    assert labels[0]["best_delta_ratio_vs_additive"] == 0.2
    assert labels[0]["harmful_rule_ids"] == ["block_heavy"]

    path = tmp_path / "probe.jsonl"
    write_jsonl(path, rows)
    audit = audit_probe_labels(path)
    assert audit["passed"] is True
    assert audit["probe_rows"] == 4
    assert audit["label_distribution"] == {"commit_heavy": 1}

    broken = probe_row(rule_id="additive_ltm", delta=0.1)
    assert "additive_ltm delta_ratio_vs_additive must be zero" in validate_probe_row(broken)

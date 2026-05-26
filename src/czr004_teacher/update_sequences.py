"""Phase4C LAU checkpoint/trace schema validation and join audits."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any


if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.splits import audit_no_leakage  # noqa: E402


CHECKPOINT_SCHEMA_VERSION = "phase4_laur_checkpoint_v1"
TRACE_EVENT_SCHEMA_VERSION = "phase4_laur_trace_event_v1"
VALID_SPLITS = {"train", "validation", "test"}
VALID_TRACE_KINDS = {"committed", "blocked"}
VALID_PROPAGATION_KINDS = {"none", "wait_propagated", "goal_wait_ignored"}

CHECKPOINT_REQUIRED_TYPES: dict[str, type | tuple[type, ...]] = {
    "schema_version": str,
    "run_id": str,
    "checkpoint_id": str,
    "split": str,
    "map_name": str,
    "agents": int,
    "seed": int,
    "time_limit_sec": (int, float),
    "iteration": int,
    "node_budget": int,
    "lower_bound_sol": int,
    "trace_event_count": int,
    "committed_count": int,
    "blocked_count": int,
    "wait_event_count": int,
    "goal_wait_ignored_count": int,
    "traffic_before_nonzero_edges": int,
    "traffic_after_nonzero_edges": int,
    "traffic_before_max_raw": (int, float),
    "traffic_after_max_raw": (int, float),
    "traffic_after_max_normalized": (int, float),
    "raw_before_topk": list,
    "raw_after_topk": list,
    "normalized_after_topk": list,
    "trace_path": str,
    "traffic_snapshot_path": str,
    "branch": str,
    "commit": str,
    "dirty": str,
}

CHECKPOINT_NULLABLE_TYPES: dict[str, type | tuple[type, ...]] = {
    "sum_of_loss_this_iteration": int,
    "sum_of_loss_ratio_this_iteration": (int, float),
    "expanded_nodes_this_iteration": int,
    "high_level_expansions_this_iteration": int,
    "low_level_pibt_calls_this_iteration": int,
}

TRACE_REQUIRED_TYPES: dict[str, type | tuple[type, ...]] = {
    "schema_version": str,
    "run_id": str,
    "checkpoint_id": str,
    "iteration": int,
    "event_index": int,
    "kind": str,
    "agent_id": int,
    "from_id": int,
    "to_id": int,
    "at_goal": bool,
    "is_wait": bool,
    "propagation_kind": str,
    "map_name": str,
    "agents": int,
    "seed": int,
}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _type_errors(row: dict, required: dict[str, type | tuple[type, ...]]) -> list[str]:
    errors: list[str] = []
    for key, expected in required.items():
        if key not in row:
            errors.append(f"missing {key}")
            continue
        if not isinstance(row[key], expected):
            errors.append(f"{key} has type {type(row[key]).__name__}, expected {expected}")
    return errors


def _nullable_type_errors(row: dict, required: dict[str, type | tuple[type, ...]]) -> list[str]:
    errors: list[str] = []
    for key, expected in required.items():
        if key not in row:
            errors.append(f"missing {key}")
            continue
        if row[key] is not None and not isinstance(row[key], expected):
            errors.append(f"{key} has type {type(row[key]).__name__}, expected {expected} or None")
    return errors


def _finite_number(row: dict, key: str, errors: list[str], *, nullable: bool = False) -> None:
    value = row.get(key)
    if nullable and value is None:
        return
    if not _is_number(value) or not math.isfinite(float(value)):
        errors.append(f"{key} must be a finite number")


def _nonnegative_int(row: dict, key: str, errors: list[str], *, nullable: bool = False) -> None:
    value = row.get(key)
    if nullable and value is None:
        return
    if not _is_int(value) or int(value) < 0:
        errors.append(f"{key} must be a nonnegative integer")


def _check_weight(value: Any, label: str, errors: list[str]) -> None:
    if not _is_number(value) or not math.isfinite(float(value)):
        errors.append(f"{label} must be a finite number")
        return
    if float(value) < 0.0 or float(value) > 10.0:
        errors.append(f"{label} must be within [0, 10]")


def _validate_raw_topk(row: dict, key: str, errors: list[str]) -> None:
    value = row.get(key)
    if not isinstance(value, list):
        return
    for index, edge in enumerate(value):
        label = f"{key}[{index}]"
        if not isinstance(edge, dict):
            errors.append(f"{label} must be an object")
            continue
        for edge_key in ("from_id", "to_id"):
            if not _is_int(edge.get(edge_key)) or int(edge[edge_key]) < 0:
                errors.append(f"{label}.{edge_key} must be a nonnegative integer")
        if not _is_number(edge.get("raw")) or not math.isfinite(float(edge["raw"])):
            errors.append(f"{label}.raw must be a finite number")
        elif float(edge["raw"]) < 0.0:
            errors.append(f"{label}.raw must be nonnegative")
        if "weight" in edge:
            _check_weight(edge["weight"], f"{label}.weight", errors)


def _validate_normalized_topk(row: dict, key: str, errors: list[str]) -> None:
    value = row.get(key)
    if not isinstance(value, list):
        return
    for index, edge in enumerate(value):
        label = f"{key}[{index}]"
        if not isinstance(edge, dict):
            errors.append(f"{label} must be an object")
            continue
        for edge_key in ("from_id", "to_id"):
            if not _is_int(edge.get(edge_key)) or int(edge[edge_key]) < 0:
                errors.append(f"{label}.{edge_key} must be a nonnegative integer")
        _check_weight(edge.get("weight"), f"{label}.weight", errors)


def validate_checkpoint_row(row: dict) -> list[str]:
    """Return schema errors for one Phase4C checkpoint row."""

    errors = _type_errors(row, CHECKPOINT_REQUIRED_TYPES)
    errors.extend(_nullable_type_errors(row, CHECKPOINT_NULLABLE_TYPES))
    if errors:
        return errors

    if row["schema_version"] != CHECKPOINT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {CHECKPOINT_SCHEMA_VERSION}")
    if row["split"] not in VALID_SPLITS:
        errors.append("split must be train, validation, or test")

    for key in (
        "agents",
        "seed",
        "iteration",
        "node_budget",
        "lower_bound_sol",
        "trace_event_count",
        "committed_count",
        "blocked_count",
        "wait_event_count",
        "goal_wait_ignored_count",
        "traffic_before_nonzero_edges",
        "traffic_after_nonzero_edges",
    ):
        _nonnegative_int(row, key, errors)
    for key in (
        "expanded_nodes_this_iteration",
        "high_level_expansions_this_iteration",
        "low_level_pibt_calls_this_iteration",
    ):
        _nonnegative_int(row, key, errors, nullable=True)

    for key in (
        "time_limit_sec",
        "traffic_before_max_raw",
        "traffic_after_max_raw",
        "traffic_after_max_normalized",
    ):
        _finite_number(row, key, errors)
    _finite_number(row, "sum_of_loss_ratio_this_iteration", errors, nullable=True)
    _check_weight(row["traffic_after_max_normalized"], "traffic_after_max_normalized", errors)

    if row["sum_of_loss_this_iteration"] is not None and int(row["sum_of_loss_this_iteration"]) < 0:
        errors.append("sum_of_loss_this_iteration must be nonnegative or null")
    if int(row["committed_count"]) + int(row["blocked_count"]) != int(row["trace_event_count"]):
        errors.append("committed_count + blocked_count must equal trace_event_count")
    if int(row["wait_event_count"]) + int(row["goal_wait_ignored_count"]) > int(row["trace_event_count"]):
        errors.append("wait_event_count + goal_wait_ignored_count must be <= trace_event_count")

    _validate_raw_topk(row, "raw_before_topk", errors)
    _validate_raw_topk(row, "raw_after_topk", errors)
    _validate_normalized_topk(row, "normalized_after_topk", errors)
    return errors


def validate_trace_event_row(row: dict) -> list[str]:
    """Return schema errors for one Phase4C raw trace event row."""

    errors = _type_errors(row, TRACE_REQUIRED_TYPES)
    if "propagated_to_id" not in row:
        errors.append("missing propagated_to_id")
    elif row["propagated_to_id"] is not None and not _is_int(row["propagated_to_id"]):
        errors.append("propagated_to_id must be an integer or null")
    if errors:
        return errors

    if row["schema_version"] != TRACE_EVENT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {TRACE_EVENT_SCHEMA_VERSION}")
    if row["kind"] not in VALID_TRACE_KINDS:
        errors.append("kind must be committed or blocked")
    if row["propagation_kind"] not in VALID_PROPAGATION_KINDS:
        errors.append("propagation_kind is invalid")

    for key in ("iteration", "event_index", "agent_id", "from_id", "to_id", "agents", "seed"):
        _nonnegative_int(row, key, errors)
    if row["propagated_to_id"] is not None and int(row["propagated_to_id"]) < 0:
        errors.append("propagated_to_id must be nonnegative or null")

    expected_wait = int(row["from_id"]) == int(row["to_id"])
    if bool(row["is_wait"]) != expected_wait:
        errors.append("is_wait must equal from_id == to_id")

    if expected_wait and bool(row["at_goal"]) and row["propagation_kind"] != "goal_wait_ignored":
        errors.append("goal wait rows must use propagation_kind=goal_wait_ignored")
    if expected_wait and not bool(row["at_goal"]) and row["propagation_kind"] != "wait_propagated":
        errors.append("non-goal wait rows must use propagation_kind=wait_propagated")
    if not expected_wait and row["propagation_kind"] != "none":
        errors.append("non-wait rows must use propagation_kind=none")
    return errors


def read_checkpoint_jsonl(path: str | Path) -> Iterator[dict]:
    yield from _read_jsonl(Path(path))


def read_trace_jsonl(path: str | Path) -> Iterator[dict]:
    yield from _read_jsonl(Path(path))


def _read_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: JSONL row must be an object")
            yield row


def build_checkpoint_features(checkpoint_row: dict, trace_rows: Iterable[dict]) -> dict:
    """Build a compact aggregate feature row from one checkpoint and its trace rows."""

    rows = list(trace_rows)
    committed = sum(1 for row in rows if row.get("kind") == "committed")
    blocked = sum(1 for row in rows if row.get("kind") == "blocked")
    wait = sum(1 for row in rows if row.get("is_wait") and not row.get("at_goal"))
    goal_wait = sum(1 for row in rows if row.get("is_wait") and row.get("at_goal"))
    denom = max(1, committed + blocked)
    return {
        "schema_version": "phase4_laur_checkpoint_features_v1",
        "run_id": checkpoint_row["run_id"],
        "checkpoint_id": checkpoint_row["checkpoint_id"],
        "iteration": checkpoint_row["iteration"],
        "agents": checkpoint_row["agents"],
        "committed_count": committed,
        "blocked_count": blocked,
        "wait_event_count": wait,
        "goal_wait_ignored_count": goal_wait,
        "blocked_ratio": blocked / denom,
        "wait_ratio": wait / denom,
        "traffic_after_nonzero_edges": checkpoint_row["traffic_after_nonzero_edges"],
        "traffic_after_max_raw": checkpoint_row["traffic_after_max_raw"],
        "traffic_after_max_normalized": checkpoint_row["traffic_after_max_normalized"],
    }


def audit_checkpoint_trace_join(checkpoint_jsonl: str | Path, trace_jsonl: str | Path) -> dict:
    """Validate Phase4C checkpoint/trace JSONL files and their join invariants."""

    checkpoint_path = Path(checkpoint_jsonl)
    trace_path = Path(trace_jsonl)
    checkpoints = list(read_checkpoint_jsonl(checkpoint_path))
    traces = list(read_trace_jsonl(trace_path))

    checkpoint_schema_errors: list[str] = []
    trace_schema_errors: list[str] = []
    join_errors: list[str] = []

    for index, row in enumerate(checkpoints, 1):
        checkpoint_schema_errors.extend(f"checkpoint row {index}: {error}" for error in validate_checkpoint_row(row))
    for index, row in enumerate(traces, 1):
        trace_schema_errors.extend(f"trace row {index}: {error}" for error in validate_trace_event_row(row))

    checkpoints_by_id = {row.get("checkpoint_id"): row for row in checkpoints}
    grouped_traces: dict[str, list[dict]] = defaultdict(list)
    for row in traces:
        checkpoint_id = str(row.get("checkpoint_id"))
        grouped_traces[checkpoint_id].append(row)
        if checkpoint_id not in checkpoints_by_id:
            join_errors.append(f"trace row references unknown checkpoint_id {checkpoint_id}")

    for checkpoint_id, checkpoint in checkpoints_by_id.items():
        rows = grouped_traces.get(str(checkpoint_id), [])
        committed = sum(1 for row in rows if row.get("kind") == "committed")
        blocked = sum(1 for row in rows if row.get("kind") == "blocked")
        wait = sum(1 for row in rows if row.get("is_wait") and not row.get("at_goal"))
        goal_wait = sum(1 for row in rows if row.get("is_wait") and row.get("at_goal"))

        expected_count = int(checkpoint["trace_event_count"])
        if len(rows) != expected_count:
            join_errors.append(
                f"{checkpoint_id}: trace_event_count={expected_count} but grouped trace rows={len(rows)}"
            )
        for key, actual in (
            ("committed_count", committed),
            ("blocked_count", blocked),
            ("wait_event_count", wait),
            ("goal_wait_ignored_count", goal_wait),
        ):
            if int(checkpoint[key]) != actual:
                join_errors.append(f"{checkpoint_id}: {key}={checkpoint[key]} but trace rows imply {actual}")

        for row in rows:
            for key in ("run_id", "iteration", "map_name", "agents", "seed"):
                if row.get(key) != checkpoint.get(key):
                    join_errors.append(f"{checkpoint_id}: trace {key}={row.get(key)!r} does not match checkpoint")

        event_indexes = [int(row["event_index"]) for row in rows if _is_int(row.get("event_index"))]
        if event_indexes != list(range(len(event_indexes))):
            join_errors.append(f"{checkpoint_id}: event_index is not contiguous from 0")

    split_rows = [
        {
            "split": row["split"],
            "map": row["map_name"],
            "seed": row["seed"],
            "run_id": row["run_id"],
        }
        for row in checkpoints
        if all(key in row for key in ("split", "map_name", "seed", "run_id"))
    ]
    split_errors = audit_no_leakage(split_rows) if split_rows else ["no checkpoint rows available for split audit"]

    result = {
        "checkpoint_jsonl": str(checkpoint_path),
        "trace_jsonl": str(trace_path),
        "checkpoint_rows": len(checkpoints),
        "trace_rows": len(traces),
        "checkpoint_schema_errors": checkpoint_schema_errors,
        "trace_schema_errors": trace_schema_errors,
        "join_errors": join_errors,
        "split_errors": split_errors,
        "checkpoint_schema_error_count": len(checkpoint_schema_errors),
        "trace_schema_error_count": len(trace_schema_errors),
        "join_error_count": len(join_errors),
        "split_error_count": len(split_errors),
    }
    result["passed"] = not (
        checkpoint_schema_errors or trace_schema_errors or join_errors or split_errors
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint-jsonl", type=Path, required=True)
    parser.add_argument("--trace-jsonl", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path)
    args = parser.parse_args(argv)

    summary = audit_checkpoint_trace_join(args.checkpoint_jsonl, args.trace_jsonl)
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

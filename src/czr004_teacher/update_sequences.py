"""Phase4C LAU checkpoint/trace schema validation and join audits."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any


if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.splits import audit_no_leakage  # noqa: E402
from czr004_teacher.features_laur import (  # noqa: E402
    FEATURE_NAMES,
    FEATURE_SET,
    build_aggregate_checkpoint_features,
    feature_vector,
    topology_for_checkpoint,
)


CHECKPOINT_SCHEMA_VERSION = "phase4_laur_checkpoint_v1"
TRACE_EVENT_SCHEMA_VERSION = "phase4_laur_trace_event_v1"
UPDATE_LABEL_SCHEMA_VERSION = "phase4_laur_update_label_v1"
BEST_RULE_LABEL_SCHEMA_VERSION = "phase4_laur_best_rule_label_v1"
UPDATE_DATASET_SCHEMA_VERSION = "phase4_laur_update_dataset_v1"
VALID_SPLITS = {"train", "validation", "test"}
VALID_TRACE_KINDS = {"committed", "blocked"}
VALID_PROPAGATION_KINDS = {"none", "wait_propagated", "goal_wait_ignored"}
VALID_RULE_IDS = {
    "additive_ltm",
    "commit_heavy",
    "block_heavy",
    "block_light",
    "wait_light",
    "wait_heavy",
    "decay_095",
    "decay_090",
}

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

PROBE_REQUIRED_TYPES: dict[str, type | tuple[type, ...]] = {
    "schema_version": str,
    "run_id": str,
    "checkpoint_id": str,
    "probe_id": str,
    "split": str,
    "map_name": str,
    "agents": int,
    "seed": int,
    "iteration": int,
    "rule_id": str,
    "rule_params": dict,
    "probe_short_budget_sec": (int, float),
    "solution_found": bool,
    "feasible": bool,
    "lower_bound_sol": int,
    "returned_solutions_count": int,
    "expanded_nodes": int,
    "high_level_expansions": int,
    "low_level_pibt_calls": int,
    "runtime_ms": (int, float),
    "additive_solution_found": bool,
    "delta_ratio_vs_additive": (int, float),
    "beats_additive": bool,
    "harmful": bool,
    "base_solution_found_this_iteration": bool,
    "trace_event_count": int,
    "branch": str,
    "commit": str,
    "dirty": str,
}

PROBE_NULLABLE_TYPES: dict[str, type | tuple[type, ...]] = {
    "sum_of_loss": int,
    "sum_of_loss_ratio": (int, float),
    "time_to_first_solution_ms": (int, float),
    "additive_sum_of_loss": int,
    "additive_sum_of_loss_ratio": (int, float),
    "base_sum_of_loss_ratio_this_iteration": (int, float),
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
    for key in ("blocked_unique_edge_count", "topk_blocked_edge_count"):
        if key in row:
            _nonnegative_int(row, key, errors)
    for key in ("topk_blocked_edge_concentration", "blocked_edge_entropy"):
        if key in row:
            _finite_number(row, key, errors)
    if "topk_blocked_edge_concentration" in row:
        value = row.get("topk_blocked_edge_concentration")
        if _is_number(value) and not (0.0 <= float(value) <= 1.0):
            errors.append("topk_blocked_edge_concentration must be within [0, 1]")

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


def validate_probe_row(row: dict) -> list[str]:
    """Return schema errors for one Phase4D update-rule probe row."""

    errors = _type_errors(row, PROBE_REQUIRED_TYPES)
    errors.extend(_nullable_type_errors(row, PROBE_NULLABLE_TYPES))
    if errors:
        return errors

    if row["schema_version"] != UPDATE_LABEL_SCHEMA_VERSION:
        errors.append(f"schema_version must be {UPDATE_LABEL_SCHEMA_VERSION}")
    if row["split"] not in VALID_SPLITS:
        errors.append("split must be train, validation, or test")
    if row["rule_id"] not in VALID_RULE_IDS:
        errors.append("rule_id is not in the configured Phase4D rule set")

    for key in (
        "agents",
        "seed",
        "iteration",
        "lower_bound_sol",
        "returned_solutions_count",
        "expanded_nodes",
        "high_level_expansions",
        "low_level_pibt_calls",
        "trace_event_count",
    ):
        _nonnegative_int(row, key, errors)
    for key in ("sum_of_loss", "additive_sum_of_loss"):
        _nonnegative_int(row, key, errors, nullable=True)
    for key in (
        "probe_short_budget_sec",
        "runtime_ms",
        "delta_ratio_vs_additive",
    ):
        _finite_number(row, key, errors)
    for key in (
        "sum_of_loss_ratio",
        "time_to_first_solution_ms",
        "additive_sum_of_loss_ratio",
        "base_sum_of_loss_ratio_this_iteration",
    ):
        _finite_number(row, key, errors, nullable=True)

    if row["solution_found"]:
        if row["sum_of_loss"] is None:
            errors.append("sum_of_loss must be non-null when solution_found is true")
        if row["sum_of_loss_ratio"] is None:
            errors.append("sum_of_loss_ratio must be non-null when solution_found is true")
    else:
        if row["sum_of_loss"] is not None:
            errors.append("sum_of_loss must be null when solution_found is false")
        if row["sum_of_loss_ratio"] is not None:
            errors.append("sum_of_loss_ratio must be null when solution_found is false")

    if row["additive_solution_found"] and row["additive_sum_of_loss_ratio"] is None:
        errors.append("additive_sum_of_loss_ratio must be non-null when additive solved")
    if row["rule_id"] == "additive_ltm":
        if abs(float(row["delta_ratio_vs_additive"])) > 1e-12:
            errors.append("additive_ltm delta_ratio_vs_additive must be zero")
        if row["harmful"]:
            errors.append("additive_ltm must not be marked harmful")

    params = row["rule_params"]
    for key in ("alpha_commit", "alpha_block", "alpha_wait", "rho_decay", "saturation_scale", "contraflow_penalty"):
        if key not in params:
            errors.append(f"rule_params missing {key}")
        elif not _is_number(params[key]) or not math.isfinite(float(params[key])):
            errors.append(f"rule_params.{key} must be a finite number")
    return errors


def read_checkpoint_jsonl(path: str | Path) -> Iterator[dict]:
    yield from _read_jsonl(Path(path))


def read_trace_jsonl(path: str | Path) -> Iterator[dict]:
    yield from _read_jsonl(Path(path))


def read_probe_jsonl(path: str | Path) -> Iterator[dict]:
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


def _probe_sort_key(row: dict) -> tuple:
    if row.get("solution_found") and row.get("sum_of_loss_ratio") is not None:
        return (1, -float(row["sum_of_loss_ratio"]), int(row.get("returned_solutions_count", 0)))
    return (0, int(row.get("returned_solutions_count", 0)), -int(row.get("expanded_nodes", 0)))


def build_best_rule_labels(probe_rows: Iterable[dict], min_delta_ratio: float = 0.005) -> list[dict]:
    """Build one checkpoint-level best-rule label from Phase4D per-rule probe rows."""

    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in probe_rows:
        grouped[str(row["checkpoint_id"])].append(row)

    labels: list[dict] = []
    for checkpoint_id in sorted(grouped):
        rows = grouped[checkpoint_id]
        additive_rows = [row for row in rows if row.get("rule_id") == "additive_ltm"]
        if not additive_rows:
            continue
        additive = additive_rows[0]
        best = max(rows, key=_probe_sort_key)
        best_delta = float(best.get("delta_ratio_vs_additive", 0.0))
        neutral = best_delta < min_delta_ratio
        label_rule_id = "neutral_additive" if neutral else str(best["rule_id"])
        harmful_rule_ids = sorted(str(row["rule_id"]) for row in rows if row.get("harmful"))

        labels.append(
            {
                "schema_version": BEST_RULE_LABEL_SCHEMA_VERSION,
                "run_id": additive["run_id"],
                "checkpoint_id": checkpoint_id,
                "split": additive["split"],
                "map_name": additive["map_name"],
                "agents": additive["agents"],
                "seed": additive["seed"],
                "iteration": additive["iteration"],
                "label_rule_id": label_rule_id,
                "best_rule_id": best["rule_id"],
                "best_probe_id": best["probe_id"],
                "best_delta_ratio_vs_additive": best_delta,
                "neutral": neutral,
                "additive_sum_of_loss_ratio": additive["sum_of_loss_ratio"],
                "best_sum_of_loss_ratio": best["sum_of_loss_ratio"],
                "rule_count": len(rows),
                "non_additive_rule_count": sum(1 for row in rows if row.get("rule_id") != "additive_ltm"),
                "harmful_rule_ids": harmful_rule_ids,
                "harmful_rule_count": len(harmful_rule_ids),
            }
        )
    return labels


def _rule_ids_from_config(config: dict[str, Any] | None) -> list[str]:
    if not config:
        return []
    probe_config = config.get("probe", {})
    if not isinstance(probe_config, dict):
        return []
    rule_set = probe_config.get("rule_set", [])
    return [str(rule_id) for rule_id in rule_set if str(rule_id)]


def build_rule_vocab(probe_rows: Iterable[dict], config: dict[str, Any] | None = None) -> list[str]:
    """Build a target vocabulary from actual probe rows, preserving config order."""

    rows = list(probe_rows)
    actual_rule_ids = {str(row["rule_id"]) for row in rows if row.get("rule_id")}
    ordered: list[str] = []
    for rule_id in _rule_ids_from_config(config):
        if rule_id in actual_rule_ids and rule_id not in ordered:
            ordered.append(rule_id)
    for rule_id in sorted(actual_rule_ids):
        if rule_id not in ordered:
            ordered.append(rule_id)
    if "neutral_additive" not in ordered:
        ordered.append("neutral_additive")
    return ordered


def _group_by_checkpoint(rows: Iterable[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row["checkpoint_id"])].append(row)
    return grouped


def build_update_dataset_rows(
    checkpoint_rows: Iterable[dict],
    trace_rows: Iterable[dict],
    probe_rows: Iterable[dict],
    *,
    config: dict[str, Any] | None = None,
    repo_root: str | Path | None = None,
    min_delta_ratio: float = 0.005,
) -> list[dict]:
    """Join Phase4C/4D artifacts into Phase4E checkpoint-level training samples."""

    checkpoints = list(checkpoint_rows)
    traces_by_checkpoint = _group_by_checkpoint(trace_rows)
    probes = list(probe_rows)
    labels = build_best_rule_labels(probes, min_delta_ratio=min_delta_ratio)
    labels_by_checkpoint = {str(label["checkpoint_id"]): label for label in labels}
    rule_vocab = build_rule_vocab(probes, config=config)
    topology_cache: dict[Path, Any] = {}

    rows: list[dict] = []
    for checkpoint in checkpoints:
        checkpoint_id = str(checkpoint["checkpoint_id"])
        label = labels_by_checkpoint.get(checkpoint_id)
        if label is None:
            continue

        rule_class = str(label["label_rule_id"])
        if rule_class not in rule_vocab:
            rule_vocab.append(rule_class)
        topology = topology_for_checkpoint(checkpoint, topology_cache, repo_root)
        features = build_aggregate_checkpoint_features(
            checkpoint,
            traces_by_checkpoint.get(checkpoint_id, []),
            topology=topology,
        )
        harmful_rule_ids = [str(rule_id) for rule_id in label.get("harmful_rule_ids", [])]
        target = {
            "rule_class": rule_class,
            "rule_class_index": rule_vocab.index(rule_class),
            "rule_vocab": list(rule_vocab),
            "harmful_update": bool(harmful_rule_ids),
            "harmful_rule_ids": harmful_rule_ids,
            "delta_ratio_best": float(label["best_delta_ratio_vs_additive"]),
            "label_confidence": abs(float(label["best_delta_ratio_vs_additive"])),
            "best_rule_id": str(label["best_rule_id"]),
            "neutral": bool(label["neutral"]),
            "additive_sum_of_loss_ratio": label.get("additive_sum_of_loss_ratio"),
            "best_sum_of_loss_ratio": label.get("best_sum_of_loss_ratio"),
        }
        rows.append(
            {
                "schema_version": UPDATE_DATASET_SCHEMA_VERSION,
                "run_id": checkpoint["run_id"],
                "checkpoint_id": checkpoint_id,
                "split": checkpoint["split"],
                "map_name": checkpoint["map_name"],
                "agents": checkpoint["agents"],
                "seed": checkpoint["seed"],
                "iteration": checkpoint["iteration"],
                "feature_set": FEATURE_SET,
                "feature_names": FEATURE_NAMES,
                "features": features,
                "feature_vector": feature_vector(features),
                "target": target,
                "source": {
                    "checkpoint_schema_version": checkpoint.get("schema_version"),
                    "best_rule_label_schema_version": label.get("schema_version"),
                    "probe_rule_count": int(label.get("rule_count", 0)),
                    "non_additive_rule_count": int(label.get("non_additive_rule_count", 0)),
                    "trace_event_count": int(checkpoint.get("trace_event_count", 0)),
                },
            }
        )
    return rows


def validate_update_dataset_row(row: dict) -> list[str]:
    """Return schema errors for one Phase4E update-dataset row."""

    errors = _type_errors(
        row,
        {
            "schema_version": str,
            "run_id": str,
            "checkpoint_id": str,
            "split": str,
            "map_name": str,
            "agents": int,
            "seed": int,
            "iteration": int,
            "feature_set": str,
            "feature_names": list,
            "features": dict,
            "feature_vector": list,
            "target": dict,
            "source": dict,
        },
    )
    if errors:
        return errors

    if row["schema_version"] != UPDATE_DATASET_SCHEMA_VERSION:
        errors.append(f"schema_version must be {UPDATE_DATASET_SCHEMA_VERSION}")
    if row["split"] not in VALID_SPLITS:
        errors.append("split must be train, validation, or test")
    if row["feature_set"] != FEATURE_SET:
        errors.append(f"feature_set must be {FEATURE_SET}")
    if row["feature_names"] != FEATURE_NAMES:
        errors.append("feature_names must match aggregate_checkpoint_v1")
    if len(row["feature_vector"]) != len(FEATURE_NAMES):
        errors.append("feature_vector length must match feature_names")
    if any(key in row["features"] for key in ("split", "map_name")):
        errors.append("features must not include split or map_name leakage fields")

    for name in FEATURE_NAMES:
        if name not in row["features"]:
            errors.append(f"features missing {name}")
            continue
        if not _is_number(row["features"][name]) or not math.isfinite(float(row["features"][name])):
            errors.append(f"features.{name} must be a finite number")
    for index, value in enumerate(row["feature_vector"]):
        if not _is_number(value) or not math.isfinite(float(value)):
            errors.append(f"feature_vector[{index}] must be a finite number")

    target = row["target"]
    for key, expected in {
        "rule_class": str,
        "rule_class_index": int,
        "rule_vocab": list,
        "harmful_update": bool,
        "harmful_rule_ids": list,
        "delta_ratio_best": (int, float),
        "label_confidence": (int, float),
        "best_rule_id": str,
        "neutral": bool,
    }.items():
        if key not in target:
            errors.append(f"target missing {key}")
        elif not isinstance(target[key], expected):
            errors.append(f"target.{key} has type {type(target[key]).__name__}, expected {expected}")
    if errors:
        return errors

    if not target["rule_vocab"] or not all(isinstance(rule, str) for rule in target["rule_vocab"]):
        errors.append("target.rule_vocab must be a nonempty string list")
    if target["rule_class"] not in target["rule_vocab"]:
        errors.append("target.rule_class must be in target.rule_vocab")
    elif int(target["rule_class_index"]) != target["rule_vocab"].index(target["rule_class"]):
        errors.append("target.rule_class_index must match target.rule_vocab")
    if bool(target["harmful_update"]) != bool(target["harmful_rule_ids"]):
        errors.append("target.harmful_update must match nonempty harmful_rule_ids")
    _finite_number(target, "delta_ratio_best", errors)
    _finite_number(target, "label_confidence", errors)
    if float(target["label_confidence"]) < 0.0:
        errors.append("target.label_confidence must be nonnegative")
    return errors


def audit_update_dataset_rows(rows: Iterable[dict], *, expected_checkpoint_rows: int | None = None) -> dict:
    dataset_rows = list(rows)
    schema_errors: list[str] = []
    for index, row in enumerate(dataset_rows, 1):
        schema_errors.extend(f"dataset row {index}: {error}" for error in validate_update_dataset_row(row))

    split_rows = [
        {
            "split": row["split"],
            "map": row["map_name"],
            "seed": row["seed"],
            "run_id": row["run_id"],
        }
        for row in dataset_rows
    ]
    split_errors = audit_no_leakage(split_rows) if split_rows else ["no dataset rows available for split audit"]
    label_distribution = Counter(row["target"]["rule_class"] for row in dataset_rows)
    best_rule_histogram = Counter(row["target"]["best_rule_id"] for row in dataset_rows)
    harmful_count = sum(1 for row in dataset_rows if row["target"]["harmful_update"])
    non_neutral_count = sum(1 for row in dataset_rows if not row["target"]["neutral"])
    rule_vocabs = {tuple(row["target"]["rule_vocab"]) for row in dataset_rows}
    rule_vocab = list(next(iter(rule_vocabs))) if len(rule_vocabs) == 1 else []

    result = {
        "schema_version": UPDATE_DATASET_SCHEMA_VERSION,
        "sample_count": len(dataset_rows),
        "expected_checkpoint_rows": expected_checkpoint_rows,
        "missing_label_count": (
            max(0, int(expected_checkpoint_rows) - len(dataset_rows))
            if expected_checkpoint_rows is not None
            else None
        ),
        "feature_set": FEATURE_SET,
        "feature_count": len(FEATURE_NAMES),
        "feature_names": FEATURE_NAMES,
        "rule_vocab": rule_vocab,
        "rule_vocab_count": len(rule_vocab),
        "label_distribution": dict(sorted(label_distribution.items())),
        "best_rule_histogram": dict(sorted(best_rule_histogram.items())),
        "non_neutral_checkpoint_count": non_neutral_count,
        "harmful_update_count": harmful_count,
        "dataset_schema_errors": schema_errors,
        "split_errors": split_errors,
        "dataset_schema_error_count": len(schema_errors),
        "split_error_count": len(split_errors),
        "dynamic_rule_vocab": True,
    }
    result["passed"] = not (schema_errors or split_errors) and bool(dataset_rows)
    return result


def write_jsonl(path: str | Path, rows: Iterable[dict]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _summary_counts_for(rows: list[dict], split: str) -> dict[str, Any]:
    scoped = rows if split == "all" else [row for row in rows if row["split"] == split]
    return {
        "split": split,
        "sample_count": len(scoped),
        "non_neutral_count": sum(1 for row in scoped if not row["target"]["neutral"]),
        "harmful_update_count": sum(1 for row in scoped if row["target"]["harmful_update"]),
        "feature_count": len(FEATURE_NAMES),
        "rule_vocab": json.dumps(scoped[0]["target"]["rule_vocab"] if scoped else [], sort_keys=True),
        "rule_class_distribution": json.dumps(
            dict(sorted(Counter(row["target"]["rule_class"] for row in scoped).items())),
            sort_keys=True,
        ),
        "best_rule_histogram": json.dumps(
            dict(sorted(Counter(row["target"]["best_rule_id"] for row in scoped).items())),
            sort_keys=True,
        ),
    }


def write_update_dataset_summary_csv(path: str | Path, rows: Iterable[dict]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    dataset_rows = list(rows)
    splits = ["all", *sorted({str(row["split"]) for row in dataset_rows})]
    fieldnames = [
        "split",
        "sample_count",
        "non_neutral_count",
        "harmful_update_count",
        "feature_count",
        "rule_vocab",
        "rule_class_distribution",
        "best_rule_histogram",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for split in splits:
            writer.writerow(_summary_counts_for(dataset_rows, split))


def _git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _dirty_state(cwd: Path) -> str:
    tracked = _git_value(["status", "--porcelain", "--untracked-files=no"], cwd)
    untracked = _git_value(["status", "--porcelain", "--untracked-files=normal"], cwd)
    if tracked:
        return "tracked-dirty"
    if any(line.startswith("??") for line in untracked.splitlines()):
        return "tracked-clean_untracked-present"
    return "clean"


def _display_path(path: str | Path, repo_root: Path) -> str:
    value = Path(path)
    try:
        return str(value.relative_to(repo_root))
    except ValueError:
        return str(value)


def write_update_dataset_report(
    path: str | Path,
    *,
    repo_root: str | Path,
    checkpoint_jsonl: str | Path,
    trace_jsonl: str | Path | None,
    probe_jsonl: str | Path,
    output_jsonl: str | Path,
    summary_csv: str | Path,
    audit: dict[str, Any],
) -> None:
    root = Path(repo_root)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    branch = _git_value(["branch", "--show-current"], root)
    commit = _git_value(["rev-parse", "--short", "HEAD"], root)
    dirty = _dirty_state(root)
    status = "passed" if audit.get("passed") else "failed"

    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4E LAU-LTM Update Dataset Report\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z')}\n")
        handle.write(f"Status: {status}\n\n")
        handle.write("## Code State\n\n")
        handle.write(f"- branch: `{branch}`\n")
        handle.write(f"- commit: `{commit}`\n")
        handle.write(f"- dirty: `{dirty}`\n\n")
        handle.write("## Inputs\n\n")
        handle.write(f"- checkpoints: `{_display_path(checkpoint_jsonl, root)}`\n")
        if trace_jsonl is not None:
            handle.write(f"- traces: `{_display_path(trace_jsonl, root)}`\n")
        handle.write(f"- probes: `{_display_path(probe_jsonl, root)}`\n\n")
        handle.write("## Outputs\n\n")
        handle.write(f"- dataset JSONL: `{_display_path(output_jsonl, root)}`\n")
        handle.write(f"- summary CSV: `{_display_path(summary_csv, root)}`\n\n")
        handle.write("## Dataset\n\n")
        handle.write(f"- samples: {audit['sample_count']}\n")
        handle.write(f"- feature_set: `{audit['feature_set']}`\n")
        handle.write(f"- feature_count: {audit['feature_count']}\n")
        handle.write(f"- rule_vocab: `{audit['rule_vocab']}`\n")
        handle.write(f"- label_distribution: `{audit['label_distribution']}`\n")
        handle.write(f"- best_rule_histogram: `{audit['best_rule_histogram']}`\n")
        handle.write(f"- non_neutral_checkpoints: {audit['non_neutral_checkpoint_count']}\n")
        handle.write(f"- harmful_update_count: {audit['harmful_update_count']}\n\n")
        handle.write("## Gate\n\n")
        handle.write(f"- dataset_schema_errors: {audit['dataset_schema_error_count']}\n")
        handle.write(f"- split_errors: {audit['split_error_count']}\n")
        handle.write(f"- missing_label_count: {audit['missing_label_count']}\n")
        handle.write(f"- dynamic_rule_vocab: {audit['dynamic_rule_vocab']}\n")
        handle.write(f"- passed: {audit['passed']}\n\n")
        handle.write("## Caveat\n\n")
        handle.write(
            "This is a Phase4E smoke dataset from the existing Phase4D smoke probes. "
            "It validates construction and schema only; it is not large enough for a "
            "learned-update performance claim.\n"
        )


def audit_probe_labels(probe_jsonl: str | Path, min_delta_ratio: float = 0.005) -> dict:
    """Validate Phase4D probe rows and summarize checkpoint-level best-rule labels."""

    probe_path = Path(probe_jsonl)
    rows = list(read_probe_jsonl(probe_path))
    schema_errors: list[str] = []
    grouping_errors: list[str] = []

    for index, row in enumerate(rows, 1):
        schema_errors.extend(f"probe row {index}: {error}" for error in validate_probe_row(row))

    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("checkpoint_id"))].append(row)

    for checkpoint_id, checkpoint_rows in grouped.items():
        additive_count = sum(1 for row in checkpoint_rows if row.get("rule_id") == "additive_ltm")
        non_additive_count = sum(1 for row in checkpoint_rows if row.get("rule_id") != "additive_ltm")
        if additive_count != 1:
            grouping_errors.append(f"{checkpoint_id}: expected exactly one additive_ltm row, found {additive_count}")
        if non_additive_count < 3:
            grouping_errors.append(f"{checkpoint_id}: expected at least 3 non-additive rule rows")
        for row in checkpoint_rows:
            if row.get("rule_id") == "additive_ltm" and abs(float(row.get("delta_ratio_vs_additive", 0.0))) > 1e-12:
                grouping_errors.append(f"{checkpoint_id}: additive_ltm delta is not zero")

    labels = build_best_rule_labels(rows, min_delta_ratio=min_delta_ratio)
    label_distribution = Counter(label["label_rule_id"] for label in labels)
    best_rule_histogram = Counter(label["best_rule_id"] for label in labels)
    harmful_update_count = sum(int(row.get("harmful", False)) for row in rows)

    result = {
        "probe_jsonl": str(probe_path),
        "probe_rows": len(rows),
        "checkpoint_count": len(grouped),
        "best_label_rows": len(labels),
        "probe_schema_errors": schema_errors,
        "grouping_errors": grouping_errors,
        "probe_schema_error_count": len(schema_errors),
        "grouping_error_count": len(grouping_errors),
        "non_neutral_checkpoint_count": sum(not label["neutral"] for label in labels),
        "harmful_update_count": harmful_update_count,
        "label_distribution": dict(sorted(label_distribution.items())),
        "best_rule_histogram": dict(sorted(best_rule_histogram.items())),
    }
    result["passed"] = not (schema_errors or grouping_errors) and bool(labels)
    return result


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


def _load_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read Phase4 LAUR config") from exc
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}


def _resolve_repo_path(path: Path | None, repo_root: Path) -> Path | None:
    if path is None:
        return None
    return path if path.is_absolute() else repo_root / path


def _config_path(config: dict[str, Any], key: str, repo_root: Path) -> Path | None:
    value = config.get(key)
    if not value:
        return None
    return _resolve_repo_path(Path(str(value)), repo_root)


def build_dataset_command(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    config_path = _resolve_repo_path(args.config, repo_root)
    config = _load_config(config_path)
    probe_config = config.get("probe", {}) if isinstance(config.get("probe", {}), dict) else {}

    checkpoint_path = _resolve_repo_path(args.checkpoint_jsonl, repo_root)
    trace_path = _resolve_repo_path(args.trace_jsonl, repo_root)
    if trace_path is None:
        trace_path = _config_path(config, "trace_jsonl", repo_root)
    probe_path = _resolve_repo_path(args.probe_jsonl, repo_root)
    output_path = _resolve_repo_path(args.output_jsonl, repo_root)
    summary_csv_path = _resolve_repo_path(args.summary_csv, repo_root)
    summary_json_path = _resolve_repo_path(args.summary_json, repo_root)
    report_path = _resolve_repo_path(args.report_md, repo_root)

    if checkpoint_path is None:
        raise ValueError("--checkpoint-jsonl is required")
    if probe_path is None:
        raise ValueError("--probe-jsonl is required")
    if output_path is None:
        raise ValueError("--output-jsonl is required")
    if summary_csv_path is None:
        raise ValueError("--summary-csv is required")

    min_delta = (
        float(args.min_delta_ratio)
        if args.min_delta_ratio is not None
        else float(probe_config.get("min_delta_ratio_for_label", 0.005))
    )

    checkpoints = list(read_checkpoint_jsonl(checkpoint_path))
    traces = list(read_trace_jsonl(trace_path)) if trace_path is not None and trace_path.exists() else []
    probes = list(read_probe_jsonl(probe_path))
    rows = build_update_dataset_rows(
        checkpoints,
        traces,
        probes,
        config=config,
        repo_root=repo_root,
        min_delta_ratio=min_delta,
    )
    audit = audit_update_dataset_rows(rows, expected_checkpoint_rows=len(checkpoints))
    audit["checkpoint_jsonl"] = str(checkpoint_path)
    audit["trace_jsonl"] = str(trace_path) if trace_path is not None else None
    audit["probe_jsonl"] = str(probe_path)
    audit["output_jsonl"] = str(output_path)
    audit["summary_csv"] = str(summary_csv_path)
    audit["min_delta_ratio"] = min_delta

    write_jsonl(output_path, rows)
    write_update_dataset_summary_csv(summary_csv_path, rows)
    if summary_json_path is not None:
        summary_json_path.parent.mkdir(parents=True, exist_ok=True)
        summary_json_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    if report_path is not None:
        write_update_dataset_report(
            report_path,
            repo_root=repo_root,
            checkpoint_jsonl=checkpoint_path,
            trace_jsonl=trace_path,
            probe_jsonl=probe_path,
            output_jsonl=output_path,
            summary_csv=summary_csv_path,
            audit=audit,
        )

    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0 if audit["passed"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    build_parser = subparsers.add_parser("build-dataset")
    build_parser.add_argument("--config", type=Path, default=Path("configs/phase4/laur_ltm.yaml"))
    build_parser.add_argument("--checkpoint-jsonl", type=Path, required=True)
    build_parser.add_argument("--trace-jsonl", type=Path)
    build_parser.add_argument("--probe-jsonl", type=Path, required=True)
    build_parser.add_argument("--output-jsonl", type=Path, required=True)
    build_parser.add_argument("--summary-csv", type=Path, required=True)
    build_parser.add_argument("--summary-json", type=Path)
    build_parser.add_argument("--report-md", type=Path)
    build_parser.add_argument("--min-delta-ratio", type=float)

    parser.add_argument("--checkpoint-jsonl", type=Path)
    parser.add_argument("--trace-jsonl", type=Path)
    parser.add_argument("--summary-json", type=Path)
    args = parser.parse_args(argv)
    if args.command == "build-dataset":
        return build_dataset_command(args)
    if args.checkpoint_jsonl is None or args.trace_jsonl is None:
        parser.error("--checkpoint-jsonl and --trace-jsonl are required unless using build-dataset")

    summary = audit_checkpoint_trace_join(args.checkpoint_jsonl, args.trace_jsonl)
    if args.summary_json:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

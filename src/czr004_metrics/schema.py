"""Phase2 run-row schema and compatibility normalization."""

from __future__ import annotations

import math
from typing import Any

from .core import sum_of_loss_ratio


REQUIRED_FIELDS = {
    "method": str,
    "map": str,
    "scen": str,
    "agents": int,
    "seed": int,
    "time_limit_sec": (int, float),
    "objective": str,
    "valid_instance": bool,
    "success": bool,
    "feasible": bool,
    "runtime_ms": (int, float, type(None)),
    "git_commit": str,
    "external_lacam2_commit": str,
    "branch": str,
    "dirty": str,
    "config_path": str,
    "platform": str,
}

SUCCESS_FIELDS = {
    "sum_of_loss": (int, float),
    "lower_bound": (int, float),
    "sum_of_loss_ratio": (int, float),
    "makespan": int,
}

PHASE2_CORE_FIELDS = {
    "time_to_first_solution_ms": (int, float, type(None)),
    "returned_solutions_count": (int, type(None)),
    "loop_cnt": (int, type(None)),
    "expanded_nodes": (int, type(None)),
    "high_level_expansions": (int, type(None)),
    "low_level_pibt_calls": (int, type(None)),
    "ltm_iterations": (int, type(None)),
    "committed_events": (int, type(None)),
    "blocked_events": (int, type(None)),
    "nonzero_ltm_edges": (int, type(None)),
}

PLANNING_EXECUTION_FIELDS = {
    "planning_execution_step_sec": (int, float, type(None)),
    "planning_execution_window": (int, type(None)),
}

PHASE2_OPTIONAL_FIELDS = {**PHASE2_CORE_FIELDS, **PLANNING_EXECUTION_FIELDS}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _coerce_optional_int(row: dict, key: str) -> None:
    value = row.get(key)
    if value is None:
        return
    if isinstance(value, bool):
        return
    if isinstance(value, float) and value.is_integer():
        row[key] = int(value)


def normalize_run_row(row: dict) -> dict:
    """Return a Phase2-compatible copy of a solver JSONL row."""

    normalized = dict(row)

    if "returned_solutions_count" not in normalized:
        normalized["returned_solutions_count"] = 1 if normalized.get("success") else 0
    if "high_level_expansions" not in normalized:
        normalized["high_level_expansions"] = normalized.get("loop_cnt")
    if "expanded_nodes" not in normalized:
        normalized["expanded_nodes"] = normalized.get("num_node_gen")
    if "low_level_pibt_calls" not in normalized:
        normalized["low_level_pibt_calls"] = None

    for key in PHASE2_OPTIONAL_FIELDS:
        _coerce_optional_int(normalized, key)

    ratio = sum_of_loss_ratio(normalized.get("sum_of_loss"), normalized.get("lower_bound"))
    if normalized.get("success") and ratio is not None and normalized.get("sum_of_loss_ratio") is None:
        normalized["sum_of_loss_ratio"] = ratio

    return normalized


def validate_run_row(row: dict, strict_phase2: bool = False) -> list[str]:
    """Return schema and consistency errors for one normalized run row."""

    errors: list[str] = []

    for key, expected_type in REQUIRED_FIELDS.items():
        if key not in row:
            errors.append(f"missing required field {key}")
            continue
        if not isinstance(row[key], expected_type):
            errors.append(f"{key} has type {type(row[key]).__name__}, expected {expected_type}")

    if row.get("success"):
        for key, expected_type in SUCCESS_FIELDS.items():
            if key not in row or row[key] is None:
                errors.append(f"successful row missing {key}")
                continue
            if not isinstance(row[key], expected_type) or isinstance(row[key], bool):
                errors.append(f"{key} has type {type(row[key]).__name__}, expected {expected_type}")

        expected_ratio = sum_of_loss_ratio(row.get("sum_of_loss"), row.get("lower_bound"))
        actual_ratio = row.get("sum_of_loss_ratio")
        if expected_ratio is not None and _is_number(actual_ratio):
            if not math.isclose(float(actual_ratio), expected_ratio, rel_tol=1e-9, abs_tol=1e-9):
                errors.append(
                    "sum_of_loss_ratio mismatch: "
                    f"expected {expected_ratio:.12g}, got {float(actual_ratio):.12g}"
                )

    for key, expected_type in PHASE2_OPTIONAL_FIELDS.items():
        if key not in row:
            if strict_phase2 and key in PHASE2_CORE_FIELDS:
                errors.append(f"missing Phase2 field {key}")
            continue
        if not isinstance(row[key], expected_type):
            errors.append(f"{key} has type {type(row[key]).__name__}, expected {expected_type}")

    if row.get("runtime_ms") is not None and float(row["runtime_ms"]) < 0:
        errors.append("runtime_ms must be nonnegative")
    if row.get("time_to_first_solution_ms") is not None:
        if float(row["time_to_first_solution_ms"]) < 0:
            errors.append("time_to_first_solution_ms must be nonnegative")
        if row.get("runtime_ms") is not None and float(row["time_to_first_solution_ms"]) > float(row["runtime_ms"]) + 1e-6:
            errors.append("time_to_first_solution_ms exceeds runtime_ms")

    return errors

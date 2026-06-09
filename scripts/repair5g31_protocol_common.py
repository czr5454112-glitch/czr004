"""Protocol-gate helpers for Repair5G.3.1 / G4 closure."""

from __future__ import annotations

import math
from typing import Any

BASELINE_METHOD = "lacam_star_ltm"

CONTROL_PAIRS = [
    ("lacam_star_ltm", "always_additive_defer"),
    ("lacam_star_ltm", "repair5f_candidate_additive_ltm"),
    ("lacam_star_ltm", "laur_disable"),
    ("lacam_star_ltm", "laur_force_additive_direct"),
    ("lacam_star_ltm", "repair5g_dual_additive_parity"),
    ("lacam_star_ltm", "repair5g_dual_c_equiv_additive"),
]

CONTROL_METHODS = list(dict.fromkeys(method for pair in CONTROL_PAIRS for method in pair))

STRICT_PARITY_FIELDS = ["success", "sum_of_loss", "lower_bound", "sum_of_loss_ratio", "makespan"]

ZERO_COUNT_GATES = {
    "missing_rows",
    "schema_errors",
    "solver_crash_count",
    "true_semantic_parity_mismatch_count",
}

STRICT_EXACT_GATE_FIELDS = [
    "additive_parity_exact",
    "always_additive_defer_parity_exact",
    "laur_disable_parity_exact",
    "laur_force_additive_direct_parity_exact",
    "dual_additive_parity_exact",
    "dual_c_equiv_additive_parity_exact",
]

ALLOWED_NON_SEMANTIC_CLASSIFICATIONS = {
    "exact",
    "time_budget_sensitivity",
    "timeout_equivalent",
    "returncode2_no_solution_equivalent",
    "reporting_only",
}

SELECTED_GATE_FIELDS = [
    "selected_better_gt_worse",
    "selected_mean_delta_ratio_vs_ltm_lt_neg_0p008",
    "selected_bootstrap_probability_mean_delta_lt_0_ge_0p99",
    "selected_ratio_worse_than_ltm_groups_le_1",
    "selected_success_worse_than_ltm_groups_eq_0",
]

REPRESENTATION_GATE_FIELDS = [
    "best_flow_shield_mean_delta_ratio_vs_ltm_lt_neg_0p010",
    "best_c_equiv_at_least_0p006_worse_than_best_flow",
    "best_scalar_at_least_0p006_worse_than_best_flow",
    "flow_shield_family_beats_random_median",
    "flow_shield_family_beats_shuffled_goal_progress_median",
]

GENERATED_ALIAS_METHODS = {
    "repair5g2_frozen_static_or_selector",
    "repair5g2_best_frozen_static_candidate",
    "repair5g2_c_equiv_best_frozen_baseline",
    "repair5g2_g1_top_diagnostic_candidate",
}


def number(value: Any, default: float = math.nan) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def zero_count_gate_passed(value: Any) -> bool:
    """Return true only for numeric zero, never for bool False."""

    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value)) and float(value) == 0.0


def classify_returncode(returncode: Any) -> str:
    code = int(number(returncode, -999))
    if code == 0:
        return "ok"
    if code == 2:
        return "returncode2_no_solution_equivalent"
    return "solver_crash"


def solver_crash_count(command_rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in command_rows if classify_returncode(row.get("returncode")) == "solver_crash")


def command_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (
        str(row.get("map")),
        int(number(row.get("agents"), 0)),
        int(number(row.get("seed"), 0)),
        str(row.get("method")),
    )


def case_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (
        str(row.get("map")),
        int(number(row.get("agents"), 0)),
        int(number(row.get("seed"), 0)),
        str(row.get("scen", "")),
    )


def run_dimension_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("repeat_index", ""),
        row.get("mode", ""),
        row.get("time_budget_sec", row.get("time_limit_sec", "")),
        row.get("ltm_iteration_budget", row.get("ltm_max_iterations", "")),
    )


def generated_row_kind(row: dict[str, Any]) -> str:
    method = str(row.get("method", ""))
    if row.get("repair5g3_synthetic_source_method") or row.get("repair5g4_synthetic_source_method"):
        return "synthetic_diagnostic"
    if method.startswith(("repair5g3_random", "repair5g3_shuffled", "repair5g4_random", "repair5g4_shuffled")):
        return "synthetic_diagnostic"
    if row.get("repair5g2_selected_source_method") or method in GENERATED_ALIAS_METHODS:
        return "selector_alias"
    return "raw_solver"


def is_raw_solver_row(row: dict[str, Any]) -> bool:
    return generated_row_kind(row) == "raw_solver"


def strict_mismatched_fields(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    return [field for field in STRICT_PARITY_FIELDS if left.get(field) != right.get(field)]


def near_time_budget(left: dict[str, Any], right: dict[str, Any], *, fraction: float = 0.85) -> bool:
    left_runtime = number(left.get("runtime_ms"), 0.0)
    right_runtime = number(right.get("runtime_ms"), 0.0)
    time_limit = max(number(left.get("time_limit_sec"), 0.0), number(right.get("time_limit_sec"), 0.0)) * 1000.0
    return time_limit > 0.0 and max(left_runtime, right_runtime) >= fraction * time_limit


def classify_strict_mismatch(left: dict[str, Any] | None, right: dict[str, Any] | None) -> str:
    if left is None or right is None:
        return "missing_row"
    if not strict_mismatched_fields(left, right):
        return "exact"
    left_rc = classify_returncode(left.get("returncode", 0))
    right_rc = classify_returncode(right.get("returncode", 0))
    if left_rc == "solver_crash" or right_rc == "solver_crash":
        return "solver_crash"
    if left_rc == "returncode2_no_solution_equivalent" or right_rc == "returncode2_no_solution_equivalent":
        return "returncode2_no_solution_equivalent"
    if bool(left.get("success")) != bool(right.get("success")) and near_time_budget(left, right):
        return "timeout_equivalent"
    if near_time_budget(left, right):
        return "time_budget_sensitivity"
    return "true_semantic_mismatch"


def protocol_gates_passed(
    gates: dict[str, Any],
    *,
    require_strict_exact: bool,
    parity_policy_compliant: bool = False,
) -> bool:
    base_required = {
        "expected_rows_full": True,
        "all_costs_finite": True,
        "cost_bounds_respected": True,
    }
    for key, expected in base_required.items():
        if gates.get(key) is not expected:
            return False
    for key in ["missing_rows", "schema_errors", "solver_crash_count", "true_semantic_parity_mismatch_count"]:
        if not zero_count_gate_passed(gates.get(key)):
            return False
    if require_strict_exact:
        return all(gates.get(key) is True for key in STRICT_EXACT_GATE_FIELDS if key in gates)
    return bool(parity_policy_compliant or gates.get("parity_policy_compliant"))


def selected_or_representation_can_override_protocol(gates: dict[str, Any]) -> bool:
    protocol = bool(gates.get("protocol_gates_passed"))
    selected = bool(gates.get("selected_gates_passed"))
    representation = bool(gates.get("representation_gates_passed"))
    return (selected or representation) and not protocol


def summarize_gate_value(key: str, value: Any) -> dict[str, Any]:
    type_name = type(value).__name__
    row = {
        "gate": key,
        "value_repr": repr(value),
        "type": type_name,
        "is_bool": isinstance(value, bool),
        "is_numeric": isinstance(value, (int, float)) and not isinstance(value, bool),
        "zero_count_gate": key in ZERO_COUNT_GATES or key.endswith("_count") or key.endswith("_rows"),
        "zero_count_strict_pass": zero_count_gate_passed(value),
        "bool_as_int_violation": False,
    }
    if row["zero_count_gate"] and isinstance(value, bool):
        row["bool_as_int_violation"] = True
    return row

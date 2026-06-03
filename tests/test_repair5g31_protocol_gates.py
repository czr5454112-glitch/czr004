from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from repair5g31_protocol_common import (  # noqa: E402
    classify_returncode,
    generated_row_kind,
    is_raw_solver_row,
    protocol_gates_passed,
    selected_or_representation_can_override_protocol,
    zero_count_gate_passed,
)


def test_false_does_not_pass_zero_count_gates() -> None:
    assert not zero_count_gate_passed(False)
    assert zero_count_gate_passed(0)
    assert zero_count_gate_passed(0.0)
    assert not zero_count_gate_passed("0")


def test_strict_parity_false_implies_protocol_failed() -> None:
    gates = {
        "expected_rows_full": True,
        "missing_rows": 0,
        "schema_errors": 0,
        "solver_crash_count": 0,
        "true_semantic_parity_mismatch_count": 0,
        "all_costs_finite": True,
        "cost_bounds_respected": True,
        "additive_parity_exact": False,
    }
    assert not protocol_gates_passed(gates, require_strict_exact=True)


def test_semantic_zero_does_not_imply_exact_parity() -> None:
    gates = {
        "expected_rows_full": True,
        "missing_rows": 0,
        "schema_errors": 0,
        "solver_crash_count": 0,
        "true_semantic_parity_mismatch_count": 0,
        "all_costs_finite": True,
        "cost_bounds_respected": True,
        "additive_parity_exact": False,
    }
    assert not protocol_gates_passed(gates, require_strict_exact=True)
    assert protocol_gates_passed(gates, require_strict_exact=False, parity_policy_compliant=True)


def test_selected_and_representation_cannot_override_protocol_failure() -> None:
    gates = {
        "protocol_gates_passed": False,
        "selected_gates_passed": True,
        "representation_gates_passed": True,
    }
    assert selected_or_representation_can_override_protocol(gates)


def test_synthetic_rows_are_not_raw_solver_rows_on_resume() -> None:
    synthetic = {
        "method": "repair5g4_random_flow_shield_diagnostic_seed0",
        "repair5g4_synthetic_source_method": "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
    }
    alias = {
        "method": "repair5g2_frozen_static_or_selector",
        "repair5g2_selected_source_method": "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
    }
    raw = {"method": "lacam_star_ltm"}
    assert generated_row_kind(synthetic) == "synthetic_diagnostic"
    assert generated_row_kind(alias) == "selector_alias"
    assert not is_raw_solver_row(synthetic)
    assert not is_raw_solver_row(alias)
    assert is_raw_solver_row(raw)


def test_returncode2_is_not_solver_crash() -> None:
    assert classify_returncode(0) == "ok"
    assert classify_returncode(2) == "returncode2_no_solution_equivalent"
    assert classify_returncode(1) == "solver_crash"

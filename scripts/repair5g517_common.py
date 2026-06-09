"""Shared helpers for Repair5G.5.17 targeted adapter/probe work."""

from __future__ import annotations

import csv
import json
import math
import subprocess
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable

from repair5g510_common import (
    boolish,
    context_key,
    finite_number,
    read_jsonl,
    write_csv_from_jsonl,
)
from repair5g512_common import (
    observed_id_flags,
    observed_id_guard,
    read_csv_rows,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)


G517_CLOSED_CLAIMS = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "aaai_ready": False,
    "runtime_claim_allowed": False,
    "learned_runtime_policy_validated": False,
}

DEFAULT_CPP_ADAPTER = "cpp/tools/phase1a_batch.cpp"
DEFAULT_G516_LATTICE = "outputs/tables/phase5p5_repair5g516_targeted_repair_lattice.csv"
DEFAULT_G516_PROBE_PLAN = "outputs/tables/phase5p5_repair5g516_local_targeted_probe_plan.csv"
DEFAULT_G515_V5_MATRIX = "outputs/tables/phase5p5_repair5g515_candidate_feature_matrix_v5.csv"
DEFAULT_BINARY = "build/phase1a-batch/phase1a_batch.exe"
DEFAULT_SELECTOR_SPEC = "artifacts/models/laur_ltm/repair5g5_contextual_flow_shield_selector/selector_spec.json"
DEFAULT_SOURCE_SCENARIO_DIR = "outputs/tmp/phase1a/generated/phase1a-generated-random"

G517_ADAPTER_SUMMARY = "outputs/reports/phase5p5_repair5g517_adapter_recognition_summary.json"
G517_ADAPTER_REPORT = "outputs/reports/phase5p5_repair5g517_adapter_recognition.md"
G517_SMOKE_SUMMARY = "outputs/reports/phase5p5_repair5g517_adapter_smoke_summary.json"
G517_SMOKE_REPORT = "outputs/reports/phase5p5_repair5g517_adapter_smoke.md"
G517_TARGETED_INTEGRITY_SUMMARY = "outputs/reports/phase5p5_repair5g517_targeted_probe_integrity_summary.json"
G517_TARGETED_INTEGRITY_REPORT = "outputs/reports/phase5p5_repair5g517_targeted_probe_integrity.md"
G517_TARGETED_RESULTS = "outputs/tables/phase5p5_repair5g517_targeted_probe_results.csv"
G517_TARGETED_PROBE_JSONL = "outputs/logs/phase5p5_repair5g517_targeted_probe/phase5p5_repair5g517_targeted_probe_update_probes.jsonl"
G517_ORACLE_SUMMARY = "outputs/reports/phase5p5_repair5g517_targeted_lattice_oracle_summary.json"
G517_ORACLE_REPORT = "outputs/reports/phase5p5_repair5g517_targeted_lattice_oracle.md"
G517_ORACLE_CONTEXT_TABLE = "outputs/tables/phase5p5_repair5g517_targeted_lattice_oracle_by_context.csv"
G517_ORACLE_CANDIDATE_TABLE = "outputs/tables/phase5p5_repair5g517_targeted_candidate_distribution.csv"
G517_FULL_INTEGRITY_SUMMARY = "outputs/reports/phase5p5_repair5g517_full_primary_24cand_integrity_summary.json"
G517_FULL_ORACLE_SUMMARY = "outputs/reports/phase5p5_repair5g517_full_primary_24cand_oracle_summary.json"
G517_SAFETY_SUMMARY = "outputs/reports/phase5p5_repair5g517_static_abstention_safety_update_summary.json"
G517_SAFETY_REPORT = "outputs/reports/phase5p5_repair5g517_static_abstention_safety_update.md"
G517_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g517_decision_summary.json"
G517_DECISION_REPORT = "outputs/reports/phase5p5_repair5g517_decision.md"

PRIMARY_BUDGETS_MS = [1000, 2000]
MAX_TARGET_CONTEXTS = 20
EXPECTED_TARGETED_ROWS = 960
EXPECTED_FULL_ROWS = 2880
DEFAULT_MARGIN = 0.005

STATIC_CANDIDATES = {
    "repair5g59_static_flow_shield",
    "repair5g59_static_abstain_candidate",
}
ADDITIVE_CANDIDATES = {
    "repair5g59_additive_fallback",
}
FIXED_SLOW_DECAY_CANDIDATE = "repair5g59_slow_decay_high_shield"


def lattice_rows(path: Path | str = DEFAULT_G516_LATTICE) -> list[dict[str, Any]]:
    return read_csv_rows(resolve(path, repo_root()))


def repair_candidate_ids(path: Path | str = DEFAULT_G516_LATTICE) -> list[str]:
    return [str(row.get("candidate_id", "")) for row in lattice_rows(path) if str(row.get("candidate_id", "")).startswith("repair5g516_")]


def plan_rows(path: Path | str = DEFAULT_G516_PROBE_PLAN) -> list[dict[str, Any]]:
    return read_csv_rows(resolve(path, repo_root()))


def bool_cell(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def lattice_param_tuple(row: dict[str, Any]) -> tuple[float, float, float, float, float, float, float, float, bool]:
    return (
        float(row["alpha_cong_committed"]),
        float(row["alpha_cong_blocked"]),
        float(row["alpha_flow_progress"]),
        float(row["alpha_flow_wait_or_nonprogress"]),
        float(row["rho_cong"]),
        float(row["rho_flow"]),
        float(row["flow_shield_beta"]),
        float(row["max_flow_shield"]),
        bool_cell(row["c_only"]),
    )


def params_close(lhs: tuple[Any, ...], rhs: tuple[Any, ...], *, eps: float = 1e-9) -> bool:
    if len(lhs) != len(rhs):
        return False
    for left, right in zip(lhs, rhs):
        if isinstance(left, bool) or isinstance(right, bool):
            if bool(left) != bool(right):
                return False
            continue
        if not math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=eps):
            return False
    return True


def candidate_ids_from_plan(rows: Iterable[dict[str, Any]]) -> list[str]:
    seen: OrderedDict[str, None] = OrderedDict()
    for row in rows:
        candidate = str(row.get("candidate_id", ""))
        if candidate:
            seen.setdefault(candidate, None)
    return list(seen)


def context_combos_from_plan(rows: Iterable[dict[str, Any]], *, limit: int | None = None) -> list[dict[str, Any]]:
    seen: OrderedDict[tuple[str, int, int], dict[str, Any]] = OrderedDict()
    for row in rows:
        key = (str(row.get("map", "")), int(finite_number(row.get("agents"), 0.0)), int(finite_number(row.get("seed"), 0.0)))
        if key[0] and key not in seen:
            seen[key] = {"map": key[0], "agents": key[1], "seed": key[2]}
        if limit is not None and len(seen) >= limit:
            break
    return list(seen.values())


def assert_observed_plan(rows: list[dict[str, Any]], *, label: str) -> dict[str, bool]:
    observed_id_guard([row.get("seed", "") for row in rows], label=label)
    return observed_id_flags(rows)


def read_csv_dicts(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def candidate_recognition_counts(rows: Iterable[dict[str, Any]], candidates: set[str]) -> dict[str, Any]:
    filtered = [row for row in rows if str(row.get("candidate_id", "")) in candidates]
    recognized = [row for row in filtered if boolish(row.get("candidate_recognized"))]
    fingerprints = [row for row in filtered if str(row.get("updateparams_fingerprint", "")).strip()]
    return {
        "rows": len(filtered),
        "recognized_rows": len(recognized),
        "fingerprint_rows": len(fingerprints),
        "candidate_recognized_all": bool(filtered) and len(recognized) == len(filtered),
        "updateparams_fingerprint_all": bool(filtered) and len(fingerprints) == len(filtered),
    }


def duplicate_context_candidate_budget_rows(rows: Iterable[dict[str, Any]]) -> int:
    counts: dict[tuple[str, str, int], int] = {}
    for row in rows:
        key = (
            context_key(row),
            str(row.get("candidate_id", "")),
            int(finite_number(row.get("short_budget_ms"), -1)),
        )
        counts[key] = counts.get(key, 0) + 1
    return sum(count - 1 for count in counts.values() if count > 1)


def external_lacam2_solver_status(root: Path | None = None) -> list[str]:
    actual_root = root or repo_root()
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--", "external/lacam2/lacam2"],
        cwd=actual_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return [completed.stderr.strip() or "git status failed"]
    return [line for line in completed.stdout.splitlines() if line.strip()]


def write_probe_csv_from_jsonl(jsonl_path: Path, csv_path: Path) -> list[dict[str, Any]]:
    rows = read_jsonl(jsonl_path)
    write_csv_from_jsonl(csv_path, rows)
    return rows


def write_empty_skip(path: Path | str, payload: dict[str, Any]) -> None:
    write_json(resolve(path, repo_root()), payload)


__all__ = [
    "ADDITIVE_CANDIDATES",
    "DEFAULT_BINARY",
    "DEFAULT_CPP_ADAPTER",
    "DEFAULT_G515_V5_MATRIX",
    "DEFAULT_G516_LATTICE",
    "DEFAULT_G516_PROBE_PLAN",
    "DEFAULT_MARGIN",
    "DEFAULT_SELECTOR_SPEC",
    "DEFAULT_SOURCE_SCENARIO_DIR",
    "EXPECTED_FULL_ROWS",
    "EXPECTED_TARGETED_ROWS",
    "FIXED_SLOW_DECAY_CANDIDATE",
    "G517_ADAPTER_REPORT",
    "G517_ADAPTER_SUMMARY",
    "G517_CLOSED_CLAIMS",
    "G517_DECISION_REPORT",
    "G517_DECISION_SUMMARY",
    "G517_FULL_INTEGRITY_SUMMARY",
    "G517_FULL_ORACLE_SUMMARY",
    "G517_ORACLE_CANDIDATE_TABLE",
    "G517_ORACLE_CONTEXT_TABLE",
    "G517_ORACLE_REPORT",
    "G517_ORACLE_SUMMARY",
    "G517_SAFETY_REPORT",
    "G517_SAFETY_SUMMARY",
    "G517_SMOKE_REPORT",
    "G517_SMOKE_SUMMARY",
    "G517_TARGETED_INTEGRITY_REPORT",
    "G517_TARGETED_INTEGRITY_SUMMARY",
    "G517_TARGETED_PROBE_JSONL",
    "G517_TARGETED_RESULTS",
    "MAX_TARGET_CONTEXTS",
    "PRIMARY_BUDGETS_MS",
    "STATIC_CANDIDATES",
    "assert_observed_plan",
    "candidate_ids_from_plan",
    "candidate_recognition_counts",
    "context_combos_from_plan",
    "duplicate_context_candidate_budget_rows",
    "external_lacam2_solver_status",
    "lattice_param_tuple",
    "lattice_rows",
    "params_close",
    "plan_rows",
    "read_csv_dicts",
    "repair_candidate_ids",
    "write_csv_rows",
    "write_empty_skip",
    "write_json",
    "write_probe_csv_from_jsonl",
    "write_text",
]

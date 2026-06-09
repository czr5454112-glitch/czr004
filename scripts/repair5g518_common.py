"""Shared helpers for Repair5G.5.18 executable lattice search."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from repair5g510_common import (
    as_jsonable,
    boolish,
    context_key,
    finite_number,
    mean,
    score_from_probe,
)
from repair5g512_common import observed_id_flags, observed_id_guard
from repair5g517_common import (
    DEFAULT_BINARY,
    DEFAULT_G516_PROBE_PLAN,
    DEFAULT_MARGIN,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    G517_ADAPTER_SUMMARY,
    G517_CLOSED_CLAIMS,
    G517_DECISION_SUMMARY,
    G517_ORACLE_CANDIDATE_TABLE,
    G517_ORACLE_CONTEXT_TABLE,
    G517_ORACLE_SUMMARY,
    G517_SMOKE_SUMMARY,
    G517_TARGETED_INTEGRITY_SUMMARY,
    G517_TARGETED_RESULTS,
    PRIMARY_BUDGETS_MS,
    candidate_ids_from_plan,
    context_combos_from_plan,
    duplicate_context_candidate_budget_rows,
    external_lacam2_solver_status,
    plan_rows,
    read_csv_dicts,
    repair_candidate_ids,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)


G518_CLOSED_CLAIMS = dict(G517_CLOSED_CLAIMS)

G518_PLAN_MD = "czr004_repair5g518_surrogate_executable_lattice_search_plan.md"
G518_AUTOPSY_REPORT = "outputs/reports/phase5p5_repair5g518_g517_lattice_autopsy.md"
G518_AUTOPSY_SUMMARY = "outputs/reports/phase5p5_repair5g518_g517_lattice_autopsy_summary.json"
G518_CANDIDATE_DOMINANCE = "outputs/tables/phase5p5_repair5g518_g517_candidate_dominance.csv"
G518_CONTEXT_FAMILY_WINNERS = "outputs/tables/phase5p5_repair5g518_context_family_winners.csv"
G518_POOL_CSV = "outputs/tables/phase5p5_repair5g518_surrogate_candidate_pool.csv"
G518_SELECTED_CSV = "outputs/tables/phase5p5_repair5g518_selected_candidate_batches.csv"
G518_PROPOSAL_REPORT = "outputs/reports/phase5p5_repair5g518_surrogate_lattice_proposal.md"
G518_PROPOSAL_SUMMARY = "outputs/reports/phase5p5_repair5g518_surrogate_lattice_proposal_summary.json"
G518_ADAPTER_SUMMARY = "outputs/reports/phase5p5_repair5g518_adapter_grammar_summary.json"
G518_ADAPTER_REPORT = "outputs/reports/phase5p5_repair5g518_adapter_grammar.md"
G518_ADAPTER_SMOKE_RESULTS = "outputs/tables/phase5p5_repair5g518_adapter_smoke_results.csv"
G518_BATCHES_SUMMARY = "outputs/reports/phase5p5_repair5g518_probe_batches_summary.json"
G518_BATCHES_REPORT = "outputs/reports/phase5p5_repair5g518_probe_batches.md"
G518_FULL_PRIMARY_INTEGRITY_SUMMARY = "outputs/reports/phase5p5_repair5g518_full_primary_integrity_summary.json"
G518_FULL_PRIMARY_ORACLE_SUMMARY = "outputs/reports/phase5p5_repair5g518_full_primary_oracle_summary.json"
G518_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g518_decision_summary.json"
G518_DECISION_REPORT = "outputs/reports/phase5p5_repair5g518_decision.md"


@dataclass(frozen=True)
class CandidateParams:
    alpha_cong_committed: float
    alpha_cong_blocked: float
    alpha_flow_progress: float
    alpha_flow_wait_or_nonprogress: float
    rho_cong: float
    rho_flow: float
    flow_shield_beta: float
    max_flow_shield: float
    c_only: bool = False

    def as_tuple(self) -> tuple[float, float, float, float, float, float, float, float, bool]:
        return (
            self.alpha_cong_committed,
            self.alpha_cong_blocked,
            self.alpha_flow_progress,
            self.alpha_flow_wait_or_nonprogress,
            self.rho_cong,
            self.rho_flow,
            self.flow_shield_beta,
            self.max_flow_shield,
            self.c_only,
        )

    def as_feature_dict(self, prefix: str = "") -> dict[str, Any]:
        return {
            f"{prefix}alpha_cong_committed": self.alpha_cong_committed,
            f"{prefix}alpha_cong_blocked": self.alpha_cong_blocked,
            f"{prefix}alpha_flow_progress": self.alpha_flow_progress,
            f"{prefix}alpha_flow_wait_or_nonprogress": self.alpha_flow_wait_or_nonprogress,
            f"{prefix}rho_cong": self.rho_cong,
            f"{prefix}rho_flow": self.rho_flow,
            f"{prefix}flow_shield_beta": self.flow_shield_beta,
            f"{prefix}max_flow_shield": self.max_flow_shield,
            f"{prefix}c_only": self.c_only,
        }


KNOWN_CANDIDATE_PARAMS: dict[str, CandidateParams | None] = {
    "repair5g59_additive_fallback": None,
    "repair5g59_static_flow_shield": CandidateParams(1.25, 1.25, 1.0, 0.75, 0.95, 1.0, 0.35, 0.75, False),
    "repair5g59_static_abstain_candidate": CandidateParams(1.25, 1.25, 1.0, 0.75, 0.95, 1.0, 0.35, 0.75, False),
    "repair5g59_c_only_f_disabled": CandidateParams(1.25, 1.25, 0.0, 0.75, 0.95, 1.0, 0.0, 0.0, True),
    "repair5g59_light_cong_light_flow": CandidateParams(1.0, 1.0, 0.75, 0.75, 0.98, 1.0, 0.25, 0.50, False),
    "repair5g59_block_heavy_flow_guard": CandidateParams(1.0, 1.5, 1.0, 0.50, 0.95, 1.0, 0.35, 0.75, False),
    "repair5g59_commit_heavy_flow_guard": CandidateParams(1.5, 1.0, 1.0, 0.75, 0.95, 1.0, 0.35, 0.75, False),
    "repair5g59_slow_decay_high_shield": CandidateParams(1.25, 1.25, 1.0, 0.75, 0.98, 1.0, 0.50, 1.00, False),
    "repair5g59_fast_decay_low_shield": CandidateParams(1.25, 1.25, 1.0, 0.75, 0.90, 1.0, 0.20, 0.50, False),
    "repair5g59_wait_conservative": CandidateParams(1.25, 1.25, 1.0, 0.50, 0.95, 1.0, 0.35, 0.75, False),
    "repair5g59_wait_aggressive": CandidateParams(1.25, 1.25, 1.0, 1.00, 0.95, 1.0, 0.35, 0.75, False),
    "repair5g59_flow_decay": CandidateParams(1.25, 1.25, 1.0, 0.75, 0.95, 0.95, 0.35, 0.75, False),
    "repair5g59_high_beta_cap_safe": CandidateParams(1.25, 1.25, 1.0, 0.75, 0.95, 1.0, 0.60, 0.75, False),
    "repair5g59_low_beta_high_cap": CandidateParams(1.25, 1.25, 1.0, 0.75, 0.95, 1.0, 0.20, 1.25, False),
    "repair5g516_slow_decay_safer_beta025_cap050": CandidateParams(1.25, 1.25, 1.00, 0.75, 0.92, 1.00, 0.25, 0.50, False),
    "repair5g516_slow_decay_safer_beta020_cap045": CandidateParams(1.20, 1.20, 1.00, 0.75, 0.90, 1.00, 0.20, 0.45, False),
    "repair5g516_slow_decay_safer_beta015_cap040": CandidateParams(1.15, 1.15, 1.00, 0.75, 0.88, 1.00, 0.15, 0.40, False),
    "repair5g516_wait_aggressive_low_cap": CandidateParams(1.00, 1.00, 1.05, 1.25, 0.95, 0.95, 0.20, 0.50, False),
    "repair5g516_wait_conservative_mid_cap": CandidateParams(1.00, 1.00, 1.00, 1.05, 0.95, 0.98, 0.18, 0.45, False),
    "repair5g516_wait_aggressive_fast_flow_decay": CandidateParams(1.00, 1.00, 1.10, 1.30, 0.95, 0.90, 0.18, 0.45, False),
    "repair5g516_commit_heavy_low_beta": CandidateParams(1.45, 0.90, 1.10, 0.80, 0.95, 1.00, 0.18, 0.45, False),
    "repair5g516_commit_heavy_static_guard": CandidateParams(1.35, 0.90, 1.05, 0.75, 0.92, 0.98, 0.15, 0.35, False),
    "repair5g516_static_boundary_light_flow": CandidateParams(1.00, 1.00, 1.00, 0.90, 0.95, 1.00, 0.10, 0.25, False),
    "repair5g516_static_boundary_c_only": CandidateParams(1.05, 1.05, 1.00, 0.75, 0.95, 1.00, 0.00, 0.00, True),
}


def read_json(path: Path | str) -> Any:
    return json.loads(resolve(path, repo_root()).read_text(encoding="utf-8"))


def maybe_read_json(path: Path | str) -> Any:
    actual = resolve(path, repo_root())
    return read_json(actual) if actual.exists() else {}


def decimal_token(value: float) -> str:
    text = f"{value:.2f}"
    return text.replace(".", "p")


def g518_candidate_id(params: CandidateParams) -> str:
    return (
        "repair5g518_grid_"
        f"c{decimal_token(params.alpha_cong_committed)}_"
        f"b{decimal_token(params.alpha_cong_blocked)}_"
        f"f{decimal_token(params.alpha_flow_progress)}_"
        f"w{decimal_token(params.alpha_flow_wait_or_nonprogress)}_"
        f"dc{decimal_token(params.rho_cong)}_"
        f"df{decimal_token(params.rho_flow)}_"
        f"beta{decimal_token(params.flow_shield_beta)}_"
        f"max{decimal_token(params.max_flow_shield)}_"
        f"c{1 if params.c_only else 0}"
    )


def parse_decimal_token(token: str) -> float:
    if not token or token.count("p") > 1:
        raise ValueError(f"invalid decimal token: {token}")
    if any(ch not in "0123456789p" for ch in token):
        raise ValueError(f"invalid decimal token: {token}")
    return float(token.replace("p", "."))


def parse_g518_candidate_id(candidate_id: str) -> CandidateParams:
    prefix = "repair5g518_grid_"
    if not candidate_id.startswith(prefix):
        raise ValueError(f"not a G5.18 grid candidate: {candidate_id}")
    parts = candidate_id[len(prefix) :].split("_")
    if len(parts) != 9:
        raise ValueError(f"expected 9 G5.18 fields: {candidate_id}")
    expected = ["c", "b", "f", "w", "dc", "df", "beta", "max"]
    values: list[float] = []
    for token, label in zip(parts[:8], expected):
        if not token.startswith(label):
            raise ValueError(f"expected {label} field in {candidate_id}")
        values.append(parse_decimal_token(token[len(label) :]))
    if parts[8] not in {"c0", "c1"}:
        raise ValueError(f"invalid c_only field in {candidate_id}")
    params = CandidateParams(*values, c_only=parts[8] == "c1")
    validate_g518_params(params)
    return params


def validate_g518_params(params: CandidateParams) -> None:
    checks = [
        ("alpha_cong_committed", params.alpha_cong_committed, 0.0, 2.0),
        ("alpha_cong_blocked", params.alpha_cong_blocked, 0.0, 2.0),
        ("alpha_flow_progress", params.alpha_flow_progress, 0.0, 2.0),
        ("alpha_flow_wait_or_nonprogress", params.alpha_flow_wait_or_nonprogress, 0.0, 2.0),
        ("rho_cong", params.rho_cong, 0.80, 1.02),
        ("rho_flow", params.rho_flow, 0.80, 1.02),
        ("flow_shield_beta", params.flow_shield_beta, 0.0, 0.80),
        ("max_flow_shield", params.max_flow_shield, 0.0, 1.50),
    ]
    for name, value, lower, upper in checks:
        if not (lower <= value <= upper):
            raise ValueError(f"{name}={value} outside [{lower}, {upper}]")


def candidate_params(candidate_id: str) -> CandidateParams | None:
    if candidate_id.startswith("repair5g518_grid_"):
        return parse_g518_candidate_id(candidate_id)
    return KNOWN_CANDIDATE_PARAMS.get(candidate_id)


def param_distance(lhs: CandidateParams | None, rhs: CandidateParams | None) -> float:
    if lhs is None or rhs is None:
        return math.inf
    total = 0.0
    for left, right in zip(lhs.as_tuple()[:-1], rhs.as_tuple()[:-1]):
        total += (float(left) - float(right)) ** 2
    total += (1.0 if lhs.c_only != rhs.c_only else 0.0)
    return math.sqrt(total)


def family_for_candidate(candidate_id: str, params: CandidateParams | None = None) -> str:
    if candidate_id in {
        "repair5g59_static_flow_shield",
        "repair5g59_static_abstain_candidate",
    }:
        return "static"
    if candidate_id == "repair5g59_additive_fallback":
        return "additive"
    if "block_heavy" in candidate_id:
        return "block_heavy"
    if "commit_heavy" in candidate_id:
        return "commit_heavy"
    if "wait_conservative" in candidate_id:
        return "wait_conservative"
    if "wait_aggressive" in candidate_id:
        return "wait_aggressive"
    if "high_beta" in candidate_id:
        return "high_beta"
    if "low_beta_high_cap" in candidate_id:
        return "low_beta_high_cap"
    if "flow_decay" in candidate_id or "fast_decay" in candidate_id or "slow_decay" in candidate_id:
        return "flow_decay"
    if "static_boundary" in candidate_id or "c_only" in candidate_id:
        return "static_boundary"
    actual = params if params is not None else candidate_params(candidate_id)
    if actual is None:
        return "unknown"
    if actual.c_only:
        return "static_boundary_c_only"
    if actual.alpha_cong_blocked >= 1.42:
        return "block_heavy"
    if actual.alpha_cong_committed >= 1.42:
        return "commit_heavy"
    if actual.alpha_flow_wait_or_nonprogress >= 0.95:
        return "wait_aggressive"
    if actual.alpha_flow_wait_or_nonprogress <= 0.60:
        return "wait_conservative"
    if actual.flow_shield_beta >= 0.55:
        return "high_beta"
    if actual.flow_shield_beta <= 0.25 and actual.max_flow_shield >= 1.0:
        return "low_beta_high_cap"
    if actual.rho_flow <= 0.97 or actual.rho_cong <= 0.92:
        return "flow_decay"
    if actual.max_flow_shield <= 0.55:
        return "static_boundary"
    return "hybrid_block_wait_flow"


def map_family(map_name: str) -> str:
    lower = map_name.lower()
    if lower.startswith("maze"):
        return "maze"
    if lower.startswith("warehouse"):
        return "warehouse"
    if lower.startswith("random"):
        return "random"
    if lower.startswith("empty"):
        return "empty"
    if lower.startswith("room"):
        return "room"
    return "other"


def old14_candidate_ids(root: Path | None = None) -> list[str]:
    actual_root = root or repo_root()
    plan = plan_rows(resolve(DEFAULT_G516_PROBE_PLAN, actual_root))
    repair_ids = set(repair_candidate_ids())
    return [candidate for candidate in candidate_ids_from_plan(plan) if candidate not in repair_ids]


def selected_rows(path: Path | str = G518_SELECTED_CSV) -> list[dict[str, Any]]:
    actual = resolve(path, repo_root())
    return read_csv_dicts(actual) if actual.exists() else []


def selected_new_candidates(batch: str, rows: list[dict[str, Any]] | None = None) -> list[str]:
    actual_rows = rows if rows is not None else selected_rows()
    return [
        str(row.get("candidate_id", ""))
        for row in actual_rows
        if str(row.get("batch", "")).upper() == batch.upper()
        and str(row.get("row_type", "")) == "new_candidate"
    ]


def selected_candidate_family_lookup(rows: list[dict[str, Any]] | None = None) -> dict[str, str]:
    actual_rows = rows if rows is not None else selected_rows()
    out = {}
    for row in actual_rows:
        candidate = str(row.get("candidate_id", ""))
        family = str(row.get("candidate_family", ""))
        if candidate and family:
            out[candidate] = family
    return out


def batch_result_csv(batch: str) -> str:
    return f"outputs/tables/phase5p5_repair5g518_batch_{batch.upper()}_probe_results.csv"


def batch_plan_csv(batch: str) -> str:
    return f"outputs/tables/phase5p5_repair5g518_batch_{batch.upper()}_probe_plan.csv"


def batch_integrity_summary(batch: str) -> str:
    return f"outputs/reports/phase5p5_repair5g518_batch_{batch.upper()}_integrity_summary.json"


def batch_integrity_report(batch: str) -> str:
    return f"outputs/reports/phase5p5_repair5g518_batch_{batch.upper()}_integrity.md"


def batch_oracle_summary(batch: str) -> str:
    return f"outputs/reports/phase5p5_repair5g518_batch_{batch.upper()}_oracle_summary.json"


def batch_oracle_report(batch: str) -> str:
    return f"outputs/reports/phase5p5_repair5g518_batch_{batch.upper()}_oracle.md"


def batch_oracle_context_csv(batch: str) -> str:
    return f"outputs/tables/phase5p5_repair5g518_batch_{batch.upper()}_oracle_by_context.csv"


def batch_candidate_distribution_csv(batch: str) -> str:
    return f"outputs/tables/phase5p5_repair5g518_batch_{batch.upper()}_candidate_distribution.csv"


def write_csv(path: Path | str, rows: Iterable[dict[str, Any]]) -> None:
    write_csv_rows(resolve(path, repo_root()), rows)


def write_json_file(path: Path | str, payload: Any) -> None:
    write_json(resolve(path, repo_root()), payload)


def write_text_file(path: Path | str, text: str) -> None:
    write_text(resolve(path, repo_root()), text)


def csv_fieldnames(rows: Iterable[dict[str, Any]]) -> list[str]:
    fieldnames: list[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    return fieldnames


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


__all__ = [
    "CandidateParams",
    "DEFAULT_BINARY",
    "DEFAULT_G516_PROBE_PLAN",
    "DEFAULT_MARGIN",
    "DEFAULT_SELECTOR_SPEC",
    "DEFAULT_SOURCE_SCENARIO_DIR",
    "G518_ADAPTER_REPORT",
    "G518_ADAPTER_SMOKE_RESULTS",
    "G518_ADAPTER_SUMMARY",
    "G518_AUTOPSY_REPORT",
    "G518_AUTOPSY_SUMMARY",
    "G518_BATCHES_REPORT",
    "G518_BATCHES_SUMMARY",
    "G518_CANDIDATE_DOMINANCE",
    "G518_CLOSED_CLAIMS",
    "G518_CONTEXT_FAMILY_WINNERS",
    "G518_DECISION_REPORT",
    "G518_DECISION_SUMMARY",
    "G518_FULL_PRIMARY_INTEGRITY_SUMMARY",
    "G518_FULL_PRIMARY_ORACLE_SUMMARY",
    "G518_PLAN_MD",
    "G518_POOL_CSV",
    "G518_PROPOSAL_REPORT",
    "G518_PROPOSAL_SUMMARY",
    "G518_SELECTED_CSV",
    "G517_ADAPTER_SUMMARY",
    "G517_DECISION_SUMMARY",
    "G517_ORACLE_CANDIDATE_TABLE",
    "G517_ORACLE_CONTEXT_TABLE",
    "G517_ORACLE_SUMMARY",
    "G517_SMOKE_SUMMARY",
    "G517_TARGETED_INTEGRITY_SUMMARY",
    "G517_TARGETED_RESULTS",
    "KNOWN_CANDIDATE_PARAMS",
    "PRIMARY_BUDGETS_MS",
    "append_jsonl",
    "as_jsonable",
    "batch_candidate_distribution_csv",
    "batch_integrity_report",
    "batch_integrity_summary",
    "batch_oracle_context_csv",
    "batch_oracle_report",
    "batch_oracle_summary",
    "batch_plan_csv",
    "batch_result_csv",
    "boolish",
    "candidate_params",
    "context_combos_from_plan",
    "context_key",
    "decimal_token",
    "duplicate_context_candidate_budget_rows",
    "external_lacam2_solver_status",
    "family_for_candidate",
    "finite_number",
    "g518_candidate_id",
    "map_family",
    "maybe_read_json",
    "mean",
    "observed_id_flags",
    "observed_id_guard",
    "old14_candidate_ids",
    "param_distance",
    "parse_g518_candidate_id",
    "plan_rows",
    "read_csv_dicts",
    "read_json",
    "repair_candidate_ids",
    "repo_root",
    "resolve",
    "score_from_probe",
    "selected_candidate_family_lookup",
    "selected_new_candidates",
    "selected_rows",
    "validate_g518_params",
    "write_csv",
    "write_json_file",
    "write_text_file",
]

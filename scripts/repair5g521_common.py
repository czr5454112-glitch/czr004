"""Shared helpers for Repair5G.5.21 second-wave lattice diagnostics."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from repair5g518_common import (
    CandidateParams,
    candidate_params as g518_candidate_params,
    decimal_token,
    external_lacam2_solver_status,
    g518_candidate_id,
    old14_candidate_ids,
    param_distance,
    parse_decimal_token,
    read_csv_dicts,
    repo_root,
    resolve,
    validate_g518_params,
)
from repair5g517_common import (
    DEFAULT_BINARY,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    PRIMARY_BUDGETS_MS,
    candidate_recognition_counts,
    duplicate_context_candidate_budget_rows,
    write_probe_csv_from_jsonl,
)
from repair5g519_common import (
    ADDITIVE_CANDIDATE,
    DEFAULT_MARGIN,
    G519_TARGET_BUDGET_AUDIT_CSV,
    STATIC_FLOW_SHIELD_CANDIDATE,
    as_jsonable,
    boolish,
    context_feature_columns,
    csv_number,
    feature_columns,
    finite_number,
    leakage_scan,
    map_agent_key,
    map_family,
    map_family_key,
    matrix,
    mean,
    read_json_file,
    read_rows,
    rows_by_context,
    select_candidate,
    suffix_for_lambda,
    write_json_file,
    write_rows,
    write_text_file,
)
from repair5g520_common import (
    G520_DECISION_SUMMARY,
    G520_FEATURE_MATRIX_CSV,
    G520_POLICY_SUMMARY,
    G520_SECOND_WAVE_CONTEXTS_CSV,
    G520_SECOND_WAVE_SUMMARY,
    G520_TARGETS_CSV,
    G520_TARGETS_SUMMARY,
    G520_TARGET_SEMANTICS_AUDIT_CSV,
    observed_id_flags,
    observed_id_guard,
)


G521_CLOSED_CLAIMS = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "runtime_claim_allowed": False,
    "learned_runtime_policy_validated": False,
    "aaai_ready": False,
}

G521_PLAN_MD = "czr004_repair5g521_second_wave_lattice_and_split_selector_plan.md"

G521_VERIFY_REPORT = "outputs/reports/phase5p5_repair5g521_g520_artifact_verification.md"
G521_VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g521_g520_artifact_verification_summary.json"

G521_AVOIDABLE_SEMANTICS_CSV = "outputs/tables/phase5p5_repair5g521_avoidable_failure_semantics.csv"
G521_AVOIDABLE_SEMANTICS_REPORT = "outputs/reports/phase5p5_repair5g521_avoidable_failure_semantics.md"
G521_AVOIDABLE_SEMANTICS_SUMMARY = "outputs/reports/phase5p5_repair5g521_avoidable_failure_semantics_summary.json"

G521_POOL_CSV = "outputs/tables/phase5p5_repair5g521_second_wave_candidate_pool.csv"
G521_SELECTED_CSV = "outputs/tables/phase5p5_repair5g521_selected_second_wave_candidates.csv"
G521_POOL_REPORT = "outputs/reports/phase5p5_repair5g521_second_wave_candidate_pool.md"
G521_POOL_SUMMARY = "outputs/reports/phase5p5_repair5g521_second_wave_candidate_pool_summary.json"

G521_ADAPTER_REPORT = "outputs/reports/phase5p5_repair5g521_second_wave_adapter_grammar.md"
G521_ADAPTER_SUMMARY = "outputs/reports/phase5p5_repair5g521_second_wave_adapter_grammar_summary.json"
G521_ADAPTER_RESULTS = "outputs/tables/phase5p5_repair5g521_adapter_smoke_results.csv"
G521_ADAPTER_LOG_DIR = "outputs/logs/phase5p5_repair5g521_adapter_smoke"
G521_ADAPTER_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g521_adapter_smoke_scenarios"
G521_ADAPTER_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g521_adapter_smoke_scenario_generation.json"

G521_TARGETED_LOG_DIR = "outputs/logs/phase5p5_repair5g521_targeted_second_wave"
G521_TARGETED_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g521_targeted_second_wave_scenarios"
G521_TARGETED_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g521_targeted_second_wave_scenario_generation.json"
G521_TARGETED_CONTEXTS_CSV = "outputs/tables/phase5p5_repair5g521_targeted_probe_contexts.csv"
G521_TARGETED_RESULTS_CSV = "outputs/tables/phase5p5_repair5g521_targeted_second_wave_probe_results.csv"
G521_TARGETED_INTEGRITY_REPORT = "outputs/reports/phase5p5_repair5g521_targeted_second_wave_integrity.md"
G521_TARGETED_INTEGRITY_SUMMARY = "outputs/reports/phase5p5_repair5g521_targeted_second_wave_integrity_summary.json"

G521_TARGETED_ORACLE_BY_CONTEXT_CSV = "outputs/tables/phase5p5_repair5g521_targeted_second_wave_oracle_by_context.csv"
G521_TARGETED_CANDIDATE_DISTRIBUTION_CSV = "outputs/tables/phase5p5_repair5g521_targeted_second_wave_candidate_distribution.csv"
G521_TARGETED_ORACLE_REPORT = "outputs/reports/phase5p5_repair5g521_targeted_second_wave_oracle.md"
G521_TARGETED_ORACLE_SUMMARY = "outputs/reports/phase5p5_repair5g521_targeted_second_wave_oracle_summary.json"

G521_FULL_LOG_DIR = "outputs/logs/phase5p5_repair5g521_full_primary_confirmation"
G521_FULL_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g521_full_primary_confirmation_scenarios"
G521_FULL_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g521_full_primary_confirmation_scenario_generation.json"
G521_FULL_SELECTED_CSV = "outputs/tables/phase5p5_repair5g521_full_primary_selected_candidates.csv"
G521_FULL_RESULTS_CSV = "outputs/tables/phase5p5_repair5g521_full_primary_confirmation_results.csv"
G521_FULL_INTEGRITY_REPORT = "outputs/reports/phase5p5_repair5g521_full_primary_confirmation_integrity.md"
G521_FULL_INTEGRITY_SUMMARY = "outputs/reports/phase5p5_repair5g521_full_primary_confirmation_integrity_summary.json"
G521_FULL_ORACLE_BY_CONTEXT_CSV = "outputs/tables/phase5p5_repair5g521_full_primary_confirmation_oracle_by_context.csv"
G521_FULL_CANDIDATE_DISTRIBUTION_CSV = "outputs/tables/phase5p5_repair5g521_full_primary_confirmation_candidate_distribution.csv"
G521_FULL_ORACLE_REPORT = "outputs/reports/phase5p5_repair5g521_full_primary_confirmation_oracle.md"
G521_FULL_ORACLE_SUMMARY = "outputs/reports/phase5p5_repair5g521_full_primary_confirmation_oracle_summary.json"

G521_CONTEXT_TARGETS_CSV = "outputs/tables/phase5p5_repair5g521_context_targets_v10.csv"
G521_FAMILY_TARGETS_CSV = "outputs/tables/phase5p5_repair5g521_family_targets_v10.csv"
G521_CANDIDATE_TARGETS_CSV = "outputs/tables/phase5p5_repair5g521_candidate_targets_v10.csv"
G521_TARGETS_REPORT = "outputs/reports/phase5p5_repair5g521_targets_v10.md"
G521_TARGETS_SUMMARY = "outputs/reports/phase5p5_repair5g521_targets_v10_summary.json"

G521_CONTEXT_FEATURES_CSV = "outputs/tables/phase5p5_repair5g521_split_context_features_v10.csv"
G521_FAMILY_FEATURES_CSV = "outputs/tables/phase5p5_repair5g521_split_family_features_v10.csv"
G521_CANDIDATE_FEATURES_CSV = "outputs/tables/phase5p5_repair5g521_split_candidate_features_v10.csv"
G521_FEATURES_REPORT = "outputs/reports/phase5p5_repair5g521_split_context_family_candidate_features.md"
G521_FEATURES_SUMMARY = "outputs/reports/phase5p5_repair5g521_split_context_family_candidate_features_summary.json"

G521_SELECTOR_EVAL_CSV = "outputs/tables/phase5p5_repair5g521_split_selector_eval.csv"
G521_SELECTOR_CONTEXT_DECISIONS_CSV = "outputs/tables/phase5p5_repair5g521_split_selector_context_decisions.csv"
G521_SELECTOR_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g521_split_selector_bootstrap.csv"
G521_SELECTOR_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g521_split_selector_calibration.csv"
G521_SELECTOR_DIAGNOSTICS_CSV = "outputs/tables/phase5p5_repair5g521_split_selector_group_diagnostics.csv"
G521_SELECTOR_REPORT = "outputs/reports/phase5p5_repair5g521_split_opportunity_selector.md"
G521_SELECTOR_SUMMARY = "outputs/reports/phase5p5_repair5g521_split_opportunity_selector_summary.json"

G521_GAP_MISSED_CSV = "outputs/tables/phase5p5_repair5g521_oracle_to_policy_gap_missed_contexts.csv"
G521_GAP_HARMFUL_CSV = "outputs/tables/phase5p5_repair5g521_oracle_to_policy_gap_harmful_contexts.csv"
G521_GAP_GROUPS_CSV = "outputs/tables/phase5p5_repair5g521_oracle_to_policy_gap_group_summary.csv"
G521_GAP_PARAMS_CSV = "outputs/tables/phase5p5_repair5g521_oracle_to_policy_gap_parameter_deltas.csv"
G521_GAP_REPORT = "outputs/reports/phase5p5_repair5g521_oracle_to_policy_gap.md"
G521_GAP_SUMMARY = "outputs/reports/phase5p5_repair5g521_oracle_to_policy_gap_summary.json"

G521_DECISION_REPORT = "outputs/reports/phase5p5_repair5g521_decision.md"
G521_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g521_decision_summary.json"

RISK_LAMBDAS = [0.05, 0.10, 0.20]
SEED = 20260608
PRIMARY_BUDGETS = [1000, 2000]


def g521_candidate_id(params: CandidateParams) -> str:
    return (
        "repair5g521_grid_"
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


def parse_grid_candidate_id(candidate_id: str, *, prefix: str) -> CandidateParams:
    if not candidate_id.startswith(prefix):
        raise ValueError(f"not a bounded grid candidate: {candidate_id}")
    parts = candidate_id[len(prefix) :].split("_")
    if len(parts) != 9:
        raise ValueError(f"expected 9 bounded grid fields: {candidate_id}")
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


def parse_g521_candidate_id(candidate_id: str) -> CandidateParams:
    return parse_grid_candidate_id(candidate_id, prefix="repair5g521_grid_")


def candidate_params(candidate_id: str) -> CandidateParams | None:
    if candidate_id.startswith("repair5g521_grid_"):
        return parse_g521_candidate_id(candidate_id)
    return g518_candidate_params(candidate_id)


def candidate_param_dict(candidate_id: str) -> dict[str, Any]:
    params = candidate_params(candidate_id)
    if params is None:
        return {
            "alpha_cong_committed": "",
            "alpha_cong_blocked": "",
            "alpha_flow_progress": "",
            "alpha_flow_wait_or_nonprogress": "",
            "rho_cong": "",
            "rho_flow": "",
            "flow_shield_beta": "",
            "max_flow_shield": "",
            "c_only": "",
        }
    return {
        "alpha_cong_committed": params.alpha_cong_committed,
        "alpha_cong_blocked": params.alpha_cong_blocked,
        "alpha_flow_progress": params.alpha_flow_progress,
        "alpha_flow_wait_or_nonprogress": params.alpha_flow_wait_or_nonprogress,
        "rho_cong": params.rho_cong,
        "rho_flow": params.rho_flow,
        "flow_shield_beta": params.flow_shield_beta,
        "max_flow_shield": params.max_flow_shield,
        "c_only": params.c_only,
    }


def numeric_candidate_param_dict(candidate_id: str) -> dict[str, float]:
    params = candidate_params(candidate_id)
    if params is None:
        return {
            "alpha_cong_committed": 1.0,
            "alpha_cong_blocked": 1.0,
            "alpha_flow_progress": 0.0,
            "alpha_flow_wait_or_nonprogress": 1.0,
            "rho_cong": 1.0,
            "rho_flow": 1.0,
            "flow_shield_beta": 0.0,
            "max_flow_shield": 0.0,
            "c_only": 0.0,
        }
    return {
        "alpha_cong_committed": params.alpha_cong_committed,
        "alpha_cong_blocked": params.alpha_cong_blocked,
        "alpha_flow_progress": params.alpha_flow_progress,
        "alpha_flow_wait_or_nonprogress": params.alpha_flow_wait_or_nonprogress,
        "rho_cong": params.rho_cong,
        "rho_flow": params.rho_flow,
        "flow_shield_beta": params.flow_shield_beta,
        "max_flow_shield": params.max_flow_shield,
        "c_only": 1.0 if params.c_only else 0.0,
    }


def family_for_candidate(candidate_id: str, params: CandidateParams | None = None) -> str:
    actual = params if params is not None else candidate_params(candidate_id)
    if candidate_id == ADDITIVE_CANDIDATE:
        return "additive"
    if candidate_id == STATIC_FLOW_SHIELD_CANDIDATE or "static_abstain" in candidate_id:
        return "static"
    if actual is None:
        if "block_heavy" in candidate_id:
            return "block_heavy"
        if "wait_conservative" in candidate_id:
            return "wait_conservative"
        if "high_beta" in candidate_id:
            return "high_beta"
        return "unknown"
    if actual.c_only:
        return "static_boundary_c_only"
    if actual.alpha_cong_committed <= 1.0 and actual.alpha_cong_blocked >= 1.38:
        return "block_heavy"
    if actual.flow_shield_beta >= 0.55 and actual.alpha_flow_wait_or_nonprogress >= 0.65:
        return "high_beta"
    if actual.alpha_flow_wait_or_nonprogress <= 0.50 and actual.flow_shield_beta <= 0.35:
        return "wait_conservative"
    if actual.rho_cong != 0.95 or actual.rho_flow != 1.0 or actual.max_flow_shield not in {0.75, 0.0}:
        return "flow_decay"
    if actual.alpha_cong_committed > actual.alpha_cong_blocked:
        return "commit_heavy"
    return "flow_shield"


def candidate_role(candidate_id: str, old_ids: set[str], g518_ids: set[str], g521_ids: set[str]) -> str:
    if candidate_id in old_ids:
        return "old14"
    if candidate_id in g521_ids:
        return "g521_second_wave"
    if candidate_id in g518_ids or candidate_id.startswith("repair5g518_grid_"):
        return "g518_retained"
    return "unknown"


def score(row: dict[str, Any] | None) -> float:
    if not row:
        return math.inf
    for field in ["score_primary", "probe_sum_of_loss_ratio", "score"]:
        value = finite_number(row.get(field), math.inf)
        if math.isfinite(value):
            return value
    return math.inf


def row_solution_found(row: dict[str, Any] | None) -> bool:
    return boolish((row or {}).get("probe_solution_found")) and boolish((row or {}).get("probe_feasible", True))


def row_finite_solution(row: dict[str, Any] | None) -> bool:
    return row_solution_found(row) and math.isfinite(score(row))


def context_budget_key(row: dict[str, Any]) -> tuple[str, int]:
    return (str(row.get("normalized_context_key", "")), int(finite_number(row.get("short_budget_ms"), -1)))


def context_candidate_budget_key(row: dict[str, Any]) -> tuple[str, str, int]:
    return (
        str(row.get("normalized_context_key", "")),
        str(row.get("candidate_id", "")),
        int(finite_number(row.get("short_budget_ms"), -1)),
    )


def rows_by_context_budget(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, int], list[dict[str, Any]]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[context_budget_key(row)].append(row)
    return dict(grouped)


def rows_by_context_candidate(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("normalized_context_key", "")), str(row.get("candidate_id", "")))].append(row)
    return dict(grouped)


def best_row(rows: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    finite = [row for row in rows if row_finite_solution(row)]
    return min(finite, key=lambda row: (score(row), str(row.get("candidate_id", "")))) if finite else None


def best_candidate_id(rows: Iterable[dict[str, Any]]) -> str:
    row = best_row(rows)
    return str(row.get("candidate_id", "")) if row else ""


def finite_delta(lhs: dict[str, Any] | None, rhs: dict[str, Any] | None) -> float:
    left = score(lhs)
    right = score(rhs)
    return left - right if math.isfinite(left) and math.isfinite(right) else math.inf


def compact_counter(rows: Iterable[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field, "")) for row in rows).items()))


def all_contexts_from_targets() -> list[dict[str, Any]]:
    rows = read_rows(G520_TARGETS_CSV)
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        context = str(row.get("normalized_context_key", ""))
        if context and context not in out:
            out[context] = {
                "normalized_context_key": context,
                "map": row.get("map", ""),
                "agents": row.get("agents", ""),
                "seed": row.get("seed", ""),
                "iteration": row.get("iteration", ""),
                "traffic_before_hash_full": row.get("traffic_before_hash_full", ""),
                "map_agent_group": row.get("map_agent_group", map_agent_key(row)),
                "map_family": row.get("map_family", map_family(str(row.get("map", "")))),
            }
    return [out[key] for key in sorted(out)]


def g518_retained_candidate_ids(limit: int = 8) -> list[str]:
    rows = read_rows(G520_TARGETS_CSV)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        candidate = str(row.get("candidate_id", ""))
        if candidate.startswith("repair5g518_grid_"):
            grouped[candidate].append(row)
    ranked = []
    for candidate, group in grouped.items():
        wins = sum(1 for row in group if boolish(row.get("is_new22_oracle_winner")) or boolish(row.get("new_opportunity_candidate")))
        safe_help = sum(1 for row in group if boolish(row.get("safe_new_candidate_positive")))
        gaps = [finite_number(row.get("new_candidate_best_gap_vs_old14"), math.inf) for row in group]
        ranked.append((-wins, -safe_help, mean(gaps), candidate))
    return [item[3] for item in sorted(ranked)[:limit]]


def selected_g521_candidate_ids(path: str | Path = G521_SELECTED_CSV) -> list[str]:
    rows = read_rows(path)
    return [
        str(row.get("candidate_id", ""))
        for row in rows
        if str(row.get("candidate_id", "")).startswith("repair5g521_grid_")
    ]


def old_g518_g521_sets() -> tuple[set[str], set[str], set[str]]:
    root = repo_root()
    return set(old14_candidate_ids(root)), set(g518_retained_candidate_ids()), set(selected_g521_candidate_ids())


def candidate_set_for_probe() -> list[str]:
    root = repo_root()
    return old14_candidate_ids(root) + g518_retained_candidate_ids() + selected_g521_candidate_ids()


def source_results_for_targets() -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    full_summary = read_json_file(G521_FULL_INTEGRITY_SUMMARY) if resolve(G521_FULL_INTEGRITY_SUMMARY, repo_root()).exists() else {}
    if full_summary.get("probe_ran"):
        return "full_primary_confirmation", read_rows(G521_FULL_RESULTS_CSV), full_summary
    targeted_summary = read_json_file(G521_TARGETED_INTEGRITY_SUMMARY) if resolve(G521_TARGETED_INTEGRITY_SUMMARY, repo_root()).exists() else {}
    return "targeted_only", read_rows(G521_TARGETED_RESULTS_CSV), targeted_summary


def finite_mean(values: Iterable[float]) -> float:
    return mean([value for value in values if math.isfinite(value)])


__all__ = [name for name in globals() if name.startswith("G521_") or name.startswith("G520_") or name.startswith("G519_") or name.isupper()] + [
    "ADDITIVE_CANDIDATE",
    "CandidateParams",
    "DEFAULT_BINARY",
    "DEFAULT_MARGIN",
    "DEFAULT_SELECTOR_SPEC",
    "DEFAULT_SOURCE_SCENARIO_DIR",
    "PRIMARY_BUDGETS",
    "PRIMARY_BUDGETS_MS",
    "STATIC_FLOW_SHIELD_CANDIDATE",
    "all_contexts_from_targets",
    "as_jsonable",
    "best_candidate_id",
    "best_row",
    "boolish",
    "candidate_param_dict",
    "candidate_params",
    "candidate_recognition_counts",
    "candidate_role",
    "candidate_set_for_probe",
    "compact_counter",
    "context_budget_key",
    "context_candidate_budget_key",
    "context_feature_columns",
    "csv_number",
    "duplicate_context_candidate_budget_rows",
    "external_lacam2_solver_status",
    "family_for_candidate",
    "feature_columns",
    "finite_delta",
    "finite_mean",
    "finite_number",
    "g518_candidate_id",
    "g518_retained_candidate_ids",
    "g521_candidate_id",
    "leakage_scan",
    "map_agent_key",
    "map_family",
    "map_family_key",
    "matrix",
    "mean",
    "numeric_candidate_param_dict",
    "observed_id_flags",
    "observed_id_guard",
    "old14_candidate_ids",
    "old_g518_g521_sets",
    "param_distance",
    "parse_g521_candidate_id",
    "read_csv_dicts",
    "read_json_file",
    "read_rows",
    "repo_root",
    "resolve",
    "row_finite_solution",
    "row_solution_found",
    "rows_by_context",
    "rows_by_context_budget",
    "rows_by_context_candidate",
    "score",
    "select_candidate",
    "selected_g521_candidate_ids",
    "source_results_for_targets",
    "suffix_for_lambda",
    "write_json_file",
    "write_probe_csv_from_jsonl",
    "write_rows",
    "write_text_file",
]

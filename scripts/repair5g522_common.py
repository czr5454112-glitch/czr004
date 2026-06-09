"""Shared helpers for Repair5G.5.22 response-surface teacher data."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from repair5g510_common import read_jsonl
from repair5g518_common import (
    CandidateParams,
    decimal_token,
    g518_candidate_id,
    param_distance,
    parse_decimal_token,
    validate_g518_params,
)
from repair5g519_common import (
    ADDITIVE_CANDIDATE,
    DEFAULT_MARGIN,
    STATIC_FLOW_SHIELD_CANDIDATE,
    as_jsonable,
    boolish,
    csv_number,
    finite_number,
    leakage_scan,
    map_agent_key,
    map_family,
    map_family_key,
    matrix,
    mean,
    read_json_file,
    read_rows,
    repo_root,
    resolve,
    rows_by_context,
    suffix_for_lambda,
    write_json_file,
    write_rows,
    write_text_file,
)
from repair5g521_common import (
    DEFAULT_BINARY,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    G520_SECOND_WAVE_CONTEXTS_CSV,
    G520_TARGETS_CSV,
    G521_ADAPTER_SUMMARY,
    G521_AVOIDABLE_SEMANTICS_CSV,
    G521_AVOIDABLE_SEMANTICS_SUMMARY,
    G521_CANDIDATE_FEATURES_CSV,
    G521_CANDIDATE_TARGETS_CSV,
    G521_CONTEXT_FEATURES_CSV,
    G521_CONTEXT_TARGETS_CSV,
    G521_DECISION_SUMMARY,
    G521_FEATURES_SUMMARY,
    G521_FAMILY_TARGETS_CSV,
    G521_GAP_GROUPS_CSV,
    G521_GAP_HARMFUL_CSV,
    G521_GAP_MISSED_CSV,
    G521_GAP_PARAMS_CSV,
    G521_GAP_SUMMARY,
    G521_POOL_CSV,
    G521_POOL_SUMMARY,
    G521_SELECTED_CSV,
    G521_SELECTOR_SUMMARY,
    G521_TARGETED_CANDIDATE_DISTRIBUTION_CSV,
    G521_TARGETED_CONTEXTS_CSV,
    G521_TARGETED_INTEGRITY_SUMMARY,
    G521_TARGETED_ORACLE_BY_CONTEXT_CSV,
    G521_TARGETED_ORACLE_SUMMARY,
    G521_TARGETED_RESULTS_CSV,
    G521_TARGETS_SUMMARY,
    G521_VERIFY_SUMMARY,
    PRIMARY_BUDGETS,
    candidate_recognition_counts,
    duplicate_context_candidate_budget_rows,
    external_lacam2_solver_status,
    g518_retained_candidate_ids,
    observed_id_flags,
    observed_id_guard,
    old14_candidate_ids,
    parse_grid_candidate_id,
    selected_g521_candidate_ids,
)


G522_CLOSED_CLAIMS = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "runtime_claim_allowed": False,
    "learned_runtime_policy_validated": False,
    "aaai_ready": False,
}

G522_PLAN_MD = "czr004_repair5g522_response_surface_teacher_dataset_plan.md"

G522_VERIFY_REPORT = "outputs/reports/phase5p5_repair5g522_g521_artifact_verification.md"
G522_VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g522_g521_artifact_verification_summary.json"

G522_AUTOPSY_CSV = "outputs/tables/phase5p5_repair5g522_g521_lattice_failure_autopsy.csv"
G522_AUTOPSY_REPORT = "outputs/reports/phase5p5_repair5g522_g521_lattice_failure_autopsy.md"
G522_AUTOPSY_SUMMARY = "outputs/reports/phase5p5_repair5g522_g521_lattice_failure_autopsy_summary.json"

G522_CONTEXT_PANEL_CSV = "outputs/tables/phase5p5_repair5g522_context_panel.csv"
G522_CONTEXT_PANEL_BUCKET_CSV = "outputs/tables/phase5p5_repair5g522_context_panel_bucket_summary.csv"
G522_CONTEXT_PANEL_REPORT = "outputs/reports/phase5p5_repair5g522_context_panel.md"
G522_CONTEXT_PANEL_SUMMARY = "outputs/reports/phase5p5_repair5g522_context_panel_summary.json"

G522_RAW_POOL_CSV = "outputs/tables/phase5p5_repair5g522_param_response_raw_pool.csv"
G522_RESPONSE_DESIGN_CSV = "outputs/tables/phase5p5_repair5g522_param_response_design.csv"
G522_GEOMETRY_CSV = "outputs/tables/phase5p5_repair5g522_param_response_geometry.csv"
G522_DESIGN_REPORT = "outputs/reports/phase5p5_repair5g522_param_response_design.md"
G522_DESIGN_SUMMARY = "outputs/reports/phase5p5_repair5g522_param_response_design_summary.json"

G522_ADAPTER_LOG_DIR = "outputs/logs/phase5p5_repair5g522_adapter_smoke"
G522_ADAPTER_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g522_adapter_smoke_scenarios"
G522_ADAPTER_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g522_adapter_smoke_scenario_generation.json"
G522_ADAPTER_RESULTS = "outputs/tables/phase5p5_repair5g522_adapter_smoke_results.csv"
G522_ADAPTER_REPORT = "outputs/reports/phase5p5_repair5g522_response_design_adapter.md"
G522_ADAPTER_SUMMARY = "outputs/reports/phase5p5_repair5g522_response_design_adapter_summary.json"

G522_PROBE_LOG_DIR = "outputs/logs/phase5p5_repair5g522_response_surface_probe"
G522_PROBE_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g522_response_surface_probe_scenarios"
G522_PROBE_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g522_response_surface_probe_scenario_generation.json"
G522_PROBE_RESULTS_CSV = "outputs/tables/phase5p5_repair5g522_response_surface_probe_results.csv"
G522_PROBE_INTEGRITY_REPORT = "outputs/reports/phase5p5_repair5g522_response_surface_probe_integrity.md"
G522_PROBE_INTEGRITY_SUMMARY = "outputs/reports/phase5p5_repair5g522_response_surface_probe_integrity_summary.json"

G522_ORACLE_BY_CONTEXT_CSV = "outputs/tables/phase5p5_repair5g522_response_surface_oracle_by_context.csv"
G522_ORACLE_CANDIDATE_DISTRIBUTION_CSV = "outputs/tables/phase5p5_repair5g522_response_surface_candidate_distribution.csv"
G522_ORACLE_PARAM_IMPORTANCE_CSV = "outputs/tables/phase5p5_repair5g522_response_surface_parameter_importance.csv"
G522_ORACLE_REGION_BUCKET_CSV = "outputs/tables/phase5p5_repair5g522_response_surface_region_bucket_summary.csv"
G522_ORACLE_REPORT = "outputs/reports/phase5p5_repair5g522_response_surface_oracle.md"
G522_ORACLE_SUMMARY = "outputs/reports/phase5p5_repair5g522_response_surface_oracle_summary.json"

G522_TEACHER_CONTEXT_CSV = "outputs/tables/phase5p5_repair5g522_neural_teacher_contexts.csv"
G522_TEACHER_CANDIDATE_CSV = "outputs/tables/phase5p5_repair5g522_neural_teacher_candidates.csv"
G522_TEACHER_PAIRWISE_CSV = "outputs/tables/phase5p5_repair5g522_neural_teacher_pairwise_preferences.csv"
G522_TEACHER_EDGE_CSV = "outputs/tables/phase5p5_repair5g522_neural_teacher_edge_updates.csv"
G522_TEACHER_EDGE_BLOCKER = "outputs/reports/phase5p5_repair5g522_edge_update_teacher_blocker.md"
G522_TEACHER_MANIFEST = "outputs/reports/phase5p5_repair5g522_neural_teacher_manifest.json"
G522_TEACHER_REPORT = "outputs/reports/phase5p5_repair5g522_neural_teacher_dataset.md"
G522_TEACHER_SUMMARY = "outputs/reports/phase5p5_repair5g522_neural_teacher_dataset_summary.json"

G522_SURROGATE_EVAL_CSV = "outputs/tables/phase5p5_repair5g522_neural_ready_surrogate_eval.csv"
G522_SURROGATE_CONTEXT_DECISIONS_CSV = "outputs/tables/phase5p5_repair5g522_neural_ready_surrogate_context_decisions.csv"
G522_SURROGATE_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g522_neural_ready_surrogate_bootstrap.csv"
G522_SURROGATE_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g522_neural_ready_surrogate_calibration.csv"
G522_SURROGATE_REPORT = "outputs/reports/phase5p5_repair5g522_neural_ready_surrogates.md"
G522_SURROGATE_SUMMARY = "outputs/reports/phase5p5_repair5g522_neural_ready_surrogates_summary.json"

G522_SIGNAL_PARAM_IMPORTANCE_CSV = "outputs/tables/phase5p5_repair5g522_signal_parameter_importance.csv"
G522_SIGNAL_BUCKET_PERF_CSV = "outputs/tables/phase5p5_repair5g522_signal_context_bucket_performance.csv"
G522_SIGNAL_RISK_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g522_signal_risk_calibration.csv"
G522_SIGNAL_MEMORIZATION_CSV = "outputs/tables/phase5p5_repair5g522_signal_nearest_g518_memorization.csv"
G522_SIGNAL_HEATMAP_CSV = "outputs/tables/phase5p5_repair5g522_signal_response_surface_heatmap.csv"
G522_SIGNAL_REPORT = "outputs/reports/phase5p5_repair5g522_signal_and_generalization.md"
G522_SIGNAL_SUMMARY = "outputs/reports/phase5p5_repair5g522_signal_and_generalization_summary.json"

G522_DECISION_REPORT = "outputs/reports/phase5p5_repair5g522_decision.md"
G522_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g522_decision_summary.json"

SEED = 20260608
NEAR_DUP_DISTANCE = 0.18


def g522_candidate_id(params: CandidateParams) -> str:
    return (
        "repair5g522_grid_"
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


def parse_g522_candidate_id(candidate_id: str) -> CandidateParams:
    return parse_grid_candidate_id(candidate_id, prefix="repair5g522_grid_")


def candidate_params(candidate_id: str) -> CandidateParams | None:
    if candidate_id.startswith("repair5g522_grid_"):
        return parse_g522_candidate_id(candidate_id)
    from repair5g521_common import candidate_params as previous_candidate_params

    return previous_candidate_params(candidate_id)


def params_fingerprint(params: CandidateParams | None) -> str:
    if params is None:
        return "additive_or_unknown"
    return "|".join(
        [
            f"{params.alpha_cong_committed:.6f}",
            f"{params.alpha_cong_blocked:.6f}",
            f"{params.alpha_flow_progress:.6f}",
            f"{params.alpha_flow_wait_or_nonprogress:.6f}",
            f"{params.rho_cong:.6f}",
            f"{params.rho_flow:.6f}",
            f"{params.flow_shield_beta:.6f}",
            f"{params.max_flow_shield:.6f}",
            "1" if params.c_only else "0",
        ]
    )


def candidate_param_dict(candidate_id: str, prefix: str = "") -> dict[str, Any]:
    params = candidate_params(candidate_id)
    if params is None:
        return {
            f"{prefix}alpha_cong_committed": "",
            f"{prefix}alpha_cong_blocked": "",
            f"{prefix}alpha_flow_progress": "",
            f"{prefix}alpha_flow_wait_or_nonprogress": "",
            f"{prefix}rho_cong": "",
            f"{prefix}rho_flow": "",
            f"{prefix}flow_shield_beta": "",
            f"{prefix}max_flow_shield": "",
            f"{prefix}c_only": "",
        }
    return params.as_feature_dict(prefix)


def numeric_candidate_param_dict(candidate_id: str, prefix: str = "") -> dict[str, float]:
    params = candidate_params(candidate_id)
    if params is None:
        values = {
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
    else:
        values = {
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
    return {f"{prefix}{key}": value for key, value in values.items()}


def clamp_params(params: CandidateParams) -> CandidateParams:
    return CandidateParams(
        min(max(params.alpha_cong_committed, 0.0), 2.0),
        min(max(params.alpha_cong_blocked, 0.0), 2.0),
        min(max(params.alpha_flow_progress, 0.0), 2.0),
        min(max(params.alpha_flow_wait_or_nonprogress, 0.0), 2.0),
        min(max(params.rho_cong, 0.80), 1.02),
        min(max(params.rho_flow, 0.80), 1.02),
        min(max(params.flow_shield_beta, 0.0), 0.80),
        min(max(params.max_flow_shield, 0.0), 1.50),
        bool(params.c_only),
    )


def family_for_candidate(candidate_id: str, design_rows: list[dict[str, Any]] | None = None) -> str:
    if design_rows:
        for row in design_rows:
            if str(row.get("candidate_id", "")) == candidate_id:
                return str(row.get("candidate_family", "") or row.get("candidate_region", ""))
    from repair5g521_common import family_for_candidate as previous_family

    return previous_family(candidate_id)


def candidate_role(candidate_id: str, old_ids: set[str], g518_ids: set[str], g521_ids: set[str], g522_ids: set[str]) -> str:
    if candidate_id in old_ids:
        return "old14"
    if candidate_id in g518_ids or candidate_id.startswith("repair5g518_grid_"):
        return "g518_retained"
    if candidate_id in g521_ids or candidate_id.startswith("repair5g521_grid_"):
        return "g521_previous_wave"
    if candidate_id in g522_ids or candidate_id.startswith("repair5g522_grid_"):
        return "g522_response_surface"
    return "unknown"


def old_g518_g521_g522_sets() -> tuple[set[str], set[str], set[str], set[str]]:
    root = repo_root()
    return (
        set(old14_candidate_ids(root)),
        set(g518_retained_candidate_ids(limit=8)),
        set(selected_g521_candidate_ids()),
        set(selected_g522_candidate_ids()),
    )


def selected_g522_candidate_ids(path: str | Path = G522_RESPONSE_DESIGN_CSV, *, include_probe_only: bool = False) -> list[str]:
    rows = read_rows(path)
    out = []
    for row in rows:
        candidate = str(row.get("candidate_id", ""))
        if not candidate.startswith("repair5g522_grid_"):
            continue
        if include_probe_only and not boolish(row.get("include_in_probe")):
            continue
        out.append(candidate)
    return out


def probe_candidate_ids() -> list[str]:
    root = repo_root()
    rows = read_rows(G522_RESPONSE_DESIGN_CSV)
    if rows:
        return [str(row.get("candidate_id", "")) for row in rows if boolish(row.get("include_in_probe"))]
    return old14_candidate_ids(root) + g518_retained_candidate_ids(limit=8) + selected_g522_candidate_ids()


def design_rows_by_candidate(path: str | Path = G522_RESPONSE_DESIGN_CSV) -> dict[str, dict[str, Any]]:
    return {str(row.get("candidate_id", "")): row for row in read_rows(path) if str(row.get("candidate_id", ""))}


def score(row: dict[str, Any] | None) -> float:
    if not row:
        return math.inf
    for field in ("score_primary", "probe_sum_of_loss_ratio", "score"):
        value = finite_number(row.get(field), math.inf)
        if math.isfinite(value):
            return value
    return math.inf


def row_solution_found(row: dict[str, Any] | None) -> bool:
    return boolish((row or {}).get("probe_solution_found")) and boolish((row or {}).get("probe_feasible", True))


def row_finite_solution(row: dict[str, Any] | None) -> bool:
    return row_solution_found(row) and math.isfinite(score(row))


def best_row(rows: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    finite = [row for row in rows if row_finite_solution(row)]
    return min(finite, key=lambda row: (score(row), str(row.get("candidate_id", "")))) if finite else None


def best_of(rows: Iterable[dict[str, Any]], allowed: set[str]) -> dict[str, Any] | None:
    return best_row([row for row in rows if str(row.get("candidate_id", "")) in allowed])


def context_budget_key(row: dict[str, Any]) -> tuple[str, int]:
    return (str(row.get("normalized_context_key", "")), int(finite_number(row.get("short_budget_ms"), -1)))


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


def finite_delta(lhs: dict[str, Any] | None, rhs: dict[str, Any] | None) -> float:
    left = score(lhs)
    right = score(rhs)
    return left - right if math.isfinite(left) and math.isfinite(right) else math.inf


def finite_mean(values: Iterable[float]) -> float:
    return mean([value for value in values if math.isfinite(value)])


def compact_counter(rows: Iterable[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field, "")) for row in rows).items()))


def context_bucket_lookup(path: str | Path = G522_CONTEXT_PANEL_CSV) -> dict[str, str]:
    return {str(row.get("normalized_context_key", "")): str(row.get("context_bucket", "")) for row in read_rows(path)}


def candidate_presence_gate(rows: list[dict[str, Any]], candidates: list[str]) -> bool:
    grouped: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        grouped[str(row.get("normalized_context_key", ""))].add(str(row.get("candidate_id", "")))
    required = set(candidates)
    return bool(grouped) and all(required <= seen for seen in grouped.values())


def parameter_names() -> list[str]:
    return [
        "alpha_cong_committed",
        "alpha_cong_blocked",
        "alpha_flow_progress",
        "alpha_flow_wait_or_nonprogress",
        "rho_cong",
        "rho_flow",
        "flow_shield_beta",
        "max_flow_shield",
        "c_only",
    ]


def pearson(xs: list[float], ys: list[float]) -> float:
    pairs = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 3:
        return math.nan
    mx = sum(x for x, _ in pairs) / len(pairs)
    my = sum(y for _, y in pairs) / len(pairs)
    vx = sum((x - mx) ** 2 for x, _ in pairs)
    vy = sum((y - my) ** 2 for _, y in pairs)
    if vx <= 0.0 or vy <= 0.0:
        return math.nan
    return sum((x - mx) * (y - my) for x, y in pairs) / math.sqrt(vx * vy)


def rank(values: list[float]) -> list[float]:
    ordered = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    for pos, (_, index) in enumerate(ordered):
        ranks[index] = float(pos + 1)
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float:
    pairs = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 3:
        return math.nan
    return pearson(rank([x for x, _ in pairs]), rank([y for _, y in pairs]))


def write_markdown_kv(path: Path | str, title: str, items: dict[str, Any], extra: str = "") -> None:
    lines = [f"# {title}", ""]
    for key, value in items.items():
        lines.append(f"- {key}: `{value}`")
    if extra:
        lines.extend(["", extra.rstrip()])
    write_text_file(path, "\n".join(lines) + "\n")


__all__ = [name for name in globals() if name.startswith("G522_") or name.startswith("G521_") or name.startswith("G520_") or name.isupper()] + [
    "ADDITIVE_CANDIDATE",
    "CandidateParams",
    "DEFAULT_BINARY",
    "DEFAULT_MARGIN",
    "DEFAULT_SELECTOR_SPEC",
    "DEFAULT_SOURCE_SCENARIO_DIR",
    "NEAR_DUP_DISTANCE",
    "PRIMARY_BUDGETS",
    "STATIC_FLOW_SHIELD_CANDIDATE",
    "as_jsonable",
    "best_of",
    "best_row",
    "boolish",
    "candidate_param_dict",
    "candidate_params",
    "candidate_presence_gate",
    "candidate_recognition_counts",
    "candidate_role",
    "clamp_params",
    "compact_counter",
    "context_bucket_lookup",
    "context_budget_key",
    "csv_number",
    "design_rows_by_candidate",
    "duplicate_context_candidate_budget_rows",
    "external_lacam2_solver_status",
    "family_for_candidate",
    "finite_delta",
    "finite_mean",
    "finite_number",
    "g518_candidate_id",
    "g518_retained_candidate_ids",
    "g522_candidate_id",
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
    "old_g518_g521_g522_sets",
    "param_distance",
    "parameter_names",
    "params_fingerprint",
    "parse_decimal_token",
    "parse_g522_candidate_id",
    "pearson",
    "probe_candidate_ids",
    "read_json_file",
    "read_jsonl",
    "read_rows",
    "repo_root",
    "resolve",
    "row_finite_solution",
    "row_solution_found",
    "rows_by_context",
    "rows_by_context_budget",
    "rows_by_context_candidate",
    "score",
    "selected_g521_candidate_ids",
    "selected_g522_candidate_ids",
    "spearman",
    "suffix_for_lambda",
    "validate_g518_params",
    "write_json_file",
    "write_markdown_kv",
    "write_rows",
    "write_text_file",
]

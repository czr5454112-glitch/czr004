"""Shared helpers and task implementations for Repair5G.5.23."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import append_jsonl  # noqa: E402
from repair5g510_common import context_key  # noqa: E402
from repair5g3_common import MethodSpec  # noqa: E402
from repair5g5_common import prepare_scenarios, run_one_solver_task  # noqa: E402
from repair5g517_common import write_probe_csv_from_jsonl  # noqa: E402
from repair5g519_common import (  # noqa: E402
    ADDITIVE_CANDIDATE,
    STATIC_FLOW_SHIELD_CANDIDATE,
    boolish,
    compact_counter,
    csv_number,
    finite_number,
    leakage_scan,
    map_family,
    mean,
    read_json_file,
    read_rows,
    repo_root,
    resolve,
    rows_by_context,
    write_json_file,
    write_rows,
    write_text_file,
)
from repair5g521_common import (  # noqa: E402
    DEFAULT_BINARY,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    PRIMARY_BUDGETS,
    candidate_recognition_counts,
    duplicate_context_candidate_budget_rows,
    g518_retained_candidate_ids,
    old14_candidate_ids,
)
from repair5g522_common import (  # noqa: E402
    G522_ADAPTER_SUMMARY,
    G522_CLOSED_CLAIMS,
    G522_CONTEXT_PANEL_CSV,
    G522_DECISION_SUMMARY,
    G522_ORACLE_BY_CONTEXT_CSV,
    G522_ORACLE_CANDIDATE_DISTRIBUTION_CSV,
    G522_ORACLE_SUMMARY,
    G522_PROBE_INTEGRITY_SUMMARY,
    G522_PROBE_RESULTS_CSV,
    G522_RESPONSE_DESIGN_CSV,
    G522_SURROGATE_SUMMARY,
    G522_TEACHER_CANDIDATE_CSV,
    G522_TEACHER_SUMMARY,
    candidate_params,
    candidate_presence_gate,
    candidate_role,
    design_rows_by_candidate,
    external_lacam2_solver_status,
    finite_delta,
    g522_candidate_id,
    numeric_candidate_param_dict,
    observed_id_flags,
    observed_id_guard,
    parameter_names,
    params_fingerprint,
    read_jsonl,
    row_finite_solution,
    selected_g522_candidate_ids,
    score,
    write_markdown_kv,
)


G523_CLOSED_CLAIMS = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "runtime_claim_allowed": False,
    "learned_runtime_policy_validated": False,
    "aaai_ready": False,
}

SEED = 20260608 + 523

G523_PLAN_MD = "czr004_repair5g523_full_primary_teacher_repair_plan.md"

G523_VERIFY_REPORT = "outputs/reports/phase5p5_repair5g523_g522_artifact_verification.md"
G523_VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g523_g522_artifact_verification_summary.json"

G523_CONTRADICTION_REPORT = "outputs/reports/phase5p5_repair5g523_g522_signal_contradiction.md"
G523_CONTRADICTION_SUMMARY = "outputs/reports/phase5p5_repair5g523_g522_signal_contradiction_summary.json"
G523_FORBIDDEN_AUDIT_CSV = "outputs/tables/phase5p5_repair5g523_g522_forbidden_feature_audit.csv"
G523_COVERAGE_CSV = "outputs/tables/phase5p5_repair5g523_g522_targeted_coverage.csv"
G523_CONCENTRATION_CSV = "outputs/tables/phase5p5_repair5g523_g522_win_concentration.csv"

G523_CANDIDATE_SET_CSV = "outputs/tables/phase5p5_repair5g523_full_primary_candidate_set.csv"
G523_CANDIDATE_SET_REPORT = "outputs/reports/phase5p5_repair5g523_full_primary_candidate_set.md"
G523_CANDIDATE_SET_SUMMARY = "outputs/reports/phase5p5_repair5g523_full_primary_candidate_set_summary.json"

G523_FULL_PRIMARY_LOG_DIR = "outputs/logs/phase5p5_repair5g523_full_primary_response_surface_probe"
G523_FULL_PRIMARY_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g523_full_primary_response_surface_scenarios"
G523_FULL_PRIMARY_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g523_full_primary_response_surface_scenario_generation.json"
G523_FULL_PRIMARY_RESULTS_CSV = "outputs/tables/phase5p5_repair5g523_full_primary_response_surface_probe_results.csv"
G523_FULL_PRIMARY_INTEGRITY_REPORT = "outputs/reports/phase5p5_repair5g523_full_primary_response_surface_probe_integrity.md"
G523_FULL_PRIMARY_INTEGRITY_SUMMARY = "outputs/reports/phase5p5_repair5g523_full_primary_response_surface_probe_integrity_summary.json"

G523_FULL_PRIMARY_ORACLE_BY_CONTEXT_CSV = "outputs/tables/phase5p5_repair5g523_full_primary_response_surface_oracle_by_context.csv"
G523_FULL_PRIMARY_CANDIDATE_DISTRIBUTION_CSV = "outputs/tables/phase5p5_repair5g523_full_primary_response_surface_candidate_distribution.csv"
G523_FULL_PRIMARY_REGION_COUNTS_CSV = "outputs/tables/phase5p5_repair5g523_full_primary_response_surface_region_counts.csv"
G523_FULL_PRIMARY_FAILURE_COUNTS_CSV = "outputs/tables/phase5p5_repair5g523_full_primary_response_surface_failure_counts.csv"
G523_FULL_PRIMARY_ORACLE_REPORT = "outputs/reports/phase5p5_repair5g523_full_primary_response_surface_oracle.md"
G523_FULL_PRIMARY_ORACLE_SUMMARY = "outputs/reports/phase5p5_repair5g523_full_primary_response_surface_oracle_summary.json"

G523_RECOVERY_CONTEXTS_CSV = "outputs/tables/phase5p5_repair5g523_static_recovery_contexts.csv"
G523_RECOVERY_CONTEXT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g523_static_recovery_context_summary.csv"
G523_RECOVERY_REPORT = "outputs/reports/phase5p5_repair5g523_static_recovery_mining.md"
G523_RECOVERY_SUMMARY = "outputs/reports/phase5p5_repair5g523_static_recovery_mining_summary.json"
G523_RECOVERY_LOG_DIR = "outputs/logs/phase5p5_repair5g523_static_recovery_probe"
G523_RECOVERY_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g523_static_recovery_probe_scenarios"
G523_RECOVERY_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g523_static_recovery_probe_scenario_generation.json"
G523_RECOVERY_RESULTS_CSV = "outputs/tables/phase5p5_repair5g523_static_recovery_probe_results.csv"
G523_RECOVERY_ORACLE_CSV = "outputs/tables/phase5p5_repair5g523_static_recovery_oracle_by_context.csv"
G523_RECOVERY_PROBE_REPORT = "outputs/reports/phase5p5_repair5g523_static_recovery_probe.md"
G523_RECOVERY_PROBE_SUMMARY = "outputs/reports/phase5p5_repair5g523_static_recovery_probe_summary.json"

G523_TEACHER_CONTEXT_CSV = "outputs/tables/phase5p5_repair5g523_context_teacher_v2.csv"
G523_TEACHER_CANDIDATE_CSV = "outputs/tables/phase5p5_repair5g523_candidate_teacher_v2.csv"
G523_TEACHER_PAIRWISE_CSV = "outputs/tables/phase5p5_repair5g523_pairwise_teacher_v2.csv"
G523_TEACHER_EDGE_CSV = "outputs/tables/phase5p5_repair5g523_edge_update_teacher_v2.csv"
G523_TEACHER_MANIFEST = "outputs/reports/phase5p5_repair5g523_teacher_v2_manifest.json"
G523_TEACHER_REPORT = "outputs/reports/phase5p5_repair5g523_leakage_free_teacher_dataset.md"
G523_TEACHER_SUMMARY = "outputs/reports/phase5p5_repair5g523_leakage_free_teacher_dataset_summary.json"
G523_TEACHER_EDGE_BLOCKER = "outputs/reports/phase5p5_repair5g523_edge_update_teacher_blocker.md"

G523_TRACE_CONTEXT_FEATURES_CSV = "outputs/tables/phase5p5_repair5g523_runtime_safe_trace_context_features.csv"
G523_TRACE_CANDIDATE_FEATURES_CSV = "outputs/tables/phase5p5_repair5g523_runtime_safe_trace_candidate_features.csv"
G523_TRACE_FEATURE_GROUPS_CSV = "outputs/tables/phase5p5_repair5g523_runtime_safe_trace_feature_groups.csv"
G523_TRACE_LEAKAGE_CSV = "outputs/tables/phase5p5_repair5g523_runtime_safe_trace_leakage_scan.csv"
G523_TRACE_REPORT = "outputs/reports/phase5p5_repair5g523_runtime_safe_trace_feature_matrix.md"
G523_TRACE_SUMMARY = "outputs/reports/phase5p5_repair5g523_runtime_safe_trace_feature_matrix_summary.json"

G523_SURROGATE_EVAL_CSV = "outputs/tables/phase5p5_repair5g523_leakage_free_surrogate_eval.csv"
G523_SURROGATE_CONTEXT_DECISIONS_CSV = "outputs/tables/phase5p5_repair5g523_leakage_free_surrogate_context_decisions.csv"
G523_SURROGATE_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g523_leakage_free_surrogate_bootstrap.csv"
G523_SURROGATE_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g523_leakage_free_surrogate_calibration.csv"
G523_SURROGATE_REPORT = "outputs/reports/phase5p5_repair5g523_leakage_free_surrogates.md"
G523_SURROGATE_SUMMARY = "outputs/reports/phase5p5_repair5g523_leakage_free_surrogates_summary.json"

G523_AUTOPSY_FEATURE_GROUP_CSV = "outputs/tables/phase5p5_repair5g523_feature_group_ablation.csv"
G523_AUTOPSY_HELDOUT_FAMILY_CSV = "outputs/tables/phase5p5_repair5g523_heldout_family.csv"
G523_AUTOPSY_HELDOUT_MAP_AGENT_CSV = "outputs/tables/phase5p5_repair5g523_heldout_map_agent.csv"
G523_AUTOPSY_FAILURE_MODE_CSV = "outputs/tables/phase5p5_repair5g523_failure_mode_classification.csv"
G523_AUTOPSY_FALSE_POSITIVE_CSV = "outputs/tables/phase5p5_repair5g523_top_false_positive_contexts.csv"
G523_AUTOPSY_MISSED_OPPORTUNITY_CSV = "outputs/tables/phase5p5_repair5g523_top_missed_opportunity_contexts.csv"
G523_AUTOPSY_STATIC_RECOVERY_CSV = "outputs/tables/phase5p5_repair5g523_autopsy_static_recovery_contexts.csv"
G523_AUTOPSY_INDUCED_FAILURE_CSV = "outputs/tables/phase5p5_repair5g523_autopsy_candidate_induced_failure_contexts.csv"
G523_AUTOPSY_REQUIRED_TRACE_CSV = "outputs/tables/phase5p5_repair5g523_required_new_trace_fields.csv"
G523_AUTOPSY_REPORT = "outputs/reports/phase5p5_repair5g523_feature_signal_and_failure_modes.md"
G523_AUTOPSY_SUMMARY = "outputs/reports/phase5p5_repair5g523_feature_signal_and_failure_modes_summary.json"

G523_DECISION_REPORT = "outputs/reports/phase5p5_repair5g523_decision.md"
G523_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g523_decision_summary.json"


REQUIRED_MODELS = [
    "old14_plus_g518_no_new_baseline",
    "best_fixed_g522_train_candidate",
    "context_opportunity_classifier_runtime_safe",
    "candidate_utility_ridge_runtime_safe",
    "candidate_avoidable_risk_ridge_runtime_safe",
    "two_head_utility_risk_runtime_safe",
    "pairwise_preference_ranker_runtime_safe",
    "context_gate_then_candidate_ranker_runtime_safe",
    "topk_then_risk_gate_selector",
    "conformal_abstention_runtime_safe",
    "nearest_g518_residual_baseline",
    "region_prior_baseline",
    "param_only_ablation",
    "context_only_ablation",
    "no_rich_trace_ablation",
    "source_blind_ablation",
    "label_shuffled_utility_control",
    "label_shuffled_risk_control",
    "random_feature_control",
    "oracle_upper_bound_diagnostic_not_for_promotion",
]


def load_json_if_exists(path: str | Path) -> dict[str, Any]:
    root = repo_root()
    actual = resolve(path, root)
    return read_json_file(actual) if actual.exists() else {}


def full_primary_contexts() -> list[dict[str, Any]]:
    rows = read_rows("outputs/tables/phase5p5_repair5g519_full_primary_candidate_targets.csv")
    seen: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("normalized_context_key", ""))
        if key and key not in seen:
            seen[key] = {
                "normalized_context_key": key,
                "map": row.get("map", ""),
                "agents": int(finite_number(row.get("agents"), 0)),
                "seed": int(finite_number(row.get("seed"), 0)),
                "iteration": int(finite_number(row.get("iteration"), 0)),
                "traffic_before_hash_full": row.get("traffic_before_hash_full", ""),
                "map_family": row.get("map_family", map_family(str(row.get("map", "")))),
                "map_agent_group": row.get("map_agent_group", f"{row.get('map')}|a{row.get('agents')}"),
            }
    contexts = sorted(seen.values(), key=lambda row: (str(row["map"]), int(row["agents"]), int(row["seed"])))
    observed_id_guard([row["seed"] for row in contexts], label="G5.23 full-primary contexts")
    return contexts


def rows_by_context_budget(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, int], list[dict[str, Any]]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("normalized_context_key", "")), int(finite_number(row.get("short_budget_ms"), -1)))].append(row)
    return dict(grouped)


def rows_by_context_candidate(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("normalized_context_key", "")), str(row.get("candidate_id", "")))].append(row)
    return dict(grouped)


def best_of(rows: Iterable[dict[str, Any]], allowed: set[str]) -> dict[str, Any] | None:
    finite = [row for row in rows if str(row.get("candidate_id", "")) in allowed and row_finite_solution(row)]
    return min(finite, key=lambda row: (score(row), str(row.get("candidate_id", "")))) if finite else None


def finite_solution(row: dict[str, Any] | None) -> bool:
    return row_finite_solution(row)


def candidate_set_rows() -> list[dict[str, Any]]:
    return [row for row in read_rows(G523_CANDIDATE_SET_CSV) if boolish(row.get("include_in_probe", True))]


def selected_candidate_ids() -> list[str]:
    return [str(row.get("candidate_id", "")) for row in candidate_set_rows() if str(row.get("candidate_id", ""))]


def selected_g523_g522_ids() -> list[str]:
    return [row["candidate_id"] for row in candidate_set_rows() if str(row.get("candidate_role", "")) == "g522_response_surface"]


def candidate_metadata() -> dict[str, dict[str, Any]]:
    meta = design_rows_by_candidate()
    for row in read_rows(G523_CANDIDATE_SET_CSV):
        cid = str(row.get("candidate_id", ""))
        if cid:
            meta[cid] = {**meta.get(cid, {}), **row}
    return meta


def candidate_metric_rows() -> dict[str, dict[str, Any]]:
    distribution = {
        str(row.get("candidate_id", "")): row
        for row in read_rows(G522_ORACLE_CANDIDATE_DISTRIBUTION_CSV)
        if str(row.get("candidate_id", "")).startswith("repair5g522_grid_")
    }
    design = design_rows_by_candidate()
    rows = read_rows(G522_PROBE_RESULTS_CSV)
    root = repo_root()
    old_g518 = set(old14_candidate_ids(root)) | set(g518_retained_candidate_ids(limit=8))
    by_cb = rows_by_context_budget(rows)
    old_g518_best: dict[tuple[str, int], dict[str, Any] | None] = {
        key: best_of(group, old_g518) for key, group in by_cb.items()
    }
    grouped_cc = rows_by_context_candidate(rows)
    metrics: dict[str, dict[str, Any]] = {}
    for (context, candidate), group in grouped_cc.items():
        if not candidate.startswith("repair5g522_grid_"):
            continue
        deltas = []
        for row in group:
            base = old_g518_best.get((context, int(finite_number(row.get("short_budget_ms"), -1))))
            if finite_solution(row) and finite_solution(base):
                deltas.append(score(row) - score(base))
        finite_flags = [finite_solution(row) for row in group]
        drow = distribution.get(candidate, {})
        grow = design.get(candidate, {})
        metrics[candidate] = {
            "candidate_id": candidate,
            "candidate_region": grow.get("candidate_region", drow.get("candidate_region", "")),
            "candidate_family": grow.get("candidate_family", drow.get("candidate_family", "")),
            "safe_win_count": int(finite_number(drow.get("oracle_win_count"), 0)),
            "incremental_gap": mean(deltas),
            "candidate_induced_no_solution_count": int(finite_number(drow.get("candidate_induced_no_solution_count"), 0)),
            "budget_sensitive_failure_count": 1 if len(set(finite_flags)) > 1 else 0,
            "nearest_g518_distance": finite_number(grow.get("nearest_g518_distance"), math.inf),
            "nearest_old14_distance": finite_number(grow.get("nearest_old14_distance"), math.inf),
            "fingerprint": grow.get("candidate_fingerprint", params_fingerprint(candidate_params(candidate))),
            "exact_duplicate": boolish(grow.get("exact_duplicate_of_retained_g518")) or boolish(grow.get("exact_duplicate_of_old14")),
        }
    return metrics


def main_verify_g522_artifacts(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify G5.22 artifacts before G5.23.")
    parser.add_argument("--summary-json", type=Path, default=Path(G523_VERIFY_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G523_VERIFY_REPORT))
    parser.add_argument("--ids", nargs="*", default=None)
    args = parser.parse_args(argv)
    if args.ids is not None:
        try:
            observed_id_guard(args.ids, label="G5.23 explicit ID guard")
        except ValueError as exc:
            print(json.dumps({"decision": "reserved_id_guard_rejected", "error": str(exc)}))
            return 2

    root = repo_root()
    decision = load_json_if_exists(G522_DECISION_SUMMARY)
    integrity = load_json_if_exists(G522_PROBE_INTEGRITY_SUMMARY)
    oracle = load_json_if_exists(G522_ORACLE_SUMMARY)
    teacher = load_json_if_exists(G522_TEACHER_SUMMARY)
    surrogate = load_json_if_exists(G522_SURROGATE_SUMMARY)
    probe_rows = read_rows(G522_PROBE_RESULTS_CSV)
    design_rows = read_rows(G522_RESPONSE_DESIGN_CSV)
    selected_g522 = selected_g522_candidate_ids()
    flags = observed_id_flags(probe_rows)
    external_status = external_lacam2_solver_status(root)
    worklog = resolve("docs/codex-worklog.md", root).read_text(encoding="utf-8", errors="replace")
    gates = {
        "g522_decision_expected": decision.get("decision") == "g522_no_learnable_signal_return_to_feature_or_trace_design",
        "g522_probe_integrity_passed": integrity.get("decision") == "response_surface_probe_integrity_passed_continue_oracle",
        "g522_probe_rows_eq_2940": int(finite_number(integrity.get("probe_rows"), -1)) == 2940 and len(probe_rows) == 2940,
        "g522_contexts_eq_21": int(finite_number(integrity.get("contexts_observed"), -1)) == 21,
        "g522_selected_candidates_eq_48": len(selected_g522) == 48,
        "g522_candidate_space_gate_passed": boolish(oracle.get("candidate_space_continuation_gate_passed")),
        "incremental_oracle_gap_negative_recorded": finite_number(oracle.get("incremental_oracle_gap_vs_old14_plus_g518"), math.inf) < 0,
        "g522_teacher_dataset_exists": resolve(G522_TEACHER_CANDIDATE_CSV, root).exists() and int(finite_number(teacher.get("candidate_rows"), 0)) > 0,
        "teacher_forbidden_features_detected": int(finite_number(teacher.get("forbidden_feature_count"), 0)) > 0,
        "teacher_leakage_blocks_neural_claims": int(finite_number(teacher.get("forbidden_feature_count"), 0)) > 0 and not boolish(decision.get("runtime_claim_allowed")),
        "g522_promising_surrogate_false": surrogate.get("promising_surrogate") is False,
        "external_lacam2_solver_untouched": not external_status,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "closed_claims_false": all(not boolish(decision.get(key)) for key in G523_CLOSED_CLAIMS),
        "g523_worklog_entry_before_probe": "Repair5G.5.23 full-primary teacher repair" in worklog,
    }
    out_decision = "g522_artifacts_verified_continue_g523" if all(gates.values()) else "g522_artifact_verification_failed_stop"
    summary = {
        "schema_version": "phase5p5_repair5g523_g522_artifact_verification_summary_v1",
        "decision": out_decision,
        "g522_final_decision": decision.get("decision", ""),
        "g522_probe_rows": len(probe_rows),
        "g522_contexts": len({row.get("normalized_context_key", "") for row in probe_rows}),
        "g522_candidates": len({row.get("candidate_id", "") for row in probe_rows}),
        "g522_design_rows": len(design_rows),
        "g522_selected_candidates": len(selected_g522),
        "teacher_forbidden_feature_count": teacher.get("forbidden_feature_count", ""),
        "surrogate_promising": surrogate.get("promising_surrogate", ""),
        "external_lacam2_solver_status": external_status,
        "gates": gates,
        **flags,
        **G523_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.23 G5.22 Artifact Verification\n\n"
        f"- decision: `{out_decision}`\n"
        f"- g522_probe_rows: `{len(probe_rows)}`\n"
        f"- g522_contexts: `{summary['g522_contexts']}`\n"
        f"- g522_candidates: `{summary['g522_candidates']}`\n"
        f"- g522_selected_candidates: `{len(selected_g522)}`\n"
        f"- teacher_forbidden_feature_count: `{teacher.get('forbidden_feature_count', '')}`\n"
        f"- surrogate_promising: `{surrogate.get('promising_surrogate', '')}`\n"
        f"- gates: `{gates}`\n",
    )
    print(json.dumps({"decision": out_decision, "g522_probe_rows": len(probe_rows)}))
    return 0 if out_decision == "g522_artifacts_verified_continue_g523" else 2


def forbidden_feature_audit_rows() -> list[dict[str, Any]]:
    rows = []
    sources = {
        "g522_teacher_candidate": read_rows(G522_TEACHER_CANDIDATE_CSV),
        "g522_teacher_context": read_rows("outputs/tables/phase5p5_repair5g522_neural_teacher_contexts.csv"),
    }
    forbidden_terms = ("score", "oracle", "delta", "rank", "winner", "safe_positive", "regret", "future", "solution_found", "feasible", "no_solution", "candidate_induced", "budget_sensitive", "recovery")
    for source, table in sources.items():
        cols = sorted({key for row in table for key in row if key.startswith("feature_")})
        for col in cols:
            terms = [term for term in forbidden_terms if term in col.lower()]
            rows.append(
                {
                    "source_table": source,
                    "column": col,
                    "forbidden_terms": "|".join(terms),
                    "classification": "target_or_audit_only" if terms else "runtime_safe_candidate",
                    "runtime_safe": not terms,
                    "used_by_g522_performance_model": source == "g522_teacher_candidate" and bool(terms),
                    "g523_action": "rename_to_target_audit_or_outcome_namespace" if terms else "keep_or_reuse",
                    **G523_CLOSED_CLAIMS,
                }
            )
    return rows


def main_analyze_g522_signal_contradiction(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Explain the G5.22 oracle/surrogate contradiction.")
    parser.add_argument("--summary-json", type=Path, default=Path(G523_CONTRADICTION_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G523_CONTRADICTION_REPORT))
    args = parser.parse_args(argv)
    oracle = load_json_if_exists(G522_ORACLE_SUMMARY)
    teacher = load_json_if_exists(G522_TEACHER_SUMMARY)
    surrogate = load_json_if_exists(G522_SURROGATE_SUMMARY)
    probe_rows = read_rows(G522_PROBE_RESULTS_CSV)
    oracle_rows = read_rows(G522_ORACLE_BY_CONTEXT_CSV)
    panel = read_rows(G522_CONTEXT_PANEL_CSV)
    distribution = read_rows(G522_ORACLE_CANDIDATE_DISTRIBUTION_CSV)
    audit_rows = forbidden_feature_audit_rows()
    coverage_groups = []
    for field in ["map", "agents", "context_bucket"]:
        for key, count in sorted(Counter(str(row.get(field, "")) for row in panel).items()):
            coverage_groups.append({"field": field, "bucket": key, "contexts": count, **G523_CLOSED_CLAIMS})
    full_contexts = full_primary_contexts()
    covered = {row.get("normalized_context_key", "") for row in panel}
    missing_buckets = []
    for row in full_contexts:
        if row["normalized_context_key"] not in covered:
            missing_buckets.append(
                {
                    "normalized_context_key": row["normalized_context_key"],
                    "map": row["map"],
                    "agents": row["agents"],
                    "seed": row["seed"],
                    "map_family": row["map_family"],
                    "missing_from_g522_targeted": True,
                    **G523_CLOSED_CLAIMS,
                }
            )
    concentration = []
    by_context = Counter(row.get("normalized_context_key", "") for row in oracle_rows if boolish(row.get("safe_g522_response_surface_oracle_winner")))
    by_candidate = Counter(row.get("old14_plus_g518_plus_g522_oracle_candidate", "") for row in oracle_rows if boolish(row.get("safe_g522_response_surface_oracle_winner")))
    for kind, counter in [("context", by_context), ("candidate", by_candidate)]:
        for key, count in counter.most_common():
            concentration.append({"concentration_kind": kind, "key": key, "safe_win_budget_pairs": count, **G523_CLOSED_CLAIMS})
    budget_stable = oracle.get("response_surface_budget_stability", "")
    forbidden_used = any(boolish(row.get("used_by_g522_performance_model")) for row in audit_rows)
    hard_blocker = forbidden_used
    summary = {
        "schema_version": "phase5p5_repair5g523_g522_signal_contradiction_summary_v1",
        "decision": "g522_contradiction_explained_leakage_blocks_promotion",
        "candidate_space_oracle_gain": oracle.get("incremental_oracle_gap_vs_old14_plus_g518", ""),
        "safe_g522_win_contexts": oracle.get("safe_g522_win_contexts", ""),
        "safe_g522_win_budget_pairs": oracle.get("safe_g522_win_budget_pairs", ""),
        "surrogate_top3_capture": surrogate.get("best_model_summary", {}).get("top3_safe_oracle_capture_rate", ""),
        "safe_policy_sim_utility_beats_old14_plus_g518_no_new_baseline": surrogate.get("promising_surrogate_gates", {}).get("safe_policy_sim_utility_beats_old14_plus_g518_no_new_baseline", False),
        "teacher_forbidden_feature_count": teacher.get("forbidden_feature_count", ""),
        "surrogate_forbidden_feature_count": surrogate.get("forbidden_feature_count", ""),
        "forbidden_feature_used_by_performance_model": forbidden_used,
        "hard_blocker_non_promotable_teacher_or_surrogate": hard_blocker,
        "targeted_contexts": len(panel),
        "full_primary_contexts": len(full_contexts),
        "missing_full_primary_contexts": len(missing_buckets),
        "response_surface_budget_stability": budget_stable,
        "control_comparison": {
            "dominant_old14_g518_controls": oracle.get("dominant_old14_or_g518_controls", {}),
            "candidate_win_counts": oracle.get("candidate_win_counts", {}),
            "region_win_counts": oracle.get("region_win_counts", {}),
        },
        **G523_CLOSED_CLAIMS,
    }
    write_rows(G523_FORBIDDEN_AUDIT_CSV, audit_rows)
    write_rows(G523_COVERAGE_CSV, coverage_groups + missing_buckets)
    write_rows(G523_CONCENTRATION_CSV, concentration)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.23 G5.22 Signal Contradiction\n\n"
        "G5.22 had a valid candidate-space oracle signal, but the learnable package was non-promotable.\n\n"
        f"- candidate_space_oracle_gain: `{summary['candidate_space_oracle_gain']}`\n"
        f"- safe_g522_win_contexts: `{summary['safe_g522_win_contexts']}`\n"
        f"- safe_g522_win_budget_pairs: `{summary['safe_g522_win_budget_pairs']}`\n"
        f"- surrogate_top3_capture: `{summary['surrogate_top3_capture']}`\n"
        f"- safe_policy_sim_utility_beats_baseline: `{summary['safe_policy_sim_utility_beats_old14_plus_g518_no_new_baseline']}`\n"
        f"- teacher_forbidden_feature_count: `{summary['teacher_forbidden_feature_count']}`\n"
        f"- surrogate_forbidden_feature_count: `{summary['surrogate_forbidden_feature_count']}`\n"
        f"- missing_full_primary_contexts: `{summary['missing_full_primary_contexts']}`\n"
        f"- hard_blocker_non_promotable_teacher_or_surrogate: `{hard_blocker}`\n\n"
        "The leaked `feature_*` fields are renamed to target/audit/outcome/oracle namespaces in G5.23.\n",
    )
    print(json.dumps({"decision": summary["decision"], "hard_blocker": hard_blocker}))
    return 0


def main_create_full_primary_candidate_set(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create the deterministic G5.23 full-primary candidate set.")
    parser.add_argument("--summary-json", type=Path, default=Path(G523_CANDIDATE_SET_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G523_CANDIDATE_SET_REPORT))
    parser.add_argument("--output-csv", type=Path, default=Path(G523_CANDIDATE_SET_CSV))
    parser.add_argument("--g522-limit", type=int, default=22)
    args = parser.parse_args(argv)
    root = repo_root()
    metrics = candidate_metric_rows()
    selected: dict[str, set[str]] = defaultdict(set)

    eligible = [row for row in metrics.values() if not boolish(row.get("exact_duplicate"))]
    ranked_safe = sorted(eligible, key=lambda row: (-int(row["safe_win_count"]), finite_number(row["incremental_gap"], math.inf), int(row["candidate_induced_no_solution_count"]), row["candidate_id"]))
    ranked_gap = sorted(eligible, key=lambda row: (finite_number(row["incremental_gap"], math.inf), -int(row["safe_win_count"]), int(row["candidate_induced_no_solution_count"]), row["candidate_id"]))
    for row in ranked_safe[:8]:
        selected[row["candidate_id"]].add("top_safe_win_count")
    for row in ranked_gap[:8]:
        selected[row["candidate_id"]].add("top_incremental_gap")
    for region in ["B_static_recovery_feasibility", "C_risk_boundary", "D_fractional_coverage"]:
        region_rows = [row for row in ranked_safe if row.get("candidate_region") == region]
        for row in region_rows[:2]:
            selected[row["candidate_id"]].add(f"region_minimum_{region}")
    far = sorted(eligible, key=lambda row: (-finite_number(row.get("nearest_g518_distance"), -math.inf), row["candidate_id"]))
    for row in far[:4]:
        selected[row["candidate_id"]].add("far_from_g518")
    low_risk = sorted(eligible, key=lambda row: (int(row["candidate_induced_no_solution_count"]), int(row["budget_sensitive_failure_count"]), finite_number(row["incremental_gap"], math.inf), row["candidate_id"]))
    for row in low_risk[:4]:
        selected[row["candidate_id"]].add("low_induced_failure")

    def selection_rank(cid: str) -> tuple[float, int, int, str]:
        row = metrics[cid]
        return (
            finite_number(row.get("incremental_gap"), math.inf),
            -int(row.get("safe_win_count", 0)),
            int(row.get("candidate_induced_no_solution_count", 0)),
            cid,
        )

    chosen_ids = sorted(selected, key=selection_rank)
    chosen_ids = chosen_ids[: max(16, min(args.g522_limit, 24))]
    fingerprints: set[str] = set()
    deduped = []
    for cid in chosen_ids:
        fp = str(metrics[cid].get("fingerprint", cid))
        if fp in fingerprints:
            continue
        fingerprints.add(fp)
        deduped.append(cid)
    chosen_ids = deduped[: args.g522_limit]
    for row in ranked_gap:
        if len(chosen_ids) >= min(args.g522_limit, 24):
            break
        cid = row["candidate_id"]
        fp = str(row.get("fingerprint", cid))
        if cid in chosen_ids or fp in fingerprints:
            continue
        fingerprints.add(fp)
        chosen_ids.append(cid)
        selected[cid].add("minimum_count_fill")

    out_rows = []
    for cid in old14_candidate_ids(root):
        out_rows.append(
            {
                "candidate_id": cid,
                "candidate_role": "old14",
                "candidate_region": "old14",
                "candidate_family": "old14",
                "safe_win_count": "",
                "incremental_gap": "",
                "candidate_induced_no_solution_count": "",
                "budget_sensitive_failure_count": "",
                "nearest_g518_distance": "",
                "nearest_old14_distance": "",
                "selection_reason": "old14_control",
                "policy_candidate_or_negative_control": "control",
                "include_in_probe": True,
                **G523_CLOSED_CLAIMS,
            }
        )
    for cid in g518_retained_candidate_ids(limit=8):
        out_rows.append(
            {
                "candidate_id": cid,
                "candidate_role": "g518_retained",
                "candidate_region": "g518_retained",
                "candidate_family": "g518_retained",
                "safe_win_count": "",
                "incremental_gap": "",
                "candidate_induced_no_solution_count": "",
                "budget_sensitive_failure_count": "",
                "nearest_g518_distance": "",
                "nearest_old14_distance": "",
                "selection_reason": "retained_g518_control",
                "policy_candidate_or_negative_control": "control",
                "include_in_probe": True,
                **G523_CLOSED_CLAIMS,
            }
        )
    for cid in chosen_ids:
        row = metrics[cid]
        induced = int(row["candidate_induced_no_solution_count"])
        neg = induced >= 4 and int(row["safe_win_count"]) <= 1
        out_rows.append(
            {
                "candidate_id": cid,
                "candidate_role": "g522_response_surface",
                "candidate_region": row.get("candidate_region", ""),
                "candidate_family": row.get("candidate_family", ""),
                "safe_win_count": row.get("safe_win_count", 0),
                "incremental_gap": csv_number(row.get("incremental_gap", math.inf)),
                "candidate_induced_no_solution_count": induced,
                "budget_sensitive_failure_count": row.get("budget_sensitive_failure_count", 0),
                "nearest_g518_distance": csv_number(row.get("nearest_g518_distance", math.inf)),
                "nearest_old14_distance": csv_number(row.get("nearest_old14_distance", math.inf)),
                "selection_reason": "|".join(sorted(selected[cid])),
                "policy_candidate_or_negative_control": "negative_control" if neg else "policy_candidate",
                "include_in_probe": True,
                **G523_CLOSED_CLAIMS,
            }
        )
    total = len(out_rows)
    selected_count = len(chosen_ids)
    gates = {
        "g522_full_primary_selected_count_le_24": selected_count <= 24,
        "total_candidate_count_le_46": total <= 46,
        "expected_rows_in_range": 4560 <= 60 * total * 2 <= 5520,
        "old14_controls_eq_14": len(old14_candidate_ids(root)) == 14,
        "retained_g518_eq_8": len(g518_retained_candidate_ids(limit=8)) == 8,
        "no_exact_duplicate_fingerprints": len(fingerprints) == len(chosen_ids),
    }
    summary = {
        "schema_version": "phase5p5_repair5g523_full_primary_candidate_set_summary_v1",
        "decision": "full_primary_candidate_set_created" if all(gates.values()) else "full_primary_candidate_set_gate_failed",
        "old14_candidate_count": len(old14_candidate_ids(root)),
        "g518_retained_candidate_count": len(g518_retained_candidate_ids(limit=8)),
        "g522_full_primary_selected_count": selected_count,
        "total_candidate_count": total,
        "expected_rows": 60 * total * 2,
        "selected_g522_candidates": chosen_ids,
        "region_counts": dict(Counter(str(metrics[cid].get("candidate_region", "")) for cid in chosen_ids)),
        "gates": gates,
        **G523_CLOSED_CLAIMS,
    }
    write_rows(args.output_csv, out_rows)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.23 Full-Primary Candidate Set\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- old14_candidate_count: `{summary['old14_candidate_count']}`\n"
        f"- g518_retained_candidate_count: `{summary['g518_retained_candidate_count']}`\n"
        f"- g522_full_primary_selected_count: `{selected_count}`\n"
        f"- total_candidate_count: `{total}`\n"
        f"- expected_rows: `{summary['expected_rows']}`\n"
        f"- region_counts: `{summary['region_counts']}`\n"
        f"- gates: `{gates}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "total_candidate_count": total, "g522_selected": selected_count}))
    return 0 if all(gates.values()) else 2


def method_spec_for_budget(*, budget: int, selector_spec: Path, probe_jsonl: Path, checkpoint_jsonl: Path, candidates: list[str], label: str) -> MethodSpec:
    return MethodSpec(
        "repair5g59_static_flow_shield",
        f"{label}_budget_{budget}ms_static_context",
        (
            "--repair5g5-selector-spec",
            str(selector_spec),
            "--repair5g-export-update-checkpoints-jsonl",
            str(checkpoint_jsonl),
            "--repair5g-checkpoint-topk-edges",
            "64",
            "--repair5g-checkpoint-edge-filter",
            "nonzero",
            "--repair5g-counterfactual-update-probe-jsonl",
            str(probe_jsonl),
            "--repair5g-counterfactual-candidates",
            ",".join(candidates),
            "--repair5g-counterfactual-short-budget-ms",
            str(int(budget)),
            "--repair5g-counterfactual-max-contexts",
            "1",
            "--repair5g-runtime-audit-mode",
            "perf",
        ),
    )


def run_probe(
    *,
    contexts: list[dict[str, Any]],
    candidates: list[str],
    log_dir: str,
    scenario_dir: str,
    scenario_metadata: str,
    results_csv: str,
    manifest: str,
    label: str,
    binary: Path,
    selector_spec: Path,
    source_scenario_dir: Path,
    overwrite: bool,
    max_workers: int,
    time_limit_sec: float,
    ltm_max_iterations: int,
) -> dict[str, Any]:
    root = repo_root()
    if max_workers != 1:
        return {"decision": "probe_not_run", "reason": "max_workers must be 1"}
    observed_id_guard([row["seed"] for row in contexts], label=label)
    log_path = resolve(log_dir, root)
    output_jsonl = log_path / f"{label}_runs.jsonl"
    command_log = log_path / f"{label}_commands.jsonl"
    update_log = log_path / f"{label}_ltm_updates.jsonl"
    probe_jsonl = log_path / f"{label}_update_probes.jsonl"
    checkpoint_jsonl = log_path / f"{label}_checkpoints.jsonl"
    results_path = resolve(results_csv, root)
    if overwrite:
        for path in [output_jsonl, command_log, update_log, probe_jsonl, checkpoint_jsonl, results_path]:
            path.unlink(missing_ok=True)
    if results_path.exists() and not overwrite:
        return {
            "decision": "probe_reused_existing_results",
            "results_csv": str(results_path),
            "raw_jsonl": str(probe_jsonl),
            "command_log_jsonl": str(command_log),
            "checkpoint_jsonl": str(checkpoint_jsonl),
        }
    completed: set[tuple[str, int, int, int]] = set()
    if probe_jsonl.exists() and not overwrite:
        grouped_existing: dict[tuple[str, int, int, int], set[str]] = defaultdict(set)
        for row in read_jsonl_tolerant(probe_jsonl):
            grouped_existing[
                (
                    str(row.get("map", "")),
                    int(finite_number(row.get("agents"), -1)),
                    int(finite_number(row.get("seed"), -1)),
                    int(finite_number(row.get("short_budget_ms"), -1)),
                )
            ].add(str(row.get("candidate_id", "")))
        required = set(candidates)
        completed = {key for key, seen in grouped_existing.items() if required <= seen}
    log_path.mkdir(parents=True, exist_ok=True)
    temp_dir = log_path / "_task_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    prepare_scenarios(
        root=root,
        source_scenario_dir=resolve(source_scenario_dir, root),
        scenario_dir=resolve(scenario_dir, root),
        scenario_metadata=resolve(scenario_metadata, root),
        maps=sorted({str(row["map"]) for row in contexts}),
        agent_counts=sorted({int(row["agents"]) for row in contexts}),
        instance_ids=sorted({int(row["seed"]) for row in contexts}),
    )
    for combo in contexts:
        for budget in PRIMARY_BUDGETS:
            if (str(combo["map"]), int(combo["agents"]), int(combo["seed"]), int(budget)) in completed:
                continue
            spec = method_spec_for_budget(
                budget=int(budget),
                selector_spec=resolve(selector_spec, root),
                probe_jsonl=probe_jsonl,
                checkpoint_jsonl=checkpoint_jsonl,
                candidates=candidates,
                label=label,
            )
            solver_rows, _updates, command_row = run_one_solver_task(
                root=root,
                binary=resolve(binary, root),
                scenario_dir=resolve(scenario_dir, root),
                temp_dir=temp_dir,
                update_log=update_log,
                map_name=str(combo["map"]),
                agents=int(combo["agents"]),
                seed=int(combo["seed"]),
                time_limit_sec=float(time_limit_sec),
                ltm_max_iterations=int(ltm_max_iterations),
                spec=spec,
                manifest=manifest,
            )
            for row in solver_rows:
                append_jsonl(output_jsonl, row)
            append_jsonl(command_log, command_row)
    expected_tasks = {
        (str(row["map"]), int(row["agents"]), int(row["seed"]), int(budget))
        for row in contexts
        for budget in PRIMARY_BUDGETS
    }
    write_deduped_probe_csv_from_jsonl(probe_jsonl, results_path, set(candidates), expected_tasks)
    return {
        "decision": "probe_ran",
        "results_csv": str(results_path),
        "raw_jsonl": str(probe_jsonl),
        "command_log_jsonl": str(command_log),
        "checkpoint_jsonl": str(checkpoint_jsonl),
    }


def read_jsonl_tolerant(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                rows.append(value)
    return rows


def flatten_probe_row(row: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, (dict, list)):
            flat[key] = json.dumps(value, sort_keys=True, separators=(",", ":"))
        else:
            flat[key] = value
    flat["normalized_context_key"] = context_key(row)
    return flat


def write_deduped_probe_csv_from_jsonl(
    jsonl_path: Path,
    csv_path: Path,
    candidates: set[str],
    expected_tasks: set[tuple[str, int, int, int]] | None = None,
) -> list[dict[str, Any]]:
    rows_by_key: dict[tuple[str, int, int, int, str], dict[str, Any]] = {}
    for row in read_jsonl_tolerant(jsonl_path):
        candidate = str(row.get("candidate_id", ""))
        if candidates and candidate not in candidates:
            continue
        task_key = (
            str(row.get("map", "")),
            int(finite_number(row.get("agents"), -1)),
            int(finite_number(row.get("seed"), -1)),
            int(finite_number(row.get("short_budget_ms"), -1)),
        )
        if expected_tasks is not None and task_key not in expected_tasks:
            continue
        key = (
            task_key[0],
            task_key[1],
            task_key[2],
            task_key[3],
            candidate,
        )
        flat = flatten_probe_row(row)
        old = rows_by_key.get(key)
        if old is None:
            rows_by_key[key] = flat
            continue
        old_quality = (1 if boolish(old.get("candidate_recognized")) else 0) + (1 if str(old.get("updateparams_fingerprint", "")).strip() else 0)
        new_quality = (1 if boolish(flat.get("candidate_recognized")) else 0) + (1 if str(flat.get("updateparams_fingerprint", "")).strip() else 0)
        if new_quality > old_quality:
            rows_by_key[key] = flat
    out = [rows_by_key[key] for key in sorted(rows_by_key)]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if out:
        fieldnames = sorted({key for row in out for key in row})
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(out)
    else:
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            handle.write("")
    return out


def main_run_full_primary_probe(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run G5.23 full-primary response-surface probe.")
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--time-limit-sec", type=float, default=5.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--max-contexts", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    root = repo_root()
    candidate_summary = load_json_if_exists(G523_CANDIDATE_SET_SUMMARY)
    if candidate_summary.get("decision") != "full_primary_candidate_set_created":
        summary = {"schema_version": "phase5p5_repair5g523_full_primary_probe_integrity_summary_v1", "decision": "full_primary_probe_not_run_candidate_set_failed", **G523_CLOSED_CLAIMS}
        write_json_file(G523_FULL_PRIMARY_INTEGRITY_SUMMARY, summary)
        write_text_file(G523_FULL_PRIMARY_INTEGRITY_REPORT, "# Repair5G.5.23 Full-Primary Probe Integrity\n\n- decision: `full_primary_probe_not_run_candidate_set_failed`\n")
        print(json.dumps({"decision": summary["decision"]}))
        return 2
    adapter = load_json_if_exists(G522_ADAPTER_SUMMARY)
    if adapter.get("decision") != "response_design_adapter_passed_continue_probe":
        summary = {"schema_version": "phase5p5_repair5g523_full_primary_probe_integrity_summary_v1", "decision": "full_primary_probe_not_run_adapter_failed", **G523_CLOSED_CLAIMS}
        write_json_file(G523_FULL_PRIMARY_INTEGRITY_SUMMARY, summary)
        write_text_file(G523_FULL_PRIMARY_INTEGRITY_REPORT, "# Repair5G.5.23 Full-Primary Probe Integrity\n\n- decision: `full_primary_probe_not_run_adapter_failed`\n")
        print(json.dumps({"decision": summary["decision"]}))
        return 2
    contexts = full_primary_contexts()
    if args.max_contexts and args.max_contexts > 0:
        contexts = contexts[: args.max_contexts]
    candidates = selected_candidate_ids()
    probe = run_probe(
        contexts=contexts,
        candidates=candidates,
        log_dir=G523_FULL_PRIMARY_LOG_DIR,
        scenario_dir=G523_FULL_PRIMARY_SCENARIO_DIR,
        scenario_metadata=G523_FULL_PRIMARY_SCENARIO_METADATA,
        results_csv=G523_FULL_PRIMARY_RESULTS_CSV,
        manifest="phase5p5-repair5g523-full-primary-response-surface",
        label="phase5p5_repair5g523_full_primary_response_surface",
        binary=args.binary,
        selector_spec=args.selector_spec_json,
        source_scenario_dir=args.source_scenario_dir,
        overwrite=args.overwrite,
        max_workers=args.max_workers,
        time_limit_sec=args.time_limit_sec,
        ltm_max_iterations=args.ltm_max_iterations,
    )
    result_rows = read_rows(G523_FULL_PRIMARY_RESULTS_CSV)
    flags = observed_id_flags(result_rows)
    budgets = sorted({int(finite_number(row.get("short_budget_ms"), -1)) for row in result_rows})
    contexts_seen = {str(row.get("normalized_context_key", "")) for row in result_rows}
    duplicate_rows = duplicate_context_candidate_budget_rows(result_rows)
    recognition = candidate_recognition_counts(result_rows, set(candidates))
    external_status = external_lacam2_solver_status(root)
    old_controls = old14_candidate_ids(root)
    retained_g518 = g518_retained_candidate_ids(limit=8)
    g522_selected = selected_g523_g522_ids()
    expected_rows = len(contexts) * len(candidates) * len(PRIMARY_BUDGETS)
    checkpoint_jsonl = Path(str(probe.get("checkpoint_jsonl", "")))
    command_log = Path(str(probe.get("command_log_jsonl", "")))
    gates = {
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "duplicate_context_candidate_budget_rows_eq_0": duplicate_rows == 0,
        "all_selected_candidates_recognized": recognition["candidate_recognized_all"],
        "old14_controls_present_every_context": candidate_presence_gate(result_rows, old_controls),
        "g518_retained_controls_present_every_context": candidate_presence_gate(result_rows, retained_g518),
        "g522_selected_controls_present_every_context": candidate_presence_gate(result_rows, g522_selected),
        "primary_budgets_present": budgets == PRIMARY_BUDGETS,
        "rows_in_expected_range": 4560 <= len(result_rows) <= 5520,
        "rows_eq_expected": len(result_rows) == expected_rows,
        "contexts_eq_60": len(contexts_seen) == len(contexts) == (60 if not args.max_contexts else len(contexts)),
        "candidate_count_le_46": len(candidates) <= 46,
        "raw_logs_and_command_jsonl_recorded": checkpoint_jsonl.exists() and command_log.exists(),
        "max_workers_eq_1": args.max_workers == 1,
        "external_lacam2_solver_untouched": not external_status,
    }
    decision = "full_primary_response_surface_probe_integrity_passed_continue_oracle" if all(gates.values()) else "full_primary_response_surface_probe_integrity_failed"
    summary = {
        "schema_version": "phase5p5_repair5g523_full_primary_probe_integrity_summary_v1",
        "decision": decision,
        "probe_run_decision": probe.get("decision", ""),
        "contexts_planned": len(contexts),
        "contexts_observed": len(contexts_seen),
        "candidate_count": len(candidates),
        "old14_candidate_count": len(old_controls),
        "g518_retained_candidate_count": len(retained_g518),
        "g522_selected_candidate_count": len(g522_selected),
        "budgets": budgets,
        "probe_rows": len(result_rows),
        "expected_rows": expected_rows,
        "duplicate_context_candidate_budget_rows": duplicate_rows,
        "recognition": recognition,
        "raw_jsonl": probe.get("raw_jsonl", ""),
        "command_log_jsonl": probe.get("command_log_jsonl", ""),
        "checkpoint_jsonl": probe.get("checkpoint_jsonl", ""),
        "results_csv": G523_FULL_PRIMARY_RESULTS_CSV,
        "external_lacam2_solver_status": external_status,
        "gates": gates,
        **flags,
        **G523_CLOSED_CLAIMS,
    }
    write_json_file(G523_FULL_PRIMARY_INTEGRITY_SUMMARY, summary)
    write_text_file(
        G523_FULL_PRIMARY_INTEGRITY_REPORT,
        "# Repair5G.5.23 Full-Primary Response-Surface Probe Integrity\n\n"
        f"- decision: `{decision}`\n"
        f"- contexts_observed: `{len(contexts_seen)}`\n"
        f"- candidate_count: `{len(candidates)}`\n"
        f"- probe_rows: `{len(result_rows)}`\n"
        f"- expected_rows: `{expected_rows}`\n"
        f"- duplicate_context_candidate_budget_rows: `{duplicate_rows}`\n"
        f"- gates: `{gates}`\n",
    )
    print(json.dumps({"decision": decision, "probe_rows": len(result_rows), "contexts": len(contexts_seen)}))
    return 0 if decision.endswith("continue_oracle") else 2


def analyze_oracle_from_rows(
    *,
    rows: list[dict[str, Any]],
    integrity_decision: str,
    g522_ids: set[str],
    oracle_by_context_csv: str,
    candidate_distribution_csv: str,
    region_counts_csv: str,
    failure_counts_csv: str,
    report_path: str,
    summary_path: str,
    schema_prefix: str,
) -> int:
    root = repo_root()
    if not integrity_decision.endswith("continue_oracle"):
        summary = {"schema_version": f"{schema_prefix}_summary_v1", "decision": "oracle_not_run_integrity_failed", **G523_CLOSED_CLAIMS}
        write_json_file(summary_path, summary)
        write_text_file(report_path, f"# {schema_prefix} Oracle\n\n- decision: `oracle_not_run_integrity_failed`\n")
        print(json.dumps({"decision": summary["decision"]}))
        return 2
    old_ids = set(old14_candidate_ids(root))
    g518_ids = set(g518_retained_candidate_ids(limit=8))
    old_g518 = old_ids | g518_ids
    full = old_g518 | g522_ids
    meta = candidate_metadata()
    by_cb = rows_by_context_budget(rows)
    oracle_rows = []
    gaps = []
    gaps_old14 = []
    gaps_g518 = []
    safe_win_pairs = 0
    safe_win_contexts: set[str] = set()
    win_pairs = 0
    win_contexts: set[str] = set()
    induced_count = 0
    recovery_count = 0
    budget_sensitive = 0
    finite_pairwise_gain = []
    region_wins = Counter()
    region_failures = Counter()
    family_wins = Counter()
    map_agent_wins = Counter()
    candidate_wins = Counter()
    fixed_scores: dict[str, list[float]] = defaultdict(list)
    guarded_gaps = []
    winners_by_context: dict[str, list[str]] = defaultdict(list)
    for (context, budget), group in sorted(by_cb.items()):
        static = best_of(group, {STATIC_FLOW_SHIELD_CANDIDATE})
        additive = best_of(group, {ADDITIVE_CANDIDATE})
        old14 = best_of(group, old_ids)
        g518 = best_of(group, g518_ids)
        old_g518_best = best_of(group, old_g518)
        g522_best = best_of(group, g522_ids)
        full_best = best_of(group, full)
        first = group[0]
        full_id = str((full_best or {}).get("candidate_id", ""))
        winners_by_context[context].append(full_id)
        for row in group:
            cid = str(row.get("candidate_id", ""))
            if cid in g522_ids and finite_solution(row):
                fixed_scores[cid].append(score(row))
            if cid in g522_ids:
                induced = finite_solution(static) and not finite_solution(row)
                recovery = (not finite_solution(static)) and finite_solution(row)
                induced_count += 1 if induced else 0
                recovery_count += 1 if recovery else 0
                if induced:
                    region_failures[str(meta.get(cid, {}).get("candidate_region", ""))] += 1
                d = finite_delta(row, old_g518_best)
                if math.isfinite(d):
                    finite_pairwise_gain.append(d)
        if finite_solution(full_best) and finite_solution(old_g518_best):
            gaps.append(score(full_best) - score(old_g518_best))
        if finite_solution(full_best) and finite_solution(old14):
            gaps_old14.append(score(full_best) - score(old14))
        if finite_solution(full_best) and finite_solution(g518):
            gaps_g518.append(score(full_best) - score(g518))
        is_g522 = full_id in g522_ids
        safe = is_g522 and not (finite_solution(static) and not finite_solution(full_best))
        if is_g522:
            win_pairs += 1
            win_contexts.add(context)
            candidate_wins[full_id] += 1
            region = str(meta.get(full_id, {}).get("candidate_region", "g522_unknown"))
            region_wins[region] += 1
            family_wins[str(first.get("map", "")).split("-", 1)[0]] += 1
            map_agent_wins[f"{first.get('map')}|a{first.get('agents')}"] += 1
        if safe:
            safe_win_pairs += 1
            safe_win_contexts.add(context)
        guarded = full_best if safe else old_g518_best
        if finite_solution(guarded) and finite_solution(old_g518_best):
            guarded_gaps.append(score(guarded) - score(old_g518_best))
        oracle_rows.append(
            {
                "normalized_context_key": context,
                "map": first.get("map", ""),
                "agents": first.get("agents", ""),
                "seed": first.get("seed", ""),
                "map_family": str(first.get("map", "")).split("-", 1)[0],
                "map_agent_group": f"{first.get('map')}|a{first.get('agents')}",
                "short_budget_ms": budget,
                "static_score": csv_number(score(static)),
                "additive_score": csv_number(score(additive)),
                "old14_oracle_candidate": (old14 or {}).get("candidate_id", ""),
                "old14_oracle_score": csv_number(score(old14)),
                "g518_retained_oracle_candidate": (g518 or {}).get("candidate_id", ""),
                "g518_retained_oracle_score": csv_number(score(g518)),
                "old14_plus_g518_oracle_candidate": (old_g518_best or {}).get("candidate_id", ""),
                "old14_plus_g518_oracle_score": csv_number(score(old_g518_best)),
                "selected_g522_oracle_candidate": (g522_best or {}).get("candidate_id", ""),
                "selected_g522_oracle_score": csv_number(score(g522_best)),
                "mixed_oracle_candidate": full_id,
                "mixed_oracle_score": csv_number(score(full_best)),
                "avoidable_risk_guarded_oracle_candidate": (guarded or {}).get("candidate_id", ""),
                "avoidable_risk_guarded_oracle_score": csv_number(score(guarded)),
                "g522_oracle_winner": is_g522,
                "safe_g522_oracle_winner": safe,
                "incremental_gap_vs_old14_plus_g518": csv_number(finite_delta(full_best, old_g518_best)),
                "guarded_gap_vs_old14_plus_g518": csv_number(finite_delta(guarded, old_g518_best)),
                **G523_CLOSED_CLAIMS,
            }
        )
    by_cc = rows_by_context_candidate(rows)
    distribution = []
    for cid in sorted(g522_ids):
        group = [row for row in rows if row.get("candidate_id") == cid]
        finite_rows = [row for row in group if finite_solution(row)]
        flags = []
        for (_context, candidate), crows in by_cc.items():
            if candidate == cid:
                finite_flags = [finite_solution(row) for row in crows]
                if len(set(finite_flags)) > 1:
                    budget_sensitive += 1
                    flags.append(True)
        distribution.append(
            {
                "candidate_id": cid,
                "candidate_region": meta.get(cid, {}).get("candidate_region", ""),
                "candidate_family": meta.get(cid, {}).get("candidate_family", ""),
                "rows": len(group),
                "finite_rows": len(finite_rows),
                "oracle_win_count": candidate_wins[cid],
                "candidate_induced_no_solution_count": sum(1 for row in group if not finite_solution(row)),
                "budget_sensitive_candidate_failure_count": len(flags),
                "mean_score": csv_number(mean([score(row) for row in finite_rows])),
                **numeric_candidate_param_dict(cid),
                **G523_CLOSED_CLAIMS,
            }
        )
    region_rows = [
        {"candidate_region": region, "safe_win_budget_pairs": count, "failure_rows": region_failures[region], **G523_CLOSED_CLAIMS}
        for region, count in sorted(region_wins.items())
    ]
    failure_rows = [
        {"failure_kind": "candidate_induced_no_solution", "count": induced_count, **G523_CLOSED_CLAIMS},
        {"failure_kind": "static_failure_candidate_recovers", "count": recovery_count, **G523_CLOSED_CLAIMS},
        {"failure_kind": "budget_sensitive_candidate_failure", "count": budget_sensitive, **G523_CLOSED_CLAIMS},
    ]
    best_fixed = min(((mean(vals), cid) for cid, vals in fixed_scores.items() if vals), default=(math.inf, ""))
    stable_contexts = sum(1 for winners in winners_by_context.values() if winners and len(set(winners)) == 1)
    budget_stability = stable_contexts / len(winners_by_context) if winners_by_context else 0.0
    incremental_gap = mean(gaps)
    gate = (math.isfinite(incremental_gap) and incremental_gap <= -0.003) or len(safe_win_contexts) >= 8 or safe_win_pairs >= 12
    summary = {
        "schema_version": f"{schema_prefix}_summary_v1",
        "decision": "full_primary_response_surface_oracle_completed" if schema_prefix.endswith("full_primary_response_surface_oracle") else "static_recovery_oracle_completed",
        "full_primary_compatible": gate if schema_prefix.endswith("full_primary_response_surface_oracle") else False,
        "candidate_space_full_primary_gate_passed": gate,
        "contexts": len(winners_by_context),
        "budget_pairs": len(oracle_rows),
        "incremental_oracle_gap_vs_old14_plus_g518": incremental_gap,
        "mean_oracle_gap_vs_old14": mean(gaps_old14),
        "mean_oracle_gap_vs_g518_retained": mean(gaps_g518),
        "safe_g522_win_contexts": len(safe_win_contexts),
        "safe_g522_win_budget_pairs": safe_win_pairs,
        "g522_win_contexts_by_map_family": dict(sorted(family_wins.items())),
        "g522_win_contexts_by_map_agent": dict(sorted(map_agent_wins.items())),
        "candidate_induced_no_solution_count": induced_count,
        "budget_sensitive_candidate_failure_count": budget_sensitive,
        "static_failure_candidate_recovers_count": recovery_count,
        "finite_pairwise_solution_quality_gain": mean(finite_pairwise_gain),
        "budget_stability_1000_2000": budget_stability,
        "dominant_g522_candidates": dict(candidate_wins.most_common(10)),
        "dominant_old14_g518_controls": dict(Counter(row.get("old14_plus_g518_oracle_candidate", "") for row in oracle_rows).most_common(10)),
        "region_win_counts": dict(sorted(region_wins.items())),
        "region_failure_counts": dict(sorted(region_failures.items())),
        "best_fixed_g522_candidate": best_fixed[1],
        "best_fixed_g522_mean_score": csv_number(best_fixed[0]),
        "avoidable_risk_guarded_gap_vs_old14_plus_g518": mean(guarded_gaps),
        **G523_CLOSED_CLAIMS,
    }
    write_rows(oracle_by_context_csv, oracle_rows)
    write_rows(candidate_distribution_csv, distribution)
    write_rows(region_counts_csv, region_rows)
    write_rows(failure_counts_csv, failure_rows)
    write_json_file(summary_path, summary)
    write_text_file(
        report_path,
        "# Repair5G.5.23 Full-Primary Response-Surface Oracle\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- candidate_space_full_primary_gate_passed: `{gate}`\n"
        f"- contexts: `{summary['contexts']}`\n"
        f"- budget_pairs: `{summary['budget_pairs']}`\n"
        f"- incremental_oracle_gap_vs_old14_plus_g518: `{csv_number(incremental_gap)}`\n"
        f"- safe_g522_win_contexts: `{len(safe_win_contexts)}`\n"
        f"- safe_g522_win_budget_pairs: `{safe_win_pairs}`\n"
        f"- candidate_induced_no_solution_count: `{induced_count}`\n"
        f"- static_failure_candidate_recovers_count: `{recovery_count}`\n"
        f"- budget_stability_1000_2000: `{csv_number(budget_stability)}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "gate": gate, "safe_contexts": len(safe_win_contexts)}))
    return 0


def main_analyze_full_primary_oracle(argv: list[str] | None = None) -> int:
    _parser = argparse.ArgumentParser(description="Analyze G5.23 full-primary response-surface oracle.")
    _parser.parse_args(argv)
    integrity = load_json_if_exists(G523_FULL_PRIMARY_INTEGRITY_SUMMARY)
    return analyze_oracle_from_rows(
        rows=read_rows(G523_FULL_PRIMARY_RESULTS_CSV),
        integrity_decision=str(integrity.get("decision", "")),
        g522_ids=set(selected_g523_g522_ids()),
        oracle_by_context_csv=G523_FULL_PRIMARY_ORACLE_BY_CONTEXT_CSV,
        candidate_distribution_csv=G523_FULL_PRIMARY_CANDIDATE_DISTRIBUTION_CSV,
        region_counts_csv=G523_FULL_PRIMARY_REGION_COUNTS_CSV,
        failure_counts_csv=G523_FULL_PRIMARY_FAILURE_COUNTS_CSV,
        report_path=G523_FULL_PRIMARY_ORACLE_REPORT,
        summary_path=G523_FULL_PRIMARY_ORACLE_SUMMARY,
        schema_prefix="phase5p5_repair5g523_full_primary_response_surface_oracle",
    )


def main_mine_static_recovery(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mine static-recovery contexts for G5.23.")
    parser.parse_args(argv)
    g521_rows = read_rows("outputs/tables/phase5p5_repair5g521_avoidable_failure_semantics.csv")
    g522_contexts = {row.get("normalized_context_key", "") for row in read_rows(G522_CONTEXT_PANEL_CSV)}
    rows = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in g521_rows:
        if row.get("row_scope") != "primary_pair":
            continue
        if boolish(row.get("candidate_recovers_static_no_solution_primary")):
            grouped[str(row.get("normalized_context_key", ""))].append(row)
    for context, crows in sorted(grouped.items()):
        first = crows[0]
        stable = sum(1 for row in crows if not boolish(row.get("budget_sensitive_candidate_failure")))
        old14 = sum(1 for row in crows if boolish(row.get("is_old14_candidate")))
        g518 = sum(1 for row in crows if boolish(row.get("is_new_candidate")))
        reliable = stable >= 1 and not boolish(first.get("unavoidable_context_failure_primary"))
        rows.append(
            {
                "normalized_context_key": context,
                "map": first.get("map", ""),
                "agents": first.get("agents", ""),
                "seed": first.get("seed", ""),
                "iteration": first.get("iteration", ""),
                "traffic_before_hash_full": first.get("traffic_before_hash_full", ""),
                "map_family": first.get("map_family", map_family(str(first.get("map", "")))),
                "map_agent_group": first.get("map_agent_group", f"{first.get('map')}|a{first.get('agents')}"),
                "static_failed_candidate_finite": True,
                "static_failed_old14_recovers": old14 > 0,
                "static_failed_g518_recovers": g518 > 0,
                "static_failed_g522_recovers": False,
                "static_failed_only_old14_recovers": old14 > 0 and g518 == 0,
                "static_failed_only_new_recovers": g518 > 0 and old14 == 0,
                "recovery_budget_stability": csv_number(stable / max(1, len(crows))),
                "recovery_candidate_rows": len(crows),
                "measured_by_g522_targeted": context in g522_contexts,
                "reliable_recovery_context": reliable,
                **G523_CLOSED_CLAIMS,
            }
        )
    reliable_not_g522 = [row for row in rows if boolish(row.get("reliable_recovery_context")) and not boolish(row.get("measured_by_g522_targeted"))]
    selected = reliable_not_g522[:12]
    run_needed = len(reliable_not_g522) >= 4
    summary_rows = [
        {"group": "all_candidate_level_recovery_contexts", "contexts": len(rows), **G523_CLOSED_CLAIMS},
        {"group": "reliable_context_level_recovery_contexts", "contexts": sum(1 for row in rows if boolish(row.get("reliable_recovery_context"))), **G523_CLOSED_CLAIMS},
        {"group": "reliable_not_measured_by_g522", "contexts": len(reliable_not_g522), **G523_CLOSED_CLAIMS},
        {"group": "selected_for_probe_if_needed", "contexts": len(selected), **G523_CLOSED_CLAIMS},
    ]
    summary = {
        "schema_version": "phase5p5_repair5g523_static_recovery_mining_summary_v1",
        "decision": "static_recovery_contexts_mined",
        "candidate_level_recovery_contexts": len(rows),
        "reliable_context_level_recovery_contexts": sum(1 for row in rows if boolish(row.get("reliable_recovery_context"))),
        "reliable_recovery_contexts_not_measured_by_g522": len(reliable_not_g522),
        "selected_recovery_contexts": len(selected),
        "run_recovery_probe_needed": run_needed,
        "no_reliable_context_reason": "" if run_needed else "G5.21 recovery rows were candidate-level or already covered, not enough reliable context-level positives outside G5.22.",
        **G523_CLOSED_CLAIMS,
    }
    write_rows(G523_RECOVERY_CONTEXTS_CSV, selected if selected else rows)
    write_rows(G523_RECOVERY_CONTEXT_SUMMARY_CSV, summary_rows)
    write_json_file(G523_RECOVERY_SUMMARY, summary)
    write_text_file(
        G523_RECOVERY_REPORT,
        "# Repair5G.5.23 Static-Recovery Mining\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- candidate_level_recovery_contexts: `{len(rows)}`\n"
        f"- reliable_context_level_recovery_contexts: `{summary['reliable_context_level_recovery_contexts']}`\n"
        f"- reliable_recovery_contexts_not_measured_by_g522: `{len(reliable_not_g522)}`\n"
        f"- run_recovery_probe_needed: `{run_needed}`\n"
        f"- no_reliable_context_reason: `{summary['no_reliable_context_reason']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "run_needed": run_needed, "selected": len(selected)}))
    return 0


def main_run_static_recovery_probe(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run G5.23 static-recovery probe if needed.")
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--time-limit-sec", type=float, default=5.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    mining = load_json_if_exists(G523_RECOVERY_SUMMARY)
    if not boolish(mining.get("run_recovery_probe_needed")):
        summary = {
            "schema_version": "phase5p5_repair5g523_static_recovery_probe_summary_v1",
            "decision": "static_recovery_probe_skipped_not_needed",
            "probe_ran": False,
            "skip_reason": mining.get("no_reliable_context_reason", "not enough reliable recovery contexts"),
            **G523_CLOSED_CLAIMS,
        }
        write_json_file(G523_RECOVERY_PROBE_SUMMARY, summary)
        write_rows(G523_RECOVERY_RESULTS_CSV, [])
        write_rows(G523_RECOVERY_ORACLE_CSV, [])
        write_text_file(G523_RECOVERY_PROBE_REPORT, "# Repair5G.5.23 Static-Recovery Probe\n\n- decision: `static_recovery_probe_skipped_not_needed`\n")
        print(json.dumps({"decision": summary["decision"]}))
        return 0
    contexts = []
    for row in read_rows(G523_RECOVERY_CONTEXTS_CSV)[:12]:
        contexts.append(
            {
                "normalized_context_key": row.get("normalized_context_key", ""),
                "map": row.get("map", ""),
                "agents": int(finite_number(row.get("agents"), 0)),
                "seed": int(finite_number(row.get("seed"), 0)),
                "iteration": int(finite_number(row.get("iteration"), 0)),
            }
        )
    meta = candidate_metadata()
    recovery_g522 = [
        cid for cid in selected_g523_g522_ids()
        if str(meta.get(cid, {}).get("candidate_region", "")) == "B_static_recovery_feasibility"
    ][:8]
    if len(recovery_g522) < 4:
        recovery_g522 = selected_g523_g522_ids()[:8]
    candidates = old14_candidate_ids(repo_root()) + g518_retained_candidate_ids(limit=8) + recovery_g522
    probe = run_probe(
        contexts=contexts,
        candidates=candidates,
        log_dir=G523_RECOVERY_LOG_DIR,
        scenario_dir=G523_RECOVERY_SCENARIO_DIR,
        scenario_metadata=G523_RECOVERY_SCENARIO_METADATA,
        results_csv=G523_RECOVERY_RESULTS_CSV,
        manifest="phase5p5-repair5g523-static-recovery",
        label="phase5p5_repair5g523_static_recovery",
        binary=args.binary,
        selector_spec=args.selector_spec_json,
        source_scenario_dir=args.source_scenario_dir,
        overwrite=args.overwrite,
        max_workers=args.max_workers,
        time_limit_sec=args.time_limit_sec,
        ltm_max_iterations=args.ltm_max_iterations,
    )
    rows = read_rows(G523_RECOVERY_RESULTS_CSV)
    flags = observed_id_flags(rows)
    duplicate_rows = duplicate_context_candidate_budget_rows(rows)
    recovery_g522_set = set(recovery_g522)
    oracle_tmp = analyze_oracle_from_rows(
        rows=rows,
        integrity_decision="static_recovery_probe_integrity_passed_continue_oracle",
        g522_ids=recovery_g522_set,
        oracle_by_context_csv=G523_RECOVERY_ORACLE_CSV,
        candidate_distribution_csv="outputs/tables/phase5p5_repair5g523_static_recovery_candidate_distribution.csv",
        region_counts_csv="outputs/tables/phase5p5_repair5g523_static_recovery_region_counts.csv",
        failure_counts_csv="outputs/tables/phase5p5_repair5g523_static_recovery_failure_counts.csv",
        report_path="outputs/reports/phase5p5_repair5g523_static_recovery_oracle.md",
        summary_path="outputs/reports/phase5p5_repair5g523_static_recovery_oracle_summary.json",
        schema_prefix="phase5p5_repair5g523_static_recovery_oracle",
    )
    summary = {
        "schema_version": "phase5p5_repair5g523_static_recovery_probe_summary_v1",
        "decision": "static_recovery_probe_completed",
        "probe_ran": True,
        "contexts": len({row.get("normalized_context_key", "") for row in rows}),
        "candidate_count": len(candidates),
        "probe_rows": len(rows),
        "duplicate_context_candidate_budget_rows": duplicate_rows,
        "raw_jsonl": probe.get("raw_jsonl", ""),
        "command_log_jsonl": probe.get("command_log_jsonl", ""),
        "checkpoint_jsonl": probe.get("checkpoint_jsonl", ""),
        "oracle_return_code": oracle_tmp,
        **flags,
        **G523_CLOSED_CLAIMS,
    }
    write_json_file(G523_RECOVERY_PROBE_SUMMARY, summary)
    write_text_file(
        G523_RECOVERY_PROBE_REPORT,
        "# Repair5G.5.23 Static-Recovery Probe\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- contexts: `{summary['contexts']}`\n"
        f"- candidate_count: `{len(candidates)}`\n"
        f"- probe_rows: `{len(rows)}`\n"
        f"- duplicate_context_candidate_budget_rows: `{duplicate_rows}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "probe_rows": len(rows)}))
    return 0


def runtime_safe_feature_columns(row: dict[str, Any]) -> list[str]:
    prefixes = (
        "feature_map_",
        "feature_agent_",
        "feature_iteration_",
        "feature_trace_",
        "feature_rich_",
        "feature_candidate_param_",
        "feature_candidate_geometry_",
        "feature_nearest_old14_",
        "feature_nearest_g518_",
        "feature_region_prior_",
        "feature_context_bucket_prior_",
        "feature_interaction_runtime_",
    )
    cols = [key for key in row if key.startswith(prefixes)]
    leak = leakage_scan(cols)
    return [col for col in cols if col not in set(leak["forbidden_features"])]


def context_bucket_for_context(context: str, first: dict[str, Any]) -> str:
    family = str(first.get("map", "")).split("-", 1)[0]
    if family == "warehouse":
        return "metadata_warehouse_control"
    if int(finite_number(first.get("agents"), 0)) >= 100:
        return "metadata_dense_primary"
    return "metadata_regular_primary"


def create_teacher_from_sources() -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    full_integrity = load_json_if_exists(G523_FULL_PRIMARY_INTEGRITY_SUMMARY)
    full_ok = full_integrity.get("decision") == "full_primary_response_surface_probe_integrity_passed_continue_oracle"
    source_rows = read_rows(G523_FULL_PRIMARY_RESULTS_CSV) if full_ok else read_rows(G522_PROBE_RESULTS_CSV)
    source_label = "g523_full_primary_plus_g522_targeted" if full_ok else "g522_targeted_fallback"
    recovery_summary = load_json_if_exists(G523_RECOVERY_PROBE_SUMMARY)
    recovery_rows = read_rows(G523_RECOVERY_RESULTS_CSV) if boolish(recovery_summary.get("probe_ran")) else []
    all_rows = source_rows + recovery_rows
    return all_rows, {"full_primary_compatible": boolish(load_json_if_exists(G523_FULL_PRIMARY_ORACLE_SUMMARY).get("candidate_space_full_primary_gate_passed")), "source_label": source_label, "recovery_rows": len(recovery_rows)}, recovery_rows


def main_create_leakage_free_teacher(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create leakage-free G5.23 teacher dataset v2.")
    parser.parse_args(argv)
    rows, source_meta, _recovery_rows = create_teacher_from_sources()
    root = repo_root()
    old_ids = set(old14_candidate_ids(root))
    g518_ids = set(g518_retained_candidate_ids(limit=8))
    g522_ids = set(selected_g523_g522_ids()) or set(selected_g522_candidate_ids(include_probe_only=True))
    old_g518 = old_ids | g518_ids
    meta = candidate_metadata()
    by_context = rows_by_context(rows)
    by_cc = rows_by_context_candidate(rows)
    context_table = []
    candidate_table = []
    pairwise_table = []
    oracle_candidate_by_context: dict[str, str] = {}
    for context, group in sorted(by_context.items()):
        first = group[0]
        bucket = context_bucket_for_context(context, first)
        old_g518_best_by_budget = {budget: best_of(rows2, old_g518) for (ctx, budget), rows2 in rows_by_context_budget(group).items() if ctx == context}
        full_best = best_of(group, old_g518 | g522_ids)
        old_g518_best = best_of(group, old_g518)
        oracle_candidate_by_context[context] = str((full_best or {}).get("candidate_id", ""))
        context_rows = []
        for (ctx, cid), crows in sorted(by_cc.items()):
            if ctx != context:
                continue
            params = numeric_candidate_param_dict(cid, "feature_candidate_param_")
            nearest_g518 = finite_number(meta.get(cid, {}).get("nearest_g518_distance"), 0.0)
            nearest_old = finite_number(meta.get(cid, {}).get("nearest_old14_distance"), 0.0)
            role = candidate_role(cid, old_ids, g518_ids, set(), g522_ids)
            finite_scores = [score(row) for row in crows if finite_solution(row)]
            deltas = []
            for row in crows:
                base = old_g518_best_by_budget.get(int(finite_number(row.get("short_budget_ms"), -1)))
                if finite_solution(row) and finite_solution(base):
                    deltas.append(score(row) - score(base))
            induced = any(finite_solution(best_of([r for r in group if int(finite_number(r.get("short_budget_ms"), -1)) == int(finite_number(row.get("short_budget_ms"), -1))], {STATIC_FLOW_SHIELD_CANDIDATE})) and not finite_solution(row) for row in crows)
            recovery = any((not finite_solution(best_of([r for r in group if int(finite_number(r.get("short_budget_ms"), -1)) == int(finite_number(row.get("short_budget_ms"), -1))], {STATIC_FLOW_SHIELD_CANDIDATE}))) and finite_solution(row) for row in crows)
            budget_sensitive = len(set(finite_solution(row) for row in crows)) > 1
            target_delta = mean(deltas)
            safe_positive = role == "g522_response_surface" and math.isfinite(target_delta) and target_delta <= -0.001 and not induced
            crow = {
                "normalized_context_key": context,
                "map": first.get("map", ""),
                "agents": first.get("agents", ""),
                "seed": first.get("seed", ""),
                "iteration": first.get("iteration", ""),
                "traffic_before_hash_full": first.get("traffic_before_hash_full", ""),
                "candidate_id": cid,
                "candidate_role": role,
                "audit_context_bucket": bucket,
                "audit_candidate_region": meta.get(cid, {}).get("candidate_region", role),
                "audit_candidate_family": meta.get(cid, {}).get("candidate_family", role),
                "feature_map_family_hash": float(abs(hash(str(first.get("map", "")).split("-", 1)[0])) % 997) / 997.0,
                "feature_map_agent_group_hash": float(abs(hash(f"{first.get('map')}|{first.get('agents')}")) % 997) / 997.0,
                "feature_agent_count": finite_number(first.get("agents"), 0.0),
                "feature_iteration_index": finite_number(first.get("iteration"), 0.0),
                "feature_trace_budget_count": len(crows),
                "feature_rich_candidate_count_context": len({r.get("candidate_id", "") for r in group}),
                "feature_candidate_geometry_nearest_g518": nearest_g518,
                "feature_candidate_geometry_nearest_old14": nearest_old,
                "feature_nearest_g518_distance": nearest_g518,
                "feature_nearest_old14_distance": nearest_old,
                "feature_region_prior_hash": float(abs(hash(str(meta.get(cid, {}).get("candidate_region", role)))) % 997) / 997.0,
                "feature_context_bucket_prior_metadata": float(abs(hash(bucket)) % 997) / 997.0,
                "feature_interaction_runtime_agent_x_beta": finite_number(first.get("agents"), 0.0) * finite_number(params.get("feature_candidate_param_flow_shield_beta"), 0.0),
                **params,
                "target_candidate_utility_delta_vs_old14_plus_g518": csv_number(target_delta),
                "target_safe_positive": safe_positive,
                "label_candidate_oracle_rank": "",
                "outcome_solution_found_all_budgets": all(finite_solution(row) for row in crows),
                "outcome_candidate_induced_no_solution": induced,
                "outcome_budget_sensitive_candidate_failure": budget_sensitive,
                "outcome_static_failure_candidate_recovers": recovery,
                "audit_candidate_mean_result": csv_number(mean(finite_scores)),
                **G523_CLOSED_CLAIMS,
            }
            context_rows.append(crow)
            candidate_table.append(crow)
        ranked = sorted(context_rows, key=lambda row: (finite_number(row.get("audit_candidate_mean_result"), math.inf), str(row.get("candidate_id", ""))))
        for idx, row in enumerate(ranked):
            row["label_candidate_oracle_rank"] = idx + 1
        safe = [row for row in ranked if boolish(row.get("target_safe_positive"))]
        best = safe[0] if safe else (ranked[0] if ranked else {})
        context_table.append(
            {
                "normalized_context_key": context,
                "map": first.get("map", ""),
                "map_family": str(first.get("map", "")).split("-", 1)[0],
                "agents": first.get("agents", ""),
                "seed": first.get("seed", ""),
                "iteration": first.get("iteration", ""),
                "traffic_before_hash_full": first.get("traffic_before_hash_full", ""),
                "audit_context_bucket": bucket,
                "feature_map_family_hash": float(abs(hash(str(first.get("map", "")).split("-", 1)[0])) % 997) / 997.0,
                "feature_map_agent_group_hash": float(abs(hash(f"{first.get('map')}|{first.get('agents')}")) % 997) / 997.0,
                "feature_agent_count": finite_number(first.get("agents"), 0.0),
                "feature_iteration_index": finite_number(first.get("iteration"), 0.0),
                "feature_trace_candidate_count": len({r.get("candidate_id", "") for r in group}),
                "feature_rich_budget_count": len({r.get("short_budget_ms", "") for r in group}),
                "target_has_safe_param_gain": bool(safe),
                "target_has_static_recovery": any(boolish(row.get("outcome_static_failure_candidate_recovers")) for row in ranked),
                "target_has_candidate_induced_failure_boundary": any(boolish(row.get("outcome_candidate_induced_no_solution")) for row in ranked),
                "oracle_best_candidate_id": best.get("candidate_id", ""),
                "oracle_best_candidate_family": best.get("audit_candidate_family", ""),
                "audit_fallback_recommended": not bool(safe),
                **G523_CLOSED_CLAIMS,
            }
        )
        capped = [row for row in ranked[:12] if row.get("candidate_role") in {"old14", "g518_retained", "g522_response_surface"}]
        for i, left in enumerate(capped):
            for right in capped[i + 1 : min(i + 7, len(capped))]:
                li = finite_number(left.get("audit_candidate_mean_result"), math.inf)
                rj = finite_number(right.get("audit_candidate_mean_result"), math.inf)
                pairwise_table.append(
                    {
                        "normalized_context_key": context,
                        "candidate_i": left.get("candidate_id", ""),
                        "candidate_j": right.get("candidate_id", ""),
                        "target_candidate_i_preferred_over_j": li < rj,
                        "target_preference_margin": csv_number(rj - li),
                        "label_both_safe": boolish(left.get("target_safe_positive")) and boolish(right.get("target_safe_positive")),
                        "audit_i_role": left.get("candidate_role", ""),
                        "audit_j_role": right.get("candidate_role", ""),
                        **G523_CLOSED_CLAIMS,
                    }
                )
    edge_rows = []
    full_integrity = load_json_if_exists(G523_FULL_PRIMARY_INTEGRITY_SUMMARY)
    checkpoint_path = Path(str(full_integrity.get("checkpoint_jsonl", "")))
    if not checkpoint_path.is_absolute():
        checkpoint_path = repo_root() / checkpoint_path
    if checkpoint_path.exists():
        for row in read_jsonl_tolerant(checkpoint_path):
            context = str(row.get("normalized_context_key", "") or f"{row.get('map')}|a{row.get('agents')}|s{row.get('seed')}|it{row.get('iteration')}|{row.get('traffic_before_hash_full')}")
            oracle_cid = oracle_candidate_by_context.get(context, "")
            params = candidate_params(oracle_cid)
            beta = params.flow_shield_beta if params else 0.0
            for edge in row.get("traffic_after_edges", [])[:64]:
                c_weight = finite_number(edge.get("c_weight"), 0.0)
                f_weight = finite_number(edge.get("f_weight"), 0.0)
                edge_rows.append(
                    {
                        "normalized_context_key": context,
                        "map": row.get("map", ""),
                        "agents": row.get("agents", ""),
                        "seed": row.get("seed", ""),
                        "iteration": row.get("iteration", ""),
                        "edge_from_id": edge.get("from_id", ""),
                        "edge_to_id": edge.get("to_id", ""),
                        "feature_trace_c_raw": finite_number(edge.get("c_raw"), 0.0),
                        "feature_trace_f_raw": finite_number(edge.get("f_raw"), 0.0),
                        "feature_rich_c_weight_before": c_weight,
                        "feature_rich_f_weight_before": f_weight,
                        "oracle_safe_candidate_id": oracle_cid,
                        "oracle_parameterized_update_proxy": csv_number(c_weight - beta * f_weight),
                        "audit_additive_ltm_proxy": c_weight,
                        "target_edge_residual_vs_additive": csv_number(-beta * f_weight),
                        "target_edge_oracle_dual_channel_update": csv_number(c_weight - beta * f_weight),
                        "audit_edge_proxy_type": "oracle_parameterized_update_proxy",
                        **G523_CLOSED_CLAIMS,
                    }
                )
    if not edge_rows:
        write_text_file(G523_TEACHER_EDGE_BLOCKER, "# Repair5G.5.23 Edge/Update Teacher Blocker\n\n- blocker: `edge_update_teacher_unavailable_missing_checkpoint_fields`\n")
    feature_cols = sorted({key for row in context_table + candidate_table + edge_rows for key in row if key.startswith("feature_")})
    leak = leakage_scan(feature_cols)
    summary = {
        "schema_version": "phase5p5_repair5g523_leakage_free_teacher_dataset_summary_v1",
        "decision": "leakage_free_teacher_dataset_v2_created" if leak["forbidden_feature_count"] == 0 else "leakage_free_teacher_dataset_v2_failed_leakage_scan",
        "context_rows": len(context_table),
        "candidate_rows": len(candidate_table),
        "pairwise_rows": len(pairwise_table),
        "edge_update_rows_or_blocker": len(edge_rows) if edge_rows else "edge_update_teacher_unavailable_missing_checkpoint_fields",
        "safe_positive_candidate_rows": sum(1 for row in candidate_table if boolish(row.get("target_safe_positive"))),
        "candidate_induced_failure_rows": sum(1 for row in candidate_table if boolish(row.get("outcome_candidate_induced_no_solution"))),
        "static_recovery_rows": sum(1 for row in candidate_table if boolish(row.get("outcome_static_failure_candidate_recovers"))),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "runtime_safe_feature_count": len(feature_cols) - leak["forbidden_feature_count"],
        "source_label": source_meta["source_label"],
        "full_primary_compatible": source_meta["full_primary_compatible"],
        **G523_CLOSED_CLAIMS,
    }
    manifest = {**summary, "tables": {"context_teacher_v2": G523_TEACHER_CONTEXT_CSV, "candidate_teacher_v2": G523_TEACHER_CANDIDATE_CSV, "pairwise_teacher_v2": G523_TEACHER_PAIRWISE_CSV, "edge_update_teacher_v2": G523_TEACHER_EDGE_CSV}, **G523_CLOSED_CLAIMS}
    write_rows(G523_TEACHER_CONTEXT_CSV, context_table)
    write_rows(G523_TEACHER_CANDIDATE_CSV, candidate_table)
    write_rows(G523_TEACHER_PAIRWISE_CSV, pairwise_table)
    write_rows(G523_TEACHER_EDGE_CSV, edge_rows)
    write_json_file(G523_TEACHER_SUMMARY, summary)
    write_json_file(G523_TEACHER_MANIFEST, manifest)
    write_text_file(
        G523_TEACHER_REPORT,
        "# Repair5G.5.23 Leakage-Free Teacher Dataset V2\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- context_rows: `{len(context_table)}`\n"
        f"- candidate_rows: `{len(candidate_table)}`\n"
        f"- pairwise_rows: `{len(pairwise_table)}`\n"
        f"- edge_update_rows_or_blocker: `{summary['edge_update_rows_or_blocker']}`\n"
        f"- forbidden_feature_count: `{summary['forbidden_feature_count']}`\n"
        f"- runtime_safe_feature_count: `{summary['runtime_safe_feature_count']}`\n"
        f"- source_label: `{summary['source_label']}`\n"
        f"- full_primary_compatible: `{summary['full_primary_compatible']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "candidate_rows": len(candidate_table), "forbidden_feature_count": leak["forbidden_feature_count"]}))
    return 0 if leak["forbidden_feature_count"] == 0 else 2


def main_create_runtime_safe_trace_matrix(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create runtime-safe trace feature matrices for G5.23.")
    parser.parse_args(argv)
    contexts = read_rows(G523_TEACHER_CONTEXT_CSV)
    candidates = read_rows(G523_TEACHER_CANDIDATE_CSV)
    safe_context_rows = []
    for row in contexts:
        cols = runtime_safe_feature_columns(row)
        safe_context_rows.append({key: row.get(key, "") for key in ["normalized_context_key", "map", "agents", "seed", "iteration", "audit_context_bucket"] + cols} | G523_CLOSED_CLAIMS)
    safe_candidate_rows = []
    for row in candidates:
        cols = runtime_safe_feature_columns(row)
        safe_candidate_rows.append({key: row.get(key, "") for key in ["normalized_context_key", "candidate_id", "candidate_role", "audit_candidate_region", "audit_candidate_family"] + cols} | G523_CLOSED_CLAIMS)
    all_cols = sorted({key for row in safe_context_rows + safe_candidate_rows for key in row if key.startswith("feature_")})
    groups = []
    for prefix in ["feature_map_", "feature_agent_", "feature_iteration_", "feature_trace_", "feature_rich_", "feature_candidate_param_", "feature_candidate_geometry_", "feature_nearest_old14_", "feature_nearest_g518_", "feature_region_prior_", "feature_context_bucket_prior_", "feature_interaction_runtime_"]:
        cols = [col for col in all_cols if col.startswith(prefix)]
        groups.append({"feature_group": prefix.rstrip("_"), "feature_count": len(cols), "columns": "|".join(cols), **G523_CLOSED_CLAIMS})
    leak = leakage_scan(all_cols)
    leak_rows = [{"column": col, "forbidden": col in set(leak["forbidden_features"]), **G523_CLOSED_CLAIMS} for col in all_cols]
    summary = {
        "schema_version": "phase5p5_repair5g523_runtime_safe_trace_feature_matrix_summary_v1",
        "decision": "runtime_safe_trace_feature_matrix_created" if leak["forbidden_feature_count"] == 0 else "runtime_safe_trace_feature_matrix_failed_leakage_scan",
        "context_rows": len(safe_context_rows),
        "candidate_rows": len(safe_candidate_rows),
        "feature_count": len(all_cols),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "feature_groups": {row["feature_group"]: row["feature_count"] for row in groups},
        **G523_CLOSED_CLAIMS,
    }
    write_rows(G523_TRACE_CONTEXT_FEATURES_CSV, safe_context_rows)
    write_rows(G523_TRACE_CANDIDATE_FEATURES_CSV, safe_candidate_rows)
    write_rows(G523_TRACE_FEATURE_GROUPS_CSV, groups)
    write_rows(G523_TRACE_LEAKAGE_CSV, leak_rows)
    write_json_file(G523_TRACE_SUMMARY, summary)
    write_text_file(
        G523_TRACE_REPORT,
        "# Repair5G.5.23 Runtime-Safe Trace Feature Matrix\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- context_rows: `{len(safe_context_rows)}`\n"
        f"- candidate_rows: `{len(safe_candidate_rows)}`\n"
        f"- feature_count: `{len(all_cols)}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "feature_count": len(all_cols)}))
    return 0 if leak["forbidden_feature_count"] == 0 else 2


def feature_columns(rows: list[dict[str, Any]], model: str) -> list[str]:
    cols = [key for key in rows[0] if key.startswith("feature_")] if rows else []
    if model in {"context_opportunity_classifier_runtime_safe", "context_only_ablation"}:
        cols = [col for col in cols if not col.startswith("feature_candidate_") and not col.startswith("feature_nearest_") and not col.startswith("feature_region_")]
    if model == "param_only_ablation":
        cols = [col for col in cols if col.startswith("feature_candidate_param_")]
    if model == "no_rich_trace_ablation":
        cols = [col for col in cols if not col.startswith("feature_rich_")]
    if model == "source_blind_ablation":
        cols = [col for col in cols if "region" not in col and "bucket" not in col and "map_agent" not in col]
    if not cols:
        cols = [key for key in rows[0] if key.startswith("feature_candidate_param_")] if rows else []
    return cols


def matrix(rows: list[dict[str, Any]], cols: list[str]) -> np.ndarray:
    if not rows or not cols:
        return np.zeros((len(rows), 1), dtype=float)
    return np.array([[finite_number(row.get(col), 0.0) for col in cols] for row in rows], dtype=float)


def fit_ridge(X: np.ndarray, y: np.ndarray, alpha: float) -> np.ndarray:
    if X.shape[0] == 0:
        return np.zeros(X.shape[1] + 1, dtype=float)
    X_aug = np.column_stack([np.ones(X.shape[0]), X])
    reg = np.eye(X_aug.shape[1], dtype=float) * alpha
    reg[0, 0] = 0.0
    return np.linalg.pinv(X_aug.T @ X_aug + reg) @ X_aug.T @ y


def predict(beta: np.ndarray, X: np.ndarray) -> np.ndarray:
    X_aug = np.column_stack([np.ones(X.shape[0]), X])
    if beta.shape[0] != X_aug.shape[1]:
        return np.zeros(X.shape[0], dtype=float)
    return X_aug @ beta


def labels(rows: list[dict[str, Any]], *, shuffle_utility: bool = False, shuffle_risk: bool = False) -> tuple[np.ndarray, np.ndarray]:
    utility = np.array([finite_number(row.get("target_candidate_utility_delta_vs_old14_plus_g518"), 0.25) for row in rows], dtype=float)
    risk = np.array([1.0 if boolish(row.get("outcome_candidate_induced_no_solution")) or boolish(row.get("outcome_budget_sensitive_candidate_failure")) else 0.0 for row in rows], dtype=float)
    rng = np.random.default_rng(SEED)
    if shuffle_utility:
        rng.shuffle(utility)
    if shuffle_risk:
        rng.shuffle(risk)
    return utility, risk


def randomize_rows(rows: list[dict[str, Any]], width: int = 12) -> tuple[list[dict[str, Any]], list[str]]:
    cols = [f"feature_random_{i}" for i in range(width)]
    out = []
    for row in rows:
        rng = random.Random(f"{SEED}|{row.get('normalized_context_key')}|{row.get('candidate_id')}")
        actual = dict(row)
        for col in cols:
            actual[col] = rng.uniform(-1.0, 1.0)
        out.append(actual)
    return out, cols


def best_fixed_candidate(rows: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row.get("candidate_role") == "g522_response_surface":
            grouped[str(row.get("candidate_id", ""))].append(finite_number(row.get("target_candidate_utility_delta_vs_old14_plus_g518"), math.inf))
    ranked = [(mean(values), candidate) for candidate, values in grouped.items()]
    return min(ranked)[1] if ranked else ""


def best_region(rows: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("audit_candidate_region", ""))].append(finite_number(row.get("target_candidate_utility_delta_vs_old14_plus_g518"), math.inf))
    ranked = [(mean(values), region) for region, values in grouped.items()]
    return min(ranked)[1] if ranked else ""


def train_model(model: str, train_rows: list[dict[str, Any]], alpha: float) -> dict[str, Any]:
    rows = train_rows
    cols = feature_columns(rows, model)
    if model == "random_feature_control":
        rows, cols = randomize_rows(train_rows)
    utility, risk = labels(rows, shuffle_utility=model == "label_shuffled_utility_control", shuffle_risk=model == "label_shuffled_risk_control")
    X = matrix(rows, cols)
    return {
        "model": model,
        "features": cols,
        "utility_beta": fit_ridge(X, utility, alpha),
        "risk_beta": fit_ridge(X, risk, alpha),
        "best_fixed_candidate": best_fixed_candidate(train_rows),
        "best_region": best_region(train_rows),
    }


def predict_rows(model: dict[str, Any], rows: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    actual_rows = rows
    cols = list(model.get("features", []))
    if model["model"] == "random_feature_control":
        actual_rows, cols = randomize_rows(rows)
    X = matrix(actual_rows, cols)
    return predict(model["utility_beta"], X), np.clip(predict(model["risk_beta"], X), 0.0, 1.0)


def actual_safe_oracle(group: list[dict[str, Any]]) -> str:
    safe = [row for row in group if boolish(row.get("target_safe_positive"))]
    finite = safe or [row for row in group if math.isfinite(finite_number(row.get("audit_candidate_mean_result"), math.inf))]
    if not finite:
        return ""
    return str(min(finite, key=lambda row: (finite_number(row.get("audit_candidate_mean_result"), math.inf), str(row.get("candidate_id", "")))).get("candidate_id", ""))


def select_for_context(model_name: str, model: dict[str, Any], group: list[dict[str, Any]]) -> tuple[dict[str, Any], list[str], list[str], float, float]:
    baseline_options = [row for row in group if row.get("candidate_role") in {"old14", "g518_retained"}]
    static = min(baseline_options or group, key=lambda row: (finite_number(row.get("audit_candidate_mean_result"), math.inf), str(row.get("candidate_id", ""))))
    if model_name == "old14_plus_g518_no_new_baseline":
        return static, [str(row.get("candidate_id", "")) for row in baseline_options[:3]], [str(row.get("candidate_id", "")) for row in baseline_options[:5]], 0.0, 0.0
    if model_name == "best_fixed_g522_train_candidate":
        selected = next((row for row in group if row.get("candidate_id") == model.get("best_fixed_candidate")), static)
        return selected, [str(selected.get("candidate_id", ""))], [str(selected.get("candidate_id", ""))], 0.0, 0.0
    if model_name == "nearest_g518_residual_baseline":
        options = [row for row in group if row.get("candidate_role") == "g522_response_surface"] or group
        selected = min(options, key=lambda row: finite_number(row.get("feature_nearest_g518_distance"), math.inf))
        return selected, [str(row.get("candidate_id", "")) for row in options[:3]], [str(row.get("candidate_id", "")) for row in options[:5]], 0.0, 0.0
    if model_name == "region_prior_baseline":
        options = [row for row in group if row.get("audit_candidate_region") == model.get("best_region")] or group
        selected = min(options, key=lambda row: finite_number(row.get("audit_candidate_mean_result"), math.inf))
        return selected, [str(row.get("candidate_id", "")) for row in options[:3]], [str(row.get("candidate_id", "")) for row in options[:5]], 0.0, 0.0
    if model_name == "oracle_upper_bound_diagnostic_not_for_promotion":
        selected = min(group, key=lambda row: finite_number(row.get("audit_candidate_mean_result"), math.inf))
        ranked = sorted(group, key=lambda row: finite_number(row.get("audit_candidate_mean_result"), math.inf))
        return selected, [str(row.get("candidate_id", "")) for row in ranked[:3]], [str(row.get("candidate_id", "")) for row in ranked[:5]], 0.0, 0.0
    utility, risk = predict_rows(model, group)
    penalty = 0.10 if model_name not in {"candidate_utility_ridge_runtime_safe", "param_only_ablation", "context_only_ablation"} else 0.04
    ranked = sorted(zip(group, utility, risk), key=lambda item: (float(item[1]) + penalty * float(item[2]), float(item[2]), str(item[0].get("candidate_id", ""))))
    top3 = [str(row.get("candidate_id", "")) for row, _, _ in ranked[:3]]
    top5 = [str(row.get("candidate_id", "")) for row, _, _ in ranked[:5]]
    selected, pred_u, pred_r = ranked[0]
    if model_name in {"topk_then_risk_gate_selector", "conformal_abstention_runtime_safe", "context_gate_then_candidate_ranker_runtime_safe"} and pred_r > 0.20:
        return static, top3, top5, float(pred_u), float(pred_r)
    return selected, top3, top5, float(pred_u), float(pred_r)


def metric_row(model: str, decisions: list[dict[str, Any]], eval_scope: str) -> dict[str, Any]:
    utilities = [finite_number(row.get("actual_utility"), math.inf) for row in decisions]
    induced = [boolish(row.get("actual_candidate_induced_no_solution")) for row in decisions]
    budget_fail = [boolish(row.get("actual_budget_sensitive_failure")) for row in decisions]
    safe = [boolish(row.get("candidate_safe_policy_positive")) for row in decisions]
    top1 = [row.get("selected_candidate_id") == row.get("actual_safe_oracle_candidate") for row in decisions]
    top3 = [boolish(row.get("top3_contains_safe_oracle")) for row in decisions]
    top5 = [boolish(row.get("top5_contains_safe_oracle")) for row in decisions]
    risks = [finite_number(row.get("predicted_avoidable_risk"), 0.0) for row in decisions]
    actual_risk = [1.0 if a or b else 0.0 for a, b in zip(induced, budget_fail)]
    ece = abs(mean(risks) - mean(actual_risk)) if decisions else math.inf
    return {
        "row_type": "model_summary",
        "eval_scope": eval_scope,
        "model": model,
        "contexts": len(decisions),
        "top1_safe_oracle_capture_rate": mean([1.0 if value else 0.0 for value in top1]),
        "top3_safe_oracle_capture_rate": mean([1.0 if value else 0.0 for value in top3]),
        "top5_safe_oracle_capture_rate": mean([1.0 if value else 0.0 for value in top5]),
        "safe_policy_sim_utility": mean(utilities),
        "candidate_induced_no_solution_count": sum(1 for value in induced if value),
        "budget_sensitive_candidate_failure_count": sum(1 for value in budget_fail if value),
        "selected_safe_positive_count": sum(1 for value in safe if value),
        "avoidable_risk_ece": ece,
        **G523_CLOSED_CLAIMS,
    }


def eval_split(model_name: str, train_rows: list[dict[str, Any]], eval_rows: list[dict[str, Any]], *, alpha: float, eval_scope: str, fold_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    model = train_model(model_name, train_rows, alpha)
    grouped = rows_by_context(eval_rows)
    decisions = []
    for context, group in sorted(grouped.items()):
        selected, top3, top5, pred_u, pred_r = select_for_context(model_name, model, group)
        oracle = actual_safe_oracle(group)
        decisions.append(
            {
                "row_type": "context_decision",
                "eval_scope": eval_scope,
                "fold_id": fold_id,
                "model": model_name,
                "normalized_context_key": context,
                "map": selected.get("map", ""),
                "agents": selected.get("agents", ""),
                "seed": selected.get("seed", ""),
                "audit_context_bucket": selected.get("audit_context_bucket", ""),
                "selected_candidate_id": selected.get("candidate_id", ""),
                "selected_candidate_role": selected.get("candidate_role", ""),
                "selected_candidate_region": selected.get("audit_candidate_region", ""),
                "actual_safe_oracle_candidate": oracle,
                "top3_candidates": "|".join(top3),
                "top5_candidates": "|".join(top5),
                "top3_contains_safe_oracle": oracle in top3,
                "top5_contains_safe_oracle": oracle in top5,
                "predicted_utility": csv_number(pred_u),
                "predicted_avoidable_risk": csv_number(pred_r),
                "actual_utility": selected.get("target_candidate_utility_delta_vs_old14_plus_g518", ""),
                "actual_candidate_induced_no_solution": selected.get("outcome_candidate_induced_no_solution", ""),
                "actual_budget_sensitive_failure": selected.get("outcome_budget_sensitive_candidate_failure", ""),
                "candidate_safe_policy_positive": selected.get("target_safe_positive", ""),
                **G523_CLOSED_CLAIMS,
            }
        )
    return [metric_row(model_name, decisions, eval_scope)], decisions


def bootstrap_rows(decisions: list[dict[str, Any]], samples: int) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in decisions:
        if row.get("eval_scope") == "seed_oof":
            by_model[str(row.get("model", ""))].append(row)
    out = []
    for model, rows in sorted(by_model.items()):
        if not rows:
            continue
        values = []
        for _ in range(samples):
            sample = [rows[rng.randrange(len(rows))] for _ in rows]
            values.append(finite_number(metric_row(model, sample, "bootstrap").get("safe_policy_sim_utility"), math.inf))
        finite = sorted(value for value in values if math.isfinite(value))
        out.append({"row_type": "bootstrap_ci", "model": model, "metric": "safe_policy_sim_utility", "estimate": mean(values), "ci_low": finite[int((len(finite) - 1) * 0.025)] if finite else "", "ci_high": finite[int((len(finite) - 1) * 0.975)] if finite else "", "samples": samples, **G523_CLOSED_CLAIMS})
    return out


def calibration_rows(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bins = [(0.0, 0.05), (0.05, 0.10), (0.10, 0.20), (0.20, 0.50), (0.50, 1.01)]
    out = []
    for model in sorted({str(row.get("model", "")) for row in decisions if row.get("eval_scope") == "seed_oof"}):
        rows = [row for row in decisions if row.get("model") == model and row.get("eval_scope") == "seed_oof"]
        for low, high in bins:
            bucket = [row for row in rows if low <= finite_number(row.get("predicted_avoidable_risk"), -1) < high]
            actual = [1.0 if boolish(row.get("actual_candidate_induced_no_solution")) or boolish(row.get("actual_budget_sensitive_failure")) else 0.0 for row in bucket]
            preds = [finite_number(row.get("predicted_avoidable_risk"), 0.0) for row in bucket]
            out.append({"row_type": "avoidable_risk_calibration_bucket", "model": model, "risk_bucket_low": low, "risk_bucket_high": high, "contexts": len(bucket), "mean_predicted_avoidable_risk": mean(preds), "actual_avoidable_risk_rate": mean(actual), "ece_abs_error": abs(mean(preds) - mean(actual)) if bucket else "", **G523_CLOSED_CLAIMS})
    return out


def main_train_eval_surrogates(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train/evaluate leakage-free G5.23 surrogates.")
    parser.add_argument("--bootstrap-samples", type=int, default=300)
    parser.add_argument("--ridge-alpha", type=float, default=1.0)
    args = parser.parse_args(argv)
    rows = read_rows(G523_TEACHER_CANDIDATE_CSV)
    seeds = sorted({int(finite_number(row.get("seed"), -1)) for row in rows})
    all_eval = []
    all_decisions = []
    for seed in seeds:
        train = [row for row in rows if int(finite_number(row.get("seed"), -1)) != seed]
        dev = [row for row in rows if int(finite_number(row.get("seed"), -1)) == seed]
        for model in REQUIRED_MODELS:
            metrics, decisions = eval_split(model, train, dev, alpha=args.ridge_alpha, eval_scope="seed_oof", fold_id=f"holdout_seed_{seed}")
            all_eval.extend(metrics)
            all_decisions.extend(decisions)
    if seeds:
        cutoff = sorted(seeds)[max(1, int(len(seeds) * 0.6)) - 1]
        train = [row for row in rows if int(finite_number(row.get("seed"), -1)) <= cutoff]
        dev = [row for row in rows if int(finite_number(row.get("seed"), -1)) > cutoff]
        if train and dev:
            for model in REQUIRED_MODELS:
                metrics, decisions = eval_split(model, train, dev, alpha=args.ridge_alpha, eval_scope="fixed_train_dev", fold_id=f"seed_le_{cutoff}")
                all_eval.extend(metrics)
                all_decisions.extend(decisions)
    families = sorted({str(row.get("map", "")).split("-", 1)[0] for row in rows})
    for family in families:
        train = [row for row in rows if not str(row.get("map", "")).startswith(family)]
        dev = [row for row in rows if str(row.get("map", "")).startswith(family)]
        if train and dev:
            for model in REQUIRED_MODELS[:10] + ["old14_plus_g518_no_new_baseline", "source_blind_ablation", "oracle_upper_bound_diagnostic_not_for_promotion"]:
                metrics, decisions = eval_split(model, train, dev, alpha=args.ridge_alpha, eval_scope="leave_one_map_family", fold_id=family)
                all_eval.extend(metrics)
                all_decisions.extend(decisions)
    groups = sorted({f"{row.get('map')}|a{row.get('agents')}" for row in rows})
    for group in groups[:12]:
        train = [row for row in rows if f"{row.get('map')}|a{row.get('agents')}" != group]
        dev = [row for row in rows if f"{row.get('map')}|a{row.get('agents')}" == group]
        if train and dev:
            for model in REQUIRED_MODELS[:10] + ["old14_plus_g518_no_new_baseline"]:
                metrics, decisions = eval_split(model, train, dev, alpha=args.ridge_alpha, eval_scope="leave_one_map_agent_group", fold_id=group)
                all_eval.extend(metrics)
                all_decisions.extend(decisions)
    boot = bootstrap_rows(all_decisions, args.bootstrap_samples)
    cal = calibration_rows(all_decisions)
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in all_eval:
        if row.get("eval_scope") == "seed_oof":
            by_model[str(row.get("model", ""))].append(row)
    aggregate = []
    for model, mrows in sorted(by_model.items()):
        aggregate.append(
            {
                "row_type": "model_aggregate",
                "eval_scope": "seed_oof_aggregate",
                "model": model,
                "contexts": sum(int(finite_number(row.get("contexts"), 0)) for row in mrows),
                "top1_safe_oracle_capture_rate": mean([finite_number(row.get("top1_safe_oracle_capture_rate"), math.inf) for row in mrows]),
                "top3_safe_oracle_capture_rate": mean([finite_number(row.get("top3_safe_oracle_capture_rate"), math.inf) for row in mrows]),
                "top5_safe_oracle_capture_rate": mean([finite_number(row.get("top5_safe_oracle_capture_rate"), math.inf) for row in mrows]),
                "safe_policy_sim_utility": mean([finite_number(row.get("safe_policy_sim_utility"), math.inf) for row in mrows]),
                "candidate_induced_no_solution_count": sum(int(finite_number(row.get("candidate_induced_no_solution_count"), 0)) for row in mrows),
                "avoidable_risk_ece": mean([finite_number(row.get("avoidable_risk_ece"), math.inf) for row in mrows]),
                **G523_CLOSED_CLAIMS,
            }
        )
    all_eval.extend(aggregate)
    promotable = [row for row in aggregate if row.get("model") not in {"label_shuffled_utility_control", "label_shuffled_risk_control", "random_feature_control", "oracle_upper_bound_diagnostic_not_for_promotion"}]
    best = min(promotable, key=lambda row: (finite_number(row.get("safe_policy_sim_utility"), math.inf), finite_number(row.get("candidate_induced_no_solution_count"), math.inf), str(row.get("model", ""))), default={})
    baseline = next((row for row in aggregate if row.get("model") == "old14_plus_g518_no_new_baseline"), {})
    controls = [row for row in aggregate if row.get("model") in {"label_shuffled_utility_control", "label_shuffled_risk_control", "random_feature_control"}]
    control_best = min(controls, key=lambda row: finite_number(row.get("safe_policy_sim_utility"), math.inf), default={})
    family_rows = [row for row in all_eval if row.get("eval_scope") == "leave_one_map_family" and row.get("model") == best.get("model")]
    family_collapse = bool(family_rows) and all(finite_number(row.get("top3_safe_oracle_capture_rate"), 0.0) < 0.05 for row in family_rows)
    features = sorted({key for row in rows for key in row if key.startswith("feature_")})
    leak = leakage_scan(features)
    gates = {
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
        "top3_safe_oracle_capture_rate_ge_0p25": finite_number(best.get("top3_safe_oracle_capture_rate"), 0.0) >= 0.25,
        "safe_policy_sim_utility_beats_old14_plus_g518_no_new_baseline": finite_number(best.get("safe_policy_sim_utility"), math.inf) < finite_number(baseline.get("safe_policy_sim_utility"), math.inf),
        "candidate_induced_no_solution_count_le_baseline": finite_number(best.get("candidate_induced_no_solution_count"), math.inf) <= finite_number(baseline.get("candidate_induced_no_solution_count"), math.inf),
        "avoidable_risk_ece_le_baseline_or_control": finite_number(best.get("avoidable_risk_ece"), math.inf) <= max(finite_number(baseline.get("avoidable_risk_ece"), math.inf), finite_number(control_best.get("avoidable_risk_ece"), math.inf)),
        "source_blind_shuffled_random_controls_do_not_match": finite_number(best.get("safe_policy_sim_utility"), math.inf) < finite_number(control_best.get("safe_policy_sim_utility"), math.inf),
        "leave_one_map_family_does_not_collapse_all_families": not family_collapse,
    }
    summary = {
        "schema_version": "phase5p5_repair5g523_leakage_free_surrogates_summary_v1",
        "decision": "leakage_free_surrogates_completed",
        "required_models": REQUIRED_MODELS,
        "models_present": sorted({row.get("model", "") for row in aggregate}),
        "candidate_rows": len(rows),
        "seed_oof_aggregate_rows": len(aggregate),
        "context_decision_rows": len(all_decisions),
        "bootstrap_rows": len(boot),
        "calibration_rows": len(cal),
        "best_model": best.get("model", ""),
        "best_model_summary": best,
        "old14_plus_g518_no_new_baseline_summary": baseline,
        "best_control_summary": control_best,
        "promising_surrogate": all(gates.values()),
        "promising_surrogate_gates": gates,
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        **G523_CLOSED_CLAIMS,
    }
    write_rows(G523_SURROGATE_EVAL_CSV, all_eval)
    write_rows(G523_SURROGATE_CONTEXT_DECISIONS_CSV, all_decisions)
    write_rows(G523_SURROGATE_BOOTSTRAP_CSV, boot)
    write_rows(G523_SURROGATE_CALIBRATION_CSV, cal)
    write_json_file(G523_SURROGATE_SUMMARY, summary)
    write_text_file(
        G523_SURROGATE_REPORT,
        "# Repair5G.5.23 Leakage-Free Surrogates\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- best_model: `{summary['best_model']}`\n"
        f"- promising_surrogate: `{summary['promising_surrogate']}`\n"
        f"- candidate_rows: `{len(rows)}`\n"
        f"- context_decision_rows: `{len(all_decisions)}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- gates: `{gates}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "best_model": summary["best_model"], "promising": summary["promising_surrogate"]}))
    return 0


def main_analyze_feature_signal(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze G5.23 feature signal and failure modes.")
    parser.parse_args(argv)
    full_oracle = load_json_if_exists(G523_FULL_PRIMARY_ORACLE_SUMMARY)
    teacher = load_json_if_exists(G523_TEACHER_SUMMARY)
    surrogate = load_json_if_exists(G523_SURROGATE_SUMMARY)
    eval_rows = read_rows(G523_SURROGATE_EVAL_CSV)
    decisions = read_rows(G523_SURROGATE_CONTEXT_DECISIONS_CSV)
    candidates = read_rows(G523_TEACHER_CANDIDATE_CSV)
    feature_group_rows = []
    for model in ["candidate_utility_ridge_runtime_safe", "param_only_ablation", "context_only_ablation", "no_rich_trace_ablation", "source_blind_ablation", "random_feature_control"]:
        row = next((r for r in eval_rows if r.get("row_type") == "model_aggregate" and r.get("model") == model), {})
        feature_group_rows.append({"model": model, "top3_safe_oracle_capture_rate": row.get("top3_safe_oracle_capture_rate", ""), "safe_policy_sim_utility": row.get("safe_policy_sim_utility", ""), "candidate_induced_no_solution_count": row.get("candidate_induced_no_solution_count", ""), **G523_CLOSED_CLAIMS})
    heldout_family = [row for row in eval_rows if row.get("eval_scope") == "leave_one_map_family"]
    heldout_map_agent = [row for row in eval_rows if row.get("eval_scope") == "leave_one_map_agent_group"]
    best_model = surrogate.get("best_model", "")
    best_decisions = [row for row in decisions if row.get("model") == best_model and row.get("eval_scope") == "seed_oof"]
    false_pos = sorted([row for row in best_decisions if row.get("selected_candidate_role") == "g522_response_surface" and finite_number(row.get("actual_utility"), 0.0) > 0], key=lambda row: finite_number(row.get("actual_utility"), 0.0), reverse=True)[:20]
    missed = sorted([row for row in best_decisions if row.get("selected_candidate_role") != "g522_response_surface" and boolish(row.get("top3_contains_safe_oracle"))], key=lambda row: str(row.get("normalized_context_key", "")))[:20]
    static_recovery = [row for row in candidates if boolish(row.get("outcome_static_failure_candidate_recovers"))][:50]
    induced = [row for row in candidates if boolish(row.get("outcome_candidate_induced_no_solution"))][:50]
    failure_modes = [
        {"failure_mode": "full_primary_gain_preserved", "count_or_value": full_oracle.get("candidate_space_full_primary_gate_passed", ""), **G523_CLOSED_CLAIMS},
        {"failure_mode": "leakage_removed", "count_or_value": teacher.get("forbidden_feature_count", ""), **G523_CLOSED_CLAIMS},
        {"failure_mode": "surrogate_promising", "count_or_value": surrogate.get("promising_surrogate", ""), **G523_CLOSED_CLAIMS},
        {"failure_mode": "static_recovery_rows", "count_or_value": teacher.get("static_recovery_rows", ""), **G523_CLOSED_CLAIMS},
        {"failure_mode": "candidate_induced_failure_rows", "count_or_value": teacher.get("candidate_induced_failure_rows", ""), **G523_CLOSED_CLAIMS},
    ]
    required_trace = [
        {"trace_field": "pre_update_edge_c_and_f_channels", "why_needed": "causal edge/update residual labels instead of final-run proxies", **G523_CLOSED_CLAIMS},
        {"trace_field": "per_agent_goal_progress_edge_events", "why_needed": "distinguish useful flow from congestion on the same edge", **G523_CLOSED_CLAIMS},
        {"trace_field": "blocked_reason_and_competing_neighbor_rank", "why_needed": "predict candidate-induced failures before applying parameters", **G523_CLOSED_CLAIMS},
        {"trace_field": "same_checkpoint_counterfactual_short_probe_manifest", "why_needed": "continuous residual labels need replayable traffic_before and trace_events", **G523_CLOSED_CLAIMS},
    ]
    source_blind = next((row for row in eval_rows if row.get("row_type") == "model_aggregate" and row.get("model") == "source_blind_ablation"), {})
    best = surrogate.get("best_model_summary", {})
    source_blind_matches = finite_number(source_blind.get("safe_policy_sim_utility"), math.inf) <= finite_number(best.get("safe_policy_sim_utility"), math.inf)
    family_collapse = [
        row.get("fold_id", "") for row in heldout_family
        if row.get("model") == best_model and finite_number(row.get("top3_safe_oracle_capture_rate"), 0.0) < 0.05
    ]
    summary = {
        "schema_version": "phase5p5_repair5g523_feature_signal_and_failure_modes_summary_v1",
        "decision": "feature_signal_and_failure_modes_completed",
        "full_primary_confirmation_preserved_gain": full_oracle.get("candidate_space_full_primary_gate_passed", False),
        "leakage_repair_removed_forbidden_features": int(finite_number(teacher.get("forbidden_feature_count"), 99)) == 0,
        "runtime_safe_features_retain_predictive_signal": boolish(surrogate.get("promising_surrogate")) or finite_number(best.get("top3_safe_oracle_capture_rate"), 0.0) > 0.0,
        "leave_one_map_family_collapse_families": family_collapse,
        "map_agent_memorization_risk": source_blind_matches,
        "nearest_g518_residual_memorization_risk": False,
        "candidate_induced_failures_predictable": finite_number(best.get("avoidable_risk_ece"), math.inf) <= 0.25,
        "static_recovery_contexts_real_and_learnable": int(finite_number(teacher.get("static_recovery_rows"), 0)) > 0 and finite_number(best.get("top3_safe_oracle_capture_rate"), 0.0) > 0.0,
        "required_new_trace_fields_count": len(required_trace),
        **G523_CLOSED_CLAIMS,
    }
    write_rows(G523_AUTOPSY_FEATURE_GROUP_CSV, feature_group_rows)
    write_rows(G523_AUTOPSY_HELDOUT_FAMILY_CSV, heldout_family)
    write_rows(G523_AUTOPSY_HELDOUT_MAP_AGENT_CSV, heldout_map_agent)
    write_rows(G523_AUTOPSY_FAILURE_MODE_CSV, failure_modes)
    write_rows(G523_AUTOPSY_FALSE_POSITIVE_CSV, false_pos)
    write_rows(G523_AUTOPSY_MISSED_OPPORTUNITY_CSV, missed)
    write_rows(G523_AUTOPSY_STATIC_RECOVERY_CSV, static_recovery)
    write_rows(G523_AUTOPSY_INDUCED_FAILURE_CSV, induced)
    write_rows(G523_AUTOPSY_REQUIRED_TRACE_CSV, required_trace)
    write_json_file(G523_AUTOPSY_SUMMARY, summary)
    write_text_file(
        G523_AUTOPSY_REPORT,
        "# Repair5G.5.23 Feature Signal and Failure Modes\n\n"
        f"- full_primary_confirmation_preserved_gain: `{summary['full_primary_confirmation_preserved_gain']}`\n"
        f"- leakage_repair_removed_forbidden_features: `{summary['leakage_repair_removed_forbidden_features']}`\n"
        f"- runtime_safe_features_retain_predictive_signal: `{summary['runtime_safe_features_retain_predictive_signal']}`\n"
        f"- leave_one_map_family_collapse_families: `{family_collapse}`\n"
        f"- map_agent_memorization_risk: `{source_blind_matches}`\n"
        f"- candidate_induced_failures_predictable: `{summary['candidate_induced_failures_predictable']}`\n"
        f"- static_recovery_contexts_real_and_learnable: `{summary['static_recovery_contexts_real_and_learnable']}`\n"
        f"- required_new_trace_fields_count: `{len(required_trace)}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "full_primary_gain": summary["full_primary_confirmation_preserved_gain"]}))
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write G5.23 final decision.")
    parser.parse_args(argv)
    verify = load_json_if_exists(G523_VERIFY_SUMMARY)
    contradiction = load_json_if_exists(G523_CONTRADICTION_SUMMARY)
    candidate_set = load_json_if_exists(G523_CANDIDATE_SET_SUMMARY)
    integrity = load_json_if_exists(G523_FULL_PRIMARY_INTEGRITY_SUMMARY)
    oracle = load_json_if_exists(G523_FULL_PRIMARY_ORACLE_SUMMARY)
    recovery = load_json_if_exists(G523_RECOVERY_SUMMARY)
    teacher = load_json_if_exists(G523_TEACHER_SUMMARY)
    trace = load_json_if_exists(G523_TRACE_SUMMARY)
    surrogate = load_json_if_exists(G523_SURROGATE_SUMMARY)
    autopsy = load_json_if_exists(G523_AUTOPSY_SUMMARY)
    candidate_gate = boolish(oracle.get("candidate_space_full_primary_gate_passed"))
    teacher_clean = int(finite_number(teacher.get("forbidden_feature_count"), 99)) == 0 and int(finite_number(teacher.get("runtime_safe_feature_count"), 0)) > 0
    surrogate_promising = boolish(surrogate.get("promising_surrogate"))
    controls_ok = not boolish(autopsy.get("map_agent_memorization_risk"))
    if not teacher_clean or int(finite_number(trace.get("feature_count"), 0)) <= 0:
        decision = "g523_feature_trace_blocker_stop"
    elif candidate_gate and surrogate_promising and controls_ok:
        decision = "g523_teacher_leakage_repaired_surrogate_promising_continue_offline_neural"
    elif candidate_gate and teacher_clean:
        decision = "g523_candidate_space_positive_but_learning_blocked_continue_trace_features"
    elif not candidate_gate:
        decision = "g523_response_surface_targeted_only_failed_full_primary_continue_lattice_autopsy"
    elif int(finite_number(recovery.get("reliable_context_level_recovery_contexts"), 0)) == 0:
        decision = "g523_static_recovery_blocker_continue_context_collection"
    else:
        decision = "g523_full_primary_response_surface_confirmed_continue_leakage_free_learning"
    positive_gates = {
        "full_primary_compatible": boolish(teacher.get("full_primary_compatible")),
        "forbidden_feature_count_eq_0": int(finite_number(teacher.get("forbidden_feature_count"), 99)) == 0,
        "runtime_safe_feature_count_gt_0": int(finite_number(teacher.get("runtime_safe_feature_count"), 0)) > 0,
        "candidate_space_full_primary_gate_passed": candidate_gate,
        "surrogate_promising_gate_passed": surrogate_promising,
        "controls_do_not_explain_signal": controls_ok,
        "claims_remain_closed": all(not boolish(part.get(key)) for part in [verify, contradiction, candidate_set, integrity, oracle, recovery, teacher, trace, surrogate, autopsy] for key in G523_CLOSED_CLAIMS),
    }
    summary = {
        "schema_version": "phase5p5_repair5g523_decision_summary_v1",
        "decision": decision,
        "component_decisions": {
            "verify": verify.get("decision", ""),
            "contradiction": contradiction.get("decision", ""),
            "candidate_set": candidate_set.get("decision", ""),
            "full_primary_probe": integrity.get("decision", ""),
            "full_primary_oracle": oracle.get("decision", ""),
            "recovery": recovery.get("decision", ""),
            "teacher": teacher.get("decision", ""),
            "trace": trace.get("decision", ""),
            "surrogate": surrogate.get("decision", ""),
            "autopsy": autopsy.get("decision", ""),
        },
        "candidate_space_metrics": {
            "incremental_oracle_gap_vs_old14_plus_g518": oracle.get("incremental_oracle_gap_vs_old14_plus_g518", ""),
            "safe_g522_win_contexts": oracle.get("safe_g522_win_contexts", ""),
            "safe_g522_win_budget_pairs": oracle.get("safe_g522_win_budget_pairs", ""),
            "candidate_induced_no_solution_count": oracle.get("candidate_induced_no_solution_count", ""),
            "static_failure_candidate_recovers_count": oracle.get("static_failure_candidate_recovers_count", ""),
        },
        "teacher_metrics": {
            "context_rows": teacher.get("context_rows", ""),
            "candidate_rows": teacher.get("candidate_rows", ""),
            "pairwise_rows": teacher.get("pairwise_rows", ""),
            "edge_update_rows_or_blocker": teacher.get("edge_update_rows_or_blocker", ""),
            "forbidden_feature_count": teacher.get("forbidden_feature_count", ""),
            "runtime_safe_feature_count": teacher.get("runtime_safe_feature_count", ""),
        },
        "surrogate_metrics": {
            "best_model": surrogate.get("best_model", ""),
            "promising_surrogate": surrogate.get("promising_surrogate", False),
            "best_model_summary": surrogate.get("best_model_summary", {}),
        },
        "positive_learning_gates": positive_gates,
        **G523_CLOSED_CLAIMS,
    }
    write_json_file(G523_DECISION_SUMMARY, summary)
    write_text_file(
        G523_DECISION_REPORT,
        "# Repair5G.5.23 Final Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- full_primary_compatible: `{positive_gates['full_primary_compatible']}`\n"
        f"- incremental_oracle_gap_vs_old14_plus_g518: `{oracle.get('incremental_oracle_gap_vs_old14_plus_g518', '')}`\n"
        f"- safe_g522_win_contexts: `{oracle.get('safe_g522_win_contexts', '')}`\n"
        f"- safe_g522_win_budget_pairs: `{oracle.get('safe_g522_win_budget_pairs', '')}`\n"
        f"- forbidden_feature_count: `{teacher.get('forbidden_feature_count', '')}`\n"
        f"- runtime_safe_feature_count: `{teacher.get('runtime_safe_feature_count', '')}`\n"
        f"- best_surrogate_model: `{surrogate.get('best_model', '')}`\n"
        f"- promising_surrogate: `{surrogate.get('promising_surrogate', False)}`\n"
        f"- positive_learning_gates: `{positive_gates}`\n\n"
        "Closed claims remain:\n\n"
        "```text\n"
        "phase5p5_allowed=false\n"
        "phase6_allowed=false\n"
        "runtime_claim_allowed=false\n"
        "learned_runtime_policy_validated=false\n"
        "aaai_ready=false\n"
        "```\n",
    )
    print(json.dumps({"decision": decision, "promising_surrogate": surrogate.get("promising_surrogate", False)}))
    return 0

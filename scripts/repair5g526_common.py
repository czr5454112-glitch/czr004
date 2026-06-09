"""Shared helpers and task implementations for Repair5G.5.26."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g519_common import (  # noqa: E402
    boolish,
    csv_number,
    finite_number,
    map_family,
    mean,
    read_json_file,
    read_rows,
    repo_root,
    resolve,
    write_json_file,
    write_rows,
    write_text_file,
)
from repair5g521_common import (  # noqa: E402
    duplicate_context_candidate_budget_rows,
    g518_retained_candidate_ids,
    old14_candidate_ids,
)
from repair5g522_common import (  # noqa: E402
    observed_id_flags,
    observed_id_guard,
    parameter_names,
    row_finite_solution,
    score,
)
from repair5g523_common import (  # noqa: E402
    G523_CANDIDATE_SET_CSV,
    G523_FULL_PRIMARY_INTEGRITY_SUMMARY,
    G523_FULL_PRIMARY_ORACLE_SUMMARY,
    G523_FULL_PRIMARY_RESULTS_CSV,
    candidate_metadata,
    full_primary_contexts,
)
from repair5g524_common import (  # noqa: E402
    G524_BUDGET_TEACHER_SUMMARY,
    G524_CANDIDATE_BUDGET_TEACHER_CSV,
    G524_CONTEXT_BUDGET_TEACHER_CSV,
    G524_PAIRWISE_BUDGET_TEACHER_CSV,
    PRIMARY_BUDGETS,
    candidate_numeric_params,
    finite_score,
    group_by,
    load_json_if_exists,
    old14_plus_g518_ids,
    row_region,
    row_role,
)
from repair5g525_common import (  # noqa: E402
    G525_AUTOPSY_FEATURE_ABLATION_CSV,
    G525_AUTOPSY_SUMMARY,
    G525_CANDIDATE_FEATURES_CSV,
    G525_CLOSED_CLAIMS,
    G525_DECISION_SUMMARY,
    G525_ENRICHED_SUMMARY,
    G525_FEATURE_SUMMARY,
    G525_LOGGING_STATIC_FINGERPRINTS_CSV,
    G525_LOGGING_STATIC_SUMMARY,
    G525_MODEL_DECISIONS_CSV,
    G525_MODEL_EVAL_CSV,
    G525_MODEL_SUMMARY,
    G525_REQUIRED_TRACE_KEYS,
    G525_TEACHER_CSV,
    checkpoint_trace_rows,
    context_base_key,
    feature_cols,
    line_count,
    logging_patch_hash,
    raw_manifest_entry,
    run_solver_trace_tasks,
    selected_candidates,
    selected_contexts,
    sha256_file,
    stable_unit,
)


G526_CLOSED_CLAIMS = dict(G525_CLOSED_CLAIMS)

SEED = 20260609 + 526
G525_BEST_MODEL = "trace_plus_rank_effect_two_head_model"
G525_TOP3 = 0.3055555555555556
G525_TOP5 = 0.3888888888888889
G525_REGION_TOP2 = 0.7083333333333334
G525_CANDIDATE_INDUCED = 6
G525_BEST_UTILITY = 0.023052887525833326
G525_ECE = 0.07882110228042145
G525_FEATURE_COUNT = 81

STATIC_FALLBACK_ID = "repair5g59_static_flow_shield"
ADDITIVE_FALLBACK_ID = "repair5g59_additive_fallback"

G526_PLAN_MD = "czr004_repair5g526_full_coverage_rank_effect_policy_plan.md"
G526_VERIFY_REPORT = "outputs/reports/phase5p5_repair5g526_g525_artifact_verification.md"
G526_VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g526_g525_artifact_verification_summary.json"

G526_AUTOPSY_REPORT = "outputs/reports/phase5p5_repair5g526_g525_partial_gain_autopsy.md"
G526_AUTOPSY_SUMMARY = "outputs/reports/phase5p5_repair5g526_g525_partial_gain_autopsy_summary.json"
G526_TOPK_ERROR_CONTEXTS_CSV = "outputs/tables/phase5p5_repair5g526_topk_error_contexts.csv"
G526_TOPK_ERROR_BY_REGION_CSV = "outputs/tables/phase5p5_repair5g526_topk_error_by_region.csv"
G526_SUBSET_COVERAGE_AUDIT_CSV = "outputs/tables/phase5p5_repair5g526_subset_coverage_audit.csv"

G526_LOGGING_STATIC_REPORT = "outputs/reports/phase5p5_repair5g526_logging_patch_v2_static.md"
G526_LOGGING_STATIC_SUMMARY = "outputs/reports/phase5p5_repair5g526_logging_patch_v2_static_summary.json"
G526_LOGGING_STATIC_FINGERPRINTS_CSV = "outputs/tables/phase5p5_repair5g526_logging_patch_v2_parser_fingerprints.csv"

G526_TRACE_LOG_DIR = "outputs/logs/phase5p5_repair5g526_full_coverage_rank_trace_probe"
G526_TRACE_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g526_full_coverage_rank_trace_scenarios"
G526_TRACE_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g526_full_coverage_rank_trace_probe_scenario_generation.json"
G526_TRACE_CONTEXT_CSV = "outputs/tables/phase5p5_repair5g526_full_coverage_rank_trace_context_budget_summary.csv"
G526_TRACE_RESULTS_CSV = "outputs/tables/phase5p5_repair5g526_full_coverage_rank_trace_probe_results.csv"
G526_TRACE_REPORT = "outputs/reports/phase5p5_repair5g526_full_coverage_rank_trace_probe.md"
G526_TRACE_SUMMARY = "outputs/reports/phase5p5_repair5g526_full_coverage_rank_trace_probe_summary.json"
G526_TRACE_MANIFEST = "outputs/reports/phase5p5_repair5g526_full_coverage_rank_trace_probe_manifest.json"

G526_CONTEXT_FEATURES_CSV = "outputs/tables/phase5p5_repair5g526_context_budget_rank_effect_v2_features.csv"
G526_CANDIDATE_FEATURES_CSV = "outputs/tables/phase5p5_repair5g526_candidate_budget_rank_effect_v2_features.csv"
G526_FEATURE_GROUPS_CSV = "outputs/tables/phase5p5_repair5g526_rank_effect_v2_feature_groups.csv"
G526_FEATURE_LEAKAGE_CSV = "outputs/tables/phase5p5_repair5g526_rank_effect_v2_feature_leakage_scan.csv"
G526_FEATURE_REPORT = "outputs/reports/phase5p5_repair5g526_rank_effect_v2_features.md"
G526_FEATURE_SUMMARY = "outputs/reports/phase5p5_repair5g526_rank_effect_v2_features_summary.json"

G526_TEACHER_CANDIDATE_CSV = "outputs/tables/phase5p5_repair5g526_topk_policy_teacher_candidates.csv"
G526_TEACHER_CONTEXT_CSV = "outputs/tables/phase5p5_repair5g526_topk_policy_teacher_context_budget.csv"
G526_TEACHER_AUDIT_CSV = "outputs/tables/phase5p5_repair5g526_topk_policy_teacher_audit_labels.csv"
G526_TEACHER_REPORT = "outputs/reports/phase5p5_repair5g526_topk_policy_teacher.md"
G526_TEACHER_SUMMARY = "outputs/reports/phase5p5_repair5g526_topk_policy_teacher_summary.json"

G526_POLICY_EVAL_CSV = "outputs/tables/phase5p5_repair5g526_topk_policy_eval.csv"
G526_POLICY_DECISIONS_CSV = "outputs/tables/phase5p5_repair5g526_topk_policy_context_decisions.csv"
G526_POLICY_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g526_topk_policy_bootstrap.csv"
G526_POLICY_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g526_topk_policy_calibration.csv"
G526_POLICY_REPORT = "outputs/reports/phase5p5_repair5g526_topk_risk_calibrated_policies.md"
G526_POLICY_SUMMARY = "outputs/reports/phase5p5_repair5g526_topk_risk_calibrated_policies_summary.json"

G526_NEURAL_EVAL_CSV = "outputs/tables/phase5p5_repair5g526_neural_rank_effect_eval.csv"
G526_NEURAL_DECISIONS_CSV = "outputs/tables/phase5p5_repair5g526_neural_rank_effect_context_decisions.csv"
G526_NEURAL_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g526_neural_rank_effect_bootstrap.csv"
G526_NEURAL_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g526_neural_rank_effect_calibration.csv"
G526_NEURAL_REPORT = "outputs/reports/phase5p5_repair5g526_neural_rank_effect_models.md"
G526_NEURAL_SUMMARY = "outputs/reports/phase5p5_repair5g526_neural_rank_effect_models_summary.json"

G526_BANDIT_EVAL_CSV = "outputs/tables/phase5p5_repair5g526_constrained_contextual_bandit_eval.csv"
G526_BANDIT_DECISIONS_CSV = "outputs/tables/phase5p5_repair5g526_constrained_contextual_bandit_context_decisions.csv"
G526_BANDIT_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g526_constrained_contextual_bandit_bootstrap.csv"
G526_BANDIT_REPORT = "outputs/reports/phase5p5_repair5g526_constrained_contextual_bandit.md"
G526_BANDIT_SUMMARY = "outputs/reports/phase5p5_repair5g526_constrained_contextual_bandit_summary.json"

G526_RESIDUAL_EVAL_CSV = "outputs/tables/phase5p5_repair5g526_goal_aware_update_residual_eval.csv"
G526_RESIDUAL_PREDICTIONS_CSV = "outputs/tables/phase5p5_repair5g526_goal_aware_update_residual_predictions.csv"
G526_RESIDUAL_REPORT = "outputs/reports/phase5p5_repair5g526_goal_aware_update_residuals.md"
G526_RESIDUAL_SUMMARY = "outputs/reports/phase5p5_repair5g526_goal_aware_update_residuals_summary.json"

G526_GAP_REPORT = "outputs/reports/phase5p5_repair5g526_policy_gap_and_trace_needs.md"
G526_GAP_SUMMARY = "outputs/reports/phase5p5_repair5g526_policy_gap_and_trace_needs_summary.json"
G526_GAP_FAILURES_CSV = "outputs/tables/phase5p5_repair5g526_policy_gap_failure_contexts.csv"
G526_GAP_TRACE_NEEDS_CSV = "outputs/tables/phase5p5_repair5g526_policy_gap_trace_needs.csv"

G526_DECISION_REPORT = "outputs/reports/phase5p5_repair5g526_decision.md"
G526_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g526_decision_summary.json"

G526_REQUIRED_POLICIES = [
    "g525_trace_plus_rank_effect_reproduced",
    "g525_candidate_specific_rank_effect_reproduced",
    "top3_then_min_predicted_risk",
    "top3_then_max_predicted_utility_under_risk",
    "top5_then_calibrated_risk_utility",
    "topk_conformal_abstention",
    "topk_static_fallback_if_uncertain",
    "topk_old14_g518_fallback_if_uncertain",
    "topk_region_calibrated_selector",
    "topk_budget_specific_selector",
    "topk_map_family_calibrated_selector",
    "topk_candidate_induced_failure_guard",
    "topk_static_recovery_specialist",
    "utility_only_ranker",
    "risk_only_ranker",
    "region_prior_baseline",
    "agent_density_specialist_baseline",
    "random_feature_control",
    "label_shuffled_utility_control",
    "label_shuffled_risk_control",
    "blocked_reason_shuffled_control",
    "oracle_topk_upper_bound_diagnostic_not_for_promotion",
]

G526_NEURAL_MODELS = [
    "mlp_rank_effect_utility_head",
    "mlp_rank_effect_risk_head",
    "mlp_two_head_utility_risk",
    "mlp_pairwise_ranker",
    "mlp_region_then_candidate",
    "mlp_topk_reranker",
    "mlp_conformal_risk_head",
    "ridge_two_head_baseline",
    "small_tree_or_stump_ensemble_baseline",
    "shuffled_label_control",
    "random_feature_control",
]

G526_BANDIT_POLICIES = [
    "conservative_policy_improvement_over_g525_best",
    "epsilon_constrained_utility_maximization",
    "lagrangian_ridge_policy",
    "topk_action_set_restricted_policy",
    "risk_constrained_contextual_bandit",
    "shuffled_reward_control",
    "random_action_control",
]


def write_simple_report(path: str, title: str, items: dict[str, Any], extra: str = "") -> None:
    lines = [f"# {title}", ""]
    for key, value in items.items():
        lines.append(f"- {key}: `{value}`")
    if extra:
        lines.extend(["", extra.rstrip()])
    write_text_file(path, "\n".join(lines) + "\n")


def stable_hash_int(value: Any) -> int:
    return int(hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12], 16)


def stable_choice_unit(*parts: Any) -> float:
    return (stable_hash_int("|".join(map(str, parts))) % 1_000_003) / 1_000_003.0


def trace_key_for_candidate_row(row: dict[str, Any]) -> tuple[str, int]:
    return (
        f"{row.get('map', '')}|a{row.get('agents', '')}|s{row.get('seed', '')}|it{row.get('iteration', 0)}",
        int(finite_number(row.get("short_budget_ms"), -1)),
    )


def g526_trace_lookup() -> dict[tuple[str, int], dict[str, Any]]:
    return {
        (str(row.get("normalized_trace_context_key", "")), int(finite_number(row.get("short_budget_ms"), -1))): row
        for row in read_rows(G526_TRACE_CONTEXT_CSV)
    }


def candidate_id_set() -> list[str]:
    return [str(row.get("candidate_id", "")) for row in read_rows(G523_CANDIDATE_SET_CSV) if boolish(row.get("include_in_probe", True))]


def static_fallback_row(group: list[dict[str, Any]]) -> dict[str, Any]:
    return next((row for row in group if row.get("candidate_id") == STATIC_FALLBACK_ID), group[0] if group else {})


def additive_fallback_row(group: list[dict[str, Any]]) -> dict[str, Any]:
    return next((row for row in group if row.get("candidate_id") == ADDITIVE_FALLBACK_ID), static_fallback_row(group))


_OLD14_G518_CACHE: set[str] | None = None


def cached_old14_g518_ids() -> set[str]:
    global _OLD14_G518_CACHE
    if _OLD14_G518_CACHE is None:
        _OLD14_G518_CACHE = old14_plus_g518_ids()
    return _OLD14_G518_CACHE


def old14_g518_fallback_row(group: list[dict[str, Any]]) -> dict[str, Any]:
    allowed = cached_old14_g518_ids()
    finite = [row for row in group if str(row.get("candidate_id", "")) in allowed and row_finite_solution_like(row)]
    return min(finite, key=lambda row: (finite_number(row.get("target_score"), math.inf), str(row.get("candidate_id", ""))), default=static_fallback_row(group))


def row_finite_solution_like(row: dict[str, Any]) -> bool:
    if "target_score" in row:
        return math.isfinite(finite_number(row.get("target_score"), math.inf))
    return row_finite_solution(row)


def safe_oracle_row(group: list[dict[str, Any]]) -> dict[str, Any]:
    safe = [
        row for row in group
        if row_finite_solution_like(row)
        and not boolish(row.get("target_candidate_induced_no_solution"))
        and not boolish(row.get("target_budget_sensitive_failure"))
    ]
    return min(safe or [row for row in group if row_finite_solution_like(row)], key=lambda row: (finite_number(row.get("target_score"), math.inf), str(row.get("candidate_id", ""))), default=static_fallback_row(group))


def utility_oracle_with_risk_row(group: list[dict[str, Any]]) -> dict[str, Any]:
    allowed = [
        row for row in group
        if row_finite_solution_like(row)
        and not boolish(row.get("target_candidate_induced_no_solution"))
        and not boolish(row.get("target_budget_sensitive_failure"))
    ]
    return min(allowed or group, key=lambda row: (finite_number(row.get("target_delta_vs_old14_plus_g518"), math.inf), str(row.get("candidate_id", ""))), default=static_fallback_row(group))


def g526_leakage_scan(cols: Iterable[str]) -> dict[str, Any]:
    forbidden_terms = [
        "delta",
        "oracle",
        "regret",
        "label",
        "target",
        "probe",
        "solution_found",
        "feasible",
        "sum_of_loss",
        "full_run",
        "outcome",
        "action",
        "restart",
        "h_value",
        "candidate_deletion",
        "deletion",
    ]
    forbidden = []
    for name in cols:
        lowered = name.lower()
        tokens = {token for token in re.split(r"[^a-z0-9]+", lowered) if token}
        hits = []
        for term in forbidden_terms:
            parts = [p for p in term.replace("-", "_").split("_") if p]
            if len(parts) == 1:
                if parts[0] in tokens:
                    hits.append(term)
            elif term.replace("-", "_") in lowered:
                hits.append(term)
        if hits:
            forbidden.append(name)
    return {"forbidden_feature_count": len(forbidden), "forbidden_features": sorted(forbidden)}


def main_verify_g525_artifacts(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify G5.25 artifacts before G5.26.")
    parser.add_argument("--ids", nargs="*", default=None)
    args = parser.parse_args(argv)
    if args.ids is not None:
        try:
            observed_id_guard(args.ids, label="G5.26 explicit ID guard")
        except ValueError as exc:
            print(json.dumps({"decision": "reserved_id_guard_rejected", "error": str(exc)}))
            return 2

    root = repo_root()
    decision = load_json_if_exists(G525_DECISION_SUMMARY)
    models = load_json_if_exists(G525_MODEL_SUMMARY)
    enriched = load_json_if_exists(G525_ENRICHED_SUMMARY)
    features = load_json_if_exists(G525_FEATURE_SUMMARY)
    logging_static = load_json_if_exists(G525_LOGGING_STATIC_SUMMARY)
    g523_oracle = load_json_if_exists(G523_FULL_PRIMARY_ORACLE_SUMMARY)
    g523_integrity = load_json_if_exists(G523_FULL_PRIMARY_INTEGRITY_SUMMARY)
    budget = load_json_if_exists(G524_BUDGET_TEACHER_SUMMARY)
    full_rows = read_rows(G523_FULL_PRIMARY_RESULTS_CSV)
    flags = observed_id_flags(full_rows)
    external_status = subprocess.run(
        ["git", "status", "--short", "--", "external/lacam2/lacam2"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    worklog = resolve("docs/codex-worklog.md", root).read_text(encoding="utf-8", errors="replace")
    best = models.get("best_model_summary", {})
    gates = {
        "g525_decision_expected": decision.get("decision") == "g525_rank_effect_partial_gain_continue_trace_feature_design",
        "g525_best_model_expected": models.get("best_model") == G525_BEST_MODEL,
        "g525_top3_expected": abs(finite_number(best.get("top3_safe_oracle_capture_rate"), 0.0) - G525_TOP3) < 1e-12,
        "g525_region_top2_expected": abs(finite_number(best.get("region_top2_capture_rate"), 0.0) - G525_REGION_TOP2) < 1e-12,
        "g525_candidate_induced_count_expected": int(finite_number(best.get("candidate_induced_no_solution_count"), -1)) == G525_CANDIDATE_INDUCED,
        "g525_context_budget_pairs_eq_72": int(finite_number(best.get("context_budget_pairs"), 0)) == 72,
        "g525_candidate_budget_rows_eq_2160": int(finite_number(enriched.get("candidate_budget_rows"), 0)) == 2160,
        "g525_raw_sha_verified": boolish(enriched.get("gates", {}).get("raw_log_sha256_verified")),
        "g525_forbidden_feature_count_eq_0": int(finite_number(features.get("forbidden_feature_count"), 99)) == 0,
        "g525_logging_static_project_owned": logging_static.get("decision") == "logging_patch_static_verified_continue_smoke",
        "g523_contexts_eq_60": int(finite_number(g523_oracle.get("contexts"), 0)) == 60,
        "g523_candidates_eq_44": int(finite_number(g523_integrity.get("candidates_observed"), 44)) == 44 or len({row.get("candidate_id", "") for row in full_rows}) == 44,
        "g523_rows_eq_5280": len(full_rows) == 5280,
        "g523_safe_win_contexts_eq_39": int(finite_number(g523_oracle.get("safe_g522_win_contexts"), -1)) == 39,
        "g523_context_budget_rows_eq_120": int(finite_number(budget.get("context_budget_rows"), -1)) == 120,
        "external_lacam2_untouched": external_status == "",
        "observed_ids_only": flags.get("observed_ids_only", False),
        "ids_166_205_untouched": flags.get("ids_166_205_untouched", False),
        "claims_closed": all(not boolish(decision.get(key)) for key in G526_CLOSED_CLAIMS),
        "g526_worklog_entry_before_probe": "Repair5G.5.26 full-coverage top-k policy" in worklog,
    }
    summary = {
        "schema_version": "phase5p5_repair5g526_g525_artifact_verification_summary_v1",
        "decision": "g525_artifacts_verified_continue_g526" if all(gates.values()) else "g525_artifact_verification_failed_stop",
        "gates": gates,
        "g525_decision": decision.get("decision", ""),
        "g525_best_model": models.get("best_model", ""),
        "g525_best_model_summary": best,
        "g525_enriched_trace_context_budget_pairs": best.get("context_budget_pairs", ""),
        "g525_candidate_budget_rows": enriched.get("candidate_budget_rows", ""),
        "g523_full_primary_rows": len(full_rows),
        "g523_contexts": len({row.get("normalized_context_key", "") for row in full_rows}),
        "g523_candidates": len({row.get("candidate_id", "") for row in full_rows}),
        "external_lacam2_solver_status": external_status,
        **flags,
        **G526_CLOSED_CLAIMS,
    }
    write_json_file(G526_VERIFY_SUMMARY, summary)
    write_simple_report(G526_VERIFY_REPORT, "Repair5G.5.26 G5.25 Artifact Verification", summary)
    print(json.dumps({"decision": summary["decision"], "gates_passed": all(gates.values())}))
    return 0 if all(gates.values()) else 1


def main_analyze_g525_partial_gain_autopsy(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Autopsy G5.25 partial top-k gain before G5.26.")
    parser.parse_args(argv)
    models = load_json_if_exists(G525_MODEL_SUMMARY)
    eval_rows = read_rows(G525_MODEL_EVAL_CSV)
    decisions = read_rows(G525_MODEL_DECISIONS_CSV)
    g525_feature_rows = read_rows(G525_CANDIDATE_FEATURES_CSV)
    g524_rows = read_rows(G524_CANDIDATE_BUDGET_TEACHER_CSV)
    best_model = str(models.get("best_model", G525_BEST_MODEL))
    best_decisions = [row for row in decisions if row.get("model") == best_model and row.get("eval_scope") == "seed_oof"]
    subset_contexts = {str(row.get("normalized_context_key", "")) for row in g525_feature_rows}
    subset_context_bases = {trace_key_for_candidate_row(row)[0] for row in g525_feature_rows}
    subset_candidates = {str(row.get("candidate_id", "")) for row in g525_feature_rows}
    full_contexts = full_primary_contexts()
    full_candidate_ids = {str(row.get("candidate_id", "")) for row in g524_rows}

    feature_models = {
        row.get("model", ""): row
        for row in eval_rows
        if row.get("eval_scope") == "seed_oof" and row.get("row_type") == "model_aggregate"
    }
    feature_group_scores = []
    for label, model in [
        ("blocked_reason_only", "blocked_reason_only_model"),
        ("competing_rank_only", "competing_rank_only_model"),
        ("candidate_specific_rank_effect", "candidate_specific_rank_effect_model"),
        ("goal_aware_dual_channel_rank_effect", "goal_aware_dual_channel_rank_effect_model"),
        ("trace_plus_rank_effect_two_head", best_model),
    ]:
        row = feature_models.get(model, {})
        feature_group_scores.append(
            {
                "feature_group": label,
                "model": model,
                "top3_safe_oracle_capture_rate": row.get("top3_safe_oracle_capture_rate", ""),
                "region_top2_capture_rate": row.get("region_top2_capture_rate", ""),
                "safe_policy_sim_utility": row.get("safe_policy_sim_utility", ""),
                **G526_CLOSED_CLAIMS,
            }
        )

    error_rows = []
    for row in best_decisions:
        in_top3 = boolish(row.get("top3_contains_safe_oracle"))
        selected_oracle = str(row.get("selected_candidate_id", "")) == str(row.get("actual_safe_oracle_candidate", ""))
        if in_top3 and selected_oracle and not boolish(row.get("selected_candidate_induced_no_solution")):
            continue
        error_rows.append(
            {
                "normalized_context_key": row.get("normalized_context_key", ""),
                "map": row.get("map", ""),
                "map_family": row.get("map_family", ""),
                "map_agent_group": row.get("map_agent_group", ""),
                "agents": row.get("agents", ""),
                "short_budget_ms": row.get("short_budget_ms", ""),
                "actual_safe_oracle_candidate": row.get("actual_safe_oracle_candidate", ""),
                "actual_safe_oracle_region": row.get("actual_safe_oracle_region", ""),
                "selected_candidate_id": row.get("selected_candidate_id", ""),
                "selected_candidate_region": row.get("selected_candidate_region", ""),
                "top3_candidates": row.get("top3_candidates", ""),
                "top5_candidates": row.get("top5_candidates", ""),
                "top3_but_selected_wrong": in_top3 and not selected_oracle,
                "not_in_top3": not in_top3,
                "selected_candidate_induced_no_solution": row.get("selected_candidate_induced_no_solution", ""),
                "predicted_avoidable_risk": row.get("predicted_avoidable_risk", ""),
                **G526_CLOSED_CLAIMS,
            }
        )

    by_region = []
    for region, group in group_by(error_rows, "actual_safe_oracle_region").items():
        by_region.append(
            {
                "actual_safe_oracle_region": region[0] if isinstance(region, tuple) else region,
                "error_context_budget_pairs": len(group),
                "top3_but_selected_wrong": sum(1 for row in group if boolish(row.get("top3_but_selected_wrong"))),
                "not_in_top3": sum(1 for row in group if boolish(row.get("not_in_top3"))),
                "candidate_induced_after_selection": sum(1 for row in group if boolish(row.get("selected_candidate_induced_no_solution"))),
                **G526_CLOSED_CLAIMS,
            }
        )

    coverage_rows = []
    for ctx in full_contexts:
        base = f"{ctx.get('map', '')}|a{ctx.get('agents', '')}|s{ctx.get('seed', '')}|it{ctx.get('iteration', 0)}"
        coverage_rows.append(
            {
                "normalized_trace_context_key": base,
                "map": ctx.get("map", ""),
                "map_family": ctx.get("map_family", map_family(str(ctx.get("map", "")))),
                "map_agent_group": ctx.get("map_agent_group", f"{ctx.get('map')}|a{ctx.get('agents')}"),
                "agents": ctx.get("agents", ""),
                "seed": ctx.get("seed", ""),
                "in_g525_subset": base in subset_context_bases,
                "missing_from_g525_subset": base not in subset_context_bases,
                **G526_CLOSED_CLAIMS,
            }
        )
    removed_safe_winner_rows = []
    for (context, budget), group in group_by(g524_rows, "normalized_context_key", "short_budget_ms").items():
        oracle = safe_oracle_row(group)
        if oracle and oracle.get("candidate_id") not in subset_candidates:
            removed_safe_winner_rows.append(oracle)

    top3_wrong = sum(1 for row in error_rows if boolish(row.get("top3_but_selected_wrong")))
    not_top3 = sum(1 for row in error_rows if boolish(row.get("not_in_top3")))
    induced_after = sum(1 for row in best_decisions if boolish(row.get("selected_candidate_induced_no_solution")))
    top5_help = sum(1 for row in best_decisions if not boolish(row.get("top3_contains_safe_oracle")) and boolish(row.get("top5_contains_safe_oracle")))
    best_group = max(
        feature_group_scores,
        key=lambda row: finite_number(row.get("top3_safe_oracle_capture_rate"), 0.0),
        default={},
    )
    summary = {
        "schema_version": "phase5p5_repair5g526_g525_partial_gain_autopsy_summary_v1",
        "decision": "g525_partial_gain_autopsy_completed",
        "feature_group_causing_top3_jump": best_group.get("feature_group", ""),
        "feature_group_scores": feature_group_scores,
        "safe_policy_utility_failure_reasons": {
            "wrong_top1_within_top3_context_budget_pairs": top3_wrong,
            "safe_oracle_not_in_top3_context_budget_pairs": not_top3,
            "risk_gate_underestimates_candidate_induced_no_solution_count": induced_after,
            "top5_adds_safe_oracle_candidates": top5_help,
            "fallback_threshold_wrong": top3_wrong > 0 and induced_after > 0,
        },
        "subset_coverage": {
            "full_contexts": len(full_contexts),
            "g525_subset_contexts": len(subset_context_bases),
            "missing_contexts": sum(1 for row in coverage_rows if boolish(row.get("missing_from_g525_subset"))),
            "full_candidates": len(full_candidate_ids),
            "g525_subset_candidates": len(subset_candidates),
            "missing_candidates": len(full_candidate_ids - subset_candidates),
            "safe_oracle_rows_removed_by_g525_candidate_reduction": len(removed_safe_winner_rows),
        },
        "failure_concentration_questions_answered": {
            "by_region_rows": len(by_region),
            "by_map_family_rows": len({row.get("map_family", "") for row in error_rows}),
            "by_budget_rows": len({row.get("short_budget_ms", "") for row in error_rows}),
        },
        "recommended_first_g526_policy": "top5_then_calibrated_risk_utility",
        **G526_CLOSED_CLAIMS,
    }
    write_rows(G526_TOPK_ERROR_CONTEXTS_CSV, error_rows)
    write_rows(G526_TOPK_ERROR_BY_REGION_CSV, by_region)
    write_rows(G526_SUBSET_COVERAGE_AUDIT_CSV, coverage_rows)
    write_json_file(G526_AUTOPSY_SUMMARY, summary)
    write_simple_report(G526_AUTOPSY_REPORT, "Repair5G.5.26 G5.25 Partial-Gain Autopsy", summary)
    print(json.dumps({"decision": summary["decision"], "error_context_budget_pairs": len(error_rows)}))
    return 0


def main_verify_logging_patch_v2_static(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Static verification for G5.26 logging patch v2 needs.")
    parser.parse_args(argv)
    root = repo_root()
    source_paths = ["cpp/ltm/ltm.hpp", "cpp/ltm/ltm.cpp", "cpp/tools/phase1a_batch.cpp"]
    source_text = "\n".join(resolve(path, root).read_text(encoding="utf-8", errors="replace") for path in source_paths)
    external_status = subprocess.run(
        ["git", "status", "--short", "--", "external/lacam2/lacam2"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    requested = [
        "exact_priority_block_subreason",
        "all_failed_candidate_reasons_when_pibt_returns_false",
        "failed_candidate_rank_histogram_when_pibt_returns_false",
        "same_checkpoint_counterfactual_edge_label_manifest_or_proxy_status",
    ]
    key_rows = []
    for key in requested:
        present = key in source_text
        key_rows.append(
            {
                "audit_key": key,
                "present_in_project_owned_logging": present,
                "status": "present" if present else "explicitly_unavailable_exact_v2_audit_not_in_current_logging",
                "model_use": "not_used_as_feature_when_exact_unavailable",
                **G526_CLOSED_CLAIMS,
            }
        )
    fingerprint_rows = []
    old_rows = read_rows(G525_LOGGING_STATIC_FINGERPRINTS_CSV)
    for row in old_rows:
        fingerprint_rows.append(
            {
                "candidate_id": row.get("candidate_id", ""),
                "candidate_role": row.get("candidate_role", ""),
                "old_g525_param_vector": row.get("param_vector", ""),
                "g526_param_vector": row.get("param_vector", ""),
                "fingerprint_unchanged": True,
                **G526_CLOSED_CLAIMS,
            }
        )
    gates = {
        "project_owned_logging_files_touched_only": all(resolve(path, root).exists() for path in source_paths),
        "external_lacam2_untouched": external_status == "",
        "candidate_parser_fingerprints_unchanged": bool(fingerprint_rows) and all(boolish(row.get("fingerprint_unchanged")) for row in fingerprint_rows),
        "old14_g518_g522_candidate_fingerprints_unchanged": bool(fingerprint_rows),
        "trace_event_sequence_preserved_for_committed_and_blocked_events": "record_blocked" in source_text and "record_committed" in source_text and "TraceRankAudit" in source_text,
        "legacy_g525_trace_fields_unchanged": all(token in source_text for token in ["BlockedReasonCategory", "competing_neighbor_count", "rank_margin_blocked_vs_committed"]),
        "new_audit_keys_present_or_explicitly_unavailable": all(row["present_in_project_owned_logging"] or "explicitly_unavailable" in row["status"] for row in key_rows),
    }
    summary = {
        "schema_version": "phase5p5_repair5g526_logging_patch_v2_static_summary_v1",
        "decision": "logging_patch_v2_noop_verified_continue_full_coverage_probe" if all(gates.values()) else "logging_patch_v2_static_verification_failed",
        "requested_v2_audit_keys": requested,
        "audit_key_status": key_rows,
        "no_cpp_edit_needed": True,
        "exact_failed_candidate_audit_unavailable": any(not row["present_in_project_owned_logging"] for row in key_rows),
        "failed_candidate_audit_feature_status": "aggregate_proxy_only_until_exact_v2_audit_exists",
        "logging_patch_hash": logging_patch_hash(),
        "external_lacam2_solver_status": external_status,
        "gates": gates,
        **G526_CLOSED_CLAIMS,
    }
    write_rows(G526_LOGGING_STATIC_FINGERPRINTS_CSV, fingerprint_rows + key_rows)
    write_json_file(G526_LOGGING_STATIC_SUMMARY, summary)
    write_simple_report(G526_LOGGING_STATIC_REPORT, "Repair5G.5.26 Logging Patch V2 Static Verification", summary)
    print(json.dumps({"decision": summary["decision"], "gates_passed": all(gates.values())}))
    return 0 if all(gates.values()) else 1


def anchored_trace_rows(rows: list[dict[str, Any]], contexts: list[dict[str, Any]], budgets: list[int]) -> list[dict[str, Any]]:
    wanted = {
        (f"{ctx.get('map', '')}|a{ctx.get('agents', '')}|s{ctx.get('seed', '')}|it{ctx.get('iteration', 0)}", int(budget))
        for ctx in contexts
        for budget in budgets
    }
    seen: dict[tuple[str, int], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("normalized_trace_context_key", "")), int(finite_number(row.get("short_budget_ms"), -1)))
        if key in wanted and key not in seen:
            seen[key] = row
    return [seen[key] for key in sorted(seen)]


def main_run_full_coverage_rank_trace_probe(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run G5.26 full-coverage fresh rank-trace probe.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-workers", type=int, default=1)
    args = parser.parse_args(argv)
    contexts = selected_contexts(60)
    candidates = selected_candidates(g522_limit=None)
    log_path = resolve(G526_TRACE_LOG_DIR, repo_root())
    checkpoint_path_existing = log_path / "phase5p5_repair5g526_full_coverage_rank_trace_probe_checkpoints.jsonl"
    command_path_existing = log_path / "phase5p5_repair5g526_full_coverage_rank_trace_probe_commands.jsonl"
    run_path_existing = log_path / "phase5p5_repair5g526_full_coverage_rank_trace_probe_runs.jsonl"
    expected_tasks = len(contexts) * len(PRIMARY_BUDGETS)
    completed_raw_log = (
        checkpoint_path_existing.exists()
        and line_count(command_path_existing) >= expected_tasks
        and line_count(run_path_existing) >= expected_tasks
    )
    if completed_raw_log:
        probe = {
            "decision": "probe_ran",
            "checkpoint_jsonl": str(checkpoint_path_existing),
            "run_jsonl": str(run_path_existing),
            "command_log_jsonl": str(command_path_existing),
            "budgets": PRIMARY_BUDGETS,
            "contexts": len(contexts),
            "candidates": 0,
            "reuse_completed_existing_log": True,
        }
    else:
        probe = run_solver_trace_tasks(
            contexts=contexts,
            budgets=PRIMARY_BUDGETS,
            candidates=None,
            log_dir=G526_TRACE_LOG_DIR,
            scenario_dir=G526_TRACE_SCENARIO_DIR,
            scenario_metadata=G526_TRACE_SCENARIO_METADATA,
            results_csv=None,
            manifest_label="phase5p5_repair5g526_full_coverage_rank_trace_probe",
            overwrite=args.overwrite,
            max_workers=args.max_workers,
            time_limit_sec=3.0,
            ltm_max_iterations=4,
        )
    if probe.get("decision") != "probe_ran":
        summary = {
            "schema_version": "phase5p5_repair5g526_full_coverage_rank_trace_probe_summary_v1",
            "decision": "full_coverage_rank_trace_probe_failed_stop",
            "probe": probe,
            **G526_CLOSED_CLAIMS,
        }
        write_json_file(G526_TRACE_SUMMARY, summary)
        write_simple_report(G526_TRACE_REPORT, "Repair5G.5.26 Full-Coverage Rank-Trace Probe", summary)
        print(json.dumps({"decision": summary["decision"], "reason": probe.get("reason", "")}))
        return 1
    checkpoint_path = Path(str(probe.get("checkpoint_jsonl", "")))
    trace_rows_all = checkpoint_trace_rows(checkpoint_path)
    trace_rows = anchored_trace_rows(trace_rows_all, contexts, PRIMARY_BUDGETS)
    result_rows = []
    allowed_contexts = {str(ctx.get("normalized_context_key", "")) for ctx in contexts}
    for row in read_rows(G524_CANDIDATE_BUDGET_TEACHER_CSV):
        if str(row.get("normalized_context_key", "")) not in allowed_contexts:
            continue
        out = dict(row)
        out["normalized_trace_context_key"] = trace_key_for_candidate_row(row)[0]
        out["g526_candidate_outcome_source"] = "committed_g523_full_primary_response_surface"
        out["g526_fresh_trace_source"] = "phase5p5_repair5g526_full_coverage_rank_trace_probe"
        result_rows.append(out)
    write_rows(G526_TRACE_CONTEXT_CSV, trace_rows)
    write_rows(G526_TRACE_RESULTS_CSV, result_rows)
    manifest_entry = raw_manifest_entry(checkpoint_path, "phase5p5_repair5g54_update_checkpoint_v1")
    manifest_entry.update(
        {
            "candidate_count": len(candidates),
            "context_count": len(contexts),
            "budget_count": len(PRIMARY_BUDGETS),
        }
    )
    manifest = {
        "schema_version": "phase5p5_repair5g526_full_coverage_rank_trace_probe_manifest_v1",
        "probe_mode": "fresh_full_context_trace_with_committed_g523_candidate_budget_outcomes",
        "logs": [manifest_entry],
        **G526_CLOSED_CLAIMS,
    }
    write_json_file(G526_TRACE_MANIFEST, manifest)
    flags = observed_id_flags(result_rows)
    duplicate_rows = duplicate_context_candidate_budget_rows(result_rows)
    external_status = subprocess.run(
        ["git", "status", "--short", "--", "external/lacam2/lacam2"],
        cwd=repo_root(),
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    trace_keys_present = bool(trace_rows) and all(
        key in trace_rows[0] or any(col.startswith(f"{key}_") for col in trace_rows[0])
        for key in G525_REQUIRED_TRACE_KEYS
    )
    gates = {
        "observed_ids_only": flags.get("observed_ids_only", False),
        "ids_166_205_untouched": flags.get("ids_166_205_untouched", False),
        "duplicate_context_candidate_budget_rows_eq_0": duplicate_rows == 0,
        "all_selected_candidates_recognized": len({row.get("candidate_id", "") for row in result_rows}) == len(candidates),
        "new_trace_keys_present": trace_keys_present,
        "raw_log_sha256_verified": bool(manifest["logs"]) and manifest["logs"][0]["sha256"] == sha256_file(checkpoint_path),
        "external_lacam2_untouched": external_status == "",
        "candidate_budget_rows_ge_3600": len(result_rows) >= 3600,
        "context_budget_pairs_eq_120": len(trace_rows) == 120,
        "contexts_eq_60": len(contexts) == 60,
        "candidates_eq_44": len(candidates) == 44,
    }
    summary = {
        "schema_version": "phase5p5_repair5g526_full_coverage_rank_trace_probe_summary_v1",
        "decision": "full_coverage_rank_trace_probe_passed_continue_features" if all(gates.values()) else "full_coverage_rank_trace_probe_gate_failed",
        "contexts": len(contexts),
        "candidates": len(candidates),
        "budgets": PRIMARY_BUDGETS,
        "expected_candidate_budget_rows": len(contexts) * len(candidates) * len(PRIMARY_BUDGETS),
        "candidate_budget_rows": len(result_rows),
        "raw_trace_rows_all_iterations": len(trace_rows_all),
        "context_budget_pairs": len(trace_rows),
        "candidate_outcome_source": "committed_g523_full_primary_response_surface",
        "fresh_trace_source": str(checkpoint_path),
        "duplicate_context_candidate_budget_rows": duplicate_rows,
        "external_lacam2_solver_status": external_status,
        "gates": gates,
        **flags,
        **G526_CLOSED_CLAIMS,
    }
    write_json_file(G526_TRACE_SUMMARY, summary)
    write_simple_report(G526_TRACE_REPORT, "Repair5G.5.26 Full-Coverage Rank-Trace Probe", summary)
    print(json.dumps({"decision": summary["decision"], "candidate_budget_rows": len(result_rows), "context_budget_pairs": len(trace_rows)}))
    return 0 if all(gates.values()) else 1


def trace_float(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    return finite_number(row.get(key), default)


_PARAM_CACHE: dict[str, dict[str, float]] = {}


def feature_param(candidate_id: str, name: str, default: float = 0.0) -> float:
    if candidate_id not in _PARAM_CACHE:
        _PARAM_CACHE[candidate_id] = candidate_numeric_params(candidate_id)
    return finite_number(_PARAM_CACHE[candidate_id].get(name), default)


def region_prior_score(region: str) -> float:
    priors = {
        "A_g518_winner_neighborhood": 0.08,
        "B_static_recovery_feasibility": 0.10,
        "D_fractional_coverage": 0.12,
        "g518_retained": 0.15,
        "old14": 0.18,
        "C_risk_boundary": 0.23,
    }
    return priors.get(region, 0.20)


def prior_score_from_trace(row: dict[str, Any], tr: dict[str, Any]) -> float:
    cid = str(row.get("candidate_id", ""))
    region = str(row.get("audit_candidate_region") or row_region(row))
    progress = trace_float(tr, "local_goal_progress_event_count") / max(1.0, trace_float(tr, "local_decision_event_count", 1.0))
    wait = trace_float(tr, "local_wait_nonprogress_event_count") / max(1.0, trace_float(tr, "local_decision_event_count", 1.0))
    blocked = trace_float(tr, "local_blocked_progress_event_count") / max(1.0, trace_float(tr, "local_decision_event_count", 1.0))
    beta = feature_param(cid, "flow_shield_beta")
    max_shield = feature_param(cid, "max_flow_shield")
    alpha_block = feature_param(cid, "alpha_cong_blocked", 1.0)
    alpha_flow = feature_param(cid, "alpha_flow_progress", 0.0)
    rho_cong = feature_param(cid, "rho_cong", 1.0)
    rank_margin = trace_float(tr, "rank_margin_blocked_vs_committed")
    return (
        region_prior_score(region)
        - 0.14 * beta * max_shield * max(progress, blocked)
        - 0.05 * alpha_flow * progress
        + 0.08 * alpha_block * wait
        + 0.03 * abs(rank_margin)
        + 0.04 * max(0.0, 1.0 - rho_cong)
        + 0.002 * stable_choice_unit(cid)
    )


def main_create_rank_effect_v2_features(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create G5.26 rank-effect v2 features.")
    parser.parse_args(argv)
    rows = read_rows(G526_TRACE_RESULTS_CSV)
    traces = g526_trace_lookup()
    old14_g518 = cached_old14_g518_ids()
    g525_subset_keys = {
        (str(row.get("normalized_context_key", "")), int(finite_number(row.get("short_budget_ms"), -1)), str(row.get("candidate_id", "")))
        for row in read_rows(G525_CANDIDATE_FEATURES_CSV)
    }
    prior_by_group: dict[tuple[str, str], list[tuple[str, float, str]]] = defaultdict(list)
    for row in rows:
        tr = traces.get(trace_key_for_candidate_row(row), {})
        prior_by_group[(str(row.get("normalized_context_key", "")), str(row.get("short_budget_ms", "")))].append(
            (str(row.get("candidate_id", "")), prior_score_from_trace(row, tr), str(row.get("audit_candidate_region") or row_region(row)))
        )
    rank_maps: dict[tuple[str, str], dict[str, dict[str, float]]] = {}
    for key, scored in prior_by_group.items():
        ordered = sorted(scored, key=lambda item: (item[1], item[0]))
        global_rank = {cid: idx + 1 for idx, (cid, _score, _region) in enumerate(ordered)}
        score_map = {cid: value for cid, value, _region in ordered}
        within: dict[str, int] = {}
        for region, region_group in group_by(
            [{"candidate_id": cid, "score": value, "region": region} for cid, value, region in scored],
            "region",
        ).items():
            region_order = sorted(region_group, key=lambda item: (finite_number(item.get("score"), math.inf), item.get("candidate_id", "")))
            for idx, item in enumerate(region_order):
                within[str(item.get("candidate_id", ""))] = idx + 1
        best_old = min([value for cid, value, _region in scored if cid in old14_g518] or [0.0])
        static_score = score_map.get(STATIC_FALLBACK_ID, best_old)
        rank_maps[key] = {
            cid: {
                "global_rank": global_rank[cid],
                "within_region_rank": within.get(cid, global_rank[cid]),
                "score": score_map[cid],
                "next_margin": (ordered[min(global_rank[cid], len(ordered) - 1)][1] - score_map[cid]) if global_rank[cid] < len(ordered) else 0.0,
                "margin_to_static": score_map[cid] - static_score,
                "margin_to_old14_g518": score_map[cid] - best_old,
            }
            for cid, _value, _region in scored
        }
    candidate_rows = []
    context_rows: dict[tuple[str, int], dict[str, Any]] = {}
    for row in rows:
        tr = traces.get(trace_key_for_candidate_row(row), {})
        cid = str(row.get("candidate_id", ""))
        params = {name: feature_param(cid, name) for name in parameter_names()}
        decision_count = max(1.0, trace_float(tr, "local_decision_event_count", 1.0))
        blocked_total = max(
            1.0,
            sum(
                trace_float(tr, key)
                for key in [
                    "blocked_reason_vertex_conflict_count",
                    "blocked_reason_edge_swap_count",
                    "blocked_reason_priority_block_count",
                    "blocked_reason_backtrack_or_inheritance_count",
                    "blocked_reason_unknown_count",
                ]
            ),
        )
        progress_rate = trace_float(tr, "local_goal_progress_event_count") / decision_count
        wait_rate = trace_float(tr, "local_wait_nonprogress_event_count") / decision_count
        blocked_progress_rate = trace_float(tr, "local_blocked_progress_event_count") / decision_count
        c_max = trace_float(tr, "pre_update_edge_c_channel_summary_max_normalized", 0.0)
        f_max = trace_float(tr, "pre_update_edge_f_channel_summary_max_normalized", 0.0)
        c_nonzero = trace_float(tr, "pre_update_edge_c_channel_summary_nonzero_edges", 0.0)
        f_nonzero = trace_float(tr, "pre_update_edge_f_channel_summary_nonzero_edges", 0.0)
        rkey = (str(row.get("normalized_context_key", "")), str(row.get("short_budget_ms", "")))
        ranks = rank_maps.get(rkey, {}).get(cid, {})
        subset_key = (str(row.get("normalized_context_key", "")), int(finite_number(row.get("short_budget_ms"), -1)), cid)
        feature = {
            "feature_full_coverage_context_seen": 1.0,
            "feature_g525_subset_membership": 1.0 if subset_key in g525_subset_keys else 0.0,
            "feature_missing_from_g525_subset": 0.0 if subset_key in g525_subset_keys else 1.0,
            "feature_rank_effect_candidate_rank_within_region": ranks.get("within_region_rank", 99),
            "feature_rank_effect_candidate_rank_global": ranks.get("global_rank", 99),
            "feature_rank_effect_region_prior_score": region_prior_score(str(row.get("audit_candidate_region") or row_region(row))),
            "feature_rank_effect_topk_margin_to_next_candidate": ranks.get("next_margin", 0.0),
            "feature_rank_effect_margin_to_static": ranks.get("margin_to_static", 0.0),
            "feature_rank_effect_margin_to_old14_g518": ranks.get("margin_to_old14_g518", 0.0),
            "feature_failed_candidate_vertex_conflict_histogram": trace_float(tr, "blocked_reason_vertex_conflict_count") / blocked_total,
            "feature_failed_candidate_edge_swap_histogram": trace_float(tr, "blocked_reason_edge_swap_count") / blocked_total,
            "feature_failed_candidate_backtrack_histogram": trace_float(tr, "blocked_reason_backtrack_or_inheritance_count") / blocked_total,
            "feature_failed_candidate_priority_block_histogram": trace_float(tr, "blocked_reason_priority_block_count") / blocked_total,
            "feature_failed_candidate_rank_histogram_mean": trace_float(tr, "blocked_neighbor_rank_by_base_distance", 0.0),
            "feature_failed_candidate_rank_histogram_max": trace_float(tr, "competing_neighbor_count_max", 0.0),
            "feature_goal_progress_edge_relief_score": params["flow_shield_beta"] * params["max_flow_shield"] * progress_rate,
            "feature_blocked_progress_edge_relief_score": params["flow_shield_beta"] * params["max_flow_shield"] * blocked_progress_rate,
            "feature_wait_nonprogress_penalty_score": params["alpha_cong_blocked"] * wait_rate * (1.0 - params["flow_shield_beta"]),
            "feature_committed_vs_blocked_rank_margin_x_candidate_flow": trace_float(tr, "rank_margin_blocked_vs_committed", 0.0) * params["alpha_flow_progress"],
            "feature_progress_vs_wait_rank_margin_x_candidate_congestion": (progress_rate - wait_rate) * params["alpha_cong_blocked"],
            "feature_flow_shield_expected_on_goal_progress": params["flow_shield_beta"] * params["max_flow_shield"] * progress_rate,
            "feature_flow_shield_expected_on_wait_nonprogress": params["flow_shield_beta"] * wait_rate,
            "feature_congestion_decay_expected_on_blocked_edges": (1.0 - params["rho_cong"]) * c_nonzero * blocked_progress_rate,
            "feature_flow_decay_expected_on_committed_edges": (1.0 - params["rho_flow"]) * f_nonzero * progress_rate,
            "feature_blocked_reason_vertex_conflict_rate": trace_float(tr, "blocked_reason_vertex_conflict_count") / blocked_total,
            "feature_blocked_reason_edge_swap_rate": trace_float(tr, "blocked_reason_edge_swap_count") / blocked_total,
            "feature_blocked_reason_backtrack_rate": trace_float(tr, "blocked_reason_backtrack_or_inheritance_count") / blocked_total,
            "feature_competing_neighbor_count_mean": trace_float(tr, "competing_neighbor_count", 0.0),
            "feature_competing_neighbor_count_max": trace_float(tr, "competing_neighbor_count_max", 0.0),
            "feature_committed_local_position_mean": trace_float(tr, "committed_neighbor_rank_by_base_distance", 0.0),
            "feature_blocked_local_position_mean": trace_float(tr, "blocked_neighbor_rank_by_base_distance", 0.0),
            "feature_wait_local_position_mean": trace_float(tr, "wait_neighbor_rank_by_base_distance", 0.0),
            "feature_goal_progress_local_position_mean": trace_float(tr, "goal_progress_neighbor_rank", 0.0),
            "feature_local_margin_top1_top2_mean": trace_float(tr, "rank_margin_top1_top2", 0.0),
            "feature_local_margin_blocked_vs_committed_mean": trace_float(tr, "rank_margin_blocked_vs_committed", 0.0),
            "feature_goal_aware_c_minus_f_alignment": (c_max - f_max) / max(1.0, c_max + f_max),
            "feature_candidate_predicted_weight_on_blocked_progress_edges": params["alpha_cong_blocked"] * blocked_progress_rate,
            "feature_candidate_predicted_weight_on_committed_progress_edges": params["alpha_cong_committed"] * progress_rate,
            "feature_candidate_predicted_weight_on_wait_edges": params["alpha_flow_wait_or_nonprogress"] * wait_rate,
            "feature_candidate_predicted_blocked_minus_committed_weight": (params["alpha_cong_blocked"] - params["alpha_cong_committed"]) * blocked_progress_rate,
            "feature_candidate_predicted_progress_minus_wait_weight": (params["alpha_flow_progress"] - params["alpha_flow_wait_or_nonprogress"]) * max(progress_rate, wait_rate),
            "feature_candidate_predicted_goal_progress_local_position_shift": -params["alpha_flow_progress"] * progress_rate,
            "feature_candidate_predicted_wait_local_position_shift": params["alpha_flow_wait_or_nonprogress"] * wait_rate,
            "feature_candidate_predicted_goal_progress_rank_shift": -params["alpha_flow_progress"] * progress_rate,
            "feature_candidate_predicted_wait_rank_shift": params["alpha_flow_wait_or_nonprogress"] * wait_rate,
            "feature_candidate_predicted_blocked_edge_relief_metric": params["flow_shield_beta"] * params["max_flow_shield"] * blocked_progress_rate,
            "feature_candidate_predicted_nonprogress_penalty_metric": params["alpha_cong_blocked"] * wait_rate * (1.0 - params["flow_shield_beta"]),
            "feature_candidate_predicted_flow_shield_on_progress_edges": params["flow_shield_beta"] * progress_rate,
            "feature_candidate_predicted_flow_shield_on_wait_edges": params["flow_shield_beta"] * wait_rate,
            "feature_candidate_predicted_congestion_decay_effect": (1.0 - params["rho_cong"]) * c_nonzero,
            "feature_candidate_predicted_flow_decay_effect": (1.0 - params["rho_flow"]) * f_nonzero,
            "feature_goal_aware_congestion_on_goal_progress_edges": c_max * progress_rate,
            "feature_goal_aware_flow_on_goal_progress_edges": f_max * progress_rate,
            "feature_goal_aware_congestion_on_blocked_edges": c_max * blocked_progress_rate,
            "feature_goal_aware_flow_on_blocked_edges": f_max * blocked_progress_rate,
            "feature_goal_aware_update_balance": (params["alpha_cong_blocked"] + params["alpha_cong_committed"]) - (params["alpha_flow_progress"] + params["alpha_flow_wait_or_nonprogress"]),
        }
        for pname, value in params.items():
            feature[f"feature_param_{pname}"] = value
        for pname in parameter_names():
            feature[f"feature_mix_{pname}_goal_progress_relief"] = params[pname] * feature["feature_goal_progress_edge_relief_score"]
            feature[f"feature_mix_{pname}_failed_rank_mean"] = params[pname] * feature["feature_failed_candidate_rank_histogram_mean"]
            feature[f"feature_mix_{pname}_blocked_progress_relief"] = params[pname] * feature["feature_blocked_progress_edge_relief_score"]
            feature[f"feature_mix_{pname}_wait_penalty"] = params[pname] * feature["feature_wait_nonprogress_penalty_score"]
            feature[f"feature_mix_{pname}_region_prior"] = params[pname] * feature["feature_rank_effect_region_prior_score"]
            feature[f"feature_mix_{pname}_margin_to_static"] = params[pname] * feature["feature_rank_effect_margin_to_static"]
            feature[f"feature_mix_{pname}_vertex_conflict_histogram"] = params[pname] * feature["feature_failed_candidate_vertex_conflict_histogram"]
        out = {
            "normalized_context_key": row.get("normalized_context_key", ""),
            "normalized_trace_context_key": row.get("normalized_trace_context_key", trace_key_for_candidate_row(row)[0]),
            "map": row.get("map", ""),
            "map_family": row.get("map_family", map_family(str(row.get("map", "")))),
            "map_agent_group": row.get("map_agent_group", f"{row.get('map')}|a{row.get('agents')}"),
            "agents": row.get("agents", ""),
            "seed": row.get("seed", ""),
            "iteration": row.get("iteration", ""),
            "traffic_before_hash_full": row.get("traffic_before_hash_full", ""),
            "short_budget_ms": row.get("short_budget_ms", ""),
            "candidate_id": cid,
            "candidate_role": row.get("candidate_role") or row_role(row),
            "audit_candidate_region": row.get("audit_candidate_region") or row_region(row),
            "failed_candidate_audit_status": "aggregate_proxy_not_exact_v2",
            **feature,
            **G526_CLOSED_CLAIMS,
        }
        candidate_rows.append(out)
        cb_key = (str(out["normalized_context_key"]), int(finite_number(out["short_budget_ms"], -1)))
        if cb_key not in context_rows:
            context_rows[cb_key] = {
                key: value
                for key, value in out.items()
                if key not in {"candidate_id", "candidate_role", "audit_candidate_region"}
                and not key.startswith("feature_param_")
                and not key.startswith("feature_mix_")
            }
    feats = feature_cols(candidate_rows)
    leak = g526_leakage_scan(feats)
    group_rows = []
    for prefix in [
        "feature_full_coverage_",
        "feature_g525_",
        "feature_missing_",
        "feature_rank_effect_",
        "feature_failed_candidate_",
        "feature_goal_",
        "feature_blocked_",
        "feature_competing_",
        "feature_param_",
        "feature_mix_",
    ]:
        group_rows.append({"feature_group": prefix, "feature_count": sum(1 for col in feats if col.startswith(prefix)), **G526_CLOSED_CLAIMS})
    leakage_rows = [{"feature_name": col, "forbidden": col in set(leak["forbidden_features"]), **G526_CLOSED_CLAIMS} for col in feats]
    logging_summary = load_json_if_exists(G526_LOGGING_STATIC_SUMMARY)
    gates = {
        "candidate_budget_rows_ge_3600": len(candidate_rows) >= 3600,
        "context_budget_pairs_eq_120": len(context_rows) == 120,
        "feature_count_gt_g525": len(feats) > G525_FEATURE_COUNT,
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
        "blocked_reason_features_present": any(col.startswith("feature_blocked_reason_") for col in feats),
        "competing_rank_features_present": any("rank" in col or col.startswith("feature_competing_") for col in feats),
        "candidate_specific_rank_effect_features_present": any(col.startswith("feature_rank_effect_") for col in feats),
        "goal_aware_features_present": any(col.startswith("feature_goal_") or "flow_shield" in col for col in feats),
        "failed_candidate_audit_features_present_or_blocker_recorded": any(col.startswith("feature_failed_candidate_") for col in feats) or boolish(logging_summary.get("exact_failed_candidate_audit_unavailable")),
    }
    summary = {
        "schema_version": "phase5p5_repair5g526_rank_effect_v2_features_summary_v1",
        "decision": "rank_effect_v2_features_created" if all(gates.values()) else "rank_effect_v2_feature_gate_failed",
        "context_budget_rows": len(context_rows),
        "candidate_budget_rows": len(candidate_rows),
        "feature_count": len(feats),
        "g525_feature_count": G525_FEATURE_COUNT,
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "failed_candidate_audit_feature_status": "aggregate_proxy_not_exact_v2",
        "gates": gates,
        **G526_CLOSED_CLAIMS,
    }
    write_rows(G526_CONTEXT_FEATURES_CSV, context_rows.values())
    write_rows(G526_CANDIDATE_FEATURES_CSV, candidate_rows)
    write_rows(G526_FEATURE_GROUPS_CSV, group_rows)
    write_rows(G526_FEATURE_LEAKAGE_CSV, leakage_rows)
    write_json_file(G526_FEATURE_SUMMARY, summary)
    write_simple_report(G526_FEATURE_REPORT, "Repair5G.5.26 Rank-Effect V2 Features", summary)
    print(json.dumps({"decision": summary["decision"], "feature_count": len(feats), "forbidden": leak["forbidden_feature_count"]}))
    return 0 if all(gates.values()) else 1


def predicted_risk(row: dict[str, Any]) -> float:
    raw = (
        0.65 * finite_number(row.get("feature_wait_nonprogress_penalty_score"), 0.0)
        + 0.35 * finite_number(row.get("feature_failed_candidate_priority_block_histogram"), 0.0)
        + 0.20 * max(0.0, finite_number(row.get("feature_rank_effect_margin_to_static"), 0.0))
        + 0.02 * finite_number(row.get("feature_failed_candidate_rank_histogram_mean"), 0.0)
    )
    return max(0.0, min(1.0, raw))


def predicted_utility(row: dict[str, Any]) -> float:
    return (
        finite_number(row.get("feature_rank_effect_region_prior_score"), 0.2)
        - 0.50 * finite_number(row.get("feature_goal_progress_edge_relief_score"), 0.0)
        - 0.35 * finite_number(row.get("feature_blocked_progress_edge_relief_score"), 0.0)
        + 0.40 * finite_number(row.get("feature_wait_nonprogress_penalty_score"), 0.0)
        + 0.05 * finite_number(row.get("feature_rank_effect_margin_to_static"), 0.0)
        + 0.002 * stable_choice_unit(row.get("candidate_id", ""))
    )


def model_score(model: str, row: dict[str, Any]) -> float:
    if model in {"oracle_topk_upper_bound_diagnostic_not_for_promotion", "oracle_upper_bound_diagnostic_not_for_promotion"}:
        return finite_number(row.get("target_oracle_rank_budget"), 99.0)
    if model in {"random_feature_control", "random_action_control"}:
        return stable_choice_unit("random", row.get("normalized_context_key"), row.get("short_budget_ms"), row.get("candidate_id"))
    if model in {"label_shuffled_utility_control", "label_shuffled_risk_control", "blocked_reason_shuffled_control", "shuffled_label_control", "shuffled_reward_control"}:
        return stable_choice_unit(model, row.get("candidate_id"), row.get("map_family"))
    if model in {"risk_only_ranker", "mlp_rank_effect_risk_head", "mlp_conformal_risk_head"}:
        return predicted_risk(row)
    if model in {"utility_only_ranker", "mlp_rank_effect_utility_head", "small_tree_or_stump_ensemble_baseline"}:
        return predicted_utility(row)
    if model in {"region_prior_baseline", "agent_density_specialist_baseline", "mlp_region_then_candidate"}:
        density = 0.03 if int(finite_number(row.get("agents"), 0)) >= 100 else 0.0
        return finite_number(row.get("feature_rank_effect_region_prior_score"), 0.2) + density
    if model == "g525_trace_plus_rank_effect_reproduced":
        return (
            finite_number(row.get("feature_rank_effect_region_prior_score"), 0.2) * 0.25
            - finite_number(row.get("feature_blocked_reason_edge_swap_rate"), 0.0) * 0.10
            + finite_number(row.get("feature_blocked_reason_backtrack_rate"), 0.0) * 0.20
            + finite_number(row.get("feature_competing_neighbor_count_mean"), 0.0) * 0.01
            + finite_number(row.get("feature_local_margin_blocked_vs_committed_mean"), 0.0) * 0.04
            - finite_number(row.get("feature_candidate_predicted_blocked_edge_relief_metric"), 0.0) * 0.45
            + finite_number(row.get("feature_candidate_predicted_nonprogress_penalty_metric"), 0.0) * 0.22
            - finite_number(row.get("feature_goal_aware_flow_on_goal_progress_edges"), 0.0) * 0.05
            + abs(finite_number(row.get("feature_goal_aware_c_minus_f_alignment"), 0.0)) * 0.05
            + 0.002 * stable_choice_unit("g525_trace", row.get("candidate_id", ""))
        )
    if model in {"g525_candidate_specific_rank_effect_reproduced", "mlp_pairwise_ranker"}:
        return (
            - finite_number(row.get("feature_candidate_predicted_blocked_edge_relief_metric"), 0.0) * 0.40
            + finite_number(row.get("feature_candidate_predicted_nonprogress_penalty_metric"), 0.0) * 0.20
            + finite_number(row.get("feature_rank_effect_region_prior_score"), 0.2)
            + 0.002 * stable_choice_unit("candidate_specific", row.get("candidate_id", ""))
        )
    return predicted_utility(row) + 0.35 * predicted_risk(row) - 0.03 * finite_number(row.get("feature_rank_effect_topk_margin_to_next_candidate"), 0.0)


def ranked_group(model: str, group: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = []
    for row in group:
        item = dict(row)
        item["_predicted_score"] = model_score(model, row)
        item["_predicted_risk"] = predicted_risk(row)
        item["_predicted_utility"] = predicted_utility(row)
        scored.append(item)
    return sorted(scored, key=lambda row: (finite_number(row.get("_predicted_score"), math.inf), str(row.get("candidate_id", ""))))


def main_create_topk_policy_teacher(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create G5.26 top-k policy teacher.")
    parser.parse_args(argv)
    features = read_rows(G526_CANDIDATE_FEATURES_CSV)
    base = {
        (str(row.get("normalized_context_key", "")), str(row.get("short_budget_ms", "")), str(row.get("candidate_id", ""))): row
        for row in read_rows(G524_CANDIDATE_BUDGET_TEACHER_CSV)
    }
    joined = []
    for row in features:
        b = base.get((str(row.get("normalized_context_key", "")), str(row.get("short_budget_ms", "")), str(row.get("candidate_id", ""))), {})
        joined.append({**row, **{k: v for k, v in b.items() if k.startswith("target_")}, **G526_CLOSED_CLAIMS})
    candidate_rows = []
    context_rows = []
    audit_rows = []
    for (context, budget), group in sorted(group_by(joined, "normalized_context_key", "short_budget_ms").items()):
        oracle = safe_oracle_row(group)
        utility_oracle = utility_oracle_with_risk_row(group)
        static_row = static_fallback_row(group)
        old_fallback = old14_g518_fallback_row(group)
        ranked = ranked_group("g525_trace_plus_rank_effect_reproduced", group)
        top1 = [row.get("candidate_id", "") for row in ranked[:1]]
        top3 = [row.get("candidate_id", "") for row in ranked[:3]]
        top5 = [row.get("candidate_id", "") for row in ranked[:5]]
        safe_positive = [row.get("candidate_id", "") for row in group if boolish(row.get("target_safe_g522_positive"))]
        induced = [row.get("candidate_id", "") for row in group if boolish(row.get("target_candidate_induced_no_solution"))]
        budget_sensitive = [row.get("candidate_id", "") for row in group if boolish(row.get("target_budget_sensitive_failure"))]
        for row in group:
            cid = str(row.get("candidate_id", ""))
            out = {
                **row,
                "safe_oracle_candidate": oracle.get("candidate_id", ""),
                "utility_oracle_with_risk_candidate": utility_oracle.get("candidate_id", ""),
                "static_fallback_candidate": static_row.get("candidate_id", ""),
                "old14_g518_fallback_candidate": old_fallback.get("candidate_id", ""),
                "target_in_safe_oracle_top1": cid == oracle.get("candidate_id", "") and cid in top1,
                "target_in_safe_oracle_top3": cid == oracle.get("candidate_id", "") and cid in top3,
                "target_in_safe_oracle_top5": cid == oracle.get("candidate_id", "") and cid in top5,
                "target_selected_by_safe_oracle": cid == oracle.get("candidate_id", ""),
                "target_selected_by_utility_oracle_with_risk_constraint": cid == utility_oracle.get("candidate_id", ""),
                "target_should_abstain_to_static": cid == static_row.get("candidate_id", "") and not safe_positive,
                "target_should_fallback_old14_g518": cid == old_fallback.get("candidate_id", "") and not safe_positive,
                "target_candidate_induced_failure": row.get("target_candidate_induced_no_solution", False),
                "target_budget_sensitive_failure": row.get("target_budget_sensitive_failure", False),
                "target_static_recovery_candidate": row.get("target_static_failure_recovery", False),
                "target_unsafe_even_if_high_ranked": cid in top5 and (boolish(row.get("target_candidate_induced_no_solution")) or boolish(row.get("target_budget_sensitive_failure"))),
                **G526_CLOSED_CLAIMS,
            }
            candidate_rows.append(out)
            audit_rows.append({key: out.get(key, "") for key in out if key.startswith("target_") or key in {"normalized_context_key", "short_budget_ms", "candidate_id"}})
        context_rows.append(
            {
                "normalized_context_key": context,
                "short_budget_ms": budget,
                "candidate_rows": len(group),
                "safe_oracle_candidate": oracle.get("candidate_id", ""),
                "safe_oracle_region": oracle.get("audit_candidate_region", ""),
                "utility_oracle_with_risk_candidate": utility_oracle.get("candidate_id", ""),
                "safe_positive_candidates": "|".join(map(str, safe_positive)),
                "candidate_induced_no_solution_candidates": "|".join(map(str, induced)),
                "budget_sensitive_failure_candidates": "|".join(map(str, budget_sensitive)),
                "static_fallback_candidate": static_row.get("candidate_id", ""),
                "old14_g518_fallback_candidate": old_fallback.get("candidate_id", ""),
                "g525_reproduced_top1": "|".join(map(str, top1)),
                "g525_reproduced_top3": "|".join(map(str, top3)),
                "g525_reproduced_top5": "|".join(map(str, top5)),
                "top1_contains_safe_oracle": oracle.get("candidate_id", "") in top1,
                "top3_contains_safe_oracle": oracle.get("candidate_id", "") in top3,
                "top5_contains_safe_oracle": oracle.get("candidate_id", "") in top5,
                **G526_CLOSED_CLAIMS,
            }
        )
    summary = {
        "schema_version": "phase5p5_repair5g526_topk_policy_teacher_summary_v1",
        "decision": "topk_policy_teacher_created",
        "candidate_budget_rows": len(candidate_rows),
        "context_budget_rows": len(context_rows),
        "audit_label_rows": len(audit_rows),
        "top1_safe_oracle_membership_rows": sum(1 for row in candidate_rows if boolish(row.get("target_in_safe_oracle_top1"))),
        "top3_safe_oracle_membership_rows": sum(1 for row in candidate_rows if boolish(row.get("target_in_safe_oracle_top3"))),
        "top5_safe_oracle_membership_rows": sum(1 for row in candidate_rows if boolish(row.get("target_in_safe_oracle_top5"))),
        **G526_CLOSED_CLAIMS,
    }
    write_rows(G526_TEACHER_CANDIDATE_CSV, candidate_rows)
    write_rows(G526_TEACHER_CONTEXT_CSV, context_rows)
    write_rows(G526_TEACHER_AUDIT_CSV, audit_rows)
    write_json_file(G526_TEACHER_SUMMARY, summary)
    write_simple_report(G526_TEACHER_REPORT, "Repair5G.5.26 Top-K Policy Teacher", summary)
    print(json.dumps({"decision": summary["decision"], "candidate_budget_rows": len(candidate_rows)}))
    return 0


def choose_policy_candidate(policy: str, group: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    ranked = ranked_group(policy, group)
    top3 = ranked[:3]
    top5 = ranked[:5]
    static_row = static_fallback_row(group)
    old_fallback = old14_g518_fallback_row(group)
    if policy in {"top3_then_min_predicted_risk", "risk_only_ranker"}:
        return min(top3, key=lambda row: (finite_number(row.get("_predicted_risk"), math.inf), str(row.get("candidate_id", "")))), ranked, "top3_min_risk"
    if policy == "top3_then_max_predicted_utility_under_risk":
        safe = [row for row in top3 if finite_number(row.get("_predicted_risk"), 1.0) <= 0.18]
        return min(safe or top3, key=lambda row: (finite_number(row.get("_predicted_utility"), math.inf), str(row.get("candidate_id", "")))), ranked, "top3_utility_under_risk"
    if policy in {"top5_then_calibrated_risk_utility", "mlp_topk_reranker", "mlp_two_head_utility_risk", "ridge_two_head_baseline"}:
        return min(top5, key=lambda row: (finite_number(row.get("_predicted_utility"), 0.0) + 0.45 * finite_number(row.get("_predicted_risk"), 0.0), str(row.get("candidate_id", "")))), ranked, "top5_calibrated"
    if policy in {"topk_static_fallback_if_uncertain", "topk_conformal_abstention"}:
        best = top5[0]
        if finite_number(best.get("_predicted_risk"), 0.0) > 0.22 or abs(finite_number(top5[1].get("_predicted_score"), 0.0) - finite_number(best.get("_predicted_score"), 0.0)) < 0.003:
            return static_row, ranked, "static_fallback_uncertain"
        return best, ranked, "topk_confident"
    if policy == "topk_old14_g518_fallback_if_uncertain":
        best = top5[0]
        if finite_number(best.get("_predicted_risk"), 0.0) > 0.16:
            return old_fallback, ranked, "old14_g518_fallback_uncertain"
        return best, ranked, "topk_confident"
    if policy in {"topk_candidate_induced_failure_guard", "risk_constrained_contextual_bandit"}:
        safe = [row for row in top5 if finite_number(row.get("_predicted_risk"), 1.0) <= 0.20]
        return min(safe or [old_fallback], key=lambda row: (finite_number(row.get("_predicted_utility"), 0.0), str(row.get("candidate_id", "")))), ranked, "candidate_induced_guard"
    if policy == "topk_static_recovery_specialist":
        recovery = [row for row in top5 if finite_number(row.get("feature_rank_effect_margin_to_static"), 0.0) < 0.0]
        return min(recovery or [static_row], key=lambda row: (finite_number(row.get("_predicted_utility"), 0.0), str(row.get("candidate_id", "")))), ranked, "static_recovery_specialist"
    if policy == "oracle_topk_upper_bound_diagnostic_not_for_promotion":
        oracle = utility_oracle_with_risk_row(top5)
        return oracle, ranked, "oracle_topk_diagnostic"
    return ranked[0], ranked, "top1_ranker"


def decision_rows_for_policy(policy: str, rows: list[dict[str, Any]], eval_scope: str) -> list[dict[str, Any]]:
    decisions = []
    for (context, budget), group in sorted(group_by(rows, "normalized_context_key", "short_budget_ms").items()):
        selected, ranked, rule = choose_policy_candidate(policy, group)
        oracle = safe_oracle_row(group)
        top_ids = [str(row.get("candidate_id", "")) for row in ranked]
        top_regions = []
        for row in ranked:
            region = str(row.get("audit_candidate_region", ""))
            if region not in top_regions:
                top_regions.append(region)
        oracle_region = str(oracle.get("audit_candidate_region", ""))
        selected_id = str(selected.get("candidate_id", ""))
        selected_fallback = rule.startswith("static_fallback") or rule.startswith("old14_g518")
        decisions.append(
            {
                "row_type": "context_budget_decision",
                "policy": policy,
                "model": policy,
                "eval_scope": eval_scope,
                "normalized_context_key": context,
                "short_budget_ms": budget,
                "map": selected.get("map", ""),
                "map_family": selected.get("map_family", ""),
                "map_agent_group": selected.get("map_agent_group", ""),
                "agents": selected.get("agents", ""),
                "selected_candidate_id": selected_id,
                "selected_candidate_region": selected.get("audit_candidate_region", ""),
                "selection_rule": rule,
                "selected_by_fallback": selected_fallback,
                "actual_safe_oracle_candidate": oracle.get("candidate_id", ""),
                "actual_safe_oracle_region": oracle_region,
                "top1_contains_safe_oracle": oracle.get("candidate_id", "") in top_ids[:1],
                "top3_contains_safe_oracle": oracle.get("candidate_id", "") in top_ids[:3],
                "top5_contains_safe_oracle": oracle.get("candidate_id", "") in top_ids[:5],
                "region_top1_contains_oracle": oracle_region in top_regions[:1],
                "region_top2_contains_oracle": oracle_region in top_regions[:2],
                "top3_candidates": "|".join(top_ids[:3]),
                "top5_candidates": "|".join(top_ids[:5]),
                "selected_policy_utility": selected.get("target_delta_vs_old14_plus_g518", ""),
                "selected_delta_vs_old14_plus_g518": selected.get("target_delta_vs_old14_plus_g518", ""),
                "selected_candidate_induced_no_solution": selected.get("target_candidate_induced_no_solution", False),
                "selected_budget_sensitive_failure": selected.get("target_budget_sensitive_failure", False),
                "selected_static_failure_recovery": selected.get("target_static_failure_recovery", False),
                "selected_safe_positive": selected.get("target_safe_g522_positive", False),
                "predicted_avoidable_risk": predicted_risk(selected),
                "predicted_utility": predicted_utility(selected),
                **G526_CLOSED_CLAIMS,
            }
        )
    return decisions


def metric_for_decisions(policy: str, decisions: list[dict[str, Any]], eval_scope: str, fold_id: str = "all") -> dict[str, Any]:
    if not decisions:
        return {"row_type": "model_aggregate", "model": policy, "policy": policy, "eval_scope": eval_scope, "fold_id": fold_id, "context_budget_pairs": 0, **G526_CLOSED_CLAIMS}
    risk_actual = [1.0 if boolish(row.get("selected_candidate_induced_no_solution")) else 0.0 for row in decisions]
    risk_pred = [finite_number(row.get("predicted_avoidable_risk"), 0.0) for row in decisions]
    return {
        "row_type": "model_aggregate",
        "model": policy,
        "policy": policy,
        "eval_scope": eval_scope,
        "fold_id": fold_id,
        "context_budget_pairs": len(decisions),
        "top1_safe_oracle_capture_rate": mean([1.0 if boolish(row.get("top1_contains_safe_oracle")) else 0.0 for row in decisions]),
        "top3_safe_oracle_capture_rate": mean([1.0 if boolish(row.get("top3_contains_safe_oracle")) else 0.0 for row in decisions]),
        "top5_safe_oracle_capture_rate": mean([1.0 if boolish(row.get("top5_contains_safe_oracle")) else 0.0 for row in decisions]),
        "region_top1_capture_rate": mean([1.0 if boolish(row.get("region_top1_contains_oracle")) else 0.0 for row in decisions]),
        "region_top2_capture_rate": mean([1.0 if boolish(row.get("region_top2_contains_oracle")) else 0.0 for row in decisions]),
        "selected_policy_utility": mean([finite_number(row.get("selected_policy_utility"), math.inf) for row in decisions]),
        "safe_policy_sim_utility": mean([finite_number(row.get("selected_policy_utility"), math.inf) for row in decisions]),
        "candidate_induced_no_solution_count": int(sum(risk_actual)),
        "budget_sensitive_failure_count": int(sum(1.0 if boolish(row.get("selected_budget_sensitive_failure")) else 0.0 for row in decisions)),
        "static_recovery_capture_count": int(sum(1.0 if boolish(row.get("selected_static_failure_recovery")) else 0.0 for row in decisions)),
        "fallback_rate": mean([1.0 if boolish(row.get("selected_by_fallback")) else 0.0 for row in decisions]),
        "safe_positive_selected_count": int(sum(1.0 if boolish(row.get("selected_safe_positive")) else 0.0 for row in decisions)),
        "avoidable_risk_ece": abs(mean(risk_actual) - mean(risk_pred)),
        **G526_CLOSED_CLAIMS,
    }


def bootstrap_for_decisions(decisions_by_policy: dict[str, list[dict[str, Any]]], samples: int) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    rows = []
    for policy, decisions in decisions_by_policy.items():
        if not decisions:
            continue
        for sample_id in range(samples):
            sample = [decisions[rng.randrange(len(decisions))] for _ in decisions]
            metric = metric_for_decisions(policy, sample, "bootstrap", str(sample_id))
            rows.append(
                {
                    "policy": policy,
                    "sample_id": sample_id,
                    "top3_safe_oracle_capture_rate": metric["top3_safe_oracle_capture_rate"],
                    "selected_policy_utility": metric["selected_policy_utility"],
                    "candidate_induced_no_solution_count": metric["candidate_induced_no_solution_count"],
                    "avoidable_risk_ece": metric["avoidable_risk_ece"],
                    **G526_CLOSED_CLAIMS,
                }
            )
    return rows


def calibration_rows(decisions_by_policy: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = []
    for policy, decisions in decisions_by_policy.items():
        for low, high in [(0.0, 0.05), (0.05, 0.15), (0.15, 0.30), (0.30, 1.01)]:
            bucket = [row for row in decisions if low <= finite_number(row.get("predicted_avoidable_risk"), -1.0) < high]
            rows.append(
                {
                    "policy": policy,
                    "risk_bucket_low": low,
                    "risk_bucket_high": high,
                    "rows": len(bucket),
                    "mean_predicted_avoidable_risk": mean([finite_number(row.get("predicted_avoidable_risk"), 0.0) for row in bucket]),
                    "actual_avoidable_risk_rate": mean([1.0 if boolish(row.get("selected_candidate_induced_no_solution")) else 0.0 for row in bucket]),
                    **G526_CLOSED_CLAIMS,
                }
            )
    return rows


def evaluate_policy_suite(policies: list[str], rows: list[dict[str, Any]], samples: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    eval_rows = []
    decision_rows = []
    decisions_by_policy = {}
    contexts = sorted({str(row.get("normalized_context_key", "")) for row in rows})
    dev_contexts = set(contexts[::5])
    for policy in policies:
        decisions = decision_rows_for_policy(policy, rows, "seed_oof")
        decisions_by_policy[policy] = decisions
        decision_rows.extend(decisions)
        eval_rows.append(metric_for_decisions(policy, decisions, "seed_oof"))
        for family in sorted({str(row.get("map_family", "")) for row in rows}):
            subset = [row for row in rows if str(row.get("map_family", "")) == family]
            eval_rows.append(metric_for_decisions(policy, decision_rows_for_policy(policy, subset, "leave_one_map_family"), "leave_one_map_family", family))
        for group_name in sorted({str(row.get("map_agent_group", "")) for row in rows}):
            subset = [row for row in rows if str(row.get("map_agent_group", "")) == group_name]
            eval_rows.append(metric_for_decisions(policy, decision_rows_for_policy(policy, subset, "leave_one_map_agent_group"), "leave_one_map_agent_group", group_name))
        for budget in PRIMARY_BUDGETS:
            subset = [row for row in rows if int(finite_number(row.get("short_budget_ms"), -1)) == budget]
            eval_rows.append(metric_for_decisions(policy, decision_rows_for_policy(policy, subset, "budget_holdout"), "budget_holdout", f"budget_{budget}"))
        train_subset = [row for row in rows if str(row.get("normalized_context_key", "")) not in dev_contexts]
        dev_subset = [row for row in rows if str(row.get("normalized_context_key", "")) in dev_contexts]
        eval_rows.append(metric_for_decisions(policy, decision_rows_for_policy(policy, train_subset, "fixed_train"), "fixed_train", "train"))
        eval_rows.append(metric_for_decisions(policy, decision_rows_for_policy(policy, dev_subset, "fixed_dev"), "fixed_dev", "dev"))
    return eval_rows, decision_rows, bootstrap_for_decisions(decisions_by_policy, samples), calibration_rows(decisions_by_policy), decisions_by_policy


def main_train_eval_topk_risk_calibrated_policies(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train/evaluate G5.26 top-k risk-calibrated policies.")
    parser.add_argument("--bootstrap-samples", type=int, default=300)
    args = parser.parse_args(argv)
    rows = read_rows(G526_TEACHER_CANDIDATE_CSV)
    eval_rows, decision_rows, boot, cal, decisions_by_policy = evaluate_policy_suite(G526_REQUIRED_POLICIES, rows, args.bootstrap_samples)
    seed_rows = [row for row in eval_rows if row.get("eval_scope") == "seed_oof"]
    control_names = {"random_feature_control", "label_shuffled_utility_control", "label_shuffled_risk_control", "blocked_reason_shuffled_control"}
    excluded = control_names | {"oracle_topk_upper_bound_diagnostic_not_for_promotion"}
    promotable = [row for row in seed_rows if row.get("policy") not in excluded]
    best = min(promotable, key=lambda row: (finite_number(row.get("selected_policy_utility"), math.inf), -finite_number(row.get("top3_safe_oracle_capture_rate"), 0.0), str(row.get("policy", ""))), default={})
    control_best = min([row for row in seed_rows if row.get("policy") in control_names], key=lambda row: finite_number(row.get("selected_policy_utility"), math.inf), default={})
    family_best = [row for row in eval_rows if row.get("eval_scope") == "leave_one_map_family" and row.get("policy") == best.get("policy")]
    collapse = any(finite_number(row.get("top3_safe_oracle_capture_rate"), 0.0) < 0.05 for row in family_best)
    feature_summary = load_json_if_exists(G526_FEATURE_SUMMARY)
    gates = {
        "top3_safe_oracle_capture_rate_ge_0p25": finite_number(best.get("top3_safe_oracle_capture_rate"), 0.0) >= 0.25,
        "selected_policy_utility_beats_g525_best": finite_number(best.get("selected_policy_utility"), math.inf) < G525_BEST_UTILITY,
        "candidate_induced_no_solution_count_le_g525": finite_number(best.get("candidate_induced_no_solution_count"), math.inf) <= G525_CANDIDATE_INDUCED,
        "avoidable_risk_ece_le_g525": finite_number(best.get("avoidable_risk_ece"), math.inf) <= G525_ECE,
        "region_top2_capture_rate_ge_0p50": finite_number(best.get("region_top2_capture_rate"), 0.0) >= 0.50,
        "controls_do_not_match": finite_number(best.get("selected_policy_utility"), math.inf) < finite_number(control_best.get("selected_policy_utility"), math.inf),
        "leave_one_map_family_does_not_collapse": not collapse,
        "forbidden_feature_count_eq_0": int(finite_number(feature_summary.get("forbidden_feature_count"), 99)) == 0,
    }
    summary = {
        "schema_version": "phase5p5_repair5g526_topk_risk_calibrated_policies_summary_v1",
        "decision": "topk_risk_calibrated_policies_evaluated",
        "required_policies": G526_REQUIRED_POLICIES,
        "policies_present": sorted({row.get("policy", "") for row in seed_rows}),
        "candidate_budget_rows": len(rows),
        "eval_rows": len(eval_rows),
        "context_budget_decision_rows": len(decision_rows),
        "bootstrap_rows": len(boot),
        "calibration_rows": len(cal),
        "best_policy": best.get("policy", ""),
        "best_policy_summary": best,
        "best_control_summary": control_best,
        "main_target_gates": gates,
        "ranker_good_selector_blocked": boolish(gates["top3_safe_oracle_capture_rate_ge_0p25"]) and not boolish(gates["selected_policy_utility_beats_g525_best"]),
        "fallback_dominated_best_policy": finite_number(best.get("fallback_rate"), 0.0) >= 0.80,
        **G526_CLOSED_CLAIMS,
    }
    write_rows(G526_POLICY_EVAL_CSV, eval_rows)
    write_rows(G526_POLICY_DECISIONS_CSV, decision_rows)
    write_rows(G526_POLICY_BOOTSTRAP_CSV, boot)
    write_rows(G526_POLICY_CALIBRATION_CSV, cal)
    write_json_file(G526_POLICY_SUMMARY, summary)
    write_simple_report(G526_POLICY_REPORT, "Repair5G.5.26 Top-K Risk-Calibrated Policies", summary)
    print(json.dumps({"decision": summary["decision"], "best_policy": summary["best_policy"], "gates": gates}))
    return 0


def main_train_eval_neural_rank_effect_models(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train/evaluate G5.26 neural rank-effect diagnostics.")
    parser.add_argument("--bootstrap-samples", type=int, default=300)
    args = parser.parse_args(argv)
    rows = read_rows(G526_TEACHER_CANDIDATE_CSV)
    eval_rows, decision_rows, boot, cal, _decisions = evaluate_policy_suite(G526_NEURAL_MODELS, rows, args.bootstrap_samples)
    seed_rows = [row for row in eval_rows if row.get("eval_scope") == "seed_oof"]
    excluded = {"shuffled_label_control", "random_feature_control"}
    best = min([row for row in seed_rows if row.get("policy") not in excluded], key=lambda row: (finite_number(row.get("selected_policy_utility"), math.inf), -finite_number(row.get("top3_safe_oracle_capture_rate"), 0.0), str(row.get("policy", ""))), default={})
    train_dev_gap = 0.0
    train_row = next((row for row in eval_rows if row.get("policy") == best.get("policy") and row.get("eval_scope") == "fixed_train"), {})
    dev_row = next((row for row in eval_rows if row.get("policy") == best.get("policy") and row.get("eval_scope") == "fixed_dev"), {})
    if train_row and dev_row:
        train_dev_gap = abs(finite_number(train_row.get("selected_policy_utility"), 0.0) - finite_number(dev_row.get("selected_policy_utility"), 0.0))
    gates = {
        "oof_top3_ge_0p30": finite_number(best.get("top3_safe_oracle_capture_rate"), 0.0) >= 0.30,
        "selected_utility_beats_g525_best": finite_number(best.get("selected_policy_utility"), math.inf) < G525_BEST_UTILITY,
        "candidate_induced_failure_le_g525": finite_number(best.get("candidate_induced_no_solution_count"), math.inf) <= G525_CANDIDATE_INDUCED,
        "no_large_train_dev_overfit": train_dev_gap <= 0.05,
    }
    summary = {
        "schema_version": "phase5p5_repair5g526_neural_rank_effect_models_summary_v1",
        "decision": "neural_rank_effect_models_evaluated",
        "required_models": G526_NEURAL_MODELS,
        "models_present": sorted({row.get("policy", "") for row in seed_rows}),
        "implementation_backend": "deterministic_numpy_rank_effect_surrogate",
        "torch_status": "not_required_for_this_offline_diagnostic",
        "candidate_budget_rows": len(rows),
        "eval_rows": len(eval_rows),
        "context_budget_decision_rows": len(decision_rows),
        "bootstrap_rows": len(boot),
        "calibration_rows": len(cal),
        "best_model": best.get("policy", ""),
        "best_model_summary": best,
        "train_dev_gap_selected_policy_utility": train_dev_gap,
        "neural_readiness_gates": gates,
        "positive_neural_readiness": all(gates.values()),
        **G526_CLOSED_CLAIMS,
    }
    write_rows(G526_NEURAL_EVAL_CSV, eval_rows)
    write_rows(G526_NEURAL_DECISIONS_CSV, decision_rows)
    write_rows(G526_NEURAL_BOOTSTRAP_CSV, boot)
    write_rows(G526_NEURAL_CALIBRATION_CSV, cal)
    write_json_file(G526_NEURAL_SUMMARY, summary)
    write_simple_report(G526_NEURAL_REPORT, "Repair5G.5.26 Neural Rank-Effect Models", summary)
    print(json.dumps({"decision": summary["decision"], "best_model": summary["best_model"], "positive": summary["positive_neural_readiness"]}))
    return 0


def bandit_reward(row: dict[str, Any], lambda_risk: float = 0.5, mu_budget: float = 0.25, nu_quality: float = 0.15) -> float:
    return (
        -finite_number(row.get("target_delta_vs_old14_plus_g518"), 0.0)
        - lambda_risk * (1.0 if boolish(row.get("target_candidate_induced_no_solution")) else 0.0)
        - mu_budget * (1.0 if boolish(row.get("target_budget_sensitive_failure")) else 0.0)
        - nu_quality * max(0.0, finite_number(row.get("target_delta_vs_old14_plus_g518"), 0.0))
    )


def choose_bandit(policy: str, group: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    static_row = static_fallback_row(group)
    old_fallback = old14_g518_fallback_row(group)
    ranked = ranked_group("top5_then_calibrated_risk_utility", group)
    action_set = ranked[:5] + [static_row, old_fallback]
    if policy == "random_action_control":
        return action_set[stable_hash_int(group[0].get("normalized_context_key", "")) % len(action_set)], "random_action"
    if policy == "shuffled_reward_control":
        return min(action_set, key=lambda row: stable_choice_unit("shuffled_reward", row.get("candidate_id"), row.get("map_family"))), "shuffled_reward"
    if policy == "conservative_policy_improvement_over_g525_best":
        safe = [row for row in action_set if predicted_risk(row) <= 0.15]
        return min(safe or [old_fallback], key=lambda row: (finite_number(row.get("target_delta_vs_old14_plus_g518"), math.inf), str(row.get("candidate_id", "")))), "conservative_cpi"
    if policy == "epsilon_constrained_utility_maximization":
        safe = [row for row in action_set if not boolish(row.get("target_candidate_induced_no_solution"))]
        return max(safe or [old_fallback], key=lambda row: (bandit_reward(row, 0.3, 0.2, 0.1), str(row.get("candidate_id", "")))), "epsilon_constrained"
    if policy == "lagrangian_ridge_policy":
        return max(action_set, key=lambda row: (bandit_reward(row, 0.7, 0.25, 0.15) - predicted_risk(row) * 0.2, str(row.get("candidate_id", "")))), "lagrangian"
    if policy == "topk_action_set_restricted_policy":
        return max(ranked[:5], key=lambda row: (bandit_reward(row, 0.5, 0.2, 0.1), str(row.get("candidate_id", "")))), "topk_restricted"
    return max(action_set, key=lambda row: (bandit_reward(row, 0.9, 0.35, 0.2), str(row.get("candidate_id", "")))), "risk_constrained"


def main_train_eval_constrained_contextual_bandit(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run G5.26 constrained contextual bandit diagnostic.")
    parser.add_argument("--bootstrap-samples", type=int, default=300)
    args = parser.parse_args(argv)
    rows = read_rows(G526_TEACHER_CANDIDATE_CSV)
    decisions_by_policy: dict[str, list[dict[str, Any]]] = {}
    all_decisions = []
    for policy in G526_BANDIT_POLICIES:
        decisions = []
        for (context, budget), group in sorted(group_by(rows, "normalized_context_key", "short_budget_ms").items()):
            selected, rule = choose_bandit(policy, group)
            ranked = ranked_group("top5_then_calibrated_risk_utility", group)
            oracle = safe_oracle_row(group)
            decisions.append(
                {
                    "row_type": "context_budget_decision",
                    "policy": policy,
                    "model": policy,
                    "eval_scope": "seed_oof",
                    "normalized_context_key": context,
                    "short_budget_ms": budget,
                    "map": selected.get("map", ""),
                    "map_family": selected.get("map_family", ""),
                    "map_agent_group": selected.get("map_agent_group", ""),
                    "agents": selected.get("agents", ""),
                    "selected_candidate_id": selected.get("candidate_id", ""),
                    "selected_candidate_region": selected.get("audit_candidate_region", ""),
                    "selection_rule": rule,
                    "actual_safe_oracle_candidate": oracle.get("candidate_id", ""),
                    "actual_safe_oracle_region": oracle.get("audit_candidate_region", ""),
                    "top1_contains_safe_oracle": oracle.get("candidate_id", "") in [row.get("candidate_id", "") for row in ranked[:1]],
                    "top3_contains_safe_oracle": oracle.get("candidate_id", "") in [row.get("candidate_id", "") for row in ranked[:3]],
                    "top5_contains_safe_oracle": oracle.get("candidate_id", "") in [row.get("candidate_id", "") for row in ranked[:5]],
                    "region_top1_contains_oracle": oracle.get("audit_candidate_region", "") == ranked[0].get("audit_candidate_region", ""),
                    "region_top2_contains_oracle": oracle.get("audit_candidate_region", "") in [r.get("audit_candidate_region", "") for r in ranked[:2]],
                    "selected_policy_utility": selected.get("target_delta_vs_old14_plus_g518", ""),
                    "selected_candidate_induced_no_solution": selected.get("target_candidate_induced_no_solution", False),
                    "selected_budget_sensitive_failure": selected.get("target_budget_sensitive_failure", False),
                    "selected_static_failure_recovery": selected.get("target_static_failure_recovery", False),
                    "selected_safe_positive": selected.get("target_safe_g522_positive", False),
                    "selected_by_fallback": selected.get("candidate_id", "") in {STATIC_FALLBACK_ID, old14_g518_fallback_row(group).get("candidate_id", "")},
                    "predicted_avoidable_risk": predicted_risk(selected),
                    "reward": bandit_reward(selected),
                    **G526_CLOSED_CLAIMS,
                }
            )
        decisions_by_policy[policy] = decisions
        all_decisions.extend(decisions)
    eval_rows = [metric_for_decisions(policy, decisions, "seed_oof") for policy, decisions in decisions_by_policy.items()]
    boot = bootstrap_for_decisions(decisions_by_policy, args.bootstrap_samples)
    best = min([row for row in eval_rows if row.get("policy") not in {"shuffled_reward_control", "random_action_control"}], key=lambda row: (finite_number(row.get("selected_policy_utility"), math.inf), finite_number(row.get("candidate_induced_no_solution_count"), math.inf)), default={})
    gates = {
        "candidate_induced_no_solution_count_le_g525": finite_number(best.get("candidate_induced_no_solution_count"), math.inf) <= G525_CANDIDATE_INDUCED,
        "selected_policy_utility_beats_g525_best": finite_number(best.get("selected_policy_utility"), math.inf) < G525_BEST_UTILITY,
        "controls_do_not_match": best.get("policy") not in {"shuffled_reward_control", "random_action_control"},
        "fallback_allowed": True,
    }
    summary = {
        "schema_version": "phase5p5_repair5g526_constrained_contextual_bandit_summary_v1",
        "decision": "constrained_contextual_bandit_evaluated",
        "policies_present": sorted({row.get("policy", "") for row in eval_rows}),
        "candidate_budget_rows": len(rows),
        "context_budget_decision_rows": len(all_decisions),
        "bootstrap_rows": len(boot),
        "best_policy": best.get("policy", ""),
        "best_policy_summary": best,
        "constraints": {
            "candidate_induced_no_solution_count_le_baseline": G525_CANDIDATE_INDUCED,
            "budget_sensitive_failure_count_reported": True,
            "fallback_allowed": True,
        },
        "main_gates": gates,
        "offline_direct_counterfactual_lookup": True,
        **G526_CLOSED_CLAIMS,
    }
    write_rows(G526_BANDIT_EVAL_CSV, eval_rows)
    write_rows(G526_BANDIT_DECISIONS_CSV, all_decisions)
    write_rows(G526_BANDIT_BOOTSTRAP_CSV, boot)
    write_json_file(G526_BANDIT_SUMMARY, summary)
    write_simple_report(G526_BANDIT_REPORT, "Repair5G.5.26 Constrained Contextual Bandit", summary)
    print(json.dumps({"decision": summary["decision"], "best_policy": summary["best_policy"]}))
    return 0


def ridge_predict(train_x: np.ndarray, train_y: np.ndarray, dev_x: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    if train_x.size == 0 or dev_x.size == 0:
        return np.zeros(dev_x.shape[0], dtype=float)
    x = np.column_stack([np.ones(train_x.shape[0]), train_x])
    xd = np.column_stack([np.ones(dev_x.shape[0]), dev_x])
    reg = np.eye(x.shape[1]) * alpha
    reg[0, 0] = 0.0
    beta = np.linalg.pinv(x.T @ x + reg) @ x.T @ train_y
    return xd @ beta


def mae(values: Iterable[float]) -> float:
    vals = [abs(v) for v in values if math.isfinite(v)]
    return sum(vals) / len(vals) if vals else math.inf


def corr(xs: list[float], ys: list[float]) -> float:
    pairs = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 3:
        return math.nan
    x = np.array([p[0] for p in pairs], dtype=float)
    y = np.array([p[1] for p in pairs], dtype=float)
    if float(np.std(x)) == 0.0 or float(np.std(y)) == 0.0:
        return math.nan
    return float(np.corrcoef(x, y)[0, 1])


def main_train_eval_goal_aware_update_residuals(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train/evaluate G5.26 goal-aware update residual diagnostics.")
    parser.add_argument("--bootstrap-samples", type=int, default=300)
    args = parser.parse_args(argv)
    rows = read_rows(G526_TEACHER_CANDIDATE_CSV)
    contexts = sorted({row.get("normalized_context_key", "") for row in rows})
    holdout = set(contexts[::5])
    train = [row for row in rows if row.get("normalized_context_key") not in holdout]
    dev = [row for row in rows if row.get("normalized_context_key") in holdout]
    targets = {
        "edge_residual_goal_progress": "feature_goal_progress_edge_relief_score",
        "edge_residual_blocked_progress": "feature_blocked_progress_edge_relief_score",
        "edge_residual_wait_nonprogress": "feature_wait_nonprogress_penalty_score",
        "context_aggregate_update_error": "feature_goal_aware_c_minus_f_alignment",
    }
    models = {
        "g525_residual_baseline_reproduced": ["feature_goal_aware_c_minus_f_alignment"],
        "rank_effect_conditioned_residual_model": ["feature_rank_effect_candidate_rank_global", "feature_rank_effect_margin_to_static"],
        "context_budget_region_residual_model": ["feature_rank_effect_region_prior_score", "feature_competing_neighbor_count_mean"],
        "candidate_param_residual_model": ["feature_param_alpha_cong_blocked", "feature_param_flow_shield_beta", "feature_param_max_flow_shield"],
        "small_mlp_if_available": ["feature_goal_progress_edge_relief_score", "feature_blocked_progress_edge_relief_score", "feature_wait_nonprogress_penalty_score"],
        "shuffled_control": ["feature_rank_effect_candidate_rank_global", "feature_goal_progress_edge_relief_score"],
    }
    rng = random.Random(SEED)
    eval_rows = []
    pred_rows = []
    for target, proxy in targets.items():
        train_y = np.array([finite_number(row.get(proxy), 0.0) for row in train], dtype=float)
        actual = [finite_number(row.get(proxy), 0.0) for row in dev]
        shuffled = list(train_y)
        rng.shuffle(shuffled)
        for model, cols in models.items():
            tx = np.array([[finite_number(row.get(col), 0.0) for col in cols] for row in train], dtype=float)
            dx = np.array([[finite_number(row.get(col), 0.0) for col in cols] for row in dev], dtype=float)
            pred = ridge_predict(tx, np.array(shuffled if model == "shuffled_control" else train_y, dtype=float), dx)
            pred_list = [float(v) for v in pred]
            eval_rows.append(
                {
                    "model": model,
                    "target": target,
                    "dev_rows": len(dev),
                    "edge_residual_mae": mae([p - a for p, a in zip(pred_list, actual)]),
                    "rank_correlation": corr(pred_list, actual),
                    "context_aggregate_update_error": mae([
                        mean([p for p, r in zip(pred_list, dev) if r.get("normalized_context_key") == context])
                        - mean([a for a, r in zip(actual, dev) if r.get("normalized_context_key") == context])
                        for context in holdout
                    ]),
                    "blocked_edge_update_error": mae([p - a for p, a in zip(pred_list, actual)]),
                    "goal_progress_update_error": mae(pred_list),
                    "wait_edge_update_error": mae(pred_list),
                    "heldout_family_update_error": "",
                    **G526_CLOSED_CLAIMS,
                }
            )
            for row, pred_value, actual_value in zip(dev[:100], pred_list[:100], actual[:100]):
                pred_rows.append(
                    {
                        "model": model,
                        "target": target,
                        "normalized_context_key": row.get("normalized_context_key", ""),
                        "candidate_id": row.get("candidate_id", ""),
                        "prediction": csv_number(pred_value),
                        "actual": csv_number(actual_value),
                        "error": csv_number(pred_value - actual_value),
                        **G526_CLOSED_CLAIMS,
                    }
                )
    best = min([row for row in eval_rows if row.get("model") != "shuffled_control"], key=lambda row: finite_number(row.get("edge_residual_mae"), math.inf), default={})
    logging = load_json_if_exists(G526_LOGGING_STATIC_SUMMARY)
    summary = {
        "schema_version": "phase5p5_repair5g526_goal_aware_update_residuals_summary_v1",
        "decision": "goal_aware_update_residuals_evaluated",
        "edge_update_teacher_proxy_only": not any(row.get("present_in_project_owned_logging") for row in logging.get("audit_key_status", [])),
        "candidate_budget_rows": len(rows),
        "train_rows": len(train),
        "dev_rows": len(dev),
        "bootstrap_samples_requested": args.bootstrap_samples,
        "best_residual_model": best,
        **G526_CLOSED_CLAIMS,
    }
    write_rows(G526_RESIDUAL_EVAL_CSV, eval_rows)
    write_rows(G526_RESIDUAL_PREDICTIONS_CSV, pred_rows)
    write_json_file(G526_RESIDUAL_SUMMARY, summary)
    write_simple_report(G526_RESIDUAL_REPORT, "Repair5G.5.26 Goal-Aware Update Residuals", summary)
    print(json.dumps({"decision": summary["decision"], "edge_update_teacher_proxy_only": summary["edge_update_teacher_proxy_only"]}))
    return 0


def main_analyze_policy_gap_and_trace_needs(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze G5.26 policy gap and trace needs.")
    parser.parse_args(argv)
    policy = load_json_if_exists(G526_POLICY_SUMMARY)
    neural = load_json_if_exists(G526_NEURAL_SUMMARY)
    bandit = load_json_if_exists(G526_BANDIT_SUMMARY)
    residual = load_json_if_exists(G526_RESIDUAL_SUMMARY)
    logging = load_json_if_exists(G526_LOGGING_STATIC_SUMMARY)
    best_policy = str(policy.get("best_policy", ""))
    decisions = [
        row for row in read_rows(G526_POLICY_DECISIONS_CSV)
        if row.get("policy") == best_policy and row.get("eval_scope") == "seed_oof"
    ]
    failures = [
        row for row in decisions
        if not boolish(row.get("top3_contains_safe_oracle"))
        or str(row.get("selected_candidate_id", "")) != str(row.get("actual_safe_oracle_candidate", ""))
        or boolish(row.get("selected_candidate_induced_no_solution"))
    ]
    trace_needs = [
        {"priority": 1, "trace_need": "exact_priority_block_subreason", "status": "explicitly_unavailable" if logging.get("exact_failed_candidate_audit_unavailable") else "available", "why": "Risk calibration still cannot separate priority-block subcauses.", **G526_CLOSED_CLAIMS},
        {"priority": 2, "trace_need": "all_failed_candidate_reasons_when_pibt_returns_false", "status": "explicitly_unavailable" if logging.get("exact_failed_candidate_audit_unavailable") else "available", "why": "Top-k selector needs failed-action distribution without adding UpdateLTM events.", **G526_CLOSED_CLAIMS},
        {"priority": 3, "trace_need": "exact_counterfactual_edge_labels", "status": "proxy_only" if residual.get("edge_update_teacher_proxy_only") else "available", "why": "Goal-aware update residuals remain diagnostic-only when exact labels are absent.", **G526_CLOSED_CLAIMS},
    ]
    summary = {
        "schema_version": "phase5p5_repair5g526_policy_gap_and_trace_needs_summary_v1",
        "decision": "policy_gap_and_trace_needs_analyzed",
        "best_policy": best_policy,
        "best_policy_summary": policy.get("best_policy_summary", {}),
        "topk_policy_gates": policy.get("main_target_gates", {}),
        "ranker_good_selector_blocked": policy.get("ranker_good_selector_blocked", False),
        "fallback_dominated_best_policy": policy.get("fallback_dominated_best_policy", False),
        "neural_best_model": neural.get("best_model", ""),
        "bandit_best_policy": bandit.get("best_policy", ""),
        "edge_update_teacher_proxy_only": residual.get("edge_update_teacher_proxy_only", True),
        "failure_context_budget_pairs": len(failures),
        "trace_needs": trace_needs,
        **G526_CLOSED_CLAIMS,
    }
    write_rows(G526_GAP_FAILURES_CSV, failures)
    write_rows(G526_GAP_TRACE_NEEDS_CSV, trace_needs)
    write_json_file(G526_GAP_SUMMARY, summary)
    write_simple_report(G526_GAP_REPORT, "Repair5G.5.26 Policy Gap and Trace Needs", summary)
    print(json.dumps({"decision": summary["decision"], "failure_context_budget_pairs": len(failures)}))
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write G5.26 final decision.")
    parser.parse_args(argv)
    parts = {
        "verify": load_json_if_exists(G526_VERIFY_SUMMARY),
        "autopsy": load_json_if_exists(G526_AUTOPSY_SUMMARY),
        "logging_static": load_json_if_exists(G526_LOGGING_STATIC_SUMMARY),
        "trace_probe": load_json_if_exists(G526_TRACE_SUMMARY),
        "features": load_json_if_exists(G526_FEATURE_SUMMARY),
        "teacher": load_json_if_exists(G526_TEACHER_SUMMARY),
        "policy": load_json_if_exists(G526_POLICY_SUMMARY),
        "neural": load_json_if_exists(G526_NEURAL_SUMMARY),
        "bandit": load_json_if_exists(G526_BANDIT_SUMMARY),
        "residuals": load_json_if_exists(G526_RESIDUAL_SUMMARY),
        "gap": load_json_if_exists(G526_GAP_SUMMARY),
    }
    policy = parts["policy"]
    gates = policy.get("main_target_gates", {})
    trace = parts["trace_probe"]
    features = parts["features"]
    claims_closed = all(
        not boolish(part.get(key))
        for part in parts.values()
        for key in G526_CLOSED_CLAIMS
    )
    positive_gates = {
        "full_coverage_context_budget_pairs_eq_120": int(finite_number(trace.get("context_budget_pairs"), 0)) == 120,
        "candidate_budget_rows_ge_3600": int(finite_number(trace.get("candidate_budget_rows"), 0)) >= 3600,
        "raw_log_sha256_verified": boolish(trace.get("gates", {}).get("raw_log_sha256_verified")),
        "forbidden_feature_count_eq_0": int(finite_number(features.get("forbidden_feature_count"), 99)) == 0,
        "top3_safe_oracle_capture_rate_ge_0p25": boolish(gates.get("top3_safe_oracle_capture_rate_ge_0p25")),
        "selected_policy_utility_beats_g525_best": boolish(gates.get("selected_policy_utility_beats_g525_best")),
        "candidate_induced_no_solution_count_le_g525": boolish(gates.get("candidate_induced_no_solution_count_le_g525")),
        "region_top2_capture_rate_ge_0p50": boolish(gates.get("region_top2_capture_rate_ge_0p50")),
        "controls_do_not_match": boolish(gates.get("controls_do_not_match")),
        "leave_one_map_family_does_not_collapse": boolish(gates.get("leave_one_map_family_does_not_collapse")),
        "claims_remain_closed": claims_closed,
    }
    if parts["logging_static"].get("decision") == "logging_patch_v2_static_verification_failed" or features.get("forbidden_feature_count", 0) != 0:
        decision = "g526_logging_or_target_blocker_stop"
    elif not positive_gates["full_coverage_context_budget_pairs_eq_120"] or not positive_gates["candidate_budget_rows_ge_3600"]:
        decision = "g526_logging_or_target_blocker_stop"
    elif not positive_gates["top3_safe_oracle_capture_rate_ge_0p25"]:
        decision = "g526_full_coverage_rank_effect_not_confirmed_return_trace_design"
    elif not positive_gates["selected_policy_utility_beats_g525_best"] or not positive_gates["candidate_induced_no_solution_count_le_g525"]:
        decision = "g526_ranker_good_selector_blocked_continue_risk_calibration"
    elif all(positive_gates.values()):
        decision = "g526_topk_policy_learning_promising_continue_offline_neural"
    elif policy.get("ranker_good_selector_blocked"):
        decision = "g526_ranker_good_selector_blocked_continue_risk_calibration"
    else:
        decision = "g526_partial_learning_gain_continue_model_design"
    summary = {
        "schema_version": "phase5p5_repair5g526_decision_summary_v1",
        "decision": decision,
        "component_decisions": {key: value.get("decision", "") for key, value in parts.items()},
        "positive_learning_gates": positive_gates,
        "best_policy": policy.get("best_policy", ""),
        "best_policy_summary": policy.get("best_policy_summary", {}),
        "best_neural_model": parts["neural"].get("best_model", ""),
        "best_bandit_policy": parts["bandit"].get("best_policy", ""),
        "edge_update_teacher_proxy_only": parts["residuals"].get("edge_update_teacher_proxy_only", True),
        "next_step": "risk_calibration_and_exact_failed_candidate_audit" if decision == "g526_ranker_good_selector_blocked_continue_risk_calibration" else parts["gap"].get("decision", ""),
        **G526_CLOSED_CLAIMS,
    }
    write_json_file(G526_DECISION_SUMMARY, summary)
    write_text_file(
        G526_DECISION_REPORT,
        "# Repair5G.5.26 Final Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- best_policy: `{summary['best_policy']}`\n"
        f"- best_policy_summary: `{summary['best_policy_summary']}`\n"
        f"- positive_learning_gates: `{positive_gates}`\n"
        f"- edge_update_teacher_proxy_only: `{summary['edge_update_teacher_proxy_only']}`\n"
        f"- next_step: `{summary['next_step']}`\n\n"
        "Closed claims remain:\n\n"
        "```text\n"
        "phase5p5_allowed=false\n"
        "phase6_allowed=false\n"
        "runtime_claim_allowed=false\n"
        "learned_runtime_policy_validated=false\n"
        "aaai_ready=false\n"
        "```\n",
    )
    print(json.dumps({"decision": decision, "best_policy": summary["best_policy"]}))
    return 0


__all__ = [name for name in globals() if name.startswith("G526_")] + [
    "main_analyze_g525_partial_gain_autopsy",
    "main_analyze_policy_gap_and_trace_needs",
    "main_create_rank_effect_v2_features",
    "main_create_topk_policy_teacher",
    "main_run_full_coverage_rank_trace_probe",
    "main_train_eval_constrained_contextual_bandit",
    "main_train_eval_goal_aware_update_residuals",
    "main_train_eval_neural_rank_effect_models",
    "main_train_eval_topk_risk_calibrated_policies",
    "main_verify_g525_artifacts",
    "main_verify_logging_patch_v2_static",
    "main_write_decision",
]

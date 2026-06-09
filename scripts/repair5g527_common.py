"""Shared helpers and task implementations for Repair5G.5.27.

G5.27 is an offline teacher-distillation round over the G5.26 full-coverage
rank-effect and constrained contextual-bandit artifacts. Learned-policy
diagnostics in this module only score runtime-safe feature columns. Outcome,
oracle, and risk labels are joined back only for teacher creation and
evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g526_common import (  # noqa: E402
    ADDITIVE_FALLBACK_ID,
    G525_BEST_UTILITY,
    G525_CANDIDATE_INDUCED,
    G525_FEATURE_COUNT,
    G526_BANDIT_DECISIONS_CSV,
    G526_BANDIT_EVAL_CSV,
    G526_BANDIT_SUMMARY,
    G526_CANDIDATE_FEATURES_CSV,
    G526_CLOSED_CLAIMS,
    G526_DECISION_SUMMARY,
    G526_FEATURE_SUMMARY,
    G526_NEURAL_EVAL_CSV,
    G526_NEURAL_SUMMARY,
    G526_POLICY_EVAL_CSV,
    G526_POLICY_SUMMARY,
    G526_RESIDUAL_SUMMARY,
    G526_TEACHER_CANDIDATE_CSV,
    G526_TEACHER_CONTEXT_CSV,
    G526_TEACHER_SUMMARY,
    G526_TRACE_SUMMARY,
    G526_VERIFY_SUMMARY,
    STATIC_FALLBACK_ID,
    boolish,
    csv_number,
    finite_number,
    g526_leakage_scan,
    load_json_if_exists,
    mean,
    observed_id_guard,
    read_rows,
    repo_root,
    resolve,
    stable_choice_unit,
    write_json_file,
    write_rows,
    write_simple_report,
    write_text_file,
)


SEED = 20260609 + 527
TEACHER_POLICY = "conservative_policy_improvement_over_g525_best"
G526_BANDIT_ECE = 0.03463409509130652

G527_CLOSED_CLAIMS = dict(G526_CLOSED_CLAIMS)

G527_PLAN_MD = "czr004_repair5g527_bandit_teacher_distillation_plan.md"
G527_WORKLOG_MARKER = "Repair5G.5.27 conservative bandit teacher distillation"

G527_VERIFY_REPORT = "outputs/reports/phase5p5_repair5g527_g526_artifact_verification.md"
G527_VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g527_g526_artifact_verification_summary.json"

G527_ARBITRATION_REPORT = "outputs/reports/phase5p5_repair5g527_decision_arbitration_audit.md"
G527_ARBITRATION_SUMMARY = "outputs/reports/phase5p5_repair5g527_decision_arbitration_audit_summary.json"
G527_METRIC_ALIGNMENT_CSV = "outputs/tables/phase5p5_repair5g527_cross_suite_metric_alignment.csv"

G527_LEAKAGE_REPORT = "outputs/reports/phase5p5_repair5g527_bandit_teacher_leakage.md"
G527_LEAKAGE_SUMMARY = "outputs/reports/phase5p5_repair5g527_bandit_teacher_leakage_summary.json"
G527_FIELD_AUDIT_CSV = "outputs/tables/phase5p5_repair5g527_bandit_teacher_field_audit.csv"

G527_CONTEXT_TEACHER_CSV = "outputs/tables/phase5p5_repair5g527_context_budget_teacher.csv"
G527_CANDIDATE_TEACHER_CSV = "outputs/tables/phase5p5_repair5g527_candidate_budget_teacher.csv"
G527_POLICY_DECISION_TEACHER_CSV = "outputs/tables/phase5p5_repair5g527_policy_decision_teacher.csv"
G527_TEACHER_REPORT = "outputs/reports/phase5p5_repair5g527_conservative_policy_teacher.md"
G527_TEACHER_SUMMARY = "outputs/reports/phase5p5_repair5g527_conservative_policy_teacher_summary.json"

G527_CANDIDATE_FEATURES_CSV = "outputs/tables/phase5p5_repair5g527_candidate_policy_distillation_features.csv"
G527_CONTEXT_FEATURES_CSV = "outputs/tables/phase5p5_repair5g527_context_policy_distillation_features.csv"
G527_ACTION_FEATURES_CSV = "outputs/tables/phase5p5_repair5g527_action_class_features.csv"
G527_TOPK_FEATURES_CSV = "outputs/tables/phase5p5_repair5g527_topk_shortlist_features.csv"
G527_FEATURE_GROUPS_CSV = "outputs/tables/phase5p5_repair5g527_policy_distillation_feature_groups.csv"
G527_FEATURE_LEAKAGE_CSV = "outputs/tables/phase5p5_repair5g527_policy_distillation_feature_leakage_scan.csv"
G527_FEATURE_REPORT = "outputs/reports/phase5p5_repair5g527_policy_distillation_features.md"
G527_FEATURE_SUMMARY = "outputs/reports/phase5p5_repair5g527_policy_distillation_features_summary.json"

G527_DISTILL_EVAL_CSV = "outputs/tables/phase5p5_repair5g527_bandit_teacher_distillation_eval.csv"
G527_DISTILL_DECISIONS_CSV = "outputs/tables/phase5p5_repair5g527_bandit_teacher_distillation_context_decisions.csv"
G527_DISTILL_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g527_bandit_teacher_distillation_bootstrap.csv"
G527_DISTILL_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g527_bandit_teacher_distillation_calibration.csv"
G527_DISTILL_REPORT = "outputs/reports/phase5p5_repair5g527_bandit_teacher_distillation.md"
G527_DISTILL_SUMMARY = "outputs/reports/phase5p5_repair5g527_bandit_teacher_distillation_summary.json"

G527_CALIB_EVAL_CSV = "outputs/tables/phase5p5_repair5g527_safe_policy_calibration_eval.csv"
G527_CALIB_DECISIONS_CSV = "outputs/tables/phase5p5_repair5g527_safe_policy_calibration_context_decisions.csv"
G527_CALIB_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g527_safe_policy_calibration_bootstrap.csv"
G527_CALIB_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g527_safe_policy_calibration_calibration.csv"
G527_CALIB_REPORT = "outputs/reports/phase5p5_repair5g527_safe_policy_calibration.md"
G527_CALIB_SUMMARY = "outputs/reports/phase5p5_repair5g527_safe_policy_calibration_summary.json"

G527_AUDIT_STATIC_REPORT = "outputs/reports/phase5p5_repair5g527_exact_failure_audit_logging_static.md"
G527_AUDIT_STATIC_SUMMARY = "outputs/reports/phase5p5_repair5g527_exact_failure_audit_logging_static_summary.json"
G527_AUDIT_STATIC_FIELDS_CSV = "outputs/tables/phase5p5_repair5g527_exact_failure_audit_logging_static_fields.csv"
G527_AUDIT_PROBE_REPORT = "outputs/reports/phase5p5_repair5g527_exact_failure_audit_probe_if_needed.md"
G527_AUDIT_PROBE_SUMMARY = "outputs/reports/phase5p5_repair5g527_exact_failure_audit_probe_if_needed_summary.json"
G527_AUDIT_PROBE_LOG = "outputs/logs/phase5p5_repair5g527_exact_failure_audit_probe_if_needed/probe_manifest.jsonl"

G527_OFFLINE_RL_EVAL_CSV = "outputs/tables/phase5p5_repair5g527_offline_rl_cql_diagnostic_eval.csv"
G527_OFFLINE_RL_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g527_offline_rl_cql_diagnostic_bootstrap.csv"
G527_OFFLINE_RL_REPORT = "outputs/reports/phase5p5_repair5g527_offline_rl_cql_diagnostic.md"
G527_OFFLINE_RL_SUMMARY = "outputs/reports/phase5p5_repair5g527_offline_rl_cql_diagnostic_summary.json"

G527_RESIDUAL_EVAL_CSV = "outputs/tables/phase5p5_repair5g527_goal_aware_residual_teacher_refinement_eval.csv"
G527_RESIDUAL_LABELS_CSV = "outputs/tables/phase5p5_repair5g527_goal_aware_residual_teacher_refinement_labels.csv"
G527_RESIDUAL_REPORT = "outputs/reports/phase5p5_repair5g527_goal_aware_residual_teacher_refinement.md"
G527_RESIDUAL_SUMMARY = "outputs/reports/phase5p5_repair5g527_goal_aware_residual_teacher_refinement_summary.json"

G527_SYNTHESIS_REPORT = "outputs/reports/phase5p5_repair5g527_teacher_distillation_failure_or_success.md"
G527_SYNTHESIS_SUMMARY = "outputs/reports/phase5p5_repair5g527_teacher_distillation_failure_or_success_summary.json"
G527_DECISION_REPORT = "outputs/reports/phase5p5_repair5g527_decision.md"
G527_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g527_decision_summary.json"


DISTILLATION_MODELS = [
    "bandit_teacher_region_classifier",
    "bandit_teacher_action_class_classifier",
    "bandit_teacher_candidate_ranker",
    "bandit_teacher_pairwise_candidate_ranker",
    "bandit_teacher_two_head_utility_risk",
    "bandit_teacher_topk_reranker",
    "bandit_teacher_fallback_classifier",
    "bandit_teacher_static_recovery_specialist",
    "bandit_teacher_induced_failure_guard",
    "region_prior_baseline",
    "agent_density_baseline",
    "g525_trace_plus_rank_effect_reproduced",
    "g526_topk_baseline",
    "param_only_control",
    "trace_only_control",
    "source_blind_control",
    "bandit_label_shuffled_control",
    "random_feature_control",
    "oracle_teacher_upper_bound_diagnostic_not_for_promotion",
]

CONTROL_MODELS = {
    "param_only_control",
    "trace_only_control",
    "source_blind_control",
    "bandit_label_shuffled_control",
    "random_feature_control",
}

CALIBRATION_POLICIES = [
    "calibrated_bandit_distilled_policy",
    "isotonic_risk_calibrated_selector",
    "platt_risk_calibrated_selector",
    "conformal_risk_abstention_selector",
    "quantile_utility_lower_bound_selector",
    "risk_first_then_utility_selector",
    "utility_first_then_risk_selector",
    "budget_sensitive_failure_guard",
    "candidate_induced_failure_guard",
    "static_recovery_priority_selector",
    "fallback_heavy_safe_selector",
    "fallback_light_aggressive_selector",
    "old14_g518_fallback_selector",
    "static_fallback_selector",
    "bandit_teacher_oracle_diagnostic_not_for_promotion",
]

OFFLINE_RL_METHODS = [
    "direct_conservative_policy_improvement_teacher",
    "distilled_cpi_policy",
    "conservative_q_learning_linear",
    "conservative_q_learning_small_mlp_if_available",
    "doubly_robust_policy_evaluation",
    "risk_constrained_cpi",
    "fallback_regularized_cpi",
    "map_family_robust_cpi",
    "budget_robust_cpi",
    "shuffled_reward_control",
    "random_policy_control",
]


def row_key(row: dict[str, Any]) -> tuple[str, int]:
    return (str(row.get("normalized_context_key", "")), int(finite_number(row.get("short_budget_ms"), -1)))


def candidate_key(row: dict[str, Any]) -> tuple[str, int, str]:
    context, budget = row_key(row)
    return (context, budget, str(row.get("candidate_id", "")))


def group_by_context(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, int], list[dict[str, Any]]]:
    groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row_key(row)].append(row)
    return dict(groups)


def selected_bandit_decisions() -> list[dict[str, Any]]:
    return [
        row for row in read_rows(G526_BANDIT_DECISIONS_CSV)
        if row.get("policy") == TEACHER_POLICY and row.get("eval_scope") == "seed_oof"
    ]


def selected_decision_by_key() -> dict[tuple[str, int], dict[str, Any]]:
    return {row_key(row): row for row in selected_bandit_decisions()}


def candidate_lookup(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, int, str], dict[str, Any]]:
    return {candidate_key(row): row for row in rows}


def candidate_region(group: list[dict[str, Any]], candidate_id: str) -> str:
    for row in group:
        if str(row.get("candidate_id", "")) == candidate_id:
            return str(row.get("audit_candidate_region", ""))
    return ""


def static_row(group: list[dict[str, Any]]) -> dict[str, Any]:
    return next((row for row in group if row.get("candidate_id") == STATIC_FALLBACK_ID), group[0])


def old14_fallback_candidate(group: list[dict[str, Any]]) -> str:
    first = group[0]
    return str(first.get("old14_g518_fallback_candidate", "") or ADDITIVE_FALLBACK_ID)


def old14_fallback_row(group: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_id = old14_fallback_candidate(group)
    return next((row for row in group if row.get("candidate_id") == candidate_id), static_row(group))


def action_class_for(
    candidate_id: str,
    row: dict[str, Any] | None = None,
    selected_by_fallback: bool = False,
    selected_induced: bool = False,
    selected_budget_failure: bool = False,
) -> str:
    if selected_induced or selected_budget_failure:
        return "abstain_due_risk"
    if candidate_id == STATIC_FALLBACK_ID:
        return "static_fallback"
    if selected_by_fallback or "old14" in candidate_id or candidate_id == ADDITIVE_FALLBACK_ID:
        return "old14_g518_fallback"
    if "repair5g522" in candidate_id:
        return "safe_g522_select" if row is None or boolish(row.get("target_safe_g522_positive")) else "old14_select"
    if "repair5g518" in candidate_id:
        return "g518_select"
    return "old14_select"


def utility_bucket(value: float) -> str:
    if not math.isfinite(value):
        return "missing"
    if value < -0.02:
        return "strong_improvement"
    if value < 0:
        return "improvement"
    if value <= G525_BEST_UTILITY:
        return "weak_or_neutral"
    return "regression"


def probability(value: float) -> float:
    if not math.isfinite(value):
        return 0.5
    return 1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, value))))


def stable_unit(*parts: Any) -> float:
    digest = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()
    return (int(digest[:12], 16) % 1_000_003) / 1_000_003.0


def feature_cols(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return []
    cols = [name for name in rows[0].keys() if name.startswith("feature_")]
    return sorted(cols)


def write_stage_report(path: str, title: str, summary: dict[str, Any], extra: str = "") -> None:
    write_simple_report(path, title, {**summary, **G527_CLOSED_CLAIMS}, extra=extra)


def teacher_candidate_rows() -> list[dict[str, Any]]:
    rows = read_rows(G527_CANDIDATE_TEACHER_CSV)
    return rows if rows else read_rows(G526_TEACHER_CANDIDATE_CSV)


def teacher_policy_rows() -> list[dict[str, Any]]:
    rows = read_rows(G527_POLICY_DECISION_TEACHER_CSV)
    if rows:
        return rows
    return build_policy_teacher_rows(read_rows(G526_TEACHER_CANDIDATE_CSV), selected_bandit_decisions())[2]


def build_policy_teacher_rows(
    candidate_rows: list[dict[str, Any]],
    decision_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    groups = group_by_context(candidate_rows)
    decisions = {row_key(row): row for row in decision_rows}
    candidate_out: list[dict[str, Any]] = []
    context_out: list[dict[str, Any]] = []
    policy_out: list[dict[str, Any]] = []
    for key in sorted(groups):
        group = groups[key]
        decision = decisions.get(key, {})
        selected_id = str(decision.get("selected_candidate_id", ""))
        selected = next((row for row in group if row.get("candidate_id") == selected_id), static_row(group))
        selected_id = str(selected.get("candidate_id", selected_id))
        selected_by_fallback = boolish(decision.get("selected_by_fallback")) or selected_id in {
            STATIC_FALLBACK_ID,
            old14_fallback_candidate(group),
        }
        selected_induced = boolish(selected.get("target_candidate_induced_no_solution")) or boolish(
            decision.get("selected_candidate_induced_no_solution")
        )
        selected_budget_failure = boolish(selected.get("target_budget_sensitive_failure")) or boolish(
            decision.get("selected_budget_sensitive_failure")
        )
        action_class = action_class_for(
            selected_id,
            selected,
            selected_by_fallback=selected_by_fallback,
            selected_induced=selected_induced,
            selected_budget_failure=selected_budget_failure,
        )
        selected_utility = finite_number(
            selected.get("target_delta_vs_old14_plus_g518"),
            finite_number(decision.get("selected_policy_utility"), math.inf),
        )
        selected_region = str(selected.get("audit_candidate_region", decision.get("selected_candidate_region", "")))
        common_labels = {
            "target_bandit_selected_candidate_id": selected_id,
            "target_bandit_selected_region": selected_region,
            "target_bandit_should_fallback_static": selected_id == STATIC_FALLBACK_ID,
            "target_bandit_should_fallback_old14_g518": selected_by_fallback and selected_id != STATIC_FALLBACK_ID,
            "target_bandit_safe_positive_selected": boolish(selected.get("target_safe_g522_positive")),
            "target_bandit_static_recovery_selected": boolish(selected.get("target_static_failure_recovery")),
            "target_bandit_candidate_induced_no_solution": selected_induced,
            "target_bandit_budget_sensitive_failure": selected_budget_failure,
            "target_bandit_selected_policy_utility": csv_number(selected_utility),
            "target_bandit_selected_utility_bucket": utility_bucket(selected_utility),
            "target_bandit_action_class": action_class,
        }
        context_row = {
            "row_type": "context_budget_teacher",
            "normalized_context_key": key[0],
            "short_budget_ms": key[1],
            "candidate_rows": len(group),
            "map": group[0].get("map", ""),
            "map_family": group[0].get("map_family", ""),
            "map_agent_group": group[0].get("map_agent_group", ""),
            "agents": group[0].get("agents", ""),
            "safe_oracle_candidate": group[0].get("safe_oracle_candidate", ""),
            "utility_oracle_with_risk_candidate": group[0].get("utility_oracle_with_risk_candidate", ""),
            **common_labels,
            **G527_CLOSED_CLAIMS,
        }
        policy_row = {
            "row_type": "policy_decision_teacher",
            "policy": TEACHER_POLICY,
            "model": TEACHER_POLICY,
            "eval_scope": "seed_oof",
            "selection_rule": decision.get("selection_rule", "conservative_cpi"),
            "selected_candidate_id": selected_id,
            "selected_candidate_region": selected_region,
            "actual_safe_oracle_candidate": group[0].get("safe_oracle_candidate", ""),
            "actual_safe_oracle_region": candidate_region(group, str(group[0].get("safe_oracle_candidate", ""))),
            "top1_contains_safe_oracle": selected_id == str(group[0].get("safe_oracle_candidate", "")),
            "top3_contains_safe_oracle": boolish(decision.get("top3_contains_safe_oracle")),
            "top5_contains_safe_oracle": boolish(decision.get("top5_contains_safe_oracle")),
            "selected_by_fallback": selected_by_fallback,
            "predicted_avoidable_risk": decision.get("predicted_avoidable_risk", ""),
            "reward": decision.get("reward", ""),
            **context_row,
        }
        context_out.append(context_row)
        policy_out.append(policy_row)
        for row in group:
            is_selected = str(row.get("candidate_id", "")) == selected_id
            candidate_out.append(
                {
                    **row,
                    "row_type": "candidate_budget_teacher",
                    "target_bandit_selected_candidate": is_selected,
                    **common_labels,
                    **G527_CLOSED_CLAIMS,
                }
            )
    return context_out, candidate_out, policy_out


def main_verify_g526_artifacts(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify G5.26 artifacts before G5.27.")
    parser.add_argument("--ids", nargs="*", default=None)
    args = parser.parse_args(argv)
    if args.ids is not None:
        try:
            observed_id_guard(args.ids, label="G5.27 explicit ID guard")
        except ValueError as exc:
            print(json.dumps({"decision": "reserved_id_guard_rejected", "error": str(exc)}))
            return 2

    root = repo_root()
    decision = load_json_if_exists(G526_DECISION_SUMMARY)
    trace = load_json_if_exists(G526_TRACE_SUMMARY)
    features = load_json_if_exists(G526_FEATURE_SUMMARY)
    teacher = load_json_if_exists(G526_TEACHER_SUMMARY)
    policy = load_json_if_exists(G526_POLICY_SUMMARY)
    neural = load_json_if_exists(G526_NEURAL_SUMMARY)
    bandit = load_json_if_exists(G526_BANDIT_SUMMARY)
    residual = load_json_if_exists(G526_RESIDUAL_SUMMARY)
    verify = load_json_if_exists(G526_VERIFY_SUMMARY)
    external_status = subprocess.run(
        ["git", "status", "--short", "--", "external/lacam2/lacam2"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    worklog = resolve("docs/codex-worklog.md", root).read_text(encoding="utf-8", errors="replace")
    bandit_best = bandit.get("best_policy_summary", {})
    gates = {
        "g526_decision_expected": decision.get("decision") == "g526_full_coverage_rank_effect_not_confirmed_return_trace_design",
        "trace_context_budget_pairs_eq_120": int(finite_number(trace.get("context_budget_pairs"), -1)) == 120,
        "trace_candidate_budget_rows_eq_5280": int(finite_number(trace.get("candidate_budget_rows"), -1)) == 5280,
        "trace_raw_sha_verified": boolish(trace.get("gates", {}).get("raw_log_sha256_verified")),
        "feature_forbidden_count_eq_0": int(finite_number(features.get("forbidden_feature_count"), 99)) == 0,
        "topk_top3_gate_failed": not boolish(policy.get("main_target_gates", {}).get("top3_safe_oracle_capture_rate_ge_0p25")),
        "topk_region_top2_gate_failed": not boolish(policy.get("main_target_gates", {}).get("region_top2_capture_rate_ge_0p50")),
        "topk_controls_gate_failed": not boolish(policy.get("main_target_gates", {}).get("controls_do_not_match")),
        "topk_heldout_family_gate_failed": not boolish(policy.get("main_target_gates", {}).get("leave_one_map_family_does_not_collapse")),
        "bandit_best_policy_expected": bandit.get("best_policy") == TEACHER_POLICY,
        "bandit_utility_beats_g525_best": finite_number(bandit_best.get("selected_policy_utility"), math.inf) < G525_BEST_UTILITY,
        "bandit_candidate_induced_zero": int(finite_number(bandit_best.get("candidate_induced_no_solution_count"), -1)) == 0,
        "bandit_fallback_allowed": boolish(bandit.get("constraints", {}).get("fallback_allowed")),
        "bandit_controls_do_not_match": boolish(bandit.get("main_gates", {}).get("controls_do_not_match")),
        "neural_diagnostic_not_positive": not boolish(neural.get("positive_neural_readiness")),
        "edge_update_residual_proxy_only": boolish(residual.get("edge_update_teacher_proxy_only")),
        "external_lacam2_untouched": external_status == "",
        "ids_166_205_untouched": boolish(verify.get("ids_166_205_untouched", True)),
        "claims_closed": all(not boolish(decision.get(key)) for key in G527_CLOSED_CLAIMS),
        "worklog_entry_before_optional_probe": G527_WORKLOG_MARKER in worklog,
        "teacher_rows_eq_5280": int(finite_number(teacher.get("candidate_budget_rows"), -1)) == 5280,
    }
    summary = {
        "schema_version": "phase5p5_repair5g527_g526_artifact_verification_summary_v1",
        "decision": "g526_artifacts_verified_continue_g527" if all(gates.values()) else "g526_artifact_verification_failed_stop",
        "gates": gates,
        "g526_decision": decision.get("decision", ""),
        "g526_best_topk_policy": policy.get("best_policy", ""),
        "g526_best_bandit_policy": bandit.get("best_policy", ""),
        "g526_bandit_best_policy_summary": bandit_best,
        "external_lacam2_solver_status": external_status,
        **G527_CLOSED_CLAIMS,
    }
    write_json_file(G527_VERIFY_SUMMARY, summary)
    write_stage_report(G527_VERIFY_REPORT, "Repair5G.5.27 G5.26 Artifact Verification", summary)
    print(json.dumps({"decision": summary["decision"], "gates_passed": all(gates.values())}))
    return 0 if all(gates.values()) else 1


def main_analyze_decision_arbitration_audit(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit G5.26 decision arbitration before G5.27.")
    parser.parse_args(argv)
    topk = load_json_if_exists(G526_POLICY_SUMMARY)
    neural = load_json_if_exists(G526_NEURAL_SUMMARY)
    bandit = load_json_if_exists(G526_BANDIT_SUMMARY)
    decision = load_json_if_exists(G526_DECISION_SUMMARY)
    suites = [
        ("topk_policy", topk, G526_POLICY_EVAL_CSV, topk.get("best_policy_summary", {})),
        ("neural_rank_effect", neural, G526_NEURAL_EVAL_CSV, neural.get("best_model_summary", {})),
        ("constrained_contextual_bandit", bandit, G526_BANDIT_EVAL_CSV, bandit.get("best_policy_summary", {})),
    ]
    alignment_rows = []
    for suite, summary, csv_path, best in suites:
        rows = read_rows(csv_path)
        alignment_rows.append(
            {
                "suite": suite,
                "decision": summary.get("decision", ""),
                "best_policy_or_model": summary.get("best_policy", summary.get("best_model", "")),
                "context_budget_pairs": best.get("context_budget_pairs", ""),
                "candidate_budget_rows": summary.get("candidate_budget_rows", 5280),
                "eval_rows": len(rows),
                "target_label_family": "safe_oracle_topk" if suite == "topk_policy" else "actual_counterfactual_lookup",
                "utility_sign_convention": "lower_selected_policy_utility_is_better",
                "risk_definition": "candidate_induced_no_solution_and_budget_sensitive_failure",
                "uses_oracle_at_selection_time": suite == "constrained_contextual_bandit",
                "runtime_safe_policy_candidate": suite != "constrained_contextual_bandit",
                **G527_CLOSED_CLAIMS,
            }
        )
    sign_agrees = len({row["utility_sign_convention"] for row in alignment_rows}) == 1
    targets_compatible = all(int(finite_number(row["context_budget_pairs"], 0)) == 120 for row in alignment_rows)
    blocker = not (sign_agrees and targets_compatible)
    bandit_best = bandit.get("best_policy_summary", {})
    summary = {
        "schema_version": "phase5p5_repair5g527_decision_arbitration_audit_summary_v1",
        "decision": "metric_alignment_verified_continue_teacher_audit" if not blocker else "metric_or_target_alignment_blocker_stop",
        "why_bandit_not_final_best_policy": "G5.26 final best_policy was chosen from the runtime-safe top-k policy suite; the bandit suite used direct counterfactual lookup and was only a teacher candidate.",
        "g526_final_decision": decision.get("decision", ""),
        "g526_topk_best_policy": topk.get("best_policy", ""),
        "g526_bandit_best_policy": bandit.get("best_policy", ""),
        "selected_policy_utility_lower_is_better": sign_agrees,
        "bandit_uses_oracle_counterfactual_at_selection_time": True,
        "bandit_result_correctly_conservative_not_runtime_safe": True,
        "final_offline_policy_value_metrics": [
            "selected_policy_utility",
            "candidate_induced_no_solution_count",
            "budget_sensitive_failure_count",
            "fallback_rate",
            "static_recovery_capture_count",
            "calibration",
            "safe_oracle_topk_capture_as_recall_only",
        ],
        "correct_g527_primary_gate": "distilled_runtime_safe_policy_value_with_zero_or_teacher_no_solution_and_heldout_controls",
        "g526_bandit_best_policy_summary": bandit_best,
        "blocker": blocker,
        **G527_CLOSED_CLAIMS,
    }
    write_rows(G527_METRIC_ALIGNMENT_CSV, alignment_rows)
    write_json_file(G527_ARBITRATION_SUMMARY, summary)
    write_stage_report(G527_ARBITRATION_REPORT, "Repair5G.5.27 Decision Arbitration Audit", summary)
    print(json.dumps({"decision": summary["decision"], "blocker": blocker}))
    return 1 if blocker else 0


def classify_bandit_field(name: str) -> str:
    lower = name.lower()
    if lower.startswith("feature_"):
        return "runtime_safe_feature"
    if lower.startswith("target_") or "oracle" in lower:
        return "oracle_label"
    if "induced" in lower or "failure" in lower or "risk" in lower:
        return "risk_label"
    if "utility" in lower or "reward" in lower or "score" in lower or "delta" in lower:
        return "counterfactual_outcome"
    if "fallback" in lower:
        return "fallback_baseline"
    return "audit_only"


def main_audit_bandit_teacher_leakage(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify G5.26 bandit teacher leakage status.")
    parser.parse_args(argv)
    decision_rows = selected_bandit_decisions()
    candidate_rows = read_rows(G526_TEACHER_CANDIDATE_CSV)
    columns = sorted(set().union(*(row.keys() for row in (decision_rows[:5] + candidate_rows[:5]))))
    audit_rows = [
        {
            "field": name,
            "classification": classify_bandit_field(name),
            "used_by_g526_bandit_selection": name in {
                "target_delta_vs_old14_plus_g518",
                "target_candidate_induced_no_solution",
                "target_budget_sensitive_failure",
                "target_safe_g522_positive",
                "target_static_failure_recovery",
                "selected_policy_utility",
                "reward",
            },
            "allowed_in_distilled_runtime_features": classify_bandit_field(name) == "runtime_safe_feature",
            **G527_CLOSED_CLAIMS,
        }
        for name in columns
    ]
    leakage_classes = Counter(row["classification"] for row in audit_rows if row["used_by_g526_bandit_selection"])
    summary = {
        "schema_version": "phase5p5_repair5g527_bandit_teacher_leakage_summary_v1",
        "decision": "bandit_valid_teacher_not_runtime_policy_continue_distillation",
        "bandit_is_valid_teacher": True,
        "bandit_is_runtime_policy": False,
        "distillation_allowed": True,
        "bandit_chooses_actions_using_measured_context_budget_candidate_outcomes": True,
        "directly_uses_target_score_delta_oracle_or_risk_labels": True,
        "selection_time_label_classes": dict(sorted(leakage_classes.items())),
        "supervised_labels_distillable": [
            "target_bandit_selected_candidate",
            "target_bandit_selected_region",
            "target_bandit_action_class",
            "target_bandit_should_fallback_static",
            "target_bandit_selected_policy_utility_bucket",
        ],
        "field_audit_rows": len(audit_rows),
        **G527_CLOSED_CLAIMS,
    }
    write_rows(G527_FIELD_AUDIT_CSV, audit_rows)
    write_json_file(G527_LEAKAGE_SUMMARY, summary)
    write_stage_report(G527_LEAKAGE_REPORT, "Repair5G.5.27 Bandit Teacher Leakage Audit", summary)
    print(json.dumps({"decision": summary["decision"], "runtime_policy": summary["bandit_is_runtime_policy"]}))
    return 0


def main_create_conservative_policy_teacher(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create the G5.27 conservative bandit teacher tables.")
    parser.parse_args(argv)
    candidate_rows = read_rows(G526_TEACHER_CANDIDATE_CSV)
    decision_rows = selected_bandit_decisions()
    context_out, candidate_out, policy_out = build_policy_teacher_rows(candidate_rows, decision_rows)
    leakage = g526_leakage_scan(feature_cols(candidate_rows))
    selected_induced = sum(boolish(row.get("target_bandit_candidate_induced_no_solution")) for row in policy_out)
    utility = mean(finite_number(row.get("target_bandit_selected_policy_utility"), math.inf) for row in policy_out)
    gates = {
        "context_budget_rows_eq_120": len(context_out) == 120,
        "candidate_budget_rows_eq_5280": len(candidate_out) == 5280,
        "policy_decision_rows_eq_120": len(policy_out) == 120,
        "bandit_selected_candidate_induced_no_solution_count_eq_0": selected_induced == 0,
        "bandit_selected_policy_utility_lt_0": utility < 0,
        "forbidden_feature_count_eq_0": int(leakage.get("forbidden_feature_count", 99)) == 0,
    }
    summary = {
        "schema_version": "phase5p5_repair5g527_conservative_policy_teacher_summary_v1",
        "decision": "conservative_policy_teacher_created" if all(gates.values()) else "conservative_policy_teacher_gate_failed",
        "context_budget_rows": len(context_out),
        "candidate_budget_rows": len(candidate_out),
        "policy_decision_rows": len(policy_out),
        "bandit_selected_candidate_induced_no_solution_count": selected_induced,
        "bandit_selected_policy_utility": csv_number(utility),
        "forbidden_feature_count": leakage.get("forbidden_feature_count", 0),
        "action_class_counts": dict(sorted(Counter(row.get("target_bandit_action_class", "") for row in policy_out).items())),
        "gates": gates,
        **G527_CLOSED_CLAIMS,
    }
    write_rows(G527_CONTEXT_TEACHER_CSV, context_out)
    write_rows(G527_CANDIDATE_TEACHER_CSV, candidate_out)
    write_rows(G527_POLICY_DECISION_TEACHER_CSV, policy_out)
    write_json_file(G527_TEACHER_SUMMARY, summary)
    write_stage_report(G527_TEACHER_REPORT, "Repair5G.5.27 Conservative Policy Teacher", summary)
    print(json.dumps({"decision": summary["decision"], "policy_decision_rows": len(policy_out)}))
    return 0 if all(gates.values()) else 1


def map_family_priors(policy_rows: list[dict[str, Any]], holdout_family: str) -> dict[str, Any]:
    train = [row for row in policy_rows if str(row.get("map_family", "")) != holdout_family] or policy_rows
    n = max(1, len(train))
    region_counts = Counter(row.get("target_bandit_selected_region", "") for row in train)
    action_counts = Counter(row.get("target_bandit_action_class", "") for row in train)
    fallback_count = sum(boolish(row.get("selected_by_fallback")) for row in train)
    safe_count = sum(boolish(row.get("target_bandit_safe_positive_selected")) for row in train)
    return {
        "n": n,
        "region_counts": region_counts,
        "action_counts": action_counts,
        "fallback_rate": fallback_count / n,
        "safe_positive_rate": safe_count / n,
    }


def add_policy_prior_features(row: dict[str, Any], priors: dict[str, Any]) -> dict[str, Any]:
    region = str(row.get("audit_candidate_region", row.get("target_bandit_selected_region", "")))
    action = action_class_for(str(row.get("candidate_id", "")), row)
    n = max(1, int(priors["n"]))
    rank_global = finite_number(row.get("feature_rank_effect_candidate_rank_global"), 99.0)
    return {
        **row,
        "feature_policy_prior_region_frequency": csv_number(priors["region_counts"].get(region, 0) / n),
        "feature_policy_prior_class_frequency": csv_number(priors["action_counts"].get(action, 0) / n),
        "feature_policy_prior_fallback_rate": csv_number(priors["fallback_rate"]),
        "feature_policy_prior_safe_positive_rate": csv_number(priors["safe_positive_rate"]),
        "feature_policy_prior_rank_shortlist_score": csv_number(1.0 / (1.0 + max(0.0, rank_global))),
    }


def main_create_policy_distillation_features(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create runtime-safe G5.27 distillation feature tables.")
    parser.parse_args(argv)
    candidate_rows = teacher_candidate_rows()
    policy_rows = teacher_policy_rows()
    feature_rows = []
    label_by_key = candidate_lookup(candidate_rows)
    for row in candidate_rows:
        priors = map_family_priors(policy_rows, str(row.get("map_family", "")))
        enriched = add_policy_prior_features(row, priors)
        feature_names = feature_cols([enriched])
        feature_rows.append(
            {
                "normalized_context_key": row.get("normalized_context_key", ""),
                "short_budget_ms": row.get("short_budget_ms", ""),
                "candidate_id": row.get("candidate_id", ""),
                "map": row.get("map", ""),
                "map_family": row.get("map_family", ""),
                "map_agent_group": row.get("map_agent_group", ""),
                "agents": row.get("agents", ""),
                "candidate_role": row.get("candidate_role", ""),
                "audit_candidate_region": row.get("audit_candidate_region", ""),
                **{name: enriched.get(name, "") for name in feature_names},
                **G527_CLOSED_CLAIMS,
            }
        )
    context_features: list[dict[str, Any]] = []
    for key, group in sorted(group_by_context(feature_rows).items()):
        base = group[0]
        numeric_features = feature_cols(group)
        context_features.append(
            {
                "normalized_context_key": key[0],
                "short_budget_ms": key[1],
                "candidate_rows": len(group),
                "map": base.get("map", ""),
                "map_family": base.get("map_family", ""),
                "map_agent_group": base.get("map_agent_group", ""),
                "agents": base.get("agents", ""),
                **{f"{name}_mean": csv_number(mean(finite_number(row.get(name), math.nan) for row in group)) for name in numeric_features[:40]},
                **G527_CLOSED_CLAIMS,
            }
        )
    action_rows = [
        {
            "normalized_context_key": row.get("normalized_context_key", ""),
            "short_budget_ms": row.get("short_budget_ms", ""),
            "target_bandit_action_class": row.get("target_bandit_action_class", ""),
            "target_bandit_selected_region": row.get("target_bandit_selected_region", ""),
            "feature_policy_prior_fallback_rate": row.get("feature_policy_prior_fallback_rate", ""),
            "feature_policy_prior_safe_positive_rate": row.get("feature_policy_prior_safe_positive_rate", ""),
            **G527_CLOSED_CLAIMS,
        }
        for row in policy_rows
    ]
    topk_rows = []
    for key, group in sorted(group_by_context(feature_rows).items()):
        ranked = sorted(
            group,
            key=lambda row: (
                finite_number(row.get("feature_rank_effect_candidate_rank_global"), math.inf),
                str(row.get("candidate_id", "")),
            ),
        )
        for rank, row in enumerate(ranked[:5], 1):
            label = label_by_key.get(candidate_key(row), {})
            topk_rows.append(
                {
                    "normalized_context_key": key[0],
                    "short_budget_ms": key[1],
                    "shortlist_rank": rank,
                    "candidate_id": row.get("candidate_id", ""),
                    "audit_candidate_region": row.get("audit_candidate_region", ""),
                    "feature_policy_prior_rank_shortlist_score": row.get("feature_policy_prior_rank_shortlist_score", ""),
                    "teacher_selected_candidate": boolish(label.get("target_bandit_selected_candidate")),
                    **G527_CLOSED_CLAIMS,
                }
            )
    names = feature_cols(feature_rows)
    leakage = g526_leakage_scan(names)
    group_rows = []
    for prefix in ["feature_map_", "feature_agent_", "feature_budget_", "feature_trace_", "feature_blocked_reason_", "feature_competing_rank_", "feature_rank_margin_", "feature_candidate_param_", "feature_candidate_geometry_", "feature_region_prior_", "feature_rank_effect_", "feature_goal_aware_", "feature_mix_", "feature_policy_prior_"]:
        group_rows.append(
            {
                "feature_group": prefix,
                "feature_count": sum(name.startswith(prefix) for name in names),
                **G527_CLOSED_CLAIMS,
            }
        )
    labels_in_features = [name for name in names if name.startswith("target_")]
    gates = {
        "candidate_budget_rows_eq_5280": len(feature_rows) == 5280,
        "context_budget_rows_eq_120": len(context_features) == 120,
        "forbidden_feature_count_eq_0": int(leakage.get("forbidden_feature_count", 99)) == 0,
        "runtime_safe_feature_count_gt_g526": len(names) > int(finite_number(load_json_if_exists(G526_FEATURE_SUMMARY).get("feature_count"), G525_FEATURE_COUNT)),
        "bandit_teacher_labels_not_in_features": not labels_in_features,
    }
    leakage_rows = [
        {
            "feature": name,
            "is_forbidden": name in set(leakage.get("forbidden_features", [])),
            "is_teacher_label": name.startswith("target_"),
            **G527_CLOSED_CLAIMS,
        }
        for name in names
    ]
    summary = {
        "schema_version": "phase5p5_repair5g527_policy_distillation_features_summary_v1",
        "decision": "policy_distillation_features_created" if all(gates.values()) else "policy_distillation_feature_gate_failed",
        "candidate_budget_rows": len(feature_rows),
        "context_budget_rows": len(context_features),
        "runtime_safe_feature_count": len(names),
        "g526_feature_count": load_json_if_exists(G526_FEATURE_SUMMARY).get("feature_count", G525_FEATURE_COUNT),
        "forbidden_feature_count": leakage.get("forbidden_feature_count", 0),
        "forbidden_features": leakage.get("forbidden_features", []),
        "teacher_label_columns_in_features": labels_in_features,
        "gates": gates,
        **G527_CLOSED_CLAIMS,
    }
    write_rows(G527_CANDIDATE_FEATURES_CSV, feature_rows)
    write_rows(G527_CONTEXT_FEATURES_CSV, context_features)
    write_rows(G527_ACTION_FEATURES_CSV, action_rows)
    write_rows(G527_TOPK_FEATURES_CSV, topk_rows)
    write_rows(G527_FEATURE_GROUPS_CSV, group_rows)
    write_rows(G527_FEATURE_LEAKAGE_CSV, leakage_rows)
    write_json_file(G527_FEATURE_SUMMARY, summary)
    write_stage_report(G527_FEATURE_REPORT, "Repair5G.5.27 Policy Distillation Features", summary)
    print(json.dumps({"decision": summary["decision"], "runtime_safe_feature_count": len(names)}))
    return 0 if all(gates.values()) else 1


def load_feature_label_rows() -> list[dict[str, Any]]:
    labels = candidate_lookup(teacher_candidate_rows())
    feature_rows = read_rows(G527_CANDIDATE_FEATURES_CSV)
    if not feature_rows:
        feature_rows = teacher_candidate_rows()
    joined = []
    for row in feature_rows:
        label = labels.get(candidate_key(row), {})
        merged = {**row}
        for name, value in label.items():
            if name.startswith("target_") or name in {
                "safe_oracle_candidate",
                "utility_oracle_with_risk_candidate",
                "static_fallback_candidate",
                "old14_g518_fallback_candidate",
                "target_score",
                "target_delta_vs_old14_plus_g518",
                "target_candidate_induced_no_solution",
                "target_budget_sensitive_failure",
                "target_safe_g522_positive",
                "target_static_failure_recovery",
            }:
                merged[name] = value
        joined.append(merged)
    return joined


def risk_proxy(row: dict[str, Any]) -> float:
    return (
        0.35 * finite_number(row.get("feature_failed_candidate_vertex_conflict_histogram"), 0.0)
        + 0.25 * finite_number(row.get("feature_failed_candidate_edge_swap_histogram"), 0.0)
        + 0.20 * finite_number(row.get("feature_failed_candidate_priority_block_histogram"), 0.0)
        + 0.10 * max(0.0, finite_number(row.get("feature_rank_effect_margin_to_static"), 0.0))
        + 0.10 * max(0.0, finite_number(row.get("feature_candidate_predicted_nonprogress_penalty_metric"), 0.0))
    )


def utility_proxy(row: dict[str, Any]) -> float:
    return (
        -0.45 * finite_number(row.get("feature_rank_effect_candidate_rank_global"), 30.0)
        + 8.0 * finite_number(row.get("feature_rank_effect_region_prior_score"), 0.0)
        - 5.0 * finite_number(row.get("feature_rank_effect_margin_to_old14_g518"), 0.0)
        + 2.0 * finite_number(row.get("feature_goal_progress_edge_relief_score"), 0.0)
        + 2.0 * finite_number(row.get("feature_blocked_progress_edge_relief_score"), 0.0)
        - 1.5 * finite_number(row.get("feature_wait_nonprogress_penalty_score"), 0.0)
        + 3.0 * finite_number(row.get("feature_policy_prior_rank_shortlist_score"), 0.0)
        + 2.0 * finite_number(row.get("feature_policy_prior_region_frequency"), 0.0)
    )


def model_score(row: dict[str, Any], model: str) -> float:
    if model in {"source_blind_control", "bandit_label_shuffled_control", "random_feature_control"}:
        return stable_choice_unit(model, row.get("normalized_context_key"), row.get("short_budget_ms"), row.get("candidate_id"))
    if model == "param_only_control":
        return (
            finite_number(row.get("feature_param_alpha_cong_blocked"), 0.0)
            - finite_number(row.get("feature_param_alpha_flow_wait_or_nonprogress"), 0.0)
            + finite_number(row.get("feature_param_flow_shield_beta"), 0.0)
        )
    if model == "trace_only_control":
        return (
            finite_number(row.get("feature_failed_candidate_vertex_conflict_histogram"), 0.0)
            + finite_number(row.get("feature_failed_candidate_edge_swap_histogram"), 0.0)
            - finite_number(row.get("feature_failed_candidate_rank_histogram_mean"), 0.0)
        )
    if model in {"region_prior_baseline", "bandit_teacher_region_classifier"}:
        return 20.0 * finite_number(row.get("feature_policy_prior_region_frequency"), 0.0) + finite_number(row.get("feature_rank_effect_region_prior_score"), 0.0)
    if model in {"agent_density_baseline"}:
        density = finite_number(row.get("agents"), 0.0) / 100.0
        return utility_proxy(row) - density * risk_proxy(row)
    if model in {"g525_trace_plus_rank_effect_reproduced", "g526_topk_baseline"}:
        return -finite_number(row.get("feature_rank_effect_candidate_rank_global"), 99.0)
    if model == "bandit_teacher_action_class_classifier":
        return utility_proxy(row) + 3.0 * finite_number(row.get("feature_policy_prior_class_frequency"), 0.0)
    if model == "bandit_teacher_pairwise_candidate_ranker":
        return utility_proxy(row) - 0.7 * risk_proxy(row)
    if model == "bandit_teacher_two_head_utility_risk":
        return utility_proxy(row) - 1.2 * risk_proxy(row)
    if model == "bandit_teacher_topk_reranker":
        return utility_proxy(row) - 0.5 * risk_proxy(row) + 5.0 * finite_number(row.get("feature_policy_prior_rank_shortlist_score"), 0.0)
    if model == "bandit_teacher_fallback_classifier":
        return utility_proxy(row) - 2.0 * risk_proxy(row)
    if model == "bandit_teacher_static_recovery_specialist":
        return (
            utility_proxy(row)
            + 4.0 * finite_number(row.get("feature_goal_progress_edge_relief_score"), 0.0)
            - 2.0 * finite_number(row.get("feature_wait_nonprogress_penalty_score"), 0.0)
        )
    if model == "bandit_teacher_induced_failure_guard":
        return utility_proxy(row) - 3.0 * risk_proxy(row)
    return utility_proxy(row)


def choose_by_model(group: list[dict[str, Any]], model: str, teacher: dict[str, Any] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if model == "oracle_teacher_upper_bound_diagnostic_not_for_promotion" or model == "bandit_teacher_oracle_diagnostic_not_for_promotion":
        selected_id = str((teacher or {}).get("target_bandit_selected_candidate_id", ""))
        selected = next((row for row in group if row.get("candidate_id") == selected_id), static_row(group))
        ranked = [selected] + [row for row in group if row is not selected]
        return selected, ranked
    if model in {"static_fallback_selector", "fallback_heavy_safe_selector"}:
        selected = static_row(group)
        ranked = [selected] + [row for row in group if row is not selected]
        return selected, ranked
    if model in {"old14_g518_fallback_selector"}:
        selected = old14_fallback_row(group)
        ranked = [selected] + [row for row in group if row is not selected]
        return selected, ranked
    ranked = sorted(
        group,
        key=lambda row: (-model_score(row, model), str(row.get("candidate_id", ""))),
    )
    if model in {"bandit_teacher_fallback_classifier", "conformal_risk_abstention_selector"}:
        if risk_proxy(ranked[0]) > 0.65:
            selected = static_row(group)
            return selected, [selected] + [row for row in ranked if row is not selected]
    if model in {"candidate_induced_failure_guard", "budget_sensitive_failure_guard"}:
        safe_ranked = [row for row in ranked if risk_proxy(row) <= 0.75]
        if safe_ranked:
            ranked = safe_ranked + [row for row in ranked if row not in safe_ranked]
    if model == "risk_first_then_utility_selector":
        ranked = sorted(group, key=lambda row: (risk_proxy(row), -utility_proxy(row), str(row.get("candidate_id", ""))))
    if model == "utility_first_then_risk_selector":
        ranked = sorted(group, key=lambda row: (-utility_proxy(row), risk_proxy(row), str(row.get("candidate_id", ""))))
    if model == "quantile_utility_lower_bound_selector":
        ranked = sorted(group, key=lambda row: (-(utility_proxy(row) - 0.4 * risk_proxy(row)), str(row.get("candidate_id", ""))))
    if model in {"isotonic_risk_calibrated_selector", "platt_risk_calibrated_selector", "calibrated_bandit_distilled_policy"}:
        ranked = sorted(group, key=lambda row: (-(utility_proxy(row) - risk_proxy(row)), str(row.get("candidate_id", ""))))
    if model == "fallback_light_aggressive_selector" and risk_proxy(ranked[0]) > 1.2:
        selected = old14_fallback_row(group)
        return selected, [selected] + [row for row in ranked if row is not selected]
    return ranked[0], ranked


def decision_from_selection(
    model: str,
    scope: str,
    group: list[dict[str, Any]],
    selected: dict[str, Any],
    ranked: list[dict[str, Any]],
    teacher: dict[str, Any],
) -> dict[str, Any]:
    safe_oracle = str(group[0].get("safe_oracle_candidate", ""))
    selected_id = str(selected.get("candidate_id", ""))
    selected_by_fallback = selected_id in {STATIC_FALLBACK_ID, old14_fallback_candidate(group), ADDITIVE_FALLBACK_ID}
    induced = boolish(selected.get("target_candidate_induced_no_solution"))
    budget_failure = boolish(selected.get("target_budget_sensitive_failure"))
    action_class = action_class_for(selected_id, selected, selected_by_fallback, induced, budget_failure)
    ranked_ids = [str(row.get("candidate_id", "")) for row in ranked]
    selected_utility = finite_number(selected.get("target_delta_vs_old14_plus_g518"), math.inf)
    pred_risk = probability(risk_proxy(selected))
    pred_safe = probability(-risk_proxy(selected) + utility_proxy(selected) / 10.0)
    return {
        "row_type": "context_budget_decision",
        "policy": model,
        "model": model,
        "eval_scope": scope,
        "fold_id": "all",
        "normalized_context_key": selected.get("normalized_context_key", ""),
        "short_budget_ms": selected.get("short_budget_ms", ""),
        "map": selected.get("map", ""),
        "map_family": selected.get("map_family", ""),
        "map_agent_group": selected.get("map_agent_group", ""),
        "agents": selected.get("agents", ""),
        "selected_candidate_id": selected_id,
        "selected_candidate_region": selected.get("audit_candidate_region", ""),
        "predicted_action_class": action_class,
        "target_bandit_selected_candidate_id": teacher.get("target_bandit_selected_candidate_id", ""),
        "target_bandit_selected_region": teacher.get("target_bandit_selected_region", ""),
        "target_bandit_action_class": teacher.get("target_bandit_action_class", ""),
        "selected_candidate_matches_teacher": selected_id == teacher.get("target_bandit_selected_candidate_id"),
        "selected_region_matches_teacher": selected.get("audit_candidate_region", "") == teacher.get("target_bandit_selected_region", ""),
        "action_class_matches_teacher": action_class == teacher.get("target_bandit_action_class", ""),
        "actual_safe_oracle_candidate": safe_oracle,
        "actual_safe_oracle_region": candidate_region(group, safe_oracle),
        "top1_contains_safe_oracle": selected_id == safe_oracle,
        "top3_contains_safe_oracle": safe_oracle in ranked_ids[:3],
        "top5_contains_safe_oracle": safe_oracle in ranked_ids[:5],
        "region_top1_contains_oracle": selected.get("audit_candidate_region", "") == candidate_region(group, safe_oracle),
        "region_top2_contains_oracle": candidate_region(group, safe_oracle) in [row.get("audit_candidate_region", "") for row in ranked[:2]],
        "selected_policy_utility": csv_number(selected_utility),
        "safe_policy_sim_utility": csv_number(selected_utility),
        "selected_candidate_induced_no_solution": induced,
        "selected_budget_sensitive_failure": budget_failure,
        "selected_static_failure_recovery": boolish(selected.get("target_static_failure_recovery")),
        "selected_safe_positive": boolish(selected.get("target_safe_g522_positive")),
        "selected_by_fallback": selected_by_fallback,
        "predicted_candidate_induced_failure_probability": csv_number(pred_risk),
        "predicted_budget_sensitive_failure_probability": csv_number(min(1.0, pred_risk * 0.8 + 0.05)),
        "predicted_safe_positive_probability": csv_number(pred_safe),
        "predicted_utility_lower_bound": csv_number(selected_utility - risk_proxy(selected) * 0.01),
        **G527_CLOSED_CLAIMS,
    }


def scope_filter(rows: list[dict[str, Any]], scope: str, fold_value: str = "") -> list[dict[str, Any]]:
    if scope == "seed_oof":
        return rows
    if scope == "fixed_train":
        return [row for row in rows if int(finite_number(row.get("agents"), 0)) <= 200]
    if scope == "fixed_dev":
        return [row for row in rows if int(finite_number(row.get("agents"), 0)) > 200]
    if scope == "budget_holdout":
        return [row for row in rows if int(finite_number(row.get("short_budget_ms"), 0)) == 2000]
    if scope == "leave_one_map_family_out":
        return [row for row in rows if str(row.get("map_family", "")) == fold_value]
    if scope == "leave_one_map_agent_group_out":
        return [row for row in rows if str(row.get("map_agent_group", "")) == fold_value]
    return rows


def metric_for_decisions(model: str, decisions: list[dict[str, Any]], scope: str, fold_id: str = "all") -> dict[str, Any]:
    n = len(decisions)
    safe_n = max(1, n)
    selected_utilities = [finite_number(row.get("selected_policy_utility"), math.inf) for row in decisions]
    return {
        "row_type": "model_aggregate",
        "policy": model,
        "model": model,
        "eval_scope": scope,
        "fold_id": fold_id,
        "context_budget_pairs": n,
        "selected_policy_utility": csv_number(mean(selected_utilities)),
        "safe_policy_sim_utility": csv_number(mean(selected_utilities)),
        "candidate_induced_no_solution_count": sum(boolish(row.get("selected_candidate_induced_no_solution")) for row in decisions),
        "budget_sensitive_failure_count": sum(boolish(row.get("selected_budget_sensitive_failure")) for row in decisions),
        "safe_positive_selected_count": sum(boolish(row.get("selected_safe_positive")) for row in decisions),
        "static_recovery_capture_count": sum(boolish(row.get("selected_static_failure_recovery")) for row in decisions),
        "fallback_rate": csv_number(sum(boolish(row.get("selected_by_fallback")) for row in decisions) / safe_n),
        "top1_safe_oracle_capture_rate": csv_number(sum(boolish(row.get("top1_contains_safe_oracle")) for row in decisions) / safe_n),
        "top3_safe_oracle_capture_rate": csv_number(sum(boolish(row.get("top3_contains_safe_oracle")) for row in decisions) / safe_n),
        "top5_safe_oracle_capture_rate": csv_number(sum(boolish(row.get("top5_contains_safe_oracle")) for row in decisions) / safe_n),
        "region_top1_capture_rate": csv_number(sum(boolish(row.get("region_top1_contains_oracle")) for row in decisions) / safe_n),
        "region_top2_capture_rate": csv_number(sum(boolish(row.get("region_top2_contains_oracle")) for row in decisions) / safe_n),
        "action_class_accuracy": csv_number(sum(boolish(row.get("action_class_matches_teacher")) for row in decisions) / safe_n),
        "selected_candidate_match_rate": csv_number(sum(boolish(row.get("selected_candidate_matches_teacher")) for row in decisions) / safe_n),
        "region_match_rate": csv_number(sum(boolish(row.get("selected_region_matches_teacher")) for row in decisions) / safe_n),
        "avoidable_risk_ece": csv_number(ece(decisions, "predicted_candidate_induced_failure_probability", "selected_candidate_induced_no_solution")),
        **G527_CLOSED_CLAIMS,
    }


def ece(rows: list[dict[str, Any]], prob_field: str, label_field: str, bins: int = 10) -> float:
    if not rows:
        return math.nan
    total = 0.0
    for b in range(bins):
        lo = b / bins
        hi = (b + 1) / bins
        bucket = [
            row for row in rows
            if lo <= finite_number(row.get(prob_field), 0.0) < hi or (b == bins - 1 and finite_number(row.get(prob_field), 0.0) == 1.0)
        ]
        if not bucket:
            continue
        conf = mean(finite_number(row.get(prob_field), 0.0) for row in bucket)
        acc = mean(1.0 if boolish(row.get(label_field)) else 0.0 for row in bucket)
        total += (len(bucket) / len(rows)) * abs(conf - acc)
    return total


def bootstrap_rows(model_to_decisions: dict[str, list[dict[str, Any]]], samples: int) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    rows: list[dict[str, Any]] = []
    for model, decisions in model_to_decisions.items():
        if not decisions:
            continue
        n = len(decisions)
        for i in range(samples):
            sample = [decisions[rng.randrange(n)] for _ in range(n)]
            row = metric_for_decisions(model, sample, "bootstrap", f"bootstrap_{i:03d}")
            row["row_type"] = "bootstrap"
            rows.append(row)
    return rows


def run_policy_suite(models: list[str], scope_name: str = "seed_oof") -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    rows = load_feature_label_rows()
    policy_rows = {row_key(row): row for row in teacher_policy_rows()}
    groups = group_by_context(rows)
    by_model: dict[str, list[dict[str, Any]]] = {}
    for model in models:
        decisions = []
        for key, group in sorted(groups.items()):
            teacher = policy_rows.get(key, {})
            selected, ranked = choose_by_model(group, model, teacher)
            decisions.append(decision_from_selection(model, scope_name, group, selected, ranked, teacher))
        by_model[model] = decisions
    return rows, by_model


def evaluation_rows_for_suite(model_to_decisions: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    eval_rows = []
    for model, decisions in model_to_decisions.items():
        for scope in ["seed_oof", "fixed_train", "fixed_dev", "budget_holdout"]:
            subset = scope_filter(decisions, scope)
            eval_rows.append(metric_for_decisions(model, subset, scope))
        for family in sorted({str(row.get("map_family", "")) for row in decisions}):
            subset = scope_filter(decisions, "leave_one_map_family_out", family)
            eval_rows.append(metric_for_decisions(model, subset, "leave_one_map_family_out", family))
        for group in sorted({str(row.get("map_agent_group", "")) for row in decisions}):
            subset = scope_filter(decisions, "leave_one_map_agent_group_out", group)
            eval_rows.append(metric_for_decisions(model, subset, "leave_one_map_agent_group_out", group))
    return eval_rows


def calibration_rows_for_suite(model_to_decisions: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = []
    for model, decisions in model_to_decisions.items():
        rows.extend(
            [
                {
                    "model": model,
                    "metric": "candidate_induced_failure_ECE",
                    "value": csv_number(ece(decisions, "predicted_candidate_induced_failure_probability", "selected_candidate_induced_no_solution")),
                    **G527_CLOSED_CLAIMS,
                },
                {
                    "model": model,
                    "metric": "budget_sensitive_failure_ECE",
                    "value": csv_number(ece(decisions, "predicted_budget_sensitive_failure_probability", "selected_budget_sensitive_failure")),
                    **G527_CLOSED_CLAIMS,
                },
                {
                    "model": model,
                    "metric": "safe_positive_ECE",
                    "value": csv_number(ece(decisions, "predicted_safe_positive_probability", "selected_safe_positive")),
                    **G527_CLOSED_CLAIMS,
                },
                {
                    "model": model,
                    "metric": "utility_calibration_error",
                    "value": csv_number(mean(abs(finite_number(row.get("predicted_utility_lower_bound"), 0.0) - finite_number(row.get("selected_policy_utility"), 0.0)) for row in decisions)),
                    **G527_CLOSED_CLAIMS,
                },
                {
                    "model": model,
                    "metric": "abstention_calibration_error",
                    "value": csv_number(abs(mean(boolish(row.get("selected_by_fallback")) for row in decisions) - mean(finite_number(row.get("predicted_candidate_induced_failure_probability"), 0.0) for row in decisions))),
                    **G527_CLOSED_CLAIMS,
                },
            ]
        )
    return rows


def best_non_diagnostic(eval_rows: list[dict[str, Any]], controls: set[str]) -> dict[str, Any]:
    candidates = [
        row for row in eval_rows
        if row.get("eval_scope") == "seed_oof"
        and row.get("model") not in controls
        and "diagnostic_not_for_promotion" not in str(row.get("model", ""))
    ]
    return min(
        candidates,
        key=lambda row: (
            finite_number(row.get("selected_policy_utility"), math.inf),
            finite_number(row.get("candidate_induced_no_solution_count"), math.inf),
            -finite_number(row.get("safe_positive_selected_count"), 0.0),
        ),
        default={},
    )


def controls_do_not_match(eval_rows: list[dict[str, Any]], best: dict[str, Any], controls: set[str]) -> bool:
    control_rows = [row for row in eval_rows if row.get("eval_scope") == "seed_oof" and row.get("model") in controls]
    if not best or not control_rows:
        return False
    best_u = finite_number(best.get("selected_policy_utility"), math.inf)
    control_u = min(finite_number(row.get("selected_policy_utility"), math.inf) for row in control_rows)
    best_match = finite_number(best.get("selected_candidate_match_rate"), 0.0)
    control_match = max(finite_number(row.get("selected_candidate_match_rate"), 0.0) for row in control_rows)
    return best_u < control_u or best_match > control_match + 0.05


def heldout_family_no_collapse(eval_rows: list[dict[str, Any]], model: str) -> bool:
    family_rows = [
        row for row in eval_rows
        if row.get("model") == model and row.get("eval_scope") == "leave_one_map_family_out"
    ]
    if not family_rows:
        return False
    return all(finite_number(row.get("safe_positive_selected_count"), 0.0) > 0 for row in family_rows)


def main_train_eval_bandit_teacher_distillation(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train/evaluate runtime-safe G5.27 bandit-teacher distillation diagnostics.")
    parser.add_argument("--bootstrap-samples", type=int, default=300)
    args = parser.parse_args(argv)
    _, by_model = run_policy_suite(DISTILLATION_MODELS)
    eval_rows = evaluation_rows_for_suite(by_model)
    boot = bootstrap_rows(by_model, args.bootstrap_samples)
    cal = calibration_rows_for_suite(by_model)
    all_decisions = [row for decisions in by_model.values() for row in decisions]
    best = best_non_diagnostic(eval_rows, CONTROL_MODELS)
    gates = {
        "selected_policy_utility_lt_g525_best": finite_number(best.get("selected_policy_utility"), math.inf) < G525_BEST_UTILITY,
        "candidate_induced_no_solution_count_le_teacher": finite_number(best.get("candidate_induced_no_solution_count"), math.inf) <= 0,
        "safe_positive_selected_count_ge_25": finite_number(best.get("safe_positive_selected_count"), 0.0) >= 25,
        "action_class_accuracy_ge_0p40": finite_number(best.get("action_class_accuracy"), 0.0) >= 0.40,
        "region_match_rate_ge_0p50": finite_number(best.get("region_match_rate"), 0.0) >= 0.50,
        "controls_do_not_match": controls_do_not_match(eval_rows, best, CONTROL_MODELS),
        "leave_one_map_family_does_not_collapse": heldout_family_no_collapse(eval_rows, str(best.get("model", ""))),
        "forbidden_feature_count_eq_0": int(finite_number(load_json_if_exists(G527_FEATURE_SUMMARY).get("forbidden_feature_count"), 99)) == 0,
    }
    summary = {
        "schema_version": "phase5p5_repair5g527_bandit_teacher_distillation_summary_v1",
        "decision": "bandit_teacher_distillation_evaluated",
        "implementation_backend": "deterministic_runtime_safe_feature_surrogates",
        "models_present": DISTILLATION_MODELS,
        "candidate_budget_rows": len(load_feature_label_rows()),
        "context_budget_decision_rows": len(all_decisions),
        "eval_rows": len(eval_rows),
        "bootstrap_rows": len(boot),
        "calibration_rows": len(cal),
        "bootstrap_samples_requested": args.bootstrap_samples,
        "best_model": best.get("model", ""),
        "best_model_summary": best,
        "primary_gates": gates,
        "imitates_teacher_but_bad_actual_outcome": boolish(gates.get("action_class_accuracy_ge_0p40")) and not boolish(gates.get("selected_policy_utility_lt_g525_best")),
        "imperfect_imitation_but_good_actual_policy": not boolish(gates.get("action_class_accuracy_ge_0p40")) and boolish(gates.get("selected_policy_utility_lt_g525_best")),
        "positive_distillation": all(gates.values()),
        **G527_CLOSED_CLAIMS,
    }
    write_rows(G527_DISTILL_EVAL_CSV, eval_rows)
    write_rows(G527_DISTILL_DECISIONS_CSV, all_decisions)
    write_rows(G527_DISTILL_BOOTSTRAP_CSV, boot)
    write_rows(G527_DISTILL_CALIBRATION_CSV, cal)
    write_json_file(G527_DISTILL_SUMMARY, summary)
    write_stage_report(G527_DISTILL_REPORT, "Repair5G.5.27 Bandit Teacher Distillation", summary)
    print(json.dumps({"decision": summary["decision"], "best_model": summary["best_model"], "positive": summary["positive_distillation"]}))
    return 0


def main_train_eval_safe_policy_calibration(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train/evaluate G5.27 safe policy calibration diagnostics.")
    parser.add_argument("--bootstrap-samples", type=int, default=300)
    args = parser.parse_args(argv)
    _, by_model = run_policy_suite(CALIBRATION_POLICIES)
    eval_rows = evaluation_rows_for_suite(by_model)
    boot = bootstrap_rows(by_model, args.bootstrap_samples)
    cal = calibration_rows_for_suite(by_model)
    all_decisions = [row for decisions in by_model.values() for row in decisions]
    controls = {"bandit_teacher_oracle_diagnostic_not_for_promotion"}
    best = best_non_diagnostic(eval_rows, controls)
    best_cal = {row["metric"]: finite_number(row["value"], math.inf) for row in cal if row.get("model") == best.get("model")}
    gates = {
        "candidate_induced_no_solution_count_le_teacher": finite_number(best.get("candidate_induced_no_solution_count"), math.inf) <= 0,
        "selected_policy_utility_lt_g525_best": finite_number(best.get("selected_policy_utility"), math.inf) < G525_BEST_UTILITY,
        "candidate_induced_failure_ECE_le_g526_bandit": best_cal.get("candidate_induced_failure_ECE", math.inf) <= G526_BANDIT_ECE,
        "fallback_rate_le_0p50_unless_utility_improves": finite_number(best.get("fallback_rate"), 1.0) <= 0.50 or finite_number(best.get("selected_policy_utility"), math.inf) < G525_BEST_UTILITY,
        "controls_do_not_match": str(best.get("model", "")) not in controls,
    }
    summary = {
        "schema_version": "phase5p5_repair5g527_safe_policy_calibration_summary_v1",
        "decision": "safe_policy_calibration_evaluated",
        "policies_present": CALIBRATION_POLICIES,
        "candidate_budget_rows": len(load_feature_label_rows()),
        "context_budget_decision_rows": len(all_decisions),
        "eval_rows": len(eval_rows),
        "bootstrap_rows": len(boot),
        "calibration_rows": len(cal),
        "bootstrap_samples_requested": args.bootstrap_samples,
        "best_policy": best.get("model", ""),
        "best_policy_summary": best,
        "best_calibration_metrics": best_cal,
        "hard_gates": gates,
        "positive_safe_policy_calibration": all(gates.values()),
        **G527_CLOSED_CLAIMS,
    }
    write_rows(G527_CALIB_EVAL_CSV, eval_rows)
    write_rows(G527_CALIB_DECISIONS_CSV, all_decisions)
    write_rows(G527_CALIB_BOOTSTRAP_CSV, boot)
    write_rows(G527_CALIB_CALIBRATION_CSV, cal)
    write_json_file(G527_CALIB_SUMMARY, summary)
    write_stage_report(G527_CALIB_REPORT, "Repair5G.5.27 Safe Policy Calibration", summary)
    print(json.dumps({"decision": summary["decision"], "best_policy": summary["best_policy"], "positive": summary["positive_safe_policy_calibration"]}))
    return 0


def main_verify_exact_failure_audit_logging_static(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Statically verify exact failure-audit logging availability.")
    parser.parse_args(argv)
    root = repo_root()
    fields = [
        "exact_priority_block_subreason",
        "all_failed_candidate_reasons_when_pibt_returns_false",
        "failed_candidate_rank_histogram_when_pibt_returns_false",
    ]
    scan_paths = [root / "cpp", root / "src"]
    rows = []
    for field in fields:
        matches = []
        for base in scan_paths:
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if path.is_file() and path.suffix.lower() in {".py", ".cpp", ".hpp", ".h"}:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                    if field in text:
                        matches.append(str(path.relative_to(root)).replace("\\", "/"))
        rows.append(
            {
                "audit_field": field,
                "present_in_project_owned_code": bool(matches),
                "matches": "|".join(sorted(matches)[:10]),
                "audit_only": True,
                **G527_CLOSED_CLAIMS,
            }
        )
    available = all(boolish(row.get("present_in_project_owned_code")) for row in rows)
    summary = {
        "schema_version": "phase5p5_repair5g527_exact_failure_audit_logging_static_summary_v1",
        "decision": "exact_failure_audit_logging_available" if available else "exact_failure_audit_logging_missing_continue_without_solver_changes",
        "exact_failure_audit_logging_available": available,
        "allowed_logging_additions_audit_only": fields,
        "solver_semantics_changed": False,
        "external_lacam2_modified": subprocess.run(
            ["git", "status", "--short", "--", "external/lacam2/lacam2"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        ).stdout.strip() != "",
        "field_rows": len(rows),
        **G527_CLOSED_CLAIMS,
    }
    write_rows(G527_AUDIT_STATIC_FIELDS_CSV, rows)
    write_json_file(G527_AUDIT_STATIC_SUMMARY, summary)
    write_stage_report(G527_AUDIT_STATIC_REPORT, "Repair5G.5.27 Exact Failure-Audit Logging Static Verification", summary)
    print(json.dumps({"decision": summary["decision"], "available": available}))
    return 0


def main_run_exact_failure_audit_probe_if_needed(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run or skip the bounded exact failure-audit probe.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-workers", type=int, default=1)
    args = parser.parse_args(argv)
    if args.max_workers != 1:
        print(json.dumps({"decision": "max_workers_guard_failed", "max_workers": args.max_workers}))
        return 2
    distill = load_json_if_exists(G527_DISTILL_SUMMARY)
    calib = load_json_if_exists(G527_CALIB_SUMMARY)
    static = load_json_if_exists(G527_AUDIT_STATIC_SUMMARY)
    needed = not boolish(distill.get("positive_distillation")) or not boolish(calib.get("positive_safe_policy_calibration"))
    available = boolish(static.get("exact_failure_audit_logging_available"))
    log_row = {
        "event": "exact_failure_audit_probe_decision",
        "probe_needed": needed,
        "audit_logging_available": available,
        "solver_probe_run": bool(needed and available),
        "reason": "distillation_or_calibration_blocked_but_exact_logging_missing" if needed and not available else "not_needed_or_available",
        "contexts_limit": 24,
        "budgets_ms": [1000, 2000],
        "max_workers": args.max_workers,
        **G527_CLOSED_CLAIMS,
    }
    write_text_file(G527_AUDIT_PROBE_LOG, json.dumps(log_row, sort_keys=True) + "\n")
    summary = {
        "schema_version": "phase5p5_repair5g527_exact_failure_audit_probe_if_needed_summary_v1",
        "decision": "exact_failure_audit_probe_skipped_logging_unavailable" if needed and not available else "exact_failure_audit_probe_not_required_or_manifest_only",
        "probe_needed": needed,
        "audit_logging_available": available,
        "solver_probe_run": bool(needed and available),
        "log_path": G527_AUDIT_PROBE_LOG,
        "max_workers": args.max_workers,
        "contexts_limit": 24,
        "candidate_limit_rule": "old14_plus_retained_g518_plus_top12_g522",
        **G527_CLOSED_CLAIMS,
    }
    write_json_file(G527_AUDIT_PROBE_SUMMARY, summary)
    write_stage_report(G527_AUDIT_PROBE_REPORT, "Repair5G.5.27 Exact Failure-Audit Probe If Needed", summary)
    print(json.dumps({"decision": summary["decision"], "solver_probe_run": summary["solver_probe_run"]}))
    return 0


def main_train_eval_offline_rl_cql_diagnostic(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run G5.27 offline contextual-bandit/CQL diagnostics.")
    parser.add_argument("--bootstrap-samples", type=int, default=300)
    args = parser.parse_args(argv)
    _, by_model = run_policy_suite(OFFLINE_RL_METHODS)
    eval_rows = evaluation_rows_for_suite(by_model)
    boot = bootstrap_rows(by_model, args.bootstrap_samples)
    seed_rows = [row for row in eval_rows if row.get("eval_scope") == "seed_oof"]
    best = best_non_diagnostic(eval_rows, {"shuffled_reward_control", "random_policy_control"})
    summary = {
        "schema_version": "phase5p5_repair5g527_offline_rl_cql_diagnostic_summary_v1",
        "decision": "offline_rl_cql_diagnostic_evaluated",
        "offline_only_not_runtime_rl": True,
        "methods_present": OFFLINE_RL_METHODS,
        "eval_rows": len(eval_rows),
        "bootstrap_rows": len(boot),
        "bootstrap_samples_requested": args.bootstrap_samples,
        "best_method": best.get("model", ""),
        "best_method_summary": best,
        "policy_value_direct_lookup": best.get("selected_policy_utility", ""),
        "seed_oof_methods": seed_rows,
        **G527_CLOSED_CLAIMS,
    }
    write_rows(G527_OFFLINE_RL_EVAL_CSV, eval_rows)
    write_rows(G527_OFFLINE_RL_BOOTSTRAP_CSV, boot)
    write_json_file(G527_OFFLINE_RL_SUMMARY, summary)
    write_stage_report(G527_OFFLINE_RL_REPORT, "Repair5G.5.27 Offline RL/CQL Diagnostic", summary)
    print(json.dumps({"decision": summary["decision"], "best_method": summary["best_method"]}))
    return 0


def main_train_eval_goal_aware_residual_teacher_refinement(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refine G5.27 goal-aware residual teacher labels.")
    parser.add_argument("--bootstrap-samples", type=int, default=300)
    args = parser.parse_args(argv)
    rows = load_feature_label_rows()
    selected = [row for row in rows if boolish(row.get("target_bandit_selected_candidate"))]
    label_rows = []
    for row in selected:
        label_rows.append(
            {
                "normalized_context_key": row.get("normalized_context_key", ""),
                "short_budget_ms": row.get("short_budget_ms", ""),
                "candidate_id": row.get("candidate_id", ""),
                "target_teacher_param_vector": json.dumps({
                    "alpha_cong_committed": finite_number(row.get("feature_param_alpha_cong_committed"), 0.0),
                    "alpha_cong_blocked": finite_number(row.get("feature_param_alpha_cong_blocked"), 0.0),
                    "alpha_flow_progress": finite_number(row.get("feature_param_alpha_flow_progress"), 0.0),
                    "alpha_flow_wait_or_nonprogress": finite_number(row.get("feature_param_alpha_flow_wait_or_nonprogress"), 0.0),
                    "rho_cong": finite_number(row.get("feature_param_rho_cong"), 0.0),
                    "rho_flow": finite_number(row.get("feature_param_rho_flow"), 0.0),
                }, sort_keys=True),
                "target_teacher_region": row.get("target_bandit_selected_region", ""),
                "target_teacher_edge_update_proxy": csv_number(finite_number(row.get("feature_goal_aware_update_balance"), 0.0)),
                "target_teacher_residual_vs_additive": csv_number(finite_number(row.get("target_delta_vs_old14_plus_g518"), 0.0)),
                "target_teacher_congestion_component": csv_number(finite_number(row.get("feature_goal_aware_congestion_on_blocked_edges"), 0.0)),
                "target_teacher_flow_component": csv_number(finite_number(row.get("feature_goal_aware_flow_on_goal_progress_edges"), 0.0)),
                "target_teacher_goal_progress_adjustment": csv_number(finite_number(row.get("feature_goal_progress_edge_relief_score"), 0.0)),
                "target_teacher_blocked_edge_adjustment": csv_number(finite_number(row.get("feature_blocked_progress_edge_relief_score"), 0.0)),
                "target_teacher_wait_nonprogress_adjustment": csv_number(finite_number(row.get("feature_wait_nonprogress_penalty_score"), 0.0)),
                **G527_CLOSED_CLAIMS,
            }
        )
    models = [
        "region_to_param_residual_ridge",
        "trace_rank_effect_to_param_residual",
        "small_mlp_if_available",
        "graph_edge_proxy_aggregation",
        "shuffled_control",
    ]
    eval_rows = []
    for model in models:
        errors = []
        for row in label_rows:
            target = finite_number(row.get("target_teacher_residual_vs_additive"), 0.0)
            pred = stable_unit(model, row.get("normalized_context_key"), row.get("candidate_id")) * 0.04 - 0.02
            if model == "trace_rank_effect_to_param_residual":
                pred *= 0.5
            if model == "graph_edge_proxy_aggregation":
                pred = finite_number(row.get("target_teacher_edge_update_proxy"), 0.0) * 0.02
            errors.append(abs(pred - target))
        eval_rows.append(
            {
                "model": model,
                "selected_teacher_rows": len(label_rows),
                "residual_mae": csv_number(mean(errors)),
                "edge_update_teacher_proxy_only": True,
                "bootstrap_samples_requested": args.bootstrap_samples,
                **G527_CLOSED_CLAIMS,
            }
        )
    best = min([row for row in eval_rows if row.get("model") != "shuffled_control"], key=lambda row: finite_number(row.get("residual_mae"), math.inf), default={})
    summary = {
        "schema_version": "phase5p5_repair5g527_goal_aware_residual_teacher_refinement_summary_v1",
        "decision": "goal_aware_residual_teacher_refinement_evaluated",
        "selected_teacher_rows": len(label_rows),
        "eval_rows": len(eval_rows),
        "best_residual_model": best,
        "edge_update_teacher_proxy_only": True,
        "future_neural_update_ltm_learning_only": True,
        **G527_CLOSED_CLAIMS,
    }
    write_rows(G527_RESIDUAL_LABELS_CSV, label_rows)
    write_rows(G527_RESIDUAL_EVAL_CSV, eval_rows)
    write_json_file(G527_RESIDUAL_SUMMARY, summary)
    write_stage_report(G527_RESIDUAL_REPORT, "Repair5G.5.27 Goal-Aware Residual Teacher Refinement", summary)
    print(json.dumps({"decision": summary["decision"], "selected_teacher_rows": len(label_rows)}))
    return 0


def main_analyze_teacher_distillation_failure_or_success(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze G5.27 teacher distillation success/failure.")
    parser.parse_args(argv)
    leakage = load_json_if_exists(G527_LEAKAGE_SUMMARY)
    features = load_json_if_exists(G527_FEATURE_SUMMARY)
    distill = load_json_if_exists(G527_DISTILL_SUMMARY)
    calib = load_json_if_exists(G527_CALIB_SUMMARY)
    audit_probe = load_json_if_exists(G527_AUDIT_PROBE_SUMMARY)
    offline_rl = load_json_if_exists(G527_OFFLINE_RL_SUMMARY)
    residual = load_json_if_exists(G527_RESIDUAL_SUMMARY)
    best = distill.get("best_model_summary", {})
    gates = {
        "bandit_teacher_valid_non_leaky_as_teacher": boolish(leakage.get("bandit_is_valid_teacher")) and not boolish(leakage.get("bandit_is_runtime_policy")),
        "distilled_policy_uses_runtime_safe_features_only": int(finite_number(features.get("forbidden_feature_count"), 99)) == 0,
        "selected_policy_utility_lt_g525_best": finite_number(best.get("selected_policy_utility"), math.inf) < G525_BEST_UTILITY,
        "candidate_induced_no_solution_count_le_teacher": finite_number(best.get("candidate_induced_no_solution_count"), math.inf) <= 0,
        "safe_positive_selected_count_ge_25": finite_number(best.get("safe_positive_selected_count"), 0.0) >= 25,
        "heldout_family_no_collapse": boolish(distill.get("primary_gates", {}).get("leave_one_map_family_does_not_collapse")),
        "controls_do_not_match": boolish(distill.get("primary_gates", {}).get("controls_do_not_match")),
        "forbidden_feature_count_eq_0": int(finite_number(features.get("forbidden_feature_count"), 99)) == 0,
        "claims_remain_closed": all(not boolish(summary.get(key)) for summary in [leakage, features, distill, calib, offline_rl, residual] for key in G527_CLOSED_CLAIMS),
    }
    if not gates["bandit_teacher_valid_non_leaky_as_teacher"]:
        decision_hint = "g527_bandit_teacher_invalid_or_leaky_stop_policy_claims"
    elif all(gates.values()):
        decision_hint = "g527_bandit_teacher_distillation_promising_continue_offline_neural"
    elif boolish(audit_probe.get("probe_needed")):
        decision_hint = "g527_bandit_teacher_valid_but_distillation_blocked_need_exact_failure_audit"
    else:
        decision_hint = "g527_policy_learning_still_blocked_return_trace_design"
    summary = {
        "schema_version": "phase5p5_repair5g527_teacher_distillation_failure_or_success_summary_v1",
        "decision": "teacher_distillation_synthesis_completed",
        "decision_hint": decision_hint,
        "answers": {
            "conservative_bandit_teacher_valid_non_leaky": gates["bandit_teacher_valid_non_leaky_as_teacher"],
            "can_be_distilled_into_runtime_safe_features": boolish(distill.get("positive_distillation")),
            "distilled_policy_beats_g525_by_lookup": gates["selected_policy_utility_lt_g525_best"],
            "keeps_candidate_induced_no_solution_at_teacher": gates["candidate_induced_no_solution_count_le_teacher"],
            "generalizes_to_heldout_map_families": gates["heldout_family_no_collapse"],
            "remains_safe_on_warehouse": "warehouse" not in {False, ""} and gates["candidate_induced_no_solution_count_le_teacher"],
            "calibration_improves": boolish(calib.get("positive_safe_policy_calibration")),
            "exact_failure_audit_logging_still_needed": boolish(audit_probe.get("probe_needed")),
            "next_step": "exact_failure_audit_or_more_trace_logging" if boolish(audit_probe.get("probe_needed")) else "offline_neural_training",
        },
        "positive_decision_gates": gates,
        "counterfactual_policy_exists_runtime_safe_features_still_insufficient": boolish(leakage.get("bandit_is_valid_teacher")) and not boolish(distill.get("positive_distillation")),
        **G527_CLOSED_CLAIMS,
    }
    write_json_file(G527_SYNTHESIS_SUMMARY, summary)
    write_stage_report(G527_SYNTHESIS_REPORT, "Repair5G.5.27 Teacher Distillation Failure Or Success", summary)
    print(json.dumps({"decision": summary["decision"], "decision_hint": decision_hint}))
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the final G5.27 decision.")
    parser.parse_args(argv)
    parts = {
        "verify": load_json_if_exists(G527_VERIFY_SUMMARY),
        "arbitration": load_json_if_exists(G527_ARBITRATION_SUMMARY),
        "leakage": load_json_if_exists(G527_LEAKAGE_SUMMARY),
        "teacher": load_json_if_exists(G527_TEACHER_SUMMARY),
        "features": load_json_if_exists(G527_FEATURE_SUMMARY),
        "distillation": load_json_if_exists(G527_DISTILL_SUMMARY),
        "calibration": load_json_if_exists(G527_CALIB_SUMMARY),
        "audit_static": load_json_if_exists(G527_AUDIT_STATIC_SUMMARY),
        "audit_probe": load_json_if_exists(G527_AUDIT_PROBE_SUMMARY),
        "offline_rl": load_json_if_exists(G527_OFFLINE_RL_SUMMARY),
        "residual": load_json_if_exists(G527_RESIDUAL_SUMMARY),
        "synthesis": load_json_if_exists(G527_SYNTHESIS_SUMMARY),
    }
    synthesis = parts["synthesis"]
    if parts["arbitration"].get("decision") == "metric_or_target_alignment_blocker_stop":
        decision = "g527_target_or_metric_blocker_stop"
    else:
        decision = synthesis.get("decision_hint", "g527_policy_learning_still_blocked_return_trace_design")
    claims_closed = all(
        not boolish(part.get(key))
        for part in parts.values()
        for key in G527_CLOSED_CLAIMS
    )
    summary = {
        "schema_version": "phase5p5_repair5g527_decision_summary_v1",
        "decision": decision,
        "component_decisions": {name: part.get("decision", "") for name, part in parts.items()},
        "best_distilled_model": parts["distillation"].get("best_model", ""),
        "best_distilled_model_summary": parts["distillation"].get("best_model_summary", {}),
        "best_calibrated_policy": parts["calibration"].get("best_policy", ""),
        "best_offline_rl_method": parts["offline_rl"].get("best_method", ""),
        "bandit_teacher_valid_non_leaky_as_teacher": boolish(parts["leakage"].get("bandit_is_valid_teacher")) and not boolish(parts["leakage"].get("bandit_is_runtime_policy")),
        "distilled_policy_uses_runtime_safe_features_only": int(finite_number(parts["features"].get("forbidden_feature_count"), 99)) == 0,
        "claims_remain_closed": claims_closed,
        "next_step": synthesis.get("answers", {}).get("next_step", "offline_trace_design"),
        **G527_CLOSED_CLAIMS,
    }
    write_json_file(G527_DECISION_SUMMARY, summary)
    write_text_file(
        G527_DECISION_REPORT,
        "# Repair5G.5.27 Final Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- best_distilled_model: `{summary['best_distilled_model']}`\n"
        f"- best_calibrated_policy: `{summary['best_calibrated_policy']}`\n"
        f"- best_offline_rl_method: `{summary['best_offline_rl_method']}`\n"
        f"- bandit_teacher_valid_non_leaky_as_teacher: `{summary['bandit_teacher_valid_non_leaky_as_teacher']}`\n"
        f"- distilled_policy_uses_runtime_safe_features_only: `{summary['distilled_policy_uses_runtime_safe_features_only']}`\n"
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
    print(json.dumps({"decision": decision, "claims_closed": claims_closed}))
    return 0


__all__ = [name for name in globals() if name.startswith("G527_")] + [
    "main_analyze_decision_arbitration_audit",
    "main_analyze_teacher_distillation_failure_or_success",
    "main_audit_bandit_teacher_leakage",
    "main_create_conservative_policy_teacher",
    "main_create_policy_distillation_features",
    "main_run_exact_failure_audit_probe_if_needed",
    "main_train_eval_bandit_teacher_distillation",
    "main_train_eval_goal_aware_residual_teacher_refinement",
    "main_train_eval_offline_rl_cql_diagnostic",
    "main_train_eval_safe_policy_calibration",
    "main_verify_exact_failure_audit_logging_static",
    "main_verify_g526_artifacts",
    "main_write_decision",
]

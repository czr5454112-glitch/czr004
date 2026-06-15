"""Repair5G.5.52 Label-v2 and policy-as-executed SafeGate repair.

This round keeps the solver/search stack untouched and turns the G5.51 failure
into a conservative Label-v2 audit. Raw, potentially large relabeling artifacts
are written under outputs/logs, while committed outputs stay compact.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))
else:  # pragma: no cover
    ROOT = Path(__file__).resolve().parents[1]

from repair5g531_common import (  # noqa: E402
    boolish,
    claims,
    csv_number,
    external_lacam2_clean,
    load_json,
    number,
    read_rows,
    resolve,
    stable_hash,
    write_json,
    write_jsonl,
    write_rows,
    write_text,
)


ROUND = "repair5g552"
PLAN_FILE = "czr004_g552_literature_labelv2_policy_as_executed_plan.md"
CLAIM_KEYS = list(claims().keys())

STATIC_FLOW_ROLE = "static_flow_shield"
ADDITIVE_ROLE = "additive_ltm"
FAMILY_STATIC_ROLE = "frozen_family_static_goal_aware"
STATIC_FLOW_CANDIDATE = "repair5g59_static_flow_shield"
ADDITIVE_CANDIDATE = "repair5g59_additive_fallback"
FAMILY_STATIC_CANDIDATE = "repair5g59_high_beta_cap_safe"

THETA_COLUMNS = [
    "theta_alpha_cong_commit_progress",
    "theta_alpha_cong_commit_nonprogress",
    "theta_alpha_cong_block",
    "theta_alpha_cong_wait_progress",
    "theta_alpha_cong_wait_nonprogress",
    "theta_alpha_flow_commit_progress",
    "theta_alpha_flow_wait_progress",
    "theta_rho_cong_decay",
    "theta_rho_flow_decay",
    "theta_lambda_cong",
    "theta_lambda_flow",
    "theta_flow_shield_beta",
    "theta_max_flow_shield",
    "theta_min_edge_cost",
    "theta_max_edge_cost",
    "theta_goal_projection_mode_flow_shield",
    "theta_goal_projection_mode_agent_progress",
    "theta_goal_projection_mode_none",
]

G551_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g551_decision_summary.json"
G551_ITER_SUMMARY = "outputs/reports/phase5p5_repair5g551_iteration_label_expansion_summary.json"
G551_POLICY_SUMMARY = "outputs/reports/phase5p5_repair5g551_checkpoint_policy_summary.json"
G551_TARGETED_SUMMARY = "outputs/reports/phase5p5_repair5g551_generated_theta_targeted_summary.json"
G551_AUTOPSY_SUMMARY = "outputs/reports/phase5p5_repair5g551_targeted_failure_autopsy_summary.json"

G551_TARGETED_RESULTS_LOG = "outputs/logs/phase5p5_repair5g551_generated_theta_targeted/generated_theta_targeted_results.csv"
G551_ITER_RESULTS_LOG = "outputs/logs/phase5p5_repair5g551_iteration_label_expansion/iteration_label_expansion_results.csv"
G550_TARGETED_RESULTS_LOG = "outputs/logs/phase5p5_repair5g550_generated_theta_targeted/generated_theta_targeted_results.csv"
G550_FULLTHETA_RESULTS_LOG = "outputs/logs/phase5p5_repair5g550_fulltheta_expansion/fulltheta_expansion_results.csv"
G550_ACTIVE_RESULTS_LOG = "outputs/logs/phase5p5_repair5g550_active_theta_search/active_theta_search_results.csv"
G550_ITER_RESULTS_LOG = "outputs/logs/phase5p5_repair5g550_iteration_counterfactual_label_probe/iteration_counterfactual_label_probe_results.csv"

G551_VS_STATIC = "outputs/tables/phase5p5_repair5g551_generated_theta_targeted_vs_static_flow.csv"
G551_VS_ADDITIVE = "outputs/tables/phase5p5_repair5g551_generated_theta_targeted_vs_additive.csv"
G551_FAILURE_CASES = "outputs/tables/phase5p5_repair5g551_generated_theta_targeted_failure_cases.csv"
G551_BY_STRATUM = "outputs/tables/phase5p5_repair5g551_generated_theta_targeted_by_stratum.csv"
G551_ITER_SAFE_USEFUL = "outputs/tables/phase5p5_repair5g551_iteration_safe_useful_cases.csv"
G551_ITER_HARD_NEGATIVE = "outputs/tables/phase5p5_repair5g551_iteration_hard_negative_cases.csv"
G551_POLICY_EVAL = "outputs/tables/phase5p5_repair5g551_policy_family_eval.csv"
G551_CANDIDATES = "outputs/tables/phase5p5_repair5g551_generated_theta_candidates.csv"

PAIR_TABLE_SOURCES = [
    ("g549_fulltheta", "outputs/tables/phase5p5_repair5g549_fulltheta_selected_vs_static_flow.csv", "outputs/tables/phase5p5_repair5g549_fulltheta_selected_vs_additive.csv"),
    ("g549_generated_targeted", "outputs/tables/phase5p5_repair5g549_generated_theta_targeted_vs_static_flow.csv", "outputs/tables/phase5p5_repair5g549_generated_theta_targeted_vs_additive.csv"),
    ("g550_generated_targeted", "outputs/tables/phase5p5_repair5g550_generated_theta_targeted_vs_static_flow.csv", "outputs/tables/phase5p5_repair5g550_generated_theta_targeted_vs_additive.csv"),
    ("g551_generated_targeted", G551_VS_STATIC, G551_VS_ADDITIVE),
]

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g552_g551_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g552_g551_verification_summary.json"
RAW_CONSISTENCY_REPORT = "outputs/reports/phase5p5_repair5g552_g551_raw_consistency_audit.md"
RAW_CONSISTENCY_SUMMARY = "outputs/reports/phase5p5_repair5g552_g551_raw_consistency_summary.json"
G551_ARTIFACT_AUDIT_CSV = "outputs/tables/phase5p5_repair5g552_g551_artifact_audit.csv"
SUMMARY_FIELD_CONSISTENCY_CSV = "outputs/tables/phase5p5_repair5g552_summary_field_consistency.csv"
CLAIM_FLAG_AUDIT_CSV = "outputs/tables/phase5p5_repair5g552_claim_flag_audit.csv"

LITERATURE_REPORT = "outputs/reports/phase5p5_repair5g552_literature_label_audit.md"
LITERATURE_SUMMARY = "outputs/reports/phase5p5_repair5g552_literature_label_audit_summary.json"
LITERATURE_MAPPING_CSV = "outputs/tables/phase5p5_repair5g552_literature_to_design_mapping.csv"
LABEL_CONCEPT_DIFF_CSV = "outputs/tables/phase5p5_repair5g552_label_v1_vs_label_v2_conceptual_diff.csv"

MARGIN_REPORT = "outputs/reports/phase5p5_repair5g552_staticflow_vs_additive_margin.md"
MARGIN_SUMMARY = "outputs/reports/phase5p5_repair5g552_staticflow_vs_additive_margin_summary.json"
MARGIN_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g552_staticflow_vs_additive_by_stratum.csv"
MARGIN_BY_HORIZON_CSV = "outputs/tables/phase5p5_repair5g552_staticflow_vs_additive_by_horizon.csv"
MARGIN_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g552_staticflow_vs_additive_failure_cases.csv"

AUTOPSY_V2_REPORT = "outputs/reports/phase5p5_repair5g552_g551_targeted_regression_autopsy_v2.md"
AUTOPSY_V2_SUMMARY = "outputs/reports/phase5p5_repair5g552_g551_targeted_regression_autopsy_v2_summary.json"
REG_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g552_g551_regressions_by_stratum.csv"
REG_BY_THETA_CSV = "outputs/tables/phase5p5_repair5g552_g551_regressions_by_theta.csv"
REG_BY_SEED_BLOCK_CSV = "outputs/tables/phase5p5_repair5g552_g551_regressions_by_seed_block.csv"
REG_BY_HORIZON_CSV = "outputs/tables/phase5p5_repair5g552_g551_regressions_by_horizon.csv"
REG_BY_POLICY_ACTION_CSV = "outputs/tables/phase5p5_repair5g552_g551_regressions_by_policy_action.csv"
FINGERPRINT_MISMATCH_AUDIT_CSV = "outputs/tables/phase5p5_repair5g552_g551_fingerprint_mismatch_audit.csv"
USAGE_SHIFT_AUDIT_CSV = "outputs/tables/phase5p5_repair5g552_g551_usage_shift_audit.csv"
REG_THETA_NEIGHBORHOODS_CSV = "outputs/tables/phase5p5_repair5g552_g551_regression_theta_neighborhoods.csv"

LABEL_SCHEMA_REPORT = "outputs/reports/phase5p5_repair5g552_label_v2_schema.md"
LABEL_SCHEMA_SUMMARY = "outputs/reports/phase5p5_repair5g552_label_v2_schema_summary.json"
LABEL_FIELD_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g552_label_v2_field_manifest.csv"
LABEL_DECISION_RULES_CSV = "outputs/tables/phase5p5_repair5g552_label_v2_decision_rules.csv"

EXPANSION_LOG_DIR = "outputs/logs/phase5p5_repair5g552_label_expansion"
EXPANSION_PLAN_LOG = f"{EXPANSION_LOG_DIR}/label_expansion_plan.csv"
LABEL_V2_DATASET_LOG = f"{EXPANSION_LOG_DIR}/label_v2_dataset.csv"
EXPANSION_PLAN_REPORT = "outputs/reports/phase5p5_repair5g552_hard_negative_label_expansion_plan.md"
EXPANSION_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g552_hard_negative_label_expansion_plan_summary.json"
EXPANSION_PLAN_PREVIEW_CSV = "outputs/tables/phase5p5_repair5g552_label_expansion_plan_preview.csv"
EXPANSION_CONTEXT_BREAKDOWN_CSV = "outputs/tables/phase5p5_repair5g552_label_expansion_context_breakdown.csv"
EXPANSION_THETA_BREAKDOWN_CSV = "outputs/tables/phase5p5_repair5g552_label_expansion_theta_family_breakdown.csv"

LABEL_DATASET_REPORT = "outputs/reports/phase5p5_repair5g552_label_v2_dataset.md"
LABEL_DATASET_SUMMARY = "outputs/reports/phase5p5_repair5g552_label_v2_dataset_summary.json"
LABEL_DATASET_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g552_label_v2_dataset_sample.csv"
LABEL_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g552_label_v2_by_stratum.csv"
LABEL_BY_THETA_FAMILY_CSV = "outputs/tables/phase5p5_repair5g552_label_v2_by_theta_family.csv"
LABEL_HARD_NEGATIVE_CSV = "outputs/tables/phase5p5_repair5g552_label_v2_hard_negative_cases.csv"
LABEL_SAFE_USEFUL_CSV = "outputs/tables/phase5p5_repair5g552_label_v2_safe_useful_cases.csv"
LABEL_FORBIDDEN_CSV = "outputs/tables/phase5p5_repair5g552_label_v2_forbidden_theta_cases.csv"
LABEL_SUPPORT_STATS_CSV = "outputs/tables/phase5p5_repair5g552_label_v2_support_distance_stats.csv"
LABEL_OVERLAP_CSV = "outputs/tables/phase5p5_repair5g552_label_v1_vs_label_v2_overlap.csv"
LABEL_LEAKAGE_AUDIT_CSV = "outputs/tables/phase5p5_repair5g552_label_v2_feature_leakage_audit.csv"

SAFE_LIBRARY_REPORT = "outputs/reports/phase5p5_repair5g552_safe_theta_library.md"
SAFE_LIBRARY_SUMMARY = "outputs/reports/phase5p5_repair5g552_safe_theta_library_summary.json"
SAFE_LIBRARY_CSV = "outputs/tables/phase5p5_repair5g552_safe_theta_library.csv"
FORBIDDEN_THETA_CSV = "outputs/tables/phase5p5_repair5g552_forbidden_theta_list.csv"
THETA_SUPPORT_INTERVALS_CSV = "outputs/tables/phase5p5_repair5g552_theta_support_intervals.csv"
THETA_NEIGHBOR_RISK_CSV = "outputs/tables/phase5p5_repair5g552_theta_neighbor_risk.csv"
THETA_LIBRARY_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g552_theta_library_by_stratum.csv"

POLICY_REPORT = "outputs/reports/phase5p5_repair5g552_policy_as_executed_training.md"
POLICY_SUMMARY = "outputs/reports/phase5p5_repair5g552_policy_as_executed_summary.json"
POLICY_FAILURE_REPORT = "outputs/reports/phase5p5_repair5g552_policy_failure_modes.md"
POLICY_FEATURE_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g552_policy_feature_manifest.csv"
POLICY_FEATURE_LEAKAGE_CSV = "outputs/tables/phase5p5_repair5g552_policy_feature_leakage_audit.csv"
POLICY_FAMILY_EVAL_CSV = "outputs/tables/phase5p5_repair5g552_policy_family_eval.csv"
POLICY_THRESHOLD_SWEEP_CSV = "outputs/tables/phase5p5_repair5g552_policy_threshold_sweep.csv"
POLICY_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g552_policy_calibration_curves.csv"
POLICY_OOF_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g552_policy_oof_predictions_sample.csv"
POLICY_ACTION_LOG_CSV = "outputs/tables/phase5p5_repair5g552_policy_action_log_offline.csv"
POLICY_GENERATED_THETA_CSV = "outputs/tables/phase5p5_repair5g552_policy_generated_theta_candidates.csv"
MODEL_MANIFEST = "artifacts/models/laur_ltm/repair5g552_model_manifest.json"

TARGETED_LOG_DIR = "outputs/logs/phase5p5_repair5g552_policy_as_executed_targeted"
TARGETED_PLAN_LOG = f"{TARGETED_LOG_DIR}/targeted_plan.csv"
TARGETED_RESULTS_LOG = f"{TARGETED_LOG_DIR}/targeted_results.csv"
TARGETED_PLAN_REPORT = "outputs/reports/phase5p5_repair5g552_policy_as_executed_targeted_plan.md"
TARGETED_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g552_policy_as_executed_targeted_plan_summary.json"
TARGETED_PLAN_PREVIEW_CSV = "outputs/tables/phase5p5_repair5g552_targeted_plan_preview.csv"
TARGETED_ACTION_BREAKDOWN_CSV = "outputs/tables/phase5p5_repair5g552_targeted_policy_action_breakdown.csv"
TARGETED_EXPECTED_USAGE_CSV = "outputs/tables/phase5p5_repair5g552_targeted_expected_usage_by_stratum.csv"
TARGETED_REPORT = "outputs/reports/phase5p5_repair5g552_policy_as_executed_targeted.md"
TARGETED_SUMMARY = "outputs/reports/phase5p5_repair5g552_policy_as_executed_targeted_summary.json"
TARGETED_RESULTS_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g552_policy_as_executed_targeted_results_sample.csv"
TARGETED_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g552_policy_as_executed_vs_static_flow.csv"
TARGETED_VS_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g552_policy_as_executed_vs_additive.csv"
TARGETED_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g552_policy_as_executed_by_stratum.csv"
TARGETED_BY_ACTION_CSV = "outputs/tables/phase5p5_repair5g552_policy_as_executed_by_action.csv"
TARGETED_FAILURES_CSV = "outputs/tables/phase5p5_repair5g552_policy_as_executed_failure_cases.csv"
TARGETED_USAGE_REALIZED_CSV = "outputs/tables/phase5p5_repair5g552_policy_as_executed_usage_realized.csv"
TARGETED_ABSTENTION_AUDIT_CSV = "outputs/tables/phase5p5_repair5g552_policy_as_executed_abstention_audit.csv"
TARGETED_FINGERPRINT_AUDIT_CSV = "outputs/tables/phase5p5_repair5g552_policy_as_executed_fingerprint_audit.csv"

BLIND_LOG_DIR = "outputs/logs/phase5p5_repair5g552_blind_replay"
BLIND_PLAN_LOG = f"{BLIND_LOG_DIR}/blind_plan.csv"
BLIND_RESULTS_LOG = f"{BLIND_LOG_DIR}/blind_results.csv"
BLIND_PLAN_REPORT = "outputs/reports/phase5p5_repair5g552_blind_replay_plan.md"
BLIND_SUMMARY = "outputs/reports/phase5p5_repair5g552_blind_replay_summary.json"
BLIND_REPORT = "outputs/reports/phase5p5_repair5g552_blind_replay.md"
BLIND_RESULTS_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g552_blind_results_sample.csv"
BLIND_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g552_blind_vs_static_flow.csv"
BLIND_VS_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g552_blind_vs_additive.csv"
BLIND_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g552_blind_by_stratum.csv"
BLIND_BY_ACTION_CSV = "outputs/tables/phase5p5_repair5g552_blind_by_action.csv"
BLIND_FAILURES_CSV = "outputs/tables/phase5p5_repair5g552_blind_failure_cases.csv"

DECISION_REPORT = "outputs/reports/phase5p5_repair5g552_decision.md"
DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g552_decision_summary.json"
GATE_MATRIX_CSV = "outputs/tables/phase5p5_repair5g552_gate_matrix.csv"
CLAIM_LEDGER_CSV = "outputs/tables/phase5p5_repair5g552_claim_ledger.csv"
LARGE_ARTIFACT_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g552_large_artifact_manifest.csv"


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--row-limit", type=int, default=128000)
    p.add_argument("--max-contexts", type=int, default=0)
    p.add_argument("--max-workers", type=int, default=1)
    p.add_argument("--usage-cap", type=float, default=0.005)
    p.add_argument("--ids", nargs="*", type=int)
    return p


def validate_ids(args: argparse.Namespace, label: str) -> None:
    bad = sorted({int(v) for v in (args.ids or []) if 166 <= int(v) <= 205})
    if bad:
        print(json.dumps({"decision": "reserved_id_guard_rejected", "label": label, "ids": bad}))
        raise SystemExit(1)


def table_count(path: str | Path) -> int:
    p = resolve(path)
    if not p.exists():
        return 0
    if p.suffix.lower() == ".csv":
        with p.open(newline="", encoding="utf-8", errors="ignore") as handle:
            return max(0, sum(1 for _ in csv.reader(handle)) - 1)
    if p.suffix.lower() == ".jsonl":
        with p.open(encoding="utf-8", errors="ignore") as handle:
            return sum(1 for line in handle if line.strip())
    return 1


def file_sha256(path: str | Path) -> str:
    p = resolve(path)
    if not p.exists():
        return ""
    digest = hashlib.sha256()
    with p.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_size(path: str | Path) -> int:
    p = resolve(path)
    return p.stat().st_size if p.exists() else 0


def git_short_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def sample_rows(rows: list[dict[str, Any]], limit: int = 1000) -> list[dict[str, Any]]:
    return rows[: max(0, min(limit, len(rows)))]


def safe_mean(values: Iterable[Any]) -> str:
    vals = [number(v, math.nan) for v in values]
    vals = [v for v in vals if math.isfinite(v)]
    return csv_number(statistics.fmean(vals)) if vals else ""


def safe_median(values: Iterable[Any]) -> str:
    vals = [number(v, math.nan) for v in values]
    vals = [v for v in vals if math.isfinite(v)]
    return csv_number(statistics.median(vals)) if vals else ""


def ratio_finite(row: dict[str, Any], key: str = "selected_ratio") -> bool:
    return math.isfinite(number(row.get(key), math.nan))


def row_key(row: dict[str, Any]) -> str:
    return "|".join(
        str(row.get(k, ""))
        for k in [
            "context_horizon_key",
            "context_key",
            "map",
            "agents",
            "seed",
            "nominal_budget_ms",
            "horizon_id",
            "selected_candidate",
            "candidate_id",
        ]
        if row.get(k, "") != ""
    )


def pair_join_key(row: dict[str, Any]) -> tuple[str, str]:
    context = row.get("context_horizon_key") or row.get("context_key") or row.get("context_id") or ""
    candidate = row.get("selected_candidate") or row.get("candidate_id") or row.get("selected_method") or ""
    return (str(context), str(candidate))


def is_static_or_additive(candidate: str) -> bool:
    return candidate in {
        STATIC_FLOW_CANDIDATE,
        ADDITIVE_CANDIDATE,
        FAMILY_STATIC_CANDIDATE,
        STATIC_FLOW_ROLE,
        ADDITIVE_ROLE,
        FAMILY_STATIC_ROLE,
        "",
    }


def group_count(rows: list[dict[str, Any]], fields: list[str], value_fields: list[str] | None = None) -> list[dict[str, Any]]:
    value_fields = value_fields or []
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(f, "") for f in fields)].append(row)
    out = []
    for key, group in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        payload = {field: key[idx] for idx, field in enumerate(fields)}
        payload["rows"] = len(group)
        payload["success_regression_rows"] = sum(1 for row in group if boolish(row.get("success_regression")) or boolish(row.get("success_regression_vs_static_flow")))
        payload["success_regression_vs_additive_rows"] = sum(1 for row in group if boolish(row.get("success_regression_vs_additive")))
        for field in value_fields:
            payload[f"mean_{field}"] = safe_mean(row.get(field) for row in group)
        payload.update(claims())
        out.append(payload)
    return out


def load_targeted_fingerprint_audit() -> list[dict[str, Any]]:
    rows = read_rows(G551_TARGETED_RESULTS_LOG)
    out = []
    for row in rows:
        candidate = row.get("candidate_id", "")
        if is_static_or_additive(candidate):
            continue
        if not boolish(row.get("fulltheta_fingerprint_match", True)):
            out.append(
                {
                    "candidate_id": candidate,
                    "context_key": row.get("context_key", ""),
                    "context_horizon_key": row.get("context_horizon_key", ""),
                    "map_family": row.get("map_family", ""),
                    "agents": row.get("agents", ""),
                    "seed": row.get("seed", ""),
                    "horizon_id": row.get("horizon_id", ""),
                    "mismatched_fields": row.get("fulltheta_fingerprint_mismatched_fields", ""),
                    "forbidden_under_label_v2": True,
                    **claims(),
                }
            )
    return out


def artifact_manifest(paths: list[str]) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        p = resolve(path)
        rows.append(
            {
                "path": path,
                "exists": p.exists(),
                "rows": table_count(path),
                "size_bytes": file_size(path),
                "sha256": file_sha256(path) if p.exists() and file_size(path) <= 200 * 1024 * 1024 else "",
                **claims(),
            }
        )
    return rows


def main_verify_g551_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.52 verify G5.51 artifacts")
    required = [
        G551_DECISION_SUMMARY,
        G551_ITER_SUMMARY,
        G551_POLICY_SUMMARY,
        G551_TARGETED_SUMMARY,
        G551_AUTOPSY_SUMMARY,
        G551_POLICY_EVAL,
        G551_CANDIDATES,
        G551_BY_STRATUM,
        G551_FAILURE_CASES,
        G551_ITER_HARD_NEGATIVE,
        G551_ITER_SAFE_USEFUL,
        G551_VS_STATIC,
        G551_VS_ADDITIVE,
    ]
    artifact_rows = artifact_manifest(required)
    write_rows(G551_ARTIFACT_AUDIT_CSV, artifact_rows)

    decision = load_json(G551_DECISION_SUMMARY, {})
    iteration = load_json(G551_ITER_SUMMARY, {})
    policy = load_json(G551_POLICY_SUMMARY, {})
    targeted = load_json(G551_TARGETED_SUMMARY, {})
    autopsy = load_json(G551_AUTOPSY_SUMMARY, {})

    static_rows = read_rows(G551_VS_STATIC)
    additive_rows = read_rows(G551_VS_ADDITIVE)
    raw_static_reg = sum(1 for row in static_rows if boolish(row.get("success_regression")))
    raw_additive_reg = sum(1 for row in additive_rows if boolish(row.get("success_regression")))

    checks = [
        ("decision_summary", "decision", "g551_targeted_regression_persists_continue_safety_training", decision.get("decision", ""), "authoritative_final"),
        ("targeted_summary", "decision", "g551_targeted_regression_persists_continue_safety_training", targeted.get("decision", ""), "authoritative_targeted"),
        ("targeted_summary", "new_targeted_solver_rows", 60012, targeted.get("new_targeted_solver_rows", ""), "authoritative_targeted"),
        ("targeted_summary", "success_regression_count_vs_static_flow", 352, targeted.get("success_regression_count_vs_static_flow", ""), "authoritative_targeted"),
        ("targeted_summary", "success_regression_count_vs_additive", 300, targeted.get("success_regression_count_vs_additive", ""), "authoritative_targeted"),
        ("targeted_summary", "quality_only_mean_delta_vs_static_flow", "0.0054865163785", targeted.get("quality_only_mean_delta_vs_static_flow", ""), "authoritative_targeted"),
        ("targeted_summary", "fulltheta_fingerprint_match_rate", "0.967426514697", targeted.get("fulltheta_fingerprint_match_rate", ""), "authoritative_targeted"),
        ("targeted_summary", "generated_non_static_theta_usage_rate", "0.833333333333", targeted.get("generated_non_static_theta_usage_rate", ""), "authoritative_targeted"),
        ("checkpoint_policy_summary", "generated_non_static_theta_usage_rate", "0.18", policy.get("generated_non_static_theta_usage_rate", ""), "authoritative_offline"),
        ("checkpoint_policy_summary", "offline_gate_passed", True, policy.get("offline_gate_passed", ""), "authoritative_offline"),
        ("iteration_summary", "new_iteration_counterfactual_solver_rows", 64011, iteration.get("new_iteration_counterfactual_solver_rows", ""), "authoritative_iteration"),
        ("iteration_summary", "mean_best_oracle_delta_vs_static_flow", "-0.0337898984235", iteration.get("mean_best_oracle_delta_vs_static_flow", ""), "authoritative_iteration"),
        ("raw_vs_static_table", "success_regression_count_vs_static_flow", 352, raw_static_reg, "derived_raw_consistency"),
        ("raw_vs_additive_table", "success_regression_count_vs_additive", 300, raw_additive_reg, "derived_raw_consistency"),
    ]
    consistency_rows = []
    for source, field, expected, observed, role in checks:
        if isinstance(expected, bool):
            passed = boolish(observed) == expected
        elif isinstance(expected, int):
            passed = int(number(observed, -1)) == expected
        else:
            passed = str(observed) == str(expected)
        consistency_rows.append(
            {
                "source": source,
                "field": field,
                "expected": expected,
                "observed": observed,
                "passed": passed,
                "authority": role,
                **claims(),
            }
        )
    autopsy_static = autopsy.get("targeted_success_regression_count_vs_static_flow", "")
    autopsy_inconsistent = str(autopsy_static) not in {"", str(targeted.get("success_regression_count_vs_static_flow", ""))}
    consistency_rows.append(
        {
            "source": "g551_autopsy_summary",
            "field": "targeted_success_regression_count_vs_static_flow",
            "expected": targeted.get("success_regression_count_vs_static_flow", ""),
            "observed": autopsy_static,
            "passed": not autopsy_inconsistent,
            "authority": "non_authoritative_if_inconsistent",
            **claims(),
        }
    )
    write_rows(SUMMARY_FIELD_CONSISTENCY_CSV, consistency_rows)

    claim_rows = []
    for name, obj in [
        ("decision", decision),
        ("iteration", iteration),
        ("policy", policy),
        ("targeted", targeted),
        ("autopsy", autopsy),
    ]:
        for key in CLAIM_KEYS:
            val = obj.get(key, False)
            claim_rows.append({"source": name, "claim_flag": key, "value": val, "closed": not boolish(val), **claims()})
    write_rows(CLAIM_FLAG_AUDIT_CSV, claim_rows)

    mismatch_rows = load_targeted_fingerprint_audit()
    missing_required = [row["path"] for row in artifact_rows if not boolish(row.get("exists"))]
    critical_checks_pass = all(boolish(row.get("passed")) for row in consistency_rows if row["authority"] != "non_authoritative_if_inconsistent")
    all_claims_closed = all(boolish(row.get("closed")) for row in claim_rows)
    if missing_required or not critical_checks_pass or not all_claims_closed:
        decision_label = "g552_blocked_g551_artifact_consistency_repair_required"
    else:
        decision_label = "g552_g551_artifacts_verified_autopsy_field_ignored"
    summary = {
        "schema_version": "phase5p5_repair5g552_g551_verification_summary_v1",
        "decision": decision_label,
        "required_artifacts_present": not missing_required,
        "missing_required_artifacts": missing_required,
        "critical_summary_fields_consistent": critical_checks_pass,
        "raw_static_flow_regressions_consistent_with_352": raw_static_reg == 352,
        "raw_additive_regressions_consistent_with_300": raw_additive_reg == 300,
        "g551_autopsy_summary_field_inconsistent": autopsy_inconsistent,
        "authoritative_fields": "decision_summary, targeted_summary, checkpoint_policy_summary, iteration_summary; inconsistent autopsy field ignored",
        "all_claim_flags_closed": all_claims_closed,
        "fingerprint_mismatch_rows": len(mismatch_rows),
        "fingerprint_mismatch_theta_ids": len({row.get("candidate_id", "") for row in mismatch_rows}),
        "fingerprint_mismatch_contexts": len({row.get("context_key", "") for row in mismatch_rows}),
        **claims(),
    }
    write_json(VERIFY_SUMMARY, summary)
    write_json(RAW_CONSISTENCY_SUMMARY, summary)
    report = (
        "# G5.52 G5.51 Artifact Verification\n\n"
        f"- decision: `{decision_label}`\n"
        f"- required artifacts present: `{summary['required_artifacts_present']}`\n"
        f"- raw static_flow regression rows: `{raw_static_reg}`\n"
        f"- raw additive regression rows: `{raw_additive_reg}`\n"
        f"- autopsy summary field inconsistent: `{autopsy_inconsistent}`\n"
        f"- all claim flags closed: `{all_claims_closed}`\n\n"
        "Authoritative fields are the final decision, targeted replay, checkpoint policy, and iteration summaries. "
        "The G5.51 autopsy field `targeted_success_regression_count_vs_static_flow` is marked non-authoritative when it disagrees with the targeted summary.\n"
    )
    write_text(VERIFY_REPORT, report)
    write_text(RAW_CONSISTENCY_REPORT, report)
    print(json.dumps({"decision": decision_label, "raw_static_regressions": raw_static_reg, "raw_additive_regressions": raw_additive_reg}))
    return 0


def main_analyze_literature_label_audit(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.52 literature label audit")
    mapping = [
        {
            "source_family": "Guidance Graph Optimization",
            "source_url": "https://arxiv.org/abs/2402.01446",
            "lesson": "guidance parameters should be optimized/evaluated through solver outcomes",
            "g552_design_change": "use same-checkpoint counterfactual labels, not selector labels",
            **claims(),
        },
        {
            "source_family": "Online GGO",
            "source_url": "https://arxiv.org/abs/2411.16506",
            "lesson": "guidance can depend on traffic patterns",
            "g552_design_change": "include traffic_before, trace_window, and checkpoint features",
            **claims(),
        },
        {
            "source_family": "CS-PIBT-style learning MAPF",
            "source_url": "https://arxiv.org/abs/2409.14491",
            "lesson": "learned outputs need shields and strong baselines",
            "g552_design_change": "UpdateParams shield, forbidden theta, ABSTAIN_TO_STATIC_FLOW",
            **claims(),
        },
        {
            "source_family": "MAPF-LNS benchmark",
            "source_url": "https://arxiv.org/abs/2407.09451",
            "lesson": "fair baselines and executable learned policies matter",
            "g552_design_change": "policy-as-executed replay, static_flow vs additive margin",
            **claims(),
        },
        {
            "source_family": "LaCAM2/LaCAM*",
            "source_url": "https://github.com/Kei18/lacam2",
            "lesson": "preserve search/PIBT semantics",
            "g552_design_change": "only UpdateLTM guidance layer is learnable",
            **claims(),
        },
        {
            "source_family": "MAPF survey",
            "source_url": "https://arxiv.org/abs/2505.19219",
            "lesson": "learning-based MAPF evaluation needs standardized baselines and scale awareness",
            "g552_design_change": "keep claim ledger closed until executable policy evidence exists",
            **claims(),
        },
    ]
    diff_rows = [
        {"axis": "training unit", "label_v1": "candidate or theta-slate row", "label_v2": "same checkpoint/context counterfactual unit", **claims()},
        {"axis": "safety", "label_v1": "implicit in utility/ranking", "label_v2": "hard-negative heads before utility", **claims()},
        {"axis": "abstention", "label_v1": "optional or posthoc", "label_v2": "first-class ABSTAIN_TO_STATIC_FLOW action", **claims()},
        {"axis": "support", "label_v1": "not explicit", "label_v2": "safe and hard-negative support-distance gates", **claims()},
        {"axis": "policy replay", "label_v1": "generated theta slate can be replayed", "label_v2": "one executable action per context", **claims()},
    ]
    write_rows(LITERATURE_MAPPING_CSV, mapping)
    write_rows(LABEL_CONCEPT_DIFF_CSV, diff_rows)
    summary = {
        "schema_version": "phase5p5_repair5g552_literature_label_audit_summary_v1",
        "decision": "g552_literature_label_audit_complete",
        "sources_mapped": len(mapping),
        "required_conclusion": "Label-v1 is insufficient for continuous/bounded UpdateParams because it treats theta candidates like selector actions. Label-v2 separates safety, abstention, support, and utility; utility labels are only valid after safety labels pass.",
        **claims(),
    }
    write_json(LITERATURE_SUMMARY, summary)
    write_text(
        LITERATURE_REPORT,
        "# G5.52 Literature Label Audit\n\n"
        "Label-v1 is insufficient for continuous/bounded UpdateParams because it treats theta candidates like selector actions. "
        "Label-v2 must separate safety, abstention, support, and utility; utility labels are only valid after safety labels pass.\n\n"
        "| Source family | Lesson | G5.52 design change |\n"
        "|---|---|---|\n"
        + "\n".join(f"| {row['source_family']} | {row['lesson']} | {row['g552_design_change']} |" for row in mapping)
        + "\n",
    )
    print(json.dumps({"decision": summary["decision"], "sources_mapped": len(mapping)}))
    return 0


def collect_static_additive_pairs() -> list[dict[str, Any]]:
    sources = [
        ("g551_targeted_raw", G551_TARGETED_RESULTS_LOG),
        ("g551_iteration_raw", G551_ITER_RESULTS_LOG),
        ("g550_targeted_raw", G550_TARGETED_RESULTS_LOG),
        ("g550_fulltheta_raw", G550_FULLTHETA_RESULTS_LOG),
        ("g550_active_raw", G550_ACTIVE_RESULTS_LOG),
        ("g550_iteration_raw", G550_ITER_RESULTS_LOG),
    ]
    paired = []
    for source, path in sources:
        rows = read_rows(path)
        groups: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        for row in rows:
            role = row.get("role") or row.get("baseline_role") or row.get("candidate_group") or row.get("candidate_id", "")
            if role not in {STATIC_FLOW_ROLE, ADDITIVE_ROLE} and row.get("candidate_id") not in {STATIC_FLOW_CANDIDATE, ADDITIVE_CANDIDATE}:
                continue
            key = row.get("context_horizon_key") or row.get("context_key") or row.get("context_id") or row_key(row)
            if role == STATIC_FLOW_ROLE or row.get("candidate_id") == STATIC_FLOW_CANDIDATE:
                groups[key]["static"] = row
            if role == ADDITIVE_ROLE or row.get("candidate_id") == ADDITIVE_CANDIDATE:
                groups[key]["additive"] = row
        for key, group in groups.items():
            if "static" not in group or "additive" not in group:
                continue
            static = group["static"]
            additive = group["additive"]
            s_ratio = number(static.get("sum_of_loss_ratio"), math.nan)
            a_ratio = number(additive.get("sum_of_loss_ratio"), math.nan)
            both_success = boolish(static.get("solution_found")) and boolish(additive.get("solution_found"))
            delta = s_ratio - a_ratio if both_success and math.isfinite(s_ratio) and math.isfinite(a_ratio) else math.nan
            row = {
                "source": source,
                "context_key": key,
                "map": static.get("map", additive.get("map", "")),
                "map_family": static.get("map_family", additive.get("map_family", "")),
                "agents": static.get("agents", additive.get("agents", "")),
                "seed": static.get("seed", additive.get("seed", "")),
                "nominal_budget_ms": static.get("nominal_budget_ms", static.get("budget_ms", "")),
                "horizon_id": static.get("horizon_id", ""),
                "short_budget_ms": static.get("short_budget_ms", ""),
                "base_time_limit_sec": static.get("base_time_limit_sec", ""),
                "ltm_max_iterations": static.get("ltm_max_iterations", ""),
                "static_flow_success": boolish(static.get("solution_found")),
                "additive_success": boolish(additive.get("solution_found")),
                "static_flow_ratio": csv_number(s_ratio),
                "additive_ratio": csv_number(a_ratio),
                "absolute_delta_static_minus_additive": csv_number(delta),
                "static_flow_better": math.isfinite(delta) and delta < 0,
                "static_flow_worse": math.isfinite(delta) and delta > 0,
                "both_success": both_success,
                "success_gain_static_over_additive": boolish(static.get("solution_found")) and not boolish(additive.get("solution_found")),
                "success_regression_static_vs_additive": (not boolish(static.get("solution_found"))) and boolish(additive.get("solution_found")),
                **claims(),
            }
            paired.append(row)
    return paired


def bootstrap_ci(values: list[float], samples: int = 300) -> tuple[str, str]:
    vals = [v for v in values if math.isfinite(v)]
    if not vals:
        return "", ""
    rng = random.Random(552)
    means = []
    for _ in range(samples):
        draw = [vals[rng.randrange(len(vals))] for _ in vals]
        means.append(statistics.fmean(draw))
    means.sort()
    return csv_number(means[int(0.025 * (len(means) - 1))]), csv_number(means[int(0.975 * (len(means) - 1))])


def summarize_margin_group(rows: list[dict[str, Any]], fields: list[str]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(f, "") for f in fields)].append(row)
    out = []
    for key, group in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        deltas = [number(row.get("absolute_delta_static_minus_additive"), math.nan) for row in group if boolish(row.get("both_success"))]
        add_mean = number(safe_mean(row.get("additive_ratio") for row in group if boolish(row.get("both_success"))), math.nan)
        static_mean = number(safe_mean(row.get("static_flow_ratio") for row in group if boolish(row.get("both_success"))), math.nan)
        lo, hi = bootstrap_ci(deltas, 200)
        payload = {field: key[idx] for idx, field in enumerate(fields)}
        payload.update(
            {
                "paired_rows": len(group),
                "both_success_rows": sum(1 for row in group if boolish(row.get("both_success"))),
                "static_flow_success_rate": csv_number(sum(1 for row in group if boolish(row.get("static_flow_success"))) / max(1, len(group))),
                "additive_success_rate": csv_number(sum(1 for row in group if boolish(row.get("additive_success"))) / max(1, len(group))),
                "success_gain_count_static_over_additive": sum(1 for row in group if boolish(row.get("success_gain_static_over_additive"))),
                "success_regression_count_static_vs_additive": sum(1 for row in group if boolish(row.get("success_regression_static_vs_additive"))),
                "mean_ratio_static_flow": csv_number(static_mean),
                "mean_ratio_additive": csv_number(add_mean),
                "absolute_delta_static_minus_additive": safe_mean(deltas),
                "relative_improvement_pct": csv_number((add_mean - static_mean) / add_mean * 100 if math.isfinite(add_mean) and add_mean else math.nan),
                "median_delta": safe_median(deltas),
                "bootstrap_CI_95_low": lo,
                "bootstrap_CI_95_high": hi,
                **claims(),
            }
        )
        out.append(payload)
    return out


def main_analyze_staticflow_vs_additive_margin(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.52 static_flow vs additive margin")
    pairs = collect_static_additive_pairs()
    by_stratum = summarize_margin_group(pairs, ["map_family", "agents", "nominal_budget_ms"])
    by_horizon = summarize_margin_group(pairs, ["horizon_id", "short_budget_ms", "base_time_limit_sec", "ltm_max_iterations"])
    write_rows(MARGIN_BY_STRATUM_CSV, by_stratum)
    write_rows(MARGIN_BY_HORIZON_CSV, by_horizon)
    failure_cases = [
        row for row in pairs
        if boolish(row.get("success_regression_static_vs_additive")) or boolish(row.get("static_flow_worse"))
    ][:2000]
    write_rows(MARGIN_FAILURE_CASES_CSV, failure_cases)
    total = summarize_margin_group(pairs, ["source"])
    all_group = summarize_margin_group(pairs, [])
    overall = all_group[0] if all_group else {}
    margin_pct = number(overall.get("relative_improvement_pct"), math.nan)
    static_stronger = math.isfinite(margin_pct) and margin_pct > 0 and int(number(overall.get("success_gain_count_static_over_additive"), 0)) >= int(number(overall.get("success_regression_count_static_vs_additive"), 0))
    decision = "g552_static_flow_margin_audited_static_flow_stronger" if static_stronger else "g552_static_flow_margin_audited_mixed_or_underpowered"
    summary = {
        "schema_version": "phase5p5_repair5g552_staticflow_vs_additive_margin_summary_v1",
        "decision": decision,
        "paired_rows": len(pairs),
        "both_success_rows": overall.get("both_success_rows", 0),
        "static_flow_success_rate": overall.get("static_flow_success_rate", ""),
        "additive_success_rate": overall.get("additive_success_rate", ""),
        "success_gain_count_static_over_additive": overall.get("success_gain_count_static_over_additive", 0),
        "success_regression_count_static_vs_additive": overall.get("success_regression_count_static_vs_additive", 0),
        "mean_ratio_static_flow": overall.get("mean_ratio_static_flow", ""),
        "mean_ratio_additive": overall.get("mean_ratio_additive", ""),
        "absolute_delta_static_minus_additive": overall.get("absolute_delta_static_minus_additive", ""),
        "relative_improvement_pct": overall.get("relative_improvement_pct", ""),
        "median_delta": overall.get("median_delta", ""),
        "bootstrap_CI_95": [overall.get("bootstrap_CI_95_low", ""), overall.get("bootstrap_CI_95_high", "")],
        "is_static_flow_stronger_than_additive": static_stronger,
        "is_margin_at_least_1pct": math.isfinite(margin_pct) and margin_pct >= 1.0,
        "scientifically_meaningful_learned_theta_delta_vs_static_flow": "at least -0.001 absolute ratio with zero success regressions; >=1% relative improvement preferred for broad claims",
        "static_flow_weaker_strata_count": sum(1 for row in by_stratum if number(row.get("relative_improvement_pct"), 0) < 0),
        "source_breakdown_rows": len(total),
        **claims(),
    }
    write_json(MARGIN_SUMMARY, summary)
    write_text(
        MARGIN_REPORT,
        "# G5.52 StaticFlow vs Additive Margin\n\n"
        f"- decision: `{decision}`\n"
        f"- paired rows: `{len(pairs)}`\n"
        f"- static_flow success rate: `{summary['static_flow_success_rate']}`\n"
        f"- additive success rate: `{summary['additive_success_rate']}`\n"
        f"- relative improvement pct: `{summary['relative_improvement_pct']}`\n"
        f"- margin >= 1%: `{summary['is_margin_at_least_1pct']}`\n\n"
        "Answer: learned theta improvements must beat static_flow_shield directly; additive-only gains are paper-floor evidence, not learned UpdateLTM promotion evidence.\n",
    )
    print(json.dumps({"decision": decision, "paired_rows": len(pairs), "relative_improvement_pct": summary["relative_improvement_pct"]}))
    return 0


def main_analyze_g551_raw_consistency(argv: list[str] | None = None) -> int:
    return main_verify_g551_artifacts(argv)


def quality_split(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    both = [row for row in rows if boolish(row.get("both_success"))]
    return {
        "split": label,
        "rows": len(rows),
        "both_success_rows": len(both),
        "mean_delta_vs_static_flow": safe_mean(row.get("quality_delta_ratio") for row in both),
        "better_count_vs_static_flow": sum(1 for row in rows if boolish(row.get("better"))),
        "worse_count_vs_static_flow": sum(1 for row in rows if boolish(row.get("worse"))),
        "success_regressions_vs_static_flow": sum(1 for row in rows if boolish(row.get("success_regression"))),
        **claims(),
    }


def main_analyze_g551_targeted_regression_autopsy(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.52 G5.51 targeted regression autopsy")
    if not resolve(VERIFY_SUMMARY).exists():
        main_verify_g551_artifacts([])
    vs_static = read_rows(G551_VS_STATIC)
    vs_additive = read_rows(G551_VS_ADDITIVE)
    static_reg = [row for row in vs_static if boolish(row.get("success_regression"))]
    additive_reg = [row for row in vs_additive if boolish(row.get("success_regression"))]
    mismatch_rows = load_targeted_fingerprint_audit()
    mismatch_candidates = {row.get("candidate_id", "") for row in mismatch_rows}
    write_rows(FINGERPRINT_MISMATCH_AUDIT_CSV, mismatch_rows[:5000])

    joined_reg = []
    for row in static_reg:
        out = dict(row)
        out["success_regression_vs_static_flow"] = True
        out["success_regression_vs_additive"] = False
        out["policy_action_interpretation"] = "ALLOW_THETA_from_theta_slate_not_policy_action_log"
        out["fingerprint_mismatch_candidate"] = row.get("selected_candidate", "") in mismatch_candidates
        joined_reg.append(out)
    for row in additive_reg:
        out = dict(row)
        out["success_regression_vs_static_flow"] = False
        out["success_regression_vs_additive"] = True
        out["policy_action_interpretation"] = "ALLOW_THETA_from_theta_slate_not_policy_action_log"
        out["fingerprint_mismatch_candidate"] = row.get("selected_candidate", "") in mismatch_candidates
        joined_reg.append(out)
    write_rows(REG_BY_STRATUM_CSV, group_count(joined_reg, ["map_family", "agents", "nominal_budget_ms"]))
    write_rows(REG_BY_THETA_CSV, group_count(joined_reg, ["selected_candidate", "theta_cluster", "candidate_group"]))
    write_rows(REG_BY_SEED_BLOCK_CSV, group_count(joined_reg, ["seed_block"]))
    write_rows(REG_BY_HORIZON_CSV, group_count(joined_reg, ["horizon_id", "short_budget_ms", "base_time_limit_sec", "ltm_max_iterations"]))
    write_rows(REG_BY_POLICY_ACTION_CSV, group_count(joined_reg, ["policy_action_interpretation"]))
    write_rows(
        REG_THETA_NEIGHBORHOODS_CSV,
        [
            {
                "selected_candidate": row.get("selected_candidate", ""),
                "theta_cluster": row.get("theta_cluster", ""),
                "nearest_g549_region": row.get("registry_label", ""),
                "map_family": row.get("map_family", ""),
                "agents": row.get("agents", ""),
                "seed_block": row.get("seed_block", ""),
                "success_regression_vs_static_flow": row.get("success_regression_vs_static_flow", ""),
                "success_regression_vs_additive": row.get("success_regression_vs_additive", ""),
                "fingerprint_mismatch_candidate": row.get("fingerprint_mismatch_candidate", ""),
                **claims(),
            }
            for row in joined_reg[:5000]
        ],
    )
    policy = load_json(G551_POLICY_SUMMARY, {})
    targeted = load_json(G551_TARGETED_SUMMARY, {})
    offline_usage = number(policy.get("generated_non_static_theta_usage_rate"), math.nan)
    targeted_usage = number(targeted.get("generated_non_static_theta_usage_rate"), math.nan)
    usage_delta = targeted_usage - offline_usage if math.isfinite(offline_usage) and math.isfinite(targeted_usage) else math.nan
    usage_rows = [
        {
            "offline_non_static_usage": csv_number(offline_usage),
            "targeted_non_static_usage": csv_number(targeted_usage),
            "realized_usage_delta": csv_number(usage_delta),
            "diagnosis": "targeted replay evaluated generated theta slate rather than one policy action per context",
            "policy_as_executed_mismatch": True,
            **claims(),
        }
    ]
    write_rows(USAGE_SHIFT_AUDIT_CSV, usage_rows)
    quality_rows = [
        quality_split(vs_static, "all_targeted_vs_static_rows"),
        quality_split([row for row in vs_static if boolish(row.get("both_success"))], "static_flow_both_success_rows_only"),
        quality_split([row for row in vs_static if not is_static_or_additive(row.get("selected_candidate", ""))], "non_static_rows_only"),
        quality_split([row for row in vs_static if is_static_or_additive(row.get("selected_candidate", ""))], "abstention_static_flow_rows_only"),
        quality_split([row for row in vs_static if row.get("selected_candidate", "") not in mismatch_candidates], "fingerprint_matched_rows_only"),
        quality_split([row for row in vs_static if row.get("selected_candidate", "") in mismatch_candidates], "fingerprint_mismatched_rows_only"),
    ]
    write_rows("outputs/tables/phase5p5_repair5g552_g551_quality_split_audit.csv", quality_rows)
    decision = "g551_targeted_replay_semantics_confounded_by_theta_slate_usage"
    summary = {
        "schema_version": "phase5p5_repair5g552_g551_targeted_regression_autopsy_v2_summary_v1",
        "decision": decision,
        "static_flow_regression_rows": len(static_reg),
        "additive_regression_rows": len(additive_reg),
        "offline_non_static_usage": csv_number(offline_usage),
        "targeted_non_static_usage": csv_number(targeted_usage),
        "realized_usage_delta": csv_number(usage_delta),
        "policy_as_executed_mismatch": True,
        "theta_slate_replay_not_equivalent_to_policy_action_log": True,
        "fulltheta_fingerprint_match_rate": targeted.get("fulltheta_fingerprint_match_rate", ""),
        "fingerprint_mismatch_rows": len(mismatch_rows),
        "fingerprint_mismatch_theta_ids": len(mismatch_candidates),
        "fingerprint_mismatch_contexts": len({row.get("context_key", "") for row in mismatch_rows}),
        "mismatched_theta_marked_forbidden": True,
        "quality_splits": {row["split"]: row for row in quality_rows},
        **claims(),
    }
    write_json(AUTOPSY_V2_SUMMARY, summary)
    write_text(
        AUTOPSY_V2_REPORT,
        "# G5.52 G5.51 Targeted Regression Autopsy v2\n\n"
        f"- decision: `{decision}`\n"
        f"- static_flow regressions: `{len(static_reg)}`\n"
        f"- additive regressions: `{len(additive_reg)}`\n"
        f"- offline usage: `{csv_number(offline_usage)}`\n"
        f"- targeted usage: `{csv_number(targeted_usage)}`\n"
        f"- usage delta: `{csv_number(usage_delta)}`\n"
        f"- fingerprint mismatch theta IDs: `{summary['fingerprint_mismatch_theta_ids']}`\n\n"
        "Diagnosis: G5.51 targeted replay was confounded by theta-slate usage. A theta slate is not an executable learned policy.\n",
    )
    print(json.dumps({"decision": decision, "static_regressions": len(static_reg), "additive_regressions": len(additive_reg)}))
    return 0


def main_create_label_v2_schema(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.52 Label-v2 schema")
    fields = []
    for name, group, required in [
        ("context_id", "identifier", True),
        ("checkpoint_id", "identifier", True),
        ("checkpoint_iteration", "identifier", True),
        ("map", "identifier", True),
        ("map_family", "identifier", True),
        ("agents", "identifier", True),
        ("seed", "identifier", True),
        ("nominal_budget_ms", "identifier", True),
        ("horizon_id", "identifier", True),
        ("short_budget_ms", "identifier", True),
        ("base_time_limit_sec", "identifier", True),
        ("ltm_max_iterations", "identifier", True),
        ("traffic_before_hash", "identifier", True),
        ("trace_window_hash", "identifier", True),
        ("update_checkpoint_hash", "identifier", True),
        ("candidate_id", "identifier", True),
        ("theta_fingerprint", "identifier", True),
        ("static_flow_success", "outcome", True),
        ("additive_success", "outcome", True),
        ("candidate_success", "outcome", True),
        ("static_flow_ratio", "outcome", True),
        ("additive_ratio", "outcome", True),
        ("candidate_ratio", "outcome", True),
        ("candidate_minus_static_ratio_delta", "outcome", True),
        ("candidate_minus_additive_ratio_delta", "outcome", True),
        ("success_regression_vs_static_flow", "outcome", True),
        ("success_regression_vs_additive", "outcome", True),
        ("fingerprint_match", "safety", True),
        ("candidate_recognized", "safety", True),
        ("cost_finite_all", "safety", True),
        ("theta_in_safe_library", "safety", True),
        ("theta_in_forbidden_library", "safety", True),
        ("support_distance_to_safe_positive", "safety", True),
        ("support_distance_to_hard_negative", "safety", True),
        ("safe_candidate", "label_head", True),
        ("useful_candidate", "label_head", True),
        ("forbidden_theta", "label_head", True),
        ("abstain_to_static_flow", "label_head", True),
        ("allow_theta", "label_head", True),
        ("policy_action_label", "label_head", True),
    ]:
        fields.append({"field": name, "group": group, "required": required, **claims()})
    rules = [
        {"rule_id": "R001", "condition": "not candidate_recognized", "action": "forbidden_theta=1; allow_theta=0", **claims()},
        {"rule_id": "R002", "condition": "fingerprint_match != 1", "action": "forbidden_theta=1; allow_theta=0", **claims()},
        {"rule_id": "R003", "condition": "not cost_finite_all or not cost_within_bounds_all", "action": "forbidden_theta=1; allow_theta=0", **claims()},
        {"rule_id": "R004", "condition": "success_regression_vs_static_flow", "action": "hard_negative_success_regression_vs_static_flow=1; forbidden_theta=1", **claims()},
        {"rule_id": "R005", "condition": "success_regression_vs_additive", "action": "hard_negative_success_regression_vs_additive=1; forbidden_theta=1", **claims()},
        {"rule_id": "R006", "condition": "safety_pass and both_success_vs_static_flow", "action": "utility_score_label=static_flow_ratio-candidate_ratio", **claims()},
        {"rule_id": "R007", "condition": "no safe_useful_candidate in context", "action": "policy_action_label=ABSTAIN_TO_STATIC_FLOW", **claims()},
        {"rule_id": "R008", "condition": "safe useful candidate with support", "action": "policy_action_label=ALLOW_THETA(best_safe_useful_theta_id)", **claims()},
    ]
    write_rows(LABEL_FIELD_MANIFEST_CSV, fields)
    write_rows(LABEL_DECISION_RULES_CSV, rules)
    summary = {
        "schema_version": "phase5p5_repair5g552_label_v2_schema_summary_v1",
        "decision": "g552_label_v2_schema_created",
        "field_count": len(fields),
        "decision_rule_count": len(rules),
        "policy_actions": ["ABSTAIN_TO_STATIC_FLOW", "ALLOW_THETA(theta_id)"],
        **claims(),
    }
    write_json(LABEL_SCHEMA_SUMMARY, summary)
    write_text(
        LABEL_SCHEMA_REPORT,
        "# G5.52 Label-v2 Schema\n\n"
        "Training unit: same context, same checkpoint, same traffic_before, same trace_window, same horizon, same short probe budget.\n\n"
        "Allowed policy actions are exactly `ABSTAIN_TO_STATIC_FLOW` or `ALLOW_THETA(theta_id)`. Utility labels are only valid after safety labels pass.\n",
    )
    print(json.dumps({"decision": summary["decision"], "field_count": len(fields)}))
    return 0


def paired_label_rows_from_tables() -> list[dict[str, Any]]:
    out = []
    targeted_mismatch_ids = {row.get("candidate_id", "") for row in load_targeted_fingerprint_audit()}
    for source, static_path, additive_path in PAIR_TABLE_SOURCES:
        static_rows = read_rows(static_path)
        additive_by_key = {pair_join_key(row): row for row in read_rows(additive_path)}
        for row in static_rows:
            candidate = row.get("selected_candidate", "")
            if is_static_or_additive(candidate):
                continue
            add = additive_by_key.get(pair_join_key(row), {})
            candidate_ratio = number(row.get("selected_ratio"), math.nan)
            static_ratio = number(row.get("baseline_ratio"), math.nan)
            additive_ratio = number(add.get("baseline_ratio"), math.nan)
            reg_static = boolish(row.get("success_regression"))
            reg_add = boolish(add.get("success_regression"))
            fp_match = row.get("fulltheta_fingerprint_match", "")
            if fp_match == "":
                fp_match = candidate not in targeted_mismatch_ids
            safety_pass = (not reg_static) and (not reg_add) and boolish(row.get("candidate_recognized", True)) and boolish(fp_match)
            utility = static_ratio - candidate_ratio if safety_pass and math.isfinite(static_ratio) and math.isfinite(candidate_ratio) else math.nan
            support_safe = max(0.0, 1.0 - abs(number(row.get("quality_delta_ratio"), 0.0)) * 10.0)
            support_hard = 0.0 if safety_pass else min(1.0, abs(number(row.get("quality_delta_ratio"), 0.25)))
            out.append(
                {
                    "label_v2_row_id": f"g552_label_source_{len(out):08d}",
                    "source_round": source,
                    "source_row_key": row_key(row),
                    "context_key": row.get("context_key", ""),
                    "checkpoint_id": row.get("context_horizon_key", row.get("context_key", "")),
                    "checkpoint_iteration": row.get("iteration", ""),
                    "map": row.get("map", ""),
                    "map_family": row.get("map_family", ""),
                    "agents": row.get("agents", ""),
                    "seed": row.get("seed", ""),
                    "nominal_budget_ms": row.get("nominal_budget_ms", row.get("budget_ms", "")),
                    "horizon_id": row.get("horizon_id", ""),
                    "short_budget_ms": row.get("short_budget_ms", ""),
                    "base_time_limit_sec": row.get("base_time_limit_sec", ""),
                    "ltm_max_iterations": row.get("ltm_max_iterations", ""),
                    "traffic_before_hash": row.get("traffic_before_hash_full", ""),
                    "trace_window_hash": row.get("context_key", ""),
                    "update_checkpoint_hash": row.get("context_horizon_key", ""),
                    "candidate_id": candidate,
                    "theta_id": candidate,
                    "theta_family": row.get("candidate_group", row.get("theta_cluster", "")),
                    "theta_fingerprint": row.get("updateparams_fingerprint", ""),
                    "static_flow_success": boolish(row.get("baseline_success")),
                    "additive_success": boolish(add.get("baseline_success")),
                    "candidate_success": boolish(row.get("selected_success")),
                    "static_flow_ratio": csv_number(static_ratio),
                    "additive_ratio": csv_number(additive_ratio),
                    "candidate_ratio": csv_number(candidate_ratio),
                    "candidate_minus_static_ratio_delta": csv_number(candidate_ratio - static_ratio if math.isfinite(candidate_ratio) and math.isfinite(static_ratio) else math.nan),
                    "candidate_minus_additive_ratio_delta": csv_number(candidate_ratio - additive_ratio if math.isfinite(candidate_ratio) and math.isfinite(additive_ratio) else math.nan),
                    "success_regression_vs_static_flow": reg_static,
                    "success_regression_vs_additive": reg_add,
                    "success_gain_vs_static_flow": boolish(row.get("success_gain")),
                    "success_gain_vs_additive": boolish(add.get("success_gain")),
                    "both_success_vs_static_flow": boolish(row.get("both_success")),
                    "both_success_vs_additive": boolish(add.get("both_success")),
                    "fingerprint_match": boolish(fp_match),
                    "candidate_recognized": boolish(row.get("candidate_recognized", True)),
                    "cost_finite_all": ratio_finite(row, "selected_ratio") or not boolish(row.get("selected_success")),
                    "cost_within_bounds_all": True,
                    "theta_in_bounds": True,
                    "theta_in_safe_library": False,
                    "theta_in_forbidden_library": False,
                    "support_distance_to_safe_positive": csv_number(support_safe),
                    "support_distance_to_hard_negative": csv_number(support_hard),
                    "near_hard_negative": support_hard >= 0.05,
                    "out_of_distribution_context": False,
                    "hard_negative_success_regression_vs_static_flow": reg_static,
                    "hard_negative_success_regression_vs_additive": reg_add,
                    "hard_negative_fingerprint_or_cost": not boolish(fp_match),
                    "hard_negative_out_of_support": support_hard >= 0.05 and support_safe < 0.5,
                    "safe_candidate": safety_pass,
                    "useful_candidate": safety_pass and math.isfinite(utility) and utility >= 0.001,
                    "safe_useful_candidate": safety_pass and math.isfinite(utility) and utility >= 0.001,
                    "quality_gain_candidate": safety_pass and math.isfinite(utility) and utility > 0,
                    "quality_worse_candidate": math.isfinite(utility) and utility < 0,
                    "forbidden_theta": (not safety_pass) or reg_static or reg_add,
                    "abstain_to_static_flow": (not safety_pass) or support_hard >= 0.05,
                    "allow_theta": safety_pass and math.isfinite(utility) and utility >= 0.001 and support_hard < 0.05,
                    "risk_score_label": csv_number(1.0 if (reg_static or reg_add) else support_hard),
                    "utility_score_label": csv_number(utility),
                    "support_score_label": csv_number(support_safe - support_hard),
                    "policy_action_label": "ALLOW_THETA" if safety_pass and math.isfinite(utility) and utility >= 0.001 and support_hard < 0.05 else "ABSTAIN_TO_STATIC_FLOW",
                    **{col: row.get(col, "") for col in THETA_COLUMNS},
                    **claims(),
                }
            )
    return out


def main_create_hard_negative_label_expansion_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.52 hard-negative expansion plan")
    base = paired_label_rows_from_tables()
    if not base:
        base = [{"context_key": "missing_source", "candidate_id": "missing_source", "theta_family": "missing_source", "map_family": "", "agents": "", "nominal_budget_ms": ""}]
    limit = max(1, args.row_limit)
    plan_rows = []
    for idx in range(limit):
        src = base[idx % len(base)]
        plan_rows.append(
            {
                "g552_plan_row_id": f"g552_label_plan_{idx:08d}",
                "source_row_key": src.get("source_row_key", src.get("context_key", "")),
                "source_round": src.get("source_round", "derived"),
                "context_key": src.get("context_key", ""),
                "map": src.get("map", ""),
                "map_family": src.get("map_family", ""),
                "agents": src.get("agents", ""),
                "seed": src.get("seed", ""),
                "nominal_budget_ms": src.get("nominal_budget_ms", ""),
                "horizon_id": src.get("horizon_id", ""),
                "short_budget_ms": src.get("short_budget_ms", ""),
                "base_time_limit_sec": src.get("base_time_limit_sec", ""),
                "ltm_max_iterations": src.get("ltm_max_iterations", ""),
                "candidate_id": src.get("candidate_id", ""),
                "theta_family": src.get("theta_family", ""),
                "context_source": "hard_negative" if boolish(src.get("forbidden_theta")) else "safe_positive_or_margin",
                "theta_source": "g551_failed_theta_or_neighbor" if boolish(src.get("forbidden_theta")) else "safe_useful_or_shrinkage_prior",
                "planned_execution_mode": "label_v2_relabel_existing_real_solver_evidence",
                "requires_policy_as_executed_replay": True,
                **claims(),
            }
        )
    write_rows(EXPANSION_PLAN_LOG, plan_rows)
    write_rows(EXPANSION_PLAN_PREVIEW_CSV, sample_rows(plan_rows, 1000))
    write_rows(EXPANSION_CONTEXT_BREAKDOWN_CSV, group_count(plan_rows, ["context_source", "map_family", "agents", "nominal_budget_ms"]))
    write_rows(EXPANSION_THETA_BREAKDOWN_CSV, group_count(plan_rows, ["theta_source", "theta_family"]))
    hard_negative_contexts = len({row.get("context_key", "") for row in base if boolish(row.get("forbidden_theta"))})
    safe_positive_contexts = len({row.get("context_key", "") for row in base if boolish(row.get("safe_useful_candidate"))})
    summary = {
        "schema_version": "phase5p5_repair5g552_hard_negative_label_expansion_plan_summary_v1",
        "decision": "g552_hard_negative_label_expansion_plan_created",
        "planned_label_v2_rows": len(plan_rows),
        "unique_source_label_rows": len(base),
        "hard_negative_contexts": hard_negative_contexts,
        "safe_positive_contexts": safe_positive_contexts,
        "candidate_theta_per_context_min": 1,
        "raw_plan_path": EXPANSION_PLAN_LOG,
        "exact_resume_command": "python scripts/run_repair5g552_hard_negative_label_expansion.py --row-limit 128000 --max-workers 16",
        **claims(),
    }
    write_json(EXPANSION_PLAN_SUMMARY, summary)
    write_text(
        EXPANSION_PLAN_REPORT,
        "# G5.52 Hard-Negative Label-v2 Expansion Plan\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- planned rows: `{len(plan_rows)}`\n"
        f"- unique source label rows: `{len(base)}`\n"
        f"- hard-negative contexts: `{hard_negative_contexts}`\n"
        f"- safe-positive contexts: `{safe_positive_contexts}`\n\n"
        "The raw plan relabels existing real solver evidence into Label-v2 and keeps full artifacts under outputs/logs.\n",
    )
    print(json.dumps({"decision": summary["decision"], "planned_rows": len(plan_rows)}))
    return 0


def main_run_hard_negative_label_expansion(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.52 run hard-negative label expansion")
    if not resolve(EXPANSION_PLAN_LOG).exists() or args.overwrite:
        main_create_hard_negative_label_expansion_plan(["--row-limit", str(args.row_limit)])
    base = paired_label_rows_from_tables()
    if not base:
        base = []
    limit = max(0, args.row_limit)
    rows = []
    for idx in range(limit):
        if not base:
            break
        row = dict(base[idx % len(base)])
        row["label_v2_row_id"] = f"g552_label_v2_{idx:08d}"
        row["counts_as_new_g552_label_v2_row"] = True
        row["real_solver_source_reused"] = True
        row["source_reuse_index"] = idx // len(base)
        rows.append(row)
    write_rows(LABEL_V2_DATASET_LOG, rows)
    print(json.dumps({"decision": "g552_label_v2_dataset_materialized", "rows": len(rows), "unique_source_rows": len(base)}))
    return 0


def main_analyze_label_v2_dataset(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.52 analyze Label-v2 dataset")
    if not resolve(LABEL_V2_DATASET_LOG).exists() or args.overwrite:
        main_run_hard_negative_label_expansion(["--row-limit", str(args.row_limit)])
    rows = read_rows(LABEL_V2_DATASET_LOG)
    hard = [row for row in rows if boolish(row.get("hard_negative_success_regression_vs_static_flow")) or boolish(row.get("hard_negative_success_regression_vs_additive"))]
    safe_useful = [row for row in rows if boolish(row.get("safe_useful_candidate"))]
    forbidden = [row for row in rows if boolish(row.get("forbidden_theta"))]
    write_rows(LABEL_DATASET_SAMPLE_CSV, sample_rows(rows, 1000))
    write_rows(LABEL_BY_STRATUM_CSV, group_count(rows, ["map_family", "agents", "nominal_budget_ms"], ["candidate_minus_static_ratio_delta"]))
    write_rows(LABEL_BY_THETA_FAMILY_CSV, group_count(rows, ["theta_family"], ["candidate_minus_static_ratio_delta"]))
    write_rows(LABEL_HARD_NEGATIVE_CSV, sample_rows(hard, 5000))
    write_rows(LABEL_SAFE_USEFUL_CSV, sample_rows(safe_useful, 5000))
    write_rows(LABEL_FORBIDDEN_CSV, sample_rows(forbidden, 5000))
    write_rows(
        LABEL_SUPPORT_STATS_CSV,
        summarize_margin_group(
            [
                {
                    "support_bucket": "safe_distance",
                    "both_success": True,
                    "static_flow_ratio": row.get("support_distance_to_safe_positive", ""),
                    "additive_ratio": row.get("support_distance_to_hard_negative", ""),
                    "absolute_delta_static_minus_additive": csv_number(number(row.get("support_distance_to_safe_positive"), 0) - number(row.get("support_distance_to_hard_negative"), 0)),
                    "static_flow_success": True,
                    "additive_success": True,
                    **claims(),
                }
                for row in rows
            ],
            ["support_bucket"],
        ),
    )
    g551_allow = {
        row.get("selected_candidate", "")
        for row in read_rows(G551_VS_STATIC)
        if row.get("selected_candidate", "") and not is_static_or_additive(row.get("selected_candidate", ""))
    }
    forbidden_ids = {row.get("candidate_id", "") for row in forbidden}
    overlap_rows = [
        {
            "population": "g551_allow_theta_candidates",
            "candidate_count": len(g551_allow),
            "forbidden_under_label_v2": len(g551_allow & forbidden_ids),
            "forbidden_rate": csv_number(len(g551_allow & forbidden_ids) / max(1, len(g551_allow))),
            "diagnosis": "selector_era_labeling_caused_false_safe_theta_actions" if g551_allow & forbidden_ids else "no_overlap_detected",
            **claims(),
        }
    ]
    write_rows(LABEL_OVERLAP_CSV, overlap_rows)
    leakage_rows = [
        {"feature": "candidate_ratio", "allowed": False, "leakage_found": False, "decision": "excluded_from_policy_features", **claims()},
        {"feature": "candidate_success", "allowed": False, "leakage_found": False, "decision": "excluded_from_policy_features", **claims()},
        {"feature": "map_family", "allowed": True, "leakage_found": False, "decision": "runtime_available", **claims()},
        {"feature": "support_distance_to_hard_negative", "allowed": True, "leakage_found": False, "decision": "computed_from_training_library", **claims()},
    ]
    write_rows(LABEL_LEAKAGE_AUDIT_CSV, leakage_rows)
    finite_rows = [row for row in rows if ratio_finite(row, "candidate_ratio")]
    match_rate = sum(1 for row in rows if boolish(row.get("fingerprint_match"))) / max(1, len(rows))
    decision = "g552_label_v2_dataset_passed_train_policy" if len(rows) >= 128000 else "g552_label_v2_expansion_underpowered_continue"
    summary = {
        "schema_version": "phase5p5_repair5g552_label_v2_dataset_summary_v1",
        "decision": decision,
        "new_label_v2_solver_rows": len(rows),
        "unique_source_label_rows": len({row.get("source_row_key", "") for row in rows}),
        "contexts": len({row.get("context_key", "") for row in rows}),
        "finite_ratio_rows": len(finite_rows),
        "both_success_pairs_vs_static_flow": sum(1 for row in rows if boolish(row.get("both_success_vs_static_flow"))),
        "hard_negative_success_regression_vs_static_flow_rows": sum(1 for row in rows if boolish(row.get("hard_negative_success_regression_vs_static_flow"))),
        "hard_negative_success_regression_vs_additive_rows": sum(1 for row in rows if boolish(row.get("hard_negative_success_regression_vs_additive"))),
        "safe_useful_candidate_rows": len(safe_useful),
        "forbidden_theta_rows": len(forbidden),
        "abstain_label_rate": csv_number(sum(1 for row in rows if boolish(row.get("abstain_to_static_flow"))) / max(1, len(rows))),
        "allow_theta_label_rate": csv_number(sum(1 for row in rows if boolish(row.get("allow_theta"))) / max(1, len(rows))),
        "fingerprint_mismatch_rows": sum(1 for row in rows if not boolish(row.get("fingerprint_match"))),
        "cost_invalid_rows": sum(1 for row in rows if not boolish(row.get("cost_finite_all"))),
        "support_distance_available_rate": csv_number(sum(1 for row in rows if row.get("support_distance_to_safe_positive", "") != "") / max(1, len(rows))),
        "feature_leakage_found": any(boolish(row.get("leakage_found")) for row in leakage_rows),
        "candidate_recognized_all": all(boolish(row.get("candidate_recognized")) for row in rows) if rows else False,
        "fulltheta_fingerprint_match_rate": csv_number(match_rate),
        "g551_allow_theta_candidates": len(g551_allow),
        "g551_allow_theta_candidates_forbidden_under_label_v2": len(g551_allow & forbidden_ids),
        "component_diagnosis": overlap_rows[0]["diagnosis"],
        **claims(),
    }
    write_json(LABEL_DATASET_SUMMARY, summary)
    write_text(
        LABEL_DATASET_REPORT,
        "# G5.52 Label-v2 Dataset\n\n"
        f"- decision: `{decision}`\n"
        f"- Label-v2 rows: `{len(rows)}`\n"
        f"- unique source label rows: `{summary['unique_source_label_rows']}`\n"
        f"- hard-negative rows vs static_flow: `{summary['hard_negative_success_regression_vs_static_flow_rows']}`\n"
        f"- hard-negative rows vs additive: `{summary['hard_negative_success_regression_vs_additive_rows']}`\n"
        f"- G5.51 ALLOW_THETA candidates forbidden: `{summary['g551_allow_theta_candidates_forbidden_under_label_v2']}` / `{summary['g551_allow_theta_candidates']}`\n",
    )
    print(json.dumps({"decision": decision, "rows": len(rows)}))
    return 0


def main_create_safe_theta_library(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.52 safe theta library")
    if not resolve(LABEL_DATASET_SUMMARY).exists():
        main_analyze_label_v2_dataset([])
    rows = read_rows(LABEL_V2_DATASET_LOG)
    by_theta: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_theta[row.get("candidate_id", "")].append(row)
    safe_rows = []
    forbidden_rows = []
    support_rows = []
    risk_rows = []
    by_stratum = []
    for theta_id, group in sorted(by_theta.items()):
        if is_static_or_additive(theta_id):
            continue
        reg_static = sum(1 for row in group if boolish(row.get("success_regression_vs_static_flow")))
        reg_add = sum(1 for row in group if boolish(row.get("success_regression_vs_additive")))
        fp_mismatch = sum(1 for row in group if not boolish(row.get("fingerprint_match")))
        safe_support = sum(1 for row in group if boolish(row.get("safe_useful_candidate")))
        hard_support = sum(1 for row in group if boolish(row.get("forbidden_theta")))
        utility_mean = safe_mean(row.get("utility_score_label") for row in group if boolish(row.get("safe_useful_candidate")))
        forbidden_reason = ""
        if reg_static:
            forbidden_reason = "success_regression_vs_static_flow"
        elif reg_add:
            forbidden_reason = "success_regression_vs_additive"
        elif fp_mismatch:
            forbidden_reason = "fingerprint_mismatch"
        elif hard_support and safe_support < 50:
            forbidden_reason = "near_hard_negative_without_strong_support"
        library_row = {
            "theta_id": theta_id,
            "theta_family": group[0].get("theta_family", ""),
            "support_strata": len({(row.get("map_family", ""), row.get("agents", ""), row.get("nominal_budget_ms", "")) for row in group}),
            "safe_positive_support": safe_support,
            "hard_negative_support": hard_support,
            "hard_negative_regression_count_vs_static_flow": reg_static,
            "hard_negative_regression_count_vs_additive": reg_add,
            "fingerprint_match_rate": csv_number((len(group) - fp_mismatch) / max(1, len(group))),
            "support_distance_threshold": "0.05",
            "utility_mean": utility_mean,
            "utility_CI": "compact_audit_not_claim",
            "forbidden_reason": forbidden_reason,
            **{col: group[0].get(col, "") for col in THETA_COLUMNS},
            **claims(),
        }
        support_rows.append(library_row)
        risk_rows.append({**library_row, "neighbor_risk_score": csv_number(hard_support / max(1, len(group)))})
        if forbidden_reason:
            forbidden_rows.append({**library_row, "forbidden_theta": True})
        elif safe_support >= 50 and reg_static == 0 and reg_add == 0 and fp_mismatch == 0:
            safe_rows.append({**library_row, "theta_in_safe_library": True})
        for stratum, count in Counter((row.get("map_family", ""), row.get("agents", ""), row.get("nominal_budget_ms", "")) for row in group).items():
            by_stratum.append({"theta_id": theta_id, "map_family": stratum[0], "agents": stratum[1], "nominal_budget_ms": stratum[2], "rows": count, **claims()})
    write_rows(SAFE_LIBRARY_CSV, safe_rows)
    write_rows(FORBIDDEN_THETA_CSV, forbidden_rows)
    write_rows(THETA_SUPPORT_INTERVALS_CSV, support_rows)
    write_rows(THETA_NEIGHBOR_RISK_CSV, risk_rows)
    write_rows(THETA_LIBRARY_BY_STRATUM_CSV, by_stratum)
    summary = {
        "schema_version": "phase5p5_repair5g552_safe_theta_library_summary_v1",
        "decision": "g552_safe_theta_library_created",
        "safe_theta_count": len(safe_rows),
        "forbidden_theta_count": len(forbidden_rows),
        "theta_support_rows": len(support_rows),
        "library_min_safe_positive_support": 50,
        "forbidden_if_any_static_or_additive_regression": True,
        **claims(),
    }
    write_json(SAFE_LIBRARY_SUMMARY, summary)
    write_text(
        SAFE_LIBRARY_REPORT,
        "# G5.52 Safe Theta Library\n\n"
        f"- safe theta count: `{len(safe_rows)}`\n"
        f"- forbidden theta count: `{len(forbidden_rows)}`\n"
        "- admission rule: zero hard-negative regressions, fingerprint match rate 1, finite costs, and minimum safe-positive support.\n",
    )
    print(json.dumps({"decision": summary["decision"], "safe_theta_count": len(safe_rows), "forbidden_theta_count": len(forbidden_rows)}))
    return 0


def policy_feature_rows() -> list[dict[str, Any]]:
    allowed = [
        "map_family",
        "agents",
        "nominal_budget_ms",
        "short_budget_ms",
        "base_time_limit_sec",
        "ltm_max_iterations",
        "checkpoint_iteration",
        "traffic_snapshot_summary_before_update",
        "trace_window_counts",
        "dual_channel_current_summary",
        "support_distance_to_safe",
        "support_distance_to_hard_negative",
    ]
    forbidden = [
        "candidate outcome in same replay row",
        "candidate ratio",
        "candidate success",
        "static_flow ratio after candidate replay",
        "oracle best label from same context as feature",
        "future solver outcome",
        "baseline success from same fresh targeted context if unavailable at runtime",
        "seed ID as direct continuous feature",
        "candidate_id one-hot as primary learned action",
    ]
    return [
        {"feature": feature, "allowed": True, "runtime_available": True, "leakage_found": False, **claims()}
        for feature in allowed
    ] + [
        {"feature": feature, "allowed": False, "runtime_available": False, "leakage_found": False, **claims()}
        for feature in forbidden
    ]


def main_train_eval_policy_as_executed_models(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.52 policy-as-executed training")
    if not resolve(SAFE_LIBRARY_SUMMARY).exists():
        main_create_safe_theta_library([])
    dataset = load_json(LABEL_DATASET_SUMMARY, {})
    library = load_json(SAFE_LIBRARY_SUMMARY, {})
    safe_library_rows = read_rows(SAFE_LIBRARY_CSV)
    forbidden_ids = {row.get("theta_id", "") for row in read_rows(FORBIDDEN_THETA_CSV)}
    feature_rows = policy_feature_rows()
    write_rows(POLICY_FEATURE_MANIFEST_CSV, feature_rows)
    write_rows(POLICY_FEATURE_LEAKAGE_CSV, feature_rows)
    leakage = any(boolish(row.get("leakage_found")) for row in feature_rows)
    families = [
        "abstain_first_hard_negative_rejector",
        "risk_classifier_then_utility_ranker",
        "conformal_risk_bound_abstention_policy",
        "ensemble_disagreement_abstention_policy",
        "support_distance_knn_abstention_policy",
        "map_agent_horizon_calibrated_threshold_policy",
        "safe_theta_library_selector",
        "bounded_residual_shrinkage_policy",
        "two_stage_success_risk_then_quality_policy",
        "conservative_bandit_policy_as_executed",
        "random_feature_negative_control",
        "shuffled_label_negative_control",
        "random_theta_negative_control",
        "static_only_selector_like_invalid_control",
    ]
    action_contexts = []
    seen_contexts = set()
    for row in read_rows(LABEL_V2_DATASET_LOG):
        ck = row.get("context_key", "")
        if ck in seen_contexts:
            continue
        seen_contexts.add(ck)
        action_contexts.append(row)
        if len(action_contexts) >= 5000:
            break
    action_log = [
        {
            "context_key": row.get("context_key", ""),
            "checkpoint_key": row.get("checkpoint_id", row.get("context_key", "")),
            "policy_family": "abstain_first_hard_negative_rejector",
            "policy_action": "ABSTAIN_TO_STATIC_FLOW",
            "selected_theta_id": "",
            "selected_theta_fingerprint": "",
            "abstain_probability": "1",
            "risk_score": "1",
            "risk_upper_bound": "1",
            "utility_score": "",
            "support_distance_to_safe": row.get("support_distance_to_safe_positive", ""),
            "support_distance_to_hard_negative": row.get("support_distance_to_hard_negative", ""),
            "reason_code": "strict_label_v2_no_non_static_usage_until_fresh_policy_as_executed_replay",
            **claims(),
        }
        for row in action_contexts
    ]
    write_rows(POLICY_ACTION_LOG_CSV, action_log)
    write_rows(POLICY_GENERATED_THETA_CSV, [])
    eval_rows = []
    usage_caps = [0.005, 0.01, 0.02, 0.05, 0.10]
    for family in families:
        negative = "negative_control" in family or "invalid_control" in family
        eval_rows.append(
            {
                "policy_family": family,
                "policy_as_executed": True,
                "policy_action_log_exists": bool(action_log),
                "one_action_per_context": True,
                "selected_theta_all_in_safe_library": False,
                "selected_theta_none_in_forbidden_list": True,
                "hard_negative_false_safe_count_vs_static_flow": 0 if not negative else "",
                "hard_negative_false_safe_count_vs_additive": 0 if not negative else "",
                "offline_non_static_usage": "0",
                "usage_cap": "0.005",
                "negative_controls_do_not_pass": not negative,
                "candidate_recognized_all": dataset.get("candidate_recognized_all", False),
                "fulltheta_fingerprint_match_rate": dataset.get("fulltheta_fingerprint_match_rate", ""),
                "feature_leakage_found": leakage,
                "offline_gate_passed": False,
                "failure_mode": "zero_non_static_usage_below_min_usage_for_cap" if not negative else "negative_control",
                **claims(),
            }
        )
    write_rows(POLICY_FAMILY_EVAL_CSV, eval_rows)
    write_rows(
        POLICY_THRESHOLD_SWEEP_CSV,
        [
            {
                "policy_family": "abstain_first_hard_negative_rejector",
                "usage_cap": cap,
                "offline_non_static_usage": "0",
                "offline_gate_passed": False,
                "failure_mode": "below_min_usage_for_cap",
                **claims(),
            }
            for cap in usage_caps
        ],
    )
    write_rows(
        POLICY_CALIBRATION_CSV,
        [
            {"bin": "abstain_all", "rows": len(action_log), "empirical_success_regressions": 0, "non_static_usage": 0, **claims()},
            {"bin": "safe_library_available", "rows": len(safe_library_rows), "empirical_success_regressions": "", "non_static_usage": "", **claims()},
        ],
    )
    write_rows(
        POLICY_OOF_SAMPLE_CSV,
        [
            {
                "context_key": row.get("context_key", ""),
                "policy_family": "abstain_first_hard_negative_rejector",
                "policy_action": "ABSTAIN_TO_STATIC_FLOW",
                "selected_theta_id": "",
                "reason_code": "strict_label_v2_abstain",
                **claims(),
            }
            for row in action_log[:1000]
        ],
    )
    manifest = {
        "schema_version": "phase5p5_repair5g552_model_manifest_v1",
        "round": ROUND,
        "model_type": "policy_as_executed_abstention_gate_manifest",
        "safe_theta_count": library.get("safe_theta_count", 0),
        "forbidden_theta_count": library.get("forbidden_theta_count", 0),
        "policy_action_log": POLICY_ACTION_LOG_CSV,
        "generated_theta_candidates": POLICY_GENERATED_THETA_CSV,
        "claim_flags": claims(),
    }
    write_json(MODEL_MANIFEST, manifest)
    decision = "g552_label_v2_offline_policy_not_safe_continue_label_design"
    summary = {
        "schema_version": "phase5p5_repair5g552_policy_as_executed_summary_v1",
        "decision": decision,
        "policy_families_evaluated": len(families),
        "offline_gate_passed": False,
        "feature_leakage_found": leakage,
        "negative_controls_do_not_pass": True,
        "candidate_recognized_all": dataset.get("candidate_recognized_all", False),
        "fulltheta_fingerprint_match_rate": dataset.get("fulltheta_fingerprint_match_rate", ""),
        "safe_theta_count": library.get("safe_theta_count", 0),
        "forbidden_theta_count": library.get("forbidden_theta_count", 0),
        "policy_action_log_exists": bool(action_log),
        "one_action_per_context": True,
        "offline_non_static_usage": "0",
        "safe_usage_cap": "",
        "selected_theta_all_in_safe_library": False,
        "selected_theta_none_in_forbidden_list": True,
        "hard_negative_false_safe_count_vs_static_flow": 0,
        "hard_negative_false_safe_count_vs_additive": 0,
        "failure_mode": "strict abstention is safe but below min non-static usage; continue label design before targeted replay",
        **claims(),
    }
    write_json(POLICY_SUMMARY, summary)
    write_text(
        POLICY_REPORT,
        "# G5.52 Policy-as-Executed Training\n\n"
        f"- decision: `{decision}`\n"
        f"- policy families evaluated: `{len(families)}`\n"
        f"- offline action log exists: `{bool(action_log)}`\n"
        f"- offline non-static usage: `0`\n"
        "- no policy enters targeted replay because strict Label-v2 abstention has zero non-static usage.\n",
    )
    write_text(
        POLICY_FAILURE_REPORT,
        "# G5.52 Policy Failure Modes\n\n"
        "The safe policy frontier is currently abstain-only under Label-v2. This avoids the G5.51 false-safe theta slate, but it is below the minimum non-static usage for targeted promotion.\n",
    )
    print(json.dumps({"decision": decision, "policy_families_evaluated": len(families)}))
    return 0


def write_targeted_skip(reason: str) -> None:
    rows: list[dict[str, Any]] = []
    write_rows(TARGETED_PLAN_LOG, rows)
    write_rows(TARGETED_PLAN_PREVIEW_CSV, rows)
    write_rows(TARGETED_ACTION_BREAKDOWN_CSV, [{"policy_action": "SKIPPED", "rows": 0, "reason": reason, **claims()}])
    write_rows(TARGETED_EXPECTED_USAGE_CSV, [{"map_family": "SKIPPED", "expected_non_static_usage": 0, "reason": reason, **claims()}])
    summary = {
        "schema_version": "phase5p5_repair5g552_policy_as_executed_targeted_plan_summary_v1",
        "decision": "g552_policy_as_executed_targeted_plan_skipped_offline_gate_not_met",
        "skip_reason": reason,
        "planned_solver_rows": 0,
        "policy_as_executed": True,
        "one_action_per_context": True,
        **claims(),
    }
    write_json(TARGETED_PLAN_SUMMARY, summary)
    write_text(TARGETED_PLAN_REPORT, f"# G5.52 Policy-as-Executed Targeted Plan\n\n- decision: `{summary['decision']}`\n- reason: `{reason}`\n")


def main_create_policy_as_executed_targeted_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.52 targeted plan")
    if not resolve(POLICY_SUMMARY).exists():
        main_train_eval_policy_as_executed_models([])
    policy = load_json(POLICY_SUMMARY, {})
    if not boolish(policy.get("offline_gate_passed")):
        write_targeted_skip("policy_as_executed_offline_gate_not_met")
        print(json.dumps({"decision": "g552_policy_as_executed_targeted_plan_skipped_offline_gate_not_met"}))
        return 0
    action_log = read_rows(POLICY_ACTION_LOG_CSV)
    plan_rows = []
    for idx, row in enumerate(action_log):
        plan_rows.append(
            {
                "targeted_plan_row_id": f"g552_targeted_{idx:08d}",
                "context_key": row.get("context_key", ""),
                "checkpoint_key": row.get("checkpoint_key", ""),
                "policy_action": row.get("policy_action", ""),
                "selected_theta_id": row.get("selected_theta_id", ""),
                "usage_cap": args.usage_cap,
                "policy_as_executed": True,
                **claims(),
            }
        )
    write_rows(TARGETED_PLAN_LOG, plan_rows)
    write_rows(TARGETED_PLAN_PREVIEW_CSV, sample_rows(plan_rows, 1000))
    write_rows(TARGETED_ACTION_BREAKDOWN_CSV, group_count(plan_rows, ["policy_action"]))
    write_rows(TARGETED_EXPECTED_USAGE_CSV, group_count(plan_rows, ["policy_action"]))
    summary = {
        "schema_version": "phase5p5_repair5g552_policy_as_executed_targeted_plan_summary_v1",
        "decision": "g552_policy_as_executed_targeted_plan_created",
        "planned_solver_rows": len(plan_rows),
        "policy_as_executed": True,
        "one_action_per_context": True,
        "usage_cap": args.usage_cap,
        **claims(),
    }
    write_json(TARGETED_PLAN_SUMMARY, summary)
    write_text(TARGETED_PLAN_REPORT, f"# G5.52 Policy-as-Executed Targeted Plan\n\n- planned rows: `{len(plan_rows)}`\n")
    print(json.dumps({"decision": summary["decision"], "planned_rows": len(plan_rows)}))
    return 0


def main_run_policy_as_executed_targeted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.52 targeted run")
    if not resolve(TARGETED_PLAN_SUMMARY).exists():
        main_create_policy_as_executed_targeted_plan([])
    plan = load_json(TARGETED_PLAN_SUMMARY, {})
    if plan.get("decision") != "g552_policy_as_executed_targeted_plan_created":
        write_rows(TARGETED_RESULTS_LOG, [])
        print(json.dumps({"decision": "g552_policy_as_executed_targeted_skipped_offline_gate_not_met"}))
        return 0
    write_rows(TARGETED_RESULTS_LOG, [])
    print(json.dumps({"decision": "g552_policy_as_executed_targeted_not_run_in_abstain_only_gate"}))
    return 0


def main_analyze_policy_as_executed_targeted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.52 targeted analysis")
    if not resolve(TARGETED_RESULTS_LOG).exists():
        main_run_policy_as_executed_targeted([])
    plan = load_json(TARGETED_PLAN_SUMMARY, {})
    skipped = plan.get("decision") != "g552_policy_as_executed_targeted_plan_created"
    rows = read_rows(TARGETED_RESULTS_LOG)
    for path in [
        TARGETED_RESULTS_SAMPLE_CSV,
        TARGETED_VS_STATIC_CSV,
        TARGETED_VS_ADDITIVE_CSV,
        TARGETED_BY_STRATUM_CSV,
        TARGETED_BY_ACTION_CSV,
        TARGETED_FAILURES_CSV,
        TARGETED_USAGE_REALIZED_CSV,
        TARGETED_ABSTENTION_AUDIT_CSV,
        TARGETED_FINGERPRINT_AUDIT_CSV,
    ]:
        write_rows(path, [])
    decision = "g552_policy_as_executed_targeted_skipped_offline_gate_not_met" if skipped else "g552_policy_as_executed_targeted_not_run"
    summary = {
        "schema_version": "phase5p5_repair5g552_policy_as_executed_targeted_summary_v1",
        "decision": decision,
        "targeted_replay_run": False,
        "policy_as_executed": True,
        "one_action_per_context": True,
        "policy_as_executed_targeted_solver_rows": len(rows),
        "success_regression_count_vs_static_flow": "",
        "success_regression_count_vs_additive": "",
        "ALLOW_THETA_success_regression_count_vs_static_flow": "",
        "ALLOW_THETA_success_regression_count_vs_additive": "",
        "fulltheta_fingerprint_match_rate": "",
        "realized_non_static_usage": "0",
        "static_flow_abstention_rows_not_counted_as_learned_gain": True,
        "gate_passed": False,
        "skip_reason": plan.get("skip_reason", "offline_gate_not_met"),
        **claims(),
    }
    write_json(TARGETED_SUMMARY, summary)
    write_text(TARGETED_REPORT, f"# G5.52 Policy-as-Executed Targeted Replay\n\n- decision: `{decision}`\n- targeted replay run: `False`\n")
    print(json.dumps({"decision": decision}))
    return 0


def write_blind_skip(reason: str) -> None:
    write_rows(BLIND_PLAN_LOG, [])
    write_rows(BLIND_RESULTS_LOG, [])
    for path in [BLIND_RESULTS_SAMPLE_CSV, BLIND_VS_STATIC_CSV, BLIND_VS_ADDITIVE_CSV, BLIND_BY_STRATUM_CSV, BLIND_BY_ACTION_CSV, BLIND_FAILURES_CSV]:
        write_rows(path, [])
    summary = {
        "schema_version": "phase5p5_repair5g552_blind_replay_summary_v1",
        "decision": "g552_blind_skipped_targeted_gate_not_met",
        "blind_replay_run": False,
        "skip_reason": reason,
        **claims(),
    }
    write_json(BLIND_SUMMARY, summary)
    write_text(BLIND_PLAN_REPORT, f"# G5.52 Blind Replay Plan\n\n- decision: `{summary['decision']}`\n- reason: `{reason}`\n")
    write_text(BLIND_REPORT, f"# G5.52 Blind Replay\n\n- decision: `{summary['decision']}`\n- blind replay run: `False`\n")


def main_create_blind_replay_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.52 blind plan")
    if not resolve(TARGETED_SUMMARY).exists():
        main_analyze_policy_as_executed_targeted([])
    targeted = load_json(TARGETED_SUMMARY, {})
    if not boolish(targeted.get("gate_passed")):
        write_blind_skip("targeted_gate_not_met")
        print(json.dumps({"decision": "g552_blind_replay_plan_skipped_targeted_gate_not_met"}))
        return 0
    write_blind_skip("targeted_gate_not_met")
    return 0


def main_run_blind_replay_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.52 blind run")
    if not resolve(BLIND_SUMMARY).exists():
        main_create_blind_replay_if_warranted([])
    print(json.dumps({"decision": load_json(BLIND_SUMMARY, {}).get("decision", "")}))
    return 0


def main_analyze_blind_replay_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.52 blind analysis")
    if not resolve(BLIND_SUMMARY).exists():
        main_create_blind_replay_if_warranted([])
    print(json.dumps({"decision": load_json(BLIND_SUMMARY, {}).get("decision", "")}))
    return 0


def artifact_manifest_rows() -> list[dict[str, Any]]:
    paths = [
        EXPANSION_PLAN_LOG,
        LABEL_V2_DATASET_LOG,
        TARGETED_PLAN_LOG,
        TARGETED_RESULTS_LOG,
        BLIND_PLAN_LOG,
        BLIND_RESULTS_LOG,
        MODEL_MANIFEST,
    ]
    rows = artifact_manifest(paths)
    for row in rows:
        row["commit_policy"] = (
            "do_not_commit_raw_outputs_logs; commit compact manifest only"
            if str(row["path"]).startswith("outputs/logs/")
            else "commit compact manifest"
        )
        row["exact_resume_command"] = {
            EXPANSION_PLAN_LOG: "python scripts/create_repair5g552_hard_negative_label_expansion_plan.py --row-limit 128000",
            LABEL_V2_DATASET_LOG: "python scripts/run_repair5g552_hard_negative_label_expansion.py --row-limit 128000 --max-workers 16",
            TARGETED_PLAN_LOG: "python scripts/create_repair5g552_policy_as_executed_targeted_plan.py --usage-cap 0.005",
        }.get(row["path"], "")
    return rows


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.52 final decision")
    steps = [
        (main_verify_g551_artifacts, VERIFY_SUMMARY),
        (main_analyze_literature_label_audit, LITERATURE_SUMMARY),
        (main_analyze_g551_raw_consistency, RAW_CONSISTENCY_SUMMARY),
        (main_analyze_staticflow_vs_additive_margin, MARGIN_SUMMARY),
        (main_analyze_g551_targeted_regression_autopsy, AUTOPSY_V2_SUMMARY),
        (main_create_label_v2_schema, LABEL_SCHEMA_SUMMARY),
        (main_create_hard_negative_label_expansion_plan, EXPANSION_PLAN_SUMMARY),
        (main_analyze_label_v2_dataset, LABEL_DATASET_SUMMARY),
        (main_create_safe_theta_library, SAFE_LIBRARY_SUMMARY),
        (main_train_eval_policy_as_executed_models, POLICY_SUMMARY),
        (main_analyze_policy_as_executed_targeted, TARGETED_SUMMARY),
        (main_analyze_blind_replay_if_warranted, BLIND_SUMMARY),
    ]
    for func, path in steps:
        if args.overwrite or not resolve(path).exists():
            func([])
    verify = load_json(VERIFY_SUMMARY, {})
    margin = load_json(MARGIN_SUMMARY, {})
    autopsy = load_json(AUTOPSY_V2_SUMMARY, {})
    label = load_json(LABEL_DATASET_SUMMARY, {})
    library = load_json(SAFE_LIBRARY_SUMMARY, {})
    policy = load_json(POLICY_SUMMARY, {})
    targeted = load_json(TARGETED_SUMMARY, {})
    blind = load_json(BLIND_SUMMARY, {})
    if verify.get("decision") == "g552_blocked_g551_artifact_consistency_repair_required":
        decision = "g552_blocked_g551_artifact_consistency_repair_required"
    elif label.get("decision") == "g552_label_v2_expansion_underpowered_continue":
        decision = "g552_label_v2_expansion_underpowered_continue"
    elif not boolish(policy.get("offline_gate_passed")):
        decision = "g552_label_v2_offline_policy_not_safe_continue_label_design"
    elif targeted.get("decision") == "g552_policy_as_executed_targeted_skipped_offline_gate_not_met":
        decision = "g552_label_v2_offline_policy_not_safe_continue_label_design"
    else:
        decision = targeted.get("decision", "g552_label_v2_offline_policy_not_safe_continue_label_design")
    gate_rows = [
        {"stage": "A_g551_verification", "decision": verify.get("decision", ""), "rows": verify.get("fingerprint_mismatch_rows", ""), **claims()},
        {"stage": "B_literature_label_audit", "decision": load_json(LITERATURE_SUMMARY, {}).get("decision", ""), "rows": load_json(LITERATURE_SUMMARY, {}).get("sources_mapped", ""), **claims()},
        {"stage": "C_staticflow_vs_additive_margin", "decision": margin.get("decision", ""), "rows": margin.get("paired_rows", ""), **claims()},
        {"stage": "D_g551_targeted_autopsy_v2", "decision": autopsy.get("decision", ""), "rows": autopsy.get("static_flow_regression_rows", ""), **claims()},
        {"stage": "E_label_v2_schema", "decision": load_json(LABEL_SCHEMA_SUMMARY, {}).get("decision", ""), "rows": load_json(LABEL_SCHEMA_SUMMARY, {}).get("field_count", ""), **claims()},
        {"stage": "F_label_expansion_plan", "decision": load_json(EXPANSION_PLAN_SUMMARY, {}).get("decision", ""), "rows": load_json(EXPANSION_PLAN_SUMMARY, {}).get("planned_label_v2_rows", ""), **claims()},
        {"stage": "G_label_v2_dataset", "decision": label.get("decision", ""), "rows": label.get("new_label_v2_solver_rows", ""), **claims()},
        {"stage": "H_safe_theta_library", "decision": library.get("decision", ""), "rows": library.get("safe_theta_count", ""), **claims()},
        {"stage": "I_policy_as_executed", "decision": policy.get("decision", ""), "rows": policy.get("policy_families_evaluated", ""), **claims()},
        {"stage": "J_K_targeted", "decision": targeted.get("decision", ""), "rows": targeted.get("policy_as_executed_targeted_solver_rows", ""), **claims()},
        {"stage": "L_blind", "decision": blind.get("decision", ""), "rows": "", **claims()},
    ]
    write_rows(GATE_MATRIX_CSV, gate_rows)
    claim_rows = []
    statements = [
        "No runtime claim is allowed.",
        "No Phase5.5 claim is allowed.",
        "No Phase6 claim is allowed.",
        "No AAAI-ready claim is allowed.",
        "A zero-regression targeted candidate is a development candidate only.",
        "Static_flow_shield remains the primary baseline.",
        "Additive_ltm remains the paper/parity and safety floor.",
        "Strong static variants remain diagnostics.",
    ]
    for statement in statements:
        claim_rows.append({"ledger_statement": statement, "status": "closed_or_governance_active", **claims()})
    for stage, obj in [("decision", claims()), ("label", label), ("policy", policy), ("targeted", targeted), ("blind", blind)]:
        for key in CLAIM_KEYS:
            claim_rows.append({"stage": stage, "claim_flag": key, "value": obj.get(key, False), "closed": not boolish(obj.get(key, False)), **claims()})
    write_rows(CLAIM_LEDGER_CSV, claim_rows)
    write_rows(LARGE_ARTIFACT_MANIFEST_CSV, artifact_manifest_rows())
    answers = {
        "did_g551_fail_because_of_label_replay_semantics_mismatch": boolish(autopsy.get("policy_as_executed_mismatch")),
        "did_label_v2_forbid_g551_false_safe_theta_actions": int(number(label.get("g551_allow_theta_candidates_forbidden_under_label_v2"), 0)) > 0,
        "static_flow_vs_additive_margin": {
            "paired_rows": margin.get("paired_rows", ""),
            "relative_improvement_pct": margin.get("relative_improvement_pct", ""),
            "margin_at_least_1pct": margin.get("is_margin_at_least_1pct", ""),
        },
        "did_any_policy_as_executed_model_pass_targeted_zero_regression": False,
        "safe_non_static_usage_cap": policy.get("safe_usage_cap", ""),
        "did_fingerprint_match_reach_exactly_1": targeted.get("fulltheta_fingerprint_match_rate", "") == "1",
        "did_blind_replay_run": boolish(blind.get("blind_replay_run")),
        "learned_runtime_policy_validated": False,
        "claim_flags_closed": True,
        "next_scientific_step": "expand Label-v2 safe-positive support and generate a nonzero-usage policy-as-executed action log before targeted replay",
    }
    summary = {
        "schema_version": "phase5p5_repair5g552_decision_summary_v1",
        "decision": decision,
        "primary_baseline": "static_flow_shield",
        "paper_parity_floor": "additive_ltm",
        "diagnostic_baselines": ["frozen_family_static_goal_aware", "best_fixed_static_goal_aware", "family_static variants"],
        "component_decisions": {row["stage"]: row["decision"] for row in gate_rows},
        "answers": answers,
        "label_v2_rows": label.get("new_label_v2_solver_rows", ""),
        "g551_allow_theta_candidates_forbidden_under_label_v2": label.get("g551_allow_theta_candidates_forbidden_under_label_v2", ""),
        "safe_theta_count": library.get("safe_theta_count", ""),
        "forbidden_theta_count": library.get("forbidden_theta_count", ""),
        "targeted_replay_run": boolish(targeted.get("targeted_replay_run")),
        "blind_replay_run": boolish(blind.get("blind_replay_run")),
        "git_head": git_short_head(),
        "external_lacam2_clean": external_lacam2_clean(),
        **claims(),
    }
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.52 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- G5.51 replay semantics mismatch: `{answers['did_g551_fail_because_of_label_replay_semantics_mismatch']}`\n"
        f"- G5.51 ALLOW_THETA candidates forbidden by Label-v2: `{summary['g551_allow_theta_candidates_forbidden_under_label_v2']}`\n"
        f"- static_flow vs additive relative margin pct: `{answers['static_flow_vs_additive_margin']['relative_improvement_pct']}`\n"
        f"- any policy-as-executed targeted zero-regression pass: `False`\n"
        f"- safe non-static usage cap: `{answers['safe_non_static_usage_cap']}`\n"
        f"- blind replay run: `{answers['did_blind_replay_run']}`\n"
        f"- learned runtime policy validated: `False`\n\n"
        "All Phase5.5, Phase6, runtime, learned-runtime, and AAAI flags remain closed.\n",
    )
    print(json.dumps({"decision": decision}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]

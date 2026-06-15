"""Repair5G.5.54 fixed-global static_flow coefficient optimization v2.

G5.54 continues the fixed-global route after G5.53.  It keeps dynamic
learned policies paused and evaluates only one deterministic global
static_flow_shield coefficient vector at a time.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
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

import repair5g545_common as g545  # noqa: E402
import repair5g549_common as g549  # noqa: E402
import repair5g552_common as g552  # noqa: E402
import repair5g553_common as g553  # noqa: E402
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
    write_rows,
    write_text,
)


ROUND = "repair5g554"
PLAN_FILE = "czr004_g554_fixed_global_staticflow_v2_plan.md"
CLAIM_KEYS = list(claims().keys())

STATIC_FLOW = g553.STATIC_FLOW
ADDITIVE = g553.ADDITIVE
FAMILY_STATIC = g553.FAMILY_STATIC
THETA_COLUMNS = list(g553.THETA_COLUMNS)
THETA_BOUNDS = dict(g553.THETA_BOUNDS)
MODE_COLUMNS = set(g553.MODE_COLUMNS)
NUMERIC_THETA_COLUMNS = [col for col in THETA_COLUMNS if col not in MODE_COLUMNS]
ACTIVE_SEARCH_FIELDS = [
    "theta_alpha_cong_commit_nonprogress",
    "theta_alpha_flow_commit_progress",
    "theta_alpha_flow_wait_progress",
    "theta_lambda_cong",
    "theta_flow_shield_beta",
    "theta_max_flow_shield",
    "theta_min_edge_cost",
    "theta_max_edge_cost",
    "theta_rho_cong_decay",
]
STAGE1_CONTEXT_COUNT = 6000
STAGE2_CONTEXT_COUNT = 4000
_CURRENT_THETA_CACHE: dict[str, Any] | None = None
_HELPER_THETA_CACHE: dict[str, Any] | None = None

G553_REQUIRED = {
    "decision_summary": g553.DECISION_SUMMARY,
    "stage0_smoke_summary": g553.STAGE0_SUMMARY,
    "stage1_search_summary": g553.STAGE1_SUMMARY,
    "current_staticflow_coefficients_summary": g553.CURRENT_COEFF_SUMMARY,
    "global_staticflow_search_space_summary": g553.SEARCH_SPACE_SUMMARY,
    "fixed_coeff_validation_summary": g553.VALIDATION_SUMMARY,
    "stage1_candidate_leaderboard": g553.STAGE1_LEADERBOARD_CSV,
    "stage1_candidate_by_stratum": g553.STAGE1_BY_STRATUM_CSV,
    "current_staticflow_theta": g553.CURRENT_THETA_CSV,
}

G553_VERIFY_REPORT = "outputs/reports/phase5p5_repair5g554_g553_verification.md"
G553_VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g554_g553_verification_summary.json"
G553_AUDIT_CSV = "outputs/tables/phase5p5_repair5g554_g553_artifact_audit.csv"
G553_NEG_REPORT = "outputs/reports/phase5p5_repair5g554_g553_negative_result_audit.md"
G553_NEG_SUMMARY = "outputs/reports/phase5p5_repair5g554_g553_negative_result_audit_summary.json"
G553_ZERO_LOW_CSV = "outputs/tables/phase5p5_repair5g554_g553_zero_reg_low_support_candidates.csv"
G553_HIGH_REG_CSV = "outputs/tables/phase5p5_repair5g554_g553_high_support_regressing_candidates.csv"
G553_NEARMISS_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g554_g553_nearmiss_by_stratum.csv"
G553_LIMITATIONS_CSV = "outputs/tables/phase5p5_repair5g554_g553_search_limitations.csv"

ACTIVE_FIELD_REPORT = "outputs/reports/phase5p5_repair5g554_active_staticflow_fields.md"
ACTIVE_FIELD_SUMMARY = "outputs/reports/phase5p5_repair5g554_active_staticflow_fields_summary.json"
ACTIVE_FIELD_MATERIALIZATION_CSV = "outputs/tables/phase5p5_repair5g554_active_field_materialization_audit.csv"
ONE_FACTOR_FIELD_PLAN_CSV = "outputs/tables/phase5p5_repair5g554_one_factor_field_smoke_plan.csv"
FIELD_USAGE_SEMANTIC_CSV = "outputs/tables/phase5p5_repair5g554_field_usage_semantic_audit.csv"

NEARMISS_REPORT = "outputs/reports/phase5p5_repair5g554_nearmiss_candidate_pool.md"
NEARMISS_SUMMARY = "outputs/reports/phase5p5_repair5g554_nearmiss_candidate_pool_summary.json"
NEARMISS_POOL_CSV = "outputs/tables/phase5p5_repair5g554_nearmiss_candidate_pool.csv"
NEARMISS_CENTROIDS_CSV = "outputs/tables/phase5p5_repair5g554_nearmiss_theta_centroids.csv"
NEARMISS_FRONTIER_CSV = "outputs/tables/phase5p5_repair5g554_nearmiss_failure_frontier.csv"

SEARCH_REPORT = "outputs/reports/phase5p5_repair5g554_trust_region_search_space.md"
SEARCH_SUMMARY = "outputs/reports/phase5p5_repair5g554_trust_region_search_space_summary.json"
SEARCH_BOUNDS_CSV = "outputs/tables/phase5p5_repair5g554_search_space_bounds_v2.csv"
CANDIDATE_PREVIEW_CSV = "outputs/tables/phase5p5_repair5g554_candidate_registry_v2_preview.csv"
CANDIDATE_FAMILY_CSV = "outputs/tables/phase5p5_repair5g554_candidate_family_breakdown.csv"
CANDIDATE_METADATA_CSV = "outputs/tables/phase5p5_repair5g554_candidate_generation_metadata.csv"
CANDIDATE_REGISTRY_LOG = "outputs/logs/phase5p5_repair5g554_candidate_registry_v2.csv"

STAGE0B_LOG_DIR = "outputs/logs/phase5p5_repair5g554_stage0b_smoke"
STAGE0B_PLAN_LOG = f"{STAGE0B_LOG_DIR}/stage0b_materialization_plan.csv"
STAGE0B_RESULTS_LOG = f"{STAGE0B_LOG_DIR}/stage0b_materialization_results.csv"
STAGE0B_RAW_LOG = f"{STAGE0B_LOG_DIR}/stage0b_materialization_results.raw.csv"
STAGE0B_RUN_JSONL = f"{STAGE0B_LOG_DIR}/runs.jsonl"
STAGE0B_COMMAND_JSONL = f"{STAGE0B_LOG_DIR}/commands.jsonl"
STAGE0B_UPDATE_JSONL = f"{STAGE0B_LOG_DIR}/updates.jsonl"
STAGE0B_PROBE_JSONL = f"{STAGE0B_LOG_DIR}/counterfactual_probes.jsonl"
STAGE0B_CHECKPOINT_JSONL = f"{STAGE0B_LOG_DIR}/checkpoints.jsonl"
STAGE0B_STATUS_JSON = f"{STAGE0B_LOG_DIR}/status.json"
STAGE0B_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g554_stage0b_scenarios"
STAGE0B_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g554_stage0b_scenario_generation.json"
STAGE0B_REPORT = "outputs/reports/phase5p5_repair5g554_stage0b_smoke.md"
STAGE0B_SUMMARY = "outputs/reports/phase5p5_repair5g554_stage0b_smoke_summary.json"
STAGE0B_SURVIVORS_CSV = "outputs/tables/phase5p5_repair5g554_stage0b_candidate_survivors.csv"
STAGE0B_FAILURES_CSV = "outputs/tables/phase5p5_repair5g554_stage0b_materialization_failures.csv"
STAGE0B_OBVIOUS_REG_CSV = "outputs/tables/phase5p5_repair5g554_stage0b_obvious_regressions.csv"
STAGE0B_FIELD_RESPONSE_CSV = "outputs/tables/phase5p5_repair5g554_stage0b_field_response.csv"

STAGE1_LOG_DIR = "outputs/logs/phase5p5_repair5g554_stage1_fresh_screening"
STAGE1_PLAN_LOG = f"{STAGE1_LOG_DIR}/stage1_fresh_screening_plan.csv"
STAGE1_RESULTS_LOG = f"{STAGE1_LOG_DIR}/stage1_fresh_screening_results.csv"
STAGE1_RAW_LOG = f"{STAGE1_LOG_DIR}/stage1_fresh_screening_results.raw.csv"
STAGE1_RUN_JSONL = f"{STAGE1_LOG_DIR}/runs.jsonl"
STAGE1_COMMAND_JSONL = f"{STAGE1_LOG_DIR}/commands.jsonl"
STAGE1_UPDATE_JSONL = f"{STAGE1_LOG_DIR}/updates.jsonl"
STAGE1_PROBE_JSONL = f"{STAGE1_LOG_DIR}/counterfactual_probes.jsonl"
STAGE1_CHECKPOINT_JSONL = f"{STAGE1_LOG_DIR}/checkpoints.jsonl"
STAGE1_STATUS_JSON = f"{STAGE1_LOG_DIR}/status.json"
STAGE1_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g554_stage1_scenarios"
STAGE1_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g554_stage1_scenario_generation.json"
STAGE1_REPORT = "outputs/reports/phase5p5_repair5g554_stage1_fresh_screening.md"
STAGE1_SUMMARY = "outputs/reports/phase5p5_repair5g554_stage1_fresh_screening_summary.json"
STAGE1_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g554_stage1_candidate_leaderboard.csv"
STAGE1_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g554_stage1_candidate_by_stratum.csv"
STAGE1_FRONTIER_CSV = "outputs/tables/phase5p5_repair5g554_stage1_success_quality_frontier.csv"
STAGE1_ZERO_REG_CSV = "outputs/tables/phase5p5_repair5g554_stage1_zero_regression_candidates.csv"
STAGE1_LOW_REG_HIGH_GAIN_CSV = "outputs/tables/phase5p5_repair5g554_stage1_low_regression_high_gain_candidates.csv"
STAGE1_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g554_stage1_failure_cases.csv"
STAGE1_PARAMETER_SENS_CSV = "outputs/tables/phase5p5_repair5g554_stage1_parameter_sensitivity.csv"

STAGE2_PLAN_REPORT = "outputs/reports/phase5p5_repair5g554_stage2_nearmiss_expansion_plan.md"
STAGE2_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g554_stage2_nearmiss_expansion_plan_summary.json"
STAGE2_PLAN_PREVIEW_CSV = "outputs/tables/phase5p5_repair5g554_stage2_nearmiss_expansion_plan_preview.csv"
STAGE2_LOG_DIR = "outputs/logs/phase5p5_repair5g554_stage2_nearmiss_expansion"
STAGE2_PLAN_LOG = f"{STAGE2_LOG_DIR}/stage2_nearmiss_expansion_plan.csv"
STAGE2_RESULTS_LOG = f"{STAGE2_LOG_DIR}/stage2_nearmiss_expansion_results.csv"
STAGE2_RAW_LOG = f"{STAGE2_LOG_DIR}/stage2_nearmiss_expansion_results.raw.csv"
STAGE2_RUN_JSONL = f"{STAGE2_LOG_DIR}/runs.jsonl"
STAGE2_COMMAND_JSONL = f"{STAGE2_LOG_DIR}/commands.jsonl"
STAGE2_UPDATE_JSONL = f"{STAGE2_LOG_DIR}/updates.jsonl"
STAGE2_PROBE_JSONL = f"{STAGE2_LOG_DIR}/counterfactual_probes.jsonl"
STAGE2_CHECKPOINT_JSONL = f"{STAGE2_LOG_DIR}/checkpoints.jsonl"
STAGE2_STATUS_JSON = f"{STAGE2_LOG_DIR}/status.json"
STAGE2_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g554_stage2_scenarios"
STAGE2_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g554_stage2_scenario_generation.json"
STAGE2_REPORT = "outputs/reports/phase5p5_repair5g554_stage2_nearmiss_expansion.md"
STAGE2_SUMMARY = "outputs/reports/phase5p5_repair5g554_stage2_nearmiss_expansion_summary.json"
STAGE2_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g554_stage2_candidate_leaderboard.csv"
STAGE2_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g554_stage2_candidate_by_stratum.csv"
STAGE2_CI_CSV = "outputs/tables/phase5p5_repair5g554_stage2_candidate_confidence_intervals.csv"
STAGE2_SHORTLIST_CSV = "outputs/tables/phase5p5_repair5g554_stage2_validation_shortlist.csv"
STAGE2_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g554_stage2_failure_cases.csv"

VALIDATION_PLAN_REPORT = "outputs/reports/phase5p5_repair5g554_validation_plan.md"
VALIDATION_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g554_validation_plan_summary.json"
VALIDATION_LOG_DIR = "outputs/logs/phase5p5_repair5g554_validation"
VALIDATION_PLAN_LOG = f"{VALIDATION_LOG_DIR}/validation_plan.csv"
VALIDATION_RESULTS_LOG = f"{VALIDATION_LOG_DIR}/validation_results.csv"
VALIDATION_RAW_LOG = f"{VALIDATION_LOG_DIR}/validation_results.raw.csv"
VALIDATION_RUN_JSONL = f"{VALIDATION_LOG_DIR}/runs.jsonl"
VALIDATION_COMMAND_JSONL = f"{VALIDATION_LOG_DIR}/commands.jsonl"
VALIDATION_UPDATE_JSONL = f"{VALIDATION_LOG_DIR}/updates.jsonl"
VALIDATION_PROBE_JSONL = f"{VALIDATION_LOG_DIR}/counterfactual_probes.jsonl"
VALIDATION_CHECKPOINT_JSONL = f"{VALIDATION_LOG_DIR}/checkpoints.jsonl"
VALIDATION_STATUS_JSON = f"{VALIDATION_LOG_DIR}/status.json"
VALIDATION_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g554_validation_scenarios"
VALIDATION_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g554_validation_scenario_generation.json"
VALIDATION_REPORT = "outputs/reports/phase5p5_repair5g554_validation.md"
VALIDATION_SUMMARY = "outputs/reports/phase5p5_repair5g554_validation_summary.json"
VALIDATION_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g554_validation_candidate_leaderboard.csv"
VALIDATION_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g554_validation_by_stratum.csv"
VALIDATION_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g554_validation_vs_additive_diagnostic.csv"
VALIDATION_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g554_validation_failure_cases.csv"

BLIND_PLAN_REPORT = "outputs/reports/phase5p5_repair5g554_blind_plan.md"
BLIND_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g554_blind_plan_summary.json"
BLIND_LOG_DIR = "outputs/logs/phase5p5_repair5g554_blind"
BLIND_PLAN_LOG = f"{BLIND_LOG_DIR}/blind_plan.csv"
BLIND_RESULTS_LOG = f"{BLIND_LOG_DIR}/blind_results.csv"
BLIND_RAW_LOG = f"{BLIND_LOG_DIR}/blind_results.raw.csv"
BLIND_RUN_JSONL = f"{BLIND_LOG_DIR}/runs.jsonl"
BLIND_COMMAND_JSONL = f"{BLIND_LOG_DIR}/commands.jsonl"
BLIND_UPDATE_JSONL = f"{BLIND_LOG_DIR}/updates.jsonl"
BLIND_PROBE_JSONL = f"{BLIND_LOG_DIR}/counterfactual_probes.jsonl"
BLIND_CHECKPOINT_JSONL = f"{BLIND_LOG_DIR}/checkpoints.jsonl"
BLIND_STATUS_JSON = f"{BLIND_LOG_DIR}/status.json"
BLIND_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g554_blind_scenarios"
BLIND_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g554_blind_scenario_generation.json"
BLIND_REPORT = "outputs/reports/phase5p5_repair5g554_blind.md"
BLIND_SUMMARY = "outputs/reports/phase5p5_repair5g554_blind_summary.json"
BLIND_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g554_blind_candidate_leaderboard.csv"
BLIND_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g554_blind_by_stratum.csv"
BLIND_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g554_blind_failure_cases.csv"

DECISION_REPORT = "outputs/reports/phase5p5_repair5g554_decision.md"
DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g554_decision_summary.json"
CLAIM_LEDGER_CSV = "outputs/tables/phase5p5_repair5g554_claim_ledger.csv"
FINAL_CANDIDATE_THETA_CSV = "outputs/tables/phase5p5_repair5g554_final_candidate_theta.csv"
LARGE_ARTIFACT_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g554_large_artifact_manifest.csv"


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--candidate-count", type=int, default=16000)
    p.add_argument("--row-limit", type=int, default=0)
    p.add_argument("--max-workers", type=int, default=1)
    p.add_argument("--binary", type=Path, default=Path(g549.DEFAULT_BINARY))
    p.add_argument("--ids", nargs="*", type=int)
    return p


def validate_ids(args: argparse.Namespace, label: str) -> None:
    bad = sorted({int(value) for value in (args.ids or []) if 166 <= int(value) <= 205})
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


def git_short_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def safe_mean(values: Iterable[Any]) -> str:
    vals = [number(v, math.nan) for v in values]
    vals = [v for v in vals if math.isfinite(v)]
    return csv_number(statistics.fmean(vals)) if vals else ""


def ci_upper(values: list[float]) -> str:
    vals = [v for v in values if math.isfinite(v)]
    if not vals:
        return ""
    if len(vals) == 1:
        return csv_number(vals[0])
    return csv_number(statistics.fmean(vals) + 1.96 * statistics.stdev(vals) / math.sqrt(len(vals)))


def theta_signature(theta: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(theta.get(col, "")) for col in THETA_COLUMNS)


def theta_mode(theta: dict[str, Any]) -> str:
    return g553.theta_mode(theta)


def clamp_theta(theta: dict[str, Any]) -> dict[str, Any]:
    return g553.clamp_theta(theta)


def current_theta() -> dict[str, Any]:
    global _CURRENT_THETA_CACHE
    if _CURRENT_THETA_CACHE is None:
        _CURRENT_THETA_CACHE = g553.actual_static_flow_theta()
    return dict(_CURRENT_THETA_CACHE)


def helper_theta() -> dict[str, Any]:
    global _HELPER_THETA_CACHE
    if _HELPER_THETA_CACHE is None:
        _HELPER_THETA_CACHE = g553.helper_static_flow_theta()
    return dict(_HELPER_THETA_CACHE)


def theta_distance(theta: dict[str, Any], base: dict[str, Any] | None = None) -> float:
    return g553.theta_distance(theta, base or current_theta())


def active_deltas(theta: dict[str, Any], base: dict[str, Any] | None = None) -> str:
    base = base or current_theta()
    changed = []
    for col in THETA_COLUMNS:
        if str(theta.get(col, "")) != str(base.get(col, "")):
            changed.append(col)
    return ";".join(changed)


def mix_theta(a: dict[str, Any], b: dict[str, Any], t: float) -> dict[str, Any]:
    theta = {}
    for col in THETA_COLUMNS:
        if col in MODE_COLUMNS:
            theta[col] = a.get(col, 0) if t < 0.5 else b.get(col, 0)
        else:
            theta[col] = number(a.get(col), 0.0) * (1 - t) + number(b.get(col), 0.0) * t
    return clamp_theta(theta)


def unit(label: str, field: str = "") -> float:
    return stable_hash(f"{ROUND}|{label}|{field}", modulo=1_000_000) / 999_999.0


def perturb_theta(center: dict[str, Any], label: str, pct: float, fields: list[str] | None = None) -> dict[str, Any]:
    theta = dict(center)
    for col in fields or NUMERIC_THETA_COLUMNS:
        lo, hi = THETA_BOUNDS[col]
        value = number(theta.get(col), lo)
        direction = -1.0 if stable_hash(f"{label}|{col}|sign", modulo=2) == 0 else 1.0
        span = max(hi - lo, abs(value), 1.0e-9)
        theta[col] = value + direction * pct * span * (0.25 + 0.75 * unit(label, col))
    return clamp_theta(theta)


def set_mode(theta: dict[str, Any], mode: str) -> dict[str, Any]:
    out = dict(theta)
    g553.patch_goal_mode(out, mode)
    return clamp_theta(out)


def baseline_rows(context: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    rows = g553.baseline_plan_rows(context, prefix)
    for idx, row in enumerate(rows):
        row["plan_row_id"] = f"{prefix}_baseline_{idx:03d}"
        row["round"] = ROUND
    return rows


def main_verify_g553_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 verify G5.53 artifacts")
    audit = []
    for label, path in G553_REQUIRED.items():
        p = resolve(path)
        audit.append(
            {
                "artifact": label,
                "path": str(p),
                "exists": p.exists(),
                "rows_or_file": table_count(path),
                "sha256": file_sha256(path),
                **claims(),
            }
        )
    decision = load_json(g553.DECISION_SUMMARY, {})
    stage0 = load_json(g553.STAGE0_SUMMARY, {})
    stage1 = load_json(g553.STAGE1_SUMMARY, {})
    validation = load_json(g553.VALIDATION_SUMMARY, {})
    coeff = load_json(g553.CURRENT_COEFF_SUMMARY, {})
    checks = {
        "g553_decision_no_promotion": decision.get("decision") == "g553_no_fixed_coeff_candidate_beats_hand_staticflow_keep_baseline",
        "stage0_fingerprint_match_rate_1": str(stage0.get("fulltheta_fingerprint_match_rate", "")) in {"1", "1.0"},
        "stage0_materialization_failures_0": int(number(stage0.get("materialization_failure_rows"), -1)) == 0,
        "stage1_reused_g552_rows": int(number(stage1.get("local_new_stage1_solver_rows"), -1)) == 0
        and int(number(stage1.get("stage1_source_reused_solver_rows"), 0)) >= 128000,
        "stage1_zero_reg_low_support_1470": int(number(stage1.get("zero_regression_low_support_candidates"), 0)) >= 1470,
        "stage1_high_support_regression_27": int(number(stage1.get("global_support_with_regression_candidates"), 0)) >= 27,
        "validation_not_run": not boolish(validation.get("validation_run")),
        "current_staticflow_materialized_baseline": coeff.get("candidate_id", STATIC_FLOW) in {"", STATIC_FLOW}
        and boolish(coeff.get("current_static_flow_materializes_with_fingerprint_match", True)),
    }
    ok = all(boolish(row["exists"]) for row in audit) and all(checks.values())
    summary = {
        "schema_version": "phase5p5_repair5g554_g553_verification_summary_v1",
        "decision": "g554_g553_verified_screening_negative_not_final" if ok else "g554_g553_verification_blocked",
        "checks": checks,
        "all_required_artifacts_exist": all(boolish(row["exists"]) for row in audit),
        "g553_decision": decision.get("decision", ""),
        "stage0_solver_rows": stage0.get("solver_rows", 0),
        "stage1_source_reused_solver_rows": stage1.get("stage1_source_reused_solver_rows", 0),
        "local_new_stage1_solver_rows": stage1.get("local_new_stage1_solver_rows", 0),
        "zero_regression_low_support_candidates": stage1.get("zero_regression_low_support_candidates", 0),
        "global_support_with_regression_candidates": stage1.get("global_support_with_regression_candidates", 0),
        "validation_run": boolish(validation.get("validation_run")),
        **claims(),
    }
    write_rows(G553_AUDIT_CSV, audit)
    write_json(G553_VERIFY_SUMMARY, summary)
    write_text(
        G553_VERIFY_REPORT,
        "# G5.54 Verification of G5.53 Artifacts\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- G5.53 decision: `{summary['g553_decision']}`\n"
        f"- Stage0 solver rows: `{summary['stage0_solver_rows']}`\n"
        f"- Stage1 reused solver-facing rows: `{summary['stage1_source_reused_solver_rows']}`\n"
        f"- local new Stage1 solver rows: `{summary['local_new_stage1_solver_rows']}`\n"
        f"- zero-regression low-support candidates: `{summary['zero_regression_low_support_candidates']}`\n"
        f"- high-support regressing candidates: `{summary['global_support_with_regression_candidates']}`\n\n"
        "Interpretation: G5.53 is a conservative no-promotion result, not a final closure of fixed-global coefficient search.\n",
    )
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_audit_g553_negative_result(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 audit G5.53 negative result")
    if not resolve(G553_VERIFY_SUMMARY).exists() or args.overwrite:
        main_verify_g553_artifacts([])
    stage1 = load_json(g553.STAGE1_SUMMARY, {})
    validation = load_json(g553.VALIDATION_SUMMARY, {})
    coeff = load_json(g553.CURRENT_COEFF_SUMMARY, {})
    leaderboard = read_rows(g553.STAGE1_LEADERBOARD_CSV)
    by_stratum = read_rows(g553.STAGE1_BY_STRATUM_CSV)
    zero_low = [
        row
        for row in leaderboard
        if int(number(row.get("success_regression_count_vs_static_flow"), 0)) == 0
        and not boolish(row.get("global_fixed_support_gate_passed"))
    ]
    high_reg = [
        row
        for row in leaderboard
        if boolish(row.get("global_fixed_support_gate_passed"))
        and int(number(row.get("success_regression_count_vs_static_flow"), 0)) > 0
    ]
    quality_near = sorted(
        leaderboard,
        key=lambda row: (
            number(row.get("both_success_quality_delta_mean_vs_static_flow"), 9.0),
            int(number(row.get("success_regression_count_vs_static_flow"), 10**9)),
        ),
    )[:200]
    top_zero_support = max((int(number(row.get("candidate_rows"), 0)) for row in zero_low), default=0)
    directions = Counter()
    base = current_theta()
    for row in zero_low[:300] + high_reg[:100] + quality_near[:100]:
        for col in ACTIVE_SEARCH_FIELDS:
            delta = number(row.get(col), number(base.get(col), 0.0)) - number(base.get(col), 0.0)
            if abs(delta) > 1.0e-9:
                directions[f"{col}:{'up' if delta > 0 else 'down'}"] += 1
    limitations = [
        {
            "limitation": "stage1_reused_prior_label_v2_rows",
            "evidence": f"local_new_stage1_solver_rows={stage1.get('local_new_stage1_solver_rows', '')}",
            "g554_response": "run fresh paired fixed-coefficient replay",
            **claims(),
        },
        {
            "limitation": "strict_global_support_dropped_zero_regression_nearmisses",
            "evidence": f"zero_regression_low_support_candidates={stage1.get('zero_regression_low_support_candidates', '')}",
            "g554_response": "expand top low-support zero-regression candidates",
            **claims(),
        },
        {
            "limitation": "validation_skipped",
            "evidence": f"validation_run={validation.get('validation_run', False)}",
            "g554_response": "create validation only after fresh Stage2 shortlist",
            **claims(),
        },
        {
            "limitation": "current_cpp_staticflow_differs_from_helper",
            "evidence": ";".join(coeff.get("legacy_helper_diff_fields", [])) if isinstance(coeff.get("legacy_helper_diff_fields"), list) else "",
            "g554_response": "anchor baseline to current C++ materialized static_flow_shield",
            **claims(),
        },
    ]
    near_by_stratum = []
    near_ids = {row.get("candidate_id") for row in zero_low[:100] + quality_near[:100]}
    for row in by_stratum:
        if row.get("candidate_id") in near_ids:
            near_by_stratum.append({**row, **claims()})
    summary = {
        "schema_version": "phase5p5_repair5g554_g553_negative_result_audit_summary_v1",
        "decision": "g553_first_pass_screening_negative_continue_g554",
        "answers": {
            "did_g553_run_fresh_stage1_solver_rows": False,
            "stage1_reused_g552_label_v2_rows": True,
            "zero_regression_candidates_rejected_for_low_support": len(zero_low),
            "top_zero_regression_candidate_support": top_zero_support,
            "quality_gain_insufficient_support_candidates": len([r for r in quality_near if not boolish(r.get("global_fixed_support_gate_passed"))]),
            "global_support_with_success_regressions": len(high_reg),
            "near_miss_parameter_directions": dict(directions.most_common(20)),
            "validation_run": boolish(validation.get("validation_run")),
            "validation_skip_reason": validation.get("skip_reason", ""),
            "baseline_is_current_cpp_staticflow_alias": True,
            "legacy_helper_diff_fields": coeff.get("legacy_helper_diff_fields", []),
            "is_final_negative": False,
        },
        "interpretation": "G5.53 is a conservative no-promotion screening negative, not a final fixed-global search closure.",
        **claims(),
    }
    write_rows(G553_ZERO_LOW_CSV, zero_low[:2000])
    write_rows(G553_HIGH_REG_CSV, high_reg[:2000])
    write_rows(G553_NEARMISS_BY_STRATUM_CSV, near_by_stratum[:3000])
    write_rows(G553_LIMITATIONS_CSV, limitations)
    write_json(G553_NEG_SUMMARY, summary)
    write_text(
        G553_NEG_REPORT,
        "# G5.54 Audit of the G5.53 Negative Result\n\n"
        "- decision: `g553_first_pass_screening_negative_continue_g554`\n"
        f"- zero-regression low-support candidates: `{len(zero_low)}`\n"
        f"- top zero-regression support: `{top_zero_support}`\n"
        f"- high-support candidates with regressions: `{len(high_reg)}`\n"
        f"- validation run: `{boolish(validation.get('validation_run'))}`\n\n"
        "G5.53 reused the G5.52 Label-v2 evidence pool for Stage1. It did not run the large fresh paired search and near-miss expansion required to close the fixed-global coefficient question.\n",
    )
    print(json.dumps({"decision": summary["decision"], "zero_low": len(zero_low), "high_reg": len(high_reg)}))
    return 0


def field_semantics(field: str) -> dict[str, Any]:
    if field in MODE_COLUMNS:
        return {
            "active_in_materialization": True,
            "active_in_update": False,
            "active_in_cost_projection": True,
            "active_only_under_specific_goal_projection_mode": True,
            "ignored_or_alias": False,
            "requires_nonzero_flow_events": False,
            "requires_nonzero_wait_progress_events": False,
        }
    if "flow" in field:
        return {
            "active_in_materialization": True,
            "active_in_update": field.startswith("theta_alpha_flow") or field == "theta_rho_flow_decay",
            "active_in_cost_projection": field in {"theta_lambda_flow", "theta_flow_shield_beta", "theta_max_flow_shield"},
            "active_only_under_specific_goal_projection_mode": field in {"theta_lambda_flow", "theta_flow_shield_beta", "theta_max_flow_shield"},
            "ignored_or_alias": field == "theta_lambda_flow" and theta_mode(current_theta()) == "flow_shield",
            "requires_nonzero_flow_events": True,
            "requires_nonzero_wait_progress_events": field == "theta_alpha_flow_wait_progress",
        }
    if "edge_cost" in field:
        return {
            "active_in_materialization": True,
            "active_in_update": False,
            "active_in_cost_projection": True,
            "active_only_under_specific_goal_projection_mode": False,
            "ignored_or_alias": False,
            "requires_nonzero_flow_events": False,
            "requires_nonzero_wait_progress_events": False,
        }
    return {
        "active_in_materialization": True,
        "active_in_update": field.startswith("theta_alpha_cong") or field == "theta_rho_cong_decay",
        "active_in_cost_projection": field == "theta_lambda_cong",
        "active_only_under_specific_goal_projection_mode": False,
        "ignored_or_alias": False,
        "requires_nonzero_flow_events": False,
        "requires_nonzero_wait_progress_events": "wait_progress" in field,
    }


def main_audit_active_staticflow_fields(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 active staticflow fields")
    base = current_theta()
    helper = helper_theta()
    materialization = []
    semantic = []
    one_factor = []
    for col in THETA_COLUMNS:
        lo, hi = THETA_BOUNDS[col]
        sem = field_semantics(col)
        materialization.append(
            {
                "theta_parameter": col,
                "current_static_flow_value": base.get(col, ""),
                "legacy_helper_static_flow_value": helper.get(col, ""),
                "differs_from_legacy_helper": str(base.get(col, "")) != str(helper.get(col, "")),
                "within_bounds": lo <= number(base.get(col), lo) <= hi,
                **sem,
                **claims(),
            }
        )
        semantic.append(
            {
                "theta_parameter": col,
                "classification": "primary_active_search_field" if col in ACTIVE_SEARCH_FIELDS else "diagnostic_or_mode_field",
                "search_budget_role": "main" if col in ACTIVE_SEARCH_FIELDS else "ablation_diagnostic",
                "special_note": (
                    "lambda_flow is treated as diagnostic unless Stage0B shows response under flow_shield"
                    if col == "theta_lambda_flow"
                    else "wait-progress flow requires nonzero wait-progress events"
                    if col == "theta_alpha_flow_wait_progress"
                    else ""
                ),
                **sem,
                **claims(),
            }
        )
        if col in NUMERIC_THETA_COLUMNS:
            for direction, factor in [("down", -0.05), ("up", 0.05)]:
                theta = dict(base)
                span = max(hi - lo, abs(number(base.get(col), 0.0)), 1.0e-9)
                theta[col] = number(base.get(col), 0.0) + factor * span
                theta = clamp_theta(theta)
                one_factor.append(
                    {
                        "candidate_id": f"g554_onefactor_{col}_{direction}",
                        "theta_parameter": col,
                        "direction": direction,
                        "current_value": base.get(col, ""),
                        "candidate_value": theta.get(col, ""),
                        "planned_for_stage0b_field_smoke": True,
                        **theta,
                        **claims(),
                    }
                )
    summary = {
        "schema_version": "phase5p5_repair5g554_active_staticflow_fields_summary_v1",
        "decision": "g554_active_field_audit_ready",
        "field_count": len(THETA_COLUMNS),
        "primary_active_search_fields": ACTIVE_SEARCH_FIELDS,
        "theta_lambda_flow_primary": False,
        "theta_alpha_flow_wait_progress_current": base.get("theta_alpha_flow_wait_progress", ""),
        "theta_lambda_flow_current": base.get("theta_lambda_flow", ""),
        "goal_projection_mode": theta_mode(base),
        **claims(),
    }
    write_rows(ACTIVE_FIELD_MATERIALIZATION_CSV, materialization)
    write_rows(ONE_FACTOR_FIELD_PLAN_CSV, one_factor)
    write_rows(FIELD_USAGE_SEMANTIC_CSV, semantic)
    write_json(ACTIVE_FIELD_SUMMARY, summary)
    write_text(
        ACTIVE_FIELD_REPORT,
        "# G5.54 Active static_flow Field Audit\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- goal projection mode: `{summary['goal_projection_mode']}`\n"
        f"- primary active search fields: `{', '.join(ACTIVE_SEARCH_FIELDS)}`\n"
        "- theta_lambda_flow is kept diagnostic unless fresh smoke shows response under flow_shield.\n"
        "- theta_alpha_flow_wait_progress is searched carefully because the current hand value is zero.\n",
    )
    print(json.dumps({"decision": summary["decision"], "fields": len(THETA_COLUMNS)}))
    return 0


def pool_row(source: str, source_id: str, theta: dict[str, Any], **extra: Any) -> dict[str, Any]:
    base = current_theta()
    return {
        "pool_id": f"g554_pool_{stable_hash(source, source_id, theta_signature(theta), modulo=10**12):012d}",
        "source": source,
        "source_id": source_id,
        "distance_from_current_static_flow": csv_number(theta_distance(theta, base)),
        "distance_from_legacy_helper": csv_number(theta_distance(theta, helper_theta())),
        "active_field_deltas": active_deltas(theta, base),
        "global_fixed_candidate": True,
        "context_dependent": False,
        **extra,
        **theta,
        **claims(),
    }


def main_create_nearmiss_candidate_pool(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 near-miss candidate pool")
    if not resolve(G553_NEG_SUMMARY).exists() or args.overwrite:
        main_audit_g553_negative_result([])
    base = current_theta()
    helper = helper_theta()
    rows = [
        pool_row("current_hand_static_flow_shield", STATIC_FLOW, base, theta_family="hand_static_reference"),
        pool_row("legacy_helper_static_flow_reference", "legacy_helper_static_flow_theta", helper, theta_family="legacy_helper_reference"),
        pool_row("hand_legacy_midpoint", "hand_helper_t050", mix_theta(base, helper, 0.5), theta_family="hand_legacy_midpoint"),
    ]
    g553_rows = read_rows(g553.STAGE1_LEADERBOARD_CSV)
    sorted_quality = sorted(g553_rows, key=lambda row: number(row.get("both_success_quality_delta_mean_vs_static_flow"), 9.0))
    buckets = [
        (
            "g553_zero_regression_low_support",
            [
                row
                for row in g553_rows
                if int(number(row.get("success_regression_count_vs_static_flow"), 0)) == 0
                and not boolish(row.get("global_fixed_support_gate_passed"))
            ][:600],
        ),
        (
            "g553_high_quality_nearmiss",
            [row for row in sorted_quality if number(row.get("both_success_quality_delta_mean_vs_static_flow"), 9.0) < 0][:400],
        ),
        (
            "g553_high_support_few_regression",
            [
                row
                for row in g553_rows
                if boolish(row.get("global_fixed_support_gate_passed"))
                and int(number(row.get("success_regression_count_vs_static_flow"), 0)) <= 3
            ][:200],
        ),
    ]
    for source, source_rows in buckets:
        for row in source_rows:
            theta = clamp_theta({col: row.get(col, base.get(col, "")) for col in THETA_COLUMNS})
            rows.append(
                pool_row(
                    source,
                    str(row.get("candidate_id", "")),
                    theta,
                    theta_family=row.get("candidate_family", source),
                    support_rows_existing=row.get("candidate_rows", ""),
                    success_regression_count_existing=row.get("success_regression_count_vs_static_flow", ""),
                    quality_delta_existing=row.get("both_success_quality_delta_mean_vs_static_flow", ""),
                    support_strata_existing=row.get("support_strata", ""),
                )
            )
            rows.append(
                pool_row(
                    f"{source}_shrinkage_to_hand",
                    f"{row.get('candidate_id', '')}_t035",
                    mix_theta(base, theta, 0.35),
                    theta_family="shrinkage_to_hand_from_risky",
                    support_rows_existing=row.get("candidate_rows", ""),
                    success_regression_count_existing=row.get("success_regression_count_vs_static_flow", ""),
                    quality_delta_existing=row.get("both_success_quality_delta_mean_vs_static_flow", ""),
                )
            )
    for row in read_rows(g552.SAFE_LIBRARY_CSV)[:200]:
        if not any(col in row for col in THETA_COLUMNS):
            continue
        theta = clamp_theta({col: row.get(col, base.get(col, "")) for col in THETA_COLUMNS})
        rows.append(pool_row("g552_safe_theta_library", str(row.get("theta_id", row.get("candidate_id", ""))), theta, theta_family="g552_safe_library"))
    seen: set[tuple[str, ...]] = set()
    unique = []
    for row in rows:
        sig = theta_signature(row)
        if sig in seen:
            continue
        seen.add(sig)
        unique.append(row)
    centroid_rows = []
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in unique:
        by_family[str(row.get("theta_family", row.get("source", "")))].append(row)
    for family, group in sorted(by_family.items()):
        centroid = {col: safe_mean([row.get(col) for row in group]) for col in NUMERIC_THETA_COLUMNS}
        mode = Counter(theta_mode(row) for row in group).most_common(1)[0][0]
        centroid = set_mode({**base, **centroid}, mode)
        centroid_rows.append(pool_row("family_centroid", family, centroid, theta_family=family, family_rows=len(group)))
    frontier = sorted(
        unique,
        key=lambda row: (
            int(number(row.get("success_regression_count_existing"), 10**9)),
            number(row.get("quality_delta_existing"), 9.0),
            number(row.get("distance_from_current_static_flow"), 9.0),
        ),
    )[:500]
    summary = {
        "schema_version": "phase5p5_repair5g554_nearmiss_candidate_pool_summary_v1",
        "decision": "g554_nearmiss_candidate_pool_created",
        "pool_rows": len(unique),
        "centroid_rows": len(centroid_rows),
        "sources": dict(Counter(row.get("source", "") for row in unique)),
        "candidate_object": "one deterministic global fixed coefficient vector",
        **claims(),
    }
    write_rows(NEARMISS_POOL_CSV, unique)
    write_rows(NEARMISS_CENTROIDS_CSV, centroid_rows)
    write_rows(NEARMISS_FRONTIER_CSV, frontier)
    write_json(NEARMISS_SUMMARY, summary)
    write_text(
        NEARMISS_REPORT,
        "# G5.54 Near-Miss Candidate Pool\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- pool rows: `{summary['pool_rows']}`\n"
        f"- centroid rows: `{summary['centroid_rows']}`\n\n"
        "Near-miss sources seed fixed global vectors only; they do not make the candidate contextual.\n",
    )
    print(json.dumps({"decision": summary["decision"], "pool_rows": len(unique)}))
    return 0


def candidate_family_rows() -> list[dict[str, Any]]:
    families = [
        "hand_static_reference",
        "legacy_helper_reference",
        "hand_legacy_midpoints",
        "one_factor_small_perturbation",
        "two_factor_interaction",
        "trust_region_sobol_around_hand",
        "trust_region_sobol_around_nearmiss",
        "cma_es_style_offline_candidates",
        "cross_entropy_elite_refits",
        "coordinate_descent_lines",
        "flow_wait_progress_micro_sweep",
        "lambda_cong_micro_sweep",
        "flow_shield_beta_cap_sweep",
        "cost_clamp_micro_sweep",
        "rho_decay_micro_sweep",
        "shrinkage_to_hand_from_risky",
        "negative_controls_wide_random",
    ]
    return [
        {
            "candidate_family": family,
            "global_fixed_vector": True,
            "context_dependent": False,
            "dynamic_policy": False,
            "allowed_for_promotion": family != "negative_controls_wide_random",
            **claims(),
        }
        for family in families
    ]


def generate_candidate_theta(family: str, index: int, pool: list[dict[str, Any]]) -> tuple[dict[str, Any], str, str]:
    base = current_theta()
    helper = helper_theta()
    label = f"{family}_{index:06d}"
    pool_row_i = pool[index % len(pool)] if pool else pool_row("current", STATIC_FLOW, base)
    center = clamp_theta({col: pool_row_i.get(col, base.get(col, "")) for col in THETA_COLUMNS})
    trust_region = "tiny"
    theta = dict(base)
    if family == "hand_static_reference":
        theta = dict(base)
    elif family == "legacy_helper_reference":
        theta = dict(helper)
    elif family == "hand_legacy_midpoints":
        theta = mix_theta(base, helper, [0.1, 0.25, 0.5, 0.75, 0.9][index % 5])
    elif family == "one_factor_small_perturbation":
        trust_region = ["tiny", "small", "medium"][index % 3]
        pct = {"tiny": 0.025, "small": 0.05, "medium": 0.10}[trust_region]
        col = ACTIVE_SEARCH_FIELDS[index % len(ACTIVE_SEARCH_FIELDS)]
        theta = perturb_theta(base, label, pct, [col])
    elif family == "two_factor_interaction":
        trust_region = "small"
        fields = [ACTIVE_SEARCH_FIELDS[index % len(ACTIVE_SEARCH_FIELDS)], ACTIVE_SEARCH_FIELDS[(index // len(ACTIVE_SEARCH_FIELDS)) % len(ACTIVE_SEARCH_FIELDS)]]
        theta = perturb_theta(base, label, 0.05, fields)
    elif family == "trust_region_sobol_around_hand":
        trust_region = ["tiny", "small", "medium"][index % 3]
        theta = perturb_theta(base, label, {"tiny": 0.025, "small": 0.05, "medium": 0.10}[trust_region], ACTIVE_SEARCH_FIELDS)
    elif family == "trust_region_sobol_around_nearmiss":
        trust_region = "near_miss"
        theta = perturb_theta(center, label, 0.05, ACTIVE_SEARCH_FIELDS)
    elif family in {"cma_es_style_offline_candidates", "cross_entropy_elite_refits"}:
        trust_region = "near_miss"
        theta = mix_theta(base, perturb_theta(center, label, 0.08, ACTIVE_SEARCH_FIELDS), 0.65)
    elif family == "coordinate_descent_lines":
        trust_region = "small"
        col = ACTIVE_SEARCH_FIELDS[index % len(ACTIVE_SEARCH_FIELDS)]
        lo, hi = THETA_BOUNDS[col]
        grid = [lo, lo + 0.25 * (hi - lo), lo + 0.5 * (hi - lo), lo + 0.75 * (hi - lo), hi]
        theta = dict(base)
        theta[col] = grid[(index // len(ACTIVE_SEARCH_FIELDS)) % len(grid)]
    elif family == "flow_wait_progress_micro_sweep":
        theta = dict(base)
        theta["theta_alpha_flow_wait_progress"] = [0.0, 0.025, 0.05, 0.075, 0.10, 0.15, 0.20][index % 7]
        theta["theta_alpha_flow_commit_progress"] = 0.90 + 0.05 * ((index // 7) % 7)
    elif family == "lambda_cong_micro_sweep":
        theta = dict(base)
        theta["theta_lambda_cong"] = 0.75 + 0.05 * (index % 11)
        theta["theta_alpha_cong_commit_nonprogress"] = 1.00 + 0.05 * ((index // 11) % 9)
    elif family == "flow_shield_beta_cap_sweep":
        theta = dict(base)
        theta["theta_flow_shield_beta"] = 0.20 + 0.025 * (index % 17)
        theta["theta_max_flow_shield"] = 0.50 + 0.05 * ((index // 17) % 11)
    elif family == "cost_clamp_micro_sweep":
        theta = dict(base)
        theta["theta_min_edge_cost"] = 0.50 + 0.05 * (index % 11)
        theta["theta_max_edge_cost"] = 9.0 + 0.25 * ((index // 11) % 13)
    elif family == "rho_decay_micro_sweep":
        theta = dict(base)
        theta["theta_rho_cong_decay"] = 0.90 + 0.005 * (index % 21)
        theta["theta_rho_flow_decay"] = 0.90 + 0.005 * ((index // 21) % 21)
    elif family == "shrinkage_to_hand_from_risky":
        trust_region = "near_miss"
        theta = mix_theta(base, center, [0.1, 0.2, 0.35, 0.5, 0.65][index % 5])
    elif family == "negative_controls_wide_random":
        trust_region = "wide_diagnostic"
        theta = dict(base)
        for col in NUMERIC_THETA_COLUMNS:
            lo, hi = THETA_BOUNDS[col]
            theta[col] = lo + (hi - lo) * unit(label, col)
        theta = set_mode(theta, ["flow_shield", "agent_progress", "none"][index % 3])
    return clamp_theta(theta), trust_region, str(pool_row_i.get("pool_id", ""))


def candidate_registry_rows(count: int) -> list[dict[str, Any]]:
    if not resolve(NEARMISS_POOL_CSV).exists():
        main_create_nearmiss_candidate_pool([])
    pool = read_rows(NEARMISS_POOL_CSV)
    families = [row["candidate_family"] for row in candidate_family_rows()]
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    index = 0
    while len(rows) < max(1, count) and index < max(1000, count * 20):
        family = families[index % len(families)]
        theta, trust_region, source_pool_id = generate_candidate_theta(family, index, pool)
        sig = theta_signature(theta)
        if sig not in seen:
            seen.add(sig)
            cid = f"g554_c{len(rows):05d}"
            rows.append(
                {
                    "registry_row_id": f"g554_registry_{len(rows):05d}",
                    "candidate_id": cid,
                    "candidate_family": family,
                    "theta_cluster": trust_region,
                    "source_pool_id": source_pool_id,
                    "distance_from_current_static_flow": csv_number(theta_distance(theta)),
                    "global_fixed_candidate": True,
                    "context_dependent": False,
                    "dynamic_policy": False,
                    "allowed_for_promotion": family != "negative_controls_wide_random",
                    **theta,
                    **claims(),
                }
            )
        index += 1
    return rows


def main_create_trust_region_search_space(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 trust-region search space")
    if not resolve(ACTIVE_FIELD_SUMMARY).exists() or args.overwrite:
        main_audit_active_staticflow_fields([])
    registry = candidate_registry_rows(max(8000, args.candidate_count))
    bounds = [
        {
            "theta_parameter": col,
            "lower_bound": lo,
            "upper_bound": hi,
            "categorical": col in MODE_COLUMNS,
            "current_static_flow_value": current_theta().get(col, ""),
            "main_search_field": col in ACTIVE_SEARCH_FIELDS,
            **claims(),
        }
        for col, (lo, hi) in THETA_BOUNDS.items()
    ]
    metadata = []
    for family, count in Counter(row["candidate_family"] for row in registry).items():
        metadata.append(
            {
                "candidate_family": family,
                "candidate_vectors": count,
                "allowed_for_promotion": family != "negative_controls_wide_random",
                "generation_policy": "deterministic trust-region and near-miss expansion",
                **claims(),
            }
        )
    summary = {
        "schema_version": "phase5p5_repair5g554_trust_region_search_space_summary_v1",
        "decision": "g554_trust_region_search_space_created",
        "candidate_vectors": len(registry),
        "distinct_candidate_vectors": len({theta_signature(row) for row in registry}),
        "preferred_candidate_vectors_met": len(registry) >= 16000,
        "minimum_candidate_vectors_met": len(registry) >= 8000,
        "baseline_candidate": STATIC_FLOW,
        "candidate_object": "one deterministic global fixed coefficient vector",
        **claims(),
    }
    write_rows(CANDIDATE_REGISTRY_LOG, registry)
    write_rows(CANDIDATE_PREVIEW_CSV, registry[:1000])
    write_rows(SEARCH_BOUNDS_CSV, bounds)
    write_rows(CANDIDATE_FAMILY_CSV, candidate_family_rows())
    write_rows(CANDIDATE_METADATA_CSV, metadata)
    write_json(SEARCH_SUMMARY, summary)
    write_text(
        SEARCH_REPORT,
        "# G5.54 Trust-Region Search Space v2\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- candidate vectors: `{summary['candidate_vectors']}`\n"
        f"- distinct vectors: `{summary['distinct_candidate_vectors']}`\n"
        f"- baseline candidate: `{STATIC_FLOW}`\n\n"
        "The raw full registry is kept under ignored `outputs/logs/`; compact previews and metadata are committed.\n",
    )
    print(json.dumps({"decision": summary["decision"], "candidate_vectors": len(registry)}))
    return 0


def fresh_seed(seed_start: int, index: int) -> int:
    seed = seed_start + index
    if 166 <= seed <= 205:
        seed += 100
    return seed


def contexts(split: str, count: int, seed_start: int) -> list[dict[str, Any]]:
    families = ["random", "maze", "warehouse"]
    agents = [50, 100]
    budgets = [2000, 1000, 500]
    short_budgets = [1000, 2000, 5000]
    base_limits = [0.50, 1.00]
    iterations = [2, 4]
    rows = []
    for idx in range(count):
        fam = families[idx % len(families)]
        agent_count = agents[(idx // len(families)) % len(agents)]
        budget = budgets[(idx // (len(families) * len(agents))) % len(budgets)]
        short_budget = short_budgets[(idx // 5) % len(short_budgets)]
        base_time = base_limits[(idx // 7) % len(base_limits)]
        ltm_iters = iterations[(idx // 11) % len(iterations)]
        seed = fresh_seed(seed_start, idx)
        rows.append(
            {
                "split": split,
                "context_id": f"{split}|{fam}|a{agent_count}|s{seed}|b{budget}|i{ltm_iters}|t{base_time}",
                "map": g553.map_for_family(fam),
                "map_family": fam,
                "agents": agent_count,
                "seed": seed,
                "nominal_budget_ms": budget,
                "budget_ms": budget,
                "horizon_id": f"{split}_short{short_budget}_t{int(base_time * 100):03d}_i{ltm_iters}",
                "short_budget_ms": short_budget,
                "base_time_limit_sec": base_time,
                "ltm_max_iterations": ltm_iters,
                "scenario_hash": stable_hash(f"{split}|{fam}|{agent_count}|{seed}|{budget}|{short_budget}|{base_time}|{ltm_iters}", modulo=10**16),
                "fresh_seed_block": g553.seed_block(seed),
                **claims(),
            }
        )
    return rows


def load_registry() -> list[dict[str, Any]]:
    if not resolve(CANDIDATE_REGISTRY_LOG).exists():
        main_create_trust_region_search_space([])
    return read_rows(CANDIDATE_REGISTRY_LOG)


def plan_rows(
    *,
    split: str,
    context_count: int,
    seed_start: int,
    candidates: list[dict[str, Any]],
    candidates_per_context: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ctxs = contexts(split, context_count, seed_start)
    if not candidates:
        return rows
    for context_idx, context in enumerate(ctxs):
        prefix = f"g554_{split}_{context_idx:05d}"
        rows.extend(baseline_rows(context, prefix))
        for offset in range(candidates_per_context):
            candidate = candidates[(context_idx * candidates_per_context + offset) % len(candidates)]
            rows.append(
                {
                    "plan_row_id": f"g554_{split}_{len(rows):09d}",
                    **context,
                    "role": f"generated_theta::{candidate['candidate_id']}",
                    "candidate_id": candidate["candidate_id"],
                    "materialized_method": candidate["candidate_id"],
                    "sampling_policy": candidate.get("candidate_family", ""),
                    "theta_cluster": candidate.get("theta_cluster", ""),
                    "candidate_family": candidate.get("candidate_family", ""),
                    "fulltheta_registry_row_id": candidate.get("registry_row_id", ""),
                    "counts_as_g554_fresh_solver_row": True,
                    "global_fixed_candidate": True,
                    **{col: candidate.get(col, "") for col in THETA_COLUMNS},
                    **claims(),
                }
            )
    for idx, row in enumerate(rows):
        row["plan_row_id"] = f"g554_{split}_{idx:09d}"
    return rows


def run_probe(
    *,
    plan: list[dict[str, Any]],
    args: argparse.Namespace,
    result_csv: str,
    raw_csv: str,
    log_dir: str,
    run_jsonl: str,
    command_jsonl: str,
    update_jsonl: str,
    probe_jsonl: str,
    checkpoint_jsonl: str,
    status_json: str,
    scenario_dir: str,
    scenario_metadata: str,
    manifest_prefix: str,
    row_prefix: str,
    execution_mode: str,
) -> list[dict[str, Any]]:
    binary = g549.binary_path(args.binary)
    if not binary.exists():
        raise FileNotFoundError(f"missing solver binary: {binary}")
    return g549.run_probe_plan(
        plan,
        binary=binary,
        overwrite=args.overwrite,
        row_limit=max(0, args.row_limit),
        max_workers=args.max_workers,
        registry_path=CANDIDATE_REGISTRY_LOG,
        result_csv=result_csv,
        raw_csv=raw_csv,
        log_dir=log_dir,
        run_jsonl=run_jsonl,
        command_jsonl=command_jsonl,
        update_jsonl=update_jsonl,
        probe_jsonl=probe_jsonl,
        checkpoint_jsonl=checkpoint_jsonl,
        status_json=status_json,
        scenario_dir=scenario_dir,
        scenario_metadata=scenario_metadata,
        manifest_prefix=manifest_prefix,
        row_prefix=row_prefix,
        execution_mode=execution_mode,
    )


def generated_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if str(row.get("role", "")).startswith("generated_theta::")]


def materialization_failures(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in generated_rows(rows):
        if not boolish(row.get("candidate_recognized", True)):
            out.append(row)
            continue
        if str(row.get("fulltheta_fingerprint_match", "")) != "" and not boolish(row.get("fulltheta_fingerprint_match")):
            out.append(row)
            continue
        if not boolish(row.get("cost_finite_all", row.get("repair5g_costs_finite", True))):
            out.append(row)
    return out


def raw_stats(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"rows": 0, "fingerprint": 0, "recognized": 0, "cost": 0, "theta": None, "family": ""})
    for row in generated_rows(rows):
        cid = str(row.get("candidate_id", ""))
        if not cid:
            continue
        s = stats[cid]
        s["rows"] += 1
        s["fingerprint"] += boolish(row.get("fulltheta_fingerprint_match", True))
        s["recognized"] += boolish(row.get("candidate_recognized", True))
        s["cost"] += boolish(row.get("cost_finite_all", row.get("repair5g_costs_finite", True)))
        s["family"] = row.get("candidate_family", s["family"])
        if s["theta"] is None:
            s["theta"] = {col: row.get(col, "") for col in THETA_COLUMNS}
    return stats


def leaderboard_from_results(
    rows: list[dict[str, Any]],
    *,
    min_rows: int,
    min_strata: int,
    min_seed_blocks: int,
    stage: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    pairs, _family_pairs, _additive_pairs, _pair_failures = g549.result_pairs(rows)
    rstats = raw_stats(rows)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_stratum: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    failures = []
    for pair in pairs:
        cid = str(pair.get("selected_candidate", ""))
        grouped[cid].append(pair)
        by_stratum[(cid, pair.get("map_family", ""), str(pair.get("agents", "")), str(pair.get("nominal_budget_ms", "")), str(pair.get("horizon_id", "")))].append(pair)
        if boolish(pair.get("success_regression")) and len(failures) < 2000:
            failures.append({**pair, **claims()})
    board = []
    for cid, group in grouped.items():
        deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in group if str(row.get("quality_delta_ratio", "")).strip()]
        deltas = [value for value in deltas if math.isfinite(value)]
        both = sum(1 for row in group if boolish(row.get("both_success")))
        regressions = sum(1 for row in group if boolish(row.get("success_regression")))
        gains = sum(1 for row in group if boolish(row.get("success_gain")))
        better = sum(1 for row in group if boolish(row.get("better")))
        worse = sum(1 for row in group if boolish(row.get("worse")))
        strata = {(row.get("map_family"), row.get("agents"), row.get("nominal_budget_ms"), row.get("horizon_id")) for row in group}
        seed_blocks = {g553.seed_block(row.get("seed")) for row in group}
        raw = rstats.get(cid, {})
        raw_rows = int(number(raw.get("rows"), 0))
        theta = raw.get("theta") or {}
        mean_delta = statistics.fmean(deltas) if deltas else math.nan
        upper = ci_upper(deltas)
        candidate_success = sum(1 for row in group if boolish(row.get("contender_success")))
        static_success = sum(1 for row in group if boolish(row.get("baseline_success")))
        success_rate_delta = (candidate_success - static_success) / max(1, len(group))
        fingerprint_all = raw_rows > 0 and int(number(raw.get("fingerprint"), 0)) == raw_rows
        recognized_all = raw_rows > 0 and int(number(raw.get("recognized"), 0)) == raw_rows
        cost_all = raw_rows > 0 and int(number(raw.get("cost"), 0)) == raw_rows
        ready = (
            regressions == 0
            and len(group) >= min_rows
            and len(strata) >= min_strata
            and len(seed_blocks) >= min_seed_blocks
            and math.isfinite(mean_delta)
            and mean_delta <= -0.001
            and (not upper or number(upper, 9.0) <= 0)
            and better > worse
            and success_rate_delta >= 0
            and fingerprint_all
            and recognized_all
            and cost_all
        )
        board.append(
            {
                "candidate_id": cid,
                "stage": stage,
                "candidate_family": raw.get("family", ""),
                "candidate_rows": len(group),
                "raw_generated_rows": raw_rows,
                "success_regression_count_vs_static_flow": regressions,
                "success_gain_count_vs_static_flow": gains,
                "success_rate_delta_vs_static_flow": csv_number(success_rate_delta),
                "both_success_quality_pairs_vs_static_flow": both,
                "both_success_quality_delta_mean_vs_static_flow": "" if not math.isfinite(mean_delta) else csv_number(mean_delta),
                "bootstrap_ci_upper": upper,
                "better_count_vs_static_flow": better,
                "worse_count_vs_static_flow": worse,
                "support_strata": len(strata),
                "support_seed_blocks": len(seed_blocks),
                "fingerprint_match_rate": csv_number(int(number(raw.get("fingerprint"), 0)) / max(1, raw_rows)),
                "candidate_recognized_all": recognized_all,
                "cost_finite_all": cost_all,
                "theta_in_bounds_all": True,
                "validation_ready" if stage == "stage1" else "shortlist_ready": ready,
                "not_ready_reason": "" if ready else (
                    "success_regression"
                    if regressions > 0
                    else "insufficient_support"
                    if len(group) < min_rows or len(strata) < min_strata or len(seed_blocks) < min_seed_blocks
                    else "quality_gate_not_met"
                    if not math.isfinite(mean_delta) or mean_delta > -0.001 or better <= worse
                    else "materialization_gate_not_met"
                ),
                "distance_from_current_static_flow": csv_number(theta_distance(theta)) if theta else "",
                **{col: theta.get(col, "") for col in THETA_COLUMNS},
                **claims(),
            }
        )
    board.sort(
        key=lambda row: (
            int(number(row.get("success_regression_count_vs_static_flow"), 10**9)),
            not boolish(row.get("validation_ready", row.get("shortlist_ready", False))),
            -int(number(row.get("candidate_rows"), 0)),
            number(row.get("both_success_quality_delta_mean_vs_static_flow"), 9.0),
            number(row.get("distance_from_current_static_flow"), 9.0),
        )
    )
    by_rows = []
    top_ids = {row["candidate_id"] for row in board[:50]}
    for (cid, fam, agents, budget, horizon), group in sorted(by_stratum.items()):
        if cid not in top_ids:
            continue
        deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in group if str(row.get("quality_delta_ratio", "")).strip()]
        by_rows.append(
            {
                "candidate_id": cid,
                "map_family": fam,
                "agents": agents,
                "nominal_budget_ms": budget,
                "horizon_id": horizon,
                "rows": len(group),
                "success_regression_count_vs_static_flow": sum(1 for row in group if boolish(row.get("success_regression"))),
                "both_success_quality_pairs_vs_static_flow": sum(1 for row in group if boolish(row.get("both_success"))),
                "both_success_quality_delta_mean_vs_static_flow": safe_mean(deltas),
                "better_count_vs_static_flow": sum(1 for row in group if boolish(row.get("better"))),
                "worse_count_vs_static_flow": sum(1 for row in group if boolish(row.get("worse"))),
                **claims(),
            }
        )
    sensitivity = []
    top_zero = [row for row in board if int(number(row.get("success_regression_count_vs_static_flow"), 0)) == 0][:200]
    for col in THETA_COLUMNS:
        vals = [number(row.get(col), math.nan) for row in top_zero]
        vals = [v for v in vals if math.isfinite(v)]
        sensitivity.append(
            {
                "theta_parameter": col,
                "top_zero_regression_candidate_count": len(top_zero),
                "min": "" if not vals else csv_number(min(vals)),
                "max": "" if not vals else csv_number(max(vals)),
                "mean": "" if not vals else csv_number(statistics.fmean(vals)),
                "current_static_flow_value": current_theta().get(col, ""),
                **claims(),
            }
        )
    return board, by_rows, failures, sensitivity


def main_run_stage0b_materialization_and_field_smoke(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 Stage0B")
    if not resolve(SEARCH_SUMMARY).exists() or args.overwrite:
        main_create_trust_region_search_space(["--candidate-count", str(max(16000, args.candidate_count))])
    registry = load_registry()[:1000]
    plan = plan_rows(split="stage0b", context_count=50, seed_start=1000, candidates=registry, candidates_per_context=200)
    write_rows(STAGE0B_PLAN_LOG, plan)
    rows = run_probe(
        plan=plan,
        args=args,
        result_csv=STAGE0B_RESULTS_LOG,
        raw_csv=STAGE0B_RAW_LOG,
        log_dir=STAGE0B_LOG_DIR,
        run_jsonl=STAGE0B_RUN_JSONL,
        command_jsonl=STAGE0B_COMMAND_JSONL,
        update_jsonl=STAGE0B_UPDATE_JSONL,
        probe_jsonl=STAGE0B_PROBE_JSONL,
        checkpoint_jsonl=STAGE0B_CHECKPOINT_JSONL,
        status_json=STAGE0B_STATUS_JSON,
        scenario_dir=STAGE0B_SCENARIO_DIR,
        scenario_metadata=STAGE0B_SCENARIO_METADATA,
        manifest_prefix="g554_stage0b",
        row_prefix="g554_stage0b_probe",
        execution_mode="new_g554_stage0b_materialization_field_smoke_solver_row",
    )
    print(json.dumps({"decision": "g554_stage0b_executed", "rows": len(rows)}))
    return 0


def main_analyze_stage0b_materialization_and_field_smoke(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 Stage0B analysis")
    if not resolve(STAGE0B_RESULTS_LOG).exists():
        rc = main_run_stage0b_materialization_and_field_smoke([])
        if rc != 0:
            return rc
    rows = read_rows(STAGE0B_RESULTS_LOG)
    failures = materialization_failures(rows)
    board, _by, pair_failures, _sens = leaderboard_from_results(rows, min_rows=1, min_strata=1, min_seed_blocks=1, stage="stage0b")
    survivors = [row for row in board if int(number(row.get("success_regression_count_vs_static_flow"), 0)) == 0]
    generated = generated_rows(rows)
    match_rate = sum(1 for row in generated if boolish(row.get("fulltheta_fingerprint_match", True))) / max(1, len(generated))
    families = []
    for family, count in Counter(row.get("candidate_family", "") for row in generated).items():
        fam_rows = [row for row in board if row.get("candidate_family") == family]
        families.append(
            {
                "candidate_family": family,
                "generated_rows": count,
                "candidate_vectors": len(fam_rows),
                "zero_regression_candidates": sum(1 for row in fam_rows if int(number(row.get("success_regression_count_vs_static_flow"), 0)) == 0),
                "mean_quality_delta_vs_static_flow": safe_mean([row.get("both_success_quality_delta_mean_vs_static_flow") for row in fam_rows]),
                **claims(),
            }
        )
    summary = {
        "schema_version": "phase5p5_repair5g554_stage0b_smoke_summary_v1",
        "decision": "g554_stage0b_smoke_passed" if rows and not failures and len(generated) >= 10000 and len({r.get("candidate_id") for r in generated}) >= 1000 else "g554_fingerprint_or_materialization_blocked",
        "stage0b_candidate_vectors": len({row.get("candidate_id") for row in generated}),
        "stage0b_solver_rows": len(rows),
        "stage0b_contexts": len({row.get("context_horizon_key") for row in rows}),
        "baseline_static_flow_rows": sum(1 for row in rows if row.get("role") == "static_flow_shield"),
        "materialization_failure_rows": len(failures),
        "stage0b_obvious_regressions": len(pair_failures),
        "stage0b_surviving_candidates": len(survivors),
        "candidate_recognized_all": bool(generated) and all(boolish(row.get("candidate_recognized", True)) for row in generated),
        "fulltheta_fingerprint_match_rate": csv_number(match_rate),
        "cost_finite_all": bool(generated) and all(boolish(row.get("cost_finite_all", row.get("repair5g_costs_finite", True))) for row in generated),
        "current_hand_static_flow_reproduced": any(row.get("candidate_id") == STATIC_FLOW for row in rows),
        **claims(),
    }
    write_rows(STAGE0B_SURVIVORS_CSV, survivors[:3000])
    write_rows(STAGE0B_FAILURES_CSV, failures[:2000])
    write_rows(STAGE0B_OBVIOUS_REG_CSV, pair_failures[:2000])
    write_rows(STAGE0B_FIELD_RESPONSE_CSV, families)
    write_json(STAGE0B_SUMMARY, summary)
    write_text(
        STAGE0B_REPORT,
        "# G5.54 Stage0B Materialization and Field Smoke\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- solver rows: `{summary['stage0b_solver_rows']}`\n"
        f"- contexts: `{summary['stage0b_contexts']}`\n"
        f"- candidate vectors: `{summary['stage0b_candidate_vectors']}`\n"
        f"- fingerprint match rate: `{summary['fulltheta_fingerprint_match_rate']}`\n"
        f"- materialization failures: `{summary['materialization_failure_rows']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows)}))
    return 0


def main_run_stage1_fresh_screening(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 Stage1 fresh screening")
    if not resolve(STAGE0B_SUMMARY).exists():
        main_analyze_stage0b_materialization_and_field_smoke([])
    registry = load_registry()[:3000]
    plan = plan_rows(split="stage1", context_count=STAGE1_CONTEXT_COUNT, seed_start=2000, candidates=registry, candidates_per_context=253)
    write_rows(STAGE1_PLAN_LOG, plan)
    rows = run_probe(
        plan=plan,
        args=args,
        result_csv=STAGE1_RESULTS_LOG,
        raw_csv=STAGE1_RAW_LOG,
        log_dir=STAGE1_LOG_DIR,
        run_jsonl=STAGE1_RUN_JSONL,
        command_jsonl=STAGE1_COMMAND_JSONL,
        update_jsonl=STAGE1_UPDATE_JSONL,
        probe_jsonl=STAGE1_PROBE_JSONL,
        checkpoint_jsonl=STAGE1_CHECKPOINT_JSONL,
        status_json=STAGE1_STATUS_JSON,
        scenario_dir=STAGE1_SCENARIO_DIR,
        scenario_metadata=STAGE1_SCENARIO_METADATA,
        manifest_prefix="g554_stage1",
        row_prefix="g554_stage1_probe",
        execution_mode="new_g554_stage1_fresh_screening_solver_row",
    )
    print(json.dumps({"decision": "g554_stage1_fresh_screening_executed", "rows": len(rows)}))
    return 0


def write_stage1_outputs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    board, by_rows, failures, sensitivity = leaderboard_from_results(rows, min_rows=1000, min_strata=4, min_seed_blocks=8, stage="stage1")
    ready = [row for row in board if boolish(row.get("validation_ready"))]
    zero_reg = [row for row in board if int(number(row.get("success_regression_count_vs_static_flow"), 0)) == 0]
    low_reg_high_gain = [
        row
        for row in board
        if int(number(row.get("success_regression_count_vs_static_flow"), 0)) <= 2
        and number(row.get("both_success_quality_delta_mean_vs_static_flow"), 9.0) <= -0.001
    ]
    frontier = []
    for row in board[:1000]:
        frontier.append(
            {
                "candidate_id": row.get("candidate_id", ""),
                "success_regression_count_vs_static_flow": row.get("success_regression_count_vs_static_flow", ""),
                "quality_delta_mean_vs_static_flow": row.get("both_success_quality_delta_mean_vs_static_flow", ""),
                "candidate_rows": row.get("candidate_rows", ""),
                "frontier_class": "validation_ready" if boolish(row.get("validation_ready")) else "near_miss_expand" if row in zero_reg[:100] or row in low_reg_high_gain[:100] else "reject_or_diagnostic",
                **claims(),
            }
        )
    generated = generated_rows(rows)
    summary = {
        "schema_version": "phase5p5_repair5g554_stage1_fresh_screening_summary_v1",
        "decision": "g554_stage1_candidate_found_continue_stage2" if ready else "g554_stage1_nearmisses_found_continue_expansion",
        "candidate_vectors_screened": len({row.get("candidate_id") for row in generated}),
        "contexts": len({row.get("context_horizon_key") for row in rows}),
        "stage1_new_solver_rows": len(rows),
        "minimum_new_stage1_solver_rows_met": len(rows) >= 256000,
        "preferred_new_stage1_solver_rows_met": len(rows) >= 512000,
        "baseline_static_flow_reference_rows": sum(1 for row in rows if row.get("role") == "static_flow_shield"),
        "stage1_validation_ready_candidates": len(ready),
        "zero_regression_candidates": len(zero_reg),
        "low_regression_high_gain_candidates": len(low_reg_high_gain),
        "search_phase_candidates_may_have_regressions": True,
        **claims(),
    }
    write_rows(STAGE1_LEADERBOARD_CSV, board[:3000])
    write_rows(STAGE1_BY_STRATUM_CSV, by_rows[:5000])
    write_rows(STAGE1_FRONTIER_CSV, frontier)
    write_rows(STAGE1_ZERO_REG_CSV, zero_reg[:3000])
    write_rows(STAGE1_LOW_REG_HIGH_GAIN_CSV, low_reg_high_gain[:3000])
    write_rows(STAGE1_FAILURE_CASES_CSV, failures[:3000])
    write_rows(STAGE1_PARAMETER_SENS_CSV, sensitivity)
    write_json(STAGE1_SUMMARY, summary)
    write_text(
        STAGE1_REPORT,
        "# G5.54 Stage1 Fresh Screening\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- new solver rows: `{summary['stage1_new_solver_rows']}`\n"
        f"- contexts: `{summary['contexts']}`\n"
        f"- candidate vectors screened: `{summary['candidate_vectors_screened']}`\n"
        f"- validation-ready candidates: `{summary['stage1_validation_ready_candidates']}`\n"
        f"- zero-regression candidates: `{summary['zero_regression_candidates']}`\n"
        f"- low-regression high-gain candidates: `{summary['low_regression_high_gain_candidates']}`\n\n"
        "This stage uses fresh paired solver replay, not reused Label-v2 rows.\n",
    )
    return summary


def main_analyze_stage1_fresh_screening(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 Stage1 analysis")
    if not resolve(STAGE1_RESULTS_LOG).exists():
        rc = main_run_stage1_fresh_screening([])
        if rc != 0:
            return rc
    summary = write_stage1_outputs(read_rows(STAGE1_RESULTS_LOG))
    print(json.dumps({"decision": summary["decision"], "rows": summary["stage1_new_solver_rows"]}))
    return 0


def stage2_candidates() -> list[dict[str, Any]]:
    if not resolve(STAGE1_LEADERBOARD_CSV).exists():
        main_analyze_stage1_fresh_screening([])
    board = read_rows(STAGE1_LEADERBOARD_CSV)
    registry = {row["candidate_id"]: row for row in load_registry()}
    selected: list[dict[str, Any]] = []

    def add(rows: list[dict[str, Any]], label: str, limit: int) -> None:
        for row in rows:
            cid = row.get("candidate_id", "")
            if cid in registry and cid not in {s["candidate_id"] for s in selected}:
                out = dict(registry[cid])
                out["stage2_selection_bucket"] = label
                selected.append(out)
            if sum(1 for s in selected if s.get("stage2_selection_bucket") == label) >= limit:
                break

    zero_low = [
        row
        for row in board
        if int(number(row.get("success_regression_count_vs_static_flow"), 0)) == 0
        and int(number(row.get("candidate_rows"), 0)) < 2000
    ]
    low_reg_gain = [
        row
        for row in board
        if int(number(row.get("success_regression_count_vs_static_flow"), 0)) <= 2
        and number(row.get("both_success_quality_delta_mean_vs_static_flow"), 9.0) <= -0.001
    ]
    hand_trust = [row for row in board if str(row.get("candidate_family", "")).startswith(("trust_region", "one_factor", "two_factor", "coordinate"))]
    negative = [row for row in board if row.get("candidate_family") == "negative_controls_wide_random"]
    add(zero_low, "top_zero_regression_low_support", 50)
    add(low_reg_gain, "top_low_regression_high_gain", 50)
    add(hand_trust, "top_hand_trust_region", 50)
    add(negative, "negative_control", 20)
    for row in load_registry():
        if len(selected) >= 170:
            break
        if row["candidate_id"] not in {s["candidate_id"] for s in selected}:
            out = dict(row)
            out["stage2_selection_bucket"] = "registry_backfill"
            selected.append(out)
    return selected[:170]


def main_create_stage2_nearmiss_expansion_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 Stage2 plan")
    candidates = stage2_candidates()
    plan = plan_rows(split="stage2", context_count=STAGE2_CONTEXT_COUNT, seed_start=4000, candidates=candidates, candidates_per_context=len(candidates))
    write_rows(STAGE2_PLAN_LOG, plan)
    write_rows(STAGE2_PLAN_PREVIEW_CSV, plan[:1000])
    bucket_counts = Counter(row.get("stage2_selection_bucket", "") for row in candidates)
    summary = {
        "schema_version": "phase5p5_repair5g554_stage2_nearmiss_expansion_plan_summary_v1",
        "decision": "g554_stage2_nearmiss_expansion_plan_created",
        "planned_solver_rows": len(plan),
        "candidate_count": len(candidates),
        "planned_contexts": STAGE2_CONTEXT_COUNT,
        "candidate_rows_per_candidate_target": 2000,
        "bucket_counts": dict(bucket_counts),
        **claims(),
    }
    write_json(STAGE2_PLAN_SUMMARY, summary)
    write_text(
        STAGE2_PLAN_REPORT,
        "# G5.54 Stage2 Near-Miss Expansion Plan\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- planned solver rows: `{summary['planned_solver_rows']}`\n"
        f"- candidates: `{summary['candidate_count']}`\n"
        f"- contexts: `{summary['planned_contexts']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(plan), "candidates": len(candidates)}))
    return 0


def main_run_stage2_nearmiss_expansion(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 Stage2 run")
    if not resolve(STAGE2_PLAN_LOG).exists() or args.overwrite:
        main_create_stage2_nearmiss_expansion_plan([])
    plan = read_rows(STAGE2_PLAN_LOG)
    rows = run_probe(
        plan=plan,
        args=args,
        result_csv=STAGE2_RESULTS_LOG,
        raw_csv=STAGE2_RAW_LOG,
        log_dir=STAGE2_LOG_DIR,
        run_jsonl=STAGE2_RUN_JSONL,
        command_jsonl=STAGE2_COMMAND_JSONL,
        update_jsonl=STAGE2_UPDATE_JSONL,
        probe_jsonl=STAGE2_PROBE_JSONL,
        checkpoint_jsonl=STAGE2_CHECKPOINT_JSONL,
        status_json=STAGE2_STATUS_JSON,
        scenario_dir=STAGE2_SCENARIO_DIR,
        scenario_metadata=STAGE2_SCENARIO_METADATA,
        manifest_prefix="g554_stage2",
        row_prefix="g554_stage2_probe",
        execution_mode="new_g554_stage2_nearmiss_expansion_solver_row",
    )
    print(json.dumps({"decision": "g554_stage2_nearmiss_expansion_executed", "rows": len(rows)}))
    return 0


def main_analyze_stage2_nearmiss_expansion(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 Stage2 analysis")
    if not resolve(STAGE2_RESULTS_LOG).exists():
        rc = main_run_stage2_nearmiss_expansion([])
        if rc != 0:
            return rc
    rows = read_rows(STAGE2_RESULTS_LOG)
    board, by_rows, failures, _sensitivity = leaderboard_from_results(rows, min_rows=2000, min_strata=6, min_seed_blocks=12, stage="stage2")
    shortlist = [row for row in board if boolish(row.get("shortlist_ready"))]
    ci_rows = [
        {
            "candidate_id": row.get("candidate_id", ""),
            "candidate_rows": row.get("candidate_rows", ""),
            "mean_quality_delta_vs_static_flow": row.get("both_success_quality_delta_mean_vs_static_flow", ""),
            "bootstrap_ci_upper": row.get("bootstrap_ci_upper", ""),
            "success_regression_count_vs_static_flow": row.get("success_regression_count_vs_static_flow", ""),
            **claims(),
        }
        for row in board
    ]
    summary = {
        "schema_version": "phase5p5_repair5g554_stage2_nearmiss_expansion_summary_v1",
        "decision": "g554_stage2_shortlist_ready_continue_validation" if shortlist else "g554_no_fixed_global_candidate_after_fresh_search_keep_hand_baseline",
        "stage2_new_solver_rows": len(rows),
        "minimum_stage2_new_solver_rows_met": len(rows) >= 256000,
        "preferred_stage2_new_solver_rows_met": len(rows) >= 512000,
        "candidate_vectors_expanded": len({row.get("candidate_id") for row in generated_rows(rows)}),
        "contexts": len({row.get("context_horizon_key") for row in rows}),
        "stage2_validation_shortlist_count": len(shortlist),
        "best_candidate_id": board[0].get("candidate_id", "") if board else "",
        "best_candidate_success_regressions_vs_static_flow": board[0].get("success_regression_count_vs_static_flow", "") if board else "",
        "best_candidate_quality_delta_vs_static_flow": board[0].get("both_success_quality_delta_mean_vs_static_flow", "") if board else "",
        **claims(),
    }
    write_rows(STAGE2_LEADERBOARD_CSV, board[:3000])
    write_rows(STAGE2_BY_STRATUM_CSV, by_rows[:8000])
    write_rows(STAGE2_CI_CSV, ci_rows[:3000])
    write_rows(STAGE2_SHORTLIST_CSV, shortlist[:50])
    write_rows(STAGE2_FAILURE_CASES_CSV, failures[:3000])
    write_json(STAGE2_SUMMARY, summary)
    write_text(
        STAGE2_REPORT,
        "# G5.54 Stage2 Near-Miss Expansion\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- new solver rows: `{summary['stage2_new_solver_rows']}`\n"
        f"- contexts: `{summary['contexts']}`\n"
        f"- expanded candidates: `{summary['candidate_vectors_expanded']}`\n"
        f"- validation shortlist count: `{summary['stage2_validation_shortlist_count']}`\n\n"
        "If no shortlist exists, the fresh Stage1+Stage2 frontier supports keeping hand static_flow as the primary baseline for this round.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "shortlist": len(shortlist)}))
    return 0


def write_validation_skip(reason: str) -> None:
    write_rows(VALIDATION_PLAN_LOG, [])
    write_rows(VALIDATION_RESULTS_LOG, [])
    for path in [VALIDATION_LEADERBOARD_CSV, VALIDATION_BY_STRATUM_CSV, VALIDATION_ADDITIVE_CSV, VALIDATION_FAILURE_CASES_CSV]:
        write_rows(path, [])
    plan_summary = {
        "schema_version": "phase5p5_repair5g554_validation_plan_summary_v1",
        "decision": "g554_validation_plan_skipped_no_stage2_shortlist",
        "planned_solver_rows": 0,
        "skip_reason": reason,
        **claims(),
    }
    summary = {
        "schema_version": "phase5p5_repair5g554_validation_summary_v1",
        "decision": "g554_validation_skipped_no_stage2_shortlist",
        "validation_run": False,
        "validation_new_solver_rows": 0,
        "heldout_candidates": 0,
        "gate_passed": False,
        "skip_reason": reason,
        **claims(),
    }
    write_json(VALIDATION_PLAN_SUMMARY, plan_summary)
    write_json(VALIDATION_SUMMARY, summary)
    write_text(VALIDATION_PLAN_REPORT, f"# G5.54 Validation Plan\n\n- decision: `{plan_summary['decision']}`\n- reason: `{reason}`\n")
    write_text(VALIDATION_REPORT, f"# G5.54 Fresh Validation\n\n- decision: `{summary['decision']}`\n- validation run: `False`\n")


def main_create_validation_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 validation plan")
    if not resolve(STAGE2_SUMMARY).exists():
        main_analyze_stage2_nearmiss_expansion([])
    shortlist = read_rows(STAGE2_SHORTLIST_CSV)[:10]
    if not shortlist:
        write_validation_skip("stage2_validation_shortlist_empty")
        print(json.dumps({"decision": "g554_validation_plan_skipped_no_stage2_shortlist"}))
        return 0
    candidates = []
    for row in shortlist:
        candidates.append(
            {
                "candidate_id": row.get("candidate_id", ""),
                "candidate_family": row.get("candidate_family", "stage2_shortlist"),
                "theta_cluster": "validation_shortlist",
                "registry_row_id": row.get("candidate_id", ""),
                **{col: row.get(col, "") for col in THETA_COLUMNS},
                **claims(),
            }
        )
    plan = plan_rows(
        split="validation",
        context_count=12000,
        seed_start=9000,
        candidates=candidates,
        candidates_per_context=len(candidates),
    )
    write_rows(VALIDATION_PLAN_LOG, plan)
    write_json(
        VALIDATION_PLAN_SUMMARY,
        {
            "schema_version": "phase5p5_repair5g554_validation_plan_summary_v1",
            "decision": "g554_validation_plan_created",
            "planned_solver_rows": len(plan),
            "heldout_candidates": len(candidates),
            "planned_contexts": 12000,
            "fresh_seeds_only": True,
            **claims(),
        },
    )
    write_text(
        VALIDATION_PLAN_REPORT,
        "# G5.54 Validation Plan\n\n"
        "- decision: `g554_validation_plan_created`\n"
        f"- heldout candidates: `{len(candidates)}`\n"
        f"- planned solver rows: `{len(plan)}`\n",
    )
    print(json.dumps({"decision": "g554_validation_plan_created", "candidates": len(candidates), "rows": len(plan)}))
    return 0


def main_run_validation(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 validation run")
    if not resolve(VALIDATION_PLAN_SUMMARY).exists():
        main_create_validation_plan([])
    plan_summary = load_json(VALIDATION_PLAN_SUMMARY, {})
    if plan_summary.get("decision") != "g554_validation_plan_created":
        print(json.dumps({"decision": plan_summary.get("decision", "")}))
        return 0
    rows = run_probe(
        plan=read_rows(VALIDATION_PLAN_LOG),
        args=args,
        result_csv=VALIDATION_RESULTS_LOG,
        raw_csv=VALIDATION_RAW_LOG,
        log_dir=VALIDATION_LOG_DIR,
        run_jsonl=VALIDATION_RUN_JSONL,
        command_jsonl=VALIDATION_COMMAND_JSONL,
        update_jsonl=VALIDATION_UPDATE_JSONL,
        probe_jsonl=VALIDATION_PROBE_JSONL,
        checkpoint_jsonl=VALIDATION_CHECKPOINT_JSONL,
        status_json=VALIDATION_STATUS_JSON,
        scenario_dir=VALIDATION_SCENARIO_DIR,
        scenario_metadata=VALIDATION_SCENARIO_METADATA,
        manifest_prefix="g554_validation",
        row_prefix="g554_validation_probe",
        execution_mode="new_g554_validation_solver_row",
    )
    print(json.dumps({"decision": "g554_validation_executed", "rows": len(rows)}))
    return 0


def main_analyze_validation(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 validation analysis")
    plan_summary = load_json(VALIDATION_PLAN_SUMMARY, {})
    if plan_summary.get("decision") and plan_summary.get("decision") != "g554_validation_plan_created":
        write_validation_skip(str(plan_summary.get("skip_reason", "stage2_validation_shortlist_empty")))
        print(json.dumps({"decision": "g554_validation_skipped_no_stage2_shortlist", "rows": 0, "passed": 0}))
        return 0
    if not resolve(VALIDATION_SUMMARY).exists():
        if not resolve(VALIDATION_RESULTS_LOG).exists():
            main_run_validation([])
    if not resolve(VALIDATION_RESULTS_LOG).exists():
        print(json.dumps({"decision": load_json(VALIDATION_SUMMARY, {}).get("decision", "")}))
        return 0
    rows = read_rows(VALIDATION_RESULTS_LOG)
    board, by_rows, failures, _sens = leaderboard_from_results(rows, min_rows=10000, min_strata=6, min_seed_blocks=12, stage="validation")
    passed = [
        row
        for row in board
        if boolish(row.get("shortlist_ready"))
        and int(number(row.get("success_regression_count_vs_static_flow"), 1)) == 0
        and number(row.get("success_rate_delta_vs_static_flow"), -1.0) >= 0
    ]
    vs_static, _vs_family, vs_additive, _pair_failures = g549.result_pairs(rows)
    add_rows = []
    for row in vs_additive[:5000]:
        add_rows.append({**row, **claims()})
    summary = {
        "schema_version": "phase5p5_repair5g554_validation_summary_v1",
        "decision": "g554_validation_passed_continue_blind" if passed else "g554_validation_failed_keep_hand_baseline",
        "validation_run": True,
        "validation_new_solver_rows": len(rows),
        "minimum_validation_solver_rows_met": len(rows) >= 120000,
        "preferred_validation_solver_rows_met": len(rows) >= 240000,
        "heldout_candidates": len({row.get("candidate_id") for row in generated_rows(rows)}),
        "gate_passed": bool(passed),
        "passing_candidate_count": len(passed),
        "best_candidate_id": board[0].get("candidate_id", "") if board else "",
        "success_regression_count_vs_static_flow": board[0].get("success_regression_count_vs_static_flow", "") if board else "",
        "success_rate_delta_vs_static_flow": board[0].get("success_rate_delta_vs_static_flow", "") if board else "",
        "both_success_quality_delta_mean_vs_static_flow": board[0].get("both_success_quality_delta_mean_vs_static_flow", "") if board else "",
        **claims(),
    }
    write_rows(VALIDATION_LEADERBOARD_CSV, board[:1000])
    write_rows(VALIDATION_BY_STRATUM_CSV, by_rows[:5000])
    write_rows(VALIDATION_ADDITIVE_CSV, add_rows)
    write_rows(VALIDATION_FAILURE_CASES_CSV, failures[:3000])
    write_json(VALIDATION_SUMMARY, summary)
    write_text(
        VALIDATION_REPORT,
        "# G5.54 Fresh Validation\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- validation rows: `{summary['validation_new_solver_rows']}`\n"
        f"- heldout candidates: `{summary['heldout_candidates']}`\n"
        f"- gate passed: `{summary['gate_passed']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "passed": len(passed)}))
    return 0


def write_blind_skip(reason: str) -> None:
    write_rows(BLIND_PLAN_LOG, [])
    write_rows(BLIND_RESULTS_LOG, [])
    for path in [BLIND_LEADERBOARD_CSV, BLIND_BY_STRATUM_CSV, BLIND_FAILURE_CASES_CSV]:
        write_rows(path, [])
    plan_summary = {
        "schema_version": "phase5p5_repair5g554_blind_plan_summary_v1",
        "decision": "g554_blind_plan_skipped_validation_gate_not_met",
        "planned_solver_rows": 0,
        "skip_reason": reason,
        **claims(),
    }
    summary = {
        "schema_version": "phase5p5_repair5g554_blind_summary_v1",
        "decision": "g554_blind_skipped_validation_gate_not_met",
        "blind_replay_run": False,
        "blind_new_solver_rows": 0,
        "gate_passed": False,
        "skip_reason": reason,
        **claims(),
    }
    write_json(BLIND_PLAN_SUMMARY, plan_summary)
    write_json(BLIND_SUMMARY, summary)
    write_text(BLIND_PLAN_REPORT, f"# G5.54 Blind Replay Plan\n\n- decision: `{plan_summary['decision']}`\n- reason: `{reason}`\n")
    write_text(BLIND_REPORT, f"# G5.54 Blind Replay\n\n- decision: `{summary['decision']}`\n- blind replay run: `False`\n")


def main_create_blind_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 blind plan")
    if not resolve(VALIDATION_SUMMARY).exists():
        main_analyze_validation([])
    validation = load_json(VALIDATION_SUMMARY, {})
    if not boolish(validation.get("gate_passed")):
        write_blind_skip("validation_gate_not_met")
        print(json.dumps({"decision": "g554_blind_plan_skipped_validation_gate_not_met"}))
        return 0
    candidates = read_rows(VALIDATION_LEADERBOARD_CSV)
    candidates = [
        row
        for row in candidates
        if boolish(row.get("shortlist_ready"))
        and int(number(row.get("success_regression_count_vs_static_flow"), 1)) == 0
    ][:3]
    if not candidates:
        write_blind_skip("validation_passed_but_no_candidate_rows")
        print(json.dumps({"decision": "g554_blind_plan_skipped_no_candidate_rows"}))
        return 0
    blind_candidates = [
        {
            "candidate_id": row.get("candidate_id", ""),
            "candidate_family": row.get("candidate_family", "validation_passed"),
            "theta_cluster": "blind_candidate",
            "registry_row_id": row.get("candidate_id", ""),
            **{col: row.get(col, "") for col in THETA_COLUMNS},
            **claims(),
        }
        for row in candidates
    ]
    plan = plan_rows(
        split="blind",
        context_count=24000,
        seed_start=30000,
        candidates=blind_candidates,
        candidates_per_context=len(blind_candidates),
    )
    write_rows(BLIND_PLAN_LOG, plan)
    write_json(
        BLIND_PLAN_SUMMARY,
        {
            "schema_version": "phase5p5_repair5g554_blind_plan_summary_v1",
            "decision": "g554_blind_plan_created",
            "planned_solver_rows": len(plan),
            "blind_candidate_count": len(blind_candidates),
            "fresh_seeds_only": True,
            "no_tuning_after_plan_created": True,
            **claims(),
        },
    )
    write_text(
        BLIND_PLAN_REPORT,
        "# G5.54 Blind Replay Plan\n\n"
        "- decision: `g554_blind_plan_created`\n"
        f"- blind candidates: `{len(blind_candidates)}`\n"
        f"- planned solver rows: `{len(plan)}`\n",
    )
    print(json.dumps({"decision": "g554_blind_plan_created", "candidates": len(blind_candidates), "rows": len(plan)}))
    return 0


def main_run_blind_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 blind run")
    if not resolve(BLIND_PLAN_SUMMARY).exists():
        main_create_blind_if_warranted([])
    plan_summary = load_json(BLIND_PLAN_SUMMARY, {})
    if plan_summary.get("decision") != "g554_blind_plan_created":
        print(json.dumps({"decision": plan_summary.get("decision", "")}))
        return 0
    rows = run_probe(
        plan=read_rows(BLIND_PLAN_LOG),
        args=args,
        result_csv=BLIND_RESULTS_LOG,
        raw_csv=BLIND_RAW_LOG,
        log_dir=BLIND_LOG_DIR,
        run_jsonl=BLIND_RUN_JSONL,
        command_jsonl=BLIND_COMMAND_JSONL,
        update_jsonl=BLIND_UPDATE_JSONL,
        probe_jsonl=BLIND_PROBE_JSONL,
        checkpoint_jsonl=BLIND_CHECKPOINT_JSONL,
        status_json=BLIND_STATUS_JSON,
        scenario_dir=BLIND_SCENARIO_DIR,
        scenario_metadata=BLIND_SCENARIO_METADATA,
        manifest_prefix="g554_blind",
        row_prefix="g554_blind_probe",
        execution_mode="new_g554_blind_solver_row",
    )
    print(json.dumps({"decision": "g554_blind_executed", "rows": len(rows)}))
    return 0


def main_analyze_blind_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 blind analysis")
    plan_summary = load_json(BLIND_PLAN_SUMMARY, {})
    if plan_summary.get("decision") and plan_summary.get("decision") != "g554_blind_plan_created":
        write_blind_skip(str(plan_summary.get("skip_reason", "validation_gate_not_met")))
        print(json.dumps({"decision": "g554_blind_skipped_validation_gate_not_met", "rows": 0, "passed": 0}))
        return 0
    if not resolve(BLIND_SUMMARY).exists():
        if not resolve(BLIND_RESULTS_LOG).exists():
            main_run_blind_if_warranted([])
    if not resolve(BLIND_RESULTS_LOG).exists():
        print(json.dumps({"decision": load_json(BLIND_SUMMARY, {}).get("decision", "")}))
        return 0
    rows = read_rows(BLIND_RESULTS_LOG)
    board, by_rows, failures, _sens = leaderboard_from_results(rows, min_rows=10000, min_strata=6, min_seed_blocks=12, stage="blind")
    passed = [
        row
        for row in board
        if boolish(row.get("shortlist_ready"))
        and int(number(row.get("success_regression_count_vs_static_flow"), 1)) == 0
        and number(row.get("success_rate_delta_vs_static_flow"), -1.0) >= 0
        and number(row.get("both_success_quality_delta_mean_vs_static_flow"), 9.0) <= -0.001
    ]
    summary = {
        "schema_version": "phase5p5_repair5g554_blind_summary_v1",
        "decision": "g554_blind_passed_fixed_candidate_found" if passed else "g554_blind_failed_keep_hand_baseline",
        "blind_replay_run": True,
        "blind_new_solver_rows": len(rows),
        "minimum_blind_solver_rows_met": len(rows) >= 120000,
        "preferred_blind_solver_rows_met": len(rows) >= 240000,
        "blind_candidate_count": len({row.get("candidate_id") for row in generated_rows(rows)}),
        "gate_passed": bool(passed),
        "passing_candidate_count": len(passed),
        "best_candidate_id": board[0].get("candidate_id", "") if board else "",
        "success_regression_count_vs_static_flow": board[0].get("success_regression_count_vs_static_flow", "") if board else "",
        "success_rate_delta_vs_static_flow": board[0].get("success_rate_delta_vs_static_flow", "") if board else "",
        "both_success_quality_delta_mean_vs_static_flow": board[0].get("both_success_quality_delta_mean_vs_static_flow", "") if board else "",
        **claims(),
    }
    write_rows(BLIND_LEADERBOARD_CSV, board[:1000])
    write_rows(BLIND_BY_STRATUM_CSV, by_rows[:5000])
    write_rows(BLIND_FAILURE_CASES_CSV, failures[:3000])
    write_json(BLIND_SUMMARY, summary)
    write_text(
        BLIND_REPORT,
        "# G5.54 Blind Replay\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- blind rows: `{summary['blind_new_solver_rows']}`\n"
        f"- candidates: `{summary['blind_candidate_count']}`\n"
        f"- gate passed: `{summary['gate_passed']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "passed": len(passed)}))
    return 0


def large_artifact_manifest_rows() -> list[dict[str, Any]]:
    paths = [
        CANDIDATE_REGISTRY_LOG,
        STAGE0B_PLAN_LOG,
        STAGE0B_RESULTS_LOG,
        STAGE1_PLAN_LOG,
        STAGE1_RESULTS_LOG,
        STAGE2_PLAN_LOG,
        STAGE2_RESULTS_LOG,
        VALIDATION_PLAN_LOG,
        VALIDATION_RESULTS_LOG,
        BLIND_PLAN_LOG,
        BLIND_RESULTS_LOG,
    ]
    resume = {
        CANDIDATE_REGISTRY_LOG: "python scripts/create_repair5g554_trust_region_search_space.py --candidate-count 16000",
        STAGE0B_RESULTS_LOG: "python scripts/run_repair5g554_stage0b_materialization_and_field_smoke.py --row-limit 10000 --max-workers 16",
        STAGE1_RESULTS_LOG: "python scripts/run_repair5g554_stage1_fresh_screening.py --row-limit 260000 --max-workers 22",
        STAGE2_RESULTS_LOG: "python scripts/run_repair5g554_stage2_nearmiss_expansion.py --row-limit 360000 --max-workers 22",
        VALIDATION_RESULTS_LOG: "python scripts/run_repair5g554_validation.py --row-limit 130000 --max-workers 22",
        BLIND_RESULTS_LOG: "python scripts/run_repair5g554_blind_if_warranted.py --row-limit 130000 --max-workers 22",
    }
    rows = []
    for path in paths:
        p = resolve(path)
        rows.append(
            {
                "path": path,
                "exists": p.exists(),
                "rows": table_count(path),
                "bytes": p.stat().st_size if p.exists() else 0,
                "sha256": file_sha256(path) if p.exists() and p.stat().st_size <= 50 * 1024 * 1024 else "",
                "commit_policy": "do_not_commit_raw_outputs_logs" if str(path).startswith("outputs/logs/") else "commit_if_compact",
                "exact_resume_command": resume.get(path, ""),
                **claims(),
            }
        )
    return rows


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.54 decision")
    steps = [
        (main_verify_g553_artifacts, G553_VERIFY_SUMMARY),
        (main_audit_g553_negative_result, G553_NEG_SUMMARY),
        (main_audit_active_staticflow_fields, ACTIVE_FIELD_SUMMARY),
        (main_create_nearmiss_candidate_pool, NEARMISS_SUMMARY),
        (main_create_trust_region_search_space, SEARCH_SUMMARY),
        (main_analyze_stage0b_materialization_and_field_smoke, STAGE0B_SUMMARY),
        (main_analyze_stage1_fresh_screening, STAGE1_SUMMARY),
        (main_analyze_stage2_nearmiss_expansion, STAGE2_SUMMARY),
        (main_analyze_validation, VALIDATION_SUMMARY),
        (main_analyze_blind_if_warranted, BLIND_SUMMARY),
    ]
    for func, path in steps:
        if args.overwrite or not resolve(path).exists():
            func([])
    verify = load_json(G553_VERIFY_SUMMARY, {})
    stage0 = load_json(STAGE0B_SUMMARY, {})
    stage1 = load_json(STAGE1_SUMMARY, {})
    stage2 = load_json(STAGE2_SUMMARY, {})
    validation = load_json(VALIDATION_SUMMARY, {})
    blind = load_json(BLIND_SUMMARY, {})
    if verify.get("decision") == "g554_g553_verification_blocked" or stage0.get("decision") == "g554_fingerprint_or_materialization_blocked":
        decision = "g554_fingerprint_or_materialization_blocked"
    elif int(number(stage1.get("stage1_new_solver_rows"), 0)) < 256000:
        decision = "g554_stage1_underpowered_continue_fresh_screening"
    elif int(number(stage2.get("stage2_new_solver_rows"), 0)) < 256000:
        decision = "g554_nearmisses_found_continue_expansion"
    elif int(number(stage2.get("stage2_validation_shortlist_count"), 0)) == 0:
        decision = "g554_no_fixed_global_candidate_after_fresh_search_keep_hand_baseline"
    elif not boolish(validation.get("gate_passed")):
        decision = "g554_validation_failed_keep_hand_baseline"
    elif not boolish(blind.get("gate_passed")):
        decision = "g554_blind_failed_keep_hand_baseline"
    else:
        decision = "g554_fixed_global_staticflow_coefficients_candidate_found_keep_claims_closed"
    promoted = decision == "g554_fixed_global_staticflow_coefficients_candidate_found_keep_claims_closed"
    claim_rows = []
    for statement in [
        "G5.54 evaluates fixed global static_flow coefficient vectors only.",
        "No dynamic learned policy, selector, checkpoint policy, or abstention gate is opened.",
        "Current hand static_flow_shield remains primary unless validation and blind gates pass with zero success regression.",
        "All Phase5.5, Phase6, runtime, learned-runtime, and AAAI claims remain closed.",
    ]:
        claim_rows.append({"ledger_statement": statement, "status": "closed_or_governance_active", **claims()})
    for stage, obj in [("verify", verify), ("stage0b", stage0), ("stage1", stage1), ("stage2", stage2), ("validation", validation), ("blind", blind)]:
        for key in CLAIM_KEYS:
            claim_rows.append({"stage": stage, "claim_flag": key, "value": obj.get(key, False), "closed": not boolish(obj.get(key, False)), **claims()})
    final_theta = []
    if promoted and resolve(STAGE2_SHORTLIST_CSV).exists():
        final_theta = read_rows(STAGE2_SHORTLIST_CSV)[:1]
    else:
        final_theta = [{"promoted": False, "reason": "no fixed-global coefficient vector passed G5.54 fresh Stage2/validation/blind gates", **current_theta(), **claims()}]
    summary = {
        "schema_version": "phase5p5_repair5g554_decision_summary_v1",
        "decision": decision,
        "primary_baseline": "current hand static_flow_shield",
        "dynamic_learned_policy_paused": True,
        "candidate_object": "one fixed global coefficient vector",
        "stage1_new_solver_rows": stage1.get("stage1_new_solver_rows", 0),
        "stage2_new_solver_rows": stage2.get("stage2_new_solver_rows", 0),
        "validation_new_solver_rows": validation.get("validation_new_solver_rows", 0),
        "blind_new_solver_rows": blind.get("blind_new_solver_rows", 0),
        "best_candidate_id": stage2.get("best_candidate_id", ""),
        "best_candidate_success_regressions_vs_static_flow": stage2.get("best_candidate_success_regressions_vs_static_flow", ""),
        "best_candidate_quality_delta_vs_static_flow": stage2.get("best_candidate_quality_delta_vs_static_flow", ""),
        "validation_passed": boolish(validation.get("gate_passed")),
        "blind_passed": boolish(blind.get("gate_passed")),
        "optimized_fixed_candidate_promoted": promoted,
        "should_hand_static_flow_remain_primary": not promoted,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
        "git_head": git_short_head(),
        "external_lacam2_clean": external_lacam2_clean(),
    }
    write_rows(CLAIM_LEDGER_CSV, claim_rows)
    write_rows(FINAL_CANDIDATE_THETA_CSV, final_theta)
    write_rows(LARGE_ARTIFACT_MANIFEST_CSV, large_artifact_manifest_rows())
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.54 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- Stage1 new solver rows: `{summary['stage1_new_solver_rows']}`\n"
        f"- Stage2 new solver rows: `{summary['stage2_new_solver_rows']}`\n"
        f"- best candidate: `{summary['best_candidate_id']}`\n"
        f"- optimized fixed candidate promoted: `{promoted}`\n"
        f"- hand static_flow remains primary: `{summary['should_hand_static_flow_remain_primary']}`\n\n"
        "G5.54 keeps dynamic learned UpdateParams policy work paused. It does not open runtime, Phase5.5, Phase6, learned-runtime, or AAAI claims.\n",
    )
    print(json.dumps({"decision": decision}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]

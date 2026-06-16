"""Repair5G.5.55 fixed-global staticflow analysis-gate repair.

G5.55 audits and repairs the G5.54 fixed-global static_flow analysis layer.
It recomputes leaderboards from raw paired replay rows with the pair schema as
the source of truth, then runs validation/blind replay only if the corrected
gate produces a shortlist.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))
else:  # pragma: no cover
    ROOT = Path(__file__).resolve().parents[1]

import repair5g549_common as g549  # noqa: E402
import repair5g553_common as g553  # noqa: E402
import repair5g554_common as g554  # noqa: E402
from repair5g531_common import (  # noqa: E402
    boolish,
    claims,
    csv_number,
    external_lacam2_clean,
    load_json,
    number,
    read_rows,
    resolve,
    write_json,
    write_rows,
    write_text,
)


ROUND = "repair5g555"
PLAN_FILE = "czr004_g555_fixed_staticflow_analysis_repair_plan.md"
CLAIM_KEYS = list(claims().keys())
MAX_VALIDATION_CANDIDATES = 8
MAX_BLIND_CANDIDATES = 3

G554_DECISION_SUMMARY = g554.DECISION_SUMMARY
G554_STAGE0B_SUMMARY = g554.STAGE0B_SUMMARY
G554_STAGE1_SUMMARY = g554.STAGE1_SUMMARY
G554_STAGE2_SUMMARY = g554.STAGE2_SUMMARY
G554_VALIDATION_SUMMARY = g554.VALIDATION_SUMMARY
G554_STAGE1_RESULTS = g554.STAGE1_RESULTS_LOG
G554_STAGE2_RESULTS = g554.STAGE2_RESULTS_LOG
G554_STAGE2_LEADERBOARD = g554.STAGE2_LEADERBOARD_CSV
G554_STAGE2_BY_STRATUM = g554.STAGE2_BY_STRATUM_CSV
G554_STAGE2_SHORTLIST = g554.STAGE2_SHORTLIST_CSV

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g555_g554_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g555_g554_verification_summary.json"
ARTIFACT_AUDIT_CSV = "outputs/tables/phase5p5_repair5g555_g554_artifact_audit.csv"
CLAIM_FLAG_AUDIT_CSV = "outputs/tables/phase5p5_repair5g555_g554_claim_flag_audit.csv"

PAIR_AUDIT_REPORT = "outputs/reports/phase5p5_repair5g555_pair_schema_gate_bug_audit.md"
PAIR_AUDIT_SUMMARY = "outputs/reports/phase5p5_repair5g555_pair_schema_gate_bug_audit_summary.json"
PAIR_SCHEMA_COLUMNS_CSV = "outputs/tables/phase5p5_repair5g555_pair_schema_columns.csv"
SUCCESS_FIELD_MAPPING_CSV = "outputs/tables/phase5p5_repair5g555_success_field_mapping_audit.csv"
STAGE2_INCONSISTENCY_CSV = "outputs/tables/phase5p5_repair5g555_stage2_leaderboard_inconsistency_audit.csv"
NOT_READY_REASON_CSV = "outputs/tables/phase5p5_repair5g555_not_ready_reason_audit.csv"

LEADERBOARD_REPORT = "outputs/reports/phase5p5_repair5g555_corrected_leaderboard.md"
LEADERBOARD_SUMMARY = "outputs/reports/phase5p5_repair5g555_corrected_leaderboard_summary.json"
STAGE1_CORRECTED_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g555_stage1_corrected_candidate_leaderboard.csv"
STAGE2_CORRECTED_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g555_stage2_corrected_candidate_leaderboard.csv"
STAGE2_CORRECTED_SHORTLIST_CSV = "outputs/tables/phase5p5_repair5g555_stage2_corrected_validation_shortlist.csv"
STAGE2_CORRECTED_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g555_stage2_corrected_by_stratum.csv"
CORRECTED_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g555_corrected_failure_cases.csv"

VALIDATION_PLAN_REPORT = "outputs/reports/phase5p5_repair5g555_corrected_validation_plan.md"
VALIDATION_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g555_corrected_validation_plan_summary.json"
VALIDATION_PLAN_PREVIEW_CSV = "outputs/tables/phase5p5_repair5g555_validation_plan_preview.csv"
VALIDATION_CANDIDATE_THETA_CSV = "outputs/tables/phase5p5_repair5g555_validation_candidate_theta.csv"
VALIDATION_LOG_DIR = "outputs/logs/phase5p5_repair5g555_validation"
VALIDATION_PLAN_LOG = f"{VALIDATION_LOG_DIR}/validation_plan.csv"
VALIDATION_RESULTS_LOG = f"{VALIDATION_LOG_DIR}/validation_results.csv"
VALIDATION_RAW_LOG = f"{VALIDATION_LOG_DIR}/validation_results.raw.csv"
VALIDATION_RUN_JSONL = f"{VALIDATION_LOG_DIR}/runs.jsonl"
VALIDATION_COMMAND_JSONL = f"{VALIDATION_LOG_DIR}/commands.jsonl"
VALIDATION_UPDATE_JSONL = f"{VALIDATION_LOG_DIR}/updates.jsonl"
VALIDATION_PROBE_JSONL = f"{VALIDATION_LOG_DIR}/counterfactual_probes.jsonl"
VALIDATION_CHECKPOINT_JSONL = f"{VALIDATION_LOG_DIR}/checkpoints.jsonl"
VALIDATION_STATUS_JSON = f"{VALIDATION_LOG_DIR}/status.json"
VALIDATION_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g555_validation_scenarios"
VALIDATION_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g555_validation_scenario_generation.json"
VALIDATION_REPORT = "outputs/reports/phase5p5_repair5g555_corrected_validation.md"
VALIDATION_SUMMARY = "outputs/reports/phase5p5_repair5g555_corrected_validation_summary.json"
VALIDATION_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g555_validation_candidate_leaderboard.csv"
VALIDATION_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g555_validation_by_stratum.csv"
VALIDATION_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g555_validation_vs_additive_diagnostic.csv"
VALIDATION_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g555_validation_failure_cases.csv"

BLIND_PLAN_REPORT = "outputs/reports/phase5p5_repair5g555_blind_plan.md"
BLIND_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g555_blind_plan_summary.json"
BLIND_LOG_DIR = "outputs/logs/phase5p5_repair5g555_blind"
BLIND_PLAN_LOG = f"{BLIND_LOG_DIR}/blind_plan.csv"
BLIND_RESULTS_LOG = f"{BLIND_LOG_DIR}/blind_results.csv"
BLIND_RAW_LOG = f"{BLIND_LOG_DIR}/blind_results.raw.csv"
BLIND_RUN_JSONL = f"{BLIND_LOG_DIR}/runs.jsonl"
BLIND_COMMAND_JSONL = f"{BLIND_LOG_DIR}/commands.jsonl"
BLIND_UPDATE_JSONL = f"{BLIND_LOG_DIR}/updates.jsonl"
BLIND_PROBE_JSONL = f"{BLIND_LOG_DIR}/counterfactual_probes.jsonl"
BLIND_CHECKPOINT_JSONL = f"{BLIND_LOG_DIR}/checkpoints.jsonl"
BLIND_STATUS_JSON = f"{BLIND_LOG_DIR}/status.json"
BLIND_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g555_blind_scenarios"
BLIND_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g555_blind_scenario_generation.json"
BLIND_REPORT = "outputs/reports/phase5p5_repair5g555_blind.md"
BLIND_SUMMARY = "outputs/reports/phase5p5_repair5g555_blind_summary.json"
BLIND_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g555_blind_candidate_leaderboard.csv"
BLIND_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g555_blind_by_stratum.csv"
BLIND_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g555_blind_failure_cases.csv"

DECISION_REPORT = "outputs/reports/phase5p5_repair5g555_decision.md"
DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g555_decision_summary.json"
CLAIM_LEDGER_CSV = "outputs/tables/phase5p5_repair5g555_claim_ledger.csv"
FINAL_CANDIDATE_THETA_CSV = "outputs/tables/phase5p5_repair5g555_final_candidate_theta.csv"
LARGE_ARTIFACT_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g555_large_artifact_manifest.csv"


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--overwrite", action="store_true")
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


def git_short_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def table_count(path: str | Path) -> int:
    return g554.table_count(path)


def file_bytes(path: str | Path) -> int:
    p = resolve(path)
    return p.stat().st_size if p.exists() else 0


def compact_sha256(path: str | Path) -> str:
    p = resolve(path)
    if not p.exists() or p.stat().st_size > 50 * 1024 * 1024:
        return ""
    return g554.file_sha256(path)


def all_claims_closed(obj: dict[str, Any]) -> bool:
    return all(not boolish(obj.get(key, False)) for key in CLAIM_KEYS)


def claim_rows_for(label: str, obj: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "source": label,
            "claim_flag": key,
            "value": obj.get(key, False),
            "closed": not boolish(obj.get(key, False)),
            **claims(),
        }
        for key in CLAIM_KEYS
    ]


def required_g554_artifacts() -> dict[str, str]:
    return {
        "decision_summary": G554_DECISION_SUMMARY,
        "stage0b_smoke_summary": G554_STAGE0B_SUMMARY,
        "stage1_fresh_screening_summary": G554_STAGE1_SUMMARY,
        "stage2_nearmiss_expansion_summary": G554_STAGE2_SUMMARY,
        "validation_summary": G554_VALIDATION_SUMMARY,
        "stage2_candidate_leaderboard": G554_STAGE2_LEADERBOARD,
        "stage2_candidate_by_stratum": G554_STAGE2_BY_STRATUM,
        "stage2_validation_shortlist": G554_STAGE2_SHORTLIST,
        "stage1_raw_results": G554_STAGE1_RESULTS,
        "stage2_raw_results": G554_STAGE2_RESULTS,
    }


def main_verify_g554_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.55 verify G5.54 artifacts")
    audit = []
    for artifact, path in required_g554_artifacts().items():
        p = resolve(path)
        audit.append(
            {
                "artifact": artifact,
                "path": path,
                "exists": p.exists(),
                "rows_or_file": table_count(path) if p.exists() else 0,
                "bytes": file_bytes(path),
                "sha256_if_compact": compact_sha256(path),
                "commit_policy": "do_not_commit_raw_csv_over_50mb" if file_bytes(path) > 50 * 1024 * 1024 else "commit_if_in_scope",
                **claims(),
            }
        )
    decision = load_json(G554_DECISION_SUMMARY, {})
    stage0 = load_json(G554_STAGE0B_SUMMARY, {})
    stage1 = load_json(G554_STAGE1_SUMMARY, {})
    stage2 = load_json(G554_STAGE2_SUMMARY, {})
    validation = load_json(G554_VALIDATION_SUMMARY, {})
    checks = {
        "g554_decision": decision.get("decision") == "g554_no_fixed_global_candidate_after_fresh_search_keep_hand_baseline",
        "stage1_new_solver_rows": int(number(stage1.get("stage1_new_solver_rows"), -1)) == 260096,
        "stage2_new_solver_rows": int(number(stage2.get("stage2_new_solver_rows"), -1)) == 360013,
        "stage2_best_candidate_id": stage2.get("best_candidate_id") == "g554_c00894",
        "stage2_best_candidate_regressions": int(number(stage2.get("best_candidate_success_regressions_vs_static_flow"), -1)) == 0,
        "stage2_best_candidate_delta": abs(number(stage2.get("best_candidate_quality_delta_vs_static_flow"), math.nan) - (-0.0315924946469)) < 1.0e-10,
        "validation_new_solver_rows": int(number(validation.get("validation_new_solver_rows"), 0)) == 0,
        "dynamic_learned_policy_paused": bool(decision.get("dynamic_learned_policy_paused", True)),
        "all_claim_flags_closed": all_claims_closed(decision) and all_claims_closed(stage0) and all_claims_closed(stage1) and all_claims_closed(stage2) and all_claims_closed(validation),
        "external_lacam2_clean": external_lacam2_clean(),
    }
    missing = [row for row in audit if not boolish(row["exists"])]
    claim_audit = []
    for label, obj in [
        ("g554_decision", decision),
        ("g554_stage0b", stage0),
        ("g554_stage1", stage1),
        ("g554_stage2", stage2),
        ("g554_validation", validation),
    ]:
        claim_audit.extend(claim_rows_for(label, obj))
    ok = not missing and all(checks.values())
    summary = {
        "schema_version": "phase5p5_repair5g555_g554_verification_summary_v1",
        "decision": "g555_g554_artifacts_verified" if ok else "g555_g554_raw_artifacts_missing_recover_or_rerun",
        "missing_artifacts": [row["artifact"] for row in missing],
        "checks": checks,
        "g554_decision": decision.get("decision", ""),
        "stage1_new_solver_rows": stage1.get("stage1_new_solver_rows", 0),
        "stage2_new_solver_rows": stage2.get("stage2_new_solver_rows", 0),
        "stage2_best_candidate_id": stage2.get("best_candidate_id", ""),
        "stage2_best_candidate_regressions": stage2.get("best_candidate_success_regressions_vs_static_flow", ""),
        "stage2_best_candidate_delta": stage2.get("best_candidate_quality_delta_vs_static_flow", ""),
        "validation_new_solver_rows": validation.get("validation_new_solver_rows", 0),
        "dynamic_learned_policy_paused": bool(decision.get("dynamic_learned_policy_paused", True)),
        "external_lacam2_clean": checks["external_lacam2_clean"],
        **claims(),
    }
    write_rows(ARTIFACT_AUDIT_CSV, audit)
    write_rows(CLAIM_FLAG_AUDIT_CSV, claim_audit)
    write_json(VERIFY_SUMMARY, summary)
    write_text(
        VERIFY_REPORT,
        "# G5.55 Verification of G5.54 Artifacts\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- missing artifacts: `{len(missing)}`\n"
        f"- G5.54 decision: `{summary['g554_decision']}`\n"
        f"- Stage1 rows: `{summary['stage1_new_solver_rows']}`\n"
        f"- Stage2 rows: `{summary['stage2_new_solver_rows']}`\n"
        f"- best Stage2 candidate: `{summary['stage2_best_candidate_id']}`\n"
        f"- external/lacam2 clean: `{summary['external_lacam2_clean']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "missing": len(missing)}))
    return 0 if ok else 2


def pair_rows_from_results(path: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows = read_rows(path)
    pairs, family_pairs, additive_pairs, pair_failures = g549.result_pairs(rows)
    return rows, pairs, family_pairs, additive_pairs, pair_failures


def theta_in_bounds(theta: dict[str, Any]) -> bool:
    if not theta:
        return False
    for col in g554.NUMERIC_THETA_COLUMNS:
        value = number(theta.get(col), math.nan)
        lo, hi = g554.THETA_BOUNDS[col]
        if not math.isfinite(value) or value < lo - 1.0e-12 or value > hi + 1.0e-12:
            return False
    mode_values = [int(number(theta.get(col), 0)) for col in g554.MODE_COLUMNS]
    return sum(1 for value in mode_values if value == 1) == 1


def goal_projection_mode(theta: dict[str, Any]) -> str:
    if boolish(theta.get("theta_goal_projection_mode_flow_shield")):
        return "flow_shield"
    if boolish(theta.get("theta_goal_projection_mode_agent_progress")):
        return "agent_progress"
    if boolish(theta.get("theta_goal_projection_mode_none")):
        return "none"
    return "unknown"


def ci_upper(values: list[float]) -> str:
    vals = [v for v in values if math.isfinite(v)]
    if not vals:
        return ""
    if len(vals) == 1:
        return csv_number(vals[0])
    return csv_number(statistics.fmean(vals) + 1.96 * statistics.stdev(vals) / math.sqrt(len(vals)))


def success_delta_from_selected(group: list[dict[str, Any]]) -> str:
    if not group:
        return ""
    if not all("selected_success" in row and "baseline_success" in row for row in group):
        return ""
    selected_success = sum(1 for row in group if boolish(row.get("selected_success")))
    baseline_success = sum(1 for row in group if boolish(row.get("baseline_success")))
    return csv_number((selected_success - baseline_success) / max(1, len(group)))


def success_delta_from_gain_regression(group: list[dict[str, Any]]) -> str:
    if not group:
        return ""
    gains = sum(1 for row in group if boolish(row.get("success_gain")))
    regressions = sum(1 for row in group if boolish(row.get("success_regression")))
    return csv_number((gains - regressions) / max(1, len(group)))


def corrected_leaderboard_from_results(
    rows: list[dict[str, Any]],
    *,
    min_rows: int,
    min_strata: int,
    min_seed_blocks: int,
    stage: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    pairs, _family_pairs, _additive_pairs, _pair_failures = g549.result_pairs(rows)
    rstats = g554.raw_stats(rows)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_stratum: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    failures: list[dict[str, Any]] = []
    for pair in pairs:
        cid = str(pair.get("selected_candidate", ""))
        if not cid:
            continue
        grouped[cid].append(pair)
        by_stratum[
            (
                cid,
                str(pair.get("map_family", "")),
                str(pair.get("agents", "")),
                str(pair.get("nominal_budget_ms", "")),
                str(pair.get("horizon_id", "")),
            )
        ].append(pair)
        if boolish(pair.get("success_regression")) and len(failures) < 3000:
            failures.append({**pair, "stage": stage, **claims()})
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
        selected_delta = success_delta_from_selected(group)
        gain_reg_delta = success_delta_from_gain_regression(group)
        success_rate_delta = selected_delta if selected_delta != "" else gain_reg_delta
        fingerprint_rate = int(number(raw.get("fingerprint"), 0)) / max(1, raw_rows)
        fingerprint_all = raw_rows > 0 and int(number(raw.get("fingerprint"), 0)) == raw_rows
        recognized_all = raw_rows > 0 and int(number(raw.get("recognized"), 0)) == raw_rows
        cost_all = raw_rows > 0 and int(number(raw.get("cost"), 0)) == raw_rows
        bounds_all = theta_in_bounds(theta)
        support_gate = len(group) >= min_rows and len(strata) >= min_strata and len(seed_blocks) >= min_seed_blocks
        quality_gate = math.isfinite(mean_delta) and mean_delta <= -0.001
        ci_gate = bool(upper) and number(upper, 9.0) <= 0
        better_gate = better > worse
        success_rate_gate = number(success_rate_delta, -1.0) >= 0
        materialization_gate = fingerprint_all and recognized_all and cost_all and bounds_all
        ready = regressions == 0 and success_rate_gate and support_gate and quality_gate and ci_gate and better_gate and materialization_gate
        if ready:
            reason = ""
        elif regressions > 0:
            reason = "success_regression"
        elif not success_rate_gate:
            reason = "success_rate_delta_gate_not_met"
        elif not support_gate:
            reason = "insufficient_support"
        elif not quality_gate:
            reason = "quality_gate_not_met"
        elif not ci_gate:
            reason = "confidence_interval_gate_not_met"
        elif not better_gate:
            reason = "better_worse_gate_not_met"
        elif not materialization_gate:
            reason = "materialization_gate_not_met"
        else:
            reason = "unknown_gate_not_met"
        board.append(
            {
                "candidate_id": cid,
                "stage": stage,
                "candidate_family": raw.get("family", ""),
                "candidate_rows": len(group),
                "raw_generated_rows": raw_rows,
                "success_regression_count_vs_static_flow": regressions,
                "success_gain_count_vs_static_flow": gains,
                "success_rate_delta_vs_static_flow": success_rate_delta,
                "success_rate_delta_from_selected_baseline": selected_delta,
                "success_rate_delta_from_gain_regression": gain_reg_delta,
                "success_rate_delta_source": "selected_success_minus_baseline_success" if selected_delta != "" else "success_gain_minus_success_regression",
                "both_success_quality_pairs_vs_static_flow": both,
                "both_success_quality_delta_mean_vs_static_flow": "" if not math.isfinite(mean_delta) else csv_number(mean_delta),
                "bootstrap_ci_upper": upper,
                "better_count_vs_static_flow": better,
                "worse_count_vs_static_flow": worse,
                "support_strata": len(strata),
                "support_seed_blocks": len(seed_blocks),
                "fulltheta_fingerprint_match_rate": csv_number(fingerprint_rate),
                "fingerprint_match_rate": csv_number(fingerprint_rate),
                "candidate_recognized_all": recognized_all,
                "cost_finite_all": cost_all,
                "theta_in_bounds_all": bounds_all,
                "materialization_gate_passed": materialization_gate,
                "support_gate_passed": support_gate,
                "quality_gate_passed": quality_gate,
                "ci_gate_passed": ci_gate,
                "better_worse_gate_passed": better_gate,
                "success_rate_gate_passed": success_rate_gate,
                "validation_ready" if stage == "stage1" else "shortlist_ready": ready,
                "not_ready_reason": reason,
                "distance_from_current_static_flow": csv_number(g554.theta_distance(theta)) if theta else "",
                "goal_projection_mode": goal_projection_mode(theta),
                "active_field_deltas": g554.active_deltas(theta) if theta else "",
                **{col: theta.get(col, "") for col in g554.THETA_COLUMNS},
                **claims(),
            }
        )
    ready_field = "validation_ready" if stage == "stage1" else "shortlist_ready"
    board.sort(
        key=lambda row: (
            int(number(row.get("success_regression_count_vs_static_flow"), 10**9)),
            not boolish(row.get(ready_field, False)),
            -int(number(row.get("candidate_rows"), 0)),
            number(row.get("bootstrap_ci_upper"), 9.0),
            number(row.get("both_success_quality_delta_mean_vs_static_flow"), 9.0),
            number(row.get("distance_from_current_static_flow"), 9.0),
        )
    )
    by_rows = []
    top_ids = {row["candidate_id"] for row in board[:80]}
    for (cid, fam, agents, budget, horizon), group in sorted(by_stratum.items()):
        if cid not in top_ids:
            continue
        deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in group if str(row.get("quality_delta_ratio", "")).strip()]
        deltas = [value for value in deltas if math.isfinite(value)]
        by_rows.append(
            {
                "candidate_id": cid,
                "stage": stage,
                "map_family": fam,
                "agents": agents,
                "nominal_budget_ms": budget,
                "horizon_id": horizon,
                "pair_rows": len(group),
                "success_regression_count": sum(1 for row in group if boolish(row.get("success_regression"))),
                "success_gain_count": sum(1 for row in group if boolish(row.get("success_gain"))),
                "success_rate_delta_from_selected_baseline": success_delta_from_selected(group),
                "success_rate_delta_from_gain_regression": success_delta_from_gain_regression(group),
                "quality_delta_mean": "" if not deltas else csv_number(statistics.fmean(deltas)),
                "better_count": sum(1 for row in group if boolish(row.get("better"))),
                "worse_count": sum(1 for row in group if boolish(row.get("worse"))),
                "seed_block_support": len({g553.seed_block(row.get("seed")) for row in group}),
                **claims(),
            }
        )
    return board, by_rows, failures


def existing_stage2_leaderboard_by_id() -> dict[str, dict[str, Any]]:
    return {str(row.get("candidate_id", "")): row for row in read_rows(G554_STAGE2_LEADERBOARD)}


def corrected_stage2_board_from_raw() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows = read_rows(G554_STAGE2_RESULTS)
    return corrected_leaderboard_from_results(rows, min_rows=2000, min_strata=6, min_seed_blocks=12, stage="stage2")


def stage2_inconsistency_rows(board: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    existing = existing_stage2_leaderboard_by_id()
    mapping_rows = []
    reason_rows = []
    for row in board:
        cid = row.get("candidate_id", "")
        old = existing.get(str(cid), {})
        old_delta = old.get("success_rate_delta_vs_static_flow", "")
        gain_delta = row.get("success_rate_delta_from_gain_regression", "")
        selected_delta = row.get("success_rate_delta_from_selected_baseline", "")
        regressions = int(number(row.get("success_regression_count_vs_static_flow"), 0))
        gains = int(number(row.get("success_gain_count_vs_static_flow"), 0))
        delta_bug = regressions == 0 and gains > 0 and number(gain_delta, 0.0) > 0 and number(old_delta, 0.0) < -0.5
        materialization_all_true = all(
            boolish(old.get(field, row.get(field, False)))
            for field in ["candidate_recognized_all", "cost_finite_all", "theta_in_bounds_all"]
        ) and number(old.get("fingerprint_match_rate", row.get("fingerprint_match_rate", 0)), 0) >= 1
        reason_misclassified = materialization_all_true and old.get("not_ready_reason", "") == "materialization_gate_not_met"
        mapping_rows.append(
            {
                "candidate_id": cid,
                "pair_rows": row.get("candidate_rows", ""),
                "success_regression_count_vs_static_flow": regressions,
                "success_gain_count_vs_static_flow": gains,
                "success_rate_delta_from_selected_baseline": selected_delta,
                "success_rate_delta_from_gain_regression": gain_delta,
                "success_rate_delta_from_existing_g554": old_delta,
                "g554_success_rate_delta_bug": delta_bug,
                "corrected_shortlist_ready": row.get("shortlist_ready", False),
                **claims(),
            }
        )
        reason_rows.append(
            {
                "candidate_id": cid,
                "existing_not_ready_reason": old.get("not_ready_reason", ""),
                "corrected_not_ready_reason": row.get("not_ready_reason", ""),
                "existing_shortlist_ready": old.get("shortlist_ready", ""),
                "corrected_shortlist_ready": row.get("shortlist_ready", ""),
                "fingerprint_match_rate": old.get("fingerprint_match_rate", row.get("fingerprint_match_rate", "")),
                "candidate_recognized_all": old.get("candidate_recognized_all", row.get("candidate_recognized_all", "")),
                "cost_finite_all": old.get("cost_finite_all", row.get("cost_finite_all", "")),
                "theta_in_bounds_all": old.get("theta_in_bounds_all", row.get("theta_in_bounds_all", "")),
                "materialization_gate_not_met_misclassified": reason_misclassified,
                **claims(),
            }
        )
    return mapping_rows, reason_rows


def main_audit_pair_schema_and_gate_bug(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.55 pair schema and gate audit")
    if not resolve(VERIFY_SUMMARY).exists():
        main_verify_g554_artifacts([])
    rows, pairs, _family_pairs, _additive_pairs, _pair_failures = pair_rows_from_results(G554_STAGE2_RESULTS)
    sample = pairs[0] if pairs else {}
    fields = [
        "selected_success",
        "contender_success",
        "candidate_success",
        "baseline_success",
        "success_regression",
        "success_gain",
        "both_success",
    ]
    schema_rows = []
    for field in fields:
        schema_rows.append(
            {
                "field": field,
                "present_in_pair_schema": field in sample,
                "nonblank_count_in_stage2_pairs": sum(1 for row in pairs if str(row.get(field, "")).strip() != ""),
                "true_count_in_stage2_pairs": sum(1 for row in pairs if boolish(row.get(field))),
                **claims(),
            }
        )
    board, _by_rows, _failures = corrected_leaderboard_from_results(rows, min_rows=2000, min_strata=6, min_seed_blocks=12, stage="stage2")
    mapping_rows, reason_rows = stage2_inconsistency_rows(board)
    bug_rows = [row for row in mapping_rows if boolish(row.get("g554_success_rate_delta_bug"))]
    misclassified_rows = [row for row in reason_rows if boolish(row.get("materialization_gate_not_met_misclassified"))]
    summary = {
        "schema_version": "phase5p5_repair5g555_pair_schema_gate_bug_audit_summary_v1",
        "decision": "g555_g554_analysis_gate_bug_confirmed" if bug_rows or misclassified_rows else "g555_g554_analysis_gate_bug_not_found",
        "stage2_raw_solver_rows": len(rows),
        "stage2_pair_rows_vs_static_flow": len(pairs),
        "pair_schema_contains_selected_success": "selected_success" in sample,
        "pair_schema_contains_contender_success": "contender_success" in sample,
        "pair_schema_contains_candidate_success": "candidate_success" in sample,
        "pair_schema_contains_baseline_success": "baseline_success" in sample,
        "g554_leaderboard_success_rate_delta_bug": bool(bug_rows),
        "g554_success_rate_delta_bug_candidate_count": len(bug_rows),
        "g554_not_ready_reason_misclassified": bool(misclassified_rows),
        "g554_not_ready_reason_misclassified_candidate_count": len(misclassified_rows),
        "g554_no_promotion_decision_analysis_confounded": bool(bug_rows or misclassified_rows),
        "top_bug_candidate_id": bug_rows[0].get("candidate_id", "") if bug_rows else "",
        **claims(),
    }
    write_rows(PAIR_SCHEMA_COLUMNS_CSV, schema_rows)
    write_rows(SUCCESS_FIELD_MAPPING_CSV, mapping_rows)
    write_rows(STAGE2_INCONSISTENCY_CSV, mapping_rows)
    write_rows(NOT_READY_REASON_CSV, reason_rows)
    write_json(PAIR_AUDIT_SUMMARY, summary)
    write_text(
        PAIR_AUDIT_REPORT,
        "# G5.55 Pair Schema and Gate Bug Audit\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- Stage2 raw rows: `{summary['stage2_raw_solver_rows']}`\n"
        f"- Stage2 vs-static pair rows: `{summary['stage2_pair_rows_vs_static_flow']}`\n"
        f"- selected_success present: `{summary['pair_schema_contains_selected_success']}`\n"
        f"- contender_success present: `{summary['pair_schema_contains_contender_success']}`\n"
        f"- success-rate delta bug confirmed: `{summary['g554_leaderboard_success_rate_delta_bug']}`\n"
        f"- not_ready_reason misclassified: `{summary['g554_not_ready_reason_misclassified']}`\n"
        f"- no-promotion decision analysis-confounded: `{summary['g554_no_promotion_decision_analysis_confounded']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "delta_bug": len(bug_rows), "reason_bug": len(misclassified_rows)}))
    return 0


def main_recompute_stage1_stage2_leaderboards(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.55 corrected leaderboard recomputation")
    if not resolve(PAIR_AUDIT_SUMMARY).exists():
        main_audit_pair_schema_and_gate_bug([])
    audit = load_json(PAIR_AUDIT_SUMMARY, {})
    stage1_rows = read_rows(G554_STAGE1_RESULTS)
    stage2_rows = read_rows(G554_STAGE2_RESULTS)
    stage1_board, _stage1_by, stage1_failures = corrected_leaderboard_from_results(stage1_rows, min_rows=1000, min_strata=4, min_seed_blocks=8, stage="stage1")
    stage2_board, stage2_by, stage2_failures = corrected_leaderboard_from_results(stage2_rows, min_rows=2000, min_strata=6, min_seed_blocks=12, stage="stage2")
    shortlist = [row for row in stage2_board if boolish(row.get("shortlist_ready"))]
    if not boolish(audit.get("g554_no_promotion_decision_analysis_confounded")):
        decision = "g555_g554_analysis_gate_bug_not_found_keep_g554_negative"
    elif shortlist:
        decision = "g555_g554_analysis_gate_bug_confirmed_recomputed_shortlist"
    else:
        decision = "g555_no_corrected_shortlist_keep_hand_staticflow"
    summary = {
        "schema_version": "phase5p5_repair5g555_corrected_leaderboard_summary_v1",
        "decision": decision,
        "g554_analysis_gate_bug_confirmed": boolish(audit.get("g554_no_promotion_decision_analysis_confounded")),
        "stage1_new_solver_rows": len(stage1_rows),
        "stage2_new_solver_rows": len(stage2_rows),
        "stage1_corrected_validation_ready_candidates": sum(1 for row in stage1_board if boolish(row.get("validation_ready"))),
        "corrected_stage2_shortlist_count": len(shortlist),
        "best_corrected_candidate_id": stage2_board[0].get("candidate_id", "") if stage2_board else "",
        "best_corrected_candidate_success_regressions_vs_static_flow": stage2_board[0].get("success_regression_count_vs_static_flow", "") if stage2_board else "",
        "best_corrected_candidate_quality_delta_vs_static_flow": stage2_board[0].get("both_success_quality_delta_mean_vs_static_flow", "") if stage2_board else "",
        "best_corrected_candidate_success_rate_delta_vs_static_flow": stage2_board[0].get("success_rate_delta_vs_static_flow", "") if stage2_board else "",
        "validation_required": bool(shortlist),
        **claims(),
    }
    failure_rows = stage1_failures[:1500] + stage2_failures[:1500]
    write_rows(STAGE1_CORRECTED_LEADERBOARD_CSV, stage1_board[:3000])
    write_rows(STAGE2_CORRECTED_LEADERBOARD_CSV, stage2_board[:3000])
    write_rows(STAGE2_CORRECTED_SHORTLIST_CSV, shortlist[:50])
    write_rows(STAGE2_CORRECTED_BY_STRATUM_CSV, stage2_by[:8000])
    write_rows(CORRECTED_FAILURE_CASES_CSV, failure_rows)
    write_json(LEADERBOARD_SUMMARY, summary)
    top_lines = []
    for row in stage2_board[:10]:
        top_lines.append(
            f"- `{row.get('candidate_id')}`: regressions={row.get('success_regression_count_vs_static_flow')}, "
            f"gains={row.get('success_gain_count_vs_static_flow')}, delta={row.get('both_success_quality_delta_mean_vs_static_flow')}, "
            f"ci_upper={row.get('bootstrap_ci_upper')}, success_rate_delta={row.get('success_rate_delta_vs_static_flow')}, "
            f"ready={row.get('shortlist_ready')}, mode={row.get('goal_projection_mode')}"
        )
    write_text(
        LEADERBOARD_REPORT,
        "# G5.55 Corrected Leaderboard\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- corrected Stage2 shortlist count: `{summary['corrected_stage2_shortlist_count']}`\n"
        f"- best corrected candidate: `{summary['best_corrected_candidate_id']}`\n"
        f"- best corrected success-rate delta: `{summary['best_corrected_candidate_success_rate_delta_vs_static_flow']}`\n\n"
        "## Top Corrected Stage2 Candidates\n\n"
        + "\n".join(top_lines)
        + "\n",
    )
    print(json.dumps({"decision": decision, "shortlist": len(shortlist), "best": summary["best_corrected_candidate_id"]}))
    return 0


def validation_candidate_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    mode = row.get("goal_projection_mode", "")
    return (
        0 if row.get("candidate_id") == "g554_c00894" else 1,
        int(number(row.get("success_regression_count_vs_static_flow"), 10**9)),
        number(row.get("bootstrap_ci_upper"), 9.0),
        number(row.get("both_success_quality_delta_mean_vs_static_flow"), 9.0),
        number(row.get("distance_from_current_static_flow"), 9.0),
        0 if mode == "flow_shield" else 1 if mode == "agent_progress" else 2,
    )


def write_validation_plan_skip(reason: str) -> None:
    empty_fields = ["candidate_id", "skip_reason"]
    write_rows(VALIDATION_PLAN_LOG, [], empty_fields)
    write_rows(VALIDATION_PLAN_PREVIEW_CSV, [], empty_fields)
    write_rows(VALIDATION_CANDIDATE_THETA_CSV, [], empty_fields)
    summary = {
        "schema_version": "phase5p5_repair5g555_corrected_validation_plan_summary_v1",
        "decision": "g555_validation_plan_skipped_no_corrected_shortlist",
        "planned_solver_rows": 0,
        "validation_candidate_count": 0,
        "skip_reason": reason,
        **claims(),
    }
    write_json(VALIDATION_PLAN_SUMMARY, summary)
    write_text(VALIDATION_PLAN_REPORT, f"# G5.55 Corrected Validation Plan\n\n- decision: `{summary['decision']}`\n- reason: `{reason}`\n")


def main_create_corrected_validation_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.55 corrected validation plan")
    if not resolve(LEADERBOARD_SUMMARY).exists() or args.overwrite:
        main_recompute_stage1_stage2_leaderboards([])
    corrected = load_json(LEADERBOARD_SUMMARY, {})
    shortlist = read_rows(STAGE2_CORRECTED_SHORTLIST_CSV)
    if not shortlist:
        write_validation_plan_skip("corrected_stage2_shortlist_empty")
        print(json.dumps({"decision": "g555_validation_plan_skipped_no_corrected_shortlist"}))
        return 0
    candidates = sorted(shortlist, key=validation_candidate_sort_key)[:MAX_VALIDATION_CANDIDATES]
    candidate_rows = []
    for row in candidates:
        candidate_rows.append(
            {
                "candidate_id": row.get("candidate_id", ""),
                "candidate_family": row.get("candidate_family", "corrected_stage2_shortlist"),
                "theta_cluster": "g555_corrected_shortlist",
                "registry_row_id": row.get("candidate_id", ""),
                "goal_projection_mode": row.get("goal_projection_mode", ""),
                "naming_note": "fixed_global_updateparams_not_flow_shield_replacement_name" if row.get("goal_projection_mode") in {"agent_progress", "none"} else "flow_shield_mode_candidate",
                **{col: row.get(col, "") for col in g554.THETA_COLUMNS},
                **claims(),
            }
        )
    plan = g554.plan_rows(
        split="validation",
        context_count=12000,
        seed_start=12000,
        candidates=candidate_rows,
        candidates_per_context=len(candidate_rows),
    )
    write_rows(VALIDATION_PLAN_LOG, plan)
    write_rows(VALIDATION_PLAN_PREVIEW_CSV, plan[:1000])
    write_rows(VALIDATION_CANDIDATE_THETA_CSV, candidate_rows)
    summary = {
        "schema_version": "phase5p5_repair5g555_corrected_validation_plan_summary_v1",
        "decision": "g555_corrected_validation_plan_created",
        "planned_solver_rows": len(plan),
        "validation_candidate_count": len(candidate_rows),
        "top_candidates_to_validate": len(candidate_rows),
        "candidate_rows_per_candidate_target": 12000,
        "minimum_validation_solver_rows_met_by_plan": len(plan) >= 120000,
        "preferred_validation_solver_rows_met_by_plan": len(plan) >= 240000,
        "fresh_heldout_seeds": True,
        "fresh_heldout_scenario_hashes": True,
        "corrected_stage2_shortlist_count": corrected.get("corrected_stage2_shortlist_count", len(shortlist)),
        **claims(),
    }
    mode_notes = "\n".join(f"- `{row['candidate_id']}`: `{row['goal_projection_mode']}` / `{row['naming_note']}`" for row in candidate_rows)
    write_json(VALIDATION_PLAN_SUMMARY, summary)
    write_text(
        VALIDATION_PLAN_REPORT,
        "# G5.55 Corrected Validation Plan\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- candidates: `{summary['validation_candidate_count']}`\n"
        f"- planned solver rows: `{summary['planned_solver_rows']}`\n"
        f"- candidate rows per candidate target: `{summary['candidate_rows_per_candidate_target']}`\n\n"
        "## Candidate Naming Notes\n\n"
        + mode_notes
        + "\n",
    )
    print(json.dumps({"decision": summary["decision"], "candidates": len(candidate_rows), "rows": len(plan)}))
    return 0


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
    return g554.run_probe(
        plan=plan,
        args=args,
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


def main_run_corrected_validation(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.55 corrected validation run")
    if not resolve(VALIDATION_PLAN_SUMMARY).exists() or args.overwrite:
        main_create_corrected_validation_plan([])
    plan_summary = load_json(VALIDATION_PLAN_SUMMARY, {})
    if plan_summary.get("decision") != "g555_corrected_validation_plan_created":
        print(json.dumps({"decision": plan_summary.get("decision", ""), "rows": 0}))
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
        manifest_prefix="g555_validation",
        row_prefix="g555_validation_probe",
        execution_mode="new_g555_corrected_validation_solver_row",
    )
    print(json.dumps({"decision": "g555_corrected_validation_executed", "rows": len(rows)}))
    return 0


def write_validation_pending(reason: str) -> None:
    summary = {
        "schema_version": "phase5p5_repair5g555_corrected_validation_summary_v1",
        "decision": "g555_corrected_validation_pending",
        "validation_run": False,
        "validation_new_solver_rows": 0,
        "validation_passed": False,
        "skip_reason": reason,
        "exact_resume_command": "python scripts/run_repair5g555_corrected_validation.py --row-limit 120000 --max-workers 20",
        **claims(),
    }
    write_json(VALIDATION_SUMMARY, summary)
    write_text(VALIDATION_REPORT, f"# G5.55 Corrected Validation\n\n- decision: `{summary['decision']}`\n- reason: `{reason}`\n")


def main_analyze_corrected_validation(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.55 corrected validation analysis")
    if not resolve(VALIDATION_PLAN_SUMMARY).exists():
        main_create_corrected_validation_plan([])
    plan_summary = load_json(VALIDATION_PLAN_SUMMARY, {})
    if plan_summary.get("decision") != "g555_corrected_validation_plan_created":
        write_validation_pending(plan_summary.get("skip_reason", "corrected_stage2_shortlist_empty"))
        print(json.dumps({"decision": "g555_validation_skipped_no_corrected_shortlist", "rows": 0, "passed": 0}))
        return 0
    if not resolve(VALIDATION_RESULTS_LOG).exists():
        write_validation_pending("validation_results_missing")
        print(json.dumps({"decision": "g555_corrected_validation_pending", "rows": 0, "passed": 0}))
        return 0
    rows = read_rows(VALIDATION_RESULTS_LOG)
    board, by_rows, failures = corrected_leaderboard_from_results(rows, min_rows=10000, min_strata=6, min_seed_blocks=12, stage="validation")
    passed = [
        row
        for row in board
        if boolish(row.get("shortlist_ready"))
        and int(number(row.get("success_regression_count_vs_static_flow"), 1)) == 0
        and number(row.get("success_rate_delta_vs_static_flow"), -1.0) >= 0
    ]
    _vs_static, _vs_family, vs_additive, _pair_failures = g549.result_pairs(rows)
    add_rows = [{**row, **claims()} for row in vs_additive[:5000]]
    summary = {
        "schema_version": "phase5p5_repair5g555_corrected_validation_summary_v1",
        "decision": "g555_corrected_validation_passed_continue_blind" if passed else "g555_corrected_validation_failed_keep_hand_staticflow",
        "validation_run": True,
        "validation_new_solver_rows": len(rows),
        "minimum_validation_solver_rows_met": len(rows) >= 120000,
        "preferred_validation_solver_rows_met": len(rows) >= 240000,
        "candidate_count": len({row.get("candidate_id") for row in g554.generated_rows(rows)}),
        "candidate_rows_per_candidate_min": min([int(number(row.get("candidate_rows"), 0)) for row in board] or [0]),
        "validation_passed": bool(passed),
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
        "# G5.55 Corrected Validation\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- validation rows: `{summary['validation_new_solver_rows']}`\n"
        f"- candidates: `{summary['candidate_count']}`\n"
        f"- gate passed: `{summary['validation_passed']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "passed": len(passed)}))
    return 0


def write_blind_skip(reason: str) -> None:
    empty_fields = ["candidate_id", "skip_reason"]
    write_rows(BLIND_PLAN_LOG, [], empty_fields)
    write_rows(BLIND_LEADERBOARD_CSV, [], empty_fields)
    write_rows(BLIND_BY_STRATUM_CSV, [], empty_fields)
    write_rows(BLIND_FAILURE_CASES_CSV, [], empty_fields)
    plan_summary = {
        "schema_version": "phase5p5_repair5g555_blind_plan_summary_v1",
        "decision": "g555_blind_plan_skipped_validation_gate_not_met",
        "planned_solver_rows": 0,
        "blind_candidate_count": 0,
        "skip_reason": reason,
        **claims(),
    }
    summary = {
        "schema_version": "phase5p5_repair5g555_blind_summary_v1",
        "decision": "g555_blind_skipped_validation_gate_not_met",
        "blind_run": False,
        "blind_new_solver_rows": 0,
        "blind_passed": False,
        "skip_reason": reason,
        **claims(),
    }
    write_json(BLIND_PLAN_SUMMARY, plan_summary)
    write_json(BLIND_SUMMARY, summary)
    write_text(BLIND_PLAN_REPORT, f"# G5.55 Blind Replay Plan\n\n- decision: `{plan_summary['decision']}`\n- reason: `{reason}`\n")
    write_text(BLIND_REPORT, f"# G5.55 Blind Replay\n\n- decision: `{summary['decision']}`\n- blind run: `False`\n")


def main_create_blind_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.55 blind plan")
    if not resolve(VALIDATION_SUMMARY).exists():
        main_analyze_corrected_validation([])
    validation = load_json(VALIDATION_SUMMARY, {})
    if not boolish(validation.get("validation_passed")):
        write_blind_skip(validation.get("decision", "validation_gate_not_met"))
        print(json.dumps({"decision": "g555_blind_plan_skipped_validation_gate_not_met"}))
        return 0
    candidates = [
        row
        for row in read_rows(VALIDATION_LEADERBOARD_CSV)
        if boolish(row.get("shortlist_ready")) and int(number(row.get("success_regression_count_vs_static_flow"), 1)) == 0
    ][:MAX_BLIND_CANDIDATES]
    if not candidates:
        write_blind_skip("validation_passed_but_no_candidate_rows")
        print(json.dumps({"decision": "g555_blind_plan_skipped_no_candidate_rows"}))
        return 0
    blind_candidates = [
        {
            "candidate_id": row.get("candidate_id", ""),
            "candidate_family": row.get("candidate_family", "validation_passed"),
            "theta_cluster": "g555_blind_candidate",
            "registry_row_id": row.get("candidate_id", ""),
            **{col: row.get(col, "") for col in g554.THETA_COLUMNS},
            **claims(),
        }
        for row in candidates
    ]
    plan = g554.plan_rows(
        split="blind",
        context_count=20000,
        seed_start=30000,
        candidates=blind_candidates,
        candidates_per_context=len(blind_candidates),
    )
    write_rows(BLIND_PLAN_LOG, plan)
    write_json(
        BLIND_PLAN_SUMMARY,
        {
            "schema_version": "phase5p5_repair5g555_blind_plan_summary_v1",
            "decision": "g555_blind_plan_created",
            "planned_solver_rows": len(plan),
            "blind_candidate_count": len(blind_candidates),
            "candidate_rows_per_candidate_target": 20000,
            "fresh_seeds_only": True,
            "no_tuning_after_plan_created": True,
            **claims(),
        },
    )
    write_text(
        BLIND_PLAN_REPORT,
        "# G5.55 Blind Replay Plan\n\n"
        "- decision: `g555_blind_plan_created`\n"
        f"- blind candidates: `{len(blind_candidates)}`\n"
        f"- planned solver rows: `{len(plan)}`\n",
    )
    print(json.dumps({"decision": "g555_blind_plan_created", "candidates": len(blind_candidates), "rows": len(plan)}))
    return 0


def main_run_blind_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.55 blind run")
    if not resolve(BLIND_PLAN_SUMMARY).exists() or args.overwrite:
        main_create_blind_if_warranted([])
    plan_summary = load_json(BLIND_PLAN_SUMMARY, {})
    if plan_summary.get("decision") != "g555_blind_plan_created":
        print(json.dumps({"decision": plan_summary.get("decision", ""), "rows": 0}))
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
        manifest_prefix="g555_blind",
        row_prefix="g555_blind_probe",
        execution_mode="new_g555_blind_solver_row",
    )
    print(json.dumps({"decision": "g555_blind_executed", "rows": len(rows)}))
    return 0


def write_blind_pending(reason: str) -> None:
    summary = {
        "schema_version": "phase5p5_repair5g555_blind_summary_v1",
        "decision": "g555_blind_pending",
        "blind_run": False,
        "blind_new_solver_rows": 0,
        "blind_passed": False,
        "skip_reason": reason,
        "exact_resume_command": "python scripts/run_repair5g555_blind_if_warranted.py --row-limit 120000 --max-workers 20",
        **claims(),
    }
    write_json(BLIND_SUMMARY, summary)
    write_text(BLIND_REPORT, f"# G5.55 Blind Replay\n\n- decision: `{summary['decision']}`\n- reason: `{reason}`\n")


def main_analyze_blind_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.55 blind analysis")
    if not resolve(BLIND_PLAN_SUMMARY).exists():
        main_create_blind_if_warranted([])
    plan_summary = load_json(BLIND_PLAN_SUMMARY, {})
    if plan_summary.get("decision") != "g555_blind_plan_created":
        write_blind_skip(plan_summary.get("skip_reason", "validation_gate_not_met"))
        print(json.dumps({"decision": "g555_blind_skipped_validation_gate_not_met", "rows": 0, "passed": 0}))
        return 0
    if not resolve(BLIND_RESULTS_LOG).exists():
        write_blind_pending("blind_results_missing")
        print(json.dumps({"decision": "g555_blind_pending", "rows": 0, "passed": 0}))
        return 0
    rows = read_rows(BLIND_RESULTS_LOG)
    board, by_rows, failures = corrected_leaderboard_from_results(rows, min_rows=10000, min_strata=6, min_seed_blocks=12, stage="blind")
    passed = [
        row
        for row in board
        if boolish(row.get("shortlist_ready"))
        and int(number(row.get("success_regression_count_vs_static_flow"), 1)) == 0
        and number(row.get("success_rate_delta_vs_static_flow"), -1.0) >= 0
        and number(row.get("both_success_quality_delta_mean_vs_static_flow"), 9.0) <= -0.001
    ]
    summary = {
        "schema_version": "phase5p5_repair5g555_blind_summary_v1",
        "decision": "g555_blind_passed_fixed_candidate_found" if passed else "g555_blind_failed_keep_hand_staticflow",
        "blind_run": True,
        "blind_new_solver_rows": len(rows),
        "minimum_blind_solver_rows_met": len(rows) >= 120000,
        "preferred_blind_solver_rows_met": len(rows) >= 240000,
        "blind_candidate_count": len({row.get("candidate_id") for row in g554.generated_rows(rows)}),
        "blind_passed": bool(passed),
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
        "# G5.55 Blind Replay\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- blind rows: `{summary['blind_new_solver_rows']}`\n"
        f"- candidates: `{summary['blind_candidate_count']}`\n"
        f"- gate passed: `{summary['blind_passed']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "passed": len(passed)}))
    return 0


def large_artifact_manifest_rows() -> list[dict[str, Any]]:
    paths = [
        G554_STAGE1_RESULTS,
        G554_STAGE2_RESULTS,
        VALIDATION_PLAN_LOG,
        VALIDATION_RESULTS_LOG,
        VALIDATION_RAW_LOG,
        BLIND_PLAN_LOG,
        BLIND_RESULTS_LOG,
        BLIND_RAW_LOG,
    ]
    resume = {
        G554_STAGE1_RESULTS: "source artifact from G5.54; do not commit raw CSV >50MB",
        G554_STAGE2_RESULTS: "source artifact from G5.54; do not commit raw CSV >50MB",
        VALIDATION_RESULTS_LOG: "python scripts/run_repair5g555_corrected_validation.py --row-limit 120000 --max-workers 20",
        BLIND_RESULTS_LOG: "python scripts/run_repair5g555_blind_if_warranted.py --row-limit 120000 --max-workers 8",
    }
    out = []
    for path in paths:
        p = resolve(path)
        out.append(
            {
                "path": path,
                "exists": p.exists(),
                "rows": table_count(path) if p.exists() else 0,
                "bytes": p.stat().st_size if p.exists() else 0,
                "sha256_if_compact": compact_sha256(path),
                "commit_policy": "do_not_commit_raw_outputs_logs" if str(path).startswith("outputs/logs/") else "commit_if_compact",
                "exact_resume_command": resume.get(path, ""),
                **claims(),
            }
        )
    return out


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.55 decision")
    if args.overwrite or not resolve(VERIFY_SUMMARY).exists():
        main_verify_g554_artifacts([])
    if args.overwrite or not resolve(PAIR_AUDIT_SUMMARY).exists():
        main_audit_pair_schema_and_gate_bug([])
    if args.overwrite or not resolve(LEADERBOARD_SUMMARY).exists():
        main_recompute_stage1_stage2_leaderboards([])
    if args.overwrite or not resolve(VALIDATION_PLAN_SUMMARY).exists():
        main_create_corrected_validation_plan([])
    if not resolve(VALIDATION_SUMMARY).exists():
        main_analyze_corrected_validation([])
    if not resolve(BLIND_PLAN_SUMMARY).exists():
        main_create_blind_if_warranted([])
    if not resolve(BLIND_SUMMARY).exists():
        main_analyze_blind_if_warranted([])

    verify = load_json(VERIFY_SUMMARY, {})
    audit = load_json(PAIR_AUDIT_SUMMARY, {})
    corrected = load_json(LEADERBOARD_SUMMARY, {})
    validation = load_json(VALIDATION_SUMMARY, {})
    blind = load_json(BLIND_SUMMARY, {})

    if verify.get("decision") == "g555_g554_raw_artifacts_missing_recover_or_rerun":
        decision = "g555_g554_raw_artifacts_missing_recover_or_rerun"
    elif not boolish(audit.get("g554_no_promotion_decision_analysis_confounded")):
        decision = "g555_g554_analysis_gate_bug_not_found_keep_g554_negative"
    elif int(number(corrected.get("corrected_stage2_shortlist_count"), 0)) == 0:
        decision = "g555_no_corrected_shortlist_keep_hand_staticflow"
    elif not boolish(validation.get("validation_run")):
        decision = "g555_g554_analysis_gate_bug_confirmed_recomputed_shortlist"
    elif not boolish(validation.get("validation_passed")):
        decision = "g555_corrected_validation_failed_keep_hand_staticflow"
    elif not boolish(blind.get("blind_run")):
        decision = "g555_fixed_global_staticflow_candidate_validated_keep_claims_closed"
    elif not boolish(blind.get("blind_passed")):
        decision = "g555_corrected_blind_failed_keep_hand_staticflow"
    else:
        decision = "g555_fixed_global_staticflow_candidate_blind_passed_keep_claims_closed"
    promoted = decision in {
        "g555_fixed_global_staticflow_candidate_validated_keep_claims_closed",
        "g555_fixed_global_staticflow_candidate_blind_passed_keep_claims_closed",
    }
    final_theta = []
    promoted_candidate_id = ""
    if promoted and boolish(blind.get("blind_passed")) and resolve(BLIND_LEADERBOARD_CSV).exists():
        final_theta = [row for row in read_rows(BLIND_LEADERBOARD_CSV) if boolish(row.get("shortlist_ready"))][:1]
        promoted_candidate_id = final_theta[0].get("candidate_id", "") if final_theta else ""
    elif promoted and resolve(VALIDATION_LEADERBOARD_CSV).exists():
        final_theta = [row for row in read_rows(VALIDATION_LEADERBOARD_CSV) if boolish(row.get("shortlist_ready"))][:1]
        promoted_candidate_id = final_theta[0].get("candidate_id", "") if final_theta else ""
    elif resolve(STAGE2_CORRECTED_SHORTLIST_CSV).exists() and int(number(corrected.get("corrected_stage2_shortlist_count"), 0)) > 0:
        final_theta = read_rows(STAGE2_CORRECTED_SHORTLIST_CSV)[:1]
    else:
        final_theta = [{"promoted": False, "reason": "no corrected fixed-global candidate completed promotion gates", **g554.current_theta(), **claims()}]
    previous_primary_baseline = "current hand static_flow_shield"
    primary_baseline = previous_primary_baseline
    if promoted:
        primary_baseline = (
            f"promoted fixed global staticflow candidate {promoted_candidate_id}"
            if promoted_candidate_id
            else "promoted fixed global staticflow candidate"
        )
    if promoted:
        baseline_result_sentence = (
            f"Corrected validation and blind replay promoted `{promoted_candidate_id}` as the stronger fixed staticflow baseline candidate; "
            "the hand static_flow_shield is no longer primary for this fixed-global route."
            if promoted_candidate_id
            else "Corrected validation/blind replay promoted a fixed global staticflow vector; the hand static_flow_shield is no longer primary for this fixed-global route."
        )
    else:
        baseline_result_sentence = "No corrected fixed-global vector completed promotion gates, so current hand static_flow_shield remains primary."
    claim_rows = []
    for statement in [
        "G5.55 keeps dynamic learned UpdateParams policy paused.",
        "G5.55 treats G5.54 no-promotion as analysis-confounded when pair-schema/gate bug is confirmed.",
        baseline_result_sentence,
        "All Phase5.5, Phase6, runtime, learned-runtime, and AAAI claims remain closed.",
    ]:
        claim_rows.append({"ledger_statement": statement, "status": "closed_or_governance_active", **claims()})
    for stage, obj in [
        ("verify", verify),
        ("pair_schema_gate_audit", audit),
        ("corrected_leaderboard", corrected),
        ("validation", validation),
        ("blind", blind),
    ]:
        claim_rows.extend(claim_rows_for(stage, obj))
    summary = {
        "schema_version": "phase5p5_repair5g555_decision_summary_v1",
        "decision": decision,
        "primary_baseline": primary_baseline,
        "previous_primary_baseline": previous_primary_baseline,
        "dynamic_learned_policy_paused": True,
        "g554_analysis_gate_bug_confirmed": boolish(audit.get("g554_no_promotion_decision_analysis_confounded")),
        "corrected_stage2_shortlist_count": corrected.get("corrected_stage2_shortlist_count", 0),
        "best_corrected_candidate_id": corrected.get("best_corrected_candidate_id", ""),
        "best_corrected_candidate_success_regressions_vs_static_flow": corrected.get("best_corrected_candidate_success_regressions_vs_static_flow", 0),
        "best_corrected_candidate_quality_delta_vs_static_flow": corrected.get("best_corrected_candidate_quality_delta_vs_static_flow", ""),
        "validation_run": boolish(validation.get("validation_run")),
        "validation_new_solver_rows": validation.get("validation_new_solver_rows", 0),
        "validation_passed": boolish(validation.get("validation_passed")),
        "blind_run": boolish(blind.get("blind_run")),
        "blind_passed": boolish(blind.get("blind_passed")),
        "optimized_fixed_candidate_promoted": promoted,
        "promoted_fixed_candidate_id": promoted_candidate_id,
        "best_blind_candidate_id": blind.get("best_candidate_id", ""),
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
        "# G5.55 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- G5.54 analysis/gate bug confirmed: `{summary['g554_analysis_gate_bug_confirmed']}`\n"
        f"- corrected Stage2 shortlist count: `{summary['corrected_stage2_shortlist_count']}`\n"
        f"- best corrected candidate: `{summary['best_corrected_candidate_id']}`\n"
        f"- validation rows: `{summary['validation_new_solver_rows']}`\n"
        f"- validation passed: `{summary['validation_passed']}`\n"
        f"- blind run: `{summary['blind_run']}`\n"
        f"- blind passed: `{summary['blind_passed']}`\n"
        f"- optimized fixed candidate promoted: `{summary['optimized_fixed_candidate_promoted']}`\n"
        f"- promoted fixed candidate: `{summary['promoted_fixed_candidate_id']}`\n"
        f"- primary baseline: `{summary['primary_baseline']}`\n"
        f"- hand static_flow remains primary: `{summary['should_hand_static_flow_remain_primary']}`\n\n"
        "G5.55 keeps dynamic learned UpdateParams policy paused and audits G5.54 fixed-global staticflow results. "
        "Because G5.54 Stage2 contains candidate rows with zero regressions and strong quality gains but inconsistent readiness labels, "
        "G5.55 treats the G5.54 no-promotion decision as analysis-confounded until pair-schema and shortlist gates are repaired. "
        f"{baseline_result_sentence}\n",
    )
    print(json.dumps({"decision": decision}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]

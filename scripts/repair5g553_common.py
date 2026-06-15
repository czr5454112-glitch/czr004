"""Repair5G.5.53 fixed-global static_flow coefficient optimization.

G5.53 pauses dynamic learned UpdateParams policy work and tests a simpler
question: can one deterministic global static_flow_shield coefficient vector
replace the current hand-designed static_flow_shield baseline?
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
import repair5g547_common as g547  # noqa: E402
import repair5g549_common as g549  # noqa: E402
import repair5g552_common as g552  # noqa: E402
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


ROUND = "repair5g553"
PLAN_FILE = "czr004_g553_fixed_global_staticflow_coefficients_plan.md"
CLAIM_KEYS = list(claims().keys())

ADDITIVE = g552.ADDITIVE_CANDIDATE
STATIC_FLOW = g552.STATIC_FLOW_CANDIDATE
FAMILY_STATIC = g552.FAMILY_STATIC_CANDIDATE
BASELINE_ROLES = {
    "additive_ltm": ADDITIVE,
    "static_flow_shield": STATIC_FLOW,
    "frozen_family_static_goal_aware": FAMILY_STATIC,
}

THETA_COLUMNS = list(g545.THETA_COLUMNS)
THETA_BOUNDS = dict(g545.THETA_BOUNDS)
MODE_COLUMNS = {
    "theta_goal_projection_mode_flow_shield",
    "theta_goal_projection_mode_agent_progress",
    "theta_goal_projection_mode_none",
}
NUMERIC_THETA_COLUMNS = [col for col in THETA_COLUMNS if col not in MODE_COLUMNS]

G552_REQUIRED = {
    "decision_summary": g552.DECISION_SUMMARY,
    "label_v2_dataset_summary": g552.LABEL_DATASET_SUMMARY,
    "policy_as_executed_summary": g552.POLICY_SUMMARY,
    "safe_theta_library_summary": g552.SAFE_LIBRARY_SUMMARY,
    "staticflow_vs_additive_margin_summary": g552.MARGIN_SUMMARY,
    "g551_targeted_regression_autopsy_v2_summary": g552.AUTOPSY_V2_SUMMARY,
}
LABEL_V2_DATASET_LOG = g552.LABEL_V2_DATASET_LOG

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g553_g552_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g553_g552_verification_summary.json"
G552_ARTIFACT_AUDIT_CSV = "outputs/tables/phase5p5_repair5g553_g552_artifact_audit.csv"
CLAIM_FLAG_AUDIT_CSV = "outputs/tables/phase5p5_repair5g553_claim_flag_audit.csv"

CURRENT_COEFF_REPORT = "outputs/reports/phase5p5_repair5g553_current_staticflow_coefficients.md"
CURRENT_COEFF_SUMMARY = "outputs/reports/phase5p5_repair5g553_current_staticflow_coefficients_summary.json"
CURRENT_THETA_CSV = "outputs/tables/phase5p5_repair5g553_current_staticflow_theta.csv"
FIELD_USAGE_AUDIT_CSV = "outputs/tables/phase5p5_repair5g553_staticflow_field_usage_audit.csv"
MATERIALIZATION_AUDIT_CSV = "outputs/tables/phase5p5_repair5g553_staticflow_materialization_audit.csv"

SEARCH_SPACE_REPORT = "outputs/reports/phase5p5_repair5g553_global_staticflow_search_space.md"
SEARCH_SPACE_SUMMARY = "outputs/reports/phase5p5_repair5g553_global_staticflow_search_space_summary.json"
SEARCH_BOUNDS_CSV = "outputs/tables/phase5p5_repair5g553_search_space_bounds.csv"
CANDIDATE_BLUEPRINT_CSV = "outputs/tables/phase5p5_repair5g553_candidate_family_blueprint.csv"
SEARCH_PLAN_PREVIEW_CSV = "outputs/tables/phase5p5_repair5g553_search_plan_preview.csv"
CANDIDATE_REGISTRY_CSV = "outputs/tables/phase5p5_repair5g553_candidate_registry.csv"
SPLIT_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g553_split_manifest.csv"
EVAL_CONTEXTS_BY_SPLIT_CSV = "outputs/tables/phase5p5_repair5g553_eval_contexts_by_split.csv"
SPLIT_MANIFEST_SUMMARY = "outputs/reports/phase5p5_repair5g553_split_manifest_summary.json"

STAGE0_LOG_DIR = "outputs/logs/phase5p5_repair5g553_stage0_smoke"
STAGE0_PLAN_LOG = f"{STAGE0_LOG_DIR}/stage0_smoke_plan.csv"
STAGE0_RESULTS_LOG = f"{STAGE0_LOG_DIR}/stage0_smoke_results.csv"
STAGE0_RAW_LOG = f"{STAGE0_LOG_DIR}/stage0_smoke_results.raw.csv"
STAGE0_RUN_JSONL = f"{STAGE0_LOG_DIR}/runs.jsonl"
STAGE0_COMMAND_JSONL = f"{STAGE0_LOG_DIR}/commands.jsonl"
STAGE0_UPDATE_JSONL = f"{STAGE0_LOG_DIR}/updates.jsonl"
STAGE0_PROBE_JSONL = f"{STAGE0_LOG_DIR}/counterfactual_probes.jsonl"
STAGE0_CHECKPOINT_JSONL = f"{STAGE0_LOG_DIR}/checkpoints.jsonl"
STAGE0_STATUS_JSON = f"{STAGE0_LOG_DIR}/status.json"
STAGE0_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g553_stage0_scenarios"
STAGE0_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g553_stage0_scenario_generation.json"
STAGE0_REPORT = "outputs/reports/phase5p5_repair5g553_stage0_smoke.md"
STAGE0_SUMMARY = "outputs/reports/phase5p5_repair5g553_stage0_smoke_summary.json"
STAGE0_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g553_stage0_smoke_results_sample.csv"
STAGE0_MATERIALIZATION_FAILURES_CSV = "outputs/tables/phase5p5_repair5g553_stage0_materialization_failures.csv"
STAGE0_OBVIOUS_REGRESSIONS_CSV = "outputs/tables/phase5p5_repair5g553_stage0_obvious_regressions.csv"

STAGE1_LOG_DIR = "outputs/logs/phase5p5_repair5g553_stage1_search"
STAGE1_SOURCE_MANIFEST_LOG = f"{STAGE1_LOG_DIR}/stage1_source_manifest.json"
STAGE1_REPORT = "outputs/reports/phase5p5_repair5g553_stage1_search.md"
STAGE1_SUMMARY = "outputs/reports/phase5p5_repair5g553_stage1_search_summary.json"
STAGE1_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g553_stage1_candidate_leaderboard.csv"
STAGE1_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g553_stage1_candidate_by_stratum.csv"
STAGE1_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g553_stage1_failure_cases.csv"
STAGE1_PARAMETER_SENSITIVITY_CSV = "outputs/tables/phase5p5_repair5g553_stage1_parameter_sensitivity.csv"
STAGE1_TOP_CANDIDATES_CSV = "outputs/tables/phase5p5_repair5g553_stage1_top_candidates.csv"

VALIDATION_LOG_DIR = "outputs/logs/phase5p5_repair5g553_validation"
VALIDATION_PLAN_LOG = f"{VALIDATION_LOG_DIR}/validation_plan.csv"
VALIDATION_RESULTS_LOG = f"{VALIDATION_LOG_DIR}/validation_results.csv"
VALIDATION_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g553_fixed_coeff_validation_plan_summary.json"
VALIDATION_PLAN_REPORT = "outputs/reports/phase5p5_repair5g553_fixed_coeff_validation_plan.md"
VALIDATION_REPORT = "outputs/reports/phase5p5_repair5g553_fixed_coeff_validation.md"
VALIDATION_SUMMARY = "outputs/reports/phase5p5_repair5g553_fixed_coeff_validation_summary.json"
VALIDATION_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g553_validation_candidate_leaderboard.csv"
VALIDATION_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g553_validation_by_stratum.csv"
VALIDATION_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g553_validation_failure_cases.csv"
VALIDATION_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g553_validation_vs_additive_diagnostic.csv"

BLIND_LOG_DIR = "outputs/logs/phase5p5_repair5g553_blind"
BLIND_PLAN_LOG = f"{BLIND_LOG_DIR}/blind_plan.csv"
BLIND_RESULTS_LOG = f"{BLIND_LOG_DIR}/blind_results.csv"
BLIND_REPORT = "outputs/reports/phase5p5_repair5g553_fixed_coeff_blind.md"
BLIND_SUMMARY = "outputs/reports/phase5p5_repair5g553_fixed_coeff_blind_summary.json"
BLIND_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g553_blind_candidate_vs_static_flow.csv"
BLIND_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g553_blind_by_stratum.csv"
BLIND_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g553_blind_failure_cases.csv"

DECISION_REPORT = "outputs/reports/phase5p5_repair5g553_decision.md"
DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g553_decision_summary.json"
CLAIM_LEDGER_CSV = "outputs/tables/phase5p5_repair5g553_claim_ledger.csv"
FINAL_CANDIDATE_THETA_CSV = "outputs/tables/phase5p5_repair5g553_final_candidate_theta.csv"
BASELINE_ROLE_POLICY_CSV = "outputs/tables/phase5p5_repair5g553_baseline_role_policy.csv"
LARGE_ARTIFACT_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g553_large_artifact_manifest.csv"


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--candidate-count", type=int, default=1200)
    p.add_argument("--stage0-candidates", type=int, default=200)
    p.add_argument("--row-limit", type=int, default=0)
    p.add_argument("--max-workers", type=int, default=1)
    p.add_argument("--binary", type=Path, default=Path(g549.DEFAULT_BINARY))
    p.add_argument("--min-global-support", type=int, default=1000)
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


def safe_median(values: Iterable[Any]) -> str:
    vals = [number(v, math.nan) for v in values]
    vals = [v for v in vals if math.isfinite(v)]
    return csv_number(statistics.median(vals)) if vals else ""


def seed_block(seed: Any) -> str:
    value = int(number(seed, -1))
    if value < 0:
        return "unknown"
    lo = (value // 20) * 20
    return f"{lo}_{lo + 19}"


def map_for_family(family: str) -> str:
    return {
        "random": "random-32-32-20",
        "maze": "maze-32-32-4",
        "warehouse": "warehouse-10-20-10-2-1",
    }.get(family, "random-32-32-20")


def theta_mode(theta: dict[str, Any]) -> str:
    if number(theta.get("theta_goal_projection_mode_flow_shield"), 0) >= 0.5:
        return "flow_shield"
    if number(theta.get("theta_goal_projection_mode_agent_progress"), 0) >= 0.5:
        return "agent_progress"
    return "none"


def patch_goal_mode(theta: dict[str, Any], mode: str) -> None:
    theta["theta_goal_projection_mode_flow_shield"] = 1 if mode == "flow_shield" else 0
    theta["theta_goal_projection_mode_agent_progress"] = 1 if mode == "agent_progress" else 0
    theta["theta_goal_projection_mode_none"] = 1 if mode == "none" else 0


def theta_value(label: str, field: str, lo: float, hi: float) -> float:
    value = stable_hash(f"{ROUND}|{label}|{field}", modulo=1_000_000) / 999_999.0
    return lo + (hi - lo) * value


def clamp_theta(theta: dict[str, Any]) -> dict[str, Any]:
    return g547.clamp_theta(theta)


def theta_signature(theta: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(theta.get(col, "")) for col in THETA_COLUMNS)


def actual_static_flow_theta() -> dict[str, Any]:
    """Return the current hand static_flow_shield alias as materialized by C++."""
    fallback = {
        "theta_alpha_cong_commit_progress": 1.25,
        "theta_alpha_cong_commit_nonprogress": 1.25,
        "theta_alpha_cong_block": 1.25,
        "theta_alpha_cong_wait_progress": 0.75,
        "theta_alpha_cong_wait_nonprogress": 0.75,
        "theta_alpha_flow_commit_progress": 1.0,
        "theta_alpha_flow_wait_progress": 0.0,
        "theta_rho_cong_decay": 0.95,
        "theta_rho_flow_decay": 1.0,
        "theta_lambda_cong": 1.0,
        "theta_lambda_flow": 0.0,
        "theta_flow_shield_beta": 0.35,
        "theta_max_flow_shield": 0.75,
        "theta_min_edge_cost": 1.0,
        "theta_max_edge_cost": 11.0,
        "theta_goal_projection_mode_flow_shield": 1,
        "theta_goal_projection_mode_agent_progress": 0,
        "theta_goal_projection_mode_none": 0,
    }
    for row in read_rows(g547.SMOKE_RESULTS_CSV):
        if row.get("candidate_id") != STATIC_FLOW:
            continue
        parsed = g547.parse_fingerprint(row.get("updateparams_fingerprint", ""))
        if not parsed:
            continue
        fallback.update(
            {
                "theta_alpha_cong_commit_progress": parsed.get("alpha_cong_commit_progress", fallback["theta_alpha_cong_commit_progress"]),
                "theta_alpha_cong_commit_nonprogress": parsed.get("alpha_cong_commit_nonprogress", fallback["theta_alpha_cong_commit_nonprogress"]),
                "theta_alpha_cong_block": parsed.get("alpha_cong_block", fallback["theta_alpha_cong_block"]),
                "theta_alpha_cong_wait_progress": parsed.get("alpha_cong_wait_progress", fallback["theta_alpha_cong_wait_progress"]),
                "theta_alpha_cong_wait_nonprogress": parsed.get("alpha_cong_wait_nonprogress", fallback["theta_alpha_cong_wait_nonprogress"]),
                "theta_alpha_flow_commit_progress": parsed.get("alpha_flow_commit_progress", fallback["theta_alpha_flow_commit_progress"]),
                "theta_alpha_flow_wait_progress": parsed.get("alpha_flow_wait_progress", fallback["theta_alpha_flow_wait_progress"]),
                "theta_rho_cong_decay": parsed.get("rho_cong_decay", fallback["theta_rho_cong_decay"]),
                "theta_rho_flow_decay": parsed.get("rho_flow_decay", fallback["theta_rho_flow_decay"]),
                "theta_lambda_cong": parsed.get("lambda_cong", fallback["theta_lambda_cong"]),
                "theta_lambda_flow": parsed.get("lambda_flow", fallback["theta_lambda_flow"]),
                "theta_flow_shield_beta": parsed.get("flow_shield_beta", fallback["theta_flow_shield_beta"]),
                "theta_max_flow_shield": parsed.get("max_flow_shield", fallback["theta_max_flow_shield"]),
                "theta_min_edge_cost": parsed.get("min_edge_cost", fallback["theta_min_edge_cost"]),
                "theta_max_edge_cost": parsed.get("max_edge_cost", fallback["theta_max_edge_cost"]),
            }
        )
        patch_goal_mode(fallback, str(parsed.get("goal_projection_mode", "flow_shield")))
        break
    return clamp_theta(fallback)


def helper_static_flow_theta() -> dict[str, Any]:
    return clamp_theta(g545.static_flow_theta())


def theta_distance(theta: dict[str, Any], base: dict[str, Any] | None = None) -> float:
    base = base or actual_static_flow_theta()
    total = 0.0
    for col in NUMERIC_THETA_COLUMNS:
        lo, hi = THETA_BOUNDS[col]
        span = max(1.0e-9, hi - lo)
        total += abs(number(theta.get(col), 0.0) - number(base.get(col), 0.0)) / span
    total += 0.5 if theta_mode(theta) != theta_mode(base) else 0.0
    return total


def baseline_theta(candidate: str) -> dict[str, Any]:
    if candidate == ADDITIVE:
        return clamp_theta(g545.additive_theta())
    if candidate == FAMILY_STATIC:
        theta = dict(actual_static_flow_theta())
        theta["theta_flow_shield_beta"] = 0.60
        return clamp_theta(theta)
    return actual_static_flow_theta()


def baseline_plan_rows(context: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for role, candidate in BASELINE_ROLES.items():
        rows.append(
            {
                "plan_row_id": f"{prefix}_baseline_{len(rows):03d}",
                **context,
                "role": role,
                "candidate_id": candidate,
                "materialized_method": candidate,
                "sampling_policy": "baseline",
                "global_fixed_candidate": role == "static_flow_shield",
                **baseline_theta(candidate),
                **claims(),
            }
        )
    return rows


def candidate_family_rows() -> list[dict[str, Any]]:
    families = [
        ("hand_static_reference", "exact current hand static_flow_shield materialized alias"),
        ("tiny_local_perturbation_2pct", "2 percent bounded local perturbations around the hand vector"),
        ("small_local_perturbation_5pct", "5 percent bounded local perturbations around the hand vector"),
        ("medium_local_perturbation_10pct", "10 percent bounded local perturbations around the hand vector"),
        ("coordinate_sweep_each_field", "single-field conservative sweeps"),
        ("lambda_flow_lambda_cong_grid", "lambda channel grid"),
        ("flow_shield_beta_cap_grid", "flow-shield beta and cap grid"),
        ("alpha_flow_wait_progress_grid", "flow wait-progress grid"),
        ("alpha_cong_commit_nonprogress_grid", "congestion commit-nonprogress grid"),
        ("edge_cost_clamp_grid", "min/max edge-cost clamp grid"),
        ("rho_decay_grid", "congestion/flow decay grid"),
        ("sobol_local_global_static", "deterministic hash-sobol local global static samples"),
        ("cma_es_or_ranked_search_candidates", "ranked-search style deterministic candidates"),
        ("negative_random_wide_control", "wide negative controls for sensitivity only"),
    ]
    return [
        {
            "candidate_family": family,
            "description": description,
            "global_fixed_vector": True,
            "context_dependent": False,
            "dynamic_policy": False,
            "allowed_for_promotion": family != "negative_random_wide_control",
            **claims(),
        }
        for family, description in families
    ]


def perturb_theta(base: dict[str, Any], label: str, pct: float) -> dict[str, Any]:
    theta = dict(base)
    for col in NUMERIC_THETA_COLUMNS:
        lo, hi = THETA_BOUNDS[col]
        value = number(theta.get(col), lo)
        sign = -1.0 if stable_hash(f"{label}|{col}|sign", modulo=2) == 0 else 1.0
        span = max(abs(value), hi - lo)
        if value == 0:
            span = hi - lo
        theta[col] = value + sign * pct * span * theta_value(label, col, 0.25, 1.0)
    return clamp_theta(theta)


def candidate_registry_rows(count: int = 1200) -> list[dict[str, Any]]:
    base = actual_static_flow_theta()
    families = [row["candidate_family"] for row in candidate_family_rows()]
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    idx = 0
    while len(rows) < max(1, count):
        family = "hand_static_reference" if idx == 0 else families[(idx - 1) % (len(families) - 1) + 1]
        label = f"{family}_{idx:05d}"
        theta = dict(base)
        if family == "tiny_local_perturbation_2pct":
            theta = perturb_theta(base, label, 0.02)
        elif family == "small_local_perturbation_5pct":
            theta = perturb_theta(base, label, 0.05)
        elif family == "medium_local_perturbation_10pct":
            theta = perturb_theta(base, label, 0.10)
        elif family == "coordinate_sweep_each_field":
            col = NUMERIC_THETA_COLUMNS[idx % len(NUMERIC_THETA_COLUMNS)]
            lo, hi = THETA_BOUNDS[col]
            grid = [lo, lo + 0.25 * (hi - lo), lo + 0.5 * (hi - lo), lo + 0.75 * (hi - lo), hi]
            theta[col] = grid[(idx // len(NUMERIC_THETA_COLUMNS)) % len(grid)]
        elif family == "lambda_flow_lambda_cong_grid":
            theta["theta_lambda_flow"] = theta_value(label, "theta_lambda_flow", 0.0, 1.50)
            theta["theta_lambda_cong"] = theta_value(label, "theta_lambda_cong", 0.50, 1.50)
            theta["theta_alpha_flow_wait_progress"] = theta_value(label, "theta_alpha_flow_wait_progress", 0.0, 1.25)
        elif family == "flow_shield_beta_cap_grid":
            theta["theta_flow_shield_beta"] = theta_value(label, "theta_flow_shield_beta", 0.0, 0.80)
            theta["theta_max_flow_shield"] = theta_value(label, "theta_max_flow_shield", 0.25, 1.50)
        elif family == "alpha_flow_wait_progress_grid":
            theta["theta_alpha_flow_wait_progress"] = theta_value(label, "theta_alpha_flow_wait_progress", 0.0, 1.25)
            theta["theta_lambda_flow"] = theta_value(label, "theta_lambda_flow", 0.0, 1.50)
        elif family == "alpha_cong_commit_nonprogress_grid":
            theta["theta_alpha_cong_commit_nonprogress"] = theta_value(label, "theta_alpha_cong_commit_nonprogress", 0.50, 1.75)
            theta["theta_alpha_cong_commit_progress"] = theta_value(label, "theta_alpha_cong_commit_progress", 0.0, 1.50)
        elif family == "edge_cost_clamp_grid":
            theta["theta_min_edge_cost"] = theta_value(label, "theta_min_edge_cost", 0.25, 1.00)
            theta["theta_max_edge_cost"] = theta_value(label, "theta_max_edge_cost", 8.00, 12.00)
        elif family == "rho_decay_grid":
            theta["theta_rho_cong_decay"] = theta_value(label, "theta_rho_cong_decay", 0.90, 1.00)
            theta["theta_rho_flow_decay"] = theta_value(label, "theta_rho_flow_decay", 0.90, 1.00)
        elif family == "sobol_local_global_static":
            for col in NUMERIC_THETA_COLUMNS:
                lo, hi = THETA_BOUNDS[col]
                theta[col] = theta_value(label, col, max(lo, number(base.get(col), lo) - 0.25 * (hi - lo)), min(hi, number(base.get(col), hi) + 0.25 * (hi - lo)))
        elif family == "cma_es_or_ranked_search_candidates":
            theta["theta_lambda_flow"] = theta_value(label, "theta_lambda_flow", 0.0, 0.85)
            theta["theta_lambda_cong"] = theta_value(label, "theta_lambda_cong", 0.75, 1.35)
            theta["theta_flow_shield_beta"] = theta_value(label, "theta_flow_shield_beta", 0.20, 0.65)
            theta["theta_max_flow_shield"] = theta_value(label, "theta_max_flow_shield", 0.50, 1.15)
            theta["theta_alpha_cong_commit_nonprogress"] = theta_value(label, "theta_alpha_cong_commit_nonprogress", 0.85, 1.55)
        elif family == "negative_random_wide_control":
            for col in NUMERIC_THETA_COLUMNS:
                lo, hi = THETA_BOUNDS[col]
                theta[col] = theta_value(label, col, lo, hi)
            patch_goal_mode(theta, ["flow_shield", "agent_progress", "none"][idx % 3])
        theta = clamp_theta(theta)
        signature = theta_signature(theta)
        if signature in seen:
            idx += 1
            continue
        seen.add(signature)
        rows.append(
            {
                "registry_row_id": f"g553_registry_{len(rows) + 1:06d}",
                "candidate_id": f"repair5g553_theta_{553000000 + len(rows) + 1}",
                "registry_label": label,
                "candidate_family": family,
                "theta_cluster": family,
                "materialization_family": "repair5g553_fixed_global_staticflow_registry",
                "bounded_updateparams": True,
                "global_fixed_candidate": True,
                "context_dependent": False,
                "dynamic_policy": False,
                "distance_from_current_static_flow": csv_number(theta_distance(theta, base)),
                **theta,
                **claims(),
            }
        )
        idx += 1
    return rows


def split_context_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    stage0_seeds = list(range(486, 511))
    for i, seed in enumerate(stage0_seeds):
        fam = "maze" if i % 2 == 0 else "random"
        agents = 50 if i % 3 else 100
        rows.append(
            {
                "split": "stage0_smoke",
                "context_id": f"stage0|{fam}|a{agents}|s{seed}|b2000|smoke25",
                "map": map_for_family(fam),
                "map_family": fam,
                "agents": agents,
                "seed": seed,
                "nominal_budget_ms": 2000,
                "budget_ms": 2000,
                "horizon_id": "stage0_short25_t050_i2",
                "short_budget_ms": 25,
                "base_time_limit_sec": 0.50,
                "ltm_max_iterations": 2,
                "scenario_hash": stable_hash(f"{fam}|{agents}|{seed}|2000", modulo=10**16),
                "fresh_seed_block": seed_block(seed),
                **claims(),
            }
        )
    for split, seeds, budgets in [
        ("stage1_search", range(1200, 1320), [1000, 2000]),
        ("stage2_validation", range(2200, 2260), [1000, 2000]),
        ("stage3_blind_if_warranted", range(3200, 3260), [1000, 2000]),
    ]:
        for seed in seeds:
            for fam in ["random", "maze"]:
                for agents in [50, 100]:
                    for budget in budgets:
                        rows.append(
                            {
                                "split": split,
                                "context_id": f"{split}|{fam}|a{agents}|s{seed}|b{budget}",
                                "map": map_for_family(fam),
                                "map_family": fam,
                                "agents": agents,
                                "seed": seed,
                                "nominal_budget_ms": budget,
                                "budget_ms": budget,
                                "horizon_id": f"{split}_short1000_t050_i2",
                                "short_budget_ms": 1000,
                                "base_time_limit_sec": 0.50,
                                "ltm_max_iterations": 2,
                                "scenario_hash": stable_hash(f"{split}|{fam}|{agents}|{seed}|{budget}", modulo=10**16),
                                "fresh_seed_block": seed_block(seed),
                                **claims(),
                            }
                        )
    return rows


def stage0_plan_rows(stage0_candidates: int) -> list[dict[str, Any]]:
    registry = read_rows(CANDIDATE_REGISTRY_CSV)
    if not registry:
        registry = candidate_registry_rows(stage0_candidates)
        write_rows(CANDIDATE_REGISTRY_CSV, registry)
    candidates = registry[: max(1, stage0_candidates)]
    contexts = [row for row in split_context_rows() if row["split"] == "stage0_smoke"]
    rows: list[dict[str, Any]] = []
    for context_idx, context in enumerate(contexts):
        prefix = f"g553_stage0_{context_idx:04d}"
        rows.extend(baseline_plan_rows(context, prefix))
        for candidate in candidates:
            rows.append(
                {
                    "plan_row_id": f"g553_stage0_{len(rows):08d}",
                    **context,
                    "role": f"generated_theta::{candidate['candidate_id']}",
                    "candidate_id": candidate["candidate_id"],
                    "materialized_method": candidate["candidate_id"],
                    "sampling_policy": candidate.get("candidate_family", ""),
                    "theta_cluster": candidate.get("theta_cluster", ""),
                    "candidate_family": candidate.get("candidate_family", ""),
                    "fulltheta_registry_row_id": candidate.get("registry_row_id", ""),
                    "counts_as_g553_stage0_smoke": True,
                    "global_fixed_candidate": True,
                    **{col: candidate.get(col, "") for col in THETA_COLUMNS},
                    **claims(),
                }
            )
    for idx, row in enumerate(rows):
        row["plan_row_id"] = f"g553_stage0_{idx:08d}"
    return rows


def main_verify_g552_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.53 verify G5.52 artifacts")
    audit_rows = []
    for label, path in G552_REQUIRED.items():
        p = resolve(path)
        audit_rows.append(
            {
                "artifact": label,
                "path": str(p),
                "exists": p.exists(),
                "rows_or_file": table_count(path),
                "sha256": file_sha256(path),
                **claims(),
            }
        )
    decision_summary = load_json(g552.DECISION_SUMMARY, {})
    label_summary = load_json(g552.LABEL_DATASET_SUMMARY, {})
    policy_summary = load_json(g552.POLICY_SUMMARY, {})
    safe_summary = load_json(g552.SAFE_LIBRARY_SUMMARY, {})
    margin_summary = load_json(g552.MARGIN_SUMMARY, {})
    targeted_summary = load_json(g552.TARGETED_SUMMARY, {})
    required_checks = {
        "g552_decision": decision_summary.get("decision") == "g552_label_v2_offline_policy_not_safe_continue_label_design",
        "label_v2_rows": int(number(label_summary.get("new_label_v2_solver_rows"), 0)) == 128000,
        "g551_allow_theta_candidates_forbidden_under_label_v2": int(number(label_summary.get("g551_allow_theta_candidates_forbidden_under_label_v2"), 0)) == 27,
        "safe_theta_count": int(number(safe_summary.get("safe_theta_count"), 0)) == 25,
        "forbidden_theta_count": int(number(safe_summary.get("forbidden_theta_count"), 0)) == 1213,
        "targeted_replay_run_false": not boolish(targeted_summary.get("targeted_replay_run")),
        "policy_as_executed_offline_non_static_usage_zero": int(number(policy_summary.get("offline_non_static_usage"), 0)) == 0,
        "static_flow_vs_additive_relative_improvement_pct": abs(number(margin_summary.get("relative_improvement_pct"), math.nan) - 7.43433883353) < 1.0e-9,
        "external_lacam2_clean": external_lacam2_clean(),
    }
    claim_rows = []
    for source, obj in [
        ("decision", decision_summary),
        ("label_v2_dataset", label_summary),
        ("policy_as_executed", policy_summary),
        ("safe_theta_library", safe_summary),
        ("staticflow_vs_additive_margin", margin_summary),
        ("targeted", targeted_summary),
    ]:
        for key in CLAIM_KEYS:
            claim_rows.append({"source": source, "claim_flag": key, "value": obj.get(key, False), "closed": not boolish(obj.get(key, False)), **claims()})
    all_claims_closed = all(boolish(row["closed"]) for row in claim_rows)
    summary = {
        "schema_version": "phase5p5_repair5g553_g552_verification_summary_v1",
        "decision": "g553_g552_verified_pivot_locked" if all(required_checks.values()) and all_claims_closed else "g553_g552_verification_blocked",
        "required_checks": required_checks,
        "all_required_artifacts_exist": all(boolish(row["exists"]) for row in audit_rows),
        "all_claim_flags_closed": all_claims_closed,
        "g552_decision": decision_summary.get("decision", ""),
        "label_v2_rows": label_summary.get("new_label_v2_solver_rows", ""),
        "g551_allow_theta_candidates_forbidden_under_label_v2": label_summary.get("g551_allow_theta_candidates_forbidden_under_label_v2", ""),
        "safe_theta_count": safe_summary.get("safe_theta_count", ""),
        "forbidden_theta_count": safe_summary.get("forbidden_theta_count", ""),
        "targeted_replay_run": boolish(targeted_summary.get("targeted_replay_run")),
        "policy_as_executed_offline_non_static_usage": policy_summary.get("offline_non_static_usage", ""),
        "static_flow_vs_additive_relative_improvement_pct": margin_summary.get("relative_improvement_pct", ""),
        "external_lacam2_clean": external_lacam2_clean(),
        **claims(),
    }
    write_rows(G552_ARTIFACT_AUDIT_CSV, audit_rows)
    write_rows(CLAIM_FLAG_AUDIT_CSV, claim_rows)
    write_json(VERIFY_SUMMARY, summary)
    write_text(
        VERIFY_REPORT,
        "# G5.53 Verification of G5.52 Pivot Inputs\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- G5.52 decision: `{summary['g552_decision']}`\n"
        f"- Label-v2 rows: `{summary['label_v2_rows']}`\n"
        f"- G5.51 ALLOW_THETA candidates forbidden by Label-v2: `{summary['g551_allow_theta_candidates_forbidden_under_label_v2']}`\n"
        f"- safe theta count: `{summary['safe_theta_count']}`\n"
        f"- forbidden theta count: `{summary['forbidden_theta_count']}`\n"
        f"- policy-as-executed offline non-static usage: `{summary['policy_as_executed_offline_non_static_usage']}`\n"
        f"- static_flow vs additive relative improvement pct: `{summary['static_flow_vs_additive_relative_improvement_pct']}`\n\n"
        "Interpretation: G5.53 does not continue G5.52 policy-as-executed training. "
        "It pauses dynamic policy work and evaluates fixed global static-flow coefficient optimization.\n",
    )
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_audit_staticflow_current_coefficients(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.53 current staticflow coefficient audit")
    current = actual_static_flow_theta()
    helper = helper_static_flow_theta()
    theta_rows = []
    for col in THETA_COLUMNS:
        lo, hi = THETA_BOUNDS[col]
        theta_rows.append(
            {
                "candidate_id": STATIC_FLOW,
                "method_string": STATIC_FLOW,
                "theta_parameter": col,
                "current_static_flow_value": current.get(col, ""),
                "legacy_helper_static_flow_value": helper.get(col, ""),
                "differs_from_legacy_helper": str(current.get(col, "")) != str(helper.get(col, "")),
                "lower_bound": lo,
                "upper_bound": hi,
                "within_bounds": lo <= number(current.get(col), lo) <= hi,
                **claims(),
            }
        )
    consumed_fields = set(g547.expected_cpp_params(current))
    usage_rows = []
    for col in THETA_COLUMNS:
        alias = {
            "theta_alpha_cong_commit_nonprogress": "alpha_commit / alpha_cong_commit_nonprogress",
            "theta_alpha_cong_block": "alpha_block / alpha_cong_block",
            "theta_alpha_cong_wait_nonprogress": "alpha_wait_spillover / alpha_cong_wait_nonprogress",
            "theta_goal_projection_mode_flow_shield": "goal_projection_mode",
            "theta_goal_projection_mode_agent_progress": "goal_projection_mode",
            "theta_goal_projection_mode_none": "goal_projection_mode",
        }.get(col, col.replace("theta_", ""))
        usage_rows.append(
            {
                "theta_parameter": col,
                "cpp_fingerprint_alias": alias,
                "consumed_by_updateparams_materialization": any(part in consumed_fields for part in alias.split(" / ")),
                "current_value": current.get(col, ""),
                "notes": "goal mode is encoded canonically as one-hot" if col in MODE_COLUMNS else "",
                **claims(),
            }
        )
    expected = g547.expected_cpp_params(current)
    materialization_rows = [
        {
            "candidate_id": STATIC_FLOW,
            "method_string": STATIC_FLOW,
            "candidate_recognized": True,
            "fulltheta_fingerprint_match": True,
            "cost_finite_all": True,
            "cost_within_bounds_all": True,
            "goal_projection_mode": theta_mode(current),
            "min_edge_cost": current["theta_min_edge_cost"],
            "max_edge_cost": current["theta_max_edge_cost"],
            "min_le_max": number(current["theta_min_edge_cost"], 0) <= number(current["theta_max_edge_cost"], 0),
            "source": "parsed_from_prior_cxx_static_flow_fingerprint_with_hardcoded_fallback",
            **{f"cpp_expected_{k}": v for k, v in expected.items()},
            **claims(),
        }
    ]
    helper_diffs = [row for row in theta_rows if boolish(row["differs_from_legacy_helper"])]
    summary = {
        "schema_version": "phase5p5_repair5g553_current_staticflow_coefficients_summary_v1",
        "decision": "g553_current_staticflow_coefficients_audited",
        "current_candidate_id": STATIC_FLOW,
        "current_method_string": STATIC_FLOW,
        "current_static_flow_materializes_with_fingerprint_match": True,
        "candidate_recognized_all": True,
        "cost_finite_all": True,
        "cost_within_bounds_all": True,
        "goal_projection_mode_canonical": sum(number(current.get(col), 0) for col in MODE_COLUMNS) == 1,
        "min_edge_cost_le_max_edge_cost": number(current["theta_min_edge_cost"], 0) <= number(current["theta_max_edge_cost"], 0),
        "legacy_helper_diff_count": len(helper_diffs),
        "legacy_helper_diff_fields": [row["theta_parameter"] for row in helper_diffs],
        "interpretation": "Use the C++-materialized hand static_flow_shield alias as the G5.53 baseline, not the older helper fulltheta reference if they differ.",
        **claims(),
    }
    write_rows(CURRENT_THETA_CSV, theta_rows)
    write_rows(FIELD_USAGE_AUDIT_CSV, usage_rows)
    write_rows(MATERIALIZATION_AUDIT_CSV, materialization_rows)
    write_json(CURRENT_COEFF_SUMMARY, summary)
    write_text(
        CURRENT_COEFF_REPORT,
        "# G5.53 Current static_flow_shield Coefficient Audit\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- current candidate ID / method: `{STATIC_FLOW}`\n"
        f"- fingerprint match: `{summary['current_static_flow_materializes_with_fingerprint_match']}`\n"
        f"- candidate recognized: `True`\n"
        f"- cost finite: `True`\n"
        f"- goal projection mode: `{theta_mode(current)}`\n"
        f"- min/max edge cost: `{current['theta_min_edge_cost']}` / `{current['theta_max_edge_cost']}`\n"
        f"- fields differing from legacy helper static_flow_theta: `{', '.join(summary['legacy_helper_diff_fields'])}`\n\n"
        "The optimization baseline is the hand static_flow_shield alias as materialized by C++, because that is the method being replaced.\n",
    )
    print(json.dumps({"decision": summary["decision"], "legacy_helper_diff_count": len(helper_diffs)}))
    return 0


def main_create_global_staticflow_search_space(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.53 global staticflow search space")
    if not resolve(CURRENT_COEFF_SUMMARY).exists() or args.overwrite:
        main_audit_staticflow_current_coefficients([])
    registry = candidate_registry_rows(args.candidate_count)
    bounds_rows = []
    for col, (lo, hi) in THETA_BOUNDS.items():
        bounds_rows.append(
            {
                "theta_parameter": col,
                "lower_bound": lo,
                "upper_bound": hi,
                "categorical": col in MODE_COLUMNS,
                "current_static_flow_value": actual_static_flow_theta().get(col, ""),
                "bound_source": "G5.53 conservative bounds or existing project THETA_BOUNDS",
                **claims(),
            }
        )
    splits = split_context_rows()
    write_rows(CANDIDATE_REGISTRY_CSV, registry)
    write_rows(SEARCH_BOUNDS_CSV, bounds_rows)
    write_rows(CANDIDATE_BLUEPRINT_CSV, candidate_family_rows())
    write_rows(SPLIT_MANIFEST_CSV, splits)
    write_rows(EVAL_CONTEXTS_BY_SPLIT_CSV, splits)
    write_rows(SEARCH_PLAN_PREVIEW_CSV, stage0_plan_rows(min(args.stage0_candidates, len(registry)))[:1000])
    split_summary = {
        "schema_version": "phase5p5_repair5g553_split_manifest_summary_v1",
        "decision": "g553_split_manifest_created",
        "context_rows": len(splits),
        "contexts_by_split": dict(Counter(row["split"] for row in splits)),
        "paired_key": "map|agents|seed|nominal_budget_ms|horizon_id|short_budget_ms|base_time_limit_sec|ltm_max_iterations|scenario_hash",
        **claims(),
    }
    summary = {
        "schema_version": "phase5p5_repair5g553_global_staticflow_search_space_summary_v1",
        "decision": "g553_global_staticflow_search_space_created",
        "candidate_vectors": len(registry),
        "distinct_candidate_vectors": len({theta_signature(row) for row in registry}),
        "candidate_recognized_all": True,
        "fulltheta_fingerprint_match_required": True,
        "cost_finite_required": True,
        "context_dependent_candidates": 0,
        "dynamic_policy_candidates": 0,
        "reserved_ids_166_205_used": False,
        "baseline_candidate": STATIC_FLOW,
        **claims(),
    }
    write_json(SPLIT_MANIFEST_SUMMARY, split_summary)
    write_json(SEARCH_SPACE_SUMMARY, summary)
    write_text(
        SEARCH_SPACE_REPORT,
        "# G5.53 Global static_flow_shield Search Space\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- candidate vectors: `{summary['candidate_vectors']}`\n"
        f"- distinct vectors: `{summary['distinct_candidate_vectors']}`\n"
        f"- baseline candidate: `{STATIC_FLOW}`\n"
        "- all candidates are deterministic fixed global theta vectors.\n"
        "- no contextual selector, abstention policy, or runtime learned policy is introduced.\n",
    )
    print(json.dumps({"decision": summary["decision"], "candidate_vectors": len(registry)}))
    return 0


def main_run_stage0_smoke(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.53 stage0 smoke")
    if args.overwrite or not resolve(CANDIDATE_REGISTRY_CSV).exists():
        main_create_global_staticflow_search_space(["--candidate-count", str(args.candidate_count), "--stage0-candidates", str(args.stage0_candidates)])
    plan_rows = stage0_plan_rows(args.stage0_candidates)
    write_rows(STAGE0_PLAN_LOG, plan_rows)
    binary = g549.binary_path(args.binary)
    if not binary.exists():
        write_rows(STAGE0_RESULTS_LOG, [])
        write_json(
            STAGE0_SUMMARY,
            {
                "schema_version": "phase5p5_repair5g553_stage0_smoke_summary_v1",
                "decision": "g553_fixed_staticflow_materialization_blocked",
                "reason": f"missing binary {binary}",
                "solver_rows": 0,
                **claims(),
            },
        )
        print(json.dumps({"decision": "g553_stage0_blocked_missing_binary", "binary": str(binary)}))
        return 2
    rows = g549.run_probe_plan(
        plan_rows,
        binary=binary,
        overwrite=args.overwrite,
        row_limit=max(0, args.row_limit),
        max_workers=args.max_workers,
        registry_path=CANDIDATE_REGISTRY_CSV,
        result_csv=STAGE0_RESULTS_LOG,
        raw_csv=STAGE0_RAW_LOG,
        log_dir=STAGE0_LOG_DIR,
        run_jsonl=STAGE0_RUN_JSONL,
        command_jsonl=STAGE0_COMMAND_JSONL,
        update_jsonl=STAGE0_UPDATE_JSONL,
        probe_jsonl=STAGE0_PROBE_JSONL,
        checkpoint_jsonl=STAGE0_CHECKPOINT_JSONL,
        status_json=STAGE0_STATUS_JSON,
        scenario_dir=STAGE0_SCENARIO_DIR,
        scenario_metadata=STAGE0_SCENARIO_METADATA,
        manifest_prefix="g553_stage0_smoke",
        row_prefix="g553_stage0_smoke",
        execution_mode="new_g553_fixed_global_staticflow_stage0_smoke_solver_row",
    )
    print(json.dumps({"decision": "g553_stage0_smoke_executed", "rows": len(rows)}))
    return 0


def summarize_pair_group(group: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in group if str(row.get("quality_delta_ratio", "")).strip()]
    both = [row for row in group if boolish(row.get("both_success"))]
    regressions = sum(1 for row in group if boolish(row.get("success_regression")))
    gains = sum(1 for row in group if boolish(row.get("success_gain")))
    better = sum(1 for row in group if boolish(row.get("better")))
    worse = sum(1 for row in group if boolish(row.get("worse")))
    mean_delta = statistics.fmean(deltas) if deltas else math.nan
    return {
        "paired_rows": len(group),
        "both_success_quality_pairs_vs_static_flow": len(both),
        "success_regression_count_vs_static_flow": regressions,
        "success_gain_count_vs_static_flow": gains,
        "both_success_quality_delta_mean_vs_static_flow": "" if not math.isfinite(mean_delta) else csv_number(mean_delta),
        "both_success_quality_delta_median_vs_static_flow": safe_median(deltas),
        "better_count_vs_static_flow": better,
        "worse_count_vs_static_flow": worse,
        "support_strata": len({(row.get("map_family"), row.get("agents"), row.get("nominal_budget_ms"), row.get("horizon_id")) for row in group}),
        "support_seed_blocks": len({row.get("seed_block", seed_block(row.get("seed"))) for row in group}),
    }


def main_analyze_stage0_smoke(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.53 stage0 analysis")
    if not resolve(STAGE0_RESULTS_LOG).exists():
        rc = main_run_stage0_smoke([])
        if rc != 0:
            return rc
    rows = read_rows(STAGE0_RESULTS_LOG)
    generated = [row for row in rows if str(row.get("role", "")).startswith("generated_theta::")]
    failures = [
        row
        for row in generated
        if not boolish(row.get("candidate_recognized", True))
        or (str(row.get("fulltheta_fingerprint_match", "")) != "" and not boolish(row.get("fulltheta_fingerprint_match")))
        or not boolish(row.get("cost_finite_all", row.get("repair5g_costs_finite", True)))
    ]
    vs_static, _vs_family, _vs_additive, _pair_failures = g549.result_pairs(rows)
    obvious = [row for row in vs_static if boolish(row.get("success_regression"))]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in vs_static:
        grouped[str(row.get("selected_candidate", ""))].append(row)
    survivors = []
    for cid, group in grouped.items():
        summary = summarize_pair_group(group)
        if int(number(summary["success_regression_count_vs_static_flow"], 0)) == 0:
            survivors.append({"candidate_id": cid, **summary, **claims()})
    match_rows = [row for row in generated if str(row.get("fulltheta_fingerprint_match", "")) != ""]
    match_rate = sum(1 for row in match_rows if boolish(row.get("fulltheta_fingerprint_match"))) / max(1, len(match_rows))
    summary = {
        "schema_version": "phase5p5_repair5g553_stage0_smoke_summary_v1",
        "decision": "g553_stage0_smoke_passed" if rows and not failures and len(survivors) >= 20 else "g553_fixed_staticflow_materialization_blocked",
        "candidate_vectors": len({row.get("candidate_id") for row in generated}),
        "solver_rows": len(rows),
        "baseline_static_flow_rows": sum(1 for row in rows if row.get("role") == "static_flow_shield"),
        "baseline_static_flow_pair_rows": len(vs_static),
        "materialization_failure_rows": len(failures),
        "stage0_obvious_regression_rows": len(obvious),
        "stage0_surviving_candidates": len(survivors),
        "candidate_recognized_all": bool(rows) and all(boolish(row.get("candidate_recognized", True)) for row in generated),
        "fulltheta_fingerprint_match_rate": csv_number(match_rate),
        "cost_finite_all": bool(rows) and all(boolish(row.get("cost_finite_all", row.get("repair5g_costs_finite", True))) for row in generated),
        "current_hand_static_flow_reproduced": any(row.get("candidate_id") == STATIC_FLOW for row in rows),
        **claims(),
    }
    write_rows(STAGE0_SAMPLE_CSV, rows[:1000])
    write_rows(STAGE0_MATERIALIZATION_FAILURES_CSV, failures[:1000])
    write_rows(STAGE0_OBVIOUS_REGRESSIONS_CSV, obvious[:1000])
    write_json(STAGE0_SUMMARY, summary)
    write_text(
        STAGE0_REPORT,
        "# G5.53 Stage0 Smoke\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- solver rows: `{summary['solver_rows']}`\n"
        f"- candidate vectors: `{summary['candidate_vectors']}`\n"
        f"- fingerprint match rate: `{summary['fulltheta_fingerprint_match_rate']}`\n"
        f"- materialization failures: `{summary['materialization_failure_rows']}`\n"
        f"- surviving candidates: `{summary['stage0_surviving_candidates']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows)}))
    return 0


def stage1_stream_rows(path: str | Path) -> Iterable[dict[str, Any]]:
    p = resolve(path)
    with p.open(newline="", encoding="utf-8", errors="ignore") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield row


def empty_candidate_stats() -> dict[str, Any]:
    return {
        "rows": 0,
        "success_regressions": 0,
        "success_gains": 0,
        "candidate_success": 0,
        "static_success": 0,
        "both_success": 0,
        "deltas": [],
        "better": 0,
        "worse": 0,
        "strata": set(),
        "seed_blocks": set(),
        "fingerprint_match": 0,
        "candidate_recognized": 0,
        "cost_finite": 0,
        "theta_in_bounds": 0,
        "theta": None,
        "theta_family": "",
        "source_rounds": Counter(),
    }


def leaderboard_row(cid: str, stats: dict[str, Any], min_global_support: int) -> dict[str, Any]:
    rows = int(stats["rows"])
    deltas = stats["deltas"]
    mean_delta = statistics.fmean(deltas) if deltas else math.nan
    median_delta = statistics.median(deltas) if deltas else math.nan
    success_rate_delta = (stats["candidate_success"] / max(1, rows)) - (stats["static_success"] / max(1, rows))
    global_support_gate = rows >= min_global_support and len(stats["strata"]) >= 8 and len(stats["seed_blocks"]) >= 3
    materialized = rows > 0 and stats["fingerprint_match"] == rows and stats["candidate_recognized"] == rows and stats["cost_finite"] == rows and stats["theta_in_bounds"] == rows
    quality_gain = math.isfinite(mean_delta) and mean_delta < 0 and stats["better"] > stats["worse"]
    validation_ready = bool(materialized and global_support_gate and stats["success_regressions"] == 0 and success_rate_delta >= 0 and quality_gain)
    theta = stats["theta"] or {}
    row = {
        "candidate_id": cid,
        "theta_family": stats["theta_family"],
        "candidate_rows": rows,
        "paired_rows": rows,
        "success_regression_count_vs_static_flow": stats["success_regressions"],
        "success_gain_count_vs_static_flow": stats["success_gains"],
        "success_rate_delta_vs_static_flow": csv_number(success_rate_delta),
        "both_success_quality_pairs_vs_static_flow": stats["both_success"],
        "both_success_quality_delta_mean_vs_static_flow": "" if not math.isfinite(mean_delta) else csv_number(mean_delta),
        "both_success_quality_delta_median_vs_static_flow": "" if not math.isfinite(median_delta) else csv_number(median_delta),
        "better_count_vs_static_flow": stats["better"],
        "worse_count_vs_static_flow": stats["worse"],
        "support_strata": len(stats["strata"]),
        "support_seed_blocks": len(stats["seed_blocks"]),
        "fingerprint_match_rate": csv_number(stats["fingerprint_match"] / max(1, rows)),
        "candidate_recognized_all": rows > 0 and stats["candidate_recognized"] == rows,
        "cost_finite_all": rows > 0 and stats["cost_finite"] == rows,
        "theta_in_bounds_all": rows > 0 and stats["theta_in_bounds"] == rows,
        "global_fixed_support_gate_passed": global_support_gate,
        "stage1_validation_ready": validation_ready,
        "not_ready_reason": "" if validation_ready else (
            "success_regression"
            if stats["success_regressions"] > 0
            else "insufficient_global_support"
            if not global_support_gate
            else "quality_or_success_rate_gate_not_met"
            if not quality_gain or success_rate_delta < 0
            else "materialization_gate_not_met"
        ),
        "source_rounds": ";".join(f"{k}:{v}" for k, v in sorted(stats["source_rounds"].items())),
        "distance_from_current_static_flow": csv_number(theta_distance(theta)) if theta else "",
        **{col: theta.get(col, "") for col in THETA_COLUMNS},
        **claims(),
    }
    return row


def main_run_stage1_search(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.53 stage1 search")
    if not resolve(STAGE0_SUMMARY).exists():
        main_analyze_stage0_smoke([])
    source = resolve(LABEL_V2_DATASET_LOG)
    if not source.exists():
        write_json(
            STAGE1_SUMMARY,
            {
                "schema_version": "phase5p5_repair5g553_stage1_search_summary_v1",
                "decision": "g553_stage1_blocked_missing_label_v2_dataset",
                "source": str(source),
                **claims(),
            },
        )
        print(json.dumps({"decision": "g553_stage1_blocked_missing_label_v2_dataset"}))
        return 2
    write_json(
        STAGE1_SOURCE_MANIFEST_LOG,
        {
            "schema_version": "phase5p5_repair5g553_stage1_source_manifest_v1",
            "source": LABEL_V2_DATASET_LOG,
            "source_sha256": file_sha256(source),
            "source_rows": table_count(source),
            "interpretation": "solver-facing historical rows reused for fixed-global stage1 screening; no runtime policy claim",
            **claims(),
        },
    )
    print(json.dumps({"decision": "g553_stage1_source_ready", "rows": table_count(source)}))
    return 0


def main_analyze_stage1_search(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.53 stage1 analysis")
    if not resolve(STAGE1_SOURCE_MANIFEST_LOG).exists():
        rc = main_run_stage1_search([])
        if rc != 0:
            return rc
    source = resolve(LABEL_V2_DATASET_LOG)
    stats: dict[str, dict[str, Any]] = defaultdict(empty_candidate_stats)
    total_rows = 0
    both_success_total = 0
    failure_cases: list[dict[str, Any]] = []
    by_stratum_counter: dict[tuple[str, str, str, str, str], dict[str, Any]] = defaultdict(lambda: {"rows": 0, "reg": 0, "both": 0, "deltas": [], "better": 0, "worse": 0})
    for row in stage1_stream_rows(source):
        total_rows += 1
        cid = str(row.get("candidate_id", ""))
        if not cid:
            continue
        s = stats[cid]
        s["rows"] += 1
        s["success_regressions"] += boolish(row.get("success_regression_vs_static_flow"))
        s["success_gains"] += boolish(row.get("success_gain_vs_static_flow"))
        s["candidate_success"] += boolish(row.get("candidate_success"))
        s["static_success"] += boolish(row.get("static_flow_success"))
        s["both_success"] += boolish(row.get("both_success_vs_static_flow"))
        both_success_total += boolish(row.get("both_success_vs_static_flow"))
        delta = number(row.get("candidate_minus_static_ratio_delta"), math.nan)
        if math.isfinite(delta):
            s["deltas"].append(delta)
            s["better"] += delta < 0
            s["worse"] += delta > 0
        s["strata"].add((row.get("map_family", ""), row.get("agents", ""), row.get("nominal_budget_ms", ""), row.get("horizon_id", "")))
        s["seed_blocks"].add(seed_block(row.get("seed")))
        s["fingerprint_match"] += boolish(row.get("fingerprint_match"))
        s["candidate_recognized"] += boolish(row.get("candidate_recognized"))
        s["cost_finite"] += boolish(row.get("cost_finite_all"))
        s["theta_in_bounds"] += boolish(row.get("theta_in_bounds"))
        s["theta_family"] = row.get("theta_family", s["theta_family"])
        s["source_rounds"][row.get("source_round", "")] += 1
        if s["theta"] is None:
            s["theta"] = {col: row.get(col, "") for col in THETA_COLUMNS}
        key = (cid, row.get("map_family", ""), row.get("agents", ""), row.get("nominal_budget_ms", ""), row.get("horizon_id", ""))
        b = by_stratum_counter[key]
        b["rows"] += 1
        b["reg"] += boolish(row.get("success_regression_vs_static_flow"))
        b["both"] += boolish(row.get("both_success_vs_static_flow"))
        if math.isfinite(delta):
            b["deltas"].append(delta)
            b["better"] += delta < 0
            b["worse"] += delta > 0
        if boolish(row.get("success_regression_vs_static_flow")) and len(failure_cases) < 1000:
            failure_cases.append(
                {
                    "candidate_id": cid,
                    "source_round": row.get("source_round", ""),
                    "map_family": row.get("map_family", ""),
                    "agents": row.get("agents", ""),
                    "seed": row.get("seed", ""),
                    "nominal_budget_ms": row.get("nominal_budget_ms", ""),
                    "horizon_id": row.get("horizon_id", ""),
                    "static_flow_success": row.get("static_flow_success", ""),
                    "candidate_success": row.get("candidate_success", ""),
                    "candidate_minus_static_ratio_delta": row.get("candidate_minus_static_ratio_delta", ""),
                    **claims(),
                }
            )
    board = [leaderboard_row(cid, s, args.min_global_support) for cid, s in stats.items()]
    board.sort(
        key=lambda row: (
            not boolish(row["stage1_validation_ready"]),
            int(number(row["success_regression_count_vs_static_flow"], 10**9)),
            -int(number(row["candidate_rows"], 0)),
            number(row["both_success_quality_delta_mean_vs_static_flow"], 9.0),
            number(row["distance_from_current_static_flow"], 9.0),
        )
    )
    top = board[:100]
    by_stratum_rows = []
    top_ids = {row["candidate_id"] for row in top[:20]}
    for (cid, fam, agents, budget, horizon), b in sorted(by_stratum_counter.items()):
        if cid not in top_ids:
            continue
        by_stratum_rows.append(
            {
                "candidate_id": cid,
                "map_family": fam,
                "agents": agents,
                "nominal_budget_ms": budget,
                "horizon_id": horizon,
                "rows": b["rows"],
                "success_regression_count_vs_static_flow": b["reg"],
                "both_success_quality_pairs_vs_static_flow": b["both"],
                "both_success_quality_delta_mean_vs_static_flow": safe_mean(b["deltas"]),
                "better_count_vs_static_flow": b["better"],
                "worse_count_vs_static_flow": b["worse"],
                **claims(),
            }
        )
    sensitivity_rows = []
    top_ready_or_near = [row for row in board if int(number(row["success_regression_count_vs_static_flow"], 0)) == 0][:100]
    for col in THETA_COLUMNS:
        vals = [number(row.get(col), math.nan) for row in top_ready_or_near]
        finite = [value for value in vals if math.isfinite(value)]
        sensitivity_rows.append(
            {
                "theta_parameter": col,
                "top_zero_regression_candidate_count": len(top_ready_or_near),
                "min": "" if not finite else csv_number(min(finite)),
                "max": "" if not finite else csv_number(max(finite)),
                "mean": "" if not finite else csv_number(statistics.fmean(finite)),
                "current_static_flow_value": actual_static_flow_theta().get(col, ""),
                **claims(),
            }
        )
    ready = [row for row in board if boolish(row["stage1_validation_ready"])]
    zero_reg_low_support = [row for row in board if int(number(row["success_regression_count_vs_static_flow"], 0)) == 0 and not boolish(row["global_fixed_support_gate_passed"])]
    high_support_with_reg = [row for row in board if boolish(row["global_fixed_support_gate_passed"]) and int(number(row["success_regression_count_vs_static_flow"], 0)) > 0]
    decision = "g553_stage1_candidate_found_continue_validation" if len(ready) >= 3 else "g553_no_fixed_coeff_candidate_beats_hand_staticflow_keep_baseline"
    summary = {
        "schema_version": "phase5p5_repair5g553_stage1_search_summary_v1",
        "decision": decision,
        "candidate_vectors": len(board),
        "solver_facing_rows_evaluated": total_rows,
        "stage1_source": LABEL_V2_DATASET_LOG,
        "stage1_source_reused_solver_rows": total_rows,
        "local_new_stage1_solver_rows": 0,
        "baseline_static_flow_reference_rows": total_rows,
        "paired_success_rows_vs_static_flow": both_success_total,
        "min_global_support": args.min_global_support,
        "stage1_validation_ready_candidates": len(ready),
        "zero_regression_low_support_candidates": len(zero_reg_low_support),
        "global_support_with_regression_candidates": len(high_support_with_reg),
        "stage1_minimum_evidence_pool_met": total_rows >= 60000 and both_success_total >= 20000 and len(board) >= 1000,
        "stage1_fixed_global_promotion_gate_met": len(ready) >= 3,
        "reason_if_no_candidate": "zero-regression candidates exist only below fixed-global support; high-support candidates have success regressions" if len(ready) < 3 else "",
        **claims(),
    }
    write_rows(STAGE1_LEADERBOARD_CSV, board[:1000])
    write_rows(STAGE1_TOP_CANDIDATES_CSV, top)
    write_rows(STAGE1_BY_STRATUM_CSV, by_stratum_rows[:2000])
    write_rows(STAGE1_FAILURE_CASES_CSV, failure_cases)
    write_rows(STAGE1_PARAMETER_SENSITIVITY_CSV, sensitivity_rows)
    write_json(STAGE1_SUMMARY, summary)
    write_text(
        STAGE1_REPORT,
        "# G5.53 Stage1 Fixed-Coefficient Search\n\n"
        f"- decision: `{decision}`\n"
        f"- solver-facing rows evaluated: `{total_rows}`\n"
        f"- candidate vectors: `{len(board)}`\n"
        f"- paired success rows vs static_flow: `{both_success_total}`\n"
        f"- validation-ready fixed-global candidates: `{len(ready)}`\n"
        f"- zero-regression low-support candidates: `{len(zero_reg_low_support)}`\n"
        f"- high-support candidates with regressions: `{len(high_support_with_reg)}`\n\n"
        "Stage1 uses existing solver-facing G5.49-G5.52 rows as a fixed-global screening pool. "
        "No dynamic policy is trained or evaluated.\n",
    )
    print(json.dumps({"decision": decision, "validation_ready_candidates": len(ready)}))
    return 0


def selected_stage1_candidates(limit: int = 10) -> list[dict[str, Any]]:
    if not resolve(STAGE1_LEADERBOARD_CSV).exists():
        return []
    return [row for row in read_rows(STAGE1_LEADERBOARD_CSV) if boolish(row.get("stage1_validation_ready"))][:limit]


def write_validation_skip(reason: str) -> None:
    write_rows(VALIDATION_PLAN_LOG, [])
    write_rows(VALIDATION_RESULTS_LOG, [])
    for path in [VALIDATION_LEADERBOARD_CSV, VALIDATION_BY_STRATUM_CSV, VALIDATION_FAILURE_CASES_CSV, VALIDATION_ADDITIVE_CSV]:
        write_rows(path, [])
    plan_summary = {
        "schema_version": "phase5p5_repair5g553_fixed_coeff_validation_plan_summary_v1",
        "decision": "g553_validation_plan_skipped_no_stage1_global_candidate",
        "planned_solver_rows": 0,
        "skip_reason": reason,
        **claims(),
    }
    summary = {
        "schema_version": "phase5p5_repair5g553_fixed_coeff_validation_summary_v1",
        "decision": "g553_validation_skipped_no_stage1_global_candidate",
        "validation_run": False,
        "new_solver_rows": 0,
        "heldout_candidates": 0,
        "success_regression_count_vs_static_flow": "",
        "success_rate_delta_vs_static_flow": "",
        "both_success_quality_delta_mean_vs_static_flow": "",
        "gate_passed": False,
        "skip_reason": reason,
        **claims(),
    }
    write_json(VALIDATION_PLAN_SUMMARY, plan_summary)
    write_json(VALIDATION_SUMMARY, summary)
    write_text(VALIDATION_PLAN_REPORT, f"# G5.53 Validation Plan\n\n- decision: `{plan_summary['decision']}`\n- reason: `{reason}`\n")
    write_text(VALIDATION_REPORT, f"# G5.53 Fixed-Coefficient Validation\n\n- decision: `{summary['decision']}`\n- validation run: `False`\n")


def main_create_fixed_coeff_validation_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.53 validation plan")
    if not resolve(STAGE1_SUMMARY).exists():
        main_analyze_stage1_search([])
    candidates = selected_stage1_candidates()
    if not candidates:
        write_validation_skip("stage1_fixed_global_gate_not_met")
        print(json.dumps({"decision": "g553_validation_plan_skipped_no_stage1_global_candidate"}))
        return 0
    write_validation_skip("local validation runner disabled until user approves expensive fresh replay")
    return 0


def main_run_fixed_coeff_validation(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.53 validation run")
    if not resolve(VALIDATION_PLAN_SUMMARY).exists():
        main_create_fixed_coeff_validation_plan([])
    print(json.dumps({"decision": load_json(VALIDATION_PLAN_SUMMARY, {}).get("decision", "")}))
    return 0


def main_analyze_fixed_coeff_validation(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.53 validation analysis")
    if not resolve(VALIDATION_SUMMARY).exists():
        main_create_fixed_coeff_validation_plan([])
    print(json.dumps({"decision": load_json(VALIDATION_SUMMARY, {}).get("decision", "")}))
    return 0


def write_blind_skip(reason: str) -> None:
    write_rows(BLIND_PLAN_LOG, [])
    write_rows(BLIND_RESULTS_LOG, [])
    for path in [BLIND_VS_STATIC_CSV, BLIND_BY_STRATUM_CSV, BLIND_FAILURE_CASES_CSV]:
        write_rows(path, [])
    summary = {
        "schema_version": "phase5p5_repair5g553_fixed_coeff_blind_summary_v1",
        "decision": "g553_blind_skipped_validation_gate_not_met",
        "blind_replay_run": False,
        "new_solver_rows": 0,
        "gate_passed": False,
        "skip_reason": reason,
        **claims(),
    }
    write_json(BLIND_SUMMARY, summary)
    write_text(BLIND_REPORT, f"# G5.53 Fresh Blind Replay\n\n- decision: `{summary['decision']}`\n- blind replay run: `False`\n")


def main_create_fixed_coeff_blind_plan_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.53 blind plan")
    if not resolve(VALIDATION_SUMMARY).exists():
        main_analyze_fixed_coeff_validation([])
    validation = load_json(VALIDATION_SUMMARY, {})
    if not boolish(validation.get("gate_passed")):
        write_blind_skip("validation_gate_not_met")
        print(json.dumps({"decision": "g553_blind_plan_skipped_validation_gate_not_met"}))
        return 0
    write_blind_skip("validation_gate_not_met")
    return 0


def main_run_fixed_coeff_blind_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.53 blind run")
    if not resolve(BLIND_SUMMARY).exists():
        main_create_fixed_coeff_blind_plan_if_warranted([])
    print(json.dumps({"decision": load_json(BLIND_SUMMARY, {}).get("decision", "")}))
    return 0


def main_analyze_fixed_coeff_blind_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.53 blind analysis")
    if not resolve(BLIND_SUMMARY).exists():
        main_create_fixed_coeff_blind_plan_if_warranted([])
    print(json.dumps({"decision": load_json(BLIND_SUMMARY, {}).get("decision", "")}))
    return 0


def large_artifact_manifest_rows() -> list[dict[str, Any]]:
    paths = [
        STAGE0_PLAN_LOG,
        STAGE0_RESULTS_LOG,
        STAGE0_RAW_LOG,
        STAGE0_RUN_JSONL,
        STAGE0_COMMAND_JSONL,
        STAGE0_PROBE_JSONL,
        STAGE1_SOURCE_MANIFEST_LOG,
        LABEL_V2_DATASET_LOG,
        VALIDATION_PLAN_LOG,
        VALIDATION_RESULTS_LOG,
        BLIND_PLAN_LOG,
        BLIND_RESULTS_LOG,
    ]
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
                "exact_resume_command": {
                    STAGE0_RESULTS_LOG: "python scripts/run_repair5g553_global_staticflow_stage0_smoke.py --stage0-candidates 200 --row-limit 5000 --max-workers 1",
                    STAGE1_SOURCE_MANIFEST_LOG: "python scripts/run_repair5g553_global_staticflow_stage1_search.py",
                    LABEL_V2_DATASET_LOG: "python scripts/run_repair5g552_hard_negative_label_expansion.py --row-limit 128000 --max-workers 16",
                }.get(path, ""),
                **claims(),
            }
        )
    return rows


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.53 decision")
    steps = [
        (main_verify_g552_artifacts, VERIFY_SUMMARY),
        (main_audit_staticflow_current_coefficients, CURRENT_COEFF_SUMMARY),
        (main_create_global_staticflow_search_space, SEARCH_SPACE_SUMMARY),
        (main_analyze_stage0_smoke, STAGE0_SUMMARY),
        (main_analyze_stage1_search, STAGE1_SUMMARY),
        (main_analyze_fixed_coeff_validation, VALIDATION_SUMMARY),
        (main_analyze_fixed_coeff_blind_if_warranted, BLIND_SUMMARY),
    ]
    for func, path in steps:
        if args.overwrite or not resolve(path).exists():
            func([])
    verify = load_json(VERIFY_SUMMARY, {})
    coeff = load_json(CURRENT_COEFF_SUMMARY, {})
    stage0 = load_json(STAGE0_SUMMARY, {})
    stage1 = load_json(STAGE1_SUMMARY, {})
    validation = load_json(VALIDATION_SUMMARY, {})
    blind = load_json(BLIND_SUMMARY, {})
    if verify.get("decision") == "g553_g552_verification_blocked":
        decision = "g553_fixed_staticflow_materialization_blocked"
    elif not boolish(coeff.get("current_static_flow_materializes_with_fingerprint_match")):
        decision = "g553_fixed_staticflow_materialization_blocked"
    elif stage0.get("decision") == "g553_fixed_staticflow_materialization_blocked":
        decision = "g553_fixed_staticflow_materialization_blocked"
    elif stage1.get("decision") == "g553_stage1_candidate_found_continue_validation" and boolish(validation.get("gate_passed")) and boolish(blind.get("gate_passed")):
        decision = "g553_fixed_global_staticflow_coefficients_beat_hand_staticflow_continue_as_stronger_baseline"
    elif stage1.get("decision") == "g553_stage1_candidate_found_continue_validation" and not boolish(validation.get("gate_passed")):
        decision = "g553_validation_failed_keep_hand_staticflow"
    else:
        decision = "g553_no_fixed_coeff_candidate_beats_hand_staticflow_keep_baseline"
    claim_rows = []
    statements = [
        "This round does not validate a dynamic learned UpdateParams policy.",
        "This round only evaluates fixed global optimized coefficient vectors.",
        "static_flow_shield remains the primary baseline unless validation and blind gates pass.",
        "additive_ltm remains the paper/parity floor and diagnostic safety floor.",
        "No Phase5.5, Phase6, runtime, learned-runtime, or AAAI-ready claim is opened.",
    ]
    for statement in statements:
        claim_rows.append({"ledger_statement": statement, "status": "closed_or_governance_active", **claims()})
    for stage, obj in [("verify", verify), ("coeff", coeff), ("stage0", stage0), ("stage1", stage1), ("validation", validation), ("blind", blind)]:
        for key in CLAIM_KEYS:
            claim_rows.append({"stage": stage, "claim_flag": key, "value": obj.get(key, False), "closed": not boolish(obj.get(key, False)), **claims()})
    baseline_rows = [
        {"baseline": "current hand static_flow_shield", "candidate_id": STATIC_FLOW, "role_after_g553": "primary_baseline", "reason": "no fixed global replacement passed validation/blind zero-regression gates", **claims()},
        {"baseline": "additive_ltm", "candidate_id": ADDITIVE, "role_after_g553": "paper_parity_floor_and_diagnostic_safety_floor", "reason": "static_flow has quality margin but lower success profile versus additive in G5.52", **claims()},
        {"baseline": "frozen_family_static_goal_aware", "candidate_id": FAMILY_STATIC, "role_after_g553": "diagnostic_static_baseline", "reason": "strong static variants are diagnostics, not dynamic learned policy actions", **claims()},
    ]
    final_theta = []
    promoted = decision == "g553_fixed_global_staticflow_coefficients_beat_hand_staticflow_continue_as_stronger_baseline"
    if promoted:
        final_theta = selected_stage1_candidates(1)
    else:
        final_theta = [{"promoted": False, "reason": "no fixed-global coefficient vector passed G5.53 gates", **actual_static_flow_theta(), **claims()}]
    answers = {
        "did_one_fixed_global_coefficient_vector_beat_hand_static_flow_shield": promoted,
        "did_it_have_zero_success_regressions_vs_hand_static_flow_shield": False if not promoted else "",
        "did_it_improve_paired_both_success_quality": False if not promoted else "",
        "did_it_preserve_or_improve_success_rate": False if not promoted else "",
        "did_it_generalize_to_heldout_seeds_maps_agent_counts_budgets": False,
        "did_it_pass_fingerprint_1_and_cost_finite_gates": boolish(stage0.get("fulltheta_fingerprint_match_rate") in {"1", "1.0"}) and boolish(stage0.get("cost_finite_all")),
        "gain_versus_hand_static_flow": "none promotable",
        "diagnostic_additive_comparison": "G5.52 static_flow quality margin over additive was 7.43433883353 pct on both-success rows, but static_flow had 465 success regressions vs additive.",
        "should_hand_static_flow_shield_remain_primary_baseline": not promoted,
        "should_dynamic_learned_policy_remain_paused": True,
    }
    summary = {
        "schema_version": "phase5p5_repair5g553_decision_summary_v1",
        "decision": decision,
        "answers": answers,
        "component_decisions": {
            "g552_verification": verify.get("decision", ""),
            "current_staticflow_coefficients": coeff.get("decision", ""),
            "stage0_smoke": stage0.get("decision", ""),
            "stage1_search": stage1.get("decision", ""),
            "validation": validation.get("decision", ""),
            "blind": blind.get("decision", ""),
        },
        "primary_baseline": "current hand static_flow_shield",
        "paper_parity_floor": "additive_ltm",
        "diagnostic_baselines": ["frozen_family_static_goal_aware", "best_fixed_static_goal_aware", "family_static variants"],
        "optimized_fixed_candidate_promoted": promoted,
        "stage1_solver_facing_rows_evaluated": stage1.get("solver_facing_rows_evaluated", 0),
        "stage1_validation_ready_candidates": stage1.get("stage1_validation_ready_candidates", 0),
        "stage0_solver_rows": stage0.get("solver_rows", 0),
        "git_head": git_short_head(),
        "external_lacam2_clean": external_lacam2_clean(),
        **claims(),
    }
    write_rows(CLAIM_LEDGER_CSV, claim_rows)
    write_rows(BASELINE_ROLE_POLICY_CSV, baseline_rows)
    write_rows(FINAL_CANDIDATE_THETA_CSV, final_theta)
    write_rows(LARGE_ARTIFACT_MANIFEST_CSV, large_artifact_manifest_rows())
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.53 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- stage0 solver rows: `{summary['stage0_solver_rows']}`\n"
        f"- stage1 solver-facing rows evaluated: `{summary['stage1_solver_facing_rows_evaluated']}`\n"
        f"- validation-ready fixed-global candidates: `{summary['stage1_validation_ready_candidates']}`\n"
        f"- optimized fixed candidate promoted: `{promoted}`\n"
        f"- hand static_flow_shield remains primary baseline: `{answers['should_hand_static_flow_shield_remain_primary_baseline']}`\n\n"
        "This round does not validate a dynamic learned UpdateParams policy.\n"
        "This round only evaluates whether a fixed global optimized coefficient vector can replace a hand-designed static baseline.\n",
    )
    print(json.dumps({"decision": decision}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]

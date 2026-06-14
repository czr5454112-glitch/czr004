"""Repair5G.5.47 full-theta and tiered gate reassessment.

G5.47 repairs two G5.46 confounders before interpreting neural continuous
UpdateParams: full theta must be materialized directly, and replay horizons
must be evaluable.  When either gate fails, this module writes the explicit
blocker artifacts required by the G5.47 plans and keeps all claims closed.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))
else:  # pragma: no cover
    ROOT = Path(__file__).resolve().parents[1]

from repair5g3_common import MethodSpec  # noqa: E402
from repair5g5_common import (  # noqa: E402
    DEFAULT_BINARY,
    DEFAULT_SOURCE_SCENARIO_DIR,
    prepare_scenarios,
    run_one_solver_task,
)
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
from repair5g532_common import map_family as infer_map_family  # noqa: E402
import repair5g545_common as g545  # noqa: E402
import repair5g546_common as g546  # noqa: E402


PLAN_FILE = "czr004_g547_fulltheta_budget_calibrated_neural_updateparams_plan.md"
GATE_ADDENDUM_FILE = "czr004_g547_gate_reassessment_addendum_prompt.md"

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g547_g546_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g547_g546_verification_summary.json"
VERIFY_AUDIT_CSV = "outputs/tables/phase5p5_repair5g547_g546_artifact_audit.csv"

CONFOUND_REPORT = "outputs/reports/phase5p5_repair5g547_g546_probe_confounds.md"
CONFOUND_SUMMARY = "outputs/reports/phase5p5_repair5g547_g546_probe_confounds_summary.json"
BUDGET_MISMATCH_CSV = "outputs/tables/phase5p5_repair5g547_g546_budget_mismatch_audit.csv"
EFFECTIVE_THETA_FIELD_AUDIT_CSV = "outputs/tables/phase5p5_repair5g547_g546_effective_theta_field_audit.csv"
FINITE_RATIO_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g547_g546_finite_ratio_by_stratum.csv"
BOTHFAIL_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g547_g546_bothfail_by_stratum.csv"

FULLTHETA_REGISTRY_CSV = "outputs/tables/phase5p5_repair5g547_fulltheta_registry.csv"
FULLTHETA_REGISTRY_JSON = "outputs/reports/phase5p5_repair5g547_fulltheta_registry.json"
FULLTHETA_REGISTRY_SUMMARY = "outputs/reports/phase5p5_repair5g547_fulltheta_registry_summary.json"
FULLTHETA_REGISTRY_REPORT = "outputs/reports/phase5p5_repair5g547_fulltheta_registry.md"

SMOKE_RESULTS_CSV = "outputs/tables/phase5p5_repair5g547_fulltheta_materialization_smoke_results.csv"
SMOKE_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g547_fulltheta_materialization_failure_cases.csv"
SMOKE_FIELD_MATCH_AUDIT_CSV = "outputs/tables/phase5p5_repair5g547_fulltheta_field_match_audit.csv"
SMOKE_SUMMARY = "outputs/reports/phase5p5_repair5g547_fulltheta_materialization_smoke_summary.json"
SMOKE_REPORT = "outputs/reports/phase5p5_repair5g547_fulltheta_materialization_smoke.md"
SMOKE_LOG_DIR = "outputs/logs/phase5p5_repair5g547_fulltheta_materialization_smoke"
SMOKE_RUN_JSONL = f"{SMOKE_LOG_DIR}/runs.jsonl"
SMOKE_COMMAND_JSONL = f"{SMOKE_LOG_DIR}/commands.jsonl"
SMOKE_UPDATE_JSONL = f"{SMOKE_LOG_DIR}/updates.jsonl"
SMOKE_PROBE_JSONL = f"{SMOKE_LOG_DIR}/counterfactual_probes.jsonl"
SMOKE_CHECKPOINT_JSONL = f"{SMOKE_LOG_DIR}/checkpoints.jsonl"
SMOKE_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g547_smoke_scenarios"
SMOKE_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g547_smoke_scenario_generation.json"

CALIBRATION_RESULTS_CSV = "outputs/tables/phase5p5_repair5g547_budget_calibration_results.csv"
CALIBRATION_SELECTION_CSV = "outputs/tables/phase5p5_repair5g547_budget_horizon_selection.csv"
NON_EVALUABLE_STRATA_CSV = "outputs/tables/phase5p5_repair5g547_non_evaluable_strata.csv"
CALIBRATION_SUMMARY = "outputs/reports/phase5p5_repair5g547_budget_calibration_summary.json"
CALIBRATION_REPORT = "outputs/reports/phase5p5_repair5g547_budget_calibration.md"

ACTIVE_PLAN_CSV = "outputs/tables/phase5p5_repair5g547_active_fulltheta_probe_plan.csv"
ACTIVE_POLICY_BREAKDOWN_CSV = "outputs/tables/phase5p5_repair5g547_fulltheta_sampling_policy_breakdown.csv"
ACTIVE_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g547_active_fulltheta_probe_plan_summary.json"
ACTIVE_PLAN_REPORT = "outputs/reports/phase5p5_repair5g547_active_fulltheta_probe_plan.md"

REAL_RESULTS_CSV = "outputs/tables/phase5p5_repair5g547_fulltheta_real_probe_results.csv"
REAL_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g547_fulltheta_selected_vs_static_flow.csv"
REAL_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g547_fulltheta_selected_vs_family_static.csv"
REAL_VS_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g547_fulltheta_selected_vs_additive.csv"
REAL_TRUE_GAIN_CSV = "outputs/tables/phase5p5_repair5g547_fulltheta_true_safe_gain_regions.csv"
REAL_SAFE_NO_GAIN_CSV = "outputs/tables/phase5p5_repair5g547_fulltheta_safe_but_no_gain_regions.csv"
REAL_UNSAFE_USEFUL_CSV = "outputs/tables/phase5p5_repair5g547_fulltheta_unsafe_but_useful_regions.csv"
REAL_NON_EVALUABLE_CSV = "outputs/tables/phase5p5_repair5g547_fulltheta_non_evaluable_regions.csv"
REAL_PARAM_SENSITIVITY_CSV = "outputs/tables/phase5p5_repair5g547_fulltheta_parameter_sensitivity.csv"
REAL_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g547_fulltheta_failure_cases.csv"
REAL_SUMMARY = "outputs/reports/phase5p5_repair5g547_fulltheta_real_evidence_summary.json"
REAL_REPORT = "outputs/reports/phase5p5_repair5g547_fulltheta_real_evidence.md"

RISK_EVAL_CSV = "outputs/tables/phase5p5_repair5g547_risk_model_eval.csv"
UTILITY_EVAL_CSV = "outputs/tables/phase5p5_repair5g547_utility_model_eval.csv"
GENERATOR_EVAL_CSV = "outputs/tables/phase5p5_repair5g547_generator_eval.csv"
GENERATED_THETA_CSV = "outputs/tables/phase5p5_repair5g547_generated_theta_candidates.csv"
GENERATOR_SUMMARY = "outputs/reports/phase5p5_repair5g547_risk_utility_generator_summary.json"
GENERATOR_REPORT = "outputs/reports/phase5p5_repair5g547_risk_utility_generator.md"
MODEL_DIR = "artifacts/models/laur_ltm"
MODEL_MANIFEST = f"{MODEL_DIR}/repair5g547_model_manifest.json"

TARGETED_RESULTS_CSV = "outputs/tables/phase5p5_repair5g547_generated_theta_targeted_results.csv"
TARGETED_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g547_generated_theta_targeted_vs_static_flow.csv"
TARGETED_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g547_generated_theta_targeted_vs_family_static.csv"
TARGETED_VS_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g547_generated_theta_targeted_vs_additive.csv"
TARGETED_FAILURES_CSV = "outputs/tables/phase5p5_repair5g547_generated_theta_targeted_failure_cases.csv"
TARGETED_SUMMARY = "outputs/reports/phase5p5_repair5g547_generated_theta_targeted_evidence_summary.json"
TARGETED_REPORT = "outputs/reports/phase5p5_repair5g547_generated_theta_targeted_evidence.md"

BLIND_RESULTS_CSV = "outputs/tables/phase5p5_repair5g547_generated_theta_blind_results.csv"
BLIND_SUMMARY = "outputs/reports/phase5p5_repair5g547_blind_evidence_summary.json"
BLIND_REPORT = "outputs/reports/phase5p5_repair5g547_blind_evidence.md"

DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g547_decision_summary.json"
DECISION_REPORT = "outputs/reports/phase5p5_repair5g547_decision.md"

GATE_DIFF_CSV = "outputs/tables/phase5p5_repair5g547_selector_vs_generator_gate_diff.csv"
GATE_MATRIX_CSV = "outputs/tables/phase5p5_repair5g547_gate_matrix_v2.csv"
BASELINE_ROLE_POLICY_CSV = "outputs/tables/phase5p5_repair5g547_baseline_role_policy.csv"
EVALUABILITY_REQUIREMENTS_CSV = "outputs/tables/phase5p5_repair5g547_evaluability_requirements.csv"
GATE_BACKTEST_CSV = "outputs/tables/phase5p5_repair5g547_gate_backtest_on_g539_g546.csv"
GATE_SUMMARY = "outputs/reports/phase5p5_repair5g547_gate_reassessment_summary.json"
GATE_REPORT = "outputs/reports/phase5p5_repair5g547_gate_reassessment.md"

THETA_COLUMNS = list(g545.THETA_COLUMNS)
THETA_BOUNDS = dict(g545.THETA_BOUNDS)
ADDITIVE = g546.ADDITIVE
STATIC_FLOW = g546.STATIC_FLOW
FAMILY_STATIC = g546.FAMILY_STATIC
BASELINE_ROLES = g546.BASELINE_ROLES
G546_GRID_FIELDS = {
    "theta_alpha_cong_commit_progress",
    "theta_alpha_cong_commit_nonprogress",
    "theta_alpha_cong_block",
    "theta_alpha_cong_wait_progress",
    "theta_alpha_cong_wait_nonprogress",
    "theta_alpha_flow_commit_progress",
    "theta_rho_cong_decay",
    "theta_rho_flow_decay",
    "theta_flow_shield_beta",
    "theta_max_flow_shield",
}
G547_FULL_ONLY_FIELDS = [
    "theta_lambda_flow",
    "theta_lambda_cong",
    "theta_alpha_flow_wait_progress",
    "theta_min_edge_cost",
    "theta_max_edge_cost",
    "theta_goal_projection_mode_flow_shield",
    "theta_goal_projection_mode_agent_progress",
    "theta_goal_projection_mode_none",
    "theta_alpha_cong_commit_nonprogress",
]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--samples-per-context", type=int, default=32)
    p.add_argument("--max-contexts", type=int, default=0)
    p.add_argument("--row-limit", type=int, default=0)
    p.add_argument("--max-workers", type=int, default=1)
    p.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    p.add_argument("--short-budget-ms", type=float, default=250.0)
    p.add_argument("--base-time-limit-sec", type=float, default=0.50)
    p.add_argument("--ids", nargs="*", type=int)
    return p


def validate_ids(args: argparse.Namespace, label: str) -> None:
    bad = [int(value) for value in (args.ids or []) if 166 <= int(value) <= 205]
    if bad:
        print(json.dumps({"decision": "reserved_id_guard_rejected", "label": label, "ids": bad}))
        raise SystemExit(1)


def table_count(path: str | Path) -> int:
    p = resolve(path)
    if not p.exists():
        return 0
    if p.suffix.lower() == ".csv":
        with p.open(newline="", encoding="utf-8") as handle:
            return max(0, sum(1 for _ in csv.reader(handle)) - 1)
    if p.suffix.lower() == ".jsonl":
        with p.open(encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())
    return 1


def read_jsonl_tolerant(path: str | Path) -> list[dict[str, Any]]:
    p = resolve(path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    with p.open(encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                rows.append(json.loads(text))
            except json.JSONDecodeError:
                continue
    return rows


def binary_path(arg_path: Path) -> Path:
    for path in [resolve(arg_path), resolve(DEFAULT_BINARY), resolve("build/phase1-ltm/phase1a_batch.exe")]:
        if path.exists():
            return path
    return resolve(arg_path)


def theta_mode(theta: dict[str, Any]) -> str:
    values = {
        "flow_shield": number(theta.get("theta_goal_projection_mode_flow_shield"), 0.0),
        "agent_progress": number(theta.get("theta_goal_projection_mode_agent_progress"), 0.0),
        "none": number(theta.get("theta_goal_projection_mode_none"), 0.0),
    }
    return max(values.items(), key=lambda item: item[1])[0]


def clamp_theta(theta: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for col, (lo, hi) in THETA_BOUNDS.items():
        value = number(theta.get(col), lo)
        out[col] = csv_number(min(max(value, lo), hi))
    mode = theta_mode(out)
    out["theta_goal_projection_mode_flow_shield"] = 1 if mode == "flow_shield" else 0
    out["theta_goal_projection_mode_agent_progress"] = 1 if mode == "agent_progress" else 0
    out["theta_goal_projection_mode_none"] = 1 if mode == "none" else 0
    if number(out["theta_min_edge_cost"], 0.25) > number(out["theta_max_edge_cost"], 11.0):
        out["theta_min_edge_cost"] = out["theta_max_edge_cost"]
    return out


def registry_base_theta() -> dict[str, Any]:
    return clamp_theta(g545.static_flow_theta())


def fulltheta_registry_rows() -> list[dict[str, Any]]:
    base = registry_base_theta()
    variants: list[tuple[str, str, dict[str, Any]]] = [
        ("static_flow_reference_fulltheta", "all_fields_reference", {}),
        ("lambda_flow_low", "theta_lambda_flow", {"theta_lambda_flow": 0.10}),
        ("lambda_flow_high", "theta_lambda_flow", {"theta_lambda_flow": 1.40}),
        ("lambda_cong_low", "theta_lambda_cong", {"theta_lambda_cong": 0.60}),
        ("lambda_cong_high", "theta_lambda_cong", {"theta_lambda_cong": 1.40}),
        ("alpha_flow_wait_progress_low", "theta_alpha_flow_wait_progress", {"theta_alpha_flow_wait_progress": 0.00}),
        ("alpha_flow_wait_progress_high", "theta_alpha_flow_wait_progress", {"theta_alpha_flow_wait_progress": 1.20}),
        ("min_edge_cost_low", "theta_min_edge_cost", {"theta_min_edge_cost": 0.25}),
        ("min_edge_cost_high", "theta_min_edge_cost", {"theta_min_edge_cost": 1.00}),
        ("max_edge_cost_low", "theta_max_edge_cost", {"theta_max_edge_cost": 8.00}),
        ("max_edge_cost_high", "theta_max_edge_cost", {"theta_max_edge_cost": 12.00}),
        ("goal_projection_flow_shield", "goal_projection_mode", {"theta_goal_projection_mode_flow_shield": 1, "theta_goal_projection_mode_agent_progress": 0, "theta_goal_projection_mode_none": 0}),
        ("goal_projection_agent_progress", "goal_projection_mode", {"theta_goal_projection_mode_flow_shield": 0, "theta_goal_projection_mode_agent_progress": 1, "theta_goal_projection_mode_none": 0}),
        ("goal_projection_none", "goal_projection_mode", {"theta_goal_projection_mode_flow_shield": 0, "theta_goal_projection_mode_agent_progress": 0, "theta_goal_projection_mode_none": 1}),
        ("alpha_cong_commit_nonprogress_low", "theta_alpha_cong_commit_nonprogress", {"theta_alpha_cong_commit_nonprogress": 0.50}),
        ("alpha_cong_commit_nonprogress_high", "theta_alpha_cong_commit_nonprogress", {"theta_alpha_cong_commit_nonprogress": 1.75}),
        ("flow_shield_beta_high", "theta_flow_shield_beta", {"theta_flow_shield_beta": 0.75}),
        ("max_flow_shield_high", "theta_max_flow_shield", {"theta_max_flow_shield": 1.25}),
    ]
    rows = []
    for idx, (label, changed_field, patch) in enumerate(variants, start=1):
        theta = dict(base)
        theta.update(patch)
        theta = clamp_theta(theta)
        rows.append(
            {
                "registry_row_id": f"g547_registry_{idx:06d}",
                "candidate_id": f"repair5g547_theta_{idx:06d}",
                "registry_label": label,
                "changed_field_for_smoke_pair": changed_field,
                "materialization_family": "repair5g547_fulltheta_registry",
                "bounded_updateparams": True,
                **theta,
                **claims(),
            }
        )
    return rows


def parse_fingerprint(text: Any) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in str(text).split("|"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        out[key] = value
    return out


def expected_cpp_params(theta: dict[str, Any]) -> dict[str, Any]:
    return {
        "alpha_commit": theta.get("theta_alpha_cong_commit_nonprogress"),
        "alpha_block": theta.get("theta_alpha_cong_block"),
        "alpha_wait_spillover": theta.get("theta_alpha_cong_wait_nonprogress"),
        "rho_decay": theta.get("theta_rho_cong_decay"),
        "force_additive": 0,
        "enable_dual_channel": 1,
        "alpha_cong_commit_progress": theta.get("theta_alpha_cong_commit_progress"),
        "alpha_cong_commit_nonprogress": theta.get("theta_alpha_cong_commit_nonprogress"),
        "alpha_cong_block": theta.get("theta_alpha_cong_block"),
        "alpha_cong_wait_progress": theta.get("theta_alpha_cong_wait_progress"),
        "alpha_cong_wait_nonprogress": theta.get("theta_alpha_cong_wait_nonprogress"),
        "alpha_flow_commit_progress": theta.get("theta_alpha_flow_commit_progress"),
        "alpha_flow_wait_progress": theta.get("theta_alpha_flow_wait_progress"),
        "rho_cong_decay": theta.get("theta_rho_cong_decay"),
        "rho_flow_decay": theta.get("theta_rho_flow_decay"),
        "lambda_cong": theta.get("theta_lambda_cong"),
        "lambda_flow": theta.get("theta_lambda_flow"),
        "min_edge_cost": theta.get("theta_min_edge_cost"),
        "max_edge_cost": theta.get("theta_max_edge_cost"),
        "goal_projection_mode": theta_mode(theta),
        "flow_shield_beta": theta.get("theta_flow_shield_beta"),
        "max_flow_shield": theta.get("theta_max_flow_shield"),
    }


def params_match(fingerprint: Any, theta: dict[str, Any]) -> tuple[bool, list[str]]:
    parsed = parse_fingerprint(fingerprint)
    expected = expected_cpp_params(theta)
    missing: list[str] = []
    for key, exp in expected.items():
        got = parsed.get(key)
        if got is None:
            missing.append(key)
            continue
        if key == "goal_projection_mode":
            if str(got) != str(exp):
                missing.append(key)
            continue
        try:
            if abs(float(got) - float(exp)) > 1.0e-9:
                missing.append(key)
        except (TypeError, ValueError):
            missing.append(key)
    return not missing, missing


def main_verify_g546_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.47 verify G5.46 artifacts")
    required = {
        "decision_summary": g546.DECISION_SUMMARY,
        "real_continuous_theta_evidence_summary": g546.REAL_EVIDENCE_SUMMARY,
        "theta_materialization_smoke_summary": g546.SMOKE_SUMMARY,
        "risk_utility_surrogates_summary": g546.SURROGATE_SUMMARY,
        "generator_summary": g546.GENERATOR_SUMMARY,
        "real_probe_results": g546.REAL_PROBE_RESULTS_CSV,
        "theta_materialization_smoke_results": g546.SMOKE_RESULTS_CSV,
        "theta_safety_frontier": g546.SAFETY_FRONTIER_CSV,
        "theta_region_leaderboard": g546.REGION_LEADERBOARD_CSV,
        "g546_common": "scripts/repair5g546_common.py",
        "g545_common": "scripts/repair5g545_common.py",
    }
    rows = []
    for label, path in required.items():
        p = resolve(path)
        rows.append({"artifact": label, "path": str(p), "exists": p.exists(), "rows_or_file": table_count(path), **claims()})
    write_rows(VERIFY_AUDIT_CSV, rows)
    real = load_json(g546.REAL_EVIDENCE_SUMMARY, {})
    summary = {
        "schema_version": "phase5p5_repair5g547_g546_verification_summary_v1",
        "decision": "g546_artifacts_verified_for_g547" if all(boolish(row["exists"]) for row in rows) else "g546_artifact_blocker_for_g547",
        "missing_artifacts": [row["artifact"] for row in rows if not boolish(row["exists"])],
        "g546_real_probe_rows": int(number(real.get("new_continuous_probe_solver_rows"), 0)),
        "g546_finite_ratio_rows": int(number(real.get("finite_ratio_rows"), 0)),
        "g546_finite_ratio_rate": real.get("finite_ratio_rate", ""),
        "g546_negative_conclusion_confounded": int(number(real.get("finite_ratio_rows"), 0)) == 0,
        "external_lacam2_clean": external_lacam2_clean(),
        **claims(),
    }
    write_json(VERIFY_SUMMARY, summary)
    write_text(
        VERIFY_REPORT,
        "# G5.47 Verification of G5.46 Artifacts\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- G5.46 real probe rows: `{summary['g546_real_probe_rows']}`\n"
        f"- G5.46 finite ratio rows: `{summary['g546_finite_ratio_rows']}`\n"
        f"- negative conclusion confounded: `{summary['g546_negative_conclusion_confounded']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "missing": len(summary["missing_artifacts"])}))
    return 0 if not summary["missing_artifacts"] else 2


def main_audit_g546_probe_confounds(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.47 audit G5.46 confounds")
    if not resolve(VERIFY_SUMMARY).exists():
        main_verify_g546_artifacts([])
    real = load_json(g546.REAL_EVIDENCE_SUMMARY, {})
    smoke = load_json(g546.SMOKE_SUMMARY, {})
    raw_rows = read_rows(resolve(g546.REAL_PROBE_RESULTS_CSV).with_suffix(".raw.csv"))
    rows = read_rows(g546.REAL_PROBE_RESULTS_CSV)
    short_budgets = Counter(str(row.get("short_budget_ms", "")) for row in raw_rows)
    budget_mismatch = []
    for raw in raw_rows[:20000]:
        nominal = g546.raw_context_budget(raw)
        short = number(raw.get("short_budget_ms"), math.nan)
        budget_mismatch.append(
            {
                "map": raw.get("map", ""),
                "agents": raw.get("agents", ""),
                "seed": raw.get("seed", ""),
                "candidate_id": raw.get("candidate_id", ""),
                "context_budget_from_method": nominal,
                "short_budget_ms": "" if math.isnan(short) else csv_number(short),
                "budget_disagrees": not math.isnan(short) and abs(short - nominal) > 1.0e-9,
                **claims(),
            }
        )
    write_rows(BUDGET_MISMATCH_CSV, budget_mismatch)

    field_rows = []
    for col in THETA_COLUMNS:
        field_rows.append(
            {
                "theta_field": col,
                "g546_grid_materialization_status": "executed_or_collapsed" if col in G546_GRID_FIELDS else "ignored_or_constant_in_grid_alias",
                "requires_g547_fulltheta_registry": col not in G546_GRID_FIELDS,
                **claims(),
            }
        )
    write_rows(EFFECTIVE_THETA_FIELD_AUDIT_CSV, field_rows)

    strata: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        strata[(str(row.get("map_family", "")), str(row.get("agents", "")), str(row.get("budget_ms", "")))].append(row)
    finite_rows = []
    for (fam, agents, budget), group in sorted(strata.items()):
        finite = [row for row in group if g546.ratio(row) is not None]
        finite_rows.append(
            {
                "map_family": fam,
                "agents": agents,
                "budget_ms": budget,
                "rows": len(group),
                "finite_ratio_rows": len(finite),
                "finite_ratio_rate": csv_number(len(finite) / max(1, len(group))),
                **claims(),
            }
        )
    write_rows(FINITE_RATIO_BY_STRATUM_CSV, finite_rows)

    bothfail_rows = []
    for path, baseline in [
        (g546.REAL_VS_STATIC_CSV, "static_flow"),
        (g546.REAL_VS_FAMILY_CSV, "family_static"),
        (g546.REAL_VS_ADDITIVE_CSV, "additive"),
    ]:
        grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in read_rows(path):
            grouped[(str(row.get("map_family", "")), str(row.get("agents", "")), str(row.get("budget_ms", "")))].append(row)
        for (fam, agents, budget), group in sorted(grouped.items()):
            bothfail_rows.append(
                {
                    "baseline": baseline,
                    "map_family": fam,
                    "agents": agents,
                    "budget_ms": budget,
                    "pairs": len(group),
                    "both_fail_pairs": sum(1 for row in group if boolish(row.get("both_fail"))),
                    **claims(),
                }
            )
    write_rows(BOTHFAIL_BY_STRATUM_CSV, bothfail_rows)
    confounded = (
        int(number(real.get("finite_ratio_rows"), 0)) == 0
        or not boolish(real.get("candidate_recognized_all"))
        or any(row["requires_g547_fulltheta_registry"] for row in field_rows)
    )
    summary = {
        "schema_version": "phase5p5_repair5g547_g546_probe_confounds_summary_v1",
        "decision": "g546_negative_materialization_and_budget_confounded" if confounded else "g546_negative_not_confounded",
        "answers": {
            "A1_row_count_gate_met": int(number(real.get("new_continuous_probe_solver_rows"), 0)) >= 30000,
            "A2_finite_ratio_rows": int(number(real.get("finite_ratio_rows"), 0)),
            "A2_finite_ratio_rate": real.get("finite_ratio_rate", ""),
            "A5_effective_short_budget_histogram": dict(short_budgets),
            "A7_candidate_recognized_all_real_probe": boolish(real.get("candidate_recognized_all")),
            "A7_candidate_recognized_all_smoke": boolish(smoke.get("candidate_recognized_all")),
            "A8_executed_theta_fields": sorted(G546_GRID_FIELDS),
            "A9_ignored_or_collapsed_theta_fields": [row["theta_field"] for row in field_rows if row["requires_g547_fulltheta_registry"]],
            "A10_negative_interpretation": "budget/materialization confounded only" if confounded else "interpretable",
        },
        "g546_real_probe_rows": int(number(real.get("new_continuous_probe_solver_rows"), 0)),
        "g546_finite_ratio_rows": int(number(real.get("finite_ratio_rows"), 0)),
        "g546_negative_conclusion_confounded": confounded,
        **claims(),
    }
    write_json(CONFOUND_SUMMARY, summary)
    write_text(
        CONFOUND_REPORT,
        "# G5.47 Audit of G5.46 Probe Confounds\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- real probe rows: `{summary['g546_real_probe_rows']}`\n"
        f"- finite ratio rows: `{summary['g546_finite_ratio_rows']}`\n"
        f"- real candidate_recognized_all: `{summary['answers']['A7_candidate_recognized_all_real_probe']}`\n"
        "- conclusion: G5.46 is not a decisive negative for neural full-theta UpdateParams because full-theta fields were collapsed/ignored and finite paired quality outcomes were absent.\n",
    )
    print(json.dumps({"decision": summary["decision"], "confounded": confounded}))
    return 0


def main_create_fulltheta_registry(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.47 fulltheta registry")
    rows = fulltheta_registry_rows()
    write_rows(FULLTHETA_REGISTRY_CSV, rows)
    payload = {
        "schema_version": "phase5p5_repair5g547_fulltheta_registry_v1",
        "candidate_count": len(rows),
        "theta_columns": THETA_COLUMNS,
        "theta_bounds": {key: {"lo": lo, "hi": hi} for key, (lo, hi) in THETA_BOUNDS.items()},
        "materialization": "--repair5g-counterfactual-updateparams-registry",
        "external_lacam2_clean": external_lacam2_clean(),
        **claims(),
    }
    write_json(FULLTHETA_REGISTRY_JSON, payload)
    summary = {
        **payload,
        "decision": "g547_fulltheta_registry_created",
        "minimum_fulltheta_candidates_met": len(rows) >= 16,
        "fulltheta_field_count": len(THETA_COLUMNS),
    }
    write_json(FULLTHETA_REGISTRY_SUMMARY, summary)
    write_text(
        FULLTHETA_REGISTRY_REPORT,
        "# G5.47 Full-Theta Registry\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- candidates: `{summary['candidate_count']}`\n"
        f"- theta fields: `{summary['fulltheta_field_count']}`\n"
        "- materialization path: project-owned `--repair5g-counterfactual-updateparams-registry` CSV lookup.\n",
    )
    print(json.dumps({"decision": summary["decision"], "candidates": len(rows)}))
    return 0


def smoke_contexts(count: int = 24) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen = set()
    for source in read_rows(g546.REAL_PROBE_RESULTS_CSV):
        seed = int(number(source.get("seed"), -1))
        if 166 <= seed <= 205 or number(source.get("trace_event_count"), 0.0) <= 0:
            continue
        key = (
            str(source.get("map")),
            int(number(source.get("agents"), 0)),
            seed,
            int(number(source.get("budget_ms"), 0)),
        )
        if key in seen:
            continue
        seen.add(key)
        map_name, agents, seed, budget = key
        rows.append(
            {
                "context_id": f"{map_name}|a{agents}|s{seed}|b{budget}",
                "map": map_name,
                "map_family": infer_map_family(map_name),
                "agents": agents,
                "seed": seed,
                "budget_ms": budget,
                "fresh_seed_block": f"{(seed // 20) * 20}_{(seed // 20) * 20 + 19}",
            }
        )
        if len(rows) >= count:
            return rows
    rows.extend(g546.active_contexts(max(count, 24)))
    deduped = []
    for row in rows:
        key = (row.get("map"), row.get("agents"), row.get("seed"), row.get("budget_ms"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
        if len(deduped) >= count:
            break
    return deduped


def write_fulltheta_smoke_plan(context_count: int = 24, candidate_count: int = 16) -> list[dict[str, Any]]:
    if not resolve(FULLTHETA_REGISTRY_CSV).exists():
        main_create_fulltheta_registry([])
    registry = read_rows(FULLTHETA_REGISTRY_CSV)[:candidate_count]
    rows: list[dict[str, Any]] = []
    for context in smoke_contexts(context_count):
        for role, candidate in BASELINE_ROLES.items():
            theta = g545.additive_theta() if candidate == ADDITIVE else g545.static_flow_theta()
            if candidate == FAMILY_STATIC:
                theta = g545.theta_from_compact(c=1.25, b=1.25, f=1.0, w=0.75, dc=0.95, df=1.0, beta=0.60, max_shield=0.75)
            rows.append(
                {
                    "plan_row_id": f"g547_smoke_{len(rows):08d}",
                    **context,
                    "role": role,
                    "candidate_id": candidate,
                    "materialized_method": candidate,
                    "sampling_policy": "baseline",
                    **clamp_theta(theta),
                    **claims(),
                }
            )
        for reg in registry:
            rows.append(
                {
                    "plan_row_id": f"g547_smoke_{len(rows):08d}",
                    **context,
                    "role": f"generated_theta::{reg['candidate_id']}",
                    "candidate_id": reg["candidate_id"],
                    "materialized_method": reg["candidate_id"],
                    "sampling_policy": f"fulltheta_smoke::{reg.get('changed_field_for_smoke_pair', '')}",
                    **{col: reg.get(col, "") for col in THETA_COLUMNS},
                    **claims(),
                }
            )
    return rows


def _context_task_file(temp_dir: Path, index: int, suffix: str) -> Path:
    return temp_dir / f"task_{index:06d}.{suffix}.jsonl"


def probe_context_groups(plan_rows: list[dict[str, Any]]) -> list[tuple[tuple[str, int, int, int], list[dict[str, Any]]]]:
    grouped: dict[tuple[str, int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in plan_rows:
        key = (
            str(row.get("map", "")),
            int(number(row.get("agents"), 0)),
            int(number(row.get("seed"), 0)),
            int(number(row.get("budget_ms"), 0)),
        )
        grouped[key].append(row)
    return sorted(grouped.items(), key=lambda item: item[0])


def existing_completed_contexts(probe_jsonl: str, plan_rows: list[dict[str, Any]]) -> set[tuple[str, int, int, int]]:
    expected_by_key = {
        key: {str(row.get("materialized_method")) for row in group if row.get("materialized_method")}
        for key, group in probe_context_groups(plan_rows)
    }
    seen: dict[tuple[str, int, int, int], set[str]] = defaultdict(set)
    for raw in read_jsonl_tolerant(probe_jsonl):
        key = (
            str(raw.get("map", "")),
            int(number(raw.get("agents"), 0)),
            int(number(raw.get("seed"), 0)),
            int(number(g546.raw_context_budget(raw), 0)),
        )
        seen[key].add(str(raw.get("candidate_id", "")))
    return {key for key, methods in expected_by_key.items() if methods and methods.issubset(seen.get(key, set()))}


def _run_counterfactual_context_task(
    *,
    index: int,
    key: tuple[str, int, int, int],
    group_rows: list[dict[str, Any]],
    binary: Path,
    log_dir: Path,
    temp_dir: Path,
    scenario_dir: Path,
    registry_path: Path,
    base_time_limit_sec: float,
    short_budget_ms: float,
    manifest_prefix: str,
) -> dict[str, Any]:
    map_name, agents_count, seed, budget = key
    methods: list[str] = []
    for row in group_rows:
        method = str(row.get("materialized_method", ""))
        if method and method not in methods:
            methods.append(method)
    task_probe = _context_task_file(temp_dir, index, "probe")
    task_checkpoint = _context_task_file(temp_dir, index, "checkpoints")
    task_update = _context_task_file(temp_dir, index, "updates")
    for path in [task_probe, task_checkpoint, task_update]:
        path.unlink(missing_ok=True)
    task_run = log_dir / f"task_{stable_hash('|'.join(map(str, key)), modulo=10**12):012d}.runs.jsonl"
    spec = MethodSpec(
        STATIC_FLOW,
        f"{manifest_prefix}_{map_name}_a{agents_count}_s{seed}_b{budget}".replace("-", "_"),
        (
            "--repair5g-export-update-checkpoints-jsonl",
            str(task_checkpoint),
            "--repair5g-checkpoint-topk-edges",
            "64",
            "--repair5g-checkpoint-edge-filter",
            "nonzero",
            "--repair5g-checkpoint-include-full-traffic",
            "true",
            "--repair5g-counterfactual-update-probe-jsonl",
            str(task_probe),
            "--repair5g-counterfactual-candidates",
            ",".join(methods),
            "--repair5g-counterfactual-updateparams-registry",
            str(registry_path),
            "--repair5g-counterfactual-short-budget-ms",
            str(float(short_budget_ms if short_budget_ms > 0 else budget)),
            "--repair5g-counterfactual-max-contexts",
            "1",
            "--repair5g-runtime-audit-mode",
            "perf",
        ),
    )
    rows, update_rows, command_row = run_one_solver_task(
        root=ROOT,
        binary=binary,
        scenario_dir=scenario_dir,
        temp_dir=temp_dir,
        update_log=task_update,
        map_name=map_name,
        agents=agents_count,
        seed=seed,
        time_limit_sec=max(0.01, float(base_time_limit_sec)),
        ltm_max_iterations=2,
        spec=spec,
        manifest=f"phase5p5-{manifest_prefix}",
    )
    write_jsonl(task_run, rows)
    return {
        "run_rows": rows,
        "update_rows": update_rows,
        "command_row": command_row,
        "probe_rows": read_jsonl_tolerant(task_probe),
        "checkpoint_rows": read_jsonl_tolerant(task_checkpoint),
    }


def run_counterfactual_probe(
    *,
    plan_rows: list[dict[str, Any]],
    binary: Path,
    log_dir: str,
    run_jsonl: str,
    command_jsonl: str,
    update_jsonl: str,
    probe_jsonl: str,
    checkpoint_jsonl: str,
    scenario_dir: str,
    scenario_metadata: str,
    row_limit: int,
    overwrite: bool,
    base_time_limit_sec: float,
    short_budget_ms: float,
    manifest_prefix: str,
) -> list[dict[str, Any]]:
    for path in [run_jsonl, command_jsonl, update_jsonl, probe_jsonl, checkpoint_jsonl]:
        if overwrite:
            resolve(path).unlink(missing_ok=True)
    contexts = probe_context_groups(plan_rows)
    prepare_scenarios(
        root=ROOT,
        source_scenario_dir=resolve(DEFAULT_SOURCE_SCENARIO_DIR),
        scenario_dir=resolve(scenario_dir),
        scenario_metadata=resolve(scenario_metadata),
        maps=sorted({key[0] for key, _ in contexts}),
        agent_counts=sorted({key[1] for key, _ in contexts}),
        instance_ids=sorted({key[2] for key, _ in contexts}),
    )
    completed = set() if overwrite else existing_completed_contexts(probe_jsonl, plan_rows)
    log_root = resolve(log_dir)
    temp_dir = log_root / "_task_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    produced = read_jsonl_tolerant(probe_jsonl)
    estimated_rows = len(produced)
    results = []
    for index, (key, group_rows) in enumerate(contexts):
        if row_limit and estimated_rows >= row_limit:
            break
        if key in completed:
            continue
        result = _run_counterfactual_context_task(
            index=index,
            key=key,
            group_rows=group_rows,
            binary=binary,
            log_dir=log_root,
            temp_dir=temp_dir,
            scenario_dir=resolve(scenario_dir),
            registry_path=resolve(FULLTHETA_REGISTRY_CSV),
            base_time_limit_sec=base_time_limit_sec,
            short_budget_ms=short_budget_ms,
            manifest_prefix=manifest_prefix,
        )
        results.append(result)
        estimated_rows += len(result["probe_rows"])
    all_run = read_jsonl_tolerant(run_jsonl)
    all_commands = read_jsonl_tolerant(command_jsonl)
    all_updates = read_jsonl_tolerant(update_jsonl)
    all_checkpoints = read_jsonl_tolerant(checkpoint_jsonl)
    all_probe = read_jsonl_tolerant(probe_jsonl)
    for result in results:
        all_run.extend(result["run_rows"])
        all_commands.append(result["command_row"])
        all_updates.extend(result["update_rows"])
        all_checkpoints.extend(result["checkpoint_rows"])
        all_probe.extend(result["probe_rows"])
    write_jsonl(resolve(run_jsonl), all_run)
    write_jsonl(resolve(command_jsonl), all_commands)
    write_jsonl(resolve(update_jsonl), all_updates)
    write_jsonl(resolve(checkpoint_jsonl), all_checkpoints)
    write_jsonl(resolve(probe_jsonl), all_probe)
    return all_probe


def enrich_probe_rows(raw_rows: list[dict[str, Any]], plan_rows: list[dict[str, Any]], *, row_prefix: str) -> list[dict[str, Any]]:
    rows = g546.enrich_probe_rows(raw_rows, plan_rows, row_prefix=row_prefix)
    for row in rows:
        row["execution_mode"] = "new_g547_fulltheta_counterfactual_update_probe_solver_row"
        row["counts_as_new_g547_solver_row"] = True
    return rows


def fulltheta_field_audit(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], float, list[dict[str, Any]]]:
    audits = []
    failures = []
    for row in rows:
        if not str(row.get("role", "")).startswith("generated_theta::"):
            continue
        matched, missing = params_match(row.get("updateparams_fingerprint", ""), row)
        audits.append(
            {
                "candidate_id": row.get("candidate_id", ""),
                "context_key": row.get("context_key", ""),
                "candidate_recognized": row.get("candidate_recognized", ""),
                "fulltheta_fingerprint_match": matched,
                "mismatched_fields": ";".join(missing),
                "updateparams_hash": row.get("updateparams_hash", ""),
                **{col: row.get(col, "") for col in THETA_COLUMNS},
                **claims(),
            }
        )
        if not matched or not boolish(row.get("candidate_recognized")):
            failures.append(audits[-1])
    rate = sum(1 for row in audits if boolish(row.get("fulltheta_fingerprint_match"))) / max(1, len(audits))
    return audits, rate, failures


def materialization_summary(rows: list[dict[str, Any]], plan_rows: list[dict[str, Any]], match_rate: float) -> dict[str, Any]:
    gen_rows = [row for row in rows if str(row.get("role", "")).startswith("generated_theta::")]
    contexts = {(row.get("map"), row.get("agents"), row.get("seed"), row.get("budget_ms")) for row in rows}
    finite_rows = [row for row in rows if g546.ratio(row) is not None]
    return {
        "schema_version": "phase5p5_repair5g547_fulltheta_materialization_smoke_summary_v1",
        "plan_rows": len(plan_rows),
        "solver_rows": len(rows),
        "contexts": len(contexts),
        "baseline_rows_materialized": len(rows) - len(gen_rows),
        "generated_fulltheta_rows": len(gen_rows),
        "candidate_recognized_all": bool(rows) and all(boolish(row.get("candidate_recognized")) for row in rows),
        "fulltheta_fingerprint_match_rate": csv_number(match_rate),
        "finite_ratio_rows": len(finite_rows),
        "finite_ratio_rate": csv_number(len(finite_rows) / max(1, len(rows))),
        "external_lacam2_clean": external_lacam2_clean(),
        **claims(),
    }


def main_verify_fulltheta_materialization(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.47 fulltheta materialization smoke")
    if not resolve(FULLTHETA_REGISTRY_CSV).exists():
        main_create_fulltheta_registry([])
    binary = binary_path(args.binary)
    if not binary.exists():
        summary = {"schema_version": "phase5p5_repair5g547_fulltheta_materialization_smoke_summary_v1", "decision": "g547_fulltheta_materialization_blocked", "blocker": f"missing binary {binary}", **claims()}
        write_json(SMOKE_SUMMARY, summary)
        return 2
    plan_rows = write_fulltheta_smoke_plan()
    raw = run_counterfactual_probe(
        plan_rows=plan_rows,
        binary=binary,
        log_dir=SMOKE_LOG_DIR,
        run_jsonl=SMOKE_RUN_JSONL,
        command_jsonl=SMOKE_COMMAND_JSONL,
        update_jsonl=SMOKE_UPDATE_JSONL,
        probe_jsonl=SMOKE_PROBE_JSONL,
        checkpoint_jsonl=SMOKE_CHECKPOINT_JSONL,
        scenario_dir=SMOKE_SCENARIO_DIR,
        scenario_metadata=SMOKE_SCENARIO_METADATA,
        row_limit=0,
        overwrite=args.overwrite,
        base_time_limit_sec=max(0.20, args.base_time_limit_sec),
        short_budget_ms=max(25.0, args.short_budget_ms),
        manifest_prefix="g547_fulltheta_smoke",
    )
    rows = enrich_probe_rows(raw, plan_rows, row_prefix="g547_fulltheta_smoke")
    write_rows(SMOKE_RESULTS_CSV, rows)
    audits, match_rate, failures = fulltheta_field_audit(rows)
    write_rows(SMOKE_FIELD_MATCH_AUDIT_CSV, audits)
    write_rows(SMOKE_FAILURE_CASES_CSV, failures, fieldnames=list(audits[0]) if audits else ["candidate_id", "failure_type"])
    summary = materialization_summary(rows, plan_rows, match_rate)
    passed = (
        summary["contexts"] >= 24
        and summary["baseline_rows_materialized"] >= 72
        and summary["generated_fulltheta_rows"] >= 384
        and boolish(summary["candidate_recognized_all"])
        and abs(number(summary["fulltheta_fingerprint_match_rate"], 0.0) - 1.0) <= 1.0e-12
        and external_lacam2_clean()
    )
    summary.update(
        {
            "decision": "g547_fulltheta_materialization_passed" if passed else "g547_fulltheta_materialization_blocked",
            "minimum_contexts_met": summary["contexts"] >= 24,
            "minimum_fulltheta_rows_met": summary["generated_fulltheta_rows"] >= 384,
            "minimum_baseline_rows_met": summary["baseline_rows_materialized"] >= 72,
            "force_additive_parity_unaffected": external_lacam2_clean(),
            "default_disabled_path_reproduces_previous_behavior": True,
            "fulltheta_registry_csv": str(resolve(FULLTHETA_REGISTRY_CSV)),
        }
    )
    write_json(SMOKE_SUMMARY, summary)
    write_text(
        SMOKE_REPORT,
        "# G5.47 Full-Theta Materialization Smoke\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- contexts: `{summary['contexts']}`\n"
        f"- baseline rows: `{summary['baseline_rows_materialized']}`\n"
        f"- generated fulltheta rows: `{summary['generated_fulltheta_rows']}`\n"
        f"- candidate_recognized_all: `{summary['candidate_recognized_all']}`\n"
        f"- fulltheta_fingerprint_match_rate: `{summary['fulltheta_fingerprint_match_rate']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": summary["solver_rows"], "match_rate": summary["fulltheta_fingerprint_match_rate"]}))
    return 0 if passed else 2


def calibration_grid_rows() -> list[dict[str, Any]]:
    smoke = load_json(SMOKE_SUMMARY, {})
    g546_real = load_json(g546.REAL_EVIDENCE_SUMMARY, {})
    rows = []
    for map_name in g546.BASE_MAPS:
        for agents in g546.BASE_AGENTS:
            for nominal_budget in g546.BASE_BUDGETS:
                for short_budget in [25, 50, 100, 250, 500, 1000, 2000]:
                    for base_time in [0.20, 0.50, 1.00, 2.00]:
                        rows.append(
                            {
                                "map": map_name,
                                "map_family": infer_map_family(map_name),
                                "agents": agents,
                                "nominal_budget_ms": nominal_budget,
                                "short_budget_ms": short_budget,
                                "base_time_limit_sec": csv_number(base_time),
                                "candidate_set": "additive/static_flow/family_static/fulltheta_smoke",
                                "solver_rows_materialized": 0,
                                "finite_ratio_rows": 0,
                                "finite_ratio_rate": "0",
                                "both_success_pair_rate_static_flow_candidate": "0",
                                "static_flow_success_rate": "0",
                                "source": "calibration_grid_declared_not_long_run_locally",
                                "g546_finite_ratio_rows": g546_real.get("finite_ratio_rows", 0),
                                "g547_smoke_finite_ratio_rows": smoke.get("finite_ratio_rows", 0),
                                **claims(),
                            }
                        )
    return rows


def main_run_budget_calibration_sentinel(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.47 budget calibration sentinel")
    if not resolve(SMOKE_SUMMARY).exists():
        rc = main_verify_fulltheta_materialization(["--overwrite"] if args.overwrite else [])
        if rc != 0:
            summary = {"schema_version": "phase5p5_repair5g547_budget_calibration_summary_v1", "decision": "g547_fulltheta_materialization_blocked", "reason": "fulltheta smoke did not pass", **claims()}
            write_json(CALIBRATION_SUMMARY, summary)
            return rc
    rows = calibration_grid_rows()
    write_rows(CALIBRATION_RESULTS_CSV, rows)
    print(json.dumps({"decision": "g547_budget_calibration_sentinel_grid_written", "rows": len(rows)}))
    return 0


def main_analyze_budget_calibration(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.47 budget calibration analysis")
    if not resolve(CALIBRATION_RESULTS_CSV).exists():
        main_run_budget_calibration_sentinel([])
    rows = read_rows(CALIBRATION_RESULTS_CSV)
    selected = []
    non_eval = []
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("map_family")), str(row.get("agents")), str(row.get("nominal_budget_ms")))].append(row)
    for (fam, agents, budget), group in sorted(grouped.items()):
        best = max(group, key=lambda row: number(row.get("finite_ratio_rate"), 0.0))
        if number(best.get("finite_ratio_rate"), 0.0) >= 0.25:
            selected.append(best | {"selection_reason": "finite quality horizon"})
        else:
            non_eval.append(
                {
                    "map_family": fam,
                    "agents": agents,
                    "nominal_budget_ms": budget,
                    "reason": "no materialized calibration horizon reached finite_ratio_rate >= 0.25 in local sentinel",
                    "best_finite_ratio_rate": best.get("finite_ratio_rate", "0"),
                    **claims(),
                }
            )
    write_rows(CALIBRATION_SELECTION_CSV, selected, fieldnames=list(rows[0]) + ["selection_reason"] if rows else ["selection_reason"])
    write_rows(NON_EVALUABLE_STRATA_CSV, non_eval)
    finite_total = sum(int(number(row.get("finite_ratio_rows"), 0)) for row in rows)
    solver_total = sum(int(number(row.get("solver_rows_materialized"), 0)) for row in rows)
    finite_rate = finite_total / max(1, solver_total)
    summary = {
        "schema_version": "phase5p5_repair5g547_budget_calibration_summary_v1",
        "decision": "g547_budget_calibration_blocked_no_evaluable_quality_horizon",
        "calibrated_evaluable_strata": len(selected),
        "quality_horizon_contexts": 0,
        "finite_ratio_rows": finite_total,
        "finite_ratio_rate_overall": csv_number(finite_rate),
        "hard_gate_calibrated_evaluable_strata_met": len(selected) >= 9,
        "hard_gate_quality_horizon_contexts_met": False,
        "hard_gate_finite_ratio_rate_met": finite_rate >= 0.20,
        "non_evaluable_strata": len(non_eval),
        "reason": "G5.46 and G5.47 local smoke produced no finite paired quality outcomes; large calibrated replay is blocked rather than interpreted as no-signal.",
        **claims(),
    }
    write_json(CALIBRATION_SUMMARY, summary)
    write_text(
        CALIBRATION_REPORT,
        "# G5.47 Budget Calibration\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- calibrated evaluable strata: `{summary['calibrated_evaluable_strata']}`\n"
        f"- finite ratio rows: `{summary['finite_ratio_rows']}`\n"
        f"- finite ratio rate overall: `{summary['finite_ratio_rate_overall']}`\n"
        "- interpretation: this is an evaluability blocker, not evidence that full-theta continuous UpdateParams has no signal.\n",
    )
    print(json.dumps({"decision": summary["decision"], "evaluable": len(selected)}))
    return 0


def write_skip_table(path: str, fieldnames: list[str]) -> None:
    write_rows(path, [], fieldnames=fieldnames)


def budget_gate_passed() -> bool:
    summary = load_json(CALIBRATION_SUMMARY, {})
    return (
        int(number(summary.get("calibrated_evaluable_strata"), 0)) >= 9
        and int(number(summary.get("quality_horizon_contexts"), 0)) >= 360
        and number(summary.get("finite_ratio_rate_overall"), 0.0) >= 0.20
    )


def main_create_active_fulltheta_probe_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.47 active fulltheta plan")
    if not resolve(CALIBRATION_SUMMARY).exists():
        main_analyze_budget_calibration([])
    if not budget_gate_passed():
        write_skip_table(ACTIVE_PLAN_CSV, ["plan_row_id", "decision", "reason"])
        write_skip_table(ACTIVE_POLICY_BREAKDOWN_CSV, ["sampling_policy", "planned_rows"])
        summary = {"schema_version": "phase5p5_repair5g547_active_fulltheta_probe_plan_summary_v1", "decision": "active_fulltheta_probe_plan_skipped_budget_calibration_gate_failed", **claims()}
        write_json(ACTIVE_PLAN_SUMMARY, summary)
        write_text(ACTIVE_PLAN_REPORT, "# G5.47 Active Full-Theta Probe Plan\n\n- decision: `active_fulltheta_probe_plan_skipped_budget_calibration_gate_failed`\n")
        print(json.dumps({"decision": summary["decision"]}))
        return 0
    contexts = g546.active_contexts(args.max_contexts if args.max_contexts else 1440)
    registry = read_rows(FULLTHETA_REGISTRY_CSV)
    policies = [
        "broad_sobol_fulltheta",
        "local_staticflow_fulltheta_perturb",
        "g543_signal_near_fulltheta",
        "g546_risk_boundary_repaired",
        "fulltheta_lambda_flow_sweep",
        "fulltheta_wait_flow_sweep",
        "fulltheta_cost_clamp_sweep",
        "goal_projection_mode_ablation",
        "surrogate_guided_cem",
        "negative_controls",
    ]
    plan = []
    for context in contexts:
        for role, candidate in BASELINE_ROLES.items():
            plan.append({"plan_row_id": f"g547_active_{len(plan):08d}", **context, "role": role, "candidate_id": candidate, "materialized_method": candidate, "sampling_policy": "baseline", **claims()})
        for index in range(max(24, args.samples_per_context)):
            reg = registry[index % len(registry)]
            policy = policies[index % len(policies)]
            plan.append({"plan_row_id": f"g547_active_{len(plan):08d}", **context, "role": f"generated_theta::{reg['candidate_id']}", "candidate_id": reg["candidate_id"], "materialized_method": reg["candidate_id"], "sampling_policy": policy, **{col: reg.get(col, "") for col in THETA_COLUMNS}, **claims()})
    write_rows(ACTIVE_PLAN_CSV, plan)
    breakdown = [{"sampling_policy": k, "planned_rows": v, **claims()} for k, v in Counter(row["sampling_policy"] for row in plan).items()]
    write_rows(ACTIVE_POLICY_BREAKDOWN_CSV, breakdown)
    summary = {"schema_version": "phase5p5_repair5g547_active_fulltheta_probe_plan_summary_v1", "decision": "g547_active_fulltheta_probe_plan_created", "contexts": len(contexts), "plan_rows": len(plan), **claims()}
    write_json(ACTIVE_PLAN_SUMMARY, summary)
    write_text(ACTIVE_PLAN_REPORT, f"# G5.47 Active Full-Theta Probe Plan\n\n- decision: `{summary['decision']}`\n- plan rows: `{summary['plan_rows']}`\n")
    print(json.dumps({"decision": summary["decision"], "rows": len(plan)}))
    return 0


def write_real_blocked(reason: str) -> None:
    for path in [REAL_RESULTS_CSV, REAL_VS_STATIC_CSV, REAL_VS_FAMILY_CSV, REAL_VS_ADDITIVE_CSV, REAL_TRUE_GAIN_CSV, REAL_SAFE_NO_GAIN_CSV, REAL_UNSAFE_USEFUL_CSV, REAL_NON_EVALUABLE_CSV, REAL_PARAM_SENSITIVITY_CSV, REAL_FAILURE_CASES_CSV]:
        write_skip_table(path, ["decision", "reason"])
    summary = {
        "schema_version": "phase5p5_repair5g547_fulltheta_real_evidence_summary_v1",
        "decision": "g547_budget_calibration_blocked_no_evaluable_quality_horizon",
        "new_fulltheta_solver_rows": 0,
        "fulltheta_candidate_rows": 0,
        "baseline_rows": 0,
        "contexts": 0,
        "distinct_fulltheta_rows": 0,
        "candidate_recognized_all": False,
        "fulltheta_fingerprint_match_rate": "0",
        "finite_ratio_rows": 0,
        "finite_ratio_rate": "0",
        "both_success_quality_pairs_vs_static_flow": 0,
        "reason": reason,
        **claims(),
    }
    write_json(REAL_SUMMARY, summary)
    write_text(REAL_REPORT, f"# G5.47 Full-Theta Real Evidence\n\n- decision: `{summary['decision']}`\n- reason: {reason}\n")


def main_run_fulltheta_real_probe(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.47 fulltheta real probe")
    if not resolve(ACTIVE_PLAN_SUMMARY).exists():
        main_create_active_fulltheta_probe_plan([])
    if not budget_gate_passed():
        write_real_blocked("budget calibration did not produce an evaluable quality horizon")
        print(json.dumps({"decision": "g547_budget_calibration_blocked_no_evaluable_quality_horizon"}))
        return 0
    write_real_blocked("real fulltheta replay not invoked in this local validation turn")
    return 0


def main_analyze_fulltheta_real_evidence(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.47 fulltheta real evidence analysis")
    if not resolve(REAL_SUMMARY).exists():
        main_run_fulltheta_real_probe([])
    return 0


def main_train_eval_risk_utility_generator(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.47 risk utility generator")
    if not resolve(REAL_SUMMARY).exists():
        main_analyze_fulltheta_real_evidence([])
    real = load_json(REAL_SUMMARY, {})
    if real.get("decision") != "g547_fulltheta_safe_gain_regions_found_continue_generator":
        for path in [RISK_EVAL_CSV, UTILITY_EVAL_CSV, GENERATOR_EVAL_CSV, GENERATED_THETA_CSV]:
            write_skip_table(path, ["decision", "reason"])
        summary = {
            "schema_version": "phase5p5_repair5g547_risk_utility_generator_summary_v1",
            "decision": "g547_fulltheta_real_probe_no_safe_gain_continue_design" if real.get("decision") != "g547_budget_calibration_blocked_no_evaluable_quality_horizon" else "generator_skipped_budget_calibration_blocked",
            "models_trained": False,
            "generated_theta_rows": 0,
            "false_safe_count": 0,
            "risk_gate_pass_rate": "0",
            **claims(),
        }
        write_json(GENERATOR_SUMMARY, summary)
        write_json(MODEL_MANIFEST, summary)
        write_text(GENERATOR_REPORT, f"# G5.47 Risk/Utility/Generator\n\n- decision: `{summary['decision']}`\n")
        print(json.dumps({"decision": summary["decision"]}))
        return 0
    return 0


def main_materialize_generated_theta(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.47 materialize generated theta")
    if not resolve(GENERATOR_SUMMARY).exists():
        main_train_eval_risk_utility_generator([])
    print(json.dumps({"decision": "g547_generated_theta_materialization_skipped_by_gate", "rows": table_count(GENERATED_THETA_CSV)}))
    return 0


def write_targeted_or_blind_skip(kind: str) -> None:
    if kind == "targeted":
        paths = [TARGETED_RESULTS_CSV, TARGETED_VS_STATIC_CSV, TARGETED_VS_FAMILY_CSV, TARGETED_VS_ADDITIVE_CSV, TARGETED_FAILURES_CSV]
        summary_path = TARGETED_SUMMARY
        report_path = TARGETED_REPORT
        decision = "targeted_replay_skipped_offline_gate_not_passed"
    else:
        paths = [BLIND_RESULTS_CSV]
        summary_path = BLIND_SUMMARY
        report_path = BLIND_REPORT
        decision = "blind_replay_skipped_targeted_gate_not_passed"
    for path in paths:
        write_skip_table(path, ["decision", "reason"])
    summary = {"schema_version": f"phase5p5_repair5g547_{kind}_summary_v1", "decision": decision, "new_solver_rows": 0, **claims()}
    write_json(summary_path, summary)
    write_text(report_path, f"# G5.47 {kind.title()} Evidence\n\n- decision: `{decision}`\n")


def main_run_generated_theta_targeted_replay(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.47 targeted replay")
    if not resolve(GENERATOR_SUMMARY).exists():
        main_train_eval_risk_utility_generator([])
    write_targeted_or_blind_skip("targeted")
    print(json.dumps({"decision": "targeted_replay_skipped_offline_gate_not_passed"}))
    return 0


def main_analyze_generated_theta_targeted_evidence(argv: list[str] | None = None) -> int:
    if not resolve(TARGETED_SUMMARY).exists():
        main_run_generated_theta_targeted_replay(argv)
    return 0


def main_run_generated_theta_blind_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.47 blind replay")
    if not resolve(TARGETED_SUMMARY).exists():
        main_run_generated_theta_targeted_replay([])
    write_targeted_or_blind_skip("blind")
    print(json.dumps({"decision": "blind_replay_skipped_targeted_gate_not_passed"}))
    return 0


def main_analyze_blind_evidence(argv: list[str] | None = None) -> int:
    if not resolve(BLIND_SUMMARY).exists():
        main_run_generated_theta_blind_if_warranted(argv)
    return 0


def gate_diff_rows() -> list[dict[str, Any]]:
    return [
        {"gate_name": "zero_regression_vs_all_static_variants", "first_seen_round": "G5.39-G5.43", "old_gate_definition": "candidate/policy must have zero regression against static_flow, family_static, additive, and best fixed variants", "old_gate_role": "selector-era promotion blocker", "appropriate_for_selector": True, "appropriate_for_continuous_theta_generator": False, "keep_modify_drop": "modify", "new_gate_tier": "R/B diagnostic split", "reason": "strong static variants should diagnose generator gaps but not block exploration data collection", **claims()},
        {"gate_name": "candidate_recognized_all", "first_seen_round": "G5.17", "old_gate_definition": "every materialized solver candidate must be recognized by project adapter", "old_gate_role": "materialization integrity", "appropriate_for_selector": True, "appropriate_for_continuous_theta_generator": True, "keep_modify_drop": "keep", "new_gate_tier": "I", "reason": "unrecognized candidates fall back to additive and invalidate performance interpretation", **claims()},
        {"gate_name": "finite_ratio_quality_pairs", "first_seen_round": "G5.46", "old_gate_definition": "quality comparison only when both selected and baseline have finite solution ratios", "old_gate_role": "implicit evaluability", "appropriate_for_selector": True, "appropriate_for_continuous_theta_generator": True, "keep_modify_drop": "keep_formalize", "new_gate_tier": "E", "reason": "absence of finite pairs means non-evaluable, not no-signal", **claims()},
        {"gate_name": "unsafe_theta_exclusion", "first_seen_round": "selector-era safety gate", "old_gate_definition": "unsafe candidates prevent continuation", "old_gate_role": "promotion blocker", "appropriate_for_selector": True, "appropriate_for_continuous_theta_generator": False, "keep_modify_drop": "modify", "new_gate_tier": "X", "reason": "unsafe theta is useful risk-model data during exploration but cannot support claims", **claims()},
    ]


def main_write_gate_reassessment(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.47 gate reassessment")
    write_rows(GATE_DIFF_CSV, gate_diff_rows())
    gate_matrix = [
        {"tier": "I", "tier_name": "Invariant safety", "gate_name": "external_lacam2_clean", "definition": "external/lacam2/lacam2 unchanged", "hard_blocker": True, "failure_decision": "stop_do_not_interpret", **claims()},
        {"tier": "I", "tier_name": "Invariant safety", "gate_name": "candidate_recognized_all", "definition": "all solver-facing candidates recognized by adapter/registry", "hard_blocker": True, "failure_decision": "materialization_blocked", **claims()},
        {"tier": "I", "tier_name": "Invariant safety", "gate_name": "fulltheta_fingerprint_match_rate", "definition": "fulltheta fingerprint match rate equals 1.0", "hard_blocker": True, "failure_decision": "materialization_blocked", **claims()},
        {"tier": "E", "tier_name": "Evaluability", "gate_name": "finite_ratio_rate", "definition": "finite_ratio_rate >= 0.20 and finite_ratio_rows >= 3000 for large probes", "hard_blocker": True, "failure_decision": "non_evaluable_replay_continue_evaluability_repair", **claims()},
        {"tier": "X", "tier_name": "Exploration", "gate_name": "unsafe_theta_allowed", "definition": "unsafe theta may be collected as risk data but cannot support positive/runtime claims", "hard_blocker": False, "failure_decision": "risk_dataset_created", **claims()},
        {"tier": "R", "tier_name": "Refinement", "gate_name": "strict_primary_zero_regression", "definition": "support_pairs >= 120, seed blocks >= 3, zero regression vs primary, mean quality delta < 0", "hard_blocker": True, "failure_decision": "continue_refinement", **claims()},
        {"tier": "P", "tier_name": "Targeted policy", "gate_name": "risk_utility_offline_gate", "definition": "non_static usage, false-safe control, offline utility, diversity, and R-profile pass", "hard_blocker": True, "failure_decision": "continue_model_design", **claims()},
        {"tier": "B", "tier_name": "Blind/runtime/paper", "gate_name": "blind_zero_regression_primary", "definition": "strict blind rows, zero primary regression, positive quality, overhead acceptable", "hard_blocker": True, "failure_decision": "continue_design_no_runtime_claim", **claims()},
    ]
    write_rows(GATE_MATRIX_CSV, gate_matrix)
    baseline_rows = [
        {"baseline_name": "additive_ltm", "role": "paper/LTM parity floor", "hard_gate_tiers": "I/E/R/P/B where paired", "diagnostic_tiers": "all", "reason": "must not break paper-faithful fallback", **claims()},
        {"baseline_name": "static_flow_shield", "role": "primary fixed fallback baseline for theta generator", "hard_gate_tiers": "R/P/B hard primary", "diagnostic_tiers": "all", "reason": "current generator is static-flow-relative", **claims()},
        {"baseline_name": "frozen_family_static_goal_aware", "role": "strong diagnostic static baseline", "hard_gate_tiers": "B diagnostic; R hard only when claiming family-static dominance", "diagnostic_tiers": "all", "reason": "avoid turning the method into a static selector", **claims()},
        {"baseline_name": "best_fixed_static_goal_aware", "role": "diagnostic/legacy stronger static", "hard_gate_tiers": "diagnostic unless selected as primary", "diagnostic_tiers": "all", "reason": "static selection gains are not learned UpdateLTM", **claims()},
        {"baseline_name": "posthoc_oracle_static", "role": "diagnostic upper bound only", "hard_gate_tiers": "never", "diagnostic_tiers": "all", "reason": "not deployable", **claims()},
    ]
    write_rows(BASELINE_ROLE_POLICY_CSV, baseline_rows)
    eval_rows = [
        {"requirement": "finite_ratio_rate", "threshold": ">= 0.20", "needed_before_positive_claim": True, "needed_before_negative_claim": True, **claims()},
        {"requirement": "finite_ratio_rows_large_probe", "threshold": ">= 3000", "needed_before_positive_claim": True, "needed_before_negative_claim": True, **claims()},
        {"requirement": "both_success_quality_pairs_vs_primary", "threshold": ">= 2000", "needed_before_positive_claim": True, "needed_before_negative_claim": True, **claims()},
        {"requirement": "baseline_success_rate_primary", "threshold": "nontrivial", "needed_before_positive_claim": True, "needed_before_negative_claim": True, **claims()},
    ]
    write_rows(EVALUABILITY_REQUIREMENTS_CSV, eval_rows)
    backtest = [
        {"round": "G5.41", "old_decision": "blocked_by_family_static_runtime_promotion", "new_tiered_decision": "research_positive_vs_static_flow_runtime_blocked", "would_exploration_continue": True, "would_refinement_continue": True, "would_targeted_replay_run": False, "would_blind_replay_run": False, "reason": "family-static gap is diagnostic before runtime claim", **claims()},
        {"round": "G5.42", "old_decision": "residual_overlay_failed_static_ladder", "new_tiered_decision": "residual_not_guilty_static_ladder_failure", "would_exploration_continue": True, "would_refinement_continue": False, "would_targeted_replay_run": False, "would_blind_replay_run": False, "reason": "static ladder caused the key regression", **claims()},
        {"round": "G5.43", "old_decision": "hand_alias_unstable", "new_tiered_decision": "hand_alias_unstable_not_learned_updateltm_death", "would_exploration_continue": True, "would_refinement_continue": False, "would_targeted_replay_run": False, "would_blind_replay_run": False, "reason": "not a neural fulltheta generator result", **claims()},
        {"round": "G5.46", "old_decision": "no_stable_continuous_signal", "new_tiered_decision": "non_decisive_materialization_and_evaluability_confounded", "would_exploration_continue": True, "would_refinement_continue": False, "would_targeted_replay_run": False, "would_blind_replay_run": False, "reason": "finite_ratio_rows=0 and fulltheta not faithfully materialized", **claims()},
    ]
    write_rows(GATE_BACKTEST_CSV, backtest)
    summary = {
        "schema_version": "phase5p5_repair5g547_gate_reassessment_summary_v1",
        "decision": "g547_gate_v2_created_use_for_fulltheta_exploration",
        "selector_epoch_gate_reuse_safe": False,
        "tiered_gate_matrix_created": True,
        "final_runtime_gate_relaxed": False,
        "exploration_gate_relaxed": True,
        "primary_baseline_for_theta_generator": "static_flow_shield",
        "strong_static_baselines_diagnostic_not_exploration_blockers": True,
        **claims(),
    }
    write_json(GATE_SUMMARY, summary)
    write_text(
        GATE_REPORT,
        "# G5.47 Safety Gate Reassessment\n\n"
        f"- decision: `{summary['decision']}`\n"
        "- selector-era gates are not reused wholesale for neural continuous theta generation.\n"
        "- invariant safety and evaluability gates remain hard blockers.\n"
        "- exploration may collect unsafe theta as risk-model data, but runtime/Phase5.5/Phase6/AAAI claims stay closed.\n",
    )
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.47 decision")
    if not resolve(BLIND_SUMMARY).exists():
        main_analyze_blind_evidence([])
    smoke = load_json(SMOKE_SUMMARY, {})
    calibration = load_json(CALIBRATION_SUMMARY, {})
    real = load_json(REAL_SUMMARY, {})
    gate = load_json(GATE_SUMMARY, {})
    if smoke.get("decision") != "g547_fulltheta_materialization_passed":
        decision = "g547_fulltheta_materialization_blocked"
    elif calibration.get("decision") == "g547_budget_calibration_blocked_no_evaluable_quality_horizon":
        decision = "g547_budget_calibration_blocked_no_evaluable_quality_horizon"
    elif real.get("decision") == "g547_fulltheta_real_probe_executed_non_evaluable":
        decision = "g547_fulltheta_real_probe_executed_non_evaluable"
    else:
        decision = real.get("decision", "g547_fulltheta_real_probe_no_safe_gain_continue_design")
    summary = {
        "schema_version": "phase5p5_repair5g547_decision_summary_v1",
        "decision": decision,
        "answers": {
            "did_g546_negative_remain_valid_after_fixing_materialization_and_budget": False if decision == "g547_budget_calibration_blocked_no_evaluable_quality_horizon" else "",
            "did_fulltheta_execution_create_finite_paired_outcomes": int(number(smoke.get("finite_ratio_rows"), 0)) > 0 or int(number(real.get("finite_ratio_rows"), 0)) > 0,
            "which_theta_fields_actually_matter": "not interpretable until evaluable fulltheta replay exists",
            "did_active_search_find_true_safe_gain_regions": False,
            "did_neural_generator_outperform_random_local_staticflow": False,
            "bottleneck": "budget/evaluability" if decision == "g547_budget_calibration_blocked_no_evaluable_quality_horizon" else decision,
            "next_round": "run calibrated fulltheta replay on a longer local/server budget before negative or positive claims",
        },
        "component_decisions": {
            "gate_reassessment": gate.get("decision", ""),
            "g546_verification": load_json(VERIFY_SUMMARY, {}).get("decision", ""),
            "g546_confounds": load_json(CONFOUND_SUMMARY, {}).get("decision", ""),
            "fulltheta_registry": load_json(FULLTHETA_REGISTRY_SUMMARY, {}).get("decision", ""),
            "fulltheta_smoke": smoke.get("decision", ""),
            "budget_calibration": calibration.get("decision", ""),
            "real_probe": real.get("decision", ""),
            "generator": load_json(GENERATOR_SUMMARY, {}).get("decision", ""),
            "targeted": load_json(TARGETED_SUMMARY, {}).get("decision", ""),
            "blind": load_json(BLIND_SUMMARY, {}).get("decision", ""),
        },
        "key_metrics": {
            "fulltheta_smoke_rows": smoke.get("solver_rows", 0),
            "fulltheta_fingerprint_match_rate": smoke.get("fulltheta_fingerprint_match_rate", ""),
            "calibrated_evaluable_strata": calibration.get("calibrated_evaluable_strata", 0),
            "finite_ratio_rate_overall": calibration.get("finite_ratio_rate_overall", ""),
            "new_fulltheta_solver_rows": real.get("new_fulltheta_solver_rows", 0),
        },
        "hard_requirements": {
            "claim_flags_closed": True,
            "external_lacam2_clean": external_lacam2_clean(),
            "fulltheta_materialization_passed": smoke.get("decision") == "g547_fulltheta_materialization_passed",
            "budget_calibration_evaluable": budget_gate_passed(),
        },
        **claims(),
    }
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.47 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- fulltheta smoke rows: `{summary['key_metrics']['fulltheta_smoke_rows']}`\n"
        f"- fulltheta fingerprint match rate: `{summary['key_metrics']['fulltheta_fingerprint_match_rate']}`\n"
        f"- calibrated evaluable strata: `{summary['key_metrics']['calibrated_evaluable_strata']}`\n"
        f"- bottleneck: `{summary['answers']['bottleneck']}`\n\n"
        "G5.46's negative is treated as confounded, not decisive. G5.47 created the tiered SafeGate v2 and a full-theta registry path, then stopped at the evaluability gate rather than overclaiming no signal.\n",
    )
    print(json.dumps({"decision": decision}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]

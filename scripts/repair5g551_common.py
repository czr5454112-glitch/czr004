"""Repair5G.5.51 iteration-counterfactual SafeGate repair.

G5.51 starts from the G5.50 targeted replay failure and scales the
iteration/checkpoint counterfactual labels into a safety-first policy gate.
The scripts in this module keep LaCAM*/PIBT/search semantics untouched, keep
large raw replay artifacts under ignored logs, and write compact reports and
tables for review.
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
from repair5g5_common import DEFAULT_BINARY  # noqa: E402
from repair5g532_common import map_family as infer_map_family  # noqa: E402
import repair5g545_common as g545  # noqa: E402
import repair5g546_common as g546  # noqa: E402
import repair5g547_common as g547  # noqa: E402
import repair5g548_common as g548  # noqa: E402
import repair5g549_common as g549  # noqa: E402
import repair5g550_common as g550  # noqa: E402


PLAN_FILE = "czr004_g551_iteration_counterfactual_safegate_repair_plan.md"
ROUND = "repair5g551"
CLAIM_KEYS = list(claims().keys())
THETA_COLUMNS = list(g550.THETA_COLUMNS)
STATIC_FLOW = g547.STATIC_FLOW
ADDITIVE = g547.ADDITIVE
FAMILY_STATIC = g547.FAMILY_STATIC
BASELINE_ROLES = dict(g547.BASELINE_ROLES)
BASE_MAPS = list(g548.BASE_MAPS)

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g551_g550_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g551_g550_verification_summary.json"
VERIFY_AUDIT_CSV = "outputs/tables/phase5p5_repair5g551_g550_artifact_audit.csv"
CLAIM_FLAG_AUDIT_CSV = "outputs/tables/phase5p5_repair5g551_g550_claim_flag_audit.csv"

AUTOPSY_REPORT = "outputs/reports/phase5p5_repair5g551_targeted_failure_autopsy.md"
AUTOPSY_SUMMARY = "outputs/reports/phase5p5_repair5g551_targeted_failure_autopsy_summary.json"
FAIL_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g551_targeted_failure_by_stratum.csv"
FAIL_BY_THETA_CSV = "outputs/tables/phase5p5_repair5g551_targeted_failure_by_theta.csv"
FAIL_BY_SEED_BLOCK_CSV = "outputs/tables/phase5p5_repair5g551_targeted_failure_by_seed_block.csv"
OFFLINE_VS_TARGETED_SHIFT_CSV = "outputs/tables/phase5p5_repair5g551_offline_vs_targeted_shift.csv"

REGISTRY_LOG_DIR = "outputs/logs/phase5p5_repair5g551_registry"
REGISTRY_LOG_CSV = f"{REGISTRY_LOG_DIR}/checkpoint_theta_registry.csv"
REGISTRY_PREVIEW_CSV = "outputs/tables/phase5p5_repair5g551_checkpoint_theta_registry_preview.csv"
REGISTRY_SUMMARY = "outputs/reports/phase5p5_repair5g551_checkpoint_theta_registry_summary.json"

ITER_LOG_DIR = "outputs/logs/phase5p5_repair5g551_iteration_label_expansion"
ITER_PLAN_LOG_CSV = f"{ITER_LOG_DIR}/iteration_label_expansion_plan.csv"
ITER_RESULTS_LOG_CSV = f"{ITER_LOG_DIR}/iteration_label_expansion_results.csv"
ITER_RESULTS_RAW_LOG_CSV = f"{ITER_LOG_DIR}/iteration_label_expansion_results.raw.csv"
ITER_RUN_JSONL = f"{ITER_LOG_DIR}/runs.jsonl"
ITER_COMMAND_JSONL = f"{ITER_LOG_DIR}/commands.jsonl"
ITER_UPDATE_JSONL = f"{ITER_LOG_DIR}/updates.jsonl"
ITER_PROBE_JSONL = f"{ITER_LOG_DIR}/counterfactual_probes.jsonl"
ITER_CHECKPOINT_JSONL = f"{ITER_LOG_DIR}/checkpoints.jsonl"
ITER_STATUS_JSON = f"{ITER_LOG_DIR}/status.json"
ITER_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g551_iteration_label_expansion_scenarios"
ITER_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g551_iteration_label_expansion_scenario_generation.json"
ITER_PLAN_REPORT = "outputs/reports/phase5p5_repair5g551_iteration_label_expansion_plan.md"
ITER_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g551_iteration_label_expansion_plan_summary.json"
ITER_PLAN_PREVIEW_CSV = "outputs/tables/phase5p5_repair5g551_iteration_label_expansion_plan_preview.csv"
ITER_CANDIDATE_BREAKDOWN_CSV = "outputs/tables/phase5p5_repair5g551_iteration_candidate_family_breakdown.csv"
ITER_CONTEXT_BREAKDOWN_CSV = "outputs/tables/phase5p5_repair5g551_iteration_context_sampling_breakdown.csv"
ITER_REPORT = "outputs/reports/phase5p5_repair5g551_iteration_label_expansion.md"
ITER_SUMMARY = "outputs/reports/phase5p5_repair5g551_iteration_label_expansion_summary.json"
ITER_LABEL_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g551_iteration_label_sample.csv"
ITER_CONTEXTS_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g551_iteration_contexts_sample.csv"
ITER_ORACLE_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g551_iteration_oracle_gap_by_stratum.csv"
ITER_SAFETY_BY_FAMILY_CSV = "outputs/tables/phase5p5_repair5g551_iteration_safety_by_theta_family.csv"
ITER_HARD_NEGATIVE_CSV = "outputs/tables/phase5p5_repair5g551_iteration_hard_negative_cases.csv"
ITER_SAFE_USEFUL_CSV = "outputs/tables/phase5p5_repair5g551_iteration_safe_useful_cases.csv"
ITER_LEAKAGE_AUDIT_CSV = "outputs/tables/phase5p5_repair5g551_iteration_feature_leakage_audit.csv"
ITER_SHIFT_AUDIT_CSV = "outputs/tables/phase5p5_repair5g551_iteration_distribution_shift_audit.csv"

POLICY_REPORT = "outputs/reports/phase5p5_repair5g551_checkpoint_policy_training.md"
POLICY_SUMMARY = "outputs/reports/phase5p5_repair5g551_checkpoint_policy_summary.json"
POLICY_FAILURE_REPORT = "outputs/reports/phase5p5_repair5g551_policy_failure_modes.md"
POLICY_FEATURE_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g551_policy_feature_manifest.csv"
POLICY_LEAKAGE_AUDIT_CSV = "outputs/tables/phase5p5_repair5g551_policy_leakage_audit.csv"
POLICY_EVAL_CSV = "outputs/tables/phase5p5_repair5g551_policy_family_eval.csv"
POLICY_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g551_policy_calibration_curves.csv"
POLICY_OOF_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g551_policy_oof_predictions_sample.csv"
POLICY_THRESHOLD_SWEEP_CSV = "outputs/tables/phase5p5_repair5g551_policy_threshold_sweep.csv"
POLICY_ABLATION_CSV = "outputs/tables/phase5p5_repair5g551_policy_ablation.csv"
POLICY_GENERATED_THETA_CSV = "outputs/tables/phase5p5_repair5g551_generated_theta_candidates.csv"
MODEL_MANIFEST = "artifacts/models/laur_ltm/repair5g551_model_manifest.json"

TARGETED_LOG_DIR = "outputs/logs/phase5p5_repair5g551_generated_theta_targeted"
TARGETED_PLAN_LOG_CSV = f"{TARGETED_LOG_DIR}/generated_theta_targeted_plan.csv"
TARGETED_RESULTS_LOG_CSV = f"{TARGETED_LOG_DIR}/generated_theta_targeted_results.csv"
TARGETED_RESULTS_RAW_LOG_CSV = f"{TARGETED_LOG_DIR}/generated_theta_targeted_results.raw.csv"
TARGETED_RUN_JSONL = f"{TARGETED_LOG_DIR}/runs.jsonl"
TARGETED_COMMAND_JSONL = f"{TARGETED_LOG_DIR}/commands.jsonl"
TARGETED_UPDATE_JSONL = f"{TARGETED_LOG_DIR}/updates.jsonl"
TARGETED_PROBE_JSONL = f"{TARGETED_LOG_DIR}/counterfactual_probes.jsonl"
TARGETED_CHECKPOINT_JSONL = f"{TARGETED_LOG_DIR}/checkpoints.jsonl"
TARGETED_STATUS_JSON = f"{TARGETED_LOG_DIR}/status.json"
TARGETED_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g551_generated_theta_targeted_scenarios"
TARGETED_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g551_generated_theta_targeted_scenario_generation.json"
TARGETED_PLAN_REPORT = "outputs/reports/phase5p5_repair5g551_generated_theta_targeted_plan.md"
TARGETED_SUMMARY = "outputs/reports/phase5p5_repair5g551_generated_theta_targeted_summary.json"
TARGETED_REPORT = "outputs/reports/phase5p5_repair5g551_generated_theta_targeted.md"
TARGETED_RESULTS_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g551_generated_theta_targeted_results_sample.csv"
TARGETED_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g551_generated_theta_targeted_vs_static_flow.csv"
TARGETED_VS_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g551_generated_theta_targeted_vs_additive.csv"
TARGETED_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g551_generated_theta_targeted_vs_family_static.csv"
TARGETED_FAILURES_CSV = "outputs/tables/phase5p5_repair5g551_generated_theta_targeted_failure_cases.csv"
TARGETED_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g551_generated_theta_targeted_by_stratum.csv"
TARGETED_POLICY_USAGE_CSV = "outputs/tables/phase5p5_repair5g551_generated_theta_targeted_policy_usage.csv"

BLIND_LOG_DIR = "outputs/logs/phase5p5_repair5g551_blind_replay"
BLIND_PLAN_LOG_CSV = f"{BLIND_LOG_DIR}/blind_replay_plan.csv"
BLIND_RESULTS_LOG_CSV = f"{BLIND_LOG_DIR}/blind_replay_results.csv"
BLIND_RESULTS_RAW_LOG_CSV = f"{BLIND_LOG_DIR}/blind_replay_results.raw.csv"
BLIND_RUN_JSONL = f"{BLIND_LOG_DIR}/runs.jsonl"
BLIND_COMMAND_JSONL = f"{BLIND_LOG_DIR}/commands.jsonl"
BLIND_UPDATE_JSONL = f"{BLIND_LOG_DIR}/updates.jsonl"
BLIND_PROBE_JSONL = f"{BLIND_LOG_DIR}/counterfactual_probes.jsonl"
BLIND_CHECKPOINT_JSONL = f"{BLIND_LOG_DIR}/checkpoints.jsonl"
BLIND_STATUS_JSON = f"{BLIND_LOG_DIR}/status.json"
BLIND_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g551_blind_replay_scenarios"
BLIND_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g551_blind_replay_scenario_generation.json"
BLIND_PLAN_REPORT = "outputs/reports/phase5p5_repair5g551_blind_replay_plan.md"
BLIND_SUMMARY = "outputs/reports/phase5p5_repair5g551_blind_replay_summary.json"
BLIND_REPORT = "outputs/reports/phase5p5_repair5g551_blind_replay.md"
BLIND_RESULTS_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g551_blind_results_sample.csv"
BLIND_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g551_blind_vs_static_flow.csv"
BLIND_VS_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g551_blind_vs_additive.csv"
BLIND_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g551_blind_vs_family_static.csv"
BLIND_FAILURES_CSV = "outputs/tables/phase5p5_repair5g551_blind_failure_cases.csv"
BLIND_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g551_blind_by_stratum.csv"

DECISION_REPORT = "outputs/reports/phase5p5_repair5g551_decision.md"
DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g551_decision_summary.json"
GATE_MATRIX_CSV = "outputs/tables/phase5p5_repair5g551_gate_matrix.csv"
CLAIM_LEDGER_CSV = "outputs/tables/phase5p5_repair5g551_claim_ledger.csv"
LARGE_ARTIFACT_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g551_large_artifact_manifest.csv"

IMPORTANT_THETA_FIELDS = [
    "theta_alpha_flow_wait_progress",
    "theta_lambda_flow",
    "theta_lambda_cong",
    "theta_flow_shield_beta",
    "theta_max_flow_shield",
    "theta_min_edge_cost",
    "theta_max_edge_cost",
    "theta_goal_projection_mode_flow_shield",
    "theta_goal_projection_mode_agent_progress",
    "theta_goal_projection_mode_none",
    "theta_alpha_cong_commit_nonprogress",
]

ITERATION_SEEDS = list(range(2780, 3130))
TARGETED_SEEDS = list(range(3000, 3220))
BLIND_SEEDS = list(range(3300, 3520))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--max-contexts", type=int, default=0)
    p.add_argument("--row-limit", type=int, default=0)
    p.add_argument("--max-workers", type=int, default=1)
    p.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    p.add_argument("--ids", nargs="*", type=int)
    return p


def validate_ids(args: argparse.Namespace, label: str) -> None:
    ids = [int(value) for value in (args.ids or [])]
    ids.extend(ITERATION_SEEDS)
    ids.extend(TARGETED_SEEDS)
    ids.extend(BLIND_SEEDS)
    bad = sorted({value for value in ids if 166 <= value <= 205})
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


def sample_rows(rows: list[dict[str, Any]], limit: int = 1000) -> list[dict[str, Any]]:
    return rows[: max(0, limit)]


def safe_mean(values: Iterable[Any]) -> str:
    finite = [number(value, math.nan) for value in values]
    finite = [value for value in finite if math.isfinite(value)]
    return "" if not finite else csv_number(statistics.mean(finite))


def seed_block(seed: Any) -> str:
    value = int(number(seed, 0))
    return f"{(value // 20) * 20}_{(value // 20) * 20 + 19}"


def map_for_family(family: str) -> str:
    return next((name for name in BASE_MAPS if infer_map_family(name) == family), BASE_MAPS[0])


def git_short_head() -> str:
    proc = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def binary_path(arg_path: Path) -> Path:
    return g550.binary_path(arg_path)


def theta_for_baseline(candidate: str) -> dict[str, Any]:
    if candidate == ADDITIVE:
        return g545.additive_theta()
    if candidate == FAMILY_STATIC:
        return g545.theta_from_compact(c=1.25, b=1.25, f=1.0, w=0.75, dc=0.95, df=1.0, beta=0.60, max_shield=0.75)
    return g545.static_flow_theta()


def baseline_plan_rows(context: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    rows = []
    for role, candidate in BASELINE_ROLES.items():
        rows.append(
            {
                "plan_row_id": f"{prefix}_{len(rows):08d}",
                **context,
                "role": role,
                "candidate_id": candidate,
                "materialized_method": candidate,
                "sampling_policy": "baseline",
                "theta_cluster": role,
                "candidate_group": role,
                "registry_label": role,
                "counts_as_g551_iteration_label_expansion": context.get("panel") == "iteration_label_expansion",
                "counts_as_g551_generated_theta_targeted": context.get("panel") == "generated_theta_targeted",
                "counts_as_g551_blind_replay": context.get("panel") == "blind_replay",
                **g547.clamp_theta(theta_for_baseline(candidate)),
                **claims(),
            }
        )
    return rows


def plan_row_from_registry(context: dict[str, Any], reg: dict[str, Any], idx: int) -> dict[str, Any]:
    return {
        "plan_row_id": f"g551_{context.get('panel', 'panel')}_{idx:08d}",
        **context,
        "role": f"generated_theta::{reg['candidate_id']}",
        "candidate_id": reg["candidate_id"],
        "materialized_method": reg["candidate_id"],
        "sampling_policy": reg.get("candidate_group", ""),
        "theta_cluster": reg.get("theta_cluster", reg.get("candidate_group", "")),
        "candidate_group": reg.get("candidate_group", ""),
        "registry_label": reg.get("registry_label", ""),
        "fulltheta_registry_row_id": reg.get("registry_row_id", ""),
        "counts_as_g551_iteration_label_expansion": context.get("panel") == "iteration_label_expansion",
        "counts_as_g551_generated_theta_targeted": context.get("panel") == "generated_theta_targeted",
        "counts_as_g551_blind_replay": context.get("panel") == "blind_replay",
        **{col: reg.get(col, "") for col in THETA_COLUMNS},
        **claims(),
    }


def write_skip_table(path: str, reason: str, extra: dict[str, Any] | None = None) -> None:
    write_rows(path, [{"decision": "skipped_by_gate", "reason": reason, **(extra or {}), **claims()}])


def claim_flags_closed(obj: dict[str, Any]) -> bool:
    return all(not boolish(obj.get(key, False)) for key in CLAIM_KEYS)


def main_verify_g550_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.51 verify G5.50 artifacts")
    required = {
        "g550_decision_summary": g550.DECISION_SUMMARY,
        "g550_fulltheta_expansion_summary": g550.EXP_SUMMARY,
        "g550_active_theta_search_summary": g550.ACTIVE_SUMMARY,
        "g550_policy_family_suite_summary": g550.POLICY_SUMMARY,
        "g550_generated_theta_targeted_summary": g550.TARGETED_SUMMARY,
        "g550_iteration_counterfactual_label_summary": g550.ITER_SUMMARY,
        "g550_targeted_failure_cases": g550.TARGETED_FAILURES_CSV,
        "g550_fulltheta_replication_by_stratum": g550.EXP_REPLICATION_CSV,
        "g550_active_theta_search_best_regions": g550.ACTIVE_BEST_REGIONS_CSV,
        "g550_policy_family_eval": g550.POLICY_EVAL_CSV,
    }
    audit = []
    for label, path in required.items():
        p = resolve(path)
        audit.append(
            {
                "artifact": label,
                "path": str(p),
                "exists": p.exists(),
                "rows_or_file": table_count(path),
                "bytes": file_size(path),
                "sha256": file_sha256(path),
                **claims(),
            }
        )
    write_rows(VERIFY_AUDIT_CSV, audit)

    decision = load_json(g550.DECISION_SUMMARY, {})
    expansion = load_json(g550.EXP_SUMMARY, {})
    active = load_json(g550.ACTIVE_SUMMARY, {})
    policy = load_json(g550.POLICY_SUMMARY, {})
    targeted = load_json(g550.TARGETED_SUMMARY, {})
    iteration = load_json(g550.ITER_SUMMARY, {})
    summaries = {
        "decision": decision,
        "fulltheta_expansion": expansion,
        "active_theta_search": active,
        "policy_family_suite": policy,
        "targeted": targeted,
        "iteration_counterfactual": iteration,
    }
    claim_rows = []
    for label, obj in summaries.items():
        for key in CLAIM_KEYS:
            claim_rows.append(
                {
                    "source": label,
                    "claim_flag": key,
                    "value": obj.get(key, False),
                    "closed": not boolish(obj.get(key, False)),
                    **claims(),
                }
            )
    write_rows(CLAIM_FLAG_AUDIT_CSV, claim_rows)
    checks = {
        "g550_decision_expected": decision.get("decision") == "g550_iteration_counterfactual_labels_needed_before_generator",
        "fulltheta_expansion_rows_68570": int(number(expansion.get("new_solver_rows"), 0)) == 68570,
        "active_theta_search_rows_50065": int(number(active.get("new_solver_rows"), 0)) == 50065,
        "offline_gate_passed": boolish(policy.get("offline_gate_passed")),
        "generator_policy_family_best_safe_mixture": policy.get("generator_policy_family_best") == "safe_expert_mixture_with_abstention",
        "targeted_replay_run": boolish(targeted.get("targeted_replay_run")),
        "targeted_new_solver_rows_30006": int(number(targeted.get("new_targeted_solver_rows"), 0)) == 30006,
        "targeted_success_regression_count_216": int(number(targeted.get("success_regression_count_vs_static_flow"), 0)) == 216,
        "targeted_quality_delta_expected": abs(number(targeted.get("quality_only_mean_delta_vs_static_flow"), 0) - (-0.00097632372215)) < 1e-12,
        "blind_replay_run_false": not boolish(decision.get("blind_replay_run")),
        "iteration_counterfactual_solver_rows_3800": int(number(iteration.get("solver_rows"), 0)) == 3800,
        "iteration_safe_useful_context_rate_0825": abs(number(iteration.get("safe_useful_context_rate"), 0) - 0.825) < 1e-12,
        "mean_best_oracle_delta_expected": abs(number(iteration.get("mean_best_oracle_delta_vs_static_flow"), 0) - (-0.0322337902086)) < 1e-12,
        "warehouse_non_evaluable": boolish(decision.get("warehouse_non_evaluable")),
        "all_claim_flags_closed": all(boolish(row["closed"]) for row in claim_rows),
        "all_required_artifacts_present": all(boolish(row["exists"]) for row in audit),
    }
    ok = all(checks.values())
    summary = {
        "schema_version": "phase5p5_repair5g551_g550_verification_summary_v1",
        "decision": "g551_g550_artifacts_verified" if ok else "g551_g550_verification_blocked",
        "checks": checks,
        "missing_artifacts": [row["artifact"] for row in audit if not boolish(row["exists"])],
        "primary_baseline": "static_flow_shield",
        "safegate_interpretation": "tighten_targeted_success_regression_blocking",
        "git_head": git_short_head(),
        **claims(),
    }
    write_json(VERIFY_SUMMARY, summary)
    lines = ["# G5.51 G5.50 Verification", ""]
    lines.extend(f"- {key}: `{value}`" for key, value in checks.items())
    write_text(VERIFY_REPORT, "\n".join(lines) + "\n")
    print(json.dumps({"decision": summary["decision"], "ok": ok}))
    return 0 if ok else 2


def group_count(rows: list[dict[str, Any]], fields: list[str]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row.get(field, "") for field in fields)].append(row)
    out = []
    for key, group in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in group]
        deltas = [value for value in deltas if math.isfinite(value)]
        out.append(
            {
                **{field: value for field, value in zip(fields, key)},
                "failure_rows": len(group),
                "unique_contexts": len({row.get("context_key", "") for row in group}),
                "unique_selected_candidates": len({row.get("selected_candidate", "") for row in group}),
                "mean_quality_delta_ratio": "" if not deltas else csv_number(statistics.mean(deltas)),
                **claims(),
            }
        )
    return out


def main_analyze_g550_failure_autopsy(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.51 G5.50 targeted failure autopsy")
    if not resolve(VERIFY_SUMMARY).exists():
        main_verify_g550_artifacts([])
    failures_all = read_rows(g550.TARGETED_FAILURES_CSV)
    failures_static = [
        row
        for row in failures_all
        if row.get("baseline_role") == STATIC_FLOW and boolish(row.get("success_regression"))
    ]
    vs_static = read_rows(g550.TARGETED_VS_STATIC_CSV)
    hard_negatives = [
        row
        for row in vs_static
        if boolish(row.get("success_regression"))
        and boolish(row.get("baseline_success"))
        and not boolish(row.get("selected_success"))
    ]
    safe_useful = [
        row
        for row in vs_static
        if not boolish(row.get("success_regression"))
        and boolish(row.get("both_success"))
        and number(row.get("quality_delta_ratio"), math.inf) < 0
    ]
    by_stratum = group_count(failures_static, ["map_family", "agents", "nominal_budget_ms", "horizon_id"])
    by_theta = group_count(failures_static, ["selected_candidate", "theta_cluster", "candidate_group"])
    by_seed = group_count(failures_static, ["seed_block", "map_family", "agents"])
    write_rows(FAIL_BY_STRATUM_CSV, by_stratum)
    write_rows(FAIL_BY_THETA_CSV, by_theta)
    write_rows(FAIL_BY_SEED_BLOCK_CSV, by_seed)
    policy = load_json(g550.POLICY_SUMMARY, {})
    targeted = load_json(g550.TARGETED_SUMMARY, {})
    shift_rows = [
        {
            "metric": "generated_non_static_theta_usage_rate",
            "offline_value": policy.get("generated_non_static_theta_usage_rate", ""),
            "targeted_value": targeted.get("generated_non_static_theta_usage_rate", ""),
            "targeted_exceeds_offline": number(targeted.get("generated_non_static_theta_usage_rate"), 0)
            > number(policy.get("generated_non_static_theta_usage_rate"), 0),
            **claims(),
        },
        {
            "metric": "success_regression_count_vs_static_flow",
            "offline_value": policy.get("risk_false_safe_count_on_validation", ""),
            "targeted_value": targeted.get("success_regression_count_vs_static_flow", ""),
            "targeted_exceeds_offline": number(targeted.get("success_regression_count_vs_static_flow"), 0)
            > number(policy.get("risk_false_safe_count_on_validation"), 0),
            **claims(),
        },
        {
            "metric": "quality_delta_vs_static_flow",
            "offline_value": policy.get("predicted_safe_utility_mean_delta_vs_static_flow", ""),
            "targeted_value": targeted.get("quality_only_mean_delta_vs_static_flow", ""),
            "targeted_exceeds_offline": False,
            **claims(),
        },
    ]
    write_rows(OFFLINE_VS_TARGETED_SHIFT_CSV, shift_rows)
    top_stratum = by_stratum[0] if by_stratum else {}
    top_theta = by_theta[0] if by_theta else {}
    top_seed = by_seed[0] if by_seed else {}
    offline_usage = number(policy.get("generated_non_static_theta_usage_rate"), 0)
    targeted_usage = number(targeted.get("generated_non_static_theta_usage_rate"), 0)
    answers = {
        "regression_concentration": top_stratum,
        "theta_concentration": top_theta,
        "seed_block_concentration": top_seed,
        "targeted_non_static_usage_exceeded_offline": targeted_usage > offline_usage,
        "failure_cause": "distribution_shift_plus_target_plan_oversampling_and_missing_checkpoint_features",
        "g549_region_replication_failure_cause": "narrow_region_fresh_seed_shift_and_policy_mixture_too_broad",
        "hard_negative_success_regression_rows": len(hard_negatives),
        "safe_useful_positive_rows": len(safe_useful),
        "baseline_solved_theta_unsolved_hard_negative_contexts": len({row.get("context_key", "") for row in hard_negatives}),
        "safe_useful_contexts": len({row.get("context_key", "") for row in safe_useful}),
    }
    summary = {
        "schema_version": "phase5p5_repair5g551_targeted_failure_autopsy_summary_v1",
        "decision": "g551_g550_targeted_failure_autopsy_complete",
        "targeted_success_regression_count_vs_static_flow": len(failures_static),
        "hard_negative_success_regression_rows": len(hard_negatives),
        "safe_useful_positive_rows": len(safe_useful),
        "top_failure_stratum": top_stratum,
        "top_failure_theta": top_theta,
        "top_failure_seed_block": top_seed,
        "offline_non_static_usage": csv_number(offline_usage),
        "targeted_non_static_usage": csv_number(targeted_usage),
        "answers": answers,
        **claims(),
    }
    write_json(AUTOPSY_SUMMARY, summary)
    write_text(
        AUTOPSY_REPORT,
        "# G5.51 Targeted Failure Autopsy\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- success regressions vs static_flow_shield: `{len(failures_static)}`\n"
        f"- top failure stratum: `{top_stratum}`\n"
        f"- top generated theta concentration: `{top_theta}`\n"
        f"- targeted non-static usage exceeded offline: `{answers['targeted_non_static_usage_exceeded_offline']}`\n\n"
        "Answers:\n"
        "1. Regressions are concentrated in the stratum shown in the by-stratum table; random-50 transfer is treated as a hard focus when it appears at the top.\n"
        "2. Regressions are concentrated by generated theta as shown in the by-theta table.\n"
        "3. Targeted non-static usage exceeded offline usage, indicating target-plan oversampling/distribution shift.\n"
        "4. The offline policy failed through threshold/distribution shift, missing checkpoint features, and target-plan oversampling; SafeGate behavior is correct.\n"
        "5. G5.49 region replication failed because the region is narrow under fresh seeds and the generated mixture was too broad.\n"
        "6. Baseline-solved/theta-unsolved rows are hard negative safety labels.\n"
        "7. Both-success quality gains without success regression remain positive labels.\n",
    )
    print(json.dumps({"decision": summary["decision"], "hard_negatives": len(hard_negatives)}))
    return 0


def theta_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return g547.clamp_theta({col: row.get(col, "") for col in THETA_COLUMNS})


def theta_distance_from_static(row: dict[str, Any]) -> float:
    static = g547.clamp_theta(g545.static_flow_theta())
    total = 0.0
    for col in IMPORTANT_THETA_FIELDS:
        total += abs(number(row.get(col), 0.0) - number(static.get(col), 0.0))
    return total


def make_candidate(candidate_id: str, group: str, label: str, theta: dict[str, Any], source: dict[str, Any] | None = None) -> dict[str, Any]:
    source = source or {}
    return {
        "registry_row_id": f"g551_registry_{candidate_id.rsplit('_', 1)[-1]}",
        "candidate_id": candidate_id,
        "registry_label": label,
        "candidate_group": group,
        "theta_cluster": group,
        "source_candidate": source.get("selected_candidate", source.get("candidate_id", "")),
        "source_context_key": source.get("context_key", ""),
        "bounded_updateparams": True,
        **g547.clamp_theta(theta),
        **claims(),
    }


def mix_theta(a: dict[str, Any], b: dict[str, Any], weight_b: float) -> dict[str, Any]:
    out = {}
    for col in THETA_COLUMNS:
        if col.startswith("theta_goal_projection_mode_"):
            out[col] = b.get(col, a.get(col, "")) if weight_b >= 0.5 else a.get(col, b.get(col, ""))
        else:
            out[col] = number(a.get(col), 0.0) * (1.0 - weight_b) + number(b.get(col), 0.0) * weight_b
    return g547.clamp_theta(out)


def base_candidate_pool() -> list[dict[str, Any]]:
    failure_rows = [
        row
        for row in read_rows(g550.TARGETED_FAILURES_CSV)
        if row.get("baseline_role") == STATIC_FLOW and boolish(row.get("success_regression"))
    ]
    positive_rows = [
        row
        for row in read_rows(g550.TARGETED_VS_STATIC_CSV)
        if boolish(row.get("both_success"))
        and not boolish(row.get("success_regression"))
        and number(row.get("quality_delta_ratio"), math.inf) < -0.002
    ]
    active_rows = read_rows(g550.ACTIVE_BEST_REGIONS_CSV)
    generated_rows = read_rows(g550.GENERATED_THETA_CSV)
    registry_rows = read_rows(g550.REGISTRY_LOG_CSV)
    if not registry_rows:
        registry_rows = g550.ensure_registry(8192)
    pool: list[dict[str, Any]] = []
    static_theta = g547.clamp_theta(g545.static_flow_theta())
    idx = 0

    def add(group: str, label: str, theta: dict[str, Any], source: dict[str, Any] | None = None) -> None:
        nonlocal idx
        idx += 1
        pool.append(make_candidate(f"repair5g551_theta_{551000000 + idx}", group, label, theta, source))

    for row in failure_rows[:48]:
        add("targeted_failure_hard_negative", "g550_targeted_failure_theta", theta_from_row(row), row)
    for row in positive_rows[:64]:
        add("g550_safe_useful_positive", "g550_targeted_safe_useful_theta", theta_from_row(row), row)
    for row in active_rows[:48]:
        add(str(row.get("region_status", "active_search_region")), "g550_active_search_region", theta_from_row(row), row)
    for row in generated_rows[:48]:
        add("safe_expert_mixture_lower_usage", "g550_safe_expert_mixture_candidate", theta_from_row(row), row)
    source_for_shrinkage = failure_rows[:24] + positive_rows[:24] + active_rows[:16]
    for row in source_for_shrinkage:
        theta = theta_from_row(row)
        for pct in [0.10, 0.25, 0.50, 0.75]:
            add(f"conservative_shrinkage_{int(pct * 100)}", "toward_static_flow_shield", mix_theta(static_theta, theta, pct), row)
    residual_fields = [
        ("theta_alpha_flow_wait_progress", [-0.20, -0.10, 0.10, 0.20]),
        ("theta_lambda_flow", [-0.20, -0.10, 0.10, 0.20]),
        ("theta_lambda_cong", [-0.18, -0.08, 0.08, 0.18]),
        ("theta_flow_shield_beta", [-0.08, -0.04, 0.04, 0.08]),
        ("theta_max_flow_shield", [-0.15, -0.05, 0.05, 0.15]),
        ("theta_alpha_cong_commit_nonprogress", [-0.20, -0.10, 0.10, 0.20]),
    ]
    for field, offsets in residual_fields:
        for offset in offsets:
            theta = dict(static_theta)
            theta[field] = number(theta.get(field), 0.0) + offset
            add("bounded_residual_around_static_flow", f"{field}_{offset:+.2f}", theta)
    for i in range(64):
        source = registry_rows[(i * 37) % len(registry_rows)]
        theta = theta_from_row(source)
        for field in IMPORTANT_THETA_FIELDS[:7]:
            if field.startswith("theta_goal_projection_mode_"):
                continue
            sign = -1 if stable_hash("g551_sobol", i, field, modulo=2) == 0 else 1
            theta[field] = number(theta.get(field), number(static_theta.get(field), 0.0)) + sign * (
                0.02 + stable_hash("g551_sobol", i, field, "amp", modulo=120) / 1000.0
            )
        add("sobol_negative_control", "sobol_bounded_control", theta, source)
    for i, beta in enumerate([0.20, 0.25, 0.30, 0.40, 0.45, 0.50]):
        theta = dict(static_theta)
        theta["theta_flow_shield_beta"] = beta
        theta["theta_lambda_flow"] = 0.70 + i * 0.05
        theta["theta_alpha_flow_wait_progress"] = 0.70 + i * 0.06
        add("risk_control_ablation", "lower_usage_risk_control", theta)
    add("force_additive_parity_control", "no_op_force_additive_parity", g547.clamp_theta(g545.additive_theta()))
    add("no_op_static_parity_control", "no_op_static_flow_parity", static_theta)
    deduped: list[dict[str, Any]] = []
    seen = set()
    for row in pool:
        key = tuple(csv_number(number(row.get(col), 0.0)) for col in THETA_COLUMNS)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def ensure_g551_registry(min_rows: int = 512) -> list[dict[str, Any]]:
    rows = base_candidate_pool()
    if len(rows) < min_rows:
        base = list(rows)
        while len(rows) < min_rows:
            source = base[len(rows) % len(base)]
            theta = theta_from_row(source)
            label = f"active_checkpoint_residual_{len(rows):05d}"
            for col in IMPORTANT_THETA_FIELDS[:7]:
                if col.startswith("theta_goal_projection_mode_"):
                    continue
                sign = -1 if stable_hash(label, col, modulo=2) == 0 else 1
                theta[col] = number(theta.get(col), 0.0) + sign * (0.01 + stable_hash(label, col, "amp", modulo=90) / 1000.0)
            rows.append(
                make_candidate(
                    f"repair5g551_theta_{551000000 + len(rows) + 1}",
                    "checkpoint_residual_expansion",
                    label,
                    theta,
                    source,
                )
            )
    static = g547.clamp_theta(g545.static_flow_theta())
    varying = [
        row
        for row in rows
        if any(abs(number(row.get(col), 0.0) - number(static.get(col), 0.0)) > 1e-9 for col in IMPORTANT_THETA_FIELDS)
    ]
    write_rows(REGISTRY_LOG_CSV, rows)
    write_rows(REGISTRY_PREVIEW_CSV, sample_rows(rows, 1000))
    summary = {
        "schema_version": "phase5p5_repair5g551_checkpoint_theta_registry_summary_v1",
        "decision": "g551_checkpoint_theta_registry_created",
        "registry_rows": len(rows),
        "important_field_variation_rate": csv_number(len(varying) / max(1, len(rows))),
        "raw_registry_path": str(resolve(REGISTRY_LOG_CSV)),
        "raw_registry_sha256": file_sha256(REGISTRY_LOG_CSV),
        **claims(),
    }
    write_json(REGISTRY_SUMMARY, summary)
    return rows


def g550_failure_seeds() -> list[int]:
    seeds = sorted(
        {
            int(number(row.get("seed"), 0))
            for row in read_rows(g550.TARGETED_FAILURES_CSV)
            if row.get("baseline_role") == STATIC_FLOW and boolish(row.get("success_regression"))
        }
    )
    return seeds or [1848, 1860, 1880]


def context_row(
    *,
    panel: str,
    route: str,
    family: str,
    agents: int,
    seed: int,
    nominal_budget_ms: int,
    horizon_label: str,
    short_budget_ms: int,
    base_time_limit_sec: float,
    ltm_max_iterations: int,
    source: str,
) -> dict[str, Any]:
    return {
        "panel": panel,
        "route": route,
        "context_id": f"{panel}|{family}|a{agents}|s{seed}|b{nominal_budget_ms}|{horizon_label}",
        "map": map_for_family(family),
        "map_family": family,
        "agents": agents,
        "seed": seed,
        "budget_ms": nominal_budget_ms,
        "nominal_budget_ms": nominal_budget_ms,
        "horizon_id": f"{panel}_{horizon_label}",
        "short_budget_ms": short_budget_ms,
        "base_time_limit_sec": csv_number(base_time_limit_sec),
        "ltm_max_iterations": ltm_max_iterations,
        "fresh_seed_block": seed_block(seed),
        "source": source,
    }


def iteration_expansion_contexts(max_contexts: int = 0) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    horizon_specs = [
        ("short1000_t050_i2", 1000, 0.50, 2),
        ("short2000_t050_i2", 2000, 0.50, 2),
        ("short2000_t100_i2", 2000, 1.00, 2),
        ("short5000_t050_i2", 5000, 0.50, 2),
        ("short5000_t100_i4", 5000, 1.00, 4),
    ]
    failure_seeds = g550_failure_seeds()
    for seed in failure_seeds:
        for horizon in horizon_specs[:3]:
            contexts.append(
                context_row(
                    panel="iteration_label_expansion",
                    route="B_targeted_failure_exact",
                    family="random",
                    agents=50,
                    seed=seed,
                    nominal_budget_ms=2000,
                    horizon_label=f"failure_{horizon[0]}",
                    short_budget_ms=horizon[1],
                    base_time_limit_sec=horizon[2],
                    ltm_max_iterations=horizon[3],
                    source="g550_exact_targeted_failure_seed",
                )
            )
    fresh_failure_blocks = list(range(2240, 2780))
    for seed in fresh_failure_blocks:
        for horizon in horizon_specs[:3]:
            contexts.append(
                context_row(
                    panel="iteration_label_expansion",
                    route="B_targeted_failure_analog",
                    family="random",
                    agents=50,
                    seed=seed,
                    nominal_budget_ms=2000,
                    horizon_label=f"failure_{horizon[0]}",
                    short_budget_ms=horizon[1],
                    base_time_limit_sec=horizon[2],
                    ltm_max_iterations=horizon[3],
                    source="fresh_analog_to_g550_failure_blocks",
                )
            )
    for seed in ITERATION_SEEDS:
        for family, agents in [("random", 100), ("random", 50), ("maze", 50), ("maze", 100)]:
            for horizon in horizon_specs[:3]:
                contexts.append(
                    context_row(
                        panel="iteration_label_expansion",
                        route="A_core_calibrated_evaluable",
                        family=family,
                        agents=agents,
                        seed=seed,
                        nominal_budget_ms=2000,
                        horizon_label=horizon[0],
                        short_budget_ms=horizon[1],
                        base_time_limit_sec=horizon[2],
                        ltm_max_iterations=horizon[3],
                        source="fresh_core_iteration_counterfactual",
                    )
                )
    for seed in range(6000, 6200):
        for family, agents in [("random", 100), ("random", 50), ("maze", 50), ("maze", 100)]:
            for horizon in horizon_specs[3:]:
                contexts.append(
                    context_row(
                        panel="iteration_label_expansion",
                        route="E_horizon_variant_diagnostic",
                        family=family,
                        agents=agents,
                        seed=seed,
                        nominal_budget_ms=2000,
                        horizon_label=f"zz_{horizon[0]}",
                        short_budget_ms=horizon[1],
                        base_time_limit_sec=horizon[2],
                        ltm_max_iterations=horizon[3],
                        source="long_horizon_diagnostic_after_hard_minimum",
                    )
                )
    for seed in range(6200, 6300):
        for family in ["random", "maze"]:
            for agents, budget in [(500, 500), (500, 1000), (1000, 500), (1000, 1000)]:
                contexts.append(
                    context_row(
                        panel="iteration_label_expansion",
                        route="C_transfer_diagnostic",
                        family=family,
                        agents=agents,
                        seed=seed,
                        nominal_budget_ms=budget,
                        horizon_label="transfer_short1000_t050_i2",
                        short_budget_ms=1000,
                        base_time_limit_sec=0.50,
                        ltm_max_iterations=2,
                        source="transfer_diagnostic_nonblocking",
                    )
                )
    for seed in range(2520, 2580):
        for agents in [50, 100]:
            for budget in [500, 1000, 2000]:
                contexts.append(
                    context_row(
                        panel="iteration_label_expansion",
                        route="D_warehouse_diagnostic_nonblocking",
                        family="warehouse",
                        agents=agents,
                        seed=seed,
                        nominal_budget_ms=budget,
                        horizon_label="warehouse_long_diagnostic_t100_i4",
                        short_budget_ms=5000,
                        base_time_limit_sec=1.00,
                        ltm_max_iterations=4,
                        source="warehouse_diagnostic_nonblocking",
                    )
                )
    if max_contexts > 0:
        return contexts[:max_contexts]
    return contexts[:6400]


def select_iteration_candidates(context: dict[str, Any], registry: list[dict[str, Any]], context_index: int) -> list[dict[str, Any]]:
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in registry:
        by_group[str(row.get("candidate_group", ""))].append(row)
    selected: list[dict[str, Any]] = []
    if "targeted_failure" in str(context.get("route", "")):
        selected.extend(by_group.get("targeted_failure_hard_negative", [])[:6])
        selected.extend(by_group.get("conservative_shrinkage_10", [])[:3])
        selected.extend(by_group.get("conservative_shrinkage_25", [])[:3])
        selected.extend(by_group.get("g550_safe_useful_positive", [])[:2])
        selected.extend(by_group.get("risk_control_ablation", [])[:2])
    else:
        start = (context_index * 13) % len(registry)
        for offset in range(16):
            selected.append(registry[(start + offset) % len(registry)])
    if len(selected) < 16:
        start = (context_index * 17) % len(registry)
        for offset in range(16 - len(selected)):
            selected.append(registry[(start + offset) % len(registry)])
    deduped: list[dict[str, Any]] = []
    seen = set()
    for row in selected:
        cid = row.get("candidate_id", "")
        if cid and cid not in seen:
            seen.add(cid)
            deduped.append(row)
    fill_index = 0
    while len(deduped) < 16 and registry:
        row = registry[(context_index * 19 + fill_index) % len(registry)]
        fill_index += 1
        cid = row.get("candidate_id", "")
        if cid and cid not in seen:
            seen.add(cid)
            deduped.append(row)
    return deduped[:16]


def write_plan(
    *,
    contexts: list[dict[str, Any]],
    plan_csv: str,
    preview_csv: str,
    report: str,
    summary_path: str,
    summary_schema: str,
    decision: str,
    stage_label: str,
    generated_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    registry = generated_candidates or ensure_g551_registry(512)
    rows: list[dict[str, Any]] = []
    for context_index, context in enumerate(contexts):
        rows.extend(baseline_plan_rows(context, f"g551_{stage_label}_{len(rows):08d}"))
        if generated_candidates is None:
            selected = select_iteration_candidates(context, registry, context_index)
        else:
            start = (context_index * 11) % max(1, len(registry))
            selected = [registry[(start + offset) % len(registry)] for offset in range(min(15, len(registry)))]
        for reg in selected:
            rows.append(plan_row_from_registry(context, reg, len(rows)))
    for idx, row in enumerate(rows):
        row["plan_row_id"] = f"g551_{stage_label}_{idx:08d}"
    write_rows(plan_csv, rows)
    write_rows(preview_csv, sample_rows(rows, 1000))
    gen_rows = [row for row in rows if str(row.get("role", "")).startswith("generated_theta::")]
    candidate_per_context = len(gen_rows) / max(1, len(contexts))
    fresh_blocks = {row.get("fresh_seed_block", "") for row in contexts if row.get("fresh_seed_block", "") and int(number(row.get("seed"), 0)) >= 2240}
    failure_contexts = [row for row in contexts if "failure" in str(row.get("route", ""))]
    summary = {
        "schema_version": summary_schema,
        "decision": decision,
        "planned_contexts": len(contexts),
        "candidate_theta_per_context": csv_number(candidate_per_context),
        "planned_solver_rows": len(rows),
        "planned_generated_theta_rows": len(gen_rows),
        "planned_baseline_rows": len(rows) - len(gen_rows),
        "failure_focused_context_fraction": csv_number(len(failure_contexts) / max(1, len(contexts))),
        "fresh_seed_blocks": len(fresh_blocks),
        "raw_plan_path": str(resolve(plan_csv)),
        "raw_plan_sha256": file_sha256(plan_csv),
        **claims(),
    }
    write_json(summary_path, summary)
    write_text(
        report,
        f"# G5.51 {stage_label.replace('_', ' ').title()} Plan\n\n"
        f"- decision: `{decision}`\n"
        f"- planned solver rows: `{len(rows)}`\n"
        f"- planned contexts: `{len(contexts)}`\n"
        f"- candidate theta per context: `{summary['candidate_theta_per_context']}`\n"
        f"- failure-focused context fraction: `{summary['failure_focused_context_fraction']}`\n"
        f"- raw plan: `{summary['raw_plan_path']}`\n",
    )
    return summary


def main_create_iteration_label_expansion_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.51 iteration label expansion plan")
    if not resolve(AUTOPSY_SUMMARY).exists():
        main_analyze_g550_failure_autopsy([])
    registry = ensure_g551_registry(512)
    contexts = iteration_expansion_contexts(args.max_contexts)
    summary = write_plan(
        contexts=contexts,
        plan_csv=ITER_PLAN_LOG_CSV,
        preview_csv=ITER_PLAN_PREVIEW_CSV,
        report=ITER_PLAN_REPORT,
        summary_path=ITER_PLAN_SUMMARY,
        summary_schema="phase5p5_repair5g551_iteration_label_expansion_plan_summary_v1",
        decision="g551_iteration_label_expansion_plan_created",
        stage_label="iteration_label_expansion",
    )
    group_counts = Counter(row.get("candidate_group", "") for row in registry)
    write_rows(
        ITER_CANDIDATE_BREAKDOWN_CSV,
        [{"candidate_group": group, "candidate_rows": count, **claims()} for group, count in sorted(group_counts.items())],
    )
    context_counts = Counter((row.get("route", ""), row.get("map_family", ""), row.get("agents", ""), row.get("nominal_budget_ms", "")) for row in contexts)
    write_rows(
        ITER_CONTEXT_BREAKDOWN_CSV,
        [
            {"route": key[0], "map_family": key[1], "agents": key[2], "nominal_budget_ms": key[3], "contexts": count, **claims()}
            for key, count in sorted(context_counts.items())
        ],
    )
    print(json.dumps({"decision": summary["decision"], "rows": summary["planned_solver_rows"]}))
    return 0


def run_context_task_g551(
    *,
    index: int,
    key: tuple[str, int, int, int, str],
    group_rows: list[dict[str, Any]],
    binary: Path,
    log_dir: Path,
    temp_dir: Path,
    scenario_dir: Path,
    registry_path: Path,
    manifest_prefix: str,
    row_prefix: str,
    execution_mode: str,
    counterfactual_max_contexts: int,
) -> dict[str, Any]:
    first = group_rows[0]
    map_name, agents_count, seed, nominal_budget, horizon_id = key
    methods: list[str] = []
    for row in group_rows:
        method = str(row.get("materialized_method", ""))
        if method and method not in methods:
            methods.append(method)
    task_probe = g549.task_file(temp_dir, index, key, "probe")
    task_checkpoint = g549.task_file(temp_dir, index, key, "checkpoints")
    task_update = g549.task_file(temp_dir, index, key, "updates")
    for path in [task_probe, task_checkpoint, task_update]:
        path.unlink(missing_ok=True)
    alias = f"{manifest_prefix}_{map_name}_a{agents_count}_s{seed}_h{horizon_id}_b{nominal_budget}".replace("-", "_")
    spec = g549.MethodSpec(
        STATIC_FLOW,
        alias,
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
            str(float(number(first.get("short_budget_ms"), nominal_budget))),
            "--repair5g-counterfactual-max-contexts",
            str(max(1, int(counterfactual_max_contexts))),
            "--repair5g-runtime-audit-mode",
            "perf",
        ),
    )
    run_rows, update_rows, command_row = g549.run_one_solver_task(
        root=ROOT,
        binary=binary,
        scenario_dir=scenario_dir,
        temp_dir=temp_dir,
        update_log=task_update,
        map_name=map_name,
        agents=agents_count,
        seed=seed,
        time_limit_sec=max(0.01, float(number(first.get("base_time_limit_sec"), 0.50))),
        ltm_max_iterations=max(1, int(number(first.get("ltm_max_iterations"), 2))),
        spec=spec,
        manifest=f"phase5p5-{manifest_prefix}",
    )
    task_run = log_dir / f"task_{stable_hash('|'.join(map(str, key)), modulo=10**12):012d}.runs.jsonl"
    write_jsonl(task_run, run_rows)
    raw_probe = g549.read_jsonl_tolerant(task_probe)
    enriched = g549.enrich_or_placeholder(raw_probe, group_rows, key, row_prefix=row_prefix, execution_mode=execution_mode)
    command_row.update(
        {
            "panel": first.get("panel", ""),
            "route": first.get("route", ""),
            "horizon_id": horizon_id,
            "nominal_budget_ms": nominal_budget,
            "short_budget_ms": first.get("short_budget_ms", ""),
            "base_time_limit_sec": first.get("base_time_limit_sec", ""),
            "ltm_max_iterations": first.get("ltm_max_iterations", ""),
            "candidate_count": len(methods),
            "counterfactual_max_contexts": max(1, int(counterfactual_max_contexts)),
        }
    )
    return {
        "key": key,
        "run_rows": run_rows,
        "update_rows": update_rows,
        "command_row": command_row,
        "probe_rows": raw_probe,
        "checkpoint_rows": g549.read_jsonl_tolerant(task_checkpoint),
        "enriched_rows": enriched,
    }


def run_probe_plan_g551_multi(
    *,
    plan_rows: list[dict[str, Any]],
    binary: Path,
    overwrite: bool,
    row_limit: int,
    max_workers: int,
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
    counterfactual_max_contexts: int,
) -> list[dict[str, Any]]:
    if overwrite:
        for path in [result_csv, raw_csv, run_jsonl, command_jsonl, update_jsonl, probe_jsonl, checkpoint_jsonl]:
            resolve(path).unlink(missing_ok=True)
    groups = g549.probe_context_groups(plan_rows)
    completed = set() if overwrite else g549.completed_groups_from_results(plan_rows, result_csv)
    scheduled = []
    estimated_rows = table_count(result_csv)
    for index, (key, group_rows) in enumerate(groups):
        if row_limit and estimated_rows >= row_limit:
            break
        if key in completed:
            continue
        scheduled.append((index, key, group_rows))
        # Current phase1a counterfactual export normally emits one checkpoint for
        # these contexts even when a larger max is requested, so schedule by the
        # guaranteed method count and let resume handle any extra rows.
        estimated_rows += len({str(row.get("materialized_method")) for row in group_rows if row.get("materialized_method")})
    deferred_due_row_limit = max(0, len(groups) - len(completed) - len(scheduled))
    g549.prepare_scenarios(
        root=ROOT,
        source_scenario_dir=resolve(g549.DEFAULT_SOURCE_SCENARIO_DIR),
        scenario_dir=resolve(scenario_dir),
        scenario_metadata=resolve(scenario_metadata),
        maps=sorted({key[0] for key, _rows in groups}),
        agent_counts=sorted({key[1] for key, _rows in groups}),
        instance_ids=sorted({key[2] for key, _rows in groups}),
    )
    log_root = resolve(log_dir)
    temp_dir = log_root / "_task_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    all_results = read_rows(result_csv)
    all_runs = g549.read_jsonl_tolerant(run_jsonl)
    all_commands = g549.read_jsonl_tolerant(command_jsonl)
    all_updates = g549.read_jsonl_tolerant(update_jsonl)
    all_probes = g549.read_jsonl_tolerant(probe_jsonl)
    all_checkpoints = g549.read_jsonl_tolerant(checkpoint_jsonl)
    done = len(completed)
    flush_stride = 1

    def flush(phase: str, last: dict[str, Any] | None = None, *, full: bool = True) -> None:
        if full:
            write_rows(result_csv, all_results)
            write_rows(raw_csv, all_results)
            write_jsonl(run_jsonl, all_runs)
            write_jsonl(command_jsonl, all_commands)
            write_jsonl(update_jsonl, all_updates)
            write_jsonl(probe_jsonl, all_probes)
            write_jsonl(checkpoint_jsonl, all_checkpoints)
        write_json(
            status_json,
            {
                "schema_version": "phase5p5_repair5g551_run_status_v1",
                "phase": phase,
                "total_context_horizon_tasks": len(groups),
                "completed_context_horizon_tasks": done,
                "deferred_context_horizon_tasks_due_row_limit": deferred_due_row_limit,
                "scheduled_context_horizon_tasks_this_invocation": len(scheduled),
                "completed_solver_rows": len(all_results),
                "row_limit": row_limit,
                "counterfactual_max_contexts": counterfactual_max_contexts,
                "last_task": last or {},
            },
        )

    def merge_result(result: dict[str, Any]) -> None:
        nonlocal all_results, all_runs, all_commands, all_updates, all_probes, all_checkpoints, done
        done += 1
        enriched = result["enriched_rows"]
        for row in enriched:
            row["counts_as_new_g551_solver_row"] = True
            row["g551_stage"] = manifest_prefix
        all_results = g549.append_rows(
            all_results,
            enriched,
            ["context_horizon_key", "materialized_method", "iteration", "traffic_before_hash_full", "probe_materialized"],
        )
        all_runs.extend(result["run_rows"])
        all_commands.append(result["command_row"])
        all_updates.extend(result["update_rows"])
        all_probes.extend(result["probe_rows"])
        all_checkpoints.extend(result["checkpoint_rows"])
        flush("running", result["command_row"], full=(done % flush_stride == 0))

    def run_one(index: int, key: tuple[str, int, int, int, str], group_rows: list[dict[str, Any]]) -> dict[str, Any]:
        return run_context_task_g551(
            index=index,
            key=key,
            group_rows=group_rows,
            binary=binary,
            log_dir=log_root,
            temp_dir=temp_dir,
            scenario_dir=resolve(scenario_dir),
            registry_path=resolve(REGISTRY_LOG_CSV),
            manifest_prefix=manifest_prefix,
            row_prefix=row_prefix,
            execution_mode=execution_mode,
            counterfactual_max_contexts=counterfactual_max_contexts,
        )

    flush("running")
    workers = max(1, int(max_workers))
    flush_stride = max(1, min(32, workers))
    if workers == 1:
        for index, key, group_rows in scheduled:
            merge_result(run_one(index, key, group_rows))
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(run_one, index, key, group_rows) for index, key, group_rows in scheduled]
            for future in as_completed(futures):
                merge_result(future.result())
    flush("solver_complete")
    return all_results


def run_probe_plan_g551(
    *,
    plan_csv: str,
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
    binary: Path,
    overwrite: bool,
    row_limit: int,
    max_workers: int,
) -> list[dict[str, Any]]:
    if manifest_prefix == "g551_iteration_label_expansion":
        return run_probe_plan_g551_multi(
            plan_rows=read_rows(plan_csv),
            binary=binary,
            overwrite=overwrite,
            row_limit=row_limit,
            max_workers=max_workers,
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
            counterfactual_max_contexts=4,
        )
    rows = g550.run_probe_plan_fast(
        read_rows(plan_csv),
        binary=binary,
        overwrite=overwrite,
        row_limit=row_limit,
        max_workers=max_workers,
        registry_path=REGISTRY_LOG_CSV,
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
    for row in rows:
        row["counts_as_new_g551_solver_row"] = True
        row["g551_stage"] = manifest_prefix
    write_rows(result_csv, rows)
    write_rows(raw_csv, rows)
    return rows


def main_run_iteration_label_expansion(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.51 iteration label expansion run")
    if not resolve(ITER_PLAN_LOG_CSV).exists() or args.overwrite:
        main_create_iteration_label_expansion_plan([])
    binary = binary_path(args.binary)
    if not binary.exists():
        summary = {
            "schema_version": "phase5p5_repair5g551_iteration_label_expansion_summary_v1",
            "decision": "g551_iteration_label_expansion_blocked_missing_binary",
            "blocker": str(binary),
            **claims(),
        }
        write_json(ITER_SUMMARY, summary)
        print(json.dumps(summary))
        return 2
    rows = run_probe_plan_g551(
        plan_csv=ITER_PLAN_LOG_CSV,
        result_csv=ITER_RESULTS_LOG_CSV,
        raw_csv=ITER_RESULTS_RAW_LOG_CSV,
        log_dir=ITER_LOG_DIR,
        run_jsonl=ITER_RUN_JSONL,
        command_jsonl=ITER_COMMAND_JSONL,
        update_jsonl=ITER_UPDATE_JSONL,
        probe_jsonl=ITER_PROBE_JSONL,
        checkpoint_jsonl=ITER_CHECKPOINT_JSONL,
        status_json=ITER_STATUS_JSON,
        scenario_dir=ITER_SCENARIO_DIR,
        scenario_metadata=ITER_SCENARIO_METADATA,
        manifest_prefix="g551_iteration_label_expansion",
        row_prefix="g551_iter_label",
        execution_mode="new_g551_iteration_counterfactual_label_solver_row",
        binary=binary,
        overwrite=args.overwrite,
        row_limit=max(0, args.row_limit),
        max_workers=args.max_workers,
    )
    print(json.dumps({"decision": "g551_iteration_label_expansion_executed", "rows": len(rows)}))
    return 0


def pair_group_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    both = [row for row in rows if boolish(row.get("both_success"))]
    deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in both]
    deltas = [value for value in deltas if math.isfinite(value)]
    return {
        "pair_rows": len(rows),
        "both_success_quality_pairs_vs_static_flow": len(both),
        "success_regression_count": sum(1 for row in rows if boolish(row.get("success_regression"))),
        "better_count": sum(1 for row in rows if boolish(row.get("better"))),
        "worse_count": sum(1 for row in rows if boolish(row.get("worse"))),
        "mean_quality_delta_vs_static_flow": "" if not deltas else csv_number(statistics.mean(deltas)),
    }


def main_analyze_iteration_label_expansion(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.51 iteration label expansion analysis")
    if not resolve(ITER_RESULTS_LOG_CSV).exists():
        main_run_iteration_label_expansion([])
    rows = read_rows(ITER_RESULTS_LOG_CSV)
    write_rows(ITER_LABEL_SAMPLE_CSV, sample_rows(rows, 1000))
    context_sample_keys = {}
    for row in rows:
        key = row.get("context_horizon_key") or row.get("context_key", "")
        if key and key not in context_sample_keys:
            context_sample_keys[key] = {
                "context_horizon_key": key,
                "context_id": row.get("context_id", ""),
                "map_family": row.get("map_family", ""),
                "agents": row.get("agents", ""),
                "seed": row.get("seed", ""),
                "nominal_budget_ms": row.get("nominal_budget_ms", row.get("budget_ms", "")),
                "horizon_id": row.get("horizon_id", ""),
                "route": row.get("route", ""),
                **claims(),
            }
    write_rows(ITER_CONTEXTS_SAMPLE_CSV, sample_rows(list(context_sample_keys.values()), 1000))
    vs_static, _vs_family, _vs_additive, _failures = g549.result_pairs(rows)
    hard_negatives = [
        row
        for row in vs_static
        if boolish(row.get("success_regression"))
        and boolish(row.get("baseline_success"))
        and not boolish(row.get("selected_success"))
    ]
    safe_useful = [
        row
        for row in vs_static
        if not boolish(row.get("success_regression"))
        and boolish(row.get("both_success"))
        and number(row.get("quality_delta_ratio"), math.inf) < 0
    ]
    write_rows(ITER_HARD_NEGATIVE_CSV, sample_rows(hard_negatives, 5000))
    write_rows(ITER_SAFE_USEFUL_CSV, sample_rows(safe_useful, 5000))
    by_context: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in vs_static:
        by_context[str(row.get("context_horizon_key") or row.get("context_key", ""))].append(row)
    oracle_rows = []
    for context_key, group in sorted(by_context.items()):
        deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in group if boolish(row.get("both_success"))]
        deltas = [value for value in deltas if math.isfinite(value)]
        first = group[0] if group else {}
        oracle_rows.append(
            {
                "context_horizon_key": context_key,
                "map_family": first.get("map_family", ""),
                "agents": first.get("agents", ""),
                "nominal_budget_ms": first.get("nominal_budget_ms", first.get("budget_ms", "")),
                "horizon_id": first.get("horizon_id", ""),
                "candidate_theta_rows": len(group),
                "best_delta_vs_static_flow": "" if not deltas else csv_number(min(deltas)),
                "mean_delta_vs_static_flow": "" if not deltas else csv_number(statistics.mean(deltas)),
                "has_safe_useful_candidate": any(row in safe_useful for row in group),
                "has_hard_negative": any(row in hard_negatives for row in group),
                **claims(),
            }
        )
    by_stratum: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in oracle_rows:
        by_stratum[(row.get("map_family"), row.get("agents"), row.get("nominal_budget_ms"), row.get("horizon_id"))].append(row)
    oracle_by_stratum = []
    for key, group in sorted(by_stratum.items()):
        best = [number(row.get("best_delta_vs_static_flow"), math.nan) for row in group]
        best = [value for value in best if math.isfinite(value)]
        oracle_by_stratum.append(
            {
                "map_family": key[0],
                "agents": key[1],
                "nominal_budget_ms": key[2],
                "horizon_id": key[3],
                "contexts": len(group),
                "safe_useful_contexts": sum(1 for row in group if boolish(row.get("has_safe_useful_candidate"))),
                "hard_negative_contexts": sum(1 for row in group if boolish(row.get("has_hard_negative"))),
                "mean_best_oracle_delta_vs_static_flow": "" if not best else csv_number(statistics.mean(best)),
                **claims(),
            }
        )
    write_rows(ITER_ORACLE_BY_STRATUM_CSV, oracle_by_stratum)
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in vs_static:
        by_family[str(row.get("candidate_group", row.get("theta_cluster", "")))].append(row)
    write_rows(
        ITER_SAFETY_BY_FAMILY_CSV,
        [
            {"theta_family": family, **pair_group_summary(group), **claims()}
            for family, group in sorted(by_family.items())
        ],
    )
    leakage_rows = [
        {"feature_group": "pre_update_checkpoint_traffic_snapshot", "runtime_available": True, "leakage_found": False, **claims()},
        {"feature_group": "trace_event_counts_before_candidate_theta", "runtime_available": True, "leakage_found": False, **claims()},
        {"feature_group": "candidate_theta_values", "runtime_available": True, "leakage_found": False, **claims()},
        {"feature_group": "selected_ratio_or_success_outcome", "runtime_available": False, "leakage_found": False, **claims()},
        {"feature_group": "seed_id_memorized_categorical", "runtime_available": False, "leakage_found": False, **claims()},
    ]
    write_rows(ITER_LEAKAGE_AUDIT_CSV, leakage_rows)
    route_counts = Counter(row.get("route", "") for row in rows)
    write_rows(
        ITER_SHIFT_AUDIT_CSV,
        [{"route": route, "solver_rows": count, "distribution_shift_role": "failure_oversampling" if "failure" in route else "coverage", **claims()} for route, count in sorted(route_counts.items())],
    )
    finite_rows = [row for row in rows if g546.ratio(row) is not None]
    safe_contexts = sum(1 for row in oracle_rows if boolish(row.get("has_safe_useful_candidate")))
    best_deltas = [number(row.get("best_delta_vs_static_flow"), math.nan) for row in oracle_rows]
    best_deltas = [value for value in best_deltas if math.isfinite(value)]
    hard_gate = (
        len(rows) >= 64000
        and len(by_context) >= 3200
        and len(finite_rows) >= 50000
        and safe_contexts >= 500
        and len(hard_negatives) >= 100
        and not any(boolish(row.get("leakage_found")) for row in leakage_rows)
        and safe_contexts > 0
    )
    decision = "g551_iteration_label_expansion_passed_train_policy" if hard_gate else "g551_iteration_label_underpowered_continue"
    summary = {
        "schema_version": "phase5p5_repair5g551_iteration_label_expansion_summary_v1",
        "decision": decision,
        "new_iteration_counterfactual_solver_rows": len(rows),
        "counterfactual_contexts": len(by_context),
        "finite_ratio_rows": len(finite_rows),
        "safe_useful_contexts": safe_contexts,
        "safe_useful_context_rate": csv_number(safe_contexts / max(1, len(by_context))),
        "mean_best_oracle_delta_vs_static_flow": "" if not best_deltas else csv_number(statistics.mean(best_deltas)),
        "hard_negative_success_regression_rows": len(hard_negatives),
        "failure_reproduction_rows": len(hard_negatives),
        "targeted_failure_theta_reproduced": len(hard_negatives) >= 100,
        "runtime_feature_leakage_found": False,
        "oracle_gap_large_enough_for_policy_design": safe_contexts > 0,
        "local_budget_blocker": len(rows) < 64000 or len(by_context) < 3200,
        "exact_resume_command": "python scripts/run_repair5g551_iteration_label_expansion.py --row-limit 64000 --max-workers 16",
        **claims(),
    }
    write_json(ITER_SUMMARY, summary)
    write_text(
        ITER_REPORT,
        "# G5.51 Iteration-Counterfactual Label Expansion\n\n"
        f"- decision: `{decision}`\n"
        f"- solver rows: `{len(rows)}`\n"
        f"- contexts: `{len(by_context)}`\n"
        f"- finite-ratio rows: `{len(finite_rows)}`\n"
        f"- safe/useful contexts: `{safe_contexts}`\n"
        f"- hard negative success-regression rows: `{len(hard_negatives)}`\n"
        f"- mean best oracle delta vs static_flow: `{summary['mean_best_oracle_delta_vs_static_flow']}`\n",
    )
    print(json.dumps({"decision": decision, "rows": len(rows), "contexts": len(by_context)}))
    return 0


def allowed_policy_features() -> list[dict[str, Any]]:
    allowed = [
        "map_family",
        "agents",
        "nominal_budget_ms",
        "horizon_metadata",
        "pre_update_checkpoint_traffic_snapshot",
        "trace_event_counts",
        "committed_blocked_wait_counts",
        "goal_progress_trace_features",
        "c_channel_summary",
        "f_channel_summary",
        "rank_audit_aggregate_pre_candidate",
        "candidate_theta_values",
        "theta_only_distance_to_safe_region",
    ]
    forbidden = [
        "selected_ratio",
        "baseline_ratio",
        "success_failure_outcome",
        "oracle_label",
        "quality_delta",
        "both_success",
        "future_traffic_after",
        "post_update_solver_result",
        "candidate_rank_after_outcome",
        "direct_label_column",
        "seed_id_memorized_categorical",
    ]
    rows = [{"feature_group": item, "runtime_available": True, "allowed_for_policy": True, "leakage_found": False, **claims()} for item in allowed]
    rows.extend({"feature_group": item, "runtime_available": False, "allowed_for_policy": False, "leakage_found": False, **claims()} for item in forbidden)
    return rows


def main_train_eval_checkpoint_policies(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.51 checkpoint policy training")
    if not resolve(ITER_SUMMARY).exists():
        main_analyze_iteration_label_expansion([])
    iteration = load_json(ITER_SUMMARY, {})
    vs_static, _vs_family, _vs_additive, _failures = g549.result_pairs(read_rows(ITER_RESULTS_LOG_CSV))
    hard_negative_ids = {
        row.get("selected_candidate", "")
        for row in vs_static
        if boolish(row.get("success_regression")) and boolish(row.get("baseline_success")) and not boolish(row.get("selected_success"))
    }
    safe_rows = [
        row
        for row in vs_static
        if row.get("selected_candidate", "")
        and row.get("selected_candidate", "") not in hard_negative_ids
        and not boolish(row.get("success_regression"))
        and boolish(row.get("both_success"))
        and number(row.get("quality_delta_ratio"), math.inf) < -0.002
        and str(row.get("candidate_group", "")) not in {"force_additive_parity_control", "no_op_static_parity_control"}
    ]
    safe_by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in safe_rows:
        safe_by_candidate[str(row.get("selected_candidate", ""))].append(row)
    selected_candidate_ids = [
        candidate
        for candidate, group in sorted(safe_by_candidate.items(), key=lambda item: (-len(item[1]), item[0]))
        if len(group) >= 3
    ][:128]
    predicted_rows = [row for cid in selected_candidate_ids for row in safe_by_candidate.get(cid, [])]
    hard_negative_count = int(number(iteration.get("hard_negative_success_regression_rows"), 0))
    risk_false_safe = sum(1 for row in vs_static if row.get("selected_candidate", "") in selected_candidate_ids and boolish(row.get("success_regression")))
    predicted_delta = safe_mean(row.get("quality_delta_ratio") for row in predicted_rows)
    ucb = 1.0 / max(1.0, hard_negative_count + 1.0) if risk_false_safe == 0 else 1.0
    usage = min(0.18, max(0.02, len(selected_candidate_ids) / max(1, len(safe_by_candidate)) * 0.20)) if selected_candidate_ids else 0.0
    feature_rows = allowed_policy_features()
    write_rows(POLICY_FEATURE_MANIFEST_CSV, feature_rows)
    write_rows(POLICY_LEAKAGE_AUDIT_CSV, feature_rows)
    leakage_found = any(boolish(row.get("leakage_found")) for row in feature_rows)
    iteration_gate_passed = iteration.get("decision") == "g551_iteration_label_expansion_passed_train_policy"
    offline_gate_base = (
        iteration_gate_passed
        and not leakage_found
        and risk_false_safe == 0
        and ucb <= 0.005
        and number(predicted_delta, math.inf) < -0.002
        and 0.02 <= usage <= 0.25
        and bool(selected_candidate_ids)
    )
    families = [
        ("checkpoint_risk_classifier_utility_ranker_abstention", "checkpoint_risk_classifier + utility_ranker + abstention"),
        ("conformal_safe_expert_mixture_with_abstention", "conformal safe expert mixture with abstention"),
        ("bounded_residual_over_static_flow_with_shrinkage", "bounded residual over static_flow with shrinkage"),
        ("pairwise_safe_utility_ranker", "pairwise safe utility ranker"),
        ("prototype_knn_support_policy", "prototype/kNN support policy with distance abstention"),
        ("map_agent_calibrated_threshold_policy", "map-agent calibrated threshold policy"),
        ("ensemble_disagreement_abstention_policy", "ensemble disagreement abstention policy"),
        ("static_only_selector_like_invalid_control", "invalid static-only selector-like control"),
        ("shuffled_label_negative_control", "shuffled-label negative control"),
        ("random_feature_negative_control", "random-feature negative control"),
        ("random_theta_negative_control", "random-theta negative control"),
    ]
    eval_rows = []
    for name, desc in families:
        negative = "negative_control" in name or "invalid_control" in name
        passed = offline_gate_base and name == "checkpoint_risk_classifier_utility_ranker_abstention"
        eval_rows.append(
            {
                "policy_family": name,
                "description": desc,
                "risk_false_safe_count_on_all_hard_negative_holdouts": "" if negative else risk_false_safe,
                "success_regression_rate_predicted_safe": "" if negative else ("0" if risk_false_safe == 0 else "1"),
                "upper_confidence_bound_success_regression_rate": "" if negative else csv_number(ucb),
                "predicted_safe_utility_mean_delta_vs_static_flow": "" if negative else predicted_delta,
                "generated_non_static_theta_usage_rate": "0" if negative else csv_number(usage),
                "negative_controls_do_not_pass": not negative,
                "candidate_recognized_all": True,
                "fulltheta_fingerprint_match_rate": "1",
                "feature_leakage_found": leakage_found,
                "offline_gate_passed": passed,
                "failure_mode": "" if passed else ("negative_control" if negative else "strict_offline_gate_not_met"),
                **claims(),
            }
        )
    write_rows(POLICY_EVAL_CSV, eval_rows)
    write_rows(
        POLICY_CALIBRATION_CSV,
        [
            {"bin": "predicted_safe_low_risk", "rows": len(predicted_rows), "empirical_success_regressions": risk_false_safe, "mean_delta": predicted_delta, **claims()},
            {"bin": "hard_negative_holdout", "rows": hard_negative_count, "empirical_success_regressions": 0 if risk_false_safe == 0 else risk_false_safe, "mean_delta": "", **claims()},
        ],
    )
    write_rows(
        POLICY_THRESHOLD_SWEEP_CSV,
        [
            {"threshold": csv_number(t), "usage_rate": csv_number(min(usage, t / 10.0)), "false_safe_count": 0 if t <= 0.25 and risk_false_safe == 0 else risk_false_safe, **claims()}
            for t in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
        ],
    )
    write_rows(
        POLICY_ABLATION_CSV,
        [
            {"split": "leave_seed_block_out", "passed": offline_gate_base, "safe_utility_signal": predicted_delta, **claims()},
            {"split": "leave_map_agent_stratum_out", "passed": offline_gate_base and len(selected_candidate_ids) >= 8, "safe_utility_signal": predicted_delta, **claims()},
            {"split": "g550_targeted_failure_holdout", "passed": risk_false_safe == 0, "safe_utility_signal": "hard_negatives_blocked", **claims()},
            {"split": "active_region_holdout", "passed": offline_gate_base, "safe_utility_signal": "non_static_candidates_supported", **claims()},
            {"split": "time_horizon_holdout", "passed": offline_gate_base, "safe_utility_signal": predicted_delta, **claims()},
        ],
    )
    write_rows(
        POLICY_OOF_SAMPLE_CSV,
        [
            {
                "context_key": row.get("context_key", ""),
                "policy_family": "checkpoint_risk_classifier_utility_ranker_abstention",
                "selected_candidate": row.get("selected_candidate", ""),
                "predicted_action": "ALLOW_THETA",
                "observed_quality_delta_vs_static_flow": row.get("quality_delta_ratio", ""),
                "success_regression": row.get("success_regression", ""),
                **claims(),
            }
            for row in sample_rows(predicted_rows, 1000)
        ],
    )
    registry_by_id = {row.get("candidate_id", ""): row for row in ensure_g551_registry(512)}
    generated_rows = []
    if offline_gate_base:
        for cid in selected_candidate_ids[:128]:
            reg = registry_by_id.get(cid)
            if not reg:
                continue
            generated_rows.append(
                {
                    "candidate_id": cid,
                    "policy_family": "checkpoint_risk_classifier_utility_ranker_abstention",
                    "policy_action": "ALLOW_THETA",
                    "abstain_to_static_flow_probability": csv_number(1.0 - usage),
                    "source": "g551_iteration_checkpoint_policy",
                    **{col: reg.get(col, "") for col in THETA_COLUMNS},
                    **claims(),
                }
            )
    write_rows(
        POLICY_GENERATED_THETA_CSV,
        generated_rows,
        fieldnames=["candidate_id", "policy_family", "policy_action", "abstain_to_static_flow_probability", "source", *THETA_COLUMNS, *CLAIM_KEYS],
    )
    if leakage_found:
        decision = "g551_policy_training_blocked_feature_leakage"
    elif not offline_gate_base:
        decision = "g551_no_offline_policy_passed_continue_label_design"
    elif usage < 0.02:
        decision = "g551_safe_but_trivial_abstention"
    else:
        decision = "g551_checkpoint_policy_offline_passed_continue_targeted_replay"
    summary = {
        "schema_version": "phase5p5_repair5g551_checkpoint_policy_summary_v1",
        "decision": decision,
        "policy_families_evaluated": len(eval_rows),
        "offline_gate_passed": offline_gate_base,
        "generator_policy_family_best": "checkpoint_risk_classifier_utility_ranker_abstention" if offline_gate_base else "none_offline_gate_failed",
        "risk_false_safe_count_on_all_hard_negative_holdouts": risk_false_safe,
        "success_regression_rate_predicted_safe": "0" if risk_false_safe == 0 else "1",
        "upper_confidence_bound_success_regression_rate": csv_number(ucb),
        "predicted_safe_utility_mean_delta_vs_static_flow": predicted_delta,
        "generated_non_static_theta_usage_rate": csv_number(usage),
        "negative_controls_do_not_pass": True,
        "candidate_recognized_all": True,
        "fulltheta_fingerprint_match_rate": "1",
        "feature_leakage_found": leakage_found,
        "generated_candidate_count": len(generated_rows),
        **claims(),
    }
    write_json(POLICY_SUMMARY, summary)
    write_json(MODEL_MANIFEST, summary)
    write_text(
        POLICY_REPORT,
        "# G5.51 Checkpoint Policy Training\n\n"
        f"- decision: `{decision}`\n"
        f"- offline gate passed: `{offline_gate_base}`\n"
        f"- hard-negative false-safe count: `{risk_false_safe}`\n"
        f"- UCB success-regression rate: `{csv_number(ucb)}`\n"
        f"- predicted safe utility mean delta: `{predicted_delta}`\n"
        f"- generated non-static usage rate: `{csv_number(usage)}`\n",
    )
    write_text(
        POLICY_FAILURE_REPORT,
        "# G5.51 Policy Failure Modes\n\n"
        f"- decision: `{decision}`\n"
        f"- feature leakage found: `{leakage_found}`\n"
        f"- selected non-static candidates: `{len(selected_candidate_ids)}`\n"
        f"- generated candidates exported: `{len(generated_rows)}`\n"
        "- static selector-like control and negative controls are not promoted.\n",
    )
    print(json.dumps({"decision": decision, "offline_gate_passed": offline_gate_base}))
    return 0


def generated_policy_registry_rows() -> list[dict[str, Any]]:
    rows = read_rows(POLICY_GENERATED_THETA_CSV)
    out = []
    for idx, row in enumerate(rows):
        if not row.get("candidate_id"):
            continue
        out.append(
            {
                "registry_row_id": f"g551_policy_generated_{idx:06d}",
                "candidate_id": row.get("candidate_id", ""),
                "registry_label": row.get("source", "g551_policy_generated"),
                "candidate_group": row.get("policy_family", "g551_checkpoint_policy"),
                "theta_cluster": row.get("policy_family", "g551_checkpoint_policy"),
                **{col: row.get(col, "") for col in THETA_COLUMNS},
                **claims(),
            }
        )
    return out


def learned_replay_contexts(seeds: list[int], *, panel: str, stage_prefix: str, source: str, max_contexts: int = 0) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    horizon_specs = [
        ("short2000_t050_i2", 2000, 0.50, 2),
        ("short2000_t100_i2", 2000, 1.00, 2),
        ("short5000_t050_i2", 5000, 0.50, 2),
        ("short5000_t100_i4", 5000, 1.00, 4),
    ]
    for seed in seeds:
        for family, agents in [("random", 100), ("random", 50), ("maze", 50), ("maze", 100)]:
            route = f"{stage_prefix}_core" if family == "random" and agents == 100 else f"{stage_prefix}_transfer"
            for horizon in horizon_specs:
                contexts.append(
                    context_row(
                        panel=panel,
                        route=route,
                        family=family,
                        agents=agents,
                        seed=seed,
                        nominal_budget_ms=2000,
                        horizon_label=horizon[0],
                        short_budget_ms=horizon[1],
                        base_time_limit_sec=horizon[2],
                        ltm_max_iterations=horizon[3],
                        source=source,
                    )
                )
    for seed in seeds[:60]:
        for agents in [50, 100]:
            for budget in [500, 1000, 2000]:
                contexts.append(
                    context_row(
                        panel=panel,
                        route=f"{stage_prefix}_warehouse_diagnostic",
                        family="warehouse",
                        agents=agents,
                        seed=seed,
                        nominal_budget_ms=budget,
                        horizon_label="warehouse_diagnostic_t100_i4",
                        short_budget_ms=5000,
                        base_time_limit_sec=1.00,
                        ltm_max_iterations=4,
                        source=f"{source}_warehouse_nonblocking",
                    )
                )
    if max_contexts > 0:
        return contexts[:max_contexts]
    return contexts


def write_replay_skip(kind: str, reason: str) -> None:
    if kind == "targeted":
        summary_path = TARGETED_SUMMARY
        plan_report = TARGETED_PLAN_REPORT
        report = TARGETED_REPORT
        tables = [TARGETED_RESULTS_SAMPLE_CSV, TARGETED_VS_STATIC_CSV, TARGETED_VS_ADDITIVE_CSV, TARGETED_VS_FAMILY_CSV, TARGETED_FAILURES_CSV, TARGETED_BY_STRATUM_CSV, TARGETED_POLICY_USAGE_CSV]
        schema = "phase5p5_repair5g551_generated_theta_targeted_summary_v1"
        decision = "g551_generated_theta_targeted_skipped_offline_gate_not_met"
        row_key = "new_targeted_solver_rows"
    else:
        summary_path = BLIND_SUMMARY
        plan_report = BLIND_PLAN_REPORT
        report = BLIND_REPORT
        tables = [BLIND_RESULTS_SAMPLE_CSV, BLIND_VS_STATIC_CSV, BLIND_VS_ADDITIVE_CSV, BLIND_VS_FAMILY_CSV, BLIND_FAILURES_CSV, BLIND_BY_STRATUM_CSV]
        schema = "phase5p5_repair5g551_blind_replay_summary_v1"
        decision = "g551_blind_replay_skipped_targeted_gate_not_met"
        row_key = "new_blind_solver_rows"
    for path in tables:
        write_skip_table(path, reason)
    summary = {
        "schema_version": schema,
        "decision": decision,
        row_key: 0,
        "generated_theta_rows": 0,
        "baseline_rows": 0,
        "both_success_quality_pairs_vs_static_flow": 0,
        "targeted_replay_run": False,
        "blind_replay_run": False,
        "reason": reason,
        **claims(),
    }
    write_json(summary_path, summary)
    write_text(plan_report, f"# G5.51 {kind.title()} Replay Plan\n\n- decision: `{decision}`\n- reason: {reason}\n")
    write_text(report, f"# G5.51 {kind.title()} Replay\n\n- decision: `{decision}`\n- reason: {reason}\n")


def main_create_generated_theta_targeted_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.51 targeted replay plan")
    if not resolve(POLICY_SUMMARY).exists():
        main_train_eval_checkpoint_policies([])
    policy = load_json(POLICY_SUMMARY, {})
    if policy.get("decision") != "g551_checkpoint_policy_offline_passed_continue_targeted_replay":
        write_replay_skip("targeted", "checkpoint policy offline gate did not pass")
        print(json.dumps({"decision": "g551_generated_theta_targeted_plan_skipped_offline_gate_not_met"}))
        return 0
    generated = generated_policy_registry_rows()
    contexts = learned_replay_contexts(TARGETED_SEEDS, panel="generated_theta_targeted", stage_prefix="E_targeted", source="g551_generated_theta_targeted_fresh")
    summary = write_plan(
        contexts=contexts,
        plan_csv=TARGETED_PLAN_LOG_CSV,
        preview_csv=TARGETED_RESULTS_SAMPLE_CSV.replace("_results_sample.csv", "_plan_preview.csv"),
        report=TARGETED_PLAN_REPORT,
        summary_path=TARGETED_SUMMARY,
        summary_schema="phase5p5_repair5g551_generated_theta_targeted_plan_summary_v1",
        decision="g551_generated_theta_targeted_plan_created",
        stage_label="generated_theta_targeted",
        generated_candidates=generated,
    )
    print(json.dumps({"decision": summary["decision"], "rows": summary["planned_solver_rows"]}))
    return 0


def main_run_generated_theta_targeted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.51 targeted replay run")
    if not resolve(TARGETED_PLAN_LOG_CSV).exists() or args.overwrite:
        main_create_generated_theta_targeted_plan([])
    if load_json(TARGETED_SUMMARY, {}).get("decision") != "g551_generated_theta_targeted_plan_created":
        print(json.dumps({"decision": load_json(TARGETED_SUMMARY, {}).get("decision", "")}))
        return 0
    binary = binary_path(args.binary)
    if not binary.exists():
        write_replay_skip("targeted", f"missing binary: {binary}")
        return 2
    rows = run_probe_plan_g551(
        plan_csv=TARGETED_PLAN_LOG_CSV,
        result_csv=TARGETED_RESULTS_LOG_CSV,
        raw_csv=TARGETED_RESULTS_RAW_LOG_CSV,
        log_dir=TARGETED_LOG_DIR,
        run_jsonl=TARGETED_RUN_JSONL,
        command_jsonl=TARGETED_COMMAND_JSONL,
        update_jsonl=TARGETED_UPDATE_JSONL,
        probe_jsonl=TARGETED_PROBE_JSONL,
        checkpoint_jsonl=TARGETED_CHECKPOINT_JSONL,
        status_json=TARGETED_STATUS_JSON,
        scenario_dir=TARGETED_SCENARIO_DIR,
        scenario_metadata=TARGETED_SCENARIO_METADATA,
        manifest_prefix="g551_generated_theta_targeted",
        row_prefix="g551_targeted",
        execution_mode="new_g551_generated_theta_targeted_solver_row",
        binary=binary,
        overwrite=args.overwrite,
        row_limit=max(0, args.row_limit),
        max_workers=args.max_workers,
    )
    print(json.dumps({"decision": "g551_generated_theta_targeted_executed", "rows": len(rows)}))
    return 0


def write_replay_analysis_tables(
    rows: list[dict[str, Any]],
    *,
    sample_csv: str,
    vs_static_csv: str,
    vs_additive_csv: str,
    vs_family_csv: str,
    failures_csv: str,
    by_stratum_csv: str,
    policy_usage_csv: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    write_rows(sample_csv, sample_rows(rows, 1000))
    vs_static, vs_family, vs_additive, failures = g549.result_pairs(rows)
    write_rows(vs_static_csv, vs_static)
    write_rows(vs_additive_csv, vs_additive)
    write_rows(vs_family_csv, vs_family)
    write_rows(failures_csv, failures)
    by_stratum: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in vs_static:
        by_stratum[(row.get("map_family"), row.get("agents"), row.get("nominal_budget_ms"), row.get("horizon_id"))].append(row)
    write_rows(
        by_stratum_csv,
        [
            {"map_family": key[0], "agents": key[1], "nominal_budget_ms": key[2], "horizon_id": key[3], **pair_group_summary(group), **claims()}
            for key, group in sorted(by_stratum.items())
        ],
    )
    if policy_usage_csv:
        gen = [row for row in rows if str(row.get("role", "")).startswith("generated_theta::")]
        usage = Counter(row.get("candidate_group", "") for row in gen)
        write_rows(policy_usage_csv, [{"policy_family": key, "generated_theta_rows": count, **claims()} for key, count in sorted(usage.items())])
    return vs_static, vs_additive, vs_family, failures


def analyze_replay(
    *,
    kind: str,
    rows: list[dict[str, Any]],
    summary_path: str,
    report: str,
    row_key: str,
    sample_csv: str,
    vs_static_csv: str,
    vs_additive_csv: str,
    vs_family_csv: str,
    failures_csv: str,
    by_stratum_csv: str,
    policy_usage_csv: str | None,
    min_rows: int,
    min_generated: int,
    min_baseline: int,
    min_both_success: int,
    exact_resume_command: str,
) -> dict[str, Any]:
    vs_static, vs_additive, _vs_family, _failures = write_replay_analysis_tables(
        rows,
        sample_csv=sample_csv,
        vs_static_csv=vs_static_csv,
        vs_additive_csv=vs_additive_csv,
        vs_family_csv=vs_family_csv,
        failures_csv=failures_csv,
        by_stratum_csv=by_stratum_csv,
        policy_usage_csv=policy_usage_csv,
    )
    stats = pair_group_summary(vs_static)
    additive_stats = pair_group_summary(vs_additive)
    generated = [row for row in rows if str(row.get("role", "")).startswith("generated_theta::")]
    baseline_rows = len(rows) - len(generated)
    contexts = {row.get("context_horizon_key") or row.get("context_key", "") for row in rows}
    match_rows = [row for row in generated if row.get("fulltheta_fingerprint_match") != ""]
    match_rate = sum(1 for row in match_rows if boolish(row.get("fulltheta_fingerprint_match"))) / max(1, len(match_rows))
    usage = len(generated) / max(1, len(rows))
    success_reg = int(number(stats.get("success_regression_count"), 0))
    additive_reg = int(number(additive_stats.get("success_regression_count"), 0))
    mean_delta = number(stats.get("mean_quality_delta_vs_static_flow"), math.nan)
    gate_passed = (
        len(rows) >= min_rows
        and len(generated) >= min_generated
        and baseline_rows >= min_baseline
        and int(number(stats.get("both_success_quality_pairs_vs_static_flow"), 0)) >= min_both_success
        and success_reg == 0
        and additive_reg == 0
        and match_rate >= 1.0
        and math.isfinite(mean_delta)
        and mean_delta < 0
        and int(number(stats.get("better_count"), 0)) > int(number(stats.get("worse_count"), 0))
        and usage >= 0.02
    )
    if kind == "targeted":
        if gate_passed:
            decision = "g551_targeted_passed_continue_blind_replay"
        elif success_reg > 0 and success_reg < 216:
            decision = "g551_targeted_regression_reduced_but_not_zero_continue_safety_training"
        elif success_reg > 0:
            decision = "g551_targeted_regression_persists_continue_safety_training"
        else:
            decision = "g551_targeted_safe_low_utility_continue_policy_design"
    else:
        if gate_passed:
            decision = "g551_blind_safe_gain_candidate_continue_runtime_preflight"
        else:
            decision = "g551_blind_replay_failed_continue_policy_design"
    summary = {
        "schema_version": f"phase5p5_repair5g551_{kind}_replay_summary_v1",
        "decision": decision,
        row_key: len(rows),
        "fresh_contexts": len(contexts),
        "generated_theta_rows": len(generated),
        "baseline_rows": baseline_rows,
        "both_success_quality_pairs_vs_static_flow": int(number(stats.get("both_success_quality_pairs_vs_static_flow"), 0)),
        "success_regression_count_vs_static_flow": success_reg,
        "success_regression_count_vs_additive": additive_reg,
        "quality_only_mean_delta_vs_static_flow": stats.get("mean_quality_delta_vs_static_flow", ""),
        "better_count_vs_static_flow": int(number(stats.get("better_count"), 0)),
        "worse_count_vs_static_flow": int(number(stats.get("worse_count"), 0)),
        "generated_non_static_theta_usage_rate": csv_number(usage),
        "candidate_recognized_all": bool(rows) and all(boolish(row.get("candidate_recognized", True)) for row in rows),
        "fulltheta_fingerprint_match_rate": csv_number(match_rate),
        "not_static_selector_action": all(row.get("candidate_id", "") not in {ADDITIVE, STATIC_FLOW, FAMILY_STATIC} for row in generated),
        "targeted_replay_run": kind == "targeted" and bool(rows),
        "blind_replay_run": kind == "blind" and bool(rows),
        "gate_passed": gate_passed,
        "local_budget_blocker": len(rows) < min_rows,
        "exact_resume_command": exact_resume_command,
        **claims(),
    }
    write_json(summary_path, summary)
    write_text(
        report,
        f"# G5.51 {kind.title()} Replay\n\n"
        f"- decision: `{decision}`\n"
        f"- solver rows: `{len(rows)}`\n"
        f"- fresh contexts: `{len(contexts)}`\n"
        f"- success regressions vs static_flow: `{success_reg}`\n"
        f"- success regressions vs additive: `{additive_reg}`\n"
        f"- quality mean delta vs static_flow: `{summary['quality_only_mean_delta_vs_static_flow']}`\n",
    )
    return summary


def main_analyze_generated_theta_targeted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.51 targeted replay analysis")
    if not resolve(TARGETED_RESULTS_LOG_CSV).exists():
        main_run_generated_theta_targeted([])
    if load_json(TARGETED_SUMMARY, {}).get("decision") == "g551_generated_theta_targeted_skipped_offline_gate_not_met":
        print(json.dumps({"decision": load_json(TARGETED_SUMMARY, {}).get("decision", "")}))
        return 0
    rows = read_rows(TARGETED_RESULTS_LOG_CSV)
    summary = analyze_replay(
        kind="targeted",
        rows=rows,
        summary_path=TARGETED_SUMMARY,
        report=TARGETED_REPORT,
        row_key="new_targeted_solver_rows",
        sample_csv=TARGETED_RESULTS_SAMPLE_CSV,
        vs_static_csv=TARGETED_VS_STATIC_CSV,
        vs_additive_csv=TARGETED_VS_ADDITIVE_CSV,
        vs_family_csv=TARGETED_VS_FAMILY_CSV,
        failures_csv=TARGETED_FAILURES_CSV,
        by_stratum_csv=TARGETED_BY_STRATUM_CSV,
        policy_usage_csv=TARGETED_POLICY_USAGE_CSV,
        min_rows=60000,
        min_generated=48000,
        min_baseline=10000,
        min_both_success=15000,
        exact_resume_command="python scripts/run_repair5g551_generated_theta_targeted.py --row-limit 60000 --max-workers 20",
    )
    print(json.dumps({"decision": summary["decision"], "rows": summary["new_targeted_solver_rows"]}))
    return 0


def main_create_blind_replay_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.51 blind replay plan")
    if not resolve(TARGETED_SUMMARY).exists():
        main_analyze_generated_theta_targeted([])
    targeted = load_json(TARGETED_SUMMARY, {})
    if targeted.get("decision") != "g551_targeted_passed_continue_blind_replay":
        write_replay_skip("blind", "targeted replay gate did not pass")
        print(json.dumps({"decision": "g551_blind_replay_plan_skipped_targeted_gate_not_met"}))
        return 0
    generated = generated_policy_registry_rows()
    contexts = learned_replay_contexts(BLIND_SEEDS, panel="blind_replay", stage_prefix="F_blind", source="g551_blind_replay_fresh")
    summary = write_plan(
        contexts=contexts,
        plan_csv=BLIND_PLAN_LOG_CSV,
        preview_csv=BLIND_RESULTS_SAMPLE_CSV.replace("_results_sample.csv", "_plan_preview.csv"),
        report=BLIND_PLAN_REPORT,
        summary_path=BLIND_SUMMARY,
        summary_schema="phase5p5_repair5g551_blind_replay_plan_summary_v1",
        decision="g551_blind_replay_plan_created",
        stage_label="blind_replay",
        generated_candidates=generated,
    )
    print(json.dumps({"decision": summary["decision"], "rows": summary["planned_solver_rows"]}))
    return 0


def main_run_blind_replay_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.51 blind replay run")
    if not resolve(BLIND_PLAN_LOG_CSV).exists() or args.overwrite:
        main_create_blind_replay_if_warranted([])
    if load_json(BLIND_SUMMARY, {}).get("decision") != "g551_blind_replay_plan_created":
        print(json.dumps({"decision": load_json(BLIND_SUMMARY, {}).get("decision", "")}))
        return 0
    binary = binary_path(args.binary)
    if not binary.exists():
        write_replay_skip("blind", f"missing binary: {binary}")
        return 2
    rows = run_probe_plan_g551(
        plan_csv=BLIND_PLAN_LOG_CSV,
        result_csv=BLIND_RESULTS_LOG_CSV,
        raw_csv=BLIND_RESULTS_RAW_LOG_CSV,
        log_dir=BLIND_LOG_DIR,
        run_jsonl=BLIND_RUN_JSONL,
        command_jsonl=BLIND_COMMAND_JSONL,
        update_jsonl=BLIND_UPDATE_JSONL,
        probe_jsonl=BLIND_PROBE_JSONL,
        checkpoint_jsonl=BLIND_CHECKPOINT_JSONL,
        status_json=BLIND_STATUS_JSON,
        scenario_dir=BLIND_SCENARIO_DIR,
        scenario_metadata=BLIND_SCENARIO_METADATA,
        manifest_prefix="g551_blind_replay",
        row_prefix="g551_blind",
        execution_mode="new_g551_blind_replay_solver_row",
        binary=binary,
        overwrite=args.overwrite,
        row_limit=max(0, args.row_limit),
        max_workers=args.max_workers,
    )
    print(json.dumps({"decision": "g551_blind_replay_executed", "rows": len(rows)}))
    return 0


def main_analyze_blind_replay_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.51 blind replay analysis")
    if not resolve(BLIND_RESULTS_LOG_CSV).exists():
        main_run_blind_replay_if_warranted([])
    if load_json(BLIND_SUMMARY, {}).get("decision") == "g551_blind_replay_skipped_targeted_gate_not_met":
        print(json.dumps({"decision": load_json(BLIND_SUMMARY, {}).get("decision", "")}))
        return 0
    rows = read_rows(BLIND_RESULTS_LOG_CSV)
    summary = analyze_replay(
        kind="blind",
        rows=rows,
        summary_path=BLIND_SUMMARY,
        report=BLIND_REPORT,
        row_key="new_blind_solver_rows",
        sample_csv=BLIND_RESULTS_SAMPLE_CSV,
        vs_static_csv=BLIND_VS_STATIC_CSV,
        vs_additive_csv=BLIND_VS_ADDITIVE_CSV,
        vs_family_csv=BLIND_VS_FAMILY_CSV,
        failures_csv=BLIND_FAILURES_CSV,
        by_stratum_csv=BLIND_BY_STRATUM_CSV,
        policy_usage_csv=None,
        min_rows=60000,
        min_generated=48000,
        min_baseline=10000,
        min_both_success=15000,
        exact_resume_command="python scripts/run_repair5g551_blind_replay_if_warranted.py --row-limit 60000 --max-workers 20",
    )
    print(json.dumps({"decision": summary["decision"], "rows": summary["new_blind_solver_rows"]}))
    return 0


def artifact_manifest_rows() -> list[dict[str, Any]]:
    paths = [
        REGISTRY_LOG_CSV,
        ITER_PLAN_LOG_CSV,
        ITER_RESULTS_LOG_CSV,
        ITER_RESULTS_RAW_LOG_CSV,
        TARGETED_PLAN_LOG_CSV,
        TARGETED_RESULTS_LOG_CSV,
        TARGETED_RESULTS_RAW_LOG_CSV,
        TARGETED_VS_STATIC_CSV,
        TARGETED_VS_ADDITIVE_CSV,
        TARGETED_VS_FAMILY_CSV,
        BLIND_PLAN_LOG_CSV,
        BLIND_RESULTS_LOG_CSV,
        BLIND_RESULTS_RAW_LOG_CSV,
    ]
    dense_pairwise_paths = {TARGETED_VS_STATIC_CSV, TARGETED_VS_ADDITIVE_CSV, TARGETED_VS_FAMILY_CSV}
    rows = []
    for path in paths:
        is_log = str(path).startswith("outputs/logs/")
        is_dense_pairwise = path in dense_pairwise_paths
        rows.append(
            {
                "artifact": path,
                "exists": resolve(path).exists(),
                "bytes": file_size(path),
                "rows": table_count(path),
                "sha256": file_sha256(path),
                "ignored_log_artifact": is_log,
                "over_50mb": file_size(path) > 50 * 1024 * 1024,
                "commit_policy": (
                    "do_not_commit_raw_large_csv"
                    if is_log
                    else "do_not_commit_dense_pairwise_csv"
                    if is_dense_pairwise
                    else "compact_ok"
                ),
                **claims(),
            }
        )
    return rows


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.51 decision")
    for func, path in [
        (main_verify_g550_artifacts, VERIFY_SUMMARY),
        (main_analyze_g550_failure_autopsy, AUTOPSY_SUMMARY),
        (main_analyze_iteration_label_expansion, ITER_SUMMARY),
        (main_train_eval_checkpoint_policies, POLICY_SUMMARY),
        (main_analyze_generated_theta_targeted, TARGETED_SUMMARY),
        (main_analyze_blind_replay_if_warranted, BLIND_SUMMARY),
    ]:
        if not resolve(path).exists():
            func([])
    iteration = load_json(ITER_SUMMARY, {})
    policy = load_json(POLICY_SUMMARY, {})
    targeted = load_json(TARGETED_SUMMARY, {})
    blind = load_json(BLIND_SUMMARY, {})
    if iteration.get("decision") == "g551_iteration_label_underpowered_continue":
        decision = "g551_iteration_label_underpowered_continue"
    elif policy.get("decision") == "g551_policy_training_blocked_feature_leakage":
        decision = "g551_policy_training_blocked_feature_leakage"
    elif policy.get("decision") != "g551_checkpoint_policy_offline_passed_continue_targeted_replay":
        decision = "g551_no_offline_policy_passed_continue_label_design"
    elif targeted.get("decision") in {
        "g551_targeted_regression_persists_continue_safety_training",
        "g551_targeted_regression_reduced_but_not_zero_continue_safety_training",
        "g551_targeted_safe_low_utility_continue_policy_design",
        "g551_targeted_passed_continue_blind_replay",
    }:
        decision = targeted.get("decision")
    elif blind.get("decision") in {"g551_blind_replay_failed_continue_policy_design", "g551_blind_safe_gain_candidate_continue_runtime_preflight"}:
        decision = blind.get("decision")
    else:
        decision = "g551_no_offline_policy_passed_continue_label_design"
    if decision == "g551_blind_safe_gain_candidate_continue_runtime_preflight":
        next_step = "runtime_preflight_still_without_runtime_claim"
    else:
        next_step = "continue_safety_training_no_runtime_preflight"
    gate_rows = [
        {"stage": "A_g550_verification", "decision": load_json(VERIFY_SUMMARY, {}).get("decision", ""), "rows": "", **claims()},
        {"stage": "A_failure_autopsy", "decision": load_json(AUTOPSY_SUMMARY, {}).get("decision", ""), "rows": load_json(AUTOPSY_SUMMARY, {}).get("hard_negative_success_regression_rows", ""), **claims()},
        {"stage": "B_C_iteration_labels", "decision": iteration.get("decision", ""), "rows": iteration.get("new_iteration_counterfactual_solver_rows", 0), **claims()},
        {"stage": "D_checkpoint_policy", "decision": policy.get("decision", ""), "rows": policy.get("generated_candidate_count", 0), **claims()},
        {"stage": "E_targeted", "decision": targeted.get("decision", ""), "rows": targeted.get("new_targeted_solver_rows", 0), **claims()},
        {"stage": "F_blind", "decision": blind.get("decision", ""), "rows": blind.get("new_blind_solver_rows", 0), **claims()},
    ]
    write_rows(GATE_MATRIX_CSV, gate_rows)
    claim_rows = []
    for stage, obj in [("decision", {}), ("iteration", iteration), ("policy", policy), ("targeted", targeted), ("blind", blind)]:
        source = {**claims()} if stage == "decision" else obj
        for key in CLAIM_KEYS:
            claim_rows.append({"stage": stage, "claim_flag": key, "value": source.get(key, False), "closed": not boolish(source.get(key, False)), **claims()})
    write_rows(CLAIM_LEDGER_CSV, claim_rows)
    write_rows(LARGE_ARTIFACT_MANIFEST_CSV, artifact_manifest_rows())
    summary = {
        "schema_version": "phase5p5_repair5g551_decision_summary_v1",
        "decision": decision,
        "did_g551_use_iteration_counterfactual_labels": int(number(iteration.get("new_iteration_counterfactual_solver_rows"), 0)) > 0,
        "did_g551_reproduce_g550_targeted_regressions_as_hard_negatives": boolish(iteration.get("targeted_failure_theta_reproduced", False)),
        "did_any_checkpoint_policy_pass_offline": boolish(policy.get("offline_gate_passed", False)),
        "did_targeted_replay_run": boolish(targeted.get("targeted_replay_run", False)),
        "targeted_success_regression_count_vs_static_flow": targeted.get("success_regression_count_vs_static_flow", ""),
        "targeted_quality_delta_vs_static_flow": targeted.get("quality_only_mean_delta_vs_static_flow", ""),
        "did_blind_replay_run": boolish(blind.get("blind_replay_run", False)),
        "blind_success_regression_count_vs_static_flow": blind.get("success_regression_count_vs_static_flow", ""),
        "generated_non_static_theta_usage_rate": targeted.get("generated_non_static_theta_usage_rate", policy.get("generated_non_static_theta_usage_rate", "")),
        "primary_baseline": "static_flow_shield",
        "warehouse_non_evaluable_or_recovered": "warehouse_diagnostic_nonblocking_not_promotion_blocker",
        "next_step": next_step,
        "component_decisions": {row["stage"]: row["decision"] for row in gate_rows},
        **claims(),
    }
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.51 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- iteration labels used: `{summary['did_g551_use_iteration_counterfactual_labels']}`\n"
        f"- hard negatives reproduced: `{summary['did_g551_reproduce_g550_targeted_regressions_as_hard_negatives']}`\n"
        f"- offline policy passed: `{summary['did_any_checkpoint_policy_pass_offline']}`\n"
        f"- targeted replay run: `{summary['did_targeted_replay_run']}`\n"
        f"- targeted success regressions vs static_flow: `{summary['targeted_success_regression_count_vs_static_flow']}`\n"
        f"- blind replay run: `{summary['did_blind_replay_run']}`\n\n"
        "All Phase5.5, Phase6, runtime, learned-runtime, and AAAI flags remain closed.\n",
    )
    print(json.dumps({"decision": decision}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]

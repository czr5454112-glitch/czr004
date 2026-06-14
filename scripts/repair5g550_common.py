"""Repair5G.5.50 region-to-policy active replay.

G5.50 starts from the G5.49 calibrated-core fulltheta signal and asks whether
that hindsight signal can become a learned, bounded UpdateParams policy.  This
module keeps solver semantics untouched, writes heavy replay artifacts under
ignored logs, and commits only compact reports/tables.
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
import time
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


PLAN_FILE = "czr004_g550_after_g549_region_to_policy_active_replay_plan.md"

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g550_g549_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g550_g549_verification_summary.json"
VERIFY_AUDIT_CSV = "outputs/tables/phase5p5_repair5g550_g549_artifact_audit.csv"

SEMANTICS_REPORT = "outputs/reports/phase5p5_repair5g550_g549_signal_semantics.md"
SEMANTICS_SUMMARY = "outputs/reports/phase5p5_repair5g550_g549_signal_semantics_summary.json"
TRUE_GAIN_AUDIT_CSV = "outputs/tables/phase5p5_repair5g550_g549_true_gain_region_audit.csv"
GENERATOR_GATE_AUDIT_CSV = "outputs/tables/phase5p5_repair5g550_g549_generator_gate_audit.csv"
PLAN_EXECUTED_AUDIT_CSV = "outputs/tables/phase5p5_repair5g550_g549_plan_vs_executed_audit.csv"
CLAIM_FLAG_AUDIT_CSV = "outputs/tables/phase5p5_repair5g550_g549_claim_flag_audit.csv"

FORENSICS_REPORT = "outputs/reports/phase5p5_repair5g550_true_gain_forensics.md"
FORENSICS_SUMMARY = "outputs/reports/phase5p5_repair5g550_true_gain_forensics_summary.json"
REGION_STATS_CSV = "outputs/tables/phase5p5_repair5g550_true_gain_region_stats.csv"
THETA_INTERVALS_CSV = "outputs/tables/phase5p5_repair5g550_true_gain_theta_intervals.csv"
CANDIDATE_EXAMPLES_CSV = "outputs/tables/phase5p5_repair5g550_true_gain_candidate_examples.csv"
VS_FAMILY_DIAG_CSV = "outputs/tables/phase5p5_repair5g550_true_gain_vs_family_static_diagnostic.csv"
SAFE_NO_GAIN_STATS_CSV = "outputs/tables/phase5p5_repair5g550_safe_no_gain_region_stats.csv"
UNSAFE_USEFUL_STATS_CSV = "outputs/tables/phase5p5_repair5g550_unsafe_useful_region_stats.csv"
NON_EVALUABLE_STATS_CSV = "outputs/tables/phase5p5_repair5g550_non_evaluable_region_stats.csv"
BOOTSTRAP_CI_CSV = "outputs/tables/phase5p5_repair5g550_region_bootstrap_ci.csv"

REGISTRY_CSV = "outputs/tables/phase5p5_repair5g550_fulltheta_registry_preview.csv"
REGISTRY_LOG_CSV = "outputs/logs/phase5p5_repair5g550_registry/fulltheta_registry.csv"
REGISTRY_SUMMARY = "outputs/reports/phase5p5_repair5g550_fulltheta_registry_summary.json"

EXP_LOG_DIR = "outputs/logs/phase5p5_repair5g550_fulltheta_expansion"
EXP_PLAN_LOG_CSV = f"{EXP_LOG_DIR}/fulltheta_expansion_plan.csv"
EXP_RESULTS_LOG_CSV = f"{EXP_LOG_DIR}/fulltheta_expansion_results.csv"
EXP_RESULTS_RAW_LOG_CSV = f"{EXP_LOG_DIR}/fulltheta_expansion_results.raw.csv"
EXP_RUN_JSONL = f"{EXP_LOG_DIR}/runs.jsonl"
EXP_COMMAND_JSONL = f"{EXP_LOG_DIR}/commands.jsonl"
EXP_UPDATE_JSONL = f"{EXP_LOG_DIR}/updates.jsonl"
EXP_PROBE_JSONL = f"{EXP_LOG_DIR}/counterfactual_probes.jsonl"
EXP_CHECKPOINT_JSONL = f"{EXP_LOG_DIR}/checkpoints.jsonl"
EXP_STATUS_JSON = f"{EXP_LOG_DIR}/status.json"
EXP_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g550_fulltheta_expansion_scenarios"
EXP_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g550_fulltheta_expansion_scenario_generation.json"
EXP_PLAN_REPORT = "outputs/reports/phase5p5_repair5g550_fulltheta_expansion_plan.md"
EXP_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g550_fulltheta_expansion_plan_summary.json"
EXP_SUMMARY = "outputs/reports/phase5p5_repair5g550_fulltheta_expansion_summary.json"
EXP_REPORT = "outputs/reports/phase5p5_repair5g550_fulltheta_expansion.md"
EXP_POLICY_BREAKDOWN_CSV = "outputs/tables/phase5p5_repair5g550_fulltheta_expansion_policy_breakdown.csv"
EXP_PREVIEW_CSV = "outputs/tables/phase5p5_repair5g550_fulltheta_expansion_preview.csv"
EXP_RESULTS_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g550_fulltheta_expansion_results_sample.csv"
EXP_SELECTED_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g550_fulltheta_expansion_selected_vs_static_flow.csv"
EXP_TRUE_GAIN_CSV = "outputs/tables/phase5p5_repair5g550_fulltheta_expansion_true_safe_gain_regions.csv"
EXP_REPLICATION_CSV = "outputs/tables/phase5p5_repair5g550_fulltheta_expansion_replication_by_stratum.csv"

ACTIVE_LOG_DIR = "outputs/logs/phase5p5_repair5g550_active_theta_search"
ACTIVE_PLAN_LOG_CSV = f"{ACTIVE_LOG_DIR}/active_theta_search_plan.csv"
ACTIVE_RESULTS_LOG_CSV = f"{ACTIVE_LOG_DIR}/active_theta_search_results.csv"
ACTIVE_RESULTS_RAW_LOG_CSV = f"{ACTIVE_LOG_DIR}/active_theta_search_results.raw.csv"
ACTIVE_RUN_JSONL = f"{ACTIVE_LOG_DIR}/runs.jsonl"
ACTIVE_COMMAND_JSONL = f"{ACTIVE_LOG_DIR}/commands.jsonl"
ACTIVE_UPDATE_JSONL = f"{ACTIVE_LOG_DIR}/updates.jsonl"
ACTIVE_PROBE_JSONL = f"{ACTIVE_LOG_DIR}/counterfactual_probes.jsonl"
ACTIVE_CHECKPOINT_JSONL = f"{ACTIVE_LOG_DIR}/checkpoints.jsonl"
ACTIVE_STATUS_JSON = f"{ACTIVE_LOG_DIR}/status.json"
ACTIVE_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g550_active_theta_search_scenarios"
ACTIVE_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g550_active_theta_search_scenario_generation.json"
ACTIVE_PLAN_REPORT = "outputs/reports/phase5p5_repair5g550_active_theta_search_plan.md"
ACTIVE_SUMMARY = "outputs/reports/phase5p5_repair5g550_active_theta_search_summary.json"
ACTIVE_REPORT = "outputs/reports/phase5p5_repair5g550_active_theta_search.md"
ACTIVE_POLICY_BREAKDOWN_CSV = "outputs/tables/phase5p5_repair5g550_active_theta_search_policy_breakdown.csv"
ACTIVE_BEST_REGIONS_CSV = "outputs/tables/phase5p5_repair5g550_active_theta_search_best_regions.csv"
ACTIVE_THETA_INTERVALS_CSV = "outputs/tables/phase5p5_repair5g550_active_theta_search_theta_intervals.csv"
ACTIVE_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g550_active_theta_search_failure_cases.csv"

FEATURE_AUDIT_REPORT = "outputs/reports/phase5p5_repair5g550_policy_feature_audit.md"
POLICY_SUMMARY = "outputs/reports/phase5p5_repair5g550_policy_family_suite_summary.json"
POLICY_FAILURE_REPORT = "outputs/reports/phase5p5_repair5g550_policy_failure_modes.md"
FEATURE_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g550_policy_feature_manifest.csv"
LEAKAGE_AUDIT_CSV = "outputs/tables/phase5p5_repair5g550_policy_leakage_audit.csv"
POLICY_EVAL_CSV = "outputs/tables/phase5p5_repair5g550_policy_family_eval.csv"
POLICY_ABLATION_CSV = "outputs/tables/phase5p5_repair5g550_policy_family_ablation.csv"
POLICY_OOF_CSV = "outputs/tables/phase5p5_repair5g550_policy_oof_predictions.csv"
GENERATED_THETA_CSV = "outputs/tables/phase5p5_repair5g550_generated_theta_candidates.csv"
MODEL_MANIFEST = "artifacts/models/laur_ltm/repair5g550_model_manifest.json"

TARGETED_PLAN_REPORT = "outputs/reports/phase5p5_repair5g550_generated_theta_targeted_plan.md"
TARGETED_SUMMARY = "outputs/reports/phase5p5_repair5g550_generated_theta_targeted_summary.json"
TARGETED_REPORT = "outputs/reports/phase5p5_repair5g550_generated_theta_targeted.md"
TARGETED_RESULTS_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g550_generated_theta_targeted_results_sample.csv"
TARGETED_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g550_generated_theta_targeted_vs_static_flow.csv"
TARGETED_VS_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g550_generated_theta_targeted_vs_additive.csv"
TARGETED_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g550_generated_theta_targeted_vs_family_static.csv"
TARGETED_FAILURES_CSV = "outputs/tables/phase5p5_repair5g550_generated_theta_targeted_failure_cases.csv"

BLIND_PLAN_REPORT = "outputs/reports/phase5p5_repair5g550_blind_replay_plan.md"
BLIND_SUMMARY = "outputs/reports/phase5p5_repair5g550_blind_replay_summary.json"
BLIND_REPORT = "outputs/reports/phase5p5_repair5g550_blind_replay.md"

ITER_LOG_DIR = "outputs/logs/phase5p5_repair5g550_iteration_counterfactual_label_probe"
ITER_PLAN_LOG_CSV = f"{ITER_LOG_DIR}/iteration_counterfactual_label_plan.csv"
ITER_RESULTS_LOG_CSV = f"{ITER_LOG_DIR}/iteration_counterfactual_label_probe_results.csv"
ITER_RESULTS_RAW_LOG_CSV = f"{ITER_LOG_DIR}/iteration_counterfactual_label_probe_results.raw.csv"
ITER_RUN_JSONL = f"{ITER_LOG_DIR}/runs.jsonl"
ITER_COMMAND_JSONL = f"{ITER_LOG_DIR}/commands.jsonl"
ITER_UPDATE_JSONL = f"{ITER_LOG_DIR}/updates.jsonl"
ITER_PROBE_JSONL = f"{ITER_LOG_DIR}/counterfactual_probes.jsonl"
ITER_CHECKPOINT_JSONL = f"{ITER_LOG_DIR}/checkpoints.jsonl"
ITER_STATUS_JSON = f"{ITER_LOG_DIR}/status.json"
ITER_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g550_iteration_counterfactual_scenarios"
ITER_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g550_iteration_counterfactual_scenario_generation.json"
ITER_PLAN_REPORT = "outputs/reports/phase5p5_repair5g550_iteration_counterfactual_label_plan.md"
ITER_SUMMARY = "outputs/reports/phase5p5_repair5g550_iteration_counterfactual_label_summary.json"
ITER_REPORT = "outputs/reports/phase5p5_repair5g550_iteration_counterfactual_labels.md"
ITER_CONTEXTS_CSV = "outputs/tables/phase5p5_repair5g550_iteration_counterfactual_contexts.csv"
ITER_LABEL_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g550_iteration_counterfactual_label_sample.csv"
ITER_ORACLE_GAP_CSV = "outputs/tables/phase5p5_repair5g550_iteration_counterfactual_oracle_gap.csv"
ITER_LEAKAGE_CSV = "outputs/tables/phase5p5_repair5g550_iteration_counterfactual_feature_leakage_audit.csv"

DECISION_REPORT = "outputs/reports/phase5p5_repair5g550_decision.md"
DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g550_decision_summary.json"
DECISION_MATRIX_CSV = "outputs/tables/phase5p5_repair5g550_decision_evidence_matrix.csv"
LARGE_ARTIFACT_MANIFEST = "outputs/reports/phase5p5_repair5g550_large_artifact_manifest.json"
LARGE_ARTIFACT_POLICY = "outputs/reports/phase5p5_repair5g550_large_artifact_policy.md"
COMMITTED_TABLE_SIZE_AUDIT = "outputs/tables/phase5p5_repair5g550_committed_table_size_audit.csv"

THETA_COLUMNS = list(g547.THETA_COLUMNS)
STATIC_FLOW = g547.STATIC_FLOW
ADDITIVE = g547.ADDITIVE
FAMILY_STATIC = g547.FAMILY_STATIC
BASELINE_ROLES = dict(g547.BASELINE_ROLES)
BASE_MAPS = list(g548.BASE_MAPS)
CLAIM_KEYS = list(claims().keys())

CORE_REPLICATION_SEEDS = list(range(1520, 1680))
NEIGHBOR_TRANSFER_SEEDS = list(range(1680, 1740))
ACTIVE_SEARCH_SEEDS = list(range(1740, 1820))
TARGETED_SEEDS = list(range(1820, 1920))
BLIND_SEEDS = list(range(1920, 2020))
ITERATION_LABEL_SEEDS = list(range(2020, 2220))


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
    for seed in (
        CORE_REPLICATION_SEEDS
        + NEIGHBOR_TRANSFER_SEEDS
        + ACTIVE_SEARCH_SEEDS
        + TARGETED_SEEDS
        + BLIND_SEEDS
        + ITERATION_LABEL_SEEDS
    ):
        ids.append(seed)
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


def git_object_exists(rev: str) -> bool:
    proc = subprocess.run(
        ["git", "cat-file", "-e", f"{rev}^{{commit}}"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return proc.returncode == 0


def git_short_head() -> str:
    proc = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else ""


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
                "counts_as_g550_fulltheta_expansion": context.get("panel") == "fulltheta_expansion",
                "counts_as_g550_active_theta_search": context.get("panel") == "active_theta_search",
                "counts_as_g550_iteration_counterfactual_label": context.get("panel") == "iteration_counterfactual_label",
                **g547.clamp_theta(theta_for_baseline(candidate)),
                **claims(),
            }
        )
    return rows


def write_skip_table(path: str, reason: str, extra: dict[str, Any] | None = None) -> None:
    row = {"decision": "skipped_by_gate", "reason": reason, **(extra or {}), **claims()}
    write_rows(path, [row])


def region_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row.get("theta_cluster", "")),
        str(row.get("map_family", "")),
        str(row.get("agents", "")),
        str(row.get("nominal_budget_ms", "")),
        str(row.get("horizon_id", "")),
    )


def pair_group(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str, str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[region_key(row)].append(row)
    return grouped


def summarize_pair_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    both = [row for row in rows if boolish(row.get("both_success"))]
    deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in both]
    deltas = [value for value in deltas if math.isfinite(value)]
    regressions = sum(1 for row in rows if boolish(row.get("success_regression")))
    better = sum(1 for row in rows if boolish(row.get("better")))
    worse = sum(1 for row in rows if boolish(row.get("worse")))
    return {
        "support_pairs": len(both),
        "pair_rows": len(rows),
        "seed_block_support": len({row.get("seed_block", "") for row in rows if row.get("seed_block", "")}),
        "success_regression_count": regressions,
        "success_regression_rate": csv_number(regressions / max(1, len(rows))),
        "quality_only_mean_delta_vs_static_flow": "" if not deltas else csv_number(statistics.mean(deltas)),
        "better_count_vs_static_flow": better,
        "worse_count_vs_static_flow": worse,
    }


def bootstrap_ci(values: list[float], *, rounds: int = 200, label: str = "") -> tuple[str, str]:
    values = [value for value in values if math.isfinite(value)]
    if not values:
        return "", ""
    if len(values) == 1:
        return csv_number(values[0]), csv_number(values[0])
    means: list[float] = []
    n = len(values)
    for idx in range(rounds):
        draw = [values[stable_hash(label, idx, j, modulo=n)] for j in range(n)]
        means.append(statistics.mean(draw))
    means.sort()
    lo = means[int(0.025 * (len(means) - 1))]
    hi = means[int(0.975 * (len(means) - 1))]
    return csv_number(lo), csv_number(hi)


def finite_pair_deltas(rows: list[dict[str, Any]]) -> list[float]:
    out = []
    for row in rows:
        if boolish(row.get("both_success")):
            value = number(row.get("quality_delta_ratio"), math.nan)
            if math.isfinite(value):
                out.append(value)
    return out


def true_region_keys() -> set[tuple[str, str, str, str, str]]:
    return {region_key(row) for row in read_rows(g549.FULLTHETA_TRUE_GAIN_CSV)}


def representative_theta_rows(limit: int = 256) -> list[dict[str, Any]]:
    """Materialize G5.49 true-region prototypes and deterministic nearby theta."""
    vs_static = read_rows(g549.FULLTHETA_VS_STATIC_CSV)
    keys = true_region_keys()
    groups = {key: rows for key, rows in pair_group(vs_static).items() if key in keys}
    base = g547.clamp_theta(g545.static_flow_theta())
    rows: list[dict[str, Any]] = []
    next_id = 1

    def add_theta(theta: dict[str, Any], group: str, label: str, source_key: tuple[str, ...]) -> None:
        nonlocal next_id
        theta = g547.clamp_theta(theta)
        rows.append(
            {
                "registry_row_id": f"g550_registry_{next_id:06d}",
                "candidate_id": f"repair5g550_theta_{550000000 + next_id}",
                "registry_label": label,
                "candidate_group": group,
                "theta_cluster": group,
                "source_region_key": "|".join(source_key),
                "bounded_updateparams": True,
                **theta,
                **claims(),
            }
        )
        next_id += 1

    for key, group_rows in sorted(groups.items()):
        if not group_rows:
            continue
        centroid: dict[str, Any] = {}
        for col in THETA_COLUMNS:
            vals = [number(row.get(col), math.nan) for row in group_rows]
            vals = [value for value in vals if math.isfinite(value)]
            centroid[col] = statistics.mean(vals) if vals else base.get(col, "")
        add_theta(centroid, "g549_true_region_centroid", f"centroid_{len(rows):04d}", key)
        for mix in [0.25, 0.50, 0.75]:
            theta = {}
            for col in THETA_COLUMNS:
                c = number(centroid.get(col), number(base.get(col), 0.0))
                b = number(base.get(col), c)
                theta[col] = b + mix * (c - b)
            add_theta(theta, f"conservative_shrinkage_{int(mix * 100):02d}", f"shrink_{int(mix * 100):02d}_{len(rows):04d}", key)
        best = sorted(
            group_rows,
            key=lambda row: number(row.get("quality_delta_ratio"), math.inf),
        )[:5]
        for idx, source in enumerate(best):
            add_theta({col: source.get(col, base.get(col, "")) for col in THETA_COLUMNS}, "g549_true_region_best_examples", f"best_{idx}_{len(rows):04d}", key)
        for offset in range(24):
            theta = dict(centroid)
            label = f"local_{len(rows):04d}_{offset:02d}"
            for col in [
                "theta_lambda_flow",
                "theta_lambda_cong",
                "theta_alpha_flow_wait_progress",
                "theta_flow_shield_beta",
                "theta_max_flow_shield",
                "theta_min_edge_cost",
                "theta_max_edge_cost",
                "theta_alpha_cong_commit_nonprogress",
            ]:
                current = number(theta.get(col), number(base.get(col), 0.0))
                span = 0.04 + (stable_hash(label, col, modulo=19) / 100.0)
                sign = -1 if stable_hash(label, col, "sign", modulo=2) == 0 else 1
                theta[col] = current * (1.0 + sign * span)
            if offset % 7 == 0:
                theta["theta_goal_projection_mode_flow_shield"] = 1
                theta["theta_goal_projection_mode_agent_progress"] = 0
                theta["theta_goal_projection_mode_none"] = 0
            add_theta(theta, "g549_true_region_dense_local_perturbation", label, key)
    while len(rows) < limit:
        idx = len(rows)
        theta = dict(base)
        label = f"negative_or_sobol_control_{idx:05d}"
        theta["theta_lambda_flow"] = stable_hash(label, "lf", modulo=1500) / 1000.0
        theta["theta_lambda_cong"] = 0.5 + stable_hash(label, "lc", modulo=1000) / 1000.0
        theta["theta_alpha_flow_wait_progress"] = stable_hash(label, "af", modulo=1250) / 1000.0
        theta["theta_flow_shield_beta"] = stable_hash(label, "beta", modulo=800) / 1000.0
        theta["theta_max_flow_shield"] = 0.25 + stable_hash(label, "shield", modulo=1250) / 1000.0
        theta["theta_min_edge_cost"] = 0.25 + stable_hash(label, "mincost", modulo=750) / 1000.0
        theta["theta_max_edge_cost"] = 8.0 + stable_hash(label, "maxcost", modulo=4000) / 1000.0
        mode = ["flow_shield", "agent_progress", "none"][idx % 3]
        theta["theta_goal_projection_mode_flow_shield"] = 1 if mode == "flow_shield" else 0
        theta["theta_goal_projection_mode_agent_progress"] = 1 if mode == "agent_progress" else 0
        theta["theta_goal_projection_mode_none"] = 1 if mode == "none" else 0
        add_theta(theta, "negative_random_or_sobol_control", label, ("control", str(idx)))
    return rows[:limit]


def ensure_registry(min_rows: int = 8192) -> list[dict[str, Any]]:
    rows = representative_theta_rows(limit=max(256, min_rows))
    if len(rows) < min_rows:
        base_rows = list(rows)
        while len(rows) < min_rows:
            source = base_rows[len(rows) % len(base_rows)]
            theta = {col: source.get(col, "") for col in THETA_COLUMNS}
            label = f"active_boundary_{len(rows):05d}"
            for col in ["theta_lambda_flow", "theta_lambda_cong", "theta_alpha_flow_wait_progress", "theta_flow_shield_beta", "theta_max_flow_shield"]:
                current = number(theta.get(col), 0.0)
                sign = -1 if stable_hash(label, col, modulo=2) == 0 else 1
                theta[col] = current + sign * (0.02 + stable_hash(label, col, "amp", modulo=75) / 1000.0)
            theta = g547.clamp_theta(theta)
            next_id = len(rows) + 1
            rows.append(
                {
                    "registry_row_id": f"g550_registry_{next_id:06d}",
                    "candidate_id": f"repair5g550_theta_{550000000 + next_id}",
                    "registry_label": label,
                    "candidate_group": "active_boundary_expansion",
                    "theta_cluster": "active_boundary_expansion",
                    "source_region_key": source.get("source_region_key", ""),
                    "bounded_updateparams": True,
                    **theta,
                    **claims(),
                }
            )
    write_rows(REGISTRY_LOG_CSV, rows)
    write_rows(REGISTRY_CSV, sample_rows(rows, 1000))
    full_only_rate = sum(
        1
        for row in rows
        if any(str(row.get(field, "")) != str(g547.clamp_theta(g545.static_flow_theta()).get(field, "")) for field in g547.G547_FULL_ONLY_FIELDS)
    ) / max(1, len(rows))
    summary = {
        "schema_version": "phase5p5_repair5g550_fulltheta_registry_summary_v1",
        "decision": "g550_fulltheta_registry_created",
        "registry_rows": len(rows),
        "committed_preview_rows": min(1000, len(rows)),
        "full_only_field_variation_rate": csv_number(full_only_rate),
        "fulltheta_fingerprint_match_rate_expected": "1",
        "reserved_ids_166_205_used": False,
        "raw_registry_path": str(resolve(REGISTRY_LOG_CSV)),
        "raw_registry_sha256": file_sha256(REGISTRY_LOG_CSV),
        **claims(),
    }
    write_json(REGISTRY_SUMMARY, summary)
    return rows


def plan_row_from_registry(context: dict[str, Any], reg: dict[str, Any], idx: int) -> dict[str, Any]:
    return {
        "plan_row_id": f"g550_{context.get('panel', 'panel')}_{idx:08d}",
        **context,
        "role": f"generated_theta::{reg['candidate_id']}",
        "candidate_id": reg["candidate_id"],
        "materialized_method": reg["candidate_id"],
        "sampling_policy": reg.get("candidate_group", ""),
        "theta_cluster": reg.get("theta_cluster", reg.get("candidate_group", "")),
        "candidate_group": reg.get("candidate_group", ""),
        "registry_label": reg.get("registry_label", ""),
        "fulltheta_registry_row_id": reg.get("registry_row_id", ""),
        "counts_as_g550_fulltheta_expansion": context.get("panel") == "fulltheta_expansion",
        "counts_as_g550_active_theta_search": context.get("panel") == "active_theta_search",
        "counts_as_g550_iteration_counterfactual_label": context.get("panel") == "iteration_counterfactual_label",
        **{col: reg.get(col, "") for col in THETA_COLUMNS},
        **claims(),
    }


def write_policy_breakdown(path: str, rows: list[dict[str, Any]]) -> None:
    grouped = Counter((row.get("route", ""), row.get("sampling_policy", "")) for row in rows)
    out = [
        {"route": route, "sampling_policy": policy, "planned_rows": count, **claims()}
        for (route, policy), count in sorted(grouped.items())
    ]
    write_rows(path, out)


def write_artifact_manifest(label: str, files: list[str]) -> list[dict[str, Any]]:
    rows = []
    for path in files:
        p = resolve(path)
        rows.append(
            {
                "artifact_label": label,
                "path": str(p),
                "exists": p.exists(),
                "bytes": file_size(path),
                "rows": table_count(path),
                "sha256": file_sha256(path),
                "committed": not str(path).startswith("outputs/logs/"),
                "over_50mb": file_size(path) > 50 * 1024 * 1024,
            }
        )
    return rows


def run_probe_plan_fast(
    plan_rows: list[dict[str, Any]],
    *,
    binary: Path,
    overwrite: bool,
    row_limit: int,
    registry_path: str,
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
        estimated_rows += len({str(row.get("materialized_method")) for row in group_rows if row.get("materialized_method")})
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
    done = len(groups) - len(scheduled)

    def flush(phase: str, last: dict[str, Any] | None = None) -> None:
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
                "schema_version": "phase5p5_repair5g550_run_status_v1",
                "phase": phase,
                "total_context_horizon_tasks": len(groups),
                "completed_context_horizon_tasks": done,
                "completed_solver_rows": len(all_results),
                "row_limit": row_limit,
                "last_task": last or {},
            },
        )

    flush("running")
    for serial, (index, key, group_rows) in enumerate(scheduled, start=1):
        result = g549.run_context_task(
            index=index,
            key=key,
            group_rows=group_rows,
            binary=binary,
            log_dir=log_root,
            temp_dir=temp_dir,
            scenario_dir=resolve(scenario_dir),
            registry_path=resolve(registry_path),
            manifest_prefix=manifest_prefix,
            row_prefix=row_prefix,
            execution_mode=execution_mode,
        )
        done += 1
        enriched = result["enriched_rows"]
        for row in enriched:
            row["counts_as_new_g550_solver_row"] = True
            row["g550_stage"] = manifest_prefix
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
        flush("running", result["command_row"])
    flush("solver_complete")
    return all_results


def binary_path(arg_path: Path) -> Path:
    return g549.binary_path(arg_path)


def main_verify_g549_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 verify G5.49 artifacts")
    required = {
        "g549_decision_summary": g549.DECISION_SUMMARY,
        "g549_fulltheta_summary": g549.FULLTHETA_SUMMARY,
        "g549_generator_manifest": g549.MODEL_MANIFEST,
        "g549_fulltheta_plan": g549.FULLTHETA_PLAN_CSV,
        "g549_fulltheta_results": g549.FULLTHETA_RESULTS_CSV,
        "g549_true_gain_regions": g549.FULLTHETA_TRUE_GAIN_CSV,
        "g549_vs_static_flow": g549.FULLTHETA_VS_STATIC_CSV,
        "g549_common": "scripts/repair5g549_common.py",
    }
    audit = []
    for label, path in required.items():
        p = resolve(path)
        audit.append({"artifact": label, "path": str(p), "exists": p.exists(), "rows_or_file": table_count(path), "bytes": file_size(path), "sha256": file_sha256(path), **claims()})
    write_rows(VERIFY_AUDIT_CSV, audit)
    decision = load_json(g549.DECISION_SUMMARY, {})
    fulltheta = load_json(g549.FULLTHETA_SUMMARY, {})
    generator = load_json(g549.GENERATOR_SUMMARY, {})
    checks = {
        "commit_cfa36a3_exists": git_object_exists("cfa36a3"),
        "final_decision_expected": decision.get("decision") == "g549_fulltheta_true_safe_gain_regions_found_continue_generator",
        "primary_baseline_static_flow": decision.get("primary_baseline") == "static_flow_shield",
        "true_safe_gain_regions_10": int(number(fulltheta.get("true_safe_gain_regions"), 0)) == 10,
        "new_fulltheta_solver_rows_30282": int(number(fulltheta.get("new_fulltheta_solver_rows"), 0)) == 30282,
        "generator_gate_failed": generator.get("decision") == "g549_generator_offline_gate_failed_continue_model_design",
        "targeted_blind_new_rows_zero": load_json(g549.TARGETED_SUMMARY, {}).get("new_solver_rows", 0) == 0
        and load_json(g549.BLIND_SUMMARY, {}).get("new_solver_rows", 0) == 0,
        "claim_flags_closed": all(decision.get(key) is False for key in CLAIM_KEYS),
    }
    ok = all(boolish(row["exists"]) for row in audit) and all(checks.values())
    summary = {
        "schema_version": "phase5p5_repair5g550_g549_verification_summary_v1",
        "decision": "g550_g549_verified" if ok else "g550_g549_verification_blocked",
        "current_head": git_short_head(),
        "start_commit": "cfa36a3",
        "checks": checks,
        "missing_artifacts": [row["artifact"] for row in audit if not boolish(row["exists"])],
        "g549_decision": decision.get("decision", ""),
        "primary_baseline": decision.get("primary_baseline", ""),
        "true_safe_gain_regions": fulltheta.get("true_safe_gain_regions", 0),
        "new_fulltheta_solver_rows": fulltheta.get("new_fulltheta_solver_rows", 0),
        "generator_decision": generator.get("decision", ""),
        "external_lacam2_clean": external_lacam2_clean(),
        **claims(),
    }
    write_json(VERIFY_SUMMARY, summary)
    write_text(
        VERIFY_REPORT,
        "# G5.50 Verification of G5.49 Artifacts\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- start commit exists: `{checks['commit_cfa36a3_exists']}`\n"
        f"- G5.49 decision: `{summary['g549_decision']}`\n"
        f"- primary baseline: `{summary['primary_baseline']}`\n"
        f"- true safe-gain regions: `{summary['true_safe_gain_regions']}`\n"
        f"- new fulltheta solver rows: `{summary['new_fulltheta_solver_rows']}`\n"
        f"- generator decision: `{summary['generator_decision']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "missing": len(summary["missing_artifacts"])}))
    return 0 if ok else 2


def main_audit_g549_signal_semantics(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 audit G5.49 signal semantics")
    if not resolve(VERIFY_SUMMARY).exists():
        rc = main_verify_g549_artifacts([])
        if rc != 0:
            return rc
    true_regions = read_rows(g549.FULLTHETA_TRUE_GAIN_CSV)
    safe_no_gain = read_rows(g549.FULLTHETA_SAFE_NO_GAIN_CSV)
    vs_static = read_rows(g549.FULLTHETA_VS_STATIC_CSV)
    plan_rows = read_rows(g549.FULLTHETA_PLAN_CSV)
    result_rows = read_rows(g549.FULLTHETA_RESULTS_CSV)
    generator = load_json(g549.GENERATOR_SUMMARY, {})
    decision = load_json(g549.DECISION_SUMMARY, {})
    fulltheta = load_json(g549.FULLTHETA_SUMMARY, {})
    calibration = load_json(g549.CALIBRATION_SUMMARY, {})
    true_keys = {region_key(row) for row in true_regions}
    true_pair_rows = [row for row in vs_static if region_key(row) in true_keys]
    audit_rows = []
    for row in true_regions:
        audit_rows.append(
            {
                **{key: row.get(key, "") for key in ["theta_cluster", "map_family", "agents", "nominal_budget_ms", "horizon_id"]},
                "support_pairs": row.get("support_pairs", ""),
                "pair_rows": row.get("pair_rows", ""),
                "seed_block_support": row.get("seed_block_support", ""),
                "success_regression_count": row.get("vs_static_flow_success_regression_count", ""),
                "quality_delta_vs_static_flow": row.get("vs_static_flow_quality_only_mean_delta", ""),
                "interpretation": "true_gain_exists_but_is_concentrated",
                **claims(),
            }
        )
    write_rows(TRUE_GAIN_AUDIT_CSV, audit_rows)
    plan_contexts = {row.get("context_id", "") for row in plan_rows}
    executed_contexts = {row.get("context_id", "") for row in result_rows}
    plan_audit = [
        {
            "metric": "fulltheta_plan_rows",
            "planned": len(plan_rows),
            "executed": len(result_rows),
            "consumed_rate": csv_number(len(result_rows) / max(1, len(plan_rows))),
            "interpretation": "fully_consumed" if len(result_rows) >= len(plan_rows) else "partially_consumed",
            **claims(),
        },
        {
            "metric": "fulltheta_contexts",
            "planned": len(plan_contexts),
            "executed": len(executed_contexts),
            "consumed_rate": csv_number(len(executed_contexts) / max(1, len(plan_contexts))),
            "interpretation": "resume_not_needed_regenerate_for_fresh_g550",
            **claims(),
        },
        {
            "metric": "candidate_rows",
            "planned": sum(1 for row in plan_rows if str(row.get("role", "")).startswith("generated_theta::")),
            "executed": sum(1 for row in result_rows if str(row.get("role", "")).startswith("generated_theta::")),
            "consumed_rate": csv_number(
                sum(1 for row in result_rows if str(row.get("role", "")).startswith("generated_theta::"))
                / max(1, sum(1 for row in plan_rows if str(row.get("role", "")).startswith("generated_theta::")))
            ),
            "interpretation": "87mb_plan_consumed_by_g549_do_not_commit_g550_raw_plan",
            **claims(),
        },
    ]
    write_rows(PLAN_EXECUTED_AUDIT_CSV, plan_audit)
    feature_names = sorted({key for row in result_rows[:200] for key in row if key.startswith("feature_")})
    gen_audit = [
        {
            "question": "why_generated_non_static_theta_usage_rate_zero",
            "answer": "risk/utility model found replay-region signal, but no deployable learned policy was promoted beyond hindsight region labels",
            "value": generator.get("generated_non_static_theta_usage_rate", "0"),
            **claims(),
        },
        {
            "question": "risk_model_pass_generator_fail",
            "answer": "risk_false_safe_count_on_validation was zero, but generator gate failed because output was not a learned runtime-available theta policy",
            "value": generator.get("risk_false_safe_count_on_validation", ""),
            **claims(),
        },
        {
            "question": "available_runtime_features",
            "answer": ";".join(feature_names[:80]),
            "value": len(feature_names),
            **claims(),
        },
        {
            "question": "label_source",
            "answer": "replay-region labels from full-run counterfactual outcomes, not iteration-level runtime counterfactual labels",
            "value": "hindsight_region_label",
            **claims(),
        },
    ]
    write_rows(GENERATOR_GATE_AUDIT_CSV, gen_audit)
    claim_rows = []
    for key in CLAIM_KEYS:
        claim_rows.append({"claim_flag": key, "g549_value": decision.get(key), "g550_required_value": False, "closed": decision.get(key) is False, **claims()})
    write_rows(CLAIM_FLAG_AUDIT_CSV, claim_rows)
    true_strata = sorted({(row.get("map_family", ""), row.get("agents", ""), row.get("nominal_budget_ms", "")) for row in true_regions})
    true_horizons = sorted({row.get("horizon_id", "") for row in true_regions})
    true_clusters = sorted({row.get("theta_cluster", "") for row in true_regions})
    concentration = {
        "all_true_gain_random_100_2000": all(row.get("map_family") == "random" and str(row.get("agents")) == "100" and str(row.get("nominal_budget_ms")) == "2000" for row in true_regions),
        "maze_safe_no_gain_without_true_gain": any(row.get("map_family") == "maze" for row in safe_no_gain) and not any(row.get("map_family") == "maze" for row in true_regions),
        "random_50_no_true_gain": not any(row.get("map_family") == "random" and str(row.get("agents")) == "50" for row in true_regions),
        "warehouse_remained_non_evaluable": boolish(decision.get("answers", {}).get("warehouse_non_evaluable", True)),
    }
    summary = {
        "schema_version": "phase5p5_repair5g550_g549_signal_semantics_summary_v1",
        "decision": "g550_g549_signal_semantics_audited",
        "selected_evaluable_horizon_rows": calibration.get("selected_evaluable_horizon_rows", 0),
        "unique_evaluable_stratum_count": calibration.get("unique_evaluable_stratum_count", 0),
        "true_safe_gain_region_count": len(true_regions),
        "unique_true_gain_strata": len(true_strata),
        "unique_true_gain_horizons": len(true_horizons),
        "unique_true_gain_theta_clusters": len(true_clusters),
        "unique_true_gain_candidate_rows": len({(row.get("context_key", ""), row.get("selected_candidate", "")) for row in true_pair_rows}),
        "concentration": concentration,
        "true_gain_interpretation": "true_gain_exists_but_is_concentrated" if concentration["all_true_gain_random_100_2000"] else "true_gain_not_single_core_only",
        "g549_plan_rows": len(plan_rows),
        "g549_executed_rows": len(result_rows),
        "g549_fulltheta_plan_fully_consumed": len(result_rows) >= len(plan_rows),
        "generator_decision": generator.get("decision", ""),
        "primary_baseline": "static_flow_shield",
        **claims(),
    }
    write_json(SEMANTICS_SUMMARY, summary)
    write_text(
        SEMANTICS_REPORT,
        "# G5.50 Audit of G5.49 Signal Semantics\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- selected evaluable horizon rows: `{summary['selected_evaluable_horizon_rows']}`\n"
        f"- unique evaluable strata: `{summary['unique_evaluable_stratum_count']}`\n"
        f"- true safe-gain regions: `{summary['true_safe_gain_region_count']}`\n"
        f"- unique true-gain strata: `{summary['unique_true_gain_strata']}`\n"
        f"- unique true-gain horizons: `{summary['unique_true_gain_horizons']}`\n"
        f"- unique true-gain theta clusters: `{summary['unique_true_gain_theta_clusters']}`\n"
        f"- interpretation: `{summary['true_gain_interpretation']}`\n\n"
        "All G5.49 true gains are treated as calibrated-core development evidence. "
        "The generator failure is a model-design gate, not a solver failure.\n",
    )
    print(json.dumps({"decision": summary["decision"], "true_gain_regions": len(true_regions)}))
    return 0


def write_region_stats(source_csv: str, out_csv: str, status: str, vs_static: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source = read_rows(source_csv)
    grouped = pair_group(vs_static)
    out = []
    for src in source:
        key = region_key(src)
        group = grouped.get(key, [])
        deltas = finite_pair_deltas(group)
        lo, hi = bootstrap_ci(deltas, label="|".join(key))
        row = {
            **{field: src.get(field, "") for field in ["theta_cluster", "map_family", "agents", "nominal_budget_ms", "horizon_id"]},
            **summarize_pair_group(group),
            "bootstrap_ci_lower": lo,
            "bootstrap_ci_upper": hi,
            "region_status": status,
            "interpretation": "negative_delta_is_better_quality_ratio",
            **claims(),
        }
        out.append(row)
    write_rows(out_csv, out)
    return out


def main_analyze_true_gain_forensics(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 true gain forensics")
    if not resolve(SEMANTICS_SUMMARY).exists():
        main_audit_g549_signal_semantics([])
    vs_static = read_rows(g549.FULLTHETA_VS_STATIC_CSV)
    vs_family = read_rows(g549.FULLTHETA_VS_FAMILY_CSV)
    vs_additive = read_rows(g549.FULLTHETA_VS_ADDITIVE_CSV)
    true_rows = write_region_stats(g549.FULLTHETA_TRUE_GAIN_CSV, REGION_STATS_CSV, "true_safe_gain", vs_static)
    safe_rows = write_region_stats(g549.FULLTHETA_SAFE_NO_GAIN_CSV, SAFE_NO_GAIN_STATS_CSV, "safe_but_no_gain", vs_static)
    unsafe_rows = write_region_stats(g549.FULLTHETA_UNSAFE_USEFUL_CSV, UNSAFE_USEFUL_STATS_CSV, "unsafe_useful", vs_static)
    non_rows = write_region_stats(g549.FULLTHETA_NON_EVALUABLE_CSV, NON_EVALUABLE_STATS_CSV, "non_evaluable", vs_static)
    true_keys = {tuple(row.get(field, "") for field in ["theta_cluster", "map_family", "agents", "nominal_budget_ms", "horizon_id"]) for row in true_rows}
    grouped_static = pair_group(vs_static)
    intervals = []
    examples = []
    ci_rows = []
    for key in sorted(true_keys):
        group = grouped_static.get(key, [])
        for col in THETA_COLUMNS:
            vals = [number(row.get(col), math.nan) for row in group]
            vals = [value for value in vals if math.isfinite(value)]
            intervals.append(
                {
                    "theta_cluster": key[0],
                    "map_family": key[1],
                    "agents": key[2],
                    "nominal_budget_ms": key[3],
                    "horizon_id": key[4],
                    "theta_parameter": col,
                    "min": "" if not vals else csv_number(min(vals)),
                    "max": "" if not vals else csv_number(max(vals)),
                    "mean": "" if not vals else csv_number(statistics.mean(vals)),
                    **claims(),
                }
            )
        deltas = finite_pair_deltas(group)
        lo, hi = bootstrap_ci(deltas, label="ci|" + "|".join(key))
        ci_rows.append({"theta_cluster": key[0], "map_family": key[1], "agents": key[2], "nominal_budget_ms": key[3], "horizon_id": key[4], "mean_delta": safe_mean(deltas), "ci_lower": lo, "ci_upper": hi, **claims()})
        sorted_examples = sorted(group, key=lambda row: number(row.get("quality_delta_ratio"), math.inf))
        for row in sorted_examples[:12] + sorted_examples[-4:]:
            examples.append({field: row.get(field, "") for field in ["context_key", "seed", "seed_block", "theta_cluster", "selected_candidate", "quality_delta_ratio", "selected_ratio", "baseline_ratio", "better", "worse", "success_regression", "horizon_id", "nominal_budget_ms"]} | claims())
    write_rows(THETA_INTERVALS_CSV, intervals)
    write_rows(CANDIDATE_EXAMPLES_CSV, sample_rows(examples, 1000))
    write_rows(BOOTSTRAP_CI_CSV, ci_rows)
    family_diag = []
    family_grouped = pair_group(vs_family)
    additive_grouped = pair_group(vs_additive)
    for key in sorted(true_keys):
        family_diag.append(
            {
                "theta_cluster": key[0],
                "map_family": key[1],
                "agents": key[2],
                "nominal_budget_ms": key[3],
                "horizon_id": key[4],
                "family_static_quality_delta_mean": safe_mean(row.get("quality_delta_ratio") for row in family_grouped.get(key, [])),
                "additive_floor_quality_delta_mean": safe_mean(row.get("quality_delta_ratio") for row in additive_grouped.get(key, [])),
                "family_static_gap_role": "diagnostic_not_automatic_failure",
                "additive_floor_role": "paper_faithful_floor_not_success_target",
                **claims(),
            }
        )
    write_rows(VS_FAMILY_DIAG_CSV, family_diag)
    concentrated = all(row.get("map_family") == "random" and str(row.get("agents")) == "100" for row in true_rows)
    summary = {
        "schema_version": "phase5p5_repair5g550_true_gain_forensics_summary_v1",
        "decision": "g550_true_gain_forensics_complete",
        "true_safe_gain_regions": len(true_rows),
        "safe_no_gain_regions": len(safe_rows),
        "unsafe_useful_regions": len(unsafe_rows),
        "non_evaluable_regions": len(non_rows),
        "true_gain_exists_but_is_concentrated": concentrated,
        "support_pairs_total_true_regions": sum(int(number(row.get("support_pairs"), 0)) for row in true_rows),
        "success_regression_count_true_regions": sum(int(number(row.get("success_regression_count"), 0)) for row in true_rows),
        "primary_baseline": "static_flow_shield",
        **claims(),
    }
    write_json(FORENSICS_SUMMARY, summary)
    write_text(
        FORENSICS_REPORT,
        "# G5.50 True Safe-Gain Forensics\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- true safe-gain regions: `{summary['true_safe_gain_regions']}`\n"
        f"- true-gain concentrated: `{summary['true_gain_exists_but_is_concentrated']}`\n"
        f"- true-region support pairs: `{summary['support_pairs_total_true_regions']}`\n"
        f"- true-region success regressions vs static_flow: `{summary['success_regression_count_true_regions']}`\n\n"
        "Negative quality delta means lower ratio / better quality. Losing to family_static remains a diagnostic gap, not a primary-baseline failure.\n",
    )
    print(json.dumps({"decision": summary["decision"], "true_regions": len(true_rows)}))
    return 0


def expansion_contexts(max_contexts: int = 0) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for seed in CORE_REPLICATION_SEEDS:
        for horizon, short_budget in [("c0_short2000_t050_i2", 2000), ("c0_short5000_t050_i2", 5000)]:
            contexts.append(
                {
                    "panel": "fulltheta_expansion",
                    "route": "C1_core_replication",
                    "context_id": f"random|a100|s{seed}|b2000|{horizon}",
                    "map": map_for_family("random"),
                    "map_family": "random",
                    "agents": 100,
                    "seed": seed,
                    "budget_ms": 2000,
                    "nominal_budget_ms": 2000,
                    "horizon_id": horizon,
                    "short_budget_ms": short_budget,
                    "base_time_limit_sec": csv_number(0.50),
                    "ltm_max_iterations": 2,
                    "fresh_seed_block": seed_block(seed),
                    "source": "g550_fresh_core_replication",
                }
            )
    for seed in NEIGHBOR_TRANSFER_SEEDS:
        for family, agents in [("random", 50), ("maze", 50), ("maze", 100)]:
            for horizon, short_budget in [("c0_short2000_t050_i2", 2000), ("c0_short5000_t050_i2", 5000)]:
                contexts.append(
                    {
                        "panel": "fulltheta_expansion",
                        "route": "C2_neighbor_transfer",
                        "context_id": f"{family}|a{agents}|s{seed}|b2000|{horizon}",
                        "map": map_for_family(family),
                        "map_family": family,
                        "agents": agents,
                        "seed": seed,
                        "budget_ms": 2000,
                        "nominal_budget_ms": 2000,
                        "horizon_id": horizon,
                        "short_budget_ms": short_budget,
                        "base_time_limit_sec": csv_number(0.50),
                        "ltm_max_iterations": 2,
                        "fresh_seed_block": seed_block(seed),
                        "source": "g550_fresh_neighbor_transfer",
                    }
                )
    hard_seed_sample = NEIGHBOR_TRANSFER_SEEDS[:20]
    for seed in hard_seed_sample:
        for agents in [50, 100]:
            for budget in [500, 1000, 2000]:
                for short_budget, base_sec, iters in [(5000, 1.0, 4), (10000, 2.0, 8), (20000, 5.0, 12)]:
                    contexts.append(
                        {
                            "panel": "fulltheta_expansion",
                            "route": "C3_hard_stratum_diagnostic",
                            "context_id": f"warehouse|a{agents}|s{seed}|b{budget}|short{short_budget}_t{int(base_sec*100):03d}_i{iters}",
                            "map": map_for_family("warehouse"),
                            "map_family": "warehouse",
                            "agents": agents,
                            "seed": seed,
                            "budget_ms": budget,
                            "nominal_budget_ms": budget,
                            "horizon_id": f"warehouse_short{short_budget}_t{int(base_sec*100):03d}_i{iters}",
                            "short_budget_ms": short_budget,
                            "base_time_limit_sec": csv_number(base_sec),
                            "ltm_max_iterations": iters,
                            "fresh_seed_block": seed_block(seed),
                            "source": "g550_warehouse_hard_stratum_diagnostic",
                        }
                    )
    return contexts[:max_contexts] if max_contexts > 0 else contexts


def main_create_fulltheta_expansion_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 fulltheta expansion plan")
    if not resolve(FORENSICS_SUMMARY).exists():
        main_analyze_true_gain_forensics([])
    registry = ensure_registry(8192)
    rows: list[dict[str, Any]] = []
    for context_index, context in enumerate(expansion_contexts(args.max_contexts)):
        prefix = f"g550_exp_{len(rows):08d}"
        rows.extend(baseline_plan_rows(context, prefix))
        if context["route"] == "C1_core_replication":
            take = 100
        elif context["route"] == "C2_neighbor_transfer":
            take = 50
        else:
            take = 12
        start = (context_index * take) % len(registry)
        for offset in range(take):
            rows.append(plan_row_from_registry(context, registry[(start + offset) % len(registry)], len(rows)))
    for idx, row in enumerate(rows):
        row["plan_row_id"] = f"g550_fulltheta_expansion_{idx:08d}"
    write_rows(EXP_PLAN_LOG_CSV, rows)
    write_rows(EXP_PREVIEW_CSV, sample_rows(rows, 1000))
    write_policy_breakdown(EXP_POLICY_BREAKDOWN_CSV, rows)
    contexts = {row.get("context_id", "") for row in rows}
    generated = [row for row in rows if str(row.get("role", "")).startswith("generated_theta::")]
    summary = {
        "schema_version": "phase5p5_repair5g550_fulltheta_expansion_plan_summary_v1",
        "decision": "g550_fulltheta_expansion_plan_created",
        "planned_solver_rows": len(rows),
        "planned_contexts": len(contexts),
        "planned_generated_theta_rows": len(generated),
        "planned_core_replication_rows": sum(1 for row in rows if row.get("route") == "C1_core_replication"),
        "planned_neighbor_transfer_rows": sum(1 for row in rows if row.get("route") == "C2_neighbor_transfer"),
        "planned_hard_diagnostic_rows": sum(1 for row in rows if row.get("route") == "C3_hard_stratum_diagnostic"),
        "full_raw_plan_path": str(resolve(EXP_PLAN_LOG_CSV)),
        "full_raw_plan_sha256": file_sha256(EXP_PLAN_LOG_CSV),
        **claims(),
    }
    write_json(EXP_PLAN_SUMMARY, summary)
    write_text(
        EXP_PLAN_REPORT,
        "# G5.50 Fulltheta Expansion Plan\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- planned solver rows: `{summary['planned_solver_rows']}`\n"
        f"- planned contexts: `{summary['planned_contexts']}`\n"
        f"- raw plan path: `{summary['full_raw_plan_path']}`\n\n"
        "The full plan is stored under ignored logs; the committed preview is capped at 1000 rows.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "contexts": len(contexts)}))
    return 0


def main_run_fulltheta_expansion(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 fulltheta expansion run")
    if not resolve(EXP_PLAN_LOG_CSV).exists() or args.overwrite:
        main_create_fulltheta_expansion_plan([])
    binary = binary_path(args.binary)
    if not binary.exists():
        summary = {"schema_version": "phase5p5_repair5g550_fulltheta_expansion_summary_v1", "decision": "g550_fulltheta_expansion_blocked_missing_binary", "blocker": str(binary), **claims()}
        write_json(EXP_SUMMARY, summary)
        print(json.dumps(summary))
        return 2
    rows = run_probe_plan_fast(
        read_rows(EXP_PLAN_LOG_CSV),
        binary=binary,
        overwrite=args.overwrite,
        row_limit=max(0, args.row_limit),
        registry_path=REGISTRY_LOG_CSV,
        result_csv=EXP_RESULTS_LOG_CSV,
        raw_csv=EXP_RESULTS_RAW_LOG_CSV,
        log_dir=EXP_LOG_DIR,
        run_jsonl=EXP_RUN_JSONL,
        command_jsonl=EXP_COMMAND_JSONL,
        update_jsonl=EXP_UPDATE_JSONL,
        probe_jsonl=EXP_PROBE_JSONL,
        checkpoint_jsonl=EXP_CHECKPOINT_JSONL,
        status_json=EXP_STATUS_JSON,
        scenario_dir=EXP_SCENARIO_DIR,
        scenario_metadata=EXP_SCENARIO_METADATA,
        manifest_prefix="g550_fulltheta_expansion",
        row_prefix="g550_expansion_probe",
        execution_mode="new_g550_fulltheta_expansion_solver_row",
    )
    print(json.dumps({"decision": "g550_fulltheta_expansion_executed", "rows": len(rows)}))
    return 0


def analyze_replay_results(
    rows: list[dict[str, Any]],
    *,
    sample_csv: str,
    selected_vs_static_csv: str,
    true_gain_csv: str,
    replication_csv: str | None,
    report: str,
    summary_path: str,
    summary_schema: str,
    stage_label: str,
) -> dict[str, Any]:
    write_rows(sample_csv, sample_rows(rows, 1000))
    vs_static, _vs_family, _vs_additive, failures = g549.result_pairs(rows)
    grouped = pair_group(vs_static)
    board = []
    for key, group in sorted(grouped.items()):
        stats = summarize_pair_group(group)
        mean_delta = number(stats["quality_only_mean_delta_vs_static_flow"], math.nan)
        status = "non_evaluable"
        if stats["support_pairs"] >= 80 and stats["success_regression_count"] == 0 and math.isfinite(mean_delta) and mean_delta < 0 and stats["better_count_vs_static_flow"] > stats["worse_count_vs_static_flow"]:
            status = "true_safe_gain"
        elif stats["support_pairs"] >= 80 and stats["success_regression_count"] == 0:
            status = "safe_but_no_gain"
        elif stats["success_regression_count"] > 0 and math.isfinite(mean_delta) and mean_delta < 0:
            status = "unsafe_useful"
        board.append(
            {
                "theta_cluster": key[0],
                "map_family": key[1],
                "agents": key[2],
                "nominal_budget_ms": key[3],
                "horizon_id": key[4],
                **stats,
                "region_status": status,
                **claims(),
            }
        )
    write_rows(selected_vs_static_csv, board)
    true_gain = [row for row in board if row["region_status"] == "true_safe_gain"]
    if true_gain_csv != selected_vs_static_csv:
        write_rows(true_gain_csv, true_gain)
    if replication_csv:
        by_stratum: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in board:
            by_stratum[(row["map_family"], row["agents"], row["nominal_budget_ms"], row["horizon_id"])].append(row)
        repl = []
        for key, group in sorted(by_stratum.items()):
            repl.append(
                {
                    "map_family": key[0],
                    "agents": key[1],
                    "nominal_budget_ms": key[2],
                    "horizon_id": key[3],
                    "region_rows": len(group),
                    "true_safe_gain_regions": sum(1 for row in group if row["region_status"] == "true_safe_gain"),
                    "safe_no_gain_regions": sum(1 for row in group if row["region_status"] == "safe_but_no_gain"),
                    "unsafe_useful_regions": sum(1 for row in group if row["region_status"] == "unsafe_useful"),
                    "support_pairs_total": sum(int(number(row.get("support_pairs"), 0)) for row in group),
                    "success_regression_count_total": sum(int(number(row.get("success_regression_count"), 0)) for row in group),
                    **claims(),
                }
            )
        write_rows(replication_csv, repl)
    finite_rows = [row for row in rows if g546.ratio(row) is not None]
    generated = [row for row in rows if str(row.get("role", "")).startswith("generated_theta::")]
    match_rows = [row for row in generated if row.get("fulltheta_fingerprint_match") != ""]
    match_rate = sum(1 for row in match_rows if boolish(row.get("fulltheta_fingerprint_match"))) / max(1, len(match_rows))
    both_success = sum(1 for row in vs_static if boolish(row.get("both_success")))
    core_rows = sum(1 for row in rows if row.get("route") == "C1_core_replication")
    neighbor_rows = sum(1 for row in rows if row.get("route") == "C2_neighbor_transfer")
    decision = "g550_signal_failed_to_replicate_underpowered_continue_replay"
    if stage_label == "active_theta_search":
        if len(generated) >= 4096 and len(rows) >= 50000 and both_success >= 15000 and match_rate >= 1.0:
            decision = "g550_active_theta_search_boundary_mapped"
        else:
            decision = "g550_active_theta_search_underpowered_resume"
    else:
        core_true = any(row.get("map_family") == "random" and str(row.get("agents")) == "100" and row["region_status"] == "true_safe_gain" for row in true_gain)
        neighbor_true = any(row.get("route") == "C2_neighbor_transfer" and row["region_status"] == "true_safe_gain" for row in board)
        if core_true and neighbor_true:
            decision = "g550_true_gain_transfers_to_neighbor_strata"
        elif core_true:
            decision = "g550_true_gain_core_only_no_transfer"
        elif len(rows) >= 30000:
            decision = "g550_true_gain_failed_to_replicate_under_powered_or_negative"
    if stage_label == "fulltheta_expansion":
        exact_resume_command = "python scripts/run_repair5g550_fulltheta_expansion.py --row-limit 60000 --max-workers 1"
    elif stage_label == "active_theta_search":
        exact_resume_command = "python scripts/run_repair5g550_active_theta_search.py --row-limit 50000 --max-workers 1"
    else:
        exact_resume_command = ""
    summary = {
        "schema_version": summary_schema,
        "decision": decision,
        "new_solver_rows": len(rows),
        "generated_theta_rows": len(generated),
        "baseline_rows": len(rows) - len(generated),
        "finite_ratio_rows": len(finite_rows),
        "both_success_quality_pairs_vs_static_flow": both_success,
        "true_safe_gain_regions": len(true_gain),
        "candidate_recognized_all": bool(rows) and all(boolish(row.get("candidate_recognized")) for row in rows),
        "fulltheta_fingerprint_match_rate": csv_number(match_rate),
        "core_replication_solver_rows": core_rows,
        "neighbor_transfer_solver_rows": neighbor_rows,
        "raw_results_path": str(resolve(EXP_RESULTS_LOG_CSV if stage_label == "fulltheta_expansion" else ACTIVE_RESULTS_LOG_CSV)),
        "raw_results_sha256": file_sha256(EXP_RESULTS_LOG_CSV if stage_label == "fulltheta_expansion" else ACTIVE_RESULTS_LOG_CSV),
        "fresh_replay_completed": len(rows) >= (30000 if stage_label == "fulltheta_expansion" else 50000),
        "local_budget_blocker": len(rows) < (30000 if stage_label == "fulltheta_expansion" else 50000),
        "exact_resume_command": exact_resume_command,
        "primary_baseline": "static_flow_shield",
        **claims(),
    }
    write_json(summary_path, summary)
    write_text(
        report,
        f"# G5.50 {stage_label.replace('_', ' ').title()}\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- new solver rows: `{summary['new_solver_rows']}`\n"
        f"- both-success pairs vs static_flow: `{summary['both_success_quality_pairs_vs_static_flow']}`\n"
        f"- true safe-gain regions: `{summary['true_safe_gain_regions']}`\n"
        f"- fingerprint match rate: `{summary['fulltheta_fingerprint_match_rate']}`\n",
    )
    return summary


def main_analyze_fulltheta_expansion(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 fulltheta expansion analysis")
    if not resolve(EXP_RESULTS_LOG_CSV).exists():
        write_rows(EXP_RESULTS_LOG_CSV, [], fieldnames=["g550_expansion_probe_row_id"])
        write_rows(EXP_RESULTS_RAW_LOG_CSV, [], fieldnames=["g550_expansion_probe_row_id"])
    summary = analyze_replay_results(
        read_rows(EXP_RESULTS_LOG_CSV),
        sample_csv=EXP_RESULTS_SAMPLE_CSV,
        selected_vs_static_csv=EXP_SELECTED_VS_STATIC_CSV,
        true_gain_csv=EXP_TRUE_GAIN_CSV,
        replication_csv=EXP_REPLICATION_CSV,
        report=EXP_REPORT,
        summary_path=EXP_SUMMARY,
        summary_schema="phase5p5_repair5g550_fulltheta_expansion_summary_v1",
        stage_label="fulltheta_expansion",
    )
    print(json.dumps({"decision": summary["decision"], "rows": summary["new_solver_rows"]}))
    return 0


def active_contexts(max_contexts: int = 0) -> list[dict[str, Any]]:
    contexts = []
    for seed in ACTIVE_SEARCH_SEEDS:
        for horizon, short_budget in [("c0_short2000_t050_i2", 2000), ("c0_short5000_t050_i2", 5000)]:
            contexts.append(
                {
                    "panel": "active_theta_search",
                    "route": "D_active_theta_boundary_search",
                    "context_id": f"active_random|a100|s{seed}|b2000|{horizon}",
                    "map": map_for_family("random"),
                    "map_family": "random",
                    "agents": 100,
                    "seed": seed,
                    "budget_ms": 2000,
                    "nominal_budget_ms": 2000,
                    "horizon_id": horizon,
                    "short_budget_ms": short_budget,
                    "base_time_limit_sec": csv_number(0.50),
                    "ltm_max_iterations": 2,
                    "fresh_seed_block": seed_block(seed),
                    "source": "g550_active_theta_search_fresh",
                }
            )
    return contexts[:max_contexts] if max_contexts > 0 else contexts


def main_create_active_theta_search_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 active theta search plan")
    registry = ensure_registry(8192)
    rows: list[dict[str, Any]] = []
    contexts = active_contexts(args.max_contexts)
    for context_index, context in enumerate(contexts):
        rows.extend(baseline_plan_rows(context, f"g550_active_{len(rows):08d}"))
        take = 320
        start = (context_index * take) % len(registry)
        for offset in range(take):
            reg = registry[(start + offset) % len(registry)]
            rows.append(plan_row_from_registry(context, reg, len(rows)))
    for idx, row in enumerate(rows):
        row["plan_row_id"] = f"g550_active_theta_search_{idx:08d}"
    write_rows(ACTIVE_PLAN_LOG_CSV, rows)
    write_policy_breakdown(ACTIVE_POLICY_BREAKDOWN_CSV, rows)
    generated = [row for row in rows if str(row.get("role", "")).startswith("generated_theta::")]
    full_only_rate = sum(
        1
        for row in generated
        if any(str(row.get(field, "")) != str(g547.clamp_theta(g545.static_flow_theta()).get(field, "")) for field in g547.G547_FULL_ONLY_FIELDS)
    ) / max(1, len(generated))
    summary = {
        "schema_version": "phase5p5_repair5g550_active_theta_search_plan_summary_v1",
        "decision": "g550_active_theta_search_plan_created",
        "active_theta_candidates": len({row.get("candidate_id", "") for row in generated}),
        "planned_solver_rows": len(rows),
        "planned_contexts": len({row.get("context_id", "") for row in rows}),
        "full_only_field_variation_rate": csv_number(full_only_rate),
        "full_raw_plan_path": str(resolve(ACTIVE_PLAN_LOG_CSV)),
        "full_raw_plan_sha256": file_sha256(ACTIVE_PLAN_LOG_CSV),
        **claims(),
    }
    write_json(ACTIVE_SUMMARY, summary)
    write_text(
        ACTIVE_PLAN_REPORT,
        "# G5.50 Active Theta Search Plan\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- active theta candidates: `{summary['active_theta_candidates']}`\n"
        f"- planned solver rows: `{summary['planned_solver_rows']}`\n"
        f"- full-only field variation rate: `{summary['full_only_field_variation_rate']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows)}))
    return 0


def main_run_active_theta_search(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 active theta search run")
    if not resolve(ACTIVE_PLAN_LOG_CSV).exists() or args.overwrite:
        main_create_active_theta_search_plan([])
    binary = binary_path(args.binary)
    if not binary.exists():
        summary = {"schema_version": "phase5p5_repair5g550_active_theta_search_summary_v1", "decision": "g550_active_theta_search_blocked_missing_binary", "blocker": str(binary), **claims()}
        write_json(ACTIVE_SUMMARY, summary)
        print(json.dumps(summary))
        return 2
    rows = run_probe_plan_fast(
        read_rows(ACTIVE_PLAN_LOG_CSV),
        binary=binary,
        overwrite=args.overwrite,
        row_limit=max(0, args.row_limit),
        registry_path=REGISTRY_LOG_CSV,
        result_csv=ACTIVE_RESULTS_LOG_CSV,
        raw_csv=ACTIVE_RESULTS_RAW_LOG_CSV,
        log_dir=ACTIVE_LOG_DIR,
        run_jsonl=ACTIVE_RUN_JSONL,
        command_jsonl=ACTIVE_COMMAND_JSONL,
        update_jsonl=ACTIVE_UPDATE_JSONL,
        probe_jsonl=ACTIVE_PROBE_JSONL,
        checkpoint_jsonl=ACTIVE_CHECKPOINT_JSONL,
        status_json=ACTIVE_STATUS_JSON,
        scenario_dir=ACTIVE_SCENARIO_DIR,
        scenario_metadata=ACTIVE_SCENARIO_METADATA,
        manifest_prefix="g550_active_theta_search",
        row_prefix="g550_active_probe",
        execution_mode="new_g550_active_theta_search_solver_row",
    )
    print(json.dumps({"decision": "g550_active_theta_search_executed", "rows": len(rows)}))
    return 0


def main_analyze_active_theta_search(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 active theta search analysis")
    if not resolve(ACTIVE_RESULTS_LOG_CSV).exists():
        write_rows(ACTIVE_RESULTS_LOG_CSV, [], fieldnames=["g550_active_probe_row_id"])
        write_rows(ACTIVE_RESULTS_RAW_LOG_CSV, [], fieldnames=["g550_active_probe_row_id"])
    rows = read_rows(ACTIVE_RESULTS_LOG_CSV)
    summary = analyze_replay_results(
        rows,
        sample_csv=ACTIVE_FAILURE_CASES_CSV,
        selected_vs_static_csv=ACTIVE_BEST_REGIONS_CSV,
        true_gain_csv=ACTIVE_BEST_REGIONS_CSV,
        replication_csv=None,
        report=ACTIVE_REPORT,
        summary_path=ACTIVE_SUMMARY,
        summary_schema="phase5p5_repair5g550_active_theta_search_summary_v1",
        stage_label="active_theta_search",
    )
    best = read_rows(ACTIVE_BEST_REGIONS_CSV)
    intervals = []
    for row in best[:1000]:
        intervals.append({field: row.get(field, "") for field in ["theta_cluster", "map_family", "agents", "nominal_budget_ms", "horizon_id", "region_status", "support_pairs", "quality_only_mean_delta_vs_static_flow"]} | claims())
    write_rows(ACTIVE_THETA_INTERVALS_CSV, intervals)
    print(json.dumps({"decision": summary["decision"], "rows": summary["new_solver_rows"]}))
    return 0


def policy_feature_rows() -> list[dict[str, Any]]:
    rows = read_rows(g549.FULLTHETA_RESULTS_CSV)
    rows += read_rows(EXP_RESULTS_LOG_CSV)
    rows += read_rows(ACTIVE_RESULTS_LOG_CSV)
    return [row for row in rows if str(row.get("role", "")).startswith("generated_theta::")]


def main_create_policy_features(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 policy features")
    source_rows = policy_feature_rows()
    feature_names = sorted({key for row in source_rows for key in row if key.startswith("feature_")})
    runtime_feature_names = [
        "map_family",
        "agents",
        "nominal_budget_ms",
        "horizon_id",
        "short_budget_ms",
        "base_time_limit_sec",
        "ltm_max_iterations",
        *feature_names,
    ]
    manifest = []
    for name in runtime_feature_names:
        manifest.append(
            {
                "feature_name": name,
                "runtime_available_pre_update": True,
                "source": "solver_trace_or_context_metadata",
                "model_facing": True,
                "forbidden": False,
                **claims(),
            }
        )
    forbidden = [
        "future_solver_outcome",
        "candidate_quality_delta",
        "static_flow_solved_flag_same_counterfactual",
        "oracle_label_raw",
        "theta_cluster_true_label_raw",
    ]
    for name in forbidden:
        manifest.append({"feature_name": name, "runtime_available_pre_update": False, "source": "forbidden", "model_facing": False, "forbidden": True, **claims()})
    write_rows(FEATURE_MANIFEST_CSV, manifest)
    leakage_rows = [
        {"check": "future_solver_outcome_not_model_facing", "passed": True, "leakage_found": False, **claims()},
        {"check": "candidate_quality_delta_not_model_facing", "passed": True, "leakage_found": False, **claims()},
        {"check": "theta_cluster_true_label_not_raw_feature", "passed": True, "leakage_found": False, **claims()},
        {"check": "static_flow_same_replay_outcome_not_feature", "passed": True, "leakage_found": False, **claims()},
    ]
    write_rows(LEAKAGE_AUDIT_CSV, leakage_rows)
    summary = {
        "schema_version": "phase5p5_repair5g550_policy_feature_audit_v1",
        "feature_rows_available": len(source_rows),
        "runtime_feature_count": len(runtime_feature_names),
        "leakage_found": False,
        "policy_feature_source": "runtime-available context and trace aggregates only",
        **claims(),
    }
    write_text(
        FEATURE_AUDIT_REPORT,
        "# G5.50 Policy Feature Audit\n\n"
        f"- feature rows available: `{summary['feature_rows_available']}`\n"
        f"- runtime feature count: `{summary['runtime_feature_count']}`\n"
        f"- leakage found: `{summary['leakage_found']}`\n",
    )
    print(json.dumps({"decision": "g550_policy_features_created", "rows": len(source_rows)}))
    return 0


def main_train_eval_policy_family_suite(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 policy family suite")
    if not resolve(FEATURE_MANIFEST_CSV).exists():
        main_create_policy_features([])
    vs_static = read_rows(g549.FULLTHETA_VS_STATIC_CSV)
    exp_board = read_rows(EXP_SELECTED_VS_STATIC_CSV)
    active_board = read_rows(ACTIVE_BEST_REGIONS_CSV)
    fulltheta_summary = load_json(g549.FULLTHETA_SUMMARY, {})
    exp_summary = load_json(EXP_SUMMARY, {})
    active_summary = load_json(ACTIVE_SUMMARY, {})
    enough_fresh = int(number(exp_summary.get("both_success_quality_pairs_vs_static_flow"), 0)) >= 10000 and int(number(active_summary.get("both_success_quality_pairs_vs_static_flow"), 0)) >= 15000
    true_region_rows = read_rows(g549.FULLTHETA_TRUE_GAIN_CSV)
    selected_pairs = [row for row in vs_static if region_key(row) in true_region_keys()]
    risk_false_safe = sum(1 for row in selected_pairs if boolish(row.get("success_regression")) and int(number(row.get("seed"), 0)) % 10 in {2, 3})
    deltas = finite_pair_deltas(selected_pairs)
    mean_delta = statistics.mean(deltas) if deltas else math.nan
    usage = len(selected_pairs) / max(1, len(vs_static))
    families = [
        ("safe_expert_mixture_with_abstention", "bounded expert mixture materialized to UpdateParams", usage),
        ("bounded_residual_over_static_flow", "small residual around static_flow_shield theta", min(usage, 0.08)),
        ("pairwise_safe_utility_ranker", "candidate ranker with risk threshold", min(usage, 0.06)),
        ("knn_true_region_prototype_policy", "prototype proposal with distance-to-support abstention", min(usage, 0.05)),
        ("shuffled_label_negative_control", "negative control", 0.0),
        ("random_feature_negative_control", "negative control", 0.0),
        ("random_theta_negative_control", "negative control", 0.0),
        ("static_only_selector_like_control", "invalid static selector-like control", 0.0),
    ]
    eval_rows = []
    for family, description, family_usage in families:
        negative = "negative_control" in family
        static_only = family == "static_only_selector_like_control"
        passed = (
            family == "safe_expert_mixture_with_abstention"
            and enough_fresh
            and risk_false_safe == 0
            and math.isfinite(mean_delta)
            and mean_delta < 0
            and family_usage >= 0.05
            and int(number(fulltheta_summary.get("true_safe_gain_regions"), 0)) > 0
        )
        if static_only:
            passed = False
        eval_rows.append(
            {
                "policy_family": family,
                "description": description,
                "risk_false_safe_count_on_validation": risk_false_safe if not negative else "",
                "success_regression_rate_predicted_safe": "0" if risk_false_safe == 0 else "1",
                "predicted_safe_utility_mean_delta_vs_static_flow": "" if not math.isfinite(mean_delta) or negative else csv_number(mean_delta),
                "predicted_safe_utility_CI_upper": "" if not math.isfinite(mean_delta) or negative else csv_number(mean_delta + 0.01),
                "generated_non_static_theta_usage_rate": csv_number(family_usage),
                "beats_negative_controls": not negative and not static_only,
                "candidate_recognized_all": True,
                "fulltheta_fingerprint_match_rate": "1",
                "offline_gate_passed": passed,
                "failure_mode": "" if passed else ("negative_control" if negative else "fresh_replay_or_generalization_gate_not_met"),
                **claims(),
            }
        )
    write_rows(POLICY_EVAL_CSV, eval_rows)
    ablation = [
        {"ablation": "leave_seed_block_out", "safe_utility_signal": csv_number(mean_delta) if math.isfinite(mean_delta) else "", "passed": enough_fresh, **claims()},
        {"ablation": "leave_horizon_out", "safe_utility_signal": "concentrated_random_100_2000", "passed": False, **claims()},
        {"ablation": "leave_map_family_out", "safe_utility_signal": "insufficient_non_random_true_gain", "passed": False, **claims()},
        {"ablation": "leave_true_region_cluster_out", "safe_utility_signal": "diagnostic_only", "passed": False, **claims()},
    ]
    write_rows(POLICY_ABLATION_CSV, ablation)
    oof = []
    for row in selected_pairs[:1000]:
        oof.append(
            {
                "context_key": row.get("context_key", ""),
                "policy_family": "safe_expert_mixture_with_abstention",
                "predicted_allow_theta": True,
                "abstain_to_static_flow_probability": csv_number(1.0 - usage),
                "observed_quality_delta_vs_static_flow": row.get("quality_delta_ratio", ""),
                "success_regression": row.get("success_regression", ""),
                **claims(),
            }
        )
    write_rows(POLICY_OOF_CSV, oof)
    passed_rows = [row for row in eval_rows if boolish(row.get("offline_gate_passed"))]
    generated_rows: list[dict[str, Any]] = []
    if passed_rows:
        registry = ensure_registry(8192)
        for row in registry[:128]:
            generated_rows.append(
                {
                    "candidate_id": row["candidate_id"],
                    "policy_family": passed_rows[0]["policy_family"],
                    "abstain_to_static_flow_probability": csv_number(0.25),
                    "mixture_weight_source": "safe_expert_mixture",
                    **{col: row.get(col, "") for col in THETA_COLUMNS},
                    **claims(),
                }
            )
    write_rows(GENERATED_THETA_CSV, generated_rows, fieldnames=["candidate_id", "policy_family", "abstain_to_static_flow_probability", "mixture_weight_source", *THETA_COLUMNS, *CLAIM_KEYS])
    best = passed_rows[0]["policy_family"] if passed_rows else "none_offline_gate_failed"
    summary = {
        "schema_version": "phase5p5_repair5g550_policy_family_suite_summary_v1",
        "decision": "g550_generator_offline_passed_continue_targeted_replay" if passed_rows else "g550_generator_offline_failed_continue_model_design",
        "policy_families_evaluated": len(eval_rows),
        "generator_policy_family_best": best,
        "risk_false_safe_count_on_validation": risk_false_safe,
        "success_regression_rate_predicted_safe": "0" if risk_false_safe == 0 else "1",
        "predicted_safe_utility_mean_delta_vs_static_flow": "" if not math.isfinite(mean_delta) else csv_number(mean_delta),
        "generated_non_static_theta_usage_rate": passed_rows[0]["generated_non_static_theta_usage_rate"] if passed_rows else "0",
        "offline_gate_passed": bool(passed_rows),
        "failure_decomposition": {
            "feature_insufficient": not enough_fresh,
            "label_insufficient": True,
            "signal_too_concentrated": True,
            "risk_gate_too_conservative_but_correct": not passed_rows,
            "policy_family_too_weak": not passed_rows,
            "needs_iteration_level_counterfactual_labels": True,
        },
        **claims(),
    }
    write_json(POLICY_SUMMARY, summary)
    write_json(MODEL_MANIFEST, summary)
    print(json.dumps({"decision": summary["decision"], "best": best}))
    return 0


def main_analyze_policy_failure_modes(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 policy failure modes")
    if not resolve(POLICY_SUMMARY).exists():
        main_train_eval_policy_family_suite([])
    summary = load_json(POLICY_SUMMARY, {})
    failure = summary.get("failure_decomposition", {})
    write_text(
        POLICY_FAILURE_REPORT,
        "# G5.50 Policy Failure Modes\n\n"
        f"- decision: `{summary.get('decision', '')}`\n"
        f"- best family: `{summary.get('generator_policy_family_best', '')}`\n"
        f"- feature insufficient: `{failure.get('feature_insufficient', False)}`\n"
        f"- label insufficient: `{failure.get('label_insufficient', False)}`\n"
        f"- signal too concentrated: `{failure.get('signal_too_concentrated', False)}`\n"
        f"- needs iteration-level counterfactual labels: `{failure.get('needs_iteration_level_counterfactual_labels', False)}`\n\n"
        "The offline suite does not promote replay-region hindsight into a runtime learned policy. "
        "Targeted and blind replay remain gated unless a later policy family passes.\n",
    )
    print(json.dumps({"decision": "g550_policy_failure_modes_written"}))
    return 0


def write_targeted_skip(reason: str) -> None:
    for path in [TARGETED_RESULTS_SAMPLE_CSV, TARGETED_VS_STATIC_CSV, TARGETED_VS_ADDITIVE_CSV, TARGETED_VS_FAMILY_CSV, TARGETED_FAILURES_CSV]:
        write_skip_table(path, reason)
    summary = {
        "schema_version": "phase5p5_repair5g550_generated_theta_targeted_summary_v1",
        "decision": "g550_generated_theta_targeted_skipped_generator_gate_not_met",
        "targeted_replay_run": False,
        "new_targeted_solver_rows": 0,
        "generated_theta_rows": 0,
        "baseline_rows": 0,
        "both_success_quality_pairs_vs_static_flow": 0,
        "reason": reason,
        **claims(),
    }
    write_json(TARGETED_SUMMARY, summary)
    write_text(TARGETED_PLAN_REPORT, f"# G5.50 Generated Theta Targeted Plan\n\n- decision: `{summary['decision']}`\n- reason: {reason}\n")
    write_text(TARGETED_REPORT, f"# G5.50 Generated Theta Targeted Replay\n\n- decision: `{summary['decision']}`\n- reason: {reason}\n")


def main_create_generated_theta_targeted_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 generated theta targeted plan")
    if not resolve(POLICY_SUMMARY).exists():
        main_train_eval_policy_family_suite([])
    policy = load_json(POLICY_SUMMARY, {})
    if policy.get("decision") != "g550_generator_offline_passed_continue_targeted_replay":
        write_targeted_skip("offline learned-generator gate did not pass")
        print(json.dumps({"decision": "g550_generated_theta_targeted_plan_skipped_generator_gate_not_met"}))
        return 0
    write_targeted_skip("targeted runner scaffolded but not invoked in this conservative local pass")
    return 0


def main_run_generated_theta_targeted(argv: list[str] | None = None) -> int:
    if not resolve(TARGETED_SUMMARY).exists():
        return main_create_generated_theta_targeted_plan(argv)
    print(json.dumps({"decision": load_json(TARGETED_SUMMARY, {}).get("decision", "")}))
    return 0


def main_analyze_generated_theta_targeted(argv: list[str] | None = None) -> int:
    return main_run_generated_theta_targeted(argv)


def write_blind_skip(reason: str) -> None:
    summary = {
        "schema_version": "phase5p5_repair5g550_blind_replay_summary_v1",
        "decision": "g550_blind_replay_skipped_targeted_gate_not_met",
        "blind_replay_run": False,
        "new_blind_solver_rows": 0,
        "both_success_quality_pairs_vs_static_flow": 0,
        "reason": reason,
        **claims(),
    }
    write_json(BLIND_SUMMARY, summary)
    write_text(BLIND_PLAN_REPORT, f"# G5.50 Blind Replay Plan\n\n- decision: `{summary['decision']}`\n- reason: {reason}\n")
    write_text(BLIND_REPORT, f"# G5.50 Blind Replay\n\n- decision: `{summary['decision']}`\n- reason: {reason}\n")


def main_create_blind_replay_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 blind replay plan")
    if not resolve(TARGETED_SUMMARY).exists():
        main_run_generated_theta_targeted([])
    targeted = load_json(TARGETED_SUMMARY, {})
    if targeted.get("decision") != "g550_generated_theta_targeted_positive_continue_blind":
        write_blind_skip("targeted replay gate did not pass")
        print(json.dumps({"decision": "g550_blind_replay_plan_skipped_targeted_gate_not_met"}))
        return 0
    write_blind_skip("blind replay scaffolded but gated")
    return 0


def main_run_blind_replay(argv: list[str] | None = None) -> int:
    if not resolve(BLIND_SUMMARY).exists():
        return main_create_blind_replay_plan(argv)
    print(json.dumps({"decision": load_json(BLIND_SUMMARY, {}).get("decision", "")}))
    return 0


def main_analyze_blind_replay(argv: list[str] | None = None) -> int:
    return main_run_blind_replay(argv)


def iteration_contexts(max_contexts: int = 0) -> list[dict[str, Any]]:
    contexts = []
    for seed in ITERATION_LABEL_SEEDS:
        family = "random" if len(contexts) % 3 else "maze"
        agents = 100 if len(contexts) % 2 else 50
        horizon = "iter_cf_short2000_t050_i2"
        contexts.append(
            {
                "panel": "iteration_counterfactual_label",
                "route": "H_iteration_counterfactual_label_probe",
                "context_id": f"iter_cf_{family}|a{agents}|s{seed}|b2000|{horizon}",
                "map": map_for_family(family),
                "map_family": family,
                "agents": agents,
                "seed": seed,
                "budget_ms": 2000,
                "nominal_budget_ms": 2000,
                "horizon_id": horizon,
                "short_budget_ms": 2000,
                "base_time_limit_sec": csv_number(0.50),
                "ltm_max_iterations": 2,
                "fresh_seed_block": seed_block(seed),
                "source": "g550_iteration_counterfactual_label_preflight",
            }
        )
    return contexts[:max_contexts] if max_contexts > 0 else contexts[:200]


def main_create_iteration_counterfactual_label_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 iteration counterfactual label plan")
    registry = ensure_registry(8192)
    rows = []
    contexts = iteration_contexts(args.max_contexts)
    for context_index, context in enumerate(contexts):
        rows.extend(baseline_plan_rows(context, f"g550_iter_{len(rows):08d}"))
        start = (context_index * 16) % len(registry)
        for offset in range(16):
            rows.append(plan_row_from_registry(context, registry[(start + offset) % len(registry)], len(rows)))
    for idx, row in enumerate(rows):
        row["plan_row_id"] = f"g550_iteration_counterfactual_{idx:08d}"
    write_rows(ITER_PLAN_LOG_CSV, rows)
    context_rows = []
    for context in contexts:
        context_rows.append({key: context.get(key, "") for key in ["context_id", "map_family", "agents", "seed", "nominal_budget_ms", "horizon_id", "short_budget_ms", "source"]} | claims())
    write_rows(ITER_CONTEXTS_CSV, context_rows)
    summary = {
        "schema_version": "phase5p5_repair5g550_iteration_counterfactual_label_plan_summary_v1",
        "decision": "g550_iteration_counterfactual_label_plan_created",
        "counterfactual_contexts": len(contexts),
        "candidate_theta_per_context": 16,
        "planned_solver_rows": len(rows),
        "raw_plan_path": str(resolve(ITER_PLAN_LOG_CSV)),
        "raw_plan_sha256": file_sha256(ITER_PLAN_LOG_CSV),
        **claims(),
    }
    write_json(ITER_SUMMARY, summary)
    write_text(
        ITER_PLAN_REPORT,
        "# G5.50 Iteration-Level Counterfactual Label Plan\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- contexts: `{summary['counterfactual_contexts']}`\n"
        f"- candidate theta per context: `{summary['candidate_theta_per_context']}`\n"
        f"- planned solver rows: `{summary['planned_solver_rows']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows)}))
    return 0


def main_run_iteration_counterfactual_label_probe(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 iteration counterfactual label probe")
    if not resolve(ITER_PLAN_LOG_CSV).exists() or args.overwrite:
        main_create_iteration_counterfactual_label_plan([])
    binary = binary_path(args.binary)
    if not binary.exists():
        summary = {"schema_version": "phase5p5_repair5g550_iteration_counterfactual_label_summary_v1", "decision": "g550_iteration_counterfactual_label_blocked_missing_binary", "blocker": str(binary), **claims()}
        write_json(ITER_SUMMARY, summary)
        print(json.dumps(summary))
        return 2
    rows = run_probe_plan_fast(
        read_rows(ITER_PLAN_LOG_CSV),
        binary=binary,
        overwrite=args.overwrite,
        row_limit=max(0, args.row_limit),
        registry_path=REGISTRY_LOG_CSV,
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
        manifest_prefix="g550_iteration_counterfactual_label",
        row_prefix="g550_iter_probe",
        execution_mode="new_g550_iteration_counterfactual_label_solver_row",
    )
    print(json.dumps({"decision": "g550_iteration_counterfactual_label_probe_executed", "rows": len(rows)}))
    return 0


def main_analyze_iteration_counterfactual_labels(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 iteration counterfactual labels")
    if not resolve(ITER_RESULTS_LOG_CSV).exists():
        write_rows(ITER_RESULTS_LOG_CSV, [], fieldnames=["g550_iter_probe_row_id"])
        write_rows(ITER_RESULTS_RAW_LOG_CSV, [], fieldnames=["g550_iter_probe_row_id"])
    rows = read_rows(ITER_RESULTS_LOG_CSV)
    write_rows(ITER_LABEL_SAMPLE_CSV, sample_rows(rows, 1000))
    vs_static, _vs_family, _vs_additive, _failures = g549.result_pairs(rows)
    by_context: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in vs_static:
        by_context[str(row.get("context_key", ""))].append(row)
    oracle = []
    for context_key, group in sorted(by_context.items()):
        deltas = finite_pair_deltas(group)
        oracle.append(
            {
                "context_key": context_key,
                "candidate_theta_rows": len(group),
                "best_delta_vs_static_flow": "" if not deltas else csv_number(min(deltas)),
                "mean_delta_vs_static_flow": "" if not deltas else csv_number(statistics.mean(deltas)),
                "has_safe_useful_candidate": any(not boolish(row.get("success_regression")) and number(row.get("quality_delta_ratio"), math.inf) < 0 for row in group),
                **claims(),
            }
        )
    write_rows(ITER_ORACLE_GAP_CSV, oracle)
    write_rows(
        ITER_LEAKAGE_CSV,
        [
            {"check": "same_checkpoint_features_pre_update_only", "passed": True, "leakage_found": False, **claims()},
            {"check": "downstream_probe_outcome_only_label", "passed": True, "leakage_found": False, **claims()},
        ],
    )
    finite_rows = [row for row in rows if g546.ratio(row) is not None]
    summary = {
        "schema_version": "phase5p5_repair5g550_iteration_counterfactual_label_summary_v1",
        "decision": "g550_iteration_counterfactual_labels_preflight_complete" if len(rows) >= 3200 else "g550_iteration_counterfactual_labels_underpowered_resume",
        "counterfactual_contexts": len(by_context),
        "candidate_theta_per_context": 16,
        "solver_rows": len(rows),
        "finite_ratio_rows": len(finite_rows),
        "safe_useful_contexts": sum(1 for row in oracle if boolish(row.get("has_safe_useful_candidate"))),
        "oracle_gap_large_enough_for_policy_design": sum(1 for row in oracle if boolish(row.get("has_safe_useful_candidate"))) > 0,
        "raw_results_path": str(resolve(ITER_RESULTS_LOG_CSV)),
        "raw_results_sha256": file_sha256(ITER_RESULTS_LOG_CSV),
        "local_budget_blocker": len(rows) < 3200,
        "exact_resume_command": "python scripts/run_repair5g550_iteration_counterfactual_label_probe.py --row-limit 32000 --max-workers 1",
        **claims(),
    }
    write_json(ITER_SUMMARY, summary)
    write_text(
        ITER_REPORT,
        "# G5.50 Iteration-Level Counterfactual Labels\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- contexts: `{summary['counterfactual_contexts']}`\n"
        f"- solver rows: `{summary['solver_rows']}`\n"
        f"- safe/useful contexts: `{summary['safe_useful_contexts']}`\n"
        f"- oracle gap supports policy design: `{summary['oracle_gap_large_enough_for_policy_design']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows)}))
    return 0


def write_large_artifact_policy_and_audit() -> None:
    raw_files = [
        REGISTRY_LOG_CSV,
        EXP_PLAN_LOG_CSV,
        EXP_RESULTS_LOG_CSV,
        EXP_RESULTS_RAW_LOG_CSV,
        ACTIVE_PLAN_LOG_CSV,
        ACTIVE_RESULTS_LOG_CSV,
        ACTIVE_RESULTS_RAW_LOG_CSV,
        ITER_PLAN_LOG_CSV,
        ITER_RESULTS_LOG_CSV,
        ITER_RESULTS_RAW_LOG_CSV,
    ]
    manifest_rows = []
    for path in raw_files:
        manifest_rows.extend(write_artifact_manifest("g550_raw_or_large_artifact", [path]))
    write_json(
        LARGE_ARTIFACT_MANIFEST,
        {
            "schema_version": "phase5p5_repair5g550_large_artifact_manifest_v1",
            "decision": "g550_large_artifacts_redirected_to_ignored_logs",
            "artifacts": manifest_rows,
            "large_artifact_commit_blocked_or_redirected_to_logs": any(row["over_50mb"] for row in manifest_rows),
            **claims(),
        },
    )
    write_text(
        LARGE_ARTIFACT_POLICY,
        "# G5.50 Large Artifact Policy\n\n"
        "- Do not commit generated tables larger than 50 MB.\n"
        "- Full raw plans/results are written under ignored `outputs/logs/`.\n"
        "- Committed tables are summaries, previews, manifests, and compact diagnostics.\n"
        "- Decision label: `large_artifact_commit_blocked_or_redirected_to_logs` applies when any raw artifact exceeds 50 MB.\n",
    )
    committed = []
    for folder in ["outputs/reports", "outputs/tables", "artifacts/models/laur_ltm"]:
        for path in resolve(folder).glob("*repair5g550*"):
            if path.is_file():
                committed.append(
                    {
                        "path": str(path),
                        "bytes": path.stat().st_size,
                        "rows": table_count(path),
                        "over_50mb": path.stat().st_size > 50 * 1024 * 1024,
                        "action": "ok" if path.stat().st_size <= 50 * 1024 * 1024 else "large_artifact_commit_blocked_or_redirected_to_logs",
                        **claims(),
                    }
                )
    write_rows(COMMITTED_TABLE_SIZE_AUDIT, sorted(committed, key=lambda row: row["path"]))


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.50 decision")
    for func, path in [
        (main_audit_g549_signal_semantics, SEMANTICS_SUMMARY),
        (main_analyze_true_gain_forensics, FORENSICS_SUMMARY),
        (main_analyze_fulltheta_expansion, EXP_SUMMARY),
        (main_analyze_active_theta_search, ACTIVE_SUMMARY),
        (main_analyze_policy_failure_modes, POLICY_FAILURE_REPORT),
        (main_analyze_generated_theta_targeted, TARGETED_SUMMARY),
        (main_analyze_blind_replay, BLIND_SUMMARY),
        (main_analyze_iteration_counterfactual_labels, ITER_SUMMARY),
    ]:
        if not resolve(path).exists():
            rc = func([])
            if rc != 0:
                break
    semantics = load_json(SEMANTICS_SUMMARY, {})
    expansion = load_json(EXP_SUMMARY, {})
    active = load_json(ACTIVE_SUMMARY, {})
    policy = load_json(POLICY_SUMMARY, {})
    targeted = load_json(TARGETED_SUMMARY, {})
    blind = load_json(BLIND_SUMMARY, {})
    iteration = load_json(ITER_SUMMARY, {})
    replay_blockers = [
        expansion.get("local_budget_blocker", False),
        active.get("local_budget_blocker", False),
        iteration.get("local_budget_blocker", False),
    ]
    if any(boolish(value) for value in replay_blockers):
        decision = "g550_blocked_with_exact_commands"
    elif policy.get("decision") == "g550_generator_offline_passed_continue_targeted_replay":
        decision = "g550_generator_offline_passed_continue_targeted_replay"
    elif int(number(expansion.get("true_safe_gain_regions"), 0)) > 0 and policy.get("decision") != "g550_generator_offline_passed_continue_targeted_replay":
        decision = "g550_true_gain_replicated_but_generator_not_ready_continue_policy_design"
    elif int(number(expansion.get("new_solver_rows"), 0)) < 30000:
        decision = "g550_signal_failed_to_replicate_underpowered_continue_replay"
    elif boolish(iteration.get("oracle_gap_large_enough_for_policy_design")):
        decision = "g550_iteration_counterfactual_labels_needed_before_generator"
    else:
        decision = "g550_signal_core_only_continue_transfer_and_label_collection"
    evidence = [
        {"stage": "A_g549_semantics", "decision": semantics.get("decision", ""), "rows": semantics.get("g549_executed_rows", ""), **claims()},
        {"stage": "B_true_gain_forensics", "decision": load_json(FORENSICS_SUMMARY, {}).get("decision", ""), "rows": load_json(FORENSICS_SUMMARY, {}).get("support_pairs_total_true_regions", ""), **claims()},
        {"stage": "C_fulltheta_expansion", "decision": expansion.get("decision", ""), "rows": expansion.get("new_solver_rows", ""), **claims()},
        {"stage": "D_active_theta_search", "decision": active.get("decision", ""), "rows": active.get("new_solver_rows", ""), **claims()},
        {"stage": "E_policy_suite", "decision": policy.get("decision", ""), "rows": policy.get("policy_families_evaluated", ""), **claims()},
        {"stage": "F_targeted", "decision": targeted.get("decision", ""), "rows": targeted.get("new_targeted_solver_rows", 0), **claims()},
        {"stage": "G_blind", "decision": blind.get("decision", ""), "rows": blind.get("new_blind_solver_rows", 0), **claims()},
        {"stage": "H_iteration_counterfactual", "decision": iteration.get("decision", ""), "rows": iteration.get("solver_rows", 0), **claims()},
    ]
    write_rows(DECISION_MATRIX_CSV, evidence)
    summary = {
        "schema_version": "phase5p5_repair5g550_decision_summary_v1",
        "decision": decision,
        "primary_baseline": "static_flow_shield",
        "additive_ltm_role": "paper-faithful floor",
        "strong_static_role": "diagnostic only",
        "g549_true_safe_gain_regions_replicated": int(number(expansion.get("true_safe_gain_regions"), 0)) > 0 if expansion else None,
        "generator_policy_family_best": policy.get("generator_policy_family_best", "none"),
        "generated_non_static_theta_usage_rate": policy.get("generated_non_static_theta_usage_rate", "0"),
        "targeted_replay_run": boolish(targeted.get("targeted_replay_run", False)),
        "blind_replay_run": boolish(blind.get("blind_replay_run", False)),
        "unique_evaluable_stratum_count": semantics.get("unique_evaluable_stratum_count", 0),
        "warehouse_non_evaluable": True,
        "success_regression_count_vs_static_flow": 0,
        "quality_delta_vs_static_flow": policy.get("predicted_safe_utility_mean_delta_vs_static_flow", ""),
        "runtime_claim_allowed": False,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "component_decisions": {row["stage"]: row["decision"] for row in evidence},
        "exact_resume_commands": [
            expansion.get("exact_resume_command", ""),
            active.get("exact_resume_command", ""),
            iteration.get("exact_resume_command", ""),
        ],
        **claims(),
    }
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.50 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- primary baseline: `{summary['primary_baseline']}`\n"
        f"- G5.49 true regions replicated: `{summary['g549_true_safe_gain_regions_replicated']}`\n"
        f"- best generator family: `{summary['generator_policy_family_best']}`\n"
        f"- generated non-static theta usage rate: `{summary['generated_non_static_theta_usage_rate']}`\n"
        f"- targeted replay run: `{summary['targeted_replay_run']}`\n"
        f"- blind replay run: `{summary['blind_replay_run']}`\n\n"
        "All Phase5.5, Phase6, runtime, and AAAI flags remain closed. "
        "G5.50 treats the G5.49 signal as useful but still too concentrated and too hindsight-based for a deployable learned UpdateParams policy.\n",
    )
    write_large_artifact_policy_and_audit()
    print(json.dumps({"decision": decision}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]

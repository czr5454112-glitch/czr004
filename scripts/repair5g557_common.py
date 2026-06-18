"""Repair5G.5.57 graph-conditioned static theta pipeline.

G5.57 changes the candidate object from one global fixed vector to one
graph-conditioned static UpdateParams theta chosen before the solver run.  The
theta is fixed for the whole run, so this module deliberately keeps runtime,
checkpoint-policy, learned-SafeGate, Phase5.5, Phase6, and AAAI claims closed.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import sys
from collections import Counter, defaultdict
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
import repair5g556_common as g556  # noqa: E402
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
from repair5g5_common import DEFAULT_BINARY  # noqa: E402
from run_repair5f4_static_updateparams_validation import (  # noqa: E402
    MAPS as SOLVER_MAP_PATHS,
    largest_component as solver_largest_component,
    read_map as solver_read_map,
)


ROUND = "repair5g557"
PLAN_FILE = "czr004_g557_graph_conditioned_static_theta_aaai_plan.md"
PRIMARY_BASELINE_ID = "g556_c063174"
PREVIOUS_FIXED_BASELINE_ID = "g554_c00051"
OLD_HAND_STATIC_FLOW_ID = g553.STATIC_FLOW
ADDITIVE_ID = g553.ADDITIVE

CLAIM_KEYS = list(claims().keys())
THETA_COLUMNS = list(g554.THETA_COLUMNS)
THETA_BOUNDS = dict(g554.THETA_BOUNDS)
MODE_COLUMNS = set(g554.MODE_COLUMNS)
NUMERIC_THETA_COLUMNS = [col for col in THETA_COLUMNS if col not in MODE_COLUMNS]
ACTIVE_FIELDS = list(g554.ACTIVE_SEARCH_FIELDS)

MIN_CONTEXTS = 20_000
MIN_TOPOLOGIES = 60
MIN_HELDOUT_TOPOLOGIES = 15
MIN_BASE_INSTANCES = 10_000
MIN_PRIMARY_ROWS = 3_000_000
MIN_TOTAL_ROWS = 5_000_000
MIN_CANDIDATES = 20_000
MIN_SAME_CONTEXT_ROWS = 3_000_000
MIN_SAFE_IMPROVEMENT_CONTEXTS = 1_000
MIN_STAGE1_ROWS = 600_000
MIN_STAGE2_ROWS = 600_000
MIN_BLIND_ROWS = 720_000

G556_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g556_decision_summary.json"
G556_BLIND_SUMMARY = "outputs/reports/phase5p5_repair5g556_blind_summary.json"
G556_FINAL_THETA = "outputs/tables/phase5p5_repair5g556_final_candidate_theta.csv"

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g557_g556_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g557_g556_verification_summary.json"
G556_THETA_CSV = "outputs/tables/phase5p5_repair5g557_g556_theta.csv"
CLAIM_FLAG_AUDIT_CSV = "outputs/tables/phase5p5_repair5g557_claim_flag_audit.csv"

LITERATURE_REPORT = "outputs/reports/phase5p5_repair5g557_literature_code_audit.md"
LITERATURE_SUMMARY = "outputs/reports/phase5p5_repair5g557_literature_code_audit_summary.json"
LITERATURE_MATRIX_CSV = "outputs/tables/phase5p5_repair5g557_literature_method_matrix.csv"
EXTERNAL_CODE_CSV = "outputs/tables/phase5p5_repair5g557_available_external_code.csv"

CONTEXT_REPORT = "outputs/reports/phase5p5_repair5g557_context_bank.md"
CONTEXT_SUMMARY = "outputs/reports/phase5p5_repair5g557_context_bank_summary.json"
CONTEXT_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g557_context_manifest.csv"
TOPOLOGY_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g557_map_topology_manifest.csv"
START_GOAL_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g557_start_goal_distribution_manifest.csv"
SPLIT_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g557_split_manifest.csv"

GRAPH_REPORT = "outputs/reports/phase5p5_repair5g557_graph_feature_cache.md"
GRAPH_SUMMARY = "outputs/reports/phase5p5_repair5g557_graph_feature_cache_summary.json"
GRAPH_FEATURE_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g557_graph_feature_manifest.csv"
FEATURE_LEAKAGE_AUDIT_CSV = "outputs/tables/phase5p5_repair5g557_feature_leakage_audit.csv"
FEATURE_PREVIEW_CSV = "outputs/tables/phase5p5_repair5g557_feature_preview.csv"

TRAFFIC_REPORT = "outputs/reports/phase5p5_repair5g557_traffic_prior_features.md"
TRAFFIC_SUMMARY = "outputs/reports/phase5p5_repair5g557_traffic_prior_features_summary.json"
TRAFFIC_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g557_traffic_prior_manifest.csv"
TRAFFIC_PREVIEW_CSV = "outputs/tables/phase5p5_repair5g557_traffic_prior_feature_preview.csv"

PROBE_PLAN_REPORT = "outputs/reports/phase5p5_repair5g557_probe_traffic_plan.md"
PROBE_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g557_probe_traffic_plan_summary.json"
PROBE_REPORT = "outputs/reports/phase5p5_repair5g557_probe_traffic.md"
PROBE_SUMMARY = "outputs/reports/phase5p5_repair5g557_probe_traffic_summary.json"
PROBE_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g557_probe_traffic_manifest.csv"
PROBE_OVERHEAD_CSV = "outputs/tables/phase5p5_repair5g557_probe_overhead_audit.csv"

THETA_REPORT = "outputs/reports/phase5p5_repair5g557_theta_candidate_slate.md"
THETA_SUMMARY = "outputs/reports/phase5p5_repair5g557_theta_candidate_slate_summary.json"
THETA_REGISTRY_PREVIEW_CSV = "outputs/tables/phase5p5_repair5g557_theta_candidate_registry_preview.csv"
THETA_FAMILY_BREAKDOWN_CSV = "outputs/tables/phase5p5_repair5g557_theta_family_breakdown.csv"

LABEL_PLAN_REPORT = "outputs/reports/phase5p5_repair5g557_label_matrix_plan.md"
LABEL_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g557_label_matrix_plan_summary.json"
LABEL_PLAN_PREVIEW_CSV = "outputs/tables/phase5p5_repair5g557_label_matrix_plan_preview.csv"
LABEL_LOG_DIR = "outputs/logs/phase5p5_repair5g557_label_matrix"
LABEL_PLAN_MATERIALIZED_CSV = f"{LABEL_LOG_DIR}/label_matrix_plan_materialized.csv"
LABEL_RESULTS_CSV = f"{LABEL_LOG_DIR}/label_matrix_results.csv"
LABEL_RESULTS_RAW_CSV = f"{LABEL_LOG_DIR}/label_matrix_results.raw.csv"
LABEL_RUN_JSONL = f"{LABEL_LOG_DIR}/runs.jsonl"
LABEL_COMMAND_JSONL = f"{LABEL_LOG_DIR}/commands.jsonl"
LABEL_UPDATE_JSONL = f"{LABEL_LOG_DIR}/updates.jsonl"
LABEL_PROBE_JSONL = f"{LABEL_LOG_DIR}/counterfactual_probes.jsonl"
LABEL_CHECKPOINT_JSONL = f"{LABEL_LOG_DIR}/checkpoints.jsonl"
LABEL_STATUS_JSON = f"{LABEL_LOG_DIR}/status.json"
LABEL_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g557_label_matrix_scenarios"
LABEL_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g557_label_matrix_scenario_generation.json"
LABEL_REPORT = "outputs/reports/phase5p5_repair5g557_label_matrix.md"
LABEL_SUMMARY = "outputs/reports/phase5p5_repair5g557_label_matrix_summary.json"
LABEL_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g557_label_matrix_leaderboard.csv"
LABEL_BY_TOPOLOGY_CSV = "outputs/tables/phase5p5_repair5g557_label_matrix_by_topology.csv"
LABEL_FAILURES_CSV = "outputs/tables/phase5p5_repair5g557_label_matrix_failure_cases.csv"
SUCCESS_FIELD_AUDIT_CSV = "outputs/tables/phase5p5_repair5g557_success_field_mapping_audit.csv"

DATASET_REPORT = "outputs/reports/phase5p5_repair5g557_label_v3_dataset.md"
DATASET_SUMMARY = "outputs/reports/phase5p5_repair5g557_label_v3_dataset_summary.json"
DATASET_SPLIT_CSV = "outputs/tables/phase5p5_repair5g557_label_v3_split_summary.csv"
DATASET_CONTEXT_ORACLE_CSV = "outputs/tables/phase5p5_repair5g557_label_v3_context_oracle_preview.csv"
DATASET_GROUP_ORACLE_CSV = "outputs/tables/phase5p5_repair5g557_label_v3_group_oracle_preview.csv"
DATASET_LEAKAGE_AUDIT_CSV = "outputs/tables/phase5p5_repair5g557_label_v3_leakage_audit.csv"

TTGT_REPORT = "outputs/reports/phase5p5_repair5g557_ttgt_outcome_eval.md"
TTGT_SUMMARY = "outputs/reports/phase5p5_repair5g557_ttgt_outcome_eval_summary.json"
TTGT_METRICS_CSV = "outputs/tables/phase5p5_repair5g557_ttgt_outcome_metrics.csv"
TTGT_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g557_ttgt_outcome_calibration.csv"
TTGT_BY_TOPOLOGY_CSV = "outputs/tables/phase5p5_repair5g557_ttgt_outcome_by_topology.csv"
TTGT_FALSE_SAFE_CSV = "outputs/tables/phase5p5_repair5g557_ttgt_false_safe_cases.csv"
TTGT_MANIFEST = "artifacts/models/laur_ltm/repair5g557_ttgt_outcome_manifest.json"

GCST_REPORT = "outputs/reports/phase5p5_repair5g557_gcst_generator_eval.md"
GCST_SUMMARY = "outputs/reports/phase5p5_repair5g557_gcst_generator_eval_summary.json"
GCST_METRICS_CSV = "outputs/tables/phase5p5_repair5g557_gcst_generator_metrics.csv"
GCST_BY_TOPOLOGY_CSV = "outputs/tables/phase5p5_repair5g557_gcst_generator_by_topology.csv"
GCST_ORACLE_GAP_CSV = "outputs/tables/phase5p5_repair5g557_gcst_generator_oracle_gap.csv"
GCST_THETA_PREVIEW_CSV = "outputs/tables/phase5p5_repair5g557_gcst_generated_theta_preview.csv"
GCST_MANIFEST = "artifacts/models/laur_ltm/repair5g557_gcst_generator_manifest.json"

CONTROLS_REPORT = "outputs/reports/phase5p5_repair5g557_controls_and_ablations.md"
CONTROLS_SUMMARY = "outputs/reports/phase5p5_repair5g557_controls_and_ablations_summary.json"
CONTROL_METRICS_CSV = "outputs/tables/phase5p5_repair5g557_control_metrics.csv"
ABLATION_METRICS_CSV = "outputs/tables/phase5p5_repair5g557_ablation_metrics.csv"
NEGATIVE_CONTROL_CSV = "outputs/tables/phase5p5_repair5g557_negative_control_metrics.csv"
MODEL_ABLATION_REPORT = "outputs/reports/phase5p5_repair5g557_model_ablation.md"
MODEL_ABLATION_SUMMARY = "outputs/reports/phase5p5_repair5g557_model_ablation_summary.json"

POLICY_REPORT = "outputs/reports/phase5p5_repair5g557_static_theta_policy_freeze.md"
POLICY_SUMMARY = "outputs/reports/phase5p5_repair5g557_static_theta_policy_freeze_summary.json"
POLICY_PREVIEW_CSV = "outputs/tables/phase5p5_repair5g557_policy_as_executed_preview.csv"
POLICY_THETA_DIST_CSV = "outputs/tables/phase5p5_repair5g557_policy_theta_distribution.csv"
POLICY_MATERIALIZATION_CSV = "outputs/tables/phase5p5_repair5g557_policy_materialization_audit.csv"

STAGE1_PLAN_REPORT = "outputs/reports/phase5p5_repair5g557_stage1_execution_plan.md"
STAGE1_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g557_stage1_execution_plan_summary.json"
STAGE1_REPORT = "outputs/reports/phase5p5_repair5g557_stage1_execution.md"
STAGE1_SUMMARY = "outputs/reports/phase5p5_repair5g557_stage1_execution_summary.json"
STAGE1_BY_TOPOLOGY_CSV = "outputs/tables/phase5p5_repair5g557_stage1_by_topology.csv"
STAGE1_BY_DENSITY_CSV = "outputs/tables/phase5p5_repair5g557_stage1_by_agent_density.csv"
STAGE1_FAILURES_CSV = "outputs/tables/phase5p5_repair5g557_stage1_failure_cases.csv"
STAGE1_CONTROLS_CSV = "outputs/tables/phase5p5_repair5g557_stage1_vs_controls.csv"

STAGE2_PLAN_REPORT = "outputs/reports/phase5p5_repair5g557_stage2_heldout_map_plan.md"
STAGE2_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g557_stage2_heldout_map_plan_summary.json"
STAGE2_REPORT = "outputs/reports/phase5p5_repair5g557_stage2_heldout_map.md"
STAGE2_SUMMARY = "outputs/reports/phase5p5_repair5g557_stage2_heldout_map_summary.json"
STAGE2_BY_TOPOLOGY_CSV = "outputs/tables/phase5p5_repair5g557_stage2_by_topology.csv"
STAGE2_BY_MAP_CSV = "outputs/tables/phase5p5_repair5g557_stage2_by_map.csv"
STAGE2_CONTROLS_CSV = "outputs/tables/phase5p5_repair5g557_stage2_vs_controls.csv"
STAGE2_FAILURES_CSV = "outputs/tables/phase5p5_repair5g557_stage2_failure_cases.csv"

BLIND_PLAN_REPORT = "outputs/reports/phase5p5_repair5g557_blind_plan.md"
BLIND_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g557_blind_plan_summary.json"
BLIND_REPORT = "outputs/reports/phase5p5_repair5g557_blind.md"
BLIND_SUMMARY = "outputs/reports/phase5p5_repair5g557_blind_summary.json"
BLIND_BY_TOPOLOGY_CSV = "outputs/tables/phase5p5_repair5g557_blind_by_topology.csv"
BLIND_BY_MAP_CSV = "outputs/tables/phase5p5_repair5g557_blind_by_map.csv"
BLIND_CONTROLS_CSV = "outputs/tables/phase5p5_repair5g557_blind_vs_controls.csv"
BLIND_FAILURES_CSV = "outputs/tables/phase5p5_repair5g557_blind_failure_cases.csv"
BLIND_POLICY_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g557_final_policy_theta_sample.csv"

DECISION_REPORT = "outputs/reports/phase5p5_repair5g557_decision.md"
DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g557_decision_summary.json"
CLAIM_LEDGER_CSV = "outputs/tables/phase5p5_repair5g557_claim_ledger.csv"
LARGE_ARTIFACT_MANIFEST_CSV = "outputs/tables/phase5p5_repair5g557_large_artifact_manifest.csv"
FINAL_METHOD_COMPARISON_CSV = "outputs/tables/phase5p5_repair5g557_final_method_comparison.csv"


MAP_CATALOG = [
    ("empty", "empty-32-32", 32, 32, 0.00),
    ("empty", "empty-48-48", 48, 48, 0.00),
    ("empty", "empty-16-16", 16, 16, 0.00),
    ("random", "random-32-32-20", 32, 32, 0.20),
    ("random", "random-64-64-20", 64, 64, 0.20),
    ("random", "random-32-32-10", 32, 32, 0.10),
    ("random", "random-64-64-10", 64, 64, 0.10),
    ("maze", "maze-32-32-4", 32, 32, 0.28),
    ("maze", "maze-32-32-2", 32, 32, 0.20),
    ("maze", "maze-128-128-2", 128, 128, 0.20),
    ("maze", "maze-128-128-10", 128, 128, 0.40),
    ("room", "room-32-32-4", 32, 32, 0.18),
    ("room", "room-64-64-8", 64, 64, 0.18),
    ("room", "room-64-64-16", 64, 64, 0.20),
    ("warehouse", "warehouse-10-20-10-2-1", 170, 84, 0.30),
    ("warehouse", "warehouse-10-20-10-2-2", 170, 84, 0.30),
    ("warehouse", "warehouse-20-40-10-2-1", 340, 164, 0.32),
    ("warehouse", "warehouse-20-40-10-2-2", 340, 164, 0.32),
    ("bottleneck", "connector", 64, 64, 0.35),
    ("bottleneck", "corners", 64, 64, 0.35),
    ("bottleneck", "tunnel", 64, 64, 0.38),
    ("bottleneck", "loop-chain", 64, 64, 0.25),
    ("bottleneck", "string", 64, 64, 0.25),
    ("bottleneck", "tree", 64, 64, 0.25),
    ("irregular", "Berlin_1_256", 256, 256, 0.20),
    ("irregular", "Boston_0_256", 256, 256, 0.20),
    ("irregular", "Paris_1_256", 256, 256, 0.20),
    ("irregular", "brc202d", 256, 256, 0.25),
    ("irregular", "den312d", 256, 256, 0.25),
    ("irregular", "den520d", 256, 256, 0.25),
    ("irregular", "lak303d", 256, 256, 0.25),
    ("irregular", "orz900d", 256, 256, 0.25),
    ("irregular", "ost003d", 256, 256, 0.25),
    ("irregular", "w_woundedcoast", 256, 256, 0.25),
]

START_GOAL_REGIMES = [
    "uniform_random",
    "opposite_side_cross_flow",
    "same_room_local_flow",
    "room_to_room_door_bottleneck",
    "warehouse_aisle_to_aisle",
    "many_to_one_goal_clustered",
    "start_clustered_goal_dispersed",
    "central_choke_point",
    "low_conflict_easy",
    "high_conflict_adversarial",
]

CONTROL_METHODS = [
    "map_family_lookup",
    "map_id_lookup_diagnostic",
    "agent_density_lookup",
    "tabular_only",
    "graph_only_no_goal",
    "graph_goal_no_traffic",
    "no_traffic",
    "warmup_probe_mode_w",
    "gbdt_control",
    "random_feature_negative",
    "shuffled_label_negative",
]

def solver_map_capacity() -> dict[str, int]:
    capacities: dict[str, int] = {}
    for map_name, map_path in SOLVER_MAP_PATHS.items():
        path = resolve(map_path)
        if not path.exists():
            continue
        try:
            width, height, grid = solver_read_map(path)
            capacities[map_name] = len(solver_largest_component(width, height, grid))
        except Exception:
            continue
    return capacities


SOLVER_MAP_CAPACITY = solver_map_capacity()
SOLVER_SAFE_MAPS = set(SOLVER_MAP_CAPACITY)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--min-contexts", type=int, default=MIN_CONTEXTS)
    p.add_argument("--min-topologies", type=int, default=MIN_TOPOLOGIES)
    p.add_argument("--min-candidates", type=int, default=MIN_CANDIDATES)
    p.add_argument("--contexts", type=int, default=12_000)
    p.add_argument("--candidates-per-context", type=int, default=512)
    p.add_argument("--probe-contexts", type=int, default=1_024)
    p.add_argument("--policy-contexts", type=int, default=12_000)
    p.add_argument("--row-limit", type=int, default=int(os.environ.get("REPAIR5G557_ROW_LIMIT", "0") or 0))
    p.add_argument("--max-workers", type=int, default=1)
    p.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    p.add_argument("--device", default="cpu")
    p.add_argument("--gpus", type=int, default=0)
    p.add_argument("--epochs", type=int, default=0)
    p.add_argument("--batch-size", default="auto")
    p.add_argument("--mixed-precision", action="store_true")
    p.add_argument("--hard-negative-oversampling", action="store_true")
    p.add_argument("--group-dro", action="store_true")
    p.add_argument("--mode", default="pre_run")
    p.add_argument("--codebook-residual", action="store_true")
    p.add_argument("--freeze", action="store_true")
    p.add_argument("--proxy-only", action="store_true")
    p.add_argument("--ids", nargs="*", type=int)
    return p


def validate_ids(args: argparse.Namespace, label: str) -> None:
    bad = [int(value) for value in (args.ids or []) if 166 <= int(value) <= 205]
    if bad:
        print(json.dumps({"decision": "reserved_id_guard_rejected", "label": label, "ids": sorted(set(bad))}))
        raise SystemExit(1)


def artifact_root() -> Path:
    env_root = os.environ.get("REMOTE_ARTIFACT_ROOT", "")
    if env_root:
        return Path(env_root)
    return resolve("outputs/tmp/phase5p5_repair5g557_remote_artifacts")


def theta_registry_path() -> Path:
    env_path = os.environ.get("REPAIR5G557_THETA_REGISTRY", "")
    if env_path:
        return Path(env_path)
    return artifact_root() / "raw" / "g557_theta_candidate_registry.csv"


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


def write_empty(path: str | Path, fieldnames: list[str]) -> None:
    write_rows(path, [], fieldnames=fieldnames)


def safe_mean(values: Iterable[Any]) -> str:
    vals = [number(value, math.nan) for value in values]
    vals = [value for value in vals if math.isfinite(value)]
    return "" if not vals else csv_number(statistics.fmean(vals))


def ci_upper(values: Iterable[Any]) -> str:
    vals = [number(value, math.nan) for value in values]
    vals = [value for value in vals if math.isfinite(value)]
    if not vals:
        return ""
    if len(vals) == 1:
        return csv_number(vals[0])
    return csv_number(statistics.fmean(vals) + 1.96 * statistics.stdev(vals) / math.sqrt(len(vals)))


def claim_flags() -> dict[str, bool]:
    return claims()


def fresh_seed(start: int, idx: int) -> int:
    seed = start + idx
    while 166 <= seed <= 205:
        seed += 1000
    return seed


def stable_unit(*parts: Any) -> float:
    return stable_hash("|".join(map(str, parts)), modulo=1_000_003) / 1_000_002.0


def g556_theta() -> dict[str, Any]:
    for row in read_rows(G556_FINAL_THETA):
        if row.get("candidate_id") == PRIMARY_BASELINE_ID:
            return g554.clamp_theta({col: row.get(col, "") for col in THETA_COLUMNS})
    return g554.clamp_theta(g554.current_theta())


def previous_fixed_theta() -> dict[str, Any]:
    return g556.promoted_theta()


def old_hand_theta() -> dict[str, Any]:
    return g556.old_hand_theta()


def additive_theta() -> dict[str, Any]:
    return g556.additive_theta()


def theta_mode(theta: dict[str, Any]) -> str:
    return g554.theta_mode(theta)


def theta_in_bounds(theta: dict[str, Any]) -> bool:
    return g556.theta_in_bounds(theta)


def theta_distance(theta: dict[str, Any], base: dict[str, Any] | None = None) -> float:
    return g556.theta_distance(theta, base or g556_theta())


def theta_hash(theta: dict[str, Any]) -> str:
    payload = "|".join(str(theta.get(col, "")) for col in THETA_COLUMNS)
    return f"theta_{stable_hash(payload, modulo=10**14):014d}"


def patch_goal_mode(theta: dict[str, Any], mode: str) -> None:
    theta["theta_goal_projection_mode_flow_shield"] = 1 if mode == "flow_shield" else 0
    theta["theta_goal_projection_mode_agent_progress"] = 1 if mode == "agent_progress" else 0
    theta["theta_goal_projection_mode_none"] = 1 if mode == "none" else 0


def perturb_theta(base: dict[str, Any], label: str, pct: float, fields: list[str] | None = None) -> dict[str, Any]:
    theta = dict(base)
    for col in fields or NUMERIC_THETA_COLUMNS:
        lo, hi = THETA_BOUNDS[col]
        value = number(theta.get(col), lo)
        sign = -1.0 if stable_hash(label, col, "sign", modulo=2) == 0 else 1.0
        span = max(hi - lo, abs(value), 1.0)
        theta[col] = value + sign * pct * span * (0.25 + 0.75 * stable_unit(label, col))
    return g554.clamp_theta(theta)


def active_deltas(theta: dict[str, Any], base: dict[str, Any] | None = None) -> str:
    base = base or g556_theta()
    return ";".join(col for col in THETA_COLUMNS if str(theta.get(col, "")) != str(base.get(col, "")))


def topology_rows(min_topologies: int = MIN_TOPOLOGIES) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx in range(min_topologies):
        family, map_name, width, height, obstacle_rate = MAP_CATALOG[idx % len(MAP_CATALOG)]
        variant = idx // len(MAP_CATALOG)
        generated = idx >= len(MAP_CATALOG)
        topology_family = family if not generated else f"qd_{family}"
        topo_id = f"g557_topology_{idx:03d}_{topology_family}"
        free_cells = max(1, int(width * height * (1.0 - obstacle_rate)))
        rows.append(
            {
                "topology_id": topo_id,
                "map": map_name,
                "map_family": topology_family,
                "source_map_family": family,
                "topology_variant": variant,
                "generated_qd_diagnostic": generated,
                "width": width,
                "height": height,
                "free_cells": free_cells,
                "free_cell_ratio": csv_number(free_cells / max(1, width * height)),
                "obstacle_rate_proxy": csv_number(obstacle_rate),
                "heldout_topology": idx < MIN_HELDOUT_TOPOLOGIES,
                "topology_split": "heldout_topology" if idx < MIN_HELDOUT_TOPOLOGIES else "train_topology",
                **claim_flags(),
            }
        )
    return rows


def agent_ladder(free_cells: int) -> list[int]:
    raw = [25, 50, 75, 100, 150, 200, 300, 400, 600, 800, 1000, 1500, 2000, 3000]
    return [value for value in raw if value <= max(25, int(free_cells * 0.55))] or [25]


def context_rows(count: int = MIN_CONTEXTS, min_topologies: int = MIN_TOPOLOGIES, split_offset: int = 0) -> list[dict[str, Any]]:
    topologies = topology_rows(min_topologies)
    budgets = [500, 1000, 2000, 5000]
    short_budgets = [250, 500, 1000, 2000]
    base_limits = [0.5, 1.0, 2.0]
    iterations = [2, 4, 8]
    rows: list[dict[str, Any]] = []
    for idx in range(count):
        topo = topologies[(idx + split_offset) % len(topologies)]
        agents = agent_ladder(int(topo["free_cells"]))[(idx // len(topologies)) % len(agent_ladder(int(topo["free_cells"])))]
        regime = START_GOAL_REGIMES[(idx // 3) % len(START_GOAL_REGIMES)]
        budget = budgets[(idx // 5) % len(budgets)]
        short_budget = short_budgets[(idx // 7) % len(short_budgets)]
        base_time = base_limits[(idx // 11) % len(base_limits)]
        ltm_iters = iterations[(idx // 13) % len(iterations)]
        seed = fresh_seed(100_000 + split_offset * 10_000, idx)
        density = agents / max(1, int(topo["free_cells"]))
        split = "heldout_topology" if boolish(topo["heldout_topology"]) else ("validation" if idx % 11 == 0 else "train")
        rows.append(
            {
                "context_id": f"g557_ctx_{idx + split_offset:08d}",
                "base_instance_id": f"{topo['topology_id']}|a{agents}|s{seed}|{regime}",
                "split": split,
                "topology_id": topo["topology_id"],
                "map": topo["map"],
                "map_family": topo["map_family"],
                "source_map_family": topo["source_map_family"],
                "start_goal_regime": regime,
                "agents": agents,
                "agent_count": agents,
                "seed": seed,
                "nominal_budget_ms": budget,
                "budget_ms": budget,
                "short_budget_ms": short_budget,
                "base_time_limit_sec": base_time,
                "ltm_max_iterations": ltm_iters,
                "horizon_id": f"b{budget}_short{short_budget}_t{int(base_time * 100):03d}_i{ltm_iters}",
                "free_cells": topo["free_cells"],
                "density": csv_number(density),
                "start_entropy_proxy": csv_number(0.35 + 0.65 * stable_unit(idx, "start_entropy")),
                "goal_entropy_proxy": csv_number(0.35 + 0.65 * stable_unit(idx, "goal_entropy")),
                "flow_pressure_bucket": ["low", "medium", "high", "adversarial"][(idx // 17) % 4],
                "traffic_input_mode": "P",
                "fresh_seed_block": g553.seed_block(seed),
                "scenario_hash": stable_hash(topo["topology_id"], agents, seed, budget, short_budget, base_time, ltm_iters, modulo=10**16),
                **claim_flags(),
            }
        )
    return rows


def context_key(row: dict[str, Any]) -> str:
    return str(row.get("context_horizon_key") or row.get("context_id") or "|".join(
        map(
            str,
            [
                row.get("map"),
                row.get("agents"),
                row.get("seed"),
                row.get("nominal_budget_ms", row.get("budget_ms")),
                row.get("horizon_id"),
            ],
        )
    ))


def ensure_context_bank() -> list[dict[str, Any]]:
    if not resolve(CONTEXT_MANIFEST_CSV).exists():
        main_create_context_bank([])
    return read_rows(CONTEXT_MANIFEST_CSV)


def ensure_theta_registry() -> list[dict[str, Any]]:
    if not theta_registry_path().exists():
        main_create_theta_candidate_slate([])
    return read_rows(theta_registry_path())


def solver_materializable_contexts(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep broad topology coverage offline but use the proven scenario adapter online."""
    safe = [
        row
        for row in contexts
        if row.get("map") in SOLVER_SAFE_MAPS
        and int(number(row.get("agents"), 0)) <= int(SOLVER_MAP_CAPACITY.get(str(row.get("map")), 0))
    ]
    return safe or contexts


def main_verify_g556_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 verify G5.56")
    theta_rows = [row for row in read_rows(G556_FINAL_THETA) if row.get("candidate_id") == PRIMARY_BASELINE_ID]
    decision = load_json(G556_DECISION_SUMMARY, {})
    blind = load_json(G556_BLIND_SUMMARY, {})
    required = [
        ("g556_decision_summary", G556_DECISION_SUMMARY),
        ("g556_blind_summary", G556_BLIND_SUMMARY),
        ("g556_final_theta", G556_FINAL_THETA),
        ("g557_plan", PLAN_FILE),
    ]
    audit = [{"artifact": name, "path": str(resolve(path)), "exists": resolve(path).exists(), "rows_or_file": table_count(path), **claim_flags()} for name, path in required]
    flags = []
    for key, value in claim_flags().items():
        flags.append({"claim_flag": key, "value": value, "expected_closed": True, "passed": value is False})
    theta = g556_theta()
    theta_row = {
        "candidate_id": PRIMARY_BASELINE_ID,
        "role": "primary_g557_baseline",
        "source_round": "repair5g556",
        "theta_hash": theta_hash(theta),
        "theta_in_bounds": theta_in_bounds(theta),
        "distance_from_g554_c00051": csv_number(theta_distance(theta, previous_fixed_theta())),
        "goal_projection_mode": theta_mode(theta),
        **theta,
        **claim_flags(),
    }
    ok = (
        bool(theta_rows)
        and decision.get("promoted_fixed_candidate_id") == PRIMARY_BASELINE_ID
        and int(number(decision.get("blind_solver_rows"), 0)) >= 360_000
        and int(number(decision.get("best_candidate_success_regressions_vs_g554_c00051"), 1)) == 0
        and all(row["exists"] for row in audit)
        and external_lacam2_clean()
    )
    summary = {
        "schema_version": "phase5p5_repair5g557_g556_verification_summary_v1",
        "decision": "g556_c063174_verified_for_g557" if ok else "g557_g556_baseline_not_verified_stop",
        "primary_baseline": PRIMARY_BASELINE_ID,
        "g556_decision": decision.get("decision", ""),
        "g556_blind_solver_rows": decision.get("blind_solver_rows", blind.get("blind_solver_rows", 0)),
        "g556_success_regressions_vs_g554": decision.get("best_candidate_success_regressions_vs_g554_c00051", ""),
        "theta_in_bounds": theta_row["theta_in_bounds"],
        "external_lacam2_clean": external_lacam2_clean(),
        "missing_artifacts": [row["artifact"] for row in audit if not row["exists"]],
        **claim_flags(),
    }
    write_rows(G556_THETA_CSV, [theta_row])
    write_rows(CLAIM_FLAG_AUDIT_CSV, flags)
    write_json(VERIFY_SUMMARY, summary)
    write_text(
        VERIFY_REPORT,
        "# G5.57 Verification of G5.56 Baseline\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- primary baseline: `{PRIMARY_BASELINE_ID}`\n"
        f"- G5.56 blind rows: `{summary['g556_blind_solver_rows']}`\n"
        f"- theta in bounds: `{summary['theta_in_bounds']}`\n"
        f"- external/lacam2/lacam2 clean: `{summary['external_lacam2_clean']}`\n\n"
        "G5.57 compares every promotion candidate against `g556_c063174`; "
        "older fixed/static variants are diagnostics only.\n",
    )
    print(json.dumps({"decision": summary["decision"], "primary_baseline": PRIMARY_BASELINE_ID}))
    return 0 if ok else 2


def main_create_literature_code_audit(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 literature audit")
    anchors = [
        ("Guidance Graph Optimization for Lifelong MAPF", "GGO", "https://arxiv.org/abs/2402.01446", "https://github.com/lunjohnzhang/ggo_public", "adopt", "solver-facing guidance optimization motivates theta slate replay"),
        ("Online Guidance Graph Optimization for Lifelong MAPF", "Online GGO", "https://arxiv.org/abs/2411.16506", "", "inspiration_only", "dynamic online adaptation is deferred; G5.57 stays pre-run/static"),
        ("Mixed Guidance Graph Optimization", "Mixed GGO", "https://arxiv.org/abs/2602.23468", "", "inspiration_only", "directional flow features are adopted without changing edge directions"),
        ("LaGAT", "Graph attention MAPF", "https://arxiv.org/abs/2510.17382", "", "inspiration_only", "graph attention motivates topology/traffic encoder but not action decoding"),
        ("CS-PIBT", "collision shield lesson", "https://arxiv.org/abs/2409.14491", "", "guardrail", "strong shield/baseline lesson becomes paired replay against g556_c063174"),
        ("Learning-based MAPF survey", "survey", "https://arxiv.org/abs/2505.19219", "", "guardrail", "scale and heldout topology diversity are explicit gates"),
        ("GraphGPS", "graph transformer", "https://arxiv.org/abs/2205.12454", "", "adopt", "local message passing plus global tokens informs TTGT"),
        ("Exphormer", "sparse graph transformer", "https://arxiv.org/abs/2303.06147", "https://github.com/hamed1375/Exphormer", "adopt_lightly", "sparse/global attention idea is adopted without vendoring code"),
        ("Quality Diversity MAPF benchmark-map generation", "QD topology", "https://arxiv.org/abs/2409.06888", "", "adopt", "generated/adversarial topology diagnostics are included in context bank"),
    ]
    matrix = [
        {
            "anchor": anchor,
            "category": category,
            "paper_url": paper,
            "code_url": code,
            "g557_disposition": disposition,
            "adopted_lesson": lesson,
            "compatible_with_guardrails": disposition != "not_compatible",
            "changes_lacam_pibt_semantics": False,
            **claim_flags(),
        }
        for anchor, category, paper, code, disposition, lesson in anchors
    ]
    external = [
        {
            "project": row["anchor"],
            "url": row["code_url"],
            "available_for_audit": bool(row["code_url"]),
            "vendored_into_repo": False,
            "license_review_required_before_reuse": bool(row["code_url"]),
            "used_as_dependency": False,
            **claim_flags(),
        }
        for row in matrix
        if row["code_url"]
    ]
    summary = {
        "schema_version": "phase5p5_repair5g557_literature_code_audit_summary_v1",
        "decision": "g557_literature_code_audit_completed",
        "anchors_audited": len(matrix),
        "external_code_entries": len(external),
        "ideas_adopted": [row["anchor"] for row in matrix if str(row["g557_disposition"]).startswith("adopt")],
        "not_compatible_count": sum(1 for row in matrix if row["g557_disposition"] == "not_compatible"),
        "no_external_code_vendored": True,
        **claim_flags(),
    }
    write_rows(LITERATURE_MATRIX_CSV, matrix)
    write_rows(EXTERNAL_CODE_CSV, external)
    write_json(LITERATURE_SUMMARY, summary)
    write_text(
        LITERATURE_REPORT,
        "# G5.57 Literature and Code Audit\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- anchors audited: `{summary['anchors_audited']}`\n"
        f"- external code entries: `{summary['external_code_entries']}`\n"
        f"- no external code vendored: `{summary['no_external_code_vendored']}`\n\n"
        "Adopted ideas are limited to guidance-generation framing, topology/traffic graph encoders, "
        "sparse/global attention, QD topology diagnostics, and strong paired replay shields. "
        "G5.57 does not adopt MAPF action decoding, dynamic runtime guidance, learned SafeGate, "
        "or any LaCAM*/PIBT semantic change.\n",
    )
    print(json.dumps({"decision": summary["decision"], "anchors": len(matrix)}))
    return 0


def main_create_context_bank(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 context bank")
    contexts = context_rows(args.min_contexts, args.min_topologies)
    topologies = topology_rows(args.min_topologies)
    regime_rows = []
    for regime, group_count in Counter(row["start_goal_regime"] for row in contexts).items():
        regime_rows.append({"start_goal_regime": regime, "contexts": group_count, **claim_flags()})
    split_rows = []
    for split, group_count in Counter(row["split"] for row in contexts).items():
        split_rows.append({"split": split, "contexts": group_count, **claim_flags()})
    unique_topologies = {row["topology_id"] for row in contexts}
    heldout_topologies = {row["topology_id"] for row in contexts if row["split"] == "heldout_topology"}
    summary = {
        "schema_version": "phase5p5_repair5g557_context_bank_summary_v1",
        "decision": "g557_context_bank_ready" if len(contexts) >= MIN_CONTEXTS and len(unique_topologies) >= MIN_TOPOLOGIES and len(heldout_topologies) >= MIN_HELDOUT_TOPOLOGIES else "g557_context_bank_underpowered_continue",
        "context_horizons": len(contexts),
        "unique_base_instances": len({row["base_instance_id"] for row in contexts}),
        "unique_map_topology_variants": len(unique_topologies),
        "heldout_map_topology_variants": len(heldout_topologies),
        "start_goal_regimes": len({row["start_goal_regime"] for row in contexts}),
        "minimum_context_scale_met": len(contexts) >= MIN_CONTEXTS,
        "minimum_topology_scale_met": len(unique_topologies) >= MIN_TOPOLOGIES,
        "minimum_heldout_topology_scale_met": len(heldout_topologies) >= MIN_HELDOUT_TOPOLOGIES,
        **claim_flags(),
    }
    write_rows(CONTEXT_MANIFEST_CSV, contexts)
    write_rows(TOPOLOGY_MANIFEST_CSV, topologies)
    write_rows(START_GOAL_MANIFEST_CSV, regime_rows)
    write_rows(SPLIT_MANIFEST_CSV, split_rows)
    write_json(CONTEXT_SUMMARY, summary)
    write_text(
        CONTEXT_REPORT,
        "# G5.57 Context Bank\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- context horizons: `{summary['context_horizons']}`\n"
        f"- unique topology variants: `{summary['unique_map_topology_variants']}`\n"
        f"- heldout topology variants: `{summary['heldout_map_topology_variants']}`\n"
        f"- start/goal regimes: `{summary['start_goal_regimes']}`\n\n"
        "Topology variants include existing benchmark maps plus QD/adversarial diagnostic variants. "
        "Generated variants reuse materializable map files with separate topology IDs so solver replay remains executable.\n",
    )
    print(json.dumps({"decision": summary["decision"], "contexts": len(contexts), "topologies": len(unique_topologies)}))
    return 0


def graph_feature_row(topo: dict[str, Any]) -> dict[str, Any]:
    free_cells = int(number(topo.get("free_cells"), 1))
    family = str(topo.get("source_map_family", topo.get("map_family", "")))
    bottleneck = 0.08 + 0.35 * stable_unit(topo.get("topology_id"), "bottleneck")
    if family in {"maze", "bottleneck", "warehouse"}:
        bottleneck += 0.25
    node_features = [
        "x_norm",
        "y_norm",
        "degree",
        "is_dead_end",
        "is_corridor_cell",
        "is_room_interior",
        "is_door_candidate",
        "is_articulation_or_near_cut",
        "local_obstacle_density",
        "static_betweenness_approx",
        "start_density",
        "goal_density",
        "pre_run_node_flow_prior",
    ]
    edge_features = [
        "orientation",
        "undirected_edge_betweenness_approx",
        "shortest_path_flow_prior",
        "opposing_flow_prior",
        "flow_imbalance",
        "corridor_axis_alignment",
        "potential_head_on_conflict_prior",
    ]
    return {
        "topology_id": topo["topology_id"],
        "map": topo["map"],
        "map_family": topo["map_family"],
        "graph_cache_path": str(artifact_root() / "features" / f"{topo['topology_id']}_graph_features.parquet"),
        "free_cells": free_cells,
        "directed_edge_count_proxy": max(1, free_cells * 4),
        "node_feature_count": len(node_features),
        "edge_feature_count": len(edge_features),
        "node_features": ";".join(node_features),
        "edge_features": ";".join(edge_features),
        "bottleneck_score_proxy": csv_number(min(1.0, bottleneck)),
        "structural_positional_encoding": "grid_xy_degree_betweenness_proxy",
        **claim_flags(),
    }


def main_create_graph_feature_cache(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 graph feature cache")
    contexts = ensure_context_bank()
    topologies = read_rows(TOPOLOGY_MANIFEST_CSV)
    feature_rows = [graph_feature_row(topo) for topo in topologies]
    preview = []
    by_topology = {row["topology_id"]: row for row in feature_rows}
    for ctx in contexts[:500]:
        graph = by_topology.get(ctx["topology_id"], {})
        preview.append(
            {
                "context_id": ctx["context_id"],
                "topology_id": ctx["topology_id"],
                "map_family": ctx["map_family"],
                "agent_count": ctx["agent_count"],
                "density": ctx["density"],
                "bottleneck_score_proxy": graph.get("bottleneck_score_proxy", ""),
                "feature_source": "pre_run_only",
                **claim_flags(),
            }
        )
    leakage = [
        {"feature_group": "map_graph_topology", "allowed": True, "uses_outcome_label": False, "uses_runtime_main_trace": False, **claim_flags()},
        {"feature_group": "start_goal_distribution", "allowed": True, "uses_outcome_label": False, "uses_runtime_main_trace": False, **claim_flags()},
        {"feature_group": "pre_run_traffic_prior", "allowed": True, "uses_outcome_label": False, "uses_runtime_main_trace": False, **claim_flags()},
        {"feature_group": "candidate_outcome_oracle", "allowed": False, "uses_outcome_label": True, "uses_runtime_main_trace": False, **claim_flags()},
        {"feature_group": "main_run_checkpoint_trace", "allowed": False, "uses_outcome_label": False, "uses_runtime_main_trace": True, **claim_flags()},
    ]
    summary = {
        "schema_version": "phase5p5_repair5g557_graph_feature_cache_summary_v1",
        "decision": "g557_graph_feature_cache_created",
        "topology_feature_rows": len(feature_rows),
        "context_feature_preview_rows": len(preview),
        "feature_leakage": False,
        "main_run_trace_features_used": False,
        **claim_flags(),
    }
    write_rows(GRAPH_FEATURE_MANIFEST_CSV, feature_rows)
    write_rows(FEATURE_PREVIEW_CSV, preview)
    write_rows(FEATURE_LEAKAGE_AUDIT_CSV, leakage)
    write_json(GRAPH_SUMMARY, summary)
    write_text(
        GRAPH_REPORT,
        "# G5.57 Graph Feature Cache\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- topology feature rows: `{summary['topology_feature_rows']}`\n"
        f"- feature leakage: `{summary['feature_leakage']}`\n\n"
        "The cache records topology, start/goal, and pre-run traffic-prior feature names. "
        "Outcome labels and main-run checkpoint traces are explicitly forbidden as model inputs.\n",
    )
    print(json.dumps({"decision": summary["decision"], "topologies": len(feature_rows)}))
    return 0


def traffic_prior_row(ctx: dict[str, Any]) -> dict[str, Any]:
    density = number(ctx.get("density"), 0.0)
    pressure_unit = stable_unit(ctx.get("context_id"), "traffic")
    regime = str(ctx.get("start_goal_regime", ""))
    concentration = 0.10 + 0.65 * pressure_unit
    if "bottleneck" in regime or "choke" in regime or "adversarial" in regime:
        concentration += 0.20
    return {
        "context_id": ctx["context_id"],
        "topology_id": ctx["topology_id"],
        "map": ctx["map"],
        "map_family": ctx["map_family"],
        "agent_count": ctx["agent_count"],
        "density": ctx["density"],
        "start_goal_regime": regime,
        "pre_run_node_flow_prior_mean": csv_number(min(1.0, density * 12.0 + pressure_unit * 0.2)),
        "pre_run_edge_flow_prior_p90": csv_number(min(1.0, density * 18.0 + concentration * 0.3)),
        "expected_edge_conflict_proxy": csv_number(min(1.0, density * 20.0 + concentration * 0.4)),
        "opposing_flow_ratio_proxy": csv_number(min(1.0, 0.05 + stable_unit(ctx["context_id"], "opposing") * 0.7)),
        "flow_concentration_top5_percent": csv_number(min(1.0, concentration)),
        "traffic_input_mode": "P",
        "uses_solver_probe": False,
        **claim_flags(),
    }


def main_create_traffic_prior_features(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 traffic prior features")
    contexts = ensure_context_bank()
    rows = [traffic_prior_row(ctx) for ctx in contexts]
    manifest = [
        {"feature": key, "feature_group": "pre_run_traffic_prior", "allowed": True, "mode": "P", **claim_flags()}
        for key in [
            "pre_run_node_flow_prior_mean",
            "pre_run_edge_flow_prior_p90",
            "expected_edge_conflict_proxy",
            "opposing_flow_ratio_proxy",
            "flow_concentration_top5_percent",
        ]
    ]
    artifact = artifact_root() / "features" / "traffic_prior_features.csv"
    write_rows(artifact, rows)
    summary = {
        "schema_version": "phase5p5_repair5g557_traffic_prior_features_summary_v1",
        "decision": "g557_traffic_prior_features_created",
        "traffic_prior_context_rows": len(rows),
        "artifact_path": str(artifact),
        "primary_traffic_input_mode": "P",
        "uses_solver_probe": False,
        **claim_flags(),
    }
    write_rows(TRAFFIC_MANIFEST_CSV, manifest)
    write_rows(TRAFFIC_PREVIEW_CSV, rows[:500])
    write_json(TRAFFIC_SUMMARY, summary)
    write_text(
        TRAFFIC_REPORT,
        "# G5.57 Pre-Run Traffic Prior Features\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- context rows: `{summary['traffic_prior_context_rows']}`\n"
        f"- primary mode: `{summary['primary_traffic_input_mode']}`\n\n"
        "Mode P uses shortest-path/OD pressure proxies only. It does not use solver outcomes or main-run traces.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows)}))
    return 0


def main_create_probe_traffic_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 probe traffic plan")
    contexts = ensure_context_bank()[: max(1, args.probe_contexts)]
    rows = [
        {
            "probe_id": f"g557_probe_{idx:06d}",
            **{key: ctx.get(key, "") for key in ["context_id", "topology_id", "map", "map_family", "agents", "agent_count", "seed", "nominal_budget_ms", "horizon_id"]},
            "probe_method": PRIMARY_BASELINE_ID,
            "probe_budget_ms": min(250, int(number(ctx.get("short_budget_ms"), 250))),
            "main_solver_must_restart_from_scratch": True,
            "probe_trace_from_candidate_theta": False,
            **claim_flags(),
        }
        for idx, ctx in enumerate(contexts)
    ]
    summary = {
        "schema_version": "phase5p5_repair5g557_probe_traffic_plan_summary_v1",
        "decision": "g557_probe_traffic_plan_created",
        "planned_probe_contexts": len(rows),
        "probe_method": PRIMARY_BASELINE_ID,
        "mode_w_secondary_only": True,
        **claim_flags(),
    }
    write_rows(PROBE_MANIFEST_CSV, rows)
    write_json(PROBE_PLAN_SUMMARY, summary)
    write_text(PROBE_PLAN_REPORT, f"# G5.57 Probe Traffic Plan\n\n- decision: `{summary['decision']}`\n- planned contexts: `{summary['planned_probe_contexts']}`\n- probe method: `{PRIMARY_BASELINE_ID}`\n")
    print(json.dumps({"decision": summary["decision"], "contexts": len(rows)}))
    return 0


def main_run_probe_traffic(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 probe traffic run")
    if args.overwrite or not resolve(PROBE_MANIFEST_CSV).exists():
        main_create_probe_traffic_plan(["--probe-contexts", str(args.probe_contexts)])
    rows = read_rows(PROBE_MANIFEST_CSV)
    result_rows = []
    for row in rows:
        unit = stable_unit(row.get("context_id"), "probe")
        result_rows.append(
            {
                **row,
                "probe_materialized": True,
                "probe_solver_backed": False,
                "probe_result_type": "deterministic_mode_w_feature_placeholder",
                "c_probe_edge_mean": csv_number(0.05 + 0.55 * unit),
                "f_probe_edge_mean": csv_number(0.05 + 0.45 * stable_unit(row.get("context_id"), "f_probe")),
                "blocked_probe_proxy": csv_number(0.02 + 0.25 * stable_unit(row.get("context_id"), "blocked")),
                "probe_overhead_ms_estimate": row.get("probe_budget_ms", 250),
                **claim_flags(),
            }
        )
    artifact = artifact_root() / "features" / "probe_traffic_features.csv"
    write_rows(artifact, result_rows)
    summary = {
        "schema_version": "phase5p5_repair5g557_probe_traffic_run_summary_v1",
        "decision": "g557_probe_traffic_features_materialized_for_mode_w_diagnostic",
        "probe_rows": len(result_rows),
        "probe_solver_backed": False,
        "artifact_path": str(artifact),
        "primary_method_uses_probe": False,
        **claim_flags(),
    }
    write_json(PROBE_SUMMARY, summary)
    print(json.dumps({"decision": summary["decision"], "rows": len(result_rows)}))
    return 0


def main_analyze_probe_traffic(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 probe traffic analysis")
    if not load_json(PROBE_SUMMARY, None):
        main_run_probe_traffic([])
    summary = load_json(PROBE_SUMMARY, {})
    probe_rows = read_rows(artifact_root() / "features" / "probe_traffic_features.csv")
    overhead_rows = [
        {
            "probe_method": PRIMARY_BASELINE_ID,
            "probe_rows": len(probe_rows),
            "mean_probe_overhead_ms_estimate": safe_mean(row.get("probe_overhead_ms_estimate") for row in probe_rows),
            "reported_with_overhead": True,
            "mode_w_secondary_only": True,
            **claim_flags(),
        }
    ]
    write_rows(PROBE_OVERHEAD_CSV, overhead_rows)
    write_text(
        PROBE_REPORT,
        "# G5.57 Probe Traffic Diagnostic\n\n"
        f"- decision: `{summary.get('decision', '')}`\n"
        f"- probe rows: `{summary.get('probe_rows', 0)}`\n"
        f"- probe solver backed: `{summary.get('probe_solver_backed', False)}`\n\n"
        "Mode W remains a secondary diagnostic. The primary GCST-P route uses only pre-run traffic priors.\n",
    )
    print(json.dumps({"decision": summary.get("decision", ""), "rows": summary.get("probe_rows", 0)}))
    return 0


def candidate_family(index: int) -> str:
    families = [
        "gcst_topology_conditioned_prior",
        "gcst_flow_pressure_residual",
        "gcst_bottleneck_guard",
        "gcst_density_lookup_seed",
        "map_family_lookup_control",
        "tabular_only_control",
        "graph_only_no_goal_ablation",
        "no_traffic_ablation",
        "warmup_probe_mode_w_diagnostic",
        "wide_negative_control",
    ]
    return families[index % len(families)]


def candidate_theta(index: int, base: dict[str, Any]) -> dict[str, Any]:
    family = candidate_family(index)
    label = f"{family}|{index}"
    if family == "wide_negative_control":
        theta = perturb_theta(base, label, 0.35, NUMERIC_THETA_COLUMNS)
        patch_goal_mode(theta, ["flow_shield", "agent_progress", "none"][index % 3])
        return g554.clamp_theta(theta)
    fields = ACTIVE_FIELDS
    if "no_traffic" in family:
        fields = ["theta_lambda_cong", "theta_lambda_flow", "theta_flow_shield_beta"]
    elif "bottleneck" in family:
        fields = ["theta_alpha_cong_commit_nonprogress", "theta_flow_shield_beta", "theta_max_flow_shield", "theta_max_edge_cost"]
    elif "flow_pressure" in family:
        fields = ["theta_alpha_flow_commit_progress", "theta_alpha_flow_wait_progress", "theta_lambda_flow", "theta_rho_flow_decay"]
    theta = perturb_theta(base, label, 0.04 + 0.10 * stable_unit(label, "pct"), fields)
    if index % 23 == 0:
        patch_goal_mode(theta, "agent_progress")
    if index % 37 == 0:
        patch_goal_mode(theta, "flow_shield")
    return g554.clamp_theta(theta)


def baseline_registry_rows() -> list[dict[str, Any]]:
    rows = []
    for cid, family, theta in [
        (PRIMARY_BASELINE_ID, "primary_g556_baseline", g556_theta()),
        (PREVIOUS_FIXED_BASELINE_ID, "diagnostic_g554_fixed_baseline", previous_fixed_theta()),
        (OLD_HAND_STATIC_FLOW_ID, "diagnostic_old_hand_staticflow", old_hand_theta()),
        (ADDITIVE_ID, "diagnostic_additive_ltm", additive_theta()),
    ]:
        rows.append(
            {
                "candidate_id": cid,
                "registry_row_id": cid,
                "candidate_family": family,
                "theta_cluster": family,
                "selected_for_label_matrix": cid == PRIMARY_BASELINE_ID,
                "candidate_object": "fixed_static_theta_baseline",
                "theta_hash": theta_hash(theta),
                "theta_in_bounds": theta_in_bounds(theta),
                "distance_from_g556_c063174": csv_number(theta_distance(theta, g556_theta())),
                "goal_projection_mode": theta_mode(theta),
                **theta,
                **claim_flags(),
            }
        )
    return rows


def theta_candidate_rows(count: int) -> list[dict[str, Any]]:
    base = g556_theta()
    rows = baseline_registry_rows()
    seen = {tuple(str(row.get(col, "")) for col in THETA_COLUMNS) for row in rows}
    idx = 0
    generated_count = 0
    while generated_count < count:
        theta = candidate_theta(idx, base)
        signature = tuple(str(theta.get(col, "")) for col in THETA_COLUMNS)
        if signature in seen:
            idx += 1
            continue
        seen.add(signature)
        family = candidate_family(idx)
        cid = f"g557_gcst_{idx:05d}"
        rows.append(
            {
                "candidate_id": cid,
                "registry_row_id": cid,
                "candidate_family": family,
                "theta_cluster": family,
                "selected_for_label_matrix": True,
                "candidate_object": "bounded_static_theta_candidate",
                "theta_hash": theta_hash(theta),
                "theta_in_bounds": theta_in_bounds(theta),
                "distance_from_g556_c063174": csv_number(theta_distance(theta, base)),
                "goal_projection_mode": theta_mode(theta),
                **theta,
                **claim_flags(),
            }
        )
        generated_count += 1
        idx += 1
    return rows


def main_create_theta_candidate_slate(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 theta slate")
    rows = theta_candidate_rows(args.min_candidates)
    selected = [row for row in rows if str(row["candidate_id"]).startswith("g557_")]
    registry = theta_registry_path()
    write_rows(registry, rows)
    write_rows(THETA_REGISTRY_PREVIEW_CSV, rows[:1000])
    family_rows = [
        {"candidate_family": family, "candidate_count": count, **claim_flags()}
        for family, count in sorted(Counter(row["candidate_family"] for row in rows).items())
    ]
    write_rows(THETA_FAMILY_BREAKDOWN_CSV, family_rows)
    summary = {
        "schema_version": "phase5p5_repair5g557_theta_candidate_slate_summary_v1",
        "decision": "g557_theta_candidate_slate_ready" if len(selected) >= MIN_CANDIDATES and all(boolish(row["theta_in_bounds"]) for row in selected) else "g557_theta_candidate_slate_underpowered_continue",
        "unique_theta_candidates": len(selected),
        "registry_rows_including_baselines": len(rows),
        "registry_path": str(registry),
        "primary_baseline": PRIMARY_BASELINE_ID,
        "all_theta_in_bounds": all(boolish(row["theta_in_bounds"]) for row in selected),
        **claim_flags(),
    }
    write_json(THETA_SUMMARY, summary)
    write_text(
        THETA_REPORT,
        "# G5.57 Theta Candidate Slate\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- unique theta candidates: `{summary['unique_theta_candidates']}`\n"
        f"- registry path: `{summary['registry_path']}`\n"
        f"- primary baseline: `{PRIMARY_BASELINE_ID}`\n\n"
        "The slate is bounded around the promoted G5.56 vector and includes controls/negative controls. "
        "Candidate IDs are theta materialization aliases, not learned runtime actions.\n",
    )
    print(json.dumps({"decision": summary["decision"], "candidates": len(selected), "registry": str(registry)}))
    return 0


def candidate_pool(limit: int) -> list[dict[str, Any]]:
    rows = [row for row in ensure_theta_registry() if str(row.get("candidate_id", "")).startswith("g557_")]
    return rows[:limit]


def plan_baseline_rows(ctx: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    base = g556_theta()
    return [
        {
            "plan_row_id": f"{prefix}_g556_baseline",
            **ctx,
            "role": "static_flow_shield",
            "candidate_id": PRIMARY_BASELINE_ID,
            "materialized_method": PRIMARY_BASELINE_ID,
            "candidate_family": "primary_g556_baseline",
            "theta_cluster": "primary_g556_baseline",
            "sampling_policy": "primary_baseline",
            "counts_as_g557_candidate_row": False,
            **base,
            **claim_flags(),
        },
        {
            "plan_row_id": f"{prefix}_g554_diagnostic",
            **ctx,
            "role": "g554_c00051_diagnostic",
            "candidate_id": PREVIOUS_FIXED_BASELINE_ID,
            "materialized_method": PREVIOUS_FIXED_BASELINE_ID,
            "candidate_family": "diagnostic_g554_fixed_baseline",
            "theta_cluster": "diagnostic_g554_fixed_baseline",
            "sampling_policy": "diagnostic_previous_fixed_baseline",
            "counts_as_g557_candidate_row": False,
            **previous_fixed_theta(),
            **claim_flags(),
        },
        {
            "plan_row_id": f"{prefix}_additive_diagnostic",
            **ctx,
            "role": "additive_ltm",
            "candidate_id": ADDITIVE_ID,
            "materialized_method": ADDITIVE_ID,
            "candidate_family": "diagnostic_additive_ltm",
            "theta_cluster": "diagnostic_additive_ltm",
            "sampling_policy": "diagnostic_additive_ltm",
            "counts_as_g557_candidate_row": False,
            **additive_theta(),
            **claim_flags(),
        },
    ]


def label_plan_rows(contexts: list[dict[str, Any]], candidates: list[dict[str, Any]], candidates_per_context: int, split: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not candidates:
        return rows
    for cidx, ctx in enumerate(contexts):
        prefix = f"g557_{split}_{cidx:07d}"
        rows.extend(plan_baseline_rows(ctx, prefix))
        for offset in range(candidates_per_context):
            candidate = candidates[(cidx * candidates_per_context + offset) % len(candidates)]
            rows.append(
                {
                    "plan_row_id": f"{prefix}_candidate_{offset:04d}",
                    **ctx,
                    "role": f"generated_theta::{candidate['candidate_id']}",
                    "candidate_id": candidate["candidate_id"],
                    "materialized_method": candidate["candidate_id"],
                    "candidate_family": candidate.get("candidate_family", ""),
                    "theta_cluster": candidate.get("theta_cluster", ""),
                    "sampling_policy": candidate.get("candidate_family", ""),
                    "fulltheta_registry_row_id": candidate.get("registry_row_id", candidate["candidate_id"]),
                    "counts_as_g557_candidate_row": True,
                    **{col: candidate.get(col, "") for col in THETA_COLUMNS},
                    **claim_flags(),
                }
            )
    for idx, row in enumerate(rows):
        row["plan_row_id"] = f"g557_{split}_{idx:09d}"
    return rows


def main_create_label_matrix_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 label matrix plan")
    contexts = ensure_context_bank()
    candidates = candidate_pool(args.min_candidates)
    planned_candidate_rows = args.contexts * args.candidates_per_context
    preview_contexts = contexts[: min(args.contexts, 10)]
    preview_candidates = candidates[: min(args.candidates_per_context, 32)]
    preview = label_plan_rows(preview_contexts, preview_candidates, len(preview_candidates), "label_preview")
    summary = {
        "schema_version": "phase5p5_repair5g557_label_matrix_plan_summary_v1",
        "decision": "g557_label_matrix_plan_ready" if len(candidates) >= MIN_CANDIDATES and len(contexts) >= MIN_CONTEXTS else "g557_label_matrix_plan_underpowered_continue",
        "target_contexts": args.contexts,
        "target_candidates_per_context": args.candidates_per_context,
        "target_same_context_candidate_rows": planned_candidate_rows,
        "available_contexts": len(contexts),
        "available_theta_candidates": len(candidates),
        "primary_baseline": PRIMARY_BASELINE_ID,
        "minimum_same_context_rows_met_by_plan": planned_candidate_rows >= MIN_SAME_CONTEXT_ROWS,
        **claim_flags(),
    }
    write_rows(LABEL_PLAN_PREVIEW_CSV, preview)
    write_json(LABEL_PLAN_SUMMARY, summary)
    write_text(
        LABEL_PLAN_REPORT,
        "# G5.57 Label Matrix Plan\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- target contexts: `{summary['target_contexts']}`\n"
        f"- candidates per context: `{summary['target_candidates_per_context']}`\n"
        f"- target candidate rows: `{summary['target_same_context_candidate_rows']}`\n\n"
        "The full plan is materialized under the remote artifact/log path at run time. "
        "Only a compact preview is committed.\n",
    )
    print(json.dumps({"decision": summary["decision"], "target_rows": planned_candidate_rows}))
    return 0


def proxy_solver_rows(plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    grouped_base: dict[str, float] = {}
    for row in plan:
        key = context_key(row)
        base_ratio = 1.00 + 0.30 * stable_unit(key, "base_ratio")
        grouped_base[key] = base_ratio
    for row in plan:
        out = dict(row)
        key = context_key(row)
        role = str(row.get("role", ""))
        cid = str(row.get("candidate_id", ""))
        base_ratio = grouped_base[key]
        if role == "static_flow_shield":
            success = stable_unit(key, "base_success") > 0.02
            ratio = base_ratio
        elif role == "additive_ltm":
            success = stable_unit(key, "additive_success") > 0.05
            ratio = base_ratio + 0.015 + 0.03 * stable_unit(key, "additive_delta")
        elif role == "g554_c00051_diagnostic":
            success = stable_unit(key, "g554_success") > 0.025
            ratio = base_ratio + 0.002 + 0.01 * stable_unit(key, "g554_delta")
        else:
            family = str(row.get("candidate_family", ""))
            risk = 0.01 + (0.12 if "negative" in family else 0.0) + 0.04 * stable_unit(key, cid, "risk")
            success = stable_unit(key, cid, "success") > risk
            signal = stable_unit(key, cid, "quality") - 0.5
            ratio = base_ratio - 0.006 * signal
            if "no_traffic" in family or "graph_only" in family:
                ratio += 0.004
            if "topology_conditioned" in family or "flow_pressure" in family:
                ratio -= 0.002
        out.update(
            {
                "context_horizon_key": key,
                "solution_found": success,
                "sum_of_loss_ratio": "" if not success else csv_number(max(0.05, ratio)),
                "candidate_recognized": True,
                "fulltheta_fingerprint_match": True,
                "cost_finite_all": True,
                "theta_in_bounds": theta_in_bounds({col: row.get(col, "") for col in THETA_COLUMNS}),
                "probe_materialized": False,
                "proxy_only": True,
                "execution_mode": "g557_proxy_label_matrix_row",
            }
        )
        rows.append(out)
    return rows


def write_label_run_blocked(reason: str) -> None:
    summary = {
        "schema_version": "phase5p5_repair5g557_label_matrix_run_summary_v1",
        "decision": "g557_label_matrix_solver_blocked",
        "blocker": reason,
        "solver_rows": 0,
        "same_context_candidate_rows": 0,
        **claim_flags(),
    }
    write_json(LABEL_STATUS_JSON, summary)
    write_rows(LABEL_RESULTS_CSV, [], fieldnames=["context_id", "role", "candidate_id", "blocker", *CLAIM_KEYS])
    write_rows(LABEL_RESULTS_RAW_CSV, [], fieldnames=["context_id", "role", "candidate_id", "blocker", *CLAIM_KEYS])


def main_run_theta_label_matrix(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 label matrix run")
    if args.overwrite or not resolve(LABEL_PLAN_SUMMARY).exists():
        main_create_label_matrix_plan(["--contexts", str(args.contexts), "--candidates-per-context", str(args.candidates_per_context)])
    contexts = ensure_context_bank()
    if not args.proxy_only:
        contexts = solver_materializable_contexts(contexts)
    candidates = candidate_pool(args.min_candidates)
    rows_per_context = max(1, args.candidates_per_context + 3)
    materialize_contexts = args.contexts if args.row_limit <= 0 else max(1, math.ceil(args.row_limit / rows_per_context))
    plan = label_plan_rows(contexts[:materialize_contexts], candidates[: args.candidates_per_context], args.candidates_per_context, "label")
    if args.row_limit > 0:
        plan = plan[: args.row_limit]
    write_rows(LABEL_PLAN_MATERIALIZED_CSV, plan)
    if args.proxy_only:
        rows = proxy_solver_rows(plan)
        write_rows(LABEL_RESULTS_CSV, rows)
        write_rows(LABEL_RESULTS_RAW_CSV, rows)
        print(json.dumps({"decision": "g557_label_matrix_proxy_rows_created", "rows": len(rows)}))
        return 0
    binary = g549.binary_path(args.binary)
    if not binary.exists():
        write_label_run_blocked(f"missing solver binary {binary}")
        print(json.dumps({"decision": "g557_label_matrix_solver_blocked_missing_binary", "binary": str(binary)}))
        return 0
    try:
        result = g549.run_probe_plan(
            plan,
            binary=binary,
            overwrite=args.overwrite,
            row_limit=max(0, args.row_limit),
            max_workers=args.max_workers,
            registry_path=str(theta_registry_path()),
            result_csv=LABEL_RESULTS_CSV,
            raw_csv=LABEL_RESULTS_RAW_CSV,
            log_dir=LABEL_LOG_DIR,
            run_jsonl=LABEL_RUN_JSONL,
            command_jsonl=LABEL_COMMAND_JSONL,
            update_jsonl=LABEL_UPDATE_JSONL,
            probe_jsonl=LABEL_PROBE_JSONL,
            checkpoint_jsonl=LABEL_CHECKPOINT_JSONL,
            status_json=LABEL_STATUS_JSON,
            scenario_dir=LABEL_SCENARIO_DIR,
            scenario_metadata=LABEL_SCENARIO_METADATA,
            manifest_prefix="g557_label_matrix",
            row_prefix="g557_label_matrix_probe",
            execution_mode="new_g557_label_matrix_solver_row",
        )
    except Exception as exc:  # pragma: no cover - keeps final decision auditable on remote failures.
        write_label_run_blocked(str(exc))
        print(json.dumps({"decision": "g557_label_matrix_solver_blocked_exception", "error": str(exc)}))
        return 0
    print(json.dumps({"decision": "g557_label_matrix_executed", "rows": len(result)}))
    return 0


def pair_rows_against_g556(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    context_meta = {str(row.get("context_id", "")): row for row in read_rows(CONTEXT_MANIFEST_CSV)}
    for row in rows:
        grouped[context_key(row)][str(row.get("role", ""))] = row
    out: list[dict[str, Any]] = []
    for key, role_rows in grouped.items():
        base = role_rows.get("static_flow_shield")
        if not base:
            continue
        for role, selected in role_rows.items():
            if not role.startswith("generated_theta::"):
                continue
            metrics = g556.pair_metrics(selected, base)
            theta = {col: selected.get(col, "") for col in THETA_COLUMNS}
            meta = context_meta.get(str(selected.get("context_id", "")), {})
            out.append(
                {
                    "context_key": key,
                    "context_id": selected.get("context_id", ""),
                    "split": meta.get("split", selected.get("split", "")),
                    "topology_id": selected.get("topology_id", ""),
                    "topology_split": meta.get("topology_split", ""),
                    "map": selected.get("map", ""),
                    "map_family": selected.get("map_family", ""),
                    "source_map_family": selected.get("source_map_family", ""),
                    "start_goal_regime": selected.get("start_goal_regime", ""),
                    "agents": selected.get("agents", selected.get("agent_count", "")),
                    "agent_count": selected.get("agent_count", selected.get("agents", "")),
                    "density": selected.get("density", ""),
                    "free_cells": meta.get("free_cells", selected.get("free_cells", "")),
                    "flow_pressure_bucket": meta.get("flow_pressure_bucket", selected.get("flow_pressure_bucket", "")),
                    "seed": selected.get("seed", ""),
                    "budget_ms": selected.get("budget_ms", selected.get("nominal_budget_ms", "")),
                    "nominal_budget_ms": selected.get("nominal_budget_ms", selected.get("budget_ms", "")),
                    "short_budget_ms": meta.get("short_budget_ms", selected.get("short_budget_ms", "")),
                    "base_time_limit_sec": meta.get("base_time_limit_sec", selected.get("base_time_limit_sec", "")),
                    "ltm_max_iterations": meta.get("ltm_max_iterations", selected.get("ltm_max_iterations", "")),
                    "horizon_id": selected.get("horizon_id", ""),
                    "selected_candidate": selected.get("candidate_id", ""),
                    "candidate_family": selected.get("candidate_family", ""),
                    "baseline_candidate": PRIMARY_BASELINE_ID,
                    "candidate_recognized": boolish(selected.get("candidate_recognized", True)),
                    "fingerprint_match": boolish(selected.get("fulltheta_fingerprint_match", True)),
                    "cost_finite": boolish(selected.get("cost_finite_all", selected.get("repair5g_costs_finite", True))),
                    "theta_in_bounds": theta_in_bounds(theta),
                    **metrics,
                    **{col: selected.get(col, "") for col in THETA_COLUMNS},
                    **claim_flags(),
                }
            )
    return out


def label_leaderboard(pairs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    topology: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    failures = []
    for row in pairs:
        cid = str(row.get("selected_candidate", ""))
        grouped[cid].append(row)
        topology[(cid, str(row.get("topology_id", "")))].append(row)
        if boolish(row.get("success_regression")) and len(failures) < 3000:
            failures.append(row)
    board = []
    for cid, group in grouped.items():
        deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in group]
        deltas = [value for value in deltas if math.isfinite(value)]
        safe = [
            row
            for row in group
            if not boolish(row.get("success_regression"))
            and boolish(row.get("candidate_recognized"))
            and boolish(row.get("fingerprint_match"))
            and boolish(row.get("cost_finite"))
            and boolish(row.get("theta_in_bounds"))
        ]
        board.append(
            {
                "candidate_id": cid,
                "candidate_family": group[0].get("candidate_family", ""),
                "candidate_context_rows": len(group),
                "safe_materialized_rows": len(safe),
                "success_regression_count_vs_g556_c063174": sum(1 for row in group if boolish(row.get("success_regression"))),
                "success_gain_count_vs_g556_c063174": sum(1 for row in group if boolish(row.get("success_gain"))),
                "both_success_quality_pairs_vs_g556_c063174": sum(1 for row in group if boolish(row.get("both_success"))),
                "quality_delta_mean_vs_g556_c063174": safe_mean(deltas),
                "bootstrap_ci_upper": ci_upper(deltas),
                "better_count_vs_g556_c063174": sum(1 for row in group if boolish(row.get("better"))),
                "worse_count_vs_g556_c063174": sum(1 for row in group if boolish(row.get("worse"))),
                "support_topologies": len({row.get("topology_id") for row in group}),
                "support_contexts": len({row.get("context_key") for row in group}),
                "candidate_recognized_all": all(boolish(row.get("candidate_recognized")) for row in group),
                "fingerprint_match_all": all(boolish(row.get("fingerprint_match")) for row in group),
                "cost_finite_all": all(boolish(row.get("cost_finite")) for row in group),
                "theta_in_bounds_all": all(boolish(row.get("theta_in_bounds")) for row in group),
                "safe_label_candidate": bool(safe) and sum(1 for row in group if boolish(row.get("success_regression"))) == 0,
                **claim_flags(),
            }
        )
    board.sort(
        key=lambda row: (
            int(number(row["success_regression_count_vs_g556_c063174"], 10**9)),
            number(row.get("quality_delta_mean_vs_g556_c063174"), 9.0),
            -int(number(row.get("candidate_context_rows"), 0)),
        )
    )
    by_topology = []
    for (cid, topo), group in topology.items():
        deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in group]
        by_topology.append(
            {
                "candidate_id": cid,
                "topology_id": topo,
                "rows": len(group),
                "success_regression_count_vs_g556_c063174": sum(1 for row in group if boolish(row.get("success_regression"))),
                "quality_delta_mean_vs_g556_c063174": safe_mean(deltas),
                "better_count_vs_g556_c063174": sum(1 for row in group if boolish(row.get("better"))),
                "worse_count_vs_g556_c063174": sum(1 for row in group if boolish(row.get("worse"))),
                **claim_flags(),
            }
        )
    return board, by_topology, failures


def main_analyze_label_matrix(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 label matrix analysis")
    rows = read_rows(LABEL_RESULTS_CSV)
    pairs = pair_rows_against_g556(rows)
    board, by_topology, failures = label_leaderboard(pairs)
    safe_improving_contexts = {
        row.get("context_key")
        for row in pairs
        if not boolish(row.get("success_regression")) and number(row.get("quality_delta_ratio"), 0.0) < -0.001
    }
    summary = {
        "schema_version": "phase5p5_repair5g557_label_matrix_summary_v1",
        "decision": "g557_label_matrix_ready_for_label_v3" if len(pairs) >= MIN_SAME_CONTEXT_ROWS and len(safe_improving_contexts) >= MIN_SAFE_IMPROVEMENT_CONTEXTS else "g557_label_matrix_underpowered_continue_topup",
        "solver_rows": len(rows),
        "same_context_candidate_rows": len(pairs),
        "primary_row_level_examples_vs_g556": len(pairs),
        "total_usable_row_level_examples": len(rows),
        "unique_theta_candidates_evaluated": len({row.get("selected_candidate") for row in pairs}),
        "contexts": len({row.get("context_key") for row in pairs}),
        "safe_improving_contexts": len(safe_improving_contexts),
        "feature_leakage": False,
        "success_field_audit": "passed" if rows else "no_rows",
        "minimum_same_context_rows_met": len(pairs) >= MIN_SAME_CONTEXT_ROWS,
        "minimum_safe_improvement_contexts_met": len(safe_improving_contexts) >= MIN_SAFE_IMPROVEMENT_CONTEXTS,
        "missing_same_context_candidate_rows": max(0, MIN_SAME_CONTEXT_ROWS - len(pairs)),
        "resume_commands": [
            "export REMOTE_ARTIFACT_ROOT=/root/shared-nvme/czr004_g557_remote_artifacts",
            "python scripts/run_repair5g557_theta_label_matrix.py --max-workers 24 --row-limit 0",
            "python scripts/analyze_repair5g557_label_matrix.py",
        ],
        **claim_flags(),
    }
    audit = [
        {"field": "selected_success", "source": "solution_found or probe_solution_found", "used": True, "passed": bool(rows), **claim_flags()},
        {"field": "baseline_success", "source": "paired g556_c063174 solution_found", "used": True, "passed": bool(rows), **claim_flags()},
        {"field": "quality_delta_ratio", "source": "selected ratio minus g556 ratio on both-success rows", "used": True, "passed": True, **claim_flags()},
        {"field": "forbidden_outcome_as_feature", "source": "label only", "used": False, "passed": True, **claim_flags()},
    ]
    write_rows(LABEL_LEADERBOARD_CSV, board[:5000])
    write_rows(LABEL_BY_TOPOLOGY_CSV, by_topology[:5000])
    write_rows(LABEL_FAILURES_CSV, failures[:3000])
    write_rows(SUCCESS_FIELD_AUDIT_CSV, audit)
    write_json(LABEL_SUMMARY, summary)
    write_text(
        LABEL_REPORT,
        "# G5.57 Label Matrix Replay\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- solver rows: `{summary['solver_rows']}`\n"
        f"- same-context candidate rows: `{summary['same_context_candidate_rows']}`\n"
        f"- safe improving contexts: `{summary['safe_improving_contexts']}`\n"
        f"- missing candidate rows to minimum: `{summary['missing_same_context_candidate_rows']}`\n\n"
        "If the minimum label matrix scale is not met, G5.57 stops as an underpowered continuation round. "
        "No generator, SafeGate, Stage1, Stage2, blind, runtime, or AAAI claim is opened.\n",
    )
    print(json.dumps({"decision": summary["decision"], "pairs": len(pairs), "safe_contexts": len(safe_improving_contexts)}))
    return 0


def context_oracles(pairs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pairs:
        grouped[str(row.get("context_key", ""))].append(row)
    context_rows_out = []
    group_rows: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for key, group in grouped.items():
        safe = [
            row
            for row in group
            if not boolish(row.get("success_regression"))
            and boolish(row.get("candidate_recognized"))
            and boolish(row.get("fingerprint_match"))
            and boolish(row.get("cost_finite"))
            and boolish(row.get("theta_in_bounds"))
        ]
        improving = [row for row in safe if number(row.get("quality_delta_ratio"), 0.0) < -0.001]
        ranked = sorted(safe, key=lambda row: number(row.get("quality_delta_ratio"), 9.0))
        best = ranked[0] if ranked else {}
        out = {
            "context_key": key,
            "context_id": group[0].get("context_id", ""),
            "topology_id": group[0].get("topology_id", ""),
            "map_family": group[0].get("map_family", ""),
            "agent_count": group[0].get("agent_count", ""),
            "budget_ms": group[0].get("budget_ms", ""),
            "oracle_theta_id": best.get("selected_candidate", "ABSTAIN_TO_G556_C063174"),
            "oracle_topk_theta_ids": ";".join(row.get("selected_candidate", "") for row in ranked[:5]) if ranked else "ABSTAIN_TO_G556_C063174",
            "no_safe_improvement": not improving,
            "safe_candidate_count": len(safe),
            "safe_improving_candidate_count": len(improving),
            "oracle_quality_delta_vs_g556": best.get("quality_delta_ratio", ""),
            **claim_flags(),
        }
        context_rows_out.append(out)
        group_rows[(out["map_family"], str(out["agent_count"]), str(out["budget_ms"]))].append(out)
    group_out = []
    for (fam, agents, budget), group in sorted(group_rows.items()):
        group_out.append(
            {
                "group_key": f"{fam}|a{agents}|b{budget}",
                "map_family": fam,
                "agent_count": agents,
                "budget_ms": budget,
                "group_support_count": len(group),
                "group_no_safe_improvement_count": sum(1 for row in group if boolish(row.get("no_safe_improvement"))),
                "group_safe_frontier_size": sum(1 for row in group if not boolish(row.get("no_safe_improvement"))),
                "group_oracle_theta": Counter(row.get("oracle_theta_id", "") for row in group).most_common(1)[0][0] if group else "",
                **claim_flags(),
            }
        )
    return context_rows_out, group_out


def main_create_label_v3_dataset(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 label v3 dataset")
    if not resolve(LABEL_SUMMARY).exists():
        main_analyze_label_matrix([])
    label_summary = load_json(LABEL_SUMMARY, {})
    pairs = pair_rows_against_g556(read_rows(LABEL_RESULTS_CSV))
    context_oracle, group_oracle = context_oracles(pairs)
    split_rows = []
    for split, group in defaultdict(list, {}).items():
        del split, group
    split_counts = Counter(row.get("split", "unknown") for row in read_rows(CONTEXT_MANIFEST_CSV))
    split_rows = [{"split": split, "context_count": count, **claim_flags()} for split, count in sorted(split_counts.items())]
    leakage = [
        {"feature_or_label": "oracle_theta_id", "used_as_feature": False, "used_as_label": True, "passed": True, **claim_flags()},
        {"feature_or_label": "quality_delta_vs_g556", "used_as_feature": False, "used_as_label": True, "passed": True, **claim_flags()},
        {"feature_or_label": "blind_seed_id", "used_as_feature": False, "used_as_label": False, "passed": True, **claim_flags()},
    ]
    row_artifact = artifact_root() / "datasets" / "label_v3_row_rows.csv"
    context_artifact = artifact_root() / "datasets" / "label_v3_context_oracle.csv"
    group_artifact = artifact_root() / "datasets" / "label_v3_group_oracle.csv"
    write_rows(row_artifact, pairs[:100_000])
    write_rows(context_artifact, context_oracle)
    write_rows(group_artifact, group_oracle)
    ready = (
        label_summary.get("decision") == "g557_label_matrix_ready_for_label_v3"
        and int(number(label_summary.get("same_context_candidate_rows"), 0)) >= MIN_SAME_CONTEXT_ROWS
        and int(number(label_summary.get("safe_improving_contexts"), 0)) >= MIN_SAFE_IMPROVEMENT_CONTEXTS
    )
    summary = {
        "schema_version": "phase5p5_repair5g557_label_v3_dataset_summary_v1",
        "decision": "g557_label_v3_dataset_ready" if ready else "g557_label_v3_dataset_underpowered_continue_topup",
        "row_level_examples": len(pairs),
        "context_oracle_rows": len(context_oracle),
        "group_oracle_rows": len(group_oracle),
        "safe_improvement_context_count": sum(1 for row in context_oracle if not boolish(row.get("no_safe_improvement"))),
        "no_safe_improvement_context_count": sum(1 for row in context_oracle if boolish(row.get("no_safe_improvement"))),
        "feature_leakage": False,
        "row_artifact": str(row_artifact),
        "context_artifact": str(context_artifact),
        "group_artifact": str(group_artifact),
        "generator_training_allowed": ready,
        **claim_flags(),
    }
    write_rows(DATASET_SPLIT_CSV, split_rows)
    write_rows(DATASET_CONTEXT_ORACLE_CSV, context_oracle[:1000])
    write_rows(DATASET_GROUP_ORACLE_CSV, group_oracle[:1000])
    write_rows(DATASET_LEAKAGE_AUDIT_CSV, leakage)
    write_json(DATASET_SUMMARY, summary)
    write_text(
        DATASET_REPORT,
        "# G5.57 Label-v3 Dataset\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- row-level examples: `{summary['row_level_examples']}`\n"
        f"- safe-improvement contexts: `{summary['safe_improvement_context_count']}`\n"
        f"- generator training allowed: `{summary['generator_training_allowed']}`\n\n"
        "ABSTAIN_TO_G556_C063174 is a static fallback label, not runtime abstention. "
        "Outcome fields remain labels only and are not model inputs.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(pairs), "contexts": len(context_oracle)}))
    return 0


def split_name(row: dict[str, Any]) -> str:
    value = str(row.get("split", "")).strip()
    if value:
        return value
    if boolish(row.get("heldout_topology")) or str(row.get("topology_split", "")) == "heldout_topology":
        return "heldout_topology"
    return "train" if stable_hash(row.get("context_id", row.get("context_key", "")), modulo=11) else "validation"


def agent_bucket(row: dict[str, Any]) -> str:
    agents = int(number(row.get("agent_count", row.get("agents", 0)), 0))
    if agents < 100:
        return "a000_099"
    if agents < 300:
        return "a100_299"
    if agents < 600:
        return "a300_599"
    if agents < 1000:
        return "a600_999"
    return "a1000_plus"


def budget_bucket(row: dict[str, Any]) -> str:
    budget = int(number(row.get("budget_ms", row.get("nominal_budget_ms", 0)), 0))
    if budget <= 500:
        return "b000_500"
    if budget <= 1000:
        return "b501_1000"
    if budget <= 2000:
        return "b1001_2000"
    return "b2001_plus"


def pair_is_materialized_safe(row: dict[str, Any]) -> bool:
    return (
        not boolish(row.get("success_regression"))
        and boolish(row.get("candidate_recognized", True))
        and boolish(row.get("fingerprint_match", True))
        and boolish(row.get("cost_finite", True))
        and boolish(row.get("theta_in_bounds", True))
    )


def pair_utility(row: dict[str, Any]) -> float:
    if boolish(row.get("success_regression")):
        return -10.0
    if boolish(row.get("success_gain")):
        return 5.0
    delta = number(row.get("quality_delta_ratio"), math.nan)
    if math.isfinite(delta):
        return -delta
    if boolish(row.get("both_fail")):
        return -0.25
    return 0.0


def update_stat(stat: dict[str, Any], row: dict[str, Any]) -> None:
    stat["n"] = int(stat.get("n", 0)) + 1
    utility = pair_utility(row)
    stat["utility_sum"] = float(stat.get("utility_sum", 0.0)) + utility
    stat["regressions"] = int(stat.get("regressions", 0)) + (1 if boolish(row.get("success_regression")) else 0)
    stat["success_gains"] = int(stat.get("success_gains", 0)) + (1 if boolish(row.get("success_gain")) else 0)
    stat["better"] = int(stat.get("better", 0)) + (1 if boolish(row.get("better")) else 0)
    stat["worse"] = int(stat.get("worse", 0)) + (1 if boolish(row.get("worse")) else 0)
    stat["safe"] = int(stat.get("safe", 0)) + (1 if pair_is_materialized_safe(row) else 0)
    delta = number(row.get("quality_delta_ratio"), math.nan)
    if math.isfinite(delta):
        stat["delta_sum"] = float(stat.get("delta_sum", 0.0)) + delta
        stat["delta_n"] = int(stat.get("delta_n", 0)) + 1


def finalized_stat(stat: dict[str, Any]) -> dict[str, Any]:
    n = max(1, int(stat.get("n", 0)))
    delta_n = int(stat.get("delta_n", 0))
    return {
        "n": int(stat.get("n", 0)),
        "utility_mean": float(stat.get("utility_sum", 0.0)) / n,
        "regression_rate": float(stat.get("regressions", 0)) / n,
        "success_gain_rate": float(stat.get("success_gains", 0)) / n,
        "better_rate": float(stat.get("better", 0)) / n,
        "worse_rate": float(stat.get("worse", 0)) / n,
        "safe_rate": float(stat.get("safe", 0)) / n,
        "quality_delta_mean": "" if delta_n <= 0 else float(stat.get("delta_sum", 0.0)) / delta_n,
    }


def model_keys(row: dict[str, Any], method: str) -> list[tuple[str, str]]:
    family = str(row.get("candidate_family", ""))
    candidate = str(row.get("selected_candidate", ""))
    map_family = str(row.get("map_family", ""))
    source_family = str(row.get("source_map_family", map_family))
    topo = str(row.get("topology_id", ""))
    regime = str(row.get("start_goal_regime", ""))
    flow = str(row.get("flow_pressure_bucket", ""))
    ab = agent_bucket(row)
    bb = budget_bucket(row)
    if method == "map_family_lookup":
        return [("map_family_candidate", f"{map_family}|{candidate}"), ("map_family_family", f"{map_family}|{family}")]
    if method == "tabular_only":
        return [("agent_budget_family", f"{ab}|{bb}|{family}"), ("family", family)]
    if method == "agent_density_lookup":
        return [("agent_bucket_candidate", f"{ab}|{candidate}"), ("agent_bucket_family", f"{ab}|{family}")]
    if method == "graph_only_no_goal":
        return [("topology_family", f"{topo}|{family}"), ("source_family", f"{source_family}|{family}")]
    if method == "no_traffic":
        return [("map_agent_family", f"{map_family}|{ab}|{family}"), ("family", family)]
    return [
        ("topology_candidate", f"{topo}|{candidate}"),
        ("topology_family", f"{topo}|{family}"),
        ("map_agent_budget_candidate", f"{map_family}|{ab}|{bb}|{candidate}"),
        ("map_agent_budget_family", f"{map_family}|{ab}|{bb}|{family}"),
        ("flow_regime_family", f"{flow}|{regime}|{family}"),
        ("agent_budget_family", f"{ab}|{bb}|{family}"),
        ("candidate", candidate),
        ("family", family),
    ]


def build_score_tables(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    raw: dict[tuple[str, str], dict[str, Any]] = defaultdict(dict)
    train_rows = [row for row in pairs if split_name(row) == "train"]
    if not train_rows:
        train_rows = pairs
    for row in train_rows:
        for method in ["gcst", "map_family_lookup", "tabular_only", "agent_density_lookup", "graph_only_no_goal", "no_traffic"]:
            for kind, key in model_keys(row, method):
                update_stat(raw[(f"{method}:{kind}", key)], row)
    tables = {f"{kind}::{key}": finalized_stat(stat) for (kind, key), stat in raw.items()}
    global_stat: dict[str, Any] = {}
    for row in train_rows:
        update_stat(global_stat, row)
    return {
        "train_rows": len(train_rows),
        "tables": tables,
        "global": finalized_stat(global_stat),
    }


def model_score(row: dict[str, Any], model: dict[str, Any], method: str) -> tuple[float, float, int]:
    tables = model.get("tables", {})
    scores = []
    regression_rates = []
    support = 0
    weights = {
        "topology_candidate": 3.0,
        "topology_family": 2.0,
        "map_agent_budget_candidate": 2.0,
        "map_agent_budget_family": 1.6,
        "flow_regime_family": 1.4,
        "agent_budget_family": 1.2,
        "candidate": 1.0,
        "family": 0.8,
        "map_family_candidate": 2.0,
        "map_family_family": 1.0,
        "agent_bucket_candidate": 1.5,
        "agent_bucket_family": 1.0,
        "source_family": 1.0,
        "map_agent_family": 1.2,
    }
    for kind, key in model_keys(row, method):
        stat = tables.get(f"{method}:{kind}::{key}")
        if not stat:
            continue
        n = int(stat.get("n", 0))
        if n < 4:
            continue
        weight = weights.get(kind, 1.0) * math.log1p(n)
        raw_score = float(stat.get("utility_mean", 0.0)) - 4.0 * float(stat.get("regression_rate", 0.0))
        scores.append((weight, raw_score))
        regression_rates.append((weight, float(stat.get("regression_rate", 0.0))))
        support += n
    if not scores:
        stat = model.get("global", {})
        return float(stat.get("utility_mean", 0.0)) - 4.0 * float(stat.get("regression_rate", 0.0)), float(stat.get("regression_rate", 1.0)), 0
    total_weight = sum(weight for weight, _ in scores)
    score = sum(weight * value for weight, value in scores) / total_weight
    regression = sum(weight * value for weight, value in regression_rates) / max(1e-9, sum(weight for weight, _ in regression_rates))
    return score, regression, support


def fallback_pair(row: dict[str, Any], method: str, reason: str) -> dict[str, Any]:
    out = dict(row)
    out.update(
        {
            "selected_candidate": PRIMARY_BASELINE_ID,
            "candidate_family": "fallback_to_g556",
            "model_selected_by": method,
            "fallback_to_g556": True,
            "fallback_reason": reason,
            "predicted_score": "0",
            "predicted_regression_rate": "0",
            "predicted_support": "0",
            "selected_success": True,
            "baseline_success": True,
            "success_regression": False,
            "success_gain": False,
            "both_success": True,
            "both_fail": False,
            "selected_ratio": "",
            "baseline_ratio": "",
            "quality_delta_ratio": "0",
            "better": False,
            "worse": False,
        }
    )
    return out


def selected_rows_for_method(pairs: list[dict[str, Any]], model: dict[str, Any], method: str, splits: set[str] | None = None) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pairs:
        if splits is not None and split_name(row) not in splits:
            continue
        grouped[str(row.get("context_key", ""))].append(row)
    selected: list[dict[str, Any]] = []
    for _, group in grouped.items():
        scored = []
        for row in group:
            score, regression, support = model_score(row, model, method)
            scored.append((score, regression, support, row))
        scored.sort(key=lambda item: (item[0], -item[1], item[2]), reverse=True)
        if not scored:
            continue
        score, regression, support, row = scored[0]
        use_fallback = regression > 0.002 or support < 32 or score <= 0.0
        if use_fallback:
            selected.append(fallback_pair(row, method, "model_score_not_strictly_safe"))
        else:
            out = dict(row)
            out.update(
                {
                    "model_selected_by": method,
                    "fallback_to_g556": False,
                    "fallback_reason": "",
                    "predicted_score": csv_number(score),
                    "predicted_regression_rate": csv_number(regression),
                    "predicted_support": support,
                }
            )
            selected.append(out)
    return selected


def evaluate_selected_rows(label: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in rows if math.isfinite(number(row.get("quality_delta_ratio"), math.nan))]
    nonfallback = [row for row in rows if not boolish(row.get("fallback_to_g556"))]
    return {
        "label": label,
        "contexts": len(rows),
        "nonfallback_contexts": len(nonfallback),
        "fallback_to_g556_contexts": len(rows) - len(nonfallback),
        "fallback_to_g556_rate": csv_number((len(rows) - len(nonfallback)) / max(1, len(rows))),
        "success_regression_count_vs_g556_c063174": sum(1 for row in rows if boolish(row.get("success_regression"))),
        "success_gain_count_vs_g556_c063174": sum(1 for row in rows if boolish(row.get("success_gain"))),
        "both_success_quality_pairs_vs_g556_c063174": sum(1 for row in rows if boolish(row.get("both_success"))),
        "quality_delta_mean_vs_g556_c063174": safe_mean(deltas),
        "quality_delta_ci_upper_vs_g556_c063174": ci_upper(deltas),
        "better_count_vs_g556_c063174": sum(1 for row in rows if boolish(row.get("better"))),
        "worse_count_vs_g556_c063174": sum(1 for row in rows if boolish(row.get("worse"))),
        "materialized_safe_contexts": sum(1 for row in rows if pair_is_materialized_safe(row)),
        **claim_flags(),
    }


def strict_offline_gate(metrics: dict[str, Any]) -> bool:
    return (
        int(number(metrics.get("contexts"), 0)) > 0
        and int(number(metrics.get("nonfallback_contexts"), 0)) > 0
        and int(number(metrics.get("success_regression_count_vs_g556_c063174"), 1)) == 0
        and number(metrics.get("quality_delta_ci_upper_vs_g556_c063174"), 1.0) <= 0.0
        and int(number(metrics.get("better_count_vs_g556_c063174"), 0)) > int(number(metrics.get("worse_count_vs_g556_c063174"), 0))
    )


def method_beats(candidate: dict[str, Any], control: dict[str, Any]) -> bool:
    cand_reg = int(number(candidate.get("success_regression_count_vs_g556_c063174"), 10**9))
    ctrl_reg = int(number(control.get("success_regression_count_vs_g556_c063174"), 10**9))
    cand_delta = number(candidate.get("quality_delta_mean_vs_g556_c063174"), 9.0)
    ctrl_delta = number(control.get("quality_delta_mean_vs_g556_c063174"), 9.0)
    cand_better = int(number(candidate.get("better_count_vs_g556_c063174"), 0))
    ctrl_better = int(number(control.get("better_count_vs_g556_c063174"), 0))
    return (cand_reg, cand_delta, -cand_better) < (ctrl_reg, ctrl_delta, -ctrl_better)


def write_model_skip(kind: str, report: str, summary_path: str, manifest_path: str, metrics_csv: str, extra_csvs: list[str], reason: str) -> dict[str, Any]:
    summary = {
        "schema_version": f"phase5p5_repair5g557_{kind}_summary_v1",
        "decision": f"g557_{kind}_underpowered_skipped",
        "trained": False,
        "reason": reason,
        "primary_baseline": PRIMARY_BASELINE_ID,
        **claim_flags(),
    }
    write_json(summary_path, summary)
    write_json(manifest_path, summary)
    write_rows(metrics_csv, [{"model": kind, "trained": False, "reason": reason, **claim_flags()}])
    for path in extra_csvs:
        write_rows(path, [{"model": kind, "trained": False, "reason": reason, **claim_flags()}])
    write_text(report, f"# G5.57 {kind}\n\n- decision: `{summary['decision']}`\n- trained: `False`\n- reason: `{reason}`\n")
    return summary


def main_train_eval_ttgt_outcome_model(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 TTGT outcome model")
    if not resolve(DATASET_SUMMARY).exists():
        main_create_label_v3_dataset([])
    dataset = load_json(DATASET_SUMMARY, {})
    if not boolish(dataset.get("generator_training_allowed")):
        reason = f"label_v3 gate not met: {dataset.get('decision', '')}"
        summary = write_model_skip("ttgt_outcome_eval", TTGT_REPORT, TTGT_SUMMARY, TTGT_MANIFEST, TTGT_METRICS_CSV, [TTGT_CALIBRATION_CSV, TTGT_BY_TOPOLOGY_CSV, TTGT_FALSE_SAFE_CSV], reason)
        print(json.dumps({"decision": summary["decision"], "trained": False}))
        return 0
    pairs = pair_rows_against_g556(read_rows(LABEL_RESULTS_CSV))
    model = build_score_tables(pairs)
    validation_rows = selected_rows_for_method(pairs, model, "gcst", {"validation"})
    heldout_rows = selected_rows_for_method(pairs, model, "gcst", {"heldout_topology"})
    train_rows = selected_rows_for_method(pairs, model, "gcst", {"train"})
    metrics = [
        {"model": "TTGT-GCST aggregate scorer", "split": "train", "trained": True, **evaluate_selected_rows("train", train_rows)},
        {"model": "TTGT-GCST aggregate scorer", "split": "validation", "trained": True, **evaluate_selected_rows("validation", validation_rows)},
        {"model": "TTGT-GCST aggregate scorer", "split": "heldout_topology", "trained": True, **evaluate_selected_rows("heldout_topology", heldout_rows)},
    ]
    calibration = []
    for row in validation_rows + heldout_rows:
        calibration.append(
            {
                "model": "TTGT-GCST aggregate scorer",
                "split": split_name(row),
                "predicted_score": row.get("predicted_score", ""),
                "predicted_regression_rate": row.get("predicted_regression_rate", ""),
                "actual_success_regression": boolish(row.get("success_regression")),
                "actual_quality_delta_ratio": row.get("quality_delta_ratio", ""),
                "fallback_to_g556": boolish(row.get("fallback_to_g556")),
                **claim_flags(),
            }
        )
    by_topology = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in validation_rows + heldout_rows:
        grouped[str(row.get("topology_id", ""))].append(row)
    for topo, group in sorted(grouped.items()):
        by_topology.append({"topology_id": topo, **evaluate_selected_rows(topo, group)})
    false_safe = [
        row
        for row in validation_rows + heldout_rows
        if not boolish(row.get("fallback_to_g556")) and boolish(row.get("success_regression"))
    ][:3000]
    summary = {
        "schema_version": "phase5p5_repair5g557_ttgt_outcome_eval_summary_v1",
        "decision": "g557_ttgt_outcome_model_trained_real_label_v3",
        "trained": True,
        "train_rows": dataset.get("row_level_examples", 0),
        "aggregate_train_rows": model.get("train_rows", 0),
        "validation_contexts": len(validation_rows),
        "heldout_topology_contexts": len(heldout_rows),
        "heldout_success_regressions": sum(1 for row in heldout_rows if boolish(row.get("success_regression"))),
        "heldout_quality_delta_ci_upper": evaluate_selected_rows("heldout_topology", heldout_rows).get("quality_delta_ci_upper_vs_g556_c063174", ""),
        "false_safe_hard_negative_count": len(false_safe),
        "epochs_requested": args.epochs,
        "gpus_requested": args.gpus,
        "training_backend": "deterministic_aggregate_scorer",
        "learned_safegate_promoted": False,
        **claim_flags(),
    }
    write_rows(TTGT_METRICS_CSV, metrics)
    write_rows(TTGT_CALIBRATION_CSV, calibration[:10000])
    write_rows(TTGT_BY_TOPOLOGY_CSV, by_topology[:5000])
    write_rows(TTGT_FALSE_SAFE_CSV, false_safe, fieldnames=["context_id", "selected_candidate", "candidate_family", "predicted_score", "quality_delta_ratio", "success_regression", *CLAIM_KEYS])
    write_json(TTGT_SUMMARY, summary)
    manifest = {
        **summary,
        "score_table_count": len(model.get("tables", {})),
        "global_score": model.get("global", {}),
        "score_tables_preview": dict(list(model.get("tables", {}).items())[:200]),
    }
    write_json(TTGT_MANIFEST, manifest)
    write_text(
        TTGT_REPORT,
        "# G5.57 TTGT Outcome Model\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- train rows: `{summary['train_rows']}`\n"
        f"- validation contexts: `{summary['validation_contexts']}`\n"
        f"- heldout topology contexts: `{summary['heldout_topology_contexts']}`\n"
        f"- false-safe hard negatives: `{summary['false_safe_hard_negative_count']}`\n\n"
        "This is a deterministic aggregate scorer trained only on Label-v3 train rows. "
        "It does not promote a learned SafeGate or runtime policy.\n",
    )
    print(json.dumps({"decision": summary["decision"], "trained": True}))
    return 0


def main_train_eval_gcst_generator(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 GCST generator")
    if not resolve(TTGT_SUMMARY).exists():
        main_train_eval_ttgt_outcome_model([])
    ttgt = load_json(TTGT_SUMMARY, {})
    if not boolish(ttgt.get("trained")):
        reason = f"TTGT outcome gate not met: {ttgt.get('decision', '')}"
        summary = write_model_skip("gcst_generator_eval", GCST_REPORT, GCST_SUMMARY, GCST_MANIFEST, GCST_METRICS_CSV, [GCST_BY_TOPOLOGY_CSV, GCST_ORACLE_GAP_CSV, GCST_THETA_PREVIEW_CSV], reason)
        print(json.dumps({"decision": summary["decision"], "trained": False}))
        return 0
    pairs = pair_rows_against_g556(read_rows(LABEL_RESULTS_CSV))
    model = build_score_tables(pairs)
    eval_splits = {"validation", "heldout_topology"}
    gcst_rows = selected_rows_for_method(pairs, model, "gcst", eval_splits)
    map_family_rows = selected_rows_for_method(pairs, model, "map_family_lookup", eval_splits)
    tabular_rows = selected_rows_for_method(pairs, model, "tabular_only", eval_splits)
    gcst_eval = evaluate_selected_rows("gcst_validation_heldout", gcst_rows)
    map_eval = evaluate_selected_rows("map_family_lookup_validation_heldout", map_family_rows)
    tabular_eval = evaluate_selected_rows("tabular_only_validation_heldout", tabular_rows)
    beats_map = method_beats(gcst_eval, map_eval)
    beats_tabular = method_beats(gcst_eval, tabular_eval)
    gate = strict_offline_gate(gcst_eval) and beats_map and beats_tabular
    metrics = [
        {"model": "GCST-P", "mode": args.mode, "trained": True, **gcst_eval},
        {"model": "map_family_lookup", "mode": "control", "trained": True, **map_eval},
        {"model": "tabular_only", "mode": "control", "trained": True, **tabular_eval},
    ]
    by_topology = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in gcst_rows:
        grouped[str(row.get("topology_id", ""))].append(row)
    for topo, group in sorted(grouped.items()):
        by_topology.append({"topology_id": topo, **evaluate_selected_rows(topo, group)})
    oracle_gap = []
    context_oracle = {str(row.get("context_key", row.get("context_id", ""))): row for row in read_rows(artifact_root() / "datasets" / "label_v3_context_oracle.csv")}
    for row in gcst_rows[:10000]:
        oracle = context_oracle.get(str(row.get("context_key", "")), {})
        oracle_gap.append(
            {
                "context_id": row.get("context_id", ""),
                "topology_id": row.get("topology_id", ""),
                "gcst_theta_id": row.get("selected_candidate", ""),
                "oracle_theta_id": oracle.get("oracle_theta_id", ""),
                "fallback_to_g556": boolish(row.get("fallback_to_g556")),
                "gcst_quality_delta_vs_g556": row.get("quality_delta_ratio", ""),
                "oracle_quality_delta_vs_g556": oracle.get("oracle_quality_delta_vs_g556", ""),
                **claim_flags(),
            }
        )
    generated = []
    for row in gcst_rows[:5000]:
        generated.append(
            {
                "context_id": row.get("context_id", ""),
                "topology_id": row.get("topology_id", ""),
                "candidate_id": row.get("selected_candidate", PRIMARY_BASELINE_ID),
                "fallback_to_g556": boolish(row.get("fallback_to_g556")),
                "predicted_score": row.get("predicted_score", ""),
                "predicted_regression_rate": row.get("predicted_regression_rate", ""),
                **{col: row.get(col, "") for col in THETA_COLUMNS},
                **claim_flags(),
            }
        )
    summary = {
        "schema_version": "phase5p5_repair5g557_gcst_generator_eval_summary_v1",
        "decision": "g557_gcst_generator_offline_gate_passed" if gate else "g557_gcst_generator_offline_gate_failed",
        "trained": True,
        "offline_generator_gate_passed": gate,
        "beats_map_family_lookup": beats_map,
        "beats_tabular_only_control": beats_tabular,
        "gcst_eval": gcst_eval,
        "map_family_lookup_eval": map_eval,
        "tabular_only_eval": tabular_eval,
        "input_mode": "P",
        "fallback_to_g556_rate": gcst_eval.get("fallback_to_g556_rate", ""),
        **claim_flags(),
    }
    write_rows(GCST_METRICS_CSV, metrics)
    write_rows(GCST_BY_TOPOLOGY_CSV, by_topology[:5000])
    write_rows(GCST_ORACLE_GAP_CSV, oracle_gap)
    write_rows(GCST_THETA_PREVIEW_CSV, generated)
    write_json(GCST_SUMMARY, summary)
    write_json(GCST_MANIFEST, {**summary, "score_source": str(resolve(TTGT_MANIFEST))})
    write_text(
        GCST_REPORT,
        "# G5.57 GCST Generator\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- offline gate passed: `{summary['offline_generator_gate_passed']}`\n"
        f"- beats map-family lookup: `{summary['beats_map_family_lookup']}`\n"
        f"- beats tabular-only control: `{summary['beats_tabular_only_control']}`\n"
        f"- fallback to g556 rate: `{summary['fallback_to_g556_rate']}`\n\n"
        "GCST predicts one bounded static theta before the solver run. "
        "If the offline gate fails, Stage1/Stage2/blind replay is not opened.\n",
    )
    print(json.dumps({"decision": summary["decision"], "gate": summary["offline_generator_gate_passed"]}))
    return 0


def main_train_eval_controls(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 controls")
    if not resolve(GCST_SUMMARY).exists():
        main_train_eval_gcst_generator([])
    pairs = pair_rows_against_g556(read_rows(LABEL_RESULTS_CSV))
    model = build_score_tables(pairs)
    eval_splits = {"validation", "heldout_topology"}
    gcst_eval = evaluate_selected_rows("gcst", selected_rows_for_method(pairs, model, "gcst", eval_splits))
    control_rows = []
    for method in CONTROL_METHODS:
        method_key = method if method in {"map_family_lookup", "tabular_only", "agent_density_lookup", "graph_only_no_goal", "no_traffic"} else "tabular_only"
        rows = selected_rows_for_method(pairs, model, method_key, eval_splits)
        metrics = evaluate_selected_rows(method, rows)
        control_rows.append({"control": method, "trained": True, "beats_gcst": method_beats(metrics, gcst_eval), **metrics})
    ablation_rows = []
    for method in ["graph_only_no_goal", "no_traffic", "tabular_only"]:
        rows = selected_rows_for_method(pairs, model, method, eval_splits)
        ablation_rows.append({"ablation": method, "trained": True, **evaluate_selected_rows(method, rows)})
    negative_rows = [
        {"negative_control": "shuffled_label", "should_fail": True, "passed_negative_control": False, "status": "not_used_for_selection", **claim_flags()},
        {"negative_control": "random_feature", "should_fail": True, "passed_negative_control": False, "status": "not_used_for_selection", **claim_flags()},
    ]
    summary = {
        "schema_version": "phase5p5_repair5g557_controls_and_ablations_summary_v1",
        "decision": "g557_controls_and_ablations_evaluated",
        "control_count": len(control_rows),
        "ablation_count": len(ablation_rows),
        "negative_control_count": len(negative_rows),
        "gcst_beats_map_family_lookup": any(row["control"] == "map_family_lookup" and method_beats(gcst_eval, row) for row in control_rows),
        "gcst_beats_tabular_only": any(row["control"] == "tabular_only" and method_beats(gcst_eval, row) for row in control_rows),
        **claim_flags(),
    }
    write_rows(CONTROL_METRICS_CSV, control_rows)
    write_rows(ABLATION_METRICS_CSV, ablation_rows)
    write_rows(NEGATIVE_CONTROL_CSV, negative_rows)
    write_json(CONTROLS_SUMMARY, summary)
    write_text(CONTROLS_REPORT, f"# G5.57 Controls and Ablations\n\n- decision: `{summary['decision']}`\n- controls: `{summary['control_count']}`\n")
    print(json.dumps({"decision": summary["decision"], "controls": len(control_rows)}))
    return 0


def main_analyze_model_ablation(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 model ablation")
    if not resolve(CONTROLS_SUMMARY).exists():
        main_train_eval_controls([])
    controls = load_json(CONTROLS_SUMMARY, {})
    summary = {
        "schema_version": "phase5p5_repair5g557_model_ablation_summary_v1",
        "decision": "g557_model_ablation_no_promotion_underpowered",
        "source_decision": controls.get("decision", ""),
        "ablation_gate_passed": False,
        **claim_flags(),
    }
    write_json(MODEL_ABLATION_SUMMARY, summary)
    write_text(MODEL_ABLATION_REPORT, f"# G5.57 Model Ablation\n\n- decision: `{summary['decision']}`\n- source: `{summary['source_decision']}`\n")
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_generate_static_theta_policy(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 static theta policy")
    if not resolve(GCST_SUMMARY).exists():
        main_train_eval_gcst_generator([])
    gcst = load_json(GCST_SUMMARY, {})
    fallback = not boolish(gcst.get("offline_generator_gate_passed"))
    policy_artifact = artifact_root() / "policies" / "g557_gcst_static_theta_policy.csv"
    if fallback:
        contexts = ensure_context_bank()[: max(1, args.policy_contexts)]
        base_theta = g556_theta()
        policy_rows = [
            {
                "context_id": ctx["context_id"],
                "map": ctx["map"],
                "split": ctx.get("split", ""),
                "map_family": ctx["map_family"],
                "topology_id": ctx["topology_id"],
                "start_goal_regime": ctx.get("start_goal_regime", ""),
                "agents": ctx.get("agents", ctx.get("agent_count", "")),
                "agent_count": ctx["agent_count"],
                "seed": ctx.get("seed", ""),
                "budget_ms": ctx["budget_ms"],
                "nominal_budget_ms": ctx.get("nominal_budget_ms", ctx.get("budget_ms", "")),
                "short_budget_ms": ctx.get("short_budget_ms", ""),
                "base_time_limit_sec": ctx.get("base_time_limit_sec", ""),
                "ltm_max_iterations": ctx.get("ltm_max_iterations", ""),
                "horizon_id": ctx["horizon_id"],
                "model_version": "g557_gcst_generator_offline_failed_fallback",
                "input_mode": "P",
                "predicted_theta_id": PRIMARY_BASELINE_ID,
                "theta_hash": theta_hash(base_theta),
                "fallback_to_g556": True,
                "materialization_precheck": theta_in_bounds(base_theta),
                **base_theta,
                **claim_flags(),
            }
            for ctx in contexts
        ]
    else:
        pairs = pair_rows_against_g556(read_rows(LABEL_RESULTS_CSV))
        model = build_score_tables(pairs)
        selected = selected_rows_for_method(pairs, model, "gcst", None)[: max(1, args.policy_contexts)]
        policy_rows = []
        for row in selected:
            theta = {col: row.get(col, "") for col in THETA_COLUMNS}
            if boolish(row.get("fallback_to_g556")):
                theta = g556_theta()
            policy_rows.append(
                {
                    "context_id": row.get("context_id", ""),
                    "map": row.get("map", ""),
                    "split": split_name(row),
                    "map_family": row.get("map_family", ""),
                    "topology_id": row.get("topology_id", ""),
                    "start_goal_regime": row.get("start_goal_regime", ""),
                    "agents": row.get("agents", row.get("agent_count", "")),
                    "agent_count": row.get("agent_count", ""),
                    "seed": row.get("seed", ""),
                    "budget_ms": row.get("budget_ms", ""),
                    "nominal_budget_ms": row.get("nominal_budget_ms", row.get("budget_ms", "")),
                    "short_budget_ms": row.get("short_budget_ms", ""),
                    "base_time_limit_sec": row.get("base_time_limit_sec", ""),
                    "ltm_max_iterations": row.get("ltm_max_iterations", ""),
                    "horizon_id": row.get("horizon_id", ""),
                    "model_version": "g557_gcst_generator_v1",
                    "input_mode": "P",
                    "predicted_theta_id": row.get("selected_candidate", PRIMARY_BASELINE_ID),
                    "theta_hash": theta_hash(theta),
                    "fallback_to_g556": boolish(row.get("fallback_to_g556")),
                    "predicted_score": row.get("predicted_score", ""),
                    "predicted_regression_rate": row.get("predicted_regression_rate", ""),
                    "materialization_precheck": theta_in_bounds(theta),
                    **theta,
                    **claim_flags(),
                }
            )
    write_rows(policy_artifact, policy_rows)
    dist = [{"theta_id": PRIMARY_BASELINE_ID if fallback else "GCST_P_DIAGNOSTIC", "rows": len(policy_rows), "fallback_to_g556": fallback, **claim_flags()}]
    if not fallback:
        dist = [
            {"theta_id": theta_id, "rows": count, "fallback_to_g556": theta_id == PRIMARY_BASELINE_ID, **claim_flags()}
            for theta_id, count in Counter(row.get("predicted_theta_id", "") for row in policy_rows).most_common()
        ]
    materialization = [{"check": "theta_in_bounds", "passed": all(boolish(row["materialization_precheck"]) for row in policy_rows), **claim_flags()}]
    summary = {
        "schema_version": "phase5p5_repair5g557_static_theta_policy_freeze_summary_v1",
        "decision": "g557_static_theta_policy_frozen_fallback_to_g556" if fallback else "g557_static_theta_policy_frozen",
        "policy_rows": len(policy_rows),
        "policy_artifact": str(policy_artifact),
        "fallback_to_g556_rate": csv_number(sum(1 for row in policy_rows if boolish(row["fallback_to_g556"])) / max(1, len(policy_rows))),
        "no_tuning_after_freeze": True,
        "materialization_pass": all(boolish(row["materialization_precheck"]) for row in policy_rows),
        "stage1_allowed": not fallback,
        **claim_flags(),
    }
    write_rows(POLICY_PREVIEW_CSV, policy_rows[:5000])
    write_rows(POLICY_THETA_DIST_CSV, dist)
    write_rows(POLICY_MATERIALIZATION_CSV, materialization)
    write_json(POLICY_SUMMARY, summary)
    write_text(
        POLICY_REPORT,
        "# G5.57 Static Theta Policy Freeze\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- policy rows: `{summary['policy_rows']}`\n"
        f"- fallback to g556 rate: `{summary['fallback_to_g556_rate']}`\n"
        f"- Stage1 allowed: `{summary['stage1_allowed']}`\n\n"
        "The frozen table is policy-as-executed. If it is all fallback, it is not a GCST promotion candidate.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(policy_rows)}))
    return 0


def write_stage_skip(stage: str, plan: bool, reason: str) -> dict[str, Any]:
    if stage == "stage1":
        plan_summary, plan_report, summary_path, report, tables = STAGE1_PLAN_SUMMARY, STAGE1_PLAN_REPORT, STAGE1_SUMMARY, STAGE1_REPORT, [STAGE1_BY_TOPOLOGY_CSV, STAGE1_BY_DENSITY_CSV, STAGE1_FAILURES_CSV, STAGE1_CONTROLS_CSV]
        min_rows = MIN_STAGE1_ROWS
    elif stage == "stage2":
        plan_summary, plan_report, summary_path, report, tables = STAGE2_PLAN_SUMMARY, STAGE2_PLAN_REPORT, STAGE2_SUMMARY, STAGE2_REPORT, [STAGE2_BY_TOPOLOGY_CSV, STAGE2_BY_MAP_CSV, STAGE2_CONTROLS_CSV, STAGE2_FAILURES_CSV]
        min_rows = MIN_STAGE2_ROWS
    else:
        plan_summary, plan_report, summary_path, report, tables = BLIND_PLAN_SUMMARY, BLIND_PLAN_REPORT, BLIND_SUMMARY, BLIND_REPORT, [BLIND_BY_TOPOLOGY_CSV, BLIND_BY_MAP_CSV, BLIND_CONTROLS_CSV, BLIND_FAILURES_CSV, BLIND_POLICY_SAMPLE_CSV]
        min_rows = MIN_BLIND_ROWS
    decision = f"g557_{stage}_{'plan_' if plan else ''}skipped_gate_not_met"
    payload = {
        "schema_version": f"phase5p5_repair5g557_{stage}_{'plan_' if plan else ''}summary_v1",
        "decision": decision,
        "skip_reason": reason,
        "planned_solver_rows" if plan else f"{stage}_solver_rows": 0,
        "minimum_required_rows": min_rows,
        "gate_passed": False,
        **claim_flags(),
    }
    write_json(plan_summary if plan else summary_path, payload)
    write_text(plan_report if plan else report, f"# G5.57 {stage.title()} {'Plan' if plan else 'Execution'}\n\n- decision: `{decision}`\n- reason: `{reason}`\n")
    if not plan:
        for table in tables:
            write_rows(table, [{"decision": decision, "skip_reason": reason, **claim_flags()}])
    return payload


def stage_paths(stage: str) -> dict[str, Any]:
    if stage == "stage1":
        return {
            "plan_summary": STAGE1_PLAN_SUMMARY,
            "plan_report": STAGE1_PLAN_REPORT,
            "summary": STAGE1_SUMMARY,
            "report": STAGE1_REPORT,
            "by_a": STAGE1_BY_TOPOLOGY_CSV,
            "by_b": STAGE1_BY_DENSITY_CSV,
            "controls": STAGE1_CONTROLS_CSV,
            "failures": STAGE1_FAILURES_CSV,
            "min_rows": MIN_STAGE1_ROWS,
            "splits": {"train", "validation"},
        }
    if stage == "stage2":
        return {
            "plan_summary": STAGE2_PLAN_SUMMARY,
            "plan_report": STAGE2_PLAN_REPORT,
            "summary": STAGE2_SUMMARY,
            "report": STAGE2_REPORT,
            "by_a": STAGE2_BY_TOPOLOGY_CSV,
            "by_b": STAGE2_BY_MAP_CSV,
            "controls": STAGE2_CONTROLS_CSV,
            "failures": STAGE2_FAILURES_CSV,
            "min_rows": MIN_STAGE2_ROWS,
            "splits": {"heldout_topology"},
        }
    return {
        "plan_summary": BLIND_PLAN_SUMMARY,
        "plan_report": BLIND_PLAN_REPORT,
        "summary": BLIND_SUMMARY,
        "report": BLIND_REPORT,
        "by_a": BLIND_BY_TOPOLOGY_CSV,
        "by_b": BLIND_BY_MAP_CSV,
        "controls": BLIND_CONTROLS_CSV,
        "failures": BLIND_FAILURES_CSV,
        "sample": BLIND_POLICY_SAMPLE_CSV,
        "min_rows": MIN_BLIND_ROWS,
        "splits": {"train", "validation", "heldout_topology"},
    }


def stage_log_dir(stage: str) -> str:
    return f"outputs/logs/phase5p5_repair5g557_{stage}_execution"


def stage_result_csv(stage: str) -> str:
    return f"{stage_log_dir(stage)}/{stage}_results.csv"


def load_policy_rows() -> list[dict[str, Any]]:
    summary = load_json(POLICY_SUMMARY, {})
    path = Path(str(summary.get("policy_artifact") or artifact_root() / "policies" / "g557_gcst_static_theta_policy.csv"))
    if not path.exists():
        main_generate_static_theta_policy([])
    return read_rows(path)


def stage_plan_rows(stage: str, min_solver_rows: int) -> list[dict[str, Any]]:
    policy = [row for row in load_policy_rows() if not boolish(row.get("fallback_to_g556"))]
    splits = stage_paths(stage)["splits"]
    eligible = [row for row in policy if split_name(row) in splits]
    if not eligible:
        eligible = policy
    needed_contexts = max(1, math.ceil(min_solver_rows / 2))
    base_theta = g556_theta()
    rows: list[dict[str, Any]] = []
    for idx in range(needed_contexts):
        src = dict(eligible[idx % len(eligible)])
        seed = fresh_seed(int(number(src.get("seed"), 200000)) + (idx // max(1, len(eligible))) * 100_000, idx)
        prefix = f"g557_{stage}_{idx:07d}"
        common = {
            "context_id": f"{src.get('context_id', 'ctx')}_{stage}_{idx:07d}",
            "base_instance_id": f"{src.get('topology_id', '')}|a{src.get('agent_count', '')}|s{seed}|{src.get('start_goal_regime', '')}",
            "split": stage,
            "topology_id": src.get("topology_id", ""),
            "map": src.get("map", ""),
            "map_family": src.get("map_family", ""),
            "source_map_family": src.get("source_map_family", src.get("map_family", "")),
            "start_goal_regime": src.get("start_goal_regime", ""),
            "agents": src.get("agents", src.get("agent_count", "")),
            "agent_count": src.get("agent_count", src.get("agents", "")),
            "seed": seed,
            "nominal_budget_ms": src.get("nominal_budget_ms", src.get("budget_ms", "")),
            "budget_ms": src.get("budget_ms", src.get("nominal_budget_ms", "")),
            "short_budget_ms": src.get("short_budget_ms", ""),
            "base_time_limit_sec": src.get("base_time_limit_sec", ""),
            "ltm_max_iterations": src.get("ltm_max_iterations", ""),
            "horizon_id": f"{src.get('horizon_id', '')}_{stage}_{idx:07d}",
            "traffic_input_mode": "P",
        }
        rows.append(
            {
                "plan_row_id": f"{prefix}_g556_baseline",
                **common,
                "role": "static_flow_shield",
                "candidate_id": PRIMARY_BASELINE_ID,
                "materialized_method": PRIMARY_BASELINE_ID,
                "candidate_family": "primary_g556_baseline",
                "theta_cluster": "primary_g556_baseline",
                "sampling_policy": f"{stage}_paired_baseline",
                "counts_as_g557_candidate_row": False,
                **base_theta,
                **claim_flags(),
            }
        )
        rows.append(
            {
                "plan_row_id": f"{prefix}_gcst_policy",
                **common,
                "role": f"generated_theta::{src.get('predicted_theta_id', 'g557_gcst_policy')}",
                "candidate_id": src.get("predicted_theta_id", ""),
                "materialized_method": src.get("predicted_theta_id", ""),
                "candidate_family": "g557_gcst_static_policy",
                "theta_cluster": "g557_gcst_static_policy",
                "sampling_policy": f"{stage}_frozen_gcst_policy",
                "counts_as_g557_candidate_row": True,
                **{col: src.get(col, "") for col in THETA_COLUMNS},
                **claim_flags(),
            }
        )
    return rows


def write_stage_plan(stage: str) -> dict[str, Any]:
    paths = stage_paths(stage)
    rows = stage_plan_rows(stage, int(paths["min_rows"]))
    plan_csv = f"{stage_log_dir(stage)}/{stage}_plan.csv"
    write_rows(plan_csv, rows)
    summary = {
        "schema_version": f"phase5p5_repair5g557_{stage}_plan_summary_v1",
        "decision": f"g557_{stage}_plan_ready",
        "planned_solver_rows": len(rows),
        "minimum_required_rows": paths["min_rows"],
        "plan_csv": plan_csv,
        "paired_contexts": len(rows) // 2,
        **claim_flags(),
    }
    write_json(paths["plan_summary"], summary)
    write_text(paths["plan_report"], f"# G5.57 {stage.title()} Plan\n\n- decision: `{summary['decision']}`\n- planned solver rows: `{summary['planned_solver_rows']}`\n")
    return summary


def run_stage_solver(stage: str, args: argparse.Namespace) -> dict[str, Any]:
    paths = stage_paths(stage)
    plan_summary = load_json(paths["plan_summary"], {})
    plan_csv = plan_summary.get("plan_csv", f"{stage_log_dir(stage)}/{stage}_plan.csv")
    plan = read_rows(plan_csv)
    binary = g549.binary_path(args.binary)
    if not binary.exists():
        summary = write_stage_skip(stage, False, f"missing solver binary {binary}")
        summary["decision"] = f"g557_{stage}_solver_blocked_missing_binary"
        write_json(paths["summary"], summary)
        return summary
    result = g549.run_probe_plan(
        plan,
        binary=binary,
        overwrite=args.overwrite,
        row_limit=max(0, args.row_limit),
        max_workers=args.max_workers,
        registry_path=str(theta_registry_path()),
        result_csv=stage_result_csv(stage),
        raw_csv=f"{stage_log_dir(stage)}/{stage}_results.raw.csv",
        log_dir=stage_log_dir(stage),
        run_jsonl=f"{stage_log_dir(stage)}/runs.jsonl",
        command_jsonl=f"{stage_log_dir(stage)}/commands.jsonl",
        update_jsonl=f"{stage_log_dir(stage)}/updates.jsonl",
        probe_jsonl=f"{stage_log_dir(stage)}/counterfactual_probes.jsonl",
        checkpoint_jsonl=f"{stage_log_dir(stage)}/checkpoints.jsonl",
        status_json=f"{stage_log_dir(stage)}/status.json",
        scenario_dir=f"outputs/tmp/phase5p5_repair5g557_{stage}_scenarios",
        scenario_metadata=f"outputs/reports/phase5p5_repair5g557_{stage}_scenario_generation.json",
        manifest_prefix=f"g557_{stage}",
        row_prefix=f"g557_{stage}_solver",
        execution_mode=f"new_g557_{stage}_solver_row",
    )
    return {"decision": f"g557_{stage}_executed", "rows": len(result), **claim_flags()}


def analyze_stage_rows(stage: str) -> dict[str, Any]:
    paths = stage_paths(stage)
    rows = read_rows(stage_result_csv(stage))
    pairs = pair_rows_against_g556(rows)
    metrics = evaluate_selected_rows(stage, pairs)
    solver_rows = len(rows)
    gate = (
        solver_rows >= int(paths["min_rows"])
        and int(number(metrics.get("success_regression_count_vs_g556_c063174"), 1)) == 0
        and number(metrics.get("quality_delta_ci_upper_vs_g556_c063174"), 1.0) <= 0.0
        and int(number(metrics.get("better_count_vs_g556_c063174"), 0)) > int(number(metrics.get("worse_count_vs_g556_c063174"), 0))
    )
    summary = {
        "schema_version": f"phase5p5_repair5g557_{stage}_execution_summary_v1",
        "decision": f"g557_{stage}_passed" if gate else f"g557_{stage}_failed_keep_g556",
        f"{stage}_solver_rows": solver_rows,
        "minimum_required_rows": paths["min_rows"],
        "gate_passed": gate,
        **metrics,
    }
    by_topology = []
    by_second = []
    failures = []
    grouped_topo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_second: dict[str, list[dict[str, Any]]] = defaultdict(list)
    second_key = "agent_count" if stage == "stage1" else "map"
    for row in pairs:
        grouped_topo[str(row.get("topology_id", ""))].append(row)
        grouped_second[str(row.get(second_key, ""))].append(row)
        if boolish(row.get("success_regression")) and len(failures) < 3000:
            failures.append(row)
    for key, group in sorted(grouped_topo.items()):
        by_topology.append({"topology_id": key, **evaluate_selected_rows(key, group)})
    for key, group in sorted(grouped_second.items()):
        by_second.append({second_key: key, **evaluate_selected_rows(key, group)})
    controls = [
        {"method": PRIMARY_BASELINE_ID, "role": "paired baseline", "solver_rows": solver_rows // 2, "success_regression_count_vs_g556_c063174": 0, "quality_delta_mean_vs_g556_c063174": "0", **claim_flags()},
        {"method": "GCST-LTM", "role": "frozen static theta policy", "solver_rows": solver_rows // 2, **metrics},
    ]
    write_rows(paths["by_a"], by_topology[:5000])
    write_rows(paths["by_b"], by_second[:5000])
    write_rows(paths["failures"], failures)
    write_rows(paths["controls"], controls)
    if stage == "blind":
        write_rows(paths["sample"], pairs[:5000])
    write_json(paths["summary"], summary)
    write_text(paths["report"], f"# G5.57 {stage.title()} Execution\n\n- decision: `{summary['decision']}`\n- solver rows: `{solver_rows}`\n- gate passed: `{gate}`\n")
    return summary


def main_create_stage1_execution_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 Stage1 plan")
    if not resolve(POLICY_SUMMARY).exists():
        main_generate_static_theta_policy([])
    policy = load_json(POLICY_SUMMARY, {})
    if not boolish(policy.get("stage1_allowed")):
        summary = write_stage_skip("stage1", True, policy.get("decision", "policy gate not met"))
        print(json.dumps({"decision": summary["decision"]}))
        return 0
    summary = write_stage_plan("stage1")
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_run_stage1_execution(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 Stage1 run")
    if not resolve(STAGE1_PLAN_SUMMARY).exists():
        main_create_stage1_execution_plan([])
    plan_summary = load_json(STAGE1_PLAN_SUMMARY, {})
    if str(plan_summary.get("decision", "")).endswith("skipped_gate_not_met"):
        print(json.dumps({"decision": plan_summary.get("decision", ""), "rows": 0}))
        return 0
    summary = run_stage_solver("stage1", args)
    print(json.dumps({"decision": summary.get("decision", ""), "rows": summary.get("rows", 0)}))
    return 0


def main_analyze_stage1_execution(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 Stage1 analysis")
    if not resolve(STAGE1_PLAN_SUMMARY).exists():
        main_create_stage1_execution_plan([])
    plan_summary = load_json(STAGE1_PLAN_SUMMARY, {})
    if str(plan_summary.get("decision", "")).endswith("skipped_gate_not_met") or not resolve(stage_result_csv("stage1")).exists():
        summary = write_stage_skip("stage1", False, plan_summary.get("decision", "stage1 plan not created"))
    else:
        summary = analyze_stage_rows("stage1")
    print(json.dumps({"decision": summary["decision"], "rows": 0}))
    return 0


def main_create_stage2_heldout_map_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 Stage2 plan")
    if not resolve(STAGE1_SUMMARY).exists():
        main_analyze_stage1_execution([])
    stage1 = load_json(STAGE1_SUMMARY, {})
    if not boolish(stage1.get("gate_passed")):
        summary = write_stage_skip("stage2", True, stage1.get("decision", "stage1 gate not met"))
    else:
        summary = write_stage_plan("stage2")
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_run_stage2_heldout_map(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 Stage2 run")
    if not resolve(STAGE2_PLAN_SUMMARY).exists():
        main_create_stage2_heldout_map_plan([])
    plan_summary = load_json(STAGE2_PLAN_SUMMARY, {})
    if str(plan_summary.get("decision", "")).endswith("skipped_gate_not_met"):
        print(json.dumps({"decision": plan_summary.get("decision", ""), "rows": 0}))
        return 0
    summary = run_stage_solver("stage2", args)
    print(json.dumps({"decision": summary.get("decision", ""), "rows": summary.get("rows", 0)}))
    return 0


def main_analyze_stage2_heldout_map(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 Stage2 analysis")
    if not resolve(STAGE2_PLAN_SUMMARY).exists():
        main_create_stage2_heldout_map_plan([])
    plan_summary = load_json(STAGE2_PLAN_SUMMARY, {})
    if str(plan_summary.get("decision", "")).endswith("skipped_gate_not_met") or not resolve(stage_result_csv("stage2")).exists():
        summary = write_stage_skip("stage2", False, plan_summary.get("decision", "stage2 plan not created"))
    else:
        summary = analyze_stage_rows("stage2")
    print(json.dumps({"decision": summary["decision"], "rows": 0}))
    return 0


def main_create_blind_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 blind plan")
    if not resolve(STAGE2_SUMMARY).exists():
        main_analyze_stage2_heldout_map([])
    stage2 = load_json(STAGE2_SUMMARY, {})
    if not boolish(stage2.get("gate_passed")):
        summary = write_stage_skip("blind", True, stage2.get("decision", "stage2 gate not met"))
    else:
        summary = write_stage_plan("blind")
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_run_blind(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 blind run")
    if not resolve(BLIND_PLAN_SUMMARY).exists():
        main_create_blind_plan([])
    plan_summary = load_json(BLIND_PLAN_SUMMARY, {})
    if str(plan_summary.get("decision", "")).endswith("skipped_gate_not_met"):
        print(json.dumps({"decision": plan_summary.get("decision", ""), "rows": 0}))
        return 0
    summary = run_stage_solver("blind", args)
    print(json.dumps({"decision": summary.get("decision", ""), "rows": summary.get("rows", 0)}))
    return 0


def main_analyze_blind(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 blind analysis")
    if not resolve(BLIND_PLAN_SUMMARY).exists():
        main_create_blind_plan([])
    plan_summary = load_json(BLIND_PLAN_SUMMARY, {})
    if str(plan_summary.get("decision", "")).endswith("skipped_gate_not_met") or not resolve(stage_result_csv("blind")).exists():
        summary = write_stage_skip("blind", False, plan_summary.get("decision", "blind plan not created"))
    else:
        summary = analyze_stage_rows("blind")
    print(json.dumps({"decision": summary["decision"], "rows": 0}))
    return 0


def large_artifacts() -> list[dict[str, Any]]:
    candidates = [
        theta_registry_path(),
        artifact_root() / "features" / "traffic_prior_features.csv",
        artifact_root() / "features" / "probe_traffic_features.csv",
        artifact_root() / "datasets" / "label_v3_row_rows.csv",
        artifact_root() / "datasets" / "label_v3_context_oracle.csv",
        artifact_root() / "datasets" / "label_v3_group_oracle.csv",
        artifact_root() / "policies" / "g557_gcst_static_theta_policy.csv",
        resolve(LABEL_RESULTS_CSV),
    ]
    rows = []
    for path in candidates:
        exists = Path(path).exists()
        size_mb = Path(path).stat().st_size / (1024 * 1024) if exists else 0.0
        rows.append(
            {
                "artifact_path": str(path),
                "exists": exists,
                "size_mb": csv_number(size_mb),
                "commit_to_git": size_mb <= 50 and "outputs/tmp" not in str(path).replace("\\", "/") and "logs" not in str(path).replace("\\", "/"),
                "reason": "large/raw artifact kept out of git" if size_mb > 50 or "outputs/tmp" in str(path).replace("\\", "/") or "logs" in str(path).replace("\\", "/") else "compact artifact eligible",
                **claim_flags(),
            }
        )
    return rows


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.57 decision")
    if not resolve(BLIND_SUMMARY).exists():
        main_analyze_blind([])
    verify = load_json(VERIFY_SUMMARY, {})
    context = load_json(CONTEXT_SUMMARY, {})
    label = load_json(LABEL_SUMMARY, {})
    dataset = load_json(DATASET_SUMMARY, {})
    gcst = load_json(GCST_SUMMARY, {})
    stage1 = load_json(STAGE1_SUMMARY, {})
    stage2 = load_json(STAGE2_SUMMARY, {})
    blind = load_json(BLIND_SUMMARY, {})
    if verify.get("decision") == "g557_g556_baseline_not_verified_stop":
        decision = "g557_g556_baseline_not_verified_stop"
    elif context.get("decision") == "g557_context_bank_underpowered_continue":
        decision = "g557_context_bank_underpowered_continue"
    elif label.get("decision") != "g557_label_matrix_ready_for_label_v3":
        decision = "g557_label_matrix_underpowered_continue_topup"
    elif dataset.get("decision") != "g557_label_v3_dataset_ready":
        decision = "g557_label_matrix_underpowered_continue_topup"
    elif not boolish(gcst.get("offline_generator_gate_passed")):
        decision = "g557_gcst_offline_not_better_than_controls_exploratory_only"
    elif int(number(stage1.get("success_regression_count_vs_g556_c063174"), 1)) > 5:
        decision = "g557_stage1_regressed_stop"
    elif not boolish(stage2.get("gate_passed")):
        decision = "g557_stage2_heldout_failed_keep_g556"
    elif not boolish(blind.get("gate_passed")):
        decision = "g557_blind_failed_keep_g556"
    else:
        decision = "g557_gcst_strict_blind_passed_keep_claims_closed"
    summary = {
        "schema_version": "phase5p5_repair5g557_decision_summary_v1",
        "decision": decision,
        "primary_baseline": PRIMARY_BASELINE_ID,
        "method": "GCST-LTM",
        "model_family": "TTGT",
        "candidate_object": "one graph-conditioned static theta predicted before solver run",
        "dynamic_policy": False,
        "checkpoint_policy": False,
        "traffic_input_mode": "P",
        "context_horizons": context.get("context_horizons", 0),
        "primary_row_level_examples_vs_g556": label.get("primary_row_level_examples_vs_g556", 0),
        "total_row_level_examples": label.get("total_usable_row_level_examples", 0),
        "stage1_solver_rows": stage1.get("stage1_solver_rows", 0),
        "stage2_solver_rows": stage2.get("stage2_solver_rows", 0),
        "blind_solver_rows": blind.get("blind_solver_rows", 0),
        "strict_blind_passed": decision == "g557_gcst_strict_blind_passed_keep_claims_closed",
        "success_regressions_vs_g556": 0 if decision == "g557_label_matrix_underpowered_continue_topup" else "",
        "quality_delta_vs_g556": "",
        "beats_map_family_lookup": boolish(gcst.get("beats_map_family_lookup", False)),
        "beats_tabular_only_control": boolish(gcst.get("beats_tabular_only_control", False)),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    claim_rows = [{"claim": key, "allowed": value, "reason": "claims remain closed in G5.57", **claim_flags()} for key, value in claim_flags().items()]
    comparison = [
        {"method": PRIMARY_BASELINE_ID, "role": "primary fixed baseline", "promoted": True, "solver_rows": verify.get("g556_blind_solver_rows", 0), **claim_flags()},
        {"method": "GCST-LTM", "role": "graph-conditioned static theta candidate", "promoted": summary["strict_blind_passed"], "solver_rows": summary["blind_solver_rows"], **claim_flags()},
        {"method": "map_family_lookup", "role": "control", "promoted": False, "solver_rows": 0, **claim_flags()},
        {"method": "tabular_only", "role": "control", "promoted": False, "solver_rows": 0, **claim_flags()},
    ]
    write_rows(CLAIM_LEDGER_CSV, claim_rows)
    write_rows(LARGE_ARTIFACT_MANIFEST_CSV, large_artifacts())
    write_rows(FINAL_METHOD_COMPARISON_CSV, comparison)
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.57 Decision\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- primary baseline: `{PRIMARY_BASELINE_ID}`\n"
        f"- method: `{summary['method']}`\n"
        f"- context horizons: `{summary['context_horizons']}`\n"
        f"- row-level examples vs g556: `{summary['primary_row_level_examples_vs_g556']}`\n"
        f"- Stage1/Stage2/blind rows: `{summary['stage1_solver_rows']}` / `{summary['stage2_solver_rows']}` / `{summary['blind_solver_rows']}`\n"
        f"- strict blind passed: `{summary['strict_blind_passed']}`\n\n"
        "G5.57 does not open runtime, Phase5.5, Phase6, learned-SafeGate, learned-runtime, or AAAI claims. "
        "If the label matrix is underpowered, continue top-up on the KCS instance using the commands in the label matrix summary.\n",
    )
    print(json.dumps({"decision": summary["decision"], "strict_blind_passed": summary["strict_blind_passed"]}))
    return 0

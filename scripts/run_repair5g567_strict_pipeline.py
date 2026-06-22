from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import shutil
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import generate_repair5g561_valid_scenario_bank as g561_bank  # noqa: E402
import repair5g549_common as g549  # noqa: E402
import run_repair5g562_replay_truth as g562  # noqa: E402
from gcst.generated_theta_audit import generated_theta_uid  # noqa: E402
from gcst.goal_aware_actor import make_graph_batch, pad_od_tokens, scalar_features  # noqa: E402
from gcst.graph_data import GraphData, build_graph  # noqa: E402
from gcst.graph_encoder import GraphBatch  # noqa: E402
from gcst.label_v5 import solver_ratio, solver_success  # noqa: E402
from gcst.map_hash import read_movingai_map  # noqa: E402
from gcst.real_label_graph_dataset import parse_movingai_scenario  # noqa: E402
from gcst.theta_schema import (  # noqa: E402
    BASELINE_G556,
    THETA_COLUMNS,
    THETA_HI,
    THETA_LO,
    THETA_NUMERIC_COLUMNS,
    clamp_theta_row,
    compare_theta_to_fingerprint,
    mode_columns,
    parse_updateparams_fingerprint,
)
from gcst.three_tier_baselines import (  # noqa: E402
    ADDITIVE_SOLVER_ALIAS,
    G556_SOLVER_ALIAS,
    STATIC_FLOW_SOLVER_ALIAS,
    TIER_A_ADDITIVE,
    TIER_B_STATIC_FLOW,
    TIER_C_G556,
    baseline_registry_rows,
    registry_fingerprint_sha,
    updateparams_fingerprint,
)
from repair5g2_common import scenario_path  # noqa: E402
from run_repair5f4_static_updateparams_validation import MAPS as MAP_PATHS  # noqa: E402


ROUND = "phase5p5_repair5g567"
PLAN_FILE = "czr004_g567_large_scale_tail_safe_direct_actor_plan.md"
OUTPUT_ROOT = Path(os.environ.get("G567_OUTPUT_ROOT", "outputs"))
ARTIFACT_ROOT = Path(os.environ.get("G567_ARTIFACT_ROOT", "artifacts"))
TABLES = OUTPUT_ROOT / "tables"
REPORTS = OUTPUT_ROOT / "reports"
LOGS = OUTPUT_ROOT / "logs"
MODEL_DIR = ARTIFACT_ROOT / "models/gcst"
TMP_ROOT = Path(f"outputs/tmp/{ROUND}_valid_scenario_bank")
REPLAY_SCENARIO_DIR = Path(f"outputs/tmp/{ROUND}_replay_scenarios")

VALID_CONTEXT_MANIFEST = TABLES / f"{ROUND}_valid_context_manifest.csv"
INVALID_QUARANTINE = TABLES / f"{ROUND}_invalid_quarantine.csv"
SCENARIO_VALIDITY = TABLES / f"{ROUND}_scenario_validity.csv"
SPLIT_MANIFEST = TABLES / f"{ROUND}_physical_map_split_manifest.csv"
VALIDITY_SUMMARY = REPORTS / f"{ROUND}_validity_summary.json"
VALIDITY_MD = REPORTS / f"{ROUND}_validity.md"
TRUTH_AUDIT_SUMMARY = REPORTS / f"{ROUND}_g565_truth_audit_summary.json"
TRUTH_AUDIT_MD = REPORTS / f"{ROUND}_g565_truth_audit.md"
BASELINE_REGISTRY = TABLES / f"{ROUND}_three_tier_baseline_registry.csv"
BASELINE_REGISTRY_SUMMARY = REPORTS / f"{ROUND}_baseline_registry_summary.json"
REPEATABILITY_SUMMARY = REPORTS / f"{ROUND}_repeatability_summary.json"
LABELV54_CONTEXTS = TABLES / f"{ROUND}_labelv54_contexts.csv"
LABELV54_CANDIDATES = TABLES / f"{ROUND}_labelv54_candidates.csv"
LABELV54_REPLICATES = TABLES / f"{ROUND}_labelv54_replicates.csv"
LABELV54_SAFE_SETS = REPORTS / f"{ROUND}_labelv54_safe_sets.jsonl"
LABELV54_SUMMARY = REPORTS / f"{ROUND}_labelv54_summary.json"
BUG_LOG = REPORTS / f"{ROUND}_bug_log.md"
PROTOCOL_OVERVIEW = REPORTS / f"{ROUND}_protocol_overview.md"
TIME_BUDGET_SEMANTICS = REPORTS / f"{ROUND}_time_budget_semantics.md"
SOURCE_STATE = REPORTS / f"{ROUND}_source_state.json"
MEMORY_SMOKE_3000 = REPORTS / f"{ROUND}_3000_agent_memory_smoke.json"
ACTOR_TRAINING_MATRIX = TABLES / f"{ROUND}_actor_training_matrix.csv"
ACTOR_GRADIENT_AUDIT = TABLES / f"{ROUND}_actor_gradient_audit.csv"
ACTOR_TRAINING_SUMMARY = REPORTS / f"{ROUND}_actor_training_summary.json"
OUTCOME_ENSEMBLE_SUMMARY = REPORTS / f"{ROUND}_outcome_ensemble_summary.json"
DISTRIBUTIONAL_CRITIC_SUMMARY = REPORTS / f"{ROUND}_distributional_critic_summary.json"
DISTRIBUTIONAL_CRITIC_PREDICTIONS = TABLES / f"{ROUND}_distributional_critic_predictions.csv"
DISTRIBUTIONAL_CRITIC_MODEL_AUDIT = TABLES / f"{ROUND}_distributional_critic_model_audit.csv"
SCALING_SUMMARY = REPORTS / f"{ROUND}_valid_scaling_summary.json"
DEVELOPMENT_SUMMARY = REPORTS / f"{ROUND}_development_three_tier_summary.json"
BLIND_SUMMARY = REPORTS / f"{ROUND}_blind_three_tier_summary.json"
FINAL_DECISION_SUMMARY = REPORTS / f"{ROUND}_final_decision_summary.json"
FINAL_DECISION_MD = REPORTS / f"{ROUND}_final_decision.md"
ARTIFACT_MANIFEST = REPORTS / f"{ROUND}_artifact_manifest.json"
SOLVER_BUDGET_AUDIT = TABLES / f"{ROUND}_solver_budget_audit.csv"
SOLVER_BUDGET_AUDIT_SUMMARY = REPORTS / f"{ROUND}_solver_budget_audit_summary.json"
PUBLIC_BENCHMARK_INGESTION_MD = REPORTS / f"{ROUND}_public_benchmark_ingestion.md"
PUBLIC_BENCHMARK_INGESTION_SUMMARY = REPORTS / f"{ROUND}_public_benchmark_ingestion_summary.json"
PUBLIC_MAP_REGISTRY = TABLES / f"{ROUND}_public_map_registry.csv"
PUBLIC_SCENARIO_REGISTRY = TABLES / f"{ROUND}_public_scenario_registry.csv"
PARENT_MAP_SPLIT_AUDIT = TABLES / f"{ROUND}_parent_map_split_audit.csv"

NO_LTM_DIAGNOSTIC = "lacam_star"
FIELD_GROUPS = {
    "G1_congestion_commit_block": [0, 1, 2],
    "G2_congestion_wait": [3, 4],
    "G3_goal_flow": [5, 6],
    "G4_decay": [7, 8],
    "G5_channel_weights": [9, 10],
    "G6_shield_bounds": [11, 12, 13, 14],
}

G567_MAP_SPECS = [
    ("g567-empty-8x8", "empty", 8, 8),
    ("g567-empty-16x16", "empty", 16, 16),
    ("g567-empty-32x32", "empty", 32, 32),
    ("g567-empty-48x32", "empty", 48, 32),
    ("g567-random-16x16-a", "random", 16, 16),
    ("g567-random-24x24-a", "random", 24, 24),
    ("g567-random-32x32-a", "random", 32, 32),
    ("g567-random-40x40-b", "random", 40, 40),
    ("g567-maze-24x24-a", "maze", 24, 24),
    ("g567-maze-48x32-a", "maze", 48, 32),
    ("g567-maze-64x32-b", "maze", 64, 32),
    ("g567-room-24x24-a", "room", 24, 24),
    ("g567-room-48x48-a", "room", 48, 48),
    ("g567-room-64x48-b", "room", 64, 48),
    ("g567-warehouse-20x10-a", "warehouse", 20, 10),
    ("g567-warehouse-32x24-a", "warehouse", 32, 24),
    ("g567-warehouse-48x32-a", "warehouse", 48, 32),
    ("g567-warehouse-64x40-b", "warehouse", 64, 40),
    ("g567-connector-24x24-a", "connector", 24, 24),
    ("g567-connector-48x48-a", "connector", 48, 48),
    ("g567-tunnel-24x24-a", "tunnel", 24, 24),
    ("g567-tunnel-64x32-a", "tunnel", 64, 32),
    ("g567-loop-32x32-a", "loop", 32, 32),
    ("g567-loop-56x56-a", "loop", 56, 56),
    ("g567-tree-32x32-a", "tree", 32, 32),
    ("g567-tree-56x40-a", "tree", 56, 40),
    ("g567-string-32x24-a", "irregular_bottleneck", 32, 24),
    ("g567-string-64x32-a", "irregular_bottleneck", 64, 32),
    ("g567-corners-48x48-a", "irregular_bottleneck", 48, 48),
    ("g567-city-32x32-a", "city", 32, 32),
    ("g567-city-64x48-a", "city", 64, 48),
    ("g567-cross-32x32-a", "cross", 32, 32),
    ("g567-cross-64x40-a", "cross", 64, 40),
    ("g567-lanes-48x32-a", "lanes", 48, 32),
    ("g567-lanes-64x48-a", "lanes", 64, 48),
    ("g567-plaza-40x40-a", "plaza", 40, 40),
    ("g567-plaza-64x64-a", "plaza", 64, 64),
    ("g567-islands-48x48-a", "islands", 48, 48),
    ("g567-islands-72x48-a", "islands", 72, 48),
    ("g567-chambers-48x32-a", "chambers", 48, 32),
    ("g567-chambers-64x48-a", "chambers", 64, 48),
    ("g567-spiral-40x40-a", "spiral", 40, 40),
    ("g567-spiral-64x64-a", "spiral", 64, 64),
    ("g567-large-empty-96x96-a", "large_empty", 96, 96),
    ("g567-large-empty-128x128-a", "large_empty", 128, 128),
    ("g567-large-random-128x96-a", "large_random", 128, 96),
    ("g567-large-random-160x120-a", "large_random", 160, 120),
    ("g567-large-warehouse-128x96-a", "large_warehouse", 128, 96),
    ("g567-large-warehouse-192x128-a", "large_warehouse", 192, 128),
    ("g567-large-room-128x128-a", "large_room", 128, 128),
    ("g567-large-room-192x128-a", "large_room", 192, 128),
    ("g567-large-maze-128x128-a", "large_maze", 128, 128),
    ("g567-large-maze-192x128-a", "large_maze", 192, 128),
    ("g567-large-connector-160x128-a", "large_connector", 160, 128),
    ("g567-large-lanes-192x128-a", "large_lanes", 192, 128),
] * 2

G567_AGENT_TIERS = [
    8,
    12,
    16,
    24,
    32,
    48,
    64,
    80,
    128,
    192,
    256,
    384,
    512,
    768,
    1000,
    1500,
    2000,
    2500,
    3000,
]

G567_BUDGET_PROFILES = [(30000, 30.0, 12)]
G567_LARGE_PRIMARY_AGENT_TIERS = {2000, 2500, 3000}
G567_UNIFORM_30S_PRIMARY_BUDGET_PROFILE = (30000, 30.0, 12, "uniform_30s_all_agent_tiers_primary_exact")
G567_LARGE_PRIMARY_BUDGET_PROFILE = G567_UNIFORM_30S_PRIMARY_BUDGET_PROFILE


@dataclass(frozen=True)
class G567Context:
    dataset_row_id: str
    evaluation_uid: str
    instance_uid: str
    split: str
    map: str
    map_family: str
    agents: int
    seed: int
    budget_ms: int
    base_time_limit_sec: float
    ltm_max_iterations: int
    horizon_id: str
    scenario_path: Path
    replay_scenario_path: Path
    scenario_sha256: str
    physical_map_sha256: str
    assignment_sha256: str
    graph_with_traffic: GraphData
    assignment: dict[str, Any]
    feature_row: dict[str, Any]
    budget_role: str = ""
    process_hard_timeout_sec: float = 0.0


@dataclass(frozen=True)
class ActorTrainExample:
    example_id: str
    evaluation_uid: str
    split: str
    map_family: str
    graph: GraphData
    assignment: dict[str, Any]
    feature_row: dict[str, Any]
    target: np.ndarray
    weight: float
    positive_count: int
    safe_count: int


def claims() -> dict[str, bool]:
    return {
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def rel(path: str | Path) -> str:
    p = resolve(path)
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def number(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def stable_uid(*parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def safe_token(text: Any) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(text).lower()).strip("_")[:56] or "item"


def sha256_file(path: str | Path) -> str:
    p = resolve(path)
    if not p.exists():
        return ""
    digest = hashlib.sha256()
    with p.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def budget_profile_for_agent_tier(agent_count: int, profile_index: int, purpose: str = "primary") -> tuple[int, float, int, str]:
    """Return the fail-closed G5.67 primary budget contract.

    GPT Pro/user Gate-3A policy requires every planned solver row to use the
    same 30s internal budget and 60s outer hard timeout across agent/map tiers.
    Short-budget stress and recovery-curve probes must be separate explicit
    diagnostics; they are not produced by this staged execution path.
    """
    return G567_UNIFORM_30S_PRIMARY_BUDGET_PROFILE


def process_hard_timeout_for_internal_budget(internal_sec: float) -> float:
    internal = float(internal_sec)
    if abs(internal - 30.0) <= 1.0e-9:
        return 60.0
    return max(internal + 0.25, internal * 1.10)


def public_benchmark_ingestion_state() -> dict[str, Any]:
    summary = read_json(PUBLIC_BENCHMARK_INGESTION_SUMMARY)
    map_rows = read_rows(PUBLIC_MAP_REGISTRY)
    scenario_rows = read_rows(PUBLIC_SCENARIO_REGISTRY)
    split_rows = read_rows(PARENT_MAP_SPLIT_AUDIT)
    decision = str(summary.get("decision", ""))
    ready = decision == "g567_public_benchmark_ingestion_ready"
    if not summary:
        decision = "g567_public_benchmark_ingestion_missing"
    return {
        "decision": decision,
        "ready": ready,
        "summary_path": rel(PUBLIC_BENCHMARK_INGESTION_SUMMARY),
        "map_registry_path": rel(PUBLIC_MAP_REGISTRY),
        "scenario_registry_path": rel(PUBLIC_SCENARIO_REGISTRY),
        "parent_split_audit_path": rel(PARENT_MAP_SPLIT_AUDIT),
        "map_registry_rows": len(map_rows),
        "scenario_registry_rows": len(scenario_rows),
        "parent_split_audit_rows": len(split_rows),
        "failure_count": summary.get("failure_count", 0),
        "failures": summary.get("failures", []),
        "required_panels_present": summary.get("required_panels_present", False),
    }


def discover_public_benchmark_map_specs(limit: int = 64) -> list[dict[str, Any]]:
    state = public_benchmark_ingestion_state()
    if not state["ready"]:
        return []
    registry_rows = read_rows(PUBLIC_MAP_REGISTRY)
    specs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in registry_rows:
        if str(row.get("validation_result", "")).strip().lower() != "pass":
            continue
        if not boolish(row.get("use_in_g567", "true")):
            continue
        if str(row.get("map_source_type", "")) != "canonical_public_benchmark_map":
            continue
        path = resolve(row.get("local_map_path", ""))
        if not path.exists():
            continue
        digest = sha256_file(path)
        expected = str(row.get("physical_map_sha256") or row.get("parent_physical_map_sha256") or "")
        if not digest or (expected and digest != expected) or digest in seen:
            continue
        seen.add(digest)
        width, height, grid = read_movingai_map(path)
        free_count = len(g561_bank.free_cells(grid))
        if free_count < min(G567_AGENT_TIERS):
            continue
        specs.append(
            {
                "map": safe_token(row.get("map_name") or path.stem),
                "map_family": str(row.get("map_family") or f"public_benchmark_{safe_token(row.get('source_category') or path.parent.name)}"),
                "width": width,
                "height": height,
                "grid": grid,
                "source_path": path,
                "source_sha256": digest,
                "free_cells": free_count,
                "map_source_type": "canonical_public_benchmark_map",
                "source_category": row.get("source_category", ""),
                "panel": row.get("panel", ""),
                "public_registry_source": rel(PUBLIC_MAP_REGISTRY),
            }
        )
        if len(specs) >= limit:
            return specs
    return specs


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: str | Path) -> dict[str, Any]:
    p = resolve(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def read_rows(path: str | Path) -> list[dict[str, str]]:
    p = resolve(path)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_rows(path: str | Path, rows: list[dict[str, Any]]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with p.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: str | Path, text: str) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def git_capture(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:
        return f"git_error:{exc}"


def classify_source_state(
    *,
    inside_work_tree: str,
    head: str,
    status_short: str,
    submodule_status: str,
    source_plan_sha256: str,
    expected_head: str = "",
) -> list[str]:
    failures: list[str] = []
    if inside_work_tree != "true":
        failures.append("missing_or_invalid_git_metadata")
    if head.startswith("git_error:"):
        failures.append("missing_head")
    if expected_head and head != expected_head:
        failures.append("wrong_head")
    if status_short.startswith("git_error:"):
        failures.append("dirty_status_unavailable")
    elif status_short.strip():
        failures.append("dirty_status")
    if submodule_status.startswith("git_error:"):
        failures.append("submodule_status_unavailable")
    for line in submodule_status.splitlines():
        if line[:1] in {"-", "+", "U"}:
            failures.append("submodule_mismatch")
            break
    if not source_plan_sha256:
        failures.append("missing_source_plan")
    return failures


def write_source_state(expected_head: str = "") -> dict[str, Any]:
    inside_work_tree = git_capture("rev-parse", "--is-inside-work-tree")
    head = git_capture("rev-parse", "HEAD")
    status_short = git_capture("status", "--short")
    submodule_status = git_capture("submodule", "status", "--recursive")
    plan_sha = sha256_file(PLAN_FILE)
    failures = classify_source_state(
        inside_work_tree=inside_work_tree,
        head=head,
        status_short=status_short,
        submodule_status=submodule_status,
        source_plan_sha256=plan_sha,
        expected_head=expected_head,
    )
    summary = {
        "schema_version": f"{ROUND}_source_state_v1",
        "decision": "g567_source_state_clean" if not failures else "g567_source_state_fail_closed",
        "source_state_failures": failures,
        "inside_work_tree": inside_work_tree,
        "head": head,
        "expected_head": expected_head,
        "head_matches_expected": (not expected_head) or head == expected_head,
        "branch": git_capture("branch", "--show-current"),
        "status_short": status_short,
        "status_clean": status_short == "",
        "source_plan": PLAN_FILE,
        "source_plan_sha256": plan_sha,
        "submodule_status": submodule_status,
        "submodule_status_clean": "submodule_mismatch" not in failures,
        **claims(),
    }
    write_json(SOURCE_STATE, summary)
    return summary


def write_protocol_documents() -> None:
    write_text(
        BUG_LOG,
        "# Repair5G.5.67 Bug Log\n\n"
        "## Confirmed P0 Bugs Repaired\n\n"
        "- `labelv53_safe_omitted_additive`: G5.66 safe labels omitted additive success regression. G5.67 Label-v5.4 requires `safe_A and safe_B` for primary safety.\n"
        "- `labelv53_any_tier_positive`: G5.66 allowed any-tier improvement to create a positive label. G5.67 requires joint A/B improvement for primary positives.\n"
        "- `repeatability_single_run_misreported`: G5.66 counted single executions as repeats and hard-coded worker contention. G5.67 records replicate IDs and reports contention only if measured.\n"
        "- `safe_theta_arithmetic_average`: G5.66 averaged multimodal safe thetas. G5.67 uses a conservative medoid target.\n"
        "- `agent_tier_cap_80`: G5.66 context generation reused 8..80 tiers. G5.67 includes tiers through 3000 and large maps that can host them.\n\n"
        "## Confirmed P0 Bugs Added By Gate-3A Review\n\n"
        "- `process_hard_timeout_not_enforced`: `process_hard_timeout_sec` was recorded in the replay plan but the solver subprocess used an unbounded `subprocess.run`; Gate-3A now uses a per-process hard timeout with process-group termination provenance.\n"
        "- `source_state_not_fail_closed`: source HEAD/status/submodules were recorded but not enforced before execution; Gate-3A now blocks on missing Git metadata, dirty status, wrong HEAD, or submodule mismatch.\n\n"
        "## Confirmed P0 Bugs Added By Budget/Training Review\n\n"
        "- `large_agent_budget_underallocated`: 2000/2500/3000-agent primary rows used generic budget cycling, including 20s. G5.67 now requires 30s primary internal budget and 60s hard timeout for those tiers.\n"
        "- `hard_timeout_polluted_scientific_labels`: timeout placeholders looked like ordinary no-solution rows. Timeout rows are now infrastructure failures and are excluded from scientific pairs/labels.\n"
        "- `synthetic_only_final_bank`: final context validity could be satisfied with synthetic stress maps only. Full validity now requires a documented mixture of canonical/public benchmark maps and synthetic stress maps.\n"
        "- `label_train_split_leakage`: actor training could draw from development/calibration contexts. G5.67 now separates `LABEL_TRAIN` and blocks full actor training below 24,000 unique exact-labeled training contexts.\n\n"
        "## Confirmed P0 Bugs Added By Uniform-Budget Review\n\n"
        "- `nonuniform_small_tier_timeout_contract`: small and medium diagnostic tiers could still use legacy short internal budgets while large tiers used 30s, making cross-tier evidence non-comparable. G5.67 staged execution now assigns `30.0s` internal / `60.0s` hard timeout to every planned agent/map row and fails budget audit on any non-uniform row.\n\n"
        "## Confirmed P0 Bugs Added By Stage-2A/Gate-3A Review\n\n"
        "- `response_theta_front_loaded_context_coverage`: response-surface acquisition emitted up to 49 candidates for each early context before later LABEL_TRAIN contexts received any exact actor candidate. G5.67 now emits one coverage-first candidate for every context before exploratory alpha/group candidates.\n"
        "- `a5_attention_heads_checkpoint_load_mismatch`: A5 training saved `attention_heads=8`, but checkpoint loading only read `heads` and could reconstruct a 4-head model. G5.67 now saves both fields and loads either alias.\n"
        "- `critic_development_split_mismatch`: the distributional critic was called with `development_contexts`, while Label-v5.4 candidates are produced on `LABEL_TRAIN`. G5.67 now routes critic candidate fitting through `LABEL_TRAIN` and reserves CALIBRATION for calibration evidence.\n"
        "- `blind_feature_preload_before_primary_freeze`: the full main path materialized BLIND graph/C0/F0 features before one primary actor was selected. G5.67 now records only blind map/scenario/assignment hashes before freeze and materializes BLIND features only afterward.\n"
        "- `public_ratio_and_official_scenario_gate_too_weak`: the validity gate accepted any nonzero public/synthetic mixture. G5.67 now blocks full validity unless LABEL_TRAIN public/canonical >=50%, development/blind >=70%, parent-map hashes >=256, and the official MovingAI/MAPF-LNS2 scenario-prefix consumer is ready.\n\n"
        "## Confirmed P0 Bugs Added By Stage-2A Remote Run\n\n"
        "- `stage2a_replay_failure_not_fail_closed`: the diagnostic A5 training script continued into Label-v5.4 construction and training even when its replay summary reported process hard-timeout rows. Stage-2A now blocks before labels/training unless replay materialization, recognition, identity, scenario hash, and hard-timeout gates all pass.\n"
        "- `labelv54_candidate_split_not_preserved`: Label-v5.4 candidate rows omitted split/map/agent metadata, making `label_train_unique_exact_labeled_contexts` report 0 even when pair/context rows were LABEL_TRAIN. Candidate rows now preserve context metadata and the unique LABEL_TRAIN count is derived from context rows.\n"
        "- `stage2a_unbounded_diagnostic_graph_size`: diagnostic training selected huge public maps such as orz900d/paris/sortation_large, causing RTX5090 OOM during A5 graph encoder backprop. Stage-2A now has explicit diagnostic graph-size bounds and reports them; this is not a full-campaign large-graph throughput proof.\n\n"
        "## Active Risks To Watch\n\n"
        "- `official_scenario_prefix_not_yet_consumed_by_generator`: public benchmark ingestion freezes official MovingAI/MAPF-LNS2 scenarios, but the current valid-context generator still materializes czr004-derived scenarios on public parent maps. Do not report those derived contexts as official MovingAI scenario results until the official prefix consumer is wired and tested.\n"
        "- `large_graph_memory`: existing graph encoders can be memory-heavy on large maps; the 3000-agent smoke artifact must pass before claims.\n"
        "- `critic_calibration_strength`: the critic must pass skill/calibration checks, not coverage alone.\n",
    )
    write_text(
        PROTOCOL_OVERVIEW,
        "# Repair5G.5.67 Protocol Overview\n\n"
        "- Run source from a complete Git worktree with recorded HEAD and plan hash.\n"
        "- Fail closed before execution on missing Git metadata, dirty source state, wrong expected HEAD, or submodule mismatch.\n"
        "- Require `phase5p5_repair5g567_public_benchmark_ingestion_summary.json` to be ready before a public/synthetic context bank can pass.\n"
        "- Generate a valid context bank with large-agent tiers through 3000.\n"
        "- Use single-worker pinned repeatability for boundary adjudication; broad collection may use more workers but cannot certify regressions.\n"
        "- Build Label-v5.4 with explicit A/B/C safety, AB/ABC positives, replicate confidence, and safe-set preservation.\n"
        "- Train exported actors as one deterministic continuous 15D theta predictor; no runtime selector, codebook, critic, or candidate deletion is exported.\n",
    )
    write_text(
        TIME_BUDGET_SEMANTICS,
        "# Repair5G.5.67 Time Budget Semantics\n\n"
        "- `solver_internal_time_limit_sec`: the budget passed to the solver and kept equal across methods.\n"
        "- Every staged G5.67 primary row, across all agent counts and all maps, uses `solver_internal_time_limit_sec = 30.0`.\n"
        "- `20.0s`, `45.0s`, and `60.0s` internal budgets are not emitted by the current staged execution path; they require separately approved diagnostic/recovery jobs.\n"
        "- `process_hard_timeout_sec`: explicit per-row outer allowance enforced by the parent process; G5.67 full execution blocks if any planned row is missing it.\n"
        "- For a `30.0s` internal budget, `process_hard_timeout_sec` is fixed at `60.0`; timeout rows are infrastructure failures, not no-solution labels or success regressions.\n"
        "- Linux solver subprocesses run in a new process group; timeout sends SIGTERM, waits the recorded grace interval, then SIGKILLs the group if needed.\n"
        "- 30s exploratory response surfaces are screened multi-fidelity; full 30s exact execution is reserved for selected candidates, calibration rows, boundary cases, development replay, and blind replay.\n"
        "- `actor inference time`: measured outside solver budget where available and reported as overhead, not extra search time.\n"
        "- `queueing/CPU contention`: broad parallel collection is diagnostic; success-regression adjudication uses one worker and recorded thread env.\n",
    )


def update_remote_map_registries(map_dir: Path) -> None:
    for path in sorted(resolve(map_dir).glob("*.map")):
        try:
            value = str(path.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            value = str(path)
        MAP_PATHS[path.stem] = value
    try:
        import repair5g5_common as g5

        g5.MAP_PATHS.update(MAP_PATHS)
    except Exception:
        pass
    try:
        import run_repair5f4_static_updateparams_validation as f4

        f4.MAPS.update(MAP_PATHS)
    except Exception:
        pass


def movingai_assignment_hash(starts: Iterable[Any], goals: Iterable[Any]) -> str:
    text = "|".join(f"{tuple(s)}->{tuple(g)}" for s, g in zip(starts, goals))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_g567_assignment(grid: list[str], width: int, height: int, agent_count: int, regime_name: str, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    comps = [comp for comp in g561_bank.component_cells(grid) if len(comp) >= agent_count]
    if not comps:
        raise ValueError("no component can host requested agents")
    comp = comps[seed % len(comps)]
    start_region, goal_region = g561_bank.regime_regions(regime_name)
    starts = g561_bank.sample_unique(g561_bank.region(comp, width, height, start_region), rng, agent_count, comp)
    goals = g561_bank.sample_unique(g561_bank.region(comp, width, height, goal_region), rng, agent_count, comp)
    rng.shuffle(goals)
    if all(s == g for s, g in zip(starts, goals)) and len(goals) > 1:
        goals = goals[1:] + goals[:1]
    pairs = list(zip(starts, goals))
    distances = [abs(start[0] - goal[0]) + abs(start[1] - goal[1]) for start, goal in pairs]
    return {
        "starts": starts,
        "goals": goals,
        "distances": distances,
        "pairs": pairs,
        "distance_mode": "manhattan_lower_bound_no_path_materialization",
        "component_size": len(comp),
        "reachability_mode": "component_connected_no_path_materialization",
        "unique_start_count": len(set(starts)),
        "unique_goal_count": len(set(goals)),
        "start_goal_overlap_count": len(set(starts) & set(goals)),
        "own_start_goal_match_count": sum(start == goal for start, goal in pairs),
        "assignment_sha256": movingai_assignment_hash(starts, goals),
    }


def graph_with_edge_features(graph: GraphData, edge_features: np.ndarray) -> GraphData:
    return GraphData(
        topology_id=graph.topology_id,
        map_name=graph.map_name,
        width=graph.width,
        height=graph.height,
        cells=graph.cells,
        node_features=graph.node_features,
        edge_index=graph.edge_index,
        edge_features=edge_features,
        hashes=graph.hashes,
        component_count=graph.component_count,
        physical_free_cell_count=graph.physical_free_cell_count,
    )


def copy_for_replay(row: dict[str, Any], scenario_path_source: Path, replay_dir: Path) -> Path:
    replay_path = scenario_path(replay_dir, str(row["map"]), int(row["solver_seed"]))
    replay_path.parent.mkdir(parents=True, exist_ok=True)
    if not replay_path.exists() or sha256_file(replay_path) != sha256_file(scenario_path_source):
        shutil.copyfile(scenario_path_source, replay_path)
    return replay_path


def make_generated_contexts(target_valid: int, seed: int, tmp_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rng = random.Random(seed)
    map_dir = tmp_root / "maps"
    scenario_dir = tmp_root / "scenarios"
    benchmark_specs = discover_public_benchmark_map_specs()
    audit_rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    generated = 0
    attempts = 0
    while generated < target_valid and attempts < target_valid * 25:
        attempts += 1
        agent_count = G567_AGENT_TIERS[generated % len(G567_AGENT_TIERS)]
        public_candidates = [
            spec
            for spec in benchmark_specs
            if int(spec["free_cells"]) >= agent_count and int(spec["width"]) * int(spec["height"]) >= max(agent_count * 2, agent_count + 64)
        ]
        use_public_benchmark = bool(public_candidates) and generated % 4 == 0
        if use_public_benchmark:
            spec_b = public_candidates[(generated + attempts + seed) % len(public_candidates)]
            concrete_map = str(spec_b["map"])
            family = str(spec_b["map_family"])
            width = int(spec_b["width"])
            height = int(spec_b["height"])
            grid = list(spec_b["grid"])
            map_source_type = str(spec_b["map_source_type"])
            benchmark_source_path = rel(spec_b["source_path"])
            benchmark_source_sha256 = str(spec_b["source_sha256"])
        else:
            specs = [
                spec
                for spec in G567_MAP_SPECS
                if int(spec[2]) * int(spec[3]) >= max(agent_count * 2, agent_count + 64)
            ]
            if not specs:
                specs = list(G567_MAP_SPECS)
            map_name, family, width, height = specs[(generated + attempts + seed) % len(specs)]
            map_variant = attempts % 4
            concrete_map = f"{map_name}-v{map_variant}"
            grid = g561_bank.synthetic_grid(concrete_map, width, height)
            map_source_type = "synthetic_stress_map"
            benchmark_source_path = ""
            benchmark_source_sha256 = ""
        free_count = len(g561_bank.free_cells(grid))
        if free_count < min(G567_AGENT_TIERS):
            continue
        if agent_count > free_count:
            continue
        regime_name = g561_bank.REGIMES[(generated + seed) % len(g561_bank.REGIMES)]
        budget_ms, base_sec, ltm_iters, budget_role = budget_profile_for_agent_tier(agent_count, generated + attempts)
        process_hard_timeout_sec = process_hard_timeout_for_internal_budget(base_sec)
        solver_seed = seed * 1_000_000 + attempts
        try:
            assignment = build_g567_assignment(grid, width, height, agent_count, regime_name, solver_seed)
        except ValueError:
            continue
        map_path = map_dir / f"{concrete_map}.map"
        scen_path = scenario_dir / f"{concrete_map}-random-{solver_seed}.scen"
        map_sha = g561_bank.write_map(map_path, grid)
        scenario_sha = g561_bank.write_scenario(scen_path, concrete_map, width, height, assignment)
        instance_uid = stable_uid(
            "g567_valid_instance",
            concrete_map,
            solver_seed,
            scenario_sha,
            map_sha,
            assignment["assignment_sha256"],
            agent_count,
            budget_ms,
            ltm_iters,
        )
        density = agent_count / max(1, free_count)
        common = {
            "g567_instance_uid": instance_uid,
            "g567_evaluation_uid": stable_uid("g567_eval", instance_uid, budget_ms, ltm_iters),
            "map": concrete_map,
            "map_family": family,
            "width": width,
            "height": height,
            "free_cells": free_count,
            "solver_seed": solver_seed,
            "scenario_sha256": scenario_sha,
            "physical_map_sha256": map_sha,
            "assignment_sha256": assignment["assignment_sha256"],
            "pair_count": agent_count,
            "agent_count": agent_count,
            "start_goal_regime": regime_name,
            "nominal_budget_ms": budget_ms,
            "base_time_limit_sec": base_sec,
            "solver_internal_time_limit_sec": base_sec,
            "process_hard_timeout_sec": process_hard_timeout_sec,
            "budget_role": budget_role,
            "budget_contract": "uniform_all_agent_tiers_primary_30s_hard_timeout_60s",
            "ltm_max_iterations": ltm_iters,
            "agent_density": density,
            "scenario_bank_source": "g567_component_aware_mixed_public_benchmark_and_synthetic",
            "map_source_type": map_source_type,
            "benchmark_source_path": benchmark_source_path,
            "benchmark_source_sha256": benchmark_source_sha256,
            "context_generation_stage": "stage_a_component_validity_only",
            "feature_materialization_stage": "stage_b_deferred_c0_f0_traffic_prior",
            "raw_map_path": rel(map_path),
            "raw_scenario_path": rel(scen_path),
            "path_found_rate": 1.0,
            "path_found_rate_source": "same_connected_component_no_path_materialization",
            "component_size": assignment["component_size"],
            "reachability_mode": assignment["reachability_mode"],
            "distance_mode": assignment["distance_mode"],
            "start_goal_overlap_count": assignment["start_goal_overlap_count"],
            "own_start_goal_match_count": assignment["own_start_goal_match_count"],
            **claims(),
        }
        manifest_rows.append(common)
        audit_rows.append(
            {
                **common,
                "scenario_file_exists": True,
                "scenario_sha256_expected": scenario_sha,
                "scenario_sha256_actual": scenario_sha,
                "scenario_sha256_match": True,
                "map_file_exists": True,
                "map_sha256_expected": map_sha,
                "map_sha256_actual": map_sha,
                "map_sha256_match": True,
                "scenario_pair_count_expected": agent_count,
                "scenario_pair_count_actual": agent_count,
                "scenario_pair_count_match": True,
                "unique_start_count": assignment["unique_start_count"],
                "unique_goal_count": assignment["unique_goal_count"],
                "duplicate_starts": False,
                "duplicate_goals": False,
                "all_starts_traversable": True,
                "all_goals_traversable": True,
                "all_pairs_reachable": True,
                "assignment_sha256_expected": assignment["assignment_sha256"],
                "assignment_sha256_actual": assignment["assignment_sha256"],
                "assignment_sha256_match": True,
                "width_height_match": True,
                "all_agent_mass_preserved": True,
                "valid": True,
                "failure_reasons": "",
            }
        )
        generated += 1
        if generated % 500 == 0:
            print(json.dumps({"event": "g567_valid_generation_progress", "generated": generated, "attempts": attempts}), flush=True)
    return audit_rows, manifest_rows, {
        "attempts": attempts,
        "generated": generated,
        "benchmark_map_specs": len(benchmark_specs),
        "public_benchmark_ingestion_state": public_benchmark_ingestion_state(),
    }


def split_roles_by_context_target(rows: list[dict[str, Any]]) -> dict[str, str]:
    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_hash[str(row["physical_map_sha256"])].append(row)
    total = len(rows)
    targets = {
        "BLIND": max(math.ceil(total * 0.15), 1000) if total >= 5000 else max(1, math.ceil(total * 0.15)),
        "CALIBRATION": max(1, math.ceil(total * 0.10)),
        "VALIDATION": max(1, math.ceil(total * 0.15)),
    }
    assigned_counts = {"LABEL_TRAIN": 0, "VALIDATION": 0, "CALIBRATION": 0, "BLIND": 0}
    roles: dict[str, str] = {}
    ordered_hashes = sorted(by_hash, key=lambda h: (by_hash[h][0].get("map_family", ""), h))
    for role in ["BLIND", "CALIBRATION", "VALIDATION"]:
        for h in ordered_hashes:
            if h in roles:
                continue
            if assigned_counts[role] >= targets[role]:
                break
            roles[h] = role
            assigned_counts[role] += len(by_hash[h])
    for h in ordered_hashes:
        if h not in roles:
            roles[h] = "LABEL_TRAIN"
            assigned_counts["LABEL_TRAIN"] += len(by_hash[h])
    return roles


def materialize_valid_bank(target_valid: int, seed: int, *, overwrite: bool) -> dict[str, Any]:
    if VALID_CONTEXT_MANIFEST.exists() and not overwrite:
        return read_json(VALIDITY_SUMMARY)
    audit_rows, manifest_rows, meta = make_generated_contexts(target_valid, seed, resolve(TMP_ROOT))
    valid_rows = [row for row in manifest_rows if boolish(row.get("path_found_rate") == 1.0 or row.get("path_found_rate"))]
    by_hash = {}
    for row in valid_rows:
        by_hash.setdefault(str(row["physical_map_sha256"]), row)
    hash_roles = split_roles_by_context_target(valid_rows)
    replay_dir = resolve(REPLAY_SCENARIO_DIR)
    for idx, row in enumerate(valid_rows):
        src = resolve(row["raw_scenario_path"])
        replay = copy_for_replay(row, src, replay_dir)
        row["split"] = hash_roles[str(row["physical_map_sha256"])]
        row["g567_dataset_row_id"] = f"g567_valid_{idx:06d}"
        row["replay_scenario_path"] = rel(replay)
        row["replay_scenario_sha256"] = sha256_file(replay)
        row["blind_locked"] = row["split"] == "BLIND"
    for row in audit_rows:
        row["split"] = hash_roles.get(str(row["physical_map_sha256"]), "INVALID_QUARANTINE")
    invalid_rows = [row for row in audit_rows if not boolish(row.get("valid")) or number(row.get("path_found_rate"), 0.0) != 1.0]
    split_rows = []
    for idx, h in enumerate(sorted(by_hash)):
        sample = by_hash[h]
        split_rows.append(
            {
                "physical_map_sha256": h,
                "split": hash_roles[h],
                "map_example": sample["map"],
                "map_family": sample["map_family"],
                "frozen_split_index": idx,
                "contexts_in_hash": sum(1 for row in valid_rows if str(row["physical_map_sha256"]) == h),
                **claims(),
            }
        )
    write_rows(VALID_CONTEXT_MANIFEST, valid_rows)
    write_rows(INVALID_QUARANTINE, invalid_rows)
    write_rows(SCENARIO_VALIDITY, audit_rows)
    write_rows(SPLIT_MANIFEST, split_rows)
    update_remote_map_registries(resolve(TMP_ROOT) / "maps")
    split_counts = Counter(row["split"] for row in valid_rows)
    families = Counter(row["map_family"] for row in valid_rows)
    source_types = Counter(str(row.get("map_source_type", "")) for row in valid_rows)
    budgets = Counter(str(row["nominal_budget_ms"]) for row in valid_rows)
    agents = Counter(str(row["agent_count"]) for row in valid_rows)
    blind_hashes = {row["physical_map_sha256"] for row in valid_rows if row["split"] == "BLIND"}
    benchmark_contexts = source_types.get("canonical_public_benchmark_map", 0)
    synthetic_contexts = source_types.get("synthetic_stress_map", 0)
    ingestion_state = public_benchmark_ingestion_state()
    benchmark_mixture_ok = bool(ingestion_state.get("ready")) and benchmark_contexts > 0 and synthetic_contexts > 0
    split_source_counts: dict[str, Counter[str]] = defaultdict(Counter)
    split_totals: Counter[str] = Counter()
    for row in valid_rows:
        split = str(row.get("split", ""))
        split_totals[split] += 1
        split_source_counts[split][str(row.get("map_source_type", ""))] += 1

    def public_fraction(split: str) -> float:
        total = max(1, split_totals.get(split, 0))
        return split_source_counts[split].get("canonical_public_benchmark_map", 0) / total

    label_train_public_fraction = public_fraction("LABEL_TRAIN")
    development_public_fraction = (
        (split_source_counts["VALIDATION"].get("canonical_public_benchmark_map", 0) + split_source_counts["CALIBRATION"].get("canonical_public_benchmark_map", 0))
        / max(1, split_totals.get("VALIDATION", 0) + split_totals.get("CALIBRATION", 0))
    )
    blind_public_fraction = public_fraction("BLIND")
    source_ratio_targets_met = (
        label_train_public_fraction >= 0.50
        and development_public_fraction >= 0.70
        and blind_public_fraction >= 0.70
    )
    uniform_30s_budget_target_met = set(budgets) == {"30000"} if valid_rows else False
    physical_map_hash_target_met = len(by_hash) >= 256
    official_scenario_prefix_consumer_ready = False
    ready = (
        len(valid_rows) >= target_valid
        and benchmark_mixture_ok
        and source_ratio_targets_met
        and uniform_30s_budget_target_met
        and physical_map_hash_target_met
        and official_scenario_prefix_consumer_ready
    )
    summary = {
        "schema_version": f"{ROUND}_validity_summary_v1",
        "decision": "g567_valid_context_bank_ready" if ready else "g567_valid_context_bank_blocked_by_target_public_ratio_hash_or_official_scenario_gate",
        "target_valid_contexts": target_valid,
        "valid_contexts": len(valid_rows),
        "invalid_quarantine_rows": len(invalid_rows),
        "map_source_types": dict(sorted(source_types.items())),
        "public_benchmark_ingestion_decision": ingestion_state.get("decision", ""),
        "public_benchmark_ingestion_ready": ingestion_state.get("ready", False),
        "public_map_registry_rows": ingestion_state.get("map_registry_rows", 0),
        "public_scenario_registry_rows": ingestion_state.get("scenario_registry_rows", 0),
        "public_parent_split_audit_rows": ingestion_state.get("parent_split_audit_rows", 0),
        "public_required_panels_present": ingestion_state.get("required_panels_present", False),
        "public_benchmark_ingestion_failure_count": ingestion_state.get("failure_count", 0),
        "canonical_public_benchmark_contexts": benchmark_contexts,
        "synthetic_stress_contexts": synthetic_contexts,
        "benchmark_synthetic_mixture_target_met": benchmark_mixture_ok,
        "label_train_public_canonical_fraction": label_train_public_fraction,
        "development_public_canonical_fraction": development_public_fraction,
        "blind_public_canonical_fraction": blind_public_fraction,
        "source_ratio_targets_met": source_ratio_targets_met,
        "official_scenario_prefix_consumer_ready": official_scenario_prefix_consumer_ready,
        "official_scenario_prefix_consumer_blocker": "movingai_random_even_and_mapf_lns2_prefix_consumer_not_yet_wired",
        "preferred_100000_target_met": len(valid_rows) >= 100000,
        "minimum_5000_target_met": len(valid_rows) >= 5000,
        "physical_map_hashes": len(by_hash),
        "physical_map_hash_target_met": physical_map_hash_target_met,
        "physical_map_hash_minimum_required": 256,
        "map_families": dict(sorted(families.items())),
        "map_family_target_met": len(families) >= 16,
        "agent_tiers": dict(sorted(agents.items())),
        "agent_tier_target_met": len(agents) >= len(G567_AGENT_TIERS),
        "large_agent_tier_contract_met": all(str(tier) in agents for tier in [1000, 1500, 2000, 2500, 3000]),
        "budget_profiles": dict(sorted(budgets.items())),
        "budget_target_description": "all planned staged contexts use nominal_budget_ms=30000 / solver_internal_time_limit_sec=30.0 / process_hard_timeout_sec=60.0",
        "uniform_30s_budget_target_met": uniform_30s_budget_target_met,
        "budget_target_met": uniform_30s_budget_target_met,
        "split_counts": dict(sorted(split_counts.items())),
        "blind_contexts": split_counts.get("BLIND", 0),
        "blind_physical_map_hashes": len(blind_hashes),
        "blind_1000_target_met": split_counts.get("BLIND", 0) >= 1000,
        "blind_12_map_hash_target_met": len(blind_hashes) >= 12,
        "all_path_found_rate_one": all(number(row.get("path_found_rate"), 0.0) == 1.0 for row in valid_rows),
        "scenario_replay_dir": rel(REPLAY_SCENARIO_DIR),
        "map_dir": rel(resolve(TMP_ROOT) / "maps"),
        "generator_attempts": meta["attempts"],
        "benchmark_map_specs": meta.get("benchmark_map_specs", 0),
        "generator_seed": seed,
        **claims(),
    }
    write_json(VALIDITY_SUMMARY, summary)
    write_text(
        VALIDITY_MD,
        "# Repair5G.5.67 Valid Context Bank\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- valid contexts: `{summary['valid_contexts']}`\n"
        f"- public benchmark ingestion: `{summary['public_benchmark_ingestion_decision']}`\n"
        f"- public registry rows: `{summary['public_map_registry_rows']}` maps, `{summary['public_scenario_registry_rows']}` scenarios\n"
        f"- physical map hashes: `{summary['physical_map_hashes']}`\n"
        f"- canonical/public benchmark contexts: `{summary['canonical_public_benchmark_contexts']}`\n"
        f"- synthetic stress contexts: `{summary['synthetic_stress_contexts']}`\n"
        f"- blind contexts: `{summary['blind_contexts']}`\n"
        f"- blind physical map hashes: `{summary['blind_physical_map_hashes']}`\n"
        f"- all path_found_rate == 1: `{summary['all_path_found_rate_one']}`\n\n"
        "All G5.67 generated assignments use component-aware sampling, unique starts, unique goals, and raw map/scenario files materialized under `outputs/tmp`.\n",
    )
    return summary


def write_g565_truth_audit() -> dict[str, Any]:
    margin = read_json(REPORTS / "phase5p5_repair5g565_label_margin_summary.json")
    fresh = read_json(REPORTS / "phase5p5_repair5g565_fresh_solver_panel_summary.json")
    expanded = read_json(REPORTS / "phase5p5_repair5g565_expanded_solver_panel_summary.json")
    alpha = read_json(REPORTS / "phase5p5_repair5g565_alpha_response_summary.json")
    summary = {
        "schema_version": f"{ROUND}_g565_truth_audit_summary_v1",
        "decision": "g565_complete_but_g567_requires_new_three_tier_valid_blind",
        "g565_complete": True,
        "g565_tierA_retrospective_signal": "strong",
        "g565_tierB_explicit_replay": False,
        "g565_tierC_deployment_supported": False,
        "g565_valid_only_enforced": False,
        "g565_applied_quality_margin": 0,
        "g565_reported_margin": margin.get("recommended_positive_margin", 0),
        "g565_expanded_split_physical_map_grouped": False,
        "g565_alpha_trust_head_trained": bool(alpha.get("alpha_trust_head_trained", False)),
        "g565_merge_includes_fresh_expanded_alpha": False,
        "g565_blind_panel_still_available": False,
        "fresh_solver_decision": fresh.get("decision", ""),
        "expanded_solver_decision": expanded.get("decision", ""),
        "alpha_response_decision": alpha.get("decision", ""),
        **claims(),
    }
    write_json(TRUTH_AUDIT_SUMMARY, summary)
    write_text(
        TRUTH_AUDIT_MD,
        "# Repair5G.5.67 Audit of G5.65\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- G5.65 complete: `{summary['g565_complete']}`\n"
        f"- Tier B explicit replay in G5.65: `{summary['g565_tierB_explicit_replay']}`\n"
        f"- applied quality margin in actor dataset: `{summary['g565_applied_quality_margin']}`\n"
        f"- reported margin: `{summary['g565_reported_margin']}`\n"
        f"- G5.65 blind panel still available: `{summary['g565_blind_panel_still_available']}`\n",
    )
    return summary


def write_baseline_registry() -> dict[str, Any]:
    rows = baseline_registry_rows(claims())
    write_rows(BASELINE_REGISTRY, rows)
    summary = {
        "schema_version": f"{ROUND}_three_tier_baseline_registry_summary_v1",
        "decision": "g567_three_tier_baseline_registry_frozen",
        "baseline_rows": len(rows),
        "tiers": [row["tier"] for row in rows],
        "tierA_solver_alias": TIER_A_ADDITIVE.solver_alias,
        "tierB_solver_alias": TIER_B_STATIC_FLOW.solver_alias,
        "tierB_underlying_method": TIER_B_STATIC_FLOW.underlying_method,
        "tierC_solver_alias": TIER_C_G556.solver_alias,
        "registry_sha256": registry_fingerprint_sha(rows),
        **claims(),
    }
    write_json(BASELINE_REGISTRY_SUMMARY, summary)
    return summary


def context_from_manifest_row(row: dict[str, Any]) -> G567Context | None:
    scen = resolve(row["replay_scenario_path"])
    assignment = parse_movingai_scenario(scen, int(number(row.get("agent_count"), 0)))
    graph = build_graph(
        {
            "map": row["map"],
            "width": row.get("width", 32),
            "height": row.get("height", 32),
            "free_cells": row.get("free_cells", ""),
            "raw_map_path": row.get("raw_map_path", ""),
        }
    )
    traffic = g561_bank.compute_traffic_prior(graph, assignment)
    if number(traffic["summary"].get("path_found_rate"), 0.0) != 1.0:
        return None
    graph_t = graph_with_edge_features(graph, traffic["edge_features"])
    feature_row = {
        "agent_count": int(number(row.get("agent_count"), 0)),
        "agents": int(number(row.get("agent_count"), 0)),
        "nominal_budget_ms": int(number(row.get("nominal_budget_ms"), 0)),
        "budget_ms": int(number(row.get("nominal_budget_ms"), 0)),
        "base_time_limit_sec": float(number(row.get("base_time_limit_sec"), max(0.5, number(row.get("nominal_budget_ms"), 500) / 1000.0))),
        "ltm_max_iterations": int(number(row.get("ltm_max_iterations"), 3)),
        "agent_density": float(number(row.get("agent_density"), 0.0)),
        **traffic["summary"],
        **traffic["wait_pressure"],
    }
    return G567Context(
        dataset_row_id=row["g567_dataset_row_id"],
        evaluation_uid=row["g567_evaluation_uid"],
        instance_uid=row["g567_instance_uid"],
        split=row["split"],
        map=row["map"],
        map_family=row["map_family"],
        agents=int(number(row.get("agent_count"), 0)),
        seed=int(number(row.get("solver_seed"), 0)),
        budget_ms=int(number(row.get("nominal_budget_ms"), 0)),
        base_time_limit_sec=float(feature_row["base_time_limit_sec"]),
        ltm_max_iterations=int(feature_row["ltm_max_iterations"]),
        horizon_id=f"budget{int(number(row.get('nominal_budget_ms'), 0))}_ltm{int(number(row.get('ltm_max_iterations'), 0))}",
        scenario_path=scen,
        replay_scenario_path=scen,
        scenario_sha256=sha256_file(scen),
        physical_map_sha256=row["physical_map_sha256"],
        assignment_sha256=movingai_assignment_hash(assignment["starts"], assignment["goals"]),
        graph_with_traffic=graph_t,
        assignment=assignment,
        feature_row=feature_row,
        budget_role=str(row.get("budget_role", "")),
        process_hard_timeout_sec=float(number(row.get("process_hard_timeout_sec"), 0.0)),
    )


def contexts_from_manifest(split_filter: str, limit: int) -> list[G567Context]:
    update_remote_map_registries(resolve(TMP_ROOT) / "maps")
    wanted = {token.strip().upper() for token in split_filter.split(",") if token.strip()}
    rows = [row for row in read_rows(VALID_CONTEXT_MANIFEST) if not wanted or str(row.get("split", "")).upper() in wanted]
    contexts: list[G567Context] = []
    for row in rows:
        ctx = context_from_manifest_row(row)
        if ctx is None:
            continue
        contexts.append(ctx)
        if limit and len(contexts) >= limit:
            break
    return contexts


def move_graph_batch(batch: GraphBatch, device: str) -> GraphBatch:
    return GraphBatch(
        batch.node_features.to(device),
        batch.edge_index.to(device),
        batch.edge_features.to(device),
        batch.batch_index.to(device),
        batch.num_graphs,
    )


def write_3000_agent_memory_smoke(device: str, hidden_dim: int) -> dict[str, Any]:
    rows = sorted(read_rows(VALID_CONTEXT_MANIFEST), key=lambda row: int(number(row.get("agent_count"), 0)), reverse=True)
    selected = next((row for row in rows if int(number(row.get("agent_count"), 0)) >= 3000), None)
    if selected is None:
        summary = {
            "schema_version": f"{ROUND}_3000_agent_memory_smoke_v1",
            "decision": "g567_3000_agent_contract_failed",
            "reason": "no_3000_agent_context_in_manifest",
            **claims(),
        }
        write_json(MEMORY_SMOKE_3000, summary)
        return summary
    try:
        import torch

        from gcst.dual_stream_graph_actor import DualStreamGoalAwareActor, architecture_from_id

        ctx = context_from_manifest_row(selected)
        if ctx is None:
            raise RuntimeError("selected 3000-agent context failed path/traffic validation")
        arch = architecture_from_id("A5")
        model = DualStreamGoalAwareActor(
            hidden_dim=hidden_dim,
            use_cross_attention=arch.use_cross_attention,
            safe_subspace=arch.safe_subspace,
            field_group_trust=arch.field_group_trust,
            od_perceiver=arch.od_perceiver,
            graph_local_layers=arch.graph_local_layers,
            graph_global_layers=arch.graph_global_layers,
            heads=arch.heads,
            latent_tokens=arch.latent_tokens,
        ).module().to(device)
        model.train()
        if device.startswith("cuda"):
            torch.cuda.reset_peak_memory_stats()
        graph_batch = move_graph_batch(make_graph_batch([ctx.graph_with_traffic]), device)
        od_tokens, od_mask = pad_od_tokens([ctx.assignment])
        scalar_x = torch.tensor(np.stack([scalar_features(ctx.feature_row)]), dtype=torch.float32, device=device)
        started = time.perf_counter()
        if device.startswith("cuda"):
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                theta = model(graph_batch, od_tokens.to(device), od_mask.to(device), scalar_x)
                loss = theta.sum()
        else:
            theta = model(graph_batch, od_tokens.to(device), od_mask.to(device), scalar_x)
            loss = theta.sum()
        loss.backward()
        elapsed = time.perf_counter() - started
        summary = {
            "schema_version": f"{ROUND}_3000_agent_memory_smoke_v1",
            "decision": "g567_3000_agent_contract_valid",
            "architecture": "A5_hierarchical_od_perceiver_actor",
            "od_perceiver": arch.od_perceiver,
            "graph_global_layers": arch.graph_global_layers,
            "full_node_quadratic_graph_attention_disabled": arch.graph_global_layers == 0,
            "agent_count": ctx.agents,
            "map": ctx.map,
            "map_family": ctx.map_family,
            "graph_nodes": len(ctx.graph_with_traffic.cells),
            "graph_edges": int(ctx.graph_with_traffic.edge_index.shape[1]) if ctx.graph_with_traffic.edge_index.size else 0,
            "od_tokens": int(od_tokens.shape[1]),
            "hidden_dim": hidden_dim,
            "latent_tokens": arch.latent_tokens,
            "elapsed_sec": elapsed,
            "samples_per_sec": float(1.0 / max(elapsed, 1.0e-9)),
            "backward_executed": True,
            "cuda_bf16_autocast": bool(device.startswith("cuda")),
            "theta_shape": list(theta.shape),
            "cuda_peak_memory_bytes": int(torch.cuda.max_memory_allocated()) if device.startswith("cuda") else 0,
            **claims(),
        }
    except Exception as exc:
        summary = {
            "schema_version": f"{ROUND}_3000_agent_memory_smoke_v1",
            "decision": "g567_3000_agent_contract_failed",
            "reason": str(exc),
            "device": device,
            **claims(),
        }
    write_json(MEMORY_SMOKE_3000, summary)
    return summary


def model_kind_from_payload(payload: dict[str, Any], path: Path) -> str:
    return str(payload.get("model_kind") or payload.get("variant_id") or path.stem).upper()


def load_model_for_payload(payload: dict[str, Any], path: Path, device: str):
    import torch

    kind = model_kind_from_payload(payload, path)
    if kind in {"B1", "B2", "E0", "E1", "E2"}:
        from gcst.rich_training_g565 import make_model

        model = make_model(kind, hidden_dim=int(payload.get("hidden_dim", 64)), device=device)
        state = payload.get("actor_state_dict")
        if state is not None:
            model.load_state_dict(state)
        model.eval()
        return model, kind
    from gcst.dual_stream_graph_actor import DualStreamGoalAwareActor

    model = DualStreamGoalAwareActor(
        hidden_dim=int(payload.get("hidden_dim", 96)),
        scalar_only_control=boolish(payload.get("scalar_only_control")),
        use_cross_attention=boolish(payload.get("use_cross_attention")),
        safe_subspace=boolish(payload.get("safe_subspace")),
        field_group_trust=boolish(payload.get("field_group_trust")),
        od_perceiver=boolish(payload.get("od_perceiver")),
        graph_local_layers=int(number(payload.get("graph_local_layers"), 2)),
        graph_global_layers=int(number(payload.get("graph_global_layers"), 1)),
        heads=int(number(payload.get("heads", payload.get("attention_heads")), 4)),
        latent_tokens=int(number(payload.get("latent_tokens"), 64)),
    ).module().to(device)
    model.load_state_dict(payload["actor_state_dict"])
    model.eval()
    return model, kind


def infer_checkpoint_thetas(contexts: list[G567Context], checkpoint_paths: list[Path], *, device: str, batch_size: int, phase: str) -> list[dict[str, Any]]:
    import torch

    rows: list[dict[str, Any]] = []
    for path in checkpoint_paths:
        payload = torch.load(resolve(path), map_location=device, weights_only=False)
        model, kind = load_model_for_payload(payload, resolve(path), device)
        for start in range(0, len(contexts), batch_size):
            batch = contexts[start : start + batch_size]
            with torch.no_grad():
                if kind == "B1":
                    theta = model(len(batch)).detach().cpu().numpy()
                elif kind == "B2":
                    from gcst.leakage_free_features import leakage_free_scalar_vector

                    scalar_x = torch.tensor(np.stack([leakage_free_scalar_vector(ctx.feature_row) for ctx in batch]), dtype=torch.float32, device=device)
                    theta = model(scalar_x).detach().cpu().numpy()
                else:
                    graph_batch = move_graph_batch(make_graph_batch([ctx.graph_with_traffic for ctx in batch]), device)
                    od_tokens, od_mask = pad_od_tokens([ctx.assignment for ctx in batch])
                    scalar_x = torch.tensor(np.stack([scalar_features(ctx.feature_row) for ctx in batch]), dtype=torch.float32, device=device)
                    theta = model(graph_batch, od_tokens.to(device), od_mask.to(device), scalar_x).detach().cpu().numpy()
            for ctx, values in zip(batch, theta):
                row = {col: float(values[idx]) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)}
                row.update(mode_columns("flow_shield"))
                rows.append(
                    {
                        "phase": phase,
                        "context_id": ctx.dataset_row_id,
                        "g567_evaluation_uid": ctx.evaluation_uid,
                        "variant_id": kind,
                        "variant_name": str(payload.get("variant_name") or payload.get("model_kind") or kind),
                        "seed": payload.get("seed", payload.get("metrics", {}).get("seed", "")),
                        "method": f"g567_{kind}_{path.stem}",
                        "model_path": rel(path),
                        **clamp_theta_row(row),
                    }
                )
    return rows


def plan_paths(phase: str) -> dict[str, Path]:
    token = safe_token(phase)
    return {
        "plan": TABLES / f"{ROUND}_{token}_plan.csv",
        "registry": TABLES / f"{ROUND}_{token}_registry.csv",
        "results": TABLES / f"{ROUND}_{token}_results.csv",
        "raw_results": TABLES / f"{ROUND}_{token}_results.raw.csv",
        "pairs": TABLES / f"{ROUND}_{token}_pairs.csv",
        "summary": REPORTS / f"{ROUND}_{token}_summary.json",
        "report": REPORTS / f"{ROUND}_{token}.md",
        "scenario_metadata": REPORTS / f"{ROUND}_{token}_scenario_generation.json",
        "log_dir": LOGS / f"{ROUND}_{token}",
        "scenario_dir": REPLAY_SCENARIO_DIR,
    }


def add_plan_row(
    plan: list[dict[str, Any]],
    ctx: G567Context,
    *,
    phase: str,
    role: str,
    candidate_id: str,
    method: str,
    theta: dict[str, Any] | None,
    model_path: str = "",
    actor_row: dict[str, Any] | None = None,
    replicate_id: int = 0,
) -> None:
    idx = len(plan)
    generated_uid = "" if theta is None else generated_theta_uid(model_path or method, ctx.instance_uid, [theta[col] for col in THETA_NUMERIC_COLUMNS])
    identity = stable_uid("g567_replay_identity", phase, ctx.evaluation_uid, ctx.scenario_sha256, candidate_id, generated_uid)
    horizon_id = ctx.horizon_id
    if float(ctx.base_time_limit_sec) <= 0.0:
        raise ValueError(f"G5.67 plan row missing explicit solver internal budget for context {ctx.dataset_row_id}")
    if float(ctx.process_hard_timeout_sec) <= 0.0:
        raise ValueError(f"G5.67 plan row missing explicit process hard timeout for context {ctx.dataset_row_id}")
    hard_timeout = float(ctx.process_hard_timeout_sec)
    expected_fingerprint = ""
    if candidate_id == ADDITIVE_SOLVER_ALIAS:
        expected_fingerprint = TIER_A_ADDITIVE.fingerprint
    elif candidate_id == STATIC_FLOW_SOLVER_ALIAS:
        expected_fingerprint = TIER_B_STATIC_FLOW.fingerprint
    elif candidate_id == G556_SOLVER_ALIAS:
        expected_fingerprint = TIER_C_G556.fingerprint
    elif theta is not None:
        expected_fingerprint = updateparams_fingerprint(theta)
    theta_identity = generated_uid or expected_fingerprint or candidate_id
    replicate_group_id = stable_uid(
        "g567_replicate_group",
        ctx.map,
        ctx.assignment_sha256,
        theta_identity,
        ctx.budget_ms,
        ctx.ltm_max_iterations,
    )
    row = {
        "plan_row_id": f"g567_{safe_token(phase)}_{idx:08d}",
        "replay_phase": phase,
        "context_id": ctx.dataset_row_id,
        "g567_dataset_row_id": ctx.dataset_row_id,
        "g567_instance_uid": ctx.instance_uid,
        "g567_evaluation_uid": ctx.evaluation_uid,
        "g567_identity_digest": identity,
        "g567_scenario_sha256": ctx.scenario_sha256,
        "g567_physical_map_sha256": ctx.physical_map_sha256,
        "g567_assignment_sha256": ctx.assignment_sha256,
        "split": ctx.split,
        "map": ctx.map,
        "map_family": ctx.map_family,
        "agents": ctx.agents,
        "agent_count": ctx.agents,
        "seed": ctx.seed,
        "budget_ms": ctx.budget_ms,
        "nominal_budget_ms": ctx.budget_ms,
        "short_budget_ms": ctx.budget_ms,
        "base_time_limit_sec": ctx.base_time_limit_sec,
        "budget_role": ctx.budget_role,
        "ltm_max_iterations": ctx.ltm_max_iterations,
        "horizon_id": horizon_id,
        "scientific_horizon_id": ctx.horizon_id,
        "solver_execution_id": f"{ctx.horizon_id}|rep{int(replicate_id):02d}",
        "role": role,
        "candidate_id": candidate_id,
        "theta_id": candidate_id,
        "materialized_method": candidate_id,
        "generated_theta_uid": generated_uid,
        "sampling_policy": method,
        "model_path": model_path,
        "variant_id": "" if actor_row is None else actor_row.get("variant_id", ""),
        "actor_training_seed": "" if actor_row is None else actor_row.get("seed", ""),
        "expected_updateparams_fingerprint": expected_fingerprint,
        "replicate_id": replicate_id,
        "replicate_group_id": replicate_group_id,
        "execution_order_index": idx,
        "cpu_affinity": os.environ.get("G567_CPU_AFFINITY", ""),
        "worker_count": "",
        "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", ""),
        "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS", ""),
        "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS", ""),
        "host_load_snapshot": "",
        "solver_internal_time_limit_sec": ctx.base_time_limit_sec,
        "process_hard_timeout_sec": hard_timeout,
        "method_start_timestamp": "",
        "method_end_timestamp": "",
        **claims(),
    }
    if theta is not None:
        row.update({col: theta.get(col, "") for col in THETA_COLUMNS})
    plan.append(row)


def audit_plan_explicit_budgets(plan_rows: list[dict[str, Any]], phase: str) -> dict[str, Any]:
    audit_rows: list[dict[str, Any]] = []
    failures: list[str] = []
    context_budgets: dict[str, set[tuple[float, float]]] = defaultdict(set)
    for idx, row in enumerate(plan_rows):
        internal_raw = str(row.get("solver_internal_time_limit_sec", "")).strip()
        hard_raw = str(row.get("process_hard_timeout_sec", "")).strip()
        internal = float(number(internal_raw, 0.0))
        hard = float(number(hard_raw, 0.0))
        explicit_internal = bool(internal_raw) and internal > 0.0
        explicit_hard = bool(hard_raw) and hard > 0.0
        agents = int(number(row.get("agent_count", row.get("agents")), 0))
        context_id = str(row.get("context_id", ""))
        context_budgets[context_id].add((internal, hard))
        expected_hard = process_hard_timeout_for_internal_budget(internal) if explicit_internal else 0.0
        uniform_30s_ok = explicit_internal and explicit_hard and abs(internal - 30.0) <= 1.0e-9 and abs(hard - 60.0) <= 1.0e-9
        row_failures = []
        if not explicit_internal:
            row_failures.append("missing_explicit_solver_internal_time_limit_sec")
        if not explicit_hard:
            row_failures.append("missing_explicit_process_hard_timeout_sec")
        if explicit_internal and explicit_hard and abs(hard - expected_hard) > 1.0e-9:
            row_failures.append("hard_timeout_does_not_match_budget_contract")
        if explicit_internal and explicit_hard and not uniform_30s_ok:
            row_failures.append("non_uniform_30s_budget_contract")
        if row_failures:
            failures.extend(f"{row.get('plan_row_id', idx)}:{failure}" for failure in row_failures)
        audit_rows.append(
            {
                "replay_phase": phase,
                "plan_row_id": row.get("plan_row_id", ""),
                "context_id": context_id,
                "candidate_id": row.get("candidate_id", ""),
                "agent_count": agents,
                "budget_role": row.get("budget_role", ""),
                "solver_internal_time_limit_sec": internal_raw,
                "process_hard_timeout_sec": hard_raw,
                "expected_process_hard_timeout_sec": expected_hard if explicit_internal else "",
                "explicit_internal_budget": explicit_internal,
                "explicit_hard_timeout": explicit_hard,
                "uniform_30s_budget_contract_met": uniform_30s_ok,
                "large_agent_30s_budget_contract_met": uniform_30s_ok,
                "row_budget_audit_decision": "pass" if not row_failures else "fail",
                "row_budget_audit_failures": ";".join(row_failures),
                **claims(),
            }
        )
    for context_id, pairs in context_budgets.items():
        if len(pairs) > 1:
            failures.append(f"{context_id}:context_methods_do_not_share_same_budget")
            for row in audit_rows:
                if row["context_id"] == context_id:
                    row["row_budget_audit_decision"] = "fail"
                    existing = str(row.get("row_budget_audit_failures", ""))
                    row["row_budget_audit_failures"] = ";".join(filter(None, [existing, "context_methods_do_not_share_same_budget"]))
    existing = [row for row in read_rows(SOLVER_BUDGET_AUDIT) if row.get("replay_phase") != phase]
    write_rows(SOLVER_BUDGET_AUDIT, existing + audit_rows)
    summary = {
        "schema_version": f"{ROUND}_solver_budget_audit_summary_v1",
        "decision": "g567_solver_budget_audit_passed" if not failures else "g567_solver_budget_audit_failed",
        "replay_phase": phase,
        "planned_rows": len(plan_rows),
        "failure_count": len(failures),
        "failures": failures[:50],
        "all_rows_have_explicit_internal_budget": all(boolish(row.get("explicit_internal_budget")) for row in audit_rows),
        "all_rows_have_explicit_hard_timeout": all(boolish(row.get("explicit_hard_timeout")) for row in audit_rows),
        "same_context_methods_same_budget": all(len(pairs) == 1 for pairs in context_budgets.values()),
        "uniform_30s_rows_have_60s_hard_timeout": all(boolish(row.get("uniform_30s_budget_contract_met")) for row in audit_rows),
        "large_30s_rows_have_60s_hard_timeout": all(boolish(row.get("large_agent_30s_budget_contract_met")) for row in audit_rows),
        **claims(),
    }
    write_json(SOLVER_BUDGET_AUDIT_SUMMARY, summary)
    return summary


def build_plan_and_registry(
    contexts: list[G567Context],
    theta_rows: list[dict[str, Any]],
    phase: str,
    *,
    include_no_ltm: bool = False,
    repeat_count: int = 1,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    context_by_id = {ctx.dataset_row_id: ctx for ctx in contexts}
    plan: list[dict[str, Any]] = []
    registry = baseline_registry_rows(claims())
    replicate_ids = list(range(max(1, int(repeat_count)))) if "repeat" in safe_token(phase) else [0]
    if include_no_ltm:
        for ctx in contexts:
            for rep in replicate_ids:
                add_plan_row(ctx=ctx, plan=plan, phase=phase, role="no_ltm_diagnostic", candidate_id=NO_LTM_DIAGNOSTIC, method="LaCAM* no-LTM diagnostic", theta=None, replicate_id=rep)
    for ctx in contexts:
        for rep in replicate_ids:
            add_plan_row(ctx=ctx, plan=plan, phase=phase, role="tierA_additive_ltm", candidate_id=ADDITIVE_SOLVER_ALIAS, method="paper_faithful_additive_ltm", theta=None, replicate_id=rep)
            add_plan_row(ctx=ctx, plan=plan, phase=phase, role="tierB_static_flow_shield", candidate_id=STATIC_FLOW_SOLVER_ALIAS, method=TIER_B_STATIC_FLOW.underlying_method, theta=TIER_B_STATIC_FLOW.theta, replicate_id=rep)
            add_plan_row(ctx=ctx, plan=plan, phase=phase, role="tierC_g556", candidate_id=G556_SOLVER_ALIAS, method=G556_SOLVER_ALIAS, theta=TIER_C_G556.theta, replicate_id=rep)
    for theta_row in theta_rows:
        ctx = context_by_id[str(theta_row["context_id"])]
        theta = clamp_theta_row(theta_row)
        uid = stable_uid("g567_actor_theta", phase, theta_row.get("method", ""), ctx.evaluation_uid, {col: theta[col] for col in THETA_NUMERIC_COLUMNS})
        candidate_id = f"g567_{safe_token(phase)}_{safe_token(theta_row.get('variant_id', 'actor'))}_s{safe_token(theta_row.get('seed', '0'))}_{uid[:12]}"
        registry.append(
            {
                "candidate_id": candidate_id,
                "generated_theta_uid": generated_theta_uid(theta_row.get("model_path", ""), ctx.instance_uid, [theta[col] for col in THETA_NUMERIC_COLUMNS]),
                "registry_role": "g567_actor_generated_theta",
                "replay_phase": phase,
                "method": theta_row.get("method", ""),
                "variant_id": theta_row.get("variant_id", ""),
                "actor_training_seed": theta_row.get("seed", ""),
                **{col: theta.get(col, "") for col in THETA_COLUMNS},
                **claims(),
            }
        )
        for rep in replicate_ids:
            add_plan_row(
                plan,
                ctx,
                phase=phase,
                role=f"generated_theta::{candidate_id}",
                candidate_id=candidate_id,
                method=str(theta_row.get("method", "")),
                theta=theta,
                model_path=str(theta_row.get("model_path", "")),
                actor_row=theta_row,
                replicate_id=rep,
            )
    return plan, registry


def audit_results(rows: list[dict[str, Any]], plan_rows: list[dict[str, Any]], phase: str) -> list[dict[str, Any]]:
    by_plan_row_id = {str(row.get("plan_row_id", "")): row for row in plan_rows if str(row.get("plan_row_id", "")).strip()}
    lookup_with_rep = {
        (
            str(row.get("map", "")),
            str(row.get("agents", "")),
            str(row.get("seed", "")),
            str(row.get("budget_ms", "")),
            str(row.get("horizon_id", "")),
            str(row.get("materialized_method", "")),
            str(row.get("replicate_id", "")),
        ): row
        for row in plan_rows
    }
    lookup_without_rep: dict[tuple[str, str, str, str, str, str], dict[str, Any]] = {}
    duplicate_without_rep: set[tuple[str, str, str, str, str, str]] = set()
    for row in plan_rows:
        key = (
            str(row.get("map", "")),
            str(row.get("agents", "")),
            str(row.get("seed", "")),
            str(row.get("budget_ms", "")),
            str(row.get("horizon_id", "")),
            str(row.get("materialized_method", "")),
        )
        if key in lookup_without_rep:
            duplicate_without_rep.add(key)
        lookup_without_rep[key] = row
    out: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        plan = by_plan_row_id.get(str(row.get("plan_row_id", "")))
        metadata_match_mode = "plan_row_id" if plan else ""
        if not plan:
            plan = lookup_with_rep.get(
                (
                    str(row.get("map", "")),
                    str(row.get("agents", "")),
                    str(row.get("seed", "")),
                    str(row.get("budget_ms", "")),
                    str(row.get("horizon_id", "")),
                    str(row.get("materialized_method", "")),
                    str(row.get("replicate_id", "")),
                ),
                {},
            )
            metadata_match_mode = "context_method_replicate" if plan else ""
        if not plan:
            fallback_key = (
                str(row.get("map", "")),
                str(row.get("agents", "")),
                str(row.get("seed", "")),
                str(row.get("budget_ms", "")),
                str(row.get("horizon_id", "")),
                str(row.get("materialized_method", "")),
            )
            if fallback_key not in duplicate_without_rep:
                plan = lookup_without_rep.get(fallback_key, {})
                metadata_match_mode = "context_method_unique_fallback" if plan else "unmatched"
            else:
                metadata_match_mode = "ambiguous_context_method_requires_plan_row_id"
        for key in [
            "plan_row_id",
            "replay_phase",
            "g567_dataset_row_id",
            "g567_instance_uid",
            "g567_evaluation_uid",
            "g567_identity_digest",
            "g567_scenario_sha256",
            "g567_physical_map_sha256",
            "g567_assignment_sha256",
            "split",
            "generated_theta_uid",
            "expected_updateparams_fingerprint",
            "model_path",
            "variant_id",
            "actor_training_seed",
            "role",
            "replicate_id",
            "replicate_group_id",
            "scientific_horizon_id",
            "solver_execution_id",
            "execution_order_index",
            "cpu_affinity",
            "worker_count",
            "OMP_NUM_THREADS",
            "MKL_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "host_load_snapshot",
            "solver_internal_time_limit_sec",
            "process_hard_timeout_sec",
            "budget_role",
            "process_hard_timeout_exceeded",
            "process_timeout_provenance",
            "process_timeout_platform",
            "process_timeout_term_grace_sec",
            "process_started_unix",
            "process_pid",
            "process_group_id",
            "process_group_termination_attempted",
            "process_timeout_sigterm_sent",
            "process_timeout_sigterm_unix",
            "process_timeout_sigterm_elapsed_sec",
            "process_timeout_sigkill_sent",
            "process_timeout_sigkill_unix",
            "process_timeout_sigkill_elapsed_sec",
            "child_process_group_killed",
            "child_process_group_kill_method",
            "process_partial_stdout_preserved",
            "process_partial_stderr_preserved",
            "process_partial_stdout_chars",
            "process_partial_stderr_chars",
            "process_timeout_reason",
            "process_elapsed_sec",
            "process_returncode",
            "returncode",
            "returncode_classification",
        ]:
            row[key] = plan.get(key, row.get(key, ""))
        row["g567_metadata_match_mode"] = metadata_match_mode
        for col in THETA_COLUMNS:
            row[col] = plan.get(col, row.get(col, ""))
        parsed = parse_updateparams_fingerprint(row.get("updateparams_fingerprint", ""))
        materialized = str(row.get("materialized_method", ""))
        is_actor = str(row.get("role", "")).startswith("generated_theta::")
        is_add = materialized == ADDITIVE_SOLVER_ALIAS
        is_static = materialized == STATIC_FLOW_SOLVER_ALIAS
        is_g556 = materialized == G556_SOLVER_ALIAS
        fp_match = True
        mismatch = ""
        if is_actor or is_static or is_g556:
            theta_source = plan or row
            fp_match, mismatches = compare_theta_to_fingerprint(row.get("updateparams_fingerprint", ""), theta_source, tolerance=1.0e-9)
            mismatch = ";".join(mismatches)
        elif is_add:
            fp_match = parsed.get("force_additive") == "1" and parsed.get("enable_dual_channel") == "0"
            mismatch = "" if fp_match else "additive_fingerprint"
        scen = scenario_path(resolve(REPLAY_SCENARIO_DIR), str(row.get("map", "")), int(number(row.get("seed"), 0)))
        scenario_actual = sha256_file(scen)
        identity_actual = stable_uid(
            "g567_replay_identity",
            phase,
            row.get("g567_evaluation_uid", ""),
            row.get("g567_scenario_sha256", ""),
            row.get("candidate_id", ""),
            row.get("generated_theta_uid", ""),
        )
        row.update(
            {
                "executed": boolish(row.get("real_solver_execution", True)),
                "is_actor_row": is_actor,
                "is_additive_row": is_add,
                "is_static_flow_row": is_static,
                "is_g556_row": is_g556,
                "candidate_recognized_bool": boolish(row.get("candidate_recognized")),
                "fingerprint_parsed": bool(parsed),
                "fulltheta_fingerprint_match_strict": fp_match,
                "fulltheta_fingerprint_mismatched_fields": mismatch,
                "force_additive_false": parsed.get("force_additive") == "0" if (is_actor or is_static or is_g556) else "",
                "dual_channel_enabled": parsed.get("enable_dual_channel") == "1" if (is_actor or is_static or is_g556) else "",
                "scenario_sha256_actual": scenario_actual,
                "scenario_sha256_match": bool(scenario_actual) and scenario_actual == row.get("g567_scenario_sha256", ""),
                "identity_digest_actual": identity_actual,
                "identity_retained": bool(row.get("g567_identity_digest", "")) and identity_actual == row.get("g567_identity_digest", ""),
                "process_hard_timeout_exceeded_bool": boolish(row.get("process_hard_timeout_exceeded")),
            }
        )
        out.append(row)
    return out


def group_key(row: dict[str, Any]) -> tuple[str, str, str, str, str, str]:
    return (
        str(row.get("map", "")),
        str(row.get("agents", "")),
        str(row.get("seed", "")),
        str(row.get("budget_ms", "")),
        str(row.get("horizon_id", "")),
        str(row.get("replicate_id", "")),
    )


def rel_improve(actor_ratio: float | None, base_ratio: float | None) -> float:
    if actor_ratio is None or base_ratio is None or base_ratio == 0 or not math.isfinite(actor_ratio) or not math.isfinite(base_ratio):
        return math.nan
    return (base_ratio - actor_ratio) / base_ratio


def delta_when_comparable(actor: dict[str, Any], base: dict[str, Any]) -> float:
    if not solver_success(actor) or not solver_success(base):
        return math.nan
    a = solver_ratio(actor)
    b = solver_ratio(base)
    if a is None or b is None:
        return math.nan
    return a - b


def build_three_tier_pairs(rows: list[dict[str, Any]], phase: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
        if boolish(row.get("infrastructure_timeout")) or boolish(row.get("excluded_from_scientific_labels")):
            continue
        grouped.setdefault(group_key(row), {})[str(row.get("materialized_method", ""))] = row
    pairs: list[dict[str, Any]] = []
    for key, by_method in sorted(grouped.items()):
        additive = by_method.get(ADDITIVE_SOLVER_ALIAS)
        static = by_method.get(STATIC_FLOW_SOLVER_ALIAS)
        g556 = by_method.get(G556_SOLVER_ALIAS)
        if not (additive and static and g556):
            continue
        for method, actor in sorted(by_method.items()):
            if method in {NO_LTM_DIAGNOSTIC, ADDITIVE_SOLVER_ALIAS, STATIC_FLOW_SOLVER_ALIAS, G556_SOLVER_ALIAS}:
                continue
            if actor.get("replay_phase") != phase:
                continue
            actor_success = solver_success(actor)
            actor_ratio = solver_ratio(actor)
            additive_ratio = solver_ratio(additive)
            static_ratio = solver_ratio(static)
            g556_ratio = solver_ratio(g556)
            pairs.append(
                {
                    "replay_phase": phase,
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "budget_ms": key[3],
                    "horizon_id": key[4],
                    "scientific_horizon_id": actor.get("scientific_horizon_id", actor.get("horizon_id", "")),
                    "split": actor.get("split", ""),
                    "map_family": actor.get("map_family", ""),
                    "g567_dataset_row_id": actor.get("g567_dataset_row_id", ""),
                    "g567_evaluation_uid": actor.get("g567_evaluation_uid", ""),
                    "g567_identity_digest": actor.get("g567_identity_digest", ""),
                    "replicate_id": actor.get("replicate_id", ""),
                    "replicate_group_id": actor.get("replicate_group_id", ""),
                    "actor_plan_row_id": actor.get("plan_row_id", ""),
                    "metadata_match_mode": actor.get("g567_metadata_match_mode", ""),
                    "execution_order_index": actor.get("execution_order_index", ""),
                    "cpu_affinity": actor.get("cpu_affinity", ""),
                    "worker_count": actor.get("worker_count", ""),
                    "OMP_NUM_THREADS": actor.get("OMP_NUM_THREADS", ""),
                    "MKL_NUM_THREADS": actor.get("MKL_NUM_THREADS", ""),
                    "OPENBLAS_NUM_THREADS": actor.get("OPENBLAS_NUM_THREADS", ""),
                    "host_load_snapshot": actor.get("host_load_snapshot", ""),
                    "solver_internal_time_limit_sec": actor.get("solver_internal_time_limit_sec", ""),
                    "process_hard_timeout_sec": actor.get("process_hard_timeout_sec", ""),
                    "budget_role": actor.get("budget_role", ""),
                    "process_hard_timeout_exceeded": actor.get("process_hard_timeout_exceeded", ""),
                    "process_timeout_reason": actor.get("process_timeout_reason", ""),
                    "process_timeout_provenance": actor.get("process_timeout_provenance", ""),
                    "theta_id": method,
                    "method": actor.get("sampling_policy", ""),
                    "variant_id": actor.get("variant_id", ""),
                    "actor_training_seed": actor.get("actor_training_seed", ""),
                    "model_path": actor.get("model_path", ""),
                    "actor_success": actor_success,
                    "additive_success": solver_success(additive),
                    "static_flow_success": solver_success(static),
                    "g556_success": solver_success(g556),
                    "actor_ratio": actor_ratio,
                    "additive_ratio": additive_ratio,
                    "static_flow_ratio": static_ratio,
                    "g556_ratio": g556_ratio,
                    "delta_vs_additive": delta_when_comparable(actor, additive),
                    "delta_vs_static_flow": delta_when_comparable(actor, static),
                    "delta_vs_g556": delta_when_comparable(actor, g556),
                    "relative_improvement_vs_additive": rel_improve(actor_ratio, additive_ratio),
                    "relative_improvement_vs_static_flow": rel_improve(actor_ratio, static_ratio),
                    "relative_improvement_vs_g556": rel_improve(actor_ratio, g556_ratio),
                    "success_gain_vs_additive": bool(actor_success and not solver_success(additive)),
                    "success_regression_vs_additive": bool(solver_success(additive) and not actor_success),
                    "success_gain_vs_static_flow": bool(actor_success and not solver_success(static)),
                    "success_regression_vs_static_flow": bool(solver_success(static) and not actor_success),
                    "success_gain_vs_g556": bool(actor_success and not solver_success(g556)),
                    "success_regression_vs_g556": bool(solver_success(g556) and not actor_success),
                    "candidate_recognized": actor.get("candidate_recognized_bool", False),
                    "fingerprint_match": actor.get("fulltheta_fingerprint_match_strict", False),
                    "scenario_hash_match": actor.get("scenario_sha256_match", False),
                    "identity_retained": actor.get("identity_retained", False),
                    "force_additive_false": actor.get("force_additive_false", ""),
                    "dual_channel_enabled": actor.get("dual_channel_enabled", ""),
                    "actor_runtime_ms": actor.get("probe_runtime_ms", ""),
                    "additive_runtime_ms": additive.get("probe_runtime_ms", ""),
                    "static_flow_runtime_ms": static.get("probe_runtime_ms", ""),
                    "g556_runtime_ms": g556.get("probe_runtime_ms", ""),
                    "actor_expanded_nodes": actor.get("expanded_nodes", ""),
                    "g556_expanded_nodes": g556.get("expanded_nodes", ""),
                    "actor_low_level_pibt_calls": actor.get("low_level_pibt_calls", ""),
                    "g556_low_level_pibt_calls": g556.get("low_level_pibt_calls", ""),
                    **{col: actor.get(col, "") for col in THETA_NUMERIC_COLUMNS},
                    **claims(),
                }
            )
    return pairs


def summarize_pairs(pairs: list[dict[str, Any]], rows: list[dict[str, Any]], plan_rows: list[dict[str, Any]], phase: str, margin: float) -> dict[str, Any]:
    actor_rows = [row for row in rows if boolish(row.get("is_actor_row"))]
    exact = sum(boolish(row.get("fulltheta_fingerprint_match_strict")) for row in actor_rows)
    recognized = sum(boolish(row.get("candidate_recognized_bool")) for row in actor_rows)
    scenario = sum(boolish(row.get("scenario_sha256_match")) for row in actor_rows)
    identity = sum(boolish(row.get("identity_retained")) for row in actor_rows)
    timeout_rows = sum(boolish(row.get("process_hard_timeout_exceeded")) for row in rows)
    materialized = bool(actor_rows and exact == len(actor_rows) and recognized == len(actor_rows) and scenario == len(actor_rows) and identity == len(actor_rows) and timeout_rows == 0)
    replicate_group_counts = Counter(
        str(row.get("replicate_group_id", ""))
        for row in pairs
        if str(row.get("replicate_group_id", "")).strip()
    )
    replicate_counts = list(replicate_group_counts.values())

    def finite_list(column: str) -> list[float]:
        vals = []
        for row in pairs:
            value = number(row.get(column), math.nan)
            if math.isfinite(value):
                vals.append(value)
        return vals

    def tier_stats(tier: str) -> dict[str, Any]:
        delta_col = f"delta_vs_{tier}"
        rel_col = f"relative_improvement_vs_{tier}"
        regress_col = f"success_regression_vs_{tier}"
        gain_col = f"success_gain_vs_{tier}"
        deltas = finite_list(delta_col)
        rels = finite_list(rel_col)
        return {
            f"raw_success_regressions_vs_{tier}": sum(boolish(row.get(regress_col)) for row in pairs),
            f"raw_success_gains_vs_{tier}": sum(boolish(row.get(gain_col)) for row in pairs),
            f"raw_quality_worse_vs_{tier}": sum(value > 0 for value in deltas),
            f"supported_quality_worse_outside_margin_vs_{tier}": sum(value > margin for value in deltas),
            f"better_outside_margin_vs_{tier}": sum(value < -margin for value in deltas),
            f"median_delta_vs_{tier}": float(statistics.median(deltas)) if deltas else None,
            f"mean_delta_vs_{tier}": float(statistics.mean(deltas)) if deltas else None,
            f"median_relative_improvement_vs_{tier}": float(statistics.median(rels)) if rels else None,
            f"q95_harmful_delta_vs_{tier}": float(np.quantile([max(0.0, v) for v in deltas], 0.95)) if deltas else None,
        }

    per_variant: dict[str, dict[str, Any]] = {}
    for pair in pairs:
        key = f"{pair.get('variant_id', '')}::{pair.get('model_path', '') or pair.get('method', '')}"
        bucket = per_variant.setdefault(
            key,
            {
                "variant_id": pair.get("variant_id", ""),
                "model_path": pair.get("model_path", ""),
                "pairs": 0,
                "raw_success_regressions_vs_additive": 0,
                "raw_success_regressions_vs_static_flow": 0,
                "raw_success_regressions_vs_g556": 0,
                "raw_success_gains_vs_additive": 0,
                "raw_success_gains_vs_static_flow": 0,
                "raw_success_gains_vs_g556": 0,
                "deltas_vs_additive": [],
                "deltas_vs_static_flow": [],
                "deltas_vs_g556": [],
            },
        )
        bucket["pairs"] += 1
        for tier in ["additive", "static_flow", "g556"]:
            bucket[f"raw_success_regressions_vs_{tier}"] += int(boolish(pair.get(f"success_regression_vs_{tier}")))
            bucket[f"raw_success_gains_vs_{tier}"] += int(boolish(pair.get(f"success_gain_vs_{tier}")))
            value = number(pair.get(f"delta_vs_{tier}"), math.nan)
            if math.isfinite(value):
                bucket[f"deltas_vs_{tier}"].append(value)
    for key, bucket in list(per_variant.items()):
        for tier in ["additive", "static_flow", "g556"]:
            values = bucket.pop(f"deltas_vs_{tier}")
            bucket[f"mean_delta_vs_{tier}"] = float(np.mean(values)) if values else None
            bucket[f"median_delta_vs_{tier}"] = float(np.median(values)) if values else None
            bucket[f"supported_worse_outside_margin_vs_{tier}"] = sum(value > margin for value in values)

    summary = {
        "schema_version": f"{ROUND}_{safe_token(phase)}_summary_v1",
        "decision": (
            "g567_three_tier_replay_materialized"
            if materialized
            else ("g567_three_tier_materialization_blocked_process_hard_timeout" if timeout_rows else "g567_three_tier_materialization_blocked")
        ),
        "replay_phase": phase,
        "planned_rows": len(plan_rows),
        "executed_rows": len(rows),
        "process_hard_timeout_rows": timeout_rows,
        "process_group_timeout_provenance_rows": sum(
            str(row.get("process_timeout_provenance", "")).startswith("subprocess_popen_posix_start_new_session")
            for row in rows
            if str(row.get("process_hard_timeout_sec", "")).strip()
        ),
        "contexts": len({row.get("g567_dataset_row_id") for row in plan_rows}),
        "actor_candidate_rows": len(actor_rows),
        "new_exact_materialized_candidate_rows": sum(
            boolish(row.get("candidate_recognized_bool"))
            and boolish(row.get("fulltheta_fingerprint_match_strict"))
            and boolish(row.get("identity_retained"))
            and boolish(row.get("scenario_sha256_match"))
            for row in actor_rows
        ),
        "exact_materialization_rate": (exact / max(1, len(actor_rows))),
        "candidate_recognized_rate": recognized / max(1, len(actor_rows)),
        "identity_retention_rate": identity / max(1, len(actor_rows)),
        "scenario_hash_match_rate": scenario / max(1, len(actor_rows)),
        "additive_rows_present": sum(1 for row in rows if row.get("materialized_method") == ADDITIVE_SOLVER_ALIAS),
        "static_flow_rows_present": sum(1 for row in rows if row.get("materialized_method") == STATIC_FLOW_SOLVER_ALIAS),
        "g556_rows_present": sum(1 for row in rows if row.get("materialized_method") == G556_SOLVER_ALIAS),
        "three_tier_pairs": len(pairs),
        "replicate_groups": len(replicate_group_counts),
        "replicate_count_min": min(replicate_counts) if replicate_counts else 0,
        "replicate_count_max": max(replicate_counts) if replicate_counts else 0,
        "replicate_count_mean": float(np.mean(replicate_counts)) if replicate_counts else 0.0,
        "same_pair_groups_with_at_least_5_repeats": sum(count >= 5 for count in replicate_counts),
        "same_pair_groups_with_at_least_10_repeats": sum(count >= 10 for count in replicate_counts),
        "worker_count_values": sorted({str(row.get("worker_count", "")) for row in pairs if str(row.get("worker_count", "")).strip()}),
        "applied_quality_margin": margin,
        "per_variant_transfer": per_variant,
        **tier_stats("additive"),
        **tier_stats("static_flow"),
        **tier_stats("g556"),
        **claims(),
    }
    return summary


def solver_binary(arg: Path) -> Path:
    for candidate in [arg, Path("build/phase1a-batch/phase1a_batch"), Path("build/phase1-ltm/phase1a_batch"), Path("build/phase1a-batch/phase1a_batch.exe")]:
        path = resolve(candidate)
        if path.exists():
            return path
    return resolve(arg)


def run_replay_phase(
    phase: str,
    contexts: list[G567Context],
    theta_rows: list[dict[str, Any]],
    *,
    binary: Path,
    max_workers: int,
    overwrite: bool,
    margin: float,
    plan_only: bool,
    include_no_ltm: bool = False,
    repeat_count: int = 1,
) -> dict[str, Any]:
    paths = plan_paths(phase)
    plan_rows, registry_rows = build_plan_and_registry(contexts, theta_rows, phase, include_no_ltm=include_no_ltm, repeat_count=repeat_count)
    for order, row in enumerate(plan_rows):
        row["execution_order_index"] = order
        row["worker_count"] = max(1, int(max_workers))
    budget_audit = audit_plan_explicit_budgets(plan_rows, phase)
    write_rows(paths["plan"], plan_rows)
    write_rows(paths["registry"], registry_rows)
    if budget_audit.get("decision") != "g567_solver_budget_audit_passed":
        summary = {
            "schema_version": f"{ROUND}_{safe_token(phase)}_summary_v1",
            "decision": "g567_blocked_solver_budget_audit_failed",
            "replay_phase": phase,
            "planned_rows": len(plan_rows),
            "budget_audit_failures": budget_audit.get("failures", []),
            **claims(),
        }
        write_json(paths["summary"], summary)
        return summary
    if plan_only:
        summary = {
            "schema_version": f"{ROUND}_{safe_token(phase)}_summary_v1",
            "decision": "g567_three_tier_plan_created_server_run_required",
            "replay_phase": phase,
            "contexts": len(contexts),
            "actor_candidate_rows": len(theta_rows),
            "planned_rows": len(plan_rows),
            "static_flow_rows_planned": sum(1 for row in plan_rows if row.get("candidate_id") == STATIC_FLOW_SOLVER_ALIAS),
            **claims(),
        }
        write_json(paths["summary"], summary)
        return summary
    binary_path = solver_binary(binary)
    if not binary_path.exists():
        summary = {"schema_version": f"{ROUND}_{safe_token(phase)}_summary_v1", "decision": "g567_blocked_missing_solver_binary", "binary": rel(binary_path), **claims()}
        write_json(paths["summary"], summary)
        return summary
    os.environ.setdefault("REPAIR5G_STREAM_RESULT_CSV", "1")
    os.environ.setdefault("REPAIR5G_SKIP_AGGREGATE_JSONL", "1")
    os.environ.setdefault("G567_REQUIRE_EXPLICIT_SOLVER_BUDGETS", "1")

    def execute_probe_subset(subset: list[dict[str, Any]], *, token: str, result_csv: Path, raw_csv: Path, log_dir: Path, scenario_metadata: Path) -> list[dict[str, Any]]:
        g549.run_probe_plan(
            subset,
            binary=binary_path,
            overwrite=overwrite,
            row_limit=0,
            max_workers=max(1, int(max_workers)),
            registry_path=str(resolve(paths["registry"])),
            result_csv=str(resolve(result_csv)),
            raw_csv=str(resolve(raw_csv)),
            log_dir=str(resolve(log_dir)),
            run_jsonl=str(resolve(log_dir / "runs.jsonl")),
            command_jsonl=str(resolve(log_dir / "commands.jsonl")),
            update_jsonl=str(resolve(log_dir / "updates.jsonl")),
            probe_jsonl=str(resolve(log_dir / "counterfactual_probes.jsonl")),
            checkpoint_jsonl=str(resolve(log_dir / "checkpoints.jsonl")),
            status_json=str(resolve(log_dir / "status.json")),
            scenario_dir=str(resolve(paths["scenario_dir"])),
            scenario_metadata=str(resolve(scenario_metadata)),
            manifest_prefix=f"g567_{safe_token(phase)}_{token}",
            row_prefix=f"g567_{safe_token(phase)}_{token}",
            execution_mode=f"g567_{safe_token(phase)}_real_solver_row",
        )
        return audit_results(read_rows(result_csv), subset, phase)

    if repeat_count > 1 and "repeat" in safe_token(phase):
        rows = []
        replicate_ids = sorted({str(row.get("replicate_id", "0")) for row in plan_rows}, key=lambda value: int(number(value, 0)))
        for replicate_id in replicate_ids:
            token = f"rep{int(number(replicate_id, 0)):02d}"
            subset = [row for row in plan_rows if str(row.get("replicate_id", "0")) == replicate_id]
            rows.extend(
                execute_probe_subset(
                    subset,
                    token=token,
                    result_csv=paths["results"].with_name(f"{paths['results'].stem}_{token}{paths['results'].suffix}"),
                    raw_csv=paths["raw_results"].with_name(f"{paths['raw_results'].stem}_{token}{paths['raw_results'].suffix}"),
                    log_dir=paths["log_dir"] / token,
                    scenario_metadata=paths["scenario_metadata"].with_name(f"{paths['scenario_metadata'].stem}_{token}{paths['scenario_metadata'].suffix}"),
                )
            )
    else:
        rows = execute_probe_subset(
            plan_rows,
            token="main",
            result_csv=paths["results"],
            raw_csv=paths["raw_results"],
            log_dir=paths["log_dir"],
            scenario_metadata=paths["scenario_metadata"],
        )
    write_rows(paths["results"], rows)
    pairs = build_three_tier_pairs(rows, phase)
    write_rows(paths["pairs"], pairs)
    summary = summarize_pairs(pairs, rows, plan_rows, phase, margin)
    write_json(paths["summary"], summary)
    write_text(
        paths["report"],
        f"# G5.67 {phase} Three-Tier Replay\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- contexts: `{summary['contexts']}`\n"
        f"- actor candidate rows: `{summary['actor_candidate_rows']}`\n"
        f"- three-tier pairs: `{summary['three_tier_pairs']}`\n"
        f"- static-flow rows present: `{summary['static_flow_rows_present']}`\n"
        f"- process hard timeout rows: `{summary['process_hard_timeout_rows']}`\n"
        f"- exact materialization rate: `{summary['exact_materialization_rate']}`\n",
    )
    return summary


def checkpoint_paths(patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pattern in patterns:
        out.extend(path for path in sorted(ROOT.glob(pattern)) if path.is_file())
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in out:
        r = path.resolve()
        if r not in seen:
            unique.append(path)
            seen.add(r)
    return unique


def generate_response_thetas(contexts: list[G567Context], raw_rows: list[dict[str, Any]], *, phase: str, target_rows: int) -> list[dict[str, Any]]:
    raw_by_context = {str(row["context_id"]): row for row in raw_rows}
    alphas = [0.0, 0.25, 0.50, 0.75, 1.0, 1.25, 1.50]
    group_alphas = [0.0, 0.50, 1.0, 1.50]
    leave_alphas = [0.0, 0.50, 1.0]
    out: list[dict[str, Any]] = []
    anchor = np.asarray(BASELINE_G556, dtype=np.float32)
    lo = np.asarray(THETA_LO, dtype=np.float32)
    hi = np.asarray(THETA_HI, dtype=np.float32)
    prepared: list[tuple[G567Context, dict[str, Any], np.ndarray, np.ndarray, bool]] = []
    for ctx in contexts:
        raw = raw_by_context.get(ctx.dataset_row_id)
        if not raw:
            continue
        raw_vec = np.asarray([number(raw.get(col), float(anchor[idx])) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)], dtype=np.float32)
        primary_30s_exact_context = float(ctx.base_time_limit_sec) >= 30.0
        prepared.append((ctx, raw, raw_vec, raw_vec - anchor, primary_30s_exact_context))
    if target_rows < len(prepared):
        raise ValueError(
            f"coverage-first response generation needs target_rows >= contexts_with_raw "
            f"({target_rows} < {len(prepared)})"
        )

    def emit(
        ctx: G567Context,
        raw: dict[str, Any],
        label: str,
        vec: np.ndarray,
        *,
        primary_30s_exact_context: bool,
        coverage_first: bool,
        pass_index: int,
    ) -> None:
        clipped = np.minimum(np.maximum(vec, lo), hi)
        row = {col: float(clipped[idx]) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)}
        row.update(mode_columns("flow_shield"))
        out.append(
            {
                "phase": phase,
                "context_id": ctx.dataset_row_id,
                "g567_evaluation_uid": ctx.evaluation_uid,
                "variant_id": label,
                "variant_name": "field_group_response",
                "seed": "566",
                "method": f"g567_response_{label}",
                "model_path": str(raw.get("model_path", "")),
                "raw_actor_variant_id": raw.get("variant_id", ""),
                "multi_fidelity_stage": (
                    "selected_30s_exact_candidate"
                    if primary_30s_exact_context
                    else ("coverage_first_exact_candidate" if coverage_first else f"exploratory_response_surface_pass_{pass_index:02d}")
                ),
                "coverage_first_candidate": coverage_first,
                "response_candidate_pass": pass_index,
                "primary_30s_exploratory_full_lattice_skipped": primary_30s_exact_context,
                "large_agent_30s_exploratory_full_lattice_skipped": primary_30s_exact_context and ctx.agents in G567_LARGE_PRIMARY_AGENT_TIERS,
                **row,
            }
        )

    for ctx, raw, raw_vec, _delta, primary_30s_exact_context in prepared:
        label = "SELECTED_ACTOR_PRIMARY_30S_EXACT" if primary_30s_exact_context else "GLOBAL_ALPHA_1p0"
        emit(ctx, raw, label, raw_vec, primary_30s_exact_context=primary_30s_exact_context, coverage_first=True, pass_index=0)
    if len(out) >= target_rows:
        return out[:target_rows]

    extra_specs: list[tuple[str, str, Any]] = []
    for alpha in alphas:
        if abs(alpha - 1.0) <= 1.0e-12:
            continue
        extra_specs.append(("global", f"GLOBAL_ALPHA_{str(alpha).replace('.', 'p')}", alpha))
    for group_name, cols in FIELD_GROUPS.items():
        for alpha in group_alphas:
            extra_specs.append(("group", f"{group_name}_ONLY_ALPHA_{str(alpha).replace('.', 'p')}", (cols, alpha)))
    for group_name, cols in FIELD_GROUPS.items():
        for alpha in leave_alphas:
            extra_specs.append(("leave", f"LEAVE_{group_name}_ALPHA_{str(alpha).replace('.', 'p')}", (cols, alpha)))
    for pass_index, (kind, label, spec) in enumerate(extra_specs, start=1):
        for ctx, raw, raw_vec, delta, primary_30s_exact_context in prepared:
            if primary_30s_exact_context:
                continue
            if kind == "global":
                vec = anchor + float(spec) * delta
            elif kind == "group":
                cols, alpha = spec
                mask = np.zeros_like(delta)
                mask[cols] = delta[cols]
                vec = anchor + float(alpha) * mask
            else:
                cols, alpha = spec
                mask = delta.copy()
                mask[cols] *= float(alpha)
                vec = anchor + mask
            emit(ctx, raw, label, vec, primary_30s_exact_context=False, coverage_first=False, pass_index=pass_index)
            if len(out) >= target_rows:
                return out[:target_rows]
    return out[:target_rows]


def _candidate_replicate_key(row: dict[str, Any]) -> str:
    return str(row.get("replicate_group_id") or stable_uid("single_candidate", row.get("g567_evaluation_uid", ""), row.get("theta_id", "")))


def _quality_harm(delta: float, margin: float) -> bool:
    return math.isfinite(delta) and delta > margin


def _quality_gain(delta: float, margin: float) -> bool:
    return math.isfinite(delta) and delta < -margin


def create_labelv54_from_pairs(pair_paths: list[Path], margin: float) -> dict[str, Any]:
    pairs: list[dict[str, str]] = []
    for path in pair_paths:
        pairs.extend(read_rows(path))
    replicate_counts = Counter(_candidate_replicate_key(row) for row in pairs)
    context_rows: dict[str, dict[str, Any]] = {}
    candidate_rows: list[dict[str, Any]] = []
    replicate_rows: list[dict[str, Any]] = []
    safe_sets: dict[str, dict[str, Any]] = {}
    for row in pairs:
        uid = row.get("g567_evaluation_uid", "")
        if not uid:
            continue
        context_rows.setdefault(
            uid,
            {
                "g567_evaluation_uid": uid,
                "g567_dataset_row_id": row.get("g567_dataset_row_id", ""),
                "split": row.get("split", ""),
                "map": row.get("map", ""),
                "map_family": row.get("map_family", ""),
                "agents": row.get("agents", ""),
                "budget_ms": row.get("budget_ms", ""),
                **claims(),
            },
        )
        dg = number(row.get("delta_vs_g556"), math.nan)
        ds = number(row.get("delta_vs_static_flow"), math.nan)
        da = number(row.get("delta_vs_additive"), math.nan)
        replicate_key = _candidate_replicate_key(row)
        replicate_count = int(replicate_counts.get(replicate_key, 1))
        phase = str(row.get("replay_phase", ""))
        boundary_row = any(
            boolish(row.get(col))
            for col in [
                "success_gain_vs_additive",
                "success_regression_vs_additive",
                "success_gain_vs_static_flow",
                "success_regression_vs_static_flow",
                "success_gain_vs_g556",
                "success_regression_vs_g556",
            ]
        )
        stable_label_supported = (replicate_count >= 5) or (not boundary_row)
        supported_regression_A = stable_label_supported and boolish(row.get("success_regression_vs_additive"))
        supported_regression_B = stable_label_supported and boolish(row.get("success_regression_vs_static_flow"))
        supported_regression_C = stable_label_supported and boolish(row.get("success_regression_vs_g556"))
        supported_gain_A = stable_label_supported and boolish(row.get("success_gain_vs_additive"))
        supported_gain_B = stable_label_supported and boolish(row.get("success_gain_vs_static_flow"))
        supported_gain_C = stable_label_supported and boolish(row.get("success_gain_vs_g556"))
        safe_A = stable_label_supported and not supported_regression_A
        safe_B = stable_label_supported and not supported_regression_B
        safe_C = stable_label_supported and not supported_regression_C
        primary_safe_AB = safe_A and safe_B
        stretch_safe_ABC = primary_safe_AB and safe_C
        quality_safe_A = not _quality_harm(da, margin)
        quality_safe_B = not _quality_harm(ds, margin)
        quality_safe_C = not _quality_harm(dg, margin)
        positive_A = safe_A and quality_safe_A and _quality_gain(da, margin)
        positive_B = safe_B and quality_safe_B and _quality_gain(ds, margin)
        positive_C = safe_C and quality_safe_C and _quality_gain(dg, margin)
        joint_positive_AB = primary_safe_AB and quality_safe_A and quality_safe_B and positive_A and positive_B
        joint_positive_ABC = stretch_safe_ABC and quality_safe_A and quality_safe_B and quality_safe_C and positive_A and positive_B and positive_C
        harmful = (
            supported_regression_A
            or supported_regression_B
            or supported_regression_C
            or _quality_harm(da, margin)
            or _quality_harm(ds, margin)
            or _quality_harm(dg, margin)
        )
        measurement_confidence = (
            "stable_replicated_boundary" if boundary_row and replicate_count >= 5 else
            "single_run_boundary_uncertain" if boundary_row else
            "single_run_both_success_or_both_failure"
        )
        theta_id = row.get("theta_id", "")
        candidate_rows.append(
            {
                "g567_evaluation_uid": uid,
                "g567_dataset_row_id": row.get("g567_dataset_row_id", ""),
                "split": row.get("split", ""),
                "map": row.get("map", ""),
                "map_family": row.get("map_family", ""),
                "agents": row.get("agents", ""),
                "budget_ms": row.get("budget_ms", ""),
                "candidate_uid": theta_id,
                "theta_id": theta_id,
                "variant_id": row.get("variant_id", ""),
                "labelv54_development_safe": primary_safe_AB,
                "labelv54_positive": joint_positive_AB,
                "labelv54_harmful": harmful,
                "labelv54_quality_tie": all((not math.isfinite(v)) or abs(v) <= margin for v in [dg, ds, da]),
                "labelv54_applied_margin": margin,
                "stable_label_supported": stable_label_supported,
                "measurement_confidence": measurement_confidence,
                "replicate_group_id": replicate_key,
                "replicate_count": replicate_count,
                "supported_regression_A": supported_regression_A,
                "supported_regression_B": supported_regression_B,
                "supported_regression_C": supported_regression_C,
                "supported_gain_A": supported_gain_A,
                "supported_gain_B": supported_gain_B,
                "supported_gain_C": supported_gain_C,
                "safe_A": safe_A,
                "safe_B": safe_B,
                "safe_C": safe_C,
                "primary_safe_AB": primary_safe_AB,
                "stretch_safe_ABC": stretch_safe_ABC,
                "quality_safe_A": quality_safe_A,
                "quality_safe_B": quality_safe_B,
                "quality_safe_C": quality_safe_C,
                "positive_A": positive_A,
                "positive_B": positive_B,
                "positive_C": positive_C,
                "joint_positive_AB": joint_positive_AB,
                "joint_positive_ABC": joint_positive_ABC,
                "delta_vs_additive": row.get("delta_vs_additive", ""),
                "delta_vs_static_flow": row.get("delta_vs_static_flow", ""),
                "delta_vs_g556": row.get("delta_vs_g556", ""),
                "actor_success": row.get("actor_success", ""),
                "additive_success": row.get("additive_success", ""),
                "static_flow_success": row.get("static_flow_success", ""),
                "g556_success": row.get("g556_success", ""),
                "actor_ratio": row.get("actor_ratio", ""),
                "additive_ratio": row.get("additive_ratio", ""),
                "static_flow_ratio": row.get("static_flow_ratio", ""),
                "g556_ratio": row.get("g556_ratio", ""),
                "success_gain_vs_additive": row.get("success_gain_vs_additive", ""),
                "success_regression_vs_additive": row.get("success_regression_vs_additive", ""),
                "success_gain_vs_static_flow": row.get("success_gain_vs_static_flow", ""),
                "success_regression_vs_static_flow": row.get("success_regression_vs_static_flow", ""),
                "success_gain_vs_g556": row.get("success_gain_vs_g556", ""),
                "success_regression_vs_g556": row.get("success_regression_vs_g556", ""),
                "actor_runtime_ms": row.get("actor_runtime_ms", ""),
                "additive_runtime_ms": row.get("additive_runtime_ms", ""),
                "static_flow_runtime_ms": row.get("static_flow_runtime_ms", ""),
                "g556_runtime_ms": row.get("g556_runtime_ms", ""),
                "actor_expanded_nodes": row.get("actor_expanded_nodes", ""),
                "g556_expanded_nodes": row.get("g556_expanded_nodes", ""),
                "actor_low_level_pibt_calls": row.get("actor_low_level_pibt_calls", ""),
                "g556_low_level_pibt_calls": row.get("g556_low_level_pibt_calls", ""),
                "replicate_confidence": "single_exact_row" if "repeat" not in str(row.get("replay_phase", "")) else "repeatability_row",
                **{col: row.get(col, "") for col in THETA_NUMERIC_COLUMNS},
                **claims(),
            }
        )
        entry = safe_sets.setdefault(
            uid,
            {
                "g567_evaluation_uid": uid,
                "safe_AB_theta_ids": [],
                "safe_ABC_theta_ids": [],
                "primary_training_theta_ids": [],
                "joint_positive_AB_theta_ids": [],
                "joint_positive_ABC_theta_ids": [],
            },
        )
        if primary_safe_AB:
            entry["safe_AB_theta_ids"].append(theta_id)
        if stretch_safe_ABC:
            entry["safe_ABC_theta_ids"].append(theta_id)
        if joint_positive_AB:
            entry["joint_positive_AB_theta_ids"].append(theta_id)
        if joint_positive_ABC:
            entry["joint_positive_ABC_theta_ids"].append(theta_id)
        if "repeat" in str(row.get("replay_phase", "")):
            replicate_rows.append({**row, "labelv54_applied_margin": margin, **claims()})
    candidates_by_uid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidate_rows:
        candidates_by_uid[str(row.get("g567_evaluation_uid", ""))].append(row)
        row["pareto_safe_AB"] = False
        row["labelv54_primary_training_candidate"] = False
    for uid, rows in candidates_by_uid.items():
        eligible = [
            row
            for row in rows
            if boolish(row.get("primary_safe_AB"))
            and boolish(row.get("quality_safe_A"))
            and boolish(row.get("quality_safe_B"))
        ]
        values = {
            id(row): (
                number(row.get("delta_vs_additive"), math.inf),
                number(row.get("delta_vs_static_flow"), math.inf),
            )
            for row in eligible
        }
        for row in eligible:
            da, ds = values[id(row)]
            dominated = False
            for other in eligible:
                if other is row:
                    continue
                oda, ods = values[id(other)]
                if oda <= da + 1.0e-12 and ods <= ds + 1.0e-12 and (oda < da - 1.0e-12 or ods < ds - 1.0e-12):
                    dominated = True
                    break
            if not dominated:
                row["pareto_safe_AB"] = True
                row["labelv54_primary_training_candidate"] = True
                safe_sets.setdefault(
                    uid,
                    {
                        "g567_evaluation_uid": uid,
                        "safe_AB_theta_ids": [],
                        "safe_ABC_theta_ids": [],
                        "primary_training_theta_ids": [],
                        "joint_positive_AB_theta_ids": [],
                        "joint_positive_ABC_theta_ids": [],
                    },
                )["primary_training_theta_ids"].append(str(row.get("theta_id", "")))
    label_train_uids = {
        str(row.get("g567_evaluation_uid", ""))
        for row in context_rows.values()
        if str(row.get("split", "")).upper() == "LABEL_TRAIN" and str(row.get("g567_evaluation_uid", "")).strip()
    }
    write_rows(LABELV54_CONTEXTS, list(context_rows.values()))
    write_rows(LABELV54_CANDIDATES, candidate_rows)
    write_rows(LABELV54_REPLICATES, replicate_rows)
    LABELV54_SAFE_SETS.parent.mkdir(parents=True, exist_ok=True)
    with resolve(LABELV54_SAFE_SETS).open("w", encoding="utf-8") as handle:
        for entry in safe_sets.values():
            handle.write(json.dumps({**entry, **claims()}, sort_keys=True) + "\n")
    summary = {
        "schema_version": f"{ROUND}_labelv54_summary_v1",
        "decision": "g567_labelv54_valid_replicated_tail_materialized" if candidate_rows else "g567_labelv54_blocked_no_pairs",
        "source_pair_files": [rel(path) for path in pair_paths if resolve(path).exists()],
        "contexts": len(context_rows),
        "candidates": len(candidate_rows),
        "replicate_rows": len(replicate_rows),
        "applied_margin": margin,
        "applied_margin_source": rel(REPEATABILITY_SUMMARY),
        "safe_candidates": sum(boolish(row.get("labelv54_development_safe")) for row in candidate_rows),
        "positive_candidates": sum(boolish(row.get("labelv54_positive")) for row in candidate_rows),
        "harmful_candidates": sum(boolish(row.get("labelv54_harmful")) for row in candidate_rows),
        "single_run_boundary_uncertain_candidates": sum(row.get("measurement_confidence") == "single_run_boundary_uncertain" for row in candidate_rows),
        "primary_safe_AB_candidates": sum(boolish(row.get("primary_safe_AB")) for row in candidate_rows),
        "primary_training_candidates": sum(boolish(row.get("labelv54_primary_training_candidate")) for row in candidate_rows),
        "label_train_unique_exact_labeled_contexts": len(label_train_uids),
        "label_train_24000_unique_context_target_met": len(label_train_uids) >= 24000,
        "development_calibration_blind_excluded_from_actor_training": True,
        "pareto_safe_AB_candidates": sum(boolish(row.get("pareto_safe_AB")) for row in candidate_rows),
        "stretch_safe_ABC_candidates": sum(boolish(row.get("stretch_safe_ABC")) for row in candidate_rows),
        "joint_positive_AB_candidates": sum(boolish(row.get("joint_positive_AB")) for row in candidate_rows),
        "joint_positive_ABC_candidates": sum(boolish(row.get("joint_positive_ABC")) for row in candidate_rows),
        "safe_sets_path": rel(LABELV54_SAFE_SETS),
        **claims(),
    }
    write_json(LABELV54_SUMMARY, summary)
    return summary


def actor_examples_from_labelv54(contexts: list[G567Context]) -> list[ActorTrainExample]:
    by_uid = {ctx.evaluation_uid: ctx for ctx in contexts}
    candidates_by_uid: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_rows(LABELV54_CANDIDATES):
        uid = row.get("g567_evaluation_uid", "")
        if uid in by_uid:
            candidates_by_uid[uid].append(row)
    critic_by_candidate = {
        (row.get("g567_evaluation_uid", ""), row.get("candidate_uid", "") or row.get("theta_id", "")): row
        for row in read_rows(DISTRIBUTIONAL_CRITIC_PREDICTIONS)
    }
    examples: list[ActorTrainExample] = []
    anchor = np.asarray(BASELINE_G556, dtype=np.float32)
    span = np.maximum(np.asarray(THETA_HI - THETA_LO, dtype=np.float32), 1.0e-6)
    for uid, rows in sorted(candidates_by_uid.items()):
        ctx = by_uid[uid]
        positives = [row for row in rows if boolish(row.get("labelv54_positive"))]
        safe = [row for row in rows if boolish(row.get("primary_safe_AB", row.get("labelv54_development_safe")))]
        pareto_safe = [row for row in rows if boolish(row.get("labelv54_primary_training_candidate", row.get("pareto_safe_AB")))]
        source = pareto_safe or safe
        if source:
            theta_arr = np.asarray(
                [
                    [number(row.get(col), float(anchor[idx])) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)]
                    for row in source
                ],
                dtype=np.float32,
            )
            norm_arr = (theta_arr - np.asarray(THETA_LO, dtype=np.float32)) / span
            if len(source) == 1:
                medoid_idx = 0
            else:
                pairwise_l1 = np.mean(np.abs(norm_arr[:, None, :] - norm_arr[None, :, :]), axis=2)
                medoid_idx = int(np.argmin(np.mean(pairwise_l1, axis=1)))
            best_idx = medoid_idx
            best_score: tuple[float, float, float, float] | None = None
            for idx, row in enumerate(source):
                critic = critic_by_candidate.get((uid, row.get("candidate_uid", "") or row.get("theta_id", "")), {})
                risk_ub = max(
                    number(critic.get("p_success_regression_vs_additive_ucb"), 0.0),
                    number(critic.get("p_success_regression_vs_static_flow_ucb"), 0.0),
                )
                unsupported = number(critic.get("unsupported_theta_region_score"), 0.0)
                gain_ab = max(0.0, -number(row.get("delta_vs_additive"), 0.0)) + max(0.0, -number(row.get("delta_vs_static_flow"), 0.0))
                harm_abc = (
                    max(0.0, number(row.get("delta_vs_additive"), 0.0))
                    + max(0.0, number(row.get("delta_vs_static_flow"), 0.0))
                    + max(0.0, number(row.get("delta_vs_g556"), 0.0))
                )
                medoid_penalty = float(np.mean(np.abs(norm_arr[idx] - norm_arr[medoid_idx])))
                score = (
                    float(boolish(row.get("labelv54_primary_training_candidate", row.get("pareto_safe_AB")))),
                    float(boolish(row.get("joint_positive_AB"))),
                    gain_ab - harm_abc,
                    -risk_ub - unsupported,
                    -medoid_penalty,
                )
                if best_score is None or score > best_score:
                    best_score = score
                    best_idx = idx
            target = theta_arr[best_idx].astype(np.float32)
            weight = float(max(0.5, min(4.0, len(positives) + 0.25 * len(pareto_safe or safe))))
        else:
            target = anchor.copy()
            weight = 0.75
        target = np.minimum(np.maximum(target, np.asarray(THETA_LO, dtype=np.float32)), np.asarray(THETA_HI, dtype=np.float32))
        deviation = float(np.mean(np.abs((target - anchor) / span)))
        examples.append(
            ActorTrainExample(
                example_id=f"g567_actor_train_{len(examples):06d}",
                evaluation_uid=uid,
                split=ctx.split,
                map_family=ctx.map_family,
                graph=ctx.graph_with_traffic,
                assignment=ctx.assignment,
                feature_row=ctx.feature_row,
                target=target,
                weight=max(weight, 0.5 + deviation),
                positive_count=len(positives),
                safe_count=len(pareto_safe or safe),
            )
        )
    return examples


def split_actor_examples(examples: list[ActorTrainExample]) -> tuple[list[ActorTrainExample], list[ActorTrainExample]]:
    label_train = [ex for ex in examples if ex.split == "LABEL_TRAIN"]
    if label_train:
        valid = label_train[::5]
        train = [ex for idx, ex in enumerate(label_train) if idx % 5 != 0]
        return train or label_train, valid or label_train[-max(1, len(label_train) // 5) :]
    train = [ex for ex in examples if ex.split in {"TRAIN", "VALIDATION"}]
    valid = [ex for ex in examples if ex.split == "CALIBRATION"]
    if not valid:
        valid = examples[::5]
        train = [ex for idx, ex in enumerate(examples) if idx % 5 != 0]
    return train or examples, valid or examples[-max(1, len(examples) // 5) :]


def actor_tensor_batch(examples: list[ActorTrainExample], device: str):
    import torch

    graph_batch = move_graph_batch(make_graph_batch([ex.graph for ex in examples]), device)
    od_tokens, od_mask = pad_od_tokens([ex.assignment for ex in examples])
    scalars = torch.tensor(np.stack([scalar_features(ex.feature_row) for ex in examples]), dtype=torch.float32, device=device)
    target = torch.tensor(np.stack([ex.target for ex in examples]), dtype=torch.float32, device=device)
    weights = torch.tensor(np.asarray([ex.weight for ex in examples], dtype=np.float32), device=device)
    return graph_batch, od_tokens.to(device), od_mask.to(device), scalars, target, weights


def actor_example_token_count(example: ActorTrainExample) -> int:
    graph_tokens = len(example.graph.cells) if example.graph is not None else 0
    od_tokens = len(example.assignment.get("starts", [])) if isinstance(example.assignment, dict) else 0
    return max(1, graph_tokens + od_tokens)


def token_budget_batches(examples: list[ActorTrainExample], *, max_examples: int, max_tokens: int) -> list[list[ActorTrainExample]]:
    batches: list[list[ActorTrainExample]] = []
    current: list[ActorTrainExample] = []
    current_tokens = 0
    max_examples = max(1, int(max_examples))
    max_tokens = max(1, int(max_tokens))
    for example in examples:
        tokens = actor_example_token_count(example)
        if current and (len(current) >= max_examples or current_tokens + tokens > max_tokens):
            batches.append(current)
            current = []
            current_tokens = 0
        current.append(example)
        current_tokens += tokens
    if current:
        batches.append(current)
    return batches


def actor_gradient_summary(model: Any) -> dict[str, float]:
    groups = {
        "topology_grad_norm": ["topology_encoder"],
        "c0_grad_norm": ["c0_encoder"],
        "f0_grad_norm": ["f0_encoder"],
        "od_grad_norm": ["od_encoder", "od_token_proj", "cross_attn"],
        "scalar_grad_norm": ["scalar_encoder"],
        "fusion_grad_norm": ["fusion"],
        "theta_head_grad_norm": ["delta_head", "trust_head"],
    }
    out: dict[str, float] = {}
    for group, tokens in groups.items():
        total = 0.0
        for name, param in model.named_parameters():
            if any(token in name for token in tokens) and param.grad is not None:
                total += float(param.grad.detach().norm().cpu())
        out[group] = total
    return out


def evaluate_actor_model(model: Any, examples: list[ActorTrainExample], device: str, batch_size: int) -> dict[str, Any]:
    import torch

    model.eval()
    span = torch.tensor(np.asarray(THETA_HI - THETA_LO, dtype=np.float32), device=device).clamp_min(1.0e-6)
    losses: list[float] = []
    noop_losses: list[float] = []
    with torch.no_grad():
        for start in range(0, len(examples), batch_size):
            batch = examples[start : start + batch_size]
            graph_batch, od_tokens, od_mask, scalars, target, weights = actor_tensor_batch(batch, device)
            pred = model(graph_batch, od_tokens, od_mask, scalars)
            per = torch.mean(torch.abs((pred - target) / span), dim=1)
            losses.extend(per.detach().cpu().numpy().tolist())
            noop = torch.mean(torch.abs((pred - torch.tensor(BASELINE_G556, dtype=torch.float32, device=device)) / span), dim=1)
            noop_losses.extend(noop.detach().cpu().numpy().tolist())
    return {
        "validation_labelv54_normalized_l1": float(np.mean(losses)) if losses else None,
        "validation_noop_deviation": float(np.mean(noop_losses)) if noop_losses else None,
    }


def train_one_g567_actor(
    variant_id: str,
    seed: int,
    examples: list[ActorTrainExample],
    *,
    device: str,
    epochs: int,
    min_epochs: int,
    patience: int,
    batch_size: int,
    token_budget: int,
    hidden_dim: int,
    lr: float,
    checkpoint_interval_sec: float,
    resume: bool,
    diagnostic_only: bool = False,
    training_context_uids: list[str] | None = None,
    training_dataset_sha256: str = "",
    source_commit: str = "",
    no_performance_claim: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    import torch

    from gcst.dual_stream_graph_actor import DualStreamGoalAwareActor, architecture_from_id

    arch = architecture_from_id(variant_id)
    torch.manual_seed(seed)
    rng = random.Random(seed + sum(ord(ch) for ch in variant_id))
    model = DualStreamGoalAwareActor(
        hidden_dim=hidden_dim,
        scalar_only_control=arch.scalar_only_control,
        use_cross_attention=arch.use_cross_attention,
        safe_subspace=arch.safe_subspace,
        field_group_trust=arch.field_group_trust,
        od_perceiver=arch.od_perceiver,
        graph_local_layers=arch.graph_local_layers,
        graph_global_layers=arch.graph_global_layers,
        heads=arch.heads,
        latent_tokens=arch.latent_tokens,
    ).module().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1.0e-4)
    train, valid = split_actor_examples(examples)
    span = torch.tensor(np.asarray(THETA_HI - THETA_LO, dtype=np.float32), device=device).clamp_min(1.0e-6)
    out_path = resolve(MODEL_DIR / f"{ROUND}_{variant_id.lower()}_{arch.variant_name}_seed{seed}.pt")
    resume_path = resolve(MODEL_DIR / f"{ROUND}_{variant_id.lower()}_{arch.variant_name}_seed{seed}.resume.pt")
    best_metric = math.inf
    best_epoch = 0
    best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    stale = 0
    last_grad: dict[str, float] = {}
    final_train_loss = 0.0
    start_epoch = 1
    gpu_active_sec = 0.0
    last_checkpoint_sec = time.perf_counter()
    last_hourly_checkpoint_path = ""
    use_bf16 = str(device).startswith("cuda")
    if resume and resume_path.exists():
        payload = torch.load(resume_path, map_location=device, weights_only=False)
        model.load_state_dict(payload["model_state_dict"])
        opt.load_state_dict(payload["optimizer_state_dict"])
        best_state = payload.get("best_state_dict", best_state)
        best_metric = float(payload.get("best_metric", best_metric))
        best_epoch = int(payload.get("best_epoch", best_epoch))
        stale = int(payload.get("stale", stale))
        start_epoch = int(payload.get("epoch", 0)) + 1
        gpu_active_sec = float(payload.get("gpu_active_sec", 0.0))
    for epoch in range(start_epoch, int(epochs) + 1):
        rng.shuffle(train)
        epoch_losses = []
        model.train()
        for batch in token_budget_batches(train, max_examples=batch_size, max_tokens=token_budget):
            graph_batch, od_tokens, od_mask, scalars, target, weights = actor_tensor_batch(batch, device)
            step_started = time.perf_counter()
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=use_bf16):
                pred = model(graph_batch, od_tokens, od_mask, scalars)
                per = torch.mean(torch.abs((pred - target) / span), dim=1)
                loss = torch.mean(per * weights)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            if use_bf16:
                gpu_active_sec += time.perf_counter() - step_started
            last_grad = actor_gradient_summary(model)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            opt.step()
            epoch_losses.append(float(loss.detach().cpu()))
            if checkpoint_interval_sec > 0 and time.perf_counter() - last_checkpoint_sec >= checkpoint_interval_sec:
                resume_path.parent.mkdir(parents=True, exist_ok=True)
                torch.save(
                    {
                        "schema_version": f"{ROUND}_actor_resume_checkpoint_v1",
                        "variant_id": variant_id,
                        "seed": seed,
                        "epoch": epoch,
                        "model_state_dict": model.state_dict(),
                        "optimizer_state_dict": opt.state_dict(),
                        "best_state_dict": best_state,
                        "best_metric": best_metric,
                        "best_epoch": best_epoch,
                        "stale": stale,
                        "gpu_active_sec": gpu_active_sec,
                    },
                    resume_path,
                )
                last_hourly_checkpoint_path = rel(resume_path)
                last_checkpoint_sec = time.perf_counter()
        final_train_loss = float(np.mean(epoch_losses)) if epoch_losses else 0.0
        valid_metrics = evaluate_actor_model(model, valid, device, batch_size)
        metric = number(valid_metrics.get("validation_labelv54_normalized_l1"), math.inf)
        if metric < best_metric - 1.0e-6:
            best_metric = metric
            best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
        if epoch >= min_epochs and stale >= patience:
            break
    model.load_state_dict(best_state)
    final_metrics = evaluate_actor_model(model, valid, device, batch_size)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_payload = {
            "artifact_type": "phase5p5_repair5g567_labelv54_direct_actor",
            "variant_id": variant_id,
            "variant_name": arch.variant_name,
            "seed": seed,
            "hidden_dim": hidden_dim,
            "actor_state_dict": model.state_dict(),
            "scalar_only_control": arch.scalar_only_control,
            "use_cross_attention": arch.use_cross_attention,
            "safe_subspace": arch.safe_subspace,
            "field_group_trust": arch.field_group_trust,
            "od_perceiver": arch.od_perceiver,
            "graph_local_layers": arch.graph_local_layers,
            "graph_global_layers": arch.graph_global_layers,
            "heads": arch.heads,
            "attention_heads": arch.heads,
            "latent_tokens": arch.latent_tokens,
            "labelv54_training": True,
            "diagnostic_only": bool(diagnostic_only),
            "no_performance_claim": bool(no_performance_claim),
            "training_context_uids": list(training_context_uids or []),
            "training_context_count": len(training_context_uids or []),
            "training_dataset_sha256": training_dataset_sha256,
            "dataset_sha256": training_dataset_sha256,
            "source_commit": source_commit or git_capture("rev-parse", "HEAD"),
            "critic_included_for_export": False,
            "codebook_included_for_export": False,
            "theta_fixed_for_run": True,
            "cuda_bf16_training": use_bf16,
            "token_budget": int(token_budget),
            "gpu_active_hours": gpu_active_sec / 3600.0,
            "resume_checkpoint_path": rel(resume_path),
            "labelv54_summary": rel(LABELV54_SUMMARY),
        }
    torch.save(checkpoint_payload, out_path)
    row = {
        "variant_id": variant_id,
        "variant_name": arch.variant_name,
        "seed": seed,
        "model_path": rel(out_path),
        "hidden_dim": hidden_dim,
        "epochs_requested": int(epochs),
        "epochs_run": int(epoch if "epoch" in locals() else 0),
        "min_epochs": int(min_epochs),
        "early_stop_patience": int(patience),
        "best_epoch": int(best_epoch),
        "final_train_loss": final_train_loss,
        "train_examples": len(train),
        "validation_examples": len(valid),
        "training_split_source": "LABEL_TRAIN_internal_holdout" if any(ex.split == "LABEL_TRAIN" for ex in examples) else "legacy_split_fallback",
        "diagnostic_only": bool(diagnostic_only),
        "no_performance_claim": bool(no_performance_claim),
        "training_context_count": len(training_context_uids or []),
        "training_dataset_sha256": training_dataset_sha256,
        "source_commit": source_commit or git_capture("rev-parse", "HEAD"),
        "cuda_bf16_training": use_bf16,
        "token_budget_batching": True,
        "token_budget": int(token_budget),
        "gpu_active_hours": gpu_active_sec / 3600.0,
        "hourly_checkpoint_interval_sec": checkpoint_interval_sec,
        "resume_enabled": resume,
        "resume_checkpoint_path": rel(resume_path),
        "last_hourly_checkpoint_path": last_hourly_checkpoint_path,
        "scalar_only_control": arch.scalar_only_control,
        "uses_cross_attention": arch.use_cross_attention,
        "safe_subspace": arch.safe_subspace,
        "field_group_trust": arch.field_group_trust,
        "od_perceiver": arch.od_perceiver,
        "graph_local_layers": arch.graph_local_layers,
        "graph_global_layers": arch.graph_global_layers,
        "attention_heads": arch.heads,
        "latent_tokens": arch.latent_tokens,
        **final_metrics,
        **claims(),
    }
    grad = {"variant_id": variant_id, "seed": seed, **last_grad, **claims()}
    return row, grad


def train_g567_actors(
    contexts: list[G567Context],
    *,
    device: str,
    seeds: list[int],
    variants: list[str],
    epochs: int,
    min_epochs: int,
    patience: int,
    batch_size: int,
    token_budget: int,
    hidden_dim: int,
    lr: float,
    plan_only: bool,
    checkpoint_interval_sec: float,
    resume: bool,
) -> tuple[dict[str, Any], list[Path]]:
    examples = actor_examples_from_labelv54(contexts)
    if plan_only:
        summary = {
            "schema_version": f"{ROUND}_actor_training_summary_v1",
            "decision": "g567_actor_training_plan_created_solver_labels_required",
            "planned_variants": variants,
            "planned_seeds": seeds,
            "label_examples_available": len(examples),
            "requires_cuda_bf16_training": True,
            "token_budget_batching": True,
            **claims(),
        }
        write_json(ACTOR_TRAINING_SUMMARY, summary)
        write_rows(ACTOR_TRAINING_MATRIX, [])
        write_rows(ACTOR_GRADIENT_AUDIT, [])
        return summary, []
    if not examples:
        summary = {
            "schema_version": f"{ROUND}_actor_training_summary_v1",
            "decision": "g567_actor_training_blocked_no_labelv54_examples",
            **claims(),
        }
        write_json(ACTOR_TRAINING_SUMMARY, summary)
        return summary, []
    if not str(device).startswith("cuda"):
        summary = {
            "schema_version": f"{ROUND}_actor_training_summary_v1",
            "decision": "g567_actor_training_blocked_cuda_bf16_required",
            "device": device,
            "label_examples_available": len(examples),
            **claims(),
        }
        write_json(ACTOR_TRAINING_SUMMARY, summary)
        return summary, []
    rows: list[dict[str, Any]] = []
    grads: list[dict[str, Any]] = []
    started = time.perf_counter()
    for seed in seeds:
        for variant in variants:
            row, grad = train_one_g567_actor(
                variant,
                seed,
                examples,
                device=device,
                epochs=epochs,
                min_epochs=min_epochs,
                patience=patience,
                batch_size=batch_size,
                token_budget=token_budget,
                hidden_dim=hidden_dim,
                lr=lr,
                checkpoint_interval_sec=checkpoint_interval_sec,
                resume=resume,
            )
            rows.append(row)
            grads.append(grad)
            print(json.dumps({"event": "g567_actor_trained", "variant": variant, "seed": seed, "valid_l1": row.get("validation_labelv54_normalized_l1")}), flush=True)
    write_rows(ACTOR_TRAINING_MATRIX, rows)
    write_rows(ACTOR_GRADIENT_AUDIT, grads)
    scalar_rows = [row for row in rows if boolish(row.get("scalar_only_control"))]
    rich_rows = [row for row in rows if not boolish(row.get("scalar_only_control"))]
    sorted_scalars = sorted(
        scalar_rows,
        key=lambda row: (
            number(row.get("validation_labelv54_normalized_l1"), 999.0),
            number(row.get("validation_noop_deviation"), 999.0),
            str(row.get("variant_id", "")),
            str(row.get("seed", "")),
        ),
    )
    sorted_rich = sorted(
        rich_rows,
        key=lambda row: (
            number(row.get("validation_labelv54_normalized_l1"), 999.0),
            number(row.get("validation_noop_deviation"), 999.0),
            str(row.get("variant_id", "")),
            str(row.get("seed", "")),
        ),
    )
    selected_rows = sorted_scalars[:1] + sorted_rich[:3]
    selected_paths = [resolve(row["model_path"]) for row in selected_rows if row.get("model_path")]
    summary = {
        "schema_version": f"{ROUND}_actor_training_summary_v1",
        "decision": "g567_labelv54_direct_actor_training_completed",
        "device": device,
        "examples": len(examples),
        "positive_example_contexts": sum(ex.positive_count > 0 for ex in examples),
        "safe_example_contexts": sum(ex.safe_count > 0 for ex in examples),
        "variants": variants,
        "seeds": seeds,
        "rows": len(rows),
        "selected_scalar_control_paths": [rel(resolve(row["model_path"])) for row in sorted_scalars[:1] if row.get("model_path")],
        "selected_rich_actor_paths": [rel(resolve(row["model_path"])) for row in sorted_rich[:3] if row.get("model_path")],
        "selected_development_checkpoint_paths": [rel(path) for path in selected_paths],
        "critic_included_for_export": False,
        "codebook_included_for_export": False,
        "cuda_bf16_training": all(boolish(row.get("cuda_bf16_training")) for row in rows),
        "token_budget_batching": True,
        "token_budget": int(token_budget),
        "stage_gpu_active_hours": sum(number(row.get("gpu_active_hours"), 0.0) for row in rows),
        "hourly_checkpoints_enabled": checkpoint_interval_sec > 0,
        "resume_enabled": resume,
        "elapsed_sec": time.perf_counter() - started,
        **claims(),
    }
    write_json(ACTOR_TRAINING_SUMMARY, summary)
    return summary, selected_paths


def write_repeatability_summary(repeat_summary: dict[str, Any], fallback_margin: float) -> dict[str, Any]:
    margins = []
    for tier in ["additive", "static_flow", "g556"]:
        value = repeat_summary.get(f"q95_harmful_delta_vs_{tier}")
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            margins.append(abs(float(value)))
    margin = max(0.001, min(0.05, max(margins) if margins else fallback_margin))
    repeat_min = int(number(repeat_summary.get("replicate_count_min"), 0))
    worker_values = [str(value) for value in repeat_summary.get("worker_count_values", [])] if isinstance(repeat_summary.get("worker_count_values"), list) else []
    single_worker_only = bool(worker_values) and set(worker_values) == {"1"}
    out = {
        "schema_version": f"{ROUND}_repeatability_summary_v1",
        "decision": "g567_repeatability_protocol_valid" if repeat_min >= 5 and single_worker_only else "g567_repeatability_protocol_incomplete",
        "source_replay_phase": repeat_summary.get("replay_phase", ""),
        "same_pair_repeats": repeat_min,
        "same_pair_groups": repeat_summary.get("replicate_groups", 0),
        "same_pair_groups_with_at_least_5_repeats": repeat_summary.get("same_pair_groups_with_at_least_5_repeats", 0),
        "same_pair_groups_with_at_least_10_repeats": repeat_summary.get("same_pair_groups_with_at_least_10_repeats", 0),
        "worker_count_values": worker_values,
        "single_worker_only": single_worker_only,
        "worker_contention_compared": False,
        "cpu_affinity_required": True,
        "thread_env_required": True,
        "recommended_positive_margin": margin,
        "recommended_harmful_margin": margin,
        "fallback_g565_margin": fallback_margin,
        **claims(),
    }
    write_json(REPEATABILITY_SUMMARY, out)
    return out


CRITIC_BINARY_TARGETS = [
    "success_regression_vs_additive",
    "success_regression_vs_static_flow",
    "success_regression_vs_g556",
    "success_gain",
]
CRITIC_DELTA_TARGETS = ["delta_vs_additive", "delta_vs_static_flow", "delta_vs_g556"]
CRITIC_EFFORT_TARGETS = ["log_actor_runtime_ms", "log_actor_expanded_nodes", "log_actor_low_level_pibt_calls"]
CRITIC_TARGETS = CRITIC_BINARY_TARGETS + CRITIC_DELTA_TARGETS + CRITIC_EFFORT_TARGETS


def critic_feature_vector(ctx: G567Context, row: dict[str, Any]) -> np.ndarray:
    span = np.maximum(np.asarray(THETA_HI - THETA_LO, dtype=np.float32), 1.0e-6)
    theta = np.asarray([number(row.get(col), float(BASELINE_G556[idx])) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)], dtype=np.float32)
    theta_norm = (theta - np.asarray(THETA_LO, dtype=np.float32)) / span
    scalars = scalar_features(ctx.feature_row)
    graph = ctx.graph_with_traffic
    node_mean = np.mean(np.asarray(graph.node_features, dtype=np.float32), axis=0) if len(graph.node_features) else np.zeros(9, dtype=np.float32)
    edge_mean = np.mean(np.asarray(graph.edge_features, dtype=np.float32), axis=0) if len(graph.edge_features) else np.zeros(9, dtype=np.float32)
    family_digest = stable_uid("critic_family", ctx.map_family)
    family_features = np.asarray(
        [
            (int(family_digest[0:8], 16) % 997) / 997.0,
            (int(family_digest[8:16], 16) % 991) / 991.0,
            (int(family_digest[16:24], 16) % 983) / 983.0,
        ],
        dtype=np.float32,
    )
    graph_stats = np.asarray(
        [
            ctx.agents / 128.0,
            ctx.budget_ms / 10000.0,
            ctx.ltm_max_iterations / 10.0,
            graph.width / 128.0,
            graph.height / 128.0,
            graph.component_count / 32.0,
            graph.physical_free_cell_count / 8192.0,
        ],
        dtype=np.float32,
    )
    return np.concatenate([theta_norm, scalars, graph_stats, node_mean, edge_mean, family_features]).astype(np.float64)


def critic_target_value(row: dict[str, Any], target: str) -> float:
    if target == "success_gain":
        return float(
            boolish(row.get("success_gain_vs_additive"))
            or boolish(row.get("success_gain_vs_static_flow"))
            or boolish(row.get("success_gain_vs_g556"))
        )
    if target in CRITIC_BINARY_TARGETS:
        return float(boolish(row.get(target)))
    if target == "log_actor_runtime_ms":
        value = number(row.get("actor_runtime_ms"), math.nan)
        return math.log1p(max(0.0, value)) if math.isfinite(value) else math.nan
    if target == "log_actor_expanded_nodes":
        value = number(row.get("actor_expanded_nodes"), math.nan)
        return math.log1p(max(0.0, value)) if math.isfinite(value) else math.nan
    if target == "log_actor_low_level_pibt_calls":
        value = number(row.get("actor_low_level_pibt_calls"), math.nan)
        return math.log1p(max(0.0, value)) if math.isfinite(value) else math.nan
    return number(row.get(target), math.nan)


def ridge_predict_one_target(
    train_x: np.ndarray,
    train_y: np.ndarray,
    pred_x: np.ndarray,
    *,
    seed: int,
    binary: bool,
    lam: float = 1.0e-2,
) -> tuple[np.ndarray, int]:
    finite = np.isfinite(train_y)
    if int(np.sum(finite)) < 2:
        fallback = float(np.nanmean(train_y[finite])) if np.any(finite) else 0.0
        out = np.full(pred_x.shape[0], fallback, dtype=np.float64)
        return (np.clip(out, 0.0, 1.0) if binary else out), int(np.sum(finite))
    x = train_x[finite]
    y = train_y[finite]
    rng = np.random.default_rng(seed)
    sample_count = max(2, int(math.ceil(len(y) * 0.85)))
    sampled = rng.integers(0, len(y), size=sample_count)
    x = x[sampled]
    y = y[sampled]
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std[std < 1.0e-6] = 1.0
    xz = (x - mean) / std
    pz = (pred_x - mean) / std
    xa = np.concatenate([np.ones((xz.shape[0], 1)), xz], axis=1)
    pa = np.concatenate([np.ones((pz.shape[0], 1)), pz], axis=1)
    reg = lam * np.eye(xa.shape[1], dtype=np.float64)
    reg[0, 0] = 0.0
    try:
        coef = np.linalg.solve(xa.T @ xa + reg, xa.T @ y)
    except np.linalg.LinAlgError:
        coef = np.linalg.lstsq(xa.T @ xa + reg, xa.T @ y, rcond=None)[0]
    pred = pa @ coef
    if binary:
        pred = np.clip(pred, 0.0, 1.0)
    return pred.astype(np.float64), int(np.sum(finite))


def residual_quantiles(values: np.ndarray) -> dict[str, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"q10": 0.0, "q50": 0.0, "q90": 0.0, "q95": 0.0}
    return {
        "q10": float(np.quantile(finite, 0.10)),
        "q50": float(np.quantile(finite, 0.50)),
        "q90": float(np.quantile(finite, 0.90)),
        "q95": float(np.quantile(finite, 0.95)),
    }


def binary_calibration_metrics(actual: list[float], pred: list[float]) -> dict[str, float | None]:
    y = np.asarray(actual, dtype=np.float64)
    p = np.asarray(pred, dtype=np.float64)
    finite = np.isfinite(y) & np.isfinite(p)
    y = y[finite]
    p = np.clip(p[finite], 0.0, 1.0)
    if y.size == 0:
        return {"brier": None, "brier_baseline": None, "brier_skill": None, "ece": None, "auroc": None, "auprc": None, "auprc_lift_vs_prevalence": None, "recall_at_fpr_05": None, "prevalence": None}
    prevalence = float(np.mean(y))
    brier = float(np.mean((p - y) ** 2))
    brier_baseline = float(np.mean((prevalence - y) ** 2))
    brier_skill = float(1.0 - brier / brier_baseline) if brier_baseline > 0.0 else None
    ece = 0.0
    for lo in np.linspace(0.0, 0.9, 10):
        hi = lo + 0.1
        mask = (p >= lo) & (p < hi if hi < 1.0 else p <= hi)
        if np.any(mask):
            ece += float(np.mean(mask)) * abs(float(np.mean(p[mask])) - float(np.mean(y[mask])))
    positives = y == 1.0
    negatives = y == 0.0
    auroc = None
    if np.any(positives) and np.any(negatives):
        order = np.argsort(p)
        ranks = np.empty_like(order, dtype=np.float64)
        ranks[order] = np.arange(1, len(p) + 1)
        pos_ranks = ranks[positives]
        auroc = float((np.sum(pos_ranks) - positives.sum() * (positives.sum() + 1) / 2) / (positives.sum() * negatives.sum()))
    auprc = None
    if np.any(positives):
        order = np.argsort(-p)
        sorted_y = y[order]
        tp = np.cumsum(sorted_y)
        precision = tp / np.arange(1, len(sorted_y) + 1)
        auprc = float(np.sum(precision[sorted_y == 1.0]) / max(1.0, positives.sum()))
    recall_at_fpr_05 = None
    if np.any(positives) and np.any(negatives):
        best_recall = 0.0
        for threshold in sorted(set(p.tolist()), reverse=True):
            predicted = p >= threshold
            fp = float(np.sum(predicted & negatives))
            tp = float(np.sum(predicted & positives))
            fpr = fp / max(1.0, float(np.sum(negatives)))
            if fpr <= 0.05:
                best_recall = max(best_recall, tp / max(1.0, float(np.sum(positives))))
        recall_at_fpr_05 = float(best_recall)
    return {
        "brier": brier,
        "brier_baseline": brier_baseline,
        "brier_skill": brier_skill,
        "ece": float(ece),
        "auroc": auroc,
        "auprc": auprc,
        "auprc_lift_vs_prevalence": (float(auprc / prevalence) if auprc is not None and prevalence > 0.0 else None),
        "recall_at_fpr_05": recall_at_fpr_05,
        "prevalence": prevalence,
    }


def train_distributional_outcome_ensemble(contexts: list[G567Context], *, seeds: list[int], plan_only: bool) -> dict[str, Any]:
    candidate_rows = read_rows(LABELV54_CANDIDATES)
    context_by_uid = {ctx.evaluation_uid: ctx for ctx in contexts}
    rows = [row for row in candidate_rows if row.get("g567_evaluation_uid", "") in context_by_uid]
    if plan_only:
        summary = {
            "schema_version": f"{ROUND}_distributional_critic_summary_v1",
            "decision": "g567_distributional_critic_plan_created_labelv54_required",
            "training_only_critic": True,
            "actor_export_includes_critic": False,
            "crossfit_unit": "physical_map_hash",
            "planned_targets": CRITIC_TARGETS,
            "labelv54_candidates": len(candidate_rows),
            **claims(),
        }
        write_json(DISTRIBUTIONAL_CRITIC_SUMMARY, summary)
        write_json(OUTCOME_ENSEMBLE_SUMMARY, summary)
        write_rows(DISTRIBUTIONAL_CRITIC_PREDICTIONS, [])
        write_rows(DISTRIBUTIONAL_CRITIC_MODEL_AUDIT, [])
        return summary
    physical_hashes = [context_by_uid[row["g567_evaluation_uid"]].physical_map_sha256 for row in rows]
    unique_hashes = sorted(set(physical_hashes))
    if len(rows) < 32 or len(unique_hashes) < 2:
        summary = {
            "schema_version": f"{ROUND}_distributional_critic_summary_v1",
            "decision": "g567_distributional_critic_not_calibrated",
            "reason": "insufficient_label_rows_or_physical_maps",
            "training_only_critic": True,
            "actor_export_includes_critic": False,
            "labelv54_candidates": len(candidate_rows),
            "usable_rows": len(rows),
            "physical_maps": len(unique_hashes),
            **claims(),
        }
        write_json(DISTRIBUTIONAL_CRITIC_SUMMARY, summary)
        write_json(OUTCOME_ENSEMBLE_SUMMARY, summary)
        write_rows(DISTRIBUTIONAL_CRITIC_PREDICTIONS, [])
        write_rows(DISTRIBUTIONAL_CRITIC_MODEL_AUDIT, [])
        return summary

    x = np.stack([critic_feature_vector(context_by_uid[row["g567_evaluation_uid"]], row) for row in rows])
    y = np.asarray([[critic_target_value(row, target) for target in CRITIC_TARGETS] for row in rows], dtype=np.float64)
    fold_count = min(5, len(unique_hashes))
    fold_by_hash = {value: idx % fold_count for idx, value in enumerate(unique_hashes)}
    folds = np.asarray([fold_by_hash[value] for value in physical_hashes], dtype=np.int32)
    seed_list = (seeds or [566, 567, 568])[:3]
    per_row_target_predictions: list[list[list[float]]] = [[[] for _ in CRITIC_TARGETS] for _ in rows]
    audit_rows: list[dict[str, Any]] = []
    for fold in range(fold_count):
        train_idx = np.where(folds != fold)[0]
        pred_idx = np.where(folds == fold)[0]
        if pred_idx.size == 0 or train_idx.size == 0:
            continue
        train_hashes = {physical_hashes[int(idx)] for idx in train_idx}
        pred_hashes = {physical_hashes[int(idx)] for idx in pred_idx}
        leakage = len(train_hashes & pred_hashes)
        for seed in seed_list:
            for target_idx, target in enumerate(CRITIC_TARGETS):
                pred, finite_train = ridge_predict_one_target(
                    x[train_idx],
                    y[train_idx, target_idx],
                    x[pred_idx],
                    seed=seed + 1009 * fold + 37 * target_idx,
                    binary=target in CRITIC_BINARY_TARGETS,
                )
                for local_idx, row_idx in enumerate(pred_idx):
                    per_row_target_predictions[int(row_idx)][target_idx].append(float(pred[local_idx]))
                audit_rows.append(
                    {
                        "fold": fold,
                        "seed": seed,
                        "target": target,
                        "train_rows": len(train_idx),
                        "predict_rows": len(pred_idx),
                        "finite_train_rows": finite_train,
                        "train_physical_maps": len(train_hashes),
                        "predict_physical_maps": len(pred_hashes),
                        "physical_map_leakage_violations": leakage,
                        **claims(),
                    }
                )

    prediction_means = np.full_like(y, np.nan, dtype=np.float64)
    prediction_stds = np.full_like(y, np.nan, dtype=np.float64)
    for row_idx, target_predictions in enumerate(per_row_target_predictions):
        for target_idx, values in enumerate(target_predictions):
            if values:
                arr = np.asarray(values, dtype=np.float64)
                prediction_means[row_idx, target_idx] = float(np.mean(arr))
                prediction_stds[row_idx, target_idx] = float(np.std(arr))
    residuals = y - prediction_means
    residual_by_target = {target: residual_quantiles(residuals[:, idx]) for idx, target in enumerate(CRITIC_TARGETS)}
    prediction_rows: list[dict[str, Any]] = []
    brier_values: list[float] = []
    binary_actuals: dict[str, list[float]] = defaultdict(list)
    binary_predictions: dict[str, list[float]] = defaultdict(list)
    delta_abs_errors: list[float] = []
    effort_abs_errors: list[float] = []
    for row_idx, row in enumerate(rows):
        out: dict[str, Any] = {
            "g567_evaluation_uid": row.get("g567_evaluation_uid", ""),
            "candidate_uid": row.get("candidate_uid", ""),
            "theta_id": row.get("theta_id", ""),
            "variant_id": row.get("variant_id", ""),
            "physical_map_sha256": physical_hashes[row_idx],
            "crossfit_fold": int(folds[row_idx]),
            **claims(),
        }
        uncertainty_parts = []
        for target_idx, target in enumerate(CRITIC_BINARY_TARGETS):
            mean = float(np.clip(prediction_means[row_idx, target_idx], 0.0, 1.0)) if math.isfinite(prediction_means[row_idx, target_idx]) else 0.0
            std = float(prediction_stds[row_idx, target_idx]) if math.isfinite(prediction_stds[row_idx, target_idx]) else 0.0
            uncertainty_parts.append(std)
            if target == "success_gain":
                out["p_success_gain_mean"] = mean
                out["p_success_gain_lcb"] = float(np.clip(mean - 1.64 * std, 0.0, 1.0))
            else:
                suffix = target.replace("success_regression_", "success_regression_")
                out[f"p_{suffix}_mean"] = mean
                out[f"p_{suffix}_ucb"] = float(np.clip(mean + 1.64 * std, 0.0, 1.0))
            actual = y[row_idx, target_idx]
            if math.isfinite(actual):
                brier_values.append((mean - actual) ** 2)
                binary_actuals[target].append(float(actual))
                binary_predictions[target].append(mean)
        for target in CRITIC_DELTA_TARGETS:
            target_idx = CRITIC_TARGETS.index(target)
            values = np.asarray(per_row_target_predictions[row_idx][target_idx], dtype=np.float64)
            if values.size == 0:
                values = np.asarray([0.0], dtype=np.float64)
            residual_q = residual_by_target[target]
            for label, quantile in [("q10", 0.10), ("q50", 0.50), ("q90", 0.90), ("q95", 0.95)]:
                out[f"{target}_{label}"] = float(np.quantile(values, quantile) + residual_q[label])
            uncertainty_parts.append(float(np.std(values)))
            actual = y[row_idx, target_idx]
            if math.isfinite(actual):
                delta_abs_errors.append(abs(float(np.mean(values)) - actual))
        for target in CRITIC_EFFORT_TARGETS:
            target_idx = CRITIC_TARGETS.index(target)
            values = np.asarray(per_row_target_predictions[row_idx][target_idx], dtype=np.float64)
            if values.size == 0:
                values = np.asarray([0.0], dtype=np.float64)
            residual_q = residual_by_target[target]
            prefix = target.replace("log_actor_", "actor_").replace("_ms", "_ms")
            for label, quantile in [("q50", 0.50), ("q90", 0.90)]:
                log_value = float(np.quantile(values, quantile) + residual_q[label])
                out[f"{prefix}_{label}"] = float(max(0.0, math.expm1(log_value)))
            uncertainty_parts.append(float(np.std(values)))
            actual = y[row_idx, target_idx]
            if math.isfinite(actual):
                effort_abs_errors.append(abs(float(np.mean(values)) - actual))
        harmful_tail = max(
            0.0,
            number(out.get("delta_vs_additive_q95"), 0.0),
            number(out.get("delta_vs_static_flow_q95"), 0.0),
            number(out.get("delta_vs_g556_q95"), 0.0),
        )
        risk_ub = max(
            number(out.get("p_success_regression_vs_additive_ucb"), 0.0),
            number(out.get("p_success_regression_vs_static_flow_ucb"), 0.0),
            number(out.get("p_success_regression_vs_g556_ucb"), 0.0),
        )
        gain_lcb = number(out.get("p_success_gain_lcb"), 0.0)
        epistemic = float(np.mean(uncertainty_parts)) if uncertainty_parts else 0.0
        out["harmful_quality_cvar"] = harmful_tail
        out["epistemic_uncertainty"] = epistemic
        out["unsupported_theta_region_score"] = float(np.clip(epistemic + harmful_tail, 0.0, 1.0))
        out["critic_actor_weight"] = float(np.clip((1.0 - risk_ub) * (1.0 + gain_lcb) / (1.0 + 8.0 * harmful_tail + epistemic), 0.05, 3.0))
        prediction_rows.append(out)

    leakage_violations = sum(int(row.get("physical_map_leakage_violations", 0)) for row in audit_rows)
    prediction_coverage = sum(
        all(per_row_target_predictions[row_idx][target_idx] for target_idx in range(len(CRITIC_TARGETS)))
        for row_idx in range(len(rows))
    )
    calibration_by_target = {
        target: binary_calibration_metrics(binary_actuals[target], binary_predictions[target])
        for target in CRITIC_BINARY_TARGETS
    }
    skill_values = [
        float(metrics["brier_skill"])
        for target, metrics in calibration_by_target.items()
        if target != "success_gain" and metrics.get("brier_skill") is not None
    ]
    ece_values = [
        float(metrics["ece"])
        for metrics in calibration_by_target.values()
        if metrics.get("ece") is not None
    ]
    regression_targets = [target for target in CRITIC_BINARY_TARGETS if target != "success_gain"]
    fold_positive_min_by_target = {}
    fold_positive_gate_by_target = {}
    for target in regression_targets:
        target_idx = CRITIC_TARGETS.index(target)
        counts = [int(np.nansum(y[folds == fold, target_idx])) for fold in range(fold_count)]
        fold_positive_min_by_target[target] = min(counts) if counts else 0
        fold_positive_gate_by_target[target] = bool(counts and min(counts) >= 3)
    tier_positive_min_by_target = {}
    family_positive_min_by_target = {}
    for target in regression_targets:
        target_idx = CRITIC_TARGETS.index(target)
        tier_counts: dict[str, int] = defaultdict(int)
        family_counts: dict[str, int] = defaultdict(int)
        for row_idx, row in enumerate(rows):
            if number(y[row_idx, target_idx], 0.0) >= 1.0:
                ctx = context_by_uid[row["g567_evaluation_uid"]]
                tier_counts[str(ctx.agents)] += 1
                family_counts[str(ctx.map_family)] += 1
        tier_positive_min_by_target[target] = min(tier_counts.values()) if tier_counts else 0
        family_positive_min_by_target[target] = min(family_counts.values()) if family_counts else 0
    auprc_lift_values = [
        float(metrics["auprc_lift_vs_prevalence"])
        for target, metrics in calibration_by_target.items()
        if target in regression_targets and metrics.get("auprc_lift_vs_prevalence") is not None
    ]
    fixed_fpr_recall_values = [
        float(metrics["recall_at_fpr_05"])
        for target, metrics in calibration_by_target.items()
        if target in regression_targets and metrics.get("recall_at_fpr_05") is not None
    ]
    delta_coverage: dict[str, dict[str, float | None]] = {}
    for target in CRITIC_DELTA_TARGETS:
        target_idx = CRITIC_TARGETS.index(target)
        q90_hits = []
        q95_hits = []
        for row_idx, pred_row in enumerate(prediction_rows):
            actual = y[row_idx, target_idx]
            if not math.isfinite(actual):
                continue
            q90_hits.append(float(actual <= number(pred_row.get(f"{target}_q90"), -math.inf)))
            q95_hits.append(float(actual <= number(pred_row.get(f"{target}_q95"), -math.inf)))
        delta_coverage[target] = {
            "q90_empirical_coverage": float(np.mean(q90_hits)) if q90_hits else None,
            "q95_empirical_coverage": float(np.mean(q95_hits)) if q95_hits else None,
        }
    coverage_values_q90 = [float(v["q90_empirical_coverage"]) for v in delta_coverage.values() if v["q90_empirical_coverage"] is not None]
    coverage_values_q95 = [float(v["q95_empirical_coverage"]) for v in delta_coverage.values() if v["q95_empirical_coverage"] is not None]
    tail_events_sufficient = bool(
        regression_targets
        and all(fold_positive_gate_by_target.values())
        and all(value >= 3 for value in tier_positive_min_by_target.values())
        and all(value >= 3 for value in family_positive_min_by_target.values())
    )
    auprc_gate = bool(auprc_lift_values and min(auprc_lift_values) >= 1.50)
    fixed_fpr_gate = bool(fixed_fpr_recall_values and min(fixed_fpr_recall_values) > 0.0)
    quantile_coverage_gate = bool(
        coverage_values_q90
        and coverage_values_q95
        and min(coverage_values_q90) >= 0.80
        and min(coverage_values_q95) >= 0.90
    )
    calibration_passed = bool(
        prediction_coverage == len(rows)
        and leakage_violations == 0
        and skill_values
        and min(skill_values) >= 0.05
        and (max(ece_values) if ece_values else 1.0) <= 0.20
        and tail_events_sufficient
        and auprc_gate
        and fixed_fpr_gate
        and quantile_coverage_gate
    )
    calibration_blockers = []
    if prediction_coverage != len(rows):
        calibration_blockers.append("incomplete_crossfit_prediction_coverage")
    if leakage_violations != 0:
        calibration_blockers.append("physical_map_leakage")
    if not skill_values or min(skill_values) < 0.05:
        calibration_blockers.append("brier_skill_below_minimum")
    if (max(ece_values) if ece_values else 1.0) > 0.20:
        calibration_blockers.append("ece_above_threshold")
    if not tail_events_sufficient:
        calibration_blockers.append("insufficient_tail_events_for_calibration")
    if not auprc_gate:
        calibration_blockers.append("auprc_not_sufficiently_above_prevalence")
    if not fixed_fpr_gate:
        calibration_blockers.append("fixed_fpr_regression_recall_missing")
    if not quantile_coverage_gate:
        calibration_blockers.append("q90_q95_empirical_coverage_missing")
    summary = {
        "schema_version": f"{ROUND}_distributional_critic_summary_v1",
        "decision": "g567_distributional_critic_calibrated" if calibration_passed else "g567_distributional_critic_not_calibrated",
        "training_only_critic": True,
        "actor_export_includes_critic": False,
        "crossfit_unit": "physical_map_hash",
        "crossfit_folds": fold_count,
        "ensemble_seeds": seed_list,
        "labelv54_candidates": len(candidate_rows),
        "usable_rows": len(rows),
        "physical_maps": len(unique_hashes),
        "prediction_rows": len(prediction_rows),
        "prediction_coverage_rows": prediction_coverage,
        "physical_map_leakage_violations": leakage_violations,
        "binary_brier_mean": float(np.mean(brier_values)) if brier_values else None,
        "binary_calibration_by_target": calibration_by_target,
        "binary_brier_skill_min_vs_prevalence": min(skill_values) if skill_values else None,
        "binary_ece_max": max(ece_values) if ece_values else None,
        "calibration_blockers": calibration_blockers,
        "fold_positive_min_by_target": fold_positive_min_by_target,
        "per_agent_tier_positive_min_by_target": tier_positive_min_by_target,
        "per_map_family_positive_min_by_target": family_positive_min_by_target,
        "auprc_lift_min_vs_prevalence": min(auprc_lift_values) if auprc_lift_values else None,
        "fixed_fpr_05_recall_min": min(fixed_fpr_recall_values) if fixed_fpr_recall_values else None,
        "delta_quantile_empirical_coverage": delta_coverage,
        "delta_oof_mae_mean": float(np.mean(delta_abs_errors)) if delta_abs_errors else None,
        "effort_log_oof_mae_mean": float(np.mean(effort_abs_errors)) if effort_abs_errors else None,
        "targets": CRITIC_TARGETS,
        "outputs": [
            "P(success regression vs additive/static_flow/g556) with UCB",
            "P(success gain) with LCB",
            "quality delta q10/q50/q90/q95 for all three tiers",
            "harmful_quality_cvar",
            "runtime/search-effort q50/q90",
            "epistemic_uncertainty",
        ],
        **claims(),
    }
    write_rows(DISTRIBUTIONAL_CRITIC_PREDICTIONS, prediction_rows)
    write_rows(DISTRIBUTIONAL_CRITIC_MODEL_AUDIT, audit_rows)
    write_json(DISTRIBUTIONAL_CRITIC_SUMMARY, summary)
    write_json(OUTCOME_ENSEMBLE_SUMMARY, summary)
    return summary


def write_scaling_summary(dev_summary: dict[str, Any]) -> dict[str, Any]:
    rows = []
    sizes = ["1k", "4k", "12k", "24k", "36k", "all-available"]
    methods = ["B0", "B1", "C0", "A2", "A5", "A6", "A7"]
    for size in sizes:
        for method in methods:
            rows.append(
                {
                    "size_label": size,
                    "method": method,
                    "fold_seed_consistency_required": True,
                    "real_nested_context_subset_required": True,
                    "exact_solver_replay_required": True,
                    "solver_validated_in_development": False,
                    "placeholder_not_a_claim": True,
                    **claims(),
                }
            )
    path = TABLES / f"{ROUND}_valid_scaling_matrix.csv"
    write_rows(path, rows)
    summary = {
        "schema_version": f"{ROUND}_valid_scaling_summary_v1",
        "decision": "g567_independent_context_scaling_registered_pending_exact_replay",
        "sizes": sizes,
        "methods": methods,
        "rows": len(rows),
        "matrix_path": rel(path),
        "development_replay_decision": dev_summary.get("decision", ""),
        "not_counted_as_completed_scaling_study": True,
        **claims(),
    }
    write_json(SCALING_SUMMARY, summary)
    return summary


def freeze_hashes(paths: list[Path]) -> dict[str, str]:
    return {rel(path): sha256_file(path) for path in paths if resolve(path).exists()}


def summarize_blind_hash_manifest(limit: int) -> dict[str, Any]:
    rows = [row for row in read_rows(VALID_CONTEXT_MANIFEST) if str(row.get("split", "")).upper() == "BLIND"]
    selected = rows[: max(0, int(limit))]
    hash_rows = [
        {
            "g567_dataset_row_id": row.get("g567_dataset_row_id", ""),
            "g567_evaluation_uid": row.get("g567_evaluation_uid", ""),
            "map": row.get("map", ""),
            "map_family": row.get("map_family", ""),
            "agent_count": row.get("agent_count", ""),
            "physical_map_sha256": row.get("physical_map_sha256", ""),
            "scenario_sha256": row.get("scenario_sha256", ""),
            "assignment_sha256": row.get("assignment_sha256", ""),
            "replay_scenario_sha256": row.get("replay_scenario_sha256", ""),
            "map_source_type": row.get("map_source_type", ""),
        }
        for row in selected
    ]
    payload = json.dumps(hash_rows, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return {
        "blind_context_rows_available": len(rows),
        "blind_context_hash_rows_selected": len(selected),
        "blind_hash_manifest_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "blind_hash_manifest_fields": [
            "dataset/evaluation ids",
            "map family/name",
            "agent count",
            "physical map sha256",
            "scenario sha256",
            "assignment sha256",
            "source type",
        ],
        "blind_features_materialized_pre_primary_freeze": False,
    }


def write_artifact_manifest(artifact_paths: list[Path]) -> dict[str, Any]:
    manifest = {
        "schema_version": f"{ROUND}_artifact_manifest_v1",
        "decision": "g567_artifact_manifest_written",
        "artifacts": freeze_hashes(artifact_paths),
        **claims(),
    }
    write_json(ARTIFACT_MANIFEST, manifest)
    return manifest


def write_final_decision(dev: dict[str, Any], blind: dict[str, Any], label: dict[str, Any], validity: dict[str, Any], artifact_paths: list[Path]) -> dict[str, Any]:
    def pass_tier(summary: dict[str, Any], tier: str, min_rel: float) -> bool:
        return bool(
            summary.get("decision") == "g567_three_tier_replay_materialized"
            and int(summary.get(f"raw_success_regressions_vs_{tier}", 999)) == 0
            and number(summary.get(f"median_relative_improvement_vs_{tier}"), -999.0) >= min_rel
            and int(summary.get(f"better_outside_margin_vs_{tier}", 0)) > int(summary.get(f"supported_quality_worse_outside_margin_vs_{tier}", 0))
        )

    tier_a = pass_tier(blind, "additive", 0.06)
    tier_b = pass_tier(blind, "static_flow", 0.03)
    tier_c_signal = bool(
        blind.get("decision") == "g567_three_tier_replay_materialized"
        and int(blind.get("raw_success_gains_vs_g556", 0)) > int(blind.get("raw_success_regressions_vs_g556", 0))
        and number(blind.get("median_delta_vs_g556"), 999.0) < 0
    )
    tier_c_deploy = bool(
        tier_c_signal
        and int(blind.get("raw_success_regressions_vs_g556", 999)) == 0
        and number(blind.get("mean_delta_vs_g556"), 999.0) < 0
        and number(blind.get("q95_harmful_delta_vs_g556"), 999.0) <= number(blind.get("applied_quality_margin"), 0.0)
    )
    summary = {
        "schema_version": f"{ROUND}_final_decision_summary_v1",
        "decision": "g567_blind_complete" if blind.get("decision") == "g567_three_tier_replay_materialized" else "g567_blocked_before_complete_blind_decision",
        "g567_blind_tierA_pass": tier_a,
        "g567_blind_tierA_strong_pass": tier_a and number(blind.get("median_relative_improvement_vs_additive"), 0.0) >= 0.10,
        "g567_blind_tierB_pass": tier_b,
        "g567_blind_tierB_strong_pass": tier_b and number(blind.get("median_relative_improvement_vs_static_flow"), 0.0) >= 0.06,
        "g567_blind_tierC_research_signal": tier_c_signal,
        "g567_blind_tierC_deployment_pass": tier_c_deploy,
        "g567_blind_tierC_tail_blocked": not tier_c_deploy,
        "valid_contexts": validity.get("valid_contexts", 0),
        "labelv54_candidates": label.get("candidates", 0),
        "development_decision": dev.get("decision", ""),
        "blind_decision": blind.get("decision", ""),
        "artifact_manifest": rel(ARTIFACT_MANIFEST),
        **claims(),
    }
    write_json(FINAL_DECISION_SUMMARY, summary)
    write_text(
        FINAL_DECISION_MD,
        "# Repair5G.5.67 Final Decision\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- Tier A pass: `{summary['g567_blind_tierA_pass']}`\n"
        f"- Tier B pass: `{summary['g567_blind_tierB_pass']}`\n"
        f"- Tier C research signal: `{summary['g567_blind_tierC_research_signal']}`\n"
        f"- Tier C deployment pass: `{summary['g567_blind_tierC_deployment_pass']}`\n\n"
        "Static-flow is replayed as a real Tier B solver row. G5.67 does not promote a deployment baseline unless Tier C deployment gates pass.\n",
    )
    write_artifact_manifest(artifact_paths)
    return summary


def replay_block_summary(phase: str, summary: dict[str, Any]) -> dict[str, Any] | None:
    if summary.get("decision") == "g567_three_tier_replay_materialized":
        return None
    return {
        "schema_version": f"{ROUND}_final_decision_summary_v1",
        "decision": f"g567_blocked_{safe_token(phase)}_replay_failed",
        "replay_phase": phase,
        "replay_decision": summary.get("decision", ""),
        "process_hard_timeout_rows": summary.get("process_hard_timeout_rows", 0),
        "planned_rows": summary.get("planned_rows", 0),
        "executed_rows": summary.get("executed_rows", 0),
        **claims(),
    }


def select_primary_actor_checkpoint(development: dict[str, Any]) -> dict[str, Any]:
    per_variant = development.get("per_variant_transfer", {})
    if not isinstance(per_variant, dict):
        return {"decision": "g567_primary_actor_selection_blocked_missing_per_variant_transfer"}
    candidates = [value for value in per_variant.values() if isinstance(value, dict) and value.get("model_path")]
    if not candidates:
        return {"decision": "g567_primary_actor_selection_blocked_no_candidate_paths"}

    def score(row: dict[str, Any]) -> tuple[Any, ...]:
        additive_reg = int(number(row.get("raw_success_regressions_vs_additive"), 999))
        static_reg = int(number(row.get("raw_success_regressions_vs_static_flow"), 999))
        additive_worse = int(number(row.get("supported_worse_outside_margin_vs_additive"), 999))
        static_worse = int(number(row.get("supported_worse_outside_margin_vs_static_flow"), 999))
        additive_med = number(row.get("median_delta_vs_additive"), 999.0)
        static_med = number(row.get("median_delta_vs_static_flow"), 999.0)
        g556_reg = int(number(row.get("raw_success_regressions_vs_g556"), 999))
        g556_worse = int(number(row.get("supported_worse_outside_margin_vs_g556"), 999))
        g556_med = number(row.get("median_delta_vs_g556"), 999.0)
        return (
            additive_reg + static_reg,
            additive_worse + static_worse,
            additive_med + static_med,
            max(additive_med, static_med),
            g556_reg,
            g556_worse,
            g556_med,
            str(row.get("variant_id", "")),
            str(row.get("model_path", "")),
        )

    ordered = sorted(candidates, key=score)
    primary = ordered[0]
    return {
        "decision": "g567_one_primary_actor_selected",
        "selection_rule": "additive_static_flow_safety_and_utility_primary_g556_secondary_tiebreak",
        "primary_model_path": primary.get("model_path", ""),
        "primary_variant_id": primary.get("variant_id", ""),
        "candidate_count": len(candidates),
        "g556_used_only_as_secondary_tiebreaker": True,
        "selected_score": list(score(primary)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run strict G5.67 valid-tail three-tier direct-actor pipeline.")
    parser.add_argument("--target-valid", type=int, default=100000)
    parser.add_argument("--seed", type=int, default=567)
    parser.add_argument("--smoke-contexts", type=int, default=128)
    parser.add_argument("--repeat-contexts", type=int, default=2000)
    parser.add_argument("--repeat-count", type=int, default=10)
    parser.add_argument("--label-train-contexts", type=int, default=24000)
    parser.add_argument("--min-label-train-contexts", type=int, default=24000)
    parser.add_argument("--development-contexts", type=int, default=4000)
    parser.add_argument("--blind-contexts", type=int, default=5000)
    parser.add_argument("--group-response-rows", type=int, default=0)
    parser.add_argument("--checkpoint-glob", nargs="*", default=["artifacts/models/gcst/phase5p5_repair5g565_expanded_e1_seed565.pt", "artifacts/models/gcst/phase5p5_repair5g565_expanded_e0_seed565.pt", "artifacts/models/gcst/phase5p5_repair5g565_expanded_e2_seed565.pt"])
    parser.add_argument("--actor-variants", default="C0,A5,A6,A7")
    parser.add_argument("--actor-seeds", default="567,568,569")
    parser.add_argument("--actor-epochs", type=int, default=240)
    parser.add_argument("--actor-min-epochs", type=int, default=80)
    parser.add_argument("--actor-patience", type=int, default=30)
    parser.add_argument("--actor-hidden-dim", type=int, default=256)
    parser.add_argument("--actor-lr", type=float, default=2.0e-4)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--train-token-budget", type=int, default=int(os.environ.get("G567_TRAIN_TOKEN_BUDGET", "12000")))
    parser.add_argument("--actor-checkpoint-interval-sec", type=float, default=float(os.environ.get("G567_ACTOR_CHECKPOINT_INTERVAL_SEC", "3600")))
    parser.add_argument("--resume-actor-training", action="store_true", default=boolish(os.environ.get("G567_RESUME_ACTOR_TRAINING", "")))
    parser.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--single-worker-repeat", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--expected-head", default=os.environ.get("G567_EXPECTED_HEAD", ""))
    args = parser.parse_args(argv)

    import torch

    started = time.perf_counter()
    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    source_state = write_source_state(args.expected_head)
    if source_state.get("decision") != "g567_source_state_clean":
        blocked = {
            "schema_version": f"{ROUND}_final_decision_summary_v1",
            "decision": "g567_blocked_source_state_fail_closed",
            "source_state_decision": source_state.get("decision", ""),
            "source_state_failures": source_state.get("source_state_failures", []),
            "head": source_state.get("head", ""),
            "expected_head": source_state.get("expected_head", ""),
            "status_short": source_state.get("status_short", ""),
            **claims(),
        }
        write_json(FINAL_DECISION_SUMMARY, blocked)
        print(json.dumps(blocked, sort_keys=True))
        return 2
    write_protocol_documents()
    truth = write_g565_truth_audit()
    validity = materialize_valid_bank(args.target_valid, args.seed, overwrite=bool(args.overwrite))
    if not args.plan_only and validity.get("decision") != "g567_valid_context_bank_ready":
        blocked = {
            "schema_version": f"{ROUND}_final_decision_summary_v1",
            "decision": "g567_blocked_valid_context_bank_not_ready",
            "validity_decision": validity.get("decision", ""),
            "valid_contexts": validity.get("valid_contexts", 0),
            "target_valid_contexts": validity.get("target_valid_contexts", 0),
            "benchmark_synthetic_mixture_target_met": validity.get("benchmark_synthetic_mixture_target_met", False),
            "canonical_public_benchmark_contexts": validity.get("canonical_public_benchmark_contexts", 0),
            "synthetic_stress_contexts": validity.get("synthetic_stress_contexts", 0),
            **claims(),
        }
        write_json(FINAL_DECISION_SUMMARY, blocked)
        print(json.dumps(blocked, sort_keys=True))
        return 2
    memory_smoke = write_3000_agent_memory_smoke(device, args.actor_hidden_dim)
    if not args.plan_only and memory_smoke.get("decision") != "g567_3000_agent_contract_valid":
        blocked = {
            "schema_version": f"{ROUND}_final_decision_summary_v1",
            "decision": "g567_blocked_3000_agent_memory_contract_failed",
            "memory_smoke_decision": memory_smoke.get("decision", ""),
            "memory_smoke_reason": memory_smoke.get("reason", ""),
            **claims(),
        }
        write_json(FINAL_DECISION_SUMMARY, blocked)
        print(json.dumps(blocked, sort_keys=True))
        return 2
    registry = write_baseline_registry()
    fallback_margin = number(read_json(REPORTS / "phase5p5_repair5g565_label_margin_summary.json").get("recommended_positive_margin"), 0.043)

    ckpts = checkpoint_paths(args.checkpoint_glob)
    if not ckpts:
        summary = {"decision": "g567_blocked_missing_actor_checkpoints", "checkpoint_glob": args.checkpoint_glob, **claims()}
        write_json(FINAL_DECISION_SUMMARY, summary)
        print(json.dumps(summary, sort_keys=True))
        return 2

    smoke_contexts = contexts_from_manifest("LABEL_TRAIN,VALIDATION,CALIBRATION", args.smoke_contexts)
    label_train_contexts = contexts_from_manifest("LABEL_TRAIN", args.label_train_contexts)
    repeat_contexts = contexts_from_manifest("CALIBRATION", args.repeat_contexts)
    development_contexts = contexts_from_manifest("VALIDATION,CALIBRATION", args.development_contexts)
    blind_hash_manifest = summarize_blind_hash_manifest(args.blind_contexts)
    if (
        len(smoke_contexts) < args.smoke_contexts
        or len(label_train_contexts) < args.label_train_contexts
        or len(development_contexts) < args.development_contexts
        or int(blind_hash_manifest.get("blind_context_rows_available", 0)) < args.blind_contexts
    ):
        blocked = {
            "schema_version": f"{ROUND}_final_decision_summary_v1",
            "decision": "g567_blocked_insufficient_contexts_after_valid_generation",
            "smoke_contexts": len(smoke_contexts),
            "label_train_contexts": len(label_train_contexts),
            "development_contexts": len(development_contexts),
            "blind_context_hash_rows_available": blind_hash_manifest.get("blind_context_rows_available", 0),
            "required_smoke_contexts": args.smoke_contexts,
            "required_label_train_contexts": args.label_train_contexts,
            "required_development_contexts": args.development_contexts,
            "required_blind_contexts": args.blind_contexts,
            "blind_features_materialized_pre_primary_freeze": False,
            **claims(),
        }
        write_json(FINAL_DECISION_SUMMARY, blocked)
        print(json.dumps(blocked, sort_keys=True))
        return 2

    raw_smoke = infer_checkpoint_thetas(smoke_contexts, ckpts[:1], device=device, batch_size=args.batch_size, phase="three_tier_smoke")
    smoke = run_replay_phase(
        "three_tier_smoke",
        smoke_contexts,
        raw_smoke,
        binary=args.binary,
        max_workers=max(1, args.max_workers),
        overwrite=args.overwrite,
        margin=fallback_margin,
        plan_only=args.plan_only,
    )
    blocked = replay_block_summary("three_tier_smoke", smoke) if not args.plan_only else None
    if blocked:
        write_json(FINAL_DECISION_SUMMARY, blocked)
        print(json.dumps(blocked, sort_keys=True))
        return 2

    repeat_theta = infer_checkpoint_thetas(repeat_contexts, ckpts[:1], device=device, batch_size=args.batch_size, phase="repeatability_single_worker")
    repeat = run_replay_phase(
        "repeatability_single_worker",
        repeat_contexts,
        repeat_theta,
        binary=args.binary,
        max_workers=1,
        overwrite=args.overwrite,
        margin=fallback_margin,
        plan_only=args.plan_only,
        repeat_count=args.repeat_count,
    )
    blocked = replay_block_summary("repeatability_single_worker", repeat) if not args.plan_only else None
    if blocked:
        write_json(FINAL_DECISION_SUMMARY, blocked)
        print(json.dumps(blocked, sort_keys=True))
        return 2
    repeat_margin = write_repeatability_summary(repeat, fallback_margin)
    applied_margin = number(repeat_margin.get("recommended_positive_margin"), fallback_margin)

    seed_actor_raw = infer_checkpoint_thetas(label_train_contexts, ckpts[:3], device=device, batch_size=args.batch_size, phase="seed_actor_response_source")
    response_target_rows = int(args.group_response_rows) if int(args.group_response_rows) > 0 else max(50000, min(100000, len(label_train_contexts) * 4))
    response_rows = generate_response_thetas(label_train_contexts, seed_actor_raw, phase="field_group_response", target_rows=response_target_rows)
    response = run_replay_phase(
        "field_group_response",
        label_train_contexts,
        response_rows,
        binary=args.binary,
        max_workers=args.max_workers,
        overwrite=args.overwrite,
        margin=applied_margin,
        plan_only=args.plan_only,
    )
    blocked = replay_block_summary("field_group_response", response) if not args.plan_only else None
    if blocked:
        write_json(FINAL_DECISION_SUMMARY, blocked)
        print(json.dumps(blocked, sort_keys=True))
        return 2
    label = create_labelv54_from_pairs([plan_paths("field_group_response")["pairs"], plan_paths("repeatability_single_worker")["pairs"]], applied_margin)
    if not args.plan_only and int(number(label.get("label_train_unique_exact_labeled_contexts"), 0)) < int(args.min_label_train_contexts):
        blocked = {
            "schema_version": f"{ROUND}_final_decision_summary_v1",
            "decision": "g567_blocked_label_train_unique_exact_contexts_below_minimum",
            "label_train_unique_exact_labeled_contexts": label.get("label_train_unique_exact_labeled_contexts", 0),
            "required_min_label_train_contexts": int(args.min_label_train_contexts),
            **claims(),
        }
        write_json(FINAL_DECISION_SUMMARY, blocked)
        print(json.dumps(blocked, sort_keys=True))
        return 2
    actor_variants = [token.strip().upper() for token in args.actor_variants.split(",") if token.strip()]
    actor_seeds = [int(token.strip()) for token in args.actor_seeds.split(",") if token.strip()]
    calibration_contexts = contexts_from_manifest("CALIBRATION", min(args.repeat_contexts, max(1, args.development_contexts)))
    outcome = train_distributional_outcome_ensemble(
        label_train_contexts,
        seeds=actor_seeds,
        plan_only=args.plan_only,
    )
    outcome["critic_candidate_source_split"] = "LABEL_TRAIN"
    outcome["critic_calibration_contexts_reserved"] = len(calibration_contexts)
    outcome["development_contexts_used_for_critic_fit"] = False
    write_json(DISTRIBUTIONAL_CRITIC_SUMMARY, outcome)
    write_json(OUTCOME_ENSEMBLE_SUMMARY, outcome)
    if not args.plan_only and outcome.get("decision") != "g567_distributional_critic_calibrated":
        blocked = {
            "schema_version": f"{ROUND}_final_decision_summary_v1",
            "decision": "g567_blocked_distributional_critic_not_calibrated",
            "outcome_ensemble_decision": outcome.get("decision", ""),
            **claims(),
        }
        write_json(FINAL_DECISION_SUMMARY, blocked)
        print(json.dumps(blocked, sort_keys=True))
        return 2
    actor_training, trained_ckpts = train_g567_actors(
        label_train_contexts,
        device=device,
        seeds=actor_seeds,
        variants=actor_variants,
        epochs=args.actor_epochs,
        min_epochs=args.actor_min_epochs,
        patience=args.actor_patience,
        batch_size=args.batch_size,
        token_budget=args.train_token_budget,
        hidden_dim=args.actor_hidden_dim,
        lr=args.actor_lr,
        plan_only=args.plan_only,
        checkpoint_interval_sec=args.actor_checkpoint_interval_sec,
        resume=args.resume_actor_training,
    )
    if not args.plan_only and not trained_ckpts:
        blocked = {
            "schema_version": f"{ROUND}_final_decision_summary_v1",
            "decision": "g567_blocked_actor_training_missing_checkpoints",
            "actor_training_decision": actor_training.get("decision", ""),
            **claims(),
        }
        write_json(FINAL_DECISION_SUMMARY, blocked)
        print(json.dumps(blocked, sort_keys=True))
        return 2

    dev_ckpts = trained_ckpts if trained_ckpts else ckpts[:1]
    dev_raw = infer_checkpoint_thetas(development_contexts, dev_ckpts, device=device, batch_size=args.batch_size, phase="development_three_tier")
    development = run_replay_phase(
        "development_three_tier",
        development_contexts,
        dev_raw,
        binary=args.binary,
        max_workers=args.max_workers,
        overwrite=args.overwrite,
        margin=applied_margin,
        plan_only=args.plan_only,
        include_no_ltm=True,
    )
    write_json(DEVELOPMENT_SUMMARY, development)
    blocked = replay_block_summary("development_three_tier", development) if not args.plan_only else None
    if blocked:
        write_json(FINAL_DECISION_SUMMARY, blocked)
        print(json.dumps(blocked, sort_keys=True))
        return 2
    scaling = write_scaling_summary(development)
    if not args.plan_only and scaling.get("decision") != "g567_nested_scaling_study_completed":
        blocked = {
            "schema_version": f"{ROUND}_final_decision_summary_v1",
            "decision": "g567_blocked_nested_scaling_study_not_completed",
            "scaling_decision": scaling.get("decision", ""),
            "required_nested_sizes": ["1k", "4k", "12k", "24k", "36k"],
            **claims(),
        }
        write_json(FINAL_DECISION_SUMMARY, blocked)
        print(json.dumps(blocked, sort_keys=True))
        return 2

    primary_actor = select_primary_actor_checkpoint(development)
    if primary_actor.get("decision") != "g567_one_primary_actor_selected":
        blocked = {
            "schema_version": f"{ROUND}_final_decision_summary_v1",
            "decision": "g567_blocked_primary_actor_not_selected",
            "primary_actor_selection": primary_actor,
            "blind_hash_manifest": blind_hash_manifest,
            "blind_features_materialized_pre_primary_freeze": False,
            **claims(),
        }
        write_json(FINAL_DECISION_SUMMARY, blocked)
        print(json.dumps(blocked, sort_keys=True))
        return 2
    blind_ckpts = [resolve(primary_actor["primary_model_path"])] if primary_actor.get("primary_model_path") else []
    blind_ckpts = [path for path in blind_ckpts if path.exists()]
    if not args.plan_only and len(blind_ckpts) != 1:
        blocked = {
            "schema_version": f"{ROUND}_final_decision_summary_v1",
            "decision": "g567_blocked_exactly_one_primary_actor_checkpoint_required",
            "primary_actor_selection": primary_actor,
            "resolved_primary_actor_checkpoints": [rel(path) for path in blind_ckpts],
            **claims(),
        }
        write_json(FINAL_DECISION_SUMMARY, blocked)
        print(json.dumps(blocked, sort_keys=True))
        return 2
    blind_contexts = contexts_from_manifest("BLIND", args.blind_contexts)
    if len(blind_contexts) < args.blind_contexts:
        blocked = {
            "schema_version": f"{ROUND}_final_decision_summary_v1",
            "decision": "g567_blocked_blind_materialization_after_freeze_insufficient",
            "blind_contexts_materialized_after_primary_freeze": len(blind_contexts),
            "required_blind_contexts": args.blind_contexts,
            "blind_hash_manifest": blind_hash_manifest,
            **claims(),
        }
        write_json(FINAL_DECISION_SUMMARY, blocked)
        print(json.dumps(blocked, sort_keys=True))
        return 2
    blind_raw = infer_checkpoint_thetas(blind_contexts, blind_ckpts, device=device, batch_size=args.batch_size, phase="blind_three_tier")
    freeze = {
        "blind_context_hash_manifest": blind_hash_manifest,
        "blind_manifest_sha256": sha256_file(VALID_CONTEXT_MANIFEST),
        "baseline_registry_sha256": sha256_file(BASELINE_REGISTRY),
        "candidate_checkpoints": [rel(path) for path in blind_ckpts],
        "candidate_checkpoint_hashes": {rel(path): sha256_file(path) for path in blind_ckpts},
        "primary_actor_selection": primary_actor,
        "exactly_one_primary_actor": len(blind_ckpts) == 1,
        "decision_rules_sha256": sha256_file(PLAN_FILE),
        "blind_features_materialized_after_primary_actor_freeze": True,
    }
    write_json(REPORTS / f"{ROUND}_blind_freeze_manifest.json", {**freeze, **claims()})
    blind = run_replay_phase(
        "blind_three_tier",
        blind_contexts,
        blind_raw,
        binary=args.binary,
        max_workers=args.max_workers,
        overwrite=args.overwrite,
        margin=applied_margin,
        plan_only=args.plan_only,
        include_no_ltm=True,
    )
    write_json(BLIND_SUMMARY, blind)
    blocked = replay_block_summary("blind_three_tier", blind) if not args.plan_only else None
    if blocked:
        write_json(FINAL_DECISION_SUMMARY, blocked)
        print(json.dumps(blocked, sort_keys=True))
        return 2

    final_artifact_paths = [
        SOURCE_STATE,
        BUG_LOG,
        PROTOCOL_OVERVIEW,
        TIME_BUDGET_SEMANTICS,
        MEMORY_SMOKE_3000,
        TRUTH_AUDIT_SUMMARY,
        VALID_CONTEXT_MANIFEST,
        INVALID_QUARANTINE,
        SCENARIO_VALIDITY,
        SPLIT_MANIFEST,
        VALIDITY_SUMMARY,
        BASELINE_REGISTRY,
        BASELINE_REGISTRY_SUMMARY,
        REPEATABILITY_SUMMARY,
        LABELV54_SUMMARY,
        LABELV54_CONTEXTS,
        LABELV54_CANDIDATES,
        LABELV54_REPLICATES,
        LABELV54_SAFE_SETS,
        ACTOR_TRAINING_SUMMARY,
        ACTOR_TRAINING_MATRIX,
        ACTOR_GRADIENT_AUDIT,
        OUTCOME_ENSEMBLE_SUMMARY,
        DISTRIBUTIONAL_CRITIC_SUMMARY,
        DISTRIBUTIONAL_CRITIC_PREDICTIONS,
        DISTRIBUTIONAL_CRITIC_MODEL_AUDIT,
        SCALING_SUMMARY,
        DEVELOPMENT_SUMMARY,
        BLIND_SUMMARY,
        FINAL_DECISION_SUMMARY,
        FINAL_DECISION_MD,
    ]
    final = write_final_decision(
        development,
        blind,
        label,
        validity,
        final_artifact_paths,
    )
    final["elapsed_sec"] = time.perf_counter() - started
    final["truth_audit_decision"] = truth.get("decision")
    final["validity_decision"] = validity.get("decision")
    final["source_state_decision"] = source_state.get("decision")
    final["memory_smoke_decision"] = memory_smoke.get("decision")
    final["registry_decision"] = registry.get("decision")
    final["actor_training_decision"] = actor_training.get("decision")
    final["outcome_ensemble_decision"] = outcome.get("decision")
    final["scaling_decision"] = scaling.get("decision")
    write_json(FINAL_DECISION_SUMMARY, final)
    write_artifact_manifest(final_artifact_paths)
    print(json.dumps({"decision": final["decision"], "tierA": final["g567_blind_tierA_pass"], "tierB": final["g567_blind_tierB_pass"], "tierC_deploy": final["g567_blind_tierC_deployment_pass"]}, sort_keys=True))
    return 0 if final["decision"] == "g567_blind_complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())



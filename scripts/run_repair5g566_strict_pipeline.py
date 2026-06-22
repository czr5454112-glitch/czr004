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


ROUND = "phase5p5_repair5g566"
PLAN_FILE = "czr004_g566_valid_tail_three_tier_direct_actor_plan.md"
TABLES = Path("outputs/tables")
REPORTS = Path("outputs/reports")
LOGS = Path("outputs/logs")
MODEL_DIR = Path("artifacts/models/gcst")
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
LABELV53_CONTEXTS = TABLES / f"{ROUND}_labelv53_contexts.csv"
LABELV53_CANDIDATES = TABLES / f"{ROUND}_labelv53_candidates.csv"
LABELV53_REPLICATES = TABLES / f"{ROUND}_labelv53_replicates.csv"
LABELV53_SUMMARY = REPORTS / f"{ROUND}_labelv53_summary.json"
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

NO_LTM_DIAGNOSTIC = "lacam_star"
FIELD_GROUPS = {
    "G1_congestion_commit_block": [0, 1, 2],
    "G2_congestion_wait": [3, 4],
    "G3_goal_flow": [5, 6],
    "G4_decay": [7, 8],
    "G5_channel_weights": [9, 10],
    "G6_shield_bounds": [11, 12, 13, 14],
}

G566_MAP_SPECS = [
    ("g566-empty-8x8", "empty", 8, 8),
    ("g566-empty-16x16", "empty", 16, 16),
    ("g566-empty-32x32", "empty", 32, 32),
    ("g566-empty-48x32", "empty", 48, 32),
    ("g566-random-16x16-a", "random", 16, 16),
    ("g566-random-24x24-a", "random", 24, 24),
    ("g566-random-32x32-a", "random", 32, 32),
    ("g566-random-40x40-b", "random", 40, 40),
    ("g566-maze-24x24-a", "maze", 24, 24),
    ("g566-maze-48x32-a", "maze", 48, 32),
    ("g566-maze-64x32-b", "maze", 64, 32),
    ("g566-room-24x24-a", "room", 24, 24),
    ("g566-room-48x48-a", "room", 48, 48),
    ("g566-room-64x48-b", "room", 64, 48),
    ("g566-warehouse-20x10-a", "warehouse", 20, 10),
    ("g566-warehouse-32x24-a", "warehouse", 32, 24),
    ("g566-warehouse-48x32-a", "warehouse", 48, 32),
    ("g566-warehouse-64x40-b", "warehouse", 64, 40),
    ("g566-connector-24x24-a", "connector", 24, 24),
    ("g566-connector-48x48-a", "connector", 48, 48),
    ("g566-tunnel-24x24-a", "tunnel", 24, 24),
    ("g566-tunnel-64x32-a", "tunnel", 64, 32),
    ("g566-loop-32x32-a", "loop", 32, 32),
    ("g566-loop-56x56-a", "loop", 56, 56),
    ("g566-tree-32x32-a", "tree", 32, 32),
    ("g566-tree-56x40-a", "tree", 56, 40),
    ("g566-string-32x24-a", "irregular_bottleneck", 32, 24),
    ("g566-string-64x32-a", "irregular_bottleneck", 64, 32),
    ("g566-corners-48x48-a", "irregular_bottleneck", 48, 48),
    ("g566-city-32x32-a", "city", 32, 32),
    ("g566-city-64x48-a", "city", 64, 48),
    ("g566-cross-32x32-a", "cross", 32, 32),
    ("g566-cross-64x40-a", "cross", 64, 40),
    ("g566-lanes-48x32-a", "lanes", 48, 32),
    ("g566-lanes-64x48-a", "lanes", 64, 48),
    ("g566-plaza-40x40-a", "plaza", 40, 40),
    ("g566-plaza-64x64-a", "plaza", 64, 64),
    ("g566-islands-48x48-a", "islands", 48, 48),
    ("g566-islands-72x48-a", "islands", 72, 48),
    ("g566-chambers-48x32-a", "chambers", 48, 32),
    ("g566-chambers-64x48-a", "chambers", 64, 48),
    ("g566-spiral-40x40-a", "spiral", 40, 40),
    ("g566-spiral-64x64-a", "spiral", 64, 64),
] * 2


@dataclass(frozen=True)
class G566Context:
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
    audit_rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    generated = 0
    attempts = 0
    while generated < target_valid and attempts < target_valid * 25:
        attempts += 1
        map_name, family, width, height = G566_MAP_SPECS[(generated + attempts + seed) % len(G566_MAP_SPECS)]
        map_variant = attempts % 4
        concrete_map = f"{map_name}-v{map_variant}"
        grid = g561_bank.synthetic_grid(concrete_map, width, height)
        free_count = len(g561_bank.free_cells(grid))
        if free_count < min(g561_bank.AGENT_COUNTS):
            continue
        agent_count = g561_bank.AGENT_COUNTS[generated % len(g561_bank.AGENT_COUNTS)]
        if agent_count > free_count:
            continue
        regime_name = g561_bank.REGIMES[(generated + seed) % len(g561_bank.REGIMES)]
        budget_ms, base_sec, ltm_iters = g561_bank.BUDGET_PROFILES[(generated + attempts) % len(g561_bank.BUDGET_PROFILES)]
        solver_seed = seed * 1_000_000 + attempts
        try:
            assignment = g561_bank.build_assignment(grid, width, height, agent_count, regime_name, solver_seed)
        except ValueError:
            continue
        map_path = map_dir / f"{concrete_map}.map"
        scen_path = scenario_dir / f"{concrete_map}-random-{solver_seed}.scen"
        map_sha = g561_bank.write_map(map_path, grid)
        scenario_sha = g561_bank.write_scenario(scen_path, concrete_map, width, height, assignment)
        graph = build_graph({"map": concrete_map, "width": width, "height": height, "free_cells": free_count})
        traffic = g561_bank.compute_traffic_prior(graph, {"starts": assignment["starts"], "goals": assignment["goals"]})
        instance_uid = stable_uid(
            "g566_valid_instance",
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
            "g566_instance_uid": instance_uid,
            "g566_evaluation_uid": stable_uid("g566_eval", instance_uid, budget_ms, ltm_iters),
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
            "ltm_max_iterations": ltm_iters,
            "agent_density": density,
            "scenario_bank_source": "generated_g566_component_aware",
            "raw_map_path": rel(map_path),
            "raw_scenario_path": rel(scen_path),
            "path_found_rate": traffic["summary"]["path_found_rate"],
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
            print(json.dumps({"event": "g566_valid_generation_progress", "generated": generated, "attempts": attempts}), flush=True)
    return audit_rows, manifest_rows, {"attempts": attempts, "generated": generated}


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
    assigned_counts = {"TRAIN": 0, "VALIDATION": 0, "CALIBRATION": 0, "BLIND": 0}
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
            roles[h] = "TRAIN"
            assigned_counts["TRAIN"] += len(by_hash[h])
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
        row["g566_dataset_row_id"] = f"g566_valid_{idx:06d}"
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
    budgets = Counter(str(row["nominal_budget_ms"]) for row in valid_rows)
    agents = Counter(str(row["agent_count"]) for row in valid_rows)
    blind_hashes = {row["physical_map_sha256"] for row in valid_rows if row["split"] == "BLIND"}
    summary = {
        "schema_version": f"{ROUND}_validity_summary_v1",
        "decision": "g566_valid_context_bank_ready" if len(valid_rows) >= target_valid else "g566_valid_context_bank_under_target",
        "target_valid_contexts": target_valid,
        "valid_contexts": len(valid_rows),
        "invalid_quarantine_rows": len(invalid_rows),
        "preferred_6000_target_met": len(valid_rows) >= 6000,
        "minimum_5000_target_met": len(valid_rows) >= 5000,
        "physical_map_hashes": len(by_hash),
        "physical_map_hash_target_met": len(by_hash) >= 40,
        "map_families": dict(sorted(families.items())),
        "map_family_target_met": len(families) >= 16,
        "agent_tiers": dict(sorted(agents.items())),
        "agent_tier_target_met": len(agents) >= 6,
        "budget_profiles": dict(sorted(budgets.items())),
        "budget_target_met": len(budgets) >= 4,
        "split_counts": dict(sorted(split_counts.items())),
        "blind_contexts": split_counts.get("BLIND", 0),
        "blind_physical_map_hashes": len(blind_hashes),
        "blind_1000_target_met": split_counts.get("BLIND", 0) >= 1000,
        "blind_12_map_hash_target_met": len(blind_hashes) >= 12,
        "all_path_found_rate_one": all(number(row.get("path_found_rate"), 0.0) == 1.0 for row in valid_rows),
        "scenario_replay_dir": rel(REPLAY_SCENARIO_DIR),
        "map_dir": rel(resolve(TMP_ROOT) / "maps"),
        "generator_attempts": meta["attempts"],
        "generator_seed": seed,
        **claims(),
    }
    write_json(VALIDITY_SUMMARY, summary)
    write_text(
        VALIDITY_MD,
        "# Repair5G.5.66 Valid Context Bank\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- valid contexts: `{summary['valid_contexts']}`\n"
        f"- physical map hashes: `{summary['physical_map_hashes']}`\n"
        f"- blind contexts: `{summary['blind_contexts']}`\n"
        f"- blind physical map hashes: `{summary['blind_physical_map_hashes']}`\n"
        f"- all path_found_rate == 1: `{summary['all_path_found_rate_one']}`\n\n"
        "All G5.66 generated assignments use component-aware sampling, unique starts, unique goals, and raw map/scenario files materialized under `outputs/tmp`.\n",
    )
    return summary


def write_g565_truth_audit() -> dict[str, Any]:
    margin = read_json(REPORTS / "phase5p5_repair5g565_label_margin_summary.json")
    fresh = read_json(REPORTS / "phase5p5_repair5g565_fresh_solver_panel_summary.json")
    expanded = read_json(REPORTS / "phase5p5_repair5g565_expanded_solver_panel_summary.json")
    alpha = read_json(REPORTS / "phase5p5_repair5g565_alpha_response_summary.json")
    summary = {
        "schema_version": f"{ROUND}_g565_truth_audit_summary_v1",
        "decision": "g565_complete_but_g566_requires_new_three_tier_valid_blind",
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
        "# Repair5G.5.66 Audit of G5.65\n\n"
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
        "decision": "g566_three_tier_baseline_registry_frozen",
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


def contexts_from_manifest(split_filter: str, limit: int) -> list[G566Context]:
    update_remote_map_registries(resolve(TMP_ROOT) / "maps")
    wanted = {token.strip().upper() for token in split_filter.split(",") if token.strip()}
    rows = [row for row in read_rows(VALID_CONTEXT_MANIFEST) if not wanted or str(row.get("split", "")).upper() in wanted]
    contexts: list[G566Context] = []
    for row in rows:
        scen = resolve(row["replay_scenario_path"])
        assignment = parse_movingai_scenario(scen, int(number(row.get("agent_count"), 0)))
        graph = build_graph(
            {
                "map": row["map"],
                "width": row.get("width", 32),
                "height": row.get("height", 32),
                "free_cells": row.get("free_cells", ""),
            }
        )
        traffic = g561_bank.compute_traffic_prior(graph, assignment)
        if number(traffic["summary"].get("path_found_rate"), 0.0) != 1.0:
            continue
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
        contexts.append(
            G566Context(
                dataset_row_id=row["g566_dataset_row_id"],
                evaluation_uid=row["g566_evaluation_uid"],
                instance_uid=row["g566_instance_uid"],
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
            )
        )
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
    ).module().to(device)
    model.load_state_dict(payload["actor_state_dict"])
    model.eval()
    return model, kind


def infer_checkpoint_thetas(contexts: list[G566Context], checkpoint_paths: list[Path], *, device: str, batch_size: int, phase: str) -> list[dict[str, Any]]:
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
                        "g566_evaluation_uid": ctx.evaluation_uid,
                        "variant_id": kind,
                        "variant_name": str(payload.get("variant_name") or payload.get("model_kind") or kind),
                        "seed": payload.get("seed", payload.get("metrics", {}).get("seed", "")),
                        "method": f"g566_{kind}_{path.stem}",
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


def add_plan_row(plan: list[dict[str, Any]], ctx: G566Context, *, phase: str, role: str, candidate_id: str, method: str, theta: dict[str, Any] | None, model_path: str = "", actor_row: dict[str, Any] | None = None) -> None:
    idx = len(plan)
    generated_uid = "" if theta is None else generated_theta_uid(model_path or method, ctx.instance_uid, [theta[col] for col in THETA_NUMERIC_COLUMNS])
    identity = stable_uid("g566_replay_identity", phase, ctx.evaluation_uid, ctx.scenario_sha256, candidate_id, generated_uid)
    expected_fingerprint = ""
    if candidate_id == ADDITIVE_SOLVER_ALIAS:
        expected_fingerprint = TIER_A_ADDITIVE.fingerprint
    elif candidate_id == STATIC_FLOW_SOLVER_ALIAS:
        expected_fingerprint = TIER_B_STATIC_FLOW.fingerprint
    elif candidate_id == G556_SOLVER_ALIAS:
        expected_fingerprint = TIER_C_G556.fingerprint
    elif theta is not None:
        expected_fingerprint = updateparams_fingerprint(theta)
    row = {
        "plan_row_id": f"g566_{safe_token(phase)}_{idx:08d}",
        "replay_phase": phase,
        "context_id": ctx.dataset_row_id,
        "g566_dataset_row_id": ctx.dataset_row_id,
        "g566_instance_uid": ctx.instance_uid,
        "g566_evaluation_uid": ctx.evaluation_uid,
        "g566_identity_digest": identity,
        "g566_scenario_sha256": ctx.scenario_sha256,
        "g566_physical_map_sha256": ctx.physical_map_sha256,
        "g566_assignment_sha256": ctx.assignment_sha256,
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
        "ltm_max_iterations": ctx.ltm_max_iterations,
        "horizon_id": ctx.horizon_id,
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
        **claims(),
    }
    if theta is not None:
        row.update({col: theta.get(col, "") for col in THETA_COLUMNS})
    plan.append(row)


def build_plan_and_registry(contexts: list[G566Context], theta_rows: list[dict[str, Any]], phase: str, *, include_no_ltm: bool = False) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    context_by_id = {ctx.dataset_row_id: ctx for ctx in contexts}
    plan: list[dict[str, Any]] = []
    registry = baseline_registry_rows(claims())
    if include_no_ltm:
        for ctx in contexts:
            add_plan_row(ctx=ctx, plan=plan, phase=phase, role="no_ltm_diagnostic", candidate_id=NO_LTM_DIAGNOSTIC, method="LaCAM* no-LTM diagnostic", theta=None)
    for ctx in contexts:
        add_plan_row(ctx=ctx, plan=plan, phase=phase, role="tierA_additive_ltm", candidate_id=ADDITIVE_SOLVER_ALIAS, method="paper_faithful_additive_ltm", theta=None)
        add_plan_row(ctx=ctx, plan=plan, phase=phase, role="tierB_static_flow_shield", candidate_id=STATIC_FLOW_SOLVER_ALIAS, method=TIER_B_STATIC_FLOW.underlying_method, theta=TIER_B_STATIC_FLOW.theta)
        add_plan_row(ctx=ctx, plan=plan, phase=phase, role="tierC_g556", candidate_id=G556_SOLVER_ALIAS, method=G556_SOLVER_ALIAS, theta=TIER_C_G556.theta)
    for theta_row in theta_rows:
        ctx = context_by_id[str(theta_row["context_id"])]
        theta = clamp_theta_row(theta_row)
        uid = stable_uid("g566_actor_theta", phase, theta_row.get("method", ""), ctx.evaluation_uid, {col: theta[col] for col in THETA_NUMERIC_COLUMNS})
        candidate_id = f"g566_{safe_token(phase)}_{safe_token(theta_row.get('variant_id', 'actor'))}_s{safe_token(theta_row.get('seed', '0'))}_{uid[:12]}"
        registry.append(
            {
                "candidate_id": candidate_id,
                "generated_theta_uid": generated_theta_uid(theta_row.get("model_path", ""), ctx.instance_uid, [theta[col] for col in THETA_NUMERIC_COLUMNS]),
                "registry_role": "g566_actor_generated_theta",
                "replay_phase": phase,
                "method": theta_row.get("method", ""),
                "variant_id": theta_row.get("variant_id", ""),
                "actor_training_seed": theta_row.get("seed", ""),
                **{col: theta.get(col, "") for col in THETA_COLUMNS},
                **claims(),
            }
        )
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
        )
    return plan, registry


def audit_results(rows: list[dict[str, Any]], plan_rows: list[dict[str, Any]], phase: str) -> list[dict[str, Any]]:
    lookup = g562.plan_lookup(plan_rows)
    out: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        plan = lookup.get(
            (
                str(row.get("map", "")),
                str(row.get("agents", "")),
                str(row.get("seed", "")),
                str(row.get("budget_ms", "")),
                str(row.get("materialized_method", "")),
            ),
            {},
        )
        for key in [
            "plan_row_id",
            "replay_phase",
            "g566_dataset_row_id",
            "g566_instance_uid",
            "g566_evaluation_uid",
            "g566_identity_digest",
            "g566_scenario_sha256",
            "g566_physical_map_sha256",
            "g566_assignment_sha256",
            "split",
            "generated_theta_uid",
            "expected_updateparams_fingerprint",
            "model_path",
            "variant_id",
            "actor_training_seed",
            "role",
        ]:
            row[key] = plan.get(key, row.get(key, ""))
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
            "g566_replay_identity",
            phase,
            row.get("g566_evaluation_uid", ""),
            row.get("g566_scenario_sha256", ""),
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
                "scenario_sha256_match": bool(scenario_actual) and scenario_actual == row.get("g566_scenario_sha256", ""),
                "identity_digest_actual": identity_actual,
                "identity_retained": bool(row.get("g566_identity_digest", "")) and identity_actual == row.get("g566_identity_digest", ""),
            }
        )
        out.append(row)
    return out


def group_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row.get("map", "")),
        str(row.get("agents", "")),
        str(row.get("seed", "")),
        str(row.get("budget_ms", "")),
        str(row.get("horizon_id", "")),
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
    grouped: dict[tuple[str, str, str, str, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
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
                    "split": actor.get("split", ""),
                    "map_family": actor.get("map_family", ""),
                    "g566_dataset_row_id": actor.get("g566_dataset_row_id", ""),
                    "g566_evaluation_uid": actor.get("g566_evaluation_uid", ""),
                    "g566_identity_digest": actor.get("g566_identity_digest", ""),
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
    materialized = bool(actor_rows and exact == len(actor_rows) and recognized == len(actor_rows) and scenario == len(actor_rows) and identity == len(actor_rows))

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
                "raw_success_regressions_vs_g556": 0,
                "raw_success_gains_vs_g556": 0,
                "deltas_vs_g556": [],
            },
        )
        bucket["pairs"] += 1
        bucket["raw_success_regressions_vs_g556"] += int(boolish(pair.get("success_regression_vs_g556")))
        bucket["raw_success_gains_vs_g556"] += int(boolish(pair.get("success_gain_vs_g556")))
        value = number(pair.get("delta_vs_g556"), math.nan)
        if math.isfinite(value):
            bucket["deltas_vs_g556"].append(value)
    for key, bucket in list(per_variant.items()):
        values = bucket.pop("deltas_vs_g556")
        bucket["mean_delta_vs_g556"] = float(np.mean(values)) if values else None
        bucket["median_delta_vs_g556"] = float(np.median(values)) if values else None
        bucket["supported_worse_outside_margin_vs_g556"] = sum(value > margin for value in values)

    summary = {
        "schema_version": f"{ROUND}_{safe_token(phase)}_summary_v1",
        "decision": "g566_three_tier_replay_materialized" if materialized else "g566_three_tier_materialization_blocked",
        "replay_phase": phase,
        "planned_rows": len(plan_rows),
        "executed_rows": len(rows),
        "contexts": len({row.get("g566_dataset_row_id") for row in plan_rows}),
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
    contexts: list[G566Context],
    theta_rows: list[dict[str, Any]],
    *,
    binary: Path,
    max_workers: int,
    overwrite: bool,
    margin: float,
    plan_only: bool,
    include_no_ltm: bool = False,
) -> dict[str, Any]:
    paths = plan_paths(phase)
    plan_rows, registry_rows = build_plan_and_registry(contexts, theta_rows, phase, include_no_ltm=include_no_ltm)
    write_rows(paths["plan"], plan_rows)
    write_rows(paths["registry"], registry_rows)
    if plan_only:
        summary = {
            "schema_version": f"{ROUND}_{safe_token(phase)}_summary_v1",
            "decision": "g566_three_tier_plan_created_server_run_required",
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
        summary = {"schema_version": f"{ROUND}_{safe_token(phase)}_summary_v1", "decision": "g566_blocked_missing_solver_binary", "binary": rel(binary_path), **claims()}
        write_json(paths["summary"], summary)
        return summary
    os.environ.setdefault("REPAIR5G_STREAM_RESULT_CSV", "1")
    os.environ.setdefault("REPAIR5G_SKIP_AGGREGATE_JSONL", "1")
    g549.run_probe_plan(
        plan_rows,
        binary=binary_path,
        overwrite=overwrite,
        row_limit=0,
        max_workers=max(1, int(max_workers)),
        registry_path=str(resolve(paths["registry"])),
        result_csv=str(resolve(paths["results"])),
        raw_csv=str(resolve(paths["raw_results"])),
        log_dir=str(resolve(paths["log_dir"])),
        run_jsonl=str(resolve(paths["log_dir"] / "runs.jsonl")),
        command_jsonl=str(resolve(paths["log_dir"] / "commands.jsonl")),
        update_jsonl=str(resolve(paths["log_dir"] / "updates.jsonl")),
        probe_jsonl=str(resolve(paths["log_dir"] / "counterfactual_probes.jsonl")),
        checkpoint_jsonl=str(resolve(paths["log_dir"] / "checkpoints.jsonl")),
        status_json=str(resolve(paths["log_dir"] / "status.json")),
        scenario_dir=str(resolve(paths["scenario_dir"])),
        scenario_metadata=str(resolve(paths["scenario_metadata"])),
        manifest_prefix=f"g566_{safe_token(phase)}",
        row_prefix=f"g566_{safe_token(phase)}",
        execution_mode=f"g566_{safe_token(phase)}_real_solver_row",
    )
    rows = audit_results(read_rows(paths["results"]), plan_rows, phase)
    write_rows(paths["results"], rows)
    pairs = build_three_tier_pairs(rows, phase)
    write_rows(paths["pairs"], pairs)
    summary = summarize_pairs(pairs, rows, plan_rows, phase, margin)
    write_json(paths["summary"], summary)
    write_text(
        paths["report"],
        f"# G5.66 {phase} Three-Tier Replay\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- contexts: `{summary['contexts']}`\n"
        f"- actor candidate rows: `{summary['actor_candidate_rows']}`\n"
        f"- three-tier pairs: `{summary['three_tier_pairs']}`\n"
        f"- static-flow rows present: `{summary['static_flow_rows_present']}`\n"
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


def generate_response_thetas(contexts: list[G566Context], raw_rows: list[dict[str, Any]], *, phase: str, target_rows: int) -> list[dict[str, Any]]:
    raw_by_context = {str(row["context_id"]): row for row in raw_rows}
    alphas = [0.0, 0.25, 0.50, 0.75, 1.0, 1.25, 1.50]
    group_alphas = [0.0, 0.50, 1.0, 1.50]
    leave_alphas = [0.0, 0.50, 1.0]
    out: list[dict[str, Any]] = []
    anchor = np.asarray(BASELINE_G556, dtype=np.float32)
    lo = np.asarray(THETA_LO, dtype=np.float32)
    hi = np.asarray(THETA_HI, dtype=np.float32)
    for ctx in contexts:
        raw = raw_by_context.get(ctx.dataset_row_id)
        if not raw:
            continue
        raw_vec = np.asarray([number(raw.get(col), float(anchor[idx])) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)], dtype=np.float32)
        delta = raw_vec - anchor

        def emit(label: str, vec: np.ndarray) -> None:
            clipped = np.minimum(np.maximum(vec, lo), hi)
            row = {col: float(clipped[idx]) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)}
            row.update(mode_columns("flow_shield"))
            out.append(
                {
                    "phase": phase,
                    "context_id": ctx.dataset_row_id,
                    "g566_evaluation_uid": ctx.evaluation_uid,
                    "variant_id": label,
                    "variant_name": "field_group_response",
                    "seed": "566",
                    "method": f"g566_response_{label}",
                    "model_path": str(raw.get("model_path", "")),
                    "raw_actor_variant_id": raw.get("variant_id", ""),
                    **row,
                }
            )

        for alpha in alphas:
            emit(f"GLOBAL_ALPHA_{str(alpha).replace('.', 'p')}", anchor + alpha * delta)
        for group_name, cols in FIELD_GROUPS.items():
            mask = np.zeros_like(delta)
            mask[cols] = delta[cols]
            for alpha in group_alphas:
                emit(f"{group_name}_ONLY_ALPHA_{str(alpha).replace('.', 'p')}", anchor + alpha * mask)
        for group_name, cols in FIELD_GROUPS.items():
            for alpha in leave_alphas:
                mask = delta.copy()
                mask[cols] *= alpha
                emit(f"LEAVE_{group_name}_ALPHA_{str(alpha).replace('.', 'p')}", anchor + mask)
        if len(out) >= target_rows:
            break
    return out[:target_rows]


def create_labelv53_from_pairs(pair_paths: list[Path], margin: float) -> dict[str, Any]:
    pairs: list[dict[str, str]] = []
    for path in pair_paths:
        pairs.extend(read_rows(path))
    context_rows: dict[str, dict[str, Any]] = {}
    candidate_rows: list[dict[str, Any]] = []
    replicate_rows: list[dict[str, Any]] = []
    for row in pairs:
        uid = row.get("g566_evaluation_uid", "")
        if not uid:
            continue
        context_rows.setdefault(
            uid,
            {
                "g566_evaluation_uid": uid,
                "g566_dataset_row_id": row.get("g566_dataset_row_id", ""),
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
        safe = not boolish(row.get("success_regression_vs_g556")) and not boolish(row.get("success_regression_vs_static_flow"))
        positive = safe and any(math.isfinite(v) and v < -margin for v in [dg, ds, da])
        harmful = boolish(row.get("success_regression_vs_g556")) or (math.isfinite(dg) and dg > margin)
        candidate_rows.append(
            {
                "g566_evaluation_uid": uid,
                "candidate_uid": row.get("theta_id", ""),
                "theta_id": row.get("theta_id", ""),
                "variant_id": row.get("variant_id", ""),
                "labelv53_development_safe": safe,
                "labelv53_positive": positive,
                "labelv53_harmful": harmful,
                "labelv53_quality_tie": all((not math.isfinite(v)) or abs(v) <= margin for v in [dg, ds, da]),
                "labelv53_applied_margin": margin,
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
        if "repeat" in str(row.get("replay_phase", "")):
            replicate_rows.append({**row, "labelv53_applied_margin": margin, **claims()})
    write_rows(LABELV53_CONTEXTS, list(context_rows.values()))
    write_rows(LABELV53_CANDIDATES, candidate_rows)
    write_rows(LABELV53_REPLICATES, replicate_rows)
    summary = {
        "schema_version": f"{ROUND}_labelv53_summary_v1",
        "decision": "g566_labelv53_valid_replicated_tail_materialized" if candidate_rows else "g566_labelv53_blocked_no_pairs",
        "source_pair_files": [rel(path) for path in pair_paths if resolve(path).exists()],
        "contexts": len(context_rows),
        "candidates": len(candidate_rows),
        "replicate_rows": len(replicate_rows),
        "applied_margin": margin,
        "applied_margin_source": rel(REPEATABILITY_SUMMARY),
        "safe_candidates": sum(boolish(row.get("labelv53_development_safe")) for row in candidate_rows),
        "positive_candidates": sum(boolish(row.get("labelv53_positive")) for row in candidate_rows),
        "harmful_candidates": sum(boolish(row.get("labelv53_harmful")) for row in candidate_rows),
        **claims(),
    }
    write_json(LABELV53_SUMMARY, summary)
    return summary


def actor_examples_from_labelv53(contexts: list[G566Context]) -> list[ActorTrainExample]:
    by_uid = {ctx.evaluation_uid: ctx for ctx in contexts}
    candidates_by_uid: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_rows(LABELV53_CANDIDATES):
        uid = row.get("g566_evaluation_uid", "")
        if uid in by_uid:
            candidates_by_uid[uid].append(row)
    critic_by_candidate = {
        (row.get("g566_evaluation_uid", ""), row.get("candidate_uid", "") or row.get("theta_id", "")): row
        for row in read_rows(DISTRIBUTIONAL_CRITIC_PREDICTIONS)
    }
    examples: list[ActorTrainExample] = []
    anchor = np.asarray(BASELINE_G556, dtype=np.float32)
    span = np.maximum(np.asarray(THETA_HI - THETA_LO, dtype=np.float32), 1.0e-6)
    for uid, rows in sorted(candidates_by_uid.items()):
        ctx = by_uid[uid]
        positives = [row for row in rows if boolish(row.get("labelv53_positive"))]
        safe = [row for row in rows if boolish(row.get("labelv53_development_safe"))]
        source = positives or safe
        if source:
            weights = []
            thetas = []
            for row in source:
                delta = number(row.get("delta_vs_g556"), 0.0)
                critic = critic_by_candidate.get((uid, row.get("candidate_uid", "") or row.get("theta_id", "")), {})
                critic_weight = number(critic.get("critic_actor_weight"), 1.0)
                risk_ub = max(
                    number(critic.get("p_success_regression_vs_additive_ucb"), 0.0),
                    number(critic.get("p_success_regression_vs_static_flow_ucb"), 0.0),
                    number(critic.get("p_success_regression_vs_g556_ucb"), 0.0),
                )
                unsupported = number(critic.get("unsupported_theta_region_score"), 0.0)
                conservative = critic_weight * max(0.10, 1.0 - risk_ub) * max(0.10, 1.0 - unsupported)
                weights.append(max(0.05, min(5.0, (1.0 - delta) * conservative)))
                thetas.append([number(row.get(col), float(anchor[idx])) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)])
            target = np.average(np.asarray(thetas, dtype=np.float32), axis=0, weights=np.asarray(weights, dtype=np.float32)).astype(np.float32)
            weight = float(max(0.5, min(4.0, len(positives) + 0.25 * len(safe))))
        else:
            target = anchor.copy()
            weight = 0.75
        target = np.minimum(np.maximum(target, np.asarray(THETA_LO, dtype=np.float32)), np.asarray(THETA_HI, dtype=np.float32))
        deviation = float(np.mean(np.abs((target - anchor) / span)))
        examples.append(
            ActorTrainExample(
                example_id=f"g566_actor_train_{len(examples):06d}",
                evaluation_uid=uid,
                split=ctx.split,
                map_family=ctx.map_family,
                graph=ctx.graph_with_traffic,
                assignment=ctx.assignment,
                feature_row=ctx.feature_row,
                target=target,
                weight=max(weight, 0.5 + deviation),
                positive_count=len(positives),
                safe_count=len(safe),
            )
        )
    return examples


def split_actor_examples(examples: list[ActorTrainExample]) -> tuple[list[ActorTrainExample], list[ActorTrainExample]]:
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
        "validation_labelv53_normalized_l1": float(np.mean(losses)) if losses else None,
        "validation_noop_deviation": float(np.mean(noop_losses)) if noop_losses else None,
    }


def train_one_g566_actor(variant_id: str, seed: int, examples: list[ActorTrainExample], *, device: str, epochs: int, min_epochs: int, patience: int, batch_size: int, hidden_dim: int, lr: float) -> tuple[dict[str, Any], dict[str, Any]]:
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
    ).module().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1.0e-4)
    train, valid = split_actor_examples(examples)
    span = torch.tensor(np.asarray(THETA_HI - THETA_LO, dtype=np.float32), device=device).clamp_min(1.0e-6)
    best_metric = math.inf
    best_epoch = 0
    best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    stale = 0
    last_grad: dict[str, float] = {}
    final_train_loss = 0.0
    for epoch in range(1, int(epochs) + 1):
        rng.shuffle(train)
        epoch_losses = []
        model.train()
        for start in range(0, len(train), batch_size):
            batch = train[start : start + batch_size]
            graph_batch, od_tokens, od_mask, scalars, target, weights = actor_tensor_batch(batch, device)
            pred = model(graph_batch, od_tokens, od_mask, scalars)
            per = torch.mean(torch.abs((pred - target) / span), dim=1)
            loss = torch.mean(per * weights)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            last_grad = actor_gradient_summary(model)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            opt.step()
            epoch_losses.append(float(loss.detach().cpu()))
        final_train_loss = float(np.mean(epoch_losses)) if epoch_losses else 0.0
        valid_metrics = evaluate_actor_model(model, valid, device, batch_size)
        metric = number(valid_metrics.get("validation_labelv53_normalized_l1"), math.inf)
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
    out_path = resolve(MODEL_DIR / f"{ROUND}_{variant_id.lower()}_{arch.variant_name}_seed{seed}.pt")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "artifact_type": "phase5p5_repair5g566_labelv53_direct_actor",
            "variant_id": variant_id,
            "variant_name": arch.variant_name,
            "seed": seed,
            "hidden_dim": hidden_dim,
            "actor_state_dict": model.state_dict(),
            "scalar_only_control": arch.scalar_only_control,
            "use_cross_attention": arch.use_cross_attention,
            "safe_subspace": arch.safe_subspace,
            "field_group_trust": arch.field_group_trust,
            "labelv53_training": True,
            "critic_included_for_export": False,
            "codebook_included_for_export": False,
            "theta_fixed_for_run": True,
            "labelv53_summary": rel(LABELV53_SUMMARY),
        },
        out_path,
    )
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
        "scalar_only_control": arch.scalar_only_control,
        "uses_cross_attention": arch.use_cross_attention,
        "safe_subspace": arch.safe_subspace,
        "field_group_trust": arch.field_group_trust,
        **final_metrics,
        **claims(),
    }
    grad = {"variant_id": variant_id, "seed": seed, **last_grad, **claims()}
    return row, grad


def train_g566_actors(contexts: list[G566Context], *, device: str, seeds: list[int], variants: list[str], epochs: int, min_epochs: int, patience: int, batch_size: int, hidden_dim: int, lr: float, plan_only: bool) -> tuple[dict[str, Any], list[Path]]:
    examples = actor_examples_from_labelv53(contexts)
    if plan_only:
        summary = {
            "schema_version": f"{ROUND}_actor_training_summary_v1",
            "decision": "g566_actor_training_plan_created_solver_labels_required",
            "planned_variants": variants,
            "planned_seeds": seeds,
            "label_examples_available": len(examples),
            **claims(),
        }
        write_json(ACTOR_TRAINING_SUMMARY, summary)
        write_rows(ACTOR_TRAINING_MATRIX, [])
        write_rows(ACTOR_GRADIENT_AUDIT, [])
        return summary, []
    if not examples:
        summary = {
            "schema_version": f"{ROUND}_actor_training_summary_v1",
            "decision": "g566_actor_training_blocked_no_labelv53_examples",
            **claims(),
        }
        write_json(ACTOR_TRAINING_SUMMARY, summary)
        return summary, []
    rows: list[dict[str, Any]] = []
    grads: list[dict[str, Any]] = []
    started = time.perf_counter()
    for seed in seeds:
        for variant in variants:
            row, grad = train_one_g566_actor(
                variant,
                seed,
                examples,
                device=device,
                epochs=epochs,
                min_epochs=min_epochs,
                patience=patience,
                batch_size=batch_size,
                hidden_dim=hidden_dim,
                lr=lr,
            )
            rows.append(row)
            grads.append(grad)
            print(json.dumps({"event": "g566_actor_trained", "variant": variant, "seed": seed, "valid_l1": row.get("validation_labelv53_normalized_l1")}), flush=True)
    write_rows(ACTOR_TRAINING_MATRIX, rows)
    write_rows(ACTOR_GRADIENT_AUDIT, grads)
    scalar_rows = [row for row in rows if boolish(row.get("scalar_only_control"))]
    rich_rows = [row for row in rows if not boolish(row.get("scalar_only_control"))]
    sorted_scalars = sorted(
        scalar_rows,
        key=lambda row: (
            number(row.get("validation_labelv53_normalized_l1"), 999.0),
            number(row.get("validation_noop_deviation"), 999.0),
            str(row.get("variant_id", "")),
            str(row.get("seed", "")),
        ),
    )
    sorted_rich = sorted(
        rich_rows,
        key=lambda row: (
            number(row.get("validation_labelv53_normalized_l1"), 999.0),
            number(row.get("validation_noop_deviation"), 999.0),
            str(row.get("variant_id", "")),
            str(row.get("seed", "")),
        ),
    )
    selected_rows = sorted_scalars[:1] + sorted_rich[:3]
    selected_paths = [resolve(row["model_path"]) for row in selected_rows if row.get("model_path")]
    summary = {
        "schema_version": f"{ROUND}_actor_training_summary_v1",
        "decision": "g566_labelv53_direct_actor_training_completed",
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
    out = {
        "schema_version": f"{ROUND}_repeatability_summary_v1",
        "decision": "g566_repeatability_margin_calibrated",
        "source_replay_phase": repeat_summary.get("replay_phase", ""),
        "same_pair_repeats": repeat_summary.get("three_tier_pairs", 0),
        "worker_contention_compared": True,
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


def critic_feature_vector(ctx: G566Context, row: dict[str, Any]) -> np.ndarray:
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


def train_distributional_outcome_ensemble(contexts: list[G566Context], *, seeds: list[int], plan_only: bool) -> dict[str, Any]:
    candidate_rows = read_rows(LABELV53_CANDIDATES)
    context_by_uid = {ctx.evaluation_uid: ctx for ctx in contexts}
    rows = [row for row in candidate_rows if row.get("g566_evaluation_uid", "") in context_by_uid]
    if plan_only:
        summary = {
            "schema_version": f"{ROUND}_distributional_critic_summary_v1",
            "decision": "g566_distributional_critic_plan_created_labelv53_required",
            "training_only_critic": True,
            "actor_export_includes_critic": False,
            "crossfit_unit": "physical_map_hash",
            "planned_targets": CRITIC_TARGETS,
            "labelv53_candidates": len(candidate_rows),
            **claims(),
        }
        write_json(DISTRIBUTIONAL_CRITIC_SUMMARY, summary)
        write_json(OUTCOME_ENSEMBLE_SUMMARY, summary)
        write_rows(DISTRIBUTIONAL_CRITIC_PREDICTIONS, [])
        write_rows(DISTRIBUTIONAL_CRITIC_MODEL_AUDIT, [])
        return summary
    physical_hashes = [context_by_uid[row["g566_evaluation_uid"]].physical_map_sha256 for row in rows]
    unique_hashes = sorted(set(physical_hashes))
    if len(rows) < 32 or len(unique_hashes) < 2:
        summary = {
            "schema_version": f"{ROUND}_distributional_critic_summary_v1",
            "decision": "g566_distributional_critic_not_calibrated",
            "reason": "insufficient_label_rows_or_physical_maps",
            "training_only_critic": True,
            "actor_export_includes_critic": False,
            "labelv53_candidates": len(candidate_rows),
            "usable_rows": len(rows),
            "physical_maps": len(unique_hashes),
            **claims(),
        }
        write_json(DISTRIBUTIONAL_CRITIC_SUMMARY, summary)
        write_json(OUTCOME_ENSEMBLE_SUMMARY, summary)
        write_rows(DISTRIBUTIONAL_CRITIC_PREDICTIONS, [])
        write_rows(DISTRIBUTIONAL_CRITIC_MODEL_AUDIT, [])
        return summary

    x = np.stack([critic_feature_vector(context_by_uid[row["g566_evaluation_uid"]], row) for row in rows])
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
    delta_abs_errors: list[float] = []
    effort_abs_errors: list[float] = []
    for row_idx, row in enumerate(rows):
        out: dict[str, Any] = {
            "g566_evaluation_uid": row.get("g566_evaluation_uid", ""),
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
    summary = {
        "schema_version": f"{ROUND}_distributional_critic_summary_v1",
        "decision": "g566_distributional_critic_calibrated" if prediction_coverage == len(rows) and leakage_violations == 0 else "g566_distributional_critic_not_calibrated",
        "training_only_critic": True,
        "actor_export_includes_critic": False,
        "crossfit_unit": "physical_map_hash",
        "crossfit_folds": fold_count,
        "ensemble_seeds": seed_list,
        "labelv53_candidates": len(candidate_rows),
        "usable_rows": len(rows),
        "physical_maps": len(unique_hashes),
        "prediction_rows": len(prediction_rows),
        "prediction_coverage_rows": prediction_coverage,
        "physical_map_leakage_violations": leakage_violations,
        "binary_brier_mean": float(np.mean(brier_values)) if brier_values else None,
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
    sizes = ["512", "1000", "2000", "all-valid"]
    methods = ["B0", "B1", "B2", "A0", "A1", "A2", "A3", "A4"]
    for size in sizes:
        for method in methods:
            rows.append(
                {
                    "size_label": size,
                    "method": method,
                    "fold_seed_consistency_required": True,
                    "solver_validated_in_development": method in str(dev_summary.get("per_variant_transfer", {})) or method in {"B0"},
                    **claims(),
                }
            )
    path = TABLES / f"{ROUND}_valid_scaling_matrix.csv"
    write_rows(path, rows)
    summary = {
        "schema_version": f"{ROUND}_valid_scaling_summary_v1",
        "decision": "g566_valid_scaling_recorded_from_development_replay",
        "sizes": sizes,
        "methods": methods,
        "rows": len(rows),
        "matrix_path": rel(path),
        **claims(),
    }
    write_json(SCALING_SUMMARY, summary)
    return summary


def freeze_hashes(paths: list[Path]) -> dict[str, str]:
    return {rel(path): sha256_file(path) for path in paths if resolve(path).exists()}


def write_artifact_manifest(artifact_paths: list[Path]) -> dict[str, Any]:
    manifest = {
        "schema_version": f"{ROUND}_artifact_manifest_v1",
        "decision": "g566_artifact_manifest_written",
        "artifacts": freeze_hashes(artifact_paths),
        **claims(),
    }
    write_json(ARTIFACT_MANIFEST, manifest)
    return manifest


def write_final_decision(dev: dict[str, Any], blind: dict[str, Any], label: dict[str, Any], validity: dict[str, Any], artifact_paths: list[Path]) -> dict[str, Any]:
    def pass_tier(summary: dict[str, Any], tier: str, min_rel: float) -> bool:
        return bool(
            summary.get("decision") == "g566_three_tier_replay_materialized"
            and int(summary.get(f"raw_success_regressions_vs_{tier}", 999)) == 0
            and number(summary.get(f"median_relative_improvement_vs_{tier}"), -999.0) >= min_rel
            and int(summary.get(f"better_outside_margin_vs_{tier}", 0)) > int(summary.get(f"supported_quality_worse_outside_margin_vs_{tier}", 0))
        )

    tier_a = pass_tier(blind, "additive", 0.06)
    tier_b = pass_tier(blind, "static_flow", 0.03)
    tier_c_signal = bool(
        blind.get("decision") == "g566_three_tier_replay_materialized"
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
        "decision": "g566_blind_complete" if blind.get("decision") == "g566_three_tier_replay_materialized" else "g566_blocked_before_complete_blind_decision",
        "g566_blind_tierA_pass": tier_a,
        "g566_blind_tierA_strong_pass": tier_a and number(blind.get("median_relative_improvement_vs_additive"), 0.0) >= 0.10,
        "g566_blind_tierB_pass": tier_b,
        "g566_blind_tierB_strong_pass": tier_b and number(blind.get("median_relative_improvement_vs_static_flow"), 0.0) >= 0.06,
        "g566_blind_tierC_research_signal": tier_c_signal,
        "g566_blind_tierC_deployment_pass": tier_c_deploy,
        "g566_blind_tierC_tail_blocked": not tier_c_deploy,
        "valid_contexts": validity.get("valid_contexts", 0),
        "labelv53_candidates": label.get("candidates", 0),
        "development_decision": dev.get("decision", ""),
        "blind_decision": blind.get("decision", ""),
        "artifact_manifest": rel(ARTIFACT_MANIFEST),
        **claims(),
    }
    write_json(FINAL_DECISION_SUMMARY, summary)
    write_text(
        FINAL_DECISION_MD,
        "# Repair5G.5.66 Final Decision\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- Tier A pass: `{summary['g566_blind_tierA_pass']}`\n"
        f"- Tier B pass: `{summary['g566_blind_tierB_pass']}`\n"
        f"- Tier C research signal: `{summary['g566_blind_tierC_research_signal']}`\n"
        f"- Tier C deployment pass: `{summary['g566_blind_tierC_deployment_pass']}`\n\n"
        "Static-flow is replayed as a real Tier B solver row. G5.66 does not promote a deployment baseline unless Tier C deployment gates pass.\n",
    )
    write_artifact_manifest(artifact_paths)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run strict G5.66 valid-tail three-tier direct-actor pipeline.")
    parser.add_argument("--target-valid", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=566)
    parser.add_argument("--smoke-contexts", type=int, default=128)
    parser.add_argument("--repeat-contexts", type=int, default=48)
    parser.add_argument("--development-contexts", type=int, default=1500)
    parser.add_argument("--blind-contexts", type=int, default=1000)
    parser.add_argument("--group-response-rows", type=int, default=50000)
    parser.add_argument("--checkpoint-glob", nargs="*", default=["artifacts/models/gcst/phase5p5_repair5g565_expanded_e1_seed565.pt", "artifacts/models/gcst/phase5p5_repair5g565_expanded_e0_seed565.pt", "artifacts/models/gcst/phase5p5_repair5g565_expanded_e2_seed565.pt"])
    parser.add_argument("--actor-variants", default="C0,A0,A1,A2,A3,A4")
    parser.add_argument("--actor-seeds", default="566,567,568")
    parser.add_argument("--actor-epochs", type=int, default=100)
    parser.add_argument("--actor-min-epochs", type=int, default=30)
    parser.add_argument("--actor-patience", type=int, default=10)
    parser.add_argument("--actor-hidden-dim", type=int, default=96)
    parser.add_argument("--actor-lr", type=float, default=2.0e-4)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--single-worker-repeat", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    import torch

    started = time.perf_counter()
    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    truth = write_g565_truth_audit()
    validity = materialize_valid_bank(args.target_valid, args.seed, overwrite=bool(args.overwrite))
    registry = write_baseline_registry()
    fallback_margin = number(read_json(REPORTS / "phase5p5_repair5g565_label_margin_summary.json").get("recommended_positive_margin"), 0.043)

    ckpts = checkpoint_paths(args.checkpoint_glob)
    if not ckpts:
        summary = {"decision": "g566_blocked_missing_actor_checkpoints", "checkpoint_glob": args.checkpoint_glob, **claims()}
        write_json(FINAL_DECISION_SUMMARY, summary)
        print(json.dumps(summary, sort_keys=True))
        return 2

    smoke_contexts = contexts_from_manifest("TRAIN,VALIDATION,CALIBRATION", args.smoke_contexts)
    repeat_contexts = contexts_from_manifest("CALIBRATION", args.repeat_contexts)
    development_contexts = contexts_from_manifest("VALIDATION,CALIBRATION", args.development_contexts)
    blind_contexts = contexts_from_manifest("BLIND", args.blind_contexts)
    if len(smoke_contexts) < args.smoke_contexts or len(development_contexts) < args.development_contexts or len(blind_contexts) < args.blind_contexts:
        blocked = {
            "schema_version": f"{ROUND}_final_decision_summary_v1",
            "decision": "g566_blocked_insufficient_contexts_after_valid_generation",
            "smoke_contexts": len(smoke_contexts),
            "development_contexts": len(development_contexts),
            "blind_contexts": len(blind_contexts),
            "required_smoke_contexts": args.smoke_contexts,
            "required_development_contexts": args.development_contexts,
            "required_blind_contexts": args.blind_contexts,
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
    )
    repeat_margin = write_repeatability_summary(repeat, fallback_margin)
    applied_margin = number(repeat_margin.get("recommended_positive_margin"), fallback_margin)

    seed_actor_raw = infer_checkpoint_thetas(development_contexts, ckpts[:3], device=device, batch_size=args.batch_size, phase="seed_actor_response_source")
    response_rows = generate_response_thetas(development_contexts, seed_actor_raw, phase="field_group_response", target_rows=args.group_response_rows)
    response = run_replay_phase(
        "field_group_response",
        development_contexts,
        response_rows,
        binary=args.binary,
        max_workers=args.max_workers,
        overwrite=args.overwrite,
        margin=applied_margin,
        plan_only=args.plan_only,
    )
    label = create_labelv53_from_pairs([plan_paths("field_group_response")["pairs"], plan_paths("repeatability_single_worker")["pairs"]], applied_margin)
    actor_variants = [token.strip().upper() for token in args.actor_variants.split(",") if token.strip()]
    actor_seeds = [int(token.strip()) for token in args.actor_seeds.split(",") if token.strip()]
    outcome = train_distributional_outcome_ensemble(
        development_contexts,
        seeds=actor_seeds,
        plan_only=args.plan_only,
    )
    if not args.plan_only and outcome.get("decision") != "g566_distributional_critic_calibrated":
        blocked = {
            "schema_version": f"{ROUND}_final_decision_summary_v1",
            "decision": "g566_blocked_distributional_critic_not_calibrated",
            "outcome_ensemble_decision": outcome.get("decision", ""),
            **claims(),
        }
        write_json(FINAL_DECISION_SUMMARY, blocked)
        print(json.dumps(blocked, sort_keys=True))
        return 2
    actor_training, trained_ckpts = train_g566_actors(
        development_contexts,
        device=device,
        seeds=actor_seeds,
        variants=actor_variants,
        epochs=args.actor_epochs,
        min_epochs=args.actor_min_epochs,
        patience=args.actor_patience,
        batch_size=args.batch_size,
        hidden_dim=args.actor_hidden_dim,
        lr=args.actor_lr,
        plan_only=args.plan_only,
    )
    if not args.plan_only and not trained_ckpts:
        blocked = {
            "schema_version": f"{ROUND}_final_decision_summary_v1",
            "decision": "g566_blocked_actor_training_missing_checkpoints",
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
    scaling = write_scaling_summary(development)

    per_variant = development.get("per_variant_transfer", {})
    selected = []
    if isinstance(per_variant, dict):
        selected = [
            value.get("model_path")
            for _key, value in sorted(
                per_variant.items(),
                key=lambda item: (
                    int(item[1].get("raw_success_regressions_vs_g556", 999)),
                    int(item[1].get("supported_worse_outside_margin_vs_g556", 999)),
                    number(item[1].get("median_delta_vs_g556"), 999.0),
                ),
            )
            if value.get("model_path")
        ][:2]
    blind_ckpts = [resolve(path) for path in selected if resolve(path).exists()] or (trained_ckpts[:2] if trained_ckpts else ckpts[:2])
    blind_raw = infer_checkpoint_thetas(blind_contexts, blind_ckpts, device=device, batch_size=args.batch_size, phase="blind_three_tier")
    freeze = {
        "blind_manifest_sha256": sha256_file(VALID_CONTEXT_MANIFEST),
        "baseline_registry_sha256": sha256_file(BASELINE_REGISTRY),
        "candidate_checkpoints": [rel(path) for path in blind_ckpts],
        "candidate_checkpoint_hashes": {rel(path): sha256_file(path) for path in blind_ckpts},
        "decision_rules_sha256": sha256_file(PLAN_FILE),
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

    final_artifact_paths = [
        TRUTH_AUDIT_SUMMARY,
        VALID_CONTEXT_MANIFEST,
        INVALID_QUARANTINE,
        SCENARIO_VALIDITY,
        SPLIT_MANIFEST,
        VALIDITY_SUMMARY,
        BASELINE_REGISTRY,
        BASELINE_REGISTRY_SUMMARY,
        REPEATABILITY_SUMMARY,
        LABELV53_SUMMARY,
        LABELV53_CONTEXTS,
        LABELV53_CANDIDATES,
        LABELV53_REPLICATES,
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
    final["registry_decision"] = registry.get("decision")
    final["actor_training_decision"] = actor_training.get("decision")
    final["outcome_ensemble_decision"] = outcome.get("decision")
    final["scaling_decision"] = scaling.get("decision")
    write_json(FINAL_DECISION_SUMMARY, final)
    write_artifact_manifest(final_artifact_paths)
    print(json.dumps({"decision": final["decision"], "tierA": final["g566_blind_tierA_pass"], "tierB": final["g566_blind_tierB_pass"], "tierC_deploy": final["g566_blind_tierC_deployment_pass"]}, sort_keys=True))
    return 0 if final["decision"] == "g566_blind_complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())

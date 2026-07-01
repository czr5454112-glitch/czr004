from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pickle
import shutil
import sys
import time
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import run_repair5g567_strict_pipeline as g567  # noqa: E402


PHASE = "gate3b_bounded_pilot"
LABEL_PHASE = "gate3b_label_train"
CALIBRATION_PHASE = "gate3b_calibration"
BOUNDARY_PHASE = "gate3b_boundary_repeat"
DEV_PHASE = "gate3b_development_three_tier"
SEED_PHASE = "gate3b_seed_actor_response"
DEFAULT_STAGE_ROOT = Path(f"outputs/tmp/{g567.ROUND}_{PHASE}")
SUMMARY_NAME = f"{g567.ROUND}_{PHASE}_summary.json"
REPORT_NAME = f"{g567.ROUND}_{PHASE}.md"
CONTEXT_MANIFEST_NAME = f"{g567.ROUND}_{PHASE}_contexts.csv"
REQUIRED_AGENT_TIERS = tuple(g567.G567_AGENT_TIERS)
REPLAY_MATERIALIZED_DECISIONS = {
    "g567_three_tier_replay_materialized",
    "g567_three_tier_replay_materialized_with_infra_timeout_exclusions",
}


def replay_materialized(summary: dict[str, Any]) -> bool:
    return str(summary.get("decision", "")) in REPLAY_MATERIALIZED_DECISIONS


def configure_isolated_outputs(stage_root: Path) -> None:
    stage_root = Path(stage_root)
    g567.OUTPUT_ROOT = stage_root
    g567.ARTIFACT_ROOT = stage_root / "artifacts"
    g567.TABLES = stage_root / "tables"
    g567.REPORTS = stage_root / "reports"
    g567.LOGS = stage_root / "logs"
    g567.MODEL_DIR = stage_root / "models" / "gcst"
    g567.TMP_ROOT = stage_root / "scenario_bank"
    g567.REPLAY_SCENARIO_DIR = stage_root / "replay_scenarios"
    g567.VALID_CONTEXT_MANIFEST = g567.TABLES / f"{g567.ROUND}_{PHASE}_valid_context_manifest.csv"
    g567.INVALID_QUARANTINE = g567.TABLES / f"{g567.ROUND}_{PHASE}_invalid_quarantine.csv"
    g567.SCENARIO_VALIDITY = g567.TABLES / f"{g567.ROUND}_{PHASE}_scenario_validity.csv"
    g567.SPLIT_MANIFEST = g567.TABLES / f"{g567.ROUND}_{PHASE}_physical_map_split_manifest.csv"
    g567.VALIDITY_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_validity_summary.json"
    g567.VALIDITY_MD = g567.REPORTS / f"{g567.ROUND}_{PHASE}_validity.md"
    g567.BASELINE_REGISTRY = g567.TABLES / f"{g567.ROUND}_{PHASE}_three_tier_baseline_registry.csv"
    g567.BASELINE_REGISTRY_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_baseline_registry_summary.json"
    g567.REPEATABILITY_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_repeatability_summary.json"
    g567.LABELV54_CONTEXTS = g567.TABLES / f"{g567.ROUND}_{PHASE}_labelv54_contexts.csv"
    g567.LABELV54_CANDIDATES = g567.TABLES / f"{g567.ROUND}_{PHASE}_labelv54_candidates.csv"
    g567.LABELV54_REPLICATES = g567.TABLES / f"{g567.ROUND}_{PHASE}_labelv54_replicates.csv"
    g567.LABELV54_SAFE_SETS = g567.REPORTS / f"{g567.ROUND}_{PHASE}_labelv54_safe_sets.jsonl"
    g567.LABELV54_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_labelv54_summary.json"
    g567.SOURCE_STATE = g567.REPORTS / f"{g567.ROUND}_{PHASE}_source_state.json"
    g567.MEMORY_SMOKE_3000 = g567.REPORTS / f"{g567.ROUND}_{PHASE}_3000_agent_memory_smoke.json"
    g567.ACTOR_TRAINING_MATRIX = g567.TABLES / f"{g567.ROUND}_{PHASE}_actor_training_matrix.csv"
    g567.ACTOR_GRADIENT_AUDIT = g567.TABLES / f"{g567.ROUND}_{PHASE}_actor_gradient_audit.csv"
    g567.ACTOR_TRAINING_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_actor_training_summary.json"
    g567.OUTCOME_ENSEMBLE_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_outcome_ensemble_summary.json"
    g567.DISTRIBUTIONAL_CRITIC_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_distributional_critic_summary.json"
    g567.DISTRIBUTIONAL_CRITIC_PREDICTIONS = g567.TABLES / f"{g567.ROUND}_{PHASE}_distributional_critic_predictions.csv"
    g567.DISTRIBUTIONAL_CRITIC_MODEL_AUDIT = g567.TABLES / f"{g567.ROUND}_{PHASE}_distributional_critic_model_audit.csv"
    g567.SCALING_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_valid_scaling_summary.json"
    g567.DEVELOPMENT_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_development_three_tier_summary.json"
    g567.BLIND_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_blind_three_tier_summary.json"
    g567.FINAL_DECISION_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_final_decision_summary.json"
    g567.FINAL_DECISION_MD = g567.REPORTS / f"{g567.ROUND}_{PHASE}_final_decision.md"
    g567.ARTIFACT_MANIFEST = g567.REPORTS / f"{g567.ROUND}_{PHASE}_artifact_manifest.json"
    g567.SOLVER_BUDGET_AUDIT = g567.TABLES / f"{g567.ROUND}_{PHASE}_solver_budget_audit.csv"
    g567.SOLVER_BUDGET_AUDIT_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_solver_budget_audit_summary.json"
    g567.PUBLIC_BENCHMARK_INGESTION_MD = g567.REPORTS / f"{g567.ROUND}_{PHASE}_public_benchmark_ingestion.md"
    g567.PUBLIC_BENCHMARK_INGESTION_SUMMARY = g567.REPORTS / f"{g567.ROUND}_{PHASE}_public_benchmark_ingestion_summary.json"
    g567.PUBLIC_MAP_REGISTRY = g567.TABLES / f"{g567.ROUND}_{PHASE}_public_map_registry.csv"
    g567.PUBLIC_SCENARIO_REGISTRY = g567.TABLES / f"{g567.ROUND}_{PHASE}_public_scenario_registry.csv"
    g567.PARENT_MAP_SPLIT_AUDIT = g567.TABLES / f"{g567.ROUND}_{PHASE}_parent_map_split_audit.csv"


def ensure_output_dirs() -> None:
    for path in [
        g567.TABLES,
        g567.REPORTS,
        g567.LOGS,
        g567.MODEL_DIR,
        g567.resolve(g567.TMP_ROOT),
        g567.resolve(g567.REPLAY_SCENARIO_DIR),
    ]:
        path.mkdir(parents=True, exist_ok=True)


def preseed_public_benchmark_metadata() -> dict[str, Any]:
    copies = [
        (ROOT / "outputs/reports/phase5p5_repair5g567_public_benchmark_ingestion.md", g567.PUBLIC_BENCHMARK_INGESTION_MD),
        (ROOT / "outputs/reports/phase5p5_repair5g567_public_benchmark_ingestion_summary.json", g567.PUBLIC_BENCHMARK_INGESTION_SUMMARY),
        (ROOT / "outputs/tables/phase5p5_repair5g567_public_map_registry.csv", g567.PUBLIC_MAP_REGISTRY),
        (ROOT / "outputs/tables/phase5p5_repair5g567_public_scenario_registry.csv", g567.PUBLIC_SCENARIO_REGISTRY),
        (ROOT / "outputs/tables/phase5p5_repair5g567_parent_map_split_audit.csv", g567.PARENT_MAP_SPLIT_AUDIT),
    ]
    missing = [str(src) for src, _dst in copies if not src.exists()]
    if missing:
        raise RuntimeError(f"Gate-3B public benchmark metadata missing: {missing}")
    for src, dst in copies:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    state = g567.public_benchmark_ingestion_state()
    if not state.get("ready"):
        raise RuntimeError(f"Gate-3B public benchmark ingestion is not ready: {state}")
    return state


def row_uid(row: dict[str, Any]) -> str:
    return str(row.get("g567_instance_uid") or g567.stable_uid("gate3b_row", row))


def row_is_public(row: dict[str, Any]) -> bool:
    return str(row.get("map_source_type", "")) == "canonical_public_benchmark_map"


def row_is_official_scenario(row: dict[str, Any]) -> bool:
    return g567.boolish(row.get("official_scenario")) or str(row.get("scenario_source_type", "")).startswith(("movingai_official", "mapf_lns2_official"))


def filter_candidate_rows(rows: list[dict[str, Any]], *, max_free_cells: int, max_area: int) -> list[dict[str, Any]]:
    filtered = []
    for row in rows:
        agents = int(g567.number(row.get("agent_count"), 0))
        area = int(g567.number(row.get("width"), 0)) * int(g567.number(row.get("height"), 0))
        free_cells = int(g567.number(row.get("free_cells"), 0))
        if agents not in REQUIRED_AGENT_TIERS:
            continue
        if free_cells > max_free_cells or area > max_area:
            continue
        filtered.append(row)
    return filtered


def public_fraction(rows: list[dict[str, Any]]) -> float:
    return sum(1 for row in rows if row_is_public(row)) / max(1, len(rows))


def official_scenario_fraction(rows: list[dict[str, Any]]) -> float:
    return sum(1 for row in rows if row_is_official_scenario(row)) / max(1, len(rows))


def parent_map_count(rows: list[dict[str, Any]]) -> int:
    return len({str(row.get("physical_map_sha256", "")) for row in rows if str(row.get("physical_map_sha256", "")).strip()})


def map_family_count(rows: list[dict[str, Any]]) -> int:
    return len({str(row.get("map_family", "")) for row in rows if str(row.get("map_family", "")).strip()})


def row_parent_hash(row: dict[str, Any]) -> str:
    return str(row.get("physical_map_sha256", ""))


def row_agent_tier(row: dict[str, Any]) -> int:
    return int(g567.number(row.get("agent_count"), 0))


def build_parent_groups(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for row in rows:
        parent = row_parent_hash(row)
        if not parent:
            continue
        group = groups.setdefault(
            parent,
            {
                "parent_hash": parent,
                "rows": [],
                "families": set(),
                "tiers": set(),
                "total_rows": 0,
                "public_rows": 0,
                "official_rows": 0,
            },
        )
        group["rows"].append(row)
        group["families"].add(str(row.get("map_family", "")))
        group["tiers"].add(row_agent_tier(row))
        group["total_rows"] += 1
        if row_is_public(row):
            group["public_rows"] += 1
        if row_is_official_scenario(row):
            group["official_rows"] += 1
    return groups


def allocate_gate3b_parent_hashes(
    rows: list[dict[str, Any]],
    *,
    requirements: dict[str, dict[str, Any]],
    required_tiers: tuple[int, ...],
) -> tuple[dict[str, set[str]], dict[str, Any]]:
    groups = build_parent_groups(rows)
    assigned: dict[str, set[str]] = {split: set() for split in requirements}
    owner: dict[str, str] = {}

    def split_groups(split: str) -> list[dict[str, Any]]:
        return [groups[parent] for parent in assigned[split]]

    def capacity(split: str, field: str) -> int:
        return sum(int(group[field]) for group in split_groups(split))

    def families(split: str) -> set[str]:
        output: set[str] = set()
        for group in split_groups(split):
            output.update(group["families"])
        return output

    def tiers(split: str) -> set[int]:
        output: set[int] = set()
        for group in split_groups(split):
            output.update(group["tiers"])
        return output

    def split_metrics(split: str) -> dict[str, Any]:
        req = requirements[split]
        return {
            "parent_map_count": len(assigned[split]),
            "map_family_count": len(families(split)),
            "tier_count": len(tiers(split) & set(required_tiers)),
            "missing_tiers": sorted(set(required_tiers) - tiers(split)),
            "total_rows_capacity": capacity(split, "total_rows"),
            "public_rows_capacity": capacity(split, "public_rows"),
            "official_rows_capacity": capacity(split, "official_rows"),
            "count_target": int(req["count"]),
            "public_target": int(req["public_target"]),
            "official_target": int(req["official_target"]),
            "min_parent_maps": int(req["min_parent_maps"]),
            "min_map_families": int(req["min_map_families"]),
        }

    def deficit(split: str, field: str, target: int) -> int:
        return max(0, target - int(split_metrics(split)[field]))

    def unassigned_groups() -> list[dict[str, Any]]:
        return [groups[parent] for parent in groups if parent not in owner]

    def add_parent(split: str, group: dict[str, Any]) -> None:
        parent = str(group["parent_hash"])
        if parent in owner and owner[parent] != split:
            raise RuntimeError(f"Gate-3B parent hash allocation conflict for {parent}")
        assigned[split].add(parent)
        owner[parent] = split

    def choose_deficit_split(metric_field: str, target_key: str) -> str | None:
        candidates = []
        for split, req in requirements.items():
            target = int(req[target_key])
            gap = deficit(split, metric_field, target)
            if gap <= 0:
                continue
            candidates.append((gap / max(1, target), gap, target, split))
        if not candidates:
            return None
        return max(candidates)[3]

    def group_score(split: str, group: dict[str, Any], *, purpose: str) -> tuple[Any, ...]:
        req = requirements[split]
        current = split_metrics(split)
        public_gap = max(0, int(req["public_target"]) - int(current["public_rows_capacity"]))
        official_gap = max(0, int(req["official_target"]) - int(current["official_rows_capacity"]))
        total_gap = max(0, int(req["count"]) - int(current["total_rows_capacity"]))
        parent_gap = max(0, int(req["min_parent_maps"]) - int(current["parent_map_count"]))
        family_gap = max(0, int(req["min_map_families"]) - int(current["map_family_count"]))
        new_families = set(group["families"]) - families(split)
        missing = set(required_tiers) - tiers(split)
        tier_gain = len(missing & set(group["tiers"]))
        public_gain = min(int(group["public_rows"]), public_gap)
        official_gain = min(int(group["official_rows"]), official_gap)
        total_gain = min(int(group["total_rows"]), total_gap)
        public_overshoot = max(0, int(group["public_rows"]) - max(1, public_gap))
        prefer_synthetic = public_gap <= 0
        return (
            0 if purpose != "official" or int(group["official_rows"]) > 0 else 1,
            0 if purpose != "public" or int(group["public_rows"]) > 0 else 1,
            official_gain / max(1, int(req["official_target"])),
            public_gain / max(1, int(req["public_target"])),
            total_gain / max(1, int(req["count"])),
            min(parent_gap, 1),
            min(family_gap, len(new_families)),
            tier_gain,
            1 if prefer_synthetic and int(group["public_rows"]) == 0 else 0,
            -public_overshoot / max(1, int(req["public_target"])),
            -abs(int(group["total_rows"]) - max(1, total_gap)),
            -int(group["total_rows"]),
            str(next(iter(sorted(group["families"])), "")),
            str(group["parent_hash"]),
        )

    def assign_best(split: str, *, purpose: str, predicate: Any) -> bool:
        candidates = [group for group in unassigned_groups() if predicate(group)]
        if not candidates:
            return False
        best = max(candidates, key=lambda group: group_score(split, group, purpose=purpose))
        add_parent(split, best)
        return True

    for metric_field, target_key, purpose, predicate in [
        ("official_rows_capacity", "official_target", "official", lambda group: int(group["official_rows"]) > 0),
        ("public_rows_capacity", "public_target", "public", lambda group: int(group["public_rows"]) > 0),
    ]:
        while True:
            split = choose_deficit_split(metric_field, target_key)
            if split is None:
                break
            if not assign_best(split, purpose=purpose, predicate=predicate):
                raise RuntimeError(f"Gate-3B global parent allocation lacks {purpose} parent capacity for {split}")

    while True:
        splits_with_missing = [
            (len(set(required_tiers) - tiers(split)), split)
            for split in requirements
            if set(required_tiers) - tiers(split)
        ]
        if not splits_with_missing:
            break
        _missing_count, split = max(splits_with_missing)
        missing = set(required_tiers) - tiers(split)
        if not assign_best(split, purpose="tier", predicate=lambda group, missing=missing: bool(set(group["tiers"]) & missing)):
            raise RuntimeError(f"Gate-3B global parent allocation lacks tier coverage for {split}: {sorted(missing)}")

    for metric_field, target_key, purpose in [
        ("parent_map_count", "min_parent_maps", "parent"),
        ("map_family_count", "min_map_families", "family"),
        ("total_rows_capacity", "count", "total"),
    ]:
        while True:
            split = choose_deficit_split(metric_field, target_key)
            if split is None:
                break
            if purpose == "family":
                existing = families(split)
                predicate = lambda group, existing=existing: bool(set(group["families"]) - existing)
            else:
                predicate = lambda group: True
            if not assign_best(split, purpose=purpose, predicate=predicate):
                raise RuntimeError(f"Gate-3B global parent allocation lacks {purpose} capacity for {split}")

    allocation_blockers = []
    for split, req in requirements.items():
        metrics = split_metrics(split)
        if metrics["public_rows_capacity"] < int(req["public_target"]):
            allocation_blockers.append(f"{split}_public_capacity_{metrics['public_rows_capacity']}_lt_{req['public_target']}")
        if metrics["official_rows_capacity"] < int(req["official_target"]):
            allocation_blockers.append(f"{split}_official_capacity_{metrics['official_rows_capacity']}_lt_{req['official_target']}")
        if metrics["total_rows_capacity"] < int(req["count"]):
            allocation_blockers.append(f"{split}_row_capacity_{metrics['total_rows_capacity']}_lt_{req['count']}")
        if metrics["parent_map_count"] < int(req["min_parent_maps"]):
            allocation_blockers.append(f"{split}_parent_capacity_{metrics['parent_map_count']}_lt_{req['min_parent_maps']}")
        if metrics["map_family_count"] < int(req["min_map_families"]):
            allocation_blockers.append(f"{split}_family_capacity_{metrics['map_family_count']}_lt_{req['min_map_families']}")
        missing_tiers = metrics["missing_tiers"]
        if missing_tiers:
            allocation_blockers.append(f"{split}_missing_tiers_{missing_tiers}")
    if allocation_blockers:
        raise RuntimeError("Gate-3B global parent allocation blockers: " + ",".join(allocation_blockers))

    meta = {
        "strategy": "simultaneous_global_parent_hash_allocation_v1",
        "unassigned_parent_maps": len(groups) - len(owner),
        "split_parent_allocation": {
            split: {
                **split_metrics(split),
                "parent_hashes": sorted(assigned[split])[:12],
                "parent_hash_count": len(assigned[split]),
            }
            for split in requirements
        },
    }
    return assigned, meta


def solve_gate3b_joint_split_allocation(
    rows: list[dict[str, Any]],
    *,
    requirements: dict[str, dict[str, Any]],
    required_tiers: tuple[int, ...],
    parent_concentration_cap_fraction: float = 0.0,
    family_concentration_cap_fraction: float = 0.0,
    milp_time_limit_sec: float = 120.0,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    try:
        from scipy.optimize import Bounds, LinearConstraint, milp
        from scipy.sparse import coo_matrix
    except Exception as exc:  # pragma: no cover - exercised only on missing runtime dependency
        raise RuntimeError(f"gate3b_candidate_pool_joint_split_infeasible: scipy_milp_unavailable:{exc}") from exc

    started = time.perf_counter()
    split_order = [split for split in ["LABEL_TRAIN", "CALIBRATION", "DEVELOPMENT"] if split in requirements]
    groups = build_parent_groups(rows)
    parent_order = sorted(groups)
    family_by_parent = {
        parent: (sorted(str(value) for value in groups[parent]["families"] if str(value).strip()) or ["unknown"])[0]
        for parent in parent_order
    }
    family_order = sorted(set(family_by_parent.values()))
    official_nonpublic_rows = [row_uid(row) for row in rows if row_is_official_scenario(row) and not row_is_public(row)]
    if official_nonpublic_rows:
        raise RuntimeError(
            "gate3b_candidate_pool_joint_split_infeasible:"
            f"official_rows_on_non_public_parent:{len(official_nonpublic_rows)}"
        )

    bucket_rows: dict[tuple[str, int, bool, bool], list[dict[str, Any]]] = {}
    for row in rows:
        parent = row_parent_hash(row)
        if not parent:
            continue
        key = (parent, row_agent_tier(row), bool(row_is_public(row)), bool(row_is_official_scenario(row)))
        bucket_rows.setdefault(key, []).append(row)
    for key in list(bucket_rows):
        bucket_rows[key] = sorted(bucket_rows[key], key=row_uid)
    bucket_keys = sorted(bucket_rows, key=lambda item: (item[0], item[1], int(item[2]), int(item[3])))

    index: dict[tuple[Any, ...], int] = {}
    lower: list[float] = []
    upper: list[float] = []
    integrality: list[int] = []
    objective: list[float] = []

    def add_var(key: tuple[Any, ...], *, ub: float, obj: float = 0.0) -> int:
        idx = len(lower)
        index[key] = idx
        lower.append(0.0)
        upper.append(float(ub))
        integrality.append(1)
        objective.append(float(obj))
        return idx

    for parent in parent_order:
        for split in split_order:
            add_var(("x", parent, split), ub=1.0, obj=1.0e-4)
    for parent, tier, public, official in bucket_keys:
        cap = len(bucket_rows[(parent, tier, public, official)])
        for split in split_order:
            add_var(("n", parent, split, tier, public, official), ub=float(cap), obj=0.0)
    for family in family_order:
        for split in split_order:
            add_var(("y", family, split), ub=1.0, obj=1.0e-5)

    row_indices: list[int] = []
    col_indices: list[int] = []
    data: list[float] = []
    lbs: list[float] = []
    ubs: list[float] = []

    def add_constraint(coeffs: list[tuple[int, float]], lb: float, ub: float) -> None:
        constraint_index = len(lbs)
        for col, value in coeffs:
            if abs(float(value)) > 0.0:
                row_indices.append(constraint_index)
                col_indices.append(int(col))
                data.append(float(value))
        lbs.append(float(lb))
        ubs.append(float(ub))

    for parent in parent_order:
        add_constraint([(index[("x", parent, split)], 1.0) for split in split_order], 0.0, 1.0)

    n_by_parent_split: dict[tuple[str, str], list[int]] = {}
    n_by_split: dict[str, list[int]] = {split: [] for split in split_order}
    n_by_split_public: dict[str, list[int]] = {split: [] for split in split_order}
    n_by_split_official: dict[str, list[int]] = {split: [] for split in split_order}
    n_by_split_tier: dict[tuple[str, int], list[int]] = {(split, tier): [] for split in split_order for tier in required_tiers}
    n_by_split_family: dict[tuple[str, str], list[int]] = {(split, family): [] for split in split_order for family in family_order}
    for parent, tier, public, official in bucket_keys:
        cap = len(bucket_rows[(parent, tier, public, official)])
        family = family_by_parent[parent]
        for split in split_order:
            n_idx = index[("n", parent, split, tier, public, official)]
            x_idx = index[("x", parent, split)]
            add_constraint([(n_idx, 1.0), (x_idx, -float(cap))], -math.inf, 0.0)
            n_by_parent_split.setdefault((parent, split), []).append(n_idx)
            n_by_split[split].append(n_idx)
            n_by_split_family[(split, family)].append(n_idx)
            if public:
                n_by_split_public[split].append(n_idx)
            if official:
                n_by_split_official[split].append(n_idx)
            if tier in required_tiers:
                n_by_split_tier[(split, tier)].append(n_idx)

    for parent in parent_order:
        for split in split_order:
            coeffs = [(idx, 1.0) for idx in n_by_parent_split.get((parent, split), [])]
            coeffs.append((index[("x", parent, split)], -1.0))
            add_constraint(coeffs, 0.0, math.inf)

    for split in split_order:
        req = requirements[split]
        count = int(req["count"])
        public_target = int(req["public_target"])
        official_target = int(req["official_target"])
        add_constraint([(idx, 1.0) for idx in n_by_split[split]], float(count), float(count))
        add_constraint([(idx, 1.0) for idx in n_by_split_public[split]], float(public_target), math.inf)
        add_constraint([(idx, 1.0) for idx in n_by_split_official[split]], float(official_target), math.inf)
        for tier in required_tiers:
            add_constraint([(idx, 1.0) for idx in n_by_split_tier[(split, tier)]], 1.0, math.inf)
        add_constraint([(index[("x", parent, split)], 1.0) for parent in parent_order], float(req["min_parent_maps"]), math.inf)
        if float(parent_concentration_cap_fraction) > 0.0:
            parent_cap = max(1, int(math.floor(count * float(parent_concentration_cap_fraction))))
            for parent in parent_order:
                add_constraint([(idx, 1.0) for idx in n_by_parent_split.get((parent, split), [])], 0.0, float(parent_cap))
        if float(family_concentration_cap_fraction) > 0.0:
            family_cap = max(1, int(math.floor(count * float(family_concentration_cap_fraction))))
            for family in family_order:
                add_constraint([(idx, 1.0) for idx in n_by_split_family[(split, family)]], 0.0, float(family_cap))

    parents_by_family: dict[str, list[str]] = {family: [] for family in family_order}
    for parent, family in family_by_parent.items():
        parents_by_family[family].append(parent)
    for split in split_order:
        for family in family_order:
            y_idx = index[("y", family, split)]
            parent_x = [index[("x", parent, split)] for parent in parents_by_family[family]]
            for x_idx in parent_x:
                add_constraint([(x_idx, 1.0), (y_idx, -1.0)], -math.inf, 0.0)
            add_constraint([(y_idx, 1.0), *[(x_idx, -1.0) for x_idx in parent_x]], -math.inf, 0.0)
        add_constraint([(index[("y", family, split)], 1.0) for family in family_order], float(requirements[split]["min_map_families"]), math.inf)

    matrix = coo_matrix((data, (row_indices, col_indices)), shape=(len(lbs), len(lower))).tocsr()
    result = milp(
        c=np.asarray(objective, dtype=np.float64),
        integrality=np.asarray(integrality, dtype=np.int8),
        bounds=Bounds(np.asarray(lower, dtype=np.float64), np.asarray(upper, dtype=np.float64)),
        constraints=LinearConstraint(matrix, np.asarray(lbs, dtype=np.float64), np.asarray(ubs, dtype=np.float64)),
        options={
            "time_limit": float(milp_time_limit_sec),
            "mip_rel_gap": 0.0,
            "disp": False,
        },
    )
    runtime = time.perf_counter() - started
    if not result.success or result.x is None:
        status = getattr(result, "status", "")
        message = getattr(result, "message", "")
        raise RuntimeError(
            "gate3b_candidate_pool_joint_split_infeasible:"
            f"milp_status={status}:message={message}:runtime_sec={runtime:.3f}"
        )

    solution = np.rint(result.x).astype(np.int64)
    selected_by_split: dict[str, list[dict[str, Any]]] = {split: [] for split in split_order}
    row_allocation: list[dict[str, Any]] = []
    for parent, tier, public, official in bucket_keys:
        capacity = len(bucket_rows[(parent, tier, public, official)])
        for split in split_order:
            n_idx = index[("n", parent, split, tier, public, official)]
            allocated = int(solution[n_idx])
            if allocated <= 0:
                continue
            if allocated > capacity:
                raise RuntimeError(f"gate3b_candidate_pool_joint_split_infeasible:bucket_overallocated:{parent}:{tier}:{public}:{official}")
            chosen = bucket_rows[(parent, tier, public, official)][:allocated]
            selected_by_split[split].extend(chosen)
            row_allocation.append(
                {
                    "split": split,
                    "physical_map_sha256": parent,
                    "map_family": family_by_parent[parent],
                    "map_source_type": "canonical_public_benchmark_map" if public else "synthetic_stress_map",
                    "agent_count": tier,
                    "public_row": bool(public),
                    "official_scenario": bool(official),
                    "allocated_rows": allocated,
                    "capacity_rows": capacity,
                    "first_row_uid": row_uid(chosen[0]),
                    "last_row_uid": row_uid(chosen[-1]),
                }
            )

    parent_capacity_rows = []
    for parent in parent_order:
        group = groups[parent]
        tier_capacity = {
            str(tier): sum(len(bucket_rows.get((parent, tier, public, official), [])) for public in [False, True] for official in [False, True])
            for tier in required_tiers
        }
        official_tier_capacity = {
            str(tier): sum(len(bucket_rows.get((parent, tier, public, True), [])) for public in [False, True])
            for tier in required_tiers
        }
        parent_capacity_rows.append(
            {
                "physical_map_sha256": parent,
                "map_family": family_by_parent[parent],
                "map_source_type": "canonical_public_benchmark_map" if int(group["public_rows"]) > 0 else "synthetic_stress_map",
                "total_rows": int(group["total_rows"]),
                "public_rows": int(group["public_rows"]),
                "official_rows": int(group["official_rows"]),
                "nonofficial_rows": int(group["total_rows"]) - int(group["official_rows"]),
                "tier_capacity_json": json.dumps(tier_capacity, sort_keys=True, separators=(",", ":")),
                "official_tier_capacity_json": json.dumps(official_tier_capacity, sort_keys=True, separators=(",", ":")),
            }
        )

    parent_assignment_rows = []
    for split in split_order:
        selected = selected_by_split[split]
        selected_by_parent = Counter(row_parent_hash(row) for row in selected)
        public_by_parent = Counter(row_parent_hash(row) for row in selected if row_is_public(row))
        official_by_parent = Counter(row_parent_hash(row) for row in selected if row_is_official_scenario(row))
        for parent, rows_selected in sorted(selected_by_parent.items()):
            parent_assignment_rows.append(
                {
                    "split": split,
                    "physical_map_sha256": parent,
                    "map_family": family_by_parent[parent],
                    "map_source_type": "canonical_public_benchmark_map" if int(groups[parent]["public_rows"]) > 0 else "synthetic_stress_map",
                    "selected_rows": int(rows_selected),
                    "selected_public_rows": int(public_by_parent[parent]),
                    "selected_official_rows": int(official_by_parent[parent]),
                    "capacity_rows": int(groups[parent]["total_rows"]),
                    "capacity_public_rows": int(groups[parent]["public_rows"]),
                    "capacity_official_rows": int(groups[parent]["official_rows"]),
                }
            )

    def split_selection_metrics(split: str) -> dict[str, Any]:
        selected = selected_by_split[split]
        parent_counts = Counter(row_parent_hash(row) for row in selected)
        family_counts = Counter(str(row.get("map_family", "")) for row in selected)
        tier_counts = Counter(str(row_agent_tier(row)) for row in selected)
        public_rows = sum(1 for row in selected if row_is_public(row))
        official_rows = sum(1 for row in selected if row_is_official_scenario(row))
        return {
            "rows": len(selected),
            "public_rows": public_rows,
            "official_rows": official_rows,
            "public_fraction": public_rows / max(1, len(selected)),
            "official_scenario_fraction": official_rows / max(1, len(selected)),
            "parent_map_count": len(parent_counts),
            "map_family_count": len(family_counts),
            "agent_tier_counts": dict(sorted(tier_counts.items(), key=lambda item: int(item[0]))),
            "missing_tiers": sorted(set(required_tiers) - {int(key) for key in tier_counts}),
            "public_parent_count": len({row_parent_hash(row) for row in selected if row_is_public(row)}),
            "official_parent_count": len({row_parent_hash(row) for row in selected if row_is_official_scenario(row)}),
            "max_parent_share": max(parent_counts.values(), default=0) / max(1, len(selected)),
            "max_family_share": max(family_counts.values(), default=0) / max(1, len(selected)),
        }

    split_metrics = {split: split_selection_metrics(split) for split in split_order}
    split_by_hash: dict[str, set[str]] = {}
    for split, selected in selected_by_split.items():
        for row in selected:
            split_by_hash.setdefault(row_parent_hash(row), set()).add(split)
    leakage = {key: sorted(value) for key, value in split_by_hash.items() if len(value) > 1}
    blockers = []
    for split, req in requirements.items():
        metrics = split_metrics[split]
        if metrics["rows"] != int(req["count"]):
            blockers.append(f"{split}_rows_{metrics['rows']}_ne_{req['count']}")
        if metrics["public_rows"] < int(req["public_target"]):
            blockers.append(f"{split}_public_{metrics['public_rows']}_lt_{req['public_target']}")
        if metrics["official_rows"] < int(req["official_target"]):
            blockers.append(f"{split}_official_{metrics['official_rows']}_lt_{req['official_target']}")
        if metrics["parent_map_count"] < int(req["min_parent_maps"]):
            blockers.append(f"{split}_parents_{metrics['parent_map_count']}_lt_{req['min_parent_maps']}")
        if metrics["map_family_count"] < int(req["min_map_families"]):
            blockers.append(f"{split}_families_{metrics['map_family_count']}_lt_{req['min_map_families']}")
        if metrics["missing_tiers"]:
            blockers.append(f"{split}_missing_tiers_{metrics['missing_tiers']}")
        if float(parent_concentration_cap_fraction) > 0.0 and metrics["max_parent_share"] > float(parent_concentration_cap_fraction) + 1.0e-12:
            blockers.append(f"{split}_parent_share_{metrics['max_parent_share']}_gt_{parent_concentration_cap_fraction}")
        if float(family_concentration_cap_fraction) > 0.0 and metrics["max_family_share"] > float(family_concentration_cap_fraction) + 1.0e-12:
            blockers.append(f"{split}_family_share_{metrics['max_family_share']}_gt_{family_concentration_cap_fraction}")
    if leakage:
        blockers.append(f"parent_split_leakage_{len(leakage)}")
    if blockers:
        raise RuntimeError("gate3b_candidate_pool_joint_split_infeasible:" + ",".join(blockers))

    meta = {
        "allocator_status": "gate3b_joint_split_allocation_feasible",
        "allocator_strategy": "scipy_milp_parent_tier_official_bucket_v1",
        "milp_status": int(getattr(result, "status", -1)),
        "milp_message": str(getattr(result, "message", "")),
        "milp_fun": float(getattr(result, "fun", 0.0)),
        "milp_mip_gap": float(getattr(result, "mip_gap", 0.0) or 0.0),
        "milp_node_count": int(getattr(result, "mip_node_count", 0) or 0),
        "milp_runtime_sec": runtime,
        "milp_time_limit_sec": float(milp_time_limit_sec),
        "variable_count": len(lower),
        "constraint_count": len(lbs),
        "parent_concentration_cap_fraction": float(parent_concentration_cap_fraction),
        "family_concentration_cap_fraction": float(family_concentration_cap_fraction),
        "parent_capacity_rows": parent_capacity_rows,
        "parent_assignment_rows": parent_assignment_rows,
        "row_allocation_rows": row_allocation,
        "split_metrics": split_metrics,
        "parent_map_split_leakage_count": len(leakage),
        "parent_map_split_leakage_examples": dict(list(leakage.items())[:5]),
        "unassigned_parent_maps": len(parent_order) - len({row["physical_map_sha256"] for row in parent_assignment_rows}),
    }
    return selected_by_split, meta


def take_split_rows(
    rows: list[dict[str, Any]],
    *,
    split: str,
    count: int,
    min_public_fraction: float,
    min_official_fraction: float,
    min_parent_maps: int,
    min_map_families: int,
    required_tiers: tuple[int, ...],
    hash_owner: dict[str, str],
    used_uids: set[str],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    selected_uids: set[str] = set()
    ordered = sorted(
        rows,
        key=lambda row: (
            0 if row_is_public(row) else 1,
            0 if row_is_official_scenario(row) else 1,
            int(g567.number(row.get("agent_count"), 0)),
            str(row.get("map_family", "")),
            str(row.get("physical_map_sha256", "")),
            row_uid(row),
        ),
    )

    def parent_hash(row: dict[str, Any]) -> str:
        return str(row.get("physical_map_sha256", ""))

    def row_tier(row: dict[str, Any]) -> int:
        return int(g567.number(row.get("agent_count"), 0))

    def base_row_key(row: dict[str, Any]) -> tuple[Any, ...]:
        return (
            row_tier(row),
            str(row.get("map_family", "")),
            parent_hash(row),
            row_uid(row),
        )

    def can_take(row: dict[str, Any]) -> bool:
        uid = row_uid(row)
        if uid in used_uids or uid in selected_uids:
            return False
        owner = hash_owner.get(parent_hash(row))
        return owner in {None, split}

    def add(row: dict[str, Any]) -> bool:
        if not can_take(row):
            return False
        uid = row_uid(row)
        selected.append(row)
        selected_uids.add(uid)
        hash_owner[parent_hash(row)] = split
        return True

    public_target = int(math.ceil(count * min_public_fraction))
    official_target = int(math.ceil(count * min_official_fraction))

    def selected_source_count(public: bool) -> int:
        return sum(1 for item in selected if row_is_public(item) is public)

    def selected_official_count() -> int:
        return sum(1 for item in selected if row_is_official_scenario(item))

    def selected_parent_hashes() -> set[str]:
        return {parent_hash(item) for item in selected}

    def selected_families() -> set[str]:
        return {str(item.get("map_family", "")) for item in selected}

    def selected_tiers() -> set[int]:
        return {row_tier(item) for item in selected}

    def group_rows(candidates: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        by_hash: dict[str, list[dict[str, Any]]] = {}
        for row in candidates:
            by_hash.setdefault(parent_hash(row), []).append(row)
        return list(by_hash.values())

    def ordered_groups(
        candidates: list[dict[str, Any]],
        *,
        prefer_existing_parent: bool,
        prefer_new_parent: bool = False,
        prefer_new_family: bool = False,
        prefer_synthetic: bool = False,
        prefer_public: bool = False,
    ) -> list[list[dict[str, Any]]]:
        hashes = selected_parent_hashes()
        families = selected_families()
        tiers = selected_tiers()

        def key(group: list[dict[str, Any]]) -> tuple[Any, ...]:
            group_hash = parent_hash(group[0])
            group_families = {str(row.get("map_family", "")) for row in group}
            group_tiers = {row_tier(row) for row in group}
            group_public = any(row_is_public(row) for row in group)
            group_official = any(row_is_official_scenario(row) for row in group)
            group_family = str(group[0].get("map_family", ""))
            missing_tier_coverage = len((set(required_tiers) - tiers) & group_tiers)
            return (
                0 if prefer_existing_parent and group_hash in hashes else 1,
                0 if prefer_new_parent and group_hash not in hashes else 1,
                0 if prefer_new_family and bool(group_families - families) else 1,
                0 if prefer_synthetic and not group_public else 1,
                0 if prefer_public and group_public else 1,
                0 if group_official else 1,
                -missing_tier_coverage,
                -len(group_tiers),
                -len(group),
                group_family,
                group_hash,
            )

        return sorted(
            [sorted(group, key=base_row_key) for group in group_rows(candidates)],
            key=key,
        )

    def add_from_groups(
        candidates: list[dict[str, Any]],
        *,
        target: int | None,
        metric: Any | None,
        prefer_existing_parent: bool,
        prefer_new_parent: bool = False,
        prefer_new_family: bool = False,
        prefer_synthetic: bool = False,
        prefer_public: bool = False,
        one_row: bool = False,
    ) -> bool:
        if not candidates or len(selected) >= count:
            return False
        groups = ordered_groups(
            candidates,
            prefer_existing_parent=prefer_existing_parent,
            prefer_new_parent=prefer_new_parent,
            prefer_new_family=prefer_new_family,
            prefer_synthetic=prefer_synthetic,
            prefer_public=prefer_public,
        )
        for group in groups:
            added = False
            for row in group:
                if len(selected) >= count:
                    return added
                if target is not None and metric is not None and metric() >= target:
                    return added
                if add(row):
                    added = True
                    if one_row:
                        return True
            if added:
                return True
        return False

    def fill_until(
        predicate: Any,
        *,
        target: int,
        metric: Any,
        prefer_public: bool = False,
        prefer_synthetic: bool = False,
    ) -> None:
        while len(selected) < count and metric() < target:
            candidates = [row for row in ordered if can_take(row) and predicate(row)]
            added = add_from_groups(
                candidates,
                target=target,
                metric=metric,
                prefer_existing_parent=True,
                prefer_public=prefer_public,
                prefer_synthetic=prefer_synthetic,
            )
            if not added:
                break

    def add_one(
        predicate: Any,
        *,
        prefer_new_parent: bool = False,
        prefer_new_family: bool = False,
        prefer_synthetic: bool = False,
        prefer_public: bool = False,
    ) -> bool:
        candidates = [row for row in ordered if can_take(row) and predicate(row)]
        return add_from_groups(
            candidates,
            target=None,
            metric=None,
            prefer_existing_parent=True,
            prefer_new_parent=prefer_new_parent,
            prefer_new_family=prefer_new_family,
            prefer_synthetic=prefer_synthetic,
            prefer_public=prefer_public,
            one_row=True,
        )

    def add_many(
        predicate: Any,
        *,
        prefer_synthetic: bool = False,
        prefer_public: bool = False,
    ) -> bool:
        candidates = [row for row in ordered if can_take(row) and predicate(row)]
        return add_from_groups(
            candidates,
            target=None,
            metric=None,
            prefer_existing_parent=True,
            prefer_synthetic=prefer_synthetic,
            prefer_public=prefer_public,
        )

    fill_until(
        lambda row: row_is_public(row) and row_is_official_scenario(row),
        target=official_target,
        metric=selected_official_count,
        prefer_public=True,
    )
    fill_until(
        row_is_public,
        target=public_target,
        metric=lambda: selected_source_count(True),
        prefer_public=True,
    )
    for tier in required_tiers:
        if tier in selected_tiers():
            continue
        prefer_synthetic = selected_source_count(True) >= public_target
        if add_one(lambda row, tier=tier: row_tier(row) == tier, prefer_synthetic=prefer_synthetic):
            continue

    while len(selected) < count and (parent_map_count(selected) < int(min_parent_maps) or map_family_count(selected) < int(min_map_families)):
        need_parent = parent_map_count(selected) < int(min_parent_maps)
        need_family = map_family_count(selected) < int(min_map_families)
        prefer_synthetic = selected_source_count(True) >= public_target
        added = False
        diversity_attempts = [
            (need_parent, need_family),
            (need_parent, False),
            (False, need_family),
            (False, False),
        ]
        for want_parent, want_family in diversity_attempts:
            hashes = selected_parent_hashes()
            families = selected_families()
            if add_one(
                lambda row, want_parent=want_parent, want_family=want_family, hashes=hashes, families=families: (
                    (not want_parent or parent_hash(row) not in hashes)
                    and (not want_family or str(row.get("map_family", "")) not in families)
                ),
                prefer_new_parent=want_parent,
                prefer_new_family=want_family,
                prefer_synthetic=prefer_synthetic,
            ):
                added = True
                break
        if not added:
            break

    while len(selected) < count:
        prefer_synthetic = selected_source_count(True) >= public_target
        preferred_predicate = (lambda row: not row_is_public(row)) if prefer_synthetic else row_is_public
        if add_many(preferred_predicate, prefer_synthetic=prefer_synthetic, prefer_public=not prefer_synthetic):
            continue
        if not add_many(lambda row: True, prefer_synthetic=prefer_synthetic, prefer_public=not prefer_synthetic):
            break
    if len(selected) < count:
        raise RuntimeError(f"not enough Gate-3B rows for {split}: {len(selected)} < {count}")
    tiers = {int(g567.number(row.get("agent_count"), 0)) for row in selected}
    missing_tiers = sorted(set(required_tiers) - tiers)
    if missing_tiers:
        raise RuntimeError(f"Gate-3B {split} missing required agent tiers: {missing_tiers}")
    if public_fraction(selected) + 1.0e-12 < min_public_fraction:
        raise RuntimeError(f"Gate-3B {split} public fraction below target: {public_fraction(selected)} < {min_public_fraction}")
    if official_scenario_fraction(selected) + 1.0e-12 < min_official_fraction:
        raise RuntimeError(f"Gate-3B {split} official scenario fraction below target: {official_scenario_fraction(selected)} < {min_official_fraction}")
    if parent_map_count(selected) < int(min_parent_maps):
        raise RuntimeError(f"Gate-3B {split} parent-map count below target: {parent_map_count(selected)} < {min_parent_maps}")
    if map_family_count(selected) < int(min_map_families):
        raise RuntimeError(f"Gate-3B {split} map-family count below target: {map_family_count(selected)} < {min_map_families}")
    used_uids.update(selected_uids)
    return selected


def select_gate3b_rows(
    rows: list[dict[str, Any]],
    *,
    label_contexts: int,
    calibration_contexts: int,
    development_contexts: int,
    label_public_fraction_min: float,
    calibration_public_fraction_min: float,
    development_public_fraction_min: float,
    label_official_scenario_fraction_min: float,
    calibration_official_scenario_fraction_min: float,
    development_official_scenario_fraction_min: float,
    label_min_parent_maps: int,
    calibration_min_parent_maps: int,
    development_min_parent_maps: int,
    label_min_map_families: int,
    calibration_min_map_families: int,
    development_min_map_families: int,
    max_train_free_cells: int,
    max_train_area: int,
    parent_concentration_cap_fraction: float = 0.0,
    family_concentration_cap_fraction: float = 0.0,
    milp_time_limit_sec: float = 120.0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    filtered = filter_candidate_rows(rows, max_free_cells=max_train_free_cells, max_area=max_train_area)
    requirements = {
        "LABEL_TRAIN": {
            "count": int(label_contexts),
            "public_target": int(math.ceil(label_contexts * label_public_fraction_min)),
            "official_target": int(math.ceil(label_contexts * label_official_scenario_fraction_min)),
            "min_parent_maps": int(label_min_parent_maps),
            "min_map_families": int(label_min_map_families),
        },
        "CALIBRATION": {
            "count": int(calibration_contexts),
            "public_target": int(math.ceil(calibration_contexts * calibration_public_fraction_min)),
            "official_target": int(math.ceil(calibration_contexts * calibration_official_scenario_fraction_min)),
            "min_parent_maps": int(calibration_min_parent_maps),
            "min_map_families": int(calibration_min_map_families),
        },
        "DEVELOPMENT": {
            "count": int(development_contexts),
            "public_target": int(math.ceil(development_contexts * development_public_fraction_min)),
            "official_target": int(math.ceil(development_contexts * development_official_scenario_fraction_min)),
            "min_parent_maps": int(development_min_parent_maps),
            "min_map_families": int(development_min_map_families),
        },
    }
    selected_by_split, allocation_meta = solve_gate3b_joint_split_allocation(
        filtered,
        requirements=requirements,
        required_tiers=REQUIRED_AGENT_TIERS,
        parent_concentration_cap_fraction=float(parent_concentration_cap_fraction),
        family_concentration_cap_fraction=float(family_concentration_cap_fraction),
        milp_time_limit_sec=float(milp_time_limit_sec),
    )
    label_rows = selected_by_split["LABEL_TRAIN"]
    calibration_rows = selected_by_split["CALIBRATION"]
    development_rows = selected_by_split["DEVELOPMENT"]
    split_by_hash: dict[str, set[str]] = {}
    for split, split_rows in [("LABEL_TRAIN", label_rows), ("CALIBRATION", calibration_rows), ("DEVELOPMENT", development_rows)]:
        for row in split_rows:
            split_by_hash.setdefault(str(row.get("physical_map_sha256", "")), set()).add(split)
    leakage = {key: sorted(value) for key, value in split_by_hash.items() if len(value) > 1}
    split_counts = {
        "LABEL_TRAIN": {
            "public_fraction": public_fraction(label_rows),
            "official_scenario_fraction": official_scenario_fraction(label_rows),
            "parent_map_count": parent_map_count(label_rows),
            "map_family_count": map_family_count(label_rows),
        },
        "CALIBRATION": {
            "public_fraction": public_fraction(calibration_rows),
            "official_scenario_fraction": official_scenario_fraction(calibration_rows),
            "parent_map_count": parent_map_count(calibration_rows),
            "map_family_count": map_family_count(calibration_rows),
        },
        "DEVELOPMENT": {
            "public_fraction": public_fraction(development_rows),
            "official_scenario_fraction": official_scenario_fraction(development_rows),
            "parent_map_count": parent_map_count(development_rows),
            "map_family_count": map_family_count(development_rows),
        },
    }
    minimums = {
        "LABEL_TRAIN": (label_min_parent_maps, label_min_map_families),
        "CALIBRATION": (calibration_min_parent_maps, calibration_min_map_families),
        "DEVELOPMENT": (development_min_parent_maps, development_min_map_families),
    }
    blockers = []
    for split, (min_parents, min_families) in minimums.items():
        if split_counts[split]["parent_map_count"] < int(min_parents):
            blockers.append(f"{split}_parent_maps_{split_counts[split]['parent_map_count']}_lt_{min_parents}")
        if split_counts[split]["map_family_count"] < int(min_families):
            blockers.append(f"{split}_map_families_{split_counts[split]['map_family_count']}_lt_{min_families}")
    if blockers:
        raise RuntimeError("Gate-3B split diversity blockers: " + ",".join(blockers))
    meta = {
        "candidate_pool_rows": len(rows),
        "filtered_candidate_rows": len(filtered),
        "label_train_public_fraction": public_fraction(label_rows),
        "calibration_public_fraction": public_fraction(calibration_rows),
        "development_public_fraction": public_fraction(development_rows),
        "label_train_official_scenario_fraction": official_scenario_fraction(label_rows),
        "calibration_official_scenario_fraction": official_scenario_fraction(calibration_rows),
        "development_official_scenario_fraction": official_scenario_fraction(development_rows),
        "split_diversity": split_counts,
        "parent_map_split_leakage_count": len(leakage),
        "parent_map_split_leakage_examples": dict(list(leakage.items())[:5]),
        "selected_agent_tiers": sorted({int(g567.number(row.get("agent_count"), 0)) for row in label_rows + calibration_rows + development_rows}),
        "selected_map_source_types": dict(Counter(str(row.get("map_source_type", "")) for row in label_rows + calibration_rows + development_rows)),
        "max_train_free_cells": max_train_free_cells,
        "max_train_area": max_train_area,
        "joint_allocator": {
            key: value
            for key, value in allocation_meta.items()
            if key not in {"parent_capacity_rows", "parent_assignment_rows", "row_allocation_rows"}
        },
        "parent_capacity_rows": allocation_meta["parent_capacity_rows"],
        "parent_assignment_rows": allocation_meta["parent_assignment_rows"],
        "row_allocation_rows": allocation_meta["row_allocation_rows"],
    }
    return label_rows, calibration_rows, development_rows, meta


def scenario_source_type(row: dict[str, Any]) -> str:
    existing = str(row.get("scenario_source_type", "")).strip()
    if existing:
        return existing
    if row_is_public(row):
        return "czr004_derived_on_public_parent_map"
    return "czr004_synthetic_derived_scenario"


def prepare_rows(rows: list[dict[str, Any]], *, split: str, prefix: str) -> list[dict[str, Any]]:
    replay_dir = g567.resolve(g567.REPLAY_SCENARIO_DIR)
    prepared = []
    for idx, source in enumerate(rows):
        row = dict(source)
        row["split"] = split
        row["g567_dataset_row_id"] = f"{prefix}_{idx:05d}"
        row["scenario_source_type"] = scenario_source_type(row)
        agents = int(g567.number(row.get("agent_count"), 0))
        budget_ms, base_sec, ltm_iters, budget_role = g567.budget_profile_for_agent_tier(agents, idx)
        row["nominal_budget_ms"] = budget_ms
        row["base_time_limit_sec"] = base_sec
        row["solver_internal_time_limit_sec"] = base_sec
        row["process_hard_timeout_sec"] = g567.process_hard_timeout_for_internal_budget(base_sec)
        row["budget_role"] = budget_role
        row["budget_contract"] = "tier_conditioned_primary_30s_small_40s_1000to2500_60s_3000_hard_timeout_2x"
        row["ltm_max_iterations"] = ltm_iters
        row["horizon_id"] = f"budget{budget_ms}_ltm{ltm_iters}"
        row["scientific_horizon_id"] = row["horizon_id"]
        instance_uid = g567.stable_uid(
            "g567_valid_instance",
            row.get("map", ""),
            row.get("solver_seed", ""),
            row.get("scenario_sha256", ""),
            row.get("physical_map_sha256", ""),
            row.get("assignment_sha256", ""),
            agents,
            budget_ms,
            ltm_iters,
        )
        row["g567_instance_uid"] = instance_uid
        row["g567_evaluation_uid"] = g567.stable_uid("g567_eval", instance_uid, budget_ms, ltm_iters)
        replay = g567.copy_for_replay(row, g567.resolve(row["raw_scenario_path"]), replay_dir)
        row["replay_scenario_path"] = g567.rel(replay)
        row["replay_scenario_sha256"] = g567.sha256_file(replay)
        row["blind_locked"] = False
        prepared.append(row)
    return prepared


def canonicalize_reused_candidate_pool_map_paths(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path_to_hashes: dict[str, set[str]] = {}
    for row in rows:
        raw_map_path = str(row.get("raw_map_path", "")).strip()
        expected = row_parent_hash(row)
        if raw_map_path and expected:
            path_to_hashes.setdefault(raw_map_path, set()).add(expected)
    collision_paths = {path for path, hashes in path_to_hashes.items() if len(hashes) > 1}
    map_dir = g567.resolve(g567.TMP_ROOT) / "maps"
    map_dir.mkdir(parents=True, exist_ok=True)
    canonicalized: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    cache: dict[tuple[str, str], tuple[Path, str]] = {}
    for source in rows:
        row = dict(source)
        raw_map_path = str(row.get("raw_map_path", "")).strip()
        expected = row_parent_hash(row)
        if not raw_map_path or not expected:
            canonicalized.append(row)
            continue
        resolved = g567.resolve(raw_map_path)
        current_sha = g567.sha256_file(resolved)
        needs_canonical = raw_map_path in collision_paths or (current_sha and current_sha != expected)
        if not needs_canonical:
            canonicalized.append(row)
            continue
        benchmark_path = str(row.get("benchmark_source_path", "")).strip()
        benchmark_sha = str(row.get("benchmark_source_sha256", "")).strip()
        can_rebuild_public = (
            row_is_public(row)
            and str(row.get("scenario_source_type", "")) == "czr004_derived_on_public_parent_map"
            and bool(benchmark_path)
        )
        if not can_rebuild_public:
            canonicalized.append(row)
            continue
        cache_key = (benchmark_path, expected)
        if cache_key not in cache:
            source_path = g567.resolve(benchmark_path)
            if not source_path.exists():
                canonicalized.append(row)
                continue
            width, height, grid = g567.read_movingai_map(source_path)
            target = map_dir / f"{g567.safe_token(row.get('map', source_path.stem))}-{expected[:16]}.map"
            actual = g567.g561_bank.write_map(target, grid)
            cache[cache_key] = (target, actual)
        target, actual = cache[cache_key]
        if actual != expected:
            canonicalized.append(row)
            continue
        row["raw_map_path_canonicalized_from"] = raw_map_path
        row["raw_map_path_canonicalization_reason"] = "public_derived_parent_hash_collision_or_stale_copy"
        row["raw_map_path"] = g567.rel(target)
        audit_rows.append(
            {
                "g567_instance_uid": row_uid(row),
                "map": row.get("map", ""),
                "physical_map_sha256": expected,
                "old_raw_map_path": raw_map_path,
                "old_raw_map_sha256": current_sha,
                "new_raw_map_path": row["raw_map_path"],
                "new_raw_map_sha256": actual,
                "benchmark_source_path": benchmark_path,
                "benchmark_source_sha256": benchmark_sha,
            }
        )
        canonicalized.append(row)
    meta = {
        "raw_map_path_collision_paths": len(collision_paths),
        "raw_map_path_collision_examples": sorted(collision_paths)[:10],
        "raw_map_path_canonicalized_rows": len(audit_rows),
        "raw_map_path_canonicalized_unique_maps": len({row["new_raw_map_path"] for row in audit_rows}),
        "raw_map_path_canonicalization_audit_rows": audit_rows,
    }
    return canonicalized, meta


def verify_candidate_pool_contract(
    rows: list[dict[str, Any]],
    *,
    candidate_pool_path: Path,
    candidate_audit_path: Path,
    canonicalized_candidate_pool_path: Path | None,
    canonicalized_candidate_audit_path: Path | None,
    canonicalization_meta: dict[str, Any],
    seed: int,
    context_pool: int,
    candidate_pool_reused: bool,
    candidate_pool_source_commit: str,
    previous_source_state: dict[str, Any],
    source_state: dict[str, Any],
    verify_file_hashes: bool,
) -> dict[str, Any]:
    row_ids = [row_uid(row) for row in rows]
    unique_row_ids = len(set(row_ids))
    parent_hashes = [row_parent_hash(row) for row in rows]
    missing_parent_hashes = sum(1 for value in parent_hashes if not value.strip())
    source_commit = ""
    if candidate_pool_reused:
        source_commit = str(candidate_pool_source_commit).strip() or str(previous_source_state.get("head", "")) or "unknown_legacy_persisted_candidate_pool"
    else:
        source_commit = str(source_state.get("head", ""))
    generator_contract_versions = Counter(str(row.get("scenario_bank_source", "")) for row in rows)
    context_generation_stages = Counter(str(row.get("context_generation_stage", "")) for row in rows)
    feature_materialization_stages = Counter(str(row.get("feature_materialization_stage", "")) for row in rows)
    contract = {
        "candidate_pool_reused": bool(candidate_pool_reused),
        "candidate_pool_path": g567.rel(candidate_pool_path),
        "candidate_pool_manifest_sha256": g567.sha256_file(candidate_pool_path),
        "candidate_pool_validity_path": g567.rel(candidate_audit_path),
        "candidate_pool_validity_sha256": g567.sha256_file(candidate_audit_path),
        "canonicalized_candidate_pool_path": g567.rel(canonicalized_candidate_pool_path) if canonicalized_candidate_pool_path is not None else "",
        "canonicalized_candidate_pool_sha256": g567.sha256_file(canonicalized_candidate_pool_path) if canonicalized_candidate_pool_path is not None else "",
        "canonicalized_candidate_validity_path": g567.rel(canonicalized_candidate_audit_path) if canonicalized_candidate_audit_path is not None else "",
        "canonicalized_candidate_validity_sha256": g567.sha256_file(canonicalized_candidate_audit_path) if canonicalized_candidate_audit_path is not None else "",
        "raw_map_path_canonicalization": {
            key: value
            for key, value in canonicalization_meta.items()
            if key != "raw_map_path_canonicalization_audit_rows"
        },
        "candidate_pool_source_commit": source_commit,
        "selection_allocator_commit": str(source_state.get("head", "")),
        "generation_seed": int(seed),
        "context_pool_target": int(context_pool),
        "public_map_registry_sha256": g567.sha256_file(g567.PUBLIC_MAP_REGISTRY),
        "public_scenario_registry_sha256": g567.sha256_file(g567.PUBLIC_SCENARIO_REGISTRY),
        "row_count": len(rows),
        "unique_row_uid_count": unique_row_ids,
        "duplicate_row_uid_count": len(rows) - unique_row_ids,
        "nonempty_parent_hash_count": len({value for value in parent_hashes if value.strip()}),
        "missing_parent_hash_rows": missing_parent_hashes,
        "generator_contract_versions": dict(generator_contract_versions),
        "context_generation_stages": dict(context_generation_stages),
        "feature_materialization_stages": dict(feature_materialization_stages),
        "verify_file_hashes": bool(verify_file_hashes),
    }
    blockers = []
    if len(rows) != int(context_pool):
        blockers.append(f"context_pool_target_mismatch_rows_{len(rows)}_ne_{int(context_pool)}")
    if unique_row_ids != len(rows):
        blockers.append(f"duplicate_row_uid_count_{len(rows) - unique_row_ids}")
    if missing_parent_hashes:
        blockers.append(f"missing_parent_hash_rows_{missing_parent_hashes}")
    if verify_file_hashes:
        checked = 0
        missing = []
        mismatches = []
        seen: set[tuple[str, str]] = set()
        path_specs: list[tuple[str, str, str]] = []
        for row in rows:
            path_specs.extend(
                [
                    ("raw_map_path", str(row.get("raw_map_path", "")), row_parent_hash(row)),
                    ("benchmark_source_path", str(row.get("benchmark_source_path", "")), str(row.get("benchmark_source_sha256", ""))),
                    ("raw_scenario_path", str(row.get("raw_scenario_path", "")), str(row.get("scenario_sha256", ""))),
                ]
            )
        for field, raw_path, expected_hash in path_specs:
            if not raw_path or not expected_hash:
                continue
            key = (field, raw_path)
            if key in seen:
                continue
            seen.add(key)
            resolved = g567.resolve(raw_path)
            if not resolved.exists():
                missing.append({"field": field, "path": raw_path})
                continue
            digest = g567.sha256_file(resolved)
            checked += 1
            if digest != expected_hash:
                mismatches.append({"field": field, "path": raw_path, "expected": expected_hash, "actual": digest})
        contract.update(
            {
                "referenced_file_hashes_checked": checked,
                "referenced_file_missing_count": len(missing),
                "referenced_file_hash_mismatch_count": len(mismatches),
                "referenced_file_missing_examples": missing[:10],
                "referenced_file_hash_mismatch_examples": mismatches[:10],
            }
        )
        if missing:
            blockers.append(f"referenced_file_missing_count_{len(missing)}")
        if mismatches:
            blockers.append(f"referenced_file_hash_mismatch_count_{len(mismatches)}")
    contract["contract_blockers"] = blockers
    contract["contract_ready"] = not blockers
    return contract


def write_split_feasibility_outputs(
    *,
    all_rows: list[dict[str, Any]],
    selection_meta: dict[str, Any],
    candidate_pool_contract: dict[str, Any],
    source_state: dict[str, Any],
    generation_meta: dict[str, Any],
) -> dict[str, Any]:
    parent_capacity_path = g567.TABLES / f"{g567.ROUND}_gate3b_parent_capacity.csv"
    parent_assignment_path = g567.TABLES / f"{g567.ROUND}_gate3b_parent_assignment.csv"
    row_allocation_path = g567.TABLES / f"{g567.ROUND}_gate3b_row_allocation.csv"
    summary_path = g567.REPORTS / f"{g567.ROUND}_gate3b_split_feasibility_summary.json"
    md_path = g567.REPORTS / f"{g567.ROUND}_gate3b_split_feasibility.md"
    g567.write_rows(parent_capacity_path, selection_meta.get("parent_capacity_rows", []))
    g567.write_rows(parent_assignment_path, selection_meta.get("parent_assignment_rows", []))
    g567.write_rows(row_allocation_path, selection_meta.get("row_allocation_rows", []))
    split_rows = {
        split: [row for row in all_rows if str(row.get("split", "")).upper() == split]
        for split in ["LABEL_TRAIN", "CALIBRATION", "DEVELOPMENT"]
    }
    split_summary = {}
    for split, rows in split_rows.items():
        parent_counts = Counter(row_parent_hash(row) for row in rows)
        family_counts = Counter(str(row.get("map_family", "")) for row in rows)
        tier_counts = Counter(str(row_agent_tier(row)) for row in rows)
        public_rows = sum(1 for row in rows if row_is_public(row))
        official_rows = sum(1 for row in rows if row_is_official_scenario(row))
        split_summary[split] = {
            "rows": len(rows),
            "public_rows": public_rows,
            "official_rows": official_rows,
            "public_fraction": public_rows / max(1, len(rows)),
            "official_scenario_fraction": official_rows / max(1, len(rows)),
            "public_parent_count": len({row_parent_hash(row) for row in rows if row_is_public(row)}),
            "official_parent_count": len({row_parent_hash(row) for row in rows if row_is_official_scenario(row)}),
            "parent_map_count": len(parent_counts),
            "map_family_count": len(family_counts),
            "agent_tier_counts": dict(sorted(tier_counts.items(), key=lambda item: int(item[0]))),
            "max_parent_share": max(parent_counts.values(), default=0) / max(1, len(rows)),
            "max_family_share": max(family_counts.values(), default=0) / max(1, len(rows)),
        }
    joint = dict(selection_meta.get("joint_allocator", {}))
    summary = {
        "schema_version": f"{g567.ROUND}_gate3b_split_feasibility_summary_v1",
        "decision": "gate3b_joint_split_allocation_feasible",
        "allocator_status": joint.get("allocator_status", "gate3b_joint_split_allocation_feasible"),
        "candidate_pool_contract": candidate_pool_contract,
        "generation_meta": generation_meta,
        "source_state": source_state,
        "split_summary": split_summary,
        "parent_map_split_leakage_count": int(selection_meta.get("parent_map_split_leakage_count", 0)),
        "parent_capacity_path": g567.rel(parent_capacity_path),
        "parent_assignment_path": g567.rel(parent_assignment_path),
        "row_allocation_path": g567.rel(row_allocation_path),
        "context_manifest_path": g567.rel(g567.TABLES / CONTEXT_MANIFEST_NAME),
        "milp_status": joint.get("milp_status"),
        "milp_message": joint.get("milp_message"),
        "milp_mip_gap": joint.get("milp_mip_gap"),
        "milp_runtime_sec": joint.get("milp_runtime_sec"),
        "milp_node_count": joint.get("milp_node_count"),
        "full_campaign_launched": False,
        "final_blind_accessed": False,
    }
    g567.write_json(summary_path, summary)
    lines = [
        "# G5.67 Gate-3B Split Feasibility\n",
        f"- decision: `{summary['decision']}`",
        f"- allocator: `{joint.get('allocator_strategy', '')}`",
        f"- MILP status/message/gap/runtime: `{joint.get('milp_status')}` / `{joint.get('milp_message')}` / `{joint.get('milp_mip_gap')}` / `{joint.get('milp_runtime_sec')}`",
        f"- candidate pool reused: `{candidate_pool_contract.get('candidate_pool_reused')}`",
        f"- candidate pool source commit: `{candidate_pool_contract.get('candidate_pool_source_commit')}`",
        f"- selection allocator commit: `{candidate_pool_contract.get('selection_allocator_commit')}`",
        f"- candidate pool manifest SHA256: `{candidate_pool_contract.get('candidate_pool_manifest_sha256')}`",
        f"- parent leakage: `{summary['parent_map_split_leakage_count']}`",
        "",
    ]
    for split, row in split_summary.items():
        lines.extend(
            [
                f"## {split}",
                f"- rows/public/official: `{row['rows']}` / `{row['public_rows']}` / `{row['official_rows']}`",
                f"- public fraction / official fraction: `{row['public_fraction']}` / `{row['official_scenario_fraction']}`",
                f"- parents/families: `{row['parent_map_count']}` / `{row['map_family_count']}`",
                f"- public parents / official parents: `{row['public_parent_count']}` / `{row['official_parent_count']}`",
                f"- max parent share / max family share: `{row['max_parent_share']}` / `{row['max_family_share']}`",
                f"- tier counts: `{json.dumps(row['agent_tier_counts'], sort_keys=True)}`",
                "",
            ]
        )
    g567.write_text(md_path, "\n".join(lines) + "\n")
    return summary


def emit_event(event: str, **fields: Any) -> None:
    payload = {
        "schema_version": f"{g567.ROUND}_{PHASE}_event_v1",
        "event": event,
        "unix": time.time(),
        **fields,
    }
    print(json.dumps(payload, sort_keys=True), flush=True)


def _materialize_one_context(index_row: tuple[int, dict[str, Any]]) -> tuple[int, g567.G567Context, str]:
    index, row = index_row
    ctx = g567.context_from_manifest_row(row)
    if ctx is None:
        raise RuntimeError(f"Gate-3B context materialization failed: {row.get('g567_dataset_row_id')}")
    return index, ctx, str(ctx.feature_row.get("traffic_prior_version", ""))


def materialize_contexts(
    rows: list[dict[str, Any]],
    *,
    phase: str,
    workers: int,
    progress_interval_sec: float,
    cache_path: Path | None = None,
) -> tuple[list[g567.G567Context], dict[str, Any]]:
    total = len(rows)
    started = time.perf_counter()
    row_ids = [str(row.get("g567_dataset_row_id", "")) for row in rows]
    cache = g567.resolve(cache_path) if cache_path is not None else None
    def cache_contract_matches(contexts_cached: list[g567.G567Context]) -> tuple[bool, list[str]]:
        mismatches: list[str] = []
        for index, (row, ctx) in enumerate(zip(rows, contexts_cached)):
            expected_internal = float(g567.number(row.get("base_time_limit_sec"), 0.0))
            expected_hard = float(g567.number(row.get("process_hard_timeout_sec"), 0.0))
            expected_budget_ms = int(g567.number(row.get("nominal_budget_ms"), 0))
            checks = [
                ("base_time_limit_sec", float(ctx.base_time_limit_sec), expected_internal),
                ("process_hard_timeout_sec", float(ctx.process_hard_timeout_sec), expected_hard),
                ("budget_ms", float(ctx.budget_ms), float(expected_budget_ms)),
            ]
            for field, actual, expected in checks:
                if abs(actual - expected) > 1.0e-9:
                    mismatches.append(f"{index}:{row_ids[index]}:{field}:{actual}!={expected}")
            expected_role = str(row.get("budget_role", ""))
            if expected_role and str(ctx.budget_role) != expected_role:
                mismatches.append(f"{index}:{row_ids[index]}:budget_role:{ctx.budget_role}!={expected_role}")
            if len(mismatches) >= 10:
                break
        return not mismatches, mismatches

    if cache is not None and cache.exists():
        with cache.open("rb") as handle:
            cached = pickle.load(handle)
        contexts_cached = list(cached.get("contexts", []))
        cached_ids = list(cached.get("row_ids", []))
        if cached_ids == row_ids and len(contexts_cached) == total:
            cache_ok, cache_mismatches = cache_contract_matches(contexts_cached)
            if not cache_ok:
                emit_event(
                    "gate3b_context_materialization_cache_invalidated",
                    phase=phase,
                    total_contexts=total,
                    cache_path=g567.rel(cache),
                    reason="cached_context_budget_contract_mismatch",
                    mismatch_examples=cache_mismatches,
                )
            else:
                traffic_versions = Counter(str(ctx.feature_row.get("traffic_prior_version", "")) for ctx in contexts_cached)
                meta = {
                    "phase": phase,
                    "contexts": len(contexts_cached),
                    "requested_workers": int(workers),
                    "workers": 0,
                    "elapsed_sec": time.perf_counter() - started,
                    "contexts_per_sec": 0.0,
                    "traffic_prior_versions": dict(traffic_versions),
                    "routing_backend_contract": "bfs",
                    "exact_bfs_lookup_cache": True,
                    "resume_cache_hit": True,
                    "cache_path": g567.rel(cache),
                }
                emit_event("gate3b_context_materialization_resume_cache_hit", **meta)
                return contexts_cached, meta
    actual_workers = max(1, min(int(workers), max(1, total)))
    if os.name == "nt":
        actual_workers = 1
    contexts: list[g567.G567Context | None] = [None] * total
    traffic_versions: Counter[str] = Counter()
    completed = 0
    last_report = started
    emit_event(
        "gate3b_context_materialization_start",
        phase=phase,
        total_contexts=total,
        workers=actual_workers,
        requested_workers=int(workers),
        routing_backend_contract="bfs",
    )

    def record_result(index: int, ctx: g567.G567Context, traffic_version: str) -> None:
        nonlocal completed
        contexts[index] = ctx
        traffic_versions[traffic_version] += 1
        completed += 1

    def maybe_report(force: bool = False) -> None:
        nonlocal last_report
        now = time.perf_counter()
        if not force and now - last_report < max(1.0, float(progress_interval_sec)):
            return
        elapsed = now - started
        emit_event(
            "gate3b_context_materialization_progress",
            phase=phase,
            completed_contexts=completed,
            total_contexts=total,
            workers=actual_workers,
            elapsed_sec=elapsed,
            contexts_per_sec=completed / max(1.0e-9, elapsed),
            traffic_prior_versions=dict(traffic_versions),
        )
        last_report = now

    if actual_workers <= 1:
        for index, row in enumerate(rows):
            out_index, ctx, traffic_version = _materialize_one_context((index, row))
            record_result(out_index, ctx, traffic_version)
            maybe_report()
    else:
        with ProcessPoolExecutor(max_workers=actual_workers) as executor:
            pending = {executor.submit(_materialize_one_context, (index, row)) for index, row in enumerate(rows)}
            while pending:
                done, pending = wait(
                    pending,
                    timeout=max(1.0, float(progress_interval_sec)),
                    return_when=FIRST_COMPLETED,
                )
                for future in done:
                    index, ctx, traffic_version = future.result()
                    record_result(index, ctx, traffic_version)
                maybe_report(force=not done)
    maybe_report(force=True)
    materialized = [ctx for ctx in contexts if ctx is not None]
    meta = {
        "phase": phase,
        "contexts": len(materialized),
        "requested_workers": int(workers),
        "workers": actual_workers,
        "elapsed_sec": time.perf_counter() - started,
        "contexts_per_sec": len(materialized) / max(1.0e-9, time.perf_counter() - started),
        "traffic_prior_versions": dict(traffic_versions),
        "routing_backend_contract": "bfs",
        "exact_bfs_lookup_cache": True,
        "resume_cache_hit": False,
        "cache_path": g567.rel(cache) if cache is not None else "",
    }
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(cache.suffix + ".tmp")
        with tmp.open("wb") as handle:
            pickle.dump({"row_ids": row_ids, "contexts": materialized}, handle)
        tmp.replace(cache)
    emit_event("gate3b_context_materialization_complete", **meta)
    return materialized, meta


def dataset_sha256(contexts: list[g567.G567Context], label_candidate_path: Path) -> str:
    payload = {
        "context_uids": [ctx.evaluation_uid for ctx in contexts],
        "context_identity": [
            {
                "evaluation_uid": ctx.evaluation_uid,
                "physical_map_sha256": ctx.physical_map_sha256,
                "scenario_sha256": ctx.scenario_sha256,
                "assignment_sha256": ctx.assignment_sha256,
            }
            for ctx in contexts
        ],
        "labelv54_candidates_sha256": g567.sha256_file(label_candidate_path),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def directory_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def replay_result_rows(phase: str) -> list[dict[str, str]]:
    return g567.read_rows(g567.plan_paths(phase)["results"])


def crash_rows(rows: list[dict[str, str]]) -> int:
    crashes = 0
    for row in rows:
        if g567.boolish(row.get("process_hard_timeout_exceeded")):
            continue
        classification = str(row.get("returncode_classification", ""))
        if "crash" in classification or classification in {"process_exception", "subprocess_exception"}:
            crashes += 1
    return crashes


def boundary_repeat_theta_rows(contexts: list[g567.G567Context]) -> list[dict[str, Any]]:
    context_ids = {ctx.dataset_row_id for ctx in contexts}
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for candidate in g567.read_rows(g567.LABELV54_CANDIDATES):
        if str(candidate.get("measurement_confidence", "")) != "single_run_boundary_uncertain":
            continue
        context_id = str(candidate.get("g567_dataset_row_id", ""))
        if context_id not in context_ids:
            continue
        theta_id = str(candidate.get("theta_id", ""))
        key = (context_id, theta_id)
        if key in seen:
            continue
        seen.add(key)
        theta = {col: candidate.get(col, "") for col in g567.THETA_NUMERIC_COLUMNS}
        row = {
            "phase": BOUNDARY_PHASE,
            "context_id": context_id,
            "g567_evaluation_uid": candidate.get("g567_evaluation_uid", ""),
            "variant_id": candidate.get("variant_id", "") or "BOUNDARY_REPEAT",
            "variant_name": "labelv54_boundary_repeat",
            "seed": "boundary5",
            "method": f"g567_boundary_repeat_{g567.safe_token(theta_id)[:48]}",
            "model_path": candidate.get("model_path", ""),
            "source_theta_id": theta_id,
            **g567.mode_columns("flow_shield"),
            **theta,
        }
        rows.append(row)
    return rows


def parent_cluster_bootstrap_lower_bound(pairs: list[dict[str, Any]], column: str, *, samples: int = 400, seed: int = 567) -> float | None:
    by_parent: dict[str, list[float]] = {}
    for row in pairs:
        value = g567.number(row.get(column), math.nan)
        parent = str(row.get("physical_map_sha256", "") or row.get("map", ""))
        if parent and math.isfinite(value):
            by_parent.setdefault(parent, []).append(value)
    clusters = [float(np.mean(values)) for values in by_parent.values() if values]
    if not clusters:
        return None
    rng = np.random.default_rng(seed)
    means = []
    arr = np.asarray(clusters, dtype=np.float64)
    for _ in range(max(1, int(samples))):
        draw = rng.choice(arr, size=len(arr), replace=True)
        means.append(float(np.mean(draw)))
    return float(np.quantile(means, 0.05))


def compute_research_signal(development_replay: dict[str, Any], primary: dict[str, Any], *, margin: float) -> dict[str, Any]:
    primary_path = str(primary.get("primary_model_path", ""))
    all_pairs = g567.read_rows(g567.plan_paths(DEV_PHASE)["pairs"])
    primary_pairs = [row for row in all_pairs if str(row.get("model_path", "")) == primary_path]
    additive_lb = parent_cluster_bootstrap_lower_bound(primary_pairs, "relative_improvement_vs_additive")
    static_lb = parent_cluster_bootstrap_lower_bound(primary_pairs, "relative_improvement_vs_static_flow")
    variant_key = None
    for key, row in development_replay.get("per_variant_transfer", {}).items():
        if isinstance(row, dict) and str(row.get("model_path", "")) == primary_path:
            variant_key = key
            variant = row
            break
    else:
        variant = {}
    additive_med = g567.number(variant.get("median_relative_improvement_vs_additive"), math.nan)
    static_med = g567.number(variant.get("median_relative_improvement_vs_static_flow"), math.nan)
    supported_reg_add = int(g567.number(variant.get("supported_success_regressions_vs_additive"), 999))
    supported_reg_static = int(g567.number(variant.get("supported_success_regressions_vs_static_flow"), 999))
    supported_gain_add = int(g567.number(variant.get("supported_success_gains_vs_additive"), 0))
    supported_gain_static = int(g567.number(variant.get("supported_success_gains_vs_static_flow"), 0))
    q95_static = g567.number(variant.get("q95_harmful_delta_vs_static_flow"), development_replay.get("q95_harmful_delta_vs_static_flow", math.inf))
    pair_count = len(primary_pairs)
    tier_a = bool(
        math.isfinite(additive_med)
        and additive_med >= 0.05
        and additive_lb is not None
        and additive_lb > 0.0
        and supported_reg_add <= max(0, math.floor(pair_count * 0.01))
        and supported_gain_add >= supported_reg_add
    )
    tier_b = bool(
        math.isfinite(static_med)
        and static_med > 0.0
        and static_lb is not None
        and static_lb > 0.0
        and supported_reg_static <= max(0, math.floor(pair_count * 0.015))
        and supported_gain_static >= supported_reg_static
        and q95_static <= margin
    )
    blockers = []
    if not tier_a:
        blockers.append("tier_A_additive_signal_missing")
    if not tier_b:
        blockers.append("tier_B_static_flow_signal_missing")
    return {
        "decision": "gate3b_research_signal_positive" if tier_a and tier_b else "gate3b_research_signal_failed",
        "primary_variant_key": variant_key,
        "primary_pair_count": pair_count,
        "tier_A_additive_positive": tier_a,
        "tier_B_static_flow_positive": tier_b,
        "median_relative_improvement_vs_additive": additive_med if math.isfinite(additive_med) else None,
        "median_relative_improvement_vs_static_flow": static_med if math.isfinite(static_med) else None,
        "parent_cluster_bootstrap_lcb05_relative_improvement_vs_additive": additive_lb,
        "parent_cluster_bootstrap_lcb05_relative_improvement_vs_static_flow": static_lb,
        "supported_success_regressions_vs_additive": supported_reg_add,
        "supported_success_regressions_vs_static_flow": supported_reg_static,
        "supported_success_gains_vs_additive": supported_gain_add,
        "supported_success_gains_vs_static_flow": supported_gain_static,
        "q95_harmful_delta_vs_static_flow": q95_static if math.isfinite(q95_static) else None,
        "blockers": blockers,
    }


def gate3b_pass_conditions(summary: dict[str, Any]) -> dict[str, bool]:
    materialization = summary.get("context_materialization", {})
    materialization_versions = [
        set(meta.get("traffic_prior_versions", {}).keys())
        for meta in materialization.values()
        if isinstance(meta, dict)
    ]
    return {
        "source_state_clean": summary.get("source_state", {}).get("decision") == "g567_source_state_clean",
        "public_benchmark_ingestion_ready": bool(summary.get("public_benchmark_ingestion", {}).get("ready")),
        "label_train_contexts_2000_to_4000": 2000 <= int(g567.number(summary.get("label_train_contexts"), 0)) <= 4000,
        "calibration_contexts_present": int(g567.number(summary.get("calibration_contexts"), 0)) >= 1,
        "development_contexts_500_to_1000": 500 <= int(g567.number(summary.get("development_contexts"), 0)) <= 1000,
        "solver_rows_50000_to_100000": 50000 <= int(g567.number(summary.get("total_solver_rows"), 0)) <= 100000,
        "all_agent_tiers_through_3000_present": set(REQUIRED_AGENT_TIERS).issubset(set(summary.get("selected_agent_tiers", []))),
        "label_public_fraction_min_met": float(g567.number(summary.get("label_train_public_fraction"), 0.0)) >= 0.50,
        "calibration_public_fraction_min_met": float(g567.number(summary.get("calibration_public_fraction"), 0.0)) >= 0.70,
        "development_public_fraction_min_met": float(g567.number(summary.get("development_public_fraction"), 0.0)) >= 0.70,
        "official_scenario_minima_met": (
            float(g567.number(summary.get("label_train_official_scenario_fraction"), 0.0)) >= 0.20
            and float(g567.number(summary.get("calibration_official_scenario_fraction"), 0.0)) >= 0.30
            and float(g567.number(summary.get("development_official_scenario_fraction"), 0.0)) >= 0.30
        ),
        "public_and_synthetic_mixture_present": {"canonical_public_benchmark_map", "synthetic_stress_map"}.issubset(set(summary.get("selected_map_source_types", {}).keys())),
        "parent_map_split_leakage_zero": int(g567.number(summary.get("parent_map_split_leakage_count"), 999)) == 0,
        "minimum_parent_maps_and_families": (
            int(g567.number(summary.get("split_diversity", {}).get("LABEL_TRAIN", {}).get("parent_map_count"), 0)) >= 32
            and int(g567.number(summary.get("split_diversity", {}).get("LABEL_TRAIN", {}).get("map_family_count"), 0)) >= 10
            and int(g567.number(summary.get("split_diversity", {}).get("CALIBRATION", {}).get("parent_map_count"), 0)) >= 12
            and int(g567.number(summary.get("split_diversity", {}).get("CALIBRATION", {}).get("map_family_count"), 0)) >= 8
            and int(g567.number(summary.get("split_diversity", {}).get("DEVELOPMENT", {}).get("parent_map_count"), 0)) >= 16
            and int(g567.number(summary.get("split_diversity", {}).get("DEVELOPMENT", {}).get("map_family_count"), 0)) >= 8
        ),
        "traffic_prior_bfs_materialization": bool(materialization_versions) and all(versions == {"traffic_prior_v1_bfs"} for versions in materialization_versions),
        "label_replay_materialized": replay_materialized(summary.get("label_replay", {})),
        "label_replay_planned_executed_exact": bool(summary.get("label_replay", {}).get("planned_executed_exact")),
        "label_replay_expected_baselines_exact": bool(summary.get("label_replay", {}).get("expected_baseline_rows_exact")),
        "development_replay_materialized": replay_materialized(summary.get("development_replay", {})),
        "development_replay_planned_executed_exact": bool(summary.get("development_replay", {}).get("planned_executed_exact")),
        "boundary_repeat_completed_or_none": replay_materialized(summary.get("boundary_repeat", {}))
        or summary.get("boundary_repeat", {}).get("decision") == "gate3b_no_boundary_repeats_required",
        "process_hard_timeouts_are_infra_excluded": (
            int(g567.number(summary.get("unexcluded_process_hard_timeout_rows"), 999)) == 0
            and int(g567.number(summary.get("process_hard_timeout_rows"), 0))
            == int(g567.number(summary.get("process_hard_timeout_rows_excluded_from_scientific_labels"), -1))
        ),
        "critic_calibrated": summary.get("critic_calibration", {}).get("decision") == "g567_distributional_critic_calibrated" and not summary.get("critic_calibration", {}).get("calibration_blockers"),
        "actor_cuda_bf16_training": all(bool(row.get("cuda_bf16_training")) for row in summary.get("actor_training_rows", [])),
        "actor_seed_count_at_least_two": len(summary.get("actor_training_rows", [])) >= 2,
        "actor_gpu_active_hours_2_to_4": 2.0 <= float(g567.number(summary.get("gpu_active_hours"), 0.0)) <= 4.4,
        "exactly_one_primary_actor": summary.get("primary_actor_selection", {}).get("decision") == "g567_one_primary_actor_selected",
        "forbidden_actions_all_false": not any(summary.get("forbidden_actions", {}).values()),
        "no_final_blind_access": not bool(summary.get("final_blind_panel_constructed_or_accessed")),
    }


def write_gate3b_report(summary: dict[str, Any]) -> None:
    path = g567.REPORTS / REPORT_NAME
    text = (
        "# Repair5G.5.67 Gate-3B Bounded Pilot\n\n"
        f"- decision: `{summary.get('decision')}`\n"
        f"- source HEAD: `{summary.get('source_state', {}).get('head', '')}`\n"
        f"- label train contexts: `{summary.get('label_train_contexts')}`\n"
        f"- calibration contexts: `{summary.get('calibration_contexts')}`\n"
        f"- development contexts: `{summary.get('development_contexts')}`\n"
        f"- total solver rows: `{summary.get('total_solver_rows')}`\n"
        f"- scientific-valid solver rows: `{summary.get('scientific_result_valid_solver_rows')}`\n"
        f"- hard-timeout rate: `{summary.get('hard_timeout_rate')}`\n"
        f"- hard-timeout rows excluded from scientific labels: `{summary.get('process_hard_timeout_rows_excluded_from_scientific_labels')}`\n"
        f"- unexcluded hard-timeout rows: `{summary.get('unexcluded_process_hard_timeout_rows')}`\n"
        f"- crash rate: `{summary.get('crash_rate')}`\n"
        f"- label public fraction: `{summary.get('label_train_public_fraction')}`\n"
        f"- calibration public fraction: `{summary.get('calibration_public_fraction')}`\n"
        f"- development public fraction: `{summary.get('development_public_fraction')}`\n"
        f"- official scenario proportion: `{summary.get('official_scenario_proportion')}`\n"
        f"- Label-v5.4 safe/positive/harmful: `{summary.get('labelv54_summary', {}).get('safe_candidates')}` / `{summary.get('labelv54_summary', {}).get('positive_candidates')}` / `{summary.get('labelv54_summary', {}).get('harmful_candidates')}`\n"
        f"- critic decision: `{summary.get('critic_calibration', {}).get('decision')}`\n"
        f"- actor GPU-active hours: `{summary.get('gpu_active_hours')}`\n"
        f"- actor seed count: `{len(summary.get('actor_training_rows', []))}`\n"
        f"- primary actor decision: `{summary.get('primary_actor_selection', {}).get('decision')}`\n"
        f"- research signal: `{summary.get('research_signal', {}).get('decision')}`\n"
        f"- full campaign launched: `{summary.get('forbidden_actions', {}).get('full_100k_generation_launched')}`\n"
        f"- final blind accessed: `{summary.get('final_blind_panel_constructed_or_accessed')}`\n\n"
        "Gate-3B is a bounded pilot only. It does not authorize the full campaign or final blind replay.\n"
    )
    g567.write_text(path, text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the G5.67 Gate-3B bounded pilot without final blind access.")
    parser.add_argument("--stage-root", type=Path, default=DEFAULT_STAGE_ROOT)
    parser.add_argument("--context-pool", type=int, default=8000)
    parser.add_argument("--label-train-contexts", type=int, default=2000)
    parser.add_argument("--calibration-contexts", type=int, default=500)
    parser.add_argument("--development-contexts", type=int, default=500)
    parser.add_argument("--label-replay-solver-rows", type=int, default=60000)
    parser.add_argument("--label-public-fraction-min", type=float, default=0.50)
    parser.add_argument("--calibration-public-fraction-min", type=float, default=0.70)
    parser.add_argument("--development-public-fraction-min", type=float, default=0.70)
    parser.add_argument("--label-official-scenario-fraction-min", type=float, default=0.20)
    parser.add_argument("--calibration-official-scenario-fraction-min", type=float, default=0.30)
    parser.add_argument("--development-official-scenario-fraction-min", type=float, default=0.30)
    parser.add_argument("--label-min-parent-maps", type=int, default=32)
    parser.add_argument("--calibration-min-parent-maps", type=int, default=12)
    parser.add_argument("--development-min-parent-maps", type=int, default=16)
    parser.add_argument("--label-min-map-families", type=int, default=10)
    parser.add_argument("--calibration-min-map-families", type=int, default=8)
    parser.add_argument("--development-min-map-families", type=int, default=8)
    parser.add_argument("--max-train-free-cells", type=int, default=24000)
    parser.add_argument("--max-train-area", type=int, default=32000)
    parser.add_argument("--parent-concentration-cap-fraction", type=float, default=0.15)
    parser.add_argument("--family-concentration-cap-fraction", type=float, default=0.30)
    parser.add_argument("--split-selection-milp-time-limit-sec", type=float, default=120.0)
    parser.add_argument("--split-selection-only", action="store_true")
    parser.add_argument("--skip-candidate-pool-file-hash-check", action="store_true")
    parser.add_argument("--candidate-pool-source-commit", default="")
    parser.add_argument("--seed", type=int, default=4567)
    parser.add_argument("--seed-checkpoint-glob", nargs="*", default=["outputs/external/phase5p5_repair5g567_evidence_ea2cb71b/stage2a/models/gcst/*.pt"])
    parser.add_argument("--actor-seed", type=int, default=567)
    parser.add_argument("--actor-seeds", default="")
    parser.add_argument("--actor-epochs", type=int, default=100000)
    parser.add_argument("--actor-min-epochs", type=int, default=2)
    parser.add_argument("--actor-patience", type=int, default=100000)
    parser.add_argument("--actor-hidden-dim", type=int, default=256)
    parser.add_argument("--actor-lr", type=float, default=2.0e-4)
    parser.add_argument("--min-gpu-active-hours", type=float, default=2.0)
    parser.add_argument("--max-gpu-active-hours", type=float, default=4.0)
    parser.add_argument("--actor-checkpoint-interval-sec", type=float, default=3600.0)
    parser.add_argument("--train-token-budget", type=int, default=12000)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--inference-token-budget", type=int, default=6000)
    parser.add_argument("--inference-progress-interval-sec", type=float, default=30.0)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--materialize-workers", type=int, default=max(1, min(8, os.cpu_count() or 1)))
    parser.add_argument("--materialize-progress-interval-sec", type=float, default=30.0)
    parser.add_argument("--margin", type=float, default=0.043)
    parser.add_argument("--expected-head", default="")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    import torch

    started = time.perf_counter()
    configure_isolated_outputs(args.stage_root)
    ensure_output_dirs()
    public_state = preseed_public_benchmark_metadata()
    previous_source_state = g567.read_json(g567.SOURCE_STATE)
    source_state = g567.write_source_state(args.expected_head)
    if source_state.get("decision") != "g567_source_state_clean":
        summary = {
            "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
            "decision": "gate3b_blocked_source_state_fail_closed",
            "source_state": source_state,
            **g567.claims(),
        }
        g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
        print(json.dumps(summary, sort_keys=True))
        return 2
    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    if not str(device).startswith("cuda") and not bool(args.split_selection_only):
        summary = {
            "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
            "decision": "gate3b_blocked_cuda_bf16_required",
            "device": device,
            **g567.claims(),
        }
        g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
        print(json.dumps(summary, sort_keys=True))
        return 2
    if not (2000 <= int(args.label_train_contexts) <= 4000):
        raise RuntimeError("Gate-3B requires 2000-4000 unique exact-labeled LABEL_TRAIN contexts")
    if int(args.calibration_contexts) < len(REQUIRED_AGENT_TIERS):
        raise RuntimeError("Gate-3B CALIBRATION must contain every required agent tier")
    if not (500 <= int(args.development_contexts) <= 1000):
        raise RuntimeError("Gate-3B requires 500-1000 development contexts")
    if not (50000 <= int(args.label_replay_solver_rows) <= 100000):
        raise RuntimeError("Gate-3B label replay solver rows must stay in 50000-100000")

    start_size = directory_size_bytes(g567.resolve(args.stage_root))
    context_manifest_path = g567.TABLES / CONTEXT_MANIFEST_NAME
    candidate_pool_path = g567.TABLES / f"{g567.ROUND}_{PHASE}_candidate_pool_manifest.csv"
    candidate_audit_path = g567.TABLES / f"{g567.ROUND}_{PHASE}_candidate_pool_validity.csv"
    canonicalized_candidate_pool_path = g567.TABLES / f"{g567.ROUND}_{PHASE}_candidate_pool_manifest_canonicalized.csv"
    canonicalized_candidate_audit_path = g567.TABLES / f"{g567.ROUND}_{PHASE}_candidate_pool_validity_canonicalized.csv"
    canonicalization_audit_path = g567.TABLES / f"{g567.ROUND}_{PHASE}_raw_map_path_canonicalization_audit.csv"
    candidate_pool_contract: dict[str, Any] = {}
    if context_manifest_path.exists() and not bool(args.overwrite):
        all_rows = g567.read_rows(context_manifest_path)
        label_rows = [row for row in all_rows if str(row.get("split", "")).upper() == "LABEL_TRAIN"]
        calibration_rows = [row for row in all_rows if str(row.get("split", "")).upper() == "CALIBRATION"]
        development_rows = [row for row in all_rows if str(row.get("split", "")).upper() == "DEVELOPMENT"]
        generation_meta = {"resumed_context_manifest": True, "generated": len(all_rows), "context_manifest_path": g567.rel(context_manifest_path)}
        audit_rows = g567.read_rows(g567.SCENARIO_VALIDITY)
        split_rows_all = label_rows + calibration_rows + development_rows
        split_by_hash: dict[str, set[str]] = {}
        for row in split_rows_all:
            split_by_hash.setdefault(str(row.get("physical_map_sha256", "")), set()).add(str(row.get("split", "")))
        leakage = {key: sorted(value) for key, value in split_by_hash.items() if len(value) > 1}
        selection_meta = {
            "candidate_pool_rows": len(all_rows),
            "filtered_candidate_rows": len(all_rows),
            "label_train_public_fraction": public_fraction(label_rows),
            "calibration_public_fraction": public_fraction(calibration_rows),
            "development_public_fraction": public_fraction(development_rows),
            "label_train_official_scenario_fraction": official_scenario_fraction(label_rows),
            "calibration_official_scenario_fraction": official_scenario_fraction(calibration_rows),
            "development_official_scenario_fraction": official_scenario_fraction(development_rows),
            "split_diversity": {
                split: {
                    "public_fraction": public_fraction(rows),
                    "official_scenario_fraction": official_scenario_fraction(rows),
                    "parent_map_count": parent_map_count(rows),
                    "map_family_count": map_family_count(rows),
                }
                for split, rows in [("LABEL_TRAIN", label_rows), ("CALIBRATION", calibration_rows), ("DEVELOPMENT", development_rows)]
            },
            "parent_map_split_leakage_count": len(leakage),
            "parent_map_split_leakage_examples": dict(list(leakage.items())[:5]),
            "selected_agent_tiers": sorted({int(g567.number(row.get("agent_count"), 0)) for row in split_rows_all}),
            "selected_map_source_types": dict(Counter(str(row.get("map_source_type", "")) for row in split_rows_all)),
            "max_train_free_cells": int(args.max_train_free_cells),
            "max_train_area": int(args.max_train_area),
        }
    else:
        if candidate_pool_path.exists() and candidate_audit_path.exists() and not bool(args.overwrite):
            manifest_rows = g567.read_rows(candidate_pool_path)
            audit_rows = g567.read_rows(candidate_audit_path)
            generation_meta = {
                "resumed_candidate_pool": True,
                "generated": len(manifest_rows),
                "candidate_pool_path": g567.rel(candidate_pool_path),
                "candidate_audit_path": g567.rel(candidate_audit_path),
            }
            candidate_pool_reused = True
        else:
            audit_rows, manifest_rows, generation_meta = g567.make_generated_contexts(int(args.context_pool), int(args.seed), g567.resolve(g567.TMP_ROOT))
            generation_meta["resumed_candidate_pool"] = False
            generation_meta["candidate_pool_path"] = g567.rel(candidate_pool_path)
            generation_meta["candidate_audit_path"] = g567.rel(candidate_audit_path)
            g567.write_rows(candidate_pool_path, manifest_rows)
            g567.write_rows(candidate_audit_path, audit_rows)
            candidate_pool_reused = False
        manifest_rows, canonicalization_meta = canonicalize_reused_candidate_pool_map_paths(manifest_rows)
        audit_rows, audit_canonicalization_meta = canonicalize_reused_candidate_pool_map_paths(audit_rows)
        if canonicalization_meta.get("raw_map_path_canonicalized_rows") or audit_canonicalization_meta.get("raw_map_path_canonicalized_rows"):
            g567.write_rows(canonicalized_candidate_pool_path, manifest_rows)
            g567.write_rows(canonicalized_candidate_audit_path, audit_rows)
            g567.write_rows(
                canonicalization_audit_path,
                list(canonicalization_meta.get("raw_map_path_canonicalization_audit_rows", []))
                + list(audit_canonicalization_meta.get("raw_map_path_canonicalization_audit_rows", [])),
            )
        else:
            canonicalized_candidate_pool_path = None
            canonicalized_candidate_audit_path = None
        candidate_pool_contract = verify_candidate_pool_contract(
            manifest_rows,
            candidate_pool_path=candidate_pool_path,
            candidate_audit_path=candidate_audit_path,
            canonicalized_candidate_pool_path=canonicalized_candidate_pool_path,
            canonicalized_candidate_audit_path=canonicalized_candidate_audit_path,
            canonicalization_meta=canonicalization_meta,
            seed=int(args.seed),
            context_pool=int(args.context_pool),
            candidate_pool_reused=candidate_pool_reused,
            candidate_pool_source_commit=str(args.candidate_pool_source_commit),
            previous_source_state=previous_source_state,
            source_state=source_state,
            verify_file_hashes=not bool(args.skip_candidate_pool_file_hash_check),
        )
        if not candidate_pool_contract.get("contract_ready"):
            summary = {
                "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
                "decision": "gate3b_candidate_pool_contract_fail_closed",
                "candidate_pool_contract": candidate_pool_contract,
                "source_state": source_state,
                **g567.claims(),
            }
            g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
            print(json.dumps(summary, sort_keys=True))
            return 2
        g567.update_remote_map_registries(g567.resolve(g567.TMP_ROOT) / "maps")
        try:
            label_rows_raw, calibration_rows_raw, development_rows_raw, selection_meta = select_gate3b_rows(
                manifest_rows,
                label_contexts=int(args.label_train_contexts),
                calibration_contexts=int(args.calibration_contexts),
                development_contexts=int(args.development_contexts),
                label_public_fraction_min=float(args.label_public_fraction_min),
                calibration_public_fraction_min=float(args.calibration_public_fraction_min),
                development_public_fraction_min=float(args.development_public_fraction_min),
                label_official_scenario_fraction_min=float(args.label_official_scenario_fraction_min),
                calibration_official_scenario_fraction_min=float(args.calibration_official_scenario_fraction_min),
                development_official_scenario_fraction_min=float(args.development_official_scenario_fraction_min),
                label_min_parent_maps=int(args.label_min_parent_maps),
                calibration_min_parent_maps=int(args.calibration_min_parent_maps),
                development_min_parent_maps=int(args.development_min_parent_maps),
                label_min_map_families=int(args.label_min_map_families),
                calibration_min_map_families=int(args.calibration_min_map_families),
                development_min_map_families=int(args.development_min_map_families),
                max_train_free_cells=int(args.max_train_free_cells),
                max_train_area=int(args.max_train_area),
                parent_concentration_cap_fraction=float(args.parent_concentration_cap_fraction),
                family_concentration_cap_fraction=float(args.family_concentration_cap_fraction),
                milp_time_limit_sec=float(args.split_selection_milp_time_limit_sec),
            )
        except RuntimeError as exc:
            summary = {
                "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
                "decision": "gate3b_candidate_pool_joint_split_infeasible",
                "error": str(exc),
                "candidate_pool_contract": candidate_pool_contract,
                "source_state": source_state,
                **g567.claims(),
            }
            g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
            print(json.dumps(summary, sort_keys=True))
            return 2
        label_rows = prepare_rows(label_rows_raw, split="LABEL_TRAIN", prefix="g567_gate3b_label_train")
        calibration_rows = prepare_rows(calibration_rows_raw, split="CALIBRATION", prefix="g567_gate3b_calibration")
        development_rows = prepare_rows(development_rows_raw, split="DEVELOPMENT", prefix="g567_gate3b_development")
        all_rows = label_rows + calibration_rows + development_rows
        g567.write_rows(g567.VALID_CONTEXT_MANIFEST, all_rows)
        g567.write_rows(g567.SCENARIO_VALIDITY, audit_rows)
        g567.write_rows(context_manifest_path, all_rows)
        split_feasibility = write_split_feasibility_outputs(
            all_rows=all_rows,
            selection_meta=selection_meta,
            candidate_pool_contract=candidate_pool_contract,
            source_state=source_state,
            generation_meta=generation_meta,
        )
        if bool(args.split_selection_only):
            summary = {
                "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
                "decision": "gate3b_joint_split_allocation_feasible",
                "split_feasibility": split_feasibility,
                "candidate_pool_contract": candidate_pool_contract,
                "source_state": source_state,
                "forbidden_actions": {
                    "context_materialization_launched": False,
                    "a5_inference_launched": False,
                    "solver_replay_launched": False,
                    "gpu_training_launched": False,
                    "full_100k_generation_launched": False,
                    "final_blind_panel_constructed_or_accessed": False,
                },
                **g567.claims(),
            }
            g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
            print(json.dumps(summary, sort_keys=True))
            return 0
    label_contexts, label_materialization = materialize_contexts(
        label_rows,
        phase="label_train",
        workers=int(args.materialize_workers),
        progress_interval_sec=float(args.materialize_progress_interval_sec),
        cache_path=g567.TABLES / f"{g567.ROUND}_{PHASE}_label_train_contexts.pkl",
    )
    calibration_contexts, calibration_materialization = materialize_contexts(
        calibration_rows,
        phase="calibration",
        workers=int(args.materialize_workers),
        progress_interval_sec=float(args.materialize_progress_interval_sec),
        cache_path=g567.TABLES / f"{g567.ROUND}_{PHASE}_calibration_contexts.pkl",
    )
    development_contexts, development_materialization = materialize_contexts(
        development_rows,
        phase="development",
        workers=int(args.materialize_workers),
        progress_interval_sec=float(args.materialize_progress_interval_sec),
        cache_path=g567.TABLES / f"{g567.ROUND}_{PHASE}_development_contexts.pkl",
    )
    memory_smoke = g567.write_3000_agent_memory_smoke(device, int(args.actor_hidden_dim))
    g567.write_baseline_registry()
    seed_ckpts = g567.checkpoint_paths(args.seed_checkpoint_glob)
    if not seed_ckpts:
        raise RuntimeError(f"Gate-3B missing seed actor checkpoint: {args.seed_checkpoint_glob}")
    exact_label_contexts = label_contexts + calibration_contexts
    seed_raw = g567.infer_checkpoint_thetas(
        exact_label_contexts,
        seed_ckpts[:1],
        device=device,
        batch_size=max(1, int(args.batch_size)),
        phase=SEED_PHASE,
        token_budget=max(0, int(args.inference_token_budget)),
        progress_interval_sec=float(args.inference_progress_interval_sec),
        output_path=g567.TABLES / f"{g567.ROUND}_{SEED_PHASE}_checkpoint_thetas.csv",
        resume=not bool(args.overwrite),
    )
    label_baseline_rows = len(exact_label_contexts) * 3
    response_target_rows = max(len(exact_label_contexts), int(args.label_replay_solver_rows) - label_baseline_rows)
    response_rows = g567.generate_response_thetas(
        exact_label_contexts,
        seed_raw,
        phase=LABEL_PHASE,
        target_rows=response_target_rows,
        allow_selected_primary_30s_surface=True,
    )
    planned_label_solver_rows = label_baseline_rows + len(response_rows)
    if planned_label_solver_rows != int(args.label_replay_solver_rows):
        raise RuntimeError(
            "Gate-3B label replay solver-row target not honored: "
            f"planned={planned_label_solver_rows} requested={int(args.label_replay_solver_rows)} "
            f"baseline_rows={label_baseline_rows} response_rows={len(response_rows)}"
        )
    if not (50000 <= planned_label_solver_rows <= 100000):
        raise RuntimeError(f"Gate-3B planned label solver rows outside bounded range: {planned_label_solver_rows}")
    label_replay = g567.run_replay_phase(
        LABEL_PHASE,
        exact_label_contexts,
        response_rows,
        binary=args.binary,
        max_workers=max(1, int(args.max_workers)),
        overwrite=bool(args.overwrite),
        margin=float(args.margin),
        plan_only=False,
    )
    if not replay_materialized(label_replay):
        summary = {
            "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
            "decision": "gate3b_blocked_label_replay_not_materialized",
            "label_replay": label_replay,
            "source_state": source_state,
            **g567.claims(),
        }
        g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
        print(json.dumps(summary, sort_keys=True))
        return 2
    prelim_label_summary = g567.create_labelv54_from_pairs([g567.plan_paths(LABEL_PHASE)["pairs"]], float(args.margin))
    boundary_rows = boundary_repeat_theta_rows(exact_label_contexts)
    if boundary_rows:
        boundary_context_ids = {str(row.get("context_id", "")) for row in boundary_rows}
        boundary_contexts = [ctx for ctx in exact_label_contexts if ctx.dataset_row_id in boundary_context_ids]
        boundary_replay = g567.run_replay_phase(
            BOUNDARY_PHASE,
            boundary_contexts,
            boundary_rows,
            binary=args.binary,
            max_workers=1,
            overwrite=bool(args.overwrite),
            margin=float(args.margin),
            plan_only=False,
            repeat_count=5,
        )
        if not replay_materialized(boundary_replay):
            summary = {
                "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
                "decision": "gate3b_blocked_boundary_repeat_not_materialized",
                "label_replay": label_replay,
                "prelim_labelv54_summary": prelim_label_summary,
                "boundary_repeat": boundary_replay,
                "source_state": source_state,
                **g567.claims(),
            }
            g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
            print(json.dumps(summary, sort_keys=True))
            return 2
        label_summary = g567.create_labelv54_from_pairs(
            [g567.plan_paths(LABEL_PHASE)["pairs"], g567.plan_paths(BOUNDARY_PHASE)["pairs"]],
            float(args.margin),
        )
    else:
        boundary_replay = {
            "schema_version": f"{g567.ROUND}_{BOUNDARY_PHASE}_summary_v1",
            "decision": "gate3b_no_boundary_repeats_required",
            "planned_rows": 0,
            "executed_rows": 0,
            "scientific_result_valid_rows": 0,
            "process_hard_timeout_rows": 0,
            "process_hard_timeout_rows_excluded_from_scientific_labels": 0,
            "unexcluded_process_hard_timeout_rows": 0,
            **g567.claims(),
        }
        label_summary = prelim_label_summary
    exact_contexts = int(g567.number(label_summary.get("label_train_unique_exact_labeled_contexts"), 0))
    if not (2000 <= exact_contexts <= 4000):
        summary = {
            "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
            "decision": "gate3b_blocked_label_train_unique_context_count",
            "label_train_unique_exact_labeled_contexts": exact_contexts,
            "required_range": [2000, 4000],
            "labelv54_summary": label_summary,
            **g567.claims(),
        }
        g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
        print(json.dumps(summary, sort_keys=True))
        return 2
    critic = g567.train_distributional_outcome_ensemble(exact_label_contexts, seeds=[int(args.actor_seed), int(args.actor_seed) + 1, int(args.actor_seed) + 2], plan_only=False)
    if critic.get("decision") != "g567_distributional_critic_calibrated" or critic.get("calibration_blockers"):
        summary = {
            "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
            "decision": "gate3b_blocked_distributional_critic_not_calibrated",
            "label_replay": label_replay,
            "boundary_repeat": boundary_replay,
            "labelv54_summary": label_summary,
            "critic_calibration": critic,
            "source_state": source_state,
            **g567.claims(),
        }
        g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
        print(json.dumps(summary, sort_keys=True))
        return 2
    examples = g567.actor_examples_from_labelv54(exact_label_contexts)
    if not examples:
        raise RuntimeError("Gate-3B produced no Label-v5.4 actor training examples")
    training_dataset_sha = dataset_sha256(exact_label_contexts, g567.LABELV54_CANDIDATES)
    actor_seed_values = [
        int(token.strip())
        for token in str(args.actor_seeds).split(",")
        if token.strip()
    ] or [int(args.actor_seed), int(args.actor_seed) + 1]
    actor_seed_values = actor_seed_values[: max(2, min(len(actor_seed_values), 4))]
    if len(actor_seed_values) < 2:
        raise RuntimeError("Gate-3B requires at least two A5 actor seeds")
    per_seed_min_gpu_hours = float(args.min_gpu_active_hours) / len(actor_seed_values)
    per_seed_max_gpu_hours = float(args.max_gpu_active_hours) / len(actor_seed_values)
    actor_rows: list[dict[str, Any]] = []
    grad_rows: list[dict[str, Any]] = []
    for actor_seed in actor_seed_values:
        actor_row, grad_row = g567.train_one_g567_actor(
            "A5",
            int(actor_seed),
            examples,
            device=device,
            epochs=int(args.actor_epochs),
            min_epochs=int(args.actor_min_epochs),
            patience=int(args.actor_patience),
            batch_size=max(1, int(args.batch_size)),
            token_budget=max(1, int(args.train_token_budget)),
            hidden_dim=int(args.actor_hidden_dim),
            lr=float(args.actor_lr),
            checkpoint_interval_sec=float(args.actor_checkpoint_interval_sec),
            resume=True,
            diagnostic_only=False,
            no_performance_claim=True,
            training_context_uids=[ctx.evaluation_uid for ctx in exact_label_contexts],
            training_dataset_sha256=training_dataset_sha,
            source_commit=source_state.get("head", ""),
            min_gpu_active_hours=per_seed_min_gpu_hours,
            max_gpu_active_hours=per_seed_max_gpu_hours,
        )
        actor_rows.append(actor_row)
        grad_rows.append(grad_row)
    g567.write_rows(g567.ACTOR_TRAINING_MATRIX, actor_rows)
    g567.write_rows(g567.ACTOR_GRADIENT_AUDIT, grad_rows)
    gpu_active_hours = sum(float(g567.number(row.get("gpu_active_hours"), 0.0)) for row in actor_rows)
    actor_training_summary = {
        "schema_version": f"{g567.ROUND}_{PHASE}_actor_training_summary_v1",
        "decision": "gate3b_a5_actor_training_completed",
        "selected_development_checkpoint_paths": [row.get("model_path", "") for row in actor_rows],
        "rows": actor_rows,
        "gradient_rows": grad_rows,
        "cuda_bf16_training": all(bool(row.get("cuda_bf16_training")) for row in actor_rows),
        "token_budget_batching": all(bool(row.get("token_budget_batching")) for row in actor_rows),
        "actor_seed_count": len(actor_rows),
        "gpu_active_hours": gpu_active_hours,
        "per_seed_min_gpu_active_hours": per_seed_min_gpu_hours,
        "per_seed_max_gpu_active_hours": per_seed_max_gpu_hours,
        **g567.claims(),
    }
    g567.write_json(g567.ACTOR_TRAINING_SUMMARY, actor_training_summary)
    actor_ckpts = [g567.resolve(row["model_path"]) for row in actor_rows]
    dev_raw = g567.infer_checkpoint_thetas(
        development_contexts,
        actor_ckpts,
        device=device,
        batch_size=max(1, int(args.batch_size)),
        phase=DEV_PHASE,
        token_budget=max(0, int(args.inference_token_budget)),
        progress_interval_sec=float(args.inference_progress_interval_sec),
        output_path=g567.TABLES / f"{g567.ROUND}_{DEV_PHASE}_checkpoint_thetas.csv",
        resume=not bool(args.overwrite),
    )
    development_replay = g567.run_replay_phase(
        DEV_PHASE,
        development_contexts,
        dev_raw,
        binary=args.binary,
        max_workers=max(1, int(args.max_workers)),
        overwrite=bool(args.overwrite),
        margin=float(args.margin),
        plan_only=False,
        include_no_ltm=True,
    )
    primary = g567.select_primary_actor_checkpoint(development_replay)
    research_signal = compute_research_signal(development_replay, primary, margin=float(args.margin))
    label_result_rows = replay_result_rows(LABEL_PHASE)
    boundary_result_rows = replay_result_rows(BOUNDARY_PHASE) if boundary_rows else []
    dev_result_rows = replay_result_rows(DEV_PHASE)
    total_solver_rows = (
        int(g567.number(label_replay.get("executed_rows"), 0))
        + int(g567.number(boundary_replay.get("executed_rows"), 0))
        + int(g567.number(development_replay.get("executed_rows"), 0))
    )
    timeout_rows = (
        int(g567.number(label_replay.get("process_hard_timeout_rows"), 0))
        + int(g567.number(boundary_replay.get("process_hard_timeout_rows"), 0))
        + int(g567.number(development_replay.get("process_hard_timeout_rows"), 0))
    )
    excluded_timeout_rows = (
        int(g567.number(label_replay.get("process_hard_timeout_rows_excluded_from_scientific_labels"), 0))
        + int(g567.number(boundary_replay.get("process_hard_timeout_rows_excluded_from_scientific_labels"), 0))
        + int(g567.number(development_replay.get("process_hard_timeout_rows_excluded_from_scientific_labels"), 0))
    )
    unexcluded_timeout_rows = (
        int(g567.number(label_replay.get("unexcluded_process_hard_timeout_rows"), 0))
        + int(g567.number(boundary_replay.get("unexcluded_process_hard_timeout_rows"), 0))
        + int(g567.number(development_replay.get("unexcluded_process_hard_timeout_rows"), 0))
    )
    scientific_valid_solver_rows = (
        int(g567.number(label_replay.get("scientific_result_valid_rows"), 0))
        + int(g567.number(boundary_replay.get("scientific_result_valid_rows"), 0))
        + int(g567.number(development_replay.get("scientific_result_valid_rows"), 0))
    )
    crash_count = crash_rows(label_result_rows) + crash_rows(boundary_result_rows) + crash_rows(dev_result_rows)
    official_scenario_rows = sum(1 for row in all_rows if row_is_official_scenario(row))
    end_size = directory_size_bytes(g567.resolve(args.stage_root))
    forbidden_actions = {
        "full_100k_generation_launched": False,
        "million_row_solver_acquisition_launched": False,
        "forty_eight_hour_training_launched": False,
        "final_blind_panel_constructed_or_accessed": False,
        "final_blind_solver_replay_launched": False,
    }
    summary = {
        "schema_version": f"{g567.ROUND}_{PHASE}_summary_v1",
        "decision": "gate3b_pending_pass_condition_evaluation",
        "source_state": source_state,
        "public_benchmark_ingestion": public_state,
        "generation_meta": generation_meta,
        "remote_stage_root": str(args.stage_root),
        "generated_contexts": len(all_rows),
        "label_train_contexts": len(label_contexts),
        "calibration_contexts": len(calibration_contexts),
        "development_contexts": len(development_contexts),
        "context_materialization": {
            "label_train": label_materialization,
            "calibration": calibration_materialization,
            "development": development_materialization,
        },
        "inference_batching": {
            "batch_size": max(1, int(args.batch_size)),
            "token_budget": max(0, int(args.inference_token_budget)),
            "progress_interval_sec": float(args.inference_progress_interval_sec),
        },
        "label_train_unique_exact_labeled_contexts": exact_contexts,
        "selected_agent_tiers": selection_meta["selected_agent_tiers"],
        "selected_map_source_types": selection_meta["selected_map_source_types"],
        "label_train_public_fraction": selection_meta["label_train_public_fraction"],
        "calibration_public_fraction": selection_meta["calibration_public_fraction"],
        "development_public_fraction": selection_meta["development_public_fraction"],
        "label_train_official_scenario_fraction": selection_meta["label_train_official_scenario_fraction"],
        "calibration_official_scenario_fraction": selection_meta["calibration_official_scenario_fraction"],
        "development_official_scenario_fraction": selection_meta["development_official_scenario_fraction"],
        "split_diversity": selection_meta.get("split_diversity", {}),
        "official_scenario_rows": official_scenario_rows,
        "official_scenario_proportion": official_scenario_rows / max(1, len(all_rows)),
        "parent_map_split_leakage_count": selection_meta["parent_map_split_leakage_count"],
        "parent_map_split_leakage_examples": selection_meta["parent_map_split_leakage_examples"],
        "memory_smoke": memory_smoke,
        "label_replay": label_replay,
        "prelim_labelv54_summary": prelim_label_summary,
        "boundary_repeat": boundary_replay,
        "boundary_repeat_candidate_rows": len(boundary_rows),
        "boundary_repeat_contexts": len({str(row.get("context_id", "")) for row in boundary_rows}),
        "labelv54_summary": label_summary,
        "critic_calibration": critic,
        "actor_training_rows": actor_rows,
        "actor_training_summary": actor_training_summary,
        "development_replay": development_replay,
        "primary_actor_selection": primary,
        "research_signal": research_signal,
        "total_solver_rows": total_solver_rows,
        "scientific_result_valid_solver_rows": scientific_valid_solver_rows,
        "process_hard_timeout_rows": timeout_rows,
        "process_hard_timeout_rows_excluded_from_scientific_labels": excluded_timeout_rows,
        "unexcluded_process_hard_timeout_rows": unexcluded_timeout_rows,
        "hard_timeout_rate": timeout_rows / max(1, total_solver_rows),
        "unexcluded_hard_timeout_rate": unexcluded_timeout_rows / max(1, total_solver_rows),
        "crash_rows": crash_count,
        "crash_rate": crash_count / max(1, total_solver_rows),
        "disk_growth_bytes": end_size - start_size,
        "disk_growth_per_10000_solver_rows_bytes": (end_size - start_size) / max(1.0, total_solver_rows / 10000.0),
        "gpu_active_hours": gpu_active_hours,
        "forbidden_actions": forbidden_actions,
        "final_blind_panel_constructed_or_accessed": False,
        "elapsed_sec": time.perf_counter() - started,
        **g567.claims(),
    }
    pass_conditions = gate3b_pass_conditions(summary)
    summary["pass_conditions"] = pass_conditions
    summary["gate3b_pipeline_pass"] = all(pass_conditions.values())
    summary["gate3b_research_signal_positive"] = research_signal.get("decision") == "gate3b_research_signal_positive"
    summary["gate3b_ready_for_full_review"] = bool(summary["gate3b_pipeline_pass"] and summary["gate3b_research_signal_positive"])
    if summary["gate3b_ready_for_full_review"]:
        summary["decision"] = "gate3b_ready_for_full_review"
    elif summary["gate3b_pipeline_pass"]:
        summary["decision"] = "gate3b_research_signal_failed"
    else:
        summary["decision"] = "gate3b_pipeline_failed"
    g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
    write_gate3b_report(summary)
    print(json.dumps({"decision": summary["decision"], "total_solver_rows": total_solver_rows, "gpu_active_hours": gpu_active_hours}, sort_keys=True))
    return 0 if summary["decision"] == "gate3b_ready_for_full_review" else 2


if __name__ == "__main__":
    raise SystemExit(main())

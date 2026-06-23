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

    def can_take(row: dict[str, Any]) -> bool:
        uid = row_uid(row)
        if uid in used_uids or uid in selected_uids:
            return False
        owner = hash_owner.get(str(row.get("physical_map_sha256", "")))
        return owner in {None, split}

    def add(row: dict[str, Any]) -> bool:
        if not can_take(row):
            return False
        uid = row_uid(row)
        selected.append(row)
        selected_uids.add(uid)
        hash_owner[str(row.get("physical_map_sha256", ""))] = split
        return True

    public_target = int(math.ceil(count * min_public_fraction))
    official_target = int(math.ceil(count * min_official_fraction))
    synthetic_target = count - public_target

    def selected_source_count(public: bool) -> int:
        return sum(1 for item in selected if row_is_public(item) is public)

    def selected_official_count() -> int:
        return sum(1 for item in selected if row_is_official_scenario(item))

    def selected_parent_hashes() -> set[str]:
        return {str(item.get("physical_map_sha256", "")) for item in selected}

    def selected_families() -> set[str]:
        return {str(item.get("map_family", "")) for item in selected}

    def diversity_order(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        hashes = selected_parent_hashes()
        families = selected_families()
        need_parent = len(hashes) < int(min_parent_maps)
        need_family = len(families) < int(min_map_families)
        def parent_key(row: dict[str, Any]) -> int:
            value = str(row.get("physical_map_sha256", ""))
            if need_parent:
                return 0 if value not in hashes else 1
            return 0 if value in hashes else 1

        def family_key(row: dict[str, Any]) -> int:
            value = str(row.get("map_family", ""))
            if need_family:
                return 0 if value not in families else 1
            return 0 if value in families else 1

        return sorted(
            candidates,
            key=lambda row: (
                parent_key(row),
                family_key(row),
                0 if row_is_public(row) else 1,
                0 if row_is_official_scenario(row) else 1,
                int(g567.number(row.get("agent_count"), 0)),
                str(row.get("map_family", "")),
                str(row.get("physical_map_sha256", "")),
                row_uid(row),
            ),
        )

    def eligible_groups(public: bool | None) -> list[list[dict[str, Any]]]:
        by_hash: dict[str, list[dict[str, Any]]] = {}
        for row in ordered:
            if public is not None and row_is_public(row) is not public:
                continue
            if not can_take(row):
                continue
            by_hash.setdefault(str(row.get("physical_map_sha256", "")), []).append(row)
        return sorted(
            by_hash.values(),
            key=lambda group: (
                -len({int(g567.number(row.get("agent_count"), 0)) for row in group}),
                -len(group),
                str(group[0].get("map_family", "")),
                str(group[0].get("physical_map_sha256", "")),
            ),
        )

    def fill_source(public: bool, target: int) -> None:
        while len(selected) < count and selected_source_count(public) < target:
            added = False
            candidates = [row for row in ordered if row_is_public(row) is public and can_take(row)]
            for row in diversity_order(candidates):
                if add(row):
                    added = True
                    break
            if not added:
                break

    def fill_official(target: int) -> None:
        while len(selected) < count and selected_official_count() < target:
            added = False
            candidates = [row for row in ordered if row_is_public(row) and row_is_official_scenario(row) and can_take(row)]
            for row in diversity_order(candidates):
                if add(row):
                    added = True
                    break
            if not added:
                break

    for tier in required_tiers:
        if len(selected) >= count:
            break
        tier_rows = [row for row in ordered if int(g567.number(row.get("agent_count"), 0)) == tier]
        preferred_public = selected_source_count(True) < public_target
        preferred = [row for row in tier_rows if row_is_public(row) is preferred_public]
        fallback = [row for row in tier_rows if row_is_public(row) is not preferred_public]
        for row in diversity_order(preferred + fallback):
            if add(row):
                break
    fill_official(official_target)
    fill_source(True, public_target)
    fill_source(False, synthetic_target)
    while len(selected) < count:
        added = False
        candidates = [row for row in ordered if can_take(row)]
        for row in diversity_order(candidates):
            if add(row):
                added = True
                break
        if not added:
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
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    filtered = filter_candidate_rows(rows, max_free_cells=max_train_free_cells, max_area=max_train_area)
    hash_owner: dict[str, str] = {}
    used_uids: set[str] = set()
    development_rows = take_split_rows(
        filtered,
        split="DEVELOPMENT",
        count=development_contexts,
        min_public_fraction=development_public_fraction_min,
        min_official_fraction=development_official_scenario_fraction_min,
        min_parent_maps=development_min_parent_maps,
        min_map_families=development_min_map_families,
        required_tiers=REQUIRED_AGENT_TIERS,
        hash_owner=hash_owner,
        used_uids=used_uids,
    )
    calibration_rows = take_split_rows(
        filtered,
        split="CALIBRATION",
        count=calibration_contexts,
        min_public_fraction=calibration_public_fraction_min,
        min_official_fraction=calibration_official_scenario_fraction_min,
        min_parent_maps=calibration_min_parent_maps,
        min_map_families=calibration_min_map_families,
        required_tiers=REQUIRED_AGENT_TIERS,
        hash_owner=hash_owner,
        used_uids=used_uids,
    )
    label_rows = take_split_rows(
        filtered,
        split="LABEL_TRAIN",
        count=label_contexts,
        min_public_fraction=label_public_fraction_min,
        min_official_fraction=label_official_scenario_fraction_min,
        min_parent_maps=label_min_parent_maps,
        min_map_families=label_min_map_families,
        required_tiers=REQUIRED_AGENT_TIERS,
        hash_owner=hash_owner,
        used_uids=used_uids,
    )
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
        replay = g567.copy_for_replay(row, g567.resolve(row["raw_scenario_path"]), replay_dir)
        row["replay_scenario_path"] = g567.rel(replay)
        row["replay_scenario_sha256"] = g567.sha256_file(replay)
        row["blind_locked"] = False
        prepared.append(row)
    return prepared


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
    if cache is not None and cache.exists():
        with cache.open("rb") as handle:
            cached = pickle.load(handle)
        contexts_cached = list(cached.get("contexts", []))
        cached_ids = list(cached.get("row_ids", []))
        if cached_ids == row_ids and len(contexts_cached) == total:
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
        "label_replay_materialized": summary.get("label_replay", {}).get("decision") == "g567_three_tier_replay_materialized",
        "label_replay_planned_executed_exact": bool(summary.get("label_replay", {}).get("planned_executed_exact")),
        "label_replay_expected_baselines_exact": bool(summary.get("label_replay", {}).get("expected_baseline_rows_exact")),
        "development_replay_materialized": summary.get("development_replay", {}).get("decision") == "g567_three_tier_replay_materialized",
        "development_replay_planned_executed_exact": bool(summary.get("development_replay", {}).get("planned_executed_exact")),
        "boundary_repeat_completed_or_none": summary.get("boundary_repeat", {}).get("decision") in {"g567_three_tier_replay_materialized", "gate3b_no_boundary_repeats_required"},
        "zero_process_hard_timeouts": int(g567.number(summary.get("process_hard_timeout_rows"), 999)) == 0,
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
        f"- hard-timeout rate: `{summary.get('hard_timeout_rate')}`\n"
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
    if not str(device).startswith("cuda"):
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
        else:
            audit_rows, manifest_rows, generation_meta = g567.make_generated_contexts(int(args.context_pool), int(args.seed), g567.resolve(g567.TMP_ROOT))
            generation_meta["resumed_candidate_pool"] = False
            generation_meta["candidate_pool_path"] = g567.rel(candidate_pool_path)
            generation_meta["candidate_audit_path"] = g567.rel(candidate_audit_path)
            g567.write_rows(candidate_pool_path, manifest_rows)
            g567.write_rows(candidate_audit_path, audit_rows)
        g567.update_remote_map_registries(g567.resolve(g567.TMP_ROOT) / "maps")
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
        )
        label_rows = prepare_rows(label_rows_raw, split="LABEL_TRAIN", prefix="g567_gate3b_label_train")
        calibration_rows = prepare_rows(calibration_rows_raw, split="CALIBRATION", prefix="g567_gate3b_calibration")
        development_rows = prepare_rows(development_rows_raw, split="DEVELOPMENT", prefix="g567_gate3b_development")
        all_rows = label_rows + calibration_rows + development_rows
        g567.write_rows(g567.VALID_CONTEXT_MANIFEST, all_rows)
        g567.write_rows(g567.SCENARIO_VALIDITY, audit_rows)
        g567.write_rows(context_manifest_path, all_rows)
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
    if label_replay.get("decision") != "g567_three_tier_replay_materialized":
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
        if boundary_replay.get("decision") != "g567_three_tier_replay_materialized":
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
            "process_hard_timeout_rows": 0,
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
        "process_hard_timeout_rows": timeout_rows,
        "hard_timeout_rate": timeout_rows / max(1, total_solver_rows),
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

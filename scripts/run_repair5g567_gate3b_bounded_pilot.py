from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import time
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import run_repair5g567_strict_pipeline as g567  # noqa: E402


PHASE = "gate3b_bounded_pilot"
LABEL_PHASE = "gate3b_label_train"
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


def take_split_rows(
    rows: list[dict[str, Any]],
    *,
    split: str,
    count: int,
    min_public_fraction: float,
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
    synthetic_target = count - public_target

    def selected_source_count(public: bool) -> int:
        return sum(1 for item in selected if row_is_public(item) is public)

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
            groups = eligible_groups(public)
            if not groups:
                break
            for row in groups[0]:
                if len(selected) >= count or selected_source_count(public) >= target:
                    break
                add(row)

    for tier in required_tiers:
        if len(selected) >= count:
            break
        tier_rows = [row for row in ordered if int(g567.number(row.get("agent_count"), 0)) == tier]
        preferred_public = selected_source_count(True) < public_target
        preferred = [row for row in tier_rows if row_is_public(row) is preferred_public]
        fallback = [row for row in tier_rows if row_is_public(row) is not preferred_public]
        for row in preferred + fallback:
            if add(row):
                break
    fill_source(True, public_target)
    fill_source(False, synthetic_target)
    while len(selected) < count:
        groups = eligible_groups(None)
        if not groups:
            break
        added = False
        for row in groups[0]:
            if len(selected) >= count:
                break
            added = add(row) or added
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
    used_uids.update(selected_uids)
    return selected


def select_gate3b_rows(
    rows: list[dict[str, Any]],
    *,
    label_contexts: int,
    development_contexts: int,
    label_public_fraction_min: float,
    development_public_fraction_min: float,
    max_train_free_cells: int,
    max_train_area: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    filtered = filter_candidate_rows(rows, max_free_cells=max_train_free_cells, max_area=max_train_area)
    hash_owner: dict[str, str] = {}
    used_uids: set[str] = set()
    development_rows = take_split_rows(
        filtered,
        split="DEVELOPMENT",
        count=development_contexts,
        min_public_fraction=development_public_fraction_min,
        required_tiers=REQUIRED_AGENT_TIERS,
        hash_owner=hash_owner,
        used_uids=used_uids,
    )
    label_rows = take_split_rows(
        filtered,
        split="LABEL_TRAIN",
        count=label_contexts,
        min_public_fraction=label_public_fraction_min,
        required_tiers=REQUIRED_AGENT_TIERS,
        hash_owner=hash_owner,
        used_uids=used_uids,
    )
    split_by_hash: dict[str, set[str]] = {}
    for split, split_rows in [("LABEL_TRAIN", label_rows), ("DEVELOPMENT", development_rows)]:
        for row in split_rows:
            split_by_hash.setdefault(str(row.get("physical_map_sha256", "")), set()).add(split)
    leakage = {key: sorted(value) for key, value in split_by_hash.items() if len(value) > 1}
    meta = {
        "candidate_pool_rows": len(rows),
        "filtered_candidate_rows": len(filtered),
        "label_train_public_fraction": public_fraction(label_rows),
        "development_public_fraction": public_fraction(development_rows),
        "parent_map_split_leakage_count": len(leakage),
        "parent_map_split_leakage_examples": dict(list(leakage.items())[:5]),
        "selected_agent_tiers": sorted({int(g567.number(row.get("agent_count"), 0)) for row in label_rows + development_rows}),
        "selected_map_source_types": dict(Counter(str(row.get("map_source_type", "")) for row in label_rows + development_rows)),
        "max_train_free_cells": max_train_free_cells,
        "max_train_area": max_train_area,
    }
    return label_rows, development_rows, meta


def scenario_source_type(row: dict[str, Any]) -> str:
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
) -> tuple[list[g567.G567Context], dict[str, Any]]:
    total = len(rows)
    started = time.perf_counter()
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
    }
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
        "development_contexts_500_to_1000": 500 <= int(g567.number(summary.get("development_contexts"), 0)) <= 1000,
        "solver_rows_50000_to_100000": 50000 <= int(g567.number(summary.get("total_solver_rows"), 0)) <= 100000,
        "all_agent_tiers_through_3000_present": set(REQUIRED_AGENT_TIERS).issubset(set(summary.get("selected_agent_tiers", []))),
        "label_public_fraction_min_met": float(g567.number(summary.get("label_train_public_fraction"), 0.0)) >= 0.50,
        "development_public_fraction_min_met": float(g567.number(summary.get("development_public_fraction"), 0.0)) >= 0.70,
        "public_and_synthetic_mixture_present": {"canonical_public_benchmark_map", "synthetic_stress_map"}.issubset(set(summary.get("selected_map_source_types", {}).keys())),
        "parent_map_split_leakage_zero": int(g567.number(summary.get("parent_map_split_leakage_count"), 999)) == 0,
        "traffic_prior_bfs_materialization": bool(materialization_versions) and all(versions == {"traffic_prior_v1_bfs"} for versions in materialization_versions),
        "label_replay_materialized": summary.get("label_replay", {}).get("decision") == "g567_three_tier_replay_materialized",
        "development_replay_materialized": summary.get("development_replay", {}).get("decision") == "g567_three_tier_replay_materialized",
        "zero_process_hard_timeouts": int(g567.number(summary.get("process_hard_timeout_rows"), 999)) == 0,
        "critic_calibration_reported": bool(summary.get("critic_calibration", {}).get("binary_calibration_by_target")),
        "actor_cuda_bf16_training": bool(summary.get("actor_training_row", {}).get("cuda_bf16_training")),
        "actor_gpu_active_hours_2_to_4": 2.0 <= float(g567.number(summary.get("actor_training_row", {}).get("gpu_active_hours"), 0.0)) <= 4.4,
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
        f"- development contexts: `{summary.get('development_contexts')}`\n"
        f"- total solver rows: `{summary.get('total_solver_rows')}`\n"
        f"- hard-timeout rate: `{summary.get('hard_timeout_rate')}`\n"
        f"- crash rate: `{summary.get('crash_rate')}`\n"
        f"- label public fraction: `{summary.get('label_train_public_fraction')}`\n"
        f"- development public fraction: `{summary.get('development_public_fraction')}`\n"
        f"- official scenario proportion: `{summary.get('official_scenario_proportion')}`\n"
        f"- Label-v5.4 safe/positive/harmful: `{summary.get('labelv54_summary', {}).get('safe_candidates')}` / `{summary.get('labelv54_summary', {}).get('positive_candidates')}` / `{summary.get('labelv54_summary', {}).get('harmful_candidates')}`\n"
        f"- critic decision: `{summary.get('critic_calibration', {}).get('decision')}`\n"
        f"- actor GPU-active hours: `{summary.get('actor_training_row', {}).get('gpu_active_hours')}`\n"
        f"- primary actor decision: `{summary.get('primary_actor_selection', {}).get('decision')}`\n"
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
    parser.add_argument("--development-contexts", type=int, default=500)
    parser.add_argument("--label-replay-solver-rows", type=int, default=60000)
    parser.add_argument("--label-public-fraction-min", type=float, default=0.50)
    parser.add_argument("--development-public-fraction-min", type=float, default=0.70)
    parser.add_argument("--max-train-free-cells", type=int, default=24000)
    parser.add_argument("--max-train-area", type=int, default=32000)
    parser.add_argument("--seed", type=int, default=4567)
    parser.add_argument("--seed-checkpoint-glob", nargs="*", default=["outputs/external/phase5p5_repair5g567_evidence_ea2cb71b/stage2a/models/gcst/*.pt"])
    parser.add_argument("--actor-seed", type=int, default=567)
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
    if not (500 <= int(args.development_contexts) <= 1000):
        raise RuntimeError("Gate-3B requires 500-1000 development contexts")
    if not (50000 <= int(args.label_replay_solver_rows) <= 100000):
        raise RuntimeError("Gate-3B label replay solver rows must stay in 50000-100000")

    start_size = directory_size_bytes(g567.resolve(args.stage_root))
    audit_rows, manifest_rows, generation_meta = g567.make_generated_contexts(int(args.context_pool), int(args.seed), g567.resolve(g567.TMP_ROOT))
    g567.update_remote_map_registries(g567.resolve(g567.TMP_ROOT) / "maps")
    label_rows_raw, development_rows_raw, selection_meta = select_gate3b_rows(
        manifest_rows,
        label_contexts=int(args.label_train_contexts),
        development_contexts=int(args.development_contexts),
        label_public_fraction_min=float(args.label_public_fraction_min),
        development_public_fraction_min=float(args.development_public_fraction_min),
        max_train_free_cells=int(args.max_train_free_cells),
        max_train_area=int(args.max_train_area),
    )
    label_rows = prepare_rows(label_rows_raw, split="LABEL_TRAIN", prefix="g567_gate3b_label_train")
    development_rows = prepare_rows(development_rows_raw, split="DEVELOPMENT", prefix="g567_gate3b_development")
    all_rows = label_rows + development_rows
    g567.write_rows(g567.VALID_CONTEXT_MANIFEST, all_rows)
    g567.write_rows(g567.SCENARIO_VALIDITY, audit_rows)
    g567.write_rows(g567.TABLES / CONTEXT_MANIFEST_NAME, all_rows)
    label_contexts, label_materialization = materialize_contexts(
        label_rows,
        phase="label_train",
        workers=int(args.materialize_workers),
        progress_interval_sec=float(args.materialize_progress_interval_sec),
    )
    development_contexts, development_materialization = materialize_contexts(
        development_rows,
        phase="development",
        workers=int(args.materialize_workers),
        progress_interval_sec=float(args.materialize_progress_interval_sec),
    )
    memory_smoke = g567.write_3000_agent_memory_smoke(device, int(args.actor_hidden_dim))
    g567.write_baseline_registry()
    seed_ckpts = g567.checkpoint_paths(args.seed_checkpoint_glob)
    if not seed_ckpts:
        raise RuntimeError(f"Gate-3B missing seed actor checkpoint: {args.seed_checkpoint_glob}")
    seed_raw = g567.infer_checkpoint_thetas(
        label_contexts,
        seed_ckpts[:1],
        device=device,
        batch_size=max(1, int(args.batch_size)),
        phase=SEED_PHASE,
        token_budget=max(0, int(args.inference_token_budget)),
        progress_interval_sec=float(args.inference_progress_interval_sec),
    )
    label_baseline_rows = len(label_contexts) * 3
    response_target_rows = max(len(label_contexts), int(args.label_replay_solver_rows) - label_baseline_rows)
    response_rows = g567.generate_response_thetas(label_contexts, seed_raw, phase=LABEL_PHASE, target_rows=response_target_rows)
    label_replay = g567.run_replay_phase(
        LABEL_PHASE,
        label_contexts,
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
    label_summary = g567.create_labelv54_from_pairs([g567.plan_paths(LABEL_PHASE)["pairs"]], float(args.margin))
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
    critic = g567.train_distributional_outcome_ensemble(label_contexts, seeds=[int(args.actor_seed), int(args.actor_seed) + 1, int(args.actor_seed) + 2], plan_only=False)
    examples = g567.actor_examples_from_labelv54(label_contexts)
    if not examples:
        raise RuntimeError("Gate-3B produced no Label-v5.4 actor training examples")
    training_dataset_sha = dataset_sha256(label_contexts, g567.LABELV54_CANDIDATES)
    actor_row, grad_row = g567.train_one_g567_actor(
        "A5",
        int(args.actor_seed),
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
        training_context_uids=[ctx.evaluation_uid for ctx in label_contexts],
        training_dataset_sha256=training_dataset_sha,
        source_commit=source_state.get("head", ""),
        min_gpu_active_hours=float(args.min_gpu_active_hours),
        max_gpu_active_hours=float(args.max_gpu_active_hours),
    )
    g567.write_rows(g567.ACTOR_TRAINING_MATRIX, [actor_row])
    g567.write_rows(g567.ACTOR_GRADIENT_AUDIT, [grad_row])
    actor_training_summary = {
        "schema_version": f"{g567.ROUND}_{PHASE}_actor_training_summary_v1",
        "decision": "gate3b_a5_actor_training_completed",
        "selected_development_checkpoint_paths": [actor_row.get("model_path", "")],
        "rows": [actor_row],
        "gradient_rows": [grad_row],
        "cuda_bf16_training": bool(actor_row.get("cuda_bf16_training")),
        "token_budget_batching": bool(actor_row.get("token_budget_batching")),
        "gpu_active_hours": actor_row.get("gpu_active_hours"),
        **g567.claims(),
    }
    g567.write_json(g567.ACTOR_TRAINING_SUMMARY, actor_training_summary)
    actor_ckpt = g567.resolve(actor_row["model_path"])
    dev_raw = g567.infer_checkpoint_thetas(
        development_contexts,
        [actor_ckpt],
        device=device,
        batch_size=max(1, int(args.batch_size)),
        phase=DEV_PHASE,
        token_budget=max(0, int(args.inference_token_budget)),
        progress_interval_sec=float(args.inference_progress_interval_sec),
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
    label_result_rows = replay_result_rows(LABEL_PHASE)
    dev_result_rows = replay_result_rows(DEV_PHASE)
    total_solver_rows = int(g567.number(label_replay.get("executed_rows"), 0)) + int(g567.number(development_replay.get("executed_rows"), 0))
    timeout_rows = int(g567.number(label_replay.get("process_hard_timeout_rows"), 0)) + int(g567.number(development_replay.get("process_hard_timeout_rows"), 0))
    crash_count = crash_rows(label_result_rows) + crash_rows(dev_result_rows)
    official_scenario_rows = sum(1 for row in all_rows if str(row.get("scenario_source_type", "")).startswith("official_"))
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
        "generated_contexts": len(manifest_rows),
        "label_train_contexts": len(label_contexts),
        "development_contexts": len(development_contexts),
        "context_materialization": {
            "label_train": label_materialization,
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
        "development_public_fraction": selection_meta["development_public_fraction"],
        "official_scenario_rows": official_scenario_rows,
        "official_scenario_proportion": official_scenario_rows / max(1, len(all_rows)),
        "parent_map_split_leakage_count": selection_meta["parent_map_split_leakage_count"],
        "parent_map_split_leakage_examples": selection_meta["parent_map_split_leakage_examples"],
        "memory_smoke": memory_smoke,
        "label_replay": label_replay,
        "labelv54_summary": label_summary,
        "critic_calibration": critic,
        "actor_training_row": actor_row,
        "actor_training_summary": actor_training_summary,
        "development_replay": development_replay,
        "primary_actor_selection": primary,
        "total_solver_rows": total_solver_rows,
        "process_hard_timeout_rows": timeout_rows,
        "hard_timeout_rate": timeout_rows / max(1, total_solver_rows),
        "crash_rows": crash_count,
        "crash_rate": crash_count / max(1, total_solver_rows),
        "disk_growth_bytes": end_size - start_size,
        "disk_growth_per_10000_solver_rows_bytes": (end_size - start_size) / max(1.0, total_solver_rows / 10000.0),
        "gpu_active_hours": actor_row.get("gpu_active_hours"),
        "forbidden_actions": forbidden_actions,
        "final_blind_panel_constructed_or_accessed": False,
        "elapsed_sec": time.perf_counter() - started,
        **g567.claims(),
    }
    pass_conditions = gate3b_pass_conditions(summary)
    summary["pass_conditions"] = pass_conditions
    summary["decision"] = "gate3b_bounded_pilot_pass" if all(pass_conditions.values()) else "gate3b_bounded_pilot_failed"
    g567.write_json(g567.REPORTS / SUMMARY_NAME, summary)
    write_gate3b_report(summary)
    print(json.dumps({"decision": summary["decision"], "total_solver_rows": total_solver_rows, "gpu_active_hours": actor_row.get("gpu_active_hours")}, sort_keys=True))
    return 0 if summary["decision"] == "gate3b_bounded_pilot_pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())

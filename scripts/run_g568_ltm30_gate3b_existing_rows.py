"""G5.68 LTM-paper-style 30s replay on existing Gate-3B rows.

This runner is diagnostic-only. It selects existing non-training Gate-3B
contexts that resemble the LTM paper's one-shot map set, then replays exactly
three methods with a 30s internal solver budget:

* paper-style additive/LTM
* historical static-flow shield
* the Gate-3B primary A5 actor checkpoint

It does not train, fine-tune, generate scenarios, launch full, touch blind
artifacts, or modify solver semantics.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import re
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import run_repair5g567_strict_pipeline as g567  # noqa: E402


DEFAULT_SOURCE_STAGE_ROOT = Path("/root/shared-nvme/g567_gate3b_bounded_2d334c79_tmux_r13_pool20000")
DEFAULT_OUTPUT_ROOT = Path("/root/shared-nvme/g568_ltm30_existingrow")
DEFAULT_PHASE = "g568_ltm30_existingrow"
DEFAULT_TARGET_CONTEXTS = 1000
DEFAULT_MAX_WORKERS = 4
DEFAULT_STOP_LAUNCH_AFTER_SEC = 7.5 * 3600.0
DEFAULT_MAX_WALL_SEC = 8.0 * 3600.0
DEFAULT_CHUNK_ROWS = 48
SELECTION_SEED = 56830
INTERNAL_BUDGET_SEC = 30.0
PROCESS_HARD_TIMEOUT_SEC = 60.0

LTM_TARGET_MAPS = [
    "empty-32-32",
    "empty-48-48",
    "random-32-32-20",
    "maze-32-32-4",
    "random-64-64-20",
    "room-64-64-8",
    "warehouse-10-20-10-2-1",
    "warehouse-10-20-10-2-2",
]

DESIRED_AGENT_TIERS = [16, 64, 256, 1000, 2000]
EVAL_SPLIT_RANK = {
    "DEVELOPMENT": 0,
    "VALIDATION": 0,
    "VALID": 0,
    "HELDOUT": 0,
    "CALIBRATION": 1,
}

METHOD_LTM = "ltm_30s"
METHOD_STATIC = "static_flow_30s"
METHOD_ACTOR = "gate3b_actor_30s"
METHODS = [METHOD_LTM, METHOD_STATIC, METHOD_ACTOR]


def output_dirs(output_root: Path) -> dict[str, Path]:
    root = output_root / "outputs"
    return {
        "root": root,
        "tables": root / "tables",
        "reports": root / "reports",
        "logs": root / "logs",
        "tmp": root / "tmp",
    }


def paths(output_root: Path) -> dict[str, Path]:
    dirs = output_dirs(output_root)
    tables = dirs["tables"]
    reports = dirs["reports"]
    logs = dirs["logs"]
    return {
        **dirs,
        "inventory": tables / "g568_ltm30_existingrow_inventory_by_map_tier.csv",
        "selected_contexts": tables / "g568_ltm30_existingrow_selected_contexts.csv",
        "selection_report": reports / "g568_ltm30_existingrow_selection_report.md",
        "plan": tables / "g568_ltm30_existingrow_plan.csv",
        "registry": tables / "g568_ltm30_existingrow_registry.csv",
        "results_raw": tables / "g568_ltm30_existingrow_results.raw.csv",
        "results": tables / "g568_ltm30_existingrow_results.csv",
        "pairs": tables / "g568_ltm30_existingrow_pairs.csv",
        "by_map": tables / "g568_ltm30_existingrow_by_map.csv",
        "by_map_family": tables / "g568_ltm30_existingrow_by_map_family.csv",
        "by_agent_tier": tables / "g568_ltm30_existingrow_by_agent_tier.csv",
        "by_split": tables / "g568_ltm30_existingrow_by_split.csv",
        "by_public_official": tables / "g568_ltm30_existingrow_by_public_official.csv",
        "summary_md": reports / "g568_ltm30_existingrow_summary.md",
        "summary_json": reports / "g568_ltm30_existingrow_summary.json",
        "partial_stop": reports / "g568_ltm30_existingrow_partial_stop.md",
        "repro": reports / "g568_ltm30_existingrow_repro.md",
        "status": reports / "g568_ltm30_existingrow_status.json",
        "scenario_metadata": reports / "g568_ltm30_existingrow_replay_scenario_generation.json",
        "theta_rows": tables / "g568_ltm30_existingrow_primary_actor_thetas.csv",
        "method_alias_audit": reports / "g568_ltm30_existingrow_method_alias_audit.json",
        "log_dir": logs / "g568_ltm30_existingrow",
        "scenario_dir": dirs["tmp"] / "g568_ltm30_existingrow_replay_scenarios",
    }


def configure_g567(source_stage_root: Path, output_root: Path) -> None:
    out = output_dirs(output_root)
    for directory in out.values():
        directory.mkdir(parents=True, exist_ok=True)
    p = paths(output_root)
    source_stage_root = source_stage_root.resolve()
    g567.OUTPUT_ROOT = out["root"]
    g567.ARTIFACT_ROOT = out["root"] / "artifacts"
    g567.TABLES = out["tables"]
    g567.REPORTS = out["reports"]
    g567.LOGS = out["logs"]
    g567.MODEL_DIR = out["root"] / "models" / "gcst"
    g567.TMP_ROOT = source_stage_root / "scenario_bank"
    g567.REPLAY_SCENARIO_DIR = p["scenario_dir"]
    g567.DEFAULT_SOURCE_SCENARIO_DIR = str(source_stage_root / "replay_scenarios")
    g567.VALID_CONTEXT_MANIFEST = (
        source_stage_root
        / "tables"
        / "phase5p5_repair5g567_gate3b_bounded_pilot_valid_context_manifest.csv"
    )
    g567.BASELINE_REGISTRY = p["registry"]
    g567.BASELINE_REGISTRY_SUMMARY = out["reports"] / "g568_ltm30_existingrow_baseline_registry_summary.json"
    g567.SOLVER_BUDGET_AUDIT = out["tables"] / "g568_ltm30_existingrow_solver_budget_audit.csv"
    g567.SOLVER_BUDGET_AUDIT_SUMMARY = out["reports"] / "g568_ltm30_existingrow_solver_budget_audit_summary.json"
    for directory in [g567.ARTIFACT_ROOT, g567.MODEL_DIR, p["log_dir"], p["scenario_dir"]]:
        directory.mkdir(parents=True, exist_ok=True)


def write_status(path: Path, **payload: Any) -> None:
    payload = {
        "schema_version": "g568_ltm30_existingrow_status_v1",
        "updated_unix": time.time(),
        **payload,
    }
    g567.write_json(path, payload)


def normalize_map_name(value: str) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def target_family(target: str) -> str:
    return target.split("-", 1)[0].replace("_", "-")


def finite_float(value: Any, default: float = math.nan) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def boolish(value: Any) -> bool:
    return g567.boolish(value)


def stable_sort_key(*parts: Any, seed: int = SELECTION_SEED) -> str:
    return hashlib.sha256(("|".join(map(str, (seed, *parts)))).encode("utf-8")).hexdigest()


def split_rank(row: dict[str, Any]) -> int:
    return EVAL_SPLIT_RANK.get(str(row.get("split", "")).upper(), 99)


def is_allowed_eval_row(row: dict[str, Any], allow_calibration: bool) -> bool:
    split = str(row.get("split", "")).upper()
    if split in {"DEVELOPMENT", "VALIDATION", "VALID", "HELDOUT"}:
        return True
    return allow_calibration and split == "CALIBRATION"


def candidate_rows_from_manifest(manifest_rows: list[dict[str, Any]], allow_calibration: bool) -> list[dict[str, Any]]:
    out = []
    for row in manifest_rows:
        if not is_allowed_eval_row(row, allow_calibration=allow_calibration):
            continue
        agents = int_value(row.get("agent_count", row.get("agents")))
        if agents <= 0 or agents > 2000:
            continue
        out.append(row)
    return out


def bind_target_maps(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_map = Counter(str(row.get("map", "")) for row in rows if str(row.get("map", "")).strip())
    by_norm: dict[str, Counter[str]] = defaultdict(Counter)
    family_maps: dict[str, Counter[str]] = defaultdict(Counter)
    map_family_lookup: dict[str, str] = {}
    for map_name, count in by_map.items():
        by_norm[normalize_map_name(map_name)][map_name] += count
    for row in rows:
        map_name = str(row.get("map", ""))
        fam = str(row.get("map_family", "")) or target_family(map_name)
        if map_name:
            family_maps[fam][map_name] += 1
            map_family_lookup[map_name] = fam

    bindings: dict[str, dict[str, Any]] = {}
    used_maps: set[str] = set()
    for target in LTM_TARGET_MAPS:
        match_type = "missing"
        selected = ""
        if target in by_map:
            selected = target
            match_type = "exact"
        else:
            norm = normalize_map_name(target)
            normalized = by_norm.get(norm, Counter())
            if normalized:
                selected = normalized.most_common(1)[0][0]
                match_type = "normalized"
        if selected:
            used_maps.add(selected)
        bindings[target] = {
            "ltm_target_map": target,
            "selected_map": selected,
            "match_type": match_type,
            "fallback": False,
            "source_family": map_family_lookup.get(selected, target_family(target).replace("-", "_")),
            "selected_map_rows": int(by_map.get(selected, 0)) if selected else 0,
        }

    for target, binding in bindings.items():
        if binding["selected_map"]:
            continue
        family = target_family(target).replace("-", "_")
        candidates = family_maps.get(family, Counter())
        if not candidates and family == "warehouse":
            candidates = family_maps.get("warehouse", Counter())
        scored = []
        for map_name, count in candidates.items():
            score = 0.0
            score += 2.0 if map_name not in used_maps else 0.0
            score += count / 10000.0
            score += difflib_ratio(normalize_map_name(target), normalize_map_name(map_name))
            scored.append((score, count, map_name))
        if scored:
            scored.sort(reverse=True)
            selected = scored[0][2]
            used_maps.add(selected)
            binding.update(
                {
                    "selected_map": selected,
                    "match_type": "fallback_same_family",
                    "fallback": True,
                    "source_family": map_family_lookup.get(selected, family),
                    "selected_map_rows": int(by_map.get(selected, 0)),
                }
            )
    return bindings


def difflib_ratio(a: str, b: str) -> float:
    # Small local helper to avoid importing difflib on every target map in older Python runtimes.
    import difflib

    return float(difflib.SequenceMatcher(None, a, b).ratio())


def choose_tiers(available_tiers: list[int], max_tiers: int) -> list[int]:
    tiers = sorted({tier for tier in available_tiers if 0 < tier <= 2000})
    chosen: list[int] = []
    for desired in DESIRED_AGENT_TIERS:
        remaining = [tier for tier in tiers if tier not in chosen]
        if not remaining:
            break
        best = min(
            remaining,
            key=lambda tier: (
                abs(math.log(max(tier, 1) / desired, 2)),
                abs(tier - desired),
                tier,
            ),
        )
        chosen.append(best)
        if len(chosen) >= max_tiers:
            break
    return sorted(chosen)


def build_inventory_and_selection(
    manifest_rows: list[dict[str, Any]],
    *,
    target_contexts: int,
    max_tiers_per_map: int,
    max_contexts_per_map_tier: int,
    allow_calibration: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    candidate_rows = candidate_rows_from_manifest(manifest_rows, allow_calibration=allow_calibration)
    bindings = bind_target_maps(candidate_rows)

    rows_by_map_tier: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in candidate_rows:
        map_name = str(row.get("map", ""))
        agents = int_value(row.get("agent_count", row.get("agents")))
        rows_by_map_tier[(map_name, agents)].append(row)

    inventory: list[dict[str, Any]] = []
    for target in LTM_TARGET_MAPS:
        binding = bindings[target]
        selected_map = str(binding.get("selected_map", ""))
        available = sorted({agents for (map_name, agents) in rows_by_map_tier if map_name == selected_map})
        selected_tiers = choose_tiers(available, max_tiers_per_map)
        for tier in available or [""]:
            tier_rows = rows_by_map_tier.get((selected_map, tier), []) if selected_map else []
            split_counts = Counter(str(row.get("split", "")) for row in tier_rows)
            inventory.append(
                {
                    "ltm_target_map": target,
                    "selected_map": selected_map,
                    "match_type": binding.get("match_type", "missing"),
                    "fallback": bool(binding.get("fallback")),
                    "map_family": binding.get("source_family", ""),
                    "agent_tier": tier,
                    "available_contexts": len(tier_rows),
                    "development_contexts": split_counts.get("DEVELOPMENT", 0),
                    "calibration_contexts": split_counts.get("CALIBRATION", 0),
                    "selected_for_primary_subset": tier in selected_tiers if selected_map else False,
                    "agent_count_primary_ltm_style": int_value(tier) <= 2000 if str(tier).strip() else False,
                }
            )

    selected: list[dict[str, Any]] = []
    selected_uids: set[str] = set()
    for target in LTM_TARGET_MAPS:
        binding = bindings[target]
        selected_map = str(binding.get("selected_map", ""))
        if not selected_map:
            continue
        available = sorted({agents for (map_name, agents) in rows_by_map_tier if map_name == selected_map})
        for tier in choose_tiers(available, max_tiers_per_map):
            tier_rows = list(rows_by_map_tier.get((selected_map, tier), []))
            tier_rows.sort(
                key=lambda row: (
                    split_rank(row),
                    stable_sort_key(
                        target,
                        selected_map,
                        tier,
                        row.get("g567_evaluation_uid", ""),
                        row.get("g567_dataset_row_id", ""),
                    ),
                )
            )
            taken = 0
            for row in tier_rows:
                uid = str(row.get("g567_evaluation_uid", "")) or str(row.get("g567_dataset_row_id", ""))
                if uid in selected_uids:
                    continue
                out = dict(row)
                out.update(
                    {
                        "ltm_target_map": target,
                        "ltm_target_match_type": binding.get("match_type", "missing"),
                        "ltm_target_selected_map": selected_map,
                        "ltm_target_fallback": bool(binding.get("fallback")),
                        "selection_seed": SELECTION_SEED,
                        "selection_policy": "target_map_then_nearest_5_agent_tiers_up_to_25_contexts_development_then_calibration",
                    }
                )
                selected.append(out)
                selected_uids.add(uid)
                taken += 1
                if taken >= max_contexts_per_map_tier or len(selected) >= target_contexts:
                    break
            if len(selected) >= target_contexts:
                break
        if len(selected) >= target_contexts:
            break

    meta = {
        "schema_version": "g568_ltm30_existingrow_selection_v1",
        "target_contexts": target_contexts,
        "selected_contexts": len(selected),
        "allow_calibration": allow_calibration,
        "selected_split_counts": dict(Counter(str(row.get("split", "")) for row in selected)),
        "selected_map_counts": dict(Counter(str(row.get("map", "")) for row in selected)),
        "selected_agent_counts": {},
        "map_bindings": list(bindings.values()),
        "expected_max_solver_rows": len(selected) * len(METHODS),
    }
    meta["selected_agent_counts"] = dict(
        sorted(Counter(int_value(row.get("agent_count", row.get("agents"))) for row in selected).items())
    )
    return inventory, selected, list(bindings.values()), meta


def write_selection_report(path: Path, bindings: list[dict[str, Any]], inventory: list[dict[str, Any]], selected: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    inv_by_target = defaultdict(list)
    for row in inventory:
        inv_by_target[row["ltm_target_map"]].append(row)
    lines = [
        "# G5.68 LTM30 Existing-Row Selection",
        "",
        "Diagnostic subset built only from existing Gate-3B non-training rows. No solver replay has happened yet at this stage.",
        "",
        f"- deterministic sampling seed: `{SELECTION_SEED}`",
        f"- selected contexts: `{len(selected)}`",
        f"- expected maximum solver rows: `{len(selected) * len(METHODS)}`",
        f"- selected split counts: `{meta.get('selected_split_counts')}`",
        "",
        "## Map Binding",
        "",
        "| LTM target | selected existing map | match type | fallback | available rows |",
        "|---|---|---|---:|---:|",
    ]
    for binding in bindings:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(binding.get("ltm_target_map", "")),
                    str(binding.get("selected_map", "")) or "MISSING",
                    str(binding.get("match_type", "")),
                    str(binding.get("fallback", "")),
                    str(binding.get("selected_map_rows", "")),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Selected Contexts By Map And Tier", "", "| target | map | tier | selected | available | dev | calibration |", "|---|---|---:|---:|---:|---:|---:|"])
    selected_counts = Counter(
        (
            str(row.get("ltm_target_map", "")),
            str(row.get("map", "")),
            int_value(row.get("agent_count", row.get("agents"))),
        )
        for row in selected
    )
    for row in inventory:
        key = (str(row.get("ltm_target_map", "")), str(row.get("selected_map", "")), int_value(row.get("agent_tier")))
        if not row.get("selected_for_primary_subset"):
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("ltm_target_map", "")),
                    str(row.get("selected_map", "")),
                    str(row.get("agent_tier", "")),
                    str(selected_counts.get(key, 0)),
                    str(row.get("available_contexts", 0)),
                    str(row.get("development_contexts", 0)),
                    str(row.get("calibration_contexts", 0)),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- `LABEL_TRAIN` rows are excluded from primary evaluation.",
            "- `CALIBRATION` rows are used only when DEVELOPMENT/VALIDATION rows alone are insufficient for the target subset size.",
            "- 3000-agent rows are excluded because this is the LTM-paper-style up-to-2000-agent subset.",
            "- Missing LTM target maps are not generated; same-family fallback maps are explicitly marked.",
            "",
        ]
    )
    g567.write_text(path, "\n".join(lines))


def discover_primary_actor(source_stage_root: Path) -> tuple[Path, dict[str, Any]]:
    final_summary = source_stage_root / "reports/phase5p5_repair5g567_gate3b_bounded_pilot_summary.json"
    training_summary = source_stage_root / "reports/phase5p5_repair5g567_gate3b_bounded_pilot_actor_training_summary.json"
    payload: dict[str, Any] = {
        "final_summary_path": str(final_summary),
        "training_summary_path": str(training_summary),
    }
    if final_summary.exists():
        data = json.loads(final_summary.read_text(encoding="utf-8"))
        primary = data.get("primary_actor_selection") or {}
        path = primary.get("primary_model_path")
        if path:
            actor_path = Path(path)
            payload["primary_actor_selection"] = primary
            payload["primary_actor_source"] = "gate3b_final_summary_primary_actor_selection"
            return actor_path, payload
    data = json.loads(training_summary.read_text(encoding="utf-8"))
    paths = data.get("selected_development_checkpoint_paths") or []
    if not paths:
        rows = data.get("rows") or []
        paths = [row.get("model_path") for row in rows if row.get("model_path")]
    if not paths:
        raise RuntimeError(f"no Gate-3B actor checkpoint discovered from {training_summary}")
    payload["primary_actor_source"] = "actor_training_summary_first_selected_path_fallback"
    payload["actor_training_summary"] = {k: data.get(k) for k in ["decision", "selected_development_checkpoint_paths", "gpu_active_hours", "actor_seed_count"]}
    return Path(paths[0]), payload


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def materialize_selected_contexts(selected_rows: list[dict[str, Any]]) -> tuple[list[g567.G567Context], list[dict[str, Any]]]:
    g567.update_remote_map_registries(g567.resolve(g567.TMP_ROOT) / "maps")
    contexts: list[g567.G567Context] = []
    failures: list[dict[str, Any]] = []
    for row in selected_rows:
        try:
            ctx = g567.context_from_manifest_row(row)
            if ctx is None:
                raise RuntimeError("context_from_manifest_row_returned_none")
            feature_row = dict(ctx.feature_row)
            feature_row.update(
                {
                    "base_time_limit_sec": INTERNAL_BUDGET_SEC,
                    "budget_ms": int(INTERNAL_BUDGET_SEC * 1000),
                    "nominal_budget_ms": int(INTERNAL_BUDGET_SEC * 1000),
                    "g568_ltm30_existingrow": True,
                    "ltm_target_map": row.get("ltm_target_map", ""),
                    "ltm_target_match_type": row.get("ltm_target_match_type", ""),
                }
            )
            ctx = replace(
                ctx,
                budget_ms=int(INTERNAL_BUDGET_SEC * 1000),
                base_time_limit_sec=INTERNAL_BUDGET_SEC,
                feature_row=feature_row,
                budget_role="g568_ltm_paper_style_30s_existing_gate3b_row",
                process_hard_timeout_sec=PROCESS_HARD_TIMEOUT_SEC,
            )
            contexts.append(ctx)
        except Exception as exc:  # noqa: BLE001
            failures.append(
                {
                    "g567_dataset_row_id": row.get("g567_dataset_row_id", ""),
                    "g567_evaluation_uid": row.get("g567_evaluation_uid", ""),
                    "map": row.get("map", ""),
                    "agent_count": row.get("agent_count", ""),
                    "failure": type(exc).__name__,
                    "message": str(exc),
                }
            )
    return contexts, failures


def method_for_plan_row(row: dict[str, Any]) -> str:
    candidate = str(row.get("candidate_id", ""))
    if candidate == g567.ADDITIVE_SOLVER_ALIAS:
        return METHOD_LTM
    if candidate == g567.STATIC_FLOW_SOLVER_ALIAS:
        return METHOD_STATIC
    return METHOD_ACTOR


def build_three_method_plan(contexts: list[g567.G567Context], theta_rows: list[dict[str, Any]], phase: str, max_workers: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    plan_rows, registry_rows = g567.build_plan_and_registry(contexts, theta_rows, phase, include_no_ltm=False)
    plan_rows = [row for row in plan_rows if str(row.get("candidate_id", "")) != g567.G556_SOLVER_ALIAS]
    candidate_ids = {str(row.get("candidate_id", "")) for row in plan_rows}
    registry_rows = [row for row in registry_rows if str(row.get("candidate_id", "")) in candidate_ids]
    actor_inference_by_context = {
        str(row.get("context_id", "")): row.get("actor_inference_ms", "")
        for row in theta_rows
    }
    for idx, row in enumerate(plan_rows):
        method = method_for_plan_row(row)
        row["plan_row_id"] = f"g568_ltm30_existingrow_{idx:08d}"
        row["execution_order_index"] = idx
        row["worker_count"] = max(1, int(max_workers))
        row["g568_method"] = method
        row["method_label"] = method
        row["ltm_paper_style_budget_sec"] = INTERNAL_BUDGET_SEC
        row["source_existing_gate3b_row_only"] = True
        row["no_training_no_regeneration_no_full"] = True
        row["actor_inference_ms"] = actor_inference_by_context.get(str(row.get("context_id", "")), "") if method == METHOD_ACTOR else 0.0
        if method == METHOD_LTM:
            row["role"] = METHOD_LTM
            row["sampling_policy"] = "paper_style_additive_ltm"
        elif method == METHOD_STATIC:
            row["role"] = METHOD_STATIC
            row["sampling_policy"] = "historical_static_flow_shield"
        else:
            row["role"] = METHOD_ACTOR
            row["sampling_policy"] = "gate3b_primary_actor_continuous_theta"
    return plan_rows, registry_rows


def audit_plan_budgets(plan_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = []
    failures = []
    by_context: dict[str, set[tuple[float, float]]] = defaultdict(set)
    for row in plan_rows:
        internal = finite_float(row.get("solver_internal_time_limit_sec"))
        hard = finite_float(row.get("process_hard_timeout_sec"))
        by_context[str(row.get("context_id", ""))].add((internal, hard))
        row_failures = []
        if abs(internal - INTERNAL_BUDGET_SEC) > 1.0e-9:
            row_failures.append("internal_budget_not_30s")
        if abs(hard - PROCESS_HARD_TIMEOUT_SEC) > 1.0e-9:
            row_failures.append("hard_timeout_not_60s")
        if row_failures:
            failures.extend(f"{row.get('plan_row_id')}:{item}" for item in row_failures)
        rows.append(
            {
                "plan_row_id": row.get("plan_row_id", ""),
                "context_id": row.get("context_id", ""),
                "g568_method": row.get("g568_method", ""),
                "agent_count": row.get("agent_count", row.get("agents", "")),
                "solver_internal_time_limit_sec": internal,
                "process_hard_timeout_sec": hard,
                "row_budget_audit_decision": "pass" if not row_failures else "fail",
                "row_budget_audit_failures": ";".join(row_failures),
            }
        )
    for context_id, budgets in by_context.items():
        if len(budgets) != 1:
            failures.append(f"{context_id}:methods_do_not_share_same_budget")
    summary = {
        "schema_version": "g568_ltm30_existingrow_budget_audit_v1",
        "decision": "pass" if not failures else "fail",
        "planned_rows": len(plan_rows),
        "failure_count": len(failures),
        "failures": failures[:100],
        "all_rows_30s_internal_60s_hard": not failures,
        "same_context_methods_same_budget": all(len(items) == 1 for items in by_context.values()),
    }
    return rows, summary


def run_direct_exact_time_capped(
    plan_rows: list[dict[str, Any]],
    *,
    binary: Path,
    max_workers: int,
    phase: str,
    p: dict[str, Path],
    overwrite: bool,
    chunk_rows: int,
    started_unix: float,
    stop_launch_after_sec: float,
    max_wall_sec: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if overwrite:
        for file_path in [p["results_raw"], p["results"], p["pairs"]]:
            file_path.unlink(missing_ok=True)
    completed_ids: set[str] = set()
    raw_rows: list[dict[str, Any]] = []
    partial_stop = False
    stop_reason = ""
    chunk_index = 0
    while len(completed_ids) < len(plan_rows):
        raw_rows = g567.read_rows(p["results_raw"])
        completed_ids = {str(row.get("plan_row_id", "")) for row in raw_rows if str(row.get("plan_row_id", "")).strip()}
        pending = [row for row in plan_rows if str(row.get("plan_row_id", "")) not in completed_ids]
        if not pending:
            break
        elapsed = time.time() - started_unix
        if elapsed >= stop_launch_after_sec:
            partial_stop = True
            stop_reason = "stop_launch_after_wall_clock_guard"
            break
        if elapsed >= max_wall_sec:
            partial_stop = True
            stop_reason = "max_wall_clock_guard"
            break
        next_ids = {str(row.get("plan_row_id", "")) for row in pending[: max(1, int(chunk_rows))]}
        active_ids = completed_ids | next_ids
        active_plan = [row for row in plan_rows if str(row.get("plan_row_id", "")) in active_ids]
        chunk_index += 1
        write_status(
            p["status"],
            phase="solver_running",
            chunk_index=chunk_index,
            completed_solver_rows=len(completed_ids),
            total_solver_rows=len(plan_rows),
            pending_solver_rows=len(pending),
            next_chunk_rows=len(next_ids),
            elapsed_sec=elapsed,
            stop_launch_after_sec=stop_launch_after_sec,
        )
        raw_rows = g567.run_direct_exact_plan(
            active_plan,
            binary=binary,
            overwrite=False,
            max_workers=max_workers,
            registry_path=p["registry"],
            result_csv=p["results_raw"],
            raw_csv=p["log_dir"] / "runner_results_mirror.csv",
            log_dir=p["log_dir"],
            scenario_dir=p["scenario_dir"],
            scenario_metadata=p["scenario_metadata"],
            manifest_prefix="g568_ltm30_existingrow",
            row_prefix="g568_ltm30_existingrow",
            execution_mode=f"g568_ltm30_existingrow_{g567.DIRECT_EXACT_EXECUTION_MODE}",
        )
    raw_rows = g567.read_rows(p["results_raw"])
    completed_ids = {str(row.get("plan_row_id", "")) for row in raw_rows if str(row.get("plan_row_id", "")).strip()}
    if len(completed_ids) < len(plan_rows) and not partial_stop:
        partial_stop = True
        stop_reason = "runner_returned_before_all_plan_rows"
    summary = {
        "schema_version": "g568_ltm30_existingrow_time_cap_v1",
        "partial_stop": partial_stop,
        "stop_reason": stop_reason,
        "chunks_launched": chunk_index,
        "completed_solver_rows": len(completed_ids),
        "total_solver_rows": len(plan_rows),
        "completed_context_method_rows_fraction": len(completed_ids) / max(1, len(plan_rows)),
        "elapsed_sec": time.time() - started_unix,
        "stop_launch_after_sec": stop_launch_after_sec,
        "max_wall_sec": max_wall_sec,
        "max_workers": max_workers,
        "chunk_rows": chunk_rows,
    }
    return raw_rows, summary


def result_success(row: dict[str, Any]) -> bool:
    for key in ["direct_exact_success", "success", "feasible", "direct_exact_feasible"]:
        if str(row.get(key, "")).strip():
            return boolish(row.get(key))
    return False


def result_ratio(row: dict[str, Any]) -> float:
    for key in ["direct_exact_sum_of_loss_ratio", "sum_of_loss_ratio", "ratio"]:
        value = finite_float(row.get(key))
        if math.isfinite(value):
            return value
    return math.nan


def q(values: list[float], quantile: float) -> float:
    vals = sorted(v for v in values if math.isfinite(v))
    if not vals:
        return math.nan
    idx = min(len(vals) - 1, max(0, int(math.ceil(quantile * len(vals))) - 1))
    return float(vals[idx])


def median(values: list[float]) -> float:
    vals = [v for v in values if math.isfinite(v)]
    return float(statistics.median(vals)) if vals else math.nan


def mean(values: list[float]) -> float:
    vals = [v for v in values if math.isfinite(v)]
    return float(statistics.mean(vals)) if vals else math.nan


def relative_improvement(a_ratio: float, b_ratio: float) -> float:
    if not (math.isfinite(a_ratio) and math.isfinite(b_ratio)):
        return math.nan
    return (b_ratio - a_ratio) / max(abs(b_ratio), 1.0e-9)


def enrich_results(rows: list[dict[str, Any]], plan_rows: list[dict[str, Any]], phase: str) -> list[dict[str, Any]]:
    plan_by_id = {str(row.get("plan_row_id", "")): row for row in plan_rows}
    out = g567.audit_results(rows, plan_rows, phase)
    enriched = []
    for row in out:
        plan = plan_by_id.get(str(row.get("plan_row_id", "")), {})
        method = str(plan.get("g568_method", method_for_plan_row(row)))
        solver_wall_ms = finite_float(row.get("process_elapsed_sec"), 0.0) * 1000.0
        actor_ms = finite_float(plan.get("actor_inference_ms"), 0.0) if method == METHOD_ACTOR else 0.0
        new = dict(row)
        new.update(
            {
                "g568_method": method,
                "method_label": method,
                "solver_wall_ms": solver_wall_ms,
                "actor_inference_ms": actor_ms,
                "total_method_ms": solver_wall_ms + actor_ms,
                "method_success": result_success(row),
                "sum_of_loss_ratio": result_ratio(row),
                "hard_timeout_row": boolish(row.get("process_hard_timeout_exceeded")),
                "infrastructure_failure_row": infrastructure_failure(row),
                "ltm30_existingrow_context": True,
                "source_existing_gate3b_row_only": True,
            }
        )
        enriched.append(new)
    return enriched


def infrastructure_failure(row: dict[str, Any]) -> bool:
    if boolish(row.get("process_hard_timeout_exceeded")):
        return True
    rc_raw = str(row.get("returncode", row.get("process_returncode", ""))).strip()
    if not rc_raw:
        return False
    rc = int_value(rc_raw, 999999)
    return rc not in {0, 2}


def build_pairs(rows: list[dict[str, Any]], selected_context_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected_meta = {str(row.get("g567_dataset_row_id", "")): row for row in selected_context_rows}
    by_context: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        context_id = str(row.get("context_id", row.get("g567_dataset_row_id", "")))
        method = str(row.get("g568_method", ""))
        if method:
            by_context[context_id][method] = row
    pairs: list[dict[str, Any]] = []
    for context_id, methods in sorted(by_context.items()):
        meta = selected_meta.get(context_id, {})
        rec: dict[str, Any] = {
            "context_id": context_id,
            "g567_evaluation_uid": meta.get("g567_evaluation_uid", ""),
            "split": meta.get("split", ""),
            "map": meta.get("map", ""),
            "map_family": meta.get("map_family", ""),
            "ltm_target_map": meta.get("ltm_target_map", ""),
            "ltm_target_match_type": meta.get("ltm_target_match_type", ""),
            "agent_count": meta.get("agent_count", meta.get("agents", "")),
            "official_scenario": meta.get("official_scenario", ""),
            "map_source_type": meta.get("map_source_type", ""),
            "scenario_source_type": meta.get("scenario_source_type", ""),
            "complete_triple": all(method in methods for method in METHODS),
        }
        for method in METHODS:
            row = methods.get(method, {})
            rec[f"{method}_present"] = bool(row)
            rec[f"{method}_success"] = result_success(row) if row else False
            rec[f"{method}_ratio"] = result_ratio(row) if row else math.nan
            rec[f"{method}_solver_wall_ms"] = finite_float(row.get("solver_wall_ms"), math.nan) if row else math.nan
            rec[f"{method}_actor_inference_ms"] = finite_float(row.get("actor_inference_ms"), 0.0) if row else math.nan
            rec[f"{method}_total_method_ms"] = finite_float(row.get("total_method_ms"), math.nan) if row else math.nan
            rec[f"{method}_hard_timeout"] = boolish(row.get("hard_timeout_row")) if row else False
            rec[f"{method}_infrastructure_failure"] = boolish(row.get("infrastructure_failure_row")) if row else False
        add_pairwise(rec, METHOD_ACTOR, METHOD_LTM, "actor_vs_ltm")
        add_pairwise(rec, METHOD_ACTOR, METHOD_STATIC, "actor_vs_static_flow")
        add_pairwise(rec, METHOD_STATIC, METHOD_LTM, "static_flow_vs_ltm")
        pairs.append(rec)
    return pairs


def add_pairwise(rec: dict[str, Any], a: str, b: str, label: str) -> None:
    a_success = boolish(rec.get(f"{a}_success"))
    b_success = boolish(rec.get(f"{b}_success"))
    a_ratio = finite_float(rec.get(f"{a}_ratio"))
    b_ratio = finite_float(rec.get(f"{b}_ratio"))
    both_success = a_success and b_success
    improvement = relative_improvement(a_ratio, b_ratio) if both_success else math.nan
    rec[f"{label}_both_success"] = both_success
    rec[f"{label}_success_gain"] = a_success and not b_success
    rec[f"{label}_success_regression"] = (not a_success) and b_success
    rec[f"{label}_relative_quality_improvement"] = improvement
    rec[f"{label}_harmful_quality_delta"] = max(0.0, -improvement) if math.isfinite(improvement) else math.nan
    rec[f"{label}_runtime_change_ms"] = finite_float(rec.get(f"{a}_total_method_ms")) - finite_float(rec.get(f"{b}_total_method_ms"))


def bootstrap_ci(values: list[float], seed: int = SELECTION_SEED, reps: int = 1000) -> dict[str, float]:
    vals = [v for v in values if math.isfinite(v)]
    if not vals:
        return {"median": math.nan, "ci_low": math.nan, "ci_high": math.nan, "n": 0}
    rng = random.Random(seed)
    medians = []
    for _ in range(max(1, reps)):
        sample = [vals[rng.randrange(len(vals))] for _ in vals]
        medians.append(statistics.median(sample))
    medians.sort()
    return {
        "median": float(statistics.median(vals)),
        "ci_low": float(medians[int(0.025 * (len(medians) - 1))]),
        "ci_high": float(medians[int(0.975 * (len(medians) - 1))]),
        "n": len(vals),
    }


def method_metrics(rows: list[dict[str, Any]], method: str) -> dict[str, Any]:
    subset = [row for row in rows if str(row.get("g568_method", "")) == method]
    successes = [row for row in subset if result_success(row)]
    ratios = [result_ratio(row) for row in successes]
    return {
        f"{method}_rows": len(subset),
        f"{method}_success_rate": sum(result_success(row) for row in subset) / max(1, len(subset)),
        f"{method}_success_count": sum(result_success(row) for row in subset),
        f"{method}_mean_sum_of_loss_ratio_successes": mean(ratios),
        f"{method}_median_sum_of_loss_ratio_successes": median(ratios),
        f"{method}_mean_solver_wall_ms": mean([finite_float(row.get("solver_wall_ms")) for row in subset]),
        f"{method}_median_solver_wall_ms": median([finite_float(row.get("solver_wall_ms")) for row in subset]),
        f"{method}_mean_total_method_ms": mean([finite_float(row.get("total_method_ms")) for row in subset]),
        f"{method}_median_total_method_ms": median([finite_float(row.get("total_method_ms")) for row in subset]),
        f"{method}_mean_actor_inference_ms": mean([finite_float(row.get("actor_inference_ms")) for row in subset]),
        f"{method}_hard_timeout_count": sum(boolish(row.get("hard_timeout_row")) for row in subset),
        f"{method}_infrastructure_failure_count": sum(boolish(row.get("infrastructure_failure_row")) for row in subset),
    }


def pair_metrics(pairs: list[dict[str, Any]], label: str) -> dict[str, Any]:
    complete = [row for row in pairs if boolish(row.get("complete_triple"))]
    improvements = [finite_float(row.get(f"{label}_relative_quality_improvement")) for row in complete]
    harmful = [finite_float(row.get(f"{label}_harmful_quality_delta")) for row in complete]
    runtimes = [finite_float(row.get(f"{label}_runtime_change_ms")) for row in complete]
    return {
        f"{label}_both_success_count": sum(boolish(row.get(f"{label}_both_success")) for row in complete),
        f"{label}_success_gain_count": sum(boolish(row.get(f"{label}_success_gain")) for row in complete),
        f"{label}_success_regression_count": sum(boolish(row.get(f"{label}_success_regression")) for row in complete),
        f"{label}_median_relative_quality_improvement": median(improvements),
        f"{label}_mean_relative_quality_improvement": mean(improvements),
        f"{label}_q25_relative_quality_improvement": q(improvements, 0.25),
        f"{label}_q75_relative_quality_improvement": q(improvements, 0.75),
        f"{label}_q95_harmful_quality_delta": q(harmful, 0.95),
        f"{label}_median_runtime_change_ms": median(runtimes),
        f"{label}_bootstrap_median_ci_low": bootstrap_ci(improvements)["ci_low"],
        f"{label}_bootstrap_median_ci_high": bootstrap_ci(improvements)["ci_high"],
    }


def summarize_all(rows: list[dict[str, Any]], pairs: list[dict[str, Any]], plan_rows: list[dict[str, Any]], time_cap: dict[str, Any], started: float) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "schema_version": "g568_ltm30_existingrow_summary_v1",
        "diagnostic_only": True,
        "no_training": True,
        "no_regeneration": True,
        "no_full_launch": True,
        "planned_rows": len(plan_rows),
        "executed_rows": len(rows),
        "planned_contexts": len({row.get("context_id") for row in plan_rows}),
        "completed_contexts_with_any_row": len({row.get("context_id") for row in rows}),
        "completed_same_context_triples": sum(boolish(row.get("complete_triple")) for row in pairs),
        "partial_stop": boolish(time_cap.get("partial_stop")),
        "time_cap": time_cap,
        "elapsed_sec": time.time() - started,
    }
    for method in METHODS:
        summary.update(method_metrics(rows, method))
    for label in ["actor_vs_ltm", "actor_vs_static_flow", "static_flow_vs_ltm"]:
        summary.update(pair_metrics(pairs, label))
    summary["decision_label"] = decision_label(summary)
    return summary


def decision_label(summary: dict[str, Any]) -> str:
    if boolish(summary.get("partial_stop")) or int_value(summary.get("completed_same_context_triples")) == 0:
        return "inconclusive_partial_or_timeout_limited"
    actor_ltm = finite_float(summary.get("actor_vs_ltm_median_relative_quality_improvement"), 0.0)
    actor_static = finite_float(summary.get("actor_vs_static_flow_median_relative_quality_improvement"), 0.0)
    reg_ltm = int_value(summary.get("actor_vs_ltm_success_regression_count"))
    reg_static = int_value(summary.get("actor_vs_static_flow_success_regression_count"))
    gain_ltm = int_value(summary.get("actor_vs_ltm_success_gain_count"))
    gain_static = int_value(summary.get("actor_vs_static_flow_success_gain_count"))
    if actor_ltm > 0.0 and actor_static > 0.0 and reg_ltm <= gain_ltm and reg_static <= gain_static:
        return "actor_positive_vs_ltm_and_static_flow_on_ltm30_subset"
    if actor_ltm > 0.0 and reg_ltm <= gain_ltm:
        return "actor_positive_vs_ltm_only_on_ltm30_subset"
    return "actor_tied_or_negative_on_ltm30_subset"


def grouped_summary(pairs: list[dict[str, Any]], group_cols: list[str]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in pairs:
        key = tuple(row.get(col, "") for col in group_cols)
        groups[key].append(row)
    out = []
    for key, rows in sorted(groups.items(), key=lambda item: tuple(map(str, item[0]))):
        rec = {col: value for col, value in zip(group_cols, key)}
        rec["contexts"] = len(rows)
        rec["complete_triples"] = sum(boolish(row.get("complete_triple")) for row in rows)
        for method in METHODS:
            rec[f"{method}_success_rate"] = sum(boolish(row.get(f"{method}_success")) for row in rows) / max(1, len(rows))
            rec[f"{method}_median_ratio"] = median([finite_float(row.get(f"{method}_ratio")) for row in rows if boolish(row.get(f"{method}_success"))])
        for label in ["actor_vs_ltm", "actor_vs_static_flow", "static_flow_vs_ltm"]:
            vals = [finite_float(row.get(f"{label}_relative_quality_improvement")) for row in rows]
            rec[f"{label}_median_relative_quality_improvement"] = median(vals)
            rec[f"{label}_success_gain_count"] = sum(boolish(row.get(f"{label}_success_gain")) for row in rows)
            rec[f"{label}_success_regression_count"] = sum(boolish(row.get(f"{label}_success_regression")) for row in rows)
        out.append(rec)
    return out


def write_summary_md(path: Path, summary: dict[str, Any], actor_meta: dict[str, Any], selection_meta: dict[str, Any]) -> None:
    def fmt(value: Any) -> str:
        f = finite_float(value)
        if math.isfinite(f):
            return f"{f:.6g}"
        return str(value)

    lines = [
        "# G5.68 LTM30 Existing-Row Replay Summary",
        "",
        "Diagnostic-only subset replay on existing Gate-3B non-training contexts. No training, no context/scenario generation, no full launch, no blind access.",
        "",
        f"- decision label: `{summary.get('decision_label')}`",
        f"- planned contexts: `{summary.get('planned_contexts')}`",
        f"- completed same-context triples: `{summary.get('completed_same_context_triples')}`",
        f"- planned/executed rows: `{summary.get('planned_rows')}` / `{summary.get('executed_rows')}`",
        f"- partial stop: `{summary.get('partial_stop')}`",
        f"- primary actor: `{actor_meta.get('primary_actor_path')}`",
        f"- selected splits: `{selection_meta.get('selected_split_counts')}`",
        "",
        "## Method Metrics",
        "",
        "| method | rows | success_rate | median_ratio_successes | hard_timeouts | infra_failures | mean_actor_ms |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for method in METHODS:
        lines.append(
            "| "
            + " | ".join(
                [
                    method,
                    str(summary.get(f"{method}_rows")),
                    fmt(summary.get(f"{method}_success_rate")),
                    fmt(summary.get(f"{method}_median_sum_of_loss_ratio_successes")),
                    str(summary.get(f"{method}_hard_timeout_count")),
                    str(summary.get(f"{method}_infrastructure_failure_count")),
                    fmt(summary.get(f"{method}_mean_actor_inference_ms")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Pairwise Same-Context Metrics",
            "",
            "| pair | both_success | success_gain | success_regression | median_rel_quality_improvement | q95_harm | bootstrap_CI |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for label in ["actor_vs_ltm", "actor_vs_static_flow", "static_flow_vs_ltm"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    label,
                    str(summary.get(f"{label}_both_success_count")),
                    str(summary.get(f"{label}_success_gain_count")),
                    str(summary.get(f"{label}_success_regression_count")),
                    fmt(summary.get(f"{label}_median_relative_quality_improvement")),
                    fmt(summary.get(f"{label}_q95_harmful_quality_delta")),
                    f"[{fmt(summary.get(f'{label}_bootstrap_median_ci_low'))}, {fmt(summary.get(f'{label}_bootstrap_median_ci_high'))}]",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Guardrails",
            "",
            "- This is a subset replay, not a full-campaign or paper claim.",
            "- If exact anytime curves are absent from solver logs, this report uses final 30s metrics and available runtime fields only.",
            "- CALIBRATION rows, if present, are reported as a limitation and are not training rows.",
            "- 3000-agent rows are excluded from the primary LTM-style analysis.",
            "",
        ]
    )
    g567.write_text(path, "\n".join(lines))


def git_text(args: list[str]) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, check=False, text=True, capture_output=True).stdout.strip()
    except Exception as exc:  # noqa: BLE001
        return f"git_error:{type(exc).__name__}:{exc}"


def write_repro(path: Path, actor_meta: dict[str, Any], plan_rows: list[dict[str, Any]], selected: list[dict[str, Any]], external_lacam_dirty: str) -> None:
    lines = [
        "# G5.68 LTM30 Existing-Row Repro",
        "",
        f"- git HEAD: `{git_text(['rev-parse', 'HEAD'])}`",
        f"- git branch: `{git_text(['branch', '--show-current'])}`",
        f"- git status short: `{git_text(['status', '--short'])[:4000]}`",
        f"- external/lacam2/lacam2 changed files: `{external_lacam_dirty or 'none'}`",
        f"- primary actor path: `{actor_meta.get('primary_actor_path')}`",
        f"- primary actor sha256: `{actor_meta.get('primary_actor_sha256')}`",
        f"- methods: `{METHODS}`",
        f"- method aliases: LTM `{g567.ADDITIVE_SOLVER_ALIAS}`, static-flow `{g567.STATIC_FLOW_SOLVER_ALIAS}`, actor generated continuous theta",
        f"- selected contexts: `{len(selected)}`",
        f"- planned rows: `{len(plan_rows)}`",
        f"- internal/hard timeout: `{INTERNAL_BUDGET_SEC}` / `{PROCESS_HARD_TIMEOUT_SEC}` seconds",
        "",
        "Validation checklist:",
        "",
        "- plan-only files written before solver execution",
        "- selected rows came from existing Gate-3B manifest",
        "- LABEL_TRAIN excluded",
        "- no 3000-agent primary rows",
        "- no solver semantic patching",
        "- no training or fine-tuning",
        "",
    ]
    g567.write_text(path, "\n".join(lines))


def write_partial_stop(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# G5.68 LTM30 Existing-Row Partial Stop",
        "",
        f"- partial stop: `{summary.get('partial_stop')}`",
        f"- stop reason: `{summary.get('time_cap', {}).get('stop_reason', '')}`",
        f"- executed rows: `{summary.get('executed_rows')}` / `{summary.get('planned_rows')}`",
        f"- completed same-context triples: `{summary.get('completed_same_context_triples')}`",
        f"- elapsed sec: `{summary.get('elapsed_sec')}`",
        "",
        "Partial results are acceptable under the task contract and must not be extrapolated to unrun contexts.",
        "",
    ]
    g567.write_text(path, "\n".join(lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-stage-root", type=Path, default=DEFAULT_SOURCE_STAGE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--phase", default=DEFAULT_PHASE)
    parser.add_argument("--target-contexts", type=int, default=DEFAULT_TARGET_CONTEXTS)
    parser.add_argument("--max-tiers-per-map", type=int, default=5)
    parser.add_argument("--max-contexts-per-map-tier", type=int, default=25)
    parser.add_argument("--allow-calibration", action="store_true", default=True)
    parser.add_argument("--no-calibration", action="store_false", dest="allow_calibration")
    parser.add_argument("--max-workers", type=int, default=DEFAULT_MAX_WORKERS)
    parser.add_argument("--chunk-rows", type=int, default=DEFAULT_CHUNK_ROWS)
    parser.add_argument("--stop-launch-after-sec", type=float, default=DEFAULT_STOP_LAUNCH_AFTER_SEC)
    parser.add_argument("--max-wall-sec", type=float, default=DEFAULT_MAX_WALL_SEC)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--inference-token-budget", type=int, default=3000)
    parser.add_argument("--inference-progress-interval-sec", type=float, default=60.0)
    parser.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = time.time()
    configure_g567(args.source_stage_root, args.output_root)
    p = paths(args.output_root)

    for directory in [p["tables"], p["reports"], p["logs"], p["tmp"], p["log_dir"], p["scenario_dir"]]:
        directory.mkdir(parents=True, exist_ok=True)

    write_status(p["status"], phase="starting", output_root=str(args.output_root), source_stage_root=str(args.source_stage_root))

    manifest_rows = g567.read_rows(g567.VALID_CONTEXT_MANIFEST)
    inventory, selected_rows, bindings, selection_meta = build_inventory_and_selection(
        manifest_rows,
        target_contexts=max(1, int(args.target_contexts)),
        max_tiers_per_map=max(1, int(args.max_tiers_per_map)),
        max_contexts_per_map_tier=max(1, int(args.max_contexts_per_map_tier)),
        allow_calibration=bool(args.allow_calibration),
    )
    g567.write_rows(p["inventory"], inventory)
    g567.write_rows(p["selected_contexts"], selected_rows)
    write_selection_report(p["selection_report"], bindings, inventory, selected_rows, selection_meta)

    actor_path, actor_meta = discover_primary_actor(args.source_stage_root)
    actor_path_resolved = g567.resolve(actor_path)
    if not actor_path_resolved.exists():
        raise FileNotFoundError(f"primary actor checkpoint missing: {actor_path}")
    actor_meta["primary_actor_path"] = str(actor_path)
    actor_meta["primary_actor_resolved_path"] = str(actor_path_resolved)
    actor_meta["primary_actor_sha256"] = sha256_file(actor_path_resolved)

    contexts, context_failures = materialize_selected_contexts(selected_rows)
    if context_failures:
        g567.write_rows(p["tables"] / "g568_ltm30_existingrow_context_materialization_failures.csv", context_failures)
    if not contexts:
        raise RuntimeError("no selected contexts materialized")

    inference_started = time.perf_counter()
    theta_rows = g567.infer_checkpoint_thetas(
        contexts,
        [actor_path],
        device=args.device,
        batch_size=max(1, int(args.batch_size)),
        phase=args.phase,
        token_budget=max(0, int(args.inference_token_budget)),
        progress_interval_sec=float(args.inference_progress_interval_sec),
        output_path=p["theta_rows"],
        resume=not bool(args.overwrite),
    )
    inference_ms = (time.perf_counter() - inference_started) * 1000.0
    per_context_ms = inference_ms / max(1, len(theta_rows))
    for row in theta_rows:
        row["actor_inference_ms"] = per_context_ms
        row["actor_inference_measurement"] = "checkpoint_total_wall_ms_divided_by_contexts"
        row["actor_inference_total_checkpoint_wall_ms"] = inference_ms
        row["primary_actor_checkpoint"] = True
    g567.write_rows(p["theta_rows"], theta_rows)

    plan_rows, registry_rows = build_three_method_plan(contexts, theta_rows, args.phase, int(args.max_workers))
    budget_rows, budget_summary = audit_plan_budgets(plan_rows)
    g567.write_rows(g567.SOLVER_BUDGET_AUDIT, budget_rows)
    g567.write_json(g567.SOLVER_BUDGET_AUDIT_SUMMARY, budget_summary)
    if budget_summary.get("decision") != "pass":
        raise RuntimeError(f"budget audit failed: {budget_summary}")

    g567.write_rows(p["plan"], plan_rows)
    g567.write_rows(p["registry"], registry_rows)
    method_alias = {
        "schema_version": "g568_ltm30_existingrow_method_alias_audit_v1",
        "ltm_30s": {
            "solver_alias": g567.ADDITIVE_SOLVER_ALIAS,
            "interpretation": "paper_style_additive_ltm",
            "traffic_map_range_expected": "[0,10]",
        },
        "static_flow_30s": {
            "solver_alias": g567.STATIC_FLOW_SOLVER_ALIAS,
            "interpretation": "historical_static_flow_shield",
        },
        "gate3b_actor_30s": {
            "checkpoint": str(actor_path),
            "checkpoint_sha256": actor_meta["primary_actor_sha256"],
            "interpretation": "Gate-3B primary actor continuous theta",
        },
    }
    g567.write_json(p["method_alias_audit"], method_alias)

    external_lacam_dirty = git_text(["status", "--short", "--", "external/lacam2/lacam2"])
    write_repro(p["repro"], actor_meta, plan_rows, selected_rows, external_lacam_dirty)

    write_status(
        p["status"],
        phase="plan_created",
        selected_contexts=len(contexts),
        selected_rows=len(selected_rows),
        materialization_failures=len(context_failures),
        planned_solver_rows=len(plan_rows),
        actor_meta=actor_meta,
    )
    if args.plan_only:
        summary = {
            "schema_version": "g568_ltm30_existingrow_plan_only_v1",
            "decision_label": "plan_only_not_executed",
            "selected_contexts": len(contexts),
            "planned_rows": len(plan_rows),
            "actor_meta": actor_meta,
            "selection_meta": selection_meta,
        }
        g567.write_json(p["summary_json"], summary)
        write_summary_md(p["summary_md"], summary, actor_meta, selection_meta)
        return 0

    raw_rows, time_cap = run_direct_exact_time_capped(
        plan_rows,
        binary=args.binary,
        max_workers=max(1, int(args.max_workers)),
        phase=args.phase,
        p=p,
        overwrite=bool(args.overwrite),
        chunk_rows=max(1, int(args.chunk_rows)),
        started_unix=started,
        stop_launch_after_sec=float(args.stop_launch_after_sec),
        max_wall_sec=float(args.max_wall_sec),
    )

    rows = enrich_results(raw_rows, plan_rows, args.phase)
    g567.write_rows(p["results"], rows)
    pairs = build_pairs(rows, selected_rows)
    g567.write_rows(p["pairs"], pairs)
    g567.write_rows(p["by_map"], grouped_summary(pairs, ["ltm_target_map", "map"]))
    g567.write_rows(p["by_map_family"], grouped_summary(pairs, ["map_family"]))
    g567.write_rows(p["by_agent_tier"], grouped_summary(pairs, ["agent_count"]))
    g567.write_rows(p["by_split"], grouped_summary(pairs, ["split"]))
    g567.write_rows(p["by_public_official"], grouped_summary(pairs, ["map_source_type", "official_scenario", "scenario_source_type"]))

    summary = summarize_all(rows, pairs, plan_rows, time_cap, started)
    summary.update(
        {
            "actor_meta": actor_meta,
            "selection_meta": selection_meta,
            "context_materialization_failures": len(context_failures),
            "anytime_curves_available": False,
            "anytime_curve_limitation": "Exact best-so-far checkpoint curves were not available without solver-semantic changes; final 30s metrics and runtime fields are reported.",
        }
    )
    g567.write_json(p["summary_json"], summary)
    write_summary_md(p["summary_md"], summary, actor_meta, selection_meta)
    if boolish(summary.get("partial_stop")):
        write_partial_stop(p["partial_stop"], summary)

    write_status(
        p["status"],
        phase="complete",
        decision_label=summary.get("decision_label"),
        executed_rows=summary.get("executed_rows"),
        planned_rows=summary.get("planned_rows"),
        completed_same_context_triples=summary.get("completed_same_context_triples"),
        partial_stop=summary.get("partial_stop"),
        elapsed_sec=summary.get("elapsed_sec"),
        summary_json=str(p["summary_json"]),
    )
    print(json.dumps({"decision_label": summary.get("decision_label"), "summary_json": str(p["summary_json"])}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

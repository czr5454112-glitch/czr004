"""Repair5G.5.49 calibration completion and fulltheta replay.

G5.49 continues from the underpowered G5.48 calibration result.  It keeps
`static_flow_shield` as the primary baseline for neural/fulltheta UpdateParams,
separates unique strata from selected horizon rows, and only advances generator
or blind stages by explicit gates.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import statistics
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
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
import repair5g547_common as g547  # noqa: E402
import repair5g548_common as g548  # noqa: E402


PLAN_FILE = "czr004_g549_calibration_completion_staticflow_primary_fulltheta_replay_plan.md"

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g549_g548_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g549_g548_verification_summary.json"
VERIFY_AUDIT_CSV = "outputs/tables/phase5p5_repair5g549_g548_artifact_audit.csv"

SEMANTICS_REPORT = "outputs/reports/phase5p5_repair5g549_g548_calibration_semantics.md"
SEMANTICS_SUMMARY = "outputs/reports/phase5p5_repair5g549_g548_calibration_semantics_summary.json"
SELECTED_HORIZON_AUDIT_CSV = "outputs/tables/phase5p5_repair5g549_g548_selected_horizon_audit.csv"
UNIQUE_EVALUABLE_STRATA_CSV = "outputs/tables/phase5p5_repair5g549_g548_unique_evaluable_strata.csv"
NON_EVALUABLE_STRATA_AUDIT_CSV = "outputs/tables/phase5p5_repair5g549_g548_non_evaluable_strata_audit.csv"

TOPUP_PLAN_CSV = "outputs/tables/phase5p5_repair5g549_calibration_topup_plan.csv"
TOPUP_POLICY_BREAKDOWN_CSV = "outputs/tables/phase5p5_repair5g549_calibration_topup_policy_breakdown.csv"
TOPUP_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g549_calibration_topup_plan_summary.json"
TOPUP_PLAN_REPORT = "outputs/reports/phase5p5_repair5g549_calibration_topup_plan.md"

TOPUP_RESULTS_CSV = "outputs/tables/phase5p5_repair5g549_calibration_topup_results.csv"
TOPUP_RESULTS_RAW_CSV = "outputs/tables/phase5p5_repair5g549_calibration_topup_results.raw.csv"
CALIBRATION_SELECTED_HORIZONS_CSV = "outputs/tables/phase5p5_repair5g549_calibration_selected_horizons_v2.csv"
CALIBRATION_NON_EVALUABLE_CSV = "outputs/tables/phase5p5_repair5g549_calibration_non_evaluable_strata_v2.csv"
CALIBRATION_BY_MAP_CSV = "outputs/tables/phase5p5_repair5g549_calibration_by_map_family.csv"
CALIBRATION_BY_BUDGET_CSV = "outputs/tables/phase5p5_repair5g549_calibration_by_budget.csv"
CALIBRATION_SUMMARY = "outputs/reports/phase5p5_repair5g549_calibration_topup_summary.json"
CALIBRATION_REPORT = "outputs/reports/phase5p5_repair5g549_calibration_topup.md"
TOPUP_LOG_DIR = "outputs/logs/phase5p5_repair5g549_calibration_topup"
TOPUP_RUN_JSONL = f"{TOPUP_LOG_DIR}/runs.jsonl"
TOPUP_COMMAND_JSONL = f"{TOPUP_LOG_DIR}/commands.jsonl"
TOPUP_UPDATE_JSONL = f"{TOPUP_LOG_DIR}/updates.jsonl"
TOPUP_PROBE_JSONL = f"{TOPUP_LOG_DIR}/counterfactual_probes.jsonl"
TOPUP_CHECKPOINT_JSONL = f"{TOPUP_LOG_DIR}/checkpoints.jsonl"
TOPUP_STATUS_JSON = f"{TOPUP_LOG_DIR}/status.json"
TOPUP_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g549_calibration_topup_scenarios"
TOPUP_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g549_calibration_topup_scenario_generation.json"

FULLTHETA_REGISTRY_CSV = "outputs/tables/phase5p5_repair5g549_fulltheta_registry.csv"
FULLTHETA_REGISTRY_SUMMARY = "outputs/reports/phase5p5_repair5g549_fulltheta_registry_summary.json"
FULLTHETA_REGISTRY_REPORT = "outputs/reports/phase5p5_repair5g549_fulltheta_registry.md"
FULLTHETA_PLAN_CSV = "outputs/tables/phase5p5_repair5g549_fulltheta_replay_plan.csv"
FULLTHETA_POLICY_BREAKDOWN_CSV = "outputs/tables/phase5p5_repair5g549_fulltheta_replay_policy_breakdown.csv"
FULLTHETA_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g549_fulltheta_replay_plan_summary.json"
FULLTHETA_PLAN_REPORT = "outputs/reports/phase5p5_repair5g549_fulltheta_replay_plan.md"

FULLTHETA_RESULTS_CSV = "outputs/tables/phase5p5_repair5g549_fulltheta_replay_results.csv"
FULLTHETA_RESULTS_RAW_CSV = "outputs/tables/phase5p5_repair5g549_fulltheta_replay_results.raw.csv"
FULLTHETA_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g549_fulltheta_selected_vs_static_flow.csv"
FULLTHETA_VS_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g549_fulltheta_selected_vs_additive.csv"
FULLTHETA_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g549_fulltheta_selected_vs_family_static.csv"
FULLTHETA_TRUE_GAIN_CSV = "outputs/tables/phase5p5_repair5g549_fulltheta_true_safe_gain_regions.csv"
FULLTHETA_SAFE_NO_GAIN_CSV = "outputs/tables/phase5p5_repair5g549_fulltheta_safe_but_no_gain_regions.csv"
FULLTHETA_UNSAFE_USEFUL_CSV = "outputs/tables/phase5p5_repair5g549_fulltheta_unsafe_but_useful_regions.csv"
FULLTHETA_NON_EVALUABLE_CSV = "outputs/tables/phase5p5_repair5g549_fulltheta_non_evaluable_regions.csv"
FULLTHETA_PARAM_SENSITIVITY_CSV = "outputs/tables/phase5p5_repair5g549_fulltheta_parameter_sensitivity.csv"
FULLTHETA_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g549_fulltheta_failure_cases.csv"
FULLTHETA_SUMMARY = "outputs/reports/phase5p5_repair5g549_fulltheta_replay_summary.json"
FULLTHETA_REPORT = "outputs/reports/phase5p5_repair5g549_fulltheta_replay.md"
FULLTHETA_LOG_DIR = "outputs/logs/phase5p5_repair5g549_fulltheta_replay"
FULLTHETA_RUN_JSONL = f"{FULLTHETA_LOG_DIR}/runs.jsonl"
FULLTHETA_COMMAND_JSONL = f"{FULLTHETA_LOG_DIR}/commands.jsonl"
FULLTHETA_UPDATE_JSONL = f"{FULLTHETA_LOG_DIR}/updates.jsonl"
FULLTHETA_PROBE_JSONL = f"{FULLTHETA_LOG_DIR}/counterfactual_probes.jsonl"
FULLTHETA_CHECKPOINT_JSONL = f"{FULLTHETA_LOG_DIR}/checkpoints.jsonl"
FULLTHETA_STATUS_JSON = f"{FULLTHETA_LOG_DIR}/status.json"
FULLTHETA_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g549_fulltheta_replay_scenarios"
FULLTHETA_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g549_fulltheta_replay_scenario_generation.json"

RISK_MODEL_EVAL_CSV = "outputs/tables/phase5p5_repair5g549_risk_model_eval.csv"
UTILITY_MODEL_EVAL_CSV = "outputs/tables/phase5p5_repair5g549_utility_model_eval.csv"
GENERATOR_EVAL_CSV = "outputs/tables/phase5p5_repair5g549_generator_eval.csv"
GENERATED_THETA_CSV = "outputs/tables/phase5p5_repair5g549_generated_theta_candidates.csv"
GENERATOR_SUMMARY = "outputs/reports/phase5p5_repair5g549_risk_utility_generator_summary.json"
GENERATOR_REPORT = "outputs/reports/phase5p5_repair5g549_risk_utility_generator.md"
MODEL_MANIFEST = "artifacts/models/laur_ltm/repair5g549_model_manifest.json"

TARGETED_RESULTS_CSV = "outputs/tables/phase5p5_repair5g549_generated_theta_targeted_results.csv"
TARGETED_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g549_generated_theta_targeted_vs_static_flow.csv"
TARGETED_VS_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g549_generated_theta_targeted_vs_additive.csv"
TARGETED_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g549_generated_theta_targeted_vs_family_static.csv"
TARGETED_FAILURES_CSV = "outputs/tables/phase5p5_repair5g549_generated_theta_targeted_failure_cases.csv"
TARGETED_SUMMARY = "outputs/reports/phase5p5_repair5g549_generated_theta_targeted_summary.json"
TARGETED_REPORT = "outputs/reports/phase5p5_repair5g549_generated_theta_targeted.md"

BLIND_RESULTS_CSV = "outputs/tables/phase5p5_repair5g549_blind_results.csv"
BLIND_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g549_blind_selected_vs_static_flow.csv"
BLIND_VS_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g549_blind_selected_vs_additive.csv"
BLIND_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g549_blind_selected_vs_family_static.csv"
BLIND_FAILURES_CSV = "outputs/tables/phase5p5_repair5g549_blind_failure_cases.csv"
BLIND_SUMMARY = "outputs/reports/phase5p5_repair5g549_blind_evidence_summary.json"
BLIND_REPORT = "outputs/reports/phase5p5_repair5g549_blind_evidence.md"

DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g549_decision_summary.json"
DECISION_REPORT = "outputs/reports/phase5p5_repair5g549_decision.md"

THETA_COLUMNS = list(g547.THETA_COLUMNS)
FULL_ONLY_FIELDS = set(g547.G547_FULL_ONLY_FIELDS)
BASELINE_ROLES = dict(g547.BASELINE_ROLES)
ADDITIVE = g547.ADDITIVE
STATIC_FLOW = g547.STATIC_FLOW
FAMILY_STATIC = g547.FAMILY_STATIC
BASE_MAPS = list(g548.BASE_MAPS)
CORE_TOPUP_SEEDS = list(range(1220, 1320))
HARD_RECOVERY_SEEDS = list(range(1320, 1324))
FULLTHETA_SEEDS = list(range(1400, 1520))

CORE_TOPUP_SHORT_BUDGETS = [1000, 2000, 5000]
CALIBRATION_FULLTHETA_ROWS_PER_CONTEXT = 27
FULLTHETA_CANDIDATES_PER_CONTEXT = 100
FULLTHETA_REGISTRY_SIZE = 2040


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
    ids.extend(CORE_TOPUP_SEEDS)
    ids.extend(HARD_RECOVERY_SEEDS)
    ids.extend(FULLTHETA_SEEDS)
    bad = [value for value in ids if 166 <= value <= 205]
    if bad:
        print(json.dumps({"decision": "reserved_id_guard_rejected", "label": label, "ids": sorted(set(bad))}))
        raise SystemExit(1)


def table_count(path: str | Path) -> int:
    p = resolve(path)
    if not p.exists():
        return 0
    if p.suffix.lower() == ".csv":
        with p.open(newline="", encoding="utf-8") as handle:
            return max(0, sum(1 for _ in csv.reader(handle)) - 1)
    if p.suffix.lower() == ".jsonl":
        with p.open(encoding="utf-8", errors="ignore") as handle:
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


def write_skip_table(path: str, reason: str) -> None:
    write_rows(path, [{"decision": "skipped_by_gate", "reason": reason, **claims()}], fieldnames=["decision", "reason", *claims().keys()])


def write_rows_atomic(path: str | Path, rows: list[dict[str, Any]]) -> None:
    target = resolve(path)
    tmp = target.with_name(target.name + ".tmp")
    last_error: OSError | None = None
    for _attempt in range(5):
        try:
            write_rows(tmp, rows)
            tmp.replace(target)
            return
        except OSError as exc:
            last_error = exc
            time.sleep(0.25)
    if last_error is not None:
        raise last_error


def append_rows(existing: list[dict[str, Any]], new_rows: list[dict[str, Any]], key_fields: list[str]) -> list[dict[str, Any]]:
    seen = {tuple(str(row.get(field, "")) for field in key_fields) for row in existing}
    out = list(existing)
    for row in new_rows:
        key = tuple(str(row.get(field, "")) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def append_rows_to_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    target = resolve(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str]
    write_header = not target.exists() or target.stat().st_size == 0
    if write_header:
        fieldnames = []
        for row in rows:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)
    else:
        with target.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            fieldnames = next(reader, [])
    with target.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def map_for_family(family: str) -> str:
    return next((name for name in BASE_MAPS if infer_map_family(name) == family), BASE_MAPS[0])


def seed_block(seed: Any) -> str:
    value = int(number(seed, 0))
    return f"{(value // 20) * 20}_{(value // 20) * 20 + 19}"


def theta_for_baseline(candidate: str) -> dict[str, Any]:
    if candidate == ADDITIVE:
        return g545.additive_theta()
    if candidate == FAMILY_STATIC:
        return g545.theta_from_compact(c=1.25, b=1.25, f=1.0, w=0.75, dc=0.95, df=1.0, beta=0.60, max_shield=0.75)
    return g545.static_flow_theta()


def baseline_plan_rows(context: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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
                "counts_as_g549_calibration_topup": context.get("panel") == "calibration_topup",
                "counts_as_g549_fulltheta_replay": context.get("panel") == "fulltheta_replay",
                **g547.clamp_theta(theta_for_baseline(candidate)),
                **claims(),
            }
        )
    return rows


def calibration_registry_rows() -> list[dict[str, Any]]:
    registry = ensure_fulltheta_registry()
    return registry[:CALIBRATION_FULLTHETA_ROWS_PER_CONTEXT]


def calibration_fulltheta_plan_rows(context: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for reg in calibration_registry_rows():
        rows.append(
            {
                "plan_row_id": f"{prefix}_{len(rows):08d}",
                **context,
                "role": f"generated_theta::{reg['candidate_id']}",
                "candidate_id": reg["candidate_id"],
                "materialized_method": reg["candidate_id"],
                "sampling_policy": f"calibration_fulltheta::{reg.get('changed_field_for_smoke_pair', '')}",
                "registry_label": reg.get("registry_label", ""),
                "theta_cluster": f"calibration_fulltheta::{reg.get('changed_field_for_smoke_pair', '')}",
                "counts_as_g549_calibration_topup": context.get("panel") == "calibration_topup",
                "counts_as_g549_fulltheta_replay": False,
                **{col: reg.get(col, "") for col in THETA_COLUMNS},
                **claims(),
            }
        )
    return rows


def topup_contexts(max_contexts: int = 0) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for seed in CORE_TOPUP_SEEDS:
        for family in ["maze", "random"]:
            map_name = map_for_family(family)
            for agents in [50, 100]:
                for short_budget in CORE_TOPUP_SHORT_BUDGETS:
                    contexts.append(
                        {
                            "panel": "calibration_topup",
                            "route": "B1_core_evaluable_topup",
                            "context_id": f"{map_name}|a{agents}|s{seed}|b2000|g549_core_short{short_budget}_t050_i2",
                            "map": map_name,
                            "map_family": family,
                            "agents": agents,
                            "seed": seed,
                            "budget_ms": 2000,
                            "nominal_budget_ms": 2000,
                            "horizon_id": f"g549_core_short{short_budget}_t050_i2",
                            "short_budget_ms": short_budget,
                            "base_time_limit_sec": csv_number(0.50),
                            "ltm_max_iterations": 2,
                            "fresh_seed_block": seed_block(seed),
                            "source": "g549_core_evaluable_topup_real_solver",
                        }
                    )
    for seed in HARD_RECOVERY_SEEDS:
        for family in ["warehouse", "maze", "random"]:
            map_name = map_for_family(family)
            budgets = [500, 1000, 2000] if family == "warehouse" else [500, 1000]
            for agents in [50, 100]:
                for budget in budgets:
                    for short_budget in [2000, 5000]:
                        contexts.append(
                            {
                                "panel": "calibration_topup",
                                "route": "B2_hard_stratum_recovery",
                                "context_id": f"{map_name}|a{agents}|s{seed}|b{budget}|g549_hard_short{short_budget}_t100_i4",
                                "map": map_name,
                                "map_family": family,
                                "agents": agents,
                                "seed": seed,
                                "budget_ms": budget,
                                "nominal_budget_ms": budget,
                                "horizon_id": f"g549_hard_short{short_budget}_t100_i4",
                                "short_budget_ms": short_budget,
                                "base_time_limit_sec": csv_number(1.00),
                                "ltm_max_iterations": 4,
                                "fresh_seed_block": seed_block(seed),
                                "source": "g549_hard_stratum_recovery_diagnostic_real_solver",
                            }
                        )
    if max_contexts > 0:
        contexts = contexts[:max_contexts]
    return contexts


def write_calibration_topup_plan(max_contexts: int = 0) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for context in topup_contexts(max_contexts):
        prefix = f"g549_topup_{len(rows):08d}"
        rows.extend(baseline_plan_rows(context, prefix))
        rows.extend(calibration_fulltheta_plan_rows(context, prefix))
    for idx, row in enumerate(rows):
        row["plan_row_id"] = f"g549_topup_{idx:08d}"
    write_rows(TOPUP_PLAN_CSV, rows)
    breakdown = []
    grouped = Counter((row.get("route", ""), row.get("sampling_policy", "")) for row in rows)
    for (route, policy), count in sorted(grouped.items()):
        breakdown.append({"route": route, "sampling_policy": policy, "planned_rows": count, **claims()})
    write_rows(TOPUP_POLICY_BREAKDOWN_CSV, breakdown)
    contexts = {row.get("context_id") for row in rows}
    summary = {
        "schema_version": "phase5p5_repair5g549_calibration_topup_plan_summary_v1",
        "decision": "g549_calibration_topup_plan_created",
        "planned_solver_rows": len(rows),
        "planned_contexts": len(contexts),
        "planned_static_flow_rows": sum(1 for row in rows if row.get("role") == "static_flow_shield"),
        "planned_fulltheta_smoke_rows": sum(1 for row in rows if str(row.get("role", "")).startswith("generated_theta::")),
        "core_route_rows": sum(1 for row in rows if row.get("route") == "B1_core_evaluable_topup"),
        "hard_recovery_rows": sum(1 for row in rows if row.get("route") == "B2_hard_stratum_recovery"),
        "minimum_plan_gate_passed": len(rows) >= 8000 and len(contexts) >= 720,
        **claims(),
    }
    write_json(TOPUP_PLAN_SUMMARY, summary)
    write_text(
        TOPUP_PLAN_REPORT,
        "# G5.49 Calibration Top-Up Plan\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- planned solver rows: `{summary['planned_solver_rows']}`\n"
        f"- planned contexts: `{summary['planned_contexts']}`\n"
        f"- planned static_flow rows: `{summary['planned_static_flow_rows']}`\n"
        f"- planned fulltheta smoke rows: `{summary['planned_fulltheta_smoke_rows']}`\n"
        "- route B1 focuses maze/random 50/100-agent 2000ms calibrated-core horizons.\n"
        "- route B2 samples warehouse and low-budget hard strata diagnostically; it cannot support a broad final claim by itself.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "contexts": len(contexts)}))
    return rows


def group_key(row: dict[str, Any]) -> tuple[str, int, int, int, str]:
    return (
        str(row.get("map", "")),
        int(number(row.get("agents"), 0)),
        int(number(row.get("seed"), 0)),
        int(number(row.get("nominal_budget_ms", row.get("budget_ms", 0)), 0)),
        str(row.get("horizon_id", "")),
    )


def probe_context_groups(plan_rows: list[dict[str, Any]]) -> list[tuple[tuple[str, int, int, int, str], list[dict[str, Any]]]]:
    grouped: dict[tuple[str, int, int, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in plan_rows:
        grouped[group_key(row)].append(row)
    family_rank = {"random": 0, "maze": 1, "warehouse": 2}

    def sort_key(item: tuple[tuple[str, int, int, int, str], list[dict[str, Any]]]) -> tuple[Any, ...]:
        key = item[0]
        return (family_rank.get(infer_map_family(key[0]), 9), key[1], key[2], key[3], key[4])

    return sorted(grouped.items(), key=sort_key)


def completed_groups_from_results(plan_rows: list[dict[str, Any]], result_path: str) -> set[tuple[str, int, int, int, str]]:
    expected = {
        key: {str(row.get("materialized_method")) for row in rows if row.get("materialized_method")}
        for key, rows in probe_context_groups(plan_rows)
    }
    seen: dict[tuple[str, int, int, int, str], set[str]] = defaultdict(set)
    for row in read_rows(result_path):
        seen[group_key(row)].add(str(row.get("materialized_method", "")))
    return {key for key, methods in expected.items() if methods and methods.issubset(seen.get(key, set()))}


def task_file(temp_dir: Path, index: int, key: tuple[str, int, int, int, str], suffix: str) -> Path:
    token = stable_hash("|".join(map(str, key)), modulo=10**12)
    return temp_dir / f"context_{index:06d}_{token:012d}.{suffix}.jsonl"


def plan_lookup(group_rows: list[dict[str, Any]]) -> dict[tuple[str, str, str, str, str], dict[str, Any]]:
    return {
        (
            str(row.get("map")),
            str(row.get("agents")),
            str(row.get("seed")),
            str(row.get("budget_ms")),
            str(row.get("materialized_method")),
        ): row
        for row in group_rows
    }


def enrich_or_placeholder(
    raw_probe: list[dict[str, Any]],
    group_rows: list[dict[str, Any]],
    key: tuple[str, int, int, int, str],
    *,
    row_prefix: str,
    execution_mode: str,
    command_row: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    first = group_rows[0]
    map_name, agents_count, seed, nominal_budget, horizon_id = key
    if raw_probe:
        enriched = g546.enrich_probe_rows(raw_probe, group_rows, row_prefix=row_prefix)
    else:
        timeout_exceeded = bool(command_row and command_row.get("process_hard_timeout_exceeded"))
        context_key = f"{map_name}|{agents_count}|{seed}|{nominal_budget}|no_probe|{horizon_id}"
        enriched = []
        for idx, plan in enumerate(group_rows):
            enriched.append(
                {
                    f"{row_prefix}_row_id": f"{row_prefix}_no_probe_{idx:08d}_{stable_hash(context_key, plan.get('materialized_method'), modulo=10**10):010d}",
                    "execution_mode": execution_mode,
                    "real_solver_execution": True,
                    "context_key": context_key,
                    "context_id": plan.get("context_id", ""),
                    "role": plan.get("role", ""),
                    "candidate_id": plan.get("candidate_id", ""),
                    "materialized_method": plan.get("materialized_method", ""),
                    "sampling_policy": plan.get("sampling_policy", ""),
                    "map": map_name,
                    "map_family": infer_map_family(map_name),
                    "agents": agents_count,
                    "seed": seed,
                    "budget_ms": nominal_budget,
                    "iteration": "",
                    "solution_found": "" if timeout_exceeded else False,
                    "probe_feasible": "" if timeout_exceeded else False,
                    "sum_of_loss_ratio": "",
                    "probe_sum_of_loss": "",
                    "probe_lower_bound": "",
                    "probe_runtime_ms": "",
                    "expanded_nodes": "",
                    "low_level_pibt_calls": "",
                    "trace_event_count": "",
                    "candidate_recognized": not timeout_exceeded,
                    "updateparams_hash": "",
                    "updateparams_fingerprint": "",
                    "traffic_before_hash_full": "",
                    **{col: plan.get(col, "") for col in THETA_COLUMNS},
                    **claims(),
                }
            )
    lookup = plan_lookup(group_rows)
    for row in enriched:
        plan = lookup.get(
            (
                str(row.get("map")),
                str(row.get("agents")),
                str(row.get("seed")),
                str(row.get("budget_ms")),
                str(row.get("materialized_method")),
            ),
            {},
        )
        row["execution_mode"] = execution_mode
        row["counts_as_new_g549_solver_row"] = True
        row["probe_materialized"] = bool(raw_probe)
        timeout_exceeded = bool(command_row and command_row.get("process_hard_timeout_exceeded"))
        row["infrastructure_timeout"] = timeout_exceeded
        row["scientific_result_valid"] = not timeout_exceeded
        row["excluded_from_scientific_labels"] = timeout_exceeded
        if timeout_exceeded:
            row["solution_found"] = ""
            row["probe_feasible"] = ""
            row["candidate_recognized"] = False
        row["no_probe_reason"] = (
            ""
            if raw_probe
            else ("process_hard_timeout_exceeded" if timeout_exceeded else "outer_static_flow_no_solution_or_no_counterfactual_checkpoint")
        )
        if command_row:
            for field in [
                "returncode",
                "returncode_classification",
                "process_hard_timeout_sec",
                "process_hard_timeout_exceeded",
                "process_timeout_provenance",
                "process_timeout_platform",
                "process_timeout_term_grace_sec",
                "process_started_unix",
                "process_pid",
                "process_group_id",
                "process_group_termination_attempted",
                "process_timeout_sigterm_sent",
                "process_timeout_sigkill_sent",
                "process_timeout_reason",
                "process_elapsed_sec",
                "process_returncode",
            ]:
                row[field] = command_row.get(field, "")
        for field in [
            "panel",
            "route",
            "horizon_id",
            "nominal_budget_ms",
            "short_budget_ms",
            "base_time_limit_sec",
            "ltm_max_iterations",
            "fresh_seed_block",
            "theta_cluster",
            "registry_label",
            "candidate_group",
            "fulltheta_registry_row_id",
            "counts_as_g549_calibration_topup",
            "counts_as_g549_fulltheta_replay",
        ]:
            row[field] = plan.get(field, first.get(field, ""))
        row["context_horizon_key"] = "|".join(map(str, key))
        if str(row.get("role", "")).startswith("generated_theta::"):
            if timeout_exceeded:
                row["fulltheta_fingerprint_match"] = False
                row["fulltheta_fingerprint_mismatched_fields"] = "process_hard_timeout_no_updateparams"
            elif not raw_probe:
                row["fulltheta_fingerprint_match"] = True
                row["fulltheta_fingerprint_mismatched_fields"] = ""
            else:
                matched, missing = g547.params_match(row.get("updateparams_fingerprint", ""), row)
                row["fulltheta_fingerprint_match"] = matched
                row["fulltheta_fingerprint_mismatched_fields"] = ";".join(missing)
        else:
            row["fulltheta_fingerprint_match"] = not timeout_exceeded
            row["fulltheta_fingerprint_mismatched_fields"] = "process_hard_timeout_no_updateparams" if timeout_exceeded else ""
    return enriched


def run_context_task(
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
) -> dict[str, Any]:
    first = group_rows[0]
    map_name, agents_count, seed, nominal_budget, horizon_id = key
    methods: list[str] = []
    for row in group_rows:
        method = str(row.get("materialized_method", ""))
        if method and method not in methods:
            methods.append(method)
    task_probe = task_file(temp_dir, index, key, "probe")
    task_checkpoint = task_file(temp_dir, index, key, "checkpoints")
    task_update = task_file(temp_dir, index, key, "updates")
    for path in [task_probe, task_checkpoint, task_update]:
        path.unlink(missing_ok=True)
    alias = f"{manifest_prefix}_{map_name}_a{agents_count}_s{seed}_h{horizon_id}_b{nominal_budget}".replace("-", "_")
    export_checkpoint_jsonl = str(os.environ.get("REPAIR5G_EXPORT_UPDATE_CHECKPOINTS_JSONL", "")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    checkpoint_args = [
        "--repair5g-checkpoint-topk-edges",
        "64",
        "--repair5g-checkpoint-edge-filter",
        "nonzero",
        "--repair5g-checkpoint-include-full-traffic",
        os.environ.get("REPAIR5G_CHECKPOINT_INCLUDE_FULL_TRAFFIC", "false"),
    ]
    if export_checkpoint_jsonl:
        checkpoint_args = [
            "--repair5g-export-update-checkpoints-jsonl",
            str(task_checkpoint),
            *checkpoint_args,
        ]
    spec = MethodSpec(
        STATIC_FLOW,
        alias,
        (
            *checkpoint_args,
            "--repair5g-counterfactual-update-probe-jsonl",
            str(task_probe),
            "--repair5g-counterfactual-candidates",
            ",".join(methods),
            "--repair5g-counterfactual-updateparams-registry",
            str(registry_path),
            "--repair5g-counterfactual-short-budget-ms",
            str(float(number(first.get("short_budget_ms"), nominal_budget))),
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
        time_limit_sec=max(0.01, float(number(first.get("base_time_limit_sec"), 0.50))),
        ltm_max_iterations=max(1, int(number(first.get("ltm_max_iterations"), 2))),
        spec=spec,
        manifest=f"phase5p5-{manifest_prefix}",
        process_hard_timeout_sec=max(
            0.01,
            float(
                number(
                    first.get("process_hard_timeout_sec"),
                    max(
                        float(number(first.get("base_time_limit_sec"), 0.50)) + 0.25,
                        float(number(first.get("base_time_limit_sec"), 0.50)) * 1.10,
                    ),
                )
            ),
        ),
    )
    task_run = log_dir / f"task_{stable_hash('|'.join(map(str, key)), modulo=10**12):012d}.runs.jsonl"
    write_jsonl(task_run, rows)
    skip_aggregate_jsonl = str(os.environ.get("REPAIR5G_SKIP_AGGREGATE_JSONL", "")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
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
        }
    )
    raw_probe = read_jsonl_tolerant(task_probe)
    checkpoint_rows = [] if skip_aggregate_jsonl or not export_checkpoint_jsonl else read_jsonl_tolerant(task_checkpoint)
    enriched = enrich_or_placeholder(
        raw_probe,
        group_rows,
        key,
        row_prefix=row_prefix,
        execution_mode=execution_mode,
        command_row=command_row,
    )
    for path in [task_probe, task_checkpoint, task_update]:
        path.unlink(missing_ok=True)
    return {
        "key": key,
        "run_rows": rows,
        "update_rows": update_rows,
        "command_row": command_row,
        "probe_rows": raw_probe,
        "checkpoint_rows": checkpoint_rows,
        "enriched_rows": enriched,
    }


def write_status(path: str, result_path: str, total: int, completed: int, phase: str, last: dict[str, Any] | None = None) -> None:
    write_json(
        path,
        {
            "schema_version": "phase5p5_repair5g549_run_status_v1",
            "phase": phase,
            "total_context_horizon_tasks": total,
            "completed_context_horizon_tasks": completed,
            "completed_solver_rows": table_count(result_path),
            "last_task": last or {},
        },
    )


def run_probe_plan(
    plan_rows: list[dict[str, Any]],
    *,
    binary: Path,
    overwrite: bool,
    row_limit: int,
    max_workers: int,
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
    groups = probe_context_groups(plan_rows)
    completed = set() if overwrite else completed_groups_from_results(plan_rows, result_csv)
    scheduled = []
    estimated_rows = table_count(result_csv)
    for index, (key, group_rows) in enumerate(groups):
        if row_limit and estimated_rows >= row_limit:
            break
        if key in completed:
            continue
        scheduled.append((index, key, group_rows))
        estimated_rows += len({str(row.get("materialized_method")) for row in group_rows if row.get("materialized_method")})
    maps_in_plan = sorted({key[0] for key, _rows in groups})
    for map_name in maps_in_plan:
        prepare_scenarios(
            root=ROOT,
            source_scenario_dir=resolve(DEFAULT_SOURCE_SCENARIO_DIR),
            scenario_dir=resolve(scenario_dir),
            scenario_metadata=resolve(scenario_metadata),
            maps=[map_name],
            agent_counts=sorted({key[1] for key, _rows in groups if key[0] == map_name}),
            instance_ids=sorted({key[2] for key, _rows in groups if key[0] == map_name}),
        )
    log_root = resolve(log_dir)
    temp_dir = log_root / "_task_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    skip_aggregate_jsonl = str(os.environ.get("REPAIR5G_SKIP_AGGREGATE_JSONL", "")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    stream_result_csv = str(os.environ.get("REPAIR5G_STREAM_RESULT_CSV", "")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    all_results = [] if stream_result_csv else read_rows(result_csv)
    all_runs = [] if skip_aggregate_jsonl else read_jsonl_tolerant(run_jsonl)
    all_commands = [] if skip_aggregate_jsonl else read_jsonl_tolerant(command_jsonl)
    all_updates = [] if skip_aggregate_jsonl else read_jsonl_tolerant(update_jsonl)
    all_probes = [] if skip_aggregate_jsonl else read_jsonl_tolerant(probe_jsonl)
    all_checkpoints = [] if skip_aggregate_jsonl else read_jsonl_tolerant(checkpoint_jsonl)
    done = len(groups) - len(scheduled)
    write_status(status_json, result_csv, len(groups), done, "running")
    pending_flush = 0
    flush_every = 100

    def flush_logs(last: dict[str, Any] | None, phase: str) -> None:
        if not stream_result_csv:
            write_rows_atomic(result_csv, all_results)
        if phase == "solver_complete" and not skip_aggregate_jsonl:
            write_rows_atomic(raw_csv, all_results)
            write_jsonl(run_jsonl, all_runs)
            write_jsonl(command_jsonl, all_commands)
            write_jsonl(update_jsonl, all_updates)
            write_jsonl(probe_jsonl, all_probes)
            write_jsonl(checkpoint_jsonl, all_checkpoints)
        elif phase == "solver_complete" and not stream_result_csv:
            write_rows_atomic(raw_csv, all_results)
        elif phase == "solver_complete":
            resolve(raw_csv).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(resolve(result_csv), resolve(raw_csv))
        write_status(status_json, result_csv, len(groups), done, phase, last or {})

    def merge_result(result: dict[str, Any]) -> None:
        nonlocal all_results, all_runs, all_commands, all_updates, all_probes, all_checkpoints, done, pending_flush
        done += 1
        if stream_result_csv:
            append_rows_to_csv(result_csv, result["enriched_rows"])
        else:
            all_results = append_rows(
                all_results,
                result["enriched_rows"],
                ["context_horizon_key", "materialized_method", "iteration", "traffic_before_hash_full", "probe_materialized"],
            )
        if not skip_aggregate_jsonl:
            all_runs.extend(result["run_rows"])
            all_commands.append(result["command_row"])
            all_updates.extend(result["update_rows"])
            all_probes.extend(result["probe_rows"])
            all_checkpoints.extend(result["checkpoint_rows"])
        pending_flush += 1
        if pending_flush >= flush_every:
            flush_logs(result["command_row"], "running")
            pending_flush = 0

    workers = max(1, int(max_workers))
    if workers == 1:
        for index, key, group_rows in scheduled:
            merge_result(
                run_context_task(
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
            )
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            scheduled_iter = iter(scheduled)
            futures = set()
            max_in_flight = max(workers, workers * 2)

            def submit_next() -> bool:
                try:
                    index, key, group_rows = next(scheduled_iter)
                except StopIteration:
                    return False
                futures.add(
                    pool.submit(
                        run_context_task,
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
                )
                return True

            for _ in range(min(max_in_flight, len(scheduled))):
                submit_next()

            while futures:
                done_futures, futures = wait(futures, return_when=FIRST_COMPLETED)
                for future in done_futures:
                    merge_result(future.result())
                    submit_next()
    flush_logs(None, "solver_complete")
    return all_results


def main_verify_g548_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.49 verify G5.48 artifacts")
    required = {
        "g548_decision_summary": g548.DECISION_SUMMARY,
        "g548_budget_calibration_summary": g548.CALIBRATION_SUMMARY,
        "g548_budget_calibration_results": g548.CALIBRATION_RESULTS_CSV,
        "g548_budget_horizon_selection": g548.CALIBRATION_SELECTION_CSV,
        "g548_fulltheta_registry": g547.FULLTHETA_REGISTRY_CSV,
        "g548_common": "scripts/repair5g548_common.py",
    }
    audit = []
    for label, path in required.items():
        p = resolve(path)
        audit.append({"artifact": label, "path": str(p), "exists": p.exists(), "rows_or_file": table_count(path), **claims()})
    write_rows(VERIFY_AUDIT_CSV, audit)
    decision = load_json(g548.DECISION_SUMMARY, {})
    calibration = load_json(g548.CALIBRATION_SUMMARY, {})
    checks = {
        "decision_underpowered_continue": decision.get("decision") == "g548_budget_calibration_underpowered_continue_calibration",
        "fulltheta_fingerprint_match_rate_is_1": str(calibration.get("fulltheta_fingerprint_match_rate", "")) in {"1", "1.0"},
        "budget_calibration_solver_rows_ge_3000": int(number(calibration.get("budget_calibration_solver_rows"), 0)) >= 3000,
        "finite_ratio_rows_is_1604": int(number(calibration.get("finite_ratio_rows"), 0)) == 1604,
        "both_success_quality_pairs_vs_static_flow_is_283": int(number(calibration.get("both_success_quality_pairs_vs_static_flow"), 0)) == 283,
    }
    ok = all(boolish(row["exists"]) for row in audit) and all(checks.values())
    summary = {
        "schema_version": "phase5p5_repair5g549_g548_verification_summary_v1",
        "decision": "g548_verified_for_g549" if ok else "g549_g548_verification_blocked",
        "missing_artifacts": [row["artifact"] for row in audit if not boolish(row["exists"])],
        "checks": checks,
        "g548_decision": decision.get("decision", ""),
        "budget_calibration_solver_rows": calibration.get("budget_calibration_solver_rows", 0),
        "finite_ratio_rows": calibration.get("finite_ratio_rows", 0),
        "both_success_quality_pairs_vs_static_flow": calibration.get("both_success_quality_pairs_vs_static_flow", 0),
        "fulltheta_fingerprint_match_rate": calibration.get("fulltheta_fingerprint_match_rate", ""),
        "external_lacam2_clean": external_lacam2_clean(),
        **claims(),
    }
    write_json(VERIFY_SUMMARY, summary)
    write_text(
        VERIFY_REPORT,
        "# G5.49 Verification of G5.48 Artifacts\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- G5.48 decision: `{summary['g548_decision']}`\n"
        f"- solver rows: `{summary['budget_calibration_solver_rows']}`\n"
        f"- finite ratio rows: `{summary['finite_ratio_rows']}`\n"
        f"- both-success pairs vs static_flow: `{summary['both_success_quality_pairs_vs_static_flow']}`\n"
        f"- fulltheta fingerprint match rate: `{summary['fulltheta_fingerprint_match_rate']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "missing": len(summary["missing_artifacts"])}))
    return 0 if ok else 2


def main_audit_g548_calibration_semantics(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.49 audit G5.48 calibration semantics")
    if not resolve(VERIFY_SUMMARY).exists():
        main_verify_g548_artifacts([])
    selected = read_rows(g548.CALIBRATION_SELECTION_CSV)
    non_eval_source = read_rows(g548.NON_EVALUABLE_STRATA_CSV)
    selected_rows = []
    for row in selected:
        selected_rows.append(
            {
                "map_family": row.get("map_family", ""),
                "agents": row.get("agents", ""),
                "nominal_budget_ms": row.get("nominal_budget_ms", ""),
                "horizon_id": row.get("horizon_id", ""),
                "short_budget_ms": row.get("short_budget_ms", ""),
                "selected_evaluable_horizon_row": True,
                "unique_stratum_key": f"{row.get('map_family')}|{row.get('agents')}|{row.get('nominal_budget_ms')}",
                **claims(),
            }
        )
    unique_keys = sorted({(row.get("map_family", ""), row.get("agents", ""), row.get("nominal_budget_ms", "")) for row in selected})
    unique_rows = [
        {"map_family": fam, "agents": agents, "nominal_budget_ms": budget, "unique_evaluable_stratum": True, **claims()}
        for fam, agents, budget in unique_keys
    ]
    non_eval_rows = []
    for row in non_eval_source:
        non_eval_rows.append(
            {
                "map_family": row.get("map_family", ""),
                "agents": row.get("agents", ""),
                "nominal_budget_ms": row.get("nominal_budget_ms", ""),
                "reason": row.get("reason", ""),
                "best_horizon_id": row.get("best_horizon_id", ""),
                "warehouse_non_evaluable": row.get("map_family", "") == "warehouse",
                **claims(),
            }
        )
    write_rows(SELECTED_HORIZON_AUDIT_CSV, selected_rows)
    write_rows(UNIQUE_EVALUABLE_STRATA_CSV, unique_rows)
    write_rows(NON_EVALUABLE_STRATA_AUDIT_CSV, non_eval_rows)
    coverage = {
        "map_families": sorted({row.get("map_family", "") for row in selected if row.get("map_family", "")}),
        "agents": sorted({str(row.get("agents", "")) for row in selected if row.get("agents", "")}),
        "nominal_budgets": sorted({str(row.get("nominal_budget_ms", "")) for row in selected if row.get("nominal_budget_ms", "")}),
        "warehouse_entirely_non_evaluable": "warehouse" not in {row.get("map_family", "") for row in selected},
    }
    summary = {
        "schema_version": "phase5p5_repair5g549_g548_calibration_semantics_summary_v1",
        "decision": "g548_calibration_semantics_audited_for_g549",
        "selected_evaluable_horizon_rows": len(selected_rows),
        "unique_evaluable_stratum_count": len(unique_rows),
        "coverage": coverage,
        "do_not_overcount_horizon_rows_as_unique_strata": True,
        **claims(),
    }
    write_json(SEMANTICS_SUMMARY, summary)
    write_text(
        SEMANTICS_REPORT,
        "# G5.49 Audit of G5.48 Calibration Semantics\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- selected evaluable horizon rows: `{summary['selected_evaluable_horizon_rows']}`\n"
        f"- unique evaluable strata: `{summary['unique_evaluable_stratum_count']}`\n"
        f"- evaluable families: `{', '.join(coverage['map_families'])}`\n"
        f"- warehouse entirely non-evaluable: `{coverage['warehouse_entirely_non_evaluable']}`\n\n"
        "G5.49 treats selected horizon rows and unique strata as separate metrics. "
        "A horizon-row count cannot silently satisfy a unique-stratum gate.\n",
    )
    print(json.dumps({"decision": summary["decision"], "unique_strata": len(unique_rows), "horizon_rows": len(selected_rows)}))
    return 0


def main_create_calibration_topup_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.49 calibration topup plan")
    if not resolve(SEMANTICS_SUMMARY).exists():
        main_audit_g548_calibration_semantics([])
    write_calibration_topup_plan(args.max_contexts)
    return 0


def main_run_calibration_topup(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.49 calibration topup")
    if not resolve(TOPUP_PLAN_CSV).exists() or args.overwrite:
        write_calibration_topup_plan(args.max_contexts)
    binary = binary_path(args.binary)
    if not binary.exists():
        summary = {"schema_version": "phase5p5_repair5g549_calibration_topup_summary_v1", "decision": "g549_calibration_topup_solver_blocked_missing_binary", "blocker": str(binary), **claims()}
        write_json(CALIBRATION_SUMMARY, summary)
        print(json.dumps(summary))
        return 2
    rows = run_probe_plan(
        read_rows(TOPUP_PLAN_CSV),
        binary=binary,
        overwrite=args.overwrite,
        row_limit=max(0, args.row_limit),
        max_workers=args.max_workers,
        registry_path=FULLTHETA_REGISTRY_CSV,
        result_csv=TOPUP_RESULTS_CSV,
        raw_csv=TOPUP_RESULTS_RAW_CSV,
        log_dir=TOPUP_LOG_DIR,
        run_jsonl=TOPUP_RUN_JSONL,
        command_jsonl=TOPUP_COMMAND_JSONL,
        update_jsonl=TOPUP_UPDATE_JSONL,
        probe_jsonl=TOPUP_PROBE_JSONL,
        checkpoint_jsonl=TOPUP_CHECKPOINT_JSONL,
        status_json=TOPUP_STATUS_JSON,
        scenario_dir=TOPUP_SCENARIO_DIR,
        scenario_metadata=TOPUP_SCENARIO_METADATA,
        manifest_prefix="g549_calibration_topup",
        row_prefix="g549_topup_probe",
        execution_mode="new_g549_calibration_topup_solver_row",
    )
    print(json.dumps({"decision": "g549_calibration_topup_executed", "rows": len(rows)}))
    return 0


def result_pairs(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    vs_static, vs_family, vs_additive, failures = g546.pairwise_tables(rows)
    by_selected = {
        (str(row.get("context_key", "")), str(row.get("candidate_id", ""))): row
        for row in rows
        if str(row.get("role", "")).startswith("generated_theta::")
    }
    for table in [vs_static, vs_family, vs_additive, failures]:
        for pair in table:
            source = by_selected.get((str(pair.get("context_key", "")), str(pair.get("selected_candidate", ""))), {})
            for field in [
                "horizon_id",
                "nominal_budget_ms",
                "short_budget_ms",
                "base_time_limit_sec",
                "ltm_max_iterations",
                "context_horizon_key",
                "panel",
                "route",
                "theta_cluster",
                "registry_label",
                "candidate_group",
            ]:
                pair[field] = source.get(field, "")
            for col in THETA_COLUMNS:
                pair[col] = source.get(col, "")
    return vs_static, vs_family, vs_additive, failures


def pair_support_by_group(pair_rows: list[dict[str, Any]], group_fields: list[str]) -> dict[tuple[Any, ...], dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in pair_rows:
        grouped[tuple(row.get(field, "") for field in group_fields)].append(row)
    out: dict[tuple[Any, ...], dict[str, Any]] = {}
    for key, group in grouped.items():
        deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in group if str(row.get("quality_delta_ratio", "")).strip()]
        out[key] = {
            "pair_rows": len(group),
            "both_success_quality_pairs_vs_static_flow": sum(1 for row in group if boolish(row.get("both_success"))),
            "success_regression_count": sum(1 for row in group if boolish(row.get("success_regression"))),
            "success_gain_count": sum(1 for row in group if boolish(row.get("success_gain"))),
            "better_count": sum(1 for row in group if boolish(row.get("better"))),
            "worse_count": sum(1 for row in group if boolish(row.get("worse"))),
            "quality_delta_mean": "" if not deltas else csv_number(statistics.mean(deltas)),
            "seed_block_support": len({row.get("seed_block", "") for row in group}),
        }
    return out


def analyze_calibration_rows(cumulative_rows: list[dict[str, Any]], topup_rows: list[dict[str, Any]]) -> dict[str, Any]:
    primary = [row for row in cumulative_rows if boolish(row.get("counts_as_g549_calibration_topup")) or boolish(row.get("counts_as_primary_calibration"))]
    generated = [row for row in primary if str(row.get("role", "")).startswith("generated_theta::")]
    static_rows = [row for row in primary if row.get("role") == "static_flow_shield"]
    finite_rows = [row for row in primary if g546.ratio(row) is not None]
    context_horizons = {row.get("context_horizon_key") for row in primary}
    vs_static, _vs_family, _vs_additive, _failures = result_pairs(primary)
    pair_by_stratum_horizon = pair_support_by_group(vs_static, ["map_family", "agents", "nominal_budget_ms", "horizon_id"])
    rows_by_stratum_horizon: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    static_by_stratum_horizon: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in primary:
        key = (row.get("map_family"), row.get("agents"), row.get("nominal_budget_ms"), row.get("horizon_id"))
        rows_by_stratum_horizon[key].append(row)
        if row.get("role") == "static_flow_shield":
            static_by_stratum_horizon[key].append(row)
    selected: list[dict[str, Any]] = []
    by_stratum_rows: list[dict[str, Any]] = []
    for key, group in sorted(rows_by_stratum_horizon.items()):
        fam, agents, budget, horizon_id = key
        static_group = static_by_stratum_horizon.get(key, [])
        pair = pair_by_stratum_horizon.get((fam, agents, budget, horizon_id), {})
        finite_count = sum(1 for row in group if g546.ratio(row) is not None)
        static_success_rate = sum(1 for row in static_group if g546.success(row)) / max(1, len(static_group))
        finite_ratio_rate = finite_count / max(1, len(group))
        both_success = int(number(pair.get("both_success_quality_pairs_vs_static_flow"), 0))
        row = {
            "map_family": fam,
            "agents": agents,
            "nominal_budget_ms": budget,
            "horizon_id": horizon_id,
            "short_budget_ms": next((r.get("short_budget_ms") for r in group), ""),
            "base_time_limit_sec": next((r.get("base_time_limit_sec") for r in group), ""),
            "ltm_max_iterations": next((r.get("ltm_max_iterations") for r in group), ""),
            "solver_rows_materialized": len(group),
            "finite_ratio_rows": finite_count,
            "finite_ratio_rate": csv_number(finite_ratio_rate),
            "static_flow_rows": len(static_group),
            "static_flow_success_rate": csv_number(static_success_rate),
            "both_success_quality_pairs_vs_static_flow": both_success,
            "candidate_recognized_all": bool(group) and all(boolish(r.get("candidate_recognized")) for r in group),
            "fulltheta_fingerprint_match_rate": csv_number(
                sum(1 for r in group if str(r.get("role", "")).startswith("generated_theta::") and boolish(r.get("probe_materialized")) and boolish(r.get("fulltheta_fingerprint_match")))
                / max(1, sum(1 for r in group if str(r.get("role", "")).startswith("generated_theta::") and boolish(r.get("probe_materialized"))))
            ),
            **claims(),
        }
        evaluable = static_success_rate >= 0.20 and finite_ratio_rate >= 0.20 and both_success >= 20 and boolish(row["candidate_recognized_all"])
        row["evaluable"] = evaluable
        row["selection_reason"] = "static_flow_success_rate>=0.20 and finite_ratio_rate>=0.20 and both_success_pairs>=20" if evaluable else ""
        by_stratum_rows.append(row)
        if evaluable:
            selected.append(row.copy())
    strata_keys = {(row.get("map_family"), row.get("agents"), row.get("nominal_budget_ms")) for row in primary}
    selected_strata = {(row["map_family"], row["agents"], row["nominal_budget_ms"]) for row in selected}
    non_eval = []
    for fam, agents, budget in sorted(strata_keys):
        candidates = [row for row in by_stratum_rows if row["map_family"] == fam and row["agents"] == agents and row["nominal_budget_ms"] == budget]
        best = max(candidates, key=lambda row: (number(row.get("finite_ratio_rate"), 0.0), number(row.get("static_flow_success_rate"), 0.0))) if candidates else {}
        if (fam, agents, budget) not in selected_strata:
            non_eval.append(
                {
                    "map_family": fam,
                    "agents": agents,
                    "nominal_budget_ms": budget,
                    "reason": "no horizon met static_flow_success_rate>=0.20, finite_ratio_rate>=0.20, both_success_quality_pairs_vs_static_flow>=20",
                    "best_horizon_id": best.get("horizon_id", ""),
                    "best_finite_ratio_rate": best.get("finite_ratio_rate", "0"),
                    "best_static_flow_success_rate": best.get("static_flow_success_rate", "0"),
                    "best_both_success_quality_pairs_vs_static_flow": best.get("both_success_quality_pairs_vs_static_flow", 0),
                    "warehouse_non_evaluable_on_local_budget": fam == "warehouse",
                    **claims(),
                }
            )
    write_rows(CALIBRATION_SELECTED_HORIZONS_CSV, selected)
    write_rows(CALIBRATION_NON_EVALUABLE_CSV, non_eval)
    by_map = []
    for fam, group in sorted(defaultdict(list, ((row.get("map_family"), []) for row in primary)).items()):
        del group
    map_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    budget_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in primary:
        map_groups[str(row.get("map_family", ""))].append(row)
        budget_groups[str(row.get("nominal_budget_ms", row.get("budget_ms", "")))].append(row)
    for fam, group in sorted(map_groups.items()):
        by_map.append({"map_family": fam, "solver_rows": len(group), "finite_ratio_rows": sum(1 for row in group if g546.ratio(row) is not None), **claims()})
    by_budget = []
    for budget, group in sorted(budget_groups.items(), key=lambda item: number(item[0], 0)):
        by_budget.append({"nominal_budget_ms": budget, "solver_rows": len(group), "finite_ratio_rows": sum(1 for row in group if g546.ratio(row) is not None), **claims()})
    write_rows(CALIBRATION_BY_MAP_CSV, by_map)
    write_rows(CALIBRATION_BY_BUDGET_CSV, by_budget)
    new_rows = len(topup_rows)
    finite_rate = len(finite_rows) / max(1, len(primary))
    both_success_total = sum(1 for row in vs_static if boolish(row.get("both_success")))
    match_gen = [row for row in generated if boolish(row.get("probe_materialized")) and row.get("fulltheta_fingerprint_match") != ""]
    match_rate = sum(1 for row in match_gen if boolish(row.get("fulltheta_fingerprint_match"))) / max(1, len(match_gen))
    unique_count = len(selected_strata)
    hard_gate = (
        new_rows >= 8000
        and len(finite_rows) >= 3000
        and finite_rate >= 0.20
        and both_success_total >= 1000
        and bool(primary)
        and all(boolish(row.get("candidate_recognized")) for row in primary)
        and match_rate >= 1.0
        and unique_count >= 4
    )
    if new_rows < 8000 or len(finite_rows) < 3000:
        decision = "g549_calibration_topup_underpowered_continue"
    elif hard_gate and unique_count < 9:
        decision = "g549_calibration_evaluable_core_ready_fulltheta_replay_development_only"
    elif hard_gate:
        decision = "g549_calibration_evaluable_core_ready_fulltheta_replay"
    else:
        decision = "g549_calibration_topup_underpowered_continue"
    return {
        "schema_version": "phase5p5_repair5g549_calibration_topup_summary_v1",
        "decision": decision,
        "new_calibration_solver_rows": new_rows,
        "cumulative_calibration_solver_rows": len(primary),
        "cumulative_context_horizons": len(context_horizons),
        "baseline_static_flow_rows": len(static_rows),
        "selected_evaluable_horizon_rows": len(selected),
        "unique_evaluable_stratum_count": unique_count,
        "cumulative_finite_ratio_rows": len(finite_rows),
        "cumulative_finite_ratio_rate": csv_number(finite_rate),
        "cumulative_both_success_quality_pairs_vs_static_flow": both_success_total,
        "candidate_recognized_all": bool(primary) and all(boolish(row.get("candidate_recognized")) for row in primary),
        "fulltheta_fingerprint_match_rate": csv_number(match_rate),
        "warehouse_non_evaluable_on_local_budget": "warehouse" not in {row["map_family"] for row in selected},
        "calibrated_core_subset_label": "calibrated_core_subset_development_only" if unique_count < 9 else "",
        "hard_gate_new_calibration_solver_rows_met": new_rows >= 8000,
        "hard_gate_cumulative_finite_ratio_rows_met": len(finite_rows) >= 3000,
        "hard_gate_cumulative_finite_ratio_rate_met": finite_rate >= 0.20,
        "hard_gate_cumulative_both_success_pairs_met": both_success_total >= 1000,
        "hard_gate_unique_evaluable_stratum_count_met": unique_count >= 4,
        "primary_baseline": "static_flow_shield",
        **claims(),
    }


def main_analyze_calibration_topup(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.49 calibration topup analysis")
    if not resolve(TOPUP_RESULTS_CSV).exists():
        rc = main_run_calibration_topup([])
        if rc != 0:
            return rc
    g548_rows = read_rows(g548.CALIBRATION_RESULTS_CSV)
    topup_rows = read_rows(TOPUP_RESULTS_CSV)
    summary = analyze_calibration_rows(g548_rows + topup_rows, topup_rows)
    write_json(CALIBRATION_SUMMARY, summary)
    write_text(
        CALIBRATION_REPORT,
        "# G5.49 Calibration Top-Up\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- new calibration solver rows: `{summary['new_calibration_solver_rows']}`\n"
        f"- cumulative finite ratio rows: `{summary['cumulative_finite_ratio_rows']}`\n"
        f"- cumulative finite ratio rate: `{summary['cumulative_finite_ratio_rate']}`\n"
        f"- both-success pairs vs static_flow: `{summary['cumulative_both_success_quality_pairs_vs_static_flow']}`\n"
        f"- selected evaluable horizon rows: `{summary['selected_evaluable_horizon_rows']}`\n"
        f"- unique evaluable strata: `{summary['unique_evaluable_stratum_count']}`\n"
        f"- warehouse non-evaluable locally: `{summary['warehouse_non_evaluable_on_local_budget']}`\n\n"
        "This stage completes the local evaluability gate for calibrated core strata only. "
        "Unique stratum count remains separate from selected horizon rows.\n",
    )
    print(json.dumps({"decision": summary["decision"], "new_rows": summary["new_calibration_solver_rows"]}))
    return 0


def calibration_gate_passed() -> bool:
    summary = load_json(CALIBRATION_SUMMARY, {})
    return str(summary.get("decision", "")).startswith("g549_calibration_evaluable_core_ready_fulltheta_replay")


def theta_value(label: str, field: str, lo: float, hi: float) -> float:
    unit = stable_hash(label, field, modulo=1_000_003) / 1_000_002.0
    return lo + unit * (hi - lo)


def patch_goal_mode(theta: dict[str, Any], mode: str) -> None:
    theta["theta_goal_projection_mode_flow_shield"] = 1 if mode == "flow_shield" else 0
    theta["theta_goal_projection_mode_agent_progress"] = 1 if mode == "agent_progress" else 0
    theta["theta_goal_projection_mode_none"] = 1 if mode == "none" else 0


def fulltheta_registry_rows(count: int = FULLTHETA_REGISTRY_SIZE) -> list[dict[str, Any]]:
    base = g547.clamp_theta(g545.static_flow_theta())
    policies = [
        "static_flow_local_perturbation_fulltheta",
        "lambda_flow_lambda_cong_sweep",
        "alpha_flow_wait_progress_sweep",
        "edge_cost_clamp_sweep",
        "goal_projection_mode_ablation",
        "alpha_cong_commit_nonprogress_sweep",
        "g543_true_near_signal_neighborhood",
        "g546_g548_safe_no_gain_neighborhood",
        "surrogate_guided_theta_if_model_exists",
        "negative_control",
    ]
    rows: list[dict[str, Any]] = []
    for idx in range(count):
        policy = policies[idx % len(policies)]
        theta = dict(base)
        label = f"{policy}_{idx:04d}"
        if policy == "static_flow_local_perturbation_fulltheta":
            for field in ["theta_lambda_flow", "theta_lambda_cong", "theta_alpha_flow_wait_progress"]:
                theta[field] = theta_value(label, field, 0.70, 1.30)
        elif policy == "lambda_flow_lambda_cong_sweep":
            theta["theta_lambda_flow"] = theta_value(label, "theta_lambda_flow", 0.0, 1.5)
            theta["theta_lambda_cong"] = theta_value(label, "theta_lambda_cong", 0.5, 1.5)
        elif policy == "alpha_flow_wait_progress_sweep":
            theta["theta_alpha_flow_wait_progress"] = theta_value(label, "theta_alpha_flow_wait_progress", 0.0, 1.25)
            theta["theta_lambda_flow"] = theta_value(label, "theta_lambda_flow", 0.0, 1.5)
        elif policy == "edge_cost_clamp_sweep":
            theta["theta_min_edge_cost"] = theta_value(label, "theta_min_edge_cost", 0.25, 1.0)
            theta["theta_max_edge_cost"] = theta_value(label, "theta_max_edge_cost", 8.0, 12.0)
        elif policy == "goal_projection_mode_ablation":
            patch_goal_mode(theta, ["flow_shield", "agent_progress", "none"][idx % 3])
            theta["theta_lambda_flow"] = theta_value(label, "theta_lambda_flow", 0.0, 1.5)
        elif policy == "alpha_cong_commit_nonprogress_sweep":
            theta["theta_alpha_cong_commit_nonprogress"] = theta_value(label, "theta_alpha_cong_commit_nonprogress", 0.5, 1.75)
            theta["theta_lambda_cong"] = theta_value(label, "theta_lambda_cong", 0.5, 1.5)
        elif policy == "g543_true_near_signal_neighborhood":
            theta["theta_flow_shield_beta"] = theta_value(label, "theta_flow_shield_beta", 0.20, 0.70)
            theta["theta_max_flow_shield"] = theta_value(label, "theta_max_flow_shield", 0.50, 1.25)
            theta["theta_lambda_flow"] = theta_value(label, "theta_lambda_flow", 0.10, 0.90)
        elif policy == "g546_g548_safe_no_gain_neighborhood":
            theta["theta_lambda_cong"] = theta_value(label, "theta_lambda_cong", 0.75, 1.40)
            theta["theta_alpha_flow_wait_progress"] = theta_value(label, "theta_alpha_flow_wait_progress", 0.20, 1.10)
            theta["theta_min_edge_cost"] = theta_value(label, "theta_min_edge_cost", 0.25, 0.80)
        elif policy == "surrogate_guided_theta_if_model_exists":
            theta["theta_lambda_flow"] = theta_value(label, "theta_lambda_flow", 0.15, 1.35)
            theta["theta_lambda_cong"] = theta_value(label, "theta_lambda_cong", 0.65, 1.45)
            theta["theta_alpha_cong_commit_nonprogress"] = theta_value(label, "theta_alpha_cong_commit_nonprogress", 0.65, 1.50)
            patch_goal_mode(theta, ["flow_shield", "agent_progress"][idx % 2])
        else:
            theta["theta_lambda_flow"] = theta_value(label, "theta_lambda_flow", 0.0, 1.5)
            theta["theta_lambda_cong"] = theta_value(label, "theta_lambda_cong", 0.5, 1.5)
            theta["theta_max_edge_cost"] = theta_value(label, "theta_max_edge_cost", 8.0, 12.0)
            patch_goal_mode(theta, "none" if idx % 2 else "agent_progress")
        theta = g547.clamp_theta(theta)
        full_only_varied = any(str(theta.get(field, "")) != str(base.get(field, "")) for field in FULL_ONLY_FIELDS)
        rows.append(
            {
                "registry_row_id": f"g549_registry_{idx + 1:06d}",
                "candidate_id": f"repair5g549_theta_{549000000 + idx + 1}",
                "registry_label": label,
                "candidate_group": policy,
                "theta_cluster": policy,
                "changed_field_for_smoke_pair": policy,
                "materialization_family": "repair5g549_fulltheta_registry",
                "bounded_updateparams": True,
                "full_only_field_varied": full_only_varied,
                **theta,
                **claims(),
            }
        )
    return rows


def ensure_fulltheta_registry() -> list[dict[str, Any]]:
    if resolve(FULLTHETA_REGISTRY_CSV).exists():
        return read_rows(FULLTHETA_REGISTRY_CSV)
    rows = fulltheta_registry_rows()
    write_rows(FULLTHETA_REGISTRY_CSV, rows)
    full_only_rate = sum(1 for row in rows if boolish(row.get("full_only_field_varied"))) / max(1, len(rows))
    summary = {
        "schema_version": "phase5p5_repair5g549_fulltheta_registry_summary_v1",
        "decision": "g549_fulltheta_registry_created",
        "registry_rows": len(rows),
        "distinct_fulltheta_rows": len({tuple(row.get(col, "") for col in THETA_COLUMNS) for row in rows}),
        "full_only_field_varied_rate": csv_number(full_only_rate),
        "reserved_ids_166_205_used": False,
        **claims(),
    }
    write_json(FULLTHETA_REGISTRY_SUMMARY, summary)
    write_text(
        FULLTHETA_REGISTRY_REPORT,
        "# G5.49 Fulltheta Registry\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- registry rows: `{summary['registry_rows']}`\n"
        f"- distinct fulltheta rows: `{summary['distinct_fulltheta_rows']}`\n"
        f"- full-only field varied rate: `{summary['full_only_field_varied_rate']}`\n",
    )
    return rows


def write_fulltheta_skip(reason: str) -> None:
    for path in [
        FULLTHETA_PLAN_CSV,
        FULLTHETA_POLICY_BREAKDOWN_CSV,
        FULLTHETA_RESULTS_CSV,
        FULLTHETA_RESULTS_RAW_CSV,
        FULLTHETA_VS_STATIC_CSV,
        FULLTHETA_VS_ADDITIVE_CSV,
        FULLTHETA_VS_FAMILY_CSV,
        FULLTHETA_TRUE_GAIN_CSV,
        FULLTHETA_SAFE_NO_GAIN_CSV,
        FULLTHETA_UNSAFE_USEFUL_CSV,
        FULLTHETA_NON_EVALUABLE_CSV,
        FULLTHETA_PARAM_SENSITIVITY_CSV,
        FULLTHETA_FAILURE_CASES_CSV,
    ]:
        write_skip_table(path, reason)
    summary = {
        "schema_version": "phase5p5_repair5g549_fulltheta_replay_summary_v1",
        "decision": "g549_fulltheta_replay_skipped_calibration_gate_not_met",
        "reason": reason,
        "new_fulltheta_solver_rows": 0,
        "finite_ratio_rows": 0,
        "both_success_quality_pairs_vs_static_flow": 0,
        "candidate_recognized_all": False,
        "fulltheta_fingerprint_match_rate": "0",
        **claims(),
    }
    write_json(FULLTHETA_SUMMARY, summary)
    write_text(FULLTHETA_REPORT, f"# G5.49 Fulltheta Replay\n\n- decision: `{summary['decision']}`\n- reason: {reason}\n")


def main_create_fulltheta_replay_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.49 fulltheta replay plan")
    if not resolve(CALIBRATION_SUMMARY).exists():
        main_analyze_calibration_topup([])
    if not calibration_gate_passed():
        write_fulltheta_skip("calibration top-up did not satisfy the G5.49 calibrated-core gate")
        print(json.dumps({"decision": "g549_fulltheta_replay_plan_skipped_calibration_gate_not_met"}))
        return 0
    selected = read_rows(CALIBRATION_SELECTED_HORIZONS_CSV)
    selected = [row for row in selected if row.get("map_family") in {"maze", "random"} and str(row.get("nominal_budget_ms")) == "2000"][:12]
    if not selected:
        selected = read_rows(CALIBRATION_SELECTED_HORIZONS_CSV)[:12]
    registry = ensure_fulltheta_registry()
    rows: list[dict[str, Any]] = []
    context_index = 0
    for sel in selected:
        for seed in FULLTHETA_SEEDS:
            context = {
                "panel": "fulltheta_replay",
                "route": "staticflow_primary_fulltheta_replay",
                "context_id": f"{sel['map_family']}|a{sel['agents']}|s{seed}|b{sel['nominal_budget_ms']}|{sel['horizon_id']}",
                "map": map_for_family(str(sel["map_family"])),
                "map_family": sel["map_family"],
                "agents": int(number(sel["agents"], 0)),
                "seed": seed,
                "budget_ms": int(number(sel["nominal_budget_ms"], 0)),
                "nominal_budget_ms": int(number(sel["nominal_budget_ms"], 0)),
                "horizon_id": sel["horizon_id"],
                "short_budget_ms": sel["short_budget_ms"],
                "base_time_limit_sec": sel["base_time_limit_sec"],
                "ltm_max_iterations": sel["ltm_max_iterations"],
                "fresh_seed_block": seed_block(seed),
                "source": "g549_calibrated_selected_horizon_v2",
            }
            prefix = f"g549_fulltheta_{len(rows):08d}"
            rows.extend(baseline_plan_rows(context, prefix))
            start = (context_index * FULLTHETA_CANDIDATES_PER_CONTEXT) % len(registry)
            for offset in range(FULLTHETA_CANDIDATES_PER_CONTEXT):
                reg = registry[(start + offset) % len(registry)]
                rows.append(
                    {
                        "plan_row_id": f"g549_fulltheta_{len(rows):08d}",
                        **context,
                        "role": f"generated_theta::{reg['candidate_id']}",
                        "candidate_id": reg["candidate_id"],
                        "materialized_method": reg["candidate_id"],
                        "sampling_policy": str(reg.get("candidate_group", reg.get("theta_cluster", ""))),
                        "theta_cluster": reg.get("theta_cluster", ""),
                        "candidate_group": reg.get("candidate_group", ""),
                        "registry_label": reg.get("registry_label", ""),
                        "fulltheta_registry_row_id": reg.get("registry_row_id", ""),
                        "counts_as_g549_calibration_topup": False,
                        "counts_as_g549_fulltheta_replay": True,
                        **{col: reg.get(col, "") for col in THETA_COLUMNS},
                        **claims(),
                    }
                )
            context_index += 1
    for idx, row in enumerate(rows):
        row["plan_row_id"] = f"g549_fulltheta_{idx:08d}"
    write_rows(FULLTHETA_PLAN_CSV, rows)
    breakdown = []
    grouped = Counter(row.get("sampling_policy", "") for row in rows if str(row.get("role", "")).startswith("generated_theta::"))
    for policy, count in sorted(grouped.items()):
        breakdown.append({"sampling_policy": policy, "planned_rows": count, **claims()})
    write_rows(FULLTHETA_POLICY_BREAKDOWN_CSV, breakdown)
    contexts = {row.get("context_id") for row in rows}
    generated = [row for row in rows if str(row.get("role", "")).startswith("generated_theta::")]
    full_only_rate = sum(1 for row in generated if any(str(row.get(field, "")) != str(g547.clamp_theta(g545.static_flow_theta()).get(field, "")) for field in FULL_ONLY_FIELDS)) / max(1, len(generated))
    summary = {
        "schema_version": "phase5p5_repair5g549_fulltheta_replay_plan_summary_v1",
        "decision": "g549_fulltheta_replay_plan_created",
        "planned_solver_rows": len(rows),
        "planned_fulltheta_candidate_rows": len(generated),
        "planned_baseline_rows": len(rows) - len(generated),
        "planned_contexts": len(contexts),
        "distinct_fulltheta_rows": len({tuple(row.get(col, "") for col in THETA_COLUMNS) for row in generated}),
        "full_only_field_variation_rate": csv_number(full_only_rate),
        "minimum_plan_gate_passed": len(rows) >= 30000 and len(generated) >= 24000 and len(rows) - len(generated) >= 4000 and len(contexts) >= 720,
        **claims(),
    }
    write_json(FULLTHETA_PLAN_SUMMARY, summary)
    write_text(
        FULLTHETA_PLAN_REPORT,
        "# G5.49 StaticFlow-Primary Fulltheta Replay Plan\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- planned solver rows: `{summary['planned_solver_rows']}`\n"
        f"- planned fulltheta candidate rows: `{summary['planned_fulltheta_candidate_rows']}`\n"
        f"- planned baseline rows: `{summary['planned_baseline_rows']}`\n"
        f"- planned contexts: `{summary['planned_contexts']}`\n"
        f"- distinct fulltheta rows: `{summary['distinct_fulltheta_rows']}`\n"
        f"- full-only field variation rate: `{summary['full_only_field_variation_rate']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "contexts": len(contexts)}))
    return 0


def main_run_fulltheta_replay(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.49 fulltheta replay")
    if not resolve(FULLTHETA_PLAN_CSV).exists() or args.overwrite:
        main_create_fulltheta_replay_plan([])
    if not calibration_gate_passed():
        write_fulltheta_skip("calibration top-up did not satisfy the G5.49 calibrated-core gate")
        print(json.dumps({"decision": "g549_fulltheta_replay_skipped_calibration_gate_not_met"}))
        return 0
    binary = binary_path(args.binary)
    if not binary.exists():
        write_fulltheta_skip(f"missing binary {binary}")
        print(json.dumps({"decision": "g549_fulltheta_replay_solver_blocked_missing_binary", "binary": str(binary)}))
        return 2
    rows = run_probe_plan(
        read_rows(FULLTHETA_PLAN_CSV),
        binary=binary,
        overwrite=args.overwrite,
        row_limit=max(0, args.row_limit),
        max_workers=args.max_workers,
        registry_path=FULLTHETA_REGISTRY_CSV,
        result_csv=FULLTHETA_RESULTS_CSV,
        raw_csv=FULLTHETA_RESULTS_RAW_CSV,
        log_dir=FULLTHETA_LOG_DIR,
        run_jsonl=FULLTHETA_RUN_JSONL,
        command_jsonl=FULLTHETA_COMMAND_JSONL,
        update_jsonl=FULLTHETA_UPDATE_JSONL,
        probe_jsonl=FULLTHETA_PROBE_JSONL,
        checkpoint_jsonl=FULLTHETA_CHECKPOINT_JSONL,
        status_json=FULLTHETA_STATUS_JSON,
        scenario_dir=FULLTHETA_SCENARIO_DIR,
        scenario_metadata=FULLTHETA_SCENARIO_METADATA,
        manifest_prefix="g549_fulltheta_replay",
        row_prefix="g549_fulltheta_probe",
        execution_mode="new_g549_staticflow_primary_fulltheta_replay_solver_row",
    )
    print(json.dumps({"decision": "g549_fulltheta_replay_executed", "rows": len(rows)}))
    return 0


def summarize_pair_group(group: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in group if str(row.get("quality_delta_ratio", "")).strip()]
    both = [row for row in group if boolish(row.get("both_success"))]
    regressions = sum(1 for row in group if boolish(row.get("success_regression")))
    better = sum(1 for row in group if boolish(row.get("better")))
    worse = sum(1 for row in group if boolish(row.get("worse")))
    mean_delta = statistics.mean(deltas) if deltas else math.nan
    support = len(both)
    seed_support = len({row.get("seed_block", "") for row in group})
    if support >= 80 and seed_support >= 3 and regressions == 0 and math.isfinite(mean_delta) and mean_delta < 0 and better > worse:
        status = "true_safe_gain"
    elif support >= 80 and regressions == 0:
        status = "safe_but_no_gain"
    elif regressions > 0 and math.isfinite(mean_delta) and mean_delta < 0:
        status = "unsafe_useful"
    else:
        status = "non_evaluable"
    near_miss = support >= 120 and regressions / max(1, len(group)) <= 0.005 and math.isfinite(mean_delta) and mean_delta < 0 and better > worse
    return {
        "support_pairs": support,
        "pair_rows": len(group),
        "seed_block_support": seed_support,
        "vs_static_flow_success_regression_count": regressions,
        "vs_static_flow_success_regression_rate": csv_number(regressions / max(1, len(group))),
        "vs_static_flow_quality_only_mean_delta": "" if not math.isfinite(mean_delta) else csv_number(mean_delta),
        "better_count_vs_static_flow": better,
        "worse_count_vs_static_flow": worse,
        "development_near_miss_profile": near_miss,
        "region_status": status,
    }


def analyze_fulltheta_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    vs_static, vs_family, vs_additive, failures = result_pairs(rows)
    write_rows(FULLTHETA_VS_STATIC_CSV, vs_static)
    write_rows(FULLTHETA_VS_ADDITIVE_CSV, vs_additive)
    write_rows(FULLTHETA_VS_FAMILY_CSV, vs_family)
    write_rows(FULLTHETA_FAILURE_CASES_CSV, failures)
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in vs_static:
        grouped[
            (
                row.get("theta_cluster", row.get("sampling_policy", "")),
                row.get("map_family", ""),
                row.get("agents", ""),
                row.get("nominal_budget_ms", ""),
                row.get("horizon_id", ""),
            )
        ].append(row)
    board = []
    for key, group in sorted(grouped.items()):
        cluster, fam, agents, budget, horizon_id = key
        board.append(
            {
                "theta_cluster": cluster,
                "map_family": fam,
                "agents": agents,
                "nominal_budget_ms": budget,
                "horizon_id": horizon_id,
                **summarize_pair_group(group),
                **claims(),
            }
        )
    write_rows(FULLTHETA_TRUE_GAIN_CSV, [row for row in board if row["region_status"] == "true_safe_gain"])
    write_rows(FULLTHETA_SAFE_NO_GAIN_CSV, [row for row in board if row["region_status"] == "safe_but_no_gain"])
    write_rows(FULLTHETA_UNSAFE_USEFUL_CSV, [row for row in board if row["region_status"] == "unsafe_useful"])
    write_rows(FULLTHETA_NON_EVALUABLE_CSV, [row for row in board if row["region_status"] == "non_evaluable"])
    generated = [row for row in rows if str(row.get("role", "")).startswith("generated_theta::")]
    sens = []
    for col in THETA_COLUMNS:
        vals = [number(row.get(col), math.nan) for row in generated]
        finite_vals = [value for value in vals if math.isfinite(value)]
        sens.append(
            {
                "theta_parameter": col,
                "mean": "" if not finite_vals else csv_number(statistics.mean(finite_vals)),
                "min": "" if not finite_vals else csv_number(min(finite_vals)),
                "max": "" if not finite_vals else csv_number(max(finite_vals)),
                **claims(),
            }
        )
    write_rows(FULLTHETA_PARAM_SENSITIVITY_CSV, sens)
    finite_rows = [row for row in rows if g546.ratio(row) is not None]
    match_gen = [row for row in generated if row.get("fulltheta_fingerprint_match") != ""]
    match_rate = sum(1 for row in match_gen if boolish(row.get("fulltheta_fingerprint_match"))) / max(1, len(match_gen))
    both_success = sum(1 for row in vs_static if boolish(row.get("both_success")))
    hard_min = len(rows) >= 30000 and len(finite_rows) >= 3000 and both_success >= 2000 and match_rate >= 1.0 and all(boolish(row.get("candidate_recognized")) for row in rows)
    true_gain = sum(1 for row in board if row["region_status"] == "true_safe_gain")
    if not hard_min:
        decision = "g549_calibration_evaluable_core_ready_fulltheta_replay_underpowered"
    elif true_gain > 0:
        decision = "g549_fulltheta_true_safe_gain_regions_found_continue_generator"
    else:
        decision = "g549_fulltheta_replay_no_primary_staticflow_signal_continue_design"
    return {
        "schema_version": "phase5p5_repair5g549_fulltheta_replay_summary_v1",
        "decision": decision,
        "new_fulltheta_solver_rows": len(rows),
        "fulltheta_candidate_rows": len(generated),
        "baseline_rows": len(rows) - len(generated),
        "contexts": len({row.get("context_horizon_key") for row in rows}),
        "distinct_fulltheta_rows": len({tuple(row.get(col, "") for col in THETA_COLUMNS) for row in generated}),
        "finite_ratio_rows": len(finite_rows),
        "both_success_quality_pairs_vs_static_flow": both_success,
        "candidate_recognized_all": bool(rows) and all(boolish(row.get("candidate_recognized")) for row in rows),
        "fulltheta_fingerprint_match_rate": csv_number(match_rate),
        "true_safe_gain_regions": true_gain,
        "safe_but_no_gain_regions": sum(1 for row in board if row["region_status"] == "safe_but_no_gain"),
        "unsafe_useful_regions": sum(1 for row in board if row["region_status"] == "unsafe_useful"),
        "non_evaluable_regions": sum(1 for row in board if row["region_status"] == "non_evaluable"),
        "primary_baseline": "static_flow_shield",
        "additive_ltm_role": "paper/parity floor",
        "family_static_role": "diagnostic baseline",
        **claims(),
    }


def main_analyze_fulltheta_replay(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.49 fulltheta replay analysis")
    if not resolve(FULLTHETA_RESULTS_CSV).exists():
        rc = main_run_fulltheta_replay([])
        if rc != 0:
            return rc
    rows = read_rows(FULLTHETA_RESULTS_CSV)
    summary = analyze_fulltheta_rows(rows)
    write_json(FULLTHETA_SUMMARY, summary)
    write_text(
        FULLTHETA_REPORT,
        "# G5.49 StaticFlow-Primary Fulltheta Replay\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- new fulltheta solver rows: `{summary['new_fulltheta_solver_rows']}`\n"
        f"- fulltheta candidate rows: `{summary['fulltheta_candidate_rows']}`\n"
        f"- baseline rows: `{summary['baseline_rows']}`\n"
        f"- finite ratio rows: `{summary['finite_ratio_rows']}`\n"
        f"- both-success pairs vs static_flow: `{summary['both_success_quality_pairs_vs_static_flow']}`\n"
        f"- true safe-gain regions: `{summary['true_safe_gain_regions']}`\n"
        f"- safe-but-no-gain regions: `{summary['safe_but_no_gain_regions']}`\n\n"
        "The primary comparison is fulltheta candidate versus static_flow_shield. "
        "Additive and family/static comparisons are diagnostics only.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": summary["new_fulltheta_solver_rows"]}))
    return 0


def main_train_eval_risk_utility_generator(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.49 risk utility generator")
    if not resolve(FULLTHETA_SUMMARY).exists():
        main_analyze_fulltheta_replay([])
    fulltheta = load_json(FULLTHETA_SUMMARY, {})
    enough_pairs = int(number(fulltheta.get("finite_ratio_rows"), 0)) >= 3000 and int(number(fulltheta.get("both_success_quality_pairs_vs_static_flow"), 0)) >= 2000
    true_regions = read_rows(FULLTHETA_TRUE_GAIN_CSV)
    if not enough_pairs or not true_regions:
        reason = "fulltheta replay did not produce usable true safe-gain signal" if enough_pairs else "fulltheta replay finite paired outcome gate not met"
        eval_row = {"decision": "g549_generator_offline_gate_failed_continue_model_design", "reason": reason, **claims()}
        write_rows(RISK_MODEL_EVAL_CSV, [eval_row])
        write_rows(UTILITY_MODEL_EVAL_CSV, [eval_row])
        write_rows(GENERATOR_EVAL_CSV, [eval_row])
        write_rows(GENERATED_THETA_CSV, [], fieldnames=["candidate_id", *THETA_COLUMNS, *claims().keys()])
        summary = {
            "schema_version": "phase5p5_repair5g549_risk_utility_generator_summary_v1",
            "decision": "g549_generator_offline_gate_failed_continue_model_design",
            "models_trained": False,
            "reason": reason,
            "risk_false_safe_count_on_validation": 0,
            "risk_gate_pass_rate": "0",
            "predicted_safe_utility_candidates": 0,
            "generated_non_static_theta_usage_rate": "0",
            **claims(),
        }
        write_json(GENERATOR_SUMMARY, summary)
        write_json(MODEL_MANIFEST, summary)
        write_text(GENERATOR_REPORT, f"# G5.49 Risk/Utility/Generator\n\n- decision: `{summary['decision']}`\n- reason: {reason}\n")
        print(json.dumps({"decision": summary["decision"]}))
        return 0
    vs_static = read_rows(FULLTHETA_VS_STATIC_CSV)
    safe_region_keys = {
        (
            row.get("theta_cluster", ""),
            row.get("map_family", ""),
            row.get("agents", ""),
            row.get("nominal_budget_ms", ""),
            row.get("horizon_id", ""),
        )
        for row in true_regions
    }
    selected_pairs = [
        row
        for row in vs_static
        if (
            row.get("theta_cluster", ""),
            row.get("map_family", ""),
            row.get("agents", ""),
            row.get("nominal_budget_ms", ""),
            row.get("horizon_id", ""),
        )
        in safe_region_keys
    ]
    validation_pairs = [row for row in selected_pairs if int(number(row.get("seed"), 0)) % 10 in {2, 3}]
    risk_false_safe = sum(1 for row in validation_pairs if boolish(row.get("success_regression")))
    pass_rate = len(selected_pairs) / max(1, len(vs_static))
    deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in selected_pairs if str(row.get("quality_delta_ratio", "")).strip()]
    utility_mean = statistics.mean(deltas) if deltas else math.nan
    risk_eval = {
        "model": "conservative_region_horizon_gate",
        "risk_false_safe_count_on_validation": risk_false_safe,
        "risk_gate_pass_rate": csv_number(pass_rate),
        "validation_pairs": len(validation_pairs),
        "selected_pairs": len(selected_pairs),
        "offline_gate_component_passed": risk_false_safe == 0 and 0.01 <= pass_rate <= 0.50,
        **claims(),
    }
    utility_eval = {
        "model": "region_mean_delta_utility",
        "selected_pairs": len(selected_pairs),
        "quality_only_mean_delta_vs_static_flow": "" if not math.isfinite(utility_mean) else csv_number(utility_mean),
        "predicted_safe_utility_candidates": len(true_regions),
        "offline_gate_component_passed": math.isfinite(utility_mean) and utility_mean < 0,
        **claims(),
    }
    generator_eval = {
        "model": "no_deployable_generator_promoted",
        "generated_theta_rows": 0,
        "generated_non_static_theta_usage_rate": "0",
        "negative_control_generator_beaten": False,
        "offline_gate_component_passed": False,
        "reason": "safe replay regions are not yet a learned generator policy",
        **claims(),
    }
    write_rows(RISK_MODEL_EVAL_CSV, [risk_eval])
    write_rows(UTILITY_MODEL_EVAL_CSV, [utility_eval])
    write_rows(GENERATOR_EVAL_CSV, [generator_eval])
    write_rows(GENERATED_THETA_CSV, [], fieldnames=["candidate_id", *THETA_COLUMNS, *claims().keys()])
    summary = {
        "schema_version": "phase5p5_repair5g549_risk_utility_generator_summary_v1",
        "decision": "g549_generator_offline_gate_failed_continue_model_design",
        "models_trained": True,
        "model_family": "conservative_region_level_risk_utility_gate",
        "reason": "true safe-gain replay regions exist, but no deployable generated-theta policy was promoted beyond replay-region hindsight",
        "risk_false_safe_count_on_validation": risk_false_safe,
        "risk_gate_pass_rate": csv_number(pass_rate),
        "predicted_safe_utility_candidates": len(true_regions),
        "generated_non_static_theta_usage_rate": "0",
        **claims(),
    }
    write_json(GENERATOR_SUMMARY, summary)
    write_json(MODEL_MANIFEST, summary)
    write_text(GENERATOR_REPORT, f"# G5.49 Risk/Utility/Generator\n\n- decision: `{summary['decision']}`\n")
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def write_targeted_or_blind_skip(kind: str, reason: str) -> None:
    if kind == "targeted":
        paths = [TARGETED_RESULTS_CSV, TARGETED_VS_STATIC_CSV, TARGETED_VS_ADDITIVE_CSV, TARGETED_VS_FAMILY_CSV, TARGETED_FAILURES_CSV]
        summary_path = TARGETED_SUMMARY
        report_path = TARGETED_REPORT
        decision = "g549_generated_theta_targeted_skipped_generator_gate_not_met"
    else:
        paths = [BLIND_RESULTS_CSV, BLIND_VS_STATIC_CSV, BLIND_VS_ADDITIVE_CSV, BLIND_VS_FAMILY_CSV, BLIND_FAILURES_CSV]
        summary_path = BLIND_SUMMARY
        report_path = BLIND_REPORT
        decision = "g549_blind_replay_skipped_targeted_gate_not_met"
    for path in paths:
        write_skip_table(path, reason)
    summary = {"schema_version": f"phase5p5_repair5g549_{kind}_summary_v1", "decision": decision, "new_solver_rows": 0, "reason": reason, **claims()}
    write_json(summary_path, summary)
    write_text(report_path, f"# G5.49 {kind.title()} Evidence\n\n- decision: `{decision}`\n- reason: {reason}\n")


def main_run_generated_theta_targeted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.49 targeted generated theta")
    if not resolve(GENERATOR_SUMMARY).exists():
        main_train_eval_risk_utility_generator([])
    generator = load_json(GENERATOR_SUMMARY, {})
    if generator.get("decision") != "g549_generator_offline_gate_passed_continue_targeted":
        write_targeted_or_blind_skip("targeted", "generator/offline gate did not pass")
        print(json.dumps({"decision": "g549_generated_theta_targeted_skipped_generator_gate_not_met"}))
        return 0
    write_targeted_or_blind_skip("targeted", "targeted replay runner intentionally gated for a later generator-positive round")
    return 0


def main_analyze_generated_theta_targeted(argv: list[str] | None = None) -> int:
    if not resolve(TARGETED_SUMMARY).exists():
        main_run_generated_theta_targeted(argv)
    return 0


def main_run_blind_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.49 blind replay")
    if not resolve(TARGETED_SUMMARY).exists():
        main_run_generated_theta_targeted([])
    targeted = load_json(TARGETED_SUMMARY, {})
    if targeted.get("decision") != "g549_generated_theta_targeted_positive_continue_blind":
        write_targeted_or_blind_skip("blind", "targeted strict gate did not pass")
        print(json.dumps({"decision": "g549_blind_replay_skipped_targeted_gate_not_met"}))
        return 0
    write_targeted_or_blind_skip("blind", "blind replay intentionally gated for a later targeted-positive round")
    return 0


def main_analyze_blind_evidence(argv: list[str] | None = None) -> int:
    if not resolve(BLIND_SUMMARY).exists():
        main_run_blind_if_warranted(argv)
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.49 decision")
    if not resolve(BLIND_SUMMARY).exists():
        main_analyze_blind_evidence([])
    verify = load_json(VERIFY_SUMMARY, {})
    semantics = load_json(SEMANTICS_SUMMARY, {})
    calibration = load_json(CALIBRATION_SUMMARY, {})
    fulltheta = load_json(FULLTHETA_SUMMARY, {})
    generator = load_json(GENERATOR_SUMMARY, {})
    targeted = load_json(TARGETED_SUMMARY, {})
    blind = load_json(BLIND_SUMMARY, {})
    if verify.get("decision") == "g549_g548_verification_blocked":
        decision = "g549_g548_verification_blocked"
    elif calibration.get("decision") == "g549_calibration_topup_underpowered_continue":
        decision = "g549_calibration_topup_underpowered_continue"
    elif fulltheta.get("decision") in {"g549_calibration_evaluable_core_ready_fulltheta_replay_underpowered", "g549_fulltheta_replay_no_primary_staticflow_signal_continue_design", "g549_fulltheta_true_safe_gain_regions_found_continue_generator"}:
        decision = fulltheta.get("decision")
    elif generator.get("decision") == "g549_generator_offline_gate_failed_continue_model_design":
        decision = "g549_generator_offline_gate_failed_continue_model_design"
    else:
        decision = fulltheta.get("decision") or calibration.get("decision") or "g549_calibration_topup_underpowered_continue"
    answers = {
        "did_g549_reach_3000_cumulative_finite_ratio_rows": int(number(calibration.get("cumulative_finite_ratio_rows"), 0)) >= 3000,
        "unique_evaluable_stratum_count": calibration.get("unique_evaluable_stratum_count", 0),
        "warehouse_non_evaluable": calibration.get("warehouse_non_evaluable_on_local_budget", True),
        "did_fulltheta_replay_run": int(number(fulltheta.get("new_fulltheta_solver_rows"), 0)) > 0,
        "did_any_fulltheta_cluster_beat_static_flow_safely": int(number(fulltheta.get("true_safe_gain_regions"), 0)) > 0,
        "were_gains_over_additive_only_or_also_static_flow": "static_flow_true_safe_gain" if int(number(fulltheta.get("true_safe_gain_regions"), 0)) > 0 else "no_static_flow_primary_true_gain",
        "did_family_static_disagreement_explain_gap": "diagnostic_only_not_primary",
        "did_generator_beat_random_or_local_static_flow_perturbations": generator.get("decision") == "g549_generator_offline_gate_passed_continue_targeted",
        "next_step": "generator_model_design" if int(number(fulltheta.get("true_safe_gain_regions"), 0)) > 0 else "fulltheta_refinement_or_server_scale_replay",
    }
    summary = {
        "schema_version": "phase5p5_repair5g549_decision_summary_v1",
        "decision": decision,
        "component_decisions": {
            "g548_verification": verify.get("decision", ""),
            "g548_calibration_semantics": semantics.get("decision", ""),
            "calibration_topup": calibration.get("decision", ""),
            "fulltheta_replay": fulltheta.get("decision", ""),
            "generator": generator.get("decision", ""),
            "targeted": targeted.get("decision", ""),
            "blind": blind.get("decision", ""),
        },
        "answers": answers,
        "key_metrics": {
            "new_calibration_solver_rows": calibration.get("new_calibration_solver_rows", 0),
            "cumulative_finite_ratio_rows": calibration.get("cumulative_finite_ratio_rows", 0),
            "unique_evaluable_stratum_count": calibration.get("unique_evaluable_stratum_count", 0),
            "new_fulltheta_solver_rows": fulltheta.get("new_fulltheta_solver_rows", 0),
            "both_success_quality_pairs_vs_static_flow": fulltheta.get("both_success_quality_pairs_vs_static_flow", 0),
            "true_safe_gain_regions": fulltheta.get("true_safe_gain_regions", 0),
            "fulltheta_fingerprint_match_rate": fulltheta.get("fulltheta_fingerprint_match_rate", "0"),
        },
        "primary_baseline": "static_flow_shield",
        "additive_ltm_role": "paper-faithful floor",
        "strong_static_role": "diagnostic only",
        **claims(),
    }
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.49 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- new calibration solver rows: `{summary['key_metrics']['new_calibration_solver_rows']}`\n"
        f"- cumulative finite ratio rows: `{summary['key_metrics']['cumulative_finite_ratio_rows']}`\n"
        f"- unique evaluable strata: `{summary['key_metrics']['unique_evaluable_stratum_count']}`\n"
        f"- fulltheta solver rows: `{summary['key_metrics']['new_fulltheta_solver_rows']}`\n"
        f"- fulltheta both-success pairs vs static_flow: `{summary['key_metrics']['both_success_quality_pairs_vs_static_flow']}`\n"
        f"- true safe-gain regions: `{summary['key_metrics']['true_safe_gain_regions']}`\n\n"
        "G5.49 keeps all Phase5.5, Phase6, runtime, and AAAI claim flags closed. "
        "The result is calibrated-core development evidence unless a later server-scale round broadens coverage.\n",
    )
    print(json.dumps({"decision": decision}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]

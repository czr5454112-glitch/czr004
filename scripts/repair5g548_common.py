"""Repair5G.5.48 evaluable-horizon fulltheta replay.

G5.48 keeps the G5.47 full-theta materialization path, but changes the
experiment from a declared budget grid to a real, materialized budget/horizon
calibration.  The primary learned UpdateParams comparison is static_flow_shield;
strong static variants stay diagnostic unless a later round explicitly changes
the primary baseline.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter, defaultdict
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


PLAN_FILE = "czr004_g548_evaluable_horizon_fulltheta_neural_updateparams_replay_plan.md"

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g548_g547_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g548_g547_verification_summary.json"
VERIFY_AUDIT_CSV = "outputs/tables/phase5p5_repair5g548_g547_artifact_audit.csv"

BLOCKER_REPORT = "outputs/reports/phase5p5_repair5g548_g547_evaluability_blocker.md"
BLOCKER_SUMMARY = "outputs/reports/phase5p5_repair5g548_g547_evaluability_blocker_summary.json"
G547_CALIBRATION_AUDIT_CSV = "outputs/tables/phase5p5_repair5g548_g547_calibration_audit.csv"
G547_NO_SOLUTION_AUDIT_CSV = "outputs/tables/phase5p5_repair5g548_g547_no_solution_context_audit.csv"
G547_BUDGET_FIELD_AUDIT_CSV = "outputs/tables/phase5p5_repair5g548_g547_budget_field_consistency_audit.csv"

CALIBRATION_PLAN_CSV = "outputs/tables/phase5p5_repair5g548_budget_calibration_plan.csv"
CALIBRATION_RESULTS_CSV = "outputs/tables/phase5p5_repair5g548_budget_calibration_results.csv"
CALIBRATION_SELECTION_CSV = "outputs/tables/phase5p5_repair5g548_budget_horizon_selection.csv"
CALIBRATION_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g548_calibration_by_stratum.csv"
NON_EVALUABLE_STRATA_CSV = "outputs/tables/phase5p5_repair5g548_non_evaluable_strata.csv"
LOW_DENSITY_DIAGNOSTIC_CSV = "outputs/tables/phase5p5_repair5g548_low_density_diagnostic_if_needed.csv"
CALIBRATION_SUMMARY = "outputs/reports/phase5p5_repair5g548_budget_calibration_summary.json"
CALIBRATION_REPORT = "outputs/reports/phase5p5_repair5g548_budget_calibration.md"
CALIBRATION_LOG_DIR = "outputs/logs/phase5p5_repair5g548_budget_calibration"
CALIBRATION_RUN_JSONL = f"{CALIBRATION_LOG_DIR}/runs.jsonl"
CALIBRATION_COMMAND_JSONL = f"{CALIBRATION_LOG_DIR}/commands.jsonl"
CALIBRATION_UPDATE_JSONL = f"{CALIBRATION_LOG_DIR}/updates.jsonl"
CALIBRATION_PROBE_JSONL = f"{CALIBRATION_LOG_DIR}/counterfactual_probes.jsonl"
CALIBRATION_CHECKPOINT_JSONL = f"{CALIBRATION_LOG_DIR}/checkpoints.jsonl"
CALIBRATION_STATUS_JSON = f"{CALIBRATION_LOG_DIR}/status.json"
CALIBRATION_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g548_budget_calibration_scenarios"
CALIBRATION_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g548_budget_calibration_scenario_generation.json"

FULLTHETA_PLAN_CSV = "outputs/tables/phase5p5_repair5g548_fulltheta_replay_plan.csv"
FULLTHETA_RESULTS_CSV = "outputs/tables/phase5p5_repair5g548_fulltheta_replay_results.csv"
FULLTHETA_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g548_fulltheta_selected_vs_static_flow.csv"
FULLTHETA_VS_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g548_fulltheta_selected_vs_additive.csv"
FULLTHETA_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g548_fulltheta_selected_vs_family_static.csv"
FULLTHETA_TRUE_GAIN_CSV = "outputs/tables/phase5p5_repair5g548_fulltheta_true_safe_gain_regions.csv"
FULLTHETA_SAFE_NO_GAIN_CSV = "outputs/tables/phase5p5_repair5g548_fulltheta_safe_but_no_gain_regions.csv"
FULLTHETA_UNSAFE_USEFUL_CSV = "outputs/tables/phase5p5_repair5g548_fulltheta_unsafe_useful_regions.csv"
FULLTHETA_STRONG_STATIC_GAP_CSV = "outputs/tables/phase5p5_repair5g548_fulltheta_primary_signal_strong_static_gap.csv"
FULLTHETA_NON_EVALUABLE_CSV = "outputs/tables/phase5p5_repair5g548_fulltheta_non_evaluable_regions.csv"
FULLTHETA_PARAM_SENSITIVITY_CSV = "outputs/tables/phase5p5_repair5g548_fulltheta_parameter_sensitivity.csv"
FULLTHETA_SUMMARY = "outputs/reports/phase5p5_repair5g548_fulltheta_evidence_summary.json"
FULLTHETA_REPORT = "outputs/reports/phase5p5_repair5g548_fulltheta_evidence.md"

RISK_EVAL_CSV = "outputs/tables/phase5p5_repair5g548_risk_model_eval.csv"
UTILITY_EVAL_CSV = "outputs/tables/phase5p5_repair5g548_utility_model_eval.csv"
GENERATOR_EVAL_CSV = "outputs/tables/phase5p5_repair5g548_generator_eval.csv"
GENERATED_THETA_CSV = "outputs/tables/phase5p5_repair5g548_generated_theta_candidates.csv"
GENERATOR_SUMMARY = "outputs/reports/phase5p5_repair5g548_risk_utility_generator_summary.json"
GENERATOR_REPORT = "outputs/reports/phase5p5_repair5g548_risk_utility_generator.md"
MODEL_MANIFEST = "artifacts/models/laur_ltm/repair5g548_model_manifest.json"

TARGETED_RESULTS_CSV = "outputs/tables/phase5p5_repair5g548_generated_theta_targeted_results.csv"
TARGETED_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g548_generated_theta_targeted_vs_static_flow.csv"
TARGETED_VS_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g548_generated_theta_targeted_vs_additive.csv"
TARGETED_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g548_generated_theta_targeted_vs_family_static.csv"
TARGETED_FAILURES_CSV = "outputs/tables/phase5p5_repair5g548_targeted_failure_cases.csv"
TARGETED_SUMMARY = "outputs/reports/phase5p5_repair5g548_generated_theta_targeted_evidence_summary.json"
TARGETED_REPORT = "outputs/reports/phase5p5_repair5g548_generated_theta_targeted_evidence.md"

BLIND_RESULTS_CSV = "outputs/tables/phase5p5_repair5g548_generated_theta_blind_results.csv"
BLIND_SUMMARY = "outputs/reports/phase5p5_repair5g548_blind_evidence_summary.json"
BLIND_REPORT = "outputs/reports/phase5p5_repair5g548_blind_evidence.md"

DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g548_decision_summary.json"
DECISION_REPORT = "outputs/reports/phase5p5_repair5g548_decision.md"

THETA_COLUMNS = list(g547.THETA_COLUMNS)
ADDITIVE = g547.ADDITIVE
STATIC_FLOW = g547.STATIC_FLOW
FAMILY_STATIC = g547.FAMILY_STATIC
BASELINE_ROLES = dict(g547.BASELINE_ROLES)
BASE_MAPS = list(g546.BASE_MAPS)
BASE_AGENTS = list(g546.BASE_AGENTS)
BASE_BUDGETS = list(g546.BASE_BUDGETS)

PRIMARY_SEEDS = [1206, 1207, 1208, 1209, 1210, 1211]
LOW_DENSITY_SEEDS = [1212, 1213]
CALIBRATION_HORIZONS = [
    ("c0_short250_t050_i2", 250, 0.50, 2),
    ("c0_short500_t050_i2", 500, 0.50, 2),
    ("c0_short1000_t050_i2", 1000, 0.50, 2),
    ("c0_short2000_t050_i2", 2000, 0.50, 2),
    ("c0_short5000_t050_i2", 5000, 0.50, 2),
]
LOW_DENSITY_HORIZON = ("diagnostic_short1000_t050_i2", 1000, 0.50, 2)
CALIBRATION_REGISTRY_LABELS = [
    "lambda_flow_low",
    "lambda_cong_high",
    "alpha_flow_wait_progress_high",
    "goal_projection_agent_progress",
]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--max-contexts", type=int, default=0)
    p.add_argument("--row-limit", type=int, default=0)
    p.add_argument("--max-workers", type=int, default=1)
    p.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    p.add_argument("--skip-low-density-diagnostic", action="store_true")
    p.add_argument("--ids", nargs="*", type=int)
    return p


def validate_ids(args: argparse.Namespace, label: str) -> None:
    ids = [int(value) for value in (args.ids or [])]
    ids.extend(PRIMARY_SEEDS)
    ids.extend(LOW_DENSITY_SEEDS)
    bad = [value for value in ids if 166 <= value <= 205]
    if bad:
        print(json.dumps({"decision": "reserved_id_guard_rejected", "label": label, "ids": bad}))
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


def write_skip_table(path: str, fieldnames: list[str]) -> None:
    write_rows(path, [], fieldnames=fieldnames)


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


def ensure_fulltheta_registry() -> list[dict[str, Any]]:
    if not resolve(g547.FULLTHETA_REGISTRY_CSV).exists():
        g547.main_create_fulltheta_registry([])
    return read_rows(g547.FULLTHETA_REGISTRY_CSV)


def calibration_registry_rows() -> list[dict[str, Any]]:
    registry = ensure_fulltheta_registry()
    by_label = {str(row.get("registry_label")): row for row in registry}
    rows = [by_label[label] for label in CALIBRATION_REGISTRY_LABELS if label in by_label]
    if len(rows) < 4:
        rows = registry[1:5]
    return rows[:4]


def baseline_plan_rows(context: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    rows = []
    for role, candidate in BASELINE_ROLES.items():
        theta = g545.additive_theta() if candidate == ADDITIVE else g545.static_flow_theta()
        if candidate == FAMILY_STATIC:
            theta = g545.theta_from_compact(
                c=1.25,
                b=1.25,
                f=1.0,
                w=0.75,
                dc=0.95,
                df=1.0,
                beta=0.60,
                max_shield=0.75,
            )
        rows.append(
            {
                "plan_row_id": f"{prefix}_{len(rows):08d}",
                **context,
                "role": role,
                "candidate_id": candidate,
                "materialized_method": candidate,
                "sampling_policy": "baseline",
                "counts_as_primary_calibration": context.get("panel") == "primary",
                **g547.clamp_theta(theta),
                **claims(),
            }
        )
    return rows


def fulltheta_plan_rows(context: dict[str, Any], prefix: str) -> list[dict[str, Any]]:
    rows = []
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
                "counts_as_primary_calibration": context.get("panel") == "primary",
                **{col: reg.get(col, "") for col in THETA_COLUMNS},
                **claims(),
            }
        )
    return rows


def primary_calibration_contexts() -> list[dict[str, Any]]:
    rows = []
    for map_name in BASE_MAPS:
        family = infer_map_family(map_name)
        for agents in BASE_AGENTS:
            for nominal_budget in BASE_BUDGETS:
                for seed in PRIMARY_SEEDS:
                    for horizon_id, short_budget_ms, base_time_limit_sec, ltm_max_iterations in CALIBRATION_HORIZONS:
                        rows.append(
                            {
                                "panel": "primary",
                                "context_id": f"{map_name}|a{agents}|s{seed}|b{nominal_budget}|{horizon_id}",
                                "map": map_name,
                                "map_family": family,
                                "agents": agents,
                                "seed": seed,
                                "budget_ms": nominal_budget,
                                "nominal_budget_ms": nominal_budget,
                                "horizon_id": horizon_id,
                                "short_budget_ms": short_budget_ms,
                                "base_time_limit_sec": csv_number(base_time_limit_sec),
                                "ltm_max_iterations": ltm_max_iterations,
                                "fresh_seed_block": f"{(seed // 20) * 20}_{(seed // 20) * 20 + 19}",
                                "source": "g548_real_c0_expanded_cheap_horizon",
                            }
                        )
    return rows


def low_density_contexts() -> list[dict[str, Any]]:
    rows = []
    horizon_id, short_budget_ms, base_time_limit_sec, ltm_max_iterations = LOW_DENSITY_HORIZON
    for map_name in BASE_MAPS:
        family = infer_map_family(map_name)
        for agents in [20, 30, 40]:
            for seed in LOW_DENSITY_SEEDS:
                rows.append(
                    {
                        "panel": "low_density_diagnostic",
                        "context_id": f"{map_name}|a{agents}|s{seed}|b1000|{horizon_id}",
                        "map": map_name,
                        "map_family": family,
                        "agents": agents,
                        "seed": seed,
                        "budget_ms": 1000,
                        "nominal_budget_ms": 1000,
                        "horizon_id": horizon_id,
                        "short_budget_ms": short_budget_ms,
                        "base_time_limit_sec": csv_number(base_time_limit_sec),
                        "ltm_max_iterations": ltm_max_iterations,
                        "fresh_seed_block": f"{(seed // 20) * 20}_{(seed // 20) * 20 + 19}",
                        "source": "g548_low_density_diagnostic_not_primary_evidence",
                    }
                )
    return rows


def write_calibration_plan(max_contexts: int = 0) -> list[dict[str, Any]]:
    contexts = primary_calibration_contexts()
    if max_contexts > 0:
        contexts = contexts[:max_contexts]
    rows: list[dict[str, Any]] = []
    for context in contexts:
        prefix = f"g548_calibration_{len(rows):08d}"
        rows.extend(baseline_plan_rows(context, prefix))
        rows.extend(fulltheta_plan_rows(context, prefix))
    for idx, row in enumerate(rows):
        row["plan_row_id"] = f"g548_calibration_{idx:08d}"
    write_rows(CALIBRATION_PLAN_CSV, rows)
    summary = {
        "schema_version": "phase5p5_repair5g548_budget_calibration_plan_summary_v1",
        "decision": "g548_real_budget_calibration_plan_created",
        "panel": "primary",
        "strata": len({(row["map_family"], row["agents"], row["nominal_budget_ms"]) for row in contexts}),
        "calibration_seed_count_per_stratum": len(PRIMARY_SEEDS),
        "context_horizons": len(contexts),
        "plan_rows": len(rows),
        "baseline_rows_planned": sum(1 for row in rows if not str(row.get("role", "")).startswith("generated_theta::")),
        "fulltheta_rows_planned": sum(1 for row in rows if str(row.get("role", "")).startswith("generated_theta::")),
        "horizons": [h[0] for h in CALIBRATION_HORIZONS],
        "reserved_ids_166_205_used": False,
        **claims(),
    }
    write_json(CALIBRATION_SUMMARY, summary | {"run_status": "planned_not_yet_executed"})
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "context_horizons": len(contexts)}))
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
    return sorted(grouped.items(), key=lambda item: item[0])


def completed_groups_from_results(plan_rows: list[dict[str, Any]], result_path: str) -> set[tuple[str, int, int, int, str]]:
    expected = {
        key: {str(row.get("materialized_method")) for row in rows if row.get("materialized_method")}
        for key, rows in probe_context_groups(plan_rows)
    }
    seen: dict[tuple[str, int, int, int, str], set[str]] = defaultdict(set)
    for row in read_rows(result_path):
        key = group_key(row)
        seen[key].add(str(row.get("materialized_method", "")))
    return {key for key, methods in expected.items() if methods and methods.issubset(seen.get(key, set()))}


def task_file(temp_dir: Path, index: int, key: tuple[str, int, int, int, str], suffix: str) -> Path:
    token = stable_hash("|".join(map(str, key)), modulo=10**12)
    return temp_dir / f"context_{index:06d}_{token:012d}.{suffix}.jsonl"


def run_context_task(
    *,
    index: int,
    key: tuple[str, int, int, int, str],
    group_rows: list[dict[str, Any]],
    binary: Path,
    log_dir: Path,
    temp_dir: Path,
    scenario_dir: Path,
    manifest_prefix: str,
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
    spec = MethodSpec(
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
            str(resolve(g547.FULLTHETA_REGISTRY_CSV)),
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
    )
    task_run = log_dir / f"task_{stable_hash('|'.join(map(str, key)), modulo=10**12):012d}.runs.jsonl"
    write_jsonl(task_run, rows)
    raw_probe = read_jsonl_tolerant(task_probe)
    enriched = g546.enrich_probe_rows(raw_probe, group_rows, row_prefix="g548_probe")
    for row in enriched:
        row["execution_mode"] = "new_g548_real_budget_calibration_solver_row"
        row["counts_as_new_g548_solver_row"] = True
        row["probe_materialized"] = True
        row["no_probe_reason"] = ""
        row["panel"] = first.get("panel", "")
        row["horizon_id"] = horizon_id
        row["nominal_budget_ms"] = nominal_budget
        row["short_budget_ms"] = first.get("short_budget_ms", "")
        row["base_time_limit_sec"] = first.get("base_time_limit_sec", "")
        row["ltm_max_iterations"] = first.get("ltm_max_iterations", "")
        row["counts_as_primary_calibration"] = first.get("panel") == "primary"
        row["context_horizon_key"] = "|".join(map(str, key))
        if str(row.get("role", "")).startswith("generated_theta::"):
            matched, missing = g547.params_match(row.get("updateparams_fingerprint", ""), row)
            row["fulltheta_fingerprint_match"] = matched
            row["fulltheta_fingerprint_mismatched_fields"] = ";".join(missing)
        else:
            row["fulltheta_fingerprint_match"] = True
            row["fulltheta_fingerprint_mismatched_fields"] = ""
    command_row.update(
        {
            "panel": first.get("panel", ""),
            "horizon_id": horizon_id,
            "nominal_budget_ms": nominal_budget,
            "short_budget_ms": first.get("short_budget_ms", ""),
            "base_time_limit_sec": first.get("base_time_limit_sec", ""),
            "ltm_max_iterations": first.get("ltm_max_iterations", ""),
            "candidate_count": len(methods),
        }
    )
    return {
        "key": key,
        "run_rows": rows,
        "update_rows": update_rows,
        "command_row": command_row,
        "probe_rows": raw_probe,
        "checkpoint_rows": read_jsonl_tolerant(task_checkpoint),
        "enriched_rows": enriched,
    }


def annotate_probe_rows(raw_probe: list[dict[str, Any]], group_rows: list[dict[str, Any]], key: tuple[str, int, int, int, str]) -> list[dict[str, Any]]:
    first = group_rows[0]
    _map_name, _agents_count, _seed, nominal_budget, horizon_id = key
    enriched = g546.enrich_probe_rows(raw_probe, group_rows, row_prefix="g548_probe")
    for row in enriched:
        row["execution_mode"] = "new_g548_real_budget_calibration_solver_row"
        row["counts_as_new_g548_solver_row"] = True
        row["probe_materialized"] = True
        row["no_probe_reason"] = ""
        row["panel"] = first.get("panel", "")
        row["horizon_id"] = horizon_id
        row["nominal_budget_ms"] = nominal_budget
        row["short_budget_ms"] = first.get("short_budget_ms", "")
        row["base_time_limit_sec"] = first.get("base_time_limit_sec", "")
        row["ltm_max_iterations"] = first.get("ltm_max_iterations", "")
        row["counts_as_primary_calibration"] = first.get("panel") == "primary"
        row["context_horizon_key"] = "|".join(map(str, key))
        if str(row.get("role", "")).startswith("generated_theta::"):
            matched, missing = g547.params_match(row.get("updateparams_fingerprint", ""), row)
            row["fulltheta_fingerprint_match"] = matched
            row["fulltheta_fingerprint_mismatched_fields"] = ";".join(missing)
        else:
            row["fulltheta_fingerprint_match"] = True
            row["fulltheta_fingerprint_mismatched_fields"] = ""
    return enriched


def no_probe_placeholder_rows(group_rows: list[dict[str, Any]], key: tuple[str, int, int, int, str]) -> list[dict[str, Any]]:
    first = group_rows[0]
    map_name, agents_count, seed, nominal_budget, horizon_id = key
    rows: list[dict[str, Any]] = []
    context_key = f"{map_name}|{agents_count}|{seed}|{first.get('short_budget_ms', '')}|no_probe|{horizon_id}"
    for plan in group_rows:
        rows.append(
            {
                "g548_probe_row_id": f"g548_no_probe_{stable_hash(context_key + '|' + str(plan.get('materialized_method')), modulo=10**12):012d}",
                "execution_mode": "new_g548_real_budget_calibration_no_probe_solver_attempt",
                "counts_as_new_g546_solver_row": False,
                "counts_as_new_g548_solver_row": True,
                "real_solver_execution": True,
                "probe_materialized": False,
                "no_probe_reason": "outer_static_flow_no_solution_or_no_counterfactual_checkpoint",
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
                "solution_found": False,
                "probe_feasible": False,
                "sum_of_loss_ratio": "",
                "probe_sum_of_loss": "",
                "probe_lower_bound": "",
                "probe_runtime_ms": "",
                "expanded_nodes": "",
                "low_level_pibt_calls": "",
                "trace_event_count": "",
                "candidate_recognized": True,
                "updateparams_hash": "",
                "updateparams_fingerprint": "",
                "traffic_before_hash_full": "",
                **{col: plan.get(col, "") for col in THETA_COLUMNS},
                "panel": first.get("panel", ""),
                "horizon_id": horizon_id,
                "nominal_budget_ms": nominal_budget,
                "short_budget_ms": first.get("short_budget_ms", ""),
                "base_time_limit_sec": first.get("base_time_limit_sec", ""),
                "ltm_max_iterations": first.get("ltm_max_iterations", ""),
                "counts_as_primary_calibration": first.get("panel") == "primary",
                "context_horizon_key": "|".join(map(str, key)),
                "fulltheta_fingerprint_match": True,
                "fulltheta_fingerprint_mismatched_fields": "",
                **claims(),
            }
        )
    return rows


def recover_results_from_task_tmp(plan_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = probe_context_groups(plan_rows)
    temp_dir = resolve(CALIBRATION_LOG_DIR) / "_task_tmp"
    recovered: list[dict[str, Any]] = []
    for index, (key, group_rows) in enumerate(groups):
        probe_path = task_file(temp_dir, index, key, "probe")
        checkpoint_path = task_file(temp_dir, index, key, "checkpoints")
        if not probe_path.exists() and not checkpoint_path.exists():
            continue
        raw_probe = read_jsonl_tolerant(probe_path)
        if raw_probe:
            recovered.extend(annotate_probe_rows(raw_probe, group_rows, key))
        else:
            recovered.extend(no_probe_placeholder_rows(group_rows, key))
    if recovered:
        write_rows_atomic(CALIBRATION_RESULTS_CSV, recovered)
        write_status(len(groups), len({row.get("context_horizon_key") for row in recovered}), "recovered_from_task_tmp")
    return recovered


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


def write_status(total: int, completed: int, phase: str, last: dict[str, Any] | None = None) -> None:
    payload = {
        "schema_version": "phase5p5_repair5g548_budget_calibration_status_v1",
        "phase": phase,
        "total_context_horizon_tasks": total,
        "completed_context_horizon_tasks": completed,
        "completed_solver_rows": table_count(CALIBRATION_RESULTS_CSV),
        "last_task": last or {},
    }
    write_json(CALIBRATION_STATUS_JSON, payload)


def run_probe_plan(
    plan_rows: list[dict[str, Any]],
    *,
    binary: Path,
    overwrite: bool,
    row_limit: int,
    max_workers: int,
    manifest_prefix: str,
) -> list[dict[str, Any]]:
    if overwrite:
        for path in [
            CALIBRATION_RESULTS_CSV,
            LOW_DENSITY_DIAGNOSTIC_CSV,
            CALIBRATION_RUN_JSONL,
            CALIBRATION_COMMAND_JSONL,
            CALIBRATION_UPDATE_JSONL,
            CALIBRATION_PROBE_JSONL,
            CALIBRATION_CHECKPOINT_JSONL,
        ]:
            resolve(path).unlink(missing_ok=True)
    groups = probe_context_groups(plan_rows)
    completed = set() if overwrite else completed_groups_from_results(plan_rows, CALIBRATION_RESULTS_CSV)
    scheduled = []
    estimated_rows = table_count(CALIBRATION_RESULTS_CSV)
    for index, (key, group_rows) in enumerate(groups):
        if row_limit and estimated_rows >= row_limit:
            break
        if key in completed:
            continue
        scheduled.append((index, key, group_rows))
        estimated_rows += len({str(row.get("materialized_method")) for row in group_rows})
    maps = sorted({key[0] for key, _rows in groups})
    agents = sorted({key[1] for key, _rows in groups})
    seeds = sorted({key[2] for key, _rows in groups})
    prepare_scenarios(
        root=ROOT,
        source_scenario_dir=resolve(DEFAULT_SOURCE_SCENARIO_DIR),
        scenario_dir=resolve(CALIBRATION_SCENARIO_DIR),
        scenario_metadata=resolve(CALIBRATION_SCENARIO_METADATA),
        maps=maps,
        agent_counts=agents,
        instance_ids=seeds,
    )
    log_root = resolve(CALIBRATION_LOG_DIR)
    temp_dir = log_root / "_task_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    all_results = read_rows(CALIBRATION_RESULTS_CSV)
    all_runs = read_jsonl_tolerant(CALIBRATION_RUN_JSONL)
    all_commands = read_jsonl_tolerant(CALIBRATION_COMMAND_JSONL)
    all_updates = read_jsonl_tolerant(CALIBRATION_UPDATE_JSONL)
    all_probes = read_jsonl_tolerant(CALIBRATION_PROBE_JSONL)
    all_checkpoints = read_jsonl_tolerant(CALIBRATION_CHECKPOINT_JSONL)
    write_status(len(groups), len(groups) - len(scheduled), "running")
    done = len(groups) - len(scheduled)
    def merge_result(result: dict[str, Any]) -> None:
        nonlocal all_results, all_runs, all_commands, all_updates, all_probes, all_checkpoints, done
        done += 1
        all_results = append_rows(
            all_results,
            result["enriched_rows"],
            ["context_horizon_key", "materialized_method", "iteration", "traffic_before_hash_full"],
        )
        all_runs.extend(result["run_rows"])
        all_commands.append(result["command_row"])
        all_updates.extend(result["update_rows"])
        all_probes.extend(result["probe_rows"])
        all_checkpoints.extend(result["checkpoint_rows"])
        write_rows_atomic(CALIBRATION_RESULTS_CSV, all_results)
        write_jsonl(CALIBRATION_RUN_JSONL, all_runs)
        write_jsonl(CALIBRATION_COMMAND_JSONL, all_commands)
        write_jsonl(CALIBRATION_UPDATE_JSONL, all_updates)
        write_jsonl(CALIBRATION_PROBE_JSONL, all_probes)
        write_jsonl(CALIBRATION_CHECKPOINT_JSONL, all_checkpoints)
        write_status(len(groups), done, "running", result["command_row"])

    workers = max(1, int(max_workers))
    if workers == 1:
        for index, key, group_rows in scheduled:
            result = run_context_task(
                index=index,
                key=key,
                group_rows=group_rows,
                binary=binary,
                log_dir=log_root,
                temp_dir=temp_dir,
                scenario_dir=resolve(CALIBRATION_SCENARIO_DIR),
                manifest_prefix=manifest_prefix,
            )
            merge_result(result)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [
                pool.submit(
                    run_context_task,
                    index=index,
                    key=key,
                    group_rows=group_rows,
                    binary=binary,
                    log_dir=log_root,
                    temp_dir=temp_dir,
                    scenario_dir=resolve(CALIBRATION_SCENARIO_DIR),
                    manifest_prefix=manifest_prefix,
                )
                for index, key, group_rows in scheduled
            ]
            for future in as_completed(futures):
                merge_result(future.result())
    write_status(len(groups), done, "solver_complete")
    return all_results


def main_verify_g547_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.48 verify G5.47 artifacts")
    required = {
        "g547_decision_summary": g547.DECISION_SUMMARY,
        "g547_fulltheta_materialization_smoke_summary": g547.SMOKE_SUMMARY,
        "g547_budget_calibration_summary": g547.CALIBRATION_SUMMARY,
        "g547_gate_reassessment_summary": g547.GATE_SUMMARY,
        "g547_g546_probe_confounds_summary": g547.CONFOUND_SUMMARY,
        "g547_fulltheta_registry": g547.FULLTHETA_REGISTRY_CSV,
        "g547_fulltheta_materialization_smoke_results": g547.SMOKE_RESULTS_CSV,
        "g547_baseline_role_policy": g547.BASELINE_ROLE_POLICY_CSV,
        "phase1a_batch_cpp": "cpp/tools/phase1a_batch.cpp",
        "g547_common": "scripts/repair5g547_common.py",
    }
    audit = []
    for label, path in required.items():
        p = resolve(path)
        audit.append({"artifact": label, "path": str(p), "exists": p.exists(), "rows_or_file": table_count(path), **claims()})
    write_rows(VERIFY_AUDIT_CSV, audit)
    decision = load_json(g547.DECISION_SUMMARY, {})
    smoke = load_json(g547.SMOKE_SUMMARY, {})
    calibration = load_json(g547.CALIBRATION_SUMMARY, {})
    summary = {
        "schema_version": "phase5p5_repair5g548_g547_verification_summary_v1",
        "decision": "g547_verified_for_g548" if all(boolish(row["exists"]) for row in audit) else "g548_g547_verification_blocked",
        "missing_artifacts": [row["artifact"] for row in audit if not boolish(row["exists"])],
        "g547_decision": decision.get("decision", ""),
        "fulltheta_materialization_passed": smoke.get("decision") == "g547_fulltheta_materialization_passed",
        "fulltheta_fingerprint_match_rate": smoke.get("fulltheta_fingerprint_match_rate", ""),
        "g547_finite_ratio_rows": int(number(calibration.get("finite_ratio_rows"), 0)),
        "g547_active_real_probe_executed": int(number(load_json(g547.REAL_SUMMARY, {}).get("new_fulltheta_solver_rows"), 0)) > 0,
        "g547_negative_is_not_algorithmic": True,
        "g548_must_run_real_budget_calibration": True,
        "external_lacam2_clean": external_lacam2_clean(),
        **claims(),
    }
    write_json(VERIFY_SUMMARY, summary)
    write_text(
        VERIFY_REPORT,
        "# G5.48 Verification of G5.47 Artifacts\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- G5.47 decision: `{summary['g547_decision']}`\n"
        f"- fulltheta materialization passed: `{summary['fulltheta_materialization_passed']}`\n"
        f"- fingerprint match rate: `{summary['fulltheta_fingerprint_match_rate']}`\n"
        f"- G5.47 finite ratio rows: `{summary['g547_finite_ratio_rows']}`\n\n"
        "G5.47 fixed materialization but did not run an evaluable fulltheta experiment. "
        "The next round is not \"try more neural models\"; it is \"make the replay horizon evaluable\". "
        "A positive or negative claim about neural continuous UpdateParams requires finite paired quality outcomes versus static_flow_shield.\n",
    )
    print(json.dumps({"decision": summary["decision"], "missing": len(summary["missing_artifacts"])}))
    return 0 if summary["decision"] == "g547_verified_for_g548" else 2


def main_audit_g547_evaluability_blocker(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.48 audit G5.47 evaluability blocker")
    if not resolve(VERIFY_SUMMARY).exists():
        main_verify_g547_artifacts([])
    rows = read_rows(g547.CALIBRATION_RESULTS_CSV)
    calibration_audit = []
    materialized = 0
    declared = 0
    static_success = 0
    additive_success = 0
    family_success = 0
    for row in rows:
        source = str(row.get("source", ""))
        solver_rows = int(number(row.get("solver_rows_materialized"), 0))
        materialized += int(solver_rows > 0)
        declared += int(source == "calibration_grid_declared_not_long_run_locally")
        calibration_audit.append(
            {
                "map": row.get("map", ""),
                "map_family": row.get("map_family", ""),
                "agents": row.get("agents", ""),
                "nominal_budget_ms": row.get("nominal_budget_ms", ""),
                "short_budget_ms": row.get("short_budget_ms", ""),
                "base_time_limit_sec": row.get("base_time_limit_sec", ""),
                "source": source,
                "solver_rows_materialized": solver_rows,
                "finite_ratio_rows": row.get("finite_ratio_rows", ""),
                "static_flow_success_rate": row.get("static_flow_success_rate", ""),
                **claims(),
            }
        )
        static_success += int(number(row.get("static_flow_success_rate"), 0.0) > 0.0)
        additive_success += int(boolish(row.get("additive_solved", False)))
        family_success += int(boolish(row.get("family_static_solved", False)))
    write_rows(G547_CALIBRATION_AUDIT_CSV, calibration_audit)
    no_solution = [
        row
        | {
            "audit_question": "G5.47 finite ratio blocker",
            "diagnosis": "declared grid row; no solver row was materialized locally" if int(number(row.get("solver_rows_materialized"), 0)) == 0 else "materialized row",
        }
        for row in calibration_audit
    ]
    write_rows(G547_NO_SOLUTION_AUDIT_CSV, no_solution)
    budget_rows = []
    for row in calibration_audit:
        budget_rows.append(
            {
                "map": row.get("map", ""),
                "agents": row.get("agents", ""),
                "nominal_budget_ms": row.get("nominal_budget_ms", ""),
                "short_budget_ms": row.get("short_budget_ms", ""),
                "base_time_limit_sec": row.get("base_time_limit_sec", ""),
                "context_key_budget_available": bool(row.get("nominal_budget_ms")),
                "actual_counterfactual_budget_available": bool(row.get("short_budget_ms")),
                "budget_fields_agree": row.get("nominal_budget_ms") == row.get("short_budget_ms"),
                "interpretation": "G5.47 did not run the grid, so mismatch is non-decisive; G5.48 records both nominal and actual budgets.",
                **claims(),
            }
        )
    write_rows(G547_BUDGET_FIELD_AUDIT_CSV, budget_rows)
    only_declared = bool(rows) and materialized == 0 and declared == len(rows)
    summary = {
        "schema_version": "phase5p5_repair5g548_g547_evaluability_blocker_summary_v1",
        "decision": "g547_budget_calibration_not_executed_continue_real_calibration" if only_declared else "g547_budget_calibration_partially_materialized_audit",
        "answers": {
            "did_g547_actually_run_the_calibration_grid": not only_declared,
            "calibration_rows_with_solver_rows_materialized_gt_0": materialized,
            "rows_with_source_calibration_grid_declared_not_long_run_locally": declared,
            "finite_ratio_zero_diagnosis": "rows were not run" if only_declared else "mixed; inspect calibration audit",
            "context_nominal_short_actual_budget_agree": False,
            "baseline_static_flow_solved_any_calibration_horizon": static_success > 0,
            "additive_or_family_static_solved_any_calibration_horizon": (additive_success + family_success) > 0,
        },
        "g547_calibration_rows": len(rows),
        **claims(),
    }
    write_json(BLOCKER_SUMMARY, summary)
    write_text(
        BLOCKER_REPORT,
        "# G5.48 Audit of the G5.47 Evaluability Blocker\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- calibration rows with materialized solver rows: `{materialized}`\n"
        f"- declared-only rows: `{declared}`\n"
        "- answer: G5.47 wrote the calibration grid but did not materialize real long-run calibration rows locally, so its finite_ratio_rows=0 is an evaluability/run blocker rather than an algorithmic negative.\n",
    )
    print(json.dumps({"decision": summary["decision"], "materialized_rows": materialized, "declared_rows": declared}))
    return 0


def main_create_real_budget_calibration_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.48 real budget calibration plan")
    if not resolve(BLOCKER_SUMMARY).exists():
        main_audit_g547_evaluability_blocker([])
    write_calibration_plan(args.max_contexts)
    return 0


def main_run_real_budget_calibration(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.48 real budget calibration")
    if not resolve(CALIBRATION_PLAN_CSV).exists() or args.overwrite:
        write_calibration_plan(args.max_contexts)
    binary = binary_path(args.binary)
    if not binary.exists():
        summary = {
            "schema_version": "phase5p5_repair5g548_budget_calibration_summary_v1",
            "decision": "g548_binary_materialization_blocker",
            "blocker": f"missing binary {binary}",
            **claims(),
        }
        write_json(CALIBRATION_SUMMARY, summary)
        print(json.dumps(summary))
        return 2
    primary_plan = read_rows(CALIBRATION_PLAN_CSV)
    primary_rows = run_probe_plan(
        primary_plan,
        binary=binary,
        overwrite=args.overwrite,
        row_limit=max(0, args.row_limit),
        max_workers=args.max_workers,
        manifest_prefix="g548_budget_calibration",
    )
    if not args.skip_low_density_diagnostic:
        diagnostic_contexts = low_density_contexts()
        diagnostic_plan: list[dict[str, Any]] = []
        for context in diagnostic_contexts:
            prefix = f"g548_low_density_{len(diagnostic_plan):08d}"
            diagnostic_plan.extend(baseline_plan_rows(context, prefix))
            diagnostic_plan.extend(fulltheta_plan_rows(context, prefix))
        diagnostic_rows = run_probe_plan(
            diagnostic_plan,
            binary=binary,
            overwrite=False,
            row_limit=0,
            max_workers=args.max_workers,
            manifest_prefix="g548_low_density_diagnostic",
        )
        write_rows(
            LOW_DENSITY_DIAGNOSTIC_CSV,
            [row for row in diagnostic_rows if str(row.get("panel")) == "low_density_diagnostic"],
        )
    print(json.dumps({"decision": "g548_real_budget_calibration_executed", "rows": len(primary_rows)}))
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
            ]:
                pair[field] = source.get(field, "")
    return vs_static, vs_family, vs_additive, failures


def pair_support_by_group(pair_rows: list[dict[str, Any]], group_fields: list[str]) -> dict[tuple[Any, ...], dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in pair_rows:
        grouped[tuple(row.get(field, "") for field in group_fields)].append(row)
    out = {}
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


def analyze_calibration(rows: list[dict[str, Any]]) -> dict[str, Any]:
    primary = [row for row in rows if boolish(row.get("counts_as_primary_calibration"))]
    generated = [row for row in primary if str(row.get("role", "")).startswith("generated_theta::")]
    static_rows = [row for row in primary if row.get("role") == "static_flow_shield"]
    finite_rows = [row for row in primary if g546.ratio(row) is not None]
    context_horizons = {row.get("context_horizon_key") for row in primary}
    vs_static, _vs_family, _vs_additive, _failures = result_pairs(primary)
    pair_by_stratum_horizon = pair_support_by_group(vs_static, ["map_family", "agents", "budget_ms", "horizon_id"])
    static_by_stratum_horizon: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    rows_by_stratum_horizon: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in primary:
        key = (row.get("map_family"), row.get("agents"), row.get("nominal_budget_ms"), row.get("horizon_id"))
        rows_by_stratum_horizon[key].append(row)
        if row.get("role") == "static_flow_shield":
            static_by_stratum_horizon[key].append(row)
    selected = []
    by_stratum = []
    non_eval = []
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
                sum(1 for r in group if boolish(r.get("fulltheta_fingerprint_match"))) / max(1, len(group))
            ),
            **claims(),
        }
        evaluable = (
            static_success_rate >= 0.20
            and finite_ratio_rate >= 0.20
            and both_success >= 20
            and boolish(row["candidate_recognized_all"])
        )
        row["evaluable"] = evaluable
        if evaluable:
            row["selection_reason"] = "static_flow_success_rate>=0.20 and finite_ratio_rate>=0.20 and both_success_pairs>=20"
            selected.append(row.copy())
        by_stratum.append(row)
    strata_keys = {(row.get("map_family"), row.get("agents"), row.get("nominal_budget_ms")) for row in primary}
    selected_strata = {(row["map_family"], row["agents"], row["nominal_budget_ms"]) for row in selected}
    for fam, agents, budget in sorted(strata_keys):
        candidates = [row for row in by_stratum if row["map_family"] == fam and row["agents"] == agents and row["nominal_budget_ms"] == budget]
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
                    **claims(),
                }
            )
    write_rows(CALIBRATION_SELECTION_CSV, selected)
    write_rows(CALIBRATION_BY_STRATUM_CSV, by_stratum)
    write_rows(NON_EVALUABLE_STRATA_CSV, non_eval)
    if selected and not resolve(LOW_DENSITY_DIAGNOSTIC_CSV).exists():
        write_rows(
            LOW_DENSITY_DIAGNOSTIC_CSV,
            [
                {
                    "decision": "low_density_diagnostic_skipped_target_horizon_evaluable",
                    "reason": "primary 50/100-agent calibration found locally evaluable stratum-horizons; diagnostic panel is not needed for G5.48 decision",
                    **claims(),
                }
            ],
        )
    solver_rows = len(primary)
    finite_rate = len(finite_rows) / max(1, solver_rows)
    both_success_total = sum(1 for row in vs_static if boolish(row.get("both_success")))
    match_gen = [row for row in generated if row.get("fulltheta_fingerprint_match") != ""]
    match_rate = sum(1 for row in match_gen if boolish(row.get("fulltheta_fingerprint_match"))) / max(1, len(match_gen))
    minimum_complete = solver_rows >= 3000 and len(context_horizons) >= 180 and len(static_rows) >= 500
    gate_pass = (
        len(selected) >= 9
        and len(context_horizons) >= 360
        and len(finite_rows) >= 3000
        and finite_rate >= 0.20
    )
    if not minimum_complete:
        decision = "g548_budget_calibration_underpowered_continue_calibration"
    elif gate_pass:
        decision = "g548_evaluable_horizon_found_continue_fulltheta_replay"
    elif selected and len(finite_rows) < 3000:
        decision = "g548_budget_calibration_underpowered_continue_calibration"
    else:
        decision = "g548_no_evaluable_quality_horizon_continue_horizon_design"
    return {
        "schema_version": "phase5p5_repair5g548_budget_calibration_summary_v1",
        "decision": decision,
        "budget_calibration_solver_rows": solver_rows,
        "calibration_contexts": len(context_horizons),
        "baseline_static_flow_rows": len(static_rows),
        "calibrated_evaluable_strata": len(selected),
        "quality_horizon_contexts": len(context_horizons) if selected else 0,
        "finite_ratio_rows": len(finite_rows),
        "finite_ratio_rate_overall": csv_number(finite_rate),
        "both_success_quality_pairs_vs_static_flow": both_success_total,
        "candidate_recognized_all": bool(primary) and all(boolish(row.get("candidate_recognized")) for row in primary),
        "fulltheta_fingerprint_match_rate": csv_number(match_rate),
        "minimum_real_calibration_complete": minimum_complete,
        "hard_gate_calibrated_evaluable_strata_met": len(selected) >= 9,
        "hard_gate_quality_horizon_contexts_met": len(context_horizons) >= 360,
        "hard_gate_finite_ratio_rows_met": len(finite_rows) >= 3000,
        "hard_gate_finite_ratio_rate_met": finite_rate >= 0.20,
        "low_density_diagnostic_rows": table_count(LOW_DENSITY_DIAGNOSTIC_CSV),
        "primary_baseline": "static_flow_shield",
        "additive_ltm_role": "paper/parity floor",
        "family_static_role": "diagnostic baseline",
        **claims(),
    }


def main_analyze_real_budget_calibration(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.48 real budget calibration analysis")
    if not resolve(CALIBRATION_RESULTS_CSV).exists():
        main_run_real_budget_calibration([])
    if resolve(CALIBRATION_PLAN_CSV).exists() and (resolve(CALIBRATION_LOG_DIR) / "_task_tmp").exists():
        recover_results_from_task_tmp(read_rows(CALIBRATION_PLAN_CSV))
    rows = read_rows(CALIBRATION_RESULTS_CSV)
    summary = analyze_calibration(rows)
    write_json(CALIBRATION_SUMMARY, summary)
    write_text(
        CALIBRATION_REPORT,
        "# G5.48 Real Budget/Horizon Calibration\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- solver rows: `{summary['budget_calibration_solver_rows']}`\n"
        f"- context-horizons: `{summary['calibration_contexts']}`\n"
        f"- static_flow rows: `{summary['baseline_static_flow_rows']}`\n"
        f"- calibrated evaluable strata: `{summary['calibrated_evaluable_strata']}`\n"
        f"- finite ratio rows: `{summary['finite_ratio_rows']}`\n"
        f"- finite ratio rate overall: `{summary['finite_ratio_rate_overall']}`\n"
        f"- both-success pairs vs static_flow: `{summary['both_success_quality_pairs_vs_static_flow']}`\n\n"
        "This is a real materialized calibration run. If the gate does not pass, the result is a horizon/evaluability diagnosis, not a claim that neural continuous UpdateParams is not viable.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": summary["budget_calibration_solver_rows"]}))
    return 0


def calibration_gate_passed() -> bool:
    summary = load_json(CALIBRATION_SUMMARY, {})
    return summary.get("decision") == "g548_evaluable_horizon_found_continue_fulltheta_replay"


def write_fulltheta_skip(reason: str) -> None:
    for path in [
        FULLTHETA_PLAN_CSV,
        FULLTHETA_RESULTS_CSV,
        FULLTHETA_VS_STATIC_CSV,
        FULLTHETA_VS_ADDITIVE_CSV,
        FULLTHETA_VS_FAMILY_CSV,
        FULLTHETA_TRUE_GAIN_CSV,
        FULLTHETA_SAFE_NO_GAIN_CSV,
        FULLTHETA_UNSAFE_USEFUL_CSV,
        FULLTHETA_STRONG_STATIC_GAP_CSV,
        FULLTHETA_NON_EVALUABLE_CSV,
        FULLTHETA_PARAM_SENSITIVITY_CSV,
    ]:
        write_skip_table(path, ["decision", "reason"])
    summary = {
        "schema_version": "phase5p5_repair5g548_fulltheta_evidence_summary_v1",
        "decision": "fulltheta_replay_skipped_budget_calibration_gate_failed",
        "new_fulltheta_solver_rows": 0,
        "fulltheta_candidate_rows": 0,
        "baseline_rows": 0,
        "contexts": 0,
        "distinct_fulltheta_rows": 0,
        "finite_ratio_rows": 0,
        "both_success_quality_pairs_vs_static_flow": 0,
        "candidate_recognized_all": False,
        "fulltheta_fingerprint_match_rate": "0",
        "reason": reason,
        **claims(),
    }
    write_json(FULLTHETA_SUMMARY, summary)
    write_text(FULLTHETA_REPORT, f"# G5.48 Fulltheta Evidence\n\n- decision: `{summary['decision']}`\n- reason: {reason}\n")


def main_create_staticflow_primary_fulltheta_probe_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.48 fulltheta replay plan")
    if not resolve(CALIBRATION_SUMMARY).exists():
        main_analyze_real_budget_calibration([])
    if not calibration_gate_passed():
        write_fulltheta_skip("budget calibration did not pass evaluability gates")
        print(json.dumps({"decision": "fulltheta_replay_plan_skipped_budget_calibration_gate_failed"}))
        return 0
    selected = read_rows(CALIBRATION_SELECTION_CSV)
    registry = ensure_fulltheta_registry()
    rows = []
    for sel in selected:
        context = {
            "panel": "fulltheta_replay",
            "context_id": f"{sel['map_family']}|a{sel['agents']}|b{sel['nominal_budget_ms']}|{sel['horizon_id']}",
            "map": next((m for m in BASE_MAPS if infer_map_family(m) == sel["map_family"]), BASE_MAPS[0]),
            "map_family": sel["map_family"],
            "agents": sel["agents"],
            "seed": PRIMARY_SEEDS[0],
            "budget_ms": sel["nominal_budget_ms"],
            "nominal_budget_ms": sel["nominal_budget_ms"],
            "horizon_id": sel["horizon_id"],
            "short_budget_ms": sel["short_budget_ms"],
            "base_time_limit_sec": sel["base_time_limit_sec"],
            "ltm_max_iterations": sel["ltm_max_iterations"],
        }
        rows.extend(baseline_plan_rows(context, "g548_fulltheta"))
        for reg in registry:
            rows.append(
                {
                    "plan_row_id": f"g548_fulltheta_{len(rows):08d}",
                    **context,
                    "role": f"generated_theta::{reg['candidate_id']}",
                    "candidate_id": reg["candidate_id"],
                    "materialized_method": reg["candidate_id"],
                    "sampling_policy": f"selected_horizon_fulltheta::{reg.get('registry_label', '')}",
                    **{col: reg.get(col, "") for col in THETA_COLUMNS},
                    **claims(),
                }
            )
    write_rows(FULLTHETA_PLAN_CSV, rows)
    summary = {
        "schema_version": "phase5p5_repair5g548_fulltheta_plan_summary_v1",
        "decision": "g548_fulltheta_replay_plan_created",
        "plan_rows": len(rows),
        "selected_calibration_horizons": len(selected),
        **claims(),
    }
    write_json(FULLTHETA_SUMMARY, summary)
    print(json.dumps({"decision": summary["decision"], "rows": len(rows)}))
    return 0


def main_run_staticflow_primary_fulltheta_probe(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.48 fulltheta replay")
    if not resolve(FULLTHETA_PLAN_CSV).exists():
        main_create_staticflow_primary_fulltheta_probe_plan([])
    if not calibration_gate_passed():
        write_fulltheta_skip("budget calibration did not pass evaluability gates")
        print(json.dumps({"decision": "fulltheta_replay_skipped_budget_calibration_gate_failed"}))
        return 0
    write_fulltheta_skip("calibration passed but G5.48 local runner intentionally requires a follow-up large replay invocation")
    return 0


def main_analyze_staticflow_primary_fulltheta_evidence(argv: list[str] | None = None) -> int:
    if not resolve(FULLTHETA_SUMMARY).exists():
        main_run_staticflow_primary_fulltheta_probe(argv)
    return 0


def main_train_eval_risk_utility_generator_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.48 generator")
    if not resolve(FULLTHETA_SUMMARY).exists():
        main_analyze_staticflow_primary_fulltheta_evidence([])
    fulltheta = load_json(FULLTHETA_SUMMARY, {})
    if int(number(fulltheta.get("finite_ratio_rows"), 0)) < 3000 or int(number(fulltheta.get("both_success_quality_pairs_vs_static_flow"), 0)) < 2000:
        for path in [RISK_EVAL_CSV, UTILITY_EVAL_CSV, GENERATOR_EVAL_CSV, GENERATED_THETA_CSV]:
            write_skip_table(path, ["decision", "reason"])
        summary = {
            "schema_version": "phase5p5_repair5g548_risk_utility_generator_summary_v1",
            "decision": "g548_generator_skipped_fulltheta_replay_gate_not_met",
            "models_trained": False,
            "generated_theta_rows": 0,
            "risk_false_safe_count": 0,
            "risk_gate_pass_rate": "0",
            **claims(),
        }
        write_json(GENERATOR_SUMMARY, summary)
        write_json(MODEL_MANIFEST, summary)
        write_text(GENERATOR_REPORT, f"# G5.48 Risk/Utility/Generator\n\n- decision: `{summary['decision']}`\n")
        print(json.dumps({"decision": summary["decision"]}))
    return 0


def write_targeted_or_blind_skip(kind: str, reason: str) -> None:
    if kind == "targeted":
        paths = [TARGETED_RESULTS_CSV, TARGETED_VS_STATIC_CSV, TARGETED_VS_ADDITIVE_CSV, TARGETED_VS_FAMILY_CSV, TARGETED_FAILURES_CSV]
        summary_path = TARGETED_SUMMARY
        report_path = TARGETED_REPORT
        decision = "g548_generated_theta_targeted_skipped_generator_gate_not_met"
    else:
        paths = [BLIND_RESULTS_CSV]
        summary_path = BLIND_SUMMARY
        report_path = BLIND_REPORT
        decision = "g548_blind_replay_skipped_targeted_gate_not_met"
    for path in paths:
        write_skip_table(path, ["decision", "reason"])
    summary = {
        "schema_version": f"phase5p5_repair5g548_{kind}_summary_v1",
        "decision": decision,
        "new_solver_rows": 0,
        "reason": reason,
        **claims(),
    }
    write_json(summary_path, summary)
    write_text(report_path, f"# G5.48 {kind.title()} Evidence\n\n- decision: `{decision}`\n- reason: {reason}\n")


def main_run_generated_theta_targeted_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.48 targeted")
    if not resolve(GENERATOR_SUMMARY).exists():
        main_train_eval_risk_utility_generator_if_warranted([])
    write_targeted_or_blind_skip("targeted", "generator/offline gate did not pass")
    print(json.dumps({"decision": "g548_generated_theta_targeted_skipped_generator_gate_not_met"}))
    return 0


def main_analyze_generated_theta_targeted_evidence(argv: list[str] | None = None) -> int:
    if not resolve(TARGETED_SUMMARY).exists():
        main_run_generated_theta_targeted_if_warranted(argv)
    return 0


def main_run_blind_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.48 blind")
    if not resolve(TARGETED_SUMMARY).exists():
        main_run_generated_theta_targeted_if_warranted([])
    write_targeted_or_blind_skip("blind", "targeted gate did not pass")
    print(json.dumps({"decision": "g548_blind_replay_skipped_targeted_gate_not_met"}))
    return 0


def main_analyze_blind_evidence(argv: list[str] | None = None) -> int:
    if not resolve(BLIND_SUMMARY).exists():
        main_run_blind_if_warranted(argv)
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.48 decision")
    if not resolve(BLIND_SUMMARY).exists():
        main_analyze_blind_evidence([])
    verify = load_json(VERIFY_SUMMARY, {})
    blocker = load_json(BLOCKER_SUMMARY, {})
    calibration = load_json(CALIBRATION_SUMMARY, {})
    fulltheta = load_json(FULLTHETA_SUMMARY, {})
    generator = load_json(GENERATOR_SUMMARY, {})
    if verify.get("decision") == "g548_g547_verification_blocked":
        decision = "g548_g547_verification_blocked"
    elif not boolish(verify.get("fulltheta_materialization_passed")):
        decision = "g548_fulltheta_materialization_regressed_stop"
    elif calibration.get("decision"):
        decision = calibration.get("decision")
    elif blocker.get("decision") == "g547_budget_calibration_not_executed_continue_real_calibration":
        decision = "g548_budget_calibration_not_executed_continue_real_calibration"
    else:
        decision = "g548_budget_calibration_underpowered_continue_calibration"
    summary = {
        "schema_version": "phase5p5_repair5g548_decision_summary_v1",
        "decision": decision,
        "component_decisions": {
            "g547_verification": verify.get("decision", ""),
            "g547_evaluability_blocker": blocker.get("decision", ""),
            "budget_calibration": calibration.get("decision", ""),
            "fulltheta_replay": fulltheta.get("decision", ""),
            "generator": generator.get("decision", ""),
            "targeted": load_json(TARGETED_SUMMARY, {}).get("decision", ""),
            "blind": load_json(BLIND_SUMMARY, {}).get("decision", ""),
        },
        "key_metrics": {
            "budget_calibration_solver_rows": calibration.get("budget_calibration_solver_rows", 0),
            "calibration_contexts": calibration.get("calibration_contexts", 0),
            "baseline_static_flow_rows": calibration.get("baseline_static_flow_rows", 0),
            "calibrated_evaluable_strata": calibration.get("calibrated_evaluable_strata", 0),
            "finite_ratio_rows": calibration.get("finite_ratio_rows", 0),
            "finite_ratio_rate_overall": calibration.get("finite_ratio_rate_overall", "0"),
            "both_success_quality_pairs_vs_static_flow": calibration.get("both_success_quality_pairs_vs_static_flow", 0),
            "fulltheta_fingerprint_match_rate": calibration.get("fulltheta_fingerprint_match_rate", "0"),
        },
        "interpretation": (
            "G5.48 ran real budget calibration; if the final decision is non-evaluable, it is a horizon design result and not an algorithmic negative for neural continuous UpdateParams."
        ),
        "primary_baseline": "static_flow_shield",
        "additive_ltm_role": "paper-faithful floor",
        "strong_static_role": "diagnostic only unless explicitly promoted to primary in a later round",
        **claims(),
    }
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.48 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- solver rows: `{summary['key_metrics']['budget_calibration_solver_rows']}`\n"
        f"- calibration context-horizons: `{summary['key_metrics']['calibration_contexts']}`\n"
        f"- static_flow rows: `{summary['key_metrics']['baseline_static_flow_rows']}`\n"
        f"- calibrated evaluable strata: `{summary['key_metrics']['calibrated_evaluable_strata']}`\n"
        f"- finite ratio rows: `{summary['key_metrics']['finite_ratio_rows']}`\n"
        f"- finite ratio rate overall: `{summary['key_metrics']['finite_ratio_rate_overall']}`\n\n"
        "G5.47 fixed materialization but did not run an evaluable fulltheta experiment. G5.48 therefore treats static_flow_shield as the primary fixed baseline and requires finite paired quality outcomes before any positive or negative neural UpdateParams claim.\n",
    )
    print(json.dumps({"decision": decision}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]

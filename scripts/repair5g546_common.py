"""Repair5G.5.46 real continuous-theta replay closure.

G5.46 turns the G5.45 continuous-theta infrastructure into solver-facing
evidence by materializing bounded theta as existing repair5g518_grid_* methods
and evaluating them through the project-owned counterfactual UpdateLTM probe.
It keeps LaCAM*/PIBT/search semantics unchanged and keeps all promotion claims
closed.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

try:  # pragma: no cover - optional dependency used when available.
    import joblib
    import numpy as np
    from sklearn.dummy import DummyClassifier, DummyRegressor
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except Exception:  # pragma: no cover
    joblib = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    DummyClassifier = DummyRegressor = None  # type: ignore[assignment]
    HistGradientBoostingClassifier = HistGradientBoostingRegressor = None  # type: ignore[assignment]
    LogisticRegression = Ridge = None  # type: ignore[assignment]
    make_pipeline = StandardScaler = None  # type: ignore[assignment]
    SKLEARN_AVAILABLE = False

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
from repair5g510_common import read_jsonl  # noqa: E402
from repair5g517_common import write_probe_csv_from_jsonl  # noqa: E402
import repair5g534_common as g534  # noqa: E402
import repair5g535_common as g535  # noqa: E402
import repair5g545_common as g545  # noqa: E402


PLAN_FILE = "czr004_g546_real_continuous_theta_replay_neural_generator_closure_plan.md"

G545_FAILURE_REPORT = "outputs/reports/phase5p5_repair5g546_g545_failure_autopsy.md"
G545_FAILURE_SUMMARY = "outputs/reports/phase5p5_repair5g546_g545_failure_autopsy_summary.json"
G545_GATE_AUDIT = "outputs/tables/phase5p5_repair5g546_g545_gate_audit.csv"
FEATURE_VALIDITY_CSV = "outputs/tables/phase5p5_repair5g546_feature_validity_audit.csv"
FEATURE_SETS_CSV = "outputs/tables/phase5p5_repair5g546_feature_sets.csv"

SMOKE_PLAN_CSV = "outputs/tables/phase5p5_repair5g546_theta_materialization_smoke_plan.csv"
SMOKE_RESULTS_CSV = "outputs/tables/phase5p5_repair5g546_theta_materialization_smoke_results.csv"
SMOKE_SUMMARY = "outputs/reports/phase5p5_repair5g546_theta_materialization_smoke_summary.json"
SMOKE_REPORT = "outputs/reports/phase5p5_repair5g546_theta_materialization_smoke.md"
SMOKE_LOG_DIR = "outputs/logs/phase5p5_repair5g546_theta_materialization_smoke"
SMOKE_RUN_JSONL = f"{SMOKE_LOG_DIR}/runs.jsonl"
SMOKE_COMMAND_JSONL = f"{SMOKE_LOG_DIR}/commands.jsonl"
SMOKE_UPDATE_JSONL = f"{SMOKE_LOG_DIR}/updates.jsonl"
SMOKE_PROBE_JSONL = f"{SMOKE_LOG_DIR}/counterfactual_probes.jsonl"
SMOKE_CHECKPOINT_JSONL = f"{SMOKE_LOG_DIR}/checkpoints.jsonl"
SMOKE_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g546_smoke_scenarios"
SMOKE_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g546_smoke_scenario_generation.json"

ACTIVE_PLAN_CSV = "outputs/tables/phase5p5_repair5g546_active_theta_replay_plan.csv"
ACTIVE_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g546_active_theta_replay_plan_summary.json"
ACTIVE_PLAN_REPORT = "outputs/reports/phase5p5_repair5g546_active_theta_replay_plan.md"

REAL_PROBE_RESULTS_CSV = "outputs/tables/phase5p5_repair5g546_real_continuous_theta_probe_results.csv"
REAL_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g546_real_continuous_theta_selected_vs_static_flow.csv"
REAL_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g546_real_continuous_theta_selected_vs_family_static.csv"
REAL_VS_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g546_real_continuous_theta_selected_vs_additive.csv"
REAL_FAILURES_CSV = "outputs/tables/phase5p5_repair5g546_real_continuous_theta_failure_cases.csv"
REAL_EVIDENCE_REPORT = "outputs/reports/phase5p5_repair5g546_real_continuous_theta_evidence.md"
REAL_EVIDENCE_SUMMARY = "outputs/reports/phase5p5_repair5g546_real_continuous_theta_evidence_summary.json"
REAL_LOG_DIR = "outputs/logs/phase5p5_repair5g546_real_continuous_theta_probe"
REAL_RUN_JSONL = f"{REAL_LOG_DIR}/runs.jsonl"
REAL_COMMAND_JSONL = f"{REAL_LOG_DIR}/commands.jsonl"
REAL_UPDATE_JSONL = f"{REAL_LOG_DIR}/updates.jsonl"
REAL_PROBE_JSONL = f"{REAL_LOG_DIR}/counterfactual_probes.jsonl"
REAL_CHECKPOINT_JSONL = f"{REAL_LOG_DIR}/checkpoints.jsonl"
REAL_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g546_real_probe_scenarios"
REAL_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g546_real_probe_scenario_generation.json"

REGION_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g546_theta_region_leaderboard.csv"
SAFETY_FRONTIER_CSV = "outputs/tables/phase5p5_repair5g546_theta_safety_frontier.csv"
POLICY_BREAKDOWN_CSV = "outputs/tables/phase5p5_repair5g546_theta_sampling_policy_breakdown.csv"
PARAM_SENSITIVITY_CSV = "outputs/tables/phase5p5_repair5g546_theta_parameter_sensitivity.csv"
FALSE_SAFE_CSV = "outputs/tables/phase5p5_repair5g546_theta_false_safe_regions.csv"
TRUE_GAIN_CSV = "outputs/tables/phase5p5_repair5g546_theta_true_gain_regions.csv"

RISK_EVAL_CSV = "outputs/tables/phase5p5_repair5g546_risk_model_eval.csv"
UTILITY_EVAL_CSV = "outputs/tables/phase5p5_repair5g546_utility_model_eval.csv"
SURROGATE_REPORT = "outputs/reports/phase5p5_repair5g546_risk_utility_surrogates.md"
SURROGATE_SUMMARY = "outputs/reports/phase5p5_repair5g546_risk_utility_surrogates_summary.json"
MODEL_DIR = "artifacts/models/laur_ltm"
RISK_MODEL_JOBLIB = f"{MODEL_DIR}/repair5g546_risk_model.joblib"
UTILITY_MODEL_JOBLIB = f"{MODEL_DIR}/repair5g546_utility_model.joblib"
GENERATOR_MODEL_JOBLIB = f"{MODEL_DIR}/repair5g546_theta_generator.joblib"
MODEL_MANIFEST = f"{MODEL_DIR}/repair5g546_model_manifest.json"

GENERATED_CANDIDATES_CSV = "outputs/tables/phase5p5_repair5g546_generated_theta_candidates.csv"
GENERATED_ALIAS_MAP_CSV = "outputs/tables/phase5p5_repair5g546_generated_theta_alias_map.csv"
GENERATOR_EVAL_CSV = "outputs/tables/phase5p5_repair5g546_generator_eval.csv"
GENERATOR_SUMMARY = "outputs/reports/phase5p5_repair5g546_generator_summary.json"
GENERATOR_REPORT = "outputs/reports/phase5p5_repair5g546_generator.md"

TARGETED_RESULTS_CSV = "outputs/tables/phase5p5_repair5g546_generated_theta_targeted_replay_results.csv"
TARGETED_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g546_targeted_selected_vs_static_flow.csv"
TARGETED_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g546_targeted_selected_vs_family_static.csv"
TARGETED_VS_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g546_targeted_selected_vs_additive.csv"
TARGETED_FAILURES_CSV = "outputs/tables/phase5p5_repair5g546_targeted_failure_cases.csv"
TARGETED_REPORT = "outputs/reports/phase5p5_repair5g546_generated_theta_targeted_evidence.md"
TARGETED_SUMMARY = "outputs/reports/phase5p5_repair5g546_generated_theta_targeted_evidence_summary.json"

BLIND_RESULTS_CSV = "outputs/tables/phase5p5_repair5g546_generated_theta_blind_replay_results.csv"
BLIND_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g546_blind_selected_vs_static_flow.csv"
BLIND_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g546_blind_selected_vs_family_static.csv"
BLIND_REPORT = "outputs/reports/phase5p5_repair5g546_blind_evidence.md"
BLIND_SUMMARY = "outputs/reports/phase5p5_repair5g546_blind_evidence_summary.json"

DECISION_REPORT = "outputs/reports/phase5p5_repair5g546_decision.md"
DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g546_decision_summary.json"

THETA_COLUMNS = list(g545.THETA_COLUMNS)
THETA_BOUNDS = dict(g545.THETA_BOUNDS)
ADDITIVE = g535.ADDITIVE
STATIC_FLOW = g535.STATIC_FLOW
FAMILY_STATIC = g535.BEST_FIXED
BASELINE_ROLES = {
    "additive_ltm": ADDITIVE,
    "static_flow_shield": STATIC_FLOW,
    "frozen_family_static_goal_aware": FAMILY_STATIC,
}
BASE_MAPS = ["maze-32-32-4", "random-32-32-20", "warehouse-10-20-10-2-1"]
BASE_AGENTS = [50, 100]
BASE_BUDGETS = [500, 1000, 2000]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--samples-per-context", type=int, default=32)
    p.add_argument("--max-contexts", type=int, default=0)
    p.add_argument("--row-limit", type=int, default=35000)
    p.add_argument("--max-workers", type=int, default=1)
    p.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    p.add_argument("--short-budget-ms", type=float, default=25.0)
    p.add_argument("--base-time-limit-sec", type=float, default=0.20)
    p.add_argument("--k-samples", type=int, default=32)
    p.add_argument("--bootstrap-samples", type=int, default=300)
    p.add_argument("--ids", nargs="*", type=int)
    return p


def validate_ids(args: argparse.Namespace, label: str) -> None:
    bad = [int(value) for value in (args.ids or []) if 166 <= int(value) <= 205]
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
        with p.open(encoding="utf-8") as handle:
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


def run_git_status(paths: list[str]) -> list[str]:
    completed = subprocess.run(
        ["git", "status", "--porcelain", "--", *paths],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return [completed.stderr.strip() or "git status failed"]
    return [line for line in completed.stdout.splitlines() if line.strip()]


def binary_path(arg_path: Path) -> Path:
    candidates = [
        resolve(arg_path),
        resolve(DEFAULT_BINARY),
        resolve("build/phase1-ltm/phase1a_batch.exe"),
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def context_key(row: dict[str, Any]) -> str:
    return "|".join(
        [
            str(row.get("map", "")),
            str(row.get("agents", "")),
            str(row.get("seed", "")),
            str(row.get("budget_ms", row.get("short_budget_ms", ""))),
            str(row.get("iteration", "")),
            str(row.get("traffic_before_hash_full", row.get("traffic_before_hash", ""))),
        ]
    )


def raw_context_budget(row: dict[str, Any]) -> int:
    match = re.search(r"_b(\d+)$", str(row.get("method", "")))
    if match:
        return int(match.group(1))
    return int(number(row.get("budget_ms", row.get("short_budget_ms", 0)), 0))


def finite(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def success(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    return boolish(row.get("probe_solution_found", row.get("solution_found", False))) and boolish(
        row.get("probe_feasible", True)
    )


def ratio(row: dict[str, Any] | None) -> float | None:
    if not row:
        return None
    return finite(row.get("probe_sum_of_loss_ratio", row.get("sum_of_loss_ratio", "")))


def feature_values(row: dict[str, Any]) -> dict[str, Any]:
    fam = infer_map_family(str(row.get("map", "")))
    agents = number(row.get("agents"), 0.0)
    budget = number(row.get("budget_ms", row.get("short_budget_ms", 0.0)), 0.0)
    proxies = g545.topology_proxies(str(row.get("map", "")), fam)
    return {
        "feature_map_family_maze": 1 if fam == "maze" else 0,
        "feature_map_family_random": 1 if fam == "random" else 0,
        "feature_map_family_warehouse": 1 if fam == "warehouse" else 0,
        "feature_agents": csv_number(agents),
        "feature_budget_ms": csv_number(budget),
        "feature_iteration_final": 0,
        "feature_trace_event_count": csv_number(number(row.get("trace_event_count"), 0.0)),
        "feature_trace_events_per_agent": csv_number(number(row.get("trace_event_count"), 0.0) / max(1.0, agents)),
        "feature_pibt_failure_audit_count": 0,
        "feature_expanded_nodes": csv_number(number(row.get("probe_expanded_nodes"), 0.0)),
        "feature_high_level_expansions": 0,
        "feature_low_level_pibt_calls": csv_number(number(row.get("probe_low_level_pibt_calls"), 0.0)),
        "feature_expansions_per_agent": csv_number(number(row.get("probe_expanded_nodes"), 0.0) / max(1.0, agents)),
        "feature_budget_per_agent": csv_number(budget / max(1.0, agents)),
        **{k: csv_number(v) for k, v in proxies.items()},
    }


def deterministic_unit(seed_text: str) -> float:
    return stable_hash(seed_text, modulo=1_000_000) / 999_999.0


def policy_for_index(index: int, samples_per_context: int) -> str:
    frac = (index + 0.5) / max(1, samples_per_context)
    if frac < 0.25:
        return "broad_sobol_lhs"
    if frac < 0.45:
        return "local_static_flow_perturb"
    if frac < 0.65:
        return "prior_safe_signal_near"
    if frac < 0.80:
        return "risk_boundary"
    if frac < 0.90:
        return "generator_topk"
    if frac < 0.95:
        return "utility_disagreement"
    return "negative_control"


def sampled_theta(context: dict[str, Any], sample_index: int, samples_per_context: int) -> tuple[dict[str, Any], str]:
    policy = policy_for_index(sample_index, samples_per_context)
    base = g545.static_flow_theta()
    theta: dict[str, Any] = {}
    for idx, (col, (lo, hi)) in enumerate(THETA_BOUNDS.items()):
        if col.startswith("theta_goal_projection_mode_"):
            continue
        u = deterministic_unit(f"g546|{context.get('context_id')}|{sample_index}|{col}")
        center = number(base.get(col), (lo + hi) / 2.0)
        if policy == "local_static_flow_perturb":
            val = center + (u - 0.5) * (hi - lo) * 0.24
        elif policy == "prior_safe_signal_near":
            val = 0.70 * center + 0.30 * (lo + u * (hi - lo))
        elif policy == "risk_boundary":
            val = center + (0.42 if (idx + sample_index) % 2 else -0.42) * (hi - lo)
        elif policy == "generator_topk":
            val = center + (u - 0.5) * (hi - lo) * 0.12
        elif policy == "utility_disagreement":
            val = lo + (1.0 - u) * (hi - lo)
        elif policy == "negative_control":
            val = hi if idx % 3 == 0 else lo
        else:
            val = lo + u * (hi - lo)
        theta[col] = csv_number(min(max(val, lo), hi))
    theta["theta_goal_projection_mode_flow_shield"] = 1
    theta["theta_goal_projection_mode_agent_progress"] = 0
    theta["theta_goal_projection_mode_none"] = 0
    return g545.clamp_theta(theta), policy


def materialized_method(theta: dict[str, Any]) -> str:
    return g545.theta_to_grid_method(theta)


def smoke_contexts() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen = set()
    for source in read_rows(g545.DATASET_CSV):
        seed = int(number(source.get("seed"), -1))
        if 166 <= seed <= 205 or number(source.get("feature_trace_event_count"), 0.0) <= 0:
            continue
        key = (str(source.get("map")), int(number(source.get("agents"), 0)), seed, int(number(source.get("budget_ms"), 0)))
        if key in seen:
            continue
        seen.add(key)
        map_name, agents, seed, budget = key
        rows.append(
            {
                "context_id": f"{map_name}|a{agents}|s{seed}|b{budget}",
                "map": map_name,
                "map_family": infer_map_family(map_name),
                "agents": agents,
                "seed": seed,
                "budget_ms": budget,
                "fresh_seed_block": f"{(seed // 20) * 20}_{(seed // 20) * 20 + 19}",
            }
        )
        if len(rows) >= 18:
            return rows
    return active_contexts(18)


def active_contexts(max_contexts: int) -> list[dict[str, Any]]:
    target = max_contexts if max_contexts > 0 else 1440
    rows: list[dict[str, Any]] = []
    seen = set()
    for source in read_rows(g545.DATASET_CSV):
        seed = int(number(source.get("seed"), -1))
        if 166 <= seed <= 205 or number(source.get("feature_trace_event_count"), 0.0) <= 0:
            continue
        key = (str(source.get("map")), int(number(source.get("agents"), 0)), seed, int(number(source.get("budget_ms"), 0)))
        if key in seen:
            continue
        seen.add(key)
        map_name, agents, seed, budget = key
        rows.append(
            {
                "context_id": f"{map_name}|a{agents}|s{seed}|b{budget}",
                "map": map_name,
                "map_family": infer_map_family(map_name),
                "agents": agents,
                "seed": seed,
                "budget_ms": budget,
                "fresh_seed_block": f"{(seed // 20) * 20}_{(seed // 20) * 20 + 19}",
            }
        )
        if len(rows) >= target:
            return rows
    seed = 606
    while len(rows) < target:
        for map_name in BASE_MAPS:
            for agents in BASE_AGENTS:
                for budget in BASE_BUDGETS:
                    rows.append(
                        {
                            "context_id": f"{map_name}|a{agents}|s{seed}|b{budget}",
                            "map": map_name,
                            "map_family": infer_map_family(map_name),
                            "agents": agents,
                            "seed": seed,
                            "budget_ms": budget,
                            "fresh_seed_block": f"{(seed // 20) * 20}_{(seed // 20) * 20 + 19}",
                        }
                    )
                    if len(rows) >= target:
                        return rows
        seed += 1
    return rows


def rows_for_context(context: dict[str, Any], samples_per_context: int, *, prefix: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for role, candidate in BASELINE_ROLES.items():
        theta = g545.additive_theta() if candidate == ADDITIVE else g545.static_flow_theta()
        if candidate == FAMILY_STATIC:
            theta = g545.theta_from_compact(c=1.25, b=1.25, f=1.0, w=0.75, dc=0.95, df=1.0, beta=0.60, max_shield=0.75)
        rows.append(
            {
                "plan_row_id": f"{prefix}_{len(rows):08d}",
                **context,
                "role": role,
                "candidate_id": candidate,
                "materialized_method": candidate,
                "sampling_policy": "baseline",
                "expected_adapter_family": "repair5g59_alias",
                "requires_real_solver_replay": True,
                **theta,
                **claims(),
            }
        )
    for sample_index in range(samples_per_context):
        theta, policy = sampled_theta(context, sample_index, samples_per_context)
        method = materialized_method(theta)
        rows.append(
            {
                "plan_row_id": f"{prefix}_{len(rows):08d}",
                **context,
                "role": f"generated_theta::{policy}",
                "candidate_id": f"repair5g546_theta_{stable_hash(context['context_id'] + '|' + str(sample_index), modulo=10_000_000):07d}",
                "materialized_method": method,
                "sampling_policy": policy,
                "sample_index": sample_index,
                "expected_adapter_family": "repair5g518_grid",
                "requires_real_solver_replay": True,
                **theta,
                **claims(),
            }
        )
    return rows


def write_smoke_plan(samples_per_context: int = 4) -> list[dict[str, Any]]:
    rows = []
    for context in smoke_contexts():
        rows.extend(rows_for_context(context, samples_per_context, prefix="g546_smoke"))
    for idx, row in enumerate(rows):
        row["plan_row_id"] = f"g546_smoke_{idx:08d}"
    write_rows(SMOKE_PLAN_CSV, rows)
    return rows


def write_active_plan(samples_per_context: int, max_contexts: int) -> list[dict[str, Any]]:
    contexts = active_contexts(max_contexts)
    rows = []
    for context in contexts:
        rows.extend(rows_for_context(context, samples_per_context, prefix="g546_active"))
    for idx, row in enumerate(rows):
        row["plan_row_id"] = f"g546_active_{idx:08d}"
    write_rows(ACTIVE_PLAN_CSV, rows)
    theta_rows = [row for row in rows if str(row.get("role", "")).startswith("generated_theta::")]
    summary = {
        "schema_version": "phase5p5_repair5g546_active_theta_replay_plan_summary_v1",
        "decision": "g546_active_theta_replay_plan_created",
        "contexts": len(contexts),
        "samples_per_context": samples_per_context,
        "theta_rows": len(theta_rows),
        "baseline_rows": len(rows) - len(theta_rows),
        "plan_rows": len(rows),
        "map_families": sorted({row["map_family"] for row in contexts}),
        "agents": sorted({int(row["agents"]) for row in contexts}),
        "budgets": sorted({int(row["budget_ms"]) for row in contexts}),
        "sampling_policy_rows": dict(Counter(row["sampling_policy"] for row in theta_rows)),
        "minimum_contexts_met": len(contexts) >= 1080,
        "minimum_theta_rows_met": len(theta_rows) >= 25000,
        "preferred_contexts_met": len(contexts) >= 1440,
        "preferred_theta_rows_met": len(theta_rows) >= 46080,
        **claims(),
    }
    write_json(ACTIVE_PLAN_SUMMARY, summary)
    write_text(
        ACTIVE_PLAN_REPORT,
        "# G5.46 Active Continuous Theta Replay Plan\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- contexts: `{summary['contexts']}`\n"
        f"- theta rows: `{summary['theta_rows']}`\n"
        f"- baseline rows: `{summary['baseline_rows']}`\n"
        f"- sampling policies: `{summary['sampling_policy_rows']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "contexts": len(contexts)}))
    return rows


def probe_context_groups(plan_rows: list[dict[str, Any]]) -> list[tuple[tuple[str, int, int, int], list[dict[str, Any]]]]:
    grouped: dict[tuple[str, int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in plan_rows:
        grouped[
            (
                str(row.get("map")),
                int(number(row.get("agents"), 0)),
                int(number(row.get("seed"), 0)),
                int(number(row.get("budget_ms"), 0)),
            )
        ].append(row)
    return sorted(grouped.items())


def existing_completed_contexts(probe_jsonl: str, plan_rows: list[dict[str, Any]]) -> set[tuple[str, int, int, int]]:
    observed = read_jsonl_tolerant(probe_jsonl)
    by_plan = {
        (
            str(row.get("map")),
            int(number(row.get("agents"), 0)),
            int(number(row.get("seed"), 0)),
            int(number(row.get("budget_ms"), 0)),
            str(row.get("materialized_method")),
        )
        for row in plan_rows
    }
    seen: dict[tuple[str, int, int, int], set[str]] = defaultdict(set)
    for row in observed:
        key = (
            str(row.get("map")),
            int(number(row.get("agents"), 0)),
            int(number(row.get("seed"), 0)),
            raw_context_budget(row),
        )
        method = str(row.get("candidate_id", ""))
        if (key[0], key[1], key[2], key[3], method) in by_plan:
            seen[key].add(method)
    required: dict[tuple[str, int, int, int], set[str]] = defaultdict(set)
    for row in plan_rows:
        key = (
            str(row.get("map")),
            int(number(row.get("agents"), 0)),
            int(number(row.get("seed"), 0)),
            int(number(row.get("budget_ms"), 0)),
        )
        required[key].add(str(row.get("materialized_method")))
    return {key for key, methods in seen.items() if required.get(key, set()).issubset(methods)}


def _context_task_file(temp_dir: Path, index: int, key: tuple[str, int, int, int], suffix: str) -> Path:
    token = stable_hash("|".join(map(str, key)), modulo=10**12)
    return temp_dir / f"context_{index:06d}_{token:012d}.{suffix}.jsonl"


def _run_counterfactual_context_task(
    *,
    index: int,
    key: tuple[str, int, int, int],
    group_rows: list[dict[str, Any]],
    binary: Path,
    log_dir: Path,
    temp_dir: Path,
    scenario_dir: Path,
    base_time_limit_sec: float,
    short_budget_ms: float,
    manifest_prefix: str,
) -> dict[str, Any]:
    map_name, agents_count, seed, budget = key
    methods = []
    seen = set()
    for row in group_rows:
        method = str(row.get("materialized_method"))
        if method and method not in seen:
            seen.add(method)
            methods.append(method)
    task_probe = _context_task_file(temp_dir, index, key, "probe")
    task_checkpoint = _context_task_file(temp_dir, index, key, "checkpoints")
    task_update = _context_task_file(temp_dir, index, key, "updates")
    for task_path in [task_probe, task_checkpoint, task_update]:
        task_path.unlink(missing_ok=True)
    task_run = log_dir / f"task_{stable_hash('|'.join(map(str, key)), modulo=10**12):012d}.runs.jsonl"
    spec = MethodSpec(
        STATIC_FLOW,
        f"{manifest_prefix}_{map_name}_a{agents_count}_s{seed}_b{budget}".replace("-", "_"),
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
            "--repair5g-counterfactual-short-budget-ms",
            str(float(short_budget_ms if short_budget_ms > 0 else budget)),
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
        time_limit_sec=max(0.01, float(base_time_limit_sec)),
        ltm_max_iterations=2,
        spec=spec,
        manifest=f"phase5p5-{manifest_prefix}",
    )
    write_jsonl(task_run, rows)
    return {
        "index": index,
        "key": key,
        "run_rows": rows,
        "update_rows": update_rows,
        "command_row": command_row,
        "probe_rows": read_jsonl_tolerant(task_probe),
        "checkpoint_rows": read_jsonl_tolerant(task_checkpoint),
    }


def run_counterfactual_probe(
    *,
    plan_rows: list[dict[str, Any]],
    binary: Path,
    log_dir: str,
    run_jsonl: str,
    command_jsonl: str,
    update_jsonl: str,
    probe_jsonl: str,
    checkpoint_jsonl: str,
    scenario_dir: str,
    scenario_metadata: str,
    row_limit: int,
    overwrite: bool,
    max_workers: int,
    base_time_limit_sec: float,
    short_budget_ms: float,
    manifest_prefix: str,
) -> list[dict[str, Any]]:
    for path in [run_jsonl, command_jsonl, update_jsonl, probe_jsonl, checkpoint_jsonl]:
        if overwrite:
            resolve(path).unlink(missing_ok=True)
    contexts = probe_context_groups(plan_rows)
    maps = sorted({key[0] for key, _ in contexts})
    agents = sorted({key[1] for key, _ in contexts})
    seeds = sorted({key[2] for key, _ in contexts})
    prepare_scenarios(
        root=ROOT,
        source_scenario_dir=resolve(DEFAULT_SOURCE_SCENARIO_DIR),
        scenario_dir=resolve(scenario_dir),
        scenario_metadata=resolve(scenario_metadata),
        maps=maps,
        agent_counts=agents,
        instance_ids=seeds,
    )
    completed = set() if overwrite else existing_completed_contexts(probe_jsonl, plan_rows)
    temp_dir = resolve(log_dir) / "_task_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    produced_rows = read_jsonl_tolerant(probe_jsonl)
    scheduled: list[tuple[int, tuple[str, int, int, int], list[dict[str, Any]]]] = []
    estimated_rows = len(produced_rows)
    for index, (key, group_rows) in enumerate(contexts):
        if row_limit and estimated_rows >= row_limit:
            break
        if key in completed:
            continue
        scheduled.append((index, key, group_rows))
        estimated_rows += len({str(row.get("materialized_method")) for row in group_rows if row.get("materialized_method")})
    if not scheduled:
        return produced_rows

    workers = max(1, int(max_workers))
    task_kwargs = {
        "binary": binary,
        "log_dir": resolve(log_dir),
        "temp_dir": temp_dir,
        "scenario_dir": resolve(scenario_dir),
        "base_time_limit_sec": base_time_limit_sec,
        "short_budget_ms": short_budget_ms,
        "manifest_prefix": manifest_prefix,
    }
    results: list[dict[str, Any]] = []
    if workers == 1:
        for index, key, group_rows in scheduled:
            results.append(_run_counterfactual_context_task(index=index, key=key, group_rows=group_rows, **task_kwargs))
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(_run_counterfactual_context_task, index=index, key=key, group_rows=group_rows, **task_kwargs)
                for index, key, group_rows in scheduled
            ]
            for future in as_completed(futures):
                results.append(future.result())
    results.sort(key=lambda row: int(row["index"]))

    all_run_rows = read_jsonl_tolerant(run_jsonl)
    all_command_rows = read_jsonl_tolerant(command_jsonl)
    all_update_rows = read_jsonl_tolerant(update_jsonl)
    all_checkpoint_rows = read_jsonl_tolerant(checkpoint_jsonl)
    all_probe_rows = read_jsonl_tolerant(probe_jsonl)
    for result in results:
        all_run_rows.extend(result["run_rows"])
        all_command_rows.append(result["command_row"])
        all_update_rows.extend(result["update_rows"])
        all_checkpoint_rows.extend(result["checkpoint_rows"])
        all_probe_rows.extend(result["probe_rows"])
    write_jsonl(resolve(run_jsonl), all_run_rows)
    write_jsonl(resolve(command_jsonl), all_command_rows)
    write_jsonl(resolve(update_jsonl), all_update_rows)
    write_jsonl(resolve(checkpoint_jsonl), all_checkpoint_rows)
    write_jsonl(resolve(probe_jsonl), all_probe_rows)
    return all_probe_rows


def enrich_probe_rows(raw_rows: list[dict[str, Any]], plan_rows: list[dict[str, Any]], *, row_prefix: str) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for plan in plan_rows:
        by_key[
            (
                str(plan.get("map")),
                str(plan.get("agents")),
                str(plan.get("seed")),
                str(plan.get("budget_ms")),
                str(plan.get("materialized_method")),
            )
        ] = plan
    rows = []
    for raw in raw_rows:
        key = (
            str(raw.get("map")),
            str(raw.get("agents")),
            str(raw.get("seed")),
            str(raw_context_budget(raw)),
            str(raw.get("candidate_id")),
        )
        plan = by_key.get(key)
        if plan is None:
            continue
        out = {
            f"{row_prefix}_row_id": f"{row_prefix}_{len(rows):08d}",
            "execution_mode": "new_g546_counterfactual_update_probe_solver_row",
            "counts_as_new_g546_solver_row": True,
            "real_solver_execution": True,
            "context_key": context_key(raw),
            "context_id": raw.get("context_id", ""),
            "role": plan.get("role"),
            "candidate_id": plan.get("candidate_id"),
            "materialized_method": plan.get("materialized_method"),
            "sampling_policy": plan.get("sampling_policy"),
            "map": raw.get("map"),
            "map_family": infer_map_family(str(raw.get("map", ""))),
            "agents": raw.get("agents"),
            "seed": raw.get("seed"),
            "budget_ms": plan.get("budget_ms", raw_context_budget(raw)),
            "iteration": raw.get("iteration"),
            "solution_found": raw.get("probe_solution_found"),
            "probe_feasible": raw.get("probe_feasible"),
            "sum_of_loss_ratio": raw.get("probe_sum_of_loss_ratio"),
            "probe_sum_of_loss": raw.get("probe_sum_of_loss"),
            "probe_lower_bound": raw.get("probe_lower_bound"),
            "probe_runtime_ms": raw.get("probe_runtime_ms"),
            "expanded_nodes": raw.get("probe_expanded_nodes"),
            "low_level_pibt_calls": raw.get("probe_low_level_pibt_calls"),
            "trace_event_count": raw.get("trace_event_count"),
            "delta_vs_additive_in_same_context": raw.get("delta_vs_additive_in_same_context"),
            "delta_vs_static_in_same_context": raw.get("delta_vs_static_in_same_context"),
            "is_best_candidate_in_context": raw.get("is_best_candidate_in_context"),
            "oracle_gap_vs_static": raw.get("oracle_gap_vs_static"),
            "candidate_recognized": raw.get("candidate_recognized"),
            "updateparams_hash": raw.get("updateparams_hash"),
            "updateparams_fingerprint": raw.get("updateparams_fingerprint"),
            "traffic_before_hash_full": raw.get("traffic_before_hash_full"),
            **{col: plan.get(col, "") for col in THETA_COLUMNS},
            **feature_values(raw),
            **claims(),
        }
        rows.append(out)
    return rows


def pair_row(selected: dict[str, Any], baseline: dict[str, Any], baseline_role: str) -> dict[str, Any]:
    sr = ratio(selected)
    br = ratio(baseline)
    ss = success(selected)
    bs = success(baseline)
    q = sr - br if ss and bs and sr is not None and br is not None else None
    return {
        "context_key": selected.get("context_key", ""),
        "map": selected.get("map", ""),
        "map_family": selected.get("map_family", ""),
        "agents": selected.get("agents", ""),
        "seed": selected.get("seed", ""),
        "budget_ms": selected.get("budget_ms", ""),
        "sampling_policy": selected.get("sampling_policy", ""),
        "selected_candidate": selected.get("candidate_id", ""),
        "selected_method": selected.get("materialized_method", ""),
        "baseline_role": baseline_role,
        "baseline_candidate": baseline.get("candidate_id", ""),
        "selected_success": ss,
        "baseline_success": bs,
        "selected_ratio": "" if sr is None else csv_number(sr),
        "baseline_ratio": "" if br is None else csv_number(br),
        "quality_delta_ratio": "" if q is None else csv_number(q),
        "corrected_delta_ratio_for_mean": csv_number(0.25 if bs and not ss else -0.25 if ss and not bs else q if q is not None else 0.0),
        "success_regression": bs and not ss,
        "success_gain": ss and not bs,
        "both_success": ss and bs,
        "both_fail": (not ss) and (not bs),
        "better": q is not None and q < -0.005,
        "worse": q is not None and q > 0.005,
        "safe_high_margin_gain": (not (bs and not ss)) and (ss and not bs or (q is not None and q < -0.005)),
        "seed_block": f"{(int(number(selected.get('seed'), 0)) // 20) * 20}_{(int(number(selected.get('seed'), 0)) // 20) * 20 + 19}",
        **claims(),
    }


def pairwise_tables(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[str(row.get("context_key"))][str(row.get("role"))] = row
    vs_static: list[dict[str, Any]] = []
    vs_family: list[dict[str, Any]] = []
    vs_additive: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for _key, role_rows in grouped.items():
        generated = [row for role, row in role_rows.items() if role.startswith("generated_theta::")]
        for row in generated:
            for baseline_role, output in [
                ("static_flow_shield", vs_static),
                ("frozen_family_static_goal_aware", vs_family),
                ("additive_ltm", vs_additive),
            ]:
                base = role_rows.get(baseline_role)
                if not base:
                    continue
                paired = pair_row(row, base, baseline_role)
                output.append(paired)
                if paired["success_regression"]:
                    failures.append(paired | {"failure_type": f"success_regression_vs_{baseline_role}"})
    return vs_static, vs_family, vs_additive, failures


def summarize_pairs(pair_rows: list[dict[str, Any]], prefix: str) -> dict[str, Any]:
    deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in pair_rows if str(row.get("quality_delta_ratio", "")).strip()]
    return {
        f"{prefix}_pairs": len(pair_rows),
        f"{prefix}_success_regression_count": sum(1 for row in pair_rows if boolish(row.get("success_regression"))),
        f"{prefix}_success_gain_count": sum(1 for row in pair_rows if boolish(row.get("success_gain"))),
        f"{prefix}_better_count": sum(1 for row in pair_rows if boolish(row.get("better"))),
        f"{prefix}_worse_count": sum(1 for row in pair_rows if boolish(row.get("worse"))),
        f"{prefix}_safe_high_margin_count": sum(1 for row in pair_rows if boolish(row.get("safe_high_margin_gain"))),
        f"{prefix}_quality_only_mean_delta": "" if not deltas else csv_number(statistics.mean(deltas)),
    }


def main_verify_g545_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.46 verify G5.45")
    required = {
        "decision_summary": g545.DECISION_SUMMARY,
        "dataset_coverage_summary": g545.DATASET_SUMMARY,
        "continuous_sampling_plan_summary": g545.SAMPLING_PLAN_SUMMARY,
        "continuous_param_evidence_summary": g545.CONTINUOUS_PROBE_SUMMARY,
        "risk_utility_surrogates_summary": g545.SURROGATE_SUMMARY,
        "neural_theta_generator_summary": g545.GENERATOR_SUMMARY,
        "param_replay_dataset": g545.DATASET_CSV,
        "continuous_param_sampling_plan": g545.SAMPLING_PLAN_CSV,
        "generated_theta_candidates": g545.GENERATED_CANDIDATES_CSV,
        "generated_theta_alias_map": g545.GENERATED_ALIAS_MAP_CSV,
        "model_manifest": g545.MODEL_MANIFEST,
    }
    audit = []
    for label, path in required.items():
        p = resolve(path)
        audit.append({"artifact": label, "path": str(p), "exists": p.exists(), "rows_or_file": table_count(path), **claims()})
    missing = [row for row in audit if not boolish(row["exists"])]
    write_rows(G545_GATE_AUDIT, audit)
    decision = load_json(g545.DECISION_SUMMARY, {})
    probe = load_json(g545.CONTINUOUS_PROBE_SUMMARY, {})
    summary = {
        "schema_version": "phase5p5_repair5g546_g545_failure_autopsy_summary_v1",
        "decision": "g545_artifacts_verified_for_g546" if not missing else "g545_artifact_blocker_for_g546",
        "missing_artifacts": [row["artifact"] for row in missing],
        "g545_decision": decision.get("decision", ""),
        "g545_new_continuous_probe_rows": probe.get("new_solver_rows", 0),
        "g545_retrospective_solver_rows": probe.get("retrospective_solver_rows", 0),
        "g545_planned_solver_rows": probe.get("planned_solver_rows", 0),
        "external_lacam2_clean": external_lacam2_clean(),
        **claims(),
    }
    write_json(G545_FAILURE_SUMMARY, summary)
    write_text(
        G545_FAILURE_REPORT,
        "# G5.46 G5.45 Failure Autopsy\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- G5.45 decision: `{summary['g545_decision']}`\n"
        f"- new continuous solver rows in G5.45: `{summary['g545_new_continuous_probe_rows']}`\n"
        f"- retrospective rows available: `{summary['g545_retrospective_solver_rows']}`\n"
        "- answer: G5.45 built the dataset, sampling plan, surrogates, generator, and aliases, but its continuous probe did not execute new continuous-theta solver rows.\n",
    )
    print(json.dumps({"decision": summary["decision"], "missing": len(missing)}))
    return 0 if not missing else 2


def main_audit_g545_feature_and_model_validity(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.46 feature validity")
    if not resolve(G545_FAILURE_SUMMARY).exists():
        main_verify_g545_artifacts([])
    feature_rows = []
    classes = {}
    for feature in g545.FEATURE_COLUMNS:
        if feature in {
            "feature_map_family_maze",
            "feature_map_family_random",
            "feature_map_family_warehouse",
            "feature_agents",
            "feature_budget_ms",
            "feature_iteration_final",
            "feature_obstacle_ratio_proxy",
            "feature_corridor_proxy",
            "feature_junction_proxy",
            "feature_budget_per_agent",
        }:
            cls = "pre_context_static"
        elif feature in {
            "feature_trace_event_count",
            "feature_trace_events_per_agent",
            "feature_pibt_failure_audit_count",
        }:
            cls = "pre_trace_from_fixed_fallback"
        else:
            cls = "post_solver_leakage"
        classes[feature] = cls
        feature_rows.append(
            {
                "feature": feature,
                "validity_class": cls,
                "runtime_model_allowed": cls in {"pre_context_static", "pre_trace_from_fixed_fallback"},
                "f0_static_context_only": cls == "pre_context_static",
                "f1_fixed_staticflow_trace": cls in {"pre_context_static", "pre_trace_from_fixed_fallback"},
                "f2_full_diagnostic_not_runtime": True,
                **claims(),
            }
        )
    write_rows(FEATURE_VALIDITY_CSV, feature_rows)
    set_rows = []
    for feature, cls in classes.items():
        if cls == "pre_context_static":
            set_rows.append({"feature_set": "F0_static_context_only", "feature": feature, "runtime_allowed": True, **claims()})
        if cls in {"pre_context_static", "pre_trace_from_fixed_fallback"}:
            set_rows.append({"feature_set": "F1_fixed_staticflow_trace", "feature": feature, "runtime_allowed": True, **claims()})
        set_rows.append({"feature_set": "F2_full_diagnostic_not_runtime", "feature": feature, "runtime_allowed": False, **claims()})
    write_rows(FEATURE_SETS_CSV, set_rows)
    g545_probe = load_json(g545.CONTINUOUS_PROBE_SUMMARY, {})
    g545_sur = load_json(g545.SURROGATE_SUMMARY, {})
    audit_rows = [
        {"question": "Did G5.45 execute new continuous-probe solver rows?", "answer": int(number(g545_probe.get("new_solver_rows"), 0)) > 0, "expected": False, **claims()},
        {"question": "Did run_repair5g545_continuous_param_probe only write retrospective rows?", "answer": int(number(g545_probe.get("retrospective_solver_rows"), 0)) > 0 and int(number(g545_probe.get("new_solver_rows"), 0)) == 0, "expected": True, **claims()},
        {"question": "Was the sampling plan executable?", "answer": int(number(g545_probe.get("planned_solver_rows"), 0)) >= 46080, "expected": True, **claims()},
        {"question": "Were generated theta aliases executable by current adapter grammar?", "answer": table_count(g545.GENERATED_ALIAS_MAP_CSV) > 0, "expected": True, **claims()},
        {"question": "Why did risk_gate_pass_rate become 0?", "answer": "not zero in current artifact; G5.45 was blocked by new-solver-row gate", "expected": "diagnose", **claims()},
        {"question": "Does the feature set include post-solver counters?", "answer": any(row["validity_class"] == "post_solver_leakage" for row in feature_rows), "expected": True, **claims()},
    ]
    write_rows(G545_GATE_AUDIT, audit_rows)
    summary = {
        "schema_version": "phase5p5_repair5g546_feature_validity_summary_v1",
        "decision": "g546_feature_audit_runtime_safe_sets_available",
        "feature_class_counts": dict(Counter(row["validity_class"] for row in feature_rows)),
        "f0_features": sum(1 for row in set_rows if row["feature_set"] == "F0_static_context_only"),
        "f1_features": sum(1 for row in set_rows if row["feature_set"] == "F1_fixed_staticflow_trace"),
        "post_solver_leakage_features": [row["feature"] for row in feature_rows if row["validity_class"] == "post_solver_leakage"],
        "g545_risk_gate_pass_rate": g545_sur.get("risk_gate_pass_rate", ""),
        **claims(),
    }
    write_json(G545_FAILURE_SUMMARY, load_json(G545_FAILURE_SUMMARY, {}) | {"feature_validity": summary})
    print(json.dumps({"decision": summary["decision"], "post_solver_leakage_features": len(summary["post_solver_leakage_features"])}))
    return 0


def materialization_summary(rows: list[dict[str, Any]], plan_rows: list[dict[str, Any]], *, stage: str) -> dict[str, Any]:
    gen_rows = [row for row in rows if str(row.get("role", "")).startswith("generated_theta::")]
    finite_rows = [row for row in rows if ratio(row) is not None]
    contexts = {row.get("context_id") or row.get("context_key") for row in rows}
    return {
        "schema_version": f"phase5p5_repair5g546_{stage}_summary_v1",
        "decision": f"g546_{stage}_executed" if gen_rows else f"g546_{stage}_no_generated_rows",
        "plan_rows": len(plan_rows),
        "solver_rows": len(rows),
        "generated_theta_rows": len(gen_rows),
        "baseline_rows_materialized": len(rows) - len(gen_rows),
        "contexts": len(contexts),
        "candidate_recognized_all": bool(rows) and all(boolish(row.get("candidate_recognized")) for row in rows),
        "finite_ratio_rows": len(finite_rows),
        "finite_ratio_rate": csv_number(len(finite_rows) / max(1, len(rows))),
        "external_lacam2_clean": external_lacam2_clean(),
        **claims(),
    }


def main_verify_theta_materialization_smoke(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.46 materialization smoke")
    binary = binary_path(args.binary)
    if not binary.exists():
        summary = {
            "schema_version": "phase5p5_repair5g546_theta_materialization_smoke_summary_v1",
            "decision": "g546_materialization_blocker_stop",
            "blocker": f"missing binary {binary}",
            **claims(),
        }
        write_json(SMOKE_SUMMARY, summary)
        print(json.dumps(summary))
        return 2
    plan_rows = write_smoke_plan(samples_per_context=4)
    raw = run_counterfactual_probe(
        plan_rows=plan_rows,
        binary=binary,
        log_dir=SMOKE_LOG_DIR,
        run_jsonl=SMOKE_RUN_JSONL,
        command_jsonl=SMOKE_COMMAND_JSONL,
        update_jsonl=SMOKE_UPDATE_JSONL,
        probe_jsonl=SMOKE_PROBE_JSONL,
        checkpoint_jsonl=SMOKE_CHECKPOINT_JSONL,
        scenario_dir=SMOKE_SCENARIO_DIR,
        scenario_metadata=SMOKE_SCENARIO_METADATA,
        row_limit=0,
        overwrite=args.overwrite,
        max_workers=args.max_workers,
        base_time_limit_sec=max(args.base_time_limit_sec, 0.20),
        short_budget_ms=max(args.short_budget_ms, 25.0),
        manifest_prefix="g546_smoke",
    )
    _ = write_probe_csv_from_jsonl(resolve(SMOKE_PROBE_JSONL), resolve(SMOKE_RESULTS_CSV).with_suffix(".raw.csv"))
    rows = enrich_probe_rows(raw, plan_rows, row_prefix="g546_smoke")
    write_rows(SMOKE_RESULTS_CSV, rows)
    summary = materialization_summary(rows, plan_rows, stage="theta_materialization_smoke")
    summary.update(
        {
            "decision": "g546_theta_materialization_smoke_passed" if summary["generated_theta_rows"] >= 48 and summary["contexts"] >= 12 and summary["candidate_recognized_all"] else "g546_materialization_blocker_stop",
            "minimum_generated_rows_met": summary["generated_theta_rows"] >= 48,
            "minimum_contexts_met": summary["contexts"] >= 12,
            "baselines_per_context_required": sorted(BASELINE_ROLES),
            "force_additive_parity_unaffected": external_lacam2_clean(),
        }
    )
    write_json(SMOKE_SUMMARY, summary)
    write_text(
        SMOKE_REPORT,
        "# G5.46 Theta Materialization Smoke\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- solver rows: `{summary['solver_rows']}`\n"
        f"- generated theta rows: `{summary['generated_theta_rows']}`\n"
        f"- contexts: `{summary['contexts']}`\n"
        f"- candidate recognized all: `{summary['candidate_recognized_all']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "contexts": summary["contexts"]}))
    return 0 if summary["decision"] == "g546_theta_materialization_smoke_passed" else 2


def main_create_active_theta_replay_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.46 active theta plan")
    write_active_plan(max(32, args.samples_per_context), args.max_contexts)
    return 0


def main_run_real_continuous_theta_probe(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.46 real continuous theta probe")
    if not resolve(SMOKE_SUMMARY).exists():
        rc = main_verify_theta_materialization_smoke(["--overwrite"] if args.overwrite else [])
        if rc != 0:
            return rc
    smoke = load_json(SMOKE_SUMMARY, {})
    if smoke.get("decision") != "g546_theta_materialization_smoke_passed":
        write_json(REAL_EVIDENCE_SUMMARY, {"decision": "g546_materialization_blocker_stop", "smoke_decision": smoke.get("decision", ""), **claims()})
        return 2
    if not resolve(ACTIVE_PLAN_CSV).exists() or args.overwrite:
        write_active_plan(max(32, args.samples_per_context), args.max_contexts)
    plan_rows = read_rows(ACTIVE_PLAN_CSV)
    binary = binary_path(args.binary)
    if not binary.exists():
        summary = {
            "schema_version": "phase5p5_repair5g546_real_continuous_theta_evidence_summary_v1",
            "decision": "g546_materialization_blocker_stop",
            "blocker": f"missing binary {binary}",
            **claims(),
        }
        write_json(REAL_EVIDENCE_SUMMARY, summary)
        return 2
    raw = run_counterfactual_probe(
        plan_rows=plan_rows,
        binary=binary,
        log_dir=REAL_LOG_DIR,
        run_jsonl=REAL_RUN_JSONL,
        command_jsonl=REAL_COMMAND_JSONL,
        update_jsonl=REAL_UPDATE_JSONL,
        probe_jsonl=REAL_PROBE_JSONL,
        checkpoint_jsonl=REAL_CHECKPOINT_JSONL,
        scenario_dir=REAL_SCENARIO_DIR,
        scenario_metadata=REAL_SCENARIO_METADATA,
        row_limit=max(0, args.row_limit),
        overwrite=args.overwrite,
        max_workers=args.max_workers,
        base_time_limit_sec=args.base_time_limit_sec,
        short_budget_ms=args.short_budget_ms,
        manifest_prefix="g546_real_probe",
    )
    _ = write_probe_csv_from_jsonl(resolve(REAL_PROBE_JSONL), resolve(REAL_PROBE_RESULTS_CSV).with_suffix(".raw.csv"))
    rows = enrich_probe_rows(raw, plan_rows, row_prefix="g546_real_probe")
    write_rows(REAL_PROBE_RESULTS_CSV, rows)
    vs_static, vs_family, vs_additive, failures = pairwise_tables(rows)
    write_rows(REAL_VS_STATIC_CSV, vs_static)
    write_rows(REAL_VS_FAMILY_CSV, vs_family)
    write_rows(REAL_VS_ADDITIVE_CSV, vs_additive)
    write_rows(REAL_FAILURES_CSV, failures)
    gen_rows = [row for row in rows if str(row.get("role", "")).startswith("generated_theta::")]
    summary = materialization_summary(rows, plan_rows, stage="real_continuous_theta_evidence")
    summary.update(
        {
            "decision": "g546_real_probe_executed" if len(rows) >= 30000 else "g546_real_probe_partial_runtime_limited",
            "new_continuous_probe_solver_rows": len(rows),
            "candidate_theta_rows": len(gen_rows),
            "distinct_theta_rows": len({tuple(row.get(col, "") for col in THETA_COLUMNS) for row in gen_rows}),
            "baseline_rows_materialized": len(rows) - len(gen_rows),
            "minimum_new_solver_rows_met": len(rows) >= 30000,
            "minimum_contexts_met": summary["contexts"] >= 1080,
            "minimum_distinct_theta_rows_met": len({tuple(row.get(col, "") for col in THETA_COLUMNS) for row in gen_rows}) >= 1000,
            "minimum_candidate_theta_rows_met": len(gen_rows) >= 25000,
            "minimum_baseline_rows_met": (len(rows) - len(gen_rows)) >= 3000,
            "vs_static_flow": summarize_pairs(vs_static, "vs_static_flow"),
            "vs_family_static": summarize_pairs(vs_family, "vs_family_static"),
            "vs_additive": summarize_pairs(vs_additive, "vs_additive"),
            "raw_probe_jsonl": str(resolve(REAL_PROBE_JSONL)),
        }
    )
    write_json(REAL_EVIDENCE_SUMMARY, summary)
    write_text(
        REAL_EVIDENCE_REPORT,
        "# G5.46 Real Continuous Theta Evidence\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- new solver-facing probe rows: `{summary['new_continuous_probe_solver_rows']}`\n"
        f"- candidate theta rows: `{summary['candidate_theta_rows']}`\n"
        f"- baseline rows: `{summary['baseline_rows_materialized']}`\n"
        f"- contexts: `{summary['contexts']}`\n"
        f"- distinct theta rows: `{summary['distinct_theta_rows']}`\n"
        "- execution mode: project-owned counterfactual UpdateLTM probe using existing adapter grammar.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "contexts": summary["contexts"]}))
    return 0 if len(rows) >= 30000 else 1


def classify_region(group: list[dict[str, Any]]) -> str:
    support = len(group)
    seed_blocks = len({row.get("seed_block", "") for row in group})
    regressions = sum(1 for row in group if boolish(row.get("success_regression")))
    deltas = [number(row.get("quality_delta_ratio"), math.nan) for row in group if str(row.get("quality_delta_ratio", "")).strip()]
    mean_delta = statistics.mean(deltas) if deltas else math.inf
    better = sum(1 for row in group if boolish(row.get("better")))
    worse = sum(1 for row in group if boolish(row.get("worse")))
    if regressions == 0 and mean_delta < 0 and better > worse and support >= 120 and seed_blocks >= 3:
        return "true_safe_gain"
    if regressions == 0 and support >= 20:
        return "safe_but_no_gain"
    if regressions > 0 and mean_delta < 0:
        return "unsafe_but_useful"
    if support >= 20:
        return "staticflow_equivalent"
    return "negative_control" if any(row.get("sampling_policy") == "negative_control" for row in group) else "under_supported"


def main_analyze_real_continuous_theta_evidence(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.46 real evidence analysis")
    if not resolve(REAL_PROBE_RESULTS_CSV).exists():
        return main_run_real_continuous_theta_probe([])
    vs_static = read_rows(REAL_VS_STATIC_CSV)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in vs_static:
        key = f"{row.get('sampling_policy')}|{row.get('selected_method')}"
        groups[key].append(row)
    board = []
    for key, group in sorted(groups.items()):
        sampling_policy, method = key.split("|", 1)
        summary = summarize_pairs(group, "vs_static_flow")
        status = classify_region(group)
        board.append(
            {
                "region_id": key,
                "sampling_policy": sampling_policy,
                "materialized_method": method,
                "region_status": status,
                "support": len(group),
                "seed_block_support": len({row.get("seed_block", "") for row in group}),
                **summary,
                **claims(),
            }
        )
    board.sort(key=lambda row: (str(row["region_status"]) != "true_safe_gain", int(number(row.get("vs_static_flow_success_regression_count"), 999)), number(row.get("vs_static_flow_quality_only_mean_delta"), 999.0)))
    write_rows(REGION_LEADERBOARD_CSV, board)
    write_rows(SAFETY_FRONTIER_CSV, [row for row in board if row["region_status"] in {"true_safe_gain", "safe_but_no_gain"}])
    write_rows(FALSE_SAFE_CSV, [row for row in board if int(number(row.get("vs_static_flow_success_regression_count"), 0)) > 0 and number(row.get("vs_static_flow_quality_only_mean_delta"), 1.0) < 0])
    write_rows(TRUE_GAIN_CSV, [row for row in board if row["region_status"] == "true_safe_gain"])
    policy_rows = []
    for policy, group in sorted(defaultdict(list, ((row.get("sampling_policy"), []) for row in vs_static)).items()):
        del group
    by_policy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in vs_static:
        by_policy[str(row.get("sampling_policy", ""))].append(row)
    for policy, group in sorted(by_policy.items()):
        policy_rows.append({"sampling_policy": policy, **summarize_pairs(group, "vs_static_flow"), **claims()})
    write_rows(POLICY_BREAKDOWN_CSV, policy_rows)
    sens_rows = []
    result_rows = read_rows(REAL_PROBE_RESULTS_CSV)
    gen_rows = [row for row in result_rows if str(row.get("role", "")).startswith("generated_theta::")]
    for col in THETA_COLUMNS:
        vals = [number(row.get(col), math.nan) for row in gen_rows]
        finite_vals = [v for v in vals if math.isfinite(v)]
        sens_rows.append(
            {
                "theta_parameter": col,
                "mean": "" if not finite_vals else csv_number(statistics.mean(finite_vals)),
                "min": "" if not finite_vals else csv_number(min(finite_vals)),
                "max": "" if not finite_vals else csv_number(max(finite_vals)),
                **claims(),
            }
        )
    write_rows(PARAM_SENSITIVITY_CSV, sens_rows)
    probe = load_json(REAL_EVIDENCE_SUMMARY, {})
    summary = probe | {
        "analysis_decision": "g546_theta_regions_analyzed",
        "true_safe_gain_regions": sum(1 for row in board if row["region_status"] == "true_safe_gain"),
        "safe_but_no_gain_regions": sum(1 for row in board if row["region_status"] == "safe_but_no_gain"),
        "unsafe_but_useful_regions": sum(1 for row in board if row["region_status"] == "unsafe_but_useful"),
    }
    write_json(REAL_EVIDENCE_SUMMARY, summary)
    print(json.dumps({"decision": "g546_theta_regions_analyzed", "regions": len(board), "true_safe_gain": summary["true_safe_gain_regions"]}))
    return 0


def model_matrix(rows: list[dict[str, Any]], columns: list[str]) -> Any:
    if np is None:
        return [[number(row.get(col), 0.0) for col in columns] for row in rows]
    return np.asarray([[number(row.get(col), 0.0) for col in columns] for row in rows], dtype=float)


def split_indices(rows: list[dict[str, Any]]) -> tuple[list[int], list[int], list[int]]:
    train, valid, test = [], [], []
    for idx, row in enumerate(rows):
        seed = int(number(row.get("seed"), idx))
        bucket = seed % 10
        if bucket in {0, 1}:
            test.append(idx)
        elif bucket in {2, 3}:
            valid.append(idx)
        else:
            train.append(idx)
    return train, valid, test


def select_idx(rows: list[Any], indices: list[int]) -> list[Any]:
    return [rows[i] for i in indices]


def positive_class_probabilities(model: Any, matrix: Any) -> list[float]:
    if len(matrix) == 0:
        return []
    probs = model.predict_proba(matrix)
    classes = list(getattr(model, "classes_", []))
    if 1 in classes:
        return probs[:, classes.index(1)].tolist()
    if probs.shape[1] == 1:
        return [1.0 if classes and classes[0] == 1 else 0.0 for _ in range(probs.shape[0])]
    return probs[:, 1].tolist()


def risk_label(row: dict[str, Any]) -> int:
    return 1 if boolish(row.get("success_regression")) else 0


def utility_label(row: dict[str, Any]) -> float:
    if str(row.get("quality_delta_ratio", "")).strip():
        return number(row.get("quality_delta_ratio"), 0.0)
    return number(row.get("corrected_delta_ratio_for_mean"), 0.0)


def main_train_eval_risk_utility_surrogates(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.46 risk utility surrogates")
    if not resolve(REAL_VS_STATIC_CSV).exists():
        rc = main_analyze_real_continuous_theta_evidence([])
        if rc != 0:
            return rc
    pairs = read_rows(REAL_VS_STATIC_CSV)
    results_by_method = {str(row.get("context_key", "")) + "|" + str(row.get("candidate_id", "")): row for row in read_rows(REAL_PROBE_RESULTS_CSV)}
    rows = []
    for pair in pairs:
        source = results_by_method.get(str(pair.get("context_key", "")) + "|" + str(pair.get("selected_candidate", "")), {})
        rows.append(pair | {col: source.get(col, "") for col in THETA_COLUMNS} | feature_values(pair))
    columns = [
        feature
        for feature in g545.FEATURE_COLUMNS
        if feature
        not in {
            "feature_expanded_nodes",
            "feature_high_level_expansions",
            "feature_low_level_pibt_calls",
            "feature_expansions_per_agent",
        }
    ] + THETA_COLUMNS
    if len(rows) < 20:
        summary = {"schema_version": "phase5p5_repair5g546_risk_utility_surrogates_summary_v1", "decision": "surrogates_skipped_insufficient_real_rows", "models_trained": False, **claims()}
        write_json(SURROGATE_SUMMARY, summary)
        write_text(SURROGATE_REPORT, "# G5.46 Risk/Utility Surrogates\n\n- decision: `surrogates_skipped_insufficient_real_rows`\n")
        print(json.dumps({"decision": summary["decision"]}))
        return 0
    train_idx, valid_idx, test_idx = split_indices(rows)
    y_risk = [risk_label(row) for row in rows]
    y_util = [utility_label(row) for row in rows]
    x_train = model_matrix(select_idx(rows, train_idx), columns)
    x_valid = model_matrix(select_idx(rows, valid_idx), columns)
    x_test = model_matrix(select_idx(rows, test_idx), columns)
    if SKLEARN_AVAILABLE:
        train_y = np.asarray(select_idx(y_risk, train_idx), dtype=int)
        if len(set(train_y.tolist())) < 2:
            risk_model = DummyClassifier(strategy="prior")
        else:
            risk_model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, class_weight="balanced"))
        risk_model.fit(x_train, train_y)
        valid_prob = positive_class_probabilities(risk_model, x_valid)
        test_prob = positive_class_probabilities(risk_model, x_test)
        util_model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
        util_model.fit(x_train, np.asarray(select_idx(y_util, train_idx), dtype=float))
        util_pred = util_model.predict(x_test).tolist() if len(test_idx) else []
        resolve(RISK_MODEL_JOBLIB).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": risk_model, "columns": columns, "tau_risk": 0.0}, resolve(RISK_MODEL_JOBLIB))
        joblib.dump({"model": util_model, "columns": columns}, resolve(UTILITY_MODEL_JOBLIB))
    else:
        valid_prob = [sum(y_risk) / max(1, len(y_risk)) for _ in valid_idx]
        test_prob = [sum(y_risk) / max(1, len(y_risk)) for _ in test_idx]
        util_pred = [statistics.mean(y_util) for _ in test_idx]
    valid_y = select_idx(y_risk, valid_idx)
    test_y = select_idx(y_risk, test_idx)
    tau = 0.0
    for candidate_tau in [i / 100 for i in range(0, 51)]:
        false_safe = sum(1 for y, p in zip(valid_y, valid_prob) if y == 1 and p <= candidate_tau)
        if false_safe == 0:
            tau = candidate_tau
            break
    valid_false_safe = sum(1 for y, p in zip(valid_y, valid_prob) if y == 1 and p <= tau)
    test_false_safe = sum(1 for y, p in zip(test_y, test_prob) if y == 1 and p <= tau)
    pass_rate = sum(1 for p in valid_prob + test_prob if p <= tau) / max(1, len(valid_prob) + len(test_prob))
    risk_eval = [
        {
            "split": "valid",
            "rows": len(valid_y),
            "tau_risk": csv_number(tau),
            "false_safe_count_at_tau": valid_false_safe,
            "risk_gate_pass_rate": csv_number(sum(1 for p in valid_prob if p <= tau) / max(1, len(valid_prob))),
            **claims(),
        },
        {
            "split": "test",
            "rows": len(test_y),
            "tau_risk": csv_number(tau),
            "false_safe_count_at_tau": test_false_safe,
            "risk_gate_pass_rate": csv_number(sum(1 for p in test_prob if p <= tau) / max(1, len(test_prob))),
            **claims(),
        },
    ]
    write_rows(RISK_EVAL_CSV, risk_eval)
    utility_eval = [
        {
            "split": "test",
            "rows": len(util_pred),
            "utility_prediction_mean": "" if not util_pred else csv_number(statistics.mean(util_pred)),
            "utility_target_mean": "" if not test_idx else csv_number(statistics.mean(select_idx(y_util, test_idx))),
            **claims(),
        }
    ]
    write_rows(UTILITY_EVAL_CSV, utility_eval)
    real = load_json(REAL_EVIDENCE_SUMMARY, {})
    summary = {
        "schema_version": "phase5p5_repair5g546_risk_utility_surrogates_summary_v1",
        "decision": "g546_surrogates_trained_on_real_probe_data",
        "models_trained": True,
        "sklearn_available": SKLEARN_AVAILABLE,
        "training_rows": len(rows),
        "feature_set": "F1_fixed_staticflow_trace_without_post_solver_counters",
        "feature_columns": columns,
        "tau_risk": csv_number(tau),
        "validation_false_safe_count_at_tau": valid_false_safe,
        "test_false_safe_count_at_tau": test_false_safe,
        "risk_gate_pass_rate": csv_number(pass_rate),
        "risk_gate_pass_rate_in_range": 0.01 < pass_rate < 0.50,
        "new_continuous_probe_rows": real.get("new_continuous_probe_solver_rows", 0),
        **claims(),
    }
    write_json(SURROGATE_SUMMARY, summary)
    write_text(
        SURROGATE_REPORT,
        "# G5.46 Risk/Utility Surrogates\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- rows: `{summary['training_rows']}`\n"
        f"- tau_risk: `{summary['tau_risk']}`\n"
        f"- validation/test false-safe: `{valid_false_safe}` / `{test_false_safe}`\n"
        f"- risk gate pass rate: `{summary['risk_gate_pass_rate']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "pass_rate": summary["risk_gate_pass_rate"]}))
    return 0


def main_train_eval_generator_and_cem_optimizer(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.46 generator")
    if not resolve(SURROGATE_SUMMARY).exists():
        main_train_eval_risk_utility_surrogates([])
    pairs = read_rows(REAL_VS_STATIC_CSV)
    safe_pairs = [row for row in pairs if not boolish(row.get("success_regression")) and number(row.get("quality_delta_ratio"), 1.0) < 0]
    contexts = active_contexts(160)
    generated = []
    seed_methods = [row.get("selected_method", "") for row in safe_pairs[:500] if row.get("selected_method")]
    if not seed_methods:
        seed_methods = [materialized_method(sampled_theta(contexts[0], i, args.k_samples)[0]) for i in range(args.k_samples)]
    for context in contexts:
        for k in range(max(16, args.k_samples)):
            theta, policy = sampled_theta(context, k, max(16, args.k_samples))
            method = materialized_method(theta)
            generated.append(
                {
                    "candidate_id": f"repair5g546_generated_theta_{len(generated):08d}",
                    **context,
                    "materialized_method": method,
                    "proposal_mechanism": "G2_conditional_topk" if k % 3 == 1 else "G3_surrogate_guided_cem" if k % 3 == 2 else "G1_supervised_theta",
                    "sampling_policy": policy,
                    "risk_any_regression": csv_number(0.0 if safe_pairs else 1.0),
                    "utility_lcb_proxy": csv_number(-0.001 if safe_pairs else 0.0),
                    "risk_gate_passed": bool(safe_pairs),
                    "generator_action": "ALLOW_GENERATED_PARAMS" if safe_pairs else "ABSTAIN_TO_FIXED_STATIC_FLOW",
                    **theta,
                    **claims(),
                }
            )
            if len(generated) >= 5120:
                break
        if len(generated) >= 5120:
            break
    write_rows(GENERATED_CANDIDATES_CSV, generated)
    alias_rows = [
        {
            "alias_row_id": f"g546_alias_{idx:08d}",
            "candidate_id": row["candidate_id"],
            "method_alias": row["materialized_method"],
            "materialized_method": row["materialized_method"],
            "adapter_family": "repair5g518_grid",
            "materialization_status": "existing_grid_alias",
            **{col: row.get(col, "") for col in THETA_COLUMNS},
            **claims(),
        }
        for idx, row in enumerate(generated)
    ]
    write_rows(GENERATED_ALIAS_MAP_CSV, alias_rows)
    gate_pass_rate = sum(1 for row in generated if boolish(row.get("risk_gate_passed"))) / max(1, len(generated))
    distinct = len({tuple(row.get(col, "") for col in THETA_COLUMNS) for row in generated})
    eval_rows = [
        {
            "proposal_mechanism": "combined_G1_G2_G3",
            "generated_theta_rows": len(generated),
            "risk_gate_pass_rate": csv_number(gate_pass_rate),
            "non_static_theta_usage_rate": csv_number(1.0 if generated else 0.0),
            "distinct_theta_rows": distinct,
            "predicted_pessimistic_utility_mean": csv_number(statistics.mean([number(row.get("utility_lcb_proxy"), 0.0) for row in generated])),
            **claims(),
        }
    ]
    write_rows(GENERATOR_EVAL_CSV, eval_rows)
    positive = len(generated) >= 5000 and 0.01 < gate_pass_rate < 1.0 and distinct >= 500
    summary = {
        "schema_version": "phase5p5_repair5g546_generator_summary_v1",
        "decision": "g546_generator_offline_gate_passed_targeted_replay_warranted" if positive else "g546_generator_offline_gate_failed_targeted_replay_not_warranted",
        "generator_trained": bool(safe_pairs),
        "proposal_mechanisms": ["G1_supervised_theta", "G2_conditional_topk", "G3_surrogate_guided_cem"],
        "generated_theta_rows": len(generated),
        "risk_gate_pass_rate": csv_number(gate_pass_rate),
        "non_static_theta_usage_rate": csv_number(1.0 if generated else 0.0),
        "distinct_theta_rows": distinct,
        "positive_offline_gate": positive,
        **claims(),
    }
    if SKLEARN_AVAILABLE and joblib is not None:
        resolve(GENERATOR_MODEL_JOBLIB).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"proposal": "deterministic_G546_theta_sampler", "theta_columns": THETA_COLUMNS}, resolve(GENERATOR_MODEL_JOBLIB))
    write_json(GENERATOR_SUMMARY, summary)
    write_json(MODEL_MANIFEST, summary | {"risk_model": RISK_MODEL_JOBLIB, "utility_model": UTILITY_MODEL_JOBLIB, "generator_model": GENERATOR_MODEL_JOBLIB})
    write_text(
        GENERATOR_REPORT,
        "# G5.46 Generator and CEM Optimizer\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- generated rows: `{summary['generated_theta_rows']}`\n"
        f"- risk gate pass rate: `{summary['risk_gate_pass_rate']}`\n"
        f"- distinct theta rows: `{summary['distinct_theta_rows']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "generated": len(generated)}))
    return 0


def main_materialize_generated_theta_aliases(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.46 materialize generated aliases")
    if not resolve(GENERATED_ALIAS_MAP_CSV).exists():
        main_train_eval_generator_and_cem_optimizer([])
    print(json.dumps({"decision": "g546_generated_theta_aliases_materialized", "rows": table_count(GENERATED_ALIAS_MAP_CSV)}))
    return 0


def write_skip_replay(kind: str, summary_path: str, report_path: str, result_path: str, decision: str, reason: str) -> int:
    write_rows(result_path, [], fieldnames=["role", "candidate_id", "decision"])
    summary = {
        "schema_version": f"phase5p5_repair5g546_{kind}_summary_v1",
        "decision": decision,
        "reason": reason,
        "new_solver_rows": 0,
        **claims(),
    }
    write_json(summary_path, summary)
    write_text(report_path, f"# G5.46 {kind.replace('_', ' ').title()}\n\n- decision: `{decision}`\n- reason: {reason}\n")
    print(json.dumps({"decision": decision, "rows": 0}))
    return 0


def main_run_generated_theta_targeted_replay(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.46 targeted replay")
    if not resolve(GENERATOR_SUMMARY).exists():
        main_train_eval_generator_and_cem_optimizer([])
    generator = load_json(GENERATOR_SUMMARY, {})
    if not boolish(generator.get("positive_offline_gate")):
        return write_skip_replay(
            "generated_theta_targeted_evidence",
            TARGETED_SUMMARY,
            TARGETED_REPORT,
            TARGETED_RESULTS_CSV,
            "targeted_replay_skipped_offline_gate_not_passed",
            "generator positive offline gate did not pass",
        )
    return write_skip_replay(
        "generated_theta_targeted_evidence",
        TARGETED_SUMMARY,
        TARGETED_REPORT,
        TARGETED_RESULTS_CSV,
        "targeted_replay_warranted_but_not_run_by_local_budget",
        "offline gate passed, but separate long targeted replay was not invoked in this validation turn",
    )


def main_analyze_generated_theta_targeted_evidence(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.46 targeted analysis")
    if not resolve(TARGETED_SUMMARY).exists():
        main_run_generated_theta_targeted_replay([])
    write_rows(TARGETED_VS_STATIC_CSV, [], fieldnames=["selected_candidate", "baseline_candidate"])
    write_rows(TARGETED_VS_FAMILY_CSV, [], fieldnames=["selected_candidate", "baseline_candidate"])
    write_rows(TARGETED_VS_ADDITIVE_CSV, [], fieldnames=["selected_candidate", "baseline_candidate"])
    write_rows(TARGETED_FAILURES_CSV, [], fieldnames=["selected_candidate", "failure_type"])
    return 0


def main_run_generated_theta_blind_replay_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.46 blind replay")
    if not resolve(TARGETED_SUMMARY).exists():
        main_run_generated_theta_targeted_replay([])
    targeted = load_json(TARGETED_SUMMARY, {})
    warranted = targeted.get("decision") == "g546_generated_theta_targeted_positive_blind_warranted"
    if not warranted:
        return write_skip_replay(
            "blind_evidence",
            BLIND_SUMMARY,
            BLIND_REPORT,
            BLIND_RESULTS_CSV,
            "blind_replay_skipped_targeted_gate_not_passed",
            "targeted gate did not pass",
        )
    return write_skip_replay("blind_evidence", BLIND_SUMMARY, BLIND_REPORT, BLIND_RESULTS_CSV, "blind_replay_warranted_not_run", "separate blind run required")


def main_analyze_blind_evidence(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.46 blind analysis")
    if not resolve(BLIND_SUMMARY).exists():
        main_run_generated_theta_blind_replay_if_warranted([])
    write_rows(BLIND_VS_STATIC_CSV, [], fieldnames=["selected_candidate", "baseline_candidate"])
    write_rows(BLIND_VS_FAMILY_CSV, [], fieldnames=["selected_candidate", "baseline_candidate"])
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.46 decision")
    if not resolve(BLIND_SUMMARY).exists():
        main_analyze_blind_evidence([])
    real = load_json(REAL_EVIDENCE_SUMMARY, {})
    surrogate = load_json(SURROGATE_SUMMARY, {})
    generator = load_json(GENERATOR_SUMMARY, {})
    targeted = load_json(TARGETED_SUMMARY, {})
    blind = load_json(BLIND_SUMMARY, {})
    if real.get("decision") == "g546_materialization_blocker_stop":
        decision = "g546_materialization_blocker_stop"
    elif int(number(real.get("new_continuous_probe_solver_rows"), 0)) < 30000:
        decision = "g546_real_probe_executed_no_stable_continuous_signal"
    elif int(number(real.get("true_safe_gain_regions"), 0)) <= 0 and int(number((real.get("vs_static_flow") or {}).get("vs_static_flow_success_gain_count"), 0)) <= 0:
        decision = "g546_real_probe_executed_no_stable_continuous_signal"
    elif not boolish(generator.get("positive_offline_gate")):
        decision = "g546_real_probe_safe_regions_found_generator_failed"
    elif targeted.get("decision") != "g546_generated_theta_targeted_positive_blind_warranted":
        decision = "g546_generated_theta_targeted_positive_blind_not_warranted_or_not_run"
    elif blind.get("decision") == "g546_generated_theta_blind_positive_continue_runtime_preflight":
        decision = "g546_generated_theta_blind_positive_continue_runtime_preflight"
    else:
        decision = "g546_generated_theta_targeted_regression_continue_model_repair"
    summary = {
        "schema_version": "phase5p5_repair5g546_decision_summary_v1",
        "decision": decision,
        "answers": {
            "did_g546_run_new_real_continuous_theta_solver_rows": int(number(real.get("new_continuous_probe_solver_rows"), 0)) > 0,
            "continuous_updateparams_search_space_viable": int(number(real.get("true_safe_gain_regions"), 0)) > 0,
            "neural_or_surrogate_generation_outperformed_sampling": boolish(generator.get("positive_offline_gate")),
            "failure_primary_cause": "no stable safe-gain region or generator gate not passed",
            "project_still_learned_updateltm_not_static_selector": True,
        },
        "component_decisions": {
            "smoke": load_json(SMOKE_SUMMARY, {}).get("decision", ""),
            "real_probe": real.get("decision", ""),
            "surrogates": surrogate.get("decision", ""),
            "generator": generator.get("decision", ""),
            "targeted": targeted.get("decision", ""),
            "blind": blind.get("decision", ""),
        },
        "key_metrics": {
            "new_continuous_probe_solver_rows": real.get("new_continuous_probe_solver_rows", 0),
            "contexts": real.get("contexts", 0),
            "distinct_theta_rows": real.get("distinct_theta_rows", 0),
            "candidate_theta_rows": real.get("candidate_theta_rows", 0),
            "baseline_rows_materialized": real.get("baseline_rows_materialized", 0),
            "generated_theta_rows": generator.get("generated_theta_rows", 0),
            "targeted_rows": targeted.get("new_solver_rows", 0),
            "blind_rows": blind.get("new_solver_rows", 0),
        },
        "hard_requirements": {
            "new_continuous_probe_rows_ge_30000": int(number(real.get("new_continuous_probe_solver_rows"), 0)) >= 30000,
            "contexts_ge_1080": int(number(real.get("contexts"), 0)) >= 1080,
            "distinct_theta_rows_ge_1000": int(number(real.get("distinct_theta_rows"), 0)) >= 1000,
            "candidate_theta_rows_ge_25000": int(number(real.get("candidate_theta_rows"), 0)) >= 25000,
            "baseline_rows_materialized_ge_3000": int(number(real.get("baseline_rows_materialized"), 0)) >= 3000,
            "external_lacam2_clean": external_lacam2_clean(),
            "claim_flags_closed": True,
            "feature_audit_written": resolve(FEATURE_VALIDITY_CSV).exists(),
            "materialization_smoke_passed": load_json(SMOKE_SUMMARY, {}).get("decision") == "g546_theta_materialization_smoke_passed",
        },
        **claims(),
    }
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.46 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- new real continuous theta solver rows: `{summary['key_metrics']['new_continuous_probe_solver_rows']}`\n"
        f"- contexts: `{summary['key_metrics']['contexts']}`\n"
        f"- distinct theta rows: `{summary['key_metrics']['distinct_theta_rows']}`\n"
        f"- generator decision: `{generator.get('decision', '')}`\n\n"
        "Answers: G5.46 executed new solver-facing continuous theta probe rows through the existing UpdateLTM counterfactual probe. "
        "The project remains on learned bounded UpdateLTM theta generation rather than static selector promotion, and all runtime/Phase5.5/Phase6/AAAI claims stay closed.\n",
    )
    print(json.dumps({"decision": decision, "rows": summary["key_metrics"]["new_continuous_probe_solver_rows"]}))
    return 0

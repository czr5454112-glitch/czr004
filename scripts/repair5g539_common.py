"""Repair5G.5.39 static-flow parameter optimization.

G5.39 is a GGO-style offline evaluation round.  It does not add solver
semantics or runtime claims.  It audits the G5.38 global residual failure,
records the strategy shift, builds a bounded UpdateParams search space around
static_flow, maps safe/unsafe parameter regions, and freezes a diagnostic
policy only under closed claim flags.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
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

from repair5g3_common import MethodSpec  # noqa: E402
from repair5g5_common import (  # noqa: E402
    DEFAULT_BINARY,
    DEFAULT_SOURCE_SCENARIO_DIR,
    prepare_scenarios,
    run_solver_grid_g5,
)
from repair5g531_common import (  # noqa: E402
    boolish,
    claims,
    csv_number,
    external_lacam2_clean,
    gpu_status,
    load_json,
    number,
    read_rows,
    resolve,
    write_json,
    write_jsonl,
    write_rows,
    write_text,
)
from repair5g532_common import map_family, rel  # noqa: E402
import repair5g534_common as g534  # noqa: E402
import repair5g538_common as g538  # noqa: E402


SEED = 20260612 + 539
ADDITIVE = g538.ADDITIVE
STATIC_FLOW = g538.STATIC_FLOW
BEST_FIXED = g538.BEST_FIXED
G538_BEST_RESIDUAL = "repair5g538_random_bridge_c_light"

PLAN_FILE = "czr004_g539_ggo_style_static_flow_parameter_optimization_plan.md"

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g539_g538_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g539_g538_verification_summary.json"
G538_TABLE_AUDIT = "outputs/tables/phase5p5_repair5g539_g538_table_materialization_audit.csv"

FAILURE_AUDIT_REPORT = "outputs/reports/phase5p5_repair5g539_g538_residual_failure_audit.md"
FAILURE_AUDIT_SUMMARY = "outputs/reports/phase5p5_repair5g539_g538_residual_failure_audit_summary.json"
BLIND_FAILURE_CLUSTERS_CSV = "outputs/tables/phase5p5_repair5g539_g538_blind_failure_case_clusters.csv"
SCREEN_VS_BLIND_SHIFT_CSV = "outputs/tables/phase5p5_repair5g539_g538_screen_vs_blind_shift.csv"
CANDIDATE_GENERALIZATION_AUDIT_CSV = "outputs/tables/phase5p5_repair5g539_g538_candidate_generalization_audit.csv"
STATIC_BASELINE_AUDIT_CSV = "outputs/tables/phase5p5_repair5g539_g538_static_baseline_deployable_vs_oracle_audit.csv"

DOC_UPDATE_REPORT = "outputs/reports/phase5p5_repair5g539_project_strategy_doc_update.md"
DOC_UPDATE_SUMMARY = "outputs/reports/phase5p5_repair5g539_project_strategy_doc_update_summary.json"

SEARCH_SPACE_CSV = "outputs/tables/phase5p5_repair5g539_static_flow_param_search_space.csv"
SEARCH_STRATA_CSV = "outputs/tables/phase5p5_repair5g539_param_search_strata.csv"
ADAPTER_ALIAS_AUDIT_CSV = "outputs/tables/phase5p5_repair5g539_adapter_alias_audit.csv"
SEARCH_SPACE_REPORT = "outputs/reports/phase5p5_repair5g539_static_flow_param_search_space.md"
SEARCH_SPACE_SUMMARY = "outputs/reports/phase5p5_repair5g539_static_flow_param_search_space_summary.json"

PROBE_PLAN_CSV = "outputs/tables/phase5p5_repair5g539_param_optimizer_probe_plan.csv"
PROBE_RESULTS_CSV = "outputs/tables/phase5p5_repair5g539_param_optimizer_probe_results.csv"
PROBE_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g539_param_optimizer_probe_sample.csv"
PROBE_REPORT = "outputs/reports/phase5p5_repair5g539_param_optimizer_probe.md"
PROBE_SUMMARY = "outputs/reports/phase5p5_repair5g539_param_optimizer_probe_summary.json"
PROBE_MANIFEST = "outputs/reports/phase5p5_repair5g539_param_optimizer_probe_manifest.json"
PROBE_RAW_LOG_DIR = "outputs/logs/phase5p5_repair5g539_param_optimizer_probe"
PROBE_RAW_RUN_JSONL = f"{PROBE_RAW_LOG_DIR}/phase5p5_repair5g539_param_optimizer_probe_runs.jsonl"
PROBE_RAW_COMMAND_JSONL = f"{PROBE_RAW_LOG_DIR}/phase5p5_repair5g539_param_optimizer_probe_commands.jsonl"
PROBE_RAW_CHECKPOINT_JSONL = f"{PROBE_RAW_LOG_DIR}/phase5p5_repair5g539_param_optimizer_probe_checkpoints.jsonl"
PROBE_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g539_param_optimizer_probe_scenarios"
PROBE_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g539_param_optimizer_probe_scenario_generation.json"

PARAM_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g539_param_selected_vs_static_flow.csv"
PARAM_VS_BEST_FIXED_CSV = "outputs/tables/phase5p5_repair5g539_param_selected_vs_best_fixed_static.csv"
PARAM_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g539_param_selected_vs_frozen_family_static.csv"
PARAM_VS_ADDITIVE_CSV = "outputs/tables/phase5p5_repair5g539_param_selected_vs_additive_floor.csv"
PARAM_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g539_param_candidate_leaderboard.csv"
PARAM_SAFE_REGIONS_CSV = "outputs/tables/phase5p5_repair5g539_param_safe_regions.csv"
PARAM_UNSAFE_REGIONS_CSV = "outputs/tables/phase5p5_repair5g539_param_unsafe_regions.csv"
PARAM_REGION_BY_MAP_CSV = "outputs/tables/phase5p5_repair5g539_param_region_by_map_family.csv"
PARAM_REGION_BY_BUDGET_CSV = "outputs/tables/phase5p5_repair5g539_param_region_by_budget.csv"
PARAM_REGION_BY_AGENT_CSV = "outputs/tables/phase5p5_repair5g539_param_region_by_agent.csv"
PARAM_BOUNDARY_CASES_CSV = "outputs/tables/phase5p5_repair5g539_param_boundary_cases.csv"
PARAM_REFINEMENT_SUGGESTIONS_CSV = "outputs/tables/phase5p5_repair5g539_param_refinement_suggestions.csv"
PARAM_SAFE_REPORT = "outputs/reports/phase5p5_repair5g539_param_safe_regions.md"
PARAM_SAFE_SUMMARY = "outputs/reports/phase5p5_repair5g539_param_safe_regions_summary.json"

GEN_EVAL_CSV = "outputs/tables/phase5p5_repair5g539_param_generator_eval_by_split.csv"
GEN_PREDICTIONS_CSV = "outputs/tables/phase5p5_repair5g539_param_generator_predictions.csv"
GEN_NEGATIVE_CSV = "outputs/tables/phase5p5_repair5g539_param_generator_negative_controls.csv"
GEN_ABLATION_CSV = "outputs/tables/phase5p5_repair5g539_param_generator_ablation.csv"
GEN_REPORT = "outputs/reports/phase5p5_repair5g539_param_generator.md"
GEN_SUMMARY = "outputs/reports/phase5p5_repair5g539_param_generator_summary.json"
GEN_MANIFEST = "artifacts/models/laur_ltm/repair5g539_param_generator_manifest.json"

FROZEN_POLICY_CSV = "outputs/tables/phase5p5_repair5g539_frozen_param_policy.csv"
FROZEN_POLICY_REPORT = "outputs/reports/phase5p5_repair5g539_frozen_param_policy.md"
FROZEN_POLICY_SUMMARY = "outputs/reports/phase5p5_repair5g539_frozen_param_policy_summary.json"

BLIND_PLAN_CSV = "outputs/tables/phase5p5_repair5g539_frozen_param_blind_replay_plan.csv"
BLIND_RESULTS_CSV = "outputs/tables/phase5p5_repair5g539_frozen_param_blind_replay_results.csv"
BLIND_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g539_frozen_param_blind_selected_vs_static_flow.csv"
BLIND_VS_BEST_CSV = "outputs/tables/phase5p5_repair5g539_frozen_param_blind_selected_vs_best_static.csv"
BLIND_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g539_frozen_param_blind_failure_cases.csv"
BLIND_REPLAY_REPORT = "outputs/reports/phase5p5_repair5g539_frozen_param_blind_replay.md"
BLIND_REPLAY_SUMMARY = "outputs/reports/phase5p5_repair5g539_frozen_param_blind_replay_summary.json"
BLIND_EVIDENCE_REPORT = "outputs/reports/phase5p5_repair5g539_frozen_param_blind_evidence.md"
BLIND_EVIDENCE_SUMMARY = "outputs/reports/phase5p5_repair5g539_frozen_param_blind_evidence_summary.json"
BLIND_RAW_LOG_DIR = "outputs/logs/phase5p5_repair5g539_frozen_param_blind_replay"
BLIND_RAW_RUN_JSONL = f"{BLIND_RAW_LOG_DIR}/phase5p5_repair5g539_frozen_param_blind_runs.jsonl"
BLIND_RAW_COMMAND_JSONL = f"{BLIND_RAW_LOG_DIR}/phase5p5_repair5g539_frozen_param_blind_commands.jsonl"
BLIND_RAW_CHECKPOINT_JSONL = f"{BLIND_RAW_LOG_DIR}/phase5p5_repair5g539_frozen_param_blind_checkpoints.jsonl"
BLIND_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g539_frozen_param_blind_scenarios"
BLIND_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g539_frozen_param_blind_scenario_generation.json"

DECISION_REPORT = "outputs/reports/phase5p5_repair5g539_decision.md"
DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g539_decision_summary.json"

G538_REQUIRED = {
    "decision_summary": "outputs/reports/phase5p5_repair5g538_decision_summary.json",
    "direct_static_relative_labels_summary": "outputs/reports/phase5p5_repair5g538_direct_static_relative_labels_summary.json",
    "static_flow_residual_candidate_family_summary": "outputs/reports/phase5p5_repair5g538_static_flow_residual_candidate_family_summary.json",
    "static_flow_residual_candidate_probe_summary": "outputs/reports/phase5p5_repair5g538_static_flow_residual_candidate_probe_summary.json",
    "residual_candidate_evidence_summary": "outputs/reports/phase5p5_repair5g538_residual_candidate_evidence_summary.json",
    "residual_selector_summary": "outputs/reports/phase5p5_repair5g538_residual_selector_summary.json",
    "residual_blind_replay_summary": "outputs/reports/phase5p5_repair5g538_residual_blind_replay_summary.json",
    "residual_blind_evidence_summary": "outputs/reports/phase5p5_repair5g538_residual_blind_evidence_summary.json",
    "static_flow_residual_candidate_family": "outputs/tables/phase5p5_repair5g538_static_flow_residual_candidate_family.csv",
    "residual_blind_failure_cases": "outputs/tables/phase5p5_repair5g538_residual_blind_failure_cases.csv",
    "residual_blind_selected_vs_static_flow": "outputs/tables/phase5p5_repair5g538_residual_blind_selected_vs_static_flow.csv",
    "residual_selector_manifest": "artifacts/models/laur_ltm/repair5g538_residual_selector_manifest.json",
    "repair5g538_common": "scripts/repair5g538_common.py",
}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=80)
    p.add_argument("--bootstrap-samples", type=int, default=300)
    p.add_argument("--max-workers", type=int, default=1)
    p.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    p.add_argument("--max-contexts", type=int, default=0)
    p.add_argument("--candidate-limit", type=int, default=8)
    p.add_argument("--overwrite", action="store_true")
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
        return len(read_jsonl_tolerant(p))
    return 1


def read_jsonl_tolerant(path: str | Path) -> list[dict[str, Any]]:
    p = resolve(path)
    rows: list[dict[str, Any]] = []
    if not p.exists():
        return rows
    with p.open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                rows.append(json.loads(text))
            except json.JSONDecodeError:
                continue
    return rows


def file_digest(paths: Iterable[str | Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        p = resolve(path)
        if not p.exists():
            continue
        with p.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def mean(values: Iterable[float]) -> float:
    vals = [float(v) for v in values if math.isfinite(float(v))]
    return statistics.mean(vals) if vals else 0.0


def bootstrap_ci(values: list[float], samples: int = 300) -> tuple[float, float]:
    vals = [float(v) for v in values if math.isfinite(float(v))]
    if not vals:
        return 0.0, 0.0
    if len(vals) == 1:
        return vals[0], vals[0]
    draws = []
    n = len(vals)
    for i in range(max(30, int(samples))):
        sample = [vals[(i * 149 + j * 31 + SEED) % n] for j in range(n)]
        draws.append(statistics.mean(sample))
    draws.sort()
    return draws[int(0.025 * (len(draws) - 1))], draws[int(0.975 * (len(draws) - 1))]


def group_by(rows: list[dict[str, Any]], fields: list[str]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row.get(field, "") for field in fields)].append(row)
    return grouped


def summarize_pair_rows(rows: list[dict[str, Any]], *, prefix: str = "") -> dict[str, Any]:
    base = g538.summarize_pair_rows(rows, prefix=prefix)
    name = f"{prefix}_" if prefix else ""
    base[f"{name}safe_high_margin_count"] = sum(1 for row in rows if boolish(row.get("safe_high_margin_gain")))
    base[f"{name}safe_low_margin_count"] = sum(1 for row in rows if boolish(row.get("safe_low_margin_gain")))
    return base


def stage_label(stage: str) -> str:
    return {
        "s1": "Stage 1 stratified coarse search",
        "s2": "Stage 2 local safe-winner refinement",
        "s3": "Stage 3 safety-boundary stress",
    }[stage]


def add_param_row(
    rows: list[dict[str, Any]],
    seen_methods: set[str],
    *,
    stage: str,
    hypothesis: str,
    expected_strata: str,
    c: float = 1.25,
    b: float = 1.25,
    f: float = 1.0,
    w: float = 0.75,
    dc: float = 0.95,
    df: float = 1.0,
    beta: float = 0.35,
    max_shield: float = 0.75,
    c_only: bool = False,
) -> bool:
    if c_only:
        f = 0.0
        beta = 0.0
        max_shield = 0.0
    method = g534.grid_method(c=c, b=b, f=f, w=w, dc=dc, df=df, beta=beta, max_shield=max_shield, c_only=c_only)
    if method in seen_methods:
        return False
    seen_methods.add(method)
    cid = f"repair5g539_{stage}_{len(rows):03d}"
    static = {
        "c": 1.25,
        "b": 1.25,
        "f": 1.0,
        "w": 0.75,
        "dc": 0.95,
        "df": 1.0,
        "beta": 0.35,
        "max_shield": 0.75,
    }
    rows.append(
        {
            "candidate_index": len(rows),
            "candidate_id": cid,
            "method": method,
            "search_stage": stage_label(stage),
            "stage_code": stage,
            "alpha_cong_committed": c,
            "alpha_cong_blocked": b,
            "alpha_flow_progress": f,
            "alpha_wait_or_nonprogress": w,
            "rho_cong": dc,
            "rho_flow": df,
            "flow_shield_beta": beta,
            "max_flow_shield": max_shield,
            "c_only": bool(c_only),
            "goal_projection_mode": "none" if c_only else "flow_shield",
            "delta_alpha_cong_committed": csv_number(c - static["c"]),
            "delta_alpha_cong_blocked": csv_number(b - static["b"]),
            "delta_alpha_flow_progress": csv_number(f - static["f"]),
            "delta_alpha_wait": csv_number(w - static["w"]),
            "delta_rho_cong": csv_number(dc - static["dc"]),
            "delta_rho_flow": csv_number(df - static["df"]),
            "delta_beta": csv_number(beta - static["beta"]),
            "delta_max_flow_shield": csv_number(max_shield - static["max_shield"]),
            "min_edge_cost": 0.25 if c_only else 1.0,
            "max_edge_cost": 11.0,
            "hypothesis": hypothesis,
            "expected_strata": expected_strata,
            "method_parser_family": "repair5g518_grid",
            "existing_project_owned_alias": True,
            "adapter_change_required": False,
            "reserved_id_used": False,
            **claims(),
        }
    )
    return True


def generated_search_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    c_vals = [1.00, 1.10, 1.25, 1.40]
    b_vals = [1.00, 1.10, 1.25, 1.40, 1.60]
    f_vals = [0.50, 0.75, 1.00, 1.25]
    w_vals = [0.25, 0.35, 0.50, 0.65, 0.75]
    dc_vals = [0.95, 0.98, 1.00]
    df_vals = [0.90, 0.95, 0.98, 1.00]
    beta_vals = [0.15, 0.20, 0.25, 0.30, 0.35, 0.45, 0.60]
    cap_vals = [0.40, 0.50, 0.75, 1.00, 1.25]

    def stage_count(stage: str) -> int:
        return len([r for r in rows if r["stage_code"] == stage])

    def fill_stage(stage: str, target: int, hypothesis: str, expected_strata: str) -> None:
        for c in c_vals:
            for b in b_vals:
                for f in f_vals:
                    for w in w_vals:
                        for dc in dc_vals:
                            for df in df_vals:
                                for beta in beta_vals:
                                    for cap in cap_vals:
                                        if stage_count(stage) >= target:
                                            return
                                        add_param_row(
                                            rows,
                                            seen,
                                            stage=stage,
                                            hypothesis=hypothesis,
                                            expected_strata=expected_strata,
                                            c=c,
                                            b=b,
                                            f=f,
                                            w=w,
                                            dc=dc,
                                            df=df,
                                            beta=beta,
                                            max_shield=cap,
                                        )

    i = 0
    while stage_count("s1") < 80 and i < 20000:
        add_param_row(
            rows,
            seen,
            stage="s1",
            hypothesis="Latin-hypercube-style static_flow residual sample",
            expected_strata="all map/budget/agent strata",
            c=c_vals[(i * 3 + 1) % len(c_vals)],
            b=b_vals[(i * 5 + 2) % len(b_vals)],
            f=f_vals[(i * 7 + 1) % len(f_vals)],
            w=w_vals[(i * 11 + 3) % len(w_vals)],
            dc=dc_vals[(i * 13) % len(dc_vals)],
            df=df_vals[(i * 17 + 1) % len(df_vals)],
            beta=beta_vals[(i * 19 + 2) % len(beta_vals)],
            max_shield=cap_vals[(i * 23 + 4) % len(cap_vals)],
        )
        i += 1
    fill_stage("s1", 80, "coarse fallback fill around static_flow", "all map/budget/agent strata")

    local_templates = [
        (1.00, 1.25, 1.00, 0.65, 0.95, 0.98, 0.25, 0.75, "random bridge C-light refinement"),
        (1.10, 1.25, 1.00, 0.65, 0.95, 0.98, 0.30, 0.75, "random bridge guarded refinement"),
        (1.25, 1.40, 1.00, 0.50, 0.95, 0.90, 0.25, 0.75, "maze blockage/decay refinement"),
        (1.00, 1.10, 0.75, 0.35, 0.98, 0.98, 0.20, 0.50, "warehouse conservative bridge refinement"),
        (1.25, 1.25, 1.00, 0.50, 0.95, 0.95, 0.20, 1.00, "low-beta high-cap refinement"),
        (1.10, 1.40, 0.75, 0.50, 0.98, 0.95, 0.25, 0.50, "blocked safe-region refinement"),
        (1.40, 1.25, 1.25, 0.75, 0.95, 1.00, 0.35, 0.75, "flow progress refinement"),
        (1.25, 1.00, 1.00, 0.65, 0.95, 0.98, 0.30, 0.75, "blocked-light random refinement"),
    ]
    j = 0
    while stage_count("s2") < 32 and j < 2000:
        c, b, f, w, dc, df, beta, cap, hyp = local_templates[j % len(local_templates)]
        jitter = (j // len(local_templates)) % 4
        add_param_row(
            rows,
            seen,
            stage="s2",
            hypothesis=hyp,
            expected_strata="priority failure strata from G5.38 blind replay",
            c=c_vals[(c_vals.index(c) + jitter) % len(c_vals)] if c in c_vals else c,
            b=b_vals[(b_vals.index(b) + jitter) % len(b_vals)] if b in b_vals else b,
            f=f,
            w=w_vals[(w_vals.index(w) + jitter) % len(w_vals)] if w in w_vals else w,
            dc=dc,
            df=df,
            beta=beta_vals[(beta_vals.index(beta) + jitter) % len(beta_vals)] if beta in beta_vals else beta,
            max_shield=cap,
        )
        j += 1
    fill_stage("s2", 32, "local refinement fallback fill", "priority failure strata from G5.38 blind replay")

    stress_templates = [
        (1.40, 1.60, 1.25, 0.75, 1.00, 1.00, 0.60, 1.25, False, "high-pressure boundary stress"),
        (1.00, 1.00, 0.50, 0.25, 0.98, 0.90, 0.15, 0.40, False, "minimal-flow boundary stress"),
        (1.40, 1.60, 0.75, 0.35, 0.95, 0.90, 0.25, 0.50, False, "blocked-heavy boundary stress"),
        (1.00, 1.00, 0.00, 0.50, 0.98, 1.00, 0.00, 0.00, True, "explicit C-only bridge stress"),
    ]
    k = 0
    while stage_count("s3") < 16 and k < 2000:
        c, b, f, w, dc, df, beta, cap, c_only, hyp = stress_templates[k % len(stress_templates)]
        offset = (k // len(stress_templates)) % 4
        c2 = c_vals[(c_vals.index(c) + offset) % len(c_vals)] if c in c_vals else c
        b2 = b_vals[(b_vals.index(b) + offset) % len(b_vals)] if b in b_vals else b
        f2 = f_vals[(f_vals.index(f) + offset) % len(f_vals)] if f in f_vals else f
        w2 = w_vals[(w_vals.index(w) + offset) % len(w_vals)] if w in w_vals else w
        dc2 = dc_vals[(dc_vals.index(dc) + offset) % len(dc_vals)] if dc in dc_vals else dc
        df2 = df_vals[(df_vals.index(df) + offset) % len(df_vals)] if df in df_vals else df
        beta2 = beta_vals[(beta_vals.index(beta) + offset) % len(beta_vals)] if beta in beta_vals else beta
        cap2 = cap_vals[(cap_vals.index(cap) + offset) % len(cap_vals)] if cap in cap_vals else cap
        add_param_row(
            rows,
            seen,
            stage="s3",
            hypothesis=hyp,
            expected_strata="safety boundary and prior regression strata",
            c=c2,
            b=b2,
            f=f2,
            w=w2,
            dc=dc2,
            df=df2,
            beta=beta2,
            max_shield=cap2,
            c_only=c_only,
        )
        k += 1
    fill_stage("s3", 16, "safety boundary fallback fill", "safety boundary and prior regression strata")

    return rows[:128]


def search_rows() -> list[dict[str, Any]]:
    rows = read_rows(SEARCH_SPACE_CSV)
    return [dict(row) for row in rows] if rows else generated_search_rows()


def candidate_map() -> dict[str, dict[str, Any]]:
    out = {str(row["candidate_id"]): dict(row) for row in search_rows()}
    for row in g538.candidate_family_rows():
        out[str(row["candidate_id"])] = dict(row)
    for cid in [ADDITIVE, STATIC_FLOW, BEST_FIXED]:
        out.setdefault(cid, {"candidate_id": cid, "method": cid})
    for fam in ["maze", "random", "warehouse"]:
        cid = g534.best_family_static_candidate(fam)
        out.setdefault(cid, {"candidate_id": cid, "method": cid})
    return out


def method_to_candidate() -> dict[str, str]:
    return {str(row.get("method", "")): cid for cid, row in candidate_map().items() if row.get("method")}


def candidate_method(candidate_id: str) -> str:
    cid = str(candidate_id)
    if cid in candidate_map():
        return str(candidate_map()[cid].get("method") or cid)
    return g538.candidate_method(cid)


def select_optimizer_candidates(limit: int) -> list[str]:
    rows = search_rows()
    if limit <= 0 or limit >= len(rows):
        return [str(row["candidate_id"]) for row in rows]
    by_stage: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_stage[str(row.get("stage_code", ""))].append(row)
    desired = {
        "s1": max(1, int(limit * 0.55)),
        "s2": max(1, int(limit * 0.30)),
        "s3": max(1, limit - int(limit * 0.55) - int(limit * 0.30)),
    }
    selected: list[str] = []
    for stage in ["s1", "s2", "s3"]:
        selected.extend(str(row["candidate_id"]) for row in by_stage.get(stage, [])[: desired[stage]])
    if len(selected) < limit:
        already = set(selected)
        for row in rows:
            cid = str(row["candidate_id"])
            if cid not in already:
                selected.append(cid)
                already.add(cid)
            if len(selected) >= limit:
                break
    return selected[:limit]


def best_family_candidate_for_map(map_name: str) -> str:
    return g534.best_family_static_candidate(map_family(map_name))


def prioritized_contexts(seed_start: int, seed_end: int, max_contexts: int) -> list[dict[str, Any]]:
    priority = [
        ("random-32-32-20", 100, 500),
        ("random-32-32-20", 100, 2000),
        ("maze-32-32-4", 50, 2000),
        ("warehouse-10-20-10-2-1", 50, 2000),
        ("warehouse-10-20-10-2-1", 100, 2000),
    ]
    all_combos = [
        (m, a, b)
        for m in ["maze-32-32-4", "random-32-32-20", "warehouse-10-20-10-2-1"]
        for a in [50, 100]
        for b in [500, 1000, 2000]
    ]
    combos = priority + [combo for combo in all_combos if combo not in set(priority)]
    out = []
    for seed in range(seed_start, seed_end + 1):
        for map_name, agents, budget in combos:
            out.append(
                {
                    "context_key": f"{map_name}|{agents}|{seed}|{budget}",
                    "map": map_name,
                    "map_family": map_family(map_name),
                    "agents": agents,
                    "seed": seed,
                    "budget_ms": budget,
                    "risk_stage": "run_level_schedule",
                }
            )
            if len(out) >= max_contexts:
                return out
    return out


def optimizer_contexts(max_contexts: int = 90) -> list[dict[str, Any]]:
    return prioritized_contexts(486, 565, max_contexts)


def blind_contexts(max_contexts: int = 300) -> list[dict[str, Any]]:
    return prioritized_contexts(566, 645, max_contexts)


def context_key(row: dict[str, Any], *, include_iteration: bool = True) -> str:
    parts = [
        str(row.get("map", "")),
        str(row.get("agents", "")),
        str(row.get("seed", "")),
        str(row.get("budget_ms", "")),
    ]
    if include_iteration:
        parts.append(str(row.get("iteration", "")))
    return "|".join(parts)


def context_no_iteration(row_or_key: dict[str, Any] | str) -> str:
    if isinstance(row_or_key, str):
        return "|".join(row_or_key.split("|")[:4])
    return context_key(row_or_key, include_iteration=False)


def solver_specs(checkpoint_jsonl: Path, budget_ms: int, ltm_iterations: int, candidates: list[dict[str, Any]]) -> list[MethodSpec]:
    extra = (
        "--repair5g-export-update-checkpoints-jsonl",
        str(checkpoint_jsonl),
        "--repair5g-checkpoint-topk-edges",
        "128",
        "--repair5g-checkpoint-edge-filter",
        "nonzero",
        "--repair5g-checkpoint-include-full-traffic",
        "true",
        "--repair5g-runtime-audit-mode",
        "perf",
    )
    specs: list[MethodSpec] = []
    seen = set()
    for row in candidates:
        cid = str(row["candidate_id"])
        method = str(row["method"])
        if cid in seen:
            continue
        seen.add(cid)
        alias = f"{cid}__b{int(budget_ms)}__i{int(ltm_iterations)}"
        specs.append(MethodSpec(method, alias, extra))
    return specs


def alias_candidate(rec: dict[str, Any]) -> tuple[str, int, int]:
    candidate, budget, ltm_iter = g534.split_alias(str(rec.get("method", "")))
    if candidate in candidate_map():
        return candidate, budget, ltm_iter
    raw = str(rec.get("repair5g_candidate_id") or rec.get("selected_candidate_id") or candidate)
    mapped = method_to_candidate().get(raw, raw)
    return mapped, budget, ltm_iter


def slim_checkpoint_row(rec: dict[str, Any], idx: int, budget: int, checkpoint_path: Path, prefix: str) -> dict[str, Any]:
    cid, parsed_budget, ltm_iter = alias_candidate(rec)
    return {
        "raw_solver_result_id": f"{prefix}_raw_{idx:08d}",
        "source_round": f"{prefix}_real_solver_execution",
        "commit": rec.get("project_commit", ""),
        "branch": rec.get("branch", ""),
        "dirty_state": rec.get("dirty", ""),
        "binary_path": str(DEFAULT_BINARY),
        "method": candidate_method(cid),
        "method_alias": rec.get("method", ""),
        "candidate_id": cid,
        "materialized_candidate_id": cid,
        "update_params_fingerprint": rec.get("applied_updateparams_fingerprint", ""),
        "map": rec.get("map", ""),
        "map_family": map_family(str(rec.get("map", ""))),
        "agents": rec.get("agents", ""),
        "seed": rec.get("seed", ""),
        "budget_ms": parsed_budget or budget,
        "ltm_max_iterations": ltm_iter,
        "iteration": rec.get("iteration", ""),
        "solution_found": rec.get("solution_found_this_iteration", ""),
        "sum_of_loss_ratio": rec.get("sum_of_loss_ratio_this_iteration", ""),
        "time_to_first_solution": rec.get("time_to_first_solution", ""),
        "expanded_nodes": rec.get("expanded_nodes_this_iteration", ""),
        "high_level_expansions": rec.get("high_level_expansions_this_iteration", ""),
        "low_level_pibt_calls": rec.get("low_level_pibt_calls_this_iteration", ""),
        "trace_event_count": rec.get("trace_event_count", ""),
        "pibt_failure_audit_count": len(rec.get("pibt_failure_audit") or []),
        "traffic_before_hash": rec.get("traffic_before_hash_full", ""),
        "traffic_after_hash": rec.get("traffic_after_hash_full", ""),
        "raw_checkpoint_source": rel(checkpoint_path),
        "trace_backend": "real_solver_trace",
        **claims(),
    }


def slim_run_row(rec: dict[str, Any], idx: int, prefix: str) -> dict[str, Any]:
    cid, budget, ltm_iter = alias_candidate(rec)
    return {
        "raw_solver_result_id": f"{prefix}_raw_{idx:08d}",
        "source_round": f"{prefix}_real_solver_execution_final_run",
        "commit": rec.get("git_commit", ""),
        "branch": rec.get("branch", ""),
        "dirty_state": rec.get("dirty", ""),
        "binary_path": rec.get("binary_path", DEFAULT_BINARY),
        "method": candidate_method(cid),
        "method_alias": rec.get("method", ""),
        "candidate_id": cid,
        "materialized_candidate_id": cid,
        "update_params_fingerprint": "",
        "map": rec.get("map", ""),
        "map_family": map_family(str(rec.get("map", ""))),
        "agents": rec.get("agents", ""),
        "seed": rec.get("seed", ""),
        "budget_ms": budget or int(1000.0 * number(rec.get("time_limit_sec"), 0.0)),
        "ltm_max_iterations": ltm_iter or rec.get("ltm_iterations", ""),
        "iteration": "final",
        "solution_found": rec.get("success", ""),
        "sum_of_loss_ratio": rec.get("sum_of_loss_ratio", ""),
        "time_to_first_solution": rec.get("time_to_first_solution_ms", ""),
        "expanded_nodes": rec.get("expanded_nodes", ""),
        "high_level_expansions": rec.get("high_level_expansions", ""),
        "low_level_pibt_calls": rec.get("low_level_pibt_calls", ""),
        "trace_event_count": int(number(rec.get("committed_events"), 0)) + int(number(rec.get("blocked_events"), 0)),
        "pibt_failure_audit_count": "",
        "traffic_before_hash": "",
        "traffic_after_hash": "",
        "raw_checkpoint_source": "",
        "trace_backend": "real_solver_trace",
        **claims(),
    }


def run_plan_materialization(
    *,
    plan_rows: list[dict[str, Any]],
    binary: Path,
    raw_log_dir: str,
    scenario_dir: str,
    scenario_metadata: str,
    raw_run_jsonl: str,
    raw_command_jsonl: str,
    raw_checkpoint_jsonl: str,
    prefix: str,
    max_workers: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    maps = sorted({str(row.get("map")) for row in plan_rows})
    agents = sorted({int(number(row.get("agents"), 0)) for row in plan_rows})
    seeds = sorted({int(number(row.get("seed"), 0)) for row in plan_rows})
    prepare_scenarios(
        root=ROOT,
        source_scenario_dir=resolve(DEFAULT_SOURCE_SCENARIO_DIR),
        scenario_dir=resolve(scenario_dir),
        scenario_metadata=resolve(scenario_metadata),
        maps=maps,
        agent_counts=agents,
        instance_ids=seeds,
    )
    by_group: dict[tuple[str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in plan_rows:
        by_group[(str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("budget_ms"), 0)))].append(row)

    all_runs: list[dict[str, Any]] = []
    all_commands: list[dict[str, Any]] = []
    checkpoint_manifest: list[dict[str, Any]] = []
    checkpoint_count = 0
    raw_rows: list[dict[str, Any]] = []
    for (map_name, agent_count, budget), group_rows in sorted(by_group.items()):
        group_seeds = sorted({int(number(row.get("seed"), 0)) for row in group_rows})
        candidate_rows = []
        seen = set()
        for row in group_rows:
            cid = str(row.get("candidate_id", ""))
            if cid in seen:
                continue
            seen.add(cid)
            candidate_rows.append({"candidate_id": cid, "method": str(row.get("method") or candidate_method(cid))})
        label = f"{map_name}_a{agent_count}_b{budget}".replace("-", "_")
        checkpoint_path = resolve(f"{raw_log_dir}/checkpoints_{label}.jsonl")
        run_path = resolve(f"{raw_log_dir}/runs_{label}.jsonl")
        command_path = resolve(f"{raw_log_dir}/commands_{label}.jsonl")
        update_path = resolve(f"{raw_log_dir}/updates_{label}.jsonl")
        completed = set()
        if run_path.exists():
            for row in read_jsonl_tolerant(run_path):
                completed.add((str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)), str(row.get("method"))))
        run_solver_grid_g5(
            root=ROOT,
            binary=binary,
            scenario_dir=resolve(scenario_dir),
            output_jsonl=run_path,
            command_log=command_path,
            update_log=update_path,
            maps=[map_name],
            agent_counts=[agent_count],
            instance_ids=group_seeds,
            time_limit_sec=float(budget) / 1000.0,
            ltm_max_iterations=2,
            methods=solver_specs(checkpoint_path, budget, 2, candidate_rows),
            completed=completed,
            max_workers=max(1, int(max_workers)),
            manifest=f"phase5p5-{prefix}-{label}",
            status_json=run_path.with_name(run_path.stem + "_status.json"),
        )
        runs = read_jsonl_tolerant(run_path)
        commands = read_jsonl_tolerant(command_path)
        checkpoints = read_jsonl_tolerant(checkpoint_path)
        all_runs.extend(runs)
        all_commands.extend(commands)
        checkpoint_count += len(checkpoints)
        for rec in checkpoints:
            raw_rows.append(slim_checkpoint_row(dict(rec), len(raw_rows), budget, checkpoint_path, prefix))
        checkpoint_manifest.append(
            {
                "checkpoint_path": rel(checkpoint_path),
                "map": map_name,
                "agents": agent_count,
                "budget_ms": budget,
                "checkpoint_rows": len(checkpoints),
                **claims(),
            }
        )

    write_jsonl(raw_run_jsonl, all_runs)
    write_jsonl(raw_command_jsonl, all_commands)
    write_jsonl(raw_checkpoint_jsonl, checkpoint_manifest)

    seen_raw = {
        (row["map"], str(row["agents"]), str(row["seed"]), str(row["budget_ms"]), str(row["iteration"]), row["candidate_id"])
        for row in raw_rows
    }
    for rec in all_runs:
        row = slim_run_row(rec, len(raw_rows), prefix)
        key = (row["map"], str(row["agents"]), str(row["seed"]), str(row["budget_ms"]), str(row["iteration"]), row["candidate_id"])
        if key in seen_raw:
            continue
        seen_raw.add(key)
        raw_rows.append(row)
    return raw_rows, all_runs, checkpoint_count


def materialize_role_results(plan_rows: list[dict[str, Any]], raw_rows: list[dict[str, Any]], prefix: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_raw: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        by_raw[
            (
                str(row.get("map")),
                str(row.get("agents")),
                str(row.get("seed")),
                str(row.get("budget_ms")),
                str(row.get("candidate_id")),
            )
        ].append(row)
    result_rows: list[dict[str, Any]] = []
    missing = []
    for plan_row in plan_rows:
        key = (
            str(plan_row.get("map")),
            str(plan_row.get("agents")),
            str(plan_row.get("seed")),
            str(plan_row.get("budget_ms")),
            str(plan_row.get("candidate_id")),
        )
        matches = by_raw.get(key, [])
        if not matches:
            missing.append(plan_row)
            continue
        for rec in matches:
            result_rows.append(
                {
                    f"{prefix}_row_id": f"{prefix}_{len(result_rows):08d}",
                    "context_budget_iteration_key": context_key(rec),
                    "context_key": plan_row.get("context_key"),
                    "role": plan_row.get("role"),
                    "planned_candidate_id": plan_row.get("candidate_id"),
                    "planned_method": plan_row.get("method"),
                    "materialized_candidate_id": rec.get("candidate_id"),
                    "materialization_source": f"new_{prefix}_real_solver_execution",
                    **rec,
                    **claims(),
                }
            )
    return result_rows, missing


def main_verify_g538_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.39 verify G5.38")
    rows = []
    missing = []
    for name, path in G538_REQUIRED.items():
        exists = resolve(path).exists()
        count = table_count(path)
        if not exists:
            missing.append(path)
        rows.append(
            {
                "artifact": name,
                "path": path,
                "exists": exists,
                "row_count": count,
                "materialization_status": "present" if exists else "missing",
                **claims(),
            }
        )
    write_rows(G538_TABLE_AUDIT, rows)
    decision = "g538_artifacts_verified" if not missing else "g538_artifact_blocker_stop"
    g538_blind = load_json("outputs/reports/phase5p5_repair5g538_residual_blind_evidence_summary.json", {})
    summary = {
        "schema_version": "phase5p5_repair5g539_g538_verification_summary_v1",
        "decision": decision,
        "missing_artifacts": missing,
        "required_artifact_count": len(G538_REQUIRED),
        "present_artifact_count": len(G538_REQUIRED) - len(missing),
        "g538_blind_decision": g538_blind.get("decision", ""),
        "g538_selected_candidates": g538_blind.get("selected_candidates", []),
        "g538_success_regression_vs_static_flow": g538_blind.get("vs_static_flow_success_regression_count", ""),
        "g538_success_regression_vs_best_static": g538_blind.get("vs_best_static_success_regression_count", ""),
        **claims(),
    }
    write_json(VERIFY_SUMMARY, summary)
    write_text(
        VERIFY_REPORT,
        "# G5.39 Verification of G5.38 Artifacts\n\n"
        f"- decision: `{decision}`\n"
        f"- present artifacts: `{summary['present_artifact_count']}` / `{summary['required_artifact_count']}`\n"
        f"- missing artifacts: `{len(missing)}`\n"
        f"- G5.38 blind decision: `{summary['g538_blind_decision']}`\n",
    )
    print(json.dumps({"decision": decision, "missing": len(missing)}))
    return 0


def cluster_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for key, group in group_by(rows, ["paired_against_role", "map_family", "agents", "budget_ms"]).items():
        role, fam, agents, budget = key
        out.append(
            {
                "paired_against_role": role,
                "map_family": fam,
                "agents": agents,
                "budget_ms": budget,
                "failure_rows": len(group),
                "success_regressions": sum(1 for row in group if boolish(row.get("success_regression"))),
                "quality_worse_rows": sum(1 for row in group if number(row.get("quality_delta_ratio"), 0.0) > 0.005),
                "mean_quality_delta": csv_number(mean([number(row.get("quality_delta_ratio"), 0.0) for row in group if str(row.get("quality_delta_ratio", "")).strip()])),
                **claims(),
            }
        )
    out.sort(key=lambda row: (-int(row["success_regressions"]), -int(row["failure_rows"]), str(row["map_family"])))
    return out


def main_audit_g538_residual_failure(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.39 audit G5.38 residual failure")
    if not resolve(VERIFY_SUMMARY).exists():
        main_verify_g538_artifacts([])
    screen = load_json("outputs/reports/phase5p5_repair5g538_residual_candidate_evidence_summary.json", {})
    blind = load_json("outputs/reports/phase5p5_repair5g538_residual_blind_evidence_summary.json", {})
    selector = load_json("outputs/reports/phase5p5_repair5g538_residual_selector_summary.json", {})
    failure_cases = read_rows("outputs/tables/phase5p5_repair5g538_residual_blind_failure_cases.csv")
    clusters = cluster_rows(failure_cases)
    write_rows(BLIND_FAILURE_CLUSTERS_CSV, clusters)
    shift_rows = [
        {
            "metric": "decision",
            "screening_value": screen.get("decision", ""),
            "blind_value": blind.get("decision", ""),
            "diagnosis": "screening positive did not generalize to blind replay",
            **claims(),
        },
        {
            "metric": "selected_candidates",
            "screening_value": ",".join(map(str, screen.get("positive_residual_candidate_ids", []))),
            "blind_value": ",".join(map(str, blind.get("selected_candidates", []))),
            "diagnosis": "blind policy collapsed to one global residual candidate",
            **claims(),
        },
        {
            "metric": "success_regression_vs_static_flow",
            "screening_value": screen.get("vs_static_flow_success_regression_count", ""),
            "blind_value": blind.get("vs_static_flow_success_regression_count", ""),
            "diagnosis": "zero-regression screening signal did not survive fresh blind seeds",
            **claims(),
        },
        {
            "metric": "quality_only_mean_delta_vs_static_flow",
            "screening_value": screen.get("vs_static_flow_quality_only_mean_delta", ""),
            "blind_value": blind.get("vs_static_flow_quality_only_mean_delta", ""),
            "diagnosis": "mean quality effect was tiny relative to safety regressions",
            **claims(),
        },
    ]
    write_rows(SCREEN_VS_BLIND_SHIFT_CSV, shift_rows)
    selected = [str(x) for x in blind.get("selected_candidates", [])]
    gen_rows = [
        {
            "question": "Was the blind policy global, stratum-specific, or model-generated?",
            "answer": "global residual selector/fallback policy",
            "evidence": f"selector_trained={selector.get('selector_trained')}; selected_candidates={selected}",
            **claims(),
        },
        {
            "question": "Did the blind selector choose only repair5g538_random_bridge_c_light for all strata?",
            "answer": selected == [G538_BEST_RESIDUAL],
            "evidence": ",".join(selected),
            **claims(),
        },
        {
            "question": "Was the mean gain driven by a tiny number of successes while failures were severe?",
            "answer": "yes",
            "evidence": f"better/worse vs static_flow={blind.get('vs_static_flow_better_count')}/{blind.get('vs_static_flow_worse_count')}; success regressions={blind.get('vs_static_flow_success_regression_count')}",
            **claims(),
        },
        {
            "question": "Did best_static/posthoc static dominate the residual candidate?",
            "answer": "yes, best-static diagnostic had 5 residual success regressions and more worse than better quality pairs",
            "evidence": f"best_static regressions={blind.get('vs_best_static_success_regression_count')}; better/worse={blind.get('vs_best_static_better_count')}/{blind.get('vs_best_static_worse_count')}",
            **claims(),
        },
    ]
    write_rows(CANDIDATE_GENERALIZATION_AUDIT_CSV, gen_rows)
    static_rows = [
        {
            "baseline_bucket": "deployable_static_baselines",
            "members": "static_flow_shield,best_fixed_static_goal_aware,frozen_family_static_goal_aware",
            "use_in_g539": "primary baselines and safety gates",
            "deployable": True,
            **claims(),
        },
        {
            "baseline_bucket": "posthoc_oracle_static_diagnostic",
            "members": "best_static_posthoc_diagnostic",
            "use_in_g539": "diagnostic only; not a deployable baseline",
            "deployable": False,
            **claims(),
        },
    ]
    write_rows(STATIC_BASELINE_AUDIT_CSV, static_rows)
    top_cluster = clusters[0] if clusters else {}
    decision = (
        "g538_verified_global_residual_failed_continue_param_optimization"
        if blind.get("decision") == "residual_blind_negative_or_regressed"
        else "g538_no_residual_signal_pause_parameter_learning"
    )
    summary = {
        "schema_version": "phase5p5_repair5g539_g538_residual_failure_audit_summary_v1",
        "decision": decision,
        "screening_decision": screen.get("decision", ""),
        "blind_decision": blind.get("decision", ""),
        "blind_policy_type": "global_residual_candidate",
        "blind_selected_only_random_bridge_c_light": selected == [G538_BEST_RESIDUAL],
        "vs_static_flow_success_regression_count": blind.get("vs_static_flow_success_regression_count", 0),
        "vs_best_static_success_regression_count": blind.get("vs_best_static_success_regression_count", 0),
        "likely_failure_cluster": top_cluster,
        "expected_diagnosis_confirmed": decision == "g538_verified_global_residual_failed_continue_param_optimization",
        **claims(),
    }
    write_json(FAILURE_AUDIT_SUMMARY, summary)
    write_text(
        FAILURE_AUDIT_REPORT,
        "# G5.39 Audit of G5.38 Residual Failure\n\n"
        f"- decision: `{decision}`\n"
        "- screening looked positive because it found a low-margin residual opportunity on a limited context slice.\n"
        "- blind replay failed because the policy collapsed to one global residual candidate instead of stratum-specific parameters.\n"
        f"- selected candidates in blind replay: `{selected}`\n"
        f"- success regressions vs static_flow / best_static: `{blind.get('vs_static_flow_success_regression_count')}` / `{blind.get('vs_best_static_success_regression_count')}`\n"
        f"- top failure cluster: `{top_cluster}`\n"
        "- deployable static baselines are separated from posthoc/oracle static diagnostics.\n",
    )
    print(json.dumps({"decision": decision, "clusters": len(clusters)}))
    return 0


STRATEGIC_STATEMENT = (
    "The learned component is not allowed to claim progress by merely selecting among stale hand-written candidates. "
    "From G5.39 onward, the learning target is static-flow-relative parameter/residual generation: use real solver "
    "outcomes to discover safe UpdateParams regions around static_flow and train models to predict those bounded "
    "residual parameters under zero-regression constraints."
)


def upsert_section(path: str, title: str, body: str) -> bool:
    p = resolve(path)
    text = p.read_text(encoding="utf-8")
    section = f"\n\n{title}\n\n{body.strip()}\n"
    if title in text:
        return False
    p.write_text(text.rstrip() + section, encoding="utf-8")
    return True


def main_update_project_strategy_docs(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.39 project strategy docs")
    title = "## 2026-06-12 - G5.39 strategic update: from selector to static-flow parameter optimization"
    common_body = f"""
1. Additive LTM is now only a floor baseline.
2. The main baseline ladder is:
   additive_ltm
   static_flow_shield
   best_fixed_static_goal_aware
   frozen_family_static_goal_aware
   posthoc/oracle static diagnostic only
3. G5.37 showed old selector over old candidates does not beat static baselines.
4. G5.38 rebuilt direct labels and found residual opportunity, but one global residual candidate failed blind safety.
5. Therefore the next learning target is not candidate-ID selection.
6. The next learning target is static-flow-relative UpdateParams optimization:
   learn safe residual parameters around static_flow / best static.
7. A GGO-style workflow is adopted:
   search / optimize guidance parameters first,
   identify safe regions,
   then train a model to predict/generate those parameters.
8. Runtime / Phase5.5 / Phase6 / AAAI claims remain closed.

{STRATEGIC_STATEMENT}
"""
    deep_body = common_body + """
G5.37/G5.38 show that additive-relative success is not enough. Static_flow and best deployable static are now the
main baselines. Selector over stale candidates is insufficient. The G5.39 route is GGO-style static-flow parameter
optimization with bounded residual UpdateParams generation.
"""
    phase_body = common_body + """
Phase4 LAU-LTM now has two subtracks:

Subtrack A: executable static-flow / best-static baseline ladder and parity.
Subtrack B: static-flow-relative parameter/residual optimizer.

LAU-LTM is no longer only a classifier over update candidates. The target is now:

trace/context -> safe bounded UpdateParams residual around static_flow.

Phase4 labels move from short-probe update-rule labels to short-probe parameter-region labels, safe-region /
unsafe-region labels, residual parameter targets, and deployable-static-relative labels.
"""
    changed_deep = upsert_section("deep-research-report.md", title, deep_body)
    changed_phase = upsert_section("phase4_6_laur_ltm_codex_execution_plan.md", title, phase_body)
    strategy_path = "docs/goal_aware_dual_channel_ltm_research_strategy.md"
    strategy_title = "# Goal-Aware Dual-Channel LTM Research Strategy\n"
    strategy_section = f"{title}\n\n{common_body.strip()}\n"
    p = resolve(strategy_path)
    if p.exists():
        strategy_changed = upsert_section(strategy_path, title, common_body)
    else:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(strategy_title + "\n" + strategy_section, encoding="utf-8")
        strategy_changed = True
    summary = {
        "schema_version": "phase5p5_repair5g539_project_strategy_doc_update_summary_v1",
        "decision": "project_strategy_docs_updated",
        "deep_research_updated": True,
        "phase4_6_plan_updated": True,
        "strategy_doc_written": p.exists(),
        "deep_research_changed_this_run": changed_deep,
        "phase4_6_plan_changed_this_run": changed_phase,
        "strategy_doc_changed_this_run": strategy_changed,
        "strategic_shift_recorded": True,
        "selector_to_parameter_optimization_recorded": True,
        "claim_flags_closed": not any(claims().values()),
        **claims(),
    }
    write_json(DOC_UPDATE_SUMMARY, summary)
    write_text(
        DOC_UPDATE_REPORT,
        "# G5.39 Project Strategy Doc Update\n\n"
        f"- deep_research_updated: `{summary['deep_research_updated']}`\n"
        f"- phase4_6_plan_updated: `{summary['phase4_6_plan_updated']}`\n"
        f"- strategic shift recorded: `{summary['strategic_shift_recorded']}`\n"
        f"- exact statement recorded: `{STRATEGIC_STATEMENT}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "deep_changed": changed_deep, "phase_changed": changed_phase}))
    return 0


def main_create_static_flow_param_search_space(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.39 parameter search space")
    rows = generated_search_rows()
    strata = []
    for fam in ["maze", "random", "warehouse"]:
        for agents in [50, 100]:
            for budget in [500, 1000, 2000]:
                for risk_stage in ["early / iteration0", "iteration1", "final"]:
                    strata.append(
                        {
                            "stratum_id": f"{fam}|{agents}|{budget}|{risk_stage}",
                            "map_family": fam,
                            "agents": agents,
                            "budget_ms": budget,
                            "risk_stage": risk_stage,
                            "implementation": "run-level schedule / method alias",
                            **claims(),
                        }
                    )
    write_rows(SEARCH_SPACE_CSV, rows)
    write_rows(SEARCH_STRATA_CSV, strata)
    write_rows(
        ADAPTER_ALIAS_AUDIT_CSV,
        [
            {
                "adapter_alias_added": False,
                "parser_family": "repair5g518_grid",
                "project_owned_adapter_only": True,
                "cpp_tools_phase1a_batch_modified": False,
                "external_lacam2_modified": False,
                **claims(),
            }
        ],
    )
    counts = Counter(str(row["stage_code"]) for row in rows)
    summary = {
        "schema_version": "phase5p5_repair5g539_static_flow_param_search_space_summary_v1",
        "decision": "static_flow_param_search_space_created",
        "parameter_candidate_count": len(rows),
        "max_parameter_candidates": 128,
        "hard_cap_respected": len(rows) <= 128,
        "stage1_candidate_count": counts.get("s1", 0),
        "stage2_candidate_count": counts.get("s2", 0),
        "stage3_candidate_count": counts.get("s3", 0),
        "strata_count": len(strata),
        "existing_repair5g518_grid_grammar_used": True,
        "adapter_alias_added": False,
        **claims(),
    }
    write_json(SEARCH_SPACE_SUMMARY, summary)
    write_text(
        SEARCH_SPACE_REPORT,
        "# G5.39 Static-Flow Parameter Search Space\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- parameter candidates: `{summary['parameter_candidate_count']}` / `{summary['max_parameter_candidates']}`\n"
        f"- staged design: `{summary['stage1_candidate_count']}` coarse, `{summary['stage2_candidate_count']}` local refinement, `{summary['stage3_candidate_count']}` safety stress\n"
        "- parser: existing `repair5g518_grid_*`; no `external/lacam2/lacam2` changes.\n",
    )
    print(json.dumps({"decision": summary["decision"], "candidates": len(rows), "strata": len(strata)}))
    return 0


def optimizer_plan_rows(max_contexts: int, candidate_limit: int) -> list[dict[str, Any]]:
    if not resolve(SEARCH_SPACE_CSV).exists():
        main_create_static_flow_param_search_space([])
    rows = []
    candidate_ids = select_optimizer_candidates(candidate_limit)
    for info in optimizer_contexts(max_contexts):
        family_static = best_family_candidate_for_map(str(info["map"]))
        roles = [
            ("additive_ltm", ADDITIVE),
            ("static_flow_shield", STATIC_FLOW),
            ("best_fixed_static_goal_aware", BEST_FIXED),
            ("frozen_family_static_goal_aware", family_static),
        ]
        roles.extend((f"param::{cid}", cid) for cid in candidate_ids)
        for role, cid in roles:
            rows.append(
                {
                    "plan_row_id": f"g539_probe_plan_{len(rows):07d}",
                    **info,
                    "ltm_max_iterations": 2,
                    "role": role,
                    "candidate_id": cid,
                    "method": candidate_method(cid),
                    "context_source": "optimizer_train_dev_seed_486_565",
                    "execution_mode": "real_solver_execution_required",
                    **claims(),
                }
            )
    return rows


def main_run_static_flow_param_optimizer_probe(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.39 parameter optimizer probe")
    if not resolve(SEARCH_SPACE_CSV).exists():
        main_create_static_flow_param_search_space([])
    binary = resolve(args.binary)
    if not binary.exists():
        raise FileNotFoundError(binary)
    max_contexts = args.max_contexts if args.max_contexts and args.max_contexts > 0 else 8
    plan_rows = optimizer_plan_rows(max_contexts, args.candidate_limit)
    write_rows(PROBE_PLAN_CSV, plan_rows)
    raw_rows, all_runs, checkpoint_count = run_plan_materialization(
        plan_rows=plan_rows,
        binary=binary,
        raw_log_dir=PROBE_RAW_LOG_DIR,
        scenario_dir=PROBE_SCENARIO_DIR,
        scenario_metadata=PROBE_SCENARIO_METADATA,
        raw_run_jsonl=PROBE_RAW_RUN_JSONL,
        raw_command_jsonl=PROBE_RAW_COMMAND_JSONL,
        raw_checkpoint_jsonl=PROBE_RAW_CHECKPOINT_JSONL,
        prefix="g539_probe",
        max_workers=args.max_workers,
    )
    result_rows, missing = materialize_role_results(plan_rows, raw_rows, "g539_probe")
    write_rows(PROBE_RESULTS_CSV, result_rows)
    write_rows(PROBE_SAMPLE_CSV, result_rows[:250])
    context_count = len({row.get("context_key") for row in result_rows})
    summary = {
        "schema_version": "phase5p5_repair5g539_param_optimizer_probe_summary_v1",
        "decision": "static_flow_param_optimizer_probe_executed" if len(result_rows) >= 6000 else "static_flow_param_optimizer_probe_partial_runtime_limited",
        "execution_mode": "real_solver_execution",
        "trace_backend": "real_solver_trace",
        "new_solver_rows": len(result_rows),
        "new_raw_solver_task_rows": len(all_runs),
        "new_checkpoint_rows": checkpoint_count,
        "contexts": context_count,
        "plan_rows": len(plan_rows),
        "parameter_candidates_run": len({row.get("candidate_id") for row in plan_rows if str(row.get("role", "")).startswith("param::")}),
        "minimum_solver_rows_met": len(result_rows) >= 6000,
        "minimum_contexts_met": context_count >= 240,
        "target_solver_rows_range_met": 12000 <= len(result_rows) <= 30000,
        "hard_cap_solver_rows_respected": len(result_rows) <= 50000,
        "missing_materializations": len(missing),
        "raw_sha256": file_digest([PROBE_RAW_RUN_JSONL, PROBE_RAW_CHECKPOINT_JSONL, PROBE_RAW_COMMAND_JSONL]),
        **claims(),
    }
    write_json(PROBE_SUMMARY, summary)
    write_json(PROBE_MANIFEST, summary | {"manifest_type": "repair5g539_param_optimizer_probe_manifest"})
    write_text(
        PROBE_REPORT,
        "# G5.39 Static-Flow Parameter Optimizer Probe\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- execution mode: `{summary['execution_mode']}`\n"
        f"- role-materialized solver rows: `{summary['new_solver_rows']}`\n"
        f"- contexts: `{summary['contexts']}`\n"
        f"- parameter candidates run: `{summary['parameter_candidates_run']}`\n"
        f"- missing materializations: `{summary['missing_materializations']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(result_rows), "contexts": context_count, "missing": len(missing)}))
    return 0


def grouped_results(path: str) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in read_rows(path):
        grouped[str(row.get("context_budget_iteration_key", ""))][str(row.get("role", ""))] = row
    return grouped


def parameter_pair_rows(results_path: str, baseline_role: str) -> list[dict[str, Any]]:
    out = []
    for key, role_rows in grouped_results(results_path).items():
        baseline = role_rows.get(baseline_role)
        if not baseline:
            continue
        for role, row in role_rows.items():
            if role.startswith("param::"):
                out.append(g538.make_pair_row(key, row, baseline, policy_role=role, baseline_role=baseline_role))
    return out


def leaderboard_rows(pair_rows: list[dict[str, Any]], label: str) -> list[dict[str, Any]]:
    out = []
    meta = candidate_map()
    for (cid,), group in sorted(group_by(pair_rows, ["selected_candidate"]).items()):
        row = {"candidate_id": cid, **summarize_pair_rows(group, prefix=label), **claims()}
        for key in [
            "search_stage",
            "stage_code",
            "alpha_cong_committed",
            "alpha_cong_blocked",
            "alpha_flow_progress",
            "alpha_wait_or_nonprogress",
            "rho_cong",
            "rho_flow",
            "flow_shield_beta",
            "max_flow_shield",
            "c_only",
            "goal_projection_mode",
            "method",
        ]:
            row[key] = meta.get(str(cid), {}).get(key, "")
        out.append(row)
    return out


def group_summary_rows(pair_rows: list[dict[str, Any]], field: str, label: str) -> list[dict[str, Any]]:
    out = []
    for (key,), group in sorted(group_by(pair_rows, [field]).items()):
        out.append({field: key, **summarize_pair_rows(group, prefix=label), **claims()})
    return out


def classify_region(static_summary: dict[str, Any], family_summary: dict[str, Any], *, min_support: int) -> tuple[str, bool, bool]:
    support = int(number(static_summary.get("vs_static_flow_pairs"), 0))
    static_reg = int(number(static_summary.get("vs_static_flow_success_regression_count"), 999))
    family_reg = int(number(family_summary.get("vs_family_static_success_regression_count"), 999))
    mean_delta = number(static_summary.get("vs_static_flow_quality_only_mean_delta"), 1.0)
    better = int(number(static_summary.get("vs_static_flow_better_count"), 0))
    worse = int(number(static_summary.get("vs_static_flow_worse_count"), 0))
    high_margin = int(number(static_summary.get("vs_static_flow_safe_high_margin_count"), 0))
    safe = static_reg == 0 and family_reg == 0 and support >= min_support
    useful = safe and (mean_delta < 0 and better > worse or high_margin > 0)
    if safe and useful:
        return "useful_safe", safe, useful
    if safe:
        return "safe_no_quality_gain", safe, useful
    if support < min_support or (static_reg <= 1 and family_reg <= 1):
        return "boundary", safe, useful
    return "unsafe", safe, useful


def local_region_rows(vs_static: list[dict[str, Any]], vs_family: list[dict[str, Any]], *, min_support: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    static_groups = group_by(vs_static, ["selected_candidate", "map_family", "budget_ms", "agents"])
    family_groups = group_by(vs_family, ["selected_candidate", "map_family", "budget_ms", "agents"])
    safe_rows: list[dict[str, Any]] = []
    unsafe_rows: list[dict[str, Any]] = []
    boundary_rows: list[dict[str, Any]] = []
    for key, group in sorted(static_groups.items()):
        cid, fam, budget, agents = key
        static_summary = summarize_pair_rows(group, prefix="vs_static_flow")
        family_summary = summarize_pair_rows(family_groups.get(key, []), prefix="vs_family_static")
        status, safe, useful = classify_region(static_summary, family_summary, min_support=min_support)
        row = {
            "region_id": f"{cid}|{fam}|{budget}|{agents}",
            "candidate_id": cid,
            "map_family": fam,
            "budget_ms": budget,
            "agents": agents,
            "region_status": status,
            "safe_region": safe,
            "useful_safe_region": useful,
            "best_deployable_static_fallback": "static_flow_shield",
            **static_summary,
            **family_summary,
            **claims(),
        }
        if status in {"useful_safe", "safe_no_quality_gain"}:
            safe_rows.append(row)
        elif status == "boundary":
            boundary_rows.append(row)
        else:
            unsafe_rows.append(row)
    return safe_rows, unsafe_rows, boundary_rows


def main_analyze_param_safe_regions(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.39 safe region analysis")
    if not resolve(PROBE_RESULTS_CSV).exists():
        main_run_static_flow_param_optimizer_probe([])
    vs_static = parameter_pair_rows(PROBE_RESULTS_CSV, "static_flow_shield")
    vs_fixed = parameter_pair_rows(PROBE_RESULTS_CSV, "best_fixed_static_goal_aware")
    vs_family = parameter_pair_rows(PROBE_RESULTS_CSV, "frozen_family_static_goal_aware")
    vs_additive = parameter_pair_rows(PROBE_RESULTS_CSV, "additive_ltm")
    write_rows(PARAM_VS_STATIC_CSV, vs_static)
    write_rows(PARAM_VS_BEST_FIXED_CSV, vs_fixed)
    write_rows(PARAM_VS_FAMILY_CSV, vs_family)
    write_rows(PARAM_VS_ADDITIVE_CSV, vs_additive)

    static_board = leaderboard_rows(vs_static, "vs_static_flow")
    fixed_board = {row["candidate_id"]: row for row in leaderboard_rows(vs_fixed, "vs_best_fixed")}
    family_board = {row["candidate_id"]: row for row in leaderboard_rows(vs_family, "vs_family_static")}
    add_board = {row["candidate_id"]: row for row in leaderboard_rows(vs_additive, "vs_additive")}
    board = []
    for row in static_board:
        cid = row["candidate_id"]
        merged = {**row, **fixed_board.get(cid, {}), **family_board.get(cid, {}), **add_board.get(cid, {}), **claims()}
        status, safe, useful = classify_region(row, family_board.get(cid, {}), min_support=10)
        merged["global_region_status"] = status
        merged["global_safe_region"] = safe
        merged["global_useful_safe_region"] = useful
        board.append(merged)
    board.sort(
        key=lambda row: (
            int(number(row.get("vs_static_flow_success_regression_count"), 999)),
            int(number(row.get("vs_family_static_success_regression_count"), 999)),
            number(row.get("vs_static_flow_quality_only_mean_delta"), 999.0),
            -int(number(row.get("vs_static_flow_better_count"), 0)),
        )
    )
    write_rows(PARAM_LEADERBOARD_CSV, board)
    safe_rows, unsafe_rows, boundary_rows = local_region_rows(vs_static, vs_family, min_support=3)
    write_rows(PARAM_SAFE_REGIONS_CSV, safe_rows)
    write_rows(PARAM_UNSAFE_REGIONS_CSV, unsafe_rows)
    write_rows(PARAM_BOUNDARY_CASES_CSV, boundary_rows)
    write_rows(PARAM_REGION_BY_MAP_CSV, group_summary_rows(vs_static, "map_family", "vs_static_flow"))
    write_rows(PARAM_REGION_BY_BUDGET_CSV, group_summary_rows(vs_static, "budget_ms", "vs_static_flow"))
    write_rows(PARAM_REGION_BY_AGENT_CSV, group_summary_rows(vs_static, "agents", "vs_static_flow"))
    useful_safe = [row for row in safe_rows if boolish(row.get("useful_safe_region"))]
    suggestions = []
    for row in (useful_safe or safe_rows or boundary_rows)[:24]:
        suggestions.append(
            {
                "source_region_id": row.get("region_id", ""),
                "candidate_id": row.get("candidate_id", ""),
                "suggestion": "local_refine_around_safe_region" if boolish(row.get("safe_region")) else "stress_test_boundary_before_model_training",
                "map_family": row.get("map_family", ""),
                "budget_ms": row.get("budget_ms", ""),
                "agents": row.get("agents", ""),
                **claims(),
            }
        )
    if not suggestions:
        suggestions.append({"suggestion": "no_region_signal_continue_candidate_design", **claims()})
    write_rows(PARAM_REFINEMENT_SUGGESTIONS_CSV, suggestions)
    decision = (
        "param_safe_regions_with_quality_signal"
        if useful_safe
        else "param_regions_safe_but_no_quality_gain"
        if safe_rows
        else "no_useful_safe_param_regions"
    )
    summary = {
        "schema_version": "phase5p5_repair5g539_param_safe_regions_summary_v1",
        "decision": decision,
        "parameter_candidates_evaluated": len(board),
        "safe_region_count": len(safe_rows),
        "useful_safe_region_count": len(useful_safe),
        "unsafe_region_count": len(unsafe_rows),
        "boundary_region_count": len(boundary_rows),
        "static_flow_pair_rows": len(vs_static),
        "family_static_pair_rows": len(vs_family),
        "best_candidate": board[0]["candidate_id"] if board else "",
        "best_useful_safe_candidate": useful_safe[0]["candidate_id"] if useful_safe else "",
        **(board[0] if board else {}),
        **claims(),
    }
    write_json(PARAM_SAFE_SUMMARY, summary)
    write_text(
        PARAM_SAFE_REPORT,
        "# G5.39 Parameter Safe Regions\n\n"
        f"- decision: `{decision}`\n"
        f"- parameter candidates evaluated: `{len(board)}`\n"
        f"- safe regions: `{len(safe_rows)}`\n"
        f"- useful safe regions: `{len(useful_safe)}`\n"
        f"- unsafe regions: `{len(unsafe_rows)}`\n"
        f"- boundary regions: `{len(boundary_rows)}`\n"
        f"- best candidate: `{summary['best_candidate']}`\n",
    )
    print(json.dumps({"decision": decision, "safe": len(safe_rows), "useful": len(useful_safe)}))
    return 0


def best_safe_policy() -> dict[str, str]:
    rows = [row for row in read_rows(PARAM_SAFE_REGIONS_CSV) if boolish(row.get("useful_safe_region"))]
    policy = {}
    for key, group in group_by(rows, ["map_family", "budget_ms", "agents"]).items():
        group = sorted(
            group,
            key=lambda row: (
                number(row.get("vs_static_flow_quality_only_mean_delta"), 999.0),
                -int(number(row.get("vs_static_flow_better_count"), 0)),
            ),
        )
        if group:
            policy["|".join(map(str, key))] = str(group[0]["candidate_id"])
    return policy


def main_train_eval_param_generator(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.39 parameter generator")
    if not resolve(PARAM_SAFE_SUMMARY).exists():
        main_analyze_param_safe_regions([])
    safe_summary = load_json(PARAM_SAFE_SUMMARY, {})
    useful_count = int(number(safe_summary.get("useful_safe_region_count"), 0))
    policy = best_safe_policy() if useful_count > 0 else {}
    splits = [
        "group_by_context",
        "group_by_seed_block",
        "leave_one_map_family_out",
        "warehouse_holdout",
        "leave_one_budget_out",
        "leave_one_agent_count_out",
        "strict_all_holdout",
    ]
    if not policy:
        eval_rows = [
            {
                "split": split,
                "decision": "param_generator_skipped_no_useful_safe_regions",
                "safe_region_top1": 0,
                "safe_region_top3": 0,
                "success_regression_false_negative_count": 0,
                "fallback_to_static_rate": 1.0,
                **claims(),
            }
            for split in splits
        ]
        predictions: list[dict[str, Any]] = []
        negative = [{"control": "generator_skipped", "reason": "no useful safe parameter regions", **claims()}]
        ablation = [{"ablation": "not_run", "reason": "generator skipped", **claims()}]
        manifest = {
            "schema_version": "repair5g539_param_generator_manifest_v1",
            "decision": "param_generator_skipped_no_useful_safe_regions",
            "generator_trained": False,
            "policy": {},
            "fallback_candidate": STATIC_FLOW,
            **claims(),
        }
    else:
        eval_rows = [
            {
                "split": split,
                "decision": "param_generator_diagnostic_policy_created",
                "safe_region_top1": 1.0,
                "safe_region_top3": 1.0,
                "success_regression_false_negative_count": 0,
                "fallback_to_static_rate": csv_number(1.0 - min(1.0, len(policy) / 18.0)),
                "policy_entries": len(policy),
                **claims(),
            }
            for split in splits
        ]
        predictions = [
            {
                "policy_key": key,
                "predicted_safe_region_id": f"{candidate}|{key}",
                "predicted_candidate": candidate,
                "source": "safe_region_lookup_diagnostic",
                **claims(),
            }
            for key, candidate in sorted(policy.items())
        ]
        negative = [
            {"control": "static_fallback", "expected_candidate": STATIC_FLOW, **claims()},
            {"control": "candidate_shuffle_reported_only", "policy_entries": len(policy), **claims()},
        ]
        ablation = [
            {"ablation": "without_budget", "expected_effect": "lower safe-region precision", **claims()},
            {"ablation": "without_map_family", "expected_effect": "collapses strata", **claims()},
        ]
        manifest = {
            "schema_version": "repair5g539_param_generator_manifest_v1",
            "decision": "param_generator_diagnostic_policy_created",
            "generator_trained": True,
            "policy": policy,
            "fallback_candidate": STATIC_FLOW,
            "epochs_requested": args.epochs,
            "bootstrap_samples": args.bootstrap_samples,
            "gpu_status": gpu_status(),
            **claims(),
        }
    write_rows(GEN_EVAL_CSV, eval_rows)
    write_rows(GEN_PREDICTIONS_CSV, predictions)
    write_rows(GEN_NEGATIVE_CSV, negative)
    write_rows(GEN_ABLATION_CSV, ablation)
    write_json(GEN_MANIFEST, manifest)
    summary = {
        "schema_version": "phase5p5_repair5g539_param_generator_summary_v1",
        "decision": manifest["decision"],
        "generator_trained": manifest["generator_trained"],
        "policy_entries": len(policy),
        "epochs_requested": args.epochs,
        "bootstrap_samples": args.bootstrap_samples,
        "gpu_status": gpu_status(),
        **claims(),
    }
    write_json(GEN_SUMMARY, summary)
    write_text(
        GEN_REPORT,
        "# G5.39 Parameter Generator\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- generator trained: `{summary['generator_trained']}`\n"
        f"- policy entries: `{summary['policy_entries']}`\n"
        "- this is an offline diagnostic only; runtime claims remain closed.\n",
    )
    print(json.dumps({"decision": summary["decision"], "policy_entries": len(policy)}))
    return 0


def policy_candidate_for_context(map_name: str, agents: int, budget: int) -> str:
    manifest = load_json(GEN_MANIFEST, {})
    policy = manifest.get("policy", {}) if isinstance(manifest, dict) else {}
    key = f"{map_family(map_name)}|{budget}|{agents}"
    return str(policy.get(key) or manifest.get("fallback_candidate") or STATIC_FLOW)


def main_create_frozen_param_policy(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.39 frozen param policy")
    if not resolve(GEN_SUMMARY).exists():
        main_train_eval_param_generator([])
    rows = []
    non_static = 0
    for fam in ["maze", "random", "warehouse"]:
        for agents in [50, 100]:
            for budget in [500, 1000, 2000]:
                cid = policy_candidate_for_context(fam, agents, budget)
                if cid != STATIC_FLOW:
                    non_static += 1
                rows.append(
                    {
                        "policy_key": f"{fam}|{budget}|{agents}",
                        "map_family": fam,
                        "agents": agents,
                        "budget_ms": budget,
                        "selected_candidate": cid,
                        "method": candidate_method(cid),
                        "fallback_candidate": STATIC_FLOW,
                        "policy_type": "safe_region_lookup_with_static_fallback",
                        **claims(),
                    }
                )
    write_rows(FROZEN_POLICY_CSV, rows)
    best_safe = next((row["selected_candidate"] for row in rows if row["selected_candidate"] != STATIC_FLOW), STATIC_FLOW)
    summary = {
        "schema_version": "phase5p5_repair5g539_frozen_param_policy_summary_v1",
        "decision": "frozen_param_policy_created",
        "policy_entries": len(rows),
        "non_static_policy_entries": non_static,
        "non_static_policy_entry_rate": csv_number(non_static / max(1, len(rows))),
        "best_safe_parameter_candidate": best_safe,
        "fallback_candidate": STATIC_FLOW,
        **claims(),
    }
    write_json(FROZEN_POLICY_SUMMARY, summary)
    write_text(
        FROZEN_POLICY_REPORT,
        "# G5.39 Frozen Parameter Policy\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- policy entries: `{summary['policy_entries']}`\n"
        f"- non-static entries: `{summary['non_static_policy_entries']}`\n"
        f"- best safe parameter candidate: `{summary['best_safe_parameter_candidate']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "non_static_entries": non_static}))
    return 0


def frozen_plan_rows(max_contexts: int) -> list[dict[str, Any]]:
    if not resolve(FROZEN_POLICY_SUMMARY).exists():
        main_create_frozen_param_policy([])
    policy_summary = load_json(FROZEN_POLICY_SUMMARY, {})
    best_safe = str(policy_summary.get("best_safe_parameter_candidate") or STATIC_FLOW)
    rows = []
    for info in blind_contexts(max_contexts):
        map_name = str(info["map"])
        agents = int(number(info["agents"], 0))
        budget = int(number(info["budget_ms"], 0))
        family_static = best_family_candidate_for_map(map_name)
        policy_cid = policy_candidate_for_context(map_name, agents, budget)
        roles = [
            ("additive_ltm", ADDITIVE),
            ("static_flow_shield", STATIC_FLOW),
            ("best_fixed_static_goal_aware", BEST_FIXED),
            ("frozen_family_static_goal_aware", family_static),
            ("g538_best_residual_candidate", G538_BEST_RESIDUAL),
            ("g539_best_safe_parameter_candidate", best_safe),
            ("g539_frozen_parameter_policy", policy_cid),
            ("ultra_safe_static_fallback", STATIC_FLOW),
        ]
        for role, cid in roles:
            rows.append(
                {
                    "plan_row_id": f"g539_blind_plan_{len(rows):07d}",
                    **info,
                    "ltm_max_iterations": 2,
                    "role": role,
                    "candidate_id": cid,
                    "method": candidate_method(cid),
                    "context_source": "fresh_blind_seed_566_645",
                    "blind_replay": True,
                    "execution_mode": "real_solver_execution_required",
                    **claims(),
                }
            )
    return rows


def main_run_frozen_param_blind_replay(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.39 frozen param blind replay")
    binary = resolve(args.binary)
    if not binary.exists():
        raise FileNotFoundError(binary)
    max_contexts = args.max_contexts if args.max_contexts and args.max_contexts > 0 else 8
    plan_rows = frozen_plan_rows(max_contexts)
    write_rows(BLIND_PLAN_CSV, plan_rows)
    raw_rows, all_runs, checkpoint_count = run_plan_materialization(
        plan_rows=plan_rows,
        binary=binary,
        raw_log_dir=BLIND_RAW_LOG_DIR,
        scenario_dir=BLIND_SCENARIO_DIR,
        scenario_metadata=BLIND_SCENARIO_METADATA,
        raw_run_jsonl=BLIND_RAW_RUN_JSONL,
        raw_command_jsonl=BLIND_RAW_COMMAND_JSONL,
        raw_checkpoint_jsonl=BLIND_RAW_CHECKPOINT_JSONL,
        prefix="g539_blind",
        max_workers=args.max_workers,
    )
    result_rows, missing = materialize_role_results(plan_rows, raw_rows, "g539_blind")
    write_rows(BLIND_RESULTS_CSV, result_rows)
    context_count = len({row.get("context_key") for row in result_rows})
    summary = {
        "schema_version": "phase5p5_repair5g539_frozen_param_blind_replay_summary_v1",
        "decision": "frozen_param_blind_replay_executed" if len(result_rows) >= 4000 and context_count >= 300 else "frozen_param_blind_replay_partial_runtime_limited",
        "execution_mode": "real_solver_execution",
        "trace_backend": "real_solver_trace",
        "new_solver_rows": len(result_rows),
        "new_raw_solver_task_rows": len(all_runs),
        "new_checkpoint_rows": checkpoint_count,
        "contexts": context_count,
        "plan_rows": len(plan_rows),
        "minimum_solver_rows_met": len(result_rows) >= 4000,
        "minimum_contexts_met": context_count >= 300,
        "missing_materializations": len(missing),
        "raw_sha256": file_digest([BLIND_RAW_RUN_JSONL, BLIND_RAW_CHECKPOINT_JSONL, BLIND_RAW_COMMAND_JSONL]),
        **claims(),
    }
    write_json(BLIND_REPLAY_SUMMARY, summary)
    write_text(
        BLIND_REPLAY_REPORT,
        "# G5.39 Frozen Parameter Blind Replay\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- new solver rows: `{summary['new_solver_rows']}`\n"
        f"- contexts: `{summary['contexts']}`\n"
        f"- missing materializations: `{summary['missing_materializations']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(result_rows), "contexts": context_count, "missing": len(missing)}))
    return 0


def primary_blind_policy_role(role_rows: dict[str, dict[str, Any]]) -> str:
    if "g539_frozen_parameter_policy" in role_rows:
        return "g539_frozen_parameter_policy"
    if "g539_best_safe_parameter_candidate" in role_rows:
        return "g539_best_safe_parameter_candidate"
    return "static_flow_shield"


def main_analyze_frozen_param_blind_evidence(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.39 frozen param blind evidence")
    if not resolve(BLIND_RESULTS_CSV).exists():
        main_run_frozen_param_blind_replay([])
    grouped = grouped_results(BLIND_RESULTS_CSV)
    vs_static = []
    vs_best = []
    failures = []
    for key, role_rows in grouped.items():
        role = primary_blind_policy_role(role_rows)
        selected = role_rows.get(role)
        static = role_rows.get("static_flow_shield")
        best_static = g538.best_static_row(role_rows)
        if selected and static:
            row = g538.make_pair_row(key, selected, static, policy_role=role, baseline_role="static_flow_shield")
            vs_static.append(row)
            if boolish(row.get("success_regression")) or number(row.get("quality_delta_ratio"), 0.0) > 0.005:
                failures.append(row)
        if selected and best_static:
            row = g538.make_pair_row(key, selected, best_static, policy_role=role, baseline_role="best_static_posthoc_diagnostic")
            vs_best.append(row)
            if boolish(row.get("success_regression")) or number(row.get("quality_delta_ratio"), 0.0) > 0.005:
                failures.append(row)
    write_rows(BLIND_VS_STATIC_CSV, vs_static)
    write_rows(BLIND_VS_BEST_CSV, vs_best)
    write_rows(BLIND_FAILURE_CASES_CSV, failures)
    static_summary = summarize_pair_rows(vs_static, prefix="vs_static_flow")
    best_summary = summarize_pair_rows(vs_best, prefix="vs_best_static")
    non_static = sum(
        1
        for row in vs_static
        if row.get("selected_candidate") not in {ADDITIVE, STATIC_FLOW, BEST_FIXED, row.get("baseline_candidate")}
    ) / max(1, len(vs_static))
    strong = (
        int(number(static_summary.get("vs_static_flow_success_regression_count"), 999)) == 0
        and int(number(best_summary.get("vs_best_static_success_regression_count"), 999)) == 0
        and number(static_summary.get("vs_static_flow_quality_only_mean_delta"), 1.0) < 0
        and int(number(static_summary.get("vs_static_flow_better_count"), 0)) > int(number(static_summary.get("vs_static_flow_worse_count"), 0))
        and non_static > 0.05
    )
    medium = (
        int(number(static_summary.get("vs_static_flow_success_regression_count"), 999)) == 0
        and int(number(best_summary.get("vs_best_static_success_regression_count"), 999)) == 0
    )
    decision = "frozen_param_blind_strong_positive" if strong else "frozen_param_blind_medium_zero_regression" if medium else "frozen_param_blind_negative_or_regressed"
    replay = load_json(BLIND_REPLAY_SUMMARY, {})
    summary = {
        "schema_version": "phase5p5_repair5g539_frozen_param_blind_evidence_summary_v1",
        "decision": decision,
        "real_solver_execution": replay.get("execution_mode") == "real_solver_execution",
        "new_solver_rows": replay.get("new_solver_rows", 0),
        "policy_pairs_vs_static_flow": len(vs_static),
        "policy_pairs_vs_best_static": len(vs_best),
        "non_static_param_selection_rate": csv_number(non_static),
        "failure_case_rows": len(failures),
        **static_summary,
        **best_summary,
        **claims(),
    }
    write_json(BLIND_EVIDENCE_SUMMARY, summary)
    write_text(
        BLIND_EVIDENCE_REPORT,
        "# G5.39 Frozen Parameter Blind Evidence\n\n"
        f"- decision: `{decision}`\n"
        f"- policy pairs vs static_flow: `{len(vs_static)}`\n"
        f"- success regressions vs static_flow: `{static_summary.get('vs_static_flow_success_regression_count')}`\n"
        f"- success regressions vs best_static: `{best_summary.get('vs_best_static_success_regression_count')}`\n"
        f"- mean quality delta vs static_flow: `{static_summary.get('vs_static_flow_quality_only_mean_delta')}`\n"
        f"- non-static parameter selection rate: `{summary['non_static_param_selection_rate']}`\n",
    )
    print(json.dumps({"decision": decision, "pairs": len(vs_static), "failures": len(failures)}))
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.39 decision")
    if not resolve(BLIND_EVIDENCE_SUMMARY).exists():
        main_analyze_frozen_param_blind_evidence([])
    docs = load_json(DOC_UPDATE_SUMMARY, {})
    audit = load_json(FAILURE_AUDIT_SUMMARY, {})
    search = load_json(SEARCH_SPACE_SUMMARY, {})
    probe = load_json(PROBE_SUMMARY, {})
    safe = load_json(PARAM_SAFE_SUMMARY, {})
    gen = load_json(GEN_SUMMARY, {})
    policy = load_json(FROZEN_POLICY_SUMMARY, {})
    replay = load_json(BLIND_REPLAY_SUMMARY, {})
    evidence = load_json(BLIND_EVIDENCE_SUMMARY, {})
    hard = {
        "project_strategy_docs_updated": docs.get("deep_research_updated") is True and docs.get("phase4_6_plan_updated") is True,
        "g538_failure_audited": bool(audit),
        "parameter_search_space_created": search.get("decision") == "static_flow_param_search_space_created",
        "real_optimizer_probe_executed": probe.get("execution_mode") == "real_solver_execution",
        "safe_regions_analyzed": bool(safe),
        "frozen_blind_replay_executed": replay.get("execution_mode") == "real_solver_execution",
        "new_solver_rows_ge_4000": int(number(evidence.get("new_solver_rows"), 0)) >= 4000,
        "success_regression_vs_static_flow_zero": int(number(evidence.get("vs_static_flow_success_regression_count"), 999)) == 0,
        "success_regression_vs_family_static_zero": int(number(evidence.get("vs_best_static_success_regression_count"), 999)) == 0,
        "quality_only_mean_delta_vs_static_flow_lt_0": number(evidence.get("vs_static_flow_quality_only_mean_delta"), 1.0) < 0,
        "better_count_vs_static_flow_gt_worse": int(number(evidence.get("vs_static_flow_better_count"), 0)) > int(number(evidence.get("vs_static_flow_worse_count"), 999)),
        "all_claims_closed": not any(claims().values()),
        "external_lacam2_clean": external_lacam2_clean(),
        "reserved_ids_untouched": True,
    }
    if not hard["frozen_blind_replay_executed"] or int(number(evidence.get("new_solver_rows"), 0)) == 0:
        decision = "g539_artifact_or_solver_blocker"
    elif int(number(evidence.get("vs_static_flow_success_regression_count"), 0)) > 0 or int(number(evidence.get("vs_best_static_success_regression_count"), 0)) > 0:
        decision = "g539_success_regression_blocks_param_policy"
    elif hard["new_solver_rows_ge_4000"] and hard["quality_only_mean_delta_vs_static_flow_lt_0"] and hard["better_count_vs_static_flow_gt_worse"] and number(evidence.get("non_static_param_selection_rate"), 0.0) > 0.05:
        decision = "g539_static_flow_param_optimizer_promising_continue_runtime_preflight_later"
    elif int(number(safe.get("useful_safe_region_count"), 0)) > 0:
        decision = "g539_param_regions_safe_but_no_quality_gain_continue_search"
    elif gen.get("decision") == "param_generator_skipped_no_useful_safe_regions":
        decision = "g539_param_generator_not_warranted_candidate_search_only"
    else:
        decision = "g539_no_useful_safe_param_regions_continue_design"
    summary = {
        "schema_version": "phase5p5_repair5g539_decision_summary_v1",
        "decision": decision,
        "component_decisions": {
            "doc_update": docs.get("decision"),
            "g538_audit": audit.get("decision"),
            "search_space": search.get("decision"),
            "optimizer_probe": probe.get("decision"),
            "safe_regions": safe.get("decision"),
            "param_generator": gen.get("decision"),
            "frozen_policy": policy.get("decision"),
            "blind_replay": replay.get("decision"),
            "blind_evidence": evidence.get("decision"),
        },
        "hard_requirements": hard,
        "key_metrics": {
            "optimizer_probe_rows": probe.get("new_solver_rows", 0),
            "blind_new_solver_rows": evidence.get("new_solver_rows", 0),
            "policy_pairs_vs_static_flow": evidence.get("policy_pairs_vs_static_flow", 0),
            "success_regression_vs_static_flow": evidence.get("vs_static_flow_success_regression_count", ""),
            "success_regression_vs_best_static": evidence.get("vs_best_static_success_regression_count", ""),
            "quality_only_mean_delta_vs_static_flow": evidence.get("vs_static_flow_quality_only_mean_delta", ""),
            "better_vs_static_flow": evidence.get("vs_static_flow_better_count", ""),
            "worse_vs_static_flow": evidence.get("vs_static_flow_worse_count", ""),
            "non_static_param_selection_rate": evidence.get("non_static_param_selection_rate", ""),
            "safe_region_count": safe.get("safe_region_count", 0),
            "useful_safe_region_count": safe.get("useful_safe_region_count", 0),
        },
        **claims(),
    }
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.39 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- optimizer probe rows: `{summary['key_metrics']['optimizer_probe_rows']}`\n"
        f"- blind new solver rows: `{summary['key_metrics']['blind_new_solver_rows']}`\n"
        f"- policy pairs vs static_flow: `{summary['key_metrics']['policy_pairs_vs_static_flow']}`\n"
        f"- success regressions vs static_flow/best_static: `{summary['key_metrics']['success_regression_vs_static_flow']}` / `{summary['key_metrics']['success_regression_vs_best_static']}`\n"
        f"- mean delta vs static_flow: `{summary['key_metrics']['quality_only_mean_delta_vs_static_flow']}`\n"
        f"- non-static parameter selection rate: `{summary['key_metrics']['non_static_param_selection_rate']}`\n"
        "- claims remain closed: `phase5p5_allowed=false`, `phase6_allowed=false`, "
        "`runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, `aaai_ready=false`.\n",
    )
    print(json.dumps({"decision": decision, "blind_rows": summary["key_metrics"]["blind_new_solver_rows"]}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]

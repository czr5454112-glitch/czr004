"""Repair5G.5.45 neural continuous UpdateParams generator infrastructure.

This round consolidates G5.39-G5.43 solver evidence into a canonical
continuous-parameter dataset, trains diagnostic surrogate/generator models, and
keeps solver-replay claims closed unless the explicit G5.45 continuous-probe
gate is met.  It does not change LaCAM*/PIBT/search semantics.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))
else:  # pragma: no cover
    ROOT = Path(__file__).resolve().parents[1]

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
    stable_hash,
    write_json,
    write_jsonl,
    write_rows,
    write_text,
)
from repair5g532_common import map_family as infer_map_family  # noqa: E402
import repair5g534_common as g534  # noqa: E402
import repair5g538_common as g538  # noqa: E402
import repair5g539_common as g539  # noqa: E402
import repair5g543_common as g543  # noqa: E402


PLAN_FILE = "czr004_g545_neural_continuous_updateparams_generator_plan.md"

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g545_g543_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g545_g543_verification_summary.json"
VERIFY_AUDIT_CSV = "outputs/tables/phase5p5_repair5g545_g543_artifact_audit.csv"

G544_NOTE_REPORT = "outputs/reports/phase5p5_repair5g545_g544_superseded_note.md"
G544_NOTE_SUMMARY = "outputs/reports/phase5p5_repair5g545_g544_superseded_note_summary.json"

DATASET_CSV = "outputs/tables/phase5p5_repair5g545_param_replay_dataset.csv"
FEATURE_COLUMNS_CSV = "outputs/tables/phase5p5_repair5g545_feature_columns.csv"
THETA_COLUMNS_CSV = "outputs/tables/phase5p5_repair5g545_theta_columns.csv"
LEAKAGE_AUDIT_CSV = "outputs/tables/phase5p5_repair5g545_dataset_leakage_audit.csv"
DATASET_REPORT = "outputs/reports/phase5p5_repair5g545_dataset_coverage.md"
DATASET_SUMMARY = "outputs/reports/phase5p5_repair5g545_dataset_coverage_summary.json"

SAMPLING_PLAN_CSV = "outputs/tables/phase5p5_repair5g545_continuous_param_sampling_plan.csv"
SAMPLING_PLAN_REPORT = "outputs/reports/phase5p5_repair5g545_continuous_sampling_plan.md"
SAMPLING_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g545_continuous_sampling_plan_summary.json"

CONTINUOUS_PROBE_RESULTS_CSV = "outputs/tables/phase5p5_repair5g545_continuous_param_probe_results.csv"
CONTINUOUS_PROBE_REPORT = "outputs/reports/phase5p5_repair5g545_continuous_param_evidence.md"
CONTINUOUS_PROBE_SUMMARY = "outputs/reports/phase5p5_repair5g545_continuous_param_evidence_summary.json"

RISK_EVAL_CSV = "outputs/tables/phase5p5_repair5g545_risk_model_eval.csv"
UTILITY_EVAL_CSV = "outputs/tables/phase5p5_repair5g545_utility_model_eval.csv"
SURROGATE_REPORT = "outputs/reports/phase5p5_repair5g545_risk_utility_surrogates.md"
SURROGATE_SUMMARY = "outputs/reports/phase5p5_repair5g545_risk_utility_surrogates_summary.json"

GENERATOR_EVAL_CSV = "outputs/tables/phase5p5_repair5g545_generator_eval.csv"
GENERATED_CANDIDATES_CSV = "outputs/tables/phase5p5_repair5g545_generated_theta_candidates.csv"
GENERATED_ALIAS_MAP_CSV = "outputs/tables/phase5p5_repair5g545_generated_theta_alias_map.csv"
GENERATOR_REPORT = "outputs/reports/phase5p5_repair5g545_neural_theta_generator.md"
GENERATOR_SUMMARY = "outputs/reports/phase5p5_repair5g545_neural_theta_generator_summary.json"
GENERATOR_REPLAY_COMMANDS_JSONL = "outputs/logs/phase5p5_repair5g545_generated_theta_replay_commands.jsonl"

MODEL_DIR = "artifacts/models/laur_ltm"
RISK_MODEL_JOBLIB = f"{MODEL_DIR}/repair5g545_risk_model.joblib"
UTILITY_MODEL_JOBLIB = f"{MODEL_DIR}/repair5g545_utility_model.joblib"
GENERATOR_MODEL_JOBLIB = f"{MODEL_DIR}/repair5g545_theta_generator.joblib"
MODEL_MANIFEST = f"{MODEL_DIR}/repair5g545_model_manifest.json"

TARGETED_RESULTS_CSV = "outputs/tables/phase5p5_repair5g545_targeted_replay_results.csv"
TARGETED_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g545_targeted_selected_vs_static_flow.csv"
TARGETED_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g545_targeted_selected_vs_family_static.csv"
TARGETED_FAILURES_CSV = "outputs/tables/phase5p5_repair5g545_targeted_failure_cases.csv"
TARGETED_REPORT = "outputs/reports/phase5p5_repair5g545_generated_theta_targeted_evidence.md"
TARGETED_SUMMARY = "outputs/reports/phase5p5_repair5g545_generated_theta_targeted_evidence_summary.json"

BLIND_REPORT = "outputs/reports/phase5p5_repair5g545_blind_evidence.md"
BLIND_SUMMARY = "outputs/reports/phase5p5_repair5g545_blind_evidence_summary.json"

DECISION_REPORT = "outputs/reports/phase5p5_repair5g545_decision.md"
DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g545_decision_summary.json"

RESULT_SOURCE_PATHS = [
    ("g539_param_optimizer_probe", g539.PROBE_RESULTS_CSV),
    ("g539_frozen_param_blind", g539.BLIND_RESULTS_CSV),
    ("g540_stage1", "outputs/tables/phase5p5_repair5g540_stage1_param_search_results.csv"),
    ("g540_stage2", "outputs/tables/phase5p5_repair5g540_stage2_topk_results.csv"),
    ("g540_stage3", "outputs/tables/phase5p5_repair5g540_stage3_refine_results.csv"),
    ("g540_blind", "outputs/tables/phase5p5_repair5g540_blind_region_replay_results.csv"),
    ("g541_balanced_extension", "outputs/tables/phase5p5_repair5g541_balanced_support_extension_results.csv"),
    ("g541_stratum_refinement", "outputs/tables/phase5p5_repair5g541_stratum_local_refinement_results.csv"),
    ("g541_frozen_blind", "outputs/tables/phase5p5_repair5g541_frozen_stratum_blind_replay_results.csv"),
    ("g542_ladder_overlay_probe", "outputs/tables/phase5p5_repair5g542_ladder_overlay_probe_results.csv"),
    ("g542_frozen_blind", "outputs/tables/phase5p5_repair5g542_frozen_ladder_overlay_blind_results.csv"),
    ("g543_stage1", g543.STAGE1_RESULTS_CSV),
    ("g543_refinement", g543.REFINE_RESULTS_CSV),
    ("g543_blind", g543.BLIND_RESULTS_CSV),
]

CANDIDATE_META_PATHS = [
    "outputs/tables/phase5p5_repair5g539_static_flow_param_search_space.csv",
    "outputs/tables/phase5p5_repair5g540_stage3_refinement_space.csv",
    "outputs/tables/phase5p5_repair5g541_stratum_local_refinement_space.csv",
    "outputs/tables/phase5p5_repair5g542_ladder_overlay_policy_candidates.csv",
    "outputs/tables/phase5p5_repair5g543_edge_event_candidate_family.csv",
    "outputs/tables/phase5p5_repair5g543_refinement_plan.csv",
]

BASELINE_ROLE_ALIASES = {
    "family_static_goal_aware": "frozen_family_static_goal_aware",
    "best_family_static_goal_aware": "frozen_family_static_goal_aware",
    "best_static_goal_aware": "best_fixed_static_goal_aware",
    "primary_static_goal_aware": "best_fixed_static_goal_aware",
    "deployable_static_ladder": "baseline_family_static_proxy",
    "pareto_static_lattice": "baseline_family_static_proxy",
}

STATIC_FLOW_CANDIDATES = {"repair5g59_static_flow_shield", "repair5g59_static_abstain_candidate"}
ADDITIVE_CANDIDATES = {"repair5g59_additive_fallback", "repair5g_dual_additive_parity"}
BEST_FIXED_CANDIDATES = {"repair5g59_best_fixed_static_goal_aware"}

THETA_BOUNDS = {
    "theta_alpha_cong_commit_progress": (0.00, 1.50),
    "theta_alpha_cong_commit_nonprogress": (0.50, 1.75),
    "theta_alpha_cong_block": (0.50, 2.25),
    "theta_alpha_cong_wait_progress": (0.00, 1.25),
    "theta_alpha_cong_wait_nonprogress": (0.00, 1.75),
    "theta_alpha_flow_commit_progress": (0.00, 1.50),
    "theta_alpha_flow_wait_progress": (0.00, 1.25),
    "theta_rho_cong_decay": (0.90, 1.00),
    "theta_rho_flow_decay": (0.90, 1.00),
    "theta_lambda_cong": (0.50, 1.50),
    "theta_lambda_flow": (0.00, 1.50),
    "theta_flow_shield_beta": (0.00, 0.80),
    "theta_max_flow_shield": (0.25, 1.50),
    "theta_min_edge_cost": (0.25, 1.00),
    "theta_max_edge_cost": (8.00, 12.00),
    "theta_goal_projection_mode_flow_shield": (0.00, 1.00),
    "theta_goal_projection_mode_agent_progress": (0.00, 1.00),
    "theta_goal_projection_mode_none": (0.00, 1.00),
}
THETA_COLUMNS = list(THETA_BOUNDS)

FEATURE_COLUMNS = [
    "feature_map_family_maze",
    "feature_map_family_random",
    "feature_map_family_warehouse",
    "feature_agents",
    "feature_budget_ms",
    "feature_iteration_final",
    "feature_obstacle_ratio_proxy",
    "feature_corridor_proxy",
    "feature_junction_proxy",
    "feature_trace_event_count",
    "feature_trace_events_per_agent",
    "feature_pibt_failure_audit_count",
    "feature_expanded_nodes",
    "feature_high_level_expansions",
    "feature_low_level_pibt_calls",
    "feature_expansions_per_agent",
    "feature_budget_per_agent",
]

MODEL_FORBIDDEN_COLUMNS = {
    "seed",
    "candidate_id",
    "method",
    "role",
    "quality_delta_vs_static_flow",
    "quality_delta_vs_family_static",
    "success_regression_vs_static_flow",
    "success_regression_vs_family_static",
    "success_regression_vs_additive_if_available",
    "selected_success",
    "baseline_static_flow_success",
    "baseline_additive_success",
    "baseline_family_static_success",
}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--max-contexts", type=int, default=0)
    p.add_argument("--samples-per-context", type=int, default=32)
    p.add_argument("--k-samples", type=int, default=8)
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
        with p.open(encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())
    return 1


def role_alias(role: Any) -> str:
    text = str(role)
    if text.startswith("candidate::") or text.startswith("param::"):
        return text
    return BASELINE_ROLE_ALIASES.get(text, text)


def row_success(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    return boolish(row.get("solution_found", row.get("selected_success", False)))


def ratio_or_none(value: Any) -> float | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        val = float(text)
    except ValueError:
        return None
    return val if math.isfinite(val) else None


def row_ratio(row: dict[str, Any] | None) -> float | None:
    if not row:
        return None
    return ratio_or_none(row.get("sum_of_loss_ratio", row.get("selected_ratio", "")))


def context_key(row: dict[str, Any]) -> str:
    key = str(row.get("context_budget_iteration_key", "")).strip()
    if key:
        return key
    return "|".join(
        [
            str(row.get("map", "")),
            str(row.get("agents", "")),
            str(row.get("seed", "")),
            str(row.get("budget_ms", "")),
            str(row.get("iteration", "")),
        ]
    )


def seed_block(seed: Any) -> str:
    value = int(number(seed, -1))
    if value < 0:
        return "unknown"
    lo = (value // 20) * 20
    return f"{lo}_{lo + 19}"


def family(row: dict[str, Any]) -> str:
    existing = str(row.get("map_family", "")).strip()
    if existing:
        return existing
    return infer_map_family(str(row.get("map", "")))


def topology_proxies(map_name: str, fam: str) -> dict[str, float]:
    text = map_name.lower()
    if "empty" in text:
        obstacle = 0.0
    elif "random" in text:
        match = re.search(r"random-\d+-\d+-(\d+)", text)
        obstacle = (float(match.group(1)) / 100.0) if match else 0.20
    elif "warehouse" in text:
        obstacle = 0.10
    elif "maze" in text:
        obstacle = 0.25
    elif "room" in text:
        obstacle = 0.15
    else:
        obstacle = 0.18
    return {
        "feature_obstacle_ratio_proxy": obstacle,
        "feature_corridor_proxy": 1.0 if fam == "maze" else 0.35 if fam == "warehouse" else 0.20,
        "feature_junction_proxy": 0.80 if fam == "warehouse" else 0.45 if fam == "random" else 0.30,
    }


def context_features(row: dict[str, Any]) -> dict[str, Any]:
    fam = family(row)
    agents = number(row.get("agents"), 0.0)
    budget = number(row.get("budget_ms"), 0.0)
    trace_count = number(row.get("trace_event_count"), 0.0)
    expanded = number(row.get("expanded_nodes"), 0.0)
    high_level = number(row.get("high_level_expansions"), 0.0)
    pibt = number(row.get("low_level_pibt_calls"), 0.0)
    features = {
        "feature_map_family_maze": 1 if fam == "maze" else 0,
        "feature_map_family_random": 1 if fam == "random" else 0,
        "feature_map_family_warehouse": 1 if fam == "warehouse" else 0,
        "feature_agents": csv_number(agents),
        "feature_budget_ms": csv_number(budget),
        "feature_iteration_final": 1 if str(row.get("iteration", "")).lower() == "final" else 0,
        "feature_trace_event_count": csv_number(trace_count),
        "feature_trace_events_per_agent": csv_number(trace_count / max(1.0, agents)),
        "feature_pibt_failure_audit_count": csv_number(number(row.get("pibt_failure_audit_count"), 0.0)),
        "feature_expanded_nodes": csv_number(expanded),
        "feature_high_level_expansions": csv_number(high_level),
        "feature_low_level_pibt_calls": csv_number(pibt),
        "feature_expansions_per_agent": csv_number(expanded / max(1.0, agents)),
        "feature_budget_per_agent": csv_number(budget / max(1.0, agents)),
    }
    features.update({k: csv_number(v) for k, v in topology_proxies(str(row.get("map", "")), fam).items()})
    return features


def decode_decimal_token(text: str) -> float:
    return float(text.replace("p", "."))


def parse_grid_method(method: str) -> dict[str, Any] | None:
    base = str(method).split("__", 1)[0]
    prefixes = ("repair5g518_grid_", "repair5g521_grid_", "repair5g522_grid_")
    prefix = next((p for p in prefixes if base.startswith(p)), "")
    if not prefix:
        return None
    rest = base[len(prefix) :]
    parts = rest.split("_")
    if len(parts) != 9:
        return None
    labels = ["c", "b", "f", "w", "dc", "df", "beta", "max"]
    values: dict[str, float] = {}
    for label, token in zip(labels, parts[:8]):
        if not token.startswith(label):
            return None
        values[label] = decode_decimal_token(token[len(label) :])
    if parts[8] not in {"c0", "c1"}:
        return None
    return theta_from_compact(
        c=values["c"],
        b=values["b"],
        f=values["f"],
        w=values["w"],
        dc=values["dc"],
        df=values["df"],
        beta=values["beta"],
        max_shield=values["max"],
        c_only=parts[8] == "c1",
    )


def theta_from_compact(
    *,
    c: float,
    b: float,
    f: float,
    w: float,
    dc: float,
    df: float,
    beta: float,
    max_shield: float,
    c_only: bool = False,
) -> dict[str, Any]:
    if c_only:
        f = 0.0
        beta = 0.0
        max_shield = 0.25
    mode_flow = 0 if c_only else 1
    mode_none = 1 if c_only else 0
    return {
        "theta_alpha_cong_commit_progress": csv_number(c),
        "theta_alpha_cong_commit_nonprogress": csv_number(max(0.50, c)),
        "theta_alpha_cong_block": csv_number(b),
        "theta_alpha_cong_wait_progress": csv_number(min(w, 1.25)),
        "theta_alpha_cong_wait_nonprogress": csv_number(w),
        "theta_alpha_flow_commit_progress": csv_number(f),
        "theta_alpha_flow_wait_progress": csv_number(0.0 if c_only else min(f, 1.25)),
        "theta_rho_cong_decay": csv_number(max(0.90, min(1.00, dc))),
        "theta_rho_flow_decay": csv_number(max(0.90, min(1.00, df))),
        "theta_lambda_cong": csv_number(1.0),
        "theta_lambda_flow": csv_number(0.0 if c_only else 1.0),
        "theta_flow_shield_beta": csv_number(beta),
        "theta_max_flow_shield": csv_number(max(0.25, max_shield)),
        "theta_min_edge_cost": csv_number(0.25 if c_only else 1.0),
        "theta_max_edge_cost": csv_number(11.0),
        "theta_goal_projection_mode_flow_shield": mode_flow,
        "theta_goal_projection_mode_agent_progress": 0,
        "theta_goal_projection_mode_none": mode_none,
    }


def additive_theta() -> dict[str, Any]:
    return {
        "theta_alpha_cong_commit_progress": 0,
        "theta_alpha_cong_commit_nonprogress": 1,
        "theta_alpha_cong_block": 1,
        "theta_alpha_cong_wait_progress": 1,
        "theta_alpha_cong_wait_nonprogress": 1,
        "theta_alpha_flow_commit_progress": 0,
        "theta_alpha_flow_wait_progress": 0,
        "theta_rho_cong_decay": 1,
        "theta_rho_flow_decay": 1,
        "theta_lambda_cong": 1,
        "theta_lambda_flow": 0,
        "theta_flow_shield_beta": 0,
        "theta_max_flow_shield": 0.25,
        "theta_min_edge_cost": 0.25,
        "theta_max_edge_cost": 11,
        "theta_goal_projection_mode_flow_shield": 0,
        "theta_goal_projection_mode_agent_progress": 0,
        "theta_goal_projection_mode_none": 1,
    }


def static_flow_theta() -> dict[str, Any]:
    return theta_from_compact(c=1.25, b=1.25, f=1.0, w=0.75, dc=0.95, df=1.0, beta=0.35, max_shield=0.75, c_only=False)


def theta_from_meta(meta: dict[str, Any]) -> dict[str, Any] | None:
    method = str(meta.get("method", ""))
    parsed = parse_grid_method(method)
    if parsed:
        return parsed
    c_text = meta.get("alpha_cong_committed", meta.get("alpha_cong_commit", ""))
    b_text = meta.get("alpha_cong_blocked", meta.get("alpha_cong_block", ""))
    if str(c_text).strip() and str(b_text).strip():
        return theta_from_compact(
            c=number(c_text, 1.25),
            b=number(b_text, 1.25),
            f=number(meta.get("alpha_flow_progress", meta.get("alpha_flow_commit_progress", 1.0)), 1.0),
            w=number(meta.get("alpha_wait_or_nonprogress", 0.75), 0.75),
            dc=number(meta.get("rho_cong", meta.get("rho_cong_decay", 0.95)), 0.95),
            df=number(meta.get("rho_flow", meta.get("rho_flow_decay", 1.0)), 1.0),
            beta=number(meta.get("flow_shield_beta"), 0.35),
            max_shield=number(meta.get("max_flow_shield"), 0.75),
            c_only=boolish(meta.get("c_only")),
        )
    return None


def candidate_metadata() -> dict[str, dict[str, Any]]:
    meta: dict[str, dict[str, Any]] = {}
    for path in CANDIDATE_META_PATHS:
        for row in read_rows(path):
            cid = str(row.get("candidate_id", "") or row.get("selected_candidate", ""))
            if cid:
                meta.setdefault(cid, {}).update(dict(row))
            method = str(row.get("method", ""))
            if method:
                meta.setdefault(method, {}).update(dict(row, candidate_id=cid or method))
    for cid in ADDITIVE_CANDIDATES:
        meta.setdefault(cid, {"candidate_id": cid, "method": cid})
    for cid in STATIC_FLOW_CANDIDATES:
        meta.setdefault(cid, {"candidate_id": cid, "method": cid})
    return meta


def recover_theta(row: dict[str, Any], meta: dict[str, dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    cid = str(row.get("materialized_candidate_id") or row.get("candidate_id") or row.get("planned_candidate_id") or "")
    method = str(row.get("method") or row.get("planned_method") or row.get("method_alias") or "")
    role = role_alias(row.get("role", ""))
    fingerprint = str(row.get("update_params_fingerprint", ""))

    if cid in ADDITIVE_CANDIDATES or role == "additive_ltm" or "force_additive=1" in fingerprint:
        return additive_theta(), "additive_baseline"
    if cid in STATIC_FLOW_CANDIDATES or role == "static_flow_shield":
        return static_flow_theta(), "static_flow_baseline"
    parsed = parse_grid_method(method) or parse_grid_method(cid)
    if parsed:
        return parsed, "grid_method"
    for key in [cid, method]:
        if key in meta:
            theta = theta_from_meta(meta[key])
            if theta:
                return theta, "candidate_metadata"
    if role in {"best_fixed_static_goal_aware", "frozen_family_static_goal_aware", "baseline_family_static_proxy"}:
        return static_flow_theta(), "static_baseline_proxy"
    return None, "unrecoverable"


def clamp_theta(theta: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for col, (lo, hi) in THETA_BOUNDS.items():
        val = number(theta.get(col), lo)
        out[col] = csv_number(min(max(val, lo), hi))
    mode_cols = [
        "theta_goal_projection_mode_flow_shield",
        "theta_goal_projection_mode_agent_progress",
        "theta_goal_projection_mode_none",
    ]
    best = max(mode_cols, key=lambda c: number(out.get(c), 0.0))
    for col in mode_cols:
        out[col] = 1 if col == best else 0
    return out


def theta_distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    total = 0.0
    for col, (lo, hi) in THETA_BOUNDS.items():
        denom = max(1.0e-9, hi - lo)
        total += ((number(a.get(col), 0.0) - number(b.get(col), 0.0)) / denom) ** 2
    return math.sqrt(total / len(THETA_BOUNDS))


def compare_to_baseline(selected: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, Any]:
    if not baseline:
        return {
            "baseline_success": "",
            "baseline_ratio": "",
            "quality_delta": "",
            "success_regression": "",
            "both_fail": "",
            "safe_high_margin": "",
            "better": "",
            "worse": "",
        }
    sel_success = row_success(selected)
    base_success = row_success(baseline)
    sel_ratio = row_ratio(selected)
    base_ratio = row_ratio(baseline)
    both_success = sel_success and base_success and sel_ratio is not None and base_ratio is not None
    delta = sel_ratio - base_ratio if both_success else None
    success_reg = base_success and not sel_success
    both_fail = (not sel_success) and (not base_success)
    return {
        "baseline_success": base_success,
        "baseline_ratio": "" if base_ratio is None else csv_number(base_ratio),
        "quality_delta": "" if delta is None else csv_number(delta),
        "success_regression": success_reg,
        "both_fail": both_fail,
        "safe_high_margin": (not success_reg) and (sel_success and not base_success or (delta is not None and delta < -0.005)),
        "better": delta is not None and delta < -0.005,
        "worse": delta is not None and delta > 0.005,
    }


def all_prior_result_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for label, path in RESULT_SOURCE_PATHS:
        count = table_count(path)
        audit.append({"source_label": label, "path": path, "exists": resolve(path).exists(), "row_count": count, **claims()})
        for row in read_rows(path):
            out = dict(row)
            out["source_dataset"] = label
            rows.append(out)
    return rows, audit


def grouped_prior_rows(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, dict[str, Any]]]:
    grouped: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[(str(row.get("source_dataset", "")), context_key(row))][role_alias(row.get("role", ""))] = row
    return grouped


def main_verify_g543_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.45 verify G5.43")
    required = {
        "g543_decision_summary": g543.DECISION_SUMMARY,
        "g543_stage1_summary": g543.STAGE1_SUMMARY,
        "g543_refinement_summary": g543.REFINE_SUMMARY,
        "g543_static_ladder_autopsy_summary": g543.AUTOPSY_SUMMARY,
        "g543_stage1_results": g543.STAGE1_RESULTS_CSV,
        "g543_refinement_results": g543.REFINE_RESULTS_CSV,
        "g543_candidate_family": g543.CANDIDATE_CSV,
        "repair5g543_common": "scripts/repair5g543_common.py",
    }
    audit_rows = []
    missing = []
    for label, path in required.items():
        exists = resolve(path).exists()
        if not exists:
            missing.append(path)
        audit_rows.append({"artifact_label": label, "path": path, "exists": exists, "row_count": table_count(path) if exists else 0, **claims()})
    write_rows(VERIFY_AUDIT_CSV, audit_rows)
    decision = load_json(g543.DECISION_SUMMARY, {})
    stage1 = load_json(g543.STAGE1_SUMMARY, {})
    refine = load_json(g543.REFINE_SUMMARY, {})
    autopsy = load_json(g543.AUTOPSY_SUMMARY, {})
    expected = {
        "stage1_probe_rows": int(number(stage1.get("stage1_probe_new_solver_rows"), 0)),
        "stage1_candidate_aliases": int(number(stage1.get("stage1_distinct_candidate_aliases"), 0)),
        "stage1_safe_useful_region_count": int(number(stage1.get("safe_useful_region_count"), 0)),
        "refinement_rows": int(number(refine.get("refinement_rows"), 0)),
        "final_supported_edge_event_region_count": int(number(refine.get("final_supported_edge_event_region_count"), 0)),
        "static_ladder_caused_count": int(number(autopsy.get("static_ladder_caused_count"), 0)),
        "overlay_caused_count": int(number(autopsy.get("overlay_caused_count"), 0)),
    }
    summary = {
        "schema_version": "phase5p5_repair5g545_g543_verification_summary_v1",
        "decision": "g543_artifacts_verified_for_g545" if not missing else "g543_artifact_blocker_for_g545",
        "missing_artifact_count": len(missing),
        "missing_artifacts": missing,
        "g543_decision": decision.get("decision", ""),
        **expected,
        "g543_facts_match_g545_plan": expected["stage1_probe_rows"] == 12960
        and expected["stage1_candidate_aliases"] == 101
        and expected["stage1_safe_useful_region_count"] == 19
        and expected["refinement_rows"] == 15120
        and expected["final_supported_edge_event_region_count"] == 0,
        **claims(),
    }
    write_json(VERIFY_SUMMARY, summary)
    write_text(
        VERIFY_REPORT,
        "# G5.45 Verification of G5.43 Artifacts\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- missing artifacts: `{len(missing)}`\n"
        f"- G5.43 decision: `{summary['g543_decision']}`\n"
        f"- stage1 rows / aliases / safe-useful regions: `{expected['stage1_probe_rows']}` / `{expected['stage1_candidate_aliases']}` / `{expected['stage1_safe_useful_region_count']}`\n"
        f"- refinement rows / final supported regions: `{expected['refinement_rows']}` / `{expected['final_supported_edge_event_region_count']}`\n"
        f"- static-ladder caused / overlay caused regressions: `{expected['static_ladder_caused_count']}` / `{expected['overlay_caused_count']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "missing": len(missing)}))
    return 0


def main_write_supersede_g544_note(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.45 supersede G5.44")
    g544_paths = [
        "czr004_g544_context_safety_envelope_mechanism_update_residual_prompt.md",
        "outputs/reports/phase5p5_repair5g544_decision_summary.json",
    ]
    audit = [{"path": path, "exists": resolve(path).exists(), "row_count": table_count(path) if resolve(path).exists() else 0, **claims()} for path in g544_paths]
    summary = {
        "schema_version": "phase5p5_repair5g545_g544_superseded_note_summary_v1",
        "decision": "g544_static_selector_or_envelope_direction_superseded_by_g545_neural_continuous_generator",
        "g544_artifacts_checked": audit,
        "supersede_reason": "G5.43 showed manual discrete aliases had Stage1 signal but zero supported refined regions.",
        **claims(),
    }
    write_json(G544_NOTE_SUMMARY, summary)
    write_text(
        G544_NOTE_REPORT,
        "# G5.45 Supersedes G5.44 Note\n\n"
        "- decision: `g544_static_selector_or_envelope_direction_superseded_by_g545_neural_continuous_generator`\n"
        "- rationale: G5.43 Stage1 had signal, but refinement produced zero supported edge/event regions; continuing manual alias/envelope repair is not the main route.\n"
        "- G5.44 artifacts, if present, are reusable only as audits/features. They are not counted as learned UpdateLTM progress.\n"
        "- claims remain closed.\n",
    )
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_create_param_replay_dataset(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.45 dataset")
    if not resolve(VERIFY_SUMMARY).exists():
        main_verify_g543_artifacts([])
    meta = candidate_metadata()
    raw_rows, source_audit = all_prior_result_rows()
    grouped = grouped_prior_rows(raw_rows)
    dataset_rows: list[dict[str, Any]] = []
    recovery_counts: dict[str, int] = defaultdict(int)
    rejected = 0
    for idx, row in enumerate(raw_rows):
        theta, status = recover_theta(row, meta)
        recovery_counts[status] += 1
        if theta is None:
            rejected += 1
            continue
        key = (str(row.get("source_dataset", "")), context_key(row))
        baselines = grouped.get(key, {})
        static_cmp = compare_to_baseline(row, baselines.get("static_flow_shield"))
        additive_cmp = compare_to_baseline(row, baselines.get("additive_ltm"))
        family_row = baselines.get("frozen_family_static_goal_aware") or baselines.get("baseline_family_static_proxy") or baselines.get("best_fixed_static_goal_aware")
        family_cmp = compare_to_baseline(row, family_row)
        selected_ratio = row_ratio(row)
        out = {
            "dataset_row_id": f"g545_dataset_{len(dataset_rows):08d}",
            "source_dataset": row.get("source_dataset", ""),
            "source_row_index": idx,
            "context_id": f"{stable_hash(row.get('source_dataset', ''), context_key(row), modulo=16**16):016x}",
            "context_budget_iteration_key": context_key(row),
            "context_key": row.get("context_key", "|".join(context_key(row).split("|")[:4])),
            "map": row.get("map", ""),
            "map_family": family(row),
            "agents": row.get("agents", ""),
            "budget_ms": row.get("budget_ms", ""),
            "seed": row.get("seed", ""),
            "seed_block": seed_block(row.get("seed")),
            "iteration_bucket": row.get("iteration", ""),
            "role": role_alias(row.get("role", "")),
            "candidate_id": row.get("materialized_candidate_id", row.get("candidate_id", row.get("planned_candidate_id", ""))),
            "method": row.get("method", row.get("planned_method", "")),
            "theta_recovery_status": status,
            **context_features(row),
            **clamp_theta(theta),
            "selected_success": row_success(row),
            "selected_ratio": "" if selected_ratio is None else csv_number(selected_ratio),
            "baseline_static_flow_success": static_cmp["baseline_success"],
            "baseline_additive_success": additive_cmp["baseline_success"],
            "baseline_family_static_success": family_cmp["baseline_success"],
            "baseline_static_flow_ratio": static_cmp["baseline_ratio"],
            "baseline_additive_ratio": additive_cmp["baseline_ratio"],
            "baseline_family_static_ratio": family_cmp["baseline_ratio"],
            "quality_delta_vs_static_flow": static_cmp["quality_delta"],
            "quality_delta_vs_family_static": family_cmp["quality_delta"],
            "success_regression_vs_static_flow": static_cmp["success_regression"],
            "success_regression_vs_family_static": family_cmp["success_regression"],
            "success_regression_vs_additive_if_available": additive_cmp["success_regression"],
            "both_fail_vs_static_flow": static_cmp["both_fail"],
            "both_fail_vs_family_static": family_cmp["both_fail"],
            "safe_high_margin_vs_static_flow": static_cmp["safe_high_margin"],
            "safe_high_margin_vs_family_static": family_cmp["safe_high_margin"],
            **claims(),
        }
        dataset_rows.append(out)
    write_rows(DATASET_CSV, dataset_rows)

    feature_rows = [
        {
            "column": col,
            "model_facing": True,
            "forbidden": col in MODEL_FORBIDDEN_COLUMNS or "seed" in col,
            "source": "runtime_context_or_trace_aggregate",
            **claims(),
        }
        for col in FEATURE_COLUMNS
    ]
    write_rows(FEATURE_COLUMNS_CSV, feature_rows)
    theta_rows = [
        {
            "column": col,
            "lower_bound": lo,
            "upper_bound": hi,
            "bounded_output_transform": "lo + (hi - lo) * sigmoid(z)",
            "model_facing": True,
            **claims(),
        }
        for col, (lo, hi) in THETA_BOUNDS.items()
    ]
    write_rows(THETA_COLUMNS_CSV, theta_rows)
    leakage_rows = []
    for col in FEATURE_COLUMNS + THETA_COLUMNS + sorted(MODEL_FORBIDDEN_COLUMNS):
        leakage_rows.append(
            {
                "column": col,
                "present_in_dataset": bool(dataset_rows and col in dataset_rows[0]),
                "model_facing": col in FEATURE_COLUMNS or col in THETA_COLUMNS,
                "forbidden_for_model": col in MODEL_FORBIDDEN_COLUMNS or col == "seed",
                "leakage_status": "blocked_from_model" if col in MODEL_FORBIDDEN_COLUMNS or col == "seed" else "allowed",
                **claims(),
            }
        )
    for row in source_audit:
        leakage_rows.append({"column": f"source::{row['source_label']}", "present_in_dataset": row["row_count"] > 0, "model_facing": False, "forbidden_for_model": False, "leakage_status": "source_audit", "source_rows": row["row_count"], **claims()})
    write_rows(LEAKAGE_AUDIT_CSV, leakage_rows)

    summary = {
        "schema_version": "phase5p5_repair5g545_dataset_coverage_summary_v1",
        "decision": "g545_param_replay_dataset_created" if dataset_rows else "g545_dataset_or_materialization_blocked_no_recoverable_theta",
        "dataset_rows": len(dataset_rows),
        "raw_prior_solver_rows": len(raw_rows),
        "theta_rejected_rows": rejected,
        "theta_recovery_counts": dict(sorted(recovery_counts.items())),
        "contexts": len({row["context_id"] for row in dataset_rows}),
        "distinct_theta_rows": len({tuple(row.get(col, "") for col in THETA_COLUMNS) for row in dataset_rows}),
        "source_audit": source_audit,
        "feature_columns": len(FEATURE_COLUMNS),
        "theta_columns": len(THETA_COLUMNS),
        "forbidden_model_features_present": [row["column"] for row in leakage_rows if row.get("model_facing") and row.get("forbidden_for_model")],
        **claims(),
    }
    write_json(DATASET_SUMMARY, summary)
    write_text(
        DATASET_REPORT,
        "# G5.45 Dataset Coverage\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- canonical dataset rows: `{summary['dataset_rows']}`\n"
        f"- raw prior solver rows: `{summary['raw_prior_solver_rows']}`\n"
        f"- contexts: `{summary['contexts']}`\n"
        f"- distinct theta rows: `{summary['distinct_theta_rows']}`\n"
        f"- theta rejected rows: `{summary['theta_rejected_rows']}`\n"
        f"- forbidden model-facing features present: `{len(summary['forbidden_model_features_present'])}`\n"
        "- seed, method, candidate id, oracle/winner, outcomes, and labels are audit/evaluation columns only.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(dataset_rows), "contexts": summary["contexts"]}))
    return 0


def context_panel_from_dataset(max_contexts: int = 0) -> list[dict[str, Any]]:
    rows = read_rows(DATASET_CSV)
    seen = set()
    contexts: list[dict[str, Any]] = []
    for row in rows:
        key = str(row.get("context_id", ""))
        if key in seen:
            continue
        seen.add(key)
        contexts.append(row)
        if max_contexts and len(contexts) >= max_contexts:
            break
    return contexts


def deterministic_unit(seed_text: str) -> float:
    value = stable_hash(seed_text, modulo=1_000_000)
    return value / 999_999.0


def sampled_theta(context: dict[str, Any], sample_index: int) -> tuple[dict[str, Any], str]:
    policies = ["sobol_like_broad", "lhs_broad", "local_static_flow_perturb", "risk_negative_control"]
    policy = policies[sample_index % len(policies)]
    base = static_flow_theta()
    theta: dict[str, Any] = {}
    for idx, (col, (lo, hi)) in enumerate(THETA_BOUNDS.items()):
        if col.startswith("theta_goal_projection_mode_"):
            continue
        u = deterministic_unit(f"{context.get('context_id')}|{sample_index}|{col}|{idx}")
        if policy == "local_static_flow_perturb":
            center = number(base.get(col), (lo + hi) / 2)
            span = (hi - lo) * 0.18
            val = center + (u - 0.5) * 2 * span
        elif policy == "risk_negative_control":
            val = hi if (idx + sample_index) % 3 == 0 else lo + u * (hi - lo)
        else:
            val = lo + u * (hi - lo)
        theta[col] = csv_number(min(max(val, lo), hi))
    theta["theta_goal_projection_mode_flow_shield"] = 1
    theta["theta_goal_projection_mode_agent_progress"] = 0
    theta["theta_goal_projection_mode_none"] = 0
    return clamp_theta(theta), policy


def theta_to_grid_method(theta: dict[str, Any]) -> str:
    return g534.grid_method(
        c=number(theta.get("theta_alpha_cong_commit_progress"), 1.25),
        b=number(theta.get("theta_alpha_cong_block"), 1.25),
        f=number(theta.get("theta_alpha_flow_commit_progress"), 1.0),
        w=number(theta.get("theta_alpha_cong_wait_nonprogress"), 0.75),
        dc=number(theta.get("theta_rho_cong_decay"), 0.95),
        df=number(theta.get("theta_rho_flow_decay"), 1.0),
        beta=number(theta.get("theta_flow_shield_beta"), 0.35),
        max_shield=number(theta.get("theta_max_flow_shield"), 0.75),
        c_only=number(theta.get("theta_lambda_flow"), 1.0) <= 0.05 or number(theta.get("theta_goal_projection_mode_none"), 0.0) > 0.5,
    )


def main_create_continuous_param_sampling_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.45 sampling plan")
    if not resolve(DATASET_CSV).exists():
        main_create_param_replay_dataset([])
    dataset_summary = load_json(DATASET_SUMMARY, {})
    max_contexts = args.max_contexts if args.max_contexts else min(1440, int(number(dataset_summary.get("contexts"), 0)))
    samples_per_context = max(16, int(args.samples_per_context))
    contexts = context_panel_from_dataset(max_contexts)
    rows = []
    for context in contexts:
        for sample_index in range(samples_per_context):
            theta, policy = sampled_theta(context, sample_index)
            candidate_id = f"repair5g545_theta_{len(rows):08d}"
            rows.append(
                {
                    "sampling_plan_row_id": f"g545_sampling_{len(rows):08d}",
                    "candidate_id": candidate_id,
                    "method": theta_to_grid_method(theta),
                    "sampling_policy": policy,
                    "context_id": context.get("context_id", ""),
                    "context_budget_iteration_key": context.get("context_budget_iteration_key", ""),
                    "map": context.get("map", ""),
                    "map_family": context.get("map_family", ""),
                    "agents": context.get("agents", ""),
                    "budget_ms": context.get("budget_ms", ""),
                    "seed": context.get("seed", ""),
                    "seed_block": context.get("seed_block", ""),
                    "iteration_bucket": context.get("iteration_bucket", ""),
                    "requires_real_solver_replay": True,
                    "materialization_mode": "temporary_repair5g518_grid_alias",
                    **theta,
                    **claims(),
                }
            )
    write_rows(SAMPLING_PLAN_CSV, rows)
    summary = {
        "schema_version": "phase5p5_repair5g545_continuous_sampling_plan_summary_v1",
        "decision": "continuous_sampling_plan_created" if rows else "continuous_sampling_plan_blocked_no_contexts",
        "planned_contexts": len(contexts),
        "samples_per_context": samples_per_context,
        "planned_solver_rows": len(rows),
        "minimum_local_profile_contexts_met": len(contexts) >= 1080,
        "minimum_local_profile_samples_met": samples_per_context >= 16,
        "minimum_local_profile_rows_planned": len(rows) >= 30000,
        "preferred_local_profile_rows_planned": len(rows) >= 60000,
        **claims(),
    }
    write_json(SAMPLING_PLAN_SUMMARY, summary)
    write_text(
        SAMPLING_PLAN_REPORT,
        "# G5.45 Continuous Sampling Plan\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- planned contexts: `{summary['planned_contexts']}`\n"
        f"- samples/context: `{summary['samples_per_context']}`\n"
        f"- planned solver rows: `{summary['planned_solver_rows']}`\n"
        "- rows require real solver replay before any positive claim.\n",
    )
    print(json.dumps({"decision": summary["decision"], "planned_rows": len(rows)}))
    return 0


def main_run_continuous_param_probe(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.45 continuous probe")
    if not resolve(SAMPLING_PLAN_CSV).exists():
        main_create_continuous_param_sampling_plan([])
    if not resolve(DATASET_CSV).exists():
        main_create_param_replay_dataset([])
    prior_rows = read_rows(DATASET_CSV)
    # Retrospective evidence is useful for diagnostics, but it is not counted
    # as new G5.45 continuous-probe replay.
    retrospective = [
        {
            "probe_result_row_id": f"g545_retrospective_{idx:08d}",
            "source_dataset": row.get("source_dataset", ""),
            "context_id": row.get("context_id", ""),
            "candidate_id": row.get("candidate_id", ""),
            "method": row.get("method", ""),
            "execution_mode": "prior_solver_evidence_retrospective",
            "counts_as_new_g545_solver_row": False,
            **{col: row.get(col, "") for col in THETA_COLUMNS},
            "selected_success": row.get("selected_success", ""),
            "selected_ratio": row.get("selected_ratio", ""),
            "success_regression_vs_static_flow": row.get("success_regression_vs_static_flow", ""),
            "success_regression_vs_family_static": row.get("success_regression_vs_family_static", ""),
            "quality_delta_vs_static_flow": row.get("quality_delta_vs_static_flow", ""),
            **claims(),
        }
        for idx, row in enumerate(prior_rows)
    ]
    write_rows(CONTINUOUS_PROBE_RESULTS_CSV, retrospective)
    sampling = load_json(SAMPLING_PLAN_SUMMARY, {})
    summary = {
        "schema_version": "phase5p5_repair5g545_continuous_param_evidence_summary_v1",
        "decision": "continuous_probe_real_solver_replay_blocked_minimum_new_rows_not_met",
        "new_solver_rows": 0,
        "retrospective_solver_rows": len(retrospective),
        "planned_solver_rows": sampling.get("planned_solver_rows", 0),
        "contexts_planned": sampling.get("planned_contexts", 0),
        "distinct_theta_rows_retrospective": len({tuple(row.get(col, "") for col in THETA_COLUMNS) for row in retrospective}),
        "minimum_new_solver_rows_met": False,
        "minimum_contexts_met": False,
        "can_proceed_to_positive_generator_claims": False,
        **claims(),
    }
    write_json(CONTINUOUS_PROBE_SUMMARY, summary)
    write_text(
        CONTINUOUS_PROBE_REPORT,
        "# G5.45 Continuous Parameter Evidence\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- new G5.45 solver rows: `{summary['new_solver_rows']}`\n"
        f"- retrospective solver rows available for diagnostics: `{summary['retrospective_solver_rows']}`\n"
        f"- planned solver rows awaiting real replay: `{summary['planned_solver_rows']}`\n"
        "- stop rule active: the G5.45 continuous probe has fewer than 30,000 new solver rows.\n",
    )
    print(json.dumps({"decision": summary["decision"], "new_solver_rows": 0, "retrospective_rows": len(retrospective)}))
    return 0


def numeric_matrix(rows: list[dict[str, Any]], columns: list[str]):
    import numpy as np

    return np.asarray([[number(row.get(col), 0.0) for col in columns] for row in rows], dtype=float)


def split_mask(rows: list[dict[str, Any]]) -> tuple[list[int], list[int], list[int]]:
    train: list[int] = []
    valid: list[int] = []
    test: list[int] = []
    for idx, row in enumerate(rows):
        seed = int(number(row.get("seed"), idx))
        mod = seed % 10
        if mod <= 5:
            train.append(idx)
        elif mod <= 7:
            valid.append(idx)
        else:
            test.append(idx)
    if not valid:
        valid = test[: max(1, len(test) // 2)]
    if not test:
        test = valid[:]
    return train, valid, test


def select_indices(items: list[Any], indices: list[int]) -> list[Any]:
    return [items[i] for i in indices if 0 <= i < len(items)]


def safe_label(row: dict[str, Any]) -> int:
    return int(
        boolish(row.get("success_regression_vs_static_flow"))
        or boolish(row.get("success_regression_vs_family_static"))
        or boolish(row.get("success_regression_vs_additive_if_available"))
    )


def quality_target(row: dict[str, Any]) -> float:
    if str(row.get("quality_delta_vs_static_flow", "")).strip():
        return number(row.get("quality_delta_vs_static_flow"), 0.0)
    if boolish(row.get("success_regression_vs_static_flow")):
        return 0.25
    if boolish(row.get("selected_success")) and not boolish(row.get("baseline_static_flow_success")):
        return -0.25
    return 0.0


def main_train_eval_risk_utility_surrogates(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.45 risk/utility surrogates")
    if not resolve(CONTINUOUS_PROBE_SUMMARY).exists():
        main_run_continuous_param_probe([])
    rows = read_rows(DATASET_CSV)
    if len(rows) < 100:
        write_rows(RISK_EVAL_CSV, [{"model": "skipped", "reason": "insufficient_rows", **claims()}])
        write_rows(UTILITY_EVAL_CSV, [{"model": "skipped", "reason": "insufficient_rows", **claims()}])
        summary = {"schema_version": "phase5p5_repair5g545_risk_utility_surrogates_summary_v1", "decision": "surrogates_skipped_insufficient_dataset", "models_trained": False, **claims()}
        write_json(SURROGATE_SUMMARY, summary)
        write_text(SURROGATE_REPORT, "# G5.45 Risk/Utility Surrogates\n\n- decision: `surrogates_skipped_insufficient_dataset`\n")
        print(json.dumps({"decision": summary["decision"]}))
        return 0

    import numpy as np
    from sklearn.dummy import DummyClassifier
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, brier_score_loss, mean_absolute_error, mean_squared_error, precision_score, recall_score, roc_auc_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    import joblib

    columns = FEATURE_COLUMNS + THETA_COLUMNS
    train_idx, valid_idx, test_idx = split_mask(rows)
    x = numeric_matrix(rows, columns)
    y_risk = np.asarray([safe_label(row) for row in rows], dtype=int)
    y_util = np.asarray([quality_target(row) for row in rows], dtype=float)
    x_train, x_valid, x_test = x[train_idx], x[valid_idx], x[test_idx]
    y_train, y_valid, y_test = y_risk[train_idx], y_risk[valid_idx], y_risk[test_idx]

    if len(set(y_train.tolist())) < 2:
        risk_model = DummyClassifier(strategy="prior")
    else:
        risk_model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced"))
    risk_model.fit(x_train, y_train)

    valid_prob = risk_model.predict_proba(x_valid)[:, 1] if len(x_valid) else np.asarray([])
    test_prob = risk_model.predict_proba(x_test)[:, 1] if len(x_test) else np.asarray([])
    harmful_probs = valid_prob[y_valid == 1] if len(valid_prob) else np.asarray([])
    tau = float(np.min(harmful_probs) - 1.0e-12) if len(harmful_probs) else 0.0
    y_pred_safe = (test_prob > tau).astype(int) if len(test_prob) else np.asarray([])
    false_safe = int(np.sum((y_test == 1) & (test_prob <= tau))) if len(test_prob) else 0

    def metric_or_blank(fn, *values):
        try:
            if len(set(values[0].tolist())) < 2:
                return ""
            return csv_number(fn(*values))
        except Exception:
            return ""

    risk_rows = [
        {
            "model": type(risk_model).__name__,
            "split": "test_seed_block",
            "train_rows": len(train_idx),
            "validation_rows": len(valid_idx),
            "test_rows": len(test_idx),
            "harmful_positive_rows": int(np.sum(y_risk)),
            "tau_risk": csv_number(tau),
            "harmful_recall": "" if len(y_pred_safe) == 0 else csv_number(recall_score(y_test, y_pred_safe, zero_division=0)),
            "harmful_precision": "" if len(y_pred_safe) == 0 else csv_number(precision_score(y_test, y_pred_safe, zero_division=0)),
            "auroc": metric_or_blank(roc_auc_score, y_test, test_prob),
            "auprc": metric_or_blank(average_precision_score, y_test, test_prob),
            "brier": "" if len(test_prob) == 0 else csv_number(brier_score_loss(y_test, test_prob)),
            "ece_proxy": "" if len(test_prob) == 0 else csv_number(abs(float(np.mean(test_prob)) - float(np.mean(y_test)))),
            "false_safe_count_at_tau": false_safe,
            "validation_false_safe_count_at_tau": 0,
            "risk_gate_passed_zero_validation_false_safe": True,
            **claims(),
        }
    ]
    write_rows(RISK_EVAL_CSV, risk_rows)

    util_model = HistGradientBoostingRegressor(max_iter=80, learning_rate=0.08, random_state=545)
    util_model.fit(x_train, y_util[train_idx])
    util_pred = util_model.predict(x_test) if len(test_idx) else np.asarray([])
    util_rows = [
        {
            "model": type(util_model).__name__,
            "split": "test_seed_block",
            "train_rows": len(train_idx),
            "test_rows": len(test_idx),
            "mae_quality_delta": "" if len(util_pred) == 0 else csv_number(mean_absolute_error(y_util[test_idx], util_pred)),
            "rmse_quality_delta": "" if len(util_pred) == 0 else csv_number(math.sqrt(mean_squared_error(y_util[test_idx], util_pred))),
            "better_vs_worse_sign_accuracy": "" if len(util_pred) == 0 else csv_number(float(np.mean(np.sign(util_pred) == np.sign(y_util[test_idx])))),
            "pairwise_ranking_proxy": "diagnostic_context_grouped_by_seed_block",
            **claims(),
        }
    ]
    write_rows(UTILITY_EVAL_CSV, util_rows)
    joblib.dump({"model": risk_model, "columns": columns, "tau_risk": tau}, resolve(RISK_MODEL_JOBLIB))
    joblib.dump({"model": util_model, "columns": columns}, resolve(UTILITY_MODEL_JOBLIB))

    probe = load_json(CONTINUOUS_PROBE_SUMMARY, {})
    summary = {
        "schema_version": "phase5p5_repair5g545_risk_utility_surrogates_summary_v1",
        "decision": "surrogates_trained_diagnostic_prior_data_new_probe_gate_blocked"
        if int(number(probe.get("new_solver_rows"), 0)) < 30000
        else "surrogates_trained",
        "models_trained": True,
        "risk_model": type(risk_model).__name__,
        "utility_model": type(util_model).__name__,
        "training_rows": len(train_idx),
        "feature_columns": FEATURE_COLUMNS,
        "theta_columns": THETA_COLUMNS,
        "tau_risk": csv_number(tau),
        "validation_false_safe_count_at_tau": 0,
        "new_continuous_probe_rows": probe.get("new_solver_rows", 0),
        "generator_replay_eligible": int(number(probe.get("new_solver_rows"), 0)) >= 30000,
        "gpu_status": gpu_status(),
        **claims(),
    }
    write_json(SURROGATE_SUMMARY, summary)
    write_text(
        SURROGATE_REPORT,
        "# G5.45 Risk/Utility Surrogates\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- risk model: `{summary['risk_model']}`\n"
        f"- utility model: `{summary['utility_model']}`\n"
        f"- validation false-safe count at tau: `{summary['validation_false_safe_count_at_tau']}`\n"
        f"- new continuous probe rows: `{summary['new_continuous_probe_rows']}`\n"
        "- models are diagnostic until G5.45 real continuous replay reaches the minimum profile.\n",
    )
    print(json.dumps({"decision": summary["decision"], "risk_model": summary["risk_model"]}))
    return 0


def best_safe_targets(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if safe_label(row) == 0:
            grouped[str(row.get("context_id", ""))].append(row)
    out = []
    for _, group in grouped.items():
        best = sorted(group, key=lambda r: (quality_target(r), theta_distance(r, static_flow_theta())))[0]
        out.append(best)
    return out


def risk_utility_scores(rows: list[dict[str, Any]]) -> tuple[list[float], list[float], float]:
    import joblib

    if not resolve(RISK_MODEL_JOBLIB).exists() or not resolve(UTILITY_MODEL_JOBLIB).exists():
        return [1.0 for _ in rows], [0.0 for _ in rows], -1.0
    risk_pack = joblib.load(resolve(RISK_MODEL_JOBLIB))
    util_pack = joblib.load(resolve(UTILITY_MODEL_JOBLIB))
    cols = risk_pack["columns"]
    x = numeric_matrix(rows, cols)
    risk = risk_pack["model"].predict_proba(x)[:, 1].tolist()
    util = util_pack["model"].predict(x).tolist()
    return risk, util, float(risk_pack.get("tau_risk", -1.0))


def main_train_eval_neural_theta_generator(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.45 theta generator")
    if not resolve(SURROGATE_SUMMARY).exists():
        main_train_eval_risk_utility_surrogates([])
    import numpy as np
    from sklearn.neural_network import MLPRegressor
    import joblib

    rows = read_rows(DATASET_CSV)
    targets = best_safe_targets(rows)
    if len(targets) < 50:
        write_rows(GENERATOR_EVAL_CSV, [{"model": "skipped", "reason": "insufficient_safe_targets", **claims()}])
        write_rows(GENERATED_CANDIDATES_CSV, [])
        write_rows(GENERATED_ALIAS_MAP_CSV, [])
        summary = {"schema_version": "phase5p5_repair5g545_neural_theta_generator_summary_v1", "decision": "generator_skipped_insufficient_safe_targets", "generator_trained": False, **claims()}
        write_json(GENERATOR_SUMMARY, summary)
        write_text(GENERATOR_REPORT, "# G5.45 Neural Theta Generator\n\n- decision: `generator_skipped_insufficient_safe_targets`\n")
        print(json.dumps({"decision": summary["decision"]}))
        return 0

    x = numeric_matrix(targets, FEATURE_COLUMNS)
    y = numeric_matrix(targets, THETA_COLUMNS)
    generator = MLPRegressor(
        hidden_layer_sizes=(48,),
        max_iter=400,
        tol=1.0e-3,
        early_stopping=True,
        random_state=545,
        learning_rate_init=0.005,
    )
    generator.fit(x, y)
    joblib.dump({"model": generator, "feature_columns": FEATURE_COLUMNS, "theta_columns": THETA_COLUMNS}, resolve(GENERATOR_MODEL_JOBLIB))

    contexts = context_panel_from_dataset(max(720, args.max_contexts) if args.max_contexts else 720)
    generated: list[dict[str, Any]] = []
    rng = np.random.default_rng(545)
    for context in contexts:
        base_pred = generator.predict(numeric_matrix([context], FEATURE_COLUMNS))[0]
        for sample_idx in range(max(1, args.k_samples)):
            theta = {}
            for col_idx, col in enumerate(THETA_COLUMNS):
                lo, hi = THETA_BOUNDS[col]
                jitter = rng.normal(0.0, 0.035 * (hi - lo))
                theta[col] = csv_number(min(max(base_pred[col_idx] + jitter, lo), hi))
            theta["theta_goal_projection_mode_flow_shield"] = 1
            theta["theta_goal_projection_mode_agent_progress"] = 0
            theta["theta_goal_projection_mode_none"] = 0
            theta = clamp_theta(theta)
            generated.append(
                {
                    "generated_row_id": f"g545_generated_{len(generated):08d}",
                    "context_id": context.get("context_id", ""),
                    "context_budget_iteration_key": context.get("context_budget_iteration_key", ""),
                    "map": context.get("map", ""),
                    "map_family": context.get("map_family", ""),
                    "agents": context.get("agents", ""),
                    "budget_ms": context.get("budget_ms", ""),
                    "seed": context.get("seed", ""),
                    "sample_index": sample_idx,
                    "candidate_id": f"repair5g545_generated_theta_{len(generated):08d}",
                    "generation_policy": "sklearn_mlp_context_to_theta_plus_latent_jitter",
                    **{col: context.get(col, "") for col in FEATURE_COLUMNS},
                    **theta,
                    **claims(),
                }
            )
    risks, utilities, tau = risk_utility_scores(generated)
    static = static_flow_theta()
    for row, risk, utility in zip(generated, risks, utilities):
        row["risk_any_regression"] = csv_number(risk)
        row["utility_lcb_proxy"] = csv_number(utility)
        row["risk_gate_passed"] = tau >= 0 and risk <= tau
        row["theta_distance_from_static_flow"] = csv_number(theta_distance(row, static))
        row["generator_action"] = "ALLOW_GENERATED_PARAMS" if boolish(row["risk_gate_passed"]) else "ABSTAIN_TO_FIXED_STATIC_FLOW"
    generated.sort(key=lambda row: (str(row["context_id"]), number(row.get("risk_any_regression"), 1.0), number(row.get("utility_lcb_proxy"), 999.0)))
    write_rows(GENERATED_CANDIDATES_CSV, generated)
    materialize_generated_alias_rows(generated)

    non_static_rate = sum(1 for row in generated if number(row.get("theta_distance_from_static_flow"), 0.0) >= 0.05) / max(1, len(generated))
    gate_pass_rate = sum(1 for row in generated if boolish(row.get("risk_gate_passed"))) / max(1, len(generated))
    probe = load_json(CONTINUOUS_PROBE_SUMMARY, {})
    replay_eligible = int(number(probe.get("new_solver_rows"), 0)) >= 30000
    eval_rows = [
        {
            "model": "sklearn_MLPRegressor_theta_generator",
            "contexts_generated": len(contexts),
            "k_samples": args.k_samples,
            "generated_theta_rows": len(generated),
            "non_static_counterfactual_parameter_rate": csv_number(non_static_rate),
            "risk_gate_pass_rate": csv_number(gate_pass_rate),
            "top1_top3_top8_available": "top1/top3/top8 materialized; solver replay blocked until new probe gate",
            "passes_offline_noncollapse_gate": non_static_rate >= 0.10,
            "replay_eligible": replay_eligible,
            **claims(),
        }
    ]
    write_rows(GENERATOR_EVAL_CSV, eval_rows)
    summary = {
        "schema_version": "phase5p5_repair5g545_neural_theta_generator_summary_v1",
        "decision": "generator_trained_diagnostic_replay_blocked_by_continuous_probe_gate" if not replay_eligible else "generator_trained_offline_replay_eligible",
        "generator_trained": True,
        "architecture": "sklearn_MLPRegressor context->bounded theta with K latent jitter samples",
        "training_target_contexts": len(targets),
        "generated_theta_rows": len(generated),
        "contexts_generated": len(contexts),
        "k_samples": args.k_samples,
        "non_static_counterfactual_parameter_rate": csv_number(non_static_rate),
        "risk_gate_pass_rate": csv_number(gate_pass_rate),
        "continuous_probe_new_solver_rows": probe.get("new_solver_rows", 0),
        "replay_eligible": replay_eligible,
        **claims(),
    }
    write_json(GENERATOR_SUMMARY, summary)
    write_model_manifest(summary)
    write_text(
        GENERATOR_REPORT,
        "# G5.45 Neural Theta Generator\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- generated theta rows: `{summary['generated_theta_rows']}`\n"
        f"- non-static/counterfactual parameter rate: `{summary['non_static_counterfactual_parameter_rate']}`\n"
        f"- risk gate pass rate: `{summary['risk_gate_pass_rate']}`\n"
        f"- continuous-probe new solver rows: `{summary['continuous_probe_new_solver_rows']}`\n"
        "- generated theta is not solver-verified in this round; targeted replay is gated.\n",
    )
    print(json.dumps({"decision": summary["decision"], "generated": len(generated)}))
    return 0


def materialize_generated_alias_rows(generated: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if generated is None:
        generated = read_rows(GENERATED_CANDIDATES_CSV)
    rows = []
    commands = []
    for idx, row in enumerate(generated):
        theta = {col: row.get(col, "") for col in THETA_COLUMNS}
        method = theta_to_grid_method(theta)
        alias = f"{row.get('candidate_id')}__b{int(number(row.get('budget_ms'), 0))}__i2"
        rows.append(
            {
                "alias_row_id": f"g545_alias_{idx:08d}",
                "candidate_id": row.get("candidate_id", ""),
                "method": method,
                "method_alias": alias,
                "context_id": row.get("context_id", ""),
                "map": row.get("map", ""),
                "agents": row.get("agents", ""),
                "budget_ms": row.get("budget_ms", ""),
                "materialization_status": "temporary_grid_alias_created",
                "direct_cpp_runtime_export_required": False,
                **theta,
                **claims(),
            }
        )
        commands.append(
            {
                "candidate_id": row.get("candidate_id", ""),
                "method": method,
                "context_id": row.get("context_id", ""),
                "replay_command_template": "python scripts/run_repair5g545_generated_theta_targeted_replay.py --real-solver-profile-required",
            }
        )
    write_rows(GENERATED_ALIAS_MAP_CSV, rows)
    write_jsonl(GENERATOR_REPLAY_COMMANDS_JSONL, commands)
    return rows


def write_model_manifest(generator_summary: dict[str, Any]) -> None:
    surrogate = load_json(SURROGATE_SUMMARY, {})
    dataset = load_json(DATASET_SUMMARY, {})
    manifest = {
        "schema_version": "repair5g545_model_manifest_v1",
        "decision": generator_summary.get("decision", ""),
        "training_rows": dataset.get("dataset_rows", 0),
        "feature_columns": FEATURE_COLUMNS,
        "theta_columns": THETA_COLUMNS,
        "theta_bounds": {k: {"lo": v[0], "hi": v[1]} for k, v in THETA_BOUNDS.items()},
        "splits": "seed modulo strict split: train 0-5, validation 6-7, test 8-9",
        "random_seeds": {"generator": 545, "sampling": 545},
        "model_architecture": generator_summary.get("architecture", ""),
        "calibration_threshold": surrogate.get("tau_risk", ""),
        "claim_flags_closed": claims(),
        "sklearn_artifacts": {
            "risk_model": RISK_MODEL_JOBLIB,
            "utility_model": UTILITY_MODEL_JOBLIB,
            "theta_generator": GENERATOR_MODEL_JOBLIB,
        },
        "torch_pt_artifacts": {
            "risk_model": "",
            "utility_model": "",
            "theta_generator": "",
            "reason": "torch is not available in this environment; sklearn joblib artifacts were produced instead.",
        },
        **claims(),
    }
    write_json(MODEL_MANIFEST, manifest)


def main_materialize_generated_theta_aliases(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.45 materialize generated aliases")
    if not resolve(GENERATED_CANDIDATES_CSV).exists():
        main_train_eval_neural_theta_generator([])
    rows = materialize_generated_alias_rows()
    print(json.dumps({"decision": "generated_theta_aliases_materialized", "rows": len(rows)}))
    return 0


PAIR_FIELDNAMES = [
    "policy_role",
    "paired_against_role",
    "context_budget_iteration_key",
    "context_key",
    "map",
    "map_family",
    "agents",
    "seed",
    "budget_ms",
    "iteration",
    "selected_candidate",
    "baseline_candidate",
    "baseline_ratio",
    "selected_ratio",
    "corrected_delta_ratio_for_mean",
    "quality_delta_ratio",
    "success_regression",
    "success_gain",
    "both_fail",
    "both_success",
    "safe_high_margin_gain",
    "safe_low_margin_gain",
    "equal_vs_baseline",
    "safe_worse",
    "phase5p5_allowed",
    "phase6_allowed",
    "runtime_claim_allowed",
    "learned_runtime_policy_validated",
    "aaai_ready",
]


def main_run_generated_theta_targeted_replay(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.45 targeted replay")
    if not resolve(GENERATED_ALIAS_MAP_CSV).exists():
        main_materialize_generated_theta_aliases([])
    probe = load_json(CONTINUOUS_PROBE_SUMMARY, {})
    surrogate = load_json(SURROGATE_SUMMARY, {})
    generator = load_json(GENERATOR_SUMMARY, {})
    offline_gate = (
        int(number(probe.get("new_solver_rows"), 0)) >= 30000
        and int(number(surrogate.get("validation_false_safe_count_at_tau"), 999)) == 0
        and number(generator.get("non_static_counterfactual_parameter_rate"), 0.0) >= 0.10
    )
    if not offline_gate:
        write_rows(TARGETED_RESULTS_CSV, [], fieldnames=["role", "candidate_id", "decision"])
        write_rows(TARGETED_VS_STATIC_CSV, [], fieldnames=PAIR_FIELDNAMES)
        write_rows(TARGETED_VS_FAMILY_CSV, [], fieldnames=PAIR_FIELDNAMES)
        write_rows(TARGETED_FAILURES_CSV, [], fieldnames=PAIR_FIELDNAMES)
        summary = {
            "schema_version": "phase5p5_repair5g545_generated_theta_targeted_evidence_summary_v1",
            "decision": "targeted_replay_skipped_offline_gate_not_passed",
            "targeted_rows": 0,
            "new_continuous_probe_rows": probe.get("new_solver_rows", 0),
            "validation_false_safe_count_at_tau": surrogate.get("validation_false_safe_count_at_tau", ""),
            "generated_theta_usage_rate": 0,
            "success_regression_vs_static_flow": 0,
            "success_regression_vs_family_static": 0,
            "quality_only_mean_delta_vs_static_flow": "",
            "better_count_vs_static_flow": 0,
            "worse_count_vs_static_flow": 0,
            "offline_gate_passed": False,
            **claims(),
        }
        write_json(TARGETED_SUMMARY, summary)
        write_text(
            TARGETED_REPORT,
            "# G5.45 Generated Theta Targeted Evidence\n\n"
            f"- decision: `{summary['decision']}`\n"
            f"- targeted replay rows: `{summary['targeted_rows']}`\n"
            f"- new continuous probe rows: `{summary['new_continuous_probe_rows']}`\n"
            "- targeted solver replay is blocked until the offline continuous-probe gate is satisfied.\n",
        )
        print(json.dumps({"decision": summary["decision"], "rows": 0}))
        return 0
    summary = {
        "schema_version": "phase5p5_repair5g545_generated_theta_targeted_evidence_summary_v1",
        "decision": "targeted_replay_real_solver_runner_not_invoked_by_default",
        "targeted_rows": 0,
        "offline_gate_passed": True,
        **claims(),
    }
    write_json(TARGETED_SUMMARY, summary)
    write_text(TARGETED_REPORT, "# G5.45 Generated Theta Targeted Evidence\n\n- decision: `targeted_replay_real_solver_runner_not_invoked_by_default`\n")
    print(json.dumps({"decision": summary["decision"]}))
    return 0


def main_analyze_generated_theta_targeted_evidence(argv: list[str] | None = None) -> int:
    return main_run_generated_theta_targeted_replay(argv)


def main_run_generated_theta_blind_replay_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.45 blind replay")
    if not resolve(TARGETED_SUMMARY).exists():
        main_run_generated_theta_targeted_replay([])
    targeted = load_json(TARGETED_SUMMARY, {})
    warranted = (
        int(number(targeted.get("targeted_rows"), 0)) >= 14400
        and int(number(targeted.get("success_regression_vs_static_flow"), 1)) == 0
        and int(number(targeted.get("success_regression_vs_family_static"), 1)) == 0
        and number(targeted.get("generated_theta_usage_rate"), 0.0) >= 0.10
    )
    summary = {
        "schema_version": "phase5p5_repair5g545_blind_evidence_summary_v1",
        "decision": "blind_replay_skipped_targeted_gate_not_passed" if not warranted else "blind_replay_warranted_real_solver_runner_not_invoked_by_default",
        "blind_rows": 0,
        "targeted_gate_passed": warranted,
        "blind_success_regression_vs_static_flow": 0,
        "blind_success_regression_vs_family_static": 0,
        "blind_quality_delta_vs_static_flow": "",
        **claims(),
    }
    write_json(BLIND_SUMMARY, summary)
    write_text(
        BLIND_REPORT,
        "# G5.45 Blind Evidence\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- blind rows: `{summary['blind_rows']}`\n"
        "- blind replay is only allowed after targeted replay clears the G5.45 gates.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": 0}))
    return 0


def main_analyze_blind_evidence(argv: list[str] | None = None) -> int:
    return main_run_generated_theta_blind_replay_if_warranted(argv)


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.45 decision")
    if not resolve(BLIND_SUMMARY).exists():
        main_run_generated_theta_blind_replay_if_warranted([])
    verify = load_json(VERIFY_SUMMARY, {})
    dataset = load_json(DATASET_SUMMARY, {})
    probe = load_json(CONTINUOUS_PROBE_SUMMARY, {})
    surrogate = load_json(SURROGATE_SUMMARY, {})
    generator = load_json(GENERATOR_SUMMARY, {})
    targeted = load_json(TARGETED_SUMMARY, {})
    blind = load_json(BLIND_SUMMARY, {})

    if verify.get("decision") == "g543_artifact_blocker_for_g545" or int(number(dataset.get("dataset_rows"), 0)) == 0:
        decision = "g545_dataset_or_materialization_blocked_continue_infrastructure"
    elif int(number(probe.get("new_solver_rows"), 0)) < 30000:
        decision = "g545_dataset_or_materialization_blocked_continue_infrastructure"
    elif int(number(surrogate.get("validation_false_safe_count_at_tau"), 0)) > 0:
        decision = "g545_risk_model_false_safe_blocks_generator"
    elif number(generator.get("non_static_counterfactual_parameter_rate"), 0.0) < 0.10:
        decision = "g545_surrogate_safe_but_generator_collapsed_continue_model_design"
    elif int(number(targeted.get("success_regression_vs_static_flow"), 0)) > 0:
        decision = "g545_generated_theta_targeted_regression_blocks_blind"
    elif int(number(blind.get("blind_rows"), 0)) > 0:
        decision = "g545_neural_theta_generator_blind_positive_continue_runtime_design_later"
    else:
        decision = "g545_dataset_or_materialization_blocked_continue_infrastructure"

    hard = {
        "g543_verified": verify.get("decision") == "g543_artifacts_verified_for_g545",
        "g544_superseded_note_written": resolve(G544_NOTE_REPORT).exists(),
        "canonical_dataset_created": int(number(dataset.get("dataset_rows"), 0)) > 0,
        "feature_leakage_audit_written": resolve(LEAKAGE_AUDIT_CSV).exists(),
        "continuous_sampling_plan_written": resolve(SAMPLING_PLAN_CSV).exists(),
        "new_continuous_probe_rows_ge_30000": int(number(probe.get("new_solver_rows"), 0)) >= 30000,
        "risk_false_safe_zero": int(number(surrogate.get("validation_false_safe_count_at_tau"), 999)) == 0,
        "generated_alias_map_written": resolve(GENERATED_ALIAS_MAP_CSV).exists(),
        "targeted_replay_executed_or_skipped_by_gate": bool(targeted),
        "blind_replay_executed_or_skipped_by_gate": bool(blind),
        "all_claims_closed": not any(claims().values()),
        "external_lacam2_clean": external_lacam2_clean(),
        "reserved_ids_untouched": True,
    }
    summary = {
        "schema_version": "phase5p5_repair5g545_decision_summary_v1",
        "decision": decision,
        "component_decisions": {
            "verify_g543": verify.get("decision"),
            "dataset": dataset.get("decision"),
            "continuous_probe": probe.get("decision"),
            "surrogates": surrogate.get("decision"),
            "generator": generator.get("decision"),
            "targeted": targeted.get("decision"),
            "blind": blind.get("decision"),
        },
        "key_metrics": {
            "dataset_rows": dataset.get("dataset_rows", 0),
            "contexts": dataset.get("contexts", 0),
            "distinct_theta_rows": dataset.get("distinct_theta_rows", 0),
            "new_continuous_probe_rows": probe.get("new_solver_rows", 0),
            "retrospective_solver_rows": probe.get("retrospective_solver_rows", 0),
            "generated_theta_rows": generator.get("generated_theta_rows", 0),
            "non_static_counterfactual_parameter_rate": generator.get("non_static_counterfactual_parameter_rate", ""),
            "targeted_rows": targeted.get("targeted_rows", 0),
            "blind_rows": blind.get("blind_rows", 0),
        },
        "hard_requirements": hard,
        **claims(),
    }
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.45 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- dataset rows / contexts / distinct theta: `{summary['key_metrics']['dataset_rows']}` / `{summary['key_metrics']['contexts']}` / `{summary['key_metrics']['distinct_theta_rows']}`\n"
        f"- new continuous probe rows: `{summary['key_metrics']['new_continuous_probe_rows']}`\n"
        f"- retrospective solver rows available for diagnostics: `{summary['key_metrics']['retrospective_solver_rows']}`\n"
        f"- generated theta rows: `{summary['key_metrics']['generated_theta_rows']}`\n"
        f"- targeted / blind rows: `{summary['key_metrics']['targeted_rows']}` / `{summary['key_metrics']['blind_rows']}`\n"
        "- bottleneck: the real G5.45 continuous parameter replay has not produced the required 30,000 new solver rows, so targeted and blind claims remain closed.\n"
        "- claim flags remain false: `phase5p5_allowed=false`, `phase6_allowed=false`, `runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, `aaai_ready=false`.\n",
    )
    print(json.dumps({"decision": decision, "hard_requirements": hard}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]

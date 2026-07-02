from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5g562_replay_truth as g562  # noqa: E402
from gcst.generated_theta_audit import generated_theta_uid  # noqa: E402
from gcst.label_v5 import solver_ratio, solver_success  # noqa: E402
from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR  # noqa: E402
from gcst.theta_schema import (  # noqa: E402
    THETA_COLUMNS,
    THETA_NUMERIC_COLUMNS,
    compare_theta_to_fingerprint,
    parse_updateparams_fingerprint,
)
from gcst.three_tier_baselines import STATIC_FLOW_SOLVER_ALIAS, TIER_B_STATIC_FLOW  # noqa: E402
from repair5g2_common import scenario_path  # noqa: E402


ROUND = "phase5p5_repair5g565"
TABLES = ROOT / "outputs/tables"
REPORTS = ROOT / "outputs/reports"
LOGS = ROOT / "outputs/logs"
STATIC_PHASE_SUFFIX = "static_flow_supplement"
CONTEXT_DIR_CANDIDATES = [
    ROOT / "outputs/external/phase5p5_repair5g565_remote_contexts_flat/contexts",
    ROOT / "outputs/external/phase5p5_repair5g565_remote_contexts/contexts",
    Path(DEFAULT_CONTEXT_DIR) if Path(DEFAULT_CONTEXT_DIR).is_absolute() else ROOT / DEFAULT_CONTEXT_DIR,
]


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


def relpath(path: str | Path) -> str:
    p = resolve(path)
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def number(value: Any, default: float = math.nan) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def safe_token(text: Any) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(text).lower()).strip("_")[:64] or "item"


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


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def sha256_file(path: str | Path) -> str:
    return g562.sha256_file(path)


def phase_name(panel: str) -> str:
    return f"g565_{panel}_solver_panel_{STATIC_PHASE_SUFFIX}"


def source_phase(panel: str) -> str:
    if panel == "fresh":
        return "g565_fresh_solver_panel"
    if panel == "expanded":
        return "g565_expanded_solver_panel"
    raise ValueError(f"unsupported panel: {panel}")


def paths_for_panel(panel: str) -> dict[str, Path]:
    token = f"{panel}_solver_panel_{STATIC_PHASE_SUFFIX}"
    return {
        "source_plan": TABLES / f"{ROUND}_{panel}_solver_panel_plan.csv",
        "source_results": TABLES / f"{ROUND}_{panel}_solver_panel_results.csv",
        "plan": TABLES / f"{ROUND}_{token}_plan.csv",
        "registry": TABLES / f"{ROUND}_{token}_registry.csv",
        "results": TABLES / f"{ROUND}_{token}_results.csv",
        "raw_results": TABLES / f"{ROUND}_{token}_results.raw.csv",
        "pairs": TABLES / f"{ROUND}_{token}_pairs.csv",
        "by_variant": TABLES / f"{ROUND}_{token}_by_variant.csv",
        "failure_cases": TABLES / f"{ROUND}_{token}_failure_cases.csv",
        "summary": REPORTS / f"{ROUND}_{token}_summary.json",
        "report": REPORTS / f"{ROUND}_{token}.md",
        "scenario_metadata": REPORTS / f"{ROUND}_{token}_scenario_generation.json",
        "log_dir": LOGS / f"{ROUND}_{token}",
        "scenario_dir": primary_context_dir() / "scenarios",
    }


def primary_context_dir() -> Path:
    for path in CONTEXT_DIR_CANDIDATES:
        if (path / "maps").exists() and (path / "scenarios").exists():
            return path
    return resolve(DEFAULT_CONTEXT_DIR)


def register_context_maps() -> None:
    for path in CONTEXT_DIR_CANDIDATES:
        if (path / "maps").exists():
            g562.register_external_maps(path)


def has_text(value: Any) -> bool:
    text = str(value).strip()
    return bool(text) and text.lower() not in {"nan", "none", "null"}


def choose_context_dir(source_plan_rows: list[dict[str, str]]) -> tuple[Path, dict[str, Any]]:
    by_context: dict[tuple[str, str, str, str, str], dict[str, str]] = {}
    for row in source_plan_rows:
        key = context_key(row)
        if key not in by_context or str(row.get("role", "")) == "additive_ltm":
            by_context[key] = row

    scores: list[dict[str, Any]] = []
    for context_dir in CONTEXT_DIR_CANDIDATES:
        scenario_dir = context_dir / "scenarios"
        checked = 0
        existing = 0
        matched = 0
        for row in by_context.values():
            expected = str(row.get("g562_scenario_sha256", "") or "")
            scen = scenario_path(scenario_dir, str(row.get("map", "")), int(number(row.get("seed"), 0)))
            actual = sha256_file(scen)
            if actual:
                existing += 1
            if expected:
                checked += 1
                matched += int(bool(actual) and actual == expected)
        scores.append(
            {
                "context_dir": relpath(context_dir),
                "scenario_dir": relpath(scenario_dir),
                "contexts": len(by_context),
                "scenario_files_existing": existing,
                "scenario_hashes_checked": checked,
                "scenario_hash_matches": matched,
            }
        )
    best = max(scores, key=lambda row: (int(row["scenario_hash_matches"]), int(row["scenario_files_existing"])))
    chosen = resolve(best["context_dir"])
    return chosen, {"chosen_context_dir": best["context_dir"], "chosen_scenario_dir": best["scenario_dir"], "context_dir_scores": scores}


def context_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row.get("map", "")),
        str(row.get("agents", "")),
        str(row.get("seed", "")),
        str(row.get("budget_ms", "")),
        str(row.get("horizon_id", "")),
    )


def plan_lookup_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row.get("map", "")),
        str(row.get("agents", "")),
        str(row.get("seed", "")),
        str(row.get("budget_ms", "")),
        str(row.get("materialized_method", "")),
    )


def static_generated_uid(row: dict[str, Any]) -> str:
    return generated_theta_uid(
        TIER_B_STATIC_FLOW.underlying_method,
        str(row.get("g562_instance_uid", "")),
        [TIER_B_STATIC_FLOW.theta[col] for col in THETA_NUMERIC_COLUMNS],
    )


def build_static_plan_rows(panel: str, source_plan_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    by_context: dict[tuple[str, str, str, str, str], dict[str, str]] = {}
    for row in source_plan_rows:
        key = context_key(row)
        if key not in by_context or str(row.get("role", "")) == "additive_ltm":
            by_context[key] = row

    phase = phase_name(panel)
    rows: list[dict[str, Any]] = []
    for idx, base in enumerate(by_context.values()):
        generated_uid = static_generated_uid(base)
        identity = g562.stable_uid(
            "g562_replay_identity",
            phase,
            base.get("g562_evaluation_uid", ""),
            base.get("g562_scenario_sha256", ""),
            STATIC_FLOW_SOLVER_ALIAS,
            generated_uid,
        )
        row = dict(base)
        row.update(
            {
                "plan_row_id": f"g562_{safe_token(phase)}_{idx:08d}",
                "replay_phase": phase,
                "role": "static_flow_shield",
                "candidate_id": STATIC_FLOW_SOLVER_ALIAS,
                "theta_id": STATIC_FLOW_SOLVER_ALIAS,
                "materialized_method": STATIC_FLOW_SOLVER_ALIAS,
                "generated_theta_uid": generated_uid,
                "sampling_policy": TIER_B_STATIC_FLOW.underlying_method,
                "model_path": "",
                "variant_id": "",
                "actor_training_seed": "",
                "expected_updateparams_fingerprint": TIER_B_STATIC_FLOW.fingerprint,
                "g562_identity_digest": identity,
                **TIER_B_STATIC_FLOW.theta,
                **claims(),
            }
        )
        rows.append(row)
    return rows


def registry_rows(panel: str) -> list[dict[str, Any]]:
    row = {
        **TIER_B_STATIC_FLOW.registry_row(),
        "generated_theta_uid": "",
        "registry_role": "g565_supplement_static_flow_baseline",
        "replay_phase": phase_name(panel),
        "method": TIER_B_STATIC_FLOW.underlying_method,
        "variant_id": "",
        "actor_training_seed": "",
        **claims(),
    }
    return [row]


def audit_static_rows(rows: list[dict[str, Any]], plan_rows: list[dict[str, Any]], scenario_dir: Path, phase: str) -> list[dict[str, Any]]:
    lookup = {plan_lookup_key(row): row for row in plan_rows}
    out: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        plan = lookup.get(plan_lookup_key(row), {})
        for key in [
            "plan_row_id",
            "replay_phase",
            "context_id",
            "g562_dataset_row_id",
            "g562_instance_uid",
            "g562_evaluation_uid",
            "g562_identity_digest",
            "g562_scenario_sha256",
            "g562_physical_map_sha256",
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
        fingerprint_present = has_text(row.get("updateparams_fingerprint", ""))
        if fingerprint_present:
            fp_match, mismatches = compare_theta_to_fingerprint(row.get("updateparams_fingerprint", ""), plan or row, tolerance=1.0e-9)
        else:
            fp_match, mismatches = "", []
        scen = scenario_path(resolve(scenario_dir), str(row.get("map", "")), int(number(row.get("seed"), 0)))
        scenario_actual = sha256_file(scen)
        identity_actual = g562.stable_uid(
            "g562_replay_identity",
            phase,
            row.get("g562_evaluation_uid", ""),
            row.get("g562_scenario_sha256", ""),
            row.get("candidate_id", ""),
            row.get("generated_theta_uid", ""),
        )
        row.update(
            {
                "executed": boolish(row.get("real_solver_execution", True)),
                "is_actor_row": False,
                "is_g556_row": False,
                "is_additive_row": False,
                "is_static_flow_row": True,
                "candidate_recognized_bool": boolish(row.get("candidate_recognized")),
                "fingerprint_parsed": bool(parsed),
                "updateparams_fingerprint_present": fingerprint_present,
                "fulltheta_fingerprint_match_strict": fp_match,
                "fulltheta_fingerprint_mismatched_fields": ";".join(mismatches),
                "force_additive_false": parsed.get("force_additive") == "0" if fingerprint_present else "",
                "dual_channel_enabled": parsed.get("enable_dual_channel") == "1" if fingerprint_present else "",
                "scenario_sha256_actual": scenario_actual,
                "scenario_sha256_match": bool(scenario_actual) and scenario_actual == row.get("g562_scenario_sha256", ""),
                "identity_digest_actual": identity_actual,
                "identity_retained": bool(row.get("g562_identity_digest", "")) and identity_actual == row.get("g562_identity_digest", ""),
            }
        )
        out.append(row)
    return out


def comparable_delta(actor: dict[str, Any], baseline: dict[str, Any]) -> float:
    if not solver_success(actor) or not solver_success(baseline):
        return math.nan
    actor_ratio = solver_ratio(actor)
    baseline_ratio = solver_ratio(baseline)
    if actor_ratio is None or baseline_ratio is None:
        return math.nan
    return actor_ratio - baseline_ratio


def relative_improvement(actor: dict[str, Any], baseline: dict[str, Any]) -> float:
    if not solver_success(actor) or not solver_success(baseline):
        return math.nan
    actor_ratio = solver_ratio(actor)
    baseline_ratio = solver_ratio(baseline)
    if actor_ratio is None or baseline_ratio in {None, 0.0}:
        return math.nan
    return (baseline_ratio - actor_ratio) / baseline_ratio


def runtime_speedup(actor: dict[str, Any], baseline: dict[str, Any]) -> float:
    actor_rt = number(actor.get("probe_runtime_ms"))
    base_rt = number(baseline.get("probe_runtime_ms"))
    if not math.isfinite(actor_rt) or not math.isfinite(base_rt) or base_rt <= 0.0:
        return math.nan
    return (base_rt - actor_rt) / base_rt


def is_actor_row(row: dict[str, Any]) -> bool:
    return boolish(row.get("is_actor_row")) or str(row.get("role", "")).startswith("generated_theta::")


def build_static_pairs(source_rows: list[dict[str, Any]], static_rows: list[dict[str, Any]], panel: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str], dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in source_rows:
        grouped[context_key(row)][str(row.get("materialized_method", ""))].append(row)
    for row in static_rows:
        grouped[context_key(row)][STATIC_FLOW_SOLVER_ALIAS].append(row)

    pairs: list[dict[str, Any]] = []
    for key, by_method in sorted(grouped.items()):
        static_list = by_method.get(STATIC_FLOW_SOLVER_ALIAS, [])
        if not static_list:
            continue
        static = static_list[0]
        actors = [row for rows in by_method.values() for row in rows if is_actor_row(row)]
        for actor in actors:
            delta = comparable_delta(actor, static)
            rel = relative_improvement(actor, static)
            speed = runtime_speedup(actor, static)
            actor_success = solver_success(actor)
            static_success = solver_success(static)
            pairs.append(
                {
                    "replay_phase": phase_name(panel),
                    "source_replay_phase": source_phase(panel),
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "budget_ms": key[3],
                    "horizon_id": key[4],
                    "split": actor.get("split", ""),
                    "map_family": actor.get("map_family", ""),
                    "g562_dataset_row_id": actor.get("g562_dataset_row_id", ""),
                    "g562_evaluation_uid": actor.get("g562_evaluation_uid", ""),
                    "g562_identity_digest": actor.get("g562_identity_digest", ""),
                    "theta_id": actor.get("materialized_method", ""),
                    "method": actor.get("sampling_policy", ""),
                    "variant_id": actor.get("variant_id", ""),
                    "actor_training_seed": actor.get("actor_training_seed", ""),
                    "model_path": actor.get("model_path", ""),
                    "actor_success": actor_success,
                    "static_flow_success": static_success,
                    "success_gain_vs_static_flow": bool(actor_success and not static_success),
                    "success_regression_vs_static_flow": bool(static_success and not actor_success),
                    "actor_ratio": solver_ratio(actor),
                    "static_flow_ratio": solver_ratio(static),
                    "delta_vs_static_flow": delta,
                    "relative_improvement_vs_static_flow": rel,
                    "runtime_speedup_vs_static_flow": speed,
                    "actor_runtime_ms": actor.get("probe_runtime_ms", ""),
                    "static_flow_runtime_ms": static.get("probe_runtime_ms", ""),
                    "actor_expanded_nodes": actor.get("expanded_nodes", ""),
                    "static_flow_expanded_nodes": static.get("expanded_nodes", ""),
                    "actor_low_level_pibt_calls": actor.get("low_level_pibt_calls", ""),
                    "static_flow_low_level_pibt_calls": static.get("low_level_pibt_calls", ""),
                    "candidate_recognized": actor.get("candidate_recognized_bool", False),
                    "fingerprint_match": actor.get("fulltheta_fingerprint_match_strict", False),
                    "static_flow_fingerprint_match": static.get("fulltheta_fingerprint_match_strict", False),
                    "scenario_hash_match": actor.get("scenario_sha256_match", False),
                    "static_flow_scenario_hash_match": static.get("scenario_sha256_match", False),
                    "identity_retained": actor.get("identity_retained", False),
                    "static_flow_identity_retained": static.get("identity_retained", False),
                    "force_additive_false": actor.get("force_additive_false", ""),
                    "dual_channel_enabled": actor.get("dual_channel_enabled", ""),
                    **{col: actor.get(col, "") for col in THETA_NUMERIC_COLUMNS},
                    **claims(),
                }
            )
    return pairs


def finite_values(rows: list[dict[str, Any]], column: str) -> list[float]:
    out: list[float] = []
    for row in rows:
        value = number(row.get(column))
        if math.isfinite(value):
            out.append(value)
    return out


def summarize_pair_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = finite_values(rows, "delta_vs_static_flow")
    rels = finite_values(rows, "relative_improvement_vs_static_flow")
    speeds = finite_values(rows, "runtime_speedup_vs_static_flow")
    actor_successes = sum(boolish(row.get("actor_success")) for row in rows)
    static_successes = sum(boolish(row.get("static_flow_success")) for row in rows)
    return {
        "pairs": len(rows),
        "finite_quality_pairs": len(deltas),
        "actor_success_count": actor_successes,
        "static_flow_success_count": static_successes,
        "actor_success_rate": actor_successes / max(1, len(rows)),
        "static_flow_success_rate": static_successes / max(1, len(rows)),
        "success_gains_vs_static_flow": sum(boolish(row.get("success_gain_vs_static_flow")) for row in rows),
        "success_regressions_vs_static_flow": sum(boolish(row.get("success_regression_vs_static_flow")) for row in rows),
        "better_count_vs_static_flow": sum(value < 0.0 for value in deltas),
        "worse_count_vs_static_flow": sum(value > 0.0 for value in deltas),
        "tie_count_vs_static_flow": sum(value == 0.0 for value in deltas),
        "mean_delta_vs_static_flow": float(statistics.mean(deltas)) if deltas else None,
        "median_delta_vs_static_flow": float(statistics.median(deltas)) if deltas else None,
        "mean_relative_improvement_vs_static_flow": float(statistics.mean(rels)) if rels else None,
        "median_relative_improvement_vs_static_flow": float(statistics.median(rels)) if rels else None,
        "mean_runtime_speedup_vs_static_flow": float(statistics.mean(speeds)) if speeds else None,
        "median_runtime_speedup_vs_static_flow": float(statistics.median(speeds)) if speeds else None,
        "quality_delta_q90_vs_static_flow": float(np.quantile(deltas, 0.90)) if deltas else None,
        "quality_delta_q95_vs_static_flow": float(np.quantile(deltas, 0.95)) if deltas else None,
    }


def by_variant_rows(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pairs:
        grouped[str(row.get("variant_id", "") or "unknown")].append(row)
    return [{"variant_id": variant, **summarize_pair_group(rows), **claims()} for variant, rows in sorted(grouped.items())]


def failure_cases(pairs: list[dict[str, Any]], limit: int = 500) -> list[dict[str, Any]]:
    def severity(row: dict[str, Any]) -> tuple[int, float]:
        delta = number(row.get("delta_vs_static_flow"), -999.0)
        return (1 if boolish(row.get("success_regression_vs_static_flow")) else 0, delta)

    cases = [
        row
        for row in pairs
        if boolish(row.get("success_regression_vs_static_flow")) or (math.isfinite(number(row.get("delta_vs_static_flow"))) and number(row.get("delta_vs_static_flow")) > 0.0)
    ]
    return sorted(cases, key=severity, reverse=True)[:limit] or [{"decision": "g565_static_flow_supplement_no_static_flow_failure_cases_observed", **claims()}]


def summarize_panel(
    panel: str,
    plan_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    static_rows: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
    elapsed_sec: float,
    context_dir_audit: dict[str, Any],
    *,
    solver_reused_existing_results: bool,
) -> dict[str, Any]:
    fingerprint_rows = [row for row in static_rows if boolish(row.get("updateparams_fingerprint_present"))]
    missing_fingerprint_rows = len(static_rows) - len(fingerprint_rows)
    static_exact = sum(boolish(row.get("fulltheta_fingerprint_match_strict")) for row in fingerprint_rows)
    static_recognized = sum(boolish(row.get("candidate_recognized_bool")) for row in static_rows)
    static_scenario = sum(boolish(row.get("scenario_sha256_match")) for row in static_rows)
    static_identity = sum(boolish(row.get("identity_retained")) for row in static_rows)
    static_force = sum(boolish(row.get("force_additive_false")) for row in fingerprint_rows)
    static_dual = sum(boolish(row.get("dual_channel_enabled")) for row in fingerprint_rows)
    materialized = bool(
        static_rows
        and static_exact == len(fingerprint_rows)
        and static_recognized == len(static_rows)
        and static_scenario == len(static_rows)
        and static_identity == len(static_rows)
        and static_force == len(fingerprint_rows)
        and static_dual == len(fingerprint_rows)
    )
    rich_pairs = [row for row in pairs if str(row.get("variant_id", "")).upper().startswith("E")]
    return {
        "schema_version": f"{ROUND}_{panel}_static_flow_supplement_summary_v1",
        "decision": "g565_static_flow_supplement_completed" if materialized else "g565_static_flow_supplement_materialization_incomplete",
        "panel": panel,
        "supplemental_not_original_gate": True,
        "same_instance_replay": True,
        "solver_reused_existing_results": solver_reused_existing_results,
        "context_dir_audit": context_dir_audit,
        "source_results": relpath(paths_for_panel(panel)["source_results"]),
        "source_plan": relpath(paths_for_panel(panel)["source_plan"]),
        "static_flow_solver_alias": STATIC_FLOW_SOLVER_ALIAS,
        "static_flow_underlying_method": TIER_B_STATIC_FLOW.underlying_method,
        "planned_static_rows": len(plan_rows),
        "executed_static_rows": len(static_rows),
        "source_rows_loaded": len(source_rows),
        "source_actor_rows_loaded": sum(is_actor_row(row) for row in source_rows),
        "contexts": len({context_key(row) for row in plan_rows}),
        "static_candidate_recognized_rate": static_recognized / max(1, len(static_rows)),
        "static_updateparams_fingerprint_present_rows": len(fingerprint_rows),
        "static_updateparams_fingerprint_missing_rows": missing_fingerprint_rows,
        "static_fingerprint_exact_rate": static_exact / max(1, len(fingerprint_rows)),
        "static_scenario_hash_match_rate": static_scenario / max(1, len(static_rows)),
        "static_identity_retention_rate": static_identity / max(1, len(static_rows)),
        "static_force_additive_false_rate": static_force / max(1, len(fingerprint_rows)),
        "static_dual_channel_enabled_rate": static_dual / max(1, len(fingerprint_rows)),
        "static_flow_materialization_passed": materialized,
        "all_actor_vs_static_flow": summarize_pair_group(pairs),
        "rich_actor_vs_static_flow": summarize_pair_group(rich_pairs),
        "variant_counts": dict(Counter(str(row.get("variant_id", "") or "unknown") for row in pairs)),
        "elapsed_sec": elapsed_sec,
        **claims(),
    }


def write_report(panel: str, summary: dict[str, Any]) -> None:
    all_stats = summary["all_actor_vs_static_flow"]
    rich_stats = summary["rich_actor_vs_static_flow"]
    text = (
        f"# G5.65 {panel.title()} Static-Flow Supplement\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- supplemental_not_original_gate: `{summary['supplemental_not_original_gate']}`\n"
        f"- same_instance_replay: `{summary['same_instance_replay']}`\n"
        f"- contexts: `{summary['contexts']}`\n"
        f"- static rows: `{summary['executed_static_rows']}`\n"
        f"- static materialization passed: `{summary['static_flow_materialization_passed']}`\n"
        f"- all actor pairs: `{all_stats['pairs']}`; better/worse/tie vs static_flow: "
        f"`{all_stats['better_count_vs_static_flow']}` / `{all_stats['worse_count_vs_static_flow']}` / `{all_stats['tie_count_vs_static_flow']}`\n"
        f"- all actor success gains/regressions vs static_flow: "
        f"`{all_stats['success_gains_vs_static_flow']}` / `{all_stats['success_regressions_vs_static_flow']}`\n"
        f"- all actor median relative improvement vs static_flow: `{all_stats['median_relative_improvement_vs_static_flow']}`\n"
        f"- rich actor pairs: `{rich_stats['pairs']}`; better/worse/tie vs static_flow: "
        f"`{rich_stats['better_count_vs_static_flow']}` / `{rich_stats['worse_count_vs_static_flow']}` / `{rich_stats['tie_count_vs_static_flow']}`\n"
        f"- rich actor success gains/regressions vs static_flow: "
        f"`{rich_stats['success_gains_vs_static_flow']}` / `{rich_stats['success_regressions_vs_static_flow']}`\n"
        f"- rich actor median relative improvement vs static_flow: `{rich_stats['median_relative_improvement_vs_static_flow']}`\n\n"
        "This supplement adds the historical hand static-flow baseline to the exact same G5.65 context panel. "
        "It is evidence for the static-flow comparison only and does not retroactively change the original G5.65 gate against g556_c063174.\n"
    )
    write_text(paths_for_panel(panel)["report"], text)


def write_combined_report(combined: dict[str, Any]) -> None:
    panels = combined.get("panels", {})

    def line(panel: str) -> str:
        summary = panels.get(panel, {})
        rich = summary.get("rich_actor_vs_static_flow", {})
        return (
            f"| {panel} | {summary.get('contexts')} | {rich.get('pairs')} | "
            f"{rich.get('success_gains_vs_static_flow')} / {rich.get('success_regressions_vs_static_flow')} | "
            f"{rich.get('better_count_vs_static_flow')} / {rich.get('worse_count_vs_static_flow')} / {rich.get('tie_count_vs_static_flow')} | "
            f"{rich.get('median_delta_vs_static_flow')} | {rich.get('median_relative_improvement_vs_static_flow')} | "
            f"{rich.get('actor_success_rate')} / {rich.get('static_flow_success_rate')} |"
        )

    text = (
        "# G5.65 Static-Flow Supplement\n\n"
        f"- decision: `{combined.get('decision')}`\n"
        f"- supplemental_not_original_gate: `{combined.get('supplemental_not_original_gate')}`\n"
        f"- static baseline: `{STATIC_FLOW_SOLVER_ALIAS}` / `{TIER_B_STATIC_FLOW.underlying_method}`\n"
        "- scope: same-context replay against the historical hand static-flow shield; the original G5.65 gate against `g556_c063174` is unchanged.\n\n"
        "| panel | contexts | rich pairs | success gains/regressions | better/worse/tie | median delta | median relative improvement | actor/static success rate |\n"
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n"
        f"{line('fresh')}\n"
        f"{line('expanded')}\n\n"
        "Interpretation: G5.65 rich actors clearly beat the old static-flow shield on this supplemental same-instance replay. "
        "This supports the weaker/static-flow comparison, while the stricter G5.65 conclusion versus `g556_c063174` remains not supported because of tail risk and success regressions against that stronger baseline.\n"
    )
    write_text(REPORTS / f"{ROUND}_static_flow_supplement.md", text)


def run_panel(panel: str, args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    paths = paths_for_panel(panel)
    source_plan_rows = read_rows(paths["source_plan"])
    source_rows = read_rows(paths["source_results"])
    if not source_plan_rows or not source_rows:
        summary = {
            "schema_version": f"{ROUND}_{panel}_static_flow_supplement_summary_v1",
            "decision": "g565_static_flow_supplement_blocked_missing_source_panel",
            "panel": panel,
            "source_plan_exists": paths["source_plan"].exists(),
            "source_results_exists": paths["source_results"].exists(),
            **claims(),
        }
        write_json(paths["summary"], summary)
        return summary

    register_context_maps()
    chosen_context_dir, context_dir_audit = choose_context_dir(source_plan_rows)
    paths["scenario_dir"] = chosen_context_dir / "scenarios"
    static_plan = build_static_plan_rows(panel, source_plan_rows)
    write_rows(paths["plan"], static_plan)
    write_rows(paths["registry"], registry_rows(panel))
    if args.plan_only:
        summary = {
            "schema_version": f"{ROUND}_{panel}_static_flow_supplement_summary_v1",
            "decision": "g565_static_flow_supplement_plan_created",
            "panel": panel,
            "planned_static_rows": len(static_plan),
            "contexts": len({context_key(row) for row in static_plan}),
            "scenario_dir": relpath(paths["scenario_dir"]),
            "context_dir_audit": context_dir_audit,
            **claims(),
        }
        write_json(paths["summary"], summary)
        return summary

    solver_reused_existing_results = bool(args.resume_existing and paths["results"].exists() and not args.overwrite)
    if not solver_reused_existing_results:
        run_args = SimpleNamespace(
            binary=args.binary,
            overwrite=bool(args.overwrite or not args.resume_existing),
            max_workers=args.max_workers,
            phase=phase_name(panel),
        )
        rc = g562.run_solver(static_plan, paths, run_args)
        if rc != 0:
            summary = {
                "schema_version": f"{ROUND}_{panel}_static_flow_supplement_summary_v1",
                "decision": "g565_static_flow_supplement_blocked_solver_not_executed",
                "panel": panel,
                "rc": rc,
                "context_dir_audit": context_dir_audit,
                **claims(),
            }
            write_json(paths["summary"], summary)
            return summary

    static_rows = audit_static_rows(read_rows(paths["results"]), static_plan, paths["scenario_dir"], phase_name(panel))
    write_rows(paths["results"], static_rows)
    pairs = build_static_pairs(source_rows, static_rows, panel)
    write_rows(paths["pairs"], pairs)
    write_rows(paths["by_variant"], by_variant_rows(pairs))
    write_rows(paths["failure_cases"], failure_cases(pairs))
    summary = summarize_panel(
        panel,
        static_plan,
        source_rows,
        static_rows,
        pairs,
        time.perf_counter() - started,
        context_dir_audit,
        solver_reused_existing_results=solver_reused_existing_results,
    )
    write_json(paths["summary"], summary)
    write_report(panel, summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Supplement G5.65 panels with same-context repair5g59_static_flow_shield replay.")
    parser.add_argument("--panels", nargs="+", default=["fresh", "expanded"], choices=["fresh", "expanded"])
    parser.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)

    summaries = [run_panel(panel, args) for panel in args.panels]
    combined = {
        "schema_version": f"{ROUND}_static_flow_supplement_combined_summary_v1",
        "decision": (
            "g565_static_flow_supplement_completed"
            if all(summary.get("decision") in {"g565_static_flow_supplement_completed", "g565_static_flow_supplement_plan_created"} for summary in summaries)
            else "g565_static_flow_supplement_incomplete"
        ),
        "panels": {str(summary.get("panel")): summary for summary in summaries},
        "supplemental_not_original_gate": True,
        **claims(),
    }
    write_json(REPORTS / f"{ROUND}_static_flow_supplement_summary.json", combined)
    write_combined_report(combined)
    print(json.dumps({"decision": combined["decision"], "panels": [summary.get("decision") for summary in summaries]}, sort_keys=True))
    return 0 if combined["decision"] == "g565_static_flow_supplement_completed" or args.plan_only else 2


if __name__ == "__main__":
    raise SystemExit(main())

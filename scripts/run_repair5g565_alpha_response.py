from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5g562_replay_truth as g562  # noqa: E402
from gcst.alpha_trust_head import alpha_blend_theta, alpha_grid  # noqa: E402
from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR, G560_TRAINING_ROWS  # noqa: E402
from gcst.theta_schema import THETA_NUMERIC_COLUMNS  # noqa: E402
from run_repair5g565_fresh_solver_panel import load_contexts  # noqa: E402


ROUND = "phase5p5_repair5g565"
REPORTS = ROOT / "outputs/reports"
TABLES = ROOT / "outputs/tables"
FRESH_SUMMARY = REPORTS / f"{ROUND}_fresh_solver_panel_summary.json"
FRESH_PAIRS = TABLES / f"{ROUND}_fresh_solver_panel_pairs.csv"
LOGS = ROOT / "outputs/logs"
MIN_ALPHA_CONTEXTS = 800


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def finite_float(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    return out if np_isfinite(out) else None


def np_isfinite(value: float) -> bool:
    return value == value and value not in {float("inf"), float("-inf")}


def claims() -> dict[str, bool]:
    return {
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }


def row_uid(row: dict[str, Any]) -> str:
    return str(row.get("g562_evaluation_uid") or row.get("g560_evaluation_uid") or row.get("evaluation_uid") or "")


def row_has_tail_risk(row: dict[str, Any]) -> bool:
    quality_delta = finite_float(row.get("quality_delta_vs_g556"))
    return boolish(row.get("success_regression")) or (quality_delta is not None and quality_delta > 0.0)


def fresh_actor_pairs_for_alpha(limit: int) -> tuple[list[dict[str, str]], bool]:
    fresh = read_json(FRESH_SUMMARY)
    pairs = read_rows(FRESH_PAIRS)
    if fresh.get("decision") == "g565_fresh_solver_transfer_positive":
        return [], False
    tail_rows = [row for row in pairs if row_uid(row) and row_has_tail_risk(row)]
    source_rows = tail_rows if tail_rows else [row for row in pairs if row_uid(row)]
    selected_uids: set[str] = set()
    selected: list[dict[str, str]] = []
    for row in source_rows:
        uid = row_uid(row)
        if not uid:
            continue
        if uid not in selected_uids and limit and len(selected_uids) >= limit:
            continue
        selected_uids.add(uid)
        selected.append(row)
    return selected, bool(tail_rows)


def effective_alpha_context_limit(requested: int, minimum: int = MIN_ALPHA_CONTEXTS) -> int:
    return max(int(requested), int(minimum))


def alpha_variant(alpha: Any) -> str:
    token = str(alpha).replace(".", "p").replace("-", "m")
    return f"ALPHA_{token}"


def alpha_actor_variant(raw_variant: Any, alpha: Any) -> str:
    raw = str(raw_variant or "ACTOR").upper()
    return f"{raw}_{alpha_variant(alpha)}"


def alpha_theta_rows(contexts: list[g562.ReplayContext], design_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    context_by_uid = {ctx.evaluation_uid: ctx for ctx in contexts}
    rows: list[dict[str, Any]] = []
    for row in design_rows:
        ctx = context_by_uid.get(str(row.get("g560_evaluation_uid", "")))
        if ctx is None:
            continue
        alpha = row.get("alpha_to_raw_actor_residual", "")
        theta = {col: row[col] for col in THETA_NUMERIC_COLUMNS if col in row}
        rows.append(
            {
                "phase": "g565_alpha_response",
                "context_id": ctx.dataset_row_id,
                "g562_evaluation_uid": ctx.evaluation_uid,
                "variant_id": alpha_actor_variant(row.get("raw_actor_variant_id", ""), alpha),
                "variant_name": f"alpha_response_{row.get('raw_actor_variant_id', '')}_{alpha}",
                "seed": row.get("raw_actor_training_seed", ""),
                "method": f"g565_alpha_response_{row.get('raw_actor_method', '')}_alpha_{alpha}",
                "model_path": row.get("raw_actor_model_path", "alpha_response_raw_actor_residual"),
                **theta,
            }
        )
    return rows


def summarize_exact_alpha(rows: list[dict[str, Any]], pairs: list[dict[str, Any]], plan_rows: list[dict[str, Any]]) -> dict[str, Any]:
    actor_rows = [row for row in rows if g562.boolish(row.get("is_actor_row"))]
    exact = sum(g562.boolish(row.get("fulltheta_fingerprint_match_strict")) for row in actor_rows)
    recognized = sum(g562.boolish(row.get("candidate_recognized_bool")) for row in actor_rows)
    scenario = sum(g562.boolish(row.get("scenario_sha256_match")) for row in actor_rows)
    identity = sum(g562.boolish(row.get("identity_retained")) for row in actor_rows)
    force_additive_false = sum(g562.boolish(row.get("force_additive_false")) for row in actor_rows)
    dual_channel_enabled = sum(g562.boolish(row.get("dual_channel_enabled")) for row in actor_rows)
    regressions = sum(g562.boolish(row.get("success_regression")) for row in pairs)
    gains = sum(g562.boolish(row.get("success_gain")) for row in pairs)
    by_alpha: dict[str, dict[str, Any]] = {}
    all_quality_values: list[float] = []
    for pair in pairs:
        variant_id = str(pair.get("variant_id", "") or "unknown")
        model_path = str(pair.get("model_path", "") or "")
        method = str(pair.get("method", "") or "")
        variant = f"{variant_id}::{model_path or method or 'unknown'}"
        bucket = by_alpha.setdefault(
            variant,
            {
                "variant_id": variant_id,
                "model_path": model_path,
                "method": method,
                "pairs": 0,
                "success_regressions": 0,
                "success_gains": 0,
                "better_count_vs_g556": 0,
                "worse_count_vs_g556": 0,
                "quality_delta_vs_g556": [],
            },
        )
        bucket["pairs"] += 1
        bucket["success_regressions"] += int(g562.boolish(pair.get("success_regression")))
        bucket["success_gains"] += int(g562.boolish(pair.get("success_gain")))
        value = finite_float(pair.get("quality_delta_vs_g556"))
        if value is not None:
            bucket["quality_delta_vs_g556"].append(value)
            all_quality_values.append(value)
            bucket["better_count_vs_g556"] += int(value < 0.0)
            bucket["worse_count_vs_g556"] += int(value > 0.0)
    alpha_curve: dict[str, Any] = {}
    for variant, bucket in sorted(by_alpha.items()):
        values = bucket.pop("quality_delta_vs_g556")
        alpha_curve[variant] = {
            **bucket,
            "mean_quality_delta_vs_g556": sum(values) / len(values) if values else None,
            "median_quality_delta_vs_g556": sorted(values)[len(values) // 2] if values else None,
            "success_regression_rate": bucket["success_regressions"] / max(1, bucket["pairs"]),
            "success_gain_rate": bucket["success_gains"] / max(1, bucket["pairs"]),
        }
    safe = [
        variant
        for variant, bucket in alpha_curve.items()
        if bucket["success_regressions"] == 0 and bucket["worse_count_vs_g556"] == 0 and bucket["pairs"]
    ]
    worse_count = sum(value > 0.0 for value in all_quality_values)
    better_count = sum(value < 0.0 for value in all_quality_values)
    harmful_tail_values = [value for value in all_quality_values if value > 0.0]
    harmful_cvar = (
        sum(sorted(harmful_tail_values, reverse=True)[: max(1, int(len(harmful_tail_values) * 0.10 + 0.999))])
        / max(1, min(len(harmful_tail_values), max(1, int(len(harmful_tail_values) * 0.10 + 0.999))))
        if harmful_tail_values
        else 0.0
    )
    return {
        "exact_materialized": True,
        "planned_rows": len(plan_rows),
        "executed_rows": len(rows),
        "actor_candidate_rows": len(actor_rows),
        "candidate_recognized_rate": recognized / max(1, len(actor_rows)),
        "fingerprint_exact_rate": exact / max(1, len(actor_rows)),
        "scenario_hash_match_rate": scenario / max(1, len(actor_rows)),
        "identity_retention_rate": identity / max(1, len(actor_rows)),
        "force_additive_false_rate": force_additive_false / max(1, len(actor_rows)),
        "dual_channel_enabled_rate": dual_channel_enabled / max(1, len(actor_rows)),
        "replay_pairs": len(pairs),
        "success_regressions": regressions,
        "success_gains": gains,
        "better_count_vs_g556": better_count,
        "worse_count_vs_g556": worse_count,
        "harmful_quality_tail_present": bool(regressions > 0 or worse_count > 0),
        "harmful_quality_delta_q90_vs_g556": sorted(all_quality_values)[int(0.90 * (len(all_quality_values) - 1))] if all_quality_values else None,
        "harmful_quality_delta_q95_vs_g556": sorted(all_quality_values)[int(0.95 * (len(all_quality_values) - 1))] if all_quality_values else None,
        "harmful_quality_delta_cvar_top10_vs_g556": harmful_cvar,
        "safe_alpha_frontier": safe,
        "alpha_curve": alpha_curve,
        "alpha_exact_materialization_passed": bool(
            actor_rows
            and exact == len(actor_rows)
            and recognized == len(actor_rows)
            and scenario == len(actor_rows)
            and identity == len(actor_rows)
            and force_additive_false == len(actor_rows)
            and dual_channel_enabled == len(actor_rows)
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the G5.65 alpha response panel when fresh transfer has tail risk.")
    parser.add_argument("--rows-path", type=Path, default=G560_TRAINING_ROWS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--max-contexts", type=int, default=MIN_ALPHA_CONTEXTS)
    parser.add_argument("--min-alpha-contexts", type=int, default=MIN_ALPHA_CONTEXTS)
    parser.add_argument("--alphas", default="0,0.125,0.25,0.5,0.75,1.0")
    parser.add_argument("--binary", type=Path, default=Path("build/phase1a-batch/phase1a_batch"))
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)

    started = time.perf_counter()
    solver_overwrite = bool(args.overwrite or not args.resume_existing)
    alphas = alpha_grid(float(token) for token in args.alphas.split(",") if token.strip())
    effective_max_contexts = effective_alpha_context_limit(args.max_contexts, args.min_alpha_contexts)
    fresh_pairs, tail_rows_present = fresh_actor_pairs_for_alpha(effective_max_contexts)
    rows: list[dict[str, Any]] = []
    for pair in fresh_pairs:
        uid = row_uid(pair)
        actor_theta = {col: finite_float(pair.get(col)) for col in THETA_NUMERIC_COLUMNS}
        if not uid or any(value is None for value in actor_theta.values()):
            continue
        for alpha in alphas:
            rows.append(
                {
                    "panel_row_id": f"g565_alpha_{len(rows):08d}",
                    "g560_evaluation_uid": uid,
                    "split": pair.get("split", ""),
                    "map": pair.get("map", ""),
                    "map_family": pair.get("map_family", ""),
                    "agent_count": pair.get("agents", ""),
                    "seed": pair.get("seed", ""),
                    "budget_ms": pair.get("budget_ms", ""),
                    "alpha_to_raw_actor_residual": alpha,
                    "raw_actor_theta_id": pair.get("theta_id", ""),
                    "raw_actor_method": pair.get("method", ""),
                    "raw_actor_variant_id": pair.get("variant_id", ""),
                    "raw_actor_training_seed": pair.get("actor_training_seed", ""),
                    "raw_actor_model_path": pair.get("model_path", ""),
                    "raw_actor_quality_delta_vs_g556": pair.get("quality_delta_vs_g556", ""),
                    "raw_actor_success_regression": pair.get("success_regression", ""),
                    "fresh_transfer_tail_context": row_has_tail_risk(pair),
                    "requires_exact_materialization_before_claim": True,
                    **alpha_blend_theta([actor_theta[col] for col in THETA_NUMERIC_COLUMNS], alpha),
                    **claims(),
                }
            )
    fresh_decision = read_json(FRESH_SUMMARY).get("decision")
    decision = "g565_alpha_response_not_needed" if not rows and fresh_decision == "g565_fresh_solver_transfer_positive" else "g565_alpha_response_panel_designed"
    summary = {
        "schema_version": f"{ROUND}_alpha_response_summary_v1",
        "decision": decision,
        "fresh_solver_decision": fresh_decision,
        "tail_contexts_from_fresh_solver": len({row_uid(row) for row in fresh_pairs if row_has_tail_risk(row)}),
        "tail_rows_present": tail_rows_present,
        "contexts_with_raw_actor_residual": len({row["g560_evaluation_uid"] for row in rows}),
        "fresh_actor_pair_rows_selected": len(fresh_pairs),
        "requested_max_contexts": int(args.max_contexts),
        "min_alpha_contexts": int(args.min_alpha_contexts),
        "effective_max_contexts": effective_max_contexts,
        "alpha_rows": len(rows),
        "alphas": alphas,
        "exact_materialized": False,
        "solver_overwrite": solver_overwrite,
        "alpha_trust_head_trained": False,
        "fresh_fixed_panel_reran_after_alpha": False,
        "alpha_repair_support_scope": "exact_alpha_response_panel_only",
        "elapsed_sec": time.perf_counter() - started,
        **claims(),
    }
    write_rows(TABLES / f"{ROUND}_alpha_response_design.csv", rows)
    if not rows or args.plan_only:
        write_rows(TABLES / f"{ROUND}_alpha_response_pairs.csv", [])
        write_json(REPORTS / f"{ROUND}_alpha_response_summary.json", summary)
        print(json.dumps(summary, sort_keys=True))
        return 0

    wanted_uids = {str(row.get("g560_evaluation_uid", "")) for row in rows}
    contexts = [ctx for ctx in load_contexts(resolve(args.rows_path), resolve(args.context_dir), 0, "any") if ctx.evaluation_uid in wanted_uids]
    theta_rows = alpha_theta_rows(contexts, rows)
    plan_rows, registry_rows = g562.build_plan_and_registry(contexts, theta_rows, "g565_alpha_response")
    paths = {
        "plan": TABLES / f"{ROUND}_alpha_response_plan.csv",
        "registry": TABLES / f"{ROUND}_alpha_response_registry.csv",
        "results": TABLES / f"{ROUND}_alpha_response_results.csv",
        "raw_results": TABLES / f"{ROUND}_alpha_response_results.raw.csv",
        "pairs": TABLES / f"{ROUND}_alpha_response_pairs.csv",
        "summary": REPORTS / f"{ROUND}_alpha_response_summary.json",
        "scenario_metadata": REPORTS / f"{ROUND}_alpha_response_scenario_generation.json",
        "log_dir": LOGS / f"{ROUND}_alpha_response",
        "scenario_dir": resolve(args.context_dir) / "scenarios",
    }
    write_rows(paths["plan"], plan_rows)
    write_rows(paths["registry"], registry_rows)
    run_args = SimpleNamespace(binary=args.binary, overwrite=solver_overwrite, max_workers=args.max_workers, phase="g565_alpha_response")
    rc = g562.run_solver(plan_rows, paths, run_args)
    if rc != 0:
        summary.update({"decision": "g565_alpha_response_blocked_solver_not_executed", "solver_rc": rc, "elapsed_sec": time.perf_counter() - started})
        write_rows(paths["pairs"], [])
        write_json(REPORTS / f"{ROUND}_alpha_response_summary.json", summary)
        print(json.dumps(summary, sort_keys=True))
        return rc
    audited = g562.audit_results(g562.read_rows(paths["results"]), plan_rows, paths["scenario_dir"], "g565_alpha_response")
    write_rows(paths["results"], audited)
    pairs = g562.build_pairs(audited, "g565_alpha_response")
    write_rows(paths["pairs"], pairs)
    exact = summarize_exact_alpha(audited, pairs, plan_rows)
    safe_gain_variants = [
        variant
        for variant, bucket in exact.get("alpha_curve", {}).items()
        if bucket.get("success_regressions") == 0 and bucket.get("worse_count_vs_g556") == 0 and bucket.get("success_gains", 0) > 0
    ]
    safe_no_gain_variants = [
        variant
        for variant, bucket in exact.get("alpha_curve", {}).items()
        if bucket.get("success_regressions") == 0 and bucket.get("worse_count_vs_g556") == 0 and bucket.get("success_gains", 0) <= 0 and bucket.get("pairs", 0)
    ]
    exact["safe_gain_alpha_variants"] = safe_gain_variants
    exact["safe_no_gain_alpha_variants"] = safe_no_gain_variants
    if exact["alpha_exact_materialization_passed"] and safe_gain_variants:
        decision = "g565_alpha_calibration_repaired_tail"
    elif exact["alpha_exact_materialization_passed"] and safe_no_gain_variants:
        decision = "g565_alpha_calibration_no_gain"
    elif exact["alpha_exact_materialization_passed"]:
        decision = "g565_alpha_calibration_tail_remaining"
    else:
        decision = "g565_alpha_response_materialization_incomplete"
    summary.update({**exact, "decision": decision, "elapsed_sec": time.perf_counter() - started})
    write_json(REPORTS / f"{ROUND}_alpha_response_summary.json", summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

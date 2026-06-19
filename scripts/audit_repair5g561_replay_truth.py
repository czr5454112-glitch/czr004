from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.label_v5 import pair_record  # noqa: E402
from gcst.schemas_v51 import PRIMARY_BASELINE, parse_bool  # noqa: E402
from gcst.theta_schema import (  # noqa: E402
    BASELINE_G556,
    THETA_HI,
    THETA_LO,
    THETA_NUMERIC_COLUMNS,
    compare_theta_to_fingerprint,
    expected_cpp_params,
    parse_updateparams_fingerprint,
    schema_json,
    schema_rows,
    theta_mode,
)


SOURCE = "phase5p5_repair5g560"
ROUND = "phase5p5_repair5g561"

G560_PLAN = Path(f"outputs/tables/{SOURCE}_direct_actor_dev_replay_plan.csv")
G560_RESULTS = Path(f"outputs/tables/{SOURCE}_direct_actor_dev_replay_results.csv")
G560_REGISTRY = Path(f"outputs/tables/{SOURCE}_direct_actor_generated_theta_registry.csv")
G560_PAIRS = Path(f"outputs/tables/{SOURCE}_direct_actor_dev_replay_pairs.csv")
G560_SUMMARY = Path(f"outputs/reports/{SOURCE}_direct_actor_dev_replay_summary.json")

AUDIT_MD = Path(f"outputs/reports/{ROUND}_g560_replay_truth_audit.md")
AUDIT_JSON = Path(f"outputs/reports/{ROUND}_g560_replay_truth_audit_summary.json")
ROW_AUDIT = Path(f"outputs/tables/{ROUND}_g560_row_materialization_audit.csv")
REGRESSION_AUDIT = Path(f"outputs/tables/{ROUND}_g560_regression_truth_audit.csv")
THETA_SCHEMA_DIFF = Path(f"outputs/tables/{ROUND}_theta_schema_diff.csv")
CANONICAL_SCHEMA_JSON = Path(f"outputs/reports/{ROUND}_canonical_theta_schema.json")
CONTRACT_RESULTS = Path(f"outputs/tables/{ROUND}_materialization_contract_results.csv")
CONTRACT_SUMMARY = Path(f"outputs/reports/{ROUND}_materialization_contract_summary.json")
CORRECTED_PAIRS = Path(f"outputs/tables/{ROUND}_corrected_g560_replay_pairs.csv")
CORRECTED_SUMMARY = Path(f"outputs/reports/{ROUND}_corrected_g560_replay_summary.json")


OLD_G560_ACTOR_BOUNDS = {
    "theta_alpha_cong_commit_progress": (0.0, 2.0),
    "theta_alpha_cong_commit_nonprogress": (0.0, 2.0),
    "theta_alpha_cong_block": (0.0, 2.0),
    "theta_alpha_cong_wait_progress": (0.0, 2.0),
    "theta_alpha_cong_wait_nonprogress": (0.0, 2.0),
    "theta_alpha_flow_commit_progress": (0.0, 2.0),
    "theta_alpha_flow_wait_progress": (0.0, 2.0),
    "theta_rho_cong_decay": (0.70, 1.0),
    "theta_rho_flow_decay": (0.70, 1.0),
    "theta_lambda_cong": (0.0, 2.0),
    "theta_lambda_flow": (0.0, 2.0),
    "theta_flow_shield_beta": (0.0, 1.0),
    "theta_max_flow_shield": (0.25, 1.5),
    "theta_min_edge_cost": (0.0, 5.0),
    "theta_max_edge_cost": (1.0, 12.0),
}


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


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
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with p.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: str | Path) -> dict[str, Any]:
    p = resolve(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def stable_uid(*parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def context_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row.get("map", "")),
        str(row.get("agents", row.get("agent_count", ""))),
        str(row.get("seed", row.get("solver_seed", ""))),
        str(row.get("budget_ms", row.get("nominal_budget_ms", ""))),
        str(row.get("horizon_id", "")),
    )


def is_actor_row(row: dict[str, Any]) -> bool:
    candidate = str(row.get("candidate_id", row.get("materialized_method", "")))
    return bool(candidate) and candidate != PRIMARY_BASELINE


def finite_float(value: Any, default: float = math.nan) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def theta_numeric_match(left: dict[str, Any], right: dict[str, Any], tol: float = 1.0e-6) -> tuple[bool, list[str]]:
    missing: list[str] = []
    for col in THETA_NUMERIC_COLUMNS:
        a = finite_float(left.get(col))
        b = finite_float(right.get(col))
        if not (math.isfinite(a) and math.isfinite(b)) or abs(a - b) > tol:
            missing.append(col)
    if theta_mode(left) != theta_mode(right):
        missing.append("theta_goal_projection_mode")
    return not missing, missing


def strict_fp_match(fingerprint: Any, theta: dict[str, Any]) -> tuple[bool, list[str]]:
    return compare_theta_to_fingerprint(fingerprint, theta, tolerance=1.0e-9)


def relaxed_fp_match(fingerprint: Any, theta: dict[str, Any]) -> tuple[bool, list[str]]:
    return compare_theta_to_fingerprint(fingerprint, theta, tolerance=1.0e-5)


def bool_from_fingerprint(parsed: dict[str, str], key: str) -> bool | None:
    value = parsed.get(key)
    if value is None:
        return None
    try:
        return abs(float(value)) > 0.5
    except ValueError:
        return str(value).strip().lower() in {"true", "yes", "y"}


def plan_identity(plan: dict[str, Any] | None, result: dict[str, Any]) -> dict[str, Any]:
    if not plan:
        return {
            "g561_plan_row_uid": "",
            "g561_instance_uid": "",
            "g561_evaluation_uid": "",
            "g561_identity_digest": "",
            "g561_scenario_sha256": "",
            "g561_physical_map_sha256": "",
        }
    instance_uid = str(plan.get("g560_instance_uid", ""))
    evaluation_uid = str(plan.get("g560_evaluation_uid", ""))
    physical_hash = str(plan.get("g560_physical_map_sha256", ""))
    scenario_hash = str(result.get("g561_scenario_sha256", result.get("g560_solver_scenario_sha256", "")))
    plan_row_uid = stable_uid("g561_from_g560_plan", plan.get("plan_row_id", ""), plan.get("candidate_id", ""))
    digest = stable_uid(plan_row_uid, instance_uid, evaluation_uid, physical_hash, scenario_hash, plan.get("candidate_id", ""))
    return {
        "g561_plan_row_uid": plan_row_uid,
        "g561_instance_uid": instance_uid,
        "g561_evaluation_uid": evaluation_uid,
        "g561_identity_digest": digest,
        "g561_scenario_sha256": scenario_hash,
        "g561_physical_map_sha256": physical_hash,
    }


def build_indices(plan_rows: list[dict[str, str]], result_rows: list[dict[str, str]], registry_rows: list[dict[str, str]]):
    plan_by_candidate = {row.get("candidate_id", ""): row for row in plan_rows if is_actor_row(row)}
    plan_by_context_candidate = {(context_key(row), row.get("candidate_id", "")): row for row in plan_rows}
    result_by_context_candidate = {(context_key(row), row.get("candidate_id", row.get("materialized_method", ""))): row for row in result_rows}
    registry_by_candidate = {row.get("candidate_id", ""): row for row in registry_rows}
    return plan_by_candidate, plan_by_context_candidate, result_by_context_candidate, registry_by_candidate


def classify_actor_row(
    result: dict[str, str],
    plan: dict[str, str] | None,
    registry: dict[str, str] | None,
    exact_match: bool,
    relaxed_match: bool,
    fingerprint_mismatches: list[str],
) -> str:
    parsed = parse_updateparams_fingerprint(result.get("updateparams_fingerprint", ""))
    force_additive = bool_from_fingerprint(parsed, "force_additive")
    dual_channel = bool_from_fingerprint(parsed, "enable_dual_channel")
    if not plan or not registry:
        return "missing_identity"
    if not result.get("updateparams_fingerprint"):
        return "missing_fingerprint"
    if not parse_bool(result.get("candidate_recognized")):
        if force_additive is True or dual_channel is False:
            return "fallback_additive_executed"
        return "unrecognized_candidate"
    if force_additive is True:
        return "fallback_additive_executed"
    if dual_channel is False:
        return "fallback_additive_executed"
    if parsed.get("goal_projection_mode") and parsed.get("goal_projection_mode") != theta_mode(plan):
        return "wrong_goal_mode"
    if exact_match:
        return "valid_exact_materialization"
    if relaxed_match:
        return "valid_with_numeric_rounding_only"
    if fingerprint_mismatches:
        return "recognized_but_fingerprint_mismatch"
    return "other_invalid"


def audit_rows(plan_rows: list[dict[str, str]], result_rows: list[dict[str, str]], registry_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    plan_by_candidate, _plan_ctx, result_by_ctx_candidate, registry_by_candidate = build_indices(plan_rows, result_rows, registry_rows)
    audits: list[dict[str, Any]] = []
    actor_pairs: list[dict[str, Any]] = []

    baseline_plan_by_eval = {row.get("g560_evaluation_uid", ""): row for row in plan_rows if row.get("candidate_id") == PRIMARY_BASELINE}
    baseline_result_by_eval: dict[str, dict[str, str]] = {}
    for eval_uid, plan in baseline_plan_by_eval.items():
        result = result_by_ctx_candidate.get((context_key(plan), PRIMARY_BASELINE))
        if result:
            baseline_result_by_eval[eval_uid] = result

    for result in result_rows:
        actor = is_actor_row(result)
        plan = plan_by_candidate.get(result.get("candidate_id", "")) if actor else None
        registry = registry_by_candidate.get(result.get("candidate_id", "")) if actor else None
        identity = plan_identity(plan, result)
        parsed = parse_updateparams_fingerprint(result.get("updateparams_fingerprint", ""))
        expected = expected_cpp_params(registry or plan or result) if actor else {}
        plan_registry_match, plan_registry_mismatch = theta_numeric_match(plan or {}, registry or {}) if actor else (True, [])
        exact_match, mismatches = strict_fp_match(result.get("updateparams_fingerprint", ""), registry or plan or result) if actor else (True, [])
        relaxed_match, relaxed_mismatches = relaxed_fp_match(result.get("updateparams_fingerprint", ""), registry or plan or result) if actor else (True, [])
        materialization_class = (
            classify_actor_row(result, plan, registry, exact_match, relaxed_match, mismatches)
            if actor
            else "baseline_control"
        )
        result_has_identity = bool(
            result.get("g561_evaluation_uid")
            or result.get("g560_evaluation_uid")
            or result.get("evaluation_uid")
            or result.get("instance_uid")
        )
        audits.append(
            {
                "source_result_row_id": result.get("g560_direct_actor_row_id", ""),
                "role": result.get("role", ""),
                "candidate_id": result.get("candidate_id", ""),
                "generated_theta_uid": result.get("generated_theta_uid", result.get("candidate_id", "")),
                "actor_row": actor,
                **identity,
                "plan_row_id": plan.get("plan_row_id", "") if plan else "",
                "g560_instance_uid": plan.get("g560_instance_uid", "") if plan else "",
                "g560_evaluation_uid": plan.get("g560_evaluation_uid", "") if plan else "",
                "result_identity_present_before_repair": result_has_identity,
                "candidate_recognized": parse_bool(result.get("candidate_recognized")),
                "fingerprint_parsed": bool(parsed),
                "force_additive": parsed.get("force_additive", ""),
                "enable_dual_channel": parsed.get("enable_dual_channel", ""),
                "goal_projection_mode": parsed.get("goal_projection_mode", ""),
                "plan_registry_match": plan_registry_match,
                "plan_registry_mismatched_fields": ";".join(plan_registry_mismatch),
                "fulltheta_fingerprint_match_strict": exact_match,
                "fulltheta_fingerprint_match_relaxed": relaxed_match,
                "fulltheta_fingerprint_mismatched_fields": ";".join(mismatches or relaxed_mismatches),
                "materialization_class": materialization_class,
                "solver_success": result.get("solution_found", ""),
                "sum_of_loss_ratio": result.get("sum_of_loss_ratio", ""),
                "updateparams_fingerprint": result.get("updateparams_fingerprint", ""),
                "expected_fingerprint_fields": json.dumps(expected, sort_keys=True),
                "phase5p5_allowed": False,
                "phase6_allowed": False,
                "runtime_claim_allowed": False,
                "learned_runtime_policy_validated": False,
                "aaai_ready": False,
            }
        )
        if actor and plan:
            baseline = baseline_result_by_eval.get(plan.get("g560_evaluation_uid", ""))
            if baseline:
                pair = pair_record(result, baseline)
                pair.update(
                    {
                        **identity,
                        "theta_id": result.get("candidate_id", ""),
                        "generated_theta_uid": result.get("generated_theta_uid", result.get("candidate_id", "")),
                        "materialization_class": materialization_class,
                        "candidate_recognized": parse_bool(result.get("candidate_recognized")),
                        "fingerprint_match": exact_match,
                        "force_additive": parsed.get("force_additive", ""),
                        "enable_dual_channel": parsed.get("enable_dual_channel", ""),
                        "goal_projection_mode": parsed.get("goal_projection_mode", ""),
                        "baseline_paired_by_evaluation_uid": True,
                        "result_identity_present_before_repair": result_has_identity,
                    }
                )
                actor_pairs.append(pair)

    class_counts = Counter(row["materialization_class"] for row in audits if row["actor_row"])
    actor_audits = [row for row in audits if row["actor_row"]]
    summary = {
        "schema_version": "phase5p5_repair5g561_g560_replay_truth_audit_summary_v1",
        "decision": "g561_g560_replay_invalid_materialization_not_actor_failure",
        "source_round": SOURCE,
        "round": ROUND,
        "solver_rows": len(result_rows),
        "planned_rows": len(plan_rows),
        "actor_rows": len(actor_audits),
        "baseline_rows": len(audits) - len(actor_audits),
        "recovered_pairs_by_evaluation_uid": len(actor_pairs),
        "materialization_class_counts": dict(sorted(class_counts.items())),
        "candidate_recognized_actor_rows": sum(1 for row in actor_audits if row["candidate_recognized"]),
        "exact_materialization_actor_rows": class_counts.get("valid_exact_materialization", 0),
        "strict_exact_materialization_rate": class_counts.get("valid_exact_materialization", 0) / max(1, len(actor_audits)),
        "unrecognized_actor_rows": class_counts.get("unrecognized_candidate", 0) + class_counts.get("fallback_additive_executed", 0),
        "result_identity_missing_actor_rows": sum(1 for row in actor_audits if not row["result_identity_present_before_repair"]),
        "scenario_sha_missing_actor_rows": sum(1 for row in actor_audits if not row["g561_scenario_sha256"]),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    return audits, actor_pairs, summary


def summarize_pairs(pairs: list[dict[str, Any]], allowed_classes: set[str] | None = None) -> dict[str, Any]:
    kept = [row for row in pairs if allowed_classes is None or row.get("materialization_class") in allowed_classes]
    deltas = [finite_float(row.get("quality_delta_vs_g556")) for row in kept]
    deltas = [value for value in deltas if math.isfinite(value)]
    return {
        "pairs": len(kept),
        "success_regressions": sum(parse_bool(row.get("success_regression")) for row in kept),
        "success_gains": sum(parse_bool(row.get("success_gain")) for row in kept),
        "both_success": sum(parse_bool(row.get("both_success")) for row in kept),
        "both_fail": sum(parse_bool(row.get("both_fail")) for row in kept),
        "mean_quality_delta_vs_g556": sum(deltas) / len(deltas) if deltas else None,
        "better_count": sum(value < 0.0 for value in deltas),
        "worse_count": sum(value > 0.0 for value in deltas),
    }


def regression_truth_rows(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for pair in pairs:
        if not parse_bool(pair.get("success_regression")):
            continue
        out.append(
            {
                "g561_evaluation_uid": pair.get("g561_evaluation_uid", ""),
                "g561_instance_uid": pair.get("g561_instance_uid", ""),
                "generated_theta_uid": pair.get("generated_theta_uid", ""),
                "materialization_class": pair.get("materialization_class", ""),
                "actor_theta_recognized": pair.get("candidate_recognized", ""),
                "actual_fingerprint_match": pair.get("fingerprint_match", ""),
                "force_additive": pair.get("force_additive", ""),
                "enable_dual_channel": pair.get("enable_dual_channel", ""),
                "goal_projection_mode": pair.get("goal_projection_mode", ""),
                "scenario_hash_exact": bool(pair.get("g561_scenario_sha256")),
                "baseline_paired_by_evaluation_uid": pair.get("baseline_paired_by_evaluation_uid", ""),
                "quality_delta_vs_g556": pair.get("quality_delta_vs_g556", ""),
                "success_regression": pair.get("success_regression", ""),
            }
        )
    return out


def write_theta_schema_artifacts() -> None:
    write_json(CANONICAL_SCHEMA_JSON, schema_json())
    rows = []
    lo = {col: float(THETA_LO[idx]) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)}
    hi = {col: float(THETA_HI[idx]) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)}
    baseline = {col: float(BASELINE_G556[idx]) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)}
    for field in schema_rows():
        name = field["name"]
        old_lo, old_hi = OLD_G560_ACTOR_BOUNDS.get(name, (field["lower"], field["upper"]))
        rows.append(
            {
                "theta_field": name,
                "old_actor_lower": old_lo,
                "old_actor_upper": old_hi,
                "canonical_lower": field["lower"],
                "canonical_upper": field["upper"],
                "canonical_baseline": baseline.get(name, field["baseline"]),
                "bounds_changed": old_lo != field["lower"] or old_hi != field["upper"],
                "cpp_parser_name": field["cpp_parser_name"],
                "registry_column_name": field["registry_column_name"],
                "fingerprint_key": field["fingerprint_key"],
                "tolerance": field["tolerance"],
            }
        )
    write_rows(THETA_SCHEMA_DIFF, rows)


def write_contract_artifacts(summary: dict[str, Any]) -> None:
    rows = []
    baseline = {col: float(BASELINE_G556[idx]) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)}
    for idx, col in enumerate(THETA_NUMERIC_COLUMNS):
        low = dict(baseline)
        high = dict(baseline)
        low[col] = float(THETA_LO[idx])
        high[col] = float(THETA_HI[idx])
        rows.append({"contract_vector_id": f"g561_contract_{len(rows):03d}", "vector_family": "field_lower_bound", "changed_field": col, **low, "executed": False, "reason": "planned_for_server_materialization_contract"})
        rows.append({"contract_vector_id": f"g561_contract_{len(rows):03d}", "vector_family": "field_upper_bound", "changed_field": col, **high, "executed": False, "reason": "planned_for_server_materialization_contract"})
    rows.append({"contract_vector_id": f"g561_contract_{len(rows):03d}", "vector_family": "g556_anchor", "changed_field": "all", **baseline, "executed": False, "reason": "planned_for_server_materialization_contract"})
    write_rows(CONTRACT_RESULTS, rows)
    write_json(
        CONTRACT_SUMMARY,
        {
            "schema_version": "phase5p5_repair5g561_materialization_contract_summary_v1",
            "decision": "g561_materialization_contract_planned_server_run_required",
            "planned_contract_vectors": len(rows),
            "executed_contract_vectors": 0,
            "source_truth_audit_decision": summary.get("decision"),
            "candidate_recognized_rate": None,
            "fingerprint_exact_match_rate": None,
            "force_additive_false_rate": None,
            "dual_channel_enabled_rate": None,
            "scenario_hash_match_rate": None,
            "identity_retention_rate": None,
            "phase5p5_allowed": False,
            "phase6_allowed": False,
            "runtime_claim_allowed": False,
            "learned_runtime_policy_validated": False,
            "aaai_ready": False,
        },
    )


def write_report(summary: dict[str, Any], corrected: dict[str, Any], committed: dict[str, Any]) -> None:
    classes = summary.get("materialization_class_counts", {})
    lines = [
        "# Repair5G.5.61 G5.60 Replay Truth Audit",
        "",
        f"Decision: `{summary['decision']}`",
        "",
        "The committed G5.60 replay cannot be read as a clean actor result: generated rows were not all recognized/materialized, and replay identity was not preserved in the result/pair tables.",
        "",
        f"- Solver rows audited: `{summary['solver_rows']}`",
        f"- Actor rows audited: `{summary['actor_rows']}`",
        f"- Exact actor materializations: `{summary['exact_materialization_actor_rows']}`",
        f"- Strict exact materialization rate: `{summary['strict_exact_materialization_rate']:.6f}`",
        f"- Actor rows missing replay identity in raw results: `{summary['result_identity_missing_actor_rows']}`",
        f"- Actor rows missing scenario SHA in raw results: `{summary['scenario_sha_missing_actor_rows']}`",
        "",
        "## Materialization Classes",
        "",
    ]
    lines.extend(f"- {name}: `{count}`" for name, count in sorted(classes.items()))
    lines.extend(
        [
            "",
            "## Recomputed Summaries",
            "",
            f"- Historical committed pairs: `{committed.get('replay_pairs', '')}`, regressions `{committed.get('success_regressions', '')}`, mean delta `{committed.get('mean_quality_delta_vs_g556', '')}`",
            f"- Evaluation-UID recovered pairs: `{corrected['all']['pairs']}`, regressions `{corrected['all']['success_regressions']}`, mean delta `{corrected['all']['mean_quality_delta_vs_g556']}`",
            f"- Recognized rows only: `{corrected['recognized']['pairs']}`, regressions `{corrected['recognized']['success_regressions']}`, mean delta `{corrected['recognized']['mean_quality_delta_vs_g556']}`",
            f"- Exact materialization only: `{corrected['exact']['pairs']}`, regressions `{corrected['exact']['success_regressions']}`, mean delta `{corrected['exact']['mean_quality_delta_vs_g556']}`",
            "",
            "Non-materialized rows are excluded from scientific actor-performance interpretation. All promotion/runtime claims remain closed.",
        ]
    )
    write_text(AUDIT_MD, "\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit G5.60 direct-actor replay materialization truth for G5.61.")
    parser.parse_args(argv)
    plan_rows = read_rows(G560_PLAN)
    result_rows = read_rows(G560_RESULTS)
    registry_rows = read_rows(G560_REGISTRY)
    if not plan_rows or not result_rows or not registry_rows:
        missing = [str(path) for path, rows in [(G560_PLAN, plan_rows), (G560_RESULTS, result_rows), (G560_REGISTRY, registry_rows)] if not rows]
        summary = {"decision": "g561_g560_replay_truth_audit_blocked_missing_inputs", "missing_inputs": missing}
        write_json(AUDIT_JSON, summary)
        print(json.dumps(summary, sort_keys=True))
        return 2
    audits, pairs, summary = audit_rows(plan_rows, result_rows, registry_rows)
    write_rows(ROW_AUDIT, audits)
    write_rows(CORRECTED_PAIRS, pairs)
    regressions = regression_truth_rows(pairs)
    write_rows(REGRESSION_AUDIT, regressions)
    committed = read_json(G560_SUMMARY)
    corrected = {
        "all": summarize_pairs(pairs),
        "recognized": summarize_pairs(pairs, {"valid_exact_materialization", "valid_with_numeric_rounding_only", "recognized_but_fingerprint_mismatch"}),
        "exact": summarize_pairs(pairs, {"valid_exact_materialization"}),
    }
    summary["committed_historical_summary"] = committed
    summary["corrected_replay_summary"] = corrected
    summary["regression_truth_rows"] = len(regressions)
    write_theta_schema_artifacts()
    write_contract_artifacts(summary)
    write_json(AUDIT_JSON, summary)
    write_json(CORRECTED_SUMMARY, {"schema_version": "phase5p5_repair5g561_corrected_g560_replay_summary_v1", **corrected})
    write_report(summary, corrected, committed)
    print(json.dumps({"decision": summary["decision"], "actor_rows": summary["actor_rows"], "exact": summary["exact_materialization_actor_rows"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

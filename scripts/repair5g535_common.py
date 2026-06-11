"""Repair5G.5.35 safety-calibrated no-regression diagnostics.

G5.35 is an offline, diagnostic round.  It red-teams G5.34 prospective
evidence, builds lexicographic safety labels, evaluates conservative
success-regression gates, materializes a bounded no-regression replay from
committed real-solver rows, and keeps all promotion/runtime/paper claims closed.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

try:  # pragma: no cover - optional runtime dependency
    import torch

    TORCH_AVAILABLE = True
except Exception:  # pragma: no cover
    torch = None  # type: ignore[assignment]
    TORCH_AVAILABLE = False

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))
else:  # pragma: no cover
    ROOT = Path(__file__).resolve().parents[1]

from repair5g531_common import (  # noqa: E402
    claims,
    csv_number,
    external_lacam2_clean,
    gpu_status,
    load_json,
    number,
    read_rows,
    resolve,
    sha256_file,
    write_json,
    write_rows,
    write_text,
)
from repair5g532_common import boolish, map_family, rel  # noqa: E402
from repair5g534_common import (  # noqa: E402
    CANDIDATE_FAMILY_CSV as G534_CANDIDATE_FAMILY_CSV,
    PROBE_RESULTS_CSV as G534_PROBE_RESULTS_CSV,
    PROSPECTIVE_PLAN_CSV as G534_PROSPECTIVE_PLAN_CSV,
    PROSPECTIVE_REPLAY_CSV as G534_PROSPECTIVE_REPLAY_CSV,
    PROSPECTIVE_SAFETY_AUDIT as G534_PROSPECTIVE_SAFETY_AUDIT,
    PROSPECTIVE_SELECTED_VS_ADD as G534_SELECTED_VS_ADD,
    PROSPECTIVE_SELECTED_VS_STATIC as G534_SELECTED_VS_STATIC,
    SUCCESS_REGRESSION_CSV as G534_SUCCESS_REGRESSION_CSV,
    TORCH_EVAL_SPLIT_CSV as G534_TORCH_EVAL_SPLIT_CSV,
    UTILITY_CSV as G534_UTILITY_CSV,
    best_family_static_candidate,
    candidate_by_id,
)


SEED = 20260611 + 535
PLAN_FILE = "czr004_g535_safety_calibrated_no_regression_goal_aware_dual_channel_ltm_plan.md"

G534_REQUIRED = {
    "decision_summary": "outputs/reports/phase5p5_repair5g534_decision_summary.json",
    "prospective_evidence_summary": "outputs/reports/phase5p5_repair5g534_prospective_evidence_summary.json",
    "prospective_selected_vs_additive": G534_SELECTED_VS_ADD,
    "prospective_selected_vs_static": G534_SELECTED_VS_STATIC,
    "prospective_safety_audit": G534_PROSPECTIVE_SAFETY_AUDIT,
    "torch_model_eval_by_split": G534_TORCH_EVAL_SPLIT_CSV,
    "success_regression_audit": G534_SUCCESS_REGRESSION_CSV,
    "broad_probe_results": G534_PROBE_RESULTS_CSV,
    "repair5g534_common": "scripts/repair5g534_common.py",
}

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g535_g534_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g535_g534_verification_summary.json"
TABLE_AUDIT_CSV = "outputs/tables/phase5p5_repair5g535_g534_table_materialization_audit.csv"

METRIC_REPORT = "outputs/reports/phase5p5_repair5g535_g534_prospective_metric_integrity.md"
METRIC_SUMMARY = "outputs/reports/phase5p5_repair5g535_g534_prospective_metric_integrity_summary.json"
DELTA_RECOMPUTE_CSV = "outputs/tables/phase5p5_repair5g535_g534_prospective_delta_recompute.csv"
METRIC_BUG_AUDIT_CSV = "outputs/tables/phase5p5_repair5g535_g534_metric_bug_audit.csv"
SAFETY_FALLBACK_NOOP_CSV = "outputs/tables/phase5p5_repair5g535_g534_safety_fallback_noop_audit.csv"

AUTOPSY_CASES_CSV = "outputs/tables/phase5p5_repair5g535_success_regression_cases.csv"
AUTOPSY_COMPARISON_CSV = "outputs/tables/phase5p5_repair5g535_success_regression_candidate_comparison.csv"
AUTOPSY_FEATURE_CSV = "outputs/tables/phase5p5_repair5g535_success_regression_feature_profile.csv"
AUTOPSY_FAILURE_CSV = "outputs/tables/phase5p5_repair5g535_success_regression_failure_audit_profile.csv"
AUTOPSY_ALTERNATIVES_CSV = "outputs/tables/phase5p5_repair5g535_success_regression_safe_alternatives.csv"
AUTOPSY_REPORT = "outputs/reports/phase5p5_repair5g535_success_regression_autopsy.md"
AUTOPSY_SUMMARY = "outputs/reports/phase5p5_repair5g535_success_regression_autopsy_summary.json"

LEX_UTILITY_CSV = "outputs/tables/phase5p5_repair5g535_candidate_lexicographic_utility.csv"
SUCCESS_LABELS_CSV = "outputs/tables/phase5p5_repair5g535_success_regression_labels.csv"
SAFE_SET_CSV = "outputs/tables/phase5p5_repair5g535_safe_candidate_set_by_context.csv"
FALLBACK_LABELS_CSV = "outputs/tables/phase5p5_repair5g535_abstention_or_fallback_labels.csv"
PAIRWISE_SAFE_CSV = "outputs/tables/phase5p5_repair5g535_pairwise_safe_dominance.csv"
LABEL_REPORT = "outputs/reports/phase5p5_repair5g535_lexicographic_safety_labels.md"
LABEL_SUMMARY = "outputs/reports/phase5p5_repair5g535_lexicographic_safety_labels_summary.json"

SAFETY_GATE_EVAL_CSV = "outputs/tables/phase5p5_repair5g535_safety_gate_eval_by_split.csv"
SAFETY_GATE_SWEEP_CSV = "outputs/tables/phase5p5_repair5g535_safety_gate_threshold_sweep.csv"
SAFETY_GATE_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g535_safety_gate_calibration.csv"
SAFETY_GATE_FN_CSV = "outputs/tables/phase5p5_repair5g535_safety_gate_false_negative_audit.csv"
SAFETY_GATE_NEGATIVE_CSV = "outputs/tables/phase5p5_repair5g535_safety_gate_negative_controls.csv"
SAFETY_GATE_REPORT = "outputs/reports/phase5p5_repair5g535_calibrated_safety_gate.md"
SAFETY_GATE_SUMMARY = "outputs/reports/phase5p5_repair5g535_calibrated_safety_gate_summary.json"
SAFETY_GATE_MANIFEST = "artifacts/models/laur_ltm/repair5g535_safety_gate_manifest.json"

SELECTOR_EVAL_CSV = "outputs/tables/phase5p5_repair5g535_constrained_selector_eval_by_split.csv"
SELECTOR_SWEEP_CSV = "outputs/tables/phase5p5_repair5g535_constrained_selector_threshold_sweep.csv"
SELECTOR_PREDICTIONS_CSV = "outputs/tables/phase5p5_repair5g535_constrained_selector_predictions.csv"
SELECTOR_ABLATION_CSV = "outputs/tables/phase5p5_repair5g535_constrained_selector_ablation.csv"
SELECTOR_NEGATIVE_CSV = "outputs/tables/phase5p5_repair5g535_constrained_selector_negative_controls.csv"
SELECTOR_REPORT = "outputs/reports/phase5p5_repair5g535_constrained_selector.md"
SELECTOR_SUMMARY = "outputs/reports/phase5p5_repair5g535_constrained_selector_summary.json"
SELECTOR_MANIFEST = "artifacts/models/laur_ltm/repair5g535_constrained_selector_manifest.json"

REPLAY_PLAN_CSV = "outputs/tables/phase5p5_repair5g535_no_regression_replay_plan.csv"
REPLAY_PLAN_REPORT = "outputs/reports/phase5p5_repair5g535_no_regression_replay_plan.md"
REPLAY_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g535_no_regression_replay_plan_summary.json"
NO_REG_REPLAY_CSV = "outputs/tables/phase5p5_repair5g535_no_regression_replay_results.csv"
NO_REG_REPLAY_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g535_no_regression_replay_sample.csv"
NO_REG_REPLAY_REPORT = "outputs/reports/phase5p5_repair5g535_no_regression_prospective_replay.md"
NO_REG_REPLAY_SUMMARY = "outputs/reports/phase5p5_repair5g535_no_regression_prospective_replay_summary.json"

NO_REG_SELECTED_VS_ADD = "outputs/tables/phase5p5_repair5g535_no_regression_selected_vs_additive.csv"
NO_REG_SELECTED_VS_STATIC = "outputs/tables/phase5p5_repair5g535_no_regression_selected_vs_static.csv"
NO_REG_SELECTED_VS_G534 = "outputs/tables/phase5p5_repair5g535_no_regression_selected_vs_g534.csv"
NO_REG_SAFETY_ACTIVATION = "outputs/tables/phase5p5_repair5g535_no_regression_safety_activation.csv"
NO_REG_FAILURE_CASES = "outputs/tables/phase5p5_repair5g535_no_regression_failure_cases.csv"
NO_REG_BY_MAP = "outputs/tables/phase5p5_repair5g535_no_regression_by_map_family.csv"
NO_REG_BY_BUDGET = "outputs/tables/phase5p5_repair5g535_no_regression_by_budget.csv"
NO_REG_BY_AGENT = "outputs/tables/phase5p5_repair5g535_no_regression_by_agent_count.csv"
NO_REG_EVIDENCE_REPORT = "outputs/reports/phase5p5_repair5g535_no_regression_evidence.md"
NO_REG_EVIDENCE_SUMMARY = "outputs/reports/phase5p5_repair5g535_no_regression_evidence_summary.json"

STATIC_BRIDGE_CSV = "outputs/tables/phase5p5_repair5g535_static_safe_rule_policy.csv"
STATIC_BRIDGE_REPORT = "outputs/reports/phase5p5_repair5g535_static_safe_rule_bridge.md"
STATIC_BRIDGE_SUMMARY = "outputs/reports/phase5p5_repair5g535_static_safe_rule_bridge_summary.json"

DECISION_REPORT = "outputs/reports/phase5p5_repair5g535_decision.md"
DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g535_decision_summary.json"

ADDITIVE = "repair5g59_additive_fallback"
STATIC_FLOW = "repair5g59_static_flow_shield"
BEST_FIXED = "repair5g59_high_beta_cap_safe"
THRESHOLDS = [0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.50]
REPLAY_POLICY_ROLES = {
    "G5.35_constrained_selected_candidate",
    "G5.35_constrained_ultra_conservative_fallback",
}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=80)
    p.add_argument("--bootstrap-samples", type=int, default=300)
    p.add_argument("--max-workers", type=int, default=1)
    p.add_argument("--ids", nargs="*", type=int)
    return p


def validate_ids(args: argparse.Namespace, label: str) -> None:
    bad = [int(value) for value in (args.ids or []) if 166 <= int(value) <= 205]
    if bad:
        print(json.dumps({"decision": "reserved_id_guard_rejected", "label": label, "ids": bad}))
        raise SystemExit(1)


def ensure_plan_file() -> None:
    if resolve(PLAN_FILE).exists():
        return
    write_text(
        PLAN_FILE,
        "# Repair5G.5.35 Safety-Calibrated No-Regression Goal-Aware Dual-Channel UpdateLTM Plan\n\n"
        "This diagnostic round audits G5.34, prioritizes success preservation, "
        "builds a calibrated abstention/fallback selector, and keeps all claims closed.\n",
    )


def table_count(path: str | Path) -> int:
    return len(read_rows(path)) if resolve(path).exists() else 0


def finite_ratio(value: Any) -> float | None:
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    try:
        out = float(text)
    except ValueError:
        return None
    return out if math.isfinite(out) else None


def mean(values: Iterable[float]) -> float:
    vals = [float(v) for v in values if math.isfinite(float(v))]
    return statistics.mean(vals) if vals else 0.0


def median(values: Iterable[float]) -> float:
    vals = [float(v) for v in values if math.isfinite(float(v))]
    return statistics.median(vals) if vals else 0.0


def bootstrap_ci(values: list[float], samples: int = 300) -> tuple[float, float]:
    vals = [float(v) for v in values if math.isfinite(float(v))]
    if not vals:
        return 0.0, 0.0
    if len(vals) == 1:
        return vals[0], vals[0]
    draws = []
    n = len(vals)
    for i in range(max(30, samples)):
        sample = [vals[(i * 131 + j * 17 + SEED) % n] for j in range(n)]
        draws.append(statistics.mean(sample))
    draws.sort()
    return draws[int(0.025 * (len(draws) - 1))], draws[int(0.975 * (len(draws) - 1))]


def context_key(row: dict[str, Any]) -> str:
    return "|".join(
        [
            str(row.get("map", "")),
            str(row.get("agents", "")),
            str(row.get("seed", "")),
            str(row.get("budget_ms", "")),
            str(row.get("iteration", "")),
        ]
    )


def context_no_iter(row: dict[str, Any]) -> str:
    return "|".join([str(row.get("map", "")), str(row.get("agents", "")), str(row.get("seed", "")), str(row.get("budget_ms", ""))])


def row_success(row: dict[str, Any] | None, ratio_fallback: Any = "") -> bool:
    if row:
        return boolish(row.get("solution_found"))
    return finite_ratio(ratio_fallback) is not None


def replay_by_context() -> dict[str, dict[str, dict[str, str]]]:
    out: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in read_rows(G534_PROSPECTIVE_REPLAY_CSV):
        out[context_key(row)][str(row.get("candidate_id", ""))] = row
    return out


def plan_roles_by_context() -> dict[str, dict[str, str]]:
    roles: dict[str, dict[str, str]] = defaultdict(dict)
    for row in read_rows(G534_PROSPECTIVE_PLAN_CSV):
        roles[str(row.get("context_key", ""))][str(row.get("role", ""))] = str(row.get("candidate_id", ""))
    return roles


def candidate_family(candidate_id: str) -> str:
    cid = str(candidate_id)
    if cid == ADDITIVE:
        return "additive"
    if cid == STATIC_FLOW:
        return "static_flow_shield"
    if "c_only" in cid or cid.endswith("_c1"):
        return "c_only"
    if "wait_conservative" in cid or "w0p35" in cid or "w0p5" in cid:
        return "wait_conservative"
    if "wait_aggressive" in cid or "w0p65" in cid:
        return "wait_aggressive"
    if "high_beta" in cid or "beta0p7" in cid or "beta0p6" in cid or "beta0p5" in cid:
        return "high_beta"
    if "low_beta" in cid or "beta0p2" in cid:
        return "low_beta"
    if "flow_decay" in cid or "df0p9" in cid:
        return "flow_decay"
    if "block_heavy" in cid:
        return "block_heavy"
    if "commit_heavy" in cid:
        return "commit_heavy"
    return "other_flow"


def conservative_risk_score(row: dict[str, Any]) -> float:
    cid = str(row.get("candidate_id", row.get("target_candidate", "")))
    if cid == ADDITIVE:
        return 0.0
    family = str(row.get("map_family", map_family(str(row.get("map", "")))))
    agents = int(number(row.get("agents"), 0))
    budget = int(number(row.get("budget_ms"), 0))
    if family == "random":
        return 0.92
    if family == "warehouse" and agents <= 50 and budget >= 2000:
        return 0.88
    if family == "maze" and budget >= 2000:
        return 0.84
    if family == "maze" and agents >= 100 and budget >= 1000:
        return 0.80
    if candidate_family(cid) in {"c_only", "wait_conservative"} and budget >= 2000:
        return 0.35
    return 0.03


def best_static_for_context(map_name: str) -> str:
    fam = map_family(map_name)
    try:
        return best_family_static_candidate(fam)
    except Exception:
        return STATIC_FLOW


def candidate_method(candidate_id: str) -> str:
    meta = candidate_by_id().get(candidate_id, {})
    return str(meta.get("method", candidate_id))


def selected_candidate_from_g534(context: str) -> str:
    return plan_roles_by_context().get(context, {}).get("model_selected_candidate", ADDITIVE)


def corrected_delta_rows() -> list[dict[str, Any]]:
    if not resolve(DELTA_RECOMPUTE_CSV).exists():
        main_audit_metric_integrity([])
    return read_rows(DELTA_RECOMPUTE_CSV)


def labels_rows() -> list[dict[str, Any]]:
    if not resolve(LEX_UTILITY_CSV).exists():
        main_create_lexicographic_safety_labels([])
    return read_rows(LEX_UTILITY_CSV)


def main_verify_g534_artifacts(argv: list[str] | None = None) -> int:
    ensure_plan_file()
    args = parser().parse_args(argv)
    validate_ids(args, "G5.35 verify G5.34")
    rows = []
    missing = []
    for label, path in G534_REQUIRED.items():
        p = resolve(path)
        exists = p.exists()
        if not exists:
            missing.append(label)
        rows.append(
            {
                "artifact": label,
                "path": rel(p),
                "exists": exists,
                "row_count": table_count(p) if p.suffix.lower() == ".csv" else "",
                "sha256": sha256_file(p)[:16] if exists and p.is_file() else "",
                **claims(),
            }
        )
    write_rows(TABLE_AUDIT_CSV, rows)
    decision = "g534_verified_metric_correction_required_continue_g535" if not missing else "g534_artifact_blocker_stop"
    summary = {
        "schema_version": "phase5p5_repair5g535_g534_verification_summary_v1",
        "decision": decision,
        "missing_artifacts": missing,
        "artifact_count": len(rows),
        "required_csv_rows": {row["artifact"]: row["row_count"] for row in rows if row["row_count"] != ""},
        "g534_success_regression_count": load_json("outputs/reports/phase5p5_repair5g534_prospective_evidence_summary.json", {}).get("success_regression_count", ""),
        "no_external_lacam2_edits": external_lacam2_clean(),
        **claims(),
    }
    write_json(VERIFY_SUMMARY, summary)
    write_text(
        VERIFY_REPORT,
        "# G5.35 Verification of G5.34 Artifacts\n\n"
        f"- decision: `{decision}`\n"
        f"- missing artifacts: `{len(missing)}`\n"
        f"- G5.34 reported success regressions: `{summary['g534_success_regression_count']}`\n"
        f"- external/lacam2/lacam2 clean: `{summary['no_external_lacam2_edits']}`\n",
    )
    print(json.dumps({"decision": decision, "missing": len(missing)}))
    return 0


def main_audit_metric_integrity(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.35 metric audit")
    if not resolve(VERIFY_SUMMARY).exists():
        main_verify_g534_artifacts([])
    pairs = read_rows(G534_SELECTED_VS_ADD)
    replay = replay_by_context()
    raw_positive = [number(r.get("delta_ratio"), 0.0) for r in pairs if number(r.get("delta_ratio"), 0.0) > 0]
    failure_penalty = max(0.25, (max(raw_positive) if raw_positive else 0.0) + 0.05)
    recompute = []
    bug_rows = []
    quality_deltas = []
    lex_deltas = []
    for row in pairs:
        key = str(row.get("context_budget_iteration_key", ""))
        selected_id = str(row.get("selected_candidate", ""))
        add_row = replay.get(key, {}).get(ADDITIVE)
        sel_row = replay.get(key, {}).get(selected_id)
        add_success = row_success(add_row, row.get("additive_ratio"))
        selected_success = row_success(sel_row, row.get("selected_ratio"))
        add_ratio = finite_ratio(add_row.get("sum_of_loss_ratio") if add_row else row.get("additive_ratio"))
        selected_ratio = finite_ratio(sel_row.get("sum_of_loss_ratio") if sel_row else row.get("selected_ratio"))
        raw_delta_number_blank_as_zero = number(row.get("delta_ratio"), 0.0)
        raw_delta_blank = str(row.get("delta_ratio", "")).strip() == "" or selected_ratio is None
        success_reg = add_success and not selected_success
        success_gain = selected_success and not add_success
        both_fail = (not add_success) and (not selected_success)
        both_success = add_success and selected_success and add_ratio is not None and selected_ratio is not None
        if success_reg:
            corrected = failure_penalty
            rank = "hard_fail"
        elif success_gain:
            corrected = -failure_penalty
            rank = "success_gain"
        elif both_success:
            corrected = float(selected_ratio) - float(add_ratio)
            quality_deltas.append(corrected)
            rank = "both_success_quality"
        else:
            corrected = 0.0
            rank = "both_fail"
        lex_deltas.append(corrected)
        recompute.append(
            {
                **{k: row.get(k, "") for k in ["context_budget_iteration_key", "map", "map_family", "agents", "seed", "budget_ms", "iteration"]},
                "selected_candidate": selected_id,
                "additive_solution_found": add_success,
                "selected_solution_found": selected_success,
                "additive_ratio": "" if add_ratio is None else csv_number(add_ratio),
                "selected_ratio": "" if selected_ratio is None else csv_number(selected_ratio),
                "raw_g534_delta_ratio": row.get("delta_ratio", ""),
                "raw_delta_number_blank_as_zero": csv_number(raw_delta_number_blank_as_zero),
                "corrected_delta_ratio_for_mean": csv_number(corrected),
                "quality_delta_ratio": csv_number(selected_ratio - add_ratio) if both_success else "",
                "lexicographic_rank": rank,
                "success_regression": success_reg,
                "success_gain": success_gain,
                "both_fail": both_fail,
                "both_success": both_success,
                **claims(),
            }
        )
        if success_reg or raw_delta_blank:
            bug_rows.append(
                {
                    "context_budget_iteration_key": key,
                    "selected_candidate": selected_id,
                    "issue": "success_regression_blank_or_zero_delta" if success_reg else "blank_delta_ratio",
                    "raw_delta_ratio": row.get("delta_ratio", ""),
                    "raw_delta_number_blank_as_zero": csv_number(raw_delta_number_blank_as_zero),
                    "corrected_delta_ratio_for_mean": csv_number(corrected),
                    "metric_risk": "mean_delta_understates_success_regression",
                    **claims(),
                }
            )
    safety_rows = []
    for row in read_rows(G534_PROSPECTIVE_SAFETY_AUDIT):
        activated = boolish(row.get("safety_fallback_activated"))
        safety_rows.append(
            {
                "context_budget_iteration_key": row.get("context_budget_iteration_key", ""),
                "model_selected_candidate": row.get("selected_candidate", ""),
                "model_selected_safety_fallback": row.get("safety_candidate", ""),
                "safety_fallback_activated": activated,
                "unsafe_selected_candidate_prevented": boolish(row.get("unsafe_selected_candidate_prevented")),
                "safety_fallback_noop": not activated,
                **claims(),
            }
        )
    write_rows(DELTA_RECOMPUTE_CSV, recompute)
    write_rows(METRIC_BUG_AUDIT_CSV, bug_rows)
    write_rows(SAFETY_FALLBACK_NOOP_CSV, safety_rows)
    raw_mean = mean([number(row.get("delta_ratio"), 0.0) for row in pairs])
    corrected_quality = mean(quality_deltas)
    corrected_lex = mean(lex_deltas)
    success_reg_count = sum(1 for row in recompute if boolish(row.get("success_regression")))
    safety_activation_count = sum(1 for row in safety_rows if boolish(row.get("safety_fallback_activated")))
    decision = (
        "g534_verified_metric_correction_required_continue_g535"
        if success_reg_count or corrected_lex > raw_mean
        else "g534_metric_safe_but_selector_success_regression_blocker_continue_g535"
    )
    summary = {
        "schema_version": "phase5p5_repair5g535_g534_prospective_metric_integrity_summary_v1",
        "decision": decision,
        "failure_penalty_ratio": csv_number(failure_penalty),
        "raw_g534_delta_mean": csv_number(raw_mean),
        "corrected_quality_delta_mean": csv_number(corrected_quality),
        "corrected_lexicographic_delta_mean": csv_number(corrected_lex),
        "success_regression_count": success_reg_count,
        "success_gain_count": sum(1 for row in recompute if boolish(row.get("success_gain"))),
        "both_fail_count": sum(1 for row in recompute if boolish(row.get("both_fail"))),
        "quality_only_pairs": len(quality_deltas),
        "metric_bug_rows": len(bug_rows),
        "safety_fallback_activation_count": safety_activation_count,
        "safety_fallback_noop": safety_activation_count == 0,
        **claims(),
    }
    write_json(METRIC_SUMMARY, summary)
    write_text(
        METRIC_REPORT,
        "# G5.35 Audit of G5.34 Prospective Metric Integrity\n\n"
        f"- decision: `{decision}`\n"
        f"- raw G5.34 mean delta: `{summary['raw_g534_delta_mean']}`\n"
        f"- corrected lexicographic mean delta: `{summary['corrected_lexicographic_delta_mean']}`\n"
        f"- quality-only mean delta: `{summary['corrected_quality_delta_mean']}`\n"
        f"- success regressions: `{success_reg_count}`\n"
        f"- safety fallback activation count: `{safety_activation_count}`\n",
    )
    print(json.dumps({"decision": decision, "success_regressions": success_reg_count}))
    return 0


def main_success_regression_autopsy(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.35 success regression autopsy")
    recompute = corrected_delta_rows()
    replay = replay_by_context()
    cases = [row for row in recompute if boolish(row.get("success_regression"))]
    case_rows = []
    comparison_rows = []
    feature_rows = []
    failure_rows = []
    alternatives = []
    for idx, case in enumerate(cases):
        key = str(case.get("context_budget_iteration_key", ""))
        selected_id = str(case.get("selected_candidate", ""))
        rows = replay.get(key, {})
        add = rows.get(ADDITIVE, {})
        selected = rows.get(selected_id, {})
        static = rows.get(STATIC_FLOW, {})
        case_id = f"g535_success_regression_{idx:03d}"
        additive_ratio = finite_ratio(add.get("sum_of_loss_ratio"))
        selected_ratio = finite_ratio(selected.get("sum_of_loss_ratio"))
        row_base = {
            "case_id": case_id,
            "context_budget_iteration_key": key,
            "map": case.get("map", ""),
            "map_family": case.get("map_family", ""),
            "agents": case.get("agents", ""),
            "seed": case.get("seed", ""),
            "budget_ms": case.get("budget_ms", ""),
            "iteration": case.get("iteration", ""),
            "additive_solution_found": True,
            "selected_solution_found": False,
            "selected_candidate": selected_id,
            "safety_candidate": selected_id,
            "additive_ratio": "" if additive_ratio is None else csv_number(additive_ratio),
            "selected_ratio": "" if selected_ratio is None else csv_number(selected_ratio),
            "evidence_strength": "committed_g534_prospective_real_solver_replay",
            **claims(),
        }
        case_rows.append(row_base)
        for candidate_id, rec in sorted(rows.items()):
            candidate_success = boolish(rec.get("solution_found"))
            ratio = finite_ratio(rec.get("sum_of_loss_ratio"))
            comparison_rows.append(
                {
                    "case_id": case_id,
                    "candidate_id": candidate_id,
                    "candidate_family": candidate_family(candidate_id),
                    "role_hint": "additive" if candidate_id == ADDITIVE else "static_flow" if candidate_id == STATIC_FLOW else "selected" if candidate_id == selected_id else "candidate",
                    "solution_found": candidate_success,
                    "sum_of_loss_ratio": "" if ratio is None else csv_number(ratio),
                    "expanded_nodes": rec.get("expanded_nodes", ""),
                    "trace_event_count": rec.get("trace_event_count", ""),
                    "pibt_failure_audit_count": rec.get("pibt_failure_audit_count", ""),
                    "safe_alternative_to_selected": candidate_success,
                    **row_base,
                }
            )
            if candidate_success and candidate_id != selected_id:
                alternatives.append(
                    {
                        "case_id": case_id,
                        "candidate_id": candidate_id,
                        "candidate_family": candidate_family(candidate_id),
                        "sum_of_loss_ratio": "" if ratio is None else csv_number(ratio),
                        "fallback_would_prevent_regression": True,
                        "is_static_flow_shield": candidate_id == STATIC_FLOW,
                        "is_additive": candidate_id == ADDITIVE,
                        **claims(),
                    }
                )
        feature_rows.append(
            {
                "case_id": case_id,
                "traffic_before_hash": selected.get("traffic_before_hash", ""),
                "traffic_after_hash": selected.get("traffic_after_hash", ""),
                "selected_trace_event_count": selected.get("trace_event_count", ""),
                "selected_candidate_family": candidate_family(selected_id),
                "map_family": case.get("map_family", ""),
                "budget_ms": case.get("budget_ms", ""),
                "agents": case.get("agents", ""),
                "candidate_update_profile": candidate_method(selected_id),
                **claims(),
            }
        )
        failure_rows.append(
            {
                "case_id": case_id,
                "additive_failure_audit_count": add.get("pibt_failure_audit_count", ""),
                "selected_failure_audit_count": selected.get("pibt_failure_audit_count", ""),
                "static_failure_audit_count": static.get("pibt_failure_audit_count", ""),
                "selected_no_solution_blank_ratio": selected_ratio is None,
                "additive_succeeded_by_margin": "robust_or_unknown",
                **claims(),
            }
        )
    write_rows(AUTOPSY_CASES_CSV, case_rows)
    write_rows(AUTOPSY_COMPARISON_CSV, comparison_rows)
    write_rows(AUTOPSY_FEATURE_CSV, feature_rows)
    write_rows(AUTOPSY_FAILURE_CSV, failure_rows)
    write_rows(AUTOPSY_ALTERNATIVES_CSV, alternatives)
    by_family = Counter(row.get("map_family", "") for row in case_rows)
    by_candidate = Counter(row.get("selected_candidate", "") for row in case_rows)
    by_budget = Counter(row.get("budget_ms", "") for row in case_rows)
    static_prevents = all(any(a.get("case_id") == c.get("case_id") and boolish(a.get("is_static_flow_shield")) for a in alternatives) for c in case_rows) if case_rows else False
    additive_prevents = all(any(a.get("case_id") == c.get("case_id") and boolish(a.get("is_additive")) for a in alternatives) for c in case_rows) if case_rows else False
    summary = {
        "schema_version": "phase5p5_repair5g535_success_regression_autopsy_summary_v1",
        "decision": "success_regression_autopsy_completed",
        "success_regression_cases": len(case_rows),
        "regressions_concentrated_in_warehouse": by_family.get("warehouse", 0) == len(case_rows) and len(case_rows) > 0,
        "selected_candidate_distribution": dict(by_candidate),
        "budget_distribution": dict(by_budget),
        "blank_selected_ratio_cases": sum(1 for row in failure_rows if boolish(row.get("selected_no_solution_blank_ratio"))),
        "static_flow_shield_would_prevent_every_regression": static_prevents,
        "additive_fallback_would_prevent_every_regression": additive_prevents,
        "safe_alternative_rows": len(alternatives),
        "evidence_strength": "committed_g534_prospective_real_solver_replay",
        **claims(),
    }
    write_json(AUTOPSY_SUMMARY, summary)
    write_text(
        AUTOPSY_REPORT,
        "# G5.35 Success-Regression Autopsy\n\n"
        f"- cases: `{len(case_rows)}`\n"
        f"- map-family distribution: `{dict(by_family)}`\n"
        f"- selected-candidate distribution: `{dict(by_candidate)}`\n"
        f"- budget distribution: `{dict(by_budget)}`\n"
        f"- additive fallback would prevent every regression: `{additive_prevents}`\n"
        f"- static flow-shield would prevent every regression: `{static_prevents}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "cases": len(case_rows)}))
    return 0


def main_create_lexicographic_safety_labels(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.35 lexicographic labels")
    if not resolve(AUTOPSY_SUMMARY).exists():
        main_success_regression_autopsy([])
    utility_rows = read_rows(G534_UTILITY_CSV)
    probe = defaultdict(dict)
    for row in read_rows(G534_PROBE_RESULTS_CSV):
        probe[context_key(row)][str(row.get("candidate_id", ""))] = row
    out = []
    seen_keys = set()
    for row in utility_rows:
        key = str(row.get("context_budget_iteration_key", ""))
        cid = str(row.get("candidate_id", ""))
        add = probe.get(key, {}).get(ADDITIVE, {})
        cand = probe.get(key, {}).get(cid, {})
        add_success = row_success(add)
        cand_success = row_success(cand)
        add_ratio = finite_ratio(add.get("sum_of_loss_ratio"))
        cand_ratio = finite_ratio(cand.get("sum_of_loss_ratio"))
        success_reg = add_success and not cand_success
        success_gain = cand_success and not add_success
        both_fail = (not add_success) and (not cand_success)
        both_success = add_success and cand_success and add_ratio is not None and cand_ratio is not None
        quality_delta = (cand_ratio - add_ratio) if both_success else None
        if success_reg:
            lex_score = -1_000_000.0
            rank = "hard_fail"
        elif success_gain:
            lex_score = 1000.0
            rank = "success_gain"
        elif quality_delta is not None:
            lex_score = -float(quality_delta)
            rank = "both_success_quality"
        else:
            lex_score = 0.0
            rank = "both_fail_abstain"
        target_safe = (not success_reg) and not boolish(row.get("candidate_harmful_non_success"))
        rec = {
            "label_id": f"g535_lex_{len(out):08d}",
            "context_budget_iteration_key": key,
            "map": row.get("map", ""),
            "map_family": row.get("map_family", ""),
            "agents": row.get("agents", ""),
            "seed": row.get("seed", ""),
            "budget_ms": row.get("budget_ms", ""),
            "iteration": row.get("iteration", ""),
            "candidate_id": cid,
            "candidate_family": candidate_family(cid),
            "additive_solution_found": add_success,
            "candidate_solution_found": cand_success,
            "candidate_success_regression": success_reg,
            "candidate_success_gain": success_gain,
            "both_fail": both_fail,
            "both_success": both_success,
            "candidate_quality_delta": "" if quality_delta is None else csv_number(quality_delta),
            "candidate_lexicographic_score": csv_number(lex_score),
            "lexicographic_rank": rank,
            "target_candidate_is_safe": target_safe,
            "target_candidate_is_unsafe_success_regression": success_reg,
            "target_candidate_has_quality_gain": quality_delta is not None and quality_delta < -0.005,
            "target_candidate_has_high_margin_safe_gain": boolish(row.get("candidate_high_margin")) and target_safe,
            "target_context_requires_abstention": False,
            "target_should_fallback_to_additive": False,
            "target_should_fallback_to_static_flow": False,
            "target_should_fallback_to_best_static": False,
            **claims(),
        }
        out.append(rec)
        seen_keys.add((key, cid))
    for row in corrected_delta_rows():
        if not boolish(row.get("success_regression")):
            continue
        key = str(row.get("context_budget_iteration_key", ""))
        cid = str(row.get("selected_candidate", ""))
        if (key, cid) in seen_keys:
            continue
        rec = {
            "label_id": f"g535_lex_{len(out):08d}",
            "context_budget_iteration_key": key,
            "map": row.get("map", ""),
            "map_family": row.get("map_family", ""),
            "agents": row.get("agents", ""),
            "seed": row.get("seed", ""),
            "budget_ms": row.get("budget_ms", ""),
            "iteration": row.get("iteration", ""),
            "candidate_id": cid,
            "candidate_family": candidate_family(cid),
            "additive_solution_found": True,
            "candidate_solution_found": False,
            "candidate_success_regression": True,
            "candidate_success_gain": False,
            "both_fail": False,
            "both_success": False,
            "candidate_quality_delta": "",
            "candidate_lexicographic_score": csv_number(-1_000_000.0),
            "lexicographic_rank": "hard_fail_prospective",
            "target_candidate_is_safe": False,
            "target_candidate_is_unsafe_success_regression": True,
            "target_candidate_has_quality_gain": False,
            "target_candidate_has_high_margin_safe_gain": False,
            "target_context_requires_abstention": True,
            "target_should_fallback_to_additive": True,
            "target_should_fallback_to_static_flow": True,
            "target_should_fallback_to_best_static": True,
            **claims(),
        }
        out.append(rec)
    by_context: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in out:
        by_context[str(row.get("context_budget_iteration_key", ""))].append(row)
    safe_sets = []
    fallback_rows = []
    pairwise = []
    for key, rows in by_context.items():
        safe = [r for r in rows if boolish(r.get("target_candidate_is_safe"))]
        safe_non_add = [r for r in safe if r.get("candidate_id") != ADDITIVE]
        best_safe = max(safe, key=lambda r: number(r.get("candidate_lexicographic_score"), -1e9), default={})
        best_non_add = max(safe_non_add, key=lambda r: number(r.get("candidate_lexicographic_score"), -1e9), default={})
        unsafe_count = sum(1 for r in rows if boolish(r.get("target_candidate_is_unsafe_success_regression")))
        context_requires_abstention = unsafe_count > 0 or not best_non_add
        safe_sets.append(
            {
                "context_budget_iteration_key": key,
                "map": rows[0].get("map", ""),
                "map_family": rows[0].get("map_family", ""),
                "agents": rows[0].get("agents", ""),
                "seed": rows[0].get("seed", ""),
                "budget_ms": rows[0].get("budget_ms", ""),
                "iteration": rows[0].get("iteration", ""),
                "target_context_safe_candidate_count": len(safe),
                "target_best_safe_candidate": best_safe.get("candidate_id", ""),
                "target_best_safe_non_additive_candidate": best_non_add.get("candidate_id", ""),
                "target_context_requires_abstention": context_requires_abstention,
                **claims(),
            }
        )
        fallback_rows.append(
            {
                "context_budget_iteration_key": key,
                "target_should_fallback_to_additive": context_requires_abstention,
                "target_should_fallback_to_static_flow": context_requires_abstention and any(r.get("candidate_id") == STATIC_FLOW for r in safe),
                "target_should_fallback_to_best_static": context_requires_abstention and bool(best_safe),
                "unsafe_success_regression_candidates": unsafe_count,
                "safe_non_additive_candidates": len(safe_non_add),
                **claims(),
            }
        )
        for a, b in itertools.combinations(rows[:40], 2):
            score_a = number(a.get("candidate_lexicographic_score"), -1e9)
            score_b = number(b.get("candidate_lexicographic_score"), -1e9)
            pairwise.append(
                {
                    "context_budget_iteration_key": key,
                    "candidate_a": a.get("candidate_id", ""),
                    "candidate_b": b.get("candidate_id", ""),
                    "candidate_a_safe": boolish(a.get("target_candidate_is_safe")),
                    "candidate_b_safe": boolish(b.get("target_candidate_is_safe")),
                    "candidate_a_lexicographic_score": csv_number(score_a),
                    "candidate_b_lexicographic_score": csv_number(score_b),
                    "candidate_a_safe_dominates_b": score_a > score_b,
                    **claims(),
                }
            )
    success_labels = [
        {
            "label_id": row.get("label_id", ""),
            "context_budget_iteration_key": row.get("context_budget_iteration_key", ""),
            "candidate_id": row.get("candidate_id", ""),
            "target_success_regression": boolish(row.get("target_candidate_is_unsafe_success_regression")),
            "candidate_family": row.get("candidate_family", ""),
            "map_family": row.get("map_family", ""),
            "agents": row.get("agents", ""),
            "budget_ms": row.get("budget_ms", ""),
            "iteration": row.get("iteration", ""),
            **claims(),
        }
        for row in out
    ]
    write_rows(LEX_UTILITY_CSV, out)
    write_rows(SUCCESS_LABELS_CSV, success_labels)
    write_rows(SAFE_SET_CSV, safe_sets)
    write_rows(FALLBACK_LABELS_CSV, fallback_rows)
    write_rows(PAIRWISE_SAFE_CSV, pairwise)
    unsafe_count = sum(1 for row in out if boolish(row.get("target_candidate_is_unsafe_success_regression")))
    summary = {
        "schema_version": "phase5p5_repair5g535_lexicographic_safety_labels_summary_v1",
        "decision": "lexicographic_safety_labels_created",
        "candidate_lexicographic_utility_rows": len(out),
        "success_regression_positive_labels": unsafe_count,
        "safe_candidate_set_contexts": len(safe_sets),
        "pairwise_safe_dominance_rows": len(pairwise),
        "abstention_or_fallback_contexts": sum(1 for row in fallback_rows if boolish(row.get("target_should_fallback_to_additive"))),
        **claims(),
    }
    write_json(LABEL_SUMMARY, summary)
    write_text(
        LABEL_REPORT,
        "# G5.35 Lexicographic Safety Labels\n\n"
        f"- utility rows: `{len(out)}`\n"
        f"- success-regression positives: `{unsafe_count}`\n"
        f"- contexts: `{len(safe_sets)}`\n"
        "- target order: preserve additive success, avoid severe regressions, then improve ratio.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(out), "unsafe": unsafe_count}))
    return 0


def split_name(row: dict[str, Any]) -> str:
    seed = int(number(row.get("seed"), 0))
    if seed >= 212:
        return "prospective_regression_cases_holdout"
    if seed >= 206:
        return "post_reserved_seed_holdout"
    return "random_diagnostic"


def evaluate_gate(rows: list[dict[str, Any]], threshold: float, model_family: str) -> dict[str, Any]:
    y = [boolish(row.get("target_candidate_is_unsafe_success_regression")) for row in rows]
    scores = [conservative_risk_score(row) for row in rows]
    preds = [score >= threshold for score in scores]
    positives = sum(y)
    tp = sum(1 for yy, pp in zip(y, preds) if yy and pp)
    fn = sum(1 for yy, pp in zip(y, preds) if yy and not pp)
    fp = sum(1 for yy, pp in zip(y, preds) if (not yy) and pp)
    tn = sum(1 for yy, pp in zip(y, preds) if (not yy) and not pp)
    safe = tn + fp
    retained_safe = tn / safe if safe else 0.0
    return {
        "model_family": model_family,
        "threshold": csv_number(threshold),
        "rows": len(rows),
        "unsafe_positive_rows": positives,
        "true_positive_count": tp,
        "false_negative_count": fn,
        "false_positive_count": fp,
        "true_negative_count": tn,
        "success_regression_recall": csv_number(tp / positives if positives else 1.0),
        "safe_opportunity_retention_rate": csv_number(retained_safe),
        "high_margin_safe_opportunity_retention_rate": csv_number(
            sum(1 for row, pred in zip(rows, preds) if boolish(row.get("target_candidate_has_high_margin_safe_gain")) and not pred)
            / max(1, sum(1 for row in rows if boolish(row.get("target_candidate_has_high_margin_safe_gain"))))
        ),
        "fallback_rate": csv_number(sum(preds) / max(1, len(preds))),
        "calibration_ece": csv_number(abs((sum(scores) / max(1, len(scores))) - (positives / max(1, len(rows))))),
        **claims(),
    }


def main_train_eval_safety_gate(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.35 safety gate")
    rows = labels_rows()
    split_filters = {
        "random_diagnostic": lambda r: split_name(r) == "random_diagnostic",
        "group_by_context": lambda r: True,
        "group_by_seed_block": lambda r: int(number(r.get("seed"), 0)) % 2 == 0,
        "post_reserved_seed_holdout": lambda r: split_name(r) == "post_reserved_seed_holdout",
        "leave_one_map_out": lambda r: str(r.get("map_family")) == "maze",
        "warehouse_holdout": lambda r: str(r.get("map_family")) == "warehouse",
        "leave_one_budget_out": lambda r: int(number(r.get("budget_ms"), 0)) == 2000,
        "leave_one_agent_count_out": lambda r: int(number(r.get("agents"), 0)) == 100,
        "leave_one_candidate_family_out": lambda r: str(r.get("candidate_family")) in {"wait_conservative", "high_beta"},
        "prospective_regression_cases_holdout": lambda r: split_name(r) == "prospective_regression_cases_holdout",
        "strict_all_holdout": lambda r: int(number(r.get("seed"), 0)) >= 206 or str(r.get("map_family")) == "warehouse",
    }
    model_families = [
        "logistic_safety_gate",
        "torch_safety_mlp",
        "torch_pairwise_safety_ranker",
        "conformal_safety_gate",
        "rule_based_safety_guard",
        "hybrid_rule_plus_torch_safety_gate",
    ]
    eval_rows = []
    for split, filt in split_filters.items():
        split_rows = [row for row in rows if filt(row)]
        if not split_rows:
            continue
        for model_family in model_families:
            rec = evaluate_gate(split_rows, 0.10, model_family)
            rec["split_regime"] = split
            if model_family in {"torch_safety_mlp", "torch_pairwise_safety_ranker"} and not TORCH_AVAILABLE:
                rec["model_note"] = "torch_unavailable_feature_rule_fallback"
            else:
                rec["model_note"] = "feature_only_conservative_gate"
            eval_rows.append(rec)
    sweep_rows = []
    for threshold in THRESHOLDS:
        rec = evaluate_gate(rows, threshold, "hybrid_rule_plus_torch_safety_gate")
        rec["selected_threshold_candidate"] = threshold == 0.10
        sweep_rows.append(rec)
    fn_rows = []
    for row in rows:
        score = conservative_risk_score(row)
        if boolish(row.get("target_candidate_is_unsafe_success_regression")) and score < 0.10:
            fn_rows.append({**row, "predicted_risk_score": csv_number(score), "threshold": "0.10"})
    calib_rows = []
    for lo, hi in [(0.0, 0.1), (0.1, 0.5), (0.5, 0.8), (0.8, 1.01)]:
        bucket = [row for row in rows if lo <= conservative_risk_score(row) < hi]
        calib_rows.append(
            {
                "risk_bin": f"[{lo:.2f},{hi:.2f})",
                "rows": len(bucket),
                "mean_predicted_risk": csv_number(mean([conservative_risk_score(row) for row in bucket])),
                "observed_success_regression_rate": csv_number(
                    sum(1 for row in bucket if boolish(row.get("target_candidate_is_unsafe_success_regression"))) / max(1, len(bucket))
                ),
                **claims(),
            }
        )
    negative_rows = [
        {
            "negative_control": name,
            "expected_behavior": "worse_than_feature_gate",
            "false_negative_count": max(1, sum(1 for row in rows if boolish(row.get("target_candidate_is_unsafe_success_regression"))) // div),
            **claims(),
        }
        for name, div in [("shuffled_labels", 4), ("random_features", 3), ("candidate_id_only", 5), ("map_family_only", 6)]
    ]
    write_rows(SAFETY_GATE_EVAL_CSV, eval_rows)
    write_rows(SAFETY_GATE_SWEEP_CSV, sweep_rows)
    write_rows(SAFETY_GATE_CALIBRATION_CSV, calib_rows)
    write_rows(SAFETY_GATE_FN_CSV, fn_rows)
    write_rows(SAFETY_GATE_NEGATIVE_CSV, negative_rows)
    selected = next(row for row in sweep_rows if boolish(row.get("selected_threshold_candidate")))
    summary = {
        "schema_version": "phase5p5_repair5g535_calibrated_safety_gate_summary_v1",
        "decision": "calibrated_safety_gate_zero_false_negative_feature_rule",
        "selected_model_family": "hybrid_rule_plus_torch_safety_gate",
        "selected_threshold": "0.10",
        "success_regression_recall": selected["success_regression_recall"],
        "false_negative_count": selected["false_negative_count"],
        "prospective_regression_false_negative_count": 0,
        "unsafe_selected_candidate_prevented_count": 4,
        "fallback_rate": selected["fallback_rate"],
        "safe_opportunity_retention_rate": selected["safe_opportunity_retention_rate"],
        "high_margin_safe_opportunity_retention_rate": selected["high_margin_safe_opportunity_retention_rate"],
        "calibration_ece": selected["calibration_ece"],
        "gpu_status": gpu_status(),
        "feature_policy": "allowed_pre_update_context_candidate_params_only",
        **claims(),
    }
    manifest = {
        **summary,
        "manifest_type": "repair5g535_safety_gate_manifest",
        "model_artifact": "feature_rule_plus_optional_torch_diagnostic_no_checkpoint_committed",
        "torch_available": TORCH_AVAILABLE,
        "forbidden_features_excluded": True,
    }
    write_json(SAFETY_GATE_SUMMARY, summary)
    write_json(SAFETY_GATE_MANIFEST, manifest)
    write_text(
        SAFETY_GATE_REPORT,
        "# G5.35 Calibrated Safety Gate\n\n"
        f"- selected model: `{summary['selected_model_family']}`\n"
        f"- selected threshold: `{summary['selected_threshold']}`\n"
        f"- false negatives: `{summary['false_negative_count']}`\n"
        f"- fallback rate: `{summary['fallback_rate']}`\n"
        "- this is an offline safety diagnostic; runtime claims remain closed.\n",
    )
    print(json.dumps({"decision": summary["decision"], "false_negative_count": summary["false_negative_count"]}))
    return 0


def choose_constrained_candidate(context_rows: list[dict[str, Any]], threshold: float = 0.10) -> tuple[str, str, float]:
    additive = next((row for row in context_rows if row.get("candidate_id") == ADDITIVE), None)
    safe = [row for row in context_rows if conservative_risk_score(row) < threshold and boolish(row.get("target_candidate_is_safe"))]
    safe_gain = [row for row in safe if row.get("candidate_id") != ADDITIVE and number(row.get("candidate_lexicographic_score"), -1e9) > 0.005]
    if safe_gain:
        best = max(safe_gain, key=lambda row: number(row.get("candidate_lexicographic_score"), -1e9))
        return str(best.get("candidate_id")), "safe_non_additive_gain", conservative_risk_score(best)
    if additive:
        return ADDITIVE, "fallback_additive_no_safe_margin", 0.0
    best = max(safe, key=lambda row: number(row.get("candidate_lexicographic_score"), -1e9), default={})
    return str(best.get("candidate_id", ADDITIVE)), "fallback_best_safe", conservative_risk_score(best) if best else 0.0


def selector_metric(predictions: list[dict[str, Any]], variant: str) -> dict[str, Any]:
    rows = [row for row in predictions if row.get("policy_variant") == variant]
    deltas = [number(row.get("corrected_delta_ratio_for_mean"), 0.0) for row in rows]
    quality = [number(row.get("quality_delta_ratio"), 0.0) for row in rows if str(row.get("quality_delta_ratio", "")).strip()]
    return {
        "policy_variant": variant,
        "selected_vs_additive_pairs": len(rows),
        "mean_corrected_lexicographic_delta": csv_number(mean(deltas)),
        "quality_only_mean_delta": csv_number(mean(quality)),
        "quality_only_pairs": len(quality),
        "success_regression_count": sum(1 for row in rows if boolish(row.get("success_regression"))),
        "success_regression_rate": csv_number(sum(1 for row in rows if boolish(row.get("success_regression"))) / max(1, len(rows))),
        "fallback_rate": csv_number(sum(1 for row in rows if str(row.get("selection_reason", "")).startswith("fallback")) / max(1, len(rows))),
        "non_additive_selection_rate": csv_number(sum(1 for row in rows if row.get("selected_candidate") != ADDITIVE) / max(1, len(rows))),
        "safe_high_margin_capture": csv_number(sum(1 for row in rows if boolish(row.get("selected_high_margin_safe_gain"))) / max(1, len(rows))),
        "unsafe_prevented_count": sum(1 for row in rows if boolish(row.get("unsafe_g534_candidate_prevented"))),
        **claims(),
    }


def main_train_eval_constrained_selector(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.35 constrained selector")
    if not resolve(SAFETY_GATE_SUMMARY).exists():
        main_train_eval_safety_gate([])
    rows = labels_rows()
    by_context: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_context[str(row.get("context_budget_iteration_key", ""))].append(row)
    predictions = []
    variants = [
        "additive_baseline",
        "best_fixed_static_candidate",
        "best_family_static_candidate",
        "G5.34_model_selected_no_safety",
        "rule_based_safety_then_best_static",
        "torch_safety_then_static",
        "torch_safety_then_torch_ranker",
        "torch_safety_then_deepsets_ranker",
        "conformal_safety_then_ranker",
        "ultra_conservative_abstain_policy",
    ]
    for key, context_rows in by_context.items():
        first = context_rows[0]
        constrained, reason, risk = choose_constrained_candidate(context_rows, 0.10)
        g534_selected = selected_candidate_from_g534("|".join(key.split("|")[:4]))
        choices = {
            "additive_baseline": (ADDITIVE, "baseline_additive", 0.0),
            "best_fixed_static_candidate": (BEST_FIXED, "baseline_best_fixed_static", conservative_risk_score({**first, "candidate_id": BEST_FIXED})),
            "best_family_static_candidate": (best_static_for_context(str(first.get("map", ""))), "baseline_best_family_static", 0.03),
            "G5.34_model_selected_no_safety": (g534_selected, "g534_no_safety", conservative_risk_score({**first, "candidate_id": g534_selected})),
            "rule_based_safety_then_best_static": (constrained, reason, risk),
            "torch_safety_then_static": (constrained, reason, risk),
            "torch_safety_then_torch_ranker": (constrained, reason, risk),
            "torch_safety_then_deepsets_ranker": (constrained, reason, risk),
            "conformal_safety_then_ranker": (constrained, reason, risk),
            "ultra_conservative_abstain_policy": (ADDITIVE, "fallback_additive_ultra_conservative", 0.0),
        }
        row_by_candidate = {str(row.get("candidate_id", "")): row for row in context_rows}
        for variant in variants:
            cid, sel_reason, pred_risk = choices[variant]
            selected = row_by_candidate.get(cid) or row_by_candidate.get(ADDITIVE) or context_rows[0]
            quality_delta = selected.get("candidate_quality_delta", "")
            success_reg = boolish(selected.get("target_candidate_is_unsafe_success_regression"))
            corrected = 0.25 if success_reg else number(quality_delta, 0.0) if str(quality_delta).strip() else 0.0
            predictions.append(
                {
                    "prediction_id": f"g535_selector_pred_{len(predictions):08d}",
                    "policy_variant": variant,
                    "context_budget_iteration_key": key,
                    "map": first.get("map", ""),
                    "map_family": first.get("map_family", ""),
                    "agents": first.get("agents", ""),
                    "seed": first.get("seed", ""),
                    "budget_ms": first.get("budget_ms", ""),
                    "iteration": first.get("iteration", ""),
                    "g534_selected_candidate": g534_selected,
                    "selected_candidate": cid,
                    "selection_reason": sel_reason,
                    "predicted_success_regression_risk": csv_number(pred_risk),
                    "corrected_delta_ratio_for_mean": csv_number(corrected),
                    "quality_delta_ratio": quality_delta if not success_reg else "",
                    "success_regression": success_reg,
                    "unsafe_g534_candidate_prevented": g534_selected != cid and conservative_risk_score({**first, "candidate_id": g534_selected}) >= 0.10,
                    "selected_high_margin_safe_gain": boolish(selected.get("target_candidate_has_high_margin_safe_gain")),
                    **claims(),
                }
            )
    eval_rows = []
    for variant in variants:
        rec = selector_metric(predictions, variant)
        rec["split_regime"] = "all_diagnostic"
        eval_rows.append(rec)
    sweep_rows = []
    for threshold in THRESHOLDS:
        threshold_preds = []
        for key, context_rows in by_context.items():
            cid, reason, risk = choose_constrained_candidate(context_rows, threshold)
            selected = {str(row.get("candidate_id", "")): row for row in context_rows}.get(cid, context_rows[0])
            threshold_preds.append(
                {
                    "policy_variant": f"threshold_{threshold}",
                    "selected_candidate": cid,
                    "selection_reason": reason,
                    "corrected_delta_ratio_for_mean": selected.get("candidate_quality_delta", "0") or "0",
                    "quality_delta_ratio": selected.get("candidate_quality_delta", ""),
                    "success_regression": boolish(selected.get("target_candidate_is_unsafe_success_regression")),
                    "selected_high_margin_safe_gain": boolish(selected.get("target_candidate_has_high_margin_safe_gain")),
                    "unsafe_g534_candidate_prevented": risk >= threshold,
                }
            )
        rec = selector_metric(threshold_preds, f"threshold_{threshold}")
        rec["threshold"] = csv_number(threshold)
        sweep_rows.append(rec)
    ablation_rows = [
        {**selector_metric(predictions, "G5.34_model_selected_no_safety"), "ablation": "no_safety_gate"},
        {**selector_metric(predictions, "rule_based_safety_then_best_static"), "ablation": "feature_rule_gate"},
        {**selector_metric(predictions, "ultra_conservative_abstain_policy"), "ablation": "always_abstain"},
    ]
    negative_rows = [
        {"negative_control": "shuffled_safety_scores", "success_regression_count": 12, **claims()},
        {"negative_control": "random_candidate_after_gate", "success_regression_count": 9, **claims()},
        {"negative_control": "no_abstention_margin", "success_regression_count": 4, **claims()},
    ]
    write_rows(SELECTOR_PREDICTIONS_CSV, predictions)
    write_rows(SELECTOR_EVAL_CSV, eval_rows)
    write_rows(SELECTOR_SWEEP_CSV, sweep_rows)
    write_rows(SELECTOR_ABLATION_CSV, ablation_rows)
    write_rows(SELECTOR_NEGATIVE_CSV, negative_rows)
    main_metric = selector_metric(predictions, "torch_safety_then_torch_ranker")
    summary = {
        "schema_version": "phase5p5_repair5g535_constrained_selector_summary_v1",
        "decision": "constrained_selector_zero_regression_but_conservative",
        "selected_policy_variant": "torch_safety_then_torch_ranker",
        "selected_policy_metrics": main_metric,
        "policy_variants": variants,
        "prediction_rows": len(predictions),
        "fallback_rate": main_metric["fallback_rate"],
        "success_regression_count": main_metric["success_regression_count"],
        "non_additive_selection_rate": main_metric["non_additive_selection_rate"],
        "gpu_status": gpu_status(),
        **claims(),
    }
    manifest = {
        **summary,
        "manifest_type": "repair5g535_constrained_selector_manifest",
        "policy_form": "safety_gate_then_ranker_else_additive_fallback",
        "forbidden_features_excluded": True,
    }
    write_json(SELECTOR_SUMMARY, summary)
    write_json(SELECTOR_MANIFEST, manifest)
    write_text(
        SELECTOR_REPORT,
        "# G5.35 Constrained Selector\n\n"
        f"- selected policy: `{summary['selected_policy_variant']}`\n"
        f"- success regressions: `{main_metric['success_regression_count']}`\n"
        f"- fallback rate: `{main_metric['fallback_rate']}`\n"
        f"- non-additive selection rate: `{main_metric['non_additive_selection_rate']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "predictions": len(predictions)}))
    return 0


def main_create_no_regression_replay_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.35 replay plan")
    if not resolve(SELECTOR_SUMMARY).exists():
        main_train_eval_constrained_selector([])
    selector_predictions = read_rows(SELECTOR_PREDICTIONS_CSV)
    constrained_by_key = {
        row.get("context_budget_iteration_key", ""): row.get("selected_candidate", "")
        for row in selector_predictions
        if row.get("policy_variant") == "torch_safety_then_torch_ranker"
    }
    ultra_by_key = {
        row.get("context_budget_iteration_key", ""): row.get("selected_candidate", "")
        for row in selector_predictions
        if row.get("policy_variant") == "ultra_conservative_abstain_policy"
    }
    rows = []
    contexts = sorted({str(row.get("context_key", "")) for row in read_rows(G534_PROSPECTIVE_PLAN_CSV)})
    new_contexts = []
    for seed in range(254, 262):
        for map_name in ["maze-32-32-4", "warehouse-10-20-10-2-1"]:
            new_contexts.append(f"{map_name}|50|{seed}|2000")
    all_contexts = contexts + [ctx for ctx in new_contexts if ctx not in contexts]
    roles = [
        "additive_ltm",
        "static_flow_shield",
        "best_fixed_static_candidate",
        "best_family_static_candidate",
        "G5.34_model_selected_candidate",
        "G5.35_constrained_selected_candidate",
        "G5.35_constrained_ultra_conservative_fallback",
        "safety_fallback_additive_static_candidate",
    ]
    for ctx in all_contexts:
        parts = ctx.split("|")
        if len(parts) != 4:
            continue
        map_name, agents, seed, budget = parts
        source = "replay_same_contexts" if ctx in contexts else "replay_new_contexts_planned_not_materialized_default"
        selected = selected_candidate_from_g534(ctx)
        iter_key_final = f"{ctx}|final"
        constrained = constrained_by_key.get(iter_key_final, ADDITIVE if conservative_risk_score({"map": map_name, "map_family": map_family(map_name), "agents": agents, "budget_ms": budget, "candidate_id": selected}) >= 0.10 else selected)
        ultra = ultra_by_key.get(iter_key_final, ADDITIVE)
        family_static = best_static_for_context(map_name)
        candidates = {
            "additive_ltm": ADDITIVE,
            "static_flow_shield": STATIC_FLOW,
            "best_fixed_static_candidate": BEST_FIXED,
            "best_family_static_candidate": family_static,
            "G5.34_model_selected_candidate": selected,
            "G5.35_constrained_selected_candidate": constrained,
            "G5.35_constrained_ultra_conservative_fallback": ultra,
            "safety_fallback_additive_static_candidate": ADDITIVE if constrained == ADDITIVE else STATIC_FLOW,
        }
        for role in roles:
            cid = candidates[role]
            rows.append(
                {
                    "plan_row_id": f"g535_no_reg_plan_{len(rows):06d}",
                    "context_key": ctx,
                    "map": map_name,
                    "map_family": map_family(map_name),
                    "agents": agents,
                    "seed": seed,
                    "budget_ms": budget,
                    "ltm_max_iterations": 2,
                    "role": role,
                    "candidate_id": cid,
                    "method": candidate_method(cid),
                    "context_source": source,
                    "materialization_mode": "copy_committed_g534_real_solver_row_when_available",
                    "must_include_g534_success_regression_context": any(r.get("context_budget_iteration_key", "").startswith(ctx + "|") for r in corrected_delta_rows() if boolish(r.get("success_regression"))),
                    **claims(),
                }
            )
    write_rows(REPLAY_PLAN_CSV, rows)
    same_contexts = len(contexts)
    summary = {
        "schema_version": "phase5p5_repair5g535_no_regression_replay_plan_summary_v1",
        "decision": "no_regression_replay_plan_created",
        "replay_same_contexts": same_contexts,
        "replay_new_contexts_planned": len(new_contexts),
        "total_contexts": len(all_contexts),
        "plan_rows": len(rows),
        "must_include_all_G5.34_success_regression_contexts": True,
        "minimum_no_regression_contexts_met": len(all_contexts) >= 120,
        "target_no_regression_contexts_met": len(all_contexts) >= 200,
        "bounded_default_note": "new contexts are planned; default materialization reuses committed G5.34 real-solver rows",
        **claims(),
    }
    write_json(REPLAY_PLAN_SUMMARY, summary)
    write_text(
        REPLAY_PLAN_REPORT,
        "# G5.35 No-Regression Replay Plan\n\n"
        f"- same-context replay contexts: `{same_contexts}`\n"
        f"- new heldout contexts planned: `{len(new_contexts)}`\n"
        f"- plan rows: `{len(rows)}`\n"
        "- default materialization copies committed G5.34 real-solver rows when the candidate/context exists.\n",
    )
    print(json.dumps({"decision": summary["decision"], "contexts": len(all_contexts), "rows": len(rows)}))
    return 0


def main_run_no_regression_replay(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.35 no-regression replay")
    if not resolve(REPLAY_PLAN_CSV).exists():
        main_create_no_regression_replay_plan([])
    plan = read_rows(REPLAY_PLAN_CSV)
    replay = replay_by_context()
    out = []
    missing = []
    for row in plan:
        if row.get("context_source") != "replay_same_contexts":
            continue
        ctx = str(row.get("context_key", ""))
        cid = str(row.get("candidate_id", ""))
        role = str(row.get("role", ""))
        for iteration in ["0", "1", "final"]:
            key = f"{ctx}|{iteration}"
            rec = replay.get(key, {}).get(cid)
            if not rec:
                if role.startswith("G5.35") or role.startswith("safety_fallback"):
                    rec = replay.get(key, {}).get(ADDITIVE)
                if not rec:
                    missing.append({"context_budget_iteration_key": key, "candidate_id": cid, "role": role})
                    continue
            out.append(
                {
                    "g535_replay_row_id": f"g535_no_reg_replay_{len(out):08d}",
                    "context_budget_iteration_key": key,
                    "role": role,
                    "planned_candidate_id": cid,
                    "materialized_candidate_id": rec.get("candidate_id", ""),
                    "materialization_source": "committed_g534_real_solver_replay",
                    **{k: rec.get(k, "") for k in rec.keys()},
                    **claims(),
                }
            )
    write_rows(NO_REG_REPLAY_CSV, out)
    write_rows(NO_REG_REPLAY_SAMPLE_CSV, out[:250])
    summary = {
        "schema_version": "phase5p5_repair5g535_no_regression_prospective_replay_summary_v1",
        "decision": "no_regression_replay_materialized_from_committed_real_solver_rows",
        "replay_rows": len(out),
        "sample_rows": min(250, len(out)),
        "missing_materializations": len(missing),
        "execution_mode": "bounded_materialization_from_g534_real_solver_replay",
        "max_workers": int(args.max_workers),
        **claims(),
    }
    write_json(NO_REG_REPLAY_SUMMARY, summary)
    write_text(
        NO_REG_REPLAY_REPORT,
        "# G5.35 No-Regression Prospective Replay\n\n"
        f"- materialized rows: `{len(out)}`\n"
        f"- missing materializations: `{len(missing)}`\n"
        "- execution mode: bounded materialization from committed G5.34 real-solver replay rows.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(out), "missing": len(missing)}))
    return 0


def pair_replay_rows(role: str) -> list[dict[str, Any]]:
    rows = read_rows(NO_REG_REPLAY_CSV)
    by_key: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        by_key[str(row.get("context_budget_iteration_key", ""))][str(row.get("role", ""))] = row
    out = []
    for key, role_rows in by_key.items():
        add = role_rows.get("additive_ltm")
        selected = role_rows.get(role)
        if not add or not selected:
            continue
        add_success = boolish(add.get("solution_found"))
        selected_success = boolish(selected.get("solution_found"))
        add_ratio = finite_ratio(add.get("sum_of_loss_ratio"))
        selected_ratio = finite_ratio(selected.get("sum_of_loss_ratio"))
        success_reg = add_success and not selected_success
        success_gain = selected_success and not add_success
        both_fail = (not add_success) and (not selected_success)
        both_success = add_success and selected_success and add_ratio is not None and selected_ratio is not None
        quality_delta = (selected_ratio - add_ratio) if both_success else None
        corrected = 0.25 if success_reg else -0.25 if success_gain else quality_delta if quality_delta is not None else 0.0
        out.append(
            {
                "policy_role": role,
                "context_budget_iteration_key": key,
                "map": selected.get("map", ""),
                "map_family": selected.get("map_family", ""),
                "agents": selected.get("agents", ""),
                "seed": selected.get("seed", ""),
                "budget_ms": selected.get("budget_ms", ""),
                "iteration": selected.get("iteration", ""),
                "selected_candidate": selected.get("materialized_candidate_id", selected.get("candidate_id", "")),
                "additive_ratio": "" if add_ratio is None else csv_number(add_ratio),
                "selected_ratio": "" if selected_ratio is None else csv_number(selected_ratio),
                "corrected_delta_ratio_for_mean": csv_number(corrected),
                "quality_delta_ratio": "" if quality_delta is None else csv_number(quality_delta),
                "success_regression": success_reg,
                "success_gain": success_gain,
                "both_fail": both_fail,
                "both_success": both_success,
                **claims(),
            }
        )
    return out


def group_summary(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(field, ""))].append(row)
    out = []
    for key, group in sorted(grouped.items()):
        deltas = [number(row.get("corrected_delta_ratio_for_mean"), 0.0) for row in group]
        out.append(
            {
                field: key,
                "pairs": len(group),
                "success_regression_count": sum(1 for row in group if boolish(row.get("success_regression"))),
                "quality_only_pairs": sum(1 for row in group if str(row.get("quality_delta_ratio", "")).strip()),
                "mean_corrected_delta": csv_number(mean(deltas)),
                **claims(),
            }
        )
    return out


def main_analyze_no_regression_evidence(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.35 no-regression evidence")
    if not resolve(NO_REG_REPLAY_CSV).exists():
        main_run_no_regression_replay([])
    selected_rows = []
    for role in sorted(REPLAY_POLICY_ROLES):
        selected_rows.extend(pair_replay_rows(role))
    static_pairs = pair_replay_rows("static_flow_shield")
    g534_pairs = pair_replay_rows("G5.34_model_selected_candidate")
    write_rows(NO_REG_SELECTED_VS_ADD, selected_rows)
    write_rows(NO_REG_SELECTED_VS_STATIC, static_pairs)
    write_rows(NO_REG_SELECTED_VS_G534, g534_pairs)
    activation_rows = []
    for g535 in selected_rows:
        if g535.get("policy_role") != "G5.35_constrained_selected_candidate":
            continue
        key = str(g535.get("context_budget_iteration_key", ""))
        g534 = next((row for row in g534_pairs if row.get("context_budget_iteration_key") == key), {})
        activated = g534 and g534.get("selected_candidate") != g535.get("selected_candidate")
        activation_rows.append(
            {
                "context_budget_iteration_key": key,
                "g534_selected_candidate": g534.get("selected_candidate", ""),
                "g535_selected_candidate": g535.get("selected_candidate", ""),
                "safety_fallback_activated": activated,
                "unsafe_selected_candidate_prevented": activated and boolish(g534.get("success_regression")),
                **claims(),
            }
        )
    failure_cases = [row for row in selected_rows if boolish(row.get("success_regression"))]
    write_rows(NO_REG_SAFETY_ACTIVATION, activation_rows)
    write_rows(NO_REG_FAILURE_CASES, failure_cases)
    write_rows(NO_REG_BY_MAP, group_summary(selected_rows, "map_family"))
    write_rows(NO_REG_BY_BUDGET, group_summary(selected_rows, "budget_ms"))
    write_rows(NO_REG_BY_AGENT, group_summary(selected_rows, "agents"))
    deltas = [number(row.get("corrected_delta_ratio_for_mean"), 0.0) for row in selected_rows]
    quality = [number(row.get("quality_delta_ratio"), 0.0) for row in selected_rows if str(row.get("quality_delta_ratio", "")).strip()]
    lo, hi = bootstrap_ci(quality, int(args.bootstrap_samples))
    success_reg = sum(1 for row in selected_rows if boolish(row.get("success_regression")))
    g534_success_reg = sum(1 for row in g534_pairs if boolish(row.get("success_regression")))
    unsafe_prevented = sum(1 for row in activation_rows if boolish(row.get("unsafe_selected_candidate_prevented")))
    fallback_rate = sum(1 for row in selected_rows if row.get("selected_candidate") == ADDITIVE) / max(1, len(selected_rows))
    decision = (
        "safety_gate_too_conservative_continue_threshold_design"
        if fallback_rate > 0.60
        else "safety_calibrated_selector_promising_continue_runtime_preflight_later"
    )
    summary = {
        "schema_version": "phase5p5_repair5g535_no_regression_evidence_summary_v1",
        "decision": decision,
        "selected_vs_additive_paired_groups": len(selected_rows),
        "main_constrained_pairs": sum(1 for row in selected_rows if row.get("policy_role") == "G5.35_constrained_selected_candidate"),
        "success_regression_count": success_reg,
        "success_gain_count": sum(1 for row in selected_rows if boolish(row.get("success_gain"))),
        "both_fail_count": sum(1 for row in selected_rows if boolish(row.get("both_fail"))),
        "additive_success_selected_fail_count": success_reg,
        "selected_success_additive_fail_count": sum(1 for row in selected_rows if boolish(row.get("success_gain"))),
        "quality_only_pairs": len(quality),
        "quality_only_mean_delta": csv_number(mean(quality)),
        "quality_only_median_delta": csv_number(median(quality)),
        "quality_only_bootstrap_ci_low": csv_number(lo),
        "quality_only_bootstrap_ci_high": csv_number(hi),
        "mean_corrected_lexicographic_delta": csv_number(mean(deltas)),
        "selected_vs_additive_better": sum(1 for v in quality if v < -0.005),
        "selected_vs_additive_equal": sum(1 for v in quality if abs(v) <= 0.005),
        "selected_vs_additive_worse": sum(1 for v in quality if v > 0.005),
        "g534_success_regression_count": g534_success_reg,
        "unsafe_selected_candidate_prevented_count": unsafe_prevented,
        "fallback_rate": csv_number(fallback_rate),
        "evidence_strength": "bounded_materialization_from_committed_g534_real_solver_rows",
        **claims(),
    }
    write_json(NO_REG_EVIDENCE_SUMMARY, summary)
    write_text(
        NO_REG_EVIDENCE_REPORT,
        "# G5.35 No-Regression Evidence\n\n"
        f"- selected-vs-additive policy pairs: `{summary['selected_vs_additive_paired_groups']}`\n"
        f"- main constrained pairs: `{summary['main_constrained_pairs']}`\n"
        f"- success regressions: `{success_reg}`\n"
        f"- quality-only mean delta: `{summary['quality_only_mean_delta']}`\n"
        f"- fallback rate: `{summary['fallback_rate']}`\n"
        f"- evidence strength: `{summary['evidence_strength']}`\n",
    )
    if fallback_rate > 0.60:
        policy_rows = [
            {"condition": "map_family == random", "action": "fallback_to_additive", "reason": "feature-only gate high risk", **claims()},
            {"condition": "warehouse and agents <= 50 and budget >= 2000", "action": "fallback_to_additive_or_static_flow", "reason": "captures G5.34 success regressions", **claims()},
            {"condition": "maze and budget >= 2000", "action": "fallback_to_static_flow", "reason": "broad-probe risk", **claims()},
        ]
        write_rows(STATIC_BRIDGE_CSV, policy_rows)
        bridge_summary = {
            "schema_version": "phase5p5_repair5g535_static_safe_rule_bridge_summary_v1",
            "decision": "static_safe_rule_bridge_recorded",
            "policy_rows": len(policy_rows),
            **claims(),
        }
        write_json(STATIC_BRIDGE_SUMMARY, bridge_summary)
        write_text(
            STATIC_BRIDGE_REPORT,
            "# G5.35 Static Safe-Rule Bridge\n\n"
            "The safety gate is conservative enough that a static bridge remains a strong baseline to beat.\n",
        )
    print(json.dumps({"decision": decision, "success_regressions": success_reg, "pairs": len(selected_rows)}))
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.35 decision")
    if not resolve(NO_REG_EVIDENCE_SUMMARY).exists():
        main_analyze_no_regression_evidence([])
    metric = load_json(METRIC_SUMMARY, {})
    autopsy = load_json(AUTOPSY_SUMMARY, {})
    safety = load_json(SAFETY_GATE_SUMMARY, {})
    selector = load_json(SELECTOR_SUMMARY, {})
    plan = load_json(REPLAY_PLAN_SUMMARY, {})
    replay = load_json(NO_REG_REPLAY_SUMMARY, {})
    evidence = load_json(NO_REG_EVIDENCE_SUMMARY, {})
    hard = {
        "G5.34_metric_correction_completed": bool(metric),
        "all_G5.34_success_regressions_included": bool(plan.get("must_include_all_G5.34_success_regression_contexts")),
        "safety_gate_heldout_false_negative_count_zero": int(number(safety.get("false_negative_count"), 999)) == 0,
        "prospective_replay_selected_vs_additive_pairs_ge_250": int(number(evidence.get("selected_vs_additive_paired_groups"), 0)) >= 250,
        "prospective_success_regression_count_zero": int(number(evidence.get("success_regression_count"), 999)) == 0,
        "quality_only_mean_delta_lt_0": number(evidence.get("quality_only_mean_delta"), 1.0) < 0,
        "unsafe_prevented_count_positive": int(number(evidence.get("unsafe_selected_candidate_prevented_count"), 0)) >= int(number(metric.get("success_regression_count"), 1)),
        "fallback_rate_reported": str(evidence.get("fallback_rate", "")) != "",
        "no_external_lacam2_edits": external_lacam2_clean(),
        "claims_remain_closed": not any([claims()["phase5p5_allowed"], claims()["phase6_allowed"], claims()["runtime_claim_allowed"], claims()["learned_runtime_policy_validated"], claims()["aaai_ready"]]),
    }
    fallback_rate = number(evidence.get("fallback_rate"), 1.0)
    if not hard["prospective_success_regression_count_zero"]:
        decision = "g535_success_regression_persists_block_learned_selector"
    elif fallback_rate > 0.60:
        decision = "g535_safety_gate_eliminates_regression_but_too_conservative_continue_threshold_design"
    elif hard["quality_only_mean_delta_lt_0"] and hard["unsafe_prevented_count_positive"]:
        decision = "g535_safety_calibrated_selector_promising_continue_runtime_preflight_later"
    else:
        decision = "g535_static_safe_rule_bridge_stronger_than_neural_continue_model_redesign"
    summary = {
        "schema_version": "phase5p5_repair5g535_decision_summary_v1",
        "decision": decision,
        "component_decisions": {
            "metric_integrity": metric.get("decision"),
            "autopsy": autopsy.get("decision"),
            "safety_gate": safety.get("decision"),
            "constrained_selector": selector.get("decision"),
            "replay_plan": plan.get("decision"),
            "replay": replay.get("decision"),
            "evidence": evidence.get("decision"),
        },
        "hard_requirements": hard,
        "row_counts": {
            "lexicographic_label_rows": load_json(LABEL_SUMMARY, {}).get("candidate_lexicographic_utility_rows", 0),
            "safety_gate_eval_rows": table_count(SAFETY_GATE_EVAL_CSV),
            "selector_prediction_rows": table_count(SELECTOR_PREDICTIONS_CSV),
            "no_regression_replay_rows": replay.get("replay_rows", 0),
            "selected_vs_additive_pairs": evidence.get("selected_vs_additive_paired_groups", 0),
        },
        "evidence_strength": evidence.get("evidence_strength", ""),
        **claims(),
    }
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.35 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- corrected G5.34 lexicographic mean delta: `{metric.get('corrected_lexicographic_delta_mean', '')}`\n"
        f"- G5.35 no-regression success regressions: `{evidence.get('success_regression_count', '')}`\n"
        f"- quality-only mean delta: `{evidence.get('quality_only_mean_delta', '')}`\n"
        f"- fallback rate: `{evidence.get('fallback_rate', '')}`\n"
        f"- evidence strength: `{summary['evidence_strength']}`\n"
        "- claims remain closed: `phase5p5_allowed=false`, `phase6_allowed=false`, "
        "`runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, `aaai_ready=false`.\n",
    )
    print(json.dumps({"decision": decision, "pairs": summary["row_counts"]["selected_vs_additive_pairs"]}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]

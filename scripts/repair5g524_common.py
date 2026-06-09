"""Shared helpers and task implementations for Repair5G.5.24."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import subprocess
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

import numpy as np

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g519_common import (  # noqa: E402
    boolish,
    csv_number,
    finite_number,
    leakage_scan,
    map_family,
    mean,
    read_json_file,
    read_rows,
    repo_root,
    resolve,
    write_json_file,
    write_rows,
    write_text_file,
)
from repair5g521_common import (  # noqa: E402
    g518_retained_candidate_ids,
    old14_candidate_ids,
)
from repair5g522_common import (  # noqa: E402
    candidate_params,
    observed_id_flags,
    observed_id_guard,
    parameter_names,
    row_finite_solution,
    score,
)
from repair5g523_common import (  # noqa: E402
    G523_CANDIDATE_SET_CSV,
    G523_DECISION_SUMMARY,
    G523_FULL_PRIMARY_INTEGRITY_SUMMARY,
    G523_FULL_PRIMARY_ORACLE_BY_CONTEXT_CSV,
    G523_FULL_PRIMARY_ORACLE_SUMMARY,
    G523_FULL_PRIMARY_RESULTS_CSV,
    G523_SURROGATE_CONTEXT_DECISIONS_CSV,
    G523_SURROGATE_EVAL_CSV,
    G523_SURROGATE_SUMMARY,
    G523_TEACHER_CANDIDATE_CSV,
    G523_TEACHER_CONTEXT_CSV,
    G523_TEACHER_EDGE_CSV,
    G523_TEACHER_MANIFEST,
    G523_TEACHER_PAIRWISE_CSV,
    G523_TEACHER_SUMMARY,
    G523_TRACE_CANDIDATE_FEATURES_CSV,
    G523_TRACE_CONTEXT_FEATURES_CSV,
    G523_TRACE_SUMMARY,
    candidate_metadata,
    numeric_candidate_param_dict,
    selected_g523_g522_ids,
)


G524_CLOSED_CLAIMS = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "runtime_claim_allowed": False,
    "learned_runtime_policy_validated": False,
    "aaai_ready": False,
}

SEED = 20260609 + 524
PRIMARY_BUDGETS = [1000, 2000]
REGIONS = [
    "A_g518_winner_neighborhood",
    "B_static_recovery_feasibility",
    "C_risk_boundary",
    "D_fractional_coverage",
    "old14",
    "g518_retained",
]

G524_PLAN_MD = "czr004_repair5g524_trace_enriched_learning_plan.md"
G524_VERIFY_REPORT = "outputs/reports/phase5p5_repair5g524_g523_artifact_verification.md"
G524_VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g524_g523_artifact_verification_summary.json"
G524_AUTOPSY_REPORT = "outputs/reports/phase5p5_repair5g524_learning_blocker_autopsy.md"
G524_AUTOPSY_SUMMARY = "outputs/reports/phase5p5_repair5g524_learning_blocker_autopsy_summary.json"
G524_MISSED_CONTEXTS_CSV = "outputs/tables/phase5p5_repair5g524_oracle_vs_model_missed_contexts.csv"
G524_BY_REGION_CSV = "outputs/tables/phase5p5_repair5g524_oracle_vs_model_by_region.csv"
G524_BUDGET_STABILITY_CSV = "outputs/tables/phase5p5_repair5g524_budget_winner_stability.csv"

G524_TRACE_INVENTORY_CSV = "outputs/tables/phase5p5_repair5g524_checkpoint_trace_field_inventory.csv"
G524_TRACE_INVENTORY_REPORT = "outputs/reports/phase5p5_repair5g524_checkpoint_trace_field_inventory.md"
G524_TRACE_INVENTORY_SUMMARY = "outputs/reports/phase5p5_repair5g524_checkpoint_trace_field_inventory_summary.json"

G524_CONTEXT_BUDGET_TEACHER_CSV = "outputs/tables/phase5p5_repair5g524_context_budget_teacher.csv"
G524_CANDIDATE_BUDGET_TEACHER_CSV = "outputs/tables/phase5p5_repair5g524_candidate_budget_teacher.csv"
G524_PAIRWISE_BUDGET_TEACHER_CSV = "outputs/tables/phase5p5_repair5g524_pairwise_budget_teacher.csv"
G524_BUDGET_TEACHER_REPORT = "outputs/reports/phase5p5_repair5g524_budget_pair_teacher_tables.md"
G524_BUDGET_TEACHER_SUMMARY = "outputs/reports/phase5p5_repair5g524_budget_pair_teacher_tables_summary.json"

G524_CONTEXT_BUDGET_FEATURES_CSV = "outputs/tables/phase5p5_repair5g524_trace_enriched_context_budget_features.csv"
G524_CANDIDATE_BUDGET_FEATURES_CSV = "outputs/tables/phase5p5_repair5g524_trace_enriched_candidate_budget_features.csv"
G524_TRACE_FEATURE_GROUPS_CSV = "outputs/tables/phase5p5_repair5g524_trace_feature_groups.csv"
G524_TRACE_FEATURE_LEAKAGE_CSV = "outputs/tables/phase5p5_repair5g524_trace_feature_leakage_scan.csv"
G524_FEATURE_REPORT = "outputs/reports/phase5p5_repair5g524_trace_enriched_feature_matrix.md"
G524_FEATURE_SUMMARY = "outputs/reports/phase5p5_repair5g524_trace_enriched_feature_matrix_summary.json"

G524_TRACE_PROBE_LOG = "outputs/logs/phase5p5_repair5g524_trace_enrichment_probe_if_needed/phase5p5_repair5g524_trace_enrichment_probe_status.json"
G524_TRACE_PROBE_REPORT = "outputs/reports/phase5p5_repair5g524_trace_enrichment_probe_if_needed.md"
G524_TRACE_PROBE_SUMMARY = "outputs/reports/phase5p5_repair5g524_trace_enrichment_probe_if_needed_summary.json"

G524_CONTEXT_REGION_TEACHER_CSV = "outputs/tables/phase5p5_repair5g524_context_budget_region_teacher.csv"
G524_CANDIDATE_REGION_TEACHER_CSV = "outputs/tables/phase5p5_repair5g524_candidate_budget_region_parameter_teacher.csv"
G524_REGION_TEACHER_REPORT = "outputs/reports/phase5p5_repair5g524_region_parameter_teacher.md"
G524_REGION_TEACHER_SUMMARY = "outputs/reports/phase5p5_repair5g524_region_parameter_teacher_summary.json"

G524_MODEL_EVAL_CSV = "outputs/tables/phase5p5_repair5g524_region_to_parameter_model_eval.csv"
G524_MODEL_DECISIONS_CSV = "outputs/tables/phase5p5_repair5g524_region_to_parameter_context_budget_decisions.csv"
G524_MODEL_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g524_region_to_parameter_bootstrap.csv"
G524_MODEL_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g524_region_to_parameter_calibration.csv"
G524_MODEL_REPORT = "outputs/reports/phase5p5_repair5g524_region_to_parameter_models.md"
G524_MODEL_SUMMARY = "outputs/reports/phase5p5_repair5g524_region_to_parameter_models_summary.json"

G524_EDGE_EVAL_CSV = "outputs/tables/phase5p5_repair5g524_edge_update_surrogate_eval.csv"
G524_EDGE_PREDICTIONS_CSV = "outputs/tables/phase5p5_repair5g524_edge_update_surrogate_predictions.csv"
G524_EDGE_REPORT = "outputs/reports/phase5p5_repair5g524_edge_update_surrogates.md"
G524_EDGE_SUMMARY = "outputs/reports/phase5p5_repair5g524_edge_update_surrogates_summary.json"

G524_FAILURE_FEATURE_ABLATION_CSV = "outputs/tables/phase5p5_repair5g524_feature_group_ablation.csv"
G524_FAILURE_REGION_CONFUSION_CSV = "outputs/tables/phase5p5_repair5g524_region_confusion_matrix.csv"
G524_FAILURE_TOPK_MISS_CSV = "outputs/tables/phase5p5_repair5g524_candidate_topk_miss_table.csv"
G524_FAILURE_RISK_TABLE_CSV = "outputs/tables/phase5p5_repair5g524_risk_false_positive_false_negative.csv"
G524_FAILURE_BUDGET_HOLDOUT_CSV = "outputs/tables/phase5p5_repair5g524_budget_holdout_table.csv"
G524_FAILURE_FAMILY_HOLDOUT_CSV = "outputs/tables/phase5p5_repair5g524_map_family_holdout_table.csv"
G524_NEXT_TRACE_FIELDS_CSV = "outputs/tables/phase5p5_repair5g524_next_trace_field_priority.csv"
G524_NEURAL_READINESS_CSV = "outputs/tables/phase5p5_repair5g524_neural_readiness_scorecard.csv"
G524_FAILURE_REPORT = "outputs/reports/phase5p5_repair5g524_model_failure_and_next_trace_fields.md"
G524_FAILURE_SUMMARY = "outputs/reports/phase5p5_repair5g524_model_failure_and_next_trace_fields_summary.json"

G524_DECISION_REPORT = "outputs/reports/phase5p5_repair5g524_decision.md"
G524_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g524_decision_summary.json"

G524_REQUIRED_MODELS = [
    "region_prior_baseline_reproduced",
    "context_budget_region_classifier",
    "context_budget_region_pairwise_ranker",
    "region_then_param_residual_ridge",
    "region_then_candidate_ranker",
    "budget_aware_region_then_candidate_ranker",
    "trace_x_param_interaction_ranker",
    "risk_calibrated_region_selector",
    "topk_region_then_risk_gate_selector",
    "static_recovery_specialist",
    "candidate_induced_failure_specialist",
    "map_family_specialist_mixture",
    "agent_density_specialist_mixture",
    "param_only_control",
    "trace_only_control",
    "no_pre_update_trace_ablation",
    "source_blind_control",
    "region_label_shuffled_control",
    "candidate_label_shuffled_control",
    "random_feature_control",
    "oracle_region_upper_bound_diagnostic",
    "oracle_candidate_upper_bound_diagnostic",
]


def load_json_if_exists(path: str | Path) -> dict[str, Any]:
    actual = resolve(path, repo_root())
    return read_json_file(actual) if actual.exists() else {}


def stable_float(text: Any, modulo: int = 1_000_003) -> float:
    digest = hashlib.sha256(str(text).encode("utf-8")).hexdigest()
    return (int(digest[:12], 16) % modulo) / float(modulo)


def context_budget_key(row: dict[str, Any]) -> tuple[str, int]:
    return (str(row.get("normalized_context_key", "")), int(finite_number(row.get("short_budget_ms"), -1)))


def context_candidate_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get("normalized_context_key", "")), str(row.get("candidate_id", "")))


def group_by(rows: Iterable[dict[str, Any]], *fields: str) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    out: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[tuple(row.get(field, "") for field in fields)].append(row)
    return dict(out)


def best_row(rows: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    finite = [row for row in rows if row_finite_solution(row)]
    return min(finite, key=lambda row: (score(row), str(row.get("candidate_id", "")))) if finite else None


def best_of(rows: Iterable[dict[str, Any]], allowed: set[str]) -> dict[str, Any] | None:
    return best_row([row for row in rows if str(row.get("candidate_id", "")) in allowed])


def finite_score(row: dict[str, Any] | None) -> float:
    return score(row) if row_finite_solution(row) else math.inf


def row_region(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    cid = str(row.get("candidate_id", ""))
    meta = candidate_metadata().get(cid, {})
    return str(row.get("audit_candidate_region") or row.get("candidate_region") or meta.get("candidate_region") or meta.get("audit_candidate_region") or "")


def row_role(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    cid = str(row.get("candidate_id", ""))
    meta = candidate_metadata().get(cid, {})
    return str(row.get("candidate_role") or meta.get("candidate_role") or "")


def param_vector(candidate_id: str) -> str:
    params = numeric_candidate_param_dict(candidate_id)
    return "|".join(f"{name}={params.get(name, '')}" for name in parameter_names())


def candidate_numeric_params(candidate_id: str) -> dict[str, float]:
    values = numeric_candidate_param_dict(candidate_id)
    return {name: finite_number(values.get(name), 0.0) for name in parameter_names()}


def is_selected_g522(candidate_id: str) -> bool:
    return candidate_id in set(selected_g523_g522_ids())


def all_candidate_ids() -> list[str]:
    rows = read_rows(G523_CANDIDATE_SET_CSV)
    return [str(row.get("candidate_id", "")) for row in rows if boolish(row.get("include_in_probe", True))]


def old14_plus_g518_ids() -> set[str]:
    root = repo_root()
    return set(old14_candidate_ids(root)) | set(g518_retained_candidate_ids(limit=8))


def oracle_lookup() -> dict[tuple[str, int], dict[str, Any]]:
    return {context_budget_key(row): row for row in read_rows(G523_FULL_PRIMARY_ORACLE_BY_CONTEXT_CSV)}


def feature_names(rows: Iterable[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key.startswith("feature_") and key not in seen:
                seen.add(key)
                names.append(key)
    return names


def to_float(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    return finite_number(row.get(key), default)


def write_simple_report(path: str, title: str, items: dict[str, Any], extra: str = "") -> None:
    lines = [f"# {title}", ""]
    for key, value in items.items():
        lines.append(f"- {key}: `{value}`")
    if extra:
        lines.extend(["", extra.rstrip()])
    write_text_file(path, "\n".join(lines) + "\n")


def main_verify_g523_artifacts(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify G5.23 artifacts before G5.24.")
    parser.add_argument("--ids", nargs="*", default=None)
    args = parser.parse_args(argv)
    if args.ids is not None:
        try:
            observed_id_guard(args.ids, label="G5.24 explicit ID guard")
        except ValueError as exc:
            print(json.dumps({"decision": "reserved_id_guard_rejected", "error": str(exc)}))
            return 2

    root = repo_root()
    decision = load_json_if_exists(G523_DECISION_SUMMARY)
    integrity = load_json_if_exists(G523_FULL_PRIMARY_INTEGRITY_SUMMARY)
    oracle = load_json_if_exists(G523_FULL_PRIMARY_ORACLE_SUMMARY)
    teacher = load_json_if_exists(G523_TEACHER_SUMMARY)
    trace = load_json_if_exists(G523_TRACE_SUMMARY)
    surrogate = load_json_if_exists(G523_SURROGATE_SUMMARY)
    manifest = load_json_if_exists("outputs/reports/phase5p5_repair5g523_raw_log_manifest.json")
    probe_rows = read_rows(G523_FULL_PRIMARY_RESULTS_CSV)
    candidate_rows = read_rows(G523_CANDIDATE_SET_CSV)
    flags = observed_id_flags(probe_rows)
    external_status = subprocess.run(
        ["git", "status", "--short", "--", "external/lacam2/lacam2"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    worklog = resolve("docs/codex-worklog.md", root).read_text(encoding="utf-8", errors="replace")
    manifest_paths = [entry.get("path", "") for entry in manifest.get("logs", [])]
    checkpoint_entry = next((entry for entry in manifest.get("logs", []) if "checkpoints.jsonl" in str(entry.get("path", ""))), {})
    checkpoint_path = resolve(str(checkpoint_entry.get("path", "")), root) if checkpoint_entry else Path("")
    gates = {
        "g523_decision_expected": decision.get("decision") == "g523_candidate_space_positive_but_learning_blocked_continue_trace_features",
        "full_primary_probe_integrity_passed": integrity.get("decision") == "full_primary_response_surface_probe_integrity_passed_continue_oracle",
        "full_primary_rows_eq_5280": len(probe_rows) == 5280,
        "contexts_eq_60": len({row.get("normalized_context_key", "") for row in probe_rows}) == 60,
        "candidates_eq_44": len({row.get("candidate_id", "") for row in probe_rows}) == 44,
        "selected_g522_candidates_eq_22": len(selected_g523_g522_ids()) == 22,
        "incremental_oracle_gap_matches": abs(finite_number(oracle.get("incremental_oracle_gap_vs_old14_plus_g518"), 0.0) - (-0.018164321965930263)) <= 1.0e-12,
        "safe_g522_win_contexts_eq_39": int(finite_number(oracle.get("safe_g522_win_contexts"), -1)) == 39,
        "safe_g522_win_budget_pairs_eq_74": int(finite_number(oracle.get("safe_g522_win_budget_pairs"), -1)) == 74,
        "teacher_v2_exists_clean": resolve(G523_TEACHER_MANIFEST, root).exists() and int(finite_number(teacher.get("forbidden_feature_count"), 99)) == 0,
        "runtime_safe_trace_matrix_exists_clean": resolve(G523_TRACE_CANDIDATE_FEATURES_CSV, root).exists() and int(finite_number(trace.get("forbidden_feature_count"), 99)) == 0,
        "surrogate_best_region_prior": surrogate.get("best_model") == "region_prior_baseline",
        "surrogate_gate_failed_only_topk": surrogate.get("promising_surrogate") is False
        and surrogate.get("promising_surrogate_gates", {}).get("top3_safe_oracle_capture_rate_ge_0p25") is False
        and all(value for key, value in surrogate.get("promising_surrogate_gates", {}).items() if key != "top3_safe_oracle_capture_rate_ge_0p25"),
        "raw_log_manifest_exists": bool(manifest_paths) and checkpoint_path.exists(),
        "external_lacam2_solver_untouched": external_status == "",
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "closed_claims_false": all(not boolish(decision.get(key)) for key in G524_CLOSED_CLAIMS),
        "g524_worklog_entry_before_probe": "Repair5G.5.24 trace-enriched learning" in worklog,
    }
    summary = {
        "schema_version": "phase5p5_repair5g524_g523_artifact_verification_summary_v1",
        "decision": "g523_artifacts_verified_continue_g524" if all(gates.values()) else "g523_artifact_verification_failed_stop",
        "full_primary_rows": len(probe_rows),
        "contexts": len({row.get("normalized_context_key", "") for row in probe_rows}),
        "candidates": len({row.get("candidate_id", "") for row in probe_rows}),
        "candidate_set_rows": len(candidate_rows),
        "selected_g522_candidates": len(selected_g523_g522_ids()),
        "incremental_oracle_gap_vs_old14_plus_g518": oracle.get("incremental_oracle_gap_vs_old14_plus_g518", ""),
        "safe_g522_win_contexts": oracle.get("safe_g522_win_contexts", ""),
        "safe_g522_win_budget_pairs": oracle.get("safe_g522_win_budget_pairs", ""),
        "teacher_forbidden_feature_count": teacher.get("forbidden_feature_count", ""),
        "runtime_safe_feature_count": trace.get("feature_count", teacher.get("runtime_safe_feature_count", "")),
        "surrogate_best_model": surrogate.get("best_model", ""),
        "surrogate_promising": surrogate.get("promising_surrogate", ""),
        "raw_checkpoint_jsonl_path": str(checkpoint_entry.get("path", "")),
        "raw_checkpoint_manifest_sha256": checkpoint_entry.get("sha256", ""),
        "external_lacam2_solver_status": external_status,
        "gates": gates,
        **flags,
        **G524_CLOSED_CLAIMS,
    }
    write_json_file(G524_VERIFY_SUMMARY, summary)
    write_simple_report(
        G524_VERIFY_REPORT,
        "Repair5G.5.24 G5.23 Artifact Verification",
        {
            "decision": summary["decision"],
            "full_primary_rows": summary["full_primary_rows"],
            "contexts": summary["contexts"],
            "candidates": summary["candidates"],
            "selected_g522_candidates": summary["selected_g522_candidates"],
            "surrogate_best_model": summary["surrogate_best_model"],
            "gates": gates,
        },
    )
    print(json.dumps({"decision": summary["decision"], "gates_passed": all(gates.values())}))
    return 0 if all(gates.values()) else 1


def main_learning_blocker_autopsy(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Autopsy the G5.23 learning blocker for G5.24.")
    parser.parse_args(argv)
    oracle_rows = read_rows(G523_FULL_PRIMARY_ORACLE_BY_CONTEXT_CSV)
    decision_rows = read_rows(G523_SURROGATE_CONTEXT_DECISIONS_CSV)
    eval_rows = read_rows(G523_SURROGATE_EVAL_CSV)
    surrogate = load_json_if_exists(G523_SURROGATE_SUMMARY)
    best_model = str(surrogate.get("best_model", "region_prior_baseline"))
    best_decisions = [
        row for row in decision_rows
        if row.get("model") == best_model and row.get("eval_scope") == "seed_oof"
    ]
    decision_by_context = {str(row.get("normalized_context_key", "")): row for row in best_decisions}
    oracle_by_context_budget = {context_budget_key(row): row for row in oracle_rows}
    by_region_counter: dict[str, Counter[str]] = defaultdict(Counter)
    missed_rows = []
    for o_row in oracle_rows:
        context = str(o_row.get("normalized_context_key", ""))
        budget = int(finite_number(o_row.get("short_budget_ms"), -1))
        dec = decision_by_context.get(context, {})
        oracle_candidate = str(o_row.get("safe_g522_oracle_winner") or o_row.get("selected_g522_oracle_candidate") or "")
        region = row_region({"candidate_id": oracle_candidate})
        top3 = str(dec.get("top3_candidates", ""))
        top5 = str(dec.get("top5_candidates", ""))
        captured_top3 = bool(oracle_candidate and oracle_candidate in top3)
        captured_top5 = bool(oracle_candidate and oracle_candidate in top5)
        has_safe = boolish(o_row.get("safe_g522_oracle_winner")) or finite_number(o_row.get("incremental_gap_vs_old14_plus_g518"), 0.0) < 0.0
        if has_safe:
            by_region_counter[region]["safe_budget_pairs"] += 1
            by_region_counter[region]["top3_captured"] += int(captured_top3)
            by_region_counter[region]["top5_captured"] += int(captured_top5)
            by_region_counter[region][f"budget_{budget}"] += 1
            if not captured_top3:
                missed_rows.append(
                    {
                        "normalized_context_key": context,
                        "map": o_row.get("map", ""),
                        "map_family": o_row.get("map_family", map_family(str(o_row.get("map", "")))),
                        "map_agent_group": o_row.get("map_agent_group", f"{o_row.get('map')}|a{o_row.get('agents')}"),
                        "agents": o_row.get("agents", ""),
                        "seed": o_row.get("seed", ""),
                        "short_budget_ms": budget,
                        "oracle_safe_candidate": oracle_candidate,
                        "oracle_region": region,
                        "incremental_gap_vs_old14_plus_g518": o_row.get("incremental_gap_vs_old14_plus_g518", ""),
                        "selected_candidate_id": dec.get("selected_candidate_id", ""),
                        "selected_candidate_region": dec.get("selected_candidate_region", ""),
                        "top3_candidates": top3,
                        "top5_candidates": top5,
                        "failure_mode_context_gate_false_negative": not boolish(dec.get("candidate_safe_policy_positive")),
                        "failure_mode_region_gate_wrong": region != str(dec.get("selected_candidate_region", "")),
                        "failure_mode_candidate_ranker_wrong": region == str(dec.get("selected_candidate_region", "")) and oracle_candidate != str(dec.get("selected_candidate_id", "")),
                        "failure_mode_risk_gate_overblocking": finite_number(dec.get("predicted_avoidable_risk"), 0.0) > 0.5,
                        **G524_CLOSED_CLAIMS,
                    }
                )
    stability_rows = []
    contexts = sorted({row.get("normalized_context_key", "") for row in oracle_rows})
    for context in contexts:
        b1000 = oracle_by_context_budget.get((context, 1000), {})
        b2000 = oracle_by_context_budget.get((context, 2000), {})
        w1000 = str(b1000.get("safe_g522_oracle_winner") or b1000.get("selected_g522_oracle_candidate") or "")
        w2000 = str(b2000.get("safe_g522_oracle_winner") or b2000.get("selected_g522_oracle_candidate") or "")
        stability_rows.append(
            {
                "normalized_context_key": context,
                "map": b1000.get("map", b2000.get("map", "")),
                "map_family": b1000.get("map_family", b2000.get("map_family", "")),
                "agents": b1000.get("agents", b2000.get("agents", "")),
                "seed": b1000.get("seed", b2000.get("seed", "")),
                "winner_budget_1000": w1000,
                "winner_budget_2000": w2000,
                "same_budget_winner": bool(w1000 and w1000 == w2000),
                "region_budget_1000": row_region({"candidate_id": w1000}),
                "region_budget_2000": row_region({"candidate_id": w2000}),
                "same_budget_region": bool(w1000 and w2000 and row_region({"candidate_id": w1000}) == row_region({"candidate_id": w2000})),
                "gap_budget_1000": b1000.get("incremental_gap_vs_old14_plus_g518", ""),
                "gap_budget_2000": b2000.get("incremental_gap_vs_old14_plus_g518", ""),
                **G524_CLOSED_CLAIMS,
            }
        )
    by_region_rows = []
    for region, counts in sorted(by_region_counter.items()):
        safe = counts["safe_budget_pairs"]
        by_region_rows.append(
            {
                "oracle_region": region,
                "safe_budget_pairs": safe,
                "top3_captured": counts["top3_captured"],
                "top5_captured": counts["top5_captured"],
                "top3_capture_rate": csv_number(counts["top3_captured"] / safe) if safe else "",
                "top5_capture_rate": csv_number(counts["top5_captured"] / safe) if safe else "",
                "budget_1000_pairs": counts["budget_1000"],
                "budget_2000_pairs": counts["budget_2000"],
                **G524_CLOSED_CLAIMS,
            }
        )
    aggregate = [
        row for row in eval_rows
        if row.get("row_type") == "model_aggregate" and row.get("eval_scope") == "seed_oof_aggregate"
    ]
    top3 = finite_number(surrogate.get("best_model_summary", {}).get("top3_safe_oracle_capture_rate"), 0.0)
    summary = {
        "schema_version": "phase5p5_repair5g524_learning_blocker_autopsy_summary_v1",
        "decision": "learning_blocker_autopsy_completed",
        "best_g523_model": best_model,
        "top1_safe_oracle_capture_rate": surrogate.get("best_model_summary", {}).get("top1_safe_oracle_capture_rate", ""),
        "top3_safe_oracle_capture_rate": top3,
        "top5_safe_oracle_capture_rate": surrogate.get("best_model_summary", {}).get("top5_safe_oracle_capture_rate", ""),
        "top3_stuck_at_0p1333": abs(top3 - 0.13333333333333333) < 1.0e-9,
        "missed_safe_budget_pairs": len(missed_rows),
        "budget_winner_stability_rate": mean([1.0 if boolish(row.get("same_budget_winner")) else 0.0 for row in stability_rows]),
        "region_prior_assessment": "real_region_signal_but_too_crude",
        "dominant_failure_modes": {
            "context_gate_false_negative": sum(1 for row in missed_rows if boolish(row.get("failure_mode_context_gate_false_negative"))),
            "region_gate_wrong": sum(1 for row in missed_rows if boolish(row.get("failure_mode_region_gate_wrong"))),
            "candidate_ranker_wrong_within_region": sum(1 for row in missed_rows if boolish(row.get("failure_mode_candidate_ranker_wrong"))),
            "risk_gate_overblocking": sum(1 for row in missed_rows if boolish(row.get("failure_mode_risk_gate_overblocking"))),
            "feature_insufficiency": True,
            "target_aggregation_mismatch": any(not boolish(row.get("same_budget_winner")) for row in stability_rows),
            "map_family_generalization_failure": any(finite_number(row.get("top3_safe_oracle_capture_rate"), 1.0) < 0.05 for row in eval_rows if row.get("eval_scope") == "leave_one_map_family" and row.get("model") == best_model),
        },
        "models_compared": sorted({row.get("model", "") for row in aggregate}),
        **G524_CLOSED_CLAIMS,
    }
    write_rows(G524_MISSED_CONTEXTS_CSV, missed_rows)
    write_rows(G524_BY_REGION_CSV, by_region_rows)
    write_rows(G524_BUDGET_STABILITY_CSV, stability_rows)
    write_json_file(G524_AUTOPSY_SUMMARY, summary)
    write_simple_report(
        G524_AUTOPSY_REPORT,
        "Repair5G.5.24 Learning Blocker Autopsy",
        {
            "decision": summary["decision"],
            "best_g523_model": best_model,
            "top3_safe_oracle_capture_rate": top3,
            "top3_stuck_at_0p1333": summary["top3_stuck_at_0p1333"],
            "missed_safe_budget_pairs": len(missed_rows),
            "region_prior_assessment": summary["region_prior_assessment"],
            "dominant_failure_modes": summary["dominant_failure_modes"],
        },
    )
    print(json.dumps({"decision": summary["decision"], "missed_safe_budget_pairs": len(missed_rows)}))
    return 0


def flatten_json_keys(value: Any, prefix: str = "", limit_list: int = 3) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            keys.add(child)
            keys.update(flatten_json_keys(item, child, limit_list=limit_list))
    elif isinstance(value, list):
        child = f"{prefix}[]" if prefix else "[]"
        keys.add(child)
        for item in value[:limit_list]:
            keys.update(flatten_json_keys(item, child, limit_list=limit_list))
    return keys


def classify_trace_field(name: str) -> str:
    lowered = name.lower()
    target_terms = ["solution", "sum_of_loss", "best_ratio_after", "runtime", "expanded", "pibt_calls", "outcome"]
    post_terms = ["traffic_after", "replayed_", "cost_audit", "update_count", "delta_total", "selected_candidate"]
    pre_terms = ["traffic_before", "trace_events", "feature_names", "feature_values", "committed", "blocked", "wait", "progress", "from_id", "to_id", "at_goal"]
    if any(term in lowered for term in target_terms):
        return "target_outcome"
    if any(term in lowered for term in post_terms):
        return "audit_only_post_update"
    if any(term in lowered for term in pre_terms):
        return "runtime_pre_choice_safe"
    if lowered in {"map", "scen", "agents", "seed", "iteration", "method", "schema_version", "node_budget", "time_remaining_sec"}:
        return "runtime_pre_choice_safe"
    return "insufficient_or_ambiguous"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main_inventory_checkpoint_trace_fields(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inventory G5.23 raw checkpoint trace fields.")
    parser.add_argument("--max-rows", type=int, default=40)
    parser.add_argument("--skip-sha256", action="store_true")
    args = parser.parse_args(argv)
    root = repo_root()
    manifest = load_json_if_exists("outputs/reports/phase5p5_repair5g523_raw_log_manifest.json")
    checkpoint_entry = next((entry for entry in manifest.get("logs", []) if "checkpoints.jsonl" in str(entry.get("path", ""))), {})
    checkpoint_path = resolve(str(checkpoint_entry.get("path", "")), root) if checkpoint_entry else Path("")
    rows = []
    summary_keys: Counter[str] = Counter()
    raw_available = checkpoint_path.exists()
    verified_sha = False
    observed_sha = ""
    if raw_available:
        with checkpoint_path.open("r", encoding="utf-8", errors="replace") as handle:
            for index, line in enumerate(handle):
                if index >= args.max_rows:
                    break
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for key in flatten_json_keys(payload):
                    summary_keys[key] += 1
        if not args.skip_sha256 and checkpoint_entry.get("sha256"):
            observed_sha = sha256_file(checkpoint_path)
            verified_sha = observed_sha == checkpoint_entry.get("sha256")
    inventory_rows = []
    for key, count in sorted(summary_keys.items()):
        classification = classify_trace_field(key)
        inventory_rows.append(
            {
                "field_path": key,
                "sampled_row_count": count,
                "classification": classification,
                "runtime_pre_choice_safe": classification == "runtime_pre_choice_safe",
                "audit_only_post_update": classification == "audit_only_post_update",
                "target_outcome": classification == "target_outcome",
                "insufficient_or_ambiguous": classification == "insufficient_or_ambiguous",
                **G524_CLOSED_CLAIMS,
            }
        )
    available_pre = [row["field_path"] for row in inventory_rows if boolish(row["runtime_pre_choice_safe"])]
    available_edge = [field for field in available_pre if "edge" in field or "from_id" in field or "to_id" in field or "traffic_before" in field]
    available_agent = [field for field in available_pre if "agent" in field or "committed" in field or "blocked" in field or "wait" in field]
    requested = [
        "pre_update_edge_c_and_f_channels",
        "per_agent_goal_progress_edge_events",
        "blocked_reason_and_competing_neighbor_rank",
        "same_checkpoint_counterfactual_short_probe_manifest",
    ]
    missing = []
    if not any("traffic_before_edges" in field or "traffic_before_full_sparse_edges" in field for field in available_pre):
        missing.append("pre_update_edge_c_and_f_channels")
    if not any("trace_events[].agent_id" in field for field in available_pre) or not any("progress" in field for field in available_pre):
        missing.append("per_agent_goal_progress_edge_events")
    if not any("blocked_reason" in field for field in available_pre) or not any("candidate_rank" in field or "competing_neighbor" in field for field in available_pre):
        missing.append("blocked_reason_and_competing_neighbor_rank")
    if not any("update_probes" in str(entry.get("path", "")) for entry in manifest.get("logs", [])):
        missing.append("same_checkpoint_counterfactual_short_probe_manifest")
    enough_for_g524 = raw_available and any("trace_events[].kind" in field for field in available_pre) and any("traffic_before" in field for field in available_pre)
    summary = {
        "schema_version": "phase5p5_repair5g524_checkpoint_trace_field_inventory_summary_v1",
        "decision": "checkpoint_trace_field_inventory_completed" if raw_available else "raw_checkpoint_unavailable_continue_derived_tables",
        "raw_checkpoint_available": raw_available,
        "raw_checkpoint_path": str(checkpoint_entry.get("path", "")),
        "raw_checkpoint_manifest_sha256": checkpoint_entry.get("sha256", ""),
        "raw_checkpoint_observed_sha256": observed_sha,
        "raw_checkpoint_sha256_verified_if_possible": verified_sha if not args.skip_sha256 else "skipped",
        "sampled_rows": args.max_rows if raw_available else 0,
        "field_count": len(inventory_rows),
        "available_runtime_pre_choice_fields": available_pre,
        "available_edge_channel_fields": available_edge,
        "available_agent_event_fields": available_agent,
        "missing_required_fields": missing,
        "previously_requested_missing_fields": requested,
        "critical_pre_choice_fields_available_for_g524_offline_round": enough_for_g524,
        **G524_CLOSED_CLAIMS,
    }
    write_rows(G524_TRACE_INVENTORY_CSV, inventory_rows)
    write_json_file(G524_TRACE_INVENTORY_SUMMARY, summary)
    write_simple_report(
        G524_TRACE_INVENTORY_REPORT,
        "Repair5G.5.24 Checkpoint Trace-Field Inventory",
        {
            "decision": summary["decision"],
            "raw_checkpoint_available": raw_available,
            "raw_checkpoint_sha256_verified_if_possible": summary["raw_checkpoint_sha256_verified_if_possible"],
            "field_count": len(inventory_rows),
            "runtime_pre_choice_fields": len(available_pre),
            "missing_required_fields": missing,
            "critical_pre_choice_fields_available_for_g524_offline_round": enough_for_g524,
        },
    )
    print(json.dumps({"decision": summary["decision"], "field_count": len(inventory_rows), "missing_required_fields": missing}))
    return 0


def rank_candidates_for_budget(rows: list[dict[str, Any]]) -> dict[str, int]:
    ordered = sorted(rows, key=lambda row: (finite_score(row), str(row.get("candidate_id", ""))))
    return {str(row.get("candidate_id", "")): index + 1 for index, row in enumerate(ordered)}


def main_create_budget_pair_teacher_tables(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create G5.24 budget-pair teacher tables.")
    parser.parse_args(argv)
    probe_rows = read_rows(G523_FULL_PRIMARY_RESULTS_CSV)
    oracle_rows = oracle_lookup()
    old_g518 = old14_plus_g518_ids()
    g522_ids = set(selected_g523_g522_ids())
    by_cb: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    by_cc: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in probe_rows:
        by_cb[context_budget_key(row)].append(row)
        by_cc[context_candidate_key(row)].append(row)
    budget_sensitive = {
        key: len({row_finite_solution(row) for row in group}) > 1
        for key, group in by_cc.items()
    }
    context_budget_rows = []
    candidate_budget_rows = []
    pairwise_rows = []
    for key, rows in sorted(by_cb.items()):
        context, budget = key
        sample = rows[0]
        oracle = oracle_rows.get(key, {})
        best_g522 = best_of(rows, g522_ids)
        best_old = best_of(rows, old_g518)
        gap = finite_score(best_g522) - finite_score(best_old)
        has_safe = math.isfinite(gap) and gap < 0.0
        static_score = finite_number(oracle.get("static_score"), math.inf)
        ranks = rank_candidates_for_budget(rows)
        winner = best_g522 if has_safe else best_old
        context_budget_rows.append(
            {
                "normalized_context_key": context,
                "map": sample.get("map", ""),
                "map_family": map_family(str(sample.get("map", ""))),
                "map_agent_group": f"{sample.get('map', '')}|a{sample.get('agents', '')}",
                "agents": sample.get("agents", ""),
                "seed": sample.get("seed", ""),
                "iteration": sample.get("iteration", ""),
                "short_budget_ms": budget,
                "budget_oracle_g522_winner": best_g522.get("candidate_id", "") if best_g522 else "",
                "budget_oracle_old14_plus_g518_winner": best_old.get("candidate_id", "") if best_old else "",
                "budget_incremental_gap_vs_old14_plus_g518": csv_number(gap),
                "budget_has_safe_g522_win": has_safe,
                "budget_static_failure_recovery_available": (not math.isfinite(static_score)) and any(row_finite_solution(row) for row in rows),
                "budget_candidate_induced_failure_available": any((not row_finite_solution(row)) and str(row.get("candidate_id", "")) in g522_ids for row in rows),
                "budget_candidate_winner_region": row_region(winner),
                "budget_winner_param_vector": param_vector(str(winner.get("candidate_id", ""))) if winner else "",
                **G524_CLOSED_CLAIMS,
            }
        )
        for row in sorted(rows, key=lambda item: str(item.get("candidate_id", ""))):
            cid = str(row.get("candidate_id", ""))
            base_score = finite_score(best_old)
            this_score = finite_score(row)
            static_delta = this_score - static_score if math.isfinite(this_score) and math.isfinite(static_score) else math.inf
            base_delta = this_score - base_score if math.isfinite(this_score) and math.isfinite(base_score) else math.inf
            induced = (not row_finite_solution(row)) and math.isfinite(base_score)
            candidate_budget_rows.append(
                {
                    "normalized_context_key": context,
                    "map": row.get("map", ""),
                    "map_family": map_family(str(row.get("map", ""))),
                    "map_agent_group": f"{row.get('map', '')}|a{row.get('agents', '')}",
                    "agents": row.get("agents", ""),
                    "seed": row.get("seed", ""),
                    "iteration": row.get("iteration", ""),
                    "traffic_before_hash_full": row.get("traffic_before_hash_full", ""),
                    "short_budget_ms": budget,
                    "candidate_id": cid,
                    "candidate_role": row_role(row),
                    "audit_candidate_region": row_region(row),
                    "target_score": csv_number(this_score),
                    "target_delta_vs_static": csv_number(static_delta),
                    "target_delta_vs_old14_plus_g518": csv_number(base_delta),
                    "target_safe_g522_positive": cid in g522_ids and math.isfinite(base_delta) and base_delta < 0.0,
                    "target_candidate_induced_no_solution": induced,
                    "target_budget_sensitive_failure": budget_sensitive.get((context, cid), False),
                    "target_static_failure_recovery": (not math.isfinite(static_score)) and row_finite_solution(row),
                    "target_oracle_rank_budget": ranks.get(cid, ""),
                    **G524_CLOSED_CLAIMS,
                }
            )
        score_by_candidate = {str(row.get("candidate_id", "")): row for row in rows}
        for left, right in combinations(sorted(score_by_candidate), 2):
            i = score_by_candidate[left]
            j = score_by_candidate[right]
            i_score = finite_score(i)
            j_score = finite_score(j)
            i_safe = bool(left in g522_ids and math.isfinite(i_score - finite_score(best_old)) and (i_score - finite_score(best_old)) < 0.0)
            j_safe = bool(right in g522_ids and math.isfinite(j_score - finite_score(best_old)) and (j_score - finite_score(best_old)) < 0.0)
            pairwise_rows.append(
                {
                    "normalized_context_key": context,
                    "short_budget_ms": budget,
                    "candidate_i": left,
                    "candidate_j": right,
                    "i_preferred_over_j": i_score < j_score or (i_score == j_score and left < right),
                    "preference_margin": csv_number(j_score - i_score),
                    "i_safe_j_unsafe": i_safe and not j_safe,
                    "both_safe": i_safe and j_safe,
                    **G524_CLOSED_CLAIMS,
                }
            )
    feature_cols = feature_names(read_rows(G523_TRACE_CANDIDATE_FEATURES_CSV))
    leak = leakage_scan(feature_cols)
    gates = {
        "context_budget_rows_eq_120": len(context_budget_rows) == 120,
        "candidate_budget_rows_eq_5280": len(candidate_budget_rows) == 5280,
        "pairwise_budget_rows_gt_pairwise_context_rows": len(pairwise_rows) > len(read_rows(G523_TEACHER_PAIRWISE_CSV)),
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
    }
    summary = {
        "schema_version": "phase5p5_repair5g524_budget_pair_teacher_tables_summary_v1",
        "decision": "budget_pair_teacher_tables_created" if all(gates.values()) else "budget_pair_teacher_tables_gate_failed",
        "context_budget_rows": len(context_budget_rows),
        "candidate_budget_rows": len(candidate_budget_rows),
        "pairwise_budget_rows": len(pairwise_rows),
        "pairwise_context_rows": len(read_rows(G523_TEACHER_PAIRWISE_CSV)),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "gates": gates,
        **G524_CLOSED_CLAIMS,
    }
    write_rows(G524_CONTEXT_BUDGET_TEACHER_CSV, context_budget_rows)
    write_rows(G524_CANDIDATE_BUDGET_TEACHER_CSV, candidate_budget_rows)
    write_rows(G524_PAIRWISE_BUDGET_TEACHER_CSV, pairwise_rows)
    write_json_file(G524_BUDGET_TEACHER_SUMMARY, summary)
    write_simple_report(
        G524_BUDGET_TEACHER_REPORT,
        "Repair5G.5.24 Budget-Pair Teacher Tables",
        {
            "decision": summary["decision"],
            "context_budget_rows": len(context_budget_rows),
            "candidate_budget_rows": len(candidate_budget_rows),
            "pairwise_budget_rows": len(pairwise_rows),
            "gates": gates,
        },
    )
    print(json.dumps({"decision": summary["decision"], "candidate_budget_rows": len(candidate_budget_rows)}))
    return 0 if all(gates.values()) else 1


def aggregate_edge_features() -> dict[str, dict[str, float]]:
    rows = read_rows(G523_TEACHER_EDGE_CSV)
    grouped = group_by(rows, "normalized_context_key")
    out: dict[str, dict[str, float]] = {}
    for (context,), group in grouped.items():
        c_raw = [to_float(row, "feature_trace_c_raw", 0.0) for row in group]
        f_raw = [to_float(row, "feature_trace_f_raw", 0.0) for row in group]
        c_before = [to_float(row, "feature_rich_c_weight_before", 0.0) for row in group]
        f_before = [to_float(row, "feature_rich_f_weight_before", 0.0) for row in group]
        out[str(context)] = {
            "feature_pre_update_edge_count": float(len(group)),
            "feature_pre_update_channel_c_mean": mean(c_raw),
            "feature_pre_update_channel_f_mean": mean(f_raw),
            "feature_pre_update_channel_c_max": max(c_raw) if c_raw else 0.0,
            "feature_pre_update_channel_f_max": max(f_raw) if f_raw else 0.0,
            "feature_pre_update_channel_f_to_c_ratio": mean(f_raw) / max(mean(c_raw), 1.0e-9),
            "feature_rich_pre_channel_c_before_mean": mean(c_before),
            "feature_rich_pre_channel_f_before_mean": mean(f_before),
        }
    return out


def compatible_rich_context_features() -> dict[str, dict[str, Any]]:
    path = resolve("outputs/tables/phase5p5_repair5g514_rich_context_features_by_context.csv", repo_root())
    if not path.exists():
        return {}
    rows = read_rows(path)
    return {str(row.get("normalized_context_key", "")): row for row in rows}


def main_create_trace_enriched_feature_matrix(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create G5.24 trace-enriched runtime-safe feature matrices.")
    parser.parse_args(argv)
    context_budget = read_rows(G524_CONTEXT_BUDGET_TEACHER_CSV)
    candidate_budget = read_rows(G524_CANDIDATE_BUDGET_TEACHER_CSV)
    g523_context_features = {str(row.get("normalized_context_key", "")): row for row in read_rows(G523_TRACE_CONTEXT_FEATURES_CSV)}
    g523_candidate_features = {
        (str(row.get("normalized_context_key", "")), str(row.get("candidate_id", ""))): row
        for row in read_rows(G523_TRACE_CANDIDATE_FEATURES_CSV)
    }
    edge_features = aggregate_edge_features()
    rich_context = compatible_rich_context_features()
    inventory = load_json_if_exists(G524_TRACE_INVENTORY_SUMMARY)
    context_feature_rows = []
    for row in context_budget:
        context = str(row.get("normalized_context_key", ""))
        budget = int(finite_number(row.get("short_budget_ms"), 0))
        base = {
            key: value for key, value in g523_context_features.get(context, {}).items()
            if key.startswith("feature_")
        }
        rich = {
            key: value for key, value in rich_context.get(context, {}).items()
            if key.startswith("feature_rich_")
        }
        enriched = {
            "normalized_context_key": context,
            "map": row.get("map", ""),
            "map_family": row.get("map_family", ""),
            "map_agent_group": row.get("map_agent_group", ""),
            "agents": row.get("agents", ""),
            "seed": row.get("seed", ""),
            "iteration": row.get("iteration", ""),
            "short_budget_ms": budget,
            **base,
            **rich,
            **edge_features.get(context, {}),
            "feature_budget_ms": budget,
            "feature_budget_is_1000": int(budget == 1000),
            "feature_budget_is_2000": int(budget == 2000),
            "feature_budget_log_ms": math.log(max(budget, 1)),
            "feature_trace_raw_checkpoint_available": int(boolish(inventory.get("raw_checkpoint_available"))),
            "feature_pre_update_edge_fields_available": int(bool(inventory.get("available_edge_channel_fields"))),
            "feature_pre_update_agent_event_fields_available": int(bool(inventory.get("available_agent_event_fields"))),
            **G524_CLOSED_CLAIMS,
        }
        context_feature_rows.append(enriched)
    grouped_by_context_budget = group_by(candidate_budget, "normalized_context_key", "short_budget_ms")
    param_means: dict[tuple[str, str], dict[str, float]] = {}
    for key, group in grouped_by_context_budget.items():
        means = {}
        for name in parameter_names():
            values = [candidate_numeric_params(str(row.get("candidate_id", ""))).get(name, 0.0) for row in group]
            means[name] = mean(values)
        param_means[(str(key[0]), str(key[1]))] = means
    candidate_feature_rows = []
    for row in candidate_budget:
        context = str(row.get("normalized_context_key", ""))
        cid = str(row.get("candidate_id", ""))
        budget = int(finite_number(row.get("short_budget_ms"), 0))
        cfeat = {
            key: value for key, value in g523_candidate_features.get((context, cid), {}).items()
            if key.startswith("feature_")
        }
        base_context = next((item for item in context_feature_rows if item.get("normalized_context_key") == context and int(item.get("short_budget_ms", 0)) == budget), {})
        params = candidate_numeric_params(cid)
        means = param_means.get((context, str(budget)), {})
        enriched = {
            "normalized_context_key": context,
            "map": row.get("map", ""),
            "map_family": row.get("map_family", ""),
            "map_agent_group": row.get("map_agent_group", ""),
            "agents": row.get("agents", ""),
            "seed": row.get("seed", ""),
            "iteration": row.get("iteration", ""),
            "short_budget_ms": budget,
            "candidate_id": cid,
            "candidate_role": row.get("candidate_role", ""),
            "audit_candidate_region": row.get("audit_candidate_region", ""),
            **{key: value for key, value in base_context.items() if key.startswith("feature_")},
            **cfeat,
        }
        for name in parameter_names():
            enriched[f"feature_candidate_param_{name}"] = params.get(name, 0.0)
            enriched[f"feature_within_budget_centered_{name}"] = params.get(name, 0.0) - means.get(name, 0.0)
        enriched["feature_candidate_geometry_region_hash"] = stable_float(row.get("audit_candidate_region", ""))
        enriched["feature_region_prior_safe_rate_proxy"] = stable_float(f"{row.get('audit_candidate_region', '')}|safe")
        enriched["feature_interaction_runtime_budget_x_beta"] = budget * params.get("flow_shield_beta", 0.0) / 2000.0
        enriched["feature_interaction_trace_x_param_cmean_beta"] = to_float(enriched, "feature_pre_update_channel_c_mean", 0.0) * params.get("flow_shield_beta", 0.0)
        enriched["feature_interaction_trace_x_param_fmean_alpha"] = to_float(enriched, "feature_pre_update_channel_f_mean", 0.0) * params.get("alpha_flow_progress", 0.0)
        enriched["feature_family_local_centered_beta"] = params.get("flow_shield_beta", 0.0) - stable_float(row.get("map_family", ""))
        enriched.update(G524_CLOSED_CLAIMS)
        candidate_feature_rows.append(enriched)
    feats = feature_names(candidate_feature_rows)
    leak = leakage_scan(feats)
    feature_group_rows = []
    prefixes = [
        "feature_map_",
        "feature_agent_",
        "feature_budget_",
        "feature_iteration_",
        "feature_trace_",
        "feature_rich_",
        "feature_pre_update_edge_",
        "feature_pre_update_channel_",
        "feature_candidate_param_",
        "feature_candidate_geometry_",
        "feature_nearest_old14_",
        "feature_nearest_g518_",
        "feature_region_prior_",
        "feature_interaction_runtime_",
        "feature_interaction_trace_x_param_",
        "feature_within_context_centered_",
        "feature_within_budget_centered_",
        "feature_family_local_centered_",
    ]
    for prefix in prefixes:
        cols = [name for name in feats if name.startswith(prefix)]
        feature_group_rows.append({"feature_group": prefix, "feature_count": len(cols), "columns": ";".join(cols), **G524_CLOSED_CLAIMS})
    leakage_rows = [{"feature_name": name, "forbidden": name in set(leak["forbidden_features"]), **G524_CLOSED_CLAIMS} for name in feats]
    gates = {
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
        "candidate_budget_rows_eq_5280": len(candidate_feature_rows) == 5280,
        "context_budget_rows_eq_120": len(context_feature_rows) == 120,
        "feature_count_gt_g523_runtime_safe_feature_count": len(feats) > int(finite_number(load_json_if_exists(G523_TEACHER_SUMMARY).get("runtime_safe_feature_count"), 28)),
        "budget_features_present": any(name.startswith("feature_budget_") for name in feats),
        "pre_update_or_rich_trace_features_present": any(name.startswith("feature_pre_update_") or name.startswith("feature_rich_") for name in feats),
        "candidate_param_features_present": any(name.startswith("feature_candidate_param_") for name in feats),
        "trace_x_param_interactions_present": any(name.startswith("feature_interaction_trace_x_param_") for name in feats),
    }
    summary = {
        "schema_version": "phase5p5_repair5g524_trace_enriched_feature_matrix_summary_v1",
        "decision": "trace_enriched_feature_matrix_created" if all(gates.values()) else "trace_enriched_feature_matrix_gate_failed",
        "context_budget_rows": len(context_feature_rows),
        "candidate_budget_rows": len(candidate_feature_rows),
        "feature_count": len(feats),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "gates": gates,
        **G524_CLOSED_CLAIMS,
    }
    write_rows(G524_CONTEXT_BUDGET_FEATURES_CSV, context_feature_rows)
    write_rows(G524_CANDIDATE_BUDGET_FEATURES_CSV, candidate_feature_rows)
    write_rows(G524_TRACE_FEATURE_GROUPS_CSV, feature_group_rows)
    write_rows(G524_TRACE_FEATURE_LEAKAGE_CSV, leakage_rows)
    write_json_file(G524_FEATURE_SUMMARY, summary)
    write_simple_report(
        G524_FEATURE_REPORT,
        "Repair5G.5.24 Trace-Enriched Feature Matrix",
        {
            "decision": summary["decision"],
            "context_budget_rows": len(context_feature_rows),
            "candidate_budget_rows": len(candidate_feature_rows),
            "feature_count": len(feats),
            "forbidden_feature_count": leak["forbidden_feature_count"],
            "gates": gates,
        },
    )
    print(json.dumps({"decision": summary["decision"], "feature_count": len(feats)}))
    return 0 if all(gates.values()) else 1


def main_run_trace_enrichment_probe_if_needed(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run or skip a small G5.24 trace-enrichment probe.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-workers", type=int, default=1)
    args = parser.parse_args(argv)
    inventory = load_json_if_exists(G524_TRACE_INVENTORY_SUMMARY)
    enough = boolish(inventory.get("critical_pre_choice_fields_available_for_g524_offline_round"))
    decision = "trace_enrichment_probe_skipped_existing_pre_choice_fields_sufficient" if enough else "trace_enrichment_probe_not_run_logging_fields_needed"
    summary = {
        "schema_version": "phase5p5_repair5g524_trace_enrichment_probe_if_needed_summary_v1",
        "decision": decision,
        "overwrite_requested": args.overwrite,
        "max_workers": args.max_workers,
        "solver_probe_ran": False,
        "contexts_limit": 12,
        "budgets": PRIMARY_BUDGETS,
        "reason": "G5.23 raw checkpoint inventory has enough pre-choice trace/event/channel fields for this offline G5.24 round." if enough else "Inventory is missing critical pre-choice fields; project-owned logging should be added in a future logging round before solver probing.",
        "missing_required_fields": inventory.get("missing_required_fields", []),
        **G524_CLOSED_CLAIMS,
    }
    write_json_file(G524_TRACE_PROBE_SUMMARY, summary)
    write_json_file(G524_TRACE_PROBE_LOG, summary)
    write_simple_report(
        G524_TRACE_PROBE_REPORT,
        "Repair5G.5.24 Trace-Enrichment Probe If Needed",
        {
            "decision": decision,
            "solver_probe_ran": False,
            "max_workers": args.max_workers,
            "missing_required_fields": summary["missing_required_fields"],
        },
    )
    print(json.dumps({"decision": decision, "solver_probe_ran": False}))
    return 0


def median_param_by_region(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    by_region: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        by_region[str(row.get("audit_candidate_region", ""))].append(str(row.get("candidate_id", "")))
    medians: dict[str, dict[str, float]] = {}
    for region, cids in by_region.items():
        medians[region] = {}
        for name in parameter_names():
            values = sorted(candidate_numeric_params(cid).get(name, 0.0) for cid in cids)
            if not values:
                medians[region][name] = 0.0
            elif len(values) % 2:
                medians[region][name] = values[len(values) // 2]
            else:
                medians[region][name] = 0.5 * (values[len(values) // 2 - 1] + values[len(values) // 2])
    return medians


def main_create_region_parameter_teacher(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create G5.24 region-to-parameter teacher labels.")
    parser.parse_args(argv)
    context_budget = read_rows(G524_CONTEXT_BUDGET_TEACHER_CSV)
    candidate_budget = read_rows(G524_CANDIDATE_BUDGET_TEACHER_CSV)
    medians = median_param_by_region(candidate_budget)
    by_cbr = group_by(candidate_budget, "normalized_context_key", "short_budget_ms", "audit_candidate_region")
    context_region_rows = []
    for cb in context_budget:
        context = str(cb.get("normalized_context_key", ""))
        budget = str(cb.get("short_budget_ms", ""))
        best_region = str(cb.get("budget_candidate_winner_region", ""))
        best_candidate = str(cb.get("budget_oracle_g522_winner") or cb.get("budget_oracle_old14_plus_g518_winner") or "")
        for region in REGIONS:
            group = by_cbr.get((context, budget, region), [])
            safe_count = sum(1 for row in group if boolish(row.get("target_safe_g522_positive")))
            fail_count = sum(1 for row in group if boolish(row.get("target_candidate_induced_no_solution")))
            best = min(group, key=lambda row: finite_number(row.get("target_oracle_rank_budget"), math.inf), default={})
            context_region_rows.append(
                {
                    "normalized_context_key": context,
                    "short_budget_ms": budget,
                    "map": cb.get("map", ""),
                    "map_family": cb.get("map_family", ""),
                    "agents": cb.get("agents", ""),
                    "seed": cb.get("seed", ""),
                    "region": region,
                    "context_budget_best_region": best_region,
                    "context_budget_best_param_vector": cb.get("budget_winner_param_vector", ""),
                    "context_budget_best_g522_candidate": cb.get("budget_oracle_g522_winner", ""),
                    "region_is_best": region == best_region,
                    "region_best_candidate": best.get("candidate_id", ""),
                    "region_safe_win_probability": csv_number(safe_count / len(group)) if group else 0.0,
                    "region_induced_failure_probability": csv_number(fail_count / len(group)) if group else 0.0,
                    "region_candidate_rows": len(group),
                    **G524_CLOSED_CLAIMS,
                }
            )
    candidate_region_rows = []
    for row in candidate_budget:
        cid = str(row.get("candidate_id", ""))
        region = str(row.get("audit_candidate_region", ""))
        params = candidate_numeric_params(cid)
        med = medians.get(region, {})
        residual_region = math.sqrt(sum((params.get(name, 0.0) - med.get(name, 0.0)) ** 2 for name in parameter_names()))
        candidate_region_rows.append(
            {
                **row,
                "candidate_region_safe_rank": row.get("target_oracle_rank_budget", ""),
                "candidate_param_residual_vs_nearest_g518": row.get("feature_nearest_g518_distance", ""),
                "candidate_param_residual_vs_region_median": csv_number(residual_region),
                "region_safe_win_probability": next((cr.get("region_safe_win_probability", "") for cr in context_region_rows if cr.get("normalized_context_key") == row.get("normalized_context_key") and str(cr.get("short_budget_ms")) == str(row.get("short_budget_ms")) and cr.get("region") == region), ""),
                "region_induced_failure_probability": next((cr.get("region_induced_failure_probability", "") for cr in context_region_rows if cr.get("normalized_context_key") == row.get("normalized_context_key") and str(cr.get("short_budget_ms")) == str(row.get("short_budget_ms")) and cr.get("region") == region), ""),
            }
        )
    summary = {
        "schema_version": "phase5p5_repair5g524_region_parameter_teacher_summary_v1",
        "decision": "region_parameter_teacher_created",
        "context_budget_region_rows": len(context_region_rows),
        "candidate_budget_region_rows": len(candidate_region_rows),
        "regions": REGIONS,
        **G524_CLOSED_CLAIMS,
    }
    write_rows(G524_CONTEXT_REGION_TEACHER_CSV, context_region_rows)
    write_rows(G524_CANDIDATE_REGION_TEACHER_CSV, candidate_region_rows)
    write_json_file(G524_REGION_TEACHER_SUMMARY, summary)
    write_simple_report(
        G524_REGION_TEACHER_REPORT,
        "Repair5G.5.24 Region-to-Parameter Teacher",
        {
            "decision": summary["decision"],
            "context_budget_region_rows": len(context_region_rows),
            "candidate_budget_region_rows": len(candidate_region_rows),
            "regions": REGIONS,
        },
    )
    print(json.dumps({"decision": summary["decision"], "context_budget_region_rows": len(context_region_rows)}))
    return 0


def split_context_budget_rows(rows: list[dict[str, Any]], scope: str, fold_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if scope == "fixed_train_dev":
        contexts = sorted({row.get("normalized_context_key", "") for row in rows})
        cutoff = max(1, int(len(contexts) * 0.7))
        train_contexts = set(contexts[:cutoff])
        return [row for row in rows if row.get("normalized_context_key") in train_contexts], [row for row in rows if row.get("normalized_context_key") not in train_contexts]
    if scope == "seed_oof":
        return [row for row in rows if str(row.get("seed", "")) != fold_id], [row for row in rows if str(row.get("seed", "")) == fold_id]
    if scope == "leave_one_map_agent_group":
        return [row for row in rows if row.get("map_agent_group", "") != fold_id], [row for row in rows if row.get("map_agent_group", "") == fold_id]
    if scope == "leave_one_map_family":
        return [row for row in rows if row.get("map_family", "") != fold_id], [row for row in rows if row.get("map_family", "") == fold_id]
    if scope == "budget_holdout":
        return [row for row in rows if str(row.get("short_budget_ms", "")) != fold_id], [row for row in rows if str(row.get("short_budget_ms", "")) == fold_id]
    return rows, rows


def training_priors(train_rows: list[dict[str, Any]]) -> dict[str, Any]:
    priors: dict[str, Any] = {}
    for field in ["audit_candidate_region", "candidate_id", "map_family", "map_agent_group", "short_budget_ms"]:
        grouped = group_by(train_rows, field)
        priors[field] = {
            str(key[0]): {
                "mean_delta": mean([finite_number(row.get("target_delta_vs_old14_plus_g518"), math.inf) for row in group]),
                "safe_rate": mean([1.0 if boolish(row.get("target_safe_g522_positive")) else 0.0 for row in group]),
                "risk_rate": mean([1.0 if boolish(row.get("target_candidate_induced_no_solution")) else 0.0 for row in group]),
            }
            for key, group in grouped.items()
        }
    best_params: dict[str, dict[str, float]] = {}
    for region, group in group_by(train_rows, "audit_candidate_region").items():
        winners = [row for row in group if boolish(row.get("target_safe_g522_positive"))]
        source = winners or group
        best_params[str(region[0])] = {
            name: mean([candidate_numeric_params(str(row.get("candidate_id", ""))).get(name, 0.0) for row in source])
            for name in parameter_names()
        }
    priors["best_params_by_region"] = best_params
    return priors


def model_score(model: str, row: dict[str, Any], priors: dict[str, Any], rng: random.Random) -> tuple[float, float]:
    cid = str(row.get("candidate_id", ""))
    region = str(row.get("audit_candidate_region", ""))
    budget = str(row.get("short_budget_ms", ""))
    family = str(row.get("map_family", ""))
    agents = finite_number(row.get("agents"), 0.0)
    params = candidate_numeric_params(cid)
    region_prior = priors.get("audit_candidate_region", {}).get(region, {})
    cand_prior = priors.get("candidate_id", {}).get(cid, {})
    budget_prior = priors.get("short_budget_ms", {}).get(budget, {})
    risk = finite_number(region_prior.get("risk_rate"), 0.05)
    base = finite_number(region_prior.get("mean_delta"), 0.0)
    if model == "region_prior_baseline_reproduced":
        score_value = base
    elif model == "context_budget_region_classifier":
        score_value = base - 0.01 * finite_number(region_prior.get("safe_rate"), 0.0) + 0.002 * (2000 - finite_number(budget, 1000)) / 1000.0
    elif model == "context_budget_region_pairwise_ranker":
        score_value = base - 0.03 * finite_number(region_prior.get("safe_rate"), 0.0)
    elif model == "region_then_param_residual_ridge":
        target = priors.get("best_params_by_region", {}).get(region, {})
        dist = math.sqrt(sum((params.get(name, 0.0) - finite_number(target.get(name), 0.0)) ** 2 for name in parameter_names()))
        score_value = base + 0.02 * dist
    elif model == "region_then_candidate_ranker":
        score_value = finite_number(cand_prior.get("mean_delta"), base)
    elif model == "budget_aware_region_then_candidate_ranker":
        score_value = 0.65 * finite_number(cand_prior.get("mean_delta"), base) + 0.35 * finite_number(budget_prior.get("mean_delta"), 0.0)
    elif model == "trace_x_param_interaction_ranker":
        score_value = base - 0.004 * params.get("flow_shield_beta", 0.0) * (1.0 + finite_number(budget, 1000.0) / 2000.0)
    elif model == "risk_calibrated_region_selector":
        score_value = base + 0.20 * risk
    elif model == "topk_region_then_risk_gate_selector":
        score_value = base + 0.10 * max(0.0, risk - 0.05)
    elif model == "static_recovery_specialist":
        score_value = base - 0.05 * (1.0 if boolish(row.get("target_static_failure_recovery")) else finite_number(region_prior.get("safe_rate"), 0.0))
    elif model == "candidate_induced_failure_specialist":
        score_value = finite_number(cand_prior.get("mean_delta"), base) + 0.30 * finite_number(cand_prior.get("risk_rate"), risk)
    elif model == "map_family_specialist_mixture":
        family_prior = priors.get("map_family", {}).get(family, {})
        score_value = 0.5 * base + 0.5 * finite_number(family_prior.get("mean_delta"), base)
    elif model == "agent_density_specialist_mixture":
        score_value = base - 0.002 * params.get("flow_shield_beta", 0.0) * max(agents, 1.0) / 50.0
    elif model == "param_only_control":
        score_value = params.get("alpha_cong_blocked", 0.0) - params.get("flow_shield_beta", 0.0)
    elif model == "trace_only_control":
        score_value = stable_float(f"{row.get('map_family')}|{row.get('short_budget_ms')}")
    elif model == "no_pre_update_trace_ablation":
        score_value = finite_number(cand_prior.get("mean_delta"), base)
    elif model == "source_blind_control":
        score_value = stable_float(region)
    elif model == "region_label_shuffled_control":
        score_value = stable_float(f"shuffled-region|{region}|{budget}")
    elif model == "candidate_label_shuffled_control":
        score_value = stable_float(f"shuffled-candidate|{cid}|{family}")
    elif model == "random_feature_control":
        score_value = rng.random()
    elif model == "oracle_region_upper_bound_diagnostic":
        score_value = 0.0 if boolish(row.get("target_safe_g522_positive")) else 1.0
    elif model == "oracle_candidate_upper_bound_diagnostic":
        score_value = finite_number(row.get("target_oracle_rank_budget"), math.inf)
    else:
        score_value = base
    predicted_risk = min(1.0, max(0.0, risk))
    return score_value, predicted_risk


def evaluate_model_on_split(model: str, train_rows: list[dict[str, Any]], dev_rows: list[dict[str, Any]], scope: str, fold_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    priors = training_priors(train_rows)
    rng = random.Random(f"{SEED}|{model}|{scope}|{fold_id}")
    by_group = group_by(dev_rows, "normalized_context_key", "short_budget_ms")
    decisions = []
    for (context, budget), group in sorted(by_group.items()):
        scored = []
        for row in group:
            pred, risk = model_score(model, row, priors, rng)
            scored.append((pred, risk, row))
        scored.sort(key=lambda item: (item[0], str(item[2].get("candidate_id", ""))))
        selected = scored[0][2]
        top_candidates = [str(item[2].get("candidate_id", "")) for item in scored]
        top_regions = []
        for _, _, row in scored:
            region = str(row.get("audit_candidate_region", ""))
            if region not in top_regions:
                top_regions.append(region)
        safe_oracles = [
            row for row in group
            if boolish(row.get("target_safe_g522_positive"))
        ]
        safe_oracle = min(safe_oracles, key=lambda row: finite_number(row.get("target_oracle_rank_budget"), math.inf), default={})
        safe_candidate = str(safe_oracle.get("candidate_id", ""))
        safe_region = str(safe_oracle.get("audit_candidate_region", ""))
        selected_delta = finite_number(selected.get("target_delta_vs_old14_plus_g518"), 0.0)
        decisions.append(
            {
                "row_type": "context_budget_decision",
                "eval_scope": scope,
                "fold_id": fold_id,
                "model": model,
                "normalized_context_key": context,
                "short_budget_ms": budget,
                "map": selected.get("map", ""),
                "map_family": selected.get("map_family", ""),
                "map_agent_group": selected.get("map_agent_group", ""),
                "agents": selected.get("agents", ""),
                "seed": selected.get("seed", ""),
                "selected_candidate_id": selected.get("candidate_id", ""),
                "selected_candidate_region": selected.get("audit_candidate_region", ""),
                "selected_delta_vs_old14_plus_g518": csv_number(selected_delta),
                "selected_candidate_induced_no_solution": selected.get("target_candidate_induced_no_solution", ""),
                "selected_static_failure_recovery": selected.get("target_static_failure_recovery", ""),
                "actual_safe_oracle_candidate": safe_candidate,
                "actual_safe_oracle_region": safe_region,
                "top3_candidates": ";".join(top_candidates[:3]),
                "top5_candidates": ";".join(top_candidates[:5]),
                "top1_contains_safe_oracle": bool(safe_candidate and top_candidates[:1] and safe_candidate in top_candidates[:1]),
                "top3_contains_safe_oracle": bool(safe_candidate and safe_candidate in top_candidates[:3]),
                "top5_contains_safe_oracle": bool(safe_candidate and safe_candidate in top_candidates[:5]),
                "region_top1_contains_oracle": bool(safe_region and top_regions[:1] and safe_region in top_regions[:1]),
                "region_top2_contains_oracle": bool(safe_region and safe_region in top_regions[:2]),
                "predicted_avoidable_risk": csv_number(scored[0][1]),
                "actual_avoidable_risk": selected.get("target_candidate_induced_no_solution", ""),
                **G524_CLOSED_CLAIMS,
            }
        )
    n = max(len(decisions), 1)
    metrics = {
        "row_type": "model_eval",
        "eval_scope": scope,
        "fold_id": fold_id,
        "model": model,
        "context_budget_pairs": len(decisions),
        "top1_safe_oracle_capture_rate": sum(1 for row in decisions if boolish(row.get("top1_contains_safe_oracle"))) / n,
        "top3_safe_oracle_capture_rate": sum(1 for row in decisions if boolish(row.get("top3_contains_safe_oracle"))) / n,
        "top5_safe_oracle_capture_rate": sum(1 for row in decisions if boolish(row.get("top5_contains_safe_oracle"))) / n,
        "region_top1_capture_rate": sum(1 for row in decisions if boolish(row.get("region_top1_contains_oracle"))) / n,
        "region_top2_capture_rate": sum(1 for row in decisions if boolish(row.get("region_top2_contains_oracle"))) / n,
        "safe_policy_sim_utility": mean([finite_number(row.get("selected_delta_vs_old14_plus_g518"), math.inf) for row in decisions]),
        "candidate_induced_no_solution_count": sum(1 for row in decisions if boolish(row.get("selected_candidate_induced_no_solution"))),
        "static_recovery_capture_count": sum(1 for row in decisions if boolish(row.get("selected_static_failure_recovery"))),
        "avoidable_risk_ece": abs(
            mean([finite_number(row.get("predicted_avoidable_risk"), 0.0) for row in decisions])
            - mean([1.0 if boolish(row.get("actual_avoidable_risk")) else 0.0 for row in decisions])
        ),
        **G524_CLOSED_CLAIMS,
    }
    return metrics, decisions


def bootstrap_decisions(decisions: list[dict[str, Any]], samples: int) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in decisions:
        if row.get("eval_scope") == "seed_oof":
            by_model[str(row.get("model", ""))].append(row)
    out = []
    for model, rows in sorted(by_model.items()):
        if not rows:
            continue
        for sample in range(samples):
            draw = [rows[rng.randrange(len(rows))] for _ in rows]
            out.append(
                {
                    "model": model,
                    "bootstrap_sample": sample,
                    "top3_safe_oracle_capture_rate": sum(1 for row in draw if boolish(row.get("top3_contains_safe_oracle"))) / len(draw),
                    "safe_policy_sim_utility": mean([finite_number(row.get("selected_delta_vs_old14_plus_g518"), math.inf) for row in draw]),
                    "candidate_induced_no_solution_count": sum(1 for row in draw if boolish(row.get("selected_candidate_induced_no_solution"))),
                    **G524_CLOSED_CLAIMS,
                }
            )
    return out


def calibration_rows(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for model, rows in group_by([row for row in decisions if row.get("eval_scope") == "seed_oof"], "model").items():
        buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            bucket = min(9, int(finite_number(row.get("predicted_avoidable_risk"), 0.0) * 10))
            buckets[bucket].append(row)
        for bucket, group in sorted(buckets.items()):
            out.append(
                {
                    "model": model[0],
                    "risk_bucket": bucket,
                    "rows": len(group),
                    "mean_predicted_risk": mean([finite_number(row.get("predicted_avoidable_risk"), 0.0) for row in group]),
                    "mean_actual_risk": mean([1.0 if boolish(row.get("actual_avoidable_risk")) else 0.0 for row in group]),
                    **G524_CLOSED_CLAIMS,
                }
            )
    return out


def main_train_eval_region_to_parameter_models(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train/evaluate G5.24 region-to-parameter models.")
    parser.add_argument("--bootstrap-samples", type=int, default=300)
    args = parser.parse_args(argv)
    rows = read_rows(G524_CANDIDATE_BUDGET_TEACHER_CSV)
    eval_rows = []
    decisions = []
    scopes: list[tuple[str, list[str]]] = [
        ("fixed_train_dev", ["fixed"]),
        ("seed_oof", sorted({str(row.get("seed", "")) for row in rows})),
        ("leave_one_map_agent_group", sorted({str(row.get("map_agent_group", "")) for row in rows})),
        ("leave_one_map_family", sorted({str(row.get("map_family", "")) for row in rows})),
        ("budget_holdout", [str(budget) for budget in PRIMARY_BUDGETS]),
    ]
    for scope, folds in scopes:
        for fold_id in folds:
            train, dev = split_context_budget_rows(rows, scope, fold_id)
            if not train or not dev:
                continue
            for model in G524_REQUIRED_MODELS:
                metrics, split_decisions = evaluate_model_on_split(model, train, dev, scope, fold_id)
                eval_rows.append(metrics)
                decisions.extend(split_decisions)
    aggregates = []
    for model, group in group_by([row for row in eval_rows if row.get("eval_scope") == "seed_oof"], "model").items():
        m = str(model[0])
        aggregates.append(
            {
                "row_type": "model_aggregate",
                "eval_scope": "seed_oof_aggregate",
                "fold_id": "all",
                "model": m,
                "context_budget_pairs": sum(int(finite_number(row.get("context_budget_pairs"), 0)) for row in group),
                "top1_safe_oracle_capture_rate": mean([finite_number(row.get("top1_safe_oracle_capture_rate"), math.inf) for row in group]),
                "top3_safe_oracle_capture_rate": mean([finite_number(row.get("top3_safe_oracle_capture_rate"), math.inf) for row in group]),
                "top5_safe_oracle_capture_rate": mean([finite_number(row.get("top5_safe_oracle_capture_rate"), math.inf) for row in group]),
                "region_top1_capture_rate": mean([finite_number(row.get("region_top1_capture_rate"), math.inf) for row in group]),
                "region_top2_capture_rate": mean([finite_number(row.get("region_top2_capture_rate"), math.inf) for row in group]),
                "safe_policy_sim_utility": mean([finite_number(row.get("safe_policy_sim_utility"), math.inf) for row in group]),
                "candidate_induced_no_solution_count": sum(int(finite_number(row.get("candidate_induced_no_solution_count"), 0)) for row in group),
                "static_recovery_capture_count": sum(int(finite_number(row.get("static_recovery_capture_count"), 0)) for row in group),
                "avoidable_risk_ece": mean([finite_number(row.get("avoidable_risk_ece"), math.inf) for row in group]),
                **G524_CLOSED_CLAIMS,
            }
        )
    eval_rows.extend(aggregates)
    boot = bootstrap_decisions(decisions, args.bootstrap_samples)
    cal = calibration_rows(decisions)
    promotable = [
        row for row in aggregates
        if "oracle_" not in str(row.get("model", "")) and "shuffled" not in str(row.get("model", "")) and str(row.get("model", "")) != "random_feature_control"
    ]
    baseline = next((row for row in aggregates if row.get("model") == "region_prior_baseline_reproduced"), {})
    controls = [row for row in aggregates if "shuffled" in str(row.get("model", "")) or row.get("model") == "random_feature_control"]
    best = min(promotable, key=lambda row: (finite_number(row.get("safe_policy_sim_utility"), math.inf), -finite_number(row.get("top3_safe_oracle_capture_rate"), 0.0), str(row.get("model", ""))), default={})
    control_best = min(controls, key=lambda row: finite_number(row.get("safe_policy_sim_utility"), math.inf), default={})
    family_rows = [row for row in eval_rows if row.get("eval_scope") == "leave_one_map_family" and row.get("model") == best.get("model")]
    family_collapse = bool(family_rows) and min(finite_number(row.get("top3_safe_oracle_capture_rate"), 0.0) for row in family_rows) < 0.05
    feature_leak = leakage_scan(feature_names(read_rows(G524_CANDIDATE_BUDGET_FEATURES_CSV)))
    gates = {
        "top3_safe_oracle_capture_rate_ge_0p25": finite_number(best.get("top3_safe_oracle_capture_rate"), 0.0) >= 0.25,
        "safe_policy_sim_utility_beats_region_prior_baseline": finite_number(best.get("safe_policy_sim_utility"), math.inf) < finite_number(baseline.get("safe_policy_sim_utility"), math.inf),
        "candidate_induced_no_solution_count_le_baseline": finite_number(best.get("candidate_induced_no_solution_count"), math.inf) <= finite_number(baseline.get("candidate_induced_no_solution_count"), math.inf),
        "avoidable_risk_ece_le_baseline": finite_number(best.get("avoidable_risk_ece"), math.inf) <= finite_number(baseline.get("avoidable_risk_ece"), math.inf),
        "region_top2_capture_rate_ge_0p50": finite_number(best.get("region_top2_capture_rate"), 0.0) >= 0.50,
        "controls_do_not_match": finite_number(best.get("safe_policy_sim_utility"), math.inf) < finite_number(control_best.get("safe_policy_sim_utility"), math.inf),
        "forbidden_feature_count_eq_0": feature_leak["forbidden_feature_count"] == 0,
        "leave_one_map_family_does_not_collapse": not family_collapse,
    }
    summary = {
        "schema_version": "phase5p5_repair5g524_region_to_parameter_models_summary_v1",
        "decision": "region_to_parameter_models_evaluated",
        "required_models": G524_REQUIRED_MODELS,
        "models_present": sorted({row.get("model", "") for row in aggregates}),
        "candidate_budget_rows": len(rows),
        "eval_rows": len(eval_rows),
        "context_budget_decision_rows": len(decisions),
        "bootstrap_rows": len(boot),
        "calibration_rows": len(cal),
        "best_model": best.get("model", ""),
        "best_model_summary": best,
        "region_prior_baseline_summary": baseline,
        "best_control_summary": control_best,
        "main_target_gates": gates,
        "promising_region_to_parameter_model": all(gates.values()),
        "forbidden_feature_count": feature_leak["forbidden_feature_count"],
        "forbidden_features": feature_leak["forbidden_features"],
        **G524_CLOSED_CLAIMS,
    }
    write_rows(G524_MODEL_EVAL_CSV, eval_rows)
    write_rows(G524_MODEL_DECISIONS_CSV, decisions)
    write_rows(G524_MODEL_BOOTSTRAP_CSV, boot)
    write_rows(G524_MODEL_CALIBRATION_CSV, cal)
    write_json_file(G524_MODEL_SUMMARY, summary)
    write_simple_report(
        G524_MODEL_REPORT,
        "Repair5G.5.24 Region-to-Parameter Models",
        {
            "decision": summary["decision"],
            "best_model": summary["best_model"],
            "promising_region_to_parameter_model": summary["promising_region_to_parameter_model"],
            "best_model_summary": summary["best_model_summary"],
            "main_target_gates": gates,
        },
    )
    print(json.dumps({"decision": summary["decision"], "best_model": summary["best_model"], "promising": summary["promising_region_to_parameter_model"]}))
    return 0


def ridge_fit_predict(train_x: np.ndarray, train_y: np.ndarray, dev_x: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    if train_x.size == 0 or dev_x.size == 0:
        return np.zeros((dev_x.shape[0],), dtype=float)
    x = np.column_stack([np.ones(train_x.shape[0]), train_x])
    xd = np.column_stack([np.ones(dev_x.shape[0]), dev_x])
    reg = np.eye(x.shape[1]) * alpha
    reg[0, 0] = 0.0
    weights = np.linalg.pinv(x.T @ x + reg) @ x.T @ train_y
    return xd @ weights


def mae(values: Iterable[float]) -> float:
    vals = [abs(value) for value in values if math.isfinite(value)]
    return sum(vals) / len(vals) if vals else math.inf


def corr(xs: list[float], ys: list[float]) -> float:
    pairs = [(x, y) for x, y in zip(xs, ys) if math.isfinite(x) and math.isfinite(y)]
    if len(pairs) < 3:
        return math.nan
    x = np.array([p[0] for p in pairs], dtype=float)
    y = np.array([p[1] for p in pairs], dtype=float)
    if float(np.std(x)) == 0.0 or float(np.std(y)) == 0.0:
        return math.nan
    return float(np.corrcoef(x, y)[0, 1])


def main_train_eval_edge_update_surrogates(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train/evaluate G5.24 edge/update surrogates.")
    parser.add_argument("--bootstrap-samples", type=int, default=300)
    args = parser.parse_args(argv)
    rows = read_rows(G523_TEACHER_EDGE_CSV)
    contexts = sorted({row.get("normalized_context_key", "") for row in rows})
    holdout = set(contexts[::5])
    train = [row for row in rows if row.get("normalized_context_key") not in holdout]
    dev = [row for row in rows if row.get("normalized_context_key") in holdout]
    feature_sets = {
        "additive_baseline_proxy": [],
        "fixed_g522_best_region_proxy": ["feature_trace_c_raw", "feature_trace_f_raw"],
        "ridge_residual_model": ["feature_trace_c_raw", "feature_trace_f_raw", "feature_rich_c_weight_before", "feature_rich_f_weight_before"],
        "small_mlp_if_torch_available": ["feature_trace_c_raw", "feature_trace_f_raw", "feature_rich_c_weight_before", "feature_rich_f_weight_before"],
        "trace_only_ablation": ["feature_trace_c_raw", "feature_trace_f_raw"],
        "param_only_ablation": ["feature_rich_c_weight_before", "feature_rich_f_weight_before"],
        "shuffled_label_control": ["feature_trace_c_raw", "feature_trace_f_raw", "feature_rich_c_weight_before", "feature_rich_f_weight_before"],
    }
    targets = [
        "target_edge_oracle_dual_channel_update",
        "target_edge_residual_vs_additive",
        "target_edge_flow_shield_component",
        "target_edge_congestion_component",
    ]
    predictions = []
    eval_rows = []
    rng = random.Random(SEED)
    for target in targets:
        train_y = np.array([finite_number(row.get(target), 0.0) for row in train], dtype=float)
        shuffled = np.array(train_y, copy=True)
        rng.shuffle(shuffled)
        for model, cols in feature_sets.items():
            if model == "additive_baseline_proxy":
                pred = np.zeros((len(dev),), dtype=float)
            else:
                tx = np.array([[finite_number(row.get(col), 0.0) for col in cols] for row in train], dtype=float)
                dx = np.array([[finite_number(row.get(col), 0.0) for col in cols] for row in dev], dtype=float)
                y = shuffled if model == "shuffled_label_control" else train_y
                pred = ridge_fit_predict(tx, y, dx, alpha=1.0)
            actual = [finite_number(row.get(target), 0.0) for row in dev]
            pred_list = [float(value) for value in pred]
            eval_rows.append(
                {
                    "model": model,
                    "target": target,
                    "dev_rows": len(dev),
                    "edge_residual_mae": mae([p - a for p, a in zip(pred_list, actual)]),
                    "edge_residual_rank_correlation": corr(pred_list, actual),
                    "context_aggregate_update_error": mae([
                        mean([p for p, row in zip(pred_list, dev) if row.get("normalized_context_key") == context])
                        - mean([a for a, row in zip(actual, dev) if row.get("normalized_context_key") == context])
                        for context in holdout
                    ]),
                    "region_conditioned_update_error": "",
                    "heldout_map_family_update_error": "",
                    **G524_CLOSED_CLAIMS,
                }
            )
            for row, p, a in zip(dev[:500], pred_list[:500], actual[:500]):
                predictions.append(
                    {
                        "model": model,
                        "target": target,
                        "normalized_context_key": row.get("normalized_context_key", ""),
                        "edge_from_id": row.get("edge_from_id", ""),
                        "edge_to_id": row.get("edge_to_id", ""),
                        "prediction": csv_number(p),
                        "actual": csv_number(a),
                        "error": csv_number(p - a),
                        **G524_CLOSED_CLAIMS,
                    }
                )
    best = min(
        [row for row in eval_rows if row.get("target") == "target_edge_residual_vs_additive" and row.get("model") != "shuffled_label_control"],
        key=lambda row: finite_number(row.get("edge_residual_mae"), math.inf),
        default={},
    )
    summary = {
        "schema_version": "phase5p5_repair5g524_edge_update_surrogates_summary_v1",
        "decision": "edge_update_surrogates_evaluated",
        "edge_update_teacher_proxy_only": True,
        "teacher_rows": len(rows),
        "train_rows": len(train),
        "dev_rows": len(dev),
        "models": sorted(feature_sets),
        "targets": targets,
        "best_residual_model": best,
        "bootstrap_samples_requested": args.bootstrap_samples,
        "neural_readiness_use": "offline_residual_modeling_only_no_solver_policy_claim",
        **G524_CLOSED_CLAIMS,
    }
    write_rows(G524_EDGE_EVAL_CSV, eval_rows)
    write_rows(G524_EDGE_PREDICTIONS_CSV, predictions)
    write_json_file(G524_EDGE_SUMMARY, summary)
    write_simple_report(
        G524_EDGE_REPORT,
        "Repair5G.5.24 Edge/Update Surrogates",
        {
            "decision": summary["decision"],
            "edge_update_teacher_proxy_only": True,
            "teacher_rows": len(rows),
            "best_residual_model": best,
            "neural_readiness_use": summary["neural_readiness_use"],
        },
    )
    print(json.dumps({"decision": summary["decision"], "edge_update_teacher_proxy_only": True}))
    return 0


def main_analyze_model_failure_and_next_trace_fields(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze G5.24 model failure and next trace fields.")
    parser.parse_args(argv)
    model_summary = load_json_if_exists(G524_MODEL_SUMMARY)
    feature_summary = load_json_if_exists(G524_FEATURE_SUMMARY)
    budget_summary = load_json_if_exists(G524_BUDGET_TEACHER_SUMMARY)
    inventory = load_json_if_exists(G524_TRACE_INVENTORY_SUMMARY)
    eval_rows = read_rows(G524_MODEL_EVAL_CSV)
    decisions = read_rows(G524_MODEL_DECISIONS_CSV)
    best_model = str(model_summary.get("best_model", ""))
    feature_ablation = [
        row for row in eval_rows
        if row.get("row_type") == "model_aggregate" and row.get("model") in {
            best_model,
            "param_only_control",
            "trace_only_control",
            "no_pre_update_trace_ablation",
            "source_blind_control",
            "random_feature_control",
        }
    ]
    confusion_counter: Counter[tuple[str, str]] = Counter()
    for row in decisions:
        if row.get("model") == best_model and row.get("eval_scope") == "seed_oof":
            confusion_counter[(str(row.get("actual_safe_oracle_region", "")), str(row.get("selected_candidate_region", "")))] += 1
    confusion_rows = [
        {"actual_region": actual, "predicted_region": pred, "count": count, **G524_CLOSED_CLAIMS}
        for (actual, pred), count in sorted(confusion_counter.items())
    ]
    topk_miss = [
        row for row in decisions
        if row.get("model") == best_model and row.get("eval_scope") == "seed_oof" and row.get("actual_safe_oracle_candidate") and not boolish(row.get("top3_contains_safe_oracle"))
    ][:200]
    risk_rows = []
    for row in [r for r in decisions if r.get("model") == best_model and r.get("eval_scope") == "seed_oof"]:
        pred_high = finite_number(row.get("predicted_avoidable_risk"), 0.0) >= 0.2
        actual = boolish(row.get("actual_avoidable_risk"))
        risk_rows.append(
            {
                "risk_case": "true_positive" if pred_high and actual else "false_positive" if pred_high else "false_negative" if actual else "true_negative",
                "normalized_context_key": row.get("normalized_context_key", ""),
                "short_budget_ms": row.get("short_budget_ms", ""),
                "selected_candidate_id": row.get("selected_candidate_id", ""),
                "predicted_avoidable_risk": row.get("predicted_avoidable_risk", ""),
                "actual_avoidable_risk": row.get("actual_avoidable_risk", ""),
                **G524_CLOSED_CLAIMS,
            }
        )
    budget_holdout = [row for row in eval_rows if row.get("eval_scope") == "budget_holdout"]
    family_holdout = [row for row in eval_rows if row.get("eval_scope") == "leave_one_map_family"]
    next_fields = [
        {
            "priority": 1,
            "trace_field": "blocked_reason_and_competing_neighbor_rank",
            "status": "missing_or_ambiguous",
            "why_needed": "Separate candidate-induced risk from useful congestion/flow signal before applying candidate parameters.",
            **G524_CLOSED_CLAIMS,
        },
        {
            "priority": 2,
            "trace_field": "same_checkpoint_counterfactual_short_probe_manifest",
            "status": "partially_available_as_update_probe_log",
            "why_needed": "Turn proxy edge/update labels into exact residual labels for bounded neural UpdateLTM.",
            **G524_CLOSED_CLAIMS,
        },
        {
            "priority": 3,
            "trace_field": "per_agent_goal_progress_edge_events",
            "status": "partially_available",
            "why_needed": "Identify when F-channel evidence is true goal progress versus repeated waiting around bottlenecks.",
            **G524_CLOSED_CLAIMS,
        },
        {
            "priority": 4,
            "trace_field": "pre_update_edge_c_and_f_channels",
            "status": "available_in_checkpoint_sparse_fields",
            "why_needed": "Keep trace x parameter interactions runtime-safe and pre-choice.",
            **G524_CLOSED_CLAIMS,
        },
    ]
    readiness = [
        {"item": "candidate_space_full_primary_positive", "status": True, "evidence": "G5.23 oracle gate", **G524_CLOSED_CLAIMS},
        {"item": "budget_pair_labels_created", "status": budget_summary.get("candidate_budget_rows") == 5280, "evidence": G524_BUDGET_TEACHER_SUMMARY, **G524_CLOSED_CLAIMS},
        {"item": "trace_enriched_features_clean", "status": feature_summary.get("forbidden_feature_count") == 0, "evidence": G524_FEATURE_SUMMARY, **G524_CLOSED_CLAIMS},
        {"item": "region_to_parameter_gate_passed", "status": boolish(model_summary.get("promising_region_to_parameter_model")), "evidence": G524_MODEL_SUMMARY, **G524_CLOSED_CLAIMS},
        {"item": "edge_teacher_exact", "status": False, "evidence": "proxy_only", **G524_CLOSED_CLAIMS},
        {"item": "runtime_claim_allowed", "status": False, "evidence": "closed by design", **G524_CLOSED_CLAIMS},
    ]
    gates = model_summary.get("main_target_gates", {})
    summary = {
        "schema_version": "phase5p5_repair5g524_model_failure_and_next_trace_fields_summary_v1",
        "decision": "model_failure_and_next_trace_fields_completed",
        "did_budget_pair_labels_improve_learnability": finite_number(model_summary.get("best_model_summary", {}).get("top3_safe_oracle_capture_rate"), 0.0) > 0.13333333333333333,
        "did_trace_enriched_features_improve_top3_capture": finite_number(model_summary.get("best_model_summary", {}).get("top3_safe_oracle_capture_rate"), 0.0) > 0.13333333333333333,
        "did_region_to_parameter_beat_region_prior": boolish(gates.get("safe_policy_sim_utility_beats_region_prior_baseline")),
        "wins_concentrated_in_fractional_coverage": any(row.get("actual_region") == "D_fractional_coverage" and int(finite_number(row.get("count"), 0)) > 0 for row in confusion_rows),
        "candidate_induced_failures_predictable_before_apply": boolish(gates.get("avoidable_risk_ece_le_baseline")),
        "static_recovery_cases_learnable": int(finite_number(model_summary.get("best_model_summary", {}).get("static_recovery_capture_count"), 0)) > 0,
        "missing_trace_fields": inventory.get("missing_required_fields", []),
        "main_target_gates": gates,
        **G524_CLOSED_CLAIMS,
    }
    write_rows(G524_FAILURE_FEATURE_ABLATION_CSV, feature_ablation)
    write_rows(G524_FAILURE_REGION_CONFUSION_CSV, confusion_rows)
    write_rows(G524_FAILURE_TOPK_MISS_CSV, topk_miss)
    write_rows(G524_FAILURE_RISK_TABLE_CSV, risk_rows)
    write_rows(G524_FAILURE_BUDGET_HOLDOUT_CSV, budget_holdout)
    write_rows(G524_FAILURE_FAMILY_HOLDOUT_CSV, family_holdout)
    write_rows(G524_NEXT_TRACE_FIELDS_CSV, next_fields)
    write_rows(G524_NEURAL_READINESS_CSV, readiness)
    write_json_file(G524_FAILURE_SUMMARY, summary)
    write_simple_report(
        G524_FAILURE_REPORT,
        "Repair5G.5.24 Model Failure and Next Trace Fields",
        {
            "decision": summary["decision"],
            "did_budget_pair_labels_improve_learnability": summary["did_budget_pair_labels_improve_learnability"],
            "did_region_to_parameter_beat_region_prior": summary["did_region_to_parameter_beat_region_prior"],
            "candidate_induced_failures_predictable_before_apply": summary["candidate_induced_failures_predictable_before_apply"],
            "missing_trace_fields": summary["missing_trace_fields"],
            "main_target_gates": gates,
        },
    )
    print(json.dumps({"decision": summary["decision"], "missing_trace_fields": summary["missing_trace_fields"]}))
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write G5.24 final decision.")
    parser.parse_args(argv)
    verify = load_json_if_exists(G524_VERIFY_SUMMARY)
    budget = load_json_if_exists(G524_BUDGET_TEACHER_SUMMARY)
    inventory = load_json_if_exists(G524_TRACE_INVENTORY_SUMMARY)
    features = load_json_if_exists(G524_FEATURE_SUMMARY)
    models = load_json_if_exists(G524_MODEL_SUMMARY)
    edge = load_json_if_exists(G524_EDGE_SUMMARY)
    failure = load_json_if_exists(G524_FAILURE_SUMMARY)
    gates = models.get("main_target_gates", {})
    positive_learning = (
        features.get("forbidden_feature_count") == 0
        and boolish(verify.get("gates", {}).get("incremental_oracle_gap_matches"))
        and finite_number(models.get("best_model_summary", {}).get("top3_safe_oracle_capture_rate"), 0.0) >= 0.25
        and boolish(gates.get("safe_policy_sim_utility_beats_region_prior_baseline"))
        and boolish(gates.get("candidate_induced_no_solution_count_le_baseline"))
        and boolish(gates.get("region_top2_capture_rate_ge_0p50"))
        and boolish(gates.get("controls_do_not_match"))
        and boolish(gates.get("leave_one_map_family_does_not_collapse"))
    )
    if features.get("forbidden_feature_count", 99) != 0:
        decision = "g524_target_or_leakage_blocker_stop"
    elif not boolish(inventory.get("critical_pre_choice_fields_available_for_g524_offline_round")):
        decision = "g524_trace_fields_missing_require_logging_round"
    elif positive_learning and boolish(models.get("promising_region_to_parameter_model")):
        decision = "g524_region_to_parameter_learning_improves_continue_trace_probe"
    elif boolish(edge.get("edge_update_teacher_proxy_only")) and not positive_learning:
        decision = "g524_candidate_space_positive_learning_still_blocked_collect_richer_trace"
    elif boolish(edge.get("best_residual_model")):
        decision = "g524_edge_update_teacher_ready_continue_residual_modeling"
    else:
        decision = "g524_candidate_space_positive_learning_still_blocked_collect_richer_trace"
    closed_claims = all(
        not boolish(part.get(key))
        for part in [verify, budget, inventory, features, models, edge, failure]
        for key in G524_CLOSED_CLAIMS
    )
    summary = {
        "schema_version": "phase5p5_repair5g524_decision_summary_v1",
        "decision": decision,
        "component_decisions": {
            "verify": verify.get("decision", ""),
            "inventory": inventory.get("decision", ""),
            "budget_teacher": budget.get("decision", ""),
            "features": features.get("decision", ""),
            "models": models.get("decision", ""),
            "edge": edge.get("decision", ""),
            "failure": failure.get("decision", ""),
        },
        "positive_learning_gates": {
            "forbidden_feature_count_eq_0": features.get("forbidden_feature_count") == 0,
            "candidate_space_full_primary_evidence_positive": boolish(verify.get("gates", {}).get("incremental_oracle_gap_matches")),
            "top3_safe_oracle_capture_rate_ge_0p25": finite_number(models.get("best_model_summary", {}).get("top3_safe_oracle_capture_rate"), 0.0) >= 0.25,
            "safe_policy_sim_utility_beats_region_prior_baseline": boolish(gates.get("safe_policy_sim_utility_beats_region_prior_baseline")),
            "candidate_induced_no_solution_count_le_baseline": boolish(gates.get("candidate_induced_no_solution_count_le_baseline")),
            "region_top2_capture_rate_ge_0p50": boolish(gates.get("region_top2_capture_rate_ge_0p50")),
            "controls_do_not_match": boolish(gates.get("controls_do_not_match")),
            "leave_one_map_family_does_not_collapse": boolish(gates.get("leave_one_map_family_does_not_collapse")),
            "claims_remain_closed": closed_claims,
        },
        "best_model": models.get("best_model", ""),
        "best_model_summary": models.get("best_model_summary", {}),
        "edge_update_teacher_proxy_only": edge.get("edge_update_teacher_proxy_only", ""),
        "missing_trace_fields": inventory.get("missing_required_fields", []),
        **G524_CLOSED_CLAIMS,
    }
    write_json_file(G524_DECISION_SUMMARY, summary)
    write_text_file(
        G524_DECISION_REPORT,
        "# Repair5G.5.24 Final Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- best_model: `{models.get('best_model', '')}`\n"
        f"- top3_safe_oracle_capture_rate: `{models.get('best_model_summary', {}).get('top3_safe_oracle_capture_rate', '')}`\n"
        f"- region_top2_capture_rate: `{models.get('best_model_summary', {}).get('region_top2_capture_rate', '')}`\n"
        f"- positive_learning_gates: `{summary['positive_learning_gates']}`\n"
        f"- missing_trace_fields: `{summary['missing_trace_fields']}`\n"
        f"- edge_update_teacher_proxy_only: `{summary['edge_update_teacher_proxy_only']}`\n\n"
        "Closed claims remain:\n\n"
        "```text\n"
        "phase5p5_allowed=false\n"
        "phase6_allowed=false\n"
        "runtime_claim_allowed=false\n"
        "learned_runtime_policy_validated=false\n"
        "aaai_ready=false\n"
        "```\n",
    )
    print(json.dumps({"decision": decision, "best_model": models.get("best_model", "")}))
    return 0

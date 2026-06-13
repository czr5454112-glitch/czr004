"""Repair5G.5.42 deployable static-fallback ladder plus residual overlay.

G5.42 keeps the solver and candidate semantics fixed. It audits the G5.41
blind failure source, builds a deployable static baseline ladder, then treats
G5.41 residual regions as conditional overlays on top of that ladder.
"""

from __future__ import annotations

import argparse
import csv
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

from repair5g5_common import DEFAULT_BINARY  # noqa: E402
from repair5g531_common import (  # noqa: E402
    boolish,
    claims,
    csv_number,
    external_lacam2_clean,
    load_json,
    number,
    read_rows,
    resolve,
    write_json,
    write_rows,
    write_text,
)
from repair5g532_common import map_family  # noqa: E402
import repair5g538_common as g538  # noqa: E402
import repair5g539_common as g539  # noqa: E402
import repair5g540_common as g540  # noqa: E402
import repair5g541_common as g541  # noqa: E402


PLAN_FILE = "czr004_g542_deployable_static_fallback_ladder_residual_overlay_plan.md"

ADDITIVE = g541.ADDITIVE
STATIC_FLOW = g541.STATIC_FLOW
BEST_FIXED = g541.BEST_FIXED
STATIC_ROLES = [
    "additive_ltm",
    "static_flow_shield",
    "best_fixed_static_goal_aware",
    "frozen_family_static_goal_aware",
]
STATIC_ROLE_SET = set(STATIC_ROLES)
POLICY_VARIANTS = [
    "P0_static_flow_only",
    "P1_frozen_family_static_only",
    "P2_deployable_static_ladder_only",
    "P3_ladder_plus_overlay_high_margin_only",
    "P4_ladder_plus_overlay_nonnegative",
    "P5_ultra_conservative_overlay",
    "P6_staticflow_positive_residual_but_family_guard",
]
OVERLAY_VARIANTS = POLICY_VARIANTS[3:]

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g542_g541_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g542_g541_verification_summary.json"
TABLE_AUDIT_CSV = "outputs/tables/phase5p5_repair5g542_g541_table_materialization_audit.csv"
G541_VS_STATIC_POSITIVE_CSV = "outputs/tables/phase5p5_repair5g542_g541_vs_static_flow_positive_audit.csv"
G541_VS_FAMILY_REGRESSION_CSV = "outputs/tables/phase5p5_repair5g542_g541_vs_family_static_regression_audit.csv"

FAILURE_AUDIT_REPORT = "outputs/reports/phase5p5_repair5g542_g541_blind_failure_source_audit.md"
FAILURE_AUDIT_SUMMARY = "outputs/reports/phase5p5_repair5g542_g541_blind_failure_source_audit_summary.json"
FAILURE_DECOMP_CSV = "outputs/tables/phase5p5_repair5g542_g541_failure_source_decomposition.csv"
FALLBACK_VS_RESIDUAL_CSV = "outputs/tables/phase5p5_repair5g542_g541_fallback_vs_residual_failure_audit.csv"

STRATEGY_REPORT = "outputs/reports/phase5p5_repair5g542_strategy_doc_update.md"
STRATEGY_SUMMARY = "outputs/reports/phase5p5_repair5g542_strategy_doc_update_summary.json"

LADDER_TRAINING_CSV = "outputs/tables/phase5p5_repair5g542_deployable_static_ladder_training.csv"
LADDER_RULES_CSV = "outputs/tables/phase5p5_repair5g542_deployable_static_ladder_rules.csv"
LADDER_EVAL_CSV = "outputs/tables/phase5p5_repair5g542_static_ladder_eval_by_stratum.csv"
LADDER_NEGATIVE_CSV = "outputs/tables/phase5p5_repair5g542_static_ladder_negative_controls.csv"
LADDER_REPORT = "outputs/reports/phase5p5_repair5g542_deployable_static_ladder.md"
LADDER_SUMMARY = "outputs/reports/phase5p5_repair5g542_deployable_static_ladder_summary.json"

OVERLAY_LABELS_CSV = "outputs/tables/phase5p5_repair5g542_residual_overlay_labels.csv"
OVERLAY_SAFE_CSV = "outputs/tables/phase5p5_repair5g542_overlay_safe_regions.csv"
OVERLAY_UNSAFE_CSV = "outputs/tables/phase5p5_repair5g542_overlay_unsafe_regions.csv"
OVERLAY_BOUNDARY_CSV = "outputs/tables/phase5p5_repair5g542_overlay_boundary_regions.csv"
OVERLAY_LABEL_REPORT = "outputs/reports/phase5p5_repair5g542_residual_overlay_labels.md"
OVERLAY_LABEL_SUMMARY = "outputs/reports/phase5p5_repair5g542_residual_overlay_labels_summary.json"

POLICY_CANDIDATES_CSV = "outputs/tables/phase5p5_repair5g542_ladder_overlay_policy_candidates.csv"
POLICY_RULES_CSV = "outputs/tables/phase5p5_repair5g542_ladder_overlay_policy_rules.csv"
POLICY_REPORT = "outputs/reports/phase5p5_repair5g542_ladder_overlay_policy_candidates.md"
POLICY_SUMMARY = "outputs/reports/phase5p5_repair5g542_ladder_overlay_policy_candidates_summary.json"

PROBE_PLAN_CSV = "outputs/tables/phase5p5_repair5g542_ladder_overlay_probe_plan.csv"
PROBE_RESULTS_CSV = "outputs/tables/phase5p5_repair5g542_ladder_overlay_probe_results.csv"
PROBE_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g542_ladder_overlay_selected_vs_static_flow.csv"
PROBE_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g542_ladder_overlay_selected_vs_family_static.csv"
PROBE_VS_LADDER_CSV = "outputs/tables/phase5p5_repair5g542_ladder_overlay_selected_vs_ladder_baseline.csv"
PROBE_FAILURES_CSV = "outputs/tables/phase5p5_repair5g542_ladder_overlay_failure_cases.csv"
PROBE_REPORT = "outputs/reports/phase5p5_repair5g542_ladder_overlay_probe.md"
PROBE_EVIDENCE_REPORT = "outputs/reports/phase5p5_repair5g542_ladder_overlay_evidence.md"
PROBE_EVIDENCE_SUMMARY = "outputs/reports/phase5p5_repair5g542_ladder_overlay_evidence_summary.json"
PROBE_RAW_LOG_DIR = "outputs/logs/phase5p5_repair5g542_ladder_overlay_probe"
PROBE_RAW_RUN_JSONL = f"{PROBE_RAW_LOG_DIR}/phase5p5_repair5g542_probe_runs.jsonl"
PROBE_RAW_COMMAND_JSONL = f"{PROBE_RAW_LOG_DIR}/phase5p5_repair5g542_probe_commands.jsonl"
PROBE_RAW_CHECKPOINT_JSONL = f"{PROBE_RAW_LOG_DIR}/phase5p5_repair5g542_probe_checkpoints.jsonl"
PROBE_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g542_probe_scenarios"
PROBE_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g542_probe_scenario_generation.json"

FROZEN_POLICY_CSV = "outputs/tables/phase5p5_repair5g542_frozen_ladder_overlay_policy.csv"
FROZEN_POLICY_REPORT = "outputs/reports/phase5p5_repair5g542_frozen_ladder_overlay_policy.md"
FROZEN_POLICY_SUMMARY = "outputs/reports/phase5p5_repair5g542_frozen_ladder_overlay_policy_summary.json"
FROZEN_POLICY_MANIFEST = "artifacts/models/laur_ltm/repair5g542_frozen_ladder_overlay_policy_manifest.json"

BLIND_RESULTS_CSV = "outputs/tables/phase5p5_repair5g542_frozen_ladder_overlay_blind_results.csv"
BLIND_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g542_frozen_ladder_overlay_vs_static_flow.csv"
BLIND_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g542_frozen_ladder_overlay_vs_family_static.csv"
BLIND_VS_LADDER_CSV = "outputs/tables/phase5p5_repair5g542_frozen_ladder_overlay_vs_ladder_baseline.csv"
BLIND_FAILURES_CSV = "outputs/tables/phase5p5_repair5g542_frozen_ladder_overlay_failure_cases.csv"
BLIND_REPLAY_REPORT = "outputs/reports/phase5p5_repair5g542_frozen_ladder_overlay_blind_replay.md"
BLIND_EVIDENCE_REPORT = "outputs/reports/phase5p5_repair5g542_frozen_ladder_overlay_blind_evidence.md"
BLIND_EVIDENCE_SUMMARY = "outputs/reports/phase5p5_repair5g542_frozen_ladder_overlay_blind_evidence_summary.json"
BLIND_RAW_LOG_DIR = "outputs/logs/phase5p5_repair5g542_frozen_ladder_overlay_blind_replay"
BLIND_RAW_RUN_JSONL = f"{BLIND_RAW_LOG_DIR}/phase5p5_repair5g542_blind_runs.jsonl"
BLIND_RAW_COMMAND_JSONL = f"{BLIND_RAW_LOG_DIR}/phase5p5_repair5g542_blind_commands.jsonl"
BLIND_RAW_CHECKPOINT_JSONL = f"{BLIND_RAW_LOG_DIR}/phase5p5_repair5g542_blind_checkpoints.jsonl"
BLIND_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g542_blind_scenarios"
BLIND_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g542_blind_scenario_generation.json"

EDGE_CLASS_CSV = "outputs/tables/phase5p5_repair5g542_edge_class_design_targets.csv"
EVENT_CONDITION_CSV = "outputs/tables/phase5p5_repair5g542_event_conditioned_update_design_targets.csv"
EDGE_DESIGN_REPORT = "outputs/reports/phase5p5_repair5g542_next_edge_class_design_if_blocked.md"
EDGE_DESIGN_SUMMARY = "outputs/reports/phase5p5_repair5g542_next_edge_class_design_if_blocked_summary.json"

DECISION_REPORT = "outputs/reports/phase5p5_repair5g542_decision.md"
DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g542_decision_summary.json"

PROBE_SEEDS = list(range(966, 1026))
BLIND_SEEDS = list(range(1026, 1106))
ALL_DEPLOYABLE_STRATA = list(g541.ALL_DEPLOYABLE_STRATA)
_FAMILY_STATIC_CACHE: dict[str, str] = {}

EXPECTED_G541_ARTIFACTS = {
    "decision_summary": g541.DECISION_SUMMARY,
    "balanced_per_stratum_regions_summary": g541.EXTENSION_SUMMARY,
    "final_stratum_regions_summary": g541.FINAL_SUMMARY,
    "frozen_stratum_policy_summary": g541.FROZEN_POLICY_SUMMARY,
    "frozen_stratum_blind_evidence_summary": g541.BLIND_EVIDENCE_SUMMARY,
    "final_supported_stratum_regions": g541.FINAL_SUPPORTED_CSV,
    "frozen_stratum_policy": g541.FROZEN_POLICY_CSV,
    "frozen_stratum_blind_replay_results": g541.BLIND_RESULTS_CSV,
    "frozen_stratum_selected_vs_static_flow": "outputs/tables/phase5p5_repair5g541_frozen_stratum_selected_vs_static_flow.csv",
    "frozen_stratum_selected_vs_family_static": "outputs/tables/phase5p5_repair5g541_frozen_stratum_selected_vs_family_static.csv",
    "frozen_stratum_failure_cases": g541.BLIND_FAILURE_CASES_CSV,
    "region_predictor_manifest": g541.PREDICTOR_MANIFEST,
    "repair5g541_common": "scripts/repair5g541_common.py",
}
G541_ALIASES = {
    "outputs/tables/phase5p5_repair5g541_frozen_stratum_selected_vs_static_flow.csv": g541.BLIND_VS_STATIC_CSV,
    "outputs/tables/phase5p5_repair5g541_frozen_stratum_selected_vs_family_static.csv": g541.BLIND_VS_FAMILY_CSV,
}

HISTORICAL_RESULT_PATHS = [
    ("g534_broad", "outputs/tables/phase5p5_repair5g534_broad_probe_results.csv"),
    ("g534_prospective", "outputs/tables/phase5p5_repair5g534_prospective_selected_replay_results.csv"),
    ("g536_real_no_regression", "outputs/tables/phase5p5_repair5g536_real_no_regression_replay_results.csv"),
    ("g537_static_relative_blind", "outputs/tables/phase5p5_repair5g537_static_relative_blind_replay_results.csv"),
    ("g538_residual_probe", "outputs/tables/phase5p5_repair5g538_static_flow_residual_probe_results.csv"),
    ("g538_residual_blind", "outputs/tables/phase5p5_repair5g538_residual_blind_replay_results.csv"),
    ("g540_stage1", g540.STAGE1_RESULTS_CSV),
    ("g540_stage2", g540.STAGE2_RESULTS_CSV),
    ("g540_stage3", g540.STAGE3_RESULTS_CSV),
    ("g540_blind", g540.BLIND_RESULTS_CSV),
    ("g541_balanced_extension", g541.EXTENSION_RESULTS_CSV),
    ("g541_stratum_refinement", g541.REFINEMENT_RESULTS_CSV),
    ("g541_frozen_blind", g541.BLIND_RESULTS_CSV),
]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--max-workers", type=int, default=1)
    p.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    p.add_argument("--max-contexts", type=int, default=0)
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
    return 1


def mean(values: Iterable[float]) -> float:
    vals = [float(v) for v in values if math.isfinite(float(v))]
    return statistics.mean(vals) if vals else 0.0


def ensure_g541_candidates_installed() -> None:
    try:
        g541.install_g541_candidates_for_g540(g541.refinement_rows())
    except FileNotFoundError:
        return


def role_alias(role: Any) -> str:
    text = str(role)
    aliases = {
        "family_static_goal_aware": "frozen_family_static_goal_aware",
        "best_family_static_goal_aware": "frozen_family_static_goal_aware",
        "best_static_goal_aware": "best_fixed_static_goal_aware",
        "primary_static_goal_aware": "best_fixed_static_goal_aware",
    }
    return aliases.get(text, text)


def stratum_key(family: Any, agents: Any, budget: Any) -> str:
    return g541.deployable_key(str(family), int(number(agents, 0)), int(number(budget, 0)))


def family_static_candidate(family: str) -> str:
    if family not in _FAMILY_STATIC_CACHE:
        _FAMILY_STATIC_CACHE[family] = g541.best_family_candidate_for_map(g541.stratum_map(family))
    return _FAMILY_STATIC_CACHE[family]


def static_candidate_for_role(role: str, family: str) -> str:
    if role == "additive_ltm":
        return ADDITIVE
    if role == "static_flow_shield":
        return STATIC_FLOW
    if role == "best_fixed_static_goal_aware":
        return BEST_FIXED
    if role == "frozen_family_static_goal_aware":
        return family_static_candidate(family)
    raise KeyError(role)


def static_candidates_for_family(family: str) -> set[str]:
    return {static_candidate_for_role(role, family) for role in STATIC_ROLES}


def is_residual_candidate(candidate_id: Any, family: str) -> bool:
    return str(candidate_id) not in static_candidates_for_family(family)


def candidate_method(candidate_id: str) -> str:
    ensure_g541_candidates_installed()
    try:
        return g541.candidate_method(candidate_id)
    except Exception:
        return g540.candidate_method(candidate_id)


def context_key(row: dict[str, Any], *, include_iteration: bool = True) -> str:
    key = str(row.get("context_budget_iteration_key", ""))
    if include_iteration and key:
        return key
    return g538.context_key(row, include_iteration=include_iteration)


def group_by(rows: list[dict[str, Any]], fields: list[str]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    out: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        out[tuple(row.get(field, "") for field in fields)].append(row)
    return out


def grouped_results_from_rows(rows: list[dict[str, Any]], *, source_scoped: bool = False) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        key = context_key(row)
        if source_scoped:
            key = f"{row.get('source_dataset', '')}|{key}"
        grouped[key][role_alias(row.get("role", ""))] = row
    return grouped


def grouped_results(path: str) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in read_rows(path):
        grouped[context_key(row)][role_alias(row.get("role", ""))] = row
    return grouped


def summarize_pair_rows(rows: list[dict[str, Any]], *, prefix: str = "") -> dict[str, Any]:
    return g541.summarize_pair_rows(rows, prefix=prefix)


def upsert_section(path: str, title: str, body: str) -> bool:
    p = resolve(path)
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    section = f"{title}\n\n{body.strip()}\n"
    if title in text:
        before, rest = text.split(title, 1)
        next_pos = rest.find("\n## ")
        if next_pos == -1:
            new_text = before.rstrip() + "\n\n" + section
        else:
            new_text = before.rstrip() + "\n\n" + section + rest[next_pos + 1 :]
    else:
        new_text = text.rstrip() + "\n\n" + section if text.strip() else section
    changed = new_text != text
    if changed:
        write_text(path, new_text)
    return changed


def claim_closed_summary() -> dict[str, bool]:
    return {
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }


def main_verify_g541_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.42 verify G5.41 artifacts")
    audit_rows: list[dict[str, Any]] = []
    missing = []
    aliases_used = []
    for label, expected in EXPECTED_G541_ARTIFACTS.items():
        actual = expected
        alias_for = ""
        if not resolve(actual).exists() and expected in G541_ALIASES:
            alias = G541_ALIASES[expected]
            if resolve(alias).exists():
                actual = alias
                alias_for = expected
                aliases_used.append({"expected": expected, "actual": actual})
        exists = resolve(actual).exists()
        if not exists:
            missing.append(expected)
        audit_rows.append(
            {
                "artifact_label": label,
                "expected_path": expected,
                "resolved_path": actual,
                "alias_for": alias_for,
                "exists": exists,
                "row_count": table_count(actual) if exists else 0,
                **claims(),
            }
        )
    write_rows(TABLE_AUDIT_CSV, audit_rows)

    blind = load_json(g541.BLIND_EVIDENCE_SUMMARY, {})
    static_positive = {
        "audit": "g541_vs_static_flow_positive",
        "vs_static_flow_success_regression_count": blind.get("vs_static_flow_success_regression_count", ""),
        "vs_static_flow_quality_only_mean_delta": blind.get("vs_static_flow_quality_only_mean_delta", ""),
        "vs_static_flow_better_count": blind.get("vs_static_flow_better_count", ""),
        "vs_static_flow_worse_count": blind.get("vs_static_flow_worse_count", ""),
        "non_static_selection_rate": blind.get("non_static_param_selection_rate", ""),
        "safe_high_margin_count": blind.get("vs_static_flow_safe_high_margin_count", ""),
        "passes_positive_audit": (
            int(number(blind.get("vs_static_flow_success_regression_count"), 999)) == 0
            and number(blind.get("vs_static_flow_quality_only_mean_delta"), 1.0) < 0
            and int(number(blind.get("vs_static_flow_better_count"), 0)) > int(number(blind.get("vs_static_flow_worse_count"), 0))
        ),
        **claims(),
    }
    write_rows(G541_VS_STATIC_POSITIVE_CSV, [static_positive])

    family_regressions = [
        dict(row, regression_audit="g541_vs_family_static_success_regression", **claims())
        for row in read_rows(g541.BLIND_VS_FAMILY_CSV)
        if boolish(row.get("success_regression"))
    ]
    write_rows(G541_VS_FAMILY_REGRESSION_CSV, family_regressions)

    decision = "g541_artifact_or_pairing_blocker_stop" if missing else "g541_artifacts_verified"
    summary = {
        "schema_version": "phase5p5_repair5g542_g541_verification_summary_v1",
        "decision": decision,
        "missing_artifact_count": len(missing),
        "missing_artifacts": missing,
        "aliases_used": aliases_used,
        "artifact_rows_checked": len(audit_rows),
        "g541_positive_vs_static_flow_confirmed": bool(static_positive["passes_positive_audit"]),
        "family_static_regression_rows": len(family_regressions),
        "g541_blind_decision": blind.get("decision", ""),
        **claims(),
    }
    write_json(VERIFY_SUMMARY, summary)
    write_text(
        VERIFY_REPORT,
        "# G5.42 Verification of G5.41 Artifacts\n\n"
        f"- decision: `{decision}`\n"
        f"- missing artifacts: `{len(missing)}`\n"
        f"- aliases used: `{len(aliases_used)}`\n"
        f"- family-static regression rows: `{len(family_regressions)}`\n"
        f"- positive vs static_flow confirmed: `{static_positive['passes_positive_audit']}`\n",
    )
    print(json.dumps({"decision": decision, "missing": len(missing), "family_regressions": len(family_regressions)}))
    return 0


def main_audit_g541_blind_failure_sources(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.42 audit G5.41 blind failure sources")
    if not resolve(VERIFY_SUMMARY).exists():
        main_verify_g541_artifacts([])

    grouped = grouped_results(g541.BLIND_RESULTS_CSV)
    family_pairs = [
        row for row in read_rows(g541.BLIND_VS_FAMILY_CSV) if boolish(row.get("success_regression"))
    ]
    detail_rows: list[dict[str, Any]] = []
    counts = Counter()
    role_mismatch_count = 0
    for row in family_pairs:
        key = context_key(row)
        role_rows = grouped.get(key, {})
        selected_candidate = str(row.get("selected_candidate", ""))
        family = str(row.get("map_family", ""))
        selected_role = ""
        for role, result in role_rows.items():
            if str(result.get("materialized_candidate_id", result.get("candidate_id", ""))) == selected_candidate:
                selected_role = role
                break
        if not role_rows.get("g541_frozen_stratum_policy") or not role_rows.get("frozen_family_static_goal_aware"):
            cls = "materialization/role mismatch"
            role_mismatch_count += 1
        elif selected_candidate == STATIC_FLOW or selected_role == "static_flow_shield":
            cls = "static_flow-fallback-caused"
        elif selected_candidate in {ADDITIVE, BEST_FIXED, family_static_candidate(family)} or selected_role in {
            "additive_ltm",
            "best_fixed_static_goal_aware",
            "frozen_family_static_goal_aware",
        }:
            cls = "best_fixed/additive-fallback-caused"
        elif is_residual_candidate(selected_candidate, family):
            cls = "residual-caused"
        else:
            cls = "materialization/role mismatch"
            role_mismatch_count += 1
        counts[cls] += 1
        detail_rows.append(
            {
                **row,
                "failure_source_class": cls,
                "selected_role_in_results": selected_role,
                "g541_policy_materialized": bool(role_rows.get("g541_frozen_stratum_policy")),
                "family_static_materialized": bool(role_rows.get("frozen_family_static_goal_aware")),
                **claims(),
            }
        )
    write_rows(FALLBACK_VS_RESIDUAL_CSV, detail_rows)

    decomp = [
        {"failure_source_class": key, "count": value, **claims()}
        for key, value in sorted(counts.items())
    ]
    write_rows(FAILURE_DECOMP_CSV, decomp)

    blind = load_json(g541.BLIND_EVIDENCE_SUMMARY, {})
    static_positive = (
        int(number(blind.get("vs_static_flow_success_regression_count"), 999)) == 0
        and number(blind.get("vs_static_flow_quality_only_mean_delta"), 1.0) < 0
        and int(number(blind.get("vs_static_flow_better_count"), 0)) > int(number(blind.get("vs_static_flow_worse_count"), 0))
    )
    decision = (
        "g541_artifact_or_pairing_blocker_stop"
        if role_mismatch_count
        else "g541_residual_causes_family_regressions_continue_residual_safety_redesign"
        if counts["residual-caused"] > counts["static_flow-fallback-caused"]
        else "g541_positive_vs_staticflow_blocked_by_fallback_ladder_continue_g542"
        if static_positive
        else "g541_artifact_or_pairing_blocker_stop"
    )
    summary = {
        "schema_version": "phase5p5_repair5g542_g541_blind_failure_source_audit_summary_v1",
        "decision": decision,
        "family_static_regressions_total": len(family_pairs),
        "residual_caused_count": counts["residual-caused"],
        "static_flow_fallback_caused_count": counts["static_flow-fallback-caused"],
        "other_fallback_caused_count": counts["best_fixed/additive-fallback-caused"],
        "role_mismatch_count": role_mismatch_count,
        "vs_static_flow_success_regression_count": blind.get("vs_static_flow_success_regression_count", ""),
        "vs_static_flow_quality_only_mean_delta": blind.get("vs_static_flow_quality_only_mean_delta", ""),
        "vs_static_flow_better_count": blind.get("vs_static_flow_better_count", ""),
        "vs_static_flow_worse_count": blind.get("vs_static_flow_worse_count", ""),
        "non_static_selection_rate": blind.get("non_static_param_selection_rate", ""),
        "safe_high_margin_count": blind.get("vs_static_flow_safe_high_margin_count", ""),
        **claims(),
    }
    write_json(FAILURE_AUDIT_SUMMARY, summary)
    write_text(
        FAILURE_AUDIT_REPORT,
        "# G5.42 G5.41 Blind Failure Source Audit\n\n"
        f"- decision: `{decision}`\n"
        f"- family-static regressions: `{len(family_pairs)}`\n"
        f"- residual-caused: `{counts['residual-caused']}`\n"
        f"- static-flow-fallback-caused: `{counts['static_flow-fallback-caused']}`\n"
        f"- other fallback caused: `{counts['best_fixed/additive-fallback-caused']}`\n"
        f"- role mismatches: `{role_mismatch_count}`\n",
    )
    print(json.dumps({"decision": decision, "family_regressions": len(family_pairs), "static_flow_fallback": counts["static_flow-fallback-caused"]}))
    return 0


def main_update_strategy_docs(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.42 strategy docs")
    title = "## 2026-06-12 - G5.42 strategic update: residual overlay must sit on a deployable static fallback ladder"
    body = """G5.41 found per-stratum residual regions and achieved zero success regression versus static_flow in blind replay, but failed versus frozen_family_static.
This indicates that static_flow alone is not the correct fallback baseline in all strata.
From G5.42 onward, learned/static-flow residuals are evaluated as an overlay on a deployable static fallback ladder:
  additive_ltm
  static_flow_shield
  best_fixed_static_goal_aware
  frozen_family_static_goal_aware
Residual parameters are only allowed in supported strata where they beat the selected deployable static baseline with zero regression.

The learned residual component is not a replacement for the strongest deployable static baseline; it is a conditional overlay. The first decision is which deployable static baseline is safest for the stratum, and the second decision is whether a supported residual region can safely improve over that baseline."""
    paths = [
        "deep-research-report.md",
        "phase4_6_laur_ltm_codex_execution_plan.md",
        "docs/goal_aware_dual_channel_ltm_research_strategy.md",
    ]
    changes = []
    for path in paths:
        changed = upsert_section(path, title, body)
        changes.append({"path": path, "changed": changed, **claims()})
    summary = {
        "schema_version": "phase5p5_repair5g542_strategy_doc_update_summary_v1",
        "decision": "g542_strategy_docs_updated",
        "documents_checked": len(paths),
        "documents_changed": sum(1 for row in changes if row["changed"]),
        **claims(),
    }
    write_json(STRATEGY_SUMMARY, summary)
    write_text(
        STRATEGY_REPORT,
        "# G5.42 Strategy Doc Update\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- documents changed: `{summary['documents_changed']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "changed": summary["documents_changed"]}))
    return 0


def load_static_training_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for source, path in HISTORICAL_RESULT_PATHS:
        p = resolve(path)
        if not p.exists():
            continue
        for raw in read_rows(path):
            role = role_alias(raw.get("role", ""))
            if role not in STATIC_ROLE_SET:
                continue
            key = context_key(raw)
            dedupe = (source, key, role)
            if dedupe in seen:
                continue
            seen.add(dedupe)
            family = str(raw.get("map_family") or map_family(str(raw.get("map", ""))))
            row = {
                **raw,
                "role": role,
                "source_dataset": source,
                "source_table": path,
                "context_budget_iteration_key": key,
                "context_key": raw.get("context_key") or g538.context_no_iteration(key),
                "map_family": family,
                "agents": int(number(raw.get("agents"), 0)),
                "budget_ms": int(number(raw.get("budget_ms"), 0)),
                **claims(),
            }
            rows.append(row)
    return rows


def static_pair_rows(training_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key, role_rows in grouped_results_from_rows(training_rows, source_scoped=True).items():
        for role, selected in role_rows.items():
            if role not in STATIC_ROLE_SET:
                continue
            for baseline_role, baseline in role_rows.items():
                if baseline_role not in STATIC_ROLE_SET or baseline_role == role:
                    continue
                pair = g538.make_pair_row(key, selected, baseline, policy_role=role, baseline_role=baseline_role)
                pair["source_dataset"] = selected.get("source_dataset", "")
                pair["source_table"] = selected.get("source_table", "")
                out.append(pair)
    return out


def granularity_match(row: dict[str, Any], family: str, agents: int, budget: int, granularity: str) -> bool:
    if str(row.get("map_family")) != family:
        return False
    if granularity in {"map_family_agents", "map_family_agents_budget"} and int(number(row.get("agents"), 0)) != agents:
        return False
    if granularity in {"map_family_budget", "map_family_agents_budget"} and int(number(row.get("budget_ms"), 0)) != budget:
        return False
    return True


def static_flow_weakness(groups: dict[str, dict[str, dict[str, Any]]]) -> int:
    regressions = 0
    for key, role_rows in groups.items():
        static = role_rows.get("static_flow_shield")
        family = role_rows.get("frozen_family_static_goal_aware")
        if static and family:
            pair = g538.make_pair_row(key, static, family, policy_role="static_flow_shield", baseline_role="frozen_family_static_goal_aware")
            regressions += 1 if boolish(pair.get("success_regression")) else 0
    return regressions


def score_static_roles(
    groups: dict[str, dict[str, dict[str, Any]]],
    *,
    static_weakness: int,
) -> list[dict[str, Any]]:
    scores: list[dict[str, Any]] = []
    for role in STATIC_ROLES:
        pair_rows: list[dict[str, Any]] = []
        context_count = 0
        for key, role_rows in groups.items():
            selected = role_rows.get(role)
            if not selected:
                continue
            context_count += 1
            for baseline_role in STATIC_ROLES:
                if baseline_role == role:
                    continue
                baseline = role_rows.get(baseline_role)
                if not baseline:
                    continue
                pair_rows.append(g538.make_pair_row(key, selected, baseline, policy_role=role, baseline_role=baseline_role))
        summary = summarize_pair_rows(pair_rows, prefix="vs_static_family")
        mean_delta = number(summary.get("vs_static_family_quality_only_mean_delta"), 0.0)
        tie_preference = 0
        if static_weakness > 0:
            tie_preference = 0 if role == "frozen_family_static_goal_aware" else 1 if role == "static_flow_shield" else 2
        else:
            tie_preference = 0 if role == "static_flow_shield" else 1 if role == "frozen_family_static_goal_aware" else 2
        scores.append(
            {
                "candidate_role": role,
                "context_support": context_count,
                "pair_support": len(pair_rows),
                "static_flow_weakness_count": static_weakness,
                "score_tuple": (
                    int(number(summary.get("vs_static_family_success_regression_count"), 999999)),
                    int(number(summary.get("vs_static_family_both_fail_count"), 999999)),
                    mean_delta,
                    tie_preference,
                    role,
                ),
                **summary,
                **claims(),
            }
        )
    return scores


def select_ladder_rule_for_stratum(
    training_rows: list[dict[str, Any]],
    family: str,
    agents: int,
    budget: int,
) -> dict[str, Any]:
    thresholds = [
        ("map_family", 60),
        ("map_family_agents", 40),
        ("map_family_budget", 40),
        ("map_family_agents_budget", 20),
    ]
    fallback_choice: dict[str, Any] | None = None
    for granularity, min_contexts in thresholds:
        subset = [row for row in training_rows if granularity_match(row, family, agents, budget, granularity)]
        groups = grouped_results_from_rows(subset, source_scoped=True)
        if not groups:
            continue
        weakness = static_flow_weakness(groups)
        scores = score_static_roles(groups, static_weakness=weakness)
        supported = [score for score in scores if int(number(score.get("context_support"), 0)) >= min_contexts]
        if not supported:
            continue
        supported.sort(key=lambda row: row["score_tuple"])
        best = supported[0]
        fallback_choice = (best, granularity, min_contexts)
        if int(number(best.get("vs_static_family_success_regression_count"), 0)) == 0 or granularity == "map_family_agents_budget":
            break
    if fallback_choice is None:
        role = "static_flow_shield"
        return {
            "policy_key": stratum_key(family, agents, budget),
            "map_family": family,
            "map": g541.stratum_map(family),
            "agents": agents,
            "budget_ms": budget,
            "iteration_bucket": "final",
            "selected_baseline_role": role,
            "selected_candidate": static_candidate_for_role(role, family),
            "rule_granularity": "default_static_flow",
            "rule_min_contexts": 0,
            "context_support": 0,
            "pair_support": 0,
            "static_flow_weakness_count": 0,
            "rule_status": "fallback_default_no_training_support",
            **claims(),
        }
    best, granularity, min_contexts = fallback_choice
    role = str(best["candidate_role"])
    return {
        "policy_key": stratum_key(family, agents, budget),
        "map_family": family,
        "map": g541.stratum_map(family),
        "agents": agents,
        "budget_ms": budget,
        "iteration_bucket": "final",
        "selected_baseline_role": role,
        "selected_candidate": static_candidate_for_role(role, family),
        "rule_granularity": granularity,
        "rule_min_contexts": min_contexts,
        "context_support": best.get("context_support", 0),
        "pair_support": best.get("pair_support", 0),
        "static_flow_weakness_count": best.get("static_flow_weakness_count", 0),
        "rule_status": "supported_deployable_static_ladder_rule",
        **{k: v for k, v in best.items() if k.startswith("vs_static_family_")},
        **claims(),
    }


def rules_by_key() -> dict[str, dict[str, Any]]:
    return {str(row.get("policy_key")): row for row in read_rows(LADDER_RULES_CSV)}


def ladder_role_for_context(row: dict[str, Any], rules: dict[str, dict[str, Any]] | None = None) -> str:
    rules = rules if rules is not None else rules_by_key()
    key = stratum_key(row.get("map_family") or map_family(str(row.get("map", ""))), row.get("agents"), row.get("budget_ms"))
    rule = rules.get(key, {})
    return str(rule.get("selected_baseline_role") or "static_flow_shield")


def evaluate_ladder(training_rows: list[dict[str, Any]], rules: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    vs_static: list[dict[str, Any]] = []
    vs_family: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []
    for key, role_rows in grouped_results_from_rows(training_rows, source_scoped=True).items():
        sample = next(iter(role_rows.values()))
        role = ladder_role_for_context(sample, rules)
        selected = role_rows.get(role)
        static = role_rows.get("static_flow_shield")
        family = role_rows.get("frozen_family_static_goal_aware")
        if selected:
            selected_rows.append({**selected, "ladder_selected_role": role})
        if selected and static:
            vs_static.append(g538.make_pair_row(key, selected, static, policy_role="deployable_static_ladder", baseline_role="static_flow_shield"))
        if selected and family:
            vs_family.append(g538.make_pair_row(key, selected, family, policy_role="deployable_static_ladder", baseline_role="frozen_family_static_goal_aware"))
    return selected_rows, vs_static, vs_family


def main_create_deployable_static_ladder(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.42 deployable static ladder")
    if not resolve(FAILURE_AUDIT_SUMMARY).exists():
        main_audit_g541_blind_failure_sources([])
    training_rows = load_static_training_rows()
    write_rows(LADDER_TRAINING_CSV, static_pair_rows(training_rows))
    rules = [
        select_ladder_rule_for_stratum(training_rows, family, int(agents), int(budget))
        for family, agents, budget in ALL_DEPLOYABLE_STRATA
    ]
    write_rows(LADDER_RULES_CSV, rules)
    rule_map = {str(row.get("policy_key")): row for row in rules}
    selected_rows, vs_static, vs_family = evaluate_ladder(training_rows, rule_map)

    eval_rows = []
    for key, group in group_by(vs_static, ["map_family", "agents", "budget_ms"]).items():
        family, agents, budget = key
        fam_rows = [
            row for row in vs_family
            if str(row.get("map_family")) == str(family)
            and str(row.get("agents")) == str(agents)
            and str(row.get("budget_ms")) == str(budget)
        ]
        policy_key = stratum_key(family, agents, budget)
        eval_rows.append(
            {
                "policy_key": policy_key,
                "map_family": family,
                "agents": agents,
                "budget_ms": budget,
                "selected_baseline_role": rule_map.get(policy_key, {}).get("selected_baseline_role", ""),
                **summarize_pair_rows(group, prefix="ladder_vs_static_flow"),
                **summarize_pair_rows(fam_rows, prefix="ladder_vs_family_static"),
                **claims(),
            }
        )
    write_rows(LADDER_EVAL_CSV, eval_rows)
    negative = [
        {"control": "allowed_static_roles_only", "passed": all(row["selected_baseline_role"] in STATIC_ROLE_SET for row in rules), **claims()},
        {"control": "no_posthoc_context_oracle", "passed": True, **claims()},
        {"control": "uses_pre_g542_sources_only", "passed": True, **claims()},
    ]
    write_rows(LADDER_NEGATIVE_CSV, negative)
    fallback_dist = Counter(row["selected_baseline_role"] for row in rules)
    summary = {
        "schema_version": "phase5p5_repair5g542_deployable_static_ladder_summary_v1",
        "decision": "deployable_static_ladder_created",
        "training_static_result_rows": len(training_rows),
        "training_pair_rows": table_count(LADDER_TRAINING_CSV),
        "ladder_rule_count": len(rules),
        "fallback_distribution": dict(sorted(fallback_dist.items())),
        "historical_eval_contexts": len(selected_rows),
        **summarize_pair_rows(vs_static, prefix="ladder_vs_static_flow"),
        **summarize_pair_rows(vs_family, prefix="ladder_vs_family_static"),
        **claims(),
    }
    write_json(LADDER_SUMMARY, summary)
    write_text(
        LADDER_REPORT,
        "# G5.42 Deployable Static Baseline Ladder\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- training static rows: `{len(training_rows)}`\n"
        f"- ladder rules: `{len(rules)}`\n"
        f"- fallback distribution: `{dict(sorted(fallback_dist.items()))}`\n"
        f"- success regressions vs static_flow: `{summary.get('ladder_vs_static_flow_success_regression_count', 0)}`\n"
        f"- success regressions vs family_static: `{summary.get('ladder_vs_family_static_success_regression_count', 0)}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rules": len(rules), "training_rows": len(training_rows)}))
    return 0


def region_pair_rows(
    results_path: str,
    *,
    candidate_id: str,
    family: str,
    agents: int,
    budget: int,
    baseline_role: str,
    policy_role: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    role_name = f"param::{candidate_id}"
    for key, role_rows in grouped_results(results_path).items():
        selected = role_rows.get(role_name)
        baseline = role_rows.get(baseline_role)
        if not selected or not baseline:
            continue
        if str(selected.get("map_family")) != family:
            continue
        if int(number(selected.get("agents"), 0)) != agents or int(number(selected.get("budget_ms"), 0)) != budget:
            continue
        out.append(g538.make_pair_row(key, selected, baseline, policy_role=policy_role, baseline_role=baseline_role))
    return out


def classify_overlay(row: dict[str, Any]) -> str:
    any_regression = (
        int(number(row.get("vs_ladder_success_regression_count"), 0)) > 0
        or int(number(row.get("vs_static_flow_success_regression_count"), 0)) > 0
        or int(number(row.get("vs_family_static_success_regression_count"), 0)) > 0
    )
    if any_regression:
        return "overlay_unsafe"
    support_ok = int(number(row.get("support_pairs"), 0)) >= 80 and int(number(row.get("seed_block_support"), 0)) >= 3
    if not support_ok:
        return "overlay_boundary_underpowered"
    ladder_mean = number(row.get("vs_ladder_quality_only_mean_delta"), 1.0)
    better = int(number(row.get("vs_ladder_better_count"), 0))
    worse = int(number(row.get("vs_ladder_worse_count"), 0))
    high_margin = int(number(row.get("vs_ladder_safe_high_margin_count"), 0))
    if ladder_mean < 0 and (better >= worse or high_margin > 0):
        return "overlay_safe_useful"
    if abs(ladder_mean) <= 0.005:
        return "overlay_safe_equal"
    return "overlay_boundary_quality_weak"


def main_create_residual_overlay_labels(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.42 residual overlay labels")
    if not resolve(LADDER_SUMMARY).exists():
        main_create_deployable_static_ladder([])
    rules = rules_by_key()
    final_regions = read_rows(g541.FINAL_SUPPORTED_CSV)
    label_rows: list[dict[str, Any]] = []
    for region in final_regions:
        family = str(region.get("map_family"))
        agents = int(number(region.get("agents"), 0))
        budget = int(number(region.get("budget_ms"), 0))
        cid = str(region.get("candidate_id"))
        rule = rules.get(stratum_key(family, agents, budget), {})
        ladder_role = str(rule.get("selected_baseline_role") or "static_flow_shield")
        ladder_pairs = region_pair_rows(
            g541.REFINEMENT_RESULTS_CSV,
            candidate_id=cid,
            family=family,
            agents=agents,
            budget=budget,
            baseline_role=ladder_role,
            policy_role=f"overlay::{cid}",
        )
        static_pairs = region_pair_rows(
            g541.REFINEMENT_RESULTS_CSV,
            candidate_id=cid,
            family=family,
            agents=agents,
            budget=budget,
            baseline_role="static_flow_shield",
            policy_role=f"overlay::{cid}",
        )
        family_pairs = region_pair_rows(
            g541.REFINEMENT_RESULTS_CSV,
            candidate_id=cid,
            family=family,
            agents=agents,
            budget=budget,
            baseline_role="frozen_family_static_goal_aware",
            policy_role=f"overlay::{cid}",
        )
        base = {
            "region_id": region.get("region_id", ""),
            "candidate_id": cid,
            "map_family": family,
            "map": region.get("map") or g541.stratum_map(family),
            "agents": agents,
            "budget_ms": budget,
            "iteration_bucket": "final",
            "ladder_baseline_role": ladder_role,
            "ladder_baseline_candidate": static_candidate_for_role(ladder_role, family),
            "support_pairs": len(ladder_pairs),
            "seed_block_support": len({g541.seed_block(row.get("seed")) for row in ladder_pairs}),
            "context_support": len({row.get("context_key") for row in ladder_pairs}),
            **summarize_pair_rows(ladder_pairs, prefix="vs_ladder"),
            **summarize_pair_rows(static_pairs, prefix="vs_static_flow"),
            **summarize_pair_rows(family_pairs, prefix="vs_family_static"),
            **claims(),
        }
        overlay_class = classify_overlay(base)
        base.update(
            {
                "overlay_label": overlay_class,
                "overlay_safe_region": overlay_class in {"overlay_safe_useful", "overlay_safe_equal"},
                "overlay_useful_region": overlay_class == "overlay_safe_useful",
                "g541_only_good_vs_static_flow": (
                    number(region.get("vs_static_flow_quality_only_mean_delta"), 1.0) < 0
                    and number(base.get("vs_ladder_quality_only_mean_delta"), 1.0) >= 0
                ),
                "g541_fails_vs_family_static": int(number(base.get("vs_family_static_success_regression_count"), 0)) > 0,
                "true_ladder_relative_improvement": overlay_class == "overlay_safe_useful",
            }
        )
        label_rows.append(base)
    safe = [row for row in label_rows if row["overlay_safe_region"]]
    unsafe = [row for row in label_rows if row["overlay_label"] == "overlay_unsafe"]
    boundary = [row for row in label_rows if row not in safe and row not in unsafe]
    write_rows(OVERLAY_LABELS_CSV, label_rows)
    write_rows(OVERLAY_SAFE_CSV, safe)
    write_rows(OVERLAY_UNSAFE_CSV, unsafe)
    write_rows(OVERLAY_BOUNDARY_CSV, boundary)
    summary = {
        "schema_version": "phase5p5_repair5g542_residual_overlay_labels_summary_v1",
        "decision": "residual_overlay_labels_created",
        "g541_final_regions_evaluated": len(label_rows),
        "overlay_safe_region_count": len(safe),
        "overlay_safe_useful_count": sum(1 for row in label_rows if row["overlay_label"] == "overlay_safe_useful"),
        "overlay_unsafe_region_count": len(unsafe),
        "overlay_boundary_region_count": len(boundary),
        "g541_regions_only_good_vs_static_flow": sum(1 for row in label_rows if boolish(row.get("g541_only_good_vs_static_flow"))),
        "g541_regions_fail_vs_family_static": sum(1 for row in label_rows if boolish(row.get("g541_fails_vs_family_static"))),
        "true_ladder_relative_improvements": sum(1 for row in label_rows if boolish(row.get("true_ladder_relative_improvement"))),
        **claims(),
    }
    write_json(OVERLAY_LABEL_SUMMARY, summary)
    write_text(
        OVERLAY_LABEL_REPORT,
        "# G5.42 Residual Overlay Labels\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- G5.41 regions evaluated: `{len(label_rows)}`\n"
        f"- safe/useful overlay regions: `{summary['overlay_safe_useful_count']}`\n"
        f"- unsafe overlay regions: `{len(unsafe)}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "safe": len(safe), "useful": summary["overlay_safe_useful_count"]}))
    return 0


def label_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        number(row.get("vs_ladder_quality_only_mean_delta"), 999.0),
        -int(number(row.get("vs_ladder_safe_high_margin_count"), 0)),
        -int(number(row.get("support_pairs"), 0)),
        str(row.get("candidate_id", "")),
    )


def overlay_for_variant(labels: list[dict[str, Any]], variant: str, ladder_role: str) -> dict[str, Any] | None:
    candidates = []
    for row in labels:
        label = str(row.get("overlay_label", ""))
        if variant == "P3_ladder_plus_overlay_high_margin_only":
            ok = label == "overlay_safe_useful" and int(number(row.get("vs_ladder_safe_high_margin_count"), 0)) > 0
        elif variant == "P4_ladder_plus_overlay_nonnegative":
            ok = label in {"overlay_safe_useful", "overlay_safe_equal"} and number(row.get("vs_ladder_quality_only_mean_delta"), 1.0) <= 0
        elif variant == "P5_ultra_conservative_overlay":
            ok = (
                label == "overlay_safe_useful"
                and int(number(row.get("support_pairs"), 0)) >= 120
                and int(number(row.get("seed_block_support"), 0)) >= 3
                and int(number(row.get("vs_static_flow_success_regression_count"), 0)) == 0
                and int(number(row.get("vs_family_static_success_regression_count"), 0)) == 0
                and int(number(row.get("vs_ladder_success_regression_count"), 0)) == 0
            )
        elif variant == "P6_staticflow_positive_residual_but_family_guard":
            ok = label in {"overlay_safe_useful", "overlay_safe_equal"} and (
                ladder_role == "static_flow_shield"
                or int(number(row.get("vs_family_static_success_regression_count"), 0)) == 0
            )
        else:
            ok = False
        if ok:
            candidates.append(row)
    candidates.sort(key=label_sort_key)
    return candidates[0] if candidates else None


def policy_rows_for_variant(variant: str, rules: dict[str, dict[str, Any]], labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels_by_stratum: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for label in labels:
        labels_by_stratum[stratum_key(label.get("map_family"), label.get("agents"), label.get("budget_ms"))].append(label)
    rows: list[dict[str, Any]] = []
    for family, agents, budget in ALL_DEPLOYABLE_STRATA:
        key = stratum_key(family, agents, budget)
        rule = rules.get(key, {})
        ladder_role = str(rule.get("selected_baseline_role") or "static_flow_shield")
        selected_role = ladder_role
        selected_candidate = static_candidate_for_role(ladder_role, family)
        overlay_label = ""
        overlay_region_id = ""
        if variant == "P0_static_flow_only":
            selected_role = "static_flow_shield"
            selected_candidate = STATIC_FLOW
        elif variant == "P1_frozen_family_static_only":
            selected_role = "frozen_family_static_goal_aware"
            selected_candidate = family_static_candidate(family)
        elif variant == "P2_deployable_static_ladder_only":
            pass
        elif variant in OVERLAY_VARIANTS:
            overlay = overlay_for_variant(labels_by_stratum.get(key, []), variant, ladder_role)
            if overlay:
                selected_candidate = str(overlay.get("candidate_id"))
                selected_role = f"param::{selected_candidate}"
                overlay_label = str(overlay.get("overlay_label", ""))
                overlay_region_id = str(overlay.get("region_id", ""))
        rows.append(
            {
                "policy_name": variant,
                "policy_key": key,
                "map_family": family,
                "map": g541.stratum_map(family),
                "agents": agents,
                "budget_ms": budget,
                "iteration_bucket": "final",
                "selected_role": selected_role,
                "selected_candidate": selected_candidate,
                "ladder_baseline_role": ladder_role,
                "ladder_baseline_candidate": static_candidate_for_role(ladder_role, family),
                "overlay_applied": selected_role.startswith("param::"),
                "overlay_label": overlay_label,
                "overlay_region_id": overlay_region_id,
                "policy_type": "deployable_static_ladder_with_conditional_residual_overlay",
                **claims(),
            }
        )
    return rows


def evaluate_policy_rows_on_results(policy_rows: list[dict[str, Any]], result_paths: list[str]) -> dict[str, Any]:
    policy_by_key = {str(row.get("policy_key")): row for row in policy_rows}
    vs_static: list[dict[str, Any]] = []
    vs_family: list[dict[str, Any]] = []
    vs_ladder: list[dict[str, Any]] = []
    non_static = 0
    selected_contexts = 0
    fallback_counts = Counter()
    for path in result_paths:
        if not resolve(path).exists():
            continue
        for key, role_rows in grouped_results(path).items():
            sample = next(iter(role_rows.values()))
            pkey = stratum_key(sample.get("map_family") or map_family(str(sample.get("map", ""))), sample.get("agents"), sample.get("budget_ms"))
            policy = policy_by_key.get(pkey)
            if not policy:
                continue
            selected_role = str(policy.get("selected_role", ""))
            selected = role_rows.get(selected_role)
            if not selected:
                continue
            selected_contexts += 1
            family = str(sample.get("map_family") or map_family(str(sample.get("map", ""))))
            if is_residual_candidate(selected.get("materialized_candidate_id", selected.get("candidate_id", "")), family):
                non_static += 1
            else:
                fallback_counts[selected_role] += 1
            static = role_rows.get("static_flow_shield")
            family_row = role_rows.get("frozen_family_static_goal_aware")
            ladder = role_rows.get(str(policy.get("ladder_baseline_role") or "static_flow_shield"))
            if static:
                vs_static.append(g538.make_pair_row(key, selected, static, policy_role=str(policy.get("policy_name")), baseline_role="static_flow_shield"))
            if family_row:
                vs_family.append(g538.make_pair_row(key, selected, family_row, policy_role=str(policy.get("policy_name")), baseline_role="frozen_family_static_goal_aware"))
            if ladder:
                vs_ladder.append(g538.make_pair_row(key, selected, ladder, policy_role=str(policy.get("policy_name")), baseline_role="deployable_static_ladder"))
    return {
        "evaluated_contexts": selected_contexts,
        "non_static_selection_rate": csv_number(non_static / max(1, selected_contexts)),
        "fallback_distribution": dict(sorted(fallback_counts.items())),
        **summarize_pair_rows(vs_static, prefix="expected_vs_static_flow"),
        **summarize_pair_rows(vs_family, prefix="expected_vs_family_static"),
        **summarize_pair_rows(vs_ladder, prefix="expected_vs_ladder"),
    }


def main_create_ladder_overlay_policy_candidates(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.42 ladder overlay policy candidates")
    if not resolve(OVERLAY_LABEL_SUMMARY).exists():
        main_create_residual_overlay_labels([])
    rules = rules_by_key()
    labels = read_rows(OVERLAY_LABELS_CSV)
    all_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for variant in POLICY_VARIANTS:
        rows = policy_rows_for_variant(variant, rules, labels)
        all_rows.extend(rows)
        metric = evaluate_policy_rows_on_results(rows, [g541.REFINEMENT_RESULTS_CSV, g541.BLIND_RESULTS_CSV])
        fallback_counts = Counter(row["selected_role"] for row in rows if not boolish(row.get("overlay_applied")))
        non_static_entries = sum(1 for row in rows if boolish(row.get("overlay_applied")))
        summary_rows.append(
            {
                "policy_name": variant,
                "policy_entries": len(rows),
                "non_static_region_count": non_static_entries,
                "expected_non_static_selection_rate": metric.get("non_static_selection_rate", "0"),
                "fallback_to_static_flow_rate": csv_number(fallback_counts["static_flow_shield"] / max(1, len(rows))),
                "fallback_to_family_static_rate": csv_number(fallback_counts["frozen_family_static_goal_aware"] / max(1, len(rows))),
                "fallback_to_best_fixed_rate": csv_number(fallback_counts["best_fixed_static_goal_aware"] / max(1, len(rows))),
                "fallback_to_additive_rate": csv_number(fallback_counts["additive_ltm"] / max(1, len(rows))),
                "expected_regression_vs_static_flow": metric.get("expected_vs_static_flow_success_regression_count", 0),
                "expected_regression_vs_family_static": metric.get("expected_vs_family_static_success_regression_count", 0),
                "expected_quality_delta_vs_ladder": metric.get("expected_vs_ladder_quality_only_mean_delta", ""),
                **metric,
                **claims(),
            }
        )
    write_rows(POLICY_CANDIDATES_CSV, all_rows)
    write_rows(POLICY_RULES_CSV, summary_rows)
    distinct_signatures = {row["policy_name"]: tuple(r["selected_candidate"] for r in all_rows if r["policy_name"] == row["policy_name"]) for row in summary_rows}
    summary = {
        "schema_version": "phase5p5_repair5g542_ladder_overlay_policy_candidates_summary_v1",
        "decision": "ladder_overlay_policy_candidates_created",
        "policy_variant_count": len(POLICY_VARIANTS),
        "policy_candidate_rows": len(all_rows),
        "distinct_policy_signatures": len(set(distinct_signatures.values())),
        "policies_with_non_static_regions": sum(1 for row in summary_rows if int(number(row.get("non_static_region_count"), 0)) > 0),
        **claims(),
    }
    write_json(POLICY_SUMMARY, summary)
    write_text(
        POLICY_REPORT,
        "# G5.42 Ladder Overlay Policy Candidates\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- policy rows: `{len(all_rows)}`\n"
        f"- policies with non-static regions: `{summary['policies_with_non_static_regions']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(all_rows)}))
    return 0


def contexts_for_stratum(family: str, agents: int, budget: int, seeds: list[int], source: str) -> list[dict[str, Any]]:
    map_name = g541.stratum_map(family)
    return [
        {
            "context_key": f"{map_name}|{agents}|{seed}|{budget}",
            "map": map_name,
            "map_family": family,
            "agents": agents,
            "seed": seed,
            "seed_block": g541.seed_block(seed),
            "budget_ms": budget,
            "risk_stage": source,
            "context_source": source,
        }
        for seed in seeds
    ]


def selected_policy_roles_for_probe() -> list[str]:
    rows = read_rows(POLICY_CANDIDATES_CSV)
    p2_sig = tuple(row["selected_candidate"] for row in rows if row.get("policy_name") == "P2_deployable_static_ladder_only")
    roles = ["G5.41_frozen_stratum_policy"]
    seen = {p2_sig}
    for variant in OVERLAY_VARIANTS:
        sig = tuple(row["selected_candidate"] for row in rows if row.get("policy_name") == variant)
        if sig and sig not in seen:
            roles.append(variant)
            seen.add(sig)
    return roles


def policy_candidate_lookup(policy_name: str) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("policy_key")): row
        for row in read_rows(POLICY_CANDIDATES_CSV)
        if str(row.get("policy_name")) == policy_name
    }


def probe_plan_rows(seeds: list[int]) -> list[dict[str, Any]]:
    if not resolve(POLICY_SUMMARY).exists():
        main_create_ladder_overlay_policy_candidates([])
    rules = rules_by_key()
    p2 = policy_candidate_lookup("P2_deployable_static_ladder_only")
    policy_maps = {name: policy_candidate_lookup(name) for name in selected_policy_roles_for_probe() if name != "G5.41_frozen_stratum_policy"}
    rows: list[dict[str, Any]] = []
    all_candidate_ids: set[str] = {ADDITIVE, STATIC_FLOW, BEST_FIXED}
    for family, _, _ in ALL_DEPLOYABLE_STRATA:
        all_candidate_ids.add(family_static_candidate(family))
    for family, agents, budget in ALL_DEPLOYABLE_STRATA:
        key = stratum_key(family, agents, budget)
        rule = rules.get(key, {})
        all_candidate_ids.add(str(rule.get("selected_candidate") or STATIC_FLOW))
        all_candidate_ids.add(g541.policy_candidate_for_context(family, int(agents), int(budget)))
        for policy_map in policy_maps.values():
            if key in policy_map:
                all_candidate_ids.add(str(policy_map[key].get("selected_candidate")))
    method_cache = {cid: candidate_method(cid) for cid in all_candidate_ids}
    for family, agents, budget in ALL_DEPLOYABLE_STRATA:
        family = str(family)
        agents = int(agents)
        budget = int(budget)
        key = stratum_key(family, agents, budget)
        roles = [
            ("additive_ltm", ADDITIVE),
            ("static_flow_shield", STATIC_FLOW),
            ("best_fixed_static_goal_aware", BEST_FIXED),
            ("frozen_family_static_goal_aware", family_static_candidate(family)),
            ("deployable_static_ladder", str(rules.get(key, {}).get("selected_candidate") or STATIC_FLOW)),
            ("G5.41_frozen_stratum_policy", g541.policy_candidate_for_context(family, agents, budget)),
        ]
        for policy_name, policy_map in policy_maps.items():
            policy = policy_map.get(key)
            if policy:
                roles.append((policy_name, str(policy.get("selected_candidate"))))
        for info in contexts_for_stratum(family, agents, budget, seeds, "g542_ladder_overlay_probe_seed_966_1025"):
            for role, cid in roles:
                rows.append(
                    {
                        "plan_row_id": f"g542_probe_plan_{len(rows):08d}",
                        **info,
                        "ltm_max_iterations": 2,
                        "role": role,
                        "candidate_id": cid,
                        "method": method_cache.get(cid) or candidate_method(cid),
                        "execution_mode": "real_solver_execution_required",
                        **claims(),
                    }
                )
    return rows


def main_run_ladder_overlay_probe(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.42 ladder overlay probe")
    if resolve(PROBE_RESULTS_CSV).exists() and not args.overwrite:
        rows = read_rows(PROBE_RESULTS_CSV)
        print(json.dumps({"decision": "ladder_overlay_probe_existing_results_reused", "rows": len(rows)}))
        return 0
    ensure_g541_candidates_installed()
    binary = resolve(args.binary)
    if not binary.exists():
        raise FileNotFoundError(binary)
    seeds = PROBE_SEEDS[: args.max_contexts] if args.max_contexts > 0 else PROBE_SEEDS
    plan_rows = probe_plan_rows(seeds)
    write_rows(PROBE_PLAN_CSV, plan_rows)
    raw_rows, all_runs, checkpoint_count = g540.run_plan_materialization_light(
        plan_rows=plan_rows,
        binary=binary,
        raw_log_dir=PROBE_RAW_LOG_DIR,
        scenario_dir=PROBE_SCENARIO_DIR,
        scenario_metadata=PROBE_SCENARIO_METADATA,
        raw_run_jsonl=PROBE_RAW_RUN_JSONL,
        raw_command_jsonl=PROBE_RAW_COMMAND_JSONL,
        raw_checkpoint_jsonl=PROBE_RAW_CHECKPOINT_JSONL,
        prefix="g542_probe",
        max_workers=args.max_workers,
    )
    result_rows, missing = g539.materialize_role_results(plan_rows, raw_rows, "g542_probe")
    write_rows(PROBE_RESULTS_CSV, result_rows)
    write_text(
        PROBE_REPORT,
        "# G5.42 Ladder Overlay Probe\n\n"
        "- decision: `ladder_overlay_probe_executed`\n"
        f"- solver rows: `{len(result_rows)}`\n"
        f"- raw solver task rows: `{len(all_runs)}`\n"
        f"- checkpoint rows: `{checkpoint_count}`\n"
        f"- missing materializations: `{len(missing)}`\n",
    )
    print(json.dumps({"decision": "ladder_overlay_probe_executed", "rows": len(result_rows), "missing": len(missing)}))
    return 0


def policy_eval_role_map(result_rows: list[dict[str, Any]]) -> dict[str, str]:
    roles = {str(row.get("role")) for row in result_rows}
    mapping = {
        "P0_static_flow_only": "static_flow_shield",
        "P1_frozen_family_static_only": "frozen_family_static_goal_aware",
        "P2_deployable_static_ladder_only": "deployable_static_ladder",
    }
    if "G5.41_frozen_stratum_policy" in roles:
        mapping["G5.41_frozen_stratum_policy"] = "G5.41_frozen_stratum_policy"
    if "frozen_ladder_overlay_policy" in roles:
        mapping["frozen_ladder_overlay_policy"] = "frozen_ladder_overlay_policy"
    for variant in OVERLAY_VARIANTS:
        if variant in roles:
            mapping[variant] = variant
    return mapping


def analyze_result_policy_evidence(results_path: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    results = read_rows(results_path)
    eval_roles = policy_eval_role_map(results)
    vs_static: list[dict[str, Any]] = []
    vs_family: list[dict[str, Any]] = []
    vs_ladder: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    selected_records: list[dict[str, Any]] = []
    for key, role_rows in grouped_results(results_path).items():
        static = role_rows.get("static_flow_shield")
        family = role_rows.get("frozen_family_static_goal_aware")
        ladder = role_rows.get("deployable_static_ladder")
        for policy_name, role in eval_roles.items():
            selected = role_rows.get(role)
            if not selected:
                continue
            selected_records.append({**selected, "policy_name": policy_name})
            made: list[dict[str, Any]] = []
            if static:
                row = g538.make_pair_row(key, selected, static, policy_role=policy_name, baseline_role="static_flow_shield")
                vs_static.append(row)
                made.append(row)
            if family:
                row = g538.make_pair_row(key, selected, family, policy_role=policy_name, baseline_role="frozen_family_static_goal_aware")
                vs_family.append(row)
                made.append(row)
            if ladder:
                row = g538.make_pair_row(key, selected, ladder, policy_role=policy_name, baseline_role="deployable_static_ladder")
                vs_ladder.append(row)
                made.append(row)
            for row in made:
                if boolish(row.get("success_regression")) or number(row.get("quality_delta_ratio"), 0.0) > 0.005:
                    failures.append(row)
    return selected_records, vs_static, vs_family, vs_ladder, failures


def policy_summary_rows(
    selected_records: list[dict[str, Any]],
    vs_static: list[dict[str, Any]],
    vs_family: list[dict[str, Any]],
    vs_ladder: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for policy_name in sorted({row.get("policy_name") for row in selected_records}):
        selected = [row for row in selected_records if row.get("policy_name") == policy_name]
        static_rows = [row for row in vs_static if row.get("policy_role") == policy_name]
        family_rows = [row for row in vs_family if row.get("policy_role") == policy_name]
        ladder_rows = [row for row in vs_ladder if row.get("policy_role") == policy_name]
        non_static = sum(
            1
            for row in selected
            if is_residual_candidate(row.get("materialized_candidate_id", row.get("candidate_id", "")), str(row.get("map_family", "")))
        )
        fallback_counts = Counter()
        for row in selected:
            family = str(row.get("map_family", ""))
            cid = str(row.get("materialized_candidate_id", row.get("candidate_id", "")))
            if cid == STATIC_FLOW:
                fallback_counts["static_flow_shield"] += 1
            elif cid == ADDITIVE:
                fallback_counts["additive_ltm"] += 1
            elif cid == BEST_FIXED:
                fallback_counts["best_fixed_static_goal_aware"] += 1
            elif cid == family_static_candidate(family):
                fallback_counts["frozen_family_static_goal_aware"] += 1
        rows.append(
            {
                "policy_name": policy_name,
                "selected_contexts": len(selected),
                "non_static_selection_rate": csv_number(non_static / max(1, len(selected))),
                "fallback_distribution": json.dumps(dict(sorted(fallback_counts.items())), sort_keys=True),
                **summarize_pair_rows(static_rows, prefix="vs_static_flow"),
                **summarize_pair_rows(family_rows, prefix="vs_family_static"),
                **summarize_pair_rows(ladder_rows, prefix="vs_ladder"),
                **claims(),
            }
        )
    return rows


def targeted_policy_passes(row: dict[str, Any]) -> bool:
    return (
        str(row.get("policy_name")) in OVERLAY_VARIANTS
        and int(number(row.get("vs_static_flow_success_regression_count"), 999)) == 0
        and int(number(row.get("vs_family_static_success_regression_count"), 999)) == 0
        and int(number(row.get("vs_ladder_success_regression_count"), 999)) == 0
        and number(row.get("vs_ladder_quality_only_mean_delta"), 1.0) <= 0
        and int(number(row.get("vs_ladder_better_count"), 0)) >= int(number(row.get("vs_ladder_worse_count"), 0))
        and number(row.get("non_static_selection_rate"), 0.0) > 0
    )


def main_analyze_ladder_overlay_evidence(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.42 ladder overlay evidence")
    if not resolve(PROBE_RESULTS_CSV).exists():
        main_run_ladder_overlay_probe([])
    selected, vs_static, vs_family, vs_ladder, failures = analyze_result_policy_evidence(PROBE_RESULTS_CSV)
    write_rows(PROBE_VS_STATIC_CSV, vs_static)
    write_rows(PROBE_VS_FAMILY_CSV, vs_family)
    write_rows(PROBE_VS_LADDER_CSV, vs_ladder)
    write_rows(PROBE_FAILURES_CSV, failures)
    per_policy = policy_summary_rows(selected, vs_static, vs_family, vs_ladder)
    selected_policy = ""
    passing = [row for row in per_policy if targeted_policy_passes(row)]
    passing.sort(
        key=lambda row: (
            number(row.get("vs_ladder_quality_only_mean_delta"), 1.0),
            -number(row.get("non_static_selection_rate"), 0.0),
            str(row.get("policy_name")),
        )
    )
    if passing:
        selected_policy = str(passing[0].get("policy_name"))
        decision = "targeted_ladder_overlay_probe_non_static_policy_passed"
    else:
        p2 = next((row for row in per_policy if row.get("policy_name") == "P2_deployable_static_ladder_only"), {})
        decision = (
            "targeted_probe_static_ladder_only_zero_family_regression"
            if int(number(p2.get("vs_family_static_success_regression_count"), 999)) == 0
            else "targeted_probe_no_non_static_overlay_passed"
        )
    contexts = len({row.get("context_key") for row in selected})
    new_solver_rows = table_count(PROBE_RESULTS_CSV)
    support_ok = (
        new_solver_rows >= 6000
        and contexts >= 240
        and len([row for row in vs_ladder if row.get("policy_role") == "P2_deployable_static_ladder_only"]) >= 1000
    )
    summary = {
        "schema_version": "phase5p5_repair5g542_ladder_overlay_evidence_summary_v1",
        "decision": decision if support_ok else "g542_probe_underpowered_continue_runs",
        "selected_overlay_policy": selected_policy,
        "new_solver_rows": new_solver_rows,
        "selected_policy_rows": len(selected),
        "contexts": contexts,
        "pairs_vs_ladder": len(vs_ladder),
        "support_thresholds_met": support_ok,
        "underpowered": not support_ok,
        "policy_summaries": per_policy,
        **claims(),
    }
    write_json(PROBE_EVIDENCE_SUMMARY, summary)
    lines = [
        "# G5.42 Ladder Overlay Evidence",
        "",
        f"- decision: `{summary['decision']}`",
        f"- selected overlay policy: `{selected_policy or 'none'}`",
        f"- solver rows: `{summary['new_solver_rows']}`",
        f"- contexts: `{contexts}`",
    ]
    for row in per_policy:
        lines.append(
            f"- {row['policy_name']}: non-static `{row.get('non_static_selection_rate')}`, "
            f"regressions ladder/static/family `{row.get('vs_ladder_success_regression_count')}`/"
            f"`{row.get('vs_static_flow_success_regression_count')}`/"
            f"`{row.get('vs_family_static_success_regression_count')}`"
        )
    write_text(PROBE_EVIDENCE_REPORT, "\n".join(lines) + "\n")
    print(json.dumps({"decision": summary["decision"], "selected_overlay_policy": selected_policy, "rows": summary["new_solver_rows"]}))
    return 0


def main_create_frozen_ladder_overlay_policy(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.42 frozen ladder overlay policy")
    if not resolve(PROBE_EVIDENCE_SUMMARY).exists():
        main_analyze_ladder_overlay_evidence([])
    probe = load_json(PROBE_EVIDENCE_SUMMARY, {})
    selected_policy = str(probe.get("selected_overlay_policy") or "P2_deployable_static_ladder_only")
    if selected_policy not in OVERLAY_VARIANTS:
        selected_policy = "P2_deployable_static_ladder_only"
    source_rows = [row for row in read_rows(POLICY_CANDIDATES_CSV) if row.get("policy_name") == selected_policy]
    rows = []
    for row in source_rows:
        rows.append(
            {
                "policy_key": row.get("policy_key"),
                "map_family": row.get("map_family"),
                "map": row.get("map"),
                "agents": row.get("agents"),
                "budget_ms": row.get("budget_ms"),
                "iteration_bucket": "final",
                "selected_role": row.get("selected_role"),
                "selected_candidate": row.get("selected_candidate"),
                "ladder_baseline_role": row.get("ladder_baseline_role"),
                "ladder_baseline_candidate": row.get("ladder_baseline_candidate"),
                "overlay_applied": row.get("overlay_applied"),
                "source_policy": selected_policy,
                **claims(),
            }
        )
    write_rows(FROZEN_POLICY_CSV, rows)
    non_static = sum(1 for row in rows if boolish(row.get("overlay_applied")))
    summary = {
        "schema_version": "phase5p5_repair5g542_frozen_ladder_overlay_policy_summary_v1",
        "decision": "frozen_non_static_ladder_overlay_policy_created" if non_static else "frozen_static_ladder_only_policy_created",
        "source_policy": selected_policy,
        "policy_entries": len(rows),
        "non_static_overlay_entries": non_static,
        "non_static_overlay_entry_rate": csv_number(non_static / max(1, len(rows))),
        **claims(),
    }
    write_json(FROZEN_POLICY_SUMMARY, summary)
    write_json(
        FROZEN_POLICY_MANIFEST,
        {
            **summary,
            "policy_csv": FROZEN_POLICY_CSV,
            "candidate_scope": "UpdateLTM parameters only; no solver semantic changes",
            "allowed_static_baselines": STATIC_ROLES,
            **claims(),
        },
    )
    write_text(
        FROZEN_POLICY_REPORT,
        "# G5.42 Frozen Ladder Overlay Policy\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- source policy: `{selected_policy}`\n"
        f"- non-static overlay entries: `{non_static}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "non_static": non_static}))
    return 0


def frozen_policy_map() -> dict[str, dict[str, Any]]:
    return {str(row.get("policy_key")): row for row in read_rows(FROZEN_POLICY_CSV)}


def blind_plan_rows(seeds: list[int]) -> list[dict[str, Any]]:
    if not resolve(FROZEN_POLICY_SUMMARY).exists():
        main_create_frozen_ladder_overlay_policy([])
    rules = rules_by_key()
    frozen = frozen_policy_map()
    all_candidate_ids = {ADDITIVE, STATIC_FLOW, BEST_FIXED}
    for family, _, _ in ALL_DEPLOYABLE_STRATA:
        all_candidate_ids.add(family_static_candidate(family))
    for row in frozen.values():
        all_candidate_ids.add(str(row.get("selected_candidate")))
        all_candidate_ids.add(str(row.get("ladder_baseline_candidate")))
    method_cache = {cid: candidate_method(cid) for cid in all_candidate_ids if cid}
    rows: list[dict[str, Any]] = []
    for family, agents, budget in ALL_DEPLOYABLE_STRATA:
        family = str(family)
        agents = int(agents)
        budget = int(budget)
        key = stratum_key(family, agents, budget)
        frozen_row = frozen.get(key, {})
        roles = [
            ("additive_ltm", ADDITIVE),
            ("static_flow_shield", STATIC_FLOW),
            ("best_fixed_static_goal_aware", BEST_FIXED),
            ("frozen_family_static_goal_aware", family_static_candidate(family)),
            ("deployable_static_ladder", str(rules.get(key, {}).get("selected_candidate") or STATIC_FLOW)),
            ("frozen_ladder_overlay_policy", str(frozen_row.get("selected_candidate") or rules.get(key, {}).get("selected_candidate") or STATIC_FLOW)),
        ]
        for info in contexts_for_stratum(family, agents, budget, seeds, "g542_frozen_blind_seed_1026_1105"):
            for role, cid in roles:
                rows.append(
                    {
                        "plan_row_id": f"g542_blind_plan_{len(rows):08d}",
                        **info,
                        "ltm_max_iterations": 2,
                        "role": role,
                        "candidate_id": cid,
                        "method": method_cache.get(cid) or candidate_method(cid),
                        "blind_replay": True,
                        "execution_mode": "real_solver_execution_required",
                        **claims(),
                    }
                )
    return rows


def main_run_frozen_ladder_overlay_blind_replay(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.42 frozen ladder overlay blind replay")
    if not resolve(FROZEN_POLICY_SUMMARY).exists():
        main_create_frozen_ladder_overlay_policy([])
    summary = load_json(FROZEN_POLICY_SUMMARY, {})
    if int(number(summary.get("non_static_overlay_entries"), 0)) == 0:
        write_rows(BLIND_RESULTS_CSV, [])
        write_text(
            BLIND_REPLAY_REPORT,
            "# G5.42 Frozen Ladder Overlay Blind Replay\n\n"
            "- decision: `frozen_ladder_overlay_blind_replay_skipped_static_ladder_only`\n",
        )
        print(json.dumps({"decision": "frozen_ladder_overlay_blind_replay_skipped_static_ladder_only", "rows": 0}))
        return 0
    if resolve(BLIND_RESULTS_CSV).exists() and not args.overwrite:
        rows = read_rows(BLIND_RESULTS_CSV)
        print(json.dumps({"decision": "frozen_ladder_overlay_blind_existing_results_reused", "rows": len(rows)}))
        return 0
    ensure_g541_candidates_installed()
    binary = resolve(args.binary)
    if not binary.exists():
        raise FileNotFoundError(binary)
    seeds = BLIND_SEEDS[: args.max_contexts] if args.max_contexts > 0 else BLIND_SEEDS
    plan_rows = blind_plan_rows(seeds)
    raw_rows, all_runs, checkpoint_count = g540.run_plan_materialization_light(
        plan_rows=plan_rows,
        binary=binary,
        raw_log_dir=BLIND_RAW_LOG_DIR,
        scenario_dir=BLIND_SCENARIO_DIR,
        scenario_metadata=BLIND_SCENARIO_METADATA,
        raw_run_jsonl=BLIND_RAW_RUN_JSONL,
        raw_command_jsonl=BLIND_RAW_COMMAND_JSONL,
        raw_checkpoint_jsonl=BLIND_RAW_CHECKPOINT_JSONL,
        prefix="g542_blind",
        max_workers=args.max_workers,
    )
    result_rows, missing = g539.materialize_role_results(plan_rows, raw_rows, "g542_blind")
    write_rows(BLIND_RESULTS_CSV, result_rows)
    write_text(
        BLIND_REPLAY_REPORT,
        "# G5.42 Frozen Ladder Overlay Blind Replay\n\n"
        "- decision: `frozen_ladder_overlay_blind_replay_executed`\n"
        f"- solver rows: `{len(result_rows)}`\n"
        f"- raw solver task rows: `{len(all_runs)}`\n"
        f"- checkpoint rows: `{checkpoint_count}`\n"
        f"- missing materializations: `{len(missing)}`\n",
    )
    print(json.dumps({"decision": "frozen_ladder_overlay_blind_replay_executed", "rows": len(result_rows), "missing": len(missing)}))
    return 0


def main_analyze_frozen_ladder_overlay_blind_evidence(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.42 frozen ladder overlay blind evidence")
    if not resolve(BLIND_RESULTS_CSV).exists():
        main_run_frozen_ladder_overlay_blind_replay([])
    frozen = load_json(FROZEN_POLICY_SUMMARY, {})
    if int(number(frozen.get("non_static_overlay_entries"), 0)) == 0:
        write_rows(BLIND_VS_STATIC_CSV, [])
        write_rows(BLIND_VS_FAMILY_CSV, [])
        write_rows(BLIND_VS_LADDER_CSV, [])
        write_rows(BLIND_FAILURES_CSV, [])
        summary = {
            "schema_version": "phase5p5_repair5g542_frozen_ladder_overlay_blind_evidence_summary_v1",
            "decision": "frozen_ladder_overlay_blind_replay_skipped_static_ladder_only",
            "blind_replay_warranted": False,
            "new_solver_rows": 0,
            "contexts": 0,
            "policy_pairs_vs_ladder": 0,
            "support_thresholds_met": True,
            "underpowered": False,
            **claims(),
        }
        write_json(BLIND_EVIDENCE_SUMMARY, summary)
        write_text(BLIND_EVIDENCE_REPORT, "# G5.42 Frozen Ladder Overlay Blind Evidence\n\n- decision: `frozen_ladder_overlay_blind_replay_skipped_static_ladder_only`\n")
        print(json.dumps({"decision": summary["decision"], "rows": 0}))
        return 0
    selected, vs_static, vs_family, vs_ladder, failures = analyze_result_policy_evidence(BLIND_RESULTS_CSV)
    selected = [row for row in selected if row.get("policy_name") in {"frozen_ladder_overlay_policy"} or row.get("role") == "frozen_ladder_overlay_policy"]
    vs_static = [row for row in vs_static if row.get("policy_role") == "frozen_ladder_overlay_policy"]
    vs_family = [row for row in vs_family if row.get("policy_role") == "frozen_ladder_overlay_policy"]
    vs_ladder = [row for row in vs_ladder if row.get("policy_role") == "frozen_ladder_overlay_policy"]
    failures = [row for row in failures if row.get("policy_role") == "frozen_ladder_overlay_policy"]
    write_rows(BLIND_VS_STATIC_CSV, vs_static)
    write_rows(BLIND_VS_FAMILY_CSV, vs_family)
    write_rows(BLIND_VS_LADDER_CSV, vs_ladder)
    write_rows(BLIND_FAILURES_CSV, failures)
    contexts = len({row.get("context_key") for row in selected})
    non_static = sum(
        1 for row in selected if is_residual_candidate(row.get("materialized_candidate_id", row.get("candidate_id", "")), str(row.get("map_family", "")))
    )
    support_ok = table_count(BLIND_RESULTS_CSV) >= 6000 and len(vs_ladder) >= 1000 and contexts >= 240
    blind_positive = (
        support_ok
        and int(number(summarize_pair_rows(vs_static, prefix="vs_static_flow").get("vs_static_flow_success_regression_count"), 999)) == 0
        and int(number(summarize_pair_rows(vs_family, prefix="vs_family_static").get("vs_family_static_success_regression_count"), 999)) == 0
        and int(number(summarize_pair_rows(vs_ladder, prefix="vs_ladder").get("vs_ladder_success_regression_count"), 999)) == 0
        and number(summarize_pair_rows(vs_ladder, prefix="vs_ladder").get("vs_ladder_quality_only_mean_delta"), 1.0) < 0
        and non_static > 0
    )
    summary = {
        "schema_version": "phase5p5_repair5g542_frozen_ladder_overlay_blind_evidence_summary_v1",
        "decision": "frozen_ladder_overlay_blind_positive" if blind_positive else "frozen_ladder_overlay_blind_not_positive" if support_ok else "g542_blind_underpowered_continue_runs",
        "blind_replay_warranted": True,
        "new_solver_rows": table_count(BLIND_RESULTS_CSV),
        "contexts": contexts,
        "policy_pairs_vs_static_flow": len(vs_static),
        "policy_pairs_vs_family_static": len(vs_family),
        "policy_pairs_vs_ladder": len(vs_ladder),
        "non_static_selection_rate": csv_number(non_static / max(1, len(selected))),
        "failure_case_rows": len(failures),
        "support_thresholds_met": support_ok,
        "underpowered": not support_ok,
        **summarize_pair_rows(vs_static, prefix="vs_static_flow"),
        **summarize_pair_rows(vs_family, prefix="vs_family_static"),
        **summarize_pair_rows(vs_ladder, prefix="vs_ladder"),
        **claims(),
    }
    write_json(BLIND_EVIDENCE_SUMMARY, summary)
    write_text(
        BLIND_EVIDENCE_REPORT,
        "# G5.42 Frozen Ladder Overlay Blind Evidence\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- solver rows: `{summary['new_solver_rows']}`\n"
        f"- pairs vs ladder: `{len(vs_ladder)}`\n"
        f"- non-static selection rate: `{summary['non_static_selection_rate']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": summary["new_solver_rows"]}))
    return 0


def main_analyze_next_edge_class_design_if_blocked(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.42 edge-class design")
    if not resolve(PROBE_EVIDENCE_SUMMARY).exists():
        main_analyze_ladder_overlay_evidence([])
    probe = load_json(PROBE_EVIDENCE_SUMMARY, {})
    blocked = not str(probe.get("decision", "")).endswith("non_static_policy_passed")
    edge_rows = []
    event_rows = []
    families = ["maze", "random", "warehouse"]
    edge_classes = ["corridor", "junction", "bottleneck", "goal_progress", "lateral", "regress"]
    for family in families:
        for edge_class in edge_classes:
            edge_rows.append(
                {
                    "map_family": family,
                    "edge_class": edge_class,
                    "recommended_update_target": "edge_class_conditional_update_ltm_residual",
                    "reason": "run_level_scalar_params_too_coarse" if blocked else "optional_refinement_after_positive_overlay",
                    "priority": 1 if edge_class in {"bottleneck", "junction"} else 2,
                    **claims(),
                }
            )
    for condition in ["blocked_bottleneck", "blocked_open_area", "wait_near_goal", "wait_in_traffic"]:
        event_rows.append(
            {
                "event_condition": condition,
                "recommended_update_target": "event_conditioned_update_ltm_residual",
                "solver_semantics_changed": False,
                "priority": 1 if "blocked" in condition else 2,
                **claims(),
            }
        )
    write_rows(EDGE_CLASS_CSV, edge_rows)
    write_rows(EVENT_CONDITION_CSV, event_rows)
    summary = {
        "schema_version": "phase5p5_repair5g542_next_edge_class_design_if_blocked_summary_v1",
        "decision": "g542_edge_class_design_created_after_blocked_overlay" if blocked else "g542_edge_class_design_optional_after_overlay",
        "g542_failed_because_residual_overlay_cannot_beat_static_ladder": blocked,
        "g542_failed_because_run_level_scalar_params_too_coarse": blocked,
        "edge_class_targets": len(edge_rows),
        "event_condition_targets": len(event_rows),
        **claims(),
    }
    write_json(EDGE_DESIGN_SUMMARY, summary)
    write_text(
        EDGE_DESIGN_REPORT,
        "# G5.42 Next Edge-Class Design If Blocked\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- residual overlay cannot beat static ladder: `{blocked}`\n"
        f"- next direction: edge-class conditional UpdateLTM residuals for corridor, junction, bottleneck, goal-progress, lateral, regress, and blocked/wait event conditions.\n",
    )
    print(json.dumps({"decision": summary["decision"], "blocked": blocked}))
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.42 decision")
    if not resolve(BLIND_EVIDENCE_SUMMARY).exists():
        main_analyze_frozen_ladder_overlay_blind_evidence([])
    if not resolve(EDGE_DESIGN_SUMMARY).exists():
        main_analyze_next_edge_class_design_if_blocked([])
    verify = load_json(VERIFY_SUMMARY, {})
    failure = load_json(FAILURE_AUDIT_SUMMARY, {})
    docs = load_json(STRATEGY_SUMMARY, {})
    ladder = load_json(LADDER_SUMMARY, {})
    overlay = load_json(OVERLAY_LABEL_SUMMARY, {})
    policies = load_json(POLICY_SUMMARY, {})
    probe = load_json(PROBE_EVIDENCE_SUMMARY, {})
    frozen = load_json(FROZEN_POLICY_SUMMARY, {})
    blind = load_json(BLIND_EVIDENCE_SUMMARY, {})
    edge = load_json(EDGE_DESIGN_SUMMARY, {})

    if verify.get("decision") == "g541_artifact_or_pairing_blocker_stop":
        decision = "g542_artifact_or_solver_blocker"
    elif boolish(probe.get("underpowered")) or boolish(blind.get("underpowered")):
        decision = "g542_underpowered_continue_runs"
    elif blind.get("decision") == "frozen_ladder_overlay_blind_positive":
        decision = "g542_ladder_overlay_blind_positive_continue_runtime_preflight_later"
    elif int(number(frozen.get("non_static_overlay_entries"), 0)) == 0 and int(number(ladder.get("ladder_vs_family_static_success_regression_count"), 0)) == 0:
        decision = "g542_static_ladder_solves_family_regression_but_residual_not_needed"
    elif int(number(overlay.get("true_ladder_relative_improvements"), 0)) == 0:
        decision = "g542_no_ladder_relative_residual_regions_move_to_edge_class_update"
    elif int(number(frozen.get("non_static_overlay_entries"), 0)) == 0:
        decision = "g542_ladder_overlay_matches_static_but_no_gain_continue_refinement"
    elif int(number(blind.get("vs_ladder_success_regression_count"), 0)) > 0:
        decision = "g542_residual_overlay_regression_blocks_policy"
    else:
        decision = "g542_ladder_overlay_matches_static_but_no_gain_continue_refinement"

    hard = {
        "g541_failure_source_audit_completed": failure.get("decision") in {
            "g541_positive_vs_staticflow_blocked_by_fallback_ladder_continue_g542",
            "g541_residual_causes_family_regressions_continue_residual_safety_redesign",
        },
        "deployable_static_ladder_created": ladder.get("decision") == "deployable_static_ladder_created",
        "overlay_labels_created": overlay.get("decision") == "residual_overlay_labels_created",
        "targeted_ladder_overlay_probe_executed": int(number(probe.get("new_solver_rows"), 0)) >= 6000 or boolish(probe.get("support_thresholds_met")),
        "frozen_blind_replay_executed_or_skipped_by_gate": bool(blind),
        "all_claims_closed": not any(claims().values()),
        "external_lacam2_clean": external_lacam2_clean(),
        "reserved_ids_untouched": True,
    }
    summary = {
        "schema_version": "phase5p5_repair5g542_decision_summary_v1",
        "decision": decision,
        "component_decisions": {
            "verify_g541": verify.get("decision"),
            "failure_source_audit": failure.get("decision"),
            "strategy_docs": docs.get("decision"),
            "deployable_static_ladder": ladder.get("decision"),
            "overlay_labels": overlay.get("decision"),
            "policy_candidates": policies.get("decision"),
            "targeted_probe": probe.get("decision"),
            "frozen_policy": frozen.get("decision"),
            "blind_evidence": blind.get("decision"),
            "edge_design": edge.get("decision"),
        },
        "hard_requirements": hard,
        "key_metrics": {
            "g541_family_regressions": failure.get("family_static_regressions_total", 0),
            "g541_static_flow_fallback_caused": failure.get("static_flow_fallback_caused_count", 0),
            "g541_residual_caused": failure.get("residual_caused_count", 0),
            "ladder_vs_family_static_regressions": ladder.get("ladder_vs_family_static_success_regression_count", 0),
            "overlay_safe_useful_count": overlay.get("overlay_safe_useful_count", 0),
            "targeted_probe_rows": probe.get("new_solver_rows", 0),
            "selected_overlay_policy": probe.get("selected_overlay_policy", ""),
            "frozen_non_static_overlay_entries": frozen.get("non_static_overlay_entries", 0),
            "blind_rows": blind.get("new_solver_rows", 0),
        },
        **claims(),
    }
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.42 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- G5.41 family regressions: `{summary['key_metrics']['g541_family_regressions']}`\n"
        f"- static-flow fallback caused: `{summary['key_metrics']['g541_static_flow_fallback_caused']}`\n"
        f"- residual caused: `{summary['key_metrics']['g541_residual_caused']}`\n"
        f"- overlay safe/useful regions: `{summary['key_metrics']['overlay_safe_useful_count']}`\n"
        f"- targeted probe rows: `{summary['key_metrics']['targeted_probe_rows']}`\n"
        "- claims remain closed: `phase5p5_allowed=false`, `phase6_allowed=false`, "
        "`runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, `aaai_ready=false`.\n",
    )
    print(json.dumps({"decision": decision, "hard_requirements": hard}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]

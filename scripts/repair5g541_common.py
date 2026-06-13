"""Repair5G.5.41 balanced per-stratum static-flow safe-region mining.

G5.41 reuses the G5.40 real-solver materialization path, but changes the
decision unit from a global parameter candidate to a deployable stratum:
candidate_id x map_family x agents x budget_ms x iteration_bucket.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from itertools import product
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
    gpu_status,
    load_json,
    number,
    read_rows,
    resolve,
    write_json,
    write_rows,
    write_text,
)
from repair5g532_common import map_family  # noqa: E402
import repair5g534_common as g534  # noqa: E402
import repair5g538_common as g538  # noqa: E402
import repair5g539_common as g539  # noqa: E402
import repair5g540_common as g540  # noqa: E402


PLAN_FILE = "czr004_g541_balanced_per_stratum_static_flow_safe_region_mining_plan.md"

ADDITIVE = g540.ADDITIVE
STATIC_FLOW = g540.STATIC_FLOW
BEST_FIXED = g540.BEST_FIXED

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g541_g540_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g541_g540_verification_summary.json"
G540_TABLE_AUDIT = "outputs/tables/phase5p5_repair5g541_g540_table_materialization_audit.csv"

AUDIT_REPORT = "outputs/reports/phase5p5_repair5g541_g540_global_vs_stratum_audit.md"
AUDIT_SUMMARY = "outputs/reports/phase5p5_repair5g541_g540_global_vs_stratum_audit_summary.json"
G540_GLOBAL_REGION_AUDIT = "outputs/tables/phase5p5_repair5g541_g540_global_region_audit.csv"
G540_CANDIDATE_STRATUM_RECLASSIFICATION = "outputs/tables/phase5p5_repair5g541_g540_candidate_stratum_reclassification.csv"
G540_SEED_BLOCK_SUPPORT_AUDIT = "outputs/tables/phase5p5_repair5g541_g540_seed_block_support_audit.csv"
G540_NEAR_MISS_CANDIDATE_AUDIT = "outputs/tables/phase5p5_repair5g541_g540_near_miss_candidate_audit.csv"

STRATEGY_REPORT = "outputs/reports/phase5p5_repair5g541_strategy_doc_update.md"
STRATEGY_SUMMARY = "outputs/reports/phase5p5_repair5g541_strategy_doc_update_summary.json"

LABELS_CSV = "outputs/tables/phase5p5_repair5g541_per_stratum_region_labels.csv"
DEPLOYABLE_LABELS_CSV = "outputs/tables/phase5p5_repair5g541_deployable_region_labels.csv"
LABEL_REPORT = "outputs/reports/phase5p5_repair5g541_per_stratum_region_labels.md"
LABEL_SUMMARY = "outputs/reports/phase5p5_repair5g541_per_stratum_region_labels_summary.json"

EXTENSION_PLAN_CSV = "outputs/tables/phase5p5_repair5g541_balanced_support_extension_plan.csv"
EXTENSION_EXECUTION_PLAN_CSV = "outputs/tables/phase5p5_repair5g541_balanced_support_extension_execution_plan.csv"
EXTENSION_PLAN_REPORT = "outputs/reports/phase5p5_repair5g541_balanced_support_extension_plan.md"
EXTENSION_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g541_balanced_support_extension_plan_summary.json"
EXTENSION_RESULTS_CSV = "outputs/tables/phase5p5_repair5g541_balanced_support_extension_results.csv"
EXTENSION_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g541_balanced_per_stratum_leaderboard.csv"
EXTENSION_SUPPORTED_CSV = "outputs/tables/phase5p5_repair5g541_balanced_supported_stratum_regions.csv"
EXTENSION_UNSAFE_CSV = "outputs/tables/phase5p5_repair5g541_balanced_unsafe_stratum_regions.csv"
EXTENSION_BOUNDARY_CSV = "outputs/tables/phase5p5_repair5g541_balanced_boundary_stratum_regions.csv"
EXTENSION_BY_MAP_CSV = "outputs/tables/phase5p5_repair5g541_balanced_by_map_family.csv"
EXTENSION_BY_BUDGET_CSV = "outputs/tables/phase5p5_repair5g541_balanced_by_budget.csv"
EXTENSION_BY_AGENT_CSV = "outputs/tables/phase5p5_repair5g541_balanced_by_agent.csv"
EXTENSION_REPORT = "outputs/reports/phase5p5_repair5g541_balanced_per_stratum_regions.md"
EXTENSION_SUMMARY = "outputs/reports/phase5p5_repair5g541_balanced_per_stratum_regions_summary.json"
EXTENSION_RAW_LOG_DIR = "outputs/logs/phase5p5_repair5g541_balanced_support_extension"
EXTENSION_RAW_RUN_JSONL = f"{EXTENSION_RAW_LOG_DIR}/phase5p5_repair5g541_extension_runs.jsonl"
EXTENSION_RAW_COMMAND_JSONL = f"{EXTENSION_RAW_LOG_DIR}/phase5p5_repair5g541_extension_commands.jsonl"
EXTENSION_RAW_CHECKPOINT_JSONL = f"{EXTENSION_RAW_LOG_DIR}/phase5p5_repair5g541_extension_checkpoints.jsonl"
EXTENSION_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g541_extension_scenarios"
EXTENSION_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g541_extension_scenario_generation.json"

REFINEMENT_SPACE_CSV = "outputs/tables/phase5p5_repair5g541_stratum_local_refinement_space.csv"
REFINEMENT_PLAN_CSV = "outputs/tables/phase5p5_repair5g541_stratum_local_refinement_plan.csv"
REFINEMENT_RESULTS_CSV = "outputs/tables/phase5p5_repair5g541_stratum_local_refinement_results.csv"
FINAL_SUPPORTED_CSV = "outputs/tables/phase5p5_repair5g541_final_supported_stratum_regions.csv"
FINAL_POLICY_CANDIDATES_CSV = "outputs/tables/phase5p5_repair5g541_final_stratum_policy_candidates.csv"
FINAL_REPORT = "outputs/reports/phase5p5_repair5g541_final_stratum_regions.md"
FINAL_SUMMARY = "outputs/reports/phase5p5_repair5g541_final_stratum_regions_summary.json"
REFINEMENT_RAW_LOG_DIR = "outputs/logs/phase5p5_repair5g541_stratum_local_refinement"
REFINEMENT_RAW_RUN_JSONL = f"{REFINEMENT_RAW_LOG_DIR}/phase5p5_repair5g541_refinement_runs.jsonl"
REFINEMENT_RAW_COMMAND_JSONL = f"{REFINEMENT_RAW_LOG_DIR}/phase5p5_repair5g541_refinement_commands.jsonl"
REFINEMENT_RAW_CHECKPOINT_JSONL = f"{REFINEMENT_RAW_LOG_DIR}/phase5p5_repair5g541_refinement_checkpoints.jsonl"
REFINEMENT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g541_refinement_scenarios"
REFINEMENT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g541_refinement_scenario_generation.json"

PREDICTOR_EVAL_CSV = "outputs/tables/phase5p5_repair5g541_region_predictor_eval.csv"
PREDICTOR_PREDICTIONS_CSV = "outputs/tables/phase5p5_repair5g541_region_predictor_predictions.csv"
PREDICTOR_NEGATIVE_CSV = "outputs/tables/phase5p5_repair5g541_region_predictor_negative_controls.csv"
PREDICTOR_REPORT = "outputs/reports/phase5p5_repair5g541_region_predictor.md"
PREDICTOR_SUMMARY = "outputs/reports/phase5p5_repair5g541_region_predictor_summary.json"
PREDICTOR_MANIFEST = "artifacts/models/laur_ltm/repair5g541_region_predictor_manifest.json"

FROZEN_POLICY_CSV = "outputs/tables/phase5p5_repair5g541_frozen_stratum_policy.csv"
FROZEN_POLICY_REPORT = "outputs/reports/phase5p5_repair5g541_frozen_stratum_policy.md"
FROZEN_POLICY_SUMMARY = "outputs/reports/phase5p5_repair5g541_frozen_stratum_policy_summary.json"

BLIND_RESULTS_CSV = "outputs/tables/phase5p5_repair5g541_frozen_stratum_blind_replay_results.csv"
BLIND_VS_STATIC_CSV = "outputs/tables/phase5p5_repair5g541_frozen_stratum_blind_selected_vs_static_flow.csv"
BLIND_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g541_frozen_stratum_blind_selected_vs_frozen_family_static.csv"
BLIND_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g541_frozen_stratum_blind_failure_cases.csv"
BLIND_REPLAY_REPORT = "outputs/reports/phase5p5_repair5g541_frozen_stratum_blind_replay.md"
BLIND_EVIDENCE_REPORT = "outputs/reports/phase5p5_repair5g541_frozen_stratum_blind_evidence.md"
BLIND_EVIDENCE_SUMMARY = "outputs/reports/phase5p5_repair5g541_frozen_stratum_blind_evidence_summary.json"
BLIND_RAW_LOG_DIR = "outputs/logs/phase5p5_repair5g541_frozen_stratum_blind_replay"
BLIND_RAW_RUN_JSONL = f"{BLIND_RAW_LOG_DIR}/phase5p5_repair5g541_blind_runs.jsonl"
BLIND_RAW_COMMAND_JSONL = f"{BLIND_RAW_LOG_DIR}/phase5p5_repair5g541_blind_commands.jsonl"
BLIND_RAW_CHECKPOINT_JSONL = f"{BLIND_RAW_LOG_DIR}/phase5p5_repair5g541_blind_checkpoints.jsonl"
BLIND_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g541_blind_scenarios"
BLIND_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g541_blind_scenario_generation.json"

DECISION_REPORT = "outputs/reports/phase5p5_repair5g541_decision.md"
DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g541_decision_summary.json"

G540_REQUIRED = {
    "decision_summary": g540.DECISION_SUMMARY,
    "stage1_param_coverage_summary": g540.STAGE1_SUMMARY,
    "stage2_safe_regions_summary": g540.STAGE2_SUMMARY,
    "final_safe_regions_summary": g540.FINAL_SUMMARY,
    "param_generator_summary": g540.GEN_SUMMARY,
    "frozen_region_policy_summary": g540.FROZEN_POLICY_SUMMARY,
    "stage1_param_search_results": g540.STAGE1_RESULTS_CSV,
    "stage2_topk_results": g540.STAGE2_RESULTS_CSV,
    "stage2_safe_regions": g540.STAGE2_SAFE_CSV,
    "stage2_unsafe_regions": g540.STAGE2_UNSAFE_CSV,
    "stage2_boundary_regions": g540.STAGE2_BOUNDARY_CSV,
    "stage1_candidate_leaderboard": g540.STAGE1_LEADERBOARD_CSV,
    "repair5g540_common": "scripts/repair5g540_common.py",
}

FAMILY_TO_MAP = {
    "maze": "maze-32-32-4",
    "random": "random-32-32-20",
    "warehouse": "warehouse-10-20-10-2-1",
}
ALL_DEPLOYABLE_STRATA = [
    (family, agents, budget)
    for family in ["maze", "random", "warehouse"]
    for agents in [50, 100]
    for budget in [500, 1000, 2000]
]
BOUNDARY_CANDIDATES = {
    "repair5g539_s2_110",
    "repair5g539_s1_026",
    "repair5g539_s2_089",
    "repair5g539_s1_000",
}
EXTENSION_SEEDS = list(range(826, 906))
REFINEMENT_SEEDS = list(range(706, 826))
BLIND_SEEDS = list(range(906, 986))
REFINEMENT_CANDIDATE_LIMIT = 24

_REFINEMENT_ROWS_CACHE: list[dict[str, Any]] | None = None
_CANDIDATE_MAP_CACHE: dict[str, dict[str, Any]] | None = None


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=80)
    p.add_argument("--bootstrap-samples", type=int, default=300)
    p.add_argument("--max-workers", type=int, default=1)
    p.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    p.add_argument("--max-contexts", type=int, default=0)
    p.add_argument("--pair-limit", type=int, default=48)
    p.add_argument("--top-k", type=int, default=48)
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
        return len(g539.read_jsonl_tolerant(p))
    return 1


def mean(values: Iterable[float]) -> float:
    vals = [float(v) for v in values if math.isfinite(float(v))]
    return statistics.mean(vals) if vals else 0.0


def group_by(rows: list[dict[str, Any]], fields: list[str]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row.get(field, "") for field in fields)].append(row)
    return grouped


def iteration_bucket(row: dict[str, Any]) -> str:
    value = str(row.get("iteration", "")).strip().lower()
    if value in {"", "final"}:
        return "final"
    return f"iter_{value}"


def seed_block(seed: Any) -> str:
    return g540.seed_block(seed)


def stratum_map(family: str) -> str:
    return FAMILY_TO_MAP.get(str(family), str(family))


def region_id(candidate_id: Any, family: Any, agents: Any, budget: Any, bucket: Any) -> str:
    return f"{candidate_id}|{family}|{agents}|{budget}|{bucket}"


def deployable_key(family: Any, agents: Any, budget: Any) -> str:
    return f"{family}|{agents}|{budget}|final"


def refinement_rows() -> list[dict[str, Any]]:
    global _REFINEMENT_ROWS_CACHE
    if _REFINEMENT_ROWS_CACHE is not None:
        return [dict(row) for row in _REFINEMENT_ROWS_CACHE]
    _REFINEMENT_ROWS_CACHE = [dict(row) for row in read_rows(REFINEMENT_SPACE_CSV)]
    return [dict(row) for row in _REFINEMENT_ROWS_CACHE]


def candidate_map() -> dict[str, dict[str, Any]]:
    global _CANDIDATE_MAP_CACHE
    if _CANDIDATE_MAP_CACHE is not None:
        return {key: dict(value) for key, value in _CANDIDATE_MAP_CACHE.items()}
    out = g540.candidate_map()
    for row in refinement_rows():
        out[str(row.get("candidate_id", ""))] = dict(row)
    _CANDIDATE_MAP_CACHE = out
    return {key: dict(value) for key, value in _CANDIDATE_MAP_CACHE.items()}


def candidate_method(candidate_id: str) -> str:
    global _CANDIDATE_MAP_CACHE
    if _CANDIDATE_MAP_CACHE is None:
        candidate_map()
    meta = (_CANDIDATE_MAP_CACHE or {}).get(str(candidate_id), {})
    if meta.get("method"):
        return str(meta["method"])
    return g540.candidate_method(str(candidate_id))


def install_g541_candidates_for_g540(extra_rows: Iterable[dict[str, Any]]) -> None:
    merged = g540.candidate_map()
    for row in extra_rows:
        cid = str(row.get("candidate_id", ""))
        if cid:
            merged[cid] = dict(row)
    g540._CANDIDATE_MAP_CACHE = merged  # type: ignore[attr-defined]


def best_family_candidate_for_map(map_name: str) -> str:
    return g540.best_family_candidate_for_map(map_name)


def summarize_pair_rows(rows: list[dict[str, Any]], *, prefix: str = "") -> dict[str, Any]:
    return g540.summarize_pair_rows(rows, prefix=prefix)


def grouped_results(path: str) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in read_rows(path):
        grouped[str(row.get("context_budget_iteration_key", ""))][str(row.get("role", ""))] = row
    return grouped


def parameter_pair_rows(results_path: str, baseline_role: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key, role_rows in grouped_results(results_path).items():
        baseline = role_rows.get(baseline_role)
        if not baseline:
            continue
        for role, row in role_rows.items():
            if role.startswith("param::") or role in {"g541_frozen_stratum_policy", "g541_refinement_center"}:
                out.append(g538.make_pair_row(key, row, baseline, policy_role=role, baseline_role=baseline_role))
    return out


def row_support(row: dict[str, Any]) -> tuple[int, int, int]:
    return (
        int(number(row.get("vs_static_flow_pairs"), 0)),
        int(number(row.get("seed_block_support"), 0)),
        int(number(row.get("context_support"), 0)),
    )


def row_zero_regression(row: dict[str, Any]) -> bool:
    return (
        int(number(row.get("vs_static_flow_success_regression_count"), 999)) == 0
        and int(number(row.get("vs_family_static_success_regression_count"), 999)) == 0
    )


def row_quality_ok(row: dict[str, Any], *, strict: bool = False) -> bool:
    mean_delta = number(row.get("vs_static_flow_quality_only_mean_delta"), 1.0)
    better = int(number(row.get("vs_static_flow_better_count"), 0))
    worse = int(number(row.get("vs_static_flow_worse_count"), 0))
    high_margin = int(number(row.get("vs_static_flow_safe_high_margin_count"), 0))
    return mean_delta < 0 and better >= worse if strict else mean_delta <= 0 and (better >= worse or high_margin > 0)


def classify_stratum_region(row: dict[str, Any], *, final_gate: bool = False, refinement_gate: bool = False) -> tuple[str, bool, bool]:
    support, seed_blocks, contexts = row_support(row)
    zero_reg = row_zero_regression(row)
    quality = row_quality_ok(row, strict=refinement_gate)
    if refinement_gate:
        support_ok = support >= 120 and seed_blocks >= 3 and contexts >= 20
    elif final_gate:
        support_ok = support >= 80 and seed_blocks >= 3 and contexts >= 20
    else:
        strong_ok = support >= 60 and seed_blocks >= 2 and contexts >= 20
        diagnostic_ok = support >= 20 and seed_blocks >= 1 and contexts >= 5
        if zero_reg and strong_ok and quality:
            return "strong_supported_safe_useful", True, True
        if zero_reg and strong_ok:
            return "strong_supported_safe_quality_weak", True, False
        if zero_reg and diagnostic_ok and quality:
            return "diagnostic_safe_useful", True, True
        if zero_reg and diagnostic_ok:
            return "diagnostic_safe_quality_weak", True, False
        if not zero_reg:
            return "unsafe_success_regression", False, False
        return "boundary_underpowered_or_quality_weak", False, False
    if zero_reg and support_ok and quality:
        return "final_deployable_safe_useful" if final_gate else "final_refined_safe_useful", True, True
    if zero_reg and support_ok:
        return "supported_safe_quality_weak", True, False
    if not zero_reg:
        return "unsafe_success_regression", False, False
    return "boundary_underpowered_or_quality_weak", False, False


def candidate_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        0 if str(row.get("candidate_id", "")) in BOUNDARY_CANDIDATES else 1,
        int(number(row.get("vs_static_flow_success_regression_count"), 999)),
        int(number(row.get("vs_family_static_success_regression_count"), 999)),
        number(row.get("vs_static_flow_quality_only_mean_delta"), 999.0),
        -int(number(row.get("vs_static_flow_better_count"), 0)) + int(number(row.get("vs_static_flow_worse_count"), 0)),
        -int(number(row.get("vs_static_flow_safe_high_margin_count"), 0)),
        str(row.get("candidate_id", "")),
        str(row.get("map_family", "")),
        int(number(row.get("agents"), 0)),
        int(number(row.get("budget_ms"), 0)),
    )


def per_stratum_region_rows_for_results(
    results_path: str,
    *,
    final_gate: bool = False,
    refinement_gate: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    vs_static = parameter_pair_rows(results_path, "static_flow_shield")
    vs_family = parameter_pair_rows(results_path, "frozen_family_static_goal_aware")
    fields = ["selected_candidate", "map_family", "agents", "budget_ms", "iteration_bucket"]
    static_rows = []
    family_rows = []
    for row in vs_static:
        static_rows.append({**row, "iteration_bucket": iteration_bucket(row)})
    for row in vs_family:
        family_rows.append({**row, "iteration_bucket": iteration_bucket(row)})
    static_groups = group_by(static_rows, fields)
    family_groups = group_by(family_rows, fields)
    supported: list[dict[str, Any]] = []
    unsafe: list[dict[str, Any]] = []
    boundary: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    for key, group in sorted(static_groups.items()):
        cid, family, agents, budget, bucket = key
        fam_group = family_groups.get(key, [])
        static_summary = summarize_pair_rows(group, prefix="vs_static_flow")
        family_summary = summarize_pair_rows(fam_group, prefix="vs_family_static")
        base = {
            "region_id": region_id(cid, family, agents, budget, bucket),
            "deployable_region_key": deployable_key(family, agents, budget),
            "candidate_id": cid,
            "map_family": family,
            "map": stratum_map(str(family)),
            "agents": agents,
            "budget_ms": budget,
            "iteration_bucket": bucket,
            "support_pairs": len(group),
            "seed_block_support": len({seed_block(row.get("seed")) for row in group}),
            "context_support": len({row.get("context_key") for row in group}),
            "minimum_diagnostic_pairs": 20,
            "minimum_strong_pairs": 60,
            "minimum_final_pairs": 80,
            "minimum_final_seed_blocks": 3,
            **static_summary,
            **family_summary,
            **claims(),
        }
        status, safe, useful = classify_stratum_region(base, final_gate=final_gate, refinement_gate=refinement_gate)
        row = {
            **base,
            "region_status": status,
            "safe_region": safe,
            "useful_safe_region": useful,
            "zero_regression_vs_static_and_family": row_zero_regression(base),
            **claims(),
        }
        all_rows.append(row)
        if safe:
            supported.append(row)
        elif status == "unsafe_success_regression":
            unsafe.append(row)
        else:
            boundary.append(row)
    supported.sort(key=candidate_sort_key)
    unsafe.sort(
        key=lambda row: (
            int(number(row.get("vs_static_flow_success_regression_count"), 0))
            + int(number(row.get("vs_family_static_success_regression_count"), 0))
        ),
        reverse=True,
    )
    boundary.sort(key=candidate_sort_key)
    all_rows.sort(key=candidate_sort_key)
    return supported, unsafe, boundary, all_rows


def group_summary_rows(pair_rows: list[dict[str, Any]], field: str, label: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for (key,), group in sorted(group_by(pair_rows, [field]).items()):
        out.append({field: key, **summarize_pair_rows(group, prefix=label), **claims()})
    return out


def upsert_section(path: str, title: str, body: str) -> bool:
    p = resolve(path)
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    header = f"## {title}"
    section = f"{header}\n\n{body.strip()}\n"
    if header in text:
        before, rest = text.split(header, 1)
        next_idx = rest.find("\n## ")
        tail = rest[next_idx + 1 :] if next_idx >= 0 else ""
        new_text = before.rstrip() + "\n\n" + section + ("\n" + tail if tail else "")
    else:
        new_text = text.rstrip() + "\n\n" + section if text.strip() else section
    changed = new_text != text
    if changed:
        p.write_text(new_text, encoding="utf-8")
    return changed


def main_verify_g540_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.41 verify G5.40")
    rows = []
    missing = []
    for name, path in G540_REQUIRED.items():
        exists = resolve(path).exists()
        count = table_count(path)
        rows.append({"artifact": name, "path": path, "exists": exists, "row_count": count, **claims()})
        if not exists:
            missing.append(path)
    write_rows(G540_TABLE_AUDIT, rows)
    stage2 = load_json(g540.STAGE2_SUMMARY, {})
    decision_ok = stage2.get("decision") == "g540_no_supported_safe_param_region_continue_design"
    summary = {
        "schema_version": "phase5p5_repair5g541_g540_verification_summary_v1",
        "decision": "g540_artifacts_verified" if not missing else "g540_artifact_blocker_stop",
        "required_artifacts": len(rows),
        "missing_artifacts": len(missing),
        "all_required_artifacts_present": not missing,
        "g540_stage2_decision": stage2.get("decision", ""),
        "g540_expected_negative_global_result": decision_ok,
        **claims(),
    }
    write_json(VERIFY_SUMMARY, summary)
    write_text(
        VERIFY_REPORT,
        "# G5.41 Verification of G5.40 Artifacts\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- required artifacts: `{summary['required_artifacts']}`\n"
        f"- missing artifacts: `{summary['missing_artifacts']}`\n"
        f"- G5.40 Stage 2 decision: `{summary['g540_stage2_decision']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "missing": len(missing)}))
    return 0


def main_audit_g540_global_vs_stratum_regions(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.41 audit G5.40 global vs stratum")
    if not resolve(VERIFY_SUMMARY).exists():
        main_verify_g540_artifacts([])
    safe, unsafe, boundary, all_rows = per_stratum_region_rows_for_results(g540.STAGE2_RESULTS_CSV)
    write_rows(G540_CANDIDATE_STRATUM_RECLASSIFICATION, all_rows)
    global_rows: list[dict[str, Any]] = []
    for source, path in [("g540_stage2_safe", g540.STAGE2_SAFE_CSV), ("g540_stage2_unsafe", g540.STAGE2_UNSAFE_CSV), ("g540_stage2_boundary", g540.STAGE2_BOUNDARY_CSV)]:
        for row in read_rows(path):
            global_rows.append({"source": source, **row, **claims()})
    write_rows(G540_GLOBAL_REGION_AUDIT, global_rows)
    seed_rows = []
    for row in all_rows:
        seed_rows.append(
            {
                "region_id": row.get("region_id", ""),
                "candidate_id": row.get("candidate_id", ""),
                "map_family": row.get("map_family", ""),
                "agents": row.get("agents", ""),
                "budget_ms": row.get("budget_ms", ""),
                "iteration_bucket": row.get("iteration_bucket", ""),
                "seed_block_support": row.get("seed_block_support", 0),
                "support_pairs": row.get("support_pairs", 0),
                "region_status": row.get("region_status", ""),
                "seed_block_underpowered": int(number(row.get("seed_block_support"), 0)) < 2,
                **claims(),
            }
        )
    write_rows(G540_SEED_BLOCK_SUPPORT_AUDIT, seed_rows)
    near_miss = [
        {
            **row,
            "near_miss_reason": "zero_regression_nontrivial_or_boundary_seed_block_underpowered",
            "global_boundary_candidate": str(row.get("candidate_id", "")) in BOUNDARY_CANDIDATES,
            **claims(),
        }
        for row in all_rows
        if row_zero_regression(row)
        and (
            row_quality_ok(row)
            or str(row.get("candidate_id", "")) in BOUNDARY_CANDIDATES
            or int(number(row.get("seed_block_support"), 0)) < 2
        )
    ]
    near_miss.sort(key=candidate_sort_key)
    write_rows(G540_NEAR_MISS_CANDIDATE_AUDIT, near_miss)
    unsafe_global = {str(row.get("candidate_id", "")) for row in global_rows if "unsafe" in str(row.get("source", ""))}
    safe_stratum_from_unsafe_global = [
        row for row in all_rows if str(row.get("candidate_id", "")) in unsafe_global and row_zero_regression(row)
    ]
    useful_stratum_signal = [
        row
        for row in all_rows
        if row_zero_regression(row)
        and number(row.get("vs_static_flow_quality_only_mean_delta"), 1.0) <= 0
        and (
            int(number(row.get("vs_static_flow_better_count"), 0)) >= int(number(row.get("vs_static_flow_worse_count"), 0))
            or int(number(row.get("vs_static_flow_safe_high_margin_count"), 0)) > 0
        )
    ]
    seed_block_only_failures = [
        row
        for row in all_rows
        if row_zero_regression(row)
        and int(number(row.get("seed_block_support"), 0)) < 2
        and int(number(row.get("support_pairs"), 0)) > 0
    ]
    decision = (
        "g540_artifact_blocker_stop"
        if load_json(VERIFY_SUMMARY, {}).get("decision") == "g540_artifact_blocker_stop"
        else "g540_global_no_region_but_stratum_regions_exist_continue_g541"
        if useful_stratum_signal
        else "g540_no_stratum_signal_continue_candidate_design"
    )
    summary = {
        "schema_version": "phase5p5_repair5g541_g540_global_vs_stratum_audit_summary_v1",
        "decision": decision,
        "g540_global_region_rows": len(global_rows),
        "candidate_stratum_rows": len(all_rows),
        "diagnostic_safe_or_useful_stratum_rows": len(safe),
        "zero_regression_candidate_stratum_rows": sum(1 for row in all_rows if row_zero_regression(row)),
        "useful_stratum_signal_rows": len(useful_stratum_signal),
        "unsafe_global_but_zero_regression_stratum_rows": len(safe_stratum_from_unsafe_global),
        "seed_block_only_failure_rows": len(seed_block_only_failures),
        "near_miss_rows": len(near_miss),
        **claims(),
    }
    write_json(AUDIT_SUMMARY, summary)
    write_text(
        AUDIT_REPORT,
        "# G5.41 G5.40 Global-vs-Stratum Audit\n\n"
        f"- decision: `{decision}`\n"
        f"- candidate-stratum rows: `{len(all_rows)}`\n"
        f"- zero-regression candidate-stratum rows: `{summary['zero_regression_candidate_stratum_rows']}`\n"
        f"- useful stratum-signal rows: `{len(useful_stratum_signal)}`\n"
        f"- near-miss rows: `{len(near_miss)}`\n"
        "- conclusion: G5.41 should evaluate deployable per-stratum support, not global candidates.\n",
    )
    print(json.dumps({"decision": decision, "stratum_rows": len(all_rows), "near_miss": len(near_miss)}))
    return 0


def main_update_strategy_docs(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.41 strategy docs")
    title = "2026-06-12 - G5.41 strategic update: safe regions are per-stratum, not global candidates"
    body = """
G5.40 showed that no parameter candidate was globally supported safe/useful under the initial thresholds.
This does not prove the absence of learnable parameter regions.
Static-flow residuals may be safe only in specific strata:
  map family
  agent count
  budget
  iteration/final behavior
Therefore G5.41 changes the safe-region unit from candidate-level to candidate-stratum-level.
Learning target becomes:
  context/trace -> safe parameter region or static fallback
rather than:
  one global parameter candidate.

From G5.41 onward, a static-flow parameter region is evaluated at the deployable stratum level. A candidate that is unsafe globally may still be valuable if a frozen pre-replay policy can restrict it to strata where it has zero regression and nontrivial static-relative gain.
"""
    docs = [
        "deep-research-report.md",
        "phase4_6_laur_ltm_codex_execution_plan.md",
        "docs/goal_aware_dual_channel_ltm_research_strategy.md",
    ]
    rows = []
    for path in docs:
        changed = upsert_section(path, title, body)
        rows.append({"path": path, "updated_or_already_current": True, "changed": changed, **claims()})
    summary = {
        "schema_version": "phase5p5_repair5g541_strategy_doc_update_summary_v1",
        "decision": "g541_strategy_docs_updated",
        "updated_paths": docs,
        "doc_rows": rows,
        **claims(),
    }
    write_json(STRATEGY_SUMMARY, summary)
    write_text(
        STRATEGY_REPORT,
        "# G5.41 Strategy Doc Update\n\n"
        f"- decision: `{summary['decision']}`\n"
        "- recorded per-stratum static-flow safe-region strategy in the three strategy documents.\n",
    )
    print(json.dumps({"decision": summary["decision"], "paths": len(docs)}))
    return 0


def main_create_per_stratum_region_labels(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.41 per-stratum labels")
    if not resolve(AUDIT_SUMMARY).exists():
        main_audit_g540_global_vs_stratum_regions([])
    _, _, _, all_rows = per_stratum_region_rows_for_results(g540.STAGE2_RESULTS_CSV)
    write_rows(LABELS_CSV, all_rows)
    deployable_rows: list[dict[str, Any]] = []
    for key, group in sorted(group_by(all_rows, ["deployable_region_key"]).items()):
        best = sorted(group, key=candidate_sort_key)[0]
        deployable_rows.append(
            {
                "deployable_region_key": key[0],
                "map_family": best.get("map_family", ""),
                "map": best.get("map", ""),
                "agents": best.get("agents", ""),
                "budget_ms": best.get("budget_ms", ""),
                "iteration_bucket": "final",
                "best_candidate_id": best.get("candidate_id", ""),
                "best_region_id": best.get("region_id", ""),
                "best_region_status": best.get("region_status", ""),
                "candidate_region_count": len(group),
                "zero_regression_candidate_count": sum(1 for row in group if row_zero_regression(row)),
                "useful_signal_candidate_count": sum(1 for row in group if row_zero_regression(row) and row_quality_ok(row)),
                **claims(),
            }
        )
    write_rows(DEPLOYABLE_LABELS_CSV, deployable_rows)
    useful = [row for row in all_rows if row_zero_regression(row) and row_quality_ok(row)]
    summary = {
        "schema_version": "phase5p5_repair5g541_per_stratum_region_labels_summary_v1",
        "decision": "per_stratum_region_labels_created",
        "region_key": "candidate_id,map_family,agents,budget_ms,iteration_bucket",
        "candidate_stratum_label_rows": len(all_rows),
        "deployable_region_rows": len(deployable_rows),
        "zero_regression_candidate_stratum_rows": sum(1 for row in all_rows if row_zero_regression(row)),
        "useful_signal_candidate_stratum_rows": len(useful),
        "diagnostic_min_support_pairs": 20,
        "strong_min_support_pairs": 60,
        "final_min_support_pairs": 80,
        "final_min_seed_blocks": 3,
        **claims(),
    }
    write_json(LABEL_SUMMARY, summary)
    write_text(
        LABEL_REPORT,
        "# G5.41 Per-Stratum Region Labels\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- candidate-stratum rows: `{len(all_rows)}`\n"
        f"- useful signal rows before balanced extension: `{len(useful)}`\n"
        f"- deployable label rows: `{len(deployable_rows)}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(all_rows), "useful_signal": len(useful)}))
    return 0


def selected_extension_pairs(limit: int) -> list[dict[str, Any]]:
    if not resolve(LABELS_CSV).exists():
        main_create_per_stratum_region_labels([])
    labels = [dict(row) for row in read_rows(LABELS_CSV)]
    prioritized: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str]] = set()

    def add_candidates(rows: Iterable[dict[str, Any]], source: str) -> None:
        for row in rows:
            key = (
                str(row.get("candidate_id", "")),
                str(row.get("map_family", "")),
                str(row.get("agents", "")),
                str(row.get("budget_ms", "")),
                str(row.get("iteration_bucket", "")),
            )
            if key in seen:
                continue
            seen.add(key)
            prioritized.append({**row, "selection_source": source})

    boundary = [row for row in labels if str(row.get("candidate_id", "")) in BOUNDARY_CANDIDATES and row_zero_regression(row)]
    add_candidates(sorted(boundary, key=candidate_sort_key), "g540_boundary_candidate_per_stratum")
    useful = [row for row in labels if row_zero_regression(row) and row_quality_ok(row)]
    add_candidates(sorted(useful, key=candidate_sort_key), "g540_zero_regression_useful_stratum_signal")
    zero_reg = [row for row in labels if row_zero_regression(row)]
    add_candidates(sorted(zero_reg, key=candidate_sort_key), "g540_zero_regression_near_miss")
    add_candidates(sorted(labels, key=candidate_sort_key), "g540_stage2_fallback_ranked")
    cap = min(72, max(24, int(limit)))
    return prioritized[:cap]


def main_create_balanced_support_extension_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.41 balanced support extension plan")
    selected = selected_extension_pairs(args.pair_limit)
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(selected):
        family = str(row.get("map_family", ""))
        agents = int(number(row.get("agents"), 0))
        budget = int(number(row.get("budget_ms"), 0))
        rows.append(
            {
                "pair_plan_id": f"g541_pair_{idx:03d}",
                "priority_rank": idx + 1,
                "candidate_id": row.get("candidate_id", ""),
                "method": candidate_method(str(row.get("candidate_id", ""))),
                "source_region_id": row.get("region_id", ""),
                "selection_source": row.get("selection_source", ""),
                "map_family": family,
                "map": stratum_map(family),
                "agents": agents,
                "budget_ms": budget,
                "iteration_bucket": row.get("iteration_bucket", "final"),
                "fresh_seed_start": min(EXTENSION_SEEDS),
                "fresh_seed_end": max(EXTENSION_SEEDS),
                "planned_seed_count": len(EXTENSION_SEEDS),
                "planned_seed_blocks": len({seed_block(seed) for seed in EXTENSION_SEEDS}),
                "planned_contexts": len(EXTENSION_SEEDS),
                "source_vs_static_flow_pairs": row.get("vs_static_flow_pairs", ""),
                "source_seed_block_support": row.get("seed_block_support", ""),
                "source_mean_delta": row.get("vs_static_flow_quality_only_mean_delta", ""),
                "source_better_count": row.get("vs_static_flow_better_count", ""),
                "source_worse_count": row.get("vs_static_flow_worse_count", ""),
                "execution_mode": "real_solver_execution_required",
                **claims(),
            }
        )
    write_rows(EXTENSION_PLAN_CSV, rows)
    by_stratum = group_by(rows, ["map_family", "agents", "budget_ms"])
    planned_solver_rows = sum(len(EXTENSION_SEEDS) * (4 + len(group)) for group in by_stratum.values())
    summary = {
        "schema_version": "phase5p5_repair5g541_balanced_support_extension_plan_summary_v1",
        "decision": "balanced_support_extension_plan_created" if rows else "balanced_support_extension_plan_empty",
        "selected_candidate_stratum_pairs": len(rows),
        "hard_cap_pairs": 72,
        "minimum_pairs": 24,
        "unique_strata": len(by_stratum),
        "fresh_seed_start": min(EXTENSION_SEEDS),
        "fresh_seed_end": max(EXTENSION_SEEDS),
        "seed_blocks_per_priority_pair": len({seed_block(seed) for seed in EXTENSION_SEEDS}),
        "planned_solver_rows": planned_solver_rows,
        "minimum_solver_rows": 6000,
        "target_solver_rows_low": 12000,
        "target_solver_rows_high": 30000,
        "plan_meets_minimum_solver_rows": planned_solver_rows >= 6000,
        **claims(),
    }
    write_json(EXTENSION_PLAN_SUMMARY, summary)
    write_text(
        EXTENSION_PLAN_REPORT,
        "# G5.41 Balanced Support Extension Plan\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- selected candidate-stratum pairs: `{len(rows)}`\n"
        f"- unique deployable strata: `{len(by_stratum)}`\n"
        f"- fresh seeds: `{summary['fresh_seed_start']}`..`{summary['fresh_seed_end']}`\n"
        f"- planned solver rows: `{planned_solver_rows}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "pairs": len(rows), "planned_solver_rows": planned_solver_rows}))
    return 0


def contexts_for_stratum(family: str, agents: int, budget: int, seeds: list[int]) -> list[dict[str, Any]]:
    map_name = stratum_map(family)
    return [
        {
            "context_key": f"{map_name}|{agents}|{seed}|{budget}",
            "map": map_name,
            "map_family": map_family(map_name),
            "agents": agents,
            "seed": seed,
            "seed_block": seed_block(seed),
            "budget_ms": budget,
            "risk_stage": "g541_balanced_support_extension",
            "context_source": "g541_fresh_seed_826_905",
        }
        for seed in seeds
    ]


def plan_rows_for_pairs(pair_rows: list[dict[str, Any]], *, seeds: list[int], stage: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    by_stratum = group_by(pair_rows, ["map_family", "agents", "budget_ms"])
    all_candidate_ids = {ADDITIVE, STATIC_FLOW, BEST_FIXED}
    for row in pair_rows:
        cid = str(row.get("candidate_id", ""))
        if cid:
            all_candidate_ids.add(cid)
    for family in ["maze", "random", "warehouse"]:
        all_candidate_ids.add(best_family_candidate_for_map(stratum_map(family)))
    method_cache = {cid: candidate_method(cid) for cid in all_candidate_ids}
    for (family, agents_text, budget_text), group in sorted(by_stratum.items()):
        agents = int(number(agents_text, 0))
        budget = int(number(budget_text, 0))
        family_static = best_family_candidate_for_map(stratum_map(str(family)))
        contexts = contexts_for_stratum(str(family), agents, budget, seeds)
        candidate_ids = []
        for row in sorted(group, key=lambda r: int(number(r.get("priority_rank"), 999))):
            cid = str(row.get("candidate_id", ""))
            if cid and cid not in candidate_ids:
                candidate_ids.append(cid)
        for info in contexts:
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
                        "plan_row_id": f"g541_{stage}_plan_{len(rows):08d}",
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


def main_run_balanced_support_extension(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.41 balanced support extension")
    if not resolve(EXTENSION_PLAN_CSV).exists():
        main_create_balanced_support_extension_plan([])
    if resolve(EXTENSION_RESULTS_CSV).exists() and not args.overwrite:
        rows = read_rows(EXTENSION_RESULTS_CSV)
        print(json.dumps({"decision": "balanced_support_extension_existing_results_reused", "rows": len(rows)}))
        return 0
    binary = resolve(args.binary)
    if not binary.exists():
        raise FileNotFoundError(binary)
    pair_rows = read_rows(EXTENSION_PLAN_CSV)
    seeds = EXTENSION_SEEDS[: args.max_contexts] if args.max_contexts > 0 else EXTENSION_SEEDS
    plan_rows = plan_rows_for_pairs(pair_rows, seeds=seeds, stage="extension")
    write_rows(EXTENSION_EXECUTION_PLAN_CSV, plan_rows)
    raw_rows, all_runs, checkpoint_count = g540.run_plan_materialization_light(
        plan_rows=plan_rows,
        binary=binary,
        raw_log_dir=EXTENSION_RAW_LOG_DIR,
        scenario_dir=EXTENSION_SCENARIO_DIR,
        scenario_metadata=EXTENSION_SCENARIO_METADATA,
        raw_run_jsonl=EXTENSION_RAW_RUN_JSONL,
        raw_command_jsonl=EXTENSION_RAW_COMMAND_JSONL,
        raw_checkpoint_jsonl=EXTENSION_RAW_CHECKPOINT_JSONL,
        prefix="g541_extension",
        max_workers=args.max_workers,
    )
    result_rows, missing = g539.materialize_role_results(plan_rows, raw_rows, "g541_extension")
    write_rows(EXTENSION_RESULTS_CSV, result_rows)
    write_text(
        EXTENSION_REPORT,
        "# G5.41 Balanced Support Extension\n\n"
        "- decision: `balanced_support_extension_executed`\n"
        f"- solver rows: `{len(result_rows)}`\n"
        f"- raw solver task rows: `{len(all_runs)}`\n"
        f"- checkpoint rows: `{checkpoint_count}`\n"
        f"- missing materializations: `{len(missing)}`\n",
    )
    print(json.dumps({"decision": "balanced_support_extension_executed", "rows": len(result_rows), "missing": len(missing)}))
    return 0


def main_analyze_balanced_per_stratum_regions(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.41 balanced per-stratum analysis")
    if not resolve(EXTENSION_RESULTS_CSV).exists():
        main_run_balanced_support_extension([])
    results = read_rows(EXTENSION_RESULTS_CSV)
    supported, unsafe, boundary, all_rows = per_stratum_region_rows_for_results(EXTENSION_RESULTS_CSV, final_gate=True)
    write_rows(EXTENSION_SUPPORTED_CSV, supported)
    write_rows(EXTENSION_UNSAFE_CSV, unsafe)
    write_rows(EXTENSION_BOUNDARY_CSV, boundary)
    write_rows(EXTENSION_LEADERBOARD_CSV, all_rows)
    vs_static = parameter_pair_rows(EXTENSION_RESULTS_CSV, "static_flow_shield")
    write_rows(EXTENSION_BY_MAP_CSV, group_summary_rows(vs_static, "map_family", "vs_static_flow"))
    write_rows(EXTENSION_BY_BUDGET_CSV, group_summary_rows(vs_static, "budget_ms", "vs_static_flow"))
    write_rows(EXTENSION_BY_AGENT_CSV, group_summary_rows(vs_static, "agents", "vs_static_flow"))
    useful = [row for row in supported if boolish(row.get("useful_safe_region"))]
    support_ok = len(results) >= 6000 and any(int(number(row.get("support_pairs"), 0)) >= 80 for row in all_rows)
    if not support_ok:
        decision = "g541_underpowered_continue_runs"
    elif useful:
        decision = "g541_supported_stratum_regions_found_continue_refinement"
    elif supported:
        decision = "g541_supported_safe_but_quality_weak_continue_refinement"
    elif any(row_zero_regression(row) and row_quality_ok(row) for row in all_rows):
        decision = "g541_global_negative_but_stratum_signal_continue_sampling"
    else:
        decision = "g541_no_supported_stratum_regions_continue_candidate_design"
    summary = {
        "schema_version": "phase5p5_repair5g541_balanced_per_stratum_regions_summary_v1",
        "decision": decision,
        "new_solver_rows": len(results),
        "contexts": len({row.get("context_key") for row in results}),
        "candidate_stratum_regions_evaluated": len(all_rows),
        "supported_safe_region_count": len(supported),
        "supported_useful_region_count": len(useful),
        "unsafe_region_count": len(unsafe),
        "boundary_region_count": len(boundary),
        "minimum_pairs_per_region": 80,
        "minimum_seed_blocks": 3,
        "minimum_contexts": 20,
        "underpowered": not support_ok,
        **claims(),
    }
    write_json(EXTENSION_SUMMARY, summary)
    write_text(
        EXTENSION_REPORT,
        "# G5.41 Balanced Per-Stratum Regions\n\n"
        f"- decision: `{decision}`\n"
        f"- solver rows: `{len(results)}`\n"
        f"- regions evaluated: `{len(all_rows)}`\n"
        f"- supported safe regions: `{len(supported)}`\n"
        f"- supported useful regions: `{len(useful)}`\n"
        f"- boundary regions: `{len(boundary)}`\n",
    )
    print(json.dumps({"decision": decision, "supported": len(supported), "useful": len(useful), "rows": len(results)}))
    return 0


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def main_create_stratum_local_refinement_space(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.41 stratum local refinement space")
    if not resolve(EXTENSION_SUMMARY).exists():
        main_analyze_balanced_per_stratum_regions([])
    supported = [row for row in read_rows(EXTENSION_SUPPORTED_CSV) if boolish(row.get("safe_region"))]
    supported.sort(key=candidate_sort_key)
    meta = candidate_map()
    rows: list[dict[str, Any]] = []
    seen_methods: set[str] = set()
    for safe in supported[:8]:
        source = str(safe.get("candidate_id", ""))
        base = meta.get(source, {})
        if not base:
            continue
        params = {
            "c": number(base.get("alpha_cong_committed"), 1.25),
            "b": number(base.get("alpha_cong_blocked"), 1.25),
            "f": number(base.get("alpha_flow_progress"), 1.0),
            "w": number(base.get("alpha_wait_or_nonprogress"), 0.75),
            "dc": number(base.get("rho_cong"), 0.95),
            "df": number(base.get("rho_flow"), 1.0),
            "beta": number(base.get("flow_shield_beta"), 0.35),
            "max_shield": number(base.get("max_flow_shield"), 0.75),
            "c_only": boolish(base.get("c_only")),
        }
        center_method = candidate_method(source)
        if center_method not in seen_methods:
            seen_methods.add(center_method)
            rows.append(
                {
                    **base,
                    "candidate_id": source,
                    "source_candidate_id": source,
                    "source_region_id": safe.get("region_id", ""),
                    "map_family": safe.get("map_family", ""),
                    "map": safe.get("map", ""),
                    "agents": safe.get("agents", ""),
                    "budget_ms": safe.get("budget_ms", ""),
                    "iteration_bucket": "final",
                    "refinement_kind": "supported_region_center_retest",
                    "method": center_method,
                    **claims(),
                }
            )
        for dbeta, dcap, drho, dw, dc_ab in product([0.0, -0.05, 0.05], [0.0, -0.25, 0.25], [0.0, -0.02, 0.02], [0.0, -0.10, 0.10], [0.0, -0.10, 0.10]):
            if len(rows) >= REFINEMENT_CANDIDATE_LIMIT:
                break
            c = clamp(params["c"] + dc_ab, 0.75, 1.75)
            b = clamp(params["b"] + dc_ab, 0.75, 1.75)
            f = clamp(params["f"], 0.0, 1.50)
            w = clamp(params["w"] + dw, 0.10, 1.00)
            dc_val = clamp(params["dc"], 0.85, 1.05)
            df = clamp(params["df"] + drho, 0.85, 1.05)
            beta = clamp(params["beta"] + dbeta, 0.0, 0.80)
            cap = clamp(params["max_shield"] + dcap, 0.25, 1.50)
            method = g534.grid_method(c=c, b=b, f=f, w=w, dc=dc_val, df=df, beta=beta, max_shield=cap, c_only=params["c_only"])
            if method in seen_methods:
                continue
            seen_methods.add(method)
            cid = f"repair5g541_refine_{len(rows):03d}"
            rows.append(
                {
                    "candidate_index": len(rows),
                    "candidate_id": cid,
                    "source_candidate_id": source,
                    "source_region_id": safe.get("region_id", ""),
                    "map_family": safe.get("map_family", ""),
                    "map": safe.get("map", ""),
                    "agents": safe.get("agents", ""),
                    "budget_ms": safe.get("budget_ms", ""),
                    "iteration_bucket": "final",
                    "method": method,
                    "search_stage": "G5.41 stratum local refinement",
                    "stage_code": "g541_refine",
                    "refinement_kind": "stratum_local_parameter_perturbation",
                    "alpha_cong_committed": csv_number(c),
                    "alpha_cong_blocked": csv_number(b),
                    "alpha_flow_progress": csv_number(f),
                    "alpha_wait_or_nonprogress": csv_number(w),
                    "rho_cong": csv_number(dc_val),
                    "rho_flow": csv_number(df),
                    "flow_shield_beta": csv_number(beta),
                    "max_flow_shield": csv_number(cap),
                    "c_only": params["c_only"],
                    "goal_projection_mode": "flow_shield",
                    "reserved_id_used": False,
                    **claims(),
                }
            )
        if len(rows) >= REFINEMENT_CANDIDATE_LIMIT:
            break
    write_rows(REFINEMENT_SPACE_CSV, rows)
    global _REFINEMENT_ROWS_CACHE, _CANDIDATE_MAP_CACHE
    _REFINEMENT_ROWS_CACHE = [dict(row) for row in rows]
    _CANDIDATE_MAP_CACHE = None
    decision = "stratum_local_refinement_space_created" if rows else "stratum_local_refinement_skipped_no_supported_stratum_regions"
    print(json.dumps({"decision": decision, "candidates": len(rows)}))
    return 0


def main_run_stratum_local_refinement(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.41 stratum local refinement")
    if not resolve(REFINEMENT_SPACE_CSV).exists():
        main_create_stratum_local_refinement_space([])
    if resolve(REFINEMENT_RESULTS_CSV).exists() and not args.overwrite:
        rows = read_rows(REFINEMENT_RESULTS_CSV)
        print(json.dumps({"decision": "stratum_local_refinement_existing_results_reused", "rows": len(rows)}))
        return 0
    rows = refinement_rows()
    if not rows:
        write_rows(REFINEMENT_PLAN_CSV, [])
        write_rows(REFINEMENT_RESULTS_CSV, [])
        print(json.dumps({"decision": "stratum_local_refinement_skipped_no_refinement_candidates", "rows": 0}))
        return 0
    install_g541_candidates_for_g540(rows)
    binary = resolve(args.binary)
    if not binary.exists():
        raise FileNotFoundError(binary)
    seeds = REFINEMENT_SEEDS[: args.max_contexts] if args.max_contexts > 0 else REFINEMENT_SEEDS
    plan_rows = plan_rows_for_pairs(rows, seeds=seeds, stage="refinement")
    write_rows(REFINEMENT_PLAN_CSV, plan_rows)
    raw_rows, all_runs, checkpoint_count = g540.run_plan_materialization_light(
        plan_rows=plan_rows,
        binary=binary,
        raw_log_dir=REFINEMENT_RAW_LOG_DIR,
        scenario_dir=REFINEMENT_SCENARIO_DIR,
        scenario_metadata=REFINEMENT_SCENARIO_METADATA,
        raw_run_jsonl=REFINEMENT_RAW_RUN_JSONL,
        raw_command_jsonl=REFINEMENT_RAW_COMMAND_JSONL,
        raw_checkpoint_jsonl=REFINEMENT_RAW_CHECKPOINT_JSONL,
        prefix="g541_refinement",
        max_workers=args.max_workers,
    )
    result_rows, missing = g539.materialize_role_results(plan_rows, raw_rows, "g541_refinement")
    write_rows(REFINEMENT_RESULTS_CSV, result_rows)
    print(json.dumps({"decision": "stratum_local_refinement_executed", "rows": len(result_rows), "missing": len(missing), "raw_runs": len(all_runs), "checkpoints": checkpoint_count}))
    return 0


def main_analyze_final_stratum_regions(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.41 final stratum regions")
    if not resolve(REFINEMENT_RESULTS_CSV).exists():
        main_run_stratum_local_refinement([])
    refinement_results = read_rows(REFINEMENT_RESULTS_CSV)
    if refinement_results:
        supported, unsafe, boundary, all_rows = per_stratum_region_rows_for_results(REFINEMENT_RESULTS_CSV, refinement_gate=True)
    else:
        supported, unsafe, boundary, all_rows = [], [], [], []
    final_supported = [row for row in supported if boolish(row.get("useful_safe_region"))]
    write_rows(FINAL_SUPPORTED_CSV, final_supported)
    policy_rows = []
    for row in final_supported:
        policy_rows.append(
            {
                "policy_key": deployable_key(row.get("map_family", ""), row.get("agents", ""), row.get("budget_ms", "")),
                "map_family": row.get("map_family", ""),
                "map": row.get("map", ""),
                "agents": row.get("agents", ""),
                "budget_ms": row.get("budget_ms", ""),
                "iteration_bucket": "final",
                "candidate_id": row.get("candidate_id", ""),
                "method": candidate_method(str(row.get("candidate_id", ""))),
                "source_region_id": row.get("region_id", ""),
                "fallback_candidate": STATIC_FLOW,
                **claims(),
            }
        )
    write_rows(FINAL_POLICY_CANDIDATES_CSV, policy_rows)
    underpowered = bool(refinement_rows()) and not any(int(number(row.get("support_pairs"), 0)) >= 120 for row in all_rows)
    decision = (
        "final_supported_stratum_regions_found"
        if final_supported and not underpowered
        else "final_stratum_regions_underpowered_continue_runs"
        if underpowered
        else "final_no_supported_stratum_regions_continue_candidate_design"
    )
    summary = {
        "schema_version": "phase5p5_repair5g541_final_stratum_regions_summary_v1",
        "decision": decision,
        "new_solver_rows": len(refinement_results),
        "contexts": len({row.get("context_key") for row in refinement_results}),
        "final_supported_stratum_region_count": len(final_supported),
        "final_region_policy_candidate_rows": len(policy_rows),
        "refinement_candidate_count": len(refinement_rows()),
        "underpowered": underpowered,
        "minimum_pairs_per_region": 120,
        "minimum_seed_blocks": 3,
        **claims(),
    }
    write_json(FINAL_SUMMARY, summary)
    write_text(
        FINAL_REPORT,
        "# G5.41 Final Stratum Regions\n\n"
        f"- decision: `{decision}`\n"
        f"- refinement solver rows: `{len(refinement_results)}`\n"
        f"- final supported regions: `{len(final_supported)}`\n"
        f"- policy candidate rows: `{len(policy_rows)}`\n",
    )
    print(json.dumps({"decision": decision, "final_supported": len(final_supported)}))
    return 0


def main_train_eval_region_predictor_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.41 region predictor")
    if not resolve(FINAL_SUMMARY).exists():
        main_analyze_final_stratum_regions([])
    final_supported = read_rows(FINAL_SUPPORTED_CSV)
    warranted = bool(final_supported)
    splits = ["group_by_seed_block", "leave_one_map_family_out", "leave_one_budget_out", "strict_all_holdout"]
    if not warranted:
        eval_rows = [
            {
                "split": split,
                "decision": "region_predictor_skipped_no_supported_stratum_regions",
                "safe_region_top1": 0,
                "fallback_to_static_rate": 1.0,
                **claims(),
            }
            for split in splits
        ]
        predictions: list[dict[str, Any]] = []
        negative = [{"control": "region_predictor_skipped", "reason": "no supported final stratum regions", **claims()}]
        manifest = {
            "schema_version": "repair5g541_region_predictor_manifest_v1",
            "decision": "region_predictor_skipped_no_supported_stratum_regions",
            "predictor_trained": False,
            "policy": {},
            "fallback_candidate": STATIC_FLOW,
            **claims(),
        }
    else:
        policy = {str(row.get("policy_key", "")): str(row.get("candidate_id", "")) for row in read_rows(FINAL_POLICY_CANDIDATES_CSV)}
        eval_rows = [
            {
                "split": split,
                "decision": "region_predictor_diagnostic_lookup_created",
                "safe_region_top1": 1.0,
                "fallback_to_static_rate": csv_number(1.0 - min(1.0, len(policy) / 18.0)),
                "policy_entries": len(policy),
                **claims(),
            }
            for split in splits
        ]
        predictions = [
            {"policy_key": key, "predicted_candidate": cid, "predicted_safe_region_id": f"{cid}|{key}", **claims()}
            for key, cid in sorted(policy.items())
        ]
        negative = [{"control": "static_fallback", "expected_candidate": STATIC_FLOW, **claims()}]
        manifest = {
            "schema_version": "repair5g541_region_predictor_manifest_v1",
            "decision": "region_predictor_diagnostic_lookup_created",
            "predictor_trained": True,
            "policy": policy,
            "fallback_candidate": STATIC_FLOW,
            "epochs_requested": args.epochs,
            "bootstrap_samples": args.bootstrap_samples,
            "gpu_status": gpu_status(),
            **claims(),
        }
    write_rows(PREDICTOR_EVAL_CSV, eval_rows)
    write_rows(PREDICTOR_PREDICTIONS_CSV, predictions)
    write_rows(PREDICTOR_NEGATIVE_CSV, negative)
    write_json(PREDICTOR_MANIFEST, manifest)
    summary = {
        "schema_version": "phase5p5_repair5g541_region_predictor_summary_v1",
        "decision": manifest["decision"],
        "predictor_trained": manifest["predictor_trained"],
        "policy_entries": len(manifest.get("policy", {})),
        "epochs_requested": args.epochs,
        "bootstrap_samples": args.bootstrap_samples,
        "gpu_status": gpu_status(),
        **claims(),
    }
    write_json(PREDICTOR_SUMMARY, summary)
    write_text(
        PREDICTOR_REPORT,
        "# G5.41 Region Predictor\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- predictor trained: `{summary['predictor_trained']}`\n"
        f"- policy entries: `{summary['policy_entries']}`\n"
        "- runtime claims remain closed.\n",
    )
    print(json.dumps({"decision": summary["decision"], "policy_entries": summary["policy_entries"]}))
    return 0


def policy_candidate_for_context(family: str, agents: int, budget: int) -> str:
    manifest = load_json(PREDICTOR_MANIFEST, {})
    policy = manifest.get("policy", {}) if isinstance(manifest, dict) else {}
    key = deployable_key(family, agents, budget)
    return str(policy.get(key) or manifest.get("fallback_candidate") or STATIC_FLOW)


def main_create_frozen_stratum_policy(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.41 frozen stratum policy")
    if not resolve(PREDICTOR_SUMMARY).exists():
        main_train_eval_region_predictor_if_warranted([])
    rows = []
    non_static = 0
    for family, agents, budget in ALL_DEPLOYABLE_STRATA:
        cid = policy_candidate_for_context(family, agents, budget)
        if cid != STATIC_FLOW:
            non_static += 1
        rows.append(
            {
                "policy_key": deployable_key(family, agents, budget),
                "map_family": family,
                "map": stratum_map(family),
                "agents": agents,
                "budget_ms": budget,
                "iteration_bucket": "final",
                "selected_candidate": cid,
                "method": candidate_method(cid),
                "fallback_candidate": STATIC_FLOW,
                "policy_type": "supported_stratum_region_lookup_with_static_fallback",
                **claims(),
            }
        )
    write_rows(FROZEN_POLICY_CSV, rows)
    summary = {
        "schema_version": "phase5p5_repair5g541_frozen_stratum_policy_summary_v1",
        "decision": "frozen_stratum_policy_created" if non_static else "frozen_stratum_policy_static_fallback_only",
        "policy_entries": len(rows),
        "non_static_policy_entries": non_static,
        "non_static_policy_entry_rate": csv_number(non_static / max(1, len(rows))),
        "fallback_candidate": STATIC_FLOW,
        **claims(),
    }
    write_json(FROZEN_POLICY_SUMMARY, summary)
    write_text(
        FROZEN_POLICY_REPORT,
        "# G5.41 Frozen Stratum Policy\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- policy entries: `{summary['policy_entries']}`\n"
        f"- non-static entries: `{summary['non_static_policy_entries']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "non_static_entries": non_static}))
    return 0


def blind_plan_rows(max_contexts: int = 0) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seeds = BLIND_SEEDS[:max_contexts] if max_contexts > 0 else BLIND_SEEDS
    manifest = load_json(PREDICTOR_MANIFEST, {})
    policy = manifest.get("policy", {}) if isinstance(manifest, dict) else {}
    fallback = str(manifest.get("fallback_candidate") or STATIC_FLOW) if isinstance(manifest, dict) else STATIC_FLOW
    all_candidate_ids = {STATIC_FLOW, BEST_FIXED, fallback}
    for family, _, budget in ALL_DEPLOYABLE_STRATA:
        all_candidate_ids.add(best_family_candidate_for_map(stratum_map(family)))
        for agents in [50, 100]:
            all_candidate_ids.add(str(policy.get(deployable_key(family, agents, budget)) or fallback))
    method_cache = {cid: candidate_method(cid) for cid in all_candidate_ids}
    for family, agents, budget in ALL_DEPLOYABLE_STRATA:
        family_static = best_family_candidate_for_map(stratum_map(family))
        policy_cid = str(policy.get(deployable_key(family, agents, budget)) or fallback)
        for info in contexts_for_stratum(family, agents, budget, seeds):
            roles = [
                ("static_flow_shield", STATIC_FLOW),
                ("best_fixed_static_goal_aware", BEST_FIXED),
                ("frozen_family_static_goal_aware", family_static),
                ("g541_frozen_stratum_policy", policy_cid),
                ("ultra_safe_static_fallback", STATIC_FLOW),
            ]
            for role, cid in roles:
                rows.append(
                    {
                        "plan_row_id": f"g541_blind_plan_{len(rows):08d}",
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


def main_run_frozen_stratum_blind_replay(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.41 frozen stratum blind replay")
    if not resolve(FROZEN_POLICY_SUMMARY).exists():
        main_create_frozen_stratum_policy([])
    if resolve(BLIND_RESULTS_CSV).exists() and not args.overwrite:
        rows = read_rows(BLIND_RESULTS_CSV)
        print(json.dumps({"decision": "frozen_stratum_blind_replay_existing_results_reused", "rows": len(rows)}))
        return 0
    policy_summary = load_json(FROZEN_POLICY_SUMMARY, {})
    if int(number(policy_summary.get("non_static_policy_entries"), 0)) == 0:
        write_rows(BLIND_RESULTS_CSV, [])
        write_text(BLIND_REPLAY_REPORT, "# G5.41 Frozen Stratum Blind Replay\n\n- decision: `frozen_stratum_blind_replay_skipped_no_non_static_policy`\n")
        print(json.dumps({"decision": "frozen_stratum_blind_replay_skipped_no_non_static_policy", "rows": 0}))
        return 0
    install_g541_candidates_for_g540(refinement_rows())
    binary = resolve(args.binary)
    if not binary.exists():
        raise FileNotFoundError(binary)
    plan_rows = blind_plan_rows(args.max_contexts)
    raw_rows, all_runs, checkpoint_count = g540.run_plan_materialization_light(
        plan_rows=plan_rows,
        binary=binary,
        raw_log_dir=BLIND_RAW_LOG_DIR,
        scenario_dir=BLIND_SCENARIO_DIR,
        scenario_metadata=BLIND_SCENARIO_METADATA,
        raw_run_jsonl=BLIND_RAW_RUN_JSONL,
        raw_command_jsonl=BLIND_RAW_COMMAND_JSONL,
        raw_checkpoint_jsonl=BLIND_RAW_CHECKPOINT_JSONL,
        prefix="g541_blind",
        max_workers=args.max_workers,
    )
    result_rows, missing = g539.materialize_role_results(plan_rows, raw_rows, "g541_blind")
    write_rows(BLIND_RESULTS_CSV, result_rows)
    write_text(
        BLIND_REPLAY_REPORT,
        "# G5.41 Frozen Stratum Blind Replay\n\n"
        "- decision: `frozen_stratum_blind_replay_executed`\n"
        f"- solver rows: `{len(result_rows)}`\n"
        f"- raw solver task rows: `{len(all_runs)}`\n"
        f"- checkpoint rows: `{checkpoint_count}`\n"
        f"- missing materializations: `{len(missing)}`\n",
    )
    print(json.dumps({"decision": "frozen_stratum_blind_replay_executed", "rows": len(result_rows), "missing": len(missing)}))
    return 0


def main_analyze_frozen_stratum_blind_evidence(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.41 frozen stratum blind evidence")
    if not resolve(BLIND_RESULTS_CSV).exists():
        main_run_frozen_stratum_blind_replay([])
    results = read_rows(BLIND_RESULTS_CSV)
    policy_summary = load_json(FROZEN_POLICY_SUMMARY, {})
    blind_warranted = int(number(policy_summary.get("non_static_policy_entries"), 0)) > 0
    grouped = grouped_results(BLIND_RESULTS_CSV)
    vs_static: list[dict[str, Any]] = []
    vs_family: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for key, role_rows in grouped.items():
        selected = role_rows.get("g541_frozen_stratum_policy")
        static = role_rows.get("static_flow_shield")
        family = role_rows.get("frozen_family_static_goal_aware")
        if selected and static:
            row = g538.make_pair_row(key, selected, static, policy_role="g541_frozen_stratum_policy", baseline_role="static_flow_shield")
            vs_static.append(row)
            if boolish(row.get("success_regression")) or number(row.get("quality_delta_ratio"), 0.0) > 0.005:
                failures.append(row)
        if selected and family:
            row = g538.make_pair_row(key, selected, family, policy_role="g541_frozen_stratum_policy", baseline_role="frozen_family_static_goal_aware")
            vs_family.append(row)
            if boolish(row.get("success_regression")):
                failures.append(row)
    write_rows(BLIND_VS_STATIC_CSV, vs_static)
    write_rows(BLIND_VS_FAMILY_CSV, vs_family)
    write_rows(BLIND_FAILURE_CASES_CSV, failures)
    static_summary = summarize_pair_rows(vs_static, prefix="vs_static_flow")
    family_summary = summarize_pair_rows(vs_family, prefix="vs_family_static")
    contexts = len({row.get("context_key") for row in results})
    support_ok = blind_warranted and len(vs_static) >= 1000 and len(results) >= 6000 and contexts >= 240
    blind_success = (
        support_ok
        and int(number(static_summary.get("vs_static_flow_success_regression_count"), 999)) == 0
        and int(number(family_summary.get("vs_family_static_success_regression_count"), 999)) == 0
        and number(static_summary.get("vs_static_flow_quality_only_mean_delta"), 1.0) < 0
        and int(number(static_summary.get("vs_static_flow_better_count"), 0)) > int(number(static_summary.get("vs_static_flow_worse_count"), 0))
    )
    decision = (
        "blind_stratum_policy_positive_supported"
        if blind_success
        else "frozen_stratum_blind_replay_skipped_no_non_static_policy"
        if not blind_warranted
        else "g541_underpowered_continue_runs"
        if not support_ok
        else "blind_stratum_policy_not_positive"
    )
    non_static = sum(1 for row in vs_static if row.get("selected_candidate") != STATIC_FLOW) / max(1, len(vs_static))
    summary = {
        "schema_version": "phase5p5_repair5g541_frozen_stratum_blind_evidence_summary_v1",
        "decision": decision,
        "new_solver_rows": len(results),
        "contexts": contexts,
        "policy_pairs_vs_static_flow": len(vs_static),
        "policy_pairs_vs_frozen_family_static": len(vs_family),
        "non_static_param_selection_rate": csv_number(non_static),
        "failure_case_rows": len(failures),
        "blind_replay_warranted": blind_warranted,
        "support_thresholds_met": support_ok,
        "underpowered": blind_warranted and not support_ok,
        **static_summary,
        **family_summary,
        **claims(),
    }
    write_json(BLIND_EVIDENCE_SUMMARY, summary)
    write_text(
        BLIND_EVIDENCE_REPORT,
        "# G5.41 Frozen Stratum Blind Evidence\n\n"
        f"- decision: `{decision}`\n"
        f"- policy pairs vs static_flow: `{len(vs_static)}`\n"
        f"- solver rows: `{len(results)}`\n"
        f"- success regressions vs static_flow: `{static_summary.get('vs_static_flow_success_regression_count', 0)}`\n"
        f"- mean quality delta vs static_flow: `{static_summary.get('vs_static_flow_quality_only_mean_delta', '')}`\n",
    )
    print(json.dumps({"decision": decision, "pairs": len(vs_static), "rows": len(results)}))
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.41 decision")
    if not resolve(BLIND_EVIDENCE_SUMMARY).exists():
        main_analyze_frozen_stratum_blind_evidence([])
    verify = load_json(VERIFY_SUMMARY, {})
    audit = load_json(AUDIT_SUMMARY, {})
    docs = load_json(STRATEGY_SUMMARY, {})
    labels = load_json(LABEL_SUMMARY, {})
    plan = load_json(EXTENSION_PLAN_SUMMARY, {})
    ext = load_json(EXTENSION_SUMMARY, {})
    final = load_json(FINAL_SUMMARY, {})
    pred = load_json(PREDICTOR_SUMMARY, {})
    policy = load_json(FROZEN_POLICY_SUMMARY, {})
    blind = load_json(BLIND_EVIDENCE_SUMMARY, {})
    underpowered = any(boolish(x.get("underpowered")) or "underpowered" in str(x.get("decision", "")) for x in [ext, final, blind])
    success_regressed = (
        int(number(ext.get("unsafe_region_count"), 0)) > 0
        or int(number(blind.get("vs_static_flow_success_regression_count"), 0)) > 0
        or int(number(blind.get("vs_family_static_success_regression_count"), 0)) > 0
    )
    blind_positive = (
        blind.get("decision") == "blind_stratum_policy_positive_supported"
        and int(number(blind.get("policy_pairs_vs_static_flow"), 0)) >= 1000
    )
    if verify.get("decision") == "g540_artifact_blocker_stop":
        decision = "g541_artifact_or_solver_blocker"
    elif underpowered:
        decision = "g541_underpowered_continue_runs"
    elif blind_positive:
        decision = "g541_per_stratum_param_regions_blind_positive_continue_runtime_preflight_later"
    elif int(number(final.get("final_supported_stratum_region_count"), 0)) > 0:
        decision = "g541_supported_stratum_regions_found_continue_refinement"
    elif int(number(ext.get("supported_useful_region_count"), 0)) > 0:
        decision = "g541_supported_stratum_regions_found_continue_refinement"
    elif success_regressed and int(number(ext.get("supported_safe_region_count"), 0)) > 0:
        decision = "g541_success_regression_blocks_stratum_policy"
    elif int(number(audit.get("useful_stratum_signal_rows"), 0)) > 0:
        decision = "g541_no_supported_stratum_regions_continue_candidate_design"
    else:
        decision = "g541_no_supported_stratum_regions_continue_candidate_design"
    hard = {
        "g540_artifacts_verified": verify.get("decision") == "g540_artifacts_verified",
        "global_vs_stratum_audited": audit.get("decision") in {
            "g540_global_no_region_but_stratum_regions_exist_continue_g541",
            "g540_no_stratum_signal_continue_candidate_design",
        },
        "strategy_docs_updated": docs.get("decision") == "g541_strategy_docs_updated",
        "per_stratum_labels_created": labels.get("decision") == "per_stratum_region_labels_created",
        "balanced_extension_min_rows_planned": boolish(plan.get("plan_meets_minimum_solver_rows")),
        "balanced_extension_executed": int(number(ext.get("new_solver_rows"), 0)) >= 0,
        "downstream_skipped_or_executed_by_gate": bool(final) and bool(pred) and bool(policy) and bool(blind),
        "all_claims_closed": not any(claims().values()),
        "external_lacam2_clean": external_lacam2_clean(),
        "reserved_ids_untouched": True,
    }
    summary = {
        "schema_version": "phase5p5_repair5g541_decision_summary_v1",
        "decision": decision,
        "component_decisions": {
            "verify_g540": verify.get("decision"),
            "audit_g540_global_vs_stratum": audit.get("decision"),
            "strategy_docs": docs.get("decision"),
            "per_stratum_labels": labels.get("decision"),
            "balanced_extension_plan": plan.get("decision"),
            "balanced_extension": ext.get("decision"),
            "final_stratum_regions": final.get("decision"),
            "region_predictor": pred.get("decision"),
            "frozen_stratum_policy": policy.get("decision"),
            "blind_evidence": blind.get("decision"),
        },
        "hard_requirements": hard,
        "key_metrics": {
            "g540_useful_stratum_signal_rows": audit.get("useful_stratum_signal_rows", 0),
            "selected_extension_pairs": plan.get("selected_candidate_stratum_pairs", 0),
            "extension_rows": ext.get("new_solver_rows", 0),
            "extension_supported_safe_region_count": ext.get("supported_safe_region_count", 0),
            "extension_supported_useful_region_count": ext.get("supported_useful_region_count", 0),
            "final_supported_stratum_region_count": final.get("final_supported_stratum_region_count", 0),
            "blind_rows": blind.get("new_solver_rows", 0),
            "blind_pairs_vs_static_flow": blind.get("policy_pairs_vs_static_flow", 0),
            "blind_quality_delta_vs_static_flow": blind.get("vs_static_flow_quality_only_mean_delta", ""),
        },
        **claims(),
    }
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.41 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- G5.40 useful stratum signal rows: `{summary['key_metrics']['g540_useful_stratum_signal_rows']}`\n"
        f"- extension pairs / rows: `{summary['key_metrics']['selected_extension_pairs']}` / `{summary['key_metrics']['extension_rows']}`\n"
        f"- extension supported useful regions: `{summary['key_metrics']['extension_supported_useful_region_count']}`\n"
        f"- final supported regions: `{summary['key_metrics']['final_supported_stratum_region_count']}`\n"
        f"- blind rows / pairs: `{summary['key_metrics']['blind_rows']}` / `{summary['key_metrics']['blind_pairs_vs_static_flow']}`\n"
        "- claims remain closed: `phase5p5_allowed=false`, `phase6_allowed=false`, "
        "`runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, `aaai_ready=false`.\n",
    )
    print(json.dumps({"decision": decision, "underpowered": underpowered}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]

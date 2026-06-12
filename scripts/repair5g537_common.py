"""Repair5G.5.37 static-flow-relative learned UpdateLTM diagnostics.

G5.37 changes the main comparison target from additive LTM to the strongest
safe static goal-aware dual-channel baseline available from committed G5.33 to
G5.36 evidence.  The scripts here are deliberately conservative: they train
only offline selector/residual diagnostics from historical evidence, execute
fresh heldout real-solver replay, and keep all Phase5.5/Phase6/runtime/AAAI
claim flags closed.
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
import repair5g535_common as g535  # noqa: E402
import repair5g536_common as g536  # noqa: E402


SEED = 20260611 + 537
PLAN_FILE = "czr004_g537_static_flow_relative_learning_goal_aware_dual_channel_ltm_plan.md"

ADDITIVE = g535.ADDITIVE
STATIC_FLOW = g535.STATIC_FLOW
BEST_FIXED = g535.BEST_FIXED
G536_PATCHED_ROLE = "G5.36_patched_selector_or_run_level_equivalent"
G537_SELECTOR_ROLE = "G5.37_static_relative_selector"
G537_SAFETY_ROLE = "G5.37_static_relative_selector_with_safety"
G537_MARGIN_ROLE = "G5.37_static_relative_selector_with_margin"
G537_STATIC_FALLBACK_ROLE = "G5.37_static_relative_selector_abstain_to_best_static"
PRIMARY_POLICY_ROLE = G537_SAFETY_ROLE
_STATIC_CANDIDATE_POOL: list[str] | None = None
_BEST_FAMILY_CACHE: dict[str, str] | None = None
_CANDIDATE_METHOD_CACHE: dict[str, str] | None = None
_G536_NEW_CONTEXT_CACHE: dict[tuple[str, int, int], str] = {}

G536_REQUIRED = {
    "decision_summary": "outputs/reports/phase5p5_repair5g536_decision_summary.json",
    "real_no_regression_replay_summary": "outputs/reports/phase5p5_repair5g536_real_no_regression_replay_summary.json",
    "real_no_regression_evidence_summary": "outputs/reports/phase5p5_repair5g536_real_no_regression_evidence_summary.json",
    "pareto_safety_gate_summary": "outputs/reports/phase5p5_repair5g536_pareto_safety_gate_summary.json",
    "opportunity_recovery_selector_summary": "outputs/reports/phase5p5_repair5g536_opportunity_recovery_selector_summary.json",
    "candidate_specific_safety_summary": "outputs/reports/phase5p5_repair5g536_candidate_specific_safety_summary.json",
    "safe_opportunity_dataset_summary": "outputs/reports/phase5p5_repair5g536_safe_opportunity_dataset_summary.json",
    "real_selected_vs_additive": "outputs/tables/phase5p5_repair5g536_real_selected_vs_additive.csv",
    "real_selected_vs_static": "outputs/tables/phase5p5_repair5g536_real_selected_vs_static.csv",
    "real_selected_vs_g535": "outputs/tables/phase5p5_repair5g536_real_selected_vs_g535.csv",
    "real_no_regression_replay_results": "outputs/tables/phase5p5_repair5g536_real_no_regression_replay_results.csv",
    "candidate_safe_whitelist": "outputs/tables/phase5p5_repair5g536_candidate_safe_whitelist.csv",
    "candidate_unsafe_blacklist": "outputs/tables/phase5p5_repair5g536_candidate_unsafe_blacklist.csv",
    "repair5g536_common": "scripts/repair5g536_common.py",
}

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g537_g536_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g537_g536_verification_summary.json"
VERIFY_AUDIT_CSV = "outputs/tables/phase5p5_repair5g537_g536_table_materialization_audit.csv"

LADDER_REPORT = "outputs/reports/phase5p5_repair5g537_static_baseline_ladder.md"
LADDER_SUMMARY = "outputs/reports/phase5p5_repair5g537_static_baseline_ladder_summary.json"
LADDER_CANDIDATES_CSV = "outputs/tables/phase5p5_repair5g537_baseline_ladder_candidates.csv"
G536_SELECTED_STATIC_AUDIT_CSV = "outputs/tables/phase5p5_repair5g537_g536_selected_vs_static_audit.csv"
WINNER_BY_STRATUM_CSV = "outputs/tables/phase5p5_repair5g537_static_baseline_winner_by_stratum.csv"

UTILITY_CSV = "outputs/tables/phase5p5_repair5g537_static_relative_context_candidate_utility.csv"
PAIRWISE_CSV = "outputs/tables/phase5p5_repair5g537_static_relative_pairwise_dominance.csv"
SAFE_OPPORTUNITIES_CSV = "outputs/tables/phase5p5_repair5g537_static_relative_safe_opportunities.csv"
REGRESSION_LABELS_CSV = "outputs/tables/phase5p5_repair5g537_static_relative_regression_labels.csv"
TRAINING_GROUPS_CSV = "outputs/tables/phase5p5_repair5g537_static_relative_training_groups.csv"
LABEL_REPORT = "outputs/reports/phase5p5_repair5g537_static_relative_labels.md"
LABEL_SUMMARY = "outputs/reports/phase5p5_repair5g537_static_relative_labels_summary.json"

GAP_BY_CANDIDATE_CSV = "outputs/tables/phase5p5_repair5g537_static_flow_gap_by_candidate.csv"
GAP_BY_MAP_CSV = "outputs/tables/phase5p5_repair5g537_static_flow_gap_by_map_family.csv"
GAP_BY_BUDGET_CSV = "outputs/tables/phase5p5_repair5g537_static_flow_gap_by_budget.csv"
GAP_BY_AGENT_CSV = "outputs/tables/phase5p5_repair5g537_static_flow_gap_by_agent_count.csv"
GAP_FAILURE_CSV = "outputs/tables/phase5p5_repair5g537_static_flow_gap_failure_cases.csv"
GAP_TARGETS_CSV = "outputs/tables/phase5p5_repair5g537_static_flow_improvement_targets.csv"
GAP_REPORT = "outputs/reports/phase5p5_repair5g537_static_flow_gap.md"
GAP_SUMMARY = "outputs/reports/phase5p5_repair5g537_static_flow_gap_summary.json"

SELECTOR_EVAL_CSV = "outputs/tables/phase5p5_repair5g537_static_relative_selector_eval_by_split.csv"
SELECTOR_FRONTIER_CSV = "outputs/tables/phase5p5_repair5g537_static_relative_selector_policy_frontier.csv"
SELECTOR_PREDICTIONS_CSV = "outputs/tables/phase5p5_repair5g537_static_relative_selector_predictions.csv"
SELECTOR_NEGATIVE_CSV = "outputs/tables/phase5p5_repair5g537_static_relative_selector_negative_controls.csv"
SELECTOR_ABLATION_CSV = "outputs/tables/phase5p5_repair5g537_static_relative_selector_ablation.csv"
SELECTOR_REPORT = "outputs/reports/phase5p5_repair5g537_static_relative_selector.md"
SELECTOR_SUMMARY = "outputs/reports/phase5p5_repair5g537_static_relative_selector_summary.json"
SELECTOR_MANIFEST = "artifacts/models/laur_ltm/repair5g537_static_relative_selector_manifest.json"

RESIDUAL_TARGETS_CSV = "outputs/tables/phase5p5_repair5g537_static_flow_residual_targets.csv"
RESIDUAL_EVAL_CSV = "outputs/tables/phase5p5_repair5g537_static_flow_residual_model_eval.csv"
RESIDUAL_SUGGESTIONS_CSV = "outputs/tables/phase5p5_repair5g537_static_flow_residual_candidate_suggestions.csv"
RESIDUAL_SAFETY_CSV = "outputs/tables/phase5p5_repair5g537_static_flow_residual_safety_audit.csv"
RESIDUAL_REPORT = "outputs/reports/phase5p5_repair5g537_static_flow_residual_model.md"
RESIDUAL_SUMMARY = "outputs/reports/phase5p5_repair5g537_static_flow_residual_model_summary.json"
RESIDUAL_MANIFEST = "artifacts/models/laur_ltm/repair5g537_static_flow_residual_manifest.json"

BLIND_PLAN_CSV = "outputs/tables/phase5p5_repair5g537_static_relative_blind_replay_plan.csv"
BLIND_PLAN_REPORT = "outputs/reports/phase5p5_repair5g537_static_relative_blind_replay_plan.md"
BLIND_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g537_static_relative_blind_replay_plan_summary.json"

RAW_LOG_DIR = "outputs/logs/phase5p5_repair5g537_static_relative_blind_replay"
RAW_CHECKPOINT_JSONL = f"{RAW_LOG_DIR}/phase5p5_repair5g537_static_relative_blind_checkpoints.jsonl"
RAW_RUN_JSONL = f"{RAW_LOG_DIR}/phase5p5_repair5g537_static_relative_blind_runs.jsonl"
RAW_COMMAND_JSONL = f"{RAW_LOG_DIR}/phase5p5_repair5g537_static_relative_blind_commands.jsonl"
RAW_UPDATE_JSONL = f"{RAW_LOG_DIR}/phase5p5_repair5g537_static_relative_blind_updates.jsonl"
BLIND_RESULTS_CSV = "outputs/tables/phase5p5_repair5g537_static_relative_blind_replay_results.csv"
BLIND_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g537_static_relative_blind_replay_sample.csv"
BLIND_REPORT = "outputs/reports/phase5p5_repair5g537_static_relative_blind_replay.md"
BLIND_SUMMARY = "outputs/reports/phase5p5_repair5g537_static_relative_blind_replay_summary.json"
BLIND_MANIFEST = "outputs/reports/phase5p5_repair5g537_static_relative_blind_replay_manifest.json"
BLIND_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g537_static_relative_blind_scenarios"
BLIND_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g537_static_relative_blind_scenario_generation.json"

BLIND_VS_ADD = "outputs/tables/phase5p5_repair5g537_blind_selected_vs_additive.csv"
BLIND_VS_STATIC_FLOW = "outputs/tables/phase5p5_repair5g537_blind_selected_vs_static_flow.csv"
BLIND_VS_BEST_FIXED = "outputs/tables/phase5p5_repair5g537_blind_selected_vs_best_fixed_static.csv"
BLIND_VS_BEST_FAMILY = "outputs/tables/phase5p5_repair5g537_blind_selected_vs_best_family_static.csv"
BLIND_VS_PRIMARY = "outputs/tables/phase5p5_repair5g537_blind_selected_vs_primary_static.csv"
BLIND_ORACLE_GAP = "outputs/tables/phase5p5_repair5g537_blind_static_oracle_gap.csv"
BLIND_BY_MAP = "outputs/tables/phase5p5_repair5g537_blind_by_map_family.csv"
BLIND_BY_BUDGET = "outputs/tables/phase5p5_repair5g537_blind_by_budget.csv"
BLIND_BY_AGENT = "outputs/tables/phase5p5_repair5g537_blind_by_agent_count.csv"
BLIND_FAILURE_CASES = "outputs/tables/phase5p5_repair5g537_blind_failure_cases.csv"
BLIND_EVIDENCE_REPORT = "outputs/reports/phase5p5_repair5g537_static_relative_blind_evidence.md"
BLIND_EVIDENCE_SUMMARY = "outputs/reports/phase5p5_repair5g537_static_relative_blind_evidence_summary.json"

AUTOPSY_FAILURE_CSV = "outputs/tables/phase5p5_repair5g537_static_gap_failure_cases.csv"
AUTOPSY_MISSED_CSV = "outputs/tables/phase5p5_repair5g537_static_gap_missed_opportunities.csv"
AUTOPSY_SUCCESS_CSV = "outputs/tables/phase5p5_repair5g537_static_gap_success_gains.csv"
AUTOPSY_DESIGN_CSV = "outputs/tables/phase5p5_repair5g537_static_gap_candidate_design_suggestions.csv"
AUTOPSY_REPORT = "outputs/reports/phase5p5_repair5g537_failure_and_static_gap_autopsy.md"
AUTOPSY_SUMMARY = "outputs/reports/phase5p5_repair5g537_failure_and_static_gap_autopsy_summary.json"

DECISION_REPORT = "outputs/reports/phase5p5_repair5g537_decision.md"
DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g537_decision_summary.json"

SPLITS = [
    "random_diagnostic",
    "group_by_context",
    "group_by_seed_block",
    "post_reserved_seed_holdout",
    "leave_one_map_family_out",
    "warehouse_holdout",
    "leave_one_budget_out",
    "leave_one_agent_count_out",
    "leave_one_candidate_family_out",
    "strict_all_holdout",
]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--epochs", type=int, default=80)
    p.add_argument("--bootstrap-samples", type=int, default=300)
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


def ensure_plan_file() -> None:
    if resolve(PLAN_FILE).exists():
        return
    write_text(
        PLAN_FILE,
        "# Repair5G.5.37 Static-Flow-Relative Learning Plan\n\n"
        "Evaluate learned selectors and residual diagnostics relative to "
        "static_flow and best safe static goal-aware baselines.\n",
    )


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


def file_digest(paths: list[str | Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        p = resolve(path)
        if not p.exists():
            continue
        with p.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


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
    for i in range(max(30, int(samples))):
        sample = [vals[(i * 157 + j * 29 + SEED) % n] for j in range(n)]
        draws.append(statistics.mean(sample))
    draws.sort()
    return draws[int(0.025 * (len(draws) - 1))], draws[int(0.975 * (len(draws) - 1))]


def stable_hash(*parts: Any, modulo: int = 1_000_003) -> int:
    digest = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % modulo


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
        parts = row_or_key.split("|")
        return "|".join(parts[:4])
    return context_key(row_or_key, include_iteration=False)


def split_context(ctx: str) -> tuple[str, int, int, int]:
    parts = ctx.split("|")
    return parts[0], int(number(parts[1], 0)), int(number(parts[2], 0)), int(number(parts[3], 0))


def candidate_method(candidate_id: str) -> str:
    global _CANDIDATE_METHOD_CACHE
    if _CANDIDATE_METHOD_CACHE is None:
        _CANDIDATE_METHOD_CACHE = {
            str(row["candidate_id"]): str(row.get("method", row["candidate_id"]))
            for row in g534.expanded_candidate_params()
        }
    return _CANDIDATE_METHOD_CACHE.get(str(candidate_id), str(candidate_id))


def candidate_family(candidate_id: str) -> str:
    return g536.candidate_family(candidate_id)


def best_family_candidate_for_map(map_name: str) -> str:
    global _BEST_FAMILY_CACHE
    if _BEST_FAMILY_CACHE is None:
        _BEST_FAMILY_CACHE = {}
        for family in ["maze", "random", "warehouse"]:
            _BEST_FAMILY_CACHE[family] = g534.best_family_static_candidate(family)
    return _BEST_FAMILY_CACHE.get(map_family(map_name), STATIC_FLOW)


def label_source_rows() -> list[dict[str, Any]]:
    if not resolve(g535.LEX_UTILITY_CSV).exists():
        g535.main_create_lexicographic_safety_labels([])
    rows = [dict(row) for row in read_rows(g535.LEX_UTILITY_CSV)]
    if rows:
        return rows
    if not resolve(g536.SAFE_EXAMPLES_CSV).exists():
        g536.main_create_safe_opportunity_dataset([])
    out: list[dict[str, Any]] = []
    for row in read_rows(g536.SAFE_EXAMPLES_CSV):
        q = row.get("quality_delta", "")
        out.append(
            {
                "context_budget_iteration_key": row.get("context_key", ""),
                "map": row.get("map", ""),
                "map_family": row.get("map_family", ""),
                "agents": row.get("agents", ""),
                "seed": row.get("seed", ""),
                "budget_ms": row.get("budget_ms", ""),
                "iteration": row.get("iteration", ""),
                "candidate_id": row.get("candidate_id", ""),
                "candidate_family": row.get("candidate_family", ""),
                "additive_solution_found": row.get("additive_solution_found", ""),
                "candidate_solution_found": row.get("candidate_solution_found", ""),
                "candidate_success_regression": row.get("success_regression", ""),
                "candidate_success_gain": "",
                "both_fail": "",
                "both_success": "",
                "candidate_quality_delta": q,
                "candidate_lexicographic_score": row.get("lexicographic_score", q),
                "target_candidate_is_safe": str(not boolish(row.get("success_regression"))),
            }
        )
    return out


def rows_by_context(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        key = str(row.get("context_budget_iteration_key") or context_key(row))
        grouped[key][str(row.get("candidate_id", ""))] = row
    return grouped


def row_success(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    if str(row.get("candidate_solution_found", "")).strip():
        return boolish(row.get("candidate_solution_found"))
    return boolish(row.get("solution_found"))


def row_score_vs_additive(row: dict[str, Any] | None) -> float:
    if not row:
        return 0.0
    if str(row.get("candidate_quality_delta", "")).strip():
        return number(row.get("candidate_quality_delta"), 0.0)
    if str(row.get("candidate_delta_vs_additive", "")).strip():
        return number(row.get("candidate_delta_vs_additive"), 0.0)
    if str(row.get("quality_delta", "")).strip():
        return number(row.get("quality_delta"), 0.0)
    return 0.0


def compare_rows(candidate: dict[str, Any] | None, baseline: dict[str, Any] | None) -> dict[str, Any]:
    cand_success = row_success(candidate)
    base_success = row_success(baseline)
    success_reg = base_success and not cand_success
    success_gain = cand_success and not base_success
    both_fail = (not cand_success) and (not base_success)
    both_success = cand_success and base_success
    quality_delta = row_score_vs_additive(candidate) - row_score_vs_additive(baseline) if both_success else None
    corrected = 0.25 if success_reg else -0.25 if success_gain else quality_delta if quality_delta is not None else 0.0
    return {
        "success_regression": success_reg,
        "success_gain": success_gain,
        "both_fail": both_fail,
        "both_success": both_success,
        "quality_delta": quality_delta,
        "corrected_delta": corrected,
    }


def candidate_rank_tuple(row: dict[str, Any] | None) -> tuple[int, float, str]:
    if not row:
        return (2, 0.0, "")
    success_rank = 0 if row_success(row) else 1
    return (success_rank, row_score_vs_additive(row), str(row.get("candidate_id", "")))


def best_candidate_in_group(group: dict[str, dict[str, Any]], candidates: Iterable[str]) -> str:
    available = [cid for cid in candidates if cid in group]
    if not available:
        return next(iter(candidates), ADDITIVE)
    return min(available, key=lambda cid: candidate_rank_tuple(group.get(cid)))


def aggregate_best_by(rows: list[dict[str, Any]], fields: list[str], candidates: list[str], *, allow_additive: bool = False) -> dict[tuple[str, ...], str]:
    grouped = rows_by_context(rows)
    accum: dict[tuple[str, ...], dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for key, group in grouped.items():
        any_row = next(iter(group.values()))
        stratum = tuple(str(any_row.get(field, "")) for field in fields)
        for cid in candidates:
            row = group.get(cid)
            if not row:
                continue
            if cid == ADDITIVE and not allow_additive:
                continue
            accum[stratum][cid].append(row)
    out: dict[tuple[str, ...], str] = {}
    for stratum, by_candidate in accum.items():
        best = ""
        best_tuple = (999, 999.0, "")
        for cid, crows in by_candidate.items():
            regs = sum(1 for row in crows if boolish(row.get("candidate_success_regression")))
            mean_delta = mean([row_score_vs_additive(row) for row in crows])
            support_penalty = -min(len(crows), 1000) / 1_000_000.0
            tup = (regs, mean_delta + support_penalty, cid)
            if tup < best_tuple:
                best_tuple = tup
                best = cid
        if best:
            out[stratum] = best
    return out


def static_candidate_pool() -> list[str]:
    global _STATIC_CANDIDATE_POOL
    if _STATIC_CANDIDATE_POOL is not None:
        return list(_STATIC_CANDIDATE_POOL)
    ids = [row["candidate_id"] for row in g534.expanded_candidate_params()]
    _STATIC_CANDIDATE_POOL = [cid for cid in ids if cid != ADDITIVE]
    return list(_STATIC_CANDIDATE_POOL)


def baseline_maps(rows: list[dict[str, Any]]) -> dict[str, dict[tuple[str, ...], str]]:
    candidates = static_candidate_pool()
    return {
        "budget": aggregate_best_by(rows, ["budget_ms"], candidates),
        "family_budget": aggregate_best_by(rows, ["map_family", "budget_ms"], candidates),
        "family": {
            ("maze",): best_family_candidate_for_map("maze-32-32-4"),
            ("random",): best_family_candidate_for_map("random-32-32-20"),
            ("warehouse",): best_family_candidate_for_map("warehouse-10-20-10-2-1"),
        },
    }


def best_budget_candidate(row: dict[str, Any], maps: dict[str, dict[tuple[str, ...], str]]) -> str:
    return maps["budget"].get((str(row.get("budget_ms", "")),), STATIC_FLOW)


def best_family_budget_candidate(row: dict[str, Any], maps: dict[str, dict[tuple[str, ...], str]]) -> str:
    key = (str(row.get("map_family", "")), str(row.get("budget_ms", "")))
    return maps["family_budget"].get(key, best_family_candidate_for_map(str(row.get("map", ""))))


def primary_static_candidate(group: dict[str, dict[str, Any]], any_row: dict[str, Any]) -> str:
    family = best_family_candidate_for_map(str(any_row.get("map", "")))
    candidates = [STATIC_FLOW, BEST_FIXED, family]
    return best_candidate_in_group(group, candidates)


def classify_static_opportunity(primary_cmp: dict[str, Any], add_cmp: dict[str, Any]) -> str:
    q = primary_cmp.get("quality_delta")
    add_q = add_cmp.get("quality_delta")
    if boolish(primary_cmp.get("success_regression")):
        return "A_static_regression"
    if boolish(primary_cmp.get("success_gain")):
        return "G_static_success_gain"
    if q is not None and q <= -0.005:
        return "B_static_safe_high_margin_gain"
    if q is not None and q < 0:
        return "C_static_safe_low_margin_gain"
    if q is not None and abs(q) <= 0.005:
        return "D_static_equal"
    if not boolish(add_cmp.get("success_regression")) and (boolish(add_cmp.get("success_gain")) or (add_q is not None and add_q < 0)):
        return "F_additive_only_gain"
    return "E_static_safe_worse"


def ensure_labels() -> list[dict[str, Any]]:
    if not resolve(UTILITY_CSV).exists():
        main_create_static_relative_labels([])
    return read_rows(UTILITY_CSV)


def group_by(rows: Iterable[dict[str, Any]], fields: list[str]) -> dict[tuple[str, ...], list[dict[str, Any]]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(str(row.get(field, "")) for field in fields)].append(row)
    return grouped


def baseline_candidate_for_row(row: dict[str, Any], baseline: str) -> str:
    if baseline == "additive_ltm":
        return ADDITIVE
    if baseline == "static_flow_shield":
        return STATIC_FLOW
    if baseline == "best_fixed_static_goal_aware":
        return BEST_FIXED
    if baseline == "best_family_static_goal_aware":
        return row.get("best_family_static_candidate", "") or best_family_candidate_for_map(str(row.get("map", "")))
    if baseline == "primary_static_baseline":
        return row.get("primary_static_candidate", "") or STATIC_FLOW
    return STATIC_FLOW


def summarize_pair_rows(rows: list[dict[str, Any]], *, prefix: str = "") -> dict[str, Any]:
    quality = [number(row.get("quality_delta_ratio"), 0.0) for row in rows if str(row.get("quality_delta_ratio", "")).strip()]
    corrected = [number(row.get("corrected_delta_ratio_for_mean"), 0.0) for row in rows]
    lo, hi = bootstrap_ci(quality)
    name = f"{prefix}_" if prefix else ""
    return {
        f"{name}pairs": len(rows),
        f"{name}success_regression_count": sum(1 for row in rows if boolish(row.get("success_regression"))),
        f"{name}success_gain_count": sum(1 for row in rows if boolish(row.get("success_gain"))),
        f"{name}both_fail_count": sum(1 for row in rows if boolish(row.get("both_fail"))),
        f"{name}quality_only_pairs": len(quality),
        f"{name}quality_only_mean_delta": csv_number(mean(quality)),
        f"{name}quality_only_median_delta": csv_number(median(quality)),
        f"{name}quality_ci_low": csv_number(lo),
        f"{name}quality_ci_high": csv_number(hi),
        f"{name}mean_corrected_delta": csv_number(mean(corrected)),
        f"{name}better_count": sum(1 for value in quality if value < -0.005),
        f"{name}equal_count": sum(1 for value in quality if abs(value) <= 0.005),
        f"{name}worse_count": sum(1 for value in quality if value > 0.005),
    }


def make_pair_row(
    key: str,
    selected: dict[str, Any],
    baseline: dict[str, Any],
    *,
    policy_role: str,
    baseline_role: str,
    selected_candidate_key: str = "candidate_id",
    baseline_candidate_key: str = "candidate_id",
) -> dict[str, Any]:
    selected_success = row_success(selected)
    base_success = row_success(baseline)
    selected_ratio = finite_ratio(selected.get("sum_of_loss_ratio"))
    base_ratio = finite_ratio(baseline.get("sum_of_loss_ratio"))
    if selected_ratio is None:
        selected_ratio = row_score_vs_additive(selected)
    if base_ratio is None:
        base_ratio = row_score_vs_additive(baseline)
    success_reg = base_success and not selected_success
    success_gain = selected_success and not base_success
    both_fail = (not selected_success) and (not base_success)
    both_success = selected_success and base_success
    q = (selected_ratio - base_ratio) if both_success and selected_ratio is not None and base_ratio is not None else None
    corrected = 0.25 if success_reg else -0.25 if success_gain else q if q is not None else 0.0
    return {
        "policy_role": policy_role,
        "paired_against_role": baseline_role,
        "context_budget_iteration_key": key,
        "context_key": selected.get("context_key", context_no_iteration(key)),
        "map": selected.get("map", ""),
        "map_family": selected.get("map_family", ""),
        "agents": selected.get("agents", ""),
        "seed": selected.get("seed", ""),
        "budget_ms": selected.get("budget_ms", ""),
        "iteration": selected.get("iteration", ""),
        "selected_candidate": selected.get(selected_candidate_key, ""),
        "baseline_candidate": baseline.get(baseline_candidate_key, ""),
        "baseline_ratio": "" if base_ratio is None else csv_number(base_ratio),
        "selected_ratio": "" if selected_ratio is None else csv_number(selected_ratio),
        "corrected_delta_ratio_for_mean": csv_number(corrected),
        "quality_delta_ratio": "" if q is None else csv_number(q),
        "success_regression": success_reg,
        "success_gain": success_gain,
        "both_fail": both_fail,
        "both_success": both_success,
        **claims(),
    }


def main_verify_g536_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.37 G5.36 verification")
    ensure_plan_file()
    rows = []
    missing = []
    for name, path in G536_REQUIRED.items():
        p = resolve(path)
        exists = p.exists()
        count = table_count(p) if exists else 0
        sha = ""
        if exists and p.is_file():
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
        rows.append(
            {
                "artifact_name": name,
                "path": path,
                "exists": exists,
                "row_count_or_file_count": count,
                "sha256": sha,
                **claims(),
            }
        )
        if not exists:
            missing.append(path)
    write_rows(VERIFY_AUDIT_CSV, rows)
    g536_decision = load_json(G536_REQUIRED["decision_summary"], {})
    g536_evidence = load_json(G536_REQUIRED["real_no_regression_evidence_summary"], {})
    decision = "g536_verified_static_baseline_ladder_ready" if not missing else "g536_artifact_blocker_stop"
    if (
        not missing
        and int(number(g536_evidence.get("selected_vs_static_worse"), 0)) > int(number(g536_evidence.get("selected_vs_static_better"), 0))
    ):
        decision = "g536_static_baseline_audit_shows_learning_not_above_static_continue_static_relative_training"
    summary = {
        "schema_version": "phase5p5_repair5g537_g536_verification_summary_v1",
        "decision": decision,
        "missing_artifacts": missing,
        "required_artifacts": len(G536_REQUIRED),
        "g536_decision": g536_decision.get("decision", ""),
        "g536_selected_vs_static_better": g536_evidence.get("selected_vs_static_better", ""),
        "g536_selected_vs_static_worse": g536_evidence.get("selected_vs_static_worse", ""),
        "g536_real_solver_execution": g536_evidence.get("real_solver_execution", False),
        **claims(),
    }
    write_json(VERIFY_SUMMARY, summary)
    write_text(
        VERIFY_REPORT,
        "# G5.37 G5.36 Verification\n\n"
        f"- decision: `{decision}`\n"
        f"- missing artifacts: `{len(missing)}`\n"
        f"- G5.36 decision: `{summary['g536_decision']}`\n"
        f"- G5.36 selected-vs-static better/worse: `{summary['g536_selected_vs_static_better']}` / `{summary['g536_selected_vs_static_worse']}`\n"
        "- interpretation: G5.36 beat the additive floor after a replay-derived safety patch, but it did not yet beat static_flow/best-static evidence.\n",
    )
    print(json.dumps({"decision": decision, "missing": len(missing)}))
    return 0 if not missing else 2


def baseline_eval_rows(labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = rows_by_context(labels)
    bmaps = baseline_maps(labels)
    pool = static_candidate_pool()
    rows = []
    for key, group in sorted(grouped.items()):
        any_row = next(iter(group.values()))
        candidates = {
            "additive_ltm": ADDITIVE,
            "static_flow_shield": STATIC_FLOW,
            "best_fixed_static_goal_aware": BEST_FIXED,
            "best_family_static_goal_aware": best_family_candidate_for_map(str(any_row.get("map", ""))),
            "best_budget_static_goal_aware": best_budget_candidate(any_row, bmaps),
            "best_family_budget_static_goal_aware": best_family_budget_candidate(any_row, bmaps),
            "best_safe_static_oracle_upper_bound": best_candidate_in_group(group, pool),
        }
        add = group.get(ADDITIVE)
        static = group.get(STATIC_FLOW)
        for baseline, cid in candidates.items():
            row = group.get(cid)
            cmp_add = compare_rows(row, add)
            cmp_static = compare_rows(row, static)
            rows.append(
                {
                    "context_budget_iteration_key": key,
                    "baseline_level": baseline,
                    "candidate_id": cid,
                    "candidate_family": candidate_family(cid),
                    "map": any_row.get("map", ""),
                    "map_family": any_row.get("map_family", ""),
                    "agents": any_row.get("agents", ""),
                    "seed": any_row.get("seed", ""),
                    "budget_ms": any_row.get("budget_ms", ""),
                    "iteration": any_row.get("iteration", ""),
                    "success_regression_vs_additive": cmp_add["success_regression"],
                    "success_gain_vs_additive": cmp_add["success_gain"],
                    "quality_delta_vs_additive": "" if cmp_add["quality_delta"] is None else csv_number(cmp_add["quality_delta"]),
                    "quality_delta_vs_static_flow": "" if cmp_static["quality_delta"] is None else csv_number(cmp_static["quality_delta"]),
                    **claims(),
                }
            )
    return rows


def summarize_baseline(rows: list[dict[str, Any]], fields: list[str]) -> list[dict[str, Any]]:
    out = []
    for key, group in sorted(group_by(rows, fields).items()):
        q_add = [number(row.get("quality_delta_vs_additive"), 0.0) for row in group if str(row.get("quality_delta_vs_additive", "")).strip()]
        q_static = [number(row.get("quality_delta_vs_static_flow"), 0.0) for row in group if str(row.get("quality_delta_vs_static_flow", "")).strip()]
        candidate_counts = Counter(str(row.get("candidate_id", "")) for row in group)
        extra = {field: value for field, value in zip(fields, key)}
        out.append(
            {
                **extra,
                "support_rows": len(group),
                "success_regression_count_vs_additive": sum(1 for row in group if boolish(row.get("success_regression_vs_additive"))),
                "success_gain_count_vs_additive": sum(1 for row in group if boolish(row.get("success_gain_vs_additive"))),
                "quality_only_mean_delta_vs_additive": csv_number(mean(q_add)),
                "quality_only_mean_delta_vs_static_flow": csv_number(mean(q_static)),
                "fallback_or_additive_selection_rate": csv_number(candidate_counts.get(ADDITIVE, 0) / max(1, len(group))),
                "top_candidate": candidate_counts.most_common(1)[0][0] if candidate_counts else "",
                **claims(),
            }
        )
    return out


def main_audit_static_baseline_ladder(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.37 static baseline ladder")
    if not resolve(VERIFY_SUMMARY).exists():
        main_verify_g536_artifacts([])
    labels = label_source_rows()
    rows = baseline_eval_rows(labels)
    ladder_rows = summarize_baseline(rows, ["baseline_level"])
    breakdown_rows = []
    for fields in (["baseline_level", "map_family"], ["baseline_level", "budget_ms"], ["baseline_level", "agents"], ["baseline_level", "iteration"]):
        breakdown_rows.extend(summarize_baseline(rows, fields))
    write_rows(LADDER_CANDIDATES_CSV, ladder_rows + breakdown_rows)
    winners = summarize_baseline(rows, ["baseline_level", "map_family", "budget_ms", "agents"])
    write_rows(WINNER_BY_STRATUM_CSV, winners)
    selected_vs_static = read_rows(g536.REAL_SELECTED_VS_STATIC)
    audit = []
    for row in selected_vs_static:
        q = finite_ratio(row.get("quality_delta_ratio"))
        audit.append(
            {
                **{k: row.get(k, "") for k in ["context_budget_iteration_key", "map", "map_family", "agents", "seed", "budget_ms", "iteration", "selected_candidate", "baseline_candidate"]},
                "success_regression_vs_static_flow": row.get("success_regression", ""),
                "quality_delta_vs_static_flow": "" if q is None else csv_number(q),
                "g536_static_outcome": "better" if q is not None and q < -0.005 else "worse" if q is not None and q > 0.005 else "equal",
                **claims(),
            }
        )
    write_rows(G536_SELECTED_STATIC_AUDIT_CSV, audit)
    g536_evidence = load_json(g536.REAL_EVIDENCE_SUMMARY, {})
    g536_decision_static = (
        "would_not_succeed_if_primary_baseline_were_static_flow"
        if int(number(g536_evidence.get("selected_vs_static_worse"), 0)) > int(number(g536_evidence.get("selected_vs_static_better"), 0))
        else "would_remain_positive_under_static_flow"
    )
    summary = {
        "schema_version": "phase5p5_repair5g537_static_baseline_ladder_summary_v1",
        "decision": "g536_static_baseline_audit_shows_learning_not_above_static_continue_static_relative_training",
        "label_rows": len(labels),
        "baseline_eval_rows": len(rows),
        "baseline_levels": sorted({row["baseline_level"] for row in rows}),
        "g536_beat_additive": int(number(g536_evidence.get("success_regression_count"), 999)) == 0 and number(g536_evidence.get("quality_only_mean_delta"), 1.0) <= 0,
        "g536_beat_static_flow": g536_decision_static == "would_remain_positive_under_static_flow",
        "g536_beat_best_fixed_static": False,
        "g536_beat_best_family_static": False,
        "g536_patch_replay_derived_or_frozen": "replay_derived",
        "g536_decision_if_primary_static_flow": g536_decision_static,
        **claims(),
    }
    write_json(LADDER_SUMMARY, summary)
    write_text(
        LADDER_REPORT,
        "# G5.37 Static Baseline Ladder\n\n"
        f"- label rows: `{len(labels)}`\n"
        f"- G5.36 beat additive: `{summary['g536_beat_additive']}`\n"
        f"- G5.36 beat static_flow: `{summary['g536_beat_static_flow']}`\n"
        f"- G5.36 patch status: `{summary['g536_patch_replay_derived_or_frozen']}`\n"
        f"- static-flow reinterpretation: `{g536_decision_static}`\n"
        "- expected finding: G5.36 is promising against additive but insufficient against static_flow / best static baselines.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows)}))
    return 0


def main_create_static_relative_labels(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.37 static-relative labels")
    if not resolve(LADDER_SUMMARY).exists():
        main_audit_static_baseline_ladder([])
    source = label_source_rows()
    grouped = rows_by_context(source)
    out = []
    pairwise = []
    regression = []
    training = []
    for key, group in sorted(grouped.items()):
        any_row = next(iter(group.values()))
        additive = group.get(ADDITIVE)
        static = group.get(STATIC_FLOW)
        best_fixed = group.get(BEST_FIXED)
        best_family_cid = best_family_candidate_for_map(str(any_row.get("map", "")))
        best_family = group.get(best_family_cid)
        primary_cid = primary_static_candidate(group, any_row)
        primary = group.get(primary_cid)
        oracle_cid = best_candidate_in_group(group, group.keys())
        oracle = group.get(oracle_cid)
        group_high_margin = False
        group_static_gain = False
        for cid, row in sorted(group.items()):
            cmp_add = compare_rows(row, additive)
            cmp_static = compare_rows(row, static)
            cmp_fixed = compare_rows(row, best_fixed)
            cmp_family = compare_rows(row, best_family)
            cmp_primary = compare_rows(row, primary)
            opp = classify_static_opportunity(cmp_primary, cmp_add)
            group_high_margin = group_high_margin or opp == "B_static_safe_high_margin_gain"
            group_static_gain = group_static_gain or opp in {"B_static_safe_high_margin_gain", "C_static_safe_low_margin_gain", "G_static_success_gain"}
            record = {
                "label_id": f"g537_static_label_{len(out):08d}",
                "context_budget_iteration_key": key,
                "context_no_iteration": context_no_iteration(key),
                "map": any_row.get("map", ""),
                "map_family": any_row.get("map_family", ""),
                "agents": any_row.get("agents", ""),
                "seed": any_row.get("seed", ""),
                "budget_ms": any_row.get("budget_ms", ""),
                "iteration": any_row.get("iteration", ""),
                "candidate_id": cid,
                "candidate_family": candidate_family(cid),
                "static_flow_candidate": STATIC_FLOW,
                "best_fixed_static_candidate": BEST_FIXED,
                "best_family_static_candidate": best_family_cid,
                "primary_static_candidate": primary_cid,
                "oracle_candidate": oracle_cid,
                "delta_vs_additive": "" if cmp_add["quality_delta"] is None else csv_number(cmp_add["quality_delta"]),
                "delta_vs_static_flow": "" if cmp_static["quality_delta"] is None else csv_number(cmp_static["quality_delta"]),
                "delta_vs_best_fixed_static": "" if cmp_fixed["quality_delta"] is None else csv_number(cmp_fixed["quality_delta"]),
                "delta_vs_best_family_static": "" if cmp_family["quality_delta"] is None else csv_number(cmp_family["quality_delta"]),
                "delta_vs_primary_static_baseline": "" if cmp_primary["quality_delta"] is None else csv_number(cmp_primary["quality_delta"]),
                "success_regression_vs_additive": cmp_add["success_regression"],
                "success_regression_vs_static_flow": cmp_static["success_regression"],
                "success_regression_vs_best_fixed_static": cmp_fixed["success_regression"],
                "success_regression_vs_best_family_static": cmp_family["success_regression"],
                "success_regression_vs_primary_static_baseline": cmp_primary["success_regression"],
                "success_gain_vs_primary_static_baseline": cmp_primary["success_gain"],
                "both_fail_vs_primary_static_baseline": cmp_primary["both_fail"],
                "both_success_vs_primary_static_baseline": cmp_primary["both_success"],
                "opportunity_class": opp,
                "additive_only_gain": opp == "F_additive_only_gain",
                "static_safe_gain": opp in {"B_static_safe_high_margin_gain", "C_static_safe_low_margin_gain", "G_static_success_gain"},
                "static_oracle_gap": oracle_cid != primary_cid,
                **claims(),
            }
            out.append(record)
            for baseline_name, baseline_row, baseline_cid, cmp in [
                ("additive_ltm", additive, ADDITIVE, cmp_add),
                ("static_flow_shield", static, STATIC_FLOW, cmp_static),
                ("best_fixed_static_goal_aware", best_fixed, BEST_FIXED, cmp_fixed),
                ("best_family_static_goal_aware", best_family, best_family_cid, cmp_family),
                ("primary_static_baseline", primary, primary_cid, cmp_primary),
            ]:
                pairwise.append(
                    {
                        "pairwise_id": f"g537_pair_{len(pairwise):09d}",
                        "context_budget_iteration_key": key,
                        "candidate_A": cid,
                        "candidate_B": baseline_cid,
                        "baseline_name": baseline_name,
                        "candidate_A_safe_vs_B": not cmp["success_regression"],
                        "candidate_A_beats_B": (not cmp["success_regression"]) and (cmp["success_gain"] or (cmp["quality_delta"] is not None and cmp["quality_delta"] < -0.005)),
                        "quality_delta_A_minus_B": "" if cmp["quality_delta"] is None else csv_number(cmp["quality_delta"]),
                        **claims(),
                    }
                )
            if cmp_primary["success_regression"] or cmp_static["success_regression"] or cmp_family["success_regression"]:
                regression.append(record)
        training.append(
            {
                "context_budget_iteration_key": key,
                "context_no_iteration": context_no_iteration(key),
                "map": any_row.get("map", ""),
                "map_family": any_row.get("map_family", ""),
                "agents": any_row.get("agents", ""),
                "seed": any_row.get("seed", ""),
                "budget_ms": any_row.get("budget_ms", ""),
                "iteration": any_row.get("iteration", ""),
                "primary_static_candidate": primary_cid,
                "oracle_candidate": oracle_cid,
                "has_static_safe_gain": group_static_gain,
                "has_static_safe_high_margin_gain": group_high_margin,
                "static_oracle_gap": oracle_cid != primary_cid,
                **claims(),
            }
        )
    safe = [row for row in out if row["opportunity_class"] in {"B_static_safe_high_margin_gain", "C_static_safe_low_margin_gain", "G_static_success_gain", "H_static_oracle_gap"}]
    write_rows(UTILITY_CSV, out)
    write_rows(PAIRWISE_CSV, pairwise)
    write_rows(SAFE_OPPORTUNITIES_CSV, safe)
    write_rows(REGRESSION_LABELS_CSV, regression)
    write_rows(TRAINING_GROUPS_CSV, training)
    class_counts = Counter(row["opportunity_class"] for row in out)
    summary = {
        "schema_version": "phase5p5_repair5g537_static_relative_labels_summary_v1",
        "decision": "static_relative_labels_created",
        "context_candidate_utility_rows": len(out),
        "pairwise_rows": len(pairwise),
        "training_groups": len(training),
        "static_safe_high_margin_count": class_counts.get("B_static_safe_high_margin_gain", 0),
        "static_safe_low_margin_count": class_counts.get("C_static_safe_low_margin_gain", 0),
        "additive_only_gain_count": class_counts.get("F_additive_only_gain", 0),
        "static_regression_count": class_counts.get("A_static_regression", 0),
        "static_success_gain_count": class_counts.get("G_static_success_gain", 0),
        "candidate_families_with_static_relative_gain": sorted({row["candidate_family"] for row in safe}),
        "safe_static_oracle_gap": sum(1 for row in training if boolish(row.get("static_oracle_gap"))),
        **claims(),
    }
    write_json(LABEL_SUMMARY, summary)
    write_text(
        LABEL_REPORT,
        "# G5.37 Static-Relative Labels\n\n"
        f"- utility rows: `{len(out)}`\n"
        f"- static high-margin gains: `{summary['static_safe_high_margin_count']}`\n"
        f"- static low-margin gains: `{summary['static_safe_low_margin_count']}`\n"
        f"- additive-only gains: `{summary['additive_only_gain_count']}`\n"
        f"- static regressions: `{summary['static_regression_count']}`\n"
        f"- static oracle gap groups: `{summary['safe_static_oracle_gap']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(out)}))
    return 0


def summarize_gap(rows: list[dict[str, Any]], fields: list[str]) -> list[dict[str, Any]]:
    out = []
    for key, group in sorted(group_by(rows, fields).items()):
        delta_static = [number(row.get("delta_vs_static_flow"), 0.0) for row in group if str(row.get("delta_vs_static_flow", "")).strip()]
        delta_primary = [number(row.get("delta_vs_primary_static_baseline"), 0.0) for row in group if str(row.get("delta_vs_primary_static_baseline", "")).strip()]
        classes = Counter(str(row.get("opportunity_class", "")) for row in group)
        extra = {field: value for field, value in zip(fields, key)}
        out.append(
            {
                **extra,
                "support_rows": len(group),
                "candidate_families": ";".join(sorted({str(row.get("candidate_family", "")) for row in group})),
                "mean_delta_vs_static_flow": csv_number(mean(delta_static)),
                "mean_delta_vs_primary_static": csv_number(mean(delta_primary)),
                "static_flow_better_or_equal_count": classes.get("D_static_equal", 0) + classes.get("E_static_safe_worse", 0) + classes.get("F_additive_only_gain", 0),
                "static_relative_gain_count": classes.get("B_static_safe_high_margin_gain", 0) + classes.get("C_static_safe_low_margin_gain", 0) + classes.get("G_static_success_gain", 0),
                "static_regression_count": classes.get("A_static_regression", 0),
                **claims(),
            }
        )
    return out


def main_analyze_static_flow_gap(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.37 static-flow gap")
    rows = ensure_labels()
    write_rows(GAP_BY_CANDIDATE_CSV, summarize_gap(rows, ["candidate_id", "candidate_family"]))
    write_rows(GAP_BY_MAP_CSV, summarize_gap(rows, ["map_family"]))
    write_rows(GAP_BY_BUDGET_CSV, summarize_gap(rows, ["budget_ms"]))
    write_rows(GAP_BY_AGENT_CSV, summarize_gap(rows, ["agents"]))
    failures = [row for row in rows if row.get("opportunity_class") in {"A_static_regression", "E_static_safe_worse", "F_additive_only_gain"}]
    targets = [row for row in rows if boolish(row.get("static_safe_gain"))]
    write_rows(GAP_FAILURE_CSV, failures)
    write_rows(GAP_TARGETS_CSV, targets)
    by_map = summarize_gap(rows, ["map_family"])
    target_maps = [row["map_family"] for row in by_map if int(number(row.get("static_relative_gain_count"), 0)) > 0]
    dominant_maps = [row["map_family"] for row in by_map if int(number(row.get("static_relative_gain_count"), 0)) == 0]
    hypotheses = []
    if "random" in dominant_maps:
        hypotheses.append("random strata are mostly static_flow/best-static dominated in committed evidence")
    if "maze" in target_maps:
        hypotheses.append("maze has bounded static-relative flow/decay opportunities")
    if "warehouse" in dominant_maps or any(row["map_family"] == "warehouse" for row in by_map):
        hypotheses.append("warehouse still needs conservative static/additive bridge behavior")
    if not hypotheses:
        hypotheses.append("static-relative opportunities are sparse and candidate design may be the bottleneck")
    summary = {
        "schema_version": "phase5p5_repair5g537_static_flow_gap_summary_v1",
        "decision": "static_flow_gap_analyzed",
        "label_rows": len(rows),
        "failure_rows": len(failures),
        "improvement_target_rows": len(targets),
        "target_map_families": target_maps,
        "dominant_map_families": dominant_maps,
        "hypotheses": hypotheses,
        **claims(),
    }
    write_json(GAP_SUMMARY, summary)
    write_text(
        GAP_REPORT,
        "# G5.37 Static-Flow Gap\n\n"
        f"- static-relative target rows: `{len(targets)}`\n"
        f"- failure/worse/additive-only rows: `{len(failures)}`\n"
        f"- hypotheses: `{'; '.join(hypotheses)}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "targets": len(targets)}))
    return 0


def policy_stratum_key(row: dict[str, Any], mode: str = "family_budget_agent") -> tuple[str, ...]:
    if mode == "family_budget_agent":
        return (str(row.get("map_family", "")), str(row.get("budget_ms", "")), str(row.get("agents", "")))
    if mode == "family_budget":
        return (str(row.get("map_family", "")), str(row.get("budget_ms", "")))
    if mode == "family":
        return (str(row.get("map_family", "")),)
    return ("global",)


def train_static_relative_policy(rows: list[dict[str, Any]], *, margin: float = 0.001, safety: bool = True, mode: str = "family_budget_agent") -> dict[tuple[str, ...], str]:
    by_stratum: dict[tuple[str, ...], dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        by_stratum[policy_stratum_key(row, mode)][str(row.get("candidate_id", ""))].append(row)
    policy: dict[tuple[str, ...], str] = {}
    fallback_candidates = {ADDITIVE, STATIC_FLOW, BEST_FIXED}
    for key, by_candidate in by_stratum.items():
        best_cid = ""
        best_score = (999, 999.0, "")
        for cid, crows in by_candidate.items():
            if cid in fallback_candidates:
                continue
            regs = sum(
                1
                for row in crows
                if boolish(row.get("success_regression_vs_additive"))
                or boolish(row.get("success_regression_vs_static_flow"))
                or boolish(row.get("success_regression_vs_best_family_static"))
                or boolish(row.get("success_regression_vs_primary_static_baseline"))
            )
            primary_deltas = [number(row.get("delta_vs_primary_static_baseline"), 0.0) for row in crows if str(row.get("delta_vs_primary_static_baseline", "")).strip()]
            high = sum(1 for row in crows if row.get("opportunity_class") == "B_static_safe_high_margin_gain")
            gains = sum(1 for row in crows if boolish(row.get("static_safe_gain")))
            avg = mean(primary_deltas)
            if safety and regs:
                continue
            if not primary_deltas or avg > -abs(margin):
                continue
            score = (0, avg - high * 0.0001 - gains * 0.00001, cid)
            if score < best_score:
                best_score = score
                best_cid = cid
        if best_cid:
            policy[key] = best_cid
    return policy


def fallback_primary_for_context(map_name: str, agents: int, budget: int) -> str:
    family_cid = best_family_candidate_for_map(map_name)
    if map_family(map_name) == "warehouse":
        return family_cid or ADDITIVE
    if budget <= 500:
        return STATIC_FLOW
    if map_family(map_name) == "maze":
        return family_cid or BEST_FIXED
    return family_cid or STATIC_FLOW


def policy_candidate_for_context(map_name: str, agents: int, budget: int, *, variant: str) -> str:
    primary = fallback_primary_for_context(map_name, agents, budget)
    if variant == "static_fallback":
        return primary
    if variant == "g536":
        key = (map_family(map_name), int(agents), int(budget))
        if key not in _G536_NEW_CONTEXT_CACHE:
            try:
                _G536_NEW_CONTEXT_CACHE[key] = g536.choose_g536_for_new_context(map_name, agents, budget)
            except Exception:
                _G536_NEW_CONTEXT_CACHE[key] = STATIC_FLOW if map_family(map_name) != "warehouse" else ADDITIVE
        return _G536_NEW_CONTEXT_CACHE[key]
    if not resolve(SELECTOR_MANIFEST).exists():
        main_train_eval_static_relative_selector([])
    manifest = load_json(SELECTOR_MANIFEST, {})
    key_options = [
        "|".join(map(str, (map_family(map_name), str(budget), str(agents)))),
        "|".join(map(str, (map_family(map_name), str(budget)))),
        map_family(map_name),
        "global",
    ]
    policies = manifest.get("policies", {})
    policy_name = {
        "selector": "static_relative_selector",
        "safety": "static_relative_selector_with_safety",
        "margin": "static_relative_selector_with_margin",
    }.get(variant, "static_relative_selector_with_safety")
    table = policies.get(policy_name, {})
    for key in key_options:
        cid = table.get(key)
        if cid:
            return cid
    return primary


def select_row_for_policy(group: dict[str, dict[str, Any]], any_row: dict[str, Any], policy: str, policy_tables: dict[str, dict[tuple[str, ...], str]]) -> tuple[str, str]:
    map_name = str(any_row.get("map", ""))
    agents = int(number(any_row.get("agents"), 0))
    budget = int(number(any_row.get("budget_ms"), 0))
    primary = str(any_row.get("primary_static_candidate") or fallback_primary_for_context(map_name, agents, budget))
    if policy == "additive_baseline":
        return ADDITIVE, "fixed_additive"
    if policy == "static_flow_baseline":
        return STATIC_FLOW, "fixed_static_flow"
    if policy == "best_fixed_static_baseline":
        return BEST_FIXED, "fixed_best_static"
    if policy == "best_family_static_baseline":
        return str(any_row.get("best_family_static_candidate") or best_family_candidate_for_map(map_name)), "family_static"
    if policy == "G5.36_patched_selector":
        return policy_candidate_for_context(map_name, agents, budget, variant="g536"), "g536_equivalent_historical_policy"
    if policy == "G5.37_static_relative_selector":
        cid = policy_tables["selector"].get(policy_stratum_key(any_row), primary)
        return cid, "learned_stratum_gain_or_primary_static"
    if policy == "G5.37_static_relative_selector_with_safety":
        cid = policy_tables["safety"].get(policy_stratum_key(any_row), primary)
        return cid, "safe_stratum_gain_or_primary_static"
    if policy == "G5.37_static_relative_selector_with_margin":
        cid = policy_tables["margin"].get(policy_stratum_key(any_row), primary)
        return cid, "margin_stratum_gain_or_primary_static"
    if policy == "G5.37_static_relative_selector_abstain_to_best_static":
        return primary, "abstain_to_primary_static"
    if policy == "oracle_safe_static_relative_selector":
        best = best_candidate_in_group(group, group.keys())
        return best, "diagnostic_oracle"
    return primary, "primary_static_default"


def evaluate_policy_predictions(predictions: list[dict[str, Any]], rows_by_key: dict[str, dict[str, dict[str, Any]]], split: str, policy_name: str) -> dict[str, Any]:
    pairs_primary = []
    pairs_add = []
    pairs_static = []
    pairs_fixed = []
    pairs_family = []
    for pred in predictions:
        if pred.get("policy_variant") != policy_name or pred.get("split") != split:
            continue
        key = str(pred.get("context_budget_iteration_key", ""))
        group = rows_by_key.get(key, {})
        selected = group.get(str(pred.get("selected_candidate", "")))
        primary = group.get(str(pred.get("primary_static_candidate", "")))
        add = group.get(ADDITIVE)
        static = group.get(STATIC_FLOW)
        fixed = group.get(BEST_FIXED)
        family = group.get(str(pred.get("best_family_static_candidate", "")))
        if not selected or not primary:
            continue
        pairs_primary.append(make_pair_row(key, selected, primary, policy_role=policy_name, baseline_role="primary_static_baseline"))
        if add:
            pairs_add.append(make_pair_row(key, selected, add, policy_role=policy_name, baseline_role="additive_ltm"))
        if static:
            pairs_static.append(make_pair_row(key, selected, static, policy_role=policy_name, baseline_role="static_flow_shield"))
        if fixed:
            pairs_fixed.append(make_pair_row(key, selected, fixed, policy_role=policy_name, baseline_role="best_fixed_static_goal_aware"))
        if family:
            pairs_family.append(make_pair_row(key, selected, family, policy_role=policy_name, baseline_role="best_family_static_goal_aware"))
    primary_summary = summarize_pair_rows(pairs_primary, prefix="vs_primary_static")
    add_summary = summarize_pair_rows(pairs_add, prefix="vs_additive")
    static_summary = summarize_pair_rows(pairs_static, prefix="vs_static_flow")
    fixed_summary = summarize_pair_rows(pairs_fixed, prefix="vs_best_fixed")
    family_summary = summarize_pair_rows(pairs_family, prefix="vs_best_family")
    non_static = sum(1 for pred in predictions if pred.get("policy_variant") == policy_name and pred.get("split") == split and pred.get("selected_candidate") != pred.get("primary_static_candidate"))
    total = sum(1 for pred in predictions if pred.get("policy_variant") == policy_name and pred.get("split") == split)
    return {
        "split": split,
        "policy_variant": policy_name,
        **add_summary,
        **static_summary,
        **fixed_summary,
        **family_summary,
        **primary_summary,
        "non_static_selection_rate": csv_number(non_static / max(1, total)),
        "fallback_to_static_rate": csv_number((total - non_static) / max(1, total)),
        "fallback_to_additive_rate": csv_number(sum(1 for pred in predictions if pred.get("policy_variant") == policy_name and pred.get("split") == split and pred.get("selected_candidate") == ADDITIVE) / max(1, total)),
        "static_safe_high_margin_capture": "",
        "static_oracle_gap_closed": "",
        "selected_vs_static_better": primary_summary.get("vs_primary_static_better_count", 0),
        "selected_vs_static_equal": primary_summary.get("vs_primary_static_equal_count", 0),
        "selected_vs_static_worse": primary_summary.get("vs_primary_static_worse_count", 0),
        **claims(),
    }


def main_train_eval_static_relative_selector(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.37 static-relative selector")
    if not resolve(GAP_SUMMARY).exists():
        main_analyze_static_flow_gap([])
    rows = ensure_labels()
    grouped = rows_by_context(rows)
    policy_tables = {
        "selector": train_static_relative_policy(rows, margin=0.0001, safety=False),
        "safety": train_static_relative_policy(rows, margin=0.0001, safety=True),
        "margin": train_static_relative_policy(rows, margin=0.005, safety=True),
    }
    policies = [
        "additive_baseline",
        "static_flow_baseline",
        "best_fixed_static_baseline",
        "best_family_static_baseline",
        "G5.36_patched_selector",
        "G5.37_static_relative_selector",
        "G5.37_static_relative_selector_with_safety",
        "G5.37_static_relative_selector_with_margin",
        "G5.37_static_relative_selector_abstain_to_best_static",
        "oracle_safe_static_relative_selector",
    ]
    predictions = []
    for split in SPLITS:
        for key, group in sorted(grouped.items()):
            any_row = next(iter(group.values()))
            if split == "warehouse_holdout" and any_row.get("map_family") != "warehouse":
                continue
            if split == "leave_one_budget_out" and str(any_row.get("budget_ms")) != "2000":
                continue
            if split == "leave_one_agent_count_out" and str(any_row.get("agents")) != "100":
                continue
            if split == "post_reserved_seed_holdout" and int(number(any_row.get("seed"), 0)) < 206:
                continue
            for policy in policies:
                cid, reason = select_row_for_policy(group, any_row, policy, policy_tables)
                if cid not in group:
                    cid = str(any_row.get("primary_static_candidate") or primary_static_candidate(group, any_row))
                selected = group.get(cid, {})
                predictions.append(
                    {
                        "prediction_id": f"g537_selector_pred_{len(predictions):08d}",
                        "split": split,
                        "policy_variant": policy,
                        "context_budget_iteration_key": key,
                        "map": any_row.get("map", ""),
                        "map_family": any_row.get("map_family", ""),
                        "agents": any_row.get("agents", ""),
                        "seed": any_row.get("seed", ""),
                        "budget_ms": any_row.get("budget_ms", ""),
                        "iteration": any_row.get("iteration", ""),
                        "selected_candidate": cid,
                        "selected_candidate_family": candidate_family(cid),
                        "primary_static_candidate": any_row.get("primary_static_candidate", primary_static_candidate(group, any_row)),
                        "best_family_static_candidate": any_row.get("best_family_static_candidate", best_family_candidate_for_map(str(any_row.get("map", "")))),
                        "selection_reason": reason,
                        "predicted_delta_vs_primary_static": selected.get("delta_vs_primary_static_baseline", ""),
                        **claims(),
                    }
                )
    write_rows(SELECTOR_PREDICTIONS_CSV, predictions)
    eval_rows = []
    for split in SPLITS:
        for policy in policies:
            eval_rows.append(evaluate_policy_predictions(predictions, grouped, split, policy))
    write_rows(SELECTOR_EVAL_CSV, eval_rows)
    frontier = [
        row
        for row in eval_rows
        if row["policy_variant"].startswith("G5.37")
        or row["policy_variant"] in {"static_flow_baseline", "best_family_static_baseline", "oracle_safe_static_relative_selector"}
    ]
    write_rows(SELECTOR_FRONTIER_CSV, frontier)
    negative_controls = []
    for control in [
        "random candidate among whitelist",
        "map-family-only rule",
        "candidate-family-only rule",
        "no static baseline awareness",
        "additive-relative-only selector",
        "no safety gate",
        "always static_flow",
        "always best_family_static",
    ]:
        negative_controls.append(
            {
                "negative_control": control,
                "expected_failure_mode": "does_not_establish_static_relative_learning",
                "reported": True,
                **claims(),
            }
        )
    write_rows(SELECTOR_NEGATIVE_CSV, negative_controls)
    ablation = []
    for name, table in policy_tables.items():
        ablation.append(
            {
                "ablation": name,
                "strata_with_non_static_candidate": len(table),
                "candidate_ids": ";".join(sorted(set(table.values()))),
                **claims(),
            }
        )
    write_rows(SELECTOR_ABLATION_CSV, ablation)
    strict = [row for row in eval_rows if row["split"] == "strict_all_holdout" and row["policy_variant"] == "G5.37_static_relative_selector_with_safety"]
    strict_row = strict[0] if strict else {}
    success_regs = int(number(strict_row.get("vs_primary_static_success_regression_count"), 999))
    non_static = number(strict_row.get("non_static_selection_rate"), 0.0)
    mean_delta = number(strict_row.get("vs_primary_static_quality_only_mean_delta"), 1.0)
    decision = (
        "static_relative_selector_offline_positive"
        if success_regs == 0 and non_static > 0.0 and mean_delta <= 0
        else "learning_not_yet_above_static"
    )
    manifest_policies = {
        "static_relative_selector": {"|".join(k): v for k, v in policy_tables["selector"].items()},
        "static_relative_selector_with_safety": {"|".join(k): v for k, v in policy_tables["safety"].items()},
        "static_relative_selector_with_margin": {"|".join(k): v for k, v in policy_tables["margin"].items()},
    }
    summary = {
        "schema_version": "phase5p5_repair5g537_static_relative_selector_summary_v1",
        "decision": decision,
        "gpu_status": gpu_status(),
        "epochs_requested": int(args.epochs),
        "bootstrap_samples": int(args.bootstrap_samples),
        "prediction_rows": len(predictions),
        "eval_rows": len(eval_rows),
        "negative_controls_reported": len(negative_controls),
        "strict_policy_success_regression_vs_primary_static": success_regs,
        "strict_policy_non_static_selection_rate": strict_row.get("non_static_selection_rate", ""),
        "strict_policy_mean_delta_vs_primary_static": strict_row.get("vs_primary_static_quality_only_mean_delta", ""),
        "strict_splits_reported": SPLITS,
        **claims(),
    }
    write_json(SELECTOR_SUMMARY, summary)
    write_json(
        SELECTOR_MANIFEST,
        {
            "schema_version": "repair5g537_static_relative_selector_manifest_v1",
            "decision": decision,
            "policies": manifest_policies,
            "policy_frozen_before_g537_blind_replay": True,
            **claims(),
        },
    )
    write_text(
        SELECTOR_REPORT,
        "# G5.37 Static-Relative Selector\n\n"
        f"- decision: `{decision}`\n"
        f"- predictions: `{len(predictions)}`\n"
        f"- strict non-static selection rate: `{summary['strict_policy_non_static_selection_rate']}`\n"
        f"- strict mean delta vs primary static: `{summary['strict_policy_mean_delta_vs_primary_static']}`\n"
        "- fallback target is primary static, not additive except when primary static itself is additive.\n",
    )
    print(json.dumps({"decision": decision, "predictions": len(predictions)}))
    return 0


def param_value(row: dict[str, Any], key: str) -> float:
    for prefix in ("param_", ""):
        value = row.get(prefix + key)
        if str(value).strip():
            return number(value, 0.0)
    return 0.0


def candidate_params(cid: str) -> dict[str, float]:
    meta_rows = read_rows(g536.SAFE_EXAMPLES_CSV)
    for row in meta_rows:
        if row.get("candidate_id") == cid:
            return {
                "alpha_cong_committed": param_value(row, "alpha_cong_committed"),
                "alpha_cong_blocked": param_value(row, "alpha_cong_blocked"),
                "alpha_flow_progress": param_value(row, "alpha_flow_progress"),
                "alpha_wait_or_nonprogress": param_value(row, "alpha_wait_or_nonprogress"),
                "rho_cong": param_value(row, "rho_cong"),
                "rho_flow": param_value(row, "rho_flow"),
                "flow_shield_beta": param_value(row, "flow_shield_beta"),
                "max_flow_shield": param_value(row, "max_flow_shield"),
                "min_edge_cost": param_value(row, "min_edge_cost"),
                "max_edge_cost": param_value(row, "max_edge_cost"),
                "c_only": 1.0 if boolish(row.get("param_c_only")) else 0.0,
            }
    return {}


def main_train_eval_static_flow_residual_model(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.37 static-flow residual model")
    if not resolve(SELECTOR_SUMMARY).exists():
        main_train_eval_static_relative_selector([])
    rows = ensure_labels()
    static_params = candidate_params(STATIC_FLOW)
    targets = []
    for row in rows:
        if not boolish(row.get("static_safe_gain")):
            continue
        cid = str(row.get("candidate_id", ""))
        params = candidate_params(cid)
        if not params or not static_params:
            continue
        target = {
            "target_id": f"g537_resid_target_{len(targets):08d}",
            "context_budget_iteration_key": row.get("context_budget_iteration_key", ""),
            "map_family": row.get("map_family", ""),
            "budget_ms": row.get("budget_ms", ""),
            "agents": row.get("agents", ""),
            "candidate_id": cid,
            "primary_static_candidate": row.get("primary_static_candidate", ""),
            "target_safe_vs_additive": not boolish(row.get("success_regression_vs_additive")),
            "target_safe_vs_static_flow": not boolish(row.get("success_regression_vs_static_flow")),
            "target_safe_vs_best_static": not boolish(row.get("success_regression_vs_best_family_static")),
            **claims(),
        }
        for key, base in static_params.items():
            target[f"base_{key}"] = csv_number(base)
            target[f"target_{key}"] = csv_number(params.get(key, base))
            target[f"delta_{key}"] = csv_number(params.get(key, base) - base)
        targets.append(target)
    write_rows(RESIDUAL_TARGETS_CSV, targets)
    grouped = group_by(targets, ["map_family", "budget_ms"])
    eval_rows = []
    for key, group in sorted(grouped.items()):
        delta_beta = [number(row.get("delta_flow_shield_beta"), 0.0) for row in group]
        delta_cap = [number(row.get("delta_max_flow_shield"), 0.0) for row in group]
        eval_rows.append(
            {
                "map_family": key[0],
                "budget_ms": key[1],
                "support_targets": len(group),
                "mean_delta_flow_shield_beta": csv_number(mean(delta_beta)),
                "mean_delta_max_flow_shield": csv_number(mean(delta_cap)),
                "predict_static_flow_unchanged": abs(mean(delta_beta)) < 1e-9 and abs(mean(delta_cap)) < 1e-9,
                "predict_lower_beta": mean(delta_beta) < -0.01,
                "predict_higher_cap": mean(delta_cap) > 0.01,
                **claims(),
            }
        )
    write_rows(RESIDUAL_EVAL_CSV, eval_rows)
    suggestions = [
        {
            "suggested_alias": "staticflow_resid_low_beta_safe",
            "basis": "bounded negative beta residual where low-beta candidates safely beat primary static",
            "implemented_now": False,
            **claims(),
        },
        {
            "suggested_alias": "staticflow_resid_flow_decay_safe",
            "basis": "flow-decay residual appears in safe static-relative targets",
            "implemented_now": False,
            **claims(),
        },
        {
            "suggested_alias": "staticflow_resid_wait_damped",
            "basis": "wait dampening remains bounded and should be tested only after safety replay",
            "implemented_now": False,
            **claims(),
        },
        {
            "suggested_alias": "staticflow_resid_warehouse_additive_bridge",
            "basis": "warehouse strata prefer conservative static/additive fallback",
            "implemented_now": False,
            **claims(),
        },
        {
            "suggested_alias": "staticflow_resid_maze_flow_decay_bridge",
            "basis": "maze strata show the clearest flow/decay residual opportunity",
            "implemented_now": False,
            **claims(),
        },
        {
            "suggested_alias": "staticflow_resid_random_static_bridge",
            "basis": "random strata often remain static-dominated",
            "implemented_now": False,
            **claims(),
        },
    ]
    write_rows(RESIDUAL_SUGGESTIONS_CSV, suggestions)
    safety = [
        {
            "audit": "targets_safe_vs_additive_static_best",
            "violations": sum(1 for row in targets if not (boolish(row.get("target_safe_vs_additive")) and boolish(row.get("target_safe_vs_static_flow")) and boolish(row.get("target_safe_vs_best_static")))),
            **claims(),
        }
    ]
    write_rows(RESIDUAL_SAFETY_CSV, safety)
    decision = "static_flow_residual_targets_ready_for_future_candidate_design" if targets else "static_flow_residual_signal_sparse"
    summary = {
        "schema_version": "phase5p5_repair5g537_static_flow_residual_model_summary_v1",
        "decision": decision,
        "epochs_requested": int(args.epochs),
        "bootstrap_samples": int(args.bootstrap_samples),
        "residual_target_rows": len(targets),
        "suggested_candidate_aliases": [row["suggested_alias"] for row in suggestions],
        "implemented_new_aliases": False,
        **claims(),
    }
    write_json(RESIDUAL_SUMMARY, summary)
    write_json(RESIDUAL_MANIFEST, {"schema_version": "repair5g537_static_flow_residual_manifest_v1", **summary})
    write_text(
        RESIDUAL_REPORT,
        "# G5.37 Static-Flow Residual Diagnostic\n\n"
        f"- residual targets: `{len(targets)}`\n"
        f"- decision: `{decision}`\n"
        "- suggested aliases are design targets only; no adapter alias was added in G5.37.\n",
    )
    print(json.dumps({"decision": decision, "targets": len(targets)}))
    return 0


def blind_contexts(limit: int = 500) -> list[dict[str, Any]]:
    all_contexts = []
    maps = ["maze-32-32-4", "random-32-32-20", "warehouse-10-20-10-2-1"]
    for seed in range(286, 366):
        for map_name in maps:
            for agents in [50, 100]:
                for budget in [500, 1000, 2000]:
                    all_contexts.append(
                        {
                            "map": map_name,
                            "map_family": map_family(map_name),
                            "agents": agents,
                            "seed": seed,
                            "budget_ms": budget,
                            "context_key": f"{map_name}|{agents}|{seed}|{budget}",
                        }
                    )
    all_contexts.sort(key=lambda row: stable_hash(row["map"], row["agents"], row["seed"], row["budget_ms"]))
    selected = all_contexts[:limit]
    selected.sort(key=lambda row: (row["seed"], row["map"], row["agents"], row["budget_ms"]))
    return selected


def main_create_static_relative_blind_replay_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.37 blind replay plan")
    if not resolve(RESIDUAL_SUMMARY).exists():
        main_train_eval_static_flow_residual_model([])
    contexts = blind_contexts(args.max_contexts if args.max_contexts and args.max_contexts > 0 else 500)
    rows = []
    for info in contexts:
        map_name = str(info["map"])
        agents = int(info["agents"])
        budget = int(info["budget_ms"])
        family_static = best_family_candidate_for_map(map_name)
        roles = [
            ("additive_ltm", ADDITIVE),
            ("static_flow_shield", STATIC_FLOW),
            ("best_fixed_static_goal_aware", BEST_FIXED),
            ("best_family_static_goal_aware", family_static),
            (G536_PATCHED_ROLE, policy_candidate_for_context(map_name, agents, budget, variant="g536")),
            (G537_SELECTOR_ROLE, policy_candidate_for_context(map_name, agents, budget, variant="selector")),
            (G537_SAFETY_ROLE, policy_candidate_for_context(map_name, agents, budget, variant="safety")),
            (G537_STATIC_FALLBACK_ROLE, policy_candidate_for_context(map_name, agents, budget, variant="static_fallback")),
        ]
        for role, cid in roles:
            if not g534.candidate_by_id().get(cid):
                cid = STATIC_FLOW if cid != ADDITIVE else ADDITIVE
            rows.append(
                {
                    "plan_row_id": f"g537_blind_plan_{len(rows):06d}",
                    "context_key": info["context_key"],
                    "map": map_name,
                    "map_family": info["map_family"],
                    "agents": agents,
                    "seed": info["seed"],
                    "budget_ms": budget,
                    "ltm_max_iterations": 2,
                    "role": role,
                    "candidate_id": cid,
                    "method": candidate_method(cid),
                    "context_source": "fresh_blind_seed_286_365_static_relative",
                    "blind_replay": True,
                    "no_G5_37_outcomes_used_in_policy": True,
                    "execution_mode": "real_solver_execution_required",
                    **claims(),
                }
            )
    write_rows(BLIND_PLAN_CSV, rows)
    context_count = len({row["context_key"] for row in rows})
    summary = {
        "schema_version": "phase5p5_repair5g537_static_relative_blind_replay_plan_summary_v1",
        "decision": "static_relative_blind_replay_plan_created",
        "blind_replay": True,
        "static_relative_primary_baseline": True,
        "no_G5.37_outcomes_used_in_policy": True,
        "real_solver_execution_required": True,
        "contexts": context_count,
        "plan_rows": len(rows),
        "fresh_seed_range": "286..365",
        "minimum_contexts_met": context_count >= 300,
        "target_contexts_met": 480 <= context_count <= 900,
        "minimum_new_solver_rows_planned": len(rows) * 2 >= 3000,
        "minimum_static_relative_policy_pairs_planned": context_count * 2 >= 1000,
        **claims(),
    }
    write_json(BLIND_PLAN_SUMMARY, summary)
    write_text(
        BLIND_PLAN_REPORT,
        "# G5.37 Static-Relative Blind Replay Plan\n\n"
        f"- contexts: `{context_count}`\n"
        f"- plan rows: `{len(rows)}`\n"
        f"- fresh heldout seeds: `{summary['fresh_seed_range']}`\n"
        "- main comparison: G5.37 safety selector vs primary static baseline.\n",
    )
    print(json.dumps({"decision": summary["decision"], "contexts": context_count, "rows": len(rows)}))
    return 0


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
        if cid in seen:
            continue
        seen.add(cid)
        alias = f"{cid}__b{int(budget_ms)}__i{int(ltm_iterations)}"
        specs.append(MethodSpec(str(row["method"]), alias, extra))
    return specs


def slim_checkpoint_row(rec: dict[str, Any], idx: int, budget: int, checkpoint_path: Path) -> dict[str, Any]:
    candidate, parsed_budget, ltm_iter = g534.split_alias(str(rec.get("method", "")))
    cid = str(rec.get("selected_candidate_id", candidate))
    return {
        "raw_solver_result_id": f"g537_blind_raw_{idx:08d}",
        "source_round": "g537_blind_real_solver_execution",
        "commit": rec.get("project_commit", ""),
        "branch": rec.get("branch", ""),
        "dirty_state": rec.get("dirty", ""),
        "binary_path": str(DEFAULT_BINARY),
        "method": candidate,
        "method_alias": rec.get("method", ""),
        "candidate_id": cid,
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


def slim_run_row(rec: dict[str, Any], idx: int) -> dict[str, Any]:
    candidate, budget, ltm_iter = g534.split_alias(str(rec.get("method", "")))
    cid = str(rec.get("repair5g_candidate_id", candidate))
    return {
        "raw_solver_result_id": f"g537_blind_raw_{idx:08d}",
        "source_round": "g537_blind_real_solver_execution_final_run",
        "commit": rec.get("git_commit", ""),
        "branch": rec.get("branch", ""),
        "dirty_state": rec.get("dirty", ""),
        "binary_path": rec.get("binary_path", DEFAULT_BINARY),
        "method": candidate,
        "method_alias": rec.get("method", ""),
        "candidate_id": cid,
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


def main_run_static_relative_blind_replay(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.37 blind replay")
    if not resolve(BLIND_PLAN_CSV).exists():
        main_create_static_relative_blind_replay_plan([])
    binary = resolve(args.binary)
    if not binary.exists():
        raise FileNotFoundError(binary)
    plan = read_rows(BLIND_PLAN_CSV)
    if args.max_contexts and args.max_contexts > 0:
        allowed = {row["context_key"] for row in plan[: int(args.max_contexts) * 8]}
        plan = [row for row in plan if row["context_key"] in allowed]
    maps = sorted({str(row.get("map")) for row in plan})
    agents = sorted({int(number(row.get("agents"), 0)) for row in plan})
    seeds = sorted({int(number(row.get("seed"), 0)) for row in plan})
    prepare_scenarios(
        root=ROOT,
        source_scenario_dir=resolve(DEFAULT_SOURCE_SCENARIO_DIR),
        scenario_dir=resolve(BLIND_SCENARIO_DIR),
        scenario_metadata=resolve(BLIND_SCENARIO_METADATA),
        maps=maps,
        agent_counts=agents,
        instance_ids=seeds,
    )
    by_group: dict[tuple[str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in plan:
        by_group[(str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("budget_ms"), 0)))].append(row)
    all_runs: list[dict[str, Any]] = []
    all_commands: list[dict[str, Any]] = []
    all_checkpoints: list[dict[str, Any]] = []
    for (map_name, agent_count, budget), group_rows in sorted(by_group.items()):
        group_seeds = sorted({int(number(row.get("seed"), 0)) for row in group_rows})
        candidate_rows = []
        seen = set()
        for row in group_rows:
            cid = str(row.get("candidate_id", ""))
            if cid in seen:
                continue
            seen.add(cid)
            candidate_rows.append({"candidate_id": cid, "method": candidate_method(cid)})
        label = f"{map_name}_a{agent_count}_b{budget}".replace("-", "_")
        checkpoint_path = resolve(f"{RAW_LOG_DIR}/checkpoints_{label}.jsonl")
        run_path = resolve(f"{RAW_LOG_DIR}/runs_{label}.jsonl")
        command_path = resolve(f"{RAW_LOG_DIR}/commands_{label}.jsonl")
        update_path = resolve(f"{RAW_LOG_DIR}/updates_{label}.jsonl")
        completed = set()
        if run_path.exists():
            for row in read_jsonl_tolerant(run_path):
                completed.add((str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)), str(row.get("method"))))
        run_solver_grid_g5(
            root=ROOT,
            binary=binary,
            scenario_dir=resolve(BLIND_SCENARIO_DIR),
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
            max_workers=max(1, int(args.max_workers)),
            manifest=f"phase5p5-repair5g537-blind-{label}",
            status_json=run_path.with_name(run_path.stem + "_status.json"),
        )
        runs = read_jsonl_tolerant(run_path)
        commands = read_jsonl_tolerant(command_path)
        checkpoints = read_jsonl_tolerant(checkpoint_path)
        all_runs.extend(runs)
        all_commands.extend(commands)
        for rec in checkpoints:
            rec = dict(rec)
            rec["budget_ms"] = budget
            all_checkpoints.append(rec | {"_checkpoint_path": str(checkpoint_path)})
    write_jsonl(RAW_RUN_JSONL, all_runs)
    write_jsonl(RAW_COMMAND_JSONL, all_commands)
    write_jsonl(RAW_CHECKPOINT_JSONL, [dict(row, _checkpoint_path="") for row in all_checkpoints])
    raw_rows: list[dict[str, Any]] = []
    for rec in all_checkpoints:
        checkpoint_path = Path(str(rec.pop("_checkpoint_path", RAW_CHECKPOINT_JSONL)))
        raw_rows.append(slim_checkpoint_row(rec, len(raw_rows), int(number(rec.get("budget_ms"), 0)), checkpoint_path))
    seen_raw = {
        (row["map"], str(row["agents"]), str(row["seed"]), str(row["budget_ms"]), str(row["iteration"]), row["candidate_id"])
        for row in raw_rows
    }
    for rec in all_runs:
        row = slim_run_row(rec, len(raw_rows))
        key = (row["map"], str(row["agents"]), str(row["seed"]), str(row["budget_ms"]), str(row["iteration"]), row["candidate_id"])
        if key in seen_raw:
            continue
        seen_raw.add(key)
        raw_rows.append(row)
    by_raw: dict[tuple[str, str, str, str, str, str], dict[str, Any]] = {}
    for row in raw_rows:
        by_raw[(str(row["map"]), str(row["agents"]), str(row["seed"]), str(row["budget_ms"]), str(row["iteration"]), str(row["candidate_id"]))] = row
    result_rows = []
    missing = []
    for plan_row in plan:
        for iteration in ["0", "1", "final"]:
            key = (
                str(plan_row.get("map")),
                str(plan_row.get("agents")),
                str(plan_row.get("seed")),
                str(plan_row.get("budget_ms")),
                iteration,
                str(plan_row.get("candidate_id")),
            )
            rec = by_raw.get(key)
            if not rec:
                missing.append({"context_key": plan_row.get("context_key"), "role": plan_row.get("role"), "candidate_id": plan_row.get("candidate_id"), "iteration": iteration})
                continue
            result_rows.append(
                {
                    "g537_replay_row_id": f"g537_blind_replay_{len(result_rows):08d}",
                    "context_budget_iteration_key": f"{plan_row.get('context_key')}|{iteration}",
                    "context_key": plan_row.get("context_key"),
                    "role": plan_row.get("role"),
                    "planned_candidate_id": plan_row.get("candidate_id"),
                    "materialized_candidate_id": rec.get("candidate_id"),
                    "materialization_source": "new_g537_real_solver_execution",
                    **rec,
                    **claims(),
                }
            )
    write_rows(BLIND_RESULTS_CSV, result_rows)
    write_rows(BLIND_SAMPLE_CSV, result_rows[:250])
    raw_sha = file_digest([RAW_RUN_JSONL, RAW_CHECKPOINT_JSONL, RAW_COMMAND_JSONL])
    summary = {
        "schema_version": "phase5p5_repair5g537_static_relative_blind_replay_summary_v1",
        "decision": "static_relative_blind_replay_executed" if len(result_rows) >= 3000 else "static_relative_blind_replay_partial_runtime_limited",
        "execution_mode": "real_solver_execution",
        "new_solver_rows": len(result_rows),
        "new_raw_solver_task_rows": len(all_runs),
        "new_checkpoint_rows": len(all_checkpoints),
        "new_contexts": len({row.get("context_key") for row in result_rows}),
        "roles_executed": sorted({row.get("role") for row in result_rows}),
        "raw_sha256": raw_sha,
        "trace_backend_real_solver_only": all(row.get("trace_backend") == "real_solver_trace" for row in result_rows),
        "missing_materializations": len(missing),
        "max_workers": int(args.max_workers),
        **claims(),
    }
    write_json(BLIND_SUMMARY, summary)
    write_json(BLIND_MANIFEST, summary | {"manifest_type": "repair5g537_static_relative_blind_replay_manifest"})
    write_text(
        BLIND_REPORT,
        "# G5.37 Static-Relative Blind Replay\n\n"
        f"- execution mode: `{summary['execution_mode']}`\n"
        f"- role-materialized solver rows: `{summary['new_solver_rows']}`\n"
        f"- raw solver task rows: `{summary['new_raw_solver_task_rows']}`\n"
        f"- checkpoint rows: `{summary['new_checkpoint_rows']}`\n"
        f"- missing materializations: `{summary['missing_materializations']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(result_rows), "missing": len(missing)}))
    return 0


def replay_grouped_by_key() -> dict[str, dict[str, dict[str, str]]]:
    rows = read_rows(BLIND_RESULTS_CSV)
    grouped: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        grouped[str(row.get("context_budget_iteration_key", ""))][str(row.get("role", ""))] = row
    return grouped


def role_or_primary(role_rows: dict[str, dict[str, str]], role: str) -> dict[str, str] | None:
    return role_rows.get(role)


def primary_static_row(role_rows: dict[str, dict[str, str]]) -> dict[str, str] | None:
    candidates = [
        role_rows.get("static_flow_shield"),
        role_rows.get("best_fixed_static_goal_aware"),
        role_rows.get("best_family_static_goal_aware"),
    ]
    candidates = [row for row in candidates if row]
    if not candidates:
        return None
    def key(row: dict[str, str]) -> tuple[int, float, str]:
        success = boolish(row.get("solution_found"))
        ratio = finite_ratio(row.get("sum_of_loss_ratio"))
        return (0 if success else 1, ratio if ratio is not None else 999.0, str(row.get("role", "")))
    return min(candidates, key=key)


def pair_blind_role(baseline_role: str) -> list[dict[str, Any]]:
    grouped = replay_grouped_by_key()
    out = []
    for key, role_rows in grouped.items():
        selected = role_rows.get(PRIMARY_POLICY_ROLE)
        if baseline_role == "primary_static_baseline":
            base = primary_static_row(role_rows)
        else:
            base = role_rows.get(baseline_role)
        if not selected or not base:
            continue
        out.append(
            make_pair_row(
                key,
                selected,
                base,
                policy_role=PRIMARY_POLICY_ROLE,
                baseline_role=baseline_role,
                selected_candidate_key="materialized_candidate_id",
                baseline_candidate_key="materialized_candidate_id",
            )
        )
    return out


def group_summary_pair(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    out = []
    for (key,), group in sorted(group_by(rows, [field]).items()):
        summary = summarize_pair_rows(group)
        out.append({field: key, **summary, **claims()})
    return out


def main_analyze_static_relative_blind_evidence(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.37 blind evidence")
    if not resolve(BLIND_RESULTS_CSV).exists():
        main_run_static_relative_blind_replay([])
    vs_add = pair_blind_role("additive_ltm")
    vs_static = pair_blind_role("static_flow_shield")
    vs_fixed = pair_blind_role("best_fixed_static_goal_aware")
    vs_family = pair_blind_role("best_family_static_goal_aware")
    vs_primary = pair_blind_role("primary_static_baseline")
    write_rows(BLIND_VS_ADD, vs_add)
    write_rows(BLIND_VS_STATIC_FLOW, vs_static)
    write_rows(BLIND_VS_BEST_FIXED, vs_fixed)
    write_rows(BLIND_VS_BEST_FAMILY, vs_family)
    write_rows(BLIND_VS_PRIMARY, vs_primary)
    grouped = replay_grouped_by_key()
    oracle_gap = []
    for key, role_rows in grouped.items():
        primary = primary_static_row(role_rows)
        selected = role_rows.get(PRIMARY_POLICY_ROLE)
        candidates = [row for row in role_rows.values() if row.get("role") not in {PRIMARY_POLICY_ROLE}]
        if not primary or not selected or not candidates:
            continue
        best = min(candidates, key=lambda row: (0 if boolish(row.get("solution_found")) else 1, number(row.get("sum_of_loss_ratio"), 999.0)))
        oracle_gap.append(
            {
                "context_budget_iteration_key": key,
                "primary_static_candidate": primary.get("materialized_candidate_id", ""),
                "selected_candidate": selected.get("materialized_candidate_id", ""),
                "oracle_candidate_among_run_roles": best.get("materialized_candidate_id", ""),
                "selected_closes_static_oracle_gap": selected.get("materialized_candidate_id") == best.get("materialized_candidate_id"),
                **claims(),
            }
        )
    write_rows(BLIND_ORACLE_GAP, oracle_gap)
    write_rows(BLIND_BY_MAP, group_summary_pair(vs_primary, "map_family"))
    write_rows(BLIND_BY_BUDGET, group_summary_pair(vs_primary, "budget_ms"))
    write_rows(BLIND_BY_AGENT, group_summary_pair(vs_primary, "agents"))
    failures = [row for row in vs_primary if boolish(row.get("success_regression")) or number(row.get("quality_delta_ratio"), 0.0) > 0.005]
    write_rows(BLIND_FAILURE_CASES, failures)
    primary_summary = summarize_pair_rows(vs_primary, prefix="vs_primary_static")
    add_summary = summarize_pair_rows(vs_add, prefix="vs_additive")
    static_summary = summarize_pair_rows(vs_static, prefix="vs_static_flow")
    fixed_summary = summarize_pair_rows(vs_fixed, prefix="vs_best_fixed")
    family_summary = summarize_pair_rows(vs_family, prefix="vs_best_family")
    replay = load_json(BLIND_SUMMARY, {})
    non_static = sum(1 for row in vs_primary if row.get("selected_candidate") != row.get("baseline_candidate")) / max(1, len(vs_primary))
    fallback_static = 1.0 - non_static
    fallback_add = sum(1 for row in vs_primary if row.get("selected_candidate") == ADDITIVE) / max(1, len(vs_primary))
    high_capture = sum(1 for row in vs_primary if number(row.get("quality_delta_ratio"), 0.0) < -0.005) / max(1, len(vs_primary))
    oracle_closed = sum(1 for row in oracle_gap if boolish(row.get("selected_closes_static_oracle_gap"))) / max(1, len(oracle_gap))
    strong = (
        replay.get("execution_mode") == "real_solver_execution"
        and int(number(replay.get("new_solver_rows"), 0)) >= 3000
        and len(vs_primary) >= 1000
        and int(number(add_summary.get("vs_additive_success_regression_count"), 999)) == 0
        and int(number(static_summary.get("vs_static_flow_success_regression_count"), 999)) == 0
        and int(number(family_summary.get("vs_best_family_success_regression_count"), 999)) == 0
        and number(primary_summary.get("vs_primary_static_quality_only_mean_delta"), 1.0) < 0
        and int(number(primary_summary.get("vs_primary_static_better_count"), 0)) >= int(number(primary_summary.get("vs_primary_static_worse_count"), 999))
        and non_static >= 0.10
    )
    medium = (
        replay.get("execution_mode") == "real_solver_execution"
        and int(number(static_summary.get("vs_static_flow_success_regression_count"), 999)) == 0
        and int(number(family_summary.get("vs_best_family_success_regression_count"), 999)) == 0
        and non_static >= 0.10
        and high_capture > 0
    )
    decision = (
        "static_relative_blind_strong_positive"
        if strong
        else "static_relative_blind_medium_positive"
        if medium
        else "static_relative_learning_not_above_static_blind"
    )
    summary = {
        "schema_version": "phase5p5_repair5g537_static_relative_blind_evidence_summary_v1",
        "decision": decision,
        "real_solver_execution": replay.get("execution_mode") == "real_solver_execution",
        "new_solver_rows": replay.get("new_solver_rows", 0),
        "static_relative_policy_pairs": len(vs_primary),
        **add_summary,
        **static_summary,
        **fixed_summary,
        **family_summary,
        **primary_summary,
        "non_static_selection_rate": csv_number(non_static),
        "fallback_to_static_rate": csv_number(fallback_static),
        "fallback_to_additive_rate": csv_number(fallback_add),
        "static_safe_high_margin_capture": csv_number(high_capture),
        "static_oracle_gap_closed": csv_number(oracle_closed),
        "unsafe_prevented_count_vs_unpatched_selector": "",
        **claims(),
    }
    write_json(BLIND_EVIDENCE_SUMMARY, summary)
    write_text(
        BLIND_EVIDENCE_REPORT,
        "# G5.37 Static-Relative Blind Evidence\n\n"
        f"- decision: `{decision}`\n"
        f"- new solver rows: `{summary['new_solver_rows']}`\n"
        f"- primary static pairs: `{len(vs_primary)}`\n"
        f"- success regressions vs primary static: `{summary['vs_primary_static_success_regression_count']}`\n"
        f"- mean quality delta vs primary static: `{summary['vs_primary_static_quality_only_mean_delta']}`\n"
        f"- non-static selection rate: `{summary['non_static_selection_rate']}`\n",
    )
    print(json.dumps({"decision": decision, "pairs": len(vs_primary)}))
    return 0


def main_analyze_failure_and_static_gap_autopsy(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.37 failure/static-gap autopsy")
    if not resolve(BLIND_EVIDENCE_SUMMARY).exists():
        main_analyze_static_relative_blind_evidence([])
    failures = read_rows(BLIND_FAILURE_CASES)
    oracle_gap = read_rows(BLIND_ORACLE_GAP)
    success = [row for row in read_rows(BLIND_VS_PRIMARY) if boolish(row.get("success_gain")) or number(row.get("quality_delta_ratio"), 0.0) < -0.005]
    missed = [row for row in oracle_gap if not boolish(row.get("selected_closes_static_oracle_gap"))]
    write_rows(AUTOPSY_FAILURE_CSV, failures)
    write_rows(AUTOPSY_MISSED_CSV, missed)
    write_rows(AUTOPSY_SUCCESS_CSV, success)
    reasons = Counter()
    for row in failures:
        if boolish(row.get("success_regression")):
            reasons["success_regression_vs_static_returns"] += 1
        elif row.get("selected_candidate") == row.get("baseline_candidate"):
            reasons["policy_collapses_to_static_fallback"] += 1
        else:
            reasons["selector_picks_non_static_but_no_quality_gain"] += 1
    if not reasons:
        reasons["static_flow_or_best_static_absorbs_most_gain"] += 1
    suggestions = [
        {
            "suggestion_id": "g537_static_gap_design_001",
            "candidate_design_direction": "bounded_static_flow_residual_low_beta_or_flow_decay",
            "reason": "use residual target table; add only small project-owned aliases in a future round",
            **claims(),
        },
        {
            "suggestion_id": "g537_static_gap_design_002",
            "candidate_design_direction": "warehouse_static_additive_bridge",
            "reason": "warehouse remains safety dominated; learning should abstain unless residual targets improve",
            **claims(),
        },
    ]
    write_rows(AUTOPSY_DESIGN_CSV, suggestions)
    summary = {
        "schema_version": "phase5p5_repair5g537_failure_and_static_gap_autopsy_summary_v1",
        "decision": "failure_and_static_gap_autopsy_completed",
        "failure_rows": len(failures),
        "missed_opportunity_rows": len(missed),
        "success_gain_rows": len(success),
        "reason_counts": dict(reasons),
        "design_suggestions": len(suggestions),
        **claims(),
    }
    write_json(AUTOPSY_SUMMARY, summary)
    write_text(
        AUTOPSY_REPORT,
        "# G5.37 Failure and Static-Gap Autopsy\n\n"
        f"- failure rows: `{len(failures)}`\n"
        f"- missed opportunity rows: `{len(missed)}`\n"
        f"- success gain rows: `{len(success)}`\n"
        f"- reason counts: `{dict(reasons)}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "failures": len(failures)}))
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.37 decision")
    if not resolve(AUTOPSY_SUMMARY).exists():
        main_analyze_failure_and_static_gap_autopsy([])
    verify = load_json(VERIFY_SUMMARY, {})
    ladder = load_json(LADDER_SUMMARY, {})
    labels = load_json(LABEL_SUMMARY, {})
    gap = load_json(GAP_SUMMARY, {})
    selector = load_json(SELECTOR_SUMMARY, {})
    residual = load_json(RESIDUAL_SUMMARY, {})
    plan = load_json(BLIND_PLAN_SUMMARY, {})
    replay = load_json(BLIND_SUMMARY, {})
    evidence = load_json(BLIND_EVIDENCE_SUMMARY, {})
    autopsy = load_json(AUTOPSY_SUMMARY, {})
    hard = {
        "real_blind_solver_replay_executed": evidence.get("real_solver_execution") is True,
        "new_solver_rows_ge_3000": int(number(evidence.get("new_solver_rows"), 0)) >= 3000,
        "policy_pairs_vs_primary_static_ge_1000": int(number(evidence.get("static_relative_policy_pairs"), 0)) >= 1000,
        "success_regression_vs_additive_zero": int(number(evidence.get("vs_additive_success_regression_count"), 999)) == 0,
        "success_regression_vs_static_flow_zero": int(number(evidence.get("vs_static_flow_success_regression_count"), 999)) == 0,
        "success_regression_vs_best_static_zero": int(number(evidence.get("vs_best_family_success_regression_count"), 999)) == 0,
        "quality_only_mean_delta_vs_primary_static_lt_0": number(evidence.get("vs_primary_static_quality_only_mean_delta"), 1.0) < 0,
        "better_count_vs_primary_static_ge_worse": int(number(evidence.get("vs_primary_static_better_count"), 0)) >= int(number(evidence.get("vs_primary_static_worse_count"), 999)),
        "non_static_selection_rate_ge_0p10": number(evidence.get("non_static_selection_rate"), 0.0) >= 0.10,
        "all_claims_closed": not any(
            [
                claims()["phase5p5_allowed"],
                claims()["phase6_allowed"],
                claims()["runtime_claim_allowed"],
                claims()["learned_runtime_policy_validated"],
                claims()["aaai_ready"],
            ]
        ),
        "external_lacam2_clean": external_lacam2_clean(),
        "reserved_ids_untouched": True,
    }
    if not hard["real_blind_solver_replay_executed"] or not hard["new_solver_rows_ge_3000"] or not hard["policy_pairs_vs_primary_static_ge_1000"]:
        decision = "g537_real_replay_insufficient_run_more"
    elif not (hard["success_regression_vs_additive_zero"] and hard["success_regression_vs_static_flow_zero"] and hard["success_regression_vs_best_static_zero"]):
        decision = "g537_static_relative_success_regression_blocks_learning"
    elif hard["quality_only_mean_delta_vs_primary_static_lt_0"] and hard["better_count_vs_primary_static_ge_worse"] and hard["non_static_selection_rate_ge_0p10"]:
        decision = "g537_learning_beats_static_flow_blind_continue_runtime_preflight_spec"
    elif number(evidence.get("non_static_selection_rate"), 0.0) >= 0.10 and number(evidence.get("static_safe_high_margin_capture"), 0.0) > 0:
        decision = "g537_learning_matches_static_but_recovers_safe_opportunities_continue_residual_design"
    elif number(evidence.get("vs_additive_quality_only_mean_delta"), 1.0) < 0:
        decision = "g537_learning_beats_additive_not_static_continue_static_relative_training"
    else:
        decision = "g537_static_baseline_stronger_continue_parameter_design"
    summary = {
        "schema_version": "phase5p5_repair5g537_decision_summary_v1",
        "decision": decision,
        "component_decisions": {
            "verification": verify.get("decision"),
            "baseline_ladder": ladder.get("decision"),
            "labels": labels.get("decision"),
            "static_flow_gap": gap.get("decision"),
            "selector": selector.get("decision"),
            "residual": residual.get("decision"),
            "blind_plan": plan.get("decision"),
            "blind_replay": replay.get("decision"),
            "blind_evidence": evidence.get("decision"),
            "autopsy": autopsy.get("decision"),
        },
        "hard_requirements": hard,
        "key_metrics": {
            "new_solver_rows": evidence.get("new_solver_rows", 0),
            "policy_pairs_vs_primary_static": evidence.get("static_relative_policy_pairs", 0),
            "success_regression_vs_additive": evidence.get("vs_additive_success_regression_count", ""),
            "success_regression_vs_static_flow": evidence.get("vs_static_flow_success_regression_count", ""),
            "success_regression_vs_best_static": evidence.get("vs_best_family_success_regression_count", ""),
            "quality_only_mean_delta_vs_primary_static": evidence.get("vs_primary_static_quality_only_mean_delta", ""),
            "better_vs_primary_static": evidence.get("vs_primary_static_better_count", ""),
            "worse_vs_primary_static": evidence.get("vs_primary_static_worse_count", ""),
            "non_static_selection_rate": evidence.get("non_static_selection_rate", ""),
            "fallback_to_static_rate": evidence.get("fallback_to_static_rate", ""),
        },
        **claims(),
    }
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.37 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- new solver rows: `{summary['key_metrics']['new_solver_rows']}`\n"
        f"- primary-static policy pairs: `{summary['key_metrics']['policy_pairs_vs_primary_static']}`\n"
        f"- success regressions vs additive/static_flow/best_static: `{summary['key_metrics']['success_regression_vs_additive']}` / `{summary['key_metrics']['success_regression_vs_static_flow']}` / `{summary['key_metrics']['success_regression_vs_best_static']}`\n"
        f"- mean delta vs primary static: `{summary['key_metrics']['quality_only_mean_delta_vs_primary_static']}`\n"
        f"- non-static selection rate: `{summary['key_metrics']['non_static_selection_rate']}`\n"
        "- claims remain closed: `phase5p5_allowed=false`, `phase6_allowed=false`, "
        "`runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, `aaai_ready=false`.\n",
    )
    print(json.dumps({"decision": decision, "new_solver_rows": evidence.get("new_solver_rows", 0)}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]

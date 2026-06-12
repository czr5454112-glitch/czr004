"""Repair5G.5.38 static-flow residual candidate design and labels.

This round audits the G5.37 static-flow-relative failure, rebuilds direct
static-relative labels from real solver rows, creates a bounded residual
candidate family through existing project-owned adapter grammar, and evaluates
the family with real solver screening and blind replay.
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
import repair5g537_common as g537  # noqa: E402


SEED = 20260612 + 538
ADDITIVE = g535.ADDITIVE
STATIC_FLOW = g535.STATIC_FLOW
BEST_FIXED = g535.BEST_FIXED

PLAN_FILE = "czr004_g538_static_flow_residual_candidate_design_and_label_rebuild_plan.md"

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g538_g537_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g538_g537_verification_summary.json"
FAILURE_AUDIT_REPORT = "outputs/reports/phase5p5_repair5g538_g537_failure_mode_audit.md"
FAILURE_AUDIT_SUMMARY = "outputs/reports/phase5p5_repair5g538_g537_failure_mode_audit_summary.json"
G537_TABLE_AUDIT = "outputs/tables/phase5p5_repair5g538_g537_table_materialization_audit.csv"
G537_LABEL_SOURCE_AUDIT = "outputs/tables/phase5p5_repair5g538_g537_label_source_audit.csv"
G537_POLICY_SPARSITY_AUDIT = "outputs/tables/phase5p5_repair5g538_g537_policy_sparsity_audit.csv"
G537_PRIMARY_STATIC_AUDIT = "outputs/tables/phase5p5_repair5g538_g537_primary_static_oracle_audit.csv"
G537_FAILURE_CLUSTER_AUDIT = "outputs/tables/phase5p5_repair5g538_g537_failure_case_cluster_audit.csv"

DIRECT_OUTCOMES_CSV = "outputs/tables/phase5p5_repair5g538_direct_context_candidate_outcomes.csv"
DIRECT_LABELS_CSV = "outputs/tables/phase5p5_repair5g538_direct_static_relative_labels.csv"
DIRECT_PAIRWISE_CSV = "outputs/tables/phase5p5_repair5g538_direct_static_relative_pairwise.csv"
DIRECT_GROUPS_CSV = "outputs/tables/phase5p5_repair5g538_direct_static_relative_training_groups.csv"
DIRECT_COVERAGE_CSV = "outputs/tables/phase5p5_repair5g538_direct_static_relative_source_coverage.csv"
DIRECT_LABEL_REPORT = "outputs/reports/phase5p5_repair5g538_direct_static_relative_labels.md"
DIRECT_LABEL_SUMMARY = "outputs/reports/phase5p5_repair5g538_direct_static_relative_labels_summary.json"

CANDIDATE_FAMILY_CSV = "outputs/tables/phase5p5_repair5g538_static_flow_residual_candidate_family.csv"
NEW_ALIAS_AUDIT_CSV = "outputs/tables/phase5p5_repair5g538_new_adapter_alias_audit.csv"
CANDIDATE_FAMILY_REPORT = "outputs/reports/phase5p5_repair5g538_static_flow_residual_candidate_family.md"
CANDIDATE_FAMILY_SUMMARY = "outputs/reports/phase5p5_repair5g538_static_flow_residual_candidate_family_summary.json"

PROBE_PLAN_CSV = "outputs/tables/phase5p5_repair5g538_static_flow_residual_probe_plan.csv"
PROBE_RESULTS_CSV = "outputs/tables/phase5p5_repair5g538_static_flow_residual_probe_results.csv"
PROBE_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g538_static_flow_residual_probe_sample.csv"
PROBE_REPORT = "outputs/reports/phase5p5_repair5g538_static_flow_residual_candidate_probe.md"
PROBE_SUMMARY = "outputs/reports/phase5p5_repair5g538_static_flow_residual_candidate_probe_summary.json"
PROBE_MANIFEST = "outputs/reports/phase5p5_repair5g538_static_flow_residual_candidate_probe_manifest.json"
PROBE_RAW_LOG_DIR = "outputs/logs/phase5p5_repair5g538_static_flow_residual_probe"
PROBE_RAW_RUN_JSONL = f"{PROBE_RAW_LOG_DIR}/phase5p5_repair5g538_static_flow_residual_probe_runs.jsonl"
PROBE_RAW_COMMAND_JSONL = f"{PROBE_RAW_LOG_DIR}/phase5p5_repair5g538_static_flow_residual_probe_commands.jsonl"
PROBE_RAW_CHECKPOINT_JSONL = f"{PROBE_RAW_LOG_DIR}/phase5p5_repair5g538_static_flow_residual_probe_checkpoints.jsonl"
PROBE_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g538_static_flow_residual_probe_scenarios"
PROBE_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g538_static_flow_residual_probe_scenario_generation.json"

RESIDUAL_VS_STATIC_FLOW_CSV = "outputs/tables/phase5p5_repair5g538_residual_vs_static_flow.csv"
RESIDUAL_VS_BEST_FIXED_CSV = "outputs/tables/phase5p5_repair5g538_residual_vs_best_fixed_static.csv"
RESIDUAL_VS_FAMILY_CSV = "outputs/tables/phase5p5_repair5g538_residual_vs_family_static.csv"
RESIDUAL_LEADERBOARD_CSV = "outputs/tables/phase5p5_repair5g538_residual_candidate_leaderboard.csv"
RESIDUAL_BY_MAP_CSV = "outputs/tables/phase5p5_repair5g538_residual_candidate_by_map_family.csv"
RESIDUAL_BY_BUDGET_CSV = "outputs/tables/phase5p5_repair5g538_residual_candidate_by_budget.csv"
RESIDUAL_BY_AGENT_CSV = "outputs/tables/phase5p5_repair5g538_residual_candidate_by_agent.csv"
RESIDUAL_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g538_residual_candidate_failure_cases.csv"
RESIDUAL_EVIDENCE_REPORT = "outputs/reports/phase5p5_repair5g538_residual_candidate_evidence.md"
RESIDUAL_EVIDENCE_SUMMARY = "outputs/reports/phase5p5_repair5g538_residual_candidate_evidence_summary.json"

SELECTOR_EVAL_CSV = "outputs/tables/phase5p5_repair5g538_residual_selector_eval_by_split.csv"
SELECTOR_PREDICTIONS_CSV = "outputs/tables/phase5p5_repair5g538_residual_selector_predictions.csv"
SELECTOR_NEGATIVE_CSV = "outputs/tables/phase5p5_repair5g538_residual_selector_negative_controls.csv"
SELECTOR_REPORT = "outputs/reports/phase5p5_repair5g538_residual_selector.md"
SELECTOR_SUMMARY = "outputs/reports/phase5p5_repair5g538_residual_selector_summary.json"
SELECTOR_MANIFEST = "artifacts/models/laur_ltm/repair5g538_residual_selector_manifest.json"

BLIND_PLAN_CSV = "outputs/tables/phase5p5_repair5g538_residual_blind_replay_plan.csv"
BLIND_PLAN_REPORT = "outputs/reports/phase5p5_repair5g538_residual_blind_replay_plan.md"
BLIND_RESULTS_CSV = "outputs/tables/phase5p5_repair5g538_residual_blind_replay_results.csv"
BLIND_VS_STATIC_FLOW_CSV = "outputs/tables/phase5p5_repair5g538_residual_blind_selected_vs_static_flow.csv"
BLIND_VS_BEST_STATIC_CSV = "outputs/tables/phase5p5_repair5g538_residual_blind_selected_vs_best_static.csv"
BLIND_FAILURE_CASES_CSV = "outputs/tables/phase5p5_repair5g538_residual_blind_failure_cases.csv"
BLIND_REPLAY_REPORT = "outputs/reports/phase5p5_repair5g538_residual_blind_replay.md"
BLIND_EVIDENCE_REPORT = "outputs/reports/phase5p5_repair5g538_residual_blind_evidence.md"
BLIND_EVIDENCE_SUMMARY = "outputs/reports/phase5p5_repair5g538_residual_blind_evidence_summary.json"
BLIND_RAW_LOG_DIR = "outputs/logs/phase5p5_repair5g538_residual_blind_replay"
BLIND_RAW_RUN_JSONL = f"{BLIND_RAW_LOG_DIR}/phase5p5_repair5g538_residual_blind_runs.jsonl"
BLIND_RAW_COMMAND_JSONL = f"{BLIND_RAW_LOG_DIR}/phase5p5_repair5g538_residual_blind_commands.jsonl"
BLIND_RAW_CHECKPOINT_JSONL = f"{BLIND_RAW_LOG_DIR}/phase5p5_repair5g538_residual_blind_checkpoints.jsonl"
BLIND_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g538_residual_blind_scenarios"
BLIND_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g538_residual_blind_scenario_generation.json"

DECISION_REPORT = "outputs/reports/phase5p5_repair5g538_decision.md"
DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g538_decision_summary.json"

G537_REQUIRED = {
    "decision_summary": "outputs/reports/phase5p5_repair5g537_decision_summary.json",
    "static_relative_blind_evidence_summary": "outputs/reports/phase5p5_repair5g537_static_relative_blind_evidence_summary.json",
    "static_relative_blind_replay_summary": "outputs/reports/phase5p5_repair5g537_static_relative_blind_replay_summary.json",
    "static_baseline_ladder_summary": "outputs/reports/phase5p5_repair5g537_static_baseline_ladder_summary.json",
    "static_relative_labels_summary": "outputs/reports/phase5p5_repair5g537_static_relative_labels_summary.json",
    "static_flow_gap_summary": "outputs/reports/phase5p5_repair5g537_static_flow_gap_summary.json",
    "static_relative_selector_summary": "outputs/reports/phase5p5_repair5g537_static_relative_selector_summary.json",
    "static_flow_residual_model_summary": "outputs/reports/phase5p5_repair5g537_static_flow_residual_model_summary.json",
    "failure_and_static_gap_autopsy_summary": "outputs/reports/phase5p5_repair5g537_failure_and_static_gap_autopsy_summary.json",
    "selector_manifest": "artifacts/models/laur_ltm/repair5g537_static_relative_selector_manifest.json",
    "static_relative_blind_replay_results": "outputs/tables/phase5p5_repair5g537_static_relative_blind_replay_results.csv",
    "blind_selected_vs_primary_static": "outputs/tables/phase5p5_repair5g537_blind_selected_vs_primary_static.csv",
    "static_gap_failure_cases": "outputs/tables/phase5p5_repair5g537_static_gap_failure_cases.csv",
    "static_relative_context_candidate_utility": "outputs/tables/phase5p5_repair5g537_static_relative_context_candidate_utility.csv",
    "repair5g537_common": "scripts/repair5g537_common.py",
}

DIRECT_SOURCE_PATHS = [
    ("G5.34_broad_probe", "outputs/tables/phase5p5_repair5g534_broad_probe_results.csv"),
    ("G5.34_prospective_selected_replay", "outputs/tables/phase5p5_repair5g534_prospective_selected_replay_results.csv"),
    ("G5.36_real_no_regression_replay", "outputs/tables/phase5p5_repair5g536_real_no_regression_replay_results.csv"),
    ("G5.37_static_relative_blind_replay", "outputs/tables/phase5p5_repair5g537_static_relative_blind_replay_results.csv"),
]

STATIC_ROLES = {
    "additive_ltm",
    "static_flow_shield",
    "best_fixed_static_goal_aware",
    "frozen_family_static_goal_aware",
    "family_static_goal_aware",
    "ultra_safe_static_fallback",
}

_CANDIDATE_FAMILY_ROWS_CACHE: list[dict[str, Any]] | None = None
_CANDIDATE_META_CACHE: dict[str, dict[str, Any]] | None = None
_METHOD_TO_CANDIDATE_CACHE: dict[str, str] | None = None
_FAMILY_BUDGET_CANDIDATE_CACHE: dict[tuple[str, int, int], str] | None = None
_BEST_FAMILY_CANDIDATE_CACHE: dict[str, str] = {}


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


def row_success(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    if str(row.get("solution_found", "")).strip():
        return boolish(row.get("solution_found"))
    if str(row.get("candidate_solution_found", "")).strip():
        return boolish(row.get("candidate_solution_found"))
    return False


def row_ratio(row: dict[str, Any] | None) -> float | None:
    if not row:
        return None
    ratio = finite_ratio(row.get("sum_of_loss_ratio"))
    if ratio is not None:
        return ratio
    return finite_ratio(row.get("candidate_quality_delta"))


def compare_candidate_to_baseline(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    cand_success = row_success(candidate)
    base_success = row_success(baseline)
    cand_ratio = row_ratio(candidate)
    base_ratio = row_ratio(baseline)
    success_reg = base_success and not cand_success
    success_gain = cand_success and not base_success
    both_fail = (not cand_success) and (not base_success)
    both_success = cand_success and base_success
    q = cand_ratio - base_ratio if both_success and cand_ratio is not None and base_ratio is not None else None
    corrected = 0.25 if success_reg else -0.25 if success_gain else q if q is not None else 0.0
    return {
        "success_regression": success_reg,
        "success_gain": success_gain,
        "both_fail": both_fail,
        "both_success": both_success,
        "quality_delta_ratio": q,
        "corrected_delta_ratio_for_mean": corrected,
        "safe_high_margin_gain": (not success_reg) and (success_gain or (q is not None and q < -0.005)),
        "safe_low_margin_gain": (not success_reg) and (q is not None and -0.005 <= q < 0.0),
        "equal": (not success_reg) and (not success_gain) and (q is not None and abs(q) <= 0.005),
        "safe_worse": (not success_reg) and (q is not None and q > 0.005),
    }


def make_pair_row(
    key: str,
    selected: dict[str, Any],
    baseline: dict[str, Any],
    *,
    policy_role: str,
    baseline_role: str,
) -> dict[str, Any]:
    cmp = compare_candidate_to_baseline(selected, baseline)
    selected_ratio = row_ratio(selected)
    baseline_ratio = row_ratio(baseline)
    return {
        "policy_role": policy_role,
        "paired_against_role": baseline_role,
        "direct_group_key": selected.get("direct_group_key", ""),
        "context_budget_iteration_key": key,
        "context_key": selected.get("context_key", context_no_iteration(key)),
        "map": selected.get("map", ""),
        "map_family": selected.get("map_family", ""),
        "agents": selected.get("agents", ""),
        "seed": selected.get("seed", ""),
        "budget_ms": selected.get("budget_ms", ""),
        "iteration": selected.get("iteration", ""),
        "selected_candidate": selected.get("materialized_candidate_id", selected.get("candidate_id", "")),
        "baseline_candidate": baseline.get("materialized_candidate_id", baseline.get("candidate_id", "")),
        "baseline_ratio": "" if baseline_ratio is None else csv_number(baseline_ratio),
        "selected_ratio": "" if selected_ratio is None else csv_number(selected_ratio),
        "corrected_delta_ratio_for_mean": csv_number(cmp["corrected_delta_ratio_for_mean"]),
        "quality_delta_ratio": "" if cmp["quality_delta_ratio"] is None else csv_number(cmp["quality_delta_ratio"]),
        "success_regression": cmp["success_regression"],
        "success_gain": cmp["success_gain"],
        "both_fail": cmp["both_fail"],
        "both_success": cmp["both_success"],
        "safe_high_margin_gain": cmp["safe_high_margin_gain"],
        "safe_low_margin_gain": cmp["safe_low_margin_gain"],
        "equal_vs_baseline": cmp["equal"],
        "safe_worse": cmp["safe_worse"],
        **claims(),
    }


def summarize_pair_rows(rows: list[dict[str, Any]], *, prefix: str = "") -> dict[str, Any]:
    quality = [
        number(row.get("quality_delta_ratio"), 0.0)
        for row in rows
        if str(row.get("quality_delta_ratio", "")).strip()
    ]
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


def best_family_candidate_for_map(map_name: str) -> str:
    family = map_name if map_name in {"maze", "random", "warehouse"} else map_family(map_name)
    if family not in _BEST_FAMILY_CANDIDATE_CACHE:
        _BEST_FAMILY_CANDIDATE_CACHE[family] = g534.best_family_static_candidate(family)
    return _BEST_FAMILY_CANDIDATE_CACHE[family]


def family_budget_candidate(family: str, budget: int, agents: int) -> str:
    global _FAMILY_BUDGET_CANDIDATE_CACHE
    if _FAMILY_BUDGET_CANDIDATE_CACHE is None:
        _FAMILY_BUDGET_CANDIDATE_CACHE = {}
        rows = read_rows("outputs/tables/phase5p5_repair5g537_static_baseline_winner_by_stratum.csv")
        for row in rows:
            if row.get("baseline_level") == "best_family_budget_static_goal_aware":
                key = (
                    str(row.get("map_family", "")),
                    int(number(row.get("budget_ms"), 0)),
                    int(number(row.get("agents"), 0)),
                )
                _FAMILY_BUDGET_CANDIDATE_CACHE[key] = str(row.get("top_candidate") or STATIC_FLOW)
    cached = _FAMILY_BUDGET_CANDIDATE_CACHE.get((family, int(budget), int(agents)))
    if cached:
        return cached
    if family not in _BEST_FAMILY_CANDIDATE_CACHE:
        _BEST_FAMILY_CANDIDATE_CACHE[family] = g534.best_family_static_candidate(family)
    return _BEST_FAMILY_CANDIDATE_CACHE[family]


def candidate_family_rows() -> list[dict[str, Any]]:
    global _CANDIDATE_FAMILY_ROWS_CACHE
    if _CANDIDATE_FAMILY_ROWS_CACHE is not None:
        return [dict(row) for row in _CANDIDATE_FAMILY_ROWS_CACHE]
    rows: list[dict[str, Any]] = []
    old = g534.candidate_by_id()
    seen: set[str] = set()

    def add_row(row: dict[str, Any]) -> None:
        cid = str(row["candidate_id"])
        if cid in seen:
            return
        seen.add(cid)
        out = dict(row)
        out["candidate_index"] = len(rows)
        out.setdefault("adapter_change_required", False)
        out.setdefault("is_new_alias", False)
        out.setdefault("existing_project_owned_alias", True)
        out.setdefault("implemented_new_aliases", False)
        out.setdefault("project_owned_adapter_only", True)
        out.update(claims())
        rows.append(out)

    def from_existing(cid: str, source: str, hypothesis: str) -> None:
        meta = dict(old.get(cid, {"candidate_id": cid, "method": cid}))
        meta["source"] = source
        meta["intended_hypothesis"] = hypothesis
        meta["expected_risk_strata"] = "baseline/control"
        meta["expected_improvement_strata"] = "deployable static anchor"
        add_row(meta)

    def add_grid(
        cid: str,
        source: str,
        hypothesis: str,
        risk: str,
        improvement: str,
        *,
        c: float = 1.25,
        b: float = 1.25,
        f: float = 1.0,
        w: float = 0.75,
        dc: float = 0.95,
        df: float = 1.0,
        beta: float = 0.35,
        max_shield: float = 0.75,
        c_only: bool = False,
    ) -> None:
        add_row(
            {
                "candidate_id": cid,
                "method": g534.grid_method(
                    c=c,
                    b=b,
                    f=f,
                    w=w,
                    dc=dc,
                    df=df,
                    beta=beta,
                    max_shield=max_shield,
                    c_only=c_only,
                ),
                "source": source,
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
                "min_edge_cost": 0.25 if c_only else 1.0,
                "max_edge_cost": 11.0,
                "intended_hypothesis": hypothesis,
                "expected_risk_strata": risk,
                "expected_improvement_strata": improvement,
                "method_parser_family": "repair5g518_grid",
                "is_new_alias": False,
                "adapter_change_required": False,
            }
        )

    from_existing(STATIC_FLOW, "static_anchor", "validated static-flow shield anchor")
    from_existing(BEST_FIXED, "static_anchor", "best fixed static goal-aware anchor")
    for fam in ["maze", "random", "warehouse"]:
        from_existing(g534.best_family_static_candidate(fam), "static_anchor", f"best {fam} family static anchor")

    add_grid("repair5g538_low_beta_b015_cap040", "residual_low_beta", "lower beta and cap around static-flow", "low shield may underuse flow", "safe low-beta static-flow residual", beta=0.15, max_shield=0.40)
    add_grid("repair5g538_low_beta_b020_cap045", "residual_low_beta", "lower beta with conservative cap", "low shield may lose maze flow benefit", "random/warehouse safety", beta=0.20, max_shield=0.45)
    add_grid("repair5g538_low_beta_b025_cap050", "residual_low_beta", "mild beta residual", "moderate low-beta risk", "static-flow low-margin opportunities", beta=0.25, max_shield=0.50)
    add_grid("repair5g538_low_beta_b030_cap075", "residual_low_beta", "near static beta with lower cap", "low cap can miss corridor benefit", "safe flow shield dampening", beta=0.30, max_shield=0.75)

    add_grid("repair5g538_flow_decay_df090", "residual_flow_decay", "strong F-channel decay", "may forget useful flow too quickly", "maze 2000 flow reset", df=0.90)
    add_grid("repair5g538_flow_decay_df095", "residual_flow_decay", "medium F-channel decay", "small flow-memory loss", "maze/random stale-flow control", df=0.95)
    add_grid("repair5g538_flow_decay_df098", "residual_flow_decay", "light F-channel decay", "minimal risk", "low-margin static-flow residual", df=0.98)

    add_grid("repair5g538_wait_damped_w035", "residual_wait_damped", "strongly damp nonprogress wait pressure", "can under-penalize stalls", "warehouse bridge", w=0.35)
    add_grid("repair5g538_wait_damped_w050", "residual_wait_damped", "wait damped to conservative G5.59 level", "low", "warehouse/random wait safety", w=0.50)
    add_grid("repair5g538_wait_damped_w065", "residual_wait_damped", "slightly damped wait pressure", "minimal", "low-margin wait repair", w=0.65)

    add_grid("repair5g538_warehouse_bridge_light_cf", "warehouse_bridge", "light C/F with slow decay", "may be too permissive", "warehouse safety bridge", c=1.0, b=1.0, f=0.75, w=0.50, dc=0.98, df=0.98, beta=0.20, max_shield=0.50)
    add_grid("repair5g538_warehouse_bridge_block_guard", "warehouse_bridge", "block guarded and wait damped", "can over-penalize blockage", "warehouse/high-risk budgets", c=1.0, b=1.25, f=0.75, w=0.35, dc=0.98, df=0.98, beta=0.25, max_shield=0.50)
    add_grid("repair5g538_warehouse_bridge_c_only_slow", "warehouse_bridge", "C-only conservative bridge", "no flow benefit", "warehouse fallback/additive bridge", c=1.0, b=1.0, f=0.0, w=0.50, dc=0.98, df=1.0, beta=0.0, max_shield=0.0, c_only=True)

    add_grid("repair5g538_maze_bridge_decay_beta025", "maze_bridge", "maze flow decay with beta 0.25", "maze-only overfit", "maze 2000 safe corridor bridge", df=0.90, beta=0.25, max_shield=0.75)
    add_grid("repair5g538_maze_bridge_decay_beta020", "maze_bridge", "maze light beta and medium decay", "may match static only", "maze 2000 low beta bridge", df=0.95, beta=0.20, max_shield=0.75)
    add_grid("repair5g538_maze_bridge_block_decay", "maze_bridge", "maze block guard with flow decay", "block-heavy regressions possible", "maze bottleneck recovery", b=1.50, w=0.50, df=0.90, beta=0.25, max_shield=0.75)

    add_grid("repair5g538_random_bridge_c_light", "random_bridge", "lighter C with near-static flow", "iteration-1 random risk", "random 50/100 bridge", c=1.0, b=1.25, w=0.65, df=0.98, beta=0.30)
    add_grid("repair5g538_random_bridge_b_light", "random_bridge", "lighter B with static C", "can miss blockage", "random iteration-1 regression repair", c=1.25, b=1.0, w=0.65, df=0.98, beta=0.30)
    add_grid("repair5g538_random_bridge_low_beta", "random_bridge", "balanced low beta random bridge", "may be too close to static", "random low-margin opportunities", c=1.0, b=1.0, w=0.75, df=0.98, beta=0.20, max_shield=0.75)

    from_existing(ADDITIVE, "control", "additive fallback control")
    _CANDIDATE_FAMILY_ROWS_CACHE = [dict(row) for row in rows]
    return rows


def candidate_meta() -> dict[str, dict[str, Any]]:
    global _CANDIDATE_META_CACHE
    if _CANDIDATE_META_CACHE is not None:
        return _CANDIDATE_META_CACHE
    meta = {str(row["candidate_id"]): row for row in g534.expanded_candidate_params()}
    for row in candidate_family_rows():
        meta[str(row["candidate_id"])] = row
    _CANDIDATE_META_CACHE = meta
    return meta


def method_to_candidate() -> dict[str, str]:
    global _METHOD_TO_CANDIDATE_CACHE
    if _METHOD_TO_CANDIDATE_CACHE is not None:
        return _METHOD_TO_CANDIDATE_CACHE
    out = {}
    for cid, row in candidate_meta().items():
        method = str(row.get("method", ""))
        if method:
            out[method] = cid
    _METHOD_TO_CANDIDATE_CACHE = out
    return out


def canonical_candidate_id(raw_id: str) -> str:
    text = str(raw_id)
    if text in candidate_meta():
        return text
    return method_to_candidate().get(text, text)


def candidate_method(candidate_id: str) -> str:
    return str(candidate_meta().get(str(candidate_id), {}).get("method", candidate_id))


def residual_candidate_ids() -> list[str]:
    rows = []
    for row in candidate_family_rows():
        source = str(row.get("source", ""))
        cid = str(row.get("candidate_id", ""))
        if source.startswith("residual_") or source.endswith("_bridge"):
            rows.append(cid)
    return rows


def role_name_for_residual(cid: str) -> str:
    return f"residual::{cid}"


def direct_candidate_id(row: dict[str, Any]) -> str:
    for key in ["materialized_candidate_id", "candidate_id", "planned_candidate_id"]:
        value = str(row.get(key, "")).strip()
        if value:
            return value
    method = str(row.get("method", ""))
    return g534.split_alias(method)[0] if method else ""


def normalize_direct_row(row: dict[str, Any], source_round: str, source_path: str, idx: int) -> dict[str, Any]:
    cid = direct_candidate_id(row)
    key = str(row.get("context_budget_iteration_key") or context_key(row))
    group_key = f"{source_round}|{key}"
    role = str(row.get("role", ""))
    if not role:
        if cid == ADDITIVE:
            role = "additive_ltm"
        elif cid == STATIC_FLOW:
            role = "static_flow_shield"
        elif cid == BEST_FIXED:
            role = "best_fixed_static_goal_aware"
        else:
            role = "candidate"
    real = str(row.get("trace_backend", "")) == "real_solver_trace" or "real_solver" in source_round
    return {
        "direct_row_id": f"g538_direct_{idx:08d}",
        "direct_group_key": group_key,
        "source_round": source_round,
        "source_path": source_path,
        "materialization_source": row.get("materialization_source", row.get("source_round", source_round)),
        "real_solver_execution": real,
        "context_budget_iteration_key": key,
        "context_key": str(row.get("context_key") or context_no_iteration(key)),
        "candidate_id": cid,
        "materialized_candidate_id": cid,
        "role": role,
        "map": row.get("map", ""),
        "map_family": row.get("map_family") or map_family(str(row.get("map", ""))),
        "agents": row.get("agents", ""),
        "seed": row.get("seed", ""),
        "budget_ms": row.get("budget_ms", ""),
        "iteration": row.get("iteration", ""),
        "solution_found": row.get("solution_found", row.get("candidate_solution_found", "")),
        "sum_of_loss_ratio": row.get("sum_of_loss_ratio", ""),
        "expanded_nodes": row.get("expanded_nodes", ""),
        "trace_event_count": row.get("trace_event_count", ""),
        "trace_backend": row.get("trace_backend", ""),
        **claims(),
    }


def load_direct_outcome_rows() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    idx = 0
    for source_round, source_path in DIRECT_SOURCE_PATHS:
        for row in read_rows(source_path):
            out.append(normalize_direct_row(row, source_round, source_path, idx))
            idx += 1
    return out


def group_rows_by_direct_group(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[str(row.get("direct_group_key", ""))][str(row.get("candidate_id", ""))] = row
    return grouped


def baseline_candidates_for(row: dict[str, Any]) -> dict[str, str]:
    family = str(row.get("map_family") or map_family(str(row.get("map", ""))))
    budget = int(number(row.get("budget_ms"), 0))
    agents = int(number(row.get("agents"), 0))
    return {
        "additive_ltm": ADDITIVE,
        "static_flow_shield": STATIC_FLOW,
        "best_fixed_static_goal_aware": BEST_FIXED,
        "frozen_family_static_goal_aware": best_family_candidate_for_map(family),
        "frozen_family_budget_static_goal_aware": family_budget_candidate(family, budget, agents),
    }


def rank_static_row(row: dict[str, Any]) -> tuple[int, float, str]:
    success = row_success(row)
    ratio = row_ratio(row)
    return (0 if success else 1, ratio if ratio is not None else 999.0, str(row.get("role", "")))


def best_static_row(role_rows: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [
        role_rows.get("static_flow_shield"),
        role_rows.get("best_fixed_static_goal_aware"),
        role_rows.get("frozen_family_static_goal_aware"),
        role_rows.get("family_static_goal_aware"),
    ]
    candidates = [row for row in candidates if row]
    return min(candidates, key=rank_static_row) if candidates else None


def main_verify_g537_artifacts(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.38 verify G5.37")
    rows = []
    missing = []
    for name, path in G537_REQUIRED.items():
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
    write_rows(G537_TABLE_AUDIT, rows)
    decision = "g537_artifacts_verified" if not missing else "g537_artifact_blocker_stop"
    summary = {
        "schema_version": "phase5p5_repair5g538_g537_verification_summary_v1",
        "decision": decision,
        "required_artifacts": len(G537_REQUIRED),
        "missing_artifacts": missing,
        "all_required_present": not missing,
        "g537_decision": load_json(G537_REQUIRED["decision_summary"], {}).get("decision", ""),
        **claims(),
    }
    write_json(VERIFY_SUMMARY, summary)
    write_text(
        VERIFY_REPORT,
        "# G5.38 Verification of G5.37 Artifacts\n\n"
        f"- decision: `{decision}`\n"
        f"- required artifacts: `{len(G537_REQUIRED)}`\n"
        f"- missing artifacts: `{len(missing)}`\n",
    )
    print(json.dumps({"decision": decision, "missing": len(missing)}))
    return 0 if not missing else 1


def main_audit_g537_failure_modes(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.38 audit G5.37")
    if not resolve(VERIFY_SUMMARY).exists():
        main_verify_g537_artifacts([])

    label_source = []
    source_counts = {
        "G5.35_lexicographic_labels": table_count(g535.LEX_UTILITY_CSV),
        "G5.36_safe_opportunity_examples": table_count(g536.SAFE_EXAMPLES_CSV),
        "G5.36_real_replay_rows": table_count("outputs/tables/phase5p5_repair5g536_real_no_regression_replay_results.csv"),
        "G5.37_blind_replay_rows": table_count("outputs/tables/phase5p5_repair5g537_static_relative_blind_replay_results.csv"),
    }
    common_text = resolve("scripts/repair5g537_common.py").read_text(encoding="utf-8")
    lex_preferred = "if rows:\n        return rows" in common_text and "g535.LEX_UTILITY_CSV" in common_text
    for source, count in source_counts.items():
        label_source.append(
            {
                "source": source,
                "row_count": count,
                "used_by_g537_label_source_rows": source == "G5.35_lexicographic_labels" and lex_preferred,
                "direct_real_replay_source": source in {"G5.36_real_replay_rows", "G5.37_blind_replay_rows"},
                **claims(),
            }
        )
    write_rows(G537_LABEL_SOURCE_AUDIT, label_source)

    manifest = load_json(G537_REQUIRED["selector_manifest"], {})
    policies = manifest.get("policies", {})
    policy_rows = []
    all_entries = 0
    covered = {"strata": set(), "families": set(), "budgets": set(), "agents": set()}
    for policy_name, entries in policies.items():
        for key, cid in dict(entries).items():
            all_entries += 1
            parts = key.split("|")
            family = parts[0] if len(parts) > 0 else ""
            budget = parts[1] if len(parts) > 1 else ""
            agents = parts[2] if len(parts) > 2 else ""
            covered["strata"].add(key)
            covered["families"].add(family)
            covered["budgets"].add(budget)
            covered["agents"].add(agents)
            policy_rows.append(
                {
                    "policy_name": policy_name,
                    "stratum": key,
                    "map_family": family,
                    "budget_ms": budget,
                    "agents": agents,
                    "candidate_id": cid,
                    **claims(),
                }
            )
    write_rows(G537_POLICY_SPARSITY_AUDIT, policy_rows)

    primary_pairs = read_rows("outputs/tables/phase5p5_repair5g537_blind_selected_vs_primary_static.csv")
    replay_rows = read_rows("outputs/tables/phase5p5_repair5g537_static_relative_blind_replay_results.csv")
    by_key_role: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in replay_rows:
        by_key_role[str(row.get("context_budget_iteration_key", ""))][str(row.get("role", ""))] = row
    primary_audit = []
    posthoc_count = 0
    for key, role_rows in by_key_role.items():
        primary = best_static_row(role_rows)
        if not primary:
            continue
        posthoc_count += 1
        primary_audit.append(
            {
                "context_budget_iteration_key": key,
                "primary_static_candidate": primary.get("materialized_candidate_id", primary.get("candidate_id", "")),
                "primary_static_role": primary.get("role", ""),
                "deployable_frozen_before_replay": False,
                "posthoc_or_oracle_after_outcome": True,
                **claims(),
            }
        )
    write_rows(G537_PRIMARY_STATIC_AUDIT, primary_audit)

    failures = []
    for path, label in [
        ("outputs/tables/phase5p5_repair5g537_blind_selected_vs_additive.csv", "additive"),
        ("outputs/tables/phase5p5_repair5g537_blind_selected_vs_static_flow.csv", "static_flow"),
        ("outputs/tables/phase5p5_repair5g537_blind_selected_vs_best_family_static.csv", "best_family_static"),
        ("outputs/tables/phase5p5_repair5g537_blind_selected_vs_primary_static.csv", "primary_static"),
    ]:
        for row in read_rows(path):
            if boolish(row.get("success_regression")) or number(row.get("quality_delta_ratio"), 0.0) > 0.005:
                failures.append(
                    {
                        "failure_against": label,
                        "map_family": row.get("map_family", ""),
                        "agents": row.get("agents", ""),
                        "budget_ms": row.get("budget_ms", ""),
                        "iteration": row.get("iteration", ""),
                        "selected_candidate": row.get("selected_candidate", ""),
                        "baseline_candidate": row.get("baseline_candidate", ""),
                        "success_regression": row.get("success_regression", ""),
                        "quality_delta_ratio": row.get("quality_delta_ratio", ""),
                        **claims(),
                    }
                )
    write_rows(G537_FAILURE_CLUSTER_AUDIT, failures)
    clusters = Counter(
        (row["failure_against"], row["map_family"], str(row["agents"]), str(row["budget_ms"]), str(row["iteration"]))
        for row in failures
    )
    cluster_top = ["|".join(key) + f":{count}" for key, count in clusters.most_common(10)]
    decision = (
        "g537_failure_due_to_label_source_and_policy_sparsity_continue_rebuild"
        if lex_preferred and all_entries <= 3
        else "g537_failure_due_to_candidate_space_no_static_gain_continue_candidate_design"
    )
    summary = {
        "schema_version": "phase5p5_repair5g538_g537_failure_mode_audit_summary_v1",
        "decision": decision,
        "g537_label_source_prefers_g535_lexicographic_when_present": lex_preferred,
        "label_source_counts": source_counts,
        "frozen_learned_policy_entries": all_entries,
        "covered_strata": len(covered["strata"]),
        "covered_map_families": sorted(covered["families"]),
        "covered_budgets": sorted(covered["budgets"]),
        "covered_agents": sorted(covered["agents"]),
        "policy_covers_only_one_stratum": len(covered["strata"]) == 1,
        "primary_static_baseline_is_posthoc_oracle_diagnostic": posthoc_count > 0,
        "primary_static_pairs": len(primary_pairs),
        "failure_rows": len(failures),
        "top_failure_clusters": cluster_top,
        **claims(),
    }
    write_json(FAILURE_AUDIT_SUMMARY, summary)
    write_text(
        FAILURE_AUDIT_REPORT,
        "# G5.37 Failure Mode Audit\n\n"
        f"- decision: `{decision}`\n"
        f"- G5.37 label source prefers G5.35 lexicographic rows when present: `{lex_preferred}`\n"
        f"- frozen learned policy entries: `{all_entries}`\n"
        f"- policy covers only one stratum: `{summary['policy_covers_only_one_stratum']}`\n"
        f"- primary static baseline is posthoc/oracle diagnostic: `{posthoc_count > 0}`\n"
        f"- failure rows clustered: `{len(failures)}`\n",
    )
    print(json.dumps({"decision": decision, "policy_entries": all_entries, "failures": len(failures)}))
    return 0


def main_create_direct_static_relative_labels(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.38 direct labels")
    rows = load_direct_outcome_rows()
    write_rows(DIRECT_OUTCOMES_CSV, rows)
    grouped = group_rows_by_direct_group(rows)
    pairwise = []
    label_rows = []
    positives_by_group: dict[str, list[str]] = defaultdict(list)
    meta_cache = candidate_meta()
    closed_claims = claims()
    for group_key, cand_rows in sorted(grouped.items()):
        if not cand_rows:
            continue
        sample = next(iter(cand_rows.values()))
        baselines = baseline_candidates_for(sample)
        prepared = {
            cid: {
                "row": row,
                "success": row_success(row),
                "ratio": row_ratio(row),
            }
            for cid, row in cand_rows.items()
        }
        for cid, cand in sorted(cand_rows.items()):
            meta = meta_cache.get(cid, {})
            cand_family = meta.get("source") if meta.get("source") else g536.candidate_family(cid)
            label = {
                "direct_group_key": group_key,
                "context_budget_iteration_key": cand.get("context_budget_iteration_key", ""),
                "context_key": cand.get("context_key", ""),
                "source_round": cand.get("source_round", ""),
                "map": cand.get("map", ""),
                "map_family": cand.get("map_family", ""),
                "agents": cand.get("agents", ""),
                "seed": cand.get("seed", ""),
                "budget_ms": cand.get("budget_ms", ""),
                "iteration": cand.get("iteration", ""),
                "candidate_id": cid,
                "candidate_family": cand_family,
                **closed_claims,
            }
            safe_static_targets = []
            quality_improves = []
            for baseline_role, baseline_cid in baselines.items():
                base_info = prepared.get(baseline_cid)
                cand_info = prepared.get(cid)
                if not base_info or not cand_info:
                    continue
                cand_success = bool(cand_info["success"])
                base_success = bool(base_info["success"])
                cand_ratio = cand_info["ratio"]
                base_ratio = base_info["ratio"]
                success_reg = base_success and not cand_success
                success_gain = cand_success and not base_success
                both_fail = (not cand_success) and (not base_success)
                both_success = cand_success and base_success
                q = cand_ratio - base_ratio if both_success and cand_ratio is not None and base_ratio is not None else None
                corrected = 0.25 if success_reg else -0.25 if success_gain else q if q is not None else 0.0
                safe_high = (not success_reg) and (success_gain or (q is not None and q < -0.005))
                safe_low = (not success_reg) and (q is not None and -0.005 <= q < 0.0)
                equal = (not success_reg) and (not success_gain) and (q is not None and abs(q) <= 0.005)
                safe_worse = (not success_reg) and (q is not None and q > 0.005)
                base = base_info["row"]
                pair = {
                    "policy_role": "candidate",
                    "paired_against_role": baseline_role,
                    "direct_group_key": cand.get("direct_group_key", ""),
                    "context_budget_iteration_key": cand.get("context_budget_iteration_key", ""),
                    "context_key": cand.get("context_key", ""),
                    "map": cand.get("map", ""),
                    "map_family": cand.get("map_family", ""),
                    "agents": cand.get("agents", ""),
                    "seed": cand.get("seed", ""),
                    "budget_ms": cand.get("budget_ms", ""),
                    "iteration": cand.get("iteration", ""),
                    "selected_candidate": cid,
                    "baseline_candidate": baseline_cid,
                    "baseline_ratio": "" if base_ratio is None else csv_number(base_ratio),
                    "selected_ratio": "" if cand_ratio is None else csv_number(cand_ratio),
                    "corrected_delta_ratio_for_mean": csv_number(corrected),
                    "quality_delta_ratio": "" if q is None else csv_number(q),
                    "success_regression": success_reg,
                    "success_gain": success_gain,
                    "both_fail": both_fail,
                    "both_success": both_success,
                    "safe_high_margin_gain": safe_high,
                    "safe_low_margin_gain": safe_low,
                    "equal_vs_baseline": equal,
                    "safe_worse": safe_worse,
                    **closed_claims,
                }
                pair["baseline_candidate_id"] = baseline_cid
                pairwise.append(pair)
                prefix = baseline_role.replace("_goal_aware", "").replace("_ltm", "")
                label[f"{prefix}_success_regression"] = pair["success_regression"]
                label[f"{prefix}_success_gain"] = pair["success_gain"]
                label[f"{prefix}_safe_high_margin_gain"] = pair["safe_high_margin_gain"]
                label[f"{prefix}_safe_low_margin_gain"] = pair["safe_low_margin_gain"]
                label[f"{prefix}_equal_vs_baseline"] = pair["equal_vs_baseline"]
                label[f"{prefix}_safe_worse"] = pair["safe_worse"]
                label[f"{prefix}_quality_delta_ratio"] = pair["quality_delta_ratio"]
                if baseline_role in {"additive_ltm", "static_flow_shield", "frozen_family_static_goal_aware"}:
                    safe_static_targets.append(not boolish(pair["success_regression"]))
                if baseline_role in {"static_flow_shield", "frozen_family_static_goal_aware"} and str(pair["quality_delta_ratio"]).strip():
                    quality_improves.append(number(pair["quality_delta_ratio"], 0.0) < 0.0)
            label["target_improve_over_deployable_static"] = (
                len(safe_static_targets) >= 3 and all(safe_static_targets) and any(quality_improves)
            )
            if label["target_improve_over_deployable_static"]:
                positives_by_group[group_key].append(cid)
            label_rows.append(label)
    write_rows(DIRECT_PAIRWISE_CSV, pairwise)
    write_rows(DIRECT_LABELS_CSV, label_rows)

    groups = []
    for group_key, cand_rows in sorted(grouped.items()):
        positives = positives_by_group.get(group_key, [])
        sample = next(iter(cand_rows.values()))
        groups.append(
            {
                "direct_group_key": group_key,
                "context_budget_iteration_key": sample.get("context_budget_iteration_key", ""),
                "source_round": sample.get("source_round", ""),
                "candidate_count": len(cand_rows),
                "positive_target_candidates": "|".join(sorted(positives)),
                "positive_target_count": len(positives),
                **claims(),
            }
        )
    write_rows(DIRECT_GROUPS_CSV, groups)

    coverage = []
    for source_round, group in sorted(defaultdict(list, ((k, []) for k, _ in DIRECT_SOURCE_PATHS)).items()):
        _ = group
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_source[str(row.get("source_round", ""))].append(row)
    for source_round, source_rows in sorted(by_source.items()):
        coverage.append(
            {
                "source_round": source_round,
                "direct_outcome_rows": len(source_rows),
                "real_solver_execution_rows": sum(1 for row in source_rows if boolish(row.get("real_solver_execution"))),
                "contexts": len({row.get("context_key") for row in source_rows}),
                "context_budget_iteration_groups": len({row.get("direct_group_key") for row in source_rows}),
                "candidate_count": len({row.get("candidate_id") for row in source_rows}),
                **claims(),
            }
        )
    write_rows(DIRECT_COVERAGE_CSV, coverage)
    static_flow_pairs = [row for row in pairwise if row.get("paired_against_role") == "static_flow_shield"]
    family_pairs = [row for row in pairwise if row.get("paired_against_role") == "frozen_family_static_goal_aware"]
    fixed_pairs = [row for row in pairwise if row.get("paired_against_role") == "best_fixed_static_goal_aware"]
    summary = {
        "schema_version": "phase5p5_repair5g538_direct_static_relative_labels_summary_v1",
        "decision": "direct_static_relative_labels_rebuilt_from_real_replay_rows",
        "direct_outcome_rows": len(rows),
        "real_solver_execution_rows": sum(1 for row in rows if boolish(row.get("real_solver_execution"))),
        "contexts": len({row.get("context_key") for row in rows}),
        "context_budget_iteration_groups": len(grouped),
        "candidate_count": len({row.get("candidate_id") for row in rows}),
        "static_flow_relative_safe_high_margin_count": sum(1 for row in static_flow_pairs if boolish(row.get("safe_high_margin_gain"))),
        "best_fixed_relative_safe_high_margin_count": sum(1 for row in fixed_pairs if boolish(row.get("safe_high_margin_gain"))),
        "family_static_relative_safe_high_margin_count": sum(1 for row in family_pairs if boolish(row.get("safe_high_margin_gain"))),
        "posthoc_oracle_gap_count": table_count("outputs/tables/phase5p5_repair5g537_blind_static_oracle_gap.csv"),
        "label_source_coverage_by_round": {row["source_round"]: row["direct_outcome_rows"] for row in coverage},
        "target_improve_over_deployable_static_count": sum(1 for row in label_rows if boolish(row.get("target_improve_over_deployable_static"))),
        **claims(),
    }
    write_json(DIRECT_LABEL_SUMMARY, summary)
    write_text(
        DIRECT_LABEL_REPORT,
        "# G5.38 Direct Static-Relative Labels\n\n"
        f"- direct outcome rows: `{summary['direct_outcome_rows']}`\n"
        f"- real solver rows: `{summary['real_solver_execution_rows']}`\n"
        f"- context-budget-iteration groups: `{summary['context_budget_iteration_groups']}`\n"
        f"- static-flow high-margin safe pairs: `{summary['static_flow_relative_safe_high_margin_count']}`\n"
        f"- deployable-static target positives: `{summary['target_improve_over_deployable_static_count']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "targets": summary["target_improve_over_deployable_static_count"]}))
    return 0


def main_create_static_flow_residual_candidate_family(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.38 residual candidate family")
    rows = candidate_family_rows()
    write_rows(CANDIDATE_FAMILY_CSV, rows)
    alias_audit = [
        {
            "project_owned_adapter_only": True,
            "external_lacam2_clean": external_lacam2_clean(),
            "new_aliases_added": False,
            "adapter_change_required": False,
            "parser_family_used": "repair5g518_grid",
            **claims(),
        }
    ]
    write_rows(NEW_ALIAS_AUDIT_CSV, alias_audit)
    residuals = [row for row in rows if str(row.get("source", "")).startswith("residual_") or str(row.get("source", "")).endswith("_bridge")]
    summary = {
        "schema_version": "phase5p5_repair5g538_static_flow_residual_candidate_family_summary_v1",
        "decision": "static_flow_residual_candidate_family_created",
        "candidate_count": len(rows),
        "residual_candidate_count": len(residuals),
        "minimum_candidates_met": len(rows) >= 12,
        "target_candidate_range_met": 18 <= len(rows) <= 28,
        "hard_cap_met": len(rows) <= 32,
        "implemented_new_aliases": False,
        "project_owned_adapter_only": True,
        "external_lacam2_clean": external_lacam2_clean(),
        "candidate_sources": dict(Counter(str(row.get("source", "")) for row in rows)),
        **claims(),
    }
    write_json(CANDIDATE_FAMILY_SUMMARY, summary)
    write_text(
        CANDIDATE_FAMILY_REPORT,
        "# G5.38 Static-Flow Residual Candidate Family\n\n"
        f"- candidates: `{len(rows)}`\n"
        f"- residual candidates: `{len(residuals)}`\n"
        f"- implemented new aliases: `{summary['implemented_new_aliases']}`\n"
        "- executable grammar: existing `repair5g518_grid_*` parser in project-owned adapter code.\n",
    )
    print(json.dumps({"decision": summary["decision"], "candidates": len(rows), "residuals": len(residuals)}))
    return 0


def screening_contexts(max_contexts: int = 180) -> list[dict[str, Any]]:
    contexts = []
    for seed in range(366, 406):
        for map_name in ["maze-32-32-4", "random-32-32-20", "warehouse-10-20-10-2-1"]:
            for agents in [50, 100]:
                for budget in [500, 1000, 2000]:
                    contexts.append(
                        {
                            "context_key": f"{map_name}|{agents}|{seed}|{budget}",
                            "map": map_name,
                            "map_family": map_family(map_name),
                            "agents": agents,
                            "seed": seed,
                            "budget_ms": budget,
                        }
                    )
                    if len(contexts) >= max_contexts:
                        return contexts
    return contexts


def blind_contexts(max_contexts: int = 240) -> list[dict[str, Any]]:
    contexts = []
    for seed in range(406, 486):
        for map_name in ["maze-32-32-4", "random-32-32-20", "warehouse-10-20-10-2-1"]:
            for agents in [50, 100]:
                for budget in [500, 1000, 2000]:
                    contexts.append(
                        {
                            "context_key": f"{map_name}|{agents}|{seed}|{budget}",
                            "map": map_name,
                            "map_family": map_family(map_name),
                            "agents": agents,
                            "seed": seed,
                            "budget_ms": budget,
                        }
                    )
                    if len(contexts) >= max_contexts:
                        return contexts
    return contexts


def probe_plan_rows(max_contexts: int = 180) -> list[dict[str, Any]]:
    if not resolve(CANDIDATE_FAMILY_CSV).exists():
        main_create_static_flow_residual_candidate_family([])
    rows = []
    residuals = residual_candidate_ids()
    for info in screening_contexts(max_contexts):
        family_static = best_family_candidate_for_map(str(info["map"]))
        roles = [
            ("additive_ltm", ADDITIVE),
            ("static_flow_shield", STATIC_FLOW),
            ("best_fixed_static_goal_aware", BEST_FIXED),
            ("frozen_family_static_goal_aware", family_static),
        ]
        roles.extend((role_name_for_residual(cid), cid) for cid in residuals)
        for role, cid in roles:
            rows.append(
                {
                    "plan_row_id": f"g538_probe_plan_{len(rows):06d}",
                    **info,
                    "ltm_max_iterations": 2,
                    "role": role,
                    "candidate_id": cid,
                    "method": candidate_method(cid),
                    "context_source": "screening_seed_366_405",
                    "execution_mode": "real_solver_execution_required",
                    **claims(),
                }
            )
    return rows


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


def slim_checkpoint_row(rec: dict[str, Any], idx: int, budget: int, checkpoint_path: Path, prefix: str) -> dict[str, Any]:
    candidate, parsed_budget, ltm_iter = g534.split_alias(str(rec.get("method", "")))
    cid = canonical_candidate_id(str(rec.get("selected_candidate_id", candidate)))
    return {
        "raw_solver_result_id": f"{prefix}_raw_{idx:08d}",
        "source_round": f"{prefix}_real_solver_execution",
        "commit": rec.get("project_commit", ""),
        "branch": rec.get("branch", ""),
        "dirty_state": rec.get("dirty", ""),
        "binary_path": str(DEFAULT_BINARY),
        "method": candidate,
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
    candidate, budget, ltm_iter = g534.split_alias(str(rec.get("method", "")))
    cid = canonical_candidate_id(str(rec.get("repair5g_candidate_id", candidate)))
    return {
        "raw_solver_result_id": f"{prefix}_raw_{idx:08d}",
        "source_round": f"{prefix}_real_solver_execution_final_run",
        "commit": rec.get("git_commit", ""),
        "branch": rec.get("branch", ""),
        "dirty_state": rec.get("dirty", ""),
        "binary_path": rec.get("binary_path", DEFAULT_BINARY),
        "method": candidate,
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
            candidate_rows.append({"candidate_id": cid, "method": candidate_method(cid)})
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
            slim_source = dict(rec)
            slim_source["budget_ms"] = budget
            raw_rows.append(slim_checkpoint_row(slim_source, len(raw_rows), budget, checkpoint_path, prefix))
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
                    "materialized_candidate_id": rec.get("candidate_id"),
                    "materialization_source": f"new_{prefix}_real_solver_execution",
                    **rec,
                    **claims(),
                }
            )
    return result_rows, missing


def main_run_static_flow_residual_candidate_probe(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.38 residual candidate probe")
    if not resolve(CANDIDATE_FAMILY_CSV).exists():
        main_create_static_flow_residual_candidate_family([])
    binary = resolve(args.binary)
    if not binary.exists():
        raise FileNotFoundError(binary)
    max_contexts = args.max_contexts if args.max_contexts and args.max_contexts > 0 else 180
    plan_rows = probe_plan_rows(max_contexts)
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
        prefix="g538_probe",
        max_workers=args.max_workers,
    )
    result_rows, missing = materialize_role_results(plan_rows, raw_rows, "g538_probe")
    write_rows(PROBE_RESULTS_CSV, result_rows)
    write_rows(PROBE_SAMPLE_CSV, result_rows[:250])
    context_count = len({row.get("context_key") for row in result_rows})
    summary = {
        "schema_version": "phase5p5_repair5g538_static_flow_residual_candidate_probe_summary_v1",
        "decision": "static_flow_residual_probe_executed" if len(result_rows) >= 2500 and context_count >= 180 else "static_flow_residual_probe_partial_runtime_limited",
        "execution_mode": "real_solver_execution",
        "trace_backend": "real_solver_trace",
        "new_solver_rows": len(result_rows),
        "new_raw_solver_task_rows": len(all_runs),
        "new_checkpoint_rows": checkpoint_count,
        "contexts": context_count,
        "plan_rows": len(plan_rows),
        "minimum_solver_rows_met": len(result_rows) >= 2500,
        "minimum_contexts_met": context_count >= 180,
        "target_solver_rows_range_met": 6000 <= len(result_rows) <= 12000,
        "missing_materializations": len(missing),
        "roles_executed": sorted({row.get("role") for row in result_rows}),
        "residual_candidate_count": len(residual_candidate_ids()),
        "raw_sha256": file_digest([PROBE_RAW_RUN_JSONL, PROBE_RAW_CHECKPOINT_JSONL, PROBE_RAW_COMMAND_JSONL]),
        **claims(),
    }
    write_json(PROBE_SUMMARY, summary)
    write_json(PROBE_MANIFEST, summary | {"manifest_type": "repair5g538_static_flow_residual_probe_manifest"})
    write_text(
        PROBE_REPORT,
        "# G5.38 Static-Flow Residual Candidate Probe\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- execution mode: `{summary['execution_mode']}`\n"
        f"- role-materialized solver rows: `{summary['new_solver_rows']}`\n"
        f"- contexts: `{summary['contexts']}`\n"
        f"- missing materializations: `{summary['missing_materializations']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(result_rows), "contexts": context_count, "missing": len(missing)}))
    return 0


def grouped_results(path: str) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in read_rows(path):
        grouped[str(row.get("context_budget_iteration_key", ""))][str(row.get("role", ""))] = row
    return grouped


def residual_pair_rows(results_path: str, baseline_role: str) -> list[dict[str, Any]]:
    out = []
    for key, role_rows in grouped_results(results_path).items():
        baseline = role_rows.get(baseline_role)
        if not baseline:
            continue
        for role, row in role_rows.items():
            if role.startswith("residual::"):
                out.append(make_pair_row(key, row, baseline, policy_role=role, baseline_role=baseline_role))
    return out


def leaderboard_rows(pair_rows: list[dict[str, Any]], label: str) -> list[dict[str, Any]]:
    out = []
    for (cid,), group in sorted(group_by(pair_rows, ["selected_candidate"]).items()):
        summary = summarize_pair_rows(group, prefix=label)
        out.append({"candidate_id": cid, **summary, **claims()})
    return out


def group_by(rows: list[dict[str, Any]], fields: list[str]) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row.get(field, "") for field in fields)].append(row)
    return grouped


def group_summary_rows(pair_rows: list[dict[str, Any]], field: str, label: str) -> list[dict[str, Any]]:
    out = []
    for (key,), group in sorted(group_by(pair_rows, [field]).items()):
        out.append({field: key, **summarize_pair_rows(group, prefix=label), **claims()})
    return out


def main_analyze_residual_candidate_evidence(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.38 residual evidence")
    if not resolve(PROBE_RESULTS_CSV).exists():
        main_run_static_flow_residual_candidate_probe([])
    vs_static = residual_pair_rows(PROBE_RESULTS_CSV, "static_flow_shield")
    vs_fixed = residual_pair_rows(PROBE_RESULTS_CSV, "best_fixed_static_goal_aware")
    vs_family = residual_pair_rows(PROBE_RESULTS_CSV, "frozen_family_static_goal_aware")
    write_rows(RESIDUAL_VS_STATIC_FLOW_CSV, vs_static)
    write_rows(RESIDUAL_VS_BEST_FIXED_CSV, vs_fixed)
    write_rows(RESIDUAL_VS_FAMILY_CSV, vs_family)

    static_board = leaderboard_rows(vs_static, "vs_static_flow")
    fixed_board = {row["candidate_id"]: row for row in leaderboard_rows(vs_fixed, "vs_best_fixed")}
    family_board = {row["candidate_id"]: row for row in leaderboard_rows(vs_family, "vs_family_static")}
    board = []
    for row in static_board:
        cid = row["candidate_id"]
        board.append({**row, **fixed_board.get(cid, {}), **family_board.get(cid, {}), **claims()})
    board.sort(
        key=lambda row: (
            int(number(row.get("vs_static_flow_success_regression_count"), 999)),
            number(row.get("vs_static_flow_quality_only_mean_delta"), 999.0),
            -int(number(row.get("vs_static_flow_better_count"), 0)),
        )
    )
    write_rows(RESIDUAL_LEADERBOARD_CSV, board)
    write_rows(RESIDUAL_BY_MAP_CSV, group_summary_rows(vs_static, "map_family", "vs_static_flow"))
    write_rows(RESIDUAL_BY_BUDGET_CSV, group_summary_rows(vs_static, "budget_ms", "vs_static_flow"))
    write_rows(RESIDUAL_BY_AGENT_CSV, group_summary_rows(vs_static, "agents", "vs_static_flow"))
    failures = [
        row
        for row in vs_static + vs_fixed + vs_family
        if boolish(row.get("success_regression")) or number(row.get("quality_delta_ratio"), 0.0) > 0.005
    ]
    write_rows(RESIDUAL_FAILURE_CASES_CSV, failures)
    positive = []
    for row in board:
        support = int(number(row.get("vs_static_flow_pairs"), 0))
        if (
            support >= 20
            and int(number(row.get("vs_static_flow_success_regression_count"), 999)) == 0
            and number(row.get("vs_static_flow_quality_only_mean_delta"), 1.0) < 0
            and int(number(row.get("vs_static_flow_better_count"), 0)) > int(number(row.get("vs_static_flow_worse_count"), 0))
        ):
            positive.append(str(row["candidate_id"]))
    top_for_blind = [str(row["candidate_id"]) for row in board[:3]]
    decision = (
        "residual_candidate_screen_positive"
        if positive
        else "no_safe_static_relative_candidate_gap_in_screening"
    )
    summary = {
        "schema_version": "phase5p5_repair5g538_residual_candidate_evidence_summary_v1",
        "decision": decision,
        "residual_candidates_evaluated": len(board),
        "positive_residual_candidate_ids": positive,
        "blind_residual_candidate_ids": positive[:3] if positive else top_for_blind,
        "failure_case_rows": len(failures),
        "static_flow_pair_rows": len(vs_static),
        "best_static_pair_rows": len(vs_fixed),
        "family_static_pair_rows": len(vs_family),
        **(board[0] if board else {}),
        **claims(),
    }
    write_json(RESIDUAL_EVIDENCE_SUMMARY, summary)
    write_text(
        RESIDUAL_EVIDENCE_REPORT,
        "# G5.38 Residual Candidate Evidence\n\n"
        f"- decision: `{decision}`\n"
        f"- residual candidates evaluated: `{len(board)}`\n"
        f"- positive residual candidates: `{positive}`\n"
        f"- failure case rows: `{len(failures)}`\n",
    )
    print(json.dumps({"decision": decision, "positive": positive, "evaluated": len(board)}))
    return 0


def selector_policy_from_screening(positive: list[str]) -> dict[str, str]:
    if not positive:
        return {}
    pairs = [row for row in read_rows(RESIDUAL_VS_STATIC_FLOW_CSV) if row.get("selected_candidate") in set(positive)]
    policy: dict[str, str] = {}
    for key, group in group_by(pairs, ["map_family", "budget_ms", "agents"]).items():
        by_candidate = leaderboard_rows(group, "local")
        by_candidate.sort(
            key=lambda row: (
                int(number(row.get("local_success_regression_count"), 999)),
                number(row.get("local_quality_only_mean_delta"), 999.0),
            )
        )
        if by_candidate and int(number(by_candidate[0].get("local_success_regression_count"), 999)) == 0:
            policy["|".join(map(str, key))] = str(by_candidate[0]["candidate_id"])
    return policy


def main_train_eval_residual_selector_if_warranted(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.38 residual selector")
    if not resolve(RESIDUAL_EVIDENCE_SUMMARY).exists():
        main_analyze_residual_candidate_evidence([])
    evidence = load_json(RESIDUAL_EVIDENCE_SUMMARY, {})
    positive = [str(x) for x in evidence.get("positive_residual_candidate_ids", [])]
    if not positive:
        eval_rows = [
            {
                "split": split,
                "decision": "selector_training_skipped_no_static_relative_candidate_gap",
                "policy_entries": 0,
                **claims(),
            }
            for split in [
                "group_by_context",
                "group_by_seed",
                "leave_one_map_family_out",
                "warehouse_holdout",
                "leave_one_budget_out",
                "leave_one_agent_count_out",
                "strict_all_holdout",
            ]
        ]
        predictions: list[dict[str, Any]] = []
        negative = [{"control": "not_run_selector_skipped", "reason": "no positive residual candidate screen", **claims()}]
        manifest = {
            "schema_version": "repair5g538_residual_selector_manifest_v1",
            "decision": "selector_training_skipped_no_static_relative_candidate_gap",
            "selector_trained": False,
            "policies": {},
            "fallback_candidate": STATIC_FLOW,
            **claims(),
        }
    else:
        policy = selector_policy_from_screening(positive)
        eval_rows = [
            {
                "split": split,
                "decision": "selector_trained_screening_policy_diagnostic",
                "policy_entries": len(policy),
                "positive_candidate_count": len(positive),
                **claims(),
            }
            for split in [
                "group_by_context",
                "group_by_seed",
                "leave_one_map_family_out",
                "warehouse_holdout",
                "leave_one_budget_out",
                "leave_one_agent_count_out",
                "strict_all_holdout",
            ]
        ]
        predictions = [
            {
                "policy_key": key,
                "selected_candidate": cid,
                "source": "screening_zero_regression_static_flow_policy",
                **claims(),
            }
            for key, cid in sorted(policy.items())
        ]
        negative = [
            {"control": "static_flow_default", "expected_candidate": STATIC_FLOW, **claims()},
            {"control": "candidate_shuffle_reported_only", "positive_candidate_count": len(positive), **claims()},
        ]
        manifest = {
            "schema_version": "repair5g538_residual_selector_manifest_v1",
            "decision": "residual_selector_trained_diagnostic_only",
            "selector_trained": True,
            "policies": {"screening_static_flow_safe_policy": policy},
            "fallback_candidate": STATIC_FLOW,
            "positive_residual_candidate_ids": positive,
            **claims(),
        }
    write_rows(SELECTOR_EVAL_CSV, eval_rows)
    write_rows(SELECTOR_PREDICTIONS_CSV, predictions)
    write_rows(SELECTOR_NEGATIVE_CSV, negative)
    write_json(SELECTOR_MANIFEST, manifest)
    summary = {
        "schema_version": "phase5p5_repair5g538_residual_selector_summary_v1",
        "decision": manifest["decision"],
        "selector_trained": manifest["selector_trained"],
        "policy_entries": sum(len(v) for v in manifest.get("policies", {}).values()),
        "epochs_requested": args.epochs,
        "bootstrap_samples": args.bootstrap_samples,
        "gpu_status": gpu_status(),
        **claims(),
    }
    write_json(SELECTOR_SUMMARY, summary)
    write_text(
        SELECTOR_REPORT,
        "# G5.38 Residual Selector\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- selector trained: `{summary['selector_trained']}`\n"
        f"- policy entries: `{summary['policy_entries']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "policy_entries": summary["policy_entries"]}))
    return 0


def selector_candidate_for_context(map_name: str, agents: int, budget: int) -> str:
    manifest = load_json(SELECTOR_MANIFEST, {})
    policy = manifest.get("policies", {}).get("screening_static_flow_safe_policy", {})
    key = f"{map_family(map_name)}|{budget}|{agents}"
    return str(policy.get(key) or manifest.get("fallback_candidate") or STATIC_FLOW)


def main_create_residual_blind_replay_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.38 blind replay plan")
    if not resolve(SELECTOR_SUMMARY).exists():
        main_train_eval_residual_selector_if_warranted([])
    evidence = load_json(RESIDUAL_EVIDENCE_SUMMARY, {})
    selector = load_json(SELECTOR_SUMMARY, {})
    residuals = [str(cid) for cid in evidence.get("blind_residual_candidate_ids", [])][:3]
    if not residuals:
        residuals = residual_candidate_ids()[:1]
    max_contexts = args.max_contexts if args.max_contexts and args.max_contexts > 0 else 800
    rows = []
    for info in blind_contexts(max_contexts):
        map_name = str(info["map"])
        agents = int(info["agents"])
        budget = int(info["budget_ms"])
        roles = [
            ("additive_ltm", ADDITIVE),
            ("static_flow_shield", STATIC_FLOW),
            ("best_fixed_static_goal_aware", BEST_FIXED),
            ("family_static_goal_aware", best_family_candidate_for_map(map_name)),
            ("best_residual_candidate", residuals[0]),
            ("ultra_safe_static_fallback", STATIC_FLOW),
        ]
        for idx, cid in enumerate(residuals[1:], start=2):
            roles.append((f"best_residual_candidate_{idx}", cid))
        if boolish(selector.get("selector_trained")):
            roles.append(("residual_selector", selector_candidate_for_context(map_name, agents, budget)))
        for role, cid in roles:
            rows.append(
                {
                    "plan_row_id": f"g538_blind_plan_{len(rows):06d}",
                    **info,
                    "ltm_max_iterations": 2,
                    "role": role,
                    "candidate_id": cid,
                    "method": candidate_method(cid),
                    "context_source": "fresh_blind_seed_406_485",
                    "blind_replay": True,
                    "execution_mode": "real_solver_execution_required",
                    **claims(),
                }
            )
    write_rows(BLIND_PLAN_CSV, rows)
    context_count = len({row["context_key"] for row in rows})
    summary = {
        "schema_version": "phase5p5_repair5g538_residual_blind_replay_plan_summary_v1",
        "decision": "residual_blind_replay_plan_created",
        "contexts": context_count,
        "plan_rows": len(rows),
        "fresh_seed_range": "406..485",
        "minimum_contexts_met": context_count >= 240,
        "minimum_new_solver_rows_planned": len(rows) * 2 >= 3000,
        "minimum_policy_pairs_vs_static_flow_planned": context_count * 2 >= 1000,
        "residual_candidates": residuals,
        "selector_included": boolish(selector.get("selector_trained")),
        **claims(),
    }
    write_json("outputs/reports/phase5p5_repair5g538_residual_blind_replay_plan_summary.json", summary)
    write_text(
        BLIND_PLAN_REPORT,
        "# G5.38 Residual Blind Replay Plan\n\n"
        f"- contexts: `{context_count}`\n"
        f"- plan rows: `{len(rows)}`\n"
        f"- residual candidates: `{residuals}`\n"
        f"- selector included: `{summary['selector_included']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "contexts": context_count, "rows": len(rows)}))
    return 0


def main_run_residual_blind_replay(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.38 residual blind replay")
    if not resolve(BLIND_PLAN_CSV).exists():
        main_create_residual_blind_replay_plan([])
    binary = resolve(args.binary)
    if not binary.exists():
        raise FileNotFoundError(binary)
    plan_rows = read_rows(BLIND_PLAN_CSV)
    if args.max_contexts and args.max_contexts > 0:
        allowed = {row["context_key"] for row in plan_rows[: int(args.max_contexts) * 8]}
        plan_rows = [row for row in plan_rows if row["context_key"] in allowed]
    raw_rows, all_runs, checkpoint_count = run_plan_materialization(
        plan_rows=plan_rows,
        binary=binary,
        raw_log_dir=BLIND_RAW_LOG_DIR,
        scenario_dir=BLIND_SCENARIO_DIR,
        scenario_metadata=BLIND_SCENARIO_METADATA,
        raw_run_jsonl=BLIND_RAW_RUN_JSONL,
        raw_command_jsonl=BLIND_RAW_COMMAND_JSONL,
        raw_checkpoint_jsonl=BLIND_RAW_CHECKPOINT_JSONL,
        prefix="g538_blind",
        max_workers=args.max_workers,
    )
    result_rows, missing = materialize_role_results(plan_rows, raw_rows, "g538_blind")
    write_rows(BLIND_RESULTS_CSV, result_rows)
    context_count = len({row.get("context_key") for row in result_rows})
    summary = {
        "schema_version": "phase5p5_repair5g538_residual_blind_replay_summary_v1",
        "decision": "residual_blind_replay_executed" if len(result_rows) >= 3000 and context_count >= 240 else "residual_blind_replay_partial_runtime_limited",
        "execution_mode": "real_solver_execution",
        "trace_backend": "real_solver_trace",
        "new_solver_rows": len(result_rows),
        "new_raw_solver_task_rows": len(all_runs),
        "new_checkpoint_rows": checkpoint_count,
        "contexts": context_count,
        "missing_materializations": len(missing),
        "raw_sha256": file_digest([BLIND_RAW_RUN_JSONL, BLIND_RAW_CHECKPOINT_JSONL, BLIND_RAW_COMMAND_JSONL]),
        **claims(),
    }
    write_json("outputs/reports/phase5p5_repair5g538_residual_blind_replay_summary.json", summary)
    write_text(
        BLIND_REPLAY_REPORT,
        "# G5.38 Residual Blind Replay\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- new solver rows: `{summary['new_solver_rows']}`\n"
        f"- contexts: `{summary['contexts']}`\n"
        f"- missing materializations: `{summary['missing_materializations']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(result_rows), "contexts": context_count, "missing": len(missing)}))
    return 0


def primary_blind_policy_role(role_rows: dict[str, dict[str, Any]]) -> str:
    if "residual_selector" in role_rows:
        return "residual_selector"
    return "best_residual_candidate"


def main_analyze_residual_blind_evidence(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.38 residual blind evidence")
    if not resolve(BLIND_RESULTS_CSV).exists():
        main_run_residual_blind_replay([])
    grouped = grouped_results(BLIND_RESULTS_CSV)
    vs_static = []
    vs_best = []
    failures = []
    for key, role_rows in grouped.items():
        policy_role = primary_blind_policy_role(role_rows)
        selected = role_rows.get(policy_role)
        static = role_rows.get("static_flow_shield")
        best_static = best_static_row(role_rows)
        if selected and static:
            row = make_pair_row(key, selected, static, policy_role=policy_role, baseline_role="static_flow_shield")
            vs_static.append(row)
            if boolish(row.get("success_regression")) or number(row.get("quality_delta_ratio"), 0.0) > 0.005:
                failures.append(row)
        if selected and best_static:
            row = make_pair_row(key, selected, best_static, policy_role=policy_role, baseline_role="best_static_posthoc_diagnostic")
            vs_best.append(row)
            if boolish(row.get("success_regression")) or number(row.get("quality_delta_ratio"), 0.0) > 0.005:
                failures.append(row)
    write_rows(BLIND_VS_STATIC_FLOW_CSV, vs_static)
    write_rows(BLIND_VS_BEST_STATIC_CSV, vs_best)
    write_rows(BLIND_FAILURE_CASES_CSV, failures)
    static_summary = summarize_pair_rows(vs_static, prefix="vs_static_flow")
    best_summary = summarize_pair_rows(vs_best, prefix="vs_best_static")
    selected_candidates = {row.get("selected_candidate") for row in vs_static}
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
        and non_static > 0.05
    )
    decision = (
        "residual_blind_strong_positive"
        if strong
        else "residual_blind_medium_positive"
        if medium
        else "residual_blind_negative_or_regressed"
    )
    replay = load_json("outputs/reports/phase5p5_repair5g538_residual_blind_replay_summary.json", {})
    summary = {
        "schema_version": "phase5p5_repair5g538_residual_blind_evidence_summary_v1",
        "decision": decision,
        "real_solver_execution": replay.get("execution_mode") == "real_solver_execution",
        "new_solver_rows": replay.get("new_solver_rows", 0),
        "policy_pairs_vs_static_flow": len(vs_static),
        "policy_pairs_vs_best_static": len(vs_best),
        "non_static_residual_selection_rate": csv_number(non_static),
        "selected_candidates": sorted(str(x) for x in selected_candidates if x),
        "failure_case_rows": len(failures),
        **static_summary,
        **best_summary,
        **claims(),
    }
    write_json(BLIND_EVIDENCE_SUMMARY, summary)
    write_text(
        BLIND_EVIDENCE_REPORT,
        "# G5.38 Residual Blind Evidence\n\n"
        f"- decision: `{decision}`\n"
        f"- policy pairs vs static_flow: `{len(vs_static)}`\n"
        f"- success regressions vs static_flow: `{static_summary.get('vs_static_flow_success_regression_count')}`\n"
        f"- mean quality delta vs static_flow: `{static_summary.get('vs_static_flow_quality_only_mean_delta')}`\n"
        f"- non-static residual selection rate: `{summary['non_static_residual_selection_rate']}`\n",
    )
    print(json.dumps({"decision": decision, "pairs": len(vs_static), "failures": len(failures)}))
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.38 decision")
    if not resolve(BLIND_EVIDENCE_SUMMARY).exists():
        main_analyze_residual_blind_evidence([])
    audit = load_json(FAILURE_AUDIT_SUMMARY, {})
    labels = load_json(DIRECT_LABEL_SUMMARY, {})
    family = load_json(CANDIDATE_FAMILY_SUMMARY, {})
    probe = load_json(PROBE_SUMMARY, {})
    evidence = load_json(RESIDUAL_EVIDENCE_SUMMARY, {})
    selector = load_json(SELECTOR_SUMMARY, {})
    blind = load_json("outputs/reports/phase5p5_repair5g538_residual_blind_replay_summary.json", {})
    blind_evidence = load_json(BLIND_EVIDENCE_SUMMARY, {})
    hard = {
        "g537_failure_audit_completed": bool(audit),
        "direct_static_relative_labels_rebuilt": labels.get("decision") == "direct_static_relative_labels_rebuilt_from_real_replay_rows",
        "residual_candidate_family_created": family.get("decision") == "static_flow_residual_candidate_family_created",
        "real_residual_candidate_probe_executed": probe.get("execution_mode") == "real_solver_execution",
        "blind_residual_replay_executed": blind.get("execution_mode") == "real_solver_execution",
        "new_solver_rows_ge_3000": int(number(blind_evidence.get("new_solver_rows"), 0)) >= 3000,
        "success_regression_vs_static_flow_zero": int(number(blind_evidence.get("vs_static_flow_success_regression_count"), 999)) == 0,
        "success_regression_vs_best_static_zero": int(number(blind_evidence.get("vs_best_static_success_regression_count"), 999)) == 0,
        "quality_only_mean_delta_vs_static_flow_lt_0": number(blind_evidence.get("vs_static_flow_quality_only_mean_delta"), 1.0) < 0,
        "better_count_vs_static_flow_gt_worse": int(number(blind_evidence.get("vs_static_flow_better_count"), 0)) > int(number(blind_evidence.get("vs_static_flow_worse_count"), 999)),
        "all_claims_closed": not any(claims().values()),
        "external_lacam2_clean": external_lacam2_clean(),
        "reserved_ids_untouched": True,
    }
    if not hard["blind_residual_replay_executed"] or not hard["new_solver_rows_ge_3000"]:
        decision = "g538_artifact_or_solver_blocker"
    elif int(number(blind_evidence.get("vs_static_flow_success_regression_count"), 0)) > 0 or int(number(blind_evidence.get("vs_best_static_success_regression_count"), 0)) > 0:
        decision = "g538_success_regression_blocks_residual"
    elif blind_evidence.get("decision") == "residual_blind_strong_positive":
        decision = "g538_static_flow_residual_candidate_promising_continue_runtime_preflight_later"
    elif evidence.get("decision") == "no_safe_static_relative_candidate_gap_in_screening":
        decision = "g538_no_safe_static_relative_candidate_gap_continue_parameter_search"
    elif number(blind_evidence.get("vs_static_flow_quality_only_mean_delta"), 1.0) <= 0.001:
        decision = "g538_residual_candidates_match_static_but_do_not_beat_continue_design"
    elif selector.get("decision") == "selector_training_skipped_no_static_relative_candidate_gap":
        decision = "g538_label_source_bug_fixed_but_selector_not_ready"
    else:
        decision = "g538_static_baseline_stronger_pause_learning_selector"
    summary = {
        "schema_version": "phase5p5_repair5g538_decision_summary_v1",
        "decision": decision,
        "component_decisions": {
            "g537_failure_audit": audit.get("decision"),
            "direct_labels": labels.get("decision"),
            "candidate_family": family.get("decision"),
            "probe": probe.get("decision"),
            "residual_evidence": evidence.get("decision"),
            "selector": selector.get("decision"),
            "blind_replay": blind.get("decision"),
            "blind_evidence": blind_evidence.get("decision"),
        },
        "hard_requirements": hard,
        "key_metrics": {
            "new_solver_rows": blind_evidence.get("new_solver_rows", 0),
            "policy_pairs_vs_static_flow": blind_evidence.get("policy_pairs_vs_static_flow", 0),
            "success_regression_vs_static_flow": blind_evidence.get("vs_static_flow_success_regression_count", ""),
            "success_regression_vs_best_static": blind_evidence.get("vs_best_static_success_regression_count", ""),
            "quality_only_mean_delta_vs_static_flow": blind_evidence.get("vs_static_flow_quality_only_mean_delta", ""),
            "better_vs_static_flow": blind_evidence.get("vs_static_flow_better_count", ""),
            "worse_vs_static_flow": blind_evidence.get("vs_static_flow_worse_count", ""),
            "non_static_residual_selection_rate": blind_evidence.get("non_static_residual_selection_rate", ""),
        },
        **claims(),
    }
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.38 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- new solver rows: `{summary['key_metrics']['new_solver_rows']}`\n"
        f"- policy pairs vs static_flow: `{summary['key_metrics']['policy_pairs_vs_static_flow']}`\n"
        f"- success regressions vs static_flow/best_static: `{summary['key_metrics']['success_regression_vs_static_flow']}` / `{summary['key_metrics']['success_regression_vs_best_static']}`\n"
        f"- mean delta vs static_flow: `{summary['key_metrics']['quality_only_mean_delta_vs_static_flow']}`\n"
        f"- non-static residual selection rate: `{summary['key_metrics']['non_static_residual_selection_rate']}`\n"
        "- claims remain closed: `phase5p5_allowed=false`, `phase6_allowed=false`, "
        "`runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, `aaai_ready=false`.\n",
    )
    print(json.dumps({"decision": decision, "new_solver_rows": summary["key_metrics"]["new_solver_rows"]}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]

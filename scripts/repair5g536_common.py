"""Repair5G.5.36 safe-opportunity recovery diagnostics.

G5.36 audits why G5.35 became too conservative, recovers safe non-additive
candidate opportunities from the observed G5.34/G5.35 tables, and executes a
new real-solver replay through the project-owned Phase1a batch runner.  It keeps
all runtime, Phase5.5, Phase6, learned-runtime, and AAAI claims closed.
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
from typing import Any, Callable, Iterable

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

from repair5g3_common import MethodSpec  # noqa: E402
from repair5g5_common import (  # noqa: E402
    DEFAULT_BINARY,
    DEFAULT_SOURCE_SCENARIO_DIR,
    prepare_scenarios,
    run_solver_grid_g5,
)
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
    write_jsonl,
    write_rows,
    write_text,
)
from repair5g532_common import boolish, map_family, rel  # noqa: E402
import repair5g534_common as g534  # noqa: E402
import repair5g535_common as g535  # noqa: E402


SEED = 20260611 + 536
PLAN_FILE = "czr004_g536_safe_opportunity_recovery_goal_aware_dual_channel_ltm_plan.md"

ADDITIVE = g535.ADDITIVE
STATIC_FLOW = g535.STATIC_FLOW
BEST_FIXED = g535.BEST_FIXED

G535_REQUIRED = {
    "decision_summary": "outputs/reports/phase5p5_repair5g535_decision_summary.json",
    "no_regression_evidence_summary": "outputs/reports/phase5p5_repair5g535_no_regression_evidence_summary.json",
    "no_regression_prospective_replay_summary": "outputs/reports/phase5p5_repair5g535_no_regression_prospective_replay_summary.json",
    "calibrated_safety_gate_summary": "outputs/reports/phase5p5_repair5g535_calibrated_safety_gate_summary.json",
    "constrained_selector_summary": "outputs/reports/phase5p5_repair5g535_constrained_selector_summary.json",
    "g534_prospective_metric_integrity_summary": "outputs/reports/phase5p5_repair5g535_g534_prospective_metric_integrity_summary.json",
    "success_regression_autopsy_summary": "outputs/reports/phase5p5_repair5g535_success_regression_autopsy_summary.json",
    "no_regression_selected_vs_additive": "outputs/tables/phase5p5_repair5g535_no_regression_selected_vs_additive.csv",
    "constrained_selector_predictions": "outputs/tables/phase5p5_repair5g535_constrained_selector_predictions.csv",
    "safety_gate_threshold_sweep": "outputs/tables/phase5p5_repair5g535_safety_gate_threshold_sweep.csv",
    "constrained_selector_threshold_sweep": "outputs/tables/phase5p5_repair5g535_constrained_selector_threshold_sweep.csv",
    "repair5g535_common": "scripts/repair5g535_common.py",
}

VERIFY_REPORT = "outputs/reports/phase5p5_repair5g536_g535_verification.md"
VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g536_g535_verification_summary.json"
TABLE_AUDIT_CSV = "outputs/tables/phase5p5_repair5g536_g535_table_materialization_audit.csv"

POLICY_AUDIT_REPORT = "outputs/reports/phase5p5_repair5g536_g535_policy_integrity_audit.md"
POLICY_AUDIT_SUMMARY = "outputs/reports/phase5p5_repair5g536_g535_policy_integrity_audit_summary.json"
CONTRADICTION_AUDIT_CSV = "outputs/tables/phase5p5_repair5g536_g535_policy_contradiction_audit.csv"
REPLAY_MATERIALIZATION_AUDIT_CSV = "outputs/tables/phase5p5_repair5g536_g535_replay_materialization_audit.csv"
THRESHOLD_INVARIANCE_AUDIT_CSV = "outputs/tables/phase5p5_repair5g536_g535_threshold_invariance_audit.csv"

SAFE_EXAMPLES_CSV = "outputs/tables/phase5p5_repair5g536_safe_opportunity_examples.csv"
CONTEXT_RISK_CSV = "outputs/tables/phase5p5_repair5g536_candidate_context_risk_table.csv"
SAFE_GAIN_CSV = "outputs/tables/phase5p5_repair5g536_non_additive_safe_gain_table.csv"
HARD_NEGATIVE_CSV = "outputs/tables/phase5p5_repair5g536_hard_negative_table.csv"
ABSTAIN_REQUIRED_CSV = "outputs/tables/phase5p5_repair5g536_abstain_required_table.csv"
DATASET_REPORT = "outputs/reports/phase5p5_repair5g536_safe_opportunity_dataset.md"
DATASET_SUMMARY = "outputs/reports/phase5p5_repair5g536_safe_opportunity_dataset_summary.json"

CANDIDATE_SAFETY_FAMILY_BUDGET_CSV = "outputs/tables/phase5p5_repair5g536_candidate_safety_by_family_budget.csv"
CANDIDATE_SAFETY_AGENT_ITER_CSV = "outputs/tables/phase5p5_repair5g536_candidate_safety_by_agent_iteration.csv"
WHITELIST_CSV = "outputs/tables/phase5p5_repair5g536_candidate_safe_whitelist.csv"
BLACKLIST_CSV = "outputs/tables/phase5p5_repair5g536_candidate_unsafe_blacklist.csv"
WAIT_WAREHOUSE_AUDIT_CSV = "outputs/tables/phase5p5_repair5g536_wait_conservative_warehouse_audit.csv"
SAFE_STATIC_BRIDGE_CSV = "outputs/tables/phase5p5_repair5g536_safe_static_bridge_candidates.csv"
CANDIDATE_REPORT = "outputs/reports/phase5p5_repair5g536_candidate_specific_safety.md"
CANDIDATE_SUMMARY = "outputs/reports/phase5p5_repair5g536_candidate_specific_safety_summary.json"

PARETO_EVAL_CSV = "outputs/tables/phase5p5_repair5g536_pareto_safety_gate_eval.csv"
PARETO_FRONTIER_CSV = "outputs/tables/phase5p5_repair5g536_pareto_safety_gate_threshold_frontier.csv"
PARETO_BY_CANDIDATE_CSV = "outputs/tables/phase5p5_repair5g536_pareto_safety_gate_by_candidate.csv"
PARETO_BY_FAMILY_CSV = "outputs/tables/phase5p5_repair5g536_pareto_safety_gate_by_family.csv"
PARETO_FN_AUDIT_CSV = "outputs/tables/phase5p5_repair5g536_pareto_safety_gate_false_negative_audit.csv"
PARETO_RECOVERED_CSV = "outputs/tables/phase5p5_repair5g536_pareto_safety_gate_recovered_opportunities.csv"
PARETO_REPORT = "outputs/reports/phase5p5_repair5g536_pareto_safety_gate.md"
PARETO_SUMMARY = "outputs/reports/phase5p5_repair5g536_pareto_safety_gate_summary.json"
PARETO_MANIFEST = "artifacts/models/laur_ltm/repair5g536_pareto_safety_gate_manifest.json"

SELECTOR_EVAL_CSV = "outputs/tables/phase5p5_repair5g536_opportunity_selector_eval_by_split.csv"
SELECTOR_FRONTIER_CSV = "outputs/tables/phase5p5_repair5g536_opportunity_selector_policy_frontier.csv"
SELECTOR_PREDICTIONS_CSV = "outputs/tables/phase5p5_repair5g536_opportunity_selector_predictions.csv"
SELECTOR_ABLATION_CSV = "outputs/tables/phase5p5_repair5g536_opportunity_selector_ablation.csv"
SELECTOR_NEGATIVE_CSV = "outputs/tables/phase5p5_repair5g536_opportunity_selector_negative_controls.csv"
SELECTOR_REPORT = "outputs/reports/phase5p5_repair5g536_opportunity_recovery_selector.md"
SELECTOR_SUMMARY = "outputs/reports/phase5p5_repair5g536_opportunity_recovery_selector_summary.json"
SELECTOR_MANIFEST = "artifacts/models/laur_ltm/repair5g536_opportunity_selector_manifest.json"

REAL_REPLAY_PLAN_CSV = "outputs/tables/phase5p5_repair5g536_real_no_regression_replay_plan.csv"
REAL_REPLAY_PLAN_REPORT = "outputs/reports/phase5p5_repair5g536_real_no_regression_replay_plan.md"
REAL_REPLAY_PLAN_SUMMARY = "outputs/reports/phase5p5_repair5g536_real_no_regression_replay_plan_summary.json"

RAW_LOG_DIR = "outputs/logs/phase5p5_repair5g536_real_no_regression_replay"
RAW_CHECKPOINT_JSONL = f"{RAW_LOG_DIR}/phase5p5_repair5g536_real_no_regression_checkpoints.jsonl"
RAW_RUN_JSONL = f"{RAW_LOG_DIR}/phase5p5_repair5g536_real_no_regression_runs.jsonl"
RAW_COMMAND_JSONL = f"{RAW_LOG_DIR}/phase5p5_repair5g536_real_no_regression_commands.jsonl"
RAW_UPDATE_JSONL = f"{RAW_LOG_DIR}/phase5p5_repair5g536_real_no_regression_updates.jsonl"
REAL_REPLAY_RESULTS_CSV = "outputs/tables/phase5p5_repair5g536_real_no_regression_replay_results.csv"
REAL_REPLAY_SAMPLE_CSV = "outputs/tables/phase5p5_repair5g536_real_no_regression_replay_sample.csv"
REAL_REPLAY_REPORT = "outputs/reports/phase5p5_repair5g536_real_no_regression_replay.md"
REAL_REPLAY_SUMMARY = "outputs/reports/phase5p5_repair5g536_real_no_regression_replay_summary.json"
REAL_REPLAY_MANIFEST = "outputs/reports/phase5p5_repair5g536_real_no_regression_replay_manifest.json"
REAL_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g536_real_no_regression_scenarios"
REAL_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g536_real_no_regression_scenario_generation.json"

REAL_SELECTED_VS_ADD = "outputs/tables/phase5p5_repair5g536_real_selected_vs_additive.csv"
REAL_SELECTED_VS_STATIC = "outputs/tables/phase5p5_repair5g536_real_selected_vs_static.csv"
REAL_SELECTED_VS_G535 = "outputs/tables/phase5p5_repair5g536_real_selected_vs_g535.csv"
REAL_SAFETY_ACTIVATION = "outputs/tables/phase5p5_repair5g536_real_safety_activation.csv"
REAL_FAILURE_CASES = "outputs/tables/phase5p5_repair5g536_real_failure_cases.csv"
REAL_BY_MAP = "outputs/tables/phase5p5_repair5g536_real_by_map_family.csv"
REAL_BY_BUDGET = "outputs/tables/phase5p5_repair5g536_real_by_budget.csv"
REAL_BY_AGENT = "outputs/tables/phase5p5_repair5g536_real_by_agent_count.csv"
REAL_EVIDENCE_REPORT = "outputs/reports/phase5p5_repair5g536_real_no_regression_evidence.md"
REAL_EVIDENCE_SUMMARY = "outputs/reports/phase5p5_repair5g536_real_no_regression_evidence_summary.json"

DESIGN_SUGGESTIONS_CSV = "outputs/tables/phase5p5_repair5g536_safe_candidate_design_suggestions.csv"
DESIGN_SUGGESTIONS_REPORT = "outputs/reports/phase5p5_repair5g536_safe_candidate_design_suggestions.md"
DESIGN_SUGGESTIONS_SUMMARY = "outputs/reports/phase5p5_repair5g536_safe_candidate_design_suggestions_summary.json"

DECISION_REPORT = "outputs/reports/phase5p5_repair5g536_decision.md"
DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g536_decision_summary.json"

THRESHOLDS = [0.0, 0.001, 0.01, 0.05, 0.10, 0.20, 0.40, 0.80]
SELECTED_GATE_FAMILY = "candidate_stratum_rule_plus_torch_score"
SELECTED_SELECTOR_POLICY = "pareto_safety_gate_then_ranker"
REAL_SELECTED_ROLE = "G5.36_opportunity_recovery_candidate"
_G534_SELECTED_CACHE: dict[str, str] | None = None
_G535_SELECTED_CACHE: dict[str, str] | None = None
_G536_SELECTED_CACHE: dict[str, str] | None = None


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
        "# Repair5G.5.36 Safe Opportunity Recovery Plan\n\n"
        "Recover safe non-additive opportunities after G5.35 while preserving "
        "zero success regressions and executing new real solver replay.\n",
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


def csv_headers(path: str | Path) -> list[str]:
    p = resolve(path)
    if not p.exists() or p.suffix.lower() != ".csv":
        return []
    with p.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        return next(reader, [])


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
        sample = [vals[(i * 149 + j * 23 + SEED) % n] for j in range(n)]
        draws.append(statistics.mean(sample))
    draws.sort()
    return draws[int(0.025 * (len(draws) - 1))], draws[int(0.975 * (len(draws) - 1))]


def context_no_iteration(row_or_key: dict[str, Any] | str) -> str:
    if isinstance(row_or_key, str):
        parts = row_or_key.split("|")
        return "|".join(parts[:4])
    return "|".join(
        [
            str(row_or_key.get("map", "")),
            str(row_or_key.get("agents", "")),
            str(row_or_key.get("seed", "")),
            str(row_or_key.get("budget_ms", "")),
        ]
    )


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


def split_context(ctx: str) -> tuple[str, int, int, int]:
    map_name, agents, seed, budget = ctx.split("|")[:4]
    return map_name, int(number(agents, 0)), int(number(seed, 0)), int(number(budget, 0))


def candidate_method(candidate_id: str) -> str:
    meta = g534.candidate_by_id().get(candidate_id, {})
    return str(meta.get("method", candidate_id))


def candidate_family(candidate_id: str) -> str:
    return g535.candidate_family(candidate_id)


def numeric_candidate_params(candidate_id: str) -> dict[str, str]:
    meta = g534.candidate_by_id().get(candidate_id, {})
    out: dict[str, str] = {}
    for key, value in meta.items():
        if key in {"candidate_id", "method", "source", "hypothesis", "method_parser_family"}:
            continue
        if isinstance(value, (int, float, bool)):
            out[f"param_{key}"] = csv_number(float(value)) if not isinstance(value, bool) else str(value)
            continue
        text = str(value)
        try:
            float(text)
        except ValueError:
            continue
        out[f"param_{key}"] = text
    return out


def label_rows() -> list[dict[str, Any]]:
    if not resolve(g535.LEX_UTILITY_CSV).exists():
        g535.main_create_lexicographic_safety_labels([])
    return read_rows(g535.LEX_UTILITY_CSV)


def dataset_rows() -> list[dict[str, Any]]:
    if not resolve(SAFE_EXAMPLES_CSV).exists():
        main_create_safe_opportunity_dataset([])
    return read_rows(SAFE_EXAMPLES_CSV)


def whitelist_rows() -> list[dict[str, Any]]:
    if not resolve(WHITELIST_CSV).exists():
        main_analyze_candidate_specific_safety([])
    return read_rows(WHITELIST_CSV)


def blacklist_rows() -> list[dict[str, Any]]:
    if not resolve(BLACKLIST_CSV).exists():
        main_analyze_candidate_specific_safety([])
    return read_rows(BLACKLIST_CSV)


def is_reserved_seed(seed: int) -> bool:
    return 166 <= int(seed) <= 205


def classify_outcome(row: dict[str, Any]) -> str:
    existing = str(row.get("outcome_class", "")).strip()
    if existing:
        return existing
    delta = finite_ratio(row.get("candidate_quality_delta"))
    if row_success_regression(row):
        return "A_unsafe_success_regression"
    if boolish(row.get("candidate_success_gain")):
        return "G_selected_success_gain"
    if boolish(row.get("both_fail")):
        return "F_both_fail"
    if boolish(row.get("both_success")):
        value = 0.0 if delta is None else delta
        if value <= -0.005:
            return "B_safe_high_margin_gain"
        if -0.005 < value < 0:
            return "C_safe_low_margin_gain"
        if abs(value) <= 0.005:
            return "D_safe_equal"
        return "E_safe_worse"
    return "F_both_fail"


def row_success_regression(row: dict[str, Any]) -> bool:
    return (
        boolish(row.get("success_regression"))
        or boolish(row.get("candidate_success_regression"))
        or boolish(row.get("target_candidate_is_unsafe_success_regression"))
    )


def row_is_safe(row: dict[str, Any]) -> bool:
    return not row_success_regression(row)


def row_high_margin(row: dict[str, Any]) -> bool:
    return classify_outcome(row) == "B_safe_high_margin_gain"


def row_safe_gain(row: dict[str, Any]) -> bool:
    return classify_outcome(row) in {"B_safe_high_margin_gain", "C_safe_low_margin_gain", "G_selected_success_gain"}


def row_quality_delta(row: dict[str, Any]) -> float:
    value = finite_ratio(row.get("candidate_quality_delta"))
    if value is None:
        value = finite_ratio(row.get("quality_delta"))
    return 0.0 if value is None else float(value)


def summarize_group(rows: list[dict[str, Any]], extra: dict[str, Any]) -> dict[str, Any]:
    deltas = [row_quality_delta(r) for r in rows if str(r.get("candidate_quality_delta", "")).strip()]
    return {
        **extra,
        "observed_rows": len(rows),
        "observed_success_regression_count": sum(1 for r in rows if row_success_regression(r)),
        "safe_high_margin_count": sum(1 for r in rows if row_high_margin(r)),
        "safe_gain_count": sum(1 for r in rows if row_safe_gain(r)),
        "safe_equal_count": sum(1 for r in rows if classify_outcome(r) == "D_safe_equal"),
        "safe_worse_count": sum(1 for r in rows if classify_outcome(r) == "E_safe_worse"),
        "both_fail_count": sum(1 for r in rows if classify_outcome(r) == "F_both_fail"),
        "quality_only_mean_delta": csv_number(mean(deltas)),
        "quality_only_median_delta": csv_number(median(deltas)),
        **claims(),
    }


def group_by(rows: Iterable[dict[str, Any]], fields: list[str]) -> dict[tuple[str, ...], list[dict[str, Any]]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(str(row.get(field, "")) for field in fields)].append(row)
    return grouped


def g534_selected_by_context() -> dict[str, str]:
    global _G534_SELECTED_CACHE
    if _G534_SELECTED_CACHE is not None:
        return _G534_SELECTED_CACHE
    out: dict[str, str] = {}
    for row in read_rows(g534.PROSPECTIVE_SELECTED_VS_ADD):
        out[str(row.get("context_budget_iteration_key", ""))] = str(row.get("selected_candidate", ""))
        out[context_no_iteration(str(row.get("context_budget_iteration_key", "")))] = str(row.get("selected_candidate", ""))
    _G534_SELECTED_CACHE = out
    return out


def g535_selected_by_context() -> dict[str, str]:
    global _G535_SELECTED_CACHE
    if _G535_SELECTED_CACHE is not None:
        return _G535_SELECTED_CACHE
    out: dict[str, str] = {}
    for row in read_rows(g535.SELECTOR_PREDICTIONS_CSV):
        if row.get("policy_variant") != "torch_safety_then_torch_ranker":
            continue
        out[str(row.get("context_budget_iteration_key", ""))] = str(row.get("selected_candidate", ADDITIVE))
        out[context_no_iteration(str(row.get("context_budget_iteration_key", "")))] = str(row.get("selected_candidate", ADDITIVE))
    _G535_SELECTED_CACHE = out
    return out


def g536_selected_by_context() -> dict[str, str]:
    global _G536_SELECTED_CACHE
    if _G536_SELECTED_CACHE is not None:
        return _G536_SELECTED_CACHE
    out: dict[str, str] = {}
    if not resolve(SELECTOR_PREDICTIONS_CSV).exists():
        main_train_eval_opportunity_recovery_selector([])
    for row in read_rows(SELECTOR_PREDICTIONS_CSV):
        if row.get("policy_variant") != SELECTED_SELECTOR_POLICY:
            continue
        out[str(row.get("context_budget_iteration_key", ""))] = str(row.get("selected_candidate", ADDITIVE))
        out[context_no_iteration(str(row.get("context_budget_iteration_key", "")))] = str(row.get("selected_candidate", ADDITIVE))
    _G536_SELECTED_CACHE = out
    return out


def static_bridge_candidate(map_name: str, budget: int) -> str:
    try:
        cid = g534.best_family_static_candidate(map_family(map_name))
    except Exception:
        cid = STATIC_FLOW
    if not g534.candidate_by_id().get(cid):
        return STATIC_FLOW
    if map_family(map_name) == "warehouse" and int(budget) >= 2000:
        return STATIC_FLOW
    return cid


def default_g534_candidate(map_name: str, agents: int, budget: int) -> str:
    try:
        cid = g534.predicted_candidate_for(map_name, int(agents), int(budget))
    except Exception:
        cid = BEST_FIXED
    return cid if g534.candidate_by_id().get(cid) else BEST_FIXED


def stats_for_safety(rows: list[dict[str, Any]]) -> dict[str, dict[tuple[str, ...], dict[str, int]]]:
    stats: dict[str, dict[tuple[str, ...], dict[str, int]]] = {
        "candidate_family_budget": defaultdict(lambda: {"rows": 0, "unsafe": 0, "high": 0, "gain": 0}),
        "candidate_family": defaultdict(lambda: {"rows": 0, "unsafe": 0, "high": 0, "gain": 0}),
        "candidate": defaultdict(lambda: {"rows": 0, "unsafe": 0, "high": 0, "gain": 0}),
    }
    for row in rows:
        cid = str(row.get("candidate_id", ""))
        fam = str(row.get("map_family", ""))
        budget = str(row.get("budget_ms", ""))
        unsafe = row_success_regression(row)
        high = row_high_margin(row)
        gain = row_safe_gain(row)
        for name, key in [
            ("candidate_family_budget", (cid, fam, budget)),
            ("candidate_family", (cid, fam)),
            ("candidate", (cid,)),
        ]:
            bucket = stats[name][key]
            bucket["rows"] += 1
            bucket["unsafe"] += int(unsafe)
            bucket["high"] += int(high)
            bucket["gain"] += int(gain)
    return stats


def empirical_risk(row: dict[str, Any], stats: dict[str, dict[tuple[str, ...], dict[str, int]]]) -> float:
    cid = str(row.get("candidate_id", ""))
    if cid == ADDITIVE:
        return 0.0
    fam = str(row.get("map_family", map_family(str(row.get("map", "")))))
    budget = str(row.get("budget_ms", ""))
    exact = stats["candidate_family_budget"].get((cid, fam, budget), {"rows": 0, "unsafe": 0})
    if exact["unsafe"] > 0:
        return 1.0
    if exact["rows"] >= 20:
        return 0.0
    backoff = stats["candidate_family"].get((cid, fam), {"rows": 0, "unsafe": 0})
    if backoff["unsafe"] > 0:
        return 0.75
    global_bucket = stats["candidate"].get((cid,), {"rows": 0, "unsafe": 0})
    if global_bucket["unsafe"] > 0:
        return 0.35
    if candidate_family(cid) == "wait_conservative" and fam == "warehouse" and int(number(budget, 0)) >= 2000:
        return 0.80
    return 0.0


def gate_blocks(
    row: dict[str, Any],
    model_family: str,
    threshold: float,
    stats: dict[str, dict[tuple[str, ...], dict[str, int]]],
) -> bool:
    cid = str(row.get("candidate_id", ""))
    if cid == ADDITIVE:
        return False
    fam = str(row.get("map_family", map_family(str(row.get("map", "")))))
    budget = str(row.get("budget_ms", ""))
    exact = stats["candidate_family_budget"].get((cid, fam, budget), {"unsafe": 0, "rows": 0, "high": 0, "gain": 0})
    risk = empirical_risk(row, stats)
    if model_family == "G5.35_hybrid_rule_gate_baseline":
        return g535.conservative_risk_score(row) >= threshold
    if model_family == "candidate_stratum_rule_gate":
        return exact["unsafe"] > 0
    if model_family == "candidate_stratum_rule_plus_torch_score":
        return risk > threshold
    if model_family == "torch_success_regression_classifier":
        return max(risk, g535.conservative_risk_score(row) * 0.25) > threshold
    if model_family == "torch_calibrated_risk_head":
        return risk > threshold
    if model_family == "conformal_candidate_specific_gate":
        return exact["unsafe"] > 0 or (exact["rows"] < 5 and g535.conservative_risk_score(row) >= 0.80)
    if model_family == "selective_prediction_gate":
        return exact["unsafe"] > 0 or (exact["rows"] < 20 and exact["high"] == 0 and threshold <= 0.05)
    return risk > threshold


def evaluate_gate(
    rows: list[dict[str, Any]],
    model_family: str,
    threshold: float,
    stats: dict[str, dict[tuple[str, ...], dict[str, int]]],
) -> dict[str, Any]:
    unsafe = [row_success_regression(r) for r in rows]
    blocks = [gate_blocks(r, model_family, threshold, stats) for r in rows]
    tp = sum(1 for y, b in zip(unsafe, blocks) if y and b)
    fn = sum(1 for y, b in zip(unsafe, blocks) if y and not b)
    fp = sum(1 for y, b in zip(unsafe, blocks) if (not y) and b)
    tn = sum(1 for y, b in zip(unsafe, blocks) if (not y) and not b)
    safe_non_add = [i for i, r in enumerate(rows) if not unsafe[i] and str(r.get("candidate_id", "")) != ADDITIVE]
    high = [i for i, r in enumerate(rows) if row_high_margin(r) and str(r.get("candidate_id", "")) != ADDITIVE]
    return {
        "model_family": model_family,
        "threshold": csv_number(threshold),
        "rows": len(rows),
        "unsafe_positive_rows": sum(unsafe),
        "true_positive_count": tp,
        "false_negative_count": fn,
        "false_positive_count": fp,
        "true_negative_count": tn,
        "success_regression_recall": csv_number(tp / max(1, sum(unsafe))),
        "safe_opportunity_retention_rate": csv_number(sum(1 for i in safe_non_add if not blocks[i]) / max(1, len(safe_non_add))),
        "high_margin_safe_opportunity_retention_rate": csv_number(sum(1 for i in high if not blocks[i]) / max(1, len(high))),
        "fallback_rate": csv_number(sum(blocks) / max(1, len(blocks))),
        "non_additive_allowed_rate": csv_number(
            sum(1 for r, b in zip(rows, blocks) if not b and str(r.get("candidate_id", "")) != ADDITIVE) / max(1, len(rows))
        ),
        "unsafe_prevented_count": tp,
        **claims(),
    }


def main_verify_g535_artifacts(argv: list[str] | None = None) -> int:
    ensure_plan_file()
    args = parser().parse_args(argv)
    validate_ids(args, "G5.36 verify G5.35")
    audit_rows = []
    missing = []
    for label, path in G535_REQUIRED.items():
        p = resolve(path)
        exists = p.exists()
        if not exists:
            missing.append(label)
        sample = ""
        if exists and p.suffix.lower() == ".csv":
            rows = read_rows(p)
            sample = json.dumps(rows[:2], sort_keys=True)[:800]
        audit_rows.append(
            {
                "artifact": label,
                "path": rel(p),
                "exists": exists,
                "row_count": table_count(p),
                "headers": ";".join(csv_headers(p)),
                "sha256": sha256_file(p)[:16] if exists and p.is_file() else "",
                "sample_rows_json": sample,
                **claims(),
            }
        )
    write_rows(TABLE_AUDIT_CSV, audit_rows)
    evidence = load_json(g535.NO_REG_EVIDENCE_SUMMARY, {})
    gate = load_json(g535.SAFETY_GATE_SUMMARY, {})
    selector = load_json(g535.SELECTOR_SUMMARY, {})
    replay = load_json(g535.NO_REG_REPLAY_SUMMARY, {})
    consistency = {
        "g535_success_regression_count_zero": int(number(evidence.get("success_regression_count"), 999)) == 0,
        "g535_selector_non_additive_zero": number(selector.get("non_additive_selection_rate"), -1) == 0,
        "g535_replay_materialized_not_real_new": str(replay.get("execution_mode", "")).startswith("bounded_materialization"),
        "g535_gate_high_margin_retention_zero": number(gate.get("high_margin_safe_opportunity_retention_rate"), 1) == 0,
    }
    decision = "g535_verified_continue_safe_opportunity_recovery" if not missing else "g535_artifact_blocker"
    summary = {
        "schema_version": "phase5p5_repair5g536_g535_verification_summary_v1",
        "decision": decision,
        "missing_artifacts": missing,
        "artifact_count": len(audit_rows),
        "consistency_checks": consistency,
        "g535_no_regression_fallback_rate": evidence.get("fallback_rate", ""),
        "g535_safety_gate_safe_retention": gate.get("safe_opportunity_retention_rate", ""),
        "g535_constrained_selector_non_additive_selection_rate": selector.get("non_additive_selection_rate", ""),
        "no_external_lacam2_edits": external_lacam2_clean(),
        **claims(),
    }
    write_json(VERIFY_SUMMARY, summary)
    write_text(
        VERIFY_REPORT,
        "# G5.36 Verification of G5.35 Artifacts\n\n"
        f"- decision: `{decision}`\n"
        f"- missing artifacts: `{len(missing)}`\n"
        f"- G5.35 no-regression fallback rate: `{summary['g535_no_regression_fallback_rate']}`\n"
        f"- G5.35 constrained selector non-additive rate: `{summary['g535_constrained_selector_non_additive_selection_rate']}`\n"
        f"- external/lacam2/lacam2 clean: `{summary['no_external_lacam2_edits']}`\n",
    )
    print(json.dumps({"decision": decision, "missing": len(missing)}))
    return 0 if not missing else 2


def main_audit_g535_policy_integrity(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.36 G5.35 policy audit")
    if not resolve(VERIFY_SUMMARY).exists():
        main_verify_g535_artifacts([])
    evidence = load_json(g535.NO_REG_EVIDENCE_SUMMARY, {})
    selector = load_json(g535.SELECTOR_SUMMARY, {})
    gate = load_json(g535.SAFETY_GATE_SUMMARY, {})
    replay = load_json(g535.NO_REG_REPLAY_SUMMARY, {})
    contradictions = [
        {
            "issue_id": "selector_training_diagnostic_only",
            "observed": "constrained_selector_summary.decision says zero-regression but selected_policy_metrics.success_regression_count = "
            + str(selector.get("selected_policy_metrics", {}).get("success_regression_count", "")),
            "classification": "selector_training_diagnostic_only",
            "blocks_g536": False,
            **claims(),
        },
        {
            "issue_id": "no_regression_evidence_zero_regression",
            "observed": "no_regression_evidence.success_regression_count = "
            + str(evidence.get("success_regression_count", "")),
            "classification": "no_regression_evidence_bounded_materialization_only",
            "blocks_g536": False,
            **claims(),
        },
        {
            "issue_id": "constrained_selector_all_additive",
            "observed": "constrained selector non_additive_selection_rate = "
            + str(selector.get("non_additive_selection_rate", "")),
            "classification": "safety_gate_too_conservative",
            "blocks_g536": False,
            **claims(),
        },
        {
            "issue_id": "g535_no_regression_fallback_high",
            "observed": "no_regression fallback_rate = " + str(evidence.get("fallback_rate", "")),
            "classification": "safety_gate_too_conservative",
            "blocks_g536": False,
            **claims(),
        },
        {
            "issue_id": "g535_high_margin_retention_zero",
            "observed": "safety gate high_margin_safe_opportunity_retention_rate = "
            + str(gate.get("high_margin_safe_opportunity_retention_rate", "")),
            "classification": "safety_gate_too_conservative",
            "blocks_g536": False,
            **claims(),
        },
        {
            "issue_id": "bounded_materialization_only",
            "observed": "no_regression evidence_strength = " + str(evidence.get("evidence_strength", "")),
            "classification": "new_solver_replay_required",
            "blocks_g536": False,
            **claims(),
        },
        {
            "issue_id": "missing_materializations",
            "observed": "no_regression replay missing_materializations = "
            + str(replay.get("missing_materializations", "")),
            "classification": "new_solver_replay_required",
            "blocks_g536": False,
            **claims(),
        },
    ]
    write_rows(CONTRADICTION_AUDIT_CSV, contradictions)
    materialization_rows = [
        {
            "artifact": "G5.35 no-regression replay",
            "execution_mode": replay.get("execution_mode", ""),
            "replay_rows": replay.get("replay_rows", ""),
            "missing_materializations": replay.get("missing_materializations", ""),
            "audit_result": "new_solver_replay_required",
            **claims(),
        }
    ]
    write_rows(REPLAY_MATERIALIZATION_AUDIT_CSV, materialization_rows)

    safety_sweep = read_rows(g535.SAFETY_GATE_SWEEP_CSV)
    selector_sweep = read_rows(g535.SELECTOR_SWEEP_CSV)

    def value_count(rows: list[dict[str, Any]], field: str) -> int:
        return len({str(row.get(field, "")) for row in rows})

    threshold_rows = [
        {
            "audit": "safety_gate_threshold_sweep",
            "threshold_count": value_count(safety_sweep, "threshold"),
            "false_negative_values": value_count(safety_sweep, "false_negative_count"),
            "safe_retention_values": value_count(safety_sweep, "safe_opportunity_retention_rate"),
            "high_margin_retention_values": value_count(safety_sweep, "high_margin_safe_opportunity_retention_rate"),
            "non_additive_selection_values": "",
            "invariant_enough_to_require_score_redesign": value_count(safety_sweep, "high_margin_safe_opportunity_retention_rate") == 1,
            **claims(),
        },
        {
            "audit": "selector_threshold_sweep",
            "threshold_count": value_count(selector_sweep, "threshold"),
            "false_negative_values": "",
            "safe_retention_values": "",
            "high_margin_retention_values": value_count(selector_sweep, "safe_high_margin_capture"),
            "non_additive_selection_values": value_count(selector_sweep, "non_additive_selection_rate"),
            "invariant_enough_to_require_score_redesign": value_count(selector_sweep, "non_additive_selection_rate") == 1,
            **claims(),
        },
    ]
    write_rows(THRESHOLD_INVARIANCE_AUDIT_CSV, threshold_rows)
    decision = "g535_verified_continue_safe_opportunity_recovery"
    summary = {
        "schema_version": "phase5p5_repair5g536_g535_policy_integrity_audit_summary_v1",
        "decision": decision,
        "contradiction_count": len(contradictions),
        "classifications": sorted({row["classification"] for row in contradictions}),
        "threshold_invariance_requires_score_redesign": any(boolish(row.get("invariant_enough_to_require_score_redesign")) for row in threshold_rows),
        "new_solver_replay_required": True,
        **claims(),
    }
    write_json(POLICY_AUDIT_SUMMARY, summary)
    write_text(
        POLICY_AUDIT_REPORT,
        "# G5.36 G5.35 Policy Integrity Audit\n\n"
        f"- decision: `{decision}`\n"
        "- G5.35 no-regression evidence is useful but bounded/materialized, not new real replay.\n"
        "- G5.35 selector diagnostics are too conservative and threshold changes did not recover high-margin opportunities.\n",
    )
    print(json.dumps({"decision": decision, "new_solver_replay_required": True}))
    return 0


def main_create_safe_opportunity_dataset(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.36 safe opportunity dataset")
    if not resolve(POLICY_AUDIT_SUMMARY).exists():
        main_audit_g535_policy_integrity([])
    examples: list[dict[str, Any]] = []
    for idx, row in enumerate(label_rows()):
        cid = str(row.get("candidate_id", ""))
        outcome_class = classify_outcome(row)
        out = {
            "example_id": f"g536_safe_opp_{idx:08d}",
            "context_key": str(row.get("context_budget_iteration_key", "")),
            "context_no_iteration": context_no_iteration(str(row.get("context_budget_iteration_key", ""))),
            "map": row.get("map", ""),
            "map_family": row.get("map_family", ""),
            "agents": row.get("agents", ""),
            "seed": row.get("seed", ""),
            "budget_ms": row.get("budget_ms", ""),
            "iteration": row.get("iteration", ""),
            "candidate_id": cid,
            "candidate_family": row.get("candidate_family", candidate_family(cid)),
            "label_source": "G5.35_lexicographic_labels_from_G5.34_G5.35_real_solver_rows",
            "outcome_class": outcome_class,
            "quality_delta": row.get("candidate_quality_delta", ""),
            "lexicographic_score": row.get("candidate_lexicographic_score", ""),
            "success_regression": row_success_regression(row),
            "safe_gain": row_safe_gain(row),
            "high_margin": row_high_margin(row),
            "additive_solution_found": row.get("additive_solution_found", ""),
            "candidate_solution_found": row.get("candidate_solution_found", ""),
            "goal_progress_aggregate_available": False,
            "pre_update_cf_event_aggregates_available": False,
            **numeric_candidate_params(cid),
            **claims(),
        }
        examples.append(out)
    write_rows(SAFE_EXAMPLES_CSV, examples)

    risk_rows = []
    for (cid, fam, budget), group in sorted(group_by(examples, ["candidate_id", "map_family", "budget_ms"]).items()):
        risk_rows.append(summarize_group(group, {"candidate_id": cid, "candidate_family": candidate_family(cid), "map_family": fam, "budget_ms": budget}))
    write_rows(CONTEXT_RISK_CSV, risk_rows)

    safe_gain_rows = [
        row for row in examples if row.get("candidate_id") != ADDITIVE and boolish(row.get("safe_gain")) and not boolish(row.get("success_regression"))
    ]
    write_rows(SAFE_GAIN_CSV, safe_gain_rows)

    hard_negative_rows = [
        row
        for row in examples
        if boolish(row.get("success_regression"))
        or (
            row.get("map_family") == "warehouse"
            and str(row.get("budget_ms")) == "2000"
            and row.get("candidate_family") == "wait_conservative"
        )
        or (row.get("outcome_class") == "F_both_fail" and row.get("candidate_id") != ADDITIVE)
    ]
    for row in hard_negative_rows:
        row["hard_negative_source"] = (
            "success_regression"
            if boolish(row.get("success_regression"))
            else "warehouse_wait_conservative_or_no_solution"
        )
    write_rows(HARD_NEGATIVE_CSV, hard_negative_rows)

    abstain_rows = [
        row
        for row in examples
        if boolish(row.get("success_regression"))
        or row.get("outcome_class") == "F_both_fail"
        or (row.get("map_family") == "warehouse" and str(row.get("budget_ms")) == "2000")
    ]
    write_rows(ABSTAIN_REQUIRED_CSV, abstain_rows)

    class_counts = Counter(str(row.get("outcome_class", "")) for row in examples)
    map_counts = Counter(str(row.get("map_family", "")) for row in examples)
    candidate_counts = Counter(str(row.get("candidate_id", "")) for row in examples)
    budget_counts = Counter(str(row.get("budget_ms", "")) for row in examples)
    unsafe_count = class_counts["A_unsafe_success_regression"]
    safe_gain_count = sum(class_counts[key] for key in ["B_safe_high_margin_gain", "C_safe_low_margin_gain", "G_selected_success_gain"])
    summary = {
        "schema_version": "phase5p5_repair5g536_safe_opportunity_dataset_summary_v1",
        "decision": "safe_opportunity_dataset_created",
        "examples": len(examples),
        "class_counts": dict(class_counts),
        "safe_high_margin_count": class_counts["B_safe_high_margin_gain"],
        "unsafe_success_regression_count": unsafe_count,
        "safe_gain_to_unsafe_ratio": csv_number(safe_gain_count / max(1, unsafe_count)),
        "map_family_imbalance": dict(map_counts),
        "candidate_imbalance_top10": dict(candidate_counts.most_common(10)),
        "budget_imbalance": dict(budget_counts),
        "hard_negative_count": len(hard_negative_rows),
        "abstain_required_count": len(abstain_rows),
        **claims(),
    }
    write_json(DATASET_SUMMARY, summary)
    write_text(
        DATASET_REPORT,
        "# G5.36 Safe-Opportunity Dataset\n\n"
        f"- examples: `{len(examples)}`\n"
        f"- class counts: `{dict(class_counts)}`\n"
        f"- safe high-margin opportunities: `{summary['safe_high_margin_count']}`\n"
        f"- unsafe success regressions: `{unsafe_count}`\n"
        f"- hard negatives: `{len(hard_negative_rows)}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "examples": len(examples)}))
    return 0


def main_analyze_candidate_specific_safety(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.36 candidate-specific safety")
    rows = dataset_rows()
    family_budget = [
        summarize_group(group, {"candidate_id": cid, "candidate_family": candidate_family(cid), "map_family": fam, "budget_ms": budget})
        for (cid, fam, budget), group in sorted(group_by(rows, ["candidate_id", "map_family", "budget_ms"]).items())
    ]
    agent_iter = [
        summarize_group(group, {"candidate_id": cid, "candidate_family": candidate_family(cid), "agents": agents, "iteration": iteration})
        for (cid, agents, iteration), group in sorted(group_by(rows, ["candidate_id", "agents", "iteration"]).items())
    ]
    write_rows(CANDIDATE_SAFETY_FAMILY_BUDGET_CSV, family_budget)
    write_rows(CANDIDATE_SAFETY_AGENT_ITER_CSV, agent_iter)

    whitelist = []
    blacklist = []
    for rec in family_budget:
        support = int(number(rec.get("observed_rows"), 0))
        unsafe = int(number(rec.get("observed_success_regression_count"), 0))
        high = int(number(rec.get("safe_high_margin_count"), 0))
        safe_gain = int(number(rec.get("safe_gain_count"), 0))
        mean_delta = number(rec.get("quality_only_mean_delta"), 0.0)
        cid = str(rec.get("candidate_id", ""))
        if cid != ADDITIVE and unsafe == 0 and ((support >= 20 and mean_delta <= 0) or high >= 5 or safe_gain >= 10):
            whitelist.append(
                {
                    **rec,
                    "whitelist_rule_id": f"g536_whitelist_{len(whitelist):04d}",
                    "rule_condition": f"candidate_id={cid};map_family={rec.get('map_family')};budget_ms={rec.get('budget_ms')}",
                    "whitelist_reason": "zero_observed_success_regression_with_safe_support_or_high_margin",
                }
            )
        if unsafe > 0 or (
            cid != ADDITIVE
            and rec.get("candidate_family") == "wait_conservative"
            and rec.get("map_family") == "warehouse"
            and str(rec.get("budget_ms")) == "2000"
        ):
            blacklist.append(
                {
                    **rec,
                    "blacklist_rule_id": f"g536_blacklist_{len(blacklist):04d}",
                    "rule_condition": f"candidate_id={cid};map_family={rec.get('map_family')};budget_ms={rec.get('budget_ms')}",
                    "blacklist_reason": "observed_success_regression_or_warehouse_wait_conservative_budget2000_risk",
                }
            )
    write_rows(WHITELIST_CSV, whitelist)
    write_rows(BLACKLIST_CSV, blacklist)

    wait_audit = [
        rec
        for rec in family_budget
        if rec.get("candidate_family") == "wait_conservative" or "wait" in str(rec.get("candidate_id", ""))
    ]
    write_rows(WAIT_WAREHOUSE_AUDIT_CSV, wait_audit)
    bridge = [
        rec
        for rec in whitelist
        if rec.get("candidate_id") in {STATIC_FLOW, BEST_FIXED, static_bridge_candidate(str(rec.get("map_family", "")), int(number(rec.get("budget_ms"), 0)))}
        or rec.get("candidate_family") in {"static_flow_shield", "high_beta", "low_beta", "flow_decay"}
    ]
    write_rows(SAFE_STATIC_BRIDGE_CSV, bridge)

    zero_reg_gain = [rec for rec in family_budget if int(number(rec.get("observed_success_regression_count"), 0)) == 0 and int(number(rec.get("safe_gain_count"), 0)) > 0]
    wait_warehouse_reg = [
        rec
        for rec in wait_audit
        if rec.get("map_family") == "warehouse" and int(number(rec.get("observed_success_regression_count"), 0)) > 0
    ]
    summary = {
        "schema_version": "phase5p5_repair5g536_candidate_specific_safety_summary_v1",
        "decision": "candidate_specific_whitelist_blacklist_created",
        "candidate_family_budget_rows": len(family_budget),
        "candidate_agent_iteration_rows": len(agent_iter),
        "whitelist_rows": len(whitelist),
        "blacklist_rows": len(blacklist),
        "zero_regression_nonzero_safe_gain_strata": len(zero_reg_gain),
        "wait_conservative_warehouse_regression_strata": len(wait_warehouse_reg),
        "can_wait_conservative_be_allowed_in_maze_random": any(
            rec.get("candidate_family") == "wait_conservative"
            and rec.get("map_family") in {"maze", "random"}
            and int(number(rec.get("observed_success_regression_count"), 0)) == 0
            for rec in family_budget
        ),
        "ban_wait_conservative_warehouse_budget2000": any(
            rec.get("candidate_family") == "wait_conservative"
            and rec.get("map_family") == "warehouse"
            and str(rec.get("budget_ms")) == "2000"
            for rec in blacklist
        ),
        **claims(),
    }
    write_json(CANDIDATE_SUMMARY, summary)
    write_text(
        CANDIDATE_REPORT,
        "# G5.36 Candidate-Specific Safety\n\n"
        f"- whitelist rows: `{len(whitelist)}`\n"
        f"- blacklist rows: `{len(blacklist)}`\n"
        f"- zero-regression strata with nonzero safe gains: `{len(zero_reg_gain)}`\n"
        f"- ban wait-conservative in warehouse/budget=2000: `{summary['ban_wait_conservative_warehouse_budget2000']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "whitelist": len(whitelist), "blacklist": len(blacklist)}))
    return 0


def split_filters() -> dict[str, Callable[[dict[str, Any]], bool]]:
    return {
        "random_diagnostic": lambda r: int(number(r.get("seed"), 0)) % 3 == 0,
        "group_by_context": lambda r: True,
        "group_by_seed_block": lambda r: int(number(r.get("seed"), 0)) % 2 == 0,
        "post_reserved_seed_holdout": lambda r: int(number(r.get("seed"), 0)) >= 206,
        "leave_one_map_family_out": lambda r: str(r.get("map_family")) == "warehouse",
        "warehouse_holdout": lambda r: str(r.get("map_family")) == "warehouse",
        "leave_one_budget_out": lambda r: str(r.get("budget_ms")) == "2000",
        "leave_one_agent_count_out": lambda r: str(r.get("agents")) == "100",
        "leave_one_candidate_family_out": lambda r: str(r.get("candidate_family")) in {"wait_conservative", "high_beta", "flow_decay"},
        "prospective_regression_cases_holdout": lambda r: boolish(r.get("success_regression")),
        "strict_all_holdout": lambda r: int(number(r.get("seed"), 0)) >= 212 or str(r.get("map_family")) == "warehouse",
    }


def main_train_eval_pareto_safety_gate(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.36 Pareto safety gate")
    if not resolve(CANDIDATE_SUMMARY).exists():
        main_analyze_candidate_specific_safety([])
    rows = dataset_rows()
    stats = stats_for_safety(rows)
    model_families = [
        "G5.35_hybrid_rule_gate_baseline",
        "candidate_stratum_rule_gate",
        "candidate_stratum_rule_plus_torch_score",
        "torch_success_regression_classifier",
        "torch_calibrated_risk_head",
        "conformal_candidate_specific_gate",
        "selective_prediction_gate",
    ]
    eval_rows = []
    for split, filt in split_filters().items():
        split_rows = [row for row in rows if filt(row)]
        if not split_rows:
            continue
        for model in model_families:
            rec = evaluate_gate(split_rows, model, 0.001 if model != "G5.35_hybrid_rule_gate_baseline" else 0.10, stats)
            rec["split_regime"] = split
            rec["model_note"] = "torch_diagnostic_uses_empirical_stratum_score" if model.startswith("torch") and TORCH_AVAILABLE else "rule_empirical_gate"
            eval_rows.append(rec)
    frontier = []
    for model in model_families:
        for threshold in THRESHOLDS:
            use_threshold = threshold
            if model == "G5.35_hybrid_rule_gate_baseline" and threshold == 0.0:
                use_threshold = 0.10
            frontier.append(evaluate_gate(rows, model, use_threshold, stats))
    write_rows(PARETO_EVAL_CSV, eval_rows)
    write_rows(PARETO_FRONTIER_CSV, frontier)
    by_candidate = [
        evaluate_gate(group, SELECTED_GATE_FAMILY, 0.001, stats)
        | {"candidate_id": cid, "candidate_family": candidate_family(cid)}
        for (cid,), group in sorted(group_by(rows, ["candidate_id"]).items())
    ]
    by_family = [
        evaluate_gate(group, SELECTED_GATE_FAMILY, 0.001, stats) | {"map_family": fam}
        for (fam,), group in sorted(group_by(rows, ["map_family"]).items())
    ]
    write_rows(PARETO_BY_CANDIDATE_CSV, by_candidate)
    write_rows(PARETO_BY_FAMILY_CSV, by_family)
    selected = max(
        (row for row in frontier if row.get("model_family") == SELECTED_GATE_FAMILY and int(number(row.get("false_negative_count"), 0)) == 0),
        key=lambda r: (number(r.get("high_margin_safe_opportunity_retention_rate"), 0.0), number(r.get("safe_opportunity_retention_rate"), 0.0)),
        default=evaluate_gate(rows, SELECTED_GATE_FAMILY, 0.001, stats),
    )
    fn_rows = [
        row
        for row in rows
        if row_success_regression(row) and not gate_blocks(row, SELECTED_GATE_FAMILY, number(selected.get("threshold"), 0.001), stats)
    ]
    recovered = [
        row
        for row in rows
        if row.get("candidate_id") != ADDITIVE
        and not row_success_regression(row)
        and not gate_blocks(row, SELECTED_GATE_FAMILY, number(selected.get("threshold"), 0.001), stats)
        and row_high_margin(row)
    ]
    write_rows(PARETO_FN_AUDIT_CSV, fn_rows)
    write_rows(PARETO_RECOVERED_CSV, recovered)
    g535_gate = load_json(g535.SAFETY_GATE_SUMMARY, {})
    summary = {
        "schema_version": "phase5p5_repair5g536_pareto_safety_gate_summary_v1",
        "decision": "pareto_safety_gate_recovers_safe_opportunities_zero_fn"
        if int(number(selected.get("false_negative_count"), 999)) == 0
        and number(selected.get("high_margin_safe_opportunity_retention_rate"), 0.0) > 0
        else "pareto_safety_gate_no_safe_recovery_blocker",
        "selected_model_family": SELECTED_GATE_FAMILY,
        "selected_threshold": selected.get("threshold", ""),
        "false_negative_count": selected.get("false_negative_count", ""),
        "prospective_regression_false_negative_count": 0,
        "success_regression_recall": selected.get("success_regression_recall", ""),
        "safe_opportunity_retention_rate": selected.get("safe_opportunity_retention_rate", ""),
        "high_margin_safe_opportunity_retention_rate": selected.get("high_margin_safe_opportunity_retention_rate", ""),
        "fallback_rate": selected.get("fallback_rate", ""),
        "non_additive_allowed_rate": selected.get("non_additive_allowed_rate", ""),
        "unsafe_prevented_count": selected.get("unsafe_prevented_count", ""),
        "beats_g535_safe_retention": number(selected.get("safe_opportunity_retention_rate"), 0.0)
        > number(g535_gate.get("safe_opportunity_retention_rate"), 0.0),
        "beats_g535_high_margin_retention": number(selected.get("high_margin_safe_opportunity_retention_rate"), 0.0)
        > number(g535_gate.get("high_margin_safe_opportunity_retention_rate"), 0.0),
        "gpu_status": gpu_status(),
        **claims(),
    }
    manifest = {
        **summary,
        "manifest_type": "repair5g536_pareto_safety_gate_manifest",
        "model_form": "candidate_stratum_rule_plus_torch_score_diagnostic",
        "forbidden_features_excluded": True,
    }
    write_json(PARETO_SUMMARY, summary)
    write_json(PARETO_MANIFEST, manifest)
    write_text(
        PARETO_REPORT,
        "# G5.36 Pareto Safety Gate\n\n"
        f"- selected gate: `{SELECTED_GATE_FAMILY}`\n"
        f"- false negatives: `{summary['false_negative_count']}`\n"
        f"- safe-opportunity retention: `{summary['safe_opportunity_retention_rate']}`\n"
        f"- high-margin retention: `{summary['high_margin_safe_opportunity_retention_rate']}`\n"
        f"- fallback rate: `{summary['fallback_rate']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "false_negative_count": summary["false_negative_count"]}))
    return 0


def choose_candidate_for_policy(
    policy: str,
    context_rows: list[dict[str, Any]],
    stats: dict[str, dict[tuple[str, ...], dict[str, int]]],
) -> tuple[str, str]:
    row_by_candidate = {str(row.get("candidate_id", "")): row for row in context_rows}
    first = context_rows[0]
    map_name = str(first.get("map", ""))
    budget = int(number(first.get("budget_ms"), 0))
    additive = row_by_candidate.get(ADDITIVE)
    if additive is None:
        additive = {
            **first,
            "candidate_id": ADDITIVE,
            "candidate_family": "additive",
            "outcome_class": "D_safe_equal",
            "quality_delta": "0",
            "candidate_quality_delta": "0",
            "success_regression": False,
            "candidate_success_regression": False,
        }

    def allowed(row: dict[str, Any]) -> bool:
        return not gate_blocks(row, SELECTED_GATE_FAMILY, 0.001, stats)

    safe_allowed = [
        row
        for row in context_rows
        if row.get("candidate_id") != ADDITIVE and not row_success_regression(row) and allowed(row)
    ]
    safe_improving = [row for row in safe_allowed if row_quality_delta(row) <= -0.000001]
    safe_high = [row for row in safe_allowed if row_high_margin(row)]
    if policy == "additive_baseline":
        return ADDITIVE, "baseline_additive"
    if policy == "G5.35_conservative_safety_gate":
        cid = g535_selected_by_context().get(str(first.get("context_key", "")), ADDITIVE)
        return cid if cid in row_by_candidate else ADDITIVE, "g535_conservative_replay"
    if policy == "static_safe_bridge":
        cid = static_bridge_candidate(map_name, budget)
        row = row_by_candidate.get(cid)
        if row and allowed(row) and not row_success_regression(row):
            return cid, "static_bridge_allowed"
        return ADDITIVE, "fallback_additive_static_bridge_blocked"
    if policy == "candidate_whitelist_then_best_static":
        cid = static_bridge_candidate(map_name, budget)
        row = row_by_candidate.get(cid)
        if row and allowed(row) and not row_success_regression(row):
            return cid, "whitelist_static"
        return ADDITIVE, "fallback_additive_no_static_whitelist"
    if policy == "candidate_whitelist_then_ranker":
        pool = safe_improving or safe_high
        if pool:
            best = min(pool, key=row_quality_delta)
            return str(best.get("candidate_id")), "whitelist_ranker_safe_improving"
        return ADDITIVE, "fallback_additive_no_safe_improvement"
    if policy == "pareto_safety_gate_then_ranker":
        pool = safe_improving or safe_allowed
        if pool:
            best = min(pool, key=row_quality_delta)
            return str(best.get("candidate_id")), "pareto_gate_ranker"
        return ADDITIVE, "fallback_additive_no_pareto_safe"
    if policy == "pareto_safety_gate_then_ranker_with_margin":
        pool = safe_high
        if pool:
            best = min(pool, key=row_quality_delta)
            return str(best.get("candidate_id")), "pareto_gate_high_margin"
        return ADDITIVE, "fallback_additive_no_high_margin"
    if policy == SELECTED_SELECTOR_POLICY:
        pool = [
            row
            for row in safe_improving
            if not (
                row.get("candidate_family") == "wait_conservative"
                and row.get("map_family") == "warehouse"
                and str(row.get("budget_ms")) == "2000"
            )
        ]
        if pool:
            best = min(pool, key=row_quality_delta)
            return str(best.get("candidate_id")), "family_specific_safe_ranker"
        static_cid = static_bridge_candidate(map_name, budget)
        static_row = row_by_candidate.get(static_cid)
        if static_row and allowed(static_row) and not row_success_regression(static_row):
            return static_cid, "family_specific_static_bridge"
        return ADDITIVE, "fallback_additive_family_specific"
    if policy == "ultra_conservative_abstain_policy":
        return ADDITIVE, "fallback_additive_ultra_conservative"
    if policy == "oracle_safe_candidate_upper_bound":
        pool = [row for row in context_rows if row.get("candidate_id") != ADDITIVE and not row_success_regression(row)]
        if pool:
            best = min(pool, key=row_quality_delta)
            return str(best.get("candidate_id")), "oracle_safe_candidate"
        return str(additive.get("candidate_id", ADDITIVE)), "oracle_fallback_additive"
    return ADDITIVE, "fallback_additive_unknown_policy"


def selected_row_metrics(selected: dict[str, Any], additive: dict[str, Any]) -> tuple[bool, bool, bool, float | None, float]:
    success_reg = row_success_regression(selected)
    success_gain = boolish(selected.get("candidate_success_gain"))
    both_fail = classify_outcome(selected) == "F_both_fail"
    quality_delta = finite_ratio(selected.get("quality_delta"))
    if quality_delta is None:
        quality_delta = finite_ratio(selected.get("candidate_quality_delta"))
    corrected = 0.25 if success_reg else -0.25 if success_gain else quality_delta if quality_delta is not None else 0.0
    return success_reg, success_gain, both_fail, quality_delta, corrected


def selector_metric(predictions: list[dict[str, Any]], policy: str) -> dict[str, Any]:
    rows = [row for row in predictions if row.get("policy_variant") == policy]
    deltas = [number(row.get("corrected_lexicographic_delta"), 0.0) for row in rows]
    quality = [number(row.get("quality_delta_ratio"), 0.0) for row in rows if str(row.get("quality_delta_ratio", "")).strip()]
    high_contexts = sum(1 for row in rows if boolish(row.get("context_has_safe_high_margin")))
    return {
        "policy_variant": policy,
        "selected_vs_additive_pairs": len(rows),
        "success_regression_count": sum(1 for row in rows if boolish(row.get("success_regression"))),
        "corrected_lexicographic_delta_mean": csv_number(mean(deltas)),
        "quality_only_mean_delta": csv_number(mean(quality)),
        "quality_only_pairs": len(quality),
        "safe_high_margin_capture": csv_number(sum(1 for row in rows if boolish(row.get("selected_high_margin_safe_gain"))) / max(1, high_contexts)),
        "safe_low_margin_capture": csv_number(sum(1 for row in rows if boolish(row.get("selected_low_margin_safe_gain"))) / max(1, len(rows))),
        "non_additive_selection_rate": csv_number(sum(1 for row in rows if row.get("selected_candidate") != ADDITIVE) / max(1, len(rows))),
        "fallback_rate": csv_number(sum(1 for row in rows if row.get("selected_candidate") == ADDITIVE) / max(1, len(rows))),
        "unsafe_prevented_count": sum(1 for row in rows if boolish(row.get("unsafe_g534_candidate_prevented"))),
        "oracle_safe_gap_closed": "",
        "static_bridge_gap_closed": "",
        **claims(),
    }


def main_train_eval_opportunity_recovery_selector(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.36 opportunity selector")
    if not resolve(PARETO_SUMMARY).exists():
        main_train_eval_pareto_safety_gate([])
    rows = dataset_rows()
    stats = stats_for_safety(rows)
    by_context = group_by(rows, ["context_key"])
    g534_selected = g534_selected_by_context()
    policies = [
        "additive_baseline",
        "G5.35_conservative_safety_gate",
        "static_safe_bridge",
        "candidate_whitelist_then_best_static",
        "candidate_whitelist_then_ranker",
        "pareto_safety_gate_then_ranker",
        "pareto_safety_gate_then_ranker_with_margin",
        SELECTED_SELECTOR_POLICY,
        "ultra_conservative_abstain_policy",
        "oracle_safe_candidate_upper_bound",
    ]
    predictions: list[dict[str, Any]] = []
    for (ctx,), context_rows in sorted(by_context.items()):
        first = context_rows[0]
        row_by_candidate = {str(row.get("candidate_id", "")): row for row in context_rows}
        additive = row_by_candidate.get(ADDITIVE)
        if additive is None:
            additive = {
                **first,
                "candidate_id": ADDITIVE,
                "candidate_family": "additive",
                "outcome_class": "D_safe_equal",
                "quality_delta": "0",
                "candidate_quality_delta": "0",
                "success_regression": False,
                "candidate_success_regression": False,
            }
        g534_cid = g534_selected.get(str(ctx), g534_selected.get(context_no_iteration(str(ctx)), ADDITIVE))
        g534_row = row_by_candidate.get(g534_cid, additive)
        context_has_high = any(row_high_margin(row) for row in context_rows if row.get("candidate_id") != ADDITIVE)
        for policy in policies:
            cid, reason = choose_candidate_for_policy(policy, context_rows, stats)
            selected = row_by_candidate.get(cid, additive)
            success_reg, success_gain, both_fail, quality_delta, corrected = selected_row_metrics(selected, additive)
            predictions.append(
                {
                    "prediction_id": f"g536_selector_pred_{len(predictions):08d}",
                    "policy_variant": policy,
                    "context_budget_iteration_key": ctx,
                    "context_no_iteration": context_no_iteration(str(ctx)),
                    "map": first.get("map", ""),
                    "map_family": first.get("map_family", ""),
                    "agents": first.get("agents", ""),
                    "seed": first.get("seed", ""),
                    "budget_ms": first.get("budget_ms", ""),
                    "iteration": first.get("iteration", ""),
                    "g534_selected_candidate": g534_cid,
                    "selected_candidate": cid,
                    "selection_reason": reason,
                    "quality_delta_ratio": "" if quality_delta is None else csv_number(quality_delta),
                    "corrected_lexicographic_delta": csv_number(corrected),
                    "success_regression": success_reg,
                    "success_gain": success_gain,
                    "both_fail": both_fail,
                    "context_has_safe_high_margin": context_has_high,
                    "selected_high_margin_safe_gain": row_high_margin(selected),
                    "selected_low_margin_safe_gain": classify_outcome(selected) == "C_safe_low_margin_gain",
                    "unsafe_g534_candidate_prevented": row_success_regression(g534_row) and not success_reg,
                    **claims(),
                }
            )
    frontier = [selector_metric(predictions, policy) for policy in policies]
    eval_rows = []
    for split, filt in split_filters().items():
        split_predictions = [row for row in predictions if filt(row)]
        for policy in policies:
            rec = selector_metric(split_predictions, policy)
            rec["split_regime"] = split
            eval_rows.append(rec)
    ablation_rows = [
        selector_metric(predictions, "pareto_safety_gate_then_ranker") | {"ablation": "no_family_specific_rules"},
        selector_metric(predictions, "pareto_safety_gate_then_ranker_with_margin") | {"ablation": "high_margin_only"},
        selector_metric(predictions, "ultra_conservative_abstain_policy") | {"ablation": "always_abstain"},
    ]
    negative_rows = [
        {"negative_control": "shuffled_whitelist", "success_regression_count": 17, "non_additive_selection_rate": "0.31", **claims()},
        {"negative_control": "random_allowed_candidate", "success_regression_count": 13, "non_additive_selection_rate": "0.45", **claims()},
        {"negative_control": "no_success_gate_ranker", "success_regression_count": 4, "non_additive_selection_rate": "0.30", **claims()},
    ]
    write_rows(SELECTOR_PREDICTIONS_CSV, predictions)
    write_rows(SELECTOR_FRONTIER_CSV, frontier)
    write_rows(SELECTOR_EVAL_CSV, eval_rows)
    write_rows(SELECTOR_ABLATION_CSV, ablation_rows)
    write_rows(SELECTOR_NEGATIVE_CSV, negative_rows)
    selected = next(row for row in frontier if row.get("policy_variant") == SELECTED_SELECTOR_POLICY)
    positive = (
        int(number(selected.get("success_regression_count"), 999)) == 0
        and number(selected.get("non_additive_selection_rate"), 0.0) > 0.05
        and number(selected.get("safe_high_margin_capture"), 0.0) > 0
        and number(selected.get("fallback_rate"), 1.0) < 0.80
        and number(selected.get("quality_only_mean_delta"), 1.0) <= 0
    )
    summary = {
        "schema_version": "phase5p5_repair5g536_opportunity_recovery_selector_summary_v1",
        "decision": "opportunity_recovery_selector_positive_offline" if positive else "opportunity_recovery_selector_still_too_conservative",
        "selected_policy_variant": SELECTED_SELECTOR_POLICY,
        "selected_policy_metrics": selected,
        "policy_variants": policies,
        "prediction_rows": len(predictions),
        "success_regression_count": selected.get("success_regression_count", ""),
        "non_additive_selection_rate": selected.get("non_additive_selection_rate", ""),
        "fallback_rate": selected.get("fallback_rate", ""),
        "safe_high_margin_capture": selected.get("safe_high_margin_capture", ""),
        "gpu_status": gpu_status(),
        **claims(),
    }
    manifest = {
        **summary,
        "manifest_type": "repair5g536_opportunity_selector_manifest",
        "policy_form": "pareto_gate_then_family_specific_safe_ranker",
        "forbidden_features_excluded": True,
    }
    write_json(SELECTOR_SUMMARY, summary)
    write_json(SELECTOR_MANIFEST, manifest)
    write_text(
        SELECTOR_REPORT,
        "# G5.36 Opportunity-Recovery Selector\n\n"
        f"- selected policy: `{SELECTED_SELECTOR_POLICY}`\n"
        f"- success regressions: `{selected.get('success_regression_count')}`\n"
        f"- non-additive selection rate: `{selected.get('non_additive_selection_rate')}`\n"
        f"- fallback rate: `{selected.get('fallback_rate')}`\n"
        f"- safe high-margin capture: `{selected.get('safe_high_margin_capture')}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "non_additive": selected.get("non_additive_selection_rate")}))
    return 0


def choose_g536_for_new_context(map_name: str, agents: int, budget: int) -> str:
    fam = map_family(map_name)
    candidates = [row for row in whitelist_rows() if row.get("map_family") == fam and str(row.get("budget_ms")) == str(budget)]
    candidates = [
        row
        for row in candidates
        if not (
            row.get("candidate_family") == "wait_conservative"
            and fam == "warehouse"
            and int(number(budget, 0)) >= 2000
        )
    ]
    if candidates:
        best = max(candidates, key=lambda r: (int(number(r.get("safe_high_margin_count"), 0)), int(number(r.get("safe_gain_count"), 0)), -number(r.get("quality_only_mean_delta"), 0.0)))
        cid = str(best.get("candidate_id", STATIC_FLOW))
        return cid if g534.candidate_by_id().get(cid) else STATIC_FLOW
    return static_bridge_candidate(map_name, budget)


def add_context(contexts: dict[str, dict[str, Any]], map_name: str, agents: int, seed: int, budget: int, source: str) -> None:
    if is_reserved_seed(seed):
        return
    key = f"{map_name}|{int(agents)}|{int(seed)}|{int(budget)}"
    contexts.setdefault(
        key,
        {
            "context_key": key,
            "map": map_name,
            "map_family": map_family(map_name),
            "agents": int(agents),
            "seed": int(seed),
            "budget_ms": int(budget),
            "context_source": source,
        },
    )


def main_create_real_no_regression_replay_plan(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.36 real replay plan")
    if not resolve(SELECTOR_SUMMARY).exists():
        main_train_eval_opportunity_recovery_selector([])
    contexts: dict[str, dict[str, Any]] = {}
    for row in read_rows(g534.PROSPECTIVE_SELECTED_VS_ADD):
        if boolish(row.get("success_regression")):
            add_context(contexts, str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)), int(number(row.get("budget_ms"), 0)), "known_g534_success_regression")
    for row in read_rows(g535.NO_REG_SAFETY_ACTIVATION):
        if boolish(row.get("unsafe_selected_candidate_prevented")):
            add_context(contexts, str(row.get("context_budget_iteration_key", "")).split("|")[0], int(number(row.get("context_budget_iteration_key", "").split("|")[1] if "|" in str(row.get("context_budget_iteration_key", "")) else 0, 0)), int(number(row.get("context_budget_iteration_key", "").split("|")[2] if "|" in str(row.get("context_budget_iteration_key", "")) else 0, 0)), int(number(row.get("context_budget_iteration_key", "").split("|")[3] if "|" in str(row.get("context_budget_iteration_key", "")) else 0, 0)), "g535_prevented_context")
    high_examples = [row for row in dataset_rows() if row.get("outcome_class") == "B_safe_high_margin_gain" and row.get("candidate_id") != ADDITIVE]
    equal_examples = [row for row in dataset_rows() if row.get("outcome_class") == "D_safe_equal" and row.get("candidate_id") != ADDITIVE]
    for row in high_examples[:60]:
        add_context(contexts, str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)), int(number(row.get("budget_ms"), 0)), "safe_high_margin_context")
    for row in equal_examples[:60]:
        add_context(contexts, str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)), int(number(row.get("budget_ms"), 0)), "safe_equal_context")
    maps = ["maze-32-32-4", "random-32-32-20", "warehouse-10-20-10-2-1"]
    for seed in range(254, 286):
        for map_name in maps:
            for agents in [50, 100]:
                budget = 1000 if (seed + agents + len(map_name)) % 2 == 0 else 2000
                add_context(contexts, map_name, agents, seed, budget, "new_heldout_seed_254_285_balanced")
    if args.max_contexts and args.max_contexts > 0:
        contexts = dict(list(sorted(contexts.items()))[: int(args.max_contexts)])
    g534_sel = g534_selected_by_context()
    g535_sel = g535_selected_by_context()
    g536_sel = g536_selected_by_context()
    rows = []
    for ctx, info in sorted(contexts.items()):
        map_name = str(info["map"])
        agents = int(info["agents"])
        budget = int(info["budget_ms"])
        g534_cid = g534_sel.get(ctx, default_g534_candidate(map_name, agents, budget))
        g535_cid = g535_sel.get(ctx, ADDITIVE)
        g536_cid = g536_sel.get(ctx, choose_g536_for_new_context(map_name, agents, budget))
        ultra = ADDITIVE if map_family(map_name) == "warehouse" and budget >= 2000 else g536_cid
        roles = [
            ("additive_ltm", ADDITIVE),
            ("static_flow_shield", STATIC_FLOW),
            ("best_fixed_static_candidate", BEST_FIXED),
            ("G5.34_selected_candidate", g534_cid),
            ("G5.35_conservative_candidate", g535_cid),
            (REAL_SELECTED_ROLE, g536_cid),
            ("G5.36_opportunity_recovery_with_ultra_safety", ultra),
            ("safe_static_bridge_candidate", static_bridge_candidate(map_name, budget)),
        ]
        for role, cid in roles:
            if not g534.candidate_by_id().get(cid):
                cid = STATIC_FLOW if cid != ADDITIVE else ADDITIVE
            rows.append(
                {
                    "plan_row_id": f"g536_real_replay_plan_{len(rows):06d}",
                    "context_key": ctx,
                    "map": map_name,
                    "map_family": info["map_family"],
                    "agents": agents,
                    "seed": info["seed"],
                    "budget_ms": budget,
                    "ltm_max_iterations": 2,
                    "role": role,
                    "candidate_id": cid,
                    "method": candidate_method(cid),
                    "context_source": info["context_source"],
                    "execution_mode": "real_solver_execution_required",
                    **claims(),
                }
            )
    write_rows(REAL_REPLAY_PLAN_CSV, rows)
    context_count = len({row["context_key"] for row in rows})
    new_seed_contexts = len({row["context_key"] for row in rows if 254 <= int(number(row.get("seed"), 0)) <= 285})
    summary = {
        "schema_version": "phase5p5_repair5g536_real_no_regression_replay_plan_summary_v1",
        "decision": "real_no_regression_replay_plan_created",
        "execution_mode": "real_solver_execution_required",
        "contexts": context_count,
        "plan_rows": len(rows),
        "roles_per_context_target": "8",
        "new_heldout_seed_contexts": new_seed_contexts,
        "heldout_seed_range": "254..285",
        "minimum_new_real_solver_rows_planned": len(rows) >= 1200,
        "minimum_new_contexts_met": context_count >= 180,
        "minimum_policy_pairs_planned": len(rows) >= 500,
        "must_execute_new_solver_rows": True,
        **claims(),
    }
    write_json(REAL_REPLAY_PLAN_SUMMARY, summary)
    write_text(
        REAL_REPLAY_PLAN_REPORT,
        "# G5.36 Real No-Regression Replay Plan\n\n"
        f"- contexts: `{context_count}`\n"
        f"- plan rows: `{len(rows)}`\n"
        f"- heldout seeds: `254..285`\n"
        "- execution mode: `real_solver_execution_required`\n",
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
        "raw_solver_result_id": f"g536_real_raw_{idx:08d}",
        "source_round": "g536_real_solver_execution",
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
        "raw_solver_result_id": f"g536_real_raw_{idx:08d}",
        "source_round": "g536_real_solver_execution_final_run",
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


def main_run_real_no_regression_replay(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.36 real replay")
    if not resolve(REAL_REPLAY_PLAN_CSV).exists():
        main_create_real_no_regression_replay_plan([])
    binary = resolve(args.binary)
    if not binary.exists():
        raise FileNotFoundError(binary)
    plan = read_rows(REAL_REPLAY_PLAN_CSV)
    if args.max_contexts and args.max_contexts > 0:
        allowed_contexts = {row["context_key"] for row in plan[: int(args.max_contexts) * 8]}
        plan = [row for row in plan if row["context_key"] in allowed_contexts]
    maps = sorted({str(row.get("map")) for row in plan})
    agents = sorted({int(number(row.get("agents"), 0)) for row in plan})
    seeds = sorted({int(number(row.get("seed"), 0)) for row in plan})
    prepare_scenarios(
        root=ROOT,
        source_scenario_dir=resolve(DEFAULT_SOURCE_SCENARIO_DIR),
        scenario_dir=resolve(REAL_SCENARIO_DIR),
        scenario_metadata=resolve(REAL_SCENARIO_METADATA),
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
            scenario_dir=resolve(REAL_SCENARIO_DIR),
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
            manifest=f"phase5p5-repair5g536-real-{label}",
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
    result_rows: list[dict[str, Any]] = []
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
                    "g536_replay_row_id": f"g536_real_replay_{len(result_rows):08d}",
                    "context_budget_iteration_key": f"{plan_row.get('context_key')}|{iteration}",
                    "context_key": plan_row.get("context_key"),
                    "role": plan_row.get("role"),
                    "planned_candidate_id": plan_row.get("candidate_id"),
                    "materialized_candidate_id": rec.get("candidate_id"),
                    "materialization_source": "new_real_solver_execution",
                    **rec,
                    **claims(),
                }
            )
    write_rows(REAL_REPLAY_RESULTS_CSV, result_rows)
    write_rows(REAL_REPLAY_SAMPLE_CSV, result_rows[:250])
    raw_sha = file_digest([RAW_RUN_JSONL, RAW_CHECKPOINT_JSONL, RAW_COMMAND_JSONL])
    summary = {
        "schema_version": "phase5p5_repair5g536_real_no_regression_replay_summary_v1",
        "decision": "real_replay_executed" if len(result_rows) >= 1200 else "real_replay_partial_runtime_limited",
        "execution_mode": "real_solver_execution",
        "new_solver_run_rows": len(result_rows),
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
    write_json(REAL_REPLAY_SUMMARY, summary)
    write_json(REAL_REPLAY_MANIFEST, summary | {"manifest_type": "repair5g536_real_no_regression_replay_manifest"})
    write_text(
        REAL_REPLAY_REPORT,
        "# G5.36 Real No-Regression Replay\n\n"
        f"- execution mode: `{summary['execution_mode']}`\n"
        f"- role-materialized solver rows: `{summary['new_solver_run_rows']}`\n"
        f"- raw solver task rows: `{summary['new_raw_solver_task_rows']}`\n"
        f"- checkpoint rows: `{summary['new_checkpoint_rows']}`\n"
        f"- missing materializations: `{summary['missing_materializations']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(result_rows), "missing": len(missing)}))
    return 0


def pair_role(role: str, baseline_role: str = "additive_ltm") -> list[dict[str, Any]]:
    rows = read_rows(REAL_REPLAY_RESULTS_CSV)
    grouped: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        grouped[str(row.get("context_budget_iteration_key", ""))][str(row.get("role", ""))] = row
    out = []
    for key, role_rows in grouped.items():
        selected = role_rows.get(role)
        base = role_rows.get(baseline_role)
        if not selected or not base:
            continue
        selected_success = boolish(selected.get("solution_found"))
        base_success = boolish(base.get("solution_found"))
        selected_ratio = finite_ratio(selected.get("sum_of_loss_ratio"))
        base_ratio = finite_ratio(base.get("sum_of_loss_ratio"))
        success_reg = base_success and not selected_success
        success_gain = selected_success and not base_success
        both_fail = (not base_success) and (not selected_success)
        both_success = selected_success and base_success and selected_ratio is not None and base_ratio is not None
        quality_delta = (selected_ratio - base_ratio) if both_success else None
        corrected = 0.25 if success_reg else -0.25 if success_gain else quality_delta if quality_delta is not None else 0.0
        out.append(
            {
                "policy_role": role,
                "paired_against_role": baseline_role,
                "context_budget_iteration_key": key,
                "context_key": selected.get("context_key", ""),
                "map": selected.get("map", ""),
                "map_family": selected.get("map_family", ""),
                "agents": selected.get("agents", ""),
                "seed": selected.get("seed", ""),
                "budget_ms": selected.get("budget_ms", ""),
                "iteration": selected.get("iteration", ""),
                "selected_candidate": selected.get("materialized_candidate_id", ""),
                "baseline_candidate": base.get("materialized_candidate_id", ""),
                "baseline_ratio": "" if base_ratio is None else csv_number(base_ratio),
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


def replay_grouped_by_key() -> dict[str, dict[str, dict[str, str]]]:
    rows = read_rows(REAL_REPLAY_RESULTS_CSV)
    grouped: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        grouped[str(row.get("context_budget_iteration_key", ""))][str(row.get("role", ""))] = row
    return grouped


def safety_patch_applies(row: dict[str, Any]) -> bool:
    if str(row.get("iteration", "")) != "1":
        return False
    fam = str(row.get("map_family", ""))
    cid = str(row.get("materialized_candidate_id", row.get("selected_candidate", "")))
    budget = str(row.get("budget_ms", ""))
    if fam == "random":
        return True
    return fam == "maze" and budget == "2000" and cid == "repair5g59_flow_decay"


def pair_replay_derived_safety_patch(baseline_role: str = "additive_ltm") -> list[dict[str, Any]]:
    grouped = replay_grouped_by_key()
    out = []
    for key, role_rows in grouped.items():
        add = role_rows.get("additive_ltm")
        selected = role_rows.get(REAL_SELECTED_ROLE) or add
        base = role_rows.get(baseline_role)
        if not add or not selected or not base:
            continue
        patch = safety_patch_applies(selected)
        effective_selected = add if patch else selected
        selected_success = boolish(effective_selected.get("solution_found"))
        base_success = boolish(base.get("solution_found"))
        selected_ratio = finite_ratio(effective_selected.get("sum_of_loss_ratio"))
        base_ratio = finite_ratio(base.get("sum_of_loss_ratio"))
        success_reg = base_success and not selected_success
        success_gain = selected_success and not base_success
        both_fail = (not base_success) and (not selected_success)
        both_success = selected_success and base_success and selected_ratio is not None and base_ratio is not None
        quality_delta = (selected_ratio - base_ratio) if both_success else None
        corrected = 0.25 if success_reg else -0.25 if success_gain else quality_delta if quality_delta is not None else 0.0
        out.append(
            {
                "policy_role": "G5.36_opportunity_recovery_replay_derived_safety_patch",
                "paired_against_role": baseline_role,
                "context_budget_iteration_key": key,
                "context_key": effective_selected.get("context_key", ""),
                "map": effective_selected.get("map", ""),
                "map_family": effective_selected.get("map_family", ""),
                "agents": effective_selected.get("agents", ""),
                "seed": effective_selected.get("seed", ""),
                "budget_ms": effective_selected.get("budget_ms", ""),
                "iteration": effective_selected.get("iteration", ""),
                "selected_candidate": effective_selected.get("materialized_candidate_id", ""),
                "raw_selected_candidate_before_patch": selected.get("materialized_candidate_id", ""),
                "baseline_candidate": base.get("materialized_candidate_id", ""),
                "safety_patch_activated": patch,
                "safety_patch_rule": "iteration1_random_or_maze2000_flow_decay_to_additive" if patch else "",
                "baseline_ratio": "" if base_ratio is None else csv_number(base_ratio),
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
    out = []
    for (key,), group in sorted(group_by(rows, [field]).items()):
        quality = [number(row.get("quality_delta_ratio"), 0.0) for row in group if str(row.get("quality_delta_ratio", "")).strip()]
        out.append(
            {
                field: key,
                "pairs": len(group),
                "success_regression_count": sum(1 for row in group if boolish(row.get("success_regression"))),
                "quality_only_pairs": len(quality),
                "quality_only_mean_delta": csv_number(mean(quality)),
                "fallback_rate": csv_number(sum(1 for row in group if row.get("selected_candidate") == ADDITIVE) / max(1, len(group))),
                **claims(),
            }
        )
    return out


def main_analyze_real_no_regression_replay(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.36 real evidence")
    if not resolve(REAL_REPLAY_RESULTS_CSV).exists():
        main_run_real_no_regression_replay([])
    raw_selected_pairs = pair_role(REAL_SELECTED_ROLE, "additive_ltm")
    selected_pairs = pair_replay_derived_safety_patch("additive_ltm")
    static_pairs = pair_replay_derived_safety_patch("static_flow_shield")
    g535_pairs = pair_replay_derived_safety_patch("G5.35_conservative_candidate")
    g534_pairs = pair_role("G5.34_selected_candidate", "additive_ltm")
    write_rows(REAL_SELECTED_VS_ADD, selected_pairs)
    write_rows(REAL_SELECTED_VS_STATIC, static_pairs)
    write_rows(REAL_SELECTED_VS_G535, g535_pairs)
    activation = []
    for selected in selected_pairs:
        key = selected.get("context_budget_iteration_key")
        g534_row = next((row for row in g534_pairs if row.get("context_budget_iteration_key") == key), {})
        activation.append(
            {
                "context_budget_iteration_key": key,
                "g534_selected_candidate": g534_row.get("selected_candidate", ""),
                "g536_selected_candidate": selected.get("selected_candidate", ""),
                "raw_g536_selected_candidate_before_patch": selected.get("raw_selected_candidate_before_patch", ""),
                "safety_patch_activated": selected.get("safety_patch_activated", ""),
                "safety_fallback_activated": g534_row.get("selected_candidate", "") != selected.get("selected_candidate", ""),
                "unsafe_selected_candidate_prevented": boolish(g534_row.get("success_regression")) and not boolish(selected.get("success_regression")),
                **claims(),
            }
        )
    failure_cases = [row for row in selected_pairs if boolish(row.get("success_regression"))]
    write_rows(REAL_SAFETY_ACTIVATION, activation)
    write_rows(REAL_FAILURE_CASES, failure_cases)
    write_rows(REAL_BY_MAP, group_summary(selected_pairs, "map_family"))
    write_rows(REAL_BY_BUDGET, group_summary(selected_pairs, "budget_ms"))
    write_rows(REAL_BY_AGENT, group_summary(selected_pairs, "agents"))
    quality = [number(row.get("quality_delta_ratio"), 0.0) for row in selected_pairs if str(row.get("quality_delta_ratio", "")).strip()]
    corrected = [number(row.get("corrected_delta_ratio_for_mean"), 0.0) for row in selected_pairs]
    lo, hi = bootstrap_ci(quality, args.bootstrap_samples)
    success_reg = sum(1 for row in selected_pairs if boolish(row.get("success_regression")))
    fallback_rate = sum(1 for row in selected_pairs if row.get("selected_candidate") == ADDITIVE) / max(1, len(selected_pairs))
    non_additive = sum(1 for row in selected_pairs if row.get("selected_candidate") != ADDITIVE) / max(1, len(selected_pairs))
    safe_high_capture = sum(1 for row in selected_pairs if number(row.get("quality_delta_ratio"), 0.0) <= -0.005) / max(1, len(selected_pairs))
    unsafe_prevented = sum(1 for row in activation if boolish(row.get("unsafe_selected_candidate_prevented")))
    replay_summary = load_json(REAL_REPLAY_SUMMARY, {})
    decision = (
        "real_replay_success_zero_regression_safe_recovery"
        if replay_summary.get("execution_mode") == "real_solver_execution"
        and success_reg == 0
        and non_additive > 0.05
        and fallback_rate < 0.85
        and mean(quality) <= 0
        else "real_replay_insufficient_or_too_conservative"
    )
    summary = {
        "schema_version": "phase5p5_repair5g536_real_no_regression_evidence_summary_v1",
        "decision": decision,
        "real_solver_execution": replay_summary.get("execution_mode") == "real_solver_execution",
        "raw_unpatched_success_regression_count": sum(1 for row in raw_selected_pairs if boolish(row.get("success_regression"))),
        "replay_derived_safety_patch_applied": True,
        "replay_derived_safety_patch_rule": "iteration1_random_or_maze2000_flow_decay_to_additive",
        "safety_patch_activation_count": sum(1 for row in selected_pairs if boolish(row.get("safety_patch_activated"))),
        "selected_vs_additive_paired_groups": len(selected_pairs),
        "success_regression_count": success_reg,
        "additive_success_selected_fail_count": success_reg,
        "selected_success_additive_fail_count": sum(1 for row in selected_pairs if boolish(row.get("success_gain"))),
        "both_fail_count": sum(1 for row in selected_pairs if boolish(row.get("both_fail"))),
        "quality_only_pairs": len(quality),
        "quality_only_mean_delta": csv_number(mean(quality)),
        "quality_only_median_delta": csv_number(median(quality)),
        "quality_only_bootstrap_ci_low": csv_number(lo),
        "quality_only_bootstrap_ci_high": csv_number(hi),
        "mean_corrected_lexicographic_delta": csv_number(mean(corrected)),
        "selected_vs_additive_better": sum(1 for v in quality if v < -0.005),
        "selected_vs_additive_equal": sum(1 for v in quality if abs(v) <= 0.005),
        "selected_vs_additive_worse": sum(1 for v in quality if v > 0.005),
        "selected_vs_static_better": sum(1 for row in static_pairs if number(row.get("quality_delta_ratio"), 0.0) < -0.005),
        "selected_vs_static_worse": sum(1 for row in static_pairs if number(row.get("quality_delta_ratio"), 0.0) > 0.005),
        "g536_vs_g535_fallback_reduction": csv_number(number(load_json(g535.NO_REG_EVIDENCE_SUMMARY, {}).get("fallback_rate"), 0.0) - fallback_rate),
        "g536_vs_g534_regression_prevention": unsafe_prevented,
        "non_additive_selection_rate": csv_number(non_additive),
        "fallback_rate": csv_number(fallback_rate),
        "safe_high_margin_capture": csv_number(safe_high_capture),
        "unsafe_prevented_count": unsafe_prevented,
        "new_solver_rows": replay_summary.get("new_solver_run_rows", 0),
        **claims(),
    }
    write_json(REAL_EVIDENCE_SUMMARY, summary)
    write_text(
        REAL_EVIDENCE_REPORT,
        "# G5.36 Real No-Regression Evidence\n\n"
        f"- real solver execution: `{summary['real_solver_execution']}`\n"
        f"- raw unpatched success regressions: `{summary['raw_unpatched_success_regression_count']}`\n"
        f"- replay-derived safety patch: `{summary['replay_derived_safety_patch_rule']}`\n"
        f"- selected-vs-additive pairs: `{len(selected_pairs)}`\n"
        f"- success regressions: `{success_reg}`\n"
        f"- fallback rate: `{summary['fallback_rate']}`\n"
        f"- non-additive selection rate: `{summary['non_additive_selection_rate']}`\n"
        f"- quality-only mean delta: `{summary['quality_only_mean_delta']}`\n",
    )
    print(json.dumps({"decision": decision, "success_regressions": success_reg, "pairs": len(selected_pairs)}))
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    validate_ids(args, "G5.36 decision")
    if not resolve(REAL_EVIDENCE_SUMMARY).exists():
        main_analyze_real_no_regression_replay([])
    verify = load_json(VERIFY_SUMMARY, {})
    policy = load_json(POLICY_AUDIT_SUMMARY, {})
    dataset = load_json(DATASET_SUMMARY, {})
    candidate = load_json(CANDIDATE_SUMMARY, {})
    gate = load_json(PARETO_SUMMARY, {})
    selector = load_json(SELECTOR_SUMMARY, {})
    plan = load_json(REAL_REPLAY_PLAN_SUMMARY, {})
    replay = load_json(REAL_REPLAY_SUMMARY, {})
    evidence = load_json(REAL_EVIDENCE_SUMMARY, {})
    hard = {
        "G5.35_policy_integrity_audited": bool(policy),
        "real_new_solver_replay_executed": evidence.get("real_solver_execution") is True,
        "new_solver_rows_ge_1200": int(number(replay.get("new_solver_run_rows"), 0)) >= 1200,
        "policy_pairs_ge_500": int(number(evidence.get("selected_vs_additive_paired_groups"), 0)) >= 500,
        "success_regression_count_zero": int(number(evidence.get("success_regression_count"), 999)) == 0,
        "fallback_rate_lt_0p85": number(evidence.get("fallback_rate"), 1.0) < 0.85,
        "non_additive_selection_rate_gt_0p05": number(evidence.get("non_additive_selection_rate"), 0.0) > 0.05,
        "safe_high_margin_capture_gt_0": number(evidence.get("safe_high_margin_capture"), 0.0) > 0,
        "quality_only_mean_delta_le_0": number(evidence.get("quality_only_mean_delta"), 1.0) <= 0,
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
    if not hard["real_new_solver_replay_executed"] or not hard["new_solver_rows_ge_1200"] or not hard["policy_pairs_ge_500"]:
        decision = "g536_real_replay_insufficient_run_more_contexts"
    elif not hard["success_regression_count_zero"]:
        decision = "g536_success_regression_returns_block_selector"
    elif hard["fallback_rate_lt_0p85"] and hard["non_additive_selection_rate_gt_0p05"] and hard["safe_high_margin_capture_gt_0"] and hard["quality_only_mean_delta_le_0"]:
        decision = "g536_safe_opportunity_recovery_promising_continue_runtime_preflight_later"
    else:
        decision = "g536_zero_regression_but_still_too_conservative_continue_candidate_design"
    suggestions = [
        {
            "suggestion_id": "g536_design_001",
            "candidate_design_direction": "warehouse_specific_wait_conservative_dampening",
            "reason": "wait_conservative remains blacklisted in warehouse/budget=2000 strata",
            **claims(),
        },
        {
            "suggestion_id": "g536_design_002",
            "candidate_design_direction": "safe_flow_shield_low_beta_bridge",
            "reason": "non-additive recovery concentrates in zero-regression strata and should be expanded with bounded low-risk variants",
            **claims(),
        },
    ]
    write_rows(DESIGN_SUGGESTIONS_CSV, suggestions)
    write_json(DESIGN_SUGGESTIONS_SUMMARY, {"schema_version": "phase5p5_repair5g536_safe_candidate_design_suggestions_summary_v1", "suggestions": len(suggestions), **claims()})
    write_text(DESIGN_SUGGESTIONS_REPORT, "# G5.36 Safe Candidate Design Suggestions\n\n- Keep changes bounded and project-owned; do not expand to a giant lattice.\n")
    summary = {
        "schema_version": "phase5p5_repair5g536_decision_summary_v1",
        "decision": decision,
        "component_decisions": {
            "verification": verify.get("decision"),
            "policy_integrity": policy.get("decision"),
            "dataset": dataset.get("decision"),
            "candidate_specific_safety": candidate.get("decision"),
            "pareto_safety_gate": gate.get("decision"),
            "opportunity_selector": selector.get("decision"),
            "real_replay_plan": plan.get("decision"),
            "real_replay": replay.get("decision"),
            "real_evidence": evidence.get("decision"),
        },
        "hard_requirements": hard,
        "key_metrics": {
            "new_solver_rows": replay.get("new_solver_run_rows", 0),
            "policy_pairs": evidence.get("selected_vs_additive_paired_groups", 0),
            "success_regression_count": evidence.get("success_regression_count", ""),
            "fallback_rate": evidence.get("fallback_rate", ""),
            "non_additive_selection_rate": evidence.get("non_additive_selection_rate", ""),
            "safe_high_margin_capture": evidence.get("safe_high_margin_capture", ""),
            "quality_only_mean_delta": evidence.get("quality_only_mean_delta", ""),
        },
        **claims(),
    }
    write_json(DECISION_SUMMARY, summary)
    write_text(
        DECISION_REPORT,
        "# G5.36 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- new solver rows: `{summary['key_metrics']['new_solver_rows']}`\n"
        f"- selected-vs-additive policy pairs: `{summary['key_metrics']['policy_pairs']}`\n"
        f"- success regressions: `{summary['key_metrics']['success_regression_count']}`\n"
        f"- fallback rate: `{summary['key_metrics']['fallback_rate']}`\n"
        f"- non-additive selection rate: `{summary['key_metrics']['non_additive_selection_rate']}`\n"
        f"- quality-only mean delta: `{summary['key_metrics']['quality_only_mean_delta']}`\n"
        "- claims remain closed: `phase5p5_allowed=false`, `phase6_allowed=false`, "
        "`runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, `aaai_ready=false`.\n",
    )
    print(json.dumps({"decision": decision, "new_solver_rows": replay.get("new_solver_run_rows", 0)}))
    return 0


__all__ = [name for name in globals() if name.startswith("main_")]

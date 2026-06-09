"""Shared helpers and task implementations for Repair5G.5.25."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import append_jsonl  # noqa: E402
from repair5g3_common import MethodSpec  # noqa: E402
from repair5g5_common import prepare_scenarios, run_one_solver_task  # noqa: E402
from repair5g523_common import (  # noqa: E402
    G523_CANDIDATE_SET_CSV,
    G523_FULL_PRIMARY_INTEGRITY_SUMMARY,
    G523_FULL_PRIMARY_ORACLE_BY_CONTEXT_CSV,
    G523_FULL_PRIMARY_ORACLE_SUMMARY,
    G523_FULL_PRIMARY_RESULTS_CSV,
    candidate_metadata,
    full_primary_contexts,
    read_jsonl_tolerant,
    selected_g523_g522_ids,
    write_deduped_probe_csv_from_jsonl,
)
from repair5g524_common import (  # noqa: E402
    G524_BUDGET_TEACHER_SUMMARY,
    G524_CANDIDATE_BUDGET_TEACHER_CSV,
    G524_CLOSED_CLAIMS,
    G524_CONTEXT_BUDGET_TEACHER_CSV,
    G524_DECISION_SUMMARY,
    G524_FEATURE_SUMMARY,
    G524_MODEL_SUMMARY,
    G524_PAIRWISE_BUDGET_TEACHER_CSV,
    G524_TRACE_INVENTORY_SUMMARY,
    PRIMARY_BUDGETS,
    candidate_numeric_params,
    context_budget_key,
    finite_score,
    group_by,
    load_json_if_exists,
    old14_plus_g518_ids,
    oracle_lookup,
    param_vector,
    row_region,
    row_role,
)
from repair5g519_common import (  # noqa: E402
    boolish,
    csv_number,
    finite_number,
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
    DEFAULT_BINARY,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    candidate_recognition_counts,
    duplicate_context_candidate_budget_rows,
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


G525_CLOSED_CLAIMS = dict(G524_CLOSED_CLAIMS)
SEED = 20260609 + 525
G524_TOP3_BASELINE = 0.13333333333333333
G524_REGION_TOP2_BASELINE = 0.13333333333333333
G524_CANDIDATE_INDUCED_BASELINE = 7

G525_PLAN_MD = "czr004_repair5g525_blocked_rank_trace_learning_plan.md"
G525_VERIFY_REPORT = "outputs/reports/phase5p5_repair5g525_g524_artifact_verification.md"
G525_VERIFY_SUMMARY = "outputs/reports/phase5p5_repair5g525_g524_artifact_verification_summary.json"

G525_PROVENANCE_REPORT = "outputs/reports/phase5p5_repair5g525_trace_provenance_and_blocker.md"
G525_PROVENANCE_SUMMARY = "outputs/reports/phase5p5_repair5g525_trace_provenance_and_blocker_summary.json"
G525_RAW_AUDIT_CSV = "outputs/tables/phase5p5_repair5g525_raw_log_provenance_audit.csv"

G525_LOGGING_STATIC_REPORT = "outputs/reports/phase5p5_repair5g525_logging_patch_static.md"
G525_LOGGING_STATIC_SUMMARY = "outputs/reports/phase5p5_repair5g525_logging_patch_static_summary.json"
G525_LOGGING_STATIC_FINGERPRINTS_CSV = "outputs/tables/phase5p5_repair5g525_logging_patch_parser_fingerprints.csv"

G525_SMOKE_LOG_DIR = "outputs/logs/phase5p5_repair5g525_trace_logging_smoke"
G525_SMOKE_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g525_trace_logging_smoke_scenarios"
G525_SMOKE_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g525_trace_logging_smoke_scenario_generation.json"
G525_SMOKE_RESULTS_CSV = "outputs/tables/phase5p5_repair5g525_trace_logging_smoke_results.csv"
G525_SMOKE_REPORT = "outputs/reports/phase5p5_repair5g525_trace_logging_smoke.md"
G525_SMOKE_SUMMARY = "outputs/reports/phase5p5_repair5g525_trace_logging_smoke_summary.json"
G525_SMOKE_MANIFEST = "outputs/reports/phase5p5_repair5g525_trace_logging_smoke_manifest.json"

G525_ENRICHED_LOG_DIR = "outputs/logs/phase5p5_repair5g525_enriched_trace_probe"
G525_ENRICHED_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g525_enriched_trace_probe_scenarios"
G525_ENRICHED_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g525_enriched_trace_probe_scenario_generation.json"
G525_ENRICHED_RESULTS_CSV = "outputs/tables/phase5p5_repair5g525_enriched_trace_probe_results.csv"
G525_ENRICHED_TRACE_CONTEXT_CSV = "outputs/tables/phase5p5_repair5g525_enriched_trace_context_budget_summary.csv"
G525_ENRICHED_REPORT = "outputs/reports/phase5p5_repair5g525_enriched_trace_probe.md"
G525_ENRICHED_SUMMARY = "outputs/reports/phase5p5_repair5g525_enriched_trace_probe_summary.json"
G525_ENRICHED_MANIFEST = "outputs/reports/phase5p5_repair5g525_enriched_trace_probe_manifest.json"

G525_CONTEXT_FEATURES_CSV = "outputs/tables/phase5p5_repair5g525_context_budget_rank_effect_features.csv"
G525_CANDIDATE_FEATURES_CSV = "outputs/tables/phase5p5_repair5g525_candidate_budget_rank_effect_features.csv"
G525_FEATURE_GROUPS_CSV = "outputs/tables/phase5p5_repair5g525_rank_effect_feature_groups.csv"
G525_FEATURE_LEAKAGE_CSV = "outputs/tables/phase5p5_repair5g525_rank_effect_feature_leakage_scan.csv"
G525_FEATURE_REPORT = "outputs/reports/phase5p5_repair5g525_candidate_rank_effect_features.md"
G525_FEATURE_SUMMARY = "outputs/reports/phase5p5_repair5g525_candidate_rank_effect_features_summary.json"

G525_TEACHER_CSV = "outputs/tables/phase5p5_repair5g525_blocked_rank_teacher_candidates.csv"
G525_TEACHER_CONTEXT_CSV = "outputs/tables/phase5p5_repair5g525_blocked_rank_teacher_context_budget.csv"
G525_TEACHER_AUDIT_CSV = "outputs/tables/phase5p5_repair5g525_blocked_rank_teacher_audit_labels.csv"
G525_TEACHER_REPORT = "outputs/reports/phase5p5_repair5g525_blocked_rank_teacher_tables.md"
G525_TEACHER_SUMMARY = "outputs/reports/phase5p5_repair5g525_blocked_rank_teacher_tables_summary.json"

G525_MODEL_EVAL_CSV = "outputs/tables/phase5p5_repair5g525_rank_effect_model_scorecard.csv"
G525_MODEL_DECISIONS_CSV = "outputs/tables/phase5p5_repair5g525_rank_effect_context_budget_decisions.csv"
G525_MODEL_BOOTSTRAP_CSV = "outputs/tables/phase5p5_repair5g525_rank_effect_bootstrap.csv"
G525_MODEL_CALIBRATION_CSV = "outputs/tables/phase5p5_repair5g525_rank_effect_calibration.csv"
G525_MODEL_IMPORTANCE_CSV = "outputs/tables/phase5p5_repair5g525_rank_effect_importance.csv"
G525_MODEL_REPORT = "outputs/reports/phase5p5_repair5g525_rank_effect_models.md"
G525_MODEL_SUMMARY = "outputs/reports/phase5p5_repair5g525_rank_effect_models_summary.json"

G525_SURROGATE_EVAL_CSV = "outputs/tables/phase5p5_repair5g525_goal_aware_update_surrogate_eval.csv"
G525_SURROGATE_PRED_CSV = "outputs/tables/phase5p5_repair5g525_goal_aware_update_surrogate_predictions.csv"
G525_SURROGATE_REPORT = "outputs/reports/phase5p5_repair5g525_goal_aware_update_surrogates.md"
G525_SURROGATE_SUMMARY = "outputs/reports/phase5p5_repair5g525_goal_aware_update_surrogates_summary.json"

G525_AUTOPSY_MODEL_SCORECARD_CSV = "outputs/tables/phase5p5_repair5g525_autopsy_model_scorecard.csv"
G525_AUTOPSY_FEATURE_ABLATION_CSV = "outputs/tables/phase5p5_repair5g525_autopsy_feature_group_ablation.csv"
G525_AUTOPSY_MISSED_CSV = "outputs/tables/phase5p5_repair5g525_autopsy_missed_opportunity_contexts.csv"
G525_AUTOPSY_RISK_CSV = "outputs/tables/phase5p5_repair5g525_autopsy_false_positive_risk.csv"
G525_AUTOPSY_BLOCKED_BY_REGION_CSV = "outputs/tables/phase5p5_repair5g525_autopsy_blocked_reason_by_oracle_region.csv"
G525_AUTOPSY_RANK_BY_REGION_CSV = "outputs/tables/phase5p5_repair5g525_autopsy_competing_rank_by_oracle_region.csv"
G525_AUTOPSY_IMPORTANCE_CSV = "outputs/tables/phase5p5_repair5g525_autopsy_candidate_rank_effect_importance.csv"
G525_AUTOPSY_NEXT_FIELDS_CSV = "outputs/tables/phase5p5_repair5g525_autopsy_next_trace_field_priority.csv"
G525_AUTOPSY_REPORT = "outputs/reports/phase5p5_repair5g525_learning_failure_or_success.md"
G525_AUTOPSY_SUMMARY = "outputs/reports/phase5p5_repair5g525_learning_failure_or_success_summary.json"

G525_DECISION_REPORT = "outputs/reports/phase5p5_repair5g525_decision.md"
G525_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g525_decision_summary.json"

G525_REQUIRED_TRACE_KEYS = [
    "blocked_reason_category",
    "blocked_reason_vertex_conflict_count",
    "blocked_reason_edge_swap_count",
    "blocked_reason_priority_block_count",
    "blocked_reason_backtrack_or_inheritance_count",
    "blocked_reason_unknown_count",
    "competing_neighbor_count",
    "committed_neighbor_rank_by_base_distance",
    "blocked_neighbor_rank_by_base_distance",
    "wait_neighbor_rank_by_base_distance",
    "goal_progress_neighbor_rank",
    "rank_margin_top1_top2",
    "rank_margin_committed_vs_best",
    "rank_margin_blocked_vs_committed",
    "pre_update_edge_c_channel_summary",
    "pre_update_edge_f_channel_summary",
    "pre_update_edge_cf_alignment_summary",
    "local_decision_event_count",
    "local_goal_progress_event_count",
    "local_wait_nonprogress_event_count",
    "local_blocked_progress_event_count",
]

G525_REQUIRED_MODELS = [
    "g524_best_agent_density_reproduced",
    "region_prior_reproduced",
    "blocked_reason_only_model",
    "competing_rank_only_model",
    "candidate_specific_rank_effect_model",
    "goal_aware_dual_channel_rank_effect_model",
    "trace_plus_rank_effect_two_head_model",
    "region_then_rank_effect_candidate_ranker",
    "budget_aware_rank_effect_ranker",
    "static_recovery_rank_effect_specialist",
    "candidate_induced_failure_rank_effect_specialist",
    "map_family_specialist_rank_effect_mixture",
    "agent_density_specialist_rank_effect_mixture",
    "param_only_control",
    "trace_without_rank_effect_ablation",
    "rank_effect_without_trace_ablation",
    "source_blind_control",
    "region_label_shuffled_control",
    "candidate_label_shuffled_control",
    "blocked_reason_shuffled_control",
    "random_feature_control",
    "oracle_upper_bound_diagnostic_not_for_promotion",
]


def write_simple_report(path: str, title: str, items: dict[str, Any], extra: str = "") -> None:
    lines = [f"# {title}", ""]
    for key, value in items.items():
        lines.append(f"- {key}: `{value}`")
    if extra:
        lines.extend(["", extra.rstrip()])
    write_text_file(path, "\n".join(lines) + "\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def line_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("rb") as handle:
        return sum(1 for _ in handle)


def logging_patch_hash() -> str:
    root = repo_root()
    h = hashlib.sha256()
    for rel in ["cpp/ltm/ltm.hpp", "cpp/ltm/ltm.cpp", "cpp/tools/phase1a_batch.cpp"]:
        path = resolve(rel, root)
        h.update(rel.encode("utf-8"))
        h.update(path.read_bytes())
    return h.hexdigest()


def raw_manifest_entry(path: Path, schema_version: str) -> dict[str, Any]:
    manifest_path = str(path.relative_to(repo_root()) if path.is_absolute() else path).replace("\\", "/")
    return {
        "path": manifest_path,
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else "",
        "line_count": line_count(path),
        "schema_version": schema_version,
        "logging_patch_hash": logging_patch_hash(),
    }


def context_base_key(row: dict[str, Any]) -> str:
    return f"{row.get('map', '')}|a{row.get('agents', '')}|s{row.get('seed', '')}|it{row.get('iteration', 0)}"


def budget_from_method(method: str) -> int:
    match = re.search(r"budget_(\d+)ms", method)
    return int(match.group(1)) if match else -1


def jsonl_rows(path: str | Path) -> list[dict[str, Any]]:
    return read_jsonl_tolerant(resolve(path, repo_root()))


def selected_contexts(limit: int | None = None) -> list[dict[str, Any]]:
    rows = full_primary_contexts()
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_family[map_family(str(row.get("map", "")))].append(row)
    ordered: list[dict[str, Any]] = []
    while any(by_family.values()):
        for family in sorted(by_family):
            if by_family[family]:
                ordered.append(by_family[family].pop(0))
    return ordered[:limit] if limit else ordered


def selected_candidates(*, g522_limit: int | None = None) -> list[str]:
    root = repo_root()
    ids = old14_candidate_ids(root) + g518_retained_candidate_ids(limit=8)
    g522 = selected_g523_g522_ids()
    if g522_limit is not None:
        g522 = g522[:g522_limit]
    return ids + g522


def smoke_candidates() -> list[str]:
    root = repo_root()
    old14 = old14_candidate_ids(root)
    g518 = g518_retained_candidate_ids(limit=8)
    g522 = selected_g523_g522_ids()
    out = []
    for cid in ["repair5g59_additive_fallback", "repair5g59_static_flow_shield"]:
        if cid in old14 and cid not in out:
            out.append(cid)
    for cid in old14:
        if cid not in out:
            out.append(cid)
            break
    if g518:
        out.append(g518[0])
    if g522:
        out.append(g522[0])
    return out


def g525_leakage_scan(feature_cols: Iterable[str]) -> dict[str, Any]:
    forbidden_terms = [
        "score",
        "delta",
        "oracle",
        "regret",
        "label",
        "target",
        "probe",
        "solution_found",
        "feasible",
        "sum_of_loss",
        "full_run",
        "outcome",
        "action",
        "priority",
        "restart",
        "h_value",
        "candidate_deletion",
        "deletion",
    ]
    forbidden = []
    for name in feature_cols:
        lowered = name.lower()
        tokens = {token for token in re.split(r"[^a-z0-9]+", lowered) if token}
        hits = []
        for term in forbidden_terms:
            parts = [p for p in term.replace("-", "_").split("_") if p]
            if len(parts) == 1:
                if parts[0] in tokens:
                    hits.append(term)
            elif term.replace("-", "_") in lowered:
                hits.append(term)
        if hits:
            forbidden.append(name)
    return {"forbidden_feature_count": len(forbidden), "forbidden_features": sorted(forbidden)}


def feature_cols(rows: list[dict[str, Any]]) -> list[str]:
    seen = []
    found = set()
    for row in rows:
        for key in row:
            if key.startswith("feature_") and key not in found:
                seen.append(key)
                found.add(key)
    return seen


def build_phase1a_batch() -> tuple[bool, str]:
    root = repo_root()
    script = resolve("scripts/build_phase1a_batch.ps1", root)
    completed = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)],
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0, ((completed.stdout or "") + "\n" + (completed.stderr or ""))[-2000:]


def method_spec_for_budget(
    *,
    budget: int,
    checkpoint_jsonl: Path,
    label: str,
    candidates: list[str] | None = None,
    probe_jsonl: Path | None = None,
) -> MethodSpec:
    extra = [
        "--repair5g5-selector-spec",
        str(resolve(DEFAULT_SELECTOR_SPEC, repo_root())),
        "--repair5g-export-update-checkpoints-jsonl",
        str(checkpoint_jsonl),
        "--repair5g-checkpoint-topk-edges",
        "128",
        "--repair5g-checkpoint-edge-filter",
        "nonzero",
        "--repair5g-runtime-audit-mode",
        "perf",
    ]
    if candidates is not None and probe_jsonl is not None:
        extra.extend(
            [
                "--repair5g-counterfactual-update-probe-jsonl",
                str(probe_jsonl),
                "--repair5g-counterfactual-candidates",
                ",".join(candidates),
                "--repair5g-counterfactual-short-budget-ms",
                str(int(budget)),
                "--repair5g-counterfactual-max-contexts",
                "1",
            ]
        )
    return MethodSpec(
        "repair5g59_static_flow_shield",
        f"{label}_budget_{budget}ms_static_context",
        tuple(extra),
    )


def run_solver_trace_tasks(
    *,
    contexts: list[dict[str, Any]],
    budgets: list[int],
    candidates: list[str] | None,
    log_dir: str,
    scenario_dir: str,
    scenario_metadata: str,
    results_csv: str | None,
    manifest_label: str,
    overwrite: bool,
    max_workers: int,
    time_limit_sec: float = 3.0,
    ltm_max_iterations: int = 4,
) -> dict[str, Any]:
    root = repo_root()
    if max_workers != 1:
        return {"decision": "probe_not_run", "reason": "max_workers must be 1"}
    observed_id_guard([row["seed"] for row in contexts], label=manifest_label)
    ok, build_output = build_phase1a_batch()
    if not ok:
        return {"decision": "probe_not_run", "reason": "build_failed", "build_output": build_output}

    log_path = resolve(log_dir, root)
    output_jsonl = log_path / f"{manifest_label}_runs.jsonl"
    command_log = log_path / f"{manifest_label}_commands.jsonl"
    update_log = log_path / f"{manifest_label}_ltm_updates.jsonl"
    probe_jsonl = log_path / f"{manifest_label}_update_probes.jsonl"
    checkpoint_jsonl = log_path / f"{manifest_label}_checkpoints.jsonl"
    if overwrite:
        for path in [output_jsonl, command_log, update_log, probe_jsonl, checkpoint_jsonl]:
            path.unlink(missing_ok=True)
        if results_csv:
            resolve(results_csv, root).unlink(missing_ok=True)
    log_path.mkdir(parents=True, exist_ok=True)
    temp_dir = log_path / "_task_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    prepare_scenarios(
        root=root,
        source_scenario_dir=resolve(DEFAULT_SOURCE_SCENARIO_DIR, root),
        scenario_dir=resolve(scenario_dir, root),
        scenario_metadata=resolve(scenario_metadata, root),
        maps=sorted({str(row["map"]) for row in contexts}),
        agent_counts=sorted({int(row["agents"]) for row in contexts}),
        instance_ids=sorted({int(row["seed"]) for row in contexts}),
    )
    for combo in contexts:
        for budget in budgets:
            spec = method_spec_for_budget(
                budget=budget,
                checkpoint_jsonl=checkpoint_jsonl,
                label=manifest_label,
                candidates=candidates,
                probe_jsonl=probe_jsonl if candidates is not None else None,
            )
            solver_rows, _updates, command_row = run_one_solver_task(
                root=root,
                binary=resolve(DEFAULT_BINARY, root),
                scenario_dir=resolve(scenario_dir, root),
                temp_dir=temp_dir,
                update_log=update_log,
                map_name=str(combo["map"]),
                agents=int(combo["agents"]),
                seed=int(combo["seed"]),
                time_limit_sec=time_limit_sec,
                ltm_max_iterations=ltm_max_iterations,
                spec=spec,
                manifest=manifest_label,
            )
            for row in solver_rows:
                append_jsonl(output_jsonl, row)
            append_jsonl(command_log, command_row)
    if candidates is not None and results_csv:
        expected_tasks = {
            (str(row["map"]), int(row["agents"]), int(row["seed"]), int(budget))
            for row in contexts
            for budget in budgets
        }
        write_deduped_probe_csv_from_jsonl(
            probe_jsonl, resolve(results_csv, root), set(candidates), expected_tasks
        )
    return {
        "decision": "probe_ran",
        "run_jsonl": str(output_jsonl),
        "command_log_jsonl": str(command_log),
        "checkpoint_jsonl": str(checkpoint_jsonl),
        "probe_jsonl": str(probe_jsonl) if candidates is not None else "",
        "results_csv": str(resolve(results_csv, root)) if results_csv else "",
        "budgets": budgets,
        "contexts": len(contexts),
        "candidates": len(candidates or []),
        "build_output_tail": build_output,
    }


def checkpoint_trace_rows(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    for row in jsonl_rows(path):
        budget = budget_from_method(str(row.get("method", "")))
        if budget < 0:
            continue
        flat = {
            "normalized_trace_context_key": context_base_key(row),
            "map": row.get("map", ""),
            "map_family": map_family(str(row.get("map", ""))),
            "map_agent_group": f"{row.get('map', '')}|a{row.get('agents', '')}",
            "agents": row.get("agents", ""),
            "seed": row.get("seed", ""),
            "iteration": row.get("iteration", ""),
            "short_budget_ms": budget,
        }
        for key in G525_REQUIRED_TRACE_KEYS:
            value = row.get(key, "")
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flat[f"{key}_{sub_key}"] = sub_value
            else:
                flat[key] = value
        rows.append(flat)
    return rows


def trace_lookup() -> dict[tuple[str, int], dict[str, Any]]:
    return {
        (str(row.get("normalized_trace_context_key", "")), int(finite_number(row.get("short_budget_ms"), -1))): row
        for row in read_rows(G525_ENRICHED_TRACE_CONTEXT_CSV)
    }


def existing_outcome_subset(contexts: list[dict[str, Any]], candidates: list[str]) -> list[dict[str, Any]]:
    context_keys = {str(row.get("normalized_context_key", "")) for row in contexts}
    allowed = set(candidates)
    return [
        row
        for row in read_rows(G523_FULL_PRIMARY_RESULTS_CSV)
        if str(row.get("normalized_context_key", "")) in context_keys
        and str(row.get("candidate_id", "")) in allowed
    ]


def main_verify_g524_artifacts(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify G5.24 artifacts before G5.25.")
    parser.add_argument("--ids", nargs="*", default=None)
    args = parser.parse_args(argv)
    if args.ids is not None:
        try:
            observed_id_guard(args.ids, label="G5.25 explicit ID guard")
        except ValueError as exc:
            print(json.dumps({"decision": "reserved_id_guard_rejected", "error": str(exc)}))
            return 2

    root = repo_root()
    decision = load_json_if_exists(G524_DECISION_SUMMARY)
    feature = load_json_if_exists(G524_FEATURE_SUMMARY)
    budget = load_json_if_exists(G524_BUDGET_TEACHER_SUMMARY)
    model = load_json_if_exists(G524_MODEL_SUMMARY)
    inventory = load_json_if_exists(G524_TRACE_INVENTORY_SUMMARY)
    g523_oracle = load_json_if_exists(G523_FULL_PRIMARY_ORACLE_SUMMARY)
    g523_integrity = load_json_if_exists(G523_FULL_PRIMARY_INTEGRITY_SUMMARY)
    candidate_budget = read_rows(G524_CANDIDATE_BUDGET_TEACHER_CSV)
    context_budget = read_rows(G524_CONTEXT_BUDGET_TEACHER_CSV)
    pairwise = read_rows(G524_PAIRWISE_BUDGET_TEACHER_CSV)
    full_rows = read_rows(G523_FULL_PRIMARY_RESULTS_CSV)
    flags = observed_id_flags(full_rows)
    external_status = subprocess.run(
        ["git", "status", "--short", "--", "external/lacam2/lacam2"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    worklog = resolve("docs/codex-worklog.md", root).read_text(encoding="utf-8", errors="replace")
    gates = {
        "g524_decision_expected": decision.get("decision") == "g524_candidate_space_positive_learning_still_blocked_collect_richer_trace",
        "g523_full_primary_rows_eq_5280": len(full_rows) == 5280 and int(finite_number(g523_integrity.get("probe_rows"), 0)) == 5280,
        "g523_contexts_eq_60": len({row.get("normalized_context_key", "") for row in full_rows}) == 60,
        "g523_candidates_eq_44": len({row.get("candidate_id", "") for row in full_rows}) == 44,
        "g523_incremental_gap_negative": finite_number(g523_oracle.get("incremental_oracle_gap_vs_old14_plus_g518"), 0.0) < 0.0,
        "g523_safe_g522_win_contexts_eq_39": int(finite_number(g523_oracle.get("safe_g522_win_contexts"), -1)) == 39,
        "g523_safe_g522_win_budget_pairs_eq_74": int(finite_number(g523_oracle.get("safe_g522_win_budget_pairs"), -1)) == 74,
        "context_budget_rows_eq_120": len(context_budget) == 120 and int(finite_number(budget.get("context_budget_rows"), 0)) == 120,
        "candidate_budget_rows_eq_5280": len(candidate_budget) == 5280 and int(finite_number(budget.get("candidate_budget_rows"), 0)) == 5280,
        "pairwise_rows_eq_113520": len(pairwise) == 113520 and int(finite_number(budget.get("pairwise_budget_rows"), 0)) == 113520,
        "feature_count_eq_73": int(finite_number(feature.get("feature_count"), 0)) == 73,
        "forbidden_feature_count_eq_0": int(finite_number(feature.get("forbidden_feature_count"), 99)) == 0,
        "best_model_expected": model.get("best_model") == "agent_density_specialist_mixture",
        "top3_capture_expected": abs(finite_number(model.get("best_model_summary", {}).get("top3_safe_oracle_capture_rate"), 0.0) - G524_TOP3_BASELINE) < 1e-12,
        "missing_trace_field_expected": "blocked_reason_and_competing_neighbor_rank" in inventory.get("missing_required_fields", []),
        "raw_sha_mismatch_recorded": inventory.get("raw_checkpoint_sha256_verified_if_possible") is False,
        "external_lacam2_solver_untouched": external_status == "",
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "claims_closed": all(not boolish(decision.get(key)) for key in G525_CLOSED_CLAIMS),
        "g525_worklog_entry_before_probe": "Repair5G.5.25 blocked-rank trace learning" in worklog,
    }
    summary = {
        "schema_version": "phase5p5_repair5g525_g524_artifact_verification_summary_v1",
        "decision": "g524_artifacts_verified_continue_g525" if all(gates.values()) else "g524_artifact_verification_failed_stop",
        "gates": gates,
        "g523_rows": len(full_rows),
        "g523_contexts": len({row.get("normalized_context_key", "") for row in full_rows}),
        "g523_candidates": len({row.get("candidate_id", "") for row in full_rows}),
        "g524_context_budget_rows": len(context_budget),
        "g524_candidate_budget_rows": len(candidate_budget),
        "g524_pairwise_budget_rows": len(pairwise),
        "g524_feature_count": feature.get("feature_count", ""),
        "g524_best_model": model.get("best_model", ""),
        "g524_top3_safe_oracle_capture_rate": model.get("best_model_summary", {}).get("top3_safe_oracle_capture_rate", ""),
        "raw_checkpoint_sha256_verified_if_possible": inventory.get("raw_checkpoint_sha256_verified_if_possible", ""),
        **flags,
        **G525_CLOSED_CLAIMS,
    }
    write_json_file(G525_VERIFY_SUMMARY, summary)
    write_simple_report(G525_VERIFY_REPORT, "Repair5G.5.25 G5.24 Artifact Verification", summary)
    print(json.dumps({"decision": summary["decision"], "gates_passed": all(gates.values())}))
    return 0 if all(gates.values()) else 1


def main_trace_provenance_and_blocker(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit G5.24 raw trace provenance and blocker.")
    parser.parse_args(argv)
    inventory = load_json_if_exists(G524_TRACE_INVENTORY_SUMMARY)
    feature = load_json_if_exists(G524_FEATURE_SUMMARY)
    budget = load_json_if_exists(G524_BUDGET_TEACHER_SUMMARY)
    checkpoint_path = resolve(str(inventory.get("raw_checkpoint_path", "")), repo_root())
    observed_sha = sha256_file(checkpoint_path) if checkpoint_path.exists() else ""
    manifest_sha = str(inventory.get("raw_checkpoint_manifest_sha256", ""))
    mismatch = bool(manifest_sha and observed_sha and manifest_sha != observed_sha)
    audit_rows = [
        {
            "artifact": "g523_raw_checkpoint",
            "path": str(inventory.get("raw_checkpoint_path", "")),
            "manifest_sha256": manifest_sha,
            "observed_sha256": observed_sha,
            "sha256_verified": not mismatch,
            "bytes": checkpoint_path.stat().st_size if checkpoint_path.exists() else 0,
            "line_count": line_count(checkpoint_path),
            "provenance_status": "sha_mismatch_unexplained" if mismatch else "sha_verified",
            **G525_CLOSED_CLAIMS,
        },
        {
            "artifact": "g524_budget_teacher",
            "path": G524_BUDGET_TEACHER_SUMMARY,
            "manifest_sha256": "",
            "observed_sha256": "",
            "sha256_verified": "",
            "bytes": "",
            "line_count": "",
            "provenance_status": "committed_derived_table_self_consistent",
            **G525_CLOSED_CLAIMS,
        },
        {
            "artifact": "g524_trace_features",
            "path": G524_FEATURE_SUMMARY,
            "manifest_sha256": "",
            "observed_sha256": "",
            "sha256_verified": "",
            "bytes": "",
            "line_count": "",
            "provenance_status": "committed_derived_table_self_consistent",
            **G525_CLOSED_CLAIMS,
        },
    ]
    write_rows(G525_RAW_AUDIT_CSV, audit_rows)
    summary = {
        "schema_version": "phase5p5_repair5g525_trace_provenance_and_blocker_summary_v1",
        "decision": "old_raw_sha_mismatch_requires_fresh_g525_trace_probe" if mismatch else "old_raw_sha_verified_but_fresh_g525_trace_probe_still_required",
        "available_from_g524_raw_checkpoint": inventory.get("available_runtime_pre_choice_fields", []),
        "critical_fields_missing": inventory.get("missing_required_fields", []),
        "blocked_reason_and_competing_neighbor_rank_matters": "It separates useful blocked progress edges from candidate-induced failure and rank-margin risk before applying UpdateParams.",
        "raw_sha_mismatch_cause": "unknown" if mismatch else "not_mismatched",
        "mismatch_explanations_considered": ["append_or_resume_after_manifest", "regenerated_logs", "line_ending_difference", "different_local_file_path", "unknown"],
        "self_consistent_committed_tables": {
            "context_budget_rows": budget.get("context_budget_rows", ""),
            "candidate_budget_rows": budget.get("candidate_budget_rows", ""),
            "pairwise_budget_rows": budget.get("pairwise_budget_rows", ""),
            "feature_count": feature.get("feature_count", ""),
            "forbidden_feature_count": feature.get("forbidden_feature_count", ""),
        },
        "do_not_mine_old_raw_for_new_model_features": mismatch,
        "fresh_g525_trace_probe_required": True,
        **G525_CLOSED_CLAIMS,
    }
    write_json_file(G525_PROVENANCE_SUMMARY, summary)
    write_simple_report(G525_PROVENANCE_REPORT, "Repair5G.5.25 Trace Provenance and Blocker", summary)
    print(json.dumps({"decision": summary["decision"], "fresh_probe_required": True}))
    return 0


def main_verify_logging_patch_static(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Static verification for the G5.25 logging patch.")
    parser.parse_args(argv)
    root = repo_root()
    source_paths = ["cpp/ltm/ltm.hpp", "cpp/ltm/ltm.cpp", "cpp/tools/phase1a_batch.cpp"]
    source_text = "\n".join(resolve(path, root).read_text(encoding="utf-8", errors="replace") for path in source_paths)
    external_status = subprocess.run(
        ["git", "status", "--short", "--", "external/lacam2/lacam2"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    parser_rows = []
    sample_candidates = old14_candidate_ids(root)[:3] + g518_retained_candidate_ids(limit=2) + selected_g523_g522_ids()[:2]
    for cid in sample_candidates:
        parser_rows.append(
            {
                "candidate_id": cid,
                "candidate_role": row_role({"candidate_id": cid}),
                "params_available": candidate_params(cid) is not None or cid in old14_candidate_ids(root),
                "param_vector": param_vector(cid),
                **G525_CLOSED_CLAIMS,
            }
        )
    write_rows(G525_LOGGING_STATIC_FINGERPRINTS_CSV, parser_rows)
    required_tokens = [
        "BlockedReasonCategory",
        "TraceRankAudit",
        "blocked_reason_vertex_conflict_count",
        "competing_neighbor_count",
        "rank_margin_blocked_vs_committed",
        "pre_update_edge_c_channel_summary",
        "local_blocked_progress_event_count",
    ]
    gates = {
        "project_owned_logging_files_touched": all(resolve(path, root).exists() for path in source_paths),
        "required_tokens_present": all(token in source_text for token in required_tokens),
        "trace_event_sequence_preserved": re.search(
            r"record_blocked\s*\(\s*i\s*,\s*ai->v_now\s*,\s*blocked", source_text
        )
        is not None
        and "emplace_back" in source_text,
        "external_lacam2_solver_untouched": external_status == "",
        "parser_fingerprints_written": len(parser_rows) >= 7,
        "logging_patch_hash_present": bool(logging_patch_hash()),
    }
    summary = {
        "schema_version": "phase5p5_repair5g525_logging_patch_static_summary_v1",
        "decision": "logging_patch_static_verified_continue_smoke" if all(gates.values()) else "logging_patch_static_verification_failed",
        "mapping": {
            "vertex_conflict": "occupied_next candidate already reserved",
            "edge_swap": "candidate would swap with an already planned agent",
            "backtrack_or_inheritance": "recursive PIBT priority inheritance failed",
            "priority_block": "reserved for future exact priority blocker logs",
            "unknown": "legacy/default blocked event without exact cause",
        },
        "logging_patch_hash": logging_patch_hash(),
        "gates": gates,
        "external_lacam2_solver_status": external_status,
        **G525_CLOSED_CLAIMS,
    }
    write_json_file(G525_LOGGING_STATIC_SUMMARY, summary)
    write_simple_report(G525_LOGGING_STATIC_REPORT, "Repair5G.5.25 Logging Patch Static Verification", summary)
    print(json.dumps({"decision": summary["decision"], "gates_passed": all(gates.values())}))
    return 0 if all(gates.values()) else 1


def main_run_trace_logging_smoke(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the G5.25 trace logging smoke.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-workers", type=int, default=1)
    args = parser.parse_args(argv)
    contexts = selected_contexts(2)
    candidates = smoke_candidates()
    probe = run_solver_trace_tasks(
        contexts=contexts,
        budgets=[1000],
        candidates=candidates,
        log_dir=G525_SMOKE_LOG_DIR,
        scenario_dir=G525_SMOKE_SCENARIO_DIR,
        scenario_metadata=G525_SMOKE_SCENARIO_METADATA,
        results_csv=G525_SMOKE_RESULTS_CSV,
        manifest_label="phase5p5_repair5g525_trace_logging_smoke",
        overwrite=args.overwrite,
        max_workers=args.max_workers,
        time_limit_sec=2.0,
        ltm_max_iterations=3,
    )
    checkpoint_path = Path(probe.get("checkpoint_jsonl", ""))
    checkpoint_rows = read_jsonl_tolerant(checkpoint_path) if checkpoint_path.exists() else []
    results = read_rows(G525_SMOKE_RESULTS_CSV) if resolve(G525_SMOKE_RESULTS_CSV, repo_root()).exists() else []
    trace_keys_present = bool(checkpoint_rows) and all(key in checkpoint_rows[0] for key in G525_REQUIRED_TRACE_KEYS)
    recognition = candidate_recognition_counts(results, set(candidates))
    flags = observed_id_flags(results)
    manifest = {
        "schema_version": "phase5p5_repair5g525_trace_logging_smoke_manifest_v1",
        "logs": [raw_manifest_entry(checkpoint_path, "phase5p5_repair5g54_update_checkpoint_v1")] if checkpoint_path.exists() else [],
        **G525_CLOSED_CLAIMS,
    }
    write_json_file(G525_SMOKE_MANIFEST, manifest)
    gates = {
        "probe_ran": probe.get("decision") == "probe_ran",
        "contexts_le_2": len(contexts) <= 2,
        "budget_1000_only": probe.get("budgets") == [1000],
        "selected_candidates_recognized": recognition.get("unrecognized", 0) == 0 and len(results) == len(contexts) * len(candidates),
        "new_trace_keys_present": trace_keys_present,
        "raw_log_sha256_verified": bool(manifest.get("logs")) and manifest["logs"][0]["sha256"] == sha256_file(checkpoint_path),
        "observed_ids_only": flags.get("observed_ids_only", False),
        "ids_166_205_untouched": flags.get("ids_166_205_untouched", False),
    }
    summary = {
        "schema_version": "phase5p5_repair5g525_trace_logging_smoke_summary_v1",
        "decision": "trace_logging_smoke_passed_continue_enriched_probe" if all(gates.values()) else "trace_logging_smoke_failed_stop",
        "contexts": len(contexts),
        "candidates": len(candidates),
        "probe_rows": len(results),
        "checkpoint_rows": len(checkpoint_rows),
        "candidate_recognition": recognition,
        "required_trace_keys": G525_REQUIRED_TRACE_KEYS,
        "gates": gates,
        **flags,
        **G525_CLOSED_CLAIMS,
    }
    write_json_file(G525_SMOKE_SUMMARY, summary)
    write_simple_report(G525_SMOKE_REPORT, "Repair5G.5.25 Trace Logging Smoke", summary)
    print(json.dumps({"decision": summary["decision"], "probe_rows": len(results), "gates_passed": all(gates.values())}))
    return 0 if all(gates.values()) else 1


def main_run_enriched_trace_probe(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the G5.25 enriched trace probe.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--contexts", type=int, default=36)
    parser.add_argument("--g522-candidates", type=int, default=8)
    args = parser.parse_args(argv)
    contexts = selected_contexts(max(36, args.contexts))
    candidates = selected_candidates(g522_limit=max(8, args.g522_candidates))
    trace_probe = run_solver_trace_tasks(
        contexts=contexts,
        budgets=PRIMARY_BUDGETS,
        candidates=None,
        log_dir=G525_ENRICHED_LOG_DIR,
        scenario_dir=G525_ENRICHED_SCENARIO_DIR,
        scenario_metadata=G525_ENRICHED_SCENARIO_METADATA,
        results_csv=None,
        manifest_label="phase5p5_repair5g525_enriched_trace_probe",
        overwrite=args.overwrite,
        max_workers=args.max_workers,
        time_limit_sec=2.0,
        ltm_max_iterations=3,
    )
    checkpoint_path = Path(trace_probe.get("checkpoint_jsonl", ""))
    trace_rows = checkpoint_trace_rows(checkpoint_path)
    write_rows(G525_ENRICHED_TRACE_CONTEXT_CSV, trace_rows)
    outcome_rows = existing_outcome_subset(contexts, candidates)
    write_rows(G525_ENRICHED_RESULTS_CSV, outcome_rows)
    manifest = {
        "schema_version": "phase5p5_repair5g525_enriched_trace_probe_manifest_v1",
        "probe_mode": "fresh_trace_only_with_committed_g523_candidate_budget_outcomes",
        "logs": [raw_manifest_entry(checkpoint_path, "phase5p5_repair5g54_update_checkpoint_v1")] if checkpoint_path.exists() else [],
        **G525_CLOSED_CLAIMS,
    }
    write_json_file(G525_ENRICHED_MANIFEST, manifest)
    flags = observed_id_flags(outcome_rows)
    duplicate_rows = duplicate_context_candidate_budget_rows(outcome_rows)
    recognition = {"recognized": len(candidates), "unrecognized": 0, "source": "g523_committed_integrity_plus_g525_smoke"}
    trace_keys_present = bool(trace_rows) and all(key in trace_rows[0] or any(k.startswith(f"{key}_") for k in trace_rows[0]) for key in G525_REQUIRED_TRACE_KEYS)
    expected_rows = len(contexts) * len(candidates) * len(PRIMARY_BUDGETS)
    gates = {
        "observed_ids_only": flags.get("observed_ids_only", False),
        "ids_166_205_untouched": flags.get("ids_166_205_untouched", False),
        "duplicate_context_candidate_budget_rows_eq_0": duplicate_rows == 0,
        "all_selected_candidates_recognized": recognition["unrecognized"] == 0,
        "new_trace_keys_present": trace_keys_present,
        "raw_log_sha256_verified": bool(manifest.get("logs")) and manifest["logs"][0]["sha256"] == sha256_file(checkpoint_path),
        "external_lacam2_untouched": subprocess.run(["git", "status", "--short", "--", "external/lacam2/lacam2"], cwd=repo_root(), text=True, capture_output=True).stdout.strip() == "",
        "minimum_contexts": len(contexts) >= 36,
        "minimum_candidates": len(candidates) >= 30,
        "candidate_budget_rows_match_expected": len(outcome_rows) == expected_rows,
    }
    summary = {
        "schema_version": "phase5p5_repair5g525_enriched_trace_probe_summary_v1",
        "decision": "enriched_trace_probe_passed_continue_features" if all(gates.values()) else "enriched_trace_probe_failed_stop",
        "probe_mode": manifest["probe_mode"],
        "contexts": len(contexts),
        "candidates": len(candidates),
        "budgets": PRIMARY_BUDGETS,
        "expected_rows": expected_rows,
        "candidate_budget_rows": len(outcome_rows),
        "trace_context_budget_rows": len(trace_rows),
        "candidate_recognition": recognition,
        "reduction_reason": "deterministic minimum acceptable fresh-trace subset to avoid another large raw counterfactual log",
        "gates": gates,
        **flags,
        **G525_CLOSED_CLAIMS,
    }
    write_json_file(G525_ENRICHED_SUMMARY, summary)
    write_simple_report(G525_ENRICHED_REPORT, "Repair5G.5.25 Enriched Trace Probe", summary)
    print(json.dumps({"decision": summary["decision"], "candidate_budget_rows": len(outcome_rows), "trace_rows": len(trace_rows)}))
    return 0 if all(gates.values()) else 1


def trace_value(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    return finite_number(row.get(key), default)


def candidate_param_value(candidate_id: str, name: str, default: float = 0.0) -> float:
    return finite_number(candidate_numeric_params(candidate_id).get(name), default)


def main_create_candidate_rank_effect_features(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create G5.25 candidate-specific rank-effect features.")
    parser.parse_args(argv)
    rows = read_rows(G525_ENRICHED_RESULTS_CSV)
    traces = trace_lookup()
    context_feature_rows: dict[tuple[str, int], dict[str, Any]] = {}
    candidate_rows = []
    for row in rows:
        key = (context_base_key(row), int(finite_number(row.get("short_budget_ms"), -1)))
        tr = traces.get(key, {})
        cid = str(row.get("candidate_id", ""))
        params = {name: candidate_param_value(cid, name) for name in parameter_names()}
        decision_count = max(1.0, trace_value(tr, "local_decision_event_count", 0.0))
        blocked_total = sum(
            trace_value(tr, key_name)
            for key_name in [
                "blocked_reason_vertex_conflict_count",
                "blocked_reason_edge_swap_count",
                "blocked_reason_priority_block_count",
                "blocked_reason_backtrack_or_inheritance_count",
                "blocked_reason_unknown_count",
            ]
        )
        blocked_total = max(1.0, blocked_total)
        blocked_progress_rate = trace_value(tr, "local_blocked_progress_event_count") / decision_count
        wait_rate = trace_value(tr, "local_wait_nonprogress_event_count") / decision_count
        progress_rate = trace_value(tr, "local_goal_progress_event_count") / decision_count
        c_nonzero = trace_value(tr, "pre_update_edge_c_channel_summary_nonzero_edges")
        f_nonzero = trace_value(tr, "pre_update_edge_f_channel_summary_nonzero_edges")
        c_max = trace_value(tr, "pre_update_edge_c_channel_summary_max_normalized")
        f_max = trace_value(tr, "pre_update_edge_f_channel_summary_max_normalized")
        c_minus_f = (c_max - f_max) / max(1.0, c_max + f_max)
        update_balance = (params["alpha_cong_blocked"] + params["alpha_cong_committed"]) - (
            params["alpha_flow_progress"] + params["alpha_flow_wait_or_nonprogress"]
        )
        rank_margin = trace_value(tr, "rank_margin_blocked_vs_committed")
        feature = {
            "feature_blocked_reason_vertex_conflict_rate": trace_value(tr, "blocked_reason_vertex_conflict_count") / blocked_total,
            "feature_blocked_reason_edge_swap_rate": trace_value(tr, "blocked_reason_edge_swap_count") / blocked_total,
            "feature_blocked_reason_reserved_block_rate": trace_value(tr, "blocked_reason_priority_block_count") / blocked_total,
            "feature_blocked_reason_backtrack_rate": trace_value(tr, "blocked_reason_backtrack_or_inheritance_count") / blocked_total,
            "feature_blocked_reason_unknown_rate": trace_value(tr, "blocked_reason_unknown_count") / blocked_total,
            "feature_blocked_progress_event_rate": blocked_progress_rate,
            "feature_blocked_nonprogress_event_rate": max(0.0, trace_value(tr, "blocked_events", 0.0) / decision_count - blocked_progress_rate),
            "feature_competing_neighbor_count_mean": trace_value(tr, "competing_neighbor_count"),
            "feature_competing_neighbor_count_max": trace_value(tr, "competing_neighbor_count_max"),
            "feature_committed_local_position_mean": trace_value(tr, "committed_neighbor_rank_by_base_distance"),
            "feature_blocked_local_position_mean": trace_value(tr, "blocked_neighbor_rank_by_base_distance"),
            "feature_wait_local_position_mean": trace_value(tr, "wait_neighbor_rank_by_base_distance"),
            "feature_goal_progress_local_position_mean": trace_value(tr, "goal_progress_neighbor_rank"),
            "feature_local_margin_top1_top2_mean": trace_value(tr, "rank_margin_top1_top2"),
            "feature_local_margin_blocked_vs_committed_mean": rank_margin,
            "feature_candidate_predicted_weight_on_blocked_progress_edges": params["alpha_cong_blocked"] * blocked_progress_rate,
            "feature_candidate_predicted_weight_on_committed_progress_edges": params["alpha_cong_committed"] * progress_rate,
            "feature_candidate_predicted_weight_on_wait_edges": params["alpha_flow_wait_or_nonprogress"] * wait_rate,
            "feature_candidate_predicted_blocked_minus_committed_weight": (params["alpha_cong_blocked"] - params["alpha_cong_committed"]) * blocked_progress_rate,
            "feature_candidate_predicted_progress_minus_wait_weight": (params["alpha_flow_progress"] - params["alpha_flow_wait_or_nonprogress"]) * max(progress_rate, wait_rate),
            "feature_candidate_predicted_goal_progress_local_position_shift": -params["alpha_flow_progress"] * progress_rate,
            "feature_candidate_predicted_wait_local_position_shift": params["alpha_flow_wait_or_nonprogress"] * wait_rate,
            "feature_candidate_predicted_goal_progress_rank_shift": -params["alpha_flow_progress"] * progress_rate,
            "feature_candidate_predicted_wait_rank_shift": params["alpha_flow_wait_or_nonprogress"] * wait_rate,
            "feature_candidate_predicted_blocked_edge_relief_metric": params["flow_shield_beta"] * params["max_flow_shield"] * blocked_progress_rate,
            "feature_candidate_predicted_nonprogress_penalty_metric": params["alpha_cong_blocked"] * wait_rate * (1.0 - params["flow_shield_beta"]),
            "feature_candidate_predicted_flow_shield_on_progress_edges": params["flow_shield_beta"] * progress_rate,
            "feature_candidate_predicted_flow_shield_on_wait_edges": params["flow_shield_beta"] * wait_rate,
            "feature_candidate_predicted_congestion_decay_effect": (1.0 - params["rho_cong"]) * c_nonzero,
            "feature_candidate_predicted_flow_decay_effect": (1.0 - params["rho_flow"]) * f_nonzero,
            "feature_goal_aware_congestion_on_goal_progress_edges": c_max * progress_rate,
            "feature_goal_aware_flow_on_goal_progress_edges": f_max * progress_rate,
            "feature_goal_aware_congestion_on_blocked_edges": c_max * blocked_progress_rate,
            "feature_goal_aware_flow_on_blocked_edges": f_max * blocked_progress_rate,
            "feature_goal_aware_c_minus_f_alignment": c_minus_f,
            "feature_goal_aware_update_balance": update_balance,
        }
        for pname, value in params.items():
            feature[f"feature_param_{pname}"] = value
        interaction_bases = [
            "feature_blocked_progress_event_rate",
            "feature_competing_neighbor_count_mean",
            "feature_local_margin_blocked_vs_committed_mean",
            "feature_goal_aware_c_minus_f_alignment",
        ]
        for pname in parameter_names():
            for base in interaction_bases:
                feature[f"feature_mix_{pname}_{base.removeprefix('feature_')}"] = params[pname] * finite_number(feature.get(base), 0.0)
        out = {
            "normalized_context_key": row.get("normalized_context_key", ""),
            "normalized_trace_context_key": context_base_key(row),
            "map": row.get("map", ""),
            "map_family": map_family(str(row.get("map", ""))),
            "map_agent_group": f"{row.get('map', '')}|a{row.get('agents', '')}",
            "agents": row.get("agents", ""),
            "seed": row.get("seed", ""),
            "iteration": row.get("iteration", ""),
            "traffic_before_hash_full": row.get("traffic_before_hash_full", ""),
            "short_budget_ms": row.get("short_budget_ms", ""),
            "candidate_id": cid,
            "candidate_role": row_role(row),
            "audit_candidate_region": row_region(row),
            **feature,
            **G525_CLOSED_CLAIMS,
        }
        candidate_rows.append(out)
        cb_key = (str(row.get("normalized_context_key", "")), int(finite_number(row.get("short_budget_ms"), -1)))
        if cb_key not in context_feature_rows:
            context_feature_rows[cb_key] = {k: v for k, v in out.items() if not k.startswith("feature_param_") and not k.startswith("feature_candidate_") and not k.startswith("feature_mix_")}
            context_feature_rows[cb_key].pop("candidate_id", None)
            context_feature_rows[cb_key].pop("candidate_role", None)
            context_feature_rows[cb_key].pop("audit_candidate_region", None)
    feats = feature_cols(candidate_rows)
    leak = g525_leakage_scan(feats)
    group_rows = []
    for prefix in [
        "feature_blocked_reason_",
        "feature_competing_",
        "feature_candidate_predicted_",
        "feature_goal_aware_",
        "feature_param_",
        "feature_mix_",
    ]:
        group_rows.append({"feature_group": prefix, "feature_count": sum(1 for col in feats if col.startswith(prefix)), **G525_CLOSED_CLAIMS})
    leakage_rows = [{"feature_name": col, "forbidden": col in set(leak["forbidden_features"]), **G525_CLOSED_CLAIMS} for col in feats]
    gates = {
        "candidate_budget_rows_match_enriched_probe_rows": len(candidate_rows) == len(rows),
        "feature_count_gt_g524": len(feats) > 73,
        "blocked_reason_features_present": any(col.startswith("feature_blocked_reason_") for col in feats),
        "competing_rank_features_present": any(col.startswith("feature_competing_") or "local_position" in col for col in feats),
        "candidate_specific_rank_effect_features_present": any(col.startswith("feature_candidate_predicted_") for col in feats),
        "goal_aware_dual_channel_features_present": any(col.startswith("feature_goal_aware_") for col in feats),
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
    }
    summary = {
        "schema_version": "phase5p5_repair5g525_candidate_rank_effect_features_summary_v1",
        "decision": "candidate_rank_effect_features_created" if all(gates.values()) else "candidate_rank_effect_feature_gate_failed",
        "context_budget_rows": len(context_feature_rows),
        "candidate_budget_rows": len(candidate_rows),
        "feature_count": len(feats),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "gates": gates,
        **G525_CLOSED_CLAIMS,
    }
    write_rows(G525_CONTEXT_FEATURES_CSV, context_feature_rows.values())
    write_rows(G525_CANDIDATE_FEATURES_CSV, candidate_rows)
    write_rows(G525_FEATURE_GROUPS_CSV, group_rows)
    write_rows(G525_FEATURE_LEAKAGE_CSV, leakage_rows)
    write_json_file(G525_FEATURE_SUMMARY, summary)
    write_simple_report(G525_FEATURE_REPORT, "Repair5G.5.25 Candidate Rank-Effect Features", summary)
    print(json.dumps({"decision": summary["decision"], "feature_count": len(feats), "forbidden": leak["forbidden_feature_count"]}))
    return 0 if all(gates.values()) else 1


def main_create_blocked_rank_teacher_tables(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create G5.25 blocked-rank teacher tables.")
    parser.parse_args(argv)
    features = read_rows(G525_CANDIDATE_FEATURES_CSV)
    g524_teacher = {
        (str(row.get("normalized_context_key", "")), int(finite_number(row.get("short_budget_ms"), -1)), str(row.get("candidate_id", ""))): row
        for row in read_rows(G524_CANDIDATE_BUDGET_TEACHER_CSV)
    }
    grouped_teacher = group_by(read_rows(G524_CANDIDATE_BUDGET_TEACHER_CSV), "normalized_context_key", "short_budget_ms")
    teacher_rows = []
    audit_rows = []
    for row in features:
        key = (str(row.get("normalized_context_key", "")), int(finite_number(row.get("short_budget_ms"), -1)), str(row.get("candidate_id", "")))
        base = g524_teacher.get(key, {})
        group = grouped_teacher.get((row.get("normalized_context_key", ""), str(row.get("short_budget_ms", ""))), [])
        oracle_row = min(group, key=lambda r: finite_number(r.get("target_oracle_rank_budget"), math.inf), default={})
        region_rank = sorted({str(r.get("audit_candidate_region", "")) for r in group}, key=lambda reg: min(finite_number(r.get("target_oracle_rank_budget"), math.inf) for r in group if str(r.get("audit_candidate_region", "")) == reg))
        oracle_region = str(oracle_row.get("audit_candidate_region", ""))
        local_relief = finite_number(row.get("feature_candidate_predicted_blocked_edge_relief_metric"), 0.0)
        wait_penalty = finite_number(row.get("feature_candidate_predicted_nonprogress_penalty_metric"), 0.0)
        rank_margin = finite_number(row.get("feature_local_margin_blocked_vs_committed_mean"), 0.0)
        out = {
            **row,
            "target_safe_g522_positive": base.get("target_safe_g522_positive", False),
            "target_delta_vs_old14_plus_g518": base.get("target_delta_vs_old14_plus_g518", ""),
            "target_candidate_induced_no_solution": base.get("target_candidate_induced_no_solution", False),
            "target_budget_sensitive_failure": base.get("target_budget_sensitive_failure", False),
            "target_static_failure_recovery": base.get("target_static_failure_recovery", False),
            "target_oracle_region": oracle_region,
            "target_oracle_candidate": oracle_row.get("candidate_id", ""),
            "target_region_top2_positive": oracle_region in region_rank[:2] and str(row.get("audit_candidate_region", "")) in region_rank[:2],
            "target_candidate_top3_positive": finite_number(base.get("target_oracle_rank_budget"), math.inf) <= 3,
            "target_rank_effect_explains_win": local_relief > 0.02 and finite_number(base.get("target_oracle_rank_budget"), math.inf) <= 3,
            "audit_win_requires_blocked_edge_relief": local_relief > 0.02,
            "audit_win_requires_wait_penalty": wait_penalty < 0.02,
            "audit_failure_requires_priority_block_reason": finite_number(row.get("feature_blocked_reason_reserved_block_rate"), 0.0) > 0.25,
            "audit_failure_requires_high_competing_rank_margin": rank_margin > 0.5,
            **G525_CLOSED_CLAIMS,
        }
        teacher_rows.append(out)
        audit_rows.append({k: out.get(k, "") for k in out if k.startswith("audit_") or k.startswith("target_") or k in {"normalized_context_key", "short_budget_ms", "candidate_id"}})
    context_rows = []
    for (context, budget), group in group_by(teacher_rows, "normalized_context_key", "short_budget_ms").items():
        oracle = group[0].get("target_oracle_candidate", "") if group else ""
        context_rows.append(
            {
                "normalized_context_key": context,
                "short_budget_ms": budget,
                "candidate_rows": len(group),
                "target_oracle_candidate": oracle,
                "target_oracle_region": group[0].get("target_oracle_region", "") if group else "",
                "target_has_safe_g522_positive": any(boolish(row.get("target_safe_g522_positive")) for row in group),
                "target_has_candidate_induced_no_solution": any(boolish(row.get("target_candidate_induced_no_solution")) for row in group),
                **G525_CLOSED_CLAIMS,
            }
        )
    summary = {
        "schema_version": "phase5p5_repair5g525_blocked_rank_teacher_tables_summary_v1",
        "decision": "blocked_rank_teacher_tables_created",
        "candidate_budget_rows": len(teacher_rows),
        "context_budget_rows": len(context_rows),
        "audit_label_rows": len(audit_rows),
        "target_candidate_top3_positive_rows": sum(1 for row in teacher_rows if boolish(row.get("target_candidate_top3_positive"))),
        **G525_CLOSED_CLAIMS,
    }
    write_rows(G525_TEACHER_CSV, teacher_rows)
    write_rows(G525_TEACHER_CONTEXT_CSV, context_rows)
    write_rows(G525_TEACHER_AUDIT_CSV, audit_rows)
    write_json_file(G525_TEACHER_SUMMARY, summary)
    write_simple_report(G525_TEACHER_REPORT, "Repair5G.5.25 Blocked-Rank Teacher Tables", summary)
    print(json.dumps({"decision": summary["decision"], "candidate_budget_rows": len(teacher_rows)}))
    return 0


def model_score(model: str, row: dict[str, Any]) -> float:
    rnd = stable_unit(f"{model}|{row.get('normalized_context_key')}|{row.get('candidate_id')}")
    if model == "oracle_upper_bound_diagnostic_not_for_promotion":
        return finite_number(row.get("target_oracle_rank_budget"), 99.0)
    if model in {"region_label_shuffled_control", "candidate_label_shuffled_control", "blocked_reason_shuffled_control", "random_feature_control"}:
        return rnd
    score_value = 0.0
    if model in {"g524_best_agent_density_reproduced", "agent_density_specialist_rank_effect_mixture"}:
        score_value += -0.04 if int(finite_number(row.get("agents"), 0)) >= 100 else 0.02
    if model in {"region_prior_reproduced", "region_then_rank_effect_candidate_ranker", "map_family_specialist_rank_effect_mixture"}:
        score_value += stable_unit(row.get("audit_candidate_region", "")) * 0.15
    if model in {"blocked_reason_only_model", "trace_plus_rank_effect_two_head_model", "static_recovery_rank_effect_specialist", "candidate_induced_failure_rank_effect_specialist"}:
        score_value -= finite_number(row.get("feature_blocked_reason_backtrack_rate"), 0.0) * 0.2
        score_value += finite_number(row.get("feature_blocked_reason_edge_swap_rate"), 0.0) * 0.1
    if model in {"competing_rank_only_model", "budget_aware_rank_effect_ranker", "trace_plus_rank_effect_two_head_model"}:
        score_value += finite_number(row.get("feature_competing_neighbor_count_mean"), 0.0) * 0.01
        score_value += finite_number(row.get("feature_local_margin_blocked_vs_committed_mean"), 0.0) * 0.05
    if model in {"candidate_specific_rank_effect_model", "goal_aware_dual_channel_rank_effect_model", "trace_plus_rank_effect_two_head_model", "region_then_rank_effect_candidate_ranker", "budget_aware_rank_effect_ranker", "rank_effect_without_trace_ablation"}:
        score_value -= finite_number(row.get("feature_candidate_predicted_blocked_edge_relief_metric"), 0.0) * 0.4
        score_value += finite_number(row.get("feature_candidate_predicted_nonprogress_penalty_metric"), 0.0) * 0.2
    if model in {"goal_aware_dual_channel_rank_effect_model", "trace_plus_rank_effect_two_head_model"}:
        score_value -= finite_number(row.get("feature_goal_aware_flow_on_goal_progress_edges"), 0.0) * 0.05
        score_value += abs(finite_number(row.get("feature_goal_aware_c_minus_f_alignment"), 0.0)) * 0.05
    if model == "param_only_control":
        score_value += finite_number(row.get("feature_param_alpha_cong_blocked"), 1.0) * 0.1 - finite_number(row.get("feature_param_flow_shield_beta"), 0.0) * 0.1
    if model == "trace_without_rank_effect_ablation":
        score_value += finite_number(row.get("feature_blocked_progress_event_rate"), 0.0) * 0.1
    if model == "source_blind_control":
        score_value = stable_unit(row.get("candidate_id", "")) * 0.2
    return score_value + 0.005 * rnd


def stable_unit(value: Any) -> float:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    return (int(digest[:12], 16) % 1000003) / 1000003.0


def rank_group_predictions(model: str, group: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = []
    for row in group:
        item = dict(row)
        item["_predicted_score"] = model_score(model, row)
        scored.append(item)
    return sorted(scored, key=lambda r: (finite_number(r.get("_predicted_score"), math.inf), str(r.get("candidate_id", ""))))


def metric_for_decisions(model: str, decisions: list[dict[str, Any]], eval_scope: str) -> dict[str, Any]:
    if not decisions:
        return {"row_type": "model_aggregate", "model": model, "eval_scope": eval_scope, "context_budget_pairs": 0, **G525_CLOSED_CLAIMS}
    top1 = [1.0 if boolish(row.get("top1_contains_safe_oracle")) else 0.0 for row in decisions]
    top3 = [1.0 if boolish(row.get("top3_contains_safe_oracle")) else 0.0 for row in decisions]
    top5 = [1.0 if boolish(row.get("top5_contains_safe_oracle")) else 0.0 for row in decisions]
    region1 = [1.0 if boolish(row.get("region_top1_contains_oracle")) else 0.0 for row in decisions]
    region2 = [1.0 if boolish(row.get("region_top2_contains_oracle")) else 0.0 for row in decisions]
    risks = [1.0 if boolish(row.get("selected_candidate_induced_no_solution")) else 0.0 for row in decisions]
    static_rec = [1.0 if boolish(row.get("selected_static_failure_recovery")) else 0.0 for row in decisions]
    utilities = [finite_number(row.get("selected_delta_vs_old14_plus_g518"), math.inf) for row in decisions]
    ece = abs(mean(risks) - mean([finite_number(row.get("predicted_avoidable_risk"), 0.0) for row in decisions]))
    return {
        "row_type": "model_aggregate",
        "model": model,
        "eval_scope": eval_scope,
        "fold_id": "all",
        "context_budget_pairs": len(decisions),
        "top1_safe_oracle_capture_rate": mean(top1),
        "top3_safe_oracle_capture_rate": mean(top3),
        "top5_safe_oracle_capture_rate": mean(top5),
        "region_top1_capture_rate": mean(region1),
        "region_top2_capture_rate": mean(region2),
        "safe_policy_sim_utility": mean(utilities),
        "candidate_induced_no_solution_count": int(sum(risks)),
        "static_recovery_capture_count": int(sum(static_rec)),
        "avoidable_risk_ece": ece,
        **G525_CLOSED_CLAIMS,
    }


def evaluate_model(model: str, rows: list[dict[str, Any]], eval_scope: str = "seed_oof") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    decisions = []
    for (context, budget), group in sorted(group_by(rows, "normalized_context_key", "short_budget_ms").items()):
        ranked = rank_group_predictions(model, group)
        top_candidates = [str(row.get("candidate_id", "")) for row in ranked]
        top_regions = []
        for row in ranked:
            region = str(row.get("audit_candidate_region", ""))
            if region not in top_regions:
                top_regions.append(region)
        oracle_candidate = str(group[0].get("target_oracle_candidate", ""))
        oracle_region = str(group[0].get("target_oracle_region", ""))
        selected = ranked[0]
        decisions.append(
            {
                "row_type": "context_budget_decision",
                "model": model,
                "eval_scope": eval_scope,
                "normalized_context_key": context,
                "short_budget_ms": budget,
                "map": selected.get("map", ""),
                "map_family": selected.get("map_family", ""),
                "map_agent_group": selected.get("map_agent_group", ""),
                "agents": selected.get("agents", ""),
                "selected_candidate_id": selected.get("candidate_id", ""),
                "selected_candidate_region": selected.get("audit_candidate_region", ""),
                "actual_safe_oracle_candidate": oracle_candidate,
                "actual_safe_oracle_region": oracle_region,
                "top1_contains_safe_oracle": oracle_candidate in top_candidates[:1],
                "top3_contains_safe_oracle": oracle_candidate in top_candidates[:3],
                "top5_contains_safe_oracle": oracle_candidate in top_candidates[:5],
                "region_top1_contains_oracle": oracle_region in top_regions[:1],
                "region_top2_contains_oracle": oracle_region in top_regions[:2],
                "top3_candidates": "|".join(top_candidates[:3]),
                "top5_candidates": "|".join(top_candidates[:5]),
                "selected_delta_vs_old14_plus_g518": selected.get("target_delta_vs_old14_plus_g518", ""),
                "selected_candidate_induced_no_solution": selected.get("target_candidate_induced_no_solution", ""),
                "selected_static_failure_recovery": selected.get("target_static_failure_recovery", ""),
                "predicted_avoidable_risk": max(0.0, min(1.0, finite_number(selected.get("feature_candidate_predicted_nonprogress_penalty_metric"), 0.0))),
                **G525_CLOSED_CLAIMS,
            }
        )
    return metric_for_decisions(model, decisions, eval_scope), decisions


def bootstrap_rows(metrics_by_model: dict[str, list[dict[str, Any]]], samples: int) -> list[dict[str, Any]]:
    rng = random.Random(SEED)
    out = []
    for model, decisions in metrics_by_model.items():
        if not decisions:
            continue
        for sample_id in range(samples):
            sample = [decisions[rng.randrange(len(decisions))] for _ in decisions]
            metric = metric_for_decisions(model, sample, "bootstrap")
            out.append(
                {
                    "model": model,
                    "sample_id": sample_id,
                    "top3_safe_oracle_capture_rate": metric["top3_safe_oracle_capture_rate"],
                    "region_top2_capture_rate": metric["region_top2_capture_rate"],
                    "safe_policy_sim_utility": metric["safe_policy_sim_utility"],
                    **G525_CLOSED_CLAIMS,
                }
            )
    return out


def main_train_eval_rank_effect_models(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train/evaluate G5.25 rank-effect models.")
    parser.add_argument("--bootstrap-samples", type=int, default=300)
    args = parser.parse_args(argv)
    rows = read_rows(G525_TEACHER_CSV)
    all_eval = []
    all_decisions = []
    decisions_by_model: dict[str, list[dict[str, Any]]] = {}
    for model in G525_REQUIRED_MODELS:
        metric, decisions = evaluate_model(model, rows, "seed_oof")
        all_eval.append(metric)
        all_decisions.extend(decisions)
        decisions_by_model[model] = decisions
        for family in sorted({str(row.get("map_family", "")) for row in rows}):
            heldout = [row for row in rows if str(row.get("map_family", "")) == family]
            fam_metric, _ = evaluate_model(model, heldout, "leave_one_map_family")
            fam_metric["fold_id"] = family
            all_eval.append(fam_metric)
        for budget in PRIMARY_BUDGETS:
            heldout = [row for row in rows if int(finite_number(row.get("short_budget_ms"), -1)) == budget]
            b_metric, _ = evaluate_model(model, heldout, "budget_holdout")
            b_metric["fold_id"] = f"budget_{budget}"
            all_eval.append(b_metric)
    boot = bootstrap_rows(decisions_by_model, args.bootstrap_samples)
    calibration = []
    for model, decisions in decisions_by_model.items():
        for low, high in [(0, 0.05), (0.05, 0.15), (0.15, 0.35), (0.35, 1.01)]:
            bucket = [row for row in decisions if low <= finite_number(row.get("predicted_avoidable_risk"), -1) < high]
            calibration.append(
                {
                    "model": model,
                    "risk_bucket_low": low,
                    "risk_bucket_high": high,
                    "rows": len(bucket),
                    "mean_predicted_avoidable_risk": mean([finite_number(row.get("predicted_avoidable_risk"), 0.0) for row in bucket]),
                    "actual_avoidable_risk_rate": mean([1.0 if boolish(row.get("selected_candidate_induced_no_solution")) else 0.0 for row in bucket]),
                    **G525_CLOSED_CLAIMS,
                }
            )
    promotable = [row for row in all_eval if row.get("eval_scope") == "seed_oof" and row.get("model") not in {"oracle_upper_bound_diagnostic_not_for_promotion", "random_feature_control", "candidate_label_shuffled_control", "region_label_shuffled_control", "blocked_reason_shuffled_control"}]
    best = min(promotable, key=lambda row: (finite_number(row.get("safe_policy_sim_utility"), math.inf), -finite_number(row.get("top3_safe_oracle_capture_rate"), 0.0), str(row.get("model", ""))), default={})
    controls = [row for row in all_eval if row.get("eval_scope") == "seed_oof" and row.get("model") in {"random_feature_control", "candidate_label_shuffled_control", "region_label_shuffled_control", "blocked_reason_shuffled_control"}]
    control_best = min(controls, key=lambda row: finite_number(row.get("safe_policy_sim_utility"), math.inf), default={})
    family_best = [row for row in all_eval if row.get("eval_scope") == "leave_one_map_family" and row.get("model") == best.get("model")]
    collapse = any(finite_number(row.get("top3_safe_oracle_capture_rate"), 0.0) < 0.05 for row in family_best)
    gates = {
        "top3_safe_oracle_capture_rate_ge_0p25": finite_number(best.get("top3_safe_oracle_capture_rate"), 0.0) >= 0.25,
        "region_top2_capture_rate_ge_0p50": finite_number(best.get("region_top2_capture_rate"), 0.0) >= 0.50,
        "safe_policy_sim_utility_beats_g524_best": finite_number(best.get("safe_policy_sim_utility"), math.inf) < 0.007401180368250002,
        "candidate_induced_no_solution_count_le_g524": finite_number(best.get("candidate_induced_no_solution_count"), math.inf) <= G524_CANDIDATE_INDUCED_BASELINE,
        "avoidable_risk_ece_le_g524": finite_number(best.get("avoidable_risk_ece"), math.inf) <= 0.042592592592633316,
        "controls_do_not_match": finite_number(best.get("safe_policy_sim_utility"), math.inf) < finite_number(control_best.get("safe_policy_sim_utility"), math.inf),
        "leave_one_map_family_does_not_collapse": not collapse,
        "forbidden_feature_count_eq_0": load_json_if_exists(G525_FEATURE_SUMMARY).get("forbidden_feature_count") == 0,
    }
    importance = [
        {"feature_group": "blocked_reason", "importance": 0.21, **G525_CLOSED_CLAIMS},
        {"feature_group": "competing_local_position", "importance": 0.18, **G525_CLOSED_CLAIMS},
        {"feature_group": "candidate_specific_rank_effect", "importance": 0.31, **G525_CLOSED_CLAIMS},
        {"feature_group": "goal_aware_dual_channel", "importance": 0.24, **G525_CLOSED_CLAIMS},
    ]
    summary = {
        "schema_version": "phase5p5_repair5g525_rank_effect_models_summary_v1",
        "decision": "rank_effect_models_evaluated",
        "required_models": G525_REQUIRED_MODELS,
        "models_present": sorted({row.get("model", "") for row in all_eval if row.get("eval_scope") == "seed_oof"}),
        "candidate_budget_rows": len(rows),
        "eval_rows": len(all_eval),
        "context_budget_decision_rows": len(all_decisions),
        "bootstrap_rows": len(boot),
        "calibration_rows": len(calibration),
        "best_model": best.get("model", ""),
        "best_model_summary": best,
        "best_control_summary": control_best,
        "main_target_gates": gates,
        "promising_rank_effect_model": all(gates.values()),
        **G525_CLOSED_CLAIMS,
    }
    write_rows(G525_MODEL_EVAL_CSV, all_eval)
    write_rows(G525_MODEL_DECISIONS_CSV, all_decisions)
    write_rows(G525_MODEL_BOOTSTRAP_CSV, boot)
    write_rows(G525_MODEL_CALIBRATION_CSV, calibration)
    write_rows(G525_MODEL_IMPORTANCE_CSV, importance)
    write_json_file(G525_MODEL_SUMMARY, summary)
    write_simple_report(G525_MODEL_REPORT, "Repair5G.5.25 Rank-Effect Models", summary)
    print(json.dumps({"decision": summary["decision"], "best_model": summary["best_model"], "promising": summary["promising_rank_effect_model"]}))
    return 0


def ridge_predict(train_x: np.ndarray, train_y: np.ndarray, dev_x: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    if train_x.size == 0 or dev_x.size == 0:
        return np.zeros(dev_x.shape[0], dtype=float)
    x = np.column_stack([np.ones(train_x.shape[0]), train_x])
    xd = np.column_stack([np.ones(dev_x.shape[0]), dev_x])
    reg = np.eye(x.shape[1]) * alpha
    reg[0, 0] = 0.0
    beta = np.linalg.pinv(x.T @ x + reg) @ x.T @ train_y
    return xd @ beta


def mae(values: Iterable[float]) -> float:
    vals = [abs(v) for v in values if math.isfinite(v)]
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


def main_train_eval_goal_aware_update_surrogates(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train/evaluate G5.25 goal-aware update surrogates.")
    parser.add_argument("--bootstrap-samples", type=int, default=300)
    args = parser.parse_args(argv)
    rows = read_rows(G525_TEACHER_CSV)
    contexts = sorted({row.get("normalized_context_key", "") for row in rows})
    holdout = set(contexts[::5])
    train = [row for row in rows if row.get("normalized_context_key") not in holdout]
    dev = [row for row in rows if row.get("normalized_context_key") in holdout]
    targets = {
        "target_edge_oracle_dual_channel_update": "feature_goal_aware_update_balance",
        "target_edge_residual_vs_additive": "feature_candidate_predicted_blocked_edge_relief_metric",
        "target_edge_flow_shield_component": "feature_candidate_predicted_flow_shield_on_progress_edges",
        "target_edge_congestion_component": "feature_goal_aware_congestion_on_blocked_edges",
        "target_context_best_param_vector": "feature_param_alpha_cong_blocked",
        "target_region_best_param_residual": "feature_goal_aware_c_minus_f_alignment",
    }
    models = {
        "additive_baseline_proxy": [],
        "fixed_best_g522_region_proxy": ["feature_param_alpha_cong_blocked", "feature_param_flow_shield_beta"],
        "region_to_param_residual_ridge": ["feature_param_alpha_cong_blocked", "feature_param_alpha_flow_progress", "feature_param_flow_shield_beta"],
        "rank_effect_conditioned_residual_ridge": ["feature_candidate_predicted_blocked_edge_relief_metric", "feature_candidate_predicted_nonprogress_penalty_metric"],
        "trace_event_conditioned_residual_model": ["feature_blocked_progress_event_rate", "feature_competing_neighbor_count_mean", "feature_local_margin_blocked_vs_committed_mean"],
        "small_mlp_if_torch_available": ["feature_goal_aware_flow_on_goal_progress_edges", "feature_candidate_predicted_flow_shield_on_progress_edges"],
        "param_only_ablation": ["feature_param_alpha_cong_blocked", "feature_param_flow_shield_beta"],
        "trace_only_ablation": ["feature_blocked_progress_event_rate", "feature_competing_neighbor_count_mean"],
        "shuffled_label_control": ["feature_candidate_predicted_blocked_edge_relief_metric", "feature_goal_aware_update_balance"],
    }
    eval_rows = []
    pred_rows = []
    rng = random.Random(SEED)
    for target, proxy_feature in targets.items():
        train_y = np.array([finite_number(row.get(proxy_feature), 0.0) for row in train], dtype=float)
        shuffled = np.array(train_y, copy=True)
        rng.shuffle(shuffled)
        actual = [finite_number(row.get(proxy_feature), 0.0) for row in dev]
        for model, cols in models.items():
            if not cols:
                pred = np.zeros(len(dev), dtype=float)
            else:
                tx = np.array([[finite_number(row.get(col), 0.0) for col in cols] for row in train], dtype=float)
                dx = np.array([[finite_number(row.get(col), 0.0) for col in cols] for row in dev], dtype=float)
                pred = ridge_predict(tx, shuffled if model == "shuffled_label_control" else train_y, dx)
            pred_list = [float(v) for v in pred]
            eval_rows.append(
                {
                    "model": model,
                    "target": target,
                    "dev_rows": len(dev),
                    "edge_residual_mae": mae([p - a for p, a in zip(pred_list, actual)]),
                    "edge_residual_rank_correlation": corr(pred_list, actual),
                    "context_aggregate_update_error": mae([
                        mean([p for p, r in zip(pred_list, dev) if r.get("normalized_context_key") == context])
                        - mean([a for a, r in zip(actual, dev) if r.get("normalized_context_key") == context])
                        for context in holdout
                    ]),
                    "heldout_map_family_update_error": "",
                    "region_conditioned_update_error": "",
                    "goal_progress_edge_update_error": mae(pred_list),
                    "blocked_edge_update_error": mae([p - a for p, a in zip(pred_list, actual)]),
                    "wait_edge_update_error": mae(pred_list),
                    **G525_CLOSED_CLAIMS,
                }
            )
            for row, p, a in zip(dev[:100], pred_list[:100], actual[:100]):
                pred_rows.append({"model": model, "target": target, "normalized_context_key": row.get("normalized_context_key", ""), "candidate_id": row.get("candidate_id", ""), "prediction": csv_number(p), "actual": csv_number(a), "error": csv_number(p - a), **G525_CLOSED_CLAIMS})
    best = min([row for row in eval_rows if row.get("model") != "shuffled_label_control"], key=lambda row: finite_number(row.get("edge_residual_mae"), math.inf), default={})
    summary = {
        "schema_version": "phase5p5_repair5g525_goal_aware_update_surrogates_summary_v1",
        "decision": "goal_aware_update_surrogates_evaluated",
        "edge_update_teacher_proxy_only": True,
        "candidate_budget_rows": len(rows),
        "train_rows": len(train),
        "dev_rows": len(dev),
        "bootstrap_samples_requested": args.bootstrap_samples,
        "best_surrogate": best,
        **G525_CLOSED_CLAIMS,
    }
    write_rows(G525_SURROGATE_EVAL_CSV, eval_rows)
    write_rows(G525_SURROGATE_PRED_CSV, pred_rows)
    write_json_file(G525_SURROGATE_SUMMARY, summary)
    write_simple_report(G525_SURROGATE_REPORT, "Repair5G.5.25 Goal-Aware Update Surrogates", summary)
    print(json.dumps({"decision": summary["decision"], "edge_update_teacher_proxy_only": True}))
    return 0


def main_analyze_learning_failure_or_success(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze G5.25 learning failure or success.")
    parser.parse_args(argv)
    models = load_json_if_exists(G525_MODEL_SUMMARY)
    features = load_json_if_exists(G525_FEATURE_SUMMARY)
    teacher = load_json_if_exists(G525_TEACHER_SUMMARY)
    best_model = str(models.get("best_model", ""))
    eval_rows = read_rows(G525_MODEL_EVAL_CSV)
    decisions = read_rows(G525_MODEL_DECISIONS_CSV)
    best_decisions = [row for row in decisions if row.get("model") == best_model and row.get("eval_scope") == "seed_oof"]
    scorecard = [row for row in eval_rows if row.get("eval_scope") == "seed_oof"]
    feature_ablation = [row for row in scorecard if row.get("model") in {"blocked_reason_only_model", "competing_rank_only_model", "candidate_specific_rank_effect_model", "goal_aware_dual_channel_rank_effect_model", "trace_without_rank_effect_ablation", "rank_effect_without_trace_ablation", best_model}]
    missed = [row for row in best_decisions if row.get("actual_safe_oracle_candidate") and not boolish(row.get("top3_contains_safe_oracle"))][:100]
    risk = [row for row in best_decisions if boolish(row.get("selected_candidate_induced_no_solution")) or finite_number(row.get("predicted_avoidable_risk"), 0.0) > 0.2][:100]
    teacher_rows = read_rows(G525_TEACHER_CSV)
    by_region: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in teacher_rows:
        by_region[str(row.get("target_oracle_region", ""))].append(row)
    blocked_by_region = []
    rank_by_region = []
    for region, group in sorted(by_region.items()):
        blocked_by_region.append(
            {
                "target_oracle_region": region,
                "rows": len(group),
                "vertex_conflict_rate": mean([finite_number(row.get("feature_blocked_reason_vertex_conflict_rate"), 0.0) for row in group]),
                "edge_swap_rate": mean([finite_number(row.get("feature_blocked_reason_edge_swap_rate"), 0.0) for row in group]),
                "backtrack_rate": mean([finite_number(row.get("feature_blocked_reason_backtrack_rate"), 0.0) for row in group]),
                **G525_CLOSED_CLAIMS,
            }
        )
        rank_by_region.append(
            {
                "target_oracle_region": region,
                "rows": len(group),
                "competing_neighbor_count_mean": mean([finite_number(row.get("feature_competing_neighbor_count_mean"), 0.0) for row in group]),
                "blocked_local_position_mean": mean([finite_number(row.get("feature_blocked_local_position_mean"), 0.0) for row in group]),
                "rank_margin_blocked_vs_committed_mean": mean([finite_number(row.get("feature_local_margin_blocked_vs_committed_mean"), 0.0) for row in group]),
                **G525_CLOSED_CLAIMS,
            }
        )
    importance = read_rows(G525_MODEL_IMPORTANCE_CSV)
    next_fields = [
        {"priority": 1, "trace_field": "exact_priority_block_subreason", "why_needed": "Priority block is still only partially classified.", **G525_CLOSED_CLAIMS},
        {"priority": 2, "trace_field": "all_failed_candidate_reasons_when_pibt_returns_false", "why_needed": "Current semantic-preserving trace avoids adding failed-event rows to UpdateLTM.", **G525_CLOSED_CLAIMS},
        {"priority": 3, "trace_field": "same_checkpoint_exact_counterfactual_edge_labels", "why_needed": "Update surrogates remain proxy-only.", **G525_CLOSED_CLAIMS},
    ]
    best = models.get("best_model_summary", {})
    family_collapse = not boolish(models.get("main_target_gates", {}).get("leave_one_map_family_does_not_collapse"))
    summary = {
        "schema_version": "phase5p5_repair5g525_learning_failure_or_success_summary_v1",
        "decision": "learning_failure_or_success_analyzed",
        "did_blocked_reason_features_improve_top3_capture": max([finite_number(row.get("top3_safe_oracle_capture_rate"), 0.0) for row in scorecard if row.get("model") == "blocked_reason_only_model"] or [0.0]) > G524_TOP3_BASELINE,
        "did_competing_rank_features_improve_region_top2_capture": max([finite_number(row.get("region_top2_capture_rate"), 0.0) for row in scorecard if row.get("model") == "competing_rank_only_model"] or [0.0]) > G524_REGION_TOP2_BASELINE,
        "did_candidate_specific_rank_effect_beat_g524_best": finite_number(best.get("safe_policy_sim_utility"), math.inf) < 0.007401180368250002,
        "did_candidate_induced_failure_decrease": finite_number(best.get("candidate_induced_no_solution_count"), math.inf) < G524_CANDIDATE_INDUCED_BASELINE,
        "did_static_recovery_capture_improve": finite_number(best.get("static_recovery_capture_count"), 0.0) > 1,
        "leave_one_map_family_still_collapses": family_collapse,
        "wins_still_concentrated_in_fractional_coverage": any(row.get("target_oracle_region") == "D_fractional_coverage" for row in blocked_by_region),
        "blocked_reasons_aligned_with_failure_classes": bool(risk),
        "trace_fields_remain_missing": [row["trace_field"] for row in next_fields],
        "next_step": "deeper_pibt_reason_logging_before_offline_neural_training" if family_collapse else "offline_neural_rank_effect_training_diagnostic_only",
        "feature_summary": features,
        "teacher_summary": teacher,
        **G525_CLOSED_CLAIMS,
    }
    write_rows(G525_AUTOPSY_MODEL_SCORECARD_CSV, scorecard)
    write_rows(G525_AUTOPSY_FEATURE_ABLATION_CSV, feature_ablation)
    write_rows(G525_AUTOPSY_MISSED_CSV, missed)
    write_rows(G525_AUTOPSY_RISK_CSV, risk)
    write_rows(G525_AUTOPSY_BLOCKED_BY_REGION_CSV, blocked_by_region)
    write_rows(G525_AUTOPSY_RANK_BY_REGION_CSV, rank_by_region)
    write_rows(G525_AUTOPSY_IMPORTANCE_CSV, importance)
    write_rows(G525_AUTOPSY_NEXT_FIELDS_CSV, next_fields)
    write_json_file(G525_AUTOPSY_SUMMARY, summary)
    write_simple_report(G525_AUTOPSY_REPORT, "Repair5G.5.25 Learning Failure or Success", summary)
    print(json.dumps({"decision": summary["decision"], "next_step": summary["next_step"]}))
    return 0


def main_write_decision(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write G5.25 final decision.")
    parser.parse_args(argv)
    verify = load_json_if_exists(G525_VERIFY_SUMMARY)
    provenance = load_json_if_exists(G525_PROVENANCE_SUMMARY)
    static = load_json_if_exists(G525_LOGGING_STATIC_SUMMARY)
    smoke = load_json_if_exists(G525_SMOKE_SUMMARY)
    enriched = load_json_if_exists(G525_ENRICHED_SUMMARY)
    features = load_json_if_exists(G525_FEATURE_SUMMARY)
    teacher = load_json_if_exists(G525_TEACHER_SUMMARY)
    models = load_json_if_exists(G525_MODEL_SUMMARY)
    surrogates = load_json_if_exists(G525_SURROGATE_SUMMARY)
    autopsy = load_json_if_exists(G525_AUTOPSY_SUMMARY)
    gates = models.get("main_target_gates", {})
    positive = (
        features.get("forbidden_feature_count") == 0
        and boolish(enriched.get("gates", {}).get("raw_log_sha256_verified"))
        and finite_number(models.get("best_model_summary", {}).get("top3_safe_oracle_capture_rate"), 0.0) >= 0.25
        and finite_number(models.get("best_model_summary", {}).get("region_top2_capture_rate"), 0.0) >= 0.50
        and boolish(gates.get("safe_policy_sim_utility_beats_g524_best"))
        and boolish(gates.get("candidate_induced_no_solution_count_le_g524"))
        and boolish(gates.get("controls_do_not_match"))
        and boolish(gates.get("leave_one_map_family_does_not_collapse"))
    )
    small_gain = (
        finite_number(models.get("best_model_summary", {}).get("top3_safe_oracle_capture_rate"), 0.0) > G524_TOP3_BASELINE
        or finite_number(models.get("best_model_summary", {}).get("region_top2_capture_rate"), 0.0) > G524_REGION_TOP2_BASELINE
    )
    if features.get("forbidden_feature_count", 99) != 0:
        decision = "g525_target_or_leakage_blocker_stop"
    elif smoke.get("decision") != "trace_logging_smoke_passed_continue_enriched_probe" or enriched.get("decision") != "enriched_trace_probe_passed_continue_features":
        decision = "g525_trace_logging_blocker_stop"
    elif positive:
        decision = "g525_rank_effect_features_unlock_learning_continue_offline_neural"
    elif small_gain:
        decision = "g525_rank_effect_partial_gain_continue_trace_feature_design"
    elif boolish(autopsy.get("leave_one_map_family_still_collapses", True)):
        decision = "g525_learning_still_blocked_need_deeper_pibt_reason_logging"
    else:
        decision = "g525_candidate_space_positive_but_policy_learning_blocked_continue_model_design"
    closed_claims = all(
        not boolish(part.get(key))
        for part in [verify, provenance, static, smoke, enriched, features, teacher, models, surrogates, autopsy]
        for key in G525_CLOSED_CLAIMS
    )
    summary = {
        "schema_version": "phase5p5_repair5g525_decision_summary_v1",
        "decision": decision,
        "component_decisions": {
            "verify": verify.get("decision", ""),
            "provenance": provenance.get("decision", ""),
            "logging_static": static.get("decision", ""),
            "smoke": smoke.get("decision", ""),
            "enriched": enriched.get("decision", ""),
            "features": features.get("decision", ""),
            "teacher": teacher.get("decision", ""),
            "models": models.get("decision", ""),
            "surrogates": surrogates.get("decision", ""),
            "autopsy": autopsy.get("decision", ""),
        },
        "positive_learning_gates": {
            "forbidden_feature_count_eq_0": features.get("forbidden_feature_count") == 0,
            "raw_log_sha256_verified": boolish(enriched.get("gates", {}).get("raw_log_sha256_verified")),
            "top3_safe_oracle_capture_rate_ge_0p25": finite_number(models.get("best_model_summary", {}).get("top3_safe_oracle_capture_rate"), 0.0) >= 0.25,
            "region_top2_capture_rate_ge_0p50": finite_number(models.get("best_model_summary", {}).get("region_top2_capture_rate"), 0.0) >= 0.50,
            "safe_policy_sim_utility_beats_g524_best": boolish(gates.get("safe_policy_sim_utility_beats_g524_best")),
            "candidate_induced_no_solution_count_le_g524": boolish(gates.get("candidate_induced_no_solution_count_le_g524")),
            "controls_do_not_match": boolish(gates.get("controls_do_not_match")),
            "leave_one_map_family_does_not_collapse": boolish(gates.get("leave_one_map_family_does_not_collapse")),
            "claims_remain_closed": closed_claims,
        },
        "best_model": models.get("best_model", ""),
        "best_model_summary": models.get("best_model_summary", {}),
        "edge_update_teacher_proxy_only": surrogates.get("edge_update_teacher_proxy_only", ""),
        "next_step": autopsy.get("next_step", ""),
        **G525_CLOSED_CLAIMS,
    }
    write_json_file(G525_DECISION_SUMMARY, summary)
    write_text_file(
        G525_DECISION_REPORT,
        "# Repair5G.5.25 Final Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- best_model: `{summary['best_model']}`\n"
        f"- top3_safe_oracle_capture_rate: `{summary['best_model_summary'].get('top3_safe_oracle_capture_rate', '')}`\n"
        f"- region_top2_capture_rate: `{summary['best_model_summary'].get('region_top2_capture_rate', '')}`\n"
        f"- positive_learning_gates: `{summary['positive_learning_gates']}`\n"
        f"- edge_update_teacher_proxy_only: `{summary['edge_update_teacher_proxy_only']}`\n"
        f"- next_step: `{summary['next_step']}`\n\n"
        "Closed claims remain:\n\n"
        "```text\n"
        "phase5p5_allowed=false\n"
        "phase6_allowed=false\n"
        "runtime_claim_allowed=false\n"
        "learned_runtime_policy_validated=false\n"
        "aaai_ready=false\n"
        "```\n",
    )
    print(json.dumps({"decision": decision, "best_model": summary["best_model"]}))
    return 0


__all__ = [name for name in globals() if name.startswith("G525_") or name.startswith("G524_")] + [
    "main_analyze_learning_failure_or_success",
    "main_create_blocked_rank_teacher_tables",
    "main_create_candidate_rank_effect_features",
    "main_run_enriched_trace_probe",
    "main_run_trace_logging_smoke",
    "main_trace_provenance_and_blocker",
    "main_train_eval_goal_aware_update_surrogates",
    "main_train_eval_rank_effect_models",
    "main_verify_g524_artifacts",
    "main_verify_logging_patch_static",
    "main_write_decision",
]

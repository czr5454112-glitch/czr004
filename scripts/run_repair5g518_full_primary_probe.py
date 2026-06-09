"""Conditionally run the G5.18 full-primary confirmation probe."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import append_jsonl  # noqa: E402
from repair5g3_common import MethodSpec  # noqa: E402
from repair5g5_common import prepare_scenarios, run_one_solver_task  # noqa: E402
from repair5g510_common import as_jsonable, best_candidate, candidate_scores_by_context_budget, mean, read_jsonl  # noqa: E402
from repair5g517_common import candidate_recognition_counts, write_probe_csv_from_jsonl  # noqa: E402
from repair5g518_common import (  # noqa: E402
    DEFAULT_BINARY,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    G518_BATCHES_SUMMARY,
    G518_CLOSED_CLAIMS,
    G518_FULL_PRIMARY_INTEGRITY_SUMMARY,
    G518_FULL_PRIMARY_ORACLE_SUMMARY,
    PRIMARY_BUDGETS_MS,
    batch_candidate_distribution_csv,
    duplicate_context_candidate_budget_rows,
    external_lacam2_solver_status,
    finite_number,
    maybe_read_json,
    observed_id_flags,
    observed_id_guard,
    old14_candidate_ids,
    read_csv_dicts,
    repo_root,
    resolve,
    score_from_probe,
    write_json_file,
)


DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g518_full_primary"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g518_full_primary_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g518_full_primary_scenario_generation.json"
DEFAULT_RESULTS_CSV = "outputs/tables/phase5p5_repair5g518_full_primary_probe_results.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--v5-csv", type=Path, default=Path("outputs/tables/phase5p5_repair5g515_candidate_feature_matrix_v5.csv"))
    parser.add_argument("--batch-summary-json", type=Path, default=Path(G518_BATCHES_SUMMARY))
    parser.add_argument("--results-csv", type=Path, default=Path(DEFAULT_RESULTS_CSV))
    parser.add_argument("--integrity-summary-json", type=Path, default=Path(G518_FULL_PRIMARY_INTEGRITY_SUMMARY))
    parser.add_argument("--oracle-summary-json", type=Path, default=Path(G518_FULL_PRIMARY_ORACLE_SUMMARY))
    parser.add_argument("--time-limit-sec", type=float, default=5.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def method_spec_for_budget(*, budget: int, selector_spec: Path, probe_jsonl: Path, checkpoint_jsonl: Path, candidates: list[str]) -> MethodSpec:
    return MethodSpec(
        "repair5g59_static_flow_shield",
        f"repair5g518_full_primary_budget_{budget}ms_static_context",
        (
            "--repair5g5-selector-spec",
            str(selector_spec),
            "--repair5g-export-update-checkpoints-jsonl",
            str(checkpoint_jsonl),
            "--repair5g-checkpoint-topk-edges",
            "64",
            "--repair5g-checkpoint-edge-filter",
            "nonzero",
            "--repair5g-counterfactual-update-probe-jsonl",
            str(probe_jsonl),
            "--repair5g-counterfactual-candidates",
            ",".join(candidates),
            "--repair5g-counterfactual-short-budget-ms",
            str(int(budget)),
            "--repair5g-counterfactual-max-contexts",
            "1",
            "--repair5g-runtime-audit-mode",
            "perf",
        ),
    )


def primary_combos(v5_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[tuple[str, int, int], dict[str, Any]] = {}
    for row in v5_rows:
        key = (str(row.get("map", "")), int(finite_number(row.get("agents"), 0)), int(finite_number(row.get("seed"), 0)))
        if key[0] and key not in seen:
            seen[key] = {"map": key[0], "agents": key[1], "seed": key[2]}
    return [seen[key] for key in sorted(seen)]


def write_skip(args: argparse.Namespace, reason: str, batch_decision: str) -> None:
    integrity = {
        "schema_version": "phase5p5_repair5g518_full_primary_integrity_summary_v1",
        "decision": "g518_full_primary_not_run_batch_gate_not_passed",
        "probe_ran": False,
        "no_run_reason": reason,
        "batch_decision": batch_decision,
        **G518_CLOSED_CLAIMS,
    }
    oracle = {
        "schema_version": "phase5p5_repair5g518_full_primary_oracle_summary_v1",
        "decision": "g518_full_primary_not_run_batch_gate_not_passed",
        "oracle_analyzed": False,
        "no_run_reason": reason,
        "batch_decision": batch_decision,
        **G518_CLOSED_CLAIMS,
    }
    write_json_file(args.integrity_summary_json, integrity)
    write_json_file(args.oracle_summary_json, oracle)


def top_new_candidates(batch_summary: dict[str, Any], limit: int = 16) -> list[str]:
    passed = set(batch_summary.get("candidate_space_gate_passed_batches", []))
    rows = []
    for batch in passed:
        rows.extend(read_csv_dicts(resolve(batch_candidate_distribution_csv(str(batch)), repo_root())))
    new_rows = [row for row in rows if row.get("candidate_role") == "g518_new_candidate"]
    ranked = sorted(
        new_rows,
        key=lambda row: (
            -int(finite_number(row.get("oracle_win_count"), 0)),
            finite_number(row.get("mean_delta_vs_static"), math.inf),
            str(row.get("dominated_by_nearest_old", "")).lower() == "true",
            row.get("candidate_id", ""),
        ),
    )
    out = []
    seen = set()
    for row in ranked:
        candidate = str(row.get("candidate_id", ""))
        if candidate and candidate not in seen:
            seen.add(candidate)
            out.append(candidate)
        if len(out) >= limit:
            break
    return out


def summarize_oracle(rows: list[dict[str, Any]], candidates: set[str], old_ids: set[str], new_ids: set[str]) -> dict[str, Any]:
    grouped = candidate_scores_by_context_budget(rows, allowed_candidates=candidates)
    gaps = []
    new_wins = 0
    complete = 0
    best_new_single = ("", math.inf)
    for (_key_budget, scores) in grouped.items():
        old_scores = {candidate: row for candidate, row in scores.items() if candidate in old_ids}
        all_scores = {candidate: row for candidate, row in scores.items() if candidate in candidates}
        old_id, old_score = best_candidate(old_scores)
        new_id, new_score = best_candidate(all_scores)
        if candidates <= set(all_scores):
            complete += 1
        if new_id in new_ids:
            new_wins += 1
        if math.isfinite(old_score) and math.isfinite(new_score):
            gaps.append(new_score - old_score)
        for candidate in new_ids:
            score = score_from_probe(scores.get(candidate, {}))
            if math.isfinite(score) and score < best_new_single[1]:
                best_new_single = (candidate, score)
    mean_gap = mean(gaps)
    improved = new_wins > 0 and math.isfinite(mean_gap) and mean_gap < 0.0
    return {
        "decision": "g518_full_primary_candidate_space_improved_continue_ranker" if improved else "g518_full_primary_candidate_space_failed_continue_update_mechanism_or_objective_design",
        "oracle_analyzed": bool(rows),
        "context_budget_pairs": len(grouped),
        "complete_context_budget_pairs": complete,
        "new_candidate_win_count": new_wins,
        "mean_new_oracle_gap_vs_old_oracle": as_jsonable(mean_gap),
        "candidate_count": len(candidates),
        "old_candidate_count": len(old_ids),
        "new_candidate_count": len(new_ids),
        "best_new_single_candidate": best_new_single[0],
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    batch_summary = maybe_read_json(args.batch_summary_json)
    batch_decision = str(batch_summary.get("decision", ""))
    if batch_decision != "g518_candidate_space_improved_continue_full_primary":
        write_skip(args, "no G5.18 batch passed the candidate-space gate", batch_decision)
        print(json.dumps({"decision": "g518_full_primary_not_run_batch_gate_not_passed", "probe_ran": False}))
        return 0
    if int(args.max_workers) != 1:
        write_skip(args, "max_workers must be 1 for G5.18 full-primary", batch_decision)
        return 2
    new_candidates = top_new_candidates(batch_summary, limit=8)
    old_controls = old14_candidate_ids(root)
    candidates = old_controls + new_candidates
    v5_rows = read_csv_dicts(resolve(args.v5_csv, root))
    combos = primary_combos(v5_rows)
    observed_id_guard([combo["seed"] for combo in combos], label="G5.18 full-primary seeds")
    log_dir = resolve(DEFAULT_LOG_DIR, root)
    scenario_dir = resolve(DEFAULT_SCENARIO_DIR, root)
    output_jsonl = log_dir / "phase5p5_repair5g518_full_primary_runs.jsonl"
    command_log = log_dir / "phase5p5_repair5g518_full_primary_commands.jsonl"
    update_log = log_dir / "phase5p5_repair5g518_full_primary_ltm_updates.jsonl"
    probe_jsonl = log_dir / "phase5p5_repair5g518_full_primary_update_probes.jsonl"
    checkpoint_jsonl = log_dir / "phase5p5_repair5g518_full_primary_checkpoints.jsonl"
    results_csv = resolve(args.results_csv, root)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log, probe_jsonl, checkpoint_jsonl, results_csv]:
            path.unlink(missing_ok=True)
    temp_dir = log_dir / "_task_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    prepare_scenarios(
        root=root,
        source_scenario_dir=resolve(args.source_scenario_dir, root),
        scenario_dir=scenario_dir,
        scenario_metadata=resolve(DEFAULT_SCENARIO_METADATA, root),
        maps=sorted({str(combo["map"]) for combo in combos}),
        agent_counts=sorted({int(combo["agents"]) for combo in combos}),
        instance_ids=sorted({int(combo["seed"]) for combo in combos}),
    )
    for combo in combos:
        for budget in PRIMARY_BUDGETS_MS:
            spec = method_spec_for_budget(
                budget=int(budget),
                selector_spec=resolve(args.selector_spec_json, root),
                probe_jsonl=probe_jsonl,
                checkpoint_jsonl=checkpoint_jsonl,
                candidates=candidates,
            )
            solver_rows, _updates, command_row = run_one_solver_task(
                root=root,
                binary=resolve(args.binary, root),
                scenario_dir=scenario_dir,
                temp_dir=temp_dir,
                update_log=update_log,
                map_name=str(combo["map"]),
                agents=int(combo["agents"]),
                seed=int(combo["seed"]),
                time_limit_sec=float(args.time_limit_sec),
                ltm_max_iterations=int(args.ltm_max_iterations),
                spec=spec,
                manifest="phase5p5-repair5g518-full-primary",
            )
            for row in solver_rows:
                append_jsonl(output_jsonl, row)
            append_jsonl(command_log, command_row)
    write_probe_csv_from_jsonl(probe_jsonl, results_csv)
    result_rows = read_csv_dicts(results_csv)
    checkpoint_rows = read_jsonl(checkpoint_jsonl)
    flags = observed_id_flags(result_rows)
    candidate_set = set(candidates)
    recognition = candidate_recognition_counts(result_rows, candidate_set)
    duplicate_rows = duplicate_context_candidate_budget_rows(result_rows)
    external_status = external_lacam2_solver_status(root)
    contexts = {row.get("normalized_context_key", "") for row in result_rows}
    budgets = sorted({int(float(row.get("short_budget_ms", 0))) for row in result_rows if row.get("short_budget_ms", "")})
    expected_rows = len(combos) * len(candidates) * len(PRIMARY_BUDGETS_MS)
    gates = {
        "probe_ran": bool(result_rows),
        "rows_eq_expected": len(result_rows) == expected_rows,
        "contexts_eq_60": len(contexts) == 60,
        "candidate_count_between_22_and_30": 22 <= len(candidates) <= 30,
        "budgets_eq_1000_2000": budgets == PRIMARY_BUDGETS_MS,
        "candidate_recognized_all": recognition["candidate_recognized_all"],
        "duplicate_context_candidate_budget_rows_eq_0": duplicate_rows == 0,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "external_lacam2_solver_untouched": not external_status,
    }
    integrity_decision = "g518_full_primary_integrity_passed_continue_oracle" if all(gates.values()) else "g518_full_primary_integrity_failed"
    integrity = {
        "schema_version": "phase5p5_repair5g518_full_primary_integrity_summary_v1",
        "decision": integrity_decision,
        "probe_ran": bool(result_rows),
        "probe_rows": len(result_rows),
        "expected_rows": expected_rows,
        "contexts": len(contexts),
        "candidate_count": len(candidates),
        "old_candidate_count": len(old_controls),
        "new_candidate_count": len(new_candidates),
        "checkpoint_rows": len(checkpoint_rows),
        "duplicate_context_candidate_budget_rows": duplicate_rows,
        "recognition": recognition,
        "external_lacam2_solver_status": external_status,
        "results_csv": str(results_csv),
        "gates": gates,
        **flags,
        **G518_CLOSED_CLAIMS,
    }
    oracle = summarize_oracle(result_rows, candidate_set, set(old_controls), set(new_candidates))
    oracle.update(
        {
            "schema_version": "phase5p5_repair5g518_full_primary_oracle_summary_v1",
            "integrity_decision": integrity_decision,
            **G518_CLOSED_CLAIMS,
        }
    )
    write_json_file(args.integrity_summary_json, integrity)
    write_json_file(args.oracle_summary_json, oracle)
    print(json.dumps({"decision": oracle["decision"], "probe_rows": len(result_rows), "mean_gap": oracle["mean_new_oracle_gap_vs_old_oracle"]}))
    return 0 if integrity_decision != "g518_full_primary_integrity_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Conditionally run the G5.17 full primary 60-context 24-candidate probe."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import append_jsonl  # noqa: E402
from repair5g3_common import MethodSpec  # noqa: E402
from repair5g5_common import prepare_scenarios, run_one_solver_task  # noqa: E402
from repair5g510_common import (  # noqa: E402
    as_jsonable,
    best_candidate,
    candidate_scores_by_context_budget,
    finite_number,
    mean,
    read_jsonl,
)
from repair5g512_common import observed_id_flags, observed_id_guard, read_csv_rows, read_json  # noqa: E402
from repair5g517_common import (  # noqa: E402
    DEFAULT_BINARY,
    DEFAULT_G515_V5_MATRIX,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    EXPECTED_FULL_ROWS,
    G517_CLOSED_CLAIMS,
    G517_FULL_INTEGRITY_SUMMARY,
    G517_FULL_ORACLE_SUMMARY,
    G517_ORACLE_SUMMARY,
    PRIMARY_BUDGETS_MS,
    candidate_ids_from_plan,
    candidate_recognition_counts,
    duplicate_context_candidate_budget_rows,
    external_lacam2_solver_status,
    plan_rows,
    read_csv_dicts,
    repair_candidate_ids,
    repo_root,
    resolve,
    write_json,
    write_probe_csv_from_jsonl,
)


DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g517_full_primary_24cand"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g517_full_primary_24cand_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g517_full_primary_24cand_scenario_generation.json"
DEFAULT_OUTPUT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g517_full_primary_24cand_runs.jsonl"
DEFAULT_COMMAND_LOG = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g517_full_primary_24cand_commands.jsonl"
DEFAULT_UPDATE_LOG = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g517_full_primary_24cand_ltm_updates.jsonl"
DEFAULT_PROBE_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g517_full_primary_24cand_update_probes.jsonl"
DEFAULT_CHECKPOINT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g517_full_primary_24cand_checkpoints.jsonl"
DEFAULT_RESULTS_CSV = "outputs/tables/phase5p5_repair5g517_full_primary_24cand_results.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--v5-csv", type=Path, default=Path(DEFAULT_G515_V5_MATRIX))
    parser.add_argument("--targeted-oracle-summary-json", type=Path, default=Path(G517_ORACLE_SUMMARY))
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_OUTPUT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMAND_LOG))
    parser.add_argument("--update-log", type=Path, default=Path(DEFAULT_UPDATE_LOG))
    parser.add_argument("--probe-jsonl", type=Path, default=Path(DEFAULT_PROBE_JSONL))
    parser.add_argument("--checkpoint-jsonl", type=Path, default=Path(DEFAULT_CHECKPOINT_JSONL))
    parser.add_argument("--results-csv", type=Path, default=Path(DEFAULT_RESULTS_CSV))
    parser.add_argument("--integrity-summary-json", type=Path, default=Path(G517_FULL_INTEGRITY_SUMMARY))
    parser.add_argument("--oracle-summary-json", type=Path, default=Path(G517_FULL_ORACLE_SUMMARY))
    parser.add_argument("--time-limit-sec", type=float, default=5.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def method_spec_for_budget(*, budget: int, selector_spec: Path, probe_jsonl: Path, checkpoint_jsonl: Path, candidates: list[str]) -> MethodSpec:
    return MethodSpec(
        "repair5g59_static_flow_shield",
        f"repair5g517_full_budget_{budget}ms_static_context",
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


def primary_combos(v5_rows: list[dict[str, str]]) -> list[dict[str, int | str]]:
    seen: dict[tuple[str, int, int], dict[str, int | str]] = {}
    for row in v5_rows:
        key = (str(row.get("map", "")), int(finite_number(row.get("agents"), 0)), int(finite_number(row.get("seed"), 0)))
        if key[0] and key not in seen:
            seen[key] = {"map": key[0], "agents": key[1], "seed": key[2]}
    return [seen[key] for key in sorted(seen)]


def write_skip(args: argparse.Namespace, root: Path, reason: str, targeted_decision: str) -> None:
    integrity = {
        "schema_version": "phase5p5_repair5g517_full_primary_24cand_integrity_summary_v1",
        "decision": "full_primary_not_run_targeted_oracle_gate_not_passed",
        "probe_ran": False,
        "no_run_reason": reason,
        "targeted_oracle_decision": targeted_decision,
        "expected_rows": EXPECTED_FULL_ROWS,
        **G517_CLOSED_CLAIMS,
    }
    oracle = {
        "schema_version": "phase5p5_repair5g517_full_primary_24cand_oracle_summary_v1",
        "decision": "full_primary_not_run_targeted_oracle_gate_not_passed",
        "oracle_analyzed": False,
        "no_run_reason": reason,
        "targeted_oracle_decision": targeted_decision,
        **G517_CLOSED_CLAIMS,
    }
    write_json(resolve(args.integrity_summary_json, root), integrity)
    write_json(resolve(args.oracle_summary_json, root), oracle)


def summarize_oracle(rows: list[dict[str, str]], candidates: set[str], repair_ids: set[str]) -> dict[str, object]:
    grouped = candidate_scores_by_context_budget(rows, allowed_candidates=candidates)
    old_ids = candidates - repair_ids
    gaps = []
    repair_wins = 0
    complete = 0
    for _key_budget, scores in grouped.items():
        old_scores = {candidate: row for candidate, row in scores.items() if candidate in old_ids}
        new_scores = {candidate: row for candidate, row in scores.items() if candidate in candidates}
        old_id, old_score = best_candidate(old_scores)
        new_id, new_score = best_candidate(new_scores)
        if candidates <= set(new_scores):
            complete += 1
        if new_id in repair_ids:
            repair_wins += 1
        if math.isfinite(old_score) and math.isfinite(new_score):
            gaps.append(new_score - old_score)
    mean_gap = mean(gaps)
    improved = repair_wins > 0 and math.isfinite(mean_gap) and mean_gap < 0.0
    return {
        "decision": "full_primary_24cand_oracle_improved_continue_ranker" if improved else "full_primary_24cand_oracle_failed_continue_lattice_design",
        "oracle_analyzed": bool(rows),
        "context_budget_pairs": len(grouped),
        "complete_context_budget_pairs": complete,
        "repair_candidate_win_count": repair_wins,
        "mean_new_oracle_gap_vs_old_oracle": as_jsonable(mean_gap),
        "candidate_count": len(candidates),
        "repair_candidate_count": len(repair_ids),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    targeted = read_json(resolve(args.targeted_oracle_summary_json, root)) if resolve(args.targeted_oracle_summary_json, root).exists() else {}
    targeted_decision = str(targeted.get("decision", ""))
    if targeted_decision != "targeted_repair_lattice_oracle_improved_continue_full_primary":
        reason = "targeted oracle gate did not pass; full-primary expansion is intentionally skipped"
        write_skip(args, root, reason, targeted_decision)
        print(json.dumps({"decision": "full_primary_not_run_targeted_oracle_gate_not_passed", "probe_ran": False}))
        return 0

    if int(args.max_workers) != 1:
        reason = "max_workers must be 1 for G5.17 local full-primary expansion"
        write_skip(args, root, reason, targeted_decision)
        print(json.dumps({"decision": "full_primary_not_run_targeted_oracle_gate_not_passed", "probe_ran": False, "reason": reason}))
        return 2

    output_jsonl = resolve(args.output_jsonl, root)
    command_log = resolve(args.command_log, root)
    update_log = resolve(args.update_log, root)
    probe_jsonl = resolve(args.probe_jsonl, root)
    checkpoint_jsonl = resolve(args.checkpoint_jsonl, root)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log, probe_jsonl, checkpoint_jsonl, resolve(args.results_csv, root)]:
            path.unlink(missing_ok=True)
    temp_dir = output_jsonl.parent / "_task_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    command_log.parent.mkdir(parents=True, exist_ok=True)

    v5_rows = read_csv_rows(resolve(args.v5_csv, root))
    combos = primary_combos(v5_rows)
    observed_id_guard([combo["seed"] for combo in combos], label="G5.17 full-primary seeds")
    candidates = candidate_ids_from_plan(plan_rows())
    repair_ids = set(repair_candidate_ids())
    maps = sorted({str(combo["map"]) for combo in combos})
    agents = sorted({int(combo["agents"]) for combo in combos})
    seeds = sorted({int(combo["seed"]) for combo in combos})
    prepare_scenarios(
        root=root,
        source_scenario_dir=resolve(args.source_scenario_dir, root),
        scenario_dir=resolve(args.scenario_dir, root),
        scenario_metadata=resolve(args.scenario_metadata_json, root),
        maps=maps,
        agent_counts=agents,
        instance_ids=seeds,
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
                scenario_dir=resolve(args.scenario_dir, root),
                temp_dir=temp_dir,
                update_log=update_log,
                map_name=str(combo["map"]),
                agents=int(combo["agents"]),
                seed=int(combo["seed"]),
                time_limit_sec=float(args.time_limit_sec),
                ltm_max_iterations=int(args.ltm_max_iterations),
                spec=spec,
                manifest="phase5p5-repair5g517-full-primary-24cand",
            )
            for row in solver_rows:
                append_jsonl(output_jsonl, row)
            append_jsonl(command_log, command_row)

    _probe_rows = write_probe_csv_from_jsonl(probe_jsonl, resolve(args.results_csv, root))
    result_rows = read_csv_dicts(resolve(args.results_csv, root))
    checkpoint_rows = read_jsonl(checkpoint_jsonl)
    flags = observed_id_flags(result_rows)
    candidate_set = set(candidates)
    recognition = candidate_recognition_counts(result_rows, candidate_set)
    duplicate_rows = duplicate_context_candidate_budget_rows(result_rows)
    external_status = external_lacam2_solver_status(root)
    contexts = {row.get("normalized_context_key", "") for row in result_rows}
    budgets = {int(float(row.get("short_budget_ms", 0))) for row in result_rows if row.get("short_budget_ms", "")}
    gates = {
        "probe_ran": bool(result_rows),
        "rows_eq_2880": len(result_rows) == EXPECTED_FULL_ROWS,
        "contexts_eq_60": len(contexts) == 60,
        "candidates_eq_24": len({row.get("candidate_id", "") for row in result_rows}) == 24,
        "budgets_eq_1000_2000": sorted(budgets) == PRIMARY_BUDGETS_MS,
        "candidate_recognized_all": recognition["candidate_recognized_all"],
        "duplicate_context_candidate_budget_rows_eq_0": duplicate_rows == 0,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "external_lacam2_solver_untouched": not external_status,
    }
    integrity_decision = "full_primary_24cand_integrity_passed_continue_oracle" if all(gates.values()) else "full_primary_24cand_integrity_failed"
    integrity = {
        "schema_version": "phase5p5_repair5g517_full_primary_24cand_integrity_summary_v1",
        "decision": integrity_decision,
        "probe_ran": bool(result_rows),
        "probe_rows": len(result_rows),
        "expected_rows": EXPECTED_FULL_ROWS,
        "contexts": len(contexts),
        "candidate_count": len({row.get("candidate_id", "") for row in result_rows}),
        "checkpoint_rows": len(checkpoint_rows),
        "duplicate_context_candidate_budget_rows": duplicate_rows,
        "recognition": recognition,
        "external_lacam2_solver_status": external_status,
        "results_csv": str(resolve(args.results_csv, root)),
        "gates": gates,
        **flags,
        **G517_CLOSED_CLAIMS,
    }
    oracle = summarize_oracle(result_rows, candidate_set, repair_ids)
    oracle.update(
        {
            "schema_version": "phase5p5_repair5g517_full_primary_24cand_oracle_summary_v1",
            "integrity_decision": integrity_decision,
            **G517_CLOSED_CLAIMS,
        }
    )
    write_json(resolve(args.integrity_summary_json, root), integrity)
    write_json(resolve(args.oracle_summary_json, root), oracle)
    print(json.dumps({"decision": oracle["decision"], "probe_rows": len(result_rows), "mean_gap": oracle["mean_new_oracle_gap_vs_old_oracle"]}))
    return 0 if integrity_decision != "full_primary_24cand_integrity_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Run the G5.17 20-context targeted repair lattice probe."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import append_jsonl  # noqa: E402
from repair5g3_common import MethodSpec  # noqa: E402
from repair5g5_common import prepare_scenarios, run_one_solver_task  # noqa: E402
from repair5g510_common import read_jsonl  # noqa: E402
from repair5g512_common import observed_id_flags, observed_id_guard  # noqa: E402
from repair5g517_common import (  # noqa: E402
    DEFAULT_BINARY,
    DEFAULT_G516_PROBE_PLAN,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    EXPECTED_TARGETED_ROWS,
    G517_ADAPTER_SUMMARY,
    G517_CLOSED_CLAIMS,
    G517_SMOKE_SUMMARY,
    G517_TARGETED_INTEGRITY_REPORT,
    G517_TARGETED_INTEGRITY_SUMMARY,
    G517_TARGETED_PROBE_JSONL,
    G517_TARGETED_RESULTS,
    MAX_TARGET_CONTEXTS,
    PRIMARY_BUDGETS_MS,
    assert_observed_plan,
    candidate_ids_from_plan,
    candidate_recognition_counts,
    context_combos_from_plan,
    duplicate_context_candidate_budget_rows,
    external_lacam2_solver_status,
    plan_rows,
    read_csv_dicts,
    repair_candidate_ids,
    repo_root,
    resolve,
    write_json,
    write_probe_csv_from_jsonl,
    write_text,
)


DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g517_targeted_probe"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g517_targeted_probe_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g517_targeted_probe_scenario_generation.json"
DEFAULT_OUTPUT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g517_targeted_probe_runs.jsonl"
DEFAULT_COMMAND_LOG = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g517_targeted_probe_commands.jsonl"
DEFAULT_UPDATE_LOG = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g517_targeted_probe_ltm_updates.jsonl"
DEFAULT_CHECKPOINT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g517_targeted_probe_checkpoints.jsonl"
DEFAULT_STATUS_JSON = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g517_targeted_probe_status.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--probe-plan-csv", type=Path, default=Path(DEFAULT_G516_PROBE_PLAN))
    parser.add_argument("--adapter-summary-json", type=Path, default=Path(G517_ADAPTER_SUMMARY))
    parser.add_argument("--adapter-smoke-summary-json", type=Path, default=Path(G517_SMOKE_SUMMARY))
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_OUTPUT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMAND_LOG))
    parser.add_argument("--update-log", type=Path, default=Path(DEFAULT_UPDATE_LOG))
    parser.add_argument("--probe-jsonl", type=Path, default=Path(G517_TARGETED_PROBE_JSONL))
    parser.add_argument("--checkpoint-jsonl", type=Path, default=Path(DEFAULT_CHECKPOINT_JSONL))
    parser.add_argument("--results-csv", type=Path, default=Path(G517_TARGETED_RESULTS))
    parser.add_argument("--summary-json", type=Path, default=Path(G517_TARGETED_INTEGRITY_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G517_TARGETED_INTEGRITY_REPORT))
    parser.add_argument("--status-json", type=Path, default=Path(DEFAULT_STATUS_JSON))
    parser.add_argument("--time-limit-sec", type=float, default=5.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def method_spec_for_budget(*, budget: int, selector_spec: Path, probe_jsonl: Path, checkpoint_jsonl: Path, candidates: list[str]) -> MethodSpec:
    return MethodSpec(
        "repair5g59_static_flow_shield",
        f"repair5g517_budget_{budget}ms_static_context",
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


def read_json_or_empty(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    plan = plan_rows(resolve(args.probe_plan_csv, root))
    flags = assert_observed_plan(plan, label="G5.17 targeted probe plan seeds")
    adapter = read_json_or_empty(resolve(args.adapter_summary_json, root))
    smoke = read_json_or_empty(resolve(args.adapter_smoke_summary_json, root))
    preflight_ok = (
        adapter.get("decision") == "adapter_recognition_passed_continue_local_probe"
        and smoke.get("decision") == "adapter_smoke_passed_continue_targeted_probe"
        and int(args.max_workers) == 1
    )
    if not preflight_ok:
        decision = "targeted_probe_integrity_failed"
        summary = {
            "schema_version": "phase5p5_repair5g517_targeted_probe_integrity_summary_v1",
            "decision": decision,
            "probe_ran": False,
            "no_run_reason": "adapter recognition or adapter smoke preflight did not pass",
            "adapter_decision": adapter.get("decision", ""),
            "adapter_smoke_decision": smoke.get("decision", ""),
            "max_workers": int(args.max_workers),
            **flags,
            **G517_CLOSED_CLAIMS,
        }
        write_json(resolve(args.summary_json, root), summary)
        write_text(resolve(args.report, root), "# Phase5.5 Repair5G.5.17 Targeted Probe Integrity\n\n- decision: `targeted_probe_integrity_failed`\n- probe_ran: `false`\n")
        print(json.dumps({"decision": decision, "probe_ran": False}))
        return 2

    output_jsonl = resolve(args.output_jsonl, root)
    command_log = resolve(args.command_log, root)
    update_log = resolve(args.update_log, root)
    probe_jsonl = resolve(args.probe_jsonl, root)
    checkpoint_jsonl = resolve(args.checkpoint_jsonl, root)
    status_json = resolve(args.status_json, root)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log, probe_jsonl, checkpoint_jsonl, resolve(args.results_csv, root), status_json]:
            path.unlink(missing_ok=True)
    temp_dir = output_jsonl.parent / "_task_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    command_log.parent.mkdir(parents=True, exist_ok=True)

    candidates = candidate_ids_from_plan(plan)
    repair_candidates = set(repair_candidate_ids())
    combos = context_combos_from_plan(plan)
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

    tasks = [(combo, budget) for combo in combos for budget in PRIMARY_BUDGETS_MS]
    status_json.parent.mkdir(parents=True, exist_ok=True)
    status_json.write_text(json.dumps({"phase": "starting", "total_tasks": len(tasks), "completed_tasks": 0}, indent=2) + "\n", encoding="utf-8")
    completed = 0
    for combo, budget in tasks:
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
            manifest="phase5p5-repair5g517-targeted-probe",
        )
        for row in solver_rows:
            append_jsonl(output_jsonl, row)
        append_jsonl(command_log, command_row)
        completed += 1
        status_json.write_text(
            json.dumps(
                {
                    "phase": "running" if completed < len(tasks) else "solver_complete",
                    "total_tasks": len(tasks),
                    "completed_tasks": completed,
                    "last_task": {
                        "map": combo["map"],
                        "agents": combo["agents"],
                        "seed": combo["seed"],
                        "budget": budget,
                        "returncode": command_row["returncode"],
                    },
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    probe_rows = write_probe_csv_from_jsonl(probe_jsonl, resolve(args.results_csv, root))
    result_rows = read_csv_dicts(resolve(args.results_csv, root))
    checkpoint_rows = read_jsonl(checkpoint_jsonl)
    observed_id_guard([row.get("seed", "") for row in result_rows], label="G5.17 targeted probe result seeds")
    result_flags = observed_id_flags(result_rows)
    candidate_set = set(candidates)
    recognition = candidate_recognition_counts(result_rows, candidate_set)
    repair_recognition = candidate_recognition_counts(result_rows, repair_candidates)
    contexts = {row.get("normalized_context_key", "") for row in result_rows}
    budgets = {int(float(row.get("short_budget_ms", 0))) for row in result_rows if row.get("short_budget_ms", "")}
    candidate_seen = {row.get("candidate_id", "") for row in result_rows}
    duplicate_rows = duplicate_context_candidate_budget_rows(result_rows)
    external_status = external_lacam2_solver_status(root)
    gates = {
        "probe_ran": bool(probe_rows),
        "rows_eq_960": len(result_rows) == EXPECTED_TARGETED_ROWS,
        "contexts_eq_target_count": len(contexts) == len(combos) <= MAX_TARGET_CONTEXTS,
        "candidates_eq_24": len(candidate_seen & candidate_set) == 24,
        "repair_candidates_eq_10": len(candidate_seen & repair_candidates) == 10,
        "budgets_eq_1000_2000": sorted(budgets) == PRIMARY_BUDGETS_MS,
        "candidate_recognized_all": recognition["candidate_recognized_all"],
        "repair_candidate_recognized_all": repair_recognition["candidate_recognized_all"],
        "duplicate_context_candidate_budget_rows_eq_0": duplicate_rows == 0,
        "ids_166_205_untouched": result_flags["ids_166_205_untouched"] and flags["ids_166_205_untouched"],
        "observed_ids_only": result_flags["observed_ids_only"] and flags["observed_ids_only"],
        "max_workers_eq_1": int(args.max_workers) == 1,
        "external_lacam2_solver_untouched": not external_status,
    }
    passed = all(gates.values())
    decision = "targeted_probe_integrity_passed_continue_oracle" if passed else "targeted_probe_integrity_failed"
    summary = {
        "schema_version": "phase5p5_repair5g517_targeted_probe_integrity_summary_v1",
        "decision": decision,
        "probe_ran": bool(probe_rows),
        "planned_rows": len(plan),
        "probe_rows": len(result_rows),
        "expected_rows": EXPECTED_TARGETED_ROWS,
        "target_contexts": len(combos),
        "measured_contexts": len(contexts),
        "candidate_count": len(candidate_seen & candidate_set),
        "repair_candidate_count": len(candidate_seen & repair_candidates),
        "budgets": sorted(budgets),
        "max_workers": int(args.max_workers),
        "checkpoint_rows": len(checkpoint_rows),
        "duplicate_context_candidate_budget_rows": duplicate_rows,
        "recognition": recognition,
        "repair_recognition": repair_recognition,
        "external_lacam2_solver_status": external_status,
        "results_csv": str(resolve(args.results_csv, root)),
        "probe_jsonl": str(probe_jsonl),
        "gates": gates,
        **result_flags,
        **G517_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.17 Targeted Probe Integrity\n\n"
        f"- decision: `{decision}`\n"
        f"- probe_ran: `{bool(probe_rows)}`\n"
        f"- probe_rows: `{len(result_rows)}`\n"
        f"- expected_rows: `{EXPECTED_TARGETED_ROWS}`\n"
        f"- target_contexts: `{len(combos)}`\n"
        f"- measured_contexts: `{len(contexts)}`\n"
        f"- candidate_count: `{len(candidate_seen & candidate_set)}`\n"
        f"- repair_candidate_count: `{len(candidate_seen & repair_candidates)}`\n"
        f"- duplicate_context_candidate_budget_rows: `{duplicate_rows}`\n"
        f"- candidate_recognized_all: `{recognition['candidate_recognized_all']}`\n"
        f"- ids_166_205_untouched: `{summary['ids_166_205_untouched']}`\n"
        f"- observed_ids_only: `{summary['observed_ids_only']}`\n"
        f"- gates: `{gates}`\n\n"
        "The probe is local, sequential, and writes isolated G5.17 output paths. These rows are candidate-space diagnostics only; runtime-policy, Phase5.5, Phase6, and AAAI claims remain closed.\n",
    )
    print(json.dumps({"decision": decision, "probe_rows": len(result_rows), "measured_contexts": len(contexts)}))
    return 0 if passed else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

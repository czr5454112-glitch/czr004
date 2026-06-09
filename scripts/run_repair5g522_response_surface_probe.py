"""Run the local G5.22 response-surface counterfactual probe."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import append_jsonl  # noqa: E402
from repair5g3_common import MethodSpec  # noqa: E402
from repair5g5_common import prepare_scenarios, run_one_solver_task  # noqa: E402
from repair5g522_common import (  # noqa: E402
    DEFAULT_BINARY,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    G522_ADAPTER_SUMMARY,
    G522_CLOSED_CLAIMS,
    G522_CONTEXT_PANEL_CSV,
    G522_PROBE_INTEGRITY_REPORT,
    G522_PROBE_INTEGRITY_SUMMARY,
    G522_PROBE_LOG_DIR,
    G522_PROBE_RESULTS_CSV,
    G522_PROBE_SCENARIO_DIR,
    G522_PROBE_SCENARIO_METADATA,
    PRIMARY_BUDGETS,
    candidate_presence_gate,
    candidate_recognition_counts,
    duplicate_context_candidate_budget_rows,
    external_lacam2_solver_status,
    finite_number,
    g518_retained_candidate_ids,
    observed_id_flags,
    observed_id_guard,
    old14_candidate_ids,
    probe_candidate_ids,
    read_json_file,
    read_jsonl,
    read_rows,
    repo_root,
    resolve,
    selected_g522_candidate_ids,
    write_json_file,
    write_text_file,
)
from repair5g517_common import write_probe_csv_from_jsonl  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(G522_PROBE_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(G522_PROBE_SCENARIO_METADATA))
    parser.add_argument("--context-panel-csv", type=Path, default=Path(G522_CONTEXT_PANEL_CSV))
    parser.add_argument("--results-csv", type=Path, default=Path(G522_PROBE_RESULTS_CSV))
    parser.add_argument("--integrity-summary-json", type=Path, default=Path(G522_PROBE_INTEGRITY_SUMMARY))
    parser.add_argument("--integrity-report", type=Path, default=Path(G522_PROBE_INTEGRITY_REPORT))
    parser.add_argument("--time-limit-sec", type=float, default=5.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--max-contexts", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def context_combo(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "normalized_context_key": row.get("normalized_context_key", ""),
        "map": row.get("map", ""),
        "agents": int(finite_number(row.get("agents"), 0)),
        "seed": int(finite_number(row.get("seed"), 0)),
        "context_bucket": row.get("context_bucket", ""),
    }


def method_spec_for_budget(*, budget: int, selector_spec: Path, probe_jsonl: Path, checkpoint_jsonl: Path, candidates: list[str]) -> MethodSpec:
    return MethodSpec(
        "repair5g59_static_flow_shield",
        f"repair5g522_response_surface_budget_{budget}ms_static_context",
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


def write_skip(args: argparse.Namespace, reason: str, adapter_decision: str = "") -> None:
    summary = {
        "schema_version": "phase5p5_repair5g522_response_surface_probe_integrity_summary_v1",
        "decision": "response_surface_probe_not_run",
        "probe_ran": False,
        "no_run_reason": reason,
        "adapter_decision": adapter_decision,
        **G522_CLOSED_CLAIMS,
    }
    write_json_file(args.integrity_summary_json, summary)
    write_text_file(args.integrity_report, f"# Repair5G.5.22 Response-Surface Probe Integrity\n\n- decision: `response_surface_probe_not_run`\n- reason: `{reason}`\n")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    if int(args.max_workers) != 1:
        write_skip(args, "max_workers must be 1 for local G5.22 response-surface probe")
        print(json.dumps({"decision": "response_surface_probe_not_run", "reason": "max_workers must be 1"}))
        return 2
    adapter = read_json_file(G522_ADAPTER_SUMMARY) if resolve(G522_ADAPTER_SUMMARY, root).exists() else {}
    if adapter.get("decision") != "response_design_adapter_passed_continue_probe":
        write_skip(args, "adapter grammar did not pass", str(adapter.get("decision", "")))
        print(json.dumps({"decision": "response_surface_probe_not_run", "reason": "adapter grammar did not pass"}))
        return 2
    contexts = [context_combo(row) for row in read_rows(args.context_panel_csv)]
    if args.max_contexts and args.max_contexts > 0:
        contexts = contexts[: int(args.max_contexts)]
    observed_id_guard([row["seed"] for row in contexts], label="G5.22 response-surface contexts")
    old_controls = old14_candidate_ids(root)
    retained_g518 = g518_retained_candidate_ids(limit=8)
    selected_g522 = selected_g522_candidate_ids(include_probe_only=True)
    candidates = probe_candidate_ids()
    log_dir = resolve(G522_PROBE_LOG_DIR, root)
    output_jsonl = log_dir / "phase5p5_repair5g522_response_surface_runs.jsonl"
    command_log = log_dir / "phase5p5_repair5g522_response_surface_commands.jsonl"
    update_log = log_dir / "phase5p5_repair5g522_response_surface_ltm_updates.jsonl"
    probe_jsonl = log_dir / "phase5p5_repair5g522_response_surface_update_probes.jsonl"
    checkpoint_jsonl = log_dir / "phase5p5_repair5g522_response_surface_checkpoints.jsonl"
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
        scenario_dir=resolve(args.scenario_dir, root),
        scenario_metadata=resolve(args.scenario_metadata_json, root),
        maps=sorted({str(row["map"]) for row in contexts}),
        agent_counts=sorted({int(row["agents"]) for row in contexts}),
        instance_ids=sorted({int(row["seed"]) for row in contexts}),
    )
    for combo in contexts:
        for budget in PRIMARY_BUDGETS:
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
                manifest="phase5p5-repair5g522-response-surface",
            )
            for row in solver_rows:
                append_jsonl(output_jsonl, row)
            append_jsonl(command_log, command_row)
    write_probe_csv_from_jsonl(probe_jsonl, results_csv)
    result_rows = read_rows(results_csv)
    checkpoint_rows = read_jsonl(checkpoint_jsonl)
    command_rows = read_jsonl(command_log)
    flags = observed_id_flags(result_rows)
    budgets = sorted({int(finite_number(row.get("short_budget_ms"), -1)) for row in result_rows})
    contexts_seen = {str(row.get("normalized_context_key", "")) for row in result_rows}
    expected_rows = len(contexts) * len(candidates) * len(PRIMARY_BUDGETS)
    recognition = candidate_recognition_counts(result_rows, set(candidates))
    duplicate_rows = duplicate_context_candidate_budget_rows(result_rows)
    external_status = external_lacam2_solver_status(root)
    gates = {
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "duplicate_context_candidate_budget_rows_eq_0": duplicate_rows == 0,
        "all_selected_candidates_recognized": recognition["candidate_recognized_all"],
        "old14_controls_present_every_context": candidate_presence_gate(result_rows, old_controls),
        "g518_retained_controls_present_every_context": candidate_presence_gate(result_rows, retained_g518),
        "g522_selected_candidates_present_every_context": candidate_presence_gate(result_rows, selected_g522),
        "primary_budgets_present": budgets == PRIMARY_BUDGETS,
        "rows_eq_expected": len(result_rows) == expected_rows,
        "contexts_le_36": len(contexts_seen) <= 36 and len(contexts_seen) == len(contexts),
        "candidate_count_le_70": len(candidates) <= 70,
        "raw_logs_and_command_jsonl_recorded": probe_jsonl.exists() and command_log.exists() and bool(command_rows),
        "max_workers_eq_1": int(args.max_workers) == 1,
        "external_lacam2_solver_untouched": not external_status,
    }
    decision = "response_surface_probe_integrity_passed_continue_oracle" if all(gates.values()) else "response_surface_probe_integrity_failed"
    summary = {
        "schema_version": "phase5p5_repair5g522_response_surface_probe_integrity_summary_v1",
        "decision": decision,
        "probe_ran": bool(result_rows),
        "contexts_planned": len(contexts),
        "contexts_observed": len(contexts_seen),
        "old14_candidate_count": len(old_controls),
        "g518_retained_candidate_count": len(retained_g518),
        "g522_selected_candidate_count": len(selected_g522),
        "candidate_count": len(candidates),
        "budgets": budgets,
        "probe_rows": len(result_rows),
        "expected_rows": expected_rows,
        "checkpoint_rows": len(checkpoint_rows),
        "command_rows": len(command_rows),
        "duplicate_context_candidate_budget_rows": duplicate_rows,
        "recognition": recognition,
        "raw_jsonl": str(probe_jsonl),
        "command_log_jsonl": str(command_log),
        "checkpoint_jsonl": str(checkpoint_jsonl),
        "results_csv": str(results_csv),
        "external_lacam2_solver_status": external_status,
        "gates": gates,
        **flags,
        **G522_CLOSED_CLAIMS,
    }
    write_json_file(args.integrity_summary_json, summary)
    write_text_file(
        args.integrity_report,
        "# Repair5G.5.22 Response-Surface Probe Integrity\n\n"
        f"- decision: `{decision}`\n"
        f"- contexts_planned: `{len(contexts)}`\n"
        f"- contexts_observed: `{len(contexts_seen)}`\n"
        f"- candidate_count: `{len(candidates)}`\n"
        f"- budgets: `{budgets}`\n"
        f"- probe_rows: `{len(result_rows)}`\n"
        f"- expected_rows: `{expected_rows}`\n"
        f"- duplicate_context_candidate_budget_rows: `{duplicate_rows}`\n"
        f"- raw_jsonl: `{probe_jsonl}`\n"
        f"- command_log_jsonl: `{command_log}`\n"
        f"- checkpoint_jsonl: `{checkpoint_jsonl}`\n"
        f"- gates: `{gates}`\n",
    )
    print(json.dumps({"decision": decision, "probe_rows": len(result_rows), "contexts": len(contexts_seen)}))
    return 0 if decision != "response_surface_probe_integrity_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

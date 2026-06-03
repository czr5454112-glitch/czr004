"""Run Repair5G.4 time-budget and LTM-iteration stress after G4 passes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import (  # noqa: E402
    AGENTS,
    CONTROL_METHODS,
    MAPS,
    add_selector_alias_rows,
    audit_and_prepare_scenarios,
    build_specs,
    frozen_underlying_methods,
    git_value,
    grouped_rows,
    load_json,
    method_stats,
    now_iso,
    paired_rows,
    read_jsonl,
    repo_root,
    resolve,
    run_solver_grid,
    schema_error_count,
    synthesize_seeded_diagnostics,
    write_csv_rows,
    write_json,
    write_jsonl,
    write_method_report,
    write_update_summary,
)
from run_repair5g4_clean_frozen_validation import G4_SYNTHETIC_METHODS  # noqa: E402


DEFAULT_BINARY = "build/phase1a-batch/phase1a_batch.exe"
DEFAULT_SOURCE_SCENARIO_DIR = "outputs/tmp/phase1a/generated/phase1a-generated-random"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g4_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g4_scenario_generation.json"
DEFAULT_RUNTIME_ROOT = "outputs/tmp/phase5p5_repair5g4_runtimes"
DEFAULT_FROZEN_SPEC = "outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json"
DEFAULT_G4_SUMMARY = "outputs/reports/phase5p5_repair5g4_clean_frozen_validation_summary.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g4_time_iteration_stress"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g4_time_iteration_stress.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g4_time_iteration_stress_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g4_time_iteration_stress_ltm_updates.jsonl"
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g4_time_iteration_stress_paired.csv"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g4_time_iteration_stress_summary.csv"
DEFAULT_BY_BUDGET = "outputs/tables/phase5p5_repair5g4_time_iteration_stress_by_budget.csv"
DEFAULT_BY_ITER = "outputs/tables/phase5p5_repair5g4_time_iteration_stress_by_iteration.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g4_time_iteration_stress_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g4_time_iteration_stress_summary.json"

SELECTED = "repair5g2_frozen_static_or_selector"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--runtime-root", type=Path, default=Path(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_SPEC))
    parser.add_argument("--g4-summary-json", type=Path, default=Path(DEFAULT_G4_SUMMARY))
    parser.add_argument("--maps", nargs="+", default=MAPS)
    parser.add_argument("--agent-counts", nargs="+", type=int, default=AGENTS)
    parser.add_argument("--instance-ids", nargs="+", type=int, default=list(range(126, 146)))
    parser.add_argument("--time-limit-sec", nargs="+", type=float, default=[1.0, 3.0, 5.0, 10.0])
    parser.add_argument("--ltm-max-iterations", nargs="+", type=int, default=[2, 4, 8])
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMANDS))
    parser.add_argument("--update-log", type=Path, default=Path(DEFAULT_UPDATES))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED))
    parser.add_argument("--summary-csv", type=Path, default=Path(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--by-budget-csv", type=Path, default=Path(DEFAULT_BY_BUDGET))
    parser.add_argument("--by-iteration-csv", type=Path, default=Path(DEFAULT_BY_ITER))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--ignore-g4-gate", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def actual_methods(spec: dict[str, Any]) -> list[str]:
    return list(
        dict.fromkeys(
            [
                *CONTROL_METHODS,
                "repair5g_dual_c_equiv_c100_b100_w075_d100",
                "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
                "repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75",
                *frozen_underlying_methods(spec),
            ]
        )
    )


def run_combo(
    *,
    root: Path,
    args: argparse.Namespace,
    specs: list[Any],
    scenario_dir: Path,
    methods: list[str],
    time_budget: float,
    iteration_budget: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    output_dir = resolve(args.output_jsonl, root).parent
    token = f"t{str(time_budget).replace('.', 'p')}_i{iteration_budget}"
    raw_jsonl = output_dir / f"{token}.raw.jsonl"
    commands = output_dir / f"{token}.commands.jsonl"
    if args.overwrite:
        for path in [raw_jsonl, commands]:
            if path.exists():
                path.unlink()
    completed = {
        (str(row.get("map")), int(row.get("agents")), int(row.get("seed")), str(row.get("method")))
        for row in read_jsonl(raw_jsonl)
    }
    if not args.skip_solver:
        run_solver_grid(
            root=root,
            binary=resolve(args.binary, root),
            scenario_dir=scenario_dir,
            output_jsonl=raw_jsonl,
            command_log=commands,
            maps=[str(value) for value in args.maps],
            agent_counts=[int(value) for value in args.agent_counts],
            instance_ids=[int(value) for value in args.instance_ids],
            time_limit_sec=float(time_budget),
            ltm_max_iterations=int(iteration_budget),
            methods=specs,
            completed=completed,
            max_workers=int(args.max_workers),
            manifest="phase5p5-repair5g4-time-iteration-stress",
            status_json=output_dir / f"{token}.status.json",
        )
    rows = [row for row in read_jsonl(raw_jsonl) if str(row.get("method")) in set(methods)]
    rows = [dict(row, time_budget_sec=time_budget, ltm_iteration_budget=iteration_budget) for row in rows]
    return rows, read_jsonl(commands)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    g4 = load_json(resolve(args.g4_summary_json, root))
    if (
        g4
        and not args.ignore_g4_gate
        and not (
            g4.get("gates", {}).get("protocol_gates_passed")
            and g4.get("gates", {}).get("representation_gates_passed")
        )
    ):
        raise SystemExit("G4 clean validation did not pass; stress is blocked")
    spec = load_json(resolve(args.frozen_selector_spec_json, root))
    methods = actual_methods(spec)
    specs = build_specs(methods, resolve(args.runtime_root, root))
    scenario_dir = resolve(args.scenario_dir, root)
    audit_and_prepare_scenarios(
        root=root,
        source_scenario_dir=resolve(args.source_scenario_dir, root),
        scenario_dir=scenario_dir,
        scenario_metadata=resolve(args.scenario_metadata_json, root),
        maps=[str(value) for value in args.maps],
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=[int(value) for value in args.instance_ids],
        generate_missing=True,
        base_seed=20260522,
    )
    output_jsonl = resolve(args.output_jsonl, root)
    command_log = resolve(args.command_log, root)
    update_log = resolve(args.update_log, root)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log]:
            if path.exists():
                path.unlink()
    all_rows: list[dict[str, Any]] = []
    all_commands: list[dict[str, Any]] = []
    for time_budget in [float(value) for value in args.time_limit_sec]:
        for iteration_budget in [int(value) for value in args.ltm_max_iterations]:
            rows, commands = run_combo(
                root=root,
                args=args,
                specs=specs,
                scenario_dir=scenario_dir,
                methods=methods,
                time_budget=time_budget,
                iteration_budget=iteration_budget,
            )
            rows = [*rows, *add_selector_alias_rows(rows, spec)]
            rows = [
                *rows,
                *synthesize_seeded_diagnostics(
                    rows,
                    synthetic_names=[
                        "repair5g4_random_flow_shield_diagnostic_seed0",
                        "repair5g4_shuffled_flow_shield_diagnostic_seed0",
                    ],
                    actual_candidate_methods=methods,
                ),
            ]
            all_rows.extend(rows)
            all_commands.extend(commands)
    write_jsonl(output_jsonl, all_rows)
    write_jsonl(command_log, all_commands)
    write_update_summary(update_log, all_rows)
    paired = paired_rows(all_rows, dimensions=["time_budget_sec", "ltm_iteration_budget"])
    stats = method_stats(paired)
    by_budget = grouped_rows(paired, group_fields=["time_budget_sec"])
    by_iteration = grouped_rows(paired, group_fields=["ltm_iteration_budget"])
    write_csv_rows(resolve(args.paired_csv, root), paired)
    write_csv_rows(resolve(args.summary_csv, root), list(stats.values()))
    write_csv_rows(resolve(args.by_budget_csv, root), by_budget)
    write_csv_rows(resolve(args.by_iteration_csv, root), by_iteration)
    selected_by_budget = {str(row["time_budget_sec"]): row for row in by_budget if row.get("method") == SELECTED}
    selected_by_iter = {str(row["ltm_iteration_budget"]): row for row in by_iteration if row.get("method") == SELECTED}
    gates = {
        "schema_errors": schema_error_count(all_rows),
        "solver_crash_count": sum(1 for row in all_commands if int(row.get("returncode", 0)) == 1),
        "selected_3s_negative": float(selected_by_budget.get("3.0", {}).get("mean_delta_ratio_vs_ltm") or 0.0) < 0.0,
        "selected_5s_not_reversed": float(selected_by_budget.get("5.0", {}).get("mean_delta_ratio_vs_ltm") or 0.0) <= 0.0,
        "selected_10s_not_reversed": float(selected_by_budget.get("10.0", {}).get("mean_delta_ratio_vs_ltm") or 0.0) <= 0.0,
        "selected_8_iterations_not_broad_harm": float(selected_by_iter.get("8", {}).get("mean_delta_ratio_vs_ltm") or 0.0) <= 0.0,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    gates["stress_protocol_passed"] = gates["schema_errors"] == 0 and gates["solver_crash_count"] == 0
    summary = {
        "schema_version": "phase5p5_repair5g4_time_iteration_stress_summary_v1",
        "created_at": now_iso(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "maps": [str(value) for value in args.maps],
        "agent_counts": [int(value) for value in args.agent_counts],
        "instance_ids": [int(value) for value in args.instance_ids],
        "time_limit_sec": [float(value) for value in args.time_limit_sec],
        "ltm_max_iterations": [int(value) for value in args.ltm_max_iterations],
        "row_count": len(all_rows),
        "method_stats": stats,
        "selected_by_budget": selected_by_budget,
        "selected_by_iteration": selected_by_iter,
        "gates": gates,
        "interpretation": "1s may be noisy; 3s should reproduce sign; 5s/10s should not reverse sign; 8 iterations should not introduce broad harm.",
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_method_report(resolve(args.report, root), title="Phase5.5 Repair5G.4 Time Iteration Stress Report", summary=summary)
    print(json.dumps({"stress_protocol_passed": gates["stress_protocol_passed"], "rows": len(all_rows)}))
    return 0 if gates["stress_protocol_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

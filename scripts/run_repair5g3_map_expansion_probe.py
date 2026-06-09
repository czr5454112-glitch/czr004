"""Run or skip the optional Repair5G.3 map/agent expansion diagnostic."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5f4_static_updateparams_validation as f4_validation  # noqa: E402
from repair5g3_common import (  # noqa: E402
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
)


DEFAULT_BINARY = "build/phase1a-batch/phase1a_batch.exe"
DEFAULT_SOURCE_SCENARIO_DIR = "outputs/tmp/phase1a/generated/phase1a-generated-random"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g3_map_expansion_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g3_map_expansion_scenario_generation.json"
DEFAULT_RUNTIME_ROOT = "outputs/tmp/phase5p5_repair5g3_runtimes"
DEFAULT_FROZEN_SPEC = "outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json"
DEFAULT_BROAD_SUMMARY = "outputs/reports/phase5p5_repair5g3_broader_validation_summary.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g3_map_expansion_probe"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g3_map_expansion_probe.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g3_map_expansion_probe_commands.jsonl"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g3_map_expansion_probe_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g3_map_expansion_probe_summary.json"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g3_map_expansion_probe_summary.csv"
DEFAULT_BY_GROUP = "outputs/tables/phase5p5_repair5g3_map_expansion_probe_by_map_agent.csv"

CANDIDATE_MAPS = [
    "random-64-64-20",
    "maze-32-32-2",
    "maze-64-64-2",
    "room-64-64-16",
    "warehouse-20-40-10-2-1",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--runtime-root", type=Path, default=Path(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_SPEC))
    parser.add_argument("--broader-summary-json", type=Path, default=Path(DEFAULT_BROAD_SUMMARY))
    parser.add_argument("--candidate-maps", nargs="+", default=CANDIDATE_MAPS)
    parser.add_argument("--agent-counts", nargs="+", type=int, default=[50, 100, 150, 200])
    parser.add_argument("--instance-ids", nargs="+", type=int, default=list(range(1, 21)))
    parser.add_argument("--time-limit-sec", type=float, default=3.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMANDS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--summary-csv", type=Path, default=Path(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_BY_GROUP))
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--ignore-broader-gate", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def available_maps(root: Path, names: list[str]) -> dict[str, str]:
    out = {}
    map_dir = root / "external/lacam2/scripts/map"
    for name in names:
        path = map_dir / f"{name}.map"
        if path.exists():
            out[name] = str(path.relative_to(root))
    return out


def feasible_agents(map_name: str, requested: list[int]) -> list[int]:
    if map_name.startswith("maze-32") or map_name.startswith("room-"):
        return [value for value in requested if value <= 100]
    if map_name.startswith("warehouse-20"):
        return [value for value in requested if value <= 200]
    return requested


def write_skip(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.3 Map Expansion Probe\n\n")
        handle.write("Diagnostic-only optional probe.\n\n")
        handle.write(f"Decision: `{summary['decision']}`\n\n")
        handle.write("## Availability Audit\n\n")
        for name, exists in summary["availability"].items():
            handle.write(f"- `{name}`: `{exists}`\n")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    broad = load_json(resolve(args.broader_summary_json, root))
    if (
        broad
        and not args.ignore_broader_gate
        and not broad.get("gates", {}).get("protocol_gates_passed", False)
    ):
        raise SystemExit("broader validation protocol gates failed; map expansion is blocked")
    available = available_maps(root, [str(value) for value in args.candidate_maps])
    availability = {name: name in available for name in args.candidate_maps}
    if not available:
        summary = {
            "schema_version": "phase5p5_repair5g3_map_expansion_probe_summary_v1",
            "created_at": now_iso(),
            "branch": git_value(["branch", "--show-current"], root),
            "commit": git_value(["rev-parse", "--short", "HEAD"], root),
            "decision": "skip_no_extra_maps_available",
            "availability": availability,
            "diagnostic_only": True,
            "phase5p5_allowed": False,
            "phase6_allowed": False,
        }
        write_json(resolve(args.summary_json, root), summary)
        write_skip(resolve(args.report, root), summary)
        print(json.dumps({"decision": summary["decision"]}))
        return 0

    for name, rel_path in available.items():
        f4_validation.MAPS[name] = rel_path

    spec = load_json(resolve(args.frozen_selector_spec_json, root))
    flow_methods = [
        "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
        "repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75",
    ]
    actual_methods = [
        "lacam_star_ltm",
        "always_additive_defer",
        "laur_disable",
        "laur_force_additive_direct",
        *frozen_underlying_methods(spec),
        *flow_methods,
    ]
    actual_methods = list(dict.fromkeys(actual_methods))
    specs = build_specs(actual_methods, resolve(args.runtime_root, root))
    selected_maps = list(available)
    agent_counts = sorted({agent for map_name in selected_maps for agent in feasible_agents(map_name, [int(v) for v in args.agent_counts])})
    scenario_dir = resolve(args.scenario_dir, root)
    audit_and_prepare_scenarios(
        root=root,
        source_scenario_dir=resolve(args.source_scenario_dir, root),
        scenario_dir=scenario_dir,
        scenario_metadata=resolve(args.scenario_metadata_json, root),
        maps=selected_maps,
        agent_counts=agent_counts,
        instance_ids=[int(value) for value in args.instance_ids],
        generate_missing=True,
        base_seed=20260522,
    )
    output_jsonl = resolve(args.output_jsonl, root)
    command_log = resolve(args.command_log, root)
    if args.overwrite:
        for path in [output_jsonl, command_log]:
            if path.exists():
                path.unlink()
    completed = {
        (str(row.get("map")), int(row.get("agents")), int(row.get("seed")), str(row.get("method")))
        for row in read_jsonl(output_jsonl)
    }
    if not args.skip_solver:
        run_solver_grid(
            root=root,
            binary=resolve(args.binary, root),
            scenario_dir=scenario_dir,
            output_jsonl=output_jsonl,
            command_log=command_log,
            maps=selected_maps,
            agent_counts=agent_counts,
            instance_ids=[int(value) for value in args.instance_ids],
            time_limit_sec=float(args.time_limit_sec),
            ltm_max_iterations=int(args.ltm_max_iterations),
            methods=specs,
            completed=completed,
            max_workers=int(args.max_workers),
            manifest="phase5p5-repair5g3-map-expansion-probe",
            status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
        )
    rows = [row for row in read_jsonl(output_jsonl) if str(row.get("method")) in set(actual_methods)]
    rows = [*rows, *add_selector_alias_rows(rows, spec)]
    rows = [
        *rows,
        *synthesize_seeded_diagnostics(
            rows,
            synthetic_names=[
                "repair5g3_random_flow_shield_diagnostic_seed0",
                "repair5g3_shuffled_flow_shield_diagnostic_seed0",
            ],
            actual_candidate_methods=actual_methods,
        ),
    ]
    write_jsonl(output_jsonl, rows)
    paired = paired_rows(rows)
    stats = method_stats(paired)
    by_group = grouped_rows(paired, group_fields=["map", "agents"])
    write_csv_rows(resolve(args.summary_csv, root), list(stats.values()))
    write_csv_rows(resolve(args.by_map_agent_csv, root), by_group)
    summary = {
        "schema_version": "phase5p5_repair5g3_map_expansion_probe_summary_v1",
        "created_at": now_iso(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "decision": "map_expansion_probe_complete",
        "availability": availability,
        "maps": selected_maps,
        "agent_counts": agent_counts,
        "instance_ids": [int(value) for value in args.instance_ids],
        "row_count": len(rows),
        "schema_errors": schema_error_count(rows),
        "solver_crash_count": sum(1 for row in read_jsonl(command_log) if int(row.get("returncode", 0)) == 1),
        "method_stats": stats,
        "gates": {
            "schema_errors_zero": schema_error_count(rows) == 0,
            "solver_crash_count_zero": sum(1 for row in read_jsonl(command_log) if int(row.get("returncode", 0)) == 1) == 0,
            "diagnostic_only": True,
            "phase5p5_allowed": False,
            "phase6_allowed": False,
        },
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_method_report(resolve(args.report, root), title="Phase5.5 Repair5G.3 Map Expansion Probe Report", summary=summary)
    print(json.dumps({"decision": summary["decision"], "rows": len(rows)}))
    return 0 if summary["schema_errors"] == 0 else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Run Repair5G.5 AAAI broader validation after fresh learned runtime passes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g5_common import (  # noqa: E402
    DEFAULT_BINARY,
    DEFAULT_FROZEN_G2_SPEC,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    G5_RUNTIME,
    actual_methods_for_reported,
    build_analysis_rows,
    load_json,
    method_specs,
    prepare_scenarios,
    rel,
    repo_root,
    resolve,
    run_solver_grid_g5,
    summarise_runtime_run,
    write_json,
    write_method_report,
)
from repair5g3_common import git_value, read_jsonl, write_csv_rows  # noqa: E402
from run_repair5f4_static_updateparams_validation import MAPS as MAP_PATHS  # noqa: E402


DEFAULT_FRESH = "outputs/reports/phase5p5_repair5g5_learned_runtime_fresh_eval_summary.json"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g5_aaai_broader_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g5_aaai_broader_scenario_generation.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g5_aaai_broader_validation"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g5_aaai_broader_validation.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g5_aaai_broader_validation_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g5_aaai_broader_validation_ltm_updates.jsonl"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g5_aaai_broader_validation_summary.csv"
DEFAULT_BY_GROUP = "outputs/tables/phase5p5_repair5g5_aaai_broader_validation_by_map_agent.csv"
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g5_aaai_broader_validation_paired.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g5_aaai_broader_validation_oracle_regret.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g5_aaai_broader_validation_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g5_aaai_broader_validation_summary.json"

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
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_G2_SPEC))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--fresh-summary-json", type=Path, default=Path(DEFAULT_FRESH))
    parser.add_argument("--maps", nargs="+", default=CANDIDATE_MAPS)
    parser.add_argument("--agent-counts", nargs="+", type=int, default=[25, 50, 100, 150, 200])
    parser.add_argument("--instance-ids", nargs="+", type=int, default=list(range(246, 256)))
    parser.add_argument("--time-limit-sec", type=float, default=3.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMANDS))
    parser.add_argument("--update-log", type=Path, default=Path(DEFAULT_UPDATES))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED))
    parser.add_argument("--summary-csv", type=Path, default=Path(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_BY_GROUP))
    parser.add_argument("--oracle-regret-csv", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--ignore-fresh-gate", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def available_maps(root: Path, requested: list[str]) -> tuple[list[str], list[str]]:
    available = []
    missing = []
    for name in requested:
        rel_path = MAP_PATHS.get(name)
        if rel_path and (root / rel_path).exists():
            available.append(name)
        else:
            missing.append(name)
    return available, missing


def write_report(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.5 AAAI Broader Validation\n\n")
        handle.write("Diagnostic-only broader validation / map availability audit.\n\n")
        for key in ["available_maps", "missing_maps", "agent_counts", "instance_ids", "broader_validation_run"]:
            handle.write(f"- `{key}`: `{summary.get(key)}`\n")
        handle.write("- phase5p5_allowed: `false`\n- phase6_allowed: `false`\n- aaai_ready: `false`\n")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    fresh = load_json(resolve(args.fresh_summary_json, root))
    if not args.ignore_fresh_gate and not fresh.get("gates", {}).get("fresh_gates_passed"):
        available, missing = available_maps(root, [str(value) for value in args.maps])
        summary = {
            "schema_version": "phase5p5_repair5g5_aaai_broader_validation_summary_v1",
            "available_maps": available,
            "missing_maps": missing,
            "broader_validation_run": False,
            "blocked_reason": "fresh learned runtime validation did not pass",
            "phase5p5_allowed": False,
            "phase6_allowed": False,
            "aaai_ready": False,
        }
        write_json(resolve(args.summary_json, root), summary)
        write_report(resolve(args.report, root), summary)
        write_csv_rows(resolve(args.summary_csv, root), [])
        write_csv_rows(resolve(args.by_map_agent_csv, root), [])
        write_csv_rows(resolve(args.paired_csv, root), [])
        write_csv_rows(resolve(args.oracle_regret_csv, root), [])
        print(json.dumps({"broader_validation_run": False, "blocked_reason": summary["blocked_reason"]}))
        return 0
    available, missing = available_maps(root, [str(value) for value in args.maps])
    if not available:
        summary = {
            "schema_version": "phase5p5_repair5g5_aaai_broader_validation_summary_v1",
            "available_maps": available,
            "missing_maps": missing,
            "broader_validation_run": False,
            "blocked_reason": "no candidate additional maps are available locally",
            "phase5p5_allowed": False,
            "phase6_allowed": False,
            "aaai_ready": False,
        }
        write_json(resolve(args.summary_json, root), summary)
        write_report(resolve(args.report, root), summary)
        write_csv_rows(resolve(args.summary_csv, root), [])
        write_csv_rows(resolve(args.by_map_agent_csv, root), [])
        write_csv_rows(resolve(args.paired_csv, root), [])
        write_csv_rows(resolve(args.oracle_regret_csv, root), [])
        print(json.dumps({"broader_validation_run": False, "blocked_reason": summary["blocked_reason"]}))
        return 0
    reported_methods = ["lacam_star_ltm", "repair5g2_best_frozen_static_candidate", "repair5g2_frozen_static_or_selector", G5_RUNTIME]
    frozen_spec = load_json(resolve(args.frozen_selector_spec_json, root))
    actual_methods = actual_methods_for_reported(reported_methods, frozen_spec)
    selector_spec = resolve(args.selector_spec_json, root)
    scenario_dir = resolve(args.scenario_dir, root)
    prepare_scenarios(
        root=root,
        source_scenario_dir=resolve(args.source_scenario_dir, root),
        scenario_dir=scenario_dir,
        scenario_metadata=resolve(args.scenario_metadata_json, root),
        maps=available,
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=[int(value) for value in args.instance_ids],
    )
    output_jsonl = resolve(args.output_jsonl, root)
    command_log = resolve(args.command_log, root)
    update_log = resolve(args.update_log, root)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log]:
            path.unlink(missing_ok=True)
    completed = {
        (str(row.get("map")), int(row.get("agents")), int(row.get("seed")), str(row.get("method")))
        for row in read_jsonl(output_jsonl)
    }
    if not args.skip_solver:
        run_solver_grid_g5(
            root=root,
            binary=resolve(args.binary, root),
            scenario_dir=scenario_dir,
            output_jsonl=output_jsonl,
            command_log=command_log,
            update_log=update_log,
            maps=available,
            agent_counts=[int(value) for value in args.agent_counts],
            instance_ids=[int(value) for value in args.instance_ids],
            time_limit_sec=float(args.time_limit_sec),
            ltm_max_iterations=int(args.ltm_max_iterations),
            methods=method_specs(actual_methods, selector_spec),
            completed=completed,
            max_workers=int(args.max_workers),
            manifest="phase5p5-repair5g5-aaai-broader-validation",
            status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
        )
    raw_rows = [row for row in read_jsonl(output_jsonl) if str(row.get("method")) in set(actual_methods)]
    rows = build_analysis_rows(raw_rows, frozen_spec, reported_methods)
    runtime_summary, _paired = summarise_runtime_run(
        rows=rows,
        update_rows=read_jsonl(update_log),
        commands=read_jsonl(command_log),
        maps=available,
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=[int(value) for value in args.instance_ids],
        reported_methods=reported_methods,
        paired_csv=resolve(args.paired_csv, root),
        summary_csv=resolve(args.summary_csv, root),
        by_map_agent_csv=resolve(args.by_map_agent_csv, root),
        oracle_csv=resolve(args.oracle_regret_csv, root),
    )
    summary = {
        "schema_version": "phase5p5_repair5g5_aaai_broader_validation_summary_v1",
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "available_maps": available,
        "missing_maps": missing,
        "agent_counts": [int(value) for value in args.agent_counts],
        "instance_ids": [int(value) for value in args.instance_ids],
        "methods": reported_methods,
        "broader_validation_run": True,
        "row_count": len(rows),
        "method_stats": runtime_summary["method_stats"],
        "gates": runtime_summary["gates"],
        "selector_spec": rel(selector_spec, root),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_method_report(resolve(args.report, root), title="Phase5.5 Repair5G.5 AAAI Broader Validation Report", summary=summary)
    print(json.dumps({"broader_validation_run": True, "rows": len(rows)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

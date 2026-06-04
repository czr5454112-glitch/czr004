"""Run Repair5G.5.3 runtime hook overhead ablation ladder."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from analyze_repair5g53_hook_overhead_ablation import main as analyze_main  # noqa: E402
from repair5g3_common import MethodSpec, number  # noqa: E402
from repair5g5_common import (  # noqa: E402
    AGENTS,
    DEFAULT_BINARY,
    DEFAULT_FROZEN_G2_SPEC,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    MAPS,
    actual_methods_for_reported,
    load_json,
    prepare_scenarios,
    read_jsonl,
    repo_root,
    resolve,
    run_solver_grid_g5,
)


DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g53_hook_overhead_ablation_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g53_hook_overhead_ablation_scenario_generation.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g53_hook_overhead_ablation"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g53_hook_overhead_ablation.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g53_hook_overhead_ablation_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g53_hook_overhead_ablation_ltm_updates.jsonl"
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g53_hook_overhead_ablation_paired.csv"
DEFAULT_COMPONENTS = "outputs/tables/phase5p5_repair5g53_hook_overhead_components.csv"
DEFAULT_REGRET = "outputs/tables/phase5p5_repair5g53_hook_overhead_regret_cases.csv"
DEFAULT_MISMATCHES = "outputs/tables/phase5p5_repair5g53_hook_overhead_mismatches.csv"
DEFAULT_BY_GROUP = "outputs/tables/phase5p5_repair5g53_hook_overhead_ablation_by_map_agent.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g53_hook_overhead_ablation_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g53_hook_overhead_ablation_summary.json"

REPORTED_METHODS = [
    "lacam_star_ltm",
    "repair5g2_best_frozen_static_candidate",
    "repair5g2_frozen_static_or_selector",
    "repair5g53_runtime_always_static_minimal_hook",
    "repair5g53_runtime_always_map_agent_minimal_hook",
    "repair5g53_runtime_static_shadow_noop_minimal",
    "repair5g53_static_hook_minimal",
    "repair5g53_static_hook_memory_counter",
    "repair5g53_static_hook_jsonl_log_only",
    "repair5g53_static_hook_params_hash_only",
    "repair5g53_static_hook_traffic_hash_only",
    "repair5g53_static_hook_cost_audit_only",
    "repair5g53_static_hook_features_no_cost_audit",
    "repair5g53_static_hook_full_features_no_jsonl",
    "repair5g53_static_hook_full_features_jsonl",
    "repair5g53_shadow_static_deferred_log",
    "repair5g53_shadow_static_full_log",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_G2_SPEC))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--maps", nargs="+", default=MAPS)
    parser.add_argument("--agent-counts", nargs="+", type=int, default=AGENTS)
    parser.add_argument("--instance-ids", nargs="+", type=int, default=list(range(146, 156)))
    parser.add_argument("--time-limit-sec", type=float, default=3.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMANDS))
    parser.add_argument("--update-log", type=Path, default=Path(DEFAULT_UPDATES))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED))
    parser.add_argument("--components-csv", type=Path, default=Path(DEFAULT_COMPONENTS))
    parser.add_argument("--regret-cases-csv", type=Path, default=Path(DEFAULT_REGRET))
    parser.add_argument("--mismatches-csv", type=Path, default=Path(DEFAULT_MISMATCHES))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_BY_GROUP))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def validate_instance_ids(instance_ids: list[int]) -> None:
    forbidden = [value for value in instance_ids if 166 <= int(value) <= 205]
    if forbidden:
        raise SystemExit(f"Repair5G.5.3 may not run reserved IDs 166..205: {forbidden}")


def method_specs(frozen_spec: dict[str, object], selector_spec: Path) -> list[MethodSpec]:
    base_reported = [method for method in REPORTED_METHODS if not method.startswith("repair5g53_")]
    specs = [MethodSpec(method, method) for method in actual_methods_for_reported(base_reported, frozen_spec)]
    for method in [method for method in REPORTED_METHODS if method.startswith("repair5g53_")]:
        specs.append(MethodSpec(method, method, ("--repair5g5-selector-spec", str(selector_spec))))
    by_alias: dict[str, MethodSpec] = {}
    for spec in specs:
        by_alias[spec.alias] = spec
    return list(by_alias.values())


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    validate_instance_ids([int(value) for value in args.instance_ids])
    root = repo_root()
    frozen_spec = load_json(resolve(args.frozen_selector_spec_json, root))
    selector_spec = resolve(args.selector_spec_json, root)
    scenario_dir = resolve(args.scenario_dir, root)
    prepare_scenarios(
        root=root,
        source_scenario_dir=resolve(args.source_scenario_dir, root),
        scenario_dir=scenario_dir,
        scenario_metadata=resolve(args.scenario_metadata_json, root),
        maps=[str(value) for value in args.maps],
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
        (str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)), str(row.get("method")))
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
            maps=[str(value) for value in args.maps],
            agent_counts=[int(value) for value in args.agent_counts],
            instance_ids=[int(value) for value in args.instance_ids],
            time_limit_sec=float(args.time_limit_sec),
            ltm_max_iterations=int(args.ltm_max_iterations),
            methods=method_specs(frozen_spec, selector_spec),
            completed=completed,
            max_workers=int(args.max_workers),
            manifest="phase5p5-repair5g53-hook-overhead-ablation",
            status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
        )
    return analyze_main(
        [
            "--output-jsonl",
            str(output_jsonl),
            "--command-log",
            str(command_log),
            "--update-log",
            str(update_log),
            "--frozen-selector-spec-json",
            str(resolve(args.frozen_selector_spec_json, root)),
            "--paired-csv",
            str(resolve(args.paired_csv, root)),
            "--components-csv",
            str(resolve(args.components_csv, root)),
            "--regret-cases-csv",
            str(resolve(args.regret_cases_csv, root)),
            "--mismatches-csv",
            str(resolve(args.mismatches_csv, root)),
            "--by-map-agent-csv",
            str(resolve(args.by_map_agent_csv, root)),
            "--report",
            str(resolve(args.report, root)),
            "--summary-json",
            str(resolve(args.summary_json, root)),
        ]
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

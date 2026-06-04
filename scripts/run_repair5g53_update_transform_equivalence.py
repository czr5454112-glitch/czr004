"""Run Repair5G.5.3 UpdateLTM transform-equivalence audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from analyze_repair5g53_update_transform_equivalence import main as analyze_main  # noqa: E402
from repair5g3_common import MethodSpec, number  # noqa: E402
from repair5g5_common import (  # noqa: E402
    AGENTS,
    DEFAULT_BINARY,
    DEFAULT_FROZEN_G2_SPEC,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    MAPS,
    load_json,
    prepare_scenarios,
    read_jsonl,
    repo_root,
    resolve,
    run_solver_grid_g5,
)


DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g53_update_transform_equivalence_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g53_update_transform_equivalence_scenario_generation.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g53_update_transform_equivalence"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g53_update_transform_equivalence_runs.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g53_update_transform_equivalence_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g53_update_transform_equivalence_ltm_updates.jsonl"
DEFAULT_AUDIT = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g53_update_transform_audit.jsonl"
DEFAULT_MISMATCH = "outputs/tables/phase5p5_repair5g53_update_transform_equivalence_mismatches.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g53_update_transform_equivalence_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g53_update_transform_equivalence_summary.json"


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
    parser.add_argument("--audit-jsonl", type=Path, default=Path(DEFAULT_AUDIT))
    parser.add_argument("--mismatch-csv", type=Path, default=Path(DEFAULT_MISMATCH))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def validate_instance_ids(instance_ids: list[int]) -> None:
    forbidden = [value for value in instance_ids if 166 <= int(value) <= 205]
    if forbidden:
        raise SystemExit(f"Repair5G.5.3 may not run reserved IDs 166..205: {forbidden}")


def method_specs(frozen_spec: dict[str, Any], selector_spec: Path, audit_jsonl: Path) -> list[MethodSpec]:
    static = str(
        frozen_spec.get("selected_static_candidate")
        or "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75"
    )
    common = ("--repair5g5-selector-spec", str(selector_spec), "--repair5g-transform-audit-jsonl", str(audit_jsonl))
    specs = [
        MethodSpec(
            static,
            "repair5g2_best_frozen_static_candidate",
            (*common, "--repair5g-transform-audit-candidate", static),
        ),
        MethodSpec(
            "repair5g53_runtime_always_map_agent_minimal_hook",
            "repair5g2_frozen_static_or_selector",
            (*common, "--repair5g-transform-audit-candidate", "repair5g2_frozen_static_or_selector"),
        ),
    ]
    for method, candidate in [
        ("repair5g52_runtime_always_static_exact", "repair5g2_best_frozen_static_candidate"),
        ("repair5g52_runtime_always_map_agent_exact", "repair5g2_frozen_static_or_selector"),
        ("repair5g_dual_additive_parity", "repair5g_dual_additive_parity"),
        ("repair5g_dual_c_equiv_additive", "repair5g_dual_c_equiv_additive"),
    ]:
        specs.append(MethodSpec(method, method, (*common, "--repair5g-transform-audit-candidate", candidate)))
    return specs


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
    audit_jsonl = resolve(args.audit_jsonl, root)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log, audit_jsonl]:
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
            methods=method_specs(frozen_spec, selector_spec, audit_jsonl),
            completed=completed,
            max_workers=int(args.max_workers),
            manifest="phase5p5-repair5g53-update-transform-equivalence",
            status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
        )
    return analyze_main(
        [
            "--audit-jsonl",
            str(audit_jsonl),
            "--mismatch-csv",
            str(resolve(args.mismatch_csv, root)),
            "--report",
            str(resolve(args.report, root)),
            "--summary-json",
            str(resolve(args.summary_json, root)),
        ]
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

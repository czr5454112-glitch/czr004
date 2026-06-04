"""Run Repair5G.5.2 force-additive and disable policy closure."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import parity_mismatch_rows  # noqa: E402
from repair5g3_common import MethodSpec, git_value, number, write_csv_rows  # noqa: E402
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
    write_json,
)
from repair5g51_common import analysis_rows_from_logs, summarise_g51_run, write_text  # noqa: E402


G52_FORCE = "repair5g52_runtime_force_additive_exact"
G52_DISABLE = "repair5g52_runtime_disable_exact"

DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g52_policy_closure_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g52_policy_closure_scenario_generation.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g52_policy_closure"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g52_policy_closure.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g52_policy_closure_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g52_policy_closure_ltm_updates.jsonl"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g52_policy_closure_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g52_policy_closure_summary.json"
DEFAULT_CASES = "outputs/tables/phase5p5_repair5g52_policy_closure_cases.csv"

REPORTED_METHODS = [
    "lacam_star_ltm",
    "always_additive_defer",
    "repair5f_candidate_additive_ltm",
    "laur_disable",
    "laur_force_additive_direct",
    "repair5g_dual_additive_parity",
    "repair5g_dual_c_equiv_additive",
    "repair5g5_contextual_flow_shield_selector_force_additive_parity",
    "repair5g5_contextual_flow_shield_selector_disable",
    G52_FORCE,
    G52_DISABLE,
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
    parser.add_argument("--cases-csv", type=Path, default=Path(DEFAULT_CASES))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def method_specs(root: Path, reported: list[str], frozen_spec: dict[str, Any], selector_spec: Path) -> list[MethodSpec]:
    actual = actual_methods_for_reported(reported, frozen_spec)
    specs = []
    for method in actual:
        extra: tuple[str, ...] = ()
        if method.startswith("repair5g5_contextual_flow_shield_selector_") or method.startswith("repair5g52_runtime_"):
            extra = ("--repair5g5-selector-spec", str(selector_spec))
        specs.append(MethodSpec(method, method, extra))
    return list({spec.alias: spec for spec in specs}.values())


def write_report(path: Path, summary: dict[str, Any]) -> None:
    gates = summary["gates"]
    write_text(
        path,
        "# Phase5.5 Repair5G.5.2 Policy Closure Report\n\n"
        f"- force_additive_policy_compliant: `{gates['force_additive_policy_compliant']}`\n"
        f"- disable_policy_compliant: `{gates['disable_policy_compliant']}`\n"
        f"- true_semantic_mismatch_count: `{gates['true_semantic_mismatch_count']}`\n"
        f"- decision: `{summary['decision']}`\n\n"
        "Policy closure is required before checkpoint export or counterfactual labels are used for learning.\n",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    frozen_spec = load_json(resolve(args.frozen_selector_spec_json, root))
    selector_spec = resolve(args.selector_spec_json, root)
    specs = method_specs(root, REPORTED_METHODS, frozen_spec, selector_spec)
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
            methods=specs,
            completed=completed,
            max_workers=int(args.max_workers),
            manifest="phase5p5-repair5g52-policy-closure",
            status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
        )
    rows = analysis_rows_from_logs(output_jsonl=output_jsonl, frozen_spec=frozen_spec, reported_methods=REPORTED_METHODS)
    commands = read_jsonl(command_log)
    update_rows = read_jsonl(update_log)
    summary_base, _paired = summarise_g51_run(
        rows=rows,
        update_rows=update_rows,
        commands=commands,
        maps=[str(value) for value in args.maps],
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=[int(value) for value in args.instance_ids],
        reported_methods=REPORTED_METHODS,
        selector_log_methods=["repair5g5_contextual_flow_shield_selector_force_additive_parity"],
        force_method=G52_FORCE,
        disable_method=G52_DISABLE,
        paired_csv=resolve(args.cases_csv, root).with_name("phase5p5_repair5g52_policy_closure_paired.csv"),
        summary_csv=resolve(args.cases_csv, root).with_name("phase5p5_repair5g52_policy_closure_summary.csv"),
        by_map_agent_csv=resolve(args.cases_csv, root).with_name("phase5p5_repair5g52_policy_closure_by_map_agent.csv"),
        oracle_csv=resolve(args.cases_csv, root).with_name("phase5p5_repair5g52_policy_closure_oracle_regret.csv"),
    )
    mismatch_pairs = [(G52_FORCE, "lacam_star_ltm"), (G52_DISABLE, "lacam_star_ltm")]
    mismatches = parity_mismatch_rows(rows, mismatch_pairs)
    write_csv_rows(resolve(args.cases_csv, root), mismatches)
    true_mismatches = [row for row in mismatches if row.get("classification") == "true_semantic_mismatch"]
    gates = dict(summary_base["gates"])
    gates.update(
        {
            "time_budget_equivalent_mismatches_classified": all(
                row.get("classification") in {"time_budget_sensitivity", "missing_row"} for row in mismatches
            ),
            "true_semantic_mismatch_count": len(true_mismatches),
        }
    )
    gates["policy_closure_passed"] = all(
        [
            gates["runtime_rows_full"],
            gates["missing_rows"] == 0,
            gates["schema_errors"] == 0,
            gates["solver_crash_count"] == 0,
            gates["force_additive_policy_compliant"],
            gates["disable_policy_compliant"],
            gates["true_semantic_mismatch_count"] == 0,
        ]
    )
    summary = {
        "schema_version": "phase5p5_repair5g52_policy_closure_summary_v1",
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "maps": [str(value) for value in args.maps],
        "agent_counts": [int(value) for value in args.agent_counts],
        "instance_ids": [int(value) for value in args.instance_ids],
        "methods": REPORTED_METHODS,
        "row_count": len(rows),
        "update_log_rows": len(update_rows),
        "method_stats": summary_base["method_stats"],
        "gates": gates,
        "decision": "policy_controls_passed" if gates["policy_closure_passed"] else "policy_controls_failed",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_report(resolve(args.report, root), summary)
    print(json.dumps({"decision": summary["decision"], "rows": len(rows)}))
    return 0 if gates["policy_closure_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

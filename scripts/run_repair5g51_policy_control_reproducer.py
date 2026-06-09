"""Reproduce and classify Repair5G.5.1 policy controls on observed IDs."""

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

from repair5g3_common import git_value, number  # noqa: E402
from repair5g5_common import (  # noqa: E402
    AGENTS,
    DEFAULT_BINARY,
    DEFAULT_FROZEN_G2_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    G5_DISABLE,
    G5_FORCE,
    MAPS,
    prepare_scenarios,
)
from repair5g51_common import (  # noqa: E402
    analysis_rows_from_logs,
    build_g51_method_specs,
    load_json,
    read_jsonl,
    repo_root,
    resolve,
    run_solver_grid_g5,
    summarise_g51_run,
    write_csv_rows,
    write_gate_audit,
    write_json,
    write_report_with_stats,
)


DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g51_policy_control_reproducer_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g51_policy_control_reproducer_scenario_generation.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g51_policy_control_reproducer"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g51_policy_control_reproducer.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g51_policy_control_reproducer_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g51_policy_control_reproducer_ltm_updates.jsonl"
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g51_policy_control_reproducer_paired.csv"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g51_policy_control_reproducer_summary.csv"
DEFAULT_BY_GROUP = "outputs/tables/phase5p5_repair5g51_policy_control_reproducer_by_map_agent.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g51_policy_control_reproducer_oracle_regret.csv"
DEFAULT_CASES = "outputs/tables/phase5p5_repair5g51_policy_control_reproducer_cases.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g51_policy_control_reproducer_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g51_policy_control_reproducer_summary.json"
DEFAULT_AUDIT = "outputs/reports/phase5p5_repair5g51_policy_control_reproducer_audit.md"

REPORTED_METHODS = [
    "lacam_star_ltm",
    "always_additive_defer",
    "repair5f_candidate_additive_ltm",
    "laur_disable",
    "laur_force_additive_direct",
    "repair5g_dual_additive_parity",
    "repair5g_dual_c_equiv_additive",
    G5_FORCE,
    G5_DISABLE,
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_G2_SPEC))
    parser.add_argument("--maps", nargs="+", default=MAPS)
    parser.add_argument("--agent-counts", nargs="+", type=int, default=AGENTS)
    parser.add_argument("--instance-ids", nargs="+", type=int, default=list(range(136, 146)))
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
    parser.add_argument("--cases-csv", type=Path, default=Path(DEFAULT_CASES))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--audit-report", type=Path, default=Path(DEFAULT_AUDIT))
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def _policy_case_rows(paired: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in paired:
        method = str(row.get("candidate_id"))
        if method not in {G5_FORCE, G5_DISABLE}:
            continue
        equal = str(row.get("equal_vs_ltm")).lower() == "true"
        worse = str(row.get("worse_vs_ltm")).lower() == "true"
        item = dict(row)
        item["strict_equal_to_ltm"] = equal and not worse
        item["g51_policy_classification"] = (
            "strict_equal" if equal and not worse else "semantic_policy_equivalent_time_budget_sensitive"
        )
        out.append(item)
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    frozen_spec = load_json(resolve(args.frozen_selector_spec_json, root))
    specs = build_g51_method_specs(root=root, reported_methods=REPORTED_METHODS, frozen_spec=frozen_spec)
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
            manifest="phase5p5-repair5g51-policy-control-reproducer",
            status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
        )
    rows = analysis_rows_from_logs(
        output_jsonl=output_jsonl,
        frozen_spec=frozen_spec,
        reported_methods=REPORTED_METHODS,
    )
    commands = read_jsonl(command_log)
    update_rows = read_jsonl(update_log)
    runtime_summary, paired = summarise_g51_run(
        rows=rows,
        update_rows=update_rows,
        commands=commands,
        maps=[str(value) for value in args.maps],
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=[int(value) for value in args.instance_ids],
        reported_methods=REPORTED_METHODS,
        selector_log_methods=[G5_FORCE],
        force_method=G5_FORCE,
        disable_method=G5_DISABLE,
        paired_csv=resolve(args.paired_csv, root),
        summary_csv=resolve(args.summary_csv, root),
        by_map_agent_csv=resolve(args.by_map_agent_csv, root),
        oracle_csv=resolve(args.oracle_regret_csv, root),
    )
    cases = _policy_case_rows(paired)
    write_csv_rows(resolve(args.cases_csv, root), cases)
    gates = dict(runtime_summary["gates"])
    gates["policy_control_reproducer_passed"] = all(
        [
            gates["runtime_rows_full"],
            gates["missing_rows"] == 0,
            gates["schema_errors"] == 0,
            gates["solver_crash_count"] == 0,
            gates["semantic_parity_mismatch_count"] == 0,
            gates["force_additive_policy_compliant"],
            gates["disable_policy_compliant"],
        ]
    )
    summary = {
        "schema_version": "phase5p5_repair5g51_policy_control_reproducer_summary_v1",
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "maps": [str(value) for value in args.maps],
        "agent_counts": [int(value) for value in args.agent_counts],
        "instance_ids": [int(value) for value in args.instance_ids],
        "time_limit_sec": float(args.time_limit_sec),
        "ltm_max_iterations": int(args.ltm_max_iterations),
        "methods": REPORTED_METHODS,
        "row_count": len(rows),
        "update_log_rows": len(update_rows),
        "method_stats": runtime_summary["method_stats"],
        "gates": gates,
        "decision": "policy_controls_passed" if gates["policy_control_reproducer_passed"] else "policy_control_bug_blocks_learning",
        "cases_csv": str(resolve(args.cases_csv, root)),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_report_with_stats(resolve(args.report, root), "Phase5.5 Repair5G.5.1 Policy Control Reproducer Report", summary)
    write_gate_audit(resolve(args.audit_report, root), "Phase5.5 Repair5G.5.1 Policy Control Reproducer Audit", summary)
    print(json.dumps({"policy_control_reproducer_passed": gates["policy_control_reproducer_passed"], "rows": len(rows)}))
    return 0 if gates["policy_control_reproducer_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

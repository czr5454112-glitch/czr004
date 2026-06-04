"""Run the Repair5G.5.4 budget-robust runtime diagnostic protocol."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import MethodSpec, number, read_jsonl  # noqa: E402
from repair5g5_common import DEFAULT_BINARY, DEFAULT_SELECTOR_SPEC, DEFAULT_SOURCE_SCENARIO_DIR, prepare_scenarios, repo_root, resolve, run_solver_grid_g5  # noqa: E402
from repair5g54_common import parse_instance_id_tokens, validate_observed_instance_ids, write_json, write_text  # noqa: E402


DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g54_budget_protocol_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g54_budget_protocol_scenario_generation.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g54_budget_protocol"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g54_budget_protocol_runs.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g54_budget_protocol_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g54_budget_protocol_ltm_updates.jsonl"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g54_budget_robust_runtime_protocol.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g54_budget_robust_runtime_run_summary.json"


BASE_METHODS = [
    ("repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75", "fixed_static"),
    ("repair5g_dual_c_equiv_additive", "fixed_map_agent"),
    ("repair5g53_runtime_always_static_minimal_hook", "minimal_hook_static"),
    ("repair5g53_runtime_always_map_agent_minimal_hook", "minimal_hook_map_agent"),
    ("repair5g5_contextual_flow_shield_selector_runtime", "selector_perf"),
    ("repair5g5_contextual_flow_shield_selector_runtime", "selector_audit"),
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--maps", nargs="+", default=["warehouse-10-20-10-2-1"])
    parser.add_argument("--agent-counts", nargs="+", type=int, default=[100])
    parser.add_argument("--instance-ids", nargs="+", default=["146"])
    parser.add_argument("--budgets-sec", nargs="+", type=float, default=[3.0, 5.0, 10.0])
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMANDS))
    parser.add_argument("--update-log", type=Path, default=Path(DEFAULT_UPDATES))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def budget_token(budget: float) -> str:
    return ("%g" % float(budget)).replace(".", "p")


def method_specs(selector_spec: Path, budget: float) -> list[MethodSpec]:
    token = budget_token(budget)
    specs: list[MethodSpec] = []
    for method, label in BASE_METHODS:
        extra: tuple[str, ...] = ()
        if label in {"selector_perf", "selector_audit"}:
            mode = "perf" if label == "selector_perf" else "audit"
            extra = ("--repair5g5-selector-spec", str(selector_spec), "--repair5g-runtime-audit-mode", mode)
        elif method.startswith("repair5g53_"):
            extra = ("--repair5g5-selector-spec", str(selector_spec), "--repair5g-runtime-audit-mode", "perf")
        specs.append(MethodSpec(method, f"repair5g54_{label}_{token}s", extra))
    return specs


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    instance_ids = validate_observed_instance_ids(parse_instance_id_tokens(args.instance_ids))
    root = repo_root()
    scenario_dir = resolve(args.scenario_dir, root)
    prepare_scenarios(
        root=root,
        source_scenario_dir=resolve(args.source_scenario_dir, root),
        scenario_dir=scenario_dir,
        scenario_metadata=resolve(args.scenario_metadata_json, root),
        maps=[str(value) for value in args.maps],
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=instance_ids,
    )
    output_jsonl = resolve(args.output_jsonl, root)
    command_log = resolve(args.command_log, root)
    update_log = resolve(args.update_log, root)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log]:
            path.unlink(missing_ok=True)
    if not args.skip_solver:
        for budget in [float(value) for value in args.budgets_sec]:
            completed = {
                (str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)), str(row.get("method")))
                for row in read_jsonl(output_jsonl)
            }
            run_solver_grid_g5(
                root=root,
                binary=resolve(args.binary, root),
                scenario_dir=scenario_dir,
                output_jsonl=output_jsonl,
                command_log=command_log,
                update_log=update_log,
                maps=[str(value) for value in args.maps],
                agent_counts=[int(value) for value in args.agent_counts],
                instance_ids=instance_ids,
                time_limit_sec=budget,
                ltm_max_iterations=int(args.ltm_max_iterations),
                methods=method_specs(resolve(args.selector_spec_json, root), budget),
                completed=completed,
                max_workers=int(args.max_workers),
                manifest="phase5p5-repair5g54-budget-runtime-protocol",
                status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
            )
    rows = read_jsonl(output_jsonl)
    summary = {
        "schema_version": "phase5p5_repair5g54_budget_robust_runtime_run_summary_v1",
        "row_count": len(rows),
        "output_jsonl": str(output_jsonl),
        "budgets_sec": [float(value) for value in args.budgets_sec],
        "maps": [str(value) for value in args.maps],
        "agent_counts": [int(value) for value in args.agent_counts],
        "instance_ids": instance_ids,
        "observed_ids_only": all(int(row.get("seed", 0)) <= 165 for row in rows),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.4 Budget-Robust Runtime Protocol\n\n"
        "This protocol reports performance mode and audit mode separately. It is diagnostic-only and not a G6 learned-runtime claim.\n\n"
        f"- row_count: `{len(rows)}`\n"
        f"- budgets_sec: `{summary['budgets_sec']}`\n"
        f"- observed_ids_only: `{summary['observed_ids_only']}`\n"
        "- 3s is the primary stress budget; 5s/10s distinguish robustness from deadline flips.\n",
    )
    print(json.dumps({"budget_protocol_rows": len(rows), "observed_ids_only": summary["observed_ids_only"]}))
    return 0 if rows else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

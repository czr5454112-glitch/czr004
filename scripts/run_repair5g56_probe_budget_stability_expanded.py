"""Run Repair5G.5.6 expanded probe-budget stability diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import MethodSpec, number  # noqa: E402
from repair5g5_common import DEFAULT_BINARY, DEFAULT_SELECTOR_SPEC, DEFAULT_SOURCE_SCENARIO_DIR, prepare_scenarios, run_solver_grid_g5  # noqa: E402
from repair5g55_common import G55_STATIC_CONTEXT_METHOD, candidate_list_from_csv, default_candidate_list, read_jsonl  # noqa: E402
from repair5g56_common import G56_AGENT_COUNTS, G56_MAPS, group_by_context, repo_root, resolve, validate_g55_instance_ids, validate_observed_rows, write_json, write_text  # noqa: E402


DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g56_probe_budget_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g56_probe_budget_scenario_generation.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g56_probe_budget_stability"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g56_probe_budget_runs.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g56_probe_budget_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g56_probe_budget_ltm_updates.jsonl"
DEFAULT_PROBES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g56_probe_budget_update_probes.jsonl"
DEFAULT_CANDIDATES = "outputs/tables/phase5p5_repair5g55_candidate_set.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g56_probe_budget_stability_run.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g56_probe_budget_stability_run_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--candidate-set-csv", type=Path, default=Path(DEFAULT_CANDIDATES))
    parser.add_argument("--maps", nargs="+", default=G56_MAPS)
    parser.add_argument("--agent-counts", nargs="+", type=int, default=G56_AGENT_COUNTS)
    parser.add_argument("--instance-ids", nargs="+", default=["146..150"])
    parser.add_argument("--budgets-ms", nargs="+", type=float, default=[250.0, 500.0, 1000.0, 2000.0])
    parser.add_argument("--time-limit-sec", type=float, default=5.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-contexts-per-group", type=int, default=1)
    parser.add_argument("--counterfactual-candidates", default="")
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMANDS))
    parser.add_argument("--update-log", type=Path, default=Path(DEFAULT_UPDATES))
    parser.add_argument("--probe-jsonl", type=Path, default=Path(DEFAULT_PROBES))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def budget_alias(budget_ms: float) -> str:
    return f"repair5g56_budget_{int(round(budget_ms))}ms_static_context"


def method_specs(selector_spec: Path, probe_jsonl: Path, args: argparse.Namespace, candidates: list[str]) -> list[MethodSpec]:
    specs = []
    for budget in args.budgets_ms:
        extra = (
            "--repair5g5-selector-spec",
            str(selector_spec),
            "--repair5g-counterfactual-update-probe-jsonl",
            str(probe_jsonl),
            "--repair5g-counterfactual-candidates",
            ",".join(candidates),
            "--repair5g-counterfactual-short-budget-ms",
            str(float(budget)),
            "--repair5g-counterfactual-max-contexts",
            str(int(args.max_contexts_per_group)),
            "--repair5g-checkpoint-topk-edges",
            "0",
            "--repair5g-runtime-audit-mode",
            "perf",
        )
        specs.append(MethodSpec(G55_STATIC_CONTEXT_METHOD, budget_alias(float(budget)), extra))
    return specs


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    instance_ids = validate_g55_instance_ids(args.instance_ids, label="Repair5G.5.6 expanded budget stability")
    maps = [str(value) for value in args.maps]
    agent_counts = [int(value) for value in args.agent_counts]
    candidates = (
        [token for token in str(args.counterfactual_candidates).split(",") if token]
        if args.counterfactual_candidates
        else candidate_list_from_csv(resolve(args.candidate_set_csv, root), default=default_candidate_list(False))
    )
    scenario_dir = resolve(args.scenario_dir, root)
    prepare_scenarios(
        root=root,
        source_scenario_dir=resolve(args.source_scenario_dir, root),
        scenario_dir=scenario_dir,
        scenario_metadata=resolve(args.scenario_metadata_json, root),
        maps=maps,
        agent_counts=agent_counts,
        instance_ids=instance_ids,
    )
    output_jsonl = resolve(args.output_jsonl, root)
    command_log = resolve(args.command_log, root)
    update_log = resolve(args.update_log, root)
    probe_jsonl = resolve(args.probe_jsonl, root)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log, probe_jsonl]:
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
            maps=maps,
            agent_counts=agent_counts,
            instance_ids=instance_ids,
            time_limit_sec=float(args.time_limit_sec),
            ltm_max_iterations=int(args.ltm_max_iterations),
            methods=method_specs(resolve(args.selector_spec_json, root), probe_jsonl, args, candidates),
            completed=completed,
            max_workers=int(args.max_workers),
            manifest="phase5p5-repair5g56-probe-budget-stability-expanded",
            status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
        )
    rows = read_jsonl(probe_jsonl)
    observed_only = validate_observed_rows(rows, label="Repair5G.5.6 expanded budget probes")
    summary = {
        "schema_version": "phase5p5_repair5g56_probe_budget_stability_run_summary_v1",
        "maps": maps,
        "agent_counts": agent_counts,
        "instance_ids": instance_ids,
        "budgets_ms": [float(value) for value in args.budgets_ms],
        "candidate_count": len(candidates),
        "probe_rows": len(rows),
        "raw_context_count": len(group_by_context(rows)),
        "observed_ids_only": observed_only,
        "ids_166_205_untouched": observed_only,
        "probe_jsonl": str(probe_jsonl),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.6 Probe Budget Stability Run\n\n"
        f"- budgets_ms: `{summary['budgets_ms']}`\n"
        f"- maps: `{maps}`\n"
        f"- agent_counts: `{agent_counts}`\n"
        f"- instance_ids: `{instance_ids}`\n"
        f"- probe_rows: `{len(rows)}`\n"
        f"- observed_ids_only: `{observed_only}`\n\n"
        "Budget probes separate stable labels from diagnostic-only unstable labels.\n",
    )
    print(json.dumps({"probe_rows": len(rows), "budgets_ms": summary["budgets_ms"]}))
    return 0 if observed_only and rows else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Run Repair5G.5.6 observed-ID counterfactual label completion."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import MethodSpec, number  # noqa: E402
from repair5g5_common import (  # noqa: E402
    DEFAULT_BINARY,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    prepare_scenarios,
    run_solver_grid_g5,
)
from repair5g55_common import (  # noqa: E402
    G55_CONTEXT_ALIAS,
    G55_STATIC_CONTEXT_METHOD,
    candidate_list_from_csv,
    default_candidate_list,
    read_jsonl,
)
from repair5g56_common import (  # noqa: E402
    G56_AGENT_COUNTS,
    G56_DEFAULT_INSTANCE_IDS,
    G56_MAPS,
    group_by_context,
    repo_root,
    resolve,
    validate_g55_instance_ids,
    validate_observed_rows,
    write_json,
    write_text,
)


DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g56_label_completion_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g56_label_completion_scenario_generation.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g56_counterfactual_label_completion"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g56_counterfactual_runs.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g56_counterfactual_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g56_counterfactual_ltm_updates.jsonl"
DEFAULT_PROBES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g56_counterfactual_update_probes.jsonl"
DEFAULT_CHECKPOINTS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g56_update_checkpoints.jsonl"
DEFAULT_CANDIDATES = "outputs/tables/phase5p5_repair5g55_candidate_set.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g56_counterfactual_label_completion_run.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g56_counterfactual_label_completion_run_summary.json"


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
    parser.add_argument("--instance-ids", nargs="+", default=[f"{G56_DEFAULT_INSTANCE_IDS[0]}..{G56_DEFAULT_INSTANCE_IDS[-1]}"])
    parser.add_argument("--time-limit-sec", type=float, default=5.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--short-budget-ms", type=float, default=1000.0)
    parser.add_argument("--max-contexts-per-group", type=int, default=2)
    parser.add_argument("--counterfactual-candidates", default="")
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMANDS))
    parser.add_argument("--update-log", type=Path, default=Path(DEFAULT_UPDATES))
    parser.add_argument("--probe-jsonl", type=Path, default=Path(DEFAULT_PROBES))
    parser.add_argument("--checkpoint-jsonl", type=Path, default=Path(DEFAULT_CHECKPOINTS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def method_specs(selector_spec: Path, probe_jsonl: Path, checkpoint_jsonl: Path, args: argparse.Namespace, candidates: list[str]) -> list[MethodSpec]:
    alias = "repair5g56_counterfactual_static_context"
    extra = (
        "--repair5g5-selector-spec",
        str(selector_spec),
        "--repair5g-export-update-checkpoints-jsonl",
        str(checkpoint_jsonl),
        "--repair5g-checkpoint-topk-edges",
        "0",
        "--repair5g-checkpoint-edge-filter",
        "nonzero",
        "--repair5g-checkpoint-include-full-traffic",
        "true",
        "--repair5g-counterfactual-update-probe-jsonl",
        str(probe_jsonl),
        "--repair5g-counterfactual-candidates",
        ",".join(candidates),
        "--repair5g-counterfactual-short-budget-ms",
        str(float(args.short_budget_ms)),
        "--repair5g-counterfactual-max-contexts",
        str(int(args.max_contexts_per_group)),
        "--repair5g-runtime-audit-mode",
        "perf",
    )
    return [MethodSpec(G55_STATIC_CONTEXT_METHOD, alias, extra)]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    instance_ids = validate_g55_instance_ids(args.instance_ids, label="Repair5G.5.6 label completion")
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
    checkpoint_jsonl = resolve(args.checkpoint_jsonl, root)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log, probe_jsonl, checkpoint_jsonl]:
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
            methods=method_specs(resolve(args.selector_spec_json, root), probe_jsonl, checkpoint_jsonl, args, candidates),
            completed=completed,
            max_workers=int(args.max_workers),
            manifest="phase5p5-repair5g56-counterfactual-label-completion",
            status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
        )

    probe_rows = read_jsonl(probe_jsonl)
    checkpoint_rows = read_jsonl(checkpoint_jsonl)
    observed_only = validate_observed_rows(probe_rows, label="Repair5G.5.6 probe rows")
    summary = {
        "schema_version": "phase5p5_repair5g56_counterfactual_label_completion_run_summary_v1",
        "maps": maps,
        "agent_counts": agent_counts,
        "instance_ids": instance_ids,
        "time_limit_sec": float(args.time_limit_sec),
        "ltm_max_iterations": int(args.ltm_max_iterations),
        "short_budget_ms": float(args.short_budget_ms),
        "max_contexts_per_group": int(args.max_contexts_per_group),
        "candidate_count": len(candidates),
        "candidate_ids": candidates,
        "probe_rows": len(probe_rows),
        "checkpoint_rows": len(checkpoint_rows),
        "context_count": len(group_by_context(probe_rows)),
        "observed_ids_only": observed_only,
        "ids_166_205_untouched": observed_only,
        "probe_jsonl": str(probe_jsonl),
        "checkpoint_jsonl": str(checkpoint_jsonl),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.6 Counterfactual Label Completion Run\n\n"
        f"- maps: `{maps}`\n"
        f"- agent_counts: `{agent_counts}`\n"
        f"- instance_ids: `{instance_ids}`\n"
        f"- max_contexts_per_group: `{int(args.max_contexts_per_group)}`\n"
        f"- context_count: `{summary['context_count']}`\n"
        f"- probe_rows: `{len(probe_rows)}`\n"
        f"- checkpoint_rows: `{len(checkpoint_rows)}`\n"
        f"- observed_ids_only: `{observed_only}`\n\n"
        "This run only collects observed-ID diagnostic labels. It does not train G6 or authorize runtime claims.\n",
    )
    print(json.dumps({"context_count": summary["context_count"], "probe_rows": len(probe_rows), "checkpoint_rows": len(checkpoint_rows)}))
    return 0 if observed_only and len(probe_rows) > 0 else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

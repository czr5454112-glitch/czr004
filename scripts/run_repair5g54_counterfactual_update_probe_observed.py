"""Run in-memory Repair5G.5.4 counterfactual UpdateLTM probes on observed IDs."""

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
from repair5g54_common import G54_CANDIDATES, boolish, load_json, parse_instance_id_tokens, validate_observed_instance_ids, write_json, write_text  # noqa: E402


DEFAULT_REPLAY_SUMMARY = "outputs/reports/phase5p5_repair5g54_checkpoint_replayability_summary.json"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g54_counterfactual_probe_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g54_counterfactual_probe_scenario_generation.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g54_counterfactual_probe"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g54_counterfactual_probe_runs.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g54_counterfactual_probe_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g54_counterfactual_probe_ltm_updates.jsonl"
DEFAULT_PROBES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g54_counterfactual_update_probes.jsonl"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g54_counterfactual_probe_run_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g54_counterfactual_probe_run_summary.json"
FROZEN_STATIC_CONTEXT_METHOD = "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--replayability-summary-json", type=Path, default=Path(DEFAULT_REPLAY_SUMMARY))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--maps", nargs="+", default=["random-32-32-20"])
    parser.add_argument("--agent-counts", nargs="+", type=int, default=[50])
    parser.add_argument("--instance-ids", nargs="+", default=["146"])
    parser.add_argument("--time-limit-sec", type=float, default=5.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--counterfactual-short-budget-ms", type=float, default=500.0)
    parser.add_argument("--counterfactual-max-contexts", type=int, default=2)
    parser.add_argument("--counterfactual-candidates", default=",".join(G54_CANDIDATES))
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


def method_specs(selector_spec: Path, probe_jsonl: Path, args: argparse.Namespace) -> list[MethodSpec]:
    extra = (
        "--repair5g5-selector-spec",
        str(selector_spec),
        "--repair5g-counterfactual-update-probe-jsonl",
        str(probe_jsonl),
        "--repair5g-counterfactual-candidates",
        str(args.counterfactual_candidates),
        "--repair5g-counterfactual-short-budget-ms",
        str(float(args.counterfactual_short_budget_ms)),
        "--repair5g-counterfactual-max-contexts",
        str(int(args.counterfactual_max_contexts)),
        "--repair5g-checkpoint-topk-edges",
        "0",
        "--repair5g-runtime-audit-mode",
        "perf",
    )
    return [MethodSpec(FROZEN_STATIC_CONTEXT_METHOD, "repair5g54_counterfactual_static_context", extra)]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    instance_ids = validate_observed_instance_ids(parse_instance_id_tokens(args.instance_ids))
    root = repo_root()
    replay_summary = load_json(resolve(args.replayability_summary_json, root))
    replay_ok = bool(replay_summary.get("gates", {}).get("checkpoint_replayability_passed"))
    probe_jsonl = resolve(args.probe_jsonl, root)
    if not replay_ok:
        reason = str(replay_summary.get("decision") or replay_summary.get("blocked_reason") or "checkpoint_replayability_not_passed")
        summary = {
            "schema_version": "phase5p5_repair5g54_counterfactual_probe_run_summary_v1",
            "probe_rows": 0,
            "counterfactual_probe_run_passed": False,
            "blocked_reason": reason,
            "phase5p5_allowed": False,
            "phase6_allowed": False,
            "aaai_ready": False,
        }
        write_json(resolve(args.summary_json, root), summary)
        write_text(resolve(args.report, root), f"# Phase5.5 Repair5G.5.4 Counterfactual Probe Run\n\nBlocked: `{reason}`.\n")
        print(json.dumps({"counterfactual_probe_run_passed": False, "blocked_reason": reason}))
        return 2

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
            maps=[str(value) for value in args.maps],
            agent_counts=[int(value) for value in args.agent_counts],
            instance_ids=instance_ids,
            time_limit_sec=float(args.time_limit_sec),
            ltm_max_iterations=int(args.ltm_max_iterations),
            methods=method_specs(resolve(args.selector_spec_json, root), probe_jsonl, args),
            completed=completed,
            max_workers=int(args.max_workers),
            manifest="phase5p5-repair5g54-counterfactual-probe",
            status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
        )
    probe_rows = read_jsonl(probe_jsonl)
    contexts = {str(row.get("context_id", "")) for row in probe_rows if row.get("context_id")}
    candidate_set = set(filter(None, str(args.counterfactual_candidates).split(",")))
    coverage = {
        context: {str(row.get("candidate_id")) for row in probe_rows if str(row.get("context_id")) == context}
        for context in contexts
    }
    candidate_coverage_complete = bool(contexts) and all(candidate_set <= seen for seen in coverage.values())
    all_observed = all(int(row.get("seed", 0)) <= 165 for row in probe_rows)
    labels_available = any(boolish(row.get("probe_solution_found")) or boolish(row.get("probe_feasible")) for row in probe_rows)
    summary = {
        "schema_version": "phase5p5_repair5g54_counterfactual_probe_run_summary_v1",
        "probe_rows": len(probe_rows),
        "context_count": len(contexts),
        "probe_jsonl": str(probe_jsonl),
        "candidate_count": len(candidate_set),
        "candidate_coverage_complete": candidate_coverage_complete,
        "labels_available": labels_available,
        "observed_ids_only": all_observed,
        "ids_166_205_untouched": all_observed,
        "counterfactual_probe_run_passed": len(probe_rows) > 0 and candidate_coverage_complete and all_observed,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.4 Counterfactual Probe Run\n\n"
        f"- probe_rows: `{len(probe_rows)}`\n"
        f"- context_count: `{len(contexts)}`\n"
        f"- candidate_coverage_complete: `{candidate_coverage_complete}`\n"
        f"- observed_ids_only: `{all_observed}`\n"
        f"- probe_jsonl: `{probe_jsonl}`\n",
    )
    print(json.dumps({"counterfactual_probe_run_passed": summary["counterfactual_probe_run_passed"], "probe_rows": len(probe_rows)}))
    return 0 if summary["counterfactual_probe_run_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

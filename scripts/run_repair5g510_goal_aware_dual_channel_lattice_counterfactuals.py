"""Run executable Repair5G.5.10 G5.9 lattice counterfactual probes."""

from __future__ import annotations

import argparse
import json
import math
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
from repair5g510_common import (  # noqa: E402
    G510_DEFAULT_BUDGETS_MS,
    G510_REFERENCE_ADDITIVE,
    G510_REFERENCE_STATIC,
    G510_STATIC_CANDIDATE,
    G59_CLOSED_STATUS,
    boolish,
    candidate_scores_by_context_budget,
    context_key,
    lattice_candidate_ids,
    read_csv_rows,
    read_jsonl,
    repo_root,
    resolve,
    validate_instance_tokens,
    write_csv_from_jsonl,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_CONTEXTS = "outputs/tables/phase5p5_repair5g58_primary_pair_confidence_by_context.csv"
DEFAULT_CANDIDATES = "outputs/tables/phase5p5_repair5g59_candidate_lattice.csv"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g510_lattice_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g510_lattice_scenario_generation.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g510_lattice_counterfactuals"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g510_lattice_runs.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g510_lattice_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g510_lattice_ltm_updates.jsonl"
DEFAULT_PROBES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g510_lattice_update_probes.jsonl"
DEFAULT_CHECKPOINTS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g510_update_checkpoints.jsonl"
DEFAULT_PLAN = "outputs/tables/phase5p5_repair5g510_lattice_counterfactual_plan.csv"
DEFAULT_RESULTS = "outputs/tables/phase5p5_repair5g510_lattice_counterfactual_results.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g510_lattice_counterfactual_run.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g510_lattice_counterfactual_run_summary.json"
STATIC_CONTEXT_METHOD = "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--contexts-csv", type=Path, default=Path(DEFAULT_CONTEXTS))
    parser.add_argument("--candidate-csv", type=Path, default=Path(DEFAULT_CANDIDATES))
    parser.add_argument("--maps", nargs="+", default=["random-32-32-20", "maze-32-32-4", "warehouse-10-20-10-2-1"])
    parser.add_argument("--agent-counts", nargs="+", type=int, default=[50, 100])
    parser.add_argument("--instance-ids", nargs="+", default=["146..155"])
    parser.add_argument("--budgets-ms", nargs="+", type=float, default=G510_DEFAULT_BUDGETS_MS)
    parser.add_argument("--time-limit-sec", type=float, default=5.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-contexts-per-group", type=int, default=1)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--include-parity-reference-candidates", action="store_true")
    parser.add_argument("--checkpoint-topk-edges", type=int, default=64)
    parser.add_argument("--include-full-traffic", action="store_true")
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMANDS))
    parser.add_argument("--update-log", type=Path, default=Path(DEFAULT_UPDATES))
    parser.add_argument("--probe-jsonl", type=Path, default=Path(DEFAULT_PROBES))
    parser.add_argument("--checkpoint-jsonl", type=Path, default=Path(DEFAULT_CHECKPOINTS))
    parser.add_argument("--plan-csv", type=Path, default=Path(DEFAULT_PLAN))
    parser.add_argument("--results-csv", type=Path, default=Path(DEFAULT_RESULTS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def candidate_list(candidate_csv: Path, *, include_reference: bool) -> list[str]:
    candidates = lattice_candidate_ids(candidate_csv)
    if include_reference:
        candidates = [G510_REFERENCE_ADDITIVE, G510_REFERENCE_STATIC, *candidates]
    return list(dict.fromkeys(candidates))


def method_specs(
    selector_spec: Path,
    probe_jsonl: Path,
    checkpoint_jsonl: Path,
    args: argparse.Namespace,
    candidates: list[str],
) -> list[MethodSpec]:
    specs = []
    for budget in args.budgets_ms:
        extra = (
            "--repair5g5-selector-spec",
            str(selector_spec),
            "--repair5g-export-update-checkpoints-jsonl",
            str(checkpoint_jsonl),
            "--repair5g-checkpoint-topk-edges",
            str(int(args.checkpoint_topk_edges)),
            "--repair5g-checkpoint-edge-filter",
            "nonzero",
            "--repair5g-checkpoint-include-full-traffic",
            "true" if args.include_full_traffic else "false",
            "--repair5g-counterfactual-update-probe-jsonl",
            str(probe_jsonl),
            "--repair5g-counterfactual-candidates",
            ",".join(candidates),
            "--repair5g-counterfactual-short-budget-ms",
            str(float(budget)),
            "--repair5g-counterfactual-max-contexts",
            str(int(args.max_contexts_per_group)),
            "--repair5g-runtime-audit-mode",
            "perf",
        )
        specs.append(
            MethodSpec(
                STATIC_CONTEXT_METHOD,
                f"repair5g510_budget_{int(round(float(budget)))}ms_static_context",
                extra,
            )
        )
    return specs


def planned_rows(
    contexts_csv: Path,
    candidates: list[str],
    budgets: list[float],
    maps: set[str],
    agents: set[int],
    seeds: set[int],
) -> list[dict[str, object]]:
    rows = []
    for context in read_csv_rows(contexts_csv):
        seed = int(number(context.get("seed"), -1))
        agent_count = int(number(context.get("agents"), -1))
        if str(context.get("map", "")) not in maps or agent_count not in agents or seed not in seeds:
            continue
        for candidate in candidates:
            for budget in budgets:
                rows.append(
                    {
                        "normalized_context_key": context.get("normalized_context_key", ""),
                        "context_id": context.get("context_id", ""),
                        "map": context.get("map", ""),
                        "agents": context.get("agents", ""),
                        "seed": context.get("seed", ""),
                        "iteration": context.get("iteration", ""),
                        "traffic_before_hash_full": context.get("traffic_before_hash_full", ""),
                        "candidate_id": candidate,
                        "short_budget_ms": int(round(float(budget))),
                        "observed_ids_only": True,
                    }
                )
    return rows


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    instance_ids = validate_instance_tokens(args.instance_ids, label="Repair5G.5.10 lattice counterfactuals")
    maps = [str(value) for value in args.maps]
    agent_counts = [int(value) for value in args.agent_counts]
    budgets = [float(value) for value in args.budgets_ms]
    candidates = candidate_list(resolve(args.candidate_csv, root), include_reference=args.include_parity_reference_candidates)
    lattice_ids = set(lattice_candidate_ids(resolve(args.candidate_csv, root)))

    plan = planned_rows(
        resolve(args.contexts_csv, root),
        [candidate for candidate in candidates if candidate in lattice_ids],
        budgets,
        set(maps),
        set(agent_counts),
        set(instance_ids),
    )
    write_csv_rows(resolve(args.plan_csv, root), plan)

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
            manifest="phase5p5-repair5g510-executable-lattice-counterfactuals",
            status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
        )

    probe_rows = read_jsonl(probe_jsonl)
    write_csv_from_jsonl(resolve(args.results_csv, root), probe_rows)
    checkpoint_rows = read_jsonl(checkpoint_jsonl)
    observed_only = True
    try:
        validate_instance_tokens([int(number(row.get("seed"), 0)) for row in probe_rows], label="Repair5G.5.10 probe rows")
    except SystemExit:
        observed_only = False
    lattice_probe_rows = [row for row in probe_rows if str(row.get("candidate_id", "")) in lattice_ids]
    grouped = candidate_scores_by_context_budget(lattice_probe_rows, allowed_candidates=lattice_ids)
    measured_contexts = len({context for context, _budget in grouped})
    measured_budgets = sorted({budget for _context, budget in grouped if math.isfinite(budget)})
    recognized_lattice_rows = [
        row for row in lattice_probe_rows if boolish(row.get("candidate_recognized"))
    ]
    complete_context_budget_pairs = sum(1 for scores in grouped.values() if lattice_ids <= set(scores))
    static_rows = [row for row in lattice_probe_rows if row.get("candidate_id") == G510_STATIC_CANDIDATE]
    summary = {
        "schema_version": "phase5p5_repair5g510_lattice_counterfactual_run_summary_v1",
        "decision": "lattice_counterfactuals_executed" if lattice_probe_rows else "lattice_counterfactuals_not_run",
        "counterfactuals_run": bool(lattice_probe_rows),
        "maps": maps,
        "agent_counts": agent_counts,
        "instance_ids": instance_ids,
        "budgets_ms": budgets,
        "primary_budgets_ms": [1000, 2000],
        "stress_budget_ms": 250,
        "bonus_budget_ms": 500,
        "candidate_count": len(lattice_ids),
        "candidate_ids": sorted(lattice_ids),
        "probe_rows_total": len(probe_rows),
        "lattice_probe_rows": len(lattice_probe_rows),
        "checkpoint_rows": len(checkpoint_rows),
        "planned_rows": len(plan),
        "measured_contexts": measured_contexts,
        "measured_budgets_ms": measured_budgets,
        "complete_context_budget_pairs": complete_context_budget_pairs,
        "recognized_lattice_rows": len(recognized_lattice_rows),
        "all_lattice_rows_recognized": len(recognized_lattice_rows) == len(lattice_probe_rows) and bool(lattice_probe_rows),
        "static_candidate_rows": len(static_rows),
        "observed_ids_only": observed_only,
        "ids_166_205_untouched": observed_only,
        "plan_csv": str(resolve(args.plan_csv, root)),
        "results_csv": str(resolve(args.results_csv, root)),
        "probe_jsonl": str(probe_jsonl),
        "checkpoint_jsonl": str(checkpoint_jsonl),
        "includes_parity_reference_candidates": bool(args.include_parity_reference_candidates),
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.10 Lattice Counterfactual Run\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- candidate_count: `{summary['candidate_count']}`\n"
        f"- lattice_probe_rows: `{summary['lattice_probe_rows']}`\n"
        f"- measured_contexts: `{summary['measured_contexts']}`\n"
        f"- budgets_ms: `{summary['budgets_ms']}`\n"
        f"- all_lattice_rows_recognized: `{summary['all_lattice_rows_recognized']}`\n"
        f"- observed_ids_only: `{summary['observed_ids_only']}`\n"
        f"- ids_166_205_untouched: `{summary['ids_166_205_untouched']}`\n\n"
        "The run uses observed scenario IDs only and invokes the existing project-owned same-context UpdateLTM probe hook. "
        "It does not change PIBT, LaCAM*, candidate generation, pruning, restarts, or external/lacam2.\n",
    )
    print(json.dumps({"decision": summary["decision"], "lattice_probe_rows": len(lattice_probe_rows), "measured_contexts": measured_contexts}))
    return 0 if summary["all_lattice_rows_recognized"] and observed_only and lattice_probe_rows else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

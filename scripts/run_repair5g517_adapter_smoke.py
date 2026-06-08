"""Run a minimal G5.17 adapter smoke for the 10 targeted repair candidates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import append_jsonl  # noqa: E402
from repair5g3_common import MethodSpec  # noqa: E402
from repair5g5_common import prepare_scenarios, run_one_solver_task  # noqa: E402
from repair5g510_common import read_jsonl  # noqa: E402
from repair5g517_common import (  # noqa: E402
    DEFAULT_BINARY,
    DEFAULT_G516_PROBE_PLAN,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    G517_CLOSED_CLAIMS,
    G517_SMOKE_REPORT,
    G517_SMOKE_SUMMARY,
    assert_observed_plan,
    candidate_recognition_counts,
    context_combos_from_plan,
    external_lacam2_solver_status,
    plan_rows,
    repair_candidate_ids,
    repo_root,
    resolve,
    write_json,
    write_probe_csv_from_jsonl,
    write_text,
)


DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g517_adapter_smoke"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g517_adapter_smoke_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g517_adapter_smoke_scenario_generation.json"
DEFAULT_OUTPUT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g517_adapter_smoke_runs.jsonl"
DEFAULT_COMMAND_LOG = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g517_adapter_smoke_commands.jsonl"
DEFAULT_UPDATE_LOG = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g517_adapter_smoke_ltm_updates.jsonl"
DEFAULT_PROBE_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g517_adapter_smoke_update_probes.jsonl"
DEFAULT_CHECKPOINT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g517_adapter_smoke_checkpoints.jsonl"
DEFAULT_RESULTS_CSV = "outputs/tables/phase5p5_repair5g517_adapter_smoke_results.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--probe-plan-csv", type=Path, default=Path(DEFAULT_G516_PROBE_PLAN))
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_OUTPUT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMAND_LOG))
    parser.add_argument("--update-log", type=Path, default=Path(DEFAULT_UPDATE_LOG))
    parser.add_argument("--probe-jsonl", type=Path, default=Path(DEFAULT_PROBE_JSONL))
    parser.add_argument("--checkpoint-jsonl", type=Path, default=Path(DEFAULT_CHECKPOINT_JSONL))
    parser.add_argument("--results-csv", type=Path, default=Path(DEFAULT_RESULTS_CSV))
    parser.add_argument("--summary-json", type=Path, default=Path(G517_SMOKE_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G517_SMOKE_REPORT))
    parser.add_argument("--time-limit-sec", type=float, default=5.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = plan_rows(resolve(args.probe_plan_csv, root))
    flags = assert_observed_plan(rows, label="G5.17 adapter smoke plan seeds")
    combo = context_combos_from_plan(rows, limit=1)[0]
    candidates = repair_candidate_ids()
    candidate_set = set(candidates)

    output_jsonl = resolve(args.output_jsonl, root)
    command_log = resolve(args.command_log, root)
    update_log = resolve(args.update_log, root)
    probe_jsonl = resolve(args.probe_jsonl, root)
    checkpoint_jsonl = resolve(args.checkpoint_jsonl, root)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log, probe_jsonl, checkpoint_jsonl, resolve(args.results_csv, root)]:
            path.unlink(missing_ok=True)
    temp_dir = output_jsonl.parent / "_task_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    command_log.parent.mkdir(parents=True, exist_ok=True)

    prepare_scenarios(
        root=root,
        source_scenario_dir=resolve(args.source_scenario_dir, root),
        scenario_dir=resolve(args.scenario_dir, root),
        scenario_metadata=resolve(args.scenario_metadata_json, root),
        maps=[str(combo["map"])],
        agent_counts=[int(combo["agents"])],
        instance_ids=[int(combo["seed"])],
    )

    spec = MethodSpec(
        "repair5g59_static_flow_shield",
        "repair5g517_adapter_smoke_static_context",
        (
            "--repair5g5-selector-spec",
            str(resolve(args.selector_spec_json, root)),
            "--repair5g-export-update-checkpoints-jsonl",
            str(checkpoint_jsonl),
            "--repair5g-checkpoint-topk-edges",
            "64",
            "--repair5g-checkpoint-edge-filter",
            "nonzero",
            "--repair5g-counterfactual-update-probe-jsonl",
            str(probe_jsonl),
            "--repair5g-counterfactual-candidates",
            ",".join(candidates),
            "--repair5g-counterfactual-short-budget-ms",
            "1000",
            "--repair5g-counterfactual-max-contexts",
            "1",
            "--repair5g-runtime-audit-mode",
            "perf",
        ),
    )
    solver_rows, _updates, command_row = run_one_solver_task(
        root=root,
        binary=resolve(args.binary, root),
        scenario_dir=resolve(args.scenario_dir, root),
        temp_dir=temp_dir,
        update_log=update_log,
        map_name=str(combo["map"]),
        agents=int(combo["agents"]),
        seed=int(combo["seed"]),
        time_limit_sec=float(args.time_limit_sec),
        ltm_max_iterations=int(args.ltm_max_iterations),
        spec=spec,
        manifest="phase5p5-repair5g517-adapter-smoke",
    )
    for row in solver_rows:
        append_jsonl(output_jsonl, row)
    append_jsonl(command_log, command_row)

    probe_rows = write_probe_csv_from_jsonl(probe_jsonl, resolve(args.results_csv, root))
    checkpoint_rows = read_jsonl(checkpoint_jsonl)
    counts = candidate_recognition_counts(probe_rows, candidate_set)
    external_status = external_lacam2_solver_status(root)
    seen_candidates = sorted({str(row.get("candidate_id", "")) for row in probe_rows if str(row.get("candidate_id", "")) in candidate_set})
    gates = {
        "smoke_probe_ran": bool(probe_rows),
        "repair_candidate_count_eq_10": len(candidates) == 10,
        "repair_candidate_rows_eq_10": counts["rows"] == 10,
        "candidate_recognized_all": counts["candidate_recognized_all"],
        "updateparams_fingerprint_all": counts["updateparams_fingerprint_all"],
        "checkpoint_rows_gt_0": len(checkpoint_rows) > 0,
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "observed_ids_only": flags["observed_ids_only"],
        "external_lacam2_solver_untouched": not external_status,
        "max_workers_eq_1": True,
    }
    passed = all(gates.values())
    decision = "adapter_smoke_passed_continue_targeted_probe" if passed else "adapter_smoke_failed_no_targeted_probe"
    summary = {
        "schema_version": "phase5p5_repair5g517_adapter_smoke_summary_v1",
        "decision": decision,
        "probe_ran": bool(probe_rows),
        "context": combo,
        "candidate_ids": candidates,
        "seen_repair_candidates": seen_candidates,
        "probe_rows": len(probe_rows),
        "checkpoint_rows": len(checkpoint_rows),
        "recognition": counts,
        "external_lacam2_solver_status": external_status,
        "results_csv": str(resolve(args.results_csv, root)),
        "probe_jsonl": str(probe_jsonl),
        "gates": gates,
        **flags,
        **G517_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.17 Adapter Smoke\n\n"
        f"- decision: `{decision}`\n"
        f"- context: `{combo}`\n"
        f"- repair_candidate_count: `{len(candidates)}`\n"
        f"- probe_rows: `{len(probe_rows)}`\n"
        f"- candidate_recognized_all: `{counts['candidate_recognized_all']}`\n"
        f"- updateparams_fingerprint_all: `{counts['updateparams_fingerprint_all']}`\n"
        f"- external_lacam2_solver_untouched: `{not external_status}`\n"
        f"- gates: `{gates}`\n\n"
        "The smoke uses one observed context, `max_workers=1`, and only the ten targeted repair candidates. It is an adapter-recognition check, not a runtime-policy validation.\n",
    )
    print(json.dumps({"decision": decision, "probe_rows": len(probe_rows), "candidate_recognized_all": counts["candidate_recognized_all"]}))
    return 0 if passed else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

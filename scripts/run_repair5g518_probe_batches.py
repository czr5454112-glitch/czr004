"""Run G5.18 bounded local probe batches against the old-14 oracle controls."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import append_jsonl  # noqa: E402
from repair5g3_common import MethodSpec  # noqa: E402
from repair5g5_common import prepare_scenarios, run_one_solver_task  # noqa: E402
from repair5g510_common import read_jsonl  # noqa: E402
from repair5g517_common import candidate_recognition_counts, write_probe_csv_from_jsonl  # noqa: E402
from repair5g518_common import (  # noqa: E402
    DEFAULT_BINARY,
    DEFAULT_G516_PROBE_PLAN,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    G518_CLOSED_CLAIMS,
    PRIMARY_BUDGETS_MS,
    batch_integrity_report,
    batch_integrity_summary,
    batch_plan_csv,
    batch_result_csv,
    context_combos_from_plan,
    duplicate_context_candidate_budget_rows,
    external_lacam2_solver_status,
    observed_id_flags,
    observed_id_guard,
    old14_candidate_ids,
    plan_rows,
    read_csv_dicts,
    repo_root,
    resolve,
    selected_new_candidates,
    selected_rows,
    write_csv,
    write_json_file,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--probe-plan-csv", type=Path, default=Path(DEFAULT_G516_PROBE_PLAN))
    parser.add_argument("--batches", default="A,B,C")
    parser.add_argument("--max-contexts", type=int, default=20)
    parser.add_argument("--time-limit-sec", type=float, default=5.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def method_spec_for_budget(*, batch: str, budget: int, selector_spec: Path, probe_jsonl: Path, checkpoint_jsonl: Path, candidates: list[str]) -> MethodSpec:
    return MethodSpec(
        "repair5g59_static_flow_shield",
        f"repair5g518_batch_{batch}_budget_{budget}ms_static_context",
        (
            "--repair5g5-selector-spec",
            str(selector_spec),
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
            str(int(budget)),
            "--repair5g-counterfactual-max-contexts",
            "1",
            "--repair5g-runtime-audit-mode",
            "perf",
        ),
    )


def category_by_context(plan: list[dict[str, Any]]) -> dict[str, str]:
    out = {}
    for row in plan:
        key = str(row.get("normalized_context_key", ""))
        if key and key not in out:
            out[key] = str(row.get("error_category", ""))
    return out


def write_batch_plan(batch: str, combos: list[dict[str, Any]], candidates: list[str], old_controls: set[str], category_lookup: dict[str, str]) -> list[dict[str, Any]]:
    rows = []
    for combo in combos:
        key_prefix = f"{combo['map']}|a{combo['agents']}|s{combo['seed']}|it0"
        matching_key = next((key for key in category_lookup if key.startswith(key_prefix)), "")
        for candidate in candidates:
            for budget in PRIMARY_BUDGETS_MS:
                rows.append(
                    {
                        "row_type": "g518_probe_batch_plan",
                        "batch": batch,
                        "normalized_context_key": matching_key,
                        "map": combo["map"],
                        "agents": combo["agents"],
                        "seed": combo["seed"],
                        "iteration": 0,
                        "error_category": category_lookup.get(matching_key, ""),
                        "candidate_id": candidate,
                        "candidate_role": "old14_control" if candidate in old_controls else "g518_new_candidate",
                        "short_budget_ms": budget,
                        "max_workers": 1,
                        "observed_ids_only": True,
                        "ids_166_205_untouched": True,
                    }
                )
    write_csv(batch_plan_csv(batch), rows)
    return rows


def run_batch(args: argparse.Namespace, root: Path, batch: str, selected: list[dict[str, Any]]) -> int:
    batch = batch.upper()
    old_controls = old14_candidate_ids(root)
    new_candidates = selected_new_candidates(batch, selected)
    candidates = old_controls + new_candidates
    source_plan = plan_rows(resolve(args.probe_plan_csv, root))
    observed_id_guard([row.get("seed", "") for row in source_plan], label=f"G5.18 batch {batch} source plan seeds")
    combos = context_combos_from_plan(source_plan, limit=int(args.max_contexts))
    category_lookup = category_by_context(source_plan)
    plan = write_batch_plan(batch, combos, candidates, set(old_controls), category_lookup)
    if int(args.max_workers) != 1:
        summary = {
            "schema_version": "phase5p5_repair5g518_batch_integrity_summary_v1",
            "batch": batch,
            "decision": "g518_probe_batch_integrity_failed",
            "probe_ran": False,
            "no_run_reason": "max_workers must be 1",
            "max_workers": int(args.max_workers),
            **G518_CLOSED_CLAIMS,
        }
        write_json_file(batch_integrity_summary(batch), summary)
        return 2
    log_dir = resolve(f"outputs/logs/phase5p5_repair5g518_batch_{batch}", root)
    scenario_dir = resolve(f"outputs/tmp/phase5p5_repair5g518_batch_{batch}_scenarios", root)
    scenario_metadata = resolve(f"outputs/reports/phase5p5_repair5g518_batch_{batch}_scenario_generation.json", root)
    output_jsonl = log_dir / f"phase5p5_repair5g518_batch_{batch}_runs.jsonl"
    command_log = log_dir / f"phase5p5_repair5g518_batch_{batch}_commands.jsonl"
    update_log = log_dir / f"phase5p5_repair5g518_batch_{batch}_ltm_updates.jsonl"
    probe_jsonl = log_dir / f"phase5p5_repair5g518_batch_{batch}_update_probes.jsonl"
    checkpoint_jsonl = log_dir / f"phase5p5_repair5g518_batch_{batch}_checkpoints.jsonl"
    status_json = log_dir / f"phase5p5_repair5g518_batch_{batch}_status.json"
    results_csv = resolve(batch_result_csv(batch), root)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log, probe_jsonl, checkpoint_jsonl, results_csv, status_json]:
            path.unlink(missing_ok=True)
    temp_dir = log_dir / "_task_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    maps = sorted({str(combo["map"]) for combo in combos})
    agents = sorted({int(combo["agents"]) for combo in combos})
    seeds = sorted({int(combo["seed"]) for combo in combos})
    prepare_scenarios(
        root=root,
        source_scenario_dir=resolve(args.source_scenario_dir, root),
        scenario_dir=scenario_dir,
        scenario_metadata=scenario_metadata,
        maps=maps,
        agent_counts=agents,
        instance_ids=seeds,
    )
    tasks = [(combo, budget) for combo in combos for budget in PRIMARY_BUDGETS_MS]
    status_json.write_text(json.dumps({"phase": "starting", "total_tasks": len(tasks), "completed_tasks": 0}, indent=2) + "\n", encoding="utf-8")
    completed = 0
    for combo, budget in tasks:
        spec = method_spec_for_budget(
            batch=batch,
            budget=int(budget),
            selector_spec=resolve(args.selector_spec_json, root),
            probe_jsonl=probe_jsonl,
            checkpoint_jsonl=checkpoint_jsonl,
            candidates=candidates,
        )
        solver_rows, _updates, command_row = run_one_solver_task(
            root=root,
            binary=resolve(args.binary, root),
            scenario_dir=scenario_dir,
            temp_dir=temp_dir,
            update_log=update_log,
            map_name=str(combo["map"]),
            agents=int(combo["agents"]),
            seed=int(combo["seed"]),
            time_limit_sec=float(args.time_limit_sec),
            ltm_max_iterations=int(args.ltm_max_iterations),
            spec=spec,
            manifest=f"phase5p5-repair5g518-batch-{batch}",
        )
        for row in solver_rows:
            append_jsonl(output_jsonl, row)
        append_jsonl(command_log, command_row)
        completed += 1
        status_json.write_text(
            json.dumps(
                {
                    "phase": "running" if completed < len(tasks) else "solver_complete",
                    "total_tasks": len(tasks),
                    "completed_tasks": completed,
                    "last_task": {
                        "map": combo["map"],
                        "agents": combo["agents"],
                        "seed": combo["seed"],
                        "budget": budget,
                        "returncode": command_row["returncode"],
                    },
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    write_probe_csv_from_jsonl(probe_jsonl, results_csv)
    result_rows = read_csv_dicts(results_csv)
    checkpoint_rows = read_jsonl(checkpoint_jsonl)
    flags = observed_id_flags(result_rows + plan)
    contexts = {row.get("normalized_context_key", "") for row in result_rows}
    budgets = sorted({int(float(row.get("short_budget_ms", 0))) for row in result_rows if row.get("short_budget_ms", "")})
    seen_candidates = {row.get("candidate_id", "") for row in result_rows}
    recognition = candidate_recognition_counts(result_rows, set(candidates))
    duplicate_rows = duplicate_context_candidate_budget_rows(result_rows)
    external_status = external_lacam2_solver_status(root)
    expected_rows = len(combos) * len(candidates) * len(PRIMARY_BUDGETS_MS)
    gates = {
        "probe_ran": bool(result_rows),
        "rows_eq_expected": len(result_rows) == expected_rows,
        "contexts_eq_planned": len(contexts) == len(combos),
        "candidate_count_eq_planned": len(seen_candidates & set(candidates)) == len(candidates),
        "old14_controls_eq_14": len(old_controls) == 14,
        "new_candidates_lte_48": len(new_candidates) <= 48,
        "target_contexts_lte_24": len(combos) <= 24,
        "budgets_eq_1000_2000": budgets == PRIMARY_BUDGETS_MS,
        "candidate_recognized_all": recognition["candidate_recognized_all"],
        "duplicate_context_candidate_budget_rows_eq_0": duplicate_rows == 0,
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "observed_ids_only": flags["observed_ids_only"],
        "external_lacam2_solver_untouched": not external_status,
        "max_workers_eq_1": int(args.max_workers) == 1,
    }
    decision = "g518_probe_batch_integrity_passed_continue_oracle" if all(gates.values()) else "g518_probe_batch_integrity_failed"
    summary = {
        "schema_version": "phase5p5_repair5g518_batch_integrity_summary_v1",
        "batch": batch,
        "decision": decision,
        "probe_ran": bool(result_rows),
        "probe_rows": len(result_rows),
        "expected_rows": expected_rows,
        "target_contexts": len(combos),
        "candidate_count": len(candidates),
        "old14_control_count": len(old_controls),
        "new_candidate_count": len(new_candidates),
        "budgets": budgets,
        "checkpoint_rows": len(checkpoint_rows),
        "duplicate_context_candidate_budget_rows": duplicate_rows,
        "recognition": recognition,
        "external_lacam2_solver_status": external_status,
        "results_csv": str(results_csv),
        "probe_plan_csv": str(resolve(batch_plan_csv(batch), root)),
        "gates": gates,
        **flags,
        **G518_CLOSED_CLAIMS,
    }
    write_json_file(batch_integrity_summary(batch), summary)
    write_text_file(
        batch_integrity_report(batch),
        f"# Phase5.5 Repair5G.5.18 Batch {batch} Probe Integrity\n\n"
        f"- decision: `{decision}`\n"
        f"- probe_rows: `{len(result_rows)}`\n"
        f"- expected_rows: `{expected_rows}`\n"
        f"- target_contexts: `{len(combos)}`\n"
        f"- old14_control_count: `{len(old_controls)}`\n"
        f"- new_candidate_count: `{len(new_candidates)}`\n"
        f"- duplicate_context_candidate_budget_rows: `{duplicate_rows}`\n"
        f"- candidate_recognized_all: `{recognition['candidate_recognized_all']}`\n"
        f"- gates: `{gates}`\n\n"
        "The batch is local, sequential, and writes isolated G5.18 output paths. These rows are candidate-space diagnostics only.\n",
    )
    print(json.dumps({"batch": batch, "decision": decision, "probe_rows": len(result_rows), "expected_rows": expected_rows}))
    return 0 if decision == "g518_probe_batch_integrity_passed_continue_oracle" else 2


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    selected = selected_rows()
    failures = 0
    for batch in [item.strip().upper() for item in args.batches.split(",") if item.strip()]:
        failures += 0 if run_batch(args, root, batch, selected) == 0 else 1
    return 0 if failures == 0 else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

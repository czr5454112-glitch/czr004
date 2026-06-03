"""Run Repair5G.3 determinism/repeat stress before broader validation."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import (  # noqa: E402
    AGENTS,
    CONTROL_METHODS,
    MAPS,
    P3_SYNTHETIC_METHODS,
    add_selector_alias_rows,
    audit_and_prepare_scenarios,
    build_specs,
    expected_keys,
    frozen_underlying_methods,
    git_value,
    grouped_rows,
    load_json,
    method_stats,
    metrics_for_rows,
    now_iso,
    paired_rows,
    parity_mismatch_rows,
    read_jsonl,
    rel,
    repo_root,
    resolve,
    run_solver_grid,
    schema_error_count,
    support_gate_summary,
    synthesize_seeded_diagnostics,
    write_csv_rows,
    write_json,
    write_jsonl,
    write_method_report,
    write_update_summary,
)


DEFAULT_BINARY = "build/phase1a-batch/phase1a_batch.exe"
DEFAULT_SOURCE_SCENARIO_DIR = "outputs/tmp/phase1a/generated/phase1a-generated-random"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g3_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g3_scenario_generation.json"
DEFAULT_RUNTIME_ROOT = "outputs/tmp/phase5p5_repair5g3_runtimes"
DEFAULT_FROZEN_SPEC = "outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g3_determinism_repeat"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g3_determinism_repeat.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g3_determinism_repeat_commands.jsonl"
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g3_determinism_repeat_paired.csv"
DEFAULT_BY_REPEAT = "outputs/tables/phase5p5_repair5g3_determinism_repeat_by_repeat.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g3_determinism_repeat_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g3_determinism_repeat_summary.json"

SELECTED = "repair5g2_frozen_static_or_selector"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--runtime-root", type=Path, default=Path(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_SPEC))
    parser.add_argument("--maps", nargs="+", default=MAPS)
    parser.add_argument("--agent-counts", nargs="+", type=int, default=AGENTS)
    parser.add_argument("--instance-ids", nargs="+", type=int, default=list(range(66, 76)))
    parser.add_argument("--time-limit-sec", type=float, default=3.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMANDS))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED))
    parser.add_argument("--by-repeat-csv", type=Path, default=Path(DEFAULT_BY_REPEAT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def run_repeat(
    *,
    root: Path,
    args: argparse.Namespace,
    repeat_index: int,
    actual_methods: list[str],
    specs: list[Any],
    scenario_dir: Path,
    output_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    rng = random.Random(20260603 + repeat_index)
    ordered = list(specs)
    rng.shuffle(ordered)
    method_order = [spec.alias for spec in ordered]
    raw_jsonl = output_dir / f"repeat_{repeat_index}.raw.jsonl"
    commands = output_dir / f"repeat_{repeat_index}.commands.jsonl"
    status = output_dir / f"repeat_{repeat_index}.status.json"
    if args.overwrite:
        for path in [raw_jsonl, commands]:
            if path.exists():
                path.unlink()
    completed = set()
    if raw_jsonl.exists():
        completed = {
            (str(row.get("map")), int(row.get("agents")), int(row.get("seed")), str(row.get("method")))
            for row in read_jsonl(raw_jsonl)
        }
    if not args.skip_solver:
        run_solver_grid(
            root=root,
            binary=resolve(args.binary, root),
            scenario_dir=scenario_dir,
            output_jsonl=raw_jsonl,
            command_log=commands,
            maps=[str(value) for value in args.maps],
            agent_counts=[int(value) for value in args.agent_counts],
            instance_ids=[int(value) for value in args.instance_ids],
            time_limit_sec=float(args.time_limit_sec),
            ltm_max_iterations=int(args.ltm_max_iterations),
            methods=ordered,
            completed=completed,
            max_workers=int(args.max_workers),
            manifest="phase5p5-repair5g3-determinism-repeat",
            status_json=status,
        )
    rows = read_jsonl(raw_jsonl)
    rows = [dict(row, repeat_index=repeat_index) for row in rows]
    rows.extend(dict(row, repeat_index=repeat_index) for row in add_selector_alias_rows(rows, load_json(resolve(args.frozen_selector_spec_json, root))))
    rows.extend(
        dict(row, repeat_index=repeat_index)
        for row in synthesize_seeded_diagnostics(
            rows,
            synthetic_names=P3_SYNTHETIC_METHODS,
            actual_candidate_methods=actual_methods,
        )
    )
    return rows, read_jsonl(commands), method_order


def write_decision_if_failed(root: Path, summary: dict[str, Any]) -> None:
    if summary["gates"].get("determinism_repeat_gates_passed"):
        return
    decision_json = root / "outputs/reports/phase5p5_repair5g3_decision_summary.json"
    decision_md = root / "outputs/reports/phase5p5_repair5g3_decision.md"
    payload = {
        "schema_version": "phase5p5_repair5g3_decision_summary_v1",
        "created_at": now_iso(),
        "decision": "stop_for_determinism_or_time_budget_autopsy",
        "reason": "Repair5G.3 determinism/repeat gates failed before broader validation.",
        "determinism_repeat_summary": rel(resolve(DEFAULT_SUMMARY, root), root),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "diagnostic_only": True,
    }
    write_json(decision_json, payload)
    decision_md.parent.mkdir(parents=True, exist_ok=True)
    decision_md.write_text(
        "# Phase5.5 Repair5G.3 Decision\n\n"
        "Decision: `stop_for_determinism_or_time_budget_autopsy`\n\n"
        "Repair5G.3 broader validation is blocked because the determinism/repeat gate failed.\n\n"
        "- phase5p5_allowed: `false`\n"
        "- phase6_allowed: `false`\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    spec = load_json(resolve(args.frozen_selector_spec_json, root))
    scenario_dir = resolve(args.scenario_dir, root)
    output_jsonl = resolve(args.output_jsonl, root)
    command_log = resolve(args.command_log, root)
    output_dir = output_jsonl.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime_root = resolve(args.runtime_root, root)
    actual_methods = [
        *CONTROL_METHODS,
        *frozen_underlying_methods(spec),
    ]
    actual_methods = list(dict.fromkeys(actual_methods))
    specs = build_specs(actual_methods, runtime_root)
    if args.overwrite:
        for path in [output_jsonl, command_log]:
            if path.exists():
                path.unlink()
    audit_and_prepare_scenarios(
        root=root,
        source_scenario_dir=resolve(args.source_scenario_dir, root),
        scenario_dir=scenario_dir,
        scenario_metadata=resolve(args.scenario_metadata_json, root),
        maps=[str(value) for value in args.maps],
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=[int(value) for value in args.instance_ids],
        generate_missing=True,
        base_seed=20260522,
    )

    all_rows: list[dict[str, Any]] = []
    all_commands: list[dict[str, Any]] = []
    method_orders: dict[str, list[str]] = {}
    for repeat_index in range(int(args.repeats)):
        rows, commands, order = run_repeat(
            root=root,
            args=args,
            repeat_index=repeat_index,
            actual_methods=actual_methods,
            specs=specs,
            scenario_dir=scenario_dir,
            output_dir=output_dir,
        )
        all_rows.extend(rows)
        all_commands.extend(commands)
        method_orders[str(repeat_index)] = order
    write_jsonl(output_jsonl, all_rows)
    write_jsonl(command_log, all_commands)
    write_update_summary(output_jsonl.with_name("phase5p5_repair5g3_determinism_repeat_ltm_updates.jsonl"), all_rows)
    paired = paired_rows(all_rows, dimensions=["repeat_index"])
    stats = method_stats(paired)
    by_repeat = grouped_rows(paired, group_fields=["repeat_index"])
    write_csv_rows(resolve(args.paired_csv, root), paired)
    write_csv_rows(resolve(args.by_repeat_csv, root), by_repeat)

    repeat_gate_rows = []
    true_semantic = 0
    parity_exact_all = True
    for repeat_index in range(int(args.repeats)):
        repeat_rows = [row for row in all_rows if int(row.get("repeat_index", -1)) == repeat_index]
        parity = support_gate_summary(repeat_rows, include_static_c_equiv_pairs=False)
        mismatches = parity_mismatch_rows(
            repeat_rows,
            [
                ("lacam_star_ltm", "always_additive_defer"),
                ("lacam_star_ltm", "repair5f_candidate_additive_ltm"),
                ("lacam_star_ltm", "laur_disable"),
                ("lacam_star_ltm", "laur_force_additive_direct"),
                ("lacam_star_ltm", "repair5g_dual_additive_parity"),
                ("lacam_star_ltm", "repair5g_dual_c_equiv_additive"),
            ],
        )
        semantic_count = sum(1 for row in mismatches if row.get("classification") == "true_semantic_mismatch")
        true_semantic += semantic_count
        selected = [row for row in paired if row.get("candidate_id") == SELECTED and int(row.get("repeat_index", -1)) == repeat_index]
        selected_metrics = metrics_for_rows(selected) if selected else {}
        repeat_gate_rows.append({"repeat_index": repeat_index, **selected_metrics})
        parity_exact_all = parity_exact_all and all(bool(parity.get(key)) for key in [
            "additive_parity_exact",
            "always_additive_defer_parity_exact",
            "laur_disable_parity_exact",
            "laur_force_additive_direct_parity_exact",
            "dual_additive_parity_exact",
            "dual_c_equiv_additive_parity_exact",
        ])
    selected_negative_repeats = sum(
        1 for row in repeat_gate_rows if float(row.get("mean_delta_ratio_vs_ltm") or 0.0) < 0.0
    )
    selected_metrics = stats.get(SELECTED, {})
    expected = expected_keys(
        [str(value) for value in args.maps],
        [int(value) for value in args.agent_counts],
        [int(value) for value in args.instance_ids],
        [*actual_methods, *FROZEN_METHODS_FOR_EXPECTED(), *P3_SYNTHETIC_METHODS],
    )
    expected_rows = len(expected) * int(args.repeats)
    gates = {
        "raw_control_parity_exact": parity_exact_all,
        "strict_control_parity_exact_for_non_timeout_equivalent_controls": true_semantic == 0,
        "true_semantic_parity_mismatch_count": true_semantic,
        "true_semantic_parity_mismatch_count_zero": true_semantic == 0,
        "solver_crash_count": sum(1 for row in all_commands if int(row.get("returncode", 0)) == 1),
        "schema_errors": schema_error_count(all_rows),
        "selected_mean_delta_sign_stable": selected_negative_repeats >= 2,
        "selected_repeat_mean_delta_ratio_vs_ltm_lt_0_repeats": selected_negative_repeats,
        "selected_success_worse_than_ltm_groups": int(selected_metrics.get("success_worse_than_ltm_groups", 99)),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    gates["determinism_repeat_gates_passed"] = (
        gates["strict_control_parity_exact_for_non_timeout_equivalent_controls"]
        and gates["true_semantic_parity_mismatch_count_zero"]
        and gates["solver_crash_count"] == 0
        and gates["schema_errors"] == 0
        and gates["selected_mean_delta_sign_stable"]
        and gates["selected_success_worse_than_ltm_groups"] == 0
    )
    summary = {
        "schema_version": "phase5p5_repair5g3_determinism_repeat_summary_v1",
        "created_at": now_iso(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "maps": [str(value) for value in args.maps],
        "agent_counts": [int(value) for value in args.agent_counts],
        "instance_ids": [int(value) for value in args.instance_ids],
        "time_limit_sec": float(args.time_limit_sec),
        "ltm_max_iterations": int(args.ltm_max_iterations),
        "repeats": int(args.repeats),
        "method_orders": method_orders,
        "row_count": len(all_rows),
        "expected_row_count": expected_rows,
        "missing_rows": max(expected_rows - len(all_rows), 0),
        "schema_errors": schema_error_count(all_rows),
        "solver_crash_count": gates["solver_crash_count"],
        "method_stats": stats,
        "repeat_selected_metrics": repeat_gate_rows,
        "gates": gates,
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_method_report(resolve(args.report, root), title="Phase5.5 Repair5G.3 Determinism Repeat Report", summary=summary)
    write_decision_if_failed(root, summary)
    print(json.dumps({"determinism_repeat_gates_passed": gates["determinism_repeat_gates_passed"], "rows": len(all_rows)}))
    return 0 if gates["determinism_repeat_gates_passed"] else 2


def FROZEN_METHODS_FOR_EXPECTED() -> list[str]:
    return [
        "repair5g2_frozen_static_or_selector",
        "repair5g2_best_frozen_static_candidate",
        "repair5g2_c_equiv_best_frozen_baseline",
        "repair5g2_g1_top_diagnostic_candidate",
    ]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

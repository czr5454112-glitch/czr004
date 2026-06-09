"""Run Repair5G.3 broader frozen validation on new IDs 66..105."""

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

from repair5g3_common import (  # noqa: E402
    AGENTS,
    FROZEN_ALIASES,
    MAPS,
    P4_SYNTHETIC_METHODS,
    add_selector_alias_rows,
    audit_and_prepare_scenarios,
    build_specs,
    expected_keys,
    g3_actual_methods,
    git_value,
    grouped_rows,
    load_json,
    method_component,
    method_stats,
    metrics_for_rows,
    now_iso,
    oracle_regret_rows,
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
DEFAULT_DETERMINISM_SUMMARY = "outputs/reports/phase5p5_repair5g3_determinism_repeat_summary.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g3_broader_validation"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g3_broader_validation.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g3_broader_validation_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g3_broader_validation_ltm_updates.jsonl"
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g3_broader_validation_paired.csv"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g3_broader_validation_summary.csv"
DEFAULT_BY_GROUP = "outputs/tables/phase5p5_repair5g3_broader_validation_by_map_agent.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g3_broader_validation_oracle_regret.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g3_broader_validation_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g3_broader_validation_summary.json"
DEFAULT_AUDIT = "outputs/reports/phase5p5_repair5g3_broader_validation_audit.md"

SELECTED = "repair5g2_frozen_static_or_selector"
STATIC = "repair5g2_best_frozen_static_candidate"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--runtime-root", type=Path, default=Path(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_SPEC))
    parser.add_argument("--determinism-summary-json", type=Path, default=Path(DEFAULT_DETERMINISM_SUMMARY))
    parser.add_argument("--maps", nargs="+", default=MAPS)
    parser.add_argument("--agent-counts", nargs="+", type=int, default=AGENTS)
    parser.add_argument("--instance-ids", nargs="+", type=int, default=list(range(66, 106)))
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
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--audit-report", type=Path, default=Path(DEFAULT_AUDIT))
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--ignore-determinism-gate", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def classification(stats: dict[str, dict[str, Any]]) -> str:
    selector_mean = float(stats.get(SELECTED, {}).get("mean_delta_ratio_vs_ltm") or math.inf)
    static_mean = float(stats.get(STATIC, {}).get("mean_delta_ratio_vs_ltm") or math.inf)
    if abs(selector_mean - static_mean) <= 0.001:
        return "tied_within_0p001"
    return "selector_beats_static" if selector_mean < static_mean else "static_beats_selector"


def write_audit(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.3 Broader Validation Audit\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write(f"- decision_after_p4: `{summary['decision_after_p4']}`\n")
        handle.write(f"- missing_rows: `{summary['missing_rows']}`\n")
        handle.write(f"- schema_errors: `{summary['schema_errors']}`\n")
        handle.write(f"- solver_crash_count: `{summary['solver_crash_count']}`\n\n")
        handle.write("## Gates\n\n")
        for key, value in summary["gates"].items():
            handle.write(f"- `{key}`: `{value}`\n")


def write_terminal_decision(root: Path, summary: dict[str, Any]) -> None:
    decision = summary["decision_after_p4"]
    if decision not in {"protocol_failed", "stop_or_return_to_representation_design"}:
        return
    decision_json = root / "outputs/reports/phase5p5_repair5g3_decision_summary.json"
    decision_md = root / "outputs/reports/phase5p5_repair5g3_decision.md"
    payload = {
        "schema_version": "phase5p5_repair5g3_decision_summary_v1",
        "created_at": now_iso(),
        "decision": decision,
        "answers": [
            f"Does flow-shield survive broader new-ID validation? `directional_only={summary['gates'].get('representation_gates_passed')}`, but protocol acceptance is blocked.",
            f"Is static flow-shield enough? `{summary['gates'].get('selector_vs_static_classification')}` under directional P4 metrics.",
            f"Does map-agent selector add value over static? `{summary['gates'].get('selector_vs_static_classification')}`.",
            "Is there evidence that a learned contextual selector is worth building/running? `not evaluated because P4 protocol did not pass`.",
            "Is the effect stable across time budgets and LTM iteration budgets? `not run because P4 protocol did not pass`.",
            "Observed IDs now include `1..105`; IDs `66..105` were used in a failed/blocked G3 protocol and should not be reused as untouched final evidence.",
            "Recommended next split: after protocol/time-budget autopsy, use the next clean range, preferably `106..145`, unless `106..125` remains reserved for a later learning-bridge holdout.",
        ],
        "broader_summary": "outputs/reports/phase5p5_repair5g3_broader_validation_summary.json",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "diagnostic_only": True,
    }
    write_json(decision_json, payload)
    decision_md.parent.mkdir(parents=True, exist_ok=True)
    with decision_md.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.3 Decision\n\n")
        handle.write(f"Decision: `{decision}`\n\n")
        for answer in payload["answers"]:
            handle.write(f"- {answer}\n")
        handle.write("\n## Boundary\n\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- diagnostic_only: `true`\n")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    determinism = load_json(resolve(args.determinism_summary_json, root))
    if (
        determinism
        and not args.ignore_determinism_gate
        and not determinism.get("gates", {}).get("determinism_repeat_gates_passed", False)
    ):
        raise SystemExit("determinism repeat gates failed; broad validation is blocked")

    spec = load_json(resolve(args.frozen_selector_spec_json, root))
    actual_methods = g3_actual_methods(spec, broad=True)
    specs = build_specs(actual_methods, resolve(args.runtime_root, root))
    scenario_dir = resolve(args.scenario_dir, root)
    output_jsonl = resolve(args.output_jsonl, root)
    command_log = resolve(args.command_log, root)
    update_log = resolve(args.update_log, root)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log]:
            if path.exists():
                path.unlink()
    _, scenario_audit = audit_and_prepare_scenarios(
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
    completed = {
        (str(row.get("map")), int(row.get("agents")), int(row.get("seed")), str(row.get("method")))
        for row in read_jsonl(output_jsonl)
    }
    if not args.skip_solver:
        run_solver_grid(
            root=root,
            binary=resolve(args.binary, root),
            scenario_dir=scenario_dir,
            output_jsonl=output_jsonl,
            command_log=command_log,
            maps=[str(value) for value in args.maps],
            agent_counts=[int(value) for value in args.agent_counts],
            instance_ids=[int(value) for value in args.instance_ids],
            time_limit_sec=float(args.time_limit_sec),
            ltm_max_iterations=int(args.ltm_max_iterations),
            methods=specs,
            completed=completed,
            max_workers=int(args.max_workers),
            manifest="phase5p5-repair5g3-broader-validation",
            status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
        )
    rows = [row for row in read_jsonl(output_jsonl) if str(row.get("method")) in set(actual_methods)]
    rows = [*rows, *add_selector_alias_rows(rows, spec)]
    rows = [
        *rows,
        *synthesize_seeded_diagnostics(
            rows,
            synthetic_names=P4_SYNTHETIC_METHODS,
            actual_candidate_methods=actual_methods,
        ),
    ]
    write_jsonl(output_jsonl, rows)
    write_update_summary(update_log, rows)
    paired = paired_rows(rows)
    stats = method_stats(paired)
    by_group = grouped_rows(paired, group_fields=["map", "agents"])
    oracle = oracle_regret_rows(paired)
    write_csv_rows(resolve(args.paired_csv, root), paired)
    write_csv_rows(resolve(args.summary_csv, root), list(stats.values()))
    write_csv_rows(resolve(args.by_map_agent_csv, root), by_group)
    write_csv_rows(resolve(args.oracle_regret_csv, root), oracle)

    command_rows = read_jsonl(command_log)
    reported_methods = [
        *[method for method in actual_methods if method not in {"repair5g_dual_c_equiv_c100_b100_w075_d090"}],
        *FROZEN_ALIASES,
        *P4_SYNTHETIC_METHODS,
    ]
    reported_methods = list(dict.fromkeys(reported_methods))
    expected = expected_keys(
        [str(value) for value in args.maps],
        [int(value) for value in args.agent_counts],
        [int(value) for value in args.instance_ids],
        reported_methods,
    )
    actual = {
        (str(row.get("map")), int(row.get("agents")), int(row.get("seed")), str(row.get("method")))
        for row in rows
    }
    missing = sorted(expected - actual)
    parity = support_gate_summary(rows, include_static_c_equiv_pairs=False)
    mismatches = parity_mismatch_rows(
        rows,
        [
            ("lacam_star_ltm", "always_additive_defer"),
            ("lacam_star_ltm", "repair5f_candidate_additive_ltm"),
            ("lacam_star_ltm", "laur_disable"),
            ("lacam_star_ltm", "laur_force_additive_direct"),
            ("lacam_star_ltm", "repair5g_dual_additive_parity"),
            ("lacam_star_ltm", "repair5g_dual_c_equiv_additive"),
        ],
    )
    semantic_mismatches = sum(1 for row in mismatches if row.get("classification") == "true_semantic_mismatch")
    selected = stats.get(SELECTED, {})
    selected_boot = selected.get("bootstrap", {})
    flow_methods = [method for method in stats if method.startswith("repair5g1_shield_") or method in {SELECTED, STATIC, "repair5g2_g1_top_diagnostic_candidate"}]
    c_methods = [
        method
        for method in stats
        if method.startswith("repair5g_dual_c_equiv_") or method == "repair5g2_c_equiv_best_frozen_baseline"
    ]
    scalar_methods = [
        "repair5f_static_c100_b100_w075_d090",
        "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only",
    ]
    best_flow = min(flow_methods, key=lambda method: float(stats[method].get("mean_delta_ratio_vs_ltm") or math.inf))
    best_c = min(c_methods, key=lambda method: float(stats[method].get("mean_delta_ratio_vs_ltm") or math.inf))
    best_scalar = min(scalar_methods, key=lambda method: float(stats[method].get("mean_delta_ratio_vs_ltm") or math.inf))
    best_flow_mean = float(stats[best_flow].get("mean_delta_ratio_vs_ltm") or math.inf)
    best_c_mean = float(stats[best_c].get("mean_delta_ratio_vs_ltm") or math.inf)
    best_scalar_mean = float(stats[best_scalar].get("mean_delta_ratio_vs_ltm") or math.inf)
    flow_means = [float(stats[method].get("mean_delta_ratio_vs_ltm") or 0.0) for method in flow_methods]
    random_means = [
        float(stats[method].get("mean_delta_ratio_vs_ltm") or 0.0)
        for method in stats
        if method.startswith("repair5g3_random_flow_shield")
    ]
    shuffled_goal_means = [
        float(stats[method].get("mean_delta_ratio_vs_ltm") or 0.0)
        for method in stats
        if method.startswith("repair5g3_shuffled_goal_progress")
    ]
    selected_mean = float(selected.get("mean_delta_ratio_vs_ltm") or math.inf)
    gates = {
        "expected_rows_full": len(missing) == 0,
        "missing_rows": len(missing),
        "schema_errors": schema_error_count(rows),
        "solver_crash_count": sum(1 for row in command_rows if int(row.get("returncode", 0)) == 1),
        "additive_parity_exact": parity.get("additive_parity_exact", False),
        "laur_disable_parity_exact": parity.get("laur_disable_parity_exact", False),
        "laur_force_additive_direct_parity_exact": parity.get("laur_force_additive_direct_parity_exact", False),
        "dual_additive_parity_exact": parity.get("dual_additive_parity_exact", False),
        "dual_c_equiv_additive_parity_exact": parity.get("dual_c_equiv_additive_parity_exact", False),
        "true_semantic_parity_mismatch_count": semantic_mismatches,
        "all_costs_finite": parity.get("all_costs_finite", False),
        "cost_bounds_respected": parity.get("cost_bounds_respected", False),
        "no_ids_le_65_used_as_g3_fresh_validation": min(int(value) for value in args.instance_ids) > 65,
        "selected_better_gt_worse": int(selected.get("better", 0)) > int(selected.get("worse", 0)),
        "selected_mean_delta_ratio_vs_ltm_lt_neg_0p008": selected_mean < -0.008,
        "selected_bootstrap_probability_mean_delta_lt_0_ge_0p99": float(selected_boot.get("prob_mean_lt_0") or 0.0) >= 0.99,
        "selected_ratio_worse_than_ltm_groups_le_1": int(selected.get("ratio_worse_than_ltm_groups", 99)) <= 1,
        "selected_success_worse_than_ltm_groups_eq_0": int(selected.get("success_worse_than_ltm_groups", 99)) == 0,
        "best_flow_shield_mean_delta_ratio_vs_ltm_lt_neg_0p010": best_flow_mean < -0.010,
        "best_c_equiv_at_least_0p006_worse_than_best_flow": (best_c_mean - best_flow_mean) >= 0.006,
        "best_scalar_at_least_0p006_worse_than_best_flow": (best_scalar_mean - best_flow_mean) >= 0.006,
        "flow_shield_family_beats_random_median": bool(random_means) and sorted(flow_means)[len(flow_means) // 2] < sorted(random_means)[len(random_means) // 2],
        "flow_shield_family_beats_shuffled_goal_progress_median": bool(shuffled_goal_means)
        and sorted(flow_means)[len(flow_means) // 2] < sorted(shuffled_goal_means)[len(shuffled_goal_means) // 2],
        "selector_vs_static_classification": classification(stats),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    protocol_pass = (
        gates["expected_rows_full"] is True
        and gates["missing_rows"] == 0
        and gates["schema_errors"] == 0
        and gates["solver_crash_count"] == 0
        and gates["additive_parity_exact"] is True
        and gates["laur_disable_parity_exact"] is True
        and gates["laur_force_additive_direct_parity_exact"] is True
        and gates["dual_additive_parity_exact"] is True
        and gates["dual_c_equiv_additive_parity_exact"] is True
        and gates["true_semantic_parity_mismatch_count"] == 0
        and gates["all_costs_finite"] is True
        and gates["cost_bounds_respected"] is True
        and gates["no_ids_le_65_used_as_g3_fresh_validation"] is True
    )
    selected_pass = all(
        bool(gates[key])
        for key in [
            "selected_better_gt_worse",
            "selected_mean_delta_ratio_vs_ltm_lt_neg_0p008",
            "selected_bootstrap_probability_mean_delta_lt_0_ge_0p99",
            "selected_ratio_worse_than_ltm_groups_le_1",
            "selected_success_worse_than_ltm_groups_eq_0",
        ]
    )
    representation_pass = all(
        bool(gates[key])
        for key in [
            "best_flow_shield_mean_delta_ratio_vs_ltm_lt_neg_0p010",
            "best_c_equiv_at_least_0p006_worse_than_best_flow",
            "best_scalar_at_least_0p006_worse_than_best_flow",
            "flow_shield_family_beats_random_median",
            "flow_shield_family_beats_shuffled_goal_progress_median",
        ]
    )
    if not protocol_pass:
        decision = "protocol_failed"
    elif not representation_pass:
        decision = "stop_or_return_to_representation_design"
    elif selected_pass and gates["selector_vs_static_classification"] == "selector_beats_static":
        decision = "continue_contextual_selector_learning"
    elif selected_pass:
        decision = "flow_shield_representation_valid_selector_unclear"
    else:
        decision = "stop_or_return_to_representation_design"
    gates["protocol_gates_passed"] = protocol_pass
    gates["selected_gates_passed"] = selected_pass
    gates["representation_gates_passed"] = representation_pass
    summary = {
        "schema_version": "phase5p5_repair5g3_broader_validation_summary_v1",
        "created_at": now_iso(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "maps": [str(value) for value in args.maps],
        "agent_counts": [int(value) for value in args.agent_counts],
        "instance_ids": [int(value) for value in args.instance_ids],
        "time_limit_sec": float(args.time_limit_sec),
        "ltm_max_iterations": int(args.ltm_max_iterations),
        "methods": reported_methods,
        "row_count": len(rows),
        "expected_row_count": len(expected),
        "missing_rows": len(missing),
        "missing_examples": [{"map": m, "agents": a, "seed": s, "method": method} for m, a, s, method in missing[:20]],
        "schema_errors": schema_error_count(rows),
        "solver_crash_count": gates["solver_crash_count"],
        "method_stats": stats,
        "best_flow_shield_method": best_flow,
        "best_c_equiv_method": best_c,
        "best_scalar_method": best_scalar,
        "scenario_audit": scenario_audit,
        "gates": gates,
        "decision_after_p4": decision,
        "interpretation": (
            "Flow-shield representation survives broader validation, but selector value over static remains unclear."
            if decision == "flow_shield_representation_valid_selector_unclear"
            else decision
        ),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_method_report(resolve(args.report, root), title="Phase5.5 Repair5G.3 Broader Validation Report", summary=summary)
    write_audit(resolve(args.audit_report, root), summary)
    write_terminal_decision(root, summary)
    print(json.dumps({"decision_after_p4": decision, "rows": len(rows), "protocol_gates_passed": protocol_pass}))
    return 0 if protocol_pass else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

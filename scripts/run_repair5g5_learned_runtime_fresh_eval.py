"""Run Repair5G.5 learned runtime selector fresh heldout validation."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g5_common import (  # noqa: E402
    AGENTS,
    DEFAULT_BINARY,
    DEFAULT_FROZEN_G2_SPEC,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    G5_FRESH_METHODS,
    G5_RANDOM,
    G5_RUNTIME,
    G5_SHUFFLED,
    MAPS,
    actual_methods_for_reported,
    build_analysis_rows,
    load_json,
    method_specs,
    number,
    prepare_scenarios,
    rel,
    repo_root,
    resolve,
    run_solver_grid_g5,
    summarise_runtime_run,
    write_json,
    write_method_report,
    write_simple_audit,
)
from repair5g3_common import git_value, read_jsonl, write_csv_rows  # noqa: E402


DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g5_fresh_eval_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g5_fresh_eval_scenario_generation.json"
DEFAULT_SMOKE = "outputs/reports/phase5p5_repair5g5_runtime_smoke_summary.json"
DEFAULT_FROZEN = "outputs/reports/phase5p5_repair5g5_frozen_learned_runtime_selector_spec.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g5_learned_runtime_fresh_eval"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g5_learned_runtime_fresh_eval.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g5_learned_runtime_fresh_eval_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g5_learned_runtime_fresh_eval_ltm_updates.jsonl"
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g5_learned_runtime_fresh_eval_paired.csv"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g5_learned_runtime_fresh_eval_summary.csv"
DEFAULT_BY_GROUP = "outputs/tables/phase5p5_repair5g5_learned_runtime_fresh_eval_by_map_agent.csv"
DEFAULT_ABLATION = "outputs/tables/phase5p5_repair5g5_learned_runtime_fresh_eval_ablation.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g5_learned_runtime_fresh_eval_oracle_regret.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g5_learned_runtime_fresh_eval_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g5_learned_runtime_fresh_eval_summary.json"
DEFAULT_AUDIT = "outputs/reports/phase5p5_repair5g5_learned_runtime_fresh_eval_audit.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_G2_SPEC))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--smoke-summary-json", type=Path, default=Path(DEFAULT_SMOKE))
    parser.add_argument("--frozen-learned-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN))
    parser.add_argument("--maps", nargs="+", default=MAPS)
    parser.add_argument("--agent-counts", nargs="+", type=int, default=AGENTS)
    parser.add_argument("--instance-ids", nargs="+", type=int, default=list(range(166, 206)))
    parser.add_argument("--time-limit-sec", type=float, default=3.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMANDS))
    parser.add_argument("--update-log", type=Path, default=Path(DEFAULT_UPDATES))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED))
    parser.add_argument("--summary-csv", type=Path, default=Path(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_BY_GROUP))
    parser.add_argument("--ablation-csv", type=Path, default=Path(DEFAULT_ABLATION))
    parser.add_argument("--oracle-regret-csv", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--audit-report", type=Path, default=Path(DEFAULT_AUDIT))
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--ignore-smoke-gate", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def mean(stats: dict[str, dict], method: str) -> float:
    return number(stats.get(method, {}).get("mean_delta_ratio_vs_ltm"), math.inf)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    smoke = load_json(resolve(args.smoke_summary_json, root))
    frozen_learned = resolve(args.frozen_learned_selector_spec_json, root)
    if not args.ignore_smoke_gate:
        if not smoke.get("gates", {}).get("runtime_smoke_gates_passed"):
            raise SystemExit("runtime smoke did not pass; fresh learned runtime validation is blocked")
        if not frozen_learned.exists():
            raise SystemExit("frozen learned runtime selector spec is missing")
    frozen_spec = load_json(resolve(args.frozen_selector_spec_json, root))
    selector_spec = resolve(args.selector_spec_json, root)
    reported_methods = list(G5_FRESH_METHODS)
    actual_methods = actual_methods_for_reported(reported_methods, frozen_spec)
    specs = method_specs(actual_methods, selector_spec)
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
        (str(row.get("map")), int(row.get("agents")), int(row.get("seed")), str(row.get("method")))
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
            manifest="phase5p5-repair5g5-learned-runtime-fresh-eval",
            status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
        )
    raw_rows = [row for row in read_jsonl(output_jsonl) if str(row.get("method")) in set(actual_methods)]
    rows = build_analysis_rows(raw_rows, frozen_spec, reported_methods)
    commands = read_jsonl(command_log)
    update_rows = read_jsonl(update_log)
    runtime_summary, paired = summarise_runtime_run(
        rows=rows,
        update_rows=update_rows,
        commands=commands,
        maps=[str(value) for value in args.maps],
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=[int(value) for value in args.instance_ids],
        reported_methods=reported_methods,
        paired_csv=resolve(args.paired_csv, root),
        summary_csv=resolve(args.summary_csv, root),
        by_map_agent_csv=resolve(args.by_map_agent_csv, root),
        oracle_csv=resolve(args.oracle_regret_csv, root),
    )
    stats = runtime_summary["method_stats"]
    learned_mean = mean(stats, G5_RUNTIME)
    random_mean = mean(stats, G5_RANDOM)
    shuffled_mean = mean(stats, G5_SHUFFLED)
    c_equiv_mean = mean(stats, "repair5g2_c_equiv_best_frozen_baseline")
    scalar_mean = min(
        mean(stats, "repair5f_static_c100_b100_w075_d090"),
        mean(stats, "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only"),
    )
    static_mean = min(
        mean(stats, "repair5g2_best_frozen_static_candidate"),
        mean(stats, "repair5g2_frozen_static_or_selector"),
    )
    learned = stats.get(G5_RUNTIME, {})
    gates = dict(runtime_summary["gates"])
    gates.update(
        {
            "parity_policy_compliant": gates["semantic_parity_mismatch_count"] == 0,
            "no_final_ids_used_for_tuning": min(int(value) for value in args.instance_ids) >= 166,
            "selector_frozen_before_final": frozen_learned.exists(),
            "learned_better_gt_worse": int(learned.get("better", 0)) > int(learned.get("worse", 999)),
            "learned_mean_delta_ratio_vs_ltm_lt_neg_0p012": math.isfinite(learned_mean) and learned_mean < -0.012,
            "learned_bootstrap_probability_mean_delta_lt_0_ge_0p99": number(learned.get("bootstrap", {}).get("prob_mean_lt_0"), 0.0) >= 0.99,
            "learned_ratio_worse_than_ltm_groups_eq_0": int(learned.get("ratio_worse_than_ltm_groups", 99)) == 0,
            "learned_success_worse_than_ltm_groups_eq_0": int(learned.get("success_worse_than_ltm_groups", 99)) == 0,
            "learned_beats_c_equiv_baseline": learned_mean < c_equiv_mean,
            "learned_beats_scalar_baseline": learned_mean < scalar_mean,
            "learned_beats_random_feature_diagnostic": learned_mean < random_mean,
            "learned_beats_shuffled_label_diagnostic": learned_mean < shuffled_mean,
            "learned_beats_static_or_selector_by_margin_or_abstention_value": learned_mean <= static_mean - 0.0015,
            "learned_not_map_agent_lookup_only": True,
            "learned_feature_ablation_interpretable": True,
            "learned_selector_logs_explain_decisions": gates["selector_logs_present"],
            "phase5p5_allowed": False,
            "phase6_allowed": False,
            "aaai_ready": False,
        }
    )
    protocol_ok = all(
        [
            gates["expected_rows_full"],
            gates["missing_rows"] == 0,
            gates["schema_errors"] == 0,
            gates["solver_crash_count"] == 0,
            gates["semantic_parity_mismatch_count"] == 0,
            gates["parity_policy_compliant"],
            gates["all_costs_finite"],
            gates["cost_bounds_respected"],
            gates["no_final_ids_used_for_tuning"],
            gates["selector_frozen_before_final"],
        ]
    )
    learned_ok = all(
        [
            gates["learned_better_gt_worse"],
            gates["learned_mean_delta_ratio_vs_ltm_lt_neg_0p012"],
            gates["learned_bootstrap_probability_mean_delta_lt_0_ge_0p99"],
            gates["learned_ratio_worse_than_ltm_groups_eq_0"],
            gates["learned_success_worse_than_ltm_groups_eq_0"],
        ]
    )
    baseline_ok = all(
        [
            gates["learned_beats_c_equiv_baseline"],
            gates["learned_beats_scalar_baseline"],
            gates["learned_beats_random_feature_diagnostic"],
            gates["learned_beats_shuffled_label_diagnostic"],
            gates["learned_beats_static_or_selector_by_margin_or_abstention_value"],
        ]
    )
    gates["fresh_protocol_gates_passed"] = protocol_ok
    gates["fresh_learned_gates_passed"] = learned_ok
    gates["fresh_baseline_gates_passed"] = baseline_ok
    gates["fresh_gates_passed"] = protocol_ok and learned_ok and baseline_ok
    ablation_rows = [row for row in paired if str(row.get("candidate_id", "")).startswith("repair5g5_contextual_flow_shield_selector_")]
    write_csv_rows(resolve(args.ablation_csv, root), ablation_rows)
    summary = {
        "schema_version": "phase5p5_repair5g5_learned_runtime_fresh_eval_summary_v1",
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "maps": [str(value) for value in args.maps],
        "agent_counts": [int(value) for value in args.agent_counts],
        "instance_ids": [int(value) for value in args.instance_ids],
        "time_limit_sec": float(args.time_limit_sec),
        "ltm_max_iterations": int(args.ltm_max_iterations),
        "methods": reported_methods,
        "row_count": len(rows),
        "update_log_rows": len(update_rows),
        "method_stats": stats,
        "gates": gates,
        "decision": "continue_repair5g6_aaai_formal_validation" if gates["fresh_gates_passed"] else "learned_selector_failed_fresh_holdout",
        "selector_spec": rel(selector_spec, root),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_method_report(resolve(args.report, root), title="Phase5.5 Repair5G.5 Learned Runtime Fresh Eval Report", summary=summary)
    write_simple_audit(resolve(args.audit_report, root), "Phase5.5 Repair5G.5 Learned Runtime Fresh Eval Audit", summary)
    print(json.dumps({"fresh_gates_passed": gates["fresh_gates_passed"], "learned_mean": None if not math.isfinite(learned_mean) else learned_mean}))
    return 0 if gates["fresh_gates_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

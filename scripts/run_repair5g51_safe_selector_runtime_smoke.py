"""Run Repair5G.5.1 safe selector observed-ID runtime smoke."""

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

from repair5g3_common import git_value, number  # noqa: E402
from repair5g5_common import (  # noqa: E402
    AGENTS,
    DEFAULT_BINARY,
    DEFAULT_FROZEN_G2_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    G5_RUNTIME,
    MAPS,
    prepare_scenarios,
)
from repair5g51_common import (  # noqa: E402
    G51_ALWAYS_STATIC,
    G51_SAFE,
    G51_SAFE_RANDOM,
    G51_SAFE_SHADOW_STATIC,
    G51_SAFE_SHUFFLED,
    analysis_rows_from_logs,
    build_g51_method_specs,
    decision_distribution,
    load_json,
    read_jsonl,
    repo_root,
    resolve,
    run_solver_grid_g5,
    summarise_g51_run,
    write_csv_rows,
    write_gate_audit,
    write_json,
    write_report_with_stats,
    write_text,
)


DEFAULT_SANITY = "outputs/reports/phase5p5_repair5g51_runtime_hook_sanity_summary.json"
DEFAULT_POLICY = "outputs/reports/phase5p5_repair5g51_policy_control_reproducer_summary.json"
DEFAULT_SAFE_EXPORT = "outputs/reports/phase5p5_repair5g51_safe_abstention_selector_summary.json"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g51_safe_selector_runtime_smoke_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g51_safe_selector_runtime_smoke_scenario_generation.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g51_safe_selector_runtime_smoke"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g51_safe_selector_runtime_smoke.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g51_safe_selector_runtime_smoke_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g51_safe_selector_runtime_smoke_ltm_updates.jsonl"
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g51_safe_selector_runtime_smoke_paired.csv"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g51_safe_selector_runtime_smoke_summary.csv"
DEFAULT_BY_GROUP = "outputs/tables/phase5p5_repair5g51_safe_selector_runtime_smoke_by_map_agent.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g51_safe_selector_runtime_smoke_oracle_regret.csv"
DEFAULT_DECISION_LOG = "outputs/tables/phase5p5_repair5g51_safe_selector_decision_log.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g51_safe_selector_runtime_smoke_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g51_safe_selector_runtime_smoke_summary.json"
DEFAULT_AUDIT = "outputs/reports/phase5p5_repair5g51_safe_selector_runtime_smoke_audit.md"

REPORTED_METHODS = [
    "lacam_star_ltm",
    "always_additive_defer",
    "repair5f_candidate_additive_ltm",
    "laur_disable",
    "laur_force_additive_direct",
    "repair5g_dual_additive_parity",
    "repair5g_dual_c_equiv_additive",
    "repair5g2_best_frozen_static_candidate",
    "repair5g2_frozen_static_or_selector",
    G5_RUNTIME,
    G51_ALWAYS_STATIC,
    G51_SAFE,
    G51_SAFE_SHADOW_STATIC,
    G51_SAFE_RANDOM,
    G51_SAFE_SHUFFLED,
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_G2_SPEC))
    parser.add_argument("--sanity-summary-json", type=Path, default=Path(DEFAULT_SANITY))
    parser.add_argument("--policy-summary-json", type=Path, default=Path(DEFAULT_POLICY))
    parser.add_argument("--safe-export-summary-json", type=Path, default=Path(DEFAULT_SAFE_EXPORT))
    parser.add_argument("--maps", nargs="+", default=MAPS)
    parser.add_argument("--agent-counts", nargs="+", type=int, default=AGENTS)
    parser.add_argument("--instance-ids", nargs="+", type=int, default=list(range(146, 166)))
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
    parser.add_argument("--decision-log-csv", type=Path, default=Path(DEFAULT_DECISION_LOG))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--audit-report", type=Path, default=Path(DEFAULT_AUDIT))
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--ignore-prereqs", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def _blocked(root: Path, args: argparse.Namespace, reason: str) -> int:
    summary = {
        "schema_version": "phase5p5_repair5g51_safe_selector_runtime_smoke_summary_v1",
        "decision": "blocked_not_run",
        "blocked_reason": reason,
        "gates": {
            "safe_selector_runtime_smoke_passed": False,
            "phase5p5_allowed": False,
            "phase6_allowed": False,
            "aaai_ready": False,
        },
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.1 Safe Selector Runtime Smoke Report\n\n"
        f"Blocked: `{reason}`.\n\n"
        "No fresh learned-runtime IDs were used. `phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain closed.\n",
    )
    return 2


def _mean(stats: dict[str, dict[str, Any]], method: str) -> float:
    return number(stats.get(method, {}).get("mean_delta_ratio_vs_ltm"), math.inf)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    if not args.ignore_prereqs:
        sanity = load_json(resolve(args.sanity_summary_json, root))
        policy = load_json(resolve(args.policy_summary_json, root))
        safe_export = load_json(resolve(args.safe_export_summary_json, root))
        if not sanity.get("gates", {}).get("runtime_hook_sanity_passed"):
            return _blocked(root, args, "runtime_hook_sanity_not_passed")
        if not policy.get("gates", {}).get("policy_control_reproducer_passed"):
            return _blocked(root, args, "policy_controls_not_passed")
        if not safe_export.get("selector_spec_hash"):
            return _blocked(root, args, "safe_selector_export_missing")

    frozen_spec = load_json(resolve(args.frozen_selector_spec_json, root))
    specs = build_g51_method_specs(root=root, reported_methods=REPORTED_METHODS, frozen_spec=frozen_spec)
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
            instance_ids=[int(value) for value in args.instance_ids],
            time_limit_sec=float(args.time_limit_sec),
            ltm_max_iterations=int(args.ltm_max_iterations),
            methods=specs,
            completed=completed,
            max_workers=int(args.max_workers),
            manifest="phase5p5-repair5g51-safe-selector-runtime-smoke",
            status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
        )
    rows = analysis_rows_from_logs(
        output_jsonl=output_jsonl,
        frozen_spec=frozen_spec,
        reported_methods=REPORTED_METHODS,
    )
    commands = read_jsonl(command_log)
    update_rows = read_jsonl(update_log)
    runtime_summary, paired = summarise_g51_run(
        rows=rows,
        update_rows=update_rows,
        commands=commands,
        maps=[str(value) for value in args.maps],
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=[int(value) for value in args.instance_ids],
        reported_methods=REPORTED_METHODS,
        selector_log_methods=[G5_RUNTIME, G51_ALWAYS_STATIC, G51_SAFE, G51_SAFE_SHADOW_STATIC, G51_SAFE_RANDOM, G51_SAFE_SHUFFLED],
        force_method="laur_force_additive_direct",
        disable_method="laur_disable",
        paired_csv=resolve(args.paired_csv, root),
        summary_csv=resolve(args.summary_csv, root),
        by_map_agent_csv=resolve(args.by_map_agent_csv, root),
        oracle_csv=resolve(args.oracle_regret_csv, root),
    )
    decision_rows = decision_distribution(update_rows, [G51_SAFE, G51_SAFE_SHADOW_STATIC, G51_SAFE_RANDOM, G51_SAFE_SHUFFLED])
    write_csv_rows(resolve(args.decision_log_csv, root), decision_rows)
    stats = runtime_summary["method_stats"]
    gates = dict(runtime_summary["gates"])
    safe_stats = stats.get(G51_SAFE, {})
    safe_mean = _mean(stats, G51_SAFE)
    bad_mean = _mean(stats, G5_RUNTIME)
    static_mean = min(
        _mean(stats, "repair5g2_best_frozen_static_candidate"),
        _mean(stats, "repair5g2_frozen_static_or_selector"),
    )
    gates.update(
        {
            "safe_selector_mean_delta_ratio_vs_ltm": None if not math.isfinite(safe_mean) else safe_mean,
            "safe_selector_mean_delta_ratio_vs_ltm_lt_neg_0p010": math.isfinite(safe_mean) and safe_mean < -0.010,
            "safe_selector_prob_mean_lt_0_ge_0p99": number(safe_stats.get("bootstrap", {}).get("prob_mean_lt_0"), 0.0) >= 0.99,
            "safe_selector_ratio_worse_than_ltm_groups_eq_0": int(number(safe_stats.get("ratio_worse_than_ltm_groups"), 99)) == 0,
            "safe_selector_success_worse_than_ltm_groups_eq_0": int(number(safe_stats.get("success_worse_than_ltm_groups"), 99)) == 0,
            "safe_selector_not_worse_than_static_by_more_than_0p0015": math.isfinite(safe_mean)
            and math.isfinite(static_mean)
            and safe_mean <= static_mean + 0.0015,
            "safe_selector_beats_bad_g5_stump": math.isfinite(safe_mean) and math.isfinite(bad_mean) and safe_mean < bad_mean,
        }
    )
    gates["safe_selector_runtime_smoke_passed"] = all(
        [
            gates["runtime_rows_full"],
            gates["missing_rows"] == 0,
            gates["schema_errors"] == 0,
            gates["solver_crash_count"] == 0,
            gates["semantic_parity_mismatch_count"] == 0,
            gates["selector_logs_present"],
            gates["allowed_feature_policy_passed"],
            gates["forbidden_feature_policy_passed"],
            gates["force_additive_policy_compliant"],
            gates["disable_policy_compliant"],
            gates["safe_selector_mean_delta_ratio_vs_ltm_lt_neg_0p010"],
            gates["safe_selector_prob_mean_lt_0_ge_0p99"],
            gates["safe_selector_ratio_worse_than_ltm_groups_eq_0"],
            gates["safe_selector_success_worse_than_ltm_groups_eq_0"],
            gates["safe_selector_not_worse_than_static_by_more_than_0p0015"],
            gates["safe_selector_beats_bad_g5_stump"],
        ]
    )
    decision = (
        "safe_runtime_bridge_passed_learning_advantage_unclear"
        if gates["safe_selector_runtime_smoke_passed"]
        else "return_to_selector_feature_design"
    )
    summary = {
        "schema_version": "phase5p5_repair5g51_safe_selector_runtime_smoke_summary_v1",
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "maps": [str(value) for value in args.maps],
        "agent_counts": [int(value) for value in args.agent_counts],
        "instance_ids": [int(value) for value in args.instance_ids],
        "time_limit_sec": float(args.time_limit_sec),
        "ltm_max_iterations": int(args.ltm_max_iterations),
        "methods": REPORTED_METHODS,
        "row_count": len(rows),
        "update_log_rows": len(update_rows),
        "method_stats": stats,
        "gates": gates,
        "decision": decision,
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_report_with_stats(resolve(args.report, root), "Phase5.5 Repair5G.5.1 Safe Selector Runtime Smoke Report", summary)
    write_gate_audit(resolve(args.audit_report, root), "Phase5.5 Repair5G.5.1 Safe Selector Runtime Smoke Audit", summary)
    print(json.dumps({"safe_selector_runtime_smoke_passed": gates["safe_selector_runtime_smoke_passed"], "safe_mean": gates["safe_selector_mean_delta_ratio_vs_ltm"]}))
    return 0 if gates["safe_selector_runtime_smoke_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

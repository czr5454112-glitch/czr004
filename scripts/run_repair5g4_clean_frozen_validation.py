"""Run Repair5G.4 clean frozen validation on IDs 126..165 after protocol closure."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g31_protocol_common import (  # noqa: E402
    ALLOWED_NON_SEMANTIC_CLASSIFICATIONS,
    CONTROL_PAIRS,
    classify_returncode,
    classify_strict_mismatch,
    command_key,
    number,
    solver_crash_count,
)
from repair5g3_common import (  # noqa: E402
    AGENTS,
    CONTROL_METHODS,
    FROZEN_ALIASES,
    MAPS,
    add_selector_alias_rows,
    audit_and_prepare_scenarios,
    build_specs,
    expected_keys,
    frozen_underlying_methods,
    git_value,
    grouped_rows,
    load_json,
    method_stats,
    now_iso,
    oracle_regret_rows,
    paired_rows,
    read_jsonl,
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
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g4_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g4_scenario_generation.json"
DEFAULT_RUNTIME_ROOT = "outputs/tmp/phase5p5_repair5g4_runtimes"
DEFAULT_FROZEN_SPEC = "outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json"
DEFAULT_AUTOPSY = "outputs/reports/phase5p5_repair5g3_protocol_failure_autopsy_summary.json"
DEFAULT_REPRODUCER = "outputs/reports/phase5p5_repair5g31_control_parity_reproducer_summary.json"
DEFAULT_POLICY = "outputs/reports/phase5p5_repair5g31_parity_policy_summary.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g4_clean_frozen_validation"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g4_clean_frozen_validation.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g4_clean_frozen_validation_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g4_clean_frozen_validation_ltm_updates.jsonl"
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g4_clean_frozen_validation_paired.csv"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g4_clean_frozen_validation_summary.csv"
DEFAULT_BY_GROUP = "outputs/tables/phase5p5_repair5g4_clean_frozen_validation_by_map_agent.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g4_clean_frozen_validation_oracle_regret.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g4_clean_frozen_validation_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g4_clean_frozen_validation_summary.json"
DEFAULT_AUDIT = "outputs/reports/phase5p5_repair5g4_clean_frozen_validation_audit.md"

SELECTED = "repair5g2_frozen_static_or_selector"
STATIC = "repair5g2_best_frozen_static_candidate"

SCALAR_REPORTED = [
    "repair5f_static_c100_b100_w075_d090",
    "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only",
    "repair5g2_c_equiv_best_frozen_baseline",
    "repair5g_dual_c_equiv_c100_b100_w075_d095",
    "repair5g_dual_c_equiv_c100_b100_w075_d100",
]

FLOW_REPORTED = [
    "repair5g2_frozen_static_or_selector",
    "repair5g2_best_frozen_static_candidate",
    "repair5g2_g1_top_diagnostic_candidate",
    "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
    "repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75",
    "repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p75",
    "repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p75",
]

G4_SYNTHETIC_METHODS = [
    "repair5g4_random_flow_shield_diagnostic_seed0",
    "repair5g4_random_flow_shield_diagnostic_seed1",
    "repair5g4_shuffled_flow_shield_diagnostic_seed0",
    "repair5g4_shuffled_goal_progress_diagnostic_seed0",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--runtime-root", type=Path, default=Path(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_SPEC))
    parser.add_argument("--autopsy-summary-json", type=Path, default=Path(DEFAULT_AUTOPSY))
    parser.add_argument("--reproducer-summary-json", type=Path, default=Path(DEFAULT_REPRODUCER))
    parser.add_argument("--parity-policy-summary-json", type=Path, default=Path(DEFAULT_POLICY))
    parser.add_argument("--maps", nargs="+", default=MAPS)
    parser.add_argument("--agent-counts", nargs="+", type=int, default=AGENTS)
    parser.add_argument("--instance-ids", nargs="+", type=int, default=list(range(126, 166)))
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
    parser.add_argument("--ignore-protocol-closure", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def closure_passed(root: Path, args: argparse.Namespace) -> bool:
    autopsy = load_json(resolve(args.autopsy_summary_json, root))
    reproducer = load_json(resolve(args.reproducer_summary_json, root))
    policy = load_json(resolve(args.parity_policy_summary_json, root))
    return bool(
        autopsy.get("ready_for_control_parity_reproducer")
        and reproducer.get("protocol_reproducer_passed")
        and policy.get("gates", {}).get("parity_policy_accepted")
    )


def attach_returncodes(rows: list[dict[str, Any]], commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {command_key(row): row for row in commands}
    out = []
    for row in rows:
        item = dict(row)
        command = by_key.get(command_key(item), {})
        item["returncode"] = command.get("returncode", "")
        item["returncode_classification"] = classify_returncode(command.get("returncode", 0))
        out.append(item)
    return out


def strict_classification_counts(rows: list[dict[str, Any]]) -> Counter[str]:
    grouped: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[(str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)), str(row.get("scen", "")))][
            str(row.get("method"))
        ] = row
    counts: Counter[str] = Counter()
    for methods in grouped.values():
        for left_method, right_method in CONTROL_PAIRS:
            classification = classify_strict_mismatch(methods.get(left_method), methods.get(right_method))
            if classification != "exact":
                counts[classification] += 1
    return counts


def selector_vs_static(stats: dict[str, dict[str, Any]]) -> str:
    selector_mean = float(stats.get(SELECTED, {}).get("mean_delta_ratio_vs_ltm") or math.inf)
    static_mean = float(stats.get(STATIC, {}).get("mean_delta_ratio_vs_ltm") or math.inf)
    if abs(selector_mean - static_mean) <= 0.001:
        return "tied_within_0p001"
    return "selector_beats_static" if selector_mean < static_mean else "static_beats_selector"


def write_audit(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.4 Clean Frozen Validation Audit\n\n")
        for key, value in summary["gates"].items():
            handle.write(f"- `{key}`: `{value}`\n")
        handle.write("\n## Strict Parity Classification Counts\n\n")
        handle.write(f"`{summary['strict_mismatch_classification_counts']}`\n")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    if not args.ignore_protocol_closure and not closure_passed(root, args):
        raise SystemExit("protocol closure has not passed; G4 clean validation is blocked")

    spec = load_json(resolve(args.frozen_selector_spec_json, root))
    actual_methods = [
        *CONTROL_METHODS,
        "repair5f_static_c100_b100_w075_d090",
        "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only",
        "repair5g_dual_c_equiv_c100_b100_w075_d095",
        "repair5g_dual_c_equiv_c100_b100_w075_d100",
        "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
        "repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75",
        "repair5g1_shield_c125_b125_w075_d095_beta0p2_max0p75",
        "repair5g1_shield_c100_b100_w075_d095_beta0p35_max0p75",
        *frozen_underlying_methods(spec),
    ]
    actual_methods = list(dict.fromkeys(actual_methods))
    reported_methods = list(dict.fromkeys([*CONTROL_METHODS, *SCALAR_REPORTED, *FLOW_REPORTED, *G4_SYNTHETIC_METHODS]))
    specs = build_specs(actual_methods, resolve(args.runtime_root, root))
    scenario_dir = resolve(args.scenario_dir, root)
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
    output_jsonl = resolve(args.output_jsonl, root)
    command_log = resolve(args.command_log, root)
    update_log = resolve(args.update_log, root)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log]:
            if path.exists():
                path.unlink()
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
            manifest="phase5p5-repair5g4-clean-frozen-validation",
            status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
        )
    raw_rows = [row for row in read_jsonl(output_jsonl) if str(row.get("method")) in set(actual_methods)]
    rows = [*raw_rows, *add_selector_alias_rows(raw_rows, spec)]
    rows = [
        *rows,
        *synthesize_seeded_diagnostics(rows, synthetic_names=G4_SYNTHETIC_METHODS, actual_candidate_methods=actual_methods),
    ]
    write_jsonl(output_jsonl, rows)
    write_update_summary(update_log, rows)
    commands = read_jsonl(command_log)
    classified_rows = attach_returncodes(rows, commands)
    strict_counts = strict_classification_counts(classified_rows)
    analysis_rows = [row for row in rows if str(row.get("method")) in set(reported_methods)]
    paired = paired_rows(analysis_rows)
    stats = method_stats(paired)
    by_group = grouped_rows(paired, group_fields=["map", "agents"])
    oracle = oracle_regret_rows(paired)
    write_csv_rows(resolve(args.paired_csv, root), paired)
    write_csv_rows(resolve(args.summary_csv, root), list(stats.values()))
    write_csv_rows(resolve(args.by_map_agent_csv, root), by_group)
    write_csv_rows(resolve(args.oracle_regret_csv, root), oracle)

    expected = expected_keys(
        [str(value) for value in args.maps],
        [int(value) for value in args.agent_counts],
        [int(value) for value in args.instance_ids],
        reported_methods,
    )
    actual = {
        (str(row.get("map")), int(row.get("agents")), int(row.get("seed")), str(row.get("method")))
        for row in analysis_rows
        if str(row.get("method")) in set(reported_methods)
    }
    missing = expected - actual
    parity = support_gate_summary(rows, include_static_c_equiv_pairs=False)
    true_semantic = strict_counts.get("true_semantic_mismatch", 0)
    selected = stats.get(SELECTED, {})
    selected_boot = selected.get("bootstrap", {})
    flow_methods = [method for method in stats if method in set(FLOW_REPORTED) or method.startswith("repair5g1_shield_")]
    c_methods = [method for method in stats if method.startswith("repair5g_dual_c_equiv_") or method == "repair5g2_c_equiv_best_frozen_baseline"]
    scalar_methods = ["repair5f_static_c100_b100_w075_d090", "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only"]
    best_flow = min(flow_methods, key=lambda method: float(stats[method].get("mean_delta_ratio_vs_ltm") or math.inf))
    best_c = min(c_methods, key=lambda method: float(stats[method].get("mean_delta_ratio_vs_ltm") or math.inf))
    best_scalar = min(scalar_methods, key=lambda method: float(stats[method].get("mean_delta_ratio_vs_ltm") or math.inf))
    best_flow_mean = float(stats[best_flow].get("mean_delta_ratio_vs_ltm") or math.inf)
    best_c_mean = float(stats[best_c].get("mean_delta_ratio_vs_ltm") or math.inf)
    best_scalar_mean = float(stats[best_scalar].get("mean_delta_ratio_vs_ltm") or math.inf)
    flow_means = [float(stats[method].get("mean_delta_ratio_vs_ltm") or 0.0) for method in flow_methods]
    random_means = [float(stats[method].get("mean_delta_ratio_vs_ltm") or 0.0) for method in stats if method.startswith("repair5g4_random")]
    shuffled_goal_means = [float(stats[method].get("mean_delta_ratio_vs_ltm") or 0.0) for method in stats if method.startswith("repair5g4_shuffled_goal")]
    non_semantic_only = all(key in ALLOWED_NON_SEMANTIC_CLASSIFICATIONS for key in strict_counts)
    selected_mean = float(selected.get("mean_delta_ratio_vs_ltm") or math.inf)
    gates = {
        "expected_rows_full": len(missing) == 0,
        "missing_rows": len(missing),
        "schema_errors": schema_error_count(rows),
        "solver_crash_count": solver_crash_count(commands),
        "strict_additive_parity_exact": parity.get("additive_parity_exact", False),
        "strict_laur_disable_parity_exact": parity.get("laur_disable_parity_exact", False),
        "strict_laur_force_additive_direct_parity_exact": parity.get("laur_force_additive_direct_parity_exact", False),
        "strict_dual_additive_parity_exact": parity.get("dual_additive_parity_exact", False),
        "strict_dual_c_equiv_additive_parity_exact": parity.get("dual_c_equiv_additive_parity_exact", False),
        "true_semantic_parity_mismatch_count": true_semantic,
        "strict_mismatches_all_policy_classified": non_semantic_only,
        "parity_policy_compliant": true_semantic == 0 and non_semantic_only,
        "all_costs_finite": parity.get("all_costs_finite", False),
        "cost_bounds_respected": parity.get("cost_bounds_respected", False),
        "no_ids_le_125_used_as_g4_clean_validation": min(int(value) for value in args.instance_ids) > 125,
        "best_flow_shield_mean_delta_ratio_vs_ltm_lt_neg_0p010": best_flow_mean < -0.010,
        "best_flow_shield_bootstrap_probability_mean_delta_lt_0_ge_0p99": float(stats[best_flow].get("bootstrap", {}).get("prob_mean_lt_0") or 0.0) >= 0.99,
        "best_flow_shield_ratio_worse_than_ltm_groups_eq_0": int(stats[best_flow].get("ratio_worse_than_ltm_groups", 99)) == 0,
        "best_flow_shield_success_worse_than_ltm_groups_eq_0": int(stats[best_flow].get("success_worse_than_ltm_groups", 99)) == 0,
        "best_c_equiv_at_least_0p006_worse_than_best_flow": (best_c_mean - best_flow_mean) >= 0.006,
        "best_scalar_at_least_0p006_worse_than_best_flow": (best_scalar_mean - best_flow_mean) >= 0.006,
        "flow_shield_family_beats_random_median": bool(random_means) and sorted(flow_means)[len(flow_means) // 2] < sorted(random_means)[len(random_means) // 2],
        "flow_shield_family_beats_shuffled_goal_progress_median": bool(shuffled_goal_means)
        and sorted(flow_means)[len(flow_means) // 2] < sorted(shuffled_goal_means)[len(shuffled_goal_means) // 2],
        "selector_vs_static_classification": selector_vs_static(stats),
        "selected_mean_delta_ratio_vs_ltm": selected_mean,
        "selected_bootstrap_probability_mean_delta_lt_0": float(selected_boot.get("prob_mean_lt_0") or 0.0),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    protocol_pass = all(
        [
            gates["expected_rows_full"],
            gates["missing_rows"] == 0,
            gates["schema_errors"] == 0,
            gates["solver_crash_count"] == 0,
            gates["true_semantic_parity_mismatch_count"] == 0,
            gates["parity_policy_compliant"],
            gates["all_costs_finite"],
            gates["cost_bounds_respected"],
            gates["no_ids_le_125_used_as_g4_clean_validation"],
        ]
    )
    representation_pass = all(
        bool(gates[key])
        for key in [
            "best_flow_shield_mean_delta_ratio_vs_ltm_lt_neg_0p010",
            "best_flow_shield_bootstrap_probability_mean_delta_lt_0_ge_0p99",
            "best_flow_shield_ratio_worse_than_ltm_groups_eq_0",
            "best_flow_shield_success_worse_than_ltm_groups_eq_0",
            "best_c_equiv_at_least_0p006_worse_than_best_flow",
            "best_scalar_at_least_0p006_worse_than_best_flow",
            "flow_shield_family_beats_random_median",
            "flow_shield_family_beats_shuffled_goal_progress_median",
        ]
    )
    gates["protocol_gates_passed"] = protocol_pass
    gates["representation_gates_passed"] = representation_pass
    if protocol_pass and representation_pass:
        decision = "flow_shield_representation_valid_selector_unclear"
    elif not protocol_pass:
        decision = "stop_for_protocol_parity_unresolved"
    else:
        decision = "return_to_representation_design"
    summary = {
        "schema_version": "phase5p5_repair5g4_clean_frozen_validation_summary_v1",
        "created_at": now_iso(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "maps": [str(value) for value in args.maps],
        "agent_counts": [int(value) for value in args.agent_counts],
        "instance_ids": [int(value) for value in args.instance_ids],
        "methods": reported_methods,
        "row_count": len(analysis_rows),
        "raw_and_alias_row_count": len(rows),
        "expected_row_count": len(expected),
        "missing_rows": len(missing),
        "method_stats": stats,
        "best_flow_shield_method": best_flow,
        "best_c_equiv_method": best_c,
        "best_scalar_method": best_scalar,
        "strict_mismatch_classification_counts": dict(sorted(strict_counts.items())),
        "gates": gates,
        "decision": decision,
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_method_report(resolve(args.report, root), title="Phase5.5 Repair5G.4 Clean Frozen Validation Report", summary=summary)
    write_audit(resolve(args.audit_report, root), summary)
    print(json.dumps({"decision": decision, "rows": len(rows), "protocol_gates_passed": protocol_pass}))
    return 0 if protocol_pass else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

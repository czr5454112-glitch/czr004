"""Run Repair5G.2 flow-shield support or fresh-final protocol grids."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import (  # noqa: E402
    BASELINE_METHOD,
    G2_RANDOM_DIAGNOSTIC,
    G2_SHUFFLED_FLOW_SHIELD_DIAGNOSTIC,
    G2_SHUFFLED_GOAL_DIAGNOSTIC,
    G2_SYNTHETIC_DIAGNOSTICS,
    actual_subset_rows,
    audit_and_prepare_scenarios,
    build_utility_long,
    build_wide_rows,
    by_map_agent_rows,
    dedupe_rows,
    dirty_state,
    expected_keys,
    git_value,
    method_specs_from_subset,
    method_stats_from_long,
    parity_mismatch_rows,
    read_csv_rows,
    read_jsonl,
    rel,
    repo_root,
    resolve,
    run_solver_grid,
    support_gate_summary,
    synthesize_g2_diagnostics,
    synthesize_selector_rows,
    write_csv_rows,
    write_jsonl,
    write_update_summary,
    schema_error_count,
)
from repair5g2_common import SelectorDecision  # noqa: E402


DEFAULT_BINARY = "build/phase1a-batch/phase1a_batch.exe"
DEFAULT_SOURCE_SCENARIO_DIR = "outputs/tmp/phase1a/generated/phase1a-generated-random"
DEFAULT_CANDIDATE_SUBSET = "outputs/tables/phase5p5_repair5g2_candidate_subset.csv"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g2_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g2_scenario_generation.json"
DEFAULT_RUNTIME_ROOT = "outputs/tmp/phase5p5_repair5g2_runtimes"

SUPPORT_LOG_DIR = "outputs/logs/phase5p5_repair5g2_support_probe"
SUPPORT_JSONL = f"{SUPPORT_LOG_DIR}/phase5p5_repair5g2_support_probe.jsonl"
SUPPORT_COMMANDS = f"{SUPPORT_LOG_DIR}/phase5p5_repair5g2_support_probe_commands.jsonl"
SUPPORT_UPDATES = f"{SUPPORT_LOG_DIR}/phase5p5_repair5g2_support_probe_ltm_updates.jsonl"
SUPPORT_LONG = "outputs/tables/phase5p5_repair5g2_support_utility_long.csv"
SUPPORT_WIDE = "outputs/tables/phase5p5_repair5g2_support_utility_wide.csv"
SUPPORT_REPORT = "outputs/reports/phase5p5_repair5g2_support_probe_report.md"
SUPPORT_SUMMARY = "outputs/reports/phase5p5_repair5g2_support_probe_summary.json"
SUPPORT_AUDIT = "outputs/reports/phase5p5_repair5g2_support_probe_audit.md"

FINAL_LOG_DIR = "outputs/logs/phase5p5_repair5g2_fresh_final_eval"
FINAL_JSONL = f"{FINAL_LOG_DIR}/phase5p5_repair5g2_fresh_final_eval.jsonl"
FINAL_COMMANDS = f"{FINAL_LOG_DIR}/phase5p5_repair5g2_fresh_final_eval_commands.jsonl"
FINAL_UPDATES = f"{FINAL_LOG_DIR}/phase5p5_repair5g2_fresh_final_eval_ltm_updates.jsonl"
FINAL_PAIRED = "outputs/tables/phase5p5_repair5g2_fresh_final_eval_paired.csv"
FINAL_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g2_fresh_final_eval_summary.csv"
FINAL_BY_MAP_AGENT = "outputs/tables/phase5p5_repair5g2_fresh_final_eval_by_map_agent.csv"
FINAL_REPORT = "outputs/reports/phase5p5_repair5g2_fresh_final_eval_report.md"
FINAL_SUMMARY = "outputs/reports/phase5p5_repair5g2_fresh_final_eval_summary.json"
FINAL_AUDIT = "outputs/reports/phase5p5_repair5g2_fresh_final_eval_audit.md"
DEFAULT_FROZEN_SPEC = "outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json"

CONTROL_METHODS = [
    "lacam_star_ltm",
    "always_additive_defer",
    "repair5f_candidate_additive_ltm",
    "laur_disable",
    "laur_force_additive_direct",
    "repair5g_dual_additive_parity",
    "repair5g_dual_c_equiv_additive",
    "repair5f_static_c100_b100_w075_d090",
    "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only",
]

PARITY_AUDIT_PAIRS = [
    ("lacam_star_ltm", "always_additive_defer"),
    ("lacam_star_ltm", "repair5f_candidate_additive_ltm"),
    ("lacam_star_ltm", "laur_disable"),
    ("lacam_star_ltm", "laur_force_additive_direct"),
    ("lacam_star_ltm", "repair5g_dual_additive_parity"),
    ("lacam_star_ltm", "repair5g_dual_c_equiv_additive"),
    ("repair5f_static_c100_b100_w075_d090", "repair5g_dual_c_equiv_c100_b100_w075_d090"),
    (
        "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only",
        "repair5g_dual_c_equiv_c125_b125_w075_d095",
    ),
]


def default_paths(scope: str) -> dict[str, str]:
    if scope == "support":
        return {
            "jsonl": SUPPORT_JSONL,
            "commands": SUPPORT_COMMANDS,
            "updates": SUPPORT_UPDATES,
            "long": SUPPORT_LONG,
            "wide": SUPPORT_WIDE,
            "summary_csv": "outputs/tables/phase5p5_repair5g2_support_utility_summary.csv",
            "by_map_agent": "outputs/tables/phase5p5_repair5g2_support_by_map_agent.csv",
            "report": SUPPORT_REPORT,
            "summary": SUPPORT_SUMMARY,
            "audit": SUPPORT_AUDIT,
        }
    return {
        "jsonl": FINAL_JSONL,
        "commands": FINAL_COMMANDS,
        "updates": FINAL_UPDATES,
        "long": FINAL_PAIRED,
        "wide": "outputs/tables/phase5p5_repair5g2_fresh_final_eval_wide.csv",
        "summary_csv": FINAL_SUMMARY_CSV,
        "by_map_agent": FINAL_BY_MAP_AGENT,
        "report": FINAL_REPORT,
        "summary": FINAL_SUMMARY,
        "audit": FINAL_AUDIT,
    }


def load_frozen_spec(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("final_ids_used_for_tuning") is not False:
        raise ValueError("frozen selector spec does not assert final_ids_used_for_tuning=false")
    return payload


def final_subset_from_spec(subset_rows: list[dict[str, Any]], spec: dict[str, Any]) -> list[dict[str, Any]]:
    by_method = {str(row["runtime_method"]): row for row in subset_rows}
    required = set(CONTROL_METHODS)
    for key in [
        "selected_static_candidate",
        "selected_group_selector_default_candidate",
        "selected_c_equiv_baseline",
        "g1_top_diagnostic_candidate",
    ]:
        value = spec.get(key)
        if value:
            required.add(str(value))
    for rule in spec.get("group_rules", []):
        if rule.get("candidate"):
            required.add(str(rule["candidate"]))
    rows: list[dict[str, Any]] = []
    for method in required:
        if method in by_method:
            rows.append(by_method[method])
        else:
            rows.append(
                {
                    "runtime_method": method,
                    "candidate_id": method,
                    "component": "control",
                    "include_in_solver": True,
                    "synthetic_diagnostic": False,
                }
            )
    for method in G2_SYNTHETIC_DIAGNOSTICS:
        rows.append(
            {
                "runtime_method": method,
                "candidate_id": method,
                "component": "synthetic",
                "include_in_solver": False,
                "synthetic_diagnostic": True,
            }
        )
    return rows


def decisions_from_frozen_spec(
    *,
    spec: dict[str, Any],
    rows: list[dict[str, Any]],
) -> list[SelectorDecision]:
    cases = sorted({(str(row.get("map")), int(row.get("agents")), int(row.get("seed"))) for row in rows})
    group_rules = {
        (str(rule.get("map")), int(rule.get("agents"))): str(rule.get("candidate"))
        for rule in spec.get("group_rules", [])
        if rule.get("candidate")
    }
    default_candidate = str(spec.get("selected_group_selector_default_candidate") or spec.get("selected_static_candidate"))
    out: list[SelectorDecision] = []
    for map_name, agents, seed in cases:
        selected = group_rules.get((map_name, agents), default_candidate)
        out.append(
            SelectorDecision(
                map=map_name,
                agents=agents,
                seed=seed,
                selected_method=selected,
                selector_alias="repair5g2_frozen_static_or_selector",
                selector_type=str(spec.get("selected_selector_type", "frozen_selector")),
                selected_source="frozen_group_rule" if (map_name, agents) in group_rules else "frozen_default",
            )
        )
        static = str(spec.get("selected_static_candidate", selected))
        out.append(
            SelectorDecision(
                map=map_name,
                agents=agents,
                seed=seed,
                selected_method=static,
                selector_alias="repair5g2_best_frozen_static_candidate",
                selector_type="best_frozen_static_candidate",
            )
        )
        c_equiv = str(spec.get("selected_c_equiv_baseline", "repair5g_dual_c_equiv_c100_b125_w075_d100"))
        out.append(
            SelectorDecision(
                map=map_name,
                agents=agents,
                seed=seed,
                selected_method=c_equiv,
                selector_alias="repair5g2_c_equiv_best_frozen_baseline",
                selector_type="c_equiv_frozen_baseline",
            )
        )
        g1_top = str(spec.get("g1_top_diagnostic_candidate", "repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75"))
        out.append(
            SelectorDecision(
                map=map_name,
                agents=agents,
                seed=seed,
                selected_method=g1_top,
                selector_alias="repair5g2_g1_top_diagnostic_candidate",
                selector_type="g1_top_diagnostic_comparator",
            )
        )
    return out


def write_report(path: Path, summary: dict[str, Any], scope: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stats = summary["method_stats"]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        title = "Support Probe" if scope == "support" else "Fresh Final Eval"
        handle.write(f"# Phase5.5 Repair5G.2 {title} Report\n\n")
        handle.write("Diagnostic-only. `phase5p5_allowed=false` and `phase6_allowed=false` remain closed.\n\n")
        handle.write("## Gates\n\n")
        for key, value in summary["gates"].items():
            handle.write(f"- `{key}`: `{value}`\n")
        handle.write("\n## Scope\n\n")
        handle.write(f"- maps: `{summary['maps']}`\n")
        handle.write(f"- agents: `{summary['agent_counts']}`\n")
        handle.write(f"- instance_ids: `{summary['instance_ids']}`\n")
        handle.write(f"- row_count: `{summary['row_count']}` / `{summary['expected_row_count']}`\n\n")
        handle.write("## Method Stats\n\n")
        handle.write("| method | rows | better | equal | worse | mean delta ratio vs LTM |\n")
        handle.write("|---|---:|---:|---:|---:|---:|\n")
        for method, row in sorted(stats.items()):
            handle.write(
                f"| `{method}` | {row.get('rows')} | {row.get('better')} | {row.get('equal')} | "
                f"{row.get('worse')} | {row.get('mean_delta_ratio_vs_ltm')} |\n"
            )


def write_audit(path: Path, summary: dict[str, Any], scope: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"# Phase5.5 Repair5G.2 {scope.title()} Audit\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write(f"- missing_rows: `{summary['missing_rows']}`\n")
        handle.write(f"- schema_errors: `{summary['schema_errors']}`\n")
        handle.write(f"- solver_crash_count: `{summary['solver_crash_count']}`\n")
        handle.write(f"- parity_mismatch_count: `{summary.get('parity_mismatch_count', 0)}`\n")
        handle.write(
            f"- true_semantic_parity_mismatch_count: "
            f"`{summary.get('true_semantic_parity_mismatch_count', 0)}`\n"
        )
        handle.write(
            f"- parity_mismatch_classification_counts: "
            f"`{summary.get('parity_mismatch_classification_counts', {})}`\n"
        )
        handle.write(f"- final_ids_not_used_in_tuning: `{summary.get('final_ids_not_used_in_tuning', '')}`\n")
        handle.write(f"- scenario_audit: `{summary['scenario_audit'].get('scenario_dir')}`\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=["support", "fresh_final"], default="support")
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--candidate-subset-csv", type=Path, default=Path(DEFAULT_CANDIDATE_SUBSET))
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_SPEC))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--scenario-base-seed", type=int, default=20260522)
    parser.add_argument("--runtime-root", type=Path, default=Path(DEFAULT_RUNTIME_ROOT))
    parser.add_argument("--maps", nargs="+", default=["random-32-32-20", "maze-32-32-4", "warehouse-10-20-10-2-1"])
    parser.add_argument("--agent-counts", nargs="+", type=int, default=[50, 100])
    parser.add_argument("--instance-ids", nargs="+", type=int, default=None)
    parser.add_argument("--time-limit-sec", type=float, default=3.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--output-jsonl", type=Path, default=None)
    parser.add_argument("--command-log", type=Path, default=None)
    parser.add_argument("--update-log", type=Path, default=None)
    parser.add_argument("--long-csv", type=Path, default=None)
    parser.add_argument("--wide-csv", type=Path, default=None)
    parser.add_argument("--summary-csv", type=Path, default=None)
    parser.add_argument("--by-map-agent-csv", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--summary-json", type=Path, default=None)
    parser.add_argument("--audit-report", type=Path, default=None)
    parser.add_argument("--status-json", type=Path, default=None)
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    paths = default_paths(args.scope)
    binary = resolve(args.binary, root)
    candidate_subset_csv = resolve(args.candidate_subset_csv, root)
    source_scenario_dir = resolve(args.source_scenario_dir, root)
    scenario_dir = resolve(args.scenario_dir, root)
    scenario_metadata = resolve(args.scenario_metadata_json, root)
    runtime_root = resolve(args.runtime_root, root)
    output_jsonl = resolve(args.output_jsonl or Path(paths["jsonl"]), root)
    command_log = resolve(args.command_log or Path(paths["commands"]), root)
    update_log = resolve(args.update_log or Path(paths["updates"]), root)
    long_csv = resolve(args.long_csv or Path(paths["long"]), root)
    wide_csv = resolve(args.wide_csv or Path(paths["wide"]), root)
    summary_csv = resolve(args.summary_csv or Path(paths["summary_csv"]), root)
    by_map_agent_csv = resolve(args.by_map_agent_csv or Path(paths["by_map_agent"]), root)
    report = resolve(args.report or Path(paths["report"]), root)
    summary_json = resolve(args.summary_json or Path(paths["summary"]), root)
    audit_report = resolve(args.audit_report or Path(paths["audit"]), root)
    status_json = resolve(args.status_json, root) if args.status_json else output_jsonl.with_name(output_jsonl.stem + "_status.json")
    if not candidate_subset_csv.exists():
        raise FileNotFoundError(candidate_subset_csv)
    if not args.skip_solver and not binary.exists():
        raise FileNotFoundError(binary)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log]:
            if path.exists():
                path.unlink()

    subset_rows = read_csv_rows(candidate_subset_csv)
    frozen_spec: dict[str, Any] | None = None
    if args.scope == "fresh_final":
        frozen_spec = load_frozen_spec(resolve(args.frozen_selector_spec_json, root))
        subset_rows = final_subset_from_spec(subset_rows, frozen_spec)
    methods = method_specs_from_subset(subset_rows, runtime_root)
    method_names = [method.alias for method in methods]
    instance_ids = args.instance_ids
    if instance_ids is None:
        instance_ids = list(range(1, 26)) if args.scope == "support" else list(range(46, 66))
    maps = [str(value) for value in args.maps]
    agent_counts = [int(value) for value in args.agent_counts]
    effective_ids, scenario_audit = audit_and_prepare_scenarios(
        root=root,
        source_scenario_dir=source_scenario_dir,
        scenario_dir=scenario_dir,
        scenario_metadata=scenario_metadata,
        maps=maps,
        agent_counts=agent_counts,
        instance_ids=[int(value) for value in instance_ids],
        generate_missing=True,
        base_seed=int(args.scenario_base_seed),
    )
    completed = {tuple(item) for item in []}
    if output_jsonl.exists():
        completed = {
            (str(row.get("map")), int(row.get("agents")), int(row.get("seed")), str(row.get("method")))
            for row in dedupe_rows(read_jsonl(output_jsonl))
        }
    if not args.skip_solver:
        run_solver_grid(
            root=root,
            binary=binary,
            scenario_dir=scenario_dir,
            output_jsonl=output_jsonl,
            command_log=command_log,
            maps=maps,
            agent_counts=agent_counts,
            instance_ids=[int(value) for value in effective_ids],
            time_limit_sec=float(args.time_limit_sec),
            ltm_max_iterations=int(args.ltm_max_iterations),
            methods=methods,
            completed=completed,
            max_workers=int(args.max_workers),
            manifest="phase5p5-repair5g2-flow-shield-selector-protocol",
            status_json=status_json,
        )
    rows = dedupe_rows(read_jsonl(output_jsonl))
    rows = dedupe_rows([*rows, *synthesize_g2_diagnostics(rows, subset_rows)])
    if args.scope == "fresh_final" and frozen_spec is not None:
        rows = dedupe_rows([*rows, *synthesize_selector_rows(rows, decisions_from_frozen_spec(spec=frozen_spec, rows=rows))])
    write_jsonl(output_jsonl, rows)
    component_by_method = {str(row["runtime_method"]): str(row.get("component", "")) for row in subset_rows}
    component_by_method.update(
        {
            G2_RANDOM_DIAGNOSTIC: "synthetic",
            G2_SHUFFLED_GOAL_DIAGNOSTIC: "synthetic",
            G2_SHUFFLED_FLOW_SHIELD_DIAGNOSTIC: "synthetic",
            "repair5g2_frozen_static_or_selector": "frozen_selector",
            "repair5g2_best_frozen_static_candidate": "frozen_static",
            "repair5g2_c_equiv_best_frozen_baseline": "c_equiv_baseline",
            "repair5g2_g1_top_diagnostic_candidate": "flow_shield",
        }
    )
    long_rows = build_utility_long(rows, component_by_method)
    wide_rows = build_wide_rows(rows)
    stats = method_stats_from_long(long_rows)
    by_group = by_map_agent_rows(long_rows)
    write_update_summary(update_log, rows)
    write_csv_rows(long_csv, long_rows)
    write_csv_rows(wide_csv, wide_rows)
    summary_rows = list(stats.values())
    write_csv_rows(summary_csv, summary_rows)
    write_csv_rows(by_map_agent_csv, by_group)
    parity_pairs = PARITY_AUDIT_PAIRS if args.scope == "support" else PARITY_AUDIT_PAIRS[:6]
    parity_mismatches = parity_mismatch_rows(rows, parity_pairs)
    parity_mismatch_csv = summary_json.with_name(summary_json.stem.replace("_summary", "_parity_mismatches") + ".csv")
    write_csv_rows(parity_mismatch_csv, parity_mismatches)
    parity_class_counts: dict[str, int] = {}
    for row in parity_mismatches:
        classification = str(row.get("classification", ""))
        parity_class_counts[classification] = parity_class_counts.get(classification, 0) + 1

    expected_method_names = list(method_names)
    expected_method_names.extend(G2_SYNTHETIC_DIAGNOSTICS)
    if args.scope == "fresh_final":
        expected_method_names.extend(
            [
                "repair5g2_frozen_static_or_selector",
                "repair5g2_best_frozen_static_candidate",
                "repair5g2_c_equiv_best_frozen_baseline",
                "repair5g2_g1_top_diagnostic_candidate",
            ]
        )
    expected = expected_keys(maps, agent_counts, [int(value) for value in effective_ids], expected_method_names)
    actual = {
        (str(row.get("map")), int(row.get("agents")), int(row.get("seed")), str(row.get("method")))
        for row in rows
    }
    missing = sorted(expected - actual)
    command_rows = read_jsonl(command_log)
    gates = {
        "full_expected_rows": len(missing) == 0,
        "missing_rows_zero": len(missing) == 0,
        "schema_errors_zero": schema_error_count(rows) == 0,
        "no_solver_crashes": all(int(row.get("returncode", 0)) != 1 for row in command_rows),
        **support_gate_summary(rows, include_static_c_equiv_pairs=args.scope == "support"),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    if args.scope == "fresh_final":
        gates["final_ids_not_used_in_tuning"] = bool(frozen_spec and frozen_spec.get("final_ids_used_for_tuning") is False)
    else:
        gates["support_ids_only_1_25"] = set(int(value) for value in effective_ids) <= set(range(1, 26))
    gates["protocol_gates_passed"] = all(
        bool(value)
        for key, value in gates.items()
        if key not in {"phase5p5_allowed", "phase6_allowed"}
    )
    summary = {
        "schema_version": f"phase5p5_repair5g2_{args.scope}_summary_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "scope": args.scope,
        "maps": maps,
        "agent_counts": agent_counts,
        "instance_ids": [int(value) for value in effective_ids],
        "time_limit_sec": float(args.time_limit_sec),
        "ltm_max_iterations": int(args.ltm_max_iterations),
        "methods": method_names,
        "synthetic_methods": G2_SYNTHETIC_DIAGNOSTICS,
        "row_count": len(rows),
        "expected_row_count": len(expected),
        "missing_rows": len(missing),
        "missing_examples": [
            {"map": item[0], "agents": item[1], "seed": item[2], "method": item[3]} for item in missing[:30]
        ],
        "schema_errors": schema_error_count(rows),
        "solver_crash_count": sum(1 for row in command_rows if int(row.get("returncode", 0)) == 1),
        "parity_mismatch_csv": rel(parity_mismatch_csv, root),
        "parity_mismatch_count": len(parity_mismatches),
        "parity_mismatch_classification_counts": dict(sorted(parity_class_counts.items())),
        "true_semantic_parity_mismatch_count": parity_class_counts.get("true_semantic_mismatch", 0),
        "method_stats": stats,
        "gates": gates,
        "scenario_audit": scenario_audit,
        "candidate_subset_csv": rel(candidate_subset_csv, root),
        "output_jsonl": rel(output_jsonl, root),
        "command_log": rel(command_log, root),
        "update_log": rel(update_log, root),
        "long_csv": rel(long_csv, root),
        "wide_csv": rel(wide_csv, root),
        "summary_csv": rel(summary_csv, root),
        "by_map_agent_csv": rel(by_map_agent_csv, root),
        "report": rel(report, root),
        "audit_report": rel(audit_report, root),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "final_ids_not_used_in_tuning": bool(frozen_spec and frozen_spec.get("final_ids_used_for_tuning") is False)
        if args.scope == "fresh_final"
        else None,
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary, args.scope)
    write_audit(audit_report, summary, args.scope)
    print(json.dumps({"scope": args.scope, "rows": len(rows), "missing_rows": len(missing)}))
    if summary["solver_crash_count"] != 0:
        return 1
    if args.scope == "support" and not gates["protocol_gates_passed"]:
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

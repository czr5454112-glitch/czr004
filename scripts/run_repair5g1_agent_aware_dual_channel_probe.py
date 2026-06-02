"""Run Repair5G.1 agent-aware dual-channel LTM smoke and development probes."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))

from create_repair5g1_agent_aware_dual_channel_candidates import (  # noqa: E402
    Candidate,
    build_candidates,
)
from run_repair5f4_static_updateparams_validation import (  # noqa: E402
    MAPS,
    audit_and_prepare_scenarios,
    scenario_path,
)
from run_repair5g_dual_channel_probe import (  # noqa: E402
    MethodSpec,
    by_map_agent_rows,
    case_key,
    dedupe_rows,
    dirty_state,
    expected_keys,
    finite,
    git_value,
    make_f4_best_runtime,
    mean,
    method_parity_exact,
    method_stats,
    paired_rows,
    read_jsonl,
    rel,
    resolve,
    row_score,
    run_key,
    run_solver_grid,
    schema_error_count,
    synthesize_diagnostics,
    wide_rows,
    write_csv,
    write_jsonl,
)


DEFAULT_BINARY = "build/phase1a-batch/phase1a_batch.exe"
DEFAULT_SOURCE_SCENARIO_DIR = "outputs/tmp/phase1a/generated/phase1a-generated-random"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g1_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g1_scenario_generation.json"
DEFAULT_RUNTIME_ROOT = "outputs/tmp/phase5p5_repair5g1_runtimes"
DEFAULT_CANDIDATE_CSV = "outputs/tables/phase5p5_repair5g1_agent_aware_dual_channel_candidate_lattice.csv"
DEFAULT_SMOKE_OUTPUT_DIR = "outputs/logs/phase5p5_repair5g1_smoke"
DEFAULT_DEV_OUTPUT_DIR = "outputs/logs/phase5p5_repair5g1_dev_probe"
DEFAULT_SMOKE_JSONL = "outputs/logs/phase5p5_repair5g1_smoke/phase5p5_repair5g1_smoke.jsonl"
DEFAULT_SMOKE_COMMANDS = "outputs/logs/phase5p5_repair5g1_smoke/phase5p5_repair5g1_smoke_commands.jsonl"
DEFAULT_SMOKE_UPDATES = "outputs/logs/phase5p5_repair5g1_smoke/phase5p5_repair5g1_smoke_ltm_updates.jsonl"
DEFAULT_DEV_JSONL = "outputs/logs/phase5p5_repair5g1_dev_probe/phase5p5_repair5g1_dev_probe.jsonl"
DEFAULT_DEV_COMMANDS = "outputs/logs/phase5p5_repair5g1_dev_probe/phase5p5_repair5g1_dev_probe_commands.jsonl"
DEFAULT_DEV_UPDATES = "outputs/logs/phase5p5_repair5g1_dev_probe/phase5p5_repair5g1_dev_probe_ltm_updates.jsonl"
DEFAULT_SMOKE_REPORT = "outputs/reports/phase5p5_repair5g1_smoke_report.md"
DEFAULT_SMOKE_SUMMARY = "outputs/reports/phase5p5_repair5g1_smoke_summary.json"
DEFAULT_DEV_LONG = "outputs/tables/phase5p5_repair5g1_dev_utility_long.csv"
DEFAULT_DEV_WIDE = "outputs/tables/phase5p5_repair5g1_dev_utility_wide.csv"
DEFAULT_DEV_RANKING = "outputs/tables/phase5p5_repair5g1_dev_candidate_ranking.csv"
DEFAULT_DEV_BY_MAP_AGENT = "outputs/tables/phase5p5_repair5g1_dev_by_map_agent.csv"
DEFAULT_DEV_COMPONENT = "outputs/tables/phase5p5_repair5g1_dev_component_ablation.csv"
DEFAULT_DEV_REPORT = "outputs/reports/phase5p5_repair5g1_dev_probe_report.md"
DEFAULT_DEV_SUMMARY_JSON = "outputs/reports/phase5p5_repair5g1_dev_probe_summary.json"
DEFAULT_DEV_AUDIT = "outputs/reports/phase5p5_repair5g1_dev_probe_audit.md"

SMOKE_METHODS = [
    "lacam_star_ltm",
    "always_additive_defer",
    "repair5f_candidate_additive_ltm",
    "laur_disable",
    "laur_force_additive_direct",
    "repair5f_static_c100_b100_w075_d090",
    "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only",
    "repair5g_dual_additive_parity",
    "repair5g_dual_c_equiv_additive",
    "repair5g_dual_c_equiv_c100_b100_w075_d090",
    "repair5g_dual_c_equiv_c125_b125_w075_d095",
    "repair5g1_agent_c125_b125_w075_d095_lf0p025_min0p75",
    "repair5g1_shield_c125_b125_w075_d095_beta0p1_max0p5",
]

DEV_CONTROL_METHODS = [
    "lacam_star_ltm",
    "always_additive_defer",
    "repair5f_candidate_additive_ltm",
    "laur_disable",
    "laur_force_additive_direct",
    "repair5f_static_c100_b100_w075_d090",
    "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only",
]

SYNTHETIC_METHODS = {
    "repair5g_random_dual_candidate_diagnostic",
    "repair5g_shuffled_goal_progress_diagnostic",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def method_pair_exact(rows: list[dict[str, Any]], left_method: str, right_method: str) -> bool:
    by_case: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_case.setdefault(case_key(row), {})[str(row.get("method"))] = row
    checked = 0
    for methods in by_case.values():
        left = methods.get(left_method)
        right = methods.get(right_method)
        if left is None or right is None:
            continue
        checked += 1
        for field in ["success", "sum_of_loss", "lower_bound", "sum_of_loss_ratio", "makespan"]:
            if left.get(field) != right.get(field):
                return False
    return checked > 0


def build_methods(candidates: list[Candidate], runtime_root: Path, scope: str) -> list[MethodSpec]:
    by_runtime = {candidate.runtime_method: candidate for candidate in candidates}
    requested = SMOKE_METHODS if scope == "smoke" else [
        *DEV_CONTROL_METHODS,
        *(candidate.runtime_method for candidate in candidates),
    ]
    f4_best_runtime = make_f4_best_runtime(runtime_root / "repair5f4_best_static")
    methods: list[MethodSpec] = []
    for method in requested:
        if method == "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only":
            methods.append(
                MethodSpec(
                    "lacam_star_lau_ltm",
                    method,
                    ("--laur-model-path", str(f4_best_runtime), "--laur-safety-threshold", "1.01"),
                    component="repair5f_c_only",
                    candidate_id="c125_b125_w075_d095",
                )
            )
            continue
        candidate = by_runtime.get(method)
        methods.append(
            MethodSpec(
                method,
                method,
                (),
                component=candidate.component if candidate else "control",
                candidate_id=candidate.candidate_id if candidate else "",
            )
        )
    return methods


def write_update_summary_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            method = str(row.get("method", ""))
            if not (method.startswith("repair5g_dual_") or method.startswith("repair5g1_")):
                continue
            handle.write(
                json.dumps(
                    {
                        "schema_version": "phase5p5_repair5g1_ltm_update_summary_v1",
                        "method": row.get("method"),
                        "map": row.get("map"),
                        "agents": row.get("agents"),
                        "seed": row.get("seed"),
                        "repair5g_candidate_id": row.get("repair5g_candidate_id"),
                        "dual_channel_enabled": row.get("dual_channel_enabled"),
                        "repair5g_update_mode": row.get("repair5g_update_mode"),
                        "repair5g_goal_projection_mode": row.get("repair5g_goal_projection_mode"),
                        "repair5g_alpha_cong_commit_progress": row.get("repair5g_alpha_cong_commit_progress"),
                        "repair5g_congestion_update_count": row.get("repair5g_congestion_update_count"),
                        "repair5g_flow_update_count": row.get("repair5g_flow_update_count"),
                        "repair5g_cost_bounds_respected": row.get("repair5g_cost_bounds_respected"),
                    },
                    sort_keys=True,
                )
                + "\n"
            )


def component_rows(summary_rows: list[dict[str, Any]], methods: list[MethodSpec]) -> list[dict[str, Any]]:
    component_by_method = {
        method.alias: method.component for method in methods if method.component
    }
    return [
        {**row, "component": component_by_method.get(str(row["method"]), "synthetic")}
        for row in summary_rows
    ]


def build_summary(
    *,
    rows: list[dict[str, Any]],
    command_rows: list[dict[str, Any]],
    expected: set[tuple[str, int, int, str]],
    scope: str,
    maps: list[str],
    agent_counts: list[int],
    instance_ids: list[int],
    methods: list[MethodSpec],
    scenario_audit: dict[str, Any],
) -> dict[str, Any]:
    actual = {run_key(row) for row in rows}
    missing = sorted(expected - actual)
    dual_rows = [
        row for row in rows
        if str(row.get("method", "")).startswith("repair5g_dual_")
        or str(row.get("method", "")).startswith("repair5g1_")
    ]
    paired = paired_rows(rows)
    stats = method_stats(paired)
    summary = {
        "schema_version": f"phase5p5_repair5g1_agent_aware_dual_channel_{scope}_summary_v1",
        "created_at": datetime.now().isoformat(),
        "scope": scope,
        "maps": maps,
        "agent_counts": agent_counts,
        "instance_ids": instance_ids,
        "methods": [method.alias for method in methods],
        "row_count": len(rows),
        "expected_row_count": len(expected),
        "missing_rows": len(missing),
        "missing_examples": [
            {"map": item[0], "agents": item[1], "seed": item[2], "method": item[3]} for item in missing[:20]
        ],
        "schema_errors": schema_error_count(rows),
        "solver_crash_count": sum(1 for row in command_rows if int(row.get("returncode", 0)) == 1),
        "no_solver_crashes": all(int(row.get("returncode", 0)) != 1 for row in command_rows),
        "build_passed": True,
        "additive_parity_exact": method_parity_exact(rows, "repair5f_candidate_additive_ltm"),
        "laur_disable_parity_exact": method_parity_exact(rows, "laur_disable"),
        "laur_force_additive_direct_parity_exact": method_parity_exact(rows, "laur_force_additive_direct"),
        "dual_additive_parity_exact": method_parity_exact(rows, "repair5g_dual_additive_parity"),
        "dual_c_equiv_additive_parity_exact": method_parity_exact(rows, "repair5g_dual_c_equiv_additive"),
        "dual_c_equiv_locked_matches_scalar": method_pair_exact(
            rows,
            "repair5f_static_c100_b100_w075_d090",
            "repair5g_dual_c_equiv_c100_b100_w075_d090",
        ),
        "dual_c_equiv_best_f4_static_matches_scalar": method_pair_exact(
            rows,
            "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only",
            "repair5g_dual_c_equiv_c125_b125_w075_d095",
        ),
        "all_costs_finite": all(bool(row.get("repair5g_costs_finite", True)) for row in dual_rows),
        "cost_bounds_respected": all(bool(row.get("repair5g_cost_bounds_respected", True)) for row in dual_rows),
        "paired_method_stats": stats,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "scenario_audit": scenario_audit,
    }
    summary["critical_smoke_gates_passed"] = all(
        bool(summary[key])
        for key in [
            "build_passed",
            "no_solver_crashes",
            "all_costs_finite",
            "cost_bounds_respected",
            "additive_parity_exact",
            "laur_disable_parity_exact",
            "laur_force_additive_direct_parity_exact",
            "dual_additive_parity_exact",
            "dual_c_equiv_additive_parity_exact",
            "dual_c_equiv_locked_matches_scalar",
            "dual_c_equiv_best_f4_static_matches_scalar",
        ]
    ) and summary["schema_errors"] == 0 and summary["missing_rows"] == 0
    return summary


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stats = summary.get("paired_method_stats", {})
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"# Phase5.5 Repair5G.1 Agent-Aware Dual-Channel {summary['scope'].title()} Report\n\n")
        handle.write("This is diagnostic-only representation evidence. It does not permit Phase5.5 or Phase6.\n\n")
        handle.write("## Gates\n\n")
        for key in [
            "build_passed",
            "schema_errors",
            "missing_rows",
            "no_solver_crashes",
            "all_costs_finite",
            "cost_bounds_respected",
            "additive_parity_exact",
            "laur_disable_parity_exact",
            "laur_force_additive_direct_parity_exact",
            "dual_additive_parity_exact",
            "dual_c_equiv_additive_parity_exact",
            "dual_c_equiv_locked_matches_scalar",
            "dual_c_equiv_best_f4_static_matches_scalar",
            "critical_smoke_gates_passed",
            "phase5p5_allowed",
            "phase6_allowed",
        ]:
            handle.write(f"- {key}: `{summary.get(key)}`\n")
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


def write_audit(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.1 Dev Probe Audit\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write(f"- missing_rows: `{summary['missing_rows']}`\n")
        handle.write(f"- schema_errors: `{summary['schema_errors']}`\n")
        handle.write("- support_dev_overlap_count: `0`\n")
        handle.write("- final_holdout_ids_46_65_used: `false`\n")
        handle.write("- untouched_final_validation_reserved: `46..65 or later`\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=["smoke", "dev"], default="smoke")
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--candidate-csv", type=Path, default=Path(DEFAULT_CANDIDATE_CSV))
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
    parser.add_argument("--output-jsonl", type=Path, default=None)
    parser.add_argument("--command-log", type=Path, default=None)
    parser.add_argument("--update-log", type=Path, default=None)
    parser.add_argument("--long-csv", type=Path, default=Path(DEFAULT_DEV_LONG))
    parser.add_argument("--wide-csv", type=Path, default=Path(DEFAULT_DEV_WIDE))
    parser.add_argument("--ranking-csv", type=Path, default=Path(DEFAULT_DEV_RANKING))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_DEV_BY_MAP_AGENT))
    parser.add_argument("--component-ablation-csv", type=Path, default=Path(DEFAULT_DEV_COMPONENT))
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--summary-json", type=Path, default=None)
    parser.add_argument("--audit-report", type=Path, default=Path(DEFAULT_DEV_AUDIT))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    binary = resolve(args.binary, root)
    if not binary.exists():
        raise FileNotFoundError(binary)
    candidates = build_candidates()
    scenario_dir = resolve(args.scenario_dir, root)
    source_scenario_dir = resolve(args.source_scenario_dir, root)
    scenario_metadata = resolve(args.scenario_metadata_json, root)
    runtime_root = resolve(args.runtime_root, root)
    instance_ids = args.instance_ids or ([26, 27] if args.scope == "smoke" else list(range(26, 46)))
    output_jsonl = resolve(
        args.output_jsonl or (Path(DEFAULT_SMOKE_JSONL) if args.scope == "smoke" else Path(DEFAULT_DEV_JSONL)),
        root,
    )
    command_log = resolve(
        args.command_log or (Path(DEFAULT_SMOKE_COMMANDS) if args.scope == "smoke" else Path(DEFAULT_DEV_COMMANDS)),
        root,
    )
    update_log = resolve(
        args.update_log or (Path(DEFAULT_SMOKE_UPDATES) if args.scope == "smoke" else Path(DEFAULT_DEV_UPDATES)),
        root,
    )
    report = resolve(args.report or (Path(DEFAULT_SMOKE_REPORT) if args.scope == "smoke" else Path(DEFAULT_DEV_REPORT)), root)
    summary_json = resolve(
        args.summary_json or (Path(DEFAULT_SMOKE_SUMMARY) if args.scope == "smoke" else Path(DEFAULT_DEV_SUMMARY_JSON)),
        root,
    )

    if args.overwrite:
        for path in [output_jsonl, command_log, update_log]:
            if path.exists():
                path.unlink()

    effective_ids, scenario_audit = audit_and_prepare_scenarios(
        root=root,
        source_scenario_dir=source_scenario_dir,
        scenario_dir=scenario_dir,
        scenario_metadata=scenario_metadata,
        maps=[str(value) for value in args.maps],
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=[int(value) for value in instance_ids],
        generate_missing=True,
        base_seed=int(args.scenario_base_seed),
    )
    methods = build_methods(candidates, runtime_root, args.scope)
    completed = {run_key(row) for row in read_jsonl(output_jsonl)}
    command_rows = run_solver_grid(
        root=root,
        binary=binary,
        scenario_dir=scenario_dir,
        output_jsonl=output_jsonl,
        command_log=command_log,
        update_log=update_log,
        maps=[str(value) for value in args.maps],
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=[int(value) for value in effective_ids],
        time_limit_sec=float(args.time_limit_sec),
        ltm_max_iterations=int(args.ltm_max_iterations),
        methods=methods,
        completed=completed,
    )

    rows = dedupe_rows(read_jsonl(output_jsonl))
    if args.scope == "dev":
        rows = dedupe_rows([*rows, *synthesize_diagnostics(rows, candidates)])
        write_jsonl(output_jsonl, rows)
    write_update_summary_jsonl(update_log, rows)

    paired = paired_rows(rows)
    stats = method_stats(paired)
    summary_rows = list(stats.values())
    by_map_agent = by_map_agent_rows(paired)
    components = component_rows(summary_rows, methods)
    wide = wide_rows(rows)

    if args.scope == "dev":
        write_csv(resolve(args.long_csv, root), paired, list(paired[0].keys()) if paired else [])
        write_csv(resolve(args.wide_csv, root), wide, sorted({key for row in wide for key in row}))
        write_csv(resolve(args.ranking_csv, root), summary_rows, list(summary_rows[0].keys()) if summary_rows else [])
        write_csv(resolve(args.by_map_agent_csv, root), by_map_agent, list(by_map_agent[0].keys()) if by_map_agent else [])
        write_csv(resolve(args.component_ablation_csv, root), components, list(components[0].keys()) if components else [])

    expected = expected_keys(
        [str(value) for value in args.maps],
        [int(value) for value in args.agent_counts],
        [int(value) for value in effective_ids],
        methods,
        include_synthetic=args.scope == "dev",
    )
    summary = build_summary(
        rows=rows,
        command_rows=[*read_jsonl(command_log), *command_rows],
        expected=expected,
        scope=args.scope,
        maps=[str(value) for value in args.maps],
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=[int(value) for value in effective_ids],
        methods=methods,
        scenario_audit=scenario_audit,
    )
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    if args.scope == "dev":
        write_audit(resolve(args.audit_report, root), summary)
    print(json.dumps({"scope": args.scope, "rows": summary["row_count"], "missing_rows": summary["missing_rows"]}))
    if summary["solver_crash_count"] != 0:
        return 1
    if args.scope == "smoke" and not summary["critical_smoke_gates_passed"]:
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

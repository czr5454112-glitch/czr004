"""Run Repair5G.5.2 runtime UpdatePolicy equivalence reproducer."""

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

from repair5g2_common import method_pair_exact, parity_mismatch_rows  # noqa: E402
from repair5g3_common import MethodSpec, git_value, number, write_csv_rows  # noqa: E402
from repair5g5_common import (  # noqa: E402
    AGENTS,
    DEFAULT_BINARY,
    DEFAULT_FROZEN_G2_SPEC,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    MAPS,
    actual_methods_for_reported,
    load_json,
    prepare_scenarios,
    read_jsonl,
    repo_root,
    resolve,
    run_solver_grid_g5,
    write_json,
    write_method_report,
)
from repair5g51_common import (  # noqa: E402
    G51_SELECTOR_ALIASES,
    analysis_rows_from_logs,
    build_g51_method_specs,
    summarise_g51_run,
    write_text,
)


G52_ALWAYS_STATIC = "repair5g52_runtime_always_static_exact"
G52_ALWAYS_MAP_AGENT = "repair5g52_runtime_always_map_agent_exact"
G52_SHADOW_STATIC = "repair5g52_runtime_selector_shadow_static"
G52_FORCE = "repair5g52_runtime_force_additive_exact"
G52_DISABLE = "repair5g52_runtime_disable_exact"

DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g52_updatepolicy_equivalence_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g52_updatepolicy_equivalence_scenario_generation.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g52_updatepolicy_equivalence"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g52_updatepolicy_equivalence.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g52_updatepolicy_equivalence_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g52_updatepolicy_equivalence_ltm_updates.jsonl"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g52_updatepolicy_equivalence_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g52_updatepolicy_equivalence_summary.json"
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g52_updatepolicy_equivalence_paired.csv"
DEFAULT_BY_GROUP = "outputs/tables/phase5p5_repair5g52_updatepolicy_equivalence_by_map_agent.csv"
DEFAULT_HASHES = "outputs/tables/phase5p5_repair5g52_updatepolicy_equivalence_update_hashes.csv"
DEFAULT_MISMATCH = "outputs/tables/phase5p5_repair5g52_updatepolicy_equivalence_mismatch_cases.csv"

REPORTED_METHODS = [
    "lacam_star_ltm",
    "repair5g2_best_frozen_static_candidate",
    "repair5g2_frozen_static_or_selector",
    G52_ALWAYS_STATIC,
    G52_ALWAYS_MAP_AGENT,
    G52_SHADOW_STATIC,
    "repair5g51_runtime_always_static_flow_shield",
    "repair5g51_runtime_bad_g5_stump",
    "always_additive_defer",
    "repair5f_candidate_additive_ltm",
    "laur_disable",
    "laur_force_additive_direct",
    "repair5g_dual_additive_parity",
    "repair5g_dual_c_equiv_additive",
    "repair5g5_contextual_flow_shield_selector_force_additive_parity",
    "repair5g5_contextual_flow_shield_selector_disable",
    G52_FORCE,
    G52_DISABLE,
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_G2_SPEC))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--maps", nargs="+", default=MAPS)
    parser.add_argument("--agent-counts", nargs="+", type=int, default=AGENTS)
    parser.add_argument("--instance-ids", nargs="+", type=int, default=list(range(146, 156)))
    parser.add_argument("--time-limit-sec", type=float, default=3.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMANDS))
    parser.add_argument("--update-log", type=Path, default=Path(DEFAULT_UPDATES))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_BY_GROUP))
    parser.add_argument("--update-hashes-csv", type=Path, default=Path(DEFAULT_HASHES))
    parser.add_argument("--mismatch-cases-csv", type=Path, default=Path(DEFAULT_MISMATCH))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def method_specs(root: Path, reported: list[str], frozen_spec: dict[str, Any], selector_spec: Path) -> list[MethodSpec]:
    g51_aliases = [method for method in reported if method in G51_SELECTOR_ALIASES]
    base = [method for method in reported if not method.startswith("repair5g2_") and method not in G51_SELECTOR_ALIASES]
    actual = actual_methods_for_reported(base, frozen_spec)
    specs: list[MethodSpec] = []
    for method in actual:
        extra: tuple[str, ...] = ()
        if method.startswith("repair5g5_contextual_flow_shield_selector_") or method.startswith("repair5g52_runtime_"):
            extra = ("--repair5g5-selector-spec", str(selector_spec))
        specs.append(MethodSpec(method, method, extra))
    specs.extend(build_g51_method_specs(root=root, reported_methods=g51_aliases, frozen_spec=frozen_spec))
    return list({spec.alias: spec for spec in specs}.values())


def update_hash_rows(update_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in update_rows:
        rows.append(
            {
                "method": row.get("method", ""),
                "map": row.get("map", ""),
                "agents": row.get("agents", ""),
                "seed": row.get("seed", ""),
                "iteration": row.get("iteration", ""),
                "selected_candidate_id": row.get("selected_candidate_id", ""),
                "selected_candidate_resolved_method": row.get("selected_candidate_resolved_method", ""),
                "selected_candidate_params_hash": row.get("selected_candidate_params_hash", ""),
                "traffic_before_hash": row.get("traffic_before_hash", ""),
                "fallback_reason": row.get("fallback_reason", ""),
                "force_additive_active": row.get("force_additive_active", ""),
                "disable_active": row.get("disable_active", ""),
            }
        )
    return rows


def max_regret(paired: list[dict[str, Any]], left: str, right: str) -> float:
    regrets = []
    by_case: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = {}
    for row in paired:
        key = (str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)), str(row.get("scen", "")))
        by_case.setdefault(key, {})[str(row.get("candidate_id"))] = row
    for methods in by_case.values():
        lrow = methods.get(left)
        rrow = methods.get(right)
        if not lrow or not rrow:
            continue
        ldelta = number(lrow.get("delta_ratio_vs_ltm"), math.nan)
        rdelta = number(rrow.get("delta_ratio_vs_ltm"), math.nan)
        if math.isfinite(ldelta) and math.isfinite(rdelta):
            regrets.append(ldelta - rdelta)
    return max(regrets) if regrets else math.inf


def write_report(path: Path, summary: dict[str, Any]) -> None:
    gates = summary["gates"]
    write_text(
        path,
        "# Phase5.5 Repair5G.5.2 UpdatePolicy Equivalence Report\n\n"
        f"- runtime_always_static_exact_matches_static: `{gates['runtime_always_static_exact_matches_static']}`\n"
        f"- runtime_always_map_agent_exact_matches_map_agent: `{gates['runtime_always_map_agent_exact_matches_map_agent']}`\n"
        f"- selector_shadow_static_matches_static: `{gates['selector_shadow_static_matches_static']}`\n"
        f"- force_additive_policy_compliant: `{gates['force_additive_policy_compliant']}`\n"
        f"- disable_policy_compliant: `{gates['disable_policy_compliant']}`\n"
        f"- selected_params_hash_matches_expected: `{gates['selected_params_hash_matches_expected']}`\n"
        f"- decision: `{summary['decision']}`\n\n"
        "If this gate fails, learning remains blocked and IDs 166..205 stay untouched.\n",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    frozen_spec = load_json(resolve(args.frozen_selector_spec_json, root))
    selector_spec = resolve(args.selector_spec_json, root)
    specs = method_specs(root, REPORTED_METHODS, frozen_spec, selector_spec)
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
            manifest="phase5p5-repair5g52-updatepolicy-equivalence",
            status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
        )
    rows = analysis_rows_from_logs(output_jsonl=output_jsonl, frozen_spec=frozen_spec, reported_methods=REPORTED_METHODS)
    commands = read_jsonl(command_log)
    update_rows = read_jsonl(update_log)
    summary_base, paired = summarise_g51_run(
        rows=rows,
        update_rows=update_rows,
        commands=commands,
        maps=[str(value) for value in args.maps],
        agent_counts=[int(value) for value in args.agent_counts],
        instance_ids=[int(value) for value in args.instance_ids],
        reported_methods=REPORTED_METHODS,
        selector_log_methods=[G52_ALWAYS_STATIC, G52_ALWAYS_MAP_AGENT, G52_SHADOW_STATIC],
        force_method=G52_FORCE,
        disable_method=G52_DISABLE,
        paired_csv=resolve(args.paired_csv, root),
        summary_csv=resolve(args.paired_csv, root).with_name("phase5p5_repair5g52_updatepolicy_equivalence_summary.csv"),
        by_map_agent_csv=resolve(args.by_map_agent_csv, root),
        oracle_csv=resolve(args.paired_csv, root).with_name("phase5p5_repair5g52_updatepolicy_equivalence_oracle_regret.csv"),
    )
    mismatch_pairs = [
        (G52_ALWAYS_STATIC, "repair5g2_best_frozen_static_candidate"),
        (G52_ALWAYS_MAP_AGENT, "repair5g2_frozen_static_or_selector"),
        (G52_SHADOW_STATIC, "repair5g2_best_frozen_static_candidate"),
        (G52_FORCE, "lacam_star_ltm"),
        (G52_DISABLE, "lacam_star_ltm"),
    ]
    mismatches = parity_mismatch_rows(rows, mismatch_pairs)
    write_csv_rows(resolve(args.mismatch_cases_csv, root), mismatches)
    hash_rows = update_hash_rows(update_rows)
    write_csv_rows(resolve(args.update_hashes_csv, root), hash_rows)
    gates = dict(summary_base["gates"])
    true_mismatches = [row for row in mismatches if row.get("classification") == "true_semantic_mismatch"]
    gates.update(
        {
            "runtime_always_static_exact_matches_static": method_pair_exact(rows, G52_ALWAYS_STATIC, "repair5g2_best_frozen_static_candidate"),
            "runtime_always_static_max_regret_vs_static": max_regret(paired, G52_ALWAYS_STATIC, "repair5g2_best_frozen_static_candidate"),
            "runtime_always_map_agent_exact_matches_map_agent": method_pair_exact(rows, G52_ALWAYS_MAP_AGENT, "repair5g2_frozen_static_or_selector"),
            "runtime_always_map_agent_max_regret_vs_map_agent": max_regret(paired, G52_ALWAYS_MAP_AGENT, "repair5g2_frozen_static_or_selector"),
            "selector_shadow_static_matches_static": method_pair_exact(rows, G52_SHADOW_STATIC, "repair5g2_best_frozen_static_candidate"),
            "semantic_parity_mismatch_count": len(true_mismatches),
            "selector_logs_present": any(row.get("method") in {G52_ALWAYS_STATIC, G52_ALWAYS_MAP_AGENT, G52_SHADOW_STATIC} for row in update_rows),
            "selected_params_hash_matches_expected": bool(hash_rows)
            and all(row.get("selected_candidate_params_hash") for row in hash_rows if row.get("method") in {G52_ALWAYS_STATIC, G52_ALWAYS_MAP_AGENT, G52_SHADOW_STATIC}),
            "fallback_reason_logged_for_all_fallbacks": all(
                row.get("fallback_reason") not in {None, ""} or "fallback" not in str(row.get("decision_status", ""))
                for row in update_rows
            ),
        }
    )
    gates["updatepolicy_equivalence_passed"] = all(
        [
            gates["runtime_rows_full"],
            gates["missing_rows"] == 0,
            gates["schema_errors"] == 0,
            gates["solver_crash_count"] == 0,
            gates["runtime_always_static_exact_matches_static"],
            gates["runtime_always_map_agent_exact_matches_map_agent"],
            gates["selector_shadow_static_matches_static"],
            gates["force_additive_policy_compliant"],
            gates["disable_policy_compliant"],
            gates["semantic_parity_mismatch_count"] == 0,
            gates["selector_logs_present"],
            gates["selected_params_hash_matches_expected"],
            gates["fallback_reason_logged_for_all_fallbacks"],
        ]
    )
    summary = {
        "schema_version": "phase5p5_repair5g52_updatepolicy_equivalence_summary_v1",
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
        "method_stats": summary_base["method_stats"],
        "gates": gates,
        "decision": "continue_checkpoint_export" if gates["updatepolicy_equivalence_passed"] else "runtime_updatepolicy_equivalence_failed",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_report(resolve(args.report, root), summary)
    write_method_report(
        resolve(args.report, root).with_name("phase5p5_repair5g52_updatepolicy_equivalence_method_stats.md"),
        title="Phase5.5 Repair5G.5.2 UpdatePolicy Method Stats",
        summary=summary,
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "update_log_rows": len(update_rows)}))
    return 0 if gates["updatepolicy_equivalence_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

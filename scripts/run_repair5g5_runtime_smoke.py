"""Run Repair5G.5 runtime contextual selector smoke on observed IDs only."""

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
    G5_RUNTIME,
    G5_SMOKE_METHODS,
    MAPS,
    actual_methods_for_reported,
    build_analysis_rows,
    load_json,
    method_specs,
    prepare_scenarios,
    rel,
    repo_root,
    resolve,
    run_solver_grid_g5,
    sha256_file,
    summarise_runtime_run,
    write_json,
    write_method_report,
    write_simple_audit,
)
from repair5g3_common import git_value, read_jsonl  # noqa: E402


DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g5_runtime_smoke_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g5_runtime_smoke_scenario_generation.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g5_runtime_smoke"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g5_runtime_smoke.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g5_runtime_smoke_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g5_runtime_smoke_ltm_updates.jsonl"
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g5_runtime_smoke_paired.csv"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g5_runtime_smoke_summary.csv"
DEFAULT_BY_GROUP = "outputs/tables/phase5p5_repair5g5_runtime_smoke_by_map_agent.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g5_runtime_smoke_oracle_regret.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g5_runtime_smoke_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g5_runtime_smoke_summary.json"
DEFAULT_AUDIT = "outputs/reports/phase5p5_repair5g5_runtime_smoke_audit.md"
DEFAULT_GAP = "outputs/reports/phase5p5_repair5g5_runtime_integration_gap.md"


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
    parser.add_argument("--instance-ids", nargs="+", type=int, default=list(range(126, 136)))
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
    parser.add_argument("--gap-report", type=Path, default=Path(DEFAULT_GAP))
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    frozen_spec = load_json(resolve(args.frozen_selector_spec_json, root))
    selector_spec = resolve(args.selector_spec_json, root)
    if not selector_spec.exists():
        raise SystemExit("selector spec has not been exported")
    reported_methods = list(G5_SMOKE_METHODS)
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
            manifest="phase5p5-repair5g5-runtime-smoke",
            status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
        )
    raw_rows = [row for row in read_jsonl(output_jsonl) if str(row.get("method")) in set(actual_methods)]
    rows = build_analysis_rows(raw_rows, frozen_spec, reported_methods)
    commands = read_jsonl(command_log)
    update_rows = read_jsonl(update_log)
    runtime_summary, _paired = summarise_runtime_run(
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
    gates = runtime_summary["gates"]
    gates["runtime_smoke_gates_passed"] = all(
        [
            gates["runtime_rows_full"],
            gates["missing_rows"] == 0,
            gates["schema_errors"] == 0,
            gates["solver_crash_count"] == 0,
            gates["selector_logs_present"],
            gates["allowed_feature_policy_passed"],
            gates["forbidden_feature_policy_passed"],
            gates["runtime_contextual_selector_mean_delta_ratio_vs_ltm_lt_0"],
            gates["runtime_contextual_selector_not_broadly_harmful"],
        ]
    )
    summary = {
        "schema_version": "phase5p5_repair5g5_runtime_smoke_summary_v1",
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
        "method_stats": runtime_summary["method_stats"],
        "gates": gates,
        "selector_spec": rel(selector_spec, root),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_method_report(resolve(args.report, root), title="Phase5.5 Repair5G.5 Runtime Smoke Report", summary=summary)
    write_simple_audit(resolve(args.audit_report, root), "Phase5.5 Repair5G.5 Runtime Smoke Audit", summary)
    if gates["runtime_smoke_gates_passed"]:
        manifest_path = selector_spec.parent / "export_manifest.json"
        candidate_path = selector_spec.parent / "candidate_set.csv"
        feature_path = selector_spec.parent / "feature_schema.json"
        frozen_spec = {
            "schema_version": "phase5p5_repair5g5_frozen_learned_runtime_selector_spec_v1",
            "training_data_ranges": "observed IDs 1..165 only",
            "dev_data_ranges": "G4 learning-bridge validation rows and runtime smoke IDs 126..135",
            "observed_ids_used": "1..165; runtime smoke used 126..135 only",
            "forbidden_final_ids": "166..205 primary fresh learned-runtime holdout",
            "selector_hash": sha256_file(selector_spec),
            "candidate_set_hash": sha256_file(candidate_path),
            "feature_schema_hash": sha256_file(feature_path),
            "export_manifest_hash": sha256_file(manifest_path),
            "runtime_binary_commit": git_value(["rev-parse", "--short", "HEAD"], root),
            "runtime_smoke_summary": rel(resolve(args.summary_json, root), root),
            "phase5p5_allowed": False,
            "phase6_allowed": False,
            "aaai_ready": False,
        }
        frozen_path = root / "outputs/reports/phase5p5_repair5g5_frozen_learned_runtime_selector_spec.json"
        write_json(frozen_path, frozen_spec)
        frozen_report = root / "outputs/reports/phase5p5_repair5g5_frozen_learned_runtime_selector_report.md"
        frozen_report.write_text(
            "# Phase5.5 Repair5G.5 Frozen Learned Runtime Selector\n\n"
            "Frozen only after observed-ID runtime smoke gates passed. Do not modify before fresh learned-runtime validation.\n\n"
            f"- selector_hash: `{frozen_spec['selector_hash']}`\n"
            f"- forbidden_final_ids: `{frozen_spec['forbidden_final_ids']}`\n"
            "- phase5p5_allowed: `false`\n"
            "- phase6_allowed: `false`\n"
            "- aaai_ready: `false`\n",
            encoding="utf-8",
        )
    else:
        runtime_stats = summary["method_stats"].get(G5_RUNTIME, {})
        gap_path = resolve(args.gap_report, root)
        gap_path.parent.mkdir(parents=True, exist_ok=True)
        gap_path.write_text(
            "# Phase5.5 Repair5G.5 Runtime Integration Gap\n\n"
            "Observed-ID runtime smoke did not pass, so the learned runtime selector remains diagnostic-only and fresh IDs 166..205 stay blocked.\n\n"
            f"- runtime_mean_delta_ratio_vs_ltm: `{gates['runtime_contextual_selector_mean_delta_ratio_vs_ltm']}`\n"
            f"- runtime_rows: `{runtime_stats.get('rows')}`\n"
            f"- runtime_better_equal_worse: `{runtime_stats.get('better')}/{runtime_stats.get('equal')}/{runtime_stats.get('worse')}`\n"
            f"- selector_logs_present: `{gates['selector_logs_present']}`\n"
            f"- allowed_feature_policy_passed: `{gates['allowed_feature_policy_passed']}`\n"
            f"- forbidden_feature_policy_passed: `{gates['forbidden_feature_policy_passed']}`\n"
            "- next_step: inspect per-update candidate timing and train a runtime-aware selector before unblocking fresh evaluation.\n"
            "- phase5p5_allowed: `false`\n"
            "- phase6_allowed: `false`\n"
            "- aaai_ready: `false`\n",
            encoding="utf-8",
        )
    print(json.dumps({"runtime_smoke_gates_passed": gates["runtime_smoke_gates_passed"], "rows": len(rows), "runtime_mean": gates["runtime_contextual_selector_mean_delta_ratio_vs_ltm"]}))
    return 0 if gates["runtime_smoke_gates_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

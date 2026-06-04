"""Export Repair5G.5.3 diagnostic checkpoints after semantic/minimal gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import MethodSpec, git_value, number  # noqa: E402
from repair5g5_common import (  # noqa: E402
    DEFAULT_BINARY,
    DEFAULT_SELECTOR_SPEC,
    DEFAULT_SOURCE_SCENARIO_DIR,
    load_json,
    prepare_scenarios,
    read_jsonl,
    repo_root,
    resolve,
    run_solver_grid_g5,
    write_json,
)
from repair5g51_common import write_text  # noqa: E402


DEFAULT_TRANSFORM_SUMMARY = "outputs/reports/phase5p5_repair5g53_update_transform_equivalence_summary.json"
DEFAULT_HOOK_SUMMARY = "outputs/reports/phase5p5_repair5g53_hook_overhead_ablation_summary.json"
DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g53_checkpoint_export_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g53_checkpoint_export_scenario_generation.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g53_checkpoint_export"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g53_checkpoint_export_runs.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g53_checkpoint_export_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g53_checkpoint_export_ltm_updates.jsonl"
DEFAULT_CHECKPOINTS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g53_update_checkpoints.jsonl"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g53_checkpoint_export_smoke_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g53_checkpoint_export_smoke_summary.json"

METHODS = [
    "repair5g53_runtime_always_static_minimal_hook",
    "repair5g53_runtime_always_map_agent_minimal_hook",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=Path(DEFAULT_BINARY))
    parser.add_argument("--selector-spec-json", type=Path, default=Path(DEFAULT_SELECTOR_SPEC))
    parser.add_argument("--transform-summary-json", type=Path, default=Path(DEFAULT_TRANSFORM_SUMMARY))
    parser.add_argument("--hook-summary-json", type=Path, default=Path(DEFAULT_HOOK_SUMMARY))
    parser.add_argument("--source-scenario-dir", type=Path, default=Path(DEFAULT_SOURCE_SCENARIO_DIR))
    parser.add_argument("--scenario-dir", type=Path, default=Path(DEFAULT_SCENARIO_DIR))
    parser.add_argument("--scenario-metadata-json", type=Path, default=Path(DEFAULT_SCENARIO_METADATA))
    parser.add_argument("--maps", nargs="+", default=["random-32-32-20", "maze-32-32-4"])
    parser.add_argument("--agent-counts", nargs="+", type=int, default=[50, 100])
    parser.add_argument("--instance-ids", nargs="+", type=int, default=list(range(146, 151)))
    parser.add_argument("--time-limit-sec", type=float, default=3.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMANDS))
    parser.add_argument("--update-log", type=Path, default=Path(DEFAULT_UPDATES))
    parser.add_argument("--checkpoint-jsonl", type=Path, default=Path(DEFAULT_CHECKPOINTS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--allow-when-blocked", action="store_true")
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def validate_instance_ids(instance_ids: list[int]) -> None:
    forbidden = [value for value in instance_ids if 166 <= int(value) <= 205]
    if forbidden:
        raise SystemExit(f"Repair5G.5.3 may not run reserved IDs 166..205: {forbidden}")


def gates_pass(root: Path, args: argparse.Namespace) -> tuple[bool, str]:
    transform = load_json(resolve(args.transform_summary_json, root))
    hook = load_json(resolve(args.hook_summary_json, root))
    if not transform:
        return False, "missing_update_transform_equivalence_summary"
    if not hook:
        return False, "missing_hook_overhead_ablation_summary"
    if not transform.get("gates", {}).get("update_transform_equivalence_passed"):
        return False, "update_transform_equivalence_failed"
    gates = hook.get("gates", {})
    if not gates.get("minimal_hook_static_matches_static") or not gates.get("minimal_hook_map_agent_matches_map_agent"):
        return False, "minimal_hook_equivalence_failed"
    return True, "gates_passed"


def write_blocked(root: Path, args: argparse.Namespace, reason: str) -> int:
    summary = {
        "schema_version": "phase5p5_repair5g53_checkpoint_export_smoke_summary_v1",
        "checkpoint_rows": 0,
        "checkpoint_export_passed": False,
        "blocked_reason": reason,
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.3 Checkpoint Export Smoke\n\n"
        f"Blocked: `{reason}`.\n\n"
        "Checkpoint export remains diagnostic-only and is not a performance runtime.\n",
    )
    print(json.dumps({"checkpoint_export_passed": False, "blocked_reason": reason}))
    return 2


def method_specs(selector_spec: Path, checkpoint_jsonl: Path) -> list[MethodSpec]:
    extra = (
        "--repair5g5-selector-spec",
        str(selector_spec),
        "--repair5g-export-update-checkpoints-jsonl",
        str(checkpoint_jsonl),
        "--repair5g-checkpoint-topk-edges",
        "0",
        "--repair5g-runtime-audit-mode",
        "audit",
    )
    return [MethodSpec(method, method, extra) for method in METHODS]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    validate_instance_ids([int(value) for value in args.instance_ids])
    root = repo_root()
    ok, reason = gates_pass(root, args)
    if not ok and not args.allow_when_blocked:
        return write_blocked(root, args, reason)
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
    checkpoint_jsonl = resolve(args.checkpoint_jsonl, root)
    if args.overwrite:
        for path in [output_jsonl, command_log, update_log, checkpoint_jsonl]:
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
            methods=method_specs(resolve(args.selector_spec_json, root), checkpoint_jsonl),
            completed=completed,
            max_workers=int(args.max_workers),
            manifest="phase5p5-repair5g53-checkpoint-export",
            status_json=output_jsonl.with_name(output_jsonl.stem + "_status.json"),
        )
    checkpoint_rows = read_jsonl(checkpoint_jsonl)
    summary = {
        "schema_version": "phase5p5_repair5g53_checkpoint_export_smoke_summary_v1",
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "checkpoint_rows": len(checkpoint_rows),
        "checkpoint_jsonl": str(checkpoint_jsonl),
        "checkpoint_export_passed": len(checkpoint_rows) > 0,
        "blocked_reason": "" if ok else reason,
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.3 Checkpoint Export Smoke\n\n"
        f"- checkpoint_rows: `{len(checkpoint_rows)}`\n"
        f"- checkpoint_export_passed: `{summary['checkpoint_export_passed']}`\n"
        f"- checkpoint_jsonl: `{checkpoint_jsonl}`\n"
        f"- diagnostic_only: `true`\n",
    )
    print(json.dumps({"checkpoint_export_passed": summary["checkpoint_export_passed"], "checkpoint_rows": len(checkpoint_rows)}))
    return 0 if summary["checkpoint_export_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

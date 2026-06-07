"""Run Repair5G.5.8 targeted primary-pair confidence expansion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from run_repair5g56_probe_budget_stability_expanded import main as run_g56_budget_probe  # noqa: E402


DEFAULT_SCENARIO_DIR = "outputs/tmp/phase5p5_repair5g58_primary_pair_scenarios"
DEFAULT_SCENARIO_METADATA = "outputs/reports/phase5p5_repair5g58_primary_pair_scenario_generation.json"
DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g58_primary_pair_confidence_expansion"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g58_primary_pair_runs.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g58_primary_pair_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g58_primary_pair_ltm_updates.jsonl"
DEFAULT_PROBES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g58_primary_pair_update_probes.jsonl"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g58_primary_pair_confidence_expansion_run.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g58_primary_pair_confidence_expansion_run_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-ids", nargs="+", default=["151..155"])
    parser.add_argument("--budgets-ms", nargs="+", type=float, default=[1000.0, 2000.0])
    parser.add_argument("--time-limit-sec", type=float, default=5.0)
    parser.add_argument("--ltm-max-iterations", type=int, default=4)
    parser.add_argument("--max-contexts-per-group", type=int, default=1)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    forwarded = [
        "--scenario-dir",
        DEFAULT_SCENARIO_DIR,
        "--scenario-metadata-json",
        DEFAULT_SCENARIO_METADATA,
        "--instance-ids",
        *[str(value) for value in args.instance_ids],
        "--budgets-ms",
        *[str(float(value)) for value in args.budgets_ms],
        "--time-limit-sec",
        str(float(args.time_limit_sec)),
        "--ltm-max-iterations",
        str(int(args.ltm_max_iterations)),
        "--max-contexts-per-group",
        str(int(args.max_contexts_per_group)),
        "--max-workers",
        str(int(args.max_workers)),
        "--output-jsonl",
        DEFAULT_JSONL,
        "--command-log",
        DEFAULT_COMMANDS,
        "--update-log",
        DEFAULT_UPDATES,
        "--probe-jsonl",
        DEFAULT_PROBES,
        "--report",
        DEFAULT_REPORT,
        "--summary-json",
        DEFAULT_SUMMARY,
    ]
    if args.skip_solver:
        forwarded.append("--skip-solver")
    if args.overwrite:
        forwarded.append("--overwrite")
    return run_g56_budget_probe(forwarded)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

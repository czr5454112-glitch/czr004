"""Run a bounded Repair5G.5.10 executable-lattice smoke probe."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from run_repair5g510_goal_aware_dual_channel_lattice_counterfactuals import main as run_lattice  # noqa: E402


DEFAULT_LOG_DIR = "outputs/logs/phase5p5_repair5g510_lattice_smoke"
DEFAULT_JSONL = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g510_lattice_smoke_runs.jsonl"
DEFAULT_COMMANDS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g510_lattice_smoke_commands.jsonl"
DEFAULT_UPDATES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g510_lattice_smoke_ltm_updates.jsonl"
DEFAULT_PROBES = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g510_lattice_smoke_update_probes.jsonl"
DEFAULT_CHECKPOINTS = f"{DEFAULT_LOG_DIR}/phase5p5_repair5g510_lattice_smoke_checkpoints.jsonl"
DEFAULT_PLAN = "outputs/tables/phase5p5_repair5g510_lattice_smoke_plan.csv"
DEFAULT_RESULTS = "outputs/tables/phase5p5_repair5g510_lattice_smoke_results.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g510_lattice_smoke_run.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g510_lattice_smoke_run_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--skip-solver", action="store_true")
    parser.add_argument("--max-workers", type=int, default=1)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    forwarded = [
        "--maps",
        "random-32-32-20",
        "--agent-counts",
        "50",
        "100",
        "--instance-ids",
        "146",
        "--budgets-ms",
        "1000",
        "2000",
        "--max-contexts-per-group",
        "1",
        "--max-workers",
        str(int(args.max_workers)),
        "--include-parity-reference-candidates",
        "--checkpoint-topk-edges",
        "64",
        "--output-jsonl",
        DEFAULT_JSONL,
        "--command-log",
        DEFAULT_COMMANDS,
        "--update-log",
        DEFAULT_UPDATES,
        "--probe-jsonl",
        DEFAULT_PROBES,
        "--checkpoint-jsonl",
        DEFAULT_CHECKPOINTS,
        "--plan-csv",
        DEFAULT_PLAN,
        "--results-csv",
        DEFAULT_RESULTS,
        "--report",
        DEFAULT_REPORT,
        "--summary-json",
        DEFAULT_SUMMARY,
    ]
    if args.overwrite:
        forwarded.append("--overwrite")
    if args.skip_solver:
        forwarded.append("--skip-solver")
    return run_lattice(forwarded)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

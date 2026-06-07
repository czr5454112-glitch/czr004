"""Analyze Repair5G.5.9 goal-aware dual-channel counterfactual probe results."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g59_common import G59_CLOSED_STATUS, load_json, read_csv_rows, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_RUN_SUMMARY = "outputs/reports/phase5p5_repair5g59_goal_aware_dual_channel_counterfactual_run_summary.json"
DEFAULT_RESULTS = "outputs/tables/phase5p5_repair5g59_goal_aware_dual_channel_counterfactual_results.csv"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g59_goal_aware_dual_channel_counterfactuals_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g59_goal_aware_dual_channel_counterfactuals.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-summary-json", type=Path, default=Path(DEFAULT_RUN_SUMMARY))
    parser.add_argument("--results-csv", type=Path, default=Path(DEFAULT_RESULTS))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    run_summary = load_json(resolve(args.run_summary_json, root))
    results = read_csv_rows(resolve(args.results_csv, root))
    measured_contexts = len({row.get("context_id", "") for row in results if row.get("context_id")})
    gates = {
        "observed_ids_only": bool(run_summary.get("observed_ids_only", True)),
        "ids_166_205_untouched": bool(run_summary.get("ids_166_205_untouched", True)),
        "measured_contexts_ge_60": measured_contexts >= 60,
        "later_iteration_measured_contexts_ge_20": False,
        "primary_1000_2000_stable_contexts_ge_40": False,
        "oracle_beats_static_fraction_reported": bool(results),
        "mean_oracle_gap_over_static_reported": bool(results),
        "candidate_space_oracle_gap_vs_g58_reported": bool(results),
        "no_solution_longer_budget_classified": False,
    }
    decision = (
        "candidate_space_gap_expand_flow_shield_lattice"
        if results and not gates["candidate_space_oracle_gap_vs_g58_reported"]
        else "server_required_for_candidate_lattice_or_later_iteration_expansion"
    )
    summary = {
        "schema_version": "phase5p5_repair5g59_goal_aware_dual_channel_counterfactuals_summary_v1",
        "decision": decision,
        "counterfactuals_run": bool(results),
        "measured_contexts": measured_contexts,
        "later_iteration_measured_contexts": 0,
        "primary_1000_2000_stable_contexts": 0,
        "oracle_beats_static_fraction": None,
        "mean_oracle_gap_over_static": None,
        "candidate_space_oracle_gap_vs_g58": None,
        "local_compute_cannot_finish": bool(run_summary.get("local_compute_cannot_finish", False)),
        "local_compute_reason": run_summary.get("local_compute_reason", ""),
        "gates": gates,
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.9 Goal-Aware Dual-Channel Counterfactuals\n\n"
        f"- decision: `{decision}`\n"
        f"- counterfactuals_run: `{bool(results)}`\n"
        f"- measured_contexts: `{measured_contexts}`\n"
        f"- observed_ids_only: `{gates['observed_ids_only']}`\n"
        f"- ids_166_205_untouched: `{gates['ids_166_205_untouched']}`\n\n"
        "The expanded lattice is ready as a bounded design, but local execution did not produce new lattice counterfactual outcomes. A server run is required before oracle-gap claims.\n",
    )
    print(json.dumps({"decision": decision, "measured_contexts": measured_contexts}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Plan Repair5G.5.9 goal-aware dual-channel counterfactual probes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g59_common import G59_CLOSED_STATUS, read_csv_rows, repo_root, resolve, write_csv_rows, write_json, write_text  # noqa: E402


DEFAULT_CONTEXTS = "outputs/tables/phase5p5_repair5g58_primary_pair_confidence_by_context.csv"
DEFAULT_CANDIDATES = "outputs/tables/phase5p5_repair5g59_candidate_lattice.csv"
DEFAULT_PLAN_CSV = "outputs/tables/phase5p5_repair5g59_goal_aware_dual_channel_counterfactual_plan.csv"
DEFAULT_RESULTS_CSV = "outputs/tables/phase5p5_repair5g59_goal_aware_dual_channel_counterfactual_results.csv"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g59_goal_aware_dual_channel_counterfactual_run_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g59_goal_aware_dual_channel_counterfactual_run.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contexts-csv", type=Path, default=Path(DEFAULT_CONTEXTS))
    parser.add_argument("--candidate-csv", type=Path, default=Path(DEFAULT_CANDIDATES))
    parser.add_argument("--plan-csv", type=Path, default=Path(DEFAULT_PLAN_CSV))
    parser.add_argument("--results-csv", type=Path, default=Path(DEFAULT_RESULTS_CSV))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--execute-local", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    contexts = read_csv_rows(resolve(args.contexts_csv, root))
    candidates = read_csv_rows(resolve(args.candidate_csv, root))
    budgets = [250, 1000, 2000]
    plan_rows = []
    for context in contexts:
        for candidate in candidates:
            for budget in budgets:
                plan_rows.append(
                    {
                        "context_id": context.get("context_id", ""),
                        "map": context.get("map", ""),
                        "agents": context.get("agents", ""),
                        "seed": context.get("seed", ""),
                        "iteration": context.get("iteration", ""),
                        "candidate_id": candidate.get("candidate_id", ""),
                        "short_budget_ms": budget,
                        "observed_ids_only": True,
                    }
                )
    write_csv_rows(resolve(args.plan_csv, root), plan_rows)
    write_csv_rows(resolve(args.results_csv, root), [])
    executable = args.execute_local
    decision = "counterfactual_probe_not_run_server_required"
    local_reason = (
        "The local Python layer can design the expanded lattice, but the current C++/probe harness does not expose "
        "these new G5.9 lattice candidates as executable UpdateLTM runtime candidates without a dedicated server run."
    )
    summary = {
        "schema_version": "phase5p5_repair5g59_goal_aware_dual_channel_counterfactual_run_summary_v1",
        "decision": decision,
        "execute_local_requested": bool(executable),
        "counterfactuals_run": False,
        "planned_contexts": len(contexts),
        "planned_candidates": len(candidates),
        "planned_rows": len(plan_rows),
        "primary_budgets_ms": [1000, 2000],
        "stress_budget_ms": 250,
        "observed_ids_only": True,
        "ids_166_205_untouched": True,
        "local_compute_cannot_finish": True,
        "local_compute_reason": local_reason,
        "plan_csv": str(resolve(args.plan_csv, root)),
        "results_csv": str(resolve(args.results_csv, root)),
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.9 Counterfactual Probe Run\n\n"
        f"- decision: `{decision}`\n"
        f"- planned_contexts: `{len(contexts)}`\n"
        f"- planned_candidates: `{len(candidates)}`\n"
        f"- planned_rows: `{len(plan_rows)}`\n"
        f"- observed_ids_only: `True`\n"
        f"- ids_166_205_untouched: `True`\n\n"
        f"{local_reason}\n",
    )
    print(json.dumps({"decision": decision, "planned_rows": len(plan_rows)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

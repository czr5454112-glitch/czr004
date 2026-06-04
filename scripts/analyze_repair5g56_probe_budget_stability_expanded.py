"""Analyze Repair5G.5.6 expanded short-probe budget stability."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g56_common import (  # noqa: E402
    G56_AGENT_COUNTS,
    G56_MAPS,
    G56_STATIC_CANDIDATE,
    G56_STABILITY_CONTEXT_TARGET,
    finite_number,
    normalized_context_key,
    normalized_context_key_text,
    read_jsonl_many,
    repo_root,
    resolve,
    score_from_label,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_G56_PROBES = "outputs/logs/phase5p5_repair5g56_probe_budget_stability/phase5p5_repair5g56_probe_budget_update_probes.jsonl"
DEFAULT_G55_PROBES = "outputs/logs/phase5p5_repair5g55_probe_budget_stability/phase5p5_repair5g55_probe_budget_update_probes.jsonl"
DEFAULT_RANKS = "outputs/tables/phase5p5_repair5g56_probe_budget_rank_stability.csv"
DEFAULT_ELIGIBLE = "outputs/tables/phase5p5_repair5g56_training_eligible_stable_contexts.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g56_probe_budget_stability.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g56_probe_budget_stability_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-jsonl", nargs="+", type=Path, default=[Path(DEFAULT_G56_PROBES), Path(DEFAULT_G55_PROBES)])
    parser.add_argument("--rank-stability-csv", type=Path, default=Path(DEFAULT_RANKS))
    parser.add_argument("--training-eligible-csv", type=Path, default=Path(DEFAULT_ELIGIBLE))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--expected-maps", nargs="+", default=G56_MAPS)
    parser.add_argument("--expected-agent-counts", nargs="+", type=int, default=G56_AGENT_COUNTS)
    return parser.parse_args(argv)


def budget_value(row: dict[str, Any]) -> float:
    return finite_number(row.get("short_budget_ms"), math.nan)


def sign_for(best_score: float, static_score: float) -> str:
    if not math.isfinite(best_score) or not math.isfinite(static_score):
        return "unmeasured"
    return "oracle_beats_static" if best_score < static_score - 1.0e-12 else "static_ties_or_beats"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    probe_paths = [resolve(path, root) for path in args.probe_jsonl]
    rows = read_jsonl_many(probe_paths)
    by_context_budget: dict[tuple[tuple[str, int, int, int, str], float], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        budget = budget_value(row)
        if math.isfinite(budget):
            by_context_budget[(normalized_context_key(row), budget)].append(row)
    context_to_budgets: dict[tuple[str, int, int, int, str], dict[float, list[dict[str, Any]]]] = defaultdict(dict)
    for (context_key, budget), group in by_context_budget.items():
        context_to_budgets[context_key][budget] = group

    rank_rows = []
    eligible_rows = []
    sign_values_seen = set()
    no_solution_warehouse_seen = False
    no_solution_warehouse_covered = False
    for context_key, budget_map in sorted(context_to_budgets.items()):
        oracle_by_budget = {}
        sign_by_budget = {}
        rank_signature_by_budget = {}
        any_no_solution = False
        for budget, group in sorted(budget_map.items()):
            ranked = sorted(
                ((score_from_label(row), row) for row in group),
                key=lambda item: (item[0], str(item[1].get("candidate_id", ""))),
            )
            finite_ranked = [(score, row) for score, row in ranked if math.isfinite(score)]
            best_score, best_row = finite_ranked[0] if finite_ranked else (math.inf, {})
            static = next((row for row in group if row.get("candidate_id") == G56_STATIC_CANDIDATE), {})
            static_score = score_from_label(static) if static else math.inf
            oracle_by_budget[budget] = str(best_row.get("candidate_id", ""))
            sign_by_budget[budget] = sign_for(best_score, static_score)
            sign_values_seen.add(sign_by_budget[budget])
            rank_signature_by_budget[budget] = tuple(str(row.get("candidate_id", "")) for _score, row in ranked)
            any_no_solution = any_no_solution or not finite_ranked
            for rank, (score, row) in enumerate(ranked, start=1):
                rank_rows.append(
                    {
                        "normalized_context_key": normalized_context_key_text(context_key),
                        "map": context_key[0],
                        "agents": context_key[1],
                        "seed": context_key[2],
                        "iteration": context_key[3],
                        "traffic_before_hash_full": context_key[4],
                        "short_budget_ms": budget,
                        "candidate_id": row.get("candidate_id", ""),
                        "rank": rank,
                        "probe_sum_of_loss_ratio": score if math.isfinite(score) else "",
                        "oracle_candidate_id_for_budget": oracle_by_budget[budget],
                        "static_vs_oracle_sign_for_budget": sign_by_budget[budget],
                    }
                )
        if "warehouse" in context_key[0] and any_no_solution:
            no_solution_warehouse_seen = True
        oracle_stable = len(set(oracle_by_budget.values())) == 1 if oracle_by_budget else False
        sign_stable = len(set(sign_by_budget.values())) == 1 if sign_by_budget else False
        rank_stable = len(set(rank_signature_by_budget.values())) == 1 if rank_signature_by_budget else False
        training_eligible = len(budget_map) >= 2 and oracle_stable and sign_stable and not any_no_solution
        if training_eligible:
            first_budget = sorted(budget_map)[0]
            eligible_rows.append(
                {
                    "normalized_context_key": normalized_context_key_text(context_key),
                    "map": context_key[0],
                    "agents": context_key[1],
                    "seed": context_key[2],
                    "iteration": context_key[3],
                    "traffic_before_hash_full": context_key[4],
                    "budget_count": len(budget_map),
                    "oracle_candidate_id": oracle_by_budget[first_budget],
                    "static_vs_oracle_sign": sign_by_budget[first_budget],
                    "oracle_candidate_stable_across_budgets": oracle_stable,
                    "candidate_rank_stable_across_budgets": rank_stable,
                    "training_eligible_label": True,
                }
            )
        no_solution_warehouse_covered = no_solution_warehouse_covered or ("warehouse" in context_key[0] and any_no_solution and len(budget_map) >= 2)

    write_csv_rows(resolve(args.rank_stability_csv, root), rank_rows)
    write_csv_rows(resolve(args.training_eligible_csv, root), eligible_rows)
    measured_contexts = sum(1 for budgets in context_to_budgets.values() if len(budgets) >= 2)
    expected_groups = {(str(map_name), int(agents)) for map_name in args.expected_maps for agents in args.expected_agent_counts}
    actual_groups = {(key[0], key[1]) for key, budgets in context_to_budgets.items() if len(budgets) >= 2}
    gates = {
        "budget_stability_measured_contexts_ge_30": measured_contexts >= G56_STABILITY_CONTEXT_TARGET,
        "training_eligible_stable_contexts_ge_30": len(eligible_rows) >= G56_STABILITY_CONTEXT_TARGET,
        "unstable_labels_separated": bool(rank_rows),
        "oracle_static_sign_stability_reported": measured_contexts > 0,
        "candidate_rank_stability_reported": measured_contexts > 0 and bool(rank_rows),
        "covers_all_maps": {group[0] for group in actual_groups} >= set(args.expected_maps),
        "covers_agents_50_and_100": {group[1] for group in actual_groups} >= set(int(value) for value in args.expected_agent_counts),
        "covers_static_and_nonstatic_win_contexts": {"oracle_beats_static", "static_ties_or_beats"} <= sign_values_seen,
        "covers_no_solution_warehouse_cases_if_present": (not no_solution_warehouse_seen) or no_solution_warehouse_covered,
        "observed_ids_only": validate_observed_rows(rows, label="Repair5G.5.6 expanded budget stability"),
    }
    gates["ids_166_205_untouched"] = gates["observed_ids_only"]
    gates["probe_budget_stability_expanded_passed"] = all(gates.values())
    summary = {
        "schema_version": "phase5p5_repair5g56_probe_budget_stability_summary_v1",
        "probe_jsonl": [str(path) for path in probe_paths],
        "probe_rows": len(rows),
        "measured_contexts": measured_contexts,
        "budget_values_ms": sorted({budget for _key, budget in by_context_budget}),
        "training_eligible_stable_contexts": len(eligible_rows),
        "unstable_contexts": max(0, measured_contexts - len(eligible_rows)),
        "rank_stability_csv": str(resolve(args.rank_stability_csv, root)),
        "training_eligible_csv": str(resolve(args.training_eligible_csv, root)),
        "gates": gates,
        "decision": "probe_budget_stability_expanded_passed" if gates["probe_budget_stability_expanded_passed"] else "probe_budget_instability_blocks_training",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "g6_training_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.6 Probe Budget Stability\n\n"
        f"- measured_contexts: `{measured_contexts}`\n"
        f"- budget_values_ms: `{summary['budget_values_ms']}`\n"
        f"- training_eligible_stable_contexts: `{len(eligible_rows)}`\n"
        f"- unstable_contexts: `{summary['unstable_contexts']}`\n"
        f"- probe_budget_stability_expanded_passed: `{gates['probe_budget_stability_expanded_passed']}`\n\n"
        "Only stable labels are eligible for G6 target construction; unstable labels remain diagnostic rows.\n",
    )
    print(json.dumps({"decision": summary["decision"], "measured_contexts": measured_contexts, "training_eligible": len(eligible_rows)}))
    return 0 if gates["observed_ids_only"] and measured_contexts > 0 else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Autopsy G5.19 ranker failures or near-misses after suite evaluation."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g519_common import (  # noqa: E402
    G519_AUTOPSY_REPORT,
    G519_AUTOPSY_SUMMARY,
    G519_CLOSED_CLAIMS,
    G519_CONTEXT_DECISIONS_CSV,
    G519_EVAL_CSV,
    G519_EVAL_SUMMARY,
    G519_FAILURE_CONTEXTS_CSV,
    G519_NEW_WIN_CONTEXTS_CSV,
    G519_ORACLE_BY_CONTEXT_CSV,
    G519_TARGETS_CSV,
    boolish,
    csv_number,
    finite_number,
    map_agent_key,
    map_family_key,
    mean,
    read_json_file,
    read_rows,
    rows_by_context,
    write_json_file,
    write_rows,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets-csv", type=Path, default=Path(G519_TARGETS_CSV))
    parser.add_argument("--oracle-by-context-csv", type=Path, default=Path(G519_ORACLE_BY_CONTEXT_CSV))
    parser.add_argument("--eval-csv", type=Path, default=Path(G519_EVAL_CSV))
    parser.add_argument("--context-decisions-csv", type=Path, default=Path(G519_CONTEXT_DECISIONS_CSV))
    parser.add_argument("--eval-summary-json", type=Path, default=Path(G519_EVAL_SUMMARY))
    parser.add_argument("--failure-contexts-csv", type=Path, default=Path(G519_FAILURE_CONTEXTS_CSV))
    parser.add_argument("--new-win-contexts-csv", type=Path, default=Path(G519_NEW_WIN_CONTEXTS_CSV))
    parser.add_argument("--report", type=Path, default=Path(G519_AUTOPSY_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G519_AUTOPSY_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    targets = read_rows(args.targets_csv)
    oracle_rows = read_rows(args.oracle_by_context_csv)
    eval_rows = read_rows(args.eval_csv)
    context_decisions = read_rows(args.context_decisions_csv)
    eval_summary = read_json_file(args.eval_summary_json)
    best_policy = str(eval_summary.get("best_policy", ""))
    best_contexts = [
        row
        for row in context_decisions
        if row.get("eval_scope") == "seed_oof" and row.get("policy") == best_policy
    ]
    new_win_rows = [row for row in oracle_rows if boolish(row.get("new_candidate_wins_budget"))]
    new_win_by_context: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in new_win_rows:
        new_win_by_context[str(row.get("normalized_context_key", ""))].append(row)
    new_win_context_rows = []
    for context, rows in sorted(new_win_by_context.items()):
        first = rows[0]
        budgets = sorted({str(row.get("short_budget_ms", "")) for row in rows})
        new_win_context_rows.append(
            {
                "normalized_context_key": context,
                "map": first.get("map", ""),
                "agents": first.get("agents", ""),
                "seed": first.get("seed", ""),
                "map_agent_group": f"{first.get('map', '')}|a{first.get('agents', '')}",
                "new_win_budgets": ",".join(budgets),
                "budget_stable_both_primary": len(budgets) == 2,
                "mean_new22_gap_vs_old14": csv_number(mean(finite_number(row.get("new22_gap_vs_old14"), math.inf) for row in rows)),
                "new22_oracle_candidates": ",".join(sorted({str(row.get("new22_oracle_candidate", "")) for row in rows})),
            }
        )

    failure_context_rows = []
    for row in best_contexts:
        if boolish(row.get("harmful_vs_static")) or finite_number(row.get("new22_oracle_regret_primary"), math.inf) > 0.005:
            failure_context_rows.append(
                {
                    "normalized_context_key": row.get("normalized_context_key", ""),
                    "policy": best_policy,
                    "map": row.get("map", ""),
                    "agents": row.get("agents", ""),
                    "seed": row.get("seed", ""),
                    "selected_candidate_id": row.get("selected_candidate_id", ""),
                    "selected_candidate_source": row.get("selected_candidate_source", ""),
                    "mean_delta_vs_static": row.get("mean_delta_vs_static", ""),
                    "harmful_vs_static": row.get("harmful_vs_static", ""),
                    "new22_oracle_regret_primary": row.get("new22_oracle_regret_primary", ""),
                    "predicted_best_candidate_id": row.get("predicted_best_candidate_id", ""),
                    "predicted_harmful_risk": row.get("predicted_harmful_risk", ""),
                    "selection_reason": row.get("selection_reason", ""),
                }
            )

    new_target_rows = [row for row in targets if boolish(row.get("is_new_candidate"))]
    new_helpful = [row for row in new_target_rows if boolish(row.get("helpful_vs_static"))]
    new_harmful = [row for row in new_target_rows if boolish(row.get("harmful_vs_static"))]
    new_winner_candidates = Counter()
    old14_winner_candidates = Counter()
    for row in targets:
        if boolish(row.get("is_new22_oracle_winner")):
            new_winner_candidates[str(row.get("candidate_id", ""))] += 1
        if boolish(row.get("is_old14_oracle_winner")):
            old14_winner_candidates[str(row.get("candidate_id", ""))] += 1
    gap_values = [finite_number(row.get("new22_gap_vs_old14"), math.inf) for row in oracle_rows]
    best_summary = eval_summary.get("best_policy_summary", {})
    eval_by_policy = {
        str(row.get("policy", "")): row
        for row in eval_rows
        if row.get("row_type") == "policy_summary" and row.get("eval_scope") == "seed_oof"
    }
    fixed_new = eval_by_policy.get("fixed_g518_best_new_by_mean_delta", {})
    fixed_new_better = finite_number(fixed_new.get("risk_adjusted_utility_lambda_0p10"), math.inf) < finite_number(best_summary.get("risk_adjusted_utility_lambda_0p10"), math.inf)
    risk_overblocked = [
        row
        for row in best_contexts
        if "fallback_static" in str(row.get("selection_reason", ""))
        and str(row.get("predicted_best_candidate_id", "")).startswith("repair5g518_grid_")
        and finite_number(row.get("predicted_harmful_risk"), math.inf) <= 0.05
    ]
    new_win_group_counts = Counter(row.get("map_agent_group", "") for row in new_win_context_rows)
    summary = {
        "schema_version": "phase5p5_repair5g519_ranker_failure_autopsy_summary_v1",
        "decision": "ranker_failure_autopsy_completed_continue_g520_planning",
        "ranker_decision": eval_summary.get("decision", ""),
        "best_policy": best_policy,
        "new_candidates_too_rare": len(new_win_context_rows) <= 3 or len(new_win_rows) <= 6,
        "new_candidate_win_contexts": len(new_win_context_rows),
        "new_candidate_win_budget_pairs": len(new_win_rows),
        "new_wins_concentrated_by_map_agent": (max(new_win_group_counts.values()) / len(new_win_context_rows) if new_win_context_rows else 0.0) >= 0.5,
        "risk_head_overblocks_new_candidates": len(risk_overblocked) > 0,
        "candidate_space_gain_small_relative_to_noise": abs(mean(gap_values)) < 0.003,
        "fixed_new_candidate_outperforms_learned_selector": fixed_new_better,
        "top_oracle_improvement_contexts": sorted(new_win_context_rows, key=lambda row: finite_number(row.get("mean_new22_gap_vs_old14"), math.inf))[:10],
        "harmful_false_positive_contexts": len([row for row in best_contexts if boolish(row.get("harmful_vs_static"))]),
        "new_candidate_budget_stable_contexts": sum(1 for row in new_win_context_rows if boolish(row.get("budget_stable_both_primary"))),
        "old14_winner_top_candidates": dict(old14_winner_candidates.most_common(10)),
        "new22_winner_top_candidates": dict(new_winner_candidates.most_common(10)),
        "next_candidate_lattice_direction": "explore near recurrent G5.18 new winners with sparse map-agent targeting" if new_win_context_rows else "return to candidate-lattice design before learned selector",
        **G519_CLOSED_CLAIMS,
    }
    write_rows(args.failure_contexts_csv, failure_context_rows)
    write_rows(args.new_win_contexts_csv, new_win_context_rows)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.19 Ranker Failure Autopsy\n\n"
        f"- ranker_decision: `{summary['ranker_decision']}`\n"
        f"- best_policy: `{best_policy}`\n"
        f"- new_candidate_win_contexts: `{summary['new_candidate_win_contexts']}`\n"
        f"- new_candidate_win_budget_pairs: `{summary['new_candidate_win_budget_pairs']}`\n"
        f"- new_candidates_too_rare: `{summary['new_candidates_too_rare']}`\n"
        f"- new_wins_concentrated_by_map_agent: `{summary['new_wins_concentrated_by_map_agent']}`\n"
        f"- risk_head_overblocks_new_candidates: `{summary['risk_head_overblocks_new_candidates']}`\n"
        f"- candidate_space_gain_small_relative_to_noise: `{summary['candidate_space_gain_small_relative_to_noise']}`\n"
        f"- fixed_new_candidate_outperforms_learned_selector: `{summary['fixed_new_candidate_outperforms_learned_selector']}`\n"
        f"- new_candidate_budget_stable_contexts: `{summary['new_candidate_budget_stable_contexts']}`\n"
        f"- next_candidate_lattice_direction: `{summary['next_candidate_lattice_direction']}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "Autopsy answers the required failure questions using the reconstructed targets, seed-OOF context decisions, and per-budget oracle rows. "
        "It does not run a solver and does not reopen Phase5.5, Phase6, runtime, or AAAI claims.\n",
    )
    print(json.dumps({"decision": summary["decision"], "best_policy": best_policy, "new_candidate_win_contexts": len(new_win_context_rows)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

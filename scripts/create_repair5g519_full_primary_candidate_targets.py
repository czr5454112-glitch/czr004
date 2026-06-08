"""Create G5.19 full-primary 22-candidate target rows from G5.18 probes."""

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

from repair5g519_common import (  # noqa: E402
    ADDITIVE_CANDIDATE,
    DEFAULT_MARGIN,
    G518_FULL_PRIMARY_RESULTS,
    G519_CANDIDATE_DISTRIBUTION_CSV,
    G519_CLOSED_CLAIMS,
    G519_ORACLE_BY_CONTEXT_CSV,
    G519_TARGETS_CSV,
    G519_TARGETS_REPORT,
    G519_TARGETS_SUMMARY,
    G519_TARGET_BUDGET_AUDIT_CSV,
    PRIMARY_BUDGETS,
    STATIC_FLOW_SHIELD_CANDIDATE,
    as_jsonable,
    best_row,
    boolish,
    candidate_param_dict,
    candidate_role,
    compact_counter,
    context_budget_key,
    csv_number,
    family_for_candidate,
    finite_number,
    finite_score,
    full_primary_candidate_ids,
    map_agent_key,
    map_family,
    mean,
    nearest_old_candidate,
    observed_id_flags,
    old14_candidate_ids,
    read_rows,
    repo_root,
    selected_metadata_by_candidate,
    selected_new_candidate_ids_from_results,
    suffix_for_lambda,
    write_json_file,
    write_rows,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, default=Path(G518_FULL_PRIMARY_RESULTS))
    parser.add_argument("--output-csv", type=Path, default=Path(G519_TARGETS_CSV))
    parser.add_argument("--budget-audit-csv", type=Path, default=Path(G519_TARGET_BUDGET_AUDIT_CSV))
    parser.add_argument("--distribution-csv", type=Path, default=Path(G519_CANDIDATE_DISTRIBUTION_CSV))
    parser.add_argument("--oracle-by-context-csv", type=Path, default=Path(G519_ORACLE_BY_CONTEXT_CSV))
    parser.add_argument("--report", type=Path, default=Path(G519_TARGETS_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G519_TARGETS_SUMMARY))
    return parser.parse_args(argv)


def score_for(group_by_candidate: dict[str, dict[str, Any]], candidate: str) -> float:
    return finite_score(group_by_candidate.get(candidate))


def rank_map(scores: dict[str, float]) -> dict[str, int]:
    ranked = sorted(scores.items(), key=lambda item: (item[1], item[0]))
    return {candidate: index + 1 for index, (candidate, _) in enumerate(ranked)}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    probe_rows = read_rows(args.input_csv)
    old_ids = set(old14_candidate_ids(root))
    candidates = full_primary_candidate_ids(probe_rows)
    new_ids = set(selected_new_candidate_ids_from_results(probe_rows, old_ids))
    selected_meta = selected_metadata_by_candidate()
    by_context_budget: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in probe_rows:
        by_context_budget[context_budget_key(row)][str(row.get("candidate_id", ""))] = row

    contexts = sorted({key for key, _budget in by_context_budget})
    target_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    oracle_context_rows: list[dict[str, Any]] = []
    distribution: dict[str, dict[str, Any]] = {}

    for context in contexts:
        budget_maps = {budget: by_context_budget[(context, budget)] for budget in PRIMARY_BUDGETS}
        first = next(iter(budget_maps[PRIMARY_BUDGETS[0]].values()))
        old_oracle_by_budget = {}
        new22_oracle_by_budget = {}
        static_score_by_budget = {}
        additive_score_by_budget = {}
        for budget, group_by_candidate in budget_maps.items():
            old_rows = [group_by_candidate[candidate] for candidate in candidates if candidate in old_ids and candidate in group_by_candidate]
            new22_rows = [group_by_candidate[candidate] for candidate in candidates if candidate in group_by_candidate]
            old_best = best_row(old_rows)
            new22_best = best_row(new22_rows)
            old_oracle_by_budget[budget] = old_best
            new22_oracle_by_budget[budget] = new22_best
            static_score_by_budget[budget] = score_for(group_by_candidate, STATIC_FLOW_SHIELD_CANDIDATE)
            additive_score_by_budget[budget] = score_for(group_by_candidate, ADDITIVE_CANDIDATE)
            oracle_context_rows.append(
                {
                    "normalized_context_key": context,
                    "map": first.get("map", ""),
                    "agents": first.get("agents", ""),
                    "seed": first.get("seed", ""),
                    "iteration": first.get("iteration", ""),
                    "traffic_before_hash_full": first.get("traffic_before_hash_full", ""),
                    "short_budget_ms": budget,
                    "old14_oracle_candidate": old_best.get("candidate_id", "") if old_best else "",
                    "old14_oracle_score": csv_number(finite_score(old_best)),
                    "new22_oracle_candidate": new22_best.get("candidate_id", "") if new22_best else "",
                    "new22_oracle_score": csv_number(finite_score(new22_best)),
                    "new_candidate_wins_budget": bool(new22_best and new22_best.get("candidate_id") in new_ids),
                    "new22_gap_vs_old14": csv_number(finite_score(new22_best) - finite_score(old_best)),
                    "static_score": csv_number(static_score_by_budget[budget]),
                    "additive_score": csv_number(additive_score_by_budget[budget]),
                    **G519_CLOSED_CLAIMS,
                }
            )

        scores_by_candidate = {
            candidate: {
                budget: score_for(budget_maps[budget], candidate)
                for budget in PRIMARY_BUDGETS
            }
            for candidate in candidates
        }
        mean_scores = {candidate: mean(scores.values()) for candidate, scores in scores_by_candidate.items()}
        ranks22 = rank_map(mean_scores)
        ranks_old14 = rank_map({candidate: score for candidate, score in mean_scores.items() if candidate in old_ids})
        old14_oracle_primary_score = mean(finite_score(old_oracle_by_budget[budget]) for budget in PRIMARY_BUDGETS)
        new22_oracle_primary_score = mean(finite_score(new22_oracle_by_budget[budget]) for budget in PRIMARY_BUDGETS)
        static_primary = mean(static_score_by_budget.values())
        additive_primary = mean(additive_score_by_budget.values())
        old14_winners = {str(old_oracle_by_budget[budget].get("candidate_id", "")) for budget in PRIMARY_BUDGETS if old_oracle_by_budget[budget]}
        new22_winners = {str(new22_oracle_by_budget[budget].get("candidate_id", "")) for budget in PRIMARY_BUDGETS if new22_oracle_by_budget[budget]}

        for candidate in candidates:
            role = candidate_role(candidate, old_ids, new_ids)
            params = candidate_param_dict(candidate)
            source_meta = selected_meta.get(candidate, {})
            source = "g518_new" if candidate in new_ids else "old14"
            family = source_meta.get("candidate_family") or family_for_candidate(candidate)
            score1000 = scores_by_candidate[candidate][1000]
            score2000 = scores_by_candidate[candidate][2000]
            mean_score = mean([score1000, score2000])
            delta_static_1000 = score1000 - static_score_by_budget[1000]
            delta_static_2000 = score2000 - static_score_by_budget[2000]
            delta_add_1000 = score1000 - additive_score_by_budget[1000]
            delta_add_2000 = score2000 - additive_score_by_budget[2000]
            mean_delta_static = mean([delta_static_1000, delta_static_2000])
            mean_delta_add = mean([delta_add_1000, delta_add_2000])
            old_regret = mean_score - old14_oracle_primary_score
            new_regret = mean_score - new22_oracle_primary_score
            nearest_old, nearest_distance = nearest_old_candidate(candidate, old_ids)
            target_weight = 1.0 + min(5.0, abs(mean_delta_static) * 100.0)
            if candidate in new22_winners:
                target_weight += 2.0
            if mean_delta_static >= DEFAULT_MARGIN:
                target_weight += 1.0
            row = {
                "normalized_context_key": context,
                "map": first.get("map", ""),
                "agents": first.get("agents", ""),
                "seed": first.get("seed", ""),
                "iteration": first.get("iteration", ""),
                "traffic_before_hash_full": first.get("traffic_before_hash_full", ""),
                "candidate_id": candidate,
                "candidate_family": family,
                "candidate_source": source,
                **params,
                "score_1000": csv_number(score1000),
                "score_2000": csv_number(score2000),
                "score_primary": csv_number(mean_score),
                "static_score_1000": csv_number(static_score_by_budget[1000]),
                "static_score_2000": csv_number(static_score_by_budget[2000]),
                "static_score_primary": csv_number(static_primary),
                "additive_score_1000": csv_number(additive_score_by_budget[1000]),
                "additive_score_2000": csv_number(additive_score_by_budget[2000]),
                "additive_score_primary": csv_number(additive_primary),
                "old14_oracle_score_1000": csv_number(finite_score(old_oracle_by_budget[1000])),
                "old14_oracle_score_2000": csv_number(finite_score(old_oracle_by_budget[2000])),
                "old14_oracle_score_primary": csv_number(old14_oracle_primary_score),
                "new22_oracle_score_1000": csv_number(finite_score(new22_oracle_by_budget[1000])),
                "new22_oracle_score_2000": csv_number(finite_score(new22_oracle_by_budget[2000])),
                "new22_oracle_score_primary": csv_number(new22_oracle_primary_score),
                "delta_vs_static_1000": csv_number(delta_static_1000),
                "delta_vs_static_2000": csv_number(delta_static_2000),
                "mean_delta_vs_static_primary": csv_number(mean_delta_static),
                "mean_delta_vs_additive_primary": csv_number(mean_delta_add),
                "old14_oracle_regret_primary": csv_number(old_regret),
                "new22_oracle_regret_primary": csv_number(new_regret),
                "rank_primary_within_22": ranks22[candidate],
                "rank_primary_within_old14_or_null": ranks_old14.get(candidate, ""),
                "oracle_candidate_old14_for_context": ",".join(sorted(old14_winners)),
                "oracle_candidate_new22_for_context": ",".join(sorted(new22_winners)),
                "is_new_candidate": candidate in new_ids,
                "is_old14_candidate": candidate in old_ids,
                "is_new22_oracle_winner": candidate in new22_winners,
                "is_old14_oracle_winner": candidate in old14_winners,
                "helpful_vs_static": mean_delta_static <= -DEFAULT_MARGIN,
                "harmful_vs_static": mean_delta_static >= DEFAULT_MARGIN,
                "near_static_neutral": abs(mean_delta_static) < DEFAULT_MARGIN,
                "static_near_oracle": (static_primary - new22_oracle_primary_score) < DEFAULT_MARGIN,
                "target_weight": csv_number(target_weight),
                "split_seed_based": "train" if int(finite_number(first.get("seed"), -1)) <= 150 else "dev",
                "map_agent_group": map_agent_key(first),
                "map_family": map_family(str(first.get("map", ""))),
                "nearest_old_candidate": nearest_old,
                "nearest_old_param_distance": csv_number(nearest_distance),
                "batch_id": source_meta.get("batch", ""),
                "surrogate_selection_score": source_meta.get("surrogate_selection_score", ""),
                "audit_only_surrogate_metadata": bool(source_meta.get("surrogate_selection_score", "")),
                "observed_ids_only": True,
                "ids_166_205_untouched": True,
                **G519_CLOSED_CLAIMS,
            }
            target_rows.append(row)
            for budget in PRIMARY_BUDGETS:
                source_budget_row = budget_maps[budget][candidate]
                audit_rows.append(
                    {
                        "normalized_context_key": context,
                        "candidate_id": candidate,
                        "candidate_source": source,
                        "short_budget_ms": budget,
                        "score": csv_number(scores_by_candidate[candidate][budget]),
                        "static_score": csv_number(static_score_by_budget[budget]),
                        "additive_score": csv_number(additive_score_by_budget[budget]),
                        "old14_oracle_score": csv_number(finite_score(old_oracle_by_budget[budget])),
                        "new22_oracle_score": csv_number(finite_score(new22_oracle_by_budget[budget])),
                        "delta_vs_static": csv_number(scores_by_candidate[candidate][budget] - static_score_by_budget[budget]),
                        "delta_vs_additive": csv_number(scores_by_candidate[candidate][budget] - additive_score_by_budget[budget]),
                        "is_budget_new22_oracle_winner": bool(
                            new22_oracle_by_budget[budget]
                            and candidate == str(new22_oracle_by_budget[budget].get("candidate_id", ""))
                        ),
                        "probe_solution_found": source_budget_row.get("probe_solution_found", ""),
                        "probe_feasible": source_budget_row.get("probe_feasible", ""),
                        "probe_runtime_ms": source_budget_row.get("probe_runtime_ms", ""),
                    }
                )

            dist = distribution.setdefault(
                candidate,
                {
                    "candidate_id": candidate,
                    "candidate_family": family,
                    "candidate_source": source,
                    "is_new_candidate": candidate in new_ids,
                    "is_old14_candidate": candidate in old_ids,
                    "contexts": 0,
                    "helpful_count": 0,
                    "harmful_count": 0,
                    "near_static_neutral_count": 0,
                    "oracle_win_count": 0,
                    "mean_delta_values": [],
                    "mean_regret_values": [],
                    "nearest_old_candidate": nearest_old,
                    "nearest_old_param_distance": nearest_distance,
                },
            )
            dist["contexts"] += 1
            dist["helpful_count"] += int(mean_delta_static <= -DEFAULT_MARGIN)
            dist["harmful_count"] += int(mean_delta_static >= DEFAULT_MARGIN)
            dist["near_static_neutral_count"] += int(abs(mean_delta_static) < DEFAULT_MARGIN)
            dist["oracle_win_count"] += int(candidate in new22_winners)
            dist["mean_delta_values"].append(mean_delta_static)
            dist["mean_regret_values"].append(new_regret)

    distribution_rows = []
    for candidate, row in sorted(distribution.items()):
        mean_delta = mean(row.pop("mean_delta_values"))
        mean_regret = mean(row.pop("mean_regret_values"))
        distribution_rows.append(
            {
                **row,
                "mean_delta_vs_static": csv_number(mean_delta),
                "mean_regret_to_new22_oracle": csv_number(mean_regret),
                "harmful_rate": csv_number(row["harmful_count"] / row["contexts"] if row["contexts"] else math.inf),
                "helpful_rate": csv_number(row["helpful_count"] / row["contexts"] if row["contexts"] else math.inf),
                "risk_adjusted_utility_lambda_0p10": csv_number(mean_delta + 0.10 * (row["harmful_count"] / row["contexts"] if row["contexts"] else math.inf)),
            }
        )

    flags = observed_id_flags(target_rows)
    new_candidate_win_contexts = sorted({row["normalized_context_key"] for row in oracle_context_rows if boolish(row.get("new_candidate_wins_budget"))})
    new_candidate_win_budget_pairs = [row for row in oracle_context_rows if boolish(row.get("new_candidate_wins_budget"))]
    best_new_rows = [row for row in distribution_rows if boolish(row.get("is_new_candidate"))]
    best_by_mean = min(best_new_rows, key=lambda row: (finite_number(row.get("mean_delta_vs_static"), math.inf), str(row.get("candidate_id", "")))) if best_new_rows else {}
    best_by_wins = max(best_new_rows, key=lambda row: (int(finite_number(row.get("oracle_win_count"), 0)), -finite_number(row.get("mean_delta_vs_static"), math.inf), str(row.get("candidate_id", "")))) if best_new_rows else {}
    best_by_risk = min(best_new_rows, key=lambda row: (finite_number(row.get("risk_adjusted_utility_lambda_0p10"), math.inf), str(row.get("candidate_id", "")))) if best_new_rows else {}
    best_by_harm = min(best_new_rows, key=lambda row: (finite_number(row.get("harmful_rate"), math.inf), finite_number(row.get("mean_delta_vs_static"), math.inf), str(row.get("candidate_id", "")))) if best_new_rows else {}
    gates = {
        "rows_eq_1320": len(target_rows) == 1320,
        "budget_audit_rows_eq_2640": len(audit_rows) == 2640,
        "contexts_eq_60": len(contexts) == 60,
        "candidates_eq_22": len(candidates) == 22,
        "old_candidate_count_eq_14": len(old_ids & set(candidates)) == 14,
        "new_candidate_count_eq_8": len(new_ids) == 8,
        "new_candidate_win_count_gt_0": len(new_candidate_win_budget_pairs) > 0,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
    }
    decision = "candidate_targets_passed_continue_feature_matrix_v8" if all(gates.values()) else "candidate_targets_failed"
    summary = {
        "schema_version": "phase5p5_repair5g519_full_primary_candidate_targets_summary_v1",
        "decision": decision,
        "target_rows": len(target_rows),
        "budget_audit_rows": len(audit_rows),
        "contexts": len(contexts),
        "candidate_count": len(candidates),
        "old_candidate_count": len(old_ids & set(candidates)),
        "new_candidate_count": len(new_ids),
        "candidate_rows_per_context": compact_counter(({"key": row["normalized_context_key"]} for row in target_rows), "key"),
        "new_candidate_win_count": len(new_candidate_win_budget_pairs),
        "new_candidate_win_contexts": len(new_candidate_win_contexts),
        "new_candidate_win_budget_pairs": len(new_candidate_win_budget_pairs),
        "best_new_single_by_mean_delta": best_by_mean.get("candidate_id", ""),
        "best_new_single_by_oracle_win_count": best_by_wins.get("candidate_id", ""),
        "best_new_single_by_risk_adjusted_utility": best_by_risk.get("candidate_id", ""),
        "best_new_single_by_low_harmful_rate": best_by_harm.get("candidate_id", ""),
        "gates": gates,
        **flags,
        **G519_CLOSED_CLAIMS,
    }
    write_rows(args.output_csv, target_rows)
    write_rows(args.budget_audit_csv, audit_rows)
    write_rows(args.distribution_csv, distribution_rows)
    write_rows(args.oracle_by_context_csv, oracle_context_rows)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.19 Full-Primary Candidate Targets\n\n"
        f"- decision: `{decision}`\n"
        f"- target_rows: `{len(target_rows)}`\n"
        f"- budget_audit_rows: `{len(audit_rows)}`\n"
        f"- contexts: `{len(contexts)}`\n"
        f"- candidate_count: `{len(candidates)}`\n"
        f"- old_candidate_count: `{len(old_ids & set(candidates))}`\n"
        f"- new_candidate_count: `{len(new_ids)}`\n"
        f"- new_candidate_win_budget_pairs: `{len(new_candidate_win_budget_pairs)}`\n"
        f"- best_new_single_by_mean_delta: `{summary['best_new_single_by_mean_delta']}`\n"
        f"- best_new_single_by_oracle_win_count: `{summary['best_new_single_by_oracle_win_count']}`\n"
        f"- best_new_single_by_risk_adjusted_utility: `{summary['best_new_single_by_risk_adjusted_utility']}`\n"
        f"- best_new_single_by_low_harmful_rate: `{summary['best_new_single_by_low_harmful_rate']}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "The G5.18 `best_new_single_candidate` is intentionally not reused as an aggregate conclusion. "
        "G5.19 recomputes best-new summaries by mean delta, oracle wins, risk-adjusted utility, and harmful-rate criteria.\n",
    )
    print(json.dumps({"decision": decision, "target_rows": len(target_rows), "new_candidate_win_count": len(new_candidate_win_budget_pairs)}))
    return 0 if decision != "candidate_targets_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

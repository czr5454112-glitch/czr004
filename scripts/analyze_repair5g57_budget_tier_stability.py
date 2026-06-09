"""Analyze Repair5G.5.7 budget-tier label stability."""

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

from repair5g57_common import (  # noqa: E402
    G57_MID_BUDGET_MS,
    G57_PRIMARY_BUDGET_MS,
    G57_SENTINEL_BUDGET_MS,
    G57_STRESS_BUDGET_MS,
    budget_summary_value,
    context_key_from_row,
    finite_number,
    format_optional_float,
    load_budget_rank_contexts,
    read_csv_rows,
    repo_root,
    resolve,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_RANK_STABILITY = "outputs/tables/phase5p5_repair5g56_probe_budget_rank_stability.csv"
DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g56_counterfactual_update_labels.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g56_oracle_by_context.csv"
DEFAULT_BY_CONTEXT = "outputs/tables/phase5p5_repair5g57_budget_tier_stability_by_context.csv"
DEFAULT_BY_MAP_AGENT = "outputs/tables/phase5p5_repair5g57_budget_tier_stability_by_map_agent.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g57_budget_tier_stability.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g57_budget_tier_stability_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rank-stability-csv", type=Path, default=Path(DEFAULT_RANK_STABILITY))
    parser.add_argument("--labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--oracle-csv", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--by-context-csv", type=Path, default=Path(DEFAULT_BY_CONTEXT))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_BY_MAP_AGENT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def agrees(left: Any, right: Any) -> bool:
    return bool(left) and bool(right) and left == right


def top_agreement(primary: dict[str, Any] | None, sentinel: dict[str, Any] | None, field: str) -> bool:
    if not primary or not sentinel:
        return False
    return tuple(primary.get(field, ())) == tuple(sentinel.get(field, ())) and bool(primary.get(field, ()))


def primary_pair_row(context: dict[str, Any]) -> dict[str, Any]:
    budgets = context["budgets"]
    stress = budgets.get(G57_STRESS_BUDGET_MS)
    mid = budgets.get(G57_MID_BUDGET_MS)
    primary = budgets.get(G57_PRIMARY_BUDGET_MS)
    sentinel = budgets.get(G57_SENTINEL_BUDGET_MS)
    primary_oracle = budget_summary_value(primary, "oracle_candidate_id")
    sentinel_oracle = budget_summary_value(sentinel, "oracle_candidate_id")
    stress_oracle = budget_summary_value(stress, "oracle_candidate_id")
    mid_oracle = budget_summary_value(mid, "oracle_candidate_id")
    primary_finite = int(budget_summary_value(primary, "finite_candidate_count", 0) or 0)
    sentinel_finite = int(budget_summary_value(sentinel, "finite_candidate_count", 0) or 0)
    stress_finite = int(budget_summary_value(stress, "finite_candidate_count", 0) or 0)
    mid_finite = int(budget_summary_value(mid, "finite_candidate_count", 0) or 0)
    primary_sentinel_measured = bool(primary and sentinel)
    oracle_1000_2000_agree = primary_sentinel_measured and agrees(primary_oracle, sentinel_oracle)
    sign_1000_2000_agree = primary_sentinel_measured and agrees(
        budget_summary_value(primary, "static_vs_oracle_sign"),
        budget_summary_value(sentinel, "static_vs_oracle_sign"),
    )
    top1_agree = top_agreement(primary, sentinel, "top1")
    top2_agree = top_agreement(primary, sentinel, "top2")
    top3_agree = top_agreement(primary, sentinel, "top3")
    feasibility_1000_2000_agree = primary_sentinel_measured and primary_finite == sentinel_finite
    no_solution_1000 = primary_sentinel_measured and primary_finite == 0
    no_solution_2000 = primary_sentinel_measured and sentinel_finite == 0
    margin_1000 = budget_summary_value(primary, "margin_vs_static", math.nan)
    margin_2000 = budget_summary_value(sentinel, "margin_vs_static", math.nan)
    if math.isfinite(finite_number(margin_1000, math.nan)) and math.isfinite(finite_number(margin_2000, math.nan)):
        margin_delta_abs = abs(float(margin_1000) - float(margin_2000))
    else:
        margin_delta_abs = math.nan
    mid_agrees_with_primary_sentinel = bool(mid) and oracle_1000_2000_agree and mid_oracle == primary_oracle
    stress_disagrees_with_primary = bool(stress and primary) and (
        stress_oracle != primary_oracle
        or budget_summary_value(stress, "static_vs_oracle_sign") != budget_summary_value(primary, "static_vs_oracle_sign")
        or stress_finite != primary_finite
    )
    return {
        "normalized_context_key": context.get("normalized_context_key", ""),
        "map": context.get("map", ""),
        "agents": context.get("agents", ""),
        "seed": context.get("seed", ""),
        "iteration": context.get("iteration", ""),
        "traffic_before_hash_full": context.get("traffic_before_hash_full", ""),
        "budgets_present": ",".join(str(int(budget)) for budget in sorted(budgets)),
        "oracle_250": stress_oracle,
        "oracle_500": mid_oracle,
        "oracle_1000": primary_oracle,
        "oracle_2000": sentinel_oracle,
        "finite_candidates_250": stress_finite,
        "finite_candidates_500": mid_finite,
        "finite_candidates_1000": primary_finite,
        "finite_candidates_2000": sentinel_finite,
        "margin_vs_static_1000": format_optional_float(margin_1000),
        "margin_vs_static_2000": format_optional_float(margin_2000),
        "margin_delta_abs_1000_2000": format_optional_float(margin_delta_abs),
        "primary_1000_2000_measured": primary_sentinel_measured,
        "oracle_agreement_1000_2000": oracle_1000_2000_agree,
        "oracle_agreement_500_with_1000_2000": mid_agrees_with_primary_sentinel,
        "static_vs_oracle_sign_1000": budget_summary_value(primary, "static_vs_oracle_sign"),
        "static_vs_oracle_sign_2000": budget_summary_value(sentinel, "static_vs_oracle_sign"),
        "static_vs_oracle_sign_agreement_1000_2000": sign_1000_2000_agree,
        "candidate_rank_top1_agreement_1000_2000": top1_agree,
        "candidate_rank_top2_agreement_1000_2000": top2_agree,
        "candidate_rank_top3_agreement_1000_2000": top3_agree,
        "feasibility_agreement_1000_2000": feasibility_1000_2000_agree,
        "no_solution_1000": no_solution_1000,
        "no_solution_2000": no_solution_2000,
        "stress_250_disagrees_with_1000": stress_disagrees_with_primary,
    }


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rank_csv = resolve(args.rank_stability_csv, root)
    labels_csv = resolve(args.labels_csv, root)
    oracle_csv = resolve(args.oracle_csv, root)
    rank_rows = read_csv_rows(rank_csv)
    labels = read_csv_rows(labels_csv)
    oracle = read_csv_rows(oracle_csv)
    contexts = load_budget_rank_contexts(rank_csv)
    context_rows = [primary_pair_row(context) for _key, context in sorted(contexts.items())]
    write_csv_rows(resolve(args.by_context_csv, root), context_rows)

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in context_rows:
        groups[(str(row.get("map", "")), str(row.get("agents", "")))].append(row)
    group_rows = []
    for (map_name, agents), rows in sorted(groups.items()):
        measured = sum(1 for row in rows if row["primary_1000_2000_measured"])
        stable = sum(1 for row in rows if row["oracle_agreement_1000_2000"] and row["static_vs_oracle_sign_agreement_1000_2000"])
        group_rows.append(
            {
                "map": map_name,
                "agents": agents,
                "context_count": len(rows),
                "primary_1000_2000_measured": measured,
                "primary_1000_2000_stable_contexts": stable,
                "stress_250_disagreements": sum(1 for row in rows if row["stress_250_disagrees_with_1000"]),
                "no_solution_1000": sum(1 for row in rows if row["no_solution_1000"]),
                "no_solution_2000": sum(1 for row in rows if row["no_solution_2000"]),
                "top1_agree_1000_2000": sum(1 for row in rows if row["candidate_rank_top1_agreement_1000_2000"]),
                "top2_agree_1000_2000": sum(1 for row in rows if row["candidate_rank_top2_agreement_1000_2000"]),
                "top3_agree_1000_2000": sum(1 for row in rows if row["candidate_rank_top3_agreement_1000_2000"]),
            }
        )
    write_csv_rows(resolve(args.by_map_agent_csv, root), group_rows)

    measured_primary = sum(1 for row in context_rows if row["primary_1000_2000_measured"])
    primary_stable = sum(
        1
        for row in context_rows
        if row["oracle_agreement_1000_2000"]
        and row["static_vs_oracle_sign_agreement_1000_2000"]
        and row["feasibility_agreement_1000_2000"]
    )
    stress_compared = sum(1 for row in context_rows if G57_STRESS_BUDGET_MS in contexts[row["normalized_context_key"]]["budgets"] and G57_PRIMARY_BUDGET_MS in contexts[row["normalized_context_key"]]["budgets"])
    stress_disagreements = sum(1 for row in context_rows if row["stress_250_disagrees_with_1000"])
    no_solution_by_budget = {}
    feasible_by_budget = {}
    for budget in [G57_STRESS_BUDGET_MS, G57_MID_BUDGET_MS, G57_PRIMARY_BUDGET_MS, G57_SENTINEL_BUDGET_MS]:
        budget_contexts = [context for context in contexts.values() if budget in context["budgets"]]
        no_solution_by_budget[str(int(budget))] = sum(1 for context in budget_contexts if int(context["budgets"][budget]["finite_candidate_count"]) == 0)
        feasible_by_budget[str(int(budget))] = sum(1 for context in budget_contexts if int(context["budgets"][budget]["finite_candidate_count"]) > 0)

    observed_rows = []
    observed_rows.extend(labels)
    observed_rows.extend(rank_rows)
    gates = {
        "budget_tier_stability_analyzed": bool(context_rows),
        "primary_1000_2000_stable_contexts_count_reported": measured_primary > 0,
        "stress_250_disagreement_rate_reported": stress_compared > 0,
        "no_solution_by_budget_reported": bool(no_solution_by_budget),
        "candidate_feasibility_by_budget_reported": bool(feasible_by_budget),
        "margin_stability_by_budget_reported": any(row.get("margin_delta_abs_1000_2000") != "" for row in context_rows),
        "observed_ids_only": validate_observed_rows(observed_rows, label="Repair5G.5.7 budget-tier stability"),
    }
    gates["ids_166_205_untouched"] = gates["observed_ids_only"]
    summary = {
        "schema_version": "phase5p5_repair5g57_budget_tier_stability_summary_v1",
        "rank_stability_csv": str(rank_csv),
        "labels_csv": str(labels_csv),
        "oracle_csv": str(oracle_csv),
        "rank_rows": len(rank_rows),
        "label_rows": len(labels),
        "oracle_rows": len(oracle),
        "context_count": len(context_rows),
        "primary_1000_2000_measured_contexts": measured_primary,
        "primary_1000_2000_stable_contexts": primary_stable,
        "oracle_agreement_1000_2000_count": sum(1 for row in context_rows if row["oracle_agreement_1000_2000"]),
        "oracle_agreement_500_with_1000_2000_count": sum(1 for row in context_rows if row["oracle_agreement_500_with_1000_2000"]),
        "static_vs_oracle_sign_agreement_1000_2000_count": sum(1 for row in context_rows if row["static_vs_oracle_sign_agreement_1000_2000"]),
        "candidate_rank_top1_agreement_1000_2000_count": sum(1 for row in context_rows if row["candidate_rank_top1_agreement_1000_2000"]),
        "candidate_rank_top2_agreement_1000_2000_count": sum(1 for row in context_rows if row["candidate_rank_top2_agreement_1000_2000"]),
        "candidate_rank_top3_agreement_1000_2000_count": sum(1 for row in context_rows if row["candidate_rank_top3_agreement_1000_2000"]),
        "stress_250_compared_contexts": stress_compared,
        "stress_250_disagreement_contexts": stress_disagreements,
        "stress_250_disagreement_rate": ratio(stress_disagreements, stress_compared),
        "no_solution_by_budget": no_solution_by_budget,
        "candidate_feasibility_by_budget": feasible_by_budget,
        "by_context_csv": str(resolve(args.by_context_csv, root)),
        "by_map_agent_csv": str(resolve(args.by_map_agent_csv, root)),
        "gates": gates,
        "decision": "budget_tier_stability_analyzed" if gates["budget_tier_stability_analyzed"] else "budget_tier_analysis_failed",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "runtime_claim_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.7 Budget-Tier Stability\n\n"
        f"- context_count: `{summary['context_count']}`\n"
        f"- primary_1000_2000_measured_contexts: `{measured_primary}`\n"
        f"- primary_1000_2000_stable_contexts: `{primary_stable}`\n"
        f"- oracle_agreement_1000_2000_count: `{summary['oracle_agreement_1000_2000_count']}`\n"
        f"- oracle_agreement_500_with_1000_2000_count: `{summary['oracle_agreement_500_with_1000_2000_count']}`\n"
        f"- stress_250_disagreement_rate: `{summary['stress_250_disagreement_rate']}`\n"
        f"- no_solution_by_budget: `{json.dumps(no_solution_by_budget, sort_keys=True)}`\n"
        f"- budget_tier_stability_analyzed: `{gates['budget_tier_stability_analyzed']}`\n\n"
        "The 250 ms tier is treated as a stress diagnostic. The primary training-confidence pair is 1000/2000 ms.\n",
    )
    print(json.dumps({"decision": summary["decision"], "primary_1000_2000_stable_contexts": primary_stable}))
    return 0 if gates["budget_tier_stability_analyzed"] and gates["observed_ids_only"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

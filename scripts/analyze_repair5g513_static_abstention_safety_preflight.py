"""Static, abstention, budget, and OOD-like safety preflight for G5.13."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import (  # noqa: E402
    DEFAULT_MARGIN,
    STATIC_FLOW_SHIELD_CANDIDATE,
    boolish,
    count_by,
    finite_number,
    map_family,
    mean,
    observed_id_flags,
    read_csv_rows,
    read_json,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)
from repair5g513_common import G513_CLOSED_CLAIMS, grouped_contexts, select_candidate  # noqa: E402


DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g512_candidate_regret_targets.csv"
DEFAULT_DECISIONS = "outputs/tables/phase5p5_repair5g512_candidate_ranker_context_decisions.csv"
DEFAULT_MODEL = "outputs/reports/phase5p5_repair5g512_candidate_ranker_model.json"
DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g513_static_abstention_safety_preflight.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g513_static_abstention_safety_preflight.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g513_static_abstention_safety_preflight_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--context-decisions-csv", type=Path, default=Path(DEFAULT_DECISIONS))
    parser.add_argument("--model-json", type=Path, default=Path(DEFAULT_MODEL))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def candidate_budget_sensitive(row: dict[str, Any]) -> tuple[bool, str]:
    delta_1000 = finite_number(row.get("delta_vs_static_1000"), math.inf)
    delta_2000 = finite_number(row.get("delta_vs_static_2000"), math.inf)
    if delta_1000 >= DEFAULT_MARGIN and delta_2000 <= -DEFAULT_MARGIN:
        return True, "1000_bad_2000_good"
    if delta_1000 <= -DEFAULT_MARGIN and delta_2000 >= DEFAULT_MARGIN:
        return True, "1000_good_2000_bad"
    return False, ""


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.targets_csv, root))
    decisions = read_csv_rows(resolve(args.context_decisions_csv, root))
    model = read_json(resolve(args.model_json, root))
    dev_rows = [row for row in rows if row.get("split") == "dev"]
    train_rows = [row for row in rows if row.get("split") == "train"]
    grouped = grouped_contexts(dev_rows)
    decision_by_context = {str(row.get("normalized_context_key", "")): row for row in decisions}
    train_map_agents = {f"{row.get('map', '')}|a{row.get('agents', '')}" for row in train_rows}
    train_map_families = {map_family(str(row.get("map", ""))) for row in train_rows}
    thresholds = model.get("thresholds", {})
    uncertainty_margin = max(0.005, finite_number(thresholds.get("confidence_margin_threshold"), 0.0) + 0.005)
    risk_threshold = finite_number(thresholds.get("harmful_risk_threshold"), 0.075)
    delta_threshold = finite_number(thresholds.get("predicted_delta_threshold"), -0.01)

    output_rows: list[dict[str, Any]] = []
    for key, group in sorted(grouped.items()):
        static = select_candidate(group, STATIC_FLOW_SHIELD_CANDIDATE)
        decision = decision_by_context.get(key, {})
        selected = select_candidate(group, str(decision.get("selected_candidate_id", STATIC_FLOW_SHIELD_CANDIDATE)))
        oracle_regret_static = finite_number(static.get("oracle_regret_primary"), math.inf)
        static_wins = finite_number(static.get("rank_primary"), math.inf) <= 1.0
        static_near_oracle = oracle_regret_static <= DEFAULT_MARGIN
        selected_delta = finite_number(selected.get("mean_delta_vs_static_primary"), math.inf)
        selected_nonstatic = str(selected.get("candidate_id", "")) != STATIC_FLOW_SHIELD_CANDIDATE
        harmful_false_positive = selected_nonstatic and selected_delta >= DEFAULT_MARGIN
        predicted_risk = finite_number(decision.get("predicted_best_harmful_risk"), math.inf)
        predicted_margin = finite_number(decision.get("predicted_margin"), math.inf)
        predicted_delta = finite_number(decision.get("predicted_best_delta"), math.inf)
        high_uncertainty = (
            abs(predicted_risk - risk_threshold) <= 0.025
            or predicted_margin <= uncertainty_margin
            or abs(predicted_delta - delta_threshold) <= 0.005
        )
        budget_sensitive = []
        infeasible_cells = 0
        for row in group:
            sensitive, label = candidate_budget_sensitive(row)
            if sensitive:
                budget_sensitive.append(f"{row.get('candidate_id', '')}:{label}")
            infeasible_cells += 1 if boolish(row.get("score_1000_penalized_infeasible")) else 0
            infeasible_cells += 1 if boolish(row.get("score_2000_penalized_infeasible")) else 0
        map_agent = f"{selected.get('map', '')}|a{selected.get('agents', '')}"
        family = map_family(str(selected.get("map", "")))
        output_rows.append(
            {
                "normalized_context_key": key,
                "map": selected.get("map", ""),
                "map_family": family,
                "agents": selected.get("agents", ""),
                "seed": selected.get("seed", ""),
                "selected_candidate_id": selected.get("candidate_id", ""),
                "selected_delta_vs_static": selected_delta,
                "static_rank_primary": static.get("rank_primary", ""),
                "static_regret_to_oracle": oracle_regret_static,
                "static_wins_context": static_wins,
                "static_near_oracle_context": static_near_oracle,
                "ranker_harmful_false_positive": harmful_false_positive,
                "high_predicted_uncertainty": high_uncertainty,
                "predicted_best_delta": decision.get("predicted_best_delta", ""),
                "predicted_best_harmful_risk": decision.get("predicted_best_harmful_risk", ""),
                "predicted_margin": decision.get("predicted_margin", ""),
                "budget_sensitive_context": bool(budget_sensitive),
                "budget_sensitive_cases": ";".join(budget_sensitive),
                "infeasible_primary_cells": infeasible_cells,
                "no_solution_or_infeasible_context": infeasible_cells > 0,
                "train_map_agent_seen": map_agent in train_map_agents,
                "train_map_family_seen": family in train_map_families,
                "ood_like_map_agent_holdout": map_agent not in train_map_agents,
                "ood_like_map_family_holdout": family not in train_map_families,
            }
        )

    static_wins = sum(1 for row in output_rows if row["static_wins_context"])
    static_near_oracle = sum(1 for row in output_rows if row["static_near_oracle_context"])
    harmful_false_positive = sum(1 for row in output_rows if row["ranker_harmful_false_positive"])
    high_uncertainty = sum(1 for row in output_rows if row["high_predicted_uncertainty"])
    budget_sensitive = sum(1 for row in output_rows if row["budget_sensitive_context"])
    no_solution_or_infeasible = sum(1 for row in output_rows if row["no_solution_or_infeasible_context"])
    ood_map_agent = sum(1 for row in output_rows if row["ood_like_map_agent_holdout"])
    ood_map_family = sum(1 for row in output_rows if row["ood_like_map_family_holdout"])
    decision = "static_abstention_safety_package_incomplete_continue_local"
    flags = observed_id_flags(output_rows)
    summary = {
        "schema_version": "phase5p5_repair5g513_static_abstention_safety_preflight_summary_v1",
        "decision": decision,
        "dev_contexts": len(output_rows),
        "static_wins_contexts": static_wins,
        "static_near_oracle_contexts": static_near_oracle,
        "ranker_harmful_false_positive_contexts": harmful_false_positive,
        "high_predicted_uncertainty_contexts": high_uncertainty,
        "budget_sensitive_contexts": budget_sensitive,
        "no_solution_or_infeasible_contexts": no_solution_or_infeasible,
        "ood_like_map_agent_holdout_contexts": ood_map_agent,
        "ood_like_map_family_holdout_contexts": ood_map_family,
        "selected_contexts_by_map_family": count_by(output_rows, "map_family"),
        "mean_static_regret_to_oracle": mean(finite_number(row.get("static_regret_to_oracle"), math.inf) for row in output_rows),
        "safety_package_complete": False,
        "reason": "Existing observed-ID artifacts support a boundary preflight, but no-solution, budget-abstain, and OOD coverage are not sufficient for runtime promotion.",
        **flags,
        **G513_CLOSED_CLAIMS,
    }
    write_csv_rows(resolve(args.output_csv, root), output_rows)
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.13 Static/Abstention Safety Preflight\n\n"
        f"- decision: `{decision}`\n"
        f"- dev_contexts: `{len(output_rows)}`\n"
        f"- static_wins_contexts: `{static_wins}`\n"
        f"- static_near_oracle_contexts: `{static_near_oracle}`\n"
        f"- ranker_harmful_false_positive_contexts: `{harmful_false_positive}`\n"
        f"- high_predicted_uncertainty_contexts: `{high_uncertainty}`\n"
        f"- budget_sensitive_contexts: `{budget_sensitive}`\n"
        f"- no_solution_or_infeasible_contexts: `{no_solution_or_infeasible}`\n"
        f"- ood_like_map_agent_holdout_contexts: `{ood_map_agent}`\n"
        f"- ood_like_map_family_holdout_contexts: `{ood_map_family}`\n"
        "- safety_package_complete: `false`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "This preflight uses existing observed-ID artifacts first. It identifies static boundaries, harmful selected contexts, high-uncertainty contexts, budget-sensitive candidates, infeasible primary cells, and observed-bank holdout coverage. "
        "It is not sufficient to open runtime, Phase5.5, Phase6, or AAAI-ready claims.\n",
    )
    print(json.dumps({"decision": decision, "dev_contexts": len(output_rows), "budget_sensitive_contexts": budget_sensitive}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

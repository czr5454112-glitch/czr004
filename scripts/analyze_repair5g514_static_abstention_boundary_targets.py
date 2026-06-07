"""Continue static/abstention boundary preflight for G5.14."""

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
from repair5g513_common import grouped_contexts, select_candidate  # noqa: E402
from repair5g514_common import DEFAULT_V4_MATRIX, G514_CLOSED_CLAIMS  # noqa: E402


DEFAULT_DECISIONS = "outputs/tables/phase5p5_repair5g514_candidate_ranker_v4_context_decisions.csv"
DEFAULT_G513_PREFLIGHT = "outputs/reports/phase5p5_repair5g513_static_abstention_safety_preflight_summary.json"
DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g514_static_abstention_boundary_targets.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g514_static_abstention_boundary_targets.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g514_static_abstention_boundary_targets_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v4-csv", type=Path, default=Path(DEFAULT_V4_MATRIX))
    parser.add_argument("--context-decisions-csv", type=Path, default=Path(DEFAULT_DECISIONS))
    parser.add_argument("--g513-summary-json", type=Path, default=Path(DEFAULT_G513_PREFLIGHT))
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
    rows = read_csv_rows(resolve(args.v4_csv, root))
    decisions = read_csv_rows(resolve(args.context_decisions_csv, root))
    g513 = read_json(resolve(args.g513_summary_json, root)) if resolve(args.g513_summary_json, root).exists() else {}
    dev_rows = [row for row in rows if row.get("split") == "dev"]
    train_rows = [row for row in rows if row.get("split") == "train"]
    grouped = grouped_contexts(dev_rows)
    decisions_v4 = {str(row.get("normalized_context_key", "")): row for row in decisions if row.get("policy") == "v4_ranker"}
    train_map_agents = {f"{row.get('map', '')}|a{row.get('agents', '')}" for row in train_rows}
    train_map_families = {map_family(str(row.get("map", ""))) for row in train_rows}

    output_rows = []
    for key, group in sorted(grouped.items()):
        static = select_candidate(group, STATIC_FLOW_SHIELD_CANDIDATE)
        decision = decisions_v4.get(key, {})
        selected = select_candidate(group, str(decision.get("selected_candidate_id", STATIC_FLOW_SHIELD_CANDIDATE)))
        oracle = min(group, key=lambda row: (finite_number(row.get("rank_primary"), math.inf), str(row.get("candidate_id", ""))))
        static_regret = finite_number(static.get("oracle_regret_primary"), math.inf)
        selected_delta = finite_number(selected.get("mean_delta_vs_static_primary"), math.inf)
        selected_nonstatic = str(selected.get("candidate_id", "")) != STATIC_FLOW_SHIELD_CANDIDATE
        harmful_false_positive = selected_nonstatic and selected_delta >= DEFAULT_MARGIN
        oracle_helpful = finite_number(oracle.get("mean_delta_vs_static_primary"), math.inf) <= -DEFAULT_MARGIN
        missed_helpful = str(selected.get("candidate_id", "")) == STATIC_FLOW_SHIELD_CANDIDATE and oracle_helpful
        predicted_margin = finite_number(decision.get("predicted_margin"), math.inf)
        predicted_risk = finite_number(decision.get("predicted_best_harmful_risk"), math.inf)
        high_uncertainty = predicted_margin <= 0.005 or abs(predicted_risk - 0.05) <= 0.025
        budget_cases = []
        infeasible_cells = 0
        for row in group:
            sensitive, label = candidate_budget_sensitive(row)
            if sensitive:
                budget_cases.append(f"{row.get('candidate_id', '')}:{label}")
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
                "oracle_candidate_for_context": oracle.get("candidate_id", ""),
                "selected_delta_vs_static": selected_delta,
                "static_rank_primary": static.get("rank_primary", ""),
                "static_regret_to_oracle": static_regret,
                "static_wins_context": finite_number(static.get("rank_primary"), math.inf) <= 1.0,
                "static_near_oracle_context": static_regret <= DEFAULT_MARGIN,
                "ranker_harmful_false_positive": harmful_false_positive,
                "missed_helpful_context": missed_helpful,
                "high_uncertainty_context": high_uncertainty,
                "budget_sensitive_context": bool(budget_cases),
                "budget_sensitive_cases": ";".join(budget_cases),
                "infeasible_primary_cells": infeasible_cells,
                "no_solution_or_infeasible_context": infeasible_cells > 0,
                "train_map_agent_seen": map_agent in train_map_agents,
                "train_map_family_seen": family in train_map_families,
                "ood_like_map_agent_holdout": map_agent not in train_map_agents,
                "ood_like_map_family_holdout": family not in train_map_families,
                "predicted_best_delta": decision.get("predicted_best_delta", ""),
                "predicted_best_harmful_risk": decision.get("predicted_best_harmful_risk", ""),
                "predicted_margin": decision.get("predicted_margin", ""),
            }
        )

    def count_true(field: str) -> int:
        return sum(1 for row in output_rows if row.get(field) is True)

    flags = observed_id_flags(output_rows)
    summary = {
        "schema_version": "phase5p5_repair5g514_static_abstention_boundary_targets_summary_v1",
        "decision": "static_abstention_safety_package_incomplete_continue_local",
        "dev_contexts": len(output_rows),
        "static_wins_contexts": count_true("static_wins_context"),
        "static_near_oracle_contexts": count_true("static_near_oracle_context"),
        "ranker_harmful_false_positive_contexts": count_true("ranker_harmful_false_positive"),
        "missed_helpful_contexts": count_true("missed_helpful_context"),
        "high_uncertainty_contexts": count_true("high_uncertainty_context"),
        "budget_sensitive_contexts": count_true("budget_sensitive_context"),
        "no_solution_or_infeasible_contexts": count_true("no_solution_or_infeasible_context"),
        "ood_like_map_agent_holdout_contexts": count_true("ood_like_map_agent_holdout"),
        "ood_like_map_family_holdout_contexts": count_true("ood_like_map_family_holdout"),
        "selected_contexts_by_map_family": count_by(output_rows, "map_family"),
        "mean_static_regret_to_oracle": mean(finite_number(row.get("static_regret_to_oracle"), math.inf) for row in output_rows),
        "g513_preflight_reference": {
            "decision": g513.get("decision", ""),
            "static_near_oracle_contexts": g513.get("static_near_oracle_contexts", ""),
            "ranker_harmful_false_positive_contexts": g513.get("ranker_harmful_false_positive_contexts", ""),
            "high_predicted_uncertainty_contexts": g513.get("high_predicted_uncertainty_contexts", ""),
        },
        "safety_package_complete": False,
        "reason": "G5.14 remains an offline observed-ID diagnostic; runtime readiness still lacks complete static, abstention, no-solution, budget-sensitive, and OOD coverage.",
        **flags,
        **G514_CLOSED_CLAIMS,
    }
    write_csv_rows(resolve(args.output_csv, root), output_rows)
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.14 Static/Abstention Boundary Targets\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- dev_contexts: `{len(output_rows)}`\n"
        f"- static_near_oracle_contexts: `{summary['static_near_oracle_contexts']}`\n"
        f"- ranker_harmful_false_positive_contexts: `{summary['ranker_harmful_false_positive_contexts']}`\n"
        f"- missed_helpful_contexts: `{summary['missed_helpful_contexts']}`\n"
        f"- high_uncertainty_contexts: `{summary['high_uncertainty_contexts']}`\n"
        f"- budget_sensitive_contexts: `{summary['budget_sensitive_contexts']}`\n"
        f"- no_solution_or_infeasible_contexts: `{summary['no_solution_or_infeasible_contexts']}`\n"
        f"- ood_like_map_agent_holdout_contexts: `{summary['ood_like_map_agent_holdout_contexts']}`\n"
        "- safety_package_complete: `false`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "This continues the G5.13 preflight with G5.14 v4 decisions. It is still a boundary inventory, not runtime readiness evidence.\n",
    )
    print(json.dumps({"decision": summary["decision"], "dev_contexts": len(output_rows), "missed_helpful": summary["missed_helpful_contexts"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

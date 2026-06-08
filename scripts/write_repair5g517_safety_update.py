"""Write the G5.17 static-abstention safety boundary update."""

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

from repair5g510_common import finite_number, score_from_probe  # noqa: E402
from repair5g512_common import observed_id_flags, read_json  # noqa: E402
from repair5g517_common import (  # noqa: E402
    G517_CLOSED_CLAIMS,
    G517_ORACLE_CONTEXT_TABLE,
    G517_ORACLE_SUMMARY,
    G517_SAFETY_REPORT,
    G517_SAFETY_SUMMARY,
    G517_TARGETED_RESULTS,
    STATIC_CANDIDATES,
    plan_rows,
    read_csv_dicts,
    repo_root,
    resolve,
    write_json,
    write_text,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-plan-csv", type=Path, default=Path("outputs/tables/phase5p5_repair5g516_local_targeted_probe_plan.csv"))
    parser.add_argument("--targeted-results-csv", type=Path, default=Path(G517_TARGETED_RESULTS))
    parser.add_argument("--oracle-context-csv", type=Path, default=Path(G517_ORACLE_CONTEXT_TABLE))
    parser.add_argument("--oracle-summary-json", type=Path, default=Path(G517_ORACLE_SUMMARY))
    parser.add_argument("--summary-json", type=Path, default=Path(G517_SAFETY_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G517_SAFETY_REPORT))
    return parser.parse_args(argv)


def contexts_by_category(plan: list[dict[str, Any]]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for row in plan:
        key = str(row.get("normalized_context_key", ""))
        category = str(row.get("error_category", ""))
        if key and category:
            out[category].add(key)
    return out


def static_wins(context_rows: list[dict[str, Any]]) -> list[str]:
    wins = []
    for row in context_rows:
        if str(row.get("new24_oracle_candidate", "")) in STATIC_CANDIDATES:
            wins.append(str(row.get("normalized_context_key", "")))
    return sorted(set(wins))


def budget_sensitive_contexts(context_rows: list[dict[str, Any]]) -> list[str]:
    by_context: dict[str, dict[int, str]] = defaultdict(dict)
    for row in context_rows:
        budget = int(finite_number(row.get("short_budget_ms"), 0))
        by_context[str(row.get("normalized_context_key", ""))][budget] = str(row.get("new24_oracle_candidate", ""))
    return sorted(
        key
        for key, budgets in by_context.items()
        if budgets.get(1000) and budgets.get(2000) and budgets.get(1000) != budgets.get(2000)
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    plan = plan_rows(resolve(args.probe_plan_csv, root))
    results = read_csv_dicts(resolve(args.targeted_results_csv, root))
    context_rows = read_csv_dicts(resolve(args.oracle_context_csv, root))
    oracle = read_json(resolve(args.oracle_summary_json, root)) if resolve(args.oracle_summary_json, root).exists() else {}
    categories = contexts_by_category(plan)
    no_solution_or_infeasible_rows = [
        row
        for row in results
        if not math.isfinite(score_from_probe(row))
    ]
    static_win_keys = static_wins(context_rows)
    budget_sensitive = budget_sensitive_contexts(context_rows)
    abstention_reasons = {
        key: "static oracle selected in targeted diagnostic; no learned runtime policy is authorized"
        for key in static_win_keys
    }
    flags = observed_id_flags(results or plan)
    no_solution_or_infeasible_coverage = len(no_solution_or_infeasible_rows)
    budget_sensitive_coverage = len(budget_sensitive)
    ood_like_holdout_coverage = 0
    safety_package_complete = (
        len(categories.get("static_near_oracle", set())) > 0
        and len(abstention_reasons) > 0
        and no_solution_or_infeasible_coverage > 0
        and budget_sensitive_coverage > 0
        and ood_like_holdout_coverage > 0
        and oracle.get("decision") in {
            "targeted_repair_v7_offline_passed_continue_safety_package",
            "full_primary_24cand_oracle_improved_continue_ranker",
        }
    )
    decision = "static_abstention_safety_package_completed" if safety_package_complete else "static_abstention_safety_package_incomplete_continue_local"
    summary = {
        "schema_version": "phase5p5_repair5g517_static_abstention_safety_update_summary_v1",
        "decision": decision,
        "targeted_oracle_decision": oracle.get("decision", ""),
        "static_near_oracle_contexts": len(categories.get("static_near_oracle", set())),
        "static_near_oracle_context_keys": sorted(categories.get("static_near_oracle", set())),
        "static_wins": len(static_win_keys),
        "static_win_context_keys": static_win_keys,
        "no_solution_or_infeasible_coverage": no_solution_or_infeasible_coverage,
        "budget_sensitive_coverage": budget_sensitive_coverage,
        "budget_sensitive_context_keys": budget_sensitive,
        "ood_like_holdout_coverage": ood_like_holdout_coverage,
        "high_uncertainty_contexts": len(categories.get("high_uncertainty", set())),
        "high_uncertainty_context_keys": sorted(categories.get("high_uncertainty", set())),
        "harmful_false_positive_contexts": len(categories.get("harmful_false_positive", set())),
        "harmful_false_positive_context_keys": sorted(categories.get("harmful_false_positive", set())),
        "abstention_reasons_logged": bool(abstention_reasons),
        "abstention_reasons": abstention_reasons,
        "safety_package_complete": safety_package_complete,
        **flags,
        **G517_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.17 Static Abstention Safety Update\n\n"
        f"- decision: `{decision}`\n"
        f"- targeted_oracle_decision: `{summary['targeted_oracle_decision']}`\n"
        f"- static_near_oracle_contexts: `{summary['static_near_oracle_contexts']}`\n"
        f"- static_wins: `{summary['static_wins']}`\n"
        f"- no_solution_or_infeasible_coverage: `{no_solution_or_infeasible_coverage}`\n"
        f"- budget_sensitive_coverage: `{budget_sensitive_coverage}`\n"
        f"- ood_like_holdout_coverage: `{ood_like_holdout_coverage}`\n"
        f"- high_uncertainty_contexts: `{summary['high_uncertainty_contexts']}`\n"
        f"- harmful_false_positive_contexts: `{summary['harmful_false_positive_contexts']}`\n"
        f"- abstention_reasons_logged: `{summary['abstention_reasons_logged']}`\n"
        f"- safety_package_complete: `{safety_package_complete}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "Runtime and Phase5.5 remain closed because the current G5.17 package does not cover no-solution/infeasible, OOD-like holdout, and complete abstention cases.\n",
    )
    print(json.dumps({"decision": decision, "safety_package_complete": safety_package_complete}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

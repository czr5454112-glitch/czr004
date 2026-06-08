"""Update static/abstention/no-solution/budget/OOD safety diagnostics for G5.16."""

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

from repair5g512_common import DEFAULT_MARGIN, finite_number, read_csv_rows, read_json, repo_root, resolve, write_json, write_text  # noqa: E402
from repair5g513_common import grouped_contexts, select_candidate  # noqa: E402
from repair5g516_common import (  # noqa: E402
    DEFAULT_G516_EVAL_CONTEXTS,
    DEFAULT_G516_EVAL_SUMMARY,
    DEFAULT_G516_V6_MATRIX,
    G516_CLOSED_CLAIMS,
)


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g516_safety_package_update.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g516_safety_package_update_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_G516_V6_MATRIX))
    parser.add_argument("--context-decisions-csv", type=Path, default=Path(DEFAULT_G516_EVAL_CONTEXTS))
    parser.add_argument("--eval-summary-json", type=Path, default=Path(DEFAULT_G516_EVAL_SUMMARY))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    return parser.parse_args(argv)


def primary_contexts(context_rows: list[dict[str, Any]], policy: str) -> list[dict[str, Any]]:
    return [row for row in context_rows if row.get("eval_scope") == "oof" and row.get("policy") == policy]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_csv, root))
    context_rows = read_csv_rows(resolve(args.context_decisions_csv, root))
    eval_summary = read_json(resolve(args.eval_summary_json, root))
    primary_policy = str(eval_summary.get("primary_policy_name", ""))
    decisions = primary_contexts(context_rows, primary_policy)
    groups = grouped_contexts(rows)
    missed_helpful = []
    static_near = []
    harmful_fp = []
    high_uncertainty = []
    abstention_reasons = {}
    for decision_row in decisions:
        key = str(decision_row.get("normalized_context_key", ""))
        group = groups.get(key, [])
        if not group:
            continue
        selected = select_candidate(group, str(decision_row.get("selected_candidate_id", "")))
        static = select_candidate(group, "repair5g59_static_flow_shield")
        oracle_id = str(selected.get("oracle_candidate_for_context", ""))
        oracle = select_candidate(group, oracle_id)
        selected_delta = finite_number(selected.get("mean_delta_vs_static_primary"), math.inf)
        oracle_delta = finite_number(oracle.get("mean_delta_vs_static_primary"), math.inf)
        if str(selected.get("candidate_id", "")) == "repair5g59_static_flow_shield" and oracle_id != "repair5g59_static_flow_shield" and oracle_delta <= -DEFAULT_MARGIN:
            missed_helpful.append(key)
            abstention_reasons[key] = decision_row.get("selection_reason", "")
        if finite_number(static.get("oracle_regret_primary"), math.inf) <= DEFAULT_MARGIN:
            static_near.append(key)
        if str(selected.get("candidate_id", "")) != "repair5g59_static_flow_shield" and selected_delta >= DEFAULT_MARGIN:
            harmful_fp.append(key)
        if str(decision_row.get("high_uncertainty_context", "")).lower() == "true":
            high_uncertainty.append(key)
    no_solution_or_infeasible_coverage = 0
    budget_sensitive_coverage = 0
    ood_like_holdout_coverage = 0
    static_boundary_exists = len(static_near) > 0
    abstention_reasons_logged = len(abstention_reasons) > 0
    harmful_false_positives_controlled = len(harmful_fp) <= 2
    safety_package_complete = (
        static_boundary_exists
        and abstention_reasons_logged
        and harmful_false_positives_controlled
        and no_solution_or_infeasible_coverage > 0
        and budget_sensitive_coverage > 0
        and ood_like_holdout_coverage > 0
    )
    decision = "static_abstention_safety_package_completed" if safety_package_complete else "static_abstention_safety_package_incomplete_continue_local"
    summary = {
        "schema_version": "phase5p5_repair5g516_safety_package_update_summary_v1",
        "decision": decision,
        "primary_policy_name": primary_policy,
        "contexts": len(decisions),
        "missed_helpful_contexts": len(missed_helpful),
        "missed_helpful_context_keys": missed_helpful,
        "static_near_oracle_contexts": len(static_near),
        "static_near_oracle_context_keys": static_near,
        "harmful_false_positive_contexts": len(harmful_fp),
        "harmful_false_positive_context_keys": harmful_fp,
        "high_uncertainty_contexts": len(high_uncertainty),
        "high_uncertainty_context_keys": high_uncertainty,
        "static_boundary_exists": static_boundary_exists,
        "abstention_reasons_logged": abstention_reasons_logged,
        "abstention_reasons": abstention_reasons,
        "harmful_false_positives_controlled": harmful_false_positives_controlled,
        "no_solution_or_infeasible_coverage": no_solution_or_infeasible_coverage,
        "budget_sensitive_coverage": budget_sensitive_coverage,
        "ood_like_holdout_coverage": ood_like_holdout_coverage,
        "safety_package_complete": safety_package_complete,
        **G516_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.16 Safety Package Update\n\n"
        f"- decision: `{decision}`\n"
        f"- primary_policy_name: `{primary_policy}`\n"
        f"- contexts: `{len(decisions)}`\n"
        f"- missed_helpful_contexts: `{len(missed_helpful)}`\n"
        f"- static_near_oracle_contexts: `{len(static_near)}`\n"
        f"- harmful_false_positive_contexts: `{len(harmful_fp)}`\n"
        f"- high_uncertainty_contexts: `{len(high_uncertainty)}`\n"
        f"- no_solution_or_infeasible_coverage: `{no_solution_or_infeasible_coverage}`\n"
        f"- budget_sensitive_coverage: `{budget_sensitive_coverage}`\n"
        f"- ood_like_holdout_coverage: `{ood_like_holdout_coverage}`\n"
        f"- safety_package_complete: `{safety_package_complete}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "Runtime remains closed because no no-solution/infeasible, budget-sensitive, or OOD-like holdout coverage exists in the current table-only G5.16 package.\n",
    )
    print(json.dumps({"decision": decision, "safety_package_complete": safety_package_complete, "harmful_false_positive_contexts": len(harmful_fp)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Update static/abstention/safety package diagnostics for G5.15."""

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
from repair5g515_common import DEFAULT_EVAL_CONTEXTS, DEFAULT_EVAL_SUMMARY, DEFAULT_V5_MATRIX, G515_CLOSED_CLAIMS  # noqa: E402


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g515_static_abstention_safety_update.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g515_static_abstention_safety_update_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_V5_MATRIX))
    parser.add_argument("--context-decisions-csv", type=Path, default=Path(DEFAULT_EVAL_CONTEXTS))
    parser.add_argument("--eval-summary-json", type=Path, default=Path(DEFAULT_EVAL_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def group_for_key(groups: dict[str, list[dict[str, Any]]], key: str) -> list[dict[str, Any]]:
    return groups.get(key, [])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_csv, root))
    context_rows = read_csv_rows(resolve(args.context_decisions_csv, root))
    eval_summary = read_json(resolve(args.eval_summary_json, root))
    primary_policy = str(eval_summary.get("primary_policy_name", ""))
    primary_contexts = [
        row
        for row in context_rows
        if row.get("eval_scope") == "oof" and row.get("policy") == primary_policy
    ]
    groups = grouped_contexts(rows)
    missed_helpful = []
    static_near_oracle = []
    harmful_false_positive = []
    high_uncertainty = []
    for decision in primary_contexts:
        key = str(decision.get("normalized_context_key", ""))
        group = group_for_key(groups, key)
        if not group:
            continue
        static = select_candidate(group, "repair5g59_static_flow_shield")
        oracle_id = str(static.get("oracle_candidate_for_context", ""))
        oracle = select_candidate(group, oracle_id)
        selected = select_candidate(group, str(decision.get("selected_candidate_id", "")))
        oracle_delta = finite_number(oracle.get("mean_delta_vs_static_primary"), math.inf)
        selected_delta = finite_number(selected.get("mean_delta_vs_static_primary"), math.inf)
        if str(selected.get("candidate_id", "")) == "repair5g59_static_flow_shield" and oracle_id != "repair5g59_static_flow_shield" and oracle_delta <= -DEFAULT_MARGIN:
            missed_helpful.append(key)
        if finite_number(static.get("oracle_regret_primary"), math.inf) <= DEFAULT_MARGIN:
            static_near_oracle.append(key)
        if str(selected.get("candidate_id", "")) != "repair5g59_static_flow_shield" and selected_delta >= DEFAULT_MARGIN:
            harmful_false_positive.append(key)
        margin = finite_number(decision.get("predicted_margin"), math.nan)
        risk = finite_number(decision.get("predicted_best_harmful_risk"), math.nan)
        if (math.isfinite(margin) and margin < 0.005) or (math.isfinite(risk) and 0.05 < risk < 0.20):
            high_uncertainty.append(key)
    no_solution_or_infeasible_contexts = 0
    budget_sensitive_contexts = 0
    ood_like_holdout_contexts = 0
    safety_package_complete = (
        len(harmful_false_positive) == 0
        and no_solution_or_infeasible_contexts > 0
        and budget_sensitive_contexts > 0
        and ood_like_holdout_contexts > 0
    )
    decision = (
        "static_abstention_safety_package_completed"
        if safety_package_complete
        else "static_abstention_safety_package_incomplete_continue_local"
    )
    summary = {
        "schema_version": "phase5p5_repair5g515_static_abstention_safety_update_summary_v1",
        "decision": decision,
        "primary_policy_name": primary_policy,
        "contexts": len(primary_contexts),
        "missed_helpful_contexts": len(missed_helpful),
        "missed_helpful_context_keys": missed_helpful,
        "static_near_oracle_contexts": len(static_near_oracle),
        "static_near_oracle_context_keys": static_near_oracle,
        "harmful_false_positive_contexts": len(harmful_false_positive),
        "harmful_false_positive_context_keys": harmful_false_positive,
        "high_uncertainty_contexts": len(high_uncertainty),
        "high_uncertainty_context_keys": high_uncertainty,
        "no_solution_or_infeasible_coverage": no_solution_or_infeasible_contexts,
        "budget_sensitive_coverage": budget_sensitive_contexts,
        "ood_like_holdout_coverage": ood_like_holdout_contexts,
        "safety_package_complete": safety_package_complete,
        **G515_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.15 Static/Abstention Safety Update\n\n"
        f"- decision: `{decision}`\n"
        f"- primary_policy_name: `{primary_policy}`\n"
        f"- contexts: `{len(primary_contexts)}`\n"
        f"- missed_helpful_contexts: `{len(missed_helpful)}`\n"
        f"- static_near_oracle_contexts: `{len(static_near_oracle)}`\n"
        f"- harmful_false_positive_contexts: `{len(harmful_false_positive)}`\n"
        f"- high_uncertainty_contexts: `{len(high_uncertainty)}`\n"
        f"- no_solution_or_infeasible_coverage: `{no_solution_or_infeasible_contexts}`\n"
        f"- budget_sensitive_coverage: `{budget_sensitive_contexts}`\n"
        f"- ood_like_holdout_coverage: `{ood_like_holdout_contexts}`\n"
        f"- safety_package_complete: `{safety_package_complete}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "The package remains incomplete because the current table-only G5.15 artifacts still have no no-solution/infeasible, budget-sensitive, or OOD-like holdout coverage. "
        "Runtime, Phase5.5, Phase6, and AAAI claims remain closed.\n",
    )
    print(json.dumps({"decision": decision, "harmful_false_positive_contexts": len(harmful_false_positive)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

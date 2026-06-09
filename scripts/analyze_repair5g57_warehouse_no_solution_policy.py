"""Classify Repair5G.5.7 warehouse no-solution policy outcomes."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g57_common import (  # noqa: E402
    G57_PRIMARY_BUDGET_MS,
    G57_SENTINEL_BUDGET_MS,
    budget_summary_value,
    context_key_from_row,
    count_by,
    load_budget_rank_contexts,
    load_json,
    read_csv_rows,
    repo_root,
    resolve,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_G56_SUMMARY = "outputs/reports/phase5p5_repair5g56_warehouse_probe_failure_summary.json"
DEFAULT_G56_CASES = "outputs/tables/phase5p5_repair5g56_warehouse_probe_failure_cases.csv"
DEFAULT_RANK_STABILITY = "outputs/tables/phase5p5_repair5g56_probe_budget_rank_stability.csv"
DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g57_warehouse_context_policy.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g57_warehouse_no_solution_policy.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g57_warehouse_no_solution_policy_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warehouse-summary-json", type=Path, default=Path(DEFAULT_G56_SUMMARY))
    parser.add_argument("--warehouse-cases-csv", type=Path, default=Path(DEFAULT_G56_CASES))
    parser.add_argument("--rank-stability-csv", type=Path, default=Path(DEFAULT_RANK_STABILITY))
    parser.add_argument("--warehouse-policy-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def classify_policy(case: dict[str, Any], context: dict[str, Any] | None) -> tuple[str, str]:
    source_classification = str(case.get("classification", ""))
    if not context:
        if source_classification == "no_solution_all_candidates":
            return "no_solution_abstain", "no budget-tier context available; carry forward G5.6 no-solution classification"
        return "candidate_space_gap", "no budget-tier context available for budget-sensitive warehouse case"
    primary = context["budgets"].get(G57_PRIMARY_BUDGET_MS)
    sentinel = context["budgets"].get(G57_SENTINEL_BUDGET_MS)
    primary_finite = int(budget_summary_value(primary, "finite_candidate_count", 0) or 0)
    sentinel_finite = int(budget_summary_value(sentinel, "finite_candidate_count", 0) or 0)
    primary_oracle = str(budget_summary_value(primary, "oracle_candidate_id"))
    sentinel_oracle = str(budget_summary_value(sentinel, "oracle_candidate_id"))
    if primary_finite == 0 and sentinel_finite == 0:
        return "no_solution_abstain", "no candidate solves under primary or sentinel budget"
    if primary_finite == 0 and sentinel_finite > 0:
        return "longer_budget_needed", "sentinel budget finds feasible candidates where primary budget does not"
    if primary_finite > 0 and sentinel_finite == 0:
        return "probe_budget_protocol_needs_revision", "primary budget appears feasible but sentinel budget does not"
    if primary_finite != sentinel_finite:
        return "candidate_space_gap", "candidate feasibility set changes between primary and sentinel budgets"
    if primary_oracle and sentinel_oracle and primary_oracle != sentinel_oracle:
        return "separate_warehouse_specialist_later", "warehouse oracle identity is budget-sensitive despite feasible candidates"
    if source_classification == "budget_sensitive_solution":
        return "longer_budget_needed", "G5.6 sentinel classified this warehouse case as budget-sensitive"
    return "valid_flat_static_default", "warehouse case is feasible and stable enough for static/default fallback"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    g56_summary = load_json(resolve(args.warehouse_summary_json, root))
    cases = read_csv_rows(resolve(args.warehouse_cases_csv, root))
    contexts = load_budget_rank_contexts(resolve(args.rank_stability_csv, root))
    rows = []
    for case in cases:
        key = context_key_from_row(case)
        context = contexts.get(key)
        policy, reason = classify_policy(case, context)
        primary = context["budgets"].get(G57_PRIMARY_BUDGET_MS) if context else None
        sentinel = context["budgets"].get(G57_SENTINEL_BUDGET_MS) if context else None
        rows.append(
            {
                "context_id": case.get("context_id", ""),
                "normalized_context_key": key,
                "map": case.get("map", ""),
                "agents": case.get("agents", ""),
                "seed": case.get("seed", ""),
                "iteration": case.get("iteration", ""),
                "traffic_before_hash_full": case.get("traffic_before_hash_full", ""),
                "g56_classification": case.get("classification", ""),
                "finite_candidate_count_g56": case.get("finite_candidate_count", ""),
                "finite_candidates_1000": budget_summary_value(primary, "finite_candidate_count", ""),
                "finite_candidates_2000": budget_summary_value(sentinel, "finite_candidate_count", ""),
                "oracle_1000": budget_summary_value(primary, "oracle_candidate_id", ""),
                "oracle_2000": budget_summary_value(sentinel, "oracle_candidate_id", ""),
                "warehouse_policy": policy,
                "policy_reason": reason,
                "not_silently_dropped": True,
            }
        )
    write_csv_rows(resolve(args.warehouse_policy_csv, root), rows)
    policy_counts = count_by(rows, "warehouse_policy")
    observed_ok = validate_observed_rows(rows, label="Repair5G.5.7 warehouse policy")
    warehouse_contexts = int(g56_summary.get("warehouse_contexts", len(cases)) or len(cases))
    gates = {
        "warehouse_policy_classified": bool(rows) and len(rows) == len(cases),
        "warehouse_contexts_not_silently_dropped": len(rows) == warehouse_contexts,
        "observed_ids_only": observed_ok,
    }
    gates["ids_166_205_untouched"] = observed_ok
    gates["warehouse_no_solution_policy_passed"] = all(gates.values())
    summary = {
        "schema_version": "phase5p5_repair5g57_warehouse_no_solution_policy_summary_v1",
        "source_summary_json": str(resolve(args.warehouse_summary_json, root)),
        "source_cases_csv": str(resolve(args.warehouse_cases_csv, root)),
        "warehouse_contexts": warehouse_contexts,
        "policy_rows": len(rows),
        "policy_counts": policy_counts,
        "warehouse_context_policy_csv": str(resolve(args.warehouse_policy_csv, root)),
        "gates": gates,
        "decision": "warehouse_policy_classified" if gates["warehouse_policy_classified"] else "warehouse_no_solution_policy_blocks_training",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "runtime_claim_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.7 Warehouse No-Solution Policy\n\n"
        f"- warehouse_contexts: `{warehouse_contexts}`\n"
        f"- policy_rows: `{len(rows)}`\n"
        f"- policy_counts: `{json.dumps(policy_counts, sort_keys=True)}`\n"
        f"- warehouse_policy_classified: `{gates['warehouse_policy_classified']}`\n"
        f"- warehouse_contexts_not_silently_dropped: `{gates['warehouse_contexts_not_silently_dropped']}`\n\n"
        "Warehouse no-solution rows are explicit abstain/longer-budget/specialist cases, not hidden training data loss.\n",
    )
    print(json.dumps({"decision": summary["decision"], "policy_counts": policy_counts}))
    return 0 if gates["warehouse_policy_classified"] and observed_ok else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

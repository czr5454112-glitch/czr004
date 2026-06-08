"""Decompose G5.20 no-solution/nonfinite risk into avoidable-failure semantics."""

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

from repair5g521_common import (  # noqa: E402
    DEFAULT_MARGIN,
    G519_TARGET_BUDGET_AUDIT_CSV,
    G520_SECOND_WAVE_CONTEXTS_CSV,
    G520_TARGETS_CSV,
    G521_AVOIDABLE_SEMANTICS_CSV,
    G521_AVOIDABLE_SEMANTICS_REPORT,
    G521_AVOIDABLE_SEMANTICS_SUMMARY,
    G521_CLOSED_CLAIMS,
    PRIMARY_BUDGETS,
    STATIC_FLOW_SHIELD_CANDIDATE,
    boolish,
    compact_counter,
    context_candidate_budget_key,
    csv_number,
    finite_number,
    map_agent_key,
    map_family,
    mean,
    old14_candidate_ids,
    read_rows,
    repo_root,
    row_finite_solution,
    score,
    write_json_file,
    write_rows,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets-csv", type=Path, default=Path(G520_TARGETS_CSV))
    parser.add_argument("--budget-audit-csv", type=Path, default=Path(G519_TARGET_BUDGET_AUDIT_CSV))
    parser.add_argument("--target-contexts-csv", type=Path, default=Path(G520_SECOND_WAVE_CONTEXTS_CSV))
    parser.add_argument("--output-csv", type=Path, default=Path(G521_AVOIDABLE_SEMANTICS_CSV))
    parser.add_argument("--report", type=Path, default=Path(G521_AVOIDABLE_SEMANTICS_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G521_AVOIDABLE_SEMANTICS_SUMMARY))
    return parser.parse_args(argv)


def budget_row_flags(candidate: dict[str, Any] | None, static: dict[str, Any] | None) -> dict[str, Any]:
    candidate_finite = row_finite_solution(candidate)
    static_finite = row_finite_solution(static)
    delta = score(candidate) - score(static) if candidate_finite and static_finite else math.inf
    return {
        "static_finite_on_budget": static_finite,
        "candidate_finite_on_budget": candidate_finite,
        "static_solution_found_on_budget": row_finite_solution(static),
        "candidate_solution_found_on_budget": row_finite_solution(candidate),
        "candidate_induced_no_solution_budget": static_finite and not candidate_finite,
        "candidate_recovers_static_no_solution_budget": (not static_finite) and candidate_finite,
        "both_fail_budget": (not static_finite) and (not candidate_finite),
        "both_finite_delta": csv_number(delta),
    }


def all_candidate_failures_for_context(
    budget_lookup: dict[tuple[str, str, int], dict[str, Any]],
    context: str,
    candidates: list[str],
) -> bool:
    for candidate in candidates:
        for budget in PRIMARY_BUDGETS:
            if row_finite_solution(budget_lookup.get((context, candidate, budget))):
                return False
    return True


def best_old14_by_budget(
    budget_lookup: dict[tuple[str, str, int], dict[str, Any]],
    context: str,
    old_ids: set[str],
) -> dict[int, dict[str, Any] | None]:
    out: dict[int, dict[str, Any] | None] = {}
    for budget in PRIMARY_BUDGETS:
        rows = [budget_lookup.get((context, candidate, budget)) for candidate in old_ids]
        finite = [row for row in rows if row_finite_solution(row)]
        out[budget] = min(finite, key=lambda row: (score(row), str(row.get("candidate_id", "")))) if finite else None
    return out


def primary_pair_fields(
    target: dict[str, Any],
    candidate_budget_rows: list[dict[str, Any] | None],
    static_budget_rows: list[dict[str, Any] | None],
    old14_budget_rows: dict[int, dict[str, Any] | None],
    *,
    unavoidable_context_failure: bool,
) -> dict[str, Any]:
    candidate_finite_by_budget = [row_finite_solution(row) for row in candidate_budget_rows]
    static_finite_by_budget = [row_finite_solution(row) for row in static_budget_rows]
    pairwise_static_deltas = []
    pairwise_old14_deltas = []
    for budget, candidate, static in zip(PRIMARY_BUDGETS, candidate_budget_rows, static_budget_rows):
        if row_finite_solution(candidate) and row_finite_solution(static):
            pairwise_static_deltas.append(score(candidate) - score(static))
        old14 = old14_budget_rows.get(budget)
        if row_finite_solution(candidate) and row_finite_solution(old14):
            pairwise_old14_deltas.append(score(candidate) - score(old14))
    delta_static = mean(pairwise_static_deltas)
    delta_old14 = mean(pairwise_old14_deltas)
    candidate_induced = any(static_ok and not cand_ok for static_ok, cand_ok in zip(static_finite_by_budget, candidate_finite_by_budget))
    recovery = any((not static_ok) and cand_ok for static_ok, cand_ok in zip(static_finite_by_budget, candidate_finite_by_budget))
    candidate_failure_same = any((not static_ok) and (not cand_ok) for static_ok, cand_ok in zip(static_finite_by_budget, candidate_finite_by_budget))
    budget_sensitive = len(set(candidate_finite_by_budget)) > 1 or len(set(static_finite_by_budget)) > 1
    helpful_static = math.isfinite(delta_static) and delta_static <= -DEFAULT_MARGIN
    helpful_old14 = math.isfinite(delta_old14) and delta_old14 <= -DEFAULT_MARGIN
    harmful_static = math.isfinite(delta_static) and delta_static >= DEFAULT_MARGIN
    return {
        "static_finite_primary_pair": all(static_finite_by_budget),
        "candidate_finite_primary_pair": all(candidate_finite_by_budget),
        "candidate_induced_no_solution_primary": candidate_induced,
        "candidate_recovers_static_no_solution_primary": recovery,
        "candidate_failure_same_as_static_primary": candidate_failure_same,
        "unavoidable_context_failure_primary": unavoidable_context_failure,
        "budget_sensitive_failure": budget_sensitive,
        "budget_sensitive_candidate_failure": budget_sensitive and any(not value for value in candidate_finite_by_budget),
        "finite_pairwise_solution_quality": bool(pairwise_static_deltas),
        "finite_pairwise_delta_vs_static_primary": csv_number(delta_static),
        "finite_pairwise_delta_vs_best_old14_primary": csv_number(delta_old14),
        "solution_quality_helpful_vs_static_finite_pair": helpful_static,
        "solution_quality_helpful_vs_old14_finite_pair": helpful_old14,
        "solution_quality_harmful_vs_static_finite_pair": harmful_static,
    }


def group_counts(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    out = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(field, ""))].append(row)
    for key, group in sorted(grouped.items()):
        out.append(
            {
                "group_type": field,
                "group_key": key,
                "rows": len(group),
                "candidate_induced_no_solution_primary": sum(1 for row in group if boolish(row.get("candidate_induced_no_solution_primary"))),
                "candidate_recovers_static_no_solution_primary": sum(1 for row in group if boolish(row.get("candidate_recovers_static_no_solution_primary"))),
                "unavoidable_context_failure_primary": sum(1 for row in group if boolish(row.get("unavoidable_context_failure_primary"))),
                "budget_sensitive_candidate_failure": sum(1 for row in group if boolish(row.get("budget_sensitive_candidate_failure"))),
                "solution_quality_harmful_vs_static_finite_pair": sum(1 for row in group if boolish(row.get("solution_quality_harmful_vs_static_finite_pair"))),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    targets = read_rows(args.targets_csv)
    budget_rows = read_rows(args.budget_audit_csv)
    second_wave_contexts = {str(row.get("normalized_context_key", "")) for row in read_rows(args.target_contexts_csv)}
    old_ids = set(old14_candidate_ids(root))
    candidates_by_context: dict[str, list[str]] = defaultdict(list)
    for target in targets:
        context = str(target.get("normalized_context_key", ""))
        candidate = str(target.get("candidate_id", ""))
        if candidate and candidate not in candidates_by_context[context]:
            candidates_by_context[context].append(candidate)
    budget_lookup = {context_candidate_budget_key(row): row for row in budget_rows}
    rows: list[dict[str, Any]] = []
    primary_rows: list[dict[str, Any]] = []
    for target in targets:
        context = str(target.get("normalized_context_key", ""))
        candidate = str(target.get("candidate_id", ""))
        old14_by_budget = best_old14_by_budget(budget_lookup, context, old_ids)
        unavoidable = all_candidate_failures_for_context(budget_lookup, context, candidates_by_context[context])
        candidate_budget_rows = [budget_lookup.get((context, candidate, budget)) for budget in PRIMARY_BUDGETS]
        static_budget_rows = [budget_lookup.get((context, STATIC_FLOW_SHIELD_CANDIDATE, budget)) for budget in PRIMARY_BUDGETS]
        common = {
            "normalized_context_key": context,
            "map": target.get("map", ""),
            "agents": target.get("agents", ""),
            "seed": target.get("seed", ""),
            "iteration": target.get("iteration", ""),
            "traffic_before_hash_full": target.get("traffic_before_hash_full", ""),
            "map_agent_group": target.get("map_agent_group", map_agent_key(target)),
            "map_family": target.get("map_family", map_family(str(target.get("map", "")))),
            "candidate_id": candidate,
            "candidate_family": target.get("candidate_family", ""),
            "candidate_source": target.get("candidate_source", ""),
            "is_old14_candidate": target.get("is_old14_candidate", ""),
            "is_new_candidate": target.get("is_new_candidate", ""),
            "opportunity_context": context in second_wave_contexts or boolish(target.get("new_opportunity_context")),
        }
        for budget, candidate_budget, static_budget in zip(PRIMARY_BUDGETS, candidate_budget_rows, static_budget_rows):
            flags = budget_row_flags(candidate_budget, static_budget)
            rows.append(
                {
                    "row_scope": "budget",
                    "short_budget_ms": budget,
                    **common,
                    **flags,
                    "budget_sensitive_failure": "",
                    "budget_sensitive_candidate_failure": "",
                    **G521_CLOSED_CLAIMS,
                }
            )
        primary = {
            "row_scope": "primary_pair",
            "short_budget_ms": "primary_1000_2000",
            **common,
            **primary_pair_fields(
                target,
                candidate_budget_rows,
                static_budget_rows,
                old14_by_budget,
                unavoidable_context_failure=unavoidable,
            ),
            **G521_CLOSED_CLAIMS,
        }
        rows.append(primary)
        primary_rows.append(primary)

    static_primary = [row for row in primary_rows if row.get("candidate_id") == STATIC_FLOW_SHIELD_CANDIDATE]
    static_solution_quality_harmful_count = sum(1 for row in static_primary if boolish(row.get("solution_quality_harmful_vs_static_finite_pair")))
    static_candidate_induced_no_solution_count = sum(1 for row in static_primary if boolish(row.get("candidate_induced_no_solution_primary")))
    groups = (
        group_counts(primary_rows, "map_family")
        + group_counts(primary_rows, "map_agent_group")
        + group_counts(primary_rows, "candidate_family")
        + group_counts(primary_rows, "candidate_source")
        + group_counts(primary_rows, "opportunity_context")
    )
    context_counts = compact_counter(targets, "normalized_context_key")
    gates = {
        "target_contexts_eq_60": len(context_counts) == 60,
        "candidate_rows_per_context_eq_22": all(count == 22 for count in context_counts.values()),
        "primary_pair_rows_eq_1320": len(primary_rows) == 1320,
        "budget_rows_eq_2640": len(rows) - len(primary_rows) == 2640,
        "static_solution_quality_harmful_count_eq_0": static_solution_quality_harmful_count == 0,
        "static_candidate_induced_no_solution_count_eq_0": static_candidate_induced_no_solution_count == 0,
    }
    decision = "avoidable_failure_semantics_passed_continue_second_wave_pool" if all(gates.values()) else "avoidable_failure_semantics_failed_stop"
    summary = {
        "schema_version": "phase5p5_repair5g521_avoidable_failure_semantics_summary_v1",
        "decision": decision,
        "rows": len(rows),
        "primary_pair_rows": len(primary_rows),
        "budget_rows": len(rows) - len(primary_rows),
        "contexts": len(context_counts),
        "static_solution_quality_harmful_count": static_solution_quality_harmful_count,
        "static_candidate_induced_no_solution_count": static_candidate_induced_no_solution_count,
        "candidate_induced_no_solution_primary_rows": sum(1 for row in primary_rows if boolish(row.get("candidate_induced_no_solution_primary"))),
        "candidate_recovers_static_no_solution_primary_rows": sum(1 for row in primary_rows if boolish(row.get("candidate_recovers_static_no_solution_primary"))),
        "unavoidable_context_failure_primary_rows": sum(1 for row in primary_rows if boolish(row.get("unavoidable_context_failure_primary"))),
        "budget_sensitive_candidate_failure_rows": sum(1 for row in primary_rows if boolish(row.get("budget_sensitive_candidate_failure"))),
        "group_counts": groups,
        "gates": gates,
        **G521_CLOSED_CLAIMS,
    }
    write_rows(args.output_csv, rows)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.21 Avoidable Failure Semantics\n\n"
        f"- decision: `{decision}`\n"
        f"- primary_pair_rows: `{len(primary_rows)}`\n"
        f"- budget_rows: `{len(rows) - len(primary_rows)}`\n"
        f"- static_solution_quality_harmful_count: `{static_solution_quality_harmful_count}`\n"
        f"- static_candidate_induced_no_solution_count: `{static_candidate_induced_no_solution_count}`\n"
        f"- candidate_induced_no_solution_primary_rows: `{summary['candidate_induced_no_solution_primary_rows']}`\n"
        f"- candidate_recovers_static_no_solution_primary_rows: `{summary['candidate_recovers_static_no_solution_primary_rows']}`\n"
        f"- unavoidable_context_failure_primary_rows: `{summary['unavoidable_context_failure_primary_rows']}`\n"
        f"- budget_sensitive_candidate_failure_rows: `{summary['budget_sensitive_candidate_failure_rows']}`\n"
        f"- gates: `{gates}`\n\n"
        "Rows include both `budget` scopes and `primary_pair` scopes. Policy risk should prioritize candidate-induced failures and finite-pair solution-quality harm, not unavoidable context failure or candidate failure that matches static failure.\n",
    )
    print(json.dumps({"decision": decision, "primary_pair_rows": len(primary_rows), "static_solution_quality_harmful_count": static_solution_quality_harmful_count}))
    return 0 if decision != "avoidable_failure_semantics_failed_stop" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

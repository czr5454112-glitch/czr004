"""Create G5.21 v10 split context/family/candidate targets."""

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
    G520_FEATURE_MATRIX_CSV,
    G521_CANDIDATE_TARGETS_CSV,
    G521_CLOSED_CLAIMS,
    G521_CONTEXT_TARGETS_CSV,
    G521_FAMILY_TARGETS_CSV,
    G521_TARGETS_REPORT,
    G521_TARGETS_SUMMARY,
    PRIMARY_BUDGETS,
    STATIC_FLOW_SHIELD_CANDIDATE,
    boolish,
    candidate_param_dict,
    candidate_role,
    csv_number,
    family_for_candidate,
    finite_delta,
    finite_number,
    g518_retained_candidate_ids,
    old14_candidate_ids,
    read_rows,
    repo_root,
    row_finite_solution,
    rows_by_context,
    score,
    selected_g521_candidate_ids,
    source_results_for_targets,
    write_json_file,
    write_rows,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-csv", type=Path, default=Path(G521_CONTEXT_TARGETS_CSV))
    parser.add_argument("--family-csv", type=Path, default=Path(G521_FAMILY_TARGETS_CSV))
    parser.add_argument("--candidate-csv", type=Path, default=Path(G521_CANDIDATE_TARGETS_CSV))
    parser.add_argument("--report", type=Path, default=Path(G521_TARGETS_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G521_TARGETS_SUMMARY))
    return parser.parse_args(argv)


def context_feature_source() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in read_rows(G520_FEATURE_MATRIX_CSV):
        context = str(row.get("normalized_context_key", ""))
        if context not in out:
            out[context] = {
                name: value
                for name, value in row.items()
                if name.startswith("feature_map_") or name.startswith("feature_rich_") or name in {"rich_context_feature_present", "map_agent_group", "map_family"}
            }
    return out


def primary_candidate_row(rows: list[dict[str, Any]], static_rows: list[dict[str, Any]], old14_rows: list[dict[str, Any]], *, old_ids: set[str], g518_ids: set[str], g521_ids: set[str]) -> dict[str, Any]:
    candidate = str(rows[0].get("candidate_id", "")) if rows else ""
    static_by_budget = {int(finite_number(row.get("short_budget_ms"), -1)): row for row in static_rows}
    old14_by_budget = {int(finite_number(row.get("short_budget_ms"), -1)): row for row in old14_rows}
    finite_scores = [score(row) for row in rows if row_finite_solution(row)]
    delta_static = []
    delta_old14 = []
    induced = False
    recovers = False
    budget_finite = []
    for row in rows:
        budget = int(finite_number(row.get("short_budget_ms"), -1))
        static = static_by_budget.get(budget)
        old14 = old14_by_budget.get(budget)
        budget_finite.append(row_finite_solution(row))
        if row_finite_solution(row) and row_finite_solution(static):
            delta_static.append(score(row) - score(static))
        if row_finite_solution(row) and row_finite_solution(old14):
            delta_old14.append(score(row) - score(old14))
        induced = induced or (row_finite_solution(static) and not row_finite_solution(row))
        recovers = recovers or ((not row_finite_solution(static)) and row_finite_solution(row))
    mean_delta_static = sum(delta_static) / len(delta_static) if delta_static else math.inf
    mean_delta_old14 = sum(delta_old14) / len(delta_old14) if delta_old14 else math.inf
    role = candidate_role(candidate, old_ids, g518_ids, g521_ids)
    is_new = role in {"g518_retained", "g521_second_wave"}
    beats_static = math.isfinite(mean_delta_static) and mean_delta_static <= -DEFAULT_MARGIN
    beats_old14 = math.isfinite(mean_delta_old14) and mean_delta_old14 <= -DEFAULT_MARGIN
    harmful_static = math.isfinite(mean_delta_static) and mean_delta_static >= DEFAULT_MARGIN
    return {
        "normalized_context_key": rows[0].get("normalized_context_key", "") if rows else "",
        "map": rows[0].get("map", "") if rows else "",
        "agents": rows[0].get("agents", "") if rows else "",
        "seed": rows[0].get("seed", "") if rows else "",
        "iteration": rows[0].get("iteration", "") if rows else "",
        "traffic_before_hash_full": rows[0].get("traffic_before_hash_full", "") if rows else "",
        "candidate_id": candidate,
        "candidate_role": role,
        "candidate_family": family_for_candidate(candidate),
        "candidate_source": role,
        "candidate_score_primary": csv_number(sum(finite_scores) / len(finite_scores) if finite_scores else math.inf),
        "candidate_finite_primary_pair": all(budget_finite) if budget_finite else False,
        "candidate_budget_sensitive": len(set(budget_finite)) > 1,
        "candidate_beats_static_finite": beats_static,
        "candidate_beats_old14_finite": beats_old14,
        "candidate_is_new_oracle_winner": False,
        "candidate_induced_no_solution": induced,
        "candidate_recovers_static_no_solution": recovers,
        "candidate_safe_policy_positive": is_new and (beats_old14 or recovers) and not induced and not harmful_static,
        "new_beats_static_finite": is_new and beats_static,
        "new_beats_best_old14_finite": is_new and beats_old14,
        "new_is_new22_oracle_winner": False,
        "new_recovers_static_no_solution": is_new and recovers,
        "new_candidate_induced_failure": is_new and induced,
        "new_helpful_but_not_policy_relevant": is_new and beats_static and not beats_old14,
        "finite_pairwise_delta_vs_static_primary": csv_number(mean_delta_static),
        "finite_pairwise_delta_vs_best_old14_primary": csv_number(mean_delta_old14),
        "solution_quality_harm_on_finite_pairs": harmful_static,
        "budget_sensitive_candidate_failure": len(set(budget_finite)) > 1 and any(not value for value in budget_finite),
        **candidate_param_dict(candidate),
        **G521_CLOSED_CLAIMS,
    }


def best_old14_rows(group: list[dict[str, Any]], old_ids: set[str]) -> list[dict[str, Any]]:
    rows = []
    for budget in PRIMARY_BUDGETS:
        finite = [
            row
            for row in group
            if str(row.get("candidate_id", "")) in old_ids
            and int(finite_number(row.get("short_budget_ms"), -1)) == budget
            and row_finite_solution(row)
        ]
        if finite:
            rows.append(min(finite, key=lambda row: (score(row), str(row.get("candidate_id", "")))))
    return rows


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    source_label, result_rows, source_summary = source_results_for_targets()
    if not result_rows:
        summary = {
            "schema_version": "phase5p5_repair5g521_targets_v10_summary_v1",
            "decision": "targets_v10_failed_no_probe_results",
            "source_label": source_label,
            **G521_CLOSED_CLAIMS,
        }
        write_json_file(args.summary_json, summary)
        print(json.dumps({"decision": summary["decision"]}))
        return 2
    old_ids = set(old14_candidate_ids(root))
    g518_ids = set(g518_retained_candidate_ids(limit=8))
    g521_ids = set(selected_g521_candidate_ids())
    context_features = context_feature_source()
    context_rows = []
    family_rows = []
    candidate_rows = []
    for context, group in sorted(rows_by_context(result_rows).items()):
        static_rows = [row for row in group if str(row.get("candidate_id", "")) == STATIC_FLOW_SHIELD_CANDIDATE]
        old14_rows = best_old14_rows(group, old_ids)
        by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in group:
            by_candidate[str(row.get("candidate_id", ""))].append(row)
        context_candidate_rows = [
            primary_candidate_row(rows, static_rows, old14_rows, old_ids=old_ids, g518_ids=g518_ids, g521_ids=g521_ids)
            for rows in by_candidate.values()
        ]
        finite_candidates = [row for row in context_candidate_rows if boolish(row.get("candidate_finite_primary_pair"))]
        new_rows = [row for row in context_candidate_rows if row.get("candidate_role") in {"g518_retained", "g521_second_wave"}]
        oracle = min(finite_candidates, key=lambda row: (finite_number(row.get("candidate_score_primary"), math.inf), str(row.get("candidate_id", "")))) if finite_candidates else {}
        for row in context_candidate_rows:
            is_oracle = row.get("candidate_id") == oracle.get("candidate_id", "")
            row["candidate_is_new_oracle_winner"] = is_oracle and row.get("candidate_role") in {"g518_retained", "g521_second_wave"}
            row["new_is_new22_oracle_winner"] = row["candidate_is_new_oracle_winner"]
            candidate_rows.append(row)
        context_has_old14_opportunity = any(boolish(row.get("candidate_beats_old14_finite")) for row in new_rows)
        context_has_safe_new = any(boolish(row.get("candidate_safe_policy_positive")) for row in new_rows)
        context_has_recovery = any(boolish(row.get("candidate_recovers_static_no_solution")) for row in new_rows)
        context_all_fail = not bool(finite_candidates)
        context_budget_sensitive = any(boolish(row.get("candidate_budget_sensitive")) for row in context_candidate_rows)
        first = group[0]
        context_rows.append(
            {
                "normalized_context_key": context,
                "map": first.get("map", ""),
                "agents": first.get("agents", ""),
                "seed": first.get("seed", ""),
                "iteration": first.get("iteration", ""),
                "traffic_before_hash_full": first.get("traffic_before_hash_full", ""),
                "source_label": source_label,
                "context_has_new_beats_old14_opportunity": context_has_old14_opportunity,
                "context_has_safe_new_candidate": context_has_safe_new,
                "context_has_static_failure_recovery_candidate": context_has_recovery,
                "context_all_candidates_fail_or_nonfinite": context_all_fail,
                "context_budget_sensitive": context_budget_sensitive,
                "context_oracle_candidate": oracle.get("candidate_id", ""),
                "context_oracle_candidate_role": oracle.get("candidate_role", ""),
                **context_features.get(context, {}),
                **G521_CLOSED_CLAIMS,
            }
        )
        family_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in context_candidate_rows:
            family_groups[str(row.get("candidate_family", ""))].append(row)
        for family, rows in sorted(family_groups.items()):
            family_best_delta = min([finite_number(row.get("finite_pairwise_delta_vs_best_old14_primary"), math.inf) for row in rows], default=math.inf)
            family_rows.append(
                {
                    "normalized_context_key": context,
                    "map": first.get("map", ""),
                    "agents": first.get("agents", ""),
                    "seed": first.get("seed", ""),
                    "candidate_family": family,
                    "family_candidate_count": len(rows),
                    "family_contains_new_candidate_beating_old14": any(boolish(row.get("candidate_beats_old14_finite")) and row.get("candidate_role") in {"g518_retained", "g521_second_wave"} for row in rows),
                    "family_contains_candidate_induced_failure": any(boolish(row.get("candidate_induced_no_solution")) for row in rows),
                    "family_contains_static_recovery": any(boolish(row.get("candidate_recovers_static_no_solution")) for row in rows),
                    "family_best_finite_delta_vs_old14": csv_number(family_best_delta),
                    **context_features.get(context, {}),
                    **G521_CLOSED_CLAIMS,
                }
            )
    gates = {
        "context_rows_gt_0": len(context_rows) > 0,
        "family_rows_gt_0": len(family_rows) > 0,
        "candidate_rows_gt_0": len(candidate_rows) > 0,
        "context_table_one_row_per_context": len(context_rows) == len({row["normalized_context_key"] for row in context_rows}),
        "candidate_table_has_static": any(row.get("candidate_id") == STATIC_FLOW_SHIELD_CANDIDATE for row in candidate_rows),
    }
    decision = "targets_v10_passed_continue_split_features" if all(gates.values()) else "targets_v10_failed"
    summary = {
        "schema_version": "phase5p5_repair5g521_targets_v10_summary_v1",
        "decision": decision,
        "source_label": source_label,
        "full_primary_compatible": source_label == "full_primary_confirmation",
        "context_rows": len(context_rows),
        "family_rows": len(family_rows),
        "candidate_rows": len(candidate_rows),
        "context_has_new_beats_old14_opportunity": sum(1 for row in context_rows if boolish(row.get("context_has_new_beats_old14_opportunity"))),
        "candidate_safe_policy_positive_rows": sum(1 for row in candidate_rows if boolish(row.get("candidate_safe_policy_positive"))),
        "gates": gates,
        **G521_CLOSED_CLAIMS,
    }
    write_rows(args.context_csv, context_rows)
    write_rows(args.family_csv, family_rows)
    write_rows(args.candidate_csv, candidate_rows)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.21 Targets V10\n\n"
        f"- decision: `{decision}`\n"
        f"- source_label: `{source_label}`\n"
        f"- full_primary_compatible: `{summary['full_primary_compatible']}`\n"
        f"- context_rows: `{len(context_rows)}`\n"
        f"- family_rows: `{len(family_rows)}`\n"
        f"- candidate_rows: `{len(candidate_rows)}`\n"
        f"- candidate_safe_policy_positive_rows: `{summary['candidate_safe_policy_positive_rows']}`\n"
        f"- gates: `{gates}`\n",
    )
    print(json.dumps({"decision": decision, "source_label": source_label, "candidate_rows": len(candidate_rows)}))
    return 0 if decision != "targets_v10_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

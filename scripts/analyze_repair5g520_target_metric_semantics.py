"""Audit G5.19 target/harm semantics and separate no-solution risk from quality harm."""

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

from repair5g520_common import (  # noqa: E402
    DEFAULT_MARGIN,
    G519_CONTEXT_DECISIONS_CSV,
    G519_EVAL_CSV,
    G519_TARGETS_CSV,
    G519_TARGET_BUDGET_AUDIT_CSV,
    G520_CLOSED_CLAIMS,
    G520_TARGET_SEMANTICS_AUDIT_CSV,
    G520_TARGET_SEMANTICS_AUDIT_REPORT,
    G520_TARGET_SEMANTICS_AUDIT_SUMMARY,
    STATIC_FLOW_SHIELD_CANDIDATE,
    boolish,
    context_candidate_budget_key,
    corrected_delta,
    csv_number,
    finite_number,
    mean,
    policy_metric_row_corrected,
    read_rows,
    row_key,
    rows_by_context,
    select_candidate,
    total_harmful,
    write_json_file,
    write_rows,
    write_text_file,
)


PRIMARY_BUDGETS = [1000, 2000]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets-csv", type=Path, default=Path(G519_TARGETS_CSV))
    parser.add_argument("--budget-audit-csv", type=Path, default=Path(G519_TARGET_BUDGET_AUDIT_CSV))
    parser.add_argument("--g519-eval-csv", type=Path, default=Path(G519_EVAL_CSV))
    parser.add_argument("--g519-context-decisions-csv", type=Path, default=Path(G519_CONTEXT_DECISIONS_CSV))
    parser.add_argument("--output-csv", type=Path, default=Path(G520_TARGET_SEMANTICS_AUDIT_CSV))
    parser.add_argument("--report", type=Path, default=Path(G520_TARGET_SEMANTICS_AUDIT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G520_TARGET_SEMANTICS_AUDIT_SUMMARY))
    return parser.parse_args(argv)


def finite_or_blank(value: Any) -> float | str:
    number = finite_number(value, math.inf)
    return csv_number(number)


def budget_flags(rows: list[dict[str, Any]]) -> dict[str, Any]:
    budgets = {int(finite_number(row.get("short_budget_ms"), -1)) for row in rows}
    finite_scores = [finite_number(row.get("score"), math.inf) for row in rows]
    return {
        "budget_rows": len(rows),
        "missing_budget_count": len(set(PRIMARY_BUDGETS) - budgets),
        "nonfinite_score_count": sum(1 for value in finite_scores if not math.isfinite(value)),
        "probe_no_solution_count": sum(
            1
            for row in rows
            if not boolish(row.get("probe_solution_found")) or not boolish(row.get("probe_feasible"))
        ),
        "all_scores_finite": len(rows) == len(PRIMARY_BUDGETS) and all(math.isfinite(value) for value in finite_scores),
        "all_probe_solution_found": all(
            boolish(row.get("probe_solution_found")) and boolish(row.get("probe_feasible"))
            for row in rows
        )
        and len(rows) == len(PRIMARY_BUDGETS),
    }


def paired_solution_delta(candidate_budget_rows: list[dict[str, Any]], static_budget_rows: list[dict[str, Any]]) -> float:
    static_by_budget = {int(finite_number(row.get("short_budget_ms"), -1)): row for row in static_budget_rows}
    deltas = []
    for row in candidate_budget_rows:
        budget = int(finite_number(row.get("short_budget_ms"), -1))
        static = static_by_budget.get(budget)
        if not static:
            continue
        score = finite_number(row.get("score"), math.inf)
        static_score = finite_number(static.get("score"), math.inf)
        if math.isfinite(score) and math.isfinite(static_score):
            deltas.append(score - static_score)
    return mean(deltas)


def corrected_label_row(
    target: dict[str, Any],
    candidate_budget_rows: list[dict[str, Any]],
    static_budget_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_flags = budget_flags(candidate_budget_rows)
    static_flags = budget_flags(static_budget_rows)
    delta = paired_solution_delta(candidate_budget_rows, static_budget_rows)
    candidate_no_solution = candidate_flags["probe_no_solution_count"] > 0 or candidate_flags["missing_budget_count"] > 0
    candidate_budget_nonfinite = (
        candidate_flags["nonfinite_score_count"] > 0
        or candidate_flags["missing_budget_count"] > 0
        or not candidate_flags["all_scores_finite"]
    )
    static_nonfinite = static_flags["nonfinite_score_count"] > 0 or static_flags["missing_budget_count"] > 0
    solution_quality_harm = math.isfinite(delta) and delta >= DEFAULT_MARGIN and not candidate_no_solution
    safe_static_neutral = (
        str(target.get("candidate_id", "")) == STATIC_FLOW_SHIELD_CANDIDATE
        and math.isfinite(delta)
        and abs(delta) < DEFAULT_MARGIN
        and not candidate_no_solution
    )
    harmful_total = bool(solution_quality_harm or candidate_no_solution or candidate_budget_nonfinite)
    old_harmful = boolish(target.get("harmful_vs_static"))
    return {
        "row_type": "target_semantics_audit",
        "normalized_context_key": target.get("normalized_context_key", ""),
        "map": target.get("map", ""),
        "agents": target.get("agents", ""),
        "seed": target.get("seed", ""),
        "candidate_id": target.get("candidate_id", ""),
        "candidate_source": target.get("candidate_source", ""),
        "is_new_candidate": target.get("is_new_candidate", ""),
        "old_mean_delta_vs_static_primary": target.get("mean_delta_vs_static_primary", ""),
        "old_harmful_vs_static": old_harmful,
        "old_helpful_vs_static": target.get("helpful_vs_static", ""),
        "candidate_budget_rows": candidate_flags["budget_rows"],
        "candidate_missing_budget_count": candidate_flags["missing_budget_count"],
        "candidate_nonfinite_score_count": candidate_flags["nonfinite_score_count"],
        "candidate_probe_no_solution_count": candidate_flags["probe_no_solution_count"],
        "static_nonfinite_score_count": static_flags["nonfinite_score_count"],
        "static_probe_no_solution_count": static_flags["probe_no_solution_count"],
        "static_budget_missing_or_nonfinite": static_nonfinite,
        "solution_quality_delta_vs_static": finite_or_blank(delta),
        "solution_quality_harmful_vs_static": solution_quality_harm,
        "no_solution_or_infeasible": candidate_no_solution,
        "budget_missing_or_nonfinite": candidate_budget_nonfinite,
        "budget_nonfinite": candidate_budget_nonfinite,
        "safe_static_neutral": safe_static_neutral,
        "harmful_total": harmful_total,
        "old_static_harm_was_no_solution_semantics": (
            str(target.get("candidate_id", "")) == STATIC_FLOW_SHIELD_CANDIDATE
            and old_harmful
            and (candidate_no_solution or candidate_budget_nonfinite)
            and not solution_quality_harm
        ),
        **G520_CLOSED_CLAIMS,
    }


def metric_shift_for_g519_policy(
    policy: str,
    context_decisions: list[dict[str, Any]],
    audit_by_key: dict[str, dict[str, Any]],
    targets_by_key: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    selected = []
    for row in context_decisions:
        if row.get("eval_scope") != "seed_oof" or row.get("policy") != policy:
            continue
        key = f"{row.get('normalized_context_key', '')}|{row.get('selected_candidate_id', '')}"
        target = dict(targets_by_key.get(key, {}))
        audit = audit_by_key.get(key, {})
        if not target:
            continue
        target.update(
            {
                "solution_quality_delta_vs_static": audit.get("solution_quality_delta_vs_static", ""),
                "solution_quality_harmful_vs_static": audit.get("solution_quality_harmful_vs_static", ""),
                "no_solution_or_infeasible": audit.get("no_solution_or_infeasible", ""),
                "budget_nonfinite": audit.get("budget_nonfinite", ""),
                "harmful_total": audit.get("harmful_total", ""),
                "helpful_vs_static_corrected": (
                    math.isfinite(corrected_delta({**target, **audit}))
                    and corrected_delta({**target, **audit}) <= -DEFAULT_MARGIN
                    and not total_harmful({**target, **audit})
                ),
            }
        )
        selected.append(target)
    old_eval = {}
    for row in read_rows(G519_EVAL_CSV):
        if row.get("row_type") == "policy_summary" and row.get("eval_scope") == "seed_oof" and row.get("policy") == policy:
            old_eval = row
            break
    corrected = policy_metric_row_corrected(policy, selected, eval_scope="seed_oof_corrected_labels")
    return {
        "policy": policy,
        "old_harmful_vs_static_rate": old_eval.get("harmful_vs_static_rate", ""),
        "old_false_positive_count": old_eval.get("false_positive_count", ""),
        "corrected_solution_quality_harmful_rate": corrected.get("solution_quality_harmful_rate", ""),
        "corrected_no_solution_rate": corrected.get("no_solution_rate", ""),
        "corrected_total_harmful_rate": corrected.get("total_harmful_rate", ""),
        "corrected_false_positive_count": corrected.get("false_positive_count", ""),
        "corrected_mean_solution_quality_delta_vs_static": corrected.get("mean_solution_quality_delta_vs_static", ""),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    targets = read_rows(args.targets_csv)
    budget_rows = read_rows(args.budget_audit_csv)
    context_decisions = read_rows(args.g519_context_decisions_csv)
    by_key_budget: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in budget_rows:
        context, candidate, _budget = context_candidate_budget_key(row)
        by_key_budget[(context, candidate)].append(row)
    audit_rows = []
    for target in targets:
        context = str(target.get("normalized_context_key", ""))
        candidate = str(target.get("candidate_id", ""))
        candidate_budget_rows = by_key_budget[(context, candidate)]
        static_budget_rows = by_key_budget[(context, STATIC_FLOW_SHIELD_CANDIDATE)]
        audit_rows.append(corrected_label_row(target, candidate_budget_rows, static_budget_rows))

    audit_by_key = {row_key(row): row for row in audit_rows}
    targets_by_key = {row_key(row): row for row in targets}
    static_rows = [row for row in audit_rows if row.get("candidate_id") == STATIC_FLOW_SHIELD_CANDIDATE]
    static_old_harm = [row for row in static_rows if boolish(row.get("old_harmful_vs_static"))]
    static_solution_harm = [row for row in static_rows if boolish(row.get("solution_quality_harmful_vs_static"))]
    static_no_solution = [row for row in static_rows if boolish(row.get("no_solution_or_infeasible")) or boolish(row.get("budget_nonfinite"))]
    contexts_with_no_solution = {
        row.get("normalized_context_key", "")
        for row in audit_rows
        if boolish(row.get("no_solution_or_infeasible")) or boolish(row.get("budget_nonfinite"))
    }
    old_harm_due_to_nonfinite = [
        row
        for row in audit_rows
        if boolish(row.get("old_harmful_vs_static"))
        and not boolish(row.get("solution_quality_harmful_vs_static"))
        and (boolish(row.get("no_solution_or_infeasible")) or boolish(row.get("budget_nonfinite")))
    ]
    metric_shift = [
        metric_shift_for_g519_policy(policy, context_decisions, audit_by_key, targets_by_key)
        for policy in ["static_flow_shield", "no_new_candidate_ablation", "old14_only_ranker"]
    ]
    gates = {
        "rows_eq_1320": len(audit_rows) == 1320,
        "static_rows_eq_60": len(static_rows) == 60,
        "static_solution_quality_harm_zero": len(static_solution_harm) == 0,
        "old_static_harm_explained_by_no_solution": len(static_old_harm) == len(static_no_solution),
        "corrected_labels_present": all("solution_quality_harmful_vs_static" in row for row in audit_rows),
    }
    if not gates["rows_eq_1320"] or not gates["static_rows_eq_60"]:
        decision = "target_semantics_blocker_stop"
    elif len(static_old_harm) > 0 and gates["static_solution_quality_harm_zero"]:
        decision = "static_harm_semantics_bug_fixed_continue_corrected_targets"
    else:
        decision = "target_semantics_clean_continue_policy"
    summary = {
        "schema_version": "phase5p5_repair5g520_target_semantics_audit_summary_v1",
        "decision": decision,
        "target_rows": len(audit_rows),
        "static_flow_shield_rows": len(static_rows),
        "static_flow_shield_old_harmful_vs_static_count": len(static_old_harm),
        "static_flow_shield_solution_quality_harmful_count": len(static_solution_harm),
        "static_flow_shield_no_solution_or_nonfinite_count": len(static_no_solution),
        "contexts_with_no_solution_or_nonfinite": len(contexts_with_no_solution),
        "old_harmful_rows_explained_by_no_solution_or_nonfinite": len(old_harm_due_to_nonfinite),
        "finite_number_inf_conversion_created_static_harm_labels": len(static_old_harm) > 0 and len(static_solution_harm) == 0,
        "metric_shift_if_no_solution_separated": metric_shift,
        "corrected_label_fields": [
            "solution_quality_delta_vs_static",
            "solution_quality_harmful_vs_static",
            "no_solution_or_infeasible",
            "budget_missing_or_nonfinite",
            "safe_static_neutral",
            "harmful_total",
        ],
        "gates": gates,
        **G520_CLOSED_CLAIMS,
    }
    write_rows(args.output_csv, audit_rows)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.20 Target Metric Semantics Audit\n\n"
        f"- decision: `{decision}`\n"
        f"- target_rows: `{len(audit_rows)}`\n"
        f"- static_flow_shield_old_harmful_vs_static_count: `{len(static_old_harm)}`\n"
        f"- static_flow_shield_solution_quality_harmful_count: `{len(static_solution_harm)}`\n"
        f"- static_flow_shield_no_solution_or_nonfinite_count: `{len(static_no_solution)}`\n"
        f"- contexts_with_no_solution_or_nonfinite: `{len(contexts_with_no_solution)}`\n"
        f"- finite_number_inf_conversion_created_static_harm_labels: `{summary['finite_number_inf_conversion_created_static_harm_labels']}`\n\n"
        "The old G5.19 harmful label used `finite_number(..., math.inf)` and then compared the result to the margin. "
        "That made no-solution/nonfinite static rows look like solution-quality harm. G5.20 keeps total risk visible, but it reports "
        "`solution_quality_harmful_vs_static`, `no_solution_or_infeasible`, and `budget_missing_or_nonfinite` separately.\n\n"
        f"Metric shifts: `{metric_shift}`\n",
    )
    print(json.dumps({"decision": decision, "static_old_harm": len(static_old_harm), "static_solution_harm": len(static_solution_harm)}))
    return 0 if decision != "target_semantics_blocker_stop" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

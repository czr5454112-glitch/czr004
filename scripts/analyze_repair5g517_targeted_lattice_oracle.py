"""Analyze G5.17 targeted repair lattice oracle gain."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g510_common import (  # noqa: E402
    as_jsonable,
    best_candidate,
    candidate_scores_by_context_budget,
    context_key,
    finite_number,
    mean,
    score_for_candidate,
    score_from_probe,
)
from repair5g512_common import observed_id_flags, read_json  # noqa: E402
from repair5g517_common import (  # noqa: E402
    ADDITIVE_CANDIDATES,
    DEFAULT_MARGIN,
    FIXED_SLOW_DECAY_CANDIDATE,
    G517_CLOSED_CLAIMS,
    G517_ORACLE_CANDIDATE_TABLE,
    G517_ORACLE_CONTEXT_TABLE,
    G517_ORACLE_REPORT,
    G517_ORACLE_SUMMARY,
    G517_TARGETED_INTEGRITY_SUMMARY,
    G517_TARGETED_RESULTS,
    STATIC_CANDIDATES,
    candidate_ids_from_plan,
    plan_rows,
    read_csv_dicts,
    repair_candidate_ids,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-csv", type=Path, default=Path(G517_TARGETED_RESULTS))
    parser.add_argument("--probe-plan-csv", type=Path, default=Path("outputs/tables/phase5p5_repair5g516_local_targeted_probe_plan.csv"))
    parser.add_argument("--integrity-summary-json", type=Path, default=Path(G517_TARGETED_INTEGRITY_SUMMARY))
    parser.add_argument("--context-table-csv", type=Path, default=Path(G517_ORACLE_CONTEXT_TABLE))
    parser.add_argument("--candidate-table-csv", type=Path, default=Path(G517_ORACLE_CANDIDATE_TABLE))
    parser.add_argument("--summary-json", type=Path, default=Path(G517_ORACLE_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G517_ORACLE_REPORT))
    return parser.parse_args(argv)


def plan_category_lookup(rows: list[dict[str, Any]]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        key = str(row.get("normalized_context_key", ""))
        category = str(row.get("error_category", ""))
        if key and category:
            out[key].add(category)
    return out


def first_present(scores: dict[str, dict[str, Any]], candidates: set[str]) -> tuple[str, float]:
    present = [(candidate, score_for_candidate(scores, candidate)) for candidate in sorted(candidates) if candidate in scores]
    finite = [(candidate, score) for candidate, score in present if math.isfinite(score)]
    if finite:
        return min(finite, key=lambda item: (item[1], item[0]))
    return (present[0][0], present[0][1]) if present else ("", math.inf)


def candidate_distribution(
    rows: list[dict[str, Any]],
    *,
    candidate_ids: set[str],
    repair_ids: set[str],
    oracle_wins: Counter[str],
) -> list[dict[str, Any]]:
    by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        candidate = str(row.get("candidate_id", ""))
        if candidate in candidate_ids:
            by_candidate[candidate].append(row)
    out = []
    for candidate in sorted(candidate_ids):
        group = by_candidate.get(candidate, [])
        deltas = [finite_number(row.get("delta_vs_static_in_same_context"), math.nan) for row in group]
        finite_deltas = [value for value in deltas if math.isfinite(value)]
        helpful = [value for value in finite_deltas if value < -DEFAULT_MARGIN]
        harmful = [value for value in finite_deltas if value > DEFAULT_MARGIN]
        out.append(
            {
                "candidate_id": candidate,
                "is_repair5g516_candidate": candidate in repair_ids,
                "rows": len(group),
                "finite_rows": sum(1 for row in group if math.isfinite(score_from_probe(row))),
                "oracle_win_count": oracle_wins.get(candidate, 0),
                "mean_score": as_jsonable(mean(score_from_probe(row) for row in group)),
                "mean_delta_vs_static": as_jsonable(mean(finite_deltas)),
                "helpful_vs_static_count": len(helpful),
                "harmful_vs_static_count": len(harmful),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_dicts(resolve(args.results_csv, root))
    plan = plan_rows(resolve(args.probe_plan_csv, root))
    integrity = read_json(resolve(args.integrity_summary_json, root)) if resolve(args.integrity_summary_json, root).exists() else {}
    all_candidates = set(candidate_ids_from_plan(plan))
    repair_ids = set(repair_candidate_ids())
    old_ids = all_candidates - repair_ids
    categories = plan_category_lookup(plan)
    grouped = candidate_scores_by_context_budget(rows, allowed_candidates=all_candidates)

    context_rows = []
    oracle_wins: Counter[str] = Counter()
    gaps = []
    repair_win_contexts: set[str] = set()
    harmful_improved_contexts: set[str] = set()
    static_boundary_rows = []
    additive_weak_rows = []
    complete_pairs = 0
    recognized_all = True
    for (key, budget), scores in sorted(grouped.items()):
        old_scores = {candidate: row for candidate, row in scores.items() if candidate in old_ids}
        new_scores = {candidate: row for candidate, row in scores.items() if candidate in all_candidates}
        old_oracle, old_score = best_candidate(old_scores)
        new_oracle, new_score = best_candidate(new_scores)
        static_candidate, static_score = first_present(new_scores, STATIC_CANDIDATES)
        additive_candidate, additive_score = first_present(new_scores, ADDITIVE_CANDIDATES)
        fixed_score = score_for_candidate(new_scores, FIXED_SLOW_DECAY_CANDIDATE)
        gap = new_score - old_score if math.isfinite(new_score) and math.isfinite(old_score) else math.inf
        cats = categories.get(key, set())
        if math.isfinite(gap):
            gaps.append(gap)
        if all_candidates <= set(new_scores):
            complete_pairs += 1
        if new_oracle in repair_ids:
            repair_win_contexts.add(key)
            oracle_wins[new_oracle] += 1
        elif new_oracle:
            oracle_wins[new_oracle] += 1
        if "harmful_false_positive" in cats and math.isfinite(gap) and gap < -DEFAULT_MARGIN:
            harmful_improved_contexts.add(key)
        if "static_near_oracle" in cats:
            static_boundary_rows.append(gap)
        if math.isfinite(additive_score) and math.isfinite(new_score) and additive_score - new_score > DEFAULT_MARGIN:
            additive_weak_rows.append(key)
        for row in new_scores.values():
            recognized_all = recognized_all and str(row.get("candidate_recognized", "")).lower() == "true"
        context_rows.append(
            {
                "normalized_context_key": key,
                "short_budget_ms": int(budget),
                "error_categories": ";".join(sorted(cats)),
                "old14_oracle_candidate": old_oracle,
                "new24_oracle_candidate": new_oracle,
                "new24_oracle_is_repair_candidate": new_oracle in repair_ids,
                "old14_oracle_score": as_jsonable(old_score),
                "new24_oracle_score": as_jsonable(new_score),
                "new_oracle_gap_vs_old_oracle": as_jsonable(gap),
                "static_candidate": static_candidate,
                "static_score": as_jsonable(static_score),
                "additive_candidate": additive_candidate,
                "additive_score": as_jsonable(additive_score),
                "fixed_slow_decay_high_shield_score": as_jsonable(fixed_score),
                "new_oracle_gap_vs_static": as_jsonable(new_score - static_score if math.isfinite(new_score) and math.isfinite(static_score) else math.inf),
                "new_oracle_gap_vs_additive": as_jsonable(new_score - additive_score if math.isfinite(new_score) and math.isfinite(additive_score) else math.inf),
                "candidate_count": len(new_scores),
                "old_candidate_count": len(old_scores),
                "repair_candidate_count": len([candidate for candidate in new_scores if candidate in repair_ids]),
            }
        )

    candidate_rows = candidate_distribution(rows, candidate_ids=all_candidates, repair_ids=repair_ids, oracle_wins=oracle_wins)
    write_csv_rows(resolve(args.context_table_csv, root), context_rows)
    write_csv_rows(resolve(args.candidate_table_csv, root), candidate_rows)

    finite_gaps = [value for value in gaps if math.isfinite(value)]
    mean_gap = mean(finite_gaps)
    static_boundary_no_worse_count = sum(1 for value in static_boundary_rows if math.isfinite(value) and value <= DEFAULT_MARGIN)
    static_boundary_contexts = {
        row["normalized_context_key"]
        for row in context_rows
        if "static_near_oracle" in str(row.get("error_categories", "")).split(";")
    }
    flags = observed_id_flags(rows)
    new_repair_win_count = sum(row["oracle_win_count"] for row in candidate_rows if row["is_repair5g516_candidate"])
    no_gain_reported = new_repair_win_count == 0 or not (math.isfinite(mean_gap) and mean_gap < -DEFAULT_MARGIN)
    gates = {
        "targeted_probe_integrity_passed": integrity.get("decision") == "targeted_probe_integrity_passed_continue_oracle",
        "new_repair_candidate_win_count_gt_0": new_repair_win_count > 0,
        "mean_new_oracle_gap_vs_old_oracle_lt_0": math.isfinite(mean_gap) and mean_gap < 0.0,
        "harmful_false_positive_target_contexts_improved_gt_0": len(harmful_improved_contexts) > 0,
        "static_boundary_contexts_no_worse_reported": bool(static_boundary_contexts) and static_boundary_no_worse_count >= 0,
        "additive_remains_weak_reported": len(additive_weak_rows) >= 0,
        "candidate_recognized_all": recognized_all and bool(rows),
        "complete_context_budget_pairs_eq_40": complete_pairs == 40,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
    }
    pass_gate = (
        gates["targeted_probe_integrity_passed"]
        and gates["new_repair_candidate_win_count_gt_0"]
        and gates["mean_new_oracle_gap_vs_old_oracle_lt_0"]
        and gates["harmful_false_positive_target_contexts_improved_gt_0"]
    )
    decision = (
        "targeted_repair_lattice_oracle_improved_continue_full_primary"
        if pass_gate
        else "targeted_repair_lattice_no_oracle_gain_continue_lattice_design"
    )
    summary = {
        "schema_version": "phase5p5_repair5g517_targeted_lattice_oracle_summary_v1",
        "decision": decision,
        "context_budget_pairs": len(context_rows),
        "complete_context_budget_pairs": complete_pairs,
        "old_candidate_count": len(old_ids),
        "new_candidate_count": len(all_candidates),
        "repair_candidate_count": len(repair_ids),
        "new_repair_candidate_win_count": new_repair_win_count,
        "repair_win_context_count": len(repair_win_contexts),
        "mean_new_oracle_gap_vs_old_oracle": as_jsonable(mean_gap),
        "harmful_false_positive_target_contexts_improved": len(harmful_improved_contexts),
        "harmful_false_positive_improved_context_keys": sorted(harmful_improved_contexts),
        "static_boundary_contexts": len(static_boundary_contexts),
        "static_boundary_context_budget_rows_no_worse": static_boundary_no_worse_count,
        "additive_weak_context_budget_rows": len(additive_weak_rows),
        "explicit_no_candidate_space_gain_reported": no_gain_reported,
        "per_candidate_win_distribution": dict(sorted(oracle_wins.items())),
        "context_oracle_csv": str(resolve(args.context_table_csv, root)),
        "candidate_distribution_csv": str(resolve(args.candidate_table_csv, root)),
        "gates": gates,
        **flags,
        **G517_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.17 Targeted Lattice Oracle\n\n"
        f"- decision: `{decision}`\n"
        f"- context_budget_pairs: `{len(context_rows)}`\n"
        f"- complete_context_budget_pairs: `{complete_pairs}`\n"
        f"- old_candidate_count: `{len(old_ids)}`\n"
        f"- new_candidate_count: `{len(all_candidates)}`\n"
        f"- repair_candidate_count: `{len(repair_ids)}`\n"
        f"- new_repair_candidate_win_count: `{new_repair_win_count}`\n"
        f"- mean_new_oracle_gap_vs_old_oracle: `{summary['mean_new_oracle_gap_vs_old_oracle']}`\n"
        f"- harmful_false_positive_target_contexts_improved: `{len(harmful_improved_contexts)}`\n"
        f"- static_boundary_contexts_no_worse_reported: `{gates['static_boundary_contexts_no_worse_reported']}`\n"
        f"- additive_weak_context_budget_rows: `{len(additive_weak_rows)}`\n"
        f"- gates: `{gates}`\n\n"
        "Negative `mean_new_oracle_gap_vs_old_oracle` means the 24-candidate oracle improved over the old 14-candidate oracle. If this gate does not pass, G5.17 stops at lattice design rather than training a learned policy on unsupported candidate-space evidence.\n",
    )
    print(json.dumps({"decision": decision, "new_repair_candidate_win_count": new_repair_win_count, "mean_gap": summary["mean_new_oracle_gap_vs_old_oracle"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

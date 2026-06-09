"""Analyze G5.18 probe batches against the old-14 candidate-space oracle."""

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
    mean,
    score_for_candidate,
    score_from_probe,
)
from repair5g518_common import (  # noqa: E402
    DEFAULT_MARGIN,
    G518_BATCHES_REPORT,
    G518_BATCHES_SUMMARY,
    G518_CLOSED_CLAIMS,
    batch_candidate_distribution_csv,
    batch_integrity_summary,
    batch_oracle_context_csv,
    batch_oracle_report,
    batch_oracle_summary,
    batch_plan_csv,
    batch_result_csv,
    candidate_params,
    family_for_candidate,
    finite_number,
    map_family,
    maybe_read_json,
    observed_id_flags,
    old14_candidate_ids,
    param_distance,
    read_csv_dicts,
    repo_root,
    resolve,
    score_from_probe,
    selected_candidate_family_lookup,
    selected_new_candidates,
    selected_rows,
    write_csv,
    write_json_file,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batches", default="A,B,C")
    parser.add_argument("--error-bank-csv", type=Path, default=Path("outputs/tables/phase5p5_repair5g516_error_bank.csv"))
    parser.add_argument("--summary-json", type=Path, default=Path(G518_BATCHES_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G518_BATCHES_REPORT))
    return parser.parse_args(argv)


def categories_by_context(plan_rows: list[dict[str, Any]], error_bank_rows: list[dict[str, Any]]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for row in plan_rows + error_bank_rows:
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


def nearest_old(candidate: str, old_ids: set[str]) -> tuple[str, float]:
    params = candidate_params(candidate)
    best = ("", math.inf)
    for old in old_ids:
        dist = param_distance(params, candidate_params(old))
        if dist < best[1]:
            best = (old, dist)
    return best


def candidate_distribution(
    rows: list[dict[str, Any]],
    grouped: dict[tuple[str, float], dict[str, dict[str, Any]]],
    *,
    old_ids: set[str],
    new_ids: set[str],
    family_lookup: dict[str, str],
    oracle_wins: Counter[str],
) -> list[dict[str, Any]]:
    by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    better_nearest: Counter[str] = Counter()
    worse_nearest: Counter[str] = Counter()
    tied_nearest: Counter[str] = Counter()
    for row in rows:
        by_candidate[str(row.get("candidate_id", ""))].append(row)
    for (_key, _budget), scores in grouped.items():
        for candidate in new_ids:
            nearest, _dist = nearest_old(candidate, old_ids)
            if candidate not in scores or nearest not in scores:
                continue
            candidate_score = score_for_candidate(scores, candidate)
            old_score = score_for_candidate(scores, nearest)
            if not math.isfinite(candidate_score) or not math.isfinite(old_score):
                continue
            if candidate_score < old_score - DEFAULT_MARGIN:
                better_nearest[candidate] += 1
            elif candidate_score > old_score + DEFAULT_MARGIN:
                worse_nearest[candidate] += 1
            else:
                tied_nearest[candidate] += 1
    out = []
    for candidate in sorted(by_candidate):
        group = by_candidate[candidate]
        params = candidate_params(candidate)
        deltas = [finite_number(row.get("delta_vs_static_in_same_context"), math.nan) for row in group]
        finite_deltas = [value for value in deltas if math.isfinite(value)]
        scores = [score_from_probe(row) for row in group]
        finite_scores = [value for value in scores if math.isfinite(value)]
        nearest, distance = nearest_old(candidate, old_ids) if candidate in new_ids else ("", math.inf)
        row = {
            "candidate_id": candidate,
            "candidate_family": family_lookup.get(candidate) or family_for_candidate(candidate, params),
            "candidate_role": "g518_new_candidate" if candidate in new_ids else "old14_control",
            "rows": len(group),
            "finite_rows": len(finite_scores),
            "oracle_win_count": oracle_wins.get(candidate, 0),
            "mean_score": as_jsonable(mean(finite_scores)),
            "mean_delta_vs_static": as_jsonable(mean(finite_deltas)),
            "helpful_vs_static_count": sum(1 for value in finite_deltas if value < -DEFAULT_MARGIN),
            "harmful_vs_static_count": sum(1 for value in finite_deltas if value > DEFAULT_MARGIN),
            "nearest_old_candidate": nearest,
            "nearest_old_param_distance": as_jsonable(distance),
            "better_than_nearest_old_rows": better_nearest.get(candidate, 0),
            "tied_nearest_old_rows": tied_nearest.get(candidate, 0),
            "worse_than_nearest_old_rows": worse_nearest.get(candidate, 0),
            "dominated_by_nearest_old": candidate in new_ids and better_nearest.get(candidate, 0) == 0 and worse_nearest.get(candidate, 0) > 0,
        }
        if params is not None:
            row.update(params.as_feature_dict())
        out.append(row)
    return out


def analyze_batch(batch: str, error_bank_rows: list[dict[str, Any]], selected: list[dict[str, Any]]) -> dict[str, Any]:
    root = repo_root()
    batch = batch.upper()
    rows = read_csv_dicts(resolve(batch_result_csv(batch), root))
    plan = read_csv_dicts(resolve(batch_plan_csv(batch), root))
    integrity = maybe_read_json(batch_integrity_summary(batch))
    family_lookup = selected_candidate_family_lookup(selected)
    old_ids = set(old14_candidate_ids(root))
    new_ids = set(selected_new_candidates(batch, selected))
    candidate_ids = old_ids | new_ids
    grouped = candidate_scores_by_context_budget(rows, allowed_candidates=candidate_ids)
    categories = categories_by_context(plan, error_bank_rows)
    context_rows = []
    oracle_wins: Counter[str] = Counter()
    family_wins: Counter[str] = Counter()
    gaps = []
    new_win_contexts = set()
    harmful_improved = set()
    missed_helpful_improved = set()
    static_boundary_contexts = set()
    static_boundary_no_worse = 0
    additive_weak = 0
    duplicate_rows = 0
    recognized_all = True
    for (key, budget), scores in sorted(grouped.items()):
        old_scores = {candidate: row for candidate, row in scores.items() if candidate in old_ids}
        all_scores = {candidate: row for candidate, row in scores.items() if candidate in candidate_ids}
        old_oracle, old_score = best_candidate(old_scores)
        new_oracle, new_score = best_candidate(all_scores)
        static_candidate, static_score = first_present(all_scores, {"repair5g59_static_flow_shield", "repair5g59_static_abstain_candidate"})
        additive_candidate, additive_score = first_present(all_scores, {"repair5g59_additive_fallback"})
        gap = new_score - old_score if math.isfinite(new_score) and math.isfinite(old_score) else math.inf
        cats = categories.get(key, set())
        if math.isfinite(gap):
            gaps.append(gap)
        if new_oracle:
            oracle_wins[new_oracle] += 1
            family_wins[family_lookup.get(new_oracle) or family_for_candidate(new_oracle, candidate_params(new_oracle))] += 1
        if new_oracle in new_ids:
            new_win_contexts.add(f"{key}|{int(budget)}")
        if "harmful_false_positive" in cats and math.isfinite(gap) and gap < -DEFAULT_MARGIN:
            harmful_improved.add(key)
        if any("missed_helpful" in category for category in cats) and math.isfinite(gap) and gap < -DEFAULT_MARGIN:
            missed_helpful_improved.add(key)
        if "static_near_oracle" in cats:
            static_boundary_contexts.add(key)
            if math.isfinite(gap) and gap <= DEFAULT_MARGIN:
                static_boundary_no_worse += 1
        if math.isfinite(additive_score) and math.isfinite(new_score) and additive_score - new_score > DEFAULT_MARGIN:
            additive_weak += 1
        for row in all_scores.values():
            recognized_all = recognized_all and str(row.get("candidate_recognized", "")).lower() == "true"
        context_rows.append(
            {
                "batch": batch,
                "normalized_context_key": key,
                "short_budget_ms": int(budget),
                "map_family": map_family(key.split("|", 1)[0]),
                "error_categories": ";".join(sorted(cats)),
                "old14_oracle_candidate": old_oracle,
                "g518_oracle_candidate": new_oracle,
                "g518_oracle_is_new_candidate": new_oracle in new_ids,
                "old14_oracle_score": as_jsonable(old_score),
                "g518_oracle_score": as_jsonable(new_score),
                "new_oracle_gap_vs_old_oracle": as_jsonable(gap),
                "static_candidate": static_candidate,
                "static_score": as_jsonable(static_score),
                "additive_candidate": additive_candidate,
                "additive_score": as_jsonable(additive_score),
                "g518_oracle_gap_vs_static": as_jsonable(new_score - static_score if math.isfinite(new_score) and math.isfinite(static_score) else math.inf),
                "g518_oracle_gap_vs_additive": as_jsonable(new_score - additive_score if math.isfinite(new_score) and math.isfinite(additive_score) else math.inf),
                "candidate_count": len(all_scores),
                "old14_candidate_count": len(old_scores),
                "new_candidate_count": len([candidate for candidate in all_scores if candidate in new_ids]),
            }
        )
    candidate_rows = candidate_distribution(rows, grouped, old_ids=old_ids, new_ids=new_ids, family_lookup=family_lookup, oracle_wins=oracle_wins)
    write_csv(batch_oracle_context_csv(batch), context_rows)
    write_csv(batch_candidate_distribution_csv(batch), candidate_rows)
    flags = observed_id_flags(rows + plan)
    mean_gap = mean(gaps)
    gate_reasons = {
        "new_candidate_win_count_ge_2": len(new_win_contexts) >= 2,
        "mean_new_oracle_gap_vs_old_oracle_le_neg_0p002": math.isfinite(mean_gap) and mean_gap <= -0.002,
        "harmful_false_positive_target_contexts_improved_ge_1": len(harmful_improved) >= 1,
        "missed_helpful_oracle_gap_reduced_ge_3": len(missed_helpful_improved) >= 3,
    }
    integrity_passed = integrity.get("decision") == "g518_probe_batch_integrity_passed_continue_oracle"
    pass_gate = integrity_passed and any(gate_reasons.values())
    decision = "g518_batch_candidate_space_improved_continue_full_primary" if pass_gate else "g518_batch_no_candidate_space_gain"
    summary = {
        "schema_version": "phase5p5_repair5g518_batch_oracle_summary_v1",
        "batch": batch,
        "decision": decision,
        "integrity_decision": integrity.get("decision", ""),
        "context_budget_pairs": len(context_rows),
        "old_candidate_count": len(old_ids),
        "new_candidate_count": len(new_ids),
        "new_candidate_win_count": len(new_win_contexts),
        "new_candidate_win_context_budget_keys": sorted(new_win_contexts),
        "mean_new_oracle_gap_vs_old_oracle": as_jsonable(mean_gap),
        "per_family_oracle_wins": dict(sorted(family_wins.items())),
        "harmful_false_positive_target_contexts_improved": len(harmful_improved),
        "harmful_false_positive_improved_context_keys": sorted(harmful_improved),
        "missed_helpful_oracle_gap_reduced_contexts": len(missed_helpful_improved),
        "missed_helpful_improved_context_keys": sorted(missed_helpful_improved),
        "static_boundary_contexts": len(static_boundary_contexts),
        "static_boundary_context_budget_rows_no_worse": static_boundary_no_worse,
        "additive_weak_context_budget_rows": additive_weak,
        "candidate_recognized_all": recognized_all and bool(rows),
        "gate_reasons": gate_reasons,
        "pass_candidate_space_gate": pass_gate,
        "context_oracle_csv": str(resolve(batch_oracle_context_csv(batch), root)),
        "candidate_distribution_csv": str(resolve(batch_candidate_distribution_csv(batch), root)),
        **flags,
        **G518_CLOSED_CLAIMS,
    }
    write_json_file(batch_oracle_summary(batch), summary)
    top_new = sorted(
        [row for row in candidate_rows if row["candidate_role"] == "g518_new_candidate"],
        key=lambda row: (-int(row["oracle_win_count"]), finite_number(row.get("mean_delta_vs_static"), math.inf), row["candidate_id"]),
    )[:8]
    top_lines = "\n".join(
        f"- `{row['candidate_id']}` ({row['candidate_family']}): wins `{row['oracle_win_count']}`, mean_delta `{row['mean_delta_vs_static']}`, dominated `{row['dominated_by_nearest_old']}`"
        for row in top_new
    )
    write_text_file(
        batch_oracle_report(batch),
        f"# Phase5.5 Repair5G.5.18 Batch {batch} Oracle\n\n"
        f"- decision: `{decision}`\n"
        f"- integrity_decision: `{integrity.get('decision', '')}`\n"
        f"- context_budget_pairs: `{len(context_rows)}`\n"
        f"- new_candidate_count: `{len(new_ids)}`\n"
        f"- new_candidate_win_count: `{len(new_win_contexts)}`\n"
        f"- mean_new_oracle_gap_vs_old_oracle: `{summary['mean_new_oracle_gap_vs_old_oracle']}`\n"
        f"- harmful_false_positive_target_contexts_improved: `{len(harmful_improved)}`\n"
        f"- missed_helpful_oracle_gap_reduced_contexts: `{len(missed_helpful_improved)}`\n"
        f"- static_boundary_context_budget_rows_no_worse: `{static_boundary_no_worse}`\n"
        f"- additive_weak_context_budget_rows: `{additive_weak}`\n"
        f"- gate_reasons: `{gate_reasons}`\n\n"
        "## Top New Candidates\n\n"
        f"{top_lines}\n\n"
        "Negative `mean_new_oracle_gap_vs_old_oracle` means the expanded batch oracle improved over the old-14 oracle. No-gain batches are kept as evidence rather than hidden.\n",
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    selected = selected_rows()
    error_bank = read_csv_dicts(resolve(args.error_bank_csv, root))
    batch_names = [item.strip().upper() for item in args.batches.split(",") if item.strip()]
    summaries = [analyze_batch(batch, error_bank, selected) for batch in batch_names]
    integrity_failed = [row["batch"] for row in summaries if row.get("integrity_decision") != "g518_probe_batch_integrity_passed_continue_oracle"]
    passed = [row["batch"] for row in summaries if row.get("pass_candidate_space_gate")]
    if integrity_failed:
        decision = "g518_surrogate_lattice_probe_integrity_failed"
    elif passed:
        decision = "g518_candidate_space_improved_continue_full_primary"
    else:
        decision = "g518_exploratory_lattice_no_gain_continue_lattice_design"
    aggregate = {
        "schema_version": "phase5p5_repair5g518_probe_batches_summary_v1",
        "decision": decision,
        "batch_count": len(summaries),
        "batches": summaries,
        "integrity_failed_batches": integrity_failed,
        "candidate_space_gate_passed_batches": passed,
        "full_primary_required": bool(passed),
        **G518_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, aggregate)
    lines = "\n".join(
        f"- Batch `{row['batch']}`: decision `{row['decision']}`, wins `{row['new_candidate_win_count']}`, mean gap `{row['mean_new_oracle_gap_vs_old_oracle']}`, gate `{row['pass_candidate_space_gate']}`"
        for row in summaries
    )
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.18 Probe Batches\n\n"
        f"- decision: `{decision}`\n"
        f"- batch_count: `{len(summaries)}`\n"
        f"- candidate_space_gate_passed_batches: `{passed}`\n"
        f"- integrity_failed_batches: `{integrity_failed}`\n\n"
        "## Batch Results\n\n"
        f"{lines}\n\n"
        "If no batch passes the candidate-space gate, full-primary expansion and ranker training remain intentionally skipped.\n",
    )
    print(json.dumps({"decision": decision, "passed_batches": passed, "integrity_failed_batches": integrity_failed}))
    return 0 if not integrity_failed else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

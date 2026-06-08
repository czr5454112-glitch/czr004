"""Autopsy why the G5.21 second-wave lattice did not improve candidate space."""

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

from repair5g522_common import (  # noqa: E402
    G521_GAP_MISSED_CSV,
    G521_POOL_CSV,
    G521_SELECTED_CSV,
    G521_TARGETED_ORACLE_BY_CONTEXT_CSV,
    G521_TARGETED_ORACLE_SUMMARY,
    G521_TARGETED_RESULTS_CSV,
    G522_AUTOPSY_CSV,
    G522_AUTOPSY_REPORT,
    G522_AUTOPSY_SUMMARY,
    G522_CLOSED_CLAIMS,
    NEAR_DUP_DISTANCE,
    boolish,
    candidate_params,
    csv_number,
    family_for_candidate,
    finite_number,
    g518_retained_candidate_ids,
    mean,
    old14_candidate_ids,
    param_distance,
    parameter_names,
    read_json_file,
    read_rows,
    repo_root,
    row_finite_solution,
    rows_by_context_budget,
    score,
    selected_g521_candidate_ids,
    write_json_file,
    write_rows,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-csv", type=Path, default=Path(G522_AUTOPSY_CSV))
    parser.add_argument("--report", type=Path, default=Path(G522_AUTOPSY_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G522_AUTOPSY_SUMMARY))
    return parser.parse_args(argv)


def nearest(candidate: str, refs: list[str]) -> tuple[str, float]:
    params = candidate_params(candidate)
    best = ("", math.inf)
    for ref in refs:
        dist = param_distance(params, candidate_params(ref))
        if dist < best[1] or (dist == best[1] and ref < best[0]):
            best = (ref, dist)
    return best


def param_delta(candidate: str, ref: str) -> dict[str, float]:
    lhs = candidate_params(candidate)
    rhs = candidate_params(ref)
    if lhs is None or rhs is None:
        return {name: math.inf for name in parameter_names()}
    return {
        "alpha_cong_committed": lhs.alpha_cong_committed - rhs.alpha_cong_committed,
        "alpha_cong_blocked": lhs.alpha_cong_blocked - rhs.alpha_cong_blocked,
        "alpha_flow_progress": lhs.alpha_flow_progress - rhs.alpha_flow_progress,
        "alpha_flow_wait_or_nonprogress": lhs.alpha_flow_wait_or_nonprogress - rhs.alpha_flow_wait_or_nonprogress,
        "rho_cong": lhs.rho_cong - rhs.rho_cong,
        "rho_flow": lhs.rho_flow - rhs.rho_flow,
        "flow_shield_beta": lhs.flow_shield_beta - rhs.flow_shield_beta,
        "max_flow_shield": lhs.max_flow_shield - rhs.max_flow_shield,
        "c_only": float(lhs.c_only) - float(rhs.c_only),
    }


def best_of(group: list[dict[str, Any]], allowed: set[str]) -> dict[str, Any] | None:
    finite = [row for row in group if str(row.get("candidate_id", "")) in allowed and row_finite_solution(row)]
    return min(finite, key=lambda row: (score(row), str(row.get("candidate_id", "")))) if finite else None


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_rows(G521_TARGETED_RESULTS_CSV)
    oracle_rows = read_rows(G521_TARGETED_ORACLE_BY_CONTEXT_CSV)
    summary521 = read_json_file(G521_TARGETED_ORACLE_SUMMARY)
    selected = selected_g521_candidate_ids(G521_SELECTED_CSV)
    retained = g518_retained_candidate_ids(limit=8)
    old14 = old14_candidate_ids(root)
    selected_meta = {str(row.get("candidate_id", "")): row for row in read_rows(G521_SELECTED_CSV)}
    pool_meta = {str(row.get("candidate_id", "")): row for row in read_rows(G521_POOL_CSV)}
    g521_set = set(selected)
    retained_set = set(retained)
    old14_set = set(old14)

    full_by_cb = rows_by_context_budget(rows)
    autopsy_rows: list[dict[str, Any]] = []
    induced_by_candidate = Counter()
    recovery_by_candidate = Counter()
    win_by_candidate = Counter()
    gain_values_by_candidate: dict[str, list[float]] = defaultdict(list)
    hidden_tie_count = 0
    for (_context, _budget), group in full_by_cb.items():
        static = best_of(group, {"repair5g59_static_flow_shield"})
        old_g518 = best_of(group, old14_set | retained_set)
        full = best_of(group, old14_set | retained_set | g521_set)
        if full and str(full.get("candidate_id", "")) in g521_set:
            win_by_candidate[str(full.get("candidate_id", ""))] += 1
        for row in group:
            cand = str(row.get("candidate_id", ""))
            if cand not in g521_set:
                continue
            if row_finite_solution(row) and row_finite_solution(old_g518):
                gain_values_by_candidate[cand].append(score(row) - score(old_g518))
            if row_finite_solution(static) and not row_finite_solution(row):
                induced_by_candidate[cand] += 1
            if (not row_finite_solution(static)) and row_finite_solution(row):
                recovery_by_candidate[cand] += 1
        if full and str(full.get("candidate_id", "")) in retained_set:
            full_params = candidate_params(str(full.get("candidate_id", "")))
            for cand in selected:
                if param_distance(candidate_params(cand), full_params) == 0.0:
                    hidden_tie_count += 1
                    break

    changed_counter = Counter()
    changed_abs: dict[str, list[float]] = defaultdict(list)
    for candidate in selected:
        nearest_g518, distance = nearest(candidate, retained)
        deltas = param_delta(candidate, nearest_g518)
        for name, value in deltas.items():
            if math.isfinite(value):
                changed_abs[name].append(abs(value))
                if abs(value) > 1.0e-9:
                    changed_counter[name] += 1
        autopsy_rows.append(
            {
                "row_type": "selected_g521_candidate",
                "candidate_id": candidate,
                "candidate_block": selected_meta.get(candidate, pool_meta.get(candidate, {})).get("candidate_block", ""),
                "candidate_family": family_for_candidate(candidate),
                "nearest_retained_g518": nearest_g518,
                "nearest_retained_g518_distance": csv_number(distance),
                "exact_duplicate_of_retained_g518": distance == 0.0,
                "near_duplicate_of_retained_g518": distance <= NEAR_DUP_DISTANCE,
                "oracle_win_budget_pairs": win_by_candidate[candidate],
                "candidate_induced_no_solution_count": induced_by_candidate[candidate],
                "static_failure_recovery_count": recovery_by_candidate[candidate],
                "mean_delta_vs_old14_plus_g518": csv_number(mean(gain_values_by_candidate[candidate])),
                **{f"delta_{name}": csv_number(value) for name, value in deltas.items()},
                **G522_CLOSED_CLAIMS,
            }
        )

    exact_count = sum(1 for row in autopsy_rows if boolish(row.get("exact_duplicate_of_retained_g518")))
    near_count = sum(1 for row in autopsy_rows if boolish(row.get("near_duplicate_of_retained_g518")))
    unique_params = len({tuple(candidate_params(candidate).as_tuple()) for candidate in selected if candidate_params(candidate) is not None})
    block_failure_counts = dict(sorted(Counter(str(row.get("candidate_block", "")) for row in autopsy_rows for _ in range(int(finite_number(row.get("candidate_induced_no_solution_count"), 0)))).items()))
    block_gain_counts = dict(sorted(Counter(str(row.get("candidate_block", "")) for row in autopsy_rows for _ in range(int(finite_number(row.get("oracle_win_budget_pairs"), 0)))).items()))
    dominant_old14 = Counter(str(row.get("g521_full_oracle_candidate", "")) for row in oracle_rows if str(row.get("g521_full_oracle_candidate", "")) in old14_set).most_common(8)
    dominant_g518 = Counter(str(row.get("g521_full_oracle_candidate", "")) for row in oracle_rows if str(row.get("g521_full_oracle_candidate", "")) in retained_set).most_common(8)
    missed_contexts = read_rows(G521_GAP_MISSED_CSV)
    response_focus_new = len({str(row.get("normalized_context_key", "")) for row in missed_contexts})
    robust_safe_wins = [
        context
        for context, group in defaultdict(list, {
            c: [row for row in oracle_rows if str(row.get("normalized_context_key", "")) == c]
            for c in {str(row.get("normalized_context_key", "")) for row in oracle_rows}
        }).items()
        if all(boolish(row.get("safe_second_wave_oracle_winner")) for row in group) and len(group) >= 2
    ]
    recommended = [
        "deduplicate exact aliases before second-wave selection",
        "increase static-recovery and feasibility-oriented contexts",
        "sample broader bounded response gradients instead of near-neighbor tweaks",
        "include risk-boundary candidates as negative teacher labels",
    ]
    summary = {
        "schema_version": "phase5p5_repair5g522_g521_lattice_failure_autopsy_summary_v1",
        "decision": "g521_lattice_failure_autopsy_completed_continue_context_panel",
        "exact_duplicate_g521_vs_g518_count": exact_count,
        "near_duplicate_g521_vs_g518_count": near_count,
        "second_wave_unique_param_count": unique_params,
        "g521_candidate_induced_no_solution_count": int(finite_number(summary521.get("candidate_induced_no_solution_count"), sum(induced_by_candidate.values()))),
        "g521_static_recovery_count": int(finite_number(summary521.get("static_failure_candidate_recovers_count"), sum(recovery_by_candidate.values()))),
        "safe_second_wave_win_contexts": int(finite_number(summary521.get("safe_second_wave_win_contexts"), 0)),
        "safe_win_robust_across_budgets_contexts": robust_safe_wins,
        "tie_breaking_hidden_duplicate_budget_pairs": hidden_tie_count,
        "dominant_retained_g518_candidates": dict(dominant_g518),
        "dominant_old14_candidates": dict(dominant_old14),
        "block_failure_counts": block_failure_counts,
        "block_gain_counts": block_gain_counts,
        "dimension_change_counts": dict(sorted(changed_counter.items())),
        "dimension_mean_abs_change": {key: mean(values) for key, values in sorted(changed_abs.items())},
        "response_region_focus_new_opportunity_contexts": response_focus_new,
        "recommended_response_surface_regions": recommended,
        **G522_CLOSED_CLAIMS,
    }
    write_rows(args.output_csv, autopsy_rows)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.22 G5.21 Lattice Failure Autopsy\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- exact_duplicate_g521_vs_g518_count: `{exact_count}`\n"
        f"- near_duplicate_g521_vs_g518_count: `{near_count}`\n"
        f"- second_wave_unique_param_count: `{unique_params}`\n"
        f"- g521_candidate_induced_no_solution_count: `{summary['g521_candidate_induced_no_solution_count']}`\n"
        f"- g521_static_recovery_count: `{summary['g521_static_recovery_count']}`\n"
        f"- safe_second_wave_win_contexts: `{summary['safe_second_wave_win_contexts']}`\n"
        f"- tie_breaking_hidden_duplicate_budget_pairs: `{hidden_tie_count}`\n"
        f"- block_failure_counts: `{block_failure_counts}`\n"
        f"- block_gain_counts: `{block_gain_counts}`\n"
        f"- recommended_response_surface_regions: `{recommended}`\n\n"
        "The G5.21 selected names were often geometrically close to retained G5.18 controls. The next step should build a broader response surface with explicit feasibility and risk-boundary strata.\n",
    )
    print(json.dumps({"decision": summary["decision"], "near_duplicates": near_count}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

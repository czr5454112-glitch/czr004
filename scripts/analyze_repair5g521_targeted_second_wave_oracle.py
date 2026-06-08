"""Analyze targeted G5.21 second-wave oracle gain."""

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
    ADDITIVE_CANDIDATE,
    G521_CLOSED_CLAIMS,
    G521_TARGETED_CANDIDATE_DISTRIBUTION_CSV,
    G521_TARGETED_INTEGRITY_SUMMARY,
    G521_TARGETED_ORACLE_BY_CONTEXT_CSV,
    G521_TARGETED_ORACLE_REPORT,
    G521_TARGETED_ORACLE_SUMMARY,
    G521_TARGETED_RESULTS_CSV,
    PRIMARY_BUDGETS,
    STATIC_FLOW_SHIELD_CANDIDATE,
    best_row,
    boolish,
    candidate_params,
    candidate_role,
    csv_number,
    family_for_candidate,
    finite_delta,
    finite_mean,
    finite_number,
    g518_retained_candidate_ids,
    mean,
    old14_candidate_ids,
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
    parser.add_argument("--results-csv", type=Path, default=Path(G521_TARGETED_RESULTS_CSV))
    parser.add_argument("--integrity-summary-json", type=Path, default=Path(G521_TARGETED_INTEGRITY_SUMMARY))
    parser.add_argument("--oracle-by-context-csv", type=Path, default=Path(G521_TARGETED_ORACLE_BY_CONTEXT_CSV))
    parser.add_argument("--candidate-distribution-csv", type=Path, default=Path(G521_TARGETED_CANDIDATE_DISTRIBUTION_CSV))
    parser.add_argument("--report", type=Path, default=Path(G521_TARGETED_ORACLE_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G521_TARGETED_ORACLE_SUMMARY))
    return parser.parse_args(argv)


def best_of(rows: list[dict[str, Any]], allowed: set[str]) -> dict[str, Any] | None:
    return best_row([row for row in rows if str(row.get("candidate_id", "")) in allowed])


def candidate_distribution(rows: list[dict[str, Any]], old_ids: set[str], g518_ids: set[str], g521_ids: set[str]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("candidate_id", ""))].append(row)
    out = []
    for candidate, group in sorted(grouped.items()):
        finite_rows = [row for row in group if row_finite_solution(row)]
        context_budget_wins = sum(1 for row in group if boolish(row.get("_g521_full_oracle_winner")))
        static = [row for row in group if boolish(row.get("_static_finite"))]
        induced = sum(1 for row in group if boolish(row.get("_candidate_induced_failure")))
        recovered = sum(1 for row in group if boolish(row.get("_candidate_recovers_static_failure")))
        out.append(
            {
                "candidate_id": candidate,
                "candidate_role": candidate_role(candidate, old_ids, g518_ids, g521_ids),
                "candidate_family": family_for_candidate(candidate),
                "rows": len(group),
                "finite_rows": len(finite_rows),
                "oracle_win_count": context_budget_wins,
                "candidate_induced_no_solution_count": induced,
                "static_failure_candidate_recovers_count": recovered,
                "mean_score": csv_number(mean([score(row) for row in finite_rows])),
                "static_finite_comparison_rows": len(static),
                **G521_CLOSED_CLAIMS,
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    integrity = read_json_file(args.integrity_summary_json)
    if integrity.get("decision") != "targeted_second_wave_probe_integrity_passed_continue_oracle":
        summary = {
            "schema_version": "phase5p5_repair5g521_targeted_second_wave_oracle_summary_v1",
            "decision": "targeted_oracle_not_run_integrity_failed",
            "integrity_decision": integrity.get("decision", ""),
            **G521_CLOSED_CLAIMS,
        }
        write_json_file(args.summary_json, summary)
        write_text_file(args.report, "# Repair5G.5.21 Targeted Second-Wave Oracle\n\n- decision: `targeted_oracle_not_run_integrity_failed`\n")
        print(json.dumps({"decision": summary["decision"]}))
        return 2

    rows = read_rows(args.results_csv)
    old_ids = set(old14_candidate_ids(root))
    g518_ids = set(g518_retained_candidate_ids(limit=8))
    g521_ids = set(selected_g521_candidate_ids())
    old_plus_g518 = old_ids | g518_ids
    full = old_ids | g518_ids | g521_ids
    by_cb = rows_by_context_budget(rows)
    oracle_rows = []
    annotated = []
    gaps_vs_old14 = []
    gaps_vs_g518_only = []
    gaps_vs_old_g518 = []
    second_wave_win_pairs = 0
    safe_second_wave_win_pairs = 0
    context_second_wave_wins: set[str] = set()
    safe_context_second_wave_wins: set[str] = set()
    candidate_induced_count = 0
    recovery_count = 0
    finite_pairwise_gains = []
    block_win_counts: dict[str, int] = defaultdict(int)
    candidate_win_counts: dict[str, int] = defaultdict(int)
    winners_by_context: dict[str, list[str]] = defaultdict(list)
    for (context, budget), group in sorted(by_cb.items()):
        static = best_of(group, {STATIC_FLOW_SHIELD_CANDIDATE})
        additive = best_of(group, {ADDITIVE_CANDIDATE})
        old14 = best_of(group, old_ids)
        g518_only = best_of(group, g518_ids)
        old_g518 = best_of(group, old_plus_g518)
        full_best = best_of(group, full)
        g521_best = best_of(group, g521_ids)
        static_finite = row_finite_solution(static)
        for row in group:
            candidate = str(row.get("candidate_id", ""))
            candidate_finite = row_finite_solution(row)
            induced = static_finite and not candidate_finite
            recovery = (not static_finite) and candidate_finite
            if candidate in g521_ids and induced:
                candidate_induced_count += 1
            if candidate in g521_ids and recovery:
                recovery_count += 1
            annotated.append({**row, "_static_finite": static_finite, "_candidate_induced_failure": induced, "_candidate_recovers_static_failure": recovery})
        full_id = str((full_best or {}).get("candidate_id", ""))
        winners_by_context[context].append(full_id)
        if row_finite_solution(full_best) and row_finite_solution(old14):
            gaps_vs_old14.append(score(full_best) - score(old14))
        if row_finite_solution(full_best) and row_finite_solution(g518_only):
            gaps_vs_g518_only.append(score(full_best) - score(g518_only))
        if row_finite_solution(full_best) and row_finite_solution(old_g518):
            gaps_vs_old_g518.append(score(full_best) - score(old_g518))
        is_g521_win = full_id in g521_ids
        safe_win = False
        if is_g521_win:
            second_wave_win_pairs += 1
            context_second_wave_wins.add(context)
            block_win_counts[family_for_candidate(full_id)] += 1
            candidate_win_counts[full_id] += 1
            full_delta_static = finite_delta(full_best, static)
            if math.isfinite(full_delta_static):
                finite_pairwise_gains.append(full_delta_static)
            safe_win = not (static_finite and not row_finite_solution(full_best))
            if safe_win:
                safe_second_wave_win_pairs += 1
                safe_context_second_wave_wins.add(context)
        oracle_rows.append(
            {
                "normalized_context_key": context,
                "short_budget_ms": budget,
                "static_candidate": STATIC_FLOW_SHIELD_CANDIDATE,
                "static_score": csv_number(score(static)),
                "additive_score": csv_number(score(additive)),
                "old14_oracle_candidate": (old14 or {}).get("candidate_id", ""),
                "old14_oracle_score": csv_number(score(old14)),
                "g518_retained8_oracle_candidate": (g518_only or {}).get("candidate_id", ""),
                "g518_retained8_oracle_score": csv_number(score(g518_only)),
                "old14_plus_g518_retained8_oracle_candidate": (old_g518 or {}).get("candidate_id", ""),
                "old14_plus_g518_retained8_oracle_score": csv_number(score(old_g518)),
                "g521_full_oracle_candidate": full_id,
                "g521_full_oracle_score": csv_number(score(full_best)),
                "best_second_wave_candidate": (g521_best or {}).get("candidate_id", ""),
                "best_second_wave_score": csv_number(score(g521_best)),
                "second_wave_oracle_winner": is_g521_win,
                "safe_second_wave_oracle_winner": safe_win,
                "gap_full_vs_old14": csv_number(score(full_best) - score(old14) if row_finite_solution(full_best) and row_finite_solution(old14) else math.inf),
                "gap_full_vs_g518_retained8": csv_number(score(full_best) - score(g518_only) if row_finite_solution(full_best) and row_finite_solution(g518_only) else math.inf),
                "gap_full_vs_old14_plus_g518": csv_number(score(full_best) - score(old_g518) if row_finite_solution(full_best) and row_finite_solution(old_g518) else math.inf),
                **G521_CLOSED_CLAIMS,
            }
        )

    winner_by_key = {(row["normalized_context_key"], int(row["short_budget_ms"])): row["g521_full_oracle_candidate"] for row in oracle_rows}
    for row in annotated:
        key = (str(row.get("normalized_context_key", "")), int(finite_number(row.get("short_budget_ms"), -1)))
        row["_g521_full_oracle_winner"] = str(row.get("candidate_id", "")) == str(winner_by_key.get(key, ""))
    distribution = candidate_distribution(annotated, old_ids, g518_ids, g521_ids)
    stable_contexts = 0
    for winners in winners_by_context.values():
        winners = [winner for winner in winners if winner]
        if len(winners) >= 2 and len(set(winners)) == 1:
            stable_contexts += 1
    budget_stability = stable_contexts / len(winners_by_context) if winners_by_context else 0.0
    second_wave_gap = mean(gaps_vs_old_g518)
    gate = (
        (math.isfinite(second_wave_gap) and second_wave_gap <= -0.001)
        or len(safe_context_second_wave_wins) >= 2
        or (recovery_count > 0 and candidate_induced_count == 0)
    )
    decision = "targeted_second_wave_gate_passed_continue_full_primary" if gate else "targeted_second_wave_gate_failed_lattice_autopsy"
    summary = {
        "schema_version": "phase5p5_repair5g521_targeted_second_wave_oracle_summary_v1",
        "decision": decision,
        "targeted_gate_passed": gate,
        "context_budget_pairs": len(oracle_rows),
        "contexts": len(winners_by_context),
        "mean_oracle_gap_vs_old14": mean(gaps_vs_old14),
        "mean_oracle_gap_vs_g518_retained8": mean(gaps_vs_g518_only),
        "second_wave_oracle_gap_vs_g518_retained8": second_wave_gap,
        "new_second_wave_win_contexts": len(context_second_wave_wins),
        "new_second_wave_win_budget_pairs": second_wave_win_pairs,
        "safe_second_wave_win_contexts": len(safe_context_second_wave_wins),
        "safe_second_wave_win_budget_pairs": safe_second_wave_win_pairs,
        "candidate_induced_no_solution_count": candidate_induced_count,
        "static_failure_candidate_recovers_count": recovery_count,
        "finite_pairwise_solution_quality_gain": mean(finite_pairwise_gains),
        "budget_stability_1000_2000": budget_stability,
        "block_win_counts": dict(sorted(block_win_counts.items())),
        "candidate_win_counts": dict(sorted(candidate_win_counts.items())),
        "best_fixed_second_wave_candidate": min(
            [row for row in distribution if row["candidate_role"] == "g521_second_wave"],
            key=lambda row: (finite_number(row.get("mean_score"), math.inf), -finite_number(row.get("oracle_win_count"), 0), str(row.get("candidate_id", ""))),
        ).get("candidate_id", "")
        if any(row["candidate_role"] == "g521_second_wave" for row in distribution)
        else "",
        "best_block_level_candidate_family": max(block_win_counts.items(), key=lambda item: (item[1], item[0]))[0] if block_win_counts else "",
        **G521_CLOSED_CLAIMS,
    }
    write_rows(args.oracle_by_context_csv, oracle_rows)
    write_rows(args.candidate_distribution_csv, distribution)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.21 Targeted Second-Wave Oracle\n\n"
        f"- decision: `{decision}`\n"
        f"- targeted_gate_passed: `{gate}`\n"
        f"- context_budget_pairs: `{len(oracle_rows)}`\n"
        f"- second_wave_oracle_gap_vs_g518_retained8: `{csv_number(second_wave_gap)}`\n"
        f"- new_second_wave_win_contexts: `{len(context_second_wave_wins)}`\n"
        f"- new_second_wave_win_budget_pairs: `{second_wave_win_pairs}`\n"
        f"- safe_second_wave_win_contexts: `{len(safe_context_second_wave_wins)}`\n"
        f"- candidate_induced_no_solution_count: `{candidate_induced_count}`\n"
        f"- static_failure_candidate_recovers_count: `{recovery_count}`\n"
        f"- budget_stability_1000_2000: `{csv_number(budget_stability)}`\n"
        f"- block_win_counts: `{dict(sorted(block_win_counts.items()))}`\n\n"
        + (
            "The targeted candidate-space gate passed, so full-primary confirmation is allowed.\n"
            if gate
            else "Deep lattice failure autopsy: the targeted probe did not show enough safe second-wave win contexts, oracle gap, or static-failure recovery to justify full-primary confirmation.\n"
        ),
    )
    print(json.dumps({"decision": decision, "targeted_gate_passed": gate, "safe_second_wave_win_contexts": len(safe_context_second_wave_wins)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Analyze G5.19 reconstructed full-primary candidate space."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g519_common import (  # noqa: E402
    DEFAULT_MARGIN,
    G519_CANDIDATE_DISTRIBUTION_CSV,
    G519_CANDIDATE_SPACE_REPORT,
    G519_CANDIDATE_SPACE_SUMMARY,
    G519_CLOSED_CLAIMS,
    G519_ORACLE_BY_CONTEXT_CSV,
    G519_TARGETS_CSV,
    boolish,
    compact_counter,
    csv_number,
    finite_number,
    map_agent_key,
    mean,
    read_rows,
    rows_by_context,
    write_json_file,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets-csv", type=Path, default=Path(G519_TARGETS_CSV))
    parser.add_argument("--oracle-by-context-csv", type=Path, default=Path(G519_ORACLE_BY_CONTEXT_CSV))
    parser.add_argument("--distribution-csv", type=Path, default=Path(G519_CANDIDATE_DISTRIBUTION_CSV))
    parser.add_argument("--report", type=Path, default=Path(G519_CANDIDATE_SPACE_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G519_CANDIDATE_SPACE_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = read_rows(args.targets_csv)
    oracle_rows = read_rows(args.oracle_by_context_csv)
    distribution = read_rows(args.distribution_csv)
    new_win_budget_rows = [row for row in oracle_rows if boolish(row.get("new_candidate_wins_budget"))]
    new_win_contexts = sorted({row.get("normalized_context_key", "") for row in new_win_budget_rows})
    gaps = [finite_number(row.get("new22_gap_vs_old14"), math.inf) for row in oracle_rows]
    additive_weak = [
        row
        for row in oracle_rows
        if finite_number(row.get("additive_score"), math.inf) - finite_number(row.get("new22_oracle_score"), math.inf) >= DEFAULT_MARGIN
    ]
    static_boundary = [
        row
        for row in oracle_rows
        if finite_number(row.get("static_score"), math.inf) - finite_number(row.get("new22_oracle_score"), math.inf) < DEFAULT_MARGIN
    ]
    harmful_false_positive_targets = [
        row
        for row in rows
        if boolish(row.get("harmful_vs_static")) and finite_number(row.get("new22_oracle_regret_primary"), math.inf) > DEFAULT_MARGIN
    ]
    missed_helpful = [
        group[0]
        for group in rows_by_context(rows).values()
        if any(finite_number(row.get("mean_delta_vs_static_primary"), math.inf) <= -DEFAULT_MARGIN for row in group)
        and finite_number(next((row for row in group if row.get("candidate_id") == "repair5g59_static_flow_shield"), group[0]).get("new22_oracle_regret_primary"), math.inf) >= DEFAULT_MARGIN
    ]
    dominated_new = [
        row
        for row in distribution
        if boolish(row.get("is_new_candidate")) and finite_number(row.get("nearest_old_param_distance"), math.inf) <= 1.0e-12
    ]
    useful_new_by_group: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if boolish(row.get("is_new_candidate")) and boolish(row.get("helpful_vs_static")):
            useful_new_by_group[map_agent_key(row)].append(str(row.get("candidate_id", "")))
    per_family_oracle = compact_counter(
        (
            {"family": row.get("candidate_family", "")}
            for row in rows
            if boolish(row.get("is_new22_oracle_winner"))
        ),
        "family",
    )
    best_new = [row for row in distribution if boolish(row.get("is_new_candidate"))]
    summary = {
        "schema_version": "phase5p5_repair5g519_full_primary_candidate_space_summary_v1",
        "decision": "candidate_space_analysis_completed_continue_feature_matrix_v8",
        "target_rows": len(rows),
        "new_candidate_win_count": len(new_win_budget_rows),
        "new_candidate_win_contexts": len(new_win_contexts),
        "new_candidate_win_budget_pairs": len(new_win_budget_rows),
        "old14_vs_new22_oracle_gap_mean": finite_number(mean(gaps), math.inf),
        "old14_vs_new22_oracle_gap_min": min(gaps) if gaps else math.inf,
        "old14_vs_new22_oracle_gap_max": max(gaps) if gaps else math.inf,
        "per_family_oracle_win_count": per_family_oracle,
        "new_candidates_dominated_by_nearest_old_candidate": [row.get("candidate_id", "") for row in dominated_new],
        "new_candidate_useful_map_agent_groups": {key: sorted(set(value)) for key, value in sorted(useful_new_by_group.items())},
        "additive_weak_context_budget_rows": len(additive_weak),
        "static_boundary_context_budget_rows": len(static_boundary),
        "harmful_false_positive_target_cases": len(harmful_false_positive_targets),
        "missed_helpful_cases": len(missed_helpful),
        "best_new_by_mean_delta": min(best_new, key=lambda row: (finite_number(row.get("mean_delta_vs_static"), math.inf), row.get("candidate_id", ""))).get("candidate_id", "") if best_new else "",
        "best_new_by_oracle_wins": max(best_new, key=lambda row: (finite_number(row.get("oracle_win_count"), 0), -finite_number(row.get("mean_delta_vs_static"), math.inf))).get("candidate_id", "") if best_new else "",
        "best_new_by_risk_adjusted": min(best_new, key=lambda row: (finite_number(row.get("risk_adjusted_utility_lambda_0p10"), math.inf), row.get("candidate_id", ""))).get("candidate_id", "") if best_new else "",
        **G519_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, summary)
    top_distribution = sorted(
        distribution,
        key=lambda row: (finite_number(row.get("mean_delta_vs_static"), math.inf), -finite_number(row.get("oracle_win_count"), 0), row.get("candidate_id", "")),
    )[:10]
    top_lines = "\n".join(
        f"- `{row.get('candidate_id', '')}` source=`{row.get('candidate_source', '')}` mean_delta=`{row.get('mean_delta_vs_static', '')}` oracle_wins=`{row.get('oracle_win_count', '')}` harmful_rate=`{row.get('harmful_rate', '')}`"
        for row in top_distribution
    )
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.19 Candidate-Space Analysis\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- new_candidate_win_count: `{summary['new_candidate_win_count']}`\n"
        f"- new_candidate_win_contexts: `{summary['new_candidate_win_contexts']}`\n"
        f"- old14_vs_new22_oracle_gap_mean: `{csv_number(summary['old14_vs_new22_oracle_gap_mean'])}`\n"
        f"- additive_weak_context_budget_rows: `{len(additive_weak)}`\n"
        f"- static_boundary_context_budget_rows: `{len(static_boundary)}`\n"
        f"- harmful_false_positive_target_cases: `{len(harmful_false_positive_targets)}`\n"
        f"- missed_helpful_cases: `{len(missed_helpful)}`\n"
        f"- best_new_by_mean_delta: `{summary['best_new_by_mean_delta']}`\n"
        f"- best_new_by_oracle_wins: `{summary['best_new_by_oracle_wins']}`\n"
        f"- best_new_by_risk_adjusted: `{summary['best_new_by_risk_adjusted']}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "## Top Candidates\n\n"
        f"{top_lines}\n\n"
        "G5.18 candidate-space evidence survives reconstruction if new candidates win budget pairs and the new22 oracle remains below the old14 oracle. "
        "This report is still oracle/candidate-space evidence, not runtime policy evidence.\n",
    )
    print(json.dumps({"decision": summary["decision"], "new_candidate_win_count": len(new_win_budget_rows)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

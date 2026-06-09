"""Analyze G5.22 response-surface oracle gain and parameter signal."""

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
    ADDITIVE_CANDIDATE,
    G522_CLOSED_CLAIMS,
    G522_ORACLE_BY_CONTEXT_CSV,
    G522_ORACLE_CANDIDATE_DISTRIBUTION_CSV,
    G522_ORACLE_PARAM_IMPORTANCE_CSV,
    G522_ORACLE_REGION_BUCKET_CSV,
    G522_ORACLE_REPORT,
    G522_ORACLE_SUMMARY,
    G522_PROBE_INTEGRITY_SUMMARY,
    G522_PROBE_RESULTS_CSV,
    STATIC_FLOW_SHIELD_CANDIDATE,
    best_of,
    boolish,
    candidate_params,
    candidate_role,
    context_bucket_lookup,
    csv_number,
    design_rows_by_candidate,
    finite_number,
    g518_retained_candidate_ids,
    mean,
    numeric_candidate_param_dict,
    old14_candidate_ids,
    parameter_names,
    pearson,
    read_json_file,
    read_rows,
    repo_root,
    row_finite_solution,
    rows_by_context_budget,
    rows_by_context_candidate,
    score,
    selected_g522_candidate_ids,
    spearman,
    write_json_file,
    write_rows,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-csv", type=Path, default=Path(G522_PROBE_RESULTS_CSV))
    parser.add_argument("--integrity-summary-json", type=Path, default=Path(G522_PROBE_INTEGRITY_SUMMARY))
    parser.add_argument("--oracle-by-context-csv", type=Path, default=Path(G522_ORACLE_BY_CONTEXT_CSV))
    parser.add_argument("--candidate-distribution-csv", type=Path, default=Path(G522_ORACLE_CANDIDATE_DISTRIBUTION_CSV))
    parser.add_argument("--param-importance-csv", type=Path, default=Path(G522_ORACLE_PARAM_IMPORTANCE_CSV))
    parser.add_argument("--region-bucket-csv", type=Path, default=Path(G522_ORACLE_REGION_BUCKET_CSV))
    parser.add_argument("--report", type=Path, default=Path(G522_ORACLE_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G522_ORACLE_SUMMARY))
    return parser.parse_args(argv)


def finite_delta(lhs: dict[str, Any] | None, rhs: dict[str, Any] | None) -> float:
    if row_finite_solution(lhs) and row_finite_solution(rhs):
        return score(lhs) - score(rhs)
    return math.inf


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    integrity = read_json_file(args.integrity_summary_json)
    if integrity.get("decision") != "response_surface_probe_integrity_passed_continue_oracle":
        summary = {
            "schema_version": "phase5p5_repair5g522_response_surface_oracle_summary_v1",
            "decision": "response_surface_oracle_not_run_integrity_failed",
            "integrity_decision": integrity.get("decision", ""),
            **G522_CLOSED_CLAIMS,
        }
        write_json_file(args.summary_json, summary)
        write_text_file(args.report, "# Repair5G.5.22 Response-Surface Oracle\n\n- decision: `response_surface_oracle_not_run_integrity_failed`\n")
        print(json.dumps({"decision": summary["decision"]}))
        return 2

    rows = read_rows(args.results_csv)
    design = design_rows_by_candidate()
    buckets = context_bucket_lookup()
    old_ids = set(old14_candidate_ids(root))
    g518_ids = set(g518_retained_candidate_ids(limit=8))
    g522_ids = set(selected_g522_candidate_ids(include_probe_only=True))
    old_g518 = old_ids | g518_ids
    full = old_g518 | g522_ids
    by_cb = rows_by_context_budget(rows)
    oracle_rows = []
    annotated = []
    gaps_old14 = []
    gaps_g518 = []
    gaps_old_g518 = []
    g522_win_pairs = 0
    safe_g522_win_pairs = 0
    safe_g522_win_contexts: set[str] = set()
    g522_win_contexts: set[str] = set()
    induced_count = 0
    recovery_count = 0
    budget_sensitive_failures = 0
    finite_pairwise_gains = []
    region_win_counts = Counter()
    candidate_win_counts = Counter()
    winners_by_context: dict[str, list[str]] = defaultdict(list)
    for (context, budget), group in sorted(by_cb.items()):
        static = best_of(group, {STATIC_FLOW_SHIELD_CANDIDATE})
        additive = best_of(group, {ADDITIVE_CANDIDATE})
        old14 = best_of(group, old_ids)
        g518_only = best_of(group, g518_ids)
        old_g518_best = best_of(group, old_g518)
        g522_best = best_of(group, g522_ids)
        full_best = best_of(group, full)
        static_finite = row_finite_solution(static)
        for row in group:
            candidate = str(row.get("candidate_id", ""))
            if candidate not in g522_ids:
                continue
            candidate_finite = row_finite_solution(row)
            induced = static_finite and not candidate_finite
            recovery = (not static_finite) and candidate_finite
            if induced:
                induced_count += 1
            if recovery:
                recovery_count += 1
            annotated.append({**row, "_static_finite": static_finite, "_candidate_induced_failure": induced, "_candidate_recovers_static_failure": recovery})
            delta = finite_delta(row, old_g518_best)
            if math.isfinite(delta):
                finite_pairwise_gains.append(delta)
        full_id = str((full_best or {}).get("candidate_id", ""))
        winners_by_context[context].append(full_id)
        if row_finite_solution(full_best) and row_finite_solution(old14):
            gaps_old14.append(score(full_best) - score(old14))
        if row_finite_solution(full_best) and row_finite_solution(g518_only):
            gaps_g518.append(score(full_best) - score(g518_only))
        if row_finite_solution(full_best) and row_finite_solution(old_g518_best):
            gaps_old_g518.append(score(full_best) - score(old_g518_best))
        is_g522_win = full_id in g522_ids
        safe_win = False
        if is_g522_win:
            g522_win_pairs += 1
            g522_win_contexts.add(context)
            candidate_win_counts[full_id] += 1
            region = str(design.get(full_id, {}).get("candidate_region", "g522_unknown"))
            region_win_counts[region] += 1
            safe_win = not (static_finite and not row_finite_solution(full_best))
            if safe_win:
                safe_g522_win_pairs += 1
                safe_g522_win_contexts.add(context)
        oracle_rows.append(
            {
                "normalized_context_key": context,
                "context_bucket": buckets.get(context, ""),
                "short_budget_ms": budget,
                "static_score": csv_number(score(static)),
                "additive_score": csv_number(score(additive)),
                "old14_oracle_candidate": (old14 or {}).get("candidate_id", ""),
                "old14_oracle_score": csv_number(score(old14)),
                "g518_retained_oracle_candidate": (g518_only or {}).get("candidate_id", ""),
                "g518_retained_oracle_score": csv_number(score(g518_only)),
                "old14_plus_g518_oracle_candidate": (old_g518_best or {}).get("candidate_id", ""),
                "old14_plus_g518_oracle_score": csv_number(score(old_g518_best)),
                "g522_oracle_candidate": (g522_best or {}).get("candidate_id", ""),
                "g522_oracle_score": csv_number(score(g522_best)),
                "old14_plus_g518_plus_g522_oracle_candidate": full_id,
                "old14_plus_g518_plus_g522_oracle_score": csv_number(score(full_best)),
                "g522_response_surface_oracle_winner": is_g522_win,
                "safe_g522_response_surface_oracle_winner": safe_win,
                "incremental_gap_vs_old14_plus_g518": csv_number(finite_delta(full_best, old_g518_best)),
                "gap_full_vs_old14": csv_number(finite_delta(full_best, old14)),
                "gap_full_vs_g518": csv_number(finite_delta(full_best, g518_only)),
                **G522_CLOSED_CLAIMS,
            }
        )

    by_context_candidate = rows_by_context_candidate(rows)
    for (context, candidate), group in by_context_candidate.items():
        if candidate not in g522_ids:
            continue
        finite_flags = [row_finite_solution(row) for row in group]
        if len(set(finite_flags)) > 1:
            budget_sensitive_failures += 1

    distribution = []
    for candidate, group in sorted(defaultdict(list, {c: [row for row in annotated if row.get("candidate_id") == c] for c in g522_ids}).items()):
        finite_rows = [row for row in group if row_finite_solution(row)]
        distribution.append(
            {
                "candidate_id": candidate,
                "candidate_role": candidate_role(candidate, old_ids, g518_ids, set(), g522_ids),
                "candidate_region": design.get(candidate, {}).get("candidate_region", ""),
                "candidate_family": design.get(candidate, {}).get("candidate_family", ""),
                "rows": len(group),
                "finite_rows": len(finite_rows),
                "oracle_win_count": candidate_win_counts[candidate],
                "candidate_induced_no_solution_count": sum(1 for row in group if boolish(row.get("_candidate_induced_failure"))),
                "static_failure_candidate_recovers_count": sum(1 for row in group if boolish(row.get("_candidate_recovers_static_failure"))),
                "mean_score": csv_number(mean([score(row) for row in finite_rows])),
                **numeric_candidate_param_dict(candidate),
                **G522_CLOSED_CLAIMS,
            }
        )

    param_rows = []
    for name in parameter_names():
        xs = [finite_number(row.get(name), math.nan) for row in distribution]
        ys_gain = [-finite_number(row.get("mean_score"), math.nan) for row in distribution]
        ys_win = [finite_number(row.get("oracle_win_count"), 0.0) for row in distribution]
        param_rows.append(
            {
                "parameter": name,
                "linear_corr_neg_mean_score": csv_number(pearson(xs, ys_gain)),
                "rank_corr_oracle_wins": csv_number(spearman(xs, ys_win)),
                "mean_value": csv_number(mean(xs)),
                **G522_CLOSED_CLAIMS,
            }
        )
    bucket_region_rows = []
    grouped_region_bucket: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in oracle_rows:
        winner = str(row.get("old14_plus_g518_plus_g522_oracle_candidate", ""))
        region = str(design.get(winner, {}).get("candidate_region", "control_or_no_g522"))
        grouped_region_bucket[(str(row.get("context_bucket", "")), region)].append(row)
    for (bucket, region), group in sorted(grouped_region_bucket.items()):
        bucket_region_rows.append(
            {
                "context_bucket": bucket,
                "candidate_region": region,
                "context_budget_pairs": len(group),
                "safe_g522_win_pairs": sum(1 for row in group if boolish(row.get("safe_g522_response_surface_oracle_winner"))),
                "mean_incremental_gap_vs_old14_plus_g518": csv_number(mean([finite_number(row.get("incremental_gap_vs_old14_plus_g518"), math.inf) for row in group])),
                **G522_CLOSED_CLAIMS,
            }
        )

    stable_contexts = sum(1 for winners in winners_by_context.values() if len(winners) >= 2 and len(set(winners)) == 1)
    budget_stability = stable_contexts / len(winners_by_context) if winners_by_context else 0.0
    incremental_gap = mean(gaps_old_g518)
    continuation_gate = (
        (math.isfinite(incremental_gap) and incremental_gap <= -0.001)
        or len(safe_g522_win_contexts) >= 3
        or (recovery_count >= 2 and induced_count <= int(finite_number(read_json_file("outputs/reports/phase5p5_repair5g521_targeted_second_wave_oracle_summary.json").get("candidate_induced_no_solution_count"), induced_count)))
    )
    summary = {
        "schema_version": "phase5p5_repair5g522_response_surface_oracle_summary_v1",
        "decision": "response_surface_oracle_completed_continue_teacher_dataset",
        "candidate_space_continuation_gate_passed": continuation_gate,
        "context_budget_pairs": len(oracle_rows),
        "contexts": len(winners_by_context),
        "mean_oracle_gap_vs_old14": mean(gaps_old14),
        "mean_oracle_gap_vs_g518_retained": mean(gaps_g518),
        "incremental_oracle_gap_vs_old14_plus_g518": incremental_gap,
        "oracle_gap_g522_vs_old14_g518": incremental_gap,
        "safe_g522_win_contexts": len(safe_g522_win_contexts),
        "safe_g522_win_budget_pairs": safe_g522_win_pairs,
        "new_g522_win_contexts": len(g522_win_contexts),
        "new_g522_win_budget_pairs": g522_win_pairs,
        "candidate_induced_no_solution_count": induced_count,
        "static_failure_candidate_recovers_count": recovery_count,
        "budget_sensitive_candidate_failure_count": budget_sensitive_failures,
        "finite_pairwise_solution_quality_gain": mean(finite_pairwise_gains),
        "response_surface_budget_stability": budget_stability,
        "per_parameter_importance_linear": {row["parameter"]: row["linear_corr_neg_mean_score"] for row in param_rows},
        "per_parameter_importance_rank": {row["parameter"]: row["rank_corr_oracle_wins"] for row in param_rows},
        "best_param_regions_by_context_bucket": [
            row for row in bucket_region_rows
            if int(finite_number(row.get("safe_g522_win_pairs"), 0)) > 0
        ],
        "dominant_old14_or_g518_controls": dict(Counter(row.get("old14_plus_g518_oracle_candidate", "") for row in oracle_rows).most_common(10)),
        "candidate_win_counts": dict(sorted(candidate_win_counts.items())),
        "region_win_counts": dict(sorted(region_win_counts.items())),
        **G522_CLOSED_CLAIMS,
    }
    write_rows(args.oracle_by_context_csv, oracle_rows)
    write_rows(args.candidate_distribution_csv, distribution)
    write_rows(args.param_importance_csv, param_rows)
    write_rows(args.region_bucket_csv, bucket_region_rows)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.22 Response-Surface Oracle\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- candidate_space_continuation_gate_passed: `{continuation_gate}`\n"
        f"- context_budget_pairs: `{len(oracle_rows)}`\n"
        f"- incremental_oracle_gap_vs_old14_plus_g518: `{csv_number(incremental_gap)}`\n"
        f"- safe_g522_win_contexts: `{len(safe_g522_win_contexts)}`\n"
        f"- safe_g522_win_budget_pairs: `{safe_g522_win_pairs}`\n"
        f"- candidate_induced_no_solution_count: `{induced_count}`\n"
        f"- static_failure_candidate_recovers_count: `{recovery_count}`\n"
        f"- response_surface_budget_stability: `{csv_number(budget_stability)}`\n"
        f"- region_win_counts: `{dict(sorted(region_win_counts.items()))}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "safe_g522_win_contexts": len(safe_g522_win_contexts)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

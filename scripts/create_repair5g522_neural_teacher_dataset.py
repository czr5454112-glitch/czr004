"""Create neural-ready teacher tables from G5.22 response-surface rows."""

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

from repair5g522_common import (  # noqa: E402
    G522_CLOSED_CLAIMS,
    G522_ORACLE_BY_CONTEXT_CSV,
    G522_ORACLE_CANDIDATE_DISTRIBUTION_CSV,
    G522_ORACLE_SUMMARY,
    G522_PROBE_INTEGRITY_SUMMARY,
    G522_PROBE_LOG_DIR,
    G522_PROBE_RESULTS_CSV,
    G522_TEACHER_CANDIDATE_CSV,
    G522_TEACHER_CONTEXT_CSV,
    G522_TEACHER_EDGE_BLOCKER,
    G522_TEACHER_EDGE_CSV,
    G522_TEACHER_MANIFEST,
    G522_TEACHER_PAIRWISE_CSV,
    G522_TEACHER_REPORT,
    G522_TEACHER_SUMMARY,
    STATIC_FLOW_SHIELD_CANDIDATE,
    boolish,
    candidate_params,
    candidate_role,
    context_bucket_lookup,
    csv_number,
    design_rows_by_candidate,
    finite_number,
    g518_retained_candidate_ids,
    leakage_scan,
    mean,
    numeric_candidate_param_dict,
    old14_candidate_ids,
    read_json_file,
    read_jsonl,
    read_rows,
    repo_root,
    row_finite_solution,
    rows_by_context,
    rows_by_context_candidate,
    score,
    selected_g522_candidate_ids,
    write_json_file,
    write_rows,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-csv", type=Path, default=Path(G522_TEACHER_CONTEXT_CSV))
    parser.add_argument("--candidate-csv", type=Path, default=Path(G522_TEACHER_CANDIDATE_CSV))
    parser.add_argument("--pairwise-csv", type=Path, default=Path(G522_TEACHER_PAIRWISE_CSV))
    parser.add_argument("--edge-csv", type=Path, default=Path(G522_TEACHER_EDGE_CSV))
    parser.add_argument("--manifest-json", type=Path, default=Path(G522_TEACHER_MANIFEST))
    parser.add_argument("--report", type=Path, default=Path(G522_TEACHER_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G522_TEACHER_SUMMARY))
    return parser.parse_args(argv)


def best_static(group: list[dict[str, Any]]) -> dict[str, Any] | None:
    finite = [row for row in group if row.get("candidate_id") == STATIC_FLOW_SHIELD_CANDIDATE and row_finite_solution(row)]
    return min(finite, key=score) if finite else None


def best_allowed(group: list[dict[str, Any]], allowed: set[str]) -> dict[str, Any] | None:
    finite = [row for row in group if str(row.get("candidate_id", "")) in allowed and row_finite_solution(row)]
    return min(finite, key=lambda row: (score(row), str(row.get("candidate_id", "")))) if finite else None


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_rows(G522_PROBE_RESULTS_CSV)
    oracle_rows = read_rows(G522_ORACLE_BY_CONTEXT_CSV)
    oracle_summary = read_json_file(G522_ORACLE_SUMMARY)
    integrity = read_json_file(G522_PROBE_INTEGRITY_SUMMARY)
    design = design_rows_by_candidate()
    buckets = context_bucket_lookup()
    old_ids = set(old14_candidate_ids(root))
    g518_ids = set(g518_retained_candidate_ids(limit=8))
    g522_ids = set(selected_g522_candidate_ids(include_probe_only=True))
    old_g518 = old_ids | g518_ids
    by_context = rows_by_context(rows)
    by_context_candidate = rows_by_context_candidate(rows)
    oracle_by_context = {str(row.get("normalized_context_key", "")): row for row in oracle_rows}
    context_table = []
    candidate_table = []
    pairwise_table = []
    for context, group in sorted(by_context.items()):
        first = group[0]
        static = best_static(group)
        old14 = best_allowed(group, old_ids)
        g518 = best_allowed(group, g518_ids)
        old_g518_best = best_allowed(group, old_g518)
        response = best_allowed(group, old_g518 | g522_ids)
        candidate_groups = {cand: values for (ctx, cand), values in by_context_candidate.items() if ctx == context}
        context_candidate_rows = []
        for candidate, crows in sorted(candidate_groups.items()):
            finite_scores = [score(row) for row in crows if row_finite_solution(row)]
            candidate_score = mean(finite_scores)
            static_deltas = [score(row) - score(static) for row in crows if row_finite_solution(row) and row_finite_solution(static)]
            old14_deltas = [score(row) - score(old14) for row in crows if row_finite_solution(row) and row_finite_solution(old14)]
            old_g518_deltas = [score(row) - score(old_g518_best) for row in crows if row_finite_solution(row) and row_finite_solution(old_g518_best)]
            finite_flags = [row_finite_solution(row) for row in crows]
            induced = row_finite_solution(static) and any(not flag for flag in finite_flags)
            recovery = (not row_finite_solution(static)) and any(finite_flags)
            params = numeric_candidate_param_dict(candidate, "feature_candidate_")
            role = candidate_role(candidate, old_ids, g518_ids, set(), g522_ids)
            table_row = {
                "normalized_context_key": context,
                "map": first.get("map", ""),
                "agents": first.get("agents", ""),
                "seed": first.get("seed", ""),
                "iteration": first.get("iteration", ""),
                "traffic_before_hash_full": first.get("traffic_before_hash_full", ""),
                "context_bucket": buckets.get(context, ""),
                "candidate_id": candidate,
                "candidate_role": role,
                "candidate_region": design.get(candidate, {}).get("candidate_region", role),
                "candidate_family": design.get(candidate, {}).get("candidate_family", role),
                "feature_context_agents": finite_number(first.get("agents"), 0.0),
                "feature_context_map_family_hash": float(abs(hash(str(first.get("map", "")).split("-", 1)[0])) % 997) / 997.0,
                "feature_context_static_score": score(static),
                "feature_context_old14_score": score(old14),
                "feature_context_old14_plus_g518_score": score(old_g518_best),
                "feature_context_response_surface_score": score(response),
                "feature_context_cost_span": max([score(row) for row in group if row_finite_solution(row)], default=math.inf) - min([score(row) for row in group if row_finite_solution(row)], default=math.inf),
                "feature_candidate_nearest_g518_distance": finite_number(design.get(candidate, {}).get("nearest_g518_distance"), 0.0),
                "feature_candidate_nearest_old_distance": finite_number(design.get(candidate, {}).get("nearest_old14_distance"), 0.0),
                "feature_interaction_region_bucket_hash": float(abs(hash(f"{buckets.get(context, '')}|{design.get(candidate, {}).get('candidate_region', role)}")) % 997) / 997.0,
                "finite_pairwise_delta_vs_static": csv_number(mean(static_deltas)),
                "finite_pairwise_delta_vs_old14": csv_number(mean(old14_deltas)),
                "finite_pairwise_delta_vs_old14_plus_g518": csv_number(mean(old_g518_deltas)),
                "candidate_induced_no_solution": induced,
                "static_failure_candidate_recovers": recovery,
                "budget_sensitive_candidate_failure": len(set(finite_flags)) > 1,
                "candidate_safe_policy_positive": role == "g522_response_surface" and (mean(old_g518_deltas) <= -0.001 or recovery) and not induced,
                "candidate_oracle_rank": "",
                "candidate_score": csv_number(candidate_score),
                **params,
                **G522_CLOSED_CLAIMS,
            }
            context_candidate_rows.append(table_row)
            candidate_table.append(table_row)
        ranked = sorted(context_candidate_rows, key=lambda row: (finite_number(row.get("candidate_score"), math.inf), str(row.get("candidate_id", ""))))
        for index, row in enumerate(ranked):
            row["candidate_oracle_rank"] = index + 1
        safe_g522 = [row for row in ranked if boolish(row.get("candidate_safe_policy_positive"))]
        context_table.append(
            {
                "normalized_context_key": context,
                "map": first.get("map", ""),
                "map_family": str(first.get("map", "")).split("-", 1)[0],
                "agents": first.get("agents", ""),
                "seed": first.get("seed", ""),
                "iteration": first.get("iteration", ""),
                "traffic_before_hash_full": first.get("traffic_before_hash_full", ""),
                "context_bucket": buckets.get(context, ""),
                "feature_agent_count": finite_number(first.get("agents"), 0.0),
                "feature_static_score": score(static),
                "feature_old14_oracle_score": score(old14),
                "feature_g518_oracle_score": score(g518),
                "feature_response_surface_oracle_score": score(response),
                "feature_progress_wait_block_proxy": finite_number(first.get("agents"), 0.0) / max(1.0, len(group)),
                "static_no_solution_status": not row_finite_solution(static),
                "old14_oracle_summary": (old14 or {}).get("candidate_id", ""),
                "g518_oracle_summary": (g518 or {}).get("candidate_id", ""),
                "response_surface_oracle_summary": (response or {}).get("candidate_id", ""),
                "context_has_safe_param_gain": bool(safe_g522),
                "context_has_static_recovery": any(boolish(row.get("static_failure_candidate_recovers")) for row in ranked),
                "context_has_candidate_induced_failure_boundary": any(boolish(row.get("candidate_induced_no_solution")) for row in ranked),
                "context_response_surface_entropy": len({row.get("candidate_region", "") for row in ranked[:5]}) / 5.0 if ranked else 0.0,
                "best_safe_param_vector": (safe_g522[0] if safe_g522 else (ranked[0] if ranked else {})).get("candidate_id", ""),
                "best_safe_param_family": (safe_g522[0] if safe_g522 else (ranked[0] if ranked else {})).get("candidate_family", ""),
                "best_safe_delta_vs_old14_g518": (safe_g522[0] if safe_g522 else (ranked[0] if ranked else {})).get("finite_pairwise_delta_vs_old14_plus_g518", ""),
                "fallback_recommended": not bool(safe_g522),
                **G522_CLOSED_CLAIMS,
            }
        )
        capped = [row for row in ranked[:12] if row.get("candidate_role") in {"old14", "g518_retained", "g522_response_surface"}]
        for i, left in enumerate(capped):
            for right in capped[i + 1 : min(i + 7, len(capped))]:
                lscore = finite_number(left.get("candidate_score"), math.inf)
                rscore = finite_number(right.get("candidate_score"), math.inf)
                pairwise_table.append(
                    {
                        "normalized_context_key": context,
                        "candidate_i": left.get("candidate_id", ""),
                        "candidate_j": right.get("candidate_id", ""),
                        "candidate_i_preferred_over_j": lscore < rscore,
                        "preference_margin": csv_number(rscore - lscore),
                        "both_safe": boolish(left.get("candidate_safe_policy_positive")) and boolish(right.get("candidate_safe_policy_positive")),
                        "i_safe_j_unsafe": boolish(left.get("candidate_safe_policy_positive")) and not boolish(right.get("candidate_safe_policy_positive")),
                        **G522_CLOSED_CLAIMS,
                    }
                )

    checkpoint_jsonl = Path(str(integrity.get("checkpoint_jsonl", "")))
    if not checkpoint_jsonl.is_absolute():
        checkpoint_jsonl = repo_root() / checkpoint_jsonl
    edge_rows = []
    if checkpoint_jsonl.exists():
        for row in read_jsonl(checkpoint_jsonl):
            context = str(row.get("traffic_before_hash_full", "") or f"{row.get('map')}|{row.get('agents')}|{row.get('seed')}|{row.get('iteration')}")
            for edge in row.get("traffic_after_edges", [])[:64]:
                beta = 0.35
                edge_rows.append(
                    {
                        "checkpoint_context_proxy": context,
                        "map": row.get("map", ""),
                        "agents": row.get("agents", ""),
                        "seed": row.get("seed", ""),
                        "iteration": row.get("iteration", ""),
                        "edge_from_id": edge.get("from_id", ""),
                        "edge_to_id": edge.get("to_id", ""),
                        "traffic_c_raw": edge.get("c_raw", ""),
                        "traffic_f_raw": edge.get("f_raw", ""),
                        "traffic_c_weight": edge.get("c_weight", ""),
                        "traffic_f_weight": edge.get("f_weight", ""),
                        "ltm_additive_update_proxy": edge.get("c_weight", ""),
                        "oracle_safe_parameterized_update_proxy": csv_number(finite_number(edge.get("c_weight"), 0.0) - beta * finite_number(edge.get("f_weight"), 0.0)),
                        "residual_target": csv_number(-beta * finite_number(edge.get("f_weight"), 0.0)),
                        **G522_CLOSED_CLAIMS,
                    }
                )
    if not edge_rows:
        write_text_file(G522_TEACHER_EDGE_BLOCKER, "# Repair5G.5.22 Edge/Update Teacher Blocker\n\n- blocker: `edge_update_teacher_unavailable_missing_checkpoint_fields`\n")

    features = sorted({key for row in candidate_table + context_table for key in row if key.startswith("feature_")})
    leak = leakage_scan(features)
    safe_positive = sum(1 for row in candidate_table if boolish(row.get("candidate_safe_policy_positive")))
    induced = sum(1 for row in candidate_table if boolish(row.get("candidate_induced_no_solution")))
    recovery = sum(1 for row in candidate_table if boolish(row.get("static_failure_candidate_recovers")))
    source_label = "targeted_response_surface_only"
    summary = {
        "schema_version": "phase5p5_repair5g522_neural_teacher_dataset_summary_v1",
        "decision": "neural_teacher_dataset_created",
        "context_rows": len(context_table),
        "candidate_rows": len(candidate_table),
        "pairwise_rows": len(pairwise_table),
        "edge_update_rows_or_blocker": len(edge_rows) if edge_rows else "edge_update_teacher_unavailable_missing_checkpoint_fields",
        "safe_positive_candidate_rows": safe_positive,
        "candidate_induced_failure_rows": induced,
        "static_recovery_rows": recovery,
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "train_dev_split_metadata": {"split": "seed_oof_plus_fixed_seed_order", "source": source_label},
        "source_label": source_label,
        "source_probe_rows": integrity.get("probe_rows", ""),
        "response_surface_rows_gt_g521_targeted": int(finite_number(integrity.get("probe_rows"), 0)) > 1596,
        "oracle_incremental_gap": oracle_summary.get("incremental_oracle_gap_vs_old14_plus_g518", ""),
        **G522_CLOSED_CLAIMS,
    }
    manifest = {
        **summary,
        "tables": {
            "context_teacher_table": str(args.context_csv),
            "candidate_teacher_table": str(args.candidate_csv),
            "pairwise_preference_table": str(args.pairwise_csv),
            "edge_update_teacher_table": str(args.edge_csv) if edge_rows else "",
        },
        "source_probe_results": G522_PROBE_RESULTS_CSV,
        "source_oracle_by_context": G522_ORACLE_BY_CONTEXT_CSV,
        **G522_CLOSED_CLAIMS,
    }
    write_rows(args.context_csv, context_table)
    write_rows(args.candidate_csv, candidate_table)
    write_rows(args.pairwise_csv, pairwise_table)
    write_rows(args.edge_csv, edge_rows)
    write_json_file(args.summary_json, summary)
    write_json_file(args.manifest_json, manifest)
    write_text_file(
        args.report,
        "# Repair5G.5.22 Neural Teacher Dataset\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- context_rows: `{len(context_table)}`\n"
        f"- candidate_rows: `{len(candidate_table)}`\n"
        f"- pairwise_rows: `{len(pairwise_table)}`\n"
        f"- edge_update_rows_or_blocker: `{summary['edge_update_rows_or_blocker']}`\n"
        f"- safe_positive_candidate_rows: `{safe_positive}`\n"
        f"- candidate_induced_failure_rows: `{induced}`\n"
        f"- static_recovery_rows: `{recovery}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- source_label: `{source_label}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "candidate_rows": len(candidate_table), "pairwise_rows": len(pairwise_table)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

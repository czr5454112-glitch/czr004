"""Analyze G5.22 response-surface signal and generalization."""

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
    G522_CLOSED_CLAIMS,
    G522_ORACLE_PARAM_IMPORTANCE_CSV,
    G522_ORACLE_REGION_BUCKET_CSV,
    G522_ORACLE_SUMMARY,
    G522_SIGNAL_BUCKET_PERF_CSV,
    G522_SIGNAL_HEATMAP_CSV,
    G522_SIGNAL_MEMORIZATION_CSV,
    G522_SIGNAL_PARAM_IMPORTANCE_CSV,
    G522_SIGNAL_REPORT,
    G522_SIGNAL_RISK_CALIBRATION_CSV,
    G522_SIGNAL_SUMMARY,
    G522_SURROGATE_CALIBRATION_CSV,
    G522_SURROGATE_CONTEXT_DECISIONS_CSV,
    G522_SURROGATE_SUMMARY,
    G522_TEACHER_CANDIDATE_CSV,
    G522_TEACHER_SUMMARY,
    boolish,
    csv_number,
    finite_number,
    mean,
    parameter_names,
    read_json_file,
    read_rows,
    write_json_file,
    write_rows,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--param-importance-csv", type=Path, default=Path(G522_SIGNAL_PARAM_IMPORTANCE_CSV))
    parser.add_argument("--bucket-performance-csv", type=Path, default=Path(G522_SIGNAL_BUCKET_PERF_CSV))
    parser.add_argument("--risk-calibration-csv", type=Path, default=Path(G522_SIGNAL_RISK_CALIBRATION_CSV))
    parser.add_argument("--memorization-csv", type=Path, default=Path(G522_SIGNAL_MEMORIZATION_CSV))
    parser.add_argument("--heatmap-csv", type=Path, default=Path(G522_SIGNAL_HEATMAP_CSV))
    parser.add_argument("--report", type=Path, default=Path(G522_SIGNAL_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G522_SIGNAL_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    oracle = read_json_file(G522_ORACLE_SUMMARY)
    teacher = read_json_file(G522_TEACHER_SUMMARY)
    surrogate = read_json_file(G522_SURROGATE_SUMMARY)
    candidates = read_rows(G522_TEACHER_CANDIDATE_CSV)
    oracle_params = read_rows(G522_ORACLE_PARAM_IMPORTANCE_CSV)
    region_buckets = read_rows(G522_ORACLE_REGION_BUCKET_CSV)
    decisions = read_rows(G522_SURROGATE_CONTEXT_DECISIONS_CSV)
    calibration = read_rows(G522_SURROGATE_CALIBRATION_CSV)

    param_rows = []
    for row in oracle_params:
        param_rows.append(
            {
                "parameter": row.get("parameter", ""),
                "global_linear_corr_neg_mean_score": row.get("linear_corr_neg_mean_score", ""),
                "global_rank_corr_oracle_wins": row.get("rank_corr_oracle_wins", ""),
                "interpretation": "higher signal" if abs(finite_number(row.get("rank_corr_oracle_wins"), 0.0)) >= 0.10 else "weak/noisy",
                **G522_CLOSED_CLAIMS,
            }
        )

    bucket_rows = []
    for row in region_buckets:
        bucket_rows.append(
            {
                "context_bucket": row.get("context_bucket", ""),
                "candidate_region": row.get("candidate_region", ""),
                "context_budget_pairs": row.get("context_budget_pairs", ""),
                "safe_g522_win_pairs": row.get("safe_g522_win_pairs", ""),
                "mean_incremental_gap_vs_old14_plus_g518": row.get("mean_incremental_gap_vs_old14_plus_g518", ""),
                "static_recovery_learnable_proxy": boolish(row.get("safe_g522_win_pairs")) and "recovery" in str(row.get("context_bucket", "")),
                **G522_CLOSED_CLAIMS,
            }
        )

    risk_rows = []
    for row in calibration:
        risk_rows.append(
            {
                "model": row.get("model", ""),
                "risk_bucket_low": row.get("risk_bucket_low", ""),
                "risk_bucket_high": row.get("risk_bucket_high", ""),
                "contexts": row.get("contexts", ""),
                "mean_predicted_avoidable_risk": row.get("mean_predicted_avoidable_risk", ""),
                "actual_avoidable_risk_rate": row.get("actual_avoidable_risk_rate", ""),
                "ece_abs_error": row.get("ece_abs_error", ""),
                **G522_CLOSED_CLAIMS,
            }
        )

    by_nearest = defaultdict(list)
    for row in candidates:
        if row.get("candidate_role") != "g522_response_surface":
            continue
        dist = finite_number(row.get("feature_candidate_nearest_g518_distance"), math.inf)
        bucket = "near_g518" if dist <= 0.18 else "mid_g518" if dist <= 0.45 else "far_g518"
        by_nearest[bucket].append(row)
    memorization_rows = []
    for bucket, rows in sorted(by_nearest.items()):
        memorization_rows.append(
            {
                "nearest_g518_bucket": bucket,
                "candidate_rows": len(rows),
                "safe_positive_rows": sum(1 for row in rows if boolish(row.get("candidate_safe_policy_positive"))),
                "candidate_induced_failure_rows": sum(1 for row in rows if boolish(row.get("candidate_induced_no_solution"))),
                "mean_delta_vs_old14_plus_g518": csv_number(mean([finite_number(row.get("finite_pairwise_delta_vs_old14_plus_g518"), math.inf) for row in rows])),
                **G522_CLOSED_CLAIMS,
            }
        )

    heatmap_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        if row.get("candidate_role") != "g522_response_surface":
            continue
        beta = finite_number(row.get("feature_candidate_flow_shield_beta"), 0.0)
        blocked = finite_number(row.get("feature_candidate_alpha_cong_blocked"), 0.0)
        beta_bin = "beta_low" if beta < 0.40 else "beta_mid" if beta < 0.60 else "beta_high"
        block_bin = "block_low" if blocked < 1.30 else "block_mid" if blocked < 1.55 else "block_high"
        heatmap_groups[(str(row.get("context_bucket", "")), beta_bin, block_bin)].append(row)
    heatmap_rows = []
    for (bucket, beta_bin, block_bin), rows in sorted(heatmap_groups.items()):
        heatmap_rows.append(
            {
                "context_bucket": bucket,
                "beta_bin": beta_bin,
                "blocked_bin": block_bin,
                "rows": len(rows),
                "safe_positive_rate": sum(1 for row in rows if boolish(row.get("candidate_safe_policy_positive"))) / len(rows),
                "induced_failure_rate": sum(1 for row in rows if boolish(row.get("candidate_induced_no_solution"))) / len(rows),
                "mean_delta_vs_old14_plus_g518": csv_number(mean([finite_number(row.get("finite_pairwise_delta_vs_old14_plus_g518"), math.inf) for row in rows])),
                **G522_CLOSED_CLAIMS,
            }
        )

    family_perf: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in decisions:
        if row.get("eval_scope") == "leave_one_map_family":
            family_perf[str(row.get("fold_id", ""))].append(row)
    collapse_families = [
        family for family, rows in family_perf.items()
        if rows and mean([1.0 if boolish(row.get("top3_contains_safe_oracle")) else 0.0 for row in rows]) < 0.15
    ]
    best_model = surrogate.get("best_model_summary", {})
    source_blind = [
        row for row in read_rows("outputs/tables/phase5p5_repair5g522_neural_ready_surrogate_eval.csv")
        if row.get("row_type") == "model_aggregate" and row.get("model") == "source_blind_ablation"
    ]
    source_blind_matches = bool(source_blind) and finite_number(source_blind[0].get("safe_policy_sim_utility"), math.inf) <= finite_number(best_model.get("safe_policy_sim_utility"), math.inf)
    nearest_memorization_only = bool(memorization_rows) and max(finite_number(row.get("safe_positive_rows"), 0) for row in memorization_rows) == finite_number(next((row for row in memorization_rows if row.get("nearest_g518_bucket") == "near_g518"), {}).get("safe_positive_rows"), 0)
    smooth_signal = (
        len(heatmap_rows) > 0
        and any(finite_number(row.get("safe_positive_rate"), 0.0) > 0.0 for row in heatmap_rows)
        and boolish(teacher.get("response_surface_rows_gt_g521_targeted"))
    )
    next_data = [
        "expand static-recovery contexts if recovery positives remain sparse",
        "add more far-from-G5.18 fractional coverage if nearest-G5.18 memorization dominates",
        "keep counterfactual checkpoint edge fields for residual/mixture learning",
        "do not move to runtime until offline controls and heldout family behavior are clean",
    ]
    summary = {
        "schema_version": "phase5p5_repair5g522_signal_and_generalization_summary_v1",
        "decision": "signal_and_generalization_autopsy_completed",
        "response_surface_signal_smooth_enough_to_learn": smooth_signal,
        "static_recovery_cases_learnable": int(finite_number(oracle.get("static_failure_candidate_recovers_count"), 0)) > 0,
        "candidate_induced_failures_predictable": finite_number(best_model.get("avoidable_risk_ece"), math.inf) <= 0.25,
        "leave_one_map_family_collapse_count": len(collapse_families),
        "leave_one_map_family_collapse_families": collapse_families,
        "source_blind_control_matches_model": source_blind_matches,
        "remaining_signal_just_nearest_g518_memorization": nearest_memorization_only,
        "candidate_rows": teacher.get("candidate_rows", ""),
        "source_probe_rows": teacher.get("source_probe_rows", ""),
        "safe_positive_candidate_rows": teacher.get("safe_positive_candidate_rows", ""),
        "candidate_induced_failure_rows": teacher.get("candidate_induced_failure_rows", ""),
        "static_recovery_rows": teacher.get("static_recovery_rows", ""),
        "best_model": surrogate.get("best_model", ""),
        "next_data_recommendation": next_data,
        **G522_CLOSED_CLAIMS,
    }
    write_rows(args.param_importance_csv, param_rows)
    write_rows(args.bucket_performance_csv, bucket_rows)
    write_rows(args.risk_calibration_csv, risk_rows)
    write_rows(args.memorization_csv, memorization_rows)
    write_rows(args.heatmap_csv, heatmap_rows)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.22 Signal and Generalization Autopsy\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- response_surface_signal_smooth_enough_to_learn: `{smooth_signal}`\n"
        f"- static_recovery_cases_learnable: `{summary['static_recovery_cases_learnable']}`\n"
        f"- candidate_induced_failures_predictable: `{summary['candidate_induced_failures_predictable']}`\n"
        f"- leave_one_map_family_collapse_count: `{len(collapse_families)}`\n"
        f"- source_blind_control_matches_model: `{source_blind_matches}`\n"
        f"- remaining_signal_just_nearest_g518_memorization: `{nearest_memorization_only}`\n"
        f"- next_data_recommendation: `{next_data}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "smooth_signal": smooth_signal}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

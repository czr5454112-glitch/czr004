"""Analyze Repair5G.5.4 same-context counterfactual UpdateLTM labels."""

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

from repair5g3_common import read_jsonl, repo_root, resolve, write_csv_rows  # noqa: E402
from repair5g54_common import G54_CANDIDATES, G54_FORBIDDEN_LABEL_FIELDS, boolish, load_json, score_from_label, validate_observed_instance_ids, write_json, write_text  # noqa: E402


DEFAULT_PROBES = "outputs/logs/phase5p5_repair5g54_counterfactual_probe/phase5p5_repair5g54_counterfactual_update_probes.jsonl"
DEFAULT_REPLAY_SUMMARY = "outputs/reports/phase5p5_repair5g54_checkpoint_replayability_summary.json"
DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g54_counterfactual_update_labels.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g54_counterfactual_oracle_by_context.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g54_counterfactual_label_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g54_counterfactual_label_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-jsonl", type=Path, default=Path(DEFAULT_PROBES))
    parser.add_argument("--replayability-summary-json", type=Path, default=Path(DEFAULT_REPLAY_SUMMARY))
    parser.add_argument("--labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--oracle-csv", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def label_csv_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "context_id": row.get("context_id", ""),
                "map": row.get("map", ""),
                "agents": row.get("agents", ""),
                "seed": row.get("seed", ""),
                "iteration": row.get("iteration", ""),
                "candidate_id": row.get("candidate_id", ""),
                "resolved_candidate_id": row.get("resolved_candidate_id", ""),
                "updateparams_hash": row.get("updateparams_hash", ""),
                "updateparams_fingerprint": row.get("updateparams_fingerprint", ""),
                "probe_solution_found": row.get("probe_solution_found", ""),
                "probe_feasible": row.get("probe_feasible", ""),
                "probe_sum_of_loss": row.get("probe_sum_of_loss", ""),
                "probe_lower_bound": row.get("probe_lower_bound", ""),
                "probe_sum_of_loss_ratio": row.get("probe_sum_of_loss_ratio", ""),
                "probe_runtime_ms": row.get("probe_runtime_ms", ""),
                "probe_expanded_nodes": row.get("probe_expanded_nodes", ""),
                "probe_low_level_pibt_calls": row.get("probe_low_level_pibt_calls", ""),
                "delta_vs_additive_in_same_context": row.get("delta_vs_additive_in_same_context", ""),
                "delta_vs_static_in_same_context": row.get("delta_vs_static_in_same_context", ""),
                "is_best_candidate_in_context": row.get("is_best_candidate_in_context", ""),
                "oracle_gap_vs_static": row.get("oracle_gap_vs_static", ""),
                "traffic_before_hash_full": row.get("traffic_before_hash_full", ""),
                "trace_event_count": row.get("trace_event_count", ""),
                "feature_leakage_safe": row.get("forbidden_feature_audit_passed", True),
            }
        )
    return out


def oracle_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_context: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_context[str(row.get("context_id", ""))].append(row)
    out: list[dict[str, Any]] = []
    required = set(G54_CANDIDATES)
    for context_id, context_rows in sorted(by_context.items()):
        seen = {str(row.get("candidate_id", "")) for row in context_rows}
        scored = [(score_from_label(row), row) for row in context_rows]
        finite = [(score, row) for score, row in scored if math.isfinite(score)]
        best_score, best_row = min(finite, key=lambda item: item[0]) if finite else (math.inf, {})
        static = next((row for row in context_rows if row.get("candidate_id") == "repair5g2_best_frozen_static_candidate"), {})
        static_score = score_from_label(static) if static else math.inf
        oracle_gap = best_score - static_score if math.isfinite(best_score) and math.isfinite(static_score) else math.nan
        out.append(
            {
                "context_id": context_id,
                "map": context_rows[0].get("map", ""),
                "agents": context_rows[0].get("agents", ""),
                "seed": context_rows[0].get("seed", ""),
                "iteration": context_rows[0].get("iteration", ""),
                "candidate_coverage_complete": required <= seen,
                "candidate_count": len(seen),
                "oracle_candidate_id": best_row.get("candidate_id", ""),
                "oracle_resolved_candidate_id": best_row.get("resolved_candidate_id", ""),
                "oracle_score": best_score if math.isfinite(best_score) else "",
                "static_score": static_score if math.isfinite(static_score) else "",
                "oracle_gap_over_static": oracle_gap if math.isfinite(oracle_gap) else "",
                "static_dominates_context": bool(math.isfinite(oracle_gap) and oracle_gap >= -1.0e-12),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    replay_summary = load_json(resolve(args.replayability_summary_json, root))
    replay_ok = bool(replay_summary.get("gates", {}).get("checkpoint_replayability_passed"))
    rows = read_jsonl(resolve(args.probe_jsonl, root))
    labels = label_csv_rows(rows)
    oracle = oracle_rows(rows)
    write_csv_rows(resolve(args.labels_csv, root), labels)
    write_csv_rows(resolve(args.oracle_csv, root), oracle)
    contexts = {row.get("context_id", "") for row in rows if row.get("context_id")}
    seeds = [int(row.get("seed", 0)) for row in rows]
    observed_ids_only = True
    try:
        validate_observed_instance_ids(seeds)
    except SystemExit:
        observed_ids_only = False
    required = set(G54_CANDIDATES)
    coverage_complete = bool(contexts) and all(
        required <= {str(row.get("candidate_id", "")) for row in rows if row.get("context_id") == context}
        for context in contexts
    )
    forbidden_fields_seen = sorted(set().union(*(set(row) & G54_FORBIDDEN_LABEL_FIELDS for row in rows)) if rows else set())
    oracle_gap_measured = any(str(row.get("oracle_gap_over_static", "")) not in {"", "nan", "None"} for row in oracle)
    non_static_wins = sum(
        1
        for row in oracle
        if row.get("oracle_candidate_id") not in {"", "repair5g2_best_frozen_static_candidate"}
    )
    static_dominates_all = bool(oracle) and all(boolish(row.get("static_dominates_context")) for row in oracle)
    gates = {
        "counterfactual_context_count_gt_0": len(contexts) > 0,
        "label_rows_gt_0": len(rows) > 0,
        "candidate_coverage_complete": coverage_complete,
        "same_context_labels_exist_for_all_candidates": coverage_complete,
        "observed_ids_only": observed_ids_only,
        "ids_166_205_untouched": observed_ids_only,
        "no_final_full_run_label_leakage": not forbidden_fields_seen,
        "runtime_feature_availability_audit_passes": replay_ok and all(boolish(row.get("forbidden_feature_audit_passed", True)) for row in rows),
        "oracle_gap_over_static_measured": oracle_gap_measured,
        "adaptive_or_static_dominance_reported": non_static_wins > 0 or static_dominates_all,
    }
    gates["counterfactual_labels_passed"] = all(gates.values())
    summary = {
        "schema_version": "phase5p5_repair5g54_counterfactual_label_summary_v1",
        "context_count": len(contexts),
        "label_rows": len(rows),
        "candidate_count": len(required),
        "oracle_rows": len(oracle),
        "non_static_oracle_win_contexts": non_static_wins,
        "static_dominates_all_contexts": static_dominates_all,
        "forbidden_fields_seen": forbidden_fields_seen,
        "labels_csv": str(resolve(args.labels_csv, root)),
        "oracle_csv": str(resolve(args.oracle_csv, root)),
        "gates": gates,
        "decision": "counterfactual_labels_available" if gates["counterfactual_labels_passed"] else "counterfactual_labels_unavailable",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.4 Counterfactual UpdateLTM Labels\n\n"
        f"- context_count: `{len(contexts)}`\n"
        f"- label_rows: `{len(rows)}`\n"
        f"- candidate_coverage_complete: `{coverage_complete}`\n"
        f"- oracle_gap_over_static_measured: `{oracle_gap_measured}`\n"
        f"- non_static_oracle_win_contexts: `{non_static_wins}`\n"
        f"- static_dominates_all_contexts: `{static_dominates_all}`\n"
        f"- counterfactual_labels_passed: `{gates['counterfactual_labels_passed']}`\n"
        f"- decision: `{summary['decision']}`\n\n"
        "No labels are inferred from final full-run outcomes.\n",
    )
    print(json.dumps({"counterfactual_labels_passed": gates["counterfactual_labels_passed"], "label_rows": len(rows)}))
    return 0 if gates["counterfactual_labels_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

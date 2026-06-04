"""Analyze Repair5G.5.5 scaled same-context counterfactual labels."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g54_common import G54_ALLOWED_RUNTIME_FEATURES, G54_FORBIDDEN_LABEL_FIELDS, boolish  # noqa: E402
from repair5g55_common import (  # noqa: E402
    G55_AGENT_COUNTS,
    G55_BASE_CANDIDATES,
    G55_CONTEXT_MINIMUM_SMOKE,
    G55_CONTEXT_TARGET,
    G55_MAPS,
    context_rows_from_labels,
    group_by_context,
    load_checkpoint_features,
    oracle_rows_from_labels,
    read_jsonl,
    repo_root,
    resolve,
    validate_g55_instance_ids,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_PROBES = "outputs/logs/phase5p5_repair5g55_scaled_counterfactual_labels/phase5p5_repair5g55_counterfactual_update_probes.jsonl"
DEFAULT_CHECKPOINTS = "outputs/logs/phase5p5_repair5g55_scaled_counterfactual_labels/phase5p5_repair5g55_update_checkpoints.jsonl"
DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g55_counterfactual_update_labels.csv"
DEFAULT_CONTEXTS = "outputs/tables/phase5p5_repair5g55_counterfactual_contexts.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g55_oracle_by_context.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g55_counterfactual_label_quality.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g55_counterfactual_label_quality_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-jsonl", type=Path, default=Path(DEFAULT_PROBES))
    parser.add_argument("--checkpoint-jsonl", type=Path, default=Path(DEFAULT_CHECKPOINTS))
    parser.add_argument("--labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--contexts-csv", type=Path, default=Path(DEFAULT_CONTEXTS))
    parser.add_argument("--oracle-csv", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--expected-maps", nargs="+", default=G55_MAPS)
    parser.add_argument("--expected-agent-counts", nargs="+", type=int, default=G55_AGENT_COUNTS)
    parser.add_argument("--expected-candidates", default=",".join(G55_BASE_CANDIDATES))
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
                "candidate_recognized": row.get("candidate_recognized", ""),
                "updateparams_hash": row.get("updateparams_hash", ""),
                "updateparams_fingerprint": row.get("updateparams_fingerprint", ""),
                "short_budget_ms": row.get("short_budget_ms", ""),
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


def checkpoint_replayability_gates(checkpoints: list[dict[str, Any]]) -> dict[str, Any]:
    forbidden = sorted(set().union(*(set(row) & G54_FORBIDDEN_LABEL_FIELDS for row in checkpoints)) if checkpoints else set())
    feature_names = {name for row in checkpoints for name in row.get("feature_names", [])}
    unexpected = sorted(str(name) for name in feature_names if str(name) not in G54_ALLOWED_RUNTIME_FEATURES)
    return {
        "checkpoint_rows_gt_0": len(checkpoints) > 0,
        "checkpoint_replayability_still_passes": bool(checkpoints)
        and all(boolish(row.get("replayed_traffic_after_hash_match", True)) for row in checkpoints)
        and all(boolish(row.get("replayed_update_stats_match", True)) for row in checkpoints),
        "checkpoint_no_forbidden_fields": not forbidden,
        "checkpoint_forbidden_fields_seen": forbidden,
        "runtime_feature_names_present": bool(feature_names),
        "runtime_feature_availability_audit_passes": bool(feature_names) and not unexpected,
        "unexpected_runtime_features": unexpected,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    expected_candidates = [token for token in str(args.expected_candidates).split(",") if token]
    probe_rows = read_jsonl(resolve(args.probe_jsonl, root))
    checkpoint_rows = read_jsonl(resolve(args.checkpoint_jsonl, root))
    labels = label_csv_rows(probe_rows)
    oracle = oracle_rows_from_labels(labels, expected_candidates)
    checkpoint_features = load_checkpoint_features(resolve(args.checkpoint_jsonl, root))
    contexts = context_rows_from_labels(labels, oracle, checkpoint_features)
    write_csv_rows(resolve(args.labels_csv, root), labels)
    write_csv_rows(resolve(args.oracle_csv, root), oracle)
    write_csv_rows(resolve(args.contexts_csv, root), contexts)

    by_context = group_by_context(labels)
    context_count = len(by_context)
    label_rows = len(labels)
    expected_label_rows = context_count * len(expected_candidates)
    seeds = [int(row.get("seed", 0)) for row in labels]
    observed_ids_only = True
    try:
        validate_g55_instance_ids(seeds, label="Repair5G.5.5 label rows")
    except SystemExit:
        observed_ids_only = False
    expected_groups = {(str(map_name), int(agents)) for map_name in args.expected_maps for agents in args.expected_agent_counts}
    actual_groups = {(str(row.get("map", "")), int(float(row.get("agents") or 0))) for row in contexts}
    missing_groups = sorted(expected_groups - actual_groups)
    required = set(expected_candidates)
    coverage_complete = bool(by_context) and all(
        required <= {str(row.get("candidate_id", "")) for row in rows}
        for rows in by_context.values()
    )
    same_context_ok = bool(by_context) and all(
        len({(row.get("map"), row.get("agents"), row.get("seed"), row.get("iteration"), row.get("traffic_before_hash_full")) for row in rows}) == 1
        for rows in by_context.values()
    )
    nonzero_trace_contexts = sum(1 for row in contexts if float(row.get("trace_event_count") or 0.0) > 0.0)
    nonzero_trace_fraction = nonzero_trace_contexts / context_count if context_count else 0.0
    forbidden_fields_seen = sorted(set().union(*(set(row) & G54_FORBIDDEN_LABEL_FIELDS for row in probe_rows)) if probe_rows else set())
    checkpoint_gates = checkpoint_replayability_gates(checkpoint_rows)
    gates = {
        "observed_ids_only": observed_ids_only,
        "ids_166_205_untouched": observed_ids_only,
        "context_count": context_count,
        "context_count_ge_60_minimum_smoke": context_count >= G55_CONTEXT_MINIMUM_SMOKE,
        "context_count_ge_120_target": context_count >= G55_CONTEXT_TARGET,
        "label_rows": label_rows,
        "label_rows_equal_context_count_times_candidate_count": label_rows == expected_label_rows and context_count > 0,
        "candidate_coverage_complete": coverage_complete,
        "same_context_labels_exist_for_all_candidates": coverage_complete and same_context_ok,
        "feature_leakage_audit_passes": not forbidden_fields_seen and all(boolish(row.get("feature_leakage_safe", True)) for row in labels),
        "runtime_feature_availability_audit_passes": checkpoint_gates["runtime_feature_availability_audit_passes"],
        "no_final_full_run_label_leakage": not forbidden_fields_seen,
        "map_agent_coverage_complete": not missing_groups,
        "missing_map_agent_groups": missing_groups,
        "nonzero_trace_context_fraction": nonzero_trace_fraction,
        "nonzero_trace_context_fraction_gt_0": nonzero_trace_fraction > 0.0,
        **checkpoint_gates,
    }
    gates["scaled_counterfactual_label_smoke_passed"] = all(
        bool(gates[key])
        for key in [
            "observed_ids_only",
            "context_count_ge_60_minimum_smoke",
            "label_rows_equal_context_count_times_candidate_count",
            "candidate_coverage_complete",
            "same_context_labels_exist_for_all_candidates",
            "feature_leakage_audit_passes",
            "runtime_feature_availability_audit_passes",
            "no_final_full_run_label_leakage",
            "map_agent_coverage_complete",
            "nonzero_trace_context_fraction_gt_0",
            "checkpoint_replayability_still_passes",
        ]
    )
    gates["scaled_counterfactual_label_target_passed"] = gates["scaled_counterfactual_label_smoke_passed"] and gates["context_count_ge_120_target"]
    oracle_beats_static = sum(1 for row in oracle if boolish(row.get("oracle_beats_static")))
    oracle_beats_additive = sum(1 for row in oracle if boolish(row.get("oracle_beats_additive")))
    gaps = [
        float(row["oracle_gap_over_static"])
        for row in oracle
        if str(row.get("oracle_gap_over_static", "")) not in {"", "nan", "None"}
        and math.isfinite(float(row["oracle_gap_over_static"]))
    ]
    summary = {
        "schema_version": "phase5p5_repair5g55_counterfactual_label_quality_summary_v1",
        "context_count": context_count,
        "label_rows": label_rows,
        "candidate_count": len(expected_candidates),
        "checkpoint_rows": len(checkpoint_rows),
        "oracle_rows": len(oracle),
        "oracle_beats_static_contexts": oracle_beats_static,
        "oracle_beats_static_fraction": oracle_beats_static / len(oracle) if oracle else 0.0,
        "oracle_beats_additive_contexts": oracle_beats_additive,
        "mean_oracle_gap_over_static": sum(gaps) / len(gaps) if gaps else None,
        "labels_csv": str(resolve(args.labels_csv, root)),
        "contexts_csv": str(resolve(args.contexts_csv, root)),
        "oracle_csv": str(resolve(args.oracle_csv, root)),
        "gates": gates,
        "decision": "scaled_labels_smoke_passed" if gates["scaled_counterfactual_label_smoke_passed"] else "scaled_labels_failed",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "g6_training_allowed": False,
        "learned_runtime_fresh_holdout": "blocked_not_run",
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.5 Counterfactual Label Quality\n\n"
        f"- context_count: `{context_count}`\n"
        f"- label_rows: `{label_rows}`\n"
        f"- candidate_count: `{len(expected_candidates)}`\n"
        f"- map_agent_coverage_complete: `{gates['map_agent_coverage_complete']}`\n"
        f"- candidate_coverage_complete: `{coverage_complete}`\n"
        f"- checkpoint_replayability_still_passes: `{gates['checkpoint_replayability_still_passes']}`\n"
        f"- scaled_counterfactual_label_smoke_passed: `{gates['scaled_counterfactual_label_smoke_passed']}`\n"
        f"- scaled_counterfactual_label_target_passed: `{gates['scaled_counterfactual_label_target_passed']}`\n"
        f"- oracle_beats_static_fraction: `{summary['oracle_beats_static_fraction']}`\n"
        f"- decision: `{summary['decision']}`\n\n"
        "Labels are same-context short-probe diagnostics only. Final full-run outcomes are not used as per-update labels, and G6 training remains blocked.\n",
    )
    print(json.dumps({"scaled_counterfactual_label_smoke_passed": gates["scaled_counterfactual_label_smoke_passed"], "context_count": context_count}))
    return 0 if gates["scaled_counterfactual_label_smoke_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

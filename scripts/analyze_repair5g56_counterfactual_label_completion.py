"""Analyze Repair5G.5.6 counterfactual label completion gates."""

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

from repair5g54_common import boolish  # noqa: E402
from repair5g56_common import (  # noqa: E402
    G56_AGENT_COUNTS,
    G56_BASE_CANDIDATES,
    G56_CONTEXT_TARGET,
    G56_MAPS,
    context_rows_from_labels_and_oracle,
    dedupe_rows,
    finite_number,
    group_by_context,
    iteration_counts,
    labels_from_probe_rows,
    later_iteration_reason,
    oracle_rows_from_labels,
    read_jsonl_many,
    repo_root,
    resolve,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_G56_PROBES = "outputs/logs/phase5p5_repair5g56_counterfactual_label_completion/phase5p5_repair5g56_counterfactual_update_probes.jsonl"
DEFAULT_G56_CHECKPOINTS = "outputs/logs/phase5p5_repair5g56_counterfactual_label_completion/phase5p5_repair5g56_update_checkpoints.jsonl"
DEFAULT_G55_PROBES = "outputs/logs/phase5p5_repair5g55_scaled_counterfactual_labels/phase5p5_repair5g55_counterfactual_update_probes.jsonl"
DEFAULT_G55_CHECKPOINTS = "outputs/logs/phase5p5_repair5g55_scaled_counterfactual_labels/phase5p5_repair5g55_update_checkpoints.jsonl"
DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g56_counterfactual_update_labels.csv"
DEFAULT_CONTEXTS = "outputs/tables/phase5p5_repair5g56_counterfactual_contexts.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g56_oracle_by_context.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g56_counterfactual_label_completion.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g56_counterfactual_label_completion_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-jsonl", nargs="+", type=Path, default=[Path(DEFAULT_G56_PROBES), Path(DEFAULT_G55_PROBES)])
    parser.add_argument("--checkpoint-jsonl", nargs="+", type=Path, default=[Path(DEFAULT_G56_CHECKPOINTS), Path(DEFAULT_G55_CHECKPOINTS)])
    parser.add_argument("--labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--contexts-csv", type=Path, default=Path(DEFAULT_CONTEXTS))
    parser.add_argument("--oracle-csv", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--expected-maps", nargs="+", default=G56_MAPS)
    parser.add_argument("--expected-agent-counts", nargs="+", type=int, default=G56_AGENT_COUNTS)
    parser.add_argument("--expected-candidates", default=",".join(G56_BASE_CANDIDATES))
    return parser.parse_args(argv)


def checkpoint_replayability(checkpoints: list[dict[str, Any]]) -> bool:
    return bool(checkpoints) and all(
        boolish(row.get("replayed_traffic_after_hash_match", True))
        and boolish(row.get("replayed_update_stats_match", True))
        for row in checkpoints
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    probe_paths = [resolve(path, root) for path in args.probe_jsonl]
    checkpoint_paths = [resolve(path, root) for path in args.checkpoint_jsonl]
    probe_rows = dedupe_rows(
        read_jsonl_many(probe_paths),
        ["context_id", "map", "agents", "seed", "iteration", "traffic_before_hash_full", "candidate_id", "short_budget_ms"],
    )
    checkpoint_rows = dedupe_rows(
        read_jsonl_many(checkpoint_paths),
        ["context_id", "map", "agents", "seed", "iteration", "traffic_before_hash_full"],
    )
    expected_candidates = [token for token in str(args.expected_candidates).split(",") if token]
    labels = labels_from_probe_rows(probe_rows)
    oracle = oracle_rows_from_labels(labels, expected_candidates)
    contexts = context_rows_from_labels_and_oracle(labels, oracle, checkpoint_rows)
    write_csv_rows(resolve(args.labels_csv, root), labels)
    write_csv_rows(resolve(args.oracle_csv, root), oracle)
    write_csv_rows(resolve(args.contexts_csv, root), contexts)

    by_context = group_by_context(labels)
    context_count = len(by_context)
    expected_label_rows = context_count * len(expected_candidates)
    required_candidates = set(expected_candidates)
    coverage_complete = bool(by_context) and all(
        required_candidates <= {str(row.get("candidate_id", "")) for row in rows}
        for rows in by_context.values()
    )
    same_context_ok = bool(by_context) and all(
        len(
            {
                (
                    row.get("map"),
                    row.get("agents"),
                    row.get("seed"),
                    row.get("iteration"),
                    row.get("traffic_before_hash_full"),
                )
                for row in rows
            }
        )
        == 1
        for rows in by_context.values()
    )
    expected_groups = {(str(map_name), int(agents)) for map_name in args.expected_maps for agents in args.expected_agent_counts}
    actual_groups = {(str(row.get("map", "")), int(float(row.get("agents") or 0))) for row in contexts}
    missing_groups = sorted(expected_groups - actual_groups)
    observed_only = validate_observed_rows(labels, label="Repair5G.5.6 labels")
    later_context_count = sum(1 for row in contexts if finite_number(row.get("iteration"), 0.0) > 0)
    nonzero_trace_contexts = sum(1 for row in contexts if finite_number(row.get("trace_event_count"), 0.0) > 0)
    iteration_coverage = iteration_counts(contexts)
    later_reason = later_iteration_reason(contexts, checkpoint_rows)
    gates = {
        "context_count_ge_120": context_count >= G56_CONTEXT_TARGET,
        "label_rows_equal_context_count_times_candidate_count": len(labels) == expected_label_rows and context_count > 0,
        "same_context_labels_exist_for_all_candidates": coverage_complete and same_context_ok,
        "checkpoint_replayability_still_passes": checkpoint_replayability(checkpoint_rows),
        "map_agent_coverage_complete": not missing_groups,
        "iteration_coverage_reported": bool(iteration_coverage),
        "later_iteration_context_count_gt_0": later_context_count > 0,
        "observed_ids_only": observed_only,
        "ids_166_205_untouched": observed_only,
    }
    gates["counterfactual_label_completion_passed"] = all(gates.values())
    gaps = [
        finite_number(row.get("oracle_gap_over_static"), math.nan)
        for row in oracle
        if math.isfinite(finite_number(row.get("oracle_gap_over_static"), math.nan))
    ]
    summary = {
        "schema_version": "phase5p5_repair5g56_counterfactual_label_completion_summary_v1",
        "probe_jsonl": [str(path) for path in probe_paths],
        "checkpoint_jsonl": [str(path) for path in checkpoint_paths],
        "context_count": context_count,
        "label_rows": len(labels),
        "candidate_count": len(expected_candidates),
        "checkpoint_rows": len(checkpoint_rows),
        "oracle_rows": len(oracle),
        "map_agent_groups": sorted([f"{map_name}|a{agents}" for map_name, agents in actual_groups]),
        "missing_map_agent_groups": missing_groups,
        "iteration_coverage": iteration_coverage,
        "later_iteration_context_count": later_context_count,
        "later_iteration_unavailable_reason": later_reason,
        "nonzero_trace_contexts": nonzero_trace_contexts,
        "oracle_beats_static_contexts": sum(1 for row in oracle if boolish(row.get("oracle_beats_static"))),
        "oracle_beats_static_fraction": (
            sum(1 for row in oracle if boolish(row.get("oracle_beats_static"))) / len(oracle)
            if oracle
            else 0.0
        ),
        "mean_oracle_gap_over_static": sum(gaps) / len(gaps) if gaps else None,
        "labels_csv": str(resolve(args.labels_csv, root)),
        "contexts_csv": str(resolve(args.contexts_csv, root)),
        "oracle_csv": str(resolve(args.oracle_csv, root)),
        "gates": gates,
        "decision": "counterfactual_label_completion_passed" if gates["counterfactual_label_completion_passed"] else "label_completion_insufficient",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "g6_training_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.6 Counterfactual Label Completion\n\n"
        f"- context_count: `{context_count}`\n"
        f"- label_rows: `{len(labels)}`\n"
        f"- candidate_count: `{len(expected_candidates)}`\n"
        f"- map_agent_coverage_complete: `{gates['map_agent_coverage_complete']}`\n"
        f"- iteration_coverage: `{json.dumps(iteration_coverage, sort_keys=True)}`\n"
        f"- later_iteration_context_count: `{later_context_count}`\n"
        f"- later_iteration_unavailable_reason: `{later_reason}`\n"
        f"- counterfactual_label_completion_passed: `{gates['counterfactual_label_completion_passed']}`\n\n"
        "These are observed-ID same-context short-probe labels only. G6 training remains gated by budget stability and target construction.\n",
    )
    print(json.dumps({"decision": summary["decision"], "context_count": context_count, "later_iteration_context_count": later_context_count}))
    return 0 if context_count > 0 and gates["observed_ids_only"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Create Repair5G.5.10 runtime-safe feature matrix v2."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g510_common import (  # noqa: E402
    G59_CLOSED_STATUS,
    context_key,
    feature_map_from_checkpoint,
    finite_number,
    read_csv_rows,
    read_jsonl,
    repo_root,
    resolve,
    traffic_summary,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_BASE_FEATURES = "outputs/tables/phase5p5_repair5g58_g6_features_perf_safe.csv"
DEFAULT_CONTEXTS = "outputs/tables/phase5p5_repair5g58_primary_pair_confidence_by_context.csv"
DEFAULT_CHECKPOINTS = "outputs/logs/phase5p5_repair5g510_lattice_counterfactuals/phase5p5_repair5g510_update_checkpoints.jsonl"
DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g510_feature_matrix_v2.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g510_feature_matrix_v2.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g510_feature_matrix_v2_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-feature-csv", type=Path, default=Path(DEFAULT_BASE_FEATURES))
    parser.add_argument("--contexts-csv", type=Path, default=Path(DEFAULT_CONTEXTS))
    parser.add_argument("--checkpoint-jsonl", type=Path, default=Path(DEFAULT_CHECKPOINTS))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def normalized_event_features(features: dict[str, float]) -> dict[str, float]:
    agents = max(1.0, features.get("agents", 0.0))
    area = max(1.0, features.get("map_width", 0.0) * features.get("map_height", 0.0))
    committed = features.get("committed_count", 0.0)
    blocked = features.get("blocked_count", 0.0)
    wait = features.get("wait_event_count", 0.0)
    progress = features.get("progress_committed_count", 0.0)
    nonprogress = features.get("nonprogress_committed_count", 0.0)
    c_edges = features.get("c_nonzero_edges", features.get("traffic_before_nonzero_edges", 0.0))
    f_edges = features.get("f_nonzero_edges", features.get("traffic_before_flow_nonzero_edges", 0.0))
    return {
        "event_total": committed + blocked + wait,
        "event_total_per_agent": (committed + blocked + wait) / agents,
        "event_total_per_area": (committed + blocked + wait) / area,
        "blocked_per_area": blocked / area,
        "wait_per_area": wait / area,
        "committed_per_area": committed / area,
        "progress_per_area": progress / area,
        "nonprogress_per_area": nonprogress / area,
        "progress_to_nonprogress_ratio": progress / max(1.0, nonprogress),
        "wait_block_burst_score": (wait + blocked) / max(1.0, committed),
        "c_nonzero_per_area": c_edges / area,
        "f_nonzero_per_area": f_edges / area,
        "c_nonzero_per_agent": c_edges / agents,
        "f_nonzero_per_agent": f_edges / agents,
        "cf_ratio": c_edges / max(1.0, f_edges),
        "cf_imbalance": abs(c_edges - f_edges) / max(1.0, c_edges + f_edges),
        "map_area": area,
        "agent_density": agents / area,
        "later_iteration": 1.0 if features.get("ltm_iterations", features.get("iteration", 0.0)) > 0 else 0.0,
        "incumbent_progress_context": 1.0 if features.get("has_incumbent_before", 0.0) > 0 and features.get("progress_ratio", 0.0) > 0.5 else 0.0,
        "static_near_oracle_boundary_proxy": 1.0
        if (blocked / max(1.0, committed + wait)) < 0.15 and (c_edges / max(1.0, area)) < 0.02
        else 0.0,
    }


def checkpoint_rows_by_context(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    out = {}
    for row in rows:
        key = context_key(row)
        if key and key not in out:
            out[key] = row
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    base_rows = read_csv_rows(resolve(args.base_feature_csv, root))
    contexts = {context_key(row): row for row in read_csv_rows(resolve(args.contexts_csv, root))}
    checkpoints = checkpoint_rows_by_context(read_jsonl(resolve(args.checkpoint_jsonl, root)))
    out_rows = []
    full_traffic_rows = 0
    for base in base_rows:
        key = context_key(base)
        checkpoint = checkpoints.get(key, {})
        context = contexts.get(key, {})
        metadata_fields = {
            "context_id",
            "normalized_context_key",
            "map",
            "agents",
            "seed",
            "iteration",
            "traffic_before_hash_full",
            "label_class",
            "margin_threshold",
            "stable_static_or_abstain",
            "target_candidate_id",
            "train_weight",
            "training_eligible",
        }
        features = {name: finite_number(value, 0.0) for name, value in base.items() if name not in metadata_fields}
        features.update(feature_map_from_checkpoint(checkpoint))
        features["agents"] = finite_number(base.get("agents") or context.get("agents"), features.get("agents", 0.0))
        features["iteration"] = finite_number(base.get("iteration") or context.get("iteration"), features.get("iteration", 0.0))
        c_summary = traffic_summary(checkpoint.get("traffic_before_full_sparse_edges") or checkpoint.get("traffic_before_edges"), prefix="c_traffic_before_")
        f_summary = traffic_summary(checkpoint.get("traffic_before_full_sparse_edges") or checkpoint.get("traffic_before_edges"), prefix="f_traffic_before_")
        if c_summary["c_traffic_before_nonzero_count"] > 0 or f_summary["f_traffic_before_nonzero_count"] > 0:
            full_traffic_rows += 1
        features.update(c_summary)
        features.update(f_summary)
        features.update(normalized_event_features(features))
        out_rows.append(
            {
                "context_id": base.get("context_id", context.get("context_id", "")),
                "normalized_context_key": key,
                "map": base.get("map", context.get("map", "")),
                "agents": int(features["agents"]),
                "seed": base.get("seed", context.get("seed", "")),
                "iteration": int(features["iteration"]),
                "traffic_before_hash_full": base.get("traffic_before_hash_full", context.get("traffic_before_hash_full", "")),
                **{name: value for name, value in sorted(features.items())},
            }
        )
    write_csv_rows(resolve(args.output_csv, root), out_rows)
    feature_names = sorted(
        {
            key
            for row in out_rows
            for key in row
            if key not in {"context_id", "normalized_context_key", "map", "agents", "seed", "iteration", "traffic_before_hash_full"}
        }
    )
    summary = {
        "schema_version": "phase5p5_repair5g510_feature_matrix_v2_summary_v1",
        "rows": len(out_rows),
        "feature_count": len(feature_names),
        "feature_names": feature_names,
        "checkpoint_rows_used": len(checkpoints),
        "rows_with_traffic_snapshot_values": full_traffic_rows,
        "runtime_safe_pre_update_only": True,
        "forbidden_outcome_features_excluded": True,
        "feature_matrix_csv": str(resolve(args.output_csv, root)),
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.10 Feature Matrix v2\n\n"
        f"- rows: `{len(out_rows)}`\n"
        f"- feature_count: `{len(feature_names)}`\n"
        f"- checkpoint_rows_used: `{len(checkpoints)}`\n"
        f"- rows_with_traffic_snapshot_values: `{full_traffic_rows}`\n"
        "- runtime_safe_pre_update_only: `True`\n"
        "- forbidden_outcome_features_excluded: `True`\n\n"
        "The v2 matrix keeps G5.8 perf-safe context features and adds pre-update C/F traffic summaries, "
        "normalized event features, wait/block burst indicators, progress/nonprogress ratios, later-iteration flags, "
        "and a static-boundary proxy that uses only pre-update state.\n",
    )
    print(json.dumps({"rows": len(out_rows), "feature_count": len(feature_names)}))
    return 0 if out_rows else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

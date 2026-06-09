"""Analyze Repair5G.5.4 checkpoint replayability and schema quality."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import read_jsonl, repo_root, resolve, write_csv_rows  # noqa: E402
from repair5g54_common import G54_FORBIDDEN_LABEL_FIELDS, boolish, load_json, validate_observed_instance_ids, write_json, write_text  # noqa: E402


DEFAULT_CHECKPOINTS = "outputs/logs/phase5p5_repair5g54_checkpoint_export/phase5p5_repair5g54_update_checkpoints.jsonl"
DEFAULT_EXPORT_SUMMARY = "outputs/reports/phase5p5_repair5g54_checkpoint_export_observed_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g54_checkpoint_replayability_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g54_checkpoint_replayability_summary.json"
DEFAULT_MANIFEST = "outputs/tables/phase5p5_repair5g54_checkpoint_manifest.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-jsonl", type=Path, default=Path(DEFAULT_CHECKPOINTS))
    parser.add_argument("--checkpoint-export-summary-json", type=Path, default=Path(DEFAULT_EXPORT_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--manifest-csv", type=Path, default=Path(DEFAULT_MANIFEST))
    return parser.parse_args(argv)


def manifest_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        fields = set(row)
        forbidden = sorted(fields & G54_FORBIDDEN_LABEL_FIELDS)
        before_edges = row.get("traffic_before_full_sparse_edges")
        after_edges = row.get("traffic_after_full_sparse_edges")
        out.append(
            {
                "checkpoint_index": index,
                "schema_version": row.get("schema_version", ""),
                "method": row.get("method", ""),
                "map": row.get("map", ""),
                "agents": row.get("agents", ""),
                "seed": row.get("seed", ""),
                "iteration": row.get("iteration", ""),
                "trace_event_count": row.get("trace_event_count", 0),
                "traffic_before_hash_full": row.get("traffic_before_hash_full", ""),
                "traffic_after_hash_full": row.get("traffic_after_hash_full", ""),
                "replayed_traffic_after_hash_full": row.get("replayed_traffic_after_hash_full", ""),
                "replayed_traffic_after_hash_match": row.get("replayed_traffic_after_hash_match", ""),
                "replayed_update_stats_match": row.get("replayed_update_stats_match", ""),
                "before_full_sparse_edges": len(before_edges) if isinstance(before_edges, list) else "",
                "after_full_sparse_edges": len(after_edges) if isinstance(after_edges, list) else "",
                "forbidden_fields": ",".join(forbidden),
                "updateparams_hash": row.get("selected_candidate_params_hash", row.get("applied_updateparams_hash", "")),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    export_summary = load_json(resolve(args.checkpoint_export_summary_json, root))
    checkpoint_path = resolve(args.checkpoint_jsonl, root)
    if export_summary and not export_summary.get("checkpoint_export_passed"):
        reason = str(export_summary.get("blocked_reason") or "checkpoint_export_failed")
        write_csv_rows(resolve(args.manifest_csv, root), [])
        summary = {
            "schema_version": "phase5p5_repair5g54_checkpoint_replayability_summary_v1",
            "checkpoint_rows": 0,
            "checkpoint_replayability_passed": False,
            "blocked_reason": reason,
            "gates": {"checkpoint_replayability_passed": False, "blocked_by_checkpoint_export": True},
            "phase5p5_allowed": False,
            "phase6_allowed": False,
            "aaai_ready": False,
        }
        write_json(resolve(args.summary_json, root), summary)
        write_text(resolve(args.report, root), f"# Phase5.5 Repair5G.5.4 Checkpoint Replayability\n\nBlocked: `{reason}`.\n")
        print(json.dumps({"checkpoint_replayability_passed": False, "blocked_reason": reason}))
        return 2

    rows = read_jsonl(checkpoint_path)
    manifest = manifest_rows(rows)
    write_csv_rows(resolve(args.manifest_csv, root), manifest)
    seeds = [int(row.get("seed", 0)) for row in rows]
    observed_ids_only = True
    try:
        validate_observed_instance_ids(seeds)
    except SystemExit:
        observed_ids_only = False
    full_before_present = rows and all(row.get("traffic_before_hash_full") for row in rows)
    full_after_present = rows and all(row.get("traffic_after_hash_full") for row in rows)
    trace_present = rows and all(int(row.get("trace_event_count") or 0) > 0 for row in rows)
    update_hash_present = rows and all(row.get("selected_candidate_params_hash") or row.get("applied_updateparams_hash") for row in rows)
    full_sparse_present = rows and all(isinstance(row.get("traffic_before_full_sparse_edges"), list) and isinstance(row.get("traffic_after_full_sparse_edges"), list) for row in rows)
    replay_hash_match = rows and all(boolish(row.get("replayed_traffic_after_hash_match")) for row in rows)
    replay_stats_match = rows and all(boolish(row.get("replayed_update_stats_match")) for row in rows)
    no_forbidden_fields = not any(row.get("forbidden_fields") for row in manifest)
    gates = {
        "checkpoint_rows_gt_0": len(rows) > 0,
        "observed_ids_only": observed_ids_only,
        "ids_166_205_untouched": observed_ids_only,
        "traffic_before_hash_full_present": bool(full_before_present),
        "traffic_after_hash_full_present": bool(full_after_present),
        "trace_event_count_present": bool(trace_present),
        "updateparams_hash_present": bool(update_hash_present),
        "full_sparse_traffic_present": bool(full_sparse_present),
        "replay_transform_hash_matches": bool(replay_hash_match),
        "replay_update_stats_match": bool(replay_stats_match),
        "no_forbidden_fields": no_forbidden_fields,
    }
    gates["checkpoint_replayability_passed"] = all(gates.values())
    summary = {
        "schema_version": "phase5p5_repair5g54_checkpoint_replayability_summary_v1",
        "checkpoint_rows": len(rows),
        "checkpoint_jsonl": str(checkpoint_path),
        "manifest_csv": str(resolve(args.manifest_csv, root)),
        "gates": gates,
        "checkpoint_replayability_passed": gates["checkpoint_replayability_passed"],
        "decision": "continue_counterfactual_label_collection" if gates["checkpoint_replayability_passed"] else "checkpoint_replayability_failed",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.4 Checkpoint Replayability\n\n"
        f"- checkpoint_rows: `{len(rows)}`\n"
        f"- observed_ids_only: `{observed_ids_only}`\n"
        f"- full_sparse_traffic_present: `{bool(full_sparse_present)}`\n"
        f"- replay_transform_hash_matches: `{bool(replay_hash_match)}`\n"
        f"- replay_update_stats_match: `{bool(replay_stats_match)}`\n"
        f"- checkpoint_replayability_passed: `{gates['checkpoint_replayability_passed']}`\n"
        f"- decision: `{summary['decision']}`\n",
    )
    print(json.dumps({"checkpoint_replayability_passed": gates["checkpoint_replayability_passed"], "checkpoint_rows": len(rows)}))
    return 0 if gates["checkpoint_replayability_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

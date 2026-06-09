"""Analyze Repair5G.5.3 checkpoint replayability schema."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import read_jsonl, repo_root, resolve, write_csv_rows, write_json  # noqa: E402
from repair5g51_common import write_text  # noqa: E402


DEFAULT_CHECKPOINTS = "outputs/logs/phase5p5_repair5g53_checkpoint_export/phase5p5_repair5g53_update_checkpoints.jsonl"
DEFAULT_EXPORT_SUMMARY = "outputs/reports/phase5p5_repair5g53_checkpoint_export_smoke_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g53_checkpoint_replayability_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g53_checkpoint_replayability_summary.json"
DEFAULT_MANIFEST = "outputs/tables/phase5p5_repair5g53_checkpoint_manifest.csv"

FORBIDDEN_FEATURES = {"instance_id", "seed", "scen", "candidate outcome", "oracle", "final solver outcome"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-jsonl", type=Path, default=Path(DEFAULT_CHECKPOINTS))
    parser.add_argument("--checkpoint-export-summary-json", type=Path, default=Path(DEFAULT_EXPORT_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--manifest-csv", type=Path, default=Path(DEFAULT_MANIFEST))
    return parser.parse_args(argv)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for index, row in enumerate(rows):
        features = [str(name) for name in row.get("feature_names", [])]
        forbidden = sorted(set(features) & FORBIDDEN_FEATURES)
        out.append(
            {
                "checkpoint_index": index,
                "method": row.get("method", ""),
                "map": row.get("map", ""),
                "agents": row.get("agents", ""),
                "seed": row.get("seed", ""),
                "iteration": row.get("iteration", ""),
                "trace_event_count": row.get("trace_event_count", 0),
                "traffic_before_hash": row.get("traffic_before_hash", ""),
                "traffic_before_edge_count": len(row.get("traffic_before_edges", []) or []),
                "feature_count": len(features),
                "forbidden_features": ",".join(forbidden),
                "selected_candidate_params_hash": row.get("selected_candidate_params_hash", ""),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    checkpoint_path = resolve(args.checkpoint_jsonl, root)
    export_summary = load_json(resolve(args.checkpoint_export_summary_json, root))
    if export_summary and not export_summary.get("checkpoint_export_passed"):
        reason = str(export_summary.get("blocked_reason") or "checkpoint_export_failed")
        write_csv_rows(resolve(args.manifest_csv, root), [])
        gates = {
            "checkpoint_rows_gt_0": False,
            "trace_events_present": False,
            "traffic_before_present": False,
            "traffic_before_hash_present": False,
            "feature_vector_present": False,
            "no_forbidden_features": True,
            "forbidden_features": [],
            "estimated_size_acceptable": True,
            "blocked_by_checkpoint_export": True,
            "checkpoint_replayability_passed": False,
        }
        summary = {
            "schema_version": "phase5p5_repair5g53_checkpoint_replayability_summary_v1",
            "checkpoint_rows": 0,
            "checkpoint_jsonl": str(checkpoint_path),
            "manifest_csv": str(resolve(args.manifest_csv, root)),
            "estimated_size_bytes": 0,
            "gates": gates,
            "decision": "checkpoint_export_blocked",
            "blocked_reason": reason,
            "phase5p5_allowed": False,
            "phase6_allowed": False,
            "aaai_ready": False,
        }
        write_json(resolve(args.summary_json, root), summary)
        write_text(
            resolve(args.report, root),
            "# Phase5.5 Repair5G.5.3 Checkpoint Replayability\n\n"
            f"Blocked: `{reason}`.\n",
        )
        print(json.dumps({"checkpoint_replayability_passed": False, "blocked_reason": reason}))
        return 2
    rows = read_jsonl(checkpoint_path)
    manifest = manifest_rows(rows)
    write_csv_rows(resolve(args.manifest_csv, root), manifest)
    checkpoint_rows = len(rows)
    trace_events_present = checkpoint_rows > 0 and all(int(row.get("trace_event_count") or 0) > 0 for row in rows)
    traffic_before_present = checkpoint_rows > 0 and all(isinstance(row.get("traffic_before_edges"), list) for row in rows)
    traffic_before_hash_present = checkpoint_rows > 0 and all(row.get("traffic_before_hash") for row in rows)
    feature_vector_present = checkpoint_rows > 0 and all(row.get("feature_names") and row.get("feature_values") for row in rows)
    forbidden_seen = sorted({item for row in manifest for item in str(row.get("forbidden_features", "")).split(",") if item})
    estimated_size = checkpoint_path.stat().st_size if checkpoint_path.exists() else 0
    gates = {
        "checkpoint_rows_gt_0": checkpoint_rows > 0,
        "trace_events_present": trace_events_present,
        "traffic_before_present": traffic_before_present,
        "traffic_before_hash_present": traffic_before_hash_present,
        "feature_vector_present": feature_vector_present,
        "no_forbidden_features": not forbidden_seen,
        "forbidden_features": forbidden_seen,
        "estimated_size_acceptable": estimated_size < 250 * 1024 * 1024,
    }
    gates["checkpoint_replayability_passed"] = all(
        gates[key]
        for key in [
            "checkpoint_rows_gt_0",
            "trace_events_present",
            "traffic_before_present",
            "traffic_before_hash_present",
            "feature_vector_present",
            "no_forbidden_features",
            "estimated_size_acceptable",
        ]
    )
    summary = {
        "schema_version": "phase5p5_repair5g53_checkpoint_replayability_summary_v1",
        "checkpoint_rows": checkpoint_rows,
        "checkpoint_jsonl": str(checkpoint_path),
        "manifest_csv": str(resolve(args.manifest_csv, root)),
        "estimated_size_bytes": estimated_size,
        "gates": gates,
        "decision": "continue_counterfactual_label_collection" if gates["checkpoint_replayability_passed"] else "checkpoint_export_failed",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.3 Checkpoint Replayability\n\n"
        f"- checkpoint_rows: `{checkpoint_rows}`\n"
        f"- trace_events_present: `{trace_events_present}`\n"
        f"- traffic_before_present: `{traffic_before_present}`\n"
        f"- feature_vector_present: `{feature_vector_present}`\n"
        f"- checkpoint_replayability_passed: `{gates['checkpoint_replayability_passed']}`\n"
        f"- decision: `{summary['decision']}`\n",
    )
    print(json.dumps({"checkpoint_replayability_passed": gates["checkpoint_replayability_passed"], "checkpoint_rows": checkpoint_rows}))
    return 0 if gates["checkpoint_replayability_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

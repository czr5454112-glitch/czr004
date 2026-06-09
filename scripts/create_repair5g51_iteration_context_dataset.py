"""Create Repair5G.5.1 iteration-context rows from observed runtime logs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g51_common import read_jsonl, repo_root, resolve, write_csv_rows, write_json, write_text  # noqa: E402


DEFAULT_LOGS = [
    "outputs/logs/phase5p5_repair5g5_runtime_smoke/phase5p5_repair5g5_runtime_smoke_ltm_updates.jsonl",
    "outputs/logs/phase5p5_repair5g51_runtime_hook_sanity/phase5p5_repair5g51_runtime_hook_sanity_ltm_updates.jsonl",
    "outputs/logs/phase5p5_repair5g51_safe_selector_runtime_smoke/phase5p5_repair5g51_safe_selector_runtime_smoke_ltm_updates.jsonl",
]
DEFAULT_CONTEXTS = "outputs/tables/phase5p5_repair5g51_iteration_contexts.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g51_iteration_context_dataset_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g51_iteration_context_dataset_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-log-jsonl", nargs="*", type=Path, default=[Path(value) for value in DEFAULT_LOGS])
    parser.add_argument("--contexts-csv", type=Path, default=Path(DEFAULT_CONTEXTS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def _context_rows(update_rows: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    out = []
    for index, row in enumerate(update_rows):
        names = [str(value) for value in row.get("runtime_feature_names", [])]
        values = row.get("runtime_feature_values", [])
        features = {f"feature_{name}": values[pos] for pos, name in enumerate(names) if pos < len(values)}
        out.append(
            {
                "context_id": f"{source}:{index}",
                "source_log": source,
                "method": row.get("method", ""),
                "map": row.get("map", ""),
                "agents": row.get("agents", ""),
                "seed": row.get("seed", ""),
                "scen": row.get("scen", ""),
                "iteration": row.get("iteration", ""),
                "has_incumbent_before": row.get("has_incumbent_before", ""),
                "best_ratio_before": row.get("best_ratio_before", ""),
                "selected_candidate_id": row.get("selected_candidate_id", ""),
                "decision_status": row.get("decision_status", ""),
                "traffic_snapshot_available": False,
                "trace_events_available": bool(names),
                **features,
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows: list[dict[str, Any]] = []
    source_counts = {}
    for path_arg in args.update_log_jsonl:
        path = resolve(path_arg, root)
        update_rows = read_jsonl(path)
        source = str(path_arg).replace("\\", "/")
        source_counts[source] = len(update_rows)
        rows.extend(_context_rows(update_rows, source))
    write_csv_rows(resolve(args.contexts_csv, root), rows)
    summary = {
        "schema_version": "phase5p5_repair5g51_iteration_context_dataset_summary_v1",
        "context_count": len(rows),
        "source_counts": source_counts,
        "observed_ids_only": True,
        "traffic_snapshots_available": False,
        "counterfactual_replay_ready": False,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.1 Iteration Context Dataset\n\n"
        f"- context_count: `{len(rows)}`\n"
        "- source: observed runtime update logs only\n"
        "- traffic_snapshots_available: `false`\n"
        "- counterfactual_replay_ready: `false`\n\n"
        "These rows are suitable for feature availability audits, but not for causal counterfactual labels until "
        "the C++ runtime exports replayable traffic snapshots or equivalent pre-update checkpoints.\n",
    )
    print(json.dumps({"context_count": len(rows)}))
    return 0 if rows else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

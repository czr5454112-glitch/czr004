"""Create G5.14 rich context features from existing checkpoint JSONL records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import (  # noqa: E402
    context_key,
    count_by,
    observed_id_flags,
    read_csv_rows,
    read_json,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)
from repair5g514_common import (  # noqa: E402
    ALLOWED_RICH_FIELDS,
    DEFAULT_CHECKPOINT_ARTIFACT_CSV,
    DEFAULT_CHECKPOINT_ARTIFACT_SUMMARY,
    DEFAULT_RICH_CONTEXT_CSV,
    DEFAULT_RICH_CONTEXT_SUMMARY,
    G514_CLOSED_CLAIMS,
    checkpoint_context_key,
    load_jsonl_records,
    rich_values_from_checkpoint,
)


DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g512_candidate_regret_targets.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g514_rich_context_features.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--artifact-csv", type=Path, default=Path(DEFAULT_CHECKPOINT_ARTIFACT_CSV))
    parser.add_argument("--artifact-summary-json", type=Path, default=Path(DEFAULT_CHECKPOINT_ARTIFACT_SUMMARY))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_RICH_CONTEXT_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_RICH_CONTEXT_SUMMARY))
    return parser.parse_args(argv)


def target_contexts(target_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    contexts: dict[str, dict[str, Any]] = {}
    for row in target_rows:
        key = str(row.get("normalized_context_key", "")) or context_key(row)
        if key in contexts:
            continue
        contexts[key] = {
            "normalized_context_key": key,
            "map": row.get("map", ""),
            "agents": row.get("agents", ""),
            "seed": row.get("seed", ""),
            "iteration": row.get("iteration", ""),
            "traffic_before_hash_full": row.get("traffic_before_hash_full", ""),
        }
    return contexts


def usable_paths(root: Path, artifact_rows: list[dict[str, Any]]) -> list[Path]:
    rows = [
        row
        for row in artifact_rows
        if int(float(row.get("usable_records", 0) or 0)) > 0
        and str(row.get("ids_166_205_untouched", "")).lower() in {"true", "1", "yes"}
    ]
    priority_tokens = [
        "phase5p5_repair5g510_lattice_counterfactuals",
        "phase5p5_repair5g511_remote",
        "phase5p5_repair5g510_lattice_smoke",
        "phase5p5_repair5g56",
        "phase5p5_repair5g55",
    ]

    def sort_key(row: dict[str, Any]) -> tuple[int, str]:
        path = str(row.get("checkpoint_path", ""))
        priority = next((index for index, token in enumerate(priority_tokens) if token in path), len(priority_tokens))
        return priority, path.lower()

    paths = []
    for row in sorted(rows, key=sort_key):
        absolute = Path(str(row.get("absolute_checkpoint_path", "")))
        if absolute.exists():
            paths.append(absolute)
            continue
        relative = resolve(str(row.get("checkpoint_path", "")), root)
        if relative.exists():
            paths.append(relative)
    return paths


def collect_records(paths: list[Path], wanted_contexts: set[str]) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    by_context: dict[str, dict[str, Any]] = {}
    scan_counts = {"checkpoint_files_parsed": 0, "usable_checkpoint_records_seen": 0, "wanted_checkpoint_records_seen": 0}
    for path in paths:
        scan_counts["checkpoint_files_parsed"] += 1
        for record in load_jsonl_records(path):
            scan_counts["usable_checkpoint_records_seen"] += 1
            key = checkpoint_context_key(record)
            if key not in wanted_contexts:
                continue
            scan_counts["wanted_checkpoint_records_seen"] += 1
            if key in by_context:
                continue
            item = {
                "normalized_context_key": key,
                "map": record.get("map", ""),
                "agents": record.get("agents", ""),
                "seed": record.get("seed", ""),
                "iteration": record.get("iteration", ""),
                "traffic_before_hash_full": record.get("traffic_before_hash_full", ""),
                "source_checkpoint_path": str(path),
                "source_checkpoint_line": record.get("_source_line_number", ""),
                "feature_source": "existing_checkpoint",
                "observed_ids_only": True,
                "ids_166_205_untouched": True,
            }
            item.update(rich_values_from_checkpoint(record))
            by_context[key] = item
            if len(by_context) == len(wanted_contexts):
                return by_context, scan_counts
    return by_context, scan_counts


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    target_rows = read_csv_rows(resolve(args.targets_csv, root))
    contexts = target_contexts(target_rows)
    artifact_rows = read_csv_rows(resolve(args.artifact_csv, root)) if resolve(args.artifact_csv, root).exists() else []
    artifact_summary = read_json(resolve(args.artifact_summary_json, root)) if resolve(args.artifact_summary_json, root).exists() else {}
    paths = usable_paths(root, artifact_rows)
    parsed, scan_counts = collect_records(paths, set(contexts))

    output_rows = []
    for key, base in sorted(contexts.items()):
        if key in parsed:
            output_rows.append(parsed[key])
        else:
            item = dict(base)
            item.update(
                {
                    "source_checkpoint_path": "",
                    "source_checkpoint_line": "",
                    "feature_source": "missing_existing_checkpoint",
                    "observed_ids_only": True,
                    "ids_166_205_untouched": True,
                }
            )
            for field in ALLOWED_RICH_FIELDS:
                item[f"rich_{field}"] = ""
                item[f"feature_rich_{field}"] = ""
            output_rows.append(item)

    rich_rows = [row for row in output_rows if row.get("feature_source") == "existing_checkpoint"]
    flags = observed_id_flags(output_rows)
    complete = len(rich_rows) == len(contexts)
    decision = (
        "existing_checkpoint_rich_features_recovered_continue_v4_matrix"
        if rich_rows
        else "existing_checkpoint_features_missing_local_probe_required"
    )
    summary = {
        "schema_version": "phase5p5_repair5g514_rich_context_features_summary_v1",
        "decision": decision,
        "artifact_search_decision": artifact_summary.get("decision", ""),
        "target_contexts": len(contexts),
        "rich_contexts": len(rich_rows),
        "missing_rich_contexts": len(contexts) - len(rich_rows),
        "rich_feature_count": len(ALLOWED_RICH_FIELDS) if rich_rows else 0,
        "source_complete": complete,
        "feature_source_distribution": count_by(output_rows, "feature_source"),
        "allowed_rich_fields": ALLOWED_RICH_FIELDS,
        "output_csv": str(resolve(args.output_csv, root)),
        **scan_counts,
        **flags,
        **G514_CLOSED_CLAIMS,
    }
    write_csv_rows(resolve(args.output_csv, root), output_rows)
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.14 Rich Context Features\n\n"
        f"- decision: `{decision}`\n"
        f"- artifact_search_decision: `{artifact_summary.get('decision', '')}`\n"
        f"- target_contexts: `{len(contexts)}`\n"
        f"- rich_contexts: `{len(rich_rows)}`\n"
        f"- missing_rich_contexts: `{len(contexts) - len(rich_rows)}`\n"
        f"- rich_feature_count: `{summary['rich_feature_count']}`\n"
        f"- source_complete: `{complete}`\n"
        f"- feature_source_distribution: `{summary['feature_source_distribution']}`\n"
        "- local_solver_probe_run: `false`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "The parser expands only the allowed pre-choice `feature_names` / `feature_values` fields from existing checkpoint JSONL rows. "
        "It does not use trace event identities, vertex IDs, probe outcomes, oracle scores, final solver outcomes, actions, priorities, restarts, h-values, or candidate deletion features.\n",
    )
    print(json.dumps({"decision": decision, "rich_contexts": len(rich_rows), "missing": len(contexts) - len(rich_rows)}))
    return 0 if rich_rows else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

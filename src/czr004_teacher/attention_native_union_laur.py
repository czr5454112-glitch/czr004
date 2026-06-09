"""Safely merge Phase4F Repair5 attention-native LAUR label datasets."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.attention_native_schema_laur import (  # noqa: E402
    ATTENTION_NATIVE_AUDIT_SCHEMA_VERSION,
    ATTENTION_NATIVE_DATASET_SCHEMA_VERSION,
    audit_attention_native_rows,
    validate_attention_native_row,
)
from czr004_teacher.stable_attention_dataset_laur import read_jsonl, write_jsonl  # noqa: E402


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path | None, root: Path) -> Path | None:
    if path is None:
        return None
    value = Path(path)
    return value if value.is_absolute() else root / value


def _token_shape(row: dict[str, Any]) -> tuple[Any, ...]:
    audit = row.get("audit", {})
    return (
        tuple(row.get("global_feature_names", [])),
        tuple(row.get("edge_feature_names", [])),
        tuple(row.get("trace_feature_names", [])),
        tuple(row.get("rule_feature_names", [])),
        tuple(row.get("rule_ids", [])),
        int(audit.get("max_edge_tokens", len(row.get("edge_tokens", [])))),
        int(audit.get("max_trace_tokens", len(row.get("trace_tokens", [])))),
        len(row.get("edge_tokens", [])),
        len(row.get("trace_tokens", [])),
        len(row.get("rule_tokens", [])),
    )


def _source_name(path: Path, index: int) -> str:
    stem = path.name
    if stem.endswith(".jsonl"):
        stem = stem[:-6]
    return f"input{index}:{stem}"


def combine_attention_native_datasets(
    input_paths: list[Path],
    *,
    duplicate_policy: str = "error",
    require_compatible_token_shape: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return merged rows and an audit summary.

    ``duplicate_policy`` is intentionally strict by default. ``first`` and
    ``last`` are only for deliberate rerun/repair cases where checkpoint IDs
    overlap and the preferred source has been decided explicitly.
    """

    if duplicate_policy not in {"error", "first", "last"}:
        raise ValueError("duplicate_policy must be one of: error, first, last")
    if not input_paths:
        raise ValueError("at least one input dataset is required")

    rows_by_checkpoint: dict[str, dict[str, Any]] = {}
    input_summaries: list[dict[str, Any]] = []
    duplicate_counts: Counter[str] = Counter()
    expected_shape: tuple[Any, ...] | None = None

    for input_index, input_path in enumerate(input_paths, 1):
        rows = read_jsonl(input_path)
        source = _source_name(input_path, input_index)
        input_errors: list[str] = []
        for row_index, row in enumerate(rows, 1):
            input_errors.extend(
                f"{input_path}:{row_index}: {error}" for error in validate_attention_native_row(row)
            )
            shape = _token_shape(row)
            if expected_shape is None:
                expected_shape = shape
            elif require_compatible_token_shape and shape != expected_shape:
                raise ValueError(
                    "incompatible attention-native token shape; "
                    f"first input shape differs from {input_path}:{row_index}"
                )
            checkpoint_id = str(row.get("checkpoint_id", ""))
            if checkpoint_id in rows_by_checkpoint:
                duplicate_counts[checkpoint_id] += 1
                if duplicate_policy == "error":
                    continue
                if duplicate_policy == "first":
                    continue
            copied = dict(row)
            copied["union_source"] = source
            rows_by_checkpoint[checkpoint_id] = copied
        if input_errors:
            raise ValueError("input attention-native schema errors:\n" + "\n".join(input_errors[:30]))
        input_summaries.append(
            {
                "path": str(input_path),
                "source": source,
                "row_count": len(rows),
                "decision_distribution": dict(
                    sorted(Counter(str(row.get("decision_target", "")) for row in rows).items())
                ),
                "split_distribution": dict(sorted(Counter(str(row.get("split", "")) for row in rows).items())),
                "validation_high_margin_opportunity_count": sum(
                    1
                    for row in rows
                    if row.get("split") == "validation" and row.get("has_high_margin_nonadditive_opportunity")
                ),
            }
        )

    if duplicate_policy == "error" and duplicate_counts:
        examples = ", ".join(sorted(duplicate_counts)[:10])
        raise ValueError(f"duplicate checkpoint_id values found across inputs: {examples}")

    merged_rows = [rows_by_checkpoint[key] for key in sorted(rows_by_checkpoint)]
    summary = audit_attention_native_rows(merged_rows)
    summary.update(
        {
            "schema_version": ATTENTION_NATIVE_AUDIT_SCHEMA_VERSION,
            "dataset_schema_version": ATTENTION_NATIVE_DATASET_SCHEMA_VERSION,
            "union_input_count": len(input_paths),
            "union_inputs": input_summaries,
            "duplicate_policy": duplicate_policy,
            "duplicate_checkpoint_count": len(duplicate_counts),
            "duplicate_checkpoint_examples": sorted(duplicate_counts)[:20],
            "require_compatible_token_shape": bool(require_compatible_token_shape),
        }
    )
    return merged_rows, summary


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair5 Attention-Native Union Audit\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("## Inputs\n\n")
        for item in summary.get("union_inputs", []):
            handle.write(f"- `{item['source']}` rows `{item['row_count']}`: `{item['path']}`\n")
        handle.write("\n## Audit\n\n")
        handle.write(f"- samples: `{summary['sample_count']}`\n")
        handle.write(f"- split counts: `{summary['split_counts']}`\n")
        handle.write(f"- decisions: `{summary['decision_distribution']}`\n")
        handle.write(f"- target rules: `{summary['target_rule_distribution']}`\n")
        handle.write(f"- validation high-margin opportunity count: `{summary['validation_high_margin_opportunity_count']}`\n")
        handle.write(f"- duplicate checkpoint count: `{summary['duplicate_checkpoint_count']}`\n")
        handle.write(f"- schema errors: `{summary['schema_error_count']}`\n")
        handle.write(f"- split leakage errors: `{summary['split_leakage_error_count']}`\n")
        handle.write(f"- passed: `{summary['passed']}`\n\n")
        handle.write("## Boundary\n\n")
        handle.write(
            "This is only an offline Repair5 attention-native label union. "
            "It does not relax gates, does not predict agent actions, does not replace PIBT/LaCAM*, "
            "and does not permit Phase5.5 runtime unless the full Repair5 promotion rule passes.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", action="append", type=Path, required=True)
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--report-md", type=Path)
    parser.add_argument("--duplicate-policy", choices=["error", "first", "last"], default="error")
    parser.add_argument("--allow-token-shape-mismatch", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    input_paths = [resolve_path(path, root) for path in args.input_jsonl]
    output_path = resolve_path(args.output_jsonl, root)
    summary_path = resolve_path(args.summary_json, root)
    report_path = resolve_path(args.report_md, root)
    assert output_path and summary_path
    resolved_inputs = [path for path in input_paths if path is not None]
    rows, summary = combine_attention_native_datasets(
        resolved_inputs,
        duplicate_policy=str(args.duplicate_policy),
        require_compatible_token_shape=not bool(args.allow_token_shape_mismatch),
    )
    if not summary["passed"]:
        raise ValueError(
            "union audit failed:\n"
            + "\n".join([*summary["schema_errors"][:20], *summary["split_leakage_errors"][:20]])
        )
    write_jsonl(output_path, rows)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if report_path is not None:
        write_report(report_path, summary)
    print(json.dumps({"dataset": str(output_path), "summary_json": str(summary_path), "rows": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

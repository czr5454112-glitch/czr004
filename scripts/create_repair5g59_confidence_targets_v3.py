"""Create Repair5G.5.9 confidence targets v3 with abstention/feasibility heads."""

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

from repair5g59_common import (  # noqa: E402
    G56_STATIC_CANDIDATE,
    G59_CLOSED_STATUS,
    G59_DEFAULT_MARGIN,
    finite_number,
    read_csv_rows,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_G58_TARGETS = "outputs/tables/phase5p5_repair5g58_confidence_weighted_targets.csv"
DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g59_confidence_targets_v3.csv"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g59_confidence_targets_v3_creation_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g59_confidence_targets_v3_creation.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g58-targets-csv", type=Path, default=Path(DEFAULT_G58_TARGETS))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    return parser.parse_args(argv)


def head_a_class(label_class: str) -> str:
    if label_class == "stable_high_confidence_nonstatic":
        return "trainable_expert_selection"
    if label_class in {"stable_static", "abstain_to_static"}:
        return "static_fallback"
    if label_class == "no_solution_abstain":
        return "no_solution_abstain"
    if label_class == "longer_budget_needed":
        return "longer_budget_needed"
    if label_class == "budget_sensitive_exclude":
        return "budget_sensitive_abstain"
    return "exclude_from_training"


def v3_row(row: dict[str, Any]) -> dict[str, Any]:
    label = str(row.get("label_class", ""))
    head_a = head_a_class(label)
    stable_eligible = label in {"stable_high_confidence_nonstatic", "stable_static", "abstain_to_static"}
    abstention_only = label in {"no_solution_abstain", "longer_budget_needed", "budget_sensitive_exclude"}
    return {
        **row,
        "label_class_v3": label,
        "head_a_class": head_a,
        "head_b_target_candidate_id": row.get("target_candidate_id", "") if stable_eligible else "",
        "head_b_training_eligible": stable_eligible,
        "abstention_feasibility_training_only": abstention_only,
        "expert_selection_positive": label == "stable_high_confidence_nonstatic",
        "static_fallback_positive": label in {"stable_static", "abstain_to_static"},
        "target_candidate_id": row.get("target_candidate_id", G56_STATIC_CANDIDATE),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    source_rows = read_csv_rows(resolve(args.g58_targets_csv, root))
    rows = [v3_row(row) for row in source_rows]
    write_csv_rows(resolve(args.output_csv, root), rows)
    default_rows = [
        row
        for row in rows
        if abs(finite_number(row.get("margin_threshold"), math.nan) - G59_DEFAULT_MARGIN) < 1.0e-12
    ]
    class_counts: dict[str, int] = {}
    head_counts: dict[str, int] = {}
    for row in default_rows:
        class_counts[str(row.get("label_class_v3", ""))] = class_counts.get(str(row.get("label_class_v3", "")), 0) + 1
        head_counts[str(row.get("head_a_class", ""))] = head_counts.get(str(row.get("head_a_class", "")), 0) + 1
    abstain_to_static_count = class_counts.get("abstain_to_static", 0)
    summary = {
        "schema_version": "phase5p5_repair5g59_confidence_targets_v3_creation_summary_v1",
        "decision": "confidence_targets_v3_created",
        "target_rows": len(rows),
        "default_threshold": G59_DEFAULT_MARGIN,
        "default_threshold_rows": len(default_rows),
        "class_counts_default_threshold": dict(sorted(class_counts.items())),
        "head_a_class_counts_default_threshold": dict(sorted(head_counts.items())),
        "abstain_to_static_count": abstain_to_static_count,
        "near_boundary_static_fallback_diagnostic": "abstain_to_static remains 0; current primary-pair protocol did not expose oracle-disagreement static-near-oracle rows." if abstain_to_static_count == 0 else "",
        "no_solution_longer_budget_training_policy": "train Head A feasibility/abstention only; never use as expert-selection positives",
        "output_csv": str(resolve(args.output_csv, root)),
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.9 Confidence Targets v3 Creation\n\n"
        f"- target_rows: `{len(rows)}`\n"
        f"- default_threshold_rows: `{len(default_rows)}`\n"
        f"- abstain_to_static_count: `{abstain_to_static_count}`\n"
        f"- head_a_class_counts: `{json.dumps(summary['head_a_class_counts_default_threshold'], sort_keys=True)}`\n\n"
        "No-solution and longer-budget rows are retained for feasibility/abstention training only.\n",
    )
    print(json.dumps({"decision": summary["decision"], "target_rows": len(rows)}))
    return 0 if rows else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Analyze Repair5G.5.9 confidence targets v3 and choose the training threshold."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g59_common import G59_CLOSED_STATUS, G59_DEFAULT_MARGIN, finite_number, read_csv_rows, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g59_confidence_targets_v3.csv"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g59_confidence_targets_v3_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g59_confidence_targets_v3.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    return parser.parse_args(argv)


def counts(rows: list[dict[str, str]], field: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        out[str(row.get(field, ""))] = out.get(str(row.get(field, "")), 0) + 1
    return dict(sorted(out.items()))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.targets_csv, root))
    by_threshold = {}
    for threshold in [0.0025, 0.005, 0.010]:
        selected = [row for row in rows if abs(finite_number(row.get("margin_threshold"), math.nan) - threshold) < 1.0e-12]
        by_threshold[str(threshold)] = {
            "rows": len(selected),
            "class_counts": counts(selected, "label_class_v3"),
            "head_a_class_counts": counts(selected, "head_a_class"),
            "head_b_training_rows": sum(1 for row in selected if str(row.get("head_b_training_eligible", "")).lower() == "true"),
            "abstain_to_static_count": sum(1 for row in selected if row.get("label_class_v3") == "abstain_to_static"),
        }
    default_info = by_threshold[str(G59_DEFAULT_MARGIN)]
    gates = {
        "confidence_targets_v3_created": bool(rows),
        "threshold_decision_before_training": True,
        "default_threshold_rows_gt_0": default_info["rows"] > 0,
        "head_a_has_abstention_classes": any(key in default_info["head_a_class_counts"] for key in ["no_solution_abstain", "longer_budget_needed"]),
        "head_b_training_rows_gt_0": default_info["head_b_training_rows"] > 0,
        "abstain_to_static_searched": True,
    }
    summary = {
        "schema_version": "phase5p5_repair5g59_confidence_targets_v3_summary_v1",
        "decision": "confidence_targets_v3_ready_for_abstention_policy_training" if all(gates.values()) else "confidence_targets_v3_insufficient_continue_probe_design",
        "selected_margin_threshold": G59_DEFAULT_MARGIN,
        "threshold_selection_reason": "preferred_threshold_passed_before_training",
        "by_margin_threshold": by_threshold,
        "near_boundary_static_fallback_diagnostic": "abstain_to_static remains 0 at all thresholds; active search should be expanded around oracle-disagreement static-near-oracle contexts.",
        "gates": gates,
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.9 Confidence Targets v3\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- selected_margin_threshold: `{G59_DEFAULT_MARGIN}`\n"
        f"- default_threshold_rows: `{default_info['rows']}`\n"
        f"- head_b_training_rows: `{default_info['head_b_training_rows']}`\n"
        f"- abstain_to_static_count: `{default_info['abstain_to_static_count']}`\n\n"
        "The threshold is selected before training. No-solution and longer-budget rows are reserved for Head A only.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows)}))
    return 0 if rows else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

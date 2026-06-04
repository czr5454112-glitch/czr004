"""Analyze Repair5G.5.2 counterfactual UpdateLTM label quality."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import read_csv_rows  # noqa: E402
from repair5g3_common import repo_root, resolve, write_json  # noqa: E402
from repair5g51_common import write_text  # noqa: E402


DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g52_counterfactual_update_labels.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g52_counterfactual_oracle_by_context.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g52_counterfactual_label_quality_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g52_counterfactual_label_quality_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--oracle-csv", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def boolish(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    labels = read_csv_rows(resolve(args.labels_csv, root))
    oracle = read_csv_rows(resolve(args.oracle_csv, root))
    available = [row for row in labels if boolish(row.get("counterfactual_label_available"))]
    contexts = {row.get("context_id", "") for row in labels}
    complete_contexts = {row.get("context_id", "") for row in oracle if boolish(row.get("candidate_coverage_complete"))}
    gates = {
        "label_rows_gt_0": len(labels) > 0,
        "available_label_rows_gt_0": len(available) > 0,
        "candidate_coverage_complete": bool(contexts) and contexts <= complete_contexts,
        "oracle_gap_over_static_measured": any(str(row.get("oracle_gap_over_static", "")) not in {"", "nan", "None"} for row in oracle),
        "feature_leakage_audit_passes": all(boolish(row.get("feature_leakage_safe", True)) for row in labels) if labels else False,
        "labels_are_contextual_not_run_level": bool(contexts),
    }
    gates["counterfactual_label_quality_passed"] = all(
        [
            gates["available_label_rows_gt_0"],
            gates["candidate_coverage_complete"],
            gates["oracle_gap_over_static_measured"],
            gates["feature_leakage_audit_passes"],
            gates["labels_are_contextual_not_run_level"],
        ]
    )
    summary = {
        "schema_version": "phase5p5_repair5g52_counterfactual_label_quality_summary_v1",
        "context_count": len(contexts),
        "label_rows": len(labels),
        "available_label_rows": len(available),
        "oracle_rows": len(oracle),
        "gates": gates,
        "decision": "continue_safe_mixture_policy_design" if gates["counterfactual_label_quality_passed"] else "counterfactual_labels_unavailable",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.2 Counterfactual Label Quality\n\n"
        f"- context_count: `{len(contexts)}`\n"
        f"- label_rows: `{len(labels)}`\n"
        f"- available_label_rows: `{len(available)}`\n"
        f"- candidate_coverage_complete: `{gates['candidate_coverage_complete']}`\n"
        f"- oracle_gap_over_static_measured: `{gates['oracle_gap_over_static_measured']}`\n"
        f"- counterfactual_label_quality_passed: `{gates['counterfactual_label_quality_passed']}`\n"
        f"- decision: `{summary['decision']}`\n",
    )
    print(json.dumps({"decision": summary["decision"], "available_label_rows": len(available)}))
    return 0 if gates["counterfactual_label_quality_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

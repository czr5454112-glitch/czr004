"""Analyze Repair5G.5.1 counterfactual label quality."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g51_common import read_csv_dicts, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_CONTEXTS = "outputs/tables/phase5p5_repair5g51_iteration_contexts.csv"
DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g51_counterfactual_update_labels.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g51_counterfactual_label_quality.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g51_counterfactual_label_quality_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contexts-csv", type=Path, default=Path(DEFAULT_CONTEXTS))
    parser.add_argument("--labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    contexts = read_csv_dicts(resolve(args.contexts_csv, root))
    labels = read_csv_dicts(resolve(args.labels_csv, root))
    available = [row for row in labels if str(row.get("counterfactual_label_available")).lower() == "true"]
    leakage_safe = all(str(row.get("leakage_safe", "true")).lower() == "true" for row in labels)
    runtime_feature_available = bool(contexts) and any(key.startswith("feature_") for key in contexts[0])
    gates = {
        "counterfactual_context_count_gt_0": len(contexts) > 0,
        "candidate_label_coverage_sufficient_for_smoke_training": len(available) >= 100,
        "label_leakage_audit_passes": leakage_safe,
        "runtime_feature_availability_audit_passes": runtime_feature_available,
        "oracle_gap_over_static_measured": False,
        "counterfactual_label_quality_passed": False,
    }
    gates["counterfactual_label_quality_passed"] = all(
        [
            gates["counterfactual_context_count_gt_0"],
            gates["candidate_label_coverage_sufficient_for_smoke_training"],
            gates["label_leakage_audit_passes"],
            gates["runtime_feature_availability_audit_passes"],
            gates["oracle_gap_over_static_measured"],
        ]
    )
    summary = {
        "schema_version": "phase5p5_repair5g51_counterfactual_label_quality_summary_v1",
        "context_count": len(contexts),
        "label_rows": len(labels),
        "available_label_rows": len(available),
        "gates": gates,
        "decision": "continue_counterfactual_label_collection"
        if not gates["counterfactual_label_quality_passed"]
        else "continue_small_neural_selector",
        "gap_report": "true counterfactual labels are unavailable without replayable pre-update traffic snapshots",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.1 Counterfactual Label Quality\n\n"
        f"- context_count: `{len(contexts)}`\n"
        f"- label_rows: `{len(labels)}`\n"
        f"- available_label_rows: `{len(available)}`\n"
        f"- counterfactual_label_quality_passed: `{gates['counterfactual_label_quality_passed']}`\n"
        "- decision: `continue_counterfactual_label_collection`\n\n"
        "No neural selector should be trained from final run outcomes masquerading as iteration-level labels. "
        "The next engineering step is minimal C++ checkpoint export for replayable UpdateLTM counterfactual probes.\n",
    )
    print(json.dumps({"counterfactual_label_quality_passed": gates["counterfactual_label_quality_passed"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Analyze Repair5G.5.7 confidence-weighted label classes."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g57_common import (  # noqa: E402
    G57_DEFAULT_MARGIN_THRESHOLD,
    G57_STATIC_ABSTAIN_CLASSES,
    count_by,
    default_threshold_rows,
    finite_number,
    is_true,
    map_agent_key,
    read_csv_rows,
    repo_root,
    resolve,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g57_confidence_weighted_labels.csv"
DEFAULT_BY_MAP_AGENT = "outputs/tables/phase5p5_repair5g57_confidence_weighted_labels_by_map_agent.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g57_confidence_weighted_label_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g57_confidence_weighted_label_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confidence-labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_BY_MAP_AGENT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--default-margin-threshold", type=float, default=G57_DEFAULT_MARGIN_THRESHOLD)
    return parser.parse_args(argv)


def threshold_rows(rows: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    return [row for row in rows if abs(finite_number(row.get("margin_threshold"), -1.0) - threshold) < 1.0e-12]


def class_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = count_by(rows, "label_class")
    for name in [
        "stable_high_confidence_nonstatic",
        "stable_static",
        "abstain_to_static",
        "no_solution_abstain",
        "budget_sensitive",
        "exclude_from_training",
    ]:
        counts.setdefault(name, 0)
    return dict(sorted(counts.items()))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    labels_csv = resolve(args.confidence_labels_csv, root)
    rows = read_csv_rows(labels_csv)
    default_rows = threshold_rows(rows, float(args.default_margin_threshold))
    training_rows = [row for row in default_rows if is_true(row.get("training_eligible"))]
    high_nonstatic = [row for row in default_rows if row.get("label_class") == "stable_high_confidence_nonstatic"]
    stable_static = [row for row in default_rows if row.get("label_class") == "stable_static"]
    abstain_static = [row for row in default_rows if row.get("label_class") == "abstain_to_static"]
    no_solution = [row for row in default_rows if row.get("label_class") == "no_solution_abstain"]
    budget_sensitive = [row for row in default_rows if row.get("label_class") == "budget_sensitive"]
    stable_static_or_abstain = [row for row in default_rows if row.get("label_class") in G57_STATIC_ABSTAIN_CLASSES]

    by_threshold = {}
    for threshold in sorted({finite_number(row.get("margin_threshold"), 0.0) for row in rows}):
        current = threshold_rows(rows, threshold)
        by_threshold[str(threshold)] = {
            "contexts": len(current),
            "training_eligible_contexts": sum(1 for row in current if is_true(row.get("training_eligible"))),
            "class_counts": class_counts(current),
        }

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in default_rows:
        groups[map_agent_key(row)].append(row)
    group_rows = []
    for key, group in sorted(groups.items()):
        first = group[0]
        group_rows.append(
            {
                "map_agent": key,
                "map": first.get("map", ""),
                "agents": first.get("agents", ""),
                "contexts": len(group),
                "training_eligible_contexts": sum(1 for row in group if is_true(row.get("training_eligible"))),
                "stable_high_confidence_nonstatic": sum(1 for row in group if row.get("label_class") == "stable_high_confidence_nonstatic"),
                "stable_static": sum(1 for row in group if row.get("label_class") == "stable_static"),
                "abstain_to_static": sum(1 for row in group if row.get("label_class") == "abstain_to_static"),
                "no_solution_abstain": sum(1 for row in group if row.get("label_class") == "no_solution_abstain"),
                "budget_sensitive": sum(1 for row in group if row.get("label_class") == "budget_sensitive"),
            }
        )
    write_csv_rows(resolve(args.by_map_agent_csv, root), group_rows)

    observed_ok = validate_observed_rows(rows, label="Repair5G.5.7 confidence label analysis")
    gates = {
        "confidence_labels_created": bool(rows),
        "training_eligible_contexts_count_reported": True,
        "stable_high_confidence_nonstatic_count_reported": True,
        "stable_static_count_reported": True,
        "abstain_to_static_count_reported": True,
        "no_solution_abstain_count_reported": True,
        "budget_sensitive_count_reported": True,
        "training_eligible_contexts_ge_30": len(training_rows) >= 30,
        "stable_high_confidence_nonstatic_count_ge_10": len(high_nonstatic) >= 10,
        "stable_static_or_abstain_count_ge_10": len(stable_static_or_abstain) >= 10,
        "observed_ids_only": observed_ok,
    }
    gates["ids_166_205_untouched"] = observed_ok
    gates["confidence_training_gate_passed"] = (
        gates["confidence_labels_created"]
        and gates["training_eligible_contexts_ge_30"]
        and gates["stable_high_confidence_nonstatic_count_ge_10"]
        and gates["stable_static_or_abstain_count_ge_10"]
        and gates["observed_ids_only"]
    )
    summary = {
        "schema_version": "phase5p5_repair5g57_confidence_weighted_label_summary_v1",
        "confidence_labels_csv": str(labels_csv),
        "by_map_agent_csv": str(resolve(args.by_map_agent_csv, root)),
        "default_margin_threshold": float(args.default_margin_threshold),
        "label_rows": len(rows),
        "default_threshold_contexts": len(default_rows),
        "class_counts_default_threshold": class_counts(default_rows),
        "training_eligible_contexts": len(training_rows),
        "stable_high_confidence_nonstatic_count": len(high_nonstatic),
        "stable_static_count": len(stable_static),
        "abstain_to_static_count": len(abstain_static),
        "stable_static_or_abstain_count": len(stable_static_or_abstain),
        "no_solution_abstain_count": len(no_solution),
        "budget_sensitive_count": len(budget_sensitive),
        "by_margin_threshold": by_threshold,
        "gates": gates,
        "decision": "confidence_labels_training_ready" if gates["confidence_training_gate_passed"] else "confidence_labels_insufficient_continue_probe_design",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "runtime_claim_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.7 Confidence-Weighted Label Analysis\n\n"
        f"- default_margin_threshold: `{summary['default_margin_threshold']}`\n"
        f"- default_threshold_contexts: `{summary['default_threshold_contexts']}`\n"
        f"- training_eligible_contexts: `{summary['training_eligible_contexts']}`\n"
        f"- stable_high_confidence_nonstatic_count: `{summary['stable_high_confidence_nonstatic_count']}`\n"
        f"- stable_static_count: `{summary['stable_static_count']}`\n"
        f"- abstain_to_static_count: `{summary['abstain_to_static_count']}`\n"
        f"- no_solution_abstain_count: `{summary['no_solution_abstain_count']}`\n"
        f"- budget_sensitive_count: `{summary['budget_sensitive_count']}`\n"
        f"- confidence_training_gate_passed: `{gates['confidence_training_gate_passed']}`\n\n"
        "Training remains blocked unless the default-threshold label mix has enough high-confidence nonstatic and static/abstain examples.\n",
    )
    print(json.dumps({"decision": summary["decision"], "training_eligible_contexts": len(training_rows)}))
    return 0 if gates["confidence_labels_created"] and observed_ok else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

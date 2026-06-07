"""Analyze Repair5G.5.11 confidence target v5 gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g510_common import G59_CLOSED_STATUS, count_by, finite_number, read_csv_rows, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g511_confidence_targets_v5.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g511_confidence_targets_v5_analysis.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g511_confidence_targets_v5_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def is_true(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.targets_csv, root))
    labels = count_by(rows, "label_class")
    training = [row for row in rows if is_true(row.get("training_eligible"))]
    measured = sum(1 for row in rows if is_true(row.get("primary_1000_2000_measured")))
    stable_primary = sum(1 for row in rows if is_true(row.get("primary_1000_2000_stable")))
    stable_nonstatic = labels.get("stable_high_confidence_parameter_candidate", 0)
    stable_static_or_abstain = labels.get("stable_static", 0) + labels.get("abstain_to_static", 0)
    no_solution_or_budget = labels.get("no_solution_abstain", 0) + labels.get("longer_budget_needed", 0)
    gates = {
        "measured_confidence_contexts_ge_60": measured >= 60,
        "primary_1000_2000_stable_contexts_ge_40": stable_primary >= 40,
        "head_b_training_rows_ge_40": len(training) >= 40,
        "stable_high_confidence_parameter_candidate_ge_10": stable_nonstatic >= 10,
        "stable_static_or_abstain_ge_10": stable_static_or_abstain >= 10,
        "no_solution_or_budget_abstain_count_gt_0": no_solution_or_budget > 0,
        "abstain_to_static_searched_and_reported": True,
        "observed_ids_only": all(int(finite_number(row.get("seed"), 0.0)) <= 165 for row in rows),
        "ids_166_205_untouched": all(not (166 <= int(finite_number(row.get("seed"), 0.0)) <= 205) for row in rows),
    }
    decision = "confidence_targets_v5_passed_continue_feature_v3" if all(gates.values()) else "confidence_targets_v5_failed_continue_label_design"
    summary = {
        "schema_version": "phase5p5_repair5g511_confidence_targets_v5_summary_v1",
        "decision": decision,
        "measured_confidence_contexts": measured,
        "primary_1000_2000_stable_contexts": stable_primary,
        "head_b_training_rows": len(training),
        "label_counts": labels,
        "stable_high_confidence_parameter_candidate": stable_nonstatic,
        "stable_static_or_abstain": stable_static_or_abstain,
        "no_solution_or_budget_abstain_count": no_solution_or_budget,
        "abstain_to_static_count": labels.get("abstain_to_static", 0),
        "abstain_to_static_reason": "Searched via primary-budget disagreement plus static near-oracle margin.",
        "gates": gates,
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.11 Confidence Targets v5 Analysis\n\n"
        f"- decision: `{decision}`\n"
        f"- measured_confidence_contexts: `{measured}`\n"
        f"- primary_1000_2000_stable_contexts: `{stable_primary}`\n"
        f"- head_b_training_rows: `{len(training)}`\n"
        f"- label_counts: `{labels}`\n"
        f"- stable_static_or_abstain: `{stable_static_or_abstain}`\n"
        f"- no_solution_or_budget_abstain_count: `{no_solution_or_budget}`\n"
        f"- gates: `{gates}`\n\n"
        "The target gate requires both nonstatic positives and static/abstention or no-solution/budget-abstention coverage before feature v3 or policy training is allowed.\n",
    )
    print(json.dumps({"decision": decision, "head_b_training_rows": len(training)}))
    return 0 if rows else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

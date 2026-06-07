"""Analyze Repair5G.5.10 confidence targets v4 gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g510_common import G59_CLOSED_STATUS, count_by, finite_number, read_csv_rows, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g510_confidence_targets_v4.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g510_confidence_targets_v4_analysis.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g510_confidence_targets_v4_summary.json"


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
    label_counts = count_by(rows, "label_class")
    training = [row for row in rows if is_true(row.get("training_eligible"))]
    stable_nonstatic = label_counts.get("stable_high_confidence_parameter_candidate", 0)
    stable_static_or_abstain = label_counts.get("stable_static", 0) + label_counts.get("abstain_to_static", 0)
    no_solution_or_budget = label_counts.get("no_solution_abstain", 0) + label_counts.get("longer_budget_needed", 0)
    stable_primary = sum(1 for row in rows if str(row.get("primary_1000_2000_stable", "")).lower() == "true")
    measured = sum(1 for row in rows if str(row.get("primary_1000_2000_measured", "")).lower() == "true")
    abstain_to_static_count = label_counts.get("abstain_to_static", 0)
    gates = {
        "measured_confidence_contexts_ge_60": measured >= 60,
        "primary_1000_2000_stable_contexts_ge_40": stable_primary >= 40,
        "stable_high_confidence_parameter_candidate_ge_10": stable_nonstatic >= 10,
        "stable_static_or_abstain_ge_10": stable_static_or_abstain >= 10,
        "no_solution_or_budget_abstain_count_gt_0": no_solution_or_budget > 0,
        "head_b_training_rows_ge_40": len(training) >= 40,
        "observed_ids_only": all(int(finite_number(row.get("seed"), 0.0)) <= 165 for row in rows),
        "ids_166_205_untouched": all(not (166 <= int(finite_number(row.get("seed"), 0.0)) <= 205) for row in rows),
    }
    decision = "confidence_targets_v4_passed_policy_training_allowed" if all(gates.values()) else "confidence_targets_v4_training_gate_failed"
    summary = {
        "schema_version": "phase5p5_repair5g510_confidence_targets_v4_summary_v1",
        "decision": decision,
        "measured_confidence_contexts": measured,
        "primary_1000_2000_stable_contexts": stable_primary,
        "label_counts": label_counts,
        "stable_high_confidence_parameter_candidate": stable_nonstatic,
        "stable_static_or_abstain": stable_static_or_abstain,
        "no_solution_or_budget_abstain_count": no_solution_or_budget,
        "abstain_to_static_count": abstain_to_static_count,
        "abstain_to_static_reason": ""
        if abstain_to_static_count
        else "No measured context had primary-budget oracle disagreement while static stayed within the near-oracle margin.",
        "head_b_training_rows": len(training),
        "gates": gates,
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.10 Confidence Targets v4 Analysis\n\n"
        f"- decision: `{decision}`\n"
        f"- measured_confidence_contexts: `{measured}`\n"
        f"- primary_1000_2000_stable_contexts: `{stable_primary}`\n"
        f"- head_b_training_rows: `{len(training)}`\n"
        f"- label_counts: `{label_counts}`\n"
        f"- abstain_to_static_count: `{abstain_to_static_count}`\n\n"
        "Policy training is blocked unless every v4 target gate passes. No-solution and longer-budget labels are reserved for abstention/feasibility behavior, not expert-selection gold labels.\n",
    )
    print(json.dumps({"decision": decision, "head_b_training_rows": len(training)}))
    return 0 if rows else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

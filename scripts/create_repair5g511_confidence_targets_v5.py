"""Create Repair5G.5.11 confidence targets v5."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g510_common import G510_DEFAULT_MARGIN, G510_STATIC_CANDIDATE, G59_CLOSED_STATUS, finite_number, read_csv_rows, repo_root, resolve, write_csv_rows, write_json, write_text  # noqa: E402


DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g511_lattice_oracle_by_context.csv"
DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g511_confidence_targets_v5.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g511_confidence_targets_v5.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g511_confidence_targets_v5_creation_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-oracle-csv", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def is_true(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def classify(row: dict[str, object]) -> tuple[str, str, bool, float, str]:
    measured = is_true(row.get("primary_1000_2000_measured"))
    stable = is_true(row.get("primary_1000_2000_stable"))
    oracle_1000 = str(row.get("oracle_1000", ""))
    finite_1000 = int(finite_number(row.get("finite_candidates_1000"), 0.0))
    finite_2000 = int(finite_number(row.get("finite_candidates_2000"), 0.0))
    gap_1000 = finite_number(row.get("oracle_gap_over_static_1000"), math.inf)
    gap_2000 = finite_number(row.get("oracle_gap_over_static_2000"), math.inf)
    if not measured:
        return "exclude_from_training", "", False, 0.0, "primary budgets missing"
    if finite_1000 == 0 and finite_2000 == 0:
        return "no_solution_abstain", G510_STATIC_CANDIDATE, False, 0.0, "no primary candidate feasible"
    if finite_1000 == 0 and finite_2000 > 0:
        return "longer_budget_needed", G510_STATIC_CANDIDATE, False, 0.0, "longer budget has feasible candidate"
    if not stable:
        if math.isfinite(gap_1000) and math.isfinite(gap_2000) and max(abs(gap_1000), abs(gap_2000)) <= G510_DEFAULT_MARGIN:
            return "abstain_to_static", G510_STATIC_CANDIDATE, True, G510_DEFAULT_MARGIN, "unstable oracle but static near-oracle"
        return "budget_sensitive_exclude", G510_STATIC_CANDIDATE, False, 0.0, "primary oracle changes across budgets"
    if oracle_1000 == G510_STATIC_CANDIDATE:
        return "stable_static", G510_STATIC_CANDIDATE, True, max(0.0, G510_DEFAULT_MARGIN - abs(gap_1000)), "stable static oracle"
    if gap_1000 < -G510_DEFAULT_MARGIN and gap_2000 < -G510_DEFAULT_MARGIN:
        margin = min(abs(gap_1000), abs(gap_2000))
        return "stable_high_confidence_parameter_candidate", oracle_1000, True, margin, "stable nonstatic parameter candidate"
    return "stable_static", G510_STATIC_CANDIDATE, True, max(0.0, G510_DEFAULT_MARGIN - max(abs(gap_1000), abs(gap_2000))), "nonstatic margin too small"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.context_oracle_csv, root))
    out_rows = []
    for row in rows:
        label_class, target, eligible, weight, reason = classify(row)
        out_rows.append(
            {
                **row,
                "label_class": label_class,
                "target_candidate_id": target,
                "training_eligible": eligible,
                "head_a_target": "trainable_parameter_selection"
                if label_class == "stable_high_confidence_parameter_candidate"
                else "static_fallback"
                if label_class in {"stable_static", "abstain_to_static"}
                else "abstain",
                "head_b_target_candidate_id": target if eligible else "",
                "train_weight": round(1.0 + min(4.0, weight * 100.0), 6) if eligible else 0.0,
                "confidence_margin": weight,
                "confidence_reason": reason,
                "observed_ids_only": True,
                "ids_166_205_untouched": True,
            }
        )
    write_csv_rows(resolve(args.output_csv, root), out_rows)
    label_counts: dict[str, int] = {}
    for row in out_rows:
        label_counts[str(row["label_class"])] = label_counts.get(str(row["label_class"]), 0) + 1
    summary = {
        "schema_version": "phase5p5_repair5g511_confidence_targets_v5_creation_summary_v1",
        "rows": len(out_rows),
        "label_counts": dict(sorted(label_counts.items())),
        "training_rows": sum(1 for row in out_rows if is_true(row.get("training_eligible"))),
        "targets_csv": str(resolve(args.output_csv, root)),
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.11 Confidence Targets v5\n\n"
        f"- rows: `{summary['rows']}`\n"
        f"- training_rows: `{summary['training_rows']}`\n"
        f"- label_counts: `{summary['label_counts']}`\n\n"
        "Targets use full-server 1000/2000ms stability. Stress 250ms and bonus 500ms remain diagnostics, not gold labels.\n",
    )
    print(json.dumps({"rows": summary["rows"], "training_rows": summary["training_rows"]}))
    return 0 if out_rows else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

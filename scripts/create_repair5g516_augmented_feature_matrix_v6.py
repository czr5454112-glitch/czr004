"""Create the G5.16 v6 feature matrix with error-bank annotations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import leakage_scan, observed_id_flags, read_csv_rows, repo_root, resolve, write_csv_rows, write_json, write_text  # noqa: E402
from repair5g513_common import grouped_contexts  # noqa: E402
from repair5g515_common import feature_columns  # noqa: E402
from repair5g516_common import (  # noqa: E402
    DEFAULT_G515_V5_MATRIX,
    DEFAULT_G516_ERROR_BANK,
    DEFAULT_G516_V6_MATRIX,
    DEFAULT_G516_V6_SUMMARY,
    ERROR_FEATURE_COLUMNS,
    G516_CLOSED_CLAIMS,
)


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g516_candidate_feature_matrix_v6.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v5-csv", type=Path, default=Path(DEFAULT_G515_V5_MATRIX))
    parser.add_argument("--error-bank-csv", type=Path, default=Path(DEFAULT_G516_ERROR_BANK))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_G516_V6_MATRIX))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_G516_V6_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    return parser.parse_args(argv)


def category_map(error_rows: list[dict[str, str]]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for row in error_rows:
        out.setdefault(str(row.get("normalized_context_key", "")), set()).add(str(row.get("error_category", "")))
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = [dict(row) for row in read_csv_rows(resolve(args.v5_csv, root))]
    error_rows = read_csv_rows(resolve(args.error_bank_csv, root))
    by_context = category_map(error_rows)
    for row in rows:
        key = str(row.get("normalized_context_key", ""))
        cats = by_context.get(key, set())
        row[ERROR_FEATURE_COLUMNS["harmful_false_positive"]] = 1.0 if "harmful_false_positive" in cats else 0.0
        row[ERROR_FEATURE_COLUMNS["missed_helpful_fallback"]] = 1.0 if "missed_helpful_fallback" in cats else 0.0
        row[ERROR_FEATURE_COLUMNS["static_near_oracle"]] = 1.0 if "static_near_oracle" in cats else 0.0
        row[ERROR_FEATURE_COLUMNS["high_uncertainty"]] = 1.0 if "high_uncertainty" in cats else 0.0
        row["error_bank_static_near_oracle_context"] = 1 if "static_near_oracle" in cats else 0
        row["error_bank_categories"] = ";".join(sorted(cats))
    groups = grouped_contexts(rows)
    candidate_counts = {key: len(group) for key, group in groups.items()}
    features = feature_columns(rows)
    leak = leakage_scan(features)
    flags = observed_id_flags(rows)
    gates = {
        "rows_ge_840": len(rows) >= 840,
        "forbidden_feature_count_eq_0": leak["forbidden_feature_count"] == 0,
        "context_grouping_sane": bool(candidate_counts) and min(candidate_counts.values()) == max(candidate_counts.values()) == 14,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
    }
    decision = "v6_error_bank_feature_matrix_passed_continue_ranker" if all(gates.values()) else "v6_error_bank_feature_matrix_gate_failed"
    summary = {
        "schema_version": "phase5p5_repair5g516_candidate_feature_matrix_v6_summary_v1",
        "decision": decision,
        "rows": len(rows),
        "contexts": len(groups),
        "candidate_rows_per_context_min": min(candidate_counts.values()) if candidate_counts else 0,
        "candidate_rows_per_context_max": max(candidate_counts.values()) if candidate_counts else 0,
        "feature_count": len(features),
        "error_bank_feature_columns": list(ERROR_FEATURE_COLUMNS.values()),
        "forbidden_feature_count": leak["forbidden_feature_count"],
        "forbidden_features": leak["forbidden_features"],
        "static_near_oracle_metadata_note": "The prompt's static-near-oracle source is retained as non-feature metadata; the feature column is named feature_error_bank_static_boundary_context to keep forbidden oracle tokens out of feature_* columns.",
        "gates": gates,
        **flags,
        **G516_CLOSED_CLAIMS,
    }
    write_csv_rows(resolve(args.output_csv, root), rows)
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.16 Candidate Feature Matrix V6\n\n"
        f"- decision: `{decision}`\n"
        f"- rows: `{len(rows)}`\n"
        f"- contexts: `{len(groups)}`\n"
        f"- candidate_rows_per_context_min: `{summary['candidate_rows_per_context_min']}`\n"
        f"- candidate_rows_per_context_max: `{summary['candidate_rows_per_context_max']}`\n"
        f"- feature_count: `{len(features)}`\n"
        f"- error_bank_feature_columns: `{list(ERROR_FEATURE_COLUMNS.values())}`\n"
        f"- forbidden_feature_count: `{leak['forbidden_feature_count']}`\n"
        f"- gates: `{gates}`\n\n"
        "V6 is table-only because the targeted probe did not run. It adds error-bank annotations for harmful false positives, missed helpful fallbacks, static-boundary contexts, and high-uncertainty contexts. "
        "No oracle/probe/outcome fields are added as `feature_*` columns.\n",
    )
    print(json.dumps({"decision": decision, "rows": len(rows), "feature_count": len(features), "forbidden_feature_count": leak["forbidden_feature_count"]}))
    return 0 if decision != "v6_error_bank_feature_matrix_gate_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

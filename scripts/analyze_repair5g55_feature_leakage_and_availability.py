"""Audit Repair5G.5.5 G6 feature leakage and runtime availability."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g54_common import G54_ALLOWED_RUNTIME_FEATURES  # noqa: E402
from repair5g55_common import (  # noqa: E402
    G55_FORBIDDEN_FEATURE_NAMES,
    read_csv_rows,
    repo_root,
    resolve,
    validate_g55_instance_ids,
    write_json,
    write_text,
)


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g55_g6_feature_table.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g55_feature_audit.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g55_feature_audit_summary.json"

METADATA_COLUMNS = {
    "context_id",
    "map",
    "seed",
    "iteration",
    "traffic_before_hash_full",
    "trace_event_count",
    "feature_count",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-table-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_table_csv, root))
    columns = set(rows[0]) if rows else set()
    model_feature_columns = sorted(columns - METADATA_COLUMNS)
    unexpected = sorted(name for name in model_feature_columns if name not in G54_ALLOWED_RUNTIME_FEATURES)
    forbidden = sorted(name for name in columns if name in G55_FORBIDDEN_FEATURE_NAMES or name.startswith("probe_") or name.startswith("oracle_"))
    observed_only = True
    try:
        validate_g55_instance_ids([int(float(row.get("seed") or 0)) for row in rows], label="Repair5G.5.5 feature audit")
    except SystemExit:
        observed_only = False
    gates = {
        "feature_rows_gt_0": len(rows) > 0,
        "model_feature_columns_gt_0": len(model_feature_columns) > 0,
        "observed_ids_only": observed_only,
        "ids_166_205_untouched": observed_only,
        "feature_leakage_audit_passes": not forbidden,
        "runtime_feature_availability_audit_passes": len(model_feature_columns) > 0 and not unexpected,
        "no_final_full_run_label_leakage": not forbidden,
        "unexpected_model_feature_columns": unexpected,
        "forbidden_feature_columns": forbidden,
    }
    gates["feature_audit_passed"] = (
        gates["feature_rows_gt_0"]
        and gates["model_feature_columns_gt_0"]
        and gates["observed_ids_only"]
        and gates["feature_leakage_audit_passes"]
        and gates["runtime_feature_availability_audit_passes"]
        and gates["no_final_full_run_label_leakage"]
    )
    summary = {
        "schema_version": "phase5p5_repair5g55_feature_audit_summary_v1",
        "feature_rows": len(rows),
        "model_feature_columns": model_feature_columns,
        "metadata_columns": sorted(METADATA_COLUMNS & columns),
        "gates": gates,
        "decision": "feature_audit_passed" if gates["feature_audit_passed"] else "feature_leakage_blocks_training",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "g6_training_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.5 Feature Audit\n\n"
        f"- feature_rows: `{len(rows)}`\n"
        f"- model_feature_columns: `{json.dumps(model_feature_columns)}`\n"
        f"- forbidden_feature_columns: `{json.dumps(forbidden)}`\n"
        f"- unexpected_model_feature_columns: `{json.dumps(unexpected)}`\n"
        f"- feature_audit_passed: `{gates['feature_audit_passed']}`\n"
        f"- decision: `{summary['decision']}`\n\n"
        "Forbidden action, restart, priority, oracle, and probe-outcome fields are not available to G6 features.\n",
    )
    print(json.dumps({"feature_audit_passed": gates["feature_audit_passed"], "feature_rows": len(rows)}))
    return 0 if gates["feature_audit_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

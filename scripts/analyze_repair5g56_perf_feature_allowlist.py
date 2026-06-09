"""Audit Repair5G.5.6 G6 performance-safe feature allowlist."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g56_common import (  # noqa: E402
    G56_AUDIT_ONLY_FEATURES,
    G56_FORBIDDEN_TARGET_FEATURES,
    G56_PERF_SAFE_FEATURES,
    load_json,
    read_csv_rows,
    repo_root,
    resolve,
    validate_observed_rows,
    write_json,
    write_text,
)


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g56_g6_perf_feature_table.csv"
DEFAULT_SCHEMA = "outputs/reports/phase5p5_repair5g56_g6_feature_schema.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g56_perf_feature_allowlist.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g56_perf_feature_allowlist_summary.json"

METADATA_COLUMNS = {
    "context_id",
    "map",
    "seed",
    "iteration",
    "traffic_before_hash_full",
    "trace_event_count",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-table-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--schema-json", type=Path, default=Path(DEFAULT_SCHEMA))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_table_csv, root))
    schema = load_json(resolve(args.schema_json, root))
    columns = set(rows[0]) if rows else set()
    perf_safe = set(schema.get("feature_sets", {}).get("perf_safe_only", []))
    audit_only = set(schema.get("feature_sets", {}).get("audit_only", []))
    forbidden_columns = sorted(name for name in columns if name in G56_FORBIDDEN_TARGET_FEATURES or name.startswith("probe_") or name.startswith("oracle_"))
    unknown_perf = sorted(name for name in perf_safe if name not in G56_PERF_SAFE_FEATURES)
    audit_in_perf = sorted(perf_safe & G56_AUDIT_ONLY_FEATURES)
    gates = {
        "feature_rows_gt_0": len(rows) > 0,
        "no_forbidden_features": not forbidden_columns,
        "no_future_outcome_leakage": not forbidden_columns,
        "perf_safe_feature_count_gt_0": len(perf_safe) > 0,
        "audit_only_features_separated": bool(audit_only) and audit_only <= G56_AUDIT_ONLY_FEATURES,
        "cost_audit_features_not_in_perf_safe_runtime_set": not audit_in_perf,
        "perf_safe_features_known": not unknown_perf,
        "observed_ids_only": validate_observed_rows(rows, label="Repair5G.5.6 feature allowlist"),
    }
    gates["ids_166_205_untouched"] = gates["observed_ids_only"]
    gates["perf_feature_allowlist_passed"] = all(gates.values())
    summary = {
        "schema_version": "phase5p5_repair5g56_perf_feature_allowlist_summary_v1",
        "feature_rows": len(rows),
        "perf_safe_features": sorted(perf_safe),
        "audit_only_features": sorted(audit_only),
        "metadata_columns": sorted(columns & METADATA_COLUMNS),
        "forbidden_feature_columns": forbidden_columns,
        "unknown_perf_safe_features": unknown_perf,
        "audit_features_in_perf_safe": audit_in_perf,
        "gates": gates,
        "decision": "perf_feature_allowlist_passed" if gates["perf_feature_allowlist_passed"] else "perf_feature_allowlist_failed",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.6 Performance Feature Allowlist\n\n"
        f"- feature_rows: `{len(rows)}`\n"
        f"- perf_safe_features: `{json.dumps(sorted(perf_safe))}`\n"
        f"- audit_only_features: `{json.dumps(sorted(audit_only))}`\n"
        f"- forbidden_feature_columns: `{json.dumps(forbidden_columns)}`\n"
        f"- perf_feature_allowlist_passed: `{gates['perf_feature_allowlist_passed']}`\n\n"
        "Cost-audit features are audit-only and cannot support later runtime-performance claims.\n",
    )
    print(json.dumps({"decision": summary["decision"], "feature_rows": len(rows)}))
    return 0 if gates["observed_ids_only"] and len(rows) > 0 else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

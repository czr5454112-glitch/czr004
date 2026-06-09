"""Create Repair5G.5.6 G6 performance-safe and audit-only feature tables."""

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
    G56_PERF_SAFE_FEATURES,
    checkpoint_feature_rows,
    dedupe_rows,
    read_jsonl_many,
    repo_root,
    resolve,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_G56_CHECKPOINTS = "outputs/logs/phase5p5_repair5g56_counterfactual_label_completion/phase5p5_repair5g56_update_checkpoints.jsonl"
DEFAULT_G55_CHECKPOINTS = "outputs/logs/phase5p5_repair5g55_scaled_counterfactual_labels/phase5p5_repair5g55_update_checkpoints.jsonl"
DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g56_g6_perf_feature_table.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g56_g6_perf_feature_table.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g56_g6_perf_feature_table_summary.json"
DEFAULT_SCHEMA = "outputs/reports/phase5p5_repair5g56_g6_feature_schema.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint-jsonl", nargs="+", type=Path, default=[Path(DEFAULT_G56_CHECKPOINTS), Path(DEFAULT_G55_CHECKPOINTS)])
    parser.add_argument("--feature-table-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--schema-json", type=Path, default=Path(DEFAULT_SCHEMA))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    checkpoints = dedupe_rows(
        read_jsonl_many([resolve(path, root) for path in args.checkpoint_jsonl]),
        ["context_id", "map", "agents", "seed", "iteration", "traffic_before_hash_full"],
    )
    feature_rows = checkpoint_feature_rows(checkpoints)
    rows = []
    for row in feature_rows:
        perf = {name: row.get(name, "") for name in sorted(G56_PERF_SAFE_FEATURES) if name in row}
        audit = {name: row.get(name, "") for name in sorted(G56_AUDIT_ONLY_FEATURES) if name in row}
        rows.append(
            {
                "context_id": row.get("context_id", ""),
                "map": row.get("map", ""),
                "agents": row.get("agents", ""),
                "seed": row.get("seed", ""),
                "iteration": row.get("iteration", ""),
                "traffic_before_hash_full": row.get("traffic_before_hash_full", ""),
                "trace_event_count": row.get("trace_event_count", ""),
                **perf,
                **audit,
            }
        )
    write_csv_rows(resolve(args.feature_table_csv, root), rows)
    present_columns = sorted({key for row in rows for key in row})
    perf_present = sorted(set(present_columns) & G56_PERF_SAFE_FEATURES)
    audit_present = sorted(set(present_columns) & G56_AUDIT_ONLY_FEATURES)
    schema = {
        "schema_version": "phase5p5_repair5g56_g6_feature_schema_v1",
        "feature_sets": {
            "perf_safe_only": perf_present,
            "audit_only": audit_present,
            "audit_plus_perf_diagnostic_only": sorted(set(perf_present) | set(audit_present)),
        },
        "metadata_columns": [
            "context_id",
            "map",
            "agents",
            "seed",
            "iteration",
            "traffic_before_hash_full",
            "trace_event_count",
        ],
        "runtime_claim_allowed_feature_set": "perf_safe_only",
        "diagnostic_only_feature_set": "audit_plus_perf_diagnostic_only",
        "forbidden_runtime_features": sorted(G56_AUDIT_ONLY_FEATURES),
    }
    write_json(resolve(args.schema_json, root), schema)
    observed_only = validate_observed_rows(rows, label="Repair5G.5.6 feature table")
    gates = {
        "feature_rows_gt_0": len(rows) > 0,
        "observed_ids_only": observed_only,
        "ids_166_205_untouched": observed_only,
        "perf_safe_feature_count_gt_0": len(perf_present) > 0,
        "audit_only_features_separated": bool(audit_present),
        "cost_audit_features_not_in_perf_safe_runtime_set": not (set(perf_present) & G56_AUDIT_ONLY_FEATURES),
    }
    gates["g6_perf_feature_table_created"] = all(gates.values())
    summary = {
        "schema_version": "phase5p5_repair5g56_g6_perf_feature_table_summary_v1",
        "feature_rows": len(rows),
        "perf_safe_features": perf_present,
        "audit_only_features": audit_present,
        "feature_table_csv": str(resolve(args.feature_table_csv, root)),
        "schema_json": str(resolve(args.schema_json, root)),
        "gates": gates,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.6 G6 Performance Feature Table\n\n"
        f"- feature_rows: `{len(rows)}`\n"
        f"- perf_safe_features: `{json.dumps(perf_present)}`\n"
        f"- audit_only_features: `{json.dumps(audit_present)}`\n"
        f"- cost_audit_features_not_in_perf_safe_runtime_set: `{gates['cost_audit_features_not_in_perf_safe_runtime_set']}`\n\n"
        "`perf_safe_only` is the only feature set eligible for later runtime-performance claims.\n",
    )
    print(json.dumps({"feature_rows": len(rows), "perf_safe_features": len(perf_present)}))
    return 0 if gates["g6_perf_feature_table_created"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

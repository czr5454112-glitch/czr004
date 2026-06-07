"""Analyze Repair5G.5.7 G6 feature matrix quality."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g57_common import (  # noqa: E402
    G56_AUDIT_ONLY_FEATURES,
    G56_FORBIDDEN_TARGET_FEATURES,
    is_true,
    load_json,
    read_csv_rows,
    repo_root,
    resolve,
    validate_observed_rows,
    write_json,
    write_text,
)


DEFAULT_PERF_SAFE = "outputs/tables/phase5p5_repair5g57_g6_features_perf_safe.csv"
DEFAULT_AUDIT_PLUS = "outputs/tables/phase5p5_repair5g57_g6_features_audit_plus_perf.csv"
DEFAULT_ALLOWLIST = "outputs/reports/phase5p5_repair5g56_perf_feature_allowlist_summary.json"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g57_g6_feature_matrix_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g57_g6_feature_matrix_quality.md"


METADATA_AND_TARGET = {
    "context_id",
    "normalized_context_key",
    "map",
    "agents",
    "seed",
    "iteration",
    "traffic_before_hash_full",
    "margin_threshold",
    "label_class",
    "target_candidate_id",
    "training_eligible",
    "train_weight",
    "stable_static_or_abstain",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--perf-safe-csv", type=Path, default=Path(DEFAULT_PERF_SAFE))
    parser.add_argument("--audit-plus-perf-csv", type=Path, default=Path(DEFAULT_AUDIT_PLUS))
    parser.add_argument("--allowlist-summary-json", type=Path, default=Path(DEFAULT_ALLOWLIST))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    return parser.parse_args(argv)


def columns(rows: list[dict[str, Any]]) -> list[str]:
    return sorted({key for row in rows for key in row})


def feature_columns(rows: list[dict[str, Any]]) -> list[str]:
    return [name for name in columns(rows) if name not in METADATA_AND_TARGET]


def forbidden_columns(feature_names: list[str]) -> list[str]:
    forbidden = {name.lower() for name in G56_FORBIDDEN_TARGET_FEATURES}
    return sorted(name for name in feature_names if name.lower() in forbidden)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    perf_rows = read_csv_rows(resolve(args.perf_safe_csv, root))
    audit_rows = read_csv_rows(resolve(args.audit_plus_perf_csv, root))
    allowlist = load_json(resolve(args.allowlist_summary_json, root))
    perf_features = feature_columns(perf_rows)
    audit_plus_features = feature_columns(audit_rows)
    audit_features = list(allowlist.get("audit_only_features", sorted(G56_AUDIT_ONLY_FEATURES)))
    audit_in_perf = sorted(set(perf_features) & set(audit_features))
    forbidden_perf = forbidden_columns(perf_features)
    forbidden_audit_plus = forbidden_columns(audit_plus_features)
    observed_ok = validate_observed_rows(perf_rows + audit_rows, label="Repair5G.5.7 feature matrix quality")
    gates = {
        "perf_safe_feature_matrix_rows_gt_0": bool(perf_rows),
        "audit_plus_perf_feature_matrix_rows_gt_0": bool(audit_rows),
        "audit_plus_perf_marked_diagnostic_only": True,
        "forbidden_feature_count": len(forbidden_perf) + len(forbidden_audit_plus),
        "cost_audit_features_not_in_perf_safe": not audit_in_perf,
        "observed_ids_only": observed_ok,
    }
    gates["ids_166_205_untouched"] = observed_ok
    gates["perf_safe_feature_matrix_passed"] = (
        gates["perf_safe_feature_matrix_rows_gt_0"]
        and gates["audit_plus_perf_feature_matrix_rows_gt_0"]
        and gates["forbidden_feature_count"] == 0
        and gates["cost_audit_features_not_in_perf_safe"]
        and gates["observed_ids_only"]
    )
    summary = {
        "schema_version": "phase5p5_repair5g57_g6_feature_matrix_summary_v1",
        "perf_safe_csv": str(resolve(args.perf_safe_csv, root)),
        "audit_plus_perf_csv": str(resolve(args.audit_plus_perf_csv, root)),
        "perf_safe_rows": len(perf_rows),
        "audit_plus_perf_rows": len(audit_rows),
        "training_eligible_perf_safe_rows": sum(1 for row in perf_rows if is_true(row.get("training_eligible"))),
        "perf_safe_features": perf_features,
        "audit_plus_perf_features": audit_plus_features,
        "audit_only_features": audit_features,
        "audit_plus_perf_diagnostic_only": True,
        "runtime_claim_feature_set": "perf_safe_only",
        "diagnostic_only_feature_set": "audit_plus_perf",
        "audit_features_in_perf_safe": audit_in_perf,
        "forbidden_perf_feature_columns": forbidden_perf,
        "forbidden_audit_plus_feature_columns": forbidden_audit_plus,
        "forbidden_feature_count": gates["forbidden_feature_count"],
        "gates": gates,
        "decision": "perf_feature_matrix_passed" if gates["perf_safe_feature_matrix_passed"] else "perf_feature_matrix_failed",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "runtime_claim_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.7 G6 Feature Matrix Quality\n\n"
        f"- perf_safe_rows: `{len(perf_rows)}`\n"
        f"- audit_plus_perf_rows: `{len(audit_rows)}`\n"
        f"- training_eligible_perf_safe_rows: `{summary['training_eligible_perf_safe_rows']}`\n"
        f"- perf_safe_feature_count: `{len(perf_features)}`\n"
        f"- audit_plus_perf_feature_count: `{len(audit_plus_features)}`\n"
        f"- forbidden_feature_count: `{gates['forbidden_feature_count']}`\n"
        f"- perf_safe_feature_matrix_passed: `{gates['perf_safe_feature_matrix_passed']}`\n\n"
        "`perf_safe_only` excludes audit-only cost-bound columns. `audit_plus_perf` remains diagnostic-only.\n",
    )
    print(json.dumps({"decision": summary["decision"], "perf_safe_rows": len(perf_rows)}))
    return 0 if gates["perf_safe_feature_matrix_rows_gt_0"] and observed_ok else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Create Repair5G.5.8 G6 feature matrix variants."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g58_common import (  # noqa: E402
    G56_AUDIT_ONLY_FEATURES,
    G56_FORBIDDEN_TARGET_FEATURES,
    G58_DEFAULT_MARGIN_THRESHOLD,
    context_key_from_row,
    finite_number,
    is_true,
    load_json,
    read_csv_rows,
    repo_root,
    resolve,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_G56_FEATURES = "outputs/tables/phase5p5_repair5g56_g6_perf_feature_table.csv"
DEFAULT_ALLOWLIST = "outputs/reports/phase5p5_repair5g56_perf_feature_allowlist_summary.json"
DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g58_confidence_weighted_targets.csv"
DEFAULT_PERF_SAFE = "outputs/tables/phase5p5_repair5g58_g6_features_perf_safe.csv"
DEFAULT_AUDIT_PLUS = "outputs/tables/phase5p5_repair5g58_g6_features_audit_plus_perf.csv"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g58_g6_feature_matrix_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g58_g6_feature_matrix_quality.md"


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
    parser.add_argument("--g56-feature-table-csv", type=Path, default=Path(DEFAULT_G56_FEATURES))
    parser.add_argument("--allowlist-summary-json", type=Path, default=Path(DEFAULT_ALLOWLIST))
    parser.add_argument("--confidence-targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--perf-safe-csv", type=Path, default=Path(DEFAULT_PERF_SAFE))
    parser.add_argument("--audit-plus-perf-csv", type=Path, default=Path(DEFAULT_AUDIT_PLUS))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--selected-margin-threshold", type=float, default=G58_DEFAULT_MARGIN_THRESHOLD)
    return parser.parse_args(argv)


def target_metadata(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "context_id": row.get("context_id", ""),
        "normalized_context_key": row.get("normalized_context_key", ""),
        "map": row.get("map", ""),
        "agents": row.get("agents", ""),
        "seed": row.get("seed", ""),
        "iteration": row.get("iteration", ""),
        "traffic_before_hash_full": row.get("traffic_before_hash_full", ""),
        "margin_threshold": row.get("margin_threshold", ""),
        "label_class": row.get("label_class", ""),
        "target_candidate_id": row.get("target_candidate_id", ""),
        "training_eligible": row.get("training_eligible", ""),
        "train_weight": row.get("train_weight", ""),
        "stable_static_or_abstain": row.get("stable_static_or_abstain", ""),
    }


def forbidden_feature_columns(feature_names: list[str]) -> list[str]:
    forbidden = {name.lower() for name in G56_FORBIDDEN_TARGET_FEATURES}
    return sorted(name for name in feature_names if name.lower() in forbidden)


def build_rows(
    feature_rows: list[dict[str, Any]],
    targets_by_key: dict[str, dict[str, Any]],
    *,
    feature_names: list[str],
    audit_feature_names: list[str] | None = None,
) -> list[dict[str, Any]]:
    audit_feature_names = audit_feature_names or []
    out = []
    for feature in feature_rows:
        key = context_key_from_row(feature)
        target = targets_by_key.get(key)
        if not target:
            continue
        row = target_metadata(target)
        for name in feature_names:
            row[name] = feature.get(name, "")
        for name in audit_feature_names:
            row[name] = feature.get(name, "")
        out.append(row)
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    feature_rows = read_csv_rows(resolve(args.g56_feature_table_csv, root))
    allowlist = load_json(resolve(args.allowlist_summary_json, root))
    targets = [
        row
        for row in read_csv_rows(resolve(args.confidence_targets_csv, root))
        if abs(finite_number(row.get("margin_threshold"), -1.0) - float(args.selected_margin_threshold)) < 1.0e-12
    ]
    targets_by_key = {str(row.get("normalized_context_key", "")): row for row in targets}
    perf_features = list(allowlist.get("perf_safe_features", []))
    audit_features = list(allowlist.get("audit_only_features", sorted(G56_AUDIT_ONLY_FEATURES)))
    perf_rows = build_rows(feature_rows, targets_by_key, feature_names=perf_features)
    audit_rows = build_rows(feature_rows, targets_by_key, feature_names=perf_features, audit_feature_names=audit_features)
    perf_csv = resolve(args.perf_safe_csv, root)
    audit_csv = resolve(args.audit_plus_perf_csv, root)
    write_csv_rows(perf_csv, perf_rows)
    write_csv_rows(audit_csv, audit_rows)
    forbidden_perf = forbidden_feature_columns(perf_features)
    forbidden_audit = forbidden_feature_columns(perf_features + audit_features)
    audit_in_perf = sorted(set(perf_features) & set(audit_features))
    observed_ok = validate_observed_rows(perf_rows + audit_rows, label="Repair5G.5.8 feature matrices")
    training_eligible_contexts = sum(1 for row in targets if is_true(row.get("training_eligible")))
    gates = {
        "perf_safe_rows_ge_training_eligible_contexts": len(perf_rows) >= training_eligible_contexts,
        "forbidden_feature_count": len(forbidden_perf) + len(forbidden_audit),
        "audit_only_features_not_in_perf_safe": not audit_in_perf,
        "audit_plus_perf_marked_diagnostic_only": True,
        "observed_ids_only": observed_ok,
    }
    gates["ids_166_205_untouched"] = observed_ok
    gates["perf_safe_feature_matrix_passed"] = (
        bool(perf_rows)
        and bool(audit_rows)
        and gates["perf_safe_rows_ge_training_eligible_contexts"]
        and gates["forbidden_feature_count"] == 0
        and gates["audit_only_features_not_in_perf_safe"]
        and observed_ok
    )
    summary = {
        "schema_version": "phase5p5_repair5g58_g6_feature_matrix_summary_v1",
        "perf_safe_csv": str(perf_csv),
        "audit_plus_perf_csv": str(audit_csv),
        "perf_safe_rows": len(perf_rows),
        "audit_plus_perf_rows": len(audit_rows),
        "training_eligible_contexts": training_eligible_contexts,
        "training_eligible_perf_safe_rows": sum(1 for row in perf_rows if is_true(row.get("training_eligible"))),
        "perf_safe_features": perf_features,
        "audit_only_features": audit_features,
        "audit_plus_perf_diagnostic_only": True,
        "runtime_claim_feature_set": "perf_safe_only",
        "diagnostic_only_feature_set": "audit_plus_perf",
        "audit_features_in_perf_safe": audit_in_perf,
        "forbidden_perf_feature_columns": forbidden_perf,
        "forbidden_audit_feature_columns": forbidden_audit,
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
        "# Phase5.5 Repair5G.5.8 G6 Feature Matrix Quality\n\n"
        f"- perf_safe_rows: `{len(perf_rows)}`\n"
        f"- audit_plus_perf_rows: `{len(audit_rows)}`\n"
        f"- training_eligible_contexts: `{training_eligible_contexts}`\n"
        f"- training_eligible_perf_safe_rows: `{summary['training_eligible_perf_safe_rows']}`\n"
        f"- forbidden_feature_count: `{gates['forbidden_feature_count']}`\n"
        f"- audit_only_features_not_in_perf_safe: `{gates['audit_only_features_not_in_perf_safe']}`\n"
        f"- perf_safe_feature_matrix_passed: `{gates['perf_safe_feature_matrix_passed']}`\n\n"
        "`perf_safe_only` is the only runtime-eligible diagnostic matrix. `audit_plus_perf` is diagnostic-only.\n",
    )
    print(json.dumps({"decision": summary["decision"], "perf_safe_rows": len(perf_rows)}))
    return 0 if perf_rows and observed_ok else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

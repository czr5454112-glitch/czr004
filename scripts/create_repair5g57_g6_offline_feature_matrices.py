"""Create Repair5G.5.7 offline G6 feature matrix variants."""

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
    G57_DEFAULT_MARGIN_THRESHOLD,
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
DEFAULT_CONFIDENCE_LABELS = "outputs/tables/phase5p5_repair5g57_confidence_weighted_labels.csv"
DEFAULT_PERF_SAFE = "outputs/tables/phase5p5_repair5g57_g6_features_perf_safe.csv"
DEFAULT_AUDIT_PLUS = "outputs/tables/phase5p5_repair5g57_g6_features_audit_plus_perf.csv"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g57_g6_feature_matrix_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g57_g6_feature_matrix_quality.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g56-feature-table-csv", type=Path, default=Path(DEFAULT_G56_FEATURES))
    parser.add_argument("--allowlist-summary-json", type=Path, default=Path(DEFAULT_ALLOWLIST))
    parser.add_argument("--confidence-labels-csv", type=Path, default=Path(DEFAULT_CONFIDENCE_LABELS))
    parser.add_argument("--perf-safe-csv", type=Path, default=Path(DEFAULT_PERF_SAFE))
    parser.add_argument("--audit-plus-perf-csv", type=Path, default=Path(DEFAULT_AUDIT_PLUS))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--default-margin-threshold", type=float, default=G57_DEFAULT_MARGIN_THRESHOLD)
    return parser.parse_args(argv)


def metadata_and_target(label: dict[str, Any]) -> dict[str, Any]:
    return {
        "context_id": label.get("context_id", ""),
        "normalized_context_key": label.get("normalized_context_key", ""),
        "map": label.get("map", ""),
        "agents": label.get("agents", ""),
        "seed": label.get("seed", ""),
        "iteration": label.get("iteration", ""),
        "traffic_before_hash_full": label.get("traffic_before_hash_full", ""),
        "margin_threshold": label.get("margin_threshold", ""),
        "label_class": label.get("label_class", ""),
        "target_candidate_id": label.get("target_candidate_id", ""),
        "training_eligible": label.get("training_eligible", ""),
        "train_weight": label.get("train_weight", ""),
        "stable_static_or_abstain": label.get("stable_static_or_abstain", ""),
    }


def forbidden_feature_columns(feature_names: list[str]) -> list[str]:
    lowered_forbidden = {name.lower() for name in G56_FORBIDDEN_TARGET_FEATURES}
    return sorted(name for name in feature_names if name.lower() in lowered_forbidden)


def build_rows(
    feature_rows: list[dict[str, Any]],
    labels_by_key: dict[str, dict[str, Any]],
    *,
    feature_names: list[str],
    audit_feature_names: list[str] | None = None,
) -> list[dict[str, Any]]:
    audit_feature_names = audit_feature_names or []
    out = []
    for feature in feature_rows:
        key = context_key_from_row(feature)
        label = labels_by_key.get(key)
        if not label:
            continue
        row = metadata_and_target(label)
        for name in feature_names:
            row[name] = feature.get(name, "")
        for name in audit_feature_names:
            row[name] = feature.get(name, "")
        out.append(row)
    return out


def write_summary_and_report(
    *,
    summary_path: Path,
    report_path: Path,
    perf_rows: list[dict[str, Any]],
    audit_rows: list[dict[str, Any]],
    perf_features: list[str],
    audit_features: list[str],
    forbidden_perf: list[str],
    forbidden_audit: list[str],
    observed_ok: bool,
    perf_safe_csv: Path,
    audit_plus_csv: Path,
) -> dict[str, Any]:
    audit_in_perf = sorted(set(perf_features) & set(audit_features))
    gates = {
        "perf_safe_feature_matrix_rows_gt_0": bool(perf_rows),
        "audit_plus_perf_feature_matrix_rows_gt_0": bool(audit_rows),
        "perf_safe_feature_matrix_passed": False,
        "audit_plus_perf_marked_diagnostic_only": True,
        "forbidden_feature_count": len(forbidden_perf) + len(forbidden_audit),
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
        "perf_safe_csv": str(perf_safe_csv),
        "audit_plus_perf_csv": str(audit_plus_csv),
        "perf_safe_rows": len(perf_rows),
        "audit_plus_perf_rows": len(audit_rows),
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
    write_json(summary_path, summary)
    write_text(
        report_path,
        "# Phase5.5 Repair5G.5.7 G6 Feature Matrix Quality\n\n"
        f"- perf_safe_rows: `{len(perf_rows)}`\n"
        f"- audit_plus_perf_rows: `{len(audit_rows)}`\n"
        f"- training_eligible_perf_safe_rows: `{summary['training_eligible_perf_safe_rows']}`\n"
        f"- perf_safe_feature_count: `{len(perf_features)}`\n"
        f"- audit_only_feature_count: `{len(audit_features)}`\n"
        f"- forbidden_feature_count: `{gates['forbidden_feature_count']}`\n"
        f"- perf_safe_feature_matrix_passed: `{gates['perf_safe_feature_matrix_passed']}`\n\n"
        "`audit_plus_perf` is diagnostic only. Runtime-performance claims may only use `perf_safe_only`.\n",
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    feature_rows = read_csv_rows(resolve(args.g56_feature_table_csv, root))
    allowlist = load_json(resolve(args.allowlist_summary_json, root))
    labels = [
        row
        for row in read_csv_rows(resolve(args.confidence_labels_csv, root))
        if abs(finite_number(row.get("margin_threshold"), -1.0) - float(args.default_margin_threshold)) < 1.0e-12
    ]
    labels_by_key = {str(row.get("normalized_context_key", "")): row for row in labels}
    perf_features = list(allowlist.get("perf_safe_features", []))
    audit_features = list(allowlist.get("audit_only_features", sorted(G56_AUDIT_ONLY_FEATURES)))
    perf_rows = build_rows(feature_rows, labels_by_key, feature_names=perf_features)
    audit_rows = build_rows(feature_rows, labels_by_key, feature_names=perf_features, audit_feature_names=audit_features)
    perf_safe_csv = resolve(args.perf_safe_csv, root)
    audit_plus_csv = resolve(args.audit_plus_perf_csv, root)
    write_csv_rows(perf_safe_csv, perf_rows)
    write_csv_rows(audit_plus_csv, audit_rows)
    forbidden_perf = forbidden_feature_columns(perf_features)
    forbidden_audit = forbidden_feature_columns(perf_features + audit_features)
    observed_ok = validate_observed_rows(perf_rows + audit_rows, label="Repair5G.5.7 feature matrices")
    summary = write_summary_and_report(
        summary_path=resolve(args.summary_json, root),
        report_path=resolve(args.report, root),
        perf_rows=perf_rows,
        audit_rows=audit_rows,
        perf_features=perf_features,
        audit_features=audit_features,
        forbidden_perf=forbidden_perf,
        forbidden_audit=forbidden_audit,
        observed_ok=observed_ok,
        perf_safe_csv=perf_safe_csv,
        audit_plus_csv=audit_plus_csv,
    )
    print(json.dumps({"decision": summary["decision"], "perf_safe_rows": len(perf_rows)}))
    return 0 if summary["gates"]["perf_safe_feature_matrix_rows_gt_0"] and observed_ok else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

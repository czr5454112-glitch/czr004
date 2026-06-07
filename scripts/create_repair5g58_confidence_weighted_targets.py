"""Create Repair5G.5.8 confidence-weighted targets from primary-pair rows."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g58_common import (  # noqa: E402
    G58_DEFAULT_MARGIN_THRESHOLD,
    G58_MARGIN_THRESHOLDS,
    G58_PRIMARY_BUDGET_MS,
    G58_SENTINEL_BUDGET_MS,
    classify_context,
    confidence_weight,
    gate_counts,
    labels_by_normalized_key,
    read_csv_rows,
    repo_root,
    resolve,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_PRIMARY = "outputs/tables/phase5p5_repair5g58_primary_pair_confidence_by_context.csv"
DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g56_counterfactual_update_labels.csv"
DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g58_confidence_weighted_targets.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g58_confidence_weighted_targets.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g58_confidence_weighted_targets_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-pair-csv", type=Path, default=Path(DEFAULT_PRIMARY))
    parser.add_argument("--source-labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--confidence-targets-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--margin-thresholds", nargs="+", type=float, default=G58_MARGIN_THRESHOLDS)
    parser.add_argument("--default-margin-threshold", type=float, default=G58_DEFAULT_MARGIN_THRESHOLD)
    return parser.parse_args(argv)


def budget_summary(row: dict[str, Any], prefix: str) -> dict[str, Any]:
    return {
        "oracle_candidate_id": row.get(f"oracle_{prefix}", ""),
        "finite_candidate_count": row.get(f"finite_candidates_{prefix}", 0),
        "static_score": row.get(f"static_score_{prefix}", ""),
        "oracle_score": row.get(f"oracle_score_{prefix}", ""),
        "margin_vs_static": row.get(f"margin_vs_static_{prefix}", ""),
        "static_vs_oracle_sign": row.get(f"static_vs_oracle_sign_{prefix}", ""),
    }


def context_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "context_id": row.get("context_id", ""),
        "normalized_context_key": row.get("normalized_context_key", ""),
        "map": row.get("map", ""),
        "agents": row.get("agents", ""),
        "seed": row.get("seed", ""),
        "iteration": row.get("iteration", ""),
        "traffic_before_hash_full": row.get("traffic_before_hash_full", ""),
        "budgets": {
            G58_PRIMARY_BUDGET_MS: budget_summary(row, "1000"),
            G58_SENTINEL_BUDGET_MS: budget_summary(row, "2000"),
        },
    }


def make_summary(rows: list[dict[str, Any]], *, default_threshold: float, observed_ok: bool, output_csv: Path) -> dict[str, Any]:
    default_rows = [row for row in rows if abs(float(row.get("margin_threshold", 0.0)) - float(default_threshold)) < 1.0e-12]
    counts = gate_counts(default_rows)
    budget_sensitive_rows = [
        row
        for row in default_rows
        if row.get("label_class") in {"budget_sensitive_exclude", "longer_budget_needed"}
    ]
    gates = {
        "confidence_labels_v2_created": bool(rows),
        "training_eligible_contexts_ge_30": counts["training_eligible_contexts"] >= 30,
        "stable_high_confidence_nonstatic_count_ge_10": counts["stable_high_confidence_nonstatic_count"] >= 10,
        "stable_static_or_abstain_count_ge_10": counts["stable_static_or_abstain_count"] >= 10,
        "budget_sensitive_excluded_or_downweighted": (not budget_sensitive_rows)
        or all(str(row.get("training_eligible", "")).lower() != "true" and float(row.get("train_weight") or 0.0) == 0.0 for row in budget_sensitive_rows),
        "no_solution_abstain_present": any(row.get("label_class") == "no_solution_abstain" for row in default_rows),
        "observed_ids_only": observed_ok,
    }
    gates["ids_166_205_untouched"] = observed_ok
    gates["confidence_training_gate_passed"] = all(gates.values())
    class_counts = {}
    for row in default_rows:
        class_counts[str(row.get("label_class", ""))] = class_counts.get(str(row.get("label_class", "")), 0) + 1
    return {
        "schema_version": "phase5p5_repair5g58_confidence_weighted_targets_summary_v1",
        "confidence_targets_csv": str(output_csv),
        "margin_thresholds": sorted({float(row.get("margin_threshold", 0.0)) for row in rows}),
        "default_margin_threshold": float(default_threshold),
        "label_rows": len(rows),
        "default_threshold_contexts": len(default_rows),
        "class_counts_default_threshold": dict(sorted(class_counts.items())),
        **counts,
        "gates": gates,
        "decision": "confidence_labels_sufficient_training_gate_passed" if gates["confidence_training_gate_passed"] else "offline_g6_not_run_training_gate_failed",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "runtime_claim_allowed": False,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    primary_rows = read_csv_rows(resolve(args.primary_pair_csv, root))
    source_labels = read_csv_rows(resolve(args.source_labels_csv, root))
    source_by_key = labels_by_normalized_key(source_labels)
    rows = []
    for primary in primary_rows:
        context = context_from_row(primary)
        key = str(primary.get("normalized_context_key", ""))
        source = source_by_key.get(key, {})
        for threshold in sorted(float(value) for value in args.margin_thresholds):
            label_class, target, training, margin, reason = classify_context(context, margin_threshold=threshold)
            rows.append(
                {
                    "context_id": source.get("context_id", primary.get("context_id", key)),
                    "normalized_context_key": key,
                    "map": primary.get("map", ""),
                    "agents": primary.get("agents", ""),
                    "seed": primary.get("seed", ""),
                    "iteration": primary.get("iteration", ""),
                    "traffic_before_hash_full": primary.get("traffic_before_hash_full", ""),
                    "margin_threshold": threshold,
                    "label_class": label_class,
                    "target_candidate_id": target,
                    "oracle_1000": primary.get("oracle_1000", ""),
                    "oracle_2000": primary.get("oracle_2000", ""),
                    "finite_candidates_1000": primary.get("finite_candidates_1000", ""),
                    "finite_candidates_2000": primary.get("finite_candidates_2000", ""),
                    "margin_vs_static_1000": primary.get("margin_vs_static_1000", ""),
                    "margin_vs_static_2000": primary.get("margin_vs_static_2000", ""),
                    "training_eligible": bool(training),
                    "train_weight": confidence_weight(context, label_class, margin),
                    "stable_static_or_abstain": label_class in {"stable_static", "abstain_to_static"},
                    "confidence_reason": reason,
                    "primary_budget_ms": int(G58_PRIMARY_BUDGET_MS),
                    "sentinel_budget_ms": int(G58_SENTINEL_BUDGET_MS),
                    "stress_250_used_for_training_gate": False,
                    "mid_500_used_as_bonus_only": True,
                }
            )
    output_csv = resolve(args.confidence_targets_csv, root)
    write_csv_rows(output_csv, rows)
    observed_ok = validate_observed_rows(primary_rows + source_labels + rows, label="Repair5G.5.8 confidence targets")
    summary = make_summary(rows, default_threshold=float(args.default_margin_threshold), observed_ok=observed_ok, output_csv=output_csv)
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.8 Confidence-Weighted Targets\n\n"
        f"- default_margin_threshold: `{summary['default_margin_threshold']}`\n"
        f"- default_threshold_contexts: `{summary['default_threshold_contexts']}`\n"
        f"- training_eligible_contexts: `{summary['training_eligible_contexts']}`\n"
        f"- stable_high_confidence_nonstatic_count: `{summary['stable_high_confidence_nonstatic_count']}`\n"
        f"- stable_static_or_abstain_count: `{summary['stable_static_or_abstain_count']}`\n"
        f"- no_solution_or_budget_abstain_count: `{summary['no_solution_or_budget_abstain_count']}`\n"
        f"- confidence_training_gate_passed: `{summary['gates']['confidence_training_gate_passed']}`\n\n"
        "Targets use 1000/2000 ms primary-pair stability. Budget-sensitive rows are not used as gold expert-selection labels.\n",
    )
    print(json.dumps({"decision": summary["decision"], "training_eligible_contexts": summary["training_eligible_contexts"]}))
    return 0 if rows and observed_ok else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

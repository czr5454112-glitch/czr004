"""Create Repair5G.5.7 confidence-weighted labels from budget-tier probes."""

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

from repair5g57_common import (  # noqa: E402
    G56_STATIC_CANDIDATE,
    G57_DEFAULT_MARGIN_THRESHOLD,
    G57_MARGIN_THRESHOLDS,
    G57_MID_BUDGET_MS,
    G57_PRIMARY_BUDGET_MS,
    G57_SENTINEL_BUDGET_MS,
    G57_STRESS_BUDGET_MS,
    G57_STATIC_ABSTAIN_CLASSES,
    G57_TRAINING_CLASSES,
    budget_summary_value,
    context_key_from_row,
    count_by,
    default_threshold_rows,
    finite_number,
    format_optional_float,
    labels_by_normalized_key,
    load_budget_rank_contexts,
    read_csv_rows,
    repo_root,
    resolve,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_RANK_STABILITY = "outputs/tables/phase5p5_repair5g56_probe_budget_rank_stability.csv"
DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g56_counterfactual_update_labels.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g56_oracle_by_context.csv"
DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g57_confidence_weighted_labels.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g57_confidence_weighted_label_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g57_confidence_weighted_label_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rank-stability-csv", type=Path, default=Path(DEFAULT_RANK_STABILITY))
    parser.add_argument("--labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--oracle-csv", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--confidence-labels-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--margin-thresholds", nargs="+", type=float, default=G57_MARGIN_THRESHOLDS)
    parser.add_argument("--default-margin-threshold", type=float, default=G57_DEFAULT_MARGIN_THRESHOLD)
    return parser.parse_args(argv)


def classify_context(
    context: dict[str, Any],
    *,
    margin_threshold: float,
) -> tuple[str, str, bool, float, str]:
    budgets = context["budgets"]
    primary = budgets.get(G57_PRIMARY_BUDGET_MS)
    sentinel = budgets.get(G57_SENTINEL_BUDGET_MS)
    if not primary or not sentinel:
        return "exclude_from_training", "", False, 0.0, "missing primary or sentinel budget"

    primary_oracle = str(budget_summary_value(primary, "oracle_candidate_id"))
    sentinel_oracle = str(budget_summary_value(sentinel, "oracle_candidate_id"))
    primary_finite = int(budget_summary_value(primary, "finite_candidate_count", 0) or 0)
    sentinel_finite = int(budget_summary_value(sentinel, "finite_candidate_count", 0) or 0)
    primary_static_score = finite_number(primary.get("static_score"), math.inf)
    sentinel_static_score = finite_number(sentinel.get("static_score"), math.inf)
    primary_oracle_score = finite_number(primary.get("oracle_score"), math.inf)
    sentinel_oracle_score = finite_number(sentinel.get("oracle_score"), math.inf)
    primary_margin = finite_number(primary.get("margin_vs_static"), math.nan)
    sentinel_margin = finite_number(sentinel.get("margin_vs_static"), math.nan)
    static_feasible_both = math.isfinite(primary_static_score) and math.isfinite(sentinel_static_score)
    oracle_feasible_both = primary_finite > 0 and sentinel_finite > 0

    if primary_finite == 0 and sentinel_finite == 0:
        return "no_solution_abstain", G56_STATIC_CANDIDATE, False, 0.0, "no candidate feasible at primary/sentinel"
    if primary_finite == 0 or sentinel_finite == 0 or primary_finite != sentinel_finite:
        return "budget_sensitive", G56_STATIC_CANDIDATE, False, 0.0, "candidate feasibility changes across primary/sentinel"
    if not oracle_feasible_both:
        return "exclude_from_training", "", False, 0.0, "unclassifiable feasibility state"

    same_oracle = bool(primary_oracle and sentinel_oracle and primary_oracle == sentinel_oracle)
    primary_static_regret = primary_static_score - primary_oracle_score if math.isfinite(primary_static_score) and math.isfinite(primary_oracle_score) else math.inf
    sentinel_static_regret = sentinel_static_score - sentinel_oracle_score if math.isfinite(sentinel_static_score) and math.isfinite(sentinel_oracle_score) else math.inf
    max_static_regret = max(primary_static_regret, sentinel_static_regret)
    if same_oracle:
        if primary_oracle != G56_STATIC_CANDIDATE and primary_margin <= -margin_threshold and sentinel_margin <= -margin_threshold:
            margin = min(abs(primary_margin), abs(sentinel_margin))
            return "stable_high_confidence_nonstatic", primary_oracle, True, margin, "1000/2000 agree on high-margin nonstatic oracle"
        return "stable_static", G56_STATIC_CANDIDATE, True, max(0.0, margin_threshold - max_static_regret), "1000/2000 agree or nonstatic margin is too small"

    if static_feasible_both and max_static_regret <= margin_threshold:
        return "abstain_to_static", G56_STATIC_CANDIDATE, True, max(0.0, margin_threshold - max_static_regret), "unstable oracle identity but static is feasible and near-oracle"
    return "budget_sensitive", G56_STATIC_CANDIDATE, False, 0.0, "1000/2000 oracle identity disagrees with nontrivial static regret"


def confidence_weight(context: dict[str, Any], label_class: str, margin: float) -> float:
    if label_class not in G57_TRAINING_CLASSES:
        return 0.0
    budgets = context["budgets"]
    primary = budgets.get(G57_PRIMARY_BUDGET_MS)
    sentinel = budgets.get(G57_SENTINEL_BUDGET_MS)
    mid = budgets.get(G57_MID_BUDGET_MS)
    stress = budgets.get(G57_STRESS_BUDGET_MS)
    base = 1.0 + min(4.0, max(0.0, margin) * 100.0)
    if mid and primary and sentinel:
        mid_oracle = budget_summary_value(mid, "oracle_candidate_id")
        if mid_oracle and mid_oracle == budget_summary_value(primary, "oracle_candidate_id") == budget_summary_value(sentinel, "oracle_candidate_id"):
            base += 0.25
    if stress and primary:
        stress_oracle = budget_summary_value(stress, "oracle_candidate_id")
        if stress_oracle and stress_oracle == budget_summary_value(primary, "oracle_candidate_id"):
            base += 0.10
    return round(min(5.0, base), 6)


def make_summary(rows: list[dict[str, Any]], *, default_threshold: float, observed_ok: bool, output_csv: Path) -> dict[str, Any]:
    default_rows = [
        row
        for row in rows
        if abs(float(row.get("margin_threshold", 0.0)) - float(default_threshold)) < 1.0e-12
    ]
    training = [row for row in default_rows if str(row.get("training_eligible", "")).lower() == "true"]
    stable_high = [row for row in default_rows if row.get("label_class") == "stable_high_confidence_nonstatic"]
    stable_static = [row for row in default_rows if row.get("label_class") == "stable_static"]
    abstain = [row for row in default_rows if row.get("label_class") == "abstain_to_static"]
    no_solution = [row for row in default_rows if row.get("label_class") == "no_solution_abstain"]
    budget_sensitive = [row for row in default_rows if row.get("label_class") == "budget_sensitive"]
    stable_static_or_abstain = stable_static + abstain
    gates = {
        "confidence_labels_created": bool(rows),
        "training_eligible_contexts_count_reported": True,
        "stable_high_confidence_nonstatic_count_reported": True,
        "stable_static_count_reported": True,
        "abstain_to_static_count_reported": True,
        "no_solution_abstain_count_reported": True,
        "budget_sensitive_count_reported": True,
        "training_eligible_contexts_ge_30": len(training) >= 30,
        "stable_high_confidence_nonstatic_count_ge_10": len(stable_high) >= 10,
        "stable_static_or_abstain_count_ge_10": len(stable_static_or_abstain) >= 10,
        "observed_ids_only": observed_ok,
    }
    gates["ids_166_205_untouched"] = observed_ok
    gates["confidence_training_gate_passed"] = (
        gates["confidence_labels_created"]
        and gates["training_eligible_contexts_ge_30"]
        and gates["stable_high_confidence_nonstatic_count_ge_10"]
        and gates["stable_static_or_abstain_count_ge_10"]
        and gates["observed_ids_only"]
    )
    return {
        "schema_version": "phase5p5_repair5g57_confidence_weighted_label_summary_v1",
        "confidence_labels_csv": str(output_csv),
        "margin_thresholds": sorted({float(row.get("margin_threshold", 0.0)) for row in rows}),
        "default_margin_threshold": default_threshold,
        "label_rows": len(rows),
        "default_threshold_contexts": len(default_rows),
        "class_counts_default_threshold": count_by(default_rows, "label_class"),
        "training_eligible_contexts": len(training),
        "stable_high_confidence_nonstatic_count": len(stable_high),
        "stable_static_count": len(stable_static),
        "abstain_to_static_count": len(abstain),
        "stable_static_or_abstain_count": len(stable_static_or_abstain),
        "no_solution_abstain_count": len(no_solution),
        "budget_sensitive_count": len(budget_sensitive),
        "gates": gates,
        "decision": "confidence_labels_training_ready" if gates["confidence_training_gate_passed"] else "confidence_labels_insufficient_continue_probe_design",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "runtime_claim_allowed": False,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rank_csv = resolve(args.rank_stability_csv, root)
    labels_csv = resolve(args.labels_csv, root)
    oracle_csv = resolve(args.oracle_csv, root)
    labels = read_csv_rows(labels_csv)
    oracle = read_csv_rows(oracle_csv)
    labels_by_key = labels_by_normalized_key(labels)
    contexts = load_budget_rank_contexts(rank_csv)
    rows = []
    for key, context in sorted(contexts.items()):
        label_row = labels_by_key.get(key, {})
        context_id = str(label_row.get("context_id", key))
        for margin_threshold in sorted(float(value) for value in args.margin_thresholds):
            label_class, target, training_eligible, margin, reason = classify_context(context, margin_threshold=margin_threshold)
            train_weight = confidence_weight(context, label_class, margin)
            primary = context["budgets"].get(G57_PRIMARY_BUDGET_MS)
            sentinel = context["budgets"].get(G57_SENTINEL_BUDGET_MS)
            mid = context["budgets"].get(G57_MID_BUDGET_MS)
            stress = context["budgets"].get(G57_STRESS_BUDGET_MS)
            rows.append(
                {
                    "context_id": context_id,
                    "normalized_context_key": key,
                    "map": context.get("map", ""),
                    "agents": context.get("agents", ""),
                    "seed": context.get("seed", ""),
                    "iteration": context.get("iteration", ""),
                    "traffic_before_hash_full": context.get("traffic_before_hash_full", ""),
                    "margin_threshold": margin_threshold,
                    "label_class": label_class,
                    "target_candidate_id": target,
                    "oracle_1000": budget_summary_value(primary, "oracle_candidate_id"),
                    "oracle_2000": budget_summary_value(sentinel, "oracle_candidate_id"),
                    "oracle_500": budget_summary_value(mid, "oracle_candidate_id"),
                    "oracle_250": budget_summary_value(stress, "oracle_candidate_id"),
                    "finite_candidates_1000": budget_summary_value(primary, "finite_candidate_count", 0),
                    "finite_candidates_2000": budget_summary_value(sentinel, "finite_candidate_count", 0),
                    "margin_vs_static_1000": format_optional_float(budget_summary_value(primary, "margin_vs_static", math.nan)),
                    "margin_vs_static_2000": format_optional_float(budget_summary_value(sentinel, "margin_vs_static", math.nan)),
                    "training_eligible": bool(training_eligible),
                    "train_weight": train_weight,
                    "stable_static_or_abstain": label_class in G57_STATIC_ABSTAIN_CLASSES,
                    "confidence_reason": reason,
                    "primary_budget_ms": int(G57_PRIMARY_BUDGET_MS),
                    "sentinel_budget_ms": int(G57_SENTINEL_BUDGET_MS),
                    "stress_250_used_for_training_gate": False,
                    "mid_500_used_as_bonus_only": True,
                }
            )
    output_csv = resolve(args.confidence_labels_csv, root)
    write_csv_rows(output_csv, rows)
    observed_ok = validate_observed_rows(labels + oracle + rows, label="Repair5G.5.7 confidence labels")
    summary = make_summary(rows, default_threshold=float(args.default_margin_threshold), observed_ok=observed_ok, output_csv=output_csv)
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.7 Confidence-Weighted Labels\n\n"
        f"- default_margin_threshold: `{summary['default_margin_threshold']}`\n"
        f"- default_threshold_contexts: `{summary['default_threshold_contexts']}`\n"
        f"- training_eligible_contexts: `{summary['training_eligible_contexts']}`\n"
        f"- stable_high_confidence_nonstatic_count: `{summary['stable_high_confidence_nonstatic_count']}`\n"
        f"- stable_static_count: `{summary['stable_static_count']}`\n"
        f"- abstain_to_static_count: `{summary['abstain_to_static_count']}`\n"
        f"- no_solution_abstain_count: `{summary['no_solution_abstain_count']}`\n"
        f"- budget_sensitive_count: `{summary['budget_sensitive_count']}`\n"
        f"- confidence_training_gate_passed: `{summary['gates']['confidence_training_gate_passed']}`\n\n"
        "Rows are constructed from primary 1000/2000 ms stability. The 250 ms tier remains a stress diagnostic, not a hard training gate.\n",
    )
    print(json.dumps({"decision": summary["decision"], "training_eligible_contexts": summary["training_eligible_contexts"]}))
    return 0 if summary["gates"]["confidence_labels_created"] and observed_ok else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

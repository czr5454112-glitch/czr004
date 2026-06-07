"""Analyze Repair5G.5.8 confidence target balance and choose threshold."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g58_common import (  # noqa: E402
    G58_ABSTAIN_BANK_CLASSES,
    G58_DEFAULT_MARGIN_THRESHOLD,
    G58_STATIC_ABSTAIN_CLASSES,
    count_by,
    finite_number,
    gate_counts,
    is_true,
    map_agent_key,
    read_csv_rows,
    repo_root,
    resolve,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g58_confidence_weighted_targets.csv"
DEFAULT_BY_MAP_AGENT = "outputs/tables/phase5p5_repair5g58_confidence_weighted_targets_by_map_agent.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g58_confidence_weighted_targets.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g58_confidence_weighted_targets_summary.json"
DEFAULT_THRESHOLD_REPORT = "outputs/reports/phase5p5_repair5g58_training_label_threshold_decision.md"
DEFAULT_THRESHOLD_SUMMARY = "outputs/reports/phase5p5_repair5g58_training_label_threshold_decision_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confidence-targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_BY_MAP_AGENT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--threshold-decision-report", type=Path, default=Path(DEFAULT_THRESHOLD_REPORT))
    parser.add_argument("--threshold-decision-summary-json", type=Path, default=Path(DEFAULT_THRESHOLD_SUMMARY))
    parser.add_argument("--preferred-threshold", type=float, default=G58_DEFAULT_MARGIN_THRESHOLD)
    return parser.parse_args(argv)


def threshold_rows(rows: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    return [row for row in rows if abs(finite_number(row.get("margin_threshold"), -1.0) - threshold) < 1.0e-12]


def class_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = count_by(rows, "label_class")
    for name in [
        "stable_high_confidence_nonstatic",
        "stable_static",
        "abstain_to_static",
        "no_solution_abstain",
        "longer_budget_needed",
        "budget_sensitive_exclude",
        "exclude_from_training",
    ]:
        counts.setdefault(name, 0)
    return dict(sorted(counts.items()))


def gate_status(rows: list[dict[str, Any]], observed_ok: bool) -> tuple[dict[str, int], dict[str, bool]]:
    counts = gate_counts(rows)
    budget_sensitive_rows = [
        row
        for row in rows
        if row.get("label_class") in {"budget_sensitive_exclude", "longer_budget_needed"}
    ]
    gates = {
        "confidence_labels_v2_created": bool(rows),
        "training_eligible_contexts_ge_30": counts["training_eligible_contexts"] >= 30,
        "stable_high_confidence_nonstatic_count_ge_10": counts["stable_high_confidence_nonstatic_count"] >= 10,
        "stable_static_or_abstain_count_ge_10": counts["stable_static_or_abstain_count"] >= 10,
        "budget_sensitive_excluded_or_downweighted": (not budget_sensitive_rows)
        or all((not is_true(row.get("training_eligible"))) and float(row.get("train_weight") or 0.0) == 0.0 for row in budget_sensitive_rows),
        "no_solution_abstain_present": any(row.get("label_class") == "no_solution_abstain" for row in rows),
        "observed_ids_only": observed_ok,
    }
    gates["ids_166_205_untouched"] = observed_ok
    gates["confidence_training_gate_passed"] = all(gates.values())
    return counts, gates


def choose_threshold(by_threshold: dict[str, dict[str, Any]], preferred: float) -> tuple[float, str]:
    preferred_key = str(float(preferred))
    if by_threshold.get(preferred_key, {}).get("gates", {}).get("confidence_training_gate_passed"):
        return float(preferred), "preferred_threshold_passed"
    for key, value in sorted(by_threshold.items(), key=lambda item: float(item[0])):
        if value.get("gates", {}).get("confidence_training_gate_passed"):
            return float(key), "first_passing_threshold_selected"
    return float(preferred), "no_threshold_passed_training_gate"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    targets_csv = resolve(args.confidence_targets_csv, root)
    rows = read_csv_rows(targets_csv)
    observed_ok = validate_observed_rows(rows, label="Repair5G.5.8 confidence target analysis")
    thresholds = sorted({finite_number(row.get("margin_threshold"), 0.0) for row in rows})
    by_threshold: dict[str, dict[str, Any]] = {}
    for threshold in thresholds:
        current = threshold_rows(rows, threshold)
        counts, gates = gate_status(current, observed_ok)
        by_threshold[str(threshold)] = {
            "contexts": len(current),
            "training_eligible_contexts": counts["training_eligible_contexts"],
            "stable_high_confidence_nonstatic_count": counts["stable_high_confidence_nonstatic_count"],
            "stable_static_or_abstain_count": counts["stable_static_or_abstain_count"],
            "no_solution_or_budget_abstain_count": counts["no_solution_or_budget_abstain_count"],
            "class_counts": class_counts(current),
            "gates": gates,
        }

    selected_threshold, selection_reason = choose_threshold(by_threshold, float(args.preferred_threshold))
    default_rows = threshold_rows(rows, selected_threshold)
    counts, gates = gate_status(default_rows, observed_ok)

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in default_rows:
        groups[map_agent_key(row)].append(row)
    group_rows = []
    for key, group in sorted(groups.items()):
        first = group[0]
        group_rows.append(
            {
                "map_agent": key,
                "map": first.get("map", ""),
                "agents": first.get("agents", ""),
                "contexts": len(group),
                "training_eligible_contexts": sum(1 for row in group if is_true(row.get("training_eligible"))),
                "stable_high_confidence_nonstatic": sum(1 for row in group if row.get("label_class") == "stable_high_confidence_nonstatic"),
                "stable_static_or_abstain": sum(1 for row in group if row.get("label_class") in G58_STATIC_ABSTAIN_CLASSES),
                "no_solution_or_budget_abstain": sum(1 for row in group if row.get("label_class") in G58_ABSTAIN_BANK_CLASSES),
                "budget_sensitive_exclude": sum(1 for row in group if row.get("label_class") == "budget_sensitive_exclude"),
            }
        )
    write_csv_rows(resolve(args.by_map_agent_csv, root), group_rows)

    summary = {
        "schema_version": "phase5p5_repair5g58_confidence_weighted_targets_summary_v1",
        "confidence_targets_csv": str(targets_csv),
        "by_map_agent_csv": str(resolve(args.by_map_agent_csv, root)),
        "selected_margin_threshold": selected_threshold,
        "threshold_selection_reason": selection_reason,
        "label_rows": len(rows),
        "default_threshold_contexts": len(default_rows),
        "class_counts_default_threshold": class_counts(default_rows),
        **counts,
        "by_margin_threshold": by_threshold,
        "gates": gates,
        "decision": "confidence_labels_sufficient_training_gate_passed" if gates["confidence_training_gate_passed"] else "offline_g6_not_run_training_gate_failed",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "runtime_claim_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.8 Confidence-Weighted Target Analysis\n\n"
        f"- selected_margin_threshold: `{selected_threshold}`\n"
        f"- threshold_selection_reason: `{selection_reason}`\n"
        f"- training_eligible_contexts: `{summary['training_eligible_contexts']}`\n"
        f"- stable_high_confidence_nonstatic_count: `{summary['stable_high_confidence_nonstatic_count']}`\n"
        f"- stable_static_or_abstain_count: `{summary['stable_static_or_abstain_count']}`\n"
        f"- no_solution_or_budget_abstain_count: `{summary['no_solution_or_budget_abstain_count']}`\n"
        f"- confidence_training_gate_passed: `{gates['confidence_training_gate_passed']}`\n\n"
        "This is a label-bank gate only. Runtime claims, Phase5.5, Phase6, and AAAI-ready status remain closed.\n",
    )

    threshold_summary = {
        "schema_version": "phase5p5_repair5g58_training_label_threshold_decision_summary_v1",
        "selected_margin_threshold": selected_threshold,
        "selection_reason": selection_reason,
        "thresholds": by_threshold,
        "offline_training_allowed": bool(gates["confidence_training_gate_passed"]),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "runtime_claim_allowed": False,
    }
    write_json(resolve(args.threshold_decision_summary_json, root), threshold_summary)
    write_text(
        resolve(args.threshold_decision_report, root),
        "# Phase5.5 Repair5G.5.8 Training Label Threshold Decision\n\n"
        f"- selected_margin_threshold: `{selected_threshold}`\n"
        f"- selection_reason: `{selection_reason}`\n"
        f"- offline_training_allowed: `{threshold_summary['offline_training_allowed']}`\n\n"
        "The threshold is selected before any optional offline G6 training and is based only on observed-ID confidence-label balance.\n",
    )
    print(json.dumps({"decision": summary["decision"], "selected_margin_threshold": selected_threshold}))
    return 0 if rows and observed_ok else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

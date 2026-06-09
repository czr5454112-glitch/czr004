"""Write final Repair5G.5.7 decision from budget-aware confidence gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g57_common import load_json, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_G56_LABEL_SUMMARY = "outputs/reports/phase5p5_repair5g56_counterfactual_label_completion_summary.json"
DEFAULT_BUDGET = "outputs/reports/phase5p5_repair5g57_budget_tier_stability_summary.json"
DEFAULT_CONFIDENCE = "outputs/reports/phase5p5_repair5g57_confidence_weighted_label_summary.json"
DEFAULT_WAREHOUSE = "outputs/reports/phase5p5_repair5g57_warehouse_no_solution_policy_summary.json"
DEFAULT_FEATURES = "outputs/reports/phase5p5_repair5g57_g6_feature_matrix_summary.json"
DEFAULT_OFFLINE = "outputs/reports/phase5p5_repair5g57_offline_safe_mixture_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g57_decision.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g57_decision_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g56-label-summary-json", type=Path, default=Path(DEFAULT_G56_LABEL_SUMMARY))
    parser.add_argument("--budget-summary-json", type=Path, default=Path(DEFAULT_BUDGET))
    parser.add_argument("--confidence-summary-json", type=Path, default=Path(DEFAULT_CONFIDENCE))
    parser.add_argument("--warehouse-summary-json", type=Path, default=Path(DEFAULT_WAREHOUSE))
    parser.add_argument("--feature-summary-json", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--offline-summary-json", type=Path, default=Path(DEFAULT_OFFLINE))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def gate(summary: dict[str, Any], name: str) -> bool:
    return bool(summary.get("gates", {}).get(name))


def decide(
    budget: dict[str, Any],
    confidence: dict[str, Any],
    warehouse: dict[str, Any],
    features: dict[str, Any],
    offline: dict[str, Any],
) -> str:
    if not gate(budget, "budget_tier_stability_analyzed"):
        return "budget_tier_analysis_failed"
    if not gate(confidence, "confidence_labels_created"):
        return "confidence_labels_insufficient_continue_probe_design"
    if not gate(confidence, "confidence_training_gate_passed"):
        return "confidence_labels_insufficient_continue_probe_design"
    if not gate(warehouse, "warehouse_policy_classified") or not gate(warehouse, "warehouse_contexts_not_silently_dropped"):
        return "warehouse_no_solution_policy_blocks_training"
    if not gate(features, "perf_safe_feature_matrix_passed"):
        return "perf_feature_matrix_failed"
    if not offline.get("offline_training_run", False):
        return "offline_g6_not_run_training_gate_failed"
    if offline.get("decision") == "offline_g6_safe_mixture_passed_continue_runtime_preflight_design":
        return "offline_g6_safe_mixture_passed_continue_runtime_preflight_design"
    if offline.get("offline_eval_run", False):
        return "offline_g6_safe_mixture_failed_continue_label_confidence_or_candidate_space"
    return "offline_g6_not_run_training_gate_failed"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    g56_labels = load_json(resolve(args.g56_label_summary_json, root))
    budget = load_json(resolve(args.budget_summary_json, root))
    confidence = load_json(resolve(args.confidence_summary_json, root))
    warehouse = load_json(resolve(args.warehouse_summary_json, root))
    features = load_json(resolve(args.feature_summary_json, root))
    offline = load_json(resolve(args.offline_summary_json, root))
    decision = decide(budget, confidence, warehouse, features, offline)
    offline_passed = offline.get("decision") == "offline_g6_safe_mixture_passed_continue_runtime_preflight_design"
    summary = {
        "schema_version": "phase5p5_repair5g57_decision_summary_v1",
        "decision": decision,
        "context_count": g56_labels.get("context_count", 0),
        "label_rows": g56_labels.get("label_rows", 0),
        "primary_1000_2000_stable_contexts": budget.get("primary_1000_2000_stable_contexts", 0),
        "training_eligible_contexts": confidence.get("training_eligible_contexts", 0),
        "stable_high_confidence_nonstatic_count": confidence.get("stable_high_confidence_nonstatic_count", 0),
        "stable_static_or_abstain_count": confidence.get("stable_static_or_abstain_count", 0),
        "warehouse_policy": warehouse.get("policy_counts", {}),
        "offline_training_run": bool(offline.get("offline_training_run", False)),
        "offline_g6_passed": bool(offline_passed),
        "ids_166_205_untouched": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "runtime_claim_allowed": False,
        "gates": {
            "budget_tier_stability_analyzed": gate(budget, "budget_tier_stability_analyzed"),
            "confidence_training_gate_passed": gate(confidence, "confidence_training_gate_passed"),
            "warehouse_policy_classified": gate(warehouse, "warehouse_policy_classified"),
            "perf_safe_feature_matrix_passed": gate(features, "perf_safe_feature_matrix_passed"),
            "offline_g6_safe_mixture_eval_passed": gate(offline, "offline_g6_safe_mixture_eval_passed"),
        },
        "evidence_artifacts": {
            "g56_label_completion": str(resolve(args.g56_label_summary_json, root)),
            "budget_tier_stability": str(resolve(args.budget_summary_json, root)),
            "confidence_labels": str(resolve(args.confidence_summary_json, root)),
            "warehouse_policy": str(resolve(args.warehouse_summary_json, root)),
            "feature_matrix": str(resolve(args.feature_summary_json, root)),
            "offline_safe_mixture": str(resolve(args.offline_summary_json, root)),
        },
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.7 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- context_count: `{summary['context_count']}`\n"
        f"- label_rows: `{summary['label_rows']}`\n"
        f"- primary_1000_2000_stable_contexts: `{summary['primary_1000_2000_stable_contexts']}`\n"
        f"- training_eligible_contexts: `{summary['training_eligible_contexts']}`\n"
        f"- stable_high_confidence_nonstatic_count: `{summary['stable_high_confidence_nonstatic_count']}`\n"
        f"- stable_static_or_abstain_count: `{summary['stable_static_or_abstain_count']}`\n"
        f"- warehouse_policy: `{json.dumps(summary['warehouse_policy'], sort_keys=True)}`\n"
        f"- offline_training_run: `{summary['offline_training_run']}`\n"
        f"- offline_g6_passed: `{summary['offline_g6_passed']}`\n"
        f"- ids_166_205_untouched: `True`\n"
        f"- phase5p5_allowed: `False`\n"
        f"- phase6_allowed: `False`\n"
        f"- aaai_ready: `False`\n"
        f"- runtime_claim_allowed: `False`\n\n"
        "G5.7 is an observed-ID diagnostic label-confidence wave. It does not authorize fresh IDs, runtime learned claims, Phase5.5, Phase6, or AAAI-ready status.\n",
    )
    print(json.dumps({"decision": decision, "offline_training_run": summary["offline_training_run"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

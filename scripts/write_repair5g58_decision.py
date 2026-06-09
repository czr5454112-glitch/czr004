"""Write final Repair5G.5.8 decision from confidence-expansion gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g58_common import load_json, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_G57_DECISION = "outputs/reports/phase5p5_repair5g57_decision_summary.json"
DEFAULT_PRIMARY = "outputs/reports/phase5p5_repair5g58_primary_pair_confidence_expansion_summary.json"
DEFAULT_CONFIDENCE = "outputs/reports/phase5p5_repair5g58_confidence_weighted_targets_summary.json"
DEFAULT_WAREHOUSE = "outputs/reports/phase5p5_repair5g58_warehouse_abstention_policy_summary.json"
DEFAULT_FEATURES = "outputs/reports/phase5p5_repair5g58_g6_feature_matrix_summary.json"
DEFAULT_TRAIN = "outputs/reports/phase5p5_repair5g58_offline_safe_mixture_train_summary.json"
DEFAULT_EVAL = "outputs/reports/phase5p5_repair5g58_offline_safe_mixture_eval_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g58_decision.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g58_decision_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g57-decision-summary-json", type=Path, default=Path(DEFAULT_G57_DECISION))
    parser.add_argument("--primary-summary-json", type=Path, default=Path(DEFAULT_PRIMARY))
    parser.add_argument("--confidence-summary-json", type=Path, default=Path(DEFAULT_CONFIDENCE))
    parser.add_argument("--warehouse-summary-json", type=Path, default=Path(DEFAULT_WAREHOUSE))
    parser.add_argument("--feature-summary-json", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--train-summary-json", type=Path, default=Path(DEFAULT_TRAIN))
    parser.add_argument("--eval-summary-json", type=Path, default=Path(DEFAULT_EVAL))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def gate(summary: dict[str, Any], name: str) -> bool:
    return bool(summary.get("gates", {}).get(name))


def decide(primary: dict[str, Any], confidence: dict[str, Any], warehouse: dict[str, Any], features: dict[str, Any], train: dict[str, Any], eval_summary: dict[str, Any]) -> str:
    if not gate(primary, "primary_pair_confidence_expansion_passed"):
        return "confidence_expansion_failed_continue_probe_design"
    if not gate(confidence, "confidence_training_gate_passed"):
        return "offline_g6_not_run_training_gate_failed"
    if not gate(warehouse, "warehouse_abstention_policy_passed"):
        return "warehouse_abstention_policy_failed"
    if not gate(features, "perf_safe_feature_matrix_passed"):
        return "perf_feature_matrix_failed"
    if not train.get("offline_training_run", False):
        return "offline_g6_not_run_training_gate_failed"
    if not eval_summary.get("offline_eval_run", False):
        return "offline_g6_not_run_training_gate_failed"
    if gate(eval_summary, "offline_g6_safe_mixture_eval_passed"):
        return "offline_g6_safe_mixture_passed_continue_runtime_preflight_design"
    return "offline_g6_safe_mixture_failed_continue_labels_or_candidate_space"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    g57 = load_json(resolve(args.g57_decision_summary_json, root))
    primary = load_json(resolve(args.primary_summary_json, root))
    confidence = load_json(resolve(args.confidence_summary_json, root))
    warehouse = load_json(resolve(args.warehouse_summary_json, root))
    features = load_json(resolve(args.feature_summary_json, root))
    train = load_json(resolve(args.train_summary_json, root))
    eval_summary = load_json(resolve(args.eval_summary_json, root))
    decision = decide(primary, confidence, warehouse, features, train, eval_summary)
    summary = {
        "schema_version": "phase5p5_repair5g58_decision_summary_v1",
        "decision": decision,
        "g57_carry_forward_decision": g57.get("decision", ""),
        "context_count": primary.get("context_count", 0),
        "measured_confidence_contexts": primary.get("measured_confidence_contexts", 0),
        "primary_1000_2000_stable_contexts": primary.get("primary_1000_2000_stable_contexts", 0),
        "training_eligible_contexts": confidence.get("training_eligible_contexts", 0),
        "stable_high_confidence_nonstatic_count": confidence.get("stable_high_confidence_nonstatic_count", 0),
        "stable_static_or_abstain_count": confidence.get("stable_static_or_abstain_count", 0),
        "no_solution_or_budget_abstain_count": confidence.get("no_solution_or_budget_abstain_count", 0),
        "warehouse_policy": warehouse.get("policy_counts", {}),
        "perf_safe_rows": features.get("perf_safe_rows", 0),
        "audit_plus_perf_rows": features.get("audit_plus_perf_rows", 0),
        "offline_training_run": bool(train.get("offline_training_run", False)),
        "offline_eval_run": bool(eval_summary.get("offline_eval_run", False)),
        "offline_g6_passed": bool(gate(eval_summary, "offline_g6_safe_mixture_eval_passed")),
        "ids_166_205_untouched": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "runtime_claim_allowed": False,
        "gates": {
            "primary_pair_confidence_expansion_passed": gate(primary, "primary_pair_confidence_expansion_passed"),
            "confidence_training_gate_passed": gate(confidence, "confidence_training_gate_passed"),
            "warehouse_abstention_policy_passed": gate(warehouse, "warehouse_abstention_policy_passed"),
            "perf_safe_feature_matrix_passed": gate(features, "perf_safe_feature_matrix_passed"),
            "offline_g6_safe_mixture_eval_passed": gate(eval_summary, "offline_g6_safe_mixture_eval_passed"),
        },
        "evidence_artifacts": {
            "g57_decision": str(resolve(args.g57_decision_summary_json, root)),
            "primary_pair_confidence": str(resolve(args.primary_summary_json, root)),
            "confidence_targets": str(resolve(args.confidence_summary_json, root)),
            "warehouse_policy": str(resolve(args.warehouse_summary_json, root)),
            "feature_matrix": str(resolve(args.feature_summary_json, root)),
            "offline_train": str(resolve(args.train_summary_json, root)),
            "offline_eval": str(resolve(args.eval_summary_json, root)),
        },
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.8 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- measured_confidence_contexts: `{summary['measured_confidence_contexts']}`\n"
        f"- primary_1000_2000_stable_contexts: `{summary['primary_1000_2000_stable_contexts']}`\n"
        f"- training_eligible_contexts: `{summary['training_eligible_contexts']}`\n"
        f"- stable_high_confidence_nonstatic_count: `{summary['stable_high_confidence_nonstatic_count']}`\n"
        f"- stable_static_or_abstain_count: `{summary['stable_static_or_abstain_count']}`\n"
        f"- no_solution_or_budget_abstain_count: `{summary['no_solution_or_budget_abstain_count']}`\n"
        f"- warehouse_policy: `{json.dumps(summary['warehouse_policy'], sort_keys=True)}`\n"
        f"- perf_safe_rows: `{summary['perf_safe_rows']}`\n"
        f"- offline_training_run: `{summary['offline_training_run']}`\n"
        f"- offline_eval_run: `{summary['offline_eval_run']}`\n"
        f"- offline_g6_passed: `{summary['offline_g6_passed']}`\n"
        f"- ids_166_205_untouched: `True`\n"
        f"- phase5p5_allowed: `False`\n"
        f"- phase6_allowed: `False`\n"
        f"- aaai_ready: `False`\n"
        f"- runtime_claim_allowed: `False`\n\n"
        "G5.8 is an observed-ID offline diagnostic wave. It does not authorize fresh IDs, runtime learned claims, Phase5.5, Phase6, or AAAI-ready status.\n",
    )
    print(json.dumps({"decision": decision, "offline_training_run": summary["offline_training_run"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

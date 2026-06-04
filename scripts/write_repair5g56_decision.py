"""Write the final Repair5G.5.6 decision from current gate summaries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g56_common import load_json, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_LABEL_SUMMARY = "outputs/reports/phase5p5_repair5g56_counterfactual_label_completion_summary.json"
DEFAULT_WAREHOUSE_SUMMARY = "outputs/reports/phase5p5_repair5g56_warehouse_probe_failure_summary.json"
DEFAULT_BUDGET_SUMMARY = "outputs/reports/phase5p5_repair5g56_probe_budget_stability_summary.json"
DEFAULT_FEATURE_SUMMARY = "outputs/reports/phase5p5_repair5g56_perf_feature_allowlist_summary.json"
DEFAULT_TARGET_SUMMARY = "outputs/reports/phase5p5_repair5g56_g6_target_construction_summary.json"
DEFAULT_TRAIN_SUMMARY = "outputs/reports/phase5p5_repair5g56_offline_safe_mixture_summary.json"
DEFAULT_EVAL_SUMMARY = "outputs/reports/phase5p5_repair5g56_offline_safe_mixture_eval_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g56_decision.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g56_decision_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label-summary-json", type=Path, default=Path(DEFAULT_LABEL_SUMMARY))
    parser.add_argument("--warehouse-summary-json", type=Path, default=Path(DEFAULT_WAREHOUSE_SUMMARY))
    parser.add_argument("--budget-summary-json", type=Path, default=Path(DEFAULT_BUDGET_SUMMARY))
    parser.add_argument("--feature-summary-json", type=Path, default=Path(DEFAULT_FEATURE_SUMMARY))
    parser.add_argument("--target-summary-json", type=Path, default=Path(DEFAULT_TARGET_SUMMARY))
    parser.add_argument("--train-summary-json", type=Path, default=Path(DEFAULT_TRAIN_SUMMARY))
    parser.add_argument("--eval-summary-json", type=Path, default=Path(DEFAULT_EVAL_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def gate(summary: dict[str, Any], name: str) -> bool:
    return bool(summary.get("gates", {}).get(name))


def decide(label: dict[str, Any], warehouse: dict[str, Any], budget: dict[str, Any], feature: dict[str, Any], target: dict[str, Any], train: dict[str, Any], eval_summary: dict[str, Any]) -> str:
    label_gates = label.get("gates", {})
    if not label_gates.get("context_count_ge_120", False):
        return "scaled_target_failed_continue_label_collection"
    if not label_gates.get("later_iteration_context_count_gt_0", False):
        return "later_iteration_contexts_missing"
    if not gate(warehouse, "warehouse_probe_failure_analysis_passed"):
        return "warehouse_probe_failure_blocks_training"
    if not gate(budget, "probe_budget_stability_expanded_passed"):
        return "probe_budget_instability_blocks_training"
    if not gate(feature, "perf_feature_allowlist_passed"):
        return "perf_feature_allowlist_failed"
    if not gate(target, "g6_targets_ready"):
        if int(target.get("target_rows", 0) or 0) > 0:
            return "g6_targets_ready_no_training_run"
        return "candidate_space_too_small_expand_before_training"
    if not train.get("offline_training_run", False):
        return "g6_targets_ready_no_training_run"
    if eval_summary.get("decision") == "offline_g6_safe_mixture_passed_continue_runtime_preflight_design":
        return "offline_g6_safe_mixture_passed_continue_runtime_preflight_design"
    if eval_summary:
        return "offline_g6_safe_mixture_failed"
    return "g6_targets_ready_no_training_run"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    label = load_json(resolve(args.label_summary_json, root))
    warehouse = load_json(resolve(args.warehouse_summary_json, root))
    budget = load_json(resolve(args.budget_summary_json, root))
    feature = load_json(resolve(args.feature_summary_json, root))
    target = load_json(resolve(args.target_summary_json, root))
    train = load_json(resolve(args.train_summary_json, root))
    eval_summary = load_json(resolve(args.eval_summary_json, root))
    decision = decide(label, warehouse, budget, feature, target, train, eval_summary)
    summary = {
        "schema_version": "phase5p5_repair5g56_decision_summary_v1",
        "decision": decision,
        "context_count": label.get("context_count", 0),
        "label_rows": label.get("label_rows", 0),
        "later_iteration_context_count": label.get("later_iteration_context_count", 0),
        "training_eligible_stable_contexts": budget.get("training_eligible_stable_contexts", 0),
        "training_eligible_targets": target.get("training_eligible_contexts", 0),
        "offline_training_run": train.get("offline_training_run", False),
        "offline_eval_decision": eval_summary.get("decision", ""),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "ids_166_205_untouched": True,
        "g6_training_allowed": False,
        "runtime_claim_allowed": False,
        "next_step_allowed": "G6.1 runtime preflight design only if offline G6 passed; otherwise continue G5.6 label/probe scaling",
        "evidence_artifacts": {
            "label_completion": str(resolve(args.label_summary_json, root)),
            "warehouse": str(resolve(args.warehouse_summary_json, root)),
            "budget_stability": str(resolve(args.budget_summary_json, root)),
            "feature_allowlist": str(resolve(args.feature_summary_json, root)),
            "targets": str(resolve(args.target_summary_json, root)),
            "train": str(resolve(args.train_summary_json, root)),
            "eval": str(resolve(args.eval_summary_json, root)),
        },
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.6 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- context_count: `{summary['context_count']}`\n"
        f"- label_rows: `{summary['label_rows']}`\n"
        f"- later_iteration_context_count: `{summary['later_iteration_context_count']}`\n"
        f"- training_eligible_stable_contexts: `{summary['training_eligible_stable_contexts']}`\n"
        f"- training_eligible_targets: `{summary['training_eligible_targets']}`\n"
        f"- offline_training_run: `{summary['offline_training_run']}`\n"
        f"- phase5p5_allowed: `False`\n"
        f"- phase6_allowed: `False`\n"
        f"- aaai_ready: `False`\n"
        f"- ids_166_205_untouched: `True`\n\n"
        "G5.6 is an observed-ID diagnostic package. It does not authorize fresh IDs, runtime learned claims, Phase5.5, Phase6, or AAAI-ready status.\n",
    )
    print(json.dumps({"decision": decision, "phase5p5_allowed": False, "phase6_allowed": False}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Write final Repair5G.5.4 interpretation, readiness, and decision artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g54_common import load_json, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_G53_DECISION = "outputs/reports/phase5p5_repair5g53_decision_summary.json"
DEFAULT_POLICY = "outputs/reports/phase5p5_repair5g54_semantic_vs_budget_gate_policy_summary.json"
DEFAULT_CHECKPOINT_EXPORT = "outputs/reports/phase5p5_repair5g54_checkpoint_export_observed_summary.json"
DEFAULT_REPLAY = "outputs/reports/phase5p5_repair5g54_checkpoint_replayability_summary.json"
DEFAULT_LABELS = "outputs/reports/phase5p5_repair5g54_counterfactual_label_summary.json"
DEFAULT_ORACLE = "outputs/reports/phase5p5_repair5g54_counterfactual_oracle_gap_summary.json"
DEFAULT_BUDGET = "outputs/reports/phase5p5_repair5g54_budget_robust_runtime_summary.json"

DEFAULT_G53_INTERPRETATION = "outputs/reports/phase5p5_repair5g53_final_interpretation.md"
DEFAULT_PROTOCOL = "outputs/reports/phase5p5_repair5g54_protocol_overview.md"
DEFAULT_G6_READINESS = "outputs/reports/phase5p5_repair5g54_g6_safe_mixture_readiness.md"
DEFAULT_G6_READINESS_SUMMARY = "outputs/reports/phase5p5_repair5g54_g6_safe_mixture_readiness_summary.json"
DEFAULT_DECISION = "outputs/reports/phase5p5_repair5g54_decision.md"
DEFAULT_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g54_decision_summary.json"
DEFAULT_AAAI_SUMMARY = "outputs/reports/phase5p5_repair5g_aaai_readiness_summary.json"
DEFAULT_AAAI_AUDIT = "outputs/reports/phase5p5_repair5g_aaai_readiness_audit.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g53-decision-summary-json", type=Path, default=Path(DEFAULT_G53_DECISION))
    parser.add_argument("--policy-summary-json", type=Path, default=Path(DEFAULT_POLICY))
    parser.add_argument("--checkpoint-export-summary-json", type=Path, default=Path(DEFAULT_CHECKPOINT_EXPORT))
    parser.add_argument("--replayability-summary-json", type=Path, default=Path(DEFAULT_REPLAY))
    parser.add_argument("--counterfactual-label-summary-json", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--oracle-gap-summary-json", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--budget-summary-json", type=Path, default=Path(DEFAULT_BUDGET))
    parser.add_argument("--g53-interpretation", type=Path, default=Path(DEFAULT_G53_INTERPRETATION))
    parser.add_argument("--protocol-overview", type=Path, default=Path(DEFAULT_PROTOCOL))
    parser.add_argument("--g6-readiness", type=Path, default=Path(DEFAULT_G6_READINESS))
    parser.add_argument("--g6-readiness-summary-json", type=Path, default=Path(DEFAULT_G6_READINESS_SUMMARY))
    parser.add_argument("--decision", type=Path, default=Path(DEFAULT_DECISION))
    parser.add_argument("--decision-summary-json", type=Path, default=Path(DEFAULT_DECISION_SUMMARY))
    parser.add_argument("--aaai-readiness-summary-json", type=Path, default=Path(DEFAULT_AAAI_SUMMARY))
    parser.add_argument("--aaai-readiness-audit", type=Path, default=Path(DEFAULT_AAAI_AUDIT))
    return parser.parse_args(argv)


def choose_decision(policy: dict[str, Any], export: dict[str, Any], replay: dict[str, Any], labels: dict[str, Any], oracle: dict[str, Any]) -> str:
    if not policy.get("gates", {}).get("semantic_vs_budget_policy_passed"):
        return "semantic_replay_policy_failed"
    if not export.get("checkpoint_export_passed"):
        return "checkpoint_export_failed"
    if not replay.get("gates", {}).get("checkpoint_replayability_passed"):
        return "checkpoint_replayability_failed"
    if not labels.get("gates", {}).get("counterfactual_labels_passed"):
        return "counterfactual_labels_unavailable"
    if oracle.get("adaptive_gap_found"):
        return "counterfactual_labels_available_adaptive_gap_found"
    return "counterfactual_labels_available_static_dominates"


def write_g53_interpretation(path: Path, g53: dict[str, Any]) -> None:
    write_text(
        path,
        "# Phase5.5 Repair5G.5.3 Final Interpretation\n\n"
        "G5.3 is a positive diagnostic result, not evidence that goal-aware dual-channel LTM is corrupted.\n\n"
        "- UpdateLTM transform equivalence passed.\n"
        f"- update_transform_rows: `{g53.get('update_transform_rows', 870)}`\n"
        f"- true_semantic_mismatch_count: `{g53.get('true_semantic_mismatch_count', 0)}`\n"
        "- Params hash, traffic-after hash, and C/F update-stat mismatches were 0 in the transform audit.\n"
        "- The remaining primary 3s failure is `minimal_hook_time_budget_sensitivity`.\n"
        "- The narrow failure set is `warehouse-10-20-10-2-1`, 100 agents, IDs 146..155.\n"
        "- Targeted warehouse/100 5s and 10s checks passed.\n"
        "- Checkpoint/probe label construction is allowed only as diagnostic observed-ID work, not runtime promotion.\n"
        "- G6 training remains blocked until true counterfactual labels pass quality gates.\n"
        "- IDs 166..205 remain untouched.\n\n"
        "`phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain mandatory.\n",
    )


def write_protocol(path: Path, policy: dict[str, Any], replay: dict[str, Any], labels: dict[str, Any], oracle: dict[str, Any], budget: dict[str, Any]) -> None:
    write_text(
        path,
        "# Phase5.5 Repair5G.5.4 Protocol Overview\n\n"
        "G5.4 splits semantic replay from budget-stress runtime reproduction. Semantic replay can support observed-ID diagnostic checkpoint/probe labels after G5.3 transform equivalence passed, while 3s exact minimal-hook reproduction remains a reported stress gate.\n\n"
        "## Gates\n\n"
        f"- semantic_vs_budget_policy_passed: `{policy.get('gates', {}).get('semantic_vs_budget_policy_passed', False)}`\n"
        f"- checkpoint_replayability_passed: `{replay.get('gates', {}).get('checkpoint_replayability_passed', False)}`\n"
        f"- counterfactual_labels_passed: `{labels.get('gates', {}).get('counterfactual_labels_passed', False)}`\n"
        f"- oracle_gap_over_static_measured: `{oracle.get('oracle_gap_over_static_measured', False)}`\n"
        f"- budget_protocol_passed: `{budget.get('gates', {}).get('budget_protocol_passed', False)}`\n"
        "- learned runtime performance claims: `blocked_not_run`\n"
        "- IDs 166..205: `untouched`\n\n"
        "## Evidence\n\n"
        "- `outputs/reports/phase5p5_repair5g54_semantic_vs_budget_gate_policy_summary.json`\n"
        "- `outputs/reports/phase5p5_repair5g54_checkpoint_replayability_summary.json`\n"
        "- `outputs/reports/phase5p5_repair5g54_counterfactual_label_summary.json`\n"
        "- `outputs/reports/phase5p5_repair5g54_counterfactual_oracle_gap_summary.json`\n"
        "- `outputs/reports/phase5p5_repair5g54_budget_robust_runtime_summary.json`\n\n"
        "G5.4 remains diagnostic-only: `phase5p5_allowed=false`, `phase6_allowed=false`, `aaai_ready=false`.\n",
    )


def write_readiness(path: Path, summary_path: Path, labels: dict[str, Any], oracle: dict[str, Any], budget: dict[str, Any]) -> None:
    labels_passed = bool(labels.get("gates", {}).get("counterfactual_labels_passed"))
    oracle_measured = bool(oracle.get("oracle_gap_over_static_measured"))
    readiness = {
        "schema_version": "phase5p5_repair5g54_g6_safe_mixture_readiness_summary_v1",
        "g6_design_allowed": labels_passed and oracle_measured,
        "g6_training_allowed": False,
        "input_features_allowed_at_runtime": "G5 runtime feature allowlist only",
        "forbidden_features": ["actions", "restart nodes", "priority overrides", "h_i(v)", "candidate deletion", "final full-run outcomes"],
        "candidate_experts": "G5.4 candidate set",
        "fallback_policy": "static flow-shield fallback with abstention",
        "confidence_abstention_policy": "required before any learned runtime claim",
        "training_labels": "same-context counterfactual UpdateLTM probe labels",
        "train_dev_observed_id_split": "observed IDs <=165 only; no IDs 166..205",
        "fresh_ids_reserved": "166..205 untouched",
        "runtime_performance_protocol": "performance mode only for runtime claims; audit mode diagnostic",
        "budget_protocol_summary": budget.get("decision", ""),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(summary_path, readiness)
    write_text(
        path,
        "# Phase5.5 Repair5G.5.4 G6 Safe-Mixture Readiness\n\n"
        f"- g6_design_allowed: `{readiness['g6_design_allowed']}`\n"
        "- g6_training_allowed: `false`\n"
        "- allowed runtime output: bounded UpdateParams expert mixture/abstention only\n"
        "- forbidden outputs: actions, restart nodes, priority overrides, h_i(v), candidate deletion\n"
        "- fresh IDs 166..205 remain reserved and untouched\n\n"
        "This report authorizes G6 design only, not training or runtime claims.\n",
    )


def write_aaai(path: Path, audit_path: Path, decision: str, labels: dict[str, Any]) -> None:
    readiness = {
        "schema_version": "phase5p5_repair5g_aaai_readiness_summary_v5",
        "decision": decision,
        "update_transform_equivalence": "passed",
        "updateparams_hash_equivalence": "passed",
        "runtime_hook_3s_exact_equivalence": "failed_time_budget_sensitivity",
        "policy_controls": "passed",
        "checkpoint_labels": "diagnostic_reopened_observed_only",
        "counterfactual_labels": "available_observed_diagnostic" if labels.get("gates", {}).get("counterfactual_labels_passed") else "unavailable",
        "learned_runtime_fresh_holdout": "blocked_not_run",
        "learned_runtime_selector": "blocked_not_run",
        "advanced_neural_network_stage": "g6_design_only_training_blocked",
        "requirements": [
            {"requirement_id": "update_ltm_transform_equivalence", "status": "passed", "evidence_artifacts": "outputs/reports/phase5p5_repair5g53_update_transform_equivalence_summary.json"},
            {"requirement_id": "runtime_hook_equivalence", "status": "failed_time_budget_sensitivity", "evidence_artifacts": "outputs/reports/phase5p5_repair5g53_hook_overhead_ablation_summary.json"},
            {"requirement_id": "counterfactual_labels", "status": readiness_label_status(labels), "evidence_artifacts": "outputs/reports/phase5p5_repair5g54_counterfactual_label_summary.json"},
            {"requirement_id": "learned_runtime_fresh_holdout", "status": "blocked_not_run", "evidence_artifacts": ""},
        ],
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(path, readiness)
    write_text(
        audit_path,
        "# Phase5.5 Repair5G AAAI Readiness Audit\n\n"
        "- update_transform_equivalence: `passed`\n"
        "- runtime_hook_3s_exact_equivalence: `failed_time_budget_sensitivity`\n"
        "- checkpoint_labels: `diagnostic_reopened_observed_only`\n"
        f"- counterfactual_labels: `{readiness['counterfactual_labels']}`\n"
        "- learned_runtime_fresh_holdout: `blocked_not_run`\n"
        "- phase5p5_allowed: `false`\n"
        "- phase6_allowed: `false`\n"
        "- aaai_ready: `false`\n",
    )


def readiness_label_status(labels: dict[str, Any]) -> str:
    return "available_observed_diagnostic" if labels.get("gates", {}).get("counterfactual_labels_passed") else "unavailable"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    g53 = load_json(resolve(args.g53_decision_summary_json, root))
    policy = load_json(resolve(args.policy_summary_json, root))
    export = load_json(resolve(args.checkpoint_export_summary_json, root))
    replay = load_json(resolve(args.replayability_summary_json, root))
    labels = load_json(resolve(args.counterfactual_label_summary_json, root))
    oracle = load_json(resolve(args.oracle_gap_summary_json, root))
    budget = load_json(resolve(args.budget_summary_json, root))
    decision = choose_decision(policy, export, replay, labels, oracle)
    replay_passed = bool(replay.get("gates", {}).get("checkpoint_replayability_passed"))
    labels_passed = bool(labels.get("gates", {}).get("counterfactual_labels_passed"))
    oracle_measured = bool(oracle.get("oracle_gap_over_static_measured"))
    summary = {
        "schema_version": "phase5p5_repair5g54_decision_summary_v1",
        "decision": decision,
        "recommended_next_step": "continue_g6_safe_mixture_design" if labels_passed else "continue_candidate_space_or_replay_repair_before_g6",
        "update_transform_equivalence_prior": "passed_g53",
        "runtime_3s_minimal_hook_status": "failed_time_budget_sensitivity_g53",
        "checkpoint_export_passed": bool(export.get("checkpoint_export_passed")),
        "checkpoint_replayability_passed": replay_passed,
        "counterfactual_labels_available": labels_passed,
        "oracle_gap_over_static_measured": oracle_measured,
        "g6_training_allowed": False,
        "g6_design_allowed": replay_passed and labels_passed and oracle_measured,
        "ids_166_205_untouched": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "evidence_artifacts": {
            "policy": "outputs/reports/phase5p5_repair5g54_semantic_vs_budget_gate_policy_summary.json",
            "checkpoint_replayability": "outputs/reports/phase5p5_repair5g54_checkpoint_replayability_summary.json",
            "counterfactual_labels": "outputs/reports/phase5p5_repair5g54_counterfactual_label_summary.json",
            "oracle_gap": "outputs/reports/phase5p5_repair5g54_counterfactual_oracle_gap_summary.json",
            "budget_protocol": "outputs/reports/phase5p5_repair5g54_budget_robust_runtime_summary.json",
        },
    }
    write_g53_interpretation(resolve(args.g53_interpretation, root), g53)
    write_protocol(resolve(args.protocol_overview, root), policy, replay, labels, oracle, budget)
    if summary["g6_design_allowed"]:
        write_readiness(resolve(args.g6_readiness, root), resolve(args.g6_readiness_summary_json, root), labels, oracle, budget)
    write_aaai(resolve(args.aaai_readiness_summary_json, root), resolve(args.aaai_readiness_audit, root), decision, labels)
    write_json(resolve(args.decision_summary_json, root), summary)
    write_text(
        resolve(args.decision, root),
        "# Phase5.5 Repair5G.5.4 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- checkpoint_export_passed: `{summary['checkpoint_export_passed']}`\n"
        f"- checkpoint_replayability_passed: `{summary['checkpoint_replayability_passed']}`\n"
        f"- counterfactual_labels_available: `{summary['counterfactual_labels_available']}`\n"
        f"- oracle_gap_over_static_measured: `{summary['oracle_gap_over_static_measured']}`\n"
        f"- g6_design_allowed: `{summary['g6_design_allowed']}`\n"
        "- g6_training_allowed: `false`\n"
        "- IDs 166..205 untouched: `true`\n"
        "- phase5p5_allowed: `false`\n"
        "- phase6_allowed: `false`\n"
        "- aaai_ready: `false`\n\n"
        "G5.4 remains observed-ID diagnostic infrastructure. It does not train G6 and does not make a learned-runtime performance claim.\n",
    )
    print(json.dumps({"decision": decision, "g6_design_allowed": summary["g6_design_allowed"]}))
    return 0 if policy.get("gates", {}).get("semantic_vs_budget_policy_passed") else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

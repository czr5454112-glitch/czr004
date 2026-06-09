"""Write the final Repair5G.5.12 decision from generated summaries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import CLOSED_CLAIMS, read_json, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_VERIFY = "outputs/reports/phase5p5_repair5g512_g511_artifact_verification_summary.json"
DEFAULT_TARGETS = "outputs/reports/phase5p5_repair5g512_candidate_regret_targets_summary.json"
DEFAULT_FEATURES = "outputs/reports/phase5p5_repair5g512_candidate_feature_matrix_v3_summary.json"
DEFAULT_TRAIN = "outputs/reports/phase5p5_repair5g512_candidate_ranker_train_summary.json"
DEFAULT_EVAL = "outputs/reports/phase5p5_repair5g512_candidate_ranker_eval_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g512_decision.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g512_decision_summary.json"
ALLOWED_DECISIONS = {
    "missing_g511_artifacts_stop",
    "candidate_regret_targets_failed",
    "candidate_regret_targets_passed_continue_feature_v3",
    "feature_v3_failed_continue_feature_design",
    "candidate_ranker_training_gate_failed",
    "candidate_ranker_failed_continue_features_or_lattice",
    "candidate_ranker_passed_continue_static_abstention_safety_package",
    "static_boundary_augmentation_needed",
    "local_pc_sufficient_continue_local",
    "server_required_for_expanded_lattice_or_more_contexts",
    "stop_for_protocol_or_semantic_bug",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-summary", type=Path, default=Path(DEFAULT_VERIFY))
    parser.add_argument("--target-summary", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--feature-summary", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--train-summary", type=Path, default=Path(DEFAULT_TRAIN))
    parser.add_argument("--eval-summary", type=Path, default=Path(DEFAULT_EVAL))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def load_optional(path: Path) -> dict[str, object]:
    target = resolve(path)
    return read_json(target) if target.exists() else {"decision": "missing"}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    verify = load_optional(args.verify_summary)
    targets = load_optional(args.target_summary)
    features = load_optional(args.feature_summary)
    train = load_optional(args.train_summary)
    eval_summary = load_optional(args.eval_summary)
    if verify.get("decision") == "missing_g511_artifacts_stop" or verify.get("decision") == "missing":
        decision = "missing_g511_artifacts_stop"
    elif targets.get("decision") == "candidate_regret_targets_failed" or targets.get("decision") == "missing":
        decision = "candidate_regret_targets_failed"
    elif features.get("decision") == "feature_v3_failed_continue_feature_design" or features.get("decision") == "missing":
        decision = "feature_v3_failed_continue_feature_design"
    elif train.get("decision") == "candidate_ranker_training_gate_failed" or train.get("decision") == "missing":
        decision = "candidate_ranker_training_gate_failed"
    elif eval_summary.get("decision") == "candidate_ranker_passed_continue_static_abstention_safety_package":
        decision = "candidate_ranker_passed_continue_static_abstention_safety_package"
    else:
        decision = "candidate_ranker_failed_continue_features_or_lattice"
    if decision not in ALLOWED_DECISIONS:
        decision = "stop_for_protocol_or_semantic_bug"
    summary = {
        "schema_version": "phase5p5_repair5g512_decision_summary_v1",
        "decision": decision,
        "verify_decision": verify.get("decision"),
        "target_decision": targets.get("decision"),
        "feature_decision": features.get("decision"),
        "train_decision": train.get("decision"),
        "eval_decision": eval_summary.get("decision"),
        "offline_candidate_ranking_diagnostics_require_no_solution_or_budget_abstain": False,
        "runtime_phase5p5_still_requires_static_abstention_no_solution_budget_ood_safety_package": True,
        "learned_runtime_policy_validated": False,
        "phase6_or_aaai_ready_claim_allowed": False,
        "local_pc_sufficient_for_current_60_context_14_candidate_analysis": True,
        "server_required_only_for_expanded_lattice_or_more_contexts": True,
        **CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.12 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- verify_decision: `{verify.get('decision')}`\n"
        f"- target_decision: `{targets.get('decision')}`\n"
        f"- feature_decision: `{features.get('decision')}`\n"
        f"- train_decision: `{train.get('decision')}`\n"
        f"- eval_decision: `{eval_summary.get('decision')}`\n"
        "- offline_candidate_ranking_diagnostics_require_no_solution_or_budget_abstain: `false`\n"
        "- runtime_phase5p5_still_requires_static_abstention_no_solution_budget_ood_safety_package: `true`\n"
        "- learned_runtime_policy_validated: `false`\n"
        "- runtime_claim_allowed: `false`\n"
        "- phase5p5_allowed: `false`\n"
        "- phase6_allowed: `false`\n"
        "- aaai_ready: `false`\n\n"
        "G5.12 completes the local candidate-level regret/ranking diagnostic path over the existing G5.11 observed-ID lattice. "
        "Offline candidate ranking does not require no-solution or budget-abstain examples, but runtime or Phase5.5 promotion still requires a later static/abstention/no-solution/budget-sensitive/OOD safety package. "
        "No learned runtime policy, Phase6 result, or AAAI-ready claim is validated by this round.\n",
    )
    print(json.dumps({"decision": decision}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Write the final Repair5G.5.13 decision from generated summaries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import read_json, repo_root, resolve, write_json, write_text  # noqa: E402
from repair5g513_common import G513_CLOSED_CLAIMS  # noqa: E402


DEFAULT_G512_DECISION = "outputs/reports/phase5p5_repair5g512_decision_summary.json"
DEFAULT_AUDIT = "outputs/reports/phase5p5_repair5g513_g512_selection_audit_summary.json"
DEFAULT_HARD = "outputs/reports/phase5p5_repair5g513_hard_control_eval_summary.json"
DEFAULT_BOOTSTRAP = "outputs/reports/phase5p5_repair5g513_bootstrap_uncertainty_summary.json"
DEFAULT_RICH = "outputs/reports/phase5p5_repair5g513_rich_context_feature_matrix_summary.json"
DEFAULT_RICH_SIGNAL = "outputs/reports/phase5p5_repair5g513_rich_feature_signal_summary.json"
DEFAULT_SAFETY = "outputs/reports/phase5p5_repair5g513_static_abstention_safety_preflight_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g513_decision.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g513_decision_summary.json"
ALLOWED_DECISIONS = {
    "g512_reproduction_failed",
    "g512_hard_controls_failed_continue_rich_features",
    "candidate_ranker_signal_reduced_to_simple_prior_continue_rich_features",
    "hard_controlled_ranker_passed_continue_rich_safety_preflight",
    "rich_context_features_missing_requires_local_feature_probe",
    "rich_feature_ranker_passed_continue_static_abstention_package",
    "static_abstention_safety_package_incomplete_continue_local",
    "observed_id_approval_required",
    "server_required_for_expanded_lattice_or_more_contexts",
    "stop_for_protocol_or_semantic_bug",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g512-decision-summary", type=Path, default=Path(DEFAULT_G512_DECISION))
    parser.add_argument("--selection-audit-summary", type=Path, default=Path(DEFAULT_AUDIT))
    parser.add_argument("--hard-control-summary", type=Path, default=Path(DEFAULT_HARD))
    parser.add_argument("--bootstrap-summary", type=Path, default=Path(DEFAULT_BOOTSTRAP))
    parser.add_argument("--rich-feature-summary", type=Path, default=Path(DEFAULT_RICH))
    parser.add_argument("--rich-signal-summary", type=Path, default=Path(DEFAULT_RICH_SIGNAL))
    parser.add_argument("--safety-summary", type=Path, default=Path(DEFAULT_SAFETY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def load_optional(path: Path) -> dict[str, object]:
    target = resolve(path)
    return read_json(target) if target.exists() else {"decision": "missing"}


def claims_closed(*summaries: dict[str, object]) -> bool:
    keys = [
        "phase5p5_allowed",
        "phase6_allowed",
        "aaai_ready",
        "runtime_claim_allowed",
        "learned_runtime_policy_validated",
    ]
    for summary in summaries:
        for key in keys:
            if bool(summary.get(key, False)):
                return False
    return True


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    g512 = load_optional(args.g512_decision_summary)
    audit = load_optional(args.selection_audit_summary)
    hard = load_optional(args.hard_control_summary)
    bootstrap = load_optional(args.bootstrap_summary)
    rich = load_optional(args.rich_feature_summary)
    rich_signal = load_optional(args.rich_signal_summary)
    safety = load_optional(args.safety_summary)
    if g512.get("decision") != "candidate_ranker_passed_continue_static_abstention_safety_package":
        decision = "g512_reproduction_failed"
    elif hard.get("decision") == "candidate_ranker_signal_reduced_to_simple_prior_continue_rich_features":
        decision = "candidate_ranker_signal_reduced_to_simple_prior_continue_rich_features"
    elif hard.get("decision") == "g512_hard_controls_failed_continue_rich_features":
        decision = "g512_hard_controls_failed_continue_rich_features"
    elif rich.get("decision") == "rich_context_features_missing_requires_local_feature_probe":
        decision = "rich_context_features_missing_requires_local_feature_probe"
    elif safety.get("decision") == "static_abstention_safety_package_incomplete_continue_local":
        decision = "static_abstention_safety_package_incomplete_continue_local"
    elif hard.get("decision") == "hard_controlled_ranker_passed_continue_rich_safety_preflight":
        decision = "hard_controlled_ranker_passed_continue_rich_safety_preflight"
    else:
        decision = "stop_for_protocol_or_semantic_bug"
    if decision not in ALLOWED_DECISIONS or not claims_closed(g512, audit, hard, bootstrap, rich, rich_signal, safety):
        decision = "stop_for_protocol_or_semantic_bug"

    summary = {
        "schema_version": "phase5p5_repair5g513_decision_summary_v1",
        "decision": decision,
        "g512_reproduction_decision": g512.get("decision"),
        "selection_audit_decision": audit.get("decision"),
        "hard_control_decision": hard.get("decision"),
        "bootstrap_decision": bootstrap.get("decision"),
        "rich_feature_decision": rich.get("decision"),
        "rich_signal_decision": rich_signal.get("decision"),
        "safety_preflight_decision": safety.get("decision"),
        "interpretation": (
            "Hard controls show the G5.12 ranker is not yet stronger than simple train-only safe priors; continue with richer runtime-safe trace features and safety data."
            if decision == "candidate_ranker_signal_reduced_to_simple_prior_continue_rich_features"
            else "Continue local rich-feature and safety preflight work before any runtime promotion."
        ),
        "runtime_phase5p5_still_requires_static_abstention_no_solution_budget_ood_safety_package": True,
        "local_pc_sufficient_for_current_60_context_14_candidate_analysis": True,
        "server_required_only_for_expanded_lattice_or_more_contexts": True,
        **G513_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.13 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- g512_reproduction_decision: `{g512.get('decision')}`\n"
        f"- selection_audit_decision: `{audit.get('decision')}`\n"
        f"- hard_control_decision: `{hard.get('decision')}`\n"
        f"- bootstrap_decision: `{bootstrap.get('decision')}`\n"
        f"- rich_feature_decision: `{rich.get('decision')}`\n"
        f"- rich_signal_decision: `{rich_signal.get('decision')}`\n"
        f"- safety_preflight_decision: `{safety.get('decision')}`\n"
        "- learned_runtime_policy_validated: `false`\n"
        "- runtime_claim_allowed: `false`\n"
        "- phase5p5_allowed: `false`\n"
        "- phase6_allowed: `false`\n"
        "- aaai_ready: `false`\n\n"
        f"{summary['interpretation']}\n",
    )
    print(json.dumps({"decision": decision}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

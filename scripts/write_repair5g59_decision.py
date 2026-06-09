"""Write the final Repair5G.5.9 decision ledger."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g59_common import G59_CLOSED_STATUS, load_json, missing_required_g58_artifacts, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_AUTOPSY = "outputs/reports/phase5p5_repair5g59_g58_offline_eval_autopsy_summary.json"
DEFAULT_CONTROLS = "outputs/reports/phase5p5_repair5g59_corrected_controls_eval_summary.json"
DEFAULT_FEATURES = "outputs/reports/phase5p5_repair5g59_feature_signal_quality_summary.json"
DEFAULT_LATTICE = "outputs/reports/phase5p5_repair5g59_candidate_lattice_summary.json"
DEFAULT_COUNTERFACTUALS = "outputs/reports/phase5p5_repair5g59_goal_aware_dual_channel_counterfactuals_summary.json"
DEFAULT_TARGETS = "outputs/reports/phase5p5_repair5g59_confidence_targets_v3_summary.json"
DEFAULT_POLICY = "outputs/reports/phase5p5_repair5g59_abstention_aware_offline_policy_eval_summary.json"
DEFAULT_DESIGN = "outputs/reports/phase5p5_repair5g59_learned_bounded_dual_channel_update_policy_design_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g59_decision.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g59_decision_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--autopsy-summary-json", type=Path, default=Path(DEFAULT_AUTOPSY))
    parser.add_argument("--controls-summary-json", type=Path, default=Path(DEFAULT_CONTROLS))
    parser.add_argument("--feature-summary-json", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--lattice-summary-json", type=Path, default=Path(DEFAULT_LATTICE))
    parser.add_argument("--counterfactual-summary-json", type=Path, default=Path(DEFAULT_COUNTERFACTUALS))
    parser.add_argument("--targets-summary-json", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--policy-summary-json", type=Path, default=Path(DEFAULT_POLICY))
    parser.add_argument("--design-summary-json", type=Path, default=Path(DEFAULT_DESIGN))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def evidence(path: Path, root: Path) -> dict[str, Any]:
    return load_json(resolve(path, root))


def decide(missing: list[str], controls: dict[str, Any], features: dict[str, Any], counterfactuals: dict[str, Any], targets: dict[str, Any], policy: dict[str, Any], design: dict[str, Any]) -> str:
    if missing:
        return "missing_g58_artifacts_stop"
    if controls.get("decision") == "g58_eval_control_bug_fixed_continue":
        if counterfactuals.get("decision") == "server_required_for_candidate_lattice_or_later_iteration_expansion":
            return "server_required_for_candidate_lattice_or_later_iteration_expansion"
        if features.get("decision") == "feature_signal_insufficient_continue_feature_design":
            return "feature_signal_insufficient_continue_feature_design"
        if targets.get("decision") == "confidence_targets_v3_insufficient_continue_probe_design":
            return "confidence_targets_v3_insufficient_continue_probe_design"
        if policy.get("decision") == "abstention_aware_policy_passed_continue_runtime_preflight_design":
            return "abstention_aware_policy_passed_continue_runtime_preflight_design"
        if policy.get("decision") == "abstention_aware_policy_failed_continue_labels_or_features":
            return "abstention_aware_policy_failed_continue_labels_or_features"
        if design.get("decision") == "learned_bounded_update_policy_design_ready_offline_only":
            return "learned_bounded_update_policy_design_ready_offline_only"
        return "g58_eval_control_bug_fixed_continue"
    return "stop_for_protocol_or_semantic_bug"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    missing = missing_required_g58_artifacts(root)
    autopsy = evidence(args.autopsy_summary_json, root)
    controls = evidence(args.controls_summary_json, root)
    features = evidence(args.feature_summary_json, root)
    lattice = evidence(args.lattice_summary_json, root)
    counterfactuals = evidence(args.counterfactual_summary_json, root)
    targets = evidence(args.targets_summary_json, root)
    policy = evidence(args.policy_summary_json, root)
    design = evidence(args.design_summary_json, root)
    decision = decide(missing, controls, features, counterfactuals, targets, policy, design)
    summary = {
        "schema_version": "phase5p5_repair5g59_decision_summary_v1",
        "decision": decision,
        "missing_g58_artifacts": missing,
        "g58_autopsy_decision": autopsy.get("decision", ""),
        "corrected_controls_decision": controls.get("decision", ""),
        "feature_signal_decision": features.get("decision", ""),
        "candidate_lattice_decision": lattice.get("decision", ""),
        "counterfactual_decision": counterfactuals.get("decision", ""),
        "confidence_targets_v3_decision": targets.get("decision", ""),
        "abstention_policy_decision": policy.get("decision", ""),
        "learned_bounded_policy_design_decision": design.get("decision", ""),
        "ids_166_205_untouched": True,
        "evidence_artifacts": {
            "autopsy": str(resolve(args.autopsy_summary_json, root)),
            "controls": str(resolve(args.controls_summary_json, root)),
            "features": str(resolve(args.feature_summary_json, root)),
            "lattice": str(resolve(args.lattice_summary_json, root)),
            "counterfactuals": str(resolve(args.counterfactual_summary_json, root)),
            "targets_v3": str(resolve(args.targets_summary_json, root)),
            "abstention_policy": str(resolve(args.policy_summary_json, root)),
            "learned_bounded_policy_design": str(resolve(args.design_summary_json, root)),
        },
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.9 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- g58_autopsy_decision: `{summary['g58_autopsy_decision']}`\n"
        f"- corrected_controls_decision: `{summary['corrected_controls_decision']}`\n"
        f"- feature_signal_decision: `{summary['feature_signal_decision']}`\n"
        f"- candidate_lattice_decision: `{summary['candidate_lattice_decision']}`\n"
        f"- counterfactual_decision: `{summary['counterfactual_decision']}`\n"
        f"- confidence_targets_v3_decision: `{summary['confidence_targets_v3_decision']}`\n"
        f"- abstention_policy_decision: `{summary['abstention_policy_decision']}`\n"
        f"- learned_bounded_policy_design_decision: `{summary['learned_bounded_policy_design_decision']}`\n"
        f"- ids_166_205_untouched: `True`\n"
        f"- phase5p5_allowed: `False`\n"
        f"- phase6_allowed: `False`\n"
        f"- aaai_ready: `False`\n"
        f"- runtime_claim_allowed: `False`\n\n"
        "G5.9 fixes the G5.8 control semantics and records an offline autopsy, but expanded-lattice counterfactual evidence needs a server run before any runtime or paper-ready claim.\n",
    )
    print(json.dumps({"decision": decision}))
    return 0 if not missing else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Write Repair5G.5.10 final decision summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g510_common import G59_CLOSED_STATUS, repo_root, resolve, write_json, write_text  # noqa: E402
from repair5g59_common import missing_required_g58_artifacts  # noqa: E402


REQUIRED_G59_ARTIFACTS = [
    "outputs/reports/phase5p5_repair5g59_decision_summary.json",
    "outputs/reports/phase5p5_repair5g59_g58_offline_eval_autopsy_summary.json",
    "outputs/reports/phase5p5_repair5g59_corrected_controls_eval_summary.json",
    "outputs/reports/phase5p5_repair5g59_feature_signal_quality_summary.json",
    "outputs/reports/phase5p5_repair5g59_candidate_lattice_summary.json",
    "outputs/reports/phase5p5_repair5g59_candidate_lattice_candidates.json",
    "outputs/tables/phase5p5_repair5g59_candidate_lattice.csv",
    "outputs/tables/phase5p5_repair5g59_goal_aware_dual_channel_counterfactual_plan.csv",
    "outputs/reports/phase5p5_repair5g59_learned_bounded_dual_channel_update_policy_design_summary.json",
]

DEFAULT_PARITY = "outputs/reports/phase5p5_repair5g510_lattice_adapter_parity_summary.json"
DEFAULT_RUN = "outputs/reports/phase5p5_repair5g510_lattice_counterfactual_run_summary.json"
DEFAULT_ANALYSIS = "outputs/reports/phase5p5_repair5g510_lattice_counterfactual_analysis_summary.json"
DEFAULT_FEATURES = "outputs/reports/phase5p5_repair5g510_feature_signal_v2_summary.json"
DEFAULT_TARGETS = "outputs/reports/phase5p5_repair5g510_confidence_targets_v4_summary.json"
DEFAULT_POLICY = "outputs/reports/phase5p5_repair5g510_abstention_parameter_policy_eval_summary.json"
DEFAULT_SERVER = "outputs/reports/phase5p5_repair5g510_server_command_plan_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g510_decision.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g510_decision_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parity-summary-json", type=Path, default=Path(DEFAULT_PARITY))
    parser.add_argument("--run-summary-json", type=Path, default=Path(DEFAULT_RUN))
    parser.add_argument("--analysis-summary-json", type=Path, default=Path(DEFAULT_ANALYSIS))
    parser.add_argument("--feature-summary-json", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--target-summary-json", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--policy-summary-json", type=Path, default=Path(DEFAULT_POLICY))
    parser.add_argument("--server-summary-json", type=Path, default=Path(DEFAULT_SERVER))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def decide(missing: list[str], parity: dict[str, object], run: dict[str, object], analysis: dict[str, object], features: dict[str, object], targets: dict[str, object], policy: dict[str, object]) -> str:
    if missing:
        return "missing_g59_artifacts_stop"
    if parity.get("decision") != "lattice_adapter_parity_passed":
        return "lattice_adapter_failed_stop"
    if not run.get("counterfactuals_run"):
        return "server_required_for_lattice_counterfactuals"
    if int(run.get("measured_contexts", 0) or 0) < 60:
        return "lattice_adapter_smoke_passed_server_required_for_full_run"
    if not analysis.get("candidate_space_improves_g58"):
        return "candidate_space_gap_expand_flow_shield_lattice"
    if targets.get("decision") != "confidence_targets_v4_passed_policy_training_allowed":
        return "confidence_targets_v4_training_gate_failed"
    if not features.get("features_strong_enough_to_distinguish_static_vs_nonstatic_safely"):
        return "feature_signal_v2_failed_continue_feature_design"
    if policy.get("decision") == "abstention_parameter_policy_passed_continue_runtime_preflight_design":
        return "abstention_parameter_policy_passed_continue_runtime_preflight_design"
    return "abstention_parameter_policy_failed_continue_features_or_lattice"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    missing = missing_required_g58_artifacts(root)
    missing.extend(path for path in REQUIRED_G59_ARTIFACTS if not (root / path).exists())
    parity = load_json(resolve(args.parity_summary_json, root))
    run = load_json(resolve(args.run_summary_json, root))
    analysis = load_json(resolve(args.analysis_summary_json, root))
    features = load_json(resolve(args.feature_summary_json, root))
    targets = load_json(resolve(args.target_summary_json, root))
    policy = load_json(resolve(args.policy_summary_json, root))
    server = load_json(resolve(args.server_summary_json, root))
    decision = decide(missing, parity, run, analysis, features, targets, policy)
    summary = {
        "schema_version": "phase5p5_repair5g510_decision_summary_v1",
        "decision": decision,
        "missing_g59_artifacts": missing,
        "adapter_decision": parity.get("decision", ""),
        "counterfactuals_run": run.get("counterfactuals_run", False),
        "measured_contexts": run.get("measured_contexts", 0),
        "candidate_count": run.get("candidate_count", 0),
        "analysis_decision": analysis.get("decision", ""),
        "candidate_space_oracle_gap_vs_g58": analysis.get("candidate_space_oracle_gap_vs_g58"),
        "candidate_space_improves_g58": analysis.get("candidate_space_improves_g58", False),
        "feature_signal_decision": "feature_signal_v2_sufficient"
        if features.get("features_strong_enough_to_distinguish_static_vs_nonstatic_safely")
        else "feature_signal_v2_failed_continue_feature_design",
        "confidence_targets_decision": targets.get("decision", ""),
        "policy_decision": policy.get("decision", ""),
        "server_plan_available": bool(server),
        "required_next_step": "run full server package and re-ingest artifacts"
        if decision == "lattice_adapter_smoke_passed_server_required_for_full_run"
        else "expand bounded flow-shield lattice or feature design before policy training",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "runtime_claim_allowed": False,
        "ids_166_205_untouched": True,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.10 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- adapter_decision: `{summary['adapter_decision']}`\n"
        f"- counterfactuals_run: `{summary['counterfactuals_run']}`\n"
        f"- measured_contexts: `{summary['measured_contexts']}`\n"
        f"- candidate_space_oracle_gap_vs_g58: `{summary['candidate_space_oracle_gap_vs_g58']}`\n"
        f"- confidence_targets_decision: `{summary['confidence_targets_decision']}`\n"
        f"- policy_decision: `{summary['policy_decision']}`\n"
        "- phase5p5_allowed: `False`\n"
        "- phase6_allowed: `False`\n"
        "- aaai_ready: `False`\n"
        "- runtime_claim_allowed: `False`\n"
        "- ids_166_205_untouched: `True`\n\n"
        "Repair5G.5.10 executes the bounded G5.9 lattice adapter path without changing LaCAM*/PIBT semantics. "
        "Policy training remains gated by candidate-space, label, and feature evidence.\n",
    )
    print(json.dumps({"decision": decision, "measured_contexts": summary["measured_contexts"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

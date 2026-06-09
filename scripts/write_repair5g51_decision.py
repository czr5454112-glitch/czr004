"""Write Repair5G.5.1 final decision and AAAI readiness corrections."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g51_common import load_json, repo_root, resolve, write_csv_rows, write_json, write_text  # noqa: E402


DEFAULT_G5_SMOKE = "outputs/reports/phase5p5_repair5g5_runtime_smoke_summary.json"
DEFAULT_AUTOPSY = "outputs/reports/phase5p5_repair5g5_runtime_selector_failure_autopsy_summary.json"
DEFAULT_SANITY = "outputs/reports/phase5p5_repair5g51_runtime_hook_sanity_summary.json"
DEFAULT_POLICY = "outputs/reports/phase5p5_repair5g51_policy_control_reproducer_summary.json"
DEFAULT_SAFE_SMOKE = "outputs/reports/phase5p5_repair5g51_safe_selector_runtime_smoke_summary.json"
DEFAULT_LABEL_QUALITY = "outputs/reports/phase5p5_repair5g51_counterfactual_label_quality_summary.json"
DEFAULT_MLP = "outputs/reports/phase5p5_repair5g51_small_mlp_selector_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g5-smoke-summary-json", type=Path, default=Path(DEFAULT_G5_SMOKE))
    parser.add_argument("--autopsy-summary-json", type=Path, default=Path(DEFAULT_AUTOPSY))
    parser.add_argument("--sanity-summary-json", type=Path, default=Path(DEFAULT_SANITY))
    parser.add_argument("--policy-summary-json", type=Path, default=Path(DEFAULT_POLICY))
    parser.add_argument("--safe-smoke-summary-json", type=Path, default=Path(DEFAULT_SAFE_SMOKE))
    parser.add_argument("--label-quality-summary-json", type=Path, default=Path(DEFAULT_LABEL_QUALITY))
    parser.add_argument("--mlp-summary-json", type=Path, default=Path(DEFAULT_MLP))
    return parser.parse_args(argv)


def _decision(sanity: dict[str, Any], policy: dict[str, Any], safe: dict[str, Any], quality: dict[str, Any], mlp: dict[str, Any]) -> str:
    if not sanity.get("gates", {}).get("runtime_hook_sanity_passed"):
        return "runtime_hook_bug_blocks_learning"
    if not policy.get("gates", {}).get("policy_control_reproducer_passed"):
        return "policy_control_bug_blocks_learning"
    if safe.get("gates", {}).get("safe_selector_runtime_smoke_passed") and not quality.get("gates", {}).get(
        "counterfactual_label_quality_passed"
    ):
        return "continue_counterfactual_label_collection"
    if safe.get("gates", {}).get("safe_selector_runtime_smoke_passed") and mlp.get("training_started"):
        return "continue_small_neural_selector"
    if safe.get("gates", {}).get("safe_selector_runtime_smoke_passed"):
        return "safe_runtime_bridge_passed_learning_advantage_unclear"
    return "return_to_selector_feature_design"


def _evidence_rows() -> list[dict[str, Any]]:
    return [
        {
            "requirement_id": "runtime_selector_integration",
            "requirement": "G5 runtime selector integration",
            "status": "passed",
            "evidence_artifacts": "outputs/reports/phase5p5_repair5g5_runtime_smoke_summary.json",
            "remaining_work": "",
        },
        {
            "requirement_id": "runtime_selector_smoke",
            "requirement": "G5 learned runtime selector observed-ID smoke",
            "status": "failed",
            "evidence_artifacts": "outputs/reports/phase5p5_repair5g5_runtime_smoke_summary.json",
            "remaining_work": "Use G5.1 safe bridge; do not run fresh learned-runtime IDs from failed selector.",
        },
        {
            "requirement_id": "learned_runtime_selector_performance",
            "requirement": "learned runtime selector performance",
            "status": "failed",
            "evidence_artifacts": "outputs/reports/phase5p5_repair5g5_runtime_selector_failure_autopsy.md",
            "remaining_work": "Counterfactual iteration labels needed before new learned selector.",
        },
        {
            "requirement_id": "learned_runtime_fresh_holdout",
            "requirement": "learned runtime fresh holdout",
            "status": "blocked_not_run",
            "evidence_artifacts": "",
            "remaining_work": "IDs 166..205 remain reserved until a corrected selector is frozen.",
        },
        {
            "requirement_id": "static_flow_shield",
            "requirement": "static/map-agent flow-shield",
            "status": "strong_baseline_not_learned_claim",
            "evidence_artifacts": "outputs/reports/phase5p5_repair5g4_clean_frozen_validation_summary.json",
            "remaining_work": "Do not present as learned-runtime AAAI claim.",
        },
        {
            "requirement_id": "advanced_neural_network_stage",
            "requirement": "advanced neural network stage",
            "status": "blocked_until_safe_runtime_selector_or_counterfactual_labels",
            "evidence_artifacts": "outputs/reports/phase5p5_repair5g51_counterfactual_label_quality_summary.json",
            "remaining_work": "Export replayable checkpoints and collect labels.",
        },
    ]


def _claim_rows() -> list[dict[str, Any]]:
    return [
        {
            "claim_id": "C1",
            "claim_text": "Flow-shield representation remains validated by G2/G4.",
            "allowed_status": "safe_diagnostic",
            "supporting_artifacts": "phase5p5_repair5g4_clean_frozen_validation_summary.json",
            "required_missing_artifacts": "",
            "risk": "Not a learned runtime selector claim.",
            "paper_section": "Results",
        },
        {
            "claim_id": "C2",
            "claim_text": "G5 learned runtime selector improves closed-loop performance.",
            "allowed_status": "forbidden_failed_smoke",
            "supporting_artifacts": "phase5p5_repair5g5_runtime_smoke_summary.json",
            "required_missing_artifacts": "corrected smoke/fresh validation",
            "risk": "Observed smoke was worse than LTM and far worse than static flow-shield.",
            "paper_section": "Results",
        },
        {
            "claim_id": "C3",
            "claim_text": "G5.1 safe bridge is a learned-advantage result.",
            "allowed_status": "forbidden_learning_advantage_unclear",
            "supporting_artifacts": "phase5p5_repair5g51_safe_selector_runtime_smoke_summary.json",
            "required_missing_artifacts": "counterfactual labels or fresh frozen learned selector",
            "risk": "Safe bridge may match static/map-agent flow-shield without adding learned value.",
            "paper_section": "Limitations",
        },
    ]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    g5 = load_json(resolve(args.g5_smoke_summary_json, root))
    autopsy = load_json(resolve(args.autopsy_summary_json, root))
    sanity = load_json(resolve(args.sanity_summary_json, root))
    policy = load_json(resolve(args.policy_summary_json, root))
    safe = load_json(resolve(args.safe_smoke_summary_json, root))
    quality = load_json(resolve(args.label_quality_summary_json, root))
    mlp = load_json(resolve(args.mlp_summary_json, root))
    decision = _decision(sanity, policy, safe, quality, mlp)
    answers = {
        "why_g5_failed": autopsy.get("failure_classification", "offline_to_runtime_selector_transfer_failure"),
        "runtime_hook_reproduced_safe_policies": bool(sanity.get("gates", {}).get("runtime_hook_sanity_passed")),
        "policy_controls_fixed_or_classified": bool(policy.get("gates", {}).get("policy_control_reproducer_passed")),
        "safe_abstention_runtime_smoke_passed": bool(safe.get("gates", {}).get("safe_selector_runtime_smoke_passed")),
        "learned_selection_adds_value_over_static_flow_shield": False,
        "counterfactual_update_ltm_labels_available": bool(
            quality.get("gates", {}).get("counterfactual_label_quality_passed")
        ),
        "small_neural_selector_justified": bool(mlp.get("training_started")),
        "ids_166_205_clean_status": "reserved_not_run_by_g51",
        "next_aaai_relevant_step": "export replayable UpdateLTM checkpoints and collect iteration-level counterfactual labels",
    }
    decision_summary = {
        "schema_version": "phase5p5_repair5g51_decision_summary_v1",
        "decision": decision,
        "answers": answers,
        "g5_runtime_smoke_failed": not bool(g5.get("gates", {}).get("runtime_smoke_gates_passed")),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(root / "outputs/reports/phase5p5_repair5g51_decision_summary.json", decision_summary)
    write_text(
        root / "outputs/reports/phase5p5_repair5g51_decision.md",
        "# Phase5.5 Repair5G.5.1 Decision\n\n"
        f"Decision: `{decision}`\n\n"
        "## Answers\n\n"
        + "\n".join(f"- `{key}`: `{value}`" for key, value in answers.items())
        + "\n\n"
        "`phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain closed. "
        "IDs 166..205 remain reserved and were not used by G5.1.\n",
    )
    write_text(
        root / "outputs/reports/phase5p5_repair5g5_final_interpretation.md",
        "# Phase5.5 Repair5G.5 Final Interpretation\n\n"
        "- G5 runtime integration exists and is auditable.\n"
        "- Runtime learned selector failed observed-ID smoke.\n"
        "- The failure is selector/policy transfer failure, not a flow-shield representation failure.\n"
        "- Static/map-agent flow-shield remains strong.\n"
        "- Random/shuffled diagnostics were much stronger than the learned runtime selector because they routed to the safe static branch.\n"
        "- No frozen learned selector was produced.\n"
        "- No fresh learned-runtime validation was run.\n"
        "- IDs 166..205 remain reserved.\n"
        "- AAAI-ready remains false.\n"
        "- `phase5p5_allowed=false` and `phase6_allowed=false` remain closed.\n",
    )
    write_text(
        root / "outputs/reports/phase5p5_repair5g51_protocol_overview.md",
        "# Phase5.5 Repair5G.5.1 Protocol Overview\n\n"
        "- scope: observed-ID runtime selector failure autopsy and safe bridge only\n"
        "- observed smoke IDs: `126..165`\n"
        "- fresh learned-runtime holdout: `166..205`, still blocked unless corrected selector passes smoke and is frozen\n"
        "- allowed runtime output: bounded UpdateParams candidate id only\n"
        "- forbidden outputs: actions, restarts, priorities, h-values, candidate deletion\n"
        "- AAAI status: `aaai_ready=false`\n"
        "- phase status: `phase5p5_allowed=false`, `phase6_allowed=false`\n",
    )
    write_text(
        root / "docs/aaai_quality_requirements.md",
        "# Repair5G AAAI Quality Requirements\n\n"
        "AAAI-ready learning claims require a learned runtime UpdateLTM selector, clean heldout validation, negative controls, ablations, stress, reproducibility manifests, and a claim ledger.\n\n"
        "- runtime_selector_integration: `passed`\n"
        "- runtime_selector_smoke: `failed`\n"
        "- learned_runtime_selector_performance: `failed`\n"
        "- learned_runtime_fresh_holdout: `blocked_not_run`\n"
        "- static_flow_shield: `strong_baseline_not_learned_claim`\n"
        "- advanced_neural_network_stage: `blocked_until_safe_runtime_selector_or_counterfactual_labels`\n"
        "- aaai_ready: `false`\n"
        "- Phase5.5 and Phase6 remain closed until paper-grade gates pass.\n",
    )
    evidence = _evidence_rows()
    claims = _claim_rows()
    write_csv_rows(root / "outputs/tables/phase5p5_repair5g_aaai_evidence_matrix.csv", evidence)
    write_csv_rows(root / "outputs/tables/phase5p5_repair5g_claim_ledger.csv", claims)
    readiness = {
        "schema_version": "phase5p5_repair5g_aaai_readiness_summary_v2",
        "decision": decision,
        "runtime_selector_integration": "passed",
        "runtime_selector_smoke": "failed",
        "learned_runtime_selector_performance": "failed",
        "learned_runtime_fresh_holdout": "blocked_not_run",
        "aaai_ready": False,
        "static_flow_shield": "strong_baseline_not_learned_claim",
        "advanced_neural_network_stage": "blocked_until_safe_runtime_selector_or_counterfactual_labels",
        "requirements": evidence,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_json(root / "outputs/reports/phase5p5_repair5g_aaai_readiness_summary.json", readiness)
    write_text(
        root / "outputs/reports/phase5p5_repair5g_aaai_readiness_audit.md",
        "# Phase5.5 Repair5G AAAI Readiness Audit\n\n"
        f"Decision state: `{decision}`.\n\n"
        "- runtime_selector_integration: `passed`\n"
        "- runtime_selector_smoke: `failed`\n"
        "- learned_runtime_selector_performance: `failed`\n"
        "- learned_runtime_fresh_holdout: `blocked_not_run`\n"
        "- aaai_ready: `false`\n"
        "- static_flow_shield: `strong_baseline_not_learned_claim`\n"
        "- advanced_neural_network_stage: `blocked_until_safe_runtime_selector_or_counterfactual_labels`\n",
    )
    print(json.dumps({"decision": decision, "aaai_ready": False}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

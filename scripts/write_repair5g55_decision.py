"""Write Repair5G.5.5 interpretation, G6 design, and final decision reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g54_common import G54_ALLOWED_RUNTIME_FEATURES  # noqa: E402
from repair5g55_common import (  # noqa: E402
    G55_BASE_CANDIDATES,
    G55_REQUIRED_FINAL_STATUS,
    load_json,
    repo_root,
    resolve,
    write_json,
    write_text,
)


DEFAULT_G54_DECISION = "outputs/reports/phase5p5_repair5g54_decision_summary.json"
DEFAULT_CANDIDATE = "outputs/reports/phase5p5_repair5g55_candidate_set_audit_summary.json"
DEFAULT_LABEL = "outputs/reports/phase5p5_repair5g55_counterfactual_label_quality_summary.json"
DEFAULT_ORACLE = "outputs/reports/phase5p5_repair5g55_oracle_gap_summary.json"
DEFAULT_BUDGET = "outputs/reports/phase5p5_repair5g55_probe_budget_stability_summary.json"
DEFAULT_FEATURE = "outputs/reports/phase5p5_repair5g55_feature_audit_summary.json"
DEFAULT_G54_INTERPRETATION = "outputs/reports/phase5p5_repair5g54_final_interpretation.md"
DEFAULT_PROTOCOL = "outputs/reports/phase5p5_repair5g55_protocol_overview.md"
DEFAULT_G6_DESIGN = "outputs/reports/phase5p5_repair5g55_g6_safe_mixture_policy_design.md"
DEFAULT_G6_SPEC = "outputs/reports/phase5p5_repair5g55_g6_safe_mixture_policy_spec.json"
DEFAULT_DECISION = "outputs/reports/phase5p5_repair5g55_decision.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g55_decision_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g54-decision-summary-json", type=Path, default=Path(DEFAULT_G54_DECISION))
    parser.add_argument("--candidate-summary-json", type=Path, default=Path(DEFAULT_CANDIDATE))
    parser.add_argument("--label-summary-json", type=Path, default=Path(DEFAULT_LABEL))
    parser.add_argument("--oracle-summary-json", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--budget-summary-json", type=Path, default=Path(DEFAULT_BUDGET))
    parser.add_argument("--feature-summary-json", type=Path, default=Path(DEFAULT_FEATURE))
    parser.add_argument("--g54-interpretation", type=Path, default=Path(DEFAULT_G54_INTERPRETATION))
    parser.add_argument("--protocol-overview", type=Path, default=Path(DEFAULT_PROTOCOL))
    parser.add_argument("--g6-design", type=Path, default=Path(DEFAULT_G6_DESIGN))
    parser.add_argument("--g6-policy-spec-json", type=Path, default=Path(DEFAULT_G6_SPEC))
    parser.add_argument("--decision", type=Path, default=Path(DEFAULT_DECISION))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def choose_decision(candidate: dict[str, Any], label: dict[str, Any], oracle: dict[str, Any], budget: dict[str, Any], feature: dict[str, Any]) -> str:
    if not candidate.get("gates", {}).get("candidate_set_audit_passed", False):
        return "candidate_space_too_small_expand_before_g6"
    if not label.get("gates", {}).get("scaled_counterfactual_label_smoke_passed", False):
        return "scaled_labels_failed"
    if not feature.get("gates", {}).get("feature_audit_passed", False):
        return "feature_leakage_blocks_training"
    if not budget.get("probe_budget_stability_measured", False):
        return "probe_budget_instability_blocks_training"
    oracle_decision = str(oracle.get("decision", ""))
    allowed = {
        "scaled_labels_passed_static_dominates",
        "scaled_labels_passed_adaptive_gap_weak",
        "scaled_labels_passed_adaptive_gap_strong_continue_g6_design",
    }
    return oracle_decision if oracle_decision in allowed else "scaled_labels_passed_adaptive_gap_weak"


def write_g54_interpretation(path: Path, g54: dict[str, Any]) -> None:
    write_text(
        path,
        "# Phase5.5 Repair5G.5.4 Final Interpretation\n\n"
        "- G5.4 succeeded as a label-infrastructure proof.\n"
        "- G5.4 did not train G6.\n"
        "- G5.4 did not make a learned-runtime performance claim.\n"
        "- G5.4 labels were too small for training: 2 contexts and 14 label rows.\n"
        "- Goal-aware dual-channel LTM is not corrupted; the G5.3 transform equivalence prior passed.\n"
        "- The 3s minimal-hook issue remains classified as warehouse/100 deadline sensitivity, not UpdateLTM transform corruption.\n"
        "- IDs 166..205 remain untouched.\n"
        "- `phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain mandatory.\n\n"
        f"Prior G5.4 decision: `{g54.get('decision', '')}`.\n",
    )


def write_protocol(path: Path, label: dict[str, Any]) -> None:
    write_text(
        path,
        "# Phase5.5 Repair5G.5.5 Protocol Overview\n\n"
        "G5.5 scales same-context UpdateLTM labels over observed IDs only, with each label row produced by applying a candidate UpdateParams set to the same pre-update traffic snapshot and trace events, then measuring a short downstream probe.\n\n"
        "Default scope:\n"
        "- maps: `random-32-32-20`, `maze-32-32-4`, `warehouse-10-20-10-2-1`\n"
        "- agents: `50`, `100`\n"
        "- primary observed IDs: `146..165`; stratified smoke may use a smaller observed subset and must report missing target coverage\n"
        "- candidates: the seven compact G5.4 candidates unless explicitly expanded after candidate-set audit\n"
        "- primary short budget: `1000 ms`; stability diagnostics compare `250`, `500`, `1000`, and optional `2000 ms`\n\n"
        f"Current scaled context count: `{label.get('context_count', 0)}`. "
        f"Smoke passed: `{label.get('gates', {}).get('scaled_counterfactual_label_smoke_passed', False)}`. "
        f"Full 120-context target passed: `{label.get('gates', {}).get('scaled_counterfactual_label_target_passed', False)}`.\n\n"
        "No final full-run outcomes are used as per-update labels. G6 training is not part of G5.5.\n",
    )


def g6_spec(candidate: dict[str, Any], label: dict[str, Any], oracle: dict[str, Any], budget: dict[str, Any], feature: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "phase5p5_repair5g55_g6_safe_mixture_policy_spec_v1",
        "method_family": "safe_learned_mixture_over_validated_UpdateLTM_experts",
        "training_allowed": False,
        "runtime_claim_allowed": False,
        "candidate_experts": list(G55_BASE_CANDIDATES),
        "fallback": {
            "default": "repair5g2_best_frozen_static_candidate",
            "high_risk": "additive_ltm_or_c_equiv_baseline",
            "abstention_required": True,
            "confidence_threshold_required": True,
        },
        "allowed_outputs": [
            "mixture_weights_over_safe_updateparams_experts",
            "abstention_probability",
            "optional_bounded_residuals_after_future_gate_only",
        ],
        "forbidden_outputs": [
            "actions",
            "restart nodes",
            "PIBT priorities",
            "h_i(v)",
            "action logits",
            "candidate deletion",
            "collision decisions",
        ],
        "allowed_feature_names": sorted(G54_ALLOWED_RUNTIME_FEATURES),
        "gates_snapshot": {
            "candidate_set_audit_passed": candidate.get("gates", {}).get("candidate_set_audit_passed", False),
            "scaled_label_smoke_passed": label.get("gates", {}).get("scaled_counterfactual_label_smoke_passed", False),
            "scaled_label_target_passed": label.get("gates", {}).get("scaled_counterfactual_label_target_passed", False),
            "oracle_decision": oracle.get("decision", ""),
            "probe_budget_stability_measured": budget.get("probe_budget_stability_measured", False),
            "feature_audit_passed": feature.get("gates", {}).get("feature_audit_passed", False),
        },
        **G55_REQUIRED_FINAL_STATUS,
    }


def write_g6_design(path: Path, spec: dict[str, Any], decision: str) -> None:
    write_text(
        path,
        "# Phase5.5 Repair5G.5.5 G6 Safe Mixture Policy Design\n\n"
        "The first G6 method should be a safe learned mixture over validated UpdateLTM experts, with static flow-shield fallback and abstention. It should not predict actions, priorities, restart nodes, h-values, collision outcomes, or candidate deletion.\n\n"
        "Policy shape:\n"
        "- input: allowed pre-update runtime features, trace aggregates, and C/F traffic summaries only\n"
        "- encoder: small calibrated linear/MLP model first\n"
        "- output: mixture weights over safe experts plus abstention/confidence\n"
        "- fallback: static flow-shield by default; additive or C-equiv only under explicit high-risk abstention\n"
        "- residuals: bounded residuals over flow-shield parameters only after mixture gap and budget stability are validated\n\n"
        f"G5.5 decision feeding this design: `{decision}`.\n"
        f"G6 training allowed now: `{spec['training_allowed']}`.\n",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    g54 = load_json(resolve(args.g54_decision_summary_json, root))
    candidate = load_json(resolve(args.candidate_summary_json, root))
    label = load_json(resolve(args.label_summary_json, root))
    oracle = load_json(resolve(args.oracle_summary_json, root))
    budget = load_json(resolve(args.budget_summary_json, root))
    feature = load_json(resolve(args.feature_summary_json, root))
    decision = choose_decision(candidate, label, oracle, budget, feature)
    spec = g6_spec(candidate, label, oracle, budget, feature)
    write_g54_interpretation(resolve(args.g54_interpretation, root), g54)
    write_protocol(resolve(args.protocol_overview, root), label)
    write_json(resolve(args.g6_policy_spec_json, root), spec)
    write_g6_design(resolve(args.g6_design, root), spec, decision)
    summary = {
        "schema_version": "phase5p5_repair5g55_decision_summary_v1",
        "decision": decision,
        "candidate_set_audit_passed": candidate.get("gates", {}).get("candidate_set_audit_passed", False),
        "scaled_label_smoke_passed": label.get("gates", {}).get("scaled_counterfactual_label_smoke_passed", False),
        "scaled_label_target_passed": label.get("gates", {}).get("scaled_counterfactual_label_target_passed", False),
        "context_count": label.get("context_count", 0),
        "label_rows": label.get("label_rows", 0),
        "oracle_beats_static_fraction": oracle.get("oracle_beats_static_fraction", 0.0),
        "probe_budget_stability_measured": budget.get("probe_budget_stability_measured", False),
        "feature_audit_passed": feature.get("gates", {}).get("feature_audit_passed", False),
        "evidence_artifacts": {
            "candidate_set": str(resolve(args.candidate_summary_json, root)),
            "label_quality": str(resolve(args.label_summary_json, root)),
            "oracle_gap": str(resolve(args.oracle_summary_json, root)),
            "probe_budget_stability": str(resolve(args.budget_summary_json, root)),
            "feature_audit": str(resolve(args.feature_summary_json, root)),
            "g6_policy_spec": str(resolve(args.g6_policy_spec_json, root)),
        },
        **G55_REQUIRED_FINAL_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.decision, root),
        "# Phase5.5 Repair5G.5.5 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- context_count: `{summary['context_count']}`\n"
        f"- label_rows: `{summary['label_rows']}`\n"
        f"- scaled_label_smoke_passed: `{summary['scaled_label_smoke_passed']}`\n"
        f"- scaled_label_target_passed: `{summary['scaled_label_target_passed']}`\n"
        f"- oracle_beats_static_fraction: `{summary['oracle_beats_static_fraction']}`\n"
        f"- probe_budget_stability_measured: `{summary['probe_budget_stability_measured']}`\n"
        f"- feature_audit_passed: `{summary['feature_audit_passed']}`\n"
        "- phase5p5_allowed: `false`\n"
        "- phase6_allowed: `false`\n"
        "- aaai_ready: `false`\n"
        "- g6_training_allowed: `false`\n"
        "- learned_runtime_fresh_holdout: `blocked_not_run`\n\n"
        "G5.5 remains observed-ID diagnostic evidence. It prepares G6 safe-mixture design but does not train or claim a learned runtime method.\n",
    )
    print(json.dumps({"decision": decision, "g6_training_allowed": False}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

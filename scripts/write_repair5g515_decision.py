"""Write the final Repair5G.5.15 decision report and G5.14 interpretation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import read_json, repo_root, resolve, write_json, write_text  # noqa: E402
from repair5g515_common import G515_CLOSED_CLAIMS  # noqa: E402


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g515_decision.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g515_decision_summary.json"
DEFAULT_G514_INTERPRETATION = "outputs/reports/phase5p5_repair5g514_final_interpretation.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--g514-final-interpretation", type=Path, default=Path(DEFAULT_G514_INTERPRETATION))
    return parser.parse_args(argv)


def maybe_json(path: str) -> dict:
    target = resolve(path, repo_root())
    return read_json(target) if target.exists() else {}


def write_g514_interpretation(path: Path) -> None:
    root = repo_root()
    eval_summary = maybe_json("outputs/reports/phase5p5_repair5g514_candidate_ranker_v4_eval_summary.json")
    decision_summary = maybe_json("outputs/reports/phase5p5_repair5g514_decision_summary.json")
    primary = eval_summary.get("primary_policy", {})
    v3 = next(
        (row for row in eval_summary.get("policy_summaries", []) if row.get("policy") == "v3_g512_ranker_reproduced"),
        {},
    )
    write_text(
        resolve(path, root),
        "# Phase5.5 Repair5G.5.14 Final Interpretation\n\n"
        "- conclusion: `G5.14 recovered rich runtime-safe trace features, but failed strict promotion because harmful rate exceeded 0.05 and risk-adjusted utility did not improve over the reproduced G5.12/G5.13 ranker.`\n"
        f"- g514_decision: `{decision_summary.get('decision', '')}`\n"
        f"- v4_mean_delta_vs_static: `{primary.get('mean_delta_vs_static', '')}`\n"
        f"- v4_harmful_vs_static_rate: `{primary.get('harmful_vs_static_rate', '')}`\n"
        f"- v4_risk_adjusted_utility_lambda_0p10: `{primary.get('risk_adjusted_utility_lambda_0p1', primary.get('risk_adjusted_utility_lambda_0p10', ''))}`\n"
        f"- reproduced_g512_mean_delta_vs_static: `{v3.get('mean_delta_vs_static', '')}`\n"
        f"- reproduced_g512_harmful_vs_static_rate: `{v3.get('harmful_vs_static_rate', '')}`\n"
        f"- reproduced_g512_risk_adjusted_utility_lambda_0p10: `{v3.get('risk_adjusted_utility_lambda_0p1', v3.get('risk_adjusted_utility_lambda_0p10', ''))}`\n"
        "- interpretation: `The recovered rich features are useful evidence, but G5.14 joined them as context-only columns. They can shift gate/fallback behavior but cannot reliably reorder candidates in a linear scorer. G5.15 therefore tests rich-by-candidate interactions and pairwise ranking.`\n"
        "- runtime_claim_allowed: `false`\n",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    write_g514_interpretation(args.g514_final_interpretation)
    verify = maybe_json("outputs/reports/phase5p5_repair5g515_g514_artifact_verification_summary.json")
    blocker = maybe_json("outputs/reports/phase5p5_repair5g515_v4_context_only_feature_blocker_summary.json")
    matrix = maybe_json("outputs/reports/phase5p5_repair5g515_candidate_feature_matrix_v5_summary.json")
    eval_summary = maybe_json("outputs/reports/phase5p5_repair5g515_calibrated_interaction_rankers_summary.json")
    autopsy = maybe_json("outputs/reports/phase5p5_repair5g515_false_positive_autopsy_summary.json")
    safety = maybe_json("outputs/reports/phase5p5_repair5g515_static_abstention_safety_update_summary.json")
    if verify.get("decision") == "missing_g514_artifacts_stop":
        decision = "missing_g514_artifacts_stop"
    elif matrix.get("decision") != "v5_interaction_feature_matrix_passed_continue_ranker":
        decision = matrix.get("decision", "v5_interaction_feature_matrix_gate_failed")
    else:
        decision = eval_summary.get("decision", "data_insufficient_continue_local_probe_or_lattice")
        if decision == "interaction_ranker_passed_continue_safety_boundary_expansion" and not safety.get("safety_package_complete", False):
            decision = "static_abstention_safety_package_incomplete_continue_local"
    summary = {
        "schema_version": "phase5p5_repair5g515_decision_summary_v1",
        "decision": decision,
        "g514_artifacts_decision": verify.get("decision", ""),
        "v4_blocker_decision": blocker.get("decision", ""),
        "v5_matrix_decision": matrix.get("decision", ""),
        "interaction_eval_decision": eval_summary.get("decision", ""),
        "primary_policy_name": eval_summary.get("primary_policy_name", ""),
        "primary_policy": eval_summary.get("primary_policy", {}),
        "false_positive_autopsy_decision": autopsy.get("decision", ""),
        "safety_update_decision": safety.get("decision", ""),
        "safety_package_complete": safety.get("safety_package_complete", False),
        "runtime_claim_allowed": False,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "learned_runtime_policy_validated": False,
        "server_required": decision == "server_required_for_expanded_lattice_or_more_contexts",
        "next_step": "continue local calibration/feature design before any runtime or server claim",
        **G515_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.15 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- g514_artifacts_decision: `{summary['g514_artifacts_decision']}`\n"
        f"- v4_blocker_decision: `{summary['v4_blocker_decision']}`\n"
        f"- v5_matrix_decision: `{summary['v5_matrix_decision']}`\n"
        f"- interaction_eval_decision: `{summary['interaction_eval_decision']}`\n"
        f"- primary_policy_name: `{summary['primary_policy_name']}`\n"
        f"- primary_policy: `{summary['primary_policy']}`\n"
        f"- false_positive_autopsy_decision: `{summary['false_positive_autopsy_decision']}`\n"
        f"- safety_update_decision: `{summary['safety_update_decision']}`\n"
        f"- safety_package_complete: `{summary['safety_package_complete']}`\n"
        "- phase5p5_allowed: `false`\n"
        "- phase6_allowed: `false`\n"
        "- aaai_ready: `false`\n"
        "- runtime_claim_allowed: `false`\n"
        "- learned_runtime_policy_validated: `false`\n\n"
        "G5.15 executed the local table-only rich-by-candidate interaction round. It does not modify solver semantics, does not touch C++ or reserved IDs, and does not export a runtime policy. "
        "Runtime, Phase5.5, Phase6, and AAAI claims remain closed until stricter safety and closed-loop evidence exist.\n",
    )
    print(json.dumps({"decision": decision, "primary_policy_name": summary["primary_policy_name"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Write the final G5.20 decision from corrected target and policy diagnostics."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g520_common import (  # noqa: E402
    G520_AUTOPSY_SUMMARY,
    G520_CLOSED_CLAIMS,
    G520_DECISION_REPORT,
    G520_DECISION_SUMMARY,
    G520_FEATURE_MATRIX_SUMMARY,
    G520_POLICY_SUMMARY,
    G520_SECOND_WAVE_SUMMARY,
    G520_TARGETS_SUMMARY,
    G520_TARGET_SEMANTICS_AUDIT_SUMMARY,
    G520_VERIFY_SUMMARY,
    csv_number,
    finite_number,
    read_json_file,
    resolve,
    write_json_file,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path(G520_DECISION_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G520_DECISION_SUMMARY))
    return parser.parse_args(argv)


def maybe_json(path: str) -> dict:
    actual = resolve(path)
    return read_json_file(actual) if actual.exists() else {}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    verify = maybe_json(G520_VERIFY_SUMMARY)
    semantics = maybe_json(G520_TARGET_SEMANTICS_AUDIT_SUMMARY)
    targets = maybe_json(G520_TARGETS_SUMMARY)
    features = maybe_json(G520_FEATURE_MATRIX_SUMMARY)
    policy = maybe_json(G520_POLICY_SUMMARY)
    autopsy = maybe_json(G520_AUTOPSY_SUMMARY)
    second_wave = maybe_json(G520_SECOND_WAVE_SUMMARY)

    if verify.get("decision") not in {"g519_artifacts_verified_continue_g520", ""}:
        decision = "metric_semantics_blocker_stop"
    elif semantics.get("decision") == "target_semantics_blocker_stop":
        decision = "metric_semantics_blocker_stop"
    elif bool(policy.get("policy_passed")):
        decision = "opportunity_gated_ranker_passed_continue_closed_loop_preflight"
    elif second_wave.get("plan_created"):
        decision = "second_wave_lattice_planned_continue_local_probe"
    elif semantics.get("decision") == "static_harm_semantics_bug_fixed_continue_corrected_targets":
        decision = "target_semantics_corrected_ranker_signal_changed_continue_validation"
    else:
        decision = "candidate_space_positive_policy_still_not_ready_continue_specialist_design"

    best = policy.get("best_policy_summary", {})
    summary = {
        "schema_version": "phase5p5_repair5g520_decision_summary_v1",
        "decision": decision,
        "g519_artifact_verification_decision": verify.get("decision", ""),
        "target_semantics_decision": semantics.get("decision", ""),
        "corrected_targets_decision": targets.get("decision", ""),
        "feature_matrix_decision": features.get("decision", ""),
        "policy_eval_decision": policy.get("decision", ""),
        "policy_passed": bool(policy.get("policy_passed")),
        "policy_hard_gates": policy.get("hard_gates", {}),
        "autopsy_decision": autopsy.get("decision", ""),
        "second_wave_decision": second_wave.get("decision", ""),
        "second_wave_plan_created": bool(second_wave.get("plan_created")),
        "solver_run": False,
        "best_policy": policy.get("best_policy", ""),
        "best_policy_summary": best,
        "static_harm_semantics_repaired": semantics.get("decision") == "static_harm_semantics_bug_fixed_continue_corrected_targets",
        "g518_candidate_space_positive_remains_valid": True,
        "g519_ranker_failure_interpretation": "ranker ignored new candidates; G5.20 treats this as candidate-policy/target-semantics/safety-calibration failure, not direction failure",
        "local_offline_diagnostic_only": True,
        **G520_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, summary)
    claim_lines = "\n".join(f"- {key}: `{value}`" for key, value in G520_CLOSED_CLAIMS.items())
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.20 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- best_policy: `{summary['best_policy']}`\n"
        f"- best_mean_solution_quality_delta_vs_static: `{csv_number(finite_number(best.get('mean_solution_quality_delta_vs_static'), math.inf))}`\n"
        f"- best_solution_quality_harmful_rate: `{csv_number(finite_number(best.get('solution_quality_harmful_rate'), math.inf))}`\n"
        f"- best_no_solution_rate: `{csv_number(finite_number(best.get('no_solution_rate'), math.inf))}`\n"
        f"- best_total_harmful_rate: `{csv_number(finite_number(best.get('total_harmful_rate'), math.inf))}`\n"
        f"- best_new_candidate_selection_count: `{best.get('new_candidate_selection_count', '')}`\n"
        f"- best_new_candidate_helpful_selection_count: `{best.get('new_candidate_helpful_selection_count', '')}`\n"
        f"- best_new_candidate_harmful_selection_count: `{best.get('new_candidate_harmful_selection_count', '')}`\n"
        f"- best_new_candidate_opportunity_capture_rate: `{csv_number(finite_number(best.get('new_candidate_opportunity_capture_rate'), math.inf))}`\n"
        f"- static_harm_semantics_repaired: `{summary['static_harm_semantics_repaired']}`\n"
        f"- second_wave_plan_created: `{summary['second_wave_plan_created']}`\n"
        f"- solver_run: `false`\n\n"
        "## Interpretation\n\n"
        "G5.18 candidate-space positive evidence remains valid. G5.19 did not fail the project direction; it showed that the current learned candidate policy ignored the new candidates. "
        "G5.20 separates solution-quality harm from no-solution/nonfinite risk, evaluates opportunity-gated policies with corrected labels, and records whether a local second-wave lattice probe is justified.\n\n"
        "## Claim Boundaries\n\n"
        f"{claim_lines}\n",
    )
    print(json.dumps({"decision": decision, "best_policy": summary["best_policy"], "second_wave_plan_created": summary["second_wave_plan_created"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

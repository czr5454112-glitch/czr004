"""Write the final G5.22 decision."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g522_common import (  # noqa: E402
    G522_ADAPTER_SUMMARY,
    G522_AUTOPSY_SUMMARY,
    G522_CLOSED_CLAIMS,
    G522_CONTEXT_PANEL_SUMMARY,
    G522_DECISION_REPORT,
    G522_DECISION_SUMMARY,
    G522_DESIGN_SUMMARY,
    G522_ORACLE_SUMMARY,
    G522_PROBE_INTEGRITY_SUMMARY,
    G522_SIGNAL_SUMMARY,
    G522_SURROGATE_SUMMARY,
    G522_TEACHER_SUMMARY,
    G522_VERIFY_SUMMARY,
    boolish,
    csv_number,
    finite_number,
    read_json_file,
    repo_root,
    resolve,
    write_json_file,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-json", type=Path, default=Path(G522_DECISION_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G522_DECISION_REPORT))
    return parser.parse_args(argv)


def load(path: str) -> dict[str, Any]:
    actual = resolve(path, repo_root())
    return read_json_file(actual) if actual.exists() else {}


def decide(parts: dict[str, dict[str, Any]]) -> str:
    if parts["verify"].get("decision") != "g521_artifacts_verified_continue_g522":
        return "g522_adapter_or_target_semantics_blocker_stop"
    if parts["adapter"].get("decision") != "response_design_adapter_passed_continue_probe":
        return "g522_adapter_or_target_semantics_blocker_stop"
    if parts["probe"].get("decision") != "response_surface_probe_integrity_passed_continue_oracle":
        return "g522_adapter_or_target_semantics_blocker_stop"
    candidate_gain = boolish(parts["oracle"].get("candidate_space_continuation_gate_passed"))
    teacher_ready = (
        boolish(parts["teacher"].get("response_surface_rows_gt_g521_targeted"))
        and int(finite_number(parts["teacher"].get("forbidden_feature_count"), 99)) == 0
        and (
            int(finite_number(parts["teacher"].get("safe_positive_candidate_rows"), 0)) > 0
            or int(finite_number(parts["teacher"].get("candidate_induced_failure_rows"), 0)) > 0
        )
    )
    surrogate_promising = boolish(parts["surrogate"].get("promising_surrogate"))
    signal_smooth = boolish(parts["signal"].get("response_surface_signal_smooth_enough_to_learn"))
    if candidate_gain and teacher_ready:
        return "g522_response_surface_candidate_space_improved_continue_neural_dataset"
    if surrogate_promising:
        return "g522_surrogate_model_promising_continue_goal_aware_update_learning"
    if teacher_ready and signal_smooth:
        return "g522_neural_teacher_dataset_ready_continue_offline_model_training"
    if teacher_ready:
        return "g522_response_surface_no_incremental_gain_continue_update_design_autopsy"
    return "g522_no_learnable_signal_return_to_feature_or_trace_design"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    parts = {
        "verify": load(G522_VERIFY_SUMMARY),
        "autopsy": load(G522_AUTOPSY_SUMMARY),
        "context": load(G522_CONTEXT_PANEL_SUMMARY),
        "design": load(G522_DESIGN_SUMMARY),
        "adapter": load(G522_ADAPTER_SUMMARY),
        "probe": load(G522_PROBE_INTEGRITY_SUMMARY),
        "oracle": load(G522_ORACLE_SUMMARY),
        "teacher": load(G522_TEACHER_SUMMARY),
        "surrogate": load(G522_SURROGATE_SUMMARY),
        "signal": load(G522_SIGNAL_SUMMARY),
    }
    decision = decide(parts)
    forbidden_feature_count = int(finite_number(parts["teacher"].get("forbidden_feature_count"), 99))
    positive_evidence = (
        boolish(parts["oracle"].get("candidate_space_continuation_gate_passed"))
        or boolish(parts["teacher"].get("response_surface_rows_gt_g521_targeted"))
    )
    gates = {
        "forbidden_feature_count_eq_0": forbidden_feature_count == 0,
        "target_semantics_valid": parts["verify"].get("decision") == "g521_artifacts_verified_continue_g522" and parts["adapter"].get("decision") == "response_design_adapter_passed_continue_probe",
        "response_surface_dataset_rows_gt_g521": boolish(parts["teacher"].get("response_surface_rows_gt_g521_targeted")),
        "candidate_space_gain_or_richer_teacher_labels": positive_evidence,
        "controls_do_not_explain_signal": not boolish(parts["signal"].get("source_blind_control_matches_model")),
        "claims_remain_closed": all(not boolish(parts[name].get(key)) for name in parts for key in G522_CLOSED_CLAIMS),
    }
    summary = {
        "schema_version": "phase5p5_repair5g522_decision_summary_v1",
        "decision": decision,
        "component_decisions": {name: part.get("decision", "") for name, part in parts.items()},
        "candidate_space_metrics": {
            "incremental_oracle_gap_vs_old14_plus_g518": parts["oracle"].get("incremental_oracle_gap_vs_old14_plus_g518", ""),
            "safe_g522_win_contexts": parts["oracle"].get("safe_g522_win_contexts", ""),
            "candidate_induced_no_solution_count": parts["oracle"].get("candidate_induced_no_solution_count", ""),
            "static_failure_candidate_recovers_count": parts["oracle"].get("static_failure_candidate_recovers_count", ""),
        },
        "teacher_metrics": {
            "context_rows": parts["teacher"].get("context_rows", ""),
            "candidate_rows": parts["teacher"].get("candidate_rows", ""),
            "pairwise_rows": parts["teacher"].get("pairwise_rows", ""),
            "edge_update_rows_or_blocker": parts["teacher"].get("edge_update_rows_or_blocker", ""),
            "safe_positive_candidate_rows": parts["teacher"].get("safe_positive_candidate_rows", ""),
            "candidate_induced_failure_rows": parts["teacher"].get("candidate_induced_failure_rows", ""),
            "static_recovery_rows": parts["teacher"].get("static_recovery_rows", ""),
        },
        "surrogate_metrics": {
            "best_model": parts["surrogate"].get("best_model", ""),
            "promising_surrogate": parts["surrogate"].get("promising_surrogate", False),
            "best_model_summary": parts["surrogate"].get("best_model_summary", {}),
        },
        "positive_decision_gates": gates,
        "claims_closed": G522_CLOSED_CLAIMS,
        **G522_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.22 Final Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- incremental_oracle_gap_vs_old14_plus_g518: `{csv_number(finite_number(parts['oracle'].get('incremental_oracle_gap_vs_old14_plus_g518'), math.inf))}`\n"
        f"- safe_g522_win_contexts: `{parts['oracle'].get('safe_g522_win_contexts', '')}`\n"
        f"- candidate_induced_no_solution_count: `{parts['oracle'].get('candidate_induced_no_solution_count', '')}`\n"
        f"- static_failure_candidate_recovers_count: `{parts['oracle'].get('static_failure_candidate_recovers_count', '')}`\n"
        f"- teacher_candidate_rows: `{parts['teacher'].get('candidate_rows', '')}`\n"
        f"- teacher_pairwise_rows: `{parts['teacher'].get('pairwise_rows', '')}`\n"
        f"- safe_positive_candidate_rows: `{parts['teacher'].get('safe_positive_candidate_rows', '')}`\n"
        f"- best_surrogate_model: `{parts['surrogate'].get('best_model', '')}`\n"
        f"- promising_surrogate: `{parts['surrogate'].get('promising_surrogate', False)}`\n"
        f"- positive_decision_gates: `{gates}`\n\n"
        "Closed claims remain:\n\n"
        "```text\n"
        "phase5p5_allowed=false\n"
        "phase6_allowed=false\n"
        "runtime_claim_allowed=false\n"
        "learned_runtime_policy_validated=false\n"
        "aaai_ready=false\n"
        "```\n",
    )
    print(json.dumps({"decision": decision, "teacher_candidate_rows": parts["teacher"].get("candidate_rows", "")}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

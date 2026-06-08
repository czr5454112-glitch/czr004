"""Write the final G5.21 decision."""

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

from repair5g521_common import (  # noqa: E402
    G521_ADAPTER_SUMMARY,
    G521_AVOIDABLE_SEMANTICS_SUMMARY,
    G521_CLOSED_CLAIMS,
    G521_DECISION_REPORT,
    G521_DECISION_SUMMARY,
    G521_FEATURES_SUMMARY,
    G521_FULL_ORACLE_SUMMARY,
    G521_GAP_SUMMARY,
    G521_POOL_SUMMARY,
    G521_SELECTOR_SUMMARY,
    G521_TARGETED_ORACLE_SUMMARY,
    G521_TARGETS_SUMMARY,
    G521_VERIFY_SUMMARY,
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
    parser.add_argument("--summary-json", type=Path, default=Path(G521_DECISION_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G521_DECISION_REPORT))
    return parser.parse_args(argv)


def load(path: str) -> dict[str, Any]:
    actual = resolve(path, repo_root())
    return read_json_file(actual) if actual.exists() else {}


def decide(
    verify: dict[str, Any],
    semantics: dict[str, Any],
    pool: dict[str, Any],
    adapter: dict[str, Any],
    targeted: dict[str, Any],
    full: dict[str, Any],
    targets: dict[str, Any],
    selector: dict[str, Any],
) -> str:
    if verify.get("decision") != "g520_artifacts_verified_continue_g521":
        return "g521_target_semantics_or_adapter_blocker_stop"
    if semantics.get("decision") != "avoidable_failure_semantics_passed_continue_second_wave_pool":
        return "g521_target_semantics_or_adapter_blocker_stop"
    if adapter.get("decision") != "adapter_grammar_passed_continue_targeted_probe":
        return "g521_target_semantics_or_adapter_blocker_stop"
    if not boolish(targeted.get("targeted_gate_passed")):
        return "g521_second_wave_no_candidate_space_gain_continue_lattice_autopsy"
    full_improved = (
        boolish(full.get("oracle_analyzed"))
        and (
            finite_number(full.get("g51822_vs_g52130_oracle_gap"), math.inf) <= -0.001
            or int(finite_number(full.get("second_wave_safe_win_contexts"), 0)) >= 2
        )
    )
    targeted_improved = (
        finite_number(targeted.get("second_wave_oracle_gap_vs_g518_retained8"), math.inf) <= -0.001
        or int(finite_number(targeted.get("safe_second_wave_win_contexts"), 0)) >= 2
    )
    candidate_space_improved = full_improved or (targeted_improved and not boolish(targets.get("full_primary_compatible")))
    if not candidate_space_improved:
        return "g521_second_wave_no_candidate_space_gain_continue_lattice_autopsy"
    if boolish(selector.get("policy_promising")):
        return "g521_second_wave_policy_captures_new_candidates_continue_safety"
    if int(finite_number(selector.get("best_policy_summary", {}).get("new_candidate_selection_count"), 0)) > 0:
        return "g521_second_wave_candidate_space_improved_continue_selector"
    return "g521_candidate_space_improved_selector_still_blocked_continue_policy_design"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    verify = load(G521_VERIFY_SUMMARY)
    semantics = load(G521_AVOIDABLE_SEMANTICS_SUMMARY)
    pool = load(G521_POOL_SUMMARY)
    adapter = load(G521_ADAPTER_SUMMARY)
    targeted = load(G521_TARGETED_ORACLE_SUMMARY)
    full = load(G521_FULL_ORACLE_SUMMARY)
    targets = load(G521_TARGETS_SUMMARY)
    features = load(G521_FEATURES_SUMMARY)
    selector = load(G521_SELECTOR_SUMMARY)
    gap = load(G521_GAP_SUMMARY)
    decision = decide(verify, semantics, pool, adapter, targeted, full, targets, selector)
    summary = {
        "schema_version": "phase5p5_repair5g521_decision_summary_v1",
        "decision": decision,
        "g520_artifact_verification_decision": verify.get("decision", ""),
        "avoidable_failure_semantics_decision": semantics.get("decision", ""),
        "candidate_pool_decision": pool.get("decision", ""),
        "adapter_decision": adapter.get("decision", ""),
        "targeted_oracle_decision": targeted.get("decision", ""),
        "targeted_gate_passed": targeted.get("targeted_gate_passed", False),
        "full_primary_oracle_decision": full.get("decision", ""),
        "full_primary_compatible": targets.get("full_primary_compatible", False),
        "targets_v10_decision": targets.get("decision", ""),
        "split_features_decision": features.get("decision", ""),
        "selector_decision": selector.get("decision", ""),
        "selector_best_policy": selector.get("best_policy", ""),
        "selector_policy_promising": selector.get("policy_promising", False),
        "gap_autopsy_decision": gap.get("decision", ""),
        "candidate_space_metrics": {
            "targeted_second_wave_oracle_gap_vs_g518_retained8": targeted.get("second_wave_oracle_gap_vs_g518_retained8", ""),
            "targeted_safe_second_wave_win_contexts": targeted.get("safe_second_wave_win_contexts", ""),
            "full_g51822_vs_g52130_oracle_gap": full.get("g51822_vs_g52130_oracle_gap", ""),
            "full_second_wave_safe_win_contexts": full.get("second_wave_safe_win_contexts", ""),
        },
        "policy_metrics": selector.get("best_policy_summary", {}),
        "claims_closed": G521_CLOSED_CLAIMS,
        **G521_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, summary)
    best = selector.get("best_policy_summary", {})
    write_text_file(
        args.report,
        "# Repair5G.5.21 Final Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- targeted_gate_passed: `{targeted.get('targeted_gate_passed', False)}`\n"
        f"- targeted_second_wave_oracle_gap_vs_g518_retained8: `{csv_number(finite_number(targeted.get('second_wave_oracle_gap_vs_g518_retained8'), math.inf))}`\n"
        f"- targeted_safe_second_wave_win_contexts: `{targeted.get('safe_second_wave_win_contexts', '')}`\n"
        f"- full_primary_compatible: `{targets.get('full_primary_compatible', False)}`\n"
        f"- full_g51822_vs_g52130_oracle_gap: `{csv_number(finite_number(full.get('g51822_vs_g52130_oracle_gap'), math.inf))}`\n"
        f"- selector_best_policy: `{selector.get('best_policy', '')}`\n"
        f"- selector_policy_promising: `{selector.get('policy_promising', False)}`\n"
        f"- best_new_candidate_selection_count: `{best.get('new_candidate_selection_count', '')}`\n"
        f"- best_new_candidate_helpful_selection_count: `{best.get('new_candidate_helpful_selection_count', '')}`\n"
        f"- best_new_candidate_induced_no_solution_count: `{best.get('new_candidate_induced_no_solution_count', '')}`\n\n"
        "Closed claims remain:\n\n"
        "```text\n"
        "phase5p5_allowed=false\n"
        "phase6_allowed=false\n"
        "runtime_claim_allowed=false\n"
        "learned_runtime_policy_validated=false\n"
        "aaai_ready=false\n"
        "```\n",
    )
    print(json.dumps({"decision": decision, "selector_best_policy": selector.get("best_policy", "")}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

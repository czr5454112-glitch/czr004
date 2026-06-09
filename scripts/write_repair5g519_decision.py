"""Write final G5.19 offline ranker decision."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g519_common import (  # noqa: E402
    G519_AUTOPSY_SUMMARY,
    G519_CANDIDATE_SPACE_SUMMARY,
    G519_CLOSED_CLAIMS,
    G519_DECISION_REPORT,
    G519_DECISION_SUMMARY,
    G519_EVAL_SUMMARY,
    G519_FEATURE_MATRIX_SUMMARY,
    G519_TARGETS_SUMMARY,
    G519_VERIFY_SUMMARY,
    csv_number,
    finite_number,
    read_json_file,
    resolve,
    write_json_file,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path(G519_DECISION_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G519_DECISION_SUMMARY))
    return parser.parse_args(argv)


def maybe_json(path: str) -> dict:
    actual = resolve(path)
    return read_json_file(actual) if actual.exists() else {}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    verify = maybe_json(G519_VERIFY_SUMMARY)
    targets = maybe_json(G519_TARGETS_SUMMARY)
    candidate_space = maybe_json(G519_CANDIDATE_SPACE_SUMMARY)
    features = maybe_json(G519_FEATURE_MATRIX_SUMMARY)
    eval_summary = maybe_json(G519_EVAL_SUMMARY)
    autopsy = maybe_json(G519_AUTOPSY_SUMMARY)

    if verify.get("decision") == "missing_g518_artifacts_stop":
        decision = "missing_g518_artifacts_stop"
    elif targets.get("decision") == "candidate_targets_failed":
        decision = "candidate_targets_failed"
    elif features.get("decision") == "feature_matrix_v8_failed":
        decision = "feature_matrix_v8_failed"
    else:
        decision = str(eval_summary.get("decision", "ranker_suite_failed_continue_feature_design"))

    best = eval_summary.get("best_policy_summary", {})
    hard_gates = eval_summary.get("hard_gates", {})
    summary = {
        "schema_version": "phase5p5_repair5g519_decision_summary_v1",
        "decision": decision,
        "g518_candidate_space_survived_target_reconstruction": targets.get("decision") == "candidate_targets_passed_continue_feature_matrix_v8"
        and finite_number(targets.get("new_candidate_win_count"), 0) > 0,
        "target_reconstruction_decision": targets.get("decision", ""),
        "feature_matrix_decision": features.get("decision", ""),
        "ranker_suite_decision": eval_summary.get("decision", ""),
        "autopsy_decision": autopsy.get("decision", ""),
        "best_policy": eval_summary.get("best_policy", ""),
        "best_policy_summary": best,
        "hard_gates": hard_gates,
        "best_new_single_by_mean_delta": targets.get("best_new_single_by_mean_delta", ""),
        "best_new_single_by_oracle_win_count": targets.get("best_new_single_by_oracle_win_count", ""),
        "best_new_single_by_risk_adjusted_utility": targets.get("best_new_single_by_risk_adjusted_utility", ""),
        "best_new_single_by_low_harmful_rate": targets.get("best_new_single_by_low_harmful_rate", ""),
        "local_pc_sufficient": True,
        "second_wave_lattice_run": False,
        "second_wave_lattice_reason": "optional continuation not required for the G5.19 ranker decision",
        **G519_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, summary)

    claim_lines = "\n".join(
        f"- {key}: `{value}`"
        for key, value in {
            "phase5p5_allowed": False,
            "phase6_allowed": False,
            "runtime_claim_allowed": False,
            "learned_runtime_policy_validated": False,
            "aaai_ready": False,
        }.items()
    )
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.19 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- best_policy: `{summary['best_policy']}`\n"
        f"- best_mean_delta_vs_static: `{csv_number(finite_number(best.get('mean_delta_vs_static'), math.inf))}`\n"
        f"- best_mean_delta_vs_additive: `{csv_number(finite_number(best.get('mean_delta_vs_additive'), math.inf))}`\n"
        f"- best_harmful_vs_static_rate: `{csv_number(finite_number(best.get('harmful_vs_static_rate'), math.inf))}`\n"
        f"- best_new_candidate_selection_count: `{best.get('new_candidate_selection_count', '')}`\n"
        f"- local_pc_sufficient: `true`\n"
        f"- second_wave_lattice_run: `false`\n\n"
        "## Required Answers\n\n"
        "1. Did G5.18 candidate-space positive evidence survive target reconstruction?\n"
        f"   `{summary['g518_candidate_space_survived_target_reconstruction']}`. Target reconstruction produced `{targets.get('target_rows', '')}` candidate rows and `{targets.get('new_candidate_win_count', '')}` new-candidate winning budget pairs.\n\n"
        "2. Which new candidates are useful by mean, oracle wins, and risk?\n"
        f"   Mean: `{summary['best_new_single_by_mean_delta']}`. Oracle wins: `{summary['best_new_single_by_oracle_win_count']}`. Risk-adjusted: `{summary['best_new_single_by_risk_adjusted_utility']}`. Low harmful rate: `{summary['best_new_single_by_low_harmful_rate']}`.\n\n"
        "3. Can a runtime-safe offline ranker select the 22-candidate lattice safely?\n"
        f"   Current diagnostic decision: `{eval_summary.get('decision', '')}`. The best policy hard gates are `{hard_gates}`.\n\n"
        "4. Does the ranker use new candidates or fall back to old14/static?\n"
        f"   Best policy new-candidate selections: `{best.get('new_candidate_selection_count', '')}`, helpful: `{best.get('new_candidate_helpful_selection_count', '')}`, harmful: `{best.get('new_candidate_harmful_selection_count', '')}`.\n\n"
        "5. Does it beat G5.15/G5.18 reproduced baselines and train-only priors?\n"
        f"   RAU baseline gates: 0.05=`{hard_gates.get('rau_0p05_improves_over_reproduced', '')}`, 0.10=`{hard_gates.get('rau_0p10_improves_over_reproduced', '')}`; train-prior gate=`{hard_gates.get('beats_train_only_map_agent_prior_0p10', '')}`.\n\n"
        "6. What remains before runtime/Phase5.5?\n"
        "   Runtime integration, Phase5.5, Phase6, learned runtime policy validation, and AAAI claims remain closed. A future round must either improve candidate-policy safety/calibration or use the autopsy to design a sparse second-wave lattice.\n\n"
        "7. Is local PC still sufficient?\n"
        "   `true`. G5.19 used offline tables and local deterministic Python diagnostics; no solver continuation was required.\n\n"
        "## Claim Boundaries\n\n"
        f"{claim_lines}\n",
    )
    print(json.dumps({"decision": decision, "best_policy": summary["best_policy"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

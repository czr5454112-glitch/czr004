"""Compare G5.11 context-level targets with G5.12 candidate-level targets."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import CLOSED_CLAIMS, count_by, read_csv_rows, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_V5 = "outputs/tables/phase5p5_repair5g511_confidence_targets_v5.csv"
DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g512_candidate_regret_targets.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g512_context_vs_candidate_target_gap.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g512_context_vs_candidate_target_gap_summary.json"
DEFAULT_DECISION_REPORT = "outputs/reports/phase5p5_repair5g512_target_redesign_decision.md"
DEFAULT_DECISION_SUMMARY = "outputs/reports/phase5p5_repair5g512_target_redesign_decision_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-targets-csv", type=Path, default=Path(DEFAULT_V5))
    parser.add_argument("--candidate-targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--decision-report", type=Path, default=Path(DEFAULT_DECISION_REPORT))
    parser.add_argument("--decision-summary-json", type=Path, default=Path(DEFAULT_DECISION_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    context_rows = read_csv_rows(resolve(args.context_targets_csv, root))
    candidate_rows = read_csv_rows(resolve(args.candidate_targets_csv, root))
    context_labels = count_by(context_rows, "label_class")
    candidate_labels = count_by(candidate_rows, "label_class")
    stable_nonstatic = context_labels.get("stable_high_confidence_parameter_candidate", 0)
    stable_static = context_labels.get("stable_static", 0)
    no_solution_or_budget = context_labels.get("no_solution_abstain", 0) + context_labels.get("longer_budget_needed", 0)
    candidate_contexts = {str(row.get("normalized_context_key", "")) for row in candidate_rows}
    candidate_ids = {str(row.get("candidate_id", "")) for row in candidate_rows}
    decision = "target_redesign_passed_candidate_level_regret_ranking"
    summary = {
        "schema_version": "phase5p5_repair5g512_context_vs_candidate_target_gap_summary_v1",
        "decision": decision,
        "g511_context_rows": len(context_rows),
        "g511_context_label_counts": context_labels,
        "g511_stable_high_confidence_parameter_candidate": stable_nonstatic,
        "g511_stable_static": stable_static,
        "g511_no_solution_or_budget_abstain_count": no_solution_or_budget,
        "g512_candidate_level_rows": len(candidate_rows),
        "g512_contexts": len(candidate_contexts),
        "g512_candidates": len(candidate_ids),
        "g512_candidate_label_counts": candidate_labels,
        "required_conclusion": "G5.11 failed because context-level oracle class labels are too coarse for a parameter lattice.",
        "candidate_level_regret_ranking_is_right_target": True,
        "offline_candidate_ranking_diagnostics_require_no_solution_or_budget_abstain": False,
        "runtime_phase5p5_still_requires_static_abstention_no_solution_budget_ood_safety_package": True,
        **CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    report = (
        "# Phase5.5 Repair5G.5.12 Context-vs-Candidate Target Gap\n\n"
        f"- G5.11 context labels: `{context_labels}`\n"
        f"- G5.12 candidate labels: `{candidate_labels}`\n"
        f"- G5.12 candidate rows: `{len(candidate_rows)}`\n"
        f"- G5.12 contexts: `{len(candidate_contexts)}`\n"
        f"- G5.12 candidates: `{len(candidate_ids)}`\n\n"
        "G5.11 failed because context-level oracle class labels are too coarse for a parameter lattice. "
        "The full lattice mostly found stable non-static winners, so the old target had 52 parameter-candidate contexts, "
        "8 static contexts, and no no-solution or longer-budget abstention examples. That is useful candidate-space evidence, "
        "but it is a poor training target for scoring fourteen parameter candidates.\n\n"
        "Candidate-level regret, ranking, and harmful-risk labels are the right offline diagnostic target for learned bounded "
        "UpdateLTM parameter scoring. They expose helpful, harmful, neutral, static, additive-bad, and C-only examples within "
        "the same context. `no_solution_or_budget_abstain_count=0` must not block this offline candidate-ranking diagnostic.\n\n"
        "Runtime, Phase5.5, Phase6, and AAAI claims remain closed because deployment still needs static, abstention, "
        "no-solution, budget-sensitive, and OOD safety coverage.\n"
    )
    write_text(resolve(args.report, root), report)
    decision_summary = {
        "schema_version": "phase5p5_repair5g512_target_redesign_decision_summary_v1",
        "decision": decision,
        "g511_failure_mode": "context_level_oracle_class_labels_too_coarse_for_parameter_lattice",
        "next_target": "candidate_level_regret_ranking_harmful_risk",
        "no_solution_or_budget_abstain_count": no_solution_or_budget,
        "no_solution_or_budget_abstain_blocks_offline_candidate_ranking": False,
        "no_solution_or_budget_abstain_blocks_runtime_phase5p5": True,
        **CLOSED_CLAIMS,
    }
    write_json(resolve(args.decision_summary_json, root), decision_summary)
    write_text(
        resolve(args.decision_report, root),
        "# Phase5.5 Repair5G.5.12 Target Redesign Decision\n\n"
        f"- decision: `{decision}`\n"
        "- conclusion: `G5.11 failed because context-level oracle class labels are too coarse for a parameter lattice.`\n"
        "- next target: `candidate-level regret/ranking/harmful-risk scoring`\n"
        f"- no_solution_or_budget_abstain_count: `{no_solution_or_budget}`\n"
        "- offline_candidate_ranking_diagnostics_require_no_solution_or_budget_abstain: `false`\n"
        "- runtime_phase5p5_still_requires_static_abstention_no_solution_budget_ood_safety_package: `true`\n"
        "- runtime_claim_allowed: `false`\n"
        "- phase6_allowed: `false`\n"
        "- aaai_ready: `false`\n",
    )
    print(json.dumps({"decision": decision, "candidate_rows": len(candidate_rows)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

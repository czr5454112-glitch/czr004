"""Write the final G5.18 decision from autopsy, proposal, probe, and full-primary evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g518_common import (  # noqa: E402
    G518_ADAPTER_SUMMARY,
    G518_AUTOPSY_SUMMARY,
    G518_BATCHES_SUMMARY,
    G518_CLOSED_CLAIMS,
    G518_DECISION_REPORT,
    G518_DECISION_SUMMARY,
    G518_FULL_PRIMARY_INTEGRITY_SUMMARY,
    G518_FULL_PRIMARY_ORACLE_SUMMARY,
    G518_PROPOSAL_SUMMARY,
    maybe_read_json,
    write_json_file,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--autopsy-summary-json", type=Path, default=Path(G518_AUTOPSY_SUMMARY))
    parser.add_argument("--proposal-summary-json", type=Path, default=Path(G518_PROPOSAL_SUMMARY))
    parser.add_argument("--adapter-summary-json", type=Path, default=Path(G518_ADAPTER_SUMMARY))
    parser.add_argument("--batches-summary-json", type=Path, default=Path(G518_BATCHES_SUMMARY))
    parser.add_argument("--full-primary-integrity-summary-json", type=Path, default=Path(G518_FULL_PRIMARY_INTEGRITY_SUMMARY))
    parser.add_argument("--full-primary-oracle-summary-json", type=Path, default=Path(G518_FULL_PRIMARY_ORACLE_SUMMARY))
    parser.add_argument("--summary-json", type=Path, default=Path(G518_DECISION_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G518_DECISION_REPORT))
    return parser.parse_args(argv)


def choose_decision(
    autopsy: dict,
    adapter: dict,
    batches: dict,
    full_integrity: dict,
    full_oracle: dict,
) -> tuple[str, str, str]:
    if autopsy.get("decision") == "g517_artifacts_missing_or_invalid_stop":
        return "g517_artifacts_missing_or_invalid_stop", "not_run", "G5.17 prerequisite artifacts failed validation."
    if adapter.get("decision") != "adapter_grammar_passed_continue_probe_batches":
        return "g518_adapter_grammar_failed", "not_run", "G5.18 generic adapter grammar did not pass recognition/smoke validation."
    batch_decision = batches.get("decision", "")
    if batch_decision == "g518_surrogate_lattice_probe_integrity_failed":
        return "g518_surrogate_lattice_probe_integrity_failed", "not_run", "At least one G5.18 probe batch failed integrity."
    if batch_decision == "g518_exploratory_lattice_no_gain_continue_lattice_design":
        return "g518_exploratory_lattice_no_gain_continue_lattice_design", "ranker_skipped_no_candidate_space_gain", "All executable surrogate-guided batches completed but did not improve the old-14 oracle."
    if full_integrity.get("decision") == "g518_full_primary_integrity_failed":
        return "stop_for_protocol_or_semantic_bug", "not_run", "Full-primary confirmation failed integrity after a batch gate passed."
    full_decision = full_oracle.get("decision", "")
    if full_decision == "g518_full_primary_candidate_space_improved_continue_ranker":
        return "g518_full_primary_candidate_space_improved_continue_ranker", "ranker_allowed_next_round", "Full-primary candidate-space oracle improved."
    if full_decision == "g518_full_primary_candidate_space_failed_continue_update_mechanism_or_objective_design":
        return "g518_full_primary_candidate_space_failed_continue_update_mechanism_or_objective_design", "ranker_skipped_full_primary_failed", "Batch gain did not survive full-primary confirmation."
    if full_decision == "g518_full_primary_not_run_batch_gate_not_passed":
        return "g518_exploratory_lattice_no_gain_continue_lattice_design", "ranker_skipped_no_candidate_space_gain", "Full-primary was correctly skipped because no batch gate passed."
    return "stop_for_protocol_or_semantic_bug", "not_run", "G5.18 evidence chain ended in an unexpected state."


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    autopsy = maybe_read_json(args.autopsy_summary_json)
    proposal = maybe_read_json(args.proposal_summary_json)
    adapter = maybe_read_json(args.adapter_summary_json)
    batches = maybe_read_json(args.batches_summary_json)
    full_integrity = maybe_read_json(args.full_primary_integrity_summary_json)
    full_oracle = maybe_read_json(args.full_primary_oracle_summary_json)
    decision, ranker_decision, rationale = choose_decision(autopsy, adapter, batches, full_integrity, full_oracle)
    summary = {
        "schema_version": "phase5p5_repair5g518_decision_summary_v1",
        "decision": decision,
        "rationale": rationale,
        "autopsy_decision": autopsy.get("decision", ""),
        "proposal_decision": proposal.get("decision", ""),
        "adapter_decision": adapter.get("decision", ""),
        "probe_batches_decision": batches.get("decision", ""),
        "full_primary_integrity_decision": full_integrity.get("decision", ""),
        "full_primary_oracle_decision": full_oracle.get("decision", ""),
        "ranker_decision": ranker_decision,
        "next_step": "continue update mechanism/objective design" if "no_gain" in decision or "failed" in decision else "continue according to decision",
        "candidate_pool_count": proposal.get("candidate_pool_count", 0),
        "selected_new_candidate_count": proposal.get("selected_new_candidate_count", 0),
        "candidate_space_gate_passed_batches": batches.get("candidate_space_gate_passed_batches", []),
        "full_primary_required": batches.get("full_primary_required", False),
        **G518_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, summary)
    batch_lines = "\n".join(
        f"- Batch `{row.get('batch')}`: `{row.get('decision')}`, wins `{row.get('new_candidate_win_count')}`, mean gap `{row.get('mean_new_oracle_gap_vs_old_oracle')}`"
        for row in batches.get("batches", [])
    )
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.18 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- rationale: {rationale}\n"
        f"- autopsy_decision: `{autopsy.get('decision', '')}`\n"
        f"- proposal_decision: `{proposal.get('decision', '')}`\n"
        f"- adapter_decision: `{adapter.get('decision', '')}`\n"
        f"- probe_batches_decision: `{batches.get('decision', '')}`\n"
        f"- full_primary_integrity_decision: `{full_integrity.get('decision', '')}`\n"
        f"- full_primary_oracle_decision: `{full_oracle.get('decision', '')}`\n"
        f"- ranker_decision: `{ranker_decision}`\n"
        f"- phase5p5_allowed: `false`\n"
        f"- phase6_allowed: `false`\n"
        f"- runtime_claim_allowed: `false`\n"
        f"- learned_runtime_policy_validated: `false`\n"
        f"- aaai_ready: `false`\n\n"
        "## Batch Evidence\n\n"
        f"{batch_lines}\n\n"
        "G5.18 does not train or promote rankers unless executable candidate-space evidence first improves and survives full-primary confirmation.\n",
    )
    print(json.dumps({"decision": decision, "ranker_decision": ranker_decision}))
    return 0 if decision not in {"g517_artifacts_missing_or_invalid_stop", "g518_adapter_grammar_failed", "g518_surrogate_lattice_probe_integrity_failed", "stop_for_protocol_or_semantic_bug"} else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

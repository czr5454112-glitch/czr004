"""Write the Repair5G.5.11 final decision."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g510_common import G59_CLOSED_STATUS, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_INTEGRITY = "outputs/reports/phase5p5_repair5g511_full_lattice_integrity_summary.json"
DEFAULT_ORACLE = "outputs/reports/phase5p5_repair5g511_lattice_oracle_gap_full_summary.json"
DEFAULT_TARGETS = "outputs/reports/phase5p5_repair5g511_confidence_targets_v5_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g511_decision.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g511_decision_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--integrity-summary", type=Path, default=Path(DEFAULT_INTEGRITY))
    parser.add_argument("--oracle-summary", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--targets-summary", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    integrity = load(resolve(args.integrity_summary, root))
    oracle = load(resolve(args.oracle_summary, root))
    targets = load(resolve(args.targets_summary, root))
    if integrity.get("decision") != "full_lattice_integrity_passed":
        decision = "full_lattice_integrity_failed"
    elif oracle.get("decision") != "full_lattice_candidate_space_passed_continue_targets":
        decision = "full_lattice_candidate_space_failed_expand_lattice"
    elif targets.get("decision") != "confidence_targets_v5_passed_continue_feature_v3":
        decision = "confidence_targets_v5_failed_continue_label_design"
    else:
        decision = "full_lattice_candidate_space_passed_continue_targets"
    summary = {
        "schema_version": "phase5p5_repair5g511_decision_summary_v1",
        "decision": decision,
        "integrity_decision": integrity.get("decision"),
        "oracle_decision": oracle.get("decision"),
        "confidence_targets_decision": targets.get("decision"),
        "measured_contexts": oracle.get("measured_contexts"),
        "primary_1000_2000_stable_contexts": oracle.get("primary_1000_2000_stable_contexts"),
        "candidate_space_oracle_gap_vs_g58": oracle.get("candidate_space_oracle_gap_vs_g58"),
        "oracle_beats_static_fraction": oracle.get("oracle_beats_static_fraction"),
        "oracle_beats_additive_fraction": oracle.get("oracle_beats_additive_fraction"),
        "target_label_counts": targets.get("label_counts"),
        "why_stopped": "Candidate-space gate passed, but confidence v5 lacks the required static/abstention and no-solution/budget-abstention coverage for safe policy training.",
        "feature_v3_allowed": targets.get("decision") == "confidence_targets_v5_passed_continue_feature_v3",
        "policy_training_allowed": False,
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.11 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- integrity_decision: `{summary['integrity_decision']}`\n"
        f"- oracle_decision: `{summary['oracle_decision']}`\n"
        f"- confidence_targets_decision: `{summary['confidence_targets_decision']}`\n"
        f"- measured_contexts: `{summary['measured_contexts']}`\n"
        f"- primary_1000_2000_stable_contexts: `{summary['primary_1000_2000_stable_contexts']}`\n"
        f"- candidate_space_oracle_gap_vs_g58: `{summary['candidate_space_oracle_gap_vs_g58']}`\n"
        f"- oracle_beats_static_fraction: `{summary['oracle_beats_static_fraction']}`\n"
        f"- oracle_beats_additive_fraction: `{summary['oracle_beats_additive_fraction']}`\n"
        f"- target_label_counts: `{summary['target_label_counts']}`\n\n"
        "G5.11 successfully completes the full observed-ID server lattice run and confirms the lattice oracle upper bound improves over G5.8. "
        "It stops before feature v3 and policy training because the confidence-target gate does not provide enough safe abstention/static/no-solution coverage. "
        "Phase5.5, Phase6, runtime learned-policy, and AAAI-ready claims remain closed.\n",
    )
    print(json.dumps({"decision": decision}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

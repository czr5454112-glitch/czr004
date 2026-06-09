"""Write the final Repair5G.5.17 decision report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import read_json  # noqa: E402
from repair5g517_common import (  # noqa: E402
    G517_ADAPTER_SUMMARY,
    G517_CLOSED_CLAIMS,
    G517_DECISION_REPORT,
    G517_DECISION_SUMMARY,
    G517_FULL_INTEGRITY_SUMMARY,
    G517_FULL_ORACLE_SUMMARY,
    G517_ORACLE_SUMMARY,
    G517_SAFETY_SUMMARY,
    G517_SMOKE_SUMMARY,
    G517_TARGETED_INTEGRITY_SUMMARY,
    repo_root,
    resolve,
    write_json,
    write_text,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-json", type=Path, default=Path(G517_DECISION_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G517_DECISION_REPORT))
    return parser.parse_args(argv)


def maybe_json(path: str) -> dict:
    target = resolve(path, repo_root())
    return read_json(target) if target.exists() else {}


def choose_decision(summaries: dict[str, dict]) -> str:
    adapter = summaries["adapter"].get("decision", "")
    smoke = summaries["smoke"].get("decision", "")
    targeted_integrity = summaries["targeted_integrity"].get("decision", "")
    targeted_oracle = summaries["targeted_oracle"].get("decision", "")
    full_integrity = summaries["full_integrity"].get("decision", "")
    full_oracle = summaries["full_oracle"].get("decision", "")
    ranker = summaries["ranker"].get("decision", "")
    if adapter != "adapter_recognition_passed_continue_local_probe":
        return "adapter_recognition_failed_no_solver_run"
    if smoke != "adapter_smoke_passed_continue_targeted_probe":
        return "adapter_smoke_failed_no_targeted_probe"
    if targeted_integrity != "targeted_probe_integrity_passed_continue_oracle":
        return "targeted_probe_integrity_failed"
    if targeted_oracle == "targeted_repair_lattice_no_oracle_gain_continue_lattice_design":
        return targeted_oracle
    if targeted_oracle == "targeted_repair_lattice_oracle_improved_continue_full_primary":
        if full_integrity == "full_primary_not_run_targeted_oracle_gate_not_passed" or not full_oracle:
            return "targeted_repair_lattice_oracle_improved_continue_full_primary"
        if full_oracle.get("decision") == "full_primary_24cand_oracle_failed_continue_lattice_design":
            return "full_primary_24cand_oracle_failed_continue_lattice_design"
        if full_oracle.get("decision") == "full_primary_24cand_oracle_improved_continue_ranker":
            if ranker == "targeted_repair_v7_offline_passed_continue_safety_package":
                return ranker
            if ranker:
                return "targeted_repair_v7_ranker_failed_continue_feature_design"
            return "full_primary_24cand_oracle_improved_continue_ranker"
    return targeted_oracle or "stop_for_semantic_or_protocol_bug"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    summaries = {
        "adapter": maybe_json(G517_ADAPTER_SUMMARY),
        "smoke": maybe_json(G517_SMOKE_SUMMARY),
        "targeted_integrity": maybe_json(G517_TARGETED_INTEGRITY_SUMMARY),
        "targeted_oracle": maybe_json(G517_ORACLE_SUMMARY),
        "full_integrity": maybe_json(G517_FULL_INTEGRITY_SUMMARY),
        "full_oracle": maybe_json(G517_FULL_ORACLE_SUMMARY),
        "ranker": maybe_json("outputs/reports/phase5p5_repair5g517_rankers_summary.json"),
        "safety": maybe_json(G517_SAFETY_SUMMARY),
    }
    decision = choose_decision(summaries)
    summary = {
        "schema_version": "phase5p5_repair5g517_decision_summary_v1",
        "decision": decision,
        "adapter_recognition_decision": summaries["adapter"].get("decision", ""),
        "adapter_smoke_decision": summaries["smoke"].get("decision", ""),
        "targeted_probe_integrity_decision": summaries["targeted_integrity"].get("decision", ""),
        "targeted_lattice_oracle_decision": summaries["targeted_oracle"].get("decision", ""),
        "full_primary_integrity_decision": summaries["full_integrity"].get("decision", ""),
        "full_primary_oracle_decision": summaries["full_oracle"].get("decision", ""),
        "ranker_decision": summaries["ranker"].get("decision", ""),
        "safety_update_decision": summaries["safety"].get("decision", ""),
        "safety_package_complete": summaries["safety"].get("safety_package_complete", False),
        "server_required": decision == "server_required_for_expanded_lattice_or_more_contexts",
        "next_step": (
            "continue targeted repair lattice design"
            if decision == "targeted_repair_lattice_no_oracle_gain_continue_lattice_design"
            else "continue full-primary or ranker work only under the recorded gates"
        ),
        **G517_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.17 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- adapter_recognition_decision: `{summary['adapter_recognition_decision']}`\n"
        f"- adapter_smoke_decision: `{summary['adapter_smoke_decision']}`\n"
        f"- targeted_probe_integrity_decision: `{summary['targeted_probe_integrity_decision']}`\n"
        f"- targeted_lattice_oracle_decision: `{summary['targeted_lattice_oracle_decision']}`\n"
        f"- full_primary_integrity_decision: `{summary['full_primary_integrity_decision']}`\n"
        f"- full_primary_oracle_decision: `{summary['full_primary_oracle_decision']}`\n"
        f"- ranker_decision: `{summary['ranker_decision']}`\n"
        f"- safety_update_decision: `{summary['safety_update_decision']}`\n"
        f"- safety_package_complete: `{summary['safety_package_complete']}`\n"
        "- phase5p5_allowed: `false`\n"
        "- phase6_allowed: `false`\n"
        "- runtime_claim_allowed: `false`\n"
        "- learned_runtime_policy_validated: `false`\n"
        "- aaai_ready: `false`\n\n"
        "G5.17 is an observed-ID candidate-space diagnostic round. It does not authorize a runtime learned policy or later-phase claim.\n",
    )
    print(json.dumps({"decision": decision}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

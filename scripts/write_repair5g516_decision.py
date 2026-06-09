"""Write the final Repair5G.5.16 decision report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import read_json, repo_root, resolve, write_json, write_text  # noqa: E402
from repair5g516_common import G516_CLOSED_CLAIMS  # noqa: E402


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g516_decision.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g516_decision_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def maybe_json(path: str) -> dict:
    target = resolve(path, repo_root())
    return read_json(target) if target.exists() else {}


def choose_decision(summaries: dict[str, dict]) -> str:
    verify = summaries["verify"]
    lattice = summaries["lattice"]
    probe = summaries["probe"]
    eval_summary = summaries["eval"]
    safety = summaries["safety"]
    if verify.get("decision") == "missing_g515_artifacts_stop":
        return "missing_g515_artifacts_stop"
    if lattice.get("decision") == "targeted_repair_lattice_requires_adapter_followup":
        return "targeted_repair_lattice_requires_adapter_followup"
    if probe.get("decision") == "targeted_probe_skipped_continue_table_diagnostics":
        return "local_targeted_probe_skipped_continue_table_diagnostics"
    if eval_summary.get("decision") == "pessimistic_ranker_passed_continue_targeted_local_probe":
        if not safety.get("safety_package_complete", False):
            return "safety_package_incomplete_continue_local"
        return "pessimistic_ranker_passed_continue_targeted_local_probe"
    return eval_summary.get("decision", "pessimistic_ranker_no_better_than_g515_continue_feature_design")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    summaries = {
        "verify": maybe_json("outputs/reports/phase5p5_repair5g516_g515_artifact_verification_summary.json"),
        "error_bank": maybe_json("outputs/reports/phase5p5_repair5g516_error_bank_summary.json"),
        "lattice": maybe_json("outputs/reports/phase5p5_repair5g516_targeted_repair_lattice_summary.json"),
        "probe_plan": maybe_json("outputs/reports/phase5p5_repair5g516_local_targeted_probe_plan_summary.json"),
        "probe": maybe_json("outputs/reports/phase5p5_repair5g516_targeted_probe_run_summary.json"),
        "v6": maybe_json("outputs/reports/phase5p5_repair5g516_candidate_feature_matrix_v6_summary.json"),
        "train": maybe_json("outputs/reports/phase5p5_repair5g516_pessimistic_safety_bound_ranker_train_summary.json"),
        "eval": maybe_json("outputs/reports/phase5p5_repair5g516_pessimistic_rankers_summary.json"),
        "autopsy": maybe_json("outputs/reports/phase5p5_repair5g516_error_autopsy_summary.json"),
        "safety": maybe_json("outputs/reports/phase5p5_repair5g516_safety_package_update_summary.json"),
    }
    decision = choose_decision(summaries)
    eval_summary = summaries["eval"]
    safety = summaries["safety"]
    summary = {
        "schema_version": "phase5p5_repair5g516_decision_summary_v1",
        "decision": decision,
        "g515_artifact_verification_decision": summaries["verify"].get("decision", ""),
        "error_bank_decision": summaries["error_bank"].get("decision", ""),
        "targeted_repair_lattice_decision": summaries["lattice"].get("decision", ""),
        "local_targeted_probe_plan_decision": summaries["probe_plan"].get("decision", ""),
        "targeted_probe_run_decision": summaries["probe"].get("decision", ""),
        "v6_matrix_decision": summaries["v6"].get("decision", ""),
        "pessimistic_ranker_train_decision": summaries["train"].get("decision", ""),
        "pessimistic_ranker_eval_decision": eval_summary.get("decision", ""),
        "primary_policy_name": eval_summary.get("primary_policy_name", ""),
        "primary_policy": eval_summary.get("primary_policy", {}),
        "error_autopsy_decision": summaries["autopsy"].get("decision", ""),
        "safety_update_decision": safety.get("decision", ""),
        "safety_package_complete": safety.get("safety_package_complete", False),
        "server_required": decision == "server_required_for_expanded_lattice_or_more_contexts",
        "next_step": "add project-owned adapter recognition for the targeted repair lattice or continue table-only feature/calibration design",
        **G516_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.16 Decision\n\n"
        f"- decision: `{decision}`\n"
        f"- g515_artifact_verification_decision: `{summary['g515_artifact_verification_decision']}`\n"
        f"- error_bank_decision: `{summary['error_bank_decision']}`\n"
        f"- targeted_repair_lattice_decision: `{summary['targeted_repair_lattice_decision']}`\n"
        f"- local_targeted_probe_plan_decision: `{summary['local_targeted_probe_plan_decision']}`\n"
        f"- targeted_probe_run_decision: `{summary['targeted_probe_run_decision']}`\n"
        f"- v6_matrix_decision: `{summary['v6_matrix_decision']}`\n"
        f"- pessimistic_ranker_eval_decision: `{summary['pessimistic_ranker_eval_decision']}`\n"
        f"- primary_policy_name: `{summary['primary_policy_name']}`\n"
        f"- primary_policy: `{summary['primary_policy']}`\n"
        f"- safety_update_decision: `{summary['safety_update_decision']}`\n"
        f"- safety_package_complete: `{summary['safety_package_complete']}`\n"
        "- phase5p5_allowed: `false`\n"
        "- phase6_allowed: `false`\n"
        "- aaai_ready: `false`\n"
        "- runtime_claim_allowed: `false`\n"
        "- learned_runtime_policy_validated: `false`\n\n"
        "G5.16 completed the local table-only diagnostics and designed a small targeted repair lattice. The solver probe did not run because the new `repair5g516_*` method names are not recognized by the current adapter. No C++ or solver semantics were changed, and no runtime/Phase5.5/Phase6/AAAI claim is opened.\n",
    )
    print(json.dumps({"decision": decision, "primary_policy_name": summary["primary_policy_name"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

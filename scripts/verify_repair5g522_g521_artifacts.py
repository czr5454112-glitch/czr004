"""Verify G5.21 artifacts before G5.22 response-surface work."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g522_common import (  # noqa: E402
    G521_ADAPTER_SUMMARY,
    G521_DECISION_SUMMARY,
    G521_GAP_SUMMARY,
    G521_SELECTOR_SUMMARY,
    G521_TARGETED_INTEGRITY_SUMMARY,
    G521_TARGETED_ORACLE_SUMMARY,
    G521_TARGETED_RESULTS_CSV,
    G521_TARGETS_SUMMARY,
    G521_VERIFY_SUMMARY,
    G522_CLOSED_CLAIMS,
    G522_VERIFY_REPORT,
    G522_VERIFY_SUMMARY,
    boolish,
    compact_counter,
    external_lacam2_solver_status,
    finite_number,
    observed_id_flags,
    observed_id_guard,
    read_json_file,
    read_rows,
    repo_root,
    resolve,
    write_json_file,
    write_text_file,
)

G521_FULL_INTEGRITY_SUMMARY = "outputs/reports/phase5p5_repair5g521_full_primary_confirmation_integrity_summary.json"

REQUIRED_INPUTS = [
    G521_VERIFY_SUMMARY,
    G521_ADAPTER_SUMMARY,
    G521_TARGETED_INTEGRITY_SUMMARY,
    G521_TARGETED_ORACLE_SUMMARY,
    G521_TARGETED_RESULTS_CSV,
    G521_TARGETS_SUMMARY,
    G521_SELECTOR_SUMMARY,
    G521_GAP_SUMMARY,
    G521_DECISION_SUMMARY,
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-json", type=Path, default=Path(G522_VERIFY_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G522_VERIFY_REPORT))
    parser.add_argument("--ids", nargs="*", default=None, help="Explicit observed-ID guard probe.")
    return parser.parse_args(argv)


def commit_lineage_includes(root: Path, commit: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.ids is not None:
        try:
            observed_id_guard(args.ids, label="G5.22 explicit ID guard")
        except ValueError as exc:
            print(json.dumps({"decision": "reserved_id_guard_rejected", "error": str(exc)}))
            return 2

    root = repo_root()
    missing = [path for path in REQUIRED_INPUTS if not resolve(path, root).exists()]
    if missing:
        summary = {
            "schema_version": "phase5p5_repair5g522_g521_artifact_verification_summary_v1",
            "decision": "missing_g521_artifacts_stop",
            "missing_required_inputs": missing,
            **G522_CLOSED_CLAIMS,
        }
        write_json_file(args.summary_json, summary)
        write_text_file(args.report, "# Repair5G.5.22 G5.21 Artifact Verification\n\n- decision: `missing_g521_artifacts_stop`\n")
        print(json.dumps({"decision": summary["decision"], "missing": missing}))
        return 2

    verify = read_json_file(G521_VERIFY_SUMMARY)
    adapter = read_json_file(G521_ADAPTER_SUMMARY)
    integrity = read_json_file(G521_TARGETED_INTEGRITY_SUMMARY)
    oracle = read_json_file(G521_TARGETED_ORACLE_SUMMARY)
    targets = read_json_file(G521_TARGETS_SUMMARY)
    selector = read_json_file(G521_SELECTOR_SUMMARY)
    gap = read_json_file(G521_GAP_SUMMARY)
    decision_summary = read_json_file(G521_DECISION_SUMMARY)
    full_integrity = read_json_file(G521_FULL_INTEGRITY_SUMMARY)
    rows = read_rows(G521_TARGETED_RESULTS_CSV)
    context_counts = compact_counter(rows, "normalized_context_key")
    candidate_counts = compact_counter(rows, "candidate_id")
    flags = observed_id_flags(rows)
    external_status = external_lacam2_solver_status(root)
    closed_claims = {
        key: not boolish(decision_summary.get(key))
        for key in G522_CLOSED_CLAIMS
    }
    gates = {
        "commit_lineage_includes_8120cf1": commit_lineage_includes(root, "8120cf1"),
        "g521_final_decision_expected": decision_summary.get("decision") == "g521_second_wave_no_candidate_space_gain_continue_lattice_autopsy",
        "g521_verify_passed": verify.get("decision") == "g520_artifacts_verified_continue_g521",
        "g521_adapter_passed": adapter.get("decision") == "adapter_grammar_passed_continue_targeted_probe",
        "targeted_probe_integrity_passed": integrity.get("decision") == "targeted_second_wave_probe_integrity_passed_continue_oracle",
        "targeted_probe_rows_eq_1596": len(rows) == 1596 and int(finite_number(integrity.get("probe_rows"), -1)) == 1596,
        "targeted_contexts_eq_21": len(context_counts) == 21 and int(finite_number(integrity.get("contexts_observed"), -1)) == 21,
        "targeted_candidates_eq_38": len(candidate_counts) == 38 and int(finite_number(integrity.get("candidate_count"), -1)) == 38,
        "targeted_gate_failed": oracle.get("decision") == "targeted_second_wave_gate_failed_lattice_autopsy" and not boolish(oracle.get("targeted_gate_passed")),
        "full_primary_confirmation_skipped": full_integrity.get("decision") == "full_primary_confirmation_skipped_targeted_gate_failed" and not boolish(full_integrity.get("probe_ran")),
        "v10_targets_exist": targets.get("decision") == "targets_v10_passed_continue_split_features",
        "split_selector_summary_exists": selector.get("decision") == "split_selector_eval_completed",
        "oracle_to_policy_gap_autopsy_exists": bool(gap.get("decision")),
        "external_lacam2_solver_untouched": not external_status,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        **{f"{key}_closed": value for key, value in closed_claims.items()},
    }
    decision = "g521_artifacts_verified_continue_g522" if all(gates.values()) else "g521_artifact_verification_failed_stop"
    summary = {
        "schema_version": "phase5p5_repair5g522_g521_artifact_verification_summary_v1",
        "decision": decision,
        "required_inputs": REQUIRED_INPUTS,
        "missing_required_inputs": [],
        "targeted_probe_rows": len(rows),
        "targeted_contexts": len(context_counts),
        "targeted_candidates": len(candidate_counts),
        "g521_final_decision": decision_summary.get("decision", ""),
        "targeted_oracle_decision": oracle.get("decision", ""),
        "full_primary_confirmation_decision": full_integrity.get("decision", ""),
        "selector_decision": selector.get("decision", ""),
        "oracle_to_policy_gap_decision": gap.get("decision", ""),
        "external_lacam2_solver_status": external_status,
        "gates": gates,
        **flags,
        **G522_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.22 G5.21 Artifact Verification\n\n"
        f"- decision: `{decision}`\n"
        f"- targeted_probe_rows: `{len(rows)}`\n"
        f"- targeted_contexts: `{len(context_counts)}`\n"
        f"- targeted_candidates: `{len(candidate_counts)}`\n"
        f"- g521_final_decision: `{decision_summary.get('decision', '')}`\n"
        f"- targeted_oracle_decision: `{oracle.get('decision', '')}`\n"
        f"- full_primary_confirmation_decision: `{full_integrity.get('decision', '')}`\n"
        f"- observed_ids_only: `{flags['observed_ids_only']}`\n"
        f"- ids_166_205_untouched: `{flags['ids_166_205_untouched']}`\n"
        f"- gates: `{gates}`\n",
    )
    print(json.dumps({"decision": decision, "targeted_probe_rows": len(rows)}))
    return 0 if decision == "g521_artifacts_verified_continue_g522" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

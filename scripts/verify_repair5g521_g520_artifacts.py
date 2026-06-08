"""Verify G5.20 artifacts before running G5.21 second-wave diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g521_common import (  # noqa: E402
    G520_DECISION_SUMMARY,
    G520_FEATURE_MATRIX_CSV,
    G520_POLICY_SUMMARY,
    G520_SECOND_WAVE_CONTEXTS_CSV,
    G520_SECOND_WAVE_SUMMARY,
    G520_TARGETS_CSV,
    G520_TARGETS_SUMMARY,
    G521_CLOSED_CLAIMS,
    G521_VERIFY_REPORT,
    G521_VERIFY_SUMMARY,
    boolish,
    compact_counter,
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


REQUIRED_INPUTS = [
    G520_DECISION_SUMMARY,
    G520_TARGETS_CSV,
    G520_TARGETS_SUMMARY,
    G520_FEATURE_MATRIX_CSV,
    G520_POLICY_SUMMARY,
    G520_SECOND_WAVE_CONTEXTS_CSV,
    G520_SECOND_WAVE_SUMMARY,
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-json", type=Path, default=Path(G521_VERIFY_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G521_VERIFY_REPORT))
    parser.add_argument("--ids", nargs="*", default=None, help="Optional explicit reserved-ID guard probe.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.ids is not None:
        try:
            observed_id_guard(args.ids, label="G5.21 explicit ID guard")
        except ValueError as exc:
            print(json.dumps({"decision": "reserved_id_guard_rejected", "error": str(exc)}))
            return 2

    root = repo_root()
    missing = [path for path in REQUIRED_INPUTS if not resolve(path, root).exists()]
    if missing:
        summary = {
            "schema_version": "phase5p5_repair5g521_g520_artifact_verification_summary_v1",
            "decision": "missing_g520_artifacts_stop",
            "missing_required_inputs": missing,
            **G521_CLOSED_CLAIMS,
        }
        write_json_file(args.summary_json, summary)
        write_text_file(args.report, "# Repair5G.5.21 G5.20 Artifact Verification\n\n- decision: `missing_g520_artifacts_stop`\n")
        print(json.dumps({"decision": summary["decision"], "missing": missing}))
        return 2

    decision_summary = read_json_file(G520_DECISION_SUMMARY)
    targets_summary = read_json_file(G520_TARGETS_SUMMARY)
    policy_summary = read_json_file(G520_POLICY_SUMMARY)
    second_wave_summary = read_json_file(G520_SECOND_WAVE_SUMMARY)
    targets = read_rows(G520_TARGETS_CSV)
    features = read_rows(G520_FEATURE_MATRIX_CSV)
    target_context_counts = compact_counter(targets, "normalized_context_key")
    feature_context_counts = compact_counter(features, "normalized_context_key")
    second_wave_rows = read_rows(G520_SECOND_WAVE_CONTEXTS_CSV)
    flags = observed_id_flags(targets + features + second_wave_rows)
    best = policy_summary.get("best_policy_summary", {})
    gates = {
        "final_decision_expected": decision_summary.get("decision") == "second_wave_lattice_planned_continue_local_probe",
        "corrected_target_rows_eq_1320": len(targets) == 1320,
        "feature_rows_eq_1320": len(features) == 1320,
        "target_contexts_eq_60": len(target_context_counts) == 60,
        "feature_contexts_eq_60": len(feature_context_counts) == 60,
        "targets_candidates_per_context_eq_22": all(count == 22 for count in target_context_counts.values()),
        "features_candidates_per_context_eq_22": all(count == 22 for count in feature_context_counts.values()),
        "g520_best_policy_no_new_candidate_ablation": policy_summary.get("best_policy") == "no_new_candidate_ablation",
        "g520_new_candidate_selection_count_eq_0": int(finite_number(best.get("new_candidate_selection_count"), -1)) == 0,
        "second_wave_plan_exists": boolish(second_wave_summary.get("plan_created")),
        "target_context_count_eq_16": len(second_wave_rows) == 16 and int(finite_number(second_wave_summary.get("target_context_count"), -1)) == 16,
        "forbidden_feature_count_eq_0": int(finite_number(policy_summary.get("forbidden_feature_count"), -1)) == 0,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "runtime_claim_allowed_false": not boolish(decision_summary.get("runtime_claim_allowed")),
    }
    decision = "g520_artifacts_verified_continue_g521" if all(gates.values()) else "g520_artifact_verification_failed_stop"
    summary = {
        "schema_version": "phase5p5_repair5g521_g520_artifact_verification_summary_v1",
        "decision": decision,
        "required_inputs": REQUIRED_INPUTS,
        "missing_required_inputs": [],
        "target_rows": len(targets),
        "feature_rows": len(features),
        "contexts": len(target_context_counts),
        "candidate_rows_per_context_min": min(target_context_counts.values()) if target_context_counts else 0,
        "candidate_rows_per_context_max": max(target_context_counts.values()) if target_context_counts else 0,
        "g520_best_policy": policy_summary.get("best_policy", ""),
        "g520_new_candidate_selection_count": best.get("new_candidate_selection_count", ""),
        "second_wave_target_context_count": len(second_wave_rows),
        "forbidden_feature_count": policy_summary.get("forbidden_feature_count", ""),
        "gates": gates,
        **flags,
        **G521_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Repair5G.5.21 G5.20 Artifact Verification\n\n"
        f"- decision: `{decision}`\n"
        f"- target_rows: `{len(targets)}`\n"
        f"- feature_rows: `{len(features)}`\n"
        f"- contexts: `{len(target_context_counts)}`\n"
        f"- candidates_per_context_min: `{summary['candidate_rows_per_context_min']}`\n"
        f"- candidates_per_context_max: `{summary['candidate_rows_per_context_max']}`\n"
        f"- g520_best_policy: `{summary['g520_best_policy']}`\n"
        f"- g520_new_candidate_selection_count: `{summary['g520_new_candidate_selection_count']}`\n"
        f"- second_wave_target_context_count: `{len(second_wave_rows)}`\n"
        f"- forbidden_feature_count: `{summary['forbidden_feature_count']}`\n"
        f"- observed_ids_only: `{flags['observed_ids_only']}`\n"
        f"- ids_166_205_untouched: `{flags['ids_166_205_untouched']}`\n"
        f"- gates: `{gates}`\n",
    )
    print(json.dumps({"decision": decision, "target_rows": len(targets), "feature_rows": len(features)}))
    return 0 if decision == "g520_artifacts_verified_continue_g521" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

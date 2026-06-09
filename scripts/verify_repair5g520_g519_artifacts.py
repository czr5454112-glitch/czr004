"""Verify G5.19 artifacts before starting G5.20 corrected policy diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g520_common import (  # noqa: E402
    G519_REQUIRED_ARTIFACTS,
    G520_CLOSED_CLAIMS,
    G520_VERIFY_REPORT,
    G520_VERIFY_SUMMARY,
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-json", type=Path, default=Path(G520_VERIFY_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G520_VERIFY_REPORT))
    parser.add_argument("--ids", nargs="*", default=None, help="Optional explicit ID guard probe.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.ids is not None:
        try:
            observed_id_guard(args.ids, label="G5.20 explicit ID guard")
        except ValueError as exc:
            print(json.dumps({"decision": "reserved_id_guard_rejected", "error": str(exc)}))
            return 2

    root = repo_root()
    missing = [path for path in G519_REQUIRED_ARTIFACTS if not resolve(path, root).exists()]
    if missing:
        summary = {
            "schema_version": "phase5p5_repair5g520_g519_artifact_verification_summary_v1",
            "decision": "missing_g519_artifacts_stop",
            "missing_required_inputs": missing,
            **G520_CLOSED_CLAIMS,
        }
        write_json_file(args.summary_json, summary)
        write_text_file(
            args.report,
            "# Phase5.5 Repair5G.5.20 G5.19 Artifact Verification\n\n"
            "- decision: `missing_g519_artifacts_stop`\n"
            f"- missing_required_inputs: `{missing}`\n",
        )
        print(json.dumps({"decision": summary["decision"], "missing_required_inputs": missing}))
        return 2

    decision_summary = read_json_file("outputs/reports/phase5p5_repair5g519_decision_summary.json")
    autopsy_summary = read_json_file("outputs/reports/phase5p5_repair5g519_ranker_failure_autopsy_summary.json")
    targets = read_rows("outputs/tables/phase5p5_repair5g519_full_primary_candidate_targets.csv")
    features = read_rows("outputs/tables/phase5p5_repair5g519_candidate_feature_matrix_v8.csv")
    eval_rows = read_rows("outputs/tables/phase5p5_repair5g519_ranker_suite_eval.csv")
    context_rows = read_rows("outputs/tables/phase5p5_repair5g519_ranker_context_decisions.csv")

    target_context_counts = compact_counter(targets, "normalized_context_key")
    feature_context_counts = compact_counter(features, "normalized_context_key")
    seed_oof_policies = {
        str(row.get("policy", ""))
        for row in eval_rows
        if row.get("row_type") == "policy_summary" and row.get("eval_scope") == "seed_oof"
    }
    seed_oof_context_policy_counts = compact_counter(
        (
            {
                "key": f"{row.get('policy', '')}|{row.get('normalized_context_key', '')}",
            }
            for row in context_rows
            if row.get("eval_scope") == "seed_oof"
        ),
        "key",
    )
    flags = observed_id_flags(targets)
    gates = {
        "g519_decision_expected": decision_summary.get("decision") == "ranker_ignores_new_candidates_continue_candidate_policy_design",
        "g519_best_policy_no_new_ablation": decision_summary.get("best_policy") == "no_new_candidate_ablation",
        "g519_candidate_space_survived": boolish(decision_summary.get("g518_candidate_space_survived_target_reconstruction")),
        "targets_rows_eq_1320": len(targets) == 1320,
        "features_rows_eq_1320": len(features) == 1320,
        "target_contexts_eq_60": len(target_context_counts) == 60,
        "feature_contexts_eq_60": len(feature_context_counts) == 60,
        "targets_22_candidates_per_context": all(count == 22 for count in target_context_counts.values()),
        "features_22_candidates_per_context": all(count == 22 for count in feature_context_counts.values()),
        "ranker_eval_has_seed_oof": len(seed_oof_policies) > 0,
        "context_decisions_seed_oof_grouped": len(seed_oof_context_policy_counts) >= len(seed_oof_policies) * 60,
        "autopsy_new_candidate_win_contexts_gt_0": int(finite_number(autopsy_summary.get("new_candidate_win_contexts"), 0)) > 0,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "runtime_claim_allowed_false": not boolish(decision_summary.get("runtime_claim_allowed")),
    }
    decision = "g519_artifacts_verified_continue_g520" if all(gates.values()) else "g519_artifact_verification_failed_stop"
    summary = {
        "schema_version": "phase5p5_repair5g520_g519_artifact_verification_summary_v1",
        "decision": decision,
        "required_inputs": G519_REQUIRED_ARTIFACTS,
        "missing_required_inputs": [],
        "target_rows": len(targets),
        "feature_rows": len(features),
        "contexts": len(target_context_counts),
        "candidate_rows_per_context_min": min(target_context_counts.values()) if target_context_counts else 0,
        "candidate_rows_per_context_max": max(target_context_counts.values()) if target_context_counts else 0,
        "seed_oof_policy_count": len(seed_oof_policies),
        "g519_best_policy": decision_summary.get("best_policy", ""),
        "g519_ranker_decision": decision_summary.get("decision", ""),
        "g519_new_candidate_win_contexts": autopsy_summary.get("new_candidate_win_contexts", ""),
        "gates": gates,
        **flags,
        **G520_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.20 G5.19 Artifact Verification\n\n"
        f"- decision: `{decision}`\n"
        f"- target_rows: `{len(targets)}`\n"
        f"- feature_rows: `{len(features)}`\n"
        f"- contexts: `{len(target_context_counts)}`\n"
        f"- candidate_rows_per_context_min: `{summary['candidate_rows_per_context_min']}`\n"
        f"- candidate_rows_per_context_max: `{summary['candidate_rows_per_context_max']}`\n"
        f"- seed_oof_policy_count: `{len(seed_oof_policies)}`\n"
        f"- g519_best_policy: `{summary['g519_best_policy']}`\n"
        f"- g519_new_candidate_win_contexts: `{summary['g519_new_candidate_win_contexts']}`\n"
        f"- observed_ids_only: `{flags['observed_ids_only']}`\n"
        f"- ids_166_205_untouched: `{flags['ids_166_205_untouched']}`\n"
        f"- gates: `{gates}`\n",
    )
    print(json.dumps({"decision": decision, "target_rows": len(targets), "feature_rows": len(features)}))
    return 0 if decision == "g519_artifacts_verified_continue_g520" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

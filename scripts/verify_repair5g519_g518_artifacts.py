"""Verify G5.18 artifacts before starting G5.19 ranker diagnostics."""

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
    G514_RICH_CONTEXT_FEATURES,
    G515_V5_MATRIX,
    G518_DECISION_SUMMARY,
    G518_FULL_PRIMARY_INTEGRITY_SUMMARY,
    G518_FULL_PRIMARY_ORACLE_SUMMARY,
    G518_FULL_PRIMARY_RESULTS,
    G518_SELECTED_CSV,
    G519_CLOSED_CLAIMS,
    G519_VERIFY_REPORT,
    G519_VERIFY_SUMMARY,
    PRIMARY_BUDGETS,
    as_jsonable,
    boolish,
    compact_counter,
    finite_number,
    full_primary_candidate_ids,
    observed_id_flags,
    old14_candidate_ids,
    read_json_file,
    read_rows,
    repo_root,
    resolve,
    selected_new_candidate_ids_from_results,
    write_json_file,
    write_text_file,
)


REQUIRED_INPUTS = [
    G518_DECISION_SUMMARY,
    G518_FULL_PRIMARY_INTEGRITY_SUMMARY,
    G518_FULL_PRIMARY_ORACLE_SUMMARY,
    G518_FULL_PRIMARY_RESULTS,
    G515_V5_MATRIX,
    G514_RICH_CONTEXT_FEATURES,
    G518_SELECTED_CSV,
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-json", type=Path, default=Path(G519_VERIFY_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(G519_VERIFY_REPORT))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    missing = [path for path in REQUIRED_INPUTS if not resolve(path, root).exists()]
    if missing:
        summary = {
            "schema_version": "phase5p5_repair5g519_g518_artifact_verification_summary_v1",
            "decision": "missing_g518_artifacts_stop",
            "missing_required_inputs": missing,
            **G519_CLOSED_CLAIMS,
        }
        write_json_file(args.summary_json, summary)
        write_text_file(
            args.report,
            "# Phase5.5 Repair5G.5.19 G5.18 Artifact Verification\n\n"
            "- decision: `missing_g518_artifacts_stop`\n"
            f"- missing_required_inputs: `{missing}`\n"
            "- runtime_claim_allowed: `false`\n",
        )
        print(json.dumps({"decision": summary["decision"], "missing_required_inputs": missing}))
        return 2

    decision_summary = read_json_file(G518_DECISION_SUMMARY)
    integrity_summary = read_json_file(G518_FULL_PRIMARY_INTEGRITY_SUMMARY)
    oracle_summary = read_json_file(G518_FULL_PRIMARY_ORACLE_SUMMARY)
    rows = read_rows(G518_FULL_PRIMARY_RESULTS)
    flags = observed_id_flags(rows)
    old_ids = set(old14_candidate_ids(root))
    candidates = full_primary_candidate_ids(rows)
    new_ids = selected_new_candidate_ids_from_results(rows, old_ids)
    contexts = {row.get("normalized_context_key", "") for row in rows}
    budgets = {int(finite_number(row.get("short_budget_ms"), -1)) for row in rows}
    context_budget_pairs = {(row.get("normalized_context_key", ""), row.get("short_budget_ms", "")) for row in rows}
    rows_per_context_budget = compact_counter(
        ({"key": f"{row.get('normalized_context_key', '')}|{row.get('short_budget_ms', '')}"} for row in rows),
        "key",
    )
    duplicate_count = sum(max(0, count - len(candidates)) for count in rows_per_context_budget.values())
    complete_context_budget_pairs = sum(1 for count in rows_per_context_budget.values() if count == len(candidates))
    gates = {
        "g518_final_decision": decision_summary.get("decision") == "g518_full_primary_candidate_space_improved_continue_ranker",
        "full_primary_rows_eq_2640": len(rows) == 2640,
        "contexts_eq_60": len(contexts) == 60,
        "candidate_count_eq_22": len(candidates) == 22,
        "old_candidate_count_eq_14": len(old_ids & set(candidates)) == 14,
        "new_candidate_count_eq_8": len(new_ids) == 8,
        "budgets_eq_1000_2000": budgets == set(PRIMARY_BUDGETS),
        "complete_context_budget_pairs_eq_120": complete_context_budget_pairs == 120 and len(context_budget_pairs) == 120,
        "duplicate_context_candidate_budget_rows_eq_0": duplicate_count == 0,
        "new_candidate_win_count_gt_0": finite_number(oracle_summary.get("new_candidate_win_count"), 0) > 0,
        "mean_new_oracle_gap_vs_old_oracle_lt_0": finite_number(oracle_summary.get("mean_new_oracle_gap_vs_old_oracle"), math.inf) < 0,
        "observed_ids_only": flags["observed_ids_only"],
        "ids_166_205_untouched": flags["ids_166_205_untouched"],
        "runtime_claim_allowed_false": not boolish(decision_summary.get("runtime_claim_allowed")),
        "integrity_summary_contexts_eq_60": int(finite_number(integrity_summary.get("contexts"), -1)) == 60,
    }
    decision = "g518_artifacts_verified_continue_g519" if all(gates.values()) else "missing_g518_artifacts_stop"
    summary = {
        "schema_version": "phase5p5_repair5g519_g518_artifact_verification_summary_v1",
        "decision": decision,
        "required_inputs": REQUIRED_INPUTS,
        "missing_required_inputs": [],
        "full_primary_rows": len(rows),
        "contexts": len(contexts),
        "candidate_count": len(candidates),
        "old_candidate_count": len(old_ids & set(candidates)),
        "new_candidate_count": len(new_ids),
        "budgets": sorted(budgets),
        "context_budget_pairs": len(context_budget_pairs),
        "complete_context_budget_pairs": complete_context_budget_pairs,
        "duplicate_context_candidate_budget_rows": duplicate_count,
        "new_candidate_win_count": int(finite_number(oracle_summary.get("new_candidate_win_count"), 0)),
        "mean_new_oracle_gap_vs_old_oracle": as_jsonable(finite_number(oracle_summary.get("mean_new_oracle_gap_vs_old_oracle"), math.inf)),
        "gates": gates,
        **flags,
        **G519_CLOSED_CLAIMS,
    }
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.19 G5.18 Artifact Verification\n\n"
        f"- decision: `{decision}`\n"
        f"- full_primary_rows: `{len(rows)}`\n"
        f"- contexts: `{len(contexts)}`\n"
        f"- candidate_count: `{len(candidates)}`\n"
        f"- old_candidate_count: `{len(old_ids & set(candidates))}`\n"
        f"- new_candidate_count: `{len(new_ids)}`\n"
        f"- budgets: `{sorted(budgets)}`\n"
        f"- new_candidate_win_count: `{summary['new_candidate_win_count']}`\n"
        f"- mean_new_oracle_gap_vs_old_oracle: `{summary['mean_new_oracle_gap_vs_old_oracle']}`\n"
        f"- observed_ids_only: `{flags['observed_ids_only']}`\n"
        f"- ids_166_205_untouched: `{flags['ids_166_205_untouched']}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        f"Gates: `{gates}`\n",
    )
    print(json.dumps({"decision": decision, "rows": len(rows), "contexts": len(contexts), "candidate_count": len(candidates)}))
    return 0 if decision == "g518_artifacts_verified_continue_g519" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

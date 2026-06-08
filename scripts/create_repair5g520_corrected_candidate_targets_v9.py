"""Build corrected G5.20 v9 candidate targets from G5.19 targets and semantics audit."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g520_common import (  # noqa: E402
    DEFAULT_MARGIN,
    G519_TARGETS_CSV,
    G520_CLOSED_CLAIMS,
    G520_TARGETS_CSV,
    G520_TARGETS_REPORT,
    G520_TARGETS_SUMMARY,
    G520_TARGET_SEMANTICS_AUDIT_CSV,
    STATIC_FLOW_SHIELD_CANDIDATE,
    boolish,
    compact_counter,
    corrected_delta,
    csv_number,
    finite_number,
    helpful,
    old14_candidate_ids,
    read_rows,
    repo_root,
    row_key,
    rows_by_context,
    total_harmful,
    write_json_file,
    write_rows,
    write_text_file,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets-csv", type=Path, default=Path(G519_TARGETS_CSV))
    parser.add_argument("--audit-csv", type=Path, default=Path(G520_TARGET_SEMANTICS_AUDIT_CSV))
    parser.add_argument("--output-csv", type=Path, default=Path(G520_TARGETS_CSV))
    parser.add_argument("--report", type=Path, default=Path(G520_TARGETS_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(G520_TARGETS_SUMMARY))
    return parser.parse_args(argv)


def score(row: dict[str, Any]) -> float:
    return finite_number(row.get("score_primary"), math.inf)


def best_finite(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    finite = [row for row in rows if math.isfinite(score(row))]
    return min(finite, key=lambda row: (score(row), str(row.get("candidate_id", "")))) if finite else None


def context_opportunity_fields(group: list[dict[str, Any]], old_ids: set[str]) -> dict[str, Any]:
    old_rows = [row for row in group if str(row.get("candidate_id", "")) in old_ids]
    new_rows = [row for row in group if boolish(row.get("is_new_candidate"))]
    old_best = best_finite(old_rows)
    new_best = best_finite(new_rows)
    old_score = score(old_best) if old_best else math.inf
    new_score = score(new_best) if new_best else math.inf
    gap = new_score - old_score
    new22_winner_is_new = any(boolish(row.get("is_new22_oracle_winner")) and boolish(row.get("is_new_candidate")) for row in group)
    opportunity = math.isfinite(gap) and gap <= -DEFAULT_MARGIN or new22_winner_is_new
    return {
        "oracle_old14_candidate_for_context_v9": old_best.get("candidate_id", "") if old_best else "",
        "oracle_old14_score_for_context_v9": csv_number(old_score),
        "oracle_new_candidate_for_context": new_best.get("candidate_id", "") if new_best else "",
        "oracle_new_candidate_score_for_context": csv_number(new_score),
        "new_candidate_best_gap_vs_old14": csv_number(gap),
        "new_candidate_win_context": bool(new22_winner_is_new),
        "new_candidate_opportunity_context": bool(opportunity),
        "new_opportunity_context": bool(opportunity),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    old_ids = set(old14_candidate_ids(root))
    targets = read_rows(args.targets_csv)
    audit = {row_key(row): row for row in read_rows(args.audit_csv)}
    rows: list[dict[str, Any]] = []
    for context, group in sorted(rows_by_context(targets).items()):
        fields = context_opportunity_fields(group, old_ids)
        oracle_new = str(fields.get("oracle_new_candidate_for_context", ""))
        for source in sorted(group, key=lambda row: str(row.get("candidate_id", ""))):
            row = dict(source)
            audit_row = audit.get(row_key(source), {})
            row.update(fields)
            for field in [
                "solution_quality_delta_vs_static",
                "solution_quality_harmful_vs_static",
                "no_solution_or_infeasible",
                "budget_missing_or_nonfinite",
                "budget_nonfinite",
                "safe_static_neutral",
                "harmful_total",
            ]:
                row[field] = audit_row.get(field, "")
            row["helpful_vs_static_corrected"] = helpful(row)
            row["total_harmful_corrected"] = total_harmful(row)
            row["new_opportunity_candidate"] = (
                boolish(row.get("is_new_candidate"))
                and boolish(row.get("new_opportunity_context"))
                and str(row.get("candidate_id", "")) == oracle_new
            )
            row["safe_new_candidate_positive"] = boolish(row.get("is_new_candidate")) and helpful(row) and not total_harmful(row)
            row["static_self_neutrality"] = (
                str(row.get("candidate_id", "")) == STATIC_FLOW_SHIELD_CANDIDATE
                and boolish(row.get("safe_static_neutral"))
            )
            row["target_semantics_version"] = "v9_solution_quality_separated_from_no_solution"
            row.update(G520_CLOSED_CLAIMS)
            rows.append(row)

    context_counts = compact_counter(rows, "normalized_context_key")
    new_opportunity_contexts = {
        row.get("normalized_context_key", "")
        for row in rows
        if boolish(row.get("new_opportunity_context"))
    }
    new_opportunity_candidates = [row for row in rows if boolish(row.get("new_opportunity_candidate"))]
    safe_new_positive_rows = [row for row in rows if boolish(row.get("safe_new_candidate_positive"))]
    corrected_solution_harm_rows = [row for row in rows if boolish(row.get("solution_quality_harmful_vs_static"))]
    no_solution_rows = [row for row in rows if boolish(row.get("no_solution_or_infeasible")) or boolish(row.get("budget_nonfinite"))]
    gates = {
        "rows_eq_1320": len(rows) == 1320,
        "contexts_eq_60": len(context_counts) == 60,
        "candidates_per_context_eq_22": all(count == 22 for count in context_counts.values()),
        "new_opportunity_contexts_gt_0": len(new_opportunity_contexts) > 0,
        "new_opportunity_candidate_rows_gt_0": len(new_opportunity_candidates) > 0,
        "safe_new_candidate_positive_rows_gt_0": len(safe_new_positive_rows) > 0,
        "static_self_neutrality_present": sum(1 for row in rows if boolish(row.get("static_self_neutrality"))) > 0,
    }
    decision = "corrected_targets_v9_passed_continue_opportunity_features" if all(gates.values()) else "corrected_targets_v9_failed"
    summary = {
        "schema_version": "phase5p5_repair5g520_corrected_candidate_targets_v9_summary_v1",
        "decision": decision,
        "target_rows": len(rows),
        "contexts": len(context_counts),
        "candidate_rows_per_context_min": min(context_counts.values()) if context_counts else 0,
        "candidate_rows_per_context_max": max(context_counts.values()) if context_counts else 0,
        "new_opportunity_contexts": len(new_opportunity_contexts),
        "new_opportunity_candidate_rows": len(new_opportunity_candidates),
        "safe_new_candidate_positive_rows": len(safe_new_positive_rows),
        "solution_quality_harmful_rows": len(corrected_solution_harm_rows),
        "no_solution_or_nonfinite_rows": len(no_solution_rows),
        "candidate_space_gain_too_sparse_for_current_policy": len(new_opportunity_contexts) < 8,
        "gates": gates,
        **G520_CLOSED_CLAIMS,
    }
    write_rows(args.output_csv, rows)
    write_json_file(args.summary_json, summary)
    write_text_file(
        args.report,
        "# Phase5.5 Repair5G.5.20 Corrected Candidate Targets V9\n\n"
        f"- decision: `{decision}`\n"
        f"- target_rows: `{len(rows)}`\n"
        f"- contexts: `{len(context_counts)}`\n"
        f"- candidate_rows_per_context_min: `{summary['candidate_rows_per_context_min']}`\n"
        f"- candidate_rows_per_context_max: `{summary['candidate_rows_per_context_max']}`\n"
        f"- new_opportunity_contexts: `{len(new_opportunity_contexts)}`\n"
        f"- new_opportunity_candidate_rows: `{len(new_opportunity_candidates)}`\n"
        f"- safe_new_candidate_positive_rows: `{len(safe_new_positive_rows)}`\n"
        f"- solution_quality_harmful_rows: `{len(corrected_solution_harm_rows)}`\n"
        f"- no_solution_or_nonfinite_rows: `{len(no_solution_rows)}`\n"
        "- runtime_claim_allowed: `false`\n\n"
        "V9 preserves one row per context and candidate while separating solution-quality harm from no-solution or nonfinite risk. "
        "New-candidate opportunity labels are target columns, not runtime feature columns.\n",
    )
    print(json.dumps({"decision": decision, "target_rows": len(rows), "new_opportunity_contexts": len(new_opportunity_contexts)}))
    return 0 if decision != "corrected_targets_v9_failed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

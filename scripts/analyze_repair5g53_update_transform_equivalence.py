"""Analyze Repair5G.5.3 UpdateLTM transform-equivalence audit rows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import git_value, read_jsonl, repo_root, resolve, write_csv_rows, write_json  # noqa: E402
from repair5g51_common import write_text  # noqa: E402


DEFAULT_AUDIT = "outputs/logs/phase5p5_repair5g53_update_transform_equivalence/phase5p5_repair5g53_update_transform_audit.jsonl"
DEFAULT_TABLE = "outputs/tables/phase5p5_repair5g53_update_transform_equivalence_mismatches.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g53_update_transform_equivalence_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g53_update_transform_equivalence_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-jsonl", type=Path, default=Path(DEFAULT_AUDIT))
    parser.add_argument("--mismatch-csv", type=Path, default=Path(DEFAULT_TABLE))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def mismatch_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        stat_match = (
            row.get("congestion_update_count_expected") == row.get("congestion_update_count_actual")
            and row.get("flow_update_count_expected") == row.get("flow_update_count_actual")
            and row.get("congestion_delta_total_expected") == row.get("congestion_delta_total_actual")
            and row.get("flow_delta_total_expected") == row.get("flow_delta_total_actual")
        )
        if bool(row.get("traffic_after_hash_match")) and bool(row.get("params_hash_match")) and stat_match:
            continue
        out.append(
            {
                "method": row.get("method", ""),
                "map": row.get("map", ""),
                "agents": row.get("agents", ""),
                "seed": row.get("seed", ""),
                "iteration": row.get("iteration", ""),
                "candidate_id": row.get("candidate_id", ""),
                "resolved_candidate_id": row.get("resolved_candidate_id", ""),
                "candidate_recognized": row.get("candidate_recognized", ""),
                "traffic_after_hash_match": row.get("traffic_after_hash_match", ""),
                "params_hash_match": row.get("params_hash_match", ""),
                "stats_match": stat_match,
                "expected_traffic_after_hash_full": row.get("expected_traffic_after_hash_full", ""),
                "actual_traffic_after_hash_full": row.get("actual_traffic_after_hash_full", ""),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    audit_path = resolve(args.audit_jsonl, root)
    rows = read_jsonl(audit_path)
    mismatches = mismatch_rows(rows)
    write_csv_rows(resolve(args.mismatch_csv, root), mismatches)
    recognized = [row for row in rows if bool(row.get("candidate_recognized"))]
    hash_mismatches = [row for row in rows if not bool(row.get("traffic_after_hash_match"))]
    param_mismatches = [row for row in rows if not bool(row.get("params_hash_match"))]
    stat_mismatches = [
        row
        for row in rows
        if row.get("congestion_update_count_expected") != row.get("congestion_update_count_actual")
        or row.get("flow_update_count_expected") != row.get("flow_update_count_actual")
        or row.get("congestion_delta_total_expected") != row.get("congestion_delta_total_actual")
        or row.get("flow_delta_total_expected") != row.get("flow_delta_total_actual")
    ]
    gates = {
        "audit_rows_gt_0": len(rows) > 0,
        "all_candidates_recognized": len(rows) > 0 and len(recognized) == len(rows),
        "traffic_after_hash_mismatch_count": len(hash_mismatches),
        "params_hash_mismatch_count": len(param_mismatches),
        "true_semantic_mismatch_count": len(mismatches),
        "cf_update_stat_mismatch_count": len(stat_mismatches),
    }
    gates["update_transform_equivalence_passed"] = all(
        [
            gates["audit_rows_gt_0"],
            gates["all_candidates_recognized"],
            gates["traffic_after_hash_mismatch_count"] == 0,
            gates["params_hash_mismatch_count"] == 0,
            gates["true_semantic_mismatch_count"] == 0,
            gates["cf_update_stat_mismatch_count"] == 0,
        ]
    )
    summary = {
        "schema_version": "phase5p5_repair5g53_update_transform_equivalence_summary_v1",
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "audit_jsonl": str(audit_path),
        "row_count": len(rows),
        "mismatch_rows": len(mismatches),
        "gates": gates,
        "decision": "continue_minimal_hook_gate" if gates["update_transform_equivalence_passed"] else "update_transform_semantic_bug",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.3 Update Transform Equivalence\n\n"
        f"- audit_rows: `{len(rows)}`\n"
        f"- traffic_after_hash_mismatch_count: `{gates['traffic_after_hash_mismatch_count']}`\n"
        f"- params_hash_mismatch_count: `{gates['params_hash_mismatch_count']}`\n"
        f"- cf_update_stat_mismatch_count: `{gates['cf_update_stat_mismatch_count']}`\n"
        f"- update_transform_equivalence_passed: `{gates['update_transform_equivalence_passed']}`\n"
        f"- decision: `{summary['decision']}`\n\n"
        "`phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain mandatory.\n",
    )
    print(json.dumps({"decision": summary["decision"], "rows": len(rows), "mismatches": len(mismatches)}))
    return 0 if gates["update_transform_equivalence_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

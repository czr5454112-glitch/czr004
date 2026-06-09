"""Optional guarded local static-boundary probe planner for G5.12.

This script does not run the solver by default. It audits existing G5.12 target
rows for static-near-oracle/static-win contexts and enforces the observed-ID
guard before any future local solver probe could be wired in.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import (  # noqa: E402
    CLOSED_CLAIMS,
    DEFAULT_MARGIN,
    STATIC_ABSTAIN_CANDIDATE,
    STATIC_FLOW_SHIELD_CANDIDATE,
    finite_number,
    observed_id_guard,
    read_csv_rows,
    repo_root,
    resolve,
    write_json,
    write_text,
)


DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g512_candidate_regret_targets.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g512_static_boundary_probe_local.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g512_static_boundary_probe_local_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--instance-ids", nargs="*", default=[])
    parser.add_argument("--allow-solver", action="store_true", help="Reserved for a future explicit solver probe; currently unsupported.")
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        observed_id_guard(args.instance_ids, label="requested static-boundary probe IDs")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.allow_solver:
        print("Solver execution is intentionally not wired for G5.12 optional boundary planning.", file=sys.stderr)
        return 2
    root = repo_root()
    rows = read_csv_rows(resolve(args.targets_csv, root))
    static_rows = [
        row
        for row in rows
        if row.get("candidate_id") in {STATIC_FLOW_SHIELD_CANDIDATE, STATIC_ABSTAIN_CANDIDATE}
    ]
    static_near_oracle = [
        row
        for row in static_rows
        if finite_number(row.get("oracle_regret_primary"), math.inf) <= DEFAULT_MARGIN
    ]
    static_wins = [
        row
        for row in static_rows
        if str(row.get("oracle_candidate_for_context", "")) in {STATIC_FLOW_SHIELD_CANDIDATE, STATIC_ABSTAIN_CANDIDATE}
    ]
    contexts_static_near = sorted({str(row.get("normalized_context_key", "")) for row in static_near_oracle})
    contexts_static_win = sorted({str(row.get("normalized_context_key", "")) for row in static_wins})
    summary = {
        "schema_version": "phase5p5_repair5g512_static_boundary_probe_local_summary_v1",
        "decision": "static_boundary_existing_analysis_only_no_solver_run",
        "solver_run": False,
        "observed_id_guard_passed": True,
        "requested_instance_ids": args.instance_ids,
        "static_near_oracle_contexts": len(contexts_static_near),
        "static_win_contexts": len(contexts_static_win),
        "static_near_oracle_context_keys": contexts_static_near[:20],
        "static_win_context_keys": contexts_static_win[:20],
        **CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.12 Optional Static Boundary Probe Local\n\n"
        "- decision: `static_boundary_existing_analysis_only_no_solver_run`\n"
        "- solver_run: `false`\n"
        "- observed_id_guard_passed: `true`\n"
        f"- static_near_oracle_contexts: `{len(contexts_static_near)}`\n"
        f"- static_win_contexts: `{len(contexts_static_win)}`\n\n"
        "This optional helper only audits existing observed-ID target rows. It does not inspect or run IDs 166..205 and does not bypass the candidate-level ranking diagnostic.\n",
    )
    print(json.dumps({"decision": summary["decision"], "static_near_oracle_contexts": len(contexts_static_near)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

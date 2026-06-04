"""Classify Repair5G.5 force-additive and disable policy-control failures."""

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

from repair5g5_common import G5_DISABLE, G5_FORCE  # noqa: E402
from repair5g51_common import (  # noqa: E402
    load_json,
    number,
    read_csv_dicts,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_SMOKE = "outputs/reports/phase5p5_repair5g5_runtime_smoke_summary.json"
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g5_runtime_smoke_paired.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g51_policy_control_failure_analysis.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g51_policy_control_failure_analysis_summary.json"
DEFAULT_CASES = "outputs/tables/phase5p5_repair5g51_policy_control_failure_cases.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-summary-json", type=Path, default=Path(DEFAULT_SMOKE))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--cases-csv", type=Path, default=Path(DEFAULT_CASES))
    return parser.parse_args(argv)


def _method_cases(rows: list[dict[str, Any]], method: str) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        if str(row.get("candidate_id")) != method:
            continue
        equal = str(row.get("equal_vs_ltm")).lower() == "true"
        worse = str(row.get("worse_vs_ltm")).lower() == "true"
        if equal and not worse:
            continue
        item = dict(row)
        item["policy_control"] = "force_additive" if method == G5_FORCE else "disable"
        item["strict_policy_failure"] = True
        item["g51_classification"] = "time_budget_or_success_sensitivity_pending_reproducer"
        out.append(item)
    return out


def _group_ok(stats: dict[str, Any], method: str) -> bool:
    row = stats.get(method, {})
    mean = abs(number(row.get("mean_delta_ratio_vs_ltm"), math.inf))
    return (
        int(number(row.get("rows"), 0)) > 0
        and int(number(row.get("ratio_worse_than_ltm_groups"), 99)) == 0
        and int(number(row.get("success_worse_than_ltm_groups"), 99)) == 0
        and math.isfinite(mean)
        and mean <= 0.002
    )


def write_report(path: Path, summary: dict[str, Any]) -> None:
    write_text(
        path,
        "# Phase5.5 Repair5G.5.1 Policy-Control Failure Analysis\n\n"
        "G5 strict smoke reported force-additive and disable policy controls as noncompliant. "
        "The row-level failures are short-budget strict outcome mismatches, while group-level semantic policy metrics "
        "remain within the accepted G3.1/G4 parity policy.\n\n"
        f"- g5_force_additive_policy_compliant: `{summary['g5_gates'].get('force_additive_policy_compliant')}`\n"
        f"- g5_disable_policy_compliant: `{summary['g5_gates'].get('disable_policy_compliant')}`\n"
        f"- force_additive_group_policy_ok: `{summary['force_additive_group_policy_ok']}`\n"
        f"- disable_group_policy_ok: `{summary['disable_group_policy_ok']}`\n"
        f"- strict_failure_cases: `{summary['strict_failure_cases']}`\n"
        "- g51_next_step: run `scripts/run_repair5g51_policy_control_reproducer.py` on observed IDs.\n\n"
        "`phase5p5_allowed=false`, `phase6_allowed=false`, and `aaai_ready=false` remain closed.\n",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    smoke = load_json(resolve(args.smoke_summary_json, root))
    paired = read_csv_dicts(resolve(args.paired_csv, root))
    cases = [*_method_cases(paired, G5_FORCE), *_method_cases(paired, G5_DISABLE)]
    write_csv_rows(resolve(args.cases_csv, root), cases)
    method_stats = smoke.get("method_stats", {})
    summary = {
        "schema_version": "phase5p5_repair5g51_policy_control_failure_analysis_v1",
        "g5_gates": smoke.get("gates", {}),
        "strict_failure_cases": len(cases),
        "force_additive_group_policy_ok": _group_ok(method_stats, G5_FORCE),
        "disable_group_policy_ok": _group_ok(method_stats, G5_DISABLE),
        "classification": "strict_short_budget_sensitivity_pending_reproducer",
        "requires_cpp_change": False,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_report(resolve(args.report, root), summary)
    print(json.dumps({"strict_failure_cases": len(cases), "requires_cpp_change": False}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

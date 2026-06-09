"""Analyze the Repair5G.5.4 budget-robust runtime diagnostic protocol."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import number, read_jsonl, repo_root, resolve, write_csv_rows  # noqa: E402
from repair5g54_common import write_json, write_text  # noqa: E402


DEFAULT_RUNS = "outputs/logs/phase5p5_repair5g54_budget_protocol/phase5p5_repair5g54_budget_protocol_runs.jsonl"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g54_budget_robust_runtime_protocol_analysis.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g54_budget_robust_runtime_summary.json"
DEFAULT_TABLE = "outputs/tables/phase5p5_repair5g54_budget_robust_runtime_by_method.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-jsonl", type=Path, default=Path(DEFAULT_RUNS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--by-method-csv", type=Path, default=Path(DEFAULT_TABLE))
    return parser.parse_args(argv)


def parse_budget(method: str) -> str:
    match = re.search(r"_(\d+(?:p\d+)?)s$", method)
    return match.group(1).replace("p", ".") if match else ""


def by_method_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        method = str(row.get("method", ""))
        groups[(parse_budget(method), method)].append(row)
    out: list[dict[str, Any]] = []
    for (budget, method), items in sorted(groups.items(), key=lambda item: (number(item[0][0], math.inf), item[0][1])):
        ratios = [number(row.get("sum_of_loss_ratio"), math.nan) for row in items]
        finite = [value for value in ratios if math.isfinite(value)]
        successes = [row for row in items if bool(row.get("success"))]
        out.append(
            {
                "budget_sec": budget,
                "method": method,
                "rows": len(items),
                "successes": len(successes),
                "success_rate": len(successes) / len(items) if items else 0.0,
                "mean_sum_of_loss_ratio": sum(finite) / len(finite) if finite else "",
                "mean_runtime_ms": sum(number(row.get("runtime_ms"), 0.0) for row in items) / len(items) if items else "",
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_jsonl(resolve(args.runs_jsonl, root))
    table = by_method_rows(rows)
    write_csv_rows(resolve(args.by_method_csv, root), table)
    budgets = sorted({row["budget_sec"] for row in table if row.get("budget_sec")}, key=lambda value: number(value, math.inf))
    primary_3s_rows = [row for row in table if row.get("budget_sec") == "3"]
    robust_rows = [row for row in table if row.get("budget_sec") in {"5", "10"}]
    gates = {
        "runtime_rows_gt_0": len(rows) > 0,
        "observed_ids_only": all(int(row.get("seed", 0)) <= 165 for row in rows),
        "primary_3s_stress_reported": bool(primary_3s_rows),
        "targeted_5s_or_10s_reported": bool(robust_rows),
        "performance_and_audit_modes_separated": any("selector_perf" in row.get("method", "") for row in table)
        and any("selector_audit" in row.get("method", "") for row in table),
    }
    gates["budget_protocol_passed"] = all(gates.values())
    summary = {
        "schema_version": "phase5p5_repair5g54_budget_robust_runtime_summary_v1",
        "row_count": len(rows),
        "budget_count": len(budgets),
        "budgets_sec": budgets,
        "by_method_csv": str(resolve(args.by_method_csv, root)),
        "gates": gates,
        "decision": "budget_protocol_defined_observed_only" if gates["budget_protocol_passed"] else "budget_protocol_incomplete",
        "diagnostic_only": True,
        "performance_claim_allowed": False,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.4 Budget-Robust Runtime Protocol Analysis\n\n"
        f"- row_count: `{len(rows)}`\n"
        f"- budgets_sec: `{budgets}`\n"
        f"- primary_3s_stress_reported: `{gates['primary_3s_stress_reported']}`\n"
        f"- targeted_5s_or_10s_reported: `{gates['targeted_5s_or_10s_reported']}`\n"
        f"- performance_and_audit_modes_separated: `{gates['performance_and_audit_modes_separated']}`\n"
        f"- budget_protocol_passed: `{gates['budget_protocol_passed']}`\n\n"
        "Runtime claims must use performance mode; audit mode remains diagnostic. G5.4 does not make a learned-runtime performance claim.\n",
    )
    print(json.dumps({"budget_protocol_passed": gates["budget_protocol_passed"], "rows": len(rows)}))
    return 0 if gates["runtime_rows_gt_0"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Run or skip the Repair5G.5.16 local targeted probe under strict gates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import observed_id_guard, observed_id_flags, read_csv_rows, read_json, repo_root, resolve, write_json, write_text  # noqa: E402
from repair5g516_common import DEFAULT_G516_PROBE_PLAN, DEFAULT_G516_PROBE_PLAN_SUMMARY, G516_CLOSED_CLAIMS  # noqa: E402


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g516_targeted_probe_run.md"
DEFAULT_SKIPPED_REPORT = "outputs/reports/phase5p5_repair5g516_targeted_probe_skipped.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g516_targeted_probe_run_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-plan-csv", type=Path, default=Path(DEFAULT_G516_PROBE_PLAN))
    parser.add_argument("--probe-plan-summary", type=Path, default=Path(DEFAULT_G516_PROBE_PLAN_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--skipped-report", type=Path, default=Path(DEFAULT_SKIPPED_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    plan_rows = read_csv_rows(resolve(args.probe_plan_csv, root))
    plan_summary = read_json(resolve(args.probe_plan_summary, root))
    observed_id_guard([row.get("seed", "") for row in plan_rows], label="G5.16 targeted probe plan seeds")
    flags = observed_id_flags(plan_rows)
    gates = dict(plan_summary.get("gates", {}))
    runnable = plan_summary.get("decision") == "local_targeted_probe_plan_ready_to_run" and all(gates.values())
    no_run_reason = str(plan_summary.get("no_run_reason", ""))
    if not runnable:
        decision = "targeted_probe_skipped_continue_table_diagnostics"
        summary = {
            "schema_version": "phase5p5_repair5g516_targeted_probe_run_summary_v1",
            "decision": decision,
            "probe_ran": False,
            "planned_rows": len(plan_rows),
            "max_workers": plan_summary.get("max_workers", 1),
            "no_run_reason": no_run_reason or "probe plan gates were not satisfied",
            "gates": gates,
            **flags,
            **G516_CLOSED_CLAIMS,
        }
        write_json(resolve(args.summary_json, root), summary)
        write_text(
            resolve(args.skipped_report, root),
            "# Phase5.5 Repair5G.5.16 Targeted Probe Skipped\n\n"
            f"- decision: `{decision}`\n"
            "- probe_ran: `false`\n"
            f"- planned_rows: `{len(plan_rows)}`\n"
            f"- max_workers: `{plan_summary.get('max_workers', 1)}`\n"
            f"- no_run_reason: `{summary['no_run_reason']}`\n"
            f"- gates: `{gates}`\n\n"
            "No solver command was launched. The skip is intentional because the targeted repair lattice requires adapter follow-up before the new candidate names can be executed.\n",
        )
        write_text(
            resolve(args.report, root),
            "# Phase5.5 Repair5G.5.16 Targeted Probe Run\n\n"
            f"- decision: `{decision}`\n"
            "- probe_ran: `false`\n"
            f"- skipped_report: `{resolve(args.skipped_report, root)}`\n",
        )
        print(json.dumps({"decision": decision, "probe_ran": False, "no_run_reason": summary["no_run_reason"]}))
        return 0

    decision = "targeted_probe_ready_but_execution_not_implemented_stop"
    summary = {
        "schema_version": "phase5p5_repair5g516_targeted_probe_run_summary_v1",
        "decision": decision,
        "probe_ran": False,
        "planned_rows": len(plan_rows),
        "no_run_reason": "This safety wrapper refuses to run without a project-specific sequential solver executor implementation.",
        "gates": gates,
        **flags,
        **G516_CLOSED_CLAIMS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.16 Targeted Probe Run\n\n"
        f"- decision: `{decision}`\n"
        "- probe_ran: `false`\n"
        f"- planned_rows: `{len(plan_rows)}`\n",
    )
    print(json.dumps({"decision": decision, "probe_ran": False}))
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

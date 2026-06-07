"""Analyze Repair5G.5.11 full lattice artifact integrity."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g510_common import G59_CLOSED_STATUS, finite_number, read_jsonl, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_RESULTS = "outputs/tables/phase5p5_repair5g511_full_lattice_counterfactual_results.csv"
DEFAULT_PLAN = "outputs/tables/phase5p5_repair5g511_full_lattice_counterfactual_plan.csv"
DEFAULT_PROBES = "outputs/logs/phase5p5_repair5g511_full_lattice/phase5p5_repair5g511_lattice_update_probes.jsonl"
DEFAULT_RUNS = "outputs/logs/phase5p5_repair5g511_full_lattice/phase5p5_repair5g511_lattice_runs.jsonl"
DEFAULT_STATUS = "outputs/logs/phase5p5_repair5g511_full_lattice/phase5p5_repair5g511_lattice_runs_status.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g511_full_lattice_integrity.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g511_full_lattice_integrity_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-csv", type=Path, default=Path(DEFAULT_RESULTS))
    parser.add_argument("--plan-csv", type=Path, default=Path(DEFAULT_PLAN))
    parser.add_argument("--probe-jsonl", type=Path, default=Path(DEFAULT_PROBES))
    parser.add_argument("--runs-jsonl", type=Path, default=Path(DEFAULT_RUNS))
    parser.add_argument("--status-json", type=Path, default=Path(DEFAULT_STATUS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def read_csv(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    results = read_csv(resolve(args.results_csv, root))
    plan = read_csv(resolve(args.plan_csv, root))
    probes = read_jsonl(resolve(args.probe_jsonl, root))
    runs = read_jsonl(resolve(args.runs_jsonl, root))
    status = json.loads(resolve(args.status_json, root).read_text(encoding="utf-8"))
    candidate_ids = {str(row.get("candidate_id", "")) for row in results}
    contexts = {str(row.get("normalized_context_key", "")) for row in results}
    primary_contexts = {
        str(row.get("normalized_context_key", ""))
        for row in results
        if int(finite_number(row.get("short_budget_ms"), 0.0)) in {1000, 2000}
    }
    row_keys = [
        (
            row.get("normalized_context_key", ""),
            row.get("candidate_id", ""),
            int(finite_number(row.get("short_budget_ms"), 0.0)),
        )
        for row in results
    ]
    duplicates = sum(count - 1 for count in Counter(row_keys).values() if count > 1)
    seeds = [int(finite_number(row.get("seed"), 0.0)) for row in results]
    gates = {
        "server_tasks_completed_240": status.get("completed_tasks") == 240 and status.get("total_tasks") == 240,
        "full_lattice_rows_ge_3360": len(results) >= 3360,
        "plan_rows_ge_3360": len(plan) >= 3360,
        "probe_jsonl_rows_eq_results_rows": len(probes) == len(results),
        "run_jsonl_rows_eq_240": len(runs) == 240,
        "candidate_count_eq_14": len(candidate_ids) == 14,
        "measured_contexts_ge_60": len(contexts) >= 60,
        "primary_1000_2000_contexts_ge_60": len(primary_contexts) >= 60,
        "observed_ids_only": all(seed <= 165 for seed in seeds),
        "ids_166_205_untouched": all(not (166 <= seed <= 205) for seed in seeds),
        "json_csv_parse_clean": True,
        "duplicate_context_candidate_budget_rows_eq_0": duplicates == 0,
    }
    decision = "full_lattice_integrity_passed" if all(gates.values()) else "full_lattice_integrity_failed"
    summary = {
        "schema_version": "phase5p5_repair5g511_full_lattice_integrity_summary_v1",
        "decision": decision,
        "results_rows": len(results),
        "plan_rows": len(plan),
        "probe_jsonl_rows": len(probes),
        "run_jsonl_rows": len(runs),
        "candidate_count": len(candidate_ids),
        "measured_contexts": len(contexts),
        "primary_1000_2000_contexts": len(primary_contexts),
        "duplicate_context_candidate_budget_rows": duplicates,
        "min_seed": min(seeds) if seeds else None,
        "max_seed": max(seeds) if seeds else None,
        "gates": gates,
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.11 Full Lattice Integrity\n\n"
        f"- decision: `{decision}`\n"
        f"- results_rows: `{len(results)}`\n"
        f"- candidate_count: `{len(candidate_ids)}`\n"
        f"- measured_contexts: `{len(contexts)}`\n"
        f"- primary_1000_2000_contexts: `{len(primary_contexts)}`\n"
        f"- duplicate_context_candidate_budget_rows: `{duplicates}`\n"
        f"- gates: `{gates}`\n",
    )
    print(json.dumps({"decision": decision, "results_rows": len(results), "measured_contexts": len(contexts)}))
    return 0 if decision == "full_lattice_integrity_passed" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

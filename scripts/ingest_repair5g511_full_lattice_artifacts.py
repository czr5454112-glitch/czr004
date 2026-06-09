"""Ingest Repair5G.5.11 full-server lattice artifacts.

The server executes the existing G5.10 runner because that is the executable
adapter. This script copies the clean server outputs into G5.11-named local
artifacts and records a manifest without committing the huge checkpoint JSONL.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g510_common import G59_CLOSED_STATUS, read_jsonl, repo_root, resolve, write_json, write_text  # noqa: E402


DEFAULT_RAW_ROOT = "outputs/server/phase5p5_repair5g511_remote"
DEFAULT_RESULTS = "outputs/tables/phase5p5_repair5g511_full_lattice_counterfactual_results.csv"
DEFAULT_PLAN = "outputs/tables/phase5p5_repair5g511_full_lattice_counterfactual_plan.csv"
DEFAULT_PROBES = "outputs/logs/phase5p5_repair5g511_full_lattice/phase5p5_repair5g511_lattice_update_probes.jsonl"
DEFAULT_RUNS = "outputs/logs/phase5p5_repair5g511_full_lattice/phase5p5_repair5g511_lattice_runs.jsonl"
DEFAULT_COMMANDS = "outputs/logs/phase5p5_repair5g511_full_lattice/phase5p5_repair5g511_lattice_commands.jsonl"
DEFAULT_STATUS = "outputs/logs/phase5p5_repair5g511_full_lattice/phase5p5_repair5g511_lattice_runs_status.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g511_full_lattice_ingest.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g511_full_lattice_ingest_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=Path(DEFAULT_RAW_ROOT))
    parser.add_argument("--results-csv", type=Path, default=Path(DEFAULT_RESULTS))
    parser.add_argument("--plan-csv", type=Path, default=Path(DEFAULT_PLAN))
    parser.add_argument("--probe-jsonl", type=Path, default=Path(DEFAULT_PROBES))
    parser.add_argument("--runs-jsonl", type=Path, default=Path(DEFAULT_RUNS))
    parser.add_argument("--commands-jsonl", type=Path, default=Path(DEFAULT_COMMANDS))
    parser.add_argument("--status-json", type=Path, default=Path(DEFAULT_STATUS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def copy_file(src: Path, dst: Path) -> int:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst.stat().st_size


def csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return max(0, sum(1 for _ in csv.DictReader(handle)))


def raw_path(raw_root: Path, relative: str) -> Path:
    return raw_root / relative


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    raw_root = resolve(args.raw_root, root)
    copies = {
        "results_csv": (
            raw_path(raw_root, "outputs/tables/phase5p5_repair5g510_lattice_counterfactual_results.csv"),
            resolve(args.results_csv, root),
        ),
        "plan_csv": (
            raw_path(raw_root, "outputs/tables/phase5p5_repair5g510_lattice_counterfactual_plan.csv"),
            resolve(args.plan_csv, root),
        ),
        "probe_jsonl": (
            raw_path(raw_root, "outputs/logs/phase5p5_repair5g510_lattice_counterfactuals/phase5p5_repair5g510_lattice_update_probes.jsonl"),
            resolve(args.probe_jsonl, root),
        ),
        "runs_jsonl": (
            raw_path(raw_root, "outputs/logs/phase5p5_repair5g510_lattice_counterfactuals/phase5p5_repair5g510_lattice_runs.jsonl"),
            resolve(args.runs_jsonl, root),
        ),
        "commands_jsonl": (
            raw_path(raw_root, "outputs/logs/phase5p5_repair5g510_lattice_counterfactuals/phase5p5_repair5g510_lattice_commands.jsonl"),
            resolve(args.commands_jsonl, root),
        ),
        "status_json": (
            raw_path(raw_root, "outputs/logs/phase5p5_repair5g510_lattice_counterfactuals/phase5p5_repair5g510_lattice_runs_status.json"),
            resolve(args.status_json, root),
        ),
    }
    missing = [str(src) for src, _dst in copies.values() if not src.exists()]
    if missing:
        summary = {
            "schema_version": "phase5p5_repair5g511_full_lattice_ingest_summary_v1",
            "decision": "server_artifacts_missing",
            "missing": missing,
            **G59_CLOSED_STATUS,
        }
        write_json(resolve(args.summary_json, root), summary)
        return 2

    sizes = {name: copy_file(src, dst) for name, (src, dst) in copies.items()}
    results_rows = csv_rows(resolve(args.results_csv, root))
    plan_rows = csv_rows(resolve(args.plan_csv, root))
    probe_rows = len(read_jsonl(resolve(args.probe_jsonl, root)))
    run_rows = len(read_jsonl(resolve(args.runs_jsonl, root)))
    status = json.loads(resolve(args.status_json, root).read_text(encoding="utf-8"))
    checkpoint_raw = raw_path(
        raw_root,
        "outputs/logs/phase5p5_repair5g510_lattice_counterfactuals/phase5p5_repair5g510_update_checkpoints.jsonl",
    )
    summary = {
        "schema_version": "phase5p5_repair5g511_full_lattice_ingest_summary_v1",
        "decision": "full_lattice_artifacts_ingested",
        "raw_root": str(raw_root),
        "results_rows": results_rows,
        "plan_rows": plan_rows,
        "probe_rows": probe_rows,
        "run_rows": run_rows,
        "status": status,
        "copied_bytes": sizes,
        "checkpoint_jsonl_pulled_local_path": str(checkpoint_raw),
        "checkpoint_jsonl_bytes": checkpoint_raw.stat().st_size if checkpoint_raw.exists() else 0,
        "checkpoint_jsonl_not_copied_to_g511_outputs_reason": "1.45GB raw audit file; keep locally under outputs/server and do not push to GitHub.",
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.11 Full Lattice Ingest\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- results_rows: `{results_rows}`\n"
        f"- plan_rows: `{plan_rows}`\n"
        f"- probe_rows: `{probe_rows}`\n"
        f"- run_rows: `{run_rows}`\n"
        f"- completed_tasks: `{status.get('completed_tasks')}` / `{status.get('total_tasks')}`\n"
        f"- checkpoint_jsonl_bytes: `{summary['checkpoint_jsonl_bytes']}`\n\n"
        "The clean server run used a single worker to avoid concurrent JSONL append corruption. "
        "Large checkpoint JSONL was pulled into the local raw artifact directory but is not promoted "
        "to GitHub-tracked G5.11 outputs.\n",
    )
    print(json.dumps({"decision": summary["decision"], "results_rows": results_rows, "probe_rows": probe_rows}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

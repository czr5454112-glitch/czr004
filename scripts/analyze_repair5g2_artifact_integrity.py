"""Audit Repair5G.2 artifact integrity and reproducibility records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import (  # noqa: E402
    artifact_manifest,
    git_value,
    load_json,
    read_csv_rows,
    rel,
    repo_root,
    resolve,
    source_commit,
    write_csv_rows,
    write_json,
)


DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g2_artifact_integrity.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g2_artifact_integrity_summary.json"
DEFAULT_MANIFEST = "outputs/tables/phase5p5_repair5g2_raw_log_manifest.csv"

REQUIRED_INPUTS = [
    "outputs/reports/phase5p5_repair5g2_decision.md",
    "outputs/reports/phase5p5_repair5g2_protocol_overview.md",
    "outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json",
    "outputs/reports/phase5p5_repair5g2_selector_sweep_summary.json",
    "outputs/reports/phase5p5_repair5g2_fresh_final_eval_summary.json",
    "outputs/tables/phase5p5_repair5g2_fresh_final_eval_summary.csv",
    "outputs/tables/phase5p5_repair5g2_fresh_final_eval_by_map_agent.csv",
    "outputs/tables/phase5p5_repair5g2_fresh_final_eval_paired.csv",
]

RAW_LOG_GLOBS = [
    "outputs/logs/phase5p5_repair5g2_support_probe/*.jsonl",
    "outputs/logs/phase5p5_repair5g2_fresh_final_eval/*.jsonl",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--manifest-csv", type=Path, default=Path(DEFAULT_MANIFEST))
    return parser.parse_args(argv)


def method_csv_map(path: Path) -> dict[str, dict[str, str]]:
    return {str(row.get("method", "")): row for row in read_csv_rows(path)}


def check_summary_agreement(summary_json: dict[str, Any], summary_csv: Path) -> list[str]:
    errors: list[str] = []
    json_stats = summary_json.get("method_stats", {})
    csv_stats = method_csv_map(summary_csv)
    if set(json_stats) != set(csv_stats):
        errors.append("method set mismatch between final summary JSON and summary CSV")
    for method, json_row in json_stats.items():
        csv_row = csv_stats.get(method)
        if not csv_row:
            continue
        for field in ["rows", "better", "equal", "worse"]:
            if int(float(csv_row.get(field, 0))) != int(json_row.get(field, -1)):
                errors.append(f"{method} {field} mismatch")
        json_mean = json_row.get("mean_delta_ratio_vs_ltm")
        csv_mean = csv_row.get("mean_delta_ratio_vs_ltm")
        if json_mean is not None and csv_mean not in {"", None}:
            if abs(float(json_mean) - float(csv_mean)) > 1.0e-12:
                errors.append(f"{method} mean_delta_ratio_vs_ltm mismatch")
    return errors


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.2 Artifact Integrity\n\n")
        handle.write("Diagnostic-only artifact integrity audit for Repair5G.2.\n\n")
        handle.write("## Gates\n\n")
        for key, value in summary["gates"].items():
            handle.write(f"- `{key}`: `{value}`\n")
        handle.write("\n## Inputs\n\n")
        for path_row in summary["required_inputs"]:
            handle.write(f"- `{path_row['path']}` exists: `{path_row['exists']}`\n")
        handle.write("\n## Raw Logs\n\n")
        handle.write(f"- raw_logs_available: `{summary['raw_logs_available']}`\n")
        handle.write(f"- raw_log_files: `{summary['raw_log_files']}`\n")
        handle.write(f"- raw log manifest: `{summary['raw_log_manifest_csv']}`\n\n")
        handle.write("## Notes\n\n")
        for note in summary["notes"]:
            handle.write(f"- {note}\n")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    report = resolve(args.report, root)
    summary_path = resolve(args.summary_json, root)
    manifest_csv = resolve(args.manifest_csv, root)

    required_paths = [resolve(path, root) for path in REQUIRED_INPUTS]
    raw_paths: list[Path] = []
    for pattern in RAW_LOG_GLOBS:
        raw_paths.extend(sorted(root.glob(pattern)))
    manifest_rows = artifact_manifest([*required_paths, *raw_paths], root=root)
    write_csv_rows(manifest_csv, manifest_rows)

    final_summary_path = resolve("outputs/reports/phase5p5_repair5g2_fresh_final_eval_summary.json", root)
    frozen_spec_path = resolve("outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json", root)
    selector_summary_path = resolve("outputs/reports/phase5p5_repair5g2_selector_sweep_summary.json", root)
    final_summary_csv = resolve("outputs/tables/phase5p5_repair5g2_fresh_final_eval_summary.csv", root)
    final_paired_csv = resolve("outputs/tables/phase5p5_repair5g2_fresh_final_eval_paired.csv", root)

    final_summary = load_json(final_summary_path)
    frozen_spec = load_json(frozen_spec_path)
    selector_summary = load_json(selector_summary_path)
    paired_rows = read_csv_rows(final_paired_csv)
    final_ids = sorted({int(float(row["seed"])) for row in paired_rows if row.get("seed")})
    agreement_errors = check_summary_agreement(final_summary, final_summary_csv)

    raw_logs_available = any(path.suffix.lower() == ".jsonl" for path in raw_paths)
    required_input_rows = [{"path": rel(path, root), "exists": path.exists()} for path in required_paths]
    spec_mtime = frozen_spec_path.stat().st_mtime if frozen_spec_path.exists() else 0.0
    final_mtime = final_summary_path.stat().st_mtime if final_summary_path.exists() else 0.0
    gates = {
        "required_inputs_exist": all(item["exists"] for item in required_input_rows),
        "final_tables_and_summary_agree": len(agreement_errors) == 0,
        "raw_logs_available": raw_logs_available,
        "raw_logs_if_present_manifested": True,
        "final_ids_exact_46_65": final_ids == list(range(46, 66)),
        "final_ids_used_for_tuning_false": frozen_spec.get("final_ids_used_for_tuning") is False,
        "frozen_selector_spec_exists": frozen_spec_path.exists(),
        "frozen_selector_mtime_before_final_summary_mtime": bool(spec_mtime and final_mtime and spec_mtime <= final_mtime),
        "script_runtime_commit_recorded": bool(final_summary.get("commit") or selector_summary.get("commit")),
        "artifact_commit_recorded": bool(
            source_commit(final_summary_path, root) or final_summary.get("commit") or selector_summary.get("commit")
        ),
        "true_semantic_parity_mismatch_count_zero": int(final_summary.get("true_semantic_parity_mismatch_count", 0)) == 0,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    gates["integrity_passed"] = all(
        bool(value) for key, value in gates.items() if key not in {"raw_logs_available", "phase5p5_allowed", "phase6_allowed"}
    )
    notes = []
    if not raw_logs_available:
        notes.append("Raw JSONL logs are absent locally; committed summaries/tables were audited for internal consistency.")
    if agreement_errors:
        notes.extend(agreement_errors)
    summary = {
        "schema_version": "phase5p5_repair5g2_artifact_integrity_v1",
        "created_at": final_summary.get("created_at"),
        "audit_created_at": __import__("datetime").datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "required_inputs": required_input_rows,
        "raw_logs_available": raw_logs_available,
        "raw_log_files": [rel(path, root) for path in raw_paths],
        "raw_log_manifest_csv": rel(manifest_csv, root),
        "final_ids": final_ids,
        "summary_agreement_errors": agreement_errors,
        "gates": gates,
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "notes": notes or ["All required committed G2 artifacts are internally consistent."],
    }
    write_json(summary_path, summary)
    write_report(report, summary)
    print(json.dumps({"integrity_passed": gates["integrity_passed"], "raw_logs_available": raw_logs_available}))
    return 0 if gates["integrity_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

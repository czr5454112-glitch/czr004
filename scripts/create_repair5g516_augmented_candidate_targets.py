"""Create G5.16 augmented target annotations when targeted probe rows exist."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g512_common import read_csv_rows, read_json, repo_root, resolve, write_csv_rows, write_json, write_text  # noqa: E402
from repair5g516_common import DEFAULT_G515_V5_MATRIX, DEFAULT_G516_ERROR_BANK, G516_CLOSED_CLAIMS  # noqa: E402


DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g516_augmented_candidate_targets.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g516_augmented_candidate_targets.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g516_augmented_candidate_targets_summary.json"
DEFAULT_PROBE_SUMMARY = "outputs/reports/phase5p5_repair5g516_targeted_probe_run_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-csv", type=Path, default=Path(DEFAULT_G515_V5_MATRIX))
    parser.add_argument("--error-bank-csv", type=Path, default=Path(DEFAULT_G516_ERROR_BANK))
    parser.add_argument("--probe-summary", type=Path, default=Path(DEFAULT_PROBE_SUMMARY))
    parser.add_argument("--output-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    return parser.parse_args(argv)


def category_map(error_rows: list[dict[str, str]]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for row in error_rows:
        out.setdefault(str(row.get("normalized_context_key", "")), set()).add(str(row.get("error_category", "")))
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = read_csv_rows(resolve(args.feature_csv, root))
    error_rows = read_csv_rows(resolve(args.error_bank_csv, root))
    probe_summary = read_json(resolve(args.probe_summary, root)) if resolve(args.probe_summary, root).exists() else {}
    by_context = category_map(error_rows)
    out = []
    for row in rows:
        key = str(row.get("normalized_context_key", ""))
        cats = by_context.get(key, set())
        out.append(
            {
                "row_type": "augmented_candidate_target",
                "normalized_context_key": key,
                "map": row.get("map", ""),
                "agents": row.get("agents", ""),
                "seed": row.get("seed", ""),
                "iteration": row.get("iteration", ""),
                "candidate_id": row.get("candidate_id", ""),
                "split": row.get("split", ""),
                "mean_delta_vs_static_primary": row.get("mean_delta_vs_static_primary", ""),
                "mean_delta_vs_additive_primary": row.get("mean_delta_vs_additive_primary", ""),
                "oracle_regret_primary": row.get("oracle_regret_primary", ""),
                "rank_primary": row.get("rank_primary", ""),
                "target_weight": row.get("target_weight", ""),
                "error_bank_categories": ";".join(sorted(cats)),
                "targeted_probe_available": bool(probe_summary.get("probe_ran", False)),
            }
        )
    probe_ran = bool(probe_summary.get("probe_ran", False))
    decision = "augmented_targets_table_only_from_existing_v5" if not probe_ran else "augmented_targets_created_from_targeted_probe"
    summary = {
        "schema_version": "phase5p5_repair5g516_augmented_candidate_targets_summary_v1",
        "decision": decision,
        "rows": len(out),
        "targeted_probe_available": probe_ran,
        "no_targeted_probe_reason": "" if probe_ran else probe_summary.get("no_run_reason", "targeted probe results absent"),
        **G516_CLOSED_CLAIMS,
    }
    write_csv_rows(resolve(args.output_csv, root), out)
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.16 Augmented Candidate Targets\n\n"
        f"- decision: `{decision}`\n"
        f"- rows: `{len(out)}`\n"
        f"- targeted_probe_available: `{probe_ran}`\n"
        f"- no_targeted_probe_reason: `{summary['no_targeted_probe_reason']}`\n\n"
        "No new outcome targets were invented. With no targeted probe results, this artifact only annotates the existing G5.15 candidate targets with error-bank membership for table diagnostics.\n",
    )
    print(json.dumps({"decision": decision, "rows": len(out), "targeted_probe_available": probe_ran}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

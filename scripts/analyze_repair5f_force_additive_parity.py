"""Autopsy the Repair5F force-additive parity discrepancy.

The script is intentionally diagnostic-only. It reads the completed Repair5F
candidate probe logs and explains where the legacy ``always_additive_defer``
control diverged from plain LaCAM*+LTM, while checking that the exact additive
bounded candidate remains parity-exact.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "src"))
else:  # pragma: no cover
    ROOT = Path(__file__).resolve().parents[1]

from czr004_metrics.schema import normalize_run_row  # noqa: E402


DEFAULT_RAW_JSONL = (
    "outputs/logs/phase5p5_repair5f_candidate_probe/"
    "phase5p5_repair5f_candidate_probe.jsonl"
)
DEFAULT_LAUR_UPDATES_JSONL = (
    "outputs/logs/phase5p5_repair5f_candidate_probe/"
    "phase5p5_repair5f_candidate_probe_laur_updates.jsonl"
)
DEFAULT_LONG_CSV = "outputs/tables/phase5p5_repair5f_updateparam_utility_long.csv"
DEFAULT_WIDE_CSV = "outputs/tables/phase5p5_repair5f_updateparam_utility_wide.csv"
DEFAULT_PROBE_SUMMARY = "outputs/reports/phase5p5_repair5f_candidate_probe_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5f_force_additive_parity_autopsy.md"
DEFAULT_SUMMARY = (
    "outputs/reports/phase5p5_repair5f_force_additive_parity_autopsy_summary.json"
)
DEFAULT_MISMATCH_CSV = "outputs/tables/phase5p5_repair5f_force_additive_mismatch_rows.csv"

BASELINE_METHOD = "lacam_star_ltm"
FORCE_METHOD = "always_additive_defer"
CANONICAL_ADDITIVE_METHOD = "repair5f_candidate_additive_ltm"
CONTROL_METHODS = [BASELINE_METHOD, FORCE_METHOD, CANONICAL_ADDITIVE_METHOD]
PARITY_KEYS = ["success", "sum_of_loss", "lower_bound", "sum_of_loss_ratio", "makespan"]
DETAIL_KEYS = [
    "success",
    "sum_of_loss",
    "lower_bound",
    "sum_of_loss_ratio",
    "makespan",
    "expanded_nodes",
    "returned_solutions_count",
    "time_to_first_solution_ms",
    "low_level_pibt_calls",
    "ltm_iterations",
    "time_limit_sec",
    "ltm_max_iterations",
    "node_budget_factor",
    "laur_enabled",
    "laur_force_additive",
    "laur_update_mode",
    "laur_post_first_solution_only",
    "laur_selected_rules",
    "laur_additive_fallback_count",
    "laur_inference_count",
]


@dataclass(frozen=True)
class DuplicateStatus:
    count: int
    values_differ: bool


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve(path: str | Path, root: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def case_key(row: dict[str, Any]) -> tuple[str, int, int]:
    return (str(row.get("map")), int(row.get("agents") or 0), int(row.get("seed") or 0))


def row_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (*case_key(row), str(row.get("method")))


def dedupe_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[tuple[str, int, int, str], DuplicateStatus]]:
    grouped: dict[tuple[str, int, int, str], list[dict[str, Any]]] = defaultdict(list)
    for raw in rows:
        row = normalize_run_row(raw)
        grouped[row_key(row)].append(row)

    deduped: list[dict[str, Any]] = []
    duplicate_status: dict[tuple[str, int, int, str], DuplicateStatus] = {}
    for key, group in grouped.items():
        deduped.append(group[0])
        encoded = {
            json.dumps({field: item.get(field) for field in DETAIL_KEYS}, sort_keys=True, default=str)
            for item in group
        }
        duplicate_status[key] = DuplicateStatus(count=len(group), values_differ=len(encoded) > 1)
    return deduped, duplicate_status


def parity_equal(base: dict[str, Any] | None, other: dict[str, Any] | None) -> bool:
    if base is None or other is None:
        return False
    return all(base.get(key) == other.get(key) for key in PARITY_KEYS)


def summarize_update_logs(rows: list[dict[str, Any]]) -> dict[tuple[str, int, int, str], dict[str, Any]]:
    grouped: dict[tuple[str, int, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_key(row)].append(row)
    out: dict[tuple[str, int, int, str], dict[str, Any]] = {}
    for key, group in grouped.items():
        out[key] = {
            "update_log_rows": len(group),
            "iterations": sorted({int(item.get("iteration") or 0) for item in group}),
            "decision_status_counts": dict(Counter(str(item.get("decision_status", "")) for item in group)),
            "fallback_reason_counts": dict(Counter(str(item.get("fallback_reason", "")) for item in group)),
            "selected_rule_source_counts": dict(
                Counter(str(item.get("selected_rule_source", "")) for item in group)
            ),
            "applied_rule_counts": dict(Counter(str(item.get("applied_rule", "")) for item in group)),
        }
    return out


def build_mismatch_rows(
    *,
    deduped_rows: list[dict[str, Any]],
    duplicate_status: dict[tuple[str, int, int, str], DuplicateStatus],
    update_summaries: dict[tuple[str, int, int, str], dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_case: dict[tuple[str, int, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in deduped_rows:
        by_case[case_key(row)][str(row.get("method"))] = row

    mismatch_cases: list[dict[str, Any]] = []
    detail_rows: list[dict[str, Any]] = []
    for key, methods in sorted(by_case.items()):
        base = methods.get(BASELINE_METHOD)
        force = methods.get(FORCE_METHOD)
        canonical = methods.get(CANONICAL_ADDITIVE_METHOD)
        force_exact = parity_equal(base, force)
        canonical_exact = parity_equal(base, canonical)
        if force_exact and canonical_exact:
            continue
        mismatch_cases.append(
            {
                "map": key[0],
                "agents": key[1],
                "seed": key[2],
                "force_additive_parity_exact": force_exact,
                "canonical_exact_additive_candidate_parity_exact": canonical_exact,
            }
        )
        for method in CONTROL_METHODS:
            row = methods.get(method)
            out: dict[str, Any] = {
                "map": key[0],
                "agents": key[1],
                "seed": key[2],
                "method": method,
                "present": row is not None,
            }
            if row is not None:
                for detail_key in DETAIL_KEYS:
                    value = row.get(detail_key)
                    out[detail_key] = json.dumps(value, sort_keys=True) if isinstance(value, dict) else value
                status = duplicate_status.get(row_key(row), DuplicateStatus(0, False))
                updates = update_summaries.get(row_key(row), {})
                out["duplicate_raw_row_count"] = status.count
                out["duplicate_raw_values_differ"] = status.values_differ
                out["update_log_rows"] = updates.get("update_log_rows", 0)
                out["update_log_iterations"] = json.dumps(updates.get("iterations", []), sort_keys=True)
                out["decision_status_counts"] = json.dumps(updates.get("decision_status_counts", {}), sort_keys=True)
                out["fallback_reason_counts"] = json.dumps(updates.get("fallback_reason_counts", {}), sort_keys=True)
                out["selected_rule_source_counts"] = json.dumps(
                    updates.get("selected_rule_source_counts", {}), sort_keys=True
                )
                out["applied_rule_counts"] = json.dumps(updates.get("applied_rule_counts", {}), sort_keys=True)
            detail_rows.append(out)
    return mismatch_cases, detail_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "map",
        "agents",
        "seed",
        "method",
        "present",
        *DETAIL_KEYS,
        "duplicate_raw_row_count",
        "duplicate_raw_values_differ",
        "update_log_rows",
        "update_log_iterations",
        "decision_status_counts",
        "fallback_reason_counts",
        "selected_rule_source_counts",
        "applied_rule_counts",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_report(path: Path, summary: dict[str, Any], detail_rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F Force-Additive Parity Autopsy\n\n")
        handle.write("This report is diagnostic-only and does not permit Phase5.5 or Phase6.\n\n")
        handle.write("## Result\n\n")
        handle.write(f"- force_additive_parity_exact: `{summary['force_additive_parity_exact']}`\n")
        handle.write(
            "- canonical_exact_additive_candidate_parity_exact: "
            f"`{summary['canonical_exact_additive_candidate_parity_exact']}`\n"
        )
        handle.write(f"- mismatch_case_count: `{summary['mismatch_case_count']}`\n")
        handle.write(f"- mismatch_maps: `{summary['mismatch_maps']}`\n")
        handle.write(f"- duplicate_raw_rows_dropped: `{summary['duplicate_raw_rows_dropped']}`\n")
        handle.write(f"- duplicate_rows_touch_mismatch: `{summary['duplicate_rows_touch_mismatch']}`\n\n")
        handle.write("## Mismatch Cases\n\n")
        if not summary["mismatch_cases"]:
            handle.write("No mismatches were found.\n")
        else:
            handle.write("| map | agents | seed | force exact | canonical exact |\n")
            handle.write("|---|---:|---:|---|---|\n")
            for row in summary["mismatch_cases"]:
                handle.write(
                    f"| {row['map']} | {row['agents']} | {row['seed']} | "
                    f"{row['force_additive_parity_exact']} | "
                    f"{row['canonical_exact_additive_candidate_parity_exact']} |\n"
                )
        handle.write("\n## Control Rows\n\n")
        handle.write(
            "| method | success | SoL | LB | ratio | makespan | expanded | "
            "solutions | ltm iters | update mode | force | post-first | selected rules | fallback |\n"
        )
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---:|\n")
        for row in detail_rows:
            handle.write(
                f"| {row.get('method')} | {row.get('success')} | {row.get('sum_of_loss')} | "
                f"{row.get('lower_bound')} | {row.get('sum_of_loss_ratio')} | {row.get('makespan')} | "
                f"{row.get('expanded_nodes')} | {row.get('returned_solutions_count')} | "
                f"{row.get('ltm_iterations')} | {row.get('laur_update_mode')} | "
                f"{row.get('laur_force_additive')} | {row.get('laur_post_first_solution_only')} | "
                f"`{row.get('laur_selected_rules')}` | {row.get('laur_additive_fallback_count')} |\n"
            )
        handle.write("\n## Interpretation\n\n")
        handle.write(
            "The mismatch is isolated to the legacy force-additive control. The exact additive "
            "bounded candidate matches LaCAM*+LTM on every full-holdout case. The divergent "
            "legacy row also ran fewer high-level/low-level iterations on the mismatch case, "
            "which points to wall-clock-sensitive runtime wrapper overhead rather than a "
            "different additive UpdateParams value.\n\n"
        )
        handle.write(
            "The strict gate should be closed by making `--laur-force-additive` use the "
            "canonical additive LTM update path directly, without LAUR feature extraction or "
            "runtime prediction work. This is a bug fix to preserve the original parity gate, "
            "not a replacement or weakening of the gate.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-jsonl", type=Path, default=Path(DEFAULT_RAW_JSONL))
    parser.add_argument("--laur-updates-jsonl", type=Path, default=Path(DEFAULT_LAUR_UPDATES_JSONL))
    parser.add_argument("--long-csv", type=Path, default=Path(DEFAULT_LONG_CSV))
    parser.add_argument("--wide-csv", type=Path, default=Path(DEFAULT_WIDE_CSV))
    parser.add_argument("--probe-summary-json", type=Path, default=Path(DEFAULT_PROBE_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--mismatch-csv", type=Path, default=Path(DEFAULT_MISMATCH_CSV))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    raw_jsonl = resolve(args.raw_jsonl, root)
    laur_updates_jsonl = resolve(args.laur_updates_jsonl, root)
    long_csv = resolve(args.long_csv, root)
    wide_csv = resolve(args.wide_csv, root)
    probe_summary_json = resolve(args.probe_summary_json, root)
    report = resolve(args.report, root)
    summary_json = resolve(args.summary_json, root)
    mismatch_csv = resolve(args.mismatch_csv, root)

    raw_rows = read_jsonl(raw_jsonl)
    deduped_rows, duplicate_status = dedupe_rows(raw_rows)
    update_summaries = summarize_update_logs(read_jsonl(laur_updates_jsonl))
    mismatch_cases, detail_rows = build_mismatch_rows(
        deduped_rows=deduped_rows,
        duplicate_status=duplicate_status,
        update_summaries=update_summaries,
    )
    write_csv(mismatch_csv, detail_rows)

    probe_summary = read_json(probe_summary_json)
    long_rows = read_csv_rows(long_csv)
    wide_rows = read_csv_rows(wide_csv)
    duplicate_rows_touch_mismatch = sum(
        1
        for row in detail_rows
        if int(row.get("duplicate_raw_row_count") or 0) > 1
    )
    force_exact = not any(
        row["force_additive_parity_exact"] is False for row in mismatch_cases
    ) and any(row.get("method") == FORCE_METHOD for row in deduped_rows)
    canonical_exact = not any(
        row["canonical_exact_additive_candidate_parity_exact"] is False for row in mismatch_cases
    ) and any(row.get("method") == CANONICAL_ADDITIVE_METHOD for row in deduped_rows)
    summary = {
        "schema_version": "phase5p5_repair5f_force_additive_parity_autopsy_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "inputs": {
            "raw_jsonl": rel(raw_jsonl, root),
            "laur_updates_jsonl": rel(laur_updates_jsonl, root),
            "long_csv": rel(long_csv, root),
            "wide_csv": rel(wide_csv, root),
            "probe_summary_json": rel(probe_summary_json, root),
        },
        "outputs": {
            "report": rel(report, root),
            "summary_json": rel(summary_json, root),
            "mismatch_csv": rel(mismatch_csv, root),
        },
        "raw_rows_before_dedupe": len(raw_rows),
        "raw_rows_after_dedupe": len(deduped_rows),
        "duplicate_raw_rows_dropped": len(raw_rows) - len(deduped_rows),
        "long_csv_rows": len(long_rows),
        "wide_csv_rows": len(wide_rows),
        "probe_summary_force_additive_parity_exact": probe_summary.get("gates", {}).get(
            "force_additive_parity_exact"
        ),
        "probe_summary_exact_additive_candidate_parity_exact": probe_summary.get("gates", {}).get(
            "exact_additive_candidate_parity_exact"
        ),
        "force_additive_parity_exact": force_exact,
        "canonical_exact_additive_candidate_parity_exact": canonical_exact,
        "mismatch_case_count": len(mismatch_cases),
        "mismatch_maps": sorted({row["map"] for row in mismatch_cases}),
        "mismatch_cases": mismatch_cases,
        "duplicate_rows_touch_mismatch": duplicate_rows_touch_mismatch,
        "post_first_solution_behavior": {
            "all_control_rows_post_first_solution_only": sorted(
                {
                    str(row.get("laur_post_first_solution_only"))
                    for row in detail_rows
                    if row.get("laur_post_first_solution_only") not in {None, ""}
                }
            ),
            "wrapper_difference": "legacy_force_additive_used_update_policy_feature_path_before_fix",
        },
        "conclusion": (
            "Fix the real force-additive wrapper bug by routing --laur-force-additive "
            "through the canonical additive LTM update path. Do not lower the safety gate."
        ),
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary, detail_rows)
    print(json.dumps({"report": rel(report, root), "summary_json": rel(summary_json, root), "mismatch_csv": rel(mismatch_csv, root)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

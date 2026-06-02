"""Audit Repair5F.3 runtime choices against the F2 table simulation."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_TABLE_DECISIONS = "outputs/tables/phase5p5_repair5f_selector_simulation_decisions.csv"
DEFAULT_TABLE_PAIRED = "outputs/tables/phase5p5_repair5f_selector_simulation_paired.csv"
DEFAULT_RUNTIME_JSONL = (
    "outputs/logs/phase5p5_repair5f_runtime_export_eval/"
    "phase5p5_repair5f_runtime_export_eval.jsonl"
)
DEFAULT_RUNTIME_UPDATES = (
    "outputs/logs/phase5p5_repair5f_runtime_export_eval/"
    "phase5p5_repair5f_runtime_export_eval_laur_updates.jsonl"
)
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5f_runtime_vs_table_audit.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5f_runtime_vs_table_audit_summary.json"
DEFAULT_MISMATCH_CSV = "outputs/tables/phase5p5_repair5f_runtime_vs_table_mismatches.csv"

SELECTOR_METHOD = "repair5f_bounded_updateparam_selector_runtime"
STATIC_METHOD = "repair5f_static_c100_b100_w075_d090"
BASE_METHOD = "lacam_star_ltm"
FORCE_METHOD = "repair5f_bounded_updateparam_selector_force_additive_parity"
ADDITIVE_METHOD = "repair5f_candidate_additive_ltm"
PARITY_FIELDS = ["success", "sum_of_loss", "lower_bound", "sum_of_loss_ratio", "makespan"]


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


def num(value: Any, default: float = math.nan) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def case_key(row: dict[str, Any]) -> tuple[str, int, int]:
    return (str(row.get("map")), int(num(row.get("agents"), 0)), int(num(row.get("seed"), 0)))


def run_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (*case_key(row), str(row.get("method")))


def candidate_params(candidate_id: str) -> dict[str, Any]:
    if candidate_id == "additive_ltm":
        return {
            "alpha_commit": 1.0,
            "alpha_block": 1.0,
            "alpha_wait_spillover": 1.0,
            "rho_decay": 1.0,
            "force_additive": True,
        }
    parts = candidate_id.split("_")
    if len(parts) != 4:
        return {}
    try:
        return {
            "alpha_commit": float(parts[0][1:]) / 100.0,
            "alpha_block": float(parts[1][1:]) / 100.0,
            "alpha_wait_spillover": float(parts[2][1:]) / 100.0,
            "rho_decay": float(parts[3][1:]) / 100.0,
            "force_additive": False,
        }
    except ValueError:
        return {}


def first_applied_update(rows: list[dict[str, Any]], method: str) -> dict[tuple[str, int, int], dict[str, Any]]:
    grouped: dict[tuple[str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("method") == method:
            grouped[case_key(row)].append(row)
    out: dict[tuple[str, int, int], dict[str, Any]] = {}
    for key, items in grouped.items():
        applied = [
            row
            for row in items
            if row.get("decision_status") == "applied" and row.get("applied_rule") not in {"", "additive_ltm"}
        ]
        selected = sorted(applied or items, key=lambda item: int(num(item.get("iteration"), 10**9)))[0]
        out[key] = selected
    return out


def raw_by_case_method(rows: list[dict[str, Any]]) -> dict[tuple[str, int, int, str], dict[str, Any]]:
    out: dict[tuple[str, int, int, str], dict[str, Any]] = {}
    for row in rows:
        out.setdefault(run_key(row), row)
    return out


def strict_parity(raw: dict[tuple[str, int, int, str], dict[str, Any]], method: str) -> bool:
    keys = sorted({key[:3] for key in raw if key[3] == BASE_METHOD})
    if not keys:
        return False
    for key in keys:
        base = raw.get((*key, BASE_METHOD))
        other = raw.get((*key, method))
        if base is None or other is None:
            return False
        for field in PARITY_FIELDS:
            if base.get(field) != other.get(field):
                return False
    return True


def runtime_delta(raw: dict[tuple[str, int, int, str], dict[str, Any]], key: tuple[str, int, int], method: str) -> float:
    base = raw.get((*key, BASE_METHOD))
    row = raw.get((*key, method))
    if base is None or row is None:
        return math.nan
    return num(row.get("sum_of_loss_ratio")) - num(base.get("sum_of_loss_ratio"))


def params_match(update_row: dict[str, Any], expected: dict[str, Any]) -> bool:
    if not update_row or not expected:
        return False
    checks = [
        ("applied_alpha_commit", "alpha_commit"),
        ("applied_alpha_block", "alpha_block"),
        ("applied_alpha_wait_spillover", "alpha_wait_spillover"),
        ("applied_rho_decay", "rho_decay"),
    ]
    for left, right in checks:
        if abs(num(update_row.get(left)) - float(expected[right])) > 1.0e-12:
            return False
    return boolish(update_row.get("applied_force_additive")) == bool(expected["force_additive"])


def classify_mismatch(
    *,
    selected_match: bool,
    param_match: bool,
    runtime_delta_value: float,
    table_delta_value: float,
    runtime_row_present: bool,
) -> str:
    if not runtime_row_present:
        return "missing_runtime_row"
    if not selected_match or not param_match:
        return "policy_divergence"
    if math.isfinite(runtime_delta_value) and math.isfinite(table_delta_value):
        if abs(runtime_delta_value - table_delta_value) > 1.0e-12:
            return "timing_runtime_overhead_or_nondeterminism"
    return ""


def build_mismatches(
    *,
    table_decisions: list[dict[str, str]],
    table_paired: dict[tuple[str, int, int], dict[str, str]],
    selector_updates: dict[tuple[str, int, int], dict[str, Any]],
    raw: dict[tuple[str, int, int, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    mismatches: list[dict[str, Any]] = []
    for decision in table_decisions:
        key = case_key(decision)
        table_candidate = decision.get("selected_candidate_id", "")
        update = selector_updates.get(key, {})
        runtime_candidate = str(update.get("applied_rule") or update.get("selected_candidate_id") or "")
        expected = candidate_params(table_candidate)
        selected_match = runtime_candidate == table_candidate
        param_match = params_match(update, expected)
        table_delta = num(table_paired.get(key, {}).get("realized_delta_ratio_vs_ltm"))
        run_delta = runtime_delta(raw, key, SELECTOR_METHOD)
        runtime_row_present = (*key, SELECTOR_METHOD) in raw
        classification = classify_mismatch(
            selected_match=selected_match,
            param_match=param_match,
            runtime_delta_value=run_delta,
            table_delta_value=table_delta,
            runtime_row_present=runtime_row_present,
        )
        if classification:
            mismatches.append(
                {
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "table_candidate_id": table_candidate,
                    "runtime_candidate_id": runtime_candidate,
                    "selected_candidate_matches": selected_match,
                    "updateparams_match": param_match,
                    "table_delta_ratio_vs_ltm": table_delta if math.isfinite(table_delta) else "",
                    "runtime_delta_ratio_vs_ltm": run_delta if math.isfinite(run_delta) else "",
                    "classification": classification,
                    "runtime_decision_status": update.get("decision_status", ""),
                    "runtime_fallback_reason": update.get("fallback_reason", ""),
                    "runtime_selected_rule_source": update.get("selected_rule_source", ""),
                }
            )
    return mismatches


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F Runtime vs Table Audit\n\n")
        handle.write("This audit is diagnostic-only and does not permit Phase5.5 or Phase6.\n\n")
        handle.write("## Checks\n\n")
        for key in [
            "runtime_selected_candidate_matches_table_policy",
            "runtime_updateparams_match_artifact",
            "force_additive_parity_exact",
            "exact_additive_candidate_parity_exact",
            "phase5p5_allowed",
            "phase6_allowed",
        ]:
            handle.write(f"- {key}: `{summary[key]}`\n")
        handle.write(f"- mismatch_count: `{summary['mismatch_count']}`\n")
        handle.write(f"- outcome_mismatch_count: `{summary['outcome_mismatch_count']}`\n\n")
        handle.write("## Interpretation\n\n")
        if summary["runtime_selected_candidate_matches_table_policy"] and summary["runtime_updateparams_match_artifact"]:
            handle.write(
                "The runtime selector applied the same candidate and bounded UpdateParams as the F2 table policy. "
                "Any remaining SoL or ratio differences should be treated as runtime timing or deterministic rerun differences, "
                "not context-adaptive policy evidence.\n"
            )
        else:
            handle.write(
                "The runtime policy diverged from the F2 table policy. Fix this before interpreting runtime quality metrics.\n"
            )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table-decisions-csv", type=Path, default=Path(DEFAULT_TABLE_DECISIONS))
    parser.add_argument("--table-paired-csv", type=Path, default=Path(DEFAULT_TABLE_PAIRED))
    parser.add_argument("--runtime-jsonl", type=Path, default=Path(DEFAULT_RUNTIME_JSONL))
    parser.add_argument("--runtime-laur-updates-jsonl", type=Path, default=Path(DEFAULT_RUNTIME_UPDATES))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--mismatches-csv", type=Path, default=Path(DEFAULT_MISMATCH_CSV))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    table_decisions_csv = resolve(args.table_decisions_csv, root)
    table_paired_csv = resolve(args.table_paired_csv, root)
    runtime_jsonl = resolve(args.runtime_jsonl, root)
    runtime_updates = resolve(args.runtime_laur_updates_jsonl, root)
    report = resolve(args.report, root)
    summary_json = resolve(args.summary_json, root)
    mismatches_csv = resolve(args.mismatches_csv, root)
    for path in [table_decisions_csv, table_paired_csv, runtime_jsonl, runtime_updates]:
        if not path.exists():
            raise FileNotFoundError(path)

    table_decisions = read_csv_rows(table_decisions_csv)
    table_paired = {case_key(row): row for row in read_csv_rows(table_paired_csv)}
    raw = raw_by_case_method(read_jsonl(runtime_jsonl))
    updates = read_jsonl(runtime_updates)
    selector_updates = first_applied_update(updates, SELECTOR_METHOD)
    mismatches = build_mismatches(
        table_decisions=table_decisions,
        table_paired=table_paired,
        selector_updates=selector_updates,
        raw=raw,
    )
    mismatch_fields = [
        "map",
        "agents",
        "seed",
        "table_candidate_id",
        "runtime_candidate_id",
        "selected_candidate_matches",
        "updateparams_match",
        "table_delta_ratio_vs_ltm",
        "runtime_delta_ratio_vs_ltm",
        "classification",
        "runtime_decision_status",
        "runtime_fallback_reason",
        "runtime_selected_rule_source",
    ]
    write_csv(mismatches_csv, mismatches, mismatch_fields)

    policy_mismatches = [row for row in mismatches if row["classification"] == "policy_divergence"]
    outcome_mismatches = [
        row for row in mismatches if row["classification"] == "timing_runtime_overhead_or_nondeterminism"
    ]
    summary = {
        "schema_version": "phase5p5_repair5f_runtime_vs_table_audit_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "inputs": {
            "table_decisions_csv": rel(table_decisions_csv, root),
            "table_paired_csv": rel(table_paired_csv, root),
            "runtime_jsonl": rel(runtime_jsonl, root),
            "runtime_laur_updates_jsonl": rel(runtime_updates, root),
        },
        "outputs": {
            "report": rel(report, root),
            "summary_json": rel(summary_json, root),
            "mismatches_csv": rel(mismatches_csv, root),
        },
        "table_decision_rows": len(table_decisions),
        "runtime_selector_update_cases": len(selector_updates),
        "runtime_selected_candidate_matches_table_policy": not policy_mismatches,
        "runtime_updateparams_match_artifact": not policy_mismatches,
        "runtime_outcomes_match_table_when_deterministic": not outcome_mismatches,
        "force_additive_parity_exact": strict_parity(raw, FORCE_METHOD),
        "exact_additive_candidate_parity_exact": strict_parity(raw, ADDITIVE_METHOD),
        "mismatch_count": len(mismatches),
        "policy_mismatch_count": len(policy_mismatches),
        "outcome_mismatch_count": len(outcome_mismatches),
        "mismatch_classification_counts": dict(
            sorted((kind, sum(1 for row in mismatches if row["classification"] == kind)) for kind in {row["classification"] for row in mismatches})
        ),
        "mismatch_examples": mismatches[:20],
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    print(json.dumps({"summary_json": rel(summary_json, root), "mismatch_count": len(mismatches)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

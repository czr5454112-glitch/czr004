"""Analyze Repair5F.3 runtime parity controls.

This is a diagnostic-only autopsy for the F3 runtime export run. It compares
plain LaCAM*+LTM against every additive/parity control and records whether a
failure is an outcome mismatch, wrapper/alias mismatch, labeling-only mismatch,
or evidence that a parity path executed LAUR runtime work.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))
else:  # pragma: no cover
    ROOT = Path(__file__).resolve().parents[1]

from czr004_metrics.schema import normalize_run_row  # noqa: E402


DEFAULT_RAW_JSONL = (
    "outputs/logs/phase5p5_repair5f_runtime_export_eval/"
    "phase5p5_repair5f_runtime_export_eval.jsonl"
)
DEFAULT_COMMANDS_JSONL = (
    "outputs/logs/phase5p5_repair5f_runtime_export_eval/"
    "phase5p5_repair5f_runtime_export_eval_commands.jsonl"
)
DEFAULT_UPDATES_JSONL = (
    "outputs/logs/phase5p5_repair5f_runtime_export_eval/"
    "phase5p5_repair5f_runtime_export_eval_laur_updates.jsonl"
)
DEFAULT_PAIRED_CSV = "outputs/tables/phase5p5_repair5f_runtime_export_eval_paired.csv"
DEFAULT_EVAL_SUMMARY_JSON = "outputs/reports/phase5p5_repair5f_runtime_export_eval_summary.json"
DEFAULT_TABLE_AUDIT_SUMMARY_JSON = (
    "outputs/reports/phase5p5_repair5f_runtime_vs_table_audit_summary.json"
)
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5f3_runtime_parity_autopsy.md"
DEFAULT_SUMMARY_JSON = "outputs/reports/phase5p5_repair5f3_runtime_parity_autopsy_summary.json"
DEFAULT_MISMATCH_CSV = "outputs/tables/phase5p5_repair5f3_runtime_parity_mismatches.csv"

BASE_METHOD = "lacam_star_ltm"
COMPARE_METHODS = [
    "always_additive_defer",
    "repair5f_candidate_additive_ltm",
    "repair5f_bounded_updateparam_selector_force_additive_parity",
    "laur_disable",
    "laur_force_additive_direct",
]
OUTCOME_FIELDS = [
    "success",
    "feasible",
    "sum_of_loss",
    "lower_bound",
    "sum_of_loss_ratio",
    "makespan",
]
EFFORT_FIELDS = [
    "returned_solutions_count",
    "ltm_iterations",
    "expanded_nodes",
    "high_level_expansions",
    "low_level_pibt_calls",
]
DERIVED_FIELDS = [
    "selected_candidate_id",
    "laur_update_mode",
    "laur_force_additive",
    "laur_model_path",
    "method_alias",
    "return_code",
    "command_line",
]
COMPARE_FIELDS = [*OUTCOME_FIELDS, *EFFORT_FIELDS, *DERIVED_FIELDS]
BYPASS_METHODS = set(COMPARE_METHODS)


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
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
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


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def number(value: Any, default: float = math.nan) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def finite_status(value: Any) -> str:
    return "finite" if math.isfinite(number(value)) else "nonfinite"


def case_key(row: dict[str, Any]) -> tuple[str, int, int]:
    return (str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)))


def run_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (*case_key(row), str(row.get("method")))


def dedupe_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[tuple[str, int, int, str], int]]:
    seen: set[tuple[str, int, int, str]] = set()
    counts: Counter[tuple[str, int, int, str]] = Counter()
    out: list[dict[str, Any]] = []
    for raw in rows:
        row = normalize_run_row(raw)
        key = run_key(row)
        counts[key] += 1
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out, dict(counts)


def stringify(value: Any) -> str:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    if value is None:
        return ""
    return str(value)


def command_line(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    command = row.get("command")
    if isinstance(command, list):
        return " ".join(str(item) for item in command)
    return stringify(command)


def selected_candidate_from_row(row: dict[str, Any] | None) -> str:
    if row is None:
        return ""
    selected = row.get("laur_selected_rules")
    if isinstance(selected, dict) and selected:
        ranked = sorted(selected.items(), key=lambda item: (-int(item[1]), str(item[0])))
        return str(ranked[0][0])
    method = str(row.get("method", ""))
    if method in {BASE_METHOD, *COMPARE_METHODS}:
        return "additive_ltm"
    if boolish(row.get("laur_force_additive")):
        return "additive_ltm"
    return ""


def summarize_updates(rows: list[dict[str, Any]]) -> dict[tuple[str, int, int, str], dict[str, Any]]:
    grouped: dict[tuple[str, int, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[run_key(row)].append(row)
    out: dict[tuple[str, int, int, str], dict[str, Any]] = {}
    for key, group in grouped.items():
        feature_rows = [
            row for row in group if row.get("runtime_feature_names") or row.get("runtime_feature_values")
        ]
        out[key] = {
            "update_log_rows": len(group),
            "feature_extraction_rows": len(feature_rows),
            "decision_status_counts": dict(Counter(str(row.get("decision_status", "")) for row in group)),
            "fallback_reason_counts": dict(Counter(str(row.get("fallback_reason", "")) for row in group)),
            "selected_rule_source_counts": dict(Counter(str(row.get("selected_rule_source", "")) for row in group)),
        }
    return out


def command_by_key(rows: list[dict[str, Any]]) -> dict[tuple[str, int, int, str], dict[str, Any]]:
    out: dict[tuple[str, int, int, str], dict[str, Any]] = {}
    for row in rows:
        out.setdefault(run_key(row), row)
    return out


def value_for(
    *,
    field: str,
    row: dict[str, Any] | None,
    command_row: dict[str, Any] | None,
) -> Any:
    if row is None:
        return None
    if field == "selected_candidate_id":
        return selected_candidate_from_row(row)
    if field == "method_alias":
        return row.get("method")
    if field == "return_code":
        return command_row.get("returncode") if command_row else ""
    if field == "command_line":
        return command_line(command_row)
    return row.get(field)


def core_outcome_exact(base: dict[str, Any] | None, other: dict[str, Any] | None) -> bool:
    if base is None or other is None:
        return False
    return all(base.get(field) == other.get(field) for field in OUTCOME_FIELDS)


def classify_field(
    *,
    field: str,
    method: str,
    base_value: Any,
    other_value: Any,
    outcome_exact: bool,
    update_summary: dict[str, Any],
) -> str:
    if field in {"success", "feasible"}:
        return "success mismatch"
    if field == "sum_of_loss_ratio" and finite_status(base_value) != finite_status(other_value):
        return "finite/nonfinite ratio mismatch"
    if field == "sum_of_loss":
        return "sum_of_loss mismatch"
    if field == "makespan":
        return "makespan mismatch"
    if field == "lower_bound":
        return "lower_bound mismatch"
    if field == "selected_candidate_id" and outcome_exact:
        return "selected-candidate labeling-only mismatch"
    if field in {"method_alias", "return_code", "command_line"}:
        return "wrapper/method alias mismatch"
    if field == "laur_model_path" and method in BYPASS_METHODS and stringify(other_value):
        return "runtime artifact loaded when it should have been bypassed"
    if field in EFFORT_FIELDS:
        return "time-budget / nondeterministic rerun difference"
    if int(update_summary.get("feature_extraction_rows") or 0) > 0 and method in BYPASS_METHODS:
        return "update log / feature extraction executed in a parity path"
    return "wrapper/method alias mismatch"


def extra_bypass_classifications(method: str, update_summary: dict[str, Any], row: dict[str, Any]) -> list[str]:
    classifications: list[str] = []
    if method not in BYPASS_METHODS:
        return classifications
    if int(update_summary.get("feature_extraction_rows") or 0) > 0:
        classifications.append("update log / feature extraction executed in a parity path")
    if stringify(row.get("laur_model_path")) and method in {
        "always_additive_defer",
        "repair5f_candidate_additive_ltm",
        "repair5f_bounded_updateparam_selector_force_additive_parity",
        "laur_disable",
        "laur_force_additive_direct",
    }:
        classifications.append("runtime artifact loaded when it should have been bypassed")
    return classifications


def build_mismatches(
    *,
    raw_rows: list[dict[str, Any]],
    commands: dict[tuple[str, int, int, str], dict[str, Any]],
    updates: dict[tuple[str, int, int, str], dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, bool], list[dict[str, Any]]]:
    by_case: dict[tuple[str, int, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in raw_rows:
        by_case[case_key(row)][str(row.get("method"))] = row

    mismatch_rows: list[dict[str, Any]] = []
    case_summaries: list[dict[str, Any]] = []
    exact_by_method: dict[str, bool] = {}
    for method in COMPARE_METHODS:
        method_present = any(method in methods for methods in by_case.values())
        exact = method_present
        for key, methods in sorted(by_case.items()):
            base = methods.get(BASE_METHOD)
            other = methods.get(method)
            base_command = commands.get((*key, BASE_METHOD))
            other_command = commands.get((*key, method))
            update_summary = updates.get((*key, method), {})
            if base is None or other is None:
                if method_present:
                    exact = False
                    mismatch_rows.append(
                        {
                            "map": key[0],
                            "agents": key[1],
                            "seed": key[2],
                            "method": method,
                            "field": "row_presence",
                            "base_value": "present" if base is not None else "missing",
                            "method_value": "present" if other is not None else "missing",
                            "equal": False,
                            "classification": "missing row",
                            "update_log_rows": update_summary.get("update_log_rows", 0),
                            "feature_extraction_rows": update_summary.get("feature_extraction_rows", 0),
                        }
                    )
                continue
            outcome_exact = core_outcome_exact(base, other)
            if not outcome_exact:
                exact = False
            case_classifications: set[str] = set()
            for field in COMPARE_FIELDS:
                base_value = value_for(
                    field=field,
                    row=base,
                    command_row=base_command,
                )
                other_value = value_for(
                    field=field,
                    row=other,
                    command_row=other_command,
                )
                equal = base_value == other_value
                if equal:
                    continue
                classification = classify_field(
                    field=field,
                    method=method,
                    base_value=base_value,
                    other_value=other_value,
                    outcome_exact=outcome_exact,
                    update_summary=update_summary,
                )
                case_classifications.add(classification)
                mismatch_rows.append(
                    {
                        "map": key[0],
                        "agents": key[1],
                        "seed": key[2],
                        "method": method,
                        "field": field,
                        "base_value": stringify(base_value),
                        "method_value": stringify(other_value),
                        "equal": False,
                        "classification": classification,
                        "update_log_rows": update_summary.get("update_log_rows", 0),
                        "feature_extraction_rows": update_summary.get("feature_extraction_rows", 0),
                    }
                )
            for classification in extra_bypass_classifications(method, update_summary, other):
                case_classifications.add(classification)
            if case_classifications:
                case_summaries.append(
                    {
                        "map": key[0],
                        "agents": key[1],
                        "seed": key[2],
                        "method": method,
                        "outcome_exact": outcome_exact,
                        "classifications": sorted(case_classifications),
                    }
                )
        exact_by_method[method] = exact
    return mismatch_rows, exact_by_method, case_summaries


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Repair5F.3 Runtime Parity Autopsy\n\n")
        handle.write("Diagnostic-only. Phase5.5 and Phase6 remain forbidden.\n\n")
        handle.write("## Core Parity\n\n")
        for method in COMPARE_METHODS:
            present = summary["method_present"].get(method, False)
            exact = summary["core_outcome_parity_exact_by_method"].get(method, False)
            handle.write(f"- `{method}`: present `{present}`, core parity `{exact}`\n")
        handle.write("\n## Classification Counts\n\n")
        if not summary["classification_counts"]:
            handle.write("No mismatches were found.\n")
        else:
            for key, value in summary["classification_counts"].items():
                handle.write(f"- {key}: `{value}`\n")
        handle.write("\n## Core Mismatch Cases\n\n")
        if not summary["core_mismatch_cases"]:
            handle.write("No core outcome mismatches were found.\n")
        else:
            handle.write("| method | map | agents | seed | classifications |\n")
            handle.write("|---|---|---:|---:|---|\n")
            for row in summary["core_mismatch_cases"]:
                handle.write(
                    f"| `{row['method']}` | {row['map']} | {row['agents']} | {row['seed']} | "
                    f"`{', '.join(row['classifications'])}` |\n"
                )
        handle.write("\n## Runtime-vs-Table Snapshot\n\n")
        table = summary.get("runtime_vs_table_audit", {})
        for key in [
            "runtime_selected_candidate_matches_table_policy",
            "runtime_updateparams_match_artifact",
            "mismatch_count",
            "force_additive_parity_exact",
            "exact_additive_candidate_parity_exact",
        ]:
            if key in table:
                handle.write(f"- {key}: `{table[key]}`\n")
        handle.write("\n## Interpretation\n\n")
        handle.write(
            "F3 remains useful positive runtime evidence for a support-trained static bounded "
            "UpdateParams rule, but the additive controls are not closed in this input run. "
            "The next step is a parity wrapper fix and a same-scope closure rerun, not larger validation.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-jsonl", type=Path, default=Path(DEFAULT_RAW_JSONL))
    parser.add_argument("--commands-jsonl", type=Path, default=Path(DEFAULT_COMMANDS_JSONL))
    parser.add_argument("--laur-updates-jsonl", type=Path, default=Path(DEFAULT_UPDATES_JSONL))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED_CSV))
    parser.add_argument("--eval-summary-json", type=Path, default=Path(DEFAULT_EVAL_SUMMARY_JSON))
    parser.add_argument("--table-audit-summary-json", type=Path, default=Path(DEFAULT_TABLE_AUDIT_SUMMARY_JSON))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--mismatch-csv", type=Path, default=Path(DEFAULT_MISMATCH_CSV))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    raw_jsonl = resolve(args.raw_jsonl, root)
    commands_jsonl = resolve(args.commands_jsonl, root)
    updates_jsonl = resolve(args.laur_updates_jsonl, root)
    paired_csv = resolve(args.paired_csv, root)
    eval_summary_json = resolve(args.eval_summary_json, root)
    table_audit_summary_json = resolve(args.table_audit_summary_json, root)
    report = resolve(args.report, root)
    summary_json = resolve(args.summary_json, root)
    mismatch_csv = resolve(args.mismatch_csv, root)
    for path in [raw_jsonl, commands_jsonl, paired_csv, eval_summary_json, table_audit_summary_json]:
        if not path.exists():
            raise FileNotFoundError(path)

    raw_before = read_jsonl(raw_jsonl)
    raw_rows, duplicate_counts = dedupe_rows(raw_before)
    command_rows = command_by_key(read_jsonl(commands_jsonl))
    update_summaries = summarize_updates(read_jsonl(updates_jsonl))
    mismatches, exact_by_method, case_summaries = build_mismatches(
        raw_rows=raw_rows,
        commands=command_rows,
        updates=update_summaries,
    )
    mismatch_fields = [
        "map",
        "agents",
        "seed",
        "method",
        "field",
        "base_value",
        "method_value",
        "equal",
        "classification",
        "update_log_rows",
        "feature_extraction_rows",
    ]
    write_csv(mismatch_csv, mismatches, mismatch_fields)

    methods_present = {
        method: any(row.get("method") == method for row in raw_rows) for method in COMPARE_METHODS
    }
    core_mismatch_cases = [
        row
        for row in case_summaries
        if not row["outcome_exact"]
    ]
    classification_counts = dict(sorted(Counter(row["classification"] for row in mismatches).items()))
    method_counts = dict(sorted(Counter(row["method"] for row in mismatches).items()))
    update_log_counts_by_method = {
        method: sum(
            int(summary.get("update_log_rows") or 0)
            for key, summary in update_summaries.items()
            if key[3] == method
        )
        for method in COMPARE_METHODS
    }
    feature_rows_by_method = {
        method: sum(
            int(summary.get("feature_extraction_rows") or 0)
            for key, summary in update_summaries.items()
            if key[3] == method
        )
        for method in COMPARE_METHODS
    }
    summary = {
        "schema_version": "phase5p5_repair5f3_runtime_parity_autopsy_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "inputs": {
            "raw_jsonl": rel(raw_jsonl, root),
            "commands_jsonl": rel(commands_jsonl, root),
            "laur_updates_jsonl": rel(updates_jsonl, root),
            "paired_csv": rel(paired_csv, root),
            "eval_summary_json": rel(eval_summary_json, root),
            "table_audit_summary_json": rel(table_audit_summary_json, root),
        },
        "outputs": {
            "report": rel(report, root),
            "summary_json": rel(summary_json, root),
            "mismatch_csv": rel(mismatch_csv, root),
        },
        "raw_rows_before_dedupe": len(raw_before),
        "raw_rows_after_dedupe": len(raw_rows),
        "duplicate_raw_rows_dropped": len(raw_before) - len(raw_rows),
        "duplicate_key_count": sum(1 for count in duplicate_counts.values() if count > 1),
        "paired_csv_rows": len(read_csv_rows(paired_csv)),
        "method_present": methods_present,
        "core_outcome_fields": OUTCOME_FIELDS,
        "effort_fields": EFFORT_FIELDS,
        "reported_fields": COMPARE_FIELDS,
        "core_outcome_parity_exact_by_method": exact_by_method,
        "force_additive_parity_exact": exact_by_method.get(
            "repair5f_bounded_updateparam_selector_force_additive_parity", False
        ),
        "exact_additive_candidate_parity_exact": exact_by_method.get("repair5f_candidate_additive_ltm", False),
        "laur_disable_parity_exact": exact_by_method.get("laur_disable", False),
        "laur_force_additive_direct_parity_exact": exact_by_method.get("laur_force_additive_direct", False),
        "mismatch_rows": len(mismatches),
        "classification_counts": classification_counts,
        "mismatch_counts_by_method": method_counts,
        "core_mismatch_case_count": len(core_mismatch_cases),
        "core_mismatch_cases": core_mismatch_cases,
        "case_mismatch_examples": case_summaries[:50],
        "update_log_counts_by_method": update_log_counts_by_method,
        "feature_extraction_rows_by_method": feature_rows_by_method,
        "eval_summary_runtime_gates": read_json(eval_summary_json).get("runtime_gates", {}),
        "runtime_vs_table_audit": read_json(table_audit_summary_json),
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    print(json.dumps({"summary_json": rel(summary_json, root), "mismatch_rows": len(mismatches)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Autopsy the Repair5G.3 strict protocol parity failure."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g31_protocol_common import (  # noqa: E402
    ALLOWED_NON_SEMANTIC_CLASSIFICATIONS,
    CONTROL_PAIRS,
    classify_returncode,
    classify_strict_mismatch,
    command_key,
    generated_row_kind,
    is_raw_solver_row,
    number,
    run_dimension_key,
    solver_crash_count,
    strict_mismatched_fields,
    summarize_gate_value,
)
from repair5g3_common import (  # noqa: E402
    load_json,
    read_csv_rows,
    read_jsonl,
    rel,
    repo_root,
    resolve,
    schema_error_count,
    support_gate_summary,
    write_csv_rows,
    write_json,
)


DEFAULT_DETERMINISM_SUMMARY = "outputs/reports/phase5p5_repair5g3_determinism_repeat_summary.json"
DEFAULT_BROAD_SUMMARY = "outputs/reports/phase5p5_repair5g3_broader_validation_summary.json"
DEFAULT_BROAD_AUDIT = "outputs/reports/phase5p5_repair5g3_broader_validation_audit.md"
DEFAULT_BROAD_PAIRED = "outputs/tables/phase5p5_repair5g3_broader_validation_paired.csv"
DEFAULT_BROAD_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g3_broader_validation_summary.csv"
DEFAULT_BROAD_BY_GROUP = "outputs/tables/phase5p5_repair5g3_broader_validation_by_map_agent.csv"
DEFAULT_BROAD_JSONL = "outputs/logs/phase5p5_repair5g3_broader_validation/phase5p5_repair5g3_broader_validation.jsonl"
DEFAULT_BROAD_COMMANDS = "outputs/logs/phase5p5_repair5g3_broader_validation/phase5p5_repair5g3_broader_validation_commands.jsonl"
DEFAULT_REPEAT_JSONL = "outputs/logs/phase5p5_repair5g3_determinism_repeat/phase5p5_repair5g3_determinism_repeat.jsonl"
DEFAULT_REPEAT_COMMANDS = "outputs/logs/phase5p5_repair5g3_determinism_repeat/phase5p5_repair5g3_determinism_repeat_commands.jsonl"

DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g3_protocol_failure_autopsy.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g3_protocol_failure_autopsy_summary.json"
DEFAULT_MISMATCH_CSV = "outputs/tables/phase5p5_repair5g3_protocol_parity_mismatch_cases.csv"
DEFAULT_RC2_CSV = "outputs/tables/phase5p5_repair5g3_protocol_returncode2_cases.csv"
DEFAULT_GATE_TYPE_CSV = "outputs/tables/phase5p5_repair5g3_protocol_gate_type_audit.csv"
DEFAULT_DUP_CSV = "outputs/tables/phase5p5_repair5g3_protocol_resume_duplicate_audit.csv"

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--determinism-summary-json", type=Path, default=Path(DEFAULT_DETERMINISM_SUMMARY))
    parser.add_argument("--broader-summary-json", type=Path, default=Path(DEFAULT_BROAD_SUMMARY))
    parser.add_argument("--broader-audit-md", type=Path, default=Path(DEFAULT_BROAD_AUDIT))
    parser.add_argument("--broader-paired-csv", type=Path, default=Path(DEFAULT_BROAD_PAIRED))
    parser.add_argument("--broader-summary-csv", type=Path, default=Path(DEFAULT_BROAD_SUMMARY_CSV))
    parser.add_argument("--broader-by-map-agent-csv", type=Path, default=Path(DEFAULT_BROAD_BY_GROUP))
    parser.add_argument("--broader-jsonl", type=Path, default=Path(DEFAULT_BROAD_JSONL))
    parser.add_argument("--broader-command-log", type=Path, default=Path(DEFAULT_BROAD_COMMANDS))
    parser.add_argument("--determinism-jsonl", type=Path, default=Path(DEFAULT_REPEAT_JSONL))
    parser.add_argument("--determinism-command-log", type=Path, default=Path(DEFAULT_REPEAT_COMMANDS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--mismatch-csv", type=Path, default=Path(DEFAULT_MISMATCH_CSV))
    parser.add_argument("--returncode2-csv", type=Path, default=Path(DEFAULT_RC2_CSV))
    parser.add_argument("--gate-type-audit-csv", type=Path, default=Path(DEFAULT_GATE_TYPE_CSV))
    parser.add_argument("--resume-duplicate-audit-csv", type=Path, default=Path(DEFAULT_DUP_CSV))
    return parser.parse_args(argv)


def attach_returncodes(rows: list[dict[str, Any]], command_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_command: dict[tuple[str, int, int, str], list[dict[str, Any]]] = defaultdict(list)
    for command in command_rows:
        by_command[command_key(command)].append(command)
    out = []
    for row in rows:
        item = dict(row)
        matches = by_command.get(command_key(row), [])
        if matches:
            item["returncode"] = matches[0].get("returncode")
            item["returncode_classification"] = classify_returncode(matches[0].get("returncode"))
        else:
            item["returncode"] = ""
            item["returncode_classification"] = "not_command_row"
        out.append(item)
    return out


def rows_by_case(rows: list[dict[str, Any]]) -> dict[tuple[Any, ...], dict[str, dict[str, Any]]]:
    grouped: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row.get("map")),
            int(number(row.get("agents"), 0)),
            int(number(row.get("seed"), 0)),
            str(row.get("scen", "")),
            *run_dimension_key(row),
        )
        grouped.setdefault(key, {})[str(row.get("method"))] = row
    return grouped


def mismatch_rows(rows: list[dict[str, Any]], *, source: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    grouped = rows_by_case(rows)
    for key, methods in sorted(grouped.items()):
        for left_method, right_method in CONTROL_PAIRS:
            left = methods.get(left_method)
            right = methods.get(right_method)
            classification = classify_strict_mismatch(left, right)
            if classification == "exact":
                continue
            mismatched = strict_mismatched_fields(left or {}, right or {})
            base = {
                "source": source,
                "map": key[0],
                "agents": key[1],
                "seed": key[2],
                "scen": key[3],
                "repeat_index": key[4],
                "mode": key[5],
                "time_budget_sec": key[6],
                "ltm_iteration_budget": key[7],
                "left_method": left_method,
                "right_method": right_method,
                "method": right_method,
                "classification": classification,
                "mismatched_fields": ",".join(mismatched) if mismatched else "missing_row",
                "affects_selected_flow_shield_comparison": False,
            }
            for prefix, row in [("left", left or {}), ("right", right or {})]:
                base.update(
                    {
                        f"{prefix}_returncode": row.get("returncode", ""),
                        f"{prefix}_returncode_classification": row.get("returncode_classification", ""),
                        f"{prefix}_success": row.get("success", ""),
                        f"{prefix}_sum_of_loss": row.get("sum_of_loss", ""),
                        f"{prefix}_ratio": row.get("sum_of_loss_ratio", ""),
                        f"{prefix}_makespan": row.get("makespan", ""),
                        f"{prefix}_expanded_nodes": row.get("expanded_nodes", ""),
                        f"{prefix}_time_to_first_solution_ms": row.get("time_to_first_solution_ms", ""),
                        f"{prefix}_runtime_ms": row.get("runtime_ms", ""),
                    }
                )
            out.append(base)
    return out


def returncode2_rows(command_rows: list[dict[str, Any]], rows: list[dict[str, Any]], *, source: str) -> list[dict[str, Any]]:
    raw_by_key = {command_key(row): row for row in rows if is_raw_solver_row(row)}
    out = []
    for command in command_rows:
        if classify_returncode(command.get("returncode")) != "returncode2_no_solution_equivalent":
            continue
        row = raw_by_key.get(command_key(command), {})
        out.append(
            {
                "source": source,
                "map": command.get("map", ""),
                "agents": command.get("agents", ""),
                "seed": command.get("seed", ""),
                "method": command.get("method", ""),
                "returncode": command.get("returncode", ""),
                "classification": "returncode2_no_solution_equivalent",
                "has_solver_row": bool(row),
                "success": row.get("success", ""),
                "sum_of_loss": row.get("sum_of_loss", ""),
                "sum_of_loss_ratio": row.get("sum_of_loss_ratio", ""),
                "makespan": row.get("makespan", ""),
                "runtime_ms": row.get("runtime_ms", ""),
                "stdout_tail": command.get("stdout", ""),
                "stderr_tail": command.get("stderr", ""),
            }
        )
    return out


def gate_type_rows(*summaries: tuple[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for source, summary in summaries:
        for key, value in sorted(summary.get("gates", {}).items()):
            out.append({"source": source, **summarize_gate_value(key, value)})
        for key in ["missing_rows", "schema_errors", "solver_crash_count", "row_count", "expected_row_count"]:
            if key in summary:
                out.append({"source": source, **summarize_gate_value(key, summary[key])})
    return out


def duplicate_audit_rows(paths: list[tuple[str, Path]], *, root: Path) -> list[dict[str, Any]]:
    out = []
    for source, path in paths:
        rows = read_jsonl(path)
        generated_counts = Counter(generated_row_kind(row) for row in rows)
        raw_seen: set[tuple[Any, ...]] = set()
        raw_duplicates = 0
        all_seen: set[tuple[Any, ...]] = set()
        all_duplicates = 0
        for row in rows:
            key = (
                str(row.get("map")),
                int(number(row.get("agents"), 0)),
                int(number(row.get("seed"), 0)),
                str(row.get("scen", "")),
                str(row.get("method")),
                *run_dimension_key(row),
            )
            if key in all_seen:
                all_duplicates += 1
            all_seen.add(key)
            if is_raw_solver_row(row):
                if key in raw_seen:
                    raw_duplicates += 1
                raw_seen.add(key)
        out.append(
            {
                "source": source,
                "path": rel(path, root),
                "row_count": len(rows),
                "raw_solver_rows": generated_counts.get("raw_solver", 0),
                "selector_alias_rows": generated_counts.get("selector_alias", 0),
                "synthetic_diagnostic_rows": generated_counts.get("synthetic_diagnostic", 0),
                "all_duplicate_keys": all_duplicates,
                "raw_solver_duplicate_keys": raw_duplicates,
                "synthetic_rows_counted_as_raw_solver_rows": 0,
                "resume_safe_raw_solver_rows": raw_duplicates == 0,
            }
        )
    return out


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.3 Protocol Failure Autopsy\n\n")
        handle.write("G3 remains a protocol failure until the sequential reproducer and parity policy are accepted.\n\n")
        handle.write("## Findings\n\n")
        handle.write(f"- Broad pair-level strict mismatches: `{summary['broad_mismatch_count']}`\n")
        handle.write(f"- Strict mismatch classifications: `{summary['mismatch_classification_counts']}`\n")
        handle.write(f"- True semantic parity mismatches: `{summary['true_semantic_parity_mismatch_count']}`\n")
        handle.write(f"- Return-code-2/no-solution-equivalent commands: `{summary['returncode2_case_count']}`\n")
        handle.write(f"- Solver crash count: `{summary['solver_crash_count']}`\n")
        handle.write(f"- Bool-as-int gate type violations: `{summary['bool_as_int_gate_type_violations']}`\n")
        handle.write(f"- Duplicate raw solver rows on resume: `{summary['raw_solver_duplicate_keys']}`\n\n")
        handle.write("## Interpretation\n\n")
        handle.write(summary["interpretation"] + "\n\n")
        handle.write("## Next Step\n\n")
        handle.write(summary["next_step"] + "\n\n")
        handle.write("## Inputs\n\n")
        for key, value in summary["input_artifacts"].items():
            handle.write(f"- `{key}`: `{value}`\n")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    determinism_summary = load_json(resolve(args.determinism_summary_json, root))
    broad_summary = load_json(resolve(args.broader_summary_json, root))
    broad_commands = read_jsonl(resolve(args.broader_command_log, root))
    repeat_commands = read_jsonl(resolve(args.determinism_command_log, root))
    broad_rows = attach_returncodes(read_jsonl(resolve(args.broader_jsonl, root)), broad_commands)
    repeat_rows = attach_returncodes(read_jsonl(resolve(args.determinism_jsonl, root)), repeat_commands)

    broad_mismatches = mismatch_rows(broad_rows, source="g3_broader")
    repeat_mismatches = mismatch_rows(repeat_rows, source="g3_determinism_repeat")
    all_mismatches = [*broad_mismatches, *repeat_mismatches]
    returncode2 = [
        *returncode2_rows(broad_commands, broad_rows, source="g3_broader"),
        *returncode2_rows(repeat_commands, repeat_rows, source="g3_determinism_repeat"),
    ]
    gate_rows = gate_type_rows(("g3_determinism_repeat", determinism_summary), ("g3_broader", broad_summary))
    duplicate_rows = duplicate_audit_rows(
        [
            ("g3_broader_jsonl", resolve(args.broader_jsonl, root)),
            ("g3_determinism_repeat_jsonl", resolve(args.determinism_jsonl, root)),
        ],
        root=root,
    )

    write_csv_rows(resolve(args.mismatch_csv, root), all_mismatches)
    write_csv_rows(resolve(args.returncode2_csv, root), returncode2)
    write_csv_rows(resolve(args.gate_type_audit_csv, root), gate_rows)
    write_csv_rows(resolve(args.resume_duplicate_audit_csv, root), duplicate_rows)

    broad_recomputed = support_gate_summary(broad_rows, include_static_c_equiv_pairs=False)
    classification_counts = Counter(row["classification"] for row in all_mismatches)
    true_semantic = classification_counts.get("true_semantic_mismatch", 0)
    non_semantic_only = all(row["classification"] in ALLOWED_NON_SEMANTIC_CLASSIFICATIONS for row in all_mismatches)
    bool_as_int_violations = sum(1 for row in gate_rows if row.get("bool_as_int_violation"))
    raw_dups = sum(int(row["raw_solver_duplicate_keys"]) for row in duplicate_rows)
    table_counts = {
        "broad_paired_rows": len(read_csv_rows(resolve(args.broader_paired_csv, root))),
        "broad_summary_rows": len(read_csv_rows(resolve(args.broader_summary_csv, root))),
        "broad_by_map_agent_rows": len(read_csv_rows(resolve(args.broader_by_map_agent_csv, root))),
    }
    summary = {
        "schema_version": "phase5p5_repair5g3_protocol_failure_autopsy_summary_v1",
        "created_at": __import__("datetime").datetime.now().isoformat(),
        "input_artifacts": {
            "determinism_summary_json": rel(resolve(args.determinism_summary_json, root), root),
            "broader_summary_json": rel(resolve(args.broader_summary_json, root), root),
            "broader_audit_md": rel(resolve(args.broader_audit_md, root), root),
            "broader_jsonl": rel(resolve(args.broader_jsonl, root), root),
            "broader_command_log": rel(resolve(args.broader_command_log, root), root),
            "determinism_jsonl": rel(resolve(args.determinism_jsonl, root), root),
            "determinism_command_log": rel(resolve(args.determinism_command_log, root), root),
        },
        "table_counts": table_counts,
        "broad_recomputed_protocol_gates": broad_recomputed,
        "broad_mismatch_count": len(broad_mismatches),
        "determinism_mismatch_count": len(repeat_mismatches),
        "mismatch_count": len(all_mismatches),
        "mismatch_classification_counts": dict(sorted(classification_counts.items())),
        "true_semantic_parity_mismatch_count": true_semantic,
        "returncode2_case_count": len(returncode2),
        "solver_crash_count": solver_crash_count([*broad_commands, *repeat_commands]),
        "schema_error_count": schema_error_count([*broad_rows, *repeat_rows]),
        "bool_as_int_gate_type_violations": bool_as_int_violations,
        "raw_solver_duplicate_keys": raw_dups,
        "synthetic_rows_counted_as_raw_solver_rows": sum(
            int(row["synthetic_rows_counted_as_raw_solver_rows"]) for row in duplicate_rows
        ),
        "all_strict_mismatches_non_semantic": non_semantic_only,
        "stop_for_semantic_parity_bug": true_semantic > 0,
        "ready_for_control_parity_reproducer": true_semantic == 0 and non_semantic_only and raw_dups == 0,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "diagnostic_only": True,
    }
    if summary["stop_for_semantic_parity_bug"]:
        summary["interpretation"] = "stop_for_semantic_parity_bug: at least one strict mismatch is not explained by the time budget, timeout, return-code-2, reporting, or missing-row classes."
        summary["next_step"] = "Stop before G4 and inspect implementation semantics."
    else:
        summary["interpretation"] = (
            "The committed G3 artifacts show strict exact parity failures, but this autopsy classifies them as "
            "non-semantic boundary effects; no true semantic parity mismatch was found in the raw rows."
        )
        summary["next_step"] = (
            "Run the sequential control-only reproducer and then write a formal parity policy before any G4 clean validation."
        )
    write_json(resolve(args.summary_json, root), summary)
    write_report(resolve(args.report, root), summary)
    print(json.dumps({"ready_for_control_parity_reproducer": summary["ready_for_control_parity_reproducer"], "mismatches": len(all_mismatches)}))
    return 0 if not summary["stop_for_semantic_parity_bug"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

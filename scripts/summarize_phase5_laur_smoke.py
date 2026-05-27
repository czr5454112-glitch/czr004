"""Summarize Phase5C LAU-LTM closed-loop smoke JSONL rows."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from czr004_metrics.schema import normalize_run_row, validate_run_row  # noqa: E402


LTM_METHOD = "lacam_star_ltm"
FORCE_METHOD = "lacam_star_lau_ltm_force_additive"
LEARNED_METHOD = "lacam_star_lau_ltm_learned_safety"


SUMMARY_FIELDS = [
    "map",
    "agents",
    "method",
    "runs",
    "successes",
    "success_rate",
    "ratio_mean",
    "runtime_ms_mean",
    "expanded_nodes_mean",
    "low_level_pibt_calls_mean",
    "laur_inference_count_mean",
    "laur_inference_total_ms_mean",
    "laur_additive_fallback_count_mean",
    "laur_safety_disabled_count_mean",
    "selected_rules",
]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _mean(values: list[float]) -> float:
    return statistics.mean(values) if values else math.nan


def _number(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value is None or isinstance(value, bool):
        return None
    return float(value)


def _format(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float) and not math.isfinite(value):
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["map"]), int(row["agents"]), str(row["method"]))].append(row)

    out: list[dict[str, Any]] = []
    for (map_name, agents, method), group in sorted(grouped.items()):
        ratios = [_number(row, "sum_of_loss_ratio") for row in group if row.get("success")]
        runtimes = [_number(row, "runtime_ms") for row in group]
        expanded = [_number(row, "expanded_nodes") for row in group]
        pibt = [_number(row, "low_level_pibt_calls") for row in group]
        inference_count = [_number(row, "laur_inference_count") for row in group]
        inference_ms = [_number(row, "laur_inference_total_ms") for row in group]
        fallback_count = [_number(row, "laur_additive_fallback_count") for row in group]
        safety_count = [_number(row, "laur_safety_disabled_count") for row in group]
        selected_rules: dict[str, int] = defaultdict(int)
        for row in group:
            for rule_id, count in (row.get("laur_selected_rules") or {}).items():
                selected_rules[str(rule_id)] += int(count)
        out.append(
            {
                "map": map_name,
                "agents": agents,
                "method": method,
                "runs": len(group),
                "successes": sum(1 for row in group if row.get("success")),
                "success_rate": sum(1 for row in group if row.get("success")) / len(group),
                "ratio_mean": _mean([value for value in ratios if value is not None]),
                "runtime_ms_mean": _mean([value for value in runtimes if value is not None]),
                "expanded_nodes_mean": _mean([value for value in expanded if value is not None]),
                "low_level_pibt_calls_mean": _mean([value for value in pibt if value is not None]),
                "laur_inference_count_mean": _mean([value for value in inference_count if value is not None]),
                "laur_inference_total_ms_mean": _mean([value for value in inference_ms if value is not None]),
                "laur_additive_fallback_count_mean": _mean([value for value in fallback_count if value is not None]),
                "laur_safety_disabled_count_mean": _mean([value for value in safety_count if value is not None]),
                "selected_rules": json.dumps(dict(sorted(selected_rules.items())), sort_keys=True),
            }
        )
    return out


def _run_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row.get("map"), int(row.get("agents", 0)), row.get("seed"), row.get("scen"))


def parity_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_key: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if row["method"] in {LTM_METHOD, FORCE_METHOD}:
            by_key[_run_key(row)][row["method"]] = row

    checked = 0
    errors: list[str] = []
    for key, methods in sorted(by_key.items()):
        if LTM_METHOD not in methods or FORCE_METHOD not in methods:
            continue
        checked += 1
        base = methods[LTM_METHOD]
        force = methods[FORCE_METHOD]
        for field in (
            "success",
            "feasible",
            "sum_of_loss",
            "lower_bound",
            "returned_solutions_count",
            "committed_events",
            "blocked_events",
            "nonzero_ltm_edges",
        ):
            if base.get(field) != force.get(field):
                errors.append(f"{key}: {field} baseline={base.get(field)} force={force.get(field)}")
        base_ratio = _number(base, "sum_of_loss_ratio")
        force_ratio = _number(force, "sum_of_loss_ratio")
        if base_ratio is not None and force_ratio is not None:
            if abs(base_ratio - force_ratio) > 1.0e-9:
                errors.append(f"{key}: ratio baseline={base_ratio} force={force_ratio}")
    return {"checked_pairs": checked, "errors": errors, "passed": checked > 0 and not errors}


def learned_vs_ltm(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_key: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if row["method"] in {LTM_METHOD, LEARNED_METHOD}:
            by_key[_run_key(row)][row["method"]] = row

    pairs = []
    for methods in by_key.values():
        if LTM_METHOD in methods and LEARNED_METHOD in methods:
            pairs.append((methods[LTM_METHOD], methods[LEARNED_METHOD]))

    if not pairs:
        return {"paired_runs": 0, "success_not_lower": False, "ratio_not_worse": False, "expanded_not_worse": False}

    ltm_success = sum(1 for base, _ in pairs if base.get("success"))
    learned_success = sum(1 for _, contender in pairs if contender.get("success"))
    ltm_ratios = [_number(base, "sum_of_loss_ratio") for base, contender in pairs if base.get("success") and contender.get("success")]
    learned_ratios = [_number(contender, "sum_of_loss_ratio") for base, contender in pairs if base.get("success") and contender.get("success")]
    ltm_expanded = [_number(base, "expanded_nodes") for base, contender in pairs if base.get("success") and contender.get("success")]
    learned_expanded = [_number(contender, "expanded_nodes") for base, contender in pairs if base.get("success") and contender.get("success")]
    ltm_ratio_mean = _mean([value for value in ltm_ratios if value is not None])
    learned_ratio_mean = _mean([value for value in learned_ratios if value is not None])
    ltm_expanded_mean = _mean([value for value in ltm_expanded if value is not None])
    learned_expanded_mean = _mean([value for value in learned_expanded if value is not None])

    return {
        "paired_runs": len(pairs),
        "ltm_successes": ltm_success,
        "learned_successes": learned_success,
        "success_not_lower": learned_success >= ltm_success,
        "ltm_ratio_mean": ltm_ratio_mean,
        "learned_ratio_mean": learned_ratio_mean,
        "ratio_not_worse": math.isfinite(ltm_ratio_mean)
        and math.isfinite(learned_ratio_mean)
        and learned_ratio_mean <= ltm_ratio_mean,
        "ltm_expanded_nodes_mean": ltm_expanded_mean,
        "learned_expanded_nodes_mean": learned_expanded_mean,
        "expanded_not_worse": math.isfinite(ltm_expanded_mean)
        and math.isfinite(learned_expanded_mean)
        and learned_expanded_mean <= ltm_expanded_mean,
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_report(
    path: Path,
    *,
    input_jsonl: Path,
    rows: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
    summary_csv: Path,
    schema_errors: list[str],
    parity: dict[str, Any],
    learned: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    overhead_reported = all(row.get("laur_inference_total_ms") is not None for row in rows if row.get("laur_enabled"))
    learned_rows = [row for row in rows if row.get("method") == LEARNED_METHOD]
    learned_inference_rows = sum(1 for row in learned_rows if int(row.get("laur_inference_count") or 0) > 0)
    ttfs_values = [row.get("time_to_first_solution_ms") for row in rows if row.get("time_to_first_solution_ms") is not None]
    runtime_smoke_gate = {
        "schema_validation": not schema_errors,
        "fallback_parity": bool(parity["passed"]),
        "learned_success_not_lower_than_ltm": bool(learned.get("success_not_lower")),
        "equal_wallclock_ratio_not_worse": bool(learned.get("ratio_not_worse")),
        "equal_node_expanded_not_worse": bool(learned.get("expanded_not_worse")),
        "overhead_reported": overhead_reported,
        "learned_runtime_exercised": learned_inference_rows > 0,
        "ttfs_gate_evaluable": bool(ttfs_values),
    }

    with path.open("w", encoding="utf-8") as handle:
        handle.write("# Phase5C LAUR Closed-Loop Smoke Report\n\n")
        handle.write("Status: generated by Phase5C smoke runner. This is a runtime smoke/ablation report, not a Phase6 performance claim.\n\n")
        handle.write("## Input\n\n")
        handle.write(f"- JSONL: `{input_jsonl}`\n")
        handle.write(f"- rows: `{len(rows)}`\n")
        handle.write(f"- schema errors: `{len(schema_errors)}`\n")
        handle.write(f"- summary CSV: `{summary_csv}`\n\n")

        handle.write("## Gate Snapshot\n\n")
        for key, value in runtime_smoke_gate.items():
            handle.write(f"- `{key}`: `{value}`\n")
        handle.write("\n")

        handle.write("## Force-Additive Parity\n\n")
        handle.write(f"- checked pairs: `{parity['checked_pairs']}`\n")
        handle.write(f"- passed: `{parity['passed']}`\n")
        if parity["errors"]:
            handle.write("- first errors:\n")
            for error in parity["errors"][:10]:
                handle.write(f"  - `{error}`\n")
        handle.write("\n")

        handle.write("## Learned Runtime vs LTM\n\n")
        for key, value in learned.items():
            handle.write(f"- `{key}`: `{_format(value)}`\n")
        handle.write("\n")

        handle.write("## Method Summary\n\n")
        for row in summary_rows:
            handle.write(
                "- "
                f"`{row['map']}` agents `{row['agents']}` method `{row['method']}`: "
                f"success `{row['successes']}/{row['runs']}`, "
                f"ratio_mean `{_format(row['ratio_mean'])}`, "
                f"inference_ms_mean `{_format(row['laur_inference_total_ms_mean'])}`, "
                f"rules `{row['selected_rules']}`\n"
            )

        handle.write("\n## Interpretation\n\n")
        if not parity["passed"]:
            handle.write("Force-additive parity failed; Phase5 learned-runtime claims must stop until parity is fixed.\n")
        elif not learned.get("success_not_lower"):
            handle.write("Learned runtime was exercised, but smoke success did not match LTM. Treat this as a diagnostic result and return to model/fallback calibration before any solver-level benefit claim.\n")
        elif not (learned.get("ratio_not_worse") or learned.get("expanded_not_worse")):
            handle.write("Learned runtime preserved success on this smoke but did not beat LTM on the available ratio/node checks. This is a valid Phase5C smoke completion, not a learned-benefit claim.\n")
        else:
            handle.write("Learned runtime passed the available conservative smoke checks here, with TTFS still unevaluable because the current runner logs it as null. Broader Phase5D/5E or Phase6-scale evaluation is still required before performance claims.\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-jsonl", required=True, type=Path)
    parser.add_argument("--summary-csv", required=True, type=Path)
    parser.add_argument("--report-md", required=True, type=Path)
    args = parser.parse_args(argv)

    raw_rows = _read_jsonl(args.input_jsonl)
    rows = [normalize_run_row(row) for row in raw_rows]
    schema_errors: list[str] = []
    for index, row in enumerate(rows, 1):
        schema_errors.extend(f"row {index}: {error}" for error in validate_run_row(row))

    summary_rows = summarize(rows)
    write_csv(args.summary_csv, summary_rows, SUMMARY_FIELDS)
    parity = parity_audit(rows)
    learned = learned_vs_ltm(rows)
    write_report(
        args.report_md,
        input_jsonl=args.input_jsonl,
        rows=rows,
        summary_rows=summary_rows,
        summary_csv=args.summary_csv,
        schema_errors=schema_errors,
        parity=parity,
        learned=learned,
    )

    if schema_errors:
        raise ValueError(f"schema validation failed: {schema_errors[:5]}")
    if not parity["passed"]:
        raise ValueError(f"force-additive parity failed: {parity['errors'][:5]}")
    print(
        "phase5_laur_smoke_summary "
        f"rows={len(rows)} parity_pairs={parity['checked_pairs']} report={args.report_md}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

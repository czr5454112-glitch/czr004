"""Classify Repair5G.5.6 warehouse probe failures and NaN gaps."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g56_common import (  # noqa: E402
    G56_STATIC_CANDIDATE,
    best_label_row,
    finite_number,
    group_by_context,
    labels_from_probe_rows,
    normalized_context_key,
    read_csv_rows,
    read_jsonl_many,
    repo_root,
    resolve,
    score_from_label,
    static_additive_rows,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_LABELS = "outputs/tables/phase5p5_repair5g56_counterfactual_update_labels.csv"
DEFAULT_SENTINEL_PROBES = "outputs/logs/phase5p5_repair5g56_warehouse_probe_budget_sentinel/phase5p5_repair5g56_warehouse_probe_budget_update_probes.jsonl"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g56_warehouse_probe_failure_analysis.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g56_warehouse_probe_failure_summary.json"
DEFAULT_CASES = "outputs/tables/phase5p5_repair5g56_warehouse_probe_failure_cases.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels-csv", type=Path, default=Path(DEFAULT_LABELS))
    parser.add_argument("--budget-probe-jsonl", nargs="*", type=Path, default=[Path(DEFAULT_SENTINEL_PROBES)])
    parser.add_argument("--cases-csv", type=Path, default=Path(DEFAULT_CASES))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def read_labels(path: Path) -> list[dict[str, Any]]:
    if path.exists():
        return read_csv_rows(path)
    return []


def budget_sensitive_context_keys(rows: list[dict[str, Any]]) -> set[tuple[str, int, int, int, str]]:
    by_context_budget: dict[tuple[tuple[str, int, int, int, str], float], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if "warehouse" not in str(row.get("map", "")):
            continue
        budget = finite_number(row.get("short_budget_ms"), math.nan)
        if math.isfinite(budget):
            by_context_budget[(normalized_context_key(row), budget)].append(row)
    by_context: dict[tuple[str, int, int, int, str], dict[float, bool]] = defaultdict(dict)
    for (key, budget), group in by_context_budget.items():
        by_context[key][budget] = any(math.isfinite(score_from_label(row)) for row in group)
    sensitive = set()
    for key, budget_map in by_context.items():
        if len(budget_map) >= 2 and len(set(budget_map.values())) > 1:
            sensitive.add(key)
    return sensitive


def classify_context(rows: list[dict[str, Any]], budget_sensitive: bool) -> str:
    if budget_sensitive:
        return "budget_sensitive_solution"
    scores = [(score_from_label(row), row) for row in rows]
    finite = [(score, row) for score, row in scores if math.isfinite(score)]
    static, _additive = static_additive_rows(rows)
    static_finite = math.isfinite(score_from_label(static)) if static else False
    if not finite:
        return "no_solution_all_candidates"
    if static_finite and len(finite) == 1:
        return "static_only_solution"
    if len(finite) < len(rows):
        best_score, best = min(finite, key=lambda item: (item[0], str(item[1].get("candidate_id", ""))))
        if str(best.get("candidate_id", "")) != G56_STATIC_CANDIDATE:
            return "oracle_nonstatic_solution"
        return "candidate_specific_failure"
    best_score, best = best_label_row(rows)
    static_score = score_from_label(static) if static else math.inf
    if str(best.get("candidate_id", "")) != G56_STATIC_CANDIDATE and best_score < static_score - 1.0e-12:
        return "oracle_nonstatic_solution"
    if all(abs(score - best_score) <= 1.0e-12 for score, _row in finite):
        return "valid_flat_no_gap"
    return "valid_flat_no_gap"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    labels = read_labels(resolve(args.labels_csv, root))
    sentinel_rows = labels_from_probe_rows(read_jsonl_many([resolve(path, root) for path in args.budget_probe_jsonl]))
    budget_sensitive = budget_sensitive_context_keys(sentinel_rows)
    warehouse_labels = [row for row in labels if "warehouse" in str(row.get("map", ""))]
    by_context = group_by_context(warehouse_labels)
    cases = []
    for context_id, rows in sorted(by_context.items()):
        first = rows[0]
        key = normalized_context_key(first)
        classification = classify_context(rows, key in budget_sensitive)
        finite_candidates = [row.get("candidate_id", "") for row in rows if math.isfinite(score_from_label(row))]
        cases.append(
            {
                "context_id": context_id,
                "map": first.get("map", ""),
                "agents": first.get("agents", ""),
                "seed": first.get("seed", ""),
                "iteration": first.get("iteration", ""),
                "traffic_before_hash_full": first.get("traffic_before_hash_full", ""),
                "classification": classification,
                "finite_candidate_count": len(finite_candidates),
                "finite_candidate_ids": ",".join(sorted(str(value) for value in finite_candidates)),
                "candidate_rows": len(rows),
            }
        )
    counts = Counter(str(row.get("classification", "")) for row in cases)
    observed_only = validate_observed_rows(warehouse_labels + sentinel_rows, label="Repair5G.5.6 warehouse classification")
    gates = {
        "warehouse_contexts_classified": bool(cases) and all(row.get("classification") for row in cases),
        "warehouse_nan_gap_rows_explained": bool(cases) and all(row.get("classification") for row in cases),
        "observed_ids_only": observed_only,
        "ids_166_205_untouched": observed_only,
    }
    gates["warehouse_probe_failure_analysis_passed"] = all(gates.values())
    write_csv_rows(resolve(args.cases_csv, root), cases)
    summary = {
        "schema_version": "phase5p5_repair5g56_warehouse_probe_failure_summary_v1",
        "warehouse_contexts": len(cases),
        "classification_counts": dict(sorted(counts.items())),
        "cases_csv": str(resolve(args.cases_csv, root)),
        "gates": gates,
        "decision": "warehouse_probe_failures_classified" if gates["warehouse_probe_failure_analysis_passed"] else "warehouse_probe_failure_blocks_training",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.6 Warehouse Probe Failure Analysis\n\n"
        f"- warehouse_contexts: `{len(cases)}`\n"
        f"- classification_counts: `{json.dumps(summary['classification_counts'], sort_keys=True)}`\n"
        f"- warehouse_contexts_classified: `{gates['warehouse_contexts_classified']}`\n"
        f"- warehouse_nan_gap_rows_explained: `{gates['warehouse_nan_gap_rows_explained']}`\n\n"
        "Warehouse failures are retained as diagnostics and must not be used to cherry-pick maps away.\n",
    )
    print(json.dumps({"decision": summary["decision"], "warehouse_contexts": len(cases)}))
    return 0 if observed_only and bool(cases) else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

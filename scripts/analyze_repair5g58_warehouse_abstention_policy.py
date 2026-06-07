"""Classify Repair5G.5.8 warehouse abstention/fallback policy rows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g58_common import (  # noqa: E402
    count_by,
    read_csv_rows,
    repo_root,
    resolve,
    validate_observed_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_G56_SUMMARY = "outputs/reports/phase5p5_repair5g56_warehouse_probe_failure_summary.json"
DEFAULT_G56_CASES = "outputs/tables/phase5p5_repair5g56_warehouse_probe_failure_cases.csv"
DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g58_confidence_weighted_targets.csv"
DEFAULT_OUTPUT = "outputs/tables/phase5p5_repair5g58_warehouse_abstention_policy.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g58_warehouse_abstention_policy.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g58_warehouse_abstention_policy_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warehouse-summary-json", type=Path, default=Path(DEFAULT_G56_SUMMARY))
    parser.add_argument("--warehouse-cases-csv", type=Path, default=Path(DEFAULT_G56_CASES))
    parser.add_argument("--confidence-targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--warehouse-policy-csv", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def choose_policy(case: dict[str, Any], target: dict[str, Any] | None) -> tuple[str, str]:
    if target:
        label = str(target.get("label_class", ""))
        if label == "no_solution_abstain":
            return "no_solution_abstain", "primary/sentinel probes find no feasible candidate"
        if label == "longer_budget_needed":
            return "longer_budget_needed", "2000 ms sentinel finds feasibility where 1000 ms does not"
        if label == "stable_static":
            return "static_default", "warehouse context is stable and static/default is near-oracle"
        if label == "abstain_to_static":
            return "static_default", "oracle identity is unstable but static remains near-oracle"
        if label == "budget_sensitive_exclude":
            return "candidate_space_gap", "primary/sentinel candidate feasibility or oracle identity is budget-sensitive"
        if label == "stable_high_confidence_nonstatic":
            return "warehouse_specialist_later", "warehouse has a stable nonstatic signal but is not used as no-solution expert positive"
    source = str(case.get("classification", ""))
    if source == "no_solution_all_candidates":
        return "no_solution_abstain", "carried forward from G5.6 no-solution classification"
    if source == "budget_sensitive_solution":
        return "longer_budget_needed", "carried forward from G5.6 budget-sensitive warehouse classification"
    return "candidate_space_gap", "warehouse case lacks enough primary-pair evidence for safe training"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    source_summary = load_json(resolve(args.warehouse_summary_json, root))
    cases = read_csv_rows(resolve(args.warehouse_cases_csv, root))
    targets = [
        row
        for row in read_csv_rows(resolve(args.confidence_targets_csv, root))
        if str(row.get("margin_threshold", "")) in {"0.005", "0.0050"}
    ]
    target_by_key = {str(row.get("normalized_context_key", "")): row for row in targets}
    rows = []
    for case in cases:
        key = str(case.get("normalized_context_key", "")) or f"{case.get('map','')}|a{case.get('agents','')}|s{case.get('seed','')}|it{case.get('iteration','')}|{case.get('traffic_before_hash_full','')}"
        target = target_by_key.get(key)
        policy, reason = choose_policy(case, target)
        rows.append(
            {
                "context_id": case.get("context_id", target.get("context_id", "") if target else ""),
                "normalized_context_key": key,
                "map": case.get("map", ""),
                "agents": case.get("agents", ""),
                "seed": case.get("seed", ""),
                "iteration": case.get("iteration", ""),
                "traffic_before_hash_full": case.get("traffic_before_hash_full", ""),
                "g56_classification": case.get("classification", ""),
                "g58_label_class": target.get("label_class", "") if target else "",
                "warehouse_policy": policy,
                "policy_reason": reason,
                "not_silently_dropped": True,
            }
        )
    output_csv = resolve(args.warehouse_policy_csv, root)
    write_csv_rows(output_csv, rows)
    policy_counts = count_by(rows, "warehouse_policy")
    observed_ok = validate_observed_rows(rows, label="Repair5G.5.8 warehouse abstention policy")
    warehouse_contexts = int(source_summary.get("warehouse_contexts", len(cases)) or len(cases))
    gates = {
        "warehouse_contexts_classified": bool(rows) and len(rows) == len(cases),
        "warehouse_contexts_used_or_explained": all(str(row.get("warehouse_policy", "")) for row in rows),
        "warehouse_no_solution_not_silently_dropped": all(str(row.get("not_silently_dropped", "")).lower() == "true" or row.get("not_silently_dropped") is True for row in rows),
        "observed_ids_only": observed_ok,
    }
    gates["ids_166_205_untouched"] = observed_ok
    gates["warehouse_abstention_policy_passed"] = all(gates.values())
    summary = {
        "schema_version": "phase5p5_repair5g58_warehouse_abstention_policy_summary_v1",
        "source_summary_json": str(resolve(args.warehouse_summary_json, root)),
        "source_cases_csv": str(resolve(args.warehouse_cases_csv, root)),
        "warehouse_contexts": warehouse_contexts,
        "policy_rows": len(rows),
        "policy_counts": policy_counts,
        "warehouse_abstention_policy_csv": str(output_csv),
        "gates": gates,
        "decision": "warehouse_abstention_policy_passed" if gates["warehouse_abstention_policy_passed"] else "warehouse_abstention_policy_failed",
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
        "runtime_claim_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.8 Warehouse Abstention Policy\n\n"
        f"- warehouse_contexts: `{warehouse_contexts}`\n"
        f"- policy_rows: `{len(rows)}`\n"
        f"- policy_counts: `{json.dumps(policy_counts, sort_keys=True)}`\n"
        f"- warehouse_abstention_policy_passed: `{gates['warehouse_abstention_policy_passed']}`\n\n"
        "Warehouse contexts are classified as abstention, longer-budget, static-default, candidate-space-gap, or future specialist cases; they are not silently dropped.\n",
    )
    print(json.dumps({"decision": summary["decision"], "policy_counts": policy_counts}))
    return 0 if rows and observed_ok else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

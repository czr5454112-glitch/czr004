"""Analyze Repair5G.5.3 runtime hook overhead ablation."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g2_common import method_pair_exact, parity_mismatch_rows  # noqa: E402
from repair5g3_common import (  # noqa: E402
    add_selector_alias_rows,
    git_value,
    grouped_rows,
    method_stats,
    number,
    paired_rows,
    read_jsonl,
    repo_root,
    resolve,
    schema_error_count,
    write_csv_rows,
    write_json,
)
from repair5g5_common import DEFAULT_FROZEN_G2_SPEC, load_json  # noqa: E402
from repair5g51_common import write_text  # noqa: E402


DEFAULT_JSONL = "outputs/logs/phase5p5_repair5g53_hook_overhead_ablation/phase5p5_repair5g53_hook_overhead_ablation.jsonl"
DEFAULT_COMMANDS = "outputs/logs/phase5p5_repair5g53_hook_overhead_ablation/phase5p5_repair5g53_hook_overhead_ablation_commands.jsonl"
DEFAULT_UPDATES = "outputs/logs/phase5p5_repair5g53_hook_overhead_ablation/phase5p5_repair5g53_hook_overhead_ablation_ltm_updates.jsonl"
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g53_hook_overhead_ablation_paired.csv"
DEFAULT_COMPONENTS = "outputs/tables/phase5p5_repair5g53_hook_overhead_components.csv"
DEFAULT_REGRET = "outputs/tables/phase5p5_repair5g53_hook_overhead_regret_cases.csv"
DEFAULT_MISMATCHES = "outputs/tables/phase5p5_repair5g53_hook_overhead_mismatches.csv"
DEFAULT_BY_GROUP = "outputs/tables/phase5p5_repair5g53_hook_overhead_ablation_by_map_agent.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g53_hook_overhead_ablation_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g53_hook_overhead_ablation_summary.json"

G53_STATIC_MIN = "repair5g53_runtime_always_static_minimal_hook"
G53_MAP_MIN = "repair5g53_runtime_always_map_agent_minimal_hook"
G53_SHADOW_NOOP = "repair5g53_runtime_static_shadow_noop_minimal"

COMPONENT_FIELDS = [
    "repair5g53_update_policy_total_ms",
    "repair5g53_feature_build_ms",
    "repair5g53_cost_audit_ms",
    "repair5g53_candidate_select_ms",
    "repair5g53_alias_resolve_ms",
    "repair5g53_params_hash_ms",
    "repair5g53_traffic_hash_ms",
    "repair5g53_json_write_ms",
    "repair5g53_update_apply_ms",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-jsonl", type=Path, default=Path(DEFAULT_JSONL))
    parser.add_argument("--command-log", type=Path, default=Path(DEFAULT_COMMANDS))
    parser.add_argument("--update-log", type=Path, default=Path(DEFAULT_UPDATES))
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_FROZEN_G2_SPEC))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED))
    parser.add_argument("--components-csv", type=Path, default=Path(DEFAULT_COMPONENTS))
    parser.add_argument("--regret-cases-csv", type=Path, default=Path(DEFAULT_REGRET))
    parser.add_argument("--mismatches-csv", type=Path, default=Path(DEFAULT_MISMATCHES))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_BY_GROUP))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def analysis_rows(raw_rows: list[dict[str, Any]], frozen_spec: dict[str, Any]) -> list[dict[str, Any]]:
    return [*raw_rows, *add_selector_alias_rows(raw_rows, frozen_spec)]


def component_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        method = str(row.get("method", ""))
        if not method.startswith("repair5g53_"):
            continue
        calls = max(1.0, number(row.get("repair5g53_update_policy_calls"), 0.0))
        item = {
            "method": method,
            "map": row.get("map", ""),
            "agents": row.get("agents", ""),
            "seed": row.get("seed", ""),
            "runtime_audit_mode": row.get("repair5g_runtime_audit_mode", ""),
            "hook_mode": row.get("repair5g53_hook_mode", ""),
            "update_policy_calls": row.get("repair5g53_update_policy_calls", 0),
        }
        for field in COMPONENT_FIELDS:
            total = number(row.get(field), 0.0)
            item[field] = total
            item[field.replace("_ms", "_per_update_ms")] = total / calls
        out.append(item)
    return out


def regret_rows(paired: list[dict[str, Any]], pairs: list[tuple[str, str]]) -> list[dict[str, Any]]:
    by_case: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = {}
    for row in paired:
        key = (str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)), str(row.get("scen", "")))
        by_case.setdefault(key, {})[str(row.get("candidate_id"))] = row
    out: list[dict[str, Any]] = []
    for key, methods in sorted(by_case.items()):
        for left, right in pairs:
            lrow = methods.get(left)
            rrow = methods.get(right)
            if not lrow or not rrow:
                continue
            ldelta = number(lrow.get("delta_ratio_vs_ltm"), math.nan)
            rdelta = number(rrow.get("delta_ratio_vs_ltm"), math.nan)
            regret = ldelta - rdelta if math.isfinite(ldelta) and math.isfinite(rdelta) else math.nan
            if math.isfinite(regret) and abs(regret) > 1.0e-12:
                out.append(
                    {
                        "map": key[0],
                        "agents": key[1],
                        "seed": key[2],
                        "scen": key[3],
                        "left_method": left,
                        "right_method": right,
                        "left_delta_ratio_vs_ltm": ldelta,
                        "right_delta_ratio_vs_ltm": rdelta,
                        "regret": regret,
                    }
                )
    return out


def dominant_component(components: list[dict[str, Any]]) -> tuple[str, float]:
    totals: dict[str, list[float]] = {}
    for row in components:
        for field in COMPONENT_FIELDS:
            if field == "repair5g53_update_policy_total_ms":
                continue
            value = number(row.get(field), 0.0)
            if value > 0.0:
                totals.setdefault(field, []).append(value)
    if not totals:
        return "", 0.0
    means = {field: statistics.mean(values) for field, values in totals.items() if values}
    field = max(means, key=means.get)
    return field, means[field]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    frozen_spec = load_json(resolve(args.frozen_selector_spec_json, root))
    rows = analysis_rows(read_jsonl(resolve(args.output_jsonl, root)), frozen_spec)
    commands = read_jsonl(resolve(args.command_log, root))
    updates = read_jsonl(resolve(args.update_log, root))
    paired = paired_rows(rows)
    stats = method_stats(paired)
    by_group = grouped_rows(paired, group_fields=["map", "agents"])
    components = component_rows(rows)
    regrets = regret_rows(
        paired,
        [
            (G53_STATIC_MIN, "repair5g2_best_frozen_static_candidate"),
            (G53_MAP_MIN, "repair5g2_frozen_static_or_selector"),
            (G53_SHADOW_NOOP, "repair5g2_best_frozen_static_candidate"),
        ],
    )
    mismatches = parity_mismatch_rows(
        rows,
        [
            (G53_STATIC_MIN, "repair5g2_best_frozen_static_candidate"),
            (G53_MAP_MIN, "repair5g2_frozen_static_or_selector"),
            (G53_SHADOW_NOOP, "repair5g2_best_frozen_static_candidate"),
        ],
    )
    true_mismatches = [row for row in mismatches if row.get("classification") == "true_semantic_mismatch"]
    time_budget_mismatches = [
        row for row in mismatches if row.get("classification") == "time_budget_sensitivity"
    ]
    missing_mismatches = [row for row in mismatches if row.get("classification") == "missing_row"]
    classification_counts = {
        name: sum(1 for row in mismatches if row.get("classification") == name)
        for name in sorted({str(row.get("classification", "")) for row in mismatches})
    }
    component_name, component_mean = dominant_component(components)
    write_csv_rows(resolve(args.paired_csv, root), paired)
    write_csv_rows(resolve(args.components_csv, root), components)
    write_csv_rows(resolve(args.regret_cases_csv, root), regrets)
    write_csv_rows(resolve(args.mismatches_csv, root), mismatches)
    write_csv_rows(resolve(args.by_map_agent_csv, root), by_group)
    failure_class = ""
    if true_mismatches:
        failure_class = "minimal_hook_true_semantic_mismatch"
    elif time_budget_mismatches:
        failure_class = "minimal_hook_time_budget_sensitivity"
    elif missing_mismatches:
        failure_class = "minimal_hook_missing_rows"
    elif mismatches:
        failure_class = "minimal_hook_unknown_mismatch"
    gates = {
        "row_count": len(rows),
        "update_log_rows": len(updates),
        "schema_errors": schema_error_count(rows),
        "solver_crash_count": sum(1 for row in commands if int(number(row.get("returncode"), 0)) == 1),
        "minimal_hook_static_matches_static": method_pair_exact(rows, G53_STATIC_MIN, "repair5g2_best_frozen_static_candidate"),
        "minimal_hook_map_agent_matches_map_agent": method_pair_exact(rows, G53_MAP_MIN, "repair5g2_frozen_static_or_selector"),
        "shadow_noop_minimal_matches_static": method_pair_exact(rows, G53_SHADOW_NOOP, "repair5g2_best_frozen_static_candidate"),
        "minimal_hook_mismatch_count": len(mismatches),
        "minimal_hook_time_budget_sensitivity_count": len(time_budget_mismatches),
        "minimal_hook_missing_row_count": len(missing_mismatches),
        "minimal_hook_mismatch_classification_counts": classification_counts,
        "minimal_hook_failure_class": failure_class,
        "true_semantic_mismatch_count": len(true_mismatches),
        "full_audit_overhead_classified": any(
            str(row.get("method")) in {"repair5g53_static_hook_full_features_jsonl", "repair5g53_shadow_static_full_log"}
            for row in rows
        )
        and bool(components),
        "dominant_overhead_component_identified": bool(component_name),
        "dominant_overhead_component": component_name,
        "dominant_overhead_component_mean_ms": component_mean,
    }
    if not gates["minimal_hook_static_matches_static"] or not gates["minimal_hook_map_agent_matches_map_agent"]:
        decision = "minimal_hook_semantic_bug"
    elif gates["dominant_overhead_component_identified"]:
        decision = "runtime_hook_overhead_classified"
    else:
        decision = "stop_for_protocol_or_semantic_bug"
    gates["hook_overhead_ablation_passed"] = decision == "runtime_hook_overhead_classified"
    summary = {
        "schema_version": "phase5p5_repair5g53_hook_overhead_ablation_summary_v1",
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "row_count": len(rows),
        "update_log_rows": len(updates),
        "method_stats": stats,
        "gates": gates,
        "decision": decision,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.3 Hook Overhead Ablation\n\n"
        f"- minimal_hook_static_matches_static: `{gates['minimal_hook_static_matches_static']}`\n"
        f"- minimal_hook_map_agent_matches_map_agent: `{gates['minimal_hook_map_agent_matches_map_agent']}`\n"
        f"- shadow_noop_minimal_matches_static: `{gates['shadow_noop_minimal_matches_static']}`\n"
        f"- minimal_hook_failure_class: `{failure_class or 'none'}`\n"
        f"- minimal_hook_time_budget_sensitivity_count: `{len(time_budget_mismatches)}`\n"
        f"- true_semantic_mismatch_count: `{gates['true_semantic_mismatch_count']}`\n"
        f"- dominant_overhead_component: `{component_name}`\n"
        f"- decision: `{decision}`\n\n"
        "This is diagnostic-only; performance claims must use `--repair5g-runtime-audit-mode perf`.\n",
    )
    print(json.dumps({"decision": decision, "rows": len(rows), "dominant_component": component_name}))
    return 0 if gates["hook_overhead_ablation_passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

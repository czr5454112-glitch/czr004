"""Create a paper-grade autopsy for the Repair5G.4 flow-shield evidence."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g3_common import (  # noqa: E402
    grouped_rows,
    method_stats,
    number,
    oracle_regret_rows,
    read_csv_rows,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
)
from repair5g5_common import load_json, rel  # noqa: E402


DEFAULT_DECISION = "outputs/reports/phase5p5_repair5g31_g4_decision.md"
DEFAULT_G4_SUMMARY = "outputs/reports/phase5p5_repair5g4_clean_frozen_validation_summary.json"
DEFAULT_STRESS_SUMMARY = "outputs/reports/phase5p5_repair5g4_time_iteration_stress_summary.json"
DEFAULT_SELECTOR_REPORT = "outputs/reports/phase5p5_repair5g4_contextual_selector_report.md"
DEFAULT_SELECTOR_SUMMARY = "outputs/reports/phase5p5_repair5g4_contextual_selector_summary.json"
DEFAULT_RUNTIME_GAP = "outputs/reports/phase5p5_repair5g4_contextual_selector_runtime_gap.md"
DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g4_clean_frozen_validation_paired.csv"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g4_clean_frozen_validation_summary.csv"
DEFAULT_BY_GROUP = "outputs/tables/phase5p5_repair5g4_clean_frozen_validation_by_map_agent.csv"
DEFAULT_STRESS_BUDGET = "outputs/tables/phase5p5_repair5g4_time_iteration_stress_by_budget.csv"
DEFAULT_STRESS_ITER = "outputs/tables/phase5p5_repair5g4_time_iteration_stress_by_iteration.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g4_paper_grade_autopsy.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g4_paper_grade_autopsy_summary.json"
DEFAULT_SELECTOR_CASES = "outputs/tables/phase5p5_repair5g4_selector_vs_static_cases.csv"
DEFAULT_ABLATION = "outputs/tables/phase5p5_repair5g4_ablation_effect_table.csv"
DEFAULT_GROUP_RISK = "outputs/tables/phase5p5_repair5g4_group_risk_table.csv"
DEFAULT_STRESS_EFFECT = "outputs/tables/phase5p5_repair5g4_stress_effect_table.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g4_oracle_regret_table.csv"
DEFAULT_SELECTOR_SWEEP = "outputs/tables/phase5p5_repair5g4_contextual_selector_sweep.csv"

SELECTOR = "repair5g2_frozen_static_or_selector"
STATIC = "repair5g2_best_frozen_static_candidate"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision-report", type=Path, default=Path(DEFAULT_DECISION))
    parser.add_argument("--g4-summary-json", type=Path, default=Path(DEFAULT_G4_SUMMARY))
    parser.add_argument("--stress-summary-json", type=Path, default=Path(DEFAULT_STRESS_SUMMARY))
    parser.add_argument("--selector-report", type=Path, default=Path(DEFAULT_SELECTOR_REPORT))
    parser.add_argument("--selector-summary-json", type=Path, default=Path(DEFAULT_SELECTOR_SUMMARY))
    parser.add_argument("--runtime-gap-report", type=Path, default=Path(DEFAULT_RUNTIME_GAP))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED))
    parser.add_argument("--summary-csv", type=Path, default=Path(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_BY_GROUP))
    parser.add_argument("--stress-by-budget-csv", type=Path, default=Path(DEFAULT_STRESS_BUDGET))
    parser.add_argument("--stress-by-iteration-csv", type=Path, default=Path(DEFAULT_STRESS_ITER))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--selector-vs-static-cases-csv", type=Path, default=Path(DEFAULT_SELECTOR_CASES))
    parser.add_argument("--ablation-effect-csv", type=Path, default=Path(DEFAULT_ABLATION))
    parser.add_argument("--group-risk-csv", type=Path, default=Path(DEFAULT_GROUP_RISK))
    parser.add_argument("--stress-effect-csv", type=Path, default=Path(DEFAULT_STRESS_EFFECT))
    parser.add_argument("--oracle-regret-csv", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--contextual-selector-sweep-csv", type=Path, default=Path(DEFAULT_SELECTOR_SWEEP))
    return parser.parse_args(argv)


def case_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (
        str(row.get("map")),
        int(number(row.get("agents"), 0)),
        int(number(row.get("seed"), 0)),
        str(row.get("scen", "")),
    )


def selector_static_cases(paired: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = {}
    for row in paired:
        grouped.setdefault(case_key(row), {})[str(row.get("candidate_id"))] = row
    out = []
    for key, rows in sorted(grouped.items()):
        selector = rows.get(SELECTOR)
        static = rows.get(STATIC)
        if selector is None or static is None:
            continue
        selector_delta = number(selector.get("delta_ratio_vs_ltm"), math.nan)
        static_delta = number(static.get("delta_ratio_vs_ltm"), math.nan)
        out.append(
            {
                "map": key[0],
                "agents": key[1],
                "seed": key[2],
                "scen": key[3],
                "selector_delta_ratio_vs_ltm": selector_delta,
                "static_delta_ratio_vs_ltm": static_delta,
                "selector_minus_static": selector_delta - static_delta
                if math.isfinite(selector_delta) and math.isfinite(static_delta)
                else "",
                "selector_selected_source_method": selector.get("repair5g2_selected_source_method", ""),
                "selector_better_than_static": math.isfinite(selector_delta)
                and math.isfinite(static_delta)
                and selector_delta < static_delta - 1.0e-12,
                "selector_worse_than_static": math.isfinite(selector_delta)
                and math.isfinite(static_delta)
                and selector_delta > static_delta + 1.0e-12,
            }
        )
    return out


def ablation_rows(stats: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for method, metrics in sorted(stats.items()):
        if method in {"lacam_star_ltm"}:
            continue
        component = "control"
        if method.startswith("repair5g1_shield_") or method.startswith("repair5g2_frozen") or method == STATIC:
            component = "flow_shield"
        elif method.startswith("repair5g_dual_c_equiv_") or method == "repair5g2_c_equiv_best_frozen_baseline":
            component = "c_equiv"
        elif method.startswith("repair5g4_random") or method.startswith("repair5g4_shuffled"):
            component = "negative_control"
        elif method.startswith("repair5f"):
            component = "scalar"
        rows.append(
            {
                "method": method,
                "component": component,
                "rows": metrics.get("rows"),
                "better": metrics.get("better"),
                "equal": metrics.get("equal"),
                "worse": metrics.get("worse"),
                "mean_delta_ratio_vs_ltm": metrics.get("mean_delta_ratio_vs_ltm"),
                "ratio_worse_than_ltm_groups": metrics.get("ratio_worse_than_ltm_groups"),
                "success_worse_than_ltm_groups": metrics.get("success_worse_than_ltm_groups"),
            }
        )
    return rows


def stress_rows(by_budget: list[dict[str, Any]], by_iter: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in by_budget:
        if row.get("method") == SELECTOR:
            rows.append({"stress_axis": "time_budget_sec", **row})
    for row in by_iter:
        if row.get("method") == SELECTOR:
            rows.append({"stress_axis": "ltm_iteration_budget", **row})
    return rows


def selector_sweep_rows(selector_summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for name, metrics in sorted(selector_summary.get("selector_metrics", {}).items()):
        rows.append(
            {
                "selector_name": name,
                "rows": metrics.get("rows"),
                "better": metrics.get("better"),
                "equal": metrics.get("equal"),
                "worse": metrics.get("worse"),
                "mean_delta_ratio_vs_ltm": metrics.get("mean_delta_ratio_vs_ltm"),
                "median_delta_ratio_vs_ltm": metrics.get("median_delta_ratio_vs_ltm"),
                "bootstrap_prob_mean_lt_0": metrics.get("bootstrap", {}).get("prob_mean_lt_0"),
                "ratio_worse_than_ltm_groups": metrics.get("ratio_worse_than_ltm_groups"),
                "success_worse_than_ltm_groups": metrics.get("success_worse_than_ltm_groups"),
                "best_selector": name == selector_summary.get("best_selector_name"),
                "diagnostic_only": selector_summary.get("diagnostic_only", True),
                "phase5p5_allowed": selector_summary.get("phase5p5_allowed", False),
                "phase6_allowed": selector_summary.get("phase6_allowed", False),
            }
        )
    if not rows:
        rows.append(
            {
                "selector_name": "blocked_no_selector_summary",
                "blocked_reason": "phase5p5_repair5g4_contextual_selector_summary.json missing selector_metrics",
                "diagnostic_only": True,
                "phase5p5_allowed": False,
                "phase6_allowed": False,
            }
        )
    return rows


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.4 Paper-Grade Autopsy\n\n")
        handle.write("Diagnostic-only consolidation. Static flow-shield is not an AAAI-ready learned runtime method.\n\n")
        handle.write("## Answers\n\n")
        for answer in summary["answers"]:
            handle.write(f"- {answer}\n")
        handle.write("\n## Safe Claims\n\n")
        for claim in summary["safe_claims"]:
            handle.write(f"- {claim}\n")
        handle.write("\n## Forbidden Claims\n\n")
        for claim in summary["forbidden_claims"]:
            handle.write(f"- {claim}\n")
        handle.write("\n## Artifact Index\n\n")
        for key, value in summary["artifacts"].items():
            handle.write(f"- `{key}`: `{value}`\n")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    g4 = load_json(resolve(args.g4_summary_json, root))
    stress = load_json(resolve(args.stress_summary_json, root))
    selector_summary = load_json(resolve(args.selector_summary_json, root))
    paired = read_csv_rows(resolve(args.paired_csv, root))
    by_group = read_csv_rows(resolve(args.by_map_agent_csv, root))
    by_budget = read_csv_rows(resolve(args.stress_by_budget_csv, root))
    by_iter = read_csv_rows(resolve(args.stress_by_iteration_csv, root))
    if not paired:
        raise SystemExit("missing G4 paired rows")
    stats = g4.get("method_stats") or method_stats(paired)
    cases = selector_static_cases(paired)
    ablations = ablation_rows(stats)
    group_risk = [
        row
        for row in by_group
        if row.get("method") in {SELECTOR, STATIC, "repair5g2_c_equiv_best_frozen_baseline"}
    ]
    stress_effect = stress_rows(by_budget, by_iter)
    oracle = oracle_regret_rows(paired)
    write_csv_rows(resolve(args.selector_vs_static_cases_csv, root), cases)
    write_csv_rows(resolve(args.ablation_effect_csv, root), ablations)
    write_csv_rows(resolve(args.group_risk_csv, root), group_risk)
    write_csv_rows(resolve(args.stress_effect_csv, root), stress_effect)
    write_csv_rows(resolve(args.oracle_regret_csv, root), oracle)
    write_csv_rows(resolve(args.contextual_selector_sweep_csv, root), selector_sweep_rows(selector_summary))
    selector_stats = stats.get(SELECTOR, {})
    static_stats = stats.get(STATIC, {})
    selector_mean = number(selector_stats.get("mean_delta_ratio_vs_ltm"), math.inf)
    static_mean = number(static_stats.get("mean_delta_ratio_vs_ltm"), math.inf)
    runtime_gap_text = resolve(args.runtime_gap_report, root).read_text(encoding="utf-8") if resolve(args.runtime_gap_report, root).exists() else ""
    answers = [
        f"Flow-shield representation validated: `{g4.get('gates', {}).get('representation_gates_passed')}`.",
        f"Frozen map-agent selector better than static: `{selector_mean < static_mean}` (selector mean {selector_mean}, static mean {static_mean}).",
        "Learned runtime selector necessary for AAAI story: `true`; G4 only validates static/map-agent flow-shield and an offline bridge.",
        "Map-agent gains are concentrated in non-warehouse random/maze groups; warehouse remains no-op or fallback-heavy.",
        f"Stress preserves sign: `{stress.get('gates', {}).get('selected_3s_negative') and stress.get('gates', {}).get('selected_5s_not_reversed') and stress.get('gates', {}).get('selected_10s_not_reversed')}`.",
        "Safe claims are representation/protocol/diagnostic claims; learned runtime and AAAI-ready claims remain forbidden.",
    ]
    summary = {
        "schema_version": "phase5p5_repair5g4_paper_grade_autopsy_summary_v1",
        "g4_summary": rel(resolve(args.g4_summary_json, root), root),
        "stress_summary": rel(resolve(args.stress_summary_json, root), root),
        "selector_report": rel(resolve(args.selector_report, root), root),
        "runtime_gap_report": rel(resolve(args.runtime_gap_report, root), root),
        "answers": answers,
        "safe_claims": [
            "Flow-shielded goal-aware dual-channel UpdateLTM is protocol-clean under the accepted parity policy on G4.",
            "Static/map-agent flow-shield beats additive LTM and scalar/C-equiv controls on G4 diagnostics.",
            "Offline decision-stump selector is promising as a bridge but not yet a runtime-validated learned method.",
        ],
        "partial_claims": [
            "Map-agent selection improves static in G4, but this is not a learned runtime UpdateLTM claim.",
            "AAAI positioning is plausible only as a future learned runtime contribution.",
        ],
        "forbidden_claims": [
            "AAAI-ready learned method.",
            "Phase5.5 or Phase6 promotion.",
            "Learned selector fresh validation passed.",
            "Static flow-shield alone is the final learned contribution.",
        ],
        "selector_vs_static": {
            "selector_mean_delta_ratio_vs_ltm": None if not math.isfinite(selector_mean) else selector_mean,
            "static_mean_delta_ratio_vs_ltm": None if not math.isfinite(static_mean) else static_mean,
            "selector_minus_static": None if not (math.isfinite(selector_mean) and math.isfinite(static_mean)) else selector_mean - static_mean,
        },
        "runtime_gap_present": "runtime selector hook" in runtime_gap_text or "no runtime" in runtime_gap_text.lower(),
        "artifacts": {
            "selector_vs_static_cases": rel(resolve(args.selector_vs_static_cases_csv, root), root),
            "ablation_effect_table": rel(resolve(args.ablation_effect_csv, root), root),
            "group_risk_table": rel(resolve(args.group_risk_csv, root), root),
            "stress_effect_table": rel(resolve(args.stress_effect_csv, root), root),
            "oracle_regret_table": rel(resolve(args.oracle_regret_csv, root), root),
            "contextual_selector_sweep": rel(resolve(args.contextual_selector_sweep_csv, root), root),
        },
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "aaai_ready": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_report(resolve(args.report, root), summary)
    print(json.dumps({"selector_minus_static": summary["selector_vs_static"]["selector_minus_static"], "aaai_ready": False}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

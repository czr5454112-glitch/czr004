"""Autopsy Repair5G.2 results as representation, selector, and diagnostic evidence."""

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
    git_value,
    grouped_rows,
    load_json,
    method_component,
    method_stats,
    metrics_for_rows,
    number,
    oracle_regret_rows,
    read_csv_rows,
    rel,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
)


DEFAULT_PAIRED = "outputs/tables/phase5p5_repair5g2_fresh_final_eval_paired.csv"
DEFAULT_BY_GROUP = "outputs/tables/phase5p5_repair5g2_fresh_final_eval_by_map_agent.csv"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase5p5_repair5g2_fresh_final_eval_summary.csv"
DEFAULT_SPEC = "outputs/reports/phase5p5_repair5g2_frozen_selector_spec.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g2_result_autopsy.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g2_result_autopsy_summary.json"
DEFAULT_SELECTOR_CASES = "outputs/tables/phase5p5_repair5g2_selector_vs_static_cases.csv"
DEFAULT_REP_DOM = "outputs/tables/phase5p5_repair5g2_representation_dominance_by_group.csv"
DEFAULT_ORACLE = "outputs/tables/phase5p5_repair5g2_final_oracle_regret.csv"
DEFAULT_WORST = "outputs/tables/phase5p5_repair5g2_worst_cases.csv"

SELECTOR = "repair5g2_frozen_static_or_selector"
STATIC = "repair5g2_best_frozen_static_candidate"
G1_TOP = "repair5g2_g1_top_diagnostic_candidate"
C_EQUIV = "repair5g2_c_equiv_best_frozen_baseline"
SCALARS = [
    C_EQUIV,
    "repair5f_static_c100_b100_w075_d090",
    "repair5f4_best_static_c125_b125_w075_d095_diagnostic_only",
]
DIAGNOSTICS = [
    "repair5g2_random_candidate_diagnostic",
    "repair5g2_shuffled_goal_progress_diagnostic",
    "repair5g2_shuffled_flow_shield_diagnostic",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_BY_GROUP))
    parser.add_argument("--summary-csv", type=Path, default=Path(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--frozen-selector-spec-json", type=Path, default=Path(DEFAULT_SPEC))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--selector-cases-csv", type=Path, default=Path(DEFAULT_SELECTOR_CASES))
    parser.add_argument("--representation-dominance-csv", type=Path, default=Path(DEFAULT_REP_DOM))
    parser.add_argument("--oracle-regret-csv", type=Path, default=Path(DEFAULT_ORACLE))
    parser.add_argument("--worst-cases-csv", type=Path, default=Path(DEFAULT_WORST))
    return parser.parse_args(argv)


def normalize_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        item = dict(row)
        item["agents"] = int(float(row.get("agents", 0) or 0))
        item["seed"] = int(float(row.get("seed", 0) or 0))
        item["delta_ratio_vs_ltm"] = number(row.get("delta_ratio_vs_ltm"), math.nan)
        item["sum_of_loss_ratio"] = number(row.get("sum_of_loss_ratio"), math.nan)
        item["better_vs_ltm"] = str(row.get("better_vs_ltm", "")).lower() == "true"
        item["equal_vs_ltm"] = str(row.get("equal_vs_ltm", "")).lower() == "true"
        item["worse_vs_ltm"] = str(row.get("worse_vs_ltm", "")).lower() == "true"
        item["component"] = row.get("component") or method_component(str(row.get("candidate_id", "")))
        out.append(item)
    return out


def by_case(rows: list[dict[str, Any]]) -> dict[tuple[str, int, int], dict[str, dict[str, Any]]]:
    grouped: dict[tuple[str, int, int], dict[str, dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((str(row["map"]), int(row["agents"]), int(row["seed"])), {})[
            str(row["candidate_id"])
        ] = row
    return grouped


def selector_cases(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for (map_name, agents, seed), methods in sorted(by_case(rows).items()):
        selector = methods.get(SELECTOR)
        static = methods.get(STATIC)
        c_equiv = methods.get(C_EQUIV)
        if selector is None or static is None:
            continue
        selector_delta = number(selector.get("delta_ratio_vs_ltm"), math.inf)
        static_delta = number(static.get("delta_ratio_vs_ltm"), math.inf)
        c_delta = number(c_equiv.get("delta_ratio_vs_ltm"), math.inf) if c_equiv else math.inf
        if selector_delta < static_delta - 1.0e-12:
            classification = "selector_wins_over_static"
        elif static_delta < selector_delta - 1.0e-12:
            classification = "static_wins_over_selector"
        else:
            classification = "selector_static_tie"
        if selector_delta <= 0.0 and static_delta <= 0.0:
            joint = "both_win_or_tie_ltm"
        elif selector_delta > 0.0 and static_delta > 0.0:
            joint = "both_lose_to_ltm"
        else:
            joint = "mixed"
        out.append(
            {
                "map": map_name,
                "agents": agents,
                "seed": seed,
                "selector_delta_ratio_vs_ltm": selector_delta,
                "static_delta_ratio_vs_ltm": static_delta,
                "c_equiv_delta_ratio_vs_ltm": c_delta if math.isfinite(c_delta) else "",
                "selector_minus_static": selector_delta - static_delta,
                "classification": classification,
                "joint_ltm_classification": joint,
                "selector_source_method": selector.get("repair5g2_selected_source_method", ""),
                "selector_avoids_harm_vs_static": static_delta > 0.0 and selector_delta <= 0.0,
                "selector_missed_gain_vs_static": static_delta < -1.0e-12 and selector_delta > static_delta + 1.0e-12,
                "flow_shield_hurts_c_equiv_safe": selector_delta > 0.0 and c_delta <= 0.0,
            }
        )
    return out


def representation_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = grouped_rows(rows, group_fields=["map", "agents"])
    out = []
    for row in grouped:
        method = str(row["method"])
        row["component"] = method_component(method)
        out.append(row)
    return out


def worst_cases(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    focus = [SELECTOR, STATIC, C_EQUIV, *DIAGNOSTICS]
    selected = [row for row in rows if row.get("candidate_id") in focus]
    selected.sort(key=lambda row: number(row.get("delta_ratio_vs_ltm"), -math.inf), reverse=True)
    return selected[:50]


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.2 Result Autopsy\n\n")
        handle.write("Diagnostic-only. `phase5p5_allowed=false` and `phase6_allowed=false` remain closed.\n\n")
        handle.write("## Answer\n\n")
        handle.write(summary["answer"] + "\n\n")
        handle.write("## Selector vs Static\n\n")
        for key, value in summary["selector_vs_static"].items():
            handle.write(f"- `{key}`: `{value}`\n")
        handle.write("\n## Representation Evidence\n\n")
        for key, value in summary["representation_evidence"].items():
            handle.write(f"- `{key}`: `{value}`\n")
        handle.write("\n## Diagnostics\n\n")
        for method, stats in summary["diagnostic_metrics"].items():
            handle.write(
                f"- `{method}`: rows `{stats.get('rows')}`, mean delta `{stats.get('mean_delta_ratio_vs_ltm')}`\n"
            )
        handle.write("\n## Risk Notes\n\n")
        for note in summary["risk_notes"]:
            handle.write(f"- {note}\n")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    rows = normalize_rows(read_csv_rows(resolve(args.paired_csv, root)))
    spec = load_json(resolve(args.frozen_selector_spec_json, root))
    stats = method_stats(rows)
    selector_case_rows = selector_cases(rows)
    rep_rows = representation_rows(rows)
    oracle_rows = oracle_regret_rows(rows)
    worst = worst_cases(rows)

    write_csv_rows(resolve(args.selector_cases_csv, root), selector_case_rows)
    write_csv_rows(resolve(args.representation_dominance_csv, root), rep_rows)
    write_csv_rows(resolve(args.oracle_regret_csv, root), oracle_rows)
    write_csv_rows(resolve(args.worst_cases_csv, root), worst)

    selector_metrics = stats.get(SELECTOR, {})
    static_metrics = stats.get(STATIC, {})
    flow_methods = [method for method in stats if method.startswith("repair5g1_shield_") or method in {SELECTOR, STATIC, G1_TOP}]
    c_methods = [method for method in stats if method in SCALARS or method.startswith("repair5g_dual_c_equiv_")]
    best_flow = min(flow_methods, key=lambda method: number(stats[method].get("mean_delta_ratio_vs_ltm"), math.inf))
    best_c = min(c_methods, key=lambda method: number(stats[method].get("mean_delta_ratio_vs_ltm"), math.inf))
    selector_mean = number(selector_metrics.get("mean_delta_ratio_vs_ltm"), math.inf)
    static_mean = number(static_metrics.get("mean_delta_ratio_vs_ltm"), math.inf)
    if abs(selector_mean - static_mean) <= 0.001:
        selector_verdict = "tied_within_0p001"
    elif selector_mean < static_mean:
        selector_verdict = "selector_beats_static"
    else:
        selector_verdict = "static_beats_selector"
    answer = (
        "G2 is mainly a representation win with selector value still unclear. "
        "Flow-shielded dual-channel UpdateLTM is much stronger than scalar/C-equivalent baselines, "
        "while the frozen selector is effectively tied with the best static flow-shield candidate."
    )
    summary = {
        "schema_version": "phase5p5_repair5g2_result_autopsy_v1",
        "created_at": __import__("datetime").datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "frozen_selector_type": spec.get("selected_selector_type", ""),
        "answer": answer,
        "selector_vs_static": {
            "selector_mean_delta_ratio_vs_ltm": selector_mean,
            "static_mean_delta_ratio_vs_ltm": static_mean,
            "selector_minus_static_mean": selector_mean - static_mean,
            "classification": selector_verdict,
            "selector_wins_cases": sum(1 for row in selector_case_rows if row["classification"] == "selector_wins_over_static"),
            "static_wins_cases": sum(1 for row in selector_case_rows if row["classification"] == "static_wins_over_selector"),
            "ties_cases": sum(1 for row in selector_case_rows if row["classification"] == "selector_static_tie"),
            "selector_avoids_harm_cases": sum(1 for row in selector_case_rows if row["selector_avoids_harm_vs_static"]),
            "selector_missed_gain_cases": sum(1 for row in selector_case_rows if row["selector_missed_gain_vs_static"]),
        },
        "representation_evidence": {
            "best_flow_shield_method": best_flow,
            "best_flow_shield_mean_delta_ratio_vs_ltm": stats[best_flow].get("mean_delta_ratio_vs_ltm"),
            "best_c_equiv_or_scalar_method": best_c,
            "best_c_equiv_or_scalar_mean_delta_ratio_vs_ltm": stats[best_c].get("mean_delta_ratio_vs_ltm"),
            "flow_minus_c_gap": number(stats[best_c].get("mean_delta_ratio_vs_ltm"), 0.0)
            - number(stats[best_flow].get("mean_delta_ratio_vs_ltm"), 0.0),
        },
        "diagnostic_metrics": {method: stats.get(method, {}) for method in DIAGNOSTICS},
        "oracle_regret_rows": len(oracle_rows),
        "risk_notes": [
            "Warehouse is mostly no-op/fallback, so random and maze carry most G2 benefit.",
            "Shuffled flow-shield diagnostic is close to the selector, so selector intelligence should not be overclaimed.",
            "IDs 46..65 are observed and can be used only as later training data, not untouched final evidence.",
        ],
        "outputs": {
            "selector_cases_csv": rel(resolve(args.selector_cases_csv, root), root),
            "representation_dominance_csv": rel(resolve(args.representation_dominance_csv, root), root),
            "oracle_regret_csv": rel(resolve(args.oracle_regret_csv, root), root),
            "worst_cases_csv": rel(resolve(args.worst_cases_csv, root), root),
        },
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_report(resolve(args.report, root), summary)
    print(json.dumps({"answer": "representation_win_selector_unclear", "selector_vs_static": selector_verdict}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

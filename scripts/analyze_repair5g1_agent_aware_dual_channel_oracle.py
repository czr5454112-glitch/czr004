"""Analyze Repair5G.1 agent-aware dual-channel LTM oracle headroom."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))

from create_repair5g1_agent_aware_dual_channel_candidates import build_candidates  # noqa: E402
from run_repair5g_dual_channel_probe import (  # noqa: E402
    case_key,
    dedupe_rows,
    finite,
    method_stats,
    paired_rows,
    read_jsonl,
    resolve,
    row_score,
)


DEFAULT_INPUT_JSONL = "outputs/logs/phase5p5_repair5g1_dev_probe/phase5p5_repair5g1_dev_probe.jsonl"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g1_agent_aware_dual_channel_oracle_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g1_agent_aware_dual_channel_oracle_summary.json"
DEFAULT_RANKING = "outputs/tables/phase5p5_repair5g1_dev_candidate_ranking.csv"
DEFAULT_ORACLE_BY_CASE = "outputs/tables/phase5p5_repair5g1_oracle_by_case.csv"
DEFAULT_GROUP_BEST = "outputs/tables/phase5p5_repair5g1_group_best_candidates.csv"
DEFAULT_DECISION = "outputs/reports/phase5p5_repair5g1_agent_aware_dual_channel_decision.md"

ORACLE_METHOD = "repair5g1_agent_aware_dual_channel_oracle_static_proxy"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def mean(values: list[float]) -> float | None:
    clean = [value for value in values if math.isfinite(value)]
    return statistics.mean(clean) if clean else None


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def candidate_components() -> dict[str, str]:
    return {
        candidate.runtime_method: candidate.component
        for candidate in build_candidates()
        if candidate.enable_dual_channel
    }


def synthesize_oracle_rows(
    rows: list[dict[str, Any]], candidate_methods: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_case: dict[tuple[str, int, int, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_case.setdefault(case_key(row), {})[str(row.get("method"))] = row

    oracle_rows: list[dict[str, Any]] = []
    by_case_rows: list[dict[str, Any]] = []
    for key, methods in sorted(by_case.items()):
        candidates = [methods[method] for method in candidate_methods if method in methods]
        base = methods.get("lacam_star_ltm")
        if not candidates or base is None:
            continue
        best = min(candidates, key=row_score)
        oracle = dict(best)
        oracle["method"] = ORACLE_METHOD
        oracle["repair5g_synthetic_source_method"] = best.get("method")
        oracle_rows.append(oracle)
        base_ratio = finite(base.get("sum_of_loss_ratio"))
        best_ratio = finite(best.get("sum_of_loss_ratio"))
        by_case_rows.append(
            {
                "map": key[0],
                "agents": key[1],
                "seed": key[2],
                "scen": key[3],
                "oracle_source_method": best.get("method"),
                "oracle_source_component": candidate_components().get(str(best.get("method")), ""),
                "lacam_star_ltm_success": base.get("success"),
                "oracle_success": best.get("success"),
                "lacam_star_ltm_ratio": base_ratio if math.isfinite(base_ratio) else None,
                "oracle_ratio": best_ratio if math.isfinite(best_ratio) else None,
                "oracle_delta_ratio_vs_ltm": (
                    best_ratio - base_ratio if math.isfinite(base_ratio) and math.isfinite(best_ratio) else None
                ),
            }
        )
    return oracle_rows, by_case_rows


def bootstrap_ci(values: list[float], *, samples: int = 2000, seed: int = 20260603) -> dict[str, float | int | None]:
    clean = [value for value in values if math.isfinite(value)]
    if not clean:
        return {"mean": None, "ci_low": None, "ci_high": None, "prob_mean_lt_0": None, "samples": 0}
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(samples):
        draw = [clean[rng.randrange(len(clean))] for _ in clean]
        means.append(statistics.mean(draw))
    means.sort()
    low_index = int(0.025 * (len(means) - 1))
    high_index = int(0.975 * (len(means) - 1))
    return {
        "mean": statistics.mean(clean),
        "ci_low": means[low_index],
        "ci_high": means[high_index],
        "prob_mean_lt_0": sum(1 for value in means if value < 0.0) / len(means),
        "samples": len(means),
    }


def group_best_rows(paired: list[dict[str, Any]], candidate_methods: set[str]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int, str], list[dict[str, Any]]] = {}
    for row in paired:
        method = str(row.get("contender_method"))
        if method not in candidate_methods:
            continue
        grouped.setdefault((str(row.get("map")), int(row.get("agents")), method), []).append(row)

    by_group: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for (map_name, agents, method), group in grouped.items():
        deltas = [float(row["delta_ratio"]) for row in group if row.get("delta_ratio") is not None]
        by_group.setdefault((map_name, agents), []).append(
            {
                "map": map_name,
                "agents": agents,
                "candidate_method": method,
                "component": candidate_components().get(method, ""),
                "rows": len(group),
                "better": sum(1 for row in group if row.get("contender_better")),
                "worse": sum(1 for row in group if row.get("contender_worse")),
                "mean_delta_ratio_vs_ltm": mean(deltas),
            }
        )
    out: list[dict[str, Any]] = []
    for rows in by_group.values():
        ranked = sorted(
            rows,
            key=lambda row: (
                finite(row.get("mean_delta_ratio_vs_ltm"), float("inf")),
                -int(row.get("better", 0)),
                int(row.get("worse", 0)),
                str(row.get("candidate_method")),
            ),
        )
        if ranked:
            out.append(ranked[0])
    return sorted(out, key=lambda row: (row["map"], row["agents"]))


def component_summary_rows(ranking: list[dict[str, Any]], components: dict[str, str]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in ranking:
        method = str(row["method"])
        if method not in components:
            continue
        grouped.setdefault(components[method], []).append(row)
    out: list[dict[str, Any]] = []
    for component, rows in sorted(grouped.items()):
        values = [finite(row.get("mean_delta_ratio_vs_ltm")) for row in rows]
        out.append(
            {
                "component": component,
                "candidate_count": len(rows),
                "best_mean_delta_ratio_vs_ltm": min([value for value in values if math.isfinite(value)], default=None),
                "mean_of_candidate_means": mean(values),
                "total_better": sum(int(row.get("better", 0)) for row in rows),
                "total_worse": sum(int(row.get("worse", 0)) for row in rows),
            }
        )
    return out


def cost_audit_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    dual = [
        row for row in rows
        if str(row.get("method", "")).startswith("repair5g_dual_")
        or str(row.get("method", "")).startswith("repair5g1_")
    ]
    min_costs = [finite(row.get("repair5g_min_traversal_cost")) for row in dual]
    max_costs = [finite(row.get("repair5g_max_traversal_cost")) for row in dual]
    return {
        "dual_rows": len(dual),
        "all_costs_finite": all(bool(row.get("repair5g_costs_finite", True)) for row in dual),
        "cost_bounds_respected": all(bool(row.get("repair5g_cost_bounds_respected", True)) for row in dual),
        "min_observed_cost": min([value for value in min_costs if math.isfinite(value)], default=None),
        "max_observed_cost": max([value for value in max_costs if math.isfinite(value)], default=None),
    }


def decide(summary: dict[str, Any]) -> str:
    gates = summary["gates"]
    oracle = summary["oracle_stats"]
    components = {row["component"]: row for row in summary["component_summary"]}
    if not gates["cost_bounds_respected"] or not gates["dual_c_equiv_closed"]:
        return "fix_implementation_before_science"
    oracle_mean = finite(oracle.get("mean_delta_ratio_vs_ltm"))
    c_best = finite(components.get("c_equiv", {}).get("best_mean_delta_ratio_vs_ltm"), float("inf"))
    best_non_c = min(
        [
            finite(row.get("best_mean_delta_ratio_vs_ltm"), float("inf"))
            for row in summary["component_summary"]
            if row.get("component") not in {"c_equiv", "parity", "diagnostic"}
        ],
        default=float("inf"),
    )
    if math.isfinite(oracle_mean) and oracle_mean < 0.0 and best_non_c < c_best:
        return "continue_repair5g_with_agent_aware_selector"
    if best_non_c >= c_best:
        return "continue_repair5f_static_protocol_instead"
    return "stop_repair5g_dual_channel"


def write_report(path: Path, summary: dict[str, Any], ranking: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.1 Agent-Aware Dual-Channel Oracle Report\n\n")
        handle.write("This is development/diagnostic-only evidence. It does not permit Phase5.5 or Phase6.\n\n")
        handle.write("## Gates\n\n")
        for key, value in summary["gates"].items():
            handle.write(f"- {key}: `{value}`\n")
        handle.write("\n## Oracle\n\n")
        for key, value in summary["oracle_stats"].items():
            handle.write(f"- {key}: `{value}`\n")
        handle.write(f"- bootstrap_ci: `{summary['oracle_bootstrap_ci']}`\n\n")
        handle.write("## Components\n\n")
        handle.write("| component | candidates | best mean delta | mean of means | total better | total worse |\n")
        handle.write("|---|---:|---:|---:|---:|---:|\n")
        for row in summary["component_summary"]:
            handle.write(
                f"| {row['component']} | {row['candidate_count']} | {row['best_mean_delta_ratio_vs_ltm']} | "
                f"{row['mean_of_candidate_means']} | {row['total_better']} | {row['total_worse']} |\n"
            )
        handle.write("\n## Candidate Ranking\n\n")
        handle.write("| rank | method | component | better | equal | worse | mean delta ratio vs LTM |\n")
        handle.write("|---:|---|---|---:|---:|---:|---:|\n")
        for index, row in enumerate(ranking[:25], start=1):
            handle.write(
                f"| {index} | `{row['method']}` | {row.get('component', '')} | {row.get('better')} | "
                f"{row.get('equal')} | {row.get('worse')} | {row.get('mean_delta_ratio_vs_ltm')} |\n"
            )


def write_decision(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    decision = summary["decision"]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5G.1 Agent-Aware Dual-Channel Decision\n\n")
        handle.write(f"Decision: `{decision}`\n\n")
        handle.write("This decision is diagnostic-only. `phase5p5_allowed=false` and `phase6_allowed=false` remain mandatory.\n\n")
        if decision == "continue_repair5g_with_agent_aware_selector":
            handle.write("A non-leaky agent-aware or flow-shield family beat the C-only diagnostic headroom. Plan a selector diagnostic without using these IDs as final evidence.\n")
        elif decision == "continue_repair5f_static_protocol_instead":
            handle.write("C-equivalent scalar candidates dominate the G1 lattice. Continue the Repair5F static/support protocol instead of promoting dual-channel flow.\n")
        elif decision == "fix_implementation_before_science":
            handle.write("Fix C-equivalence, parity, or cost-bound implementation gates before running or interpreting larger probes.\n")
        else:
            handle.write("Stop Repair5G dual-channel flow: C-equivalence closed, but agent-aware/flow-shield candidates still do not show useful headroom.\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, default=Path(DEFAULT_INPUT_JSONL))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--ranking-csv", type=Path, default=Path(DEFAULT_RANKING))
    parser.add_argument("--oracle-by-case-csv", type=Path, default=Path(DEFAULT_ORACLE_BY_CASE))
    parser.add_argument("--group-best-csv", type=Path, default=Path(DEFAULT_GROUP_BEST))
    parser.add_argument("--decision-report", type=Path, default=Path(DEFAULT_DECISION))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    input_jsonl = resolve(args.input_jsonl, root)
    rows = dedupe_rows(read_jsonl(input_jsonl))
    components = candidate_components()
    candidate_methods = set(components)
    oracle_rows, oracle_by_case = synthesize_oracle_rows(rows, candidate_methods)
    all_rows = dedupe_rows([*rows, *oracle_rows])
    paired = paired_rows(all_rows)
    stats = method_stats(paired)
    ranking = [
        {**stats[method], "component": components.get(method, "")}
        for method in stats
        if method in candidate_methods
        or method in {ORACLE_METHOD, "repair5g_random_dual_candidate_diagnostic", "repair5g_shuffled_goal_progress_diagnostic"}
    ]
    ranking.sort(
        key=lambda row: (
            finite(row.get("mean_delta_ratio_vs_ltm"), float("inf")),
            -int(row.get("better", 0)),
            int(row.get("worse", 0)),
            str(row.get("method")),
        )
    )
    group_best = group_best_rows(paired, candidate_methods)
    component_summary = component_summary_rows(ranking, components)
    oracle_stats = stats.get(
        ORACLE_METHOD,
        {"rows": 0, "better": 0, "equal": 0, "worse": 0, "mean_delta_ratio_vs_ltm": None},
    )
    oracle_deltas = [
        float(row["delta_ratio"])
        for row in paired
        if row.get("contender_method") == ORACLE_METHOD and row.get("delta_ratio") is not None
    ]
    cost_summary = cost_audit_summary(rows)
    gates = {
        "dual_c_equiv_closed": any(row.get("component") == "c_equiv" for row in component_summary),
        "cost_bounds_respected": cost_summary["cost_bounds_respected"],
        "dual_channel_oracle_better_gt_worse": int(oracle_stats.get("better", 0)) > int(oracle_stats.get("worse", 0)),
        "dual_channel_oracle_mean_delta_ratio_vs_ltm_lt_0": finite(oracle_stats.get("mean_delta_ratio_vs_ltm")) < 0.0,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    summary = {
        "schema_version": "phase5p5_repair5g1_agent_aware_dual_channel_oracle_summary_v1",
        "created_at": datetime.now().isoformat(),
        "input_jsonl": str(input_jsonl.relative_to(root)) if input_jsonl.is_relative_to(root) else str(input_jsonl),
        "row_count": len(rows),
        "oracle_case_count": len(oracle_by_case),
        "candidate_methods": sorted(candidate_methods),
        "oracle_stats": oracle_stats,
        "oracle_bootstrap_ci": bootstrap_ci(oracle_deltas),
        "component_summary": component_summary,
        "cost_audit": cost_summary,
        "gates": gates,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    summary["decision"] = decide(summary)

    write_csv(resolve(args.ranking_csv, root), ranking, ["method", "component", "rows", "better", "equal", "worse", "mean_delta_ratio_vs_ltm"])
    write_csv(resolve(args.oracle_by_case_csv, root), oracle_by_case, list(oracle_by_case[0].keys()) if oracle_by_case else [])
    write_csv(resolve(args.group_best_csv, root), group_best, list(group_best[0].keys()) if group_best else [])
    summary_path = resolve(args.summary_json, root)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(resolve(args.report, root), summary, ranking)
    write_decision(resolve(args.decision_report, root), summary)
    print(json.dumps({"rows": len(rows), "oracle_cases": len(oracle_by_case), "decision": summary["decision"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

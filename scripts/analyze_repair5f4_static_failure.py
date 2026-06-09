"""Autopsy the Repair5F.4 fresh-ID static UpdateParams failure.

This is diagnostic-only. It consumes the already completed F4-A validation
tables and explains where the locked c100_b100_w075_d090 rule failed without
selecting, exporting, or promoting a new candidate.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import subprocess
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_SUMMARY_JSON = "outputs/reports/phase5p5_repair5f4_static_updateparams_validation_summary.json"
DEFAULT_VALIDATION_REPORT = "outputs/reports/phase5p5_repair5f4_static_updateparams_validation_report.md"
DEFAULT_PAIRED_CSV = "outputs/tables/phase5p5_repair5f4_static_updateparams_validation_paired.csv"
DEFAULT_BY_GROUP_CSV = "outputs/tables/phase5p5_repair5f4_static_updateparams_validation_by_map_agent.csv"
DEFAULT_COMPONENT_CSV = "outputs/tables/phase5p5_repair5f4_static_updateparams_validation_component_ablation.csv"
DEFAULT_FRESHNESS_JSON = (
    "outputs/reports/phase5p5_repair5f4_static_updateparams_validation_freshness_audit_summary.json"
)

DEFAULT_REPORT = "outputs/reports/phase5p5_repair5f4_static_failure_autopsy.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5f4_static_failure_autopsy_summary.json"
DEFAULT_CASES = "outputs/tables/phase5p5_repair5f4_static_failure_cases.csv"
DEFAULT_GROUPS = "outputs/tables/phase5p5_repair5f4_static_failure_by_group.csv"
DEFAULT_COMPONENT_DOMINANCE = "outputs/tables/phase5p5_repair5f4_component_dominance.csv"

LOCKED_METHOD = "repair5f_static_c100_b100_w075_d090"
RANDOM_METHOD = "repair5f_f4_deterministic_random_candidate_diagnostic"
E5_METHOD = "repair5e5_crossfold_utility_reranker"
E5_SHUFFLED_METHOD = "repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic"
COMPONENT_METHODS = [
    "repair5f_static_c100_b100_w075_d100",
    "repair5f_static_c100_b100_w100_d090",
    "repair5f_static_c100_b100_w100_d095",
    "repair5f_static_c100_b100_w075_d095",
    LOCKED_METHOD,
]
METHOD_LABELS = {
    "repair5f_static_c100_b100_w075_d100": "wait 0.75 only",
    "repair5f_static_c100_b100_w100_d090": "decay 0.90 only",
    "repair5f_static_c100_b100_w100_d095": "decay 0.95 only",
    "repair5f_static_c100_b100_w075_d095": "wait 0.75 + decay 0.95",
    LOCKED_METHOD: "locked wait 0.75 + decay 0.90",
    RANDOM_METHOD: "deterministic random candidate diagnostic",
    E5_METHOD: "Repair5E5 real diagnostic",
    E5_SHUFFLED_METHOD: "Repair5E5 shuffled diagnostic",
}


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


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def dirty_state(root: Path) -> str:
    status = git_value(["status", "--short"], root)
    if not status:
        return "clean"
    tracked = [line for line in status.splitlines() if not line.startswith("??")]
    untracked = [line for line in status.splitlines() if line.startswith("??")]
    if tracked and untracked:
        return "tracked-dirty_untracked-present"
    if tracked:
        return "tracked-dirty"
    return "untracked-present"


def number(value: Any, default: float = math.nan) -> float:
    if value is None or isinstance(value, bool):
        return default
    text = str(value).strip()
    if not text:
        return default
    try:
        out = float(text)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def mean(values: list[float]) -> float | None:
    clean = [float(value) for value in values if math.isfinite(float(value))]
    return statistics.mean(clean) if clean else None


def median(values: list[float]) -> float | None:
    clean = [float(value) for value in values if math.isfinite(float(value))]
    return statistics.median(clean) if clean else None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def case_key(row: dict[str, Any]) -> tuple[str, int, int]:
    return (str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)))


def group_key(row: dict[str, Any]) -> tuple[str, int]:
    return (str(row.get("map")), int(number(row.get("agents"), 0)))


def bootstrap(values: list[float], seed: int = 54141, samples: int = 5000) -> dict[str, Any]:
    clean = [float(value) for value in values if math.isfinite(float(value))]
    if not clean:
        return {"mean": None, "ci95": [None, None], "probability_mean_delta_lt_0": None}
    rng = random.Random(seed)
    draws: list[float] = []
    n = len(clean)
    for _ in range(samples):
        draws.append(sum(clean[rng.randrange(n)] for _ in range(n)) / n)
    draws.sort()
    lo = draws[int(0.025 * (samples - 1))]
    hi = draws[int(0.975 * (samples - 1))]
    return {
        "mean": statistics.mean(clean),
        "ci95": [lo, hi],
        "probability_mean_delta_lt_0": sum(1 for value in draws if value < 0.0) / samples,
    }


def metric_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = [number(row.get("delta_ratio_vs_ltm")) for row in rows]
    deltas = [value for value in deltas if math.isfinite(value)]
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[group_key(row)].append(row)
    success_regressions = sum(
        1 for row in rows if boolish(row.get("ltm_success")) and not boolish(row.get("success"))
    )
    success_improvements = sum(
        1 for row in rows if boolish(row.get("success")) and not boolish(row.get("ltm_success"))
    )
    boot = bootstrap(deltas)
    return {
        "rows": len(rows),
        "better": sum(1 for value in deltas if value < -1.0e-12),
        "equal": sum(1 for value in deltas if abs(value) <= 1.0e-12),
        "worse": sum(1 for value in deltas if value > 1.0e-12),
        "mean_delta_ratio_vs_ltm": mean(deltas),
        "median_delta_ratio_vs_ltm": median(deltas),
        "bootstrap_95ci_mean_delta_ratio_vs_ltm": boot["ci95"],
        "bootstrap_probability_mean_delta_lt_0": boot["probability_mean_delta_lt_0"],
        "ratio_worse_than_ltm_groups": sum(
            1
            for items in grouped.values()
            if (mean([number(item.get("delta_ratio_vs_ltm")) for item in items]) or 0.0) > 1.0e-12
        ),
        "success_regressions": success_regressions,
        "success_improvements": success_improvements,
        "success_worse_than_ltm_groups": sum(
            1
            for items in grouped.values()
            if sum(boolish(item.get("ltm_success")) and not boolish(item.get("success")) for item in items)
            > sum(boolish(item.get("success")) and not boolish(item.get("ltm_success")) for item in items)
        ),
    }


def by_method(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        out[str(row.get("method", ""))].append(row)
    return dict(out)


def build_failure_cases(main_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in main_rows:
        delta = number(row.get("delta_ratio_vs_ltm"))
        if delta > 1.0e-12:
            classification = "worse"
        elif delta < -1.0e-12:
            classification = "better"
        else:
            classification = "equal"
        out.append(
            {
                "map": row.get("map", ""),
                "agents": int(number(row.get("agents"), 0)),
                "seed": int(number(row.get("seed"), 0)),
                "scen": row.get("scen", ""),
                "method": LOCKED_METHOD,
                "classification": classification,
                "success": boolish(row.get("success")),
                "ltm_success": boolish(row.get("ltm_success")),
                "success_regression": boolish(row.get("ltm_success")) and not boolish(row.get("success")),
                "sum_of_loss_ratio": number(row.get("sum_of_loss_ratio")),
                "ltm_sum_of_loss_ratio": number(row.get("ltm_sum_of_loss_ratio")),
                "delta_ratio_vs_ltm": delta,
                "expanded_delta_vs_ltm": number(row.get("expanded_delta_vs_ltm")),
                "low_level_pibt_delta_vs_ltm": number(row.get("low_level_pibt_delta_vs_ltm")),
                "ttfs_delta_vs_ltm": number(row.get("ttfs_delta_vs_ltm")),
            }
        )
    out.sort(key=lambda item: (-number(item["delta_ratio_vs_ltm"], 0.0), item["map"], item["agents"], item["seed"]))
    return out


def build_group_rows(rows_by_method: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for method in sorted(rows_by_method):
        if method not in {LOCKED_METHOD, RANDOM_METHOD, E5_METHOD, E5_SHUFFLED_METHOD, *COMPONENT_METHODS}:
            continue
        grouped: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
        for row in rows_by_method[method]:
            grouped[group_key(row)].append(row)
        for (map_name, agents), items in sorted(grouped.items()):
            metrics = metric_rows(items)
            equal_share = metrics["equal"] / metrics["rows"] if metrics["rows"] else 0.0
            worse_share = metrics["worse"] / metrics["rows"] if metrics["rows"] else 0.0
            out.append(
                {
                    "method": method,
                    "label": METHOD_LABELS.get(method, method),
                    "map": map_name,
                    "agents": agents,
                    "rows": metrics["rows"],
                    "better": metrics["better"],
                    "equal": metrics["equal"],
                    "worse": metrics["worse"],
                    "mean_delta_ratio_vs_ltm": metrics["mean_delta_ratio_vs_ltm"],
                    "median_delta_ratio_vs_ltm": metrics["median_delta_ratio_vs_ltm"],
                    "success_regressions": metrics["success_regressions"],
                    "success_improvements": metrics["success_improvements"],
                    "equal_share": equal_share,
                    "worse_share": worse_share,
                    "mostly_no_effect": equal_share >= 0.80,
                }
            )
    out.sort(
        key=lambda item: (
            0 if item["method"] == LOCKED_METHOD else 1,
            -number(item["mean_delta_ratio_vs_ltm"], 0.0),
            item["method"],
            item["map"],
            item["agents"],
        )
    )
    return out


def pairwise_component_matrix(rows_by_method: dict[str, list[dict[str, str]]]) -> dict[str, dict[str, dict[str, int]]]:
    by_case_method: dict[tuple[str, int, int], dict[str, dict[str, str]]] = defaultdict(dict)
    for method in COMPONENT_METHODS:
        for row in rows_by_method.get(method, []):
            by_case_method[case_key(row)][method] = row
    matrix: dict[str, dict[str, dict[str, int]]] = {}
    for left in COMPONENT_METHODS:
        matrix[left] = {}
        for right in COMPONENT_METHODS:
            if left == right:
                continue
            wins = ties = losses = compared = 0
            for methods in by_case_method.values():
                if left not in methods or right not in methods:
                    continue
                compared += 1
                left_delta = number(methods[left].get("delta_ratio_vs_ltm"), 0.0)
                right_delta = number(methods[right].get("delta_ratio_vs_ltm"), 0.0)
                if left_delta < right_delta - 1.0e-12:
                    wins += 1
                elif left_delta > right_delta + 1.0e-12:
                    losses += 1
                else:
                    ties += 1
            matrix[left][right] = {"compared": compared, "wins": wins, "ties": ties, "losses": losses}
    return matrix


def build_component_rows(rows_by_method: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    matrix = pairwise_component_matrix(rows_by_method)
    out: list[dict[str, Any]] = []
    for method in COMPONENT_METHODS:
        rows = rows_by_method.get(method, [])
        metrics = metric_rows(rows)
        pairwise = matrix.get(method, {})
        pairwise_wins = sum(item["wins"] for item in pairwise.values())
        pairwise_losses = sum(item["losses"] for item in pairwise.values())
        out.append(
            {
                "candidate_method": method,
                "candidate_id": method.replace("repair5f_static_", ""),
                "label": METHOD_LABELS.get(method, method),
                "rows": metrics["rows"],
                "better": metrics["better"],
                "equal": metrics["equal"],
                "worse": metrics["worse"],
                "mean_delta_ratio_vs_ltm": metrics["mean_delta_ratio_vs_ltm"],
                "median_delta_ratio_vs_ltm": metrics["median_delta_ratio_vs_ltm"],
                "bootstrap_95ci_mean_delta_ratio_vs_ltm": json.dumps(
                    metrics["bootstrap_95ci_mean_delta_ratio_vs_ltm"]
                ),
                "bootstrap_probability_mean_delta_lt_0": metrics["bootstrap_probability_mean_delta_lt_0"],
                "ratio_worse_than_ltm_groups": metrics["ratio_worse_than_ltm_groups"],
                "success_worse_than_ltm_groups": metrics["success_worse_than_ltm_groups"],
                "pairwise_total_wins": pairwise_wins,
                "pairwise_total_losses": pairwise_losses,
                "pairwise_beats_minus_losses": pairwise_wins - pairwise_losses,
                "pairwise_matrix": json.dumps(pairwise, sort_keys=True),
            }
        )
    out.sort(
        key=lambda item: (
            number(item["mean_delta_ratio_vs_ltm"], 0.0),
            -int(item["better"]),
            int(item["worse"]),
            item["candidate_method"],
        )
    )
    return out


def concentration_summary(main_rows: list[dict[str, str]]) -> dict[str, Any]:
    total_worse = sum(1 for row in main_rows if number(row.get("delta_ratio_vs_ltm")) > 1.0e-12)
    by_map: dict[str, Counter[str]] = defaultdict(Counter)
    for row in main_rows:
        delta = number(row.get("delta_ratio_vs_ltm"))
        bucket = "worse" if delta > 1.0e-12 else "better" if delta < -1.0e-12 else "equal"
        by_map[str(row.get("map", ""))][bucket] += 1
    out = {}
    for map_name, counts in sorted(by_map.items()):
        rows = sum(counts.values())
        out[map_name] = {
            "rows": rows,
            "better": counts["better"],
            "equal": counts["equal"],
            "worse": counts["worse"],
            "worse_share_of_map": counts["worse"] / rows if rows else 0.0,
            "worse_share_of_all_worse": counts["worse"] / total_worse if total_worse else 0.0,
            "mostly_no_effect": counts["equal"] / rows >= 0.80 if rows else False,
        }
    return out


def comparison_summary(rows_by_method: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    locked_metrics = metric_rows(rows_by_method.get(LOCKED_METHOD, []))
    locked_mean = number(locked_metrics.get("mean_delta_ratio_vs_ltm"))
    for method in [RANDOM_METHOD, E5_METHOD, E5_SHUFFLED_METHOD]:
        rows = rows_by_method.get(method, [])
        if not rows:
            out[method] = {"available": False}
            continue
        metrics = metric_rows(rows)
        mean_delta = number(metrics.get("mean_delta_ratio_vs_ltm"))
        out[method] = {
            "available": True,
            "label": METHOD_LABELS.get(method, method),
            "metrics": metrics,
            "locked_mean_minus_comparator_mean": locked_mean - mean_delta,
            "locked_beats_comparator_on_mean": locked_mean < mean_delta,
        }
    return out


def build_summary(
    *,
    root: Path,
    validation_summary: dict[str, Any],
    freshness_summary: dict[str, Any],
    paired: list[dict[str, str]],
    group_rows: list[dict[str, Any]],
    component_rows: list[dict[str, Any]],
    report: Path,
    summary_path: Path,
    cases_path: Path,
    groups_path: Path,
    component_path: Path,
) -> dict[str, Any]:
    rows_by_method = by_method(paired)
    main_rows = rows_by_method.get(LOCKED_METHOD, [])
    main_metrics = metric_rows(main_rows)
    main_group_rows = [row for row in group_rows if row["method"] == LOCKED_METHOD]
    worst_groups = sorted(main_group_rows, key=lambda row: number(row["mean_delta_ratio_vs_ltm"], 0.0), reverse=True)
    best_groups = sorted(main_group_rows, key=lambda row: number(row["mean_delta_ratio_vs_ltm"], 0.0))
    comparisons = comparison_summary(rows_by_method)
    component_best = component_rows[0] if component_rows else {}
    return {
        "schema_version": "phase5p5_repair5f4_static_failure_autopsy_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "locked_method": LOCKED_METHOD,
        "locked_candidate_generalized": False,
        "f4_outcomes_used_for_retuning": False,
        "source_validation_summary_json": validation_summary.get("summary_json") or DEFAULT_SUMMARY_JSON,
        "source_validation_report": DEFAULT_VALIDATION_REPORT,
        "freshness_and_parity_controls": {
            "force_additive_parity_exact": freshness_summary.get("force_additive_parity_exact"),
            "exact_additive_candidate_parity_exact": freshness_summary.get("exact_additive_candidate_parity_exact"),
            "laur_disable_parity_exact": freshness_summary.get("laur_disable_parity_exact"),
            "laur_force_additive_direct_parity_exact": freshness_summary.get("laur_force_additive_direct_parity_exact"),
            "support_validation_overlap_count": freshness_summary.get("support_validation_overlap_count"),
            "f2f3_holdout_validation_overlap_count": freshness_summary.get("f2f3_holdout_validation_overlap_count"),
        },
        "locked_metrics": main_metrics,
        "locked_failure_concentration": concentration_summary(main_rows),
        "worst_groups": worst_groups[:6],
        "best_groups": best_groups[:6],
        "component_best_by_mean": component_best,
        "component_rows": component_rows,
        "component_pairwise_matrix": pairwise_component_matrix(rows_by_method),
        "diagnostic_comparisons": comparisons,
        "warehouse_mostly_no_effect": all(
            row["mostly_no_effect"] for row in main_group_rows if str(row["map"]).startswith("warehouse")
        ),
        "interpretation": (
            "F4-A was a clean diagnostic failure, not an engineering failure. Coverage, freshness, and parity "
            "controls passed, but the locked c100_b100_w075_d090 rule did not generalize and did not beat the "
            "deterministic random candidate diagnostic on mean delta. Component evidence points to decay 0.90 "
            "and global static selection as plausible causes, but those observations are diagnostic-only."
        ),
        "outputs": {
            "report": rel(report, root),
            "summary_json": rel(summary_path, root),
            "failure_cases_csv": rel(cases_path, root),
            "failure_by_group_csv": rel(groups_path, root),
            "component_dominance_csv": rel(component_path, root),
        },
    }


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    locked = summary["locked_metrics"]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F.4 Static Failure Autopsy\n\n")
        handle.write("Diagnostic-only autopsy of the fresh-ID F4-A static UpdateParams failure.\n\n")
        handle.write("## Boundary\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- f4_outcomes_used_for_retuning: `false`\n\n")
        handle.write("## Locked Rule\n\n")
        handle.write(f"- method: `{summary['locked_method']}`\n")
        handle.write(f"- rows: `{locked['rows']}`\n")
        handle.write(f"- better / equal / worse: `{locked['better']} / {locked['equal']} / {locked['worse']}`\n")
        handle.write(f"- mean_delta_ratio_vs_ltm: `{locked['mean_delta_ratio_vs_ltm']}`\n")
        handle.write(
            f"- bootstrap_95ci_mean_delta_ratio_vs_ltm: `{locked['bootstrap_95ci_mean_delta_ratio_vs_ltm']}`\n"
        )
        handle.write(f"- ratio_worse_than_ltm_groups: `{locked['ratio_worse_than_ltm_groups']}`\n")
        handle.write(f"- success_worse_than_ltm_groups: `{locked['success_worse_than_ltm_groups']}`\n\n")
        handle.write("## Freshness And Parity\n\n")
        for key, value in summary["freshness_and_parity_controls"].items():
            handle.write(f"- {key}: `{value}`\n")
        handle.write("\n## Worst Groups\n\n")
        handle.write("| map | agents | rows | better | equal | worse | mean delta | success regressions |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in summary["worst_groups"]:
            handle.write(
                f"| {row['map']} | {row['agents']} | {row['rows']} | {row['better']} | {row['equal']} | "
                f"{row['worse']} | {row['mean_delta_ratio_vs_ltm']} | {row['success_regressions']} |\n"
            )
        handle.write("\n## Best Groups\n\n")
        handle.write("| map | agents | rows | better | equal | worse | mean delta |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|\n")
        for row in summary["best_groups"]:
            handle.write(
                f"| {row['map']} | {row['agents']} | {row['rows']} | {row['better']} | {row['equal']} | "
                f"{row['worse']} | {row['mean_delta_ratio_vs_ltm']} |\n"
            )
        handle.write("\n## Component Dominance\n\n")
        handle.write("| candidate | rows | better | equal | worse | mean delta | p(mean < 0) | pairwise W-L |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for row in summary["component_rows"]:
            handle.write(
                f"| `{row['candidate_id']}` | {row['rows']} | {row['better']} | {row['equal']} | "
                f"{row['worse']} | {row['mean_delta_ratio_vs_ltm']} | "
                f"{row['bootstrap_probability_mean_delta_lt_0']} | {row['pairwise_beats_minus_losses']} |\n"
            )
        handle.write("\n## Diagnostic Comparisons\n\n")
        for method, item in summary["diagnostic_comparisons"].items():
            if not item.get("available"):
                handle.write(f"- `{method}`: unavailable\n")
                continue
            metrics = item["metrics"]
            handle.write(
                f"- `{method}`: {metrics['better']} / {metrics['equal']} / {metrics['worse']}, "
                f"mean `{metrics['mean_delta_ratio_vs_ltm']}`, "
                f"locked_beats_on_mean=`{item['locked_beats_comparator_on_mean']}`\n"
            )
        handle.write("\n## Interpretation\n\n")
        handle.write(summary["interpretation"] + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation-summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--validation-report", type=Path, default=Path(DEFAULT_VALIDATION_REPORT))
    parser.add_argument("--paired-csv", type=Path, default=Path(DEFAULT_PAIRED_CSV))
    parser.add_argument("--by-map-agent-csv", type=Path, default=Path(DEFAULT_BY_GROUP_CSV))
    parser.add_argument("--component-ablation-csv", type=Path, default=Path(DEFAULT_COMPONENT_CSV))
    parser.add_argument("--freshness-summary-json", type=Path, default=Path(DEFAULT_FRESHNESS_JSON))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--failure-cases-csv", type=Path, default=Path(DEFAULT_CASES))
    parser.add_argument("--failure-by-group-csv", type=Path, default=Path(DEFAULT_GROUPS))
    parser.add_argument("--component-dominance-csv", type=Path, default=Path(DEFAULT_COMPONENT_DOMINANCE))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    validation_summary = read_json(resolve(args.validation_summary_json, root))
    freshness_summary = read_json(resolve(args.freshness_summary_json, root))
    paired_path = resolve(args.paired_csv, root)
    report = resolve(args.report, root)
    summary_path = resolve(args.summary_json, root)
    cases_path = resolve(args.failure_cases_csv, root)
    groups_path = resolve(args.failure_by_group_csv, root)
    component_path = resolve(args.component_dominance_csv, root)

    # Read these required inputs even though the detailed autopsy is rebuilt
    # from paired rows; their existence is part of the F4 evidence chain.
    for path in [
        resolve(args.validation_report, root),
        resolve(args.by_map_agent_csv, root),
        resolve(args.component_ablation_csv, root),
    ]:
        if not path.exists():
            raise FileNotFoundError(path)

    paired = read_csv(paired_path)
    rows_by_method = by_method(paired)
    main_rows = rows_by_method.get(LOCKED_METHOD, [])
    if not main_rows:
        raise ValueError(f"missing locked method rows: {LOCKED_METHOD}")

    failure_cases = build_failure_cases(main_rows)
    group_rows = build_group_rows(rows_by_method)
    component_rows = build_component_rows(rows_by_method)
    summary = build_summary(
        root=root,
        validation_summary=validation_summary,
        freshness_summary=freshness_summary,
        paired=paired,
        group_rows=group_rows,
        component_rows=component_rows,
        report=report,
        summary_path=summary_path,
        cases_path=cases_path,
        groups_path=groups_path,
        component_path=component_path,
    )

    write_csv(
        cases_path,
        failure_cases,
        [
            "map",
            "agents",
            "seed",
            "scen",
            "method",
            "classification",
            "success",
            "ltm_success",
            "success_regression",
            "sum_of_loss_ratio",
            "ltm_sum_of_loss_ratio",
            "delta_ratio_vs_ltm",
            "expanded_delta_vs_ltm",
            "low_level_pibt_delta_vs_ltm",
            "ttfs_delta_vs_ltm",
        ],
    )
    write_csv(
        groups_path,
        group_rows,
        [
            "method",
            "label",
            "map",
            "agents",
            "rows",
            "better",
            "equal",
            "worse",
            "mean_delta_ratio_vs_ltm",
            "median_delta_ratio_vs_ltm",
            "success_regressions",
            "success_improvements",
            "equal_share",
            "worse_share",
            "mostly_no_effect",
        ],
    )
    write_csv(
        component_path,
        component_rows,
        [
            "candidate_method",
            "candidate_id",
            "label",
            "rows",
            "better",
            "equal",
            "worse",
            "mean_delta_ratio_vs_ltm",
            "median_delta_ratio_vs_ltm",
            "bootstrap_95ci_mean_delta_ratio_vs_ltm",
            "bootstrap_probability_mean_delta_lt_0",
            "ratio_worse_than_ltm_groups",
            "success_worse_than_ltm_groups",
            "pairwise_total_wins",
            "pairwise_total_losses",
            "pairwise_beats_minus_losses",
            "pairwise_matrix",
        ],
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    print(json.dumps({"summary_json": rel(summary_path, root), "report": rel(report, root)}, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Shared experiment aggregation, paired tests, and P&E summaries."""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import Any

from .schema import normalize_run_row


MAP_ORDER = [
    "empty-32-32",
    "empty-48-48",
    "random-32-32-20",
    "maze-32-32-4",
    "random-64-64-20",
    "room-64-64-8",
    "warehouse-10-20-10-2-1",
    "warehouse-10-20-10-2-2",
]


def _map_sort_key(map_name: str) -> tuple[int, str]:
    return (MAP_ORDER.index(map_name) if map_name in MAP_ORDER else 999, map_name)


def _mean(values: Sequence[float]) -> float:
    return statistics.mean(values) if values else math.nan


def _median(values: Sequence[float]) -> float:
    return statistics.median(values) if values else math.nan


def _stdev(values: Sequence[float]) -> float:
    return statistics.stdev(values) if len(values) > 1 else (0.0 if values else math.nan)


def summarize_by_group(rows: Iterable[dict]) -> list[dict]:
    grouped: dict[tuple[str, int, str], list[dict]] = defaultdict(list)
    for row in rows:
        normalized = normalize_run_row(row)
        grouped[(normalized["map"], int(normalized["agents"]), normalized["method"])].append(normalized)

    out: list[dict] = []
    for (map_name, agents, method), group in sorted(
        grouped.items(), key=lambda item: (_map_sort_key(item[0][0]), item[0][1], item[0][2])
    ):
        ratios = [
            float(row["sum_of_loss_ratio"])
            for row in group
            if row.get("success") and row.get("sum_of_loss_ratio") is not None
        ]
        runtimes = [float(row["runtime_ms"]) for row in group if row.get("runtime_ms") is not None]
        ttfs = [
            float(row["time_to_first_solution_ms"])
            for row in group
            if row.get("time_to_first_solution_ms") is not None
        ]
        high_level = [
            float(row["high_level_expansions"])
            for row in group
            if row.get("high_level_expansions") is not None
        ]
        expanded = [
            float(row["expanded_nodes"])
            for row in group
            if row.get("expanded_nodes") is not None
        ]
        pibt = [
            float(row["low_level_pibt_calls"])
            for row in group
            if row.get("low_level_pibt_calls") is not None
        ]
        returned = [
            int(row["returned_solutions_count"])
            for row in group
            if row.get("returned_solutions_count") is not None
        ]
        success_count = sum(1 for row in group if row.get("success"))
        out.append(
            {
                "map": map_name,
                "agents": agents,
                "method": method,
                "runs": len(group),
                "successes": success_count,
                "success_rate": success_count / len(group) if group else 0.0,
                "ratio_mean": _mean(ratios),
                "ratio_median": _median(ratios),
                "ratio_std": _stdev(ratios),
                "runtime_ms_mean": _mean(runtimes),
                "time_to_first_solution_ms_mean": _mean(ttfs),
                "returned_solutions_count_mean": _mean(returned),
                "expanded_nodes_mean": _mean(expanded),
                "high_level_expansions_mean": _mean(high_level),
                "low_level_pibt_calls_mean": _mean(pibt),
            }
        )
    return out


def paired_rows(
    rows: Iterable[dict],
    baseline: str,
    contender: str,
    key_fields: tuple[str, ...] = ("map", "agents", "seed", "scen"),
) -> list[dict]:
    by_key: dict[tuple[Any, ...], dict[str, dict]] = defaultdict(dict)
    for row in rows:
        normalized = normalize_run_row(row)
        if not normalized.get("success") or normalized.get("sum_of_loss_ratio") is None:
            continue
        if normalized.get("method") not in {baseline, contender}:
            continue
        key = tuple(normalized.get(field) for field in key_fields)
        by_key[key][normalized["method"]] = normalized

    pairs: list[dict] = []
    for key, methods in sorted(by_key.items()):
        if baseline not in methods or contender not in methods:
            continue
        base_row = methods[baseline]
        cont_row = methods[contender]
        base_ratio = float(base_row["sum_of_loss_ratio"])
        cont_ratio = float(cont_row["sum_of_loss_ratio"])
        delta = cont_ratio - base_ratio
        relative_improvement = (base_ratio - cont_ratio) / base_ratio if base_ratio else math.nan
        out = {field: value for field, value in zip(key_fields, key)}
        out.update(
            {
                "baseline_method": baseline,
                "contender_method": contender,
                "baseline_ratio": base_ratio,
                "contender_ratio": cont_ratio,
                "delta_ratio": delta,
                "relative_improvement": relative_improvement,
                "contender_better": cont_ratio < base_ratio,
            }
        )
        pairs.append(out)
    return pairs


def _binomial_two_sided_pvalue(successes: int, trials: int) -> float | None:
    if trials <= 0:
        return None
    try:
        from scipy.stats import binomtest

        return float(binomtest(successes, trials, p=0.5, alternative="two-sided").pvalue)
    except Exception:
        probability = 0.0
        observed = min(successes, trials - successes)
        for k in range(0, observed + 1):
            probability += math.comb(trials, k) * (0.5**trials)
        return min(1.0, 2.0 * probability)


def summarize_paired_methods(rows: Iterable[dict], baseline: str, contender: str) -> dict:
    pairs = paired_rows(rows, baseline, contender)
    if not pairs:
        return {
            "paired_successes": 0,
            "contender_better": 0,
            "baseline_ratio_mean": math.nan,
            "contender_ratio_mean": math.nan,
            "relative_ratio_improvement": math.nan,
            "sign_test_pvalue": None,
        }

    base_ratios = [float(row["baseline_ratio"]) for row in pairs]
    cont_ratios = [float(row["contender_ratio"]) for row in pairs]
    wins = sum(1 for row in pairs if row["contender_better"])
    base_mean = statistics.mean(base_ratios)
    cont_mean = statistics.mean(cont_ratios)
    return {
        "paired_successes": len(pairs),
        "contender_better": wins,
        "baseline_ratio_mean": base_mean,
        "contender_ratio_mean": cont_mean,
        "relative_ratio_improvement": (base_mean - cont_mean) / base_mean if base_mean else math.nan,
        "sign_test_pvalue": _binomial_two_sided_pvalue(wins, len(pairs)),
    }


def phase1a_gate(rows: Iterable[dict], baseline: str = "lacam_star", contender: str = "lacam_star_ltm") -> dict:
    summary = summarize_by_group(row for row in rows if int(row.get("agents", 0)) <= 2000)
    by_key: dict[tuple[str, int], dict[str, dict]] = defaultdict(dict)
    for row in summary:
        by_key[(row["map"], int(row["agents"]))][row["method"]] = row

    groups = []
    for (map_name, agents), methods in sorted(by_key.items(), key=lambda item: (_map_sort_key(item[0][0]), item[0][1])):
        if baseline not in methods or contender not in methods:
            continue
        base_ratio = float(methods[baseline]["ratio_mean"])
        cont_ratio = float(methods[contender]["ratio_mean"])
        if not math.isfinite(base_ratio) or not math.isfinite(cont_ratio):
            continue
        groups.append(
            {
                "map": map_name,
                "agents": agents,
                "baseline_ratio_mean": base_ratio,
                "contender_ratio_mean": cont_ratio,
                "contender_better": cont_ratio < base_ratio,
            }
        )

    maps = sorted({group["map"] for group in groups}, key=_map_sort_key)
    maps_passing = 0
    for map_name in maps:
        map_groups = [group for group in groups if group["map"] == map_name]
        if map_groups and sum(1 for group in map_groups if group["contender_better"]) / len(map_groups) >= 0.70:
            maps_passing += 1

    group_wins = sum(1 for group in groups if group["contender_better"])
    return {
        "groups": len(groups),
        "group_wins": group_wins,
        "maps": len(maps),
        "maps_passing_70pct": maps_passing,
        "pass_a": maps_passing >= 6 and (group_wins / len(groups) if groups else 0.0) >= 0.70,
    }


def summarize_planning_execution(rows: Iterable[dict]) -> list[dict]:
    """Aggregate planning-and-execution rows by E/X/method when present."""

    grouped: dict[tuple[float, int, str], list[dict]] = defaultdict(list)
    for row in rows:
        normalized = normalize_run_row(row)
        step = normalized.get("planning_execution_step_sec")
        window = normalized.get("planning_execution_window")
        if step is None or window is None:
            continue
        grouped[(float(step), int(window), normalized["method"])].append(normalized)

    out: list[dict] = []
    for (step, window, method), group in sorted(grouped.items()):
        ratios = [
            float(row["sum_of_loss_ratio"])
            for row in group
            if row.get("success") and row.get("sum_of_loss_ratio") is not None
        ]
        out.append(
            {
                "planning_execution_step_sec": step,
                "planning_execution_window": window,
                "method": method,
                "runs": len(group),
                "successes": sum(1 for row in group if row.get("success")),
                "ratio_mean": _mean(ratios),
                "ratio_median": _median(ratios),
            }
        )
    return out

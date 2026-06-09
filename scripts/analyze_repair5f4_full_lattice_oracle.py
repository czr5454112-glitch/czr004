"""Analyze the Repair5F.4 full bounded-lattice F4 oracle diagnostic.

This script is diagnostic-only. It uses F4 fresh-ID lattice outcomes to measure
headroom, robust static behavior, group-adaptive oracle behavior, and
support-to-F4 rank transfer. It must not be used to promote or export a runtime
artifact.
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


DEFAULT_LONG = "outputs/tables/phase5p5_repair5f4_full_lattice_utility_long.csv"
DEFAULT_WIDE = "outputs/tables/phase5p5_repair5f4_full_lattice_utility_wide.csv"
DEFAULT_STATIC_PAIRED = "outputs/tables/phase5p5_repair5f4_static_updateparams_validation_paired.csv"
DEFAULT_STATIC_BY_GROUP = "outputs/tables/phase5p5_repair5f4_static_updateparams_validation_by_map_agent.csv"
DEFAULT_THRESHOLD_SUMMARY = "outputs/reports/phase5p5_repair5f_selector_threshold_sweep_summary.json"
DEFAULT_SIMULATION_SUMMARY = "outputs/reports/phase5p5_repair5f_selector_simulation_summary.json"
DEFAULT_SUPPORT_LONG = "outputs/tables/phase5p5_repair5f_selector_support_utility_long.csv"

DEFAULT_REPORT = "outputs/reports/phase5p5_repair5f4_full_lattice_oracle_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5f4_full_lattice_oracle_summary.json"
DEFAULT_ORACLE_CASES = "outputs/tables/phase5p5_repair5f4_full_lattice_oracle_by_case.csv"
DEFAULT_STATIC_RANKING = "outputs/tables/phase5p5_repair5f4_full_lattice_static_candidate_ranking.csv"
DEFAULT_GROUP_BEST = "outputs/tables/phase5p5_repair5f4_full_lattice_group_best_candidates.csv"
DEFAULT_RANK_CORR = "outputs/tables/phase5p5_repair5f4_support_vs_f4_rank_correlation.csv"
DEFAULT_DECISION = "outputs/reports/phase5p5_repair5f4_failure_oracle_diagnosis_decision.md"

ADDITIVE_CANDIDATE = "additive_ltm"
LOCKED_CANDIDATE = "c100_b100_w075_d090"
COMPONENT_CANDIDATES = {
    "c100_b100_w075_d100",
    "c100_b100_w100_d090",
    "c100_b100_w100_d095",
    "c100_b100_w075_d095",
    LOCKED_CANDIDATE,
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


def bootstrap(values: list[float], seed: int = 54142, samples: int = 5000) -> dict[str, Any]:
    clean = [float(value) for value in values if math.isfinite(float(value))]
    if not clean:
        return {"ci95": [None, None], "probability_mean_delta_lt_0": None}
    rng = random.Random(seed)
    n = len(clean)
    draws = [sum(clean[rng.randrange(n)] for _ in range(n)) / n for _ in range(samples)]
    draws.sort()
    return {
        "ci95": [draws[int(0.025 * (samples - 1))], draws[int(0.975 * (samples - 1))]],
        "probability_mean_delta_lt_0": sum(1 for value in draws if value < 0.0) / samples,
    }


def pearson(left: list[float], right: list[float]) -> float | None:
    pairs = [(a, b) for a, b in zip(left, right) if math.isfinite(a) and math.isfinite(b)]
    if len(pairs) < 2:
        return None
    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    sx = statistics.pstdev(xs)
    sy = statistics.pstdev(ys)
    if sx <= 1.0e-12 or sy <= 1.0e-12:
        return None
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    return statistics.mean((x - mx) * (y - my) for x, y in pairs) / (sx * sy)


def candidate_rows_by_case(long_rows: list[dict[str, str]]) -> dict[tuple[str, int, int], dict[str, dict[str, str]]]:
    out: dict[tuple[str, int, int], dict[str, dict[str, str]]] = defaultdict(dict)
    for row in long_rows:
        candidate = str(row.get("candidate_id", ""))
        if not candidate:
            continue
        out[case_key(row)][candidate] = row
    return dict(out)


def static_ltm_success(static_paired: list[dict[str, str]]) -> dict[tuple[str, int, int], bool]:
    out: dict[tuple[str, int, int], bool] = {}
    for row in static_paired:
        if str(row.get("method")) == f"repair5f_static_{LOCKED_CANDIDATE}":
            out[case_key(row)] = boolish(row.get("ltm_success"))
    return out


def summarize_realized(rows: list[dict[str, Any]], delta_key: str = "delta_ratio_vs_ltm") -> dict[str, Any]:
    deltas = [number(row.get(delta_key)) for row in rows]
    deltas = [value for value in deltas if math.isfinite(value)]
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[group_key(row)].append(row)
    boot = bootstrap(deltas)
    success_regressions = sum(
        1 for row in rows if bool(row.get("ltm_success", True)) and not bool(row.get("success", True))
    )
    success_improvements = sum(
        1 for row in rows if bool(row.get("success", True)) and not bool(row.get("ltm_success", True))
    )
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
            if (mean([number(item.get(delta_key)) for item in items]) or 0.0) > 1.0e-12
        ),
        "success_regressions": success_regressions,
        "success_improvements": success_improvements,
        "success_worse_than_ltm_groups": sum(
            1
            for items in grouped.values()
            if sum(bool(item.get("ltm_success", True)) and not bool(item.get("success", True)) for item in items)
            > sum(bool(item.get("success", True)) and not bool(item.get("ltm_success", True)) for item in items)
        ),
    }


def best_row(rows: dict[str, dict[str, str]]) -> dict[str, str]:
    return sorted(
        rows.values(),
        key=lambda row: (
            number(row.get("delta_ratio_vs_ltm"), 0.0),
            0 if boolish(row.get("success")) else 1,
            number(row.get("sum_of_loss_ratio"), float("inf")),
            str(row.get("candidate_id", "")),
        ),
    )[0]


def build_oracle_cases(
    by_case: dict[tuple[str, int, int], dict[str, dict[str, str]]],
    ltm_success: dict[tuple[str, int, int], bool],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key, candidate_rows in sorted(by_case.items()):
        row = best_row(candidate_rows)
        delta = number(row.get("delta_ratio_vs_ltm"), 0.0)
        out.append(
            {
                "map": key[0],
                "agents": key[1],
                "seed": key[2],
                "scen": row.get("scen", ""),
                "oracle_candidate_id": row.get("candidate_id", ""),
                "oracle_delta_ratio_vs_ltm": delta,
                "delta_ratio_vs_ltm": delta,
                "success": boolish(row.get("success")),
                "ltm_success": ltm_success.get(key, True),
                "sum_of_loss_ratio": number(row.get("sum_of_loss_ratio")),
                "better_vs_ltm": delta < -1.0e-12,
                "equal_vs_ltm": abs(delta) <= 1.0e-12,
                "worse_vs_ltm": delta > 1.0e-12,
                "selected_is_additive": row.get("candidate_id") == ADDITIVE_CANDIDATE,
            }
        )
    return out


def build_static_ranking(
    by_case: dict[tuple[str, int, int], dict[str, dict[str, str]]],
    ltm_success: dict[tuple[str, int, int], bool],
) -> list[dict[str, Any]]:
    by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for key, candidates in by_case.items():
        for candidate, row in candidates.items():
            delta = number(row.get("delta_ratio_vs_ltm"), 0.0)
            by_candidate[candidate].append(
                {
                    "map": key[0],
                    "agents": key[1],
                    "seed": key[2],
                    "candidate_id": candidate,
                    "delta_ratio_vs_ltm": delta,
                    "success": boolish(row.get("success")),
                    "ltm_success": ltm_success.get(key, True),
                    "sum_of_loss_ratio": number(row.get("sum_of_loss_ratio")),
                }
            )
    rows: list[dict[str, Any]] = []
    for candidate, items in by_candidate.items():
        metrics = summarize_realized(items)
        group_means: dict[str, float] = {}
        grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
        for item in items:
            grouped[group_key(item)].append(item)
        for (map_name, agents), group_items in grouped.items():
            group_means[f"{map_name}|a{agents}"] = mean([number(item.get("delta_ratio_vs_ltm")) for item in group_items]) or 0.0
        worst_group = max(group_means.items(), key=lambda item: item[1]) if group_means else ("", math.nan)
        best_group = min(group_means.items(), key=lambda item: item[1]) if group_means else ("", math.nan)
        rows.append(
            {
                "candidate_id": candidate,
                "rows": metrics["rows"],
                "better": metrics["better"],
                "equal": metrics["equal"],
                "worse": metrics["worse"],
                "better_minus_worse": metrics["better"] - metrics["worse"],
                "mean_delta_ratio_vs_ltm": metrics["mean_delta_ratio_vs_ltm"],
                "median_delta_ratio_vs_ltm": metrics["median_delta_ratio_vs_ltm"],
                "bootstrap_95ci_mean_delta_ratio_vs_ltm": json.dumps(
                    metrics["bootstrap_95ci_mean_delta_ratio_vs_ltm"]
                ),
                "bootstrap_probability_mean_delta_lt_0": metrics["bootstrap_probability_mean_delta_lt_0"],
                "ratio_worse_than_ltm_groups": metrics["ratio_worse_than_ltm_groups"],
                "success_worse_than_ltm_groups": metrics["success_worse_than_ltm_groups"],
                "success_regressions": metrics["success_regressions"],
                "success_improvements": metrics["success_improvements"],
                "worst_group": worst_group[0],
                "worst_group_mean_delta_ratio_vs_ltm": worst_group[1],
                "best_group": best_group[0],
                "best_group_mean_delta_ratio_vs_ltm": best_group[1],
                "is_locked_f4_candidate": candidate == LOCKED_CANDIDATE,
                "is_component_candidate": candidate in COMPONENT_CANDIDATES,
            }
        )
    rows.sort(
        key=lambda item: (
            number(item["mean_delta_ratio_vs_ltm"], 0.0),
            number(item["worst_group_mean_delta_ratio_vs_ltm"], 0.0),
            -int(item["better"]),
            int(item["worse"]),
            item["candidate_id"],
        )
    )
    for rank, row in enumerate(rows, 1):
        row["f4_mean_rank"] = rank
    return rows


def realize_candidate(
    candidate: str,
    cases: list[tuple[str, int, int]],
    by_case: dict[tuple[str, int, int], dict[str, dict[str, str]]],
    ltm_success: dict[tuple[str, int, int], bool],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for key in cases:
        row = by_case[key][candidate]
        delta = number(row.get("delta_ratio_vs_ltm"), 0.0)
        out.append(
            {
                "map": key[0],
                "agents": key[1],
                "seed": key[2],
                "selected_candidate_id": candidate,
                "delta_ratio_vs_ltm": delta,
                "success": boolish(row.get("success")),
                "ltm_success": ltm_success.get(key, True),
            }
        )
    return out


def leave_one_group_static_selection(
    by_case: dict[tuple[str, int, int], dict[str, dict[str, str]]],
    ltm_success: dict[tuple[str, int, int], bool],
) -> dict[str, Any]:
    cases_by_group: dict[tuple[str, int], list[tuple[str, int, int]]] = defaultdict(list)
    for key in by_case:
        cases_by_group[(key[0], key[1])].append(key)

    decisions: list[dict[str, Any]] = []
    realized: list[dict[str, Any]] = []
    candidate_ids = sorted({candidate for rows in by_case.values() for candidate in rows})
    for held_group, held_cases in sorted(cases_by_group.items()):
        train_cases = [key for key in by_case if (key[0], key[1]) != held_group]
        scores: list[tuple[float, str]] = []
        for candidate in candidate_ids:
            values = [
                number(by_case[key][candidate].get("delta_ratio_vs_ltm"), 0.0)
                for key in train_cases
                if candidate in by_case[key]
            ]
            if values:
                scores.append((statistics.mean(values), candidate))
        scores.sort(key=lambda item: (item[0], item[1]))
        selected = scores[0][1]
        held_rows = realize_candidate(selected, held_cases, by_case, ltm_success)
        metrics = summarize_realized(held_rows)
        decisions.append(
            {
                "heldout_map": held_group[0],
                "heldout_agents": held_group[1],
                "selected_candidate_id": selected,
                "train_mean_delta_ratio_vs_ltm": scores[0][0],
                "heldout_rows": metrics["rows"],
                "heldout_better": metrics["better"],
                "heldout_equal": metrics["equal"],
                "heldout_worse": metrics["worse"],
                "heldout_mean_delta_ratio_vs_ltm": metrics["mean_delta_ratio_vs_ltm"],
            }
        )
        realized.extend(held_rows)
    return {"decisions": decisions, "metrics": summarize_realized(realized)}


def maximin_static_selection(static_rows: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = []
    for row in static_rows:
        candidates.append(
            (
                number(row.get("worst_group_mean_delta_ratio_vs_ltm"), math.inf),
                number(row.get("mean_delta_ratio_vs_ltm"), math.inf),
                str(row.get("candidate_id")),
                row,
            )
        )
    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    return candidates[0][3] if candidates else {}


def group_adaptive_oracle(
    by_case: dict[tuple[str, int, int], dict[str, dict[str, str]]],
    ltm_success: dict[tuple[str, int, int], bool],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cases_by_group: dict[tuple[str, int], list[tuple[str, int, int]]] = defaultdict(list)
    for key in by_case:
        cases_by_group[(key[0], key[1])].append(key)
    group_rows: list[dict[str, Any]] = []
    realized: list[dict[str, Any]] = []
    candidate_ids = sorted({candidate for rows in by_case.values() for candidate in rows})
    for group, cases in sorted(cases_by_group.items()):
        scores: list[tuple[float, str]] = []
        for candidate in candidate_ids:
            values = [
                number(by_case[key][candidate].get("delta_ratio_vs_ltm"), 0.0)
                for key in cases
                if candidate in by_case[key]
            ]
            if values:
                scores.append((statistics.mean(values), candidate))
        scores.sort(key=lambda item: (item[0], item[1]))
        selected = scores[0][1]
        rows = realize_candidate(selected, cases, by_case, ltm_success)
        metrics = summarize_realized(rows)
        group_rows.append(
            {
                "selection_type": "group_adaptive_oracle",
                "map": group[0],
                "agents": group[1],
                "selected_candidate_id": selected,
                "rows": metrics["rows"],
                "better": metrics["better"],
                "equal": metrics["equal"],
                "worse": metrics["worse"],
                "mean_delta_ratio_vs_ltm": metrics["mean_delta_ratio_vs_ltm"],
                "ratio_worse_than_ltm_groups": metrics["ratio_worse_than_ltm_groups"],
            }
        )
        realized.extend(rows)
    return group_rows, summarize_realized(realized)


def static_group_best_rows(
    by_case: dict[tuple[str, int, int], dict[str, dict[str, str]]],
    static_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    cases_by_group: dict[tuple[str, int], list[tuple[str, int, int]]] = defaultdict(list)
    for key in by_case:
        cases_by_group[(key[0], key[1])].append(key)
    candidate_ids = sorted({candidate for rows in by_case.values() for candidate in rows})
    out: list[dict[str, Any]] = []
    for group, cases in sorted(cases_by_group.items()):
        scores = []
        for candidate in candidate_ids:
            values = [
                number(by_case[key][candidate].get("delta_ratio_vs_ltm"), 0.0)
                for key in cases
                if candidate in by_case[key]
            ]
            if values:
                scores.append((statistics.mean(values), candidate))
        scores.sort(key=lambda item: (item[0], item[1]))
        out.append(
            {
                "selection_type": "best_static_within_group_diagnostic",
                "map": group[0],
                "agents": group[1],
                "selected_candidate_id": scores[0][1],
                "rows": len(cases),
                "better": "",
                "equal": "",
                "worse": "",
                "mean_delta_ratio_vs_ltm": scores[0][0],
                "ratio_worse_than_ltm_groups": "",
            }
        )
    best_static = static_rows[0] if static_rows else {}
    if best_static:
        out.append(
            {
                "selection_type": "best_single_static_on_f4_diagnostic",
                "map": "all",
                "agents": "all",
                "selected_candidate_id": best_static["candidate_id"],
                "rows": best_static["rows"],
                "better": best_static["better"],
                "equal": best_static["equal"],
                "worse": best_static["worse"],
                "mean_delta_ratio_vs_ltm": best_static["mean_delta_ratio_vs_ltm"],
                "ratio_worse_than_ltm_groups": best_static["ratio_worse_than_ltm_groups"],
            }
        )
    return out


def rank_map(rows: list[dict[str, Any]], mean_key: str) -> dict[str, int]:
    ordered = sorted(rows, key=lambda row: (number(row.get(mean_key), math.inf), str(row.get("candidate_id"))))
    return {str(row["candidate_id"]): index for index, row in enumerate(ordered, 1)}


def support_vs_f4_rank_rows(
    support_long: Path,
    f4_static_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not support_long.exists():
        return [], {"support_long_available": False}
    support_rows = read_csv(support_long)
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in support_rows:
        candidate = str(row.get("candidate_id", ""))
        if not candidate:
            continue
        grouped[candidate].append(number(row.get("delta_ratio_vs_ltm"), 0.0))
    support_stats = [
        {
            "candidate_id": candidate,
            "support_mean_delta_ratio_vs_ltm": mean(values),
            "support_rows": len(values),
        }
        for candidate, values in grouped.items()
    ]
    support_rank = rank_map(support_stats, "support_mean_delta_ratio_vs_ltm")
    f4_rank = {str(row["candidate_id"]): int(row["f4_mean_rank"]) for row in f4_static_rows}
    f4_by_candidate = {str(row["candidate_id"]): row for row in f4_static_rows}
    support_by_candidate = {str(row["candidate_id"]): row for row in support_stats}
    common = sorted(set(support_rank) & set(f4_rank))
    rows: list[dict[str, Any]] = []
    for candidate in common:
        support_mean = support_by_candidate[candidate]["support_mean_delta_ratio_vs_ltm"]
        f4_mean = f4_by_candidate[candidate]["mean_delta_ratio_vs_ltm"]
        rows.append(
            {
                "candidate_id": candidate,
                "support_rows": support_by_candidate[candidate]["support_rows"],
                "support_mean_delta_ratio_vs_ltm": support_mean,
                "support_mean_rank": support_rank[candidate],
                "f4_rows": f4_by_candidate[candidate]["rows"],
                "f4_mean_delta_ratio_vs_ltm": f4_mean,
                "f4_mean_rank": f4_rank[candidate],
                "rank_delta_f4_minus_support": f4_rank[candidate] - support_rank[candidate],
                "is_locked_candidate": candidate == LOCKED_CANDIDATE,
            }
        )
    support_means = [number(row["support_mean_delta_ratio_vs_ltm"]) for row in rows]
    f4_means = [number(row["f4_mean_delta_ratio_vs_ltm"]) for row in rows]
    support_ranks = [number(row["support_mean_rank"]) for row in rows]
    f4_ranks = [number(row["f4_mean_rank"]) for row in rows]
    locked = next((row for row in rows if row["candidate_id"] == LOCKED_CANDIDATE), None)
    summary = {
        "support_long_available": True,
        "common_candidate_count": len(common),
        "pearson_mean_delta": pearson(support_means, f4_means),
        "spearman_rank_correlation": pearson(support_ranks, f4_ranks),
        "locked_candidate_support_rank": locked.get("support_mean_rank") if locked else None,
        "locked_candidate_f4_rank": locked.get("f4_mean_rank") if locked else None,
        "support_overranked_locked_candidate": (
            bool(locked)
            and number(locked.get("support_mean_rank"), math.inf) <= 5
            and number(locked.get("f4_mean_rank"), 0) > number(locked.get("support_mean_rank"), 0)
        ),
    }
    return rows, summary


def classify_failure(
    *,
    oracle_metrics: dict[str, Any],
    best_static: dict[str, Any],
    leave_one_group: dict[str, Any],
    group_adaptive_metrics: dict[str, Any],
    rank_transfer: dict[str, Any],
) -> dict[str, Any]:
    oracle_weak = (
        number(oracle_metrics.get("mean_delta_ratio_vs_ltm"), 0.0) >= 0.0
        or int(oracle_metrics.get("better", 0)) <= int(oracle_metrics.get("worse", 0))
        or int(oracle_metrics.get("ratio_worse_than_ltm_groups", 0)) > 1
        or int(oracle_metrics.get("success_worse_than_ltm_groups", 0)) > 0
    )
    best_static_weak = (
        number(best_static.get("mean_delta_ratio_vs_ltm"), 0.0) >= 0.0
        or int(best_static.get("better", 0)) <= int(best_static.get("worse", 0))
        or int(best_static.get("ratio_worse_than_ltm_groups", 0)) > 1
        or int(best_static.get("success_worse_than_ltm_groups", 0)) > 0
    )
    loo_metrics = leave_one_group.get("metrics", {})
    robust_static_weak = (
        number(loo_metrics.get("mean_delta_ratio_vs_ltm"), 0.0) >= 0.0
        or int(loo_metrics.get("better", 0)) <= int(loo_metrics.get("worse", 0))
        or int(loo_metrics.get("ratio_worse_than_ltm_groups", 0)) > 1
        or int(loo_metrics.get("success_worse_than_ltm_groups", 0)) > 0
    )
    transfer_poor = (
        rank_transfer.get("spearman_rank_correlation") is None
        or number(rank_transfer.get("spearman_rank_correlation"), 0.0) < 0.25
        or bool(rank_transfer.get("support_overranked_locked_candidate"))
    )
    group_gap = number(best_static.get("mean_delta_ratio_vs_ltm"), 0.0) - number(
        group_adaptive_metrics.get("mean_delta_ratio_vs_ltm"), 0.0
    )
    group_heterogeneity = group_gap > 0.001 or int(best_static.get("ratio_worse_than_ltm_groups", 0)) > int(
        group_adaptive_metrics.get("ratio_worse_than_ltm_groups", 0)
    )
    noisy_effects = (
        abs(number(best_static.get("mean_delta_ratio_vs_ltm"), 0.0)) < 0.001
        or int(best_static.get("equal", 0)) >= int(best_static.get("better", 0)) + int(best_static.get("worse", 0))
    )
    return {
        "no_headroom": oracle_weak,
        "static_overfit": bool(rank_transfer.get("support_overranked_locked_candidate")),
        "group_heterogeneity": group_heterogeneity,
        "noisy_time_budget_sensitive_effects": noisy_effects,
        "selector_objective_mismatch": transfer_poor,
        "best_static_weak": best_static_weak,
        "leave_one_group_robust_static_weak": robust_static_weak,
    }


def decision_from_summary(summary: dict[str, Any]) -> dict[str, Any]:
    oracle = summary["oracle_metrics"]
    best_static = summary["best_single_static_candidate"]
    classification = summary["failure_classification"]
    oracle_weak = bool(classification["no_headroom"])
    best_static_weak = bool(classification["best_static_weak"])
    robust_static_weak = bool(classification["leave_one_group_robust_static_weak"])
    transfer_poor = bool(classification["selector_objective_mismatch"])
    if oracle_weak:
        decision = "stop_bounded_updateparams_branch_as_currently_defined"
        rationale = (
            "The F4 full-lattice oracle is weak under the Repair5F.4.1 stop rule, so bounded UpdateParams "
            "does not have enough robust fresh-ID headroom in its current form."
        )
    elif best_static_weak and robust_static_weak:
        decision = "plan_repair5g_group_context_adaptive_selector"
        rationale = (
            "The F4 oracle has headroom, but single static and leave-one-group static selection are weak. "
            "A future selector must be trained on allowed support/validation data and tested only on untouched IDs."
        )
    else:
        decision = "plan_new_static_candidate_protocol_with_untouched_final_validation"
        rationale = (
            "A static candidate appears robust on F4, but that is diagnostic-only because F4 outcomes observed it. "
            "Any static claim requires a new support/validation protocol and a fresh final holdout."
        )
    if transfer_poor:
        rationale += " Support-to-F4 transfer is poor or overranked the locked rule, so the selector objective also needs diagnosis."
    return {
        "decision": decision,
        "rationale": rationale,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "do_not_promote": True,
        "do_not_retune_from_f4": True,
        "best_static_candidate_id": best_static.get("candidate_id"),
        "oracle_mean_delta_ratio_vs_ltm": oracle.get("mean_delta_ratio_vs_ltm"),
    }


def build_summary(
    *,
    root: Path,
    long_path: Path,
    wide_path: Path,
    static_paired_path: Path,
    static_by_group_path: Path,
    threshold_summary: dict[str, Any],
    simulation_summary: dict[str, Any],
    support_long_path: Path,
    report: Path,
    summary_path: Path,
    oracle_cases_path: Path,
    static_ranking_path: Path,
    group_best_path: Path,
    rank_corr_path: Path,
    decision_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    long_rows = read_csv(long_path)
    wide_rows = read_csv(wide_path)
    static_paired = read_csv(static_paired_path)
    if not static_by_group_path.exists():
        raise FileNotFoundError(static_by_group_path)
    by_case = candidate_rows_by_case(long_rows)
    ltm_success = static_ltm_success(static_paired)
    oracle_cases = build_oracle_cases(by_case, ltm_success)
    oracle_metrics = summarize_realized(oracle_cases, "oracle_delta_ratio_vs_ltm")
    oracle_metrics["selected_candidate_distribution"] = dict(
        sorted(Counter(row["oracle_candidate_id"] for row in oracle_cases).items())
    )

    static_rows = build_static_ranking(by_case, ltm_success)
    best_static = static_rows[0] if static_rows else {}
    maximin = maximin_static_selection(static_rows)
    leave_one_group = leave_one_group_static_selection(by_case, ltm_success)
    group_oracle_rows, group_oracle_metrics = group_adaptive_oracle(by_case, ltm_success)
    group_best_rows = static_group_best_rows(by_case, static_rows) + group_oracle_rows
    rank_rows, rank_summary = support_vs_f4_rank_rows(support_long_path, static_rows)
    classification = classify_failure(
        oracle_metrics=oracle_metrics,
        best_static=best_static,
        leave_one_group=leave_one_group,
        group_adaptive_metrics=group_oracle_metrics,
        rank_transfer=rank_summary,
    )
    summary = {
        "schema_version": "phase5p5_repair5f4_full_lattice_oracle_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "f4_outcomes_used_for_retuning": False,
        "scope": {
            "cases": len(by_case),
            "wide_rows": len(wide_rows),
            "candidate_count": len({candidate for rows in by_case.values() for candidate in rows}),
            "long_rows": len(long_rows),
        },
        "inputs": {
            "long_csv": rel(long_path, root),
            "wide_csv": rel(wide_path, root),
            "static_paired_csv": rel(static_paired_path, root),
            "static_by_group_csv": rel(static_by_group_path, root),
            "threshold_summary_json": DEFAULT_THRESHOLD_SUMMARY,
            "simulation_summary_json": DEFAULT_SIMULATION_SUMMARY,
            "support_long_csv": rel(support_long_path, root) if support_long_path.exists() else "",
        },
        "support_selector_context": {
            "best_support_selector": threshold_summary.get("best_support_selector"),
            "best_support_metrics": threshold_summary.get("best_support_metrics"),
            "simulation_main_metrics": simulation_summary.get("main_metrics"),
            "simulation_comparator_metrics": simulation_summary.get("comparator_metrics"),
        },
        "oracle_metrics": oracle_metrics,
        "best_single_static_candidate": best_static,
        "locked_candidate_ranking": next((row for row in static_rows if row["candidate_id"] == LOCKED_CANDIDATE), {}),
        "component_candidate_rankings": [row for row in static_rows if row["candidate_id"] in COMPONENT_CANDIDATES],
        "maximin_group_mean_static_candidate": maximin,
        "leave_one_group_static_selection": leave_one_group,
        "group_adaptive_oracle_metrics": group_oracle_metrics,
        "support_vs_f4_rank_transfer": rank_summary,
        "failure_classification": classification,
        "outputs": {
            "report": rel(report, root),
            "summary_json": rel(summary_path, root),
            "oracle_by_case_csv": rel(oracle_cases_path, root),
            "static_candidate_ranking_csv": rel(static_ranking_path, root),
            "group_best_candidates_csv": rel(group_best_path, root),
            "support_vs_f4_rank_correlation_csv": rel(rank_corr_path, root),
            "decision_report": rel(decision_path, root),
        },
    }
    summary["decision"] = decision_from_summary(summary)
    return summary, oracle_cases, static_rows, group_best_rows, rank_rows


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    oracle = summary["oracle_metrics"]
    best_static = summary["best_single_static_candidate"]
    group_oracle = summary["group_adaptive_oracle_metrics"]
    decision = summary["decision"]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F.4 Full-Lattice Oracle Diagnosis\n\n")
        handle.write("Diagnostic-only full bounded UpdateParams lattice analysis on F4 fresh IDs 26..45.\n\n")
        handle.write("## Boundary\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- f4_outcomes_used_for_retuning: `false`\n\n")
        handle.write("## F4 Full-Lattice Oracle\n\n")
        handle.write(f"- rows: `{oracle['rows']}`\n")
        handle.write(f"- better / equal / worse: `{oracle['better']} / {oracle['equal']} / {oracle['worse']}`\n")
        handle.write(f"- mean_delta_ratio_vs_ltm: `{oracle['mean_delta_ratio_vs_ltm']}`\n")
        handle.write(f"- ratio_worse_than_ltm_groups: `{oracle['ratio_worse_than_ltm_groups']}`\n")
        handle.write(f"- success_worse_than_ltm_groups: `{oracle['success_worse_than_ltm_groups']}`\n")
        handle.write(f"- selected_candidate_distribution: `{oracle['selected_candidate_distribution']}`\n\n")
        handle.write("## Static Diagnostics\n\n")
        handle.write(f"- best_single_static_candidate: `{best_static.get('candidate_id')}`\n")
        handle.write(f"- best_static_mean_delta_ratio_vs_ltm: `{best_static.get('mean_delta_ratio_vs_ltm')}`\n")
        handle.write(
            f"- best_static better/equal/worse: `{best_static.get('better')} / {best_static.get('equal')} / {best_static.get('worse')}`\n"
        )
        handle.write(
            f"- locked_candidate_ranking: `{summary.get('locked_candidate_ranking', {}).get('f4_mean_rank')}`\n"
        )
        handle.write(
            f"- leave_one_group_static_mean_delta_ratio_vs_ltm: `{summary['leave_one_group_static_selection']['metrics'].get('mean_delta_ratio_vs_ltm')}`\n"
        )
        handle.write(
            f"- maximin_group_mean_static_candidate: `{summary['maximin_group_mean_static_candidate'].get('candidate_id')}`\n\n"
        )
        handle.write("## Group-Adaptive Oracle\n\n")
        handle.write(f"- better / equal / worse: `{group_oracle['better']} / {group_oracle['equal']} / {group_oracle['worse']}`\n")
        handle.write(f"- mean_delta_ratio_vs_ltm: `{group_oracle['mean_delta_ratio_vs_ltm']}`\n")
        handle.write(f"- ratio_worse_than_ltm_groups: `{group_oracle['ratio_worse_than_ltm_groups']}`\n\n")
        handle.write("## Support-vs-F4 Transfer\n\n")
        transfer = summary["support_vs_f4_rank_transfer"]
        for key in [
            "common_candidate_count",
            "pearson_mean_delta",
            "spearman_rank_correlation",
            "locked_candidate_support_rank",
            "locked_candidate_f4_rank",
            "support_overranked_locked_candidate",
        ]:
            handle.write(f"- {key}: `{transfer.get(key)}`\n")
        handle.write("\n## Failure Classification\n\n")
        for key, value in summary["failure_classification"].items():
            handle.write(f"- {key}: `{value}`\n")
        handle.write("\n## Decision\n\n")
        handle.write(f"- decision: `{decision['decision']}`\n")
        handle.write(f"- rationale: {decision['rationale']}\n")


def write_decision(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    decision = summary["decision"]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5F.4 Failure Oracle Diagnosis Decision\n\n")
        handle.write("- diagnostic_only: `true`\n")
        handle.write("- phase5p5_allowed: `false`\n")
        handle.write("- phase6_allowed: `false`\n")
        handle.write("- do_not_promote: `true`\n")
        handle.write("- do_not_retune_from_f4: `true`\n\n")
        handle.write("## Decision\n\n")
        handle.write(f"`{decision['decision']}`\n\n")
        handle.write(decision["rationale"] + "\n\n")
        handle.write("## Evidence\n\n")
        oracle = summary["oracle_metrics"]
        best_static = summary["best_single_static_candidate"]
        loo = summary["leave_one_group_static_selection"]["metrics"]
        transfer = summary["support_vs_f4_rank_transfer"]
        handle.write(
            f"- F4 oracle: {oracle['better']} / {oracle['equal']} / {oracle['worse']}, "
            f"mean `{oracle['mean_delta_ratio_vs_ltm']}`, ratio-worse groups `{oracle['ratio_worse_than_ltm_groups']}`, "
            f"success-worse groups `{oracle['success_worse_than_ltm_groups']}`.\n"
        )
        handle.write(
            f"- Best F4 static candidate `{best_static.get('candidate_id')}`: "
            f"{best_static.get('better')} / {best_static.get('equal')} / {best_static.get('worse')}, "
            f"mean `{best_static.get('mean_delta_ratio_vs_ltm')}`, "
            f"ratio-worse groups `{best_static.get('ratio_worse_than_ltm_groups')}`.\n"
        )
        handle.write(
            f"- Leave-one-group static selection: {loo.get('better')} / {loo.get('equal')} / {loo.get('worse')}, "
            f"mean `{loo.get('mean_delta_ratio_vs_ltm')}`.\n"
        )
        handle.write(
            f"- Support-vs-F4 rank transfer: Spearman `{transfer.get('spearman_rank_correlation')}`, "
            f"locked support rank `{transfer.get('locked_candidate_support_rank')}`, "
            f"locked F4 rank `{transfer.get('locked_candidate_f4_rank')}`.\n\n"
        )
        handle.write("## Boundary\n\n")
        handle.write(
            "Any candidate or selector suggested by this diagnosis must be trained/tuned only on allowed support and "
            "validation data and evaluated on a new untouched final holdout such as IDs 46..65 or later. F4 outcomes "
            "remain diagnostic-only evidence.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--long-csv", type=Path, default=Path(DEFAULT_LONG))
    parser.add_argument("--wide-csv", type=Path, default=Path(DEFAULT_WIDE))
    parser.add_argument("--static-paired-csv", type=Path, default=Path(DEFAULT_STATIC_PAIRED))
    parser.add_argument("--static-by-map-agent-csv", type=Path, default=Path(DEFAULT_STATIC_BY_GROUP))
    parser.add_argument("--selector-threshold-summary-json", type=Path, default=Path(DEFAULT_THRESHOLD_SUMMARY))
    parser.add_argument("--selector-simulation-summary-json", type=Path, default=Path(DEFAULT_SIMULATION_SUMMARY))
    parser.add_argument("--support-long-csv", type=Path, default=Path(DEFAULT_SUPPORT_LONG))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--oracle-by-case-csv", type=Path, default=Path(DEFAULT_ORACLE_CASES))
    parser.add_argument("--static-ranking-csv", type=Path, default=Path(DEFAULT_STATIC_RANKING))
    parser.add_argument("--group-best-candidates-csv", type=Path, default=Path(DEFAULT_GROUP_BEST))
    parser.add_argument("--support-vs-f4-rank-correlation-csv", type=Path, default=Path(DEFAULT_RANK_CORR))
    parser.add_argument("--decision-report", type=Path, default=Path(DEFAULT_DECISION))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    long_path = resolve(args.long_csv, root)
    wide_path = resolve(args.wide_csv, root)
    static_paired_path = resolve(args.static_paired_csv, root)
    static_by_group_path = resolve(args.static_by_map_agent_csv, root)
    threshold_path = resolve(args.selector_threshold_summary_json, root)
    simulation_path = resolve(args.selector_simulation_summary_json, root)
    support_long_path = resolve(args.support_long_csv, root)
    report = resolve(args.report, root)
    summary_path = resolve(args.summary_json, root)
    oracle_cases_path = resolve(args.oracle_by_case_csv, root)
    static_ranking_path = resolve(args.static_ranking_csv, root)
    group_best_path = resolve(args.group_best_candidates_csv, root)
    rank_corr_path = resolve(args.support_vs_f4_rank_correlation_csv, root)
    decision_path = resolve(args.decision_report, root)

    for path in [long_path, wide_path, static_paired_path, static_by_group_path, threshold_path, simulation_path]:
        if not path.exists():
            raise FileNotFoundError(path)

    summary, oracle_cases, static_rows, group_best_rows, rank_rows = build_summary(
        root=root,
        long_path=long_path,
        wide_path=wide_path,
        static_paired_path=static_paired_path,
        static_by_group_path=static_by_group_path,
        threshold_summary=read_json(threshold_path),
        simulation_summary=read_json(simulation_path),
        support_long_path=support_long_path,
        report=report,
        summary_path=summary_path,
        oracle_cases_path=oracle_cases_path,
        static_ranking_path=static_ranking_path,
        group_best_path=group_best_path,
        rank_corr_path=rank_corr_path,
        decision_path=decision_path,
    )

    write_csv(
        oracle_cases_path,
        oracle_cases,
        [
            "map",
            "agents",
            "seed",
            "scen",
            "oracle_candidate_id",
            "oracle_delta_ratio_vs_ltm",
            "success",
            "ltm_success",
            "sum_of_loss_ratio",
            "better_vs_ltm",
            "equal_vs_ltm",
            "worse_vs_ltm",
            "selected_is_additive",
        ],
    )
    write_csv(
        static_ranking_path,
        static_rows,
        [
            "f4_mean_rank",
            "candidate_id",
            "rows",
            "better",
            "equal",
            "worse",
            "better_minus_worse",
            "mean_delta_ratio_vs_ltm",
            "median_delta_ratio_vs_ltm",
            "bootstrap_95ci_mean_delta_ratio_vs_ltm",
            "bootstrap_probability_mean_delta_lt_0",
            "ratio_worse_than_ltm_groups",
            "success_worse_than_ltm_groups",
            "success_regressions",
            "success_improvements",
            "worst_group",
            "worst_group_mean_delta_ratio_vs_ltm",
            "best_group",
            "best_group_mean_delta_ratio_vs_ltm",
            "is_locked_f4_candidate",
            "is_component_candidate",
        ],
    )
    write_csv(
        group_best_path,
        group_best_rows,
        [
            "selection_type",
            "map",
            "agents",
            "selected_candidate_id",
            "rows",
            "better",
            "equal",
            "worse",
            "mean_delta_ratio_vs_ltm",
            "ratio_worse_than_ltm_groups",
        ],
    )
    write_csv(
        rank_corr_path,
        rank_rows,
        [
            "candidate_id",
            "support_rows",
            "support_mean_delta_ratio_vs_ltm",
            "support_mean_rank",
            "f4_rows",
            "f4_mean_delta_ratio_vs_ltm",
            "f4_mean_rank",
            "rank_delta_f4_minus_support",
            "is_locked_candidate",
        ],
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    write_decision(decision_path, summary)
    print(
        json.dumps(
            {
                "summary_json": rel(summary_path, root),
                "report": rel(report, root),
                "decision": rel(decision_path, root),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

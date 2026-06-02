"""Shared helpers for Repair5F.2 selector diagnostics.

The helpers in this module are deliberately table-level. They train and apply
bounded UpdateParams selectors from support evidence only; final-holdout
outcomes are consumed only by the simulation evaluator.
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ADDITIVE_CANDIDATE = "additive_ltm"
SELECTOR_METHOD = "repair5f_support_trained_selector_simulation"

METADATA_FIELDS = [
    "case_id",
    "map",
    "map_family",
    "agents",
    "seed",
    "scen",
    "split_bucket",
    "source_update_method",
    "source_update_iteration",
    "source_feature_available",
]

ALLOWED_FEATURES = [
    "agents",
    "map_width",
    "map_height",
    "obstacle_ratio",
    "free_cells",
    "density",
    "iteration",
    "time_remaining_sec",
    "max_iterations",
    "has_solution_before",
    "best_ratio_before",
    "improved_last_iteration",
    "returned_solutions_count_so_far",
    "committed_count",
    "blocked_count",
    "wait_event_count",
    "goal_wait_ignored_count",
    "blocked_per_committed",
    "wait_per_committed",
    "blocked_per_agent",
    "committed_per_agent",
    "nonzero_edges_before",
    "max_raw_before",
    "mean_topk_raw_before",
    "max_weight_before",
    "topk_raw_delta_mean",
    "topk_raw_delta_max",
    "new_nonzero_edges_count",
    "topk_blocked_edge_concentration",
    "entropy_edge_usage",
    "local_degree_mean_topk",
    "current_additive_max_normalized_weight",
    "weight_entropy",
    "saturated_edge_count",
]

FORBIDDEN_FEATURES = [
    "instance_id",
    "seed",
    "scen",
    "candidate outcome columns from holdout",
    "holdout best candidate",
    "holdout ratio_delta_vs_ltm",
    "holdout success_delta",
    "final solver outcome not available before choosing",
]


@dataclass(frozen=True)
class SelectorSpec:
    selector_type: str
    min_support_count: int
    min_effective_neighbors: int
    max_neighbor_distance: float
    min_predicted_margin: float
    max_candidate_worse_rate: float
    max_group_worse_rate: float
    additive_fallback_threshold: float
    non_additive_budget: float
    candidate_whitelist: tuple[str, ...] = ()
    candidate_blacklist: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "SelectorSpec":
        return cls(
            selector_type=str(row["selector_type"]),
            min_support_count=int(float(row["min_support_count"])),
            min_effective_neighbors=int(float(row["min_effective_neighbors"])),
            max_neighbor_distance=number(row["max_neighbor_distance"], float("inf")),
            min_predicted_margin=number(row["min_predicted_margin"], 0.0),
            max_candidate_worse_rate=number(row["max_candidate_worse_rate"], 1.0),
            max_group_worse_rate=number(row["max_group_worse_rate"], 1.0),
            additive_fallback_threshold=number(row.get("additive_fallback_threshold"), 0.0),
            non_additive_budget=number(row.get("non_additive_budget"), 1.0),
            candidate_whitelist=tuple(row.get("candidate_whitelist") or ()),
            candidate_blacklist=tuple(row.get("candidate_blacklist") or ()),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "selector_type": self.selector_type,
            "min_support_count": self.min_support_count,
            "min_effective_neighbors": self.min_effective_neighbors,
            "max_neighbor_distance": self.max_neighbor_distance,
            "min_predicted_margin": self.min_predicted_margin,
            "max_candidate_worse_rate": self.max_candidate_worse_rate,
            "max_group_worse_rate": self.max_group_worse_rate,
            "additive_fallback_threshold": self.additive_fallback_threshold,
            "non_additive_budget": self.non_additive_budget,
            "candidate_whitelist": list(self.candidate_whitelist),
            "candidate_blacklist": list(self.candidate_blacklist),
        }


def number(value: Any, default: float = math.nan) -> float:
    if value is None or isinstance(value, bool):
        return default
    text = str(value).strip()
    if text == "":
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


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    with tmp_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    tmp_path.replace(path)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def case_key(row: dict[str, Any]) -> tuple[str, int, int]:
    return (str(row.get("map")), int(number(row.get("agents"), 0)), int(number(row.get("seed"), 0)))


def case_id_from_key(key: tuple[str, int, int]) -> str:
    return f"{key[0]}|a{key[1]}|s{key[2]}"


def map_family(map_name: str) -> str:
    return str(map_name).split("-", 1)[0]


def map_defaults(map_name: str) -> dict[str, float]:
    parts = str(map_name).split("-")
    width = number(parts[1] if len(parts) > 2 else "", 0.0)
    height = number(parts[2] if len(parts) > 2 else "", 0.0)
    obstacle_ratio = 0.0
    if str(map_name).startswith("random-") and len(parts) >= 4:
        obstacle_ratio = number(parts[3], 0.0) / 100.0
    if str(map_name).startswith("maze-"):
        obstacle_ratio = 0.0
    if str(map_name).startswith("warehouse-"):
        width = number(parts[2] if len(parts) > 2 else "", 0.0)
        height = number(parts[1] if len(parts) > 1 else "", 0.0)
        obstacle_ratio = 0.0
    free_cells = max(width * height * (1.0 - obstacle_ratio), 0.0)
    return {
        "map_width": width,
        "map_height": height,
        "obstacle_ratio": obstacle_ratio,
        "free_cells": free_cells,
        "density": obstacle_ratio,
    }


def feature_map_from_update(row: dict[str, Any]) -> dict[str, float]:
    names = row.get("runtime_feature_names") or []
    values = row.get("runtime_feature_values") or []
    out: dict[str, float] = {}
    for name, value in zip(names, values):
        out[str(name)] = number(value, 0.0)
    for name in ALLOWED_FEATURES:
        if name in row and name not in out:
            out[name] = number(row.get(name), 0.0)
    return out


def _update_priority(row: dict[str, Any]) -> tuple[int, int, str]:
    method = str(row.get("method", ""))
    has_solution = boolish(row.get("has_incumbent_before")) or boolish(row.get("has_solution_before"))
    if method == "repair5f_candidate_additive_ltm" and has_solution:
        tier = 0
    elif method.startswith("repair5f_candidate_") and has_solution:
        tier = 1
    elif has_solution:
        tier = 2
    else:
        tier = 3
    return (tier, int(number(row.get("iteration"), 10**9)), method)


def context_features_from_update_log(update_log: Path) -> dict[tuple[str, int, int], dict[str, Any]]:
    grouped: dict[tuple[str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(update_log):
        if row.get("runtime_feature_names") and row.get("runtime_feature_values"):
            grouped[case_key(row)].append(row)
    out: dict[tuple[str, int, int], dict[str, Any]] = {}
    for key, rows in grouped.items():
        selected = sorted(rows, key=_update_priority)[0]
        features = feature_map_from_update(selected)
        out[key] = {
            **features,
            "source_update_method": selected.get("method", ""),
            "source_update_iteration": int(number(selected.get("iteration"), -1)),
            "source_feature_available": True,
        }
    return out


def build_context_rows(
    *,
    utility_wide_csv: Path,
    update_log_jsonl: Path,
    split_name: str,
    feature_names: list[str] | None = None,
) -> list[dict[str, Any]]:
    feature_names = feature_names or ALLOWED_FEATURES
    update_features = context_features_from_update_log(update_log_jsonl)
    rows: list[dict[str, Any]] = []
    for wide in read_csv_rows(utility_wide_csv):
        key = case_key(wide)
        map_name = key[0]
        features: dict[str, Any] = dict(map_defaults(map_name))
        features.update(update_features.get(key, {}))
        row: dict[str, Any] = {
            "case_id": case_id_from_key(key),
            "map": map_name,
            "map_family": map_family(map_name),
            "agents": key[1],
            "seed": key[2],
            "scen": wide.get("scen", ""),
            "split_bucket": split_name,
            "source_update_method": features.get("source_update_method", ""),
            "source_update_iteration": features.get("source_update_iteration", ""),
            "source_feature_available": bool(features.get("source_feature_available")),
        }
        for name in feature_names:
            value = features.get(name)
            if name == "agents":
                value = key[1]
            row[name] = number(value, 0.0)
        rows.append(row)
    return sorted(rows, key=lambda item: (item["map"], int(number(item["agents"], 0)), int(number(item["seed"], 0))))


def load_utility_long(path: Path) -> dict[tuple[str, int, int], dict[str, dict[str, Any]]]:
    out: dict[tuple[str, int, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in read_csv_rows(path):
        candidate = str(row.get("candidate_id", ""))
        if not candidate:
            continue
        delta = number(row.get("delta_ratio_vs_ltm"))
        out[case_key(row)][candidate] = {
            "delta": delta if math.isfinite(delta) else 0.0,
            "success": boolish(row.get("success")),
            "sum_of_loss_ratio": number(row.get("sum_of_loss_ratio")),
            "better_vs_ltm": boolish(row.get("better_vs_ltm")),
            "equal_vs_ltm": boolish(row.get("equal_vs_ltm")),
            "worse_vs_ltm": boolish(row.get("worse_vs_ltm")),
        }
    return dict(out)


def available_candidates(utility_by_case: dict[tuple[str, int, int], dict[str, dict[str, Any]]]) -> list[str]:
    candidates = sorted({candidate for rows in utility_by_case.values() for candidate in rows})
    if ADDITIVE_CANDIDATE in candidates:
        candidates.remove(ADDITIVE_CANDIDATE)
        return [ADDITIVE_CANDIDATE, *candidates]
    return candidates


def feature_stats(contexts: list[dict[str, Any]], feature_names: list[str]) -> dict[str, dict[str, float]]:
    stats: dict[str, dict[str, float]] = {}
    for name in feature_names:
        values = [number(row.get(name), 0.0) for row in contexts]
        mu = statistics.mean(values) if values else 0.0
        sigma = statistics.pstdev(values) if len(values) > 1 else 0.0
        stats[name] = {"mean": mu, "std": sigma if sigma > 1.0e-12 else 1.0}
    return stats


def distance(left: dict[str, Any], right: dict[str, Any], stats: dict[str, dict[str, float]], features: list[str]) -> float:
    total = 0.0
    used = 0
    for name in features:
        stat = stats[name]
        a = (number(left.get(name), 0.0) - stat["mean"]) / stat["std"]
        b = (number(right.get(name), 0.0) - stat["mean"]) / stat["std"]
        total += (a - b) ** 2
        used += 1
    return math.sqrt(total / used) if used else 0.0


def neighbor_cases(
    *,
    target: dict[str, Any],
    support_contexts: list[dict[str, Any]],
    stats: dict[str, dict[str, float]],
    feature_names: list[str],
    spec: SelectorSpec,
    exclude_key: tuple[str, int, int] | None = None,
) -> list[tuple[float, dict[str, Any]]]:
    rows: list[tuple[float, dict[str, Any]]] = []
    for support in support_contexts:
        key = case_key(support)
        if exclude_key is not None and key == exclude_key:
            continue
        rows.append((distance(target, support, stats, feature_names), support))
    rows.sort(
        key=lambda item: (
            item[0],
            item[1]["map"],
            int(number(item[1]["agents"], 0)),
            int(number(item[1]["seed"], 0)),
        )
    )
    if spec.selector_type == "candidate_risk_capped":
        return rows
    within = [item for item in rows if item[0] <= spec.max_neighbor_distance]
    if spec.selector_type == "knn_utility":
        limit = max(spec.min_support_count, spec.min_effective_neighbors)
        return (within or rows)[:limit]
    if spec.selector_type == "group_balanced_utility" and not within:
        return rows
    return within


def candidate_score(
    *,
    candidate: str,
    neighbors: list[tuple[float, dict[str, Any]]],
    utility_by_case: dict[tuple[str, int, int], dict[str, dict[str, Any]]],
    group_balanced: bool,
) -> dict[str, Any] | None:
    values: list[float] = []
    group_values: dict[tuple[str, int], list[float]] = defaultdict(list)
    nearest_distance = math.inf
    for dist, context in neighbors:
        key = case_key(context)
        item = utility_by_case.get(key, {}).get(candidate)
        if item is None:
            continue
        delta = number(item.get("delta"), 0.0)
        values.append(delta)
        group_values[(str(context["map"]), int(number(context["agents"], 0)))].append(delta)
        nearest_distance = min(nearest_distance, dist)
    if not values:
        return None
    group_means = [statistics.mean(items) for items in group_values.values() if items]
    predicted_delta = statistics.mean(group_means) if group_balanced and group_means else statistics.mean(values)
    return {
        "candidate_id": candidate,
        "support_count": len(values),
        "effective_neighbors": len(values),
        "nearest_distance": nearest_distance if math.isfinite(nearest_distance) else "",
        "predicted_delta_ratio": predicted_delta,
        "predicted_margin_ratio": -predicted_delta,
        "candidate_worse_rate": sum(1 for value in values if value > 1.0e-12) / len(values),
        "group_worse_rate": (
            sum(1 for value in group_means if value > 1.0e-12) / len(group_means)
            if group_means
            else 1.0
        ),
    }


def select_candidate(
    *,
    target: dict[str, Any],
    support_contexts: list[dict[str, Any]],
    utility_by_case: dict[tuple[str, int, int], dict[str, dict[str, Any]]],
    stats: dict[str, dict[str, float]],
    feature_names: list[str],
    spec: SelectorSpec,
    exclude_key: tuple[str, int, int] | None = None,
) -> dict[str, Any]:
    neighbors = neighbor_cases(
        target=target,
        support_contexts=support_contexts,
        stats=stats,
        feature_names=feature_names,
        spec=spec,
        exclude_key=exclude_key,
    )
    whitelist = set(spec.candidate_whitelist)
    blacklist = set(spec.candidate_blacklist)
    candidates = available_candidates(utility_by_case)
    if whitelist:
        candidates = [candidate for candidate in candidates if candidate in whitelist or candidate == ADDITIVE_CANDIDATE]
    candidates = [candidate for candidate in candidates if candidate not in blacklist]

    scored: list[dict[str, Any]] = []
    group_balanced = spec.selector_type == "group_balanced_utility"
    for candidate in candidates:
        score = candidate_score(
            candidate=candidate,
            neighbors=neighbors,
            utility_by_case=utility_by_case,
            group_balanced=group_balanced,
        )
        if score is None:
            continue
        if score["support_count"] < spec.min_support_count:
            continue
        if score["effective_neighbors"] < spec.min_effective_neighbors:
            continue
        if score["candidate_worse_rate"] > spec.max_candidate_worse_rate:
            continue
        if score["group_worse_rate"] > spec.max_group_worse_rate:
            continue
        scored.append(score)

    if not scored:
        return fallback_decision(target, "insufficient_support_or_risk")
    scored.sort(
        key=lambda row: (
            row["predicted_delta_ratio"],
            row["candidate_worse_rate"],
            row["group_worse_rate"],
            str(row["candidate_id"]),
        )
    )
    best = scored[0]
    threshold = max(spec.min_predicted_margin, spec.additive_fallback_threshold)
    if best["candidate_id"] == ADDITIVE_CANDIDATE or best["predicted_margin_ratio"] < threshold:
        decision = fallback_decision(target, "insufficient_margin")
        decision.update({key: best[key] for key in best if key != "candidate_id"})
        return decision
    return {
        **base_decision_fields(target),
        **best,
        "selected_candidate_id": best["candidate_id"],
        "decision_status": "selected_nonadditive",
        "fallback_reason": "",
    }


def base_decision_fields(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": row["case_id"],
        "map": row["map"],
        "map_family": row.get("map_family", map_family(str(row["map"]))),
        "agents": int(number(row["agents"], 0)),
        "seed": int(number(row["seed"], 0)),
        "scen": row.get("scen", ""),
    }


def fallback_decision(row: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        **base_decision_fields(row),
        "selected_candidate_id": ADDITIVE_CANDIDATE,
        "candidate_id": ADDITIVE_CANDIDATE,
        "decision_status": "additive_fallback",
        "fallback_reason": reason,
        "support_count": 0,
        "effective_neighbors": 0,
        "nearest_distance": "",
        "predicted_delta_ratio": 0.0,
        "predicted_margin_ratio": 0.0,
        "candidate_worse_rate": 0.0,
        "group_worse_rate": 0.0,
    }


def apply_nonadditive_budget(decisions: list[dict[str, Any]], spec: SelectorSpec) -> list[dict[str, Any]]:
    nonadditive = [row for row in decisions if row["selected_candidate_id"] != ADDITIVE_CANDIDATE]
    if spec.non_additive_budget <= 0:
        keep = 0
    elif spec.non_additive_budget <= 1.0:
        keep = int(math.floor(len(decisions) * spec.non_additive_budget))
    else:
        keep = int(spec.non_additive_budget)
    keep_ids = {
        id(row)
        for row in sorted(
            nonadditive,
            key=lambda item: (number(item.get("predicted_margin_ratio"), 0.0), -number(item.get("nearest_distance"), 0.0)),
            reverse=True,
        )[:keep]
    }
    out: list[dict[str, Any]] = []
    for row in decisions:
        if row["selected_candidate_id"] == ADDITIVE_CANDIDATE or id(row) in keep_ids:
            out.append(row)
            continue
        updated = dict(row)
        updated["selected_candidate_id"] = ADDITIVE_CANDIDATE
        updated["candidate_id"] = ADDITIVE_CANDIDATE
        updated["decision_status"] = "additive_fallback"
        updated["fallback_reason"] = "non_additive_budget"
        out.append(updated)
    return out


def apply_selector(
    *,
    contexts: list[dict[str, Any]],
    support_contexts: list[dict[str, Any]],
    utility_by_case: dict[tuple[str, int, int], dict[str, dict[str, Any]]],
    feature_names: list[str],
    spec: SelectorSpec,
    leave_one_out: bool,
) -> list[dict[str, Any]]:
    stats = feature_stats(support_contexts, feature_names)
    decisions: list[dict[str, Any]] = []
    for context in contexts:
        exclude = case_key(context) if leave_one_out else None
        decisions.append(
            select_candidate(
                target=context,
                support_contexts=support_contexts,
                utility_by_case=utility_by_case,
                stats=stats,
                feature_names=feature_names,
                spec=spec,
                exclude_key=exclude,
            )
        )
    return apply_nonadditive_budget(decisions, spec)


def attach_realized_outcomes(
    decisions: list[dict[str, Any]],
    utility_by_case: dict[tuple[str, int, int], dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for decision in decisions:
        key = case_key(decision)
        selected = str(decision["selected_candidate_id"])
        item = utility_by_case.get(key, {}).get(selected, {"delta": 0.0, "success": True})
        delta = number(item.get("delta"), 0.0)
        rows.append(
            {
                **decision,
                "realized_delta_ratio_vs_ltm": delta,
                "realized_success": bool(item.get("success", True)),
                "better_vs_ltm": delta < -1.0e-12,
                "equal_vs_ltm": abs(delta) <= 1.0e-12,
                "worse_vs_ltm": delta > 1.0e-12,
            }
        )
    return rows


def metrics_for_realized(rows: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = [number(row.get("realized_delta_ratio_vs_ltm"), 0.0) for row in rows]
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["map"]), int(number(row["agents"], 0)))].append(row)
    candidate_counts = Counter(str(row["selected_candidate_id"]) for row in rows)
    nonadditive_rows = [row for row in rows if row["selected_candidate_id"] != ADDITIVE_CANDIDATE]
    return {
        "rows": len(rows),
        "better": sum(1 for value in deltas if value < -1.0e-12),
        "equal": sum(1 for value in deltas if abs(value) <= 1.0e-12),
        "worse": sum(1 for value in deltas if value > 1.0e-12),
        "mean_delta_ratio_vs_ltm": mean(deltas),
        "ratio_worse_than_ltm_groups": sum(
            1
            for items in grouped.values()
            if mean([number(item.get("realized_delta_ratio_vs_ltm"), 0.0) for item in items]) is not None
            and float(mean([number(item.get("realized_delta_ratio_vs_ltm"), 0.0) for item in items])) > 1.0e-12
        ),
        "success_worse_than_ltm_groups": 0,
        "zero_nonadditive_groups": sum(
            1 for items in grouped.values() if all(item["selected_candidate_id"] == ADDITIVE_CANDIDATE for item in items)
        ),
        "selected_nonadditive_cases": len(nonadditive_rows),
        "additive_fallback_cases": len(rows) - len(nonadditive_rows),
        "additive_fallback_rate": (len(rows) - len(nonadditive_rows)) / len(rows) if rows else 0.0,
        "selected_candidate_distribution": dict(sorted(candidate_counts.items())),
    }


def correlation_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    margins = [number(row.get("predicted_margin_ratio")) for row in rows]
    realized = [number(row.get("realized_delta_ratio_vs_ltm")) for row in rows]
    distances = [number(row.get("nearest_distance")) for row in rows]

    def pearson(left: list[float], right: list[float]) -> float | None:
        pairs = [(a, b) for a, b in zip(left, right) if math.isfinite(a) and math.isfinite(b)]
        if len(pairs) < 2:
            return None
        xs = [item[0] for item in pairs]
        ys = [item[1] for item in pairs]
        sx = statistics.pstdev(xs)
        sy = statistics.pstdev(ys)
        if sx <= 1.0e-12 or sy <= 1.0e-12:
            return None
        mx = statistics.mean(xs)
        my = statistics.mean(ys)
        return statistics.mean([(x - mx) * (y - my) for x, y in pairs]) / (sx * sy)

    return {
        "support_margin_vs_realized_delta_pearson": pearson(margins, realized),
        "nearest_distance_vs_realized_delta_pearson": pearson(distances, realized),
    }


def per_group_breakdown(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["map"]), int(number(row["agents"], 0)))].append(row)
    out: list[dict[str, Any]] = []
    for (map_name, agents), items in sorted(grouped.items()):
        metrics = metrics_for_realized(items)
        out.append(
            {
                "map": map_name,
                "agents": agents,
                "rows": len(items),
                "better": metrics["better"],
                "equal": metrics["equal"],
                "worse": metrics["worse"],
                "mean_delta_ratio_vs_ltm": metrics["mean_delta_ratio_vs_ltm"],
                "selected_nonadditive_cases": metrics["selected_nonadditive_cases"],
            }
        )
    return out

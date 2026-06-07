"""Shared helpers for Repair5G.5.10 executable lattice work."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from repair5g54_common import parse_instance_id_tokens, validate_observed_instance_ids
from repair5g59_common import (
    G59_CLOSED_STATUS,
    read_csv_rows,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)


G510_STATIC_CANDIDATE = "repair5g59_static_flow_shield"
G510_STATIC_ALIAS_CANDIDATE = "repair5g59_static_abstain_candidate"
G510_ADDITIVE_CANDIDATE = "repair5g59_additive_fallback"
G510_C_ONLY_CANDIDATE = "repair5g59_c_only_f_disabled"
G510_REFERENCE_STATIC = "repair5g2_best_frozen_static_candidate"
G510_REFERENCE_ADDITIVE = "additive_ltm"
G510_PRIMARY_BUDGETS_MS = [1000.0, 2000.0]
G510_STRESS_BUDGET_MS = 250.0
G510_BONUS_BUDGET_MS = 500.0
G510_DEFAULT_BUDGETS_MS = [1000.0, 2000.0, 250.0, 500.0]
G510_DEFAULT_MARGIN = 0.005


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def finite_number(value: Any, default: float = math.inf) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return numeric if math.isfinite(numeric) else default


def maybe_number(value: Any) -> float | None:
    numeric = finite_number(value, math.nan)
    return numeric if math.isfinite(numeric) else None


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def mean(values: Iterable[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return sum(finite) / len(finite) if finite else math.inf


def as_jsonable(value: float) -> float | None:
    return value if math.isfinite(value) else None


def quantile(values: list[float], frac: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * frac)))
    return ordered[index]


def entropy(values: list[float]) -> float:
    positive = [value for value in values if value > 0.0 and math.isfinite(value)]
    total = sum(positive)
    if total <= 0.0:
        return 0.0
    out = 0.0
    for value in positive:
        p = value / total
        out -= p * math.log(p)
    return out


def budget_key(value: Any) -> float:
    numeric = finite_number(value, math.nan)
    return float(round(numeric)) if math.isfinite(numeric) else math.nan


def context_key(row: dict[str, Any]) -> str:
    normalized = str(row.get("normalized_context_key", ""))
    if normalized:
        return normalized
    traffic_hash = str(row.get("traffic_before_hash_full") or row.get("traffic_before_hash") or "")
    return (
        f"{row.get('map', '')}|a{int(finite_number(row.get('agents'), 0.0))}"
        f"|s{int(finite_number(row.get('seed'), 0.0))}"
        f"|it{int(finite_number(row.get('iteration'), 0.0))}|{traffic_hash}"
    )


def map_agent_key(row: dict[str, Any]) -> str:
    return f"{row.get('map', '')}|a{int(finite_number(row.get('agents'), 0.0))}"


def observed_seed_ids(rows: Iterable[dict[str, Any]]) -> list[int]:
    seeds: list[int] = []
    for row in rows:
        seed = maybe_number(row.get("seed"))
        if seed is not None:
            seeds.append(int(seed))
    return sorted(set(seeds))


def validate_instance_tokens(tokens: Iterable[Any], *, label: str) -> list[int]:
    return validate_observed_instance_ids(parse_instance_id_tokens(tokens), label=label)


def lattice_candidates(candidate_csv: Path) -> list[dict[str, Any]]:
    rows = read_csv_rows(candidate_csv)
    return [row for row in rows if str(row.get("candidate_id", ""))]


def lattice_candidate_ids(candidate_csv: Path) -> list[str]:
    return [str(row["candidate_id"]) for row in lattice_candidates(candidate_csv)]


def score_from_probe(row: dict[str, Any]) -> float:
    if not boolish(row.get("probe_solution_found")) or not boolish(row.get("probe_feasible")):
        return math.inf
    return finite_number(row.get("probe_sum_of_loss_ratio"), math.inf)


def csv_rows_from_jsonl(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        flat = {}
        for key, value in row.items():
            if isinstance(value, (dict, list)):
                flat[key] = json.dumps(value, sort_keys=True, separators=(",", ":"))
            else:
                flat[key] = value
        flat["normalized_context_key"] = context_key(row)
        out.append(flat)
    return out


def write_csv_from_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    write_csv_rows(path, csv_rows_from_jsonl(rows))


def candidate_scores_by_context_budget(
    rows: Iterable[dict[str, Any]],
    *,
    allowed_candidates: set[str] | None = None,
) -> dict[tuple[str, float], dict[str, dict[str, Any]]]:
    grouped: dict[tuple[str, float], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        candidate = str(row.get("candidate_id", ""))
        if allowed_candidates is not None and candidate not in allowed_candidates:
            continue
        budget = budget_key(row.get("short_budget_ms"))
        key = context_key(row)
        if not key or not math.isfinite(budget) or not candidate:
            continue
        old = grouped[(key, budget)].get(candidate)
        if old is None or score_from_probe(row) < score_from_probe(old):
            grouped[(key, budget)][candidate] = row
    return grouped


def best_candidate(scores: dict[str, dict[str, Any]]) -> tuple[str, float]:
    ranked = [
        (candidate, score_from_probe(row))
        for candidate, row in scores.items()
        if math.isfinite(score_from_probe(row))
    ]
    if not ranked:
        return "", math.inf
    return min(ranked, key=lambda item: (item[1], item[0]))


def score_for_candidate(scores: dict[str, dict[str, Any]], candidate: str) -> float:
    row = scores.get(candidate)
    return score_from_probe(row) if row is not None else math.inf


def parse_json_cell(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return value
    text = str(value or "").strip()
    if not text:
        return []
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return []


def traffic_summary(edges: Any, *, prefix: str) -> dict[str, float]:
    parsed = parse_json_cell(edges)
    raw_values = []
    flow_values = []
    iterable = parsed if isinstance(parsed, list) else []
    for item in iterable:
        if not isinstance(item, dict):
            continue
        raw = maybe_number(item.get("raw"))
        flow = maybe_number(item.get("flow_raw"))
        if raw is not None and raw > 0.0:
            raw_values.append(raw)
        if flow is not None and flow > 0.0:
            flow_values.append(flow)
    values = flow_values if prefix.startswith("f_") else raw_values
    return {
        f"{prefix}nonzero_count": float(len(values)),
        f"{prefix}mean": mean(values) if values else 0.0,
        f"{prefix}max": max(values) if values else 0.0,
        f"{prefix}p25": quantile(values, 0.25),
        f"{prefix}median": quantile(values, 0.50),
        f"{prefix}p75": quantile(values, 0.75),
        f"{prefix}entropy": entropy(values),
    }


def feature_map_from_checkpoint(row: dict[str, Any]) -> dict[str, float]:
    names = parse_json_cell(row.get("feature_names"))
    values = parse_json_cell(row.get("feature_values"))
    out: dict[str, float] = {}
    if isinstance(names, list) and isinstance(values, list):
        for name, value in zip(names, values):
            out[str(name)] = finite_number(value, 0.0)
    return out


def count_by(rows: Iterable[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field, "")) for row in rows).items()))


__all__ = [
    "G510_ADDITIVE_CANDIDATE",
    "G510_BONUS_BUDGET_MS",
    "G510_C_ONLY_CANDIDATE",
    "G510_DEFAULT_BUDGETS_MS",
    "G510_DEFAULT_MARGIN",
    "G510_PRIMARY_BUDGETS_MS",
    "G510_REFERENCE_ADDITIVE",
    "G510_REFERENCE_STATIC",
    "G510_STATIC_ALIAS_CANDIDATE",
    "G510_STATIC_CANDIDATE",
    "G510_STRESS_BUDGET_MS",
    "G59_CLOSED_STATUS",
    "as_jsonable",
    "best_candidate",
    "boolish",
    "budget_key",
    "candidate_scores_by_context_budget",
    "context_key",
    "count_by",
    "csv_rows_from_jsonl",
    "feature_map_from_checkpoint",
    "finite_number",
    "lattice_candidate_ids",
    "lattice_candidates",
    "map_agent_key",
    "mean",
    "maybe_number",
    "observed_seed_ids",
    "read_csv_rows",
    "read_jsonl",
    "repo_root",
    "resolve",
    "score_for_candidate",
    "score_from_probe",
    "traffic_summary",
    "validate_instance_tokens",
    "write_csv_from_jsonl",
    "write_csv_rows",
    "write_json",
    "write_jsonl",
    "write_text",
]

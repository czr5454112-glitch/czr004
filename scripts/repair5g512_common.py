"""Shared helpers for Repair5G.5.12 candidate regret/ranking diagnostics."""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


PRIMARY_BUDGETS_MS = [1000, 2000]
STATIC_FLOW_SHIELD_CANDIDATE = "repair5g59_static_flow_shield"
STATIC_ABSTAIN_CANDIDATE = "repair5g59_static_abstain_candidate"
ADDITIVE_CANDIDATE = "repair5g59_additive_fallback"
C_ONLY_CANDIDATE = "repair5g59_c_only_f_disabled"
SLOW_DECAY_HIGH_SHIELD_CANDIDATE = "repair5g59_slow_decay_high_shield"
DEFAULT_MARGIN = 0.005
CLOSED_CLAIMS = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "runtime_claim_allowed": False,
    "aaai_ready": False,
}
FORBIDDEN_FEATURE_TERMS = [
    "score",
    "delta",
    "oracle",
    "regret",
    "rank",
    "label",
    "target",
    "probe",
    "solution_found",
    "feasible",
    "sum_of_loss",
    "full_run",
    "full-run",
    "outcome",
    "action",
    "priority",
    "restart",
    "h_value",
    "candidate_deletion",
    "deletion",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve(path: Path | str, root: Path | None = None) -> Path:
    item = Path(path)
    if item.is_absolute():
        return item
    return (root or repo_root()) / item


def read_csv_rows(path: Path | str) -> list[dict[str, Any]]:
    with resolve(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path | str, rows: Iterable[dict[str, Any]]) -> None:
    out = list(rows)
    target = resolve(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in out:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in out:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def read_json(path: Path | str) -> Any:
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def write_json(path: Path | str, payload: Any) -> None:
    target = resolve(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path | str, text: str) -> None:
    target = resolve(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def finite_number(value: Any, default: float = math.inf) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return numeric if math.isfinite(numeric) else default


def finite_or_none(value: Any) -> float | None:
    numeric = finite_number(value, math.nan)
    return numeric if math.isfinite(numeric) else None


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def as_jsonable(value: float) -> float | None:
    return value if math.isfinite(value) else None


def csv_number(value: float) -> float | str:
    return round(value, 12) if math.isfinite(value) else ""


def mean(values: Iterable[float]) -> float:
    finite = [value for value in values if math.isfinite(value)]
    return sum(finite) / len(finite) if finite else math.inf


def context_key(row: dict[str, Any]) -> str:
    existing = str(row.get("normalized_context_key", "")).strip()
    if existing:
        return existing
    return (
        f"{row.get('map', '')}|a{int(finite_number(row.get('agents'), 0.0))}"
        f"|s{int(finite_number(row.get('seed'), 0.0))}"
        f"|it{int(finite_number(row.get('iteration'), 0.0))}"
        f"|{row.get('traffic_before_hash_full', '')}"
    )


def map_family(map_name: str) -> str:
    lower = map_name.lower()
    if lower.startswith("maze"):
        return "maze"
    if lower.startswith("warehouse"):
        return "warehouse"
    if lower.startswith("random"):
        return "random"
    if lower.startswith("empty"):
        return "empty"
    if lower.startswith("room"):
        return "room"
    return "other"


def extract_seed_ids(values: Iterable[Any]) -> list[int]:
    seeds: list[int] = []
    for value in values:
        numeric = finite_or_none(value)
        if numeric is not None:
            seeds.append(int(numeric))
            continue
        for match in re.finditer(r"(?<!\d)(\d{1,4})(?!\d)", str(value)):
            seeds.append(int(match.group(1)))
    return sorted(set(seeds))


def observed_id_guard(values: Iterable[Any], *, label: str = "observed ids") -> list[int]:
    ids = extract_seed_ids(values)
    forbidden = [value for value in ids if 166 <= value <= 205]
    if forbidden:
        raise ValueError(f"{label} include reserved IDs 166..205: {forbidden}")
    future = [value for value in ids if value > 205]
    if future:
        raise ValueError(f"{label} include unapproved future IDs: {future}")
    return ids


def observed_id_flags(rows: Iterable[dict[str, Any]]) -> dict[str, bool]:
    seeds = extract_seed_ids(row.get("seed", "") for row in rows)
    return {
        "observed_ids_only": all(seed <= 165 for seed in seeds),
        "ids_166_205_untouched": all(not (166 <= seed <= 205) for seed in seeds),
    }


def score_from_probe(row: dict[str, Any]) -> float:
    if not boolish(row.get("probe_solution_found")) or not boolish(row.get("probe_feasible")):
        return math.inf
    return finite_number(row.get("probe_sum_of_loss_ratio"), math.inf)


def group_rows_by_context(rows: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[context_key(row)].append(row)
    return dict(grouped)


def split_for_seed(seed: Any) -> str:
    value = int(finite_number(seed, -1))
    if 146 <= value <= 150:
        return "train"
    if 151 <= value <= 155:
        return "dev"
    return "audit_only"


def count_by(rows: Iterable[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field, "")) for row in rows).items()))


def leakage_scan(feature_names: Iterable[str]) -> dict[str, Any]:
    forbidden: list[str] = []
    for name in feature_names:
        lowered = name.lower()
        tokens = {token for token in re.split(r"[^a-z0-9]+", lowered) if token}
        hits = []
        for term in FORBIDDEN_FEATURE_TERMS:
            normalized = term.replace("-", "_")
            term_tokens = [token for token in normalized.split("_") if token]
            if len(term_tokens) == 1:
                if term_tokens[0] in tokens:
                    hits.append(term)
            elif normalized in lowered:
                hits.append(term)
        if hits:
            forbidden.append(name)
    return {
        "forbidden_feature_count": len(forbidden),
        "forbidden_features": sorted(forbidden),
    }


def require_files(paths: Iterable[Path | str]) -> list[str]:
    missing = []
    for path in paths:
        if not resolve(path).exists():
            missing.append(str(path))
    return missing


def ranking(values: dict[str, float]) -> dict[str, int]:
    ranked = sorted(values.items(), key=lambda item: (item[1], item[0]))
    return {candidate: index + 1 for index, (candidate, _) in enumerate(ranked)}

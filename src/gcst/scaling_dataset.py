"""Grouped splits and nested scaling subsets for G5.63."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any, Iterable, Sequence


def stable_hash(text: Any, seed: int = 0) -> str:
    return hashlib.sha256(f"{seed}|{text}".encode("utf-8")).hexdigest()


def dataset_sha256(rows: Sequence[dict[str, Any]]) -> str:
    text = json.dumps(list(rows), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def physical_hash(row: dict[str, Any]) -> str:
    return str(
        row.get("physical_map_sha256")
        or row.get("g560_physical_map_sha256")
        or row.get("physical_map_sha256_expected")
        or row.get("map")
        or row.get("map_name")
        or "unknown"
    )


def context_uid(row: dict[str, Any]) -> str:
    return str(row.get("evaluation_uid") or row.get("g560_evaluation_uid") or row.get("dataset_row_id") or row.get("instance_uid") or "")


def make_grouped_split_manifest(
    rows: Sequence[dict[str, Any]],
    *,
    seed: int = 563,
    validation_fraction: float = 0.20,
    heldout_fraction: float = 0.10,
    blind_fraction: float = 0.10,
    split_key: str = "g563_split",
) -> list[dict[str, Any]]:
    """Assign split labels by physical-map hash so no hash overlaps."""

    groups = sorted({physical_hash(row) for row in rows}, key=lambda key: stable_hash(key, seed))
    n = len(groups)
    if n == 0:
        return []
    blind_n = max(1, round(n * blind_fraction)) if n >= 4 and blind_fraction > 0 else 0
    heldout_n = max(1, round(n * heldout_fraction)) if n - blind_n >= 3 and heldout_fraction > 0 else 0
    validation_n = max(1, round(n * validation_fraction)) if n - blind_n - heldout_n >= 2 and validation_fraction > 0 else 0
    assignment: dict[str, str] = {}
    for idx, group in enumerate(groups):
        if idx < blind_n:
            assignment[group] = "blind"
        elif idx < blind_n + heldout_n:
            assignment[group] = "heldout"
        elif idx < blind_n + heldout_n + validation_n:
            assignment[group] = "validation"
        else:
            assignment[group] = "train"
    manifest = []
    for row in rows:
        out = dict(row)
        out[split_key] = assignment[physical_hash(row)]
        out["g563_physical_group"] = physical_hash(row)
        out["g563_split_seed"] = seed
        manifest.append(out)
    return manifest


def split_hash_sets(rows: Iterable[dict[str, Any]], split_key: str = "g563_split") -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        out[str(row.get(split_key, "unassigned"))].add(physical_hash(row))
    return dict(out)


def assert_split_hashes_disjoint(rows: Iterable[dict[str, Any]], split_key: str = "g563_split") -> bool:
    sets = split_hash_sets(rows, split_key=split_key)
    names = sorted(sets)
    for idx, left in enumerate(names):
        for right in names[idx + 1 :]:
            overlap = sets[left] & sets[right]
            if overlap:
                raise AssertionError(f"physical-map hashes overlap between {left} and {right}: {sorted(overlap)[:3]}")
    return True


def _stratum(row: dict[str, Any], strata_keys: Sequence[str]) -> tuple[str, ...]:
    if not strata_keys:
        return ("all",)
    return tuple(str(row.get(key, "")) for key in strata_keys)


def nested_stratified_subsets(
    rows: Sequence[dict[str, Any]],
    sizes: Sequence[int],
    *,
    seed: int = 563,
    context_key: str = "evaluation_uid",
    strata_keys: Sequence[str] = ("map_family", "agent_count", "budget_ms"),
) -> dict[int, list[str]]:
    """Return deterministic nested context-id prefixes with stratum round-robin."""

    by_stratum: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_stratum[_stratum(row, strata_keys)].append(dict(row))
    for key in by_stratum:
        by_stratum[key].sort(key=lambda row: stable_hash(context_uid(row) or row.get(context_key, ""), seed))
    order: list[str] = []
    strata = sorted(by_stratum, key=lambda key: stable_hash("|".join(key), seed))
    cursor = {key: 0 for key in strata}
    while len(order) < len(rows):
        progressed = False
        for key in strata:
            idx = cursor[key]
            if idx >= len(by_stratum[key]):
                continue
            row = by_stratum[key][idx]
            uid = context_uid(row) or str(row.get(context_key, ""))
            if uid and uid not in order:
                order.append(uid)
            cursor[key] += 1
            progressed = True
        if not progressed:
            break
    out: dict[int, list[str]] = {}
    for size in sorted({int(size) for size in sizes if int(size) > 0}):
        out[size] = order[: min(size, len(order))]
    return out


def fixed_validation_ids(rows: Sequence[dict[str, Any]], split_key: str = "g563_split") -> list[str]:
    ids = [context_uid(row) for row in rows if str(row.get(split_key)) == "validation" and context_uid(row)]
    return sorted(set(ids))


def validation_manifest_sha256(ids: Sequence[str]) -> str:
    return hashlib.sha256(json.dumps(sorted(ids), separators=(",", ":")).encode("utf-8")).hexdigest()

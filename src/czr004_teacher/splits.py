"""Deterministic Phase3 map-holdout split rules."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable


DEFAULT_SPLIT_MAPS: dict[str, tuple[str, ...]] = {
    "train": (
        "empty-32-32",
        "random-32-32-20",
        "random-64-64-20",
        "room-64-64-8",
        "warehouse-10-20-10-2-1",
        "warehouse-10-20-10-2-2",
    ),
    "validation": ("empty-48-48",),
    "test": ("maze-32-32-4",),
}


def validate_split_maps(split_maps: dict[str, Iterable[str]]) -> list[str]:
    errors: list[str] = []
    seen: dict[str, str] = {}
    for split, maps in split_maps.items():
        if split not in {"train", "validation", "test"}:
            errors.append(f"unsupported split {split}")
        for map_name in maps:
            if map_name in seen:
                errors.append(f"map {map_name} appears in both {seen[map_name]} and {split}")
            seen[map_name] = split
    for required in ("train", "validation", "test"):
        if not tuple(split_maps.get(required, ())):
            errors.append(f"split {required} has no maps")
    return errors


def split_for(map_name: str, split_maps: dict[str, Iterable[str]] | None = None) -> str:
    maps = split_maps or DEFAULT_SPLIT_MAPS
    for split, names in maps.items():
        if map_name in set(names):
            return split
    raise KeyError(f"map {map_name!r} is not assigned to a Phase3 split")


def audit_no_leakage(rows: Iterable[dict]) -> list[str]:
    """Check that no map, map+seed, or run id crosses split boundaries."""

    map_splits: dict[str, set[str]] = defaultdict(set)
    map_seed_splits: dict[tuple[str, int], set[str]] = defaultdict(set)
    run_splits: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        split = str(row["split"])
        map_name = str(row["map"])
        seed = int(row["seed"])
        map_splits[map_name].add(split)
        map_seed_splits[(map_name, seed)].add(split)
        run_splits[str(row["run_id"])].add(split)

    errors: list[str] = []
    for map_name, splits in sorted(map_splits.items()):
        if len(splits) > 1:
            errors.append(f"map {map_name} leaks across splits: {sorted(splits)}")
    for (map_name, seed), splits in sorted(map_seed_splits.items()):
        if len(splits) > 1:
            errors.append(f"map/seed {map_name}/{seed} leaks across splits: {sorted(splits)}")
    for run_id, splits in sorted(run_splits.items()):
        if len(splits) > 1:
            errors.append(f"run_id {run_id} leaks across splits: {sorted(splits)}")
    return errors

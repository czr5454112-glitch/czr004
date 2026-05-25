"""Core solver metric definitions used by all experiment stages."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence


def stable_arrival_time(path: Sequence[object], goal: object | None = None) -> int:
    """Return the first timestep after which the agent stays at its goal."""

    if not path:
        raise ValueError("agent path must not be empty")
    target = path[-1] if goal is None else goal
    for index in range(len(path)):
        if path[index] == target and all(value == target for value in path[index:]):
            return index
    return len(path) - 1


def sum_of_loss(paths: Sequence[Sequence[object]]) -> int:
    """Compute MAPF sum-of-loss as the sum of stable arrival times."""

    if not paths:
        return 0
    return sum(stable_arrival_time(path) for path in paths)


def lower_bound_from_distances(distances: Iterable[int | float]) -> float:
    """Compute the SoL lower bound from per-agent shortest path distances."""

    total = 0.0
    for distance in distances:
        if not math.isfinite(float(distance)) or float(distance) < 0:
            raise ValueError(f"invalid lower-bound distance: {distance}")
        total += float(distance)
    return total


def sum_of_loss_ratio(sum_of_loss_value: int | float | None, lower_bound: int | float | None) -> float | None:
    """Return SoL ratio, or None when the run has no valid solution ratio."""

    if sum_of_loss_value is None or lower_bound is None:
        return None
    denominator = float(lower_bound)
    if denominator <= 0 or not math.isfinite(denominator):
        return None
    numerator = float(sum_of_loss_value)
    if not math.isfinite(numerator):
        return None
    return numerator / denominator

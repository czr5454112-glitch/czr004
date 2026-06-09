"""Incumbent-log parsing and anytime quality metrics."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .core import sum_of_loss_ratio


@dataclass(frozen=True)
class IncumbentEvent:
    time_ms: float
    sum_of_loss: float
    lower_bound: float
    returned_solutions_count: int = 1

    @property
    def ratio(self) -> float | None:
        return sum_of_loss_ratio(self.sum_of_loss, self.lower_bound)


def _event_from_mapping(item: dict[str, Any]) -> IncumbentEvent | None:
    time_ms = item.get("time_ms", item.get("runtime_ms", item.get("elapsed_ms")))
    loss = item.get("sum_of_loss", item.get("cost", item.get("solution_cost")))
    lower_bound = item.get("lower_bound", item.get("sum_of_costs_lower_bound"))
    if time_ms is None or loss is None or lower_bound is None:
        return None
    return IncumbentEvent(
        time_ms=float(time_ms),
        sum_of_loss=float(loss),
        lower_bound=float(lower_bound),
        returned_solutions_count=int(item.get("returned_solutions_count", 1)),
    )


def parse_incumbent_events(path: Path) -> list[IncumbentEvent]:
    """Parse JSONL incumbent events or solver rows into chronological events."""

    events: list[IncumbentEvent] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL") from exc

            nested = item.get("incumbents")
            if isinstance(nested, list):
                for event_item in nested:
                    if isinstance(event_item, dict):
                        event = _event_from_mapping(event_item)
                        if event is not None:
                            events.append(event)
                continue

            if item.get("success", True):
                event = _event_from_mapping(item)
                if event is not None:
                    events.append(event)

    events.sort(key=lambda event: event.time_ms)
    return events


def anytime_auc(
    events: list[IncumbentEvent],
    horizon_ms: float,
    *,
    initial_ratio: float | None = None,
    normalize: bool = True,
) -> float | None:
    """Integrate best-so-far SoL ratio over time; lower is better."""

    if horizon_ms <= 0:
        raise ValueError("horizon_ms must be positive")
    valid_events = [event for event in events if event.ratio is not None and event.time_ms <= horizon_ms]
    if not valid_events and initial_ratio is None:
        return None

    valid_events.sort(key=lambda event: event.time_ms)
    current = float(initial_ratio if initial_ratio is not None else valid_events[0].ratio)
    last_time = 0.0
    area = 0.0

    for event in valid_events:
        event_time = max(0.0, min(float(event.time_ms), horizon_ms))
        if event_time > last_time:
            area += (event_time - last_time) * current
            last_time = event_time
        event_ratio = event.ratio
        if event_ratio is not None and event_ratio < current:
            current = event_ratio

    if last_time < horizon_ms:
        area += (horizon_ms - last_time) * current

    return area / horizon_ms if normalize else area

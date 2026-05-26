"""Aggregate checkpoint-level features for Phase4E LAU-LTM samples."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any


FEATURE_SET = "aggregate_checkpoint_v1"
FEATURE_NAMES = [
    "agents",
    "free_cells",
    "density",
    "map_width",
    "map_height",
    "obstacle_ratio",
    "iteration",
    "node_budget",
    "elapsed_ms",
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


def _to_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return default


def _ratio(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def _entropy(values: Iterable[float]) -> float:
    positive = [float(value) for value in values if float(value) > 0.0]
    total = sum(positive)
    if total <= 0.0:
        return 0.0
    return -sum((value / total) * math.log(value / total) for value in positive)


def _edge_key(edge: dict[str, Any]) -> tuple[int, int]:
    return int(edge.get("from_id", -1)), int(edge.get("to_id", -1))


def _raw_by_edge(edges: Iterable[dict[str, Any]]) -> dict[tuple[int, int], float]:
    return {_edge_key(edge): _to_float(edge.get("raw")) for edge in edges}


class MapTopology:
    """Small MovingAI map parser matching LaCAM2 compact vertex ids."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.width = 0
        self.height = 0
        self.free_cells = 0
        self.obstacle_cells = 0
        self.degrees: dict[int, int] = {}
        self._load()

    @property
    def density_denominator(self) -> int:
        return max(1, self.free_cells)

    @property
    def obstacle_ratio(self) -> float:
        total = self.width * self.height
        return _ratio(self.obstacle_cells, total)

    def degree(self, vertex_id: int) -> int:
        return self.degrees.get(int(vertex_id), 0)

    def _load(self) -> None:
        lines = self.path.read_text(encoding="utf-8").splitlines()
        map_start = None
        grid: list[str] = []
        for index, line in enumerate(lines):
            if line.startswith("height "):
                self.height = int(line.split()[1])
            elif line.startswith("width "):
                self.width = int(line.split()[1])
            elif line == "map":
                map_start = index + 1
                break
        if map_start is None:
            raise ValueError(f"{self.path}: missing MovingAI map body")
        grid = lines[map_start : map_start + self.height]
        if len(grid) != self.height:
            raise ValueError(f"{self.path}: expected {self.height} map rows, found {len(grid)}")

        id_by_cell: dict[tuple[int, int], int] = {}
        for y, row in enumerate(grid):
            if len(row) != self.width:
                raise ValueError(f"{self.path}: row {y} width mismatch")
            for x, char in enumerate(row):
                if char in {"@", "T"}:
                    self.obstacle_cells += 1
                    continue
                vertex_id = len(id_by_cell)
                id_by_cell[(x, y)] = vertex_id
        self.free_cells = len(id_by_cell)

        for (x, y), vertex_id in id_by_cell.items():
            degree = 0
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) in id_by_cell:
                    degree += 1
            self.degrees[vertex_id] = degree


def _resolve_map_path(checkpoint_row: dict[str, Any], repo_root: str | Path | None) -> Path:
    value = checkpoint_row.get("map_path") or checkpoint_row.get("map")
    if not value:
        raise ValueError("checkpoint row is missing map_path")
    path = Path(str(value))
    if path.is_absolute():
        return path
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    return root / path


def topology_for_checkpoint(
    checkpoint_row: dict[str, Any],
    cache: dict[Path, MapTopology],
    repo_root: str | Path | None = None,
) -> MapTopology:
    path = _resolve_map_path(checkpoint_row, repo_root).resolve()
    if path not in cache:
        cache[path] = MapTopology(path)
    return cache[path]


def build_aggregate_checkpoint_features(
    checkpoint_row: dict[str, Any],
    trace_rows: Iterable[dict[str, Any]],
    *,
    topology: MapTopology,
) -> dict[str, float]:
    """Return numeric model features for one Phase4E checkpoint sample."""

    rows = list(trace_rows)
    trace_counter = Counter(str(row.get("kind")) for row in rows)
    committed = int(trace_counter.get("committed", checkpoint_row.get("committed_count", 0)))
    blocked = int(trace_counter.get("blocked", checkpoint_row.get("blocked_count", 0)))
    wait = sum(1 for row in rows if row.get("is_wait") and not row.get("at_goal"))
    goal_wait = sum(1 for row in rows if row.get("is_wait") and row.get("at_goal"))
    if not rows:
        committed = int(checkpoint_row.get("committed_count", 0))
        blocked = int(checkpoint_row.get("blocked_count", 0))
        wait = int(checkpoint_row.get("wait_event_count", 0))
        goal_wait = int(checkpoint_row.get("goal_wait_ignored_count", 0))

    raw_before = list(checkpoint_row.get("raw_before_topk", []))
    raw_after = list(checkpoint_row.get("raw_after_topk", []))
    normalized_after = list(checkpoint_row.get("normalized_after_topk", []))
    before_by_edge = _raw_by_edge(raw_before)
    after_by_edge = _raw_by_edge(raw_after)
    raw_deltas = [
        after_value - before_by_edge.get(edge_key, 0.0)
        for edge_key, after_value in after_by_edge.items()
    ]
    blocked_edges = Counter(
        (int(row["from_id"]), int(row["to_id"]))
        for row in rows
        if row.get("kind") == "blocked" and "from_id" in row and "to_id" in row
    )
    topk_after_keys = set(after_by_edge)
    topk_blocked_count = sum(count for edge, count in blocked_edges.items() if edge in topk_after_keys)

    after_weights = [_to_float(edge.get("weight")) for edge in normalized_after]
    after_raw_values = list(after_by_edge.values())
    topk_vertex_ids = [vertex_id for edge in after_by_edge for vertex_id in edge]
    local_degrees = [topology.degree(vertex_id) for vertex_id in topk_vertex_ids]
    max_weight_before = 10.0 if _to_float(checkpoint_row.get("traffic_before_max_raw")) > 0.0 else 0.0

    current_ratio = checkpoint_row.get("sum_of_loss_ratio_this_iteration")
    has_solution = 1.0 if current_ratio is not None else 0.0
    iteration = int(checkpoint_row.get("iteration", 0))
    best_ratio_before = _to_float(current_ratio)

    features = {
        "agents": float(checkpoint_row.get("agents", 0)),
        "free_cells": float(topology.free_cells),
        "density": _ratio(float(checkpoint_row.get("agents", 0)), topology.density_denominator),
        "map_width": float(topology.width),
        "map_height": float(topology.height),
        "obstacle_ratio": topology.obstacle_ratio,
        "iteration": float(iteration),
        "node_budget": float(checkpoint_row.get("node_budget", 0)),
        "elapsed_ms": _to_float(checkpoint_row.get("elapsed_ms")),
        "time_remaining_sec": _to_float(checkpoint_row.get("time_remaining_sec"), _to_float(checkpoint_row.get("time_limit_sec"))),
        "max_iterations": float(checkpoint_row.get("max_iterations", 0)),
        "has_solution_before": has_solution,
        "best_ratio_before": best_ratio_before,
        "improved_last_iteration": has_solution if iteration == 0 else 0.0,
        "returned_solutions_count_so_far": has_solution,
        "committed_count": float(committed),
        "blocked_count": float(blocked),
        "wait_event_count": float(wait),
        "goal_wait_ignored_count": float(goal_wait),
        "blocked_per_committed": _ratio(blocked, committed),
        "wait_per_committed": _ratio(wait, committed),
        "blocked_per_agent": _ratio(blocked, float(checkpoint_row.get("agents", 0))),
        "committed_per_agent": _ratio(committed, float(checkpoint_row.get("agents", 0))),
        "nonzero_edges_before": float(checkpoint_row.get("traffic_before_nonzero_edges", 0)),
        "max_raw_before": _to_float(checkpoint_row.get("traffic_before_max_raw")),
        "mean_topk_raw_before": _ratio(sum(before_by_edge.values()), len(before_by_edge)),
        "max_weight_before": max_weight_before,
        "topk_raw_delta_mean": _ratio(sum(raw_deltas), len(raw_deltas)),
        "topk_raw_delta_max": max(raw_deltas) if raw_deltas else 0.0,
        "new_nonzero_edges_count": float(
            max(
                0,
                int(checkpoint_row.get("traffic_after_nonzero_edges", 0))
                - int(checkpoint_row.get("traffic_before_nonzero_edges", 0)),
            )
        ),
        "topk_blocked_edge_concentration": _ratio(topk_blocked_count, blocked),
        "entropy_edge_usage": _entropy(blocked_edges.values()),
        "local_degree_mean_topk": _ratio(sum(local_degrees), len(local_degrees)),
        "current_additive_max_normalized_weight": _to_float(checkpoint_row.get("traffic_after_max_normalized")),
        "weight_entropy": _entropy(after_weights),
        "saturated_edge_count": float(sum(1 for weight in after_weights if weight >= 9.999)),
    }
    return {name: float(features[name]) for name in FEATURE_NAMES}


def feature_vector(features: dict[str, float]) -> list[float]:
    return [float(features[name]) for name in FEATURE_NAMES]

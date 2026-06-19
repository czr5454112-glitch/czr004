"""Start/goal assignment and context identity features."""

from __future__ import annotations

import hashlib
import random
from typing import Any

import numpy as np

from .graph_data import GraphData


def _sha(parts: list[Any]) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()


def _sample(cells: list[tuple[int, int]], rng: random.Random, count: int) -> list[tuple[int, int]]:
    if count <= len(cells):
        return rng.sample(cells, count)
    return [cells[i % len(cells)] for i in range(count)]


def _region(cells: list[tuple[int, int]], width: int, height: int, name: str) -> list[tuple[int, int]]:
    if name == "left":
        out = [c for c in cells if c[0] < width * 0.33]
    elif name == "right":
        out = [c for c in cells if c[0] > width * 0.67]
    elif name == "top":
        out = [c for c in cells if c[1] < height * 0.33]
    elif name == "bottom":
        out = [c for c in cells if c[1] > height * 0.67]
    elif name == "center":
        out = [c for c in cells if abs(c[0] - width / 2) < width * 0.15 and abs(c[1] - height / 2) < height * 0.15]
    else:
        out = cells
    return out or cells


def generate_assignment(graph: GraphData, context: dict[str, Any], max_agents: int | None = 96) -> dict[str, Any]:
    requested = int(float(context.get("agent_count") or context.get("agents") or 32))
    count = min(requested, max_agents) if max_agents else requested
    seed = int(float(context.get("seed") or 0))
    regime = str(context.get("start_goal_regime") or "uniform_random")
    rng = random.Random(seed)
    cells = graph.cells or [(0, 0)]
    if regime == "opposite_side_cross_flow":
        starts = _sample(_region(cells, graph.width, graph.height, "left"), rng, count)
        goals = _sample(_region(cells, graph.width, graph.height, "right"), rng, count)
    elif regime in {"many_to_one_goal_clustered", "central_choke_point", "high_conflict_adversarial"}:
        starts = _sample(_region(cells, graph.width, graph.height, "left"), rng, count)
        goals = _sample(_region(cells, graph.width, graph.height, "center"), rng, count)
    elif regime in {"room_to_room_door_bottleneck", "warehouse_aisle_to_aisle"}:
        starts = _sample(_region(cells, graph.width, graph.height, "top"), rng, count)
        goals = _sample(_region(cells, graph.width, graph.height, "bottom"), rng, count)
    elif regime == "clustered_starts_to_dispersed_goals":
        starts = _sample(_region(cells, graph.width, graph.height, "center"), rng, count)
        goals = _sample(cells, rng, count)
    else:
        starts = _sample(cells, rng, count)
        goals = _sample(cells, rng, count)
    distances = [abs(s[0] - g[0]) + abs(s[1] - g[1]) for s, g in zip(starts, goals)]
    start_hash = _sha([*starts])
    goal_hash = _sha([*goals])
    pair_hash = _sha([*(f"{s}->{g}" for s, g in zip(starts, goals))])
    od = []
    for s, g, dist in zip(starts, goals, distances):
        od.append(
            [
                s[0] / max(1, graph.width - 1),
                s[1] / max(1, graph.height - 1),
                g[0] / max(1, graph.width - 1),
                g[1] / max(1, graph.height - 1),
                dist / max(1, graph.width + graph.height),
                float(s[0] < g[0]) - float(s[0] > g[0]),
            ]
        )
    return {
        "requested_agent_count": requested,
        "encoded_agent_count": count,
        "starts": starts,
        "goals": goals,
        "start_positions_sha256": start_hash,
        "goal_positions_sha256": goal_hash,
        "start_goal_assignment_hash": pair_hash,
        "shortest_path_distance_mean": float(np.mean(distances)) if distances else 0.0,
        "shortest_path_distance_max": int(max(distances)) if distances else 0,
        "od_tokens": np.asarray(od, dtype=np.float32),
    }


def build_context_uid(context: dict[str, Any], physical_map_sha256: str, assignment: dict[str, Any]) -> str:
    parts = [
        physical_map_sha256,
        assignment["start_positions_sha256"],
        assignment["goal_positions_sha256"],
        context.get("agent_count", context.get("agents", "")),
        context.get("seed", context.get("solver_seed", "")),
        context.get("nominal_budget_ms", context.get("budget_ms", "")),
        context.get("short_budget_ms", ""),
        context.get("base_time_limit_sec", ""),
        context.get("ltm_max_iterations", ""),
    ]
    return _sha(parts)

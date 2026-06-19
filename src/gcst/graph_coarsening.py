"""Topology-preserving graph views for G5.59.

The first G5.59 representation is intentionally conservative: an identity
``corridor graph`` where every traversable grid cell remains represented.  It is
a valid control for the corridor-junction abstraction because it preserves
connectivity and shortest paths exactly while avoiding the G5.58 stride-sample
bug.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .graph_data import GraphData, build_graph, connected_components
from .traffic_prior import shortest_path


@dataclass
class CorridorGraph:
    graph: GraphData
    cell_assignment: dict[tuple[int, int], int]
    superedge_lengths: np.ndarray
    shortest_path_distortion_mean: float
    shortest_path_distortion_max: float
    original_component_count: int
    coarsened_component_count: int


def build_corridor_graph(row: dict[str, Any]) -> CorridorGraph:
    graph = build_graph(row, max_nodes=None)
    assignment = {cell: idx for idx, cell in enumerate(graph.cells)}
    lengths = np.ones((graph.edge_index.shape[1],), dtype=np.float32)
    component_count = connected_components(graph.cells, graph.edge_index)
    return CorridorGraph(
        graph=graph,
        cell_assignment=assignment,
        superedge_lengths=lengths,
        shortest_path_distortion_mean=0.0,
        shortest_path_distortion_max=0.0,
        original_component_count=component_count,
        coarsened_component_count=component_count,
    )


def audit_corridor_graph(row: dict[str, Any], pairs: list[tuple[tuple[int, int], tuple[int, int]]] | None = None) -> dict[str, Any]:
    corridor = build_corridor_graph(row)
    graph = corridor.graph
    distortions: list[float] = []
    if pairs:
        for start, goal in pairs:
            full_path = shortest_path(graph, start, goal)
            coarse_path = shortest_path(corridor.graph, start, goal)
            if full_path and coarse_path:
                distortions.append((len(coarse_path) - len(full_path)) / max(1, len(full_path) - 1))
    return {
        "topology_id": graph.topology_id,
        "map": graph.map_name,
        "free_cell_count": len(graph.cells),
        "represented_cell_count": len(corridor.cell_assignment),
        "all_cells_assigned": len(corridor.cell_assignment) == len(graph.cells),
        "original_component_count": corridor.original_component_count,
        "coarsened_component_count": corridor.coarsened_component_count,
        "component_count_unchanged": corridor.original_component_count == corridor.coarsened_component_count,
        "shortest_path_distortion_mean": float(np.mean(distortions)) if distortions else corridor.shortest_path_distortion_mean,
        "shortest_path_distortion_max": float(np.max(distortions)) if distortions else corridor.shortest_path_distortion_max,
        "connectivity_preserved": corridor.original_component_count == corridor.coarsened_component_count,
        **graph.hashes,
    }

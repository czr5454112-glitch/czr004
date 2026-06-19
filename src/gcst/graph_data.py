"""Real grid-graph materialization and features for G5.58."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .map_hash import adjacency_edges, free_cells, is_free, load_grid, physical_hashes


@dataclass
class GraphData:
    topology_id: str
    map_name: str
    width: int
    height: int
    cells: list[tuple[int, int]]
    node_features: np.ndarray
    edge_index: np.ndarray
    edge_features: np.ndarray
    hashes: dict[str, Any]


NODE_FEATURE_NAMES = [
    "x_norm",
    "y_norm",
    "degree_norm",
    "dead_end",
    "corridor",
    "intersection",
    "local_obstacle_density_r1",
    "border_distance_norm",
    "centrality_proxy",
]

EDGE_FEATURE_NAMES = [
    "dx",
    "dy",
    "edge_length",
    "corridor_axis_alignment",
    "edge_betweenness_proxy",
    "shortest_path_flow_prior",
    "opposing_flow_prior",
    "flow_imbalance",
    "head_on_pressure",
]


def _degree_lookup(grid: list[str]) -> dict[tuple[int, int], int]:
    free = set(free_cells(grid))
    deg: dict[tuple[int, int], int] = {}
    for x, y in free:
        deg[(x, y)] = sum((x + dx, y + dy) in free for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)])
    return deg


def _local_obstacle_density(grid: list[str], x: int, y: int) -> float:
    height = len(grid)
    width = max((len(row) for row in grid), default=0)
    total = 0
    blocked = 0
    for yy in range(y - 1, y + 2):
        for xx in range(x - 1, x + 2):
            if xx == x and yy == y:
                continue
            total += 1
            if not (0 <= xx < width and 0 <= yy < height and is_free(grid[yy][xx])):
                blocked += 1
    return blocked / max(1, total)


def build_graph(row: dict[str, Any], max_nodes: int | None = None) -> GraphData:
    width, height, grid, _source = load_grid(row)
    cells = free_cells(grid)
    if max_nodes and len(cells) > max_nodes:
        stride = max(1, len(cells) // max_nodes)
        cells = cells[::stride][:max_nodes]
    cell_to_idx = {cell: idx for idx, cell in enumerate(cells)}
    degree = _degree_lookup(grid)
    node_rows = []
    for x, y in cells:
        deg = degree.get((x, y), 0)
        border_dist = min(x, y, max(0, width - 1 - x), max(0, height - 1 - y))
        max_border = max(1, min(width, height) / 2)
        centrality = 1.0 - abs((x / max(1, width - 1)) - 0.5) - abs((y / max(1, height - 1)) - 0.5)
        node_rows.append(
            [
                x / max(1, width - 1),
                y / max(1, height - 1),
                deg / 4.0,
                float(deg <= 1),
                float(deg == 2),
                float(deg >= 3),
                _local_obstacle_density(grid, x, y),
                min(1.0, border_dist / max_border),
                max(0.0, centrality),
            ]
        )
    edges = []
    edge_rows = []
    for x, y, nx, ny in adjacency_edges(grid):
        if (x, y) not in cell_to_idx or (nx, ny) not in cell_to_idx:
            continue
        src = cell_to_idx[(x, y)]
        dst = cell_to_idx[(nx, ny)]
        dx = nx - x
        dy = ny - y
        src_deg = max(1, degree.get((x, y), 1))
        dst_deg = max(1, degree.get((nx, ny), 1))
        edges.append((src, dst))
        edge_rows.append(
            [
                float(dx),
                float(dy),
                1.0,
                float((dx != 0 and src_deg == 2 and dst_deg == 2) or (dy != 0 and src_deg == 2 and dst_deg == 2)),
                1.0 / min(src_deg, dst_deg),
                0.0,
                0.0,
                0.0,
                0.0,
            ]
        )
    edge_index = np.asarray(edges, dtype=np.int64).T if edges else np.zeros((2, 0), dtype=np.int64)
    return GraphData(
        topology_id=str(row.get("topology_id", "")),
        map_name=str(row.get("map", row.get("map_name", ""))),
        width=width,
        height=height,
        cells=cells,
        node_features=np.asarray(node_rows, dtype=np.float32),
        edge_index=edge_index,
        edge_features=np.asarray(edge_rows, dtype=np.float32),
        hashes=physical_hashes(row),
    )


def graph_summary(graph: GraphData) -> dict[str, Any]:
    node_mean = graph.node_features.mean(axis=0) if len(graph.node_features) else np.zeros(len(NODE_FEATURE_NAMES))
    edge_mean = graph.edge_features.mean(axis=0) if len(graph.edge_features) else np.zeros(len(EDGE_FEATURE_NAMES))
    out = {
        "topology_id": graph.topology_id,
        "map": graph.map_name,
        "node_count": int(graph.node_features.shape[0]),
        "directed_edge_count": int(graph.edge_features.shape[0]),
        "node_feature_count": int(graph.node_features.shape[1]) if graph.node_features.ndim == 2 else 0,
        "edge_feature_count": int(graph.edge_features.shape[1]) if graph.edge_features.ndim == 2 else 0,
    }
    for name, value in zip(NODE_FEATURE_NAMES, node_mean):
        out[f"node_mean_{name}"] = float(value)
    for name, value in zip(EDGE_FEATURE_NAMES, edge_mean):
        out[f"edge_mean_{name}"] = float(value)
    out.update(graph.hashes)
    return out

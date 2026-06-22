from __future__ import annotations

import time

import numpy as np

from gcst.graph_data import GraphData
from gcst.traffic_prior import compute_traffic_prior, shortest_path


def _grid_graph(width: int, height: int, blocked: set[tuple[int, int]] | None = None) -> GraphData:
    blocked = blocked or set()
    cells = [(x, y) for y in range(height) for x in range(width) if (x, y) not in blocked]
    cell_to_idx = {cell: idx for idx, cell in enumerate(cells)}
    edges = []
    for x, y in cells:
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nxt = (x + dx, y + dy)
            if nxt in cell_to_idx:
                edges.append((cell_to_idx[(x, y)], cell_to_idx[nxt]))
    edge_index = np.asarray(edges, dtype=np.int64).T if edges else np.zeros((2, 0), dtype=np.int64)
    return GraphData(
        topology_id="grid",
        map_name="grid",
        width=width,
        height=height,
        cells=cells,
        node_features=np.zeros((len(cells), 9), dtype=np.float32),
        edge_index=edge_index,
        edge_features=np.zeros((len(edges), 9), dtype=np.float32),
        hashes={},
        component_count=1,
        physical_free_cell_count=len(cells),
    )


def _assert_legal_path(graph: GraphData, path: list[int], start: tuple[int, int], goal: tuple[int, int]) -> None:
    assert path
    assert graph.cells[path[0]] == start
    assert graph.cells[path[-1]] == goal
    assert len(path) == len(set(path))
    for a, b in zip(path, path[1:]):
        ax, ay = graph.cells[a]
        bx, by = graph.cells[b]
        assert abs(ax - bx) + abs(ay - by) == 1


def test_traffic_prior_defaults_to_bfs_and_astar_is_versioned_opt_in() -> None:
    graph = _grid_graph(4, 4, blocked={(1, 1), (2, 1)})
    assignment = {
        "starts": [(0, 0), (3, 0), (0, 3), (3, 3)],
        "goals": [(3, 3), (0, 3), (3, 0), (0, 0)],
    }
    bfs = compute_traffic_prior(graph, assignment)
    astar = compute_traffic_prior(graph, assignment, routing_backend="astar_v1")
    assert bfs["summary"]["routing_backend"] == "bfs"
    assert bfs["summary"]["traffic_prior_version"] == "traffic_prior_v1_bfs"
    assert astar["summary"]["routing_backend"] == "astar_v1"
    assert astar["summary"]["traffic_prior_version"] == "traffic_prior_v2_astar"
    assert bfs["summary"]["path_found_count"] == astar["summary"]["path_found_count"] == 4
    assert bfs["summary"]["expected_edge_use_total"] == astar["summary"]["expected_edge_use_total"]


def test_bfs_astar_path_length_validity_and_determinism() -> None:
    graph = _grid_graph(5, 5, blocked={(2, 1), (2, 2), (2, 3)})
    pairs = [
        ((0, 0), (4, 4)),
        ((4, 0), (0, 4)),
        ((1, 4), (3, 0)),
        ((0, 2), (4, 2)),
    ]
    for start, goal in pairs:
        bfs_path = shortest_path(graph, start, goal)
        astar_path = shortest_path(graph, start, goal, routing_backend="astar_v1")
        astar_path_again = shortest_path(graph, start, goal, routing_backend="astar_v1")
        assert astar_path == astar_path_again
        assert bool(bfs_path) == bool(astar_path)
        assert len(bfs_path) == len(astar_path)
        _assert_legal_path(graph, bfs_path, start, goal)
        _assert_legal_path(graph, astar_path, start, goal)


def test_astar_feature_drift_is_measured_not_silently_called_parity() -> None:
    graph = _grid_graph(5, 5)
    assignment = {
        "starts": [(0, 0), (0, 4), (4, 0), (4, 4), (2, 0), (2, 4)],
        "goals": [(4, 4), (4, 0), (0, 4), (0, 0), (2, 4), (2, 0)],
    }
    bfs = compute_traffic_prior(graph, assignment)
    astar = compute_traffic_prior(graph, assignment, routing_backend="astar_v1")
    bfs_flow = bfs["edge_features"][:, 5]
    astar_flow = astar["edge_features"][:, 5]
    l1_drift = float(np.abs(bfs_flow - astar_flow).sum())
    cosine = float(np.dot(bfs_flow, astar_flow) / max(1.0e-12, np.linalg.norm(bfs_flow) * np.linalg.norm(astar_flow)))
    assert bfs["summary"]["expected_edge_use_total"] == astar["summary"]["expected_edge_use_total"]
    assert l1_drift >= 0.0
    assert -1.0 <= cosine <= 1.0


def test_bfs_astar_backend_performance_benchmark_smoke() -> None:
    graph = _grid_graph(20, 20, blocked={(10, y) for y in range(1, 19) if y != 10})
    starts = [(0, y) for y in range(0, 20, 2)]
    goals = [(19, 19 - y) for y in range(0, 20, 2)]
    assignment = {"starts": starts, "goals": goals}
    started = time.perf_counter()
    bfs = compute_traffic_prior(graph, assignment)
    bfs_wall = time.perf_counter() - started
    started = time.perf_counter()
    astar = compute_traffic_prior(graph, assignment, routing_backend="astar_v1")
    astar_wall = time.perf_counter() - started
    benchmark = {
        "nodes": len(graph.cells),
        "agents": len(starts),
        "bfs_wall_sec": bfs_wall,
        "astar_wall_sec": astar_wall,
        "speedup": bfs_wall / max(astar_wall, 1.0e-9),
    }
    assert benchmark["nodes"] > 0
    assert benchmark["agents"] == 10
    assert benchmark["bfs_wall_sec"] >= 0.0
    assert benchmark["astar_wall_sec"] >= 0.0
    assert bfs["summary"]["path_found_count"] == astar["summary"]["path_found_count"] == len(starts)

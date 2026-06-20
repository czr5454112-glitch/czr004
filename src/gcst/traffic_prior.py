"""Pre-run traffic priors from actual start-goal assignments."""

from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np

from .graph_data import GraphData


def _adjacency(graph: GraphData) -> dict[int, list[int]]:
    out: dict[int, list[int]] = {i: [] for i in range(len(graph.cells))}
    if graph.edge_index.size:
        for src, dst in graph.edge_index.T:
            out[int(src)].append(int(dst))
    return out


def _shortest_path_from_lookup(
    adj: dict[int, list[int]],
    cell_to_idx: dict[tuple[int, int], int],
    start: tuple[int, int],
    goal: tuple[int, int],
) -> list[int]:
    if start not in cell_to_idx or goal not in cell_to_idx:
        return []
    src = cell_to_idx[start]
    dst = cell_to_idx[goal]
    parent = {src: -1}
    q: deque[int] = deque([src])
    while q:
        cur = q.popleft()
        if cur == dst:
            break
        for nxt in adj.get(cur, []):
            if nxt not in parent:
                parent[nxt] = cur
                q.append(nxt)
    if dst not in parent:
        return []
    path = [dst]
    while path[-1] != src:
        path.append(parent[path[-1]])
    return list(reversed(path))


def shortest_path(graph: GraphData, start: tuple[int, int], goal: tuple[int, int]) -> list[int]:
    cell_to_idx = {cell: i for i, cell in enumerate(graph.cells)}
    return _shortest_path_from_lookup(_adjacency(graph), cell_to_idx, start, goal)


def compute_traffic_prior(graph: GraphData, assignment: dict[str, Any]) -> dict[str, Any]:
    adj = _adjacency(graph)
    cell_to_idx = {cell: i for i, cell in enumerate(graph.cells)}
    edge_to_idx = {(int(s), int(d)): i for i, (s, d) in enumerate(graph.edge_index.T)} if graph.edge_index.size else {}
    counts = np.zeros((graph.edge_features.shape[0],), dtype=np.float32)
    opposite = np.zeros_like(counts)
    paths = []
    path_found = 0
    expected_edge_use_total = 0.0
    for start, goal in zip(assignment["starts"], assignment["goals"]):
        path = _shortest_path_from_lookup(adj, cell_to_idx, start, goal)
        paths.append(path)
        if path:
            path_found += 1
            expected_edge_use_total += max(0, len(path) - 1)
        for a, b in zip(path, path[1:]):
            idx = edge_to_idx.get((a, b))
            if idx is not None:
                counts[idx] += 1.0
                rev = edge_to_idx.get((b, a))
                if rev is not None:
                    opposite[rev] += 1.0
    if counts.size:
        norm = max(float(counts.max()), 1.0)
        flow = counts / norm
        opp = opposite / max(float(opposite.max()), 1.0)
        imbalance = np.abs(flow - opp)
        head_on = np.minimum(flow, opp)
        edge_features = graph.edge_features.copy()
        edge_features[:, 5] = flow
        edge_features[:, 6] = opp
        edge_features[:, 7] = imbalance
        edge_features[:, 8] = head_on
    else:
        edge_features = graph.edge_features.copy()
        flow = opp = imbalance = head_on = np.zeros((0,), dtype=np.float32)
    summary = {
        "edge_use_total": float(counts.sum()),
        "edge_use_max": float(counts.max()) if counts.size else 0.0,
        "edge_use_mean": float(counts.mean()) if counts.size else 0.0,
        "opposing_flow_total": float(opposite.sum()),
        "opposing_flow_ratio": float(opposite.sum() / max(1.0, counts.sum())),
        "path_overlap_concentration": float((counts.max() / max(1.0, counts.sum()))) if counts.size else 0.0,
        "bottleneck_demand": float(np.percentile(flow, 95)) if flow.size else 0.0,
        "head_on_pressure": float(head_on.mean()) if head_on.size else 0.0,
        "flow_imbalance_mean": float(imbalance.mean()) if imbalance.size else 0.0,
        "paths_computed": len(paths),
        "path_found_count": int(path_found),
        "path_found_rate": float(path_found / max(1, len(paths))),
        "expected_edge_use_total": float(expected_edge_use_total),
        "flow_mass_preservation_ratio": float(counts.sum() / max(1.0, expected_edge_use_total)),
        "nonzero_flow": bool(float(counts.sum()) > 0.0),
    }
    node_counts = np.zeros((len(graph.cells),), dtype=np.float32)
    for path in paths:
        for node in path:
            if 0 <= int(node) < len(node_counts):
                node_counts[int(node)] += 1.0
    if node_counts.size and node_counts.sum() > 0:
        normalized_nodes = node_counts / max(float(node_counts.max()), 1.0)
        wait_pressure = {
            "vertex_wait_pressure_max": float(normalized_nodes.max()),
            "vertex_wait_pressure_mean": float(normalized_nodes.mean()),
            "vertex_wait_pressure_nonzero_rate": float((normalized_nodes > 0).mean()),
        }
    else:
        wait_pressure = {
            "vertex_wait_pressure_max": 0.0,
            "vertex_wait_pressure_mean": 0.0,
            "vertex_wait_pressure_nonzero_rate": 0.0,
        }
    return {"edge_features": edge_features, "summary": summary, "paths": paths, "wait_pressure": wait_pressure}

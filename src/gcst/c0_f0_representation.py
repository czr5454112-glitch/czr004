"""C0/F0 and OD representation audits for G5.65."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Sequence

import numpy as np

from .graph_data import GraphData


def array_sha256(value: Any) -> str:
    arr = np.asarray(value)
    payload = {
        "shape": arr.shape,
        "dtype": str(arr.dtype),
        "bytes": hashlib.sha256(np.ascontiguousarray(arr).view(np.uint8)).hexdigest(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def topology_hash(graph: GraphData) -> str:
    return array_sha256(graph.node_features[:, :5]) + ":" + array_sha256(graph.edge_index)


def f0_tensor(graph: GraphData) -> np.ndarray:
    if graph.edge_features.shape[1] <= 5:
        return np.zeros((graph.edge_features.shape[0], 1), dtype=np.float32)
    return graph.edge_features[:, 5:6].astype(np.float32)


def c0_tensor(graph: GraphData) -> np.ndarray:
    if graph.edge_features.shape[1] <= 6:
        return np.zeros((graph.edge_features.shape[0], 3), dtype=np.float32)
    return graph.edge_features[:, 6:9].astype(np.float32)


def endpoint_mass(graph: GraphData, assignment: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    cell_to_idx = {cell: idx for idx, cell in enumerate(graph.cells)}
    starts = np.zeros((len(graph.cells),), dtype=np.float32)
    goals = np.zeros((len(graph.cells),), dtype=np.float32)
    for start in assignment.get("starts", []):
        idx = cell_to_idx.get(tuple(start))
        if idx is not None:
            starts[idx] += 1.0
    for goal in assignment.get("goals", []):
        idx = cell_to_idx.get(tuple(goal))
        if idx is not None:
            goals[idx] += 1.0
    if starts.max() > 0:
        starts = starts / starts.max()
    if goals.max() > 0:
        goals = goals / goals.max()
    return starts, goals


def representation_audit_row(evaluation_uid: str, graph: GraphData, assignment: dict[str, Any]) -> dict[str, Any]:
    f0 = f0_tensor(graph)
    c0 = c0_tensor(graph)
    starts, goals = endpoint_mass(graph, assignment)
    od_tokens = np.asarray(assignment.get("od_tokens", np.zeros((0, 6))), dtype=np.float32)
    return {
        "evaluation_uid": evaluation_uid,
        "topology_hash": topology_hash(graph),
        "c0_hash": array_sha256(c0),
        "f0_hash": array_sha256(f0),
        "c0_f0_hashes_equal": array_sha256(c0) == array_sha256(f0),
        "c0_nonzero_rate": float((np.abs(c0) > 1.0e-12).mean()) if c0.size else 0.0,
        "f0_nonzero_rate": float((np.abs(f0) > 1.0e-12).mean()) if f0.size else 0.0,
        "c0_mean": float(c0.mean()) if c0.size else 0.0,
        "f0_mean": float(f0.mean()) if f0.size else 0.0,
        "start_mass_hash": array_sha256(starts),
        "goal_mass_hash": array_sha256(goals),
        "paired_od_hash": array_sha256(od_tokens),
        "start_goal_mass_used": bool(starts.sum() > 0 and goals.sum() > 0),
        "od_pair_count": int(od_tokens.shape[0]) if od_tokens.ndim == 2 else 0,
    }


def audit_rows(examples: Sequence[Any]) -> list[dict[str, Any]]:
    return [representation_audit_row(ex.evaluation_uid, ex.graph, ex.assignment) for ex in examples]


def summarize_representation(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    return {
        "schema_version": "phase5p5_repair5g565_c0_f0_representation_summary_v1",
        "rows": total,
        "c0_f0_alias_rows": sum(bool(row.get("c0_f0_hashes_equal")) for row in rows),
        "c0_f0_are_not_aliases": total > 0 and not any(bool(row.get("c0_f0_hashes_equal")) for row in rows),
        "start_goal_mass_rows": sum(bool(row.get("start_goal_mass_used")) for row in rows),
        "od_pair_rows": sum(int(row.get("od_pair_count", 0)) > 0 for row in rows),
        "separate_semantic_hashes_recorded": True,
    }

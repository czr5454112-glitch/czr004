from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.features_laur import build_aggregate_checkpoint_features


class DummyTopology:
    free_cells = 100
    density_denominator = 100
    width = 10
    height = 10
    obstacle_ratio = 0.0

    def degree(self, vertex_id: int) -> int:
        return 4 if vertex_id >= 0 else 0


def _checkpoint_row() -> dict:
    return {
        "agents": 20,
        "iteration": 1,
        "node_budget": 10,
        "time_limit_sec": 8,
        "max_iterations": 4,
        "sum_of_loss_ratio_this_iteration": None,
        "committed_count": 10,
        "blocked_count": 4,
        "wait_event_count": 1,
        "goal_wait_ignored_count": 0,
        "traffic_before_nonzero_edges": 1,
        "traffic_after_nonzero_edges": 2,
        "traffic_before_max_raw": 1,
        "traffic_after_max_raw": 4,
        "traffic_after_max_normalized": 10,
        "raw_before_topk": [{"from_id": 1, "to_id": 2, "raw": 1}],
        "raw_after_topk": [{"from_id": 1, "to_id": 2, "raw": 3}],
        "normalized_after_topk": [{"from_id": 1, "to_id": 2, "weight": 10}],
        "topk_blocked_edge_concentration": 0.75,
        "blocked_edge_entropy": 1.25,
    }


def test_checkpoint_trace_summary_features_are_used_without_raw_trace() -> None:
    features = build_aggregate_checkpoint_features(
        _checkpoint_row(),
        [],
        topology=DummyTopology(),
    )

    assert features["topk_blocked_edge_concentration"] == 0.75
    assert features["entropy_edge_usage"] == 1.25


def test_raw_trace_rows_take_precedence_over_checkpoint_trace_summary() -> None:
    checkpoint = _checkpoint_row()
    checkpoint["topk_blocked_edge_concentration"] = 0.0
    checkpoint["blocked_edge_entropy"] = 0.0
    traces = [
        {"kind": "blocked", "from_id": 1, "to_id": 2},
        {"kind": "blocked", "from_id": 1, "to_id": 2},
        {"kind": "blocked", "from_id": 3, "to_id": 4},
    ]

    features = build_aggregate_checkpoint_features(
        checkpoint,
        traces,
        topology=DummyTopology(),
    )

    expected_entropy = -((2 / 3) * math.log(2 / 3) + (1 / 3) * math.log(1 / 3))
    assert features["topk_blocked_edge_concentration"] == 2 / 3
    assert math.isclose(features["entropy_edge_usage"], expected_entropy)

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.features_laur import FEATURE_NAMES, FEATURE_SET  # noqa: E402
from czr004_teacher.token_dataset_laur import (  # noqa: E402
    audit_token_update_dataset_rows,
    build_token_update_dataset_rows,
    validate_token_update_dataset_row,
)
from czr004_teacher.token_features_laur import EXECUTABLE_RULE_IDS  # noqa: E402


def _checkpoint() -> dict:
    return {
        "schema_version": "phase4_laur_checkpoint_v1",
        "run_id": "run-1",
        "checkpoint_id": "run-1__iter0",
        "split": "train",
        "map_name": "empty-16-16",
        "map_path": "external/lacam2/scripts/map/empty-16-16.map",
        "agents": 50,
        "seed": 1,
        "time_limit_sec": 3,
        "max_iterations": 4,
        "iteration": 0,
        "node_budget": 0,
        "trace_event_count": 15,
        "committed_count": 10,
        "blocked_count": 5,
        "wait_event_count": 2,
        "goal_wait_ignored_count": 1,
        "blocked_unique_edge_count": 4,
        "topk_blocked_edge_count": 2,
        "traffic_after_nonzero_edges": 3,
        "raw_before_topk": [{"from_id": 1, "to_id": 2, "raw": 1}],
        "raw_after_topk": [{"from_id": 1, "to_id": 2, "raw": 3}, {"from_id": 2, "to_id": 3, "raw": 2}],
        "normalized_after_topk": [
            {"from_id": 1, "to_id": 2, "weight": 10},
            {"from_id": 2, "to_id": 3, "weight": 6},
        ],
    }


def _dataset_v1(rule_id: str) -> dict:
    features = {name: float(index + 1) for index, name in enumerate(FEATURE_NAMES)}
    return {
        "schema_version": "phase4_laur_update_dataset_v1",
        "run_id": "run-1",
        "checkpoint_id": "run-1__iter0",
        "split": "train",
        "map_name": "empty-16-16",
        "agents": 50,
        "seed": 1,
        "iteration": 0,
        "feature_set": FEATURE_SET,
        "feature_names": list(FEATURE_NAMES),
        "features": features,
        "feature_vector": [features[name] for name in FEATURE_NAMES],
        "target": {
            "rule_class": rule_id,
            "rule_class_index": 8 if rule_id == "neutral_additive" else EXECUTABLE_RULE_IDS.index(rule_id),
            "rule_vocab": [*EXECUTABLE_RULE_IDS, "neutral_additive"],
            "harmful_update": True,
            "harmful_rule_ids": ["block_heavy"],
            "delta_ratio_best": 0.0 if rule_id == "neutral_additive" else 0.02,
            "label_confidence": 0.02,
            "best_rule_id": "additive_ltm" if rule_id == "neutral_additive" else rule_id,
            "neutral": rule_id == "neutral_additive",
        },
        "source": {},
    }


def _probe(rule_id: str, delta: float, harmful: bool = False) -> dict:
    return {
        "schema_version": "phase4_laur_update_label_v1",
        "run_id": "run-1",
        "checkpoint_id": "run-1__iter0",
        "rule_id": rule_id,
        "delta_ratio_vs_additive": delta,
        "harmful": harmful,
    }


def test_repair2_token_dataset_cleans_neutral_executable_target() -> None:
    rows = build_token_update_dataset_rows(
        [_checkpoint()],
        [_dataset_v1("neutral_additive")],
        [
            _probe("additive_ltm", 0.0),
            _probe("commit_heavy", 0.001),
            _probe("block_heavy", -0.02, harmful=True),
        ],
        repo_root_path=ROOT,
        max_edge_tokens=4,
        max_trace_tokens=4,
    )

    assert len(rows) == 1
    row = rows[0]
    assert validate_token_update_dataset_row(row) == []
    assert row["schema_version"] == "phase4_laur_update_dataset_v2"
    assert row["target"]["rule_class_original"] == "neutral_additive"
    assert row["target"]["best_rule_executable"] == "additive_ltm"
    assert row["target"]["is_neutral_label"] is True
    assert row["rule_vocab"] == EXECUTABLE_RULE_IDS
    assert abs(sum(row["soft_rule_target"]) - 1.0) < 1e-9
    assert row["edge_tokens"]
    assert row["trace_tokens"]
    assert "split" not in row["global_feature_names"]
    assert "map_name" not in row["global_feature_names"]

    audit = audit_token_update_dataset_rows(rows)
    assert audit["passed"] is True
    assert audit["executable_label_distribution"] == {"additive_ltm": 1}

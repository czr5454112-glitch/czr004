from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.stable_attention_dataset_laur import (  # noqa: E402
    audit_stable_attention_dataset_rows,
    build_stable_attention_dataset_rows,
    validate_stable_attention_dataset_row,
)
from czr004_teacher.stable_attention_tokens_laur import EXECUTABLE_RULE_IDS  # noqa: E402


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
        "solution_found_this_iteration": True,
        "sum_of_loss_this_iteration": 120,
        "sum_of_loss_ratio_this_iteration": 1.2,
        "trace_event_count": 15,
        "committed_count": 10,
        "blocked_count": 5,
        "wait_event_count": 2,
        "goal_wait_ignored_count": 1,
        "traffic_before_nonzero_edges": 2,
        "traffic_before_max_raw": 4,
        "raw_before_topk": [
            {"from_id": 1, "to_id": 2, "raw": 4},
            {"from_id": 2, "to_id": 3, "raw": 1},
        ],
        "raw_after_topk": [
            {"from_id": 1, "to_id": 2, "raw": 7},
            {"from_id": 2, "to_id": 3, "raw": 2},
            {"from_id": 3, "to_id": 3, "raw": 1},
        ],
        "normalized_after_topk": [
            {"from_id": 1, "to_id": 2, "weight": 10},
            {"from_id": 2, "to_id": 3, "weight": 3},
            {"from_id": 3, "to_id": 3, "weight": 1},
        ],
    }


def _stable_dataset() -> dict:
    return {
        "schema_version": "phase4_laur_update_dataset_v1",
        "run_id": "run-1",
        "checkpoint_id": "run-1__iter0",
        "split": "train",
        "map_name": "empty-16-16",
        "agents": 50,
        "seed": 1,
        "iteration": 0,
        "feature_names": ["agents"],
        "feature_vector": [50.0],
        "target": {
            "rule_class": "neutral_additive",
            "rule_class_index": 8,
            "rule_vocab": [*EXECUTABLE_RULE_IDS, "neutral_additive"],
            "best_rule_id": "additive_ltm",
            "delta_ratio_best": 0.0,
            "harmful_update": True,
            "harmful_rule_ids": ["block_heavy"],
            "neutral": True,
            "stable_target": {
                "schema_version": "phase4_laur_stable_target_v1",
                "original_target": {
                    "rule_class": "commit_heavy",
                    "rule_class_index": 1,
                    "best_rule_id": "commit_heavy",
                    "delta_ratio_best": 0.02,
                    "label_confidence": 0.02,
                    "neutral": False,
                },
                "stable_rule": "neutral_additive",
                "stable_executable": "additive_ltm",
                "stable_delta": 0.0,
                "best_rule": "commit_heavy",
                "best_delta": 0.003,
                "best_minus_stable": 0.003,
                "tie_rules": ["additive_ltm", "commit_heavy"],
                "tie_count": 2,
                "reason": "additive_within_tie_band",
            },
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


def _rows() -> list[dict]:
    probes = [
        _probe("additive_ltm", 0.0),
        _probe("commit_heavy", 0.003),
        _probe("block_heavy", -0.02, harmful=True),
        _probe("block_light", 0.001),
        _probe("wait_light", 0.0),
        _probe("wait_heavy", -0.001),
        _probe("decay_095", 0.0),
        _probe("decay_090", 0.0),
    ]
    return build_stable_attention_dataset_rows(
        [_checkpoint()],
        [_stable_dataset()],
        probes,
        repo_root_path=ROOT,
        max_edge_tokens=4,
        max_trace_tokens=4,
        soft_temperature=0.010,
        soft_hard_mix=0.5,
    )


def test_stable_target_fields_present() -> None:
    row = _rows()[0]
    assert validate_stable_attention_dataset_row(row) == []
    for key in (
        "rule_class_original",
        "rule_class_stable",
        "rule_class_executable",
        "is_neutral_label",
        "best_minus_second_margin",
        "best_minus_additive_margin",
        "rule_delta_vector",
        "rule_harmful_vector",
        "soft_rule_target_stable",
        "soft_rule_target_probe",
    ):
        assert key in row["target"]


def test_original_and_stable_targets_preserved() -> None:
    target = _rows()[0]["target"]
    assert target["rule_class_original"] == "commit_heavy"
    assert target["rule_class_stable"] == "neutral_additive"
    assert target["stable_target_reason"] == "additive_within_tie_band"


def test_neutral_additive_executes_as_additive_ltm() -> None:
    target = _rows()[0]["target"]
    assert target["rule_class_stable"] == "neutral_additive"
    assert target["rule_class_executable"] == "additive_ltm"
    assert target["rule_class_executable_index"] == 0


def test_executable_rule_vocab_has_8_rules() -> None:
    row = _rows()[0]
    assert row["rule_vocab"] == EXECUTABLE_RULE_IDS
    assert len(row["rule_vocab"]) == 8


def test_soft_targets_sum_to_one() -> None:
    row = _rows()[0]
    assert abs(sum(row["target"]["soft_rule_target_stable"]) - 1.0) < 1e-9
    assert abs(sum(row["target"]["soft_rule_target_probe"]) - 1.0) < 1e-9


def test_rule_delta_vector_order_matches_rule_vocab() -> None:
    row = _rows()[0]
    delta_by_rule = dict(zip(row["rule_vocab"], row["target"]["rule_delta_vector"]))
    assert delta_by_rule["additive_ltm"] == 0.0
    assert delta_by_rule["commit_heavy"] == 0.003
    assert delta_by_rule["block_heavy"] == -0.02
    assert row["target"]["rule_harmful_vector"][EXECUTABLE_RULE_IDS.index("block_heavy")] == 1


def test_dataset_audit_reports_masks_and_no_leakage() -> None:
    audit = audit_stable_attention_dataset_rows(_rows())
    assert audit["passed"] is True
    assert audit["rule_vocab_count"] == 8
    assert audit["schema_error_count"] == 0
    assert audit["split_leakage_error_count"] == 0

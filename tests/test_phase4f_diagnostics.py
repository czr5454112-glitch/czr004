from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eval.diagnose_laur_phase4f import (  # noqa: E402
    build_feature_drift_rows,
    family_for_rule,
    margin_detail_for_checkpoint,
    safety_metrics_for_threshold,
)


def test_margin_detail_tracks_near_tie_candidates() -> None:
    dataset_row = {
        "checkpoint_id": "ckpt-1",
        "split": "validation",
        "map_name": "maze-32-32-4",
        "agents": 100,
        "seed": 3,
        "iteration": 2,
        "target": {
            "rule_class": "commit_heavy",
            "best_rule_id": "commit_heavy",
            "delta_ratio_best": 0.02,
            "label_confidence": 0.02,
            "neutral": False,
        },
    }
    probe_rows = [
        {"checkpoint_id": "ckpt-1", "rule_id": "additive_ltm", "delta_ratio_vs_additive": 0.0, "harmful": False},
        {"checkpoint_id": "ckpt-1", "rule_id": "commit_heavy", "delta_ratio_vs_additive": 0.020, "harmful": False},
        {"checkpoint_id": "ckpt-1", "rule_id": "block_heavy", "delta_ratio_vs_additive": 0.019, "harmful": True},
    ]

    detail = margin_detail_for_checkpoint(dataset_row, probe_rows)

    assert detail["delta_best_rule_id"] == "commit_heavy"
    assert round(detail["best_minus_second_margin"], 6) == 0.001
    assert detail["within_0_0025_count"] == 2
    assert detail["harmful_candidate_count"] == 1


def test_safety_threshold_reports_fallback_tradeoff() -> None:
    rows = [
        {"harmful_update": "1", "harmful_update_probability": "0.9", "predicted_rule_delta_ratio_vs_additive": "-0.04"},
        {"harmful_update": "1", "harmful_update_probability": "0.4", "predicted_rule_delta_ratio_vs_additive": "0.02"},
        {"harmful_update": "0", "harmful_update_probability": "0.2", "predicted_rule_delta_ratio_vs_additive": "0.03"},
    ]

    metrics = safety_metrics_for_threshold(rows, 0.5)

    assert metrics["tp"] == 1
    assert metrics["fn"] == 1
    assert metrics["fp"] == 0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 0.5
    assert round(metrics["fallback_rate"], 6) == round(1 / 3, 6)
    assert round(metrics["mean_delta_after_gate"], 6) == round((0.0 + 0.02 + 0.03) / 3, 6)


def test_feature_drift_and_rule_family_helpers() -> None:
    rows = [
        {"split": "train", "map_name": "empty", "feature_names": ["a"], "feature_vector": [1.0]},
        {"split": "train", "map_name": "empty", "feature_names": ["a"], "feature_vector": [2.0]},
        {"split": "validation", "map_name": "maze", "feature_names": ["a"], "feature_vector": [4.0]},
    ]

    drift_rows = build_feature_drift_rows(rows)
    all_drift = [row for row in drift_rows if row["comparison"] == "validation_all"][0]

    assert all_drift["feature"] == "a"
    assert all_drift["train_n"] == 2
    assert all_drift["other_n"] == 1
    assert all_drift["standardized_mean_diff"] > 0
    assert family_for_rule("wait_heavy") == "wait"
    assert family_for_rule("neutral_additive") == "additive_or_neutral"

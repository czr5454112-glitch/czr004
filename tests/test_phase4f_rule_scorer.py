from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from train.train_laur_rule_scorer import (  # noqa: E402
    RULE_PARAM_NAMES,
    binary_metrics,
    rule_feature_vector,
    topk_indices,
)


def test_rule_feature_vector_contains_one_hot_and_params() -> None:
    rules = ["additive_ltm", "block_heavy"]
    params = {
        "alpha_commit": 1.0,
        "alpha_block": 1.5,
        "alpha_wait": 1.0,
        "rho_decay": 1.0,
        "saturation_scale": 1.0,
        "contraflow_penalty": 0.0,
        "force_additive": False,
    }

    vector = rule_feature_vector("block_heavy", params, rules)

    assert vector[:2] == [0.0, 1.0]
    assert len(vector) == len(rules) + len(RULE_PARAM_NAMES)
    assert vector[-1] == 0.0


def test_topk_and_binary_metrics_helpers() -> None:
    assert topk_indices([0.1, 0.9, 0.2], 2) == [1, 2]

    metrics = binary_metrics([1, 1, 0], [1, 0, 1])

    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1"] == 0.5

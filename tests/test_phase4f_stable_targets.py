from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.features_laur import FEATURE_NAMES, FEATURE_SET  # noqa: E402
from czr004_teacher.stable_targets_laur import (  # noqa: E402
    build_stable_target_rows,
    stable_rule_for_probe_group,
)
from czr004_teacher.update_sequences import validate_update_dataset_row  # noqa: E402


RULES = ["additive_ltm", "commit_heavy", "block_heavy", "neutral_additive"]


def _probe(rule_id: str, delta: float) -> dict:
    return {
        "checkpoint_id": "c0",
        "rule_id": rule_id,
        "delta_ratio_vs_additive": delta,
    }


def _dataset_row() -> dict:
    features = {name: float(index + 1) for index, name in enumerate(FEATURE_NAMES)}
    return {
        "schema_version": "phase4_laur_update_dataset_v1",
        "run_id": "run",
        "checkpoint_id": "c0",
        "split": "train",
        "map_name": "map",
        "agents": 10,
        "seed": 1,
        "iteration": 0,
        "feature_set": FEATURE_SET,
        "feature_names": list(FEATURE_NAMES),
        "features": features,
        "feature_vector": [features[name] for name in FEATURE_NAMES],
        "target": {
            "rule_class": "commit_heavy",
            "rule_class_index": RULES.index("commit_heavy"),
            "rule_vocab": list(RULES),
            "harmful_update": False,
            "harmful_rule_ids": [],
            "delta_ratio_best": 0.010,
            "label_confidence": 0.010,
            "best_rule_id": "commit_heavy",
            "neutral": False,
        },
        "source": {},
    }


def test_stable_rule_prefers_additive_inside_tie_band() -> None:
    stable = stable_rule_for_probe_group(
        [_probe("additive_ltm", 0.0), _probe("commit_heavy", 0.004)],
        tie_epsilon=0.005,
        neutral_delta_threshold=0.005,
    )

    assert stable["stable_rule"] == "neutral_additive"
    assert stable["reason"] == "best_below_neutral_threshold"


def test_stable_target_rows_update_target_and_preserve_original() -> None:
    rows = build_stable_target_rows(
        [_dataset_row()],
        [_probe("additive_ltm", 0.0), _probe("commit_heavy", 0.008), _probe("block_heavy", 0.010)],
        tie_epsilon=0.005,
        neutral_delta_threshold=0.005,
        rule_priority=["additive_ltm", "commit_heavy", "block_heavy"],
    )

    assert len(rows) == 1
    row = rows[0]
    assert validate_update_dataset_row(row) == []
    assert row["target"]["rule_class"] == "commit_heavy"
    assert row["target"]["stable_target"]["original_target"]["rule_class"] == "commit_heavy"
    assert row["target"]["stable_target"]["best_rule"] == "block_heavy"
    assert row["target"]["stable_target"]["best_minus_stable"] > 0.0

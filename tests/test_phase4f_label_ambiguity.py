from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eval.diagnose_laur_label_ambiguity import (  # noqa: E402
    checkpoint_margin_detail,
    prediction_regret_rows,
)


def _dataset_row() -> dict:
    return {
        "checkpoint_id": "c0",
        "split": "validation",
        "map_name": "map",
        "agents": 10,
        "seed": 1,
        "iteration": 0,
        "target": {"rule_class": "neutral_additive"},
    }


def _probe(rule_id: str, delta: float) -> dict:
    return {
        "checkpoint_id": "c0",
        "rule_id": rule_id,
        "delta_ratio_vs_additive": delta,
        "harmful": False,
    }


def test_margin_detail_maps_neutral_to_executable_additive() -> None:
    detail = checkpoint_margin_detail(
        _dataset_row(),
        [_probe("additive_ltm", 0.0), _probe("commit_heavy", 0.002)],
        epsilons=[0.005],
    )

    assert detail["target_rule_original"] == "neutral_additive"
    assert detail["target_rule_executable"] == "additive_ltm"
    assert detail["best_probe_rule"] == "commit_heavy"
    assert detail["target_in_tie_eps_0_005"] == 1


def test_prediction_regret_counts_near_tie_prediction() -> None:
    records = prediction_regret_rows(
        model_label="m",
        prediction_rows=[{"checkpoint_id": "c0", "predicted_rule": "additive_ltm"}],
        dataset_rows_by_checkpoint={"c0": _dataset_row()},
        probe_rows_by_checkpoint={
            "c0": [_probe("additive_ltm", 0.0), _probe("commit_heavy", 0.002)]
        },
        epsilons=[0.001, 0.005],
    )

    assert len(records) == 1
    assert records[0]["exact_executable_correct"] == 1
    assert records[0]["pred_within_eps_0_001"] == 0
    assert records[0]["pred_within_eps_0_005"] == 1

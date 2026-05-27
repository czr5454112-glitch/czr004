from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from train.train_laur_stable_attention import model_selection_score, phase4f_gate, select_rule  # noqa: E402
from eval.eval_laur_stable_attention import advanced_promotion_gate  # noqa: E402


def test_selection_policy_falls_back_when_all_non_additive_unsafe() -> None:
    result = select_rule(
        [0.0, 0.10, 0.08, 0.03, 0.02, 0.01, 0.0, 0.0],
        [0.0, 0.9, 0.8, 0.7, 0.7, 0.8, 0.9, 0.9],
        safety_threshold=0.10,
        safety_penalty=0.02,
        confidence_margin=0.002,
    )
    assert result["selected_index"] == 0
    assert result["fallback_reason"] == "unsafe"


def test_selection_policy_uses_confidence_margin_against_additive() -> None:
    result = select_rule(
        [0.0, 0.001, 0.0005, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.0] * 8,
        safety_threshold=0.10,
        safety_penalty=0.02,
        confidence_margin=0.002,
    )
    assert result["selected_index"] == 0
    assert result["fallback_reason"] == "low_confidence"


def test_selection_policy_selects_safe_positive_rule() -> None:
    result = select_rule(
        [0.0, 0.004, 0.03, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.0, 0.05, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0],
        safety_threshold=0.10,
        safety_penalty=0.02,
        confidence_margin=0.002,
    )
    assert result["selected_index"] == 2
    assert result["fallback_reason"] == "selected"


def test_phase4f_gate_keeps_original_thresholds() -> None:
    gate = phase4f_gate(
        {
            "rule_top1_accuracy": 0.35,
            "rule_top3_accuracy": 0.70,
            "harmful_update_recall": 0.80,
            "harmful_update_precision": 0.30,
            "predicted_rule_validation_mean_delta_ratio": 0.001,
        }
    )
    gate["validation_non_neutral"]["value"] = 50
    gate["validation_non_neutral"]["passed"] = True
    gate["passed"] = all(bool(value["passed"]) for value in gate.values() if isinstance(value, dict))
    assert gate["passed"] is True


def test_advanced_promotion_gate_requires_any_condition_not_all() -> None:
    summary = {
        "metrics_by_split": {
            "validation": {
                "predicted_rule_validation_mean_delta_ratio": 0.001,
                "rule_top3_accuracy": 0.60,
                "harmful_update_recall": 0.90,
            }
        }
    }
    baseline = {"metrics_by_split": {"validation": {"rule_top3_accuracy": 0.80}}}

    gate = advanced_promotion_gate([summary], repair3_baseline=baseline)

    assert gate["condition_b_average_delta_positive"]["passed"] is True
    assert gate["condition_c_top3_not_worse_than_repair3_minus_002"]["passed"] is False
    assert gate["passed"] is True


def test_phase4f_selection_score_prioritizes_gate_balance() -> None:
    high_top3_low_safety = {
        "rule_top1_accuracy": 0.45,
        "rule_top3_accuracy": 0.80,
        "harmful_update_recall": 0.90,
        "harmful_update_precision": 0.15,
        "predicted_rule_validation_mean_delta_ratio": 0.004,
    }
    lower_ranking_balanced_safety = {
        "rule_top1_accuracy": 0.36,
        "rule_top3_accuracy": 0.71,
        "harmful_update_recall": 0.82,
        "harmful_update_precision": 0.30,
        "predicted_rule_validation_mean_delta_ratio": 0.001,
    }

    assert model_selection_score(
        lower_ranking_balanced_safety, mode="phase4f_gate"
    ) > model_selection_score(high_top3_low_safety, mode="phase4f_gate")

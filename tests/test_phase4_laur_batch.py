from scripts.run_phase4_laur_batch import phase4f_performance_gate


def test_phase4f_performance_gate_rejects_weak_validation_metrics() -> None:
    eval_summary = {
        "metrics_by_split": {
            "validation": {
                "rule_top1_accuracy": 0.1375,
                "rule_top3_accuracy": 0.4875,
                "harmful_update_recall": 0.0714,
                "harmful_update_precision": 0.4,
                "predicted_rule_validation_mean_delta_ratio": 0.002,
                "neutral_additive_rate": 0.1125,
            }
        }
    }

    gate = phase4f_performance_gate(eval_summary, validation_non_neutral_checkpoints=58)

    assert gate["phase4f_validation_non_neutral_gate"]
    assert not gate["phase4f_validation_rule_top1_gate"]
    assert not gate["phase4f_validation_rule_top3_gate"]
    assert not gate["phase4f_harmful_update_recall_gate"]
    assert gate["phase4f_harmful_update_precision_gate"]
    assert not gate["phase4f_performance_gate_passed"]


def test_phase4f_performance_gate_accepts_threshold_metrics() -> None:
    eval_summary = {
        "metrics_by_split": {
            "validation": {
                "rule_top1_accuracy": 0.35,
                "rule_top3_accuracy": 0.70,
                "harmful_update_recall": 0.80,
                "harmful_update_precision": 0.30,
                "predicted_rule_validation_mean_delta_ratio": 0.0,
                "neutral_additive_rate": 0.2,
            }
        }
    }

    gate = phase4f_performance_gate(eval_summary, validation_non_neutral_checkpoints=50)

    assert gate["phase4f_performance_gate_passed"]

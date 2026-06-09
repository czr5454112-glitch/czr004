from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from czr004_teacher.stable_attention_tokens_laur import EXECUTABLE_RULE_IDS  # noqa: E402
from eval.eval_laur_repair5_safe_reranker import safe_reranker_records  # noqa: E402
from eval.eval_laur_repair5_selected_safety_alignment import summarize_alignment  # noqa: E402
from eval.eval_laur_repair5_composite_inference import composite_records  # noqa: E402
from eval.eval_laur_repair5_final_gate import safety_calibration_label  # noqa: E402
from run_phase5p5_laur_diagnostic_preflight import build_preflight_plan  # noqa: E402
from run_phase5p5_laur_diagnostic_preflight_exec import summarize_rows  # noqa: E402
from train.train_laur_attention_native import calibrate_safety_thresholds_from_scores  # noqa: E402
from train.train_laur_attention_reranker import build_reranker_example  # noqa: E402


def _label_row() -> dict:
    target_index = EXECUTABLE_RULE_IDS.index("block_heavy")
    return {
        "split": "validation",
        "checkpoint_id": "case-1",
        "run_id": "run-1",
        "map_name": "empty-8-8",
        "agents": 16,
        "seed": 1,
        "iteration": 0,
        "decision_target": "use_nonadditive",
        "target_rule": "block_heavy",
        "target": {"target_rule_index": target_index},
        "probe_delta_vector": [0.0, 0.01, 0.08, 0.06, 0.02, 0.01, -0.01, -0.01],
        "risk_adjusted_utility_vector": [0.0, 0.01, 0.08, 0.06, 0.02, 0.01, -0.01, -0.01],
        "probe_harmful_vector": [False, False, False, True, False, False, False, False],
        "rule_ids": EXECUTABLE_RULE_IDS,
        "has_nonadditive_opportunity": True,
        "has_high_margin_nonadditive_opportunity": True,
        "audit": {"label_params": {"opportunity_margin": 0.01}},
    }


def _eval_row() -> dict:
    return {
        "checkpoint_id": "case-1",
        "split": "validation",
        "rule_scores": json.dumps([0.0, 0.40, 0.45, 0.50, 0.10, 0.05, -0.10, -0.20]),
        "harmful_probs": json.dumps([0.01, 0.10, 0.10, 0.90, 0.05, 0.05, 0.05, 0.05]),
        "opportunity_prob": 0.90,
        "defer_prob": 0.10,
    }


def test_repair5c_composite_recovers_safe_target_from_top3() -> None:
    metrics, records = composite_records(
        labels={"case-1": _label_row()},
        ranking_rows={"case-1": _eval_row()},
        safety_rows={"case-1": _eval_row()},
        anti_rows={"case-1": _eval_row()},
        calibration={"threshold_by_rule": {rule: 0.50 for rule in EXECUTABLE_RULE_IDS}},
        modes=["top3_per_rule_safety_utility"],
        top_k=3,
        default_threshold=0.50,
        opportunity_threshold=0.50,
        defer_threshold=0.50,
    )

    assert records[0]["selected_rule"] == "block_heavy"
    assert metrics["top3_per_rule_safety_utility"]["rule_top1"] == 1.0
    assert metrics["top3_per_rule_safety_utility"]["selected_vs_additive_delta"] > 0.0


def test_attention_native_per_family_safety_calibration_is_available() -> None:
    records = [
        {"rule_index": 1, "rule_id": "commit_heavy", "label": 1, "score": 0.80},
        {"rule_index": 1, "rule_id": "commit_heavy", "label": 0, "score": 0.10},
        {"rule_index": 2, "rule_id": "block_heavy", "label": 1, "score": 0.70},
        {"rule_index": 3, "rule_id": "block_light", "label": 0, "score": 0.20},
    ]

    calibration = calibrate_safety_thresholds_from_scores(
        records,
        candidate_thresholds=[0.10, 0.50, 0.75],
        min_recall=0.80,
        min_precision=0.30,
        mode="per_family",
    )

    assert calibration["threshold_by_family"]["commit"] == 0.75
    assert calibration["threshold_by_family"]["block"] == 0.50
    assert calibration["threshold_by_family"]["additive"] > 1.0


def test_reranker_example_targets_top3_rule_when_available() -> None:
    example = build_reranker_example(
        _label_row(),
        _eval_row(),
        thresholds=[0.50] * len(EXECUTABLE_RULE_IDS),
        top_k=3,
    )

    assert example is not None
    target_rule = EXECUTABLE_RULE_IDS[example["candidate_rule_indices"][example["target_pos"]]]
    assert target_rule == "block_heavy"


def test_final_gate_labels_safety_calibration_candidates_without_unlocking() -> None:
    safety = {
        "harmful_recall": {"passed": True},
        "harmful_precision": {"passed": False},
        "passed": False,
    }

    assert (
        safety_calibration_label(
            safety,
            safety_calibration_report={"per_rule_threshold_pass": True, "per_family_threshold_pass": False},
        )
        == "candidate_for_composite_or_preflight"
    )


def test_diagnostic_preflight_plan_never_unlocks_phase5p5() -> None:
    plan = build_preflight_plan(
        composite_summary={
            "metrics_by_mode": {
                "top3_per_rule_safety_utility": {
                    "selected_vs_additive_delta": 0.01,
                    "harmful_recall": 0.90,
                    "high_margin_capture": 0.50,
                    "utility_regret_to_oracle": 0.0,
                }
            }
        }
    )

    assert plan["diagnostic_preflight_warranted"] is True
    assert plan["phase5p5_allowed"] is False
    assert plan["phase6_allowed"] is False


def test_selected_safety_alignment_counts_selected_false_negative() -> None:
    records = [
        {
            "mode": "top3_per_rule_safety_utility",
            "map_name": "empty-8-8",
            "selected_rule": "block_heavy",
            "harmful_labels": json.dumps([0, 0, 1, 0, 0, 0, 0, 0]),
            "harmful_predictions": json.dumps([0, 0, 0, 0, 0, 0, 0, 0]),
        }
    ]

    summary = summarize_alignment(
        records,
        calibration={"threshold_by_rule": {rule: 0.50 for rule in EXECUTABLE_RULE_IDS}},
        default_threshold=0.50,
    )

    mode = summary["top3_per_rule_safety_utility"]
    assert mode["all_rule_safety"]["fn"] == 1
    assert mode["selected_rule_safety"]["fn"] == 1
    assert mode["selected_harmful_false_negative_by_rule"] == {"block_heavy": 1}


def test_safe_reranker_masks_unsafe_top_candidate_and_recovers_target() -> None:
    metrics_records, metrics = safe_reranker_records(
        labels={"case-1": _label_row()},
        eval_rows={"case-1": _eval_row()},
        calibration={"threshold_by_rule": {rule: 0.50 for rule in EXECUTABLE_RULE_IDS}},
        scorer=None,
        top_k=3,
        safety_scope="per_rule",
        default_threshold=0.50,
        opportunity_threshold=0.50,
        defer_threshold=0.50,
        min_utility_margin=0.0,
    )

    assert metrics_records[0]["selected_rule"] == "block_heavy"
    assert metrics_records[0]["selected_decision"] == "use_nonadditive"
    assert metrics["selected_harmful_rate"] == 0.0
    assert metrics["selected_vs_additive_delta"] > 0.0


def test_preflight_exec_summary_reports_laur_update_rates_without_unlocking() -> None:
    rows = [
        {
            "method": "repair3_safe_runtime",
            "map": "empty-8-8",
            "scen": "empty-8-8-random-1.scen",
            "agents": 16,
            "seed": 1,
            "time_limit_sec": 1.0,
            "objective": "sum_of_loss",
            "valid_instance": True,
            "success": True,
            "feasible": True,
            "sum_of_loss": 12,
            "lower_bound": 10,
            "sum_of_loss_ratio": 1.2,
            "makespan": 5,
            "runtime_ms": 10.0,
            "time_to_first_solution_ms": 4.0,
            "returned_solutions_count": 1,
            "loop_cnt": 2,
            "expanded_nodes": 3,
            "high_level_expansions": 2,
            "low_level_pibt_calls": 7,
            "laur_inference_total_ms": 0.2,
            "laur_inference_count": 2,
            "laur_additive_fallback_count": 1,
            "laur_safety_disabled_count": 0,
            "laur_selected_rules": {"block_heavy": 1},
            "git_commit": "test",
            "external_lacam2_commit": "test",
            "branch": "test",
            "dirty": "test",
            "binary_path": "test",
            "config_path": "test",
            "platform": "test",
        }
    ]

    summary = summarize_rows(rows)

    assert summary[0]["non_additive_update_rate"] == 0.5
    assert summary[0]["fallback_defer_rate"] == 0.5
    assert summary[0]["selected_harmful_update_rate"] is None

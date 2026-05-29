from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from train.losses_laur_attention_native import (  # noqa: E402
    AttentionNativeLossWeights,
    laur_attention_native_loss,
)
from eval.eval_laur_anti_escape import resolve_path as resolve_anti_escape_path  # noqa: E402
from eval.eval_laur_repair5_layered_gate import summarize_one  # noqa: E402
from eval.eval_laur_repair5_final_gate import aggregate_final_gate  # noqa: E402
from train.train_laur_attention_native import (  # noqa: E402
    anti_escape_metrics,
    attention_native_gate,
    calibrate_safety_thresholds_from_scores,
    model_selection_score,
    select_attention_native,
)
from models.laur_attention_native import EDGE_TRACE_TRANSFORMER_NAME, build_model  # noqa: E402


def _record(**overrides: object) -> dict:
    base = {
        "selected_decision": "use_nonadditive",
        "predicted_rule": "commit_heavy",
        "selected_rule_harmful": False,
        "selected_vs_additive_delta": 0.020,
        "opportunity_margin": 0.010,
        "has_nonadditive_opportunity": True,
        "has_high_margin_nonadditive_opportunity": True,
    }
    base.update(overrides)
    return base


def test_attention_native_selection_defers_when_opportunity_head_is_low() -> None:
    result = select_attention_native(
        [0.0, 0.10, 0.08, 0.03, 0.02, 0.01, 0.0, 0.0],
        [0.0] * 8,
        opportunity_prob=0.10,
        defer_prob=0.10,
        safety_threshold=0.10,
        safety_penalty=0.02,
        opportunity_threshold=0.50,
        defer_threshold=0.50,
        confidence_margin=0.002,
    )

    assert result["selected_decision"] == "defer_ltm"
    assert result["fallback_reason"] == "low_opportunity"


def test_attention_native_selection_uses_best_safe_nonadditive() -> None:
    result = select_attention_native(
        [0.0, 0.02, 0.04, 0.03, 0.02, 0.01, 0.0, 0.0],
        [0.0, 0.05, 0.20, 0.05, 0.05, 0.05, 0.05, 0.05],
        opportunity_prob=0.90,
        defer_prob=0.10,
        safety_threshold=0.10,
        safety_penalty=0.02,
        opportunity_threshold=0.50,
        defer_threshold=0.50,
        confidence_margin=0.002,
    )

    assert result["selected_decision"] == "use_nonadditive"
    assert result["selected_index"] == 3


def test_attention_native_gate_keeps_original_phase4f_thresholds() -> None:
    gate = attention_native_gate(
        {
            "rule_top1_accuracy": 0.35,
            "rule_top3_accuracy": 0.70,
            "harmful_update_recall": 0.80,
            "harmful_update_precision": 0.30,
            "predicted_rule_validation_mean_delta_ratio": 0.001,
            "validation_non_neutral": 50,
        }
    )

    assert gate["passed"] is True


def test_anti_escape_gate_fails_inconclusive_when_high_margin_count_is_low() -> None:
    summary = anti_escape_metrics([_record()] * 3)

    assert summary["passed"] is False
    assert summary["inconclusive"] is True
    assert summary["reason"] == "validation high-margin opportunity count below threshold"


def test_anti_escape_gate_flags_additive_escape_on_high_margin_samples() -> None:
    records = [
        _record(selected_decision="defer_ltm", predicted_rule="additive_ltm", selected_vs_additive_delta=0.0)
        for _ in range(50)
    ]

    summary = anti_escape_metrics(records)

    assert summary["validation_high_margin_opportunity_count"] == 50
    assert summary["high_margin_nonadditive_capture_rate"] == 0.0
    assert summary["avoidable_additive_or_defer_rate"] == 1.0
    assert summary["passed"] is False


def test_anti_escape_gate_passes_capture_thresholds() -> None:
    records = [_record() for _ in range(50)] + [
        _record(
            selected_decision="defer_ltm",
            predicted_rule="additive_ltm",
            selected_vs_additive_delta=0.0,
        )
        for _ in range(10)
    ]

    summary = anti_escape_metrics(records)

    assert summary["validation_high_margin_opportunity_count"] == 60
    assert summary["high_margin_nonadditive_capture_rate"] >= 0.40
    assert summary["avoidable_additive_or_defer_rate"] <= 0.60
    assert summary["passed"] is True


def test_model_selection_prefers_balanced_safety_over_anti_only() -> None:
    safety_balanced = {
        "rule_top1_accuracy": 0.18,
        "rule_top3_accuracy": 0.64,
        "harmful_update_recall": 0.84,
        "harmful_update_precision": 0.27,
        "selected_vs_additive_delta_mean": 0.003,
        "attention_native_gate": attention_native_gate(
            {
                "rule_top1_accuracy": 0.18,
                "rule_top3_accuracy": 0.64,
                "harmful_update_recall": 0.84,
                "harmful_update_precision": 0.27,
                "predicted_rule_validation_mean_delta_ratio": 0.003,
                "validation_non_neutral": 293,
            }
        ),
        "anti_escape_gate": {"passed": False, "high_margin_nonadditive_capture_rate": 0.25},
    }
    anti_only = {
        "rule_top1_accuracy": 0.20,
        "rule_top3_accuracy": 0.60,
        "harmful_update_recall": 0.34,
        "harmful_update_precision": 0.24,
        "selected_vs_additive_delta_mean": 0.006,
        "attention_native_gate": attention_native_gate(
            {
                "rule_top1_accuracy": 0.20,
                "rule_top3_accuracy": 0.60,
                "harmful_update_recall": 0.34,
                "harmful_update_precision": 0.24,
                "predicted_rule_validation_mean_delta_ratio": 0.006,
                "validation_non_neutral": 293,
            }
        ),
        "anti_escape_gate": {"passed": True, "high_margin_nonadditive_capture_rate": 0.52},
    }

    assert model_selection_score(safety_balanced) > model_selection_score(anti_only)


def test_harmful_pairwise_loss_penalizes_misordered_harmful_logits() -> None:
    torch = pytest.importorskip("torch")
    outputs = {
        "rule_score": torch.zeros((1, 3), dtype=torch.float32),
        "delta_pred": torch.zeros((1, 3), dtype=torch.float32),
        "harmful_logit": torch.tensor([[-1.0, 1.0, 1.0]], dtype=torch.float32),
        "opportunity_logit": torch.zeros((1,), dtype=torch.float32),
        "defer_logit": torch.zeros((1,), dtype=torch.float32),
        "family_logits": torch.zeros((1, 3, 2), dtype=torch.float32),
    }
    targets = {
        "soft_utility_target": torch.full((1, 3), 1.0 / 3.0),
        "utility_target": torch.zeros((1, 3), dtype=torch.float32),
        "harmful_target": torch.tensor([[1.0, 0.0, 0.0]], dtype=torch.float32),
        "opportunity_target": torch.zeros((1,), dtype=torch.float32),
        "defer_target": torch.zeros((1,), dtype=torch.float32),
        "family_target": torch.zeros((1,), dtype=torch.long),
        "use_nonadditive_mask": torch.zeros((1,), dtype=torch.bool),
        "rule_target": torch.zeros((1,), dtype=torch.long),
        "pairwise_dominance": torch.zeros((1, 3, 3), dtype=torch.float32),
        "pairwise_observed": torch.zeros((1, 3, 3), dtype=torch.float32),
        "anti_escape_sample": torch.zeros((1,), dtype=torch.float32),
        "anti_escape_candidate_mask": torch.zeros((1, 3), dtype=torch.bool),
    }

    loss = laur_attention_native_loss(
        outputs,
        targets,
        additive_index=0,
        weights=AttentionNativeLossWeights(lambda_harmful_pairwise=1.0, harmful_pairwise_margin=0.5),
    )

    assert float(loss["harmful_pairwise_margin"]) > 0.0


def test_rule_margin_loss_targets_attention_native_rule() -> None:
    torch = pytest.importorskip("torch")
    outputs = {
        "rule_score": torch.tensor([[0.0, 0.10, 0.00], [0.0, 0.10, 0.00]], dtype=torch.float32),
        "delta_pred": torch.zeros((2, 3), dtype=torch.float32),
        "harmful_logit": torch.zeros((2, 3), dtype=torch.float32),
        "opportunity_logit": torch.zeros((2,), dtype=torch.float32),
        "defer_logit": torch.zeros((2,), dtype=torch.float32),
        "family_logits": torch.zeros((2, 3, 2), dtype=torch.float32),
    }
    targets = {
        "soft_utility_target": torch.full((2, 3), 1.0 / 3.0),
        "utility_target": torch.zeros((2, 3), dtype=torch.float32),
        "harmful_target": torch.zeros((2, 3), dtype=torch.float32),
        "opportunity_target": torch.ones((2,), dtype=torch.float32),
        "defer_target": torch.zeros((2,), dtype=torch.float32),
        "family_target": torch.zeros((2,), dtype=torch.long),
        "use_nonadditive_mask": torch.ones((2,), dtype=torch.bool),
        "rule_target": torch.tensor([2, 1], dtype=torch.long),
        "high_margin_opportunity_mask": torch.tensor([1.0, 0.0], dtype=torch.float32),
        "pairwise_dominance": torch.zeros((2, 3, 3), dtype=torch.float32),
        "pairwise_observed": torch.zeros((2, 3, 3), dtype=torch.float32),
        "anti_escape_sample": torch.zeros((2,), dtype=torch.float32),
        "anti_escape_candidate_mask": torch.zeros((2, 3), dtype=torch.bool),
    }

    loss = laur_attention_native_loss(
        outputs,
        targets,
        additive_index=0,
        weights=AttentionNativeLossWeights(
            lambda_rule_ce=1.0,
            lambda_rule_margin=1.0,
            rule_margin=0.05,
            rule_margin_high_margin_weight=3.0,
        ),
    )

    assert float(loss["rule_ce"]) > 0.0
    assert float(loss["rule_margin"]) > 0.0


def test_high_margin_and_anti_candidate_safety_losses_are_available() -> None:
    torch = pytest.importorskip("torch")
    outputs = {
        "rule_score": torch.zeros((2, 3), dtype=torch.float32),
        "delta_pred": torch.zeros((2, 3), dtype=torch.float32),
        "harmful_logit": torch.tensor([[3.0, -1.0, -1.0], [-1.0, 3.0, 3.0]], dtype=torch.float32),
        "opportunity_logit": torch.zeros((2,), dtype=torch.float32),
        "defer_logit": torch.zeros((2,), dtype=torch.float32),
        "family_logits": torch.zeros((2, 3, 2), dtype=torch.float32),
    }
    targets = {
        "soft_utility_target": torch.full((2, 3), 1.0 / 3.0),
        "utility_target": torch.zeros((2, 3), dtype=torch.float32),
        "harmful_target": torch.tensor([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]], dtype=torch.float32),
        "opportunity_target": torch.ones((2,), dtype=torch.float32),
        "defer_target": torch.zeros((2,), dtype=torch.float32),
        "family_target": torch.zeros((2,), dtype=torch.long),
        "use_nonadditive_mask": torch.ones((2,), dtype=torch.bool),
        "rule_target": torch.zeros((2,), dtype=torch.long),
        "high_margin_opportunity_mask": torch.tensor([1.0, 0.0], dtype=torch.float32),
        "pairwise_dominance": torch.zeros((2, 3, 3), dtype=torch.float32),
        "pairwise_observed": torch.zeros((2, 3, 3), dtype=torch.float32),
        "anti_escape_sample": torch.tensor([0.0, 1.0], dtype=torch.float32),
        "anti_escape_candidate_mask": torch.tensor([[0, 0, 0], [0, 1, 0]], dtype=torch.bool),
    }

    loss = laur_attention_native_loss(
        outputs,
        targets,
        additive_index=0,
        weights=AttentionNativeLossWeights(
            lambda_high_margin_harmful=1.0,
            lambda_anti_candidate_safety=1.0,
        ),
    )

    assert float(loss["high_margin_harmful_bce"]) > 0.0
    assert float(loss["anti_candidate_safety_bce"]) > 0.0


def test_attention_native_model_supports_optional_mlp_heads() -> None:
    torch = pytest.importorskip("torch")
    model = build_model(
        EDGE_TRACE_TRANSFORMER_NAME,
        global_dim=5,
        edge_dim=4,
        trace_dim=3,
        rule_dim=6,
        num_rules=8,
        num_families=4,
        d_model=16,
        n_heads=4,
        n_layers=1,
        dropout=0.0,
        head_hidden_dim=12,
        head_dropout=0.0,
    )
    batch = {
        "global_features": torch.zeros(2, 5),
        "edge_tokens": torch.zeros(2, 3, 4),
        "edge_mask": torch.tensor([[1, 1, 0], [1, 0, 0]], dtype=torch.bool),
        "trace_tokens": torch.zeros(2, 2, 3),
        "trace_mask": torch.tensor([[1, 0], [1, 1]], dtype=torch.bool),
        "rule_tokens": torch.zeros(2, 8, 6),
    }

    outputs = model(batch)

    assert outputs["rule_score"].shape == (2, 8)
    assert outputs["harmful_logit"].shape == (2, 8)
    assert outputs["family_logits"].shape == (2, 8, 4)


def test_anti_escape_resolve_path_expands_seed_placeholder() -> None:
    root = Path("/tmp/root")

    resolved = resolve_anti_escape_path("outputs/tables/eval_seed{seed}.csv", root, seed=103)

    assert resolved == root / "outputs/tables/eval_seed103.csv"


def test_global_safety_calibration_uses_one_threshold() -> None:
    records = [
        {"rule_index": 0, "label": 1, "score": 0.90},
        {"rule_index": 1, "label": 1, "score": 0.80},
        {"rule_index": 0, "label": 0, "score": 0.10},
        {"rule_index": 1, "label": 0, "score": 0.20},
    ]

    calibration = calibrate_safety_thresholds_from_scores(
        records,
        candidate_thresholds=[0.10, 0.50, 0.85],
        min_recall=0.80,
        min_precision=0.30,
        mode="global",
    )

    assert calibration["threshold"] == 0.50
    assert len(set(calibration["thresholds"])) == 1
    assert calibration["train_metrics"]["recall"] == 1.0


def _passing_final_gate_summary(seed: int = 61) -> dict:
    metrics = {
        "rule_top1_accuracy": 0.35,
        "rule_top3_accuracy": 0.70,
        "harmful_update_recall": 0.80,
        "harmful_update_precision": 0.30,
        "predicted_rule_validation_mean_delta_ratio": 0.001,
        "validation_non_neutral": 100,
    }
    gate = attention_native_gate(metrics)
    return {
        "seed": seed,
        "phase4f_gate": gate,
        "anti_escape_gate": {"passed": True},
        "metrics_by_split": {
            "validation": {
                **metrics,
                "attention_native_gate": gate,
            }
        },
    }


def test_repair5_final_gate_requires_explicit_phase4f_gate() -> None:
    summary = _passing_final_gate_summary()
    summary.pop("phase4f_gate")

    result = aggregate_final_gate([summary], label_audit={"passed": True}, required_seeds=[61])

    seed_result = result["seed_results"][0]
    assert seed_result["original_phase4f_gate_passed"] is False
    assert "phase4f_gate" in seed_result["missing_required_gate_fields"]
    assert result["runtime_allowed"] is False


def test_repair5_final_gate_requires_explicit_attention_native_gate() -> None:
    summary = _passing_final_gate_summary()
    summary["metrics_by_split"]["validation"].pop("attention_native_gate")

    result = aggregate_final_gate([summary], label_audit={"passed": True}, required_seeds=[61])

    seed_result = result["seed_results"][0]
    assert seed_result["attention_native_gate_passed"] is False
    assert "metrics_by_split.validation.attention_native_gate" in seed_result["missing_required_gate_fields"]
    assert result["runtime_allowed"] is False


def test_repair5_layered_gate_allows_development_without_runtime(tmp_path: Path) -> None:
    audit_path = tmp_path / "outputs/reports/phase4f_repair5_attention_native_label_audit.json"
    audit_path.parent.mkdir(parents=True)
    audit_path.write_text('{"passed": true}\n', encoding="utf-8")
    summary_path = tmp_path / "outputs/reports/phase4f_repair5_attention_native_eval_seed61_summary.json"
    summary_path.write_text(
        """{
          "seed": 61,
          "dataset": "artifacts/teacher/laur/full_repair5_attention_native/update_labels/data.jsonl",
          "phase4f_gate": {"passed": false},
          "anti_escape_gate": {
            "passed": false,
            "validation_high_margin_opportunity_count": 80,
            "high_margin_nonadditive_capture_rate": 0.30,
            "avoidable_additive_or_defer_rate": 0.70
          },
          "metrics_by_split": {
            "validation": {
              "rule_top1_accuracy": 0.26,
              "rule_top3_accuracy": 0.61,
              "harmful_update_recall": 0.71,
              "harmful_update_precision": 0.26,
              "predicted_rule_validation_mean_delta_ratio": 0.001,
              "selected_vs_additive_delta_mean": 0.002,
              "attention_native_gate": {"passed": false}
            }
          }
        }""",
        encoding="utf-8",
    )

    result = summarize_one(summary_path, root=tmp_path, reference_capture=0.0, reference_fallback=1.0)

    assert result["development_gate"]["passed"] is True
    assert result["promotion_candidate_gate"]["passed"] is False
    assert result["runtime_claim_seed_gate"]["passed"] is False
    assert result["interpretation"] == "early_promising_not_promotable"


def test_repair5_layered_gate_keeps_runtime_strict(tmp_path: Path) -> None:
    audit_path = tmp_path / "outputs/reports/phase4f_repair5_attention_native_rawtrace_label_audit.json"
    audit_path.parent.mkdir(parents=True)
    audit_path.write_text('{"passed": true}\n', encoding="utf-8")
    summary_path = tmp_path / "outputs/reports/phase4f_repair5_rawtrace_edge_eval_seed61_summary.json"
    summary = _passing_final_gate_summary()
    summary["dataset"] = "artifacts/teacher/laur/full_repair5_attention_native_rawtrace/update_labels/data.jsonl"
    summary["anti_escape_gate"] = {
        "passed": True,
        "validation_high_margin_opportunity_count": 80,
        "high_margin_nonadditive_capture_rate": 0.50,
        "avoidable_additive_or_defer_rate": 0.40,
    }
    summary_path.write_text(__import__("json").dumps(summary), encoding="utf-8")

    result = summarize_one(summary_path, root=tmp_path, reference_capture=0.0, reference_fallback=1.0)

    assert result["development_gate"]["passed"] is True
    assert result["promotion_candidate_gate"]["passed"] is True
    assert result["runtime_claim_seed_gate"]["passed"] is True
    assert result["runtime_claim_seed_gate"]["note"].startswith("Diagnostic only")

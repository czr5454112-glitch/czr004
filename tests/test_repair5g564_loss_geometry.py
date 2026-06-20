from __future__ import annotations

import importlib
from pathlib import Path

import numpy as np
import pytest

from gcst.label_v52_set import CENSORED_UNKNOWN, ROW_CENSORED, classify_candidate_row, context_from_rows
from gcst.leakage_free_features import (
    PRE_SOLVER_SCALAR_FEATURES,
    RICH_ACTOR_INPUTS,
    actor_inputs_are_pre_solver_only,
    assert_no_forbidden_features,
    audit_feature_schema,
    export_schema_excludes_outcome_features,
    leakage_report_dict,
)
from gcst.loss_geometry_g564 import (
    ProjectedThetaOracle,
    adaptive_harmful_margin,
    conflicting_theta_pairs,
    floor_corrected_positive_loss_np,
    nearest_harmful_repulsion_loss_np,
    positive_softmin_floor,
    positive_wta_loss_np,
)
from gcst.replay_label_merge import merge_rows_by_context
from gcst.scaling_dataset import (
    assert_split_hashes_disjoint,
    fixed_validation_ids,
    make_grouped_split_manifest,
    nested_stratified_subsets,
    validation_manifest_sha256,
)
from gcst.label_v52_set import context_dataset_sha256
from gcst.theta_schema import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS


def row(
    uid: str,
    idx: int,
    *,
    safe: bool = True,
    comparable: bool = True,
    delta: float = 0.0,
    gain: bool = False,
    regression: bool = False,
    theta_shift: float = 0.0,
):
    out = {
        "g560_evaluation_uid": uid,
        "g560_instance_uid": f"inst_{uid}",
        "split": "train",
        "g560_physical_map_sha256": f"hash_{uid}",
        "map": "empty-8-8",
        "map_family": "empty",
        "agent_count": "8",
        "nominal_budget_ms": "500",
        "labelv51_development_safe": str(safe),
        "labelv51_comparable_quality": str(comparable),
        "quality_delta_vs_g556": str(delta),
        "labelv51_success_gain": str(gain),
        "labelv51_success_regression": str(regression),
        "candidate_uid": f"{uid}_{idx}",
    }
    for col_i, col in enumerate(THETA_NUMERIC_COLUMNS):
        out[col] = str(float(BASELINE_G556[col_i] + theta_shift))
    return out


def test_scaling_features_exclude_positive_rows():
    with pytest.raises(AssertionError):
        assert_no_forbidden_features(["agent_count", "positive_rows"])


def test_scaling_features_exclude_harmful_rows():
    audit = audit_feature_schema(["agent_count", "harmful_rows"])
    assert audit.allowed is False
    assert audit.forbidden_features == ("harmful_rows",)


def test_scaling_features_exclude_label_state():
    with pytest.raises(AssertionError):
        export_schema_excludes_outcome_features({"feature_names": ["agent_count", "label_state"]})


def test_actor_inputs_are_pre_solver_only():
    assert actor_inputs_are_pre_solver_only(RICH_ACTOR_INPUTS)
    with pytest.raises(AssertionError):
        actor_inputs_are_pre_solver_only([*PRE_SOLVER_SCALAR_FEATURES, "quality_delta_vs_g556"])


def test_export_schema_excludes_outcome_features():
    assert export_schema_excludes_outcome_features({"feature_names": list(PRE_SOLVER_SCALAR_FEATURES)})
    assert leakage_report_dict()["g563_scalar_scaling_valid_primary_evidence"] is False


def test_softmin_floor_computed_and_floor_corrected_zero_at_oracle():
    positives = np.stack([BASELINE_G556 - 0.1, BASELINE_G556 + 0.1]).astype(np.float32)
    floor = positive_softmin_floor(positives, tau=0.05)
    corrected = [floor_corrected_positive_loss_np(theta, positives, tau=0.05) for theta in positives]
    assert np.isfinite(floor)
    assert min(corrected) == pytest.approx(0.0, abs=1.0e-7)


def test_wta_loss_zero_at_selected_positive():
    positives = np.stack([BASELINE_G556 - 0.2, BASELINE_G556 + 0.2]).astype(np.float32)
    assert positive_wta_loss_np(positives[1], positives) == pytest.approx(0.0)


def test_nearest_harmful_not_diluted_by_far_harmful():
    theta = BASELINE_G556.copy()
    harmful = np.stack([BASELINE_G556 + 0.001, THETA_HI]).astype(np.float32)
    assert nearest_harmful_repulsion_loss_np(theta, harmful, margin=0.12) > 0.10


def test_adaptive_margin_feasible_for_separated_positive_harmful():
    positives = np.stack([BASELINE_G556 - 0.05]).astype(np.float32)
    harmful = np.stack([BASELINE_G556 + 0.05]).astype(np.float32)
    margin = adaptive_harmful_margin(positives, harmful, requested_margin=0.12)
    assert margin.feasible is True
    assert 0.0 < margin.feasible_margin <= 0.12


def test_conflicting_near_duplicate_flagged():
    context = context_from_rows(
        "ctx",
        [
            row("ctx", 0, safe=True, comparable=True, delta=-0.2, gain=True, theta_shift=0.0),
            row("ctx", 1, safe=False, comparable=True, delta=0.3, theta_shift=0.0001),
        ],
    )
    assert conflicting_theta_pairs(context, distance_threshold=0.01)


def test_censored_not_negative():
    state, _delta, _weight = classify_candidate_row(row("c", 0, safe=False, comparable=False))
    context = context_from_rows("c", [row("c", 0, safe=False, comparable=False)])
    assert state == ROW_CENSORED
    assert context.label_state == CENSORED_UNKNOWN


@pytest.mark.skipif(importlib.util.find_spec("torch") is None, reason="torch unavailable")
def test_optimizer_no_weight_decay_init_g556_and_no_sigmoid():
    oracle = ProjectedThetaOracle(lr=0.1)
    assert np.allclose(oracle.theta_numpy(), BASELINE_G556)
    assert oracle.uses_sigmoid_parameterization is False
    assert oracle.optimizer.param_groups[0]["weight_decay"] == 0.0


@pytest.mark.skipif(importlib.util.find_spec("torch") is None, reason="torch unavailable")
def test_projected_parameter_reaches_bounds():
    import torch

    oracle = ProjectedThetaOracle(initial_theta=THETA_HI + 99.0, lr=0.1)
    oracle.project_()
    assert np.allclose(oracle.theta_numpy(), THETA_HI)
    oracle.theta.data = torch.as_tensor(THETA_LO - 99.0, dtype=oracle.theta.dtype)
    oracle.project_()
    assert np.allclose(oracle.theta_numpy(), THETA_LO)


def test_nested_prefix_validation_manifest_and_physical_hashes_disjoint():
    rows = [
        {"evaluation_uid": f"ctx_{idx}", "physical_map_sha256": f"map_{idx}", "map_family": "m", "agent_count": idx % 3, "budget_ms": 500}
        for idx in range(20)
    ]
    manifest = make_grouped_split_manifest(rows, seed=564, split_key="g564_split")
    assert assert_split_hashes_disjoint(manifest, split_key="g564_split")
    subsets = nested_stratified_subsets([r for r in manifest if r["g564_split"] == "train"], [4, 8], seed=564)
    assert subsets[4] == subsets[8][:4]
    validation = fixed_validation_ids(manifest, split_key="g564_split")
    assert validation_manifest_sha256(validation) == validation_manifest_sha256(list(reversed(validation)))


def test_gate_rejects_g563_label_leakage():
    report = leakage_report_dict()
    assert "positive_rows" in report["g563_forbidden_features"]
    assert report["g564_forbidden_features"] == []


def test_replay_merge_changes_dataset_hash():
    base_rows = [row("ctx", 0, safe=True, comparable=True, delta=-0.1, gain=True, theta_shift=0.0)]
    replay_rows = [row("ctx", 1, safe=False, comparable=True, delta=0.4, theta_shift=0.2)]
    base = merge_rows_by_context(base_rows, [])
    merged = merge_rows_by_context(base_rows, replay_rows)
    assert context_dataset_sha256(base) != context_dataset_sha256(merged)

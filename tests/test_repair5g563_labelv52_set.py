from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from gcst.label_v52_set import (
    CENSORED_UNKNOWN,
    HARMFUL_SUPPORTED,
    MIXED_FRONTIER,
    ROW_CENSORED,
    ROW_HARMFUL_REGRESSION,
    ROW_POSITIVE,
    ROW_SAFE_NONIMPROVING,
    SAFE_NONIMPROVING_SUPPORTED,
    candidate_manifest_rows,
    classify_candidate_row,
    context_from_rows,
    label_v52_summary,
)
from gcst.replay_label_merge import merge_rows_by_context, replay_merge_summary
from gcst.run_provenance import append_progress, read_progress, summary_matches_progress
from gcst.scaling_dataset import (
    assert_split_hashes_disjoint,
    fixed_validation_ids,
    make_grouped_split_manifest,
    nested_stratified_subsets,
    validation_manifest_sha256,
)
from gcst.set_valued_actor_losses import harmful_repulsion_loss, positive_set_softmin_loss, set_valued_actor_loss
from gcst.theta_schema import BASELINE_G556, THETA_NUMERIC_COLUMNS


def row(uid: str, idx: int, *, safe: bool = True, comparable: bool = True, delta: float = 0.0, gain: bool = False, regression: bool = False, theta_shift: float = 0.0):
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


@pytest.mark.skipif(__import__("importlib").util.find_spec("torch") is None, reason="torch unavailable")
def test_multimodal_safe_set_is_not_averaged():
    import torch

    left = torch.tensor(BASELINE_G556 - 0.2, dtype=torch.float32)
    right = torch.tensor(BASELINE_G556 + 0.2, dtype=torch.float32)
    midpoint = torch.tensor(BASELINE_G556, dtype=torch.float32)
    safe = torch.stack([left, right])
    assert float(positive_set_softmin_loss(left, safe)) < float(positive_set_softmin_loss(midpoint, safe))
    assert float(positive_set_softmin_loss(right, safe)) < float(positive_set_softmin_loss(midpoint, safe))


def test_identity_rows_are_losslessly_preserved_and_positive_set_not_averaged():
    rows = [
        row("ctx", 0, delta=-0.4, gain=True, theta_shift=-0.2),
        row("ctx", 1, delta=-0.3, gain=True, theta_shift=0.2),
        row("ctx", 2, delta=0.5, safe=False, theta_shift=0.45),
        row("ctx", 3, comparable=False, safe=False),
    ]
    context = context_from_rows("ctx", rows)
    assert context.label_state == MIXED_FRONTIER
    assert context.original_row_count == 4
    assert context.positive_thetas.shape[0] == 2
    assert not hasattr(context, "target_theta")
    assert len(candidate_manifest_rows(context)) == len(rows)


def test_positive_only_filter_removed_and_censored_context_retained():
    context = context_from_rows("ctx", [row("ctx", 0, safe=False, comparable=False)])
    assert context.label_state == CENSORED_UNKNOWN
    summary = label_v52_summary([context])
    assert summary["contexts"] == 1
    assert summary["candidate_rows"] == 1
    assert summary["censored_rows_are_negative"] is False


def test_censored_is_not_harmful_and_success_regression_is_harmful():
    censored_state, _delta, _weight = classify_candidate_row(row("c", 0, safe=False, comparable=False))
    harmful_state, _delta, weight = classify_candidate_row(row("h", 0, safe=False, comparable=False, regression=True))
    assert censored_state == ROW_CENSORED
    assert harmful_state == ROW_HARMFUL_REGRESSION
    assert weight > 1.0


def test_noise_band_creates_tie_safe_nonimproving():
    rows = [row("tie", idx, safe=True, comparable=True, delta=0.005) for idx in range(4)]
    context = context_from_rows("tie", rows, quality_margin=0.01, min_verified_coverage=4)
    assert {candidate.row_state for candidate in context.candidates} == {ROW_SAFE_NONIMPROVING}
    assert context.label_state == SAFE_NONIMPROVING_SUPPORTED


def test_no_positive_observed_is_not_automatically_verified_noop():
    context = context_from_rows("thin", [row("thin", 0, safe=True, comparable=True, delta=0.0)], min_verified_coverage=4)
    assert context.label_state == CENSORED_UNKNOWN
    assert context.coverage["verified_no_positive_supported"] is False


def test_candidate_rows_do_not_count_as_independent_contexts():
    context = context_from_rows("ctx", [row("ctx", idx, delta=-0.1, gain=True) for idx in range(5)])
    summary = label_v52_summary([context])
    assert summary["candidate_rows"] == 5
    assert summary["independent_contexts"] == 1
    assert summary["candidate_rows_count_as_independent_contexts"] is False


@pytest.mark.skipif(__import__("importlib").util.find_spec("torch") is None, reason="torch unavailable")
def test_censored_loss_does_not_apply_harmful_repulsion():
    import torch

    theta = torch.tensor(BASELINE_G556, dtype=torch.float32)
    harmful = torch.stack([theta])
    loss, terms = set_valued_actor_loss(
        theta,
        label_state=CENSORED_UNKNOWN,
        positive_thetas=torch.zeros((0, len(THETA_NUMERIC_COLUMNS))),
        harmful_thetas=harmful,
        safe_thetas=torch.zeros((0, len(THETA_NUMERIC_COLUMNS))),
    )
    assert float(terms["harmful_margin_loss"]) == pytest.approx(0.0)
    assert float(loss) == pytest.approx(float(terms["trust_loss"]))
    assert float(harmful_repulsion_loss(theta, harmful)) > 0.0


def test_train_validation_heldout_hashes_disjoint_and_fixed_validation():
    rows = [
        {"evaluation_uid": f"ctx_{idx}", "physical_map_sha256": f"map_{idx}", "map_family": "m", "agent_count": 8, "budget_ms": 500}
        for idx in range(10)
    ]
    manifest = make_grouped_split_manifest(rows, seed=1, validation_fraction=0.2, heldout_fraction=0.2, blind_fraction=0.1)
    assert assert_split_hashes_disjoint(manifest)
    validation = fixed_validation_ids(manifest)
    assert validation
    assert validation_manifest_sha256(validation) == validation_manifest_sha256(list(reversed(validation)))


def test_nested_scaling_subsets_are_nested():
    rows = [
        {"evaluation_uid": f"ctx_{idx}", "physical_map_sha256": f"map_{idx % 4}", "map_family": f"fam_{idx % 2}", "agent_count": idx % 3, "budget_ms": 500}
        for idx in range(20)
    ]
    subsets = nested_stratified_subsets(rows, [4, 8, 12], seed=2)
    assert subsets[4] == subsets[8][:4]
    assert subsets[8] == subsets[12][:8]


def test_run_uid_provenance_filters_stale_progress(tmp_path: Path):
    progress = tmp_path / "progress.jsonl"
    append_progress(progress, "run_a", {"event": "start", "dataset_count": 3})
    append_progress(progress, "run_b", {"event": "start", "dataset_count": 99})
    append_progress(progress, "run_a", {"event": "done"})
    rows = read_progress(progress, "run_a")
    assert len(rows) == 2
    assert summary_matches_progress({"run_uid": "run_a", "dataset_count": 3}, rows)
    with pytest.raises(AssertionError):
        summary_matches_progress({"run_uid": "run_a", "dataset_count": 4}, rows)


def test_true_cycle_merge_adds_rows_to_next_dataset():
    base_rows = [row("ctx", 0, delta=-0.1, gain=True)]
    replay_rows = [row("ctx", 1, safe=False, comparable=True, delta=0.5), row("new", 0, delta=-0.2, gain=True)]
    base = merge_rows_by_context(base_rows, [])
    merged = merge_rows_by_context(base_rows, replay_rows)
    summary = replay_merge_summary(base, merged)
    assert summary["merged_contexts"] == 2
    assert summary["new_unique_contexts"] == 1
    assert summary["expanded_existing_contexts"] == 1

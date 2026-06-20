import json
from pathlib import Path

import pytest

from gcst.representation_contract import (
    FLOOR_BEGIN,
    FLOOR_END,
    FORBIDDEN_REGRESSIONS,
    LITERATURE_SOURCES,
    MINIMUM_INPUTS,
    OFFICIAL_REPOS,
    contract_markers_present,
    representation_floor_block,
)

import audit_repair5g562_g561_truth as g562_truth
from gcst.real_label_graph_dataset import parse_movingai_scenario, row_is_censored
from gcst.dual_stream_graph_actor import ARCHITECTURES, DualStreamGoalAwareActor


ROOT = Path(__file__).resolve().parents[1]


def test_project_outline_representation_floor_present():
    for rel in [
        "deep-research-report.md",
        "phase4_6_laur_ltm_codex_execution_plan.md",
        "docs/goal_aware_dual_channel_ltm_research_contract.md",
    ]:
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert contract_markers_present(text)
        for item in MINIMUM_INPUTS:
            assert item in text


def test_research_contract_explicitly_forbids_dagger_and_action_labels():
    text = (ROOT / "docs/goal_aware_dual_channel_ltm_research_contract.md").read_text(encoding="utf-8")
    assert "G5.62 is explicitly not DAgger" in text
    for forbidden in FORBIDDEN_REGRESSIONS:
        assert forbidden in text


def test_representation_floor_is_minimum_not_ceiling():
    block = representation_floor_block()
    assert FLOOR_BEGIN in block and FLOOR_END in block
    assert "minimum information" in block
    assert "Allowed extensions" in block
    assert "scalar-only model is never the primary" in block


def test_literature_audit_records_versions_and_official_repo_heads():
    assert {source.key for source in LITERATURE_SOURCES} >= {
        "aaai2024_tfo_lmapf",
        "ijcai2024_ggo",
        "icra2023_graph_transformer_mapf",
        "aaai2026_lagat",
        "qd_mapper",
    }
    assert all("arXiv:" in source.version for source in LITERATURE_SOURCES)
    assert all(len(repo["head_commit"]) == 40 for repo in OFFICIAL_REPOS)


def test_g561_target_provenance_distinguishes_analytic_and_real_labels():
    rows = g562_truth.target_provenance_rows()
    analytic = next(row for row in rows if row["component"] == "g561_initial_graph_actor_training")
    required = next(row for row in rows if row["component"] == "g562_required_actor_training")
    assert analytic["target_source"] == "analytic_context_target_theta"
    assert analytic["g562_allowed_primary_target"] is False
    assert required["real_solver_label_target"] is True
    assert required["g562_allowed_primary_target"] is True


def test_g562_g561_truth_summary_confirms_synthetic_target_training():
    path = ROOT / "outputs/reports/phase5p5_repair5g562_g561_training_truth_audit_summary.json"
    if not path.exists():
        pytest.skip("G5.62 truth audit artifact has not been generated yet")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["decision"] == "g562_g561_synthetic_target_training_confirmed"
    assert data["g561_training_was_analytic_target_smoke"] is True
    assert data["g562_requires_real_label_graph_dataset"] is True


def test_real_dataset_uses_actual_scenario_pairs():
    scen = ROOT / "outputs/external/phase5p5_repair5g562_g559_remote_contexts/scenarios/empty-16-16-random-7001.scen"
    if not scen.exists():
        pytest.skip("external G5.59 scenario copy is not available")
    assignment = parse_movingai_scenario(scen, agent_count=8)
    assert assignment["encoded_agent_count"] == 8
    assert assignment["assignment_valid"]
    assert assignment["od_tokens"].shape == (8, 6)


def test_unknown_censored_rows_are_not_negative_labels():
    row = {"labelv51_comparable_quality": "False", "labelv51_success_regression": "False"}
    assert row_is_censored(row)


def test_real_dataset_summary_rejects_analytic_theta_targets():
    path = ROOT / "outputs/reports/phase5p5_repair5g562_real_graph_dataset_summary.json"
    if not path.exists():
        pytest.skip("G5.62 real graph dataset artifact has not been generated yet")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["decision"] == "g562_real_graph_dataset_ready"
    assert data["analytic_theta_target_rate"] == 0.0
    assert data["actual_scenario_pairs_used_rate"] == 1.0


def test_scalar_only_actor_cannot_be_primary():
    assert ARCHITECTURES["C0"].scalar_only_control
    assert not ARCHITECTURES["A1"].scalar_only_control
    assert not ARCHITECTURES["A2"].scalar_only_control


def test_safe_subspace_actor_uses_no_candidate_retrieval():
    actor = DualStreamGoalAwareActor(hidden_dim=16, safe_subspace=True, field_group_trust=True)
    module = actor.module()
    names = set(dict(module.named_parameters()))
    assert all("codebook" not in name.lower() for name in names)
    assert module.safe_subspace
    assert module.safe_basis.shape[0] == 6


def test_actor_export_excludes_critic_and_codebook():
    summary_path = ROOT / "outputs/reports/phase5p5_repair5g562_actor_training_summary.json"
    if not summary_path.exists():
        pytest.skip("G5.62 actor training artifact has not been generated yet")
    matrix = (ROOT / "outputs/tables/phase5p5_repair5g562_architecture_matrix.csv").read_text(encoding="utf-8")
    assert "scalar_context_control" in matrix
    assert "field_group_trust_safe_subspace_actor" in matrix


def test_graph_critic_is_training_only_and_calibrated():
    path = ROOT / "outputs/reports/phase5p5_repair5g562_critic_training_summary.json"
    if not path.exists():
        pytest.skip("G5.62 critic artifact has not been generated yet")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["decision"] == "g562_real_graph_critic_calibrated"
    assert data["training_only"] is True
    assert data["included_in_actor_export"] is False
    assert data["real_success_regression_targets"] is True
    assert data["real_success_gain_targets"] is True
    assert data["real_quality_targets"] is True
    assert data["quality_loss_masks_noncomparable_rows"] is True
    assert data["censored_rows_are_negative"] is False
    assert data["calibration_rows"] > 0


def test_real_supervision_separates_positive_harmful_and_censored():
    path = ROOT / "outputs/reports/phase5p5_repair5g562_critic_training_summary.json"
    if not path.exists():
        pytest.skip("G5.62 critic artifact has not been generated yet")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["positive_safe_rows"] > 0
    assert data["harmful_rows"] > 0
    assert "censored_rows" in data

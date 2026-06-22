from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5g567_strict_pipeline as g567  # noqa: E402
import repair5g549_common as g549  # noqa: E402


def _context(*, agents: int, base_sec: float, budget_ms: int = 30000, hard_timeout_sec: float | None = None) -> g567.G567Context:
    return g567.G567Context(
        dataset_row_id=f"ctx-{agents}",
        evaluation_uid=f"eval-{agents}",
        instance_uid=f"inst-{agents}",
        split="VALIDATION",
        map="unit-map",
        map_family="unit",
        agents=agents,
        seed=567,
        budget_ms=budget_ms,
        base_time_limit_sec=base_sec,
        ltm_max_iterations=12,
        horizon_id=f"budget{budget_ms}_ltm12",
        scenario_path=Path("unused.scen"),
        replay_scenario_path=Path("unused.scen"),
        scenario_sha256="scenario-sha",
        physical_map_sha256="map-sha",
        assignment_sha256="assignment-sha",
        graph_with_traffic=None,  # type: ignore[arg-type]
        assignment={},
        feature_row={},
        budget_role="uniform_30s_all_agent_tiers_primary_exact",
        process_hard_timeout_sec=(
            g567.process_hard_timeout_for_internal_budget(base_sec)
            if hard_timeout_sec is None
            else hard_timeout_sec
        ),
    )


def test_all_agent_primary_budget_contract_is_30s_with_60s_hard_timeout() -> None:
    for tier in [32, 64, 128, 1000, 2000, 2500, 3000]:
        budget_ms, base_sec, ltm_iters, role = g567.budget_profile_for_agent_tier(tier, 0)
        assert budget_ms == 30000
        assert base_sec == 30.0
        assert ltm_iters == 12
        assert role == "uniform_30s_all_agent_tiers_primary_exact"
        assert g567.process_hard_timeout_for_internal_budget(base_sec) == 60.0


def test_nonprimary_purpose_does_not_override_uniform_30s_contract() -> None:
    expected = (30000, 30.0, 12, "uniform_30s_all_agent_tiers_primary_exact")
    for tier in [32, 3000]:
        assert g567.budget_profile_for_agent_tier(tier, 0, "short_budget_stress_diagnostic") == expected
        assert g567.budget_profile_for_agent_tier(tier, 0, "symmetric_recovery_curve_45s") == expected
        assert g567.budget_profile_for_agent_tier(tier, 0, "symmetric_recovery_curve_60s") == expected


def test_plan_rows_keep_same_uniform_30s_budget_for_all_methods() -> None:
    ctx = _context(agents=3000, base_sec=30.0)
    theta = {col: float(g567.BASELINE_G556[idx]) for idx, col in enumerate(g567.THETA_NUMERIC_COLUMNS)}
    theta.update(g567.mode_columns("flow_shield"))
    plan, _registry = g567.build_plan_and_registry(
        [ctx],
        [{"context_id": ctx.dataset_row_id, "variant_id": "A5", "seed": 567, "method": "unit_a5", "model_path": "unit.pt", **theta}],
        "unit_large_budget",
    )
    assert {row["solver_internal_time_limit_sec"] for row in plan} == {30.0}
    assert {row["process_hard_timeout_sec"] for row in plan} == {60.0}
    assert {row["budget_role"] for row in plan} == {"uniform_30s_all_agent_tiers_primary_exact"}


def test_plan_generation_fails_closed_without_explicit_hard_timeout() -> None:
    ctx = _context(agents=3000, base_sec=30.0, hard_timeout_sec=0.0)
    with pytest.raises(ValueError, match="missing explicit process hard timeout"):
        g567.build_plan_and_registry([ctx], [], "unit_missing_timeout")


def test_solver_budget_audit_rejects_mixed_context_budgets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(g567, "SOLVER_BUDGET_AUDIT", tmp_path / "budget_audit.csv")
    monkeypatch.setattr(g567, "SOLVER_BUDGET_AUDIT_SUMMARY", tmp_path / "budget_audit.json")
    ctx = _context(agents=3000, base_sec=30.0)
    rows, _registry = g567.build_plan_and_registry([ctx], [], "unit_budget_audit")
    rows[0]["process_hard_timeout_sec"] = 61.0
    summary = g567.audit_plan_explicit_budgets(rows, "unit_budget_audit")
    assert summary["decision"] == "g567_solver_budget_audit_failed"
    assert any("context_methods_do_not_share_same_budget" in item for item in summary["failures"])


def test_solver_budget_audit_rejects_any_non_30s_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(g567, "SOLVER_BUDGET_AUDIT", tmp_path / "budget_audit.csv")
    monkeypatch.setattr(g567, "SOLVER_BUDGET_AUDIT_SUMMARY", tmp_path / "budget_audit.json")
    ctx = _context(agents=64, base_sec=20.0, budget_ms=20000)
    rows, _registry = g567.build_plan_and_registry([ctx], [], "unit_budget_audit")
    summary = g567.audit_plan_explicit_budgets(rows, "unit_budget_audit")
    assert summary["decision"] == "g567_solver_budget_audit_failed"
    assert summary["uniform_30s_rows_have_60s_hard_timeout"] is False
    assert any("non_uniform_30s_budget_contract" in item for item in summary["failures"])


def test_g567_row_process_isolation_splits_candidate_group(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = _context(agents=64, base_sec=30.0)
    theta = {col: float(g567.BASELINE_G556[idx]) for idx, col in enumerate(g567.THETA_NUMERIC_COLUMNS)}
    theta.update(g567.mode_columns("flow_shield"))
    plan, _registry = g567.build_plan_and_registry(
        [ctx],
        [{"context_id": ctx.dataset_row_id, "variant_id": "A5", "seed": 567, "method": "unit_a5", "model_path": "unit.pt", **theta}],
        "unit_row_isolation",
    )
    monkeypatch.delenv("G567_REPLAY_ROW_PROCESS_ISOLATION", raising=False)
    grouped = g549.probe_execution_groups(plan)
    assert len(grouped) == 1
    assert len(grouped[0][1]) == 4

    monkeypatch.setenv("G567_REPLAY_ROW_PROCESS_ISOLATION", "1")
    isolated = g549.probe_execution_groups(plan)
    assert len(isolated) == 4
    assert all(len(group_rows) == 1 for _key, group_rows in isolated)
    assert {group_rows[0]["candidate_id"] for _key, group_rows in isolated} == {
        g567.ADDITIVE_SOLVER_ALIAS,
        g567.STATIC_FLOW_SOLVER_ALIAS,
        g567.G556_SOLVER_ALIAS,
        next(row["candidate_id"] for row in plan if str(row["role"]).startswith("generated_theta::")),
    }


def test_primary_30s_response_generation_uses_selected_candidate_not_full_lattice() -> None:
    ctx = _context(agents=3000, base_sec=30.0)
    raw = {
        "context_id": ctx.dataset_row_id,
        "variant_id": "A5",
        "model_path": "unit.pt",
        **{col: float(g567.BASELINE_G556[idx]) for idx, col in enumerate(g567.THETA_NUMERIC_COLUMNS)},
    }
    rows = g567.generate_response_thetas([ctx], [raw], phase="field_group_response", target_rows=1000)
    assert len(rows) == 1
    assert rows[0]["variant_id"] == "SELECTED_ACTOR_PRIMARY_30S_EXACT"
    assert rows[0]["multi_fidelity_stage"] == "selected_30s_exact_candidate"
    assert rows[0]["primary_30s_exploratory_full_lattice_skipped"] is True
    assert rows[0]["large_agent_30s_exploratory_full_lattice_skipped"] is True


def test_response_generation_is_coverage_first_across_contexts() -> None:
    contexts = [
        _context(agents=32, base_sec=30.0, budget_ms=30000),
        _context(agents=64, base_sec=30.0, budget_ms=30000),
        _context(agents=128, base_sec=30.0, budget_ms=30000),
    ]
    raw_rows = [
        {
            "context_id": ctx.dataset_row_id,
            "variant_id": "A5",
            "model_path": "unit.pt",
            **{col: float(g567.BASELINE_G556[idx]) for idx, col in enumerate(g567.THETA_NUMERIC_COLUMNS)},
        }
        for ctx in contexts
    ]
    rows = g567.generate_response_thetas(contexts, raw_rows, phase="field_group_response", target_rows=len(contexts))
    assert {row["context_id"] for row in rows} == {ctx.dataset_row_id for ctx in contexts}
    assert all(row["coverage_first_candidate"] is True for row in rows)
    assert {row["multi_fidelity_stage"] for row in rows} == {"selected_30s_exact_candidate"}
    assert {row["primary_30s_exploratory_full_lattice_skipped"] for row in rows} == {True}


def test_response_generation_fails_closed_when_target_rows_cannot_cover_contexts() -> None:
    contexts = [
        _context(agents=32, base_sec=1.0, budget_ms=1000),
        _context(agents=64, base_sec=1.0, budget_ms=1000),
    ]
    raw_rows = [
        {
            "context_id": ctx.dataset_row_id,
            "variant_id": "A5",
            "model_path": "unit.pt",
            **{col: float(g567.BASELINE_G556[idx]) for idx, col in enumerate(g567.THETA_NUMERIC_COLUMNS)},
        }
        for ctx in contexts
    ]
    with pytest.raises(ValueError, match="coverage-first"):
        g567.generate_response_thetas(contexts, raw_rows, phase="field_group_response", target_rows=1)


def test_split_roles_uses_label_train_not_train() -> None:
    rows = [
        {"physical_map_sha256": f"hash-{idx}", "map_family": f"family-{idx % 4}"}
        for idx in range(20)
    ]
    roles = g567.split_roles_by_context_target(rows)
    assert "TRAIN" not in set(roles.values())
    assert "LABEL_TRAIN" in set(roles.values())


def test_token_budget_batches_bound_examples_and_tokens() -> None:
    examples = []
    for idx, tokens in enumerate([5, 7, 20, 4]):
        graph = type("Graph", (), {"cells": list(range(tokens - 1))})()
        examples.append(
            g567.ActorTrainExample(
                example_id=f"ex-{idx}",
                evaluation_uid=f"uid-{idx}",
                split="LABEL_TRAIN",
                map_family="unit",
                graph=graph,  # type: ignore[arg-type]
                assignment={"starts": [(0, 0)]},
                feature_row={},
                target=g567.BASELINE_G556.copy(),
                weight=1.0,
                positive_count=1,
                safe_count=1,
            )
        )
    batches = g567.token_budget_batches(examples, max_examples=2, max_tokens=12)
    assert [len(batch) for batch in batches] == [2, 1, 1]
    assert all(sum(g567.actor_example_token_count(ex) for ex in batch) <= 20 for batch in batches)


def test_primary_actor_selection_prioritizes_additive_static_before_g556() -> None:
    selected = g567.select_primary_actor_checkpoint(
        {
            "per_variant_transfer": {
                "unsafe_good_g556": {
                    "variant_id": "A5",
                    "model_path": "unsafe.pt",
                    "raw_success_regressions_vs_additive": 1,
                    "raw_success_regressions_vs_static_flow": 0,
                    "supported_worse_outside_margin_vs_additive": 0,
                    "supported_worse_outside_margin_vs_static_flow": 0,
                    "median_delta_vs_additive": -1.0,
                    "median_delta_vs_static_flow": -1.0,
                    "raw_success_regressions_vs_g556": 0,
                    "supported_worse_outside_margin_vs_g556": 0,
                    "median_delta_vs_g556": -10.0,
                },
                "safe_weaker_g556": {
                    "variant_id": "A6",
                    "model_path": "safe.pt",
                    "raw_success_regressions_vs_additive": 0,
                    "raw_success_regressions_vs_static_flow": 0,
                    "supported_worse_outside_margin_vs_additive": 0,
                    "supported_worse_outside_margin_vs_static_flow": 0,
                    "median_delta_vs_additive": 0.0,
                    "median_delta_vs_static_flow": 0.0,
                    "raw_success_regressions_vs_g556": 1,
                    "supported_worse_outside_margin_vs_g556": 1,
                    "median_delta_vs_g556": 10.0,
                },
            }
        }
    )
    assert selected["decision"] == "g567_one_primary_actor_selected"
    assert selected["primary_model_path"] == "safe.pt"
    assert selected["g556_used_only_as_secondary_tiebreaker"] is True

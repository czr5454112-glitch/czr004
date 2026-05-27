from __future__ import annotations

import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from czr004_metrics.core import lower_bound_from_distances, sum_of_loss, sum_of_loss_ratio
from czr004_metrics.incumbent import IncumbentEvent, anytime_auc, parse_incumbent_events
from czr004_metrics.schema import normalize_run_row, validate_run_row
from czr004_metrics.summary import phase1a_gate, summarize_by_group, summarize_paired_methods, summarize_planning_execution


def row(method: str, ratio: float, *, map_name: str = "empty-32-32", agents: int = 100, seed: int = 1) -> dict:
    lower_bound = 100
    return {
        "method": method,
        "map": map_name,
        "map_path": "map",
        "scen": f"seed-{seed}",
        "scen_path": "scen",
        "agents": agents,
        "seed": seed,
        "time_limit_sec": 30,
        "objective": "sum_of_loss",
        "valid_instance": True,
        "success": True,
        "feasible": True,
        "sum_of_loss": int(ratio * lower_bound),
        "lower_bound": lower_bound,
        "sum_of_loss_ratio": ratio,
        "makespan": 10,
        "runtime_ms": 1000,
        "time_to_first_solution_ms": None,
        "loop_cnt": 7,
        "ltm_iterations": 0,
        "committed_events": 0,
        "blocked_events": 0,
        "nonzero_ltm_edges": 0,
        "git_commit": "abc",
        "external_lacam2_commit": "def",
        "branch": "test",
        "dirty": "clean",
        "binary_path": "bin",
        "config_path": "cfg",
        "platform": "pytest",
    }


def test_core_sol_ratio_definitions() -> None:
    paths = [
        ["a", "b", "goal", "goal"],
        ["x", "goal", "goal", "goal"],
        ["goal"],
    ]
    assert sum_of_loss(paths) == 3
    assert lower_bound_from_distances([2, 1, 0]) == 3
    assert sum_of_loss_ratio(6, 3) == 2
    assert sum_of_loss_ratio(6, 0) is None


def test_schema_normalizes_phase1a_rows() -> None:
    normalized = normalize_run_row(row("lacam_star", 1.2))
    assert normalized["returned_solutions_count"] == 1
    assert normalized["high_level_expansions"] == 7
    assert normalized["low_level_pibt_calls"] is None
    assert normalized["laur_enabled"] is False
    assert normalized["laur_inference_count"] == 0
    assert normalized["laur_selected_rules"] == {}
    assert validate_run_row(normalized) == []


def test_schema_accepts_phase5_laur_runtime_fields() -> None:
    run = row("lacam_star_lau_ltm", 1.2)
    run.update(
        {
            "laur_enabled": True,
            "laur_force_additive": True,
            "laur_update_mode": "force_additive",
            "laur_model_path": "configs/phase5/laur_additive_only",
            "laur_inference_count": 2,
            "laur_inference_total_ms": 0.25,
            "laur_update_runtime_ms": 0.25,
            "laur_additive_fallback_count": 1,
            "laur_safety_disabled_count": 0,
            "laur_update_period_restarts": 1,
            "laur_post_first_solution_only": True,
            "laur_selected_rules": {"additive_ltm": 2},
        }
    )

    normalized = normalize_run_row(run)

    assert normalized["laur_force_additive"] is True
    assert validate_run_row(normalized) == []


def test_anytime_auc_uses_best_so_far_curve() -> None:
    events = [
        IncumbentEvent(time_ms=100, sum_of_loss=150, lower_bound=100),
        IncumbentEvent(time_ms=500, sum_of_loss=120, lower_bound=100),
    ]
    assert math.isclose(anytime_auc(events, 1000), 1.35)


def test_incumbent_parser_accepts_nested_and_row_events(tmp_path: Path) -> None:
    path = tmp_path / "incumbents.jsonl"
    path.write_text(
        "\n".join(
            [
                '{"incumbents":[{"time_ms":10,"sum_of_loss":150,"lower_bound":100}]}',
                '{"success":true,"runtime_ms":20,"sum_of_loss":120,"lower_bound":100}',
            ]
        ),
        encoding="utf-8",
    )
    events = parse_incumbent_events(path)
    assert [event.time_ms for event in events] == [10, 20]
    assert [event.ratio for event in events] == [1.5, 1.2]


def test_group_and_paired_statistics() -> None:
    rows = [
        row("lacam_star", 1.4, seed=1),
        row("lacam_star_ltm", 1.1, seed=1),
        row("lacam_star", 1.6, seed=2),
        row("lacam_star_ltm", 1.2, seed=2),
    ]
    grouped = summarize_by_group(rows)
    assert len(grouped) == 2
    paired = summarize_paired_methods(rows, "lacam_star", "lacam_star_ltm")
    assert paired["paired_successes"] == 2
    assert paired["contender_better"] == 2
    assert paired["relative_ratio_improvement"] > 0


def test_phase1a_gate_and_planning_execution_summary() -> None:
    rows = []
    for map_index in range(6):
        map_name = f"map-{map_index}"
        for agents in (100, 200):
            rows.append(row("lacam_star", 1.5, map_name=map_name, agents=agents, seed=1))
            rows.append(row("lacam_star_ltm", 1.2, map_name=map_name, agents=agents, seed=1))
    gate = phase1a_gate(rows)
    assert gate["pass_a"] is True

    pe_row = row("lacam_star_ltm", 1.2)
    pe_row["planning_execution_step_sec"] = 0.5
    pe_row["planning_execution_window"] = 10
    pe_summary = summarize_planning_execution([pe_row])
    assert pe_summary[0]["planning_execution_step_sec"] == 0.5
    assert pe_summary[0]["planning_execution_window"] == 10

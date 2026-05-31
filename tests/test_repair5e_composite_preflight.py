from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from eval.repair5d_composite_spec import (  # noqa: E402
    SPEC_SCHEMA_VERSION,
    build_best_composite_spec,
    load_composite_spec,
    write_json,
)
from run_phase5p5_laur_diagnostic_preflight_exec import (  # noqa: E402
    add_ltm_group_deltas,
    synthesize_oracle_static_proxy_rows,
)
from distill_repair5d_composite_to_runtime import runtime_feature_vector  # noqa: E402


def _best_grid_row(tmp_path: Path) -> dict:
    ranking = tmp_path / "phase4f_repair5_expand5000_nextwave_normal_attn_linear_head_rank_safe_eval_seed61.csv"
    safety = tmp_path / "phase4f_repair5_expand5000_hightoken_ht_mlp_target_global_eval_seed61.csv"
    anti = tmp_path / "phase4f_repair5_expand5000_postnext_hightoken_attn_mlp_head_rank_recall_perrule_eval_seed61.csv"
    return {
        "grid_mode": "rank_model_top5_safety_model_per_rule_utility_rerank",
        "composite_mode": "top3_per_rule_safety_utility",
        "top_k": 5,
        "ranking_csv": str(ranking),
        "safety_csv": str(safety),
        "anti_csv": str(anti),
        "sample_count": 762,
        "rule_top1": 0.4989648033126294,
        "rule_top3": 0.8716356107660456,
        "harmful_recall": 0.8010680907877169,
        "harmful_precision": 0.30045067601402103,
        "high_margin_capture": 0.41935483870967744,
        "selected_vs_additive_delta": 0.008891221060077253,
        "selected_harmful_rate": 0.005249343832020997,
        "global_additive_or_defer_rate": 0.29133858267716534,
    }


def test_repair5d_best_composite_spec_freezes_expected_row(tmp_path: Path) -> None:
    calibration = tmp_path / "phase4f_repair5_per_rule_safety_calibration.json"
    calibration.write_text("{}", encoding="utf-8")
    summary_path = tmp_path / "grid.json"
    summary = {"summary_rows": [_best_grid_row(tmp_path)]}
    spec = build_best_composite_spec(
        grid_summary=summary,
        grid_summary_path=summary_path,
        safety_calibration=calibration,
        root=ROOT,
    )

    assert spec["schema_version"] == SPEC_SCHEMA_VERSION
    assert spec["phase5p5_allowed"] is False
    assert spec["phase6_allowed"] is False
    assert spec["mode"] == "rank_model_top5_safety_model_per_rule_utility_rerank"
    assert spec["offline_validation"]["sample_count"] == 762


def test_repair5d_spec_loader_rejects_unlock(tmp_path: Path) -> None:
    spec = build_best_composite_spec(
        grid_summary={"summary_rows": [_best_grid_row(tmp_path)]},
        grid_summary_path=tmp_path / "grid.json",
        safety_calibration=tmp_path / "phase4f_repair5_per_rule_safety_calibration.json",
        root=ROOT,
    )
    spec["phase6_allowed"] = True
    path = tmp_path / "bad_spec.json"
    write_json(path, spec)

    try:
        load_composite_spec(path)
    except ValueError as exc:
        assert "phase6_allowed" in str(exc) or "unlock" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("bad spec was accepted")


def test_repair5e_runtime_feature_vector_maps_attention_globals() -> None:
    row = {
        "global_feature_names": [
            "agents",
            "density",
            "map_width",
            "map_height",
            "obstacle_ratio",
            "iteration",
            "committed_count",
            "blocked_count",
        ],
        "global_features": [50.0, 0.25, 16.0, 16.0, 0.0, 2.0, 100.0, 25.0],
    }

    vector = runtime_feature_vector(row)

    assert len(vector) == 36
    assert vector[0] == 50.0
    assert vector[1] == 200.0
    assert vector[2] == 0.25


def test_repair5e_preflight_synthesizes_static_oracle_proxy_and_deltas() -> None:
    base = {
        "map": "empty-8-8",
        "scen": "empty-8-8-random-1.scen",
        "agents": 16,
        "seed": 1,
        "success": True,
        "feasible": True,
        "sum_of_loss_ratio": 1.2,
        "expanded_nodes": 10,
        "time_to_first_solution_ms": 5.0,
        "returned_solutions_count": 1,
        "low_level_pibt_calls": 8,
        "laur_selected_rules": {},
    }
    rows = [
        {**base, "method": "lacam_star_ltm"},
        {**base, "method": "oracle_probe_static_block_heavy", "sum_of_loss_ratio": 1.1, "expanded_nodes": 12},
        {**base, "method": "oracle_probe_static_wait_light", "sum_of_loss_ratio": 1.3, "expanded_nodes": 8},
    ]

    oracle = synthesize_oracle_static_proxy_rows(rows)
    summary = add_ltm_group_deltas(
        [
            {
                "map": "empty-8-8",
                "agents": 16,
                "method": "lacam_star_ltm",
                "sum_of_loss_ratio_mean": 1.2,
                "expanded_nodes_mean": 10,
                "time_to_first_solution_ms_mean": 5.0,
            },
            {
                "map": "empty-8-8",
                "agents": 16,
                "method": "oracle_teacher_forced_best_safe_update_static_proxy",
                "sum_of_loss_ratio_mean": 1.1,
                "expanded_nodes_mean": 12,
                "time_to_first_solution_ms_mean": 5.0,
            },
        ]
    )

    assert oracle[0]["method"] == "oracle_teacher_forced_best_safe_update_static_proxy"
    assert oracle[0]["oracle_proxy_source_method"] == "oracle_probe_static_block_heavy"
    assert summary[1]["ratio_delta_vs_ltm"] == -0.09999999999999987

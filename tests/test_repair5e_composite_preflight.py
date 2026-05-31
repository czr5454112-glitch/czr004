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
    build_methods,
    synthesize_oracle_static_proxy_rows,
)
from distill_repair5d_composite_to_runtime import runtime_feature_vector  # noqa: E402
from analyze_repair5e2_runtime_feature_ood import (  # noqa: E402
    REQUIRED_UPDATE_LOG_FIELDS,
    analyze_rows,
)
from audit_repair5e3_oracle_support_leakage import audit_leakage  # noqa: E402


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


def test_repair5e_caseb_ood_guard_candidate_is_wired(tmp_path: Path) -> None:
    methods, skipped = build_methods(
        root=ROOT,
        additive_model=tmp_path / "additive",
        repair3_runtime=None,
        repair5d_runtime=None,
        repair5e_ood_guard_runtime=tmp_path / "guard_runtime",
        include_static_proxies=False,
        include_oracle_static_probe=False,
        include_ood_guard_candidate=True,
        ood_guard_z_threshold=4.5,
    )

    by_alias = {method.alias: method for method in methods}

    guarded = by_alias["repair5e_caseb_ood_guard_distilled"]
    assert "--laur-ood-z-threshold" in guarded.extra_args
    assert "4.5" in guarded.extra_args
    assert "--laur-safety-threshold" in guarded.extra_args

    parity = by_alias["repair5e_caseb_ood_guard_force_additive_parity"]
    assert "--laur-force-additive" in parity.extra_args
    assert "--laur-ood-z-threshold" in parity.extra_args

    assert any(row["method"] == "repair3_safe_runtime" for row in skipped)
    assert any(row["method"] == "repair5d_composite_diagnostic_distilled" for row in skipped)


def test_repair5e2_guarded_selector_candidate_is_wired(tmp_path: Path) -> None:
    methods, skipped = build_methods(
        root=ROOT,
        additive_model=tmp_path / "additive",
        repair3_runtime=None,
        repair5d_runtime=None,
        repair5e_ood_guard_runtime=None,
        repair5e2_runtime=tmp_path / "repair5e2_runtime",
        include_static_proxies=False,
        include_oracle_static_probe=False,
        include_repair5e2_candidate=True,
        repair5e2_ood_guard_z_threshold=5.0,
    )

    by_alias = {method.alias: method for method in methods}
    guarded = by_alias["repair5e2_guarded_oracle_aligned_selector"]
    assert "--laur-model-path" in guarded.extra_args
    assert "--laur-ood-z-threshold" in guarded.extra_args
    assert "--laur-safety-threshold" in guarded.extra_args

    parity = by_alias["repair5e2_guarded_oracle_aligned_selector_force_additive_parity"]
    assert "--laur-force-additive" in parity.extra_args
    assert not any(row["method"] == "repair5e2_guarded_oracle_aligned_selector" for row in skipped)


def test_repair5e3_split_selector_and_ablation_candidates_are_wired(tmp_path: Path) -> None:
    methods, skipped = build_methods(
        root=ROOT,
        additive_model=tmp_path / "additive",
        repair3_runtime=None,
        repair5d_runtime=None,
        repair5e_ood_guard_runtime=None,
        repair5e2_runtime=tmp_path / "repair5e2_runtime",
        repair5e3_runtime=tmp_path / "repair5e3_runtime",
        repair5e3_e2_shuffled_runtime=tmp_path / "repair5e3_shuffled",
        include_static_proxies=False,
        include_oracle_static_probe=False,
        include_repair5e3_candidate=True,
        include_repair5e3_e2_ablation_candidates=True,
        repair5e3_ood_guard_z_threshold=4.0,
    )

    by_alias = {method.alias: method for method in methods}
    guarded = by_alias["repair5e3_split_guarded_selector"]
    assert "--laur-model-path" in guarded.extra_args
    assert "--laur-ood-z-threshold" in guarded.extra_args
    assert "4.0" in guarded.extra_args

    parity = by_alias["repair5e3_split_guarded_selector_force_additive_parity"]
    assert "--laur-force-additive" in parity.extra_args

    disabled = by_alias["repair5e3_e2_recovery_disabled_parity"]
    assert "--laur-force-additive" in disabled.extra_args

    shuffled = by_alias["repair5e3_e2_recovery_shuffled_support_diagnostic"]
    assert "--laur-model-path" in shuffled.extra_args
    assert not any(row["method"] == "repair5e3_split_guarded_selector" for row in skipped)


def test_repair5e2_update_log_runtime_feature_fields_are_analyzable(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    (runtime_dir / "features.txt").write_text("agents\nentropy_edge_usage\n", encoding="utf-8")
    (runtime_dir / "mean.csv").write_text("50,2.75\n", encoding="utf-8")
    (runtime_dir / "std.csv").write_text("10,0.05\n", encoding="utf-8")

    row = {
        "method": "repair5e2_guarded_oracle_aligned_selector",
        "map": "random-32-32-20",
        "agents": 50,
        "seed": 1,
        "scen": "random-32-32-20-random-1.scen",
        "iteration": 1,
        "predicted_rule": "commit_heavy",
        "applied_rule": "additive_ltm",
        "runtime_feature_names": ["agents", "entropy_edge_usage"],
        "runtime_feature_values": [50.0, 0.0],
        "feature_max_abs_z": 55.0,
        "feature_mean_abs_z": 27.5,
        "feature_outside_3sigma_count": 1,
        "feature_outside_5sigma_count": 1,
        "ood_guard_triggered": True,
        "ood_z_threshold": 5.0,
        "selected_rule_before_guard": "commit_heavy",
        "selected_rule_after_guard": "additive_ltm",
        "selected_rule_source": "ood_guard",
    }
    assert all(field in row for field in REQUIRED_UPDATE_LOG_FIELDS)

    summary, details = analyze_rows(
        [row],
        runtime_dir=runtime_dir,
        methods={"repair5e2_guarded_oracle_aligned_selector"},
    )

    assert summary["missing_required_field_counts"] == {}
    assert details[0]["top_feature_by_abs_z"] == "entropy_edge_usage"
    assert summary["rule_before_after_source_counts"]["commit_heavy->additive_ltm:ood_guard"] == 1


def test_repair5e3_auditor_catches_overlapping_support_and_eval_paths(tmp_path: Path) -> None:
    eval_jsonl = tmp_path / "eval.jsonl"
    eval_jsonl.write_text(
        json.dumps({"method": "lacam_star_ltm", "map": "random-32-32-20", "agents": 50, "seed": 4}) + "\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "train_support_paths": [str(eval_jsonl)],
                "train_instance_ids": [4],
                "maps": ["random-32-32-20"],
                "agent_counts": [50],
                "recovery_rules": [
                    {
                        "map": "random-32-32-20",
                        "agents": 50,
                        "rule_id": "block_light",
                        "support_rows": 1,
                        "support_better": 1,
                        "support_equal": 0,
                        "support_worse": 0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    support_csv = tmp_path / "repair5e2_recovery_rules.csv"
    support_csv.write_text(
        "map_width,map_height,obstacle_ratio_min,obstacle_ratio_max,agents,rule_id,support_mean_delta,support_rows,source\n"
        "32,32,0.1,0.2,50,block_light,-0.1,1,test\n",
        encoding="utf-8",
    )

    summary, provenance = audit_leakage(
        root=tmp_path,
        runtime_dir=tmp_path,
        manifest_path=manifest,
        support_csv=support_csv,
        eval_jsonl_paths=[eval_jsonl],
        preflight_summary_paths=[],
    )

    assert summary["leakage_detected"] is True
    assert summary["eval_raw_jsonl_paths_appear_in_train_support_metadata"] is True
    assert summary["support_eval_instance_overlap_count"] == 1
    assert "git_head_sha" in provenance
    assert "runtime_manifest_sha256" in provenance

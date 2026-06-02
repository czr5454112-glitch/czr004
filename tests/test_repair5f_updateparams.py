from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from create_repair5f_updateparam_candidates import build_candidates  # noqa: E402
from run_repair5f_updateparam_probe_table import (  # noqa: E402
    completed_probe_keys,
    dedupe_probe_rows,
    exact_additive_candidate_parity_exact,
    force_additive_parity_exact,
    synthesize_diagnostics,
    write_candidate_runtime,
)
from analyze_repair5f_force_additive_parity import (  # noqa: E402
    build_mismatch_rows,
    dedupe_rows as dedupe_autopsy_rows,
    summarize_update_logs,
)
from run_repair5f_force_additive_parity_reproducer import (  # noqa: E402
    build_reproducer_methods,
)
from run_repair5f_runtime_export_eval import selected_candidate_from_row  # noqa: E402
from run_repair5f3_runtime_parity_reproducer import (  # noqa: E402
    build_reproducer_methods as build_f3_reproducer_methods,
)


def test_repair5f_lattice_is_sparse_bounded_and_contains_old_presets() -> None:
    candidates = build_candidates()
    by_id = {candidate.candidate_id: candidate for candidate in candidates}
    old = {
        candidate.old_equivalent_rule: candidate.candidate_id
        for candidate in candidates
        if candidate.old_equivalent_rule
    }

    assert 25 <= len(candidates) <= 60
    assert len(candidates) < 375
    assert by_id["additive_ltm"].force_additive is True
    assert old == {
        "additive_ltm": "additive_ltm",
        "commit_heavy": "c150_b100_w100_d100",
        "block_heavy": "c100_b150_w100_d100",
        "block_light": "c100_b050_w100_d100",
        "wait_light": "c100_b100_w050_d100",
        "wait_heavy": "c100_b100_w150_d100",
        "decay_095": "c100_b100_w100_d095",
        "decay_090": "c100_b100_w100_d090",
    }
    assert max(candidate.alpha_commit for candidate in candidates) == 1.5
    assert min(candidate.alpha_block for candidate in candidates) == 0.5
    assert {candidate.rho_decay for candidate in candidates} == {0.90, 0.95, 1.0}


def test_repair5f_candidate_runtime_exports_custom_updateparams(tmp_path: Path) -> None:
    candidate = next(
        item for item in build_candidates() if item.candidate_id == "c075_b125_w125_d095"
    )
    runtime_dir = write_candidate_runtime(tmp_path, candidate)

    with (runtime_dir / "rules.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert (runtime_dir / "features.txt").read_text(encoding="utf-8").strip() == "bias"
    assert rows == [
        {
            "rule_id": "c075_b125_w125_d095",
            "alpha_commit": "0.75",
            "alpha_block": "1.25",
            "alpha_wait": "1.25",
            "rho_decay": "0.95",
            "saturation_scale": "1",
            "contraflow_penalty": "0",
            "force_additive": "false",
        }
    ]


def test_repair5f_synthesizes_oracle_random_and_shuffled_diagnostics() -> None:
    rows = [
        {
            "map": "random-32-32-20",
            "agents": 50,
            "seed": 21,
            "scen": "case21.scen",
            "method": "repair5f_candidate_a",
            "success": True,
            "sum_of_loss_ratio": 1.2,
            "expanded_nodes": 10,
            "time_to_first_solution_ms": 5,
        },
        {
            "map": "random-32-32-20",
            "agents": 50,
            "seed": 21,
            "scen": "case21.scen",
            "method": "repair5f_candidate_b",
            "success": True,
            "sum_of_loss_ratio": 1.1,
            "expanded_nodes": 20,
            "time_to_first_solution_ms": 5,
        },
        {
            "map": "random-32-32-20",
            "agents": 50,
            "seed": 22,
            "scen": "case22.scen",
            "method": "repair5f_candidate_a",
            "success": True,
            "sum_of_loss_ratio": 1.0,
            "expanded_nodes": 10,
            "time_to_first_solution_ms": 5,
        },
        {
            "map": "random-32-32-20",
            "agents": 50,
            "seed": 22,
            "scen": "case22.scen",
            "method": "repair5f_candidate_b",
            "success": True,
            "sum_of_loss_ratio": 1.3,
            "expanded_nodes": 20,
            "time_to_first_solution_ms": 5,
        },
    ]

    synthetic = synthesize_diagnostics(rows)
    methods = [row["method"] for row in synthetic]

    assert methods.count("repair5f_candidate_lattice_oracle_static_proxy") == 2
    assert methods.count("repair5f_bounded_updateparam_selector_random_candidate_diagnostic") == 2
    assert methods.count("repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic") == 2
    oracle_candidates = {
        row["seed"]: row["repair5f_synthetic_candidate_id"]
        for row in synthetic
        if row["method"] == "repair5f_candidate_lattice_oracle_static_proxy"
    }
    assert oracle_candidates == {21: "b", 22: "a"}


def test_repair5f_completed_probe_keys_support_resume() -> None:
    rows = [
        {"map": "random-32-32-20", "agents": "50", "seed": "21", "method": "lacam_star_ltm"},
        {"map": "random-32-32-20", "agents": 50, "seed": 21, "method": "repair5f_candidate_a"},
    ]

    assert completed_probe_keys(rows) == {
        ("random-32-32-20", 50, 21, "lacam_star_ltm"),
        ("random-32-32-20", 50, 21, "repair5f_candidate_a"),
    }


def test_repair5f_dedupes_probe_rows_by_case_method() -> None:
    rows = [
        {"map": "m", "agents": 50, "seed": 21, "method": "a", "value": 1},
        {"map": "m", "agents": 50, "seed": 21, "method": "a", "value": 2},
        {"map": "m", "agents": 50, "seed": 21, "method": "b", "value": 3},
    ]

    assert dedupe_probe_rows(rows) == [
        {"map": "m", "agents": 50, "seed": 21, "method": "a", "value": 1},
        {"map": "m", "agents": 50, "seed": 21, "method": "b", "value": 3},
    ]


def test_repair5f_tracks_force_and_exact_additive_parity_separately() -> None:
    common = {
        "map": "m",
        "agents": 50,
        "seed": 21,
        "scen": "case.scen",
        "success": True,
        "lower_bound": 10,
        "makespan": 5,
    }
    rows = [
        {**common, "method": "lacam_star_ltm", "sum_of_loss": 12, "sum_of_loss_ratio": 1.2},
        {**common, "method": "always_additive_defer", "sum_of_loss": 13, "sum_of_loss_ratio": 1.3},
        {**common, "method": "repair5f_candidate_additive_ltm", "sum_of_loss": 12, "sum_of_loss_ratio": 1.2},
    ]

    assert not force_additive_parity_exact(rows)
    assert exact_additive_candidate_parity_exact(rows)


def test_repair5f_autopsy_reports_legacy_force_mismatch_only() -> None:
    common = {
        "map": "warehouse-10-20-10-2-1",
        "agents": 50,
        "seed": 25,
        "scen": "case.scen",
        "success": True,
        "lower_bound": 10,
        "makespan": 5,
    }
    raw_rows = [
        {**common, "method": "lacam_star_ltm", "sum_of_loss": 12, "sum_of_loss_ratio": 1.2},
        {
            **common,
            "method": "always_additive_defer",
            "sum_of_loss": 13,
            "sum_of_loss_ratio": 1.3,
            "laur_force_additive": True,
        },
        {
            **common,
            "method": "always_additive_defer",
            "sum_of_loss": 13,
            "sum_of_loss_ratio": 1.3,
            "laur_force_additive": True,
        },
        {
            **common,
            "method": "repair5f_candidate_additive_ltm",
            "sum_of_loss": 12,
            "sum_of_loss_ratio": 1.2,
            "laur_force_additive": False,
        },
    ]
    update_logs = [
        {
            **common,
            "method": "always_additive_defer",
            "iteration": 1,
            "decision_status": "force_additive",
            "fallback_reason": "force_additive",
            "selected_rule_source": "force_additive",
            "applied_rule": "additive_ltm",
        }
    ]

    deduped, duplicate_status = dedupe_autopsy_rows(raw_rows)
    mismatch_cases, detail_rows = build_mismatch_rows(
        deduped_rows=deduped,
        duplicate_status=duplicate_status,
        update_summaries=summarize_update_logs(update_logs),
    )

    assert mismatch_cases == [
        {
            "map": "warehouse-10-20-10-2-1",
            "agents": 50,
            "seed": 25,
            "force_additive_parity_exact": False,
            "canonical_exact_additive_candidate_parity_exact": True,
        }
    ]
    force_row = next(row for row in detail_rows if row["method"] == "always_additive_defer")
    assert force_row["duplicate_raw_row_count"] == 2
    assert force_row["decision_status_counts"] == '{"force_additive": 1}'


def test_repair5f_reproducer_includes_canonical_controls(tmp_path: Path) -> None:
    methods = build_reproducer_methods(
        runtime_root=tmp_path / "runtime",
        additive_runtime=tmp_path / "additive_only",
    )
    by_alias = {method.alias: method for method in methods}

    assert set(by_alias) == {
        "lacam_star_ltm",
        "always_additive_defer",
        "repair5f_candidate_additive_ltm",
        "laur_disable",
        "laur_force_additive_direct",
    }
    assert "--laur-force-additive" in by_alias["always_additive_defer"].extra_args
    assert "--laur-model-path" in by_alias["always_additive_defer"].extra_args
    assert by_alias["laur_force_additive_direct"].extra_args == ("--laur-force-additive",)


def test_repair5f3_selector_force_parity_labels_additive_candidate() -> None:
    assert selected_candidate_from_row(
        {
            "method": "repair5f_bounded_updateparam_selector_force_additive_parity",
            "laur_selected_rules": {},
        }
    ) == "additive_ltm"
    assert selected_candidate_from_row(
        {
            "method": "laur_force_additive_direct",
            "laur_force_additive": True,
            "laur_selected_rules": {},
        }
    ) == "additive_ltm"


def test_repair5f3_reproducer_includes_runtime_parity_controls() -> None:
    methods = build_f3_reproducer_methods()
    by_alias = {method.alias: method for method in methods}

    assert set(by_alias) == {
        "lacam_star_ltm",
        "always_additive_defer",
        "repair5f_candidate_additive_ltm",
        "repair5f_bounded_updateparam_selector_force_additive_parity",
        "laur_disable",
        "laur_force_additive_direct",
    }
    assert by_alias["always_additive_defer"].method == "always_additive_defer"
    assert by_alias["repair5f_candidate_additive_ltm"].extra_args == ()
    assert by_alias["laur_disable"].method == "laur_disable"
    assert by_alias["laur_force_additive_direct"].method == "laur_force_additive_direct"

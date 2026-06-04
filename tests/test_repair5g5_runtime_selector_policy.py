from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from repair5g5_common import (  # noqa: E402
    G5_DISABLE,
    G5_FORCE,
    G5_RUNTIME,
    summarise_runtime_run,
)


def _row(method: str, ratio: float) -> dict:
    return {
        "map": "unit-map",
        "agents": 50,
        "seed": 126,
        "scen": "unit.scen",
        "method": method,
        "success": True,
        "sum_of_loss_ratio": ratio,
        "repair5g_costs_finite": True,
        "repair5g_cost_bounds_respected": True,
    }


def _summarise(tmp_path: Path, update_feature_names: list[str]) -> dict:
    rows = [
        _row("lacam_star_ltm", 1.0),
        _row(G5_RUNTIME, 0.9),
        _row(G5_FORCE, 1.0),
        _row(G5_DISABLE, 1.0),
    ]
    update_rows = [
        {
            "method": G5_RUNTIME,
            "runtime_feature_names": update_feature_names,
            "runtime_feature_values": [50.0 for _ in update_feature_names],
        }
    ]
    summary, _paired = summarise_runtime_run(
        rows=rows,
        update_rows=update_rows,
        commands=[{"returncode": 0}],
        maps=["unit-map"],
        agent_counts=[50],
        instance_ids=[126],
        reported_methods=["lacam_star_ltm", G5_RUNTIME, G5_FORCE, G5_DISABLE],
        paired_csv=tmp_path / "paired.csv",
        summary_csv=tmp_path / "summary.csv",
        by_map_agent_csv=tmp_path / "by_group.csv",
        oracle_csv=tmp_path / "oracle.csv",
    )
    return summary


def test_runtime_selector_mean_zero_is_not_treated_as_missing(tmp_path: Path) -> None:
    summary = _summarise(tmp_path, ["agents", "ltm_iterations", "cost_bounds_respected"])
    gates = summary["gates"]

    assert gates["runtime_contextual_selector_mean_delta_ratio_vs_ltm"] == -0.09999999999999998
    assert gates["runtime_contextual_selector_mean_delta_ratio_vs_ltm_lt_0"]
    assert gates["force_additive_policy_compliant"]
    assert gates["disable_policy_compliant"]
    assert gates["allowed_feature_policy_passed"]
    assert gates["forbidden_feature_policy_passed"]


def test_runtime_selector_rejects_forbidden_or_unexpected_features(tmp_path: Path) -> None:
    summary = _summarise(tmp_path, ["agents", "seed", "candidate outcome"])
    gates = summary["gates"]

    assert not gates["allowed_feature_policy_passed"]
    assert not gates["forbidden_feature_policy_passed"]
    assert "seed" in gates["unexpected_runtime_features"]
    assert "candidate outcome" in gates["unexpected_runtime_features"]

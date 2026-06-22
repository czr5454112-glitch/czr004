from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_repair5g567_strict_pipeline as g567  # noqa: E402


def _patch_outputs(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(g567, "LABELV54_CONTEXTS", tmp_path / "contexts.csv")
    monkeypatch.setattr(g567, "LABELV54_CANDIDATES", tmp_path / "candidates.csv")
    monkeypatch.setattr(g567, "LABELV54_REPLICATES", tmp_path / "replicates.csv")
    monkeypatch.setattr(g567, "LABELV54_SAFE_SETS", tmp_path / "safe_sets.jsonl")
    monkeypatch.setattr(g567, "LABELV54_SUMMARY", tmp_path / "summary.json")
    monkeypatch.setattr(g567, "REPEATABILITY_SUMMARY", tmp_path / "repeatability.json")


def _row(**updates):
    row = {
        "replay_phase": "repeatability_single_worker",
        "g567_evaluation_uid": "uid-1",
        "g567_dataset_row_id": "ctx-1",
        "theta_id": "theta-1",
        "variant_id": "A5",
        "split": "CALIBRATION",
        "map": "m",
        "map_family": "f",
        "agents": "32",
        "budget_ms": "1000",
        "replicate_group_id": "rg-1",
        "delta_vs_additive": "0.0",
        "delta_vs_static_flow": "0.0",
        "delta_vs_g556": "0.0",
        "success_gain_vs_additive": "False",
        "success_regression_vs_additive": "False",
        "success_gain_vs_static_flow": "False",
        "success_regression_vs_static_flow": "False",
        "success_gain_vs_g556": "False",
        "success_regression_vs_g556": "False",
    }
    row.update(updates)
    return row


def _label_rows(monkeypatch, tmp_path: Path, rows: list[dict[str, str]], margin: float = 0.05):
    _patch_outputs(monkeypatch, tmp_path)
    pair_path = tmp_path / "pairs.csv"
    g567.write_rows(pair_path, rows)
    g567.create_labelv54_from_pairs([pair_path], margin)
    return g567.read_rows(tmp_path / "candidates.csv")


def _replicated(row: dict[str, str], count: int = 5) -> list[dict[str, str]]:
    return [{**row, "replicate_id": str(idx)} for idx in range(count)]


def test_additive_regression_can_never_be_primary_safe(monkeypatch, tmp_path: Path) -> None:
    rows = _label_rows(monkeypatch, tmp_path, _replicated(_row(success_regression_vs_additive="True")))
    assert rows
    assert all(not g567.boolish(row["primary_safe_AB"]) for row in rows)
    assert all(g567.boolish(row["supported_regression_A"]) for row in rows)


def test_static_flow_regression_can_never_be_primary_safe(monkeypatch, tmp_path: Path) -> None:
    rows = _label_rows(monkeypatch, tmp_path, _replicated(_row(success_regression_vs_static_flow="True")))
    assert all(not g567.boolish(row["primary_safe_AB"]) for row in rows)
    assert all(g567.boolish(row["supported_regression_B"]) for row in rows)


def test_g556_only_regression_remains_ab_safe_not_abc_safe(monkeypatch, tmp_path: Path) -> None:
    rows = _label_rows(monkeypatch, tmp_path, _replicated(_row(success_regression_vs_g556="True")))
    assert all(g567.boolish(row["primary_safe_AB"]) for row in rows)
    assert all(not g567.boolish(row["stretch_safe_ABC"]) for row in rows)


def test_better_vs_additive_alone_does_not_create_joint_positive_ab(monkeypatch, tmp_path: Path) -> None:
    rows = _label_rows(monkeypatch, tmp_path, [_row(replay_phase="field_group_response", delta_vs_additive="-0.20")])
    assert g567.boolish(rows[0]["positive_A"])
    assert not g567.boolish(rows[0]["positive_B"])
    assert not g567.boolish(rows[0]["joint_positive_AB"])
    assert not g567.boolish(rows[0]["labelv54_positive"])
    assert g567.boolish(rows[0]["labelv54_primary_training_candidate"])
    assert g567.boolish(rows[0]["pareto_safe_AB"])


def test_quality_harm_vs_static_flow_is_not_hidden_by_additive_gain(monkeypatch, tmp_path: Path) -> None:
    rows = _label_rows(
        monkeypatch,
        tmp_path,
        [_row(replay_phase="field_group_response", delta_vs_additive="-0.20", delta_vs_static_flow="0.20")],
    )
    assert not g567.boolish(rows[0]["quality_safe_B"])
    assert not g567.boolish(rows[0]["joint_positive_AB"])
    assert g567.boolish(rows[0]["labelv54_harmful"])


def test_single_run_boundary_is_uncertain_not_stable_safe(monkeypatch, tmp_path: Path) -> None:
    rows = _label_rows(monkeypatch, tmp_path, [_row(replay_phase="field_group_response", success_gain_vs_additive="True")])
    assert rows[0]["measurement_confidence"] == "single_run_boundary_uncertain"
    assert not g567.boolish(rows[0]["stable_label_supported"])
    assert not g567.boolish(rows[0]["primary_safe_AB"])

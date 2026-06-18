from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import finalize_repair5g557_remote_results as finalize  # noqa: E402


def test_tail_text_keeps_short_text() -> None:
    assert finalize.tail_text("abc", limit=5) == "abc"


def test_tail_text_trims_from_left() -> None:
    assert finalize.tail_text("abcdef", limit=3) == "def"


def test_repo_path_resolves_relative_paths() -> None:
    resolved = finalize.repo_path(Path("outputs/reports/example.json"))

    assert resolved == finalize.ROOT / "outputs/reports/example.json"


def test_finalize_validation_covers_required_stage_scripts() -> None:
    required = {
        "scripts/verify_repair5g557_g556_artifacts.py",
        "scripts/run_repair5g557_theta_label_matrix.py",
        "scripts/train_eval_repair5g557_ttgt_outcome_model.py",
        "scripts/train_eval_repair5g557_gcst_generator.py",
        "scripts/run_repair5g557_stage1_execution.py",
        "scripts/run_repair5g557_stage2_heldout_map.py",
        "scripts/run_repair5g557_blind.py",
        "scripts/write_repair5g557_decision.py",
    }

    assert required.issubset(set(finalize.PY_COMPILE_PATHS))
    assert required.issubset(set(finalize.DIFF_CHECK_PATHS))


def test_parse_g557_summaries_reports_errors(monkeypatch, tmp_path: Path) -> None:
    reports = tmp_path / "outputs/reports"
    reports.mkdir(parents=True)
    good = reports / "phase5p5_repair5g557_decision_summary.json"
    bad = reports / "phase5p5_repair5g557_bad_summary.json"
    good.write_text(json.dumps({"decision": "synthetic"}), encoding="utf-8")
    bad.write_text("{bad", encoding="utf-8")
    monkeypatch.setattr(finalize, "ROOT", tmp_path)

    result = finalize.parse_g557_summaries()

    assert result["passed"] is False
    assert "outputs/reports/phase5p5_repair5g557_decision_summary.json" in result["parsed"]
    assert "outputs/reports/phase5p5_repair5g557_bad_summary.json" in result["errors"]

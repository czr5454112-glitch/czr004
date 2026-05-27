from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.features_laur import FEATURE_NAMES  # noqa: E402


def test_phase5_additive_only_runtime_config_matches_phase4_feature_order() -> None:
    feature_path = ROOT / "configs" / "phase5" / "laur_additive_only" / "features.txt"
    features = [line.strip() for line in feature_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert features == FEATURE_NAMES


def test_phase5_additive_only_runtime_config_is_exact_additive_rule() -> None:
    rules_path = ROOT / "configs" / "phase5" / "laur_additive_only" / "rules.csv"
    rows = list(csv.DictReader(rules_path.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 1
    row = rows[0]
    assert row["rule_id"] == "additive_ltm"
    assert row["force_additive"] == "true"
    assert float(row["alpha_commit"]) == 1.0
    assert float(row["alpha_block"]) == 1.0
    assert float(row["alpha_wait"]) == 1.0
    assert float(row["rho_decay"]) == 1.0
    assert float(row["saturation_scale"]) == 1.0
    assert float(row["contraflow_penalty"]) == 0.0

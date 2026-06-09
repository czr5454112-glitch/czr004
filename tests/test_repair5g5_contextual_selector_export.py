from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from repair5g5_common import DEFAULT_SELECTOR_SPEC, G5_ALLOWED_FEATURES  # noqa: E402


def test_repair5g5_selector_export_is_diagnostic_and_holdout_clean() -> None:
    spec_path = ROOT / DEFAULT_SELECTOR_SPEC
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    assert spec["schema_version"] == "phase5p5_repair5g5_contextual_selector_runtime_spec_v1"
    assert spec["diagnostic_only"] is True
    assert spec["phase5p5_allowed"] is False
    assert spec["phase6_allowed"] is False
    assert spec["aaai_ready"] is False
    assert spec["forbidden_final_ids"] == "166..205 primary learned-runtime holdout"
    assert set(spec["allowed_features"]) == G5_ALLOWED_FEATURES
    assert not set(spec["forbidden_features"]) & G5_ALLOWED_FEATURES


def test_repair5g5_selector_candidate_set_has_bounded_runtime_targets() -> None:
    candidate_path = ROOT / "artifacts/models/laur_ltm/repair5g5_contextual_flow_shield_selector/candidate_set.csv"
    with candidate_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    by_id = {row["candidate_id"]: row for row in rows}
    assert by_id["repair5g2_best_frozen_static_candidate"]["bounded_updateparams"] == "True"
    assert by_id["repair5g2_best_frozen_static_candidate"]["phase5p5_allowed"] == "False"
    assert by_id["repair5g_dual_c_equiv_c100_b100_w100_d090"]["bounded_updateparams"] == "True"
    assert by_id["repair5g_dual_c_equiv_additive"]["phase6_allowed"] == "False"

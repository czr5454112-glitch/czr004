from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from czr004_teacher.features_laur import FEATURE_NAMES  # noqa: E402
from export_phase5_laur_mlp_runtime import export_runtime_dir  # noqa: E402


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


def test_phase5_mlp_json_export_converts_to_runtime_csv(tmp_path: Path) -> None:
    weights = {
        "schema_version": "laur_mlp_v1_weights",
        "input_features": ["agents", "blocked_count"],
        "normalization": {"mean": [1.0, 2.0], "std": [3.0, 4.0]},
        "layers": [
            {"type": "linear", "weight": [[0.1, 0.2]], "bias": [0.3]},
            {"type": "relu"},
            {"type": "linear_rule_head", "weight": [[0.4], [0.5]], "bias": [0.6, 0.7]},
            {"type": "linear_safety_head", "weight": [[0.8]], "bias": [0.9]},
            {"type": "linear_delta_head", "weight": [[1.0]], "bias": [1.1]},
        ],
        "rules": {"0": "additive_ltm", "1": "block_heavy"},
        "rule_params": {
            "additive_ltm": {
                "alpha_commit": 1.0,
                "alpha_block": 1.0,
                "alpha_wait": 1.0,
                "rho_decay": 1.0,
                "saturation_scale": 1.0,
                "contraflow_penalty": 0.0,
                "force_additive": True,
            },
            "block_heavy": {
                "alpha_commit": 1.0,
                "alpha_block": 1.5,
                "alpha_wait": 1.0,
                "rho_decay": 1.0,
                "saturation_scale": 1.0,
                "contraflow_penalty": 0.0,
                "force_additive": False,
            },
        },
    }
    weights_path = tmp_path / "laur_mlp_v1_weights.json"
    weights_path.write_text(json.dumps(weights), encoding="utf-8")

    export_runtime_dir(weights_path, tmp_path / "runtime")

    assert (tmp_path / "runtime" / "features.txt").read_text(encoding="utf-8") == "agents\nblocked_count\n"
    rules = list(csv.DictReader((tmp_path / "runtime" / "rules.csv").read_text(encoding="utf-8").splitlines()))
    assert [row["rule_id"] for row in rules] == ["additive_ltm", "block_heavy"]
    assert rules[1]["alpha_block"] == "1.5"
    assert (tmp_path / "runtime" / "layer0_weight.csv").read_text(encoding="utf-8").strip() == "0.1,0.2"

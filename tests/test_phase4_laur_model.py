from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

torch = pytest.importorskip("torch")

from czr004_teacher.features_laur import FEATURE_NAMES, FEATURE_SET  # noqa: E402
from czr004_teacher.update_sequences import validate_update_dataset_row  # noqa: E402
from eval.eval_laur_offline import _feature_vector_for_export, main as eval_main  # noqa: E402
from models.laur_ltm import load_export  # noqa: E402
from train.train_laur_ltm import _soft_rule_targets, main as train_main  # noqa: E402


RULES = ["additive_ltm", "commit_heavy", "block_heavy", "wait_light", "neutral_additive"]


def _row(index: int, rule_id: str, *, split: str = "train", harmful: bool = False) -> dict:
    features = {name: float(index + offset + 1) for offset, name in enumerate(FEATURE_NAMES)}
    feature_vector = [features[name] for name in FEATURE_NAMES]
    delta = 0.02 + index * 0.01 if rule_id != "neutral_additive" else 0.0
    row = {
        "schema_version": "phase4_laur_update_dataset_v1",
        "run_id": f"run-{index}",
        "checkpoint_id": f"run-{index}__iter0",
        "split": split,
        "map_name": f"map-{split}",
        "agents": 10 + index,
        "seed": index,
        "iteration": 0,
        "feature_set": FEATURE_SET,
        "feature_names": FEATURE_NAMES,
        "features": features,
        "feature_vector": feature_vector,
        "target": {
            "rule_class": rule_id,
            "rule_class_index": RULES.index(rule_id),
            "rule_vocab": RULES,
            "harmful_update": harmful,
            "harmful_rule_ids": ["block_light"] if harmful else [],
            "delta_ratio_best": delta,
            "label_confidence": abs(delta),
            "best_rule_id": rule_id if rule_id != "neutral_additive" else "additive_ltm",
            "neutral": rule_id == "neutral_additive",
            "additive_sum_of_loss_ratio": 1.0,
            "best_sum_of_loss_ratio": 1.0 - delta,
        },
        "source": {
            "checkpoint_schema_version": "phase4_laur_checkpoint_v1",
            "best_rule_label_schema_version": "phase4_laur_best_rule_label_v1",
            "probe_rule_count": len(RULES),
            "non_additive_rule_count": len(RULES) - 2,
            "trace_event_count": 12,
        },
    }
    assert validate_update_dataset_row(row) == []
    return row


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def test_phase4f_train_and_eval_smoke(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.jsonl"
    config = tmp_path / "laur_ltm.yaml"
    output_dir = tmp_path / "model"
    train_report = tmp_path / "train.md"
    eval_report = tmp_path / "eval.md"
    eval_csv = tmp_path / "eval.csv"
    rows = [
        _row(0, "commit_heavy", split="train"),
        _row(1, "block_heavy", split="train", harmful=True),
        _row(2, "wait_light", split="validation"),
        _row(3, "neutral_additive", split="test"),
    ]
    _write_jsonl(dataset, rows)
    config.write_text("schema_version: phase4_laur_config_v1\n", encoding="utf-8")

    assert train_main(
        [
            "--config",
            str(config),
            "--dataset",
            str(dataset),
            "--output-dir",
            str(output_dir),
            "--report",
            str(train_report),
            "--epochs",
            "25",
            "--hidden-dim",
            "8",
            "--learning-rate",
            "0.02",
            "--seed",
            "3",
        ]
    ) == 0
    weights = output_dir / "laur_mlp_v1_weights.json"
    assert weights.exists()
    assert (output_dir / "laur_mlp_v1_feature_stats.json").exists()
    assert (output_dir / "laur_mlp_v1_rules.json").exists()
    export = load_export(weights)
    assert export["input_features"] == FEATURE_NAMES
    assert list(export["rules"].values()) == RULES
    assert train_report.exists()

    assert eval_main(
        [
            "--config",
            str(config),
            "--dataset",
            str(dataset),
            "--model",
            str(weights),
            "--report",
            str(eval_report),
            "--summary-csv",
            str(eval_csv),
        ]
    ) == 0
    assert eval_report.exists()
    assert eval_csv.read_text(encoding="utf-8").splitlines()[0].startswith("split,run_id")


def test_phase4f_eval_builds_export_feature_subset() -> None:
    row = _row(0, "commit_heavy")
    export = {"input_features": FEATURE_NAMES[1:4]}

    vector = _feature_vector_for_export(row, export)

    assert vector == [float(row["features"][name]) for name in FEATURE_NAMES[1:4]]


def test_phase4f_soft_rule_targets_mix_hard_and_probe_delta_distribution() -> None:
    row = _row(0, "commit_heavy")
    probe_rows = {
        row["checkpoint_id"]: [
            {"rule_id": "additive_ltm", "delta_ratio_vs_additive": 0.0},
            {"rule_id": "commit_heavy", "delta_ratio_vs_additive": 0.02},
            {"rule_id": "block_heavy", "delta_ratio_vs_additive": 0.019},
        ]
    }

    targets = _soft_rule_targets(
        [row],
        RULES,
        probe_rows,
        neutral_threshold=0.005,
        temperature=0.01,
        hard_mix=0.5,
    )

    assert len(targets) == 1
    assert abs(sum(targets[0]) - 1.0) < 1e-9
    assert targets[0][RULES.index("commit_heavy")] > targets[0][RULES.index("block_heavy")]
    assert targets[0][RULES.index("block_heavy")] > 0.0

"""Offline evaluation for Phase4F Repair2 LAU-LTM rule-attention models."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.token_dataset_laur import read_jsonl  # noqa: E402
from models.laur_rule_attention import LAURuleAttentionModel  # noqa: E402
from train.train_laur_rule_attention import (  # noqa: E402
    evaluate_model,
    phase4f_gate,
    split_rows,
    validate_rows,
    write_csv,
)

try:
    import torch
except ImportError as exc:  # pragma: no cover - eval is run in czr004 env
    raise RuntimeError("PyTorch is required for Phase4F Repair2 evaluation") from exc


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path | None, root: Path) -> Path | None:
    if path is None:
        return None
    value = Path(path)
    return value if value.is_absolute() else root / value


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def write_report(path: Path, *, root: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    validation = summary["metrics_by_split"].get("validation", {})
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair2 Rule-Attention Offline Evaluation\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("## Code State\n\n")
        handle.write(f"- branch: `{git_value(['branch', '--show-current'], root)}`\n")
        handle.write(f"- commit: `{git_value(['rev-parse', '--short', 'HEAD'], root)}`\n\n")
        handle.write("## Inputs\n\n")
        handle.write(f"- dataset: `{summary['dataset']}`\n")
        handle.write(f"- model: `{summary['model']}`\n")
        handle.write(f"- architecture: `{summary['architecture']}`\n\n")
        handle.write("## Validation Metrics\n\n")
        handle.write(f"- top1: `{validation.get('rule_top1_accuracy')}`\n")
        handle.write(f"- top3: `{validation.get('rule_top3_accuracy')}`\n")
        handle.write(f"- family top1: `{validation.get('family_top1_accuracy')}`\n")
        handle.write(f"- harmful recall: `{validation.get('harmful_update_recall')}`\n")
        handle.write(f"- harmful precision: `{validation.get('harmful_update_precision')}`\n")
        handle.write(
            f"- mean selected delta: `{validation.get('predicted_rule_validation_mean_delta_ratio')}`\n\n"
        )
        handle.write("## Phase4F Gate\n\n")
        gate = summary.get("phase4f_gate", {})
        for key, value in gate.items():
            if key == "passed" or not isinstance(value, dict):
                continue
            handle.write(
                f"- {key}: `{value.get('value')}` vs `{value.get('threshold')}` -> "
                f"{'pass' if value.get('passed') else 'fail'}\n"
            )
        handle.write(f"\nOverall: `{'pass' if gate.get('passed') else 'fail'}`\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--summary-csv", type=Path, required=True)
    parser.add_argument("--harmful-threshold", type=float)
    parser.add_argument("--min-confidence", type=float)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"], default="auto")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    dataset_path = resolve_path(args.dataset, root)
    model_path = resolve_path(args.model, root)
    report_path = resolve_path(args.report, root)
    summary_json_path = resolve_path(args.summary_json, root)
    summary_csv_path = resolve_path(args.summary_csv, root)
    assert dataset_path and model_path and report_path and summary_json_path and summary_csv_path
    rows = read_jsonl(dataset_path)
    validate_rows(rows)
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    model = LAURuleAttentionModel(**checkpoint["model_args"]).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    harmful_threshold = float(
        args.harmful_threshold if args.harmful_threshold is not None else checkpoint.get("harmful_threshold", 0.10)
    )
    min_confidence = float(
        args.min_confidence if args.min_confidence is not None else checkpoint.get("min_confidence", 0.0)
    )
    splits = split_rows(rows)
    metrics_by_split: dict[str, dict[str, Any]] = {}
    all_records: list[dict[str, Any]] = []
    for split_name, split_values in sorted(splits.items()):
        metrics, records = evaluate_model(
            model,
            split_values,
            stats=checkpoint["feature_stats"],
            device=device,
            harmful_threshold=harmful_threshold,
            min_confidence=min_confidence,
        )
        metrics_by_split[split_name] = metrics
        all_records.extend(records)
    gate = phase4f_gate(metrics_by_split.get("validation", {}))
    validation_non_neutral = sum(1 for row in splits.get("validation", []) if not row["target"]["is_neutral_label"])
    gate["validation_non_neutral"]["value"] = validation_non_neutral
    gate["validation_non_neutral"]["passed"] = validation_non_neutral >= 50
    gate["passed"] = all(bool(value["passed"]) for value in gate.values() if isinstance(value, dict))
    write_csv(summary_csv_path, all_records)
    summary = {
        "schema_version": "phase4f_repair2_rule_attention_eval_summary_v1",
        "dataset": str(dataset_path),
        "model": str(model_path),
        "architecture": checkpoint["model_args"]["architecture"],
        "device": str(device),
        "harmful_threshold": harmful_threshold,
        "min_confidence": min_confidence,
        "metrics_by_split": metrics_by_split,
        "phase4f_gate": gate,
    }
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report_path, root=root, summary=summary)
    print(json.dumps({"summary_json": str(summary_json_path), "report": str(report_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

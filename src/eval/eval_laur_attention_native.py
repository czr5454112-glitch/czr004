"""Offline evaluation for Phase4F Repair5 attention-native LAUR models."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.stable_attention_dataset_laur import read_jsonl  # noqa: E402
from models.laur_attention_native import SET_RULE_TRANSFORMER_NAME, build_model  # noqa: E402
from train.train_laur_attention_native import (  # noqa: E402
    anti_escape_metrics,
    calibrate_safety_thresholds_from_scores,
    collect_harmful_rule_scores,
    config_get,
    evaluate_model,
    split_rows,
    validate_rows,
    write_csv,
)

try:
    import torch
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyTorch is required for Repair5 attention-native evaluation") from exc


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path | None, root: Path, *, seed: int | None = None) -> Path | None:
    if path is None:
        return None
    text = str(path)
    if seed is not None:
        text = text.format(seed=seed)
    value = Path(text)
    return value if value.is_absolute() else root / value


def load_config(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read Repair5 configs") from exc
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def dirty_state(root: Path) -> str:
    status = git_value(["status", "--short"], root)
    if not status:
        return "clean"
    tracked = [line for line in status.splitlines() if not line.startswith("??")]
    untracked = [line for line in status.splitlines() if line.startswith("??")]
    if tracked and untracked:
        return "tracked-dirty_untracked-present"
    if tracked:
        return "tracked-dirty"
    return "untracked-present"


def write_per_map_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    grouped: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[(str(record["map_name"]), int(record["agents"]), str(record["split"]))].append(record)
    fieldnames = [
        "split",
        "map_name",
        "agents",
        "sample_count",
        "use_nonadditive_target_count",
        "top1",
        "top3",
        "decision_accuracy",
        "high_margin_opportunity_count",
        "high_margin_capture_rate",
        "global_additive_or_defer_rate",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for (map_name, agents, split), values in sorted(grouped.items()):
            target = [row for row in values if row["decision_target"] == "use_nonadditive"]
            high_margin = [row for row in values if row["has_high_margin_nonadditive_opportunity"]]
            captured = [
                row
                for row in high_margin
                if row["selected_decision"] != "defer_ltm"
                and row["predicted_rule"] != "additive_ltm"
                and not row["selected_rule_harmful"]
                and float(row["selected_vs_additive_delta"]) >= float(row["opportunity_margin"])
            ]
            writer.writerow(
                {
                    "split": split,
                    "map_name": map_name,
                    "agents": agents,
                    "sample_count": len(values),
                    "use_nonadditive_target_count": len(target),
                    "top1": sum(1 for row in target if row["attention_top1"]) / len(target) if target else 0.0,
                    "top3": sum(1 for row in target if row["attention_top3"]) / len(target) if target else 0.0,
                    "decision_accuracy": sum(1 for row in values if row["decision_correct"]) / len(values),
                    "high_margin_opportunity_count": len(high_margin),
                    "high_margin_capture_rate": len(captured) / len(high_margin) if high_margin else 0.0,
                    "global_additive_or_defer_rate": sum(
                        1
                        for row in values
                        if row["selected_decision"] == "defer_ltm" or row["predicted_rule"] == "additive_ltm"
                    )
                    / len(values),
                }
            )


def write_confusion_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter((str(row["target_rule"]), str(row["predicted_rule"]), str(row["selected_decision"])) for row in records)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["target_rule", "predicted_rule", "selected_decision", "count"])
        writer.writeheader()
        for (target, predicted, decision), count in sorted(counts.items()):
            writer.writerow(
                {
                    "target_rule": target,
                    "predicted_rule": predicted,
                    "selected_decision": decision,
                    "count": count,
                }
            )


def write_report(path: Path, *, root: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    validation = summary["metrics_by_split"].get("validation", {})
    gate = validation.get("attention_native_gate", {})
    anti = validation.get("anti_escape_gate", {})
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair5 Attention-Native Offline Evaluation\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("## Code State\n\n")
        handle.write(f"- branch: `{git_value(['branch', '--show-current'], root)}`\n")
        handle.write(f"- commit: `{git_value(['rev-parse', '--short', 'HEAD'], root)}`\n")
        handle.write(f"- dirty: `{dirty_state(root)}`\n\n")
        handle.write("## Inputs\n\n")
        handle.write(f"- dataset: `{summary['dataset']}`\n")
        handle.write(f"- model: `{summary['model']}`\n")
        handle.write(f"- model_name: `{summary['model_name']}`\n")
        handle.write(f"- seed: `{summary.get('seed')}`\n")
        handle.write(f"- device: `{summary.get('device')}`\n\n")
        handle.write("## Validation Metrics\n\n")
        handle.write(f"- attention top1: `{validation.get('rule_top1_accuracy')}`\n")
        handle.write(f"- attention top3: `{validation.get('rule_top3_accuracy')}`\n")
        handle.write(f"- validation non-neutral/use_nonadditive: `{validation.get('validation_non_neutral')}`\n")
        handle.write(f"- harmful recall: `{validation.get('harmful_update_recall')}`\n")
        handle.write(f"- harmful precision: `{validation.get('harmful_update_precision')}`\n")
        handle.write(f"- mean selected delta: `{validation.get('predicted_rule_validation_mean_delta_ratio')}`\n")
        handle.write(f"- selected-vs-additive delta: `{validation.get('selected_vs_additive_delta_mean')}`\n")
        handle.write(f"- selected rules: `{validation.get('selected_rule_distribution')}`\n")
        handle.write(f"- decisions: `{validation.get('decision_distribution')}`\n\n")
        handle.write("## Attention-Native Gate\n\n")
        for key, value in gate.items():
            if key == "passed" or not isinstance(value, dict):
                continue
            handle.write(
                f"- {key}: `{value.get('value')}` vs `{value.get('threshold')}` -> "
                f"{'pass' if value.get('passed') else 'fail'}\n"
            )
        handle.write(f"\nOverall: `{'pass' if gate.get('passed') else 'fail'}`\n\n")
        handle.write("## Anti-Escape Gate\n\n")
        for key, value in anti.get("checks", {}).items():
            handle.write(
                f"- {key}: `{value.get('value')}` vs `{value.get('threshold')}` -> "
                f"{'pass' if value.get('passed') else 'fail'}\n"
            )
        handle.write(f"\nOverall: `{'pass' if anti.get('passed') else 'fail'}`\n")
        handle.write(f"Reason: `{anti.get('reason')}`\n\n")
        handle.write("## Boundary\n\n")
        handle.write(
            "This report is offline-only. Repair5 runtime remains forbidden unless "
            "all required original, attention-native, safety, anti-escape, and multi-seed gates pass.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--summary-csv", type=Path)
    parser.add_argument("--per-map-csv", type=Path)
    parser.add_argument("--confusion-csv", type=Path)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"])
    parser.add_argument("--calibrate-safety", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    config_path = resolve_path(args.config, root)
    config = load_config(config_path)
    native = config.get("attention_native", {}) if isinstance(config.get("attention_native"), dict) else {}
    train_config = config_get(config, "attention_native", "training", default={}) or {}
    eval_config = config_get(config, "attention_native", "eval", default={}) or {}
    gate_config = config.get("gate", {}) if isinstance(config.get("gate"), dict) else {}
    anti_thresholds = config.get("anti_escape", {}) if isinstance(config.get("anti_escape"), dict) else {}
    seed = int(args.seed if args.seed is not None else train_config.get("seed", 61))

    dataset_path = resolve_path(args.dataset or native.get("dataset_jsonl"), root)
    model_path = resolve_path(args.model or eval_config.get("model_path") or train_config.get("model_path"), root, seed=seed)
    report_path = resolve_path(args.report or eval_config.get("eval_report_md"), root, seed=seed)
    summary_json_path = resolve_path(args.summary_json or eval_config.get("eval_summary_json"), root, seed=seed)
    summary_csv_path = resolve_path(args.summary_csv or eval_config.get("eval_summary_csv"), root, seed=seed)
    per_map_path = resolve_path(args.per_map_csv or eval_config.get("per_map_csv"), root, seed=seed)
    confusion_path = resolve_path(args.confusion_csv or eval_config.get("confusion_csv"), root, seed=seed)
    if None in (dataset_path, model_path, report_path, summary_json_path, summary_csv_path, per_map_path, confusion_path):
        raise ValueError("dataset/model/report/summary/table paths are required")
    assert dataset_path and model_path and report_path and summary_json_path and summary_csv_path and per_map_path and confusion_path

    rows = read_jsonl(dataset_path)
    validate_rows(rows)
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    device_name = args.device or eval_config.get("device", "auto")
    if device_name == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(device_name)
    model = build_model(checkpoint.get("model_name", SET_RULE_TRANSFORMER_NAME), **checkpoint["model_args"]).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    splits = split_rows(rows)
    batch_size = int(args.batch_size or eval_config.get("batch_size", train_config.get("batch_size", 128)))
    safety_threshold: Any = checkpoint.get(
        "effective_safety_threshold",
        checkpoint.get("safety_threshold", float(eval_config.get("safety_threshold", 0.10))),
    )
    safety_calibration = checkpoint.get("safety_calibration")
    if bool(args.calibrate_safety or eval_config.get("calibrate_safety_thresholds", False)):
        calibration_grid = [
            float(value)
            for value in eval_config.get(
                "safety_calibration_thresholds",
                [0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80],
            )
        ]
        safety_calibration = calibrate_safety_thresholds_from_scores(
            collect_harmful_rule_scores(
                model,
                splits.get("train", []),
                stats=checkpoint["feature_stats"],
                device=device,
                batch_size=batch_size,
            ),
            candidate_thresholds=calibration_grid,
            min_recall=float(gate_config.get("harmful_recall_min", 0.80)),
            min_precision=float(gate_config.get("harmful_precision_min", 0.30)),
            mode=str(eval_config.get("safety_calibration_mode", "per_rule")),
        )
        safety_threshold = list(safety_calibration["thresholds"])
    selection = checkpoint.get("selection", {})
    metrics_by_split: dict[str, dict[str, Any]] = {}
    all_records: list[dict[str, Any]] = []
    for split_name, split_values in sorted(splits.items()):
        metrics, records = evaluate_model(
            model,
            split_values,
            stats=checkpoint["feature_stats"],
            device=device,
            batch_size=batch_size,
            safety_threshold=safety_threshold,
            safety_penalty=float(eval_config.get("safety_penalty", selection.get("safety_penalty", 0.02))),
            opportunity_threshold=float(eval_config.get("opportunity_threshold", selection.get("opportunity_threshold", 0.50))),
            defer_threshold=float(eval_config.get("defer_threshold", selection.get("defer_threshold", 0.50))),
            confidence_margin=float(eval_config.get("confidence_margin", selection.get("confidence_margin", 0.002))),
            anti_escape_thresholds=anti_thresholds,
        )
        metrics_by_split[split_name] = metrics
        all_records.extend(records)

    write_csv(summary_csv_path, all_records)
    validation_records = [record for record in all_records if record["split"] == "validation"]
    write_per_map_csv(per_map_path, validation_records)
    write_confusion_csv(confusion_path, validation_records)
    validation_anti = anti_escape_metrics(validation_records, thresholds=anti_thresholds)
    summary = {
        "schema_version": "phase4f_repair5_attention_native_eval_summary_v1",
        "dataset": str(dataset_path),
        "model": str(model_path),
        "model_name": checkpoint.get("model_name"),
        "model_args": checkpoint.get("model_args"),
        "seed": seed,
        "device": str(device),
        "safety_threshold": safety_threshold,
        "safety_calibration": safety_calibration,
        "metrics_by_split": metrics_by_split,
        "phase4f_gate": metrics_by_split.get("validation", {}).get("attention_native_gate", {}),
        "anti_escape_gate": validation_anti,
        "runtime_allowed": False,
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
    }
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report_path, root=root, summary=summary)
    print(json.dumps({"summary_json": str(summary_json_path), "report": str(report_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

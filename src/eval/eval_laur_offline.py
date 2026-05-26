"""Offline evaluation for exported Phase4F LAU-LTM JSON models."""

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

from czr004_teacher.update_sequences import read_probe_jsonl, validate_update_dataset_row  # noqa: E402
from models.laur_ltm import forward_exported_model, load_export  # noqa: E402


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve(path: str | Path | None, root: Path) -> Path | None:
    if path is None:
        return None
    value = Path(path)
    return value if value.is_absolute() else root / value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: JSONL row must be an object")
            rows.append(row)
    return rows


def _load_config(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read Phase4 LAUR config") from exc
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}


def _validate_rows(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for index, row in enumerate(rows, 1):
        errors.extend(f"row {index}: {error}" for error in validate_update_dataset_row(row))
    if not rows:
        errors.append("dataset is empty")
    return errors


def _topk_indices(values: list[float], k: int) -> list[int]:
    return sorted(range(len(values)), key=lambda index: values[index], reverse=True)[:k]


def _binary_metrics(labels: list[int], predictions: list[int]) -> dict[str, float]:
    tp = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 1)
    fp = sum(1 for label, pred in zip(labels, predictions) if label == 0 and pred == 1)
    fn = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 0)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def _binary_auroc(labels: list[int], scores: list[float]) -> float | None:
    positives = [score for label, score in zip(labels, scores) if label == 1]
    negatives = [score for label, score in zip(labels, scores) if label == 0]
    if not positives or not negatives:
        return None
    wins = 0.0
    for pos in positives:
        for neg in negatives:
            if pos > neg:
                wins += 1.0
            elif pos == neg:
                wins += 0.5
    return wins / (len(positives) * len(negatives))


def _probe_delta_lookup(path: Path | None) -> dict[tuple[str, str], float]:
    if path is None or not path.exists():
        return {}
    return {
        (str(row["checkpoint_id"]), str(row["rule_id"])): float(row["delta_ratio_vs_additive"])
        for row in read_probe_jsonl(path)
    }


def _predict_rows(
    rows: list[dict[str, Any]],
    export: dict[str, Any],
    *,
    harmful_threshold: float,
    probe_deltas: dict[tuple[str, str], float],
) -> list[dict[str, Any]]:
    rules = {int(index): rule_id for index, rule_id in export["rules"].items()}
    records: list[dict[str, Any]] = []
    for row in rows:
        prediction = forward_exported_model(export, [float(value) for value in row["feature_vector"]])
        probabilities = [float(value) for value in prediction["rule_probabilities"]]
        top3 = _topk_indices(probabilities, min(3, len(probabilities)))
        pred_index = top3[0]
        target_rule = str(row["target"]["rule_class"])
        target_index = int(row["target"]["rule_class_index"])
        pred_rule = rules[pred_index]
        if pred_rule in {"additive_ltm", "neutral_additive"}:
            predicted_delta = 0.0
        else:
            predicted_delta = probe_deltas.get(
                (str(row["checkpoint_id"]), pred_rule),
                float(row["target"]["delta_ratio_best"]) if pred_rule == target_rule else 0.0,
            )
        records.append(
            {
                "run_id": row["run_id"],
                "checkpoint_id": row["checkpoint_id"],
                "split": row["split"],
                "map_name": row["map_name"],
                "agents": row["agents"],
                "seed": row["seed"],
                "iteration": row["iteration"],
                "target_rule": target_rule,
                "predicted_rule": pred_rule,
                "top1_correct": int(pred_index == target_index),
                "top3_correct": int(target_index in top3),
                "harmful_update": int(bool(row["target"]["harmful_update"])),
                "harmful_update_probability": float(prediction["harmful_update_probability"]),
                "harmful_prediction": int(
                    float(prediction["harmful_update_probability"]) >= harmful_threshold
                ),
                "delta_ratio_best": float(row["target"]["delta_ratio_best"]),
                "predicted_rule_delta_ratio_vs_additive": predicted_delta,
                "delta_pred": float(prediction["delta_pred"]),
                "neutral": int(bool(row["target"]["neutral"])),
            }
        )
    return records


def _metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {
            "sample_count": 0,
            "rule_top1_accuracy": None,
            "rule_top3_accuracy": None,
            "non_neutral_rule_top1_accuracy": None,
            "harmful_update_precision": None,
            "harmful_update_recall": None,
            "harmful_update_f1": None,
            "safety_auroc": None,
            "predicted_rule_validation_mean_delta_ratio": None,
            "neutral_additive_rate": None,
        }
    top1 = [int(row["top1_correct"]) for row in records]
    top3 = [int(row["top3_correct"]) for row in records]
    non_neutral = [row for row in records if not int(row["neutral"])]
    harmful_labels = [int(row["harmful_update"]) for row in records]
    harmful_preds = [int(row["harmful_prediction"]) for row in records]
    harmful_scores = [float(row["harmful_update_probability"]) for row in records]
    safety = _binary_metrics(harmful_labels, harmful_preds)
    neutral_additive = [
        row for row in records if row["predicted_rule"] in {"additive_ltm", "neutral_additive"}
    ]
    return {
        "sample_count": len(records),
        "rule_top1_accuracy": sum(top1) / len(top1),
        "rule_top3_accuracy": sum(top3) / len(top3),
        "non_neutral_rule_top1_accuracy": (
            sum(int(row["top1_correct"]) for row in non_neutral) / len(non_neutral)
            if non_neutral
            else None
        ),
        "harmful_update_precision": safety["precision"],
        "harmful_update_recall": safety["recall"],
        "harmful_update_f1": safety["f1"],
        "safety_auroc": _binary_auroc(harmful_labels, harmful_scores),
        "predicted_rule_validation_mean_delta_ratio": sum(
            float(row["predicted_rule_delta_ratio_vs_additive"]) for row in records
        )
        / len(records),
        "neutral_additive_rate": len(neutral_additive) / len(records),
        "label_distribution": dict(sorted(Counter(row["target_rule"] for row in records).items())),
        "predicted_rule_distribution": dict(
            sorted(Counter(row["predicted_rule"] for row in records).items())
        ),
    }


def _metrics_by_split(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped["all"] = list(records)
    for row in records:
        grouped[str(row["split"])].append(row)
    return {split: _metrics(rows) for split, rows in sorted(grouped.items())}


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "split",
        "run_id",
        "checkpoint_id",
        "map_name",
        "agents",
        "seed",
        "iteration",
        "target_rule",
        "predicted_rule",
        "top1_correct",
        "top3_correct",
        "harmful_update",
        "harmful_update_probability",
        "harmful_prediction",
        "delta_ratio_best",
        "predicted_rule_delta_ratio_vs_additive",
        "delta_pred",
        "neutral",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            writer.writerow({key: row[key] for key in fieldnames})


def _git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def _dirty_state(cwd: Path) -> str:
    tracked = _git_value(["status", "--porcelain", "--untracked-files=no"], cwd)
    untracked = _git_value(["status", "--porcelain", "--untracked-files=normal"], cwd)
    if tracked:
        return "tracked-dirty"
    if any(line.startswith("??") for line in untracked.splitlines()):
        return "tracked-clean_untracked-present"
    return "clean"


def _display(path: str | Path, root: Path) -> str:
    value = Path(path)
    try:
        return str(value.relative_to(root))
    except ValueError:
        return str(value)


def _write_report(
    path: Path,
    *,
    root: Path,
    dataset_path: Path,
    model_path: Path,
    summary_csv: Path,
    probe_path: Path | None,
    metrics_by_split: dict[str, dict[str, Any]],
    gate: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    branch = _git_value(["branch", "--show-current"], root)
    commit = _git_value(["rev-parse", "--short", "HEAD"], root)
    dirty = _dirty_state(root)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F LAU-LTM Offline Evaluation Report\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z')}\n")
        handle.write(f"Status: {'passed' if gate['passed'] else 'failed'}\n\n")
        handle.write("## Code State\n\n")
        handle.write(f"- branch: `{branch}`\n")
        handle.write(f"- commit: `{commit}`\n")
        handle.write(f"- dirty: `{dirty}`\n\n")
        handle.write("## Inputs\n\n")
        handle.write(f"- dataset: `{_display(dataset_path, root)}`\n")
        handle.write(f"- model: `{_display(model_path, root)}`\n")
        handle.write(f"- probes: `{_display(probe_path, root) if probe_path else 'not_available'}`\n\n")
        handle.write("## Outputs\n\n")
        handle.write(f"- summary_csv: `{_display(summary_csv, root)}`\n\n")
        handle.write("## Metrics\n\n")
        for split, metrics in metrics_by_split.items():
            handle.write(f"### {split}\n\n")
            for key in (
                "sample_count",
                "rule_top1_accuracy",
                "rule_top3_accuracy",
                "non_neutral_rule_top1_accuracy",
                "harmful_update_precision",
                "harmful_update_recall",
                "harmful_update_f1",
                "safety_auroc",
                "predicted_rule_validation_mean_delta_ratio",
                "neutral_additive_rate",
            ):
                handle.write(f"- {key}: `{metrics.get(key)}`\n")
            handle.write("\n")
        handle.write("## Gate\n\n")
        for key, value in gate.items():
            handle.write(f"- {key}: `{value}`\n")
        handle.write("\n")
        handle.write("## Caveat\n\n")
        handle.write(
            "This offline eval checks exported-model inference and metrics only. "
            "The smoke dataset is too small for a learned-update performance claim.\n"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--probe-jsonl", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-csv", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--harmful-threshold", type=float, default=0.5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = _repo_root()
    config_path = _resolve(args.config, root)
    config = _load_config(config_path)
    dataset_path = _resolve(args.dataset, root)
    model_path = _resolve(args.model, root)
    report_path = _resolve(args.report, root)
    summary_csv_path = _resolve(args.summary_csv, root)
    summary_json_path = _resolve(args.summary_json, root) if args.summary_json else None
    probe_path = _resolve(args.probe_jsonl, root)
    if probe_path is None and config.get("probe_output_jsonl"):
        probe_path = _resolve(Path(str(config["probe_output_jsonl"])), root)
    if dataset_path is None or model_path is None or report_path is None or summary_csv_path is None:
        raise ValueError("--dataset, --model, --report, and --summary-csv are required")

    rows = _read_jsonl(dataset_path)
    schema_errors = _validate_rows(rows)
    if schema_errors:
        raise ValueError("Phase4F eval dataset schema errors:\n" + "\n".join(schema_errors[:20]))
    export = load_export(model_path)
    probe_deltas = _probe_delta_lookup(probe_path)
    records = _predict_rows(
        rows,
        export,
        harmful_threshold=float(args.harmful_threshold),
        probe_deltas=probe_deltas,
    )
    metrics = _metrics_by_split(records)
    _write_csv(summary_csv_path, records)
    gate = {
        "eval_script_runs_end_to_end": True,
        "schema_validation_passes": True,
        "model_export_file_exists": model_path.exists(),
        "validation_metrics_computed": bool(records),
        "summary_csv_written": summary_csv_path.exists(),
    }
    gate["passed"] = all(bool(value) for value in gate.values())
    summary = {
        "schema_version": "phase4_laur_offline_eval_summary_v1",
        "dataset": str(dataset_path),
        "model": str(model_path),
        "probe_jsonl": str(probe_path) if probe_path else None,
        "metrics_by_split": metrics,
        "summary_csv": str(summary_csv_path),
        "gate": gate,
    }
    if summary_json_path is not None:
        summary_json_path.parent.mkdir(parents=True, exist_ok=True)
        summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_report(
        report_path,
        root=root,
        dataset_path=dataset_path,
        model_path=model_path,
        summary_csv=summary_csv_path,
        probe_path=probe_path,
        metrics_by_split=metrics,
        gate=gate,
    )
    print(json.dumps({"report": str(report_path), "summary_csv": str(summary_csv_path), "passed": gate["passed"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

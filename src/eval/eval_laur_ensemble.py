"""Offline evaluation for an ensemble of exported Phase4F LAU-LTM JSON models."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from eval.eval_laur_offline import (  # noqa: E402
    _feature_vector_for_export,
    _metrics_by_split,
    _probe_delta_lookup,
    _read_jsonl,
    _topk_indices,
    _validate_rows,
    _write_csv,
)
from models.laur_ltm import forward_exported_model, load_export  # noqa: E402


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path | None, root: Path) -> Path | None:
    if path is None:
        return None
    value = Path(path)
    return value if value.is_absolute() else root / value


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def predict_rows(
    rows: list[dict[str, Any]],
    exports: list[dict[str, Any]],
    *,
    harmful_threshold: float,
    probe_deltas: dict[tuple[str, str], float],
) -> list[dict[str, Any]]:
    if not exports:
        raise ValueError("at least one model is required")
    base_rules = {int(index): rule_id for index, rule_id in exports[0]["rules"].items()}
    for export in exports[1:]:
        rules = {int(index): rule_id for index, rule_id in export["rules"].items()}
        if rules != base_rules:
            raise ValueError("all ensemble models must use the same rule vocabulary")

    records: list[dict[str, Any]] = []
    for row in rows:
        rule_probability_rows: list[list[float]] = []
        harmful_scores: list[float] = []
        delta_scores: list[float] = []
        for export in exports:
            prediction = forward_exported_model(export, _feature_vector_for_export(row, export))
            rule_probability_rows.append([float(value) for value in prediction["rule_probabilities"]])
            harmful_scores.append(float(prediction["harmful_update_probability"]))
            delta_scores.append(float(prediction["delta_pred"]))
        probabilities = [
            average([probability_row[index] for probability_row in rule_probability_rows])
            for index in range(len(rule_probability_rows[0]))
        ]
        top3 = _topk_indices(probabilities, min(3, len(probabilities)))
        pred_index = top3[0]
        target_rule = str(row["target"]["rule_class"])
        target_index = int(row["target"]["rule_class_index"])
        pred_rule = base_rules[pred_index]
        if pred_rule in {"additive_ltm", "neutral_additive"}:
            predicted_delta = 0.0
        else:
            predicted_delta = probe_deltas.get((str(row["checkpoint_id"]), pred_rule), 0.0)
        harmful_probability = average(harmful_scores)
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
                "harmful_update_probability": harmful_probability,
                "harmful_prediction": int(harmful_probability >= harmful_threshold),
                "delta_ratio_best": float(row["target"]["delta_ratio_best"]),
                "predicted_rule_delta_ratio_vs_additive": predicted_delta,
                "delta_pred": average(delta_scores),
                "neutral": int(bool(row["target"]["neutral"])),
            }
        )
    return records


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics = summary["metrics_by_split"]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F LAU-LTM Ensemble Offline Evaluation\n\n")
        handle.write("## Inputs\n\n")
        handle.write(f"- dataset: `{summary['dataset']}`\n")
        handle.write("- models:\n")
        for model in summary["models"]:
            handle.write(f"  - `{model}`\n")
        handle.write(f"- harmful_threshold: `{summary['harmful_threshold']}`\n\n")
        handle.write("## Metrics\n\n")
        for split, values in metrics.items():
            handle.write(f"### {split}\n\n")
            for key in (
                "sample_count",
                "rule_top1_accuracy",
                "rule_top3_accuracy",
                "harmful_update_precision",
                "harmful_update_recall",
                "predicted_rule_validation_mean_delta_ratio",
                "neutral_additive_rate",
            ):
                handle.write(f"- {key}: `{values.get(key)}`\n")
            handle.write("\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--models", type=Path, nargs="+", required=True)
    parser.add_argument("--probe-jsonl", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-csv", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--harmful-threshold", type=float, default=0.1)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    dataset_path = resolve_path(args.dataset, root)
    model_paths = [resolve_path(path, root) for path in args.models]
    probe_path = resolve_path(args.probe_jsonl, root)
    report_path = resolve_path(args.report, root)
    summary_csv_path = resolve_path(args.summary_csv, root)
    summary_json_path = resolve_path(args.summary_json, root)
    assert dataset_path and report_path and summary_csv_path and summary_json_path

    rows = _read_jsonl(dataset_path)
    errors = _validate_rows(rows)
    if errors:
        raise ValueError("Phase4F eval dataset schema errors:\n" + "\n".join(errors[:20]))
    exports = [load_export(path) for path in model_paths if path is not None]
    records = predict_rows(
        rows,
        exports,
        harmful_threshold=float(args.harmful_threshold),
        probe_deltas=_probe_delta_lookup(probe_path),
    )
    metrics = _metrics_by_split(records)
    _write_csv(summary_csv_path, records)
    summary = {
        "schema_version": "phase4_laur_ensemble_eval_summary_v1",
        "dataset": str(dataset_path),
        "models": [str(path) for path in model_paths],
        "probe_jsonl": str(probe_path) if probe_path else None,
        "harmful_threshold": float(args.harmful_threshold),
        "metrics_by_split": metrics,
        "summary_csv": str(summary_csv_path),
    }
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report_path, summary)
    print(json.dumps({"report": str(report_path), "summary_json": str(summary_json_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

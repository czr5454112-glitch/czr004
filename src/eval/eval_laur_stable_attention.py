"""Offline evaluation for Phase4F.4 LAU stable-target attention models."""

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
from czr004_teacher.stable_attention_tokens_laur import (  # noqa: E402
    EXECUTABLE_RULE_IDS,
    SET_RULE_TRANSFORMER_NAME,
)
from models.laur_stable_attention import build_model  # noqa: E402
from train.train_laur_stable_attention import (  # noqa: E402
    config_get,
    dirty_state,
    evaluate_model,
    git_value,
    phase4f_gate,
    resolve_path,
    split_rows,
    validate_rows,
    write_csv,
)

try:
    import torch
except ImportError as exc:  # pragma: no cover - eval is run in czr004 env
    raise RuntimeError("PyTorch is required for Phase4F.4 stable-attention evaluation") from exc


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_config(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read Phase4 LAUR configs") from exc
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


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
        "top1",
        "top3",
        "mean_selected_delta",
        "fallback_rate",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for (map_name, agents, split), values in sorted(grouped.items()):
            writer.writerow(
                {
                    "split": split,
                    "map_name": map_name,
                    "agents": agents,
                    "sample_count": len(values),
                    "top1": sum(1 for row in values if row["stable_top1"]) / len(values),
                    "top3": sum(1 for row in values if row["stable_top3"]) / len(values),
                    "mean_selected_delta": sum(float(row["selected_delta"]) for row in values) / len(values),
                    "fallback_rate": sum(1 for row in values if row["fallback_reason"] != "selected") / len(values),
                }
            )


def write_confusion_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter((str(row["target_rule_executable"]), str(row["predicted_rule"])) for row in records)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["target_rule", "predicted_rule", "count"])
        writer.writeheader()
        for (target, predicted), count in sorted(counts.items()):
            writer.writerow({"target_rule": target, "predicted_rule": predicted, "count": count})


def write_threshold_sweep_csv(
    path: Path,
    *,
    model: Any,
    rows: list[dict[str, Any]],
    stats: dict[str, Any],
    device: torch.device,
    batch_size: int,
    safety_penalty: float,
    confidence_margin: float,
    thresholds: list[float],
) -> list[dict[str, Any]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for threshold in thresholds:
        metrics, _ = evaluate_model(
            model,
            rows,
            stats=stats,
            device=device,
            batch_size=batch_size,
            safety_threshold=float(threshold),
            safety_penalty=safety_penalty,
            confidence_margin=confidence_margin,
        )
        results.append(
            {
                "safety_threshold": float(threshold),
                "top1": metrics.get("rule_top1_accuracy"),
                "top3": metrics.get("rule_top3_accuracy"),
                "harmful_recall": metrics.get("harmful_update_recall"),
                "harmful_precision": metrics.get("harmful_update_precision"),
                "mean_selected_delta": metrics.get("predicted_rule_validation_mean_delta_ratio"),
                "fallback_rate": metrics.get("fallback_rate"),
                "unsafe_fallback_rate": metrics.get("unsafe_fallback_rate"),
                "low_confidence_fallback_rate": metrics.get("low_confidence_fallback_rate"),
            }
        )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].keys()) if results else ["safety_threshold"])
        writer.writeheader()
        writer.writerows(results)
    return results


def _metric_from_summary(summary: dict[str, Any], key: str) -> Any:
    return summary.get("metrics_by_split", {}).get("validation", {}).get(key)


def advanced_promotion_gate(
    summaries: list[dict[str, Any]],
    *,
    repair3_baseline: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not summaries:
        return {"passed": False, "reason": "no seed summaries available"}
    deltas = [float(_metric_from_summary(summary, "predicted_rule_validation_mean_delta_ratio") or 0.0) for summary in summaries]
    top3 = [float(_metric_from_summary(summary, "rule_top3_accuracy") or 0.0) for summary in summaries]
    recall = [float(_metric_from_summary(summary, "harmful_update_recall") or 0.0) for summary in summaries]
    baseline_top3 = None
    if repair3_baseline is not None:
        baseline_top3 = repair3_baseline.get("metrics_by_split", {}).get("validation", {}).get("rule_top3_accuracy")
        if baseline_top3 is None:
            baseline_top3 = repair3_baseline.get("validation", {}).get("top3")
    baseline_top3_float = float(baseline_top3) if baseline_top3 is not None else None
    checks = {
        "condition_a_positive_delta_two_of_three": {
            "value": sum(1 for value in deltas if value > 0.0),
            "threshold": ">= 2",
            "passed": sum(1 for value in deltas if value > 0.0) >= min(2, len(deltas)),
        },
        "condition_b_average_delta_positive": {
            "value": sum(deltas) / len(deltas),
            "threshold": "> 0.0",
            "passed": (sum(deltas) / len(deltas)) > 0.0,
        },
        "condition_c_top3_not_worse_than_repair3_minus_002": {
            "value": sum(top3) / len(top3),
            "threshold": None if baseline_top3_float is None else baseline_top3_float - 0.02,
            "passed": True if baseline_top3_float is None else (sum(top3) / len(top3)) >= baseline_top3_float - 0.02,
        },
        "condition_d_recall_every_seed": {
            "value": min(recall),
            "threshold": ">= 0.80",
            "passed": min(recall) >= 0.80,
        },
    }
    condition_items = [value for value in checks.values() if isinstance(value, dict)]
    checks["passed"] = any(bool(value["passed"]) for value in condition_items)
    checks["promotion_rule"] = "at_least_one_advanced_condition"
    return checks


def write_report(path: Path, *, root: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    validation = summary["metrics_by_split"].get("validation", {})
    gate = summary.get("phase4f_gate", {})
    promotion = summary.get("advanced_promotion_gate", {})
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair4 Stable-Attention Offline Evaluation\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("## Code State\n\n")
        handle.write(f"- branch: `{git_value(['branch', '--show-current'], root)}`\n")
        handle.write(f"- commit: `{git_value(['rev-parse', '--short', 'HEAD'], root)}`\n")
        handle.write(f"- dirty: `{dirty_state(root)}`\n\n")
        handle.write("## Inputs\n\n")
        handle.write(f"- dataset: `{summary['dataset']}`\n")
        handle.write(f"- model: `{summary['model']}`\n")
        handle.write(f"- model_name: `{summary['model_name']}`\n")
        handle.write(f"- parameter_count: `{summary.get('parameter_count')}`\n")
        handle.write(f"- seed: `{summary.get('seed')}`\n")
        handle.write(f"- device: `{summary.get('device')}`\n\n")
        handle.write("## Validation Metrics\n\n")
        handle.write(f"- executable/stable top1: `{validation.get('rule_top1_accuracy')}`\n")
        handle.write(f"- executable/stable top3: `{validation.get('rule_top3_accuracy')}`\n")
        handle.write(f"- original top1: `{validation.get('original_target_top1_accuracy')}`\n")
        handle.write(f"- original top3: `{validation.get('original_target_top3_accuracy')}`\n")
        handle.write(f"- harmful recall: `{validation.get('harmful_update_recall')}`\n")
        handle.write(f"- harmful precision: `{validation.get('harmful_update_precision')}`\n")
        handle.write(f"- mean selected delta: `{validation.get('predicted_rule_validation_mean_delta_ratio')}`\n")
        handle.write(f"- selected-vs-additive delta: `{validation.get('selected_vs_additive_delta_mean')}`\n")
        handle.write(f"- fallback rate: `{validation.get('fallback_rate')}`\n")
        handle.write(f"- pairwise ranking accuracy: `{validation.get('pairwise_ranking_accuracy')}`\n")
        handle.write(f"- Spearman q/delta: `{validation.get('spearman_q_delta_mean')}`\n\n")
        handle.write("## Phase4F Gate\n\n")
        for key, value in gate.items():
            if key == "passed" or not isinstance(value, dict):
                continue
            handle.write(
                f"- {key}: `{value.get('value')}` vs `{value.get('threshold')}` -> "
                f"{'pass' if value.get('passed') else 'fail'}\n"
            )
        handle.write(f"\nOverall: `{'pass' if gate.get('passed') else 'fail'}`\n\n")
        handle.write("## Advanced Promotion Gate\n\n")
        for key, value in promotion.items():
            if key == "passed" or not isinstance(value, dict):
                continue
            handle.write(
                f"- {key}: `{value.get('value')}` vs `{value.get('threshold')}` -> "
                f"{'pass' if value.get('passed') else 'fail'}\n"
            )
        handle.write(f"\nPhase5.5 allowed: `{'yes' if gate.get('passed') and promotion.get('passed') else 'no'}`\n\n")
        handle.write("## Boundary\n\n")
        handle.write(
            "This report is offline-only. Phase5.5 runtime integration is allowed "
            "only if the original Phase4F gate and the multi-seed advanced promotion "
            "gate both pass.\n"
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
    parser.add_argument("--threshold-sweep-csv", type=Path)
    parser.add_argument("--safety-threshold", type=float)
    parser.add_argument("--safety-penalty", type=float)
    parser.add_argument("--confidence-margin", type=float)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    config_path = resolve_path(args.config, root)
    config = load_config(config_path)
    stable_attention = config.get("stable_attention", {}) if isinstance(config.get("stable_attention"), dict) else {}
    train_config = config_get(config, "stable_attention", "training", default={}) or {}
    eval_config = config_get(config, "stable_attention", "eval", default={}) or {}
    seed = int(args.seed if args.seed is not None else train_config.get("seed", 61))

    dataset_path = resolve_path(args.dataset or stable_attention.get("dataset_jsonl"), root)
    model_path = resolve_path(args.model or eval_config.get("model_path") or train_config.get("model_path"), root, seed=seed)
    if model_path is None:
        output_dir = resolve_path(train_config.get("model_output_dir"), root, seed=seed)
        model_path = output_dir / "laur_stable_attention_v1.pt" if output_dir is not None else None
    report_path = resolve_path(args.report or eval_config.get("eval_report_md"), root, seed=seed)
    summary_json_path = resolve_path(args.summary_json or eval_config.get("eval_summary_json"), root, seed=seed)
    summary_csv_path = resolve_path(args.summary_csv or eval_config.get("eval_summary_csv"), root, seed=seed)
    per_map_path = resolve_path(args.per_map_csv or eval_config.get("per_map_csv"), root, seed=seed)
    confusion_path = resolve_path(args.confusion_csv or eval_config.get("confusion_csv"), root, seed=seed)
    threshold_path = resolve_path(args.threshold_sweep_csv or eval_config.get("threshold_sweep_csv"), root, seed=seed)
    if None in (dataset_path, model_path, report_path, summary_json_path, summary_csv_path, per_map_path, confusion_path, threshold_path):
        raise ValueError("dataset/model/report/summary/table paths are required")
    assert dataset_path and model_path and report_path and summary_json_path and summary_csv_path and per_map_path and confusion_path and threshold_path

    rows = read_jsonl(dataset_path)
    validate_rows(rows)
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    if args.device == "auto" or (args.device is None and str(eval_config.get("device", "auto")) == "auto"):
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device or eval_config.get("device", "cpu"))
    model = build_model(checkpoint.get("model_name", SET_RULE_TRANSFORMER_NAME), **checkpoint["model_args"]).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    safety_threshold = float(args.safety_threshold if args.safety_threshold is not None else eval_config.get("safety_threshold", checkpoint.get("safety_threshold", 0.10)))
    safety_penalty = float(args.safety_penalty if args.safety_penalty is not None else eval_config.get("safety_penalty", checkpoint.get("safety_penalty", 0.02)))
    confidence_margin = float(args.confidence_margin if args.confidence_margin is not None else eval_config.get("confidence_margin", checkpoint.get("confidence_margin", 0.002)))
    batch_size = int(args.batch_size or eval_config.get("batch_size", train_config.get("batch_size", 128)))
    splits = split_rows(rows)
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
            safety_penalty=safety_penalty,
            confidence_margin=confidence_margin,
        )
        metrics_by_split[split_name] = metrics
        all_records.extend(records)
    gate = phase4f_gate(metrics_by_split.get("validation", {}))
    validation_non_neutral = sum(1 for row in splits.get("validation", []) if not row["target"]["is_neutral_label"])
    gate["validation_non_neutral"]["value"] = validation_non_neutral
    gate["validation_non_neutral"]["passed"] = validation_non_neutral >= 50
    gate["passed"] = all(bool(value["passed"]) for value in gate.values() if isinstance(value, dict))

    write_csv(summary_csv_path, all_records)
    validation_records = [record for record in all_records if record["split"] == "validation"]
    write_per_map_csv(per_map_path, validation_records)
    write_confusion_csv(confusion_path, validation_records)
    sweep_thresholds = [float(value) for value in eval_config.get("threshold_sweep", [0.05, 0.10, 0.20, 0.30])]
    threshold_sweep = write_threshold_sweep_csv(
        threshold_path,
        model=model,
        rows=splits.get("validation", []),
        stats=checkpoint["feature_stats"],
        device=device,
        batch_size=batch_size,
        safety_penalty=safety_penalty,
        confidence_margin=confidence_margin,
        thresholds=sweep_thresholds,
    )
    baseline_path = resolve_path(eval_config.get("repair3_baseline_summary_json"), root)
    baseline = load_json(baseline_path)
    seed_summary_paths = [
        resolve_path(path, root, seed=int(value))
        for value, path in [
            (seed_value, eval_config.get("eval_summary_json"))
            for seed_value in eval_config.get("promotion_seeds", [seed])
        ]
    ]
    seed_summaries = [load_json(path) for path in seed_summary_paths if path is not None and path.exists()]
    current_summary_stub = {
        "metrics_by_split": metrics_by_split,
        "seed": seed,
    }
    if not any(summary and int(summary.get("seed", -1)) == seed for summary in seed_summaries):
        seed_summaries.append(current_summary_stub)
    promotion = advanced_promotion_gate([summary for summary in seed_summaries if summary], repair3_baseline=baseline)
    summary = {
        "schema_version": "phase4f_repair4_stable_attention_eval_summary_v1",
        "dataset": str(dataset_path),
        "model": str(model_path),
        "model_name": checkpoint.get("model_name"),
        "model_args": checkpoint.get("model_args"),
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "seed": seed,
        "device": str(device),
        "safety_threshold": safety_threshold,
        "safety_penalty": safety_penalty,
        "confidence_margin": confidence_margin,
        "metrics_by_split": metrics_by_split,
        "phase4f_gate": gate,
        "advanced_promotion_gate": promotion,
        "threshold_sweep": threshold_sweep,
        "repair3_baseline_summary_json": str(baseline_path) if baseline_path else None,
        "phase5p5_runtime_allowed": bool(gate.get("passed") and promotion.get("passed")),
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

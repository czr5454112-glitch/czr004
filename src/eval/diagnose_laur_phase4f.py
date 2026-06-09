"""Failure diagnostics for Phase4F LAUR-LTM full artifacts.

The diagnostics here are intentionally offline-only. They read the recorded
dataset, probe rows, and exported evaluation CSV, then produce tables that make
the failed validation gate easier to debug without changing the gate itself.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any


DEFAULT_DATASET = Path("artifacts/teacher/laur/full/update_labels/phase4_laur_update_dataset_full.jsonl")
DEFAULT_PROBES = Path("artifacts/teacher/laur/full/probes/phase4_laur_probe_full.jsonl")
DEFAULT_EVAL_CSV = Path("outputs/tables/phase4_laur_ltm_offline_eval_full.csv")
DEFAULT_OUTPUT_DIR = Path("outputs/tables")
DEFAULT_REPORT = Path("outputs/reports/phase4f_laur_failure_diagnostics.md")
DEFAULT_SUMMARY_JSON = Path("outputs/reports/phase4_laur_ltm_offline_eval_full_summary.json")

MARGIN_THRESHOLDS = (0.001, 0.0025, 0.005, 0.01, 0.02, 0.05)
SAFETY_THRESHOLDS = tuple(round(index / 20.0, 2) for index in range(0, 21))
NEUTRAL_DELTA_THRESHOLD = 0.005


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path, root: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
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


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def pstdev(values: list[float]) -> float | None:
    if not values:
        return None
    mu = sum(values) / len(values)
    return math.sqrt(sum((value - mu) ** 2 for value in values) / len(values))


def quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def fmt_float(value: float | None, digits: int = 4) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def binary_metrics(labels: list[int], predictions: list[int]) -> dict[str, float]:
    tp = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 1)
    fp = sum(1 for label, pred in zip(labels, predictions) if label == 0 and pred == 1)
    fn = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 0)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def group_probe_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["checkpoint_id"])].append(row)
    return grouped


def probe_delta(row: dict[str, Any]) -> float:
    return safe_float(row.get("delta_ratio_vs_additive"), default=float("-inf"))


def sorted_probe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (probe_delta(row), str(row.get("rule_id", ""))), reverse=True)


def margin_detail_for_checkpoint(
    dataset_row: dict[str, Any],
    probe_rows: list[dict[str, Any]],
    *,
    neutral_threshold: float = NEUTRAL_DELTA_THRESHOLD,
) -> dict[str, Any]:
    checkpoint_id = str(dataset_row["checkpoint_id"])
    target = dataset_row["target"]
    sorted_rows = sorted_probe_rows(probe_rows)
    if not sorted_rows:
        raise ValueError(f"no probe rows for checkpoint {checkpoint_id}")

    best = sorted_rows[0]
    second = sorted_rows[1] if len(sorted_rows) > 1 else sorted_rows[0]
    best_delta = probe_delta(best)
    second_delta = probe_delta(second)
    additive_delta = next(
        (probe_delta(row) for row in probe_rows if str(row.get("rule_id")) == "additive_ltm"),
        0.0,
    )
    detail: dict[str, Any] = {
        "split": dataset_row["split"],
        "map_name": dataset_row["map_name"],
        "agents": dataset_row["agents"],
        "seed": dataset_row["seed"],
        "iteration": dataset_row["iteration"],
        "checkpoint_id": checkpoint_id,
        "target_rule": target["rule_class"],
        "target_best_rule_id": target.get("best_rule_id"),
        "delta_best_rule_id": best.get("rule_id"),
        "second_delta_rule_id": second.get("rule_id"),
        "candidate_count": len(probe_rows),
        "harmful_candidate_count": sum(1 for row in probe_rows if bool(row.get("harmful"))),
        "best_delta_ratio": best_delta,
        "second_delta_ratio": second_delta,
        "best_minus_second_margin": best_delta - second_delta,
        "best_minus_additive_margin": best_delta - additive_delta,
        "best_minus_neutral_threshold": best_delta - neutral_threshold,
        "label_delta_ratio_best": safe_float(target.get("delta_ratio_best")),
        "label_confidence": safe_float(target.get("label_confidence")),
        "neutral": int(bool(target.get("neutral"))),
    }
    for threshold in MARGIN_THRESHOLDS:
        suffix = str(threshold).replace(".", "_")
        detail[f"within_{suffix}_count"] = sum(
            1 for row in probe_rows if best_delta - probe_delta(row) <= threshold
        )
        detail[f"margin_le_{suffix}"] = int(best_delta - second_delta <= threshold)
    return detail


def build_margin_details(
    dataset_rows: list[dict[str, Any]], probe_rows_by_checkpoint: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for row in dataset_rows:
        checkpoint_id = str(row["checkpoint_id"])
        probe_rows = probe_rows_by_checkpoint.get(checkpoint_id, [])
        if not probe_rows:
            continue
        details.append(margin_detail_for_checkpoint(row, probe_rows))
    return details


def build_margin_histogram(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in details:
        groups[("all", "all")].append(row)
        groups[("split", str(row["split"]))].append(row)
        groups[("map", str(row["map_name"]))].append(row)
        if str(row["split"]) == "validation":
            groups[("validation_map", str(row["map_name"]))].append(row)
            groups[("validation_agents", str(row["agents"]))].append(row)
            groups[("validation_iteration", str(row["iteration"]))].append(row)

    output: list[dict[str, Any]] = []
    for (group_type, group_value), rows in sorted(groups.items()):
        for threshold in MARGIN_THRESHOLDS:
            near = [row for row in rows if safe_float(row["best_minus_second_margin"]) <= threshold]
            output.append(
                {
                    "group_type": group_type,
                    "group_value": group_value,
                    "threshold": threshold,
                    "sample_count": len(rows),
                    "near_tie_count": len(near),
                    "near_tie_rate": len(near) / len(rows) if rows else 0.0,
                    "neutral_count": sum(int(row["neutral"]) for row in rows),
                    "mean_best_minus_second_margin": mean(
                        [safe_float(row["best_minus_second_margin"]) for row in rows]
                    ),
                    "median_best_minus_second_margin": quantile(
                        [safe_float(row["best_minus_second_margin"]) for row in rows], 0.5
                    ),
                    "mean_best_minus_neutral_threshold": mean(
                        [safe_float(row["best_minus_neutral_threshold"]) for row in rows]
                    ),
                }
            )
    return output


def family_for_rule(rule_id: str) -> str:
    if rule_id in {"additive_ltm", "neutral_additive"}:
        return "additive_or_neutral"
    if rule_id.startswith("block_"):
        return "block"
    if rule_id.startswith("wait_"):
        return "wait"
    if rule_id.startswith("decay_"):
        return "decay"
    if rule_id.startswith("commit_"):
        return "commit"
    return rule_id


def build_confusion_rows(eval_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], Counter[tuple[str, str]]] = defaultdict(Counter)
    for row in eval_rows:
        target = str(row["target_rule"])
        predicted = str(row["predicted_rule"])
        keys = [
            ("all", "all"),
            ("split", str(row["split"])),
            ("map", str(row["map_name"])),
            ("agents", str(row["agents"])),
            ("iteration", str(row["iteration"])),
            ("split_map", f"{row['split']}:{row['map_name']}"),
        ]
        for key in keys:
            groups[key][(target, predicted)] += 1

    output: list[dict[str, Any]] = []
    for (group_type, group_value), counter in sorted(groups.items()):
        for (target, predicted), count in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
            output.append(
                {
                    "group_type": group_type,
                    "group_value": group_value,
                    "target_rule": target,
                    "predicted_rule": predicted,
                    "target_family": family_for_rule(target),
                    "predicted_family": family_for_rule(predicted),
                    "correct_rule": int(target == predicted),
                    "correct_family": int(family_for_rule(target) == family_for_rule(predicted)),
                    "count": count,
                }
            )
    return output


def safety_metrics_for_threshold(rows: list[dict[str, str]], threshold: float) -> dict[str, Any]:
    labels = [safe_int(row["harmful_update"]) for row in rows]
    predictions = [
        int(safe_float(row["harmful_update_probability"]) >= threshold)
        for row in rows
    ]
    metrics = binary_metrics(labels, predictions)
    deltas = [safe_float(row["predicted_rule_delta_ratio_vs_additive"]) for row in rows]
    gated_deltas = [
        0.0 if prediction else safe_float(row["predicted_rule_delta_ratio_vs_additive"])
        for row, prediction in zip(rows, predictions)
    ]
    predicted_count = sum(predictions)
    metrics.update(
        {
            "sample_count": len(rows),
            "harmful_count": sum(labels),
            "predicted_harmful_count": predicted_count,
            "fallback_rate": predicted_count / len(rows) if rows else 0.0,
            "mean_delta_no_gate": mean(deltas),
            "mean_delta_after_gate": mean(gated_deltas),
            "mean_delta_loss_from_gate": (
                (mean(deltas) or 0.0) - (mean(gated_deltas) or 0.0)
            ),
        }
    )
    return metrics


def build_safety_sweep_rows(eval_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in eval_rows:
        groups[("all", "all")].append(row)
        groups[("split", str(row["split"]))].append(row)
        groups[("map", str(row["map_name"]))].append(row)
        if str(row["split"]) == "validation":
            groups[("validation_map", str(row["map_name"]))].append(row)
            groups[("validation_agents", str(row["agents"]))].append(row)
            groups[("validation_iteration", str(row["iteration"]))].append(row)

    output: list[dict[str, Any]] = []
    for (group_type, group_value), rows in sorted(groups.items()):
        for threshold in SAFETY_THRESHOLDS:
            metrics = safety_metrics_for_threshold(rows, threshold)
            output.append({"group_type": group_type, "group_value": group_value, "threshold": threshold, **metrics})
    return output


def summarize_values(values: list[float]) -> dict[str, float | None]:
    return {
        "mean": mean(values),
        "std": pstdev(values),
        "q10": quantile(values, 0.1),
        "q50": quantile(values, 0.5),
        "q90": quantile(values, 0.9),
    }


def feature_names_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    for row in rows:
        names = row.get("feature_names")
        if isinstance(names, list) and all(isinstance(name, str) for name in names):
            return list(names)
    feature_keys: set[str] = set()
    for row in rows:
        features = row.get("features")
        if isinstance(features, dict):
            feature_keys.update(str(key) for key in features)
    return sorted(feature_keys)


def feature_value(row: dict[str, Any], name: str) -> float | None:
    features = row.get("features")
    if isinstance(features, dict) and name in features:
        return safe_float(features[name])
    names = row.get("feature_names")
    vector = row.get("feature_vector")
    if isinstance(names, list) and isinstance(vector, list) and name in names:
        index = names.index(name)
        if index < len(vector):
            return safe_float(vector[index])
    return None


def values_for_feature(rows: list[dict[str, Any]], feature_name: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = feature_value(row, feature_name)
        if value is not None:
            values.append(value)
    return values


def standardized_mean_difference(base: list[float], other: list[float]) -> float | None:
    if not base or not other:
        return None
    base_mean = mean(base) or 0.0
    other_mean = mean(other) or 0.0
    base_std = pstdev(base) or 0.0
    other_std = pstdev(other) or 0.0
    pooled = math.sqrt((base_std**2 + other_std**2) / 2.0)
    if pooled == 0.0:
        return 0.0 if base_mean == other_mean else float("inf")
    return abs(base_mean - other_mean) / pooled


def build_feature_drift_rows(dataset_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    train_rows = [row for row in dataset_rows if str(row.get("split")) == "train"]
    validation_rows = [row for row in dataset_rows if str(row.get("split")) == "validation"]
    validation_maps: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in validation_rows:
        validation_maps[str(row.get("map_name"))].append(row)

    comparisons: list[tuple[str, list[dict[str, Any]]]] = [("validation_all", validation_rows)]
    comparisons.extend((f"validation_map:{map_name}", rows) for map_name, rows in sorted(validation_maps.items()))

    output: list[dict[str, Any]] = []
    for feature_name in feature_names_from_rows(dataset_rows):
        train_values = values_for_feature(train_rows, feature_name)
        train_summary = summarize_values(train_values)
        for comparison, rows in comparisons:
            other_values = values_for_feature(rows, feature_name)
            other_summary = summarize_values(other_values)
            output.append(
                {
                    "feature": feature_name,
                    "comparison": comparison,
                    "train_n": len(train_values),
                    "other_n": len(other_values),
                    "train_mean": train_summary["mean"],
                    "other_mean": other_summary["mean"],
                    "train_std": train_summary["std"],
                    "other_std": other_summary["std"],
                    "standardized_mean_diff": standardized_mean_difference(train_values, other_values),
                    "train_q10": train_summary["q10"],
                    "other_q10": other_summary["q10"],
                    "train_q50": train_summary["q50"],
                    "other_q50": other_summary["q50"],
                    "train_q90": train_summary["q90"],
                    "other_q90": other_summary["q90"],
                }
            )
    return output


def basic_metrics(rows: list[dict[str, str]]) -> dict[str, Any]:
    if not rows:
        return {
            "sample_count": 0,
            "top1": None,
            "top3": None,
            "family_top1": None,
            "harmful_precision": None,
            "harmful_recall": None,
            "mean_delta": None,
        }
    top1 = [safe_int(row["top1_correct"]) for row in rows]
    top3 = [safe_int(row["top3_correct"]) for row in rows]
    family = [
        int(family_for_rule(str(row["target_rule"])) == family_for_rule(str(row["predicted_rule"])))
        for row in rows
    ]
    safety = binary_metrics(
        [safe_int(row["harmful_update"]) for row in rows],
        [safe_int(row["harmful_prediction"]) for row in rows],
    )
    return {
        "sample_count": len(rows),
        "top1": sum(top1) / len(top1),
        "top3": sum(top3) / len(top3),
        "family_top1": sum(family) / len(family),
        "harmful_precision": safety["precision"],
        "harmful_recall": safety["recall"],
        "mean_delta": mean([safe_float(row["predicted_rule_delta_ratio_vs_additive"]) for row in rows]),
    }


def split_eval_rows(eval_rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in eval_rows:
        grouped[str(row["split"])].append(row)
    return grouped


def best_safety_threshold(
    sweep_rows: list[dict[str, Any]],
    *,
    group_type: str,
    group_value: str,
    min_recall: float = 0.80,
    min_precision: float = 0.30,
) -> dict[str, Any] | None:
    candidates = [
        row
        for row in sweep_rows
        if row["group_type"] == group_type
        and row["group_value"] == group_value
        and safe_float(row["recall"]) >= min_recall
        and safe_float(row["precision"]) >= min_precision
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda row: (
            safe_float(row.get("mean_delta_after_gate")),
            -safe_float(row.get("fallback_rate")),
            safe_float(row.get("threshold")),
        ),
    )


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def top_validation_confusions(confusion_rows: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    return [
        row
        for row in confusion_rows
        if row["group_type"] == "split"
        and row["group_value"] == "validation"
        and not int(row["correct_rule"])
    ][:limit]


def top_feature_drift(feature_drift_rows: list[dict[str, Any]], comparison: str, limit: int = 12) -> list[dict[str, Any]]:
    rows = [row for row in feature_drift_rows if row["comparison"] == comparison]
    return sorted(
        rows,
        key=lambda row: safe_float(row.get("standardized_mean_diff"), default=-1.0),
        reverse=True,
    )[:limit]


def threshold_summary_row(
    margin_rows: list[dict[str, Any]], group_type: str, group_value: str, threshold: float
) -> dict[str, Any] | None:
    for row in margin_rows:
        if (
            row["group_type"] == group_type
            and row["group_value"] == group_value
            and safe_float(row["threshold"]) == threshold
        ):
            return row
    return None


def write_report(
    report_path: Path,
    *,
    dataset_path: Path,
    probe_path: Path,
    eval_csv_path: Path,
    summary_json_path: Path,
    dataset_rows: list[dict[str, Any]],
    probe_rows: list[dict[str, Any]],
    eval_rows: list[dict[str, str]],
    margin_histogram_rows: list[dict[str, Any]],
    confusion_rows: list[dict[str, Any]],
    safety_sweep_rows: list[dict[str, Any]],
    feature_drift_rows: list[dict[str, Any]],
    output_paths: dict[str, Path],
) -> None:
    split_rows = split_eval_rows(eval_rows)
    train_metrics = basic_metrics(split_rows.get("train", []))
    validation_metrics = basic_metrics(split_rows.get("validation", []))
    all_metrics = basic_metrics(eval_rows)

    summary_json = load_optional_json(summary_json_path)
    gate_passed = summary_json.get("gate", {}).get("passed")
    validation_near_005 = threshold_summary_row(margin_histogram_rows, "split", "validation", 0.005)
    validation_near_010 = threshold_summary_row(margin_histogram_rows, "split", "validation", 0.01)
    all_near_005 = threshold_summary_row(margin_histogram_rows, "all", "all", 0.005)
    best_validation_threshold = best_safety_threshold(
        safety_sweep_rows, group_type="split", group_value="validation"
    )
    best_train_threshold = best_safety_threshold(safety_sweep_rows, group_type="split", group_value="train")
    top_confusions = top_validation_confusions(confusion_rows)
    top_drift = top_feature_drift(feature_drift_rows, "validation_all")
    validation_maps = sorted({str(row["map_name"]) for row in eval_rows if str(row["split"]) == "validation"})

    lines: list[str] = [
        "# Phase4F LAUR Failure Diagnostics",
        "",
        f"Date: {date.today().isoformat()}",
        "",
        "## Scope",
        "",
        "This report is a P0 diagnostic pass over the completed Phase4F full run. It does not lower the Phase4F gate, does not change labels, and does not advance the model into Phase5 learned runtime.",
        "",
        "## Inputs",
        "",
        f"- dataset: `{dataset_path.as_posix()}`",
        f"- probes: `{probe_path.as_posix()}`",
        f"- offline eval CSV: `{eval_csv_path.as_posix()}`",
        f"- offline eval summary: `{summary_json_path.as_posix()}`",
        f"- dataset rows: `{len(dataset_rows)}`",
        f"- probe rows: `{len(probe_rows)}`",
        f"- eval rows: `{len(eval_rows)}`",
        f"- eval gate script passed operationally: `{gate_passed}`",
        "",
        "## Gate Recap",
        "",
        "| split | samples | exact top1 | exact top3 | family top1 | harmful recall | harmful precision | mean predicted delta |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| train | {train_metrics['sample_count']} | {fmt_float(train_metrics['top1'])} | "
            f"{fmt_float(train_metrics['top3'])} | {fmt_float(train_metrics['family_top1'])} | "
            f"{fmt_float(train_metrics['harmful_recall'])} | {fmt_float(train_metrics['harmful_precision'])} | "
            f"{fmt_float(train_metrics['mean_delta'])} |"
        ),
        (
            f"| validation | {validation_metrics['sample_count']} | {fmt_float(validation_metrics['top1'])} | "
            f"{fmt_float(validation_metrics['top3'])} | {fmt_float(validation_metrics['family_top1'])} | "
            f"{fmt_float(validation_metrics['harmful_recall'])} | {fmt_float(validation_metrics['harmful_precision'])} | "
            f"{fmt_float(validation_metrics['mean_delta'])} |"
        ),
        (
            f"| all | {all_metrics['sample_count']} | {fmt_float(all_metrics['top1'])} | "
            f"{fmt_float(all_metrics['top3'])} | {fmt_float(all_metrics['family_top1'])} | "
            f"{fmt_float(all_metrics['harmful_recall'])} | {fmt_float(all_metrics['harmful_precision'])} | "
            f"{fmt_float(all_metrics['mean_delta'])} |"
        ),
        "",
        "Family top1 collapses `block_*`, `wait_*`, `decay_*`, `commit_*`, and additive/neutral variants. It is diagnostic only; the Phase4F gate still uses exact rule top1/top3.",
        "",
        "## Label Margins",
        "",
    ]
    if validation_near_005:
        lines.extend(
            [
                (
                    f"- Validation checkpoints with best-vs-second probe margin <= 0.005: "
                    f"`{validation_near_005['near_tie_count']}` / `{validation_near_005['sample_count']}` "
                    f"({fmt_float(safe_float(validation_near_005['near_tie_rate']) * 100.0, 2)}%)."
                ),
            ]
        )
    if validation_near_010:
        lines.append(
            (
                f"- Validation checkpoints with margin <= 0.010: "
                f"`{validation_near_010['near_tie_count']}` / `{validation_near_010['sample_count']}` "
                f"({fmt_float(safe_float(validation_near_010['near_tie_rate']) * 100.0, 2)}%)."
            )
        )
    if all_near_005:
        lines.append(
            (
                f"- All checkpoints with margin <= 0.005: `{all_near_005['near_tie_count']}` / "
                f"`{all_near_005['sample_count']}` "
                f"({fmt_float(safe_float(all_near_005['near_tie_rate']) * 100.0, 2)}%)."
            )
        )
    lines.extend(
        [
            "- Near ties make hard best-rule classification brittle: a top1 miss can still be a near-equivalent update by measured short-probe delta.",
            "",
            "## Validation Confusions",
            "",
            "| target | predicted | target family | predicted family | count |",
            "|---|---|---|---|---:|",
        ]
    )
    for row in top_confusions:
        lines.append(
            f"| {row['target_rule']} | {row['predicted_rule']} | {row['target_family']} | {row['predicted_family']} | {row['count']} |"
        )
    lines.extend(
        [
            "",
            "The largest failures remain concentrated around neutral/additive semantics, block-heavy predictions, and wait-vs-block confusion on held-out maps.",
            "",
            "## Safety Threshold Sweep",
            "",
            "The current offline eval uses threshold `0.50`. The sweep below is diagnostic only; any deployable threshold must be chosen on train/calibration data and then re-evaluated.",
            "",
        ]
    )
    if best_train_threshold:
        lines.append(
            (
                f"- Train-calibrated candidate meeting recall >= 0.80 and precision >= 0.30: "
                f"threshold `{fmt_float(safe_float(best_train_threshold['threshold']), 2)}`, "
                f"recall `{fmt_float(safe_float(best_train_threshold['recall']))}`, "
                f"precision `{fmt_float(safe_float(best_train_threshold['precision']))}`, "
                f"fallback rate `{fmt_float(safe_float(best_train_threshold['fallback_rate']))}`, "
                f"mean delta after fallback `{fmt_float(safe_float(best_train_threshold['mean_delta_after_gate']))}`."
            )
        )
    else:
        lines.append("- No train threshold in the sweep satisfies recall >= 0.80 and precision >= 0.30.")
    if best_validation_threshold:
        lines.append(
            (
                f"- Validation diagnostic candidate meeting recall >= 0.80 and precision >= 0.30: "
                f"threshold `{fmt_float(safe_float(best_validation_threshold['threshold']), 2)}`, "
                f"recall `{fmt_float(safe_float(best_validation_threshold['recall']))}`, "
                f"precision `{fmt_float(safe_float(best_validation_threshold['precision']))}`, "
                f"fallback rate `{fmt_float(safe_float(best_validation_threshold['fallback_rate']))}`, "
                f"mean delta after fallback `{fmt_float(safe_float(best_validation_threshold['mean_delta_after_gate']))}`."
            )
        )
    else:
        lines.append("- No validation threshold in the sweep satisfies recall >= 0.80 and precision >= 0.30.")
    lines.extend(
        [
            "",
            "## Feature Drift",
            "",
            "| feature | standardized mean diff | train mean | validation mean |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in top_drift:
        lines.append(
            (
                f"| {row['feature']} | {fmt_float(safe_float(row['standardized_mean_diff']))} | "
                f"{fmt_float(safe_float(row['train_mean']))} | {fmt_float(safe_float(row['other_mean']))} |"
            )
        )
    lines.extend(
        [
            "",
            f"Validation maps covered in drift comparisons: `{', '.join(validation_maps)}`.",
            "",
            "## Generated Tables",
            "",
        ]
    )
    for label, path in output_paths.items():
        lines.append(f"- {label}: `{path.as_posix()}`")
    lines.extend(
        [
            "",
            "## Next Repair Order",
            "",
            "1. Preserve the current exact-rule gate, but add diagnostics for collapsed additive/neutral and rule-family accuracy so we can tell semantic confusion from total failure.",
            "2. Try safety calibration next: lower or calibrate the harmful threshold on train/calibration to recover recall, then measure fallback rate and mean predicted delta.",
            "3. If exact rule top1/top3 remains poor, move to margin-aware labels or a rule-aware scorer that ranks `(checkpoint, update_rule)` candidates instead of predicting one hard class from checkpoint features alone.",
            "4. Keep Phase5 learned runtime blocked until the exact validation top1/top3 and harmful recall gates pass without using validation to tune final thresholds.",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--probes", type=Path, default=DEFAULT_PROBES)
    parser.add_argument("--eval-csv", type=Path, default=DEFAULT_EVAL_CSV)
    parser.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    dataset_path = resolve_path(args.dataset, root)
    probe_path = resolve_path(args.probes, root)
    eval_csv_path = resolve_path(args.eval_csv, root)
    summary_json_path = resolve_path(args.summary_json, root)
    output_dir = resolve_path(args.output_dir, root)
    report_path = resolve_path(args.report, root)

    dataset_rows = read_jsonl(dataset_path)
    probe_rows = read_jsonl(probe_path)
    eval_rows = read_csv_dicts(eval_csv_path)

    probe_rows_by_checkpoint = group_probe_rows(probe_rows)
    margin_details = build_margin_details(dataset_rows, probe_rows_by_checkpoint)
    margin_histogram = build_margin_histogram(margin_details)
    confusion_rows = build_confusion_rows(eval_rows)
    safety_sweep_rows = build_safety_sweep_rows(eval_rows)
    feature_drift_rows = build_feature_drift_rows(dataset_rows)

    margin_detail_path = output_dir / "phase4f_laur_label_margin_details.csv"
    margin_histogram_path = output_dir / "phase4f_laur_label_margin_histogram.csv"
    confusion_path = output_dir / "phase4f_laur_per_map_confusion.csv"
    safety_path = output_dir / "phase4f_laur_safety_threshold_sweep.csv"
    feature_drift_path = output_dir / "phase4f_laur_feature_drift.csv"

    margin_detail_fields = [
        "split",
        "map_name",
        "agents",
        "seed",
        "iteration",
        "checkpoint_id",
        "target_rule",
        "target_best_rule_id",
        "delta_best_rule_id",
        "second_delta_rule_id",
        "candidate_count",
        "harmful_candidate_count",
        "best_delta_ratio",
        "second_delta_ratio",
        "best_minus_second_margin",
        "best_minus_additive_margin",
        "best_minus_neutral_threshold",
        "label_delta_ratio_best",
        "label_confidence",
        "neutral",
    ]
    for threshold in MARGIN_THRESHOLDS:
        suffix = str(threshold).replace(".", "_")
        margin_detail_fields.extend([f"within_{suffix}_count", f"margin_le_{suffix}"])

    write_csv(margin_detail_path, margin_details, margin_detail_fields)
    write_csv(
        margin_histogram_path,
        margin_histogram,
        [
            "group_type",
            "group_value",
            "threshold",
            "sample_count",
            "near_tie_count",
            "near_tie_rate",
            "neutral_count",
            "mean_best_minus_second_margin",
            "median_best_minus_second_margin",
            "mean_best_minus_neutral_threshold",
        ],
    )
    write_csv(
        confusion_path,
        confusion_rows,
        [
            "group_type",
            "group_value",
            "target_rule",
            "predicted_rule",
            "target_family",
            "predicted_family",
            "correct_rule",
            "correct_family",
            "count",
        ],
    )
    write_csv(
        safety_path,
        safety_sweep_rows,
        [
            "group_type",
            "group_value",
            "threshold",
            "sample_count",
            "harmful_count",
            "predicted_harmful_count",
            "tp",
            "fp",
            "fn",
            "precision",
            "recall",
            "f1",
            "fallback_rate",
            "mean_delta_no_gate",
            "mean_delta_after_gate",
            "mean_delta_loss_from_gate",
        ],
    )
    write_csv(
        feature_drift_path,
        feature_drift_rows,
        [
            "feature",
            "comparison",
            "train_n",
            "other_n",
            "train_mean",
            "other_mean",
            "train_std",
            "other_std",
            "standardized_mean_diff",
            "train_q10",
            "other_q10",
            "train_q50",
            "other_q50",
            "train_q90",
            "other_q90",
        ],
    )

    output_paths = {
        "label margin details": margin_detail_path.relative_to(root),
        "label margin histogram": margin_histogram_path.relative_to(root),
        "per-map confusion": confusion_path.relative_to(root),
        "safety threshold sweep": safety_path.relative_to(root),
        "feature drift": feature_drift_path.relative_to(root),
    }
    write_report(
        report_path,
        dataset_path=dataset_path.relative_to(root),
        probe_path=probe_path.relative_to(root),
        eval_csv_path=eval_csv_path.relative_to(root),
        summary_json_path=summary_json_path.relative_to(root),
        dataset_rows=dataset_rows,
        probe_rows=probe_rows,
        eval_rows=eval_rows,
        margin_histogram_rows=margin_histogram,
        confusion_rows=confusion_rows,
        safety_sweep_rows=safety_sweep_rows,
        feature_drift_rows=feature_drift_rows,
        output_paths=output_paths,
    )
    print(f"wrote {report_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

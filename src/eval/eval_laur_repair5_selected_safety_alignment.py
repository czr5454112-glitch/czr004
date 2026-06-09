"""Selected-rule safety alignment diagnostic for Repair5D LAUR composites."""

from __future__ import annotations

import argparse
import ast
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

from czr004_teacher.stable_attention_tokens_laur import EXECUTABLE_RULE_IDS, rule_family  # noqa: E402


DEFAULT_INPUT_CSV = "outputs/tables/phase4f_repair5c_composite_inference.csv"
DEFAULT_CALIBRATION_JSON = "outputs/reports/phase4f_repair5_per_rule_safety_calibration.json"
DEFAULT_SUMMARY_JSON = "outputs/reports/phase4f_repair5_selected_safety_alignment.json"
DEFAULT_REPORT = "outputs/reports/phase4f_repair5_selected_safety_alignment.md"


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


def parse_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    text = str(value or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            return []
    return parsed if isinstance(parsed, list) else []


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def binary_metrics(labels: list[int], predictions: list[int]) -> dict[str, Any]:
    tp = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 1)
    fp = sum(1 for label, pred in zip(labels, predictions) if label == 0 and pred == 1)
    tn = sum(1 for label, pred in zip(labels, predictions) if label == 0 and pred == 0)
    fn = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 0)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "precision": precision, "recall": recall}


def load_rows(path: Path, *, mode_filter: str | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if mode_filter and str(row.get("mode")) != mode_filter:
                continue
            rows.append(row)
    return rows


def load_calibration(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def threshold_for(rule: str, mode: str, calibration: dict[str, Any], default: float) -> float | None:
    if mode == "oracle" or "oracle_safety" in mode:
        return None
    if "family" in mode:
        by_family = calibration.get("threshold_by_family") or {}
        return float(by_family.get(rule_family(rule), default))
    by_rule = calibration.get("threshold_by_rule") or {}
    if by_rule:
        return float(by_rule.get(rule, default))
    global_threshold = calibration.get("threshold")
    if global_threshold is None and isinstance(calibration.get("global_threshold"), dict):
        global_threshold = calibration["global_threshold"].get("threshold")
    return float(global_threshold if global_threshold is not None else default)


def summarize_alignment(
    rows: list[dict[str, Any]],
    *,
    calibration: dict[str, Any],
    default_threshold: float,
) -> dict[str, Any]:
    by_mode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_mode[str(row.get("mode", ""))].append(row)

    summaries: dict[str, Any] = {}
    for mode, mode_rows in sorted(by_mode.items()):
        all_labels: list[int] = []
        all_predictions: list[int] = []
        selected_labels: list[int] = []
        selected_predictions: list[int] = []
        selected_false_negative_by_rule: Counter[str] = Counter()
        selected_false_positive_by_rule: Counter[str] = Counter()
        selected_false_negative_by_family: Counter[str] = Counter()
        selected_false_positive_by_family: Counter[str] = Counter()
        selected_false_negative_by_map: Counter[str] = Counter()
        selected_false_positive_by_map: Counter[str] = Counter()
        threshold_used: Counter[str] = Counter()
        selected_harmful_count = 0
        selected_safe_but_masked_count = 0
        for row in mode_rows:
            labels = [1 if parse_bool(value) else 0 for value in parse_list(row.get("harmful_labels"))]
            predictions = [1 if parse_bool(value) else 0 for value in parse_list(row.get("harmful_predictions"))]
            if len(labels) != len(EXECUTABLE_RULE_IDS) or len(predictions) != len(EXECUTABLE_RULE_IDS):
                continue
            all_labels.extend(labels)
            all_predictions.extend(predictions)
            selected_rule = str(row.get("selected_rule", ""))
            if selected_rule not in EXECUTABLE_RULE_IDS:
                continue
            index = EXECUTABLE_RULE_IDS.index(selected_rule)
            label = int(labels[index])
            pred = int(predictions[index])
            selected_labels.append(label)
            selected_predictions.append(pred)
            threshold = threshold_for(selected_rule, mode, calibration, default_threshold)
            threshold_used[f"{selected_rule}:{threshold if threshold is not None else 'oracle'}"] += 1
            if label:
                selected_harmful_count += 1
            if label and not pred:
                selected_false_negative_by_rule[selected_rule] += 1
                selected_false_negative_by_family[rule_family(selected_rule)] += 1
                selected_false_negative_by_map[str(row.get("map_name", ""))] += 1
            if not label and pred:
                selected_safe_but_masked_count += 1
                selected_false_positive_by_rule[selected_rule] += 1
                selected_false_positive_by_family[rule_family(selected_rule)] += 1
                selected_false_positive_by_map[str(row.get("map_name", ""))] += 1
        summaries[mode] = {
            "sample_count": len(mode_rows),
            "all_rule_safety": binary_metrics(all_labels, all_predictions),
            "selected_rule_safety": binary_metrics(selected_labels, selected_predictions),
            "selected_harmful_rate": selected_harmful_count / len(selected_labels) if selected_labels else 0.0,
            "selected_safe_but_masked_rate": selected_safe_but_masked_count / len(selected_labels) if selected_labels else 0.0,
            "selected_harmful_false_negative_by_rule": dict(sorted(selected_false_negative_by_rule.items())),
            "selected_safe_false_positive_by_rule": dict(sorted(selected_false_positive_by_rule.items())),
            "selected_harmful_false_negative_by_family": dict(sorted(selected_false_negative_by_family.items())),
            "selected_safe_false_positive_by_family": dict(sorted(selected_false_positive_by_family.items())),
            "selected_harmful_false_negative_by_map": dict(sorted(selected_false_negative_by_map.items())),
            "selected_safe_false_positive_by_map": dict(sorted(selected_false_positive_by_map.items())),
            "selected_threshold_usage": dict(sorted(threshold_used.items())),
        }
    return summaries


def write_report(path: Path, *, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair5 Selected Safety Alignment\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("This diagnostic compares all-rule harmful recall/precision with selected-rule behavior. It does not lower the final safety gate.\n\n")
        handle.write("| mode | samples | all recall | all precision | selected harmful | selected FN | selected FP |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|\n")
        for mode, values in summary.get("metrics_by_mode", {}).items():
            all_rule = values["all_rule_safety"]
            selected = values["selected_rule_safety"]
            handle.write(
                f"| {mode} | {values['sample_count']} | {all_rule['recall']:.6f} | "
                f"{all_rule['precision']:.6f} | {values['selected_harmful_rate']:.6f} | "
                f"{selected['fn']} | {selected['fp']} |\n"
            )
        handle.write("\n## Boundary\n\nPhase5.5 and Phase6 remain forbidden.\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", type=Path, default=Path(DEFAULT_INPUT_CSV))
    parser.add_argument("--calibration-json", type=Path, default=Path(DEFAULT_CALIBRATION_JSON))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--mode")
    parser.add_argument("--default-threshold", type=float, default=0.35)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    input_csv = resolve_path(args.input_csv, root)
    calibration_json = resolve_path(args.calibration_json, root)
    summary_json = resolve_path(args.summary_json, root)
    report = resolve_path(args.report, root)
    if None in (input_csv, summary_json, report):
        raise ValueError("required paths could not be resolved")
    assert input_csv and summary_json and report
    rows = load_rows(input_csv, mode_filter=args.mode)
    metrics = summarize_alignment(rows, calibration=load_calibration(calibration_json), default_threshold=float(args.default_threshold))
    summary = {
        "schema_version": "phase4f_repair5_selected_safety_alignment_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "input_csv": str(input_csv),
        "calibration_json": str(calibration_json) if calibration_json else None,
        "metrics_by_mode": metrics,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary=summary)
    print(json.dumps({"summary_json": str(summary_json), "report": str(report)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

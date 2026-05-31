"""Repair5C composite inference diagnostics for attention-native LAUR.

This script recombines existing model outputs without retraining. It is
diagnostic-only: a good result here can justify reranking or preflight work,
but it never permits Phase5.5 runtime promotion.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.stable_attention_dataset_laur import read_jsonl  # noqa: E402
from czr004_teacher.stable_attention_tokens_laur import EXECUTABLE_RULE_IDS, rule_family  # noqa: E402


DEFAULT_DATASET = (
    "artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace_hightoken/update_labels/"
    "phase4_laur_attention_native_expand5000_rawtrace_hightoken_dataset.jsonl.zst"
)
DEFAULT_RANKING_CSV = (
    "outputs/tables/"
    "phase4f_repair5_expand5000_postnext_hightoken_attn_mlp_head_rank_recall_perrule_eval_seed61.csv"
)
DEFAULT_CALIBRATION_JSON = "outputs/reports/phase4f_repair5_per_rule_safety_calibration.json"
DEFAULT_SUMMARY_JSON = "outputs/reports/phase4f_repair5c_composite_inference_summary.json"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase4f_repair5c_composite_inference.csv"
DEFAULT_REPORT = "outputs/reports/phase4f_repair5c_composite_inference.md"

COMPOSITE_MODES = [
    "top3_per_rule_safety_utility",
    "anti_decision_top3_per_rule_safety",
    "top3_anti_margin_per_family_safety",
    "oracle_decision_learned_rerank",
    "learned_decision_oracle_safety",
]


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


def finite(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number or number in {float("inf"), float("-inf")}:
        return default
    return number


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def topk_indices(values: list[float], k: int) -> list[int]:
    return sorted(range(len(values)), key=lambda index: values[index], reverse=True)[: max(0, int(k))]


def binary_metrics(labels: list[int], predictions: list[int]) -> dict[str, float]:
    tp = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 1)
    fp = sum(1 for label, pred in zip(labels, predictions) if label == 0 and pred == 1)
    fn = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 0)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def load_eval_rows(path: Path, *, split: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if split and str(row.get("split")) != split:
                continue
            checkpoint_id = str(row.get("checkpoint_id", ""))
            if checkpoint_id:
                rows[checkpoint_id] = row
    return rows


def load_label_rows(path: Path, *, split: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        if split and str(row.get("split")) != split:
            continue
        if row.get("rule_ids") != EXECUTABLE_RULE_IDS:
            continue
        checkpoint_id = str(row.get("checkpoint_id", ""))
        if checkpoint_id:
            rows[checkpoint_id] = row
    return rows


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def thresholds_from_calibration(
    calibration: dict[str, Any],
    *,
    mode: str,
    default_threshold: float,
) -> list[float]:
    if mode == "oracle":
        return [-1.0] * len(EXECUTABLE_RULE_IDS)
    if mode == "per_rule":
        by_rule = calibration.get("threshold_by_rule") or {}
        if not by_rule and isinstance(calibration.get("safety_calibration"), dict):
            by_rule = calibration["safety_calibration"].get("threshold_by_rule") or {}
        return [finite(by_rule.get(rule), default_threshold) for rule in EXECUTABLE_RULE_IDS]
    if mode == "per_family":
        by_family = calibration.get("threshold_by_family") or {}
        if not by_family and isinstance(calibration.get("safety_calibration"), dict):
            by_family = calibration["safety_calibration"].get("threshold_by_family") or {}
        return [finite(by_family.get(rule_family(rule)), default_threshold) for rule in EXECUTABLE_RULE_IDS]
    global_value = calibration.get("threshold")
    if global_value is None and isinstance(calibration.get("global_threshold"), dict):
        global_value = calibration["global_threshold"].get("threshold")
    if global_value is None and isinstance(calibration.get("global_calibration"), dict):
        global_value = calibration["global_calibration"].get("threshold")
    return [finite(global_value, default_threshold)] * len(EXECUTABLE_RULE_IDS)


def safety_predictions(
    harmful_probs: list[float],
    harmful_labels: list[int],
    *,
    thresholds: list[float],
    oracle: bool = False,
) -> list[int]:
    if oracle:
        return [int(value) for value in harmful_labels]
    return [
        1 if finite(probability) >= float(thresholds[index]) else 0
        for index, probability in enumerate(harmful_probs)
    ]


def _best_by(values: list[float], candidates: list[int]) -> int | None:
    if not candidates:
        return None
    return max(candidates, key=lambda index: (float(values[index]), -index))


def _oracle_safe_indices(harmful_labels: list[int]) -> list[int]:
    additive = EXECUTABLE_RULE_IDS.index("additive_ltm")
    return [
        index
        for index, label in enumerate(harmful_labels)
        if index != additive and int(label) == 0
    ]


def select_composite(
    *,
    mode: str,
    label: dict[str, Any],
    ranking_row: dict[str, Any],
    safety_row: dict[str, Any],
    anti_row: dict[str, Any],
    thresholds: list[float],
    top_k: int,
    opportunity_threshold: float,
    defer_threshold: float,
) -> dict[str, Any]:
    additive = EXECUTABLE_RULE_IDS.index("additive_ltm")
    scores = [finite(value) for value in parse_list(ranking_row.get("rule_scores"))]
    safety_probs = [finite(value) for value in parse_list(safety_row.get("harmful_probs"))]
    anti_opportunity = finite(anti_row.get("opportunity_prob"))
    anti_defer = finite(anti_row.get("defer_prob"))
    harmful_labels = [1 if value else 0 for value in label["probe_harmful_vector"]]
    utilities = [finite(value) for value in label["risk_adjusted_utility_vector"]]
    if len(scores) != len(EXECUTABLE_RULE_IDS):
        scores = [0.0] * len(EXECUTABLE_RULE_IDS)
    if len(safety_probs) != len(EXECUTABLE_RULE_IDS):
        safety_probs = [0.0] * len(EXECUTABLE_RULE_IDS)
    ranked = topk_indices(scores, len(EXECUTABLE_RULE_IDS))
    top_candidates = ranked[:top_k]

    if mode == "learned_decision_oracle_safety":
        unsafe = [bool(value) for value in harmful_labels]
        safety_mode = "oracle"
    elif mode == "oracle_decision_learned_rerank":
        unsafe = [
            finite(safety_probs[index]) >= float(thresholds[index])
            for index in range(len(EXECUTABLE_RULE_IDS))
        ]
        safety_mode = "learned"
    else:
        unsafe = [
            finite(safety_probs[index]) >= float(thresholds[index])
            for index in range(len(EXECUTABLE_RULE_IDS))
        ]
        safety_mode = "learned"

    safe_top = [index for index in top_candidates if index != additive and not unsafe[index]]
    oracle_safe = _oracle_safe_indices(harmful_labels)
    oracle_best = _best_by(utilities, oracle_safe)
    selected = additive
    selected_decision = "defer_ltm"
    reason = "mode_default_defer"

    if mode == "top3_per_rule_safety_utility":
        best = _best_by(utilities, safe_top)
        if best is not None:
            selected = int(best)
            selected_decision = "use_nonadditive"
            reason = "topk_safe_utility"
        else:
            reason = "no_safe_topk_candidate"
    elif mode == "anti_decision_top3_per_rule_safety":
        if anti_opportunity < opportunity_threshold:
            reason = "anti_low_opportunity"
        elif anti_defer >= defer_threshold:
            reason = "anti_defer"
        else:
            best = _best_by(scores, safe_top)
            if best is not None:
                selected = int(best)
                selected_decision = "use_nonadditive"
                reason = "anti_topk_safe_rank"
            else:
                reason = "anti_no_safe_topk_candidate"
    elif mode == "top3_anti_margin_per_family_safety":
        if anti_opportunity - anti_defer <= 0.0:
            reason = "anti_margin_nonpositive"
        else:
            adjusted = [
                float(scores[index]) + 0.05 * float(anti_opportunity - anti_defer)
                for index in range(len(scores))
            ]
            best = _best_by(adjusted, safe_top)
            if best is not None:
                selected = int(best)
                selected_decision = "use_nonadditive"
                reason = "family_safe_anti_margin_rank"
            else:
                reason = "family_safe_no_safe_topk_candidate"
    elif mode == "oracle_decision_learned_rerank":
        if str(label.get("decision_target")) != "use_nonadditive":
            reason = "oracle_decision_defer"
        else:
            best = _best_by(scores, safe_top)
            if best is not None:
                selected = int(best)
                selected_decision = "use_nonadditive"
                reason = "oracle_decision_learned_rank"
            else:
                reason = "oracle_decision_no_safe_topk_candidate"
    elif mode == "learned_decision_oracle_safety":
        if anti_opportunity < opportunity_threshold:
            reason = "learned_decision_low_opportunity"
        elif anti_defer >= defer_threshold:
            reason = "learned_decision_defer"
        else:
            best = _best_by(scores, safe_top)
            if best is not None:
                selected = int(best)
                selected_decision = "use_nonadditive"
                reason = "oracle_safety_learned_rank"
            else:
                reason = "oracle_safety_no_safe_topk_candidate"
    else:
        raise ValueError(f"unknown composite mode {mode}")

    return {
        "selected_index": selected,
        "selected_rule": EXECUTABLE_RULE_IDS[selected],
        "selected_decision": selected_decision,
        "fallback_reason": reason,
        "ranked_indices": ranked,
        "top_candidate_indices": top_candidates,
        "oracle_best_safe_index": oracle_best,
        "safety_mode": safety_mode,
        "safety_predictions": safety_predictions(
            safety_probs,
            harmful_labels,
            thresholds=thresholds,
            oracle=mode == "learned_decision_oracle_safety",
        ),
    }


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {
            "sample_count": 0,
            "rule_top1": 0.0,
            "rule_top3": 0.0,
            "safe_utility_top1": 0.0,
            "safe_utility_top3": 0.0,
            "utility_regret_to_oracle": 0.0,
            "selected_vs_additive_delta": 0.0,
            "harmful_precision": 0.0,
            "harmful_recall": 0.0,
            "high_margin_capture": 0.0,
            "avoidable_defer_additive": 0.0,
        }
    labels: list[int] = []
    predictions: list[int] = []
    for record in records:
        labels.extend(int(value) for value in parse_list(record["harmful_labels"]))
        predictions.extend(int(value) for value in parse_list(record["harmful_predictions"]))
    safety = binary_metrics(labels, predictions)
    target_records = [row for row in records if row["decision_target"] == "use_nonadditive"]
    high_margin = [row for row in records if parse_bool(row["has_high_margin_nonadditive_opportunity"])]
    captured = [
        row
        for row in high_margin
        if row["selected_decision"] == "use_nonadditive"
        and row["selected_rule"] != "additive_ltm"
        and not parse_bool(row["selected_rule_harmful"])
        and finite(row["selected_vs_additive_delta"]) >= finite(row["opportunity_margin"])
    ]
    escaped = [
        row
        for row in high_margin
        if row["selected_decision"] == "defer_ltm" or row["selected_rule"] == "additive_ltm"
    ]
    return {
        "sample_count": len(records),
        "target_nonadditive_count": len(target_records),
        "rule_top1": (
            sum(1 for row in target_records if parse_bool(row["rule_top1"])) / len(target_records)
            if target_records
            else 0.0
        ),
        "rule_top3": (
            sum(1 for row in target_records if parse_bool(row["rule_top3"])) / len(target_records)
            if target_records
            else 0.0
        ),
        "safe_utility_top1": sum(1 for row in records if parse_bool(row["safe_utility_top1"])) / len(records),
        "safe_utility_top3": sum(1 for row in records if parse_bool(row["safe_utility_top3"])) / len(records),
        "utility_regret_to_oracle": sum(finite(row["utility_regret_to_oracle"]) for row in records) / len(records),
        "selected_vs_additive_delta": sum(finite(row["selected_vs_additive_delta"]) for row in records) / len(records),
        "selected_vs_additive_utility": sum(finite(row["selected_vs_additive_utility"]) for row in records) / len(records),
        "harmful_precision": safety["precision"],
        "harmful_recall": safety["recall"],
        "harmful_f1": safety["f1"],
        "selected_harmful_rate": sum(1 for row in records if parse_bool(row["selected_rule_harmful"])) / len(records),
        "high_margin_opportunity_count": len(high_margin),
        "high_margin_capture": len(captured) / len(high_margin) if high_margin else 0.0,
        "avoidable_defer_additive": len(escaped) / len(high_margin) if high_margin else 1.0,
        "global_additive_or_defer_rate": (
            sum(
                1
                for row in records
                if row["selected_decision"] == "defer_ltm" or row["selected_rule"] == "additive_ltm"
            )
            / len(records)
        ),
        "selected_rule_distribution": dict(sorted(Counter(str(row["selected_rule"]) for row in records).items())),
        "decision_distribution": dict(sorted(Counter(str(row["selected_decision"]) for row in records).items())),
    }


def composite_records(
    *,
    labels: dict[str, dict[str, Any]],
    ranking_rows: dict[str, dict[str, Any]],
    safety_rows: dict[str, dict[str, Any]],
    anti_rows: dict[str, dict[str, Any]],
    calibration: dict[str, Any],
    modes: list[str],
    top_k: int,
    default_threshold: float,
    opportunity_threshold: float,
    defer_threshold: float,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    additive = EXECUTABLE_RULE_IDS.index("additive_ltm")
    thresholds_by_mode = {
        "global": thresholds_from_calibration(
            calibration,
            mode="global",
            default_threshold=default_threshold,
        ),
        "per_rule": thresholds_from_calibration(
            calibration,
            mode="per_rule",
            default_threshold=default_threshold,
        ),
        "per_family": thresholds_from_calibration(
            calibration,
            mode="per_family",
            default_threshold=default_threshold,
        ),
        "oracle": thresholds_from_calibration(
            calibration,
            mode="oracle",
            default_threshold=default_threshold,
        ),
    }
    all_records: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, Any]] = {}
    common_ids = sorted(set(labels) & set(ranking_rows) & set(safety_rows) & set(anti_rows))
    for mode in modes:
        if mode == "top3_anti_margin_per_family_safety":
            thresholds = thresholds_by_mode["per_family"]
        elif mode == "learned_decision_oracle_safety":
            thresholds = thresholds_by_mode["oracle"]
        else:
            thresholds = thresholds_by_mode["per_rule"]
        mode_records: list[dict[str, Any]] = []
        for checkpoint_id in common_ids:
            label = labels[checkpoint_id]
            selection = select_composite(
                mode=mode,
                label=label,
                ranking_row=ranking_rows[checkpoint_id],
                safety_row=safety_rows[checkpoint_id],
                anti_row=anti_rows[checkpoint_id],
                thresholds=thresholds,
                top_k=top_k,
                opportunity_threshold=opportunity_threshold,
                defer_threshold=defer_threshold,
            )
            selected = int(selection["selected_index"])
            target_index = int(label["target"]["target_rule_index"])
            deltas = [finite(value) for value in label["probe_delta_vector"]]
            utilities = [finite(value) for value in label["risk_adjusted_utility_vector"]]
            harmful_labels = [1 if value else 0 for value in label["probe_harmful_vector"]]
            oracle_safe = _oracle_safe_indices(harmful_labels)
            oracle_best = selection["oracle_best_safe_index"]
            oracle_top3 = topk_indices(
                [utilities[index] if index in oracle_safe else -1.0e9 for index in range(len(utilities))],
                min(3, len(utilities)),
            )
            record = {
                "mode": mode,
                "split": label["split"],
                "checkpoint_id": checkpoint_id,
                "run_id": label["run_id"],
                "map_name": label["map_name"],
                "agents": label["agents"],
                "seed": label["seed"],
                "iteration": label["iteration"],
                "decision_target": label["decision_target"],
                "target_rule": label["target_rule"],
                "selected_decision": selection["selected_decision"],
                "selected_rule": selection["selected_rule"],
                "fallback_reason": selection["fallback_reason"],
                "rule_top1": bool(label["decision_target"] == "use_nonadditive" and selected == target_index),
                "rule_top3": bool(
                    label["decision_target"] == "use_nonadditive"
                    and target_index in selection["top_candidate_indices"]
                ),
                "safe_utility_top1": bool(oracle_best is not None and selected == int(oracle_best)),
                "safe_utility_top3": bool(selected in oracle_top3),
                "selected_delta": deltas[selected],
                "additive_delta": deltas[additive],
                "selected_vs_additive_delta": deltas[selected] - deltas[additive],
                "selected_utility": utilities[selected],
                "additive_utility": utilities[additive],
                "selected_vs_additive_utility": utilities[selected] - utilities[additive],
                "oracle_best_safe_rule": (
                    EXECUTABLE_RULE_IDS[int(oracle_best)] if oracle_best is not None else ""
                ),
                "oracle_best_safe_utility": utilities[int(oracle_best)] if oracle_best is not None else 0.0,
                "utility_regret_to_oracle": (
                    utilities[int(oracle_best)] - utilities[selected] if oracle_best is not None else 0.0
                ),
                "selected_rule_harmful": bool(harmful_labels[selected]),
                "has_nonadditive_opportunity": bool(label["has_nonadditive_opportunity"]),
                "has_high_margin_nonadditive_opportunity": bool(
                    label["has_high_margin_nonadditive_opportunity"]
                ),
                "opportunity_margin": finite(label.get("audit", {}).get("label_params", {}).get("opportunity_margin"), 0.010),
                "top_candidate_rules": json.dumps(
                    [EXECUTABLE_RULE_IDS[index] for index in selection["top_candidate_indices"]]
                ),
                "harmful_labels": json.dumps(harmful_labels),
                "harmful_predictions": json.dumps(selection["safety_predictions"]),
                "safety_mode": selection["safety_mode"],
            }
            mode_records.append(record)
            all_records.append(record)
        summaries[mode] = summarize_records(mode_records)
    return summaries, all_records


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)


def write_report(path: Path, *, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair5C Composite Inference Diagnostic\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("## Boundary\n\n")
        handle.write(
            "This is no-retraining diagnostic evidence only. It does not permit Phase5.5 runtime "
            "promotion and does not relax any Repair5 gate.\n\n"
        )
        handle.write("## Inputs\n\n")
        for key in ("dataset", "ranking_csv", "safety_csv", "anti_csv", "calibration_json"):
            handle.write(f"- {key}: `{summary.get(key)}`\n")
        handle.write("\n## Mode Metrics\n\n")
        handle.write(
            "| mode | samples | top1 | top3 | safe utility top1 | regret | selected-vs-additive | "
            "harm recall | harm precision | high-margin capture | additive/defer |\n"
        )
        handle.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for mode, metrics in summary["metrics_by_mode"].items():
            handle.write(
                f"| {mode} | {metrics.get('sample_count')} | {metrics.get('rule_top1'):.6f} | "
                f"{metrics.get('rule_top3'):.6f} | {metrics.get('safe_utility_top1'):.6f} | "
                f"{metrics.get('utility_regret_to_oracle'):.6f} | "
                f"{metrics.get('selected_vs_additive_delta'):.6f} | "
                f"{metrics.get('harmful_recall'):.6f} | {metrics.get('harmful_precision'):.6f} | "
                f"{metrics.get('high_margin_capture'):.6f} | "
                f"{metrics.get('global_additive_or_defer_rate'):.6f} |\n"
            )
        handle.write("\n## Interpretation\n\n")
        handle.write(
            "Use this to decide whether selection composition or a second-stage reranker is worth training. "
            "If all modes stay flat, the next repair should focus on output space or representation.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path(DEFAULT_DATASET))
    parser.add_argument("--ranking-csv", type=Path, default=Path(DEFAULT_RANKING_CSV))
    parser.add_argument("--safety-csv", type=Path)
    parser.add_argument("--anti-csv", type=Path)
    parser.add_argument("--calibration-json", type=Path, default=Path(DEFAULT_CALIBRATION_JSON))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--summary-csv", type=Path, default=Path(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--mode", action="append", choices=COMPOSITE_MODES, default=[])
    parser.add_argument("--split", default="validation")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--default-threshold", type=float, default=0.35)
    parser.add_argument("--opportunity-threshold", type=float, default=0.50)
    parser.add_argument("--defer-threshold", type=float, default=0.50)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    dataset_path = resolve_path(args.dataset, root)
    ranking_csv = resolve_path(args.ranking_csv, root)
    safety_csv = resolve_path(args.safety_csv or args.ranking_csv, root)
    anti_csv = resolve_path(args.anti_csv or args.ranking_csv, root)
    calibration_json = resolve_path(args.calibration_json, root)
    summary_json = resolve_path(args.summary_json, root)
    summary_csv = resolve_path(args.summary_csv, root)
    report = resolve_path(args.report, root)
    if None in (dataset_path, ranking_csv, safety_csv, anti_csv, summary_json, summary_csv, report):
        raise ValueError("dataset/csv/output paths are required")
    assert dataset_path and ranking_csv and safety_csv and anti_csv and summary_json and summary_csv and report
    labels = load_label_rows(dataset_path, split=str(args.split))
    ranking_rows = load_eval_rows(ranking_csv, split=str(args.split))
    safety_rows = load_eval_rows(safety_csv, split=str(args.split))
    anti_rows = load_eval_rows(anti_csv, split=str(args.split))
    modes = args.mode or COMPOSITE_MODES
    metrics_by_mode, records = composite_records(
        labels=labels,
        ranking_rows=ranking_rows,
        safety_rows=safety_rows,
        anti_rows=anti_rows,
        calibration=load_json(calibration_json),
        modes=modes,
        top_k=int(args.top_k),
        default_threshold=float(args.default_threshold),
        opportunity_threshold=float(args.opportunity_threshold),
        defer_threshold=float(args.defer_threshold),
    )
    summary = {
        "schema_version": "phase4f_repair5c_composite_inference_summary_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "dataset": str(dataset_path),
        "ranking_csv": str(ranking_csv),
        "safety_csv": str(safety_csv),
        "anti_csv": str(anti_csv),
        "calibration_json": str(calibration_json) if calibration_json else None,
        "split": str(args.split),
        "top_k": int(args.top_k),
        "common_checkpoint_count": len(set(labels) & set(ranking_rows) & set(safety_rows) & set(anti_rows)),
        "metrics_by_mode": metrics_by_mode,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_csv(summary_csv, records)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary=summary)
    print(json.dumps({"summary_json": str(summary_json), "summary_csv": str(summary_csv), "report": str(report)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

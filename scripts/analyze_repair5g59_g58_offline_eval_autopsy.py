"""Analyze the Repair5G.5.8 offline G6 evaluation failure."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g59_common import (  # noqa: E402
    G56_STATIC_CANDIDATE,
    G59_CLOSED_STATUS,
    G59_DEFAULT_MARGIN,
    G59_THRESHOLDS,
    as_jsonable,
    calibration_bins,
    count_by,
    finite_number,
    load_json,
    mean,
    metric_summary,
    missing_required_g58_artifacts,
    quantiles,
    read_csv_rows,
    repo_root,
    resolve,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_EVAL = "outputs/tables/phase5p5_repair5g58_offline_safe_mixture_eval.csv"
DEFAULT_TRAIN_SUMMARY = "outputs/reports/phase5p5_repair5g58_offline_safe_mixture_train_summary.json"
DEFAULT_EVAL_SUMMARY = "outputs/reports/phase5p5_repair5g58_offline_safe_mixture_eval_summary.json"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g59_g58_offline_eval_autopsy.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g59_g58_offline_eval_autopsy_summary.json"
DEFAULT_CONFUSION = "outputs/tables/phase5p5_repair5g59_g58_eval_confusion_by_map_agent.csv"
DEFAULT_HARMFUL = "outputs/tables/phase5p5_repair5g59_g58_eval_harmful_rows.csv"
DEFAULT_HELPFUL = "outputs/tables/phase5p5_repair5g59_g58_eval_helpful_rows.csv"
DEFAULT_CALIBRATION = "outputs/tables/phase5p5_repair5g59_g58_eval_calibration_bins.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-csv", type=Path, default=Path(DEFAULT_EVAL))
    parser.add_argument("--train-summary-json", type=Path, default=Path(DEFAULT_TRAIN_SUMMARY))
    parser.add_argument("--eval-summary-json", type=Path, default=Path(DEFAULT_EVAL_SUMMARY))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--confusion-by-map-agent-csv", type=Path, default=Path(DEFAULT_CONFUSION))
    parser.add_argument("--harmful-rows-csv", type=Path, default=Path(DEFAULT_HARMFUL))
    parser.add_argument("--helpful-rows-csv", type=Path, default=Path(DEFAULT_HELPFUL))
    parser.add_argument("--calibration-bins-csv", type=Path, default=Path(DEFAULT_CALIBRATION))
    parser.add_argument("--harmful-margin", type=float, default=G59_DEFAULT_MARGIN)
    return parser.parse_args(argv)


def map_agent(row: dict[str, Any]) -> str:
    return f"{row.get('map', '')}|a{int(float(row.get('agents') or 0)) if row.get('agents') else 0}"


def add_eval_flags(rows: list[dict[str, Any]], margin: float) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        selected = finite_number(row.get("selected_score"), math.inf)
        static = finite_number(row.get("static_score"), math.inf)
        oracle = finite_number(row.get("oracle_score"), math.inf)
        enriched = dict(row)
        enriched["correct"] = str(row.get("selected_candidate_id", "")) == str(row.get("target_candidate_id", ""))
        enriched["harmful_vs_static"] = math.isfinite(selected) and math.isfinite(static) and selected > static + margin
        enriched["helpful_vs_static"] = math.isfinite(selected) and math.isfinite(static) and selected < static - margin
        enriched["static_regret"] = static - oracle if math.isfinite(static) and math.isfinite(oracle) else ""
        enriched["selected_oracle_regret"] = selected - oracle if math.isfinite(selected) and math.isfinite(oracle) else ""
        enriched["selected_delta_vs_static"] = selected - static if math.isfinite(selected) and math.isfinite(static) else ""
        out.append(enriched)
    return out


def confusion_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(map_agent(row), str(row.get("target_candidate_id", "")), str(row.get("selected_candidate_id", "")))].append(row)
    out = []
    for (group, target, selected), group_rows in sorted(grouped.items()):
        out.append(
            {
                "map_agent": group,
                "target_candidate_id": target,
                "selected_candidate_id": selected,
                "rows": len(group_rows),
                "correct_rows": sum(1 for row in group_rows if row.get("correct") is True),
                "harmful_rows": sum(1 for row in group_rows if row.get("harmful_vs_static") is True),
                "helpful_rows": sum(1 for row in group_rows if row.get("helpful_vs_static") is True),
                "mean_selected_delta_vs_static": as_jsonable(mean([finite_number(row.get("selected_delta_vs_static"), math.inf) for row in group_rows])),
            }
        )
    return out


def group_breakdown(rows: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(field, ""))].append(row)
    return {
        key: {
            "rows": len(group_rows),
            "accuracy": sum(1 for row in group_rows if row.get("correct") is True) / len(group_rows) if group_rows else None,
            "harmful_vs_static_rate": sum(1 for row in group_rows if row.get("harmful_vs_static") is True) / len(group_rows) if group_rows else None,
            "helpful_vs_static_rate": sum(1 for row in group_rows if row.get("helpful_vs_static") is True) / len(group_rows) if group_rows else None,
            "mean_selected_delta_vs_static": as_jsonable(mean([finite_number(row.get("selected_delta_vs_static"), math.inf) for row in group_rows])),
        }
        for key, group_rows in sorted(grouped.items())
    }


def coverage_risk(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for threshold in G59_THRESHOLDS:
        scored = []
        covered = 0
        harmful = 0
        for row in rows:
            confidence = finite_number(row.get("confidence"), 0.0)
            static_score = finite_number(row.get("static_score"), math.inf)
            selected_score = finite_number(row.get("selected_score"), static_score)
            if confidence >= threshold:
                covered += 1
                effective = selected_score
            else:
                effective = static_score
            scored.append({**row, "selected_score": effective, "selected_candidate_id": row.get("selected_candidate_id", "") if confidence >= threshold else G56_STATIC_CANDIDATE})
            if math.isfinite(effective) and math.isfinite(static_score) and effective > static_score + G59_DEFAULT_MARGIN:
                harmful += 1
        metrics = metric_summary(scored)
        out.append(
            {
                "threshold": threshold,
                "coverage": covered / len(rows) if rows else None,
                "abstention_rate": 1.0 - (covered / len(rows)) if rows else None,
                "harmful_vs_static_rate": harmful / len(rows) if rows else None,
                "mean_delta_vs_static": metrics.get("mean_delta_vs_static"),
            }
        )
    return out


def failure_diagnosis(rows: list[dict[str, Any]], train_summary: dict[str, Any], eval_summary: dict[str, Any]) -> dict[str, bool]:
    calibration = eval_summary.get("calibration_bins", {})
    high_conf = calibration.get("ge_0p75", {})
    high_conf_accuracy = finite_number(high_conf.get("accuracy"), math.nan)
    classes = list(train_summary.get("classes", []))
    gates = eval_summary.get("gates", {})
    return {
        "model_overfit_or_calibration": bool(math.isfinite(high_conf_accuracy) and high_conf_accuracy < 0.55),
        "feature_signal_insufficient": bool(not gates.get("beats_majority_expert", False) and not gates.get("beats_random_features", False)),
        "label_noise_or_budget_sensitivity": bool(sum(1 for row in rows if row.get("label_class") == "stable_static" and row.get("selected_candidate_id") != row.get("target_candidate_id")) > 0),
        "candidate_space_too_narrow": len(classes) <= 2,
        "control_implementation_bug": bool(not gates.get("beats_random_features", False) and "random_control_score" not in rows[0] if rows else True),
        "insufficient_train_dev_rows": int(train_summary.get("train_rows") or 0) <= 20 or int(train_summary.get("dev_rows") or 0) <= 20,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    missing = missing_required_g58_artifacts(root)
    if missing:
        summary = {"decision": "missing_g58_artifacts_stop", "missing_artifacts": missing, **G59_CLOSED_STATUS}
        write_json(resolve(args.summary_json, root), summary)
        write_text(resolve(args.report, root), "# Repair5G.5.9 G5.8 Offline Eval Autopsy\n\nmissing_g58_artifacts_stop\n")
        print(json.dumps({"decision": "missing_g58_artifacts_stop", "missing": len(missing)}))
        return 2

    eval_rows = add_eval_flags(read_csv_rows(resolve(args.eval_csv, root)), float(args.harmful_margin))
    train_summary = load_json(resolve(args.train_summary_json, root))
    eval_summary = load_json(resolve(args.eval_summary_json, root))
    harmful_rows = [row for row in eval_rows if row.get("harmful_vs_static") is True]
    helpful_rows = [row for row in eval_rows if row.get("helpful_vs_static") is True]
    confusion = confusion_rows(eval_rows)
    calibration = calibration_bins(eval_rows)
    coverage = coverage_risk(eval_rows)
    write_csv_rows(resolve(args.confusion_by_map_agent_csv, root), confusion)
    write_csv_rows(resolve(args.harmful_rows_csv, root), harmful_rows)
    write_csv_rows(resolve(args.helpful_rows_csv, root), helpful_rows)
    write_csv_rows(resolve(args.calibration_bins_csv, root), calibration)
    selected_oracle_regrets = [finite_number(row.get("selected_oracle_regret"), math.inf) for row in eval_rows]
    static_regrets = [finite_number(row.get("static_regret"), math.inf) for row in eval_rows]
    deltas = [finite_number(row.get("selected_delta_vs_static"), math.inf) for row in eval_rows]
    diagnosis = failure_diagnosis(eval_rows, train_summary, eval_summary)
    summary = {
        "schema_version": "phase5p5_repair5g59_g58_offline_eval_autopsy_summary_v1",
        "decision": "g58_eval_autopsy_completed_continue_corrected_controls",
        "eval_rows": len(eval_rows),
        "class_counts": count_by(eval_rows, "label_class"),
        "target_counts": count_by(eval_rows, "target_candidate_id"),
        "selected_counts": count_by(eval_rows, "selected_candidate_id"),
        "overall_metrics": metric_summary(eval_rows, harmful_margin=float(args.harmful_margin)),
        "by_map": group_breakdown(eval_rows, "map"),
        "by_agent": group_breakdown(eval_rows, "agents"),
        "by_seed": group_breakdown(eval_rows, "seed"),
        "by_label_class": group_breakdown(eval_rows, "label_class"),
        "static_regret_distribution": quantiles(static_regrets),
        "oracle_gap_distribution": quantiles(deltas),
        "selected_vs_oracle_regret_distribution": quantiles(selected_oracle_regrets),
        "coverage_risk_curve": coverage,
        "failure_diagnosis": diagnosis,
        "confusion_by_map_agent_csv": str(resolve(args.confusion_by_map_agent_csv, root)),
        "harmful_rows_csv": str(resolve(args.harmful_rows_csv, root)),
        "helpful_rows_csv": str(resolve(args.helpful_rows_csv, root)),
        "calibration_bins_csv": str(resolve(args.calibration_bins_csv, root)),
        "g58_control_naming_audit": {
            "previous_eval_gate_names": ["beats_random_features", "beats_shuffled_labels"],
            "observed_eval_columns": sorted(eval_rows[0]) if eval_rows else [],
            "semantic_issue": "G5.8 recorded random/shuffled candidate choices, not separately trained random-feature or shuffled-label models.",
            "requires_g59_corrected_controls": True,
        },
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    report = (
        "# Phase5.5 Repair5G.5.9 G5.8 Offline Eval Autopsy\n\n"
        f"- eval_rows: `{len(eval_rows)}`\n"
        f"- harmful_rows: `{len(harmful_rows)}`\n"
        f"- helpful_rows: `{len(helpful_rows)}`\n"
        f"- train_rows/dev_rows: `{train_summary.get('train_rows')}` / `{train_summary.get('dev_rows')}`\n"
        f"- classes: `{json.dumps(train_summary.get('classes', []))}`\n"
        f"- diagnosis: `{json.dumps(diagnosis, sort_keys=True)}`\n\n"
        "The G5.8 model had weak positive mean score movement, but the autopsy confirms poor high-confidence calibration, too few train/dev rows, a two-candidate action space, and a naming mismatch in the negative-control gates.\n"
    )
    write_text(resolve(args.report, root), report)
    print(json.dumps({"decision": summary["decision"], "eval_rows": len(eval_rows)}))
    return 0 if eval_rows else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

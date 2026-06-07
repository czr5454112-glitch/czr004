"""Audit Repair5G.5.9 feature signal quality for offline G6 learning."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "scripts"))

from repair5g59_common import (  # noqa: E402
    G59_CLOSED_STATUS,
    default_threshold_targets,
    feature_names_from_summary,
    finite_number,
    is_true,
    load_json,
    mean,
    predict_model,
    read_csv_rows,
    repo_root,
    resolve,
    row_split,
    target_classes,
    train_multinomial_model,
    training_rows,
    write_csv_rows,
    write_json,
    write_text,
)


DEFAULT_FEATURES = "outputs/tables/phase5p5_repair5g58_g6_features_perf_safe.csv"
DEFAULT_FEATURE_SUMMARY = "outputs/reports/phase5p5_repair5g58_g6_feature_matrix_summary.json"
DEFAULT_TARGETS = "outputs/tables/phase5p5_repair5g58_confidence_weighted_targets.csv"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5g59_feature_signal_quality.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5g59_feature_signal_quality_summary.json"
DEFAULT_FEATURE_TABLE = "outputs/tables/phase5p5_repair5g59_feature_signal_quality.csv"
DEFAULT_ABLATION_TABLE = "outputs/tables/phase5p5_repair5g59_feature_ablation_quality.csv"


ABLATIONS = {
    "all_perf_safe": None,
    "no_map_dimensions": {"agents", "map_width", "map_height", "free_cells", "obstacle_ratio", "density"},
    "no_density_free_cell_features": {"density", "free_cells", "obstacle_ratio"},
    "no_incumbent_history_features": {"ltm_iterations", "returned_solutions_count_so_far", "has_incumbent_before", "best_ratio_before", "improved_last_iteration"},
    "only_trace_event_features": {
        "committed_count",
        "blocked_count",
        "wait_event_count",
        "progress_committed_count",
        "nonprogress_committed_count",
        "blocked_per_committed",
        "wait_per_committed",
        "blocked_per_agent",
        "committed_per_agent",
        "progress_ratio",
    },
    "only_cf_traffic_map_summary_features": {
        "c_update_count",
        "f_update_count",
        "c_nonzero_edges",
        "f_nonzero_edges",
        "c_flow_update_ratio",
    },
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-matrix-csv", type=Path, default=Path(DEFAULT_FEATURES))
    parser.add_argument("--feature-summary-json", type=Path, default=Path(DEFAULT_FEATURE_SUMMARY))
    parser.add_argument("--targets-csv", type=Path, default=Path(DEFAULT_TARGETS))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    parser.add_argument("--feature-quality-csv", type=Path, default=Path(DEFAULT_FEATURE_TABLE))
    parser.add_argument("--feature-ablation-csv", type=Path, default=Path(DEFAULT_ABLATION_TABLE))
    parser.add_argument("--seed", type=int, default=20260607)
    return parser.parse_args(argv)


def merge_rows(feature_rows: list[dict[str, Any]], target_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    targets_by_context = {row.get("context_id", ""): row for row in target_rows}
    out = []
    for row in feature_rows:
        target = targets_by_context.get(row.get("context_id", ""))
        if target:
            out.append({**row, **{key: target.get(key, row.get(key, "")) for key in target}})
    return out


def feature_stats(rows: list[dict[str, Any]], feature_names: list[str]) -> list[dict[str, Any]]:
    train = [row for row in rows if row_split(row) == "train"]
    dev = [row for row in rows if row_split(row) == "dev"]
    stable = [row for row in rows if is_true(row.get("training_eligible"))]
    out = []
    for name in feature_names:
        values = [finite_number(row.get(name), math.nan) for row in rows]
        finite = [value for value in values if math.isfinite(value)]
        train_values = [finite_number(row.get(name), math.nan) for row in train]
        dev_values = [finite_number(row.get(name), math.nan) for row in dev]
        nonstatic_values = [finite_number(row.get(name), math.nan) for row in stable if row.get("label_class") == "stable_high_confidence_nonstatic"]
        static_values = [finite_number(row.get(name), math.nan) for row in stable if row.get("label_class") in {"stable_static", "abstain_to_static"}]
        finite_train = [value for value in train_values if math.isfinite(value)]
        finite_dev = [value for value in dev_values if math.isfinite(value)]
        finite_nonstatic = [value for value in nonstatic_values if math.isfinite(value)]
        finite_static = [value for value in static_values if math.isfinite(value)]
        variance = 0.0
        if finite:
            avg = mean(finite)
            variance = sum((value - avg) ** 2 for value in finite) / len(finite)
        train_mean = mean(finite_train)
        dev_mean = mean(finite_dev)
        nonstatic_mean = mean(finite_nonstatic)
        static_mean = mean(finite_static)
        out.append(
            {
                "feature": name,
                "mean": mean(finite),
                "variance": variance,
                "constant": variance <= 1.0e-12,
                "train_mean": train_mean if math.isfinite(train_mean) else "",
                "dev_mean": dev_mean if math.isfinite(dev_mean) else "",
                "train_dev_abs_shift": abs(train_mean - dev_mean) if math.isfinite(train_mean) and math.isfinite(dev_mean) else "",
                "nonstatic_mean": nonstatic_mean if math.isfinite(nonstatic_mean) else "",
                "static_mean": static_mean if math.isfinite(static_mean) else "",
                "univariate_effect_nonstatic_minus_static": nonstatic_mean - static_mean if math.isfinite(nonstatic_mean) and math.isfinite(static_mean) else "",
            }
        )
    return out


def ablation_features(name: str, feature_names: list[str]) -> list[str]:
    spec = ABLATIONS[name]
    if spec is None:
        return feature_names
    if name.startswith("only_"):
        return [feature for feature in feature_names if feature in spec]
    return [feature for feature in feature_names if feature not in spec]


def ablation_eval(rows: list[dict[str, Any]], feature_names: list[str], classes: list[str], seed: int) -> list[dict[str, Any]]:
    train = [row for row in training_rows(rows) if row_split(row) == "train"]
    dev = [row for row in training_rows(rows) if row_split(row) == "dev"]
    out = []
    for name in ABLATIONS:
        selected_features = ablation_features(name, feature_names)
        model = train_multinomial_model(
            train,
            selected_features,
            classes,
            label_field="target_candidate_id",
            seed=seed,
            epochs=180,
            learning_rate=0.03,
            salt=f"repair5g59_feature_ablation_{name}",
        )
        correct = 0
        confidences = []
        for row in dev:
            pred, confidence = predict_model(model, row)
            correct += int(pred == row.get("target_candidate_id", ""))
            confidences.append(confidence)
        out.append(
            {
                "ablation": name,
                "feature_count": len(selected_features),
                "dev_rows": len(dev),
                "dev_accuracy": correct / len(dev) if dev else "",
                "mean_confidence": mean(confidences) if confidences else "",
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    feature_rows = read_csv_rows(resolve(args.feature_matrix_csv, root))
    feature_summary = load_json(resolve(args.feature_summary_json, root))
    target_rows = default_threshold_targets(read_csv_rows(resolve(args.targets_csv, root)))
    rows = merge_rows(feature_rows, target_rows)
    feature_names = feature_names_from_summary(feature_summary, rows)
    stats_rows = feature_stats(rows, feature_names)
    classes = target_classes(training_rows(rows))
    ablations = ablation_eval(rows, feature_names, classes, int(args.seed))
    write_csv_rows(resolve(args.feature_quality_csv, root), stats_rows)
    write_csv_rows(resolve(args.feature_ablation_csv, root), ablations)
    constant = [row["feature"] for row in stats_rows if row.get("constant") is True]
    high_shift = [
        row["feature"]
        for row in stats_rows
        if finite_number(row.get("train_dev_abs_shift"), 0.0) > max(1.0, abs(finite_number(row.get("train_mean"), 0.0)) * 0.5)
    ]
    best_ablation_accuracy = max([finite_number(row.get("dev_accuracy"), math.nan) for row in ablations], default=math.nan)
    leakage_risk_features = sorted(set(feature_names) & {"agents", "map_width", "map_height", "density", "free_cells", "obstacle_ratio"})
    feature_signal_too_weak = bool(not math.isfinite(best_ablation_accuracy) or best_ablation_accuracy < 0.65)
    summary = {
        "schema_version": "phase5p5_repair5g59_feature_signal_quality_summary_v1",
        "decision": "feature_signal_insufficient_continue_feature_design" if feature_signal_too_weak else "feature_signal_has_weak_but_usable_signal_continue",
        "rows": len(rows),
        "training_eligible_rows": len(training_rows(rows)),
        "feature_count": len(feature_names),
        "constant_features": constant,
        "constant_feature_count": len(constant),
        "high_train_dev_shift_features": high_shift,
        "map_agent_leakage_risk_features": leakage_risk_features,
        "feature_ablation_results": ablations,
        "best_ablation_dev_accuracy": best_ablation_accuracy if math.isfinite(best_ablation_accuracy) else None,
        "current_features_too_weak_to_distinguish_static_vs_nonstatic_safely": feature_signal_too_weak,
        "feature_quality_csv": str(resolve(args.feature_quality_csv, root)),
        "feature_ablation_csv": str(resolve(args.feature_ablation_csv, root)),
        **G59_CLOSED_STATUS,
    }
    write_json(resolve(args.summary_json, root), summary)
    write_text(
        resolve(args.report, root),
        "# Phase5.5 Repair5G.5.9 Feature Signal Quality\n\n"
        f"- rows: `{len(rows)}`\n"
        f"- training_eligible_rows: `{len(training_rows(rows))}`\n"
        f"- feature_count: `{len(feature_names)}`\n"
        f"- constant_feature_count: `{len(constant)}`\n"
        f"- high_train_dev_shift_features: `{json.dumps(high_shift)}`\n"
        f"- map_agent_leakage_risk_features: `{json.dumps(leakage_risk_features)}`\n"
        f"- best_ablation_dev_accuracy: `{summary['best_ablation_dev_accuracy']}`\n"
        f"- decision: `{summary['decision']}`\n\n"
        "This audit is diagnostic-only; it does not authorize runtime claims or Phase5.5 promotion.\n",
    )
    print(json.dumps({"decision": summary["decision"], "feature_count": len(feature_names)}))
    return 0 if rows and feature_names else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

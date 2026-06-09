"""Repair5D multi-source composite grid for LAUR Repair5 outputs.

The grid recombines ranking, safety, and anti/defer CSVs from existing
checkpoints. It performs no training and never permits runtime promotion.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from eval.eval_laur_repair5_composite_inference import (  # noqa: E402
    DEFAULT_CALIBRATION_JSON,
    DEFAULT_DATASET,
    composite_records,
    load_eval_rows,
    load_json,
    load_label_rows,
    resolve_path,
)


DEFAULT_RANKING_CSVS = [
    "outputs/tables/phase4f_repair5_expand5000_postnext_hightoken_attn_mlp_head_rank_recall_perrule_eval_seed61.csv",
    "outputs/tables/phase4f_repair5_expand5000_nextwave_normal_attn_linear_head_rank_safe_eval_seed61.csv",
    "outputs/tables/phase4f_repair5_rawtrace_edge_sf_target_ce1_margin1_hm4_eval_seed61.csv",
]
DEFAULT_SAFETY_CSVS = [
    "outputs/tables/phase4f_repair5_expand5000_postnext_hightoken_attn_mlp_head_rank_recall_perrule_eval_seed61.csv",
    "outputs/tables/phase4f_repair5_expand5000_nextwave_normal_attn_linear_head_rank_safe_eval_seed61.csv",
    "outputs/tables/phase4f_repair5_expand5000_hightoken_ht_mlp_target_global_eval_seed61.csv",
]
DEFAULT_ANTI_CSVS = [
    "outputs/tables/phase4f_repair5_rawtrace_edge_sf_global_pair_neg2_anti2_eval_seed61.csv",
    "outputs/tables/phase4f_repair5_rawtrace_edge_sf_global_rank3_anti3_eval_seed61.csv",
    "outputs/tables/phase4f_repair5_expand5000_postnext_hightoken_attn_mlp_head_rank_recall_perrule_eval_seed61.csv",
]
DEFAULT_SUMMARY_JSON = "outputs/reports/phase4f_repair5d_composite_grid_summary.json"
DEFAULT_SUMMARY_CSV = "outputs/tables/phase4f_repair5d_composite_grid_summary.csv"
DEFAULT_RECORDS_CSV = "outputs/tables/phase4f_repair5d_composite_grid_records.csv"
DEFAULT_REPORT = "outputs/reports/phase4f_repair5d_composite_grid.md"


@dataclass(frozen=True)
class GridMode:
    name: str
    composite_mode: str
    top_k: int
    description: str


GRID_MODES = [
    GridMode(
        "rank_model_top3_safety_model_per_rule_utility_rerank",
        "top3_per_rule_safety_utility",
        3,
        "top3 rank candidates, learned per-rule safety thresholds, oracle utility rerank diagnostic",
    ),
    GridMode(
        "rank_model_top5_safety_model_per_rule_utility_rerank",
        "top3_per_rule_safety_utility",
        5,
        "top5 rank candidates, learned per-rule safety thresholds, oracle utility rerank diagnostic",
    ),
    GridMode(
        "rank_model_top3_anti_decision_margin_safety_model_per_family",
        "top3_anti_margin_per_family_safety",
        3,
        "top3 rank candidates, anti opportunity-defer margin, learned per-family safety",
    ),
    GridMode(
        "rank_model_top3_learned_defer_penalty_per_rule_safety",
        "anti_decision_top3_per_rule_safety",
        3,
        "top3 rank candidates, learned anti/defer decision, learned per-rule safety",
    ),
    GridMode(
        "rank_model_top5_utility_regret_min_selected_harmful_constraint",
        "top3_per_rule_safety_utility",
        5,
        "top5 utility-regret diagnostic, ranked with selected harmful-rate constraint in report",
    ),
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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


def _existing(paths: list[str | Path], root: Path) -> list[Path]:
    out: list[Path] = []
    for path in paths:
        resolved = resolve_path(path, root)
        if resolved is not None and resolved.exists():
            out.append(resolved)
    return out


def _short(path: Path) -> str:
    return path.stem.replace("phase4f_repair5_", "")


def score_metrics(metrics: dict[str, Any]) -> float:
    harmful = float(metrics.get("selected_harmful_rate") or 0.0)
    recall = float(metrics.get("harmful_recall") or 0.0)
    precision = float(metrics.get("harmful_precision") or 0.0)
    delta = float(metrics.get("selected_vs_additive_delta") or 0.0)
    regret = float(metrics.get("utility_regret_to_oracle") or 0.0)
    capture = float(metrics.get("high_margin_capture") or 0.0)
    penalty = 0.0
    if harmful > 0.02:
        penalty += 10.0 * (harmful - 0.02)
    penalty += max(0.0, 0.80 - recall) * 0.05
    penalty += max(0.0, 0.30 - precision) * 0.05
    return delta + 0.05 * capture - regret - penalty


def run_grid(
    *,
    labels: dict[str, dict[str, Any]],
    ranking_sources: dict[Path, dict[str, dict[str, Any]]],
    safety_sources: dict[Path, dict[str, dict[str, Any]]],
    anti_sources: dict[Path, dict[str, dict[str, Any]]],
    calibration: dict[str, Any],
    modes: list[GridMode],
    default_threshold: float,
    opportunity_threshold: float,
    defer_threshold: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summary_rows: list[dict[str, Any]] = []
    record_rows: list[dict[str, Any]] = []
    for mode in modes:
        for ranking_path, ranking_rows in ranking_sources.items():
            for safety_path, safety_rows in safety_sources.items():
                for anti_path, anti_rows in anti_sources.items():
                    metrics_by_mode, records = composite_records(
                        labels=labels,
                        ranking_rows=ranking_rows,
                        safety_rows=safety_rows,
                        anti_rows=anti_rows,
                        calibration=calibration,
                        modes=[mode.composite_mode],
                        top_k=mode.top_k,
                        default_threshold=default_threshold,
                        opportunity_threshold=opportunity_threshold,
                        defer_threshold=defer_threshold,
                    )
                    metrics = metrics_by_mode[mode.composite_mode]
                    grid_id = f"{mode.name}__rank={_short(ranking_path)}__safety={_short(safety_path)}__anti={_short(anti_path)}"
                    summary_row = {
                        "grid_id": grid_id,
                        "grid_mode": mode.name,
                        "composite_mode": mode.composite_mode,
                        "top_k": mode.top_k,
                        "ranking_csv": str(ranking_path),
                        "safety_csv": str(safety_path),
                        "anti_csv": str(anti_path),
                        "sample_count": metrics.get("sample_count", 0),
                        "rule_top1": metrics.get("rule_top1"),
                        "rule_top3": metrics.get("rule_top3"),
                        "safe_utility_top1": metrics.get("safe_utility_top1"),
                        "safe_utility_top3": metrics.get("safe_utility_top3"),
                        "utility_regret_to_oracle": metrics.get("utility_regret_to_oracle"),
                        "selected_vs_additive_delta": metrics.get("selected_vs_additive_delta"),
                        "selected_vs_additive_utility": metrics.get("selected_vs_additive_utility"),
                        "harmful_recall": metrics.get("harmful_recall"),
                        "harmful_precision": metrics.get("harmful_precision"),
                        "selected_harmful_rate": metrics.get("selected_harmful_rate"),
                        "high_margin_capture": metrics.get("high_margin_capture"),
                        "global_additive_or_defer_rate": metrics.get("global_additive_or_defer_rate"),
                        "passes_selected_harmful_le_001": float(metrics.get("selected_harmful_rate") or 0.0) <= 0.01,
                        "passes_selected_harmful_le_002": float(metrics.get("selected_harmful_rate") or 0.0) <= 0.02,
                        "recall_gap_to_gate": max(0.0, 0.80 - float(metrics.get("harmful_recall") or 0.0)),
                        "precision_gap_to_gate": max(0.0, 0.30 - float(metrics.get("harmful_precision") or 0.0)),
                        "score": score_metrics(metrics),
                    }
                    summary_rows.append(summary_row)
                    for record in records:
                        out = dict(record)
                        out["grid_id"] = grid_id
                        out["grid_mode"] = mode.name
                        out["ranking_csv"] = str(ranking_path)
                        out["safety_csv"] = str(safety_path)
                        out["anti_csv"] = str(anti_path)
                        record_rows.append(out)
    summary_rows.sort(key=lambda row: float(row["score"]), reverse=True)
    return summary_rows, record_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, *, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair5D Composite Grid\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("This is no-retraining diagnostic evidence only. Phase5.5 and Phase6 remain forbidden.\n\n")
        handle.write("## Top Modes\n\n")
        handle.write(
            "| rank | mode | samples | delta | regret | selected harmful | recall | precision | high-margin | defer/additive | score |\n"
        )
        handle.write("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for index, row in enumerate(summary["summary_rows"][:20], 1):
            handle.write(
                f"| {index} | {row['grid_mode']} | {row['sample_count']} | "
                f"{float(row['selected_vs_additive_delta'] or 0.0):.6f} | "
                f"{float(row['utility_regret_to_oracle'] or 0.0):.6f} | "
                f"{float(row['selected_harmful_rate'] or 0.0):.6f} | "
                f"{float(row['harmful_recall'] or 0.0):.6f} | "
                f"{float(row['harmful_precision'] or 0.0):.6f} | "
                f"{float(row['high_margin_capture'] or 0.0):.6f} | "
                f"{float(row['global_additive_or_defer_rate'] or 0.0):.6f} | "
                f"{float(row['score']):.6f} |\n"
            )
        handle.write("\n## Interpretation\n\n")
        handle.write(
            "The ranking favors positive selected-vs-additive delta, low regret, high high-margin capture, "
            "and selected harmful rate at or below 0.01-0.02. This report does not lower the final safety gate.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path(DEFAULT_DATASET))
    parser.add_argument("--ranking-csv", action="append", type=Path, default=[])
    parser.add_argument("--safety-csv", action="append", type=Path, default=[])
    parser.add_argument("--anti-csv", action="append", type=Path, default=[])
    parser.add_argument("--calibration-json", type=Path, default=Path(DEFAULT_CALIBRATION_JSON))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--summary-csv", type=Path, default=Path(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--records-csv", type=Path, default=Path(DEFAULT_RECORDS_CSV))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--split", default="validation")
    parser.add_argument("--default-threshold", type=float, default=0.35)
    parser.add_argument("--opportunity-threshold", type=float, default=0.50)
    parser.add_argument("--defer-threshold", type=float, default=0.50)
    parser.add_argument("--no-records", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    dataset = resolve_path(args.dataset, root)
    calibration_json = resolve_path(args.calibration_json, root)
    summary_json = resolve_path(args.summary_json, root)
    summary_csv = resolve_path(args.summary_csv, root)
    records_csv = resolve_path(args.records_csv, root)
    report = resolve_path(args.report, root)
    if None in (dataset, summary_json, summary_csv, records_csv, report):
        raise ValueError("required paths could not be resolved")
    assert dataset and summary_json and summary_csv and records_csv and report
    ranking_paths = _existing(args.ranking_csv or DEFAULT_RANKING_CSVS, root)
    safety_paths = _existing(args.safety_csv or DEFAULT_SAFETY_CSVS, root)
    anti_paths = _existing(args.anti_csv or DEFAULT_ANTI_CSVS, root)
    if not ranking_paths or not safety_paths or not anti_paths:
        raise FileNotFoundError("at least one ranking, safety, and anti CSV is required")
    labels = load_label_rows(dataset, split=str(args.split))
    ranking_sources = {path: load_eval_rows(path, split=str(args.split)) for path in ranking_paths}
    safety_sources = {path: load_eval_rows(path, split=str(args.split)) for path in safety_paths}
    anti_sources = {path: load_eval_rows(path, split=str(args.split)) for path in anti_paths}
    summary_rows, records = run_grid(
        labels=labels,
        ranking_sources=ranking_sources,
        safety_sources=safety_sources,
        anti_sources=anti_sources,
        calibration=load_json(calibration_json),
        modes=GRID_MODES,
        default_threshold=float(args.default_threshold),
        opportunity_threshold=float(args.opportunity_threshold),
        defer_threshold=float(args.defer_threshold),
    )
    summary = {
        "schema_version": "phase4f_repair5d_composite_grid_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "dataset": str(dataset),
        "split": str(args.split),
        "ranking_csvs": [str(path) for path in ranking_paths],
        "safety_csvs": [str(path) for path in safety_paths],
        "anti_csvs": [str(path) for path in anti_paths],
        "summary_rows": summary_rows,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    write_csv(summary_csv, summary_rows)
    if not args.no_records:
        write_csv(records_csv, records)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary=summary)
    print(json.dumps({"summary_json": str(summary_json), "summary_csv": str(summary_csv), "records_csv": str(records_csv), "report": str(report)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

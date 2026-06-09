"""Diagnose Phase4F LAU-LTM label ambiguity and prediction regret."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.token_features_laur import executable_rule_id  # noqa: E402


DEFAULT_EPSILONS = [0.001, 0.0025, 0.005, 0.01, 0.02]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path | None, root: Path) -> Path | None:
    if path is None:
        return None
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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


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


def group_by_checkpoint(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["checkpoint_id"])].append(row)
    return grouped


def dataset_by_checkpoint(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["checkpoint_id"]): row for row in rows}


def target_rule_original(row: dict[str, Any]) -> str:
    target = row.get("target", {})
    if "rule_class_original" in target:
        return str(target["rule_class_original"])
    return str(target.get("rule_class", ""))


def target_rule_executable(row: dict[str, Any]) -> str:
    target = row.get("target", {})
    if "best_rule_executable" in target:
        return str(target["best_rule_executable"])
    return executable_rule_id(target.get("rule_class"))


def sorted_probe_rules(probe_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        probe_rows,
        key=lambda row: (safe_float(row.get("delta_ratio_vs_additive"), float("-inf")), str(row.get("rule_id", ""))),
        reverse=True,
    )


def probe_delta_lookup(probe_rows: list[dict[str, Any]]) -> dict[str, float]:
    lookup: dict[str, float] = {}
    for row in probe_rows:
        lookup[executable_rule_id(str(row.get("rule_id", "")))] = safe_float(row.get("delta_ratio_vs_additive"))
    return lookup


def checkpoint_margin_detail(
    dataset_row: dict[str, Any],
    probe_rows: list[dict[str, Any]],
    *,
    epsilons: list[float],
) -> dict[str, Any]:
    ordered = sorted_probe_rules(probe_rows)
    if not ordered:
        raise ValueError(f"missing probe rows for {dataset_row['checkpoint_id']}")
    best_delta = safe_float(ordered[0].get("delta_ratio_vs_additive"))
    second_delta = safe_float(ordered[1].get("delta_ratio_vs_additive")) if len(ordered) > 1 else best_delta
    target_exec = target_rule_executable(dataset_row)
    deltas = probe_delta_lookup(probe_rows)
    target_delta = deltas.get(target_exec, 0.0)
    detail = {
        "checkpoint_id": dataset_row["checkpoint_id"],
        "split": dataset_row["split"],
        "map_name": dataset_row["map_name"],
        "agents": dataset_row["agents"],
        "seed": dataset_row["seed"],
        "iteration": dataset_row["iteration"],
        "target_rule_original": target_rule_original(dataset_row),
        "target_rule_executable": target_exec,
        "best_probe_rule": executable_rule_id(str(ordered[0].get("rule_id", ""))),
        "second_probe_rule": executable_rule_id(str(ordered[1].get("rule_id", ""))) if len(ordered) > 1 else executable_rule_id(str(ordered[0].get("rule_id", ""))),
        "best_delta": best_delta,
        "second_delta": second_delta,
        "best_minus_second": best_delta - second_delta,
        "target_delta": target_delta,
        "best_minus_target": best_delta - target_delta,
        "candidate_count": len(probe_rows),
        "harmful_candidate_count": sum(1 for row in probe_rows if row.get("harmful")),
    }
    for epsilon in epsilons:
        key = str(epsilon).replace(".", "_")
        detail[f"tie_count_eps_{key}"] = sum(
            1
            for row in ordered
            if best_delta - safe_float(row.get("delta_ratio_vs_additive")) <= float(epsilon)
        )
        detail[f"target_in_tie_eps_{key}"] = int(detail["best_minus_target"] <= float(epsilon))
    return detail


def build_margin_details(
    dataset_rows: list[dict[str, Any]],
    probe_rows_by_checkpoint: dict[str, list[dict[str, Any]]],
    *,
    epsilons: list[float],
) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for row in dataset_rows:
        checkpoint_id = str(row["checkpoint_id"])
        probes = probe_rows_by_checkpoint.get(checkpoint_id, [])
        if probes:
            details.append(checkpoint_margin_detail(row, probes, epsilons=epsilons))
    return details


def parse_prediction_arg(value: str) -> tuple[str, Path]:
    if "=" not in value:
        path = Path(value)
        return path.stem, path
    label, path = value.split("=", 1)
    return label.strip(), Path(path.strip())


def prediction_target_exec(prediction_row: dict[str, str], dataset_row: dict[str, Any]) -> str:
    if prediction_row.get("target_rule_executable"):
        return executable_rule_id(prediction_row["target_rule_executable"])
    if prediction_row.get("target_rule"):
        return executable_rule_id(prediction_row["target_rule"])
    return target_rule_executable(dataset_row)


def prediction_top3_rules(prediction_row: dict[str, str]) -> list[str]:
    value = prediction_row.get("top3_rules", "")
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [executable_rule_id(str(rule_id)) for rule_id in parsed]


def prediction_regret_rows(
    *,
    model_label: str,
    prediction_rows: list[dict[str, str]],
    dataset_rows_by_checkpoint: dict[str, dict[str, Any]],
    probe_rows_by_checkpoint: dict[str, list[dict[str, Any]]],
    epsilons: list[float],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for prediction in prediction_rows:
        checkpoint_id = str(prediction.get("checkpoint_id", ""))
        dataset_row = dataset_rows_by_checkpoint.get(checkpoint_id)
        probes = probe_rows_by_checkpoint.get(checkpoint_id, [])
        if dataset_row is None or not probes:
            continue
        ordered = sorted_probe_rules(probes)
        deltas = probe_delta_lookup(probes)
        best_delta = safe_float(ordered[0].get("delta_ratio_vs_additive"))
        pred_rule = executable_rule_id(prediction.get("predicted_rule"))
        pred_delta = deltas.get(pred_rule, 0.0)
        target_exec = prediction_target_exec(prediction, dataset_row)
        target_delta = deltas.get(target_exec, 0.0)
        top3 = prediction_top3_rules(prediction)
        record: dict[str, Any] = {
            "model": model_label,
            "checkpoint_id": checkpoint_id,
            "split": dataset_row["split"],
            "map_name": dataset_row["map_name"],
            "agents": dataset_row["agents"],
            "seed": dataset_row["seed"],
            "iteration": dataset_row["iteration"],
            "target_rule_original": target_rule_original(dataset_row),
            "target_rule_executable": target_exec,
            "predicted_rule": pred_rule,
            "exact_executable_correct": int(pred_rule == target_exec),
            "prediction_delta": pred_delta,
            "target_delta": target_delta,
            "best_delta": best_delta,
            "regret_vs_best": best_delta - pred_delta,
            "regret_vs_target": target_delta - pred_delta,
            "target_regret_vs_best": best_delta - target_delta,
            "predicted_rank_by_delta": 1
            + sum(1 for row in ordered if safe_float(row.get("delta_ratio_vs_additive")) > pred_delta),
            "top3_rule_count": len(top3),
        }
        for epsilon in epsilons:
            key = str(epsilon).replace(".", "_")
            tie_rules = {
                executable_rule_id(str(row.get("rule_id", "")))
                for row in ordered
                if best_delta - safe_float(row.get("delta_ratio_vs_additive")) <= float(epsilon)
            }
            record[f"pred_within_eps_{key}"] = int(pred_rule in tie_rules)
            record[f"top3_hits_tie_eps_{key}"] = int(bool(top3) and bool(set(top3) & tie_rules))
        records.append(record)
    return records


def split_summary(rows: list[dict[str, Any]], *, epsilons: list[float]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[("all", "all")].append(row)
        grouped[("split", str(row["split"]))].append(row)
        grouped[("map", str(row["map_name"]))].append(row)
        if row.get("model"):
            grouped[(f"model:{row['model']}:split", str(row["split"]))].append(row)
    summaries: list[dict[str, Any]] = []
    for (scope, name), values in sorted(grouped.items()):
        if not values:
            continue
        summary: dict[str, Any] = {
            "scope": scope,
            "name": name,
            "sample_count": len(values),
        }
        if "best_minus_second" in values[0]:
            margins = [float(row["best_minus_second"]) for row in values]
            summary.update(
                {
                    "best_minus_second_mean": mean(margins),
                    "best_minus_second_q50": quantile(margins, 0.50),
                    "best_minus_second_q90": quantile(margins, 0.90),
                }
            )
            for epsilon in epsilons:
                key = str(epsilon).replace(".", "_")
                summary[f"margin_le_eps_{key}_rate"] = sum(
                    1 for row in values if float(row["best_minus_second"]) <= float(epsilon)
                ) / len(values)
                summary[f"target_in_tie_eps_{key}_rate"] = sum(
                    int(row[f"target_in_tie_eps_{key}"]) for row in values
                ) / len(values)
        if "regret_vs_best" in values[0]:
            regrets = [float(row["regret_vs_best"]) for row in values]
            summary.update(
                {
                    "exact_executable_top1": sum(int(row["exact_executable_correct"]) for row in values) / len(values),
                    "regret_vs_best_mean": mean(regrets),
                    "regret_vs_best_q50": quantile(regrets, 0.50),
                    "regret_vs_best_q90": quantile(regrets, 0.90),
                    "predicted_delta_mean": mean([float(row["prediction_delta"]) for row in values]),
                    "predicted_rank_by_delta_mean": mean([float(row["predicted_rank_by_delta"]) for row in values]),
                }
            )
            for epsilon in epsilons:
                key = str(epsilon).replace(".", "_")
                summary[f"pred_within_eps_{key}_rate"] = sum(
                    int(row[f"pred_within_eps_{key}"]) for row in values
                ) / len(values)
                if any(int(row["top3_rule_count"]) for row in values):
                    summary[f"top3_hits_tie_eps_{key}_rate"] = sum(
                        int(row[f"top3_hits_tie_eps_{key}"]) for row in values
                    ) / len(values)
        summaries.append(summary)
    return summaries


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def write_report(
    path: Path,
    *,
    root: Path,
    dataset_path: Path,
    probe_path: Path,
    prediction_paths: list[tuple[str, Path]],
    margin_summary: list[dict[str, Any]],
    prediction_summary: list[dict[str, Any]],
    epsilons: list[float],
) -> None:
    def row_for(summary: list[dict[str, Any]], scope: str, name: str) -> dict[str, Any]:
        return next((row for row in summary if row["scope"] == scope and row["name"] == name), {})

    validation_margin = row_for(margin_summary, "split", "validation")
    lines = [
        "# Phase4F Repair1 Label Ambiguity Diagnostics",
        "",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}",
        "",
        "## Code State",
        "",
        f"- branch: `{git_value(['branch', '--show-current'], root)}`",
        f"- commit: `{git_value(['rev-parse', '--short', 'HEAD'], root)}`",
        "",
        "## Inputs",
        "",
        f"- dataset: `{dataset_path.relative_to(root).as_posix()}`",
        f"- probes: `{probe_path.relative_to(root).as_posix()}`",
        "- prediction CSVs:",
    ]
    for label, path_value in prediction_paths:
        lines.append(f"  - `{label}`: `{path_value.relative_to(root).as_posix()}`")
    lines.extend(["", "## Validation Probe Margins", ""])
    lines.append(f"- validation samples: `{validation_margin.get('sample_count')}`")
    for epsilon in epsilons:
        key = str(epsilon).replace(".", "_")
        lines.append(
            f"- best-vs-second <= {epsilon}: "
            f"`{validation_margin.get(f'margin_le_eps_{key}_rate')}`"
        )
    lines.extend(["", "## Prediction Regret", ""])
    lines.append(
        "| model split | samples | exact top1 | pred within 0.005 | pred within 0.010 | regret mean | regret q90 | predicted rank mean |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for summary_row in prediction_summary:
        scope = str(summary_row["scope"])
        if not scope.endswith(":split") or summary_row["name"] != "validation":
            continue
        model = scope.removeprefix("model:").removesuffix(":split")
        lines.append(
            f"| {model} validation | {summary_row.get('sample_count')} | "
            f"{summary_row.get('exact_executable_top1')} | "
            f"{summary_row.get('pred_within_eps_0_005_rate')} | "
            f"{summary_row.get('pred_within_eps_0_01_rate')} | "
            f"{summary_row.get('regret_vs_best_mean')} | "
            f"{summary_row.get('regret_vs_best_q90')} | "
            f"{summary_row.get('predicted_rank_by_delta_mean')} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This diagnostic does not lower or replace the Phase4F exact-rule gate. It checks whether failed exact predictions are still near the best observed short-probe rule by delta.",
            "",
            "If exact top1/top3 fails while predicted regret is often small, the next repair should focus on stable target formulation and tie-aware labels before larger models. If regret remains large, the next repair should focus on richer trace features or additional train coverage.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--probes", type=Path, required=True)
    parser.add_argument("--prediction-csv", action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--epsilons", default=",".join(str(value) for value in DEFAULT_EPSILONS))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    dataset_path = resolve_path(args.dataset, root)
    probe_path = resolve_path(args.probes, root)
    output_dir = resolve_path(args.output_dir, root)
    report_path = resolve_path(args.report, root)
    summary_json_path = resolve_path(args.summary_json, root)
    assert dataset_path and probe_path and output_dir and report_path and summary_json_path
    epsilons = [float(item.strip()) for item in str(args.epsilons).split(",") if item.strip()]
    dataset_rows = read_jsonl(dataset_path)
    probe_rows = read_jsonl(probe_path)
    dataset_lookup = dataset_by_checkpoint(dataset_rows)
    probe_groups = group_by_checkpoint(probe_rows)
    prediction_paths = [(label, resolve_path(path, root)) for label, path in map(parse_prediction_arg, args.prediction_csv)]
    prediction_paths = [(label, path) for label, path in prediction_paths if path is not None]

    margin_details = build_margin_details(dataset_rows, probe_groups, epsilons=epsilons)
    margin_summary = split_summary(margin_details, epsilons=epsilons)
    prediction_records: list[dict[str, Any]] = []
    for label, path in prediction_paths:
        prediction_records.extend(
            prediction_regret_rows(
                model_label=label,
                prediction_rows=read_csv(path),
                dataset_rows_by_checkpoint=dataset_lookup,
                probe_rows_by_checkpoint=probe_groups,
                epsilons=epsilons,
            )
        )
    prediction_summary = split_summary(prediction_records, epsilons=epsilons)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "phase4f_label_ambiguity_margin_details.csv", margin_details)
    write_csv(output_dir / "phase4f_label_ambiguity_margin_summary.csv", margin_summary)
    write_csv(output_dir / "phase4f_label_ambiguity_prediction_regret.csv", prediction_records)
    write_csv(output_dir / "phase4f_label_ambiguity_prediction_summary.csv", prediction_summary)
    summary = {
        "schema_version": "phase4f_label_ambiguity_diagnostics_v1",
        "dataset": str(dataset_path),
        "probes": str(probe_path),
        "prediction_csvs": [{"label": label, "path": str(path)} for label, path in prediction_paths],
        "epsilons": epsilons,
        "margin_summary": margin_summary,
        "prediction_summary": prediction_summary,
    }
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(
        report_path,
        root=root,
        dataset_path=dataset_path,
        probe_path=probe_path,
        prediction_paths=prediction_paths,
        margin_summary=margin_summary,
        prediction_summary=prediction_summary,
        epsilons=epsilons,
    )
    print(json.dumps({"report": str(report_path), "summary_json": str(summary_json_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

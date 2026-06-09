"""Per-rule and per-family safety calibration for Repair5B LAUR.

The script calibrates harmful-rule probability thresholds from existing
Repair5 eval CSV files. It is diagnostic-only and does not permit runtime.
"""

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


DEFAULT_EVAL_CSV_CANDIDATES = [
    "outputs/tables/phase4f_repair5_expand5000_hightoken_ht_mlp_target_global_eval_seed61.csv",
    "outputs/tables/phase4f_repair5_rawtrace_edge_sf_global_pair_neg2_anti2_eval_seed61.csv",
    "outputs/tables/phase4f_repair5_expand5000_postnext_hightoken_attn_mlp_head_rank_recall_perrule_eval_seed61.csv",
    "outputs/tables/phase4f_repair5_expand5000_postnext_hightoken_attn_linear_head_rank_recall_lowanti_eval_seed61.csv",
]

DEFAULT_THRESHOLDS = [
    0.01,
    0.02,
    0.03,
    0.04,
    0.05,
    0.07,
    0.09,
    0.10,
    0.12,
    0.15,
    0.17,
    0.20,
    0.25,
    0.30,
    0.35,
    0.40,
    0.45,
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
    0.85,
    0.90,
    0.95,
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


def resolve_existing(path: str | Path, root: Path) -> Path:
    value = Path(path)
    candidate = value if value.is_absolute() else root / value
    if candidate.exists():
        return candidate
    raise FileNotFoundError(candidate)


def default_eval_csv(root: Path) -> Path:
    for candidate in DEFAULT_EVAL_CSV_CANDIDATES:
        path = root / candidate
        if path.exists():
            return path
    raise FileNotFoundError("no default Repair5 eval CSV found for safety calibration")


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def parse_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    text = str(value or "").strip()
    if not text:
        return []
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


def safe_div(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def f1_score(precision: float, recall: float) -> float:
    return 2.0 * precision * recall / (precision + recall) if precision + recall > 0.0 else 0.0


def confusion(items: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for item in items:
        label = bool(item["label"])
        pred = float(item["prob"]) >= float(threshold)
        if label and pred:
            tp += 1
        elif label and not pred:
            fn += 1
        elif not label and pred:
            fp += 1
        else:
            tn += 1
    recall = safe_div(tp, tp + fn)
    precision = safe_div(tp, tp + fp)
    return {
        "threshold": float(threshold),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "recall": recall,
        "precision": precision,
        "f1": f1_score(precision, recall),
        "support": len(items),
        "positive_count": tp + fn,
        "negative_count": tn + fp,
    }


def choose_threshold(
    items: list[dict[str, Any]],
    thresholds: list[float],
    *,
    min_recall: float,
    min_precision: float,
) -> dict[str, Any]:
    scored = [confusion(items, threshold) for threshold in thresholds]
    feasible = [
        row
        for row in scored
        if row["recall"] >= min_recall and row["precision"] >= min_precision and row["positive_count"] > 0
    ]
    if feasible:
        best = max(feasible, key=lambda row: (row["f1"], row["precision"], row["recall"], -row["threshold"]))
        best["passed"] = True
        best["selection_reason"] = "meets_recall_precision_targets"
        return best
    best = max(
        scored,
        key=lambda row: (
            min(row["recall"] / max(min_recall, 1.0e-9), 1.0)
            + min(row["precision"] / max(min_precision, 1.0e-9), 1.0),
            row["f1"],
            row["recall"],
            row["precision"],
        ),
    )
    best["passed"] = False
    best["selection_reason"] = "best_available_below_target"
    return best


def load_items(paths: list[Path], *, split: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items: list[dict[str, Any]] = []
    selected_records: list[dict[str, Any]] = []
    for path in paths:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if str(row.get("split", "")) != str(split):
                    continue
                probs = [finite(value) for value in parse_list(row.get("harmful_probs"))]
                labels = [1 if parse_bool(value) else 0 for value in parse_list(row.get("harmful_labels"))]
                if len(probs) != len(EXECUTABLE_RULE_IDS) or len(labels) != len(EXECUTABLE_RULE_IDS):
                    continue
                for index, rule in enumerate(EXECUTABLE_RULE_IDS):
                    items.append(
                        {
                            "source_csv": str(path),
                            "checkpoint_id": row.get("checkpoint_id", ""),
                            "rule": rule,
                            "family": rule_family(rule),
                            "prob": probs[index],
                            "label": labels[index],
                            "selected_rule": row.get("predicted_rule", ""),
                            "selected_rule_harmful": parse_bool(row.get("selected_rule_harmful")),
                            "has_high_margin_nonadditive_opportunity": parse_bool(
                                row.get("has_high_margin_nonadditive_opportunity")
                            ),
                        }
                    )
                selected_rule = str(row.get("predicted_rule", ""))
                if selected_rule in EXECUTABLE_RULE_IDS:
                    index = EXECUTABLE_RULE_IDS.index(selected_rule)
                    selected_records.append(
                        {
                            "source_csv": str(path),
                            "checkpoint_id": row.get("checkpoint_id", ""),
                            "rule": selected_rule,
                            "family": rule_family(selected_rule),
                            "prob": probs[index],
                            "label": labels[index],
                            "selected_rule_harmful": parse_bool(row.get("selected_rule_harmful")),
                            "fallback_reason": str(row.get("fallback_reason", "")),
                        }
                    )
    return items, selected_records


def apply_group_thresholds(
    items: list[dict[str, Any]],
    thresholds: dict[str, float],
    *,
    group_key: str,
    min_recall: float,
    min_precision: float,
) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for item in items:
        threshold = thresholds.get(str(item[group_key]), thresholds.get("global", 0.10))
        label = bool(item["label"])
        pred = float(item["prob"]) >= float(threshold)
        if label and pred:
            tp += 1
        elif label and not pred:
            fn += 1
        elif not label and pred:
            fp += 1
        else:
            tn += 1
    recall = safe_div(tp, tp + fn)
    precision = safe_div(tp, tp + fp)
    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "recall": recall,
        "precision": precision,
        "f1": f1_score(precision, recall),
        "passed": recall >= min_recall and precision >= min_precision,
        "support": len(items),
        "positive_count": tp + fn,
        "negative_count": tn + fp,
    }


def selected_distribution(
    selected_records: list[dict[str, Any]],
    thresholds: dict[str, float],
    *,
    group_key: str,
) -> dict[str, Any]:
    false_negative = Counter()
    false_positive = Counter()
    for record in selected_records:
        threshold = thresholds.get(str(record[group_key]), thresholds.get("global", 0.10))
        pred_harmful = float(record["prob"]) >= float(threshold)
        label = bool(record["label"])
        if label and not pred_harmful:
            false_negative[str(record["rule"])] += 1
        if not label and pred_harmful:
            false_positive[str(record["rule"])] += 1
    return {
        "selected_harmful_false_negative_by_rule": dict(sorted(false_negative.items())),
        "selected_safe_false_positive_by_rule": dict(sorted(false_positive.items())),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_report(path: Path, *, root: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    global_result = summary["global_threshold"]
    per_rule = summary["per_rule_application"]
    per_family = summary["per_family_application"]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair5 Per-Rule Safety Calibration\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("## Code State\n\n")
        handle.write(f"- branch: `{git_value(['branch', '--show-current'], root)}`\n")
        handle.write(f"- commit: `{git_value(['rev-parse', '--short', 'HEAD'], root)}`\n")
        handle.write(f"- dirty: `{dirty_state(root)}`\n\n")
        handle.write("## Inputs\n\n")
        for path_text in summary["eval_csvs"]:
            handle.write(f"- `{path_text}`\n")
        handle.write(f"\n- calibration split: `{summary.get('calibration_split')}`\n")
        handle.write(f"- evaluation split: `{summary.get('evaluation_split')}`\n")
        handle.write("\n## Results\n\n")
        handle.write(
            f"- global threshold `{global_result['threshold']}`: recall `{global_result['recall']}`, "
            f"precision `{global_result['precision']}`, passed `{global_result['passed']}`\n"
        )
        handle.write(
            f"- per-rule application: recall `{per_rule['recall']}`, precision `{per_rule['precision']}`, "
            f"passed `{per_rule['passed']}`\n"
        )
        handle.write(
            f"- per-family application: recall `{per_family['recall']}`, precision `{per_family['precision']}`, "
            f"passed `{per_family['passed']}`\n\n"
        )
        handle.write("## Boundary\n\n")
        handle.write(
            "This report calibrates offline harmful-rule probabilities only. It does not lower gates and does not allow runtime.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-csv", action="append", type=Path, default=[])
    parser.add_argument("--summary-json", type=Path, default=Path("outputs/reports/phase4f_repair5_per_rule_safety_calibration.json"))
    parser.add_argument("--report", type=Path, default=Path("outputs/reports/phase4f_repair5_per_rule_safety_calibration.md"))
    parser.add_argument("--thresholds-csv", type=Path, default=Path("outputs/tables/phase4f_repair5_per_rule_safety_thresholds.csv"))
    parser.add_argument(
        "--comparison-report",
        type=Path,
        default=Path("outputs/reports/phase4f_repair5_safety_calibration_comparison.md"),
    )
    parser.add_argument("--calibration-split", default="train")
    parser.add_argument("--eval-split", default="validation")
    parser.add_argument("--min-recall", type=float, default=0.80)
    parser.add_argument("--min-precision", type=float, default=0.30)
    parser.add_argument("--threshold", action="append", type=float, default=[])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    paths = [resolve_existing(path, root) for path in args.eval_csv]
    if not paths:
        paths = [default_eval_csv(root)]
    thresholds = sorted(set(args.threshold or DEFAULT_THRESHOLDS))
    calibration_items, _calibration_selected = load_items(paths, split=str(args.calibration_split))
    eval_items, selected_records = load_items(paths, split=str(args.eval_split))
    if not calibration_items:
        raise ValueError(f"no {args.calibration_split} harmful_probs/harmful_labels rows found")
    if not eval_items:
        raise ValueError(f"no {args.eval_split} harmful_probs/harmful_labels rows found")

    global_calibration = choose_threshold(
        calibration_items,
        thresholds,
        min_recall=args.min_recall,
        min_precision=args.min_precision,
    )
    global_thresholds = {"global": float(global_calibration["threshold"])}
    global_application = apply_group_thresholds(
        eval_items,
        global_thresholds,
        group_key="rule",
        min_recall=args.min_recall,
        min_precision=args.min_precision,
    )
    global_result = {
        "threshold": float(global_calibration["threshold"]),
        **global_application,
        "calibration": global_calibration,
    }

    by_rule: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in calibration_items:
        by_rule[str(item["rule"])].append(item)
        by_family[str(item["family"])].append(item)

    threshold_rows: list[dict[str, Any]] = []
    global_row = {"scope": "global", "group": "global", **global_result}
    threshold_rows.append(global_row)

    per_rule_thresholds: dict[str, float] = {}
    for rule in EXECUTABLE_RULE_IDS:
        result = choose_threshold(by_rule[rule], thresholds, min_recall=args.min_recall, min_precision=args.min_precision)
        per_rule_thresholds[rule] = float(result["threshold"])
        threshold_rows.append({"scope": "rule", "group": rule, **result})

    per_family_thresholds: dict[str, float] = {}
    for family in sorted(by_family):
        result = choose_threshold(
            by_family[family],
            thresholds,
            min_recall=args.min_recall,
            min_precision=args.min_precision,
        )
        per_family_thresholds[family] = float(result["threshold"])
        threshold_rows.append({"scope": "family", "group": family, **result})

    per_rule_application = apply_group_thresholds(
        eval_items,
        per_rule_thresholds,
        group_key="rule",
        min_recall=args.min_recall,
        min_precision=args.min_precision,
    )
    per_family_application = apply_group_thresholds(
        eval_items,
        per_family_thresholds,
        group_key="family",
        min_recall=args.min_recall,
        min_precision=args.min_precision,
    )
    selected_global = selected_distribution(selected_records, global_thresholds, group_key="rule")
    selected_rule = selected_distribution(selected_records, per_rule_thresholds, group_key="rule")
    selected_family = selected_distribution(selected_records, per_family_thresholds, group_key="family")

    write_csv(
        root / args.thresholds_csv,
        threshold_rows,
        [
            "scope",
            "group",
            "threshold",
            "tp",
            "fp",
            "tn",
            "fn",
            "recall",
            "precision",
            "f1",
            "support",
            "positive_count",
            "negative_count",
            "passed",
            "selection_reason",
        ],
    )

    summary = {
        "schema_version": "phase4f_repair5b_per_rule_safety_calibration_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "eval_csvs": [str(path) for path in paths],
        "calibration_split": str(args.calibration_split),
        "evaluation_split": str(args.eval_split),
        "calibration_support": len(calibration_items),
        "evaluation_support": len(eval_items),
        "threshold_grid": thresholds,
        "targets": {
            "harmful_recall_min": args.min_recall,
            "harmful_precision_min": args.min_precision,
        },
        "global_threshold": global_result,
        "global_calibration": global_calibration,
        "threshold_by_rule": per_rule_thresholds,
        "threshold_by_family": per_family_thresholds,
        "per_rule_application": per_rule_application,
        "per_family_application": per_family_application,
        "selected_false_negative_distribution": {
            "global": selected_global,
            "per_rule": selected_rule,
            "per_family": selected_family,
        },
        "global_threshold_pass": bool(global_result["passed"]),
        "per_rule_threshold_pass": bool(per_rule_application["passed"]),
        "per_family_threshold_pass": bool(per_family_application["passed"]),
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    summary_path = root / args.summary_json
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    write_report(root / args.report, root=root, summary=summary)
    write_report(root / args.comparison_report, root=root, summary=summary)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

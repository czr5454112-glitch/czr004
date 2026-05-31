"""Distill the frozen Repair5D composite into the existing diagnostic MLP runtime.

This is a transfer-test bridge only. It trains a small LAU-MLP-v1 to imitate
the frozen Repair5D composite decisions on checkpoint-level features that the
current C++ LAUR runtime can compute.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))

from czr004_teacher.features_laur import FEATURE_NAMES  # noqa: E402
from czr004_teacher.stable_attention_tokens_laur import EXECUTABLE_RULE_IDS  # noqa: E402
from eval.eval_laur_repair5_composite_inference import (  # noqa: E402
    DEFAULT_DATASET,
    composite_records,
    load_eval_rows,
    load_json,
    load_label_rows,
)
from eval.repair5d_composite_spec import load_composite_spec, repo_root, resolve_path  # noqa: E402
from export_phase5_laur_mlp_runtime import export_runtime_dir  # noqa: E402
from models.laur_ltm import LaurMlpV1, write_laur_mlp_exports  # noqa: E402

try:
    import torch
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyTorch is required for Repair5D diagnostic distillation") from exc


DEFAULT_SPEC = "outputs/reports/phase4f_repair5d_best_composite_spec.json"
DEFAULT_OUTPUT_DIR = "artifacts/models/laur_ltm/repair5d_composite_distilled"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5d_composite_distill_report.md"
DEFAULT_SUMMARY_JSON = "outputs/reports/phase5p5_repair5d_composite_distill_summary.json"
DEFAULT_DECISIONS_CSV = "outputs/tables/phase5p5_repair5d_composite_distill_decisions.csv"

DISTILL_FEATURE_NAMES = [
    "agents",
    "free_cells",
    "density",
    "map_width",
    "map_height",
    "obstacle_ratio",
    "iteration",
    "has_solution_before",
    "best_ratio_before",
    "improved_last_iteration",
    "returned_solutions_count_so_far",
    "committed_count",
    "blocked_count",
    "wait_event_count",
    "goal_wait_ignored_count",
    "blocked_per_committed",
    "wait_per_committed",
    "blocked_per_agent",
    "committed_per_agent",
    "nonzero_edges_before",
    "max_raw_before",
    "entropy_edge_usage",
    "weight_entropy",
]

ATTENTION_TO_RUNTIME_FEATURES = {
    "agents": "agents",
    "density": "density",
    "map_width": "map_width",
    "map_height": "map_height",
    "obstacle_ratio": "obstacle_ratio",
    "iteration": "iteration",
    "has_solution_before": "has_incumbent_before_update",
    "best_ratio_before": "best_ratio_before_update",
    "improved_last_iteration": "improved_this_iteration",
    "returned_solutions_count_so_far": "returned_solutions_count_so_far",
    "committed_count": "committed_count",
    "blocked_count": "blocked_count",
    "wait_event_count": "wait_event_count",
    "goal_wait_ignored_count": "goal_wait_ignored_count",
    "blocked_per_committed": "blocked_per_committed",
    "wait_per_committed": "wait_per_committed",
    "nonzero_edges_before": "traffic_before_nonzero_edges",
    "max_raw_before": "traffic_before_max_raw",
    "entropy_edge_usage": "traffic_after_additive_estimated_entropy",
    "weight_entropy": "traffic_before_entropy",
}


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


def finite(value: Any, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def feature_lookup(row: dict[str, Any]) -> dict[str, float]:
    names = [str(name) for name in row.get("global_feature_names", [])]
    values = list(row.get("global_features", []))
    return {name: finite(values[index]) for index, name in enumerate(names) if index < len(values)}


def runtime_feature_vector(row: dict[str, Any]) -> list[float]:
    lookup = feature_lookup(row)
    agents = finite(lookup.get("agents"))
    density = finite(lookup.get("density"))
    committed = finite(lookup.get("committed_count"))
    blocked = finite(lookup.get("blocked_count"))
    free_cells = agents / density if density > 0.0 else 0.0
    vector: dict[str, float] = {
        name: finite(lookup.get(source_name))
        for name, source_name in ATTENTION_TO_RUNTIME_FEATURES.items()
    }
    vector.update(
        {
            "free_cells": free_cells,
            "node_budget": finite(row.get("node_budget"), 0.0),
            "elapsed_ms": finite(row.get("elapsed_ms"), 0.0),
            "time_remaining_sec": finite(row.get("time_remaining_sec"), 0.0),
            "max_iterations": finite(row.get("max_iterations"), 4.0),
            "blocked_per_agent": blocked / agents if agents else 0.0,
            "committed_per_agent": committed / agents if agents else 0.0,
            "mean_topk_raw_before": finite(lookup.get("traffic_before_max_raw"), 0.0),
            "max_weight_before": 0.0,
            "topk_raw_delta_mean": 0.0,
            "topk_raw_delta_max": 0.0,
            "new_nonzero_edges_count": 0.0,
            "topk_blocked_edge_concentration": 0.0,
            "local_degree_mean_topk": 0.0,
            "current_additive_max_normalized_weight": 0.0,
            "saturated_edge_count": 0.0,
        }
    )
    return [finite(vector.get(name)) for name in FEATURE_NAMES]


def selected_runtime_feature_vector(row: dict[str, Any], names: list[str]) -> list[float]:
    full = runtime_feature_vector(row)
    by_name = {name: full[index] for index, name in enumerate(FEATURE_NAMES)}
    return [by_name[name] for name in names]


def feature_stats(matrix: list[list[float]]) -> tuple[list[float], list[float]]:
    dim = len(matrix[0]) if matrix else 0
    mean = [sum(row[col] for row in matrix) / len(matrix) for col in range(dim)]
    std: list[float] = []
    for col in range(dim):
        var = sum((row[col] - mean[col]) ** 2 for row in matrix) / len(matrix)
        value = math.sqrt(max(0.0, var))
        std.append(value if value > 1.0e-12 else 1.0)
    return mean, std


def standardize(matrix: list[list[float]], mean: list[float], std: list[float]) -> list[list[float]]:
    return [[(value - mean[col]) / std[col] for col, value in enumerate(row)] for row in matrix]


def records_for_split(
    *,
    dataset: Path,
    spec: dict[str, Any],
    split: str,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    labels = load_label_rows(dataset, split=split)
    ranking_rows = load_eval_rows(Path(spec["ranking_csv"]), split=split)
    safety_rows = load_eval_rows(Path(spec["safety_csv"]), split=split)
    anti_rows = load_eval_rows(Path(spec["anti_csv"]), split=split)
    _metrics, records = composite_records(
        labels=labels,
        ranking_rows=ranking_rows,
        safety_rows=safety_rows,
        anti_rows=anti_rows,
        calibration=load_json(Path(spec["safety_calibration"])),
        modes=[str(spec["composite_mode"])],
        top_k=int(spec["top_k"]),
        default_threshold=float(spec.get("default_threshold", 0.35)),
        opportunity_threshold=float(spec.get("opportunity_threshold", 0.50)),
        defer_threshold=float(spec.get("defer_threshold", 0.50)),
    )
    by_id = {str(row["checkpoint_id"]): row for row in labels.values()}
    return by_id, records


def build_examples(
    label_rows: dict[str, dict[str, Any]],
    records: list[dict[str, Any]],
    *,
    feature_names: list[str],
) -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for record in records:
        checkpoint_id = str(record["checkpoint_id"])
        label_row = label_rows.get(checkpoint_id)
        if label_row is None:
            continue
        selected_rule = str(record["selected_rule"])
        if selected_rule not in EXECUTABLE_RULE_IDS:
            selected_rule = "additive_ltm"
        examples.append(
            {
                "checkpoint_id": checkpoint_id,
                "split": str(record["split"]),
                "map_name": str(record.get("map_name", "")),
                "agents": int(record.get("agents") or 0),
                "seed": int(record.get("seed") or 0),
                "iteration": int(record.get("iteration") or 0),
                "selected_rule": selected_rule,
                "selected_rule_index": EXECUTABLE_RULE_IDS.index(selected_rule),
                "selected_decision": str(record["selected_decision"]),
                "selected_rule_harmful": bool(record["selected_rule_harmful"]),
                "selected_vs_additive_delta": finite(record["selected_vs_additive_delta"]),
                "feature_vector": selected_runtime_feature_vector(label_row, feature_names),
            }
        )
    return examples


def evaluate(
    model: LaurMlpV1,
    examples: list[dict[str, Any]],
    *,
    mean: list[float],
    std: list[float],
    device: torch.device,
    harmful_threshold: float,
) -> dict[str, Any]:
    if not examples:
        return {"sample_count": 0}
    matrix = standardize([row["feature_vector"] for row in examples], mean, std)
    x = torch.tensor(matrix, dtype=torch.float32, device=device)
    with torch.no_grad():
        out = model(x)
        rule_logits = out["rule_logits"].detach().cpu().tolist()
        harmful_probs = torch.sigmoid(out["safety_logit"]).detach().cpu().tolist()
    preds = [max(range(len(row)), key=lambda index: row[index]) for row in rule_logits]
    targets = [int(row["selected_rule_index"]) for row in examples]
    harmful_targets = [1 if row["selected_rule_harmful"] else 0 for row in examples]
    harmful_pred = [1 if finite(prob) >= harmful_threshold else 0 for prob in harmful_probs]
    tp = sum(1 for label, pred in zip(harmful_targets, harmful_pred) if label == 1 and pred == 1)
    fp = sum(1 for label, pred in zip(harmful_targets, harmful_pred) if label == 0 and pred == 1)
    fn = sum(1 for label, pred in zip(harmful_targets, harmful_pred) if label == 1 and pred == 0)
    nonadditive = {rule for rule in EXECUTABLE_RULE_IDS if rule != "additive_ltm"}
    return {
        "sample_count": len(examples),
        "rule_top1": sum(1 for pred, target in zip(preds, targets) if pred == target) / len(examples),
        "target_non_additive_rate": sum(1 for row in examples if row["selected_rule"] in nonadditive) / len(examples),
        "predicted_non_additive_rate": sum(1 for pred in preds if EXECUTABLE_RULE_IDS[pred] in nonadditive) / len(examples),
        "target_additive_or_defer_rate": sum(
            1
            for row in examples
            if row["selected_rule"] == "additive_ltm" or row["selected_decision"] == "defer_ltm"
        )
        / len(examples),
        "target_selected_harmful_rate": sum(harmful_targets) / len(examples),
        "harmful_precision": tp / (tp + fp) if tp + fp else 0.0,
        "harmful_recall": tp / (tp + fn) if tp + fn else 0.0,
        "predicted_rule_distribution": dict(sorted(Counter(EXECUTABLE_RULE_IDS[pred] for pred in preds).items())),
        "target_rule_distribution": dict(sorted(Counter(row["selected_rule"] for row in examples).items())),
    }


def write_decisions_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "checkpoint_id",
        "split",
        "map_name",
        "agents",
        "seed",
        "iteration",
        "selected_rule",
        "selected_decision",
        "selected_rule_harmful",
        "selected_vs_additive_delta",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, *, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5D Composite Distill Diagnostic\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("This is diagnostic-only distillation into the existing LAUR MLP runtime format. It does not permit Phase5.5 or Phase6.\n\n")
        handle.write("## Outputs\n\n")
        for key in ("weights_json", "runtime_dir", "decisions_csv"):
            handle.write(f"- {key}: `{summary.get(key)}`\n")
        handle.write("\n## Metrics\n\n")
        for split in ("train", "validation"):
            metrics = summary["metrics"].get(split, {})
            handle.write(f"### {split}\n\n")
            for key, value in metrics.items():
                handle.write(f"- {key}: `{value}`\n")
            handle.write("\n")
        handle.write("## Boundary\n\n")
        handle.write("- phase5p5_allowed: `False`\n")
        handle.write("- phase6_allowed: `False`\n")
        handle.write("- This is a temporary transfer-test bridge, not a formal Repair5D native export.\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec-json", type=Path, default=Path(DEFAULT_SPEC))
    parser.add_argument("--dataset", type=Path, default=Path(DEFAULT_DATASET))
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY_JSON))
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--decisions-csv", type=Path, default=Path(DEFAULT_DECISIONS_CSV))
    parser.add_argument("--epochs", type=int, default=500)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=3.0e-3)
    parser.add_argument("--weight-decay", type=float, default=1.0e-4)
    parser.add_argument("--seed", type=int, default=61)
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda", "auto"])
    parser.add_argument("--harmful-threshold", type=float, default=0.30)
    parser.add_argument("--feature-names", nargs="+", default=list(DISTILL_FEATURE_NAMES))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    spec_path = resolve_path(args.spec_json, root)
    dataset = resolve_path(args.dataset, root)
    output_dir = resolve_path(args.output_dir, root)
    summary_json = resolve_path(args.summary_json, root)
    report = resolve_path(args.report, root)
    decisions_csv = resolve_path(args.decisions_csv, root)
    if None in (spec_path, dataset, output_dir, summary_json, report, decisions_csv):
        raise ValueError("required paths could not be resolved")
    assert spec_path and dataset and output_dir and summary_json and report and decisions_csv

    spec = load_composite_spec(spec_path)
    train_labels, train_records = records_for_split(dataset=dataset, spec=spec, split="train")
    val_labels, val_records = records_for_split(dataset=dataset, spec=spec, split="validation")
    feature_names = [str(name) for name in args.feature_names]
    missing_features = sorted(set(feature_names) - set(FEATURE_NAMES))
    if missing_features:
        raise ValueError(f"unsupported runtime feature names: {missing_features}")
    train_examples = build_examples(train_labels, train_records, feature_names=feature_names)
    val_examples = build_examples(val_labels, val_records, feature_names=feature_names)
    if not train_examples:
        raise ValueError("no train examples available for distillation")
    if not val_examples:
        raise ValueError("no validation examples available for distillation")

    torch.manual_seed(int(args.seed))
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    matrix = [row["feature_vector"] for row in train_examples]
    mean, std = feature_stats(matrix)
    x_train = torch.tensor(standardize(matrix, mean, std), dtype=torch.float32, device=device)
    y_rule = torch.tensor([row["selected_rule_index"] for row in train_examples], dtype=torch.long, device=device)
    y_harmful = torch.tensor([1.0 if row["selected_rule_harmful"] else 0.0 for row in train_examples], dtype=torch.float32, device=device)
    y_delta = torch.tensor([row["selected_vs_additive_delta"] for row in train_examples], dtype=torch.float32, device=device)

    model = LaurMlpV1(len(feature_names), len(EXECUTABLE_RULE_IDS), hidden_dim=int(args.hidden_dim)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(args.learning_rate), weight_decay=float(args.weight_decay))
    final_loss = 0.0
    for _epoch in range(int(args.epochs)):
        optimizer.zero_grad(set_to_none=True)
        out = model(x_train)
        rule_loss = torch.nn.functional.cross_entropy(out["rule_logits"], y_rule)
        safety_loss = torch.nn.functional.binary_cross_entropy_with_logits(out["safety_logit"], y_harmful)
        delta_loss = torch.nn.functional.smooth_l1_loss(out["delta_pred"], y_delta)
        loss = rule_loss + 0.25 * safety_loss + 0.05 * delta_loss
        loss.backward()
        optimizer.step()
        final_loss = float(loss.detach().cpu())

    model.eval()
    metrics = {
        "train": evaluate(
            model,
            train_examples,
            mean=mean,
            std=std,
            device=device,
            harmful_threshold=float(args.harmful_threshold),
        ),
        "validation": evaluate(
            model,
            val_examples,
            mean=mean,
            std=std,
            device=device,
            harmful_threshold=float(args.harmful_threshold),
        ),
    }

    metadata = {
        "created_at": datetime.now().isoformat(),
        "source_spec": str(spec_path),
        "dataset": str(dataset),
        "schema_version": "repair5d_composite_distill_v1",
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "epochs": int(args.epochs),
        "hidden_dim": int(args.hidden_dim),
        "learning_rate": float(args.learning_rate),
        "weight_decay": float(args.weight_decay),
        "seed": int(args.seed),
        "input_features": feature_names,
    }
    paths = write_laur_mlp_exports(
        model,
        output_dir=output_dir,
        input_features=feature_names,
        feature_mean=mean,
        feature_std=std,
        rules=list(EXECUTABLE_RULE_IDS),
        metadata=metadata,
    )
    export_runtime_dir(paths["weights"], output_dir)
    write_decisions_csv(decisions_csv, train_examples + val_examples)

    summary = {
        "schema_version": "phase5p5_repair5d_composite_distill_v1",
        "created_at": datetime.now().isoformat(),
        "branch": git_value(["branch", "--show-current"], root),
        "commit": git_value(["rev-parse", "--short", "HEAD"], root),
        "dirty": dirty_state(root),
        "source_spec": str(spec_path),
        "dataset": str(dataset),
        "weights_json": str(paths["weights"]),
        "runtime_dir": str(output_dir),
        "decisions_csv": str(decisions_csv),
        "train_samples": len(train_examples),
        "validation_samples": len(val_examples),
        "feature_names": feature_names,
        "final_loss": final_loss,
        "metrics": metrics,
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary=summary)
    print(json.dumps({"runtime_dir": str(output_dir), "summary_json": str(summary_json), "report": str(report)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

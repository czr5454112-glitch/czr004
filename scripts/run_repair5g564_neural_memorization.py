from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR, G560_TRAINING_ROWS  # noqa: E402
from gcst.rich_actor_training_g564 import load_rich_set_examples, rich_prediction_sensitivity, train_rich  # noqa: E402


ROUND = "phase5p5_repair5g564"
REPORTS = ROOT / "outputs/reports"
TABLES = ROOT / "outputs/tables"


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run G5.64 rich graph-actor memorization probe.")
    parser.add_argument("--rows-path", type=Path, default=G560_TRAINING_ROWS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--max-contexts", type=int, default=48)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--lr", type=float, default=5.0e-4)
    parser.add_argument("--hidden-dim", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--seed", type=int, default=564)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args(argv)

    import torch

    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    examples = load_rich_set_examples(resolve(args.rows_path), resolve(args.context_dir), max_contexts=args.max_contexts)
    examples = [ex for ex in examples if len(ex.label_context.positive_candidates) or len(ex.label_context.harmful_candidates)]
    if len(examples) < 4:
        raise SystemExit("need at least four labeled contexts for G5.64 neural memorization")
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    sensitivity: dict[str, float] = {}
    for subset_size in [1, 4]:
        subset = examples[:subset_size]
        model, metrics = train_rich(
            subset,
            subset,
            seed=args.seed + subset_size,
            steps=args.steps,
            lr=args.lr,
            hidden_dim=args.hidden_dim,
            batch_size=min(args.batch_size, subset_size),
            device=device,
        )
        row = {
            "subset_size": subset_size,
            "train_contexts": subset_size,
            "validation_contexts": subset_size,
            **metrics,
        }
        rows.append(row)
        if subset_size == 4:
            sensitivity = rich_prediction_sensitivity(model, subset, device=device)
    branch_keys = [
        "topology_grad_norm",
        "c0_grad_norm",
        "f0_grad_norm",
        "od_grad_norm",
        "scalar_grad_norm",
        "theta_head_grad_norm",
    ]
    four = next(row for row in rows if row["subset_size"] == 4)
    branches_receive_gradients = all(float(four.get(key, 0.0)) > 0.0 for key in branch_keys)
    loss_improved = all(float(row["final_validation_loss"]) < float(row["initial_validation_loss"]) for row in rows)
    interventions_effect = any(float(sensitivity.get(key, 0.0)) > 1.0e-7 for key in sensitivity)
    passed = bool(loss_improved and branches_receive_gradients and interventions_effect)
    summary = {
        "schema_version": f"{ROUND}_neural_memorization_summary_v1",
        "decision": "g564_neural_memorization_passed" if passed else "g564_neural_memorization_failed_architecture_or_batching",
        "device": device,
        "max_contexts_loaded": args.max_contexts,
        "eligible_contexts": len(examples),
        "steps": args.steps,
        "seed": args.seed,
        "rich_actor_used": True,
        "scalar_model_is_primary": False,
        "loss_improved_one_and_four_contexts": loss_improved,
        "branches_receive_gradients": branches_receive_gradients,
        "od_shuffle_changes_prediction": float(sensitivity.get("od_shuffle_mean_abs_theta_delta", 0.0)) > 1.0e-7,
        "c0_f0_interventions_change_prediction": float(sensitivity.get("c0_zero_mean_abs_theta_delta", 0.0))
        + float(sensitivity.get("f0_zero_mean_abs_theta_delta", 0.0))
        > 1.0e-7,
        **sensitivity,
        "elapsed_sec": time.perf_counter() - started,
    }
    write_rows(TABLES / f"{ROUND}_neural_memorization_branch_gradient_audit.csv", rows)
    write_json(REPORTS / f"{ROUND}_neural_memorization_summary.json", summary)
    print(json.dumps({"decision": summary["decision"], "device": device, "eligible_contexts": len(examples)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.label_v52_set import LabelV52Context, context_manifest_row, contexts_from_groups  # noqa: E402
from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR, G560_TRAINING_ROWS, load_label_groups  # noqa: E402
from gcst.run_provenance import append_progress, new_run_uid, progress_path, read_progress, summary_matches_progress  # noqa: E402
from gcst.scaling_dataset import (  # noqa: E402
    assert_split_hashes_disjoint,
    fixed_validation_ids,
    make_grouped_split_manifest,
    nested_stratified_subsets,
    validation_manifest_sha256,
)
from gcst.set_valued_actor_losses import set_valued_actor_loss  # noqa: E402
from gcst.theta_schema import THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS  # noqa: E402


ROUND = "phase5p5_repair5g563"
SUMMARY_JSON = Path(f"outputs/reports/{ROUND}_scaling_study_summary.json")
RESULTS_CSV = Path(f"outputs/tables/{ROUND}_scaling_study_results.csv")


FEATURES = [
    "agent_count",
    "budget_ms",
    "original_row_count",
    "positive_rows",
    "safe_rows",
    "harmful_rows",
    "censored_rows",
]


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_rows(path: str | Path, rows: list[dict[str, Any]]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with p.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def context_features(context: LabelV52Context) -> np.ndarray:
    row = context_manifest_row(context)
    values = [float(row.get(name, 0.0) or 0.0) for name in FEATURES]
    values[0] = values[0] / 256.0
    values[1] = values[1] / 10000.0
    for idx in range(2, len(values)):
        values[idx] = math.log1p(max(0.0, values[idx]))
    return np.asarray(values, dtype=np.float32)


def make_loss_item(context: LabelV52Context) -> dict[str, Any]:
    return {
        "label_state": context.label_state,
        "positive_thetas": context.positive_thetas,
        "harmful_thetas": context.harmful_thetas,
        "safe_thetas": context.safe_thetas,
        "positive_weights": context.positive_weights,
        "harmful_weights": context.harmful_weights,
    }


def train_scalar_model(
    train_contexts: list[LabelV52Context],
    valid_contexts: list[LabelV52Context],
    *,
    seed: int,
    steps: int,
    lr: float,
    hidden_dim: int,
    device: str,
) -> dict[str, float]:
    import torch

    torch.manual_seed(seed)
    lo = torch.tensor(THETA_LO, dtype=torch.float32, device=device)
    hi = torch.tensor(THETA_HI, dtype=torch.float32, device=device)
    model = torch.nn.Sequential(
        torch.nn.Linear(len(FEATURES), hidden_dim),
        torch.nn.SiLU(),
        torch.nn.Linear(hidden_dim, hidden_dim),
        torch.nn.SiLU(),
        torch.nn.Linear(hidden_dim, len(THETA_NUMERIC_COLUMNS)),
    ).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1.0e-4)
    train_x = torch.tensor(np.stack([context_features(context) for context in train_contexts]), dtype=torch.float32, device=device)
    train_items = [make_loss_item(context) for context in train_contexts]
    valid_x = torch.tensor(np.stack([context_features(context) for context in valid_contexts]), dtype=torch.float32, device=device)
    valid_items = [make_loss_item(context) for context in valid_contexts]

    def eval_loss(x, items) -> float:
        model.eval()
        with torch.no_grad():
            pred = lo + torch.sigmoid(model(x)) * (hi - lo)
            losses = []
            for idx, item in enumerate(items):
                loss, _ = set_valued_actor_loss(
                    pred[idx],
                    label_state=item["label_state"],
                    positive_thetas=torch.tensor(item["positive_thetas"], dtype=torch.float32, device=device),
                    harmful_thetas=torch.tensor(item["harmful_thetas"], dtype=torch.float32, device=device),
                    safe_thetas=torch.tensor(item["safe_thetas"], dtype=torch.float32, device=device),
                    positive_weights=torch.tensor(item["positive_weights"], dtype=torch.float32, device=device),
                    harmful_weights=torch.tensor(item["harmful_weights"], dtype=torch.float32, device=device),
                )
                losses.append(loss)
            return float(torch.stack(losses).mean().cpu()) if losses else 0.0

    initial_valid = eval_loss(valid_x, valid_items)
    best_valid = initial_valid
    final_train = 0.0
    for _step in range(1, steps + 1):
        model.train()
        pred = lo + torch.sigmoid(model(train_x)) * (hi - lo)
        losses = []
        for idx, item in enumerate(train_items):
            loss, _ = set_valued_actor_loss(
                pred[idx],
                label_state=item["label_state"],
                positive_thetas=torch.tensor(item["positive_thetas"], dtype=torch.float32, device=device),
                harmful_thetas=torch.tensor(item["harmful_thetas"], dtype=torch.float32, device=device),
                safe_thetas=torch.tensor(item["safe_thetas"], dtype=torch.float32, device=device),
                positive_weights=torch.tensor(item["positive_weights"], dtype=torch.float32, device=device),
                harmful_weights=torch.tensor(item["harmful_weights"], dtype=torch.float32, device=device),
            )
            losses.append(loss)
        train_loss = torch.stack(losses).mean()
        opt.zero_grad(set_to_none=True)
        train_loss.backward()
        opt.step()
        final_train = float(train_loss.detach().cpu())
        if _step % max(1, steps // 5) == 0 or _step == steps:
            best_valid = min(best_valid, eval_loss(valid_x, valid_items))
    final_valid = eval_loss(valid_x, valid_items)
    return {
        "initial_validation_loss": initial_valid,
        "best_validation_loss": best_valid,
        "final_validation_loss": final_valid,
        "final_train_loss": final_train,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run G5.63 nested current-data scaling study.")
    parser.add_argument("--rows-path", type=Path, default=G560_TRAINING_ROWS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--max-contexts", type=int, default=512)
    parser.add_argument("--sizes", default="32,64,128,256")
    parser.add_argument("--seeds", default="563,564,565")
    parser.add_argument("--steps", type=int, default=150)
    parser.add_argument("--lr", type=float, default=1.0e-3)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args(argv)

    import torch

    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    groups = load_label_groups(resolve(args.rows_path), resolve(args.context_dir), max_contexts=args.max_contexts)
    contexts = contexts_from_groups(groups)
    by_uid = {context.evaluation_uid: context for context in contexts}
    manifest = [context_manifest_row(context) for context in contexts]
    split_rows = make_grouped_split_manifest(manifest, seed=563)
    assert_split_hashes_disjoint(split_rows)
    train_rows = [row for row in split_rows if row["g563_split"] == "train" and row["evaluation_uid"] in by_uid]
    valid_ids = fixed_validation_ids(split_rows)
    valid_contexts = [by_uid[uid] for uid in valid_ids if uid in by_uid]
    if not train_rows or not valid_contexts:
        raise SystemExit("grouped split did not produce train and validation contexts")
    sizes = [int(token) for token in args.sizes.split(",") if token.strip()]
    seeds = [int(token) for token in args.seeds.split(",") if token.strip()]
    nested = nested_stratified_subsets(train_rows, sizes, seed=563)
    run_uid = new_run_uid(ROUND, "scaling")
    pfile = progress_path(ROOT, ROUND, run_uid)
    append_progress(pfile, run_uid, {"event": "start", "contexts": len(contexts), "dataset_count": len(contexts), "device": device})
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    for size in sorted(nested):
        subset_ids = nested[size]
        train_contexts = [by_uid[uid] for uid in subset_ids if uid in by_uid]
        if not train_contexts:
            continue
        for seed in seeds:
            metrics = train_scalar_model(
                train_contexts,
                valid_contexts,
                seed=seed,
                steps=args.steps,
                lr=args.lr,
                hidden_dim=args.hidden_dim,
                device=device,
            )
            row = {
                "run_uid": run_uid,
                "method": "scalar_context_set_mlp_control",
                "size": len(train_contexts),
                "seed": seed,
                "steps": args.steps,
                "context_presentations": len(train_contexts) * args.steps,
                "fixed_validation_contexts": len(valid_contexts),
                "fixed_validation_manifest_sha256": validation_manifest_sha256(valid_ids),
                **metrics,
            }
            rows.append(row)
            append_progress(pfile, run_uid, {"event": "scaling_row", **row})
    by_size: dict[int, list[float]] = {}
    for row in rows:
        by_size.setdefault(int(row["size"]), []).append(float(row["best_validation_loss"]))
    medians = {size: float(np.median(values)) for size, values in sorted(by_size.items())}
    ordered_sizes = sorted(medians)
    monotone_improvement = sum(
        medians[right] <= medians[left] for left, right in zip(ordered_sizes, ordered_sizes[1:])
    )
    positive_slope = bool(len(ordered_sizes) >= 3 and medians[ordered_sizes[-1]] < medians[ordered_sizes[0]])
    summary = {
        "schema_version": f"{ROUND}_scaling_study_summary_v1",
        "decision": "g563_validation_loss_scales_with_context_count" if positive_slope else "g563_validation_loss_flat_label_or_representation_blocker",
        "run_uid": run_uid,
        "progress_jsonl": str(pfile.relative_to(ROOT)).replace("\\", "/"),
        "device": device,
        "contexts": len(contexts),
        "dataset_count": len(contexts),
        "train_contexts_available": len(train_rows),
        "fixed_validation_contexts": len(valid_contexts),
        "fixed_validation_manifest_sha256": validation_manifest_sha256(valid_ids),
        "sizes": ordered_sizes,
        "median_best_validation_loss_by_size": medians,
        "nonincreasing_adjacent_steps": monotone_improvement,
        "scaling_positive": positive_slope,
        "results_rows": len(rows),
        "elapsed_sec": time.perf_counter() - started,
    }
    progress_rows = read_progress(pfile, run_uid)
    summary_matches_progress(summary, progress_rows)
    write_rows(RESULTS_CSV, rows)
    write_json(SUMMARY_JSON, summary)
    print(json.dumps({"decision": summary["decision"], "sizes": ordered_sizes, "rows": len(rows)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

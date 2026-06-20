from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.label_v52_set import contexts_from_groups  # noqa: E402
from gcst.loss_geometry_g564 import (  # noqa: E402
    adaptive_harmful_margin,
    conflicting_theta_pairs,
    floor_corrected_positive_loss_np,
    nearest_harmful_repulsion_loss_np,
    positive_softmin_floor,
    positive_wta_loss_np,
    theta_row,
)
from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR, G560_TRAINING_ROWS, load_label_groups  # noqa: E402
from gcst.theta_schema import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS  # noqa: E402


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


def torch_context_loss(theta, context, device: str, tau: float):
    import torch

    span = torch.as_tensor(THETA_HI - THETA_LO, dtype=theta.dtype, device=device).clamp_min(1.0e-6)
    total = theta.sum() * 0.0
    if len(context.positive_candidates):
        pos = torch.as_tensor(context.positive_thetas, dtype=theta.dtype, device=device)
        weights = torch.as_tensor(context.positive_weights, dtype=theta.dtype, device=device)
        weights = weights / weights.sum().clamp_min(1.0e-12)
        distances = torch.mean(torch.abs((theta.view(1, -1) - pos) / span), dim=-1)
        raw = -float(tau) * torch.logsumexp(torch.log(weights.clamp_min(1.0e-12)) - distances / float(tau), dim=0)
        floor = positive_softmin_floor(context.positive_thetas, context.positive_weights, tau=tau)
        total = total + torch.relu(raw - float(floor))
    if len(context.harmful_candidates):
        harm = torch.as_tensor(context.harmful_thetas, dtype=theta.dtype, device=device)
        distances = torch.mean(torch.abs((theta.view(1, -1) - harm) / span), dim=-1)
        margin = adaptive_harmful_margin(context.positive_thetas, context.harmful_thetas).feasible_margin
        total = total + torch.relu(float(margin) - distances.min())
    if not len(context.positive_candidates):
        anchor = torch.as_tensor(BASELINE_G556, dtype=theta.dtype, device=device)
        total = total + 0.01 * torch.mean(torch.abs((theta - anchor) / span))
    return total


def metric_loss(theta: np.ndarray, context, tau: float) -> dict[str, float]:
    positive = (
        max(0.0, floor_corrected_positive_loss_np(theta, context.positive_thetas, context.positive_weights, tau=tau))
        if len(context.positive_candidates)
        else 0.0
    )
    wta = positive_wta_loss_np(theta, context.positive_thetas) if len(context.positive_candidates) else 0.0
    harmful_margin = adaptive_harmful_margin(context.positive_thetas, context.harmful_thetas).feasible_margin
    harmful = nearest_harmful_repulsion_loss_np(theta, context.harmful_thetas, margin=harmful_margin)
    total = positive + harmful
    if not len(context.positive_candidates):
        span = np.maximum(THETA_HI - THETA_LO, 1.0e-6)
        total += 0.01 * float(np.mean(np.abs((theta - BASELINE_G556) / span)))
    return {
        "floor_corrected_positive_loss": float(positive),
        "wta_positive_loss": float(wta),
        "nearest_harmful_margin_loss": float(harmful),
        "total_repaired_loss": float(total),
    }


def train_context(context, *, steps: int, lr: float, seed: int, tau: float, device: str) -> dict[str, Any]:
    import torch

    torch.manual_seed(seed)
    lo = torch.as_tensor(THETA_LO, dtype=torch.float32, device=device)
    hi = torch.as_tensor(THETA_HI, dtype=torch.float32, device=device)
    theta = torch.nn.Parameter(torch.as_tensor(BASELINE_G556, dtype=torch.float32, device=device).clone())
    opt = torch.optim.AdamW([theta], lr=lr, weight_decay=0.0)
    initial = metric_loss(BASELINE_G556, context, tau)
    best_loss = initial["total_repaired_loss"]
    best_theta = BASELINE_G556.copy()
    final_loss = best_loss
    for _step in range(steps):
        opt.zero_grad(set_to_none=True)
        loss = torch_context_loss(theta, context, device, tau)
        loss.backward()
        opt.step()
        with torch.no_grad():
            theta.clamp_(lo, hi)
        arr = theta.detach().cpu().numpy().astype(np.float32)
        metrics = metric_loss(arr, context, tau)
        final_loss = metrics["total_repaired_loss"]
        if final_loss < best_loss:
            best_loss = final_loss
            best_theta = arr.copy()
    final_metrics = metric_loss(theta.detach().cpu().numpy().astype(np.float32), context, tau)
    best_metrics = metric_loss(best_theta, context, tau)
    return {
        "evaluation_uid": context.evaluation_uid,
        "label_state": context.label_state,
        "positive_rows": len(context.positive_candidates),
        "harmful_rows": len(context.harmful_candidates),
        "censored_rows": len(context.censored_candidates),
        "steps": steps,
        "lr": lr,
        "seed": seed,
        "initial_total_repaired_loss": initial["total_repaired_loss"],
        "final_total_repaired_loss": final_metrics["total_repaired_loss"],
        "best_total_repaired_loss": best_metrics["total_repaired_loss"],
        "initial_floor_corrected_positive_loss": initial["floor_corrected_positive_loss"],
        "best_floor_corrected_positive_loss": best_metrics["floor_corrected_positive_loss"],
        "initial_nearest_harmful_margin_loss": initial["nearest_harmful_margin_loss"],
        "best_nearest_harmful_margin_loss": best_metrics["nearest_harmful_margin_loss"],
        "oracle_initialized_at_g556": True,
        "optimizer": "AdamW",
        "weight_decay": 0.0,
        "uses_sigmoid_parameterization": False,
        "projected_to_theta_bounds_each_step": True,
        **theta_row(best_theta, prefix="oracle_"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run G5.64 per-context projected parameter oracle.")
    parser.add_argument("--rows-path", type=Path, default=G560_TRAINING_ROWS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--max-contexts", type=int, default=128)
    parser.add_argument("--steps", type=int, default=160)
    parser.add_argument("--lr", type=float, default=0.04)
    parser.add_argument("--seed", type=int, default=564)
    parser.add_argument("--tau", type=float, default=0.05)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args(argv)

    import torch

    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    groups = load_label_groups(resolve(args.rows_path), resolve(args.context_dir), max_contexts=args.max_contexts)
    if not groups:
        raise SystemExit("no Label-v5.1 groups with local scenario files available")
    contexts = contexts_from_groups(groups)
    started = time.perf_counter()
    rows = [train_context(context, steps=args.steps, lr=args.lr, seed=args.seed, tau=args.tau, device=device) for context in contexts]
    conflicts = [item for context in contexts for item in conflicting_theta_pairs(context)]
    initial = [float(row["initial_total_repaired_loss"]) for row in rows]
    best = [float(row["best_total_repaired_loss"]) for row in rows]
    improved = [b < i - 1.0e-6 for i, b in zip(initial, best)]
    median_initial = float(np.median(initial)) if initial else 0.0
    median_best = float(np.median(best)) if best else 0.0
    blocked_by_conflicts = bool(conflicts)
    passed = bool(rows and median_best <= median_initial * 0.75 and not blocked_by_conflicts)
    decision = (
        "g564_parameter_oracle_passed"
        if passed
        else "g564_parameter_oracle_blocked_by_conflicting_labels"
        if blocked_by_conflicts
        else "g564_parameter_oracle_failed_loss_repair"
    )
    summary = {
        "schema_version": f"{ROUND}_parameter_oracle_summary_v1",
        "decision": decision,
        "device": device,
        "contexts": len(contexts),
        "steps": args.steps,
        "seed": args.seed,
        "median_initial_total_repaired_loss": median_initial,
        "median_best_total_repaired_loss": median_best,
        "contexts_improved": int(sum(improved)),
        "improvement_rate": float(sum(improved) / max(1, len(improved))),
        "conflicting_theta_pairs": len(conflicts),
        "oracle_initialized_at_g556": True,
        "optimizer": "AdamW",
        "weight_decay": 0.0,
        "uses_sigmoid_parameterization": False,
        "projected_to_theta_bounds_each_step": True,
        "elapsed_sec": time.perf_counter() - started,
    }
    write_rows(TABLES / f"{ROUND}_loss_repair_matrix.csv", rows)
    write_rows(TABLES / f"{ROUND}_overfit_by_context.csv", rows)
    write_json(REPORTS / f"{ROUND}_parameter_oracle_summary.json", summary)
    print(json.dumps({"decision": decision, "contexts": len(contexts), "median_best": median_best}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

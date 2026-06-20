from __future__ import annotations

import argparse
import json
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.label_v52_set import LabelV52Context, contexts_from_groups  # noqa: E402
from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR, G560_TRAINING_ROWS, load_label_groups  # noqa: E402
from gcst.run_provenance import append_progress, new_run_uid, progress_path, read_progress, summary_matches_progress  # noqa: E402
from gcst.set_valued_actor_losses import positive_set_softmin_loss, set_valued_actor_loss  # noqa: E402
from gcst.theta_schema import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS  # noqa: E402


ROUND = "phase5p5_repair5g563"
SUMMARY_JSON = Path(f"outputs/reports/{ROUND}_tiny_overfit_summary.json")


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def select_contexts(contexts: list[LabelV52Context], n: int, require_harmful: bool = True) -> list[LabelV52Context]:
    eligible = [
        context
        for context in contexts
        if len(context.positive_candidates) > 0 and (not require_harmful or len(context.harmful_candidates) > 0)
    ]
    if len(eligible) < n:
        eligible = [context for context in contexts if len(context.positive_candidates) > 0]
    return eligible[:n]


def make_loss_item(context: LabelV52Context) -> dict[str, Any]:
    return {
        "label_state": context.label_state,
        "positive_thetas": context.positive_thetas,
        "harmful_thetas": context.harmful_thetas,
        "safe_thetas": context.safe_thetas,
        "positive_weights": context.positive_weights,
        "harmful_weights": context.harmful_weights,
    }


def multimodal_midpoint_check(device: str) -> dict[str, float | bool]:
    import torch

    left = torch.tensor(BASELINE_G556 - 0.2, dtype=torch.float32, device=device)
    right = torch.tensor(BASELINE_G556 + 0.2, dtype=torch.float32, device=device)
    midpoint = torch.tensor(BASELINE_G556, dtype=torch.float32, device=device)
    safe = torch.stack([left, right])
    left_loss = float(positive_set_softmin_loss(left, safe).detach().cpu())
    mid_loss = float(positive_set_softmin_loss(midpoint, safe).detach().cpu())
    return {
        "left_mode_loss": left_loss,
        "midpoint_loss": mid_loss,
        "mode_beats_midpoint": left_loss < mid_loss,
    }


@dataclass
class OverfitResult:
    initial_loss: float
    final_loss: float
    min_loss: float
    steps: int


def run_embedding_overfit(contexts: list[LabelV52Context], *, steps: int, lr: float, seed: int, device: str, progress_file: Path, run_uid: str) -> OverfitResult:
    import torch

    torch.manual_seed(seed)
    lo = torch.tensor(THETA_LO, dtype=torch.float32, device=device)
    hi = torch.tensor(THETA_HI, dtype=torch.float32, device=device)
    logits = torch.nn.Parameter(torch.zeros((len(contexts), len(THETA_NUMERIC_COLUMNS)), dtype=torch.float32, device=device))
    opt = torch.optim.AdamW([logits], lr=lr)
    items = [make_loss_item(context) for context in contexts]

    def current_loss() -> torch.Tensor:
        theta = lo + torch.sigmoid(logits) * (hi - lo)
        losses = []
        for idx, item in enumerate(items):
            loss, _terms = set_valued_actor_loss(
                theta[idx],
                label_state=item["label_state"],
                positive_thetas=torch.tensor(item["positive_thetas"], dtype=torch.float32, device=device),
                harmful_thetas=torch.tensor(item["harmful_thetas"], dtype=torch.float32, device=device),
                safe_thetas=torch.tensor(item["safe_thetas"], dtype=torch.float32, device=device),
                positive_weights=torch.tensor(item["positive_weights"], dtype=torch.float32, device=device),
                harmful_weights=torch.tensor(item["harmful_weights"], dtype=torch.float32, device=device),
            )
            losses.append(loss)
        return torch.stack(losses).mean()

    initial = float(current_loss().detach().cpu())
    best = initial
    for step in range(1, steps + 1):
        loss = current_loss()
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        best = min(best, float(loss.detach().cpu()))
        if step == 1 or step == steps or step % max(1, steps // 5) == 0:
            append_progress(progress_file, run_uid, {"event": "tiny_overfit_step", "step": step, "loss": float(loss.detach().cpu())})
    final = float(current_loss().detach().cpu())
    return OverfitResult(initial_loss=initial, final_loss=final, min_loss=best, steps=steps)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a tiny G5.63 set-valued overfit proof.")
    parser.add_argument("--rows-path", type=Path, default=G560_TRAINING_ROWS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--max-contexts", type=int, default=256)
    parser.add_argument("--overfit-contexts", type=int, default=16)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--lr", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=563)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args(argv)

    import torch

    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    groups = load_label_groups(resolve(args.rows_path), resolve(args.context_dir), max_contexts=args.max_contexts)
    contexts = contexts_from_groups(groups)
    selected = select_contexts(contexts, args.overfit_contexts, require_harmful=True)
    if not selected:
        raise SystemExit("no positive Label-v5.2 contexts available for tiny overfit")
    run_uid = new_run_uid(ROUND, "tiny_overfit")
    pfile = progress_path(ROOT, ROUND, run_uid)
    append_progress(pfile, run_uid, {"event": "start", "contexts": len(selected), "dataset_count": len(selected), "device": device})
    started = time.perf_counter()
    result = run_embedding_overfit(
        selected,
        steps=args.steps,
        lr=args.lr,
        seed=args.seed,
        device=device,
        progress_file=pfile,
        run_uid=run_uid,
    )
    midpoint = multimodal_midpoint_check(device)
    reduction = (result.initial_loss - result.final_loss) / max(1.0e-12, result.initial_loss)
    passed = result.final_loss < result.initial_loss * 0.50 and bool(midpoint["mode_beats_midpoint"])
    summary = {
        "schema_version": f"{ROUND}_tiny_overfit_summary_v1",
        "decision": "g563_tiny_overfit_passed" if passed else "g563_tiny_overfit_failed_repair_model_or_loss",
        "run_uid": run_uid,
        "progress_jsonl": str(pfile.relative_to(ROOT)).replace("\\", "/"),
        "device": device,
        "contexts": len(selected),
        "dataset_count": len(selected),
        "steps": args.steps,
        "initial_loss": result.initial_loss,
        "final_loss": result.final_loss,
        "min_loss": result.min_loss,
        "loss_reduction_fraction": reduction,
        "positive_set_is_not_averaged": bool(midpoint["mode_beats_midpoint"]),
        "midpoint_check": midpoint,
        "elapsed_sec": time.perf_counter() - started,
    }
    progress_rows = read_progress(pfile, run_uid)
    summary_matches_progress(summary, progress_rows)
    write_json(SUMMARY_JSON, summary)
    print(json.dumps({"decision": summary["decision"], "initial_loss": result.initial_loss, "final_loss": result.final_loss}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

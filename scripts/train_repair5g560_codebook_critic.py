from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.real_critic_training import train_and_evaluate
from gcst.stage_state import record_stage


def main_train_g560_codebook_critic() -> dict:
    parser = argparse.ArgumentParser(description="Train the real Repair5G.5.60 Label-v5.1 codebook critic.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--seed", type=int, default=560)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--steps", type=int, default=20000)
    parser.add_argument("--fold-steps", type=int, default=4000)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--batch-groups", type=int, default=12)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()
    summary = train_and_evaluate(args.root, args.seed, args.hidden_dim, args.steps, args.fold_steps, args.folds, args.batch_groups, args.device)
    record_stage(
        "real_codebook_critic_training",
        "completed" if summary.get("final_checkpoint_step", 0) > 0 else "gate_failed",
        bool(summary.get("final_checkpoint_step", 0) > 0),
        "python scripts/train_repair5g560_codebook_critic.py",
        [
            summary.get("model_path", ""),
            "outputs/reports/phase5p5_repair5g560_codebook_critic_training_summary.json",
            "outputs/tables/phase5p5_repair5g560_codebook_critic_epoch_metrics.csv",
            "outputs/tables/phase5p5_repair5g560_codebook_critic_fold_metrics.csv",
            "outputs/tables/phase5p5_repair5g560_selector_eval.csv",
        ],
        summary,
        args.root,
    )
    print(summary)
    return summary


if __name__ == "__main__":
    main_train_g560_codebook_critic()

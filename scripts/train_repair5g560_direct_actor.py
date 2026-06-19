from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.actor_critic_training import train_g0_actor, write_valid_training_rows
from gcst.stage_state import record_stage


def main_train_g560_direct_actor() -> dict:
    parser = argparse.ArgumentParser(description="Train G5.60 G0 direct continuous actor.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--seed", type=int, default=560)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--steps", type=int, default=6000)
    parser.add_argument("--batch-groups", type=int, default=64)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()
    valid = write_valid_training_rows(args.root)
    summary = train_g0_actor(args.root, args.seed, args.hidden_dim, args.steps, args.batch_groups, args.device)
    summary["valid_label_summary"] = valid
    record_stage(
        "direct_actor_g0_training",
        "completed",
        bool(summary.get("model_path")),
        "python scripts/train_repair5g560_direct_actor.py",
        [
            summary.get("model_path", ""),
            "outputs/reports/phase5p5_repair5g560_direct_actor_g0_training_summary.json",
            "outputs/tables/phase5p5_repair5g560_labelv51_valid_training_rows.csv",
        ],
        summary,
        args.root,
    )
    print(summary)
    return summary


if __name__ == "__main__":
    main_train_g560_direct_actor()

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.actor_critic_training import train_g1_actor_critic, write_valid_training_rows
from gcst.stage_state import record_stage


def main_train_g560_direct_actor_critic() -> dict:
    parser = argparse.ArgumentParser(description="Train G5.60 G1 direct actor with training-time auxiliary critic.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--seed", type=int, default=561)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--actor-steps", type=int, default=5000)
    parser.add_argument("--critic-steps", type=int, default=3000)
    parser.add_argument("--batch-groups", type=int, default=64)
    parser.add_argument("--batch-rows", type=int, default=512)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()
    valid = write_valid_training_rows(args.root)
    summary = train_g1_actor_critic(
        args.root,
        args.seed,
        args.hidden_dim,
        args.actor_steps,
        args.critic_steps,
        args.batch_groups,
        args.batch_rows,
        args.device,
    )
    summary["valid_label_summary"] = valid
    record_stage(
        "direct_actor_g1_aux_critic_training",
        "completed",
        bool(summary.get("model_path")) and bool(summary.get("auxiliary_critic_path")),
        "python scripts/train_repair5g560_direct_actor_critic.py",
        [
            summary.get("model_path", ""),
            summary.get("auxiliary_critic_path", ""),
            "outputs/reports/phase5p5_repair5g560_direct_actor_g1_training_summary.json",
        ],
        summary,
        args.root,
    )
    print(summary)
    return summary


if __name__ == "__main__":
    main_train_g560_direct_actor_critic()

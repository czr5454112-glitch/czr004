from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.actor_critic_training import evaluate_direct_actors
from gcst.stage_state import record_stage


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate G5.60 direct actor checkpoints offline.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--model-path", action="append", default=None)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    summary = evaluate_direct_actors(args.root, args.model_path, args.device)
    record_stage(
        "direct_actor_offline_evaluation",
        "completed",
        bool(summary.get("anti_selector_passed")),
        "python scripts/eval_repair5g560_direct_actor.py",
        [
            "outputs/reports/phase5p5_repair5g560_direct_actor_evaluation.md",
            "outputs/reports/phase5p5_repair5g560_direct_actor_evaluation_summary.json",
            "outputs/tables/phase5p5_repair5g560_direct_actor_eval.csv",
            "outputs/tables/phase5p5_repair5g560_direct_actor_generated_theta.csv",
            "outputs/reports/phase5p5_repair5g560_generated_theta_novelty_summary.json",
        ],
        summary,
        args.root,
    )
    print(summary)


if __name__ == "__main__":
    main()

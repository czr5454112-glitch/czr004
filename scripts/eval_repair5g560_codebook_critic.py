from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.real_critic_training import EVAL_JSON, SELECTOR_EVAL_CSV, resolve
from gcst.stage_state import record_stage


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the latest G5.60 codebook critic evaluation artifacts.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    eval_path = resolve(EVAL_JSON, args.root)
    selector_path = resolve(SELECTOR_EVAL_CSV, args.root)
    if not eval_path.exists() or not selector_path.exists():
        raise FileNotFoundError("Train the G5.60 codebook critic before running evaluation audit.")
    summary = json.loads(eval_path.read_text(encoding="utf-8"))
    record_stage(
        "real_codebook_critic_evaluation",
        "completed",
        bool(summary.get("critic_learnability_gate_passed")),
        "python scripts/eval_repair5g560_codebook_critic.py",
        [
            "outputs/reports/phase5p5_repair5g560_codebook_critic_evaluation.md",
            "outputs/reports/phase5p5_repair5g560_codebook_critic_evaluation_summary.json",
            "outputs/tables/phase5p5_repair5g560_selector_eval.csv",
            "outputs/tables/phase5p5_repair5g560_failure_attribution.csv",
            "outputs/reports/phase5p5_repair5g560_failure_attribution.md",
            "outputs/reports/phase5p5_repair5g560_decision.md",
            "outputs/reports/phase5p5_repair5g560_decision_summary.json",
        ],
        summary,
        args.root,
    )
    print(summary)


if __name__ == "__main__":
    main()

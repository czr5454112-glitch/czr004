from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.real_critic_training import write_oracle_and_candidate_audit
from gcst.stage_state import record_stage


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze real oracle opportunity and G5.59 candidate support before training.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    summary = write_oracle_and_candidate_audit(args.root)
    record_stage(
        "oracle_and_candidate_space_audit",
        "completed",
        not bool(summary.get("candidate_slate_blocker")),
        "python scripts/analyze_repair5g560_oracle_gap.py",
        [
            "outputs/reports/phase5p5_repair5g560_oracle_opportunity.md",
            "outputs/reports/phase5p5_repair5g560_oracle_opportunity_summary.json",
            "outputs/tables/phase5p5_repair5g560_candidate_space_audit.csv",
        ],
        summary,
        args.root,
    )
    print(summary)


if __name__ == "__main__":
    main()

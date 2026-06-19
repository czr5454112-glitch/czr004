from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.identity_recovery import write_truth_audit
from gcst.stage_state import record_stage


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the Repair5G.5.60 source-of-truth audit for G5.59.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    summary = write_truth_audit(args.root)
    record_stage(
        "g559_truth_audit",
        "completed",
        True,
        "python scripts/audit_repair5g560_g559_truth.py",
        [
            "outputs/reports/phase5p5_repair5g560_g559_truth_audit.md",
            "outputs/reports/phase5p5_repair5g560_g559_truth_audit_summary.json",
            "outputs/tables/phase5p5_repair5g560_stage_implementation_audit.csv",
            "outputs/tables/phase5p5_repair5g560_identity_failure_audit.csv",
            "outputs/tables/phase5p5_repair5g560_scenario_validity_pre_audit.csv",
            "outputs/tables/phase5p5_repair5g560_training_entrypoint_audit.csv",
        ],
        summary,
        args.root,
    )
    print(summary)


if __name__ == "__main__":
    main()

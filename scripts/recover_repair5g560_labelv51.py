from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.identity_recovery import recover_labelv51
from gcst.stage_state import record_stage


def main() -> None:
    parser = argparse.ArgumentParser(description="Recover G5.59 pair rows into identity-safe Label-v5.1 rows.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    summary = recover_labelv51(args.root)
    record_stage(
        "labelv51_identity_recovery",
        "completed" if summary.get("recovery_gate_passed") else "gate_failed",
        bool(summary.get("recovery_gate_passed")),
        "python scripts/recover_repair5g560_labelv51.py",
        [
            "outputs/reports/phase5p5_repair5g560_labelv51_recovery.md",
            "outputs/reports/phase5p5_repair5g560_labelv51_recovery_summary.json",
            "outputs/tables/phase5p5_repair5g560_identity_crosswalk.csv",
            "outputs/tables/phase5p5_repair5g560_labelv51_join_audit.csv",
            "outputs/tables/phase5p5_repair5g560_labelv51_quarantine.csv",
            "outputs/tables/phase5p5_repair5g560_labelv51_training_rows.csv",
            "outputs/tables/phase5p5_repair5g560_labelv51_safe_sets.csv",
        ],
        summary,
        args.root,
    )
    print(summary)


if __name__ == "__main__":
    main()

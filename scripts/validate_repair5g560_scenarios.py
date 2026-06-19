from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.scenario_validation import validate_scenarios
from gcst.stage_state import record_stage


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate actual G5.59 MovingAI map/scenario files for G5.60.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--rewrite-from", default=None)
    parser.add_argument("--rewrite-to", default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    summary = validate_scenarios(args.root, args.rewrite_from, args.rewrite_to, args.limit)
    gate_passed = bool(summary.get("scenario_validity_gate_passed"))
    record_stage(
        "scenario_validity",
        "completed" if gate_passed else "gate_failed",
        gate_passed,
        "python scripts/validate_repair5g560_scenarios.py",
        [
            "outputs/tables/phase5p5_repair5g560_scenario_validity_audit.csv",
            "outputs/reports/phase5p5_repair5g560_scenario_validity_summary.json",
            "outputs/reports/phase5p5_repair5g560_scenario_validity.md",
        ],
        summary,
        args.root,
    )
    print(summary)


if __name__ == "__main__":
    main()

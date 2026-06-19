from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.actor_critic_training import export_actor_bundle
from gcst.stage_state import record_stage


def main() -> None:
    parser = argparse.ArgumentParser(description="Export actor-only G5.60 direct generator bundle.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--output-path", default=None)
    args = parser.parse_args()
    summary = export_actor_bundle(args.root, args.model_path, args.output_path)
    record_stage(
        "direct_actor_export",
        "completed",
        bool(summary.get("export_path")) and not summary.get("contains_auxiliary_critic"),
        "python scripts/export_repair5g560_direct_actor.py",
        [summary.get("export_path", ""), "outputs/reports/phase5p5_repair5g560_direct_actor_export_manifest.json"],
        summary,
        args.root,
    )
    print(summary)


if __name__ == "__main__":
    main()

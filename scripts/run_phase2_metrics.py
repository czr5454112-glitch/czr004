"""Run the shared Phase2 metrics harness from the repository root."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from czr004_metrics.cli import main


if __name__ == "__main__":
    raise SystemExit(main())

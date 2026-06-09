"""Run a focused G5.23 static-recovery probe only if mining requires it."""

from __future__ import annotations

from repair5g523_common import main_run_static_recovery_probe


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main_run_static_recovery_probe())

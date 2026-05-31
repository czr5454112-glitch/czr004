"""Freeze the best Repair5D composite as a versioned Repair5E spec."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / "src"))

from eval.repair5d_composite_spec import (  # noqa: E402
    build_best_composite_spec,
    load_json,
    repo_root,
    resolve_path,
    write_json,
    write_spec_markdown,
)


DEFAULT_GRID_SUMMARY = "outputs/reports/phase4f_repair5d_composite_grid_summary.json"
DEFAULT_CALIBRATION = "outputs/reports/phase4f_repair5_per_rule_safety_calibration.json"
DEFAULT_OUTPUT_JSON = "outputs/reports/phase4f_repair5d_best_composite_spec.json"
DEFAULT_OUTPUT_MD = "outputs/reports/phase4f_repair5d_best_composite_spec.md"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid-summary-json", type=Path, default=Path(DEFAULT_GRID_SUMMARY))
    parser.add_argument("--safety-calibration-json", type=Path, default=Path(DEFAULT_CALIBRATION))
    parser.add_argument("--output-json", type=Path, default=Path(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-md", type=Path, default=Path(DEFAULT_OUTPUT_MD))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    grid_summary = resolve_path(args.grid_summary_json, root)
    calibration = resolve_path(args.safety_calibration_json, root)
    output_json = resolve_path(args.output_json, root)
    output_md = resolve_path(args.output_md, root)
    if None in (grid_summary, calibration, output_json, output_md):
        raise ValueError("required paths could not be resolved")
    assert grid_summary and calibration and output_json and output_md
    if not grid_summary.exists():
        raise FileNotFoundError(grid_summary)
    if not calibration.exists():
        raise FileNotFoundError(calibration)

    spec = build_best_composite_spec(
        grid_summary=load_json(grid_summary),
        grid_summary_path=grid_summary,
        safety_calibration=calibration,
        root=root,
    )
    write_json(output_json, spec)
    write_spec_markdown(output_md, spec)
    print(json.dumps({"spec_json": str(output_json), "spec_md": str(output_md)}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ROUND = "phase5p5_repair5g565"
REPORTS = ROOT / "outputs/reports"


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def read_rows(path: Path) -> list[dict[str, str]]:
    p = resolve(path)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def finite(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    return out if np.isfinite(out) else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Calibrate G5.65 label/noise margin from exact paired rows.")
    parser.add_argument(
        "--pairs",
        nargs="*",
        type=Path,
        default=[
            Path("outputs/tables/phase5p5_repair5g562_cycle1_pairs.csv"),
            Path("outputs/tables/phase5p5_repair5g562_cycle2_pairs.csv"),
            Path("outputs/tables/phase5p5_repair5g562_cycle3_pairs.csv"),
            Path("outputs/tables/phase5p5_repair5g565_fresh_solver_panel_pairs.csv"),
        ],
    )
    args = parser.parse_args(argv)
    rows: list[dict[str, str]] = []
    sources = []
    for path in args.pairs:
        part = read_rows(path)
        if part:
            sources.append(str(resolve(path)).replace("\\", "/"))
            rows.extend(part)
    deltas = [finite(row.get("quality_delta_vs_g556")) for row in rows]
    deltas = [value for value in deltas if value is not None]
    abs_near = [abs(value) for value in deltas if abs(value) <= 0.25]
    median = float(np.median(deltas)) if deltas else 0.0
    mad = float(np.median([abs(value - median) for value in deltas])) if deltas else 0.0
    near_mad = float(np.median(abs_near)) if abs_near else mad
    margin = max(0.001, min(0.05, 2.0 * near_mad))
    summary = {
        "schema_version": f"{ROUND}_label_margin_summary_v1",
        "decision": "g565_label_margin_calibrated",
        "source_pair_files": sources,
        "exact_pair_rows": len(rows),
        "finite_quality_delta_rows": len(deltas),
        "median_quality_delta_vs_g556": median,
        "mad_quality_delta_vs_g556": mad,
        "near_tie_abs_delta_median": near_mad,
        "recommended_positive_margin": margin,
        "recommended_harmful_margin": margin,
        "fresh_g565_pairs_included": any("repair5g565" in source for source in sources),
        "success_stability_rows": sum(str(row.get("both_success", "")).lower() == "true" for row in rows),
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / f"{ROUND}_label_margin_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": summary["decision"], "margin": margin, "rows": len(rows)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Summarize Phase1a JSONL output into CSV and a paper-style ratio plot."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from czr004_metrics.io import read_jsonl, write_csv as write_rows_csv
from czr004_metrics.summary import MAP_ORDER, summarize_by_group


def write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "map",
        "agents",
        "method",
        "runs",
        "successes",
        "success_rate",
        "ratio_mean",
        "ratio_median",
        "ratio_std",
        "runtime_ms_mean",
    ]
    write_rows_csv(path, rows, fieldnames)


def plot_summary(path: Path, rows: list[dict]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    maps = sorted(
        {row["map"] for row in rows},
        key=lambda value: (MAP_ORDER.index(value) if value in MAP_ORDER else 999, value),
    )
    if not maps:
        return

    cols = 4 if len(maps) > 1 else 1
    rows_count = math.ceil(len(maps) / cols)
    fig, axes = plt.subplots(rows_count, cols, figsize=(4.2 * cols, 3.4 * rows_count), squeeze=False)
    methods = ["lacam_star", "lacam_star_ltm"]
    colors = {"lacam_star": "#1f77b4", "lacam_star_ltm": "#d62728"}

    for index, map_name in enumerate(maps):
        ax = axes[index // cols][index % cols]
        ax.set_title(map_name)
        for method in methods:
            points = [
                row
                for row in rows
                if row["map"] == map_name
                and row["method"] == method
                and not math.isnan(float(row["ratio_mean"]))
            ]
            points.sort(key=lambda row: int(row["agents"]))
            if not points:
                continue
            ax.plot(
                [int(row["agents"]) for row in points],
                [float(row["ratio_mean"]) for row in points],
                marker="o",
                linewidth=1.5,
                label=method,
                color=colors.get(method),
            )
        ax.set_xlabel("Number of Agents")
        ax.set_ylabel("Sum-of-Loss Ratio")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

    for index in range(len(maps), rows_count * cols):
        axes[index // cols][index % cols].axis("off")

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-csv", default=Path("outputs/tables/phase1a_ratio_by_map.csv"), type=Path)
    parser.add_argument("--output-figure", default=Path("outputs/figures/phase1a_ratio_by_map.png"), type=Path)
    args = parser.parse_args()

    rows = read_jsonl(args.input)
    summary = summarize_by_group(rows)
    write_csv(args.output_csv, summary)
    plot_summary(args.output_figure, summary)
    print(f"rows={len(rows)} groups={len(summary)} csv={args.output_csv} figure={args.output_figure}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

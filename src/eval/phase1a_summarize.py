"""Summarize Phase1a JSONL output into CSV and a paper-style ratio plot."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


MAP_ORDER = [
    "empty-32-32",
    "empty-48-48",
    "random-32-32-20",
    "maze-32-32-4",
    "random-64-64-20",
    "room-64-64-8",
    "warehouse-10-20-10-2-1",
    "warehouse-10-20-10-2-2",
]


def read_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL") from exc
    return rows


def stdev_or_zero(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) > 1 else 0.0


def summarize(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, int, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["map"], int(row["agents"]), row["method"])].append(row)

    summary: list[dict] = []
    for (map_name, agents, method), group in sorted(
        grouped.items(), key=lambda item: (MAP_ORDER.index(item[0][0]) if item[0][0] in MAP_ORDER else 999, item[0][0], item[0][1], item[0][2])
    ):
        ratios = [
            float(row["sum_of_loss_ratio"])
            for row in group
            if row.get("success") and row.get("sum_of_loss_ratio") is not None
        ]
        runtimes = [float(row["runtime_ms"]) for row in group if row.get("runtime_ms") is not None]
        success_count = sum(1 for row in group if row.get("success"))
        summary.append(
            {
                "map": map_name,
                "agents": agents,
                "method": method,
                "runs": len(group),
                "successes": success_count,
                "success_rate": success_count / len(group) if group else 0.0,
                "ratio_mean": statistics.mean(ratios) if ratios else math.nan,
                "ratio_median": statistics.median(ratios) if ratios else math.nan,
                "ratio_std": stdev_or_zero(ratios) if ratios else math.nan,
                "runtime_ms_mean": statistics.mean(runtimes) if runtimes else math.nan,
            }
        )
    return summary


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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

    rows = read_rows(args.input)
    summary = summarize(rows)
    write_csv(args.output_csv, summary)
    plot_summary(args.output_figure, summary)
    print(f"rows={len(rows)} groups={len(summary)} csv={args.output_csv} figure={args.output_figure}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.label_v52_set import contexts_from_groups  # noqa: E402
from gcst.loss_geometry_g564 import context_loss_geometry, conflicting_theta_pairs, summarize_geometry_rows  # noqa: E402
from gcst.real_label_graph_dataset import DEFAULT_CONTEXT_DIR, G560_TRAINING_ROWS, load_label_groups  # noqa: E402


ROUND = "phase5p5_repair5g564"
REPORTS = ROOT / "outputs/reports"
TABLES = ROOT / "outputs/tables"


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze G5.64 Label-v5.2 loss geometry.")
    parser.add_argument("--rows-path", type=Path, default=G560_TRAINING_ROWS)
    parser.add_argument("--context-dir", type=Path, default=DEFAULT_CONTEXT_DIR)
    parser.add_argument("--max-contexts", type=int, default=1000)
    parser.add_argument("--tau", type=float, default=0.05)
    parser.add_argument("--harmful-margin", type=float, default=0.12)
    parser.add_argument("--conflict-distance", type=float, default=0.015)
    args = parser.parse_args(argv)

    groups = load_label_groups(resolve(args.rows_path), resolve(args.context_dir), max_contexts=args.max_contexts)
    if not groups:
        raise SystemExit("no Label-v5.1 groups with local scenario files available")
    contexts = contexts_from_groups(groups)
    rows = [
        context_loss_geometry(
            context,
            tau=args.tau,
            requested_harmful_margin=args.harmful_margin,
            conflict_distance_threshold=args.conflict_distance,
        )
        for context in contexts
    ]
    conflicts = [
        row
        for context in contexts
        for row in conflicting_theta_pairs(context, distance_threshold=args.conflict_distance)
    ]
    summary = summarize_geometry_rows(rows)
    summary.update(
        {
            "decision": "g564_loss_geometry_audited",
            "rows_path": str(resolve(args.rows_path)).replace("\\", "/"),
            "context_dir": str(resolve(args.context_dir)).replace("\\", "/"),
            "conflicting_theta_pairs": len(conflicts),
            "conflict_distance_threshold": args.conflict_distance,
            "harmful_margin_requested": args.harmful_margin,
            "tau": args.tau,
        }
    )
    write_rows(TABLES / f"{ROUND}_loss_geometry_by_context.csv", rows)
    write_rows(TABLES / f"{ROUND}_conflicting_theta_pairs.csv", conflicts)
    write_json(REPORTS / f"{ROUND}_loss_geometry_summary.json", summary)
    (REPORTS / f"{ROUND}_loss_geometry.md").write_text(
        "# G5.64 Loss Geometry\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- contexts: `{summary['contexts']}`; positive contexts: `{summary['positive_contexts']}`\n"
        f"- conflicting near-duplicate theta pairs: `{summary['conflicting_theta_pairs']}` across `{summary['conflict_contexts']}` contexts\n"
        f"- median baseline floor-corrected positive loss: `{summary['median_baseline_floor_corrected_positive_loss']}`\n"
        "- softmin floors are computed per context before interpreting oracle/memorization loss.\n"
        "- censored rows remain unknown, not negative examples.\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": summary["decision"], "contexts": summary["contexts"], "conflicts": len(conflicts)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

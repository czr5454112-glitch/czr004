from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.real_label_graph_dataset import load_label_groups, number, row_is_harmful, row_is_positive, row_is_censored  # noqa: E402


ROUND = "phase5p5_repair5g562"
TABLE = Path(f"outputs/tables/{ROUND}_positive_frontier_acquisition.csv")
SUMMARY = Path(f"outputs/reports/{ROUND}_positive_frontier_acquisition_summary.json")


def claims() -> dict[str, bool]:
    return {
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with p.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict[str, Any]) -> None:
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def acquisition_rows(max_contexts: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in load_label_groups(max_contexts=max_contexts):
        positives = [row for row in group.rows if row_is_positive(row)]
        harmful = [row for row in group.rows if row_is_harmful(row)]
        censored = [row for row in group.rows if row_is_censored(row)]
        if not positives and not harmful:
            continue
        best_delta = min([number(row.get("quality_delta_vs_g556"), 0.0) for row in positives], default=0.0)
        worst_delta = max([number(row.get("quality_delta_vs_g556"), 0.0) for row in harmful], default=0.0)
        priority = (1 if positives else 0) + max(0.0, -best_delta) + max(0.0, worst_delta) + 0.1 * len(censored)
        rows.append(
            {
                "acquisition_row_id": f"g562_frontier_{len(rows):08d}",
                "g560_evaluation_uid": group.evaluation_uid,
                "split": group.split,
                "map": group.map,
                "map_family": group.map_family,
                "agent_count": group.agent_count,
                "seed": group.seed,
                "budget_ms": group.budget_ms,
                "positive_rows": len(positives),
                "harmful_rows": len(harmful),
                "censored_rows": len(censored),
                "best_positive_quality_delta_vs_g556": best_delta if positives else "",
                "worst_harmful_quality_delta_vs_g556": worst_delta if harmful else "",
                "frontier_priority_score": priority,
                "targeted_design_reason": "positive_frontier_and_boundary" if positives and harmful else ("positive_frontier" if positives else "unsafe_boundary"),
                "requires_new_exact_materialization": True,
                **claims(),
            }
        )
    rows.sort(key=lambda row: float(row["frontier_priority_score"]), reverse=True)
    for rank, row in enumerate(rows, start=1):
        row["frontier_rank"] = rank
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Select G5.62 positive-frontier acquisition contexts.")
    parser.add_argument("--max-contexts", type=int, default=800)
    args = parser.parse_args(argv)
    rows = acquisition_rows(args.max_contexts)
    write_rows(TABLE, rows)
    summary = {
        "schema_version": f"{ROUND}_positive_frontier_acquisition_summary_v1",
        "decision": "g562_positive_frontier_acquisition_designed_server_materialization_required",
        "acquisition_contexts": len(rows),
        "positive_contexts": sum(int(row["positive_rows"]) > 0 for row in rows),
        "unsafe_boundary_contexts": sum(int(row["harmful_rows"]) > 0 for row in rows),
        "censored_contexts": sum(int(row["censored_rows"]) > 0 for row in rows),
        **claims(),
    }
    write_json(SUMMARY, summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

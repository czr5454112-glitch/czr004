from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.real_label_graph_dataset import load_label_groups, number, positive_target  # noqa: E402
from gcst.theta_schema import BASELINE_G556, THETA_NUMERIC_COLUMNS, clamp_theta_row, mode_columns  # noqa: E402


ROUND = "phase5p5_repair5g562"
PAIRS = Path(f"outputs/tables/{ROUND}_alpha_response_pairs.csv")
SUMMARY = Path(f"outputs/reports/{ROUND}_alpha_response_summary.json")


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


def alpha_rows(max_contexts: int, alphas: list[float]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in load_label_groups(max_contexts=max_contexts):
        target, best_delta = positive_target(group.rows)
        if target is None or best_delta is None:
            continue
        for alpha in alphas:
            theta = np.asarray(BASELINE_G556, dtype=np.float32) * (1.0 - alpha) + np.asarray(target, dtype=np.float32) * alpha
            theta_row = {col: float(theta[idx]) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)}
            theta_row.update(mode_columns("flow_shield"))
            rows.append(
                {
                    "panel_row_id": f"g562_alpha_{len(rows):08d}",
                    "g560_evaluation_uid": group.evaluation_uid,
                    "split": group.split,
                    "map": group.map,
                    "map_family": group.map_family,
                    "agent_count": group.agent_count,
                    "seed": group.seed,
                    "budget_ms": group.budget_ms,
                    "alpha_to_real_positive_safe_target": alpha,
                    "best_observed_positive_quality_delta_vs_g556": best_delta,
                    "source_positive_rows": sum(number(row.get("quality_delta_vs_g556"), 0.0) < 0.0 for row in group.rows),
                    "requires_exact_materialization_before_claim": True,
                    **clamp_theta_row(theta_row),
                    **claims(),
                }
            )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Design the G5.62 alpha-response acquisition panel.")
    parser.add_argument("--max-contexts", type=int, default=800)
    parser.add_argument("--alphas", default="0,0.25,0.5,0.75,1.0")
    args = parser.parse_args(argv)
    alphas = [float(token) for token in args.alphas.split(",") if token.strip()]
    rows = alpha_rows(args.max_contexts, alphas)
    write_rows(PAIRS, rows)
    summary = {
        "schema_version": f"{ROUND}_alpha_response_summary_v1",
        "decision": "g562_alpha_response_acquisition_designed_server_materialization_required",
        "contexts_with_positive_frontier": len({row["g560_evaluation_uid"] for row in rows}),
        "alpha_rows": len(rows),
        "alphas": alphas,
        "exact_materialized": False,
        **claims(),
    }
    write_json(SUMMARY, summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

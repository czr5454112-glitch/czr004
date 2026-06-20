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

from gcst.real_label_graph_dataset import load_label_groups, number, row_is_positive, theta_from_row  # noqa: E402
from gcst.theta_schema import BASELINE_G556, THETA_NUMERIC_COLUMNS, clamp_theta_row, mode_columns  # noqa: E402


ROUND = "phase5p5_repair5g562"
PAIRS = Path(f"outputs/tables/{ROUND}_optimizer_teacher_pairs.csv")
SUMMARY = Path(f"outputs/reports/{ROUND}_optimizer_teacher_summary.json")


GROUPS = [
    ["theta_alpha_cong_commit_progress", "theta_alpha_cong_commit_nonprogress", "theta_alpha_cong_block"],
    ["theta_alpha_cong_wait_progress", "theta_alpha_cong_wait_nonprogress"],
    ["theta_alpha_flow_commit_progress", "theta_alpha_flow_wait_progress"],
    ["theta_rho_cong_decay", "theta_rho_flow_decay"],
    ["theta_lambda_cong", "theta_lambda_flow"],
    ["theta_flow_shield_beta", "theta_max_flow_shield", "theta_min_edge_cost", "theta_max_edge_cost"],
]


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


def teacher_rows(max_contexts: int, per_context: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    baseline = np.asarray(BASELINE_G556, dtype=np.float32)
    for group in load_label_groups(max_contexts=max_contexts):
        positives = [row for row in group.rows if row_is_positive(row)]
        positives.sort(key=lambda row: number(row.get("quality_delta_vs_g556"), 0.0))
        for rank, source in enumerate(positives[:per_context], start=1):
            theta = theta_from_row(source)
            residual = theta - baseline
            group_values = []
            for cols in GROUPS:
                idxs = [THETA_NUMERIC_COLUMNS.index(col) for col in cols]
                group_values.append(float(np.mean(residual[idxs])))
            row = {col: float(theta[idx]) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)}
            row.update(mode_columns("flow_shield"))
            rows.append(
                {
                    "teacher_row_id": f"g562_teacher_{len(rows):08d}",
                    "teacher_type": "bounded_safe_subspace_real_label_teacher",
                    "deployed_optimizer": False,
                    "g560_evaluation_uid": group.evaluation_uid,
                    "split": group.split,
                    "map": group.map,
                    "map_family": group.map_family,
                    "agent_count": group.agent_count,
                    "seed": group.seed,
                    "budget_ms": group.budget_ms,
                    "positive_rank": rank,
                    "observed_quality_delta_vs_g556": number(source.get("quality_delta_vs_g556"), 0.0),
                    "safe_subspace_coordinates": ";".join(f"{value:.8g}" for value in group_values),
                    "requires_exact_materialization_before_claim": False,
                    **clamp_theta_row(row),
                    **claims(),
                }
            )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the G5.62 optimizer-teacher diagnostic from real safe labels.")
    parser.add_argument("--max-contexts", type=int, default=800)
    parser.add_argument("--per-context", type=int, default=2)
    args = parser.parse_args(argv)
    rows = teacher_rows(args.max_contexts, args.per_context)
    write_rows(PAIRS, rows)
    summary = {
        "schema_version": f"{ROUND}_optimizer_teacher_summary_v1",
        "decision": "g562_optimizer_teacher_diagnostic_completed",
        "teacher_rows": len(rows),
        "contexts": len({row["g560_evaluation_uid"] for row in rows}),
        "deployed_optimizer": False,
        "safe_subspace_dimensions": len(GROUPS),
        **claims(),
    }
    write_json(SUMMARY, summary)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Label-v4 context IDs, safe sets, and learnability labels."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

import numpy as np

from .scenario_features import build_context_uid
from .theta_schema import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS

THETA_COLUMNS = [*THETA_NUMERIC_COLUMNS, "theta_goal_projection_mode"]


def theta_vector(row: dict[str, Any]) -> np.ndarray:
    vals = []
    for col, base in zip(THETA_NUMERIC_COLUMNS, BASELINE_G556):
        try:
            vals.append(float(row.get(col, base)))
        except Exception:
            vals.append(float(base))
    return np.asarray(vals, dtype=np.float32)


def theta_from_vector(vec: np.ndarray) -> dict[str, Any]:
    out = {col: float(value) for col, value in zip(THETA_NUMERIC_COLUMNS, vec)}
    out["theta_goal_projection_mode"] = "flow_shield"
    return out


def context_target_theta(graph_summary: dict[str, Any], traffic_summary: dict[str, Any]) -> np.ndarray:
    density = float(graph_summary.get("agent_density", graph_summary.get("density", 0.05)) or 0.05)
    bottleneck = float(traffic_summary.get("bottleneck_demand", 0.0))
    opposing = float(traffic_summary.get("opposing_flow_ratio", 0.0))
    head_on = float(traffic_summary.get("head_on_pressure", 0.0))
    target = BASELINE_G556.copy()
    target[2] = np.clip(1.0 + 0.8 * bottleneck + 0.4 * head_on, 0.0, 2.0)
    target[5] = np.clip(0.8 + 0.9 * (1.0 - opposing), 0.0, 2.0)
    target[6] = np.clip(0.55 + 0.8 * (1.0 - bottleneck), 0.0, 2.0)
    target[7] = np.clip(0.96 - 0.18 * density - 0.08 * opposing, 0.70, 1.0)
    target[9] = np.clip(0.45 + 1.2 * bottleneck, 0.0, 2.0)
    target[11] = np.clip(0.25 + 0.7 * opposing + 0.5 * head_on, 0.0, 1.0)
    target[12] = np.clip(0.65 + 0.5 * (bottleneck + opposing), 0.25, 1.5)
    return np.minimum(np.maximum(target, THETA_LO), THETA_HI).astype(np.float32)


def score_theta(theta: np.ndarray, target: np.ndarray, traffic_summary: dict[str, Any]) -> dict[str, Any]:
    span = np.maximum(THETA_HI - THETA_LO, 1e-6)
    dist = float(np.mean(np.abs((theta - target) / span)))
    base_dist = float(np.mean(np.abs((BASELINE_G556 - target) / span)))
    quality_delta = dist - base_dist
    risk = max(0.0, dist - 0.17) + 0.15 * max(0.0, float(traffic_summary.get("head_on_pressure", 0.0)) - 0.25)
    success_regression = risk > 0.08
    success_gain = (quality_delta < -0.025) and not success_regression
    both_success = not success_regression
    return {
        "selected_success": not success_regression,
        "baseline_success": True,
        "success_regression": success_regression,
        "success_gain": success_gain,
        "both_success": both_success,
        "both_fail": False,
        "quality_delta_vs_g556": quality_delta,
        "candidate_recognized": True,
        "fingerprint_match": True,
        "cost_finite": math.isfinite(quality_delta),
        "theta_in_bounds": bool(np.all(theta >= THETA_LO) and np.all(theta <= THETA_HI)),
    }


def build_pair_labels(
    context_uid: str,
    theta_rows: list[dict[str, Any]],
    graph_summary: dict[str, Any],
    traffic_summary: dict[str, Any],
    limit: int = 64,
) -> list[dict[str, Any]]:
    target = context_target_theta(graph_summary, traffic_summary)
    rows = []
    for theta_row in theta_rows[:limit]:
        theta = theta_vector(theta_row)
        label = score_theta(theta, target, traffic_summary)
        rows.append(
            {
                "context_uid": context_uid,
                "candidate_id": theta_row.get("candidate_id", ""),
                "row_weight": 1.0 / max(1, min(limit, len(theta_rows))),
                "target_theta_l1_to_context": float(np.mean(np.abs(theta - target))),
                **label,
                **{col: float(val) for col, val in zip(THETA_NUMERIC_COLUMNS, theta)},
            }
        )
    return rows


def context_safe_sets(pair_rows: list[dict[str, Any]], top_k: int = 8) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pair_rows:
        grouped[str(row["context_uid"])].append(row)
    out = []
    for uid, rows in grouped.items():
        safe = [r for r in rows if not r.get("success_regression") and r.get("theta_in_bounds")]
        improving = [r for r in safe if r.get("success_gain")]
        ranked = sorted(safe, key=lambda r: float(r.get("quality_delta_vs_g556", 0.0)))
        out.append(
            {
                "context_uid": uid,
                "safe_theta_ids": ";".join(str(r["candidate_id"]) for r in safe),
                "safe_improving_theta_ids": ";".join(str(r["candidate_id"]) for r in improving),
                "Pareto_theta_ids": ";".join(str(r["candidate_id"]) for r in ranked[:top_k]),
                "top_k_safe_theta_ids": ";".join(str(r["candidate_id"]) for r in ranked[:top_k]),
                "fallback_required": len(improving) == 0,
                "best_observed_quality_delta": min((float(r.get("quality_delta_vs_g556", 0.0)) for r in safe), default=0.0),
                "safe_frontier_size": len(safe),
                "theta_cluster_representatives": ";".join(str(r["candidate_id"]) for r in ranked[: min(top_k, 6)]),
            }
        )
    return out

"""Label-v5 real-solver preference labels.

This module never fabricates solver outcomes.  It converts paired solver rows
into per-theta labels, aggregate safe sets, and listwise targets.
"""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from typing import Any

import numpy as np

from .label_v4 import THETA_NUMERIC_COLUMNS, theta_vector


def _sha(parts: list[Any]) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()


def instance_uid(
    physical_map_sha256: str,
    paired_start_goal_assignment_sha256: str,
    agent_count: int,
    planning_budget: Any,
    ltm_iteration_budget: Any,
) -> str:
    return _sha([physical_map_sha256, paired_start_goal_assignment_sha256, int(agent_count), planning_budget, ltm_iteration_budget])


def evaluation_uid(instance_uid_value: str, solver_rng_seed: Any) -> str:
    return _sha([instance_uid_value, solver_rng_seed])


def solver_success(row: dict[str, Any]) -> bool:
    return str(row.get("solution_found", row.get("probe_solution_found", ""))).strip().lower() in {"1", "true", "yes", "y"}


def solver_ratio(row: dict[str, Any]) -> float | None:
    for key in ["sum_of_loss_ratio", "probe_sum_of_loss_ratio", "selected_ratio", "baseline_ratio"]:
        text = str(row.get(key, "")).strip()
        if not text:
            continue
        try:
            value = float(text)
            if math.isfinite(value):
                return value
        except Exception:
            continue
    return None


def theta_id(row: dict[str, Any]) -> str:
    return str(row.get("theta_id") or row.get("candidate_id") or row.get("materialized_method") or row.get("role") or "")


def pair_record(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    cand_success = solver_success(candidate)
    base_success = solver_success(baseline)
    cand_ratio = solver_ratio(candidate)
    base_ratio = solver_ratio(baseline)
    both_success = cand_success and base_success
    quality_delta = cand_ratio - base_ratio if both_success and cand_ratio is not None and base_ratio is not None else math.nan
    return {
        "instance_uid": candidate.get("instance_uid", ""),
        "evaluation_uid": candidate.get("evaluation_uid", ""),
        "theta_id": theta_id(candidate),
        "candidate_success": cand_success,
        "baseline_success": base_success,
        "success_regression": bool(base_success and not cand_success),
        "success_gain": bool(cand_success and not base_success),
        "both_success": bool(both_success),
        "both_fail": bool((not cand_success) and (not base_success)),
        "quality_delta_vs_g556": quality_delta,
        "candidate_recognized": str(candidate.get("candidate_recognized", "true")).lower() in {"1", "true", "yes"},
        "fingerprint_match": str(candidate.get("fulltheta_fingerprint_match", candidate.get("fingerprint_match", "true"))).lower() in {"1", "true", "yes"},
        "cost_finite": bool(math.isfinite(quality_delta)) if both_success else bool(cand_success != base_success),
        "theta_in_bounds": str(candidate.get("theta_in_bounds", "true")).lower() in {"1", "true", "yes"},
        "runtime": candidate.get("runtime", candidate.get("probe_runtime_ms", "")),
        **{col: candidate.get(col, "") for col in THETA_NUMERIC_COLUMNS},
    }


def aggregate_replicates(pair_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in pair_rows:
        grouped[(str(row.get("instance_uid", "")), str(row.get("theta_id", "")))].append(row)
    out: list[dict[str, Any]] = []
    for (uid, tid), rows in sorted(grouped.items()):
        deltas = [float(r["quality_delta_vs_g556"]) for r in rows if isinstance(r.get("quality_delta_vs_g556"), (int, float)) and math.isfinite(float(r["quality_delta_vs_g556"]))]
        mean = float(np.mean(deltas)) if deltas else math.nan
        ci = float(1.96 * np.std(deltas, ddof=1) / math.sqrt(len(deltas))) if len(deltas) > 1 else 0.0
        out.append(
            {
                "instance_uid": uid,
                "theta_id": tid,
                "replicate_count": len(rows),
                "success_regression_count": sum(bool(r.get("success_regression")) for r in rows),
                "success_gain_count": sum(bool(r.get("success_gain")) for r in rows),
                "quality_delta_mean": mean,
                "quality_delta_CI": ci,
                "worst_replicate_delta": max(deltas) if deltas else math.nan,
                "development_safe": sum(bool(r.get("success_regression")) for r in rows) == 0,
                "promotion_safe": sum(bool(r.get("success_regression")) for r in rows) == 0 and len(rows) >= 3,
            }
        )
    return out


def safe_sets(aggregate_rows: list[dict[str, Any]], top_k: int = 8, temperature: float = 0.15) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in aggregate_rows:
        grouped[str(row.get("instance_uid", ""))].append(row)
    out: list[dict[str, Any]] = []
    for uid, rows in sorted(grouped.items()):
        safe = [r for r in rows if bool(r.get("development_safe"))]
        improving = [r for r in safe if math.isfinite(float(r.get("quality_delta_mean", math.nan))) and float(r.get("quality_delta_mean", 0.0)) < 0.0]
        ranked = sorted(safe, key=lambda r: float(r.get("quality_delta_mean", math.inf)))
        if safe:
            vals = np.asarray([float(r.get("quality_delta_mean", 0.0)) for r in safe], dtype=np.float64)
            vals = vals - np.nanmin(vals)
            probs = np.exp(-vals / max(temperature, 1.0e-6))
            probs = probs / max(float(probs.sum()), 1.0e-12)
            prob_map = {str(r["theta_id"]): float(p) for r, p in zip(safe, probs)}
        else:
            prob_map = {}
        out.append(
            {
                "instance_uid": uid,
                "safe_theta_ids": ";".join(str(r["theta_id"]) for r in safe),
                "safe_improving_theta_ids": ";".join(str(r["theta_id"]) for r in improving),
                "Pareto_theta_ids": ";".join(str(r["theta_id"]) for r in ranked[:top_k]),
                "top_k_safe_theta_ids": ";".join(str(r["theta_id"]) for r in ranked[:top_k]),
                "fallback_required": len(improving) == 0,
                "soft_listwise_target": ";".join(f"{tid}:{prob:.8g}" for tid, prob in sorted(prob_map.items())),
            }
        )
    return out


def row_weight_by_instance(pair_rows: list[dict[str, Any]]) -> list[float]:
    counts: dict[str, int] = defaultdict(int)
    for row in pair_rows:
        counts[str(row.get("instance_uid", ""))] += 1
    instance_count = max(1, len(counts))
    return [1.0 / (instance_count * max(1, counts[str(row.get("instance_uid", ""))])) for row in pair_rows]


def theta_distance(a: dict[str, Any], b: dict[str, Any]) -> float:
    va = theta_vector(a)
    vb = theta_vector(b)
    return float(np.mean(np.abs(va - vb)))

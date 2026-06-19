"""Generated-theta identity and novelty audits for direct actors."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .label_v4 import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS


def generated_theta_uid(model_checkpoint: str, instance_uid: str, theta_values: list[float] | np.ndarray) -> str:
    values = [round(float(v), 10) for v in list(theta_values)]
    payload = json.dumps([model_checkpoint, instance_uid, values], ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def theta_matrix(rows: list[dict[str, Any]]) -> np.ndarray:
    vals = []
    for row in rows:
        vals.append([float(row.get(col, BASELINE_G556[idx])) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)])
    return np.asarray(vals, dtype=np.float32)


def normalized_distances(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    span = np.maximum(np.asarray(THETA_HI - THETA_LO, dtype=np.float32), 1.0e-6)
    return np.mean(np.abs((a[:, None, :] - b[None, :, :]) / span), axis=-1)


def audit_generated_theta(generated_rows: list[dict[str, Any]], observed_rows: list[dict[str, Any]], safe_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if not generated_rows:
        return {"generated_rows": 0}
    gen = theta_matrix(generated_rows)
    obs = theta_matrix(observed_rows) if observed_rows else np.asarray(BASELINE_G556, dtype=np.float32).reshape(1, -1)
    safe = theta_matrix(safe_rows or []) if safe_rows else obs
    d_obs = normalized_distances(gen, obs)
    d_safe = normalized_distances(gen, safe)
    baseline = np.asarray(BASELINE_G556, dtype=np.float32)
    rounded = {tuple(round(float(v), 8) for v in row) for row in gen}
    pairwise = normalized_distances(gen, gen)
    upper = pairwise[np.triu_indices_from(pairwise, k=1)] if len(gen) > 1 else np.asarray([0.0])
    return {
        "generated_rows": int(len(gen)),
        "exact_match_rate_to_observed_theta": float((d_obs.min(axis=1) <= 1.0e-10).mean()),
        "nearest_observed_theta_distance_mean": float(d_obs.min(axis=1).mean()),
        "nearest_safe_theta_distance_mean": float(d_safe.min(axis=1).mean()),
        "unique_generated_theta_count": int(len(rounded)),
        "theta_hash_count": int(len({row.get("generated_theta_uid", "") for row in generated_rows})),
        "fraction_exactly_equal_to_g556": float(np.all(np.isclose(gen, baseline, atol=1.0e-8), axis=1).mean()),
        "fraction_within_epsilon_of_g556": float((np.mean(np.abs(gen - baseline), axis=1) <= 1.0e-4).mean()),
        "pairwise_generated_theta_distance_mean": float(upper.mean()),
        "per_field": {
            col: {
                "mean": float(gen[:, idx].mean()),
                "std": float(gen[:, idx].std()),
                "min": float(gen[:, idx].min()),
                "max": float(gen[:, idx].max()),
                "residual_variance": float(np.var(gen[:, idx] - float(BASELINE_G556[idx]))),
            }
            for idx, col in enumerate(THETA_NUMERIC_COLUMNS)
        },
    }


def write_audit(path: str | Path, summary: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

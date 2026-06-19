"""Canonical solver-facing UpdateParams schema for direct continuous actors."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ThetaField:
    name: str
    dtype: str
    lower: float
    upper: float
    default: float | str
    baseline: float | str
    mode_representation: str
    cpp_parser_name: str
    registry_column_name: str
    fingerprint_key: str
    tolerance: float = 1.0e-6


NUMERIC_SCHEMA: list[ThetaField] = [
    ThetaField("theta_alpha_cong_commit_progress", "float", 0.00, 1.50, 1.25, 1.25, "numeric", "alpha_cong_commit_progress", "theta_alpha_cong_commit_progress", "alpha_cong_commit_progress"),
    ThetaField("theta_alpha_cong_commit_nonprogress", "float", 0.50, 1.75, 1.1580041646957397, 1.1580041646957397, "numeric", "alpha_cong_commit_nonprogress", "theta_alpha_cong_commit_nonprogress", "alpha_cong_commit_nonprogress"),
    ThetaField("theta_alpha_cong_block", "float", 0.50, 2.25, 1.25, 1.25, "numeric", "alpha_cong_block", "theta_alpha_cong_block", "alpha_cong_block"),
    ThetaField("theta_alpha_cong_wait_progress", "float", 0.00, 1.25, 0.75, 0.75, "numeric", "alpha_cong_wait_progress", "theta_alpha_cong_wait_progress", "alpha_cong_wait_progress"),
    ThetaField("theta_alpha_cong_wait_nonprogress", "float", 0.00, 1.75, 0.75, 0.75, "numeric", "alpha_cong_wait_nonprogress", "theta_alpha_cong_wait_nonprogress", "alpha_cong_wait_nonprogress"),
    ThetaField("theta_alpha_flow_commit_progress", "float", 0.00, 1.50, 1.040339708328247, 1.040339708328247, "numeric", "alpha_flow_commit_progress", "theta_alpha_flow_commit_progress", "alpha_flow_commit_progress"),
    ThetaField("theta_alpha_flow_wait_progress", "float", 0.00, 1.25, 0.6932658553123474, 0.6932658553123474, "numeric", "alpha_flow_wait_progress", "theta_alpha_flow_wait_progress", "alpha_flow_wait_progress"),
    ThetaField("theta_rho_cong_decay", "float", 0.90, 1.00, 0.9799358248710632, 0.9799358248710632, "numeric", "rho_cong_decay", "theta_rho_cong_decay", "rho_cong_decay"),
    ThetaField("theta_rho_flow_decay", "float", 0.90, 1.00, 1.0, 1.0, "numeric", "rho_flow_decay", "theta_rho_flow_decay", "rho_flow_decay"),
    ThetaField("theta_lambda_cong", "float", 0.50, 1.50, 0.6841553449630737, 0.6841553449630737, "numeric", "lambda_cong", "theta_lambda_cong", "lambda_cong"),
    ThetaField("theta_lambda_flow", "float", 0.00, 1.50, 0.6499999761581421, 0.6499999761581421, "numeric", "lambda_flow", "theta_lambda_flow", "lambda_flow"),
    ThetaField("theta_flow_shield_beta", "float", 0.00, 0.80, 0.3355112671852112, 0.3355112671852112, "numeric", "flow_shield_beta", "theta_flow_shield_beta", "flow_shield_beta"),
    ThetaField("theta_max_flow_shield", "float", 0.25, 1.50, 0.8590060472488403, 0.8590060472488403, "numeric", "max_flow_shield", "theta_max_flow_shield", "max_flow_shield"),
    ThetaField("theta_min_edge_cost", "float", 0.25, 1.00, 1.0, 1.0, "numeric", "min_edge_cost", "theta_min_edge_cost", "min_edge_cost"),
    ThetaField("theta_max_edge_cost", "float", 8.00, 12.00, 10.79326343536377, 10.79326343536377, "numeric", "max_edge_cost", "theta_max_edge_cost", "max_edge_cost"),
]

MODE_SCHEMA: list[ThetaField] = [
    ThetaField("theta_goal_projection_mode_flow_shield", "bool_onehot", 0.0, 1.0, 1.0, 1.0, "one_hot_goal_projection_mode", "goal_projection_mode", "theta_goal_projection_mode_flow_shield", "goal_projection_mode"),
    ThetaField("theta_goal_projection_mode_agent_progress", "bool_onehot", 0.0, 1.0, 0.0, 0.0, "one_hot_goal_projection_mode", "goal_projection_mode", "theta_goal_projection_mode_agent_progress", "goal_projection_mode"),
    ThetaField("theta_goal_projection_mode_none", "bool_onehot", 0.0, 1.0, 0.0, 0.0, "one_hot_goal_projection_mode", "goal_projection_mode", "theta_goal_projection_mode_none", "goal_projection_mode"),
]

THETA_SCHEMA: list[ThetaField] = [*NUMERIC_SCHEMA, *MODE_SCHEMA]
THETA_NUMERIC_COLUMNS = [field.name for field in NUMERIC_SCHEMA]
THETA_MODE_COLUMNS = [field.name for field in MODE_SCHEMA]
THETA_COLUMNS = [field.name for field in THETA_SCHEMA]

THETA_LO = np.asarray([field.lower for field in NUMERIC_SCHEMA], dtype=np.float32)
THETA_HI = np.asarray([field.upper for field in NUMERIC_SCHEMA], dtype=np.float32)
BASELINE_G556 = np.asarray([float(field.baseline) for field in NUMERIC_SCHEMA], dtype=np.float32)
THETA_BOUNDS = {field.name: (field.lower, field.upper) for field in THETA_SCHEMA}
THETA_TOLERANCE = {field.name: field.tolerance for field in THETA_SCHEMA}


def _finite_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if np.isfinite(out) else default


def clamp_numeric_theta(values: list[float] | np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float32)
    return np.minimum(np.maximum(arr, THETA_LO), THETA_HI).astype(np.float32)


def clamp_theta_row(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for idx, field in enumerate(NUMERIC_SCHEMA):
        out[field.name] = float(min(max(_finite_float(row.get(field.name), float(BASELINE_G556[idx])), field.lower), field.upper))
    mode = theta_mode(row)
    out.update(mode_columns(mode))
    if out["theta_min_edge_cost"] > out["theta_max_edge_cost"]:
        out["theta_min_edge_cost"] = out["theta_max_edge_cost"]
    return out


def theta_vector_from_row(row: dict[str, Any]) -> np.ndarray:
    return clamp_numeric_theta([_finite_float(row.get(col), float(BASELINE_G556[idx])) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)])


def mode_columns(mode: str = "flow_shield") -> dict[str, int]:
    normalized = mode if mode in {"flow_shield", "agent_progress", "none"} else "flow_shield"
    return {
        "theta_goal_projection_mode_flow_shield": 1 if normalized == "flow_shield" else 0,
        "theta_goal_projection_mode_agent_progress": 1 if normalized == "agent_progress" else 0,
        "theta_goal_projection_mode_none": 1 if normalized == "none" else 0,
    }


def theta_mode(row: dict[str, Any]) -> str:
    raw = str(row.get("theta_goal_projection_mode", "")).strip()
    if raw in {"flow_shield", "agent_progress", "none"}:
        return raw
    scores = {
        "flow_shield": _finite_float(row.get("theta_goal_projection_mode_flow_shield"), 1.0),
        "agent_progress": _finite_float(row.get("theta_goal_projection_mode_agent_progress"), 0.0),
        "none": _finite_float(row.get("theta_goal_projection_mode_none"), 0.0),
    }
    return max(scores.items(), key=lambda item: item[1])[0]


def parse_updateparams_fingerprint(text: Any) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for part in str(text or "").split("|"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def expected_cpp_params(theta: dict[str, Any]) -> dict[str, Any]:
    row = clamp_theta_row(theta)
    return {
        "alpha_commit": row["theta_alpha_cong_commit_nonprogress"],
        "alpha_block": row["theta_alpha_cong_block"],
        "alpha_wait_spillover": row["theta_alpha_cong_wait_nonprogress"],
        "rho_decay": row["theta_rho_cong_decay"],
        "force_additive": 0,
        "enable_dual_channel": 1,
        "alpha_cong_commit_progress": row["theta_alpha_cong_commit_progress"],
        "alpha_cong_commit_nonprogress": row["theta_alpha_cong_commit_nonprogress"],
        "alpha_cong_block": row["theta_alpha_cong_block"],
        "alpha_cong_wait_progress": row["theta_alpha_cong_wait_progress"],
        "alpha_cong_wait_nonprogress": row["theta_alpha_cong_wait_nonprogress"],
        "alpha_flow_commit_progress": row["theta_alpha_flow_commit_progress"],
        "alpha_flow_wait_progress": row["theta_alpha_flow_wait_progress"],
        "rho_cong_decay": row["theta_rho_cong_decay"],
        "rho_flow_decay": row["theta_rho_flow_decay"],
        "lambda_cong": row["theta_lambda_cong"],
        "lambda_flow": row["theta_lambda_flow"],
        "min_edge_cost": row["theta_min_edge_cost"],
        "max_edge_cost": row["theta_max_edge_cost"],
        "goal_projection_mode": theta_mode(row),
        "flow_shield_beta": row["theta_flow_shield_beta"],
        "max_flow_shield": row["theta_max_flow_shield"],
    }


def compare_theta_to_fingerprint(fingerprint: Any, theta: dict[str, Any], tolerance: float = 1.0e-6) -> tuple[bool, list[str]]:
    parsed = parse_updateparams_fingerprint(fingerprint)
    expected = expected_cpp_params(theta)
    mismatched: list[str] = []
    for key, exp in expected.items():
        got = parsed.get(key)
        if got is None:
            mismatched.append(key)
            continue
        if key == "goal_projection_mode":
            if str(got) != str(exp):
                mismatched.append(key)
            continue
        try:
            if abs(float(got) - float(exp)) > tolerance:
                mismatched.append(key)
        except (TypeError, ValueError):
            mismatched.append(key)
    return not mismatched, mismatched


def schema_rows() -> list[dict[str, Any]]:
    return [asdict(field) for field in THETA_SCHEMA]


def schema_json() -> dict[str, Any]:
    return {
        "schema_version": "phase5p5_repair5g561_canonical_solver_theta_schema_v1",
        "numeric_columns": THETA_NUMERIC_COLUMNS,
        "mode_columns": THETA_MODE_COLUMNS,
        "fields": schema_rows(),
        "source_of_truth": "src/gcst/theta_schema.py",
    }

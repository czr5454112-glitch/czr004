"""Leakage-free feature contracts for G5.64.

G5.63's scalar scaling probe accidentally used label-derived context counts as
model inputs.  This module makes the allowed inference surface explicit and
keeps outcome columns quarantined for audit/reporting only.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import numpy as np


PRE_SOLVER_SCALAR_FEATURES = (
    "agent_count",
    "nominal_budget_ms",
    "base_time_limit_sec",
    "ltm_max_iterations",
    "agent_density",
    "path_found_rate",
    "nonzero_flow",
)

RICH_ACTOR_INPUTS = (
    "graph_topology",
    "paired_od",
    "directed_c0",
    "directed_f0",
    "agent_count",
    "solver_budget",
    "ltm_iteration_budget",
    "agent_density",
)

LABEL_OUTCOME_FEATURES = frozenset(
    {
        "label_state",
        "row_state",
        "positive_rows",
        "positive_count",
        "safe_rows",
        "safe_count",
        "safe_nonimproving_rows",
        "harmful_rows",
        "harmful_count",
        "censored_rows",
        "censored_count",
        "quality_delta_vs_g556",
        "best_positive_delta",
        "safe_improving_count",
        "labelv51_development_safe",
        "labelv51_comparable_quality",
        "labelv51_success_gain",
        "labelv51_success_regression",
        "labelv51_success_rate_delta",
        "labelv51_runtime_delta",
        "labelv51_quality_delta",
        "original_row_count",
        "candidate_rows",
        "candidate_rows_count_as_independent_contexts",
    }
)

G563_LEAKING_SCALAR_FEATURES = (
    "agent_count",
    "budget_ms",
    "original_row_count",
    "positive_rows",
    "safe_rows",
    "harmful_rows",
    "censored_rows",
)


@dataclass(frozen=True)
class FeatureAudit:
    feature_names: tuple[str, ...]
    forbidden_features: tuple[str, ...]
    allowed: bool
    schema_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "feature_names": list(self.feature_names),
            "forbidden_features": list(self.forbidden_features),
            "allowed": self.allowed,
            "schema_sha256": self.schema_sha256,
        }


def _canonical(name: str) -> str:
    return str(name).strip()


def feature_schema_sha256(feature_names: Sequence[str]) -> str:
    text = "\n".join(_canonical(name) for name in feature_names)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def forbidden_features(feature_names: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({_canonical(name) for name in feature_names if _canonical(name) in LABEL_OUTCOME_FEATURES}))


def audit_feature_schema(feature_names: Sequence[str]) -> FeatureAudit:
    names = tuple(_canonical(name) for name in feature_names)
    blocked = forbidden_features(names)
    return FeatureAudit(names, blocked, not blocked, feature_schema_sha256(names))


def assert_no_forbidden_features(feature_names: Sequence[str]) -> bool:
    audit = audit_feature_schema(feature_names)
    if not audit.allowed:
        raise AssertionError(f"label/outcome leakage features are forbidden: {list(audit.forbidden_features)}")
    return True


def export_schema_excludes_outcome_features(schema: dict[str, Any] | Sequence[str]) -> bool:
    if isinstance(schema, dict):
        names = schema.get("feature_names") or schema.get("features") or schema.keys()
    else:
        names = schema
    return assert_no_forbidden_features([str(name) for name in names])


def actor_inputs_are_pre_solver_only(input_names: Sequence[str]) -> bool:
    names = tuple(_canonical(name) for name in input_names)
    allowed = set(PRE_SOLVER_SCALAR_FEATURES) | set(RICH_ACTOR_INPUTS)
    unknown = sorted(name for name in names if name not in allowed)
    if unknown:
        raise AssertionError(f"actor inputs must be pre-solver fields only, got {unknown}")
    return assert_no_forbidden_features(names)


def _float(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        value = float(row.get(key, default))
    except Exception:
        return default
    return value if math.isfinite(value) else default


def leakage_free_scalar_vector(row: dict[str, Any]) -> np.ndarray:
    """Return the G5.64 scalar-control vector with no label-derived columns."""

    nonzero = str(row.get("nonzero_flow", "")).strip().lower() in {"1", "true", "yes", "y"}
    values = [
        _float(row, "agent_count", _float(row, "agents", 0.0)) / 256.0,
        _float(row, "nominal_budget_ms", _float(row, "budget_ms", 0.0)) / 10000.0,
        _float(row, "base_time_limit_sec", 0.5),
        _float(row, "ltm_max_iterations", 2.0) / 16.0,
        _float(row, "agent_density", 0.0),
        _float(row, "path_found_rate", 0.0),
        float(nonzero),
    ]
    return np.asarray(values, dtype=np.float32)


def leakage_report_dict() -> dict[str, Any]:
    g563_audit = audit_feature_schema(G563_LEAKING_SCALAR_FEATURES)
    g564_audit = audit_feature_schema(PRE_SOLVER_SCALAR_FEATURES)
    return {
        "schema_version": "phase5p5_repair5g564_leakage_feature_contract_v1",
        "g563_scalar_features": list(G563_LEAKING_SCALAR_FEATURES),
        "g563_forbidden_features": list(g563_audit.forbidden_features),
        "g563_scalar_scaling_valid_primary_evidence": False,
        "g564_pre_solver_scalar_features": list(PRE_SOLVER_SCALAR_FEATURES),
        "g564_forbidden_features": list(g564_audit.forbidden_features),
        "g564_feature_schema_sha256": g564_audit.schema_sha256,
        "rich_actor_inputs": list(RICH_ACTOR_INPUTS),
        "actor_inputs_pre_solver_only": True,
    }

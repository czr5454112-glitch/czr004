"""Versioned Label-v5.1 identity contracts for Repair5G.5.60."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

SCHEMA_VERSION = "label_v5.1_identity_safe"
ROUND = "phase5p5_repair5g560"
SOURCE_ROUND = "phase5p5_repair5g559"
PRIMARY_BASELINE = "g556_c063174"


def stable_sha256(parts: list[Any]) -> str:
    payload = json.dumps(parts, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LabelV51Identity:
    """Immutable row identity that never reuses legacy generic column names."""

    g560_plan_row_uid: str
    g560_instance_uid: str
    g560_evaluation_uid: str
    g560_physical_map_sha256: str
    g560_start_goal_assignment_sha256: str
    g560_solver_scenario_sha256: str
    g560_theta_id: str
    g560_candidate_id: str
    legacy_context_key: str
    legacy_solver_seed: str

    def digest(self) -> str:
        return identity_digest(asdict(self))


def legacy_context_key(row: dict[str, Any]) -> str:
    return "|".join(
        [
            str(row.get("map", "")),
            str(row.get("agent_count", row.get("agents", ""))),
            str(row.get("seed", row.get("solver_seed", ""))),
            str(row.get("nominal_budget_ms", row.get("budget_ms", ""))),
            str(row.get("horizon_id", "")),
        ]
    )


def identity_digest(row: dict[str, Any]) -> str:
    return stable_sha256(
        [
            row.get("g560_plan_row_uid", ""),
            row.get("g560_instance_uid", ""),
            row.get("g560_evaluation_uid", ""),
            row.get("g560_theta_id", ""),
            row.get("g560_physical_map_sha256", ""),
            row.get("g560_start_goal_assignment_sha256", ""),
            row.get("g560_solver_scenario_sha256", ""),
        ]
    )


def bool_text(value: Any) -> str:
    return "True" if bool(value) else "False"


def parse_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def parse_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if out == out and abs(out) != float("inf") else default

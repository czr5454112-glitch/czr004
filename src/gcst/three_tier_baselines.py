"""Three-tier baseline registry for Repair5G.5.66.

This module is intentionally solver-facing: it records the concrete aliases and
theta fingerprints that must be materialized in every G5.66 development and
blind replay panel.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .theta_schema import BASELINE_G556, THETA_NUMERIC_COLUMNS, clamp_theta_row, expected_cpp_params, mode_columns


ADDITIVE_SOLVER_ALIAS = "repair5g59_additive_fallback"
STATIC_FLOW_SOLVER_ALIAS = "repair5g59_static_flow_shield"
G556_SOLVER_ALIAS = "g556_c063174"


@dataclass(frozen=True)
class BaselineTier:
    tier: str
    canonical_report_id: str
    solver_alias: str
    registry_alias: str
    underlying_method: str
    role: str
    theta: dict[str, Any] | None
    required_force_additive: int
    required_enable_dual_channel: int
    source: str

    @property
    def fingerprint(self) -> str:
        if self.theta is None:
            return "force_additive=1|enable_dual_channel=0"
        return updateparams_fingerprint(self.theta)

    @property
    def source_sha256(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def registry_row(self) -> dict[str, Any]:
        row = {
            "candidate_id": self.solver_alias,
            "materialized_method": self.solver_alias,
            "tier": self.tier,
            "canonical_report_id": self.canonical_report_id,
            "solver_alias": self.solver_alias,
            "registry_alias": self.registry_alias,
            "underlying_method": self.underlying_method,
            "role": self.role,
            "required_force_additive": self.required_force_additive,
            "required_enable_dual_channel": self.required_enable_dual_channel,
            "expected_updateparams_fingerprint": self.fingerprint,
            "source": self.source,
            "source_sha256": self.source_sha256,
        }
        if self.theta is not None:
            row.update(self.theta)
        return row


def updateparams_fingerprint(theta: dict[str, Any]) -> str:
    params = expected_cpp_params(theta)
    return "|".join(f"{key}={value}" for key, value in params.items())


def g556_theta() -> dict[str, Any]:
    row = {col: float(value) for col, value in zip(THETA_NUMERIC_COLUMNS, BASELINE_G556)}
    row.update(mode_columns("flow_shield"))
    return clamp_theta_row(row)


def static_flow_theta() -> dict[str, Any]:
    row = {
        "theta_alpha_cong_commit_progress": 1.25,
        "theta_alpha_cong_commit_nonprogress": 1.25,
        "theta_alpha_cong_block": 1.25,
        "theta_alpha_cong_wait_progress": 0.75,
        "theta_alpha_cong_wait_nonprogress": 0.75,
        "theta_alpha_flow_commit_progress": 1.0,
        "theta_alpha_flow_wait_progress": 1.0,
        "theta_rho_cong_decay": 0.95,
        "theta_rho_flow_decay": 1.0,
        "theta_lambda_cong": 1.0,
        "theta_lambda_flow": 1.0,
        "theta_flow_shield_beta": 0.35,
        "theta_max_flow_shield": 0.75,
        "theta_min_edge_cost": 1.0,
        "theta_max_edge_cost": 11.0,
        **mode_columns("flow_shield"),
    }
    return clamp_theta_row(row)


TIER_A_ADDITIVE = BaselineTier(
    tier="A",
    canonical_report_id="paper_additive_ltm",
    solver_alias=ADDITIVE_SOLVER_ALIAS,
    registry_alias="paper_faithful_additive_ltm",
    underlying_method="additive_ltm_force_additive",
    role="tierA_additive_ltm",
    theta=None,
    required_force_additive=1,
    required_enable_dual_channel=0,
    source="G5.59 additive fallback alias and G5.66 plan section 5.1",
)

TIER_B_STATIC_FLOW = BaselineTier(
    tier="B",
    canonical_report_id="static_flow_shield_hand",
    solver_alias=STATIC_FLOW_SOLVER_ALIAS,
    registry_alias="repair5g2_best_frozen_static_candidate",
    underlying_method="repair5g1_shield_c125_b125_w075_d095_beta0p35_max0p75",
    role="tierB_static_flow_shield",
    theta=static_flow_theta(),
    required_force_additive=0,
    required_enable_dual_channel=1,
    source="scripts/repair5g545_common.py::static_flow_theta and historical repair5g59_static_flow_shield alias",
)

TIER_C_G556 = BaselineTier(
    tier="C",
    canonical_report_id=G556_SOLVER_ALIAS,
    solver_alias=G556_SOLVER_ALIAS,
    registry_alias=G556_SOLVER_ALIAS,
    underlying_method=G556_SOLVER_ALIAS,
    role="tierC_g556_fixed_global",
    theta=g556_theta(),
    required_force_additive=0,
    required_enable_dual_channel=1,
    source="src/gcst/theta_schema.py BASELINE_G556",
)

BASELINES: tuple[BaselineTier, BaselineTier, BaselineTier] = (TIER_A_ADDITIVE, TIER_B_STATIC_FLOW, TIER_C_G556)


def baseline_by_alias(alias: str) -> BaselineTier:
    wanted = str(alias)
    for tier in BASELINES:
        accepted = {
            tier.canonical_report_id,
            tier.solver_alias,
            tier.registry_alias,
            tier.underlying_method,
            tier.role,
        }
        if wanted in accepted:
            return tier
    raise KeyError(f"unknown G5.66 baseline alias: {alias}")


def baseline_registry_rows(extra_claims: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    claims = dict(extra_claims or {})
    return [{**tier.registry_row(), **claims} for tier in BASELINES]


def all_solver_aliases() -> list[str]:
    return [tier.solver_alias for tier in BASELINES]


def fingerprint_matches(parsed: dict[str, str], tier: BaselineTier, *, tolerance: float = 1.0e-6) -> tuple[bool, list[str]]:
    mismatches: list[str] = []
    force = parsed.get("force_additive")
    dual = parsed.get("enable_dual_channel")
    if force is not None and int(float(force)) != tier.required_force_additive:
        mismatches.append("force_additive")
    if dual is not None and int(float(dual)) != tier.required_enable_dual_channel:
        mismatches.append("enable_dual_channel")
    if tier.theta is None:
        return not mismatches and force == "1" and dual == "0", mismatches
    expected = expected_cpp_params(tier.theta)
    for key, value in expected.items():
        got = parsed.get(key)
        if got is None:
            mismatches.append(key)
            continue
        if key == "goal_projection_mode":
            if str(got) != str(value):
                mismatches.append(key)
            continue
        try:
            if abs(float(got) - float(value)) > tolerance:
                mismatches.append(key)
        except (TypeError, ValueError):
            mismatches.append(key)
    return not mismatches, mismatches


def registry_fingerprint_sha(rows: Iterable[dict[str, Any]]) -> str:
    payload = json.dumps(list(rows), sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

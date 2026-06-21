"""Opportunity-aware context labels for G5.65."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from .label_v52_set import LabelV52Context
from .repaired_set_risk import DEFAULT_REPAIRED_RISK, RepairedRiskConfig, context_loss_np, normalized_theta_distance_np
from .theta_schema import BASELINE_G556


TRIVIAL_G556_OPTIMAL = "TRIVIAL_G556_OPTIMAL"
NONTRIVIAL_OPPORTUNITY = "NONTRIVIAL_OPPORTUNITY"
MIXED_SAFETY_BOUNDARY = "MIXED_SAFETY_BOUNDARY"
UNSUPPORTED_CENSORED = "UNSUPPORTED_CENSORED"
HARMFUL_ONLY = "HARMFUL_ONLY"


@dataclass(frozen=True)
class OpportunityMetrics:
    evaluation_uid: str
    label_state: str
    opportunity_category: str
    g556_risk: float
    oracle_risk: float
    oracle_gap: float
    positive_mode_count: int
    harmful_count: int
    candidate_coverage: int
    censoring_rate: float
    nearest_positive_distance_from_g556: float | None
    harmful_boundary_distance: float | None
    loss_config_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "evaluation_uid": self.evaluation_uid,
            "label_state": self.label_state,
            "opportunity_category": self.opportunity_category,
            "g556_risk": self.g556_risk,
            "oracle_risk": self.oracle_risk,
            "oracle_gap": self.oracle_gap,
            "positive_mode_count": self.positive_mode_count,
            "harmful_count": self.harmful_count,
            "candidate_coverage": self.candidate_coverage,
            "censoring_rate": self.censoring_rate,
            "nearest_positive_distance_from_g556": self.nearest_positive_distance_from_g556,
            "harmful_boundary_distance": self.harmful_boundary_distance,
            "loss_config_sha256": self.loss_config_sha256,
        }


def oracle_theta_candidates(context: LabelV52Context) -> list[np.ndarray]:
    candidates: list[np.ndarray] = []
    candidates.append(BASELINE_G556.astype(np.float32))
    for row in [*context.positive_candidates, *context.safe_nonimproving_candidates]:
        candidates.append(row.theta.astype(np.float32))
    if not context.positive_candidates and context.harmful_candidates:
        candidates.append(BASELINE_G556.astype(np.float32))
    return candidates


def opportunity_metrics(
    context: LabelV52Context,
    cfg: RepairedRiskConfig = DEFAULT_REPAIRED_RISK,
    *,
    epsilon: float = 1.0e-4,
    boundary_distance: float = 0.05,
) -> OpportunityMetrics:
    g556_risk, _ = context_loss_np(BASELINE_G556, context, cfg)
    risks = [context_loss_np(theta, context, cfg)[0] for theta in oracle_theta_candidates(context)]
    oracle_risk = float(min(risks)) if risks else float(g556_risk)
    oracle_gap = max(0.0, float(g556_risk - oracle_risk))
    nearest_positive = None
    if len(context.positive_candidates):
        d = normalized_theta_distance_np(BASELINE_G556, context.positive_thetas)
        nearest_positive = float(d.min()) if d.size else None
    harmful_boundary = None
    if len(context.positive_candidates) and len(context.harmful_candidates):
        harmful_boundary = min(float(normalized_theta_distance_np(pos.theta, context.harmful_thetas).min()) for pos in context.positive_candidates)
    censoring_rate = len(context.censored_candidates) / max(1, context.original_row_count)
    if not len(context.positive_candidates) and not len(context.harmful_candidates):
        category = UNSUPPORTED_CENSORED
    elif len(context.harmful_candidates) and not len(context.positive_candidates):
        category = HARMFUL_ONLY
    elif harmful_boundary is not None and harmful_boundary <= float(boundary_distance):
        category = MIXED_SAFETY_BOUNDARY
    elif oracle_gap > float(epsilon):
        category = NONTRIVIAL_OPPORTUNITY
    else:
        category = TRIVIAL_G556_OPTIMAL
    return OpportunityMetrics(
        evaluation_uid=context.evaluation_uid,
        label_state=context.label_state,
        opportunity_category=category,
        g556_risk=float(g556_risk),
        oracle_risk=float(oracle_risk),
        oracle_gap=float(oracle_gap),
        positive_mode_count=len(context.positive_candidates),
        harmful_count=len(context.harmful_candidates),
        candidate_coverage=context.original_row_count,
        censoring_rate=float(censoring_rate),
        nearest_positive_distance_from_g556=nearest_positive,
        harmful_boundary_distance=harmful_boundary,
        loss_config_sha256=cfg.sha256,
    )


def opportunity_table(contexts: Sequence[LabelV52Context], cfg: RepairedRiskConfig = DEFAULT_REPAIRED_RISK) -> list[dict[str, Any]]:
    return [opportunity_metrics(context, cfg).as_dict() for context in contexts]


def normalized_oracle_regret(actor_risk: float, metrics: OpportunityMetrics, *, epsilon: float = 1.0e-4) -> float:
    denom = max(float(metrics.g556_risk - metrics.oracle_risk), float(epsilon))
    return float((float(actor_risk) - float(metrics.oracle_risk)) / denom)

"""Loss helpers for Phase4F LAU-LTM update-rule training."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import torch
    import torch.nn.functional as F
except ImportError:  # pragma: no cover - exercised only outside the project env
    torch = None
    F = None


@dataclass(frozen=True)
class LaurLossWeights:
    rule_ce: float = 1.0
    safety_bce: float = 0.5
    delta_regression: float = 0.25
    ltm_regularization: float = 0.02
    neutral_regularization_multiplier: float = 2.0


def require_torch() -> None:
    if torch is None or F is None:
        raise RuntimeError(
            "PyTorch is required for LAU-LTM training. Use the czr004 conda "
            "environment from environment.yml."
        )


def laur_ltm_loss(
    outputs: dict[str, Any],
    *,
    rule_target: Any,
    rule_target_probs: Any | None = None,
    harmful_target: Any,
    delta_target: Any,
    neutral_target: Any,
    additive_index: int,
    neutral_index: int | None,
    weights: LaurLossWeights | None = None,
) -> dict[str, Any]:
    """Compute the Phase4F multi-head loss.

    The regularization term penalizes probability mass assigned to active
    non-additive update rules; `additive_ltm` and `neutral_additive` are treated
    as fallback-compatible classes.
    """

    require_torch()
    opts = weights or LaurLossWeights()
    logits = outputs["rule_logits"]
    probs = torch.softmax(logits, dim=-1)
    if rule_target_probs is None:
        rule_loss = F.cross_entropy(logits, rule_target)
    else:
        rule_loss = -(rule_target_probs.float() * F.log_softmax(logits, dim=-1)).sum(dim=-1).mean()
    safety_loss = F.binary_cross_entropy_with_logits(
        outputs["safety_logit"], harmful_target.float()
    )
    delta_loss = F.smooth_l1_loss(outputs["delta_pred"], delta_target.float())

    safe_mask = torch.zeros(logits.shape[-1], device=logits.device, dtype=logits.dtype)
    safe_mask[int(additive_index)] = 1.0
    if neutral_index is not None:
        safe_mask[int(neutral_index)] = 1.0
    non_additive_probability = (probs * (1.0 - safe_mask)).sum(dim=-1)
    neutral_multiplier = 1.0 + neutral_target.float() * (
        float(opts.neutral_regularization_multiplier) - 1.0
    )
    regularization_loss = (non_additive_probability * neutral_multiplier).mean()

    total = (
        float(opts.rule_ce) * rule_loss
        + float(opts.safety_bce) * safety_loss
        + float(opts.delta_regression) * delta_loss
        + float(opts.ltm_regularization) * regularization_loss
    )
    return {
        "total": total,
        "rule_ce": rule_loss.detach(),
        "safety_bce": safety_loss.detach(),
        "delta_regression": delta_loss.detach(),
        "additive_deviation_penalty": regularization_loss.detach(),
    }

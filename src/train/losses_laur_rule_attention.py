"""Losses for Phase4F Repair2 rule-conditioned attention training."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import torch
    import torch.nn.functional as F
except ImportError:  # pragma: no cover - exercised only outside project env
    torch = None
    F = None


@dataclass(frozen=True)
class RuleAttentionLossWeights:
    listwise_kl: float = 1.0
    pairwise_margin: float = 0.35
    delta_regression: float = 0.4
    harmful_bce: float = 0.35
    family_ce: float = 0.1
    additive_regularization: float = 0.02
    neutral_regularization_multiplier: float = 2.0


def require_torch() -> None:
    if torch is None or F is None:
        raise RuntimeError("PyTorch is required for LAU rule-attention losses")


def laur_rule_attention_loss(
    outputs: dict[str, Any],
    targets: dict[str, Any],
    *,
    additive_index: int,
    weights: RuleAttentionLossWeights | None = None,
) -> dict[str, Any]:
    """Compute listwise, ranking, delta, safety, and family losses."""

    require_torch()
    opts = weights or RuleAttentionLossWeights()
    scores = outputs["rule_score"]
    harmful_logit = outputs["harmful_logit"]
    soft_target = targets["soft_rule_target"].float()
    rule_target = targets["rule_target"].long()
    delta_target = targets["delta_target"].float()
    harmful_target = targets["harmful_target"].float()
    family_target = targets["family_target"].long()
    neutral_target = targets["neutral_target"].float()

    listwise_loss = -(soft_target * F.log_softmax(scores, dim=-1)).sum(dim=-1).mean()

    target_scores = scores.gather(1, rule_target.view(-1, 1))
    non_target = torch.ones_like(scores, dtype=torch.bool)
    non_target.scatter_(1, rule_target.view(-1, 1), False)
    margin_loss = F.relu(float(opts.pairwise_margin) - (target_scores - scores))
    margin_loss = margin_loss.masked_select(non_target).mean()

    delta_loss = F.smooth_l1_loss(scores, delta_target)
    harmful_loss = F.binary_cross_entropy_with_logits(harmful_logit, harmful_target)
    selected_family_logits = outputs["family_logits"][
        torch.arange(scores.shape[0], device=scores.device), rule_target
    ]
    family_loss = F.cross_entropy(selected_family_logits, family_target)

    probs = torch.softmax(scores, dim=-1)
    additive_probability = probs[:, int(additive_index)]
    neutral_multiplier = 1.0 + neutral_target * (
        float(opts.neutral_regularization_multiplier) - 1.0
    )
    additive_reg = ((1.0 - additive_probability) * neutral_multiplier).mean()

    total = (
        float(opts.listwise_kl) * listwise_loss
        + float(opts.pairwise_margin) * margin_loss
        + float(opts.delta_regression) * delta_loss
        + float(opts.harmful_bce) * harmful_loss
        + float(opts.family_ce) * family_loss
        + float(opts.additive_regularization) * additive_reg
    )
    return {
        "total": total,
        "listwise_kl": listwise_loss.detach(),
        "pairwise_margin": margin_loss.detach(),
        "delta_regression": delta_loss.detach(),
        "harmful_bce": harmful_loss.detach(),
        "family_ce": family_loss.detach(),
        "additive_regularization": additive_reg.detach(),
    }

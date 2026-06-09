"""Losses for LAU-StableAttention-v1 update-rule models."""

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
class StableAttentionLossWeights:
    lambda_listwise: float = 1.0
    lambda_pairwise: float = 0.5
    lambda_delta: float = 0.5
    lambda_safe: float = 2.0
    lambda_family: float = 0.1
    lambda_conf: float = 0.1
    lambda_additive: float = 0.1
    pairwise_margin: float = 0.005
    harmful_pos_weight: float = 1.0


def require_torch() -> None:
    if torch is None or F is None:
        raise RuntimeError("PyTorch is required for LAU stable-attention losses")


def _pairwise_margin_loss(q_delta: Any, delta_target: Any, margin: float) -> Any:
    target_diff = delta_target.unsqueeze(2) - delta_target.unsqueeze(1)
    score_diff = q_delta.unsqueeze(2) - q_delta.unsqueeze(1)
    mask = target_diff > float(margin)
    if not bool(mask.any()):
        return q_delta.new_tensor(0.0)
    return F.relu(float(margin) - score_diff).masked_select(mask).mean()


def laur_stable_attention_loss(
    outputs: dict[str, Any],
    targets: dict[str, Any],
    *,
    additive_index: int,
    weights: StableAttentionLossWeights | None = None,
) -> dict[str, Any]:
    """Compute listwise, pairwise, delta, safety, family, and fallback losses."""

    require_torch()
    opts = weights or StableAttentionLossWeights()
    q_delta = outputs["q_delta"]
    harmful_logit = outputs["harmful_logit"]
    soft_target = targets["soft_rule_target_stable"].float()
    delta_target = targets["delta_target"].float()
    harmful_target = targets["harmful_target"].float()
    rule_target = targets["rule_target"].long()
    family_target = targets["family_target"].long()
    neutral_target = targets["neutral_target"].float()
    confidence_target = targets["confidence_target"].float()

    listwise_loss = F.kl_div(F.log_softmax(q_delta, dim=-1), soft_target, reduction="batchmean")
    pairwise_loss = _pairwise_margin_loss(q_delta, delta_target, opts.pairwise_margin)
    delta_loss = F.smooth_l1_loss(q_delta, delta_target)
    pos_weight = torch.tensor(float(opts.harmful_pos_weight), dtype=q_delta.dtype, device=q_delta.device)
    harmful_loss = F.binary_cross_entropy_with_logits(
        harmful_logit,
        harmful_target,
        pos_weight=pos_weight,
    )
    selected_family_logits = outputs["family_logits"][
        torch.arange(q_delta.shape[0], device=q_delta.device), rule_target
    ]
    family_loss = F.cross_entropy(selected_family_logits, family_target)
    selected_confidence = outputs["confidence_logit"].gather(1, rule_target.view(-1, 1)).squeeze(1)
    confidence_loss = F.binary_cross_entropy_with_logits(selected_confidence, confidence_target)
    additive_score = q_delta[:, int(additive_index)]
    non_additive = torch.cat(
        [q_delta[:, : int(additive_index)], q_delta[:, int(additive_index) + 1 :]],
        dim=1,
    )
    max_non_additive = non_additive.max(dim=1).values if non_additive.shape[1] else additive_score
    additive_loss = (F.relu(max_non_additive - additive_score) * neutral_target).mean()

    total = (
        float(opts.lambda_listwise) * listwise_loss
        + float(opts.lambda_pairwise) * pairwise_loss
        + float(opts.lambda_delta) * delta_loss
        + float(opts.lambda_safe) * harmful_loss
        + float(opts.lambda_family) * family_loss
        + float(opts.lambda_conf) * confidence_loss
        + float(opts.lambda_additive) * additive_loss
    )
    return {
        "total": total,
        "listwise_kl": listwise_loss.detach(),
        "pairwise_margin": pairwise_loss.detach(),
        "delta_regression": delta_loss.detach(),
        "harmful_bce": harmful_loss.detach(),
        "family_ce": family_loss.detach(),
        "confidence_bce": confidence_loss.detach(),
        "additive_regularization": additive_loss.detach(),
    }

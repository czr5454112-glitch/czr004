"""Losses for Phase4F Repair5 attention-native LAUR models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import torch
    import torch.nn.functional as F
except ImportError:  # pragma: no cover
    torch = None
    F = None


@dataclass(frozen=True)
class AttentionNativeLossWeights:
    lambda_listwise: float = 1.0
    lambda_pairwise: float = 1.0
    lambda_rule_ce: float = 0.0
    lambda_rule_margin: float = 0.0
    lambda_delta: float = 0.5
    lambda_harmful: float = 2.0
    lambda_harmful_pairwise: float = 0.0
    lambda_high_margin_harmful: float = 0.0
    lambda_anti_candidate_safety: float = 0.0
    lambda_opportunity: float = 1.0
    lambda_defer: float = 0.5
    lambda_anti_escape: float = 2.0
    lambda_family: float = 0.1
    anti_escape_score_margin: float = 0.005
    rule_margin: float = 0.010
    rule_ce_high_margin_weight: float = 1.0
    rule_margin_high_margin_weight: float = 1.0
    harmful_pairwise_margin: float = 0.25
    harmful_pos_weight: float = 1.0
    harmful_negative_weight: float = 1.0
    harmful_focal_gamma: float = 0.0
    opportunity_pos_weight: float = 1.0


def require_torch() -> None:
    if torch is None or F is None:
        raise RuntimeError("PyTorch is required for LAU attention-native losses")


def _pairwise_ranknet_loss(rule_score: Any, targets: dict[str, Any]) -> Any:
    dominance = targets["pairwise_dominance"].float()
    observed = targets["pairwise_observed"].float()
    score_diff = rule_score.unsqueeze(2) - rule_score.unsqueeze(1)
    mask = observed > 0.5
    if not bool(mask.any()):
        return rule_score.new_tensor(0.0)
    return F.binary_cross_entropy_with_logits(
        score_diff.masked_select(mask),
        dominance.masked_select(mask),
    )


def _anti_escape_loss(
    rule_score: Any,
    defer_logit: Any,
    targets: dict[str, Any],
    *,
    additive_index: int,
    margin: float,
) -> Any:
    sample_mask = targets["anti_escape_sample"].float() > 0.5
    if not bool(sample_mask.any()):
        return rule_score.new_tensor(0.0)
    candidate_mask = targets["anti_escape_candidate_mask"].bool()
    very_low = rule_score.new_full(rule_score.shape, -1.0e9)
    candidate_scores = torch.where(candidate_mask, rule_score, very_low)
    best_nonadditive = candidate_scores.max(dim=1).values
    active_best = best_nonadditive.masked_select(sample_mask)
    additive_score = rule_score[:, int(additive_index)].masked_select(sample_mask)
    active_defer = defer_logit.masked_select(sample_mask)
    return (
        F.relu(additive_score + float(margin) - active_best).mean()
        + F.relu(active_defer + float(margin) - active_best).mean()
    )


def _weighted_focal_bce_with_logits(
    logits: Any,
    target: Any,
    *,
    pos_weight: float,
    negative_weight: float,
    gamma: float,
) -> Any:
    per_item = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
    weight = target * float(pos_weight) + (1.0 - target) * float(negative_weight)
    if float(gamma) > 0.0:
        prob = torch.sigmoid(logits)
        prob_target = target * prob + (1.0 - target) * (1.0 - prob)
        weight = weight * torch.pow((1.0 - prob_target).clamp_min(1.0e-6), float(gamma))
    return (per_item * weight).mean()


def _harmful_pairwise_margin_loss(harmful_logit: Any, harmful_target: Any, *, margin: float) -> Any:
    positive = harmful_target.float() > 0.5
    negative = ~positive
    pair_mask = positive.unsqueeze(2) & negative.unsqueeze(1)
    if not bool(pair_mask.any()):
        return harmful_logit.new_tensor(0.0)
    diff = harmful_logit.unsqueeze(2) - harmful_logit.unsqueeze(1)
    return F.relu(float(margin) - diff.masked_select(pair_mask)).mean()


def _high_margin_harmful_loss(harmful_logit: Any, harmful_target: Any, targets: dict[str, Any], opts: AttentionNativeLossWeights) -> Any:
    high_margin = targets.get("high_margin_opportunity_mask")
    if high_margin is None:
        return harmful_logit.new_tensor(0.0)
    sample_mask = high_margin.float() > 0.5
    if not bool(sample_mask.any()):
        return harmful_logit.new_tensor(0.0)
    return _weighted_focal_bce_with_logits(
        harmful_logit[sample_mask],
        harmful_target[sample_mask],
        pos_weight=float(opts.harmful_pos_weight),
        negative_weight=float(opts.harmful_negative_weight),
        gamma=float(opts.harmful_focal_gamma),
    )


def _anti_candidate_safety_loss(harmful_logit: Any, targets: dict[str, Any]) -> Any:
    sample_mask = targets["anti_escape_sample"].float() > 0.5
    candidate_mask = targets["anti_escape_candidate_mask"].bool()
    mask = candidate_mask & sample_mask.unsqueeze(1)
    if not bool(mask.any()):
        return harmful_logit.new_tensor(0.0)
    return F.binary_cross_entropy_with_logits(harmful_logit.masked_select(mask), harmful_logit.new_zeros(int(mask.sum())))


def _high_margin_weight(targets: dict[str, Any], base_mask: Any, *, high_margin_weight: float) -> Any:
    high_margin = targets.get("high_margin_opportunity_mask")
    if high_margin is None:
        return base_mask.float()
    return 1.0 + (float(high_margin_weight) - 1.0) * high_margin.float().masked_select(base_mask)


def _weighted_rule_ce_loss(
    rule_score: Any,
    target_rule: Any,
    targets: dict[str, Any],
    *,
    use_nonadditive_mask: Any,
    high_margin_weight: float,
) -> Any:
    if not bool(use_nonadditive_mask.any()):
        return rule_score.new_tensor(0.0)
    per_sample = F.cross_entropy(
        rule_score[use_nonadditive_mask],
        target_rule[use_nonadditive_mask],
        reduction="none",
    )
    sample_weight = _high_margin_weight(targets, use_nonadditive_mask, high_margin_weight=high_margin_weight).to(
        dtype=per_sample.dtype,
        device=per_sample.device,
    )
    return (per_sample * sample_weight).sum() / sample_weight.sum().clamp_min(1.0e-6)


def _target_rule_margin_loss(
    rule_score: Any,
    target_rule: Any,
    targets: dict[str, Any],
    *,
    use_nonadditive_mask: Any,
    margin: float,
    high_margin_weight: float,
) -> Any:
    if not bool(use_nonadditive_mask.any()):
        return rule_score.new_tensor(0.0)
    active_scores = rule_score[use_nonadditive_mask]
    active_target = target_rule[use_nonadditive_mask].clamp(min=0, max=active_scores.shape[1] - 1)
    target_scores = active_scores.gather(1, active_target.unsqueeze(1)).squeeze(1)
    other_scores = active_scores.clone()
    other_scores.scatter_(1, active_target.unsqueeze(1), -1.0e9)
    strongest_other = other_scores.max(dim=1).values
    per_sample = F.relu(strongest_other + float(margin) - target_scores)
    sample_weight = _high_margin_weight(targets, use_nonadditive_mask, high_margin_weight=high_margin_weight).to(
        dtype=per_sample.dtype,
        device=per_sample.device,
    )
    return (per_sample * sample_weight).sum() / sample_weight.sum().clamp_min(1.0e-6)


def laur_attention_native_loss(
    outputs: dict[str, Any],
    targets: dict[str, Any],
    *,
    additive_index: int,
    weights: AttentionNativeLossWeights | None = None,
) -> dict[str, Any]:
    """Compute Repair5 listwise, pairwise, safety, opportunity, and anti-escape losses."""

    require_torch()
    opts = weights or AttentionNativeLossWeights()
    rule_score = outputs["rule_score"]
    delta_pred = outputs["delta_pred"]
    harmful_logit = outputs["harmful_logit"]
    opportunity_logit = outputs["opportunity_logit"]
    defer_logit = outputs["defer_logit"]

    soft_target = targets["soft_utility_target"].float()
    utility_target = targets["utility_target"].float()
    harmful_target = targets["harmful_target"].float()
    opportunity_target = targets["opportunity_target"].float()
    defer_target = targets["defer_target"].float()
    family_target = targets["family_target"].long()
    use_nonadditive_mask = targets["use_nonadditive_mask"].bool()
    target_rule = targets["rule_target"].long()

    listwise_loss = F.kl_div(F.log_softmax(rule_score, dim=-1), soft_target, reduction="batchmean")
    pairwise_loss = _pairwise_ranknet_loss(rule_score, targets)
    rule_ce_loss = _weighted_rule_ce_loss(
        rule_score,
        target_rule,
        targets,
        use_nonadditive_mask=use_nonadditive_mask,
        high_margin_weight=float(opts.rule_ce_high_margin_weight),
    )
    rule_margin_loss = _target_rule_margin_loss(
        rule_score,
        target_rule,
        targets,
        use_nonadditive_mask=use_nonadditive_mask,
        margin=float(opts.rule_margin),
        high_margin_weight=float(opts.rule_margin_high_margin_weight),
    )
    delta_loss = F.smooth_l1_loss(delta_pred, utility_target)
    harmful_loss = _weighted_focal_bce_with_logits(
        harmful_logit,
        harmful_target,
        pos_weight=float(opts.harmful_pos_weight),
        negative_weight=float(opts.harmful_negative_weight),
        gamma=float(opts.harmful_focal_gamma),
    )
    harmful_pairwise_loss = _harmful_pairwise_margin_loss(
        harmful_logit,
        harmful_target,
        margin=float(opts.harmful_pairwise_margin),
    )
    high_margin_harmful_loss = _high_margin_harmful_loss(harmful_logit, harmful_target, targets, opts)
    anti_candidate_safety_loss = _anti_candidate_safety_loss(harmful_logit, targets)
    opportunity_pos_weight = torch.tensor(
        float(opts.opportunity_pos_weight),
        dtype=rule_score.dtype,
        device=rule_score.device,
    )
    opportunity_loss = F.binary_cross_entropy_with_logits(
        opportunity_logit,
        opportunity_target,
        pos_weight=opportunity_pos_weight,
    )
    defer_loss = F.binary_cross_entropy_with_logits(defer_logit, defer_target)
    if bool(use_nonadditive_mask.any()):
        selected_family_logits = outputs["family_logits"][
            torch.arange(rule_score.shape[0], device=rule_score.device), target_rule.clamp_min(0)
        ]
        family_loss = F.cross_entropy(
            selected_family_logits[use_nonadditive_mask],
            family_target[use_nonadditive_mask],
        )
    else:
        family_loss = rule_score.new_tensor(0.0)
    anti_escape_loss = _anti_escape_loss(
        rule_score,
        defer_logit,
        targets,
        additive_index=additive_index,
        margin=float(opts.anti_escape_score_margin),
    )

    total = (
        float(opts.lambda_listwise) * listwise_loss
        + float(opts.lambda_pairwise) * pairwise_loss
        + float(opts.lambda_rule_ce) * rule_ce_loss
        + float(opts.lambda_rule_margin) * rule_margin_loss
        + float(opts.lambda_delta) * delta_loss
        + float(opts.lambda_harmful) * harmful_loss
        + float(opts.lambda_harmful_pairwise) * harmful_pairwise_loss
        + float(opts.lambda_high_margin_harmful) * high_margin_harmful_loss
        + float(opts.lambda_anti_candidate_safety) * anti_candidate_safety_loss
        + float(opts.lambda_opportunity) * opportunity_loss
        + float(opts.lambda_defer) * defer_loss
        + float(opts.lambda_anti_escape) * anti_escape_loss
        + float(opts.lambda_family) * family_loss
    )
    return {
        "total": total,
        "listwise_kl": listwise_loss.detach(),
        "pairwise_ranknet": pairwise_loss.detach(),
        "rule_ce": rule_ce_loss.detach(),
        "rule_margin": rule_margin_loss.detach(),
        "utility_regression": delta_loss.detach(),
        "harmful_bce": harmful_loss.detach(),
        "harmful_pairwise_margin": harmful_pairwise_loss.detach(),
        "high_margin_harmful_bce": high_margin_harmful_loss.detach(),
        "anti_candidate_safety_bce": anti_candidate_safety_loss.detach(),
        "opportunity_bce": opportunity_loss.detach(),
        "defer_bce": defer_loss.detach(),
        "anti_escape_margin": anti_escape_loss.detach(),
        "family_ce": family_loss.detach(),
    }

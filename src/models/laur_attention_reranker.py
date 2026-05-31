"""Second-stage candidate reranker for Repair5C LAUR attention outputs."""

from __future__ import annotations

from typing import Any

try:
    import torch
    from torch import nn
except ImportError:  # pragma: no cover
    torch = None
    nn = None


MODEL_SCHEMA_VERSION = "laur_attention_reranker_v1_checkpoint"
MODEL_NAME = "LAU-TopKRuleReranker-v1"


def torch_available() -> bool:
    return torch is not None and nn is not None


def require_torch() -> None:
    if not torch_available():
        raise RuntimeError("PyTorch is required for LAUR attention reranking")


if torch_available():

    class LAUTopKRuleRerankerV1(nn.Module):
        """MLP reranker over a small set of candidate rules.

        Inputs are per-candidate numeric features plus an executable-rule id.
        The model scores only the supplied candidates; callers should mask any
        padded candidate slots before computing losses or selecting argmax.
        """

        def __init__(
            self,
            *,
            feature_dim: int,
            num_rules: int,
            rule_embedding_dim: int = 8,
            hidden_dim: int = 48,
            dropout: float = 0.1,
        ) -> None:
            super().__init__()
            self.feature_dim = int(feature_dim)
            self.num_rules = int(num_rules)
            self.rule_embedding_dim = int(rule_embedding_dim)
            self.hidden_dim = int(hidden_dim)
            self.dropout = float(dropout)
            self.model_name = MODEL_NAME
            self.rule_embedding = nn.Embedding(self.num_rules, self.rule_embedding_dim)
            self.net = nn.Sequential(
                nn.LayerNorm(self.feature_dim + self.rule_embedding_dim),
                nn.Linear(self.feature_dim + self.rule_embedding_dim, self.hidden_dim),
                nn.GELU(),
                nn.Dropout(self.dropout),
                nn.Linear(self.hidden_dim, self.hidden_dim),
                nn.GELU(),
                nn.Dropout(self.dropout),
                nn.Linear(self.hidden_dim, 1),
            )

        def forward(self, batch: dict[str, Any]) -> dict[str, Any]:
            features = batch["candidate_features"]
            rule_indices = batch["candidate_rule_indices"].long()
            mask = batch.get("candidate_mask")
            embedded = self.rule_embedding(rule_indices)
            scores = self.net(torch.cat([features, embedded], dim=-1)).squeeze(-1)
            if mask is not None:
                scores = scores.masked_fill(~mask.bool(), -1.0e9)
            return {"candidate_scores": scores}

else:

    class LAUTopKRuleRerankerV1:  # type: ignore[no-redef]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            require_torch()


def build_model(model_name: str, **kwargs: Any) -> Any:
    require_torch()
    if model_name != MODEL_NAME:
        raise ValueError(f"unknown LAUR reranker model {model_name}")
    return LAUTopKRuleRerankerV1(**kwargs)


def parameter_count(model: Any) -> int:
    require_torch()
    return int(sum(parameter.numel() for parameter in model.parameters()))

"""Stable-target attention models for LAU update-rule prediction."""

from __future__ import annotations

from typing import Any

try:
    import torch
    from torch import nn
except ImportError:  # pragma: no cover - exercised only outside the project env
    torch = None
    nn = None


MODEL_SCHEMA_VERSION = "laur_stable_attention_v1_checkpoint"
MODEL_FAMILY_NAME = "LAU-StableAttention-v1"
SET_RULE_TRANSFORMER_NAME = "LAU-SetRuleTransformer-v1"
EDGE_TRACE_TRANSFORMER_NAME = "LAU-EdgeTraceTransformer-v3"


def torch_available() -> bool:
    return torch is not None and nn is not None


def require_torch() -> None:
    if not torch_available():
        raise RuntimeError("PyTorch is required for LAU stable-attention training")


if torch_available():

    class NumericEncoder(nn.Module):
        def __init__(self, input_dim: int, d_model: int, dropout: float = 0.0) -> None:
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(int(input_dim), int(d_model)),
                nn.LayerNorm(int(d_model)),
                nn.GELU(),
                nn.Dropout(float(dropout)),
            )

        def forward(self, values: Any) -> Any:
            return self.net(values)


    class LAUSetRuleTransformerV1(nn.Module):
        """Rule-conditioned Set Transformer over global, edge, and rule tokens."""

        def __init__(
            self,
            *,
            global_dim: int,
            edge_dim: int,
            rule_dim: int,
            num_rules: int,
            num_families: int,
            d_model: int = 64,
            n_heads: int = 2,
            n_layers: int = 2,
            dropout: float = 0.1,
        ) -> None:
            super().__init__()
            self.global_dim = int(global_dim)
            self.edge_dim = int(edge_dim)
            self.trace_dim = 0
            self.rule_dim = int(rule_dim)
            self.num_rules = int(num_rules)
            self.num_families = int(num_families)
            self.d_model = int(d_model)
            self.n_heads = int(n_heads)
            self.n_layers = int(n_layers)
            self.dropout = float(dropout)
            self.model_name = SET_RULE_TRANSFORMER_NAME

            self.global_encoder = NumericEncoder(self.global_dim, self.d_model, dropout)
            self.edge_encoder = NumericEncoder(self.edge_dim, self.d_model, dropout)
            self.rule_encoder = NumericEncoder(self.rule_dim, self.d_model, dropout)
            self.type_embedding = nn.Embedding(3, self.d_model)

            encoder_layer = nn.TransformerEncoderLayer(
                d_model=self.d_model,
                nhead=self.n_heads,
                dim_feedforward=self.d_model * 4,
                dropout=self.dropout,
                batch_first=True,
                activation="gelu",
                norm_first=True,
            )
            self.edge_set_encoder = nn.TransformerEncoder(encoder_layer, num_layers=self.n_layers)
            self.rule_cross_attention = nn.MultiheadAttention(
                self.d_model,
                self.n_heads,
                dropout=self.dropout,
                batch_first=True,
            )
            rule_layer = nn.TransformerEncoderLayer(
                d_model=self.d_model,
                nhead=self.n_heads,
                dim_feedforward=self.d_model * 4,
                dropout=self.dropout,
                batch_first=True,
                activation="gelu",
                norm_first=True,
            )
            self.rule_self_attention = nn.TransformerEncoder(rule_layer, num_layers=1)
            self.rule_norm = nn.LayerNorm(self.d_model)
            self.q_delta_head = nn.Linear(self.d_model, 1)
            self.harmful_head = nn.Linear(self.d_model, 1)
            self.family_head = nn.Linear(self.d_model, self.num_families)
            self.confidence_head = nn.Linear(self.d_model, 1)

        def _context_tokens(self, batch: dict[str, Any]) -> tuple[Any, Any]:
            global_x = batch["global_features"]
            edge_x = batch["edge_tokens"]
            edge_mask = batch["edge_mask"].bool()
            batch_size = global_x.shape[0]
            global_token = self.global_encoder(global_x).unsqueeze(1)
            global_token = global_token + self.type_embedding.weight[0].view(1, 1, -1)
            edge_tokens = self.edge_encoder(edge_x) + self.type_embedding.weight[1].view(1, 1, -1)
            context = torch.cat([global_token, edge_tokens], dim=1)
            context_mask = torch.cat(
                [
                    torch.ones((batch_size, 1), dtype=torch.bool, device=global_x.device),
                    edge_mask,
                ],
                dim=1,
            )
            return context, context_mask

        def forward(self, batch: dict[str, Any]) -> dict[str, Any]:
            context, context_mask = self._context_tokens(batch)
            encoded = self.edge_set_encoder(context, src_key_padding_mask=~context_mask)
            rule_tokens = self.rule_encoder(batch["rule_tokens"])
            rule_tokens = rule_tokens + self.type_embedding.weight[2].view(1, 1, -1)
            attended, _ = self.rule_cross_attention(
                query=rule_tokens,
                key=encoded,
                value=encoded,
                key_padding_mask=~context_mask,
                need_weights=False,
            )
            rule_hidden = self.rule_norm(rule_tokens + attended)
            rule_hidden = self.rule_self_attention(rule_hidden)
            return {
                "q_delta": self.q_delta_head(rule_hidden).squeeze(-1),
                "harmful_logit": self.harmful_head(rule_hidden).squeeze(-1),
                "family_logits": self.family_head(rule_hidden),
                "confidence_logit": self.confidence_head(rule_hidden).squeeze(-1),
            }


    class LAUEdgeTraceTransformerV3(LAUSetRuleTransformerV1):
        """Stable attention variant that also encodes compressed trace tokens."""

        def __init__(
            self,
            *,
            global_dim: int,
            edge_dim: int,
            trace_dim: int,
            rule_dim: int,
            num_rules: int,
            num_families: int,
            d_model: int = 96,
            n_heads: int = 4,
            n_layers: int = 2,
            dropout: float = 0.1,
        ) -> None:
            super().__init__(
                global_dim=global_dim,
                edge_dim=edge_dim,
                rule_dim=rule_dim,
                num_rules=num_rules,
                num_families=num_families,
                d_model=d_model,
                n_heads=n_heads,
                n_layers=n_layers,
                dropout=dropout,
            )
            self.trace_dim = int(trace_dim)
            self.model_name = EDGE_TRACE_TRANSFORMER_NAME
            self.trace_encoder = NumericEncoder(self.trace_dim, self.d_model, dropout)
            self.type_embedding = nn.Embedding(4, self.d_model)

        def _context_tokens(self, batch: dict[str, Any]) -> tuple[Any, Any]:
            global_x = batch["global_features"]
            edge_x = batch["edge_tokens"]
            trace_x = batch["trace_tokens"]
            edge_mask = batch["edge_mask"].bool()
            trace_mask = batch["trace_mask"].bool()
            batch_size = global_x.shape[0]
            global_token = self.global_encoder(global_x).unsqueeze(1)
            global_token = global_token + self.type_embedding.weight[0].view(1, 1, -1)
            edge_tokens = self.edge_encoder(edge_x) + self.type_embedding.weight[1].view(1, 1, -1)
            trace_tokens = self.trace_encoder(trace_x) + self.type_embedding.weight[2].view(1, 1, -1)
            context = torch.cat([global_token, edge_tokens, trace_tokens], dim=1)
            context_mask = torch.cat(
                [
                    torch.ones((batch_size, 1), dtype=torch.bool, device=global_x.device),
                    edge_mask,
                    trace_mask,
                ],
                dim=1,
            )
            return context, context_mask

        def forward(self, batch: dict[str, Any]) -> dict[str, Any]:
            context, context_mask = self._context_tokens(batch)
            encoded = self.edge_set_encoder(context, src_key_padding_mask=~context_mask)
            rule_tokens = self.rule_encoder(batch["rule_tokens"])
            rule_tokens = rule_tokens + self.type_embedding.weight[3].view(1, 1, -1)
            attended, _ = self.rule_cross_attention(
                query=rule_tokens,
                key=encoded,
                value=encoded,
                key_padding_mask=~context_mask,
                need_weights=False,
            )
            rule_hidden = self.rule_norm(rule_tokens + attended)
            rule_hidden = self.rule_self_attention(rule_hidden)
            return {
                "q_delta": self.q_delta_head(rule_hidden).squeeze(-1),
                "harmful_logit": self.harmful_head(rule_hidden).squeeze(-1),
                "family_logits": self.family_head(rule_hidden),
                "confidence_logit": self.confidence_head(rule_hidden).squeeze(-1),
            }

else:

    class LAUSetRuleTransformerV1:  # type: ignore[no-redef]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            require_torch()


    class LAUEdgeTraceTransformerV3:  # type: ignore[no-redef]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            require_torch()


def parameter_count(model: Any) -> int:
    require_torch()
    return int(sum(parameter.numel() for parameter in model.parameters()))


def build_model(model_name: str, **kwargs: Any) -> Any:
    require_torch()
    if model_name == SET_RULE_TRANSFORMER_NAME:
        filtered = {key: value for key, value in kwargs.items() if key != "trace_dim"}
        return LAUSetRuleTransformerV1(**filtered)
    if model_name == EDGE_TRACE_TRANSFORMER_NAME:
        return LAUEdgeTraceTransformerV3(**kwargs)
    raise ValueError(f"unknown LAU stable-attention model {model_name}")

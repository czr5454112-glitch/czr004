"""Rule-conditioned attention models for Phase4F Repair2 LAU-LTM."""

from __future__ import annotations

from typing import Any

try:
    import torch
    from torch import nn
except ImportError:  # pragma: no cover - exercised only outside project env
    torch = None
    nn = None


MODEL_SCHEMA_VERSION = "laur_rule_attention_v2_checkpoint"
EDGE_TRACE_MODEL_NAME = "LAU-EdgeTraceTransformer-v2"
SET_MODEL_NAME = "LAU-SetTransformer-v2"


def torch_available() -> bool:
    return torch is not None and nn is not None


def require_torch() -> None:
    if not torch_available():
        raise RuntimeError("PyTorch is required for LAU rule-attention training")


if torch_available():

    class LAURuleAttentionModel(nn.Module):
        """Attention model that scores every executable update rule.

        The model encodes global checkpoint features plus traffic-map edge tokens
        and optional trace/count tokens, then lets candidate rule tokens attend to
        that context. Outputs are per-rule score, per-rule harmful logit, and
        per-rule family logits.
        """

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
            nhead: int = 4,
            num_layers: int = 2,
            dropout: float = 0.1,
            architecture: str = EDGE_TRACE_MODEL_NAME,
        ) -> None:
            super().__init__()
            self.global_dim = int(global_dim)
            self.edge_dim = int(edge_dim)
            self.trace_dim = int(trace_dim)
            self.rule_dim = int(rule_dim)
            self.num_rules = int(num_rules)
            self.num_families = int(num_families)
            self.d_model = int(d_model)
            self.architecture = str(architecture)
            self.global_proj = nn.Linear(self.global_dim, self.d_model)
            self.edge_proj = nn.Linear(self.edge_dim, self.d_model)
            self.trace_proj = nn.Linear(self.trace_dim, self.d_model)
            self.rule_proj = nn.Linear(self.rule_dim, self.d_model)
            self.type_embedding = nn.Embedding(4, self.d_model)
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=self.d_model,
                nhead=int(nhead),
                dim_feedforward=self.d_model * 4,
                dropout=float(dropout),
                batch_first=True,
                activation="gelu",
                norm_first=True,
            )
            self.context_encoder = nn.TransformerEncoder(encoder_layer, num_layers=int(num_layers))
            self.rule_cross_attention = nn.MultiheadAttention(
                self.d_model,
                int(nhead),
                dropout=float(dropout),
                batch_first=True,
            )
            self.rule_norm = nn.LayerNorm(self.d_model)
            self.rule_mlp = nn.Sequential(
                nn.Linear(self.d_model, self.d_model),
                nn.GELU(),
                nn.Dropout(float(dropout)),
                nn.Linear(self.d_model, self.d_model),
                nn.GELU(),
            )
            self.score_head = nn.Linear(self.d_model, 1)
            self.harmful_head = nn.Linear(self.d_model, 1)
            self.family_head = nn.Linear(self.d_model, self.num_families)

        def _context_tokens(self, batch: dict[str, Any]) -> tuple[Any, Any]:
            global_x = batch["global_features"]
            edge_x = batch["edge_tokens"]
            trace_x = batch["trace_tokens"]
            edge_mask = batch["edge_mask"].bool()
            trace_mask = batch["trace_mask"].bool()
            batch_size = global_x.shape[0]
            global_token = self.global_proj(global_x).unsqueeze(1)
            global_token = global_token + self.type_embedding.weight[0].view(1, 1, -1)
            edge_tokens = self.edge_proj(edge_x) + self.type_embedding.weight[1].view(1, 1, -1)
            pieces = [global_token, edge_tokens]
            masks = [
                torch.ones((batch_size, 1), dtype=torch.bool, device=global_x.device),
                edge_mask,
            ]
            if self.architecture == EDGE_TRACE_MODEL_NAME:
                trace_tokens = self.trace_proj(trace_x) + self.type_embedding.weight[2].view(1, 1, -1)
                pieces.append(trace_tokens)
                masks.append(trace_mask)
            context = torch.cat(pieces, dim=1)
            context_mask = torch.cat(masks, dim=1)
            return context, context_mask

        def forward(self, batch: dict[str, Any]) -> dict[str, Any]:
            context, context_mask = self._context_tokens(batch)
            encoded = self.context_encoder(context, src_key_padding_mask=~context_mask)
            rule_tokens = self.rule_proj(batch["rule_tokens"]) + self.type_embedding.weight[3].view(1, 1, -1)
            attended, _ = self.rule_cross_attention(
                query=rule_tokens,
                key=encoded,
                value=encoded,
                key_padding_mask=~context_mask,
                need_weights=False,
            )
            rule_hidden = self.rule_norm(rule_tokens + attended)
            rule_hidden = self.rule_norm(rule_hidden + self.rule_mlp(rule_hidden))
            return {
                "rule_score": self.score_head(rule_hidden).squeeze(-1),
                "harmful_logit": self.harmful_head(rule_hidden).squeeze(-1),
                "family_logits": self.family_head(rule_hidden),
            }

else:

    class LAURuleAttentionModel:  # type: ignore[no-redef]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            require_torch()

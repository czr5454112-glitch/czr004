"""Static inference rule for SafeGCST-v2."""

from __future__ import annotations

import torch

from .graph_encoder import GraphGPSLiteEncoder
from .od_encoder import ODSetEncoder
from .theta_critic import ThetaCritic
from .theta_generator import MultiProposalThetaGenerator


class SafeGCSTv2(torch.nn.Module):
    def __init__(self, node_dim: int = 9, edge_dim: int = 9, od_dim: int = 6, hidden_dim: int = 256, proposals: int = 8) -> None:
        super().__init__()
        self.graph_encoder = GraphGPSLiteEncoder(node_dim=node_dim, edge_dim=edge_dim, hidden_dim=hidden_dim)
        self.od_encoder = ODSetEncoder(input_dim=od_dim, hidden_dim=hidden_dim)
        self.generator = MultiProposalThetaGenerator(hidden_dim=hidden_dim, proposals=proposals)
        self.critic = ThetaCritic(hidden_dim=hidden_dim)

    def encode(self, graph_batch, od_tokens, od_mask=None):
        return self.graph_encoder(graph_batch), self.od_encoder(od_tokens, od_mask)


def choose_static_theta(
    theta: torch.Tensor,
    confidence: torch.Tensor,
    regression_prob: torch.Tensor,
    quality_delta: torch.Tensor,
    risk_threshold: float = 0.02,
) -> tuple[torch.Tensor | None, int, str]:
    safe = regression_prob <= risk_threshold
    if not bool(safe.any()):
        return None, -1, "fallback_to_g556_no_calibrated_safe_proposal"
    utility = confidence - quality_delta
    utility = torch.where(safe, utility, torch.full_like(utility, -1e9))
    idx = int(torch.argmax(utility).item())
    return theta[idx], idx, "gcst_static_theta_selected"

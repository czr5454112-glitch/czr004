"""Leakage-free rich actor training helpers for G5.64 experiments."""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from .dual_stream_graph_actor import DualStreamGoalAwareActor
from .goal_aware_actor import make_graph_batch, pad_od_tokens, scalar_features
from .graph_data import GraphData
from .graph_encoder import GraphBatch
from .label_v52_set import LabelV52Context, contexts_from_groups
from .leakage_free_features import PRE_SOLVER_SCALAR_FEATURES, assert_no_forbidden_features, leakage_free_scalar_vector
from .real_label_graph_dataset import build_example, load_label_groups
from .set_valued_actor_losses import set_valued_actor_loss
from .theta_schema import THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS


@dataclass
class RichSetExample:
    evaluation_uid: str
    split: str
    physical_map_sha256: str
    map_family: str
    graph: GraphData
    assignment: dict[str, Any]
    scalar_context: dict[str, Any]
    label_context: LabelV52Context


def graph_with_edge_features(graph: GraphData, edge_features: np.ndarray) -> GraphData:
    return GraphData(
        topology_id=graph.topology_id,
        map_name=graph.map_name,
        width=graph.width,
        height=graph.height,
        cells=graph.cells,
        node_features=graph.node_features,
        edge_index=graph.edge_index,
        edge_features=edge_features,
        hashes=graph.hashes,
        component_count=graph.component_count,
        physical_free_cell_count=graph.physical_free_cell_count,
    )


def load_rich_set_examples(
    rows_path: str | Path,
    context_dir: str | Path,
    *,
    max_contexts: int = 0,
) -> list[RichSetExample]:
    groups = load_label_groups(rows_path, context_dir, max_contexts=max_contexts)
    contexts = {context.evaluation_uid: context for context in contexts_from_groups(groups)}
    out: list[RichSetExample] = []
    for group in groups:
        context = contexts.get(group.evaluation_uid)
        if context is None:
            continue
        built = build_example(group)
        graph_t = graph_with_edge_features(built.graph, built.traffic["edge_features"])
        scalar_context = {
            "agent_count": group.agent_count,
            "agents": group.agent_count,
            "nominal_budget_ms": group.budget_ms,
            "budget_ms": group.budget_ms,
            "base_time_limit_sec": group.rows[0].get("base_time_limit_sec", 1.0),
            "ltm_max_iterations": group.rows[0].get("ltm_max_iterations", 3),
            "agent_density": group.rows[0].get("agent_density", 0.0),
            **built.traffic["summary"],
        }
        out.append(
            RichSetExample(
                evaluation_uid=group.evaluation_uid,
                split=group.split,
                physical_map_sha256=group.physical_map_sha256_expected,
                map_family=group.map_family,
                graph=graph_t,
                assignment=built.assignment,
                scalar_context=scalar_context,
                label_context=context,
            )
        )
    return out


def move_graph_batch(batch: GraphBatch, device: str) -> GraphBatch:
    return GraphBatch(
        batch.node_features.to(device),
        batch.edge_index.to(device),
        batch.edge_features.to(device),
        batch.batch_index.to(device),
        batch.num_graphs,
    )


def loss_item(context: LabelV52Context) -> dict[str, Any]:
    return {
        "label_state": context.label_state,
        "positive_thetas": context.positive_thetas,
        "harmful_thetas": context.harmful_thetas,
        "safe_thetas": context.safe_thetas,
        "positive_weights": context.positive_weights,
        "harmful_weights": context.harmful_weights,
    }


def tensor_batch(examples: Sequence[RichSetExample], device: str):
    import torch

    graph_batch = move_graph_batch(make_graph_batch([ex.graph for ex in examples]), device)
    od_tokens, od_mask = pad_od_tokens([ex.assignment for ex in examples])
    scalars = torch.tensor(np.stack([scalar_features(ex.scalar_context) for ex in examples]), dtype=torch.float32, device=device)
    items = [loss_item(ex.label_context) for ex in examples]
    return graph_batch, od_tokens.to(device), od_mask.to(device), scalars, items


def scalar_control_batch(examples: Sequence[RichSetExample], device: str):
    import torch

    assert_no_forbidden_features(PRE_SOLVER_SCALAR_FEATURES)
    return torch.tensor(np.stack([leakage_free_scalar_vector(ex.scalar_context) for ex in examples]), dtype=torch.float32, device=device)


def batch_set_loss(theta_hat, items: list[dict[str, Any]], device: str):
    import torch

    losses = []
    for idx, item in enumerate(items):
        loss, _terms = set_valued_actor_loss(
            theta_hat[idx],
            label_state=str(item["label_state"]),
            positive_thetas=torch.as_tensor(item["positive_thetas"], dtype=torch.float32, device=device),
            harmful_thetas=torch.as_tensor(item["harmful_thetas"], dtype=torch.float32, device=device),
            safe_thetas=torch.as_tensor(item["safe_thetas"], dtype=torch.float32, device=device),
            positive_weights=torch.as_tensor(item["positive_weights"], dtype=torch.float32, device=device),
            harmful_weights=torch.as_tensor(item["harmful_weights"], dtype=torch.float32, device=device),
        )
        losses.append(loss)
    return torch.stack(losses).mean() if losses else theta_hat.sum() * 0.0


def split_by_ids(examples: Sequence[RichSetExample], train_ids: Sequence[str], valid_ids: Sequence[str]):
    by_uid = {ex.evaluation_uid: ex for ex in examples}
    train = [by_uid[uid] for uid in train_ids if uid in by_uid]
    valid = [by_uid[uid] for uid in valid_ids if uid in by_uid]
    return train, valid


def fallback_split(examples: Sequence[RichSetExample]):
    valid = [ex for idx, ex in enumerate(examples) if idx % 5 == 0]
    train = [ex for idx, ex in enumerate(examples) if idx % 5 != 0]
    return train or list(examples), valid or list(examples[-max(1, len(examples) // 5) :])


def gradient_summary(model: Any) -> dict[str, float]:
    groups = {
        "topology_grad_norm": ["topology_encoder"],
        "c0_grad_norm": ["c0_encoder"],
        "f0_grad_norm": ["f0_encoder"],
        "od_grad_norm": ["od_encoder", "od_token_proj", "cross_attn"],
        "scalar_grad_norm": ["scalar_encoder"],
        "fusion_grad_norm": ["fusion"],
        "theta_head_grad_norm": ["delta_head", "trust_head"],
    }
    out: dict[str, float] = {}
    for group, tokens in groups.items():
        total = 0.0
        for name, param in model.named_parameters():
            if any(token in name for token in tokens) and param.grad is not None:
                total += float(param.grad.detach().norm().cpu())
        out[group] = total
    return out


def make_dual_stream_model(hidden_dim: int, device: str):
    return DualStreamGoalAwareActor(hidden_dim=hidden_dim, use_cross_attention=True).module().to(device)


def make_scalar_control_model(hidden_dim: int, device: str):
    import torch

    assert_no_forbidden_features(PRE_SOLVER_SCALAR_FEATURES)
    lo = torch.as_tensor(THETA_LO, dtype=torch.float32, device=device)
    hi = torch.as_tensor(THETA_HI, dtype=torch.float32, device=device)

    class ScalarControl(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.net = torch.nn.Sequential(
                torch.nn.Linear(len(PRE_SOLVER_SCALAR_FEATURES), hidden_dim),
                torch.nn.SiLU(),
                torch.nn.Linear(hidden_dim, hidden_dim),
                torch.nn.SiLU(),
                torch.nn.Linear(hidden_dim, len(THETA_NUMERIC_COLUMNS)),
            )
            self.register_buffer("lo", lo)
            self.register_buffer("hi", hi)

        def forward(self, scalar_x):
            return self.lo + torch.sigmoid(self.net(scalar_x.float())) * (self.hi - self.lo)

    return ScalarControl().to(device)


def evaluate_rich(model: Any, examples: Sequence[RichSetExample], *, device: str, batch_size: int) -> float:
    model.eval()
    losses = []
    import torch

    with torch.no_grad():
        for start in range(0, len(examples), batch_size):
            batch = list(examples[start : start + batch_size])
            graph_batch, od_tokens, od_mask, scalars, items = tensor_batch(batch, device)
            pred = model(graph_batch, od_tokens, od_mask, scalars)
            losses.append(batch_set_loss(pred, items, device))
    return float(torch.stack(losses).mean().cpu()) if losses else 0.0


def evaluate_scalar(model: Any, examples: Sequence[RichSetExample], *, device: str, batch_size: int) -> float:
    model.eval()
    losses = []
    import torch

    with torch.no_grad():
        for start in range(0, len(examples), batch_size):
            batch = list(examples[start : start + batch_size])
            x = scalar_control_batch(batch, device)
            items = [loss_item(ex.label_context) for ex in batch]
            pred = model(x)
            losses.append(batch_set_loss(pred, items, device))
    return float(torch.stack(losses).mean().cpu()) if losses else 0.0


def train_rich(
    examples: Sequence[RichSetExample],
    valid_examples: Sequence[RichSetExample],
    *,
    seed: int,
    steps: int,
    lr: float,
    hidden_dim: int,
    batch_size: int,
    device: str,
) -> tuple[Any, dict[str, Any]]:
    import torch

    rng = random.Random(seed)
    torch.manual_seed(seed)
    model = make_dual_stream_model(hidden_dim, device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.0)
    initial_valid = evaluate_rich(model, valid_examples, device=device, batch_size=batch_size)
    last_grad: dict[str, float] = {}
    final_train = 0.0
    train_examples = list(examples)
    for _step in range(steps):
        model.train()
        batch = rng.sample(train_examples, min(batch_size, len(train_examples)))
        graph_batch, od_tokens, od_mask, scalars, items = tensor_batch(batch, device)
        pred = model(graph_batch, od_tokens, od_mask, scalars)
        loss = batch_set_loss(pred, items, device)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        last_grad = gradient_summary(model)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
        opt.step()
        final_train = float(loss.detach().cpu())
    final_valid = evaluate_rich(model, valid_examples, device=device, batch_size=batch_size)
    return model, {
        "method": "rich_graph_actor",
        "seed": seed,
        "steps": steps,
        "initial_validation_loss": initial_valid,
        "final_validation_loss": final_valid,
        "final_train_loss": final_train,
        "validation_loss_delta": final_valid - initial_valid,
        "rich_actor_used": True,
        "weight_decay": 0.0,
        **last_grad,
    }


def train_scalar(
    examples: Sequence[RichSetExample],
    valid_examples: Sequence[RichSetExample],
    *,
    seed: int,
    steps: int,
    lr: float,
    hidden_dim: int,
    batch_size: int,
    device: str,
) -> tuple[Any, dict[str, Any]]:
    import torch

    rng = random.Random(seed)
    torch.manual_seed(seed)
    model = make_scalar_control_model(hidden_dim, device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.0)
    initial_valid = evaluate_scalar(model, valid_examples, device=device, batch_size=batch_size)
    final_train = 0.0
    train_examples = list(examples)
    for _step in range(steps):
        model.train()
        batch = rng.sample(train_examples, min(batch_size, len(train_examples)))
        x = scalar_control_batch(batch, device)
        items = [loss_item(ex.label_context) for ex in batch]
        pred = model(x)
        loss = batch_set_loss(pred, items, device)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
        opt.step()
        final_train = float(loss.detach().cpu())
    final_valid = evaluate_scalar(model, valid_examples, device=device, batch_size=batch_size)
    return model, {
        "method": "scalar_pre_solver_control",
        "seed": seed,
        "steps": steps,
        "initial_validation_loss": initial_valid,
        "final_validation_loss": final_valid,
        "final_train_loss": final_train,
        "validation_loss_delta": final_valid - initial_valid,
        "rich_actor_used": False,
        "uses_label_leakage_features": False,
        "weight_decay": 0.0,
    }


def rich_prediction_sensitivity(model: Any, examples: Sequence[RichSetExample], *, device: str) -> dict[str, float]:
    import torch

    batch = list(examples)
    graph_batch, od_tokens, od_mask, scalars, _items = tensor_batch(batch, device)
    model.eval()
    with torch.no_grad():
        base = model(graph_batch, od_tokens, od_mask, scalars)
        shuffled = torch.flip(od_tokens, dims=[1])
        od_pred = model(graph_batch, shuffled, od_mask, scalars)
        no_c0 = GraphBatch(
            graph_batch.node_features,
            graph_batch.edge_index,
            graph_batch.edge_features.clone(),
            graph_batch.batch_index,
            graph_batch.num_graphs,
        )
        if no_c0.edge_features.size(-1) >= 9:
            no_c0.edge_features[:, 6:9] = 0.0
        c0_pred = model(no_c0, od_tokens, od_mask, scalars)
        no_f0 = GraphBatch(
            graph_batch.node_features,
            graph_batch.edge_index,
            graph_batch.edge_features.clone(),
            graph_batch.batch_index,
            graph_batch.num_graphs,
        )
        if no_f0.edge_features.size(-1) >= 9:
            no_f0.edge_features[:, 5] = 0.0
        f0_pred = model(no_f0, od_tokens, od_mask, scalars)
    span = torch.as_tensor(THETA_HI - THETA_LO, dtype=base.dtype, device=device).clamp_min(1.0e-6)
    return {
        "od_shuffle_mean_abs_theta_delta": float(torch.mean(torch.abs((base - od_pred) / span)).cpu()),
        "c0_zero_mean_abs_theta_delta": float(torch.mean(torch.abs((base - c0_pred) / span)).cpu()),
        "f0_zero_mean_abs_theta_delta": float(torch.mean(torch.abs((base - f0_pred) / span)).cpu()),
    }

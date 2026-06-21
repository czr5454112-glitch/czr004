"""G5.65 matched-control rich actor training helpers."""

from __future__ import annotations

import random
from pathlib import Path
from contextlib import nullcontext
from typing import Any, Sequence

import numpy as np

from .dual_stream_graph_actor import DualStreamGoalAwareActor
from .goal_aware_actor import make_graph_batch, pad_od_tokens, scalar_features
from .graph_encoder import GraphBatch
from .leakage_free_features import leakage_free_scalar_vector
from .matched_theta_heads import (
    GlobalResidualTheta,
    ScalarResidualActor,
    matched_output_metadata,
    zero_delta_heads,
)
from .opportunity_labels import OpportunityMetrics, normalized_oracle_regret, opportunity_metrics
from .repaired_set_risk import DEFAULT_REPAIRED_RISK, RepairedRiskConfig, batch_context_loss_torch, context_loss_np, loss_item_from_context
from .rich_actor_training_g564 import RichSetExample, load_rich_set_examples
from .shared_edge_attention_actor import make_shared_edge_attention_actor
from .theta_schema import BASELINE_G556, THETA_HI, THETA_LO, THETA_NUMERIC_COLUMNS


MODEL_KINDS = ("B0", "B1", "B2", "E0", "E1", "E2")


def load_examples(rows_path: str | Path, context_dir: str | Path, *, max_contexts: int = 0) -> list[RichSetExample]:
    return load_rich_set_examples(rows_path, context_dir, max_contexts=max_contexts)


def move_graph_batch(batch: GraphBatch, device: str) -> GraphBatch:
    return GraphBatch(
        batch.node_features.to(device),
        batch.edge_index.to(device),
        batch.edge_features.to(device),
        batch.batch_index.to(device),
        batch.num_graphs,
    )


def tensor_batch(examples: Sequence[RichSetExample], device: str):
    import torch

    graph_batch = move_graph_batch(make_graph_batch([ex.graph for ex in examples]), device)
    od_tokens, od_mask = pad_od_tokens([ex.assignment for ex in examples])
    rich_scalars = torch.tensor(np.stack([scalar_features(ex.scalar_context) for ex in examples]), dtype=torch.float32, device=device)
    scalar_x = torch.tensor(np.stack([leakage_free_scalar_vector(ex.scalar_context) for ex in examples]), dtype=torch.float32, device=device)
    items = [loss_item_from_context(ex.label_context) for ex in examples]
    return graph_batch, od_tokens.to(device), od_mask.to(device), rich_scalars, scalar_x, items


def scalar_tensor(examples: Sequence[RichSetExample], device: str):
    import torch

    return torch.tensor(np.stack([leakage_free_scalar_vector(ex.scalar_context) for ex in examples]), dtype=torch.float32, device=device)


def loss_items(examples: Sequence[RichSetExample]):
    return [loss_item_from_context(ex.label_context) for ex in examples]


def make_model(model_kind: str, *, hidden_dim: int, device: str):
    kind = str(model_kind).upper()
    if kind == "B1":
        return GlobalResidualTheta().module().to(device)
    if kind == "B2":
        return ScalarResidualActor(hidden_dim=hidden_dim).module().to(device)
    if kind == "E0":
        model = DualStreamGoalAwareActor(hidden_dim=hidden_dim, use_cross_attention=False, residual_scale=0.30).module().to(device)
        zero_delta_heads(model)
        return model
    if kind == "E1":
        return make_shared_edge_attention_actor(hidden_dim=hidden_dim, local_layers=2, residual_scale=0.30).to(device)
    if kind == "E2":
        model = DualStreamGoalAwareActor(hidden_dim=hidden_dim, use_cross_attention=True, residual_scale=0.30).module().to(device)
        zero_delta_heads(model)
        return model
    raise KeyError(f"unknown G5.65 model kind: {model_kind}")


def predict_theta(model_kind: str, model: Any, examples: Sequence[RichSetExample], device: str):
    import torch

    kind = str(model_kind).upper()
    if kind == "B0":
        return torch.as_tensor(BASELINE_G556, dtype=torch.float32, device=device).view(1, -1).expand(len(examples), -1)
    if kind == "B1":
        return model(len(examples))
    if kind == "B2":
        return model(scalar_tensor(examples, device))
    graph_batch, od_tokens, od_mask, rich_scalars, scalar_x, _items = tensor_batch(examples, device)
    return model(graph_batch, od_tokens, od_mask, rich_scalars)


def batch_loss_for_examples(
    model_kind: str,
    model: Any,
    examples: Sequence[RichSetExample],
    *,
    cfg: RepairedRiskConfig,
    device: str,
):
    import torch

    items = loss_items(examples)
    pred = predict_theta(model_kind, model, examples, device)
    return batch_context_loss_torch(pred, items, cfg)


def evaluate_model(
    model_kind: str,
    model: Any,
    examples: Sequence[RichSetExample],
    *,
    cfg: RepairedRiskConfig = DEFAULT_REPAIRED_RISK,
    device: str,
    batch_size: int = 8,
) -> tuple[float, list[dict[str, Any]]]:
    import torch

    rows: list[dict[str, Any]] = []
    losses = []
    with torch.no_grad():
        for start in range(0, len(examples), batch_size):
            batch = list(examples[start : start + batch_size])
            pred = predict_theta(model_kind, model, batch, device).detach().cpu().numpy()
            for ex, theta in zip(batch, pred):
                risk, terms = context_loss_np(theta, ex.label_context, cfg)
                metrics = opportunity_metrics(ex.label_context, cfg)
                regret = normalized_oracle_regret(risk, metrics)
                distance_to_g556 = float(np.mean(np.abs((theta - BASELINE_G556) / np.maximum(THETA_HI - THETA_LO, 1.0e-6))))
                rows.append(
                    {
                        "evaluation_uid": ex.evaluation_uid,
                        "model_kind": model_kind,
                        "split": ex.split,
                        "map_family": ex.map_family,
                        "opportunity_category": metrics.opportunity_category,
                        "actor_risk": risk,
                        "g556_risk": metrics.g556_risk,
                        "oracle_risk": metrics.oracle_risk,
                        "oracle_gap": metrics.oracle_gap,
                        "normalized_oracle_regret": regret,
                        "distance_to_g556": distance_to_g556,
                        "positive_loss": terms.get("positive_loss", 0.0),
                        "harmful_loss": terms.get("harmful_loss", 0.0),
                        "trust_loss": terms.get("trust_loss", 0.0),
                        "loss_config_sha256": cfg.sha256,
                    }
                )
                losses.append(float(risk))
    return (float(np.mean(losses)) if losses else 0.0), rows


def gradient_summary(model: Any) -> dict[str, float]:
    groups = {
        "topology_grad_norm": ["topology_encoder", "graph_encoder"],
        "c0_grad_norm": ["c0_encoder"],
        "f0_grad_norm": ["f0_encoder"],
        "od_grad_norm": ["od_encoder", "od_token_proj", "cross_attn"],
        "scalar_grad_norm": ["scalar_encoder", "body"],
        "fusion_grad_norm": ["fusion"],
        "theta_head_grad_norm": ["delta_head", "theta_head"],
        "trust_head_grad_norm": ["trust_head", "trust_logit"],
    }
    out: dict[str, float] = {}
    for group, tokens in groups.items():
        total = 0.0
        for name, param in model.named_parameters():
            if any(token in name for token in tokens) and param.grad is not None:
                total += float(param.grad.detach().norm().cpu())
        out[group] = total
    return out


def train_model(
    model_kind: str,
    train_examples: Sequence[RichSetExample],
    valid_examples: Sequence[RichSetExample],
    *,
    cfg: RepairedRiskConfig = DEFAULT_REPAIRED_RISK,
    seed: int,
    epochs: int,
    lr: float,
    hidden_dim: int,
    batch_size: int,
    device: str,
    weight_decay: float = 0.0,
    min_epochs: int = 0,
    early_stop_patience: int = 0,
    min_delta: float = 1.0e-7,
    amp_bf16: bool = False,
) -> tuple[Any, dict[str, Any]]:
    import torch

    kind = str(model_kind).upper()
    if kind == "B0":
        initial_valid, _ = evaluate_model(kind, None, valid_examples, cfg=cfg, device=device, batch_size=batch_size)
        return None, {
            "model_kind": kind,
            "seed": seed,
            "epochs": 0,
            "epochs_run": 0,
            "best_epoch": 0,
            "early_stop_patience": int(early_stop_patience),
            "min_epochs": int(min_epochs),
            "stopped_early": False,
            "amp_bf16": bool(amp_bf16),
            "initial_validation_risk": initial_valid,
            "best_validation_risk": initial_valid,
            "final_validation_risk": initial_valid,
            "final_train_risk": initial_valid,
            "loss_config_sha256": cfg.sha256,
            **matched_output_metadata("B0_always_g556"),
        }
    rng = random.Random(seed)
    torch.manual_seed(seed)
    model = make_model(kind, hidden_dim=hidden_dim, device=device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    initial_valid, _ = evaluate_model(kind, model, valid_examples, cfg=cfg, device=device, batch_size=batch_size)
    best_valid = initial_valid
    best_epoch = 0
    best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    final_train = 0.0
    grad = {}
    train = list(train_examples)
    stale_epochs = 0
    autocast_enabled = bool(amp_bf16 and str(device).startswith("cuda"))
    for epoch in range(1, int(epochs) + 1):
        rng.shuffle(train)
        epoch_losses = []
        for start in range(0, len(train), batch_size):
            batch = train[start : start + batch_size]
            ctx = torch.autocast(device_type="cuda", dtype=torch.bfloat16) if autocast_enabled else nullcontext()
            with ctx:
                loss, _terms = batch_loss_for_examples(kind, model, batch, cfg=cfg, device=device)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            if not grad:
                grad = gradient_summary(model)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 2.0)
            opt.step()
            epoch_losses.append(float(loss.detach().cpu()))
        final_train = float(np.mean(epoch_losses)) if epoch_losses else 0.0
        valid_risk, _ = evaluate_model(kind, model, valid_examples, cfg=cfg, device=device, batch_size=batch_size)
        if valid_risk < best_valid - float(min_delta):
            best_valid = valid_risk
            best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            stale_epochs = 0
        else:
            stale_epochs += 1
        if early_stop_patience and epoch >= int(min_epochs) and stale_epochs >= int(early_stop_patience):
            break
    model.load_state_dict(best_state)
    final_valid, _ = evaluate_model(kind, model, valid_examples, cfg=cfg, device=device, batch_size=batch_size)
    return model, {
        "model_kind": kind,
        "seed": seed,
        "epochs": int(epochs),
        "epochs_run": int(epoch if "epoch" in locals() else 0),
        "best_epoch": int(best_epoch),
        "early_stop_patience": int(early_stop_patience),
        "min_epochs": int(min_epochs),
        "stopped_early": bool(early_stop_patience and (epoch if "epoch" in locals() else 0) < int(epochs)),
        "amp_bf16": bool(amp_bf16),
        "initial_validation_risk": float(initial_valid),
        "best_validation_risk": float(best_valid),
        "final_validation_risk": float(final_valid),
        "final_train_risk": float(final_train),
        "loss_config_sha256": cfg.sha256,
        "weight_decay": float(weight_decay),
        **matched_output_metadata(kind),
        **grad,
    }


def checkpoint_payload(model_kind: str, model: Any, metrics: dict[str, Any], cfg: RepairedRiskConfig, hidden_dim: int) -> dict[str, Any]:
    return {
        "artifact_type": "phase5p5_repair5g565_matched_repaired_risk_actor",
        "model_kind": model_kind,
        "hidden_dim": int(hidden_dim),
        "loss_config": cfg.to_dict(),
        "loss_config_sha256": cfg.sha256,
        "metrics": metrics,
        "theta_columns": list(THETA_NUMERIC_COLUMNS),
        "actor_state_dict": None if model is None else model.state_dict(),
        **matched_output_metadata(model_kind),
    }

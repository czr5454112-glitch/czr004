"""Actor-only inference for exported Repair5G.5.60 direct generators."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .direct_actor import ACTOR_FEATURE_SCHEMA, ActorNormalizer, DirectGCSTActor, actor_features
from .label_v4 import THETA_NUMERIC_COLUMNS


def load_actor_bundle(path: str | Path, device: str = "cpu") -> dict[str, Any]:
    import torch

    bundle = torch.load(Path(path), map_location=device, weights_only=False)
    forbidden = {"auxiliary_state_dict", "memory_table", "selector_table"}
    present = sorted(forbidden.intersection(bundle.keys()))
    if present:
        raise ValueError(f"Actor bundle contains forbidden training-only keys: {present}")
    model = DirectGCSTActor(
        input_dim=len(bundle["feature_schema"]),
        hidden_dim=int(bundle.get("hidden_dim", 128)),
        residual_scale=float(bundle.get("residual_scale", 0.35)),
    ).module()
    model.load_state_dict(bundle["actor_state_dict"])
    model.to(device)
    model.eval()
    normalizer = ActorNormalizer(mean=np.asarray(bundle["feature_mean"], dtype=np.float32), std=np.asarray(bundle["feature_std"], dtype=np.float32))
    return {"model": model, "normalizer": normalizer, "device": device, "metadata": bundle}


def predict_theta(bundle: dict[str, Any], instance_row: dict[str, Any]) -> dict[str, float]:
    import torch

    x = actor_features(instance_row).reshape(1, -1)
    x = bundle["normalizer"].transform(x)
    xt = torch.tensor(x, dtype=torch.float32, device=bundle["device"])
    model = bundle["model"]
    with torch.no_grad():
        theta = model(xt).detach().cpu().numpy()[0]
    return {col: float(value) for col, value in zip(THETA_NUMERIC_COLUMNS, theta)}


def single_forward_predict(path: str | Path, instance_row: dict[str, Any], device: str = "cpu") -> dict[str, float]:
    return predict_theta(load_actor_bundle(path, device=device), instance_row)

"""LAU-LTM checkpoint-level update-rule model and JSON export helpers."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

try:
    import torch
    from torch import nn
except ImportError:  # pragma: no cover - exercised only outside the project env
    torch = None
    nn = None


MODEL_SCHEMA_VERSION = "laur_mlp_v1_weights"
FEATURE_STATS_SCHEMA_VERSION = "laur_mlp_v1_feature_stats"
RULES_SCHEMA_VERSION = "laur_mlp_v1_rules"
MODEL_NAME = "LAU-MLP-v1"


DEFAULT_RULE_PARAMS: dict[str, dict[str, float | bool]] = {
    "additive_ltm": {
        "alpha_commit": 1.0,
        "alpha_block": 1.0,
        "alpha_wait": 1.0,
        "rho_decay": 1.0,
        "saturation_scale": 1.0,
        "contraflow_penalty": 0.0,
        "force_additive": True,
    },
    "commit_heavy": {
        "alpha_commit": 1.5,
        "alpha_block": 1.0,
        "alpha_wait": 1.0,
        "rho_decay": 1.0,
        "saturation_scale": 1.0,
        "contraflow_penalty": 0.0,
        "force_additive": False,
    },
    "block_heavy": {
        "alpha_commit": 1.0,
        "alpha_block": 1.5,
        "alpha_wait": 1.0,
        "rho_decay": 1.0,
        "saturation_scale": 1.0,
        "contraflow_penalty": 0.0,
        "force_additive": False,
    },
    "block_light": {
        "alpha_commit": 1.0,
        "alpha_block": 0.5,
        "alpha_wait": 1.0,
        "rho_decay": 1.0,
        "saturation_scale": 1.0,
        "contraflow_penalty": 0.0,
        "force_additive": False,
    },
    "wait_light": {
        "alpha_commit": 1.0,
        "alpha_block": 1.0,
        "alpha_wait": 0.5,
        "rho_decay": 1.0,
        "saturation_scale": 1.0,
        "contraflow_penalty": 0.0,
        "force_additive": False,
    },
    "wait_heavy": {
        "alpha_commit": 1.0,
        "alpha_block": 1.0,
        "alpha_wait": 1.5,
        "rho_decay": 1.0,
        "saturation_scale": 1.0,
        "contraflow_penalty": 0.0,
        "force_additive": False,
    },
    "decay_095": {
        "alpha_commit": 1.0,
        "alpha_block": 1.0,
        "alpha_wait": 1.0,
        "rho_decay": 0.95,
        "saturation_scale": 1.0,
        "contraflow_penalty": 0.0,
        "force_additive": False,
    },
    "decay_090": {
        "alpha_commit": 1.0,
        "alpha_block": 1.0,
        "alpha_wait": 1.0,
        "rho_decay": 0.90,
        "saturation_scale": 1.0,
        "contraflow_penalty": 0.0,
        "force_additive": False,
    },
    "neutral_additive": {
        "alpha_commit": 1.0,
        "alpha_block": 1.0,
        "alpha_wait": 1.0,
        "rho_decay": 1.0,
        "saturation_scale": 1.0,
        "contraflow_penalty": 0.0,
        "force_additive": True,
    },
}


def torch_available() -> bool:
    return torch is not None and nn is not None


def require_torch() -> None:
    if not torch_available():
        raise RuntimeError(
            "PyTorch is required for LAU-LTM training. Use the czr004 conda "
            "environment from environment.yml."
        )


if torch_available():

    class LaurMlpV1(nn.Module):
        """Small checkpoint-level MLP for Phase4F update-rule prediction."""

        def __init__(self, input_dim: int, num_rules: int, hidden_dim: int = 64):
            super().__init__()
            self.input_dim = int(input_dim)
            self.num_rules = int(num_rules)
            self.hidden_dim = int(hidden_dim)
            self.encoder = nn.Sequential(
                nn.Linear(self.input_dim, self.hidden_dim),
                nn.ReLU(),
            )
            self.rule_head = nn.Linear(self.hidden_dim, self.num_rules)
            self.safety_head = nn.Linear(self.hidden_dim, 1)
            self.delta_head = nn.Linear(self.hidden_dim, 1)

        def forward(self, x: Any) -> dict[str, Any]:
            h = self.encoder(x)
            return {
                "rule_logits": self.rule_head(h),
                "safety_logit": self.safety_head(h).squeeze(-1),
                "delta_pred": self.delta_head(h).squeeze(-1),
            }

else:

    class LaurMlpV1:  # type: ignore[no-redef]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            require_torch()


def _tensor_to_nested_list(value: Any) -> list[Any]:
    require_torch()
    return value.detach().cpu().tolist()


def _write_json(path: str | Path, payload: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def export_laur_mlp_v1(
    model: LaurMlpV1,
    *,
    input_features: list[str],
    feature_mean: list[float],
    feature_std: list[float],
    rules: list[str],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a C++-friendly JSON description of a trained LAU-MLP-v1."""

    require_torch()
    model_cpu = model.cpu()
    layer0 = model_cpu.encoder[0]
    payload = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "model_name": MODEL_NAME,
        "input_dim": len(input_features),
        "hidden_dim": int(model_cpu.hidden_dim),
        "num_rules": len(rules),
        "input_features": list(input_features),
        "normalization": {
            "mean": [float(value) for value in feature_mean],
            "std": [float(value) for value in feature_std],
        },
        "layers": [
            {
                "type": "linear",
                "weight": _tensor_to_nested_list(layer0.weight),
                "bias": _tensor_to_nested_list(layer0.bias),
            },
            {"type": "relu"},
            {
                "type": "linear_rule_head",
                "weight": _tensor_to_nested_list(model_cpu.rule_head.weight),
                "bias": _tensor_to_nested_list(model_cpu.rule_head.bias),
            },
            {
                "type": "linear_safety_head",
                "weight": _tensor_to_nested_list(model_cpu.safety_head.weight),
                "bias": _tensor_to_nested_list(model_cpu.safety_head.bias),
            },
            {
                "type": "linear_delta_head",
                "weight": _tensor_to_nested_list(model_cpu.delta_head.weight),
                "bias": _tensor_to_nested_list(model_cpu.delta_head.bias),
            },
        ],
        "rules": {str(index): rule_id for index, rule_id in enumerate(rules)},
        "rule_params": {
            rule_id: DEFAULT_RULE_PARAMS.get(rule_id, DEFAULT_RULE_PARAMS["additive_ltm"])
            for rule_id in rules
        },
        "metadata": metadata or {},
    }
    return payload


def write_laur_mlp_exports(
    model: LaurMlpV1,
    *,
    output_dir: str | Path,
    input_features: list[str],
    feature_mean: list[float],
    feature_std: list[float],
    rules: list[str],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Path]:
    """Write weights, feature stats, and rule metadata JSON files."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    weights = export_laur_mlp_v1(
        model,
        input_features=input_features,
        feature_mean=feature_mean,
        feature_std=feature_std,
        rules=rules,
        metadata=metadata,
    )
    feature_stats = {
        "schema_version": FEATURE_STATS_SCHEMA_VERSION,
        "model_name": MODEL_NAME,
        "input_features": list(input_features),
        "normalization": weights["normalization"],
        "metadata": metadata or {},
    }
    rules_payload = {
        "schema_version": RULES_SCHEMA_VERSION,
        "model_name": MODEL_NAME,
        "rules": weights["rules"],
        "rule_params": weights["rule_params"],
        "metadata": metadata or {},
    }

    paths = {
        "weights": output / "laur_mlp_v1_weights.json",
        "feature_stats": output / "laur_mlp_v1_feature_stats.json",
        "rules": output / "laur_mlp_v1_rules.json",
    }
    _write_json(paths["weights"], weights)
    _write_json(paths["feature_stats"], feature_stats)
    _write_json(paths["rules"], rules_payload)
    return paths


def load_export(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != MODEL_SCHEMA_VERSION:
        raise ValueError(f"{path}: expected schema_version {MODEL_SCHEMA_VERSION}")
    return payload


def _linear(values: list[float], layer: dict[str, Any]) -> list[float]:
    weights = layer["weight"]
    bias = layer["bias"]
    return [
        float(sum(float(weight) * value for weight, value in zip(row, values)) + float(bias_value))
        for row, bias_value in zip(weights, bias)
    ]


def _softmax(logits: list[float]) -> list[float]:
    if not logits:
        return []
    pivot = max(logits)
    values = [math.exp(value - pivot) for value in logits]
    total = sum(values)
    return [value / total for value in values] if total else [1.0 / len(logits)] * len(logits)


def _sigmoid(value: float) -> float:
    if value >= 0.0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def forward_exported_model(export: dict[str, Any], feature_vector: list[float]) -> dict[str, Any]:
    """Run the exported JSON model without PyTorch."""

    norm = export["normalization"]
    means = [float(value) for value in norm["mean"]]
    stds = [float(value) if float(value) > 1e-12 else 1.0 for value in norm["std"]]
    if len(feature_vector) != len(means):
        raise ValueError(
            f"feature_vector has length {len(feature_vector)}, expected {len(means)}"
        )
    values = [(float(value) - mean) / std for value, mean, std in zip(feature_vector, means, stds)]
    layer0 = next(layer for layer in export["layers"] if layer["type"] == "linear")
    hidden = [max(0.0, value) for value in _linear(values, layer0)]
    rule_head = next(layer for layer in export["layers"] if layer["type"] == "linear_rule_head")
    safety_head = next(layer for layer in export["layers"] if layer["type"] == "linear_safety_head")
    delta_head = next(layer for layer in export["layers"] if layer["type"] == "linear_delta_head")
    rule_logits = _linear(hidden, rule_head)
    rule_probabilities = _softmax(rule_logits)
    safety_logit = _linear(hidden, safety_head)[0]
    delta_pred = _linear(hidden, delta_head)[0]
    return {
        "rule_logits": rule_logits,
        "rule_probabilities": rule_probabilities,
        "safety_logit": safety_logit,
        "harmful_update_probability": _sigmoid(safety_logit),
        "delta_pred": delta_pred,
    }

"""Convert a Phase4F LAU-MLP JSON export to the Phase5 C++ CSV runtime format."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _layer(payload: dict[str, Any], layer_type: str) -> dict[str, Any]:
    for layer in payload.get("layers", []):
        if layer.get("type") == layer_type:
            return layer
    raise ValueError(f"missing layer {layer_type}")


def _write_rows(path: Path, rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerows(rows)


def _write_vector(path: Path, values: list[Any]) -> None:
    _write_rows(path, [[float(value) for value in values]])


def _write_matrix(path: Path, values: list[list[Any]]) -> None:
    _write_rows(path, [[float(value) for value in row] for row in values])


def export_runtime_dir(weights_path: Path, output_dir: Path) -> dict[str, Path]:
    payload = json.loads(weights_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "laur_mlp_v1_weights":
        raise ValueError(f"{weights_path}: expected laur_mlp_v1_weights schema")

    output_dir.mkdir(parents=True, exist_ok=True)

    feature_names = [str(name) for name in payload["input_features"]]
    (output_dir / "features.txt").write_text(
        "\n".join(feature_names) + "\n", encoding="utf-8"
    )

    normalization = payload["normalization"]
    _write_vector(output_dir / "mean.csv", normalization["mean"])
    _write_vector(output_dir / "std.csv", normalization["std"])

    layer0 = _layer(payload, "linear")
    rule_head = _layer(payload, "linear_rule_head")
    safety_head = _layer(payload, "linear_safety_head")
    delta_head = _layer(payload, "linear_delta_head")
    _write_matrix(output_dir / "layer0_weight.csv", layer0["weight"])
    _write_vector(output_dir / "layer0_bias.csv", layer0["bias"])
    _write_matrix(output_dir / "rule_head_weight.csv", rule_head["weight"])
    _write_vector(output_dir / "rule_head_bias.csv", rule_head["bias"])
    _write_matrix(output_dir / "safety_head_weight.csv", safety_head["weight"])
    _write_vector(output_dir / "safety_head_bias.csv", safety_head["bias"])
    _write_matrix(output_dir / "delta_head_weight.csv", delta_head["weight"])
    _write_vector(output_dir / "delta_head_bias.csv", delta_head["bias"])

    rules = payload["rules"]
    rule_params = payload.get("rule_params", {})
    ordered_rules = [rules[str(index)] for index in range(len(rules))]
    with (output_dir / "rules.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "rule_id",
                "alpha_commit",
                "alpha_block",
                "alpha_wait",
                "rho_decay",
                "saturation_scale",
                "contraflow_penalty",
                "force_additive",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for rule_id in ordered_rules:
            params = rule_params.get(rule_id, rule_params.get("additive_ltm", {}))
            writer.writerow(
                {
                    "rule_id": rule_id,
                    "alpha_commit": float(params.get("alpha_commit", 1.0)),
                    "alpha_block": float(params.get("alpha_block", 1.0)),
                    "alpha_wait": float(params.get("alpha_wait", 1.0)),
                    "rho_decay": float(params.get("rho_decay", 1.0)),
                    "saturation_scale": float(params.get("saturation_scale", 1.0)),
                    "contraflow_penalty": float(params.get("contraflow_penalty", 0.0)),
                    "force_additive": "true" if params.get("force_additive", False) else "false",
                }
            )

    return {
        "features": output_dir / "features.txt",
        "rules": output_dir / "rules.csv",
        "layer0_weight": output_dir / "layer0_weight.csv",
        "rule_head_weight": output_dir / "rule_head_weight.csv",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights-json", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)

    paths = export_runtime_dir(args.weights_json, args.output_dir)
    print(f"phase5_laur_runtime_export output={args.output_dir}")
    for name, path in paths.items():
        print(f"{name}={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

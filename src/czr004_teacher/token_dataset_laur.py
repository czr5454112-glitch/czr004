"""Build Phase4F Repair2 token/rule-aware LAU-LTM update datasets."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.token_features_laur import (  # noqa: E402
    EDGE_FEATURE_NAMES,
    EXECUTABLE_RULE_IDS,
    ORIGINAL_EXTRA_RULE_IDS,
    RULE_FAMILY_IDS,
    RULE_FEATURE_NAMES,
    TOKEN_DATASET_SCHEMA_VERSION,
    TOKEN_FEATURE_SET,
    TRACE_FEATURE_NAMES,
    build_edge_tokens,
    build_rule_tokens,
    build_trace_count_tokens,
    executable_rule_id,
    finite_float,
    mixed_soft_rule_target,
    rule_family,
    rule_family_index,
    topology_for_token_features,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path | None, root: Path) -> Path | None:
    if path is None:
        return None
    value = Path(path)
    return value if value.is_absolute() else root / value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: JSONL row must be an object")
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def load_config(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read Phase4 LAUR configs") from exc
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def group_by_checkpoint(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["checkpoint_id"])].append(row)
    return grouped


def row_by_checkpoint(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["checkpoint_id"]): row for row in rows}


def probe_delta_vector(probe_rows: list[dict[str, Any]], rule_ids: list[str]) -> list[float]:
    lookup = {str(row["rule_id"]): finite_float(row.get("delta_ratio_vs_additive")) for row in probe_rows}
    return [lookup.get(rule_id, 0.0) for rule_id in rule_ids]


def probe_harmful_vector(probe_rows: list[dict[str, Any]], rule_ids: list[str]) -> list[int]:
    lookup = {str(row["rule_id"]): 1 if row.get("harmful") else 0 for row in probe_rows}
    return [lookup.get(rule_id, 0) for rule_id in rule_ids]


def target_from_v1(
    dataset_row: dict[str, Any],
    *,
    delta_vector: list[float],
    harmful_vector: list[int],
    soft_temperature: float,
    soft_hard_mix: float,
) -> tuple[dict[str, Any], list[float]]:
    source_target = dataset_row["target"]
    original_rule = str(source_target["rule_class"])
    best_rule_original = str(source_target.get("best_rule_id", original_rule))
    executable_rule = executable_rule_id(original_rule)
    executable_index = EXECUTABLE_RULE_IDS.index(executable_rule)
    original_rule_vocab = list(source_target.get("rule_vocab", []))
    for rule_id in ORIGINAL_EXTRA_RULE_IDS:
        if rule_id not in original_rule_vocab:
            original_rule_vocab.append(rule_id)
    soft_target = mixed_soft_rule_target(
        delta_vector,
        hard_index=executable_index,
        temperature=soft_temperature,
        hard_mix=soft_hard_mix,
    )
    target = {
        "rule_class_original": original_rule,
        "rule_class_original_index": int(source_target.get("rule_class_index", 0)),
        "rule_vocab_original": original_rule_vocab,
        "best_rule_original": best_rule_original,
        "best_rule_executable": executable_rule,
        "best_rule_executable_index": executable_index,
        "rule_vocab_executable": list(EXECUTABLE_RULE_IDS),
        "rule_family": rule_family(executable_rule),
        "rule_family_index": rule_family_index(executable_rule),
        "rule_family_vocab": list(RULE_FAMILY_IDS),
        "is_neutral_label": bool(source_target.get("neutral", original_rule == "neutral_additive")),
        "harmful_update": bool(source_target.get("harmful_update", False)),
        "harmful_rule_ids_original": [str(rule_id) for rule_id in source_target.get("harmful_rule_ids", [])],
        "target_rule_harmful": bool(harmful_vector[executable_index]),
        "any_harmful_candidate": bool(any(harmful_vector)),
        "delta_ratio_best_original": finite_float(source_target.get("delta_ratio_best")),
        "delta_ratio_target_executable": float(delta_vector[executable_index]),
        "label_confidence": finite_float(source_target.get("label_confidence")),
        "additive_sum_of_loss_ratio": source_target.get("additive_sum_of_loss_ratio"),
        "best_sum_of_loss_ratio": source_target.get("best_sum_of_loss_ratio"),
    }
    return target, soft_target


def build_token_update_dataset_rows(
    checkpoint_rows: list[dict[str, Any]],
    dataset_v1_rows: list[dict[str, Any]],
    probe_rows: list[dict[str, Any]],
    *,
    repo_root_path: str | Path | None = None,
    max_edge_tokens: int = 64,
    max_trace_tokens: int = 64,
    soft_temperature: float = 0.01,
    soft_hard_mix: float = 0.5,
) -> list[dict[str, Any]]:
    checkpoints = row_by_checkpoint(checkpoint_rows)
    probes = group_by_checkpoint(probe_rows)
    topology_cache: dict[Path, Any] = {}
    output: list[dict[str, Any]] = []

    for dataset_row in dataset_v1_rows:
        checkpoint_id = str(dataset_row["checkpoint_id"])
        checkpoint = checkpoints.get(checkpoint_id)
        if checkpoint is None:
            continue
        probe_group = probes.get(checkpoint_id, [])
        topology = topology_for_token_features(checkpoint, topology_cache, repo_root=repo_root_path)
        delta_vector = probe_delta_vector(probe_group, EXECUTABLE_RULE_IDS)
        harmful_vector = probe_harmful_vector(probe_group, EXECUTABLE_RULE_IDS)
        target, soft_target = target_from_v1(
            dataset_row,
            delta_vector=delta_vector,
            harmful_vector=harmful_vector,
            soft_temperature=soft_temperature,
            soft_hard_mix=soft_hard_mix,
        )
        output.append(
            {
                "schema_version": TOKEN_DATASET_SCHEMA_VERSION,
                "run_id": dataset_row["run_id"],
                "checkpoint_id": checkpoint_id,
                "split": dataset_row["split"],
                "map_name": dataset_row["map_name"],
                "agents": int(dataset_row["agents"]),
                "seed": int(dataset_row["seed"]),
                "iteration": int(dataset_row["iteration"]),
                "feature_set": TOKEN_FEATURE_SET,
                "global_feature_names": list(dataset_row["feature_names"]),
                "global_features": [float(value) for value in dataset_row["feature_vector"]],
                "edge_feature_names": list(EDGE_FEATURE_NAMES),
                "edge_tokens": build_edge_tokens(
                    checkpoint,
                    max_edge_tokens=max_edge_tokens,
                    topology=topology,
                ),
                "trace_feature_names": list(TRACE_FEATURE_NAMES),
                "trace_tokens": build_trace_count_tokens(
                    checkpoint,
                    trace_rows=None,
                    max_trace_tokens=max_trace_tokens,
                ),
                "rule_feature_names": list(RULE_FEATURE_NAMES),
                "rule_vocab": list(EXECUTABLE_RULE_IDS),
                "rule_tokens": build_rule_tokens(EXECUTABLE_RULE_IDS),
                "rule_delta_vector": delta_vector,
                "rule_harmful_vector": harmful_vector,
                "soft_rule_target": soft_target,
                "target": target,
                "source": {
                    "dataset_v1_schema_version": dataset_row.get("schema_version"),
                    "checkpoint_schema_version": checkpoint.get("schema_version"),
                    "probe_schema_version": probe_group[0].get("schema_version") if probe_group else None,
                    "probe_rule_count": len(probe_group),
                    "checkpoint_trace_event_count": int(checkpoint.get("trace_event_count", 0) or 0),
                    "uses_raw_trace_tokens": False,
                    "raw_trace_token_reason": "repair2_initial_local_run_uses_checkpoint_count_tokens",
                },
                "audit": {
                    "max_edge_tokens": int(max_edge_tokens),
                    "max_trace_tokens": int(max_trace_tokens),
                    "edge_token_count": len(build_edge_tokens(checkpoint, max_edge_tokens=max_edge_tokens, topology=topology)),
                    "trace_token_count": len(build_trace_count_tokens(checkpoint, trace_rows=None, max_trace_tokens=max_trace_tokens)),
                    "soft_temperature": float(soft_temperature),
                    "soft_hard_mix": float(soft_hard_mix),
                },
            }
        )
    return output


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _validate_vector(name: str, values: Any, expected_len: int, errors: list[str]) -> None:
    if not isinstance(values, list):
        errors.append(f"{name} must be a list")
        return
    if len(values) != expected_len:
        errors.append(f"{name} length must be {expected_len}")
    for index, value in enumerate(values):
        if not _is_finite_number(value):
            errors.append(f"{name}[{index}] must be finite numeric")


def _validate_token_matrix(name: str, values: Any, expected_len: int, errors: list[str]) -> None:
    if not isinstance(values, list):
        errors.append(f"{name} must be a list")
        return
    for row_index, token in enumerate(values):
        if not isinstance(token, list):
            errors.append(f"{name}[{row_index}] must be a list")
            continue
        if len(token) != expected_len:
            errors.append(f"{name}[{row_index}] length must be {expected_len}")
        for col_index, value in enumerate(token):
            if not _is_finite_number(value):
                errors.append(f"{name}[{row_index}][{col_index}] must be finite numeric")


def validate_token_update_dataset_row(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version": str,
        "run_id": str,
        "checkpoint_id": str,
        "split": str,
        "map_name": str,
        "agents": int,
        "seed": int,
        "iteration": int,
        "feature_set": str,
        "global_feature_names": list,
        "global_features": list,
        "edge_feature_names": list,
        "edge_tokens": list,
        "trace_feature_names": list,
        "trace_tokens": list,
        "rule_feature_names": list,
        "rule_vocab": list,
        "rule_tokens": list,
        "rule_delta_vector": list,
        "rule_harmful_vector": list,
        "soft_rule_target": list,
        "target": dict,
        "source": dict,
        "audit": dict,
    }
    for key, expected in required.items():
        if key not in row:
            errors.append(f"missing {key}")
        elif not isinstance(row[key], expected):
            errors.append(f"{key} has type {type(row[key]).__name__}, expected {expected}")
    if errors:
        return errors

    if row["schema_version"] != TOKEN_DATASET_SCHEMA_VERSION:
        errors.append(f"schema_version must be {TOKEN_DATASET_SCHEMA_VERSION}")
    if row["feature_set"] != TOKEN_FEATURE_SET:
        errors.append(f"feature_set must be {TOKEN_FEATURE_SET}")
    if row["split"] not in {"train", "validation", "test"}:
        errors.append("split must be train, validation, or test")
    if any(name in row["global_feature_names"] for name in ("split", "map_name")):
        errors.append("global_feature_names must not include leakage fields")
    _validate_vector("global_features", row["global_features"], len(row["global_feature_names"]), errors)
    if row["edge_feature_names"] != EDGE_FEATURE_NAMES:
        errors.append("edge_feature_names mismatch")
    if row["trace_feature_names"] != TRACE_FEATURE_NAMES:
        errors.append("trace_feature_names mismatch")
    if row["rule_feature_names"] != RULE_FEATURE_NAMES:
        errors.append("rule_feature_names mismatch")
    if row["rule_vocab"] != EXECUTABLE_RULE_IDS:
        errors.append("rule_vocab must be executable Phase4 rule ids")
    _validate_token_matrix("edge_tokens", row["edge_tokens"], len(EDGE_FEATURE_NAMES), errors)
    _validate_token_matrix("trace_tokens", row["trace_tokens"], len(TRACE_FEATURE_NAMES), errors)
    _validate_token_matrix("rule_tokens", row["rule_tokens"], len(RULE_FEATURE_NAMES), errors)
    _validate_vector("rule_delta_vector", row["rule_delta_vector"], len(EXECUTABLE_RULE_IDS), errors)
    if not isinstance(row["rule_harmful_vector"], list) or len(row["rule_harmful_vector"]) != len(EXECUTABLE_RULE_IDS):
        errors.append("rule_harmful_vector length mismatch")
    else:
        for index, value in enumerate(row["rule_harmful_vector"]):
            if value not in {0, 1, False, True}:
                errors.append(f"rule_harmful_vector[{index}] must be binary")
    _validate_vector("soft_rule_target", row["soft_rule_target"], len(EXECUTABLE_RULE_IDS), errors)
    if abs(sum(float(value) for value in row["soft_rule_target"]) - 1.0) > 1e-6:
        errors.append("soft_rule_target must sum to 1")

    target = row["target"]
    for key in (
        "rule_class_original",
        "best_rule_original",
        "best_rule_executable",
        "best_rule_executable_index",
        "rule_vocab_executable",
        "rule_family",
        "rule_family_index",
        "is_neutral_label",
        "harmful_update",
    ):
        if key not in target:
            errors.append(f"target missing {key}")
    if errors:
        return errors
    if target["best_rule_executable"] not in EXECUTABLE_RULE_IDS:
        errors.append("target.best_rule_executable must be executable")
    elif int(target["best_rule_executable_index"]) != EXECUTABLE_RULE_IDS.index(target["best_rule_executable"]):
        errors.append("target.best_rule_executable_index mismatch")
    if target["rule_vocab_executable"] != EXECUTABLE_RULE_IDS:
        errors.append("target.rule_vocab_executable mismatch")
    if target["rule_family"] not in RULE_FAMILY_IDS:
        errors.append("target.rule_family unknown")
    elif int(target["rule_family_index"]) != RULE_FAMILY_IDS.index(target["rule_family"]):
        errors.append("target.rule_family_index mismatch")
    if target["rule_class_original"] == "neutral_additive" and target["best_rule_executable"] != "additive_ltm":
        errors.append("neutral_additive original label must clean to additive_ltm")
    return errors


def audit_token_update_dataset_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    schema_errors: list[str] = []
    for index, row in enumerate(rows, 1):
        schema_errors.extend(f"row {index}: {error}" for error in validate_token_update_dataset_row(row))
    split_counts = Counter(str(row["split"]) for row in rows)
    executable_distribution = Counter(row["target"]["best_rule_executable"] for row in rows)
    original_distribution = Counter(row["target"]["rule_class_original"] for row in rows)
    family_distribution = Counter(row["target"]["rule_family"] for row in rows)
    non_neutral = sum(1 for row in rows if not row["target"]["is_neutral_label"])
    harmful = sum(1 for row in rows if row["target"]["harmful_update"])
    summary = {
        "schema_version": TOKEN_DATASET_SCHEMA_VERSION,
        "sample_count": len(rows),
        "split_counts": dict(sorted(split_counts.items())),
        "rule_vocab": list(EXECUTABLE_RULE_IDS),
        "rule_vocab_count": len(EXECUTABLE_RULE_IDS),
        "original_label_distribution": dict(sorted(original_distribution.items())),
        "executable_label_distribution": dict(sorted(executable_distribution.items())),
        "family_distribution": dict(sorted(family_distribution.items())),
        "non_neutral_checkpoint_count": non_neutral,
        "harmful_update_count": harmful,
        "edge_feature_count": len(EDGE_FEATURE_NAMES),
        "trace_feature_count": len(TRACE_FEATURE_NAMES),
        "rule_feature_count": len(RULE_FEATURE_NAMES),
        "max_edge_tokens_observed": max((len(row["edge_tokens"]) for row in rows), default=0),
        "max_trace_tokens_observed": max((len(row["trace_tokens"]) for row in rows), default=0),
        "schema_errors": schema_errors[:50],
        "schema_error_count": len(schema_errors),
    }
    summary["passed"] = bool(rows) and not schema_errors
    return summary


def write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["split"]), str(row["map_name"]))].append(row)
    fieldnames = [
        "split",
        "map_name",
        "sample_count",
        "non_neutral_count",
        "harmful_update_count",
        "original_label_distribution",
        "executable_label_distribution",
        "family_distribution",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for (split, map_name), values in sorted(grouped.items()):
            writer.writerow(
                {
                    "split": split,
                    "map_name": map_name,
                    "sample_count": len(values),
                    "non_neutral_count": sum(1 for row in values if not row["target"]["is_neutral_label"]),
                    "harmful_update_count": sum(1 for row in values if row["target"]["harmful_update"]),
                    "original_label_distribution": json.dumps(
                        dict(sorted(Counter(row["target"]["rule_class_original"] for row in values).items())),
                        sort_keys=True,
                    ),
                    "executable_label_distribution": json.dumps(
                        dict(sorted(Counter(row["target"]["best_rule_executable"] for row in values).items())),
                        sort_keys=True,
                    ),
                    "family_distribution": json.dumps(
                        dict(sorted(Counter(row["target"]["rule_family"] for row in values).items())),
                        sort_keys=True,
                    ),
                }
            )


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--checkpoint-jsonl", type=Path)
    parser.add_argument("--dataset-v1-jsonl", type=Path)
    parser.add_argument("--probe-jsonl", type=Path)
    parser.add_argument("--output-jsonl", type=Path)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--summary-csv", type=Path)
    parser.add_argument("--max-edge-tokens", type=int)
    parser.add_argument("--max-trace-tokens", type=int)
    parser.add_argument("--soft-temperature", type=float)
    parser.add_argument("--soft-hard-mix", type=float)
    return parser.parse_args(argv)


def _config_path(config: dict[str, Any], *keys: str) -> Any:
    current: Any = config
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    config_path = resolve_path(args.config, root)
    config = load_config(config_path)
    repair2 = config.get("repair2", {}) if isinstance(config.get("repair2", {}), dict) else {}
    dataset_opts = repair2.get("dataset", {}) if isinstance(repair2.get("dataset", {}), dict) else {}

    checkpoint_path = resolve_path(args.checkpoint_jsonl or config.get("checkpoint_jsonl"), root)
    dataset_v1_path = resolve_path(args.dataset_v1_jsonl or config.get("dataset_jsonl"), root)
    probe_path = resolve_path(args.probe_jsonl or config.get("probe_output_jsonl"), root)
    output_path = resolve_path(args.output_jsonl or _config_path(config, "repair2", "dataset_jsonl"), root)
    summary_json_path = resolve_path(args.summary_json or _config_path(config, "repair2", "dataset_summary_json"), root)
    summary_csv_path = resolve_path(args.summary_csv or _config_path(config, "repair2", "dataset_summary_csv"), root)
    if None in (checkpoint_path, dataset_v1_path, probe_path, output_path, summary_json_path, summary_csv_path):
        raise ValueError("checkpoint, v1 dataset, probe, output, and summary paths are required")
    assert checkpoint_path and dataset_v1_path and probe_path and output_path and summary_json_path and summary_csv_path

    max_edge_tokens = int(args.max_edge_tokens or dataset_opts.get("max_edge_tokens", 64))
    max_trace_tokens = int(args.max_trace_tokens or dataset_opts.get("max_trace_tokens", 64))
    soft_temperature = float(args.soft_temperature or dataset_opts.get("soft_label_temperature", 0.01))
    soft_hard_mix = float(args.soft_hard_mix if args.soft_hard_mix is not None else dataset_opts.get("soft_label_hard_mix", 0.5))

    rows = build_token_update_dataset_rows(
        read_jsonl(checkpoint_path),
        read_jsonl(dataset_v1_path),
        read_jsonl(probe_path),
        repo_root_path=root,
        max_edge_tokens=max_edge_tokens,
        max_trace_tokens=max_trace_tokens,
        soft_temperature=soft_temperature,
        soft_hard_mix=soft_hard_mix,
    )
    summary = audit_token_update_dataset_rows(rows)
    summary.update(
        {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S %z"),
            "branch": git_value(["branch", "--show-current"], root),
            "commit": git_value(["rev-parse", "--short", "HEAD"], root),
            "checkpoint_jsonl": str(checkpoint_path),
            "dataset_v1_jsonl": str(dataset_v1_path),
            "probe_jsonl": str(probe_path),
            "output_jsonl": str(output_path),
            "max_edge_tokens": max_edge_tokens,
            "max_trace_tokens": max_trace_tokens,
            "soft_label_temperature": soft_temperature,
            "soft_label_hard_mix": soft_hard_mix,
        }
    )
    if not summary["passed"]:
        raise ValueError("Repair2 token dataset audit failed:\n" + "\n".join(summary["schema_errors"][:20]))
    write_jsonl(output_path, rows)
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_summary_csv(summary_csv_path, rows)
    print(json.dumps({"output_jsonl": str(output_path), "summary_json": str(summary_json_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

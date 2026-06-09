"""Build Phase4F.4 stable-target attention datasets for LAU update rules."""

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

from czr004_teacher.stable_attention_tokens_laur import (  # noqa: E402
    EDGE_FEATURE_NAMES,
    EXECUTABLE_RULE_IDS,
    GLOBAL_FEATURE_NAMES,
    MODEL_FAMILY_NAME,
    RULE_FAMILY_IDS,
    RULE_FEATURE_NAMES,
    STABLE_ATTENTION_DATASET_SCHEMA_VERSION,
    STABLE_ATTENTION_FEATURE_SET,
    TRACE_FEATURE_NAMES,
    best_minus_additive_margin,
    best_minus_second_margin,
    build_edge_tokens,
    build_global_features,
    build_rule_tokens,
    build_trace_tokens,
    edge_candidate_count,
    executable_rule_id,
    finite,
    rule_delta_vector,
    rule_family,
    rule_family_index,
    rule_harmful_vector,
    soft_probe_target,
    soft_stable_target,
)
from czr004_teacher.topology_features_laur import TokenMapTopology, topology_for_checkpoint  # noqa: E402


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


def config_get(config: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = config
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def group_by_checkpoint(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["checkpoint_id"])].append(row)
    return grouped


def row_by_checkpoint(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["checkpoint_id"]): row for row in rows}


def _pad_tokens(tokens: list[list[float]], *, max_tokens: int, feature_count: int) -> tuple[list[list[float]], list[int]]:
    limit = max(0, int(max_tokens))
    clipped = tokens[:limit]
    mask = [1] * len(clipped)
    zero = [0.0] * feature_count
    while len(clipped) < limit:
        clipped.append(list(zero))
        mask.append(0)
    return clipped, mask


def _target_from_stable_row(
    dataset_row: dict[str, Any],
    probe_rows: list[dict[str, Any]],
    *,
    soft_temperature: float,
    soft_hard_mix: float,
) -> dict[str, Any]:
    source_target = dataset_row["target"]
    stable_meta = source_target.get("stable_target", {}) if isinstance(source_target.get("stable_target"), dict) else {}
    original_target = stable_meta.get("original_target", {}) if isinstance(stable_meta.get("original_target"), dict) else {}
    original_rule = str(original_target.get("rule_class", source_target.get("rule_class", "additive_ltm")))
    stable_rule = str(stable_meta.get("stable_rule", source_target.get("rule_class", "additive_ltm")))
    executable_rule = executable_rule_id(stable_meta.get("stable_executable", source_target.get("best_rule_id", stable_rule)))
    stable_index = EXECUTABLE_RULE_IDS.index(executable_rule)
    deltas = rule_delta_vector(probe_rows, EXECUTABLE_RULE_IDS)
    harmful = rule_harmful_vector(probe_rows, EXECUTABLE_RULE_IDS)
    stable_soft = soft_stable_target(
        deltas,
        stable_index=stable_index,
        temperature=soft_temperature,
        hard_mix=soft_hard_mix,
    )
    probe_soft = soft_probe_target(deltas, temperature=soft_temperature)
    return {
        "rule_class_original": original_rule,
        "rule_class_stable": stable_rule,
        "rule_class_executable": executable_rule,
        "rule_class_executable_index": stable_index,
        "rule_vocab_original": list(source_target.get("rule_vocab", [])),
        "rule_vocab_executable": list(EXECUTABLE_RULE_IDS),
        "rule_family": rule_family(executable_rule),
        "rule_family_index": rule_family_index(executable_rule),
        "rule_family_vocab": list(RULE_FAMILY_IDS),
        "is_neutral_label": stable_rule == "neutral_additive" or bool(source_target.get("neutral", False)),
        "harmful_update": bool(source_target.get("harmful_update", False)),
        "target_rule_harmful": bool(harmful[stable_index]),
        "any_harmful_candidate": bool(any(harmful)),
        "best_minus_second_margin": best_minus_second_margin(deltas),
        "best_minus_additive_margin": best_minus_additive_margin(deltas),
        "best_minus_stable_margin": finite(stable_meta.get("best_minus_stable")),
        "stable_target_reason": str(stable_meta.get("reason", "")),
        "stable_tie_count": int(stable_meta.get("tie_count", 0) or 0),
        "stable_tie_rules": list(stable_meta.get("tie_rules", [])),
        "rule_delta_vector": deltas,
        "rule_harmful_vector": harmful,
        "soft_rule_target_stable": stable_soft,
        "soft_rule_target_probe": probe_soft,
    }


def build_stable_attention_dataset_rows(
    checkpoint_rows: list[dict[str, Any]],
    stable_dataset_rows: list[dict[str, Any]],
    probe_rows: list[dict[str, Any]],
    *,
    repo_root_path: str | Path | None = None,
    max_edge_tokens: int = 64,
    max_trace_tokens: int = 128,
    soft_temperature: float = 0.010,
    soft_hard_mix: float = 0.5,
) -> list[dict[str, Any]]:
    checkpoints = row_by_checkpoint(checkpoint_rows)
    probes = group_by_checkpoint(probe_rows)
    topology_cache: dict[Path, TokenMapTopology] = {}
    output: list[dict[str, Any]] = []
    for dataset_row in stable_dataset_rows:
        checkpoint_id = str(dataset_row["checkpoint_id"])
        checkpoint = checkpoints.get(checkpoint_id)
        if checkpoint is None:
            continue
        probe_group = probes.get(checkpoint_id, [])
        topology = topology_for_checkpoint(checkpoint, topology_cache, repo_root=repo_root_path)
        edge_unpadded = build_edge_tokens(
            checkpoint,
            topology=topology,
            trace_rows=None,
            max_edge_tokens=max_edge_tokens,
        )
        edge_index = {
            (int(edge.get("from_id", -1)), int(edge.get("to_id", -1))): index
            for index, edge in enumerate(checkpoint.get("raw_after_topk", [])[: int(max_edge_tokens)])
        }
        trace_unpadded = build_trace_tokens(
            checkpoint,
            edge_index=edge_index,
            trace_rows=None,
            max_trace_tokens=max_trace_tokens,
        )
        edge_tokens, edge_mask = _pad_tokens(
            edge_unpadded,
            max_tokens=max_edge_tokens,
            feature_count=len(EDGE_FEATURE_NAMES),
        )
        trace_tokens, trace_mask = _pad_tokens(
            trace_unpadded,
            max_tokens=max_trace_tokens,
            feature_count=len(TRACE_FEATURE_NAMES),
        )
        target = _target_from_stable_row(
            dataset_row,
            probe_group,
            soft_temperature=soft_temperature,
            soft_hard_mix=soft_hard_mix,
        )
        output.append(
            {
                "schema_version": STABLE_ATTENTION_DATASET_SCHEMA_VERSION,
                "model_family": MODEL_FAMILY_NAME,
                "run_id": dataset_row["run_id"],
                "checkpoint_id": checkpoint_id,
                "split": dataset_row["split"],
                "map_name": dataset_row["map_name"],
                "agents": int(dataset_row["agents"]),
                "seed": int(dataset_row["seed"]),
                "iteration": int(dataset_row["iteration"]),
                "feature_set": STABLE_ATTENTION_FEATURE_SET,
                "global_feature_names": list(GLOBAL_FEATURE_NAMES),
                "global_features": build_global_features(checkpoint, topology=topology),
                "edge_feature_names": list(EDGE_FEATURE_NAMES),
                "edge_tokens": edge_tokens,
                "edge_mask": edge_mask,
                "trace_feature_names": list(TRACE_FEATURE_NAMES),
                "trace_tokens": trace_tokens,
                "trace_mask": trace_mask,
                "rule_feature_names": list(RULE_FEATURE_NAMES),
                "rule_vocab": list(EXECUTABLE_RULE_IDS),
                "rule_tokens": build_rule_tokens(EXECUTABLE_RULE_IDS),
                "rule_mask": [1] * len(EXECUTABLE_RULE_IDS),
                "rule_delta_vector": list(target["rule_delta_vector"]),
                "rule_harmful_vector": list(target["rule_harmful_vector"]),
                "soft_rule_target_stable": list(target["soft_rule_target_stable"]),
                "soft_rule_target_probe": list(target["soft_rule_target_probe"]),
                "target": target,
                "source": {
                    "stable_dataset_schema_version": dataset_row.get("schema_version"),
                    "checkpoint_schema_version": checkpoint.get("schema_version"),
                    "probe_schema_version": probe_group[0].get("schema_version") if probe_group else None,
                    "probe_rule_count": len(probe_group),
                    "checkpoint_trace_event_count": int(checkpoint.get("trace_event_count", 0) or 0),
                    "uses_raw_trace_tokens": False,
                    "raw_trace_token_reason": "phase4f4_v1_uses_checkpoint_level_compressed_trace_tokens",
                },
                "audit": {
                    "max_edge_tokens": int(max_edge_tokens),
                    "max_trace_tokens": int(max_trace_tokens),
                    "edge_candidate_count": edge_candidate_count(checkpoint),
                    "edge_token_count": len(edge_unpadded),
                    "edge_truncated": edge_candidate_count(checkpoint) > int(max_edge_tokens),
                    "trace_candidate_count": len(trace_unpadded),
                    "trace_token_count": len(trace_unpadded),
                    "trace_truncated": len(trace_unpadded) > int(max_trace_tokens),
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


def _validate_token_matrix(name: str, values: Any, expected_rows: int, expected_cols: int, errors: list[str]) -> None:
    if not isinstance(values, list):
        errors.append(f"{name} must be a list")
        return
    if len(values) != expected_rows:
        errors.append(f"{name} row count must be {expected_rows}")
    for row_index, token in enumerate(values):
        if not isinstance(token, list):
            errors.append(f"{name}[{row_index}] must be a list")
            continue
        _validate_vector(f"{name}[{row_index}]", token, expected_cols, errors)


def validate_stable_attention_dataset_row(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version": str,
        "model_family": str,
        "checkpoint_id": str,
        "split": str,
        "global_feature_names": list,
        "global_features": list,
        "edge_feature_names": list,
        "edge_tokens": list,
        "edge_mask": list,
        "trace_feature_names": list,
        "trace_tokens": list,
        "trace_mask": list,
        "rule_feature_names": list,
        "rule_vocab": list,
        "rule_tokens": list,
        "rule_mask": list,
        "rule_delta_vector": list,
        "rule_harmful_vector": list,
        "soft_rule_target_stable": list,
        "soft_rule_target_probe": list,
        "target": dict,
        "source": dict,
        "audit": dict,
    }
    for key, expected_type in required.items():
        if key not in row:
            errors.append(f"missing {key}")
        elif not isinstance(row[key], expected_type):
            errors.append(f"{key} has type {type(row[key]).__name__}, expected {expected_type.__name__}")
    if errors:
        return errors

    if row["schema_version"] != STABLE_ATTENTION_DATASET_SCHEMA_VERSION:
        errors.append(f"schema_version must be {STABLE_ATTENTION_DATASET_SCHEMA_VERSION}")
    if row["model_family"] != MODEL_FAMILY_NAME:
        errors.append(f"model_family must be {MODEL_FAMILY_NAME}")
    if row["split"] not in {"train", "validation", "test"}:
        errors.append("split must be train, validation, or test")
    if row["global_feature_names"] != GLOBAL_FEATURE_NAMES:
        errors.append("global_feature_names mismatch")
    if any(name in row["global_feature_names"] for name in ("split", "map_name", "run_id", "checkpoint_id")):
        errors.append("global_feature_names must not include leakage fields")
    if row["edge_feature_names"] != EDGE_FEATURE_NAMES:
        errors.append("edge_feature_names mismatch")
    if row["trace_feature_names"] != TRACE_FEATURE_NAMES:
        errors.append("trace_feature_names mismatch")
    if row["rule_feature_names"] != RULE_FEATURE_NAMES:
        errors.append("rule_feature_names mismatch")
    if row["rule_vocab"] != EXECUTABLE_RULE_IDS:
        errors.append("rule_vocab must be executable stable-attention rules")
    _validate_vector("global_features", row["global_features"], len(GLOBAL_FEATURE_NAMES), errors)
    _validate_token_matrix(
        "edge_tokens",
        row["edge_tokens"],
        int(row["audit"].get("max_edge_tokens", len(row["edge_tokens"]))),
        len(EDGE_FEATURE_NAMES),
        errors,
    )
    _validate_token_matrix(
        "trace_tokens",
        row["trace_tokens"],
        int(row["audit"].get("max_trace_tokens", len(row["trace_tokens"]))),
        len(TRACE_FEATURE_NAMES),
        errors,
    )
    _validate_token_matrix("rule_tokens", row["rule_tokens"], len(EXECUTABLE_RULE_IDS), len(RULE_FEATURE_NAMES), errors)
    _validate_vector("rule_delta_vector", row["rule_delta_vector"], len(EXECUTABLE_RULE_IDS), errors)
    _validate_vector("soft_rule_target_stable", row["soft_rule_target_stable"], len(EXECUTABLE_RULE_IDS), errors)
    _validate_vector("soft_rule_target_probe", row["soft_rule_target_probe"], len(EXECUTABLE_RULE_IDS), errors)
    for key in ("edge_mask", "trace_mask", "rule_mask"):
        if any(value not in {0, 1, False, True} for value in row[key]):
            errors.append(f"{key} must be binary")
    if len(row["edge_mask"]) != int(row["audit"].get("max_edge_tokens", len(row["edge_tokens"]))):
        errors.append("edge_mask length mismatch")
    if len(row["trace_mask"]) != int(row["audit"].get("max_trace_tokens", len(row["trace_tokens"]))):
        errors.append("trace_mask length mismatch")
    if len(row["rule_mask"]) != len(EXECUTABLE_RULE_IDS):
        errors.append("rule_mask length mismatch")
    if not isinstance(row["rule_harmful_vector"], list) or len(row["rule_harmful_vector"]) != len(EXECUTABLE_RULE_IDS):
        errors.append("rule_harmful_vector length mismatch")
    elif any(value not in {0, 1, False, True} for value in row["rule_harmful_vector"]):
        errors.append("rule_harmful_vector must be binary")
    for soft_name in ("soft_rule_target_stable", "soft_rule_target_probe"):
        if abs(sum(float(value) for value in row[soft_name]) - 1.0) > 1e-6:
            errors.append(f"{soft_name} must sum to one")

    target = row["target"]
    for key in (
        "rule_class_original",
        "rule_class_stable",
        "rule_class_executable",
        "is_neutral_label",
        "best_minus_second_margin",
        "best_minus_additive_margin",
        "rule_delta_vector",
        "rule_harmful_vector",
        "soft_rule_target_stable",
        "soft_rule_target_probe",
    ):
        if key not in target:
            errors.append(f"target missing {key}")
    if errors:
        return errors
    if target["rule_class_executable"] not in EXECUTABLE_RULE_IDS:
        errors.append("target.rule_class_executable must be executable")
    elif int(target["rule_class_executable_index"]) != EXECUTABLE_RULE_IDS.index(target["rule_class_executable"]):
        errors.append("target.rule_class_executable_index mismatch")
    if target["rule_class_stable"] == "neutral_additive" and target["rule_class_executable"] != "additive_ltm":
        errors.append("neutral_additive must execute as additive_ltm")
    if target["rule_delta_vector"] != row["rule_delta_vector"]:
        errors.append("target.rule_delta_vector must match top-level vector")
    if target["rule_harmful_vector"] != row["rule_harmful_vector"]:
        errors.append("target.rule_harmful_vector must match top-level vector")
    return errors


def audit_stable_attention_dataset_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    schema_errors: list[str] = []
    for index, row in enumerate(rows, 1):
        schema_errors.extend(f"row {index}: {error}" for error in validate_stable_attention_dataset_row(row))
    split_counts = Counter(str(row["split"]) for row in rows)
    stable_distribution = Counter(str(row["target"]["rule_class_stable"]) for row in rows)
    original_distribution = Counter(str(row["target"]["rule_class_original"]) for row in rows)
    executable_distribution = Counter(str(row["target"]["rule_class_executable"]) for row in rows)
    map_splits: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        map_splits[str(row["map_name"])].add(str(row["split"]))
    leakage_errors = [
        f"{map_name} appears in splits {sorted(splits)}"
        for map_name, splits in sorted(map_splits.items())
        if len(splits) > 1
    ]
    edge_truncated = sum(1 for row in rows if row["audit"].get("edge_truncated"))
    trace_truncated = sum(1 for row in rows if row["audit"].get("trace_truncated"))
    summary = {
        "schema_version": "phase4_laur_stable_attention_dataset_audit_v1",
        "dataset_schema_version": STABLE_ATTENTION_DATASET_SCHEMA_VERSION,
        "model_family": MODEL_FAMILY_NAME,
        "sample_count": len(rows),
        "split_counts": dict(sorted(split_counts.items())),
        "rule_vocab": list(EXECUTABLE_RULE_IDS),
        "rule_vocab_count": len(EXECUTABLE_RULE_IDS),
        "original_label_distribution": dict(sorted(original_distribution.items())),
        "stable_label_distribution": dict(sorted(stable_distribution.items())),
        "executable_label_distribution": dict(sorted(executable_distribution.items())),
        "non_neutral_checkpoint_count": sum(1 for row in rows if not row["target"]["is_neutral_label"]),
        "harmful_update_count": sum(1 for row in rows if row["target"]["harmful_update"]),
        "global_feature_count": len(GLOBAL_FEATURE_NAMES),
        "edge_feature_count": len(EDGE_FEATURE_NAMES),
        "trace_feature_count": len(TRACE_FEATURE_NAMES),
        "rule_feature_count": len(RULE_FEATURE_NAMES),
        "max_edge_tokens": max((int(row["audit"].get("max_edge_tokens", 0)) for row in rows), default=0),
        "max_trace_tokens": max((int(row["audit"].get("max_trace_tokens", 0)) for row in rows), default=0),
        "edge_truncated_count": edge_truncated,
        "edge_truncation_rate": edge_truncated / len(rows) if rows else 0.0,
        "trace_truncated_count": trace_truncated,
        "trace_truncation_rate": trace_truncated / len(rows) if rows else 0.0,
        "split_leakage_errors": leakage_errors,
        "split_leakage_error_count": len(leakage_errors),
        "schema_errors": schema_errors[:50],
        "schema_error_count": len(schema_errors),
    }
    summary["passed"] = bool(rows) and not schema_errors and not leakage_errors
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
        "stable_label_distribution",
        "executable_label_distribution",
        "edge_truncation_rate",
        "trace_truncation_rate",
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
                    "stable_label_distribution": json.dumps(
                        dict(sorted(Counter(row["target"]["rule_class_stable"] for row in values).items())),
                        sort_keys=True,
                    ),
                    "executable_label_distribution": json.dumps(
                        dict(sorted(Counter(row["target"]["rule_class_executable"] for row in values).items())),
                        sort_keys=True,
                    ),
                    "edge_truncation_rate": sum(1 for row in values if row["audit"].get("edge_truncated")) / len(values),
                    "trace_truncation_rate": sum(1 for row in values if row["audit"].get("trace_truncated")) / len(values),
                }
            )


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def dirty_state(root: Path) -> str:
    status = git_value(["status", "--short"], root)
    if not status:
        return "clean"
    tracked = [line for line in status.splitlines() if not line.startswith("??")]
    untracked = [line for line in status.splitlines() if line.startswith("??")]
    if tracked and untracked:
        return "tracked-dirty_untracked-present"
    if tracked:
        return "tracked-dirty"
    return "untracked-present"


def write_report(path: Path, *, root: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair4 Stable-Attention Dataset Report\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("## Code State\n\n")
        handle.write(f"- branch: `{git_value(['branch', '--show-current'], root)}`\n")
        handle.write(f"- commit: `{git_value(['rev-parse', '--short', 'HEAD'], root)}`\n")
        handle.write(f"- dirty: `{dirty_state(root)}`\n\n")
        handle.write("## Inputs\n\n")
        handle.write(f"- checkpoints: `{summary.get('checkpoint_jsonl')}`\n")
        handle.write(f"- stable dataset: `{summary.get('stable_dataset_jsonl')}`\n")
        handle.write(f"- probes: `{summary.get('probe_jsonl')}`\n")
        handle.write(f"- output: `{summary.get('output_jsonl')}`\n\n")
        handle.write("## Audit\n\n")
        handle.write(f"- samples: `{summary['sample_count']}`\n")
        handle.write(f"- schema errors: `{summary['schema_error_count']}`\n")
        handle.write(f"- split leakage errors: `{summary['split_leakage_error_count']}`\n")
        handle.write(f"- rule vocab count: `{summary['rule_vocab_count']}`\n")
        handle.write(f"- edge truncation rate: `{summary['edge_truncation_rate']}`\n")
        handle.write(f"- trace truncation rate: `{summary['trace_truncation_rate']}`\n")
        handle.write(f"- stable labels: `{summary['stable_label_distribution']}`\n")
        handle.write(f"- executable labels: `{summary['executable_label_distribution']}`\n\n")
        handle.write("## Boundary\n\n")
        handle.write(
            "This dataset exposes Repair3 stable targets for update-rule selection only. "
            "It does not use raw trace payloads, predict agent actions, or change "
            "LaCAM*/PIBT semantics.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--checkpoint-jsonl", type=Path)
    parser.add_argument("--stable-dataset-jsonl", type=Path)
    parser.add_argument("--probe-jsonl", type=Path)
    parser.add_argument("--output-jsonl", type=Path)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--summary-csv", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--max-edge-tokens", type=int)
    parser.add_argument("--max-trace-tokens", type=int)
    parser.add_argument("--soft-temperature", type=float)
    parser.add_argument("--soft-hard-mix", type=float)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    config_path = resolve_path(args.config, root)
    config = load_config(config_path)
    tokenization = config_get(config, "stable_attention", "tokenization", default={}) or {}
    stable_attention = config.get("stable_attention", {}) if isinstance(config.get("stable_attention"), dict) else {}

    checkpoint_path = resolve_path(args.checkpoint_jsonl or stable_attention.get("checkpoint_jsonl"), root)
    stable_dataset_path = resolve_path(args.stable_dataset_jsonl or stable_attention.get("stable_dataset_jsonl"), root)
    probe_path = resolve_path(args.probe_jsonl or stable_attention.get("probe_jsonl"), root)
    output_path = resolve_path(args.output_jsonl or stable_attention.get("dataset_jsonl"), root)
    summary_json_path = resolve_path(args.summary_json or stable_attention.get("dataset_summary_json"), root)
    summary_csv_path = resolve_path(args.summary_csv or stable_attention.get("dataset_summary_csv"), root)
    report_path = resolve_path(args.report or stable_attention.get("dataset_report_md"), root)
    if None in (checkpoint_path, stable_dataset_path, probe_path, output_path, summary_json_path, summary_csv_path, report_path):
        raise ValueError("checkpoint/stable dataset/probe/output/report paths are required")
    assert checkpoint_path and stable_dataset_path and probe_path and output_path and summary_json_path and summary_csv_path and report_path

    max_edge_tokens = int(args.max_edge_tokens or tokenization.get("max_edge_tokens", 64))
    max_trace_tokens = int(args.max_trace_tokens or tokenization.get("max_trace_tokens", 128))
    soft_temperature = float(args.soft_temperature or tokenization.get("soft_target_temperature", 0.010))
    soft_hard_mix = float(
        args.soft_hard_mix if args.soft_hard_mix is not None else tokenization.get("soft_target_hard_mix", 0.5)
    )
    rows = build_stable_attention_dataset_rows(
        read_jsonl(checkpoint_path),
        read_jsonl(stable_dataset_path),
        read_jsonl(probe_path),
        repo_root_path=root,
        max_edge_tokens=max_edge_tokens,
        max_trace_tokens=max_trace_tokens,
        soft_temperature=soft_temperature,
        soft_hard_mix=soft_hard_mix,
    )
    summary = audit_stable_attention_dataset_rows(rows)
    summary.update(
        {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S %z").strip(),
            "branch": git_value(["branch", "--show-current"], root),
            "commit": git_value(["rev-parse", "--short", "HEAD"], root),
            "dirty": dirty_state(root),
            "checkpoint_jsonl": str(checkpoint_path),
            "stable_dataset_jsonl": str(stable_dataset_path),
            "probe_jsonl": str(probe_path),
            "output_jsonl": str(output_path),
            "max_edge_tokens_configured": max_edge_tokens,
            "max_trace_tokens_configured": max_trace_tokens,
            "soft_target_temperature": soft_temperature,
            "soft_target_hard_mix": soft_hard_mix,
        }
    )
    if not summary["passed"]:
        raise ValueError(
            "stable-attention dataset audit failed:\n"
            + "\n".join([*summary["schema_errors"][:20], *summary["split_leakage_errors"][:20]])
        )
    write_jsonl(output_path, rows)
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_summary_csv(summary_csv_path, rows)
    write_report(report_path, root=root, summary=summary)
    print(json.dumps({"output_jsonl": str(output_path), "summary_json": str(summary_json_path), "report": str(report_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

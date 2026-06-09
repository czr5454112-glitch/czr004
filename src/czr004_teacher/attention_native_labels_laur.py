"""Build Phase4F Repair5 attention-native LAUR update-rule label datasets."""

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

from czr004_teacher.attention_native_schema_laur import (  # noqa: E402
    ATTENTION_NATIVE_DATASET_SCHEMA_VERSION,
    ATTENTION_NATIVE_FEATURE_SET,
    DEFAULT_LABEL_PARAMS,
    MODEL_FAMILY_NAME,
    audit_attention_native_rows,
    validate_attention_native_row,
)
from czr004_teacher.stable_attention_dataset_laur import (  # noqa: E402
    aggregate_trace_rows_by_checkpoint,
    group_by_checkpoint,
    read_jsonl,
    resolve_path,
    row_by_checkpoint,
    write_jsonl,
)
from czr004_teacher.stable_attention_tokens_laur import (  # noqa: E402
    EDGE_FEATURE_NAMES,
    EXECUTABLE_RULE_IDS,
    GLOBAL_FEATURE_NAMES,
    RULE_FEATURE_NAMES,
    TRACE_FEATURE_NAMES,
    build_edge_tokens,
    build_global_features,
    build_rule_tokens,
    build_trace_tokens,
    edge_candidate_count,
    finite,
    rule_family,
    rule_family_index,
    top_edge_keys,
)
from czr004_teacher.topology_features_laur import TokenMapTopology, topology_for_checkpoint  # noqa: E402


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_config(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read Repair5 configs") from exc
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def config_get(config: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = config
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


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


def _pad_tokens(
    tokens: list[list[float]],
    *,
    max_tokens: int,
    feature_count: int,
) -> tuple[list[list[float]], list[int]]:
    limit = max(0, int(max_tokens))
    clipped = [list(token[:feature_count]) for token in tokens[:limit]]
    mask = [1] * len(clipped)
    zero = [0.0] * feature_count
    while len(clipped) < limit:
        clipped.append(list(zero))
        mask.append(0)
    return clipped, mask


def _stable_softmax(values: list[float], temperature: float) -> list[float]:
    if not values:
        return []
    temp = max(1.0e-9, float(temperature))
    scaled = [float(value) / temp for value in values]
    max_value = max(scaled)
    exp_values = [math.exp(max(-60.0, min(60.0, value - max_value))) for value in scaled]
    total = sum(exp_values)
    if total <= 0.0:
        return [1.0 / len(values)] * len(values)
    return [value / total for value in exp_values]


def _probe_lookup(probe_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("rule_id")): row for row in probe_rows}


def _probe_delta_vector(probe_rows: list[dict[str, Any]]) -> tuple[list[float], list[int]]:
    lookup = _probe_lookup(probe_rows)
    values: list[float] = []
    present: list[int] = []
    for rule_id in EXECUTABLE_RULE_IDS:
        row = lookup.get(rule_id)
        if row is None or row.get("delta_ratio_vs_additive") is None:
            values.append(0.0)
            present.append(0)
        else:
            values.append(finite(row.get("delta_ratio_vs_additive")))
            present.append(1)
    return values, present


def _probe_harmful_vector(probe_rows: list[dict[str, Any]]) -> tuple[list[int], list[int]]:
    lookup = _probe_lookup(probe_rows)
    values: list[int] = []
    present: list[int] = []
    for rule_id in EXECUTABLE_RULE_IDS:
        row = lookup.get(rule_id)
        if row is None or "harmful" not in row:
            values.append(1)
            present.append(0)
        else:
            values.append(1 if row.get("harmful") else 0)
            present.append(1)
    return values, present


def _probe_success_vector(probe_rows: list[dict[str, Any]]) -> tuple[list[int], list[int]]:
    lookup = _probe_lookup(probe_rows)
    values: list[int] = []
    present: list[int] = []
    for rule_id in EXECUTABLE_RULE_IDS:
        row = lookup.get(rule_id)
        if row is None:
            values.append(0)
            present.append(0)
            continue
        if "solution_found" in row or "feasible" in row:
            values.append(1 if bool(row.get("solution_found", True)) and bool(row.get("feasible", True)) else 0)
            present.append(1)
        else:
            values.append(1)
            present.append(0)
    return values, present


def _probe_ttfs_regression_vector(probe_rows: list[dict[str, Any]]) -> tuple[list[float], list[int]]:
    lookup = _probe_lookup(probe_rows)
    additive = lookup.get("additive_ltm", {})
    additive_ttfs = additive.get("time_to_first_solution_ms")
    values: list[float] = []
    present: list[int] = []
    for rule_id in EXECUTABLE_RULE_IDS:
        row = lookup.get(rule_id)
        if row is None:
            values.append(1.0)
            present.append(0)
            continue
        if row.get("ttfs_regression_ratio") is not None:
            values.append(max(0.0, finite(row.get("ttfs_regression_ratio"), 1.0)))
            present.append(1)
            continue
        rule_ttfs = row.get("time_to_first_solution_ms")
        if rule_ttfs is None or additive_ttfs is None or finite(additive_ttfs) <= 0.0:
            values.append(1.0)
            present.append(0)
        else:
            values.append(max(0.0, finite(rule_ttfs) / finite(additive_ttfs)))
            present.append(1)
    return values, present


def _clip(value: float, lower: float, upper: float) -> float:
    return max(float(lower), min(float(upper), float(value)))


def compute_attention_native_target(
    probe_rows: list[dict[str, Any]],
    *,
    label_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    params = {**DEFAULT_LABEL_PARAMS, **(label_params or {})}
    additive_index = EXECUTABLE_RULE_IDS.index("additive_ltm")
    deltas, delta_present = _probe_delta_vector(probe_rows)
    harmful, harmful_present = _probe_harmful_vector(probe_rows)
    success, success_present = _probe_success_vector(probe_rows)
    ttfs, ttfs_present = _probe_ttfs_regression_vector(probe_rows)

    utilities: list[float] = []
    for delta, is_harmful, is_success, ttfs_ratio in zip(deltas, harmful, success, ttfs):
        utility = (
            float(delta)
            - float(params["harm_penalty"]) * float(bool(is_harmful))
            - float(params["failure_penalty"]) * float(not bool(is_success))
            - float(params["ttfs_penalty"]) * max(0.0, float(ttfs_ratio) - 1.0)
        )
        utilities.append(_clip(utility, float(params["utility_clip_min"]), float(params["utility_clip_max"])))

    safe = [1 if bool(success[index]) and bool(harmful_present[index]) and not bool(harmful[index]) else 0 for index in range(len(EXECUTABLE_RULE_IDS))]
    safe_nonadditive = [1 if index != additive_index and safe[index] else 0 for index in range(len(EXECUTABLE_RULE_IDS))]
    utility_additive = utilities[additive_index]
    safe_nonadditive_indices = [index for index, value in enumerate(safe_nonadditive) if value]
    best_safe_index: int | None = None
    if safe_nonadditive_indices:
        best_safe_index = max(safe_nonadditive_indices, key=lambda index: utilities[index])
    best_advantage = (utilities[best_safe_index] - utility_additive) if best_safe_index is not None else 0.0
    opportunity_margin = float(params["opportunity_margin"])
    high_margin = float(params["high_margin_opportunity_margin"])
    min_safe_utility = float(params["min_safe_utility"])
    opportunity_mask = [
        1
        if index != additive_index
        and safe[index]
        and utilities[index] - utility_additive >= opportunity_margin
        and utilities[index] > min_safe_utility
        else 0
        for index in range(len(EXECUTABLE_RULE_IDS))
    ]
    high_margin_mask = [
        1
        if index != additive_index
        and safe[index]
        and utilities[index] - utility_additive >= high_margin
        and utilities[index] > min_safe_utility
        else 0
        for index in range(len(EXECUTABLE_RULE_IDS))
    ]
    has_opportunity = any(bool(value) for value in opportunity_mask)
    has_high_margin_opportunity = any(bool(value) for value in high_margin_mask)

    if best_safe_index is None:
        decision = "defer_ltm"
        defer_reason = "all_nonadditive_unsafe"
        target_rule: str | None = None
    elif best_advantage < 0.0:
        decision = "defer_ltm"
        defer_reason = "additive_is_best_safe"
        target_rule = EXECUTABLE_RULE_IDS[best_safe_index]
    elif best_advantage < opportunity_margin:
        decision = "defer_ltm"
        defer_reason = "ambiguous_low_margin"
        target_rule = EXECUTABLE_RULE_IDS[best_safe_index]
    else:
        decision = "use_nonadditive"
        defer_reason = None
        target_rule = EXECUTABLE_RULE_IDS[best_safe_index]

    soft_values = [
        value if safe[index] else min(float(value), float(params["harmful_floor"]))
        for index, value in enumerate(utilities)
    ]
    soft_target = _stable_softmax(soft_values, float(params["softmax_temperature"]))
    pairwise_margin = float(params["pairwise_margin"])
    dominance: list[list[int]] = []
    observed: list[list[int]] = []
    for i in range(len(EXECUTABLE_RULE_IDS)):
        dominance_row: list[int] = []
        observed_row: list[int] = []
        for j in range(len(EXECUTABLE_RULE_IDS)):
            if i == j:
                dominance_row.append(0)
                observed_row.append(0)
                continue
            diff = utilities[i] - utilities[j]
            inverse_diff = utilities[j] - utilities[i]
            observed_pair = (safe[i] and diff >= pairwise_margin) or (safe[j] and inverse_diff >= pairwise_margin)
            dominance_row.append(1 if safe[i] and diff >= pairwise_margin else 0)
            observed_row.append(1 if observed_pair else 0)
        dominance.append(dominance_row)
        observed.append(observed_row)

    target_index = EXECUTABLE_RULE_IDS.index(target_rule) if target_rule in EXECUTABLE_RULE_IDS else -1
    attention_target_rule = target_rule if decision == "use_nonadditive" else None
    return {
        "probe_delta_vector": deltas,
        "probe_delta_present_vector": delta_present,
        "probe_harmful_vector": harmful,
        "probe_harmful_present_vector": harmful_present,
        "probe_success_vector": success,
        "probe_success_present_vector": success_present,
        "ttfs_regression_vector": ttfs,
        "ttfs_present_vector": ttfs_present,
        "risk_adjusted_utility_vector": utilities,
        "soft_utility_target": soft_target,
        "pairwise_dominance_matrix": dominance,
        "pairwise_observed_mask": observed,
        "safe_rule_mask": safe,
        "safe_nonadditive_mask": safe_nonadditive,
        "has_nonadditive_opportunity": bool(has_opportunity),
        "has_high_margin_nonadditive_opportunity": bool(has_high_margin_opportunity),
        "best_safe_nonadditive_rule": EXECUTABLE_RULE_IDS[best_safe_index] if best_safe_index is not None else None,
        "best_safe_nonadditive_index": int(best_safe_index) if best_safe_index is not None else -1,
        "best_safe_nonadditive_advantage": float(best_advantage),
        "decision_target": decision,
        "decision_index": 0 if decision == "use_nonadditive" else 1,
        "target_rule": target_rule,
        "target_rule_index": target_index,
        "attention_target_rule": attention_target_rule,
        "defer_reason": defer_reason,
        "anti_escape_sample": bool(has_high_margin_opportunity),
        "anti_escape_candidate_mask": opportunity_mask,
        "rule_family": rule_family(target_rule),
        "rule_family_index": rule_family_index(target_rule),
        "label_params": params,
        "coverage": {
            "has_probe_delta": all(bool(value) for value in delta_present),
            "has_probe_harmful": all(bool(value) for value in harmful_present),
            "has_probe_success": all(bool(value) for value in success_present),
            "has_ttfs": all(bool(value) for value in ttfs_present),
        },
    }


def build_attention_native_rows(
    checkpoint_rows: list[dict[str, Any]],
    probe_rows: list[dict[str, Any]],
    *,
    repo_root_path: str | Path | None = None,
    max_edge_tokens: int = 64,
    max_trace_tokens: int = 128,
    label_params: dict[str, Any] | None = None,
    trace_rows_by_checkpoint: dict[str, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    checkpoints = row_by_checkpoint(checkpoint_rows)
    probes = group_by_checkpoint(probe_rows)
    topology_cache: dict[Path, TokenMapTopology] = {}
    rows: list[dict[str, Any]] = []
    for checkpoint_id, checkpoint in checkpoints.items():
        probe_group = probes.get(checkpoint_id, [])
        trace_group = trace_rows_by_checkpoint.get(checkpoint_id, []) if trace_rows_by_checkpoint is not None else None
        target = compute_attention_native_target(probe_group, label_params=label_params)
        topology = topology_for_checkpoint(checkpoint, topology_cache, repo_root=repo_root_path)
        edge_unpadded = build_edge_tokens(
            checkpoint,
            topology=topology,
            trace_rows=trace_group,
            max_edge_tokens=max_edge_tokens,
        )
        edge_index = {
            edge_key: index
            for index, edge_key in enumerate(
                top_edge_keys(checkpoint, trace_rows=trace_group, max_edge_tokens=max_edge_tokens)
            )
        }
        trace_unpadded = build_trace_tokens(
            checkpoint,
            edge_index=edge_index,
            trace_rows=trace_group,
            max_trace_tokens=max_trace_tokens,
        )
        trace_candidate_count = len(trace_group) if trace_group is not None else len(trace_unpadded)
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
        row = {
            "schema_version": ATTENTION_NATIVE_DATASET_SCHEMA_VERSION,
            "model_family": MODEL_FAMILY_NAME,
            "run_id": checkpoint.get("run_id", ""),
            "checkpoint_id": checkpoint_id,
            "split": checkpoint.get("split", "train"),
            "map_name": checkpoint.get("map_name", ""),
            "agents": int(checkpoint.get("agents", 0) or 0),
            "seed": int(checkpoint.get("seed", 0) or 0),
            "iteration": int(checkpoint.get("iteration", 0) or 0),
            "feature_set": ATTENTION_NATIVE_FEATURE_SET,
            "global_feature_names": list(GLOBAL_FEATURE_NAMES),
            "global_features": build_global_features(checkpoint, topology=topology),
            "edge_feature_names": list(EDGE_FEATURE_NAMES),
            "edge_tokens": edge_tokens,
            "edge_mask": edge_mask,
            "trace_feature_names": list(TRACE_FEATURE_NAMES),
            "trace_tokens": trace_tokens,
            "trace_mask": trace_mask,
            "rule_feature_names": list(RULE_FEATURE_NAMES),
            "rule_ids": list(EXECUTABLE_RULE_IDS),
            "rule_tokens": build_rule_tokens(EXECUTABLE_RULE_IDS),
            "rule_mask": [1] * len(EXECUTABLE_RULE_IDS),
            "probe_delta_vector": list(target["probe_delta_vector"]),
            "probe_harmful_vector": list(target["probe_harmful_vector"]),
            "probe_success_vector": list(target["probe_success_vector"]),
            "ttfs_regression_vector": list(target["ttfs_regression_vector"]),
            "risk_adjusted_utility_vector": list(target["risk_adjusted_utility_vector"]),
            "soft_utility_target": list(target["soft_utility_target"]),
            "pairwise_dominance_matrix": list(target["pairwise_dominance_matrix"]),
            "pairwise_observed_mask": list(target["pairwise_observed_mask"]),
            "safe_rule_mask": list(target["safe_rule_mask"]),
            "safe_nonadditive_mask": list(target["safe_nonadditive_mask"]),
            "has_nonadditive_opportunity": bool(target["has_nonadditive_opportunity"]),
            "has_high_margin_nonadditive_opportunity": bool(target["has_high_margin_nonadditive_opportunity"]),
            "best_safe_nonadditive_rule": target["best_safe_nonadditive_rule"],
            "best_safe_nonadditive_index": int(target["best_safe_nonadditive_index"]),
            "best_safe_nonadditive_advantage": float(target["best_safe_nonadditive_advantage"]),
            "decision_target": target["decision_target"],
            "target_rule": target["target_rule"],
            "defer_reason": target["defer_reason"],
            "anti_escape_sample": bool(target["anti_escape_sample"]),
            "anti_escape_candidate_mask": list(target["anti_escape_candidate_mask"]),
            "coverage": dict(target["coverage"]),
            "target": {
                "decision_target": target["decision_target"],
                "decision_index": int(target["decision_index"]),
                "target_rule": target["target_rule"],
                "target_rule_index": int(target["target_rule_index"]),
                "attention_target_rule": target["attention_target_rule"],
                "has_nonadditive_opportunity": bool(target["has_nonadditive_opportunity"]),
                "has_high_margin_nonadditive_opportunity": bool(target["has_high_margin_nonadditive_opportunity"]),
                "best_safe_nonadditive_rule": target["best_safe_nonadditive_rule"],
                "best_safe_nonadditive_index": int(target["best_safe_nonadditive_index"]),
                "best_safe_nonadditive_advantage": float(target["best_safe_nonadditive_advantage"]),
                "defer_reason": target["defer_reason"],
                "rule_family": target["rule_family"],
                "rule_family_index": int(target["rule_family_index"]),
                "rule_vocab_executable": list(EXECUTABLE_RULE_IDS),
                "probe_delta_vector": list(target["probe_delta_vector"]),
                "probe_harmful_vector": list(target["probe_harmful_vector"]),
                "probe_success_vector": list(target["probe_success_vector"]),
                "risk_adjusted_utility_vector": list(target["risk_adjusted_utility_vector"]),
                "safe_rule_mask": list(target["safe_rule_mask"]),
                "safe_nonadditive_mask": list(target["safe_nonadditive_mask"]),
                "anti_escape_candidate_mask": list(target["anti_escape_candidate_mask"]),
                "soft_utility_target": list(target["soft_utility_target"]),
            },
            "source": {
                "checkpoint_schema_version": checkpoint.get("schema_version"),
                "probe_schema_version": probe_group[0].get("schema_version") if probe_group else None,
                "probe_rule_count": len(probe_group),
                "checkpoint_trace_event_count": int(checkpoint.get("trace_event_count", 0) or 0),
                "uses_raw_trace_tokens": trace_rows_by_checkpoint is not None,
                "raw_trace_token_reason": (
                    "raw_trace_event_aggregates_by_checkpoint"
                    if trace_rows_by_checkpoint is not None
                    else "checkpoint_level_compressed_trace_tokens"
                ),
            },
            "audit": {
                "max_edge_tokens": int(max_edge_tokens),
                "max_trace_tokens": int(max_trace_tokens),
                "edge_candidate_count": edge_candidate_count(checkpoint, trace_rows=trace_group),
                "edge_token_count": len(edge_unpadded),
                "edge_truncated": edge_candidate_count(checkpoint, trace_rows=trace_group) > int(max_edge_tokens),
                "trace_candidate_count": trace_candidate_count,
                "trace_token_count": len(trace_unpadded),
                "trace_truncated": trace_candidate_count > int(max_trace_tokens),
                "label_params": dict(target["label_params"]),
            },
        }
        rows.append(row)
    return rows


def write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["split"]), str(row["map_name"]))].append(row)
    fieldnames = [
        "split",
        "map_name",
        "sample_count",
        "opportunity_count",
        "high_margin_opportunity_count",
        "decision_distribution",
        "target_rule_distribution",
        "defer_reason_distribution",
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
                    "opportunity_count": sum(1 for row in values if row["has_nonadditive_opportunity"]),
                    "high_margin_opportunity_count": sum(
                        1 for row in values if row["has_high_margin_nonadditive_opportunity"]
                    ),
                    "decision_distribution": json.dumps(
                        dict(sorted(Counter(row["decision_target"] for row in values).items())),
                        sort_keys=True,
                    ),
                    "target_rule_distribution": json.dumps(
                        dict(sorted(Counter(str(row["target_rule"]) for row in values).items())),
                        sort_keys=True,
                    ),
                    "defer_reason_distribution": json.dumps(
                        dict(sorted(Counter(str(row["defer_reason"]) for row in values).items())),
                        sort_keys=True,
                    ),
                }
            )


def write_report(path: Path, *, root: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4F Repair5 Attention-Native Label Audit\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z').strip()}\n\n")
        handle.write("## Code State\n\n")
        handle.write(f"- branch: `{git_value(['branch', '--show-current'], root)}`\n")
        handle.write(f"- commit: `{git_value(['rev-parse', '--short', 'HEAD'], root)}`\n")
        handle.write(f"- dirty: `{dirty_state(root)}`\n\n")
        handle.write("## Inputs\n\n")
        handle.write(f"- checkpoints: `{summary.get('checkpoint_jsonl')}`\n")
        handle.write(f"- probes: `{summary.get('probe_jsonl')}`\n")
        handle.write(f"- raw trace: `{summary.get('trace_jsonl')}`\n")
        handle.write(f"- output: `{summary.get('output_jsonl')}`\n\n")
        handle.write("## Audit\n\n")
        handle.write(f"- samples: `{summary['sample_count']}`\n")
        handle.write(f"- schema errors: `{summary['schema_error_count']}`\n")
        handle.write(f"- split leakage errors: `{summary['split_leakage_error_count']}`\n")
        handle.write(f"- decisions: `{summary['decision_distribution']}`\n")
        handle.write(f"- target rules: `{summary['target_rule_distribution']}`\n")
        handle.write(f"- defer reasons: `{summary['defer_reason_distribution']}`\n")
        handle.write(f"- opportunity count: `{summary['nonadditive_opportunity_count']}`\n")
        handle.write(f"- high-margin opportunity count: `{summary['high_margin_nonadditive_opportunity_count']}`\n")
        handle.write(f"- validation opportunity count: `{summary['validation_opportunity_count']}`\n")
        handle.write(f"- validation high-margin opportunity count: `{summary['validation_high_margin_opportunity_count']}`\n")
        handle.write(f"- missing harmful coverage: `{summary['missing_harmful_coverage_count']}`\n")
        handle.write(f"- passed: `{summary['passed']}`\n\n")
        handle.write("## Boundary\n\n")
        handle.write(
            "This dataset is Repair5 attention-native supervision for LAUR/LAU UpdateLTM only. "
            "`defer_ltm` is a meta-decision and is not an executable update rule; runtime maps it "
            "to additive LTM only after offline gates pass.\n"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--checkpoint-jsonl", type=Path)
    parser.add_argument("--probe-jsonl", type=Path)
    parser.add_argument("--trace-jsonl", type=Path)
    parser.add_argument("--output-jsonl", type=Path)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--summary-csv", type=Path)
    parser.add_argument("--report-md", type=Path)
    parser.add_argument("--max-edge-tokens", type=int)
    parser.add_argument("--max-trace-tokens", type=int)
    parser.add_argument("--use-raw-trace", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    config_path = resolve_path(args.config, root)
    config = load_config(config_path)
    inputs = config.get("inputs", {}) if isinstance(config.get("inputs"), dict) else {}
    outputs = config.get("outputs", {}) if isinstance(config.get("outputs"), dict) else {}
    tokenization = config.get("tokenization", {}) if isinstance(config.get("tokenization"), dict) else {}
    label_config = config.get("label", {}) if isinstance(config.get("label"), dict) else {}

    checkpoint_path = resolve_path(args.checkpoint_jsonl or inputs.get("checkpoint_jsonl"), root)
    probe_path = resolve_path(args.probe_jsonl or inputs.get("probe_jsonl"), root)
    trace_path = resolve_path(args.trace_jsonl or inputs.get("raw_trace_zst"), root)
    output_path = resolve_path(args.output_jsonl or outputs.get("dataset_jsonl"), root)
    summary_json_path = resolve_path(args.summary_json or outputs.get("label_audit_json"), root)
    summary_csv_path = resolve_path(args.summary_csv or outputs.get("label_audit_csv"), root)
    report_path = resolve_path(args.report_md or outputs.get("label_audit_md"), root)
    if None in (checkpoint_path, probe_path, output_path, summary_json_path, summary_csv_path, report_path):
        raise ValueError("checkpoint/probe/output/summary/report paths are required")
    assert checkpoint_path and probe_path and output_path and summary_json_path and summary_csv_path and report_path

    max_edge_tokens = int(args.max_edge_tokens or tokenization.get("max_edge_tokens", 64))
    max_trace_tokens = int(args.max_trace_tokens or tokenization.get("max_trace_tokens", 128))
    checkpoint_rows = read_jsonl(checkpoint_path)
    probe_rows = read_jsonl(probe_path)
    trace_rows_by_checkpoint = None
    use_raw_trace = bool(args.use_raw_trace or tokenization.get("use_raw_trace", False))
    if use_raw_trace:
        if trace_path is None or not trace_path.exists():
            raise FileNotFoundError(f"raw trace requested but not found: {trace_path}")
        trace_rows_by_checkpoint = aggregate_trace_rows_by_checkpoint(
            trace_path,
            {str(row["checkpoint_id"]) for row in checkpoint_rows},
        )
    rows = build_attention_native_rows(
        checkpoint_rows,
        probe_rows,
        repo_root_path=root,
        max_edge_tokens=max_edge_tokens,
        max_trace_tokens=max_trace_tokens,
        label_params=label_config,
        trace_rows_by_checkpoint=trace_rows_by_checkpoint,
    )
    schema_errors: list[str] = []
    for index, row in enumerate(rows, 1):
        schema_errors.extend(f"row {index}: {error}" for error in validate_attention_native_row(row))
    if schema_errors:
        raise ValueError("attention-native dataset schema errors:\n" + "\n".join(schema_errors[:30]))

    summary = audit_attention_native_rows(rows)
    summary.update(
        {
            "checkpoint_jsonl": str(checkpoint_path),
            "probe_jsonl": str(probe_path),
            "trace_jsonl": str(trace_path) if trace_path else None,
            "output_jsonl": str(output_path),
            "label_params": {**DEFAULT_LABEL_PARAMS, **label_config},
            "max_edge_tokens": max_edge_tokens,
            "max_trace_tokens": max_trace_tokens,
            "uses_raw_trace_tokens": trace_rows_by_checkpoint is not None,
            "branch": git_value(["branch", "--show-current"], root),
            "commit": git_value(["rev-parse", "--short", "HEAD"], root),
            "dirty": dirty_state(root),
        }
    )
    write_jsonl(output_path, rows)
    summary_json_path.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_summary_csv(summary_csv_path, rows)
    write_report(report_path, root=root, summary=summary)
    print(json.dumps({"dataset": str(output_path), "summary_json": str(summary_json_path), "report": str(report_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

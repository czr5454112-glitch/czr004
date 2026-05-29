"""Schema and gate helpers for Phase4F Repair5 attention-native LAUR labels."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

from czr004_teacher.stable_attention_tokens_laur import (
    EDGE_FEATURE_NAMES,
    EXECUTABLE_RULE_IDS,
    GLOBAL_FEATURE_NAMES,
    RULE_FEATURE_NAMES,
    TRACE_FEATURE_NAMES,
)


ATTENTION_NATIVE_DATASET_SCHEMA_VERSION = "phase4_laur_attention_native_label_dataset_v1"
ATTENTION_NATIVE_AUDIT_SCHEMA_VERSION = "phase4_laur_attention_native_label_audit_v1"
ATTENTION_NATIVE_FEATURE_SET = "attention_native_tokens_v1"
MODEL_FAMILY_NAME = "LAU-AttentionNative-v1"
DECISION_IDS = ["use_nonadditive", "defer_ltm"]
DEFER_REASONS = [
    "all_nonadditive_unsafe",
    "additive_is_best_safe",
    "ambiguous_low_margin",
    "missing_probe_evidence",
]

DEFAULT_LABEL_PARAMS = {
    "harm_penalty": 0.050,
    "failure_penalty": 0.100,
    "ttfs_penalty": 0.010,
    "utility_clip_min": -0.100,
    "utility_clip_max": 0.100,
    "opportunity_margin": 0.010,
    "high_margin_opportunity_margin": 0.020,
    "pairwise_margin": 0.005,
    "softmax_temperature": 0.010,
    "harmful_floor": -0.050,
    "min_safe_utility": 0.0,
}

DEFAULT_ANTI_ESCAPE_THRESHOLDS = {
    "min_validation_high_margin_opportunity_count": 50,
    "high_margin_nonadditive_capture_rate_min": 0.40,
    "avoidable_additive_or_defer_rate_max": 0.60,
    "anti_escape_mean_selected_vs_additive_delta_min": 0.005,
    "opportunity_nonadditive_selection_rate_min": 0.35,
    "global_additive_or_defer_rate_max": 0.70,
}


def is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _validate_vector(
    name: str,
    values: Any,
    expected_len: int,
    errors: list[str],
    *,
    binary: bool = False,
) -> None:
    if not isinstance(values, list):
        errors.append(f"{name} must be a list")
        return
    if len(values) != expected_len:
        errors.append(f"{name} length must be {expected_len}")
    for index, value in enumerate(values):
        if binary:
            if value not in {0, 1, False, True}:
                errors.append(f"{name}[{index}] must be binary")
        elif not is_finite_number(value):
            errors.append(f"{name}[{index}] must be finite numeric")


def _validate_token_matrix(
    name: str,
    values: Any,
    expected_rows: int,
    expected_cols: int,
    errors: list[str],
) -> None:
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


def _validate_matrix(
    name: str,
    values: Any,
    expected_rows: int,
    expected_cols: int,
    errors: list[str],
    *,
    binary: bool = False,
) -> None:
    if not isinstance(values, list):
        errors.append(f"{name} must be a list")
        return
    if len(values) != expected_rows:
        errors.append(f"{name} row count must be {expected_rows}")
    for row_index, row in enumerate(values):
        if not isinstance(row, list):
            errors.append(f"{name}[{row_index}] must be a list")
            continue
        _validate_vector(f"{name}[{row_index}]", row, expected_cols, errors, binary=binary)


def validate_attention_native_row(row: dict[str, Any]) -> list[str]:
    """Return schema errors for one Repair5 attention-native dataset row."""

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
        "rule_ids": list,
        "rule_tokens": list,
        "rule_mask": list,
        "probe_delta_vector": list,
        "probe_harmful_vector": list,
        "probe_success_vector": list,
        "risk_adjusted_utility_vector": list,
        "soft_utility_target": list,
        "pairwise_dominance_matrix": list,
        "pairwise_observed_mask": list,
        "safe_rule_mask": list,
        "safe_nonadditive_mask": list,
        "has_nonadditive_opportunity": bool,
        "has_high_margin_nonadditive_opportunity": bool,
        "decision_target": str,
        "anti_escape_sample": bool,
        "anti_escape_candidate_mask": list,
        "coverage": dict,
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

    rule_count = len(EXECUTABLE_RULE_IDS)
    if row["schema_version"] != ATTENTION_NATIVE_DATASET_SCHEMA_VERSION:
        errors.append(f"schema_version must be {ATTENTION_NATIVE_DATASET_SCHEMA_VERSION}")
    if row["model_family"] != MODEL_FAMILY_NAME:
        errors.append(f"model_family must be {MODEL_FAMILY_NAME}")
    if row["split"] not in {"train", "validation", "test"}:
        errors.append("split must be train, validation, or test")
    if row["rule_ids"] != EXECUTABLE_RULE_IDS:
        errors.append("rule_ids must be executable LAUR update rules")
    if "defer_ltm" in row["rule_ids"]:
        errors.append("defer_ltm must not be an executable rule id")
    if row["decision_target"] not in DECISION_IDS:
        errors.append(f"decision_target must be one of {DECISION_IDS}")
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
    _validate_token_matrix("rule_tokens", row["rule_tokens"], rule_count, len(RULE_FEATURE_NAMES), errors)
    for key in ("edge_mask", "trace_mask", "rule_mask"):
        if any(value not in {0, 1, False, True} for value in row[key]):
            errors.append(f"{key} must be binary")
    if len(row["edge_mask"]) != int(row["audit"].get("max_edge_tokens", len(row["edge_tokens"]))):
        errors.append("edge_mask length mismatch")
    if len(row["trace_mask"]) != int(row["audit"].get("max_trace_tokens", len(row["trace_tokens"]))):
        errors.append("trace_mask length mismatch")
    if len(row["rule_mask"]) != rule_count:
        errors.append("rule_mask length mismatch")

    for key in (
        "probe_delta_vector",
        "risk_adjusted_utility_vector",
        "soft_utility_target",
        "best_safe_nonadditive_advantage",
    ):
        if key == "best_safe_nonadditive_advantage":
            if not is_finite_number(row.get(key)):
                errors.append(f"{key} must be finite numeric")
            continue
        _validate_vector(key, row[key], rule_count, errors)
    for key in (
        "probe_harmful_vector",
        "probe_success_vector",
        "safe_rule_mask",
        "safe_nonadditive_mask",
        "anti_escape_candidate_mask",
    ):
        _validate_vector(key, row[key], rule_count, errors, binary=True)
    _validate_matrix("pairwise_dominance_matrix", row["pairwise_dominance_matrix"], rule_count, rule_count, errors, binary=True)
    _validate_matrix("pairwise_observed_mask", row["pairwise_observed_mask"], rule_count, rule_count, errors, binary=True)
    if abs(sum(float(value) for value in row["soft_utility_target"]) - 1.0) > 1e-6:
        errors.append("soft_utility_target must sum to one")
    if row["anti_escape_sample"] != row["has_high_margin_nonadditive_opportunity"]:
        errors.append("anti_escape_sample must equal has_high_margin_nonadditive_opportunity")
    if row["anti_escape_sample"] and not any(bool(value) for value in row["anti_escape_candidate_mask"]):
        errors.append("anti_escape_sample requires a candidate mask")

    target = row["target"]
    for key in (
        "decision_target",
        "target_rule",
        "attention_target_rule",
        "decision_index",
        "target_rule_index",
        "has_nonadditive_opportunity",
        "has_high_margin_nonadditive_opportunity",
        "safe_rule_mask",
        "safe_nonadditive_mask",
        "risk_adjusted_utility_vector",
    ):
        if key not in target:
            errors.append(f"target missing {key}")
    if errors:
        return errors
    if target["decision_target"] != row["decision_target"]:
        errors.append("target.decision_target must match top-level decision_target")
    if target["decision_target"] == "use_nonadditive":
        if target["target_rule"] not in EXECUTABLE_RULE_IDS or target["target_rule"] == "additive_ltm":
            errors.append("use_nonadditive target_rule must be a non-additive executable rule")
        elif int(target["target_rule_index"]) != EXECUTABLE_RULE_IDS.index(target["target_rule"]):
            errors.append("target_rule_index mismatch")
        if target["attention_target_rule"] != target["target_rule"]:
            errors.append("attention_target_rule must equal target_rule on use_nonadditive samples")
    else:
        if target["attention_target_rule"] is not None:
            errors.append("defer_ltm samples must not expose an attention_target_rule")
        if target["target_rule"] not in {None, "additive_ltm"} and target["target_rule"] not in EXECUTABLE_RULE_IDS:
            errors.append("defer target_rule must be null or executable")
        if row.get("defer_reason") not in DEFER_REASONS:
            errors.append("defer_ltm samples require a known defer_reason")
    if target["risk_adjusted_utility_vector"] != row["risk_adjusted_utility_vector"]:
        errors.append("target.risk_adjusted_utility_vector must match top-level vector")
    if target["safe_rule_mask"] != row["safe_rule_mask"]:
        errors.append("target.safe_rule_mask must match top-level safe_rule_mask")
    if target["safe_nonadditive_mask"] != row["safe_nonadditive_mask"]:
        errors.append("target.safe_nonadditive_mask must match top-level safe_nonadditive_mask")
    return errors


def split_leakage_errors(rows: list[dict[str, Any]]) -> list[str]:
    map_splits: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        map_splits[str(row.get("map_name", ""))].add(str(row.get("split", "")))
    return [
        f"{map_name} appears in splits {sorted(splits)}"
        for map_name, splits in sorted(map_splits.items())
        if len(splits) > 1
    ]


def audit_attention_native_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    schema_errors: list[str] = []
    for index, row in enumerate(rows, 1):
        schema_errors.extend(f"row {index}: {error}" for error in validate_attention_native_row(row))
    leakage = split_leakage_errors(rows)
    split_counts = Counter(str(row.get("split", "")) for row in rows)
    decision_distribution = Counter(str(row.get("decision_target", "")) for row in rows)
    target_rules = Counter(str(row.get("target", {}).get("target_rule")) for row in rows)
    defer_reasons = Counter(str(row.get("defer_reason")) for row in rows if row.get("decision_target") == "defer_ltm")
    opportunity = [row for row in rows if row.get("has_nonadditive_opportunity")]
    high_margin = [row for row in rows if row.get("has_high_margin_nonadditive_opportunity")]
    split_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        split_groups[str(row.get("split", ""))].append(row)
    split_diagnostics: dict[str, dict[str, Any]] = {}
    for split, values in sorted(split_groups.items()):
        split_diagnostics[split] = {
            "sample_count": len(values),
            "decision_distribution": dict(
                sorted(Counter(str(row.get("decision_target", "")) for row in values).items())
            ),
            "target_rule_distribution": dict(
                sorted(Counter(str(row.get("target", {}).get("target_rule")) for row in values).items())
            ),
            "defer_reason_distribution": dict(
                sorted(
                    Counter(
                        str(row.get("defer_reason"))
                        for row in values
                        if row.get("decision_target") == "defer_ltm"
                    ).items()
                )
            ),
            "nonadditive_opportunity_count": sum(
                1 for row in values if row.get("has_nonadditive_opportunity")
            ),
            "high_margin_nonadditive_opportunity_count": sum(
                1 for row in values if row.get("has_high_margin_nonadditive_opportunity")
            ),
        }
    missing_harmful = sum(1 for row in rows if not row.get("coverage", {}).get("has_probe_harmful", False))
    missing_delta = sum(1 for row in rows if not row.get("coverage", {}).get("has_probe_delta", False))
    summary = {
        "schema_version": ATTENTION_NATIVE_AUDIT_SCHEMA_VERSION,
        "dataset_schema_version": ATTENTION_NATIVE_DATASET_SCHEMA_VERSION,
        "model_family": MODEL_FAMILY_NAME,
        "sample_count": len(rows),
        "split_counts": dict(sorted(split_counts.items())),
        "split_diagnostics": split_diagnostics,
        "rule_ids": list(EXECUTABLE_RULE_IDS),
        "decision_distribution": dict(sorted(decision_distribution.items())),
        "target_rule_distribution": dict(sorted(target_rules.items())),
        "defer_reason_distribution": dict(sorted(defer_reasons.items())),
        "nonadditive_opportunity_count": len(opportunity),
        "high_margin_nonadditive_opportunity_count": len(high_margin),
        "nonadditive_opportunity_rate": len(opportunity) / len(rows) if rows else 0.0,
        "high_margin_nonadditive_opportunity_rate": len(high_margin) / len(rows) if rows else 0.0,
        "validation_opportunity_count": sum(
            1 for row in rows if row.get("split") == "validation" and row.get("has_nonadditive_opportunity")
        ),
        "validation_high_margin_opportunity_count": sum(
            1
            for row in rows
            if row.get("split") == "validation" and row.get("has_high_margin_nonadditive_opportunity")
        ),
        "missing_harmful_coverage_count": missing_harmful,
        "missing_delta_coverage_count": missing_delta,
        "global_feature_count": len(GLOBAL_FEATURE_NAMES),
        "edge_feature_count": len(EDGE_FEATURE_NAMES),
        "trace_feature_count": len(TRACE_FEATURE_NAMES),
        "rule_feature_count": len(RULE_FEATURE_NAMES),
        "schema_errors": schema_errors[:50],
        "schema_error_count": len(schema_errors),
        "split_leakage_errors": leakage,
        "split_leakage_error_count": len(leakage),
    }
    summary["passed"] = bool(rows) and not schema_errors and not leakage
    return summary

"""Shared helpers for Repair5G.5.14 rich trace feature diagnostics."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable

from repair5g512_common import (
    boolish,
    context_key,
    csv_number,
    finite_number,
    observed_id_guard,
    repo_root,
)


G514_CLOSED_CLAIMS = {
    "phase5p5_allowed": False,
    "phase6_allowed": False,
    "aaai_ready": False,
    "runtime_claim_allowed": False,
    "learned_runtime_policy_validated": False,
}

RISK_LAMBDAS = [0.05, 0.10, 0.20]

ALLOWED_RICH_FIELDS = [
    "committed_count",
    "blocked_count",
    "wait_event_count",
    "progress_committed_count",
    "nonprogress_committed_count",
    "blocked_per_committed",
    "wait_per_committed",
    "blocked_per_agent",
    "committed_per_agent",
    "progress_ratio",
    "c_update_count",
    "f_update_count",
    "c_nonzero_edges",
    "f_nonzero_edges",
    "c_flow_update_ratio",
    "cost_min",
    "cost_max",
    "cost_span",
    "cost_bounds_respected",
]

REQUIRED_CHECKPOINT_KEYS = [
    "feature_names",
    "feature_values",
    "traffic_before_hash_full",
    "map",
    "agents",
    "seed",
    "iteration",
]

DEFAULT_CHECKPOINT_ARTIFACT_CSV = "outputs/tables/phase5p5_repair5g514_existing_rich_checkpoint_artifacts.csv"
DEFAULT_CHECKPOINT_ARTIFACT_SUMMARY = "outputs/reports/phase5p5_repair5g514_existing_rich_checkpoint_artifacts_summary.json"
DEFAULT_RICH_CONTEXT_CSV = "outputs/tables/phase5p5_repair5g514_rich_context_features_by_context.csv"
DEFAULT_RICH_CONTEXT_SUMMARY = "outputs/reports/phase5p5_repair5g514_rich_context_features_summary.json"
DEFAULT_V4_MATRIX = "outputs/tables/phase5p5_repair5g514_candidate_feature_matrix_v4.csv"
DEFAULT_V4_MODEL = "outputs/reports/phase5p5_repair5g514_candidate_ranker_v4_model.json"


def rich_feature_column(field: str) -> str:
    return f"feature_rich_{field}"


def all_rich_feature_columns() -> list[str]:
    return [rich_feature_column(field) for field in ALLOWED_RICH_FIELDS]


def expand_feature_vector(record: dict[str, Any]) -> dict[str, Any]:
    names = record.get("feature_names", [])
    values = record.get("feature_values", [])
    if not isinstance(names, list) or not isinstance(values, list):
        return {}
    return {str(name): value for name, value in zip(names, values)}


def checkpoint_record_has_required_fields(record: dict[str, Any]) -> bool:
    if not all(key in record for key in REQUIRED_CHECKPOINT_KEYS):
        return False
    feature_values = expand_feature_vector(record)
    return all(field in feature_values for field in ALLOWED_RICH_FIELDS)


def checkpoint_context_key(record: dict[str, Any]) -> str:
    return context_key(
        {
            "map": record.get("map", ""),
            "agents": record.get("agents", ""),
            "seed": record.get("seed", ""),
            "iteration": record.get("iteration", ""),
            "traffic_before_hash_full": record.get("traffic_before_hash_full", ""),
        }
    )


def rich_values_from_checkpoint(record: dict[str, Any]) -> dict[str, Any]:
    features = expand_feature_vector(record)
    values: dict[str, Any] = {}
    for field in ALLOWED_RICH_FIELDS:
        raw = features.get(field, "")
        if field == "cost_bounds_respected":
            values[f"rich_{field}"] = boolish(raw)
            values[rich_feature_column(field)] = 1.0 if boolish(raw) else 0.0
        else:
            values[f"rich_{field}"] = csv_number(finite_number(raw, 0.0))
            values[rich_feature_column(field)] = csv_number(finite_number(raw, 0.0))
    return values


def load_jsonl_records(path: Path, *, required_only: bool = True) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            if required_only and not all(f'"{key}"' in line for key in REQUIRED_CHECKPOINT_KEYS):
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if required_only and not checkpoint_record_has_required_fields(record):
                continue
            record["_source_line_number"] = line_number
            yield record


def observed_flags_for_seeds(seeds: Iterable[Any]) -> dict[str, bool]:
    ids = observed_id_guard(seeds, label="G5.14 rich checkpoint seeds")
    return {
        "observed_ids_only": all(seed <= 165 for seed in ids),
        "ids_166_205_untouched": all(not (166 <= seed <= 205) for seed in ids),
    }


def risk_adjusted_summary(row: dict[str, Any]) -> dict[str, Any]:
    mean_delta = finite_number(row.get("mean_delta_vs_static"), math.inf)
    harmful = finite_number(row.get("harmful_vs_static_rate"), math.inf)
    return {
        f"risk_adjusted_utility_lambda_{str(lam).replace('.', 'p')}": (
            mean_delta + lam * harmful if math.isfinite(mean_delta) and math.isfinite(harmful) else math.inf
        )
        for lam in RISK_LAMBDAS
    }


def default_search_roots(root: Path | None = None) -> list[Path]:
    base = root or repo_root()
    return [
        base / "outputs" / "logs",
        base / "outputs" / "server" / "phase5p5_repair5g511_remote",
        base / "outputs" / "server",
    ]

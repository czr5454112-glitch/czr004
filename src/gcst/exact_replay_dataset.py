"""Exact replay pair ingestion helpers for G5.65 repair experiments."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable

from .theta_schema import THETA_NUMERIC_COLUMNS


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def replay_context_uid(row: dict[str, Any]) -> str:
    return str(
        row.get("g562_evaluation_uid")
        or row.get("g561_evaluation_uid")
        or row.get("g560_evaluation_uid")
        or row.get("evaluation_uid")
        or row.get("context_id")
        or ""
    )


def replay_dataset_uid(row: dict[str, Any]) -> str:
    return str(
        row.get("g562_dataset_row_id")
        or row.get("g561_dataset_row_id")
        or row.get("g560_instance_uid")
        or row.get("dataset_row_id")
        or row.get("context_id")
        or ""
    )


def exact_pair_is_materialized(row: dict[str, Any]) -> bool:
    return (
        boolish(row.get("candidate_recognized", row.get("candidate_recognized_bool", "true")))
        and boolish(row.get("fingerprint_match", row.get("fulltheta_fingerprint_match_strict", "true")))
        and boolish(row.get("scenario_hash_match", row.get("scenario_sha256_match", "true")))
    )


def exact_pair_to_label_row(row: dict[str, Any], source_path: str) -> dict[str, Any]:
    safe = (not boolish(row.get("success_regression"))) and exact_pair_is_materialized(row)
    out: dict[str, Any] = {
        "g560_evaluation_uid": replay_context_uid(row),
        "g560_instance_uid": replay_dataset_uid(row),
        "split": row.get("split", "unassigned"),
        "g560_physical_map_sha256": row.get("g562_physical_map_sha256") or row.get("physical_map_sha256", ""),
        "map": row.get("map", ""),
        "map_family": row.get("map_family", ""),
        "agent_count": row.get("agents", row.get("agent_count", "")),
        "nominal_budget_ms": row.get("budget_ms", ""),
        "horizon_id": row.get("horizon_id", ""),
        "candidate_uid": row.get("theta_id", row.get("candidate_id", "")),
        "generated_theta_uid": row.get("theta_id", row.get("candidate_id", "")),
        "labelv51_development_safe": str(safe),
        "labelv51_comparable_quality": str(boolish(row.get("both_success"))),
        "quality_delta_vs_g556": row.get("quality_delta_vs_g556", ""),
        "labelv51_success_gain": row.get("success_gain", "False"),
        "labelv51_success_regression": row.get("success_regression", "False"),
        "g565_source_replay_pair": source_path,
    }
    for col in THETA_NUMERIC_COLUMNS:
        out[col] = row.get(col, "")
    return out


def unique_exact_label_rows(rows: Iterable[dict[str, Any]], source_path: str) -> list[dict[str, Any]]:
    dedup: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        converted = exact_pair_to_label_row(row, source_path)
        key = (
            str(converted.get("g560_evaluation_uid", "")),
            str(converted.get("candidate_uid", "")),
            str(converted.get("g565_source_replay_pair", "")),
        )
        if key[0] and key[1]:
            dedup[key] = converted
    return list(dedup.values())

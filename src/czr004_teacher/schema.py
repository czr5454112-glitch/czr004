"""Schema checks for Phase3 teacher manifests and edge labels."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


EDGE_LABEL_SCHEMA_VERSION = "phase3_edge_label_v1"
MANIFEST_SCHEMA_VERSION = "phase3_teacher_manifest_v1"
TRACE_SCHEMA_VERSION = "phase3_pibt_trace_v1"
PRIMARY_SUPERVISION = "online_residual"

VALID_SPLITS = {"train", "validation", "test"}

EDGE_LABEL_REQUIRED_TYPES: dict[str, type | tuple[type, ...]] = {
    "schema_version": str,
    "run_id": str,
    "source": str,
    "method": str,
    "map": str,
    "scen": str,
    "agents": int,
    "seed": int,
    "time_limit_sec": (int, float),
    "objective": str,
    "from_id": int,
    "to_id": int,
    "from_index": int,
    "to_index": int,
    "from_x": int,
    "from_y": int,
    "to_x": int,
    "to_y": int,
    "from_degree": int,
    "to_degree": int,
    "ltm_raw_count": (int, float),
    "ltm_normalized_weight": (int, float),
    "warm_start_target_weight": (int, float),
    "residual_reference_weight": (int, float),
    "residual_delta_target": (int, float),
    "traversal_cost": (int, float),
    "nonzero": bool,
    "map_vertices": int,
}

MANIFEST_REQUIRED_TYPES: dict[str, type | tuple[type, ...]] = {
    "schema_version": str,
    "run_id": str,
    "split": str,
    "primary_supervision": str,
    "warm_start_target": str,
    "edge_label_schema_version": str,
    "trace_schema_version": str,
    "label_path": str,
    "label_sha256": str,
    "label_rows": int,
    "method": str,
    "map": str,
    "scen": str,
    "agents": int,
    "seed": int,
    "time_limit_sec": (int, float),
    "objective": str,
    "success": bool,
    "feasible": bool,
    "git_commit": str,
    "external_lacam2_commit": str,
    "source_manifest": str,
}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _type_errors(row: dict, required: dict[str, type | tuple[type, ...]]) -> list[str]:
    errors: list[str] = []
    for key, expected in required.items():
        if key not in row:
            errors.append(f"missing {key}")
            continue
        if not isinstance(row[key], expected):
            errors.append(f"{key} has type {type(row[key]).__name__}, expected {expected}")
    return errors


def _finite_number(row: dict, key: str, errors: list[str]) -> None:
    value = row.get(key)
    if not _is_number(value) or not math.isfinite(float(value)):
        errors.append(f"{key} must be a finite number")


def validate_edge_label(row: dict) -> list[str]:
    """Return validation errors for one Phase3 edge-label row."""

    errors = _type_errors(row, EDGE_LABEL_REQUIRED_TYPES)
    if errors:
        return errors

    if row["schema_version"] != EDGE_LABEL_SCHEMA_VERSION:
        errors.append(f"schema_version must be {EDGE_LABEL_SCHEMA_VERSION}")
    if row["source"] != "final_ltm_traffic_map":
        errors.append("source must be final_ltm_traffic_map")
    if row["method"] != "lacam_star_ltm":
        errors.append("method must be lacam_star_ltm")
    if row["objective"] != "sum_of_loss":
        errors.append("objective must be sum_of_loss")

    for key in (
        "agents",
        "seed",
        "from_id",
        "to_id",
        "from_index",
        "to_index",
        "from_x",
        "from_y",
        "to_x",
        "to_y",
        "from_degree",
        "to_degree",
        "map_vertices",
    ):
        if int(row[key]) < 0:
            errors.append(f"{key} must be nonnegative")

    for key in (
        "time_limit_sec",
        "ltm_raw_count",
        "ltm_normalized_weight",
        "warm_start_target_weight",
        "residual_reference_weight",
        "residual_delta_target",
        "traversal_cost",
    ):
        _finite_number(row, key, errors)

    for key in ("ltm_normalized_weight", "warm_start_target_weight", "residual_reference_weight"):
        value = float(row[key])
        if value < 0.0 or value > 10.0:
            errors.append(f"{key} must be within [0, 10]")

    if float(row["ltm_raw_count"]) < 0.0:
        errors.append("ltm_raw_count must be nonnegative")
    if bool(row["nonzero"]) != (float(row["ltm_raw_count"]) > 0.0):
        errors.append("nonzero must match ltm_raw_count > 0")
    if not math.isclose(float(row["traversal_cost"]), 1.0 + float(row["ltm_normalized_weight"]), rel_tol=1e-9):
        errors.append("traversal_cost must equal 1 + ltm_normalized_weight")

    return errors


def validate_manifest_row(row: dict) -> list[str]:
    """Return validation errors for one Phase3 teacher manifest row."""

    errors = _type_errors(row, MANIFEST_REQUIRED_TYPES)
    if errors:
        return errors

    if row["schema_version"] != MANIFEST_SCHEMA_VERSION:
        errors.append(f"schema_version must be {MANIFEST_SCHEMA_VERSION}")
    if row["split"] not in VALID_SPLITS:
        errors.append("split must be train, validation, or test")
    if row["primary_supervision"] != PRIMARY_SUPERVISION:
        errors.append(f"primary_supervision must be {PRIMARY_SUPERVISION}")
    if row["warm_start_target"] != "ltm_normalized_edge_weight":
        errors.append("warm_start_target must be ltm_normalized_edge_weight")
    if row["edge_label_schema_version"] != EDGE_LABEL_SCHEMA_VERSION:
        errors.append(f"edge_label_schema_version must be {EDGE_LABEL_SCHEMA_VERSION}")
    if row["trace_schema_version"] != TRACE_SCHEMA_VERSION:
        errors.append(f"trace_schema_version must be {TRACE_SCHEMA_VERSION}")
    if row["method"] != "lacam_star_ltm":
        errors.append("method must be lacam_star_ltm")
    if row["objective"] != "sum_of_loss":
        errors.append("objective must be sum_of_loss")
    if row["label_rows"] <= 0:
        errors.append("label_rows must be positive")
    if len(row["label_sha256"]) != 64:
        errors.append("label_sha256 must be a hex SHA256 digest")

    return errors


def run_id_for(
    *,
    map_name: str,
    scen: str,
    agents: int,
    seed: int,
    time_limit_sec: float,
    source_manifest: str,
) -> str:
    """Build a stable compact run id for teacher-label files."""

    payload = {
        "agents": int(agents),
        "map": map_name,
        "scen": scen,
        "seed": int(seed),
        "source_manifest": source_manifest.replace("\\", "/"),
        "time_limit_sec": float(time_limit_sec),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    return f"{map_name}__a{int(agents)}__s{int(seed)}__{digest}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_jsonl_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())

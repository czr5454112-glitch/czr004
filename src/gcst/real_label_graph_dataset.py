"""Real Label-v5.1 graph/OD/C0/F0 dataset helpers for G5.62."""

from __future__ import annotations

import csv
import hashlib
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .graph_data import GraphData, build_graph
from .scenario_features import _sha
from .theta_schema import BASELINE_G556, THETA_NUMERIC_COLUMNS
from .traffic_prior import compute_traffic_prior


ROOT = Path(__file__).resolve().parents[2]
G560_TRAINING_ROWS = Path("outputs/tables/phase5p5_repair5g560_labelv51_training_rows.csv")
DEFAULT_CONTEXT_DIR = Path("outputs/external/phase5p5_repair5g562_g559_remote_contexts")


@dataclass(frozen=True)
class RealLabelGroup:
    evaluation_uid: str
    instance_uid: str
    split: str
    map: str
    map_family: str
    agent_count: int
    seed: int
    budget_ms: int
    horizon_id: str
    scenario_path: Path
    scenario_sha256_expected: str
    physical_map_sha256_expected: str
    rows: list[dict[str, str]]


@dataclass(frozen=True)
class RealGraphExample:
    group: RealLabelGroup
    graph: GraphData
    assignment: dict[str, Any]
    traffic: dict[str, Any]
    safe_count: int
    safe_improving_count: int
    harmful_count: int
    censored_count: int
    best_positive_delta: float | None
    target_theta: np.ndarray | None


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def read_rows(path: str | Path, limit: int | None = None) -> list[dict[str, str]]:
    p = resolve(path)
    if not p.exists():
        return []
    out = []
    with p.open(newline="", encoding="utf-8") as handle:
        for idx, row in enumerate(csv.DictReader(handle)):
            out.append(dict(row))
            if limit is not None and idx + 1 >= limit:
                break
    return out


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def number(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    return out if math.isfinite(out) else default


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with resolve(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def local_scenario_path(remote_path: str, context_dir: str | Path = DEFAULT_CONTEXT_DIR) -> Path:
    return resolve(context_dir) / "scenarios" / Path(remote_path).name


def parse_movingai_scenario(path: str | Path, agent_count: int | None = None) -> dict[str, Any]:
    p = resolve(path)
    starts: list[tuple[int, int]] = []
    goals: list[tuple[int, int]] = []
    optimal_lengths: list[float] = []
    map_name = ""
    width = height = 0
    with p.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.lower().startswith("version"):
                continue
            parts = line.split()
            if len(parts) < 9:
                continue
            map_name = parts[1]
            width = int(float(parts[2]))
            height = int(float(parts[3]))
            starts.append((int(float(parts[4])), int(float(parts[5]))))
            goals.append((int(float(parts[6])), int(float(parts[7]))))
            optimal_lengths.append(float(parts[8]))
            if agent_count is not None and len(starts) >= agent_count:
                break
    distances = [abs(s[0] - g[0]) + abs(s[1] - g[1]) for s, g in zip(starts, goals)]
    od = []
    for s, g, dist in zip(starts, goals, distances):
        od.append(
            [
                s[0] / max(1, width - 1),
                s[1] / max(1, height - 1),
                g[0] / max(1, width - 1),
                g[1] / max(1, height - 1),
                dist / max(1, width + height),
                float(s[0] < g[0]) - float(s[0] > g[0]),
            ]
        )
    return {
        "scenario_path": str(p),
        "scenario_sha256": sha256_file(p),
        "map_file": map_name,
        "width": width,
        "height": height,
        "requested_agent_count": int(agent_count or len(starts)),
        "encoded_agent_count": len(starts),
        "represented_agent_mass": len(starts),
        "all_agent_mass_preserved": agent_count is None or len(starts) == int(agent_count),
        "assignment_capacity_limited": agent_count is not None and len(starts) < int(agent_count),
        "unique_start_count": len(set(starts)),
        "unique_goal_count": len(set(goals)),
        "assignment_valid": len(set(starts)) == len(starts) and len(set(goals)) == len(goals),
        "starts": starts,
        "goals": goals,
        "start_positions_sha256": _sha([*starts]),
        "goal_positions_sha256": _sha([*goals]),
        "start_goal_assignment_hash": _sha([*(f"{s}->{g}" for s, g in zip(starts, goals))]),
        "shortest_path_distance_mean": float(np.mean(distances)) if distances else 0.0,
        "shortest_path_distance_max": int(max(distances)) if distances else 0,
        "movingai_optimal_length_mean": float(np.mean(optimal_lengths)) if optimal_lengths else 0.0,
        "od_tokens": np.asarray(od, dtype=np.float32),
    }


def _seed_from_context(row: dict[str, str]) -> int:
    legacy = str(row.get("legacy_context_key", ""))
    parts = legacy.split("|")
    if len(parts) >= 3:
        return int(number(parts[2], 0))
    return int(number(row.get("legacy_solver_seed"), 0))


def load_label_groups(
    rows_path: str | Path = G560_TRAINING_ROWS,
    context_dir: str | Path = DEFAULT_CONTEXT_DIR,
    max_contexts: int = 0,
) -> list[RealLabelGroup]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_rows(rows_path):
        if row.get("g560_evaluation_uid"):
            grouped[row["g560_evaluation_uid"]].append(row)
    groups: list[RealLabelGroup] = []
    for evaluation_uid, rows in sorted(grouped.items()):
        first = rows[0]
        scenario = local_scenario_path(first.get("solver_scenario_path", ""), context_dir)
        if not scenario.exists():
            continue
        groups.append(
            RealLabelGroup(
                evaluation_uid=evaluation_uid,
                instance_uid=first.get("g560_instance_uid", ""),
                split=first.get("split", "unassigned"),
                map=first.get("map", ""),
                map_family=first.get("map_family", ""),
                agent_count=int(number(first.get("agent_count"), 0)),
                seed=_seed_from_context(first),
                budget_ms=int(number(first.get("nominal_budget_ms"), 0)),
                horizon_id=first.get("horizon_id", ""),
                scenario_path=scenario,
                scenario_sha256_expected=first.get("g560_solver_scenario_sha256", ""),
                physical_map_sha256_expected=first.get("g560_physical_map_sha256", ""),
                rows=rows,
            )
        )
        if max_contexts and len(groups) >= max_contexts:
            break
    return groups


def theta_from_row(row: dict[str, str]) -> np.ndarray:
    return np.asarray([number(row.get(col), float(BASELINE_G556[idx])) for idx, col in enumerate(THETA_NUMERIC_COLUMNS)], dtype=np.float32)


def row_is_safe(row: dict[str, str]) -> bool:
    return boolish(row.get("labelv51_development_safe"))


def row_is_positive(row: dict[str, str]) -> bool:
    return row_is_safe(row) and (
        boolish(row.get("labelv51_success_gain"))
        or (boolish(row.get("labelv51_comparable_quality")) and number(row.get("quality_delta_vs_g556"), 0.0) < 0.0)
    )


def row_is_harmful(row: dict[str, str]) -> bool:
    return boolish(row.get("labelv51_success_regression")) or (
        boolish(row.get("labelv51_comparable_quality")) and number(row.get("quality_delta_vs_g556"), 0.0) > 0.0
    )


def row_is_censored(row: dict[str, str]) -> bool:
    return not boolish(row.get("labelv51_comparable_quality")) and not boolish(row.get("labelv51_success_regression"))


def positive_target(rows: Iterable[dict[str, str]]) -> tuple[np.ndarray | None, float | None]:
    positives = [row for row in rows if row_is_positive(row)]
    if not positives:
        return None, None
    positives.sort(key=lambda row: number(row.get("quality_delta_vs_g556"), 0.0))
    weights = np.asarray([max(0.05, min(4.0, 1.0 - number(row.get("quality_delta_vs_g556"), 0.0))) for row in positives], dtype=np.float32)
    theta = np.stack([theta_from_row(row) for row in positives]).astype(np.float32)
    target = np.average(theta, axis=0, weights=weights)
    return target.astype(np.float32), number(positives[0].get("quality_delta_vs_g556"), 0.0)


def wait_pressure_from_paths(paths: list[list[int]], node_count: int) -> dict[str, float]:
    counts = np.zeros((node_count,), dtype=np.float32)
    for path in paths:
        for node in path:
            if 0 <= int(node) < node_count:
                counts[int(node)] += 1.0
    if not counts.size or counts.sum() <= 0:
        return {"vertex_wait_pressure_max": 0.0, "vertex_wait_pressure_mean": 0.0, "vertex_wait_pressure_nonzero_rate": 0.0}
    normalized = counts / max(float(counts.max()), 1.0)
    return {
        "vertex_wait_pressure_max": float(normalized.max()),
        "vertex_wait_pressure_mean": float(normalized.mean()),
        "vertex_wait_pressure_nonzero_rate": float((normalized > 0).mean()),
    }


def build_example(group: RealLabelGroup) -> RealGraphExample:
    assignment = parse_movingai_scenario(group.scenario_path, group.agent_count)
    graph = build_graph({"map": group.map, "width": assignment["width"], "height": assignment["height"]})
    traffic = compute_traffic_prior(graph, assignment)
    target, best_delta = positive_target(group.rows)
    safe_count = sum(row_is_safe(row) for row in group.rows)
    pos_count = sum(row_is_positive(row) for row in group.rows)
    harmful_count = sum(row_is_harmful(row) for row in group.rows)
    censored_count = sum(row_is_censored(row) for row in group.rows)
    return RealGraphExample(
        group=group,
        graph=graph,
        assignment=assignment,
        traffic=traffic,
        safe_count=safe_count,
        safe_improving_count=pos_count,
        harmful_count=harmful_count,
        censored_count=censored_count,
        best_positive_delta=best_delta,
        target_theta=target,
    )


def split_counts(groups: Iterable[RealLabelGroup]) -> dict[str, int]:
    return dict(Counter(group.split for group in groups))

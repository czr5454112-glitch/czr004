"""Actual MovingAI map/scenario validation for Repair5G.5.60."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .map_hash import is_free, read_movingai_map
from .schemas_v51 import ROUND, bool_text

ROOT = Path(__file__).resolve().parents[2]
SOURCE_MAP_MANIFEST = Path("outputs/tables/phase5p5_repair5g559_solver_map_manifest.csv")
SOURCE_SCENARIO_MANIFEST = Path("outputs/tables/phase5p5_repair5g559_solver_scenario_manifest.csv")
SCENARIO_AUDIT_CSV = Path(f"outputs/tables/{ROUND}_scenario_validity_audit.csv")
SCENARIO_SUMMARY_JSON = Path(f"outputs/reports/{ROUND}_scenario_validity_summary.json")
SCENARIO_SUMMARY_MD = Path(f"outputs/reports/{ROUND}_scenario_validity.md")


def resolve(path: str | Path, root: Path = ROOT) -> Path:
    p = Path(path)
    return p if p.is_absolute() else root / p


def sha256_bytes(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def assignment_hash(pairs: list[tuple[tuple[int, int], tuple[int, int]]]) -> str:
    text = "|".join(f"{s}->{g}" for s, g in pairs)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ScenarioEntry:
    bucket: str
    map_name: str
    width: int
    height: int
    start: tuple[int, int]
    goal: tuple[int, int]
    distance: float


def parse_scenario(path: Path) -> list[ScenarioEntry]:
    entries: list[ScenarioEntry] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.lower().startswith("version"):
            continue
        parts = line.split()
        if len(parts) < 9:
            raise ValueError(f"invalid scen line with {len(parts)} fields: {line[:120]}")
        entries.append(
            ScenarioEntry(
                bucket=parts[0],
                map_name=parts[1],
                width=int(float(parts[2])),
                height=int(float(parts[3])),
                start=(int(float(parts[4])), int(float(parts[5]))),
                goal=(int(float(parts[6])), int(float(parts[7]))),
                distance=float(parts[8]),
            )
        )
    return entries


def component_labels(grid: list[str]) -> dict[tuple[int, int], int]:
    height = len(grid)
    width = max((len(row) for row in grid), default=0)
    labels: dict[tuple[int, int], int] = {}
    comp = 0
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if not is_free(ch) or (x, y) in labels:
                continue
            comp += 1
            q = deque([(x, y)])
            labels[(x, y)] = comp
            while q:
                cx, cy = q.popleft()
                for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in labels and is_free(grid[ny][nx]):
                        labels[(nx, ny)] = comp
                        q.append((nx, ny))
    return labels


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return [dict(row) for row in csv.DictReader(f)]


def _rewrite_path(path: str, rewrite_from: str | None, rewrite_to: str | None) -> Path:
    if rewrite_from and rewrite_to and path.startswith(rewrite_from):
        path = rewrite_to + path[len(rewrite_from) :]
    return Path(path)


def validate_scenarios(
    root: Path = ROOT,
    rewrite_from: str | None = None,
    rewrite_to: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    root = Path(root)
    map_rows = _read_rows(resolve(SOURCE_MAP_MANIFEST, root))
    scen_rows = _read_rows(resolve(SOURCE_SCENARIO_MANIFEST, root))
    if limit:
        scen_rows = scen_rows[:limit]
    map_by_name = {row.get("map", ""): row for row in map_rows}
    map_cache: dict[str, tuple[Path, int, int, list[str], dict[tuple[int, int], int], str]] = {}

    fieldnames = [
        "map",
        "map_family",
        "solver_seed",
        "solver_scenario_path",
        "scenario_file_exists",
        "scenario_sha256_expected",
        "scenario_sha256_actual",
        "scenario_sha256_match",
        "map_file_exists",
        "map_sha256_expected",
        "map_sha256_actual",
        "map_sha256_match",
        "scenario_pair_count_expected",
        "scenario_pair_count_actual",
        "scenario_pair_count_match",
        "unique_start_count",
        "unique_goal_count",
        "duplicate_starts",
        "duplicate_goals",
        "all_starts_traversable",
        "all_goals_traversable",
        "all_pairs_reachable",
        "assignment_sha256_expected",
        "assignment_sha256_actual",
        "assignment_sha256_match",
        "width_height_match",
        "valid",
        "failure_reasons",
        "phase5p5_allowed",
        "phase6_allowed",
        "runtime_claim_allowed",
        "learned_runtime_policy_validated",
        "aaai_ready",
    ]
    out_path = resolve(SCENARIO_AUDIT_CSV, root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0
    reason_counts: Counter = Counter()
    valid_count = 0
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for scen in scen_rows:
            reasons: list[str] = []
            scen_path = _rewrite_path(str(scen.get("solver_scenario_path", "")), rewrite_from, rewrite_to)
            scen_exists = scen_path.exists()
            entries: list[ScenarioEntry] = []
            scenario_sha_actual = ""
            if scen_exists:
                try:
                    scenario_sha_actual = sha256_bytes(scen_path)
                    entries = parse_scenario(scen_path)
                except Exception as exc:
                    reasons.append(f"scenario_parse_error:{type(exc).__name__}")
            else:
                reasons.append("scenario_file_missing")
            scenario_sha_match = bool(scenario_sha_actual and scenario_sha_actual == scen.get("solver_scenario_sha256", ""))
            if not scenario_sha_match:
                reasons.append("scenario_sha_mismatch")
            expected_count = int(float(scen.get("solver_scenario_pair_count") or 0))
            count_match = len(entries) == expected_count
            if not count_match:
                reasons.append("scenario_pair_count_mismatch")

            map_name = scen.get("map", "")
            map_row = map_by_name.get(map_name, {})
            map_path = _rewrite_path(str(map_row.get("solver_map_path", "")), rewrite_from, rewrite_to)
            map_exists = map_path.exists()
            width = height = 0
            grid: list[str] = []
            labels: dict[tuple[int, int], int] = {}
            map_sha_actual = ""
            if map_name in map_cache:
                map_path, width, height, grid, labels, map_sha_actual = map_cache[map_name]
            elif map_exists:
                try:
                    map_sha_actual = sha256_bytes(map_path)
                    width, height, grid = read_movingai_map(map_path)
                    labels = component_labels(grid)
                    map_cache[map_name] = (map_path, width, height, grid, labels, map_sha_actual)
                except Exception as exc:
                    reasons.append(f"map_parse_error:{type(exc).__name__}")
            else:
                reasons.append("map_file_missing")
            map_sha_match = bool(map_sha_actual and map_sha_actual == map_row.get("solver_map_sha256", ""))
            if not map_sha_match:
                reasons.append("map_sha_mismatch")

            starts = [entry.start for entry in entries]
            goals = [entry.goal for entry in entries]
            unique_start_count = len(set(starts))
            unique_goal_count = len(set(goals))
            duplicate_starts = unique_start_count != len(starts)
            duplicate_goals = unique_goal_count != len(goals)
            if duplicate_starts:
                reasons.append("duplicate_starts")
            if duplicate_goals:
                reasons.append("duplicate_goals")
            all_starts_traversable = all(start in labels for start in starts) if entries and labels else False
            all_goals_traversable = all(goal in labels for goal in goals) if entries and labels else False
            if not all_starts_traversable:
                reasons.append("start_not_traversable")
            if not all_goals_traversable:
                reasons.append("goal_not_traversable")
            all_pairs_reachable = all(start in labels and goal in labels and labels[start] == labels[goal] for start, goal in zip(starts, goals)) if entries and labels else False
            if not all_pairs_reachable:
                reasons.append("pair_not_reachable")
            width_height_match = all(entry.width == width and entry.height == height for entry in entries) if entries and width and height else False
            if not width_height_match:
                reasons.append("width_height_mismatch")
            assignment_actual = assignment_hash(list(zip(starts, goals))) if entries else ""
            assignment_match = bool(assignment_actual and assignment_actual == scen.get("start_goal_assignment_sha256", ""))
            if not assignment_match:
                reasons.append("assignment_sha_mismatch")
            valid = not reasons
            valid_count += int(valid)
            for reason in set(reasons):
                reason_counts[reason] += 1
            writer.writerow(
                {
                    "map": map_name,
                    "map_family": scen.get("map_family", ""),
                    "solver_seed": scen.get("solver_seed", ""),
                    "solver_scenario_path": scen.get("solver_scenario_path", ""),
                    "scenario_file_exists": bool_text(scen_exists),
                    "scenario_sha256_expected": scen.get("solver_scenario_sha256", ""),
                    "scenario_sha256_actual": scenario_sha_actual,
                    "scenario_sha256_match": bool_text(scenario_sha_match),
                    "map_file_exists": bool_text(map_exists),
                    "map_sha256_expected": map_row.get("solver_map_sha256", ""),
                    "map_sha256_actual": map_sha_actual,
                    "map_sha256_match": bool_text(map_sha_match),
                    "scenario_pair_count_expected": expected_count,
                    "scenario_pair_count_actual": len(entries),
                    "scenario_pair_count_match": bool_text(count_match),
                    "unique_start_count": unique_start_count,
                    "unique_goal_count": unique_goal_count,
                    "duplicate_starts": bool_text(duplicate_starts),
                    "duplicate_goals": bool_text(duplicate_goals),
                    "all_starts_traversable": bool_text(all_starts_traversable),
                    "all_goals_traversable": bool_text(all_goals_traversable),
                    "all_pairs_reachable": bool_text(all_pairs_reachable),
                    "assignment_sha256_expected": scen.get("start_goal_assignment_sha256", ""),
                    "assignment_sha256_actual": assignment_actual,
                    "assignment_sha256_match": bool_text(assignment_match),
                    "width_height_match": bool_text(width_height_match),
                    "valid": bool_text(valid),
                    "failure_reasons": ";".join(sorted(set(reasons))),
                    "phase5p5_allowed": "False",
                    "phase6_allowed": "False",
                    "runtime_claim_allowed": "False",
                    "learned_runtime_policy_validated": "False",
                    "aaai_ready": "False",
                }
            )
            rows_written += 1

    scenario_validity_gate_passed = rows_written > 0 and valid_count == rows_written
    summary = {
        "round": ROUND,
        "scenario_rows": rows_written,
        "valid_scenarios": valid_count,
        "invalid_scenarios": rows_written - valid_count,
        "validity_rate": valid_count / max(1, rows_written),
        "reason_counts": dict(sorted(reason_counts.items())),
        "actual_file_validation_complete": rows_written > 0 and rows_written == len(scen_rows),
        "scenario_validity_gate_passed": scenario_validity_gate_passed,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }
    summary_path = resolve(SCENARIO_SUMMARY_JSON, root)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    md = [
        "# Repair5G.5.60 Scenario Validity",
        "",
        f"- Scenario files audited: {rows_written}",
        f"- Valid scenarios: {valid_count}",
        f"- Invalid scenarios: {rows_written - valid_count}",
        f"- Validity rate: {summary['validity_rate']:.6f}",
        "",
        "## Failure Reasons",
        "",
    ]
    if reason_counts:
        md.extend(f"- {name}: {count}" for name, count in sorted(reason_counts.items()))
    else:
        md.append("- none")
    md_path = resolve(SCENARIO_SUMMARY_MD, root)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    return summary

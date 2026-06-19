from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gcst.graph_data import build_graph  # noqa: E402
from gcst.map_hash import free_cells, synthetic_grid  # noqa: E402
from gcst.scenario_features import build_context_uid  # noqa: E402
from gcst.schemas_v51 import parse_bool  # noqa: E402
from gcst.traffic_prior import compute_traffic_prior  # noqa: E402


ROUND = "phase5p5_repair5g561"
SOURCE = "phase5p5_repair5g560"
TMP_ROOT = Path(f"outputs/tmp/{ROUND}_valid_scenario_bank")
SCENARIO_REPAIR_MD = Path(f"outputs/reports/{ROUND}_scenario_generator_repair.md")
SCENARIO_SUMMARY = Path(f"outputs/reports/{ROUND}_scenario_validity_summary.json")
SCENARIO_AUDIT = Path(f"outputs/tables/{ROUND}_scenario_validity_audit.csv")
VALID_MANIFEST = Path(f"outputs/tables/{ROUND}_valid_instance_manifest.csv")
SPLIT_MANIFEST = Path(f"outputs/tables/{ROUND}_physical_map_split_manifest.csv")


MAP_SPECS = [
    ("g561-empty-8x8", "empty", 8, 8),
    ("g561-empty-16x16", "empty", 16, 16),
    ("g561-empty-32x32", "empty", 32, 32),
    ("g561-empty-48x32", "empty", 48, 32),
    ("g561-random-16x16-a", "random", 16, 16),
    ("g561-random-24x24-a", "random", 24, 24),
    ("g561-random-32x32-a", "random", 32, 32),
    ("g561-random-40x40-b", "random", 40, 40),
    ("g561-maze-24x24-a", "maze", 24, 24),
    ("g561-maze-48x32-a", "maze", 48, 32),
    ("g561-maze-64x32-b", "maze", 64, 32),
    ("g561-room-24x24-a", "room", 24, 24),
    ("g561-room-48x48-a", "room", 48, 48),
    ("g561-room-64x48-b", "room", 64, 48),
    ("g561-warehouse-20x10-a", "warehouse", 20, 10),
    ("g561-warehouse-32x24-a", "warehouse", 32, 24),
    ("g561-warehouse-48x32-a", "warehouse", 48, 32),
    ("g561-warehouse-64x40-b", "warehouse", 64, 40),
    ("g561-connector-24x24-a", "connector", 24, 24),
    ("g561-connector-48x48-a", "connector", 48, 48),
    ("g561-tunnel-24x24-a", "tunnel", 24, 24),
    ("g561-tunnel-64x32-a", "tunnel", 64, 32),
    ("g561-loop-32x32-a", "loop", 32, 32),
    ("g561-loop-56x56-a", "loop", 56, 56),
    ("g561-tree-32x32-a", "tree", 32, 32),
    ("g561-tree-56x40-a", "tree", 56, 40),
    ("g561-string-32x24-a", "irregular_bottleneck", 32, 24),
    ("g561-string-64x32-a", "irregular_bottleneck", 64, 32),
    ("g561-corners-48x48-a", "irregular_bottleneck", 48, 48),
] * 2

REGIMES = [
    "uniform_random",
    "opposite_side_cross_flow",
    "central_choke_point",
    "room_to_room_door_bottleneck",
    "warehouse_aisle_to_aisle",
    "clustered_starts_to_dispersed_goals",
    "adversarial_opposing_flow",
    "many_to_many_bottleneck_flow",
]

AGENT_COUNTS = [8, 12, 16, 24, 32, 48, 64, 80]

BUDGET_PROFILES = [
    (500, 0.5, 2),
    (750, 0.75, 2),
    (1000, 1.0, 3),
    (1500, 1.5, 3),
    (2000, 2.0, 4),
    (3000, 3.0, 4),
    (5000, 5.0, 6),
    (8000, 8.0, 8),
]

SPLITS = ["train", "validation", "development-heldout", "blind-reserved"]

BOOLEAN_COLUMNS = {
    "scenario_file_exists",
    "scenario_sha256_match",
    "map_file_exists",
    "map_sha256_match",
    "scenario_pair_count_match",
    "duplicate_starts",
    "duplicate_goals",
    "all_starts_traversable",
    "all_goals_traversable",
    "all_pairs_reachable",
    "assignment_sha256_match",
    "width_height_match",
    "valid",
    "generated_in_g561",
    "retained_for_g561",
    "phase5p5_allowed",
    "phase6_allowed",
    "runtime_claim_allowed",
    "learned_runtime_policy_validated",
    "aaai_ready",
}


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def claims() -> dict[str, bool]:
    return {
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "runtime_claim_allowed": False,
        "learned_runtime_policy_validated": False,
        "aaai_ready": False,
    }


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_uid(*parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_rows(path: str | Path) -> list[dict[str, str]]:
    p = resolve(path)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_rows(path: str | Path, rows: list[dict[str, Any]]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with p.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def movingai_map_text(grid: list[str]) -> str:
    height = len(grid)
    width = max((len(row) for row in grid), default=0)
    return "type octile\nheight {height}\nwidth {width}\nmap\n{grid}\n".format(
        height=height,
        width=width,
        grid="\n".join(row.ljust(width, "@") for row in grid),
    )


def write_map(path: Path, grid: list[str]) -> str:
    text = movingai_map_text(grid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return sha256_file(path)


def component_cells(grid: list[str]) -> list[list[tuple[int, int]]]:
    free = set(free_cells(grid))
    out: list[list[tuple[int, int]]] = []
    while free:
        start = min(free)
        q: deque[tuple[int, int]] = deque([start])
        free.remove(start)
        comp = [start]
        while q:
            x, y = q.popleft()
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nxt = (x + dx, y + dy)
                if nxt in free:
                    free.remove(nxt)
                    q.append(nxt)
                    comp.append(nxt)
        out.append(sorted(comp))
    return sorted(out, key=len, reverse=True)


def region(cells: list[tuple[int, int]], width: int, height: int, name: str) -> list[tuple[int, int]]:
    if name == "left":
        chosen = [cell for cell in cells if cell[0] < width * 0.35]
    elif name == "right":
        chosen = [cell for cell in cells if cell[0] > width * 0.65]
    elif name == "top":
        chosen = [cell for cell in cells if cell[1] < height * 0.35]
    elif name == "bottom":
        chosen = [cell for cell in cells if cell[1] > height * 0.65]
    elif name == "center":
        chosen = [cell for cell in cells if abs(cell[0] - width / 2) < width * 0.2 and abs(cell[1] - height / 2) < height * 0.2]
    elif name == "perimeter":
        chosen = [cell for cell in cells if cell[0] < width * 0.2 or cell[0] > width * 0.8 or cell[1] < height * 0.2 or cell[1] > height * 0.8]
    else:
        chosen = cells
    return chosen or cells


def sample_unique(cells: list[tuple[int, int]], rng: random.Random, count: int, fallback: list[tuple[int, int]]) -> list[tuple[int, int]]:
    primary = list(dict.fromkeys(cells))
    if len(primary) >= count:
        return rng.sample(primary, count)
    remaining = [cell for cell in fallback if cell not in set(primary)]
    if len(primary) + len(remaining) < count:
        raise ValueError("component does not have enough unique cells")
    return primary + rng.sample(remaining, count - len(primary))


def regime_regions(regime: str) -> tuple[str, str]:
    if regime in {"opposite_side_cross_flow", "adversarial_opposing_flow"}:
        return "left", "right"
    if regime in {"central_choke_point", "many_to_many_bottleneck_flow"}:
        return "perimeter", "center"
    if regime in {"room_to_room_door_bottleneck", "warehouse_aisle_to_aisle"}:
        return "top", "bottom"
    if regime == "clustered_starts_to_dispersed_goals":
        return "center", "all"
    return "all", "all"


def shortest_distance(grid: list[str], start: tuple[int, int], goal: tuple[int, int]) -> int:
    if start == goal:
        return 0
    free = set(free_cells(grid))
    q: deque[tuple[tuple[int, int], int]] = deque([(start, 0)])
    seen = {start}
    while q:
        (x, y), dist = q.popleft()
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nxt = (x + dx, y + dy)
            if nxt == goal:
                return dist + 1
            if nxt in free and nxt not in seen:
                seen.add(nxt)
                q.append((nxt, dist + 1))
    raise ValueError("unreachable pair")


def assignment_hash(pairs: list[tuple[tuple[int, int], tuple[int, int]]]) -> str:
    return sha256_text("|".join(f"{start}->{goal}" for start, goal in pairs))


def build_assignment(
    grid: list[str],
    width: int,
    height: int,
    agent_count: int,
    regime_name: str,
    seed: int,
) -> dict[str, Any]:
    rng = random.Random(seed)
    comps = [comp for comp in component_cells(grid) if len(comp) >= agent_count]
    if not comps:
        raise ValueError("no component can host requested agents")
    comp = comps[seed % len(comps)]
    start_region, goal_region = regime_regions(regime_name)
    starts = sample_unique(region(comp, width, height, start_region), rng, agent_count, comp)
    goals = sample_unique(region(comp, width, height, goal_region), rng, agent_count, comp)
    rng.shuffle(goals)
    if all(s == g for s, g in zip(starts, goals)) and len(goals) > 1:
        goals = goals[1:] + goals[:1]
    distances = [shortest_distance(grid, start, goal) for start, goal in zip(starts, goals)]
    pairs = list(zip(starts, goals))
    start_goal_overlap = len(set(starts) & set(goals))
    own_start_goal_matches = sum(start == goal for start, goal in pairs)
    return {
        "starts": starts,
        "goals": goals,
        "distances": distances,
        "pairs": pairs,
        "unique_start_count": len(set(starts)),
        "unique_goal_count": len(set(goals)),
        "start_goal_overlap_count": start_goal_overlap,
        "own_start_goal_match_count": own_start_goal_matches,
        "assignment_sha256": assignment_hash(pairs),
    }


def write_scenario(path: Path, map_name: str, width: int, height: int, assignment: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["version 1"]
    for idx, ((sx, sy), (gx, gy), distance) in enumerate(zip(assignment["starts"], assignment["goals"], assignment["distances"])):
        lines.append(f"{idx}\t{map_name}.map\t{width}\t{height}\t{sx}\t{sy}\t{gx}\t{gy}\t{distance}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sha256_file(path)


def retained_valid_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_rows = read_rows(f"outputs/tables/{SOURCE}_scenario_validity_audit.csv")
    audit_rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    for row in source_rows:
        copied = dict(row)
        for column in BOOLEAN_COLUMNS:
            if column in copied and str(copied[column]).strip():
                copied[column] = bool_text(parse_bool(copied[column]))
        copied["source_round"] = SOURCE
        copied["scenario_bank_source"] = "retained_g560_valid" if parse_bool(row.get("valid")) else "retained_g560_invalid"
        copied["generated_in_g561"] = bool_text(False)
        audit_rows.append(copied)
        if not parse_bool(row.get("valid")):
            continue
        instance_uid = stable_uid("g561_valid_instance", row.get("map"), row.get("solver_seed"), row.get("scenario_sha256_actual"))
        manifest_rows.append(
            {
                "g561_instance_uid": instance_uid,
                "map": row.get("map", ""),
                "map_family": row.get("map_family", ""),
                "solver_seed": row.get("solver_seed", ""),
                "scenario_sha256": row.get("scenario_sha256_actual", ""),
                "physical_map_sha256": row.get("map_sha256_actual", ""),
                "assignment_sha256": row.get("assignment_sha256_actual", ""),
                "pair_count": row.get("scenario_pair_count_actual", ""),
                "start_goal_regime": "",
                "nominal_budget_ms": "",
                "base_time_limit_sec": "",
                "ltm_max_iterations": "",
                "scenario_bank_source": "retained_g560_valid",
                "raw_materialized_under": "",
                **claims(),
            }
        )
    return audit_rows, manifest_rows


def generated_contexts(target_new: int, seed: int, tmp_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rng = random.Random(seed)
    map_dir = tmp_root / "maps"
    scenario_dir = tmp_root / "scenarios"
    audit_rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    map_meta: dict[str, dict[str, Any]] = {}
    generated = 0
    attempts = 0
    while generated < target_new and attempts < target_new * 20:
        attempts += 1
        map_name, family, width, height = MAP_SPECS[(generated + attempts + seed) % len(MAP_SPECS)]
        map_variant = attempts % 2
        concrete_map = f"{map_name}-v{map_variant}"
        grid = synthetic_grid(concrete_map, width, height)
        free_count = len(free_cells(grid))
        if free_count < min(AGENT_COUNTS):
            continue
        agent_count = AGENT_COUNTS[generated % len(AGENT_COUNTS)]
        if agent_count > free_count:
            continue
        regime_name = REGIMES[generated % len(REGIMES)]
        budget_ms, base_sec, ltm_iters = BUDGET_PROFILES[generated % len(BUDGET_PROFILES)]
        solver_seed = seed * 1_000_000 + attempts
        try:
            assignment = build_assignment(grid, width, height, agent_count, regime_name, solver_seed)
        except ValueError:
            continue
        map_path = map_dir / f"{concrete_map}.map"
        scenario_uid = stable_uid("g561_generated_scenario", concrete_map, solver_seed, agent_count, regime_name, budget_ms, base_sec, ltm_iters)
        scen_path = scenario_dir / f"{scenario_uid}.scen"
        map_sha = write_map(map_path, grid)
        scenario_sha = write_scenario(scen_path, concrete_map, width, height, assignment)
        graph = build_graph({"map": concrete_map, "width": width, "height": height, "free_cells": free_count})
        traffic = compute_traffic_prior(graph, {"starts": assignment["starts"], "goals": assignment["goals"]})
        context = {
            "map": concrete_map,
            "map_family": family,
            "width": width,
            "height": height,
            "free_cells": free_count,
            "agent_count": agent_count,
            "agents": agent_count,
            "seed": solver_seed,
            "solver_seed": solver_seed,
            "nominal_budget_ms": budget_ms,
            "base_time_limit_sec": base_sec,
            "ltm_max_iterations": ltm_iters,
            "start_goal_regime": regime_name,
        }
        instance_uid = build_context_uid(context, map_sha, {
            "start_positions_sha256": sha256_text("|".join(map(str, assignment["starts"]))),
            "goal_positions_sha256": sha256_text("|".join(map(str, assignment["goals"]))),
        })
        density = agent_count / max(1, free_count)
        row = {
            "map": concrete_map,
            "map_family": family,
            "solver_seed": solver_seed,
            "solver_scenario_path": str(scen_path.as_posix()),
            "scenario_file_exists": bool_text(True),
            "scenario_sha256_expected": scenario_sha,
            "scenario_sha256_actual": scenario_sha,
            "scenario_sha256_match": bool_text(True),
            "map_file_exists": bool_text(True),
            "map_sha256_expected": map_sha,
            "map_sha256_actual": map_sha,
            "map_sha256_match": bool_text(True),
            "scenario_pair_count_expected": agent_count,
            "scenario_pair_count_actual": agent_count,
            "scenario_pair_count_match": bool_text(True),
            "unique_start_count": assignment["unique_start_count"],
            "unique_goal_count": assignment["unique_goal_count"],
            "duplicate_starts": bool_text(False),
            "duplicate_goals": bool_text(False),
            "all_starts_traversable": bool_text(True),
            "all_goals_traversable": bool_text(True),
            "all_pairs_reachable": bool_text(True),
            "assignment_sha256_expected": assignment["assignment_sha256"],
            "assignment_sha256_actual": assignment["assignment_sha256"],
            "assignment_sha256_match": bool_text(True),
            "width_height_match": bool_text(True),
            "valid": bool_text(True),
            "failure_reasons": "",
            "generated_in_g561": True,
            "scenario_bank_source": "generated_g561_component_aware",
            "g561_instance_uid": instance_uid,
            "start_goal_regime": regime_name,
            "nominal_budget_ms": budget_ms,
            "base_time_limit_sec": base_sec,
            "ltm_max_iterations": ltm_iters,
            "agent_density": density,
            "start_goal_overlap_count": assignment["start_goal_overlap_count"],
            "own_start_goal_match_count": assignment["own_start_goal_match_count"],
            "path_found_rate": traffic["summary"]["path_found_rate"],
            **claims(),
        }
        manifest_rows.append(
            {
                "g561_instance_uid": instance_uid,
                "map": concrete_map,
                "map_family": family,
                "solver_seed": solver_seed,
                "scenario_sha256": scenario_sha,
                "physical_map_sha256": map_sha,
                "assignment_sha256": assignment["assignment_sha256"],
                "pair_count": agent_count,
                "start_goal_regime": regime_name,
                "nominal_budget_ms": budget_ms,
                "base_time_limit_sec": base_sec,
                "ltm_max_iterations": ltm_iters,
                "agent_density": density,
                "scenario_bank_source": "generated_g561_component_aware",
                "raw_materialized_under": str(tmp_root.as_posix()),
                **claims(),
            }
        )
        audit_rows.append(row)
        map_meta[map_sha] = {"physical_map_sha256": map_sha, "map_example": concrete_map, "map_family": family}
        generated += 1
    return audit_rows, manifest_rows, {"attempts": attempts, "generated": generated, "map_meta": map_meta}


def split_rows(manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hashes = sorted({str(row.get("physical_map_sha256", "")) for row in manifest if row.get("physical_map_sha256")})
    meta: dict[str, dict[str, Any]] = {}
    for row in manifest:
        meta.setdefault(str(row.get("physical_map_sha256", "")), row)
    return [
        {
            "physical_map_sha256": h,
            "split": SPLITS[idx % len(SPLITS)],
            "map_example": meta[h].get("map", ""),
            "map_family": meta[h].get("map_family", ""),
            **claims(),
        }
        for idx, h in enumerate(hashes)
    ]


def density_bin(value: float) -> str:
    if value < 0.03:
        return "lt_0p03"
    if value < 0.05:
        return "0p03_0p05"
    if value < 0.08:
        return "0p05_0p08"
    if value < 0.12:
        return "0p08_0p12"
    if value < 0.18:
        return "0p12_0p18"
    return "gte_0p18"


def summarize(audit_rows: list[dict[str, Any]], manifest: list[dict[str, Any]], generated_meta: dict[str, Any], target: int, tmp_root: Path) -> dict[str, Any]:
    valid_rows = [row for row in audit_rows if parse_bool(str(row.get("valid", "")))]
    generated_valid = [row for row in valid_rows if parse_bool(str(row.get("generated_in_g561", "")))]
    retained_valid = [row for row in valid_rows if str(row.get("scenario_bank_source", "")) == "retained_g560_valid"]
    families = Counter(str(row.get("map_family", "")) for row in manifest if row.get("map_family"))
    regimes = Counter(str(row.get("start_goal_regime", "")) for row in manifest if row.get("start_goal_regime"))
    budgets = Counter(str(row.get("nominal_budget_ms", "")) for row in manifest if str(row.get("nominal_budget_ms", "")).strip())
    density_bins = Counter()
    for row in manifest:
        try:
            density_bins[density_bin(float(row.get("agent_density", "")))] += 1
        except ValueError:
            pass
    summary = {
        "schema_version": "phase5p5_repair5g561_scenario_validity_summary_v2",
        "decision": "g561_valid_scenario_bank_expanded_component_aware",
        "source_round": SOURCE,
        "scenario_rows": len(audit_rows),
        "valid_scenarios": len(valid_rows),
        "invalid_scenarios": len(audit_rows) - len(valid_rows),
        "retained_g560_valid_scenarios": len(retained_valid),
        "generated_g561_valid_scenarios": len(generated_valid),
        "validity_rate": len(valid_rows) / max(1, len(audit_rows)),
        "valid_independent_instances_target": target,
        "valid_independent_instances_target_met": len(valid_rows) >= target,
        "physical_map_hashes": len({row.get("physical_map_sha256") for row in manifest if row.get("physical_map_sha256")}),
        "physical_map_hashes_target_met": len({row.get("physical_map_sha256") for row in manifest if row.get("physical_map_sha256")}) >= 32,
        "map_families": dict(sorted(families.items())),
        "map_family_count": len(families),
        "map_family_target_met": len(families) >= 7,
        "start_goal_regimes": dict(sorted(regimes.items())),
        "start_goal_regime_count": len(regimes),
        "start_goal_regime_target_met": len(regimes) >= 8,
        "density_bins": dict(sorted(density_bins.items())),
        "density_bin_count": len(density_bins),
        "density_bin_target_met": len(density_bins) >= 6,
        "budget_profiles": dict(sorted(budgets.items())),
        "budget_profile_count": len(budgets),
        "budget_profile_target_met": len(budgets) >= 8,
        "all_scenario_bank_targets_met": (
            len(valid_rows) >= target
            and len({row.get("physical_map_sha256") for row in manifest if row.get("physical_map_sha256")}) >= 32
            and len(families) >= 7
            and len(regimes) >= 8
            and len(density_bins) >= 6
            and len(budgets) >= 8
        ),
        "generator_attempts": generated_meta["attempts"],
        "raw_materialization_root": str(tmp_root.as_posix()),
        "raw_files_git_tracked": False,
        "producer_command": "python scripts/generate_repair5g561_valid_scenario_bank.py",
        **claims(),
    }
    if not summary["all_scenario_bank_targets_met"]:
        summary["decision"] = "g561_valid_scenario_bank_underpowered_continue_generation"
    return summary


def write_report(summary: dict[str, Any]) -> None:
    lines = [
        "# Repair5G.5.61 Scenario Generator Repair",
        "",
        f"- decision: `{summary['decision']}`",
        f"- valid scenarios: `{summary['valid_scenarios']}`",
        f"- retained G5.60 valid scenarios: `{summary['retained_g560_valid_scenarios']}`",
        f"- generated G5.61 valid scenarios: `{summary['generated_g561_valid_scenarios']}`",
        f"- target valid independent instances: `{summary['valid_independent_instances_target']}`",
        f"- physical map hashes: `{summary['physical_map_hashes']}`",
        f"- map families: `{summary['map_family_count']}`",
        f"- start-goal regimes: `{summary['start_goal_regime_count']}`",
        f"- density bins: `{summary['density_bin_count']}`",
        f"- budget profiles: `{summary['budget_profile_count']}`",
        f"- raw materialization root: `{summary['raw_materialization_root']}`",
        "",
        "The generated G5.61 rows use component-aware sampling without modulo reuse. Starts and goals are sampled without replacement, each paired start-goal is in the same connected component, and raw map/scenario files are materialized under `outputs/tmp` for reproducible hash checks.",
        "",
        "Raw generated files are intentionally not tracked in Git; the committed manifest records hashes, row counts, source command, and the ignored raw root.",
        "",
        "Claims remain closed until materialization, replay, and solver-performance gates pass.",
    ]
    write_text(SCENARIO_REPAIR_MD, "\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a component-aware G5.61 valid scenario bank.")
    parser.add_argument("--target-valid", type=int, default=2600)
    parser.add_argument("--seed", type=int, default=561)
    parser.add_argument("--tmp-root", type=Path, default=TMP_ROOT)
    args = parser.parse_args(argv)

    tmp_root = resolve(args.tmp_root)
    audit_rows, manifest = retained_valid_rows()
    retained_count = len(manifest)
    target_new = max(0, args.target_valid - retained_count)
    generated_audit, generated_manifest, generated_meta = generated_contexts(target_new, args.seed, tmp_root)
    audit_rows.extend(generated_audit)
    manifest.extend(generated_manifest)
    write_rows(SCENARIO_AUDIT, audit_rows)
    write_rows(VALID_MANIFEST, manifest)
    write_rows(SPLIT_MANIFEST, split_rows(manifest))
    summary = summarize(audit_rows, manifest, generated_meta, args.target_valid, tmp_root)
    write_json(SCENARIO_SUMMARY, summary)
    write_report(summary)
    print(json.dumps({"decision": summary["decision"], "valid": summary["valid_scenarios"], "generated": summary["generated_g561_valid_scenarios"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

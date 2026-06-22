from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
ROUND = "phase5p5_repair5g567"
OUTPUT_ROOT = Path(os.environ.get("G567_OUTPUT_ROOT", "outputs"))
TABLES = OUTPUT_ROOT / "tables"
REPORTS = OUTPUT_ROOT / "reports"
DEFAULT_BENCHMARK_ROOT = Path(os.environ.get("G567_BENCHMARK_ROOT", ROOT / "external" / "benchmarks"))

PUBLIC_INGESTION_MD = REPORTS / f"{ROUND}_public_benchmark_ingestion.md"
PUBLIC_INGESTION_SUMMARY = REPORTS / f"{ROUND}_public_benchmark_ingestion_summary.json"
PUBLIC_MAP_REGISTRY = TABLES / f"{ROUND}_public_map_registry.csv"
PUBLIC_SCENARIO_REGISTRY = TABLES / f"{ROUND}_public_scenario_registry.csv"
PARENT_MAP_SPLIT_AUDIT = TABLES / f"{ROUND}_parent_map_split_audit.csv"

MOVINGAI_ARCHIVES = {
    "mapf-map": "https://movingai.com/benchmarks/mapf/mapf-map.zip",
    "mapf-scen-random": "https://movingai.com/benchmarks/mapf/mapf-scen-random.zip",
    "mapf-scen-even": "https://movingai.com/benchmarks/mapf/mapf-scen-even.zip",
}
GIT_SOURCES = {
    "mapf_lns2": {
        "url": "https://github.com/Jiaoyang-Li/MAPF-LNS2",
        "branch": "init-LNS",
        "path": "mapf_lns2",
        "required": True,
        "source_category": "mapf_lns2_experiment5_high_agent",
    },
    "ggo_public": {
        "url": "https://github.com/lunjohnzhang/ggo_public",
        "branch": "",
        "path": "ggo_public",
        "required": True,
        "source_category": "ggo_alignment_reference",
    },
    "lorr_benchmark_archive": {
        "url": "https://github.com/MAPF-Competition/Benchmark-Archive",
        "branch": "",
        "path": "lorr_benchmark_archive",
        "required": True,
        "source_category": "lorr_ood_reference",
    },
    "sillm_icra2025": {
        "url": "https://github.com/DiligentPanda/Scalable-Imitation-Learning-for-LMAPF",
        "branch": "static_guidance",
        "path": "sillm_icra2025",
        "required": False,
        "source_category": "sillm_large_map_reference",
    },
}

MOVINGAI_PANEL_M_MAPS = [
    "empty-16-16",
    "empty-32-32",
    "empty-48-48",
    "random-32-32-10",
    "random-32-32-20",
    "random-64-64-10",
    "random-64-64-20",
    "maze-32-32-2",
    "maze-32-32-4",
    "maze-128-128-1",
    "maze-128-128-2",
    "maze-128-128-10",
    "room-32-32-4",
    "room-64-64-8",
    "room-64-64-16",
    "warehouse-10-20-10-2-1",
    "warehouse-10-20-10-2-2",
    "warehouse-20-40-10-2-1",
    "warehouse-20-40-10-2-2",
    "den312d",
    "den520d",
    "ost003d",
    "lak303d",
    "brc202d",
    "Berlin_1_256",
    "Boston_0_256",
    "Paris_1_256",
    "ht_chantry",
    "ht_mansion_n",
    "lt_gallowstemplar_n",
    "w_woundedcoast",
    "orz900d",
]
HIGH_AGENT_TIERS = [1000, 1500, 2000, 2500, 3000]
GGO_ALIGNMENT_PANEL = [
    ("random-32-32-20", 400),
    ("warehouse-33x36", 400),
    ("room-64-64-8", 1500),
    ("maze-32-32-4", 400),
    ("empty-48-48", 1000),
    ("random-64-64-20", 1500),
    ("den312d", 1200),
]
MOVINGAI_STANDARD_TIERS = [8, 12, 16, 24, 32, 48, 64, 80, 128, 192, 256, 384, 512, 768, 1000, 1500, 2000, 2500, 3000]


@dataclass(frozen=True)
class MapInfo:
    path: Path
    map_name: str
    width: int
    height: int
    grid: list[str]
    physical_map_sha256: str
    free_cells: int


@dataclass(frozen=True)
class ScenarioRow:
    bucket: str
    map_name: str
    width: int
    height: int
    start_x: int
    start_y: int
    goal_x: int
    goal_y: int
    optimal_length: str


_COMPONENT_CACHE: dict[str, dict[tuple[int, int], int]] = {}
_SCENARIO_CACHE: dict[str, list[ScenarioRow]] = {}


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def rel(path: str | Path) -> str:
    p = resolve(path)
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def source_rel(path: str | Path, source_root: str | Path) -> str:
    p = resolve(path)
    root = resolve(source_root)
    try:
        return str(p.relative_to(root)).replace("\\", "/")
    except ValueError:
        return rel(p)


def sha256_file(path: str | Path) -> str:
    p = resolve(path)
    if not p.exists() or not p.is_file():
        return ""
    digest = hashlib.sha256()
    with p.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


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


def read_rows(path: str | Path) -> list[dict[str, str]]:
    p = resolve(path)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def source_license_status(root: Path, default: str) -> str:
    for name in ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "README.md", "README.txt"]:
        path = root / name
        if path.exists() and path.is_file():
            digest = sha256_file(path)
            return f"metadata_only_raw_not_committed; license_file={rel(path)}; license_sha256={digest}"
    return default


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False)


def ensure_git_source(key: str, cfg: dict[str, Any], bench_root: Path, *, no_download: bool, refresh_git: bool) -> dict[str, Any]:
    target = bench_root / str(cfg["path"])
    if not no_download:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not (target / ".git").exists():
            clone_args = ["clone", "--depth", "1"]
            branch = str(cfg.get("branch") or "")
            if branch:
                clone_args.extend(["--branch", branch])
            if key == "sillm_icra2025":
                clone_args.append("--recursive")
            clone_args.extend([str(cfg["url"]), str(target)])
            completed = run_git(clone_args, ROOT)
            if completed.returncode != 0:
                return {
                    "source_key": key,
                    "source_url": cfg["url"],
                    "source_status": "clone_failed",
                    "source_error": completed.stderr.strip()[-1000:],
                    "source_required": bool(cfg.get("required")),
                }
        elif refresh_git:
            fetch_args = ["fetch", "--depth", "1", "origin"]
            branch = str(cfg.get("branch") or "")
            if branch:
                fetch_args.append(branch)
            fetch = run_git(fetch_args, target)
            if fetch.returncode == 0 and branch:
                run_git(["checkout", "FETCH_HEAD"], target)
    if not (target / ".git").exists():
        return {
            "source_key": key,
            "source_url": cfg["url"],
            "source_status": "missing",
            "source_required": bool(cfg.get("required")),
            "local_source_path": rel(target),
        }
    commit = run_git(["rev-parse", "HEAD"], target).stdout.strip()
    return {
        "source_key": key,
        "source_url": cfg["url"],
        "source_status": "available",
        "source_required": bool(cfg.get("required")),
        "git_commit": commit,
        "git_branch_requested": cfg.get("branch", ""),
        "local_source_path": rel(target),
        "license_and_redistribution_status": source_license_status(
            target,
            "metadata_only_raw_not_committed; no_top_level_license_file_detected",
        ),
    }


def download_file(url: str, dest: Path, *, no_download: bool) -> dict[str, Any]:
    if not no_download:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            with urllib.request.urlopen(url, timeout=120) as response, dest.open("wb") as handle:
                shutil.copyfileobj(response, handle)
    digest = sha256_file(dest)
    return {
        "source_url": url,
        "local_archive_path": rel(dest),
        "archive_sha256": digest,
        "source_status": "available" if digest else "missing",
        "license_and_redistribution_status": "MovingAI public MAPF benchmark archive; metadata committed only; raw archive not committed",
    }


def extract_zip(archive: Path, extract_dir: Path, *, no_download: bool) -> bool:
    if no_download or not archive.exists():
        return False
    marker = extract_dir / ".extracted.sha256"
    digest = sha256_file(archive)
    if marker.exists() and marker.read_text(encoding="utf-8").strip() == digest:
        return True
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(extract_dir)
    marker.write_text(digest + "\n", encoding="utf-8")
    return True


def read_movingai_map(path: str | Path) -> MapInfo:
    p = resolve(path)
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    width = height = 0
    map_index = -1
    for idx, line in enumerate(lines):
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0].lower() == "height":
            height = int(parts[1])
        elif len(parts) >= 2 and parts[0].lower() == "width":
            width = int(parts[1])
        elif parts and parts[0].lower() == "map":
            map_index = idx + 1
            break
    if width <= 0 or height <= 0 or map_index < 0:
        raise ValueError(f"{p}: invalid MovingAI map header")
    grid = [line.rstrip("\n") for line in lines[map_index : map_index + height]]
    if len(grid) != height or any(len(row) != width for row in grid):
        raise ValueError(f"{p}: invalid MovingAI map body")
    free_count = sum(1 for row in grid for ch in row if is_free_char(ch))
    return MapInfo(p, p.stem, width, height, grid, sha256_file(p), free_count)


def is_free_char(ch: str) -> bool:
    return ch not in {"@", "T", "O", "W"}


def parse_movingai_scenario(path: str | Path) -> list[ScenarioRow]:
    p = resolve(path)
    cache_key = str(p)
    if cache_key in _SCENARIO_CACHE:
        return _SCENARIO_CACHE[cache_key]
    rows: list[ScenarioRow] = []
    if not p.exists():
        return rows
    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.lower().startswith("version"):
            continue
        parts = line.split()
        if len(parts) < 9:
            continue
        rows.append(
            ScenarioRow(
                bucket=parts[0],
                map_name=Path(parts[1]).stem,
                width=int(float(parts[2])),
                height=int(float(parts[3])),
                start_x=int(float(parts[4])),
                start_y=int(float(parts[5])),
                goal_x=int(float(parts[6])),
                goal_y=int(float(parts[7])),
                optimal_length=parts[8],
            )
        )
    _SCENARIO_CACHE[cache_key] = rows
    return rows


def connected_components(info: MapInfo) -> dict[tuple[int, int], int]:
    if info.physical_map_sha256 in _COMPONENT_CACHE:
        return _COMPONENT_CACHE[info.physical_map_sha256]
    comp: dict[tuple[int, int], int] = {}
    component_id = 0
    for y, row in enumerate(info.grid):
        for x, ch in enumerate(row):
            if not is_free_char(ch) or (x, y) in comp:
                continue
            component_id += 1
            queue: deque[tuple[int, int]] = deque([(x, y)])
            comp[(x, y)] = component_id
            while queue:
                cx, cy = queue.popleft()
                for nx, ny in [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)]:
                    if nx < 0 or ny < 0 or nx >= info.width or ny >= info.height:
                        continue
                    if (nx, ny) in comp or not is_free_char(info.grid[ny][nx]):
                        continue
                    comp[(nx, ny)] = component_id
                    queue.append((nx, ny))
    _COMPONENT_CACHE[info.physical_map_sha256] = comp
    return comp


def validate_scenario_prefix(info: MapInfo, scenario_path: Path, requested_agents: int) -> dict[str, Any]:
    rows = parse_movingai_scenario(scenario_path)
    prefix = rows[:requested_agents]
    failures: list[str] = []
    if len(rows) < requested_agents:
        failures.append("scenario_row_count_insufficient_for_requested_tier")
    starts = [(row.start_x, row.start_y) for row in prefix]
    goals = [(row.goal_x, row.goal_y) for row in prefix]
    if len(starts) != len(set(starts)):
        failures.append("duplicate_starts_in_prefix")
    if len(goals) != len(set(goals)):
        failures.append("duplicate_goals_in_prefix")
    comp = connected_components(info)
    unreachable = 0
    blocked_endpoint = 0
    dimension_mismatch = 0
    for row in prefix:
        if row.width != info.width or row.height != info.height:
            dimension_mismatch += 1
        start = (row.start_x, row.start_y)
        goal = (row.goal_x, row.goal_y)
        if start not in comp or goal not in comp:
            blocked_endpoint += 1
        elif comp[start] != comp[goal]:
            unreachable += 1
    if dimension_mismatch:
        failures.append("scenario_map_dimension_mismatch")
    if blocked_endpoint:
        failures.append("scenario_endpoint_blocked_or_out_of_bounds")
    if unreachable:
        failures.append("od_unreachable_in_prefix")
    return {
        "scenario_rows_available": len(rows),
        "requested_agent_tier": requested_agents,
        "prefix_rows_validated": len(prefix),
        "duplicate_start_count": len(starts) - len(set(starts)),
        "duplicate_goal_count": len(goals) - len(set(goals)),
        "dimension_mismatch_count": dimension_mismatch,
        "blocked_endpoint_count": blocked_endpoint,
        "od_unreachable_count": unreachable,
        "validation_result": "pass" if not failures else "fail",
        "validation_failures": ";".join(failures),
    }


def find_first(root: Path, filename: str) -> Path | None:
    if not root.exists():
        return None
    matches = sorted(root.rglob(filename))
    return matches[0] if matches else None


def find_ggo_reference_artifact(root: Path, map_name: str) -> Path | None:
    if not root.exists():
        return None
    tokens = [map_name, map_name.replace("-", "_")]
    for token in tokens:
        matches = sorted(root.rglob(f"*{token}*.json"))
        if matches:
            return matches[0]
    if map_name == "warehouse-33x36":
        matches = sorted(root.rglob("*warehouse_33x36*.json"))
        if matches:
            return matches[0]
    return None


def movingai_family(map_name: str) -> str:
    if map_name.startswith("empty"):
        return "empty"
    if map_name.startswith("random"):
        return "random"
    if map_name.startswith("maze"):
        return "maze"
    if map_name.startswith("room"):
        return "room"
    if map_name.startswith("warehouse"):
        return "warehouse"
    if map_name in {"Berlin_1_256", "Boston_0_256", "Paris_1_256"}:
        return "city"
    if map_name.startswith(("den", "ost", "lak", "brc", "ht_", "lt_", "w_", "orz")):
        return "game"
    return "public_other"


def map_registry_row(
    info: MapInfo,
    *,
    source_key: str,
    source_url: str,
    source_provenance: str,
    source_category: str,
    panel: str,
    original_relative_path: str,
    license_status: str,
    scientific_split: str = "split_later_by_parent_map_hash",
    validation_result: str = "pass",
    validation_failures: str = "",
    use_in_g567: bool = True,
) -> dict[str, Any]:
    return {
        "source_key": source_key,
        "source_url": source_url,
        "source_provenance": source_provenance,
        "license_and_redistribution_status": license_status,
        "original_relative_path": original_relative_path,
        "local_map_path": rel(info.path),
        "map_name": info.map_name,
        "map_family": movingai_family(info.map_name),
        "map_scenario_format": "movingai_map",
        "parent_physical_map_sha256": info.physical_map_sha256,
        "physical_map_sha256": info.physical_map_sha256,
        "width": info.width,
        "height": info.height,
        "free_cells": info.free_cells,
        "source_category": source_category,
        "map_source_type": "canonical_public_benchmark_map",
        "panel": panel,
        "official_scenario": "",
        "czr004_derived_scenario": "",
        "scientific_split": scientific_split,
        "agent_count_capacity": info.free_cells,
        "validation_result": validation_result,
        "validation_failures": validation_failures,
        "use_in_g567": use_in_g567,
    }


def scenario_registry_row(
    *,
    scenario_path: Path,
    info: MapInfo,
    requested_agents: int,
    source_key: str,
    source_url: str,
    source_provenance: str,
    source_category: str,
    panel: str,
    scenario_source_type: str,
    official_scenario: bool,
    czr004_derived_scenario: bool,
    scenario_prefix_family: str,
    license_status: str,
    original_relative_path: str | None = None,
) -> dict[str, Any]:
    validation = validate_scenario_prefix(info, scenario_path, requested_agents)
    return {
        "source_key": source_key,
        "source_url": source_url,
        "source_provenance": source_provenance,
        "license_and_redistribution_status": license_status,
        "original_relative_path": original_relative_path or rel(scenario_path),
        "local_scenario_path": rel(scenario_path),
        "map_name": info.map_name,
        "local_map_path": rel(info.path),
        "parent_physical_map_sha256": info.physical_map_sha256,
        "physical_map_sha256": info.physical_map_sha256,
        "scenario_sha256": sha256_file(scenario_path),
        "map_scenario_format": "movingai_scen",
        "source_category": source_category,
        "scenario_source_type": scenario_source_type,
        "panel": panel,
        "official_scenario": official_scenario,
        "czr004_derived_scenario": czr004_derived_scenario,
        "scenario_prefix_family": scenario_prefix_family,
        "scientific_split": "split_later_by_parent_map_hash",
        "agent_count_capacity": validation["scenario_rows_available"],
        **validation,
    }


def build_parent_split_audit(map_rows: list[dict[str, Any]], scenario_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in [*map_rows, *scenario_rows]:
        digest = str(row.get("parent_physical_map_sha256", ""))
        if digest:
            grouped.setdefault(digest, []).append(row)
    audit_rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for digest, rows in sorted(grouped.items()):
        splits = sorted({str(row.get("scientific_split", "")) for row in rows if str(row.get("scientific_split", ""))})
        official_values = sorted({str(row.get("official_scenario", "")) for row in rows if str(row.get("official_scenario", ""))})
        derived_values = sorted({str(row.get("czr004_derived_scenario", "")) for row in rows if str(row.get("czr004_derived_scenario", ""))})
        crosses = len([split for split in splits if split not in {"", "split_later_by_parent_map_hash"}]) > 1
        indistinguishable = "True" in official_values and "True" in derived_values and not any(str(row.get("scenario_source_type", "")) for row in rows)
        if crosses:
            failures.append(f"{digest}:parent_map_crosses_scientific_splits")
        if indistinguishable:
            failures.append(f"{digest}:official_and_derived_scenarios_indistinguishable")
        audit_rows.append(
            {
                "parent_physical_map_sha256": digest,
                "map_examples": ";".join(sorted({str(row.get("map_name", "")) for row in rows if row.get("map_name")}))[:500],
                "source_categories": ";".join(sorted({str(row.get("source_category", "")) for row in rows if row.get("source_category")})),
                "panels": ";".join(sorted({str(row.get("panel", "")) for row in rows if row.get("panel")})),
                "scientific_splits_observed": ";".join(splits),
                "parent_map_crosses_scientific_splits": crosses,
                "official_scenario_values": ";".join(official_values),
                "derived_scenario_values": ";".join(derived_values),
                "official_and_derived_scenarios_distinguishable": not indistinguishable,
                "rows_for_parent": len(rows),
                "validation_result": "fail" if crosses or indistinguishable else "pass",
            }
        )
    return audit_rows, failures


def ingest_public_benchmarks(
    *,
    benchmark_root: Path,
    no_download: bool = False,
    refresh_git: bool = False,
    include_optional_sillm: bool = True,
) -> dict[str, Any]:
    benchmark_root = resolve(benchmark_root)
    movingai_root = benchmark_root / "movingai_mapf"
    archive_dir = movingai_root / "archives"
    extract_root = movingai_root / "extracted"
    source_rows: list[dict[str, Any]] = []
    source_errors: list[str] = []
    for key, url in MOVINGAI_ARCHIVES.items():
        archive = archive_dir / f"{key}.zip"
        row = download_file(url, archive, no_download=no_download)
        row["source_key"] = key
        row["source_required"] = True
        row["source_provenance"] = row.get("archive_sha256", "")
        source_rows.append(row)
        if row["source_status"] != "available":
            source_errors.append(f"{key}:archive_missing_or_hash_unavailable")
        extract_zip(archive, extract_root / key, no_download=no_download)
    for key, cfg in GIT_SOURCES.items():
        if key == "sillm_icra2025" and not include_optional_sillm:
            continue
        row = ensure_git_source(key, cfg, benchmark_root, no_download=no_download, refresh_git=refresh_git)
        row["source_provenance"] = row.get("git_commit", "")
        source_rows.append(row)
        if row.get("source_required") and row.get("source_status") != "available":
            source_errors.append(f"{key}:git_source_missing_or_commit_unavailable")

    source_by_key = {str(row["source_key"]): row for row in source_rows}
    map_rows: list[dict[str, Any]] = []
    scenario_rows: list[dict[str, Any]] = []
    map_infos: dict[str, MapInfo] = {}

    map_extract = extract_root / "mapf-map"
    random_extract = extract_root / "mapf-scen-random"
    even_extract = extract_root / "mapf-scen-even"
    movingai_source = source_by_key.get("mapf-map", {})
    movingai_license = str(movingai_source.get("license_and_redistribution_status", "metadata_only_raw_not_committed"))
    for map_name in MOVINGAI_PANEL_M_MAPS:
        path = find_first(map_extract, f"{map_name}.map")
        if path is None:
            map_rows.append(
                {
                    "source_key": "mapf-map",
                    "source_url": MOVINGAI_ARCHIVES["mapf-map"],
                    "source_provenance": movingai_source.get("archive_sha256", ""),
                    "license_and_redistribution_status": movingai_license,
                    "original_relative_path": f"{map_name}.map",
                    "map_name": map_name,
                    "map_family": movingai_family(map_name),
                    "map_scenario_format": "movingai_map",
                    "source_category": "movingai_canonical",
                    "map_source_type": "canonical_public_benchmark_map",
                    "panel": "M",
                    "scientific_split": "split_later_by_parent_map_hash",
                    "validation_result": "fail",
                    "validation_failures": "required_movingai_map_missing",
                    "use_in_g567": False,
                }
            )
            continue
        try:
            info = read_movingai_map(path)
            map_infos[map_name] = info
            map_rows.append(
                map_registry_row(
                    info,
                    source_key="mapf-map",
                    source_url=MOVINGAI_ARCHIVES["mapf-map"],
                    source_provenance=str(movingai_source.get("archive_sha256", "")),
                    source_category="movingai_canonical",
                    panel="M",
                    original_relative_path=source_rel(path, map_extract),
                    license_status=movingai_license,
                )
            )
        except Exception as exc:
            map_rows.append(
                {
                    "source_key": "mapf-map",
                    "source_url": MOVINGAI_ARCHIVES["mapf-map"],
                    "source_provenance": movingai_source.get("archive_sha256", ""),
                    "license_and_redistribution_status": movingai_license,
                    "original_relative_path": rel(path),
                    "map_name": map_name,
                    "source_category": "movingai_canonical",
                    "panel": "M",
                    "validation_result": "fail",
                    "validation_failures": f"movingai_map_parse_failed:{exc}",
                    "use_in_g567": False,
                }
            )

    for map_name, info in sorted(map_infos.items()):
        max_standard_tier = min(max(MOVINGAI_STANDARD_TIERS), info.free_cells)
        for kind, root, source_key in [
            ("random", random_extract, "mapf-scen-random"),
            ("even", even_extract, "mapf-scen-even"),
        ]:
            scenario_path = find_first(root, f"{map_name}-{kind}-1.scen")
            if scenario_path is None:
                scenario_rows.append(
                    {
                        "source_key": source_key,
                        "source_url": MOVINGAI_ARCHIVES[source_key],
                        "source_provenance": source_by_key.get(source_key, {}).get("archive_sha256", ""),
                        "license_and_redistribution_status": str(source_by_key.get(source_key, {}).get("license_and_redistribution_status", "")),
                        "original_relative_path": f"{map_name}-{kind}-1.scen",
                        "map_name": map_name,
                        "local_map_path": rel(info.path),
                        "parent_physical_map_sha256": info.physical_map_sha256,
                        "physical_map_sha256": info.physical_map_sha256,
                        "map_scenario_format": "movingai_scen",
                        "source_category": "movingai_canonical",
                        "scenario_source_type": f"movingai_official_{kind}",
                        "panel": "M",
                        "official_scenario": True,
                        "czr004_derived_scenario": False,
                        "scenario_prefix_family": f"{map_name}-{kind}-missing",
                        "scientific_split": "split_later_by_parent_map_hash",
                        "requested_agent_tier": max(requested_tiers),
                        "validation_result": "fail",
                        "validation_failures": "required_movingai_scenario_missing",
                    }
                )
                continue
            scenario_capacity = len(parse_movingai_scenario(scenario_path))
            requested_tiers = sorted({tier for tier in MOVINGAI_STANDARD_TIERS if tier <= min(max_standard_tier, scenario_capacity)})
            if not requested_tiers and scenario_capacity > 0:
                requested_tiers = [min(info.free_cells, scenario_capacity)]
            for tier in requested_tiers:
                scenario_rows.append(
                    scenario_registry_row(
                        scenario_path=scenario_path,
                        info=info,
                        requested_agents=tier,
                        source_key=source_key,
                        source_url=MOVINGAI_ARCHIVES[source_key],
                        source_provenance=str(source_by_key.get(source_key, {}).get("archive_sha256", "")),
                        source_category="movingai_canonical",
                        panel="M",
                        scenario_source_type=f"movingai_official_{kind}",
                        official_scenario=True,
                        czr004_derived_scenario=False,
                        scenario_prefix_family=f"{map_name}-{kind}-1",
                        license_status=str(source_by_key.get(source_key, {}).get("license_and_redistribution_status", "")),
                        original_relative_path=source_rel(scenario_path, root),
                    )
                )

    if "orz900d" in map_infos:
        info = map_infos["orz900d"]
        for idx in range(1, 26):
            scenario_path = find_first(even_extract, f"orz900d-even-{idx}.scen")
            if scenario_path is None:
                scenario_rows.append(
                    {
                        "source_key": "mapf-scen-even",
                        "source_url": MOVINGAI_ARCHIVES["mapf-scen-even"],
                        "source_provenance": source_by_key.get("mapf-scen-even", {}).get("archive_sha256", ""),
                        "map_name": "orz900d",
                        "parent_physical_map_sha256": info.physical_map_sha256,
                        "scenario_prefix_family": f"orz900d-even-{idx}",
                        "panel": "H",
                        "source_category": "movingai_high_agent_orz900d",
                        "official_scenario": True,
                        "czr004_derived_scenario": False,
                        "validation_result": "fail",
                        "validation_failures": "required_orz900d_even_scenario_missing",
                    }
                )
                continue
            for tier in HIGH_AGENT_TIERS:
                scenario_rows.append(
                    scenario_registry_row(
                        scenario_path=scenario_path,
                        info=info,
                        requested_agents=tier,
                        source_key="mapf-scen-even",
                        source_url=MOVINGAI_ARCHIVES["mapf-scen-even"],
                        source_provenance=str(source_by_key.get("mapf-scen-even", {}).get("archive_sha256", "")),
                        source_category="movingai_high_agent_orz900d",
                        panel="H",
                        scenario_source_type="movingai_official_even_high_agent_prefix",
                        official_scenario=True,
                        czr004_derived_scenario=False,
                        scenario_prefix_family=f"orz900d-even-{idx}",
                        license_status=str(source_by_key.get("mapf-scen-even", {}).get("license_and_redistribution_status", "")),
                        original_relative_path=source_rel(scenario_path, even_extract),
                    )
                )

    lns2_row = source_by_key.get("mapf_lns2", {})
    lns2_root = benchmark_root / "mapf_lns2"
    warehouse_info = map_infos.get("warehouse-20-40-10-2-2")
    if warehouse_info is not None:
        for scenario_path in sorted((lns2_root / "instances").glob("warehouse-20-40-10-2-2-10000agents-*.scen")):
            for tier in HIGH_AGENT_TIERS:
                scenario_rows.append(
                    scenario_registry_row(
                        scenario_path=scenario_path,
                        info=warehouse_info,
                        requested_agents=tier,
                        source_key="mapf_lns2",
                        source_url=str(GIT_SOURCES["mapf_lns2"]["url"]),
                        source_provenance=str(lns2_row.get("git_commit", "")),
                        source_category="mapf_lns2_experiment5_high_agent",
                        panel="H",
                        scenario_source_type="mapf_lns2_official_10000_agent_prefix",
                        official_scenario=True,
                        czr004_derived_scenario=False,
                        scenario_prefix_family=Path(scenario_path).stem,
                        license_status=str(lns2_row.get("license_and_redistribution_status", "")),
                        original_relative_path=source_rel(scenario_path, lns2_root),
                    )
                )
        if not any(row.get("source_category") == "mapf_lns2_experiment5_high_agent" for row in scenario_rows):
            scenario_rows.append(
                {
                    "source_key": "mapf_lns2",
                    "source_url": str(GIT_SOURCES["mapf_lns2"]["url"]),
                    "source_provenance": str(lns2_row.get("git_commit", "")),
                    "map_name": "warehouse-20-40-10-2-2",
                    "parent_physical_map_sha256": warehouse_info.physical_map_sha256,
                    "panel": "H",
                    "source_category": "mapf_lns2_experiment5_high_agent",
                    "official_scenario": True,
                    "czr004_derived_scenario": False,
                    "scenario_prefix_family": "warehouse-20-40-10-2-2-10000agents",
                    "requested_agent_tier": 3000,
                    "validation_result": "fail",
                    "validation_failures": "required_mapf_lns2_10000_agent_scenarios_missing",
                }
            )

    for map_name, tier in GGO_ALIGNMENT_PANEL:
        info = map_infos.get(map_name)
        if info is None:
            ggo_source = source_by_key.get("ggo_public", {})
            ggo_root = resolve(ggo_source.get("local_source_path", benchmark_root / str(GIT_SOURCES["ggo_public"]["path"])))
            reference = find_ggo_reference_artifact(ggo_root, map_name)
            reference_sha = sha256_file(reference) if reference else ""
            map_rows.append(
                {
                    "source_key": "ggo_public",
                    "source_url": str(GIT_SOURCES["ggo_public"]["url"]),
                    "source_provenance": ggo_source.get("git_commit", ""),
                    "license_and_redistribution_status": ggo_source.get("license_and_redistribution_status", ""),
                    "original_relative_path": source_rel(reference, ggo_root) if reference else f"ggo_alignment_panel:{map_name}/{tier}",
                    "local_map_path": "",
                    "map_name": map_name,
                    "parent_physical_map_sha256": reference_sha,
                    "physical_map_sha256": reference_sha,
                    "map_scenario_format": "ggo_json_guidance_reference",
                    "source_category": "ggo_alignment_reference",
                    "map_source_type": "ggo_alignment_reference_not_direct_movingai_instance",
                    "panel": "G",
                    "official_scenario": False,
                    "czr004_derived_scenario": True,
                    "scientific_split": "split_later_by_parent_map_hash",
                    "agent_count_capacity": tier,
                    "validation_result": "pass" if reference_sha else "fail",
                    "validation_failures": "" if reference_sha else "ggo_panel_parent_map_not_resolved_to_reference_artifact",
                    "use_in_g567": False,
                }
            )
            if reference_sha:
                scenario_rows.append(
                    {
                        "source_key": "ggo_public",
                        "source_url": str(GIT_SOURCES["ggo_public"]["url"]),
                        "source_provenance": ggo_source.get("git_commit", ""),
                        "license_and_redistribution_status": ggo_source.get("license_and_redistribution_status", ""),
                        "original_relative_path": source_rel(reference, ggo_root),
                        "local_scenario_path": "",
                        "map_name": map_name,
                        "local_map_path": "",
                        "parent_physical_map_sha256": reference_sha,
                        "physical_map_sha256": reference_sha,
                        "scenario_sha256": "",
                        "map_scenario_format": "ggo_json_guidance_reference",
                        "source_category": "ggo_alignment_reference",
                        "scenario_source_type": "ggo_alignment_reference_not_direct_one_shot_mapf_scenario",
                        "panel": "G",
                        "official_scenario": False,
                        "czr004_derived_scenario": True,
                        "scenario_prefix_family": f"ggo-panel-{map_name}-{tier}",
                        "scientific_split": "split_later_by_parent_map_hash",
                        "agent_count_capacity": tier,
                        "requested_agent_tier": tier,
                        "scenario_rows_available": "",
                        "prefix_rows_validated": "",
                        "validation_result": "pass",
                        "validation_failures": "",
                    }
                )
            continue
        scenario_rows.append(
            {
                "source_key": "ggo_public",
                "source_url": str(GIT_SOURCES["ggo_public"]["url"]),
                "source_provenance": source_by_key.get("ggo_public", {}).get("git_commit", ""),
                "license_and_redistribution_status": source_by_key.get("ggo_public", {}).get("license_and_redistribution_status", ""),
                "original_relative_path": f"ggo_alignment_panel:{map_name}/{tier}",
                "map_name": map_name,
                "local_map_path": rel(info.path),
                "parent_physical_map_sha256": info.physical_map_sha256,
                "physical_map_sha256": info.physical_map_sha256,
                "map_scenario_format": "ggo_guidance_reference_or_czr004_derived_one_shot",
                "source_category": "ggo_alignment_reference",
                "scenario_source_type": "czr004_derived_one_shot_required_from_ggo_panel_spec",
                "panel": "G",
                "official_scenario": False,
                "czr004_derived_scenario": True,
                "scenario_prefix_family": f"ggo-panel-{map_name}-{tier}",
                "scientific_split": "split_later_by_parent_map_hash",
                "agent_count_capacity": info.free_cells,
                "requested_agent_tier": tier,
                "validation_result": "pass" if info.free_cells >= tier else "fail",
                "validation_failures": "" if info.free_cells >= tier else "ggo_panel_tier_exceeds_free_cells",
            }
        )

    for key in ["lorr_benchmark_archive", "sillm_icra2025"]:
        source = source_by_key.get(key, {})
        if source.get("source_status") != "available":
            continue
        root = resolve(source.get("local_source_path", benchmark_root / str(GIT_SOURCES[key]["path"])))
        limit = 64
        for path in sorted(root.rglob("*.map"))[:limit]:
            try:
                info = read_movingai_map(path)
            except Exception:
                continue
            map_rows.append(
                map_registry_row(
                    info,
                    source_key=key,
                    source_url=str(GIT_SOURCES[key]["url"]),
                    source_provenance=str(source.get("git_commit", "")),
                    source_category=str(GIT_SOURCES[key]["source_category"]),
                    panel="L",
                    original_relative_path=source_rel(path, root),
                    license_status=str(source.get("license_and_redistribution_status", "")),
                    validation_result="pass",
                    validation_failures="",
                    use_in_g567=True,
                )
            )

    split_audit_rows, split_failures = build_parent_split_audit(map_rows, scenario_rows)
    validation_failures = [
        f"map:{row.get('map_name')}:{row.get('validation_failures')}"
        for row in map_rows
        if row.get("validation_result") == "fail"
    ]
    validation_failures.extend(
        f"scenario:{row.get('scenario_prefix_family')}:{row.get('requested_agent_tier')}:{row.get('validation_failures')}"
        for row in scenario_rows
        if row.get("validation_result") == "fail"
    )
    provenance_failures = [
        f"{row.get('source_key')}:missing_source_provenance"
        for row in source_rows
        if row.get("source_required") and not row.get("source_provenance")
    ]
    panel_counts = Counter(str(row.get("panel", "")) for row in map_rows if row.get("validation_result") == "pass")
    scenario_panel_counts = Counter(str(row.get("panel", "")) for row in scenario_rows if row.get("validation_result") == "pass")
    required_panels_present = all(panel_counts.get(panel, 0) + scenario_panel_counts.get(panel, 0) > 0 for panel in ["M", "H", "G", "L"])
    failures = source_errors + provenance_failures + validation_failures + split_failures
    if not required_panels_present:
        failures.append("required_public_panels_M_H_G_L_not_all_present")
    decision = "g567_public_benchmark_ingestion_ready" if not failures else "g567_public_benchmark_ingestion_blocked"
    summary = {
        "schema_version": f"{ROUND}_public_benchmark_ingestion_summary_v1",
        "decision": decision,
        "benchmark_root": rel(benchmark_root),
        "sources": source_rows,
        "source_count": len(source_rows),
        "sources_available": sum(1 for row in source_rows if row.get("source_status") == "available"),
        "map_registry_rows": len(map_rows),
        "valid_map_registry_rows": sum(1 for row in map_rows if row.get("validation_result") == "pass"),
        "scenario_registry_rows": len(scenario_rows),
        "valid_scenario_registry_rows": sum(1 for row in scenario_rows if row.get("validation_result") == "pass"),
        "panel_map_counts": dict(sorted(panel_counts.items())),
        "panel_scenario_counts": dict(sorted(scenario_panel_counts.items())),
        "required_panels_present": required_panels_present,
        "parent_split_audit_rows": len(split_audit_rows),
        "failure_count": len(failures),
        "failures": failures[:200],
        "raw_archives_committed": False,
        "final_blind_accessed": False,
        "created_unix": time.time(),
    }
    write_rows(PUBLIC_MAP_REGISTRY, map_rows)
    write_rows(PUBLIC_SCENARIO_REGISTRY, scenario_rows)
    write_rows(PARENT_MAP_SPLIT_AUDIT, split_audit_rows)
    write_json(PUBLIC_INGESTION_SUMMARY, summary)
    write_text(
        PUBLIC_INGESTION_MD,
        "# Repair5G.5.67 Public Benchmark Ingestion\n\n"
        f"- decision: `{summary['decision']}`\n"
        f"- benchmark root: `{summary['benchmark_root']}`\n"
        f"- sources available: `{summary['sources_available']}/{summary['source_count']}`\n"
        f"- map registry rows: `{summary['map_registry_rows']}` valid `{summary['valid_map_registry_rows']}`\n"
        f"- scenario registry rows: `{summary['scenario_registry_rows']}` valid `{summary['valid_scenario_registry_rows']}`\n"
        f"- panels present: `{summary['required_panels_present']}`\n"
        f"- failure count: `{summary['failure_count']}`\n\n"
        "Raw archives and cloned benchmark repositories are not committed. This ingestion writes hashes, commits, source URLs, license/redistribution notes, parent-map hashes, official-vs-derived scenario flags, split policy, capacity, and validation results.\n\n"
        "Panel L rows are OOD or derived one-shot diagnostics only; they are not reported as original lifelong benchmark results.\n",
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download/freeze public benchmark metadata for Repair5G.5.67.")
    parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    parser.add_argument("--no-download", action="store_true", help="Only inspect existing local benchmark files.")
    parser.add_argument("--refresh-git", action="store_true", help="Refresh existing git sources before freezing commits.")
    parser.add_argument("--skip-optional-sillm", action="store_true")
    args = parser.parse_args(argv)
    summary = ingest_public_benchmarks(
        benchmark_root=args.benchmark_root,
        no_download=bool(args.no_download),
        refresh_git=bool(args.refresh_git),
        include_optional_sillm=not bool(args.skip_optional_sillm),
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary.get("decision") == "g567_public_benchmark_ingestion_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate deterministic Phase1a random MAPF scenarios.

The LTM paper states that it generates 25 random instances per map. The public
MovingAI random .scen files are too small for several Figure 1 agent counts, so
this script creates auditable, deterministic random scenarios with enough
start-goal pairs for the frozen Phase1a schedule.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import zipfile
from collections import deque
from pathlib import Path


SCRIPT_VERSION = "phase1a-scenario-generator-v1"
ZIP_TIMESTAMP = (2026, 5, 22, 0, 0, 0)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_manifest(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def read_map(path: Path) -> tuple[int, int, list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    height = None
    width = None
    map_start = None
    for index, line in enumerate(lines):
        if line.startswith("height "):
            height = int(line.split()[1])
        elif line.startswith("width "):
            width = int(line.split()[1])
        elif line == "map":
            map_start = index + 1
            break

    if height is None or width is None or map_start is None:
        raise ValueError(f"{path}: invalid MovingAI map header")

    grid = lines[map_start : map_start + height]
    if len(grid) != height or any(len(row) != width for row in grid):
        raise ValueError(f"{path}: map dimensions do not match header")
    return width, height, grid


def free_cells(grid: list[str]) -> list[tuple[int, int]]:
    cells: list[tuple[int, int]] = []
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell not in {"@", "T"}:
                cells.append((x, y))
    return cells


def largest_component(width: int, height: int, grid: list[str]) -> list[tuple[int, int]]:
    free = set(free_cells(grid))
    seen: set[tuple[int, int]] = set()
    best: list[tuple[int, int]] = []

    for start in free:
        if start in seen:
            continue
        component: list[tuple[int, int]] = []
        queue: deque[tuple[int, int]] = deque([start])
        seen.add(start)
        while queue:
            x, y = queue.popleft()
            component.append((x, y))
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                nxt = (nx, ny)
                if 0 <= nx < width and 0 <= ny < height and nxt in free and nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        if len(component) > len(best):
            best = component

    return sorted(best, key=lambda cell: (cell[1], cell[0]))


def map_seed(base_seed: int, map_name: str, instance_id: int) -> int:
    digest = hashlib.sha256(f"{SCRIPT_VERSION}|{base_seed}|{map_name}|{instance_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def deranged_goals(
    rng: random.Random,
    cells: list[tuple[int, int]],
    starts: list[tuple[int, int]],
    count: int,
) -> list[tuple[int, int]]:
    for _ in range(1000):
        goals = rng.sample(cells, count)
        if all(start != goal for start, goal in zip(starts, goals)):
            return goals
    raise RuntimeError("failed to sample goal derangement")


def manhattan(start: tuple[int, int], goal: tuple[int, int]) -> int:
    return abs(start[0] - goal[0]) + abs(start[1] - goal[1])


def scenario_text(
    map_name: str,
    width: int,
    height: int,
    starts: list[tuple[int, int]],
    goals: list[tuple[int, int]],
) -> str:
    lines = ["version 1"]
    for index, (start, goal) in enumerate(zip(starts, goals)):
        sx, sy = start
        gx, gy = goal
        distance_hint = manhattan(start, goal)
        lines.append(
            f"{index}\t{map_name}.map\t{width}\t{height}\t{sx}\t{sy}\t{gx}\t{gy}\t{distance_hint}"
        )
    return "\n".join(lines) + "\n"


def write_zip(output_zip: Path, source_dir: Path) -> None:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    if output_zip.exists():
        output_zip.unlink()

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file():
                continue
            arcname = path.relative_to(source_dir.parent).as_posix()
            info = zipfile.ZipInfo(arcname, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="configs/phase1a/manifest.jsonl")
    parser.add_argument("--output-dir", default="outputs/tmp/phase1a/generated/phase1a-generated-random")
    parser.add_argument("--output-zip", default="outputs/tmp/phase1a/generated/phase1a-generated-random.zip")
    parser.add_argument("--metadata", default="outputs/reports/phase1a_generated_scenarios_manifest.json")
    parser.add_argument("--base-seed", type=int, default=20260522)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    root = project_root()
    manifest = read_manifest(root / args.manifest)
    output_dir = root / args.output_dir
    output_zip = root / args.output_zip
    metadata_path = root / args.metadata

    if output_dir.exists():
        if not args.overwrite:
            raise FileExistsError(f"{output_dir} exists; pass --overwrite")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata: dict = {
        "script_version": SCRIPT_VERSION,
        "base_seed": args.base_seed,
        "scenario_dir": args.output_dir.replace("\\", "/"),
        "scenario_zip": args.output_zip.replace("\\", "/"),
        "rules": {
            "component": "largest 4-neighbor connected free-cell component",
            "starts": "sampled without replacement",
            "goals": "sampled without replacement",
            "per_agent_start_goal": "start != goal",
            "distance_column": "Manhattan distance hint; LaCAM2 parser ignores this column and recomputes graph distances",
        },
        "maps": [],
    }

    for record in manifest:
        map_name = record["map"]
        map_path = root / record["map_path"]
        width, height, grid = read_map(map_path)
        cells = largest_component(width, height, grid)
        max_agents = max(int(value) for value in record["agent_counts"])
        if len(cells) < max_agents:
            raise ValueError(
                f"{map_name}: largest connected component has {len(cells)} cells, "
                f"but max_agents={max_agents}"
            )

        map_meta = {
            "map": map_name,
            "map_path": record["map_path"],
            "width": width,
            "height": height,
            "free_cells_largest_component": len(cells),
            "max_agents": max_agents,
            "instances": [],
        }

        for instance_id in [int(value) for value in record["instances"]]:
            rng = random.Random(map_seed(args.base_seed, map_name, instance_id))
            starts = rng.sample(cells, max_agents)
            goals = deranged_goals(rng, cells, starts, max_agents)
            text = scenario_text(map_name, width, height, starts, goals)

            relative = Path("phase1a-generated-random") / f"{map_name}-random-{instance_id}.scen"
            path = output_dir / relative.name
            path.write_text(text, encoding="utf-8", newline="\n")
            map_meta["instances"].append(
                {
                    "id": instance_id,
                    "pairs": max_agents,
                    "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "path": relative.as_posix(),
                }
            )

        metadata["maps"].append(map_meta)

    write_zip(output_zip, output_dir)
    metadata["zip_sha256"] = sha256_file(output_zip)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    total_files = sum(len(item["instances"]) for item in metadata["maps"])
    print(f"Generated {total_files} scenarios: {output_dir}")
    print(f"Archive: {output_zip}")
    print(f"Metadata: {metadata_path}")
    print(f"Archive sha256: {metadata['zip_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

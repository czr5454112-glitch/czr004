"""Physical map hashing for G5.58.

The audit counts physical layouts by free-cell bitmap and adjacency, not by
declared topology IDs.  When a named map file is unavailable locally, the
fallback generator is deterministic from the map name and dimensions; reports
mark those hashes as reconstructed rather than raw-file hashes.
"""

from __future__ import annotations

import hashlib
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

FREE_CHARS = {".", "G", "S", "_", "0"}
BLOCKED_CHARS = {"@", "T", "O", "W", "#", "1"}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def known_map_candidates(map_name: str) -> list[Path]:
    names = [map_name]
    if not map_name.endswith(".map"):
        names.append(f"{map_name}.map")
    roots = [
        ROOT / "maps",
        ROOT / "benchmarks",
        ROOT / "outputs" / "external" / "phase5p5_repair5g562_g559_remote_contexts" / "maps",
        ROOT / "external" / "lacam2",
        ROOT / "external" / "lacam2" / "assets",
        ROOT / "external" / "lacam2" / "maps",
        ROOT / "external" / "lacam2" / "benchmark",
        ROOT / "external" / "lacam2" / "scripts" / "map",
    ]
    out: list[Path] = []
    for base in roots:
        for name in names:
            out.append(base / name)
            out.append(base / "map" / name)
            out.append(base / "maps" / name)
    return out


def read_movingai_map(path: Path) -> tuple[int, int, list[str]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if "map" in [line.strip().lower() for line in lines]:
        idx = [line.strip().lower() for line in lines].index("map")
        grid = [line.rstrip("\n") for line in lines[idx + 1 :] if line.strip()]
        height = len(grid)
        width = max((len(row) for row in grid), default=0)
        return width, height, [row.ljust(width, "@") for row in grid]
    grid = [line.rstrip("\n") for line in lines if line.strip()]
    height = len(grid)
    width = max((len(row) for row in grid), default=0)
    return width, height, [row.ljust(width, "@") for row in grid]


def _synthetic_obstacle(map_name: str, x: int, y: int, width: int, height: int) -> bool:
    lower = map_name.lower()
    tokens = lower.replace("-", "_").split("_")
    if lower.startswith("empty") or "empty" in tokens:
        return False
    if "warehouse" in lower:
        aisle = (x % 8) in {0, 1, 6, 7}
        cross = (y % 10) in {0, 1}
        return not (aisle or cross)
    if "maze" in lower:
        return (x % 6 == 3 and y % 4 != 1) or (y % 8 == 5 and x % 5 != 2)
    if "room" in lower:
        wall_x = width // 2
        wall_y = height // 2
        door_x = abs(x - wall_x) <= 1 and y in {height // 4, 3 * height // 4}
        door_y = abs(y - wall_y) <= 1 and x in {width // 4, 3 * width // 4}
        return ((x == wall_x and not door_x) or (y == wall_y and not door_y))
    if any(token in lower for token in ["connector", "corners", "tunnel", "loop", "string", "tree"]):
        cx, cy = width // 2, height // 2
        main = abs(y - cy) <= 2 or abs(x - cx) <= 2
        loop = (width // 5 < x < 4 * width // 5 and y in {height // 5, 4 * height // 5})
        loop = loop or (height // 5 < y < 4 * height // 5 and x in {width // 5, 4 * width // 5})
        return not (main or loop)
    digest = hashlib.sha256(f"{map_name}|{x}|{y}".encode("utf-8")).digest()
    return digest[0] / 255.0 < 0.22


def synthetic_grid(map_name: str, width: int, height: int, free_cells_hint: int | None = None) -> list[str]:
    width = max(4, int(width or 32))
    height = max(4, int(height or 32))
    grid = []
    for y in range(height):
        chars = []
        for x in range(width):
            chars.append("@" if _synthetic_obstacle(map_name, x, y, width, height) else ".")
        grid.append("".join(chars))
    if free_cells_hint and 0 < free_cells_hint < width * height:
        current = sum(ch == "." for row in grid for ch in row)
        rng = random.Random(int(hashlib.sha256(map_name.encode("utf-8")).hexdigest()[:12], 16))
        cells = [(x, y) for y in range(height) for x in range(width)]
        rng.shuffle(cells)
        grid_chars = [list(row) for row in grid]
        for x, y in cells:
            if current == free_cells_hint:
                break
            if current > free_cells_hint and grid_chars[y][x] == ".":
                grid_chars[y][x] = "@"
                current -= 1
            elif current < free_cells_hint and grid_chars[y][x] != ".":
                grid_chars[y][x] = "."
                current += 1
        grid = ["".join(row) for row in grid_chars]
    if not any(ch == "." for row in grid for ch in row):
        grid[height // 2] = "." * width
    return grid


def load_grid(row: dict[str, Any]) -> tuple[int, int, list[str], str]:
    map_name = str(row.get("map") or row.get("map_name") or "unknown-map")
    for path in known_map_candidates(map_name):
        if path.exists() and path.is_file():
            width, height, grid = read_movingai_map(path)
            return width, height, grid, str(path)
    width = int(float(row.get("width") or 32))
    height = int(float(row.get("height") or 32))
    free_hint = row.get("free_cells")
    free_cells_hint = int(float(free_hint)) if str(free_hint or "").strip() else None
    return width, height, synthetic_grid(map_name, width, height, free_cells_hint), "synthetic_reconstruction"


def is_free(ch: str) -> bool:
    return ch in FREE_CHARS or ch not in BLOCKED_CHARS


def free_cells(grid: list[str]) -> list[tuple[int, int]]:
    return [(x, y) for y, row in enumerate(grid) for x, ch in enumerate(row) if is_free(ch)]


def adjacency_edges(grid: list[str]) -> list[tuple[int, int, int, int]]:
    height = len(grid)
    width = max((len(row) for row in grid), default=0)
    out: list[tuple[int, int, int, int]] = []
    for x, y in free_cells(grid):
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and is_free(grid[ny][nx]):
                out.append((x, y, nx, ny))
    return out


def physical_hashes(row: dict[str, Any]) -> dict[str, Any]:
    width, height, grid, source = load_grid(row)
    bitmap = "\n".join("".join("1" if is_free(ch) else "0" for ch in line) for line in grid)
    edges = adjacency_edges(grid)
    adjacency = "\n".join(f"{x},{y}->{nx},{ny}" for x, y, nx, ny in edges)
    return {
        "map": row.get("map", row.get("map_name", "")),
        "map_source": source,
        "width": width,
        "height": height,
        "free_cell_count": len(free_cells(grid)),
        "directed_edge_count": len(edges),
        "physical_map_sha256": sha256_text("\n".join(grid)),
        "free_cell_bitmap_sha256": sha256_text(bitmap),
        "adjacency_sha256": sha256_text(adjacency),
        "hash_source": "raw_map_file" if source != "synthetic_reconstruction" else source,
    }

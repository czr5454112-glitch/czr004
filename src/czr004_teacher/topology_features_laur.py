"""Topology helpers for LAU stable-attention token features."""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any


class TokenMapTopology:
    """MovingAI map topology with LaCAM-style compact free-cell ids."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.width = 0
        self.height = 0
        self.free_cells = 0
        self.obstacle_cells = 0
        self.id_to_xy: dict[int, tuple[int, int]] = {}
        self.xy_to_id: dict[tuple[int, int], int] = {}
        self.neighbors: dict[int, list[int]] = {}
        self._load()

    @property
    def obstacle_ratio(self) -> float:
        total = self.width * self.height
        return float(self.obstacle_cells) / float(total) if total else 0.0

    def coord(self, vertex_id: int) -> tuple[int, int] | None:
        return self.id_to_xy.get(int(vertex_id))

    def degree(self, vertex_id: int) -> int:
        return len(self.neighbors.get(int(vertex_id), []))

    def shares_endpoint(self, first: tuple[int, int], second: tuple[int, int]) -> bool:
        return first[0] in second or first[1] in second

    def graph_distance(self, source: int, target: int, *, max_depth: int = 2) -> int | None:
        source = int(source)
        target = int(target)
        if source == target:
            return 0
        frontier: deque[tuple[int, int]] = deque([(source, 0)])
        seen = {source}
        while frontier:
            node, depth = frontier.popleft()
            if depth >= max_depth:
                continue
            for nxt in self.neighbors.get(node, []):
                if nxt == target:
                    return depth + 1
                if nxt not in seen:
                    seen.add(nxt)
                    frontier.append((nxt, depth + 1))
        return None

    def local_obstacle_boundary_score(self, vertex_id: int) -> float:
        xy = self.coord(vertex_id)
        if xy is None:
            return 0.0
        x, y = xy
        blocked = 0
        total = 0
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            total += 1
            if nx < 0 or ny < 0 or nx >= self.width or ny >= self.height:
                blocked += 1
            elif (nx, ny) not in self.xy_to_id:
                blocked += 1
        return float(blocked) / float(total) if total else 0.0

    def _load(self) -> None:
        lines = self.path.read_text(encoding="utf-8").splitlines()
        map_start = None
        for index, line in enumerate(lines):
            if line.startswith("height "):
                self.height = int(line.split()[1])
            elif line.startswith("width "):
                self.width = int(line.split()[1])
            elif line == "map":
                map_start = index + 1
                break
        if map_start is None:
            raise ValueError(f"{self.path}: missing MovingAI map body")
        grid = lines[map_start : map_start + self.height]
        if len(grid) != self.height:
            raise ValueError(f"{self.path}: expected {self.height} map rows, found {len(grid)}")
        for y, row in enumerate(grid):
            if len(row) != self.width:
                raise ValueError(f"{self.path}: row {y} width mismatch")
            for x, char in enumerate(row):
                if char in {"@", "T"}:
                    self.obstacle_cells += 1
                    continue
                vertex_id = len(self.id_to_xy)
                self.id_to_xy[vertex_id] = (x, y)
                self.xy_to_id[(x, y)] = vertex_id
        self.free_cells = len(self.id_to_xy)
        for vertex_id, (x, y) in self.id_to_xy.items():
            adjacent: list[int] = []
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if (nx, ny) in self.xy_to_id:
                    adjacent.append(self.xy_to_id[(nx, ny)])
            self.neighbors[vertex_id] = adjacent


def local_map_path(checkpoint_row: dict[str, Any], repo_root: str | Path | None = None) -> Path | None:
    value = checkpoint_row.get("map_path") or checkpoint_row.get("map")
    if not value:
        return None
    path = Path(str(value))
    if path.exists():
        return path
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    if not path.is_absolute() and (root / path).exists():
        return root / path
    candidates = [
        root / "external" / "lacam2" / "scripts" / "map" / path.name,
        root / "external" / "lacam2" / "assets" / path.name,
        root / "assets" / path.name,
    ]
    return next((candidate for candidate in candidates if candidate.exists()), None)


def topology_for_checkpoint(
    checkpoint_row: dict[str, Any],
    cache: dict[Path, TokenMapTopology],
    repo_root: str | Path | None = None,
) -> TokenMapTopology | None:
    path = local_map_path(checkpoint_row, repo_root=repo_root)
    if path is None:
        return None
    resolved = path.resolve()
    if resolved not in cache:
        cache[resolved] = TokenMapTopology(resolved)
    return cache[resolved]

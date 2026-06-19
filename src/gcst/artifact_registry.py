"""Durable artifact registry helpers for remote G5.59 runs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class ArtifactEntry:
    uri: str
    schema_version: str
    row_count: int
    size_bytes: int
    sha256: str
    producer_command: str
    source_commit: str


def sha256_file(path: Path, limit_bytes: int | None = None) -> str:
    if not path.exists() or not path.is_file():
        return ""
    if limit_bytes is not None and path.stat().st_size > limit_bytes:
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def row_count(path: Path) -> int:
    if not path.exists() or not path.is_file():
        return 0
    if path.suffix.lower() == ".csv":
        with path.open("rb") as handle:
            return max(0, sum(1 for _ in handle) - 1)
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        with path.open("rb") as handle:
            return sum(1 for line in handle if line.strip())
    return 1


def make_entry(path: Path, *, schema_version: str, producer_command: str, source_commit: str, root: Path | None = None) -> ArtifactEntry:
    root = root or path.parent
    uri = str(path if path.is_absolute() else path)
    try:
        uri = str(path.resolve().relative_to(root.resolve()))
    except Exception:
        pass
    return ArtifactEntry(
        uri=uri.replace("\\", "/"),
        schema_version=schema_version,
        row_count=row_count(path),
        size_bytes=path.stat().st_size if path.exists() else 0,
        sha256=sha256_file(path, limit_bytes=200 * 1024 * 1024),
        producer_command=producer_command,
        source_commit=source_commit,
    )


def write_registry(path: Path, entries: list[ArtifactEntry], extra: dict[str, Any] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": "phase5p5_repair5g559_artifact_registry_v1", "entries": [asdict(e) for e in entries], **(extra or {})}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

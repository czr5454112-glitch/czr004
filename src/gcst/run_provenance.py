"""Run-scoped provenance helpers for G5.63."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, Iterable


def new_run_uid(round_name: str, slug: str = "") -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in slug.strip().lower()).strip("_")
    suffix = f"_{cleaned}" if cleaned else ""
    stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    return f"{round_name}{suffix}_{stamp}_{uuid.uuid4().hex[:10]}"


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_json(data: Any) -> str:
    text = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def progress_path(root: str | Path, round_name: str, run_uid: str) -> Path:
    return Path(root) / "outputs" / "reports" / f"{round_name}_{run_uid}_progress.jsonl"


def append_progress(path: str | Path, run_uid: str, row: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"run_uid": run_uid, "time_unix": time.time(), **row}
    with p.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def read_progress(path: str | Path, run_uid: str | None = None) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    with p.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if run_uid is None or row.get("run_uid") == run_uid:
                rows.append(row)
    return rows


def progress_dataset_count(rows: Iterable[dict[str, Any]]) -> int | None:
    for row in rows:
        if "dataset_count" in row:
            try:
                return int(row["dataset_count"])
            except Exception:
                return None
        if row.get("event") in {"start", "dataset_ready"} and "contexts" in row:
            try:
                return int(row["contexts"])
            except Exception:
                return None
    return None


def summary_matches_progress(summary: dict[str, Any], progress_rows: list[dict[str, Any]]) -> bool:
    if not progress_rows:
        raise AssertionError("no run-scoped progress rows")
    run_uid = summary.get("run_uid")
    if not run_uid:
        raise AssertionError("summary is missing run_uid")
    mismatched = [row.get("run_uid") for row in progress_rows if row.get("run_uid") != run_uid]
    if mismatched:
        raise AssertionError("progress rows include a different run_uid")
    expected = summary.get("dataset_count", summary.get("contexts"))
    observed = progress_dataset_count(progress_rows)
    if expected is not None and observed is not None and int(expected) != int(observed):
        raise AssertionError(f"summary dataset count {expected} != progress dataset count {observed}")
    return True


def artifact_manifest(paths: Iterable[str | Path], root: str | Path = ".") -> list[dict[str, Any]]:
    root_path = Path(root).resolve()
    rows = []
    for path in paths:
        p = Path(path)
        if not p.exists() or not p.is_file():
            continue
        try:
            rel = p.resolve().relative_to(root_path)
        except ValueError:
            rel = p.resolve()
        rows.append({"path": str(rel).replace("\\", "/"), "bytes": p.stat().st_size, "sha256": sha256_file(p)})
    return rows

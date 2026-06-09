"""Merge Repair5F.2 per-map support probe chunks into the required paths."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = "outputs/logs/phase5p5_repair5f_selector_support_probe"
DEFAULT_OUTPUT_STEM = "phase5p5_repair5f_selector_support_probe"
DEFAULT_CHUNKS = [
    (
        "outputs/logs/phase5p5_repair5f_selector_support_probe",
        "phase5p5_repair5f_selector_support_probe",
    ),
    (
        "outputs/logs/phase5p5_repair5f_selector_support_probe_maze_tmp",
        "phase5p5_repair5f_selector_support_probe_maze_tmp",
    ),
    (
        "outputs/logs/phase5p5_repair5f_selector_support_probe_warehouse_tmp",
        "phase5p5_repair5f_selector_support_probe_warehouse_tmp",
    ),
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve(path: str | Path, root: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def skip_method(method: Any) -> bool:
    return str(method).startswith("repair5e5_")


def raw_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (
        str(row.get("map")),
        int(float(row.get("agents") or 0)),
        int(float(row.get("seed") or 0)),
        str(row.get("method")),
    )


def iter_jsonl(path: Path) -> list[tuple[str, dict[str, Any]]]:
    if not path.exists():
        return []
    rows: list[tuple[str, dict[str, Any]]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if skip_method(row.get("method")):
                continue
            rows.append((json.dumps(row, sort_keys=True), row))
    return rows


def write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        for line in lines:
            handle.write(line.rstrip("\n") + "\n")
    tmp.replace(path)


def merge_raw(output: Path, chunk_paths: list[Path]) -> dict[str, int]:
    seen: set[tuple[str, int, int, str]] = set()
    lines: list[str] = []
    input_rows = 0
    skipped_duplicates = 0
    for path in chunk_paths:
        for line, row in iter_jsonl(path):
            input_rows += 1
            key = raw_key(row)
            if key in seen:
                skipped_duplicates += 1
                continue
            seen.add(key)
            lines.append(line)
    write_lines(output, lines)
    return {
        "input_rows": input_rows,
        "output_rows": len(lines),
        "skipped_duplicates": skipped_duplicates,
    }


def merge_line_log(output: Path, chunk_paths: list[Path]) -> dict[str, int]:
    seen: set[str] = set()
    lines: list[str] = []
    input_rows = 0
    skipped_duplicates = 0
    for path in chunk_paths:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                if not raw_line.strip():
                    continue
                try:
                    row = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if skip_method(row.get("method")):
                    continue
                line = raw_line.strip()
                input_rows += 1
                if line in seen:
                    skipped_duplicates += 1
                    continue
                seen.add(line)
                lines.append(line)
    write_lines(output, lines)
    return {
        "input_rows": input_rows,
        "output_rows": len(lines),
        "skipped_duplicates": skipped_duplicates,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output-stem", default=DEFAULT_OUTPUT_STEM)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    output_dir = resolve(args.output_dir, root)
    raw_chunks = [resolve(Path(directory) / f"{stem}.jsonl", root) for directory, stem in DEFAULT_CHUNKS]
    command_chunks = [resolve(Path(directory) / f"{stem}_commands.jsonl", root) for directory, stem in DEFAULT_CHUNKS]
    update_chunks = [resolve(Path(directory) / f"{stem}_laur_updates.jsonl", root) for directory, stem in DEFAULT_CHUNKS]
    raw_output = output_dir / f"{args.output_stem}.jsonl"
    command_output = output_dir / f"{args.output_stem}_commands.jsonl"
    update_output = output_dir / f"{args.output_stem}_laur_updates.jsonl"
    summary = {
        "raw": merge_raw(raw_output, raw_chunks),
        "commands": merge_line_log(command_output, command_chunks),
        "laur_updates": merge_line_log(update_output, update_chunks),
        "raw_output": str(raw_output),
        "command_output": str(command_output),
        "laur_update_output": str(update_output),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

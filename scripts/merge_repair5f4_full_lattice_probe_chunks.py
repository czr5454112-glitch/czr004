"""Merge Repair5F.4 full-lattice probe chunks into the required log paths."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = "outputs/logs/phase5p5_repair5f4_full_lattice_probe"
DEFAULT_OUTPUT_STEM = "phase5p5_repair5f4_full_lattice_probe"
DEFAULT_CHUNK_PREFIX = "phase5p5_repair5f4_full_lattice_probe_chunk"
DEFAULT_PARTIAL_DIR = "outputs/logs/phase5p5_repair5f4_full_lattice_probe_serial_partial"


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


def jsonl_rows(path: Path) -> list[tuple[str, dict[str, Any]]]:
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


def merge_raw(output: Path, inputs: list[Path]) -> dict[str, int]:
    seen: set[tuple[str, int, int, str]] = set()
    lines: list[str] = []
    input_rows = 0
    skipped_duplicates = 0
    for path in inputs:
        for line, row in jsonl_rows(path):
            input_rows += 1
            key = raw_key(row)
            if key in seen:
                skipped_duplicates += 1
                continue
            seen.add(key)
            lines.append(line)
    write_lines(output, lines)
    return {"input_rows": input_rows, "output_rows": len(lines), "skipped_duplicates": skipped_duplicates}


def merge_line_log(output: Path, inputs: list[Path]) -> dict[str, int]:
    seen: set[str] = set()
    lines: list[str] = []
    input_rows = 0
    skipped_duplicates = 0
    for path in inputs:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if skip_method(row.get("method")):
                    continue
                normalized = json.dumps(row, sort_keys=True)
                input_rows += 1
                if normalized in seen:
                    skipped_duplicates += 1
                    continue
                seen.add(normalized)
                lines.append(normalized)
    write_lines(output, lines)
    return {"input_rows": input_rows, "output_rows": len(lines), "skipped_duplicates": skipped_duplicates}


def merge_command_log(output: Path, inputs: list[Path], raw_output: Path) -> dict[str, int]:
    raw_keys = {raw_key(row) for _line, row in jsonl_rows(raw_output)}
    seen: set[tuple[str, int, int, str]] = set()
    lines: list[str] = []
    input_rows = 0
    skipped_duplicates = 0
    skipped_without_raw = 0
    for path in inputs:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if skip_method(row.get("method")):
                    continue
                input_rows += 1
                key = raw_key(row)
                if key not in raw_keys:
                    skipped_without_raw += 1
                    continue
                if key in seen:
                    skipped_duplicates += 1
                    continue
                seen.add(key)
                lines.append(json.dumps(row, sort_keys=True))
    write_lines(output, lines)
    return {
        "input_rows": input_rows,
        "output_rows": len(lines),
        "skipped_duplicates": skipped_duplicates,
        "skipped_without_raw": skipped_without_raw,
    }


def chunk_dirs(root: Path, count: int, partial_dir: Path) -> list[tuple[Path, str]]:
    chunks: list[tuple[Path, str]] = []
    if partial_dir.exists():
        chunks.append((partial_dir, DEFAULT_OUTPUT_STEM))
    for index in range(count):
        stem = f"{DEFAULT_CHUNK_PREFIX}{index:02d}"
        directory = root / "outputs" / "logs" / stem
        if directory.exists():
            chunks.append((directory, stem))
    return chunks


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output-stem", default=DEFAULT_OUTPUT_STEM)
    parser.add_argument("--partial-dir", type=Path, default=Path(DEFAULT_PARTIAL_DIR))
    parser.add_argument("--chunk-count", type=int, default=8)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    output_dir = resolve(args.output_dir, root)
    partial_dir = resolve(args.partial_dir, root)
    chunks = chunk_dirs(root, int(args.chunk_count), partial_dir)
    raw_inputs = [directory / f"{stem}.jsonl" for directory, stem in chunks]
    command_inputs = [directory / f"{stem}_commands.jsonl" for directory, stem in chunks]
    update_inputs = [directory / f"{stem}_laur_updates.jsonl" for directory, stem in chunks]
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_output = output_dir / f"{args.output_stem}.jsonl"
    command_output = output_dir / f"{args.output_stem}_commands.jsonl"
    update_output = output_dir / f"{args.output_stem}_laur_updates.jsonl"
    raw_summary = merge_raw(raw_output, raw_inputs)
    summary = {
        "chunks": [str(path) for path, _stem in chunks],
        "raw": raw_summary,
        "commands": merge_command_log(command_output, command_inputs, raw_output),
        "laur_updates": merge_line_log(update_output, update_inputs),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

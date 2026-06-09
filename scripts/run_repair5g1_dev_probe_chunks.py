"""Run the Repair5G.1 dev probe in independent chunks and merge outputs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROBE_SCRIPT = ROOT / "scripts" / "run_repair5g1_agent_aware_dual_channel_probe.py"
MAPS = ["random-32-32-20", "maze-32-32-4", "warehouse-10-20-10-2-1"]
ID_GROUPS = [
    ("i26_30", [26, 27, 28, 29, 30]),
    ("i31_35", [31, 32, 33, 34, 35]),
    ("i36_40", [36, 37, 38, 39, 40]),
    ("i41_45", [41, 42, 43, 44, 45]),
]
AGENTS = [50, 100]

CHUNK_LOG_DIR = ROOT / "outputs" / "logs" / "phase5p5_repair5g1_dev_probe_chunks"
CHUNK_TABLE_DIR = ROOT / "outputs" / "tables" / "phase5p5_repair5g1_dev_probe_chunks"
CHUNK_REPORT_DIR = ROOT / "outputs" / "reports" / "phase5p5_repair5g1_dev_probe_chunks"
STATUS_PATH = ROOT / "outputs" / "reports" / "phase5p5_repair5g1_dev_chunk_status.json"
FINAL_LOG_DIR = ROOT / "outputs" / "logs" / "phase5p5_repair5g1_dev_probe"
FINAL_JSONL = FINAL_LOG_DIR / "phase5p5_repair5g1_dev_probe.jsonl"
FINAL_COMMANDS = FINAL_LOG_DIR / "phase5p5_repair5g1_dev_probe_commands.jsonl"
FINAL_UPDATES = FINAL_LOG_DIR / "phase5p5_repair5g1_dev_probe_ltm_updates.jsonl"


@dataclass
class Chunk:
    name: str
    agent: int
    instance_ids: list[int]
    jsonl: Path
    commands: Path
    updates: Path
    stdout: Path
    stderr: Path
    long_csv: Path
    wide_csv: Path
    ranking_csv: Path
    by_map_agent_csv: Path
    component_csv: Path
    report: Path
    summary: Path
    audit: Path


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def tail_text(path: Path, limit: int = 1000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-limit:]


def build_chunks() -> list[Chunk]:
    chunks: list[Chunk] = []
    for suffix, instance_ids in ID_GROUPS:
        for agent in AGENTS:
            name = f"chunk_{suffix}_a{agent}"
            chunks.append(
                Chunk(
                    name=name,
                    agent=agent,
                    instance_ids=instance_ids,
                    jsonl=CHUNK_LOG_DIR / f"{name}.jsonl",
                    commands=CHUNK_LOG_DIR / f"{name}.commands.jsonl",
                    updates=CHUNK_LOG_DIR / f"{name}.updates.jsonl",
                    stdout=CHUNK_LOG_DIR / f"{name}.stdout.log",
                    stderr=CHUNK_LOG_DIR / f"{name}.stderr.log",
                    long_csv=CHUNK_TABLE_DIR / f"{name}.long.csv",
                    wide_csv=CHUNK_TABLE_DIR / f"{name}.wide.csv",
                    ranking_csv=CHUNK_TABLE_DIR / f"{name}.ranking.csv",
                    by_map_agent_csv=CHUNK_TABLE_DIR / f"{name}.by_map_agent.csv",
                    component_csv=CHUNK_TABLE_DIR / f"{name}.component.csv",
                    report=CHUNK_REPORT_DIR / f"{name}.report.md",
                    summary=CHUNK_REPORT_DIR / f"{name}.summary.json",
                    audit=CHUNK_REPORT_DIR / f"{name}.audit.md",
                )
            )
    return chunks


def chunk_command(chunk: Chunk) -> list[str]:
    return [
        sys.executable,
        str(PROBE_SCRIPT),
        "--scope",
        "dev",
        "--maps",
        *MAPS,
        "--agent-counts",
        str(chunk.agent),
        "--instance-ids",
        *(str(value) for value in chunk.instance_ids),
        "--output-jsonl",
        str(chunk.jsonl),
        "--command-log",
        str(chunk.commands),
        "--update-log",
        str(chunk.updates),
        "--long-csv",
        str(chunk.long_csv),
        "--wide-csv",
        str(chunk.wide_csv),
        "--ranking-csv",
        str(chunk.ranking_csv),
        "--by-map-agent-csv",
        str(chunk.by_map_agent_csv),
        "--component-ablation-csv",
        str(chunk.component_csv),
        "--report",
        str(chunk.report),
        "--summary-json",
        str(chunk.summary),
        "--audit-report",
        str(chunk.audit),
        "--overwrite",
    ]


def remove_chunk_outputs(chunks: list[Chunk]) -> None:
    for directory in [CHUNK_LOG_DIR, CHUNK_TABLE_DIR, CHUNK_REPORT_DIR, FINAL_LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    for chunk in chunks:
        for path in [
            chunk.jsonl,
            chunk.commands,
            chunk.updates,
            chunk.stdout,
            chunk.stderr,
            chunk.long_csv,
            chunk.wide_csv,
            chunk.ranking_csv,
            chunk.by_map_agent_csv,
            chunk.component_csv,
            chunk.report,
            chunk.summary,
            chunk.audit,
        ]:
            if path.exists():
                path.unlink()


def write_status(
    *,
    pending: list[Chunk],
    running: list[dict[str, Any]],
    done: list[dict[str, Any]],
    phase: str,
    final_returncode: int | None = None,
) -> None:
    payload = {
        "schema_version": "phase5p5_repair5g1_dev_chunk_status_v1",
        "phase": phase,
        "created_at_unix": time.time(),
        "pending": [chunk.name for chunk in pending],
        "running": [
            {
                "name": item["chunk"].name,
                "pid": item["process"].pid,
                "rows": count_lines(item["chunk"].jsonl),
                "commands": count_lines(item["chunk"].commands),
            }
            for item in running
        ],
        "done": done,
        "total_solver_rows": sum(count_lines(chunk.jsonl) for chunk in build_chunks()),
        "total_command_rows": sum(count_lines(chunk.commands) for chunk in build_chunks()),
        "expected_solver_rows_with_synthetic": 17040,
        "expected_command_rows": 16800,
        "final_returncode": final_returncode,
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def merge_files(chunks: list[Chunk], attr: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as target:
        for chunk in chunks:
            path = getattr(chunk, attr)
            if not path.exists():
                continue
            with path.open("r", encoding="utf-8", errors="replace") as source:
                for line in source:
                    target.write(line)


def finalize(chunks: list[Chunk]) -> int:
    merge_files(chunks, "jsonl", FINAL_JSONL)
    merge_files(chunks, "commands", FINAL_COMMANDS)
    merge_files(chunks, "updates", FINAL_UPDATES)
    stdout_path = CHUNK_LOG_DIR / "finalize.stdout.log"
    stderr_path = CHUNK_LOG_DIR / "finalize.stderr.log"
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr:
        completed = subprocess.run(
            [sys.executable, str(PROBE_SCRIPT), "--scope", "dev"],
            cwd=ROOT,
            stdout=stdout,
            stderr=stderr,
            text=True,
        )
    return completed.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--poll-sec", type=float, default=10.0)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    chunks = build_chunks()
    for directory in [CHUNK_LOG_DIR, CHUNK_TABLE_DIR, CHUNK_REPORT_DIR, FINAL_LOG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    if args.overwrite:
        remove_chunk_outputs(chunks)
        for path in [FINAL_JSONL, FINAL_COMMANDS, FINAL_UPDATES, STATUS_PATH]:
            if path.exists():
                path.unlink()

    pending = chunks[:]
    running: list[dict[str, Any]] = []
    done: list[dict[str, Any]] = []
    write_status(pending=pending, running=running, done=done, phase="starting")

    while pending or running:
        while pending and len(running) < max(1, int(args.max_workers)):
            chunk = pending.pop(0)
            stdout = chunk.stdout.open("w", encoding="utf-8")
            stderr = chunk.stderr.open("w", encoding="utf-8")
            process = subprocess.Popen(
                chunk_command(chunk),
                cwd=ROOT,
                stdout=stdout,
                stderr=stderr,
                text=True,
            )
            running.append(
                {"chunk": chunk, "process": process, "stdout": stdout, "stderr": stderr}
            )

        still_running: list[dict[str, Any]] = []
        for item in running:
            process = item["process"]
            returncode = process.poll()
            if returncode is None:
                still_running.append(item)
                continue
            item["stdout"].close()
            item["stderr"].close()
            chunk = item["chunk"]
            done.append(
                {
                    "name": chunk.name,
                    "returncode": returncode,
                    "rows": count_lines(chunk.jsonl),
                    "commands": count_lines(chunk.commands),
                    "stderr_tail": tail_text(chunk.stderr),
                }
            )
        running = still_running
        write_status(pending=pending, running=running, done=done, phase="running")

        failed = [item for item in done if int(item["returncode"]) != 0]
        if failed:
            for item in running:
                item["process"].terminate()
                item["stdout"].close()
                item["stderr"].close()
            write_status(pending=pending, running=[], done=done, phase="failed")
            return 1

        if pending or running:
            time.sleep(max(1.0, float(args.poll_sec)))

    final_returncode = finalize(chunks)
    phase = "complete" if final_returncode == 0 else "finalize_failed"
    write_status(
        pending=[],
        running=[],
        done=done,
        phase=phase,
        final_returncode=final_returncode,
    )
    return final_returncode


if __name__ == "__main__":
    raise SystemExit(main())

"""Run the Phase4C LAU checkpoint/raw-trace smoke record pipeline."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from czr004_teacher.update_sequences import audit_checkpoint_trace_join  # noqa: E402


def load_config(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to read Phase4 LAUR config") from exc
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def ensure_within_root(path: Path) -> Path:
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"refusing to remove path outside repository: {resolved}")
    return resolved


def remove_file_if_exists(path: Path) -> None:
    resolved = ensure_within_root(path)
    if resolved.exists():
        if resolved.is_dir():
            raise IsADirectoryError(resolved)
        resolved.unlink()


def remove_tree_if_exists(path: Path) -> None:
    resolved = ensure_within_root(path)
    if resolved.exists():
        if not resolved.is_dir():
            raise NotADirectoryError(resolved)
        shutil.rmtree(resolved)


def git_value(args: list[str], cwd: Path = ROOT) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except subprocess.CalledProcessError:
        return ""


def dirty_state() -> str:
    tracked = git_value(["status", "--porcelain", "--untracked-files=no"])
    untracked = git_value(["status", "--porcelain", "--untracked-files=normal"])
    has_untracked = any(line.startswith("??") for line in untracked.splitlines())
    if tracked:
        return "tracked-dirty"
    if has_untracked:
        return "tracked-clean_untracked-present"
    return "clean"


def default_run_id(config: dict[str, Any]) -> str:
    return (
        f"{config['map_name']}__a{int(config['agents'])}"
        f"__s{int(config['seed'])}__phase4c_smoke"
    )


def file_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def total_tree_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def command_string(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def write_report(
    path: Path,
    *,
    config_path: Path,
    config: dict[str, Any],
    record_command: list[str],
    audit_command: list[str],
    metadata: dict[str, str],
    completed: subprocess.CompletedProcess[str],
    audit_summary: dict[str, Any],
    checkpoint_path: Path,
    trace_path: Path,
    snapshot_root: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    status = "passed" if audit_summary["passed"] and completed.returncode == 0 else "failed"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase4C LAU Trace/Checkpoint Report\n\n")
        handle.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z')}\n")
        handle.write(f"Status: {status}\n\n")

        handle.write("## Scope\n\n")
        handle.write(
            "Phase4C records iteration-level LAU checkpoints and raw PIBT trace events. "
            "No learning/training, `cpp/ntm` change, learned restart, or runtime learned update is included.\n\n"
        )

        handle.write("## Code State\n\n")
        handle.write(f"- branch: `{metadata['branch']}`\n")
        handle.write(f"- commit: `{metadata['commit']}`\n")
        handle.write(f"- dirty: `{metadata['dirty']}`\n")
        handle.write(f"- config: `{config_path.relative_to(ROOT)}`\n\n")

        handle.write("## Smoke Run\n\n")
        handle.write(f"- map: `{config['map_name']}`\n")
        handle.write(f"- agents: {config['agents']}\n")
        handle.write(f"- seed: {config['seed']}\n")
        handle.write(f"- time_limit_sec: {config['time_limit_sec']}\n")
        handle.write(f"- max_iterations: {config['max_iterations']}\n")
        handle.write(f"- record exit code: {completed.returncode}\n\n")

        handle.write("## Commands\n\n")
        handle.write("```powershell\n")
        handle.write("powershell -ExecutionPolicy Bypass -File scripts\\build_phase4_laur_record.ps1\n")
        handle.write(command_string(record_command) + "\n")
        handle.write(command_string(audit_command) + "\n")
        handle.write("powershell -ExecutionPolicy Bypass -File scripts\\build_phase1_ltm.ps1\n")
        handle.write("powershell -ExecutionPolicy Bypass -File scripts\\phase1_ltm_smoke.ps1\n")
        handle.write("powershell -ExecutionPolicy Bypass -File scripts\\build_phase4_laur_smoke.ps1\n")
        handle.write("powershell -ExecutionPolicy Bypass -File scripts\\phase4_laur_update_smoke.ps1\n")
        handle.write("```\n\n")

        handle.write("## Outputs\n\n")
        handle.write(f"- checkpoint JSONL: `{checkpoint_path.relative_to(ROOT)}` ({file_size(checkpoint_path)} bytes)\n")
        handle.write(f"- raw trace JSONL: `{trace_path.relative_to(ROOT)}` ({file_size(trace_path)} bytes)\n")
        handle.write(
            f"- traffic snapshots: `{snapshot_root.relative_to(ROOT)}` "
            f"({total_tree_size(snapshot_root)} bytes)\n"
        )
        if config.get("audit_summary_json"):
            summary_path = resolve_repo_path(config["audit_summary_json"])
            handle.write(f"- audit summary: `{summary_path.relative_to(ROOT)}` ({file_size(summary_path)} bytes)\n")
        handle.write("\n")

        handle.write("## Audit Result\n\n")
        handle.write(f"- checkpoint rows: {audit_summary['checkpoint_rows']}\n")
        handle.write(f"- trace rows: {audit_summary['trace_rows']}\n")
        handle.write(f"- checkpoint schema errors: {audit_summary['checkpoint_schema_error_count']}\n")
        handle.write(f"- trace schema errors: {audit_summary['trace_schema_error_count']}\n")
        handle.write(f"- checkpoint-trace join errors: {audit_summary['join_error_count']}\n")
        handle.write(f"- split leakage errors: {audit_summary['split_error_count']}\n")
        handle.write(f"- audit passed: {audit_summary['passed']}\n\n")

        handle.write("## Regression Gates\n\n")
        handle.write("- Phase1 LTM smoke: pending external command run\n")
        handle.write("- Phase4B force-additive update smoke: pending external command run\n\n")

        handle.write("## Record Stdout\n\n")
        handle.write("```text\n")
        handle.write(completed.stdout.strip() + "\n")
        handle.write("```\n\n")
        if completed.stderr.strip():
            handle.write("## Record Stderr\n\n")
            handle.write("```text\n")
            handle.write(completed.stderr.strip() + "\n")
            handle.write("```\n")


def run(config_path: Path, overwrite: bool) -> int:
    config = load_config(config_path)
    if config.get("schema_version") != "phase4_laur_config_v1":
        raise ValueError("config schema_version must be phase4_laur_config_v1")

    binary = resolve_repo_path(config["binary"])
    checkpoint_path = resolve_repo_path(config["checkpoint_jsonl"])
    trace_path = resolve_repo_path(config["trace_jsonl"])
    snapshot_root = resolve_repo_path(config["traffic_snapshot_root"])
    report_path = resolve_repo_path(config["report_md"])
    summary_path = resolve_repo_path(config["audit_summary_json"])

    if overwrite:
        remove_file_if_exists(checkpoint_path)
        remove_file_if_exists(trace_path)
        remove_file_if_exists(summary_path)
        remove_file_if_exists(report_path)
        remove_tree_if_exists(snapshot_root)
    elif checkpoint_path.exists() or trace_path.exists() or snapshot_root.exists():
        raise FileExistsError("Phase4C outputs already exist; pass --overwrite")

    if not binary.exists():
        raise FileNotFoundError(f"missing Phase4C record binary: {binary}")

    metadata = {
        "branch": git_value(["branch", "--show-current"]),
        "commit": git_value(["rev-parse", "--short", "HEAD"]),
        "dirty": dirty_state(),
    }
    run_id = config.get("run_id") or default_run_id(config)
    record_command = [
        str(binary),
        "--map",
        str(resolve_repo_path(config["map"])),
        "--scen",
        str(resolve_repo_path(config["scen"])),
        "--map-name",
        str(config["map_name"]),
        "--split",
        str(config.get("split", "train")),
        "--agents",
        str(config["agents"]),
        "--seed",
        str(config["seed"]),
        "--time-limit-sec",
        str(config["time_limit_sec"]),
        "--max-iterations",
        str(config["max_iterations"]),
        "--run-id",
        str(run_id),
        "--checkpoint-jsonl",
        str(checkpoint_path),
        "--trace-jsonl",
        str(trace_path),
        "--traffic-snapshot-root",
        str(snapshot_root),
        "--checkpoint-topk-edges",
        str(config.get("checkpoint_topk_edges", 16)),
        "--branch",
        metadata["branch"],
        "--commit",
        metadata["commit"],
        "--dirty",
        metadata["dirty"],
        "--export-raw-trace",
        "--export-checkpoints",
        "--force-additive",
    ]
    completed = subprocess.run(record_command, cwd=ROOT, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(
            "Phase4C record command failed "
            f"exit={completed.returncode}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )

    audit_command = [
        sys.executable,
        str(ROOT / "src" / "czr004_teacher" / "update_sequences.py"),
        "--checkpoint-jsonl",
        str(checkpoint_path),
        "--trace-jsonl",
        str(trace_path),
        "--summary-json",
        str(summary_path),
    ]
    audit_summary = audit_checkpoint_trace_join(checkpoint_path, trace_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(audit_summary, indent=2, sort_keys=True), encoding="utf-8")
    if not audit_summary["passed"]:
        raise ValueError("Phase4C checkpoint/trace audit failed:\n" + json.dumps(audit_summary, indent=2))

    write_report(
        report_path,
        config_path=config_path,
        config=config,
        record_command=record_command,
        audit_command=audit_command,
        metadata=metadata,
        completed=completed,
        audit_summary=audit_summary,
        checkpoint_path=checkpoint_path,
        trace_path=trace_path,
        snapshot_root=snapshot_root,
    )
    print(
        "phase4_laur_record_pipeline "
        f"checkpoint_rows={audit_summary['checkpoint_rows']} "
        f"trace_rows={audit_summary['trace_rows']} report={report_path}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/phase4/laur_ltm.yaml"))
    parser.add_argument("--mode", choices=["smoke"], default="smoke")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    config_path = resolve_repo_path(args.config)
    return run(config_path, args.overwrite)


if __name__ == "__main__":
    raise SystemExit(main())

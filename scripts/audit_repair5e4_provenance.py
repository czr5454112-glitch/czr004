"""Write the Repair5E.4 provenance audit report and summary."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_RUNTIME_DIR = "artifacts/models/laur_ltm/repair5e4_closed_loop_utility_selector"
DEFAULT_RUNTIME_MANIFEST = "artifacts/models/laur_ltm/repair5e4_closed_loop_utility_selector/repair5e4_closed_loop_utility_selector_manifest.json"
DEFAULT_TRAIN_LOG_DIR = "outputs/logs/phase5p5_repair5e4_train_support"
DEFAULT_REPORT = "outputs/reports/phase5p5_repair5e4_provenance_audit_report.md"
DEFAULT_SUMMARY = "outputs/reports/phase5p5_repair5e4_provenance_audit_summary.json"

SCRIPT_PATHS = [
    "scripts/audit_repair5e4_provenance.py",
    "scripts/create_repair5e4_closed_loop_utility_table.py",
    "scripts/create_repair5e4_runtime_feature_stats_from_train_support.py",
    "scripts/audit_repair5e4_runtime_feature_stats.py",
    "scripts/create_repair5e4_closed_loop_utility_selector_runtime.py",
    "scripts/run_phase5p5_laur_diagnostic_preflight_exec.py",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(path: str | Path | None, root: Path) -> Path | None:
    if path is None:
        return None
    value = Path(path)
    return value if value.is_absolute() else root / value


def rel(path: Path | None, root: Path) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def git_value(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def sha256_file(path: Path | None) -> str | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_jsonl(log_dir: Path) -> list[Path]:
    if not log_dir.exists():
        return []
    return sorted(path for path in log_dir.glob("*.jsonl") if path.is_file())


def write_report(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("# Phase5.5 Repair5E.4 Provenance Audit\n\n")
        handle.write(f"- git_head_sha: `{summary['git_head_sha']}`\n")
        handle.write(f"- git_branch: `{summary['git_branch']}`\n")
        handle.write(f"- tracked_dirty_files_count: `{summary['tracked_dirty_files_count']}`\n")
        handle.write(f"- untracked_files_count: `{summary['untracked_files_count']}`\n")
        handle.write(f"- clean_tracked_worktree: `{summary['clean_tracked_worktree']}`\n")
        handle.write(f"- runtime_manifest_sha256: `{summary['runtime_manifest_sha256']}`\n")
        handle.write(f"- runtime_artifact_dir: `{summary['runtime_artifact_dir']}`\n\n")
        handle.write("## Tracked Dirty Files\n\n")
        for item in summary.get("tracked_dirty_files", []):
            handle.write(f"- `{item}`\n")
        handle.write("\n## Inputs\n\n")
        handle.write(f"- train_support_log_paths: `{summary.get('train_support_log_paths')}`\n")
        handle.write(f"- eval_log_paths: `{summary.get('eval_log_paths')}`\n")
        handle.write(f"- forbidden_eval_support_paths: `{summary.get('forbidden_eval_support_paths')}`\n\n")
        handle.write("## Script Hashes\n\n")
        handle.write(json.dumps(summary.get("script_sha256", {}), indent=2, sort_keys=True))
        handle.write("\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-dir", type=Path, default=Path(DEFAULT_RUNTIME_DIR))
    parser.add_argument("--runtime-manifest", type=Path, default=Path(DEFAULT_RUNTIME_MANIFEST))
    parser.add_argument("--train-log-dir", type=Path, default=Path(DEFAULT_TRAIN_LOG_DIR))
    parser.add_argument("--train-support-log-path", type=Path, action="append", default=[])
    parser.add_argument("--eval-log-path", type=Path, action="append", default=[])
    parser.add_argument("--forbidden-eval-support-path", type=Path, action="append", default=[])
    parser.add_argument("--report", type=Path, default=Path(DEFAULT_REPORT))
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_SUMMARY))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    runtime_dir = resolve_path(args.runtime_dir, root)
    runtime_manifest = resolve_path(args.runtime_manifest, root)
    train_log_dir = resolve_path(args.train_log_dir, root)
    train_paths = [path for path in (resolve_path(value, root) for value in args.train_support_log_path) if path]
    if not train_paths and train_log_dir is not None:
        train_paths = discover_jsonl(train_log_dir)
    eval_paths = [path for path in (resolve_path(value, root) for value in args.eval_log_path) if path]
    forbidden_paths = [
        path for path in (resolve_path(value, root) for value in args.forbidden_eval_support_path) if path
    ]
    status = git_value(["status", "--short"], root)
    status_lines = [line for line in status.splitlines() if line.strip()]
    tracked = [line for line in status_lines if not line.startswith("??")]
    untracked = [line for line in status_lines if line.startswith("??")]
    report = resolve_path(args.report, root)
    summary_json = resolve_path(args.summary_json, root)
    assert runtime_dir and report and summary_json
    summary = {
        "schema_version": "phase5p5_repair5e4_provenance_audit_v1",
        "created_at": datetime.now().isoformat(),
        "diagnostic_only": True,
        "phase5p5_allowed": False,
        "phase6_allowed": False,
        "git_head_sha": git_value(["rev-parse", "HEAD"], root),
        "git_branch": git_value(["branch", "--show-current"], root),
        "git_status_short": status_lines,
        "tracked_dirty_files_count": len(tracked),
        "untracked_files_count": len(untracked),
        "tracked_dirty_files": tracked,
        "untracked_files_sample": untracked[:50],
        "clean_tracked_worktree": len(tracked) == 0,
        "runtime_manifest_sha256": sha256_file(runtime_manifest),
        "runtime_artifact_dir": rel(runtime_dir, root),
        "runtime_manifest": rel(runtime_manifest, root),
        "script_sha256": {
            script: sha256_file(resolve_path(script, root)) for script in SCRIPT_PATHS
        },
        "train_support_log_paths": [rel(path, root) for path in train_paths],
        "eval_log_paths": [rel(path, root) for path in eval_paths],
        "forbidden_eval_support_paths": [rel(path, root) for path in forbidden_paths],
        "outputs": {"report": rel(report, root), "summary_json": rel(summary_json, root)},
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report, summary)
    print(json.dumps(summary["outputs"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

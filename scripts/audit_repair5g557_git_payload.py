"""Audit the staged G5.57 Git payload before commit/push.

The repository often has unrelated dirty state and large generated artifacts.
Run this after staging the intended G5.57 files and before committing.  The
audit checks that staged paths are in the expected G5.57/doc/tooling surface,
that raw logs/server bundles are not staged, that files are not oversized, and
that staged text does not look like it contains secrets.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_SECRET_SCAN_BYTES = 5 * 1024 * 1024

ALLOWED_EXACT = {
    "czr004_g557_graph_conditioned_static_theta_aaai_plan.md",
    "deep-research-report.md",
    "phase4_6_laur_ltm_codex_execution_plan.md",
}

ALLOWED_PREFIXES = (
    "outputs/reports/phase5p5_repair5g557",
    "outputs/tables/phase5p5_repair5g557",
    "artifacts/models/laur_ltm/repair5g557",
)

FORBIDDEN_PREFIXES = (
    "outputs/logs/",
    "outputs/server/",
    "outputs/tmp/",
    "artifacts/teacher/",
    "artifacts/checkpoints/",
)

FORBIDDEN_SUFFIXES = (
    ".tar",
    ".tar.gz",
    ".tgz",
    ".zip",
    ".7z",
    ".zst",
    ".pt",
    ".pth",
)

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|pwd)\b\s*[:=]\s*['\"][^'\"\n]{12,}['\"]"),
    re.compile(r"(?i)\bREPAIR5G557_SSH_PASSWORD\b\s*="),
    re.compile(r"密码\s*[:=]\s*\S{8,}"),
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paths", nargs="*", help="Audit explicit paths instead of currently staged files")
    parser.add_argument("--allow-empty", action="store_true")
    parser.add_argument("--summary-json", type=Path, default=Path("outputs/reports/phase5p5_repair5g557_git_payload_audit_summary.json"))
    return parser.parse_args(argv)


def normalize_path(path: str) -> str:
    path = path.replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    pure = PurePosixPath(path)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"unsafe staged path: {path!r}")
    return pure.as_posix()


def get_staged_paths() -> list[tuple[str, str]]:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-status", "-z"],
        cwd=ROOT,
        text=False,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", "replace"))
    fields = proc.stdout.decode("utf-8", "replace").split("\0")
    result: list[tuple[str, str]] = []
    i = 0
    while i < len(fields) and fields[i]:
        status = fields[i]
        i += 1
        if status.startswith(("R", "C")):
            if i + 1 >= len(fields):
                break
            _old = fields[i]
            new = fields[i + 1]
            i += 2
            result.append((status, normalize_path(new)))
        else:
            if i >= len(fields):
                break
            result.append((status, normalize_path(fields[i])))
            i += 1
    return result


def is_allowed_path(rel: str) -> bool:
    if rel in ALLOWED_EXACT:
        return True
    if rel.startswith("scripts/") and "repair5g557" in Path(rel).name and rel.endswith(".py"):
        return True
    if rel.startswith("tests/") and Path(rel).name.startswith("test_repair5g557") and rel.endswith(".py"):
        return True
    if any(rel.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        return True
    return False


def has_forbidden_path_shape(rel: str) -> str | None:
    low = rel.lower()
    if any(low.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
        return "raw/log/server/tmp artifact path"
    if "/logs/" in low or "/tmp/" in low or "/raw/" in low:
        return "raw/log/tmp path segment"
    if low.endswith(FORBIDDEN_SUFFIXES):
        return "archive/checkpoint-like file suffix"
    return None


def is_text_candidate(path: Path) -> bool:
    return path.suffix.lower() in {".py", ".md", ".json", ".csv", ".txt", ".yml", ".yaml"} or path.name.endswith(".jsonl")


def secret_hits(path: Path) -> list[str]:
    if not path.exists() or not path.is_file() or path.stat().st_size > MAX_SECRET_SCAN_BYTES:
        return []
    if not is_text_candidate(path):
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    hits = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            hits.append(pattern.pattern)
    return hits


def audit_paths(paths: list[tuple[str, str]]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for status, rel in paths:
        target = ROOT / rel
        path_allowed = is_allowed_path(rel)
        forbidden_reason = has_forbidden_path_shape(rel)
        checks.append({"path": rel, "status": status, "check": "allowed_path", "passed": path_allowed, "detail": "allowed" if path_allowed else "outside G5.57 payload allowlist"})
        checks.append({"path": rel, "status": status, "check": "forbidden_path_shape", "passed": forbidden_reason is None, "detail": forbidden_reason or "ok"})
        if status != "D" and target.exists():
            size = target.stat().st_size
            checks.append({"path": rel, "status": status, "check": "file_size", "passed": size <= MAX_FILE_BYTES, "detail": f"{size} <= {MAX_FILE_BYTES}"})
            hits = secret_hits(target)
            checks.append({"path": rel, "status": status, "check": "secret_scan", "passed": not hits, "detail": "; ".join(hits) if hits else "ok"})
        elif status != "D":
            checks.append({"path": rel, "status": status, "check": "file_exists", "passed": False, "detail": "staged path missing in worktree"})
    failed = [check for check in checks if not check["passed"]]
    return {
        "schema_version": "phase5p5_repair5g557_git_payload_audit_summary_v1",
        "passed": not failed,
        "path_count": len(paths),
        "failed_count": len(failed),
        "checks": checks,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    target = path if path.is_absolute() else ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.paths is None:
        paths = get_staged_paths()
    else:
        paths = [("M", normalize_path(path)) for path in args.paths]
    if not paths and not args.allow_empty:
        summary = {
            "schema_version": "phase5p5_repair5g557_git_payload_audit_summary_v1",
            "passed": False,
            "path_count": 0,
            "failed_count": 1,
            "checks": [{"check": "non_empty_payload", "passed": False, "detail": "no staged paths"}],
        }
    else:
        summary = audit_paths(paths)
    write_json(args.summary_json, summary)
    print(json.dumps({"passed": summary["passed"], "paths": summary["path_count"], "failed_count": summary["failed_count"]}, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

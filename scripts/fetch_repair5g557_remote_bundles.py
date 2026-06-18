"""Fetch and verify compact Repair5G.5.57 remote bundles.

Credentials are intentionally not stored in this script.  Pass the password via
an environment variable, stdin, SSH agent/key, or interactive prompt.  Downloaded
tarballs are kept under outputs/server by default so they stay out of Git.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = "ssh.zw1.paratera.com"
DEFAULT_PORT = 2222
DEFAULT_USERNAME = "root@ackcs-00gjh3x3"
DEFAULT_REMOTE_DIR = "/root/shared-nvme/czr004_g557_bundles"
DEFAULT_DEST = "outputs/server/phase5p5_repair5g557_bundles"

KIND_PATTERNS = {
    "compact": ("czr004_g557_compact_results_*.tar.gz",),
    "meta": ("czr004_g557_meta_logs_*.tar.gz",),
    "snapshot": (
        "czr004_g557_*_snapshot_*.tar.gz",
        "czr004_g557_*_caretaker_*.tar.gz",
    ),
}


@dataclass(frozen=True)
class RemoteBundle:
    kind: str
    mtime: float
    size_bytes: int
    remote_path: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--username", default=DEFAULT_USERNAME)
    parser.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR)
    parser.add_argument("--dest", type=Path, default=Path(DEFAULT_DEST))
    parser.add_argument("--kinds", nargs="+", choices=sorted(KIND_PATTERNS), default=["compact", "meta"])
    parser.add_argument("--password-env", default="REPAIR5G557_SSH_PASSWORD")
    parser.add_argument("--password-stdin", action="store_true")
    parser.add_argument("--identity-file", type=Path)
    parser.add_argument("--allow-missing-compact", action="store_true")
    parser.add_argument("--summary-json", type=Path, default=Path(DEFAULT_DEST) / "fetch_manifest.json")
    return parser.parse_args(argv)


def repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def read_password(args: argparse.Namespace) -> str | None:
    if args.password_stdin:
        password = sys.stdin.read().strip()
        return password or None
    env_name = str(args.password_env or "")
    if env_name and os.environ.get(env_name):
        return os.environ[env_name]
    if args.identity_file:
        return None
    if sys.stdin.isatty():
        password = getpass.getpass(f"SSH password for {args.username}@{args.host}: ")
        return password or None
    return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_find_line(kind: str, line: str) -> RemoteBundle | None:
    line = line.strip()
    if not line:
        return None
    parts = line.split("\t", 2)
    if len(parts) != 3:
        raise ValueError(f"unexpected find output: {line!r}")
    return RemoteBundle(kind=kind, mtime=float(parts[0]), size_bytes=int(parts[1]), remote_path=parts[2])


def parse_sha256_text(text: str) -> tuple[str, str]:
    first = text.strip().splitlines()[0]
    parts = first.split()
    if len(parts) < 2:
        raise ValueError(f"invalid sha256 file content: {text!r}")
    digest, filename = parts[0].lower(), parts[-1].lstrip("*")
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError(f"invalid sha256 digest: {digest!r}")
    return digest, Path(filename).name


def verify_sha256(bundle: Path, sha_path: Path) -> dict[str, Any]:
    expected, expected_name = parse_sha256_text(sha_path.read_text(encoding="utf-8"))
    actual = sha256_file(bundle)
    ok = expected == actual
    return {
        "bundle": str(bundle),
        "sha256_file": str(sha_path),
        "expected_filename": expected_name,
        "expected_sha256": expected,
        "actual_sha256": actual,
        "passed": ok,
    }


def import_paramiko():
    try:
        import paramiko  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on local env
        raise SystemExit("paramiko is required for remote bundle fetch") from exc
    return paramiko


def connect(args: argparse.Namespace):
    paramiko = import_paramiko()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs: dict[str, Any] = {
        "hostname": args.host,
        "port": args.port,
        "username": args.username,
        "timeout": 20,
        "banner_timeout": 20,
        "auth_timeout": 20,
        "look_for_keys": True,
        "allow_agent": True,
    }
    password = read_password(args)
    if password:
        connect_kwargs["password"] = password
        connect_kwargs["look_for_keys"] = False
        connect_kwargs["allow_agent"] = False
    if args.identity_file:
        connect_kwargs["key_filename"] = str(args.identity_file)
    client.connect(**connect_kwargs)
    return client


def latest_bundle(client: Any, remote_dir: str, kind: str) -> RemoteBundle | None:
    patterns = KIND_PATTERNS[kind]
    find_parts = [
        "find",
        shlex.quote(remote_dir),
        "-maxdepth",
        "1",
        "-type",
        "f",
        "\\(",
    ]
    for idx, pattern in enumerate(patterns):
        if idx:
            find_parts.append("-o")
        find_parts.extend(["-name", shlex.quote(pattern)])
    find_parts.extend(["\\)", "-printf", shlex.quote("%T@\t%s\t%p\n")])
    cmd = " ".join(find_parts) + " 2>/dev/null | sort -n | tail -1"
    _stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    if code != 0:
        raise RuntimeError(f"remote find failed code={code}: {err.strip()}")
    return parse_find_line(kind, out)


def download_bundle(sftp: Any, bundle: RemoteBundle, dest_dir: Path) -> dict[str, Any]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    local_bundle = dest_dir / Path(bundle.remote_path).name
    local_sha = dest_dir / (Path(bundle.remote_path).name + ".sha256")
    sftp.get(bundle.remote_path, str(local_bundle))
    sha_remote = bundle.remote_path + ".sha256"
    sha_downloaded = False
    try:
        sftp.get(sha_remote, str(local_sha))
        sha_downloaded = True
    except OSError:
        local_sha = Path("")
    verification = verify_sha256(local_bundle, local_sha) if sha_downloaded else {"passed": False, "reason": "missing remote sha256"}
    if sha_downloaded and not verification["passed"]:
        raise ValueError(f"sha256 mismatch for {local_bundle}")
    return {
        "kind": bundle.kind,
        "remote_path": bundle.remote_path,
        "remote_size_bytes": bundle.size_bytes,
        "remote_mtime": bundle.mtime,
        "local_path": str(local_bundle),
        "local_size_bytes": local_bundle.stat().st_size,
        "sha256": verification,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    dest = repo_path(args.dest)
    summary_path = repo_path(args.summary_json)
    client = connect(args)
    downloads: list[dict[str, Any]] = []
    missing: list[str] = []
    try:
        sftp = client.open_sftp()
        try:
            for kind in args.kinds:
                bundle = latest_bundle(client, args.remote_dir, kind)
                if bundle is None:
                    missing.append(kind)
                    continue
                downloads.append(download_bundle(sftp, bundle, dest))
        finally:
            sftp.close()
    finally:
        client.close()

    compact_missing = "compact" in missing and not args.allow_missing_compact
    summary = {
        "schema_version": "phase5p5_repair5g557_remote_bundle_fetch_manifest_v1",
        "host": args.host,
        "port": args.port,
        "username": args.username,
        "remote_dir": args.remote_dir,
        "dest": str(dest),
        "requested_kinds": args.kinds,
        "missing_kinds": missing,
        "downloads": downloads,
        "passed": not compact_missing and all(bool(item.get("sha256", {}).get("passed")) for item in downloads),
    }
    write_json(summary_path, summary)
    print(json.dumps({"passed": summary["passed"], "downloads": len(downloads), "missing": missing}, sort_keys=True))
    return 0 if summary["passed"] else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

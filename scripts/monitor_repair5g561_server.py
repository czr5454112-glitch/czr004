from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ROUND = "phase5p5_repair5g561"

DEFAULT_REPORTS = [
    f"outputs/reports/{ROUND}_server_tmux.log",
    f"outputs/reports/{ROUND}_training_progress.jsonl",
    f"outputs/reports/{ROUND}_training_summary.json",
    f"outputs/reports/{ROUND}_decision_summary.json",
    f"outputs/reports/{ROUND}_representation_truth.md",
    f"outputs/reports/{ROUND}_decision.md",
]

DEFAULT_TABLES = [
    f"outputs/tables/{ROUND}_model_variant_matrix.csv",
    f"outputs/tables/{ROUND}_ablation_matrix.csv",
    f"outputs/tables/{ROUND}_causal_sensitivity_audit.csv",
    f"outputs/tables/{ROUND}_critic_calibration.csv",
    f"outputs/tables/{ROUND}_offline_model_comparison.csv",
]


def env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def connect(args: argparse.Namespace) -> Any:
    try:
        import paramiko
    except ImportError as exc:
        raise SystemExit("paramiko is required: python -m pip install paramiko") from exc

    password = os.environ.get(args.password_env, "")
    if not password:
        raise SystemExit(f"missing password env var: {args.password_env}")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=args.host,
        port=args.port,
        username=args.user,
        password=password,
        timeout=args.timeout,
        banner_timeout=args.timeout,
        auth_timeout=args.timeout,
        look_for_keys=False,
        allow_agent=False,
    )
    return client


def exec_text(client: Any, command: str, timeout: int) -> tuple[int, str, str]:
    stdin, stdout, stderr = client.exec_command(command, get_pty=False, timeout=timeout)
    del stdin
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    return stdout.channel.recv_exit_status(), out, err


def remote_status(client: Any, args: argparse.Namespace) -> dict[str, Any]:
    workdir = shlex.quote(args.workdir)
    session = shlex.quote(args.session)
    command = f"""
set -u
printf '=== time ===\\n'
date -u +%Y-%m-%dT%H:%M:%SZ
date +%Y-%m-%dT%H:%M:%S%z
printf '=== tmux ===\\n'
tmux ls || true
printf '=== train process ===\\n'
ps -o pid,etime,pcpu,pmem,cmd -p $(pgrep -f 'train_repair5g561_goal_aware_actor.py' | head -1) 2>/dev/null || echo TRAIN_PROCESS_NOT_FOUND
printf '=== final marker ===\\n'
grep -n 'G5.61 SERVER RUN DONE' {workdir}/outputs/reports/{ROUND}_server_tmux.log || true
printf '=== progress tail ===\\n'
tail -n 20 {workdir}/outputs/reports/{ROUND}_training_progress.jsonl 2>/dev/null || echo PROGRESS_NOT_PRESENT
printf '=== model mtimes ===\\n'
ls -lh --time-style=long-iso {workdir}/artifacts/models/gcst/g561_*.pt 2>/dev/null || true
printf '=== summaries ===\\n'
python3 - <<'PY'
from pathlib import Path
import json
import time

root = Path({args.workdir!r})
for name in ["{ROUND}_training_summary.json", "{ROUND}_decision_summary.json"]:
    path = root / "outputs" / "reports" / name
    if not path.exists():
        print(name, "MISSING")
        continue
    data = json.loads(path.read_text())
    keys = [
        "decision",
        "device",
        "cuda_available",
        "cuda_used",
        "samples",
        "steps_per_variant",
        "best_variant_id",
        "best_validation_normalized_l1",
        "causal_sensitivity_passed",
        "run_elapsed_sec",
        "phase5p5_allowed",
        "phase6_allowed",
        "aaai_ready",
    ]
    compact = {{key: data.get(key) for key in keys if key in data}}
    print(name, json.dumps(compact, sort_keys=True), "mtime", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(path.stat().st_mtime)))
PY
printf '=== nvidia-smi ===\\n'
nvidia-smi || true
printf '=== attach_hint ===\\n'
printf 'tmux attach -t {session}\\n'
"""
    rc, out, err = exec_text(client, command, args.command_timeout)
    return {"returncode": rc, "stdout": out, "stderr": err}


def remote_exists(sftp: Any, path: str) -> bool:
    try:
        sftp.stat(path)
        return True
    except OSError:
        return False


def pull_one(sftp: Any, remote_root: str, local_root: Path, rel_path: str) -> dict[str, Any]:
    remote_path = remote_root.rstrip("/") + "/" + rel_path.replace("\\", "/")
    local_path = local_root / rel_path
    if not remote_exists(sftp, remote_path):
        return {"path": rel_path, "pulled": False, "reason": "missing_remote"}
    local_path.parent.mkdir(parents=True, exist_ok=True)
    sftp.get(remote_path, str(local_path))
    return {"path": rel_path, "pulled": True, "bytes": local_path.stat().st_size}


def pull_artifacts(client: Any, args: argparse.Namespace) -> list[dict[str, Any]]:
    sftp = client.open_sftp()
    try:
        pulled = []
        for rel_path in DEFAULT_REPORTS + DEFAULT_TABLES:
            pulled.append(pull_one(sftp, args.workdir, Path(args.local_root), rel_path))
        if args.pull_models:
            remote_dir = args.workdir.rstrip("/") + "/artifacts/models/gcst"
            try:
                for name in sftp.listdir(remote_dir):
                    if name.startswith("g561_") and name.endswith(".pt"):
                        rel_path = f"artifacts/models/gcst/{name}"
                        pulled.append(pull_one(sftp, args.workdir, Path(args.local_root), rel_path))
            except OSError:
                pulled.append({"path": "artifacts/models/gcst/g561_*.pt", "pulled": False, "reason": "missing_remote_dir"})
        return pulled
    finally:
        sftp.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Monitor and pull G5.61 RTX5090 tmux artifacts.")
    parser.add_argument("--host", default=env("G561_SSH_HOST", "ssh.bj8.bz1.paratera.com"))
    parser.add_argument("--port", type=int, default=int(env("G561_SSH_PORT", "2233")))
    parser.add_argument("--user", default=env("G561_SSH_USER", "root@ackcs-00gjh6i6"))
    parser.add_argument("--password-env", default="G561_SSH_PASSWORD")
    parser.add_argument("--workdir", default=env("G561_REMOTE_WORKDIR", "/root/shared-nvme/czr004_g561_7aa3ce2"))
    parser.add_argument("--session", default=env("G561_TMUX_SESSION", "g561_7aa3ce2"))
    parser.add_argument("--local-root", default=str(ROOT))
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--command-timeout", type=int, default=120)
    parser.add_argument("--pull", action="store_true")
    parser.add_argument("--pull-models", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    client = connect(args)
    try:
        status = remote_status(client, args)
        result: dict[str, Any] = {"status": status}
        if args.pull:
            result["pulled"] = pull_artifacts(client, args)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(status["stdout"], end="")
            if status["stderr"]:
                print("--- STDERR ---")
                print(status["stderr"], end="")
            if args.pull:
                print("=== pulled ===")
                for row in result["pulled"]:
                    print(json.dumps(row, sort_keys=True))
        return int(status["returncode"])
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())

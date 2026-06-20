from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


DEFAULT_REMOTE_WORKDIR = "/root/shared-nvme/czr004_g562_real_label_graph_actor"


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor the remote G5.62 tmux/server run without storing credentials.")
    parser.add_argument("--host", default=os.environ.get("G562_SSH_HOST", "ssh.bj8.bz1.paratera.com"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("G562_SSH_PORT", "2233")))
    parser.add_argument("--username", default=os.environ.get("G562_SSH_USERNAME", "root@ackcs-00gjh6i6"))
    parser.add_argument("--password-env", default="G562_SSH_PASSWORD")
    parser.add_argument("--remote-workdir", default=os.environ.get("G562_REMOTE_WORKDIR", DEFAULT_REMOTE_WORKDIR))
    parser.add_argument("--tail", type=int, default=80)
    args = parser.parse_args()

    password = os.environ.get(args.password_env)
    if not password:
        raise SystemExit(f"set {args.password_env} in the environment; credentials are not stored in this script")

    import paramiko

    cmd = f"""cd {args.remote_workdir!r}
tmux ls || true
ls -t outputs/logs/phase5p5_repair5g562_server/g562_full_*.log 2>/dev/null | head -1 | xargs -r tail -{int(args.tail)}
nvidia-smi --query-gpu=name,memory.used,utilization.gpu --format=csv,noheader || true
python - <<'PY'
import json, pathlib
for name in [
  'phase5p5_repair5g562_actor_training_summary.json',
  'phase5p5_repair5g562_critic_training_summary.json',
  'phase5p5_repair5g562_cycle1_summary.json',
  'phase5p5_repair5g562_cycle2_summary.json',
  'phase5p5_repair5g562_cycle3_summary.json',
  'phase5p5_repair5g562_decision_summary.json',
]:
    p=pathlib.Path('outputs/reports')/name
    if p.exists():
        try:
            data=json.loads(p.read_text())
        except Exception as exc:
            data={'error':str(exc)}
        print('SUMMARY', name, json.dumps(data, sort_keys=True)[:2000])
PY
"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=args.host,
        port=args.port,
        username=args.username,
        password=password,
        look_for_keys=False,
        allow_agent=False,
        timeout=20,
    )
    _stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
    print(stdout.read().decode("utf-8", "replace"))
    err = stderr.read().decode("utf-8", "replace")
    if err.strip():
        print(err)
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

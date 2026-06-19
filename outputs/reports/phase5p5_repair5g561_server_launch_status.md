# Repair5G.5.61 Server Launch Status

- local commit: `acf0ca6a48a052457ecb63795758b613d81de420`
- pushed branch: `server-code`
- requested server: RTX5090 / Paratera
- attempted alias: `paratera-rtx5090`
- attempted historical host: `ssh.zw1.paratera.com:2222`

Status: `blocked_before_tmux_launch`

The pushed G5.61 code and artifacts are available on `origin/server-code`, but this Codex session could not start the remote tmux run:

- `paratera-rtx5090` (`111.127.53.198:2222`) timed out at TCP connect.
- Historical gateway `ssh.zw1.paratera.com:2222` was reachable, but the available SSH key was not accepted and the server requested a password.

No remote training or solver tmux session was started from this session.

Recommended server command once access is restored:

```bash
mkdir -p /root/shared-nvme
cd /root/shared-nvme
git clone https://github.com/czr5454112-glitch/czr004.git czr004_g561_acf0ca6 || true
cd /root/shared-nvme/czr004_g561_acf0ca6
git fetch origin server-code
git checkout server-code
git reset --hard acf0ca6a48a052457ecb63795758b613d81de420
export REMOTE_ARTIFACT_ROOT=/root/shared-nvme/czr004_g561_remote_artifacts
export TMPDIR=/root/shared-nvme/tmp
mkdir -p "$REMOTE_ARTIFACT_ROOT" "$TMPDIR"
tmux new -d -s g561 "python scripts/audit_repair5g561_replay_truth.py && python scripts/train_repair5g561_goal_aware_actor.py --samples 96 --steps 400 --batch-size 4 --hidden-dim 64 --device auto --variants F1 F2 F4 F6 F7 && python scripts/write_repair5g561_decision.py 2>&1 | tee outputs/reports/phase5p5_repair5g561_server_tmux.log"
```

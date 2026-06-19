# Repair5G.5.61 Server Launch Status

- status: `completed_in_tmux_on_rtx5090`
- source commit: `7aa3ce2b7cee8f66152f2640c37ddbd77429a0f1`
- pushed branch: `server-code`
- instance: `ackcs-00gjh6i6`
- remote host: `ssh.bj8.bz1.paratera.com:2233`
- remote user: `root@ackcs-00gjh6i6`
- remote hostname: `p-c4d1118c7152-ackcs-00gjh6i6`
- remote workdir: `/root/shared-nvme/czr004_g561_7aa3ce2`
- tmux session: `g561_7aa3ce2`
- remote log: `/root/shared-nvme/czr004_g561_7aa3ce2/outputs/reports/phase5p5_repair5g561_server_tmux.log`
- local pulled log snapshot: `outputs/reports/phase5p5_repair5g561_server_tmux.log`

## Environment Probe

- GPU: NVIDIA GeForce RTX 5090, 32607 MiB
- driver: `580.105.08`
- CUDA: `13.0`
- PyTorch: `2.7.0a0+7c8ec84dab.nv25.03`
- `torch.cuda.is_available()`: `True`
- `/root/shared-nvme`: 200G available at launch

## Launch Command

The remote HTTPS clone hit a transient GnuTLS receive error, so the exact tracked source commit was deployed as a minimal git archive and extracted into the remote workdir. No local dirty worktree files were included.

```bash
cd /root/shared-nvme/czr004_g561_7aa3ce2
tmux new-session -d -s g561_7aa3ce2 'bash /root/shared-nvme/czr004_g561_7aa3ce2/run_g561_server.sh'
```

The tmux script runs:

```bash
python3 scripts/audit_repair5g561_replay_truth.py
python3 scripts/train_repair5g561_goal_aware_actor.py --samples 128 --steps 500 --batch-size 8 --hidden-dim 96 --device auto --variants F1 F2 F4 F6 F7
python3 scripts/write_repair5g561_decision.py
```

## Observed State

The tmux job completed at `2026-06-19T12:57:17Z` and was observed complete at `2026-06-19T12:57:41Z`.

- training process: complete
- GPU memory at completion observation: `1 MiB`
- GPU utilization at completion observation: `0%`
- training device: `cuda`
- samples: `128`
- steps per variant: `500`
- best variant: `F7`
- best validation normalized L1: `0.11238349974155426`
- completed server checkpoint rewrites:
  - `artifacts/models/gcst/g561_f1_scalar_conservative_actor_seed561.pt`
  - `artifacts/models/gcst/g561_f2_graph_only_direct_actor_seed561.pt`
  - `artifacts/models/gcst/g561_f4_graph_paired_od_actor_seed561.pt`
  - `artifacts/models/gcst/g561_f6_full_goal_aware_dual_channel_actor_seed561.pt`
  - `artifacts/models/gcst/g561_f7_full_goal_aware_actor_training_critic_seed561.pt`

The audit stage had completed inside the server log:

```json
{"actor_rows": 300, "decision": "g561_g560_replay_invalid_materialization_not_actor_failure", "exact": 165}
```

The server training summary, model comparison tables, tmux log, and checkpoints were pulled with `--pull-training-only --pull-models` so the local expanded scenario-bank and decision artifacts were not overwritten by the older remote payload.

This run predates the training-progress JSONL instrumentation added in `scripts/monitor_repair5g561_server.py` / `scripts/train_repair5g561_goal_aware_actor.py`, so `outputs/reports/phase5p5_repair5g561_training_progress.jsonl` is expected to be absent for the currently running tmux job.

Resume/status command:

```bash
ssh -p 2233 'root@ackcs-00gjh6i6'@ssh.bj8.bz1.paratera.com
tmux attach -t g561_7aa3ce2
tail -f /root/shared-nvme/czr004_g561_7aa3ce2/outputs/reports/phase5p5_repair5g561_server_tmux.log
```

Local monitor command:

```powershell
$env:G561_SSH_PASSWORD='<password>'
python scripts/monitor_repair5g561_server.py
python scripts/monitor_repair5g561_server.py --pull --pull-training-only --pull-models
```

Claims remain closed:

- `phase5p5_allowed = false`
- `phase6_allowed = false`
- `runtime_claim_allowed = false`
- `learned_runtime_policy_validated = false`
- `aaai_ready = false`

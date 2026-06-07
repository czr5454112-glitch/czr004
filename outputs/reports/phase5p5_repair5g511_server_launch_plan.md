# Phase5.5 Repair5G.5.11 Server Launch Plan

## Server

```text
instance = ackcs-00gjh3x3
host = ssh.zw1.paratera.com
port = 2222
user = root@ackcs-00gjh3x3
resource = 2 x RTX4090, 22 vCPU, 120GB RAM
os = Ubuntu 24.04
```

The raw password is not stored in this tracked report.

## Launch

Preferred command:

```bash
tmux new-session -d -s repair5g511 'cd /workspace/czr004 && bash scripts/server_run_repair5g511_full_lattice.sh'
```

The committed script runs:

```bash
bash scripts/build_phase1a_batch.sh
python scripts/run_repair5g510_executable_lattice_smoke.py --overwrite --max-workers 1
python scripts/analyze_repair5g510_lattice_adapter_parity.py
python scripts/run_repair5g510_goal_aware_dual_channel_lattice_counterfactuals.py \
  --binary build/phase1a-batch/phase1a_batch \
  --overwrite \
  --instance-ids 146..155 \
  --budgets-ms 250 500 1000 2000 \
  --max-contexts-per-group 1 \
  --max-workers 1 \
  --checkpoint-topk-edges 256 \
  --include-full-traffic
python scripts/analyze_repair5g510_lattice_counterfactual_oracle_gap.py
```

## Actual Run Notes

GitHub clone from the server failed because outbound GitHub HTTPS was unavailable. A clean local source bundle from pushed commit `44035e6` was uploaded instead.

The first server run used `--max-workers 4` and completed all 240 solver tasks, but concurrent appends corrupted the shared probe JSONL. The accepted run used `--max-workers 1`, completed cleanly, and produced 3360 valid lattice probe rows.

## Pull-back

Pulled artifacts:

```text
outputs/tables/phase5p5_repair5g510_lattice_counterfactual_results.csv
outputs/tables/phase5p5_repair5g510_lattice_counterfactual_plan.csv
outputs/reports/phase5p5_repair5g510_lattice_counterfactual_*.*
outputs/logs/phase5p5_repair5g510_lattice_counterfactuals/*.jsonl
outputs/logs/phase5p5_repair5g511/full_lattice_clean_*.log
```

The 1.45GB checkpoint JSONL is retained locally under `outputs/server/phase5p5_repair5g511_remote/` and is not committed.

#!/usr/bin/env bash
set -euo pipefail

cd /root/czr004
mkdir -p outputs/logs

session="${G559_TMUX_SESSION:-g559}"
log_path="outputs/logs/phase5p5_repair5g559_5090_tmux.log"

if tmux has-session -t "${session}" 2>/dev/null; then
  echo "tmux session already exists: ${session}"
  tmux ls
  exit 0
fi

tmux new-session -d -s "${session}" "cd /root/czr004 && bash scripts/server_start_repair5g559_5090.sh 2>&1 | tee ${log_path}"
tmux ls

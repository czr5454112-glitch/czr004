#!/usr/bin/env bash
set -euo pipefail

WORK=${WORK:-/root/shared-nvme/czr004_phase4_repair1_43633e7}
SESSION=${SESSION:-repair5b_hier_hightoken_rank_first_seed61}
cd "$WORK"

LOG_DIR=outputs/logs/repair5b_hier_hightoken_rank_first_seed61
mkdir -p "$LOG_DIR"

tmux kill-session -t "$SESSION" 2>/dev/null || true
tmux new-session -d -s "$SESSION" -c "$WORK" \
  "bash -lc 'set -o pipefail; export CUDA_VISIBLE_DEVICES=0; echo START \$(date -Is); python src/train/train_laur_attention_native.py --config configs/phase4/generated_repair5_hier_curriculum/hier_hightoken_rank_first.yaml --seed 61 2>&1 | tee $LOG_DIR/train.log; code=\${PIPESTATUS[0]}; echo \$code > $LOG_DIR/exit_code.txt; echo END \$(date -Is) code=\$code; exit \$code'"

tmux ls
tmux capture-pane -pt "$SESSION" -S -20

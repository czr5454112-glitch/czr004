#!/usr/bin/env bash
set -euo pipefail

repo_dir="${1:-/root/shared-nvme/czr004}"
session="${2:-phase4_laur_full}"
log_dir="$repo_dir/outputs/logs/phase4_laur_full"
tmux_log_dir="$repo_dir/outputs/logs/phase4_laur_full_tmux"
driver_log="$tmux_log_dir/tmux_driver.log"
pane_log="$tmux_log_dir/tmux_pane.log"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is required on the server" >&2
  exit 1
fi

if tmux has-session -t "$session" 2>/dev/null; then
  echo "tmux session already exists: $session" >&2
  echo "Attach with: tmux attach -t $session" >&2
  exit 1
fi

mkdir -p "$tmux_log_dir"
: > "$driver_log"
: > "$pane_log"

tmux new-session -d -s "$session" bash -lc "
  set -euo pipefail
  exec > >(tee -a '$driver_log') 2>&1
  cd '$repo_dir'
  echo '[phase4-full] started at' \"\$(date -Iseconds)\"
  echo '[phase4-full] repo:' \"\$(pwd)\"
  git status --short --branch
  python3 --version
  python3 - <<'PY'
import torch, yaml
print('torch', torch.__version__)
print('cuda_available', torch.cuda.is_available())
print('yaml ok')
PY
  set +e
  python3 scripts/run_phase4_laur_batch.py \
    --config configs/phase4/laur_ltm_full.yaml \
    --prepare-scenarios \
    --build \
    --overwrite
  status=\$?
  set -e
  echo '[phase4-full] batch exit code:' \"\$status\"
  echo '[phase4-full] finished at' \"\$(date -Iseconds)\"
  exit \"\$status\"
"

tmux pipe-pane -o -t "$session" "cat >> '$pane_log'"

echo "Started tmux session: $session"
echo "Attach: tmux attach -t $session"
echo "Driver log: $driver_log"
echo "Pane log: $pane_log"

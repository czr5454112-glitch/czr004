#!/usr/bin/env bash
set -euo pipefail

repo_dir="${1:-/root/shared-nvme/czr004_g556_9e083eb}"
session="${2:-g556}"
artifact_root="${3:-/root/shared-nvme/czr004_g556_remote_artifacts}"
tmux_log_dir="$repo_dir/outputs/logs/phase5p5_repair5g556_tmux"
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

mkdir -p "$tmux_log_dir" "$artifact_root"/{raw,parquet,model_checkpoints,solver_results,tmp,input_logs}
: > "$driver_log"
: > "$pane_log"

tmux new-session -d -s "$session" bash -lc "
  set -euo pipefail
  exec > >(tee -a '$driver_log') 2>&1
  cd '$repo_dir'
  export PYTHONUNBUFFERED=1
  export OMP_NUM_THREADS=\"\${OMP_NUM_THREADS:-6}\"
  export MKL_NUM_THREADS=\"\${MKL_NUM_THREADS:-6}\"
  export TMPDIR=\"\${TMPDIR:-/root/shared-nvme/tmp}\"
  export REMOTE_ARTIFACT_ROOT='$artifact_root'
  mkdir -p \"\$TMPDIR\" '$artifact_root'/raw '$artifact_root'/parquet '$artifact_root'/model_checkpoints '$artifact_root'/solver_results '$artifact_root'/tmp '$artifact_root'/input_logs

  echo '[repair5g556] started at' \"\$(date -Iseconds)\"
  echo '[repair5g556] repo:' \"\$(pwd)\"
  echo '[repair5g556] artifact_root:' \"\$REMOTE_ARTIFACT_ROOT\"
  git -c submodule.recurse=false status --short --branch --ignore-submodules=all || true
  python3 --version
  command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv || true
  python3 - <<'PY'
import torch
print('torch', torch.__version__)
print('cuda_available', torch.cuda.is_available())
print('cuda_device_count', torch.cuda.device_count())
PY

  if [ ! -x build/phase1a-batch/phase1a_batch ]; then
    bash scripts/build_phase1a_batch.sh
  fi
  if [ -x build/phase1a-batch/phase1a_batch ] && [ ! -e build/phase1a-batch/phase1a_batch.exe ]; then
    ln -s phase1a_batch build/phase1a-batch/phase1a_batch.exe
  fi

  python3 scripts/verify_repair5g556_g555_artifacts.py --overwrite
  python3 scripts/audit_repair5g556_promoted_baseline.py --overwrite
  python3 scripts/create_repair5g556_literature_model_audit.py --overwrite
  python3 scripts/create_repair5g556_unified_fixedtheta_dataset_manifest.py --overwrite
  python3 scripts/create_repair5g556_surrogate_dataset.py --overwrite
  python3 scripts/train_eval_repair5g556_ftrst_surrogate.py --device cuda --gpus 2 --epochs 80 --batch-size auto
  python3 scripts/train_eval_repair5g556_ft_transformer_baseline.py --device cuda --gpus 2 --epochs 50 --batch-size auto
  python3 scripts/train_eval_repair5g556_saint_amformer_diagnostics.py --train-row-limit 300000
  python3 scripts/train_eval_repair5g556_tabm_and_mlp_controls.py --train-row-limit 300000
  python3 scripts/train_eval_repair5g556_gbdt_controls.py --train-row-limit 300000
  python3 scripts/generate_repair5g556_surrogate_candidates.py --candidate-count 100000 --selected-count 3000 --overwrite
  python3 scripts/create_repair5g556_stage1_solver_screen_plan.py --overwrite
  python3 scripts/run_repair5g556_stage1_solver_screen.py --max-workers 24 --overwrite
  python3 scripts/analyze_repair5g556_stage1_solver_screen.py --overwrite
  python3 scripts/create_repair5g556_stage2_elite_validation_plan.py --overwrite
  python3 scripts/run_repair5g556_stage2_elite_validation.py --max-workers 24 --overwrite
  python3 scripts/analyze_repair5g556_stage2_elite_validation.py --overwrite
  python3 scripts/create_repair5g556_blind_if_warranted.py --overwrite
  python3 scripts/run_repair5g556_blind_if_warranted.py --max-workers 24 --overwrite
  python3 scripts/analyze_repair5g556_blind_if_warranted.py --overwrite
  python3 scripts/write_repair5g556_decision.py --overwrite
  command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv || true
  echo '[repair5g556] finished at' \"\$(date -Iseconds)\"
"

tmux pipe-pane -o -t "$session" "cat >> '$pane_log'"

echo "Started tmux session: $session"
echo "Attach: tmux attach -t $session"
echo "Driver log: $driver_log"
echo "Pane log: $pane_log"

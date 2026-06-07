#!/usr/bin/env bash
set -euo pipefail

export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"

LOG_DIR="outputs/logs/phase5p5_repair5g511"
mkdir -p "$LOG_DIR"

{
  echo "[repair5g511] start $(date '+%Y-%m-%d %H:%M:%S %Z')"
  command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv || true
  bash scripts/build_phase1a_batch.sh
  if [ -x build/phase1a-batch/phase1a_batch ] && [ ! -e build/phase1a-batch/phase1a_batch.exe ]; then
    ln -s phase1a_batch build/phase1a-batch/phase1a_batch.exe
  fi
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
  echo "[repair5g511] finish $(date '+%Y-%m-%d %H:%M:%S %Z')"
} 2>&1 | tee -a "$LOG_DIR/full_lattice_$(date +%Y%m%d_%H%M%S).log"

#!/usr/bin/env bash
set -uo pipefail

ROOT=/root/shared-nvme/czr004_phase4_repair1_43633e7
cd "$ROOT"

LOG=outputs/logs/phase4f_repair5_expand5000_recovery_20260528.log
mkdir -p "$(dirname "$LOG")"
exec > >(tee -a "$LOG") 2>&1

echo "[START] $(date '+%Y-%m-%dT%H:%M:%S%z') Repair5 expand5000 recovery"
df -h /root/shared-nvme || true
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits || true

run_step() {
  local name="$1"
  local script="$2"
  echo "[RECOVERY][$name][start] $(date '+%Y-%m-%dT%H:%M:%S%z') script=$script"
  if [ ! -f "$script" ]; then
    echo "[RECOVERY][$name][missing] script=$script"
    return 127
  fi
  bash "$script"
  local rc=$?
  echo "[RECOVERY][$name][done] $(date '+%Y-%m-%dT%H:%M:%S%z') rc=$rc"
  return "$rc"
}

run_step normal_token run_repair5_expand5000_waiter_20260528.sh
normal_rc=$?

run_step high_token run_repair5_expand5000_hightoken_waiter_20260528.sh
high_rc=$?

run_step followup run_repair5_expand5000_followup_waiter_20260528.sh
followup_rc=$?

echo "[DONE] $(date '+%Y-%m-%dT%H:%M:%S%z') Repair5 expand5000 recovery normal_rc=$normal_rc high_rc=$high_rc followup_rc=$followup_rc"
df -h /root/shared-nvme || true
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits || true

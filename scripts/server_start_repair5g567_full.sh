#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo"

choose_shared_root() {
  if [[ -n "${G567_SHARED_ROOT:-}" ]]; then
    echo "$G567_SHARED_ROOT"
    return 0
  fi
  for candidate in /mnt/shared /mnt/share /shared /data /workspace/shared /root/shared /root/autodl-tmp; do
    if [[ -d "$candidate" ]]; then
      echo "$candidate/repair5g567"
      return 0
    fi
  done
  echo "$repo/.g567_local_storage"
}

shared_root="$(choose_shared_root)"
mkdir -p "$shared_root"
required_kb=$(( ${G567_REQUIRE_SHARED_FREE_GB:-150} * 1024 * 1024 ))
available_kb="$(df -Pk "$shared_root" | awk 'NR==2 {print $4}')"
if [[ "$available_kb" -lt "$required_kb" ]]; then
  echo "G5.67 storage gate failed: $shared_root has ${available_kb}KB free, requires ${required_kb}KB" >&2
  df -h >&2
  exit 2
fi

export PYTHONUNBUFFERED=1
export REPAIR5G_STREAM_RESULT_CSV=1
export REPAIR5G_SKIP_AGGREGATE_JSONL=1
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export G567_OUTPUT_ROOT="${G567_OUTPUT_ROOT:-$shared_root/outputs}"
export G567_ARTIFACT_ROOT="${G567_ARTIFACT_ROOT:-$shared_root/artifacts}"
export TMPDIR="${TMPDIR:-$shared_root/tmp}"
export G567_CPU_AFFINITY="${G567_CPU_AFFINITY:-${G567_CPUSET:-0-13}}"

mkdir -p "$G567_OUTPUT_ROOT" "$G567_ARTIFACT_ROOT" "$TMPDIR" "$shared_root/logs"

if [[ ! -d external/lacam2/.git && ! -f external/lacam2/CMakeLists.txt ]]; then
  git submodule update --init --recursive external/lacam2
fi

if [[ ! -x build/phase1a-batch/phase1a_batch ]]; then
  bash scripts/build_phase1a_batch.sh
fi

if [[ -x build/phase1a-batch/phase1a_batch && ! -e build/phase1a-batch/phase1a_batch.exe ]]; then
  ln -s phase1a_batch build/phase1a-batch/phase1a_batch.exe || true
fi

run_log="$shared_root/logs/phase5p5_repair5g567_tmux_full.log"
{
  echo "===== G5.67 full run start $(date -Is) ====="
  echo "repo=$repo"
  echo "shared_root=$shared_root"
  git rev-parse HEAD
  git status --short
  git submodule status || true
  df -h
  nvidia-smi || true
} | tee "$run_log"

cmd=(
  python scripts/run_repair5g567_strict_pipeline.py
  --target-valid "${G567_TARGET_VALID:-100000}"
  --smoke-contexts "${G567_SMOKE_CONTEXTS:-128}"
  --repeat-contexts "${G567_REPEAT_CONTEXTS:-2000}"
  --repeat-count "${G567_REPEAT_COUNT:-10}"
  --development-contexts "${G567_DEVELOPMENT_CONTEXTS:-4000}"
  --blind-contexts "${G567_BLIND_CONTEXTS:-5000}"
  --group-response-rows "${G567_GROUP_RESPONSE_ROWS:-1000000}"
  --checkpoint-glob
    artifacts/models/gcst/phase5p5_repair5g565_expanded_e1_seed565.pt
    artifacts/models/gcst/phase5p5_repair5g565_expanded_e0_seed565.pt
    artifacts/models/gcst/phase5p5_repair5g565_expanded_e2_seed565.pt
  --actor-variants "${G567_ACTOR_VARIANTS:-C0,A5,A6,A7}"
  --actor-seeds "${G567_ACTOR_SEEDS:-567,568,569}"
  --actor-epochs "${G567_ACTOR_EPOCHS:-240}"
  --actor-min-epochs "${G567_ACTOR_MIN_EPOCHS:-80}"
  --actor-patience "${G567_ACTOR_PATIENCE:-30}"
  --actor-hidden-dim "${G567_ACTOR_HIDDEN_DIM:-256}"
  --actor-lr "${G567_ACTOR_LR:-0.0002}"
  --device "${G567_DEVICE:-auto}"
  --batch-size "${G567_BATCH_SIZE:-1}"
  --max-workers "${G567_MAX_WORKERS:-8}"
  --binary "${G567_SOLVER_BINARY:-build/phase1a-batch/phase1a_batch}"
  --overwrite
)

if command -v taskset >/dev/null 2>&1; then
  taskset -c "$G567_CPU_AFFINITY" "${cmd[@]}" 2>&1 | tee -a "$run_log"
else
  "${cmd[@]}" 2>&1 | tee -a "$run_log"
fi

echo "===== G5.67 full run end $(date -Is) =====" | tee -a "$run_log"

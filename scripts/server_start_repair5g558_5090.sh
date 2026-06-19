#!/usr/bin/env bash
set -euo pipefail

cd "${CZRS_REPO_ROOT:-/root/czr004}"

export PYTHONPATH="$PWD/src:$PWD/scripts:${PYTHONPATH:-}"
export REMOTE_ARTIFACT_ROOT="${REMOTE_ARTIFACT_ROOT:-/root/shared-nvme/czr004_g557_remote_artifacts}"
export G558_ARTIFACT_ROOT="${G558_ARTIFACT_ROOT:-/root/shared-nvme/czr004_g558_remote_artifacts}"
mkdir -p "$G558_ARTIFACT_ROOT" /root/shared-nvme/tmp

python -m pytest \
  -o cache_dir=/tmp/pytest-cache-czr004 \
  --basetemp=/tmp/pytest-basetemp-czr004 \
  tests/test_repair5g558_gcst.py

python scripts/run_repair5g558_5090_smoke.py \
  --contexts "${G558_CONTEXTS:-192}" \
  --candidates-per-context "${G558_CANDIDATES_PER_CONTEXT:-64}" \
  --max-nodes "${G558_MAX_NODES:-96}" \
  --max-agents "${G558_MAX_AGENTS:-64}" \
  --steps "${G558_STEPS:-140}" \
  --batch-size "${G558_BATCH_SIZE:-16}" \
  --device "${G558_DEVICE:-cuda}" \
  --smoke

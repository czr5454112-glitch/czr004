#!/usr/bin/env bash
set -euo pipefail

cd /root/czr004
mkdir -p outputs/logs /root/shared-nvme/czr004_g559_remote_artifacts/{contexts,candidates,pair_rows,replicate_aggregates,graph_tensors,traffic_tensors,checkpoints,solver_logs}

export PYTHONPATH=/root/czr004/src:/root/czr004/scripts:${PYTHONPATH:-}
export REMOTE_ARTIFACT_ROOT=/root/shared-nvme/czr004_g559_remote_artifacts
export G559_SOURCE_COMMIT="${G559_SOURCE_COMMIT:-5e90b92778b61ef386fc7b5f279b162da348a3c8}"
export REPAIR5G_SKIP_AGGREGATE_JSONL=1
export REPAIR5G_STREAM_RESULT_CSV=1

python -m pytest -q tests/test_repair5g559_gcst.py tests/test_repair5g558_gcst.py \
  -o cache_dir=/tmp/pytest-cache-czr004-g559 \
  --basetemp=/tmp/pytest-basetemp-czr004-g559

python scripts/run_repair5g559_5090.py \
  --pilot-instances "${G559_PILOT_INSTANCES:-2000}" \
  --candidates-per-instance "${G559_CANDIDATES_PER_INSTANCE:-64}" \
  --codebook-size "${G559_CODEBOOK_SIZE:-1024}" \
  --row-limit "${G559_ROW_LIMIT:-0}" \
  --max-workers "${G559_MAX_WORKERS:-1}" \
  --binary "${G559_SOLVER_BINARY:-build/phase1a-batch/phase1a_batch}"

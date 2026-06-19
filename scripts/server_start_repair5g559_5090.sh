#!/usr/bin/env bash
set -euo pipefail

cd /root/czr004
mkdir -p outputs/logs /root/shared-nvme/czr004_g559_remote_artifacts/{contexts,candidates,pair_rows,replicate_aggregates,graph_tensors,traffic_tensors,checkpoints,solver_logs}

export PYTHONPATH=/root/czr004/src:/root/czr004/scripts:${PYTHONPATH:-}
export REMOTE_ARTIFACT_ROOT=/root/shared-nvme/czr004_g559_remote_artifacts
export REPAIR5G_SKIP_AGGREGATE_JSONL=1
export REPAIR5G_STREAM_RESULT_CSV=1

python -m pytest -q tests/test_repair5g559_gcst.py tests/test_repair5g558_gcst.py \
  -o cache_dir=/tmp/pytest-cache-czr004-g559 \
  --basetemp=/tmp/pytest-basetemp-czr004-g559

python scripts/run_repair5g559_5090_smoke.py \
  --smoke \
  --pilot-instances 24 \
  --candidates-per-instance 4 \
  --codebook-size 64 \
  --row-limit 0 \
  --max-workers 1 \
  --binary build/phase1a-batch/phase1a_batch

#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

mkdir -p outputs/logs
export PYTHONUNBUFFERED=1
export REPAIR5G_STREAM_RESULT_CSV=1
export REPAIR5G_SKIP_AGGREGATE_JSONL=1

python scripts/run_repair5g566_strict_pipeline.py \
  --target-valid 6000 \
  --smoke-contexts 128 \
  --repeat-contexts 48 \
  --development-contexts 1500 \
  --blind-contexts 1000 \
  --group-response-rows 50000 \
  --checkpoint-glob \
    artifacts/models/gcst/phase5p5_repair5g565_expanded_e1_seed565.pt \
    artifacts/models/gcst/phase5p5_repair5g565_expanded_e0_seed565.pt \
    artifacts/models/gcst/phase5p5_repair5g565_expanded_e2_seed565.pt \
  --actor-variants C0,A0,A1,A2,A3,A4 \
  --actor-seeds 566,567,568 \
  --actor-epochs 100 \
  --actor-min-epochs 30 \
  --actor-patience 10 \
  --actor-hidden-dim 96 \
  --actor-lr 0.0002 \
  --device auto \
  --batch-size 8 \
  --max-workers 8 \
  --binary build/phase1a-batch/phase1a_batch \
  --overwrite

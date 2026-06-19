#!/usr/bin/env bash
set -euo pipefail
cd "${CZR004_ROOT:-/root/czr004}"
export PYTHONPATH="$PWD/src:$PWD/scripts:${PYTHONPATH:-}"
export REMOTE_ARTIFACT_ROOT="${REMOTE_ARTIFACT_ROOT:-/root/shared-nvme/czr004_g559_remote_artifacts}"
python scripts/run_repair5g559_5090.py --pilot-instances 2000 --candidates-per-instance 64 --codebook-size 1024 --row-limit 0 --max-workers 12 --seed 20260619 --binary build/phase1a-batch/phase1a_batch

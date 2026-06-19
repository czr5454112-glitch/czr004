#!/usr/bin/env bash
set -euo pipefail

cd /root/czr004
export PYTHONPATH=/root/czr004/src:/root/czr004/scripts:${PYTHONPATH:-}
export REMOTE_ARTIFACT_ROOT=/root/shared-nvme/czr004_g559_remote_artifacts

mkdir -p outputs/reports outputs/tables artifacts/models/gcst
python scripts/run_repair5g560_phase0.py \
  --root /root/czr004 \
  --hidden-dim "${G560_HIDDEN_DIM:-128}" \
  --seed "${G560_SEED:-560}" \
  --g0-steps "${G560_G0_STEPS:-6000}" \
  --g1-actor-steps "${G560_G1_ACTOR_STEPS:-5000}" \
  --g1-critic-steps "${G560_G1_CRITIC_STEPS:-3000}" \
  --replay-limit "${G560_REPLAY_LIMIT:-300}"

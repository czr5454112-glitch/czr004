#!/usr/bin/env bash
set -euo pipefail

repo_dir="${1:-/root/shared-nvme/czr004_g557}"
session="${2:-g557}"
artifact_root="${3:-/root/shared-nvme/czr004_g557_remote_artifacts}"
tmux_log_dir="$repo_dir/outputs/logs/phase5p5_repair5g557_tmux"
driver_log="$tmux_log_dir/tmux_driver.log"
pane_log="$tmux_log_dir/tmux_pane.log"
label_row_limit="${G557_LABEL_ROW_LIMIT:-0}"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is required on the server" >&2
  exit 1
fi

if tmux has-session -t "$session" 2>/dev/null; then
  echo "tmux session already exists: $session" >&2
  echo "Attach with: tmux attach -t $session" >&2
  exit 1
fi

mkdir -p "$tmux_log_dir" "$artifact_root"/{raw,features,datasets,solver_results,model_checkpoints,tmp,input_logs}
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
  export REPAIR5G_STREAM_RESULT_CSV=\"\${REPAIR5G_STREAM_RESULT_CSV:-1}\"
  export REPAIR5G_SKIP_AGGREGATE_JSONL=\"\${REPAIR5G_SKIP_AGGREGATE_JSONL:-1}\"
  mkdir -p \"\$TMPDIR\" '$artifact_root'/raw '$artifact_root'/features '$artifact_root'/datasets '$artifact_root'/solver_results '$artifact_root'/model_checkpoints '$artifact_root'/tmp '$artifact_root'/input_logs

  echo '[repair5g557] started at' \"\$(date -Iseconds)\"
  echo '[repair5g557] repo:' \"\$(pwd)\"
  echo '[repair5g557] artifact_root:' \"\$REMOTE_ARTIFACT_ROOT\"
  echo '[repair5g557] label_row_limit:' '$label_row_limit'
  git -c submodule.recurse=false status --short --branch --ignore-submodules=all || true
  python3 --version
  command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv || true
  python3 - <<'PY'
try:
    import torch
    print('torch', torch.__version__)
    print('cuda_available', torch.cuda.is_available())
    print('cuda_device_count', torch.cuda.device_count())
except Exception as exc:
    print('torch_unavailable', exc)
PY

  if [ ! -x build/phase1a-batch/phase1a_batch ]; then
    bash scripts/build_phase1a_batch.sh || true
  fi
  if [ -x build/phase1a-batch/phase1a_batch ] && [ ! -e build/phase1a-batch/phase1a_batch.exe ]; then
    ln -s phase1a_batch build/phase1a-batch/phase1a_batch.exe || true
  fi

  python3 -m py_compile \
    scripts/repair5g557_common.py \
    scripts/verify_repair5g557_g556_artifacts.py \
    scripts/create_repair5g557_literature_code_audit.py \
    scripts/create_repair5g557_context_bank.py \
    scripts/create_repair5g557_graph_feature_cache.py \
    scripts/create_repair5g557_traffic_prior_features.py \
    scripts/create_repair5g557_theta_candidate_slate.py \
    scripts/create_repair5g557_label_matrix_plan.py \
    scripts/run_repair5g557_theta_label_matrix.py \
    scripts/analyze_repair5g557_label_matrix.py \
    scripts/create_repair5g557_label_v3_dataset.py \
    scripts/train_eval_repair5g557_ttgt_outcome_model.py \
    scripts/train_eval_repair5g557_gcst_generator.py \
    scripts/train_eval_repair5g557_controls.py \
    scripts/generate_repair5g557_static_theta_policy.py \
    scripts/analyze_repair5g557_model_ablation.py \
    scripts/write_repair5g557_decision.py

  python3 scripts/verify_repair5g557_g556_artifacts.py
  if ! python3 - <<'PY'
import json
import sys
from pathlib import Path

summary_path = Path('outputs/reports/phase5p5_repair5g557_g556_verification_summary.json')
summary = json.loads(summary_path.read_text(encoding='utf-8'))
ok = (
    summary.get('decision') == 'g557_g556_baseline_verified'
    and summary.get('primary_baseline') == 'g556_c063174'
    and bool(summary.get('external_lacam2_clean'))
    and not summary.get('missing_artifacts')
)
print('[repair5g557] g556 baseline gate:', {
    'decision': summary.get('decision'),
    'primary_baseline': summary.get('primary_baseline'),
    'external_lacam2_clean': summary.get('external_lacam2_clean'),
    'missing_artifacts': summary.get('missing_artifacts'),
    'ok': ok,
})
sys.exit(0 if ok else 1)
PY
  then
    echo '[repair5g557] G5.56 baseline verification failed; stopping before G5.57 data generation'
    python3 scripts/write_repair5g557_decision.py || true
    exit 10
  fi
  python3 scripts/create_repair5g557_literature_code_audit.py --overwrite
  python3 scripts/create_repair5g557_context_bank.py --min-contexts 20000 --min-topologies 60 --overwrite
  python3 scripts/create_repair5g557_graph_feature_cache.py --overwrite
  python3 scripts/create_repair5g557_traffic_prior_features.py --overwrite

  python3 scripts/create_repair5g557_probe_traffic_plan.py --probe-contexts 1024 --overwrite
  python3 scripts/run_repair5g557_probe_traffic.py --overwrite
  python3 scripts/analyze_repair5g557_probe_traffic.py

  python3 scripts/create_repair5g557_theta_candidate_slate.py --min-candidates 20000 --overwrite
  python3 scripts/create_repair5g557_label_matrix_plan.py --contexts 12000 --candidates-per-context 512 --overwrite
  python3 scripts/run_repair5g557_theta_label_matrix.py --max-workers 24 --row-limit '$label_row_limit' --overwrite
  python3 scripts/analyze_repair5g557_label_matrix.py
  if ! python3 - <<'PY'
import json
import sys
from pathlib import Path

summary_path = Path('outputs/reports/phase5p5_repair5g557_label_matrix_summary.json')
summary = json.loads(summary_path.read_text(encoding='utf-8'))
same_context_rows = int(summary.get('same_context_candidate_rows') or 0)
total_rows = int(summary.get('total_usable_row_level_examples') or 0)
primary_rows = int(summary.get('primary_row_level_examples_vs_g556') or 0)
ok = same_context_rows >= 3_000_000 and total_rows >= 5_000_000 and primary_rows >= 3_000_000
print('[repair5g557] label matrix gate:', {
    'same_context_candidate_rows': same_context_rows,
    'total_usable_row_level_examples': total_rows,
    'primary_row_level_examples_vs_g556': primary_rows,
    'ok': ok,
})
sys.exit(0 if ok else 1)
PY
  then
    echo '[repair5g557] label matrix underpowered; writing conservative decision and stopping before model/stage replay'
    python3 scripts/write_repair5g557_decision.py || true
    exit 20
  fi
  python3 scripts/create_repair5g557_label_v3_dataset.py

  python3 scripts/train_eval_repair5g557_ttgt_outcome_model.py --device cuda --gpus 2 --epochs 120 --mixed-precision
  python3 scripts/train_eval_repair5g557_gcst_generator.py --device cuda --gpus 2 --epochs 150 --mode pre_run --codebook-residual
  python3 scripts/train_eval_repair5g557_controls.py
  python3 scripts/analyze_repair5g557_model_ablation.py

  python3 scripts/generate_repair5g557_static_theta_policy.py --freeze
  python3 scripts/create_repair5g557_stage1_execution_plan.py
  python3 scripts/run_repair5g557_stage1_execution.py --max-workers 24
  python3 scripts/analyze_repair5g557_stage1_execution.py

  python3 scripts/create_repair5g557_stage2_heldout_map_plan.py
  python3 scripts/run_repair5g557_stage2_heldout_map.py --max-workers 24
  python3 scripts/analyze_repair5g557_stage2_heldout_map.py

  python3 scripts/create_repair5g557_blind_plan.py
  python3 scripts/run_repair5g557_blind.py --max-workers 24
  python3 scripts/analyze_repair5g557_blind.py
  python3 scripts/write_repair5g557_decision.py

  python3 - <<'PY'
import glob, json
for path in glob.glob('outputs/reports/phase5p5_repair5g557_*summary.json'):
    with open(path, 'r', encoding='utf-8') as handle:
        json.load(handle)
print('g557 json summaries parse')
PY
  command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv || true
  echo '[repair5g557] finished at' \"\$(date -Iseconds)\"
"

tmux pipe-pane -o -t "$session" "cat >> '$pane_log'"

echo "Started tmux session: $session"
echo "Attach: tmux attach -t $session"
echo "Driver log: $driver_log"
echo "Pane log: $pane_log"

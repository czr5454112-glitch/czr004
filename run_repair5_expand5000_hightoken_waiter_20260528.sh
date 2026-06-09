#!/usr/bin/env bash
set -euo pipefail
ROOT=/root/shared-nvme/czr004_phase4_repair1_43633e7
SESSION_TO_WAIT=repair5_expand5000_waiter_20260528
LOG=$ROOT/outputs/logs/phase4f_repair5_expand5000_hightoken_waiter_20260528.log
mkdir -p "$ROOT/outputs/logs"
exec > >(tee -a "$LOG") 2>&1
cd "$ROOT"

echo "[START] $(date '+%Y-%m-%dT%H:%M:%S%z') Repair5 expand5000 high-token waiter"
echo "[INFO] waiting for ${SESSION_TO_WAIT} to finish if it is still alive"
while tmux has-session -t "$SESSION_TO_WAIT" 2>/dev/null; do
  date '+%Y-%m-%dT%H:%M:%S%z'
  sleep 60
done

echo "[INFO] preflight $(date '+%Y-%m-%dT%H:%M:%S%z')"
df -h /root/shared-nvme || true
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits || true

BASE_CONFIG=configs/phase4/laur_ltm_full_repair5_attention_native_expand5000_rawtrace_hightoken.yaml
CHECKPOINT=artifacts/teacher/laur/full_repair5_expand5000/checkpoints/phase4_laur_checkpoints_full_repair5_expand5000.jsonl
PROBE=artifacts/teacher/laur/full_repair5_expand5000/probes/phase4_laur_probe_full_repair5_expand5000.jsonl
TRACE=artifacts/teacher/laur/full_repair5_expand5000/traces/phase4_laur_trace_full_repair5_expand5000.jsonl.zst
DATASET=artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace_hightoken/update_labels/phase4_laur_attention_native_expand5000_rawtrace_hightoken_dataset.jsonl
AUDIT=outputs/reports/phase4f_repair5_attention_native_expand5000_rawtrace_hightoken_label_audit.json

for required in "$CHECKPOINT" "$PROBE" "$TRACE"; do
  if [ ! -s "$required" ]; then
    echo "[ERROR] required expand5000 artifact missing or empty: $required"
    exit 2
  fi
done

echo "[DATA][hightoken_labels] $(date '+%Y-%m-%dT%H:%M:%S%z')"
if [ -s "$DATASET" ] && [ -s "$AUDIT" ]; then
  echo "[DATA] existing high-token dataset/audit found; skipping label rebuild"
else
  python src/czr004_teacher/attention_native_labels_laur.py --config "$BASE_CONFIG"
fi

python - <<'PY'
import json
from pathlib import Path
p = Path('outputs/reports/phase4f_repair5_attention_native_expand5000_rawtrace_hightoken_label_audit.json')
a = json.loads(p.read_text())
keys = [
    'sample_count', 'split_counts', 'decision_distribution', 'target_rule_distribution',
    'nonadditive_opportunity_count', 'high_margin_nonadditive_opportunity_count',
    'validation_opportunity_count', 'validation_high_margin_opportunity_count',
    'split_diagnostics', 'max_edge_tokens', 'max_trace_tokens', 'passed'
]
print('HIGHTOKEN_AUDIT', json.dumps({k: a.get(k) for k in keys}, sort_keys=True))
PY

mkdir -p configs/phase4/generated_repair5_expand5000_hightoken
python - <<'PY'
import copy, yaml
from pathlib import Path
base_path = Path('configs/phase4/laur_ltm_full_repair5_attention_native_expand5000_rawtrace_hightoken.yaml')
base = yaml.safe_load(base_path.read_text())
outdir = Path('configs/phase4/generated_repair5_expand5000_hightoken')
outdir.mkdir(parents=True, exist_ok=True)

def set_path(obj, dotted, value):
    cur = obj
    parts = dotted.split('.')
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value

def make_variant(name, mods):
    cfg = copy.deepcopy(base)
    cfg['mode'] = f"phase4-full-repair5-attention-native-expand5000-rawtrace-hightoken-{name}"
    train = cfg['attention_native']['training']
    ev = cfg['attention_native']['eval']
    outputs = cfg['outputs']
    train['model_output_dir'] = f'artifacts/models/laur_ltm/full_repair5_expand5000_hightoken_{name}_seed{{seed}}'
    train['model_path'] = f'artifacts/models/laur_ltm/full_repair5_expand5000_hightoken_{name}_seed{{seed}}/laur_attention_native_hightoken_{name}_v1.pt'
    train['train_report_md'] = f'outputs/reports/phase4f_repair5_expand5000_hightoken_{name}_train_seed{{seed}}.md'
    train['train_summary_json'] = f'outputs/reports/phase4f_repair5_expand5000_hightoken_{name}_train_seed{{seed}}_summary.json'
    train['train_summary_csv'] = f'outputs/tables/phase4f_repair5_expand5000_hightoken_{name}_train_seed{{seed}}.csv'
    ev['model_path'] = train['model_path']
    ev['eval_report_md'] = f'outputs/reports/phase4f_repair5_expand5000_hightoken_{name}_eval_seed{{seed}}.md'
    ev['eval_summary_json'] = f'outputs/reports/phase4f_repair5_expand5000_hightoken_{name}_eval_seed{{seed}}_summary.json'
    ev['eval_summary_csv'] = f'outputs/tables/phase4f_repair5_expand5000_hightoken_{name}_eval_seed{{seed}}.csv'
    ev['per_map_csv'] = f'outputs/tables/phase4f_repair5_expand5000_hightoken_{name}_per_map_seed{{seed}}.csv'
    ev['confusion_csv'] = f'outputs/tables/phase4f_repair5_expand5000_hightoken_{name}_confusion_seed{{seed}}.csv'
    outputs['anti_escape_gate_summary_json'] = f'outputs/reports/phase4f_repair5_expand5000_hightoken_{name}_anti_escape_gate_seed{{seed}}_summary.json'
    outputs['anti_escape_report_md'] = f'outputs/reports/phase4f_repair5_expand5000_hightoken_{name}_anti_escape_seed{{seed}}_report.md'
    outputs['final_gate_summary_json'] = f'outputs/reports/phase4f_repair5_expand5000_hightoken_{name}_final_gate_summary.json'
    outputs['final_gate_report_md'] = f'outputs/reports/phase4f_repair5_expand5000_hightoken_{name}_final_gate_report.md'
    for dotted, value in mods.items():
        set_path(cfg, dotted, value)
    path = outdir / f'{name}.yaml'
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding='utf-8')
    print(path.as_posix())

variants = {
    'ht_mlp_target_global': {},
    'ht_linear_target_global': {
        'attention_native.model.head_hidden_dim': 0,
        'attention_native.model.head_dropout': 0.0,
    },
}
for name, mods in variants.items():
    make_variant(name, mods)
PY

seed_gate() {
  local cfg="$1"
  local seed="$2"
  python - "$cfg" "$seed" <<'PY'
import json, sys, yaml
from pathlib import Path
cfg_path = Path(sys.argv[1])
seed = int(sys.argv[2])
cfg = yaml.safe_load(cfg_path.read_text())
root = Path('.')
def resolve(text):
    p = Path(str(text).format(seed=seed))
    return p if p.is_absolute() else root / p
summary_path = resolve(cfg['attention_native']['eval']['eval_summary_json'])
anti_path = resolve(cfg['outputs']['anti_escape_gate_summary_json'])
e = json.loads(summary_path.read_text())
a = json.loads(anti_path.read_text())
v = e.get('metrics_by_split', {}).get('validation', {})
phase = e.get('phase4f_gate') or v.get('attention_native_gate') or {}
attention = v.get('attention_native_gate') or phase
recall = float(v.get('harmful_update_recall') or 0.0)
precision = float(v.get('harmful_update_precision') or 0.0)
metrics = {
    'config': cfg_path.stem,
    'seed': seed,
    'top1': v.get('rule_top1_accuracy'),
    'top3': v.get('rule_top3_accuracy'),
    'recall': recall,
    'precision': precision,
    'delta': v.get('predicted_rule_validation_mean_delta_ratio'),
    'phase4f': bool(phase.get('passed')),
    'attention': bool(attention.get('passed')),
    'safety': bool(recall >= 0.80 and precision >= 0.30),
    'anti': bool(a.get('passed')),
}
metrics['passed'] = bool(metrics['phase4f'] and metrics['attention'] and metrics['safety'] and metrics['anti'])
print('SEED_GATE', json.dumps(metrics, sort_keys=True))
raise SystemExit(0 if metrics['passed'] else 1)
PY
}

run_seed() {
  local cfg="$1"
  local seed="$2"
  echo "[VARIANT][$(basename "$cfg" .yaml)][seed${seed}][train] $(date '+%Y-%m-%dT%H:%M:%S%z')"
  python src/train/train_laur_attention_native.py --config "$cfg" --seed "$seed"
  echo "[VARIANT][$(basename "$cfg" .yaml)][seed${seed}][eval] $(date '+%Y-%m-%dT%H:%M:%S%z')"
  python src/eval/eval_laur_attention_native.py --config "$cfg" --seed "$seed"
  echo "[VARIANT][$(basename "$cfg" .yaml)][seed${seed}][anti] $(date '+%Y-%m-%dT%H:%M:%S%z')"
  python src/eval/eval_laur_anti_escape.py --config "$cfg" --seed "$seed"
  seed_gate "$cfg" "$seed"
}

for cfg in \
  configs/phase4/generated_repair5_expand5000_hightoken/ht_mlp_target_global.yaml \
  configs/phase4/generated_repair5_expand5000_hightoken/ht_linear_target_global.yaml; do
  echo "[VARIANT][$(basename "$cfg" .yaml)] seed61 screening"
  if run_seed "$cfg" 61; then
    echo "[PROMOTE][$(basename "$cfg" .yaml)] seed61 passed; running seeds 103/107"
    promoted=1
    for seed in 103 107; do
      if ! run_seed "$cfg" "$seed"; then
        promoted=0
      fi
    done
    if [ "$promoted" -eq 1 ]; then
      echo "[FINAL_GATE][$(basename "$cfg" .yaml)] $(date '+%Y-%m-%dT%H:%M:%S%z')"
      python src/eval/eval_laur_repair5_final_gate.py --config "$cfg"
    else
      echo "[NO_FINAL_GATE][$(basename "$cfg" .yaml)] promoted seed failed; Phase5.5 remains blocked"
    fi
  else
    echo "[NO_PROMOTION][$(basename "$cfg" .yaml)] seed61 failed; Phase5.5 remains blocked"
  fi
  df -h /root/shared-nvme || true
  nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits || true
done

echo "[DONE] $(date '+%Y-%m-%dT%H:%M:%S%z') Repair5 expand5000 high-token waiter"

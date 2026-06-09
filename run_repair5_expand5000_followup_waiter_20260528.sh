#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/root/shared-nvme/czr004_phase4_repair1_43633e7}
WAIT_SESSIONS=(
  repair5_expand5000_waiter_20260528
  repair5_expand5000_hightoken_waiter_20260528
)
LOG=$ROOT/outputs/logs/phase4f_repair5_expand5000_followup_waiter_20260528.log
mkdir -p "$ROOT/outputs/logs"
exec > >(tee -a "$LOG") 2>&1
cd "$ROOT"

echo "[START] $(date '+%Y-%m-%dT%H:%M:%S%z') Repair5 expand5000 follow-up waiter"
echo "[INFO] waiting for primary expand5000 and high-token queues"
while true; do
  alive=0
  for session in "${WAIT_SESSIONS[@]}"; do
    if tmux has-session -t "$session" 2>/dev/null; then
      alive=1
      echo "$(date '+%Y-%m-%dT%H:%M:%S%z') waiting for $session"
    fi
  done
  if [ "$alive" -eq 0 ]; then
    break
  fi
  sleep 300
done

echo "[INFO] preflight $(date '+%Y-%m-%dT%H:%M:%S%z')"
df -h /root/shared-nvme || true
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits || true

set +e
python - <<'PY'
import json
from pathlib import Path
passed = []
for path in Path("outputs/reports").glob("phase4f_repair5_expand5000*final_gate_summary.json"):
    try:
        data = json.loads(path.read_text())
    except Exception:
        continue
    if data.get("runtime_allowed") or data.get("phase5p5_allowed"):
        passed.append(path.as_posix())
if passed:
    print("EXISTING_FINAL_GATE_PASS", json.dumps(passed, sort_keys=True))
    raise SystemExit(10)
print("NO_EXISTING_EXPAND5000_FINAL_GATE_PASS")
PY
status=$?
set -e
if [ "$status" -eq 10 ]; then
  echo "[SKIP] an expand5000 final gate already allows Phase5.5; follow-up variants are skipped"
  exit 0
elif [ "$status" -ne 0 ]; then
  echo "[ERROR] final-gate precheck failed with status $status"
  exit "$status"
fi

DATASET=artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace/update_labels/phase4_laur_attention_native_expand5000_rawtrace_dataset.jsonl
AUDIT=outputs/reports/phase4f_repair5_attention_native_expand5000_rawtrace_label_audit.json
if [ ! -s "$DATASET" ] || [ ! -s "$AUDIT" ]; then
  echo "[ERROR] normal-token expand5000 attention-native dataset/audit missing"
  ls -lh "$DATASET" "$AUDIT" 2>/dev/null || true
  exit 2
fi

python - <<'PY'
import json
from pathlib import Path
a = json.loads(Path("outputs/reports/phase4f_repair5_attention_native_expand5000_rawtrace_label_audit.json").read_text())
keys = [
    "sample_count",
    "split_counts",
    "decision_distribution",
    "target_rule_distribution",
    "nonadditive_opportunity_count",
    "high_margin_nonadditive_opportunity_count",
    "validation_opportunity_count",
    "validation_high_margin_opportunity_count",
    "split_diagnostics",
    "passed",
]
print("FOLLOWUP_BASE_AUDIT", json.dumps({k: a.get(k) for k in keys}, sort_keys=True))
PY

mkdir -p configs/phase4/generated_repair5_expand5000_followup
python - <<'PY'
import copy
from pathlib import Path
import yaml

base_path = Path("configs/phase4/laur_ltm_full_repair5_attention_native_expand5000_rawtrace_edge.yaml")
base = yaml.safe_load(base_path.read_text())
outdir = Path("configs/phase4/generated_repair5_expand5000_followup")
outdir.mkdir(parents=True, exist_ok=True)


def set_path(obj, dotted, value):
    cur = obj
    parts = dotted.split(".")
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def make_variant(name, mods):
    cfg = copy.deepcopy(base)
    cfg["mode"] = f"phase4-full-repair5-attention-native-expand5000-followup-{name}"
    train = cfg["attention_native"]["training"]
    ev = cfg["attention_native"]["eval"]
    outputs = cfg["outputs"]
    train["model_output_dir"] = f"artifacts/models/laur_ltm/full_repair5_expand5000_followup_{name}_seed{{seed}}"
    train["model_path"] = (
        f"artifacts/models/laur_ltm/full_repair5_expand5000_followup_{name}_seed{{seed}}/"
        f"laur_attention_native_expand5000_followup_{name}_v1.pt"
    )
    train["train_report_md"] = f"outputs/reports/phase4f_repair5_expand5000_followup_{name}_train_seed{{seed}}.md"
    train["train_summary_json"] = f"outputs/reports/phase4f_repair5_expand5000_followup_{name}_train_seed{{seed}}_summary.json"
    train["train_summary_csv"] = f"outputs/tables/phase4f_repair5_expand5000_followup_{name}_train_seed{{seed}}.csv"
    ev["model_path"] = train["model_path"]
    ev["eval_report_md"] = f"outputs/reports/phase4f_repair5_expand5000_followup_{name}_eval_seed{{seed}}.md"
    ev["eval_summary_json"] = f"outputs/reports/phase4f_repair5_expand5000_followup_{name}_eval_seed{{seed}}_summary.json"
    ev["eval_summary_csv"] = f"outputs/tables/phase4f_repair5_expand5000_followup_{name}_eval_seed{{seed}}.csv"
    ev["per_map_csv"] = f"outputs/tables/phase4f_repair5_expand5000_followup_{name}_per_map_seed{{seed}}.csv"
    ev["confusion_csv"] = f"outputs/tables/phase4f_repair5_expand5000_followup_{name}_confusion_seed{{seed}}.csv"
    outputs["anti_escape_gate_summary_json"] = (
        f"outputs/reports/phase4f_repair5_expand5000_followup_{name}_anti_escape_gate_seed{{seed}}_summary.json"
    )
    outputs["anti_escape_report_md"] = (
        f"outputs/reports/phase4f_repair5_expand5000_followup_{name}_anti_escape_seed{{seed}}_report.md"
    )
    outputs["final_gate_summary_json"] = f"outputs/reports/phase4f_repair5_expand5000_followup_{name}_final_gate_summary.json"
    outputs["final_gate_report_md"] = f"outputs/reports/phase4f_repair5_expand5000_followup_{name}_final_gate_report.md"
    for dotted, value in mods.items():
        set_path(cfg, dotted, value)
    path = outdir / f"{name}.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    print(path.as_posix())


variants = {
    "ex5000_follow_pair_focal_m035_lh4": {
        "attention_native.loss.lambda_pairwise": 2.5,
        "attention_native.loss.lambda_harmful": 4.0,
        "attention_native.loss.lambda_harmful_pairwise": 3.0,
        "attention_native.loss.harmful_pairwise_margin": 0.035,
        "attention_native.loss.harmful_negative_weight": 2.0,
        "attention_native.loss.harmful_focal_gamma": 2.0,
        "attention_native.loss.lambda_anti_escape": 2.0,
        "attention_native.loss.lambda_rule_ce": 1.0,
        "attention_native.loss.lambda_rule_margin": 1.0,
    },
    "ex5000_follow_global_rank3_anti3": {
        "attention_native.loss.lambda_pairwise": 3.0,
        "attention_native.loss.lambda_harmful": 6.0,
        "attention_native.loss.lambda_harmful_pairwise": 2.0,
        "attention_native.loss.lambda_anti_escape": 3.0,
        "attention_native.loss.harmful_negative_weight": 2.0,
        "attention_native.loss.lambda_rule_ce": 1.0,
        "attention_native.loss.lambda_rule_margin": 1.0,
    },
    "ex5000_follow_target_ce2_margin1_hm3": {
        "attention_native.loss.lambda_pairwise": 2.0,
        "attention_native.loss.lambda_harmful": 8.0,
        "attention_native.loss.lambda_harmful_pairwise": 2.0,
        "attention_native.loss.lambda_anti_escape": 2.0,
        "attention_native.loss.lambda_rule_ce": 2.0,
        "attention_native.loss.lambda_rule_margin": 1.0,
        "attention_native.loss.rule_margin": 0.05,
        "attention_native.loss.rule_ce_high_margin_weight": 3.0,
        "attention_native.loss.rule_margin_high_margin_weight": 3.0,
    },
    "ex5000_follow_target_margin2_rank3_safe5": {
        "attention_native.loss.lambda_pairwise": 3.0,
        "attention_native.loss.lambda_harmful": 5.0,
        "attention_native.loss.lambda_harmful_pairwise": 2.0,
        "attention_native.loss.lambda_anti_escape": 2.0,
        "attention_native.loss.lambda_rule_ce": 0.5,
        "attention_native.loss.lambda_rule_margin": 2.0,
        "attention_native.loss.rule_margin": 0.05,
        "attention_native.loss.harmful_negative_weight": 2.0,
        "attention_native.loss.rule_ce_high_margin_weight": 4.0,
        "attention_native.loss.rule_margin_high_margin_weight": 5.0,
    },
}
for name, mods in variants.items():
    make_variant(name, mods)
PY

seed_gate() {
  local cfg="$1"
  local seed="$2"
  python - "$cfg" "$seed" <<'PY'
import json
import sys
from pathlib import Path
import yaml

cfg_path = Path(sys.argv[1])
seed = int(sys.argv[2])
cfg = yaml.safe_load(cfg_path.read_text())
root = Path(".")


def resolve(text):
    p = Path(str(text).format(seed=seed))
    return p if p.is_absolute() else root / p


summary_path = resolve(cfg["attention_native"]["eval"]["eval_summary_json"])
anti_path = resolve(cfg["outputs"]["anti_escape_gate_summary_json"])
e = json.loads(summary_path.read_text())
a = json.loads(anti_path.read_text())
v = e.get("metrics_by_split", {}).get("validation", {})
phase = e.get("phase4f_gate") or v.get("attention_native_gate") or {}
attention = v.get("attention_native_gate") or phase
recall = float(v.get("harmful_update_recall") or 0.0)
precision = float(v.get("harmful_update_precision") or 0.0)
metrics = {
    "config": cfg_path.stem,
    "seed": seed,
    "top1": v.get("rule_top1_accuracy"),
    "top3": v.get("rule_top3_accuracy"),
    "recall": recall,
    "precision": precision,
    "delta": v.get("predicted_rule_validation_mean_delta_ratio"),
    "phase4f": bool(phase.get("passed")),
    "attention": bool(attention.get("passed")),
    "safety": bool(recall >= 0.80 and precision >= 0.30),
    "anti": bool(a.get("passed")),
}
metrics["passed"] = bool(metrics["phase4f"] and metrics["attention"] and metrics["safety"] and metrics["anti"])
print("FOLLOWUP_SEED_GATE", json.dumps(metrics, sort_keys=True))
raise SystemExit(0 if metrics["passed"] else 1)
PY
}

run_seed() {
  local cfg="$1"
  local seed="$2"
  echo "[FOLLOWUP][$(basename "$cfg" .yaml)][seed${seed}][train] $(date '+%Y-%m-%dT%H:%M:%S%z')"
  python src/train/train_laur_attention_native.py --config "$cfg" --seed "$seed"
  echo "[FOLLOWUP][$(basename "$cfg" .yaml)][seed${seed}][eval] $(date '+%Y-%m-%dT%H:%M:%S%z')"
  python src/eval/eval_laur_attention_native.py --config "$cfg" --seed "$seed"
  echo "[FOLLOWUP][$(basename "$cfg" .yaml)][seed${seed}][anti] $(date '+%Y-%m-%dT%H:%M:%S%z')"
  python src/eval/eval_laur_anti_escape.py --config "$cfg" --seed "$seed"
  seed_gate "$cfg" "$seed"
}

for cfg in \
  configs/phase4/generated_repair5_expand5000_followup/ex5000_follow_pair_focal_m035_lh4.yaml \
  configs/phase4/generated_repair5_expand5000_followup/ex5000_follow_global_rank3_anti3.yaml \
  configs/phase4/generated_repair5_expand5000_followup/ex5000_follow_target_ce2_margin1_hm3.yaml \
  configs/phase4/generated_repair5_expand5000_followup/ex5000_follow_target_margin2_rank3_safe5.yaml; do
  name=$(basename "$cfg" .yaml)
  echo "[FOLLOWUP_VARIANT][$name] seed61 screening"
  if run_seed "$cfg" 61; then
    echo "[FOLLOWUP_PROMOTE][$name] seed61 passed; running seeds 103/107"
    promoted=1
    for seed in 103 107; do
      if ! run_seed "$cfg" "$seed"; then
        promoted=0
      fi
    done
    if [ "$promoted" -eq 1 ]; then
      echo "[FOLLOWUP_FINAL_GATE][$name] $(date '+%Y-%m-%dT%H:%M:%S%z')"
      python src/eval/eval_laur_repair5_final_gate.py --config "$cfg"
    else
      echo "[FOLLOWUP_NO_FINAL_GATE][$name] promoted seed failed; Phase5.5 remains blocked"
    fi
  else
    echo "[FOLLOWUP_NO_PROMOTION][$name] seed61 failed; Phase5.5 remains blocked"
  fi
  df -h /root/shared-nvme || true
  nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits || true
done

echo "[DONE] $(date '+%Y-%m-%dT%H:%M:%S%z') Repair5 expand5000 follow-up waiter"

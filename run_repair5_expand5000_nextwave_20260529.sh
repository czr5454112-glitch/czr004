#!/usr/bin/env bash
set -uo pipefail

ROOT=${ROOT:-/root/shared-nvme/czr004_phase4_repair1_43633e7}
LOG=$ROOT/outputs/logs/phase4f_repair5_expand5000_nextwave_20260529.log
SESSION_NAME=repair5_expand5000_nextwave_20260529

mkdir -p "$ROOT/outputs/logs"
exec > >(tee -a "$LOG") 2>&1
cd "$ROOT"

echo "[START] $(date '+%Y-%m-%dT%H:%M:%S%z') Repair5 expand5000 nextwave"
echo "[INFO] session=$SESSION_NAME"
df -h /root/shared-nvme || true
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits || true

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
precheck_rc=$?
if [ "$precheck_rc" -eq 10 ]; then
  echo "[SKIP] an expand5000 final gate already allows Phase5.5; nextwave variants are skipped"
  exit 0
fi
if [ "$precheck_rc" -ne 0 ]; then
  echo "[ERROR] final-gate precheck failed rc=$precheck_rc"
  exit "$precheck_rc"
fi

NORMAL_DATASET=artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace/update_labels/phase4_laur_attention_native_expand5000_rawtrace_dataset.jsonl
NORMAL_AUDIT=outputs/reports/phase4f_repair5_attention_native_expand5000_rawtrace_label_audit.json
HIGHTOKEN_DATASET=artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace_hightoken/update_labels/phase4_laur_attention_native_expand5000_rawtrace_hightoken_dataset.jsonl
HIGHTOKEN_AUDIT=outputs/reports/phase4f_repair5_attention_native_expand5000_rawtrace_hightoken_label_audit.json

for required in "$NORMAL_DATASET" "$NORMAL_AUDIT" "$HIGHTOKEN_DATASET" "$HIGHTOKEN_AUDIT"; do
  if [ ! -s "$required" ]; then
    echo "[ERROR] required expand5000 artifact missing: $required"
    exit 2
  fi
done

python - <<'PY'
import json
from pathlib import Path

for name, path in [
    ("normal", Path("outputs/reports/phase4f_repair5_attention_native_expand5000_rawtrace_label_audit.json")),
    ("hightoken", Path("outputs/reports/phase4f_repair5_attention_native_expand5000_rawtrace_hightoken_label_audit.json")),
]:
    data = json.loads(path.read_text())
    keys = [
        "passed",
        "sample_count",
        "split_counts",
        "decision_distribution",
        "target_rule_distribution",
        "validation_opportunity_count",
        "validation_high_margin_opportunity_count",
    ]
    print("NEXTWAVE_BASE_AUDIT", name, json.dumps({k: data.get(k) for k in keys}, sort_keys=True))
    if not data.get("passed"):
        raise SystemExit(f"{name} label audit failed")
PY

mkdir -p configs/phase4/generated_repair5_expand5000_nextwave
python - <<'PY'
import copy
from pathlib import Path
import yaml

BASES = {
    "normal": Path("configs/phase4/laur_ltm_full_repair5_attention_native_expand5000_rawtrace_edge.yaml"),
    "hightoken": Path("configs/phase4/laur_ltm_full_repair5_attention_native_expand5000_rawtrace_hightoken.yaml"),
}
outdir = Path("configs/phase4/generated_repair5_expand5000_nextwave")
outdir.mkdir(parents=True, exist_ok=True)


def set_path(obj, dotted, value):
    cur = obj
    parts = dotted.split(".")
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def make_variant(name, base_key, mods):
    cfg = copy.deepcopy(yaml.safe_load(BASES[base_key].read_text()))
    cfg["mode"] = f"phase4-full-repair5-attention-native-expand5000-nextwave-{name}"
    train = cfg["attention_native"]["training"]
    ev = cfg["attention_native"]["eval"]
    outputs = cfg["outputs"]

    train["model_output_dir"] = f"artifacts/models/laur_ltm/full_repair5_expand5000_nextwave_{name}_seed{{seed}}"
    train["model_path"] = (
        f"artifacts/models/laur_ltm/full_repair5_expand5000_nextwave_{name}_seed{{seed}}/"
        f"laur_attention_native_expand5000_nextwave_{name}_v1.pt"
    )
    train["train_report_md"] = f"outputs/reports/phase4f_repair5_expand5000_nextwave_{name}_train_seed{{seed}}.md"
    train["train_summary_json"] = f"outputs/reports/phase4f_repair5_expand5000_nextwave_{name}_train_seed{{seed}}_summary.json"
    train["train_summary_csv"] = f"outputs/tables/phase4f_repair5_expand5000_nextwave_{name}_train_seed{{seed}}.csv"
    ev["model_path"] = train["model_path"]
    ev["eval_report_md"] = f"outputs/reports/phase4f_repair5_expand5000_nextwave_{name}_eval_seed{{seed}}.md"
    ev["eval_summary_json"] = f"outputs/reports/phase4f_repair5_expand5000_nextwave_{name}_eval_seed{{seed}}_summary.json"
    ev["eval_summary_csv"] = f"outputs/tables/phase4f_repair5_expand5000_nextwave_{name}_eval_seed{{seed}}.csv"
    ev["per_map_csv"] = f"outputs/tables/phase4f_repair5_expand5000_nextwave_{name}_per_map_seed{{seed}}.csv"
    ev["confusion_csv"] = f"outputs/tables/phase4f_repair5_expand5000_nextwave_{name}_confusion_seed{{seed}}.csv"
    outputs["anti_escape_gate_summary_json"] = (
        f"outputs/reports/phase4f_repair5_expand5000_nextwave_{name}_anti_escape_gate_seed{{seed}}_summary.json"
    )
    outputs["anti_escape_report_md"] = (
        f"outputs/reports/phase4f_repair5_expand5000_nextwave_{name}_anti_escape_seed{{seed}}_report.md"
    )
    outputs["final_gate_summary_json"] = f"outputs/reports/phase4f_repair5_expand5000_nextwave_{name}_final_gate_summary.json"
    outputs["final_gate_report_md"] = f"outputs/reports/phase4f_repair5_expand5000_nextwave_{name}_final_gate_report.md"

    for dotted, value in mods.items():
        set_path(cfg, dotted, value)

    path = outdir / f"{name}.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    print(path.as_posix())


# MLP here means a shallow output head on top of LAU-EdgeTraceTransformer-v4,
# not the old Phase5C MLP-only baseline.
variants = {
    "hightoken_attn_mlp_head_candidate_safe_lh5": (
        "hightoken",
        {
            "attention_native.training.epochs": 240,
            "attention_native.training.batch_size": 64,
            "attention_native.eval.batch_size": 64,
            "attention_native.model.d_model": 96,
            "attention_native.model.n_layers": 2,
            "attention_native.model.head_hidden_dim": 64,
            "attention_native.model.head_dropout": 0.1,
            "attention_native.loss.lambda_pairwise": 2.5,
            "attention_native.loss.lambda_harmful": 8.0,
            "attention_native.loss.lambda_harmful_pairwise": 2.0,
            "attention_native.loss.lambda_high_margin_harmful": 4.0,
            "attention_native.loss.lambda_anti_candidate_safety": 5.0,
            "attention_native.loss.lambda_anti_escape": 4.0,
            "attention_native.loss.lambda_rule_ce": 2.0,
            "attention_native.loss.lambda_rule_margin": 1.5,
            "attention_native.loss.harmful_negative_weight": 2.5,
            "attention_native.loss.harmful_focal_gamma": 1.0,
            "attention_native.loss.rule_ce_high_margin_weight": 5.0,
            "attention_native.loss.rule_margin_high_margin_weight": 5.0,
        },
    ),
    "hightoken_attn_linear_head_candidate_safe_lh6": (
        "hightoken",
        {
            "attention_native.training.epochs": 240,
            "attention_native.training.batch_size": 64,
            "attention_native.eval.batch_size": 64,
            "attention_native.model.d_model": 96,
            "attention_native.model.n_layers": 2,
            "attention_native.model.head_hidden_dim": 0,
            "attention_native.model.head_dropout": 0.0,
            "attention_native.loss.lambda_pairwise": 3.0,
            "attention_native.loss.lambda_harmful": 10.0,
            "attention_native.loss.lambda_harmful_pairwise": 3.0,
            "attention_native.loss.lambda_high_margin_harmful": 5.0,
            "attention_native.loss.lambda_anti_candidate_safety": 6.0,
            "attention_native.loss.lambda_anti_escape": 5.0,
            "attention_native.loss.lambda_rule_ce": 1.5,
            "attention_native.loss.lambda_rule_margin": 2.0,
            "attention_native.loss.harmful_negative_weight": 2.5,
            "attention_native.loss.harmful_focal_gamma": 1.5,
            "attention_native.loss.rule_ce_high_margin_weight": 5.0,
            "attention_native.loss.rule_margin_high_margin_weight": 6.0,
        },
    ),
    "normal_attn_mlp_head_highcap_candidate_safe": (
        "normal",
        {
            "attention_native.training.epochs": 240,
            "attention_native.training.batch_size": 48,
            "attention_native.eval.batch_size": 64,
            "attention_native.model.d_model": 128,
            "attention_native.model.n_heads": 4,
            "attention_native.model.n_layers": 3,
            "attention_native.model.head_hidden_dim": 96,
            "attention_native.model.head_dropout": 0.1,
            "attention_native.loss.lambda_pairwise": 2.5,
            "attention_native.loss.lambda_harmful": 10.0,
            "attention_native.loss.lambda_harmful_pairwise": 2.5,
            "attention_native.loss.lambda_high_margin_harmful": 4.0,
            "attention_native.loss.lambda_anti_candidate_safety": 4.0,
            "attention_native.loss.lambda_anti_escape": 4.0,
            "attention_native.loss.lambda_rule_ce": 2.0,
            "attention_native.loss.lambda_rule_margin": 2.0,
            "attention_native.loss.harmful_negative_weight": 2.5,
            "attention_native.loss.harmful_focal_gamma": 1.0,
            "attention_native.loss.rule_ce_high_margin_weight": 5.0,
            "attention_native.loss.rule_margin_high_margin_weight": 5.0,
        },
    ),
    "normal_attn_linear_head_rank_safe": (
        "normal",
        {
            "attention_native.training.epochs": 220,
            "attention_native.training.batch_size": 96,
            "attention_native.eval.batch_size": 96,
            "attention_native.model.d_model": 96,
            "attention_native.model.n_layers": 2,
            "attention_native.model.head_hidden_dim": 0,
            "attention_native.model.head_dropout": 0.0,
            "attention_native.loss.lambda_pairwise": 3.0,
            "attention_native.loss.lambda_harmful": 10.0,
            "attention_native.loss.lambda_harmful_pairwise": 3.0,
            "attention_native.loss.lambda_high_margin_harmful": 5.0,
            "attention_native.loss.lambda_anti_candidate_safety": 5.0,
            "attention_native.loss.lambda_anti_escape": 5.0,
            "attention_native.loss.lambda_rule_ce": 1.0,
            "attention_native.loss.lambda_rule_margin": 1.0,
            "attention_native.loss.harmful_negative_weight": 3.0,
            "attention_native.loss.harmful_focal_gamma": 2.0,
            "attention_native.loss.rule_ce_high_margin_weight": 4.0,
            "attention_native.loss.rule_margin_high_margin_weight": 4.0,
        },
    ),
}

for name, (base_key, mods) in variants.items():
    make_variant(name, base_key, mods)
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


def resolve(text):
    return Path(str(text).format(seed=seed))


summary_path = resolve(cfg["attention_native"]["eval"]["eval_summary_json"])
anti_path = resolve(cfg["outputs"]["anti_escape_gate_summary_json"])
e = json.loads(summary_path.read_text())
a = json.loads(anti_path.read_text())
v = e.get("metrics_by_split", {}).get("validation", {})
phase = e.get("phase4f_gate")
attention = v.get("attention_native_gate")
recall = float(v.get("harmful_update_recall") or 0.0)
precision = float(v.get("harmful_update_precision") or 0.0)
missing = []
if not isinstance(phase, dict) or "passed" not in phase:
    missing.append("phase4f_gate")
if not isinstance(attention, dict) or "passed" not in attention:
    missing.append("metrics_by_split.validation.attention_native_gate")
if not isinstance(a, dict) or "passed" not in a:
    missing.append("anti_escape_gate")
metrics = {
    "config": cfg_path.stem,
    "seed": seed,
    "top1": v.get("rule_top1_accuracy"),
    "top3": v.get("rule_top3_accuracy"),
    "recall": recall,
    "precision": precision,
    "delta": v.get("predicted_rule_validation_mean_delta_ratio"),
    "phase4f": bool(isinstance(phase, dict) and phase.get("passed")),
    "attention": bool(isinstance(attention, dict) and attention.get("passed")),
    "safety": bool(recall >= 0.80 and precision >= 0.30),
    "anti": bool(isinstance(a, dict) and a.get("passed")),
    "anti_reason": a.get("reason") if isinstance(a, dict) else None,
    "missing_required_gate_fields": missing,
}
metrics["passed"] = bool(
    not missing
    and metrics["phase4f"]
    and metrics["attention"]
    and metrics["safety"]
    and metrics["anti"]
)
print("NEXTWAVE_SEED_GATE", json.dumps(metrics, sort_keys=True))
raise SystemExit(0 if metrics["passed"] else 1)
PY
}

run_seed() {
  local cfg="$1"
  local seed="$2"
  local name
  name=$(basename "$cfg" .yaml)
  echo "[NEXTWAVE][$name][seed${seed}][train] $(date '+%Y-%m-%dT%H:%M:%S%z')"
  if ! python src/train/train_laur_attention_native.py --config "$cfg" --seed "$seed"; then
    echo "[NEXTWAVE][$name][seed${seed}][train_failed]"
    return 2
  fi
  echo "[NEXTWAVE][$name][seed${seed}][eval] $(date '+%Y-%m-%dT%H:%M:%S%z')"
  if ! python src/eval/eval_laur_attention_native.py --config "$cfg" --seed "$seed"; then
    echo "[NEXTWAVE][$name][seed${seed}][eval_failed]"
    return 3
  fi
  echo "[NEXTWAVE][$name][seed${seed}][anti] $(date '+%Y-%m-%dT%H:%M:%S%z')"
  if ! python src/eval/eval_laur_anti_escape.py --config "$cfg" --seed "$seed"; then
    echo "[NEXTWAVE][$name][seed${seed}][anti_failed]"
    return 4
  fi
  seed_gate "$cfg" "$seed"
}

CONFIGS=(
  configs/phase4/generated_repair5_expand5000_nextwave/hightoken_attn_mlp_head_candidate_safe_lh5.yaml
  configs/phase4/generated_repair5_expand5000_nextwave/hightoken_attn_linear_head_candidate_safe_lh6.yaml
  configs/phase4/generated_repair5_expand5000_nextwave/normal_attn_mlp_head_highcap_candidate_safe.yaml
  configs/phase4/generated_repair5_expand5000_nextwave/normal_attn_linear_head_rank_safe.yaml
)

for cfg in "${CONFIGS[@]}"; do
  name=$(basename "$cfg" .yaml)
  echo "[NEXTWAVE_VARIANT][$name] seed61 screening"
  if run_seed "$cfg" 61; then
    echo "[NEXTWAVE_PROMOTE][$name] seed61 passed; running seeds 103/107"
    promoted=1
    for seed in 103 107; do
      if ! run_seed "$cfg" "$seed"; then
        promoted=0
      fi
    done
    if [ "$promoted" -eq 1 ]; then
      echo "[NEXTWAVE_FINAL_GATE][$name] $(date '+%Y-%m-%dT%H:%M:%S%z')"
      python src/eval/eval_laur_repair5_final_gate.py --config "$cfg" || true
    else
      echo "[NEXTWAVE_NO_FINAL_GATE][$name] promoted seed failed; Phase5.5 remains forbidden"
    fi
  else
    echo "[NEXTWAVE_NO_PROMOTION][$name] seed61 failed; Phase5.5 remains forbidden"
  fi
  df -h /root/shared-nvme || true
  nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits || true
done

echo "[DONE] $(date '+%Y-%m-%dT%H:%M:%S%z') Repair5 expand5000 nextwave"

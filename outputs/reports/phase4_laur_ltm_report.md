# Phase4 LAU-LTM Smoke Gate Report

Date: 2026-05-26 13:35:00
Status: Phase4 smoke gate passed; Phase4 pilot/full gate not yet run

## Code State

- branch: `phase4-laur-ltm`
- base commit before this report: `ddaefa2`
- scope: LAU-only first, learned restart not started

## Goal

Phase4 builds the data and training loop for learning LTM update dynamics:

```text
parameterized UpdateLTM
  -> iteration checkpoints and raw PIBT traces
  -> update-rule short probes
  -> checkpoint-level update dataset
  -> LAU-MLP-v1 training and offline eval
```

## Architecture Decision

- Model: `LAU-MLP-v1`
- Inputs: `aggregate_checkpoint_v1` checkpoint-level features
- Outputs: update-rule class, harmful-update safety logit, delta-ratio proxy
- Runtime boundary: no C++ solver integration in Phase4F
- Fallback principle: `additive_ltm` and `neutral_additive` remain fallback-compatible classes

## Data

- Dataset: `artifacts/teacher/laur/update_labels/phase4_laur_update_dataset_smoke.jsonl`
- Samples: 4
- Feature count: 36
- Rule vocabulary: `additive_ltm`, `commit_heavy`, `block_heavy`, `block_light`, `wait_light`, `wait_heavy`, `decay_095`, `decay_090`, `neutral_additive`
- Label distribution: one each for `commit_heavy`, `block_heavy`, `decay_090`, `wait_light`
- Caveat: this is a smoke dataset only; validation reuses all rows because there is no held-out validation split yet

## Validation Evidence

- Phase4B update API report: `outputs/reports/phase4_laur_ltm_update_api_report.md`
- Phase4C checkpoint/trace report: `outputs/reports/phase4_laur_trace_checkpoint_report.md`
- Phase4D probe label report: `outputs/reports/phase4_laur_probe_label_report.md`
- Phase4E update dataset report: `outputs/reports/phase4_laur_update_dataset_report.md`
- Phase4F training report: `outputs/reports/phase4_laur_ltm_train_smoke.md`
- Phase4F offline eval report: `outputs/reports/phase4_laur_ltm_offline_eval.md`

## Phase4F Outputs

- Weights: `artifacts/models/laur_ltm/smoke/laur_mlp_v1_weights.json`
- Feature stats: `artifacts/models/laur_ltm/smoke/laur_mlp_v1_feature_stats.json`
- Rule metadata: `artifacts/models/laur_ltm/smoke/laur_mlp_v1_rules.json`
- Offline eval CSV: `outputs/tables/phase4_laur_ltm_offline_eval.csv`

## Smoke Metrics

- Train script: passed end-to-end
- Eval script: passed end-to-end
- Schema validation: passed
- Exported model JSON exists: yes
- Offline metrics computed: yes
- Offline eval rule top-1 accuracy on smoke rows: 1.0
- Offline eval harmful-update F1 on smoke rows: 1.0
- Offline eval predicted-rule mean delta-ratio on smoke rows: 0.0211141060197675

These metrics only prove the pipe can overfit the tiny smoke set. They do not prove learned-update generalization.

## Gate

- Phase4 smoke gate: pass
- Phase4 pilot/full gate: not run
- Phase5 force-additive / oracle-rule integration smoke: allowed as the next engineering step
- Phase5 learned runtime performance claim: not allowed yet

Before enabling a learned C++ runtime claim, run a pilot/full dataset with held-out maps and check the Phase4F pilot thresholds:

```text
validation non-neutral checkpoints >= 50
rule_top1_accuracy >= 0.35
rule_top3_accuracy >= 0.70
harmful_update_recall >= 0.80
harmful_update_precision >= 0.30
predicted-rule validation mean delta_ratio_vs_additive >= 0.0
```

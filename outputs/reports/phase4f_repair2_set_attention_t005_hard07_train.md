# Phase4F Repair2 Rule-Attention Train Report

Date: 2026-05-27 10:17:52

## Code State

- branch: `phase4-laur-ltm`
- commit: `80a437c`
- dirty: `tracked-dirty`

## Inputs

- dataset: `C:\PROGRAMING\czr004\artifacts\teacher\laur\full_repair2\update_labels\phase4_laur_update_dataset_full_repair2_v2_t005_hard07.jsonl`
- model_path: `C:\PROGRAMING\czr004\artifacts\models\laur_ltm\full_repair2_set_attention_t005_hard07\laur_rule_attention_v2.pt`
- architecture: `LAU-SetTransformer-v2`
- epochs: `350`
- harmful_threshold: `0.1`

## Metrics

| split | samples | top1 | top3 | family top1 | harmful recall | harmful precision | mean selected delta | additive rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 2526 | 0.34560570071258906 | 0.5186064924782264 | 0.35471100554235946 | 0.9712918660287081 | 0.5503840939900587 | 0.008555193430264825 | 0.6223277909738717 |
| validation | 459 | 0.3093681917211329 | 0.5032679738562091 | 0.3224400871459695 | 0.9826589595375722 | 0.3953488372093023 | 0.008040149194424901 | 0.5337690631808278 |

## Phase4F Gate

- validation_top1: `0.3093681917211329` vs `0.35` -> fail
- validation_top3: `0.5032679738562091` vs `0.7` -> fail
- harmful_recall: `0.9826589595375722` vs `0.8` -> pass
- harmful_precision: `0.3953488372093023` vs `0.3` -> pass
- predicted_mean_delta: `0.008040149194424901` vs `0.0` -> pass
- validation_non_neutral: `359` vs `50` -> pass

Overall: `fail`

## Boundary

This is an offline Phase4F repair experiment. It does not integrate a learned model into the C++ solver runtime and does not change the Phase4F performance gate.

# Phase4F Repair2 Rule-Attention Train Report

Date: 2026-05-27 10:14:06

## Code State

- branch: `phase4-laur-ltm`
- commit: `80a437c`
- dirty: `tracked-dirty`

## Inputs

- dataset: `C:\PROGRAMING\czr004\artifacts\teacher\laur\full_repair2\update_labels\phase4_laur_update_dataset_full_repair2_v2.jsonl`
- model_path: `C:\PROGRAMING\czr004\artifacts\models\laur_ltm\full_repair2_attention\laur_rule_attention_v2.pt`
- architecture: `LAU-EdgeTraceTransformer-v2`
- epochs: `350`
- harmful_threshold: `0.1`

## Metrics

| split | samples | top1 | top3 | family top1 | harmful recall | harmful precision | mean selected delta | additive rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 2526 | 0.3147268408551069 | 0.5027711797307997 | 0.32977038796516234 | 0.9808612440191388 | 0.5352480417754569 | 0.009305530064245103 | 0.5589865399841647 |
| validation | 459 | 0.30501089324618735 | 0.5163398692810458 | 0.3093681917211329 | 0.953757225433526 | 0.4252577319587629 | 0.00701193871029579 | 0.47058823529411764 |

## Phase4F Gate

- validation_top1: `0.30501089324618735` vs `0.35` -> fail
- validation_top3: `0.5163398692810458` vs `0.7` -> fail
- harmful_recall: `0.953757225433526` vs `0.8` -> pass
- harmful_precision: `0.4252577319587629` vs `0.3` -> pass
- predicted_mean_delta: `0.00701193871029579` vs `0.0` -> pass
- validation_non_neutral: `359` vs `50` -> pass

Overall: `fail`

## Boundary

This is an offline Phase4F repair experiment. It does not integrate a learned model into the C++ solver runtime and does not change the Phase4F performance gate.

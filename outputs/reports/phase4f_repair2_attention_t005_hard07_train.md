# Phase4F Repair2 Rule-Attention Train Report

Date: 2026-05-27 10:17:56

## Code State

- branch: `phase4-laur-ltm`
- commit: `80a437c`
- dirty: `tracked-dirty`

## Inputs

- dataset: `C:\PROGRAMING\czr004\artifacts\teacher\laur\full_repair2\update_labels\phase4_laur_update_dataset_full_repair2_v2_t005_hard07.jsonl`
- model_path: `C:\PROGRAMING\czr004\artifacts\models\laur_ltm\full_repair2_attention_t005_hard07\laur_rule_attention_v2.pt`
- architecture: `LAU-EdgeTraceTransformer-v2`
- epochs: `350`
- harmful_threshold: `0.1`

## Metrics

| split | samples | top1 | top3 | family top1 | harmful recall | harmful precision | mean selected delta | additive rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 2526 | 0.2917656373713381 | 0.47624703087885983 | 0.29691211401425177 | 0.9776714513556619 | 0.528448275862069 | 0.005787708721618537 | 0.6912114014251781 |
| validation | 459 | 0.3093681917211329 | 0.4989106753812636 | 0.3115468409586057 | 0.9710982658959537 | 0.3870967741935484 | 0.004508862030381155 | 0.5947712418300654 |

## Phase4F Gate

- validation_top1: `0.3093681917211329` vs `0.35` -> fail
- validation_top3: `0.4989106753812636` vs `0.7` -> fail
- harmful_recall: `0.9710982658959537` vs `0.8` -> pass
- harmful_precision: `0.3870967741935484` vs `0.3` -> pass
- predicted_mean_delta: `0.004508862030381155` vs `0.0` -> pass
- validation_non_neutral: `359` vs `50` -> pass

Overall: `fail`

## Boundary

This is an offline Phase4F repair experiment. It does not integrate a learned model into the C++ solver runtime and does not change the Phase4F performance gate.

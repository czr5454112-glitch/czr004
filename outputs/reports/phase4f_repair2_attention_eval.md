# Phase4F Repair2 Rule-Attention Offline Evaluation

Date: 2026-05-27 10:14:23

## Code State

- branch: `phase4-laur-ltm`
- commit: `80a437c`

## Inputs

- dataset: `C:\PROGRAMING\czr004\artifacts\teacher\laur\full_repair2\update_labels\phase4_laur_update_dataset_full_repair2_v2.jsonl`
- model: `C:\PROGRAMING\czr004\artifacts\models\laur_ltm\full_repair2_attention\laur_rule_attention_v2.pt`
- architecture: `LAU-EdgeTraceTransformer-v2`

## Validation Metrics

- top1: `0.30501089324618735`
- top3: `0.5163398692810458`
- family top1: `0.3093681917211329`
- harmful recall: `0.953757225433526`
- harmful precision: `0.4252577319587629`
- mean selected delta: `0.00701193871029579`

## Phase4F Gate

- validation_top1: `0.30501089324618735` vs `0.35` -> fail
- validation_top3: `0.5163398692810458` vs `0.7` -> fail
- harmful_recall: `0.953757225433526` vs `0.8` -> pass
- harmful_precision: `0.4252577319587629` vs `0.3` -> pass
- predicted_mean_delta: `0.00701193871029579` vs `0.0` -> pass
- validation_non_neutral: `359` vs `50` -> pass

Overall: `fail`

# Phase4F Repair2 Rule-Attention Offline Evaluation

Date: 2026-05-27 10:15:53

## Code State

- branch: `phase4-laur-ltm`
- commit: `80a437c`

## Inputs

- dataset: `C:\PROGRAMING\czr004\artifacts\teacher\laur\full_repair2\update_labels\phase4_laur_update_dataset_full_repair2_v2.jsonl`
- model: `C:\PROGRAMING\czr004\artifacts\models\laur_ltm\full_repair2_set_attention\laur_rule_attention_v2.pt`
- architecture: `LAU-SetTransformer-v2`

## Validation Metrics

- top1: `0.3159041394335512`
- top3: `0.5032679738562091`
- family top1: `0.32461873638344224`
- harmful recall: `0.9710982658959537`
- harmful precision: `0.3916083916083916`
- mean selected delta: `0.004997741152722399`

## Phase4F Gate

- validation_top1: `0.3159041394335512` vs `0.35` -> fail
- validation_top3: `0.5032679738562091` vs `0.7` -> fail
- harmful_recall: `0.9710982658959537` vs `0.8` -> pass
- harmful_precision: `0.3916083916083916` vs `0.3` -> pass
- predicted_mean_delta: `0.004997741152722399` vs `0.0` -> pass
- validation_non_neutral: `359` vs `50` -> pass

Overall: `fail`

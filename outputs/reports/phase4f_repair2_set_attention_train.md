# Phase4F Repair2 Rule-Attention Train Report

Date: 2026-05-27 10:15:12

## Code State

- branch: `phase4-laur-ltm`
- commit: `80a437c`
- dirty: `tracked-dirty`

## Inputs

- dataset: `C:\PROGRAMING\czr004\artifacts\teacher\laur\full_repair2\update_labels\phase4_laur_update_dataset_full_repair2_v2.jsonl`
- model_path: `C:\PROGRAMING\czr004\artifacts\models\laur_ltm\full_repair2_set_attention\laur_rule_attention_v2.pt`
- architecture: `LAU-SetTransformer-v2`
- epochs: `350`
- harmful_threshold: `0.1`

## Metrics

| split | samples | top1 | top3 | family top1 | harmful recall | harmful precision | mean selected delta | additive rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| train | 2526 | 0.3004750593824228 | 0.4679334916864608 | 0.3079968329374505 | 0.9760765550239234 | 0.5160202360876898 | 0.006316611635744744 | 0.666270783847981 |
| validation | 459 | 0.3159041394335512 | 0.5032679738562091 | 0.32461873638344224 | 0.9710982658959537 | 0.3916083916083916 | 0.004997741152722399 | 0.5403050108932462 |

## Phase4F Gate

- validation_top1: `0.3159041394335512` vs `0.35` -> fail
- validation_top3: `0.5032679738562091` vs `0.7` -> fail
- harmful_recall: `0.9710982658959537` vs `0.8` -> pass
- harmful_precision: `0.3916083916083916` vs `0.3` -> pass
- predicted_mean_delta: `0.004997741152722399` vs `0.0` -> pass
- validation_non_neutral: `359` vs `50` -> pass

Overall: `fail`

## Boundary

This is an offline Phase4F repair experiment. It does not integrate a learned model into the C++ solver runtime and does not change the Phase4F performance gate.

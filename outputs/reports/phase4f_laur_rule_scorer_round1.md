# Phase4F Rule-Aware Scorer Experiment

Date: 2026-05-26 19:43:36 

## Code State

- branch: `phase4-laur-ltm`
- commit: `9e6479c`
- dirty: `tracked-clean_untracked-present`

## Inputs

- dataset: `C:\PROGRAMING\czr004\artifacts\teacher\laur\full\update_labels\phase4_laur_update_dataset_full.jsonl`
- probes: `C:\PROGRAMING\czr004\artifacts\teacher\laur\full\probes\phase4_laur_probe_full.jsonl`
- train pair rows: `11512`
- validation checkpoints: `458`
- neutral_threshold: `0.005`
- harmful_threshold: `0.1`

## Metrics

| split | samples | top1 | top3 | harmful recall | harmful precision | mean predicted delta | neutral rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 1439 | 0.443363446838082 | 0.788047255038221 | 0.978369384359401 | 0.5485074626865671 | 0.02604337418510064 | 0.20013898540653233 |
| validation | 458 | 0.18777292576419213 | 0.49563318777292575 | 0.8397790055248618 | 0.4887459807073955 | -0.0010369694942634368 | 0.19213973799126638 |

## Interpretation

This is an offline P4 repair experiment. It tests whether rule-aware candidate scoring is a better direction than direct hard-class checkpoint classification. It is not a Phase5 runtime integration.

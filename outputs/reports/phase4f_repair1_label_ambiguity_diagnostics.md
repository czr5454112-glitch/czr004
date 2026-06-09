# Phase4F Repair1 Label Ambiguity Diagnostics

Date: 2026-05-27 10:32:57

## Code State

- branch: `phase4-laur-ltm`
- commit: `6a36212`

## Inputs

- dataset: `artifacts/teacher/laur/full_repair1/update_labels/phase4_laur_update_dataset_full_repair1.jsonl`
- probes: `artifacts/teacher/laur/full_repair1/probes/phase4_laur_probe_full_repair1.jsonl`
- prediction CSVs:
  - `repair1_mlp`: `outputs/tables/phase4_laur_ltm_offline_eval_full_repair1.csv`
  - `repair2_edge`: `outputs/tables/phase4f_repair2_attention_eval.csv`
  - `repair2_set`: `outputs/tables/phase4f_repair2_set_attention_eval.csv`

## Validation Probe Margins

- validation samples: `459`
- best-vs-second <= 0.001: `0.21568627450980393`
- best-vs-second <= 0.0025: `0.3660130718954248`
- best-vs-second <= 0.005: `0.5337690631808278`
- best-vs-second <= 0.01: `0.7058823529411765`
- best-vs-second <= 0.02: `0.8235294117647058`

## Prediction Regret

| model split | samples | exact top1 | pred within 0.005 | pred within 0.010 | regret mean | regret q90 | predicted rank mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| repair1_mlp validation | 459 | 0.30718954248366015 | 0.44880174291938996 | 0.5751633986928104 | 0.07309220560457912 | 0.08784100770538199 | 3.4618736383442266 |
| repair2_edge validation | 459 | 0.30501089324618735 | 0.4335511982570806 | 0.5577342047930284 | 0.07706863512071478 | 0.10977145626419987 | 3.4422657952069717 |
| repair2_set validation | 459 | 0.3159041394335512 | 0.41830065359477125 | 0.5424836601307189 | 0.0790828326782882 | 0.11912088938939995 | 3.522875816993464 |

## Interpretation

This diagnostic does not lower or replace the Phase4F exact-rule gate. It checks whether failed exact predictions are still near the best observed short-probe rule by delta.

If exact top1/top3 fails while predicted regret is often small, the next repair should focus on stable target formulation and tie-aware labels before larger models. If regret remains large, the next repair should focus on richer trace features or additional train coverage.

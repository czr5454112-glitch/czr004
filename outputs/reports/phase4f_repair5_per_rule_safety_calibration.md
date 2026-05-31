# Phase4F Repair5 Per-Rule Safety Calibration

Date: 2026-05-31 09:04:55

## Code State

- branch: `phase4f5p5-stable-attention-lau`
- commit: `7bf0b0a`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- `C:\PROGRAMING\czr004\outputs\tables\phase4f_repair5_expand5000_hightoken_ht_mlp_target_global_eval_seed61.csv`

## Results

- global threshold `0.35`: recall `0.8197596795727636`, precision `0.29490874159462055`, passed `False`
- per-rule application: recall `0.829105473965287`, precision `0.3005808325266215`, passed `True`
- per-family application: recall `0.8024032042723631`, precision `0.30430379746835445`, passed `True`

## Boundary

This report calibrates offline harmful-rule probabilities only. It does not lower gates and does not allow runtime.

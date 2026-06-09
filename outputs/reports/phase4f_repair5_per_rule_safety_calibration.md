# Phase4F Repair5 Per-Rule Safety Calibration

Date: 2026-05-31 12:12:16

## Code State

- branch: `phase4f5p5-stable-attention-lau`
- commit: `70951f0`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- `C:\PROGRAMING\czr004\outputs\tables\phase4f_repair5_expand5000_postnext_hightoken_attn_mlp_head_rank_recall_perrule_eval_seed61.csv`

- calibration split: `train`
- evaluation split: `validation`

## Results

- global threshold `0.35`: recall `0.8064085447263017`, precision `0.2881679389312977`, passed `False`
- per-rule application: recall `0.7837116154873164`, precision `0.289590527873705`, passed `False`
- per-family application: recall `0.7970627503337784`, precision `0.2891041162227603`, passed `False`

## Boundary

This report calibrates offline harmful-rule probabilities only. It does not lower gates and does not allow runtime.

# Phase4F Repair5 Attention-Native Label Audit

Date: 2026-05-27 19:35:16

## Code State

- branch: `phase4f5p5-stable-attention-lau`
- commit: `a024b0e`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- checkpoints: `C:\PROGRAMING\czr004\artifacts\teacher\laur\full_repair1\checkpoints\phase4_laur_checkpoints_full_repair1.jsonl`
- probes: `C:\PROGRAMING\czr004\artifacts\teacher\laur\full_repair1\probes\phase4_laur_probe_full_repair1.jsonl`
- raw trace: `C:\PROGRAMING\czr004\artifacts\teacher\laur\full_repair1\traces\phase4_laur_trace_full_repair1.jsonl.zst`
- output: `C:\PROGRAMING\czr004\artifacts\teacher\laur\full_repair5_attention_native\update_labels\phase4_laur_attention_native_dataset.jsonl`

## Audit

- samples: `2985`
- schema errors: `0`
- split leakage errors: `0`
- decisions: `{'defer_ltm': 1000, 'use_nonadditive': 1985}`
- target rules: `{'None': 110, 'block_heavy': 623, 'block_light': 319, 'commit_heavy': 592, 'decay_090': 192, 'decay_095': 308, 'wait_heavy': 323, 'wait_light': 518}`
- defer reasons: `{'additive_is_best_safe': 158, 'all_nonadditive_unsafe': 110, 'ambiguous_low_margin': 732}`
- opportunity count: `1985`
- high-margin opportunity count: `1412`
- validation opportunity count: `293`
- validation high-margin opportunity count: `185`
- missing harmful coverage: `0`
- passed: `True`

## Boundary

This dataset is Repair5 attention-native supervision for LAUR/LAU UpdateLTM only. `defer_ltm` is a meta-decision and is not an executable update rule; runtime maps it to additive LTM only after offline gates pass.

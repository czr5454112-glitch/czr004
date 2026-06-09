# Phase4F Repair5 Attention-Native Label Audit

Date: 2026-05-28 17:46:44

## Code State

- branch: `phase4-laur-ltm`
- commit: `43633e7`
- dirty: `tracked-dirty_untracked-present`

## Inputs

- checkpoints: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_expand5000/checkpoints/phase4_laur_checkpoints_full_repair5_expand5000.jsonl`
- probes: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_expand5000/probes/phase4_laur_probe_full_repair5_expand5000.jsonl`
- raw trace: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_expand5000/traces/phase4_laur_trace_full_repair5_expand5000.jsonl.zst`
- output: `/root/shared-nvme/czr004_phase4_repair1_43633e7/artifacts/teacher/laur/full_repair5_attention_native_expand5000_rawtrace_hightoken/update_labels/phase4_laur_attention_native_expand5000_rawtrace_hightoken_dataset.jsonl`

## Audit

- samples: `4956`
- schema errors: `0`
- split leakage errors: `0`
- decisions: `{'defer_ltm': 1682, 'use_nonadditive': 3274}`
- target rules: `{'None': 168, 'block_heavy': 1037, 'block_light': 531, 'commit_heavy': 977, 'decay_090': 315, 'decay_095': 511, 'wait_heavy': 561, 'wait_light': 856}`
- defer reasons: `{'additive_is_best_safe': 258, 'all_nonadditive_unsafe': 168, 'ambiguous_low_margin': 1256}`
- opportunity count: `3274`
- high-margin opportunity count: `2325`
- validation opportunity count: `483`
- validation high-margin opportunity count: `310`
- missing harmful coverage: `0`
- passed: `True`

## Boundary

This dataset is Repair5 attention-native supervision for LAUR/LAU UpdateLTM only. `defer_ltm` is a meta-decision and is not an executable update rule; runtime maps it to additive LTM only after offline gates pass.

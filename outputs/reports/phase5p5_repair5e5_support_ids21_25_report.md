# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-06-01 12:48:42

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_support_ids21_25\phase5p5_repair5e5_support_ids21_25.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_support_ids21_25\phase5p5_repair5e5_support_ids21_25_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_support_ids21_25\phase5p5_repair5e5_support_ids21_25_commands.jsonl`

## Provenance

- git branch: `phase4f5p5-stable-attention-lau`
- git commit: `db0f494`
- git dirty state: `tracked-dirty_untracked-present`
- clean tracked worktree: `False`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agent_counts: `[50, 100]`
- instances_per_setting: `3`
- instance_ids: `[21, 22, 23, 24, 25]`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`
- methods: `['lacam_star_ltm', 'always_additive_defer', 'oracle_teacher_forced_best_safe_update_static_proxy']`
- support_methods: `['oracle_probe_static_block_heavy', 'oracle_probe_static_block_light', 'oracle_probe_static_commit_heavy', 'oracle_probe_static_decay_090', 'oracle_probe_static_decay_095', 'oracle_probe_static_wait_heavy', 'oracle_probe_static_wait_light']`

## Runtime Availability

- `repair5d_native_composite_export`: `not_feasible_current_cxx_runtime_accepts_single_mlp_runtime_only_distilled_bridge_used`
- `oracle_teacher_forced_best_safe_update_full_hook`: `full_per_update_teacher_force_hook_not_available_static_rule_probe_proxy_executed`
- `repair3_runtime_export`: `existing_runtime_dir`
- `repair5d_spec`: `available`
- `repair5d_runtime_distill`: `available`
- `repair5e_ood_guard_runtime`: `available`
- `repair5e2_guarded_oracle_aligned_selector_runtime`: `available`
- `repair5e3_split_guarded_selector_runtime`: `available`
- `repair5e3_e2_shuffled_support_diagnostic_runtime`: `available`
- `repair5e4_closed_loop_utility_selector_runtime`: `available`
- `repair5e4_closed_loop_utility_selector_shuffled_labels_runtime`: `available`
- `repair5e4_calibrated_guard_only_on_e3_split_runtime`: `available`
- `repair5e5_crossfold_utility_reranker_runtime`: `missing_runtime_dir_or_required_files`
- `repair5e5_crossfold_utility_reranker_shuffled_labels_runtime`: `missing_runtime_dir_or_required_files`
- `repair5e5_crossfold_utility_reranker_loose_threshold_runtime`: `missing_runtime_dir_or_required_files`
- `repair5e5_crossfold_utility_reranker_strict_threshold_runtime`: `missing_runtime_dir_or_required_files`

## Group Summary

| map | agents | method | runs | success | ratio | d ratio | expanded | d expanded | TTFS ms | d TTFS | pibt | fallback | non-additive | overhead ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| maze-32-32-4 | 50 | always_additive_defer | 5 | 1.000000 | 1.185242544024 | 0.0 | 435.6 | 0.0 | 188.2 | 1.1999999999999886 | 21575.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.185242544024 | None | 435.6 | None | 187.0 | None | 21575.4 | None | None | 0.0 |
| maze-32-32-4 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.163585877162 | -0.021656666861999962 | 426.8 | -8.800000000000011 | 190.4 | 3.4000000000000057 | 21137.8 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 100 | always_additive_defer | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 395.0 | -0.8000000000000114 | 62993.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.259743057366 | None | 537.6 | None | 395.8 | None | 62993.4 | None | None | 0.0 |
| maze-32-32-4 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.246184685418 | -0.013558371947999914 | 528.2 | -9.399999999999977 | 395.8 | 0.0 | 62653.0 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 50 | always_additive_defer | 5 | 1.000000 | 1.152551037608 | 0.0 | 229.4 | 0.0 | 160.0 | -5.400000000000006 | 14588.4 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.152551037608 | None | 229.4 | None | 165.4 | None | 14588.4 | None | None | 0.0 |
| random-32-32-20 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.148166444848 | -0.004384592759999917 | 204.4 | -25.0 | 162.0 | -3.4000000000000057 | 10223.2 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 100 | always_additive_defer | 5 | 1.000000 | 1.1863313626698 | 0.0 | 271.4 | 0.0 | 327.6 | -3.3999999999999773 | 32894.6 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.1863313626698 | None | 271.4 | None | 331.0 | None | 32894.6 | None | None | 0.0 |
| random-32-32-20 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.1637490592716 | -0.0225823033982 | 249.2 | -22.19999999999999 | 328.8 | -2.1999999999999886 | 27563.4 | 0.25 | 0.75 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | always_additive_defer | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1334.0 | 13.599999999999909 | 19457.4 | 0.3333333333333333 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.07784849222 | None | 392.2 | None | 1320.4 | None | 19457.4 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.07784849222 | 0.0 | 391.6 | -0.5999999999999659 | 1352.2 | 31.799999999999955 | 19457.4 | 0.4166666666666667 | 0.5833333333333334 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | always_additive_defer | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2669.6 | 65.19999999999982 | 20731.2 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.170794865788 | None | 209.4 | None | 2604.4 | None | 20731.2 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2497.2 | -107.20000000000027 | 20731.2 | 0.5 | 0.5 | 0.0 |

## Stop Condition Snapshot

{
  "method_flags": {
    "always_additive_defer": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "oracle_teacher_forced_best_safe_update_static_proxy": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    }
  },
  "oracle_replay_executed": true,
  "oracle_replay_scope": "static_rule_proxy",
  "paired_rows": 60,
  "repair5c_composite_closed_loop_executed": false,
  "repair5d_composite_closed_loop_executed": false,
  "strict_safety_mask_blocks_all_learned_choices": false
}

## Decision Table Interpretation

{
  "case": "B",
  "oracle_positive": true,
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "recommended_action": "improve_composite_or_reranker_do_not_jump_to_delta_updateparams",
  "repair5d_positive": false
}

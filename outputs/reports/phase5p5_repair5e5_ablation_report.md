# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-06-01 15:56:32

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_ablation\phase5p5_repair5e5_ablation_rerun.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_ablation\phase5p5_repair5e5_ablation_rerun_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_ablation\phase5p5_repair5e5_ablation_rerun_commands.jsonl`

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
- methods: `['lacam_star_ltm', 'repair5e4_calibrated_guard_only_on_e3_split', 'repair5e4_closed_loop_utility_selector', 'repair5e5_crossfold_utility_reranker', 'repair5e5_crossfold_utility_reranker_force_additive_parity', 'repair5e5_crossfold_utility_reranker_recovery_disabled_parity', 'repair5e5_crossfold_utility_reranker_no_ood_guard_diagnostic', 'repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic', 'repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic', 'repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic']`
- support_methods: `[]`

## Runtime Availability

- `repair5d_native_composite_export`: `not_feasible_current_cxx_runtime_accepts_single_mlp_runtime_only_distilled_bridge_used`
- `oracle_teacher_forced_best_safe_update`: `not_executed_pass_include_oracle_static_probe_for_static_upper_bound_proxy`
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
- `repair5e5_crossfold_utility_reranker_runtime`: `available`
- `repair5e5_crossfold_utility_reranker_shuffled_labels_runtime`: `available`
- `repair5e5_crossfold_utility_reranker_loose_threshold_runtime`: `available`
- `repair5e5_crossfold_utility_reranker_strict_threshold_runtime`: `available`

## Group Summary

| map | agents | method | runs | success | ratio | d ratio | expanded | d expanded | TTFS ms | d TTFS | pibt | fallback | non-additive | overhead ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| maze-32-32-4 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.185242544024 | None | 435.6 | None | 186.8 | None | 21575.4 | None | None | 0.0 |
| maze-32-32-4 | 50 | repair5e4_calibrated_guard_only_on_e3_split | 5 | 1.000000 | 1.185242544024 | 0.0 | 435.6 | 0.0 | 187.6 | 0.799999999999983 | 21575.4 | 0.25 | 0.0 | 0.44584 |
| maze-32-32-4 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.185242544024 | 0.0 | 435.6 | 0.0 | 186.0 | -0.8000000000000114 | 21575.4 | 0.25 | 0.0 | 0.44256 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.17202051813 | -0.0132220258939999 | 423.4 | -12.200000000000045 | 186.6 | -0.20000000000001705 | 21101.8 | 0.25 | 0.75 | 0.43052 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.185242544024 | 0.0 | 435.6 | 0.0 | 185.8 | -1.0 | 21575.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic | 5 | 1.000000 | 1.17202051813 | -0.0132220258939999 | 423.4 | -12.200000000000045 | 185.4 | -1.4000000000000057 | 21101.8 | 0.25 | 0.75 | 0.45738 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker_no_ood_guard_diagnostic | 5 | 1.000000 | 1.17202051813 | -0.0132220258939999 | 423.4 | -12.200000000000045 | 187.6 | 0.799999999999983 | 21101.8 | 0.25 | 0.75 | 0.4107 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker_recovery_disabled_parity | 5 | 1.000000 | 1.185242544024 | 0.0 | 435.6 | 0.0 | 187.0 | 0.19999999999998863 | 21575.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic | 5 | 1.000000 | 1.168372818782 | -0.016869725242000033 | 438.4 | 2.7999999999999545 | 188.4 | 1.5999999999999943 | 21713.8 | 0.25 | 0.75 | 0.44578 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic | 5 | 1.000000 | 1.185242544024 | 0.0 | 435.6 | 0.0 | 189.4 | 2.5999999999999943 | 21575.4 | 0.25 | 0.0 | 0.46414 |
| maze-32-32-4 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.259743057366 | None | 537.6 | None | 388.6 | None | 62993.4 | None | None | 0.0 |
| maze-32-32-4 | 100 | repair5e4_calibrated_guard_only_on_e3_split | 5 | 1.000000 | 1.271933791468 | 0.012190734102 | 565.4 | 27.799999999999955 | 389.0 | 0.39999999999997726 | 69661.8 | 0.25 | 0.75 | 0.51762 |
| maze-32-32-4 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 387.8 | -0.8000000000000114 | 62993.4 | 0.25 | 0.0 | 0.47093999999999997 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 390.6 | 2.0 | 62993.4 | 0.25 | 0.0 | 0.4496 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 389.0 | 0.39999999999997726 | 62993.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 391.2 | 2.599999999999966 | 62993.4 | 0.25 | 0.0 | 0.47384 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker_no_ood_guard_diagnostic | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 387.8 | -0.8000000000000114 | 62993.4 | 0.25 | 0.0 | 0.47962 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker_recovery_disabled_parity | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 394.4 | 5.7999999999999545 | 62993.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 393.0 | 4.399999999999977 | 62993.4 | 0.25 | 0.0 | 0.46448 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 387.2 | -1.400000000000034 | 62993.4 | 0.25 | 0.0 | 0.46798 |
| random-32-32-20 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.152551037608 | None | 229.4 | None | 164.6 | None | 14588.4 | None | None | 0.0 |
| random-32-32-20 | 50 | repair5e4_calibrated_guard_only_on_e3_split | 5 | 1.000000 | 1.1614813279979999 | 0.008930290389999929 | 209.4 | -20.0 | 164.4 | -0.19999999999998863 | 10742.8 | 0.25 | 0.75 | 0.42956 |
| random-32-32-20 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.157676980172 | 0.005125942564000008 | 223.2 | -6.200000000000017 | 164.0 | -0.5999999999999943 | 14262.4 | 0.25 | 0.75 | 0.42118 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.160189815082 | 0.007638777474000102 | 232.8 | 3.4000000000000057 | 164.2 | -0.4000000000000057 | 14590.8 | 0.25 | 0.75 | 0.43318 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.152551037608 | 0.0 | 229.4 | 0.0 | 161.8 | -2.799999999999983 | 14588.4 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic | 5 | 1.000000 | 1.160189815082 | 0.007638777474000102 | 232.8 | 3.4000000000000057 | 164.4 | -0.19999999999998863 | 14590.8 | 0.25 | 0.75 | 0.44642 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_no_ood_guard_diagnostic | 5 | 1.000000 | 1.160189815082 | 0.007638777474000102 | 232.8 | 3.4000000000000057 | 162.4 | -2.1999999999999886 | 14590.8 | 0.25 | 0.75 | 0.42234 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_recovery_disabled_parity | 5 | 1.000000 | 1.152551037608 | 0.0 | 229.4 | 0.0 | 163.2 | -1.4000000000000057 | 14588.4 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic | 5 | 1.000000 | 1.1569523424919999 | 0.004401304883999924 | 228.6 | -0.8000000000000114 | 162.2 | -2.4000000000000057 | 14427.2 | 0.25 | 0.75 | 0.41894 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic | 5 | 1.000000 | 1.160189815082 | 0.007638777474000102 | 228.4 | -1.0 | 163.2 | -1.4000000000000057 | 14302.2 | 0.25 | 0.75 | 0.44242 |
| random-32-32-20 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.1863313626698 | None | 271.4 | None | 335.6 | None | 32894.6 | None | None | 0.0 |
| random-32-32-20 | 100 | repair5e4_calibrated_guard_only_on_e3_split | 5 | 1.000000 | 1.1805769331418001 | -0.005754429527999871 | 268.6 | -2.7999999999999545 | 339.8 | 4.199999999999989 | 33837.0 | 0.25 | 0.75 | 0.42166 |
| random-32-32-20 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.1863675087318 | 3.614606199997539e-05 | 269.2 | -2.1999999999999886 | 334.4 | -1.2000000000000455 | 32652.8 | 0.25 | 0.75 | 0.43214 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.1863675087318 | 3.614606199997539e-05 | 269.2 | -2.1999999999999886 | 339.0 | 3.3999999999999773 | 32652.8 | 0.25 | 0.75 | 0.44078 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.1863313626698 | 0.0 | 271.4 | 0.0 | 332.8 | -2.8000000000000114 | 32894.6 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic | 5 | 1.000000 | 1.1863675087318 | 3.614606199997539e-05 | 269.2 | -2.1999999999999886 | 339.4 | 3.7999999999999545 | 32652.8 | 0.25 | 0.75 | 0.42242 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker_no_ood_guard_diagnostic | 5 | 1.000000 | 1.1863675087318 | 3.614606199997539e-05 | 269.2 | -2.1999999999999886 | 335.6 | 0.0 | 32652.8 | 0.25 | 0.75 | 0.4209 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker_recovery_disabled_parity | 5 | 1.000000 | 1.1863313626698 | 0.0 | 271.4 | 0.0 | 332.2 | -3.400000000000034 | 32894.6 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic | 5 | 1.000000 | 1.1753849399268002 | -0.01094642274299984 | 246.6 | -24.799999999999983 | 336.0 | 0.39999999999997726 | 25867.6 | 0.25 | 0.75 | 0.44023999999999996 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic | 5 | 1.000000 | 1.1863313626698 | 0.0 | 271.4 | 0.0 | 340.0 | 4.399999999999977 | 32894.6 | 0.25 | 0.0 | 0.43998 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.07784849222 | None | 392.2 | None | 1281.8 | None | 19457.4 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5e4_calibrated_guard_only_on_e3_split | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1274.2 | -7.599999999999909 | 19457.4 | 0.3333333333333333 | 0.0 | 0.32882 |
| warehouse-10-20-10-2-1 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1265.6 | -16.200000000000045 | 19457.4 | 0.3333333333333333 | 0.0 | 0.33116 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1274.4 | -7.399999999999864 | 19457.4 | 0.3333333333333333 | 0.0 | 0.33992 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1289.8 | 8.0 | 19457.4 | 0.3333333333333333 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1256.6 | -25.200000000000045 | 19457.4 | 0.3333333333333333 | 0.0 | 0.332 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker_no_ood_guard_diagnostic | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1275.2 | -6.599999999999909 | 19457.4 | 0.3333333333333333 | 0.0 | 0.3347 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker_recovery_disabled_parity | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1270.0 | -11.799999999999955 | 19457.4 | 0.3333333333333333 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1271.4 | -10.399999999999864 | 19457.4 | 0.3333333333333333 | 0.0 | 0.32666 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1279.6 | -2.2000000000000455 | 19457.4 | 0.3333333333333333 | 0.0 | 0.34602 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.170794865788 | None | 209.4 | None | 2520.2 | None | 20731.2 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5e4_calibrated_guard_only_on_e3_split | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2539.6 | 19.40000000000009 | 20731.2 | 0.5 | 0.0 | 0.1993 |
| warehouse-10-20-10-2-1 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2535.6 | 15.400000000000091 | 20731.2 | 0.5 | 0.0 | 0.19828 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2571.0 | 50.80000000000018 | 20731.2 | 0.5 | 0.0 | 0.20514 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2530.8 | 10.600000000000364 | 20731.2 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic | 5 | 0.800000 | 1.17101628003 | 0.00022141424199983994 | 167.4 | -42.0 | 2518.0 | -2.199999999999818 | 16553.0 | 0.5555555555555556 | 0.0 | 0.1486 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker_no_ood_guard_diagnostic | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2526.6 | 6.400000000000091 | 20731.2 | 0.5 | 0.0 | 0.18086 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker_recovery_disabled_parity | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2528.2 | 8.0 | 20731.2 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2523.2 | 3.0 | 20731.2 | 0.5 | 0.0 | 0.19708 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2563.6 | 43.40000000000009 | 20731.2 | 0.5 | 0.0 | 0.24898 |

## Stop Condition Snapshot

{
  "method_flags": {
    "repair5e4_calibrated_guard_only_on_e3_split": {
      "ratio_worse_than_ltm_groups": 2,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 3
    },
    "repair5e4_closed_loop_utility_selector": {
      "ratio_worse_than_ltm_groups": 2,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 4
    },
    "repair5e5_crossfold_utility_reranker": {
      "ratio_worse_than_ltm_groups": 2,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 3
    },
    "repair5e5_crossfold_utility_reranker_force_additive_parity": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic": {
      "ratio_worse_than_ltm_groups": 3,
      "success_worse_than_ltm_groups": 1,
      "zero_nonadditive_groups": 3
    },
    "repair5e5_crossfold_utility_reranker_no_ood_guard_diagnostic": {
      "ratio_worse_than_ltm_groups": 2,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 3
    },
    "repair5e5_crossfold_utility_reranker_recovery_disabled_parity": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic": {
      "ratio_worse_than_ltm_groups": 1,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 3
    },
    "repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic": {
      "ratio_worse_than_ltm_groups": 1,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 5
    }
  },
  "oracle_replay_executed": false,
  "oracle_replay_scope": "not_executed",
  "paired_rows": 270,
  "repair5c_composite_closed_loop_executed": false,
  "repair5d_composite_closed_loop_executed": false,
  "strict_safety_mask_blocks_all_learned_choices": false
}

## Decision Table Interpretation

{
  "case": "C",
  "oracle_positive": false,
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "recommended_action": "do_not_promote_repair5e5_consider_repair5f_side_branch_after_diagnostics",
  "repair5e5_crossfold_utility_reranker_positive": false
}

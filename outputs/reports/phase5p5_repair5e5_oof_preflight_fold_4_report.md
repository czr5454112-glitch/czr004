# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-06-01 15:39:14

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight_fold_4.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight_fold_4_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight_fold_4_commands.jsonl`

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
- methods: `['lacam_star', 'lacam_star_ltm', 'always_additive_defer', 'repair5d_composite_diagnostic_distilled', 'repair5e_caseb_ood_guard_distilled', 'repair5e3_split_guarded_selector', 'repair5e4_closed_loop_utility_selector', 'repair5e5_crossfold_utility_reranker', 'repair5e5_crossfold_utility_reranker_force_additive_parity', 'oracle_teacher_forced_best_safe_update_static_proxy']`
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
- `repair5e5_crossfold_utility_reranker_runtime`: `available`
- `repair5e5_crossfold_utility_reranker_shuffled_labels_runtime`: `available`
- `repair5e5_crossfold_utility_reranker_loose_threshold_runtime`: `available`
- `repair5e5_crossfold_utility_reranker_strict_threshold_runtime`: `available`

## Group Summary

| map | agents | method | runs | success | ratio | d ratio | expanded | d expanded | TTFS ms | d TTFS | pibt | fallback | non-additive | overhead ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| maze-32-32-4 | 50 | always_additive_defer | 5 | 1.000000 | 1.185242544024 | 0.0 | 435.6 | 0.0 | 183.6 | -0.8000000000000114 | 21575.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | lacam_star | 5 | 1.000000 | 1.189429693908 | 0.004187149884000041 | 8420.0 | 7984.4 | 3144.4886 | 2960.0886 | None | None | None | 0.0 |
| maze-32-32-4 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.185242544024 | None | 435.6 | None | 184.4 | None | 21575.4 | None | None | 0.0 |
| maze-32-32-4 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.163585877162 | -0.021656666861999962 | 426.8 | -8.800000000000011 | 183.6 | -0.8000000000000114 | 21137.8 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.176846472892 | -0.008396071131999916 | 437.0 | 1.3999999999999773 | 184.4 | 0.0 | 21644.4 | 0.25 | 0.75 | 0.34918 |
| maze-32-32-4 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.185242544024 | 0.0 | 435.6 | 0.0 | 184.0 | -0.4000000000000057 | 21575.4 | 0.5714285714285714 | 0.0 | 0.38388 |
| maze-32-32-4 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.185242544024 | 0.0 | 435.6 | 0.0 | 183.8 | -0.5999999999999943 | 21575.4 | 0.25 | 0.0 | 0.43238 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.17202051813 | -0.0132220258939999 | 423.4 | -12.200000000000045 | 184.6 | 0.19999999999998863 | 21101.8 | 0.25 | 0.75 | 0.41088 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.185242544024 | 0.0 | 435.6 | 0.0 | 186.0 | 1.5999999999999943 | 21575.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.185242544024 | 0.0 | 435.6 | 0.0 | 184.0 | -0.4000000000000057 | 21575.4 | 0.5714285714285714 | 0.0 | 0.34409999999999996 |
| maze-32-32-4 | 100 | always_additive_defer | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 382.2 | -0.4000000000000341 | 62993.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | lacam_star | 5 | 1.000000 | 1.350963713534 | 0.09122065616800001 | 5214.0 | 4676.4 | 3101.42322 | 2718.82322 | None | None | None | 0.0 |
| maze-32-32-4 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.259743057366 | None | 537.6 | None | 382.6 | None | 62993.4 | None | None | 0.0 |
| maze-32-32-4 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.246184685418 | -0.013558371947999914 | 528.2 | -9.399999999999977 | 382.4 | -0.20000000000004547 | 62653.0 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.258088470876 | -0.001654586489999943 | 523.4 | -14.200000000000045 | 384.2 | 1.599999999999966 | 62177.6 | 0.25 | 0.75 | 0.3426 |
| maze-32-32-4 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 383.0 | 0.39999999999997726 | 62993.4 | 0.5714285714285714 | 0.0 | 0.3792 |
| maze-32-32-4 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 383.2 | 0.5999999999999659 | 62993.4 | 0.25 | 0.0 | 0.5179199999999999 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 381.6 | -1.0 | 62993.4 | 0.25 | 0.0 | 0.47436 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 384.6 | 2.0 | 62993.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 384.2 | 1.599999999999966 | 62993.4 | 0.5714285714285714 | 0.0 | 0.3631 |
| random-32-32-20 | 50 | always_additive_defer | 5 | 1.000000 | 1.152551037608 | 0.0 | 229.4 | 0.0 | 160.2 | -1.0 | 14588.4 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | lacam_star | 5 | 1.000000 | 1.146064960866 | -0.006486076741999858 | 10142.4 | 9913.0 | 3148.86672 | 2987.66672 | None | None | None | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.152551037608 | None | 229.4 | None | 161.2 | None | 14588.4 | None | None | 0.0 |
| random-32-32-20 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.148166444848 | -0.004384592759999917 | 204.4 | -25.0 | 160.8 | -0.39999999999997726 | 10223.2 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.150195965144 | -0.0023550724640000187 | 218.4 | -11.0 | 159.0 | -2.1999999999999886 | 12810.2 | 0.25 | 0.75 | 0.34682 |
| random-32-32-20 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.152551037608 | 0.0 | 229.4 | 0.0 | 161.2 | 0.0 | 14588.4 | 0.5714285714285714 | 0.0 | 0.37486 |
| random-32-32-20 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.157676980172 | 0.005125942564000008 | 223.2 | -6.200000000000017 | 160.0 | -1.1999999999999886 | 14262.4 | 0.25 | 0.75 | 0.43136 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.160189815082 | 0.007638777474000102 | 232.8 | 3.4000000000000057 | 161.8 | 0.6000000000000227 | 14590.8 | 0.25 | 0.75 | 0.41536 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.152551037608 | 0.0 | 229.4 | 0.0 | 161.6 | 0.4000000000000057 | 14588.4 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.152551037608 | 0.0 | 229.4 | 0.0 | 159.8 | -1.3999999999999773 | 14588.4 | 0.5714285714285714 | 0.0 | 0.37746 |
| random-32-32-20 | 100 | always_additive_defer | 5 | 1.000000 | 1.1863313626698 | 0.0 | 271.4 | 0.0 | 329.6 | 0.8000000000000114 | 32894.6 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | lacam_star | 5 | 1.000000 | 1.1903326872938 | 0.004001324624000047 | 6802.8 | 6531.400000000001 | 3095.87092 | 2767.0709199999997 | None | None | None | 0.0 |
| random-32-32-20 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.1863313626698 | None | 271.4 | None | 328.8 | None | 32894.6 | None | None | 0.0 |
| random-32-32-20 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.1637490592716 | -0.0225823033982 | 249.2 | -22.19999999999999 | 327.2 | -1.6000000000000227 | 27563.2 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.1757283331098 | -0.010603029559999921 | 290.4 | 19.0 | 329.4 | 0.5999999999999659 | 38187.0 | 0.25 | 0.75 | 0.35956 |
| random-32-32-20 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.1863313626698 | 0.0 | 271.4 | 0.0 | 331.0 | 2.1999999999999886 | 32894.6 | 0.5714285714285714 | 0.0 | 0.3878 |
| random-32-32-20 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.1863675087318 | 3.614606199997539e-05 | 269.2 | -2.1999999999999886 | 330.4 | 1.599999999999966 | 32652.8 | 0.25 | 0.75 | 0.42728 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.1863675087318 | 3.614606199997539e-05 | 269.2 | -2.1999999999999886 | 334.0 | 5.199999999999989 | 32652.8 | 0.25 | 0.75 | 0.44242 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.1863313626698 | 0.0 | 271.4 | 0.0 | 328.0 | -0.8000000000000114 | 32894.6 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.1863313626698 | 0.0 | 271.4 | 0.0 | 341.8 | 13.0 | 32894.6 | 0.5714285714285714 | 0.0 | 0.35552 |
| warehouse-10-20-10-2-1 | 50 | always_additive_defer | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1176.0 | -9.599999999999909 | 19457.4 | 0.3333333333333333 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star | 5 | 1.000000 | 1.067463976644 | -0.010384515576000064 | 8352.2 | 7960.000000000001 | 3109.55478 | 1923.95478 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.07784849222 | None | 392.2 | None | 1185.6 | None | 19457.4 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1173.0 | -12.599999999999909 | 19457.4 | 0.3333333333333333 | 0.6666666666666666 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1188.4 | 2.800000000000182 | 19457.4 | 0.3333333333333333 | 0.6666666666666666 | 0.31008 |
| warehouse-10-20-10-2-1 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1181.8 | -3.7999999999999545 | 19457.4 | 0.6 | 0.0 | 0.31976 |
| warehouse-10-20-10-2-1 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1176.6 | -9.0 | 19457.4 | 0.3333333333333333 | 0.0 | 0.34496 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1171.4 | -14.199999999999818 | 19457.4 | 0.3333333333333333 | 0.0 | 0.35774 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1177.2 | -8.399999999999864 | 19457.4 | 0.3333333333333333 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1184.4 | -1.199999999999818 | 19457.4 | 0.6 | 0.0 | 0.3204 |
| warehouse-10-20-10-2-1 | 100 | always_additive_defer | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2340.4 | 1.800000000000182 | 20731.2 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star | 5 | 1.000000 | 1.147929257486 | -0.022865608302000018 | 7245.2 | 7035.8 | 3085.37044 | 746.7704400000002 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.170794865788 | None | 209.4 | None | 2338.6 | None | 20731.2 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2371.0 | 32.40000000000009 | 20731.2 | 0.5 | 0.5 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2335.4 | -3.199999999999818 | 20731.2 | 0.5 | 0.5 | 0.17608 |
| warehouse-10-20-10-2-1 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2334.8 | -3.799999999999727 | 20731.2 | 0.6666666666666666 | 0.0 | 0.22914 |
| warehouse-10-20-10-2-1 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2342.0 | 3.400000000000091 | 20731.2 | 0.5 | 0.0 | 0.20542 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2419.0 | 80.40000000000009 | 20731.2 | 0.5 | 0.0 | 0.24742 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2421.6 | 83.0 | 20731.2 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2338.4 | -0.1999999999998181 | 20731.2 | 0.6666666666666666 | 0.0 | 0.21168 |

## Stop Condition Snapshot

{
  "method_flags": {
    "always_additive_defer": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "lacam_star": {
      "ratio_worse_than_ltm_groups": 3,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "oracle_teacher_forced_best_safe_update_static_proxy": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair5d_composite_diagnostic_distilled": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair5e3_split_guarded_selector": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
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
    "repair5e_caseb_ood_guard_distilled": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    }
  },
  "oracle_replay_executed": true,
  "oracle_replay_scope": "static_rule_proxy",
  "paired_rows": 270,
  "repair5c_composite_closed_loop_executed": false,
  "repair5d_composite_closed_loop_executed": true,
  "strict_safety_mask_blocks_all_learned_choices": false
}

## Decision Table Interpretation

{
  "case": "B",
  "oracle_positive": true,
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "recommended_action": "e5_not_promotable_inspect_crossfold_utility_reranker",
  "repair5e5_crossfold_utility_reranker_positive": false
}

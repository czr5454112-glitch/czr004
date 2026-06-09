# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-06-01 13:33:30

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_preflight\phase5p5_repair5e5_preflight.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_preflight\phase5p5_repair5e5_preflight_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_preflight\phase5p5_repair5e5_preflight_commands.jsonl`

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
| maze-32-32-4 | 50 | always_additive_defer | 5 | 1.000000 | 1.185242544024 | 0.0 | 435.6 | 0.0 | 184.4 | -0.799999999999983 | 21575.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | lacam_star | 5 | 1.000000 | 1.189429693908 | 0.004187149884000041 | 8411.0 | 7975.4 | 3143.56724 | 2958.36724 | None | None | None | 0.0 |
| maze-32-32-4 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.185242544024 | None | 435.6 | None | 185.2 | None | 21575.4 | None | None | 0.0 |
| maze-32-32-4 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.163585877162 | -0.021656666861999962 | 426.8 | -8.800000000000011 | 183.8 | -1.3999999999999773 | 21137.8 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.176846472892 | -0.008396071131999916 | 437.0 | 1.3999999999999773 | 185.8 | 0.6000000000000227 | 21644.4 | 0.25 | 0.75 | 0.34328 |
| maze-32-32-4 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.185242544024 | 0.0 | 435.6 | 0.0 | 187.2 | 2.0 | 21575.4 | 0.5714285714285714 | 0.0 | 0.37184 |
| maze-32-32-4 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.185242544024 | 0.0 | 435.6 | 0.0 | 185.0 | -0.19999999999998863 | 21575.4 | 0.25 | 0.0 | 0.44296 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.17202051813 | -0.0132220258939999 | 423.4 | -12.200000000000045 | 187.0 | 1.8000000000000114 | 21101.8 | 0.25 | 0.75 | 0.41814 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.185242544024 | 0.0 | 435.6 | 0.0 | 183.6 | -1.5999999999999943 | 21575.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.185242544024 | 0.0 | 435.6 | 0.0 | 185.8 | 0.6000000000000227 | 21575.4 | 0.5714285714285714 | 0.0 | 0.3581 |
| maze-32-32-4 | 100 | always_additive_defer | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 387.0 | -2.6000000000000227 | 62993.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | lacam_star | 5 | 1.000000 | 1.350963713534 | 0.09122065616800001 | 5157.0 | 4619.4 | 3106.4783 | 2716.8783000000003 | None | None | None | 0.0 |
| maze-32-32-4 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.259743057366 | None | 537.6 | None | 389.6 | None | 62993.4 | None | None | 0.0 |
| maze-32-32-4 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.246184685418 | -0.013558371947999914 | 528.2 | -9.399999999999977 | 391.6 | 2.0 | 62653.0 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.258088470876 | -0.001654586489999943 | 523.4 | -14.200000000000045 | 388.0 | -1.6000000000000227 | 62177.6 | 0.25 | 0.75 | 0.34018 |
| maze-32-32-4 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 388.6 | -1.0 | 62993.4 | 0.5714285714285714 | 0.0 | 0.37922 |
| maze-32-32-4 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 387.8 | -1.8000000000000114 | 62993.4 | 0.25 | 0.0 | 0.43646 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 386.0 | -3.6000000000000227 | 62993.4 | 0.25 | 0.0 | 0.51504 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 387.8 | -1.8000000000000114 | 62993.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.259743057366 | 0.0 | 537.6 | 0.0 | 394.4 | 4.7999999999999545 | 62993.4 | 0.5714285714285714 | 0.0 | 0.35196 |
| random-32-32-20 | 50 | always_additive_defer | 5 | 1.000000 | 1.152551037608 | 0.0 | 229.4 | 0.0 | 160.8 | 0.20000000000001705 | 14588.4 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | lacam_star | 5 | 1.000000 | 1.146064960866 | -0.006486076741999858 | 10102.6 | 9873.2 | 3127.0058400000003 | 2966.4058400000004 | None | None | None | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.152551037608 | None | 229.4 | None | 160.6 | None | 14588.4 | None | None | 0.0 |
| random-32-32-20 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.148166444848 | -0.004384592759999917 | 204.4 | -25.0 | 158.4 | -2.1999999999999886 | 10223.2 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.150195965144 | -0.0023550724640000187 | 218.4 | -11.0 | 162.4 | 1.8000000000000114 | 12810.2 | 0.25 | 0.75 | 0.34548 |
| random-32-32-20 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.152551037608 | 0.0 | 229.4 | 0.0 | 161.2 | 0.5999999999999943 | 14588.4 | 0.5714285714285714 | 0.0 | 0.37857999999999997 |
| random-32-32-20 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.157676980172 | 0.005125942564000008 | 223.2 | -6.200000000000017 | 158.0 | -2.5999999999999943 | 14262.4 | 0.25 | 0.75 | 0.46796 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.160189815082 | 0.007638777474000102 | 232.8 | 3.4000000000000057 | 160.0 | -0.5999999999999943 | 14590.8 | 0.25 | 0.75 | 0.4145 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.152551037608 | 0.0 | 229.4 | 0.0 | 160.2 | -0.4000000000000057 | 14588.4 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.152551037608 | 0.0 | 229.4 | 0.0 | 160.8 | 0.20000000000001705 | 14588.4 | 0.5714285714285714 | 0.0 | 0.3528 |
| random-32-32-20 | 100 | always_additive_defer | 5 | 1.000000 | 1.1863313626698 | 0.0 | 271.4 | 0.0 | 326.8 | -0.5999999999999659 | 32894.6 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | lacam_star | 5 | 1.000000 | 1.1903326872938 | 0.004001324624000047 | 6879.0 | 6607.6 | 3109.63186 | 2782.23186 | None | None | None | 0.0 |
| random-32-32-20 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.1863313626698 | None | 271.4 | None | 327.4 | None | 32894.6 | None | None | 0.0 |
| random-32-32-20 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.1637490592716 | -0.0225823033982 | 249.2 | -22.19999999999999 | 325.4 | -2.0 | 27563.4 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.1757283331098 | -0.010603029559999921 | 290.4 | 19.0 | 327.4 | 0.0 | 38187.0 | 0.25 | 0.75 | 0.36834 |
| random-32-32-20 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.1863313626698 | 0.0 | 271.4 | 0.0 | 326.6 | -0.7999999999999545 | 32894.6 | 0.5714285714285714 | 0.0 | 0.3977 |
| random-32-32-20 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.1863675087318 | 3.614606199997539e-05 | 269.2 | -2.1999999999999886 | 327.2 | -0.19999999999998863 | 32652.8 | 0.25 | 0.75 | 0.4192 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.1863675087318 | 3.614606199997539e-05 | 269.2 | -2.1999999999999886 | 325.8 | -1.599999999999966 | 32652.8 | 0.25 | 0.75 | 0.47093999999999997 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.1863313626698 | 0.0 | 271.4 | 0.0 | 329.4 | 2.0 | 32894.6 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.1863313626698 | 0.0 | 271.4 | 0.0 | 329.8 | 2.400000000000034 | 32894.6 | 0.5714285714285714 | 0.0 | 0.34232 |
| warehouse-10-20-10-2-1 | 50 | always_additive_defer | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.0 | -0.19999999999998863 | 1305.8 | 44.0 | 19457.4 | 0.35714285714285715 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star | 5 | 1.000000 | 1.067463976644 | -0.010384515576000064 | 8300.8 | 7908.599999999999 | 3106.7914 | 1844.9914 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.07784849222 | None | 392.2 | None | 1261.8 | None | 19457.4 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.0 | -0.19999999999998863 | 1265.0 | 3.2000000000000455 | 19457.4 | 0.35714285714285715 | 0.6428571428571429 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1273.2 | 11.400000000000091 | 19457.4 | 0.3333333333333333 | 0.6666666666666666 | 0.31866 |
| warehouse-10-20-10-2-1 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1279.8 | 18.0 | 19457.4 | 0.6 | 0.0 | 0.30072 |
| warehouse-10-20-10-2-1 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1297.0 | 35.200000000000045 | 19457.4 | 0.3333333333333333 | 0.0 | 0.34824 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1277.8 | 16.0 | 19457.4 | 0.3333333333333333 | 0.0 | 0.34728 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1285.2 | 23.40000000000009 | 19457.4 | 0.3333333333333333 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.07784849222 | 0.0 | 392.2 | 0.0 | 1278.6 | 16.799999999999955 | 19457.4 | 0.6 | 0.0 | 0.27777999999999997 |
| warehouse-10-20-10-2-1 | 100 | always_additive_defer | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2596.0 | 18.800000000000182 | 20731.2 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star | 5 | 1.000000 | 1.147929257486 | -0.022865608302000018 | 7035.2 | 6825.8 | 3085.24982 | 508.0498200000002 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.170794865788 | None | 209.4 | None | 2577.2 | None | 20731.2 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.2 | -0.20000000000001705 | 2556.0 | -21.199999999999818 | 20731.2 | 0.5555555555555556 | 0.4444444444444444 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2610.4 | 33.20000000000027 | 20731.2 | 0.5 | 0.5 | 0.16233999999999998 |
| warehouse-10-20-10-2-1 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2591.2 | 14.0 | 20731.2 | 0.6666666666666666 | 0.0 | 0.2041 |
| warehouse-10-20-10-2-1 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2581.8 | 4.600000000000364 | 20731.2 | 0.5 | 0.0 | 0.20912 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2545.0 | -32.19999999999982 | 20731.2 | 0.5 | 0.0 | 0.22122 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2592.2 | 15.0 | 20731.2 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.170794865788 | 0.0 | 209.4 | 0.0 | 2588.6 | 11.400000000000091 | 20731.2 | 0.6666666666666666 | 0.0 | 0.1675 |

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

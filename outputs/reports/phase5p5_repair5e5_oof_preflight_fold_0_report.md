# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-06-01 13:59:08

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight_fold_0.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight_fold_0_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight_fold_0_commands.jsonl`

## Provenance

- git branch: `phase4f5p5-stable-attention-lau`
- git commit: `db0f494`
- git dirty state: `tracked-dirty_untracked-present`
- clean tracked worktree: `False`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agent_counts: `[50, 100]`
- instances_per_setting: `3`
- instance_ids: `[1, 2, 3, 4, 5]`
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
| maze-32-32-4 | 50 | always_additive_defer | 5 | 1.000000 | 1.14545031823 | 0.0 | 415.6 | 0.0 | 194.4 | 3.0 | 20579.8 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | lacam_star | 5 | 1.000000 | 1.17613693775 | 0.030686619519999958 | 6192.4 | 5776.799999999999 | 3082.8349 | 2891.4348999999997 | None | None | None | 0.0 |
| maze-32-32-4 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.14545031823 | None | 415.6 | None | 191.4 | None | 20579.8 | None | None | 0.0 |
| maze-32-32-4 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.140785782512 | -0.0046645357179999625 | 415.4 | -0.20000000000004547 | 193.0 | 1.5999999999999943 | 20599.4 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.161474283152 | 0.016023964921999978 | 420.0 | 4.399999999999977 | 195.0 | 3.5999999999999943 | 20799.2 | 0.25 | 0.75 | 0.34737999999999997 |
| maze-32-32-4 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.14545031823 | 0.0 | 415.6 | 0.0 | 195.0 | 3.5999999999999943 | 20579.8 | 0.5714285714285714 | 0.0 | 0.3957 |
| maze-32-32-4 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.14545031823 | 0.0 | 415.6 | 0.0 | 195.8 | 4.400000000000006 | 20579.8 | 0.25 | 0.0 | 0.44694 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.149208234714 | 0.0037579164840000345 | 415.2 | -0.4000000000000341 | 199.2 | 7.799999999999983 | 20598.6 | 0.25 | 0.75 | 0.43498 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.14545031823 | 0.0 | 415.6 | 0.0 | 192.4 | 1.0 | 20579.8 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.14545031823 | 0.0 | 415.6 | 0.0 | 193.2 | 1.799999999999983 | 20579.8 | 0.5714285714285714 | 0.0 | 0.37572 |
| maze-32-32-4 | 100 | always_additive_defer | 5 | 1.000000 | 1.267260872084 | 0.0 | 513.8 | 0.0 | 391.0 | -2.6000000000000227 | 63108.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | lacam_star | 5 | 1.000000 | 1.313048909384 | 0.04578803730000014 | 10178.8 | 9665.0 | 3124.82164 | 2731.22164 | None | None | None | 0.0 |
| maze-32-32-4 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.267260872084 | None | 513.8 | None | 393.6 | None | 63108.4 | None | None | 0.0 |
| maze-32-32-4 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.24536119787 | -0.021899674213999853 | 490.6 | -23.199999999999932 | 399.6 | 6.0 | 59059.0 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.27168751887 | 0.004426646786000132 | 455.4 | -58.39999999999998 | 394.4 | 0.7999999999999545 | 45267.6 | 0.25 | 0.75 | 0.37032 |
| maze-32-32-4 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.267260872084 | 0.0 | 513.8 | 0.0 | 391.6 | -2.0 | 63108.4 | 0.5714285714285714 | 0.0 | 0.4069 |
| maze-32-32-4 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.267260872084 | 0.0 | 513.8 | 0.0 | 397.8 | 4.199999999999989 | 63108.4 | 0.25 | 0.0 | 0.4505 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.267260872084 | 0.0 | 513.8 | 0.0 | 395.6 | 2.0 | 63108.4 | 0.25 | 0.0 | 0.46128 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.267260872084 | 0.0 | 513.8 | 0.0 | 396.4 | 2.7999999999999545 | 63108.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.267260872084 | 0.0 | 513.8 | 0.0 | 393.8 | 0.19999999999998863 | 63108.4 | 0.5714285714285714 | 0.0 | 0.3764 |
| random-32-32-20 | 50 | always_additive_defer | 5 | 1.000000 | 1.1291142841119999 | 0.0 | 255.4 | 0.0 | 161.6 | 2.0 | 17647.8 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | lacam_star | 5 | 1.000000 | 1.121504451404 | -0.007609832707999864 | 15155.8 | 14900.4 | 3215.37686 | 3055.77686 | None | None | None | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.1291142841119999 | None | 255.4 | None | 159.6 | None | 17647.8 | None | None | 0.0 |
| random-32-32-20 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.123996173876 | -0.00511811023599984 | 211.4 | -44.0 | 159.8 | 0.20000000000001705 | 10713.4 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.126752079388 | -0.00236220472399995 | 238.2 | -17.200000000000017 | 158.4 | -1.1999999999999886 | 14681.2 | 0.25 | 0.75 | 0.3491 |
| random-32-32-20 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.1291142841119999 | 0.0 | 255.4 | 0.0 | 159.6 | 0.0 | 17647.8 | 0.5714285714285714 | 0.0 | 0.37202 |
| random-32-32-20 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.123996173876 | -0.00511811023599984 | 240.0 | -15.400000000000006 | 158.4 | -1.1999999999999886 | 15496.6 | 0.25 | 0.75 | 0.42178 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.1291142841119999 | 0.0 | 230.8 | -24.599999999999994 | 158.2 | -1.4000000000000057 | 14039.2 | 0.25 | 0.75 | 0.40986 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.1291142841119999 | 0.0 | 255.4 | 0.0 | 160.4 | 0.8000000000000114 | 17647.8 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.1291142841119999 | 0.0 | 255.4 | 0.0 | 162.0 | 2.4000000000000057 | 17647.8 | 0.5714285714285714 | 0.0 | 0.3549 |
| random-32-32-20 | 100 | always_additive_defer | 5 | 1.000000 | 1.277199279786 | 0.0 | 227.6 | 0.0 | 318.8 | -5.399999999999977 | 22470.2 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | lacam_star | 5 | 1.000000 | 1.284460875676 | 0.007261595890000194 | 6364.0 | 6136.4 | 3091.82438 | 2767.62438 | None | None | None | 0.0 |
| random-32-32-20 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.277199279786 | None | 227.6 | None | 324.2 | None | 22470.2 | None | None | 0.0 |
| random-32-32-20 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.253774846898 | -0.023424432888000002 | 260.0 | 32.400000000000006 | 317.8 | -6.399999999999977 | 31492.8 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.277546309544 | 0.00034702975800016134 | 239.4 | 11.800000000000011 | 319.4 | -4.800000000000011 | 24691.4 | 0.25 | 0.75 | 0.35176 |
| random-32-32-20 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.277199279786 | 0.0 | 227.6 | 0.0 | 315.6 | -8.599999999999966 | 22470.2 | 0.5714285714285714 | 0.0 | 0.41796 |
| random-32-32-20 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.276803700444 | -0.0003955793419998521 | 223.8 | -3.799999999999983 | 317.2 | -7.0 | 22011.2 | 0.25 | 0.75 | 0.42902 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.277793654336 | 0.0005943745500001096 | 251.8 | 24.200000000000017 | 315.4 | -8.800000000000011 | 30720.4 | 0.25 | 0.75 | 0.4193 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.277199279786 | 0.0 | 227.6 | 0.0 | 316.8 | -7.399999999999977 | 22470.2 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.277199279786 | 0.0 | 227.6 | 0.0 | 316.2 | -8.0 | 22470.2 | 0.5714285714285714 | 0.0 | 0.35468 |
| warehouse-10-20-10-2-1 | 50 | always_additive_defer | 5 | 1.000000 | 1.094732265074 | 0.0 | 412.2 | 0.0 | 1295.8 | -10.0 | 20454.2 | 0.3333333333333333 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star | 5 | 1.000000 | 1.084801665644 | -0.009930599429999853 | 6491.8 | 6079.6 | 3085.0290800000002 | 1779.2290800000003 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.094732265074 | None | 412.2 | None | 1305.8 | None | 20454.2 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.094732265074 | 0.0 | 411.8 | -0.39999999999997726 | 1327.8 | 22.0 | 20454.2 | 0.38461538461538464 | 0.6153846153846154 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.094732265074 | 0.0 | 412.2 | 0.0 | 1284.4 | -21.399999999999864 | 20454.2 | 0.3333333333333333 | 0.6666666666666666 | 0.27674 |
| warehouse-10-20-10-2-1 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.094732265074 | 0.0 | 412.2 | 0.0 | 1298.0 | -7.7999999999999545 | 20454.2 | 0.6 | 0.0 | 0.2813 |
| warehouse-10-20-10-2-1 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.094732265074 | 0.0 | 412.2 | 0.0 | 1310.2 | 4.400000000000091 | 20454.2 | 0.3333333333333333 | 0.0 | 0.3703 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.094732265074 | 0.0 | 412.2 | 0.0 | 1296.2 | -9.599999999999909 | 20454.2 | 0.3333333333333333 | 0.0 | 0.34892 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.094732265074 | 0.0 | 412.0 | -0.19999999999998863 | 1318.4 | 12.600000000000136 | 20454.2 | 0.35714285714285715 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.094732265074 | 0.0 | 412.2 | 0.0 | 1300.4 | -5.399999999999864 | 20454.2 | 0.6 | 0.0 | 0.28284 |
| warehouse-10-20-10-2-1 | 100 | always_additive_defer | 5 | 1.000000 | 1.15625096979 | 0.0 | 214.0 | 0.0 | 2649.8 | 72.40000000000009 | 21215.0 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star | 5 | 1.000000 | 1.152826230914 | -0.003424738876000033 | 4761.8 | 4547.8 | 3072.00504 | 494.6050399999999 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.15625096979 | None | 214.0 | None | 2577.4 | None | 21215.0 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.15625096979 | 0.0 | 213.8 | -0.19999999999998863 | 2565.0 | -12.400000000000091 | 21215.0 | 0.5555555555555556 | 0.4444444444444444 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.15625096979 | 0.0 | 214.0 | 0.0 | 2559.4 | -18.0 | 21215.0 | 0.5 | 0.5 | 0.17012 |
| warehouse-10-20-10-2-1 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.15625096979 | 0.0 | 214.0 | 0.0 | 2600.2 | 22.799999999999727 | 21215.0 | 0.6666666666666666 | 0.0 | 0.17856 |
| warehouse-10-20-10-2-1 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.15625096979 | 0.0 | 214.0 | 0.0 | 2585.2 | 7.799999999999727 | 21215.0 | 0.5 | 0.0 | 0.2022 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.15625096979 | 0.0 | 214.0 | 0.0 | 2599.8 | 22.40000000000009 | 21215.0 | 0.5 | 0.0 | 0.2036 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.15625096979 | 0.0 | 214.0 | 0.0 | 2593.2 | 15.799999999999727 | 21215.0 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.15625096979 | 0.0 | 214.0 | 0.0 | 2568.4 | -9.0 | 21215.0 | 0.6666666666666666 | 0.0 | 0.17312 |

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
      "ratio_worse_than_ltm_groups": 3,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair5e3_split_guarded_selector": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "repair5e4_closed_loop_utility_selector": {
      "ratio_worse_than_ltm_groups": 0,
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

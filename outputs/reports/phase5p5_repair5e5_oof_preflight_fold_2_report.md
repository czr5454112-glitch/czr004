# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-06-01 14:49:34

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight_fold_2.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight_fold_2_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight_fold_2_commands.jsonl`

## Provenance

- git branch: `phase4f5p5-stable-attention-lau`
- git commit: `db0f494`
- git dirty state: `tracked-dirty_untracked-present`
- clean tracked worktree: `False`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agent_counts: `[50, 100]`
- instances_per_setting: `3`
- instance_ids: `[11, 12, 13, 14, 15]`
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
| maze-32-32-4 | 50 | always_additive_defer | 5 | 1.000000 | 1.171863178984 | 0.0 | 440.8 | 0.0 | 186.0 | -0.8000000000000114 | 21839.2 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | lacam_star | 5 | 1.000000 | 1.155033093434 | -0.016830085549999874 | 13381.6 | 12940.800000000001 | 3182.5385 | 2995.7385 | None | None | None | 0.0 |
| maze-32-32-4 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.171863178984 | None | 440.8 | None | 186.8 | None | 21839.2 | None | None | 0.0 |
| maze-32-32-4 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.1461150395019999 | -0.025748139482000054 | 429.6 | -11.199999999999989 | 188.4 | 1.5999999999999943 | 21280.0 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.169553073932 | -0.002310105052000022 | 457.8 | 17.0 | 186.2 | -0.6000000000000227 | 22690.0 | 0.25 | 0.75 | 0.35302 |
| maze-32-32-4 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.171863178984 | 0.0 | 440.8 | 0.0 | 185.0 | -1.8000000000000114 | 21839.2 | 0.5714285714285714 | 0.0 | 0.38748 |
| maze-32-32-4 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.171863178984 | 0.0 | 440.8 | 0.0 | 188.8 | 2.0 | 21839.2 | 0.25 | 0.0 | 0.44124 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.163346655666 | -0.008516523318000013 | 427.2 | -13.600000000000023 | 184.0 | -2.8000000000000114 | 21160.0 | 0.25 | 0.75 | 0.41622 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.171863178984 | 0.0 | 440.8 | 0.0 | 186.4 | -0.4000000000000057 | 21839.2 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.171863178984 | 0.0 | 440.8 | 0.0 | 187.6 | 0.799999999999983 | 21839.2 | 0.5714285714285714 | 0.0 | 0.35438000000000003 |
| maze-32-32-4 | 100 | always_additive_defer | 5 | 1.000000 | 1.296783823846 | 0.0 | 547.4 | 0.0 | 398.0 | 0.0 | 57814.2 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | lacam_star | 5 | 1.000000 | 1.344127472726 | 0.04734364887999987 | 10576.0 | 10028.6 | 3159.79894 | 2761.79894 | None | None | None | 0.0 |
| maze-32-32-4 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.296783823846 | None | 547.4 | None | 398.0 | None | 57814.2 | None | None | 0.0 |
| maze-32-32-4 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.246406293204 | -0.05037753064200001 | 512.0 | -35.39999999999998 | 396.6 | -1.3999999999999773 | 53913.8 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.27749140403 | -0.01929241981600005 | 520.4 | -27.0 | 399.4 | 1.3999999999999773 | 54813.4 | 0.25 | 0.75 | 0.39339999999999997 |
| maze-32-32-4 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.296783823846 | 0.0 | 547.4 | 0.0 | 398.6 | 0.6000000000000227 | 57814.2 | 0.5714285714285714 | 0.0 | 0.40288 |
| maze-32-32-4 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.296783823846 | 0.0 | 547.4 | 0.0 | 400.0 | 2.0 | 57814.2 | 0.25 | 0.0 | 0.44176 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.296783823846 | 0.0 | 547.4 | 0.0 | 399.8 | 1.8000000000000114 | 57814.2 | 0.25 | 0.0 | 0.44904 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.296783823846 | 0.0 | 547.4 | 0.0 | 397.0 | -1.0 | 57814.2 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.296783823846 | 0.0 | 547.4 | 0.0 | 399.8 | 1.8000000000000114 | 57814.2 | 0.5714285714285714 | 0.0 | 0.35228 |
| random-32-32-20 | 50 | always_additive_defer | 5 | 1.000000 | 1.1584585119320001 | 0.0 | 227.4 | 0.0 | 160.6 | -1.200000000000017 | 11244.4 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | lacam_star | 5 | 1.000000 | 1.121619025418 | -0.03683948651400004 | 7188.0 | 6960.6 | 3088.23548 | 2926.4354799999996 | None | None | None | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.1584585119320001 | None | 227.4 | None | 161.8 | None | 11244.4 | None | None | 0.0 |
| random-32-32-20 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.1395094905779999 | -0.01894902135400023 | 239.6 | 12.199999999999989 | 162.6 | 0.799999999999983 | 14556.0 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.142568100974 | -0.015890410958000034 | 240.8 | 13.400000000000006 | 161.8 | 0.0 | 14433.8 | 0.25 | 0.75 | 0.34822000000000003 |
| random-32-32-20 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.1584585119320001 | 0.0 | 227.4 | 0.0 | 161.2 | -0.6000000000000227 | 11244.4 | 0.5714285714285714 | 0.0 | 0.39172 |
| random-32-32-20 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.14019367175 | -0.01826484018200003 | 226.2 | -1.200000000000017 | 161.8 | 0.0 | 11499.8 | 0.25 | 0.75 | 0.41398 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.1584585119320001 | 0.0 | 227.4 | 0.0 | 161.0 | -0.8000000000000114 | 11244.4 | 0.25 | 0.0 | 0.4719 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.1584585119320001 | 0.0 | 227.4 | 0.0 | 161.0 | -0.8000000000000114 | 11244.4 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.1584585119320001 | 0.0 | 227.4 | 0.0 | 159.6 | -2.200000000000017 | 11244.4 | 0.5714285714285714 | 0.0 | 0.35722000000000004 |
| random-32-32-20 | 100 | always_additive_defer | 5 | 1.000000 | 1.277069674098 | 0.0 | 267.6 | 0.0 | 323.8 | 0.19999999999998863 | 30906.6 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | lacam_star | 5 | 1.000000 | 1.28275164965 | 0.005681975551999896 | 6542.4 | 6274.799999999999 | 3090.28698 | 2766.68698 | None | None | None | 0.0 |
| random-32-32-20 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.277069674098 | None | 267.6 | None | 323.6 | None | 30906.6 | None | None | 0.0 |
| random-32-32-20 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.25922191824 | -0.017847755858000136 | 283.2 | 15.599999999999966 | 327.2 | 3.599999999999966 | 35439.4 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.277780151156 | 0.0007104770579999808 | 307.6 | 40.0 | 325.0 | 1.3999999999999773 | 43538.4 | 0.25 | 0.75 | 0.34996 |
| random-32-32-20 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.277069674098 | 0.0 | 267.6 | 0.0 | 330.4 | 6.7999999999999545 | 30906.6 | 0.5714285714285714 | 0.0 | 0.38638 |
| random-32-32-20 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.28621792844 | 0.00914825434199984 | 278.0 | 10.399999999999977 | 324.8 | 1.1999999999999886 | 34392.8 | 0.25 | 0.75 | 0.42832 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.26552159777 | -0.011548076328000034 | 270.2 | 2.599999999999966 | 326.4 | 2.7999999999999545 | 31806.8 | 0.25 | 0.75 | 0.41074 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.277069674098 | 0.0 | 267.6 | 0.0 | 326.4 | 2.7999999999999545 | 30906.6 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.277069674098 | 0.0 | 267.6 | 0.0 | 323.8 | 0.19999999999998863 | 30906.6 | 0.5714285714285714 | 0.0 | 0.36072 |
| warehouse-10-20-10-2-1 | 50 | always_additive_defer | 5 | 1.000000 | 1.06006630308 | 0.0 | 363.4 | 0.0 | 1252.2 | 13.200000000000045 | 18018.0 | 0.3333333333333333 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star | 5 | 1.000000 | 1.0681385326319999 | 0.008072229551999932 | 10537.4 | 10174.0 | 3124.02914 | 1885.02914 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.06006630308 | None | 363.4 | None | 1239.0 | None | 18018.0 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.06006630308 | 0.0 | 363.2 | -0.19999999999998863 | 1257.4 | 18.40000000000009 | 18018.0 | 0.35714285714285715 | 0.6428571428571429 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.06006630308 | 0.0 | 363.4 | 0.0 | 1237.0 | -2.0 | 18018.0 | 0.3333333333333333 | 0.6666666666666666 | 0.28328 |
| warehouse-10-20-10-2-1 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.06006630308 | 0.0 | 363.4 | 0.0 | 1270.2 | 31.200000000000045 | 18018.0 | 0.6 | 0.0 | 0.37068 |
| warehouse-10-20-10-2-1 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.06006630308 | 0.0 | 363.4 | 0.0 | 1254.0 | 15.0 | 18018.0 | 0.3333333333333333 | 0.0 | 0.40592 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.06006630308 | 0.0 | 363.4 | 0.0 | 1248.2 | 9.200000000000045 | 18018.0 | 0.3333333333333333 | 0.0 | 0.40172 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.06006630308 | 0.0 | 363.4 | 0.0 | 1253.8 | 14.799999999999955 | 18018.0 | 0.3333333333333333 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.06006630308 | 0.0 | 363.2 | -0.19999999999998863 | 1288.8 | 49.799999999999955 | 18018.0 | 0.6086956521739131 | 0.0 | 0.26292 |
| warehouse-10-20-10-2-1 | 100 | always_additive_defer | 5 | 1.000000 | 1.171715370742 | 0.0 | 196.6 | 0.0 | 2523.8 | 34.20000000000027 | 19454.0 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star | 5 | 1.000000 | 1.167907540038 | -0.003807830704000148 | 6642.6 | 6446.0 | 3088.44518 | 598.8451800000003 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.171715370742 | None | 196.6 | None | 2489.6 | None | 19454.0 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.171715370742 | 0.0 | 196.6 | 0.0 | 2384.8 | -104.79999999999973 | 19454.0 | 0.5 | 0.5 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.171715370742 | 0.0 | 196.6 | 0.0 | 2551.2 | 61.59999999999991 | 19454.0 | 0.5 | 0.5 | 0.16946 |
| warehouse-10-20-10-2-1 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.171715370742 | 0.0 | 196.6 | 0.0 | 2472.4 | -17.199999999999818 | 19454.0 | 0.6666666666666666 | 0.0 | 0.15948 |
| warehouse-10-20-10-2-1 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.171715370742 | 0.0 | 196.6 | 0.0 | 2462.2 | -27.40000000000009 | 19454.0 | 0.5 | 0.0 | 0.2246 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.171715370742 | 0.0 | 196.6 | 0.0 | 2492.4 | 2.800000000000182 | 19454.0 | 0.5 | 0.0 | 0.24388 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.171715370742 | 0.0 | 196.6 | 0.0 | 2472.6 | -17.0 | 19454.0 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.171715370742 | 0.0 | 196.6 | 0.0 | 2551.8 | 62.20000000000027 | 19454.0 | 0.6666666666666666 | 0.0 | 0.1504 |

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
      "ratio_worse_than_ltm_groups": 1,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair5e3_split_guarded_selector": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "repair5e4_closed_loop_utility_selector": {
      "ratio_worse_than_ltm_groups": 1,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 4
    },
    "repair5e5_crossfold_utility_reranker": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 4
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
  "case": "A",
  "oracle_positive": true,
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "recommended_action": "larger_multi_map_validation_then_phase5p5_runtime_export_design",
  "repair5e5_crossfold_utility_reranker_positive": true
}

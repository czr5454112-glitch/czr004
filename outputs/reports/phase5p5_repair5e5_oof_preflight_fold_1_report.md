# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-06-01 14:24:41

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight_fold_1.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight_fold_1_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight_fold_1_commands.jsonl`

## Provenance

- git branch: `phase4f5p5-stable-attention-lau`
- git commit: `db0f494`
- git dirty state: `tracked-dirty_untracked-present`
- clean tracked worktree: `False`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agent_counts: `[50, 100]`
- instances_per_setting: `3`
- instance_ids: `[6, 7, 8, 9, 10]`
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
| maze-32-32-4 | 50 | always_additive_defer | 5 | 1.000000 | 1.17595300704 | 0.0 | 406.0 | 0.0 | 186.8 | 1.200000000000017 | 20209.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | lacam_star | 5 | 1.000000 | 1.169407560264 | -0.006545446775999997 | 9631.6 | 9225.6 | 3135.86248 | 2950.26248 | None | None | None | 0.0 |
| maze-32-32-4 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.17595300704 | None | 406.0 | None | 185.6 | None | 20209.4 | None | None | 0.0 |
| maze-32-32-4 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.148784345352 | -0.02716866168800003 | 393.0 | -13.0 | 183.8 | -1.799999999999983 | 19560.2 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.167767980784 | -0.008185026255999928 | 399.6 | -6.399999999999977 | 185.2 | -0.4000000000000057 | 19887.4 | 0.25 | 0.75 | 0.3519 |
| maze-32-32-4 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.17595300704 | 0.0 | 406.0 | 0.0 | 183.8 | -1.799999999999983 | 20209.4 | 0.5714285714285714 | 0.0 | 0.37307999999999997 |
| maze-32-32-4 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.17595300704 | 0.0 | 406.0 | 0.0 | 184.4 | -1.1999999999999886 | 20209.4 | 0.25 | 0.0 | 0.45692 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.16151720481 | -0.014435802229999961 | 393.0 | -13.0 | 184.2 | -1.4000000000000057 | 19560.0 | 0.25 | 0.75 | 0.4111 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.17595300704 | 0.0 | 406.0 | 0.0 | 185.2 | -0.4000000000000057 | 20209.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.17595300704 | 0.0 | 406.0 | 0.0 | 184.6 | -1.0 | 20209.4 | 0.5714285714285714 | 0.0 | 0.36802 |
| maze-32-32-4 | 100 | always_additive_defer | 5 | 1.000000 | 1.259502918144 | 0.0 | 583.8 | 0.0 | 399.2 | 12.399999999999977 | 82754.2 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | lacam_star | 5 | 1.000000 | 1.343380856474 | 0.0838779383299999 | 10067.0 | 9483.2 | 3168.75826 | 2781.95826 | None | None | None | 0.0 |
| maze-32-32-4 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.259502918144 | None | 583.8 | None | 386.8 | None | 82754.2 | None | None | 0.0 |
| maze-32-32-4 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.246311931166 | -0.01319098697800003 | 543.0 | -40.799999999999955 | 392.2 | 5.399999999999977 | 70332.4 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.278179490348 | 0.018676572203999875 | 550.0 | -33.799999999999955 | 389.8 | 3.0 | 70758.4 | 0.25 | 0.75 | 0.35324 |
| maze-32-32-4 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.259502918144 | 0.0 | 583.8 | 0.0 | 390.2 | 3.3999999999999773 | 82754.2 | 0.5714285714285714 | 0.0 | 0.39058 |
| maze-32-32-4 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.259502918144 | 0.0 | 583.8 | 0.0 | 390.0 | 3.1999999999999886 | 82754.2 | 0.2857142857142857 | 0.0 | 0.45342 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.259502918144 | 0.0 | 583.8 | 0.0 | 396.2 | 9.399999999999977 | 82754.2 | 0.2857142857142857 | 0.0 | 0.44638 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.259502918144 | 0.0 | 583.8 | 0.0 | 389.0 | 2.1999999999999886 | 82754.2 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.259502918144 | 0.0 | 583.8 | 0.0 | 397.0 | 10.199999999999989 | 82754.2 | 0.5714285714285714 | 0.0 | 0.35316 |
| random-32-32-20 | 50 | always_additive_defer | 5 | 1.000000 | 1.123790307662 | 0.0 | 225.6 | 0.0 | 159.4 | 1.200000000000017 | 11126.6 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | lacam_star | 5 | 1.000000 | 1.123487905596 | -0.00030240206599985164 | 11792.8 | 11567.199999999999 | 3161.22258 | 3003.0225800000003 | None | None | None | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.123790307662 | None | 225.6 | None | 158.2 | None | 11126.6 | None | None | 0.0 |
| random-32-32-20 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.123790307662 | 0.0 | 218.8 | -6.799999999999983 | 158.2 | 0.0 | 10787.0 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.123790307662 | 0.0 | 220.4 | -5.199999999999989 | 159.0 | 0.8000000000000114 | 10866.8 | 0.25 | 0.75 | 0.34362000000000004 |
| random-32-32-20 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.123790307662 | 0.0 | 225.6 | 0.0 | 159.8 | 1.6000000000000227 | 11126.6 | 0.5714285714285714 | 0.0 | 0.37082 |
| random-32-32-20 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.123790307662 | 0.0 | 223.6 | -2.0 | 159.4 | 1.200000000000017 | 11027.2 | 0.25 | 0.75 | 0.40396 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.123790307662 | 0.0 | 224.8 | -0.799999999999983 | 158.6 | 0.4000000000000057 | 11086.4 | 0.25 | 0.75 | 0.45666 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.123790307662 | 0.0 | 225.6 | 0.0 | 160.2 | 2.0 | 11126.6 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.123790307662 | 0.0 | 225.6 | 0.0 | 160.0 | 1.8000000000000114 | 11126.6 | 0.5714285714285714 | 0.0 | 0.35660000000000003 |
| random-32-32-20 | 100 | always_additive_defer | 5 | 1.000000 | 1.247950214826 | 0.0 | 306.0 | 0.0 | 324.2 | 0.19999999999998863 | 44110.0 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | lacam_star | 5 | 1.000000 | 1.274000205726 | 0.026049990900000042 | 6609.4 | 6303.4 | 3095.57436 | 2771.57436 | None | None | None | 0.0 |
| random-32-32-20 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.247950214826 | None | 306.0 | None | 324.0 | None | 44110.0 | None | None | 0.0 |
| random-32-32-20 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.217382394086 | -0.030567820739999974 | 297.0 | -9.0 | 322.2 | -1.8000000000000114 | 43835.8 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.250517709248 | 0.002567494421999994 | 311.8 | 5.800000000000011 | 320.8 | -3.1999999999999886 | 49615.4 | 0.25 | 0.75 | 0.35218 |
| random-32-32-20 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.247950214826 | 0.0 | 306.0 | 0.0 | 320.4 | -3.6000000000000227 | 44110.0 | 0.5714285714285714 | 0.0 | 0.41056000000000004 |
| random-32-32-20 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.236406888276 | -0.01154332655000001 | 328.0 | 22.0 | 322.8 | -1.1999999999999886 | 52288.8 | 0.25 | 0.75 | 0.434 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.242969446308 | -0.0049807685179998895 | 324.6 | 18.600000000000023 | 324.2 | 0.19999999999998863 | 52482.6 | 0.25 | 0.75 | 0.42864 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.247950214826 | 0.0 | 306.0 | 0.0 | 322.0 | -2.0 | 44110.0 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.247950214826 | 0.0 | 306.0 | 0.0 | 319.4 | -4.600000000000023 | 44110.0 | 0.5714285714285714 | 0.0 | 0.3548 |
| warehouse-10-20-10-2-1 | 50 | always_additive_defer | 5 | 1.000000 | 1.081685295278 | 0.0 | 399.0 | 0.0 | 1296.6 | -4.0 | 19799.4 | 0.3333333333333333 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star | 5 | 1.000000 | 1.080263179398 | -0.0014221158800000744 | 7460.0 | 7061.0 | 3100.15984 | 1799.55984 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.081685295278 | None | 399.0 | None | 1300.6 | None | 19799.4 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.081685295278 | 0.0 | 399.0 | 0.0 | 1267.8 | -32.799999999999955 | 19799.4 | 0.3333333333333333 | 0.6666666666666666 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.081685295278 | 0.0 | 399.0 | 0.0 | 1316.4 | 15.800000000000182 | 19799.4 | 0.3333333333333333 | 0.6666666666666666 | 0.3353 |
| warehouse-10-20-10-2-1 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.081685295278 | 0.0 | 399.0 | 0.0 | 1328.6 | 28.0 | 19799.4 | 0.6 | 0.0 | 0.35128 |
| warehouse-10-20-10-2-1 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.081685295278 | 0.0 | 399.0 | 0.0 | 1328.8 | 28.200000000000045 | 19799.4 | 0.3333333333333333 | 0.0 | 0.41534 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.081685295278 | 0.0 | 399.0 | 0.0 | 1328.2 | 27.600000000000136 | 19799.4 | 0.3333333333333333 | 0.0 | 0.37066 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.081685295278 | 0.0 | 398.8 | -0.19999999999998863 | 1371.8 | 71.20000000000005 | 19799.4 | 0.35714285714285715 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.081685295278 | 0.0 | 399.0 | 0.0 | 1290.6 | -10.0 | 19799.4 | 0.6 | 0.0 | 0.31488 |
| warehouse-10-20-10-2-1 | 100 | always_additive_defer | 5 | 1.000000 | 1.154685179194 | 0.0 | 201.0 | 0.0 | 2598.2 | 28.0 | 19896.0 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star | 5 | 1.000000 | 1.143462498768 | -0.011222680426000053 | 6778.4 | 6577.4 | 3088.46774 | 518.2677400000002 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.154685179194 | None | 201.0 | None | 2570.2 | None | 19896.0 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.154685179194 | 0.0 | 201.0 | 0.0 | 2493.6 | -76.59999999999991 | 19896.0 | 0.5 | 0.5 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.154685179194 | 0.0 | 201.0 | 0.0 | 2580.2 | 10.0 | 19896.0 | 0.5 | 0.5 | 0.1922 |
| warehouse-10-20-10-2-1 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.154685179194 | 0.0 | 201.0 | 0.0 | 2553.8 | -16.399999999999636 | 19896.0 | 0.6666666666666666 | 0.0 | 0.16799999999999998 |
| warehouse-10-20-10-2-1 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.154685179194 | 0.0 | 201.0 | 0.0 | 2571.2 | 1.0 | 19896.0 | 0.5 | 0.0 | 0.23992 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.154685179194 | 0.0 | 201.0 | 0.0 | 2584.0 | 13.800000000000182 | 19896.0 | 0.5 | 0.0 | 0.20592 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.154685179194 | 0.0 | 201.0 | 0.0 | 2527.6 | -42.59999999999991 | 19896.0 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.154685179194 | 0.0 | 201.0 | 0.0 | 2563.8 | -6.399999999999636 | 19896.0 | 0.6666666666666666 | 0.0 | 0.19468 |

## Stop Condition Snapshot

{
  "method_flags": {
    "always_additive_defer": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "lacam_star": {
      "ratio_worse_than_ltm_groups": 2,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "oracle_teacher_forced_best_safe_update_static_proxy": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair5d_composite_diagnostic_distilled": {
      "ratio_worse_than_ltm_groups": 2,
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
      "ratio_worse_than_ltm_groups": 0,
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
  "case": "A",
  "oracle_positive": true,
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "recommended_action": "larger_multi_map_validation_then_phase5p5_runtime_export_design",
  "repair5e5_crossfold_utility_reranker_positive": true
}

# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-06-01 15:14:46

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight_fold_3.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight_fold_3_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight_fold_3_commands.jsonl`

## Provenance

- git branch: `phase4f5p5-stable-attention-lau`
- git commit: `db0f494`
- git dirty state: `tracked-dirty_untracked-present`
- clean tracked worktree: `False`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agent_counts: `[50, 100]`
- instances_per_setting: `3`
- instance_ids: `[16, 17, 18, 19, 20]`
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
| maze-32-32-4 | 50 | always_additive_defer | 5 | 1.000000 | 1.1077440817918 | 0.0 | 435.8 | 0.0 | 184.6 | -2.0 | 21638.6 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | lacam_star | 5 | 1.000000 | 1.1157021627086001 | 0.007958080916800059 | 8760.4 | 8324.6 | 3139.70266 | 2953.10266 | None | None | None | 0.0 |
| maze-32-32-4 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.1077440817918 | None | 435.8 | None | 186.6 | None | 21638.6 | None | None | 0.0 |
| maze-32-32-4 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.0975390883312 | -0.01020499346060011 | 422.6 | -13.199999999999989 | 185.0 | -1.5999999999999943 | 20929.4 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.1114151033406 | 0.0036710215487998354 | 438.6 | 2.8000000000000114 | 185.8 | -0.799999999999983 | 21778.8 | 0.25 | 0.75 | 0.34702 |
| maze-32-32-4 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.1077440817918 | 0.0 | 435.8 | 0.0 | 187.0 | 0.4000000000000057 | 21638.6 | 0.5714285714285714 | 0.0 | 0.37198 |
| maze-32-32-4 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.1077440817918 | 0.0 | 435.8 | 0.0 | 187.4 | 0.8000000000000114 | 21638.6 | 0.25 | 0.0 | 0.43395999999999996 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.1071372161368 | -0.0006068656550000107 | 423.6 | -12.199999999999989 | 185.8 | -0.799999999999983 | 20978.8 | 0.25 | 0.75 | 0.43648 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.1077440817918 | 0.0 | 435.8 | 0.0 | 187.4 | 0.8000000000000114 | 21638.6 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.1077440817918 | 0.0 | 435.8 | 0.0 | 188.2 | 1.5999999999999943 | 21638.6 | 0.5714285714285714 | 0.0 | 0.41376 |
| maze-32-32-4 | 100 | always_additive_defer | 5 | 1.000000 | 1.201815701882 | 0.0 | 584.6 | 0.0 | 391.4 | 3.7999999999999545 | 85089.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | lacam_star | 5 | 1.000000 | 1.261191108758 | 0.05937540687599996 | 7454.2 | 6869.599999999999 | 3140.56838 | 2752.9683800000003 | None | None | None | 0.0 |
| maze-32-32-4 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.201815701882 | None | 584.6 | None | 387.6 | None | 85089.4 | None | None | 0.0 |
| maze-32-32-4 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.1809781797180001 | -0.02083752216399981 | 568.2 | -16.399999999999977 | 387.6 | 0.0 | 81238.0 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.205305065884 | 0.0034893640020001726 | 598.8 | 14.199999999999932 | 392.2 | 4.599999999999966 | 88372.2 | 0.25 | 0.75 | 0.34706 |
| maze-32-32-4 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.201815701882 | 0.0 | 584.6 | 0.0 | 390.4 | 2.7999999999999545 | 85089.4 | 0.5714285714285714 | 0.0 | 0.37774 |
| maze-32-32-4 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.201815701882 | 0.0 | 584.6 | 0.0 | 388.6 | 1.0 | 85089.4 | 0.25 | 0.0 | 0.4467 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.201815701882 | 0.0 | 584.6 | 0.0 | 386.4 | -1.2000000000000455 | 85089.4 | 0.25 | 0.0 | 0.44216 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.201815701882 | 0.0 | 584.6 | 0.0 | 386.2 | -1.400000000000034 | 85089.4 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.201815701882 | 0.0 | 584.6 | 0.0 | 388.4 | 0.7999999999999545 | 85089.4 | 0.5714285714285714 | 0.0 | 0.35256 |
| random-32-32-20 | 50 | always_additive_defer | 5 | 1.000000 | 1.11039573014 | 0.0 | 219.2 | 0.0 | 160.2 | 1.1999999999999886 | 11635.6 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | lacam_star | 5 | 1.000000 | 1.113643203614 | 0.0032474734740000066 | 11092.6 | 10873.4 | 3143.4204600000003 | 2984.4204600000003 | None | None | None | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.11039573014 | None | 219.2 | None | 159.0 | None | 11635.6 | None | None | 0.0 |
| random-32-32-20 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.11055952599 | 0.00016379585000003694 | 211.8 | -7.399999999999977 | 167.6 | 8.599999999999994 | 10603.6 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.117316282746 | 0.006920552605999886 | 213.6 | -5.599999999999994 | 159.6 | 0.5999999999999943 | 10654.4 | 0.25 | 0.75 | 0.34358 |
| random-32-32-20 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.11039573014 | 0.0 | 219.2 | 0.0 | 159.0 | 0.0 | 11635.6 | 0.5714285714285714 | 0.0 | 0.37578 |
| random-32-32-20 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.113937904368 | 0.0035421742279999613 | 220.6 | 1.4000000000000057 | 159.8 | 0.8000000000000114 | 11787.2 | 0.25 | 0.75 | 0.41352 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.11191087734 | 0.0015151471999999 | 216.0 | -3.1999999999999886 | 177.6 | 18.599999999999994 | 11026.0 | 0.25 | 0.75 | 0.42894 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.11039573014 | 0.0 | 219.2 | 0.0 | 162.6 | 3.5999999999999943 | 11635.6 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.11039573014 | 0.0 | 219.2 | 0.0 | 160.0 | 1.0 | 11635.6 | 0.5714285714285714 | 0.0 | 0.3531 |
| random-32-32-20 | 100 | always_additive_defer | 5 | 1.000000 | 1.257231836326 | 0.0 | 268.8 | 0.0 | 318.8 | -0.39999999999997726 | 33364.0 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | lacam_star | 5 | 1.000000 | 1.247880916062 | -0.009350920264000084 | 4288.2 | 4019.3999999999996 | 3057.9073 | 2738.7073 | None | None | None | 0.0 |
| random-32-32-20 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.257231836326 | None | 268.8 | None | 319.2 | None | 33364.0 | None | None | 0.0 |
| random-32-32-20 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.2328982862 | -0.024333550126000025 | 240.4 | -28.400000000000006 | 320.4 | 1.1999999999999886 | 25199.2 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.238977313556 | -0.018254522769999948 | 242.4 | -26.400000000000006 | 319.0 | -0.19999999999998863 | 24805.8 | 0.25 | 0.75 | 0.35860000000000003 |
| random-32-32-20 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.257231836326 | 0.0 | 268.8 | 0.0 | 320.8 | 1.6000000000000227 | 33364.0 | 0.5714285714285714 | 0.0 | 0.4163 |
| random-32-32-20 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.252907999962 | -0.004323836363999911 | 245.4 | -23.400000000000006 | 319.8 | 0.6000000000000227 | 25892.8 | 0.25 | 0.75 | 0.45696 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.257231836326 | 0.0 | 268.8 | 0.0 | 319.4 | 0.19999999999998863 | 33364.0 | 0.25 | 0.0 | 0.43078 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.257231836326 | 0.0 | 268.8 | 0.0 | 320.0 | 0.8000000000000114 | 33364.0 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.257231836326 | 0.0 | 268.8 | 0.0 | 317.8 | -1.3999999999999773 | 33364.0 | 0.5714285714285714 | 0.0 | 0.34122 |
| warehouse-10-20-10-2-1 | 50 | always_additive_defer | 5 | 1.000000 | 1.104304243934 | 0.0 | 399.8 | 0.0 | 1244.4 | 11.800000000000182 | 19836.2 | 0.3333333333333333 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star | 5 | 1.000000 | 1.090236015286 | -0.014068228648000058 | 10070.4 | 9670.6 | 3124.4262400000002 | 1891.8262400000003 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 5 | 1.000000 | 1.104304243934 | None | 399.8 | None | 1232.6 | None | 19836.2 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.104304243934 | 0.0 | 399.4 | -0.4000000000000341 | 1302.4 | 69.80000000000018 | 19836.2 | 0.38461538461538464 | 0.6153846153846154 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.104304243934 | 0.0 | 399.8 | 0.0 | 1293.0 | 60.40000000000009 | 19836.2 | 0.3333333333333333 | 0.6666666666666666 | 0.27894 |
| warehouse-10-20-10-2-1 | 50 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.104304243934 | 0.0 | 399.6 | -0.19999999999998863 | 1310.8 | 78.20000000000005 | 19836.2 | 0.6086956521739131 | 0.0 | 0.25712 |
| warehouse-10-20-10-2-1 | 50 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.104304243934 | 0.0 | 399.6 | -0.19999999999998863 | 1329.6 | 97.0 | 19836.2 | 0.35714285714285715 | 0.0 | 0.4482 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.104304243934 | 0.0 | 399.6 | -0.19999999999998863 | 1343.8 | 111.20000000000005 | 19836.2 | 0.35714285714285715 | 0.0 | 0.30814 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.104304243934 | 0.0 | 399.8 | 0.0 | 1269.6 | 37.0 | 19836.2 | 0.3333333333333333 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.104304243934 | 0.0 | 399.8 | 0.0 | 1288.0 | 55.40000000000009 | 19836.2 | 0.6 | 0.0 | 0.27602 |
| warehouse-10-20-10-2-1 | 100 | always_additive_defer | 5 | 1.000000 | 1.1848493966359999 | 0.0 | 225.8 | -0.19999999999998863 | 2634.2 | 52.59999999999991 | 22390.6 | 0.5555555555555556 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star | 5 | 1.000000 | 1.163132724414 | -0.02171667222199991 | 6559.8 | 6333.8 | 3081.25764 | 499.6576399999999 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 5 | 1.000000 | 1.1848493966359999 | None | 226.0 | None | 2581.6 | None | 22390.6 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 5 | 1.000000 | 1.1848493966359999 | 0.0 | 226.0 | 0.0 | 2456.8 | -124.79999999999973 | 22390.6 | 0.5 | 0.5 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5d_composite_diagnostic_distilled | 5 | 1.000000 | 1.1848493966359999 | 0.0 | 226.0 | 0.0 | 2604.6 | 23.0 | 22390.6 | 0.5 | 0.5 | 0.16104000000000002 |
| warehouse-10-20-10-2-1 | 100 | repair5e3_split_guarded_selector | 5 | 1.000000 | 1.1848493966359999 | 0.0 | 226.0 | 0.0 | 2596.8 | 15.200000000000273 | 22390.6 | 0.6666666666666666 | 0.0 | 0.16338 |
| warehouse-10-20-10-2-1 | 100 | repair5e4_closed_loop_utility_selector | 5 | 1.000000 | 1.1848493966359999 | 0.0 | 226.0 | 0.0 | 2618.8 | 37.20000000000027 | 22390.6 | 0.5 | 0.0 | 0.19052 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker | 5 | 1.000000 | 1.1848493966359999 | 0.0 | 225.8 | -0.19999999999998863 | 2596.8 | 15.200000000000273 | 22390.6 | 0.5555555555555556 | 0.0 | 0.16314 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 5 | 1.000000 | 1.1848493966359999 | 0.0 | 226.0 | 0.0 | 2579.0 | -2.599999999999909 | 22390.6 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5e_caseb_ood_guard_distilled | 5 | 1.000000 | 1.1848493966359999 | 0.0 | 226.0 | 0.0 | 2634.4 | 52.80000000000018 | 22390.6 | 0.6666666666666666 | 0.0 | 0.19608 |

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
      "ratio_worse_than_ltm_groups": 1,
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
      "ratio_worse_than_ltm_groups": 1,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 4
    },
    "repair5e5_crossfold_utility_reranker": {
      "ratio_worse_than_ltm_groups": 1,
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
  "case": "B",
  "oracle_positive": true,
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "recommended_action": "e5_not_promotable_inspect_crossfold_utility_reranker",
  "repair5e5_crossfold_utility_reranker_positive": false
}

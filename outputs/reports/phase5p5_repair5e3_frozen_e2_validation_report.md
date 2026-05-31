# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-05-31 22:11:47

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e3_frozen_e2_validation\phase5p5_repair5e3_frozen_e2_validation.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e3_frozen_e2_validation\phase5p5_repair5e3_frozen_e2_validation_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e3_frozen_e2_validation\phase5p5_repair5e3_frozen_e2_validation_commands.jsonl`

## Provenance

- git branch: `phase4f5p5-stable-attention-lau`
- git commit: `c609bb8`
- git dirty state: `tracked-dirty_untracked-present`
- clean tracked worktree: `False`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agent_counts: `[50, 100]`
- instances_per_setting: `10`
- instance_ids: `[4, 5, 6, 7, 8, 9, 10, 11, 12, 13]`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`
- methods: `['lacam_star', 'lacam_star_ltm', 'always_additive_defer', 'repair5d_composite_diagnostic_distilled', 'repair5e_caseb_ood_guard_distilled', 'repair5e2_guarded_oracle_aligned_selector', 'repair5e2_guarded_oracle_aligned_selector_force_additive_parity', 'oracle_teacher_forced_best_safe_update_static_proxy']`
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

## Group Summary

| map | agents | method | runs | success | ratio | d ratio | expanded | d expanded | TTFS ms | d TTFS | pibt | fallback | non-additive | overhead ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| maze-32-32-4 | 50 | always_additive_defer | 10 | 1.000000 | 1.179648373932 | 0.0 | 418.6 | 0.0 | 180.9 | -2.9000000000000057 | 20784.6 | 0.25 | 0.0 | 0.00146 |
| maze-32-32-4 | 50 | lacam_star | 10 | 1.000000 | 1.183694077136 | 0.004045703203999995 | 9220.5 | 8801.9 | 3134.48348 | 2950.6834799999997 | None | None | None | 0.0 |
| maze-32-32-4 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.179648373932 | None | 418.6 | None | 183.8 | None | 20784.6 | None | None | 0.0 |
| maze-32-32-4 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.156527908372 | -0.023120465560000136 | 405.6 | -13.0 | 182.9 | -0.9000000000000057 | 20135.1 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 50 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.17980087608 | 0.00015250214799999995 | 419.5 | 0.8999999999999773 | 185.5 | 1.6999999999999886 | 20828.3 | 0.25 | 0.75 | 0.34251 |
| maze-32-32-4 | 50 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.179648373932 | 0.0 | 418.6 | 0.0 | 183.3 | -0.5 | 20784.6 | 0.25 | 0.0 | 0.37118 |
| maze-32-32-4 | 50 | repair5e2_guarded_oracle_aligned_selector_force_additive_parity | 10 | 1.000000 | 1.179648373932 | 0.0 | 418.6 | 0.0 | 183.3 | -0.5 | 20784.6 | 0.25 | 0.0 | 0.0014 |
| maze-32-32-4 | 50 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.179648373932 | 0.0 | 418.6 | 0.0 | 187.0 | 3.1999999999999886 | 20784.6 | 0.5714285714285714 | 0.0 | 0.34122 |
| maze-32-32-4 | 100 | always_additive_defer | 10 | 1.000000 | 1.274641298306 | 0.0 | 570.7 | 0.0 | 384.9 | -1.400000000000034 | 76626.8 | 0.25 | 0.0 | 0.00141 |
| maze-32-32-4 | 100 | lacam_star | 10 | 1.000000 | 1.353079659015 | 0.07843836070900001 | 9841.2 | 9270.5 | 3151.62374 | 2765.32374 | None | None | None | 0.0 |
| maze-32-32-4 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.274641298306 | None | 570.7 | None | 386.3 | None | 76626.8 | None | None | 0.0 |
| maze-32-32-4 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.2465909347620001 | -0.028050363543999923 | 524.7 | -46.0 | 385.9 | -0.4000000000000341 | 67039.6 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 100 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.279410197178 | 0.004768898872000049 | 517.9 | -52.80000000000007 | 385.2 | -1.1000000000000227 | 61026.1 | 0.25 | 0.75 | 0.33855 |
| maze-32-32-4 | 100 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.277044530069 | 0.0024032317630000577 | 538.9 | -31.800000000000068 | 385.0 | -1.3000000000000114 | 64830.1 | 0.25 | 0.75 | 0.35187 |
| maze-32-32-4 | 100 | repair5e2_guarded_oracle_aligned_selector_force_additive_parity | 10 | 1.000000 | 1.274641298306 | 0.0 | 570.7 | 0.0 | 388.4 | 2.099999999999966 | 76626.8 | 0.25 | 0.0 | 0.00148 |
| maze-32-32-4 | 100 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.274641298306 | 0.0 | 570.7 | 0.0 | 385.3 | -1.0 | 76626.8 | 0.5714285714285714 | 0.0 | 0.35552 |
| random-32-32-20 | 50 | always_additive_defer | 10 | 1.000000 | 1.136125751546 | 0.0 | 225.7 | 0.0 | 157.3 | -0.09999999999999432 | 11107.4 | 0.25 | 0.0 | 0.00146 |
| random-32-32-20 | 50 | lacam_star | 10 | 1.000000 | 1.118625719692 | -0.017500031853999953 | 10203.8 | 9978.099999999999 | 3140.92728 | 2983.52728 | None | None | None | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.136125751546 | None | 225.7 | None | 157.4 | None | 11107.4 | None | None | 0.0 |
| random-32-32-20 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.133315930043 | -0.0028098215029999096 | 222.9 | -2.799999999999983 | 157.1 | -0.30000000000001137 | 11153.7 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 50 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.134944649184 | -0.001181102361999864 | 221.1 | -4.599999999999994 | 156.6 | -0.8000000000000114 | 10894.5 | 0.25 | 0.75 | 0.34401 |
| random-32-32-20 | 50 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.136125751546 | 0.0 | 227.4 | 1.700000000000017 | 158.7 | 1.299999999999983 | 11466.5 | 0.25 | 0.75 | 0.34285 |
| random-32-32-20 | 50 | repair5e2_guarded_oracle_aligned_selector_force_additive_parity | 10 | 1.000000 | 1.136125751546 | 0.0 | 225.7 | 0.0 | 158.5 | 1.0999999999999943 | 11107.4 | 0.25 | 0.0 | 0.00141 |
| random-32-32-20 | 50 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.136125751546 | 0.0 | 225.7 | 0.0 | 157.1 | -0.30000000000001137 | 11107.4 | 0.5714285714285714 | 0.0 | 0.35441999999999996 |
| random-32-32-20 | 100 | always_additive_defer | 10 | 1.000000 | 1.26309792983 | 0.0 | 282.5 | 0.0 | 317.0 | 1.8999999999999773 | 36713.9 | 0.25 | 0.0 | 0.00146 |
| random-32-32-20 | 100 | lacam_star | 10 | 1.000000 | 1.282298345536 | 0.01920041570599995 | 6423.1 | 6140.6 | 3092.5141 | 2777.4141 | None | None | None | 0.0 |
| random-32-32-20 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.26309792983 | None | 282.5 | None | 315.1 | None | 36713.9 | None | None | 0.0 |
| random-32-32-20 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.238276991717 | -0.024820938113000013 | 290.3 | 7.800000000000011 | 317.3 | 2.1999999999999886 | 39619.1 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 100 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.265167796623 | 0.0020698667929999193 | 309.5 | 27.0 | 316.2 | 1.099999999999966 | 46537.8 | 0.25 | 0.75 | 0.33272999999999997 |
| random-32-32-20 | 100 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.270130312873 | 0.007032383042999912 | 286.0 | 3.5 | 316.4 | 1.2999999999999545 | 38181.5 | 0.25 | 0.75 | 0.37185999999999997 |
| random-32-32-20 | 100 | repair5e2_guarded_oracle_aligned_selector_force_additive_parity | 10 | 1.000000 | 1.26309792983 | 0.0 | 282.5 | 0.0 | 316.0 | 0.8999999999999773 | 36713.9 | 0.25 | 0.0 | 0.00138 |
| random-32-32-20 | 100 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.26309792983 | 0.0 | 282.5 | 0.0 | 317.0 | 1.8999999999999773 | 36713.9 | 0.5714285714285714 | 0.0 | 0.34011 |
| warehouse-10-20-10-2-1 | 50 | always_additive_defer | 10 | 1.000000 | 1.084755136352 | 0.0 | 393.6 | 0.0 | 1227.7 | -0.20000000000004547 | 19527.8 | 0.3333333333333333 | 0.0 | 0.0013 |
| warehouse-10-20-10-2-1 | 50 | lacam_star | 10 | 1.000000 | 1.0894851463620001 | 0.004730010010000063 | 7208.3 | 6814.7 | 3097.22245 | 1869.3224500000001 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.084755136352 | None | 393.6 | None | 1227.9 | None | 19527.8 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.084755136352 | 0.0 | 393.4 | -0.20000000000004547 | 1235.0 | 7.099999999999909 | 19527.8 | 0.35714285714285715 | 0.6428571428571429 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.089946125579 | 0.005190989226999898 | 374.5 | -19.100000000000023 | 1268.3 | 40.399999999999864 | 18577.8 | 0.3448275862068966 | 0.6551724137931034 | 0.29767 |
| warehouse-10-20-10-2-1 | 50 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.089946125579 | 0.005190989226999898 | 368.2 | -25.400000000000034 | 1299.7 | 71.79999999999995 | 18272.8 | 0.5142857142857142 | 0.0 | 0.25922 |
| warehouse-10-20-10-2-1 | 50 | repair5e2_guarded_oracle_aligned_selector_force_additive_parity | 10 | 1.000000 | 1.084755136352 | 0.0 | 393.6 | 0.0 | 1253.1 | 25.199999999999818 | 19527.8 | 0.3333333333333333 | 0.0 | 0.00123 |
| warehouse-10-20-10-2-1 | 50 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.089946125579 | 0.005190989226999898 | 374.4 | -19.200000000000045 | 1304.8 | 76.89999999999986 | 18577.8 | 0.6086956521739131 | 0.0 | 0.27112 |
| warehouse-10-20-10-2-1 | 100 | always_additive_defer | 10 | 1.000000 | 1.164186801731 | 0.0 | 207.1 | 0.0 | 2424.9 | -29.5 | 20514.3 | 0.5 | 0.0 | 0.00074 |
| warehouse-10-20-10-2-1 | 100 | lacam_star | 10 | 1.000000 | 1.155208912119 | -0.008977889612000078 | 6723.4 | 6516.299999999999 | 3091.31009 | 636.9100899999999 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.164186801731 | None | 207.1 | None | 2454.4 | None | 20514.3 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.164186801731 | 0.0 | 207.1 | 0.0 | 2343.7 | -110.70000000000027 | 20514.3 | 0.5 | 0.5 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.164186801731 | 0.0 | 207.1 | 0.0 | 2437.3 | -17.09999999999991 | 20514.3 | 0.5 | 0.5 | 0.18161 |
| warehouse-10-20-10-2-1 | 100 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.164186801731 | 0.0 | 207.1 | 0.0 | 2466.7 | 12.299999999999727 | 20514.3 | 0.6666666666666666 | 0.0 | 0.16728 |
| warehouse-10-20-10-2-1 | 100 | repair5e2_guarded_oracle_aligned_selector_force_additive_parity | 10 | 1.000000 | 1.164186801731 | 0.0 | 207.1 | 0.0 | 2471.6 | 17.199999999999818 | 20514.3 | 0.5 | 0.0 | 0.0008 |
| warehouse-10-20-10-2-1 | 100 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.164186801731 | 0.0 | 207.1 | 0.0 | 2450.1 | -4.300000000000182 | 20514.3 | 0.6666666666666666 | 0.0 | 0.19963 |

## Stop Condition Snapshot

{
  "method_flags": {
    "always_additive_defer": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "lacam_star": {
      "ratio_worse_than_ltm_groups": 4,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "oracle_teacher_forced_best_safe_update_static_proxy": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair5d_composite_diagnostic_distilled": {
      "ratio_worse_than_ltm_groups": 4,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair5e2_guarded_oracle_aligned_selector": {
      "ratio_worse_than_ltm_groups": 3,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 3
    },
    "repair5e2_guarded_oracle_aligned_selector_force_additive_parity": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "repair5e_caseb_ood_guard_distilled": {
      "ratio_worse_than_ltm_groups": 1,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    }
  },
  "oracle_replay_executed": true,
  "oracle_replay_scope": "static_rule_proxy",
  "paired_rows": 420,
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
  "recommended_action": "improve_composite_or_reranker_do_not_jump_to_delta_updateparams",
  "repair5d_positive": false
}

# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-06-01 11:44:27

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e4_preflight\phase5p5_repair5e4_preflight.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e4_preflight\phase5p5_repair5e4_preflight_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e4_preflight\phase5p5_repair5e4_preflight_commands.jsonl`

## Provenance

- git branch: `phase4f5p5-stable-attention-lau`
- git commit: `48b5c6d`
- git dirty state: `tracked-dirty_untracked-present`
- clean tracked worktree: `False`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agent_counts: `[50, 100]`
- instances_per_setting: `3`
- instance_ids: `[11, 12, 13, 14, 15, 16, 17, 18, 19, 20]`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`
- methods: `['lacam_star', 'lacam_star_ltm', 'always_additive_defer', 'repair5d_composite_diagnostic_distilled', 'repair5e_caseb_ood_guard_distilled', 'repair5e3_split_guarded_selector', 'repair5e4_closed_loop_utility_selector', 'repair5e4_closed_loop_utility_selector_force_additive_parity', 'oracle_teacher_forced_best_safe_update_static_proxy']`
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

## Group Summary

| map | agents | method | runs | success | ratio | d ratio | expanded | d expanded | TTFS ms | d TTFS | pibt | fallback | non-additive | overhead ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| maze-32-32-4 | 50 | always_additive_defer | 10 | 1.000000 | 1.1398036303879 | 0.0 | 438.3 | 0.0 | 185.2 | -0.4000000000000057 | 21738.9 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | lacam_star | 10 | 1.000000 | 1.1353676280713 | -0.004436002316599907 | 11151.7 | 10713.400000000001 | 3166.83758 | 2981.23758 | None | None | None | 0.0 |
| maze-32-32-4 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.1398036303879 | None | 438.3 | None | 185.6 | None | 21738.9 | None | None | 0.0 |
| maze-32-32-4 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.1218270639166 | -0.01797656647130008 | 426.1 | -12.199999999999989 | 185.9 | 0.30000000000001137 | 21104.7 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 50 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.1404840886363 | 0.0006804582483999067 | 448.2 | 9.899999999999977 | 186.9 | 1.3000000000000114 | 22234.4 | 0.25 | 0.75 | 0.35644 |
| maze-32-32-4 | 50 | repair5e3_split_guarded_selector | 10 | 1.000000 | 1.1398036303879 | 0.0 | 438.3 | 0.0 | 186.1 | 0.5 | 21738.9 | 0.5714285714285714 | 0.0 | 0.38794 |
| maze-32-32-4 | 50 | repair5e4_closed_loop_utility_selector | 10 | 1.000000 | 1.1398036303879 | 0.0 | 438.3 | 0.0 | 186.5 | 0.9000000000000057 | 21738.9 | 0.25 | 0.0 | 0.45336 |
| maze-32-32-4 | 50 | repair5e4_closed_loop_utility_selector_force_additive_parity | 10 | 1.000000 | 1.1398036303879 | 0.0 | 438.3 | 0.0 | 184.6 | -1.0 | 21738.9 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.1398036303879 | 0.0 | 438.3 | 0.0 | 185.8 | 0.20000000000001705 | 21738.9 | 0.5714285714285714 | 0.0 | 0.3538 |
| maze-32-32-4 | 100 | always_additive_defer | 10 | 1.000000 | 1.2492997628640001 | 0.0 | 566.0 | 0.0 | 393.2 | -1.400000000000034 | 71451.8 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | lacam_star | 10 | 1.000000 | 1.302659290742 | 0.05335952787799991 | 9039.0 | 8473.0 | 3166.01094 | 2771.41094 | None | None | None | 0.0 |
| maze-32-32-4 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.2492997628640001 | None | 566.0 | None | 394.6 | None | 71451.8 | None | None | 0.0 |
| maze-32-32-4 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.213692236461 | -0.03560752640300002 | 540.1 | -25.899999999999977 | 392.9 | -1.7000000000000455 | 67575.9 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 100 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.241398234957 | -0.00790152790700005 | 559.6 | -6.399999999999977 | 392.2 | -2.400000000000034 | 71592.8 | 0.25 | 0.75 | 0.33922 |
| maze-32-32-4 | 100 | repair5e3_split_guarded_selector | 10 | 1.000000 | 1.2492997628640001 | 0.0 | 566.0 | 0.0 | 393.9 | -0.7000000000000455 | 71451.8 | 0.5714285714285714 | 0.0 | 0.37596 |
| maze-32-32-4 | 100 | repair5e4_closed_loop_utility_selector | 10 | 1.000000 | 1.2492997628640001 | 0.0 | 566.0 | 0.0 | 393.1 | -1.5 | 71451.8 | 0.25 | 0.0 | 0.46736 |
| maze-32-32-4 | 100 | repair5e4_closed_loop_utility_selector_force_additive_parity | 10 | 1.000000 | 1.2492997628640001 | 0.0 | 566.0 | 0.0 | 391.9 | -2.7000000000000455 | 71451.8 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.2492997628640001 | 0.0 | 566.0 | 0.0 | 394.7 | 0.0999999999999659 | 71451.8 | 0.5714285714285714 | 0.0 | 0.35904 |
| random-32-32-20 | 50 | always_additive_defer | 10 | 1.000000 | 1.134427121036 | 0.0 | 223.3 | 0.0 | 160.2 | 0.799999999999983 | 11440.0 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | lacam_star | 10 | 1.000000 | 1.117631114516 | -0.016796006519999906 | 9087.0 | 8863.7 | 3124.59563 | 2965.1956299999997 | None | None | None | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.134427121036 | None | 223.3 | None | 159.4 | None | 11440.0 | None | None | 0.0 |
| random-32-32-20 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.125034508284 | -0.009392612751999874 | 225.7 | 2.3999999999999773 | 160.1 | 0.6999999999999886 | 12579.8 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 50 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.1299421918600001 | -0.004484929175999852 | 227.2 | 3.8999999999999773 | 160.6 | 1.1999999999999886 | 12544.1 | 0.25 | 0.75 | 0.3584 |
| random-32-32-20 | 50 | repair5e3_split_guarded_selector | 10 | 1.000000 | 1.134427121036 | 0.0 | 223.3 | 0.0 | 160.0 | 0.5999999999999943 | 11440.0 | 0.5714285714285714 | 0.0 | 0.41763 |
| random-32-32-20 | 50 | repair5e4_closed_loop_utility_selector | 10 | 1.000000 | 1.127065788059 | -0.007361332976999924 | 223.4 | 0.09999999999999432 | 160.8 | 1.4000000000000057 | 11643.5 | 0.25 | 0.75 | 0.42304 |
| random-32-32-20 | 50 | repair5e4_closed_loop_utility_selector_force_additive_parity | 10 | 1.000000 | 1.134427121036 | 0.0 | 223.3 | 0.0 | 160.2 | 0.799999999999983 | 11440.0 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.134427121036 | 0.0 | 223.3 | 0.0 | 160.4 | 1.0 | 11440.0 | 0.5714285714285714 | 0.0 | 0.36519 |
| random-32-32-20 | 100 | always_additive_defer | 10 | 1.000000 | 1.267150755212 | 0.0 | 268.2 | 0.0 | 319.8 | -1.0 | 32135.3 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | lacam_star | 10 | 1.000000 | 1.265316282856 | -0.0018344723559999832 | 5482.6 | 5214.400000000001 | 3079.55167 | 2758.7516699999996 | None | None | None | 0.0 |
| random-32-32-20 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.267150755212 | None | 268.2 | None | 320.8 | None | 32135.3 | None | None | 0.0 |
| random-32-32-20 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.24606010222 | -0.02109065299200008 | 261.8 | -6.399999999999977 | 322.9 | 2.099999999999966 | 30319.3 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 100 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.258378732356 | -0.008772022855999984 | 275.0 | 6.800000000000011 | 318.1 | -2.6999999999999886 | 34172.1 | 0.25 | 0.75 | 0.34647 |
| random-32-32-20 | 100 | repair5e3_split_guarded_selector | 10 | 1.000000 | 1.267150755212 | 0.0 | 268.2 | 0.0 | 320.6 | -0.19999999999998863 | 32135.3 | 0.5714285714285714 | 0.0 | 0.41057 |
| random-32-32-20 | 100 | repair5e4_closed_loop_utility_selector | 10 | 1.000000 | 1.269562964201 | 0.0024122089889999643 | 261.7 | -6.5 | 319.8 | -1.0 | 30142.8 | 0.25 | 0.75 | 0.43139 |
| random-32-32-20 | 100 | repair5e4_closed_loop_utility_selector_force_additive_parity | 10 | 1.000000 | 1.267150755212 | 0.0 | 268.2 | 0.0 | 320.4 | -0.4000000000000341 | 32135.3 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.267150755212 | 0.0 | 268.2 | 0.0 | 322.6 | 1.8000000000000114 | 32135.3 | 0.5714285714285714 | 0.0 | 0.38067 |
| warehouse-10-20-10-2-1 | 50 | always_additive_defer | 10 | 1.000000 | 1.082185273507 | 0.0 | 381.5 | -0.10000000000002274 | 1317.0 | 6.2000000000000455 | 18927.1 | 0.3448275862068966 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star | 10 | 1.000000 | 1.079187273959 | -0.002997999547999841 | 10061.9 | 9680.3 | 3116.64007 | 1805.84007 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.082185273507 | None | 381.6 | None | 1310.8 | None | 18927.1 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.082185273507 | 0.0 | 363.6 | -18.0 | 1320.0 | 9.200000000000045 | 18037.1 | 0.35714285714285715 | 0.6428571428571429 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.082185273507 | 0.0 | 381.4 | -0.20000000000004547 | 1320.4 | 9.600000000000136 | 18927.1 | 0.35714285714285715 | 0.6428571428571429 | 0.25257 |
| warehouse-10-20-10-2-1 | 50 | repair5e3_split_guarded_selector | 10 | 1.000000 | 1.082185273507 | 0.0 | 381.6 | 0.0 | 1309.6 | -1.2000000000000455 | 18927.1 | 0.6 | 0.0 | 0.2907 |
| warehouse-10-20-10-2-1 | 50 | repair5e4_closed_loop_utility_selector | 10 | 1.000000 | 1.082185273507 | 0.0 | 381.5 | -0.10000000000002274 | 1305.5 | -5.2999999999999545 | 18927.1 | 0.3448275862068966 | 0.0 | 0.32294 |
| warehouse-10-20-10-2-1 | 50 | repair5e4_closed_loop_utility_selector_force_additive_parity | 10 | 1.000000 | 1.082185273507 | 0.0 | 381.6 | 0.0 | 1311.3 | 0.5 | 18927.1 | 0.3333333333333333 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.082185273507 | 0.0 | 381.5 | -0.10000000000002274 | 1340.7 | 29.90000000000009 | 18927.1 | 0.6041666666666666 | 0.0 | 0.26957 |
| warehouse-10-20-10-2-1 | 100 | always_additive_defer | 10 | 1.000000 | 1.178282383689 | 0.0 | 211.3 | 0.0 | 2621.5 | 18.59999999999991 | 20922.3 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star | 10 | 1.000000 | 1.165520132226 | -0.012762251462999918 | 6561.2 | 6349.9 | 3079.32853 | 476.4285299999997 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.178282383689 | None | 211.3 | None | 2602.9 | None | 20922.3 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.178282383689 | 0.0 | 211.3 | 0.0 | 2585.4 | -17.5 | 20922.3 | 0.5 | 0.5 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.178282383689 | 0.0 | 211.2 | -0.10000000000002274 | 2651.5 | 48.59999999999991 | 20922.3 | 0.5263157894736842 | 0.47368421052631576 | 0.13532 |
| warehouse-10-20-10-2-1 | 100 | repair5e3_split_guarded_selector | 10 | 1.000000 | 1.178282383689 | 0.0 | 211.2 | -0.10000000000002274 | 2637.1 | 34.19999999999982 | 20922.3 | 0.6785714285714286 | 0.0 | 0.15515 |
| warehouse-10-20-10-2-1 | 100 | repair5e4_closed_loop_utility_selector | 10 | 1.000000 | 1.178282383689 | 0.0 | 211.3 | 0.0 | 2639.7 | 36.79999999999973 | 20922.3 | 0.5 | 0.0 | 0.25695 |
| warehouse-10-20-10-2-1 | 100 | repair5e4_closed_loop_utility_selector_force_additive_parity | 10 | 1.000000 | 1.178282383689 | 0.0 | 211.3 | 0.0 | 2630.7 | 27.799999999999727 | 20922.3 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.178282383689 | 0.0 | 211.3 | 0.0 | 2623.5 | 20.59999999999991 | 20922.3 | 0.6666666666666666 | 0.0 | 0.1468 |

## Stop Condition Snapshot

{
  "method_flags": {
    "always_additive_defer": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "lacam_star": {
      "ratio_worse_than_ltm_groups": 1,
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
    "repair5e4_closed_loop_utility_selector_force_additive_parity": {
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
  "paired_rows": 480,
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
  "recommended_action": "e4_not_promotable_inspect_utility_labels_guard_and_feature_calibration",
  "repair5e4_closed_loop_utility_selector_positive": false
}

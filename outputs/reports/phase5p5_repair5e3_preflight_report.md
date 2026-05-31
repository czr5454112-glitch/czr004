# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-05-31 22:14:45

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e3_preflight\phase5p5_repair5e3_preflight.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e3_preflight\phase5p5_repair5e3_preflight_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e3_preflight\phase5p5_repair5e3_preflight_commands.jsonl`

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
- methods: `['lacam_star', 'lacam_star_ltm', 'always_additive_defer', 'repair5d_composite_diagnostic_distilled', 'repair5e_caseb_ood_guard_distilled', 'repair5e2_guarded_oracle_aligned_selector', 'repair5e3_split_guarded_selector', 'repair5e3_split_guarded_selector_force_additive_parity', 'oracle_teacher_forced_best_safe_update_static_proxy']`
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
| maze-32-32-4 | 50 | always_additive_defer | 10 | 1.000000 | 1.179648373932 | 0.0 | 418.6 | 0.0 | 185.4 | 0.5 | 20784.6 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | lacam_star | 10 | 1.000000 | 1.183694077136 | 0.004045703203999995 | 8910.6 | 8492.0 | 3135.96809 | 2951.0680899999998 | None | None | None | 0.0 |
| maze-32-32-4 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.179648373932 | None | 418.6 | None | 184.9 | None | 20784.6 | None | None | 0.0 |
| maze-32-32-4 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.156527908372 | -0.023120465560000136 | 405.6 | -13.0 | 183.9 | -1.0 | 20135.1 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 50 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.17980087608 | 0.00015250214799999995 | 419.5 | 0.8999999999999773 | 184.3 | -0.5999999999999943 | 20828.3 | 0.25 | 0.75 | 0.32954 |
| maze-32-32-4 | 50 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.179648373932 | 0.0 | 418.6 | 0.0 | 186.0 | 1.0999999999999943 | 20784.6 | 0.25 | 0.0 | 0.35232 |
| maze-32-32-4 | 50 | repair5e3_split_guarded_selector | 10 | 1.000000 | 1.179648373932 | 0.0 | 418.6 | 0.0 | 185.0 | 0.09999999999999432 | 20784.6 | 0.5714285714285714 | 0.0 | 0.36313 |
| maze-32-32-4 | 50 | repair5e3_split_guarded_selector_force_additive_parity | 10 | 1.000000 | 1.179648373932 | 0.0 | 418.6 | 0.0 | 184.8 | -0.09999999999999432 | 20784.6 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.179648373932 | 0.0 | 418.6 | 0.0 | 185.9 | 1.0 | 20784.6 | 0.5714285714285714 | 0.0 | 0.32745 |
| maze-32-32-4 | 100 | always_additive_defer | 10 | 1.000000 | 1.274641298306 | 0.0 | 570.7 | 0.0 | 391.0 | -3.6999999999999886 | 76626.8 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | lacam_star | 10 | 1.000000 | 1.353079659015 | 0.07843836070900001 | 9716.2 | 9145.5 | 3156.7156 | 2762.0156 | None | None | None | 0.0 |
| maze-32-32-4 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.274641298306 | None | 570.7 | None | 394.7 | None | 76626.8 | None | None | 0.0 |
| maze-32-32-4 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.2465909347620001 | -0.028050363543999923 | 524.7 | -46.0 | 386.9 | -7.800000000000011 | 67039.6 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 100 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.279410197178 | 0.004768898872000049 | 517.9 | -52.80000000000007 | 394.1 | -0.5999999999999659 | 61026.1 | 0.25 | 0.75 | 0.34737 |
| maze-32-32-4 | 100 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.277044530069 | 0.0024032317630000577 | 538.9 | -31.800000000000068 | 390.0 | -4.699999999999989 | 64830.1 | 0.25 | 0.75 | 0.35549 |
| maze-32-32-4 | 100 | repair5e3_split_guarded_selector | 10 | 1.000000 | 1.274641298306 | 0.0 | 570.7 | 0.0 | 387.2 | -7.5 | 76626.8 | 0.5714285714285714 | 0.0 | 0.36280999999999997 |
| maze-32-32-4 | 100 | repair5e3_split_guarded_selector_force_additive_parity | 10 | 1.000000 | 1.274641298306 | 0.0 | 570.7 | 0.0 | 389.0 | -5.699999999999989 | 76626.8 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.274641298306 | 0.0 | 570.7 | 0.0 | 394.1 | -0.5999999999999659 | 76626.8 | 0.5714285714285714 | 0.0 | 0.33246 |
| random-32-32-20 | 50 | always_additive_defer | 10 | 1.000000 | 1.136125751546 | 0.0 | 225.7 | 0.0 | 160.3 | -1.1999999999999886 | 11107.4 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | lacam_star | 10 | 1.000000 | 1.118625719692 | -0.017500031853999953 | 10011.1 | 9785.4 | 3127.33698 | 2965.83698 | None | None | None | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.136125751546 | None | 225.7 | None | 161.5 | None | 11107.4 | None | None | 0.0 |
| random-32-32-20 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.133315930043 | -0.0028098215029999096 | 222.9 | -2.799999999999983 | 159.2 | -2.3000000000000114 | 11153.7 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 50 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.134944649184 | -0.001181102361999864 | 221.1 | -4.599999999999994 | 159.9 | -1.5999999999999943 | 10894.5 | 0.25 | 0.75 | 0.34977 |
| random-32-32-20 | 50 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.136125751546 | 0.0 | 227.4 | 1.700000000000017 | 162.5 | 1.0 | 11466.5 | 0.25 | 0.75 | 0.34233 |
| random-32-32-20 | 50 | repair5e3_split_guarded_selector | 10 | 1.000000 | 1.136125751546 | 0.0 | 225.7 | 0.0 | 160.8 | -0.6999999999999886 | 11107.4 | 0.5714285714285714 | 0.0 | 0.36695 |
| random-32-32-20 | 50 | repair5e3_split_guarded_selector_force_additive_parity | 10 | 1.000000 | 1.136125751546 | 0.0 | 225.7 | 0.0 | 160.3 | -1.1999999999999886 | 11107.4 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.136125751546 | 0.0 | 225.7 | 0.0 | 161.3 | -0.19999999999998863 | 11107.4 | 0.5714285714285714 | 0.0 | 0.39009 |
| random-32-32-20 | 100 | always_additive_defer | 10 | 1.000000 | 1.26309792983 | 0.0 | 282.5 | 0.0 | 320.2 | -0.10000000000002274 | 36713.9 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | lacam_star | 10 | 1.000000 | 1.282298345536 | 0.01920041570599995 | 6284.8 | 6002.3 | 3092.49967 | 2772.19967 | None | None | None | 0.0 |
| random-32-32-20 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.26309792983 | None | 282.5 | None | 320.3 | None | 36713.9 | None | None | 0.0 |
| random-32-32-20 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.238276991717 | -0.024820938113000013 | 290.3 | 7.800000000000011 | 319.5 | -0.8000000000000114 | 39619.1 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 100 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.265167796623 | 0.0020698667929999193 | 309.5 | 27.0 | 319.9 | -0.4000000000000341 | 46537.8 | 0.25 | 0.75 | 0.33283 |
| random-32-32-20 | 100 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.270130312873 | 0.007032383042999912 | 286.0 | 3.5 | 322.4 | 2.099999999999966 | 38181.5 | 0.25 | 0.75 | 0.3335 |
| random-32-32-20 | 100 | repair5e3_split_guarded_selector | 10 | 1.000000 | 1.26309792983 | 0.0 | 282.5 | 0.0 | 322.3 | 2.0 | 36713.9 | 0.5714285714285714 | 0.0 | 0.37168 |
| random-32-32-20 | 100 | repair5e3_split_guarded_selector_force_additive_parity | 10 | 1.000000 | 1.26309792983 | 0.0 | 282.5 | 0.0 | 317.1 | -3.1999999999999886 | 36713.9 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.26309792983 | 0.0 | 282.5 | 0.0 | 321.0 | 0.6999999999999886 | 36713.9 | 0.5714285714285714 | 0.0 | 0.35375 |
| warehouse-10-20-10-2-1 | 50 | always_additive_defer | 10 | 1.000000 | 1.084755136352 | 0.0 | 393.6 | 0.0 | 1235.2 | -39.799999999999955 | 19527.8 | 0.3333333333333333 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star | 10 | 1.000000 | 1.0894851463620001 | 0.004730010010000063 | 7165.6 | 6772.0 | 3096.75261 | 1821.75261 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.084755136352 | None | 393.6 | None | 1275.0 | None | 19527.8 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.084755136352 | 0.0 | 358.3 | -35.30000000000001 | 1400.7 | 125.70000000000005 | 17772.9 | 0.35714285714285715 | 0.6428571428571429 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.084755136352 | 0.0 | 393.6 | 0.0 | 1256.0 | -19.0 | 19527.8 | 0.3333333333333333 | 0.6666666666666666 | 0.28307 |
| warehouse-10-20-10-2-1 | 50 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.084755136352 | 0.0 | 374.8 | -18.80000000000001 | 1418.7 | 143.70000000000005 | 18597.8 | 0.5135135135135135 | 0.0 | 0.25169 |
| warehouse-10-20-10-2-1 | 50 | repair5e3_split_guarded_selector | 10 | 1.000000 | 1.084755136352 | 0.0 | 374.9 | -18.700000000000045 | 1263.3 | -11.700000000000045 | 18597.8 | 0.6041666666666666 | 0.0 | 0.29673 |
| warehouse-10-20-10-2-1 | 50 | repair5e3_split_guarded_selector_force_additive_parity | 10 | 1.000000 | 1.084755136352 | 0.0 | 374.9 | -18.700000000000045 | 1316.4 | 41.40000000000009 | 18597.8 | 0.3448275862068966 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.084755136352 | 0.0 | 393.5 | -0.10000000000002274 | 1252.6 | -22.40000000000009 | 19527.8 | 0.6041666666666666 | 0.0 | 0.2712 |
| warehouse-10-20-10-2-1 | 100 | always_additive_defer | 10 | 1.000000 | 1.164186801731 | 0.0 | 207.1 | 0.0 | 2516.9 | 32.20000000000027 | 20514.3 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star | 10 | 1.000000 | 1.155208912119 | -0.008977889612000078 | 6617.6 | 6410.5 | 3096.50423 | 611.8042300000002 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.164186801731 | None | 207.1 | None | 2484.7 | None | 20514.3 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.164186801731 | 0.0 | 207.0 | -0.09999999999999432 | 2424.3 | -60.399999999999636 | 20514.3 | 0.5263157894736842 | 0.47368421052631576 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5d_composite_diagnostic_distilled | 10 | 1.000000 | 1.164186801731 | 0.0 | 207.1 | 0.0 | 2497.0 | 12.300000000000182 | 20514.3 | 0.5 | 0.5 | 0.16147 |
| warehouse-10-20-10-2-1 | 100 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.164186801731 | 0.0 | 207.1 | 0.0 | 2481.0 | -3.699999999999818 | 20514.3 | 0.6666666666666666 | 0.0 | 0.14579 |
| warehouse-10-20-10-2-1 | 100 | repair5e3_split_guarded_selector | 10 | 1.000000 | 1.164186801731 | 0.0 | 207.1 | 0.0 | 2428.3 | -56.399999999999636 | 20514.3 | 0.6666666666666666 | 0.0 | 0.16312000000000001 |
| warehouse-10-20-10-2-1 | 100 | repair5e3_split_guarded_selector_force_additive_parity | 10 | 1.000000 | 1.164186801731 | 0.0 | 207.1 | 0.0 | 2454.4 | -30.299999999999727 | 20514.3 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5e_caseb_ood_guard_distilled | 10 | 1.000000 | 1.164186801731 | 0.0 | 207.1 | 0.0 | 2484.8 | 0.1000000000003638 | 20514.3 | 0.6666666666666666 | 0.0 | 0.18537 |

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
      "ratio_worse_than_ltm_groups": 3,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair5e2_guarded_oracle_aligned_selector": {
      "ratio_worse_than_ltm_groups": 2,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 3
    },
    "repair5e3_split_guarded_selector": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "repair5e3_split_guarded_selector_force_additive_parity": {
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
  "case": "C",
  "oracle_positive": true,
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "recommended_action": "treat_e2_as_same_scope_oracle_support_overfit_train_better_selector_do_not_promote",
  "repair5e2_survives_heldout": false,
  "repair5e3_split_selector_positive": false
}

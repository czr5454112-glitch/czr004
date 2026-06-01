# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-06-01 15:40:11

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_oof_preflight\phase5p5_repair5e5_oof_preflight_commands.jsonl`

## Provenance

- git branch: `phase4f5p5-stable-attention-lau`
- git commit: `db0f494`
- git dirty state: `tracked-dirty_untracked-present`
- clean tracked worktree: `False`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agent_counts: `[50, 100]`
- instances_per_setting: `3`
- instance_ids: `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]`
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
| maze-32-32-4 | 50 | always_additive_defer | 25 | 1.000000 | 1.1572506260139601 | 0.0 | 426.76 | 0.0 | 187.08 | 0.12000000000000455 | 21168.48 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | lacam_star | 25 | 1.000000 | 1.16114188961292 | 0.00389126359895986 | 9277.2 | 8850.44 | 3137.085428 | 2950.125428 | None | None | None | 0.0 |
| maze-32-32-4 | 50 | lacam_star_ltm | 25 | 1.000000 | 1.1572506260139601 | None | 426.76 | None | 186.96 | None | 21168.48 | None | None | 0.0 |
| maze-32-32-4 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 25 | 1.000000 | 1.13936202657184 | -0.017888599442120068 | 417.48 | -9.279999999999973 | 186.76 | -0.20000000000001705 | 20701.36 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 50 | repair5d_composite_diagnostic_distilled | 25 | 1.000000 | 1.15741138282012 | 0.00016075680615990073 | 430.6 | 3.840000000000032 | 187.32 | 0.3599999999999852 | 21359.96 | 0.25 | 0.75 | 0.3497 |
| maze-32-32-4 | 50 | repair5e3_split_guarded_selector | 25 | 1.000000 | 1.1572506260139601 | 0.0 | 426.76 | 0.0 | 186.96 | 0.0 | 21168.48 | 0.5714285714285714 | 0.0 | 0.382424 |
| maze-32-32-4 | 50 | repair5e4_closed_loop_utility_selector | 25 | 1.000000 | 1.1572506260139601 | 0.0 | 426.76 | 0.0 | 188.04 | 1.079999999999984 | 21168.48 | 0.25 | 0.0 | 0.442288 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker | 25 | 1.000000 | 1.15064596589136 | -0.006604660122600192 | 416.48 | -10.279999999999973 | 187.56 | 0.5999999999999943 | 20679.84 | 0.25 | 0.75 | 0.421932 |
| maze-32-32-4 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 25 | 1.000000 | 1.1572506260139601 | 0.0 | 426.76 | 0.0 | 187.48 | 0.5199999999999818 | 21168.48 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | repair5e_caseb_ood_guard_distilled | 25 | 1.000000 | 1.1572506260139601 | 0.0 | 426.76 | 0.0 | 187.52 | 0.5600000000000023 | 21168.48 | 0.5714285714285714 | 0.0 | 0.371196 |
| maze-32-32-4 | 100 | always_additive_defer | 25 | 1.000000 | 1.2570212746644 | 0.0 | 553.44 | 0.0 | 392.36 | 2.6399999999999864 | 70351.92 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | lacam_star | 25 | 1.000000 | 1.3225424121752 | 0.06552113751080002 | 8698.0 | 8144.5599999999995 | 3139.074088 | 2749.354088 | None | None | None | 0.0 |
| maze-32-32-4 | 100 | lacam_star_ltm | 25 | 1.000000 | 1.2570212746644 | None | 553.44 | None | 389.72 | None | 70351.92 | None | None | 0.0 |
| maze-32-32-4 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 25 | 1.000000 | 1.2330484574752 | -0.02397281718919997 | 528.4 | -25.040000000000077 | 391.68 | 1.9599999999999795 | 65439.24 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 100 | repair5d_composite_diagnostic_distilled | 25 | 1.000000 | 1.2581503900016 | 0.0011291153371999485 | 529.6 | -23.840000000000032 | 392.0 | 2.2799999999999727 | 64277.84 | 0.25 | 0.75 | 0.361324 |
| maze-32-32-4 | 100 | repair5e3_split_guarded_selector | 25 | 1.000000 | 1.2570212746644 | 0.0 | 553.44 | 0.0 | 390.76 | 1.0399999999999636 | 70351.92 | 0.5714285714285714 | 0.0 | 0.39146 |
| maze-32-32-4 | 100 | repair5e4_closed_loop_utility_selector | 25 | 1.000000 | 1.2570212746644 | 0.0 | 553.44 | 0.0 | 391.92 | 2.1999999999999886 | 70351.92 | 0.25742574257425743 | 0.0 | 0.46206 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker | 25 | 1.000000 | 1.2570212746644 | 0.0 | 553.44 | 0.0 | 391.92 | 2.1999999999999886 | 70351.92 | 0.25742574257425743 | 0.0 | 0.454644 |
| maze-32-32-4 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 25 | 1.000000 | 1.2570212746644 | 0.0 | 553.44 | 0.0 | 390.64 | 0.9199999999999591 | 70351.92 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | repair5e_caseb_ood_guard_distilled | 25 | 1.000000 | 1.2570212746644 | 0.0 | 553.44 | 0.0 | 392.64 | 2.919999999999959 | 70351.92 | 0.5714285714285714 | 0.0 | 0.3595 |
| random-32-32-20 | 50 | always_additive_defer | 25 | 1.000000 | 1.1348619742908 | 0.0 | 231.4 | 0.0 | 160.4 | 0.4399999999999977 | 13248.56 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | lacam_star | 25 | 1.000000 | 1.1252639093796 | -0.009598064911199966 | 11074.32 | 10842.92 | 3151.42442 | 2991.46442 | None | None | None | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 25 | 1.000000 | 1.1348619742908 | None | 231.4 | None | 159.96 | None | 13248.56 | None | None | 0.0 |
| random-32-32-20 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 25 | 1.000000 | 1.1292043885908 | -0.005657585699999856 | 217.2 | -14.200000000000017 | 161.8 | 1.8400000000000034 | 11376.64 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 50 | repair5d_composite_diagnostic_distilled | 25 | 1.000000 | 1.1321245471828 | -0.002737427107999846 | 226.28 | -5.1200000000000045 | 159.56 | -0.4000000000000057 | 12689.28 | 0.25 | 0.75 | 0.346268 |
| random-32-32-20 | 50 | repair5e3_split_guarded_selector | 25 | 1.000000 | 1.1348619742908 | 0.0 | 231.4 | 0.0 | 160.16 | 0.19999999999998863 | 13248.56 | 0.5714285714285714 | 0.0 | 0.37704 |
| random-32-32-20 | 50 | repair5e4_closed_loop_utility_selector | 25 | 1.000000 | 1.1319190075656 | -0.0029429667251998914 | 226.72 | -4.680000000000007 | 159.88 | -0.0800000000000125 | 12814.64 | 0.25 | 0.75 | 0.41692 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker | 25 | 1.000000 | 1.1366927592256 | 0.001830784934800045 | 226.36 | -5.039999999999992 | 163.44 | 3.4799999999999898 | 12397.36 | 0.25 | 0.6 | 0.436544 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 25 | 1.000000 | 1.1348619742908 | 0.0 | 231.4 | 0.0 | 161.16 | 1.1999999999999886 | 13248.56 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | repair5e_caseb_ood_guard_distilled | 25 | 1.000000 | 1.1348619742908 | 0.0 | 231.4 | 0.0 | 160.28 | 0.3199999999999932 | 13248.56 | 0.5714285714285714 | 0.0 | 0.359856 |
| random-32-32-20 | 100 | always_additive_defer | 25 | 1.000000 | 1.24915647354116 | 0.0 | 268.28 | 0.0 | 323.04 | -0.9199999999999591 | 32749.08 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | lacam_star | 25 | 1.000000 | 1.25588526688156 | 0.006728793340400108 | 6121.36 | 5853.08 | 3086.292788 | 2762.332788 | None | None | None | 0.0 |
| random-32-32-20 | 100 | lacam_star_ltm | 25 | 1.000000 | 1.24915647354116 | None | 268.28 | None | 323.96 | None | 32749.08 | None | None | 0.0 |
| random-32-32-20 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 25 | 1.000000 | 1.22540530093912 | -0.02375117260204007 | 265.96 | -2.319999999999993 | 322.96 | -1.0 | 32706.08 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 100 | repair5d_composite_diagnostic_distilled | 25 | 1.000000 | 1.24410996332276 | -0.00504651021840008 | 278.32 | 10.04000000000002 | 322.72 | -1.2399999999999523 | 36167.6 | 0.25 | 0.75 | 0.354412 |
| random-32-32-20 | 100 | repair5e3_split_guarded_selector | 25 | 1.000000 | 1.24915647354116 | 0.0 | 268.28 | 0.0 | 323.64 | -0.3199999999999932 | 32749.08 | 0.5714285714285714 | 0.0 | 0.4038 |
| random-32-32-20 | 100 | repair5e4_closed_loop_utility_selector | 25 | 1.000000 | 1.24774080517076 | -0.0014156683704000805 | 268.88 | 0.6000000000000227 | 323.0 | -0.9599999999999795 | 33447.68 | 0.25 | 0.75 | 0.435116 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker | 25 | 1.000000 | 1.24597680869436 | -0.003179664846800101 | 276.92 | 8.640000000000043 | 323.88 | -0.07999999999998408 | 36205.32 | 0.25 | 0.6 | 0.426376 |
| random-32-32-20 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 25 | 1.000000 | 1.24915647354116 | 0.0 | 268.28 | 0.0 | 322.64 | -1.3199999999999932 | 32749.08 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | repair5e_caseb_ood_guard_distilled | 25 | 1.000000 | 1.24915647354116 | 0.0 | 268.28 | 0.0 | 323.8 | -0.15999999999996817 | 32749.08 | 0.5714285714285714 | 0.0 | 0.353388 |
| warehouse-10-20-10-2-1 | 50 | always_additive_defer | 25 | 1.000000 | 1.0837273199172 | 0.0 | 393.32 | 0.0 | 1253.0 | 0.2799999999999727 | 19513.04 | 0.3333333333333333 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star | 25 | 1.000000 | 1.0781806739208 | -0.005546645996399979 | 8582.36 | 8189.040000000001 | 3108.639816 | 1855.9198159999999 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 25 | 1.000000 | 1.0837273199172 | None | 393.32 | None | 1252.72 | None | 19513.04 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 25 | 1.000000 | 1.0837273199172 | 0.0 | 393.12 | -0.19999999999998863 | 1265.68 | 12.960000000000036 | 19513.04 | 0.35714285714285715 | 0.6428571428571429 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5d_composite_diagnostic_distilled | 25 | 1.000000 | 1.0837273199172 | 0.0 | 393.32 | 0.0 | 1263.84 | 11.11999999999989 | 19513.04 | 0.3333333333333333 | 0.6666666666666666 | 0.296868 |
| warehouse-10-20-10-2-1 | 50 | repair5e3_split_guarded_selector | 25 | 1.000000 | 1.0837273199172 | 0.0 | 393.28 | -0.040000000000020464 | 1277.88 | 25.160000000000082 | 19513.04 | 0.6016260162601627 | 0.0 | 0.316028 |
| warehouse-10-20-10-2-1 | 50 | repair5e4_closed_loop_utility_selector | 25 | 1.000000 | 1.0837273199172 | 0.0 | 393.28 | -0.040000000000020464 | 1279.84 | 27.11999999999989 | 19513.04 | 0.33783783783783783 | 0.0 | 0.396944 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker | 25 | 1.000000 | 1.0837273199172 | 0.0 | 393.28 | -0.040000000000020464 | 1277.56 | 24.839999999999918 | 19513.04 | 0.33783783783783783 | 0.0 | 0.357436 |
| warehouse-10-20-10-2-1 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 25 | 1.000000 | 1.0837273199172 | 0.0 | 393.24 | -0.07999999999998408 | 1278.16 | 25.440000000000055 | 19513.04 | 0.3424657534246575 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5e_caseb_ood_guard_distilled | 25 | 1.000000 | 1.0837273199172 | 0.0 | 393.28 | -0.040000000000020464 | 1270.44 | 17.720000000000027 | 19513.04 | 0.6016260162601627 | 0.0 | 0.291412 |
| warehouse-10-20-10-2-1 | 100 | always_additive_defer | 25 | 1.000000 | 1.16765915643 | 0.0 | 209.36 | -0.03999999999999204 | 2549.28 | 37.80000000000018 | 20737.36 | 0.5102040816326531 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star | 25 | 1.000000 | 1.155051650324 | -0.012607506106000033 | 6397.56 | 6188.160000000001 | 3083.109208 | 571.6292079999998 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 25 | 1.000000 | 1.16765915643 | None | 209.4 | None | 2511.48 | None | 20737.36 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 25 | 1.000000 | 1.16765915643 | 0.0 | 209.36 | -0.03999999999999204 | 2454.24 | -57.24000000000024 | 20737.36 | 0.5102040816326531 | 0.4897959183673469 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5d_composite_diagnostic_distilled | 25 | 1.000000 | 1.16765915643 | 0.0 | 209.4 | 0.0 | 2526.16 | 14.679999999999836 | 20737.36 | 0.5 | 0.5 | 0.17378 |
| warehouse-10-20-10-2-1 | 100 | repair5e3_split_guarded_selector | 25 | 1.000000 | 1.16765915643 | 0.0 | 209.4 | 0.0 | 2511.6 | 0.11999999999989086 | 20737.36 | 0.6666666666666666 | 0.0 | 0.179712 |
| warehouse-10-20-10-2-1 | 100 | repair5e4_closed_loop_utility_selector | 25 | 1.000000 | 1.16765915643 | 0.0 | 209.4 | 0.0 | 2515.88 | 4.400000000000091 | 20737.36 | 0.5 | 0.0 | 0.212532 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker | 25 | 1.000000 | 1.16765915643 | 0.0 | 209.36 | -0.03999999999999204 | 2538.4 | 26.920000000000073 | 20737.36 | 0.5102040816326531 | 0.0 | 0.212792 |
| warehouse-10-20-10-2-1 | 100 | repair5e5_crossfold_utility_reranker_force_additive_parity | 25 | 1.000000 | 1.16765915643 | 0.0 | 209.4 | 0.0 | 2518.8 | 7.320000000000164 | 20737.36 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5e_caseb_ood_guard_distilled | 25 | 1.000000 | 1.16765915643 | 0.0 | 209.4 | 0.0 | 2531.36 | 19.88000000000011 | 20737.36 | 0.6666666666666666 | 0.0 | 0.185192 |

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
      "ratio_worse_than_ltm_groups": 1,
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
  "paired_rows": 1350,
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

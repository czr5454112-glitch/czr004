# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-05-31 17:09:36

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e_caseb_preflight\phase5p5_repair5e_caseb_preflight.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e_caseb_preflight\phase5p5_repair5e_caseb_preflight_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e_caseb_preflight\phase5p5_repair5e_caseb_preflight_commands.jsonl`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agent_counts: `[50, 100]`
- instances_per_setting: `3`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`
- methods: `['lacam_star', 'lacam_star_ltm', 'always_additive_defer', 'repair3_safe_runtime', 'repair5d_composite_diagnostic_distilled', 'repair5d_force_additive_defer_parity', 'repair5e_caseb_ood_guard_distilled', 'repair5e_caseb_ood_guard_force_additive_parity', 'oracle_teacher_forced_best_safe_update_static_proxy']`
- support_methods: `['oracle_probe_static_block_heavy', 'oracle_probe_static_block_light', 'oracle_probe_static_commit_heavy', 'oracle_probe_static_decay_090', 'oracle_probe_static_decay_095', 'oracle_probe_static_wait_heavy', 'oracle_probe_static_wait_light']`

## Runtime Availability

- `repair5d_native_composite_export`: `not_feasible_current_cxx_runtime_accepts_single_mlp_runtime_only_distilled_bridge_used`
- `oracle_teacher_forced_best_safe_update_full_hook`: `full_per_update_teacher_force_hook_not_available_static_rule_probe_proxy_executed`
- `repair3_runtime_export`: `existing_runtime_dir`
- `repair5d_spec`: `available`
- `repair5d_runtime_distill`: `available`
- `repair5e_ood_guard_runtime`: `available`

## Group Summary

| map | agents | method | runs | success | ratio | d ratio | expanded | d expanded | TTFS ms | d TTFS | pibt | fallback | non-additive | overhead ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| maze-32-32-4 | 50 | always_additive_defer | 3 | 1.000000 | 1.1401441011333333 | 0.0 | 432.6666666666667 | 0.0 | 202.66666666666666 | 2.0 | 21433.333333333332 | 0.25 | 0.0 | 0.0012 |
| maze-32-32-4 | 50 | lacam_star | 3 | 1.000000 | 1.1470132688133334 | 0.006869167680000121 | 6698.333333333333 | 6265.666666666666 | 3091.3487333333333 | 2890.6820666666667 | None | None | None | 0.0 |
| maze-32-32-4 | 50 | lacam_star_ltm | 3 | 1.000000 | 1.1401441011333333 | None | 432.6666666666667 | None | 200.66666666666666 | None | 21433.333333333332 | None | None | 0.0 |
| maze-32-32-4 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.1328595356366666 | -0.007284565496666673 | 433.3333333333333 | 0.6666666666666288 | 200.66666666666666 | 0.0 | 21515.666666666668 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 50 | repair3_safe_runtime | 3 | 1.000000 | 1.15399561856 | 0.013851517426666682 | 442.0 | 9.333333333333314 | 207.33333333333334 | 6.666666666666686 | 21900.0 | 0.25 | 0.75 | 0.3388 |
| maze-32-32-4 | 50 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.1545778601899999 | 0.01443375905666655 | 440.3333333333333 | 7.666666666666629 | 202.66666666666666 | 2.0 | 21816.666666666668 | 0.25 | 0.75 | 0.3387 |
| maze-32-32-4 | 50 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.1401441011333333 | 0.0 | 432.6666666666667 | 0.0 | 199.66666666666666 | -1.0 | 21433.333333333332 | 0.25 | 0.0 | 0.0011666666666666665 |
| maze-32-32-4 | 50 | repair5e_caseb_ood_guard_distilled | 3 | 1.000000 | 1.1401441011333333 | 0.0 | 432.6666666666667 | 0.0 | 199.66666666666666 | -1.0 | 21433.333333333332 | 0.5714285714285714 | 0.0 | 0.20553333333333332 |
| maze-32-32-4 | 50 | repair5e_caseb_ood_guard_force_additive_parity | 3 | 1.000000 | 1.1401441011333333 | 0.0 | 432.6666666666667 | 0.0 | 200.33333333333334 | -0.3333333333333144 | 21433.333333333332 | 0.25 | 0.0 | 0.0012 |
| maze-32-32-4 | 100 | always_additive_defer | 3 | 1.000000 | 1.2851182965933334 | 0.0 | 482.3333333333333 | 0.0 | 415.6666666666667 | 3.6666666666666856 | 48214.666666666664 | 0.25 | 0.0 | 0.0011 |
| maze-32-32-4 | 100 | lacam_star | 3 | 1.000000 | 1.31428648418 | 0.029168187586666505 | 10923.0 | 10440.666666666666 | 3138.210633333333 | 2726.210633333333 | None | None | None | 0.0 |
| maze-32-32-4 | 100 | lacam_star_ltm | 3 | 1.000000 | 1.2851182965933334 | None | 482.3333333333333 | None | 412.0 | None | 48214.666666666664 | None | None | 0.0 |
| maze-32-32-4 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.26637622155 | -0.01874207504333336 | 465.3333333333333 | -17.0 | 407.0 | -5.0 | 46156.0 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 100 | repair3_safe_runtime | 3 | 1.000000 | 1.2689469156366666 | -0.016171380956666814 | 463.6666666666667 | -18.66666666666663 | 409.6666666666667 | -2.3333333333333144 | 46055.666666666664 | 0.25 | 0.75 | 0.31016666666666665 |
| maze-32-32-4 | 100 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.2848718756066666 | -0.00024642098666682877 | 466.3333333333333 | -16.0 | 416.0 | 4.0 | 46459.0 | 0.25 | 0.75 | 0.31833333333333336 |
| maze-32-32-4 | 100 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.2851182965933334 | 0.0 | 482.3333333333333 | 0.0 | 404.6666666666667 | -7.333333333333314 | 48214.666666666664 | 0.25 | 0.0 | 0.0014666666666666667 |
| maze-32-32-4 | 100 | repair5e_caseb_ood_guard_distilled | 3 | 1.000000 | 1.2851182965933334 | 0.0 | 482.3333333333333 | 0.0 | 408.6666666666667 | -3.3333333333333144 | 48214.666666666664 | 0.5714285714285714 | 0.0 | 0.22243333333333334 |
| maze-32-32-4 | 100 | repair5e_caseb_ood_guard_force_additive_parity | 3 | 1.000000 | 1.2851182965933334 | 0.0 | 482.3333333333333 | 0.0 | 415.3333333333333 | 3.3333333333333144 | 48214.666666666664 | 0.25 | 0.0 | 0.0013333333333333333 |
| random-32-32-20 | 50 | always_additive_defer | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 279.0 | 0.0 | 164.66666666666666 | 0.6666666666666572 | 22213.0 | 0.25 | 0.0 | 0.0013 |
| random-32-32-20 | 50 | lacam_star | 3 | 1.000000 | 1.1221591878866668 | 0.004319551673333422 | 17246.666666666668 | 16967.666666666668 | 3218.2562666666668 | 3054.2562666666668 | None | None | None | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 3 | 1.000000 | 1.1178396362133334 | None | 279.0 | None | 164.0 | None | 22213.0 | None | None | 0.0 |
| random-32-32-20 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 201.66666666666666 | -77.33333333333334 | 164.33333333333334 | 0.3333333333333428 | 9883.0 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 50 | repair3_safe_runtime | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 252.0 | -27.0 | 163.66666666666666 | -0.3333333333333428 | 17357.333333333332 | 0.25 | 0.75 | 0.3221333333333333 |
| random-32-32-20 | 50 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 252.0 | -27.0 | 164.66666666666666 | 0.6666666666666572 | 17357.333333333332 | 0.25 | 0.75 | 0.34236666666666665 |
| random-32-32-20 | 50 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 279.0 | 0.0 | 164.33333333333334 | 0.3333333333333428 | 22213.0 | 0.25 | 0.0 | 0.0012333333333333332 |
| random-32-32-20 | 50 | repair5e_caseb_ood_guard_distilled | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 279.0 | 0.0 | 164.66666666666666 | 0.6666666666666572 | 22213.0 | 0.5714285714285714 | 0.0 | 0.2529666666666667 |
| random-32-32-20 | 50 | repair5e_caseb_ood_guard_force_additive_parity | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 279.0 | 0.0 | 165.66666666666666 | 1.6666666666666572 | 22213.0 | 0.25 | 0.0 | 0.0014333333333333333 |
| random-32-32-20 | 100 | always_additive_defer | 3 | 1.000000 | 1.2777344629866667 | 0.0 | 223.66666666666666 | 0.0 | 339.6666666666667 | 2.0 | 22157.666666666668 | 0.25 | 0.0 | 0.0009 |
| random-32-32-20 | 100 | lacam_star | 3 | 1.000000 | 1.27971949887 | 0.0019850358833333193 | 7286.0 | 7062.333333333333 | 3092.5629 | 2754.8962333333334 | None | None | None | 0.0 |
| random-32-32-20 | 100 | lacam_star_ltm | 3 | 1.000000 | 1.2777344629866667 | None | 223.66666666666666 | None | 337.6666666666667 | None | 22157.666666666668 | None | None | 0.0 |
| random-32-32-20 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.2429697170766667 | -0.034764745910000006 | 271.3333333333333 | 47.66666666666666 | 347.6666666666667 | 10.0 | 36495.0 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 100 | repair3_safe_runtime | 3 | 1.000000 | 1.26817218132 | -0.009562281666666728 | 310.0 | 86.33333333333334 | 338.0 | 0.3333333333333144 | 47631.666666666664 | 0.25 | 0.75 | 0.3234 |
| random-32-32-20 | 100 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.2791087185966665 | 0.0013742556099998193 | 238.33333333333334 | 14.666666666666686 | 333.6666666666667 | -4.0 | 25228.0 | 0.25 | 0.75 | 0.3635 |
| random-32-32-20 | 100 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.2777344629866667 | 0.0 | 223.66666666666666 | 0.0 | 337.0 | -0.6666666666666856 | 22157.666666666668 | 0.25 | 0.0 | 0.0011666666666666665 |
| random-32-32-20 | 100 | repair5e_caseb_ood_guard_distilled | 3 | 1.000000 | 1.2777344629866667 | 0.0 | 223.66666666666666 | 0.0 | 337.3333333333333 | -0.33333333333337123 | 22157.666666666668 | 0.5714285714285714 | 0.0 | 0.2182 |
| random-32-32-20 | 100 | repair5e_caseb_ood_guard_force_additive_parity | 3 | 1.000000 | 1.2777344629866667 | 0.0 | 223.66666666666666 | 0.0 | 344.0 | 6.333333333333314 | 22157.666666666668 | 0.25 | 0.0 | 0.0011666666666666665 |
| warehouse-10-20-10-2-1 | 50 | always_additive_defer | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.0 | -0.3333333333333144 | 1453.3333333333333 | 1.666666666666515 | 20228.666666666668 | 0.42857142857142855 | 0.0 | 0.0008 |
| warehouse-10-20-10-2-1 | 50 | lacam_star | 3 | 1.000000 | 1.0596392266699999 | -0.01780021828666678 | 7440.333333333333 | 7033.0 | 3080.774933333333 | 1629.1082666666664 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 3 | 1.000000 | 1.0774394449566667 | None | 407.3333333333333 | None | 1451.6666666666667 | None | 20228.666666666668 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 393.6666666666667 | -13.666666666666629 | 1468.6666666666667 | 17.0 | 19578.666666666668 | 0.5 | 0.5 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair3_safe_runtime | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.0 | -0.3333333333333144 | 1422.6666666666667 | -29.0 | 20228.666666666668 | 0.42857142857142855 | 0.5714285714285714 | 0.17076666666666668 |
| warehouse-10-20-10-2-1 | 50 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.0 | -0.3333333333333144 | 1421.6666666666667 | -30.0 | 20228.666666666668 | 0.42857142857142855 | 0.5714285714285714 | 0.16693333333333332 |
| warehouse-10-20-10-2-1 | 50 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.0 | -0.3333333333333144 | 1438.0 | -13.666666666666742 | 20228.666666666668 | 0.42857142857142855 | 0.0 | 0.0007 |
| warehouse-10-20-10-2-1 | 50 | repair5e_caseb_ood_guard_distilled | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.6666666666667 | 0.33333333333337123 | 1433.6666666666667 | -18.0 | 20228.666666666668 | 0.6 | 0.0 | 0.1877 |
| warehouse-10-20-10-2-1 | 50 | repair5e_caseb_ood_guard_force_additive_parity | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 385.6666666666667 | -21.66666666666663 | 1497.0 | 45.33333333333326 | 19181.0 | 0.5 | 0.0 | 0.00046666666666666666 |
| warehouse-10-20-10-2-1 | 100 | always_additive_defer | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2864.0 | 73.0 | 19662.333333333332 | 0.5 | 0.0 | 0.00043333333333333337 |
| warehouse-10-20-10-2-1 | 100 | lacam_star | 3 | 1.000000 | 1.1424659003833333 | 0.002748407043333234 | 3775.6666666666665 | 3577.0 | 3048.5196666666666 | 257.5196666666666 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 3 | 1.000000 | 1.13971749334 | None | 198.66666666666666 | None | 2791.0 | None | 19662.333333333332 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2789.6666666666665 | -1.333333333333485 | 19662.333333333332 | 0.5 | 0.5 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair3_safe_runtime | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2854.6666666666665 | 63.666666666666515 | 19662.333333333332 | 0.5 | 0.5 | 0.3819666666666667 |
| warehouse-10-20-10-2-1 | 100 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2882.3333333333335 | 91.33333333333348 | 19662.333333333332 | 0.5 | 0.5 | 0.128 |
| warehouse-10-20-10-2-1 | 100 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2837.3333333333335 | 46.333333333333485 | 19662.333333333332 | 0.5 | 0.0 | 0.0005666666666666667 |
| warehouse-10-20-10-2-1 | 100 | repair5e_caseb_ood_guard_distilled | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2850.0 | 59.0 | 19662.333333333332 | 0.6666666666666666 | 0.0 | 0.0765 |
| warehouse-10-20-10-2-1 | 100 | repair5e_caseb_ood_guard_force_additive_parity | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2872.3333333333335 | 81.33333333333348 | 19662.333333333332 | 0.5 | 0.0 | 0.00036666666666666667 |

## Stop Condition Snapshot

{
  "method_flags": {
    "always_additive_defer": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "lacam_star": {
      "ratio_worse_than_ltm_groups": 5,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "oracle_teacher_forced_best_safe_update_static_proxy": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair3_safe_runtime": {
      "ratio_worse_than_ltm_groups": 1,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair5d_composite_diagnostic_distilled": {
      "ratio_worse_than_ltm_groups": 2,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair5d_force_additive_defer_parity": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "repair5e_caseb_ood_guard_distilled": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "repair5e_caseb_ood_guard_force_additive_parity": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    }
  },
  "oracle_replay_executed": true,
  "oracle_replay_scope": "static_rule_proxy",
  "paired_rows": 144,
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

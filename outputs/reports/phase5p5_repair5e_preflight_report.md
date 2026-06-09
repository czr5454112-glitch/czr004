# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-05-31 14:37:26

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e_preflight\phase5p5_repair5e_preflight.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e_preflight\phase5p5_repair5e_preflight_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e_preflight\phase5p5_repair5e_preflight_commands.jsonl`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agent_counts: `[50, 100]`
- instances_per_setting: `3`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`
- methods: `['lacam_star', 'lacam_star_ltm', 'always_additive_defer', 'repair3_safe_runtime', 'repair5d_composite_diagnostic_distilled', 'repair5d_force_additive_defer_parity', 'oracle_teacher_forced_best_safe_update_static_proxy']`
- support_methods: `['oracle_probe_static_block_heavy', 'oracle_probe_static_block_light', 'oracle_probe_static_commit_heavy', 'oracle_probe_static_decay_090', 'oracle_probe_static_decay_095', 'oracle_probe_static_wait_heavy', 'oracle_probe_static_wait_light']`

## Runtime Availability

- `repair5d_native_composite_export`: `not_feasible_current_cxx_runtime_accepts_single_mlp_runtime_only_distilled_bridge_used`
- `oracle_teacher_forced_best_safe_update_full_hook`: `full_per_update_teacher_force_hook_not_available_static_rule_probe_proxy_executed`
- `repair3_runtime_export`: `existing_runtime_dir`
- `repair5d_spec`: `available`
- `repair5d_runtime_distill`: `available`

## Group Summary

| map | agents | method | runs | success | ratio | d ratio | expanded | d expanded | TTFS ms | d TTFS | pibt | fallback | non-additive | overhead ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| maze-32-32-4 | 50 | always_additive_defer | 3 | 1.000000 | 1.1401441011333333 | 0.0 | 432.6666666666667 | 0.0 | 191.33333333333334 | -2.666666666666657 | 21433.333333333332 | 0.25 | 0.0 | 0.0013666666666666666 |
| maze-32-32-4 | 50 | lacam_star | 3 | 1.000000 | 1.1470132688133334 | 0.006869167680000121 | 6760.666666666667 | 6328.0 | 3096.3766 | 2902.3766 | None | None | None | 0.0 |
| maze-32-32-4 | 50 | lacam_star_ltm | 3 | 1.000000 | 1.1401441011333333 | None | 432.6666666666667 | None | 194.0 | None | 21433.333333333332 | None | None | 0.0 |
| maze-32-32-4 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.1328595356366666 | -0.007284565496666673 | 433.3333333333333 | 0.6666666666666288 | 192.33333333333334 | -1.6666666666666572 | 21515.666666666668 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 50 | repair3_safe_runtime | 3 | 1.000000 | 1.15399561856 | 0.013851517426666682 | 442.0 | 9.333333333333314 | 191.0 | -3.0 | 21900.0 | 0.25 | 0.75 | 0.30596666666666666 |
| maze-32-32-4 | 50 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.1545778601899999 | 0.01443375905666655 | 440.3333333333333 | 7.666666666666629 | 189.33333333333334 | -4.666666666666657 | 21816.666666666668 | 0.25 | 0.75 | 0.3052666666666667 |
| maze-32-32-4 | 50 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.1401441011333333 | 0.0 | 432.6666666666667 | 0.0 | 190.66666666666666 | -3.333333333333343 | 21433.333333333332 | 0.25 | 0.0 | 0.0013666666666666666 |
| maze-32-32-4 | 100 | always_additive_defer | 3 | 1.000000 | 1.2851182965933334 | 0.0 | 482.3333333333333 | 0.0 | 393.3333333333333 | -0.6666666666666856 | 48214.666666666664 | 0.25 | 0.0 | 0.0013 |
| maze-32-32-4 | 100 | lacam_star | 3 | 1.000000 | 1.31428648418 | 0.029168187586666505 | 11325.666666666666 | 10843.333333333332 | 3149.351133333333 | 2755.351133333333 | None | None | None | 0.0 |
| maze-32-32-4 | 100 | lacam_star_ltm | 3 | 1.000000 | 1.2851182965933334 | None | 482.3333333333333 | None | 394.0 | None | 48214.666666666664 | None | None | 0.0 |
| maze-32-32-4 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.26637622155 | -0.01874207504333336 | 465.3333333333333 | -17.0 | 397.0 | 3.0 | 46156.0 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 100 | repair3_safe_runtime | 3 | 1.000000 | 1.2689469156366666 | -0.016171380956666814 | 463.6666666666667 | -18.66666666666663 | 397.6666666666667 | 3.6666666666666856 | 46055.666666666664 | 0.25 | 0.75 | 0.30593333333333333 |
| maze-32-32-4 | 100 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.2848718756066666 | -0.00024642098666682877 | 466.3333333333333 | -16.0 | 392.0 | -2.0 | 46459.0 | 0.25 | 0.75 | 0.29673333333333335 |
| maze-32-32-4 | 100 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.2851182965933334 | 0.0 | 482.3333333333333 | 0.0 | 390.3333333333333 | -3.6666666666666856 | 48214.666666666664 | 0.25 | 0.0 | 0.0013 |
| random-32-32-20 | 50 | always_additive_defer | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 279.0 | 0.0 | 161.33333333333334 | 3.6666666666666856 | 22213.0 | 0.25 | 0.0 | 0.0016333333333333334 |
| random-32-32-20 | 50 | lacam_star | 3 | 1.000000 | 1.1221591878866668 | 0.004319551673333422 | 17504.666666666668 | 17225.666666666668 | 3241.4994666666666 | 3083.8328 | None | None | None | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 3 | 1.000000 | 1.1178396362133334 | None | 279.0 | None | 157.66666666666666 | None | 22213.0 | None | None | 0.0 |
| random-32-32-20 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 201.66666666666666 | -77.33333333333334 | 157.66666666666666 | 0.0 | 9882.0 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 50 | repair3_safe_runtime | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 252.0 | -27.0 | 158.0 | 0.3333333333333428 | 17357.333333333332 | 0.25 | 0.75 | 0.30546666666666666 |
| random-32-32-20 | 50 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 252.0 | -27.0 | 159.66666666666666 | 2.0 | 17357.333333333332 | 0.25 | 0.75 | 0.3181333333333333 |
| random-32-32-20 | 50 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 279.0 | 0.0 | 158.0 | 0.3333333333333428 | 22213.0 | 0.25 | 0.0 | 0.0014333333333333333 |
| random-32-32-20 | 100 | always_additive_defer | 3 | 1.000000 | 1.2777344629866667 | 0.0 | 223.66666666666666 | 0.0 | 319.6666666666667 | 0.33333333333337123 | 22157.666666666668 | 0.25 | 0.0 | 0.0015999999999999999 |
| random-32-32-20 | 100 | lacam_star | 3 | 1.000000 | 1.27971949887 | 0.0019850358833333193 | 7668.666666666667 | 7445.0 | 3113.005 | 2793.6716666666666 | None | None | None | 0.0 |
| random-32-32-20 | 100 | lacam_star_ltm | 3 | 1.000000 | 1.2777344629866667 | None | 223.66666666666666 | None | 319.3333333333333 | None | 22157.666666666668 | None | None | 0.0 |
| random-32-32-20 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.2429697170766667 | -0.034764745910000006 | 271.3333333333333 | 47.66666666666666 | 322.6666666666667 | 3.3333333333333712 | 36495.0 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 100 | repair3_safe_runtime | 3 | 1.000000 | 1.26817218132 | -0.009562281666666728 | 310.0 | 86.33333333333334 | 316.0 | -3.3333333333333144 | 47631.666666666664 | 0.25 | 0.75 | 0.3127 |
| random-32-32-20 | 100 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.2791087185966665 | 0.0013742556099998193 | 238.33333333333334 | 14.666666666666686 | 319.3333333333333 | 0.0 | 25228.0 | 0.25 | 0.75 | 0.3154 |
| random-32-32-20 | 100 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.2777344629866667 | 0.0 | 223.66666666666666 | 0.0 | 315.3333333333333 | -4.0 | 22157.666666666668 | 0.25 | 0.0 | 0.0013 |
| warehouse-10-20-10-2-1 | 50 | always_additive_defer | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.6666666666667 | 0.0 | 1295.3333333333333 | 7.666666666666515 | 20228.666666666668 | 0.3333333333333333 | 0.0 | 0.0011666666666666668 |
| warehouse-10-20-10-2-1 | 50 | lacam_star | 3 | 1.000000 | 1.0596392266699999 | -0.01780021828666678 | 7427.0 | 7019.333333333333 | 3091.108566666667 | 1803.4419 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 3 | 1.000000 | 1.0774394449566667 | None | 407.6666666666667 | None | 1287.6666666666667 | None | 20228.666666666668 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.6666666666667 | 0.0 | 1273.0 | -14.666666666666742 | 20228.666666666668 | 0.3333333333333333 | 0.6666666666666666 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair3_safe_runtime | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.6666666666667 | 0.0 | 1294.3333333333333 | 6.666666666666515 | 20228.666666666668 | 0.3333333333333333 | 0.6666666666666666 | 0.2544666666666667 |
| warehouse-10-20-10-2-1 | 50 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.6666666666667 | 0.0 | 1290.6666666666667 | 3.0 | 20228.666666666668 | 0.3333333333333333 | 0.6666666666666666 | 0.25273333333333337 |
| warehouse-10-20-10-2-1 | 50 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.6666666666667 | 0.0 | 1307.3333333333333 | 19.666666666666515 | 20228.666666666668 | 0.3333333333333333 | 0.0 | 0.0012666666666666666 |
| warehouse-10-20-10-2-1 | 100 | always_additive_defer | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2559.0 | 21.333333333333485 | 19662.333333333332 | 0.5 | 0.0 | 0.0005666666666666667 |
| warehouse-10-20-10-2-1 | 100 | lacam_star | 3 | 1.000000 | 1.1424659003833333 | 0.002748407043333234 | 3827.3333333333335 | 3628.666666666667 | 3050.6655 | 512.9988333333336 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 3 | 1.000000 | 1.13971749334 | None | 198.66666666666666 | None | 2537.6666666666665 | None | 19662.333333333332 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2484.3333333333335 | -53.33333333333303 | 19662.333333333332 | 0.5 | 0.5 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair3_safe_runtime | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2543.6666666666665 | 6.0 | 19662.333333333332 | 0.5 | 0.5 | 0.14426666666666665 |
| warehouse-10-20-10-2-1 | 100 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2553.0 | 15.333333333333485 | 19662.333333333332 | 0.5 | 0.5 | 0.12393333333333334 |
| warehouse-10-20-10-2-1 | 100 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2539.6666666666665 | 2.0 | 19662.333333333332 | 0.5 | 0.0 | 0.0004 |

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
    }
  },
  "oracle_replay_executed": true,
  "oracle_replay_scope": "static_rule_proxy",
  "paired_rows": 108,
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

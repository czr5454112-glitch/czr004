# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-05-31 18:32:02

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e2_preflight\phase5p5_repair5e2_preflight.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e2_preflight\phase5p5_repair5e2_preflight_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e2_preflight\phase5p5_repair5e2_preflight_commands.jsonl`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agent_counts: `[50, 100]`
- instances_per_setting: `3`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`
- methods: `['lacam_star', 'lacam_star_ltm', 'always_additive_defer', 'repair3_safe_runtime', 'repair5d_composite_diagnostic_distilled', 'repair5d_force_additive_defer_parity', 'repair5e_caseb_ood_guard_distilled', 'repair5e_caseb_ood_guard_force_additive_parity', 'repair5e2_guarded_oracle_aligned_selector', 'repair5e2_guarded_oracle_aligned_selector_force_additive_parity', 'oracle_teacher_forced_best_safe_update_static_proxy']`
- support_methods: `['oracle_probe_static_block_heavy', 'oracle_probe_static_block_light', 'oracle_probe_static_commit_heavy', 'oracle_probe_static_decay_090', 'oracle_probe_static_decay_095', 'oracle_probe_static_wait_heavy', 'oracle_probe_static_wait_light']`

## Runtime Availability

- `repair5d_native_composite_export`: `not_feasible_current_cxx_runtime_accepts_single_mlp_runtime_only_distilled_bridge_used`
- `oracle_teacher_forced_best_safe_update_full_hook`: `full_per_update_teacher_force_hook_not_available_static_rule_probe_proxy_executed`
- `repair3_runtime_export`: `existing_runtime_dir`
- `repair5d_spec`: `available`
- `repair5d_runtime_distill`: `available`
- `repair5e_ood_guard_runtime`: `available`
- `repair5e2_guarded_oracle_aligned_selector_runtime`: `available`

## Group Summary

| map | agents | method | runs | success | ratio | d ratio | expanded | d expanded | TTFS ms | d TTFS | pibt | fallback | non-additive | overhead ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| maze-32-32-4 | 50 | always_additive_defer | 3 | 1.000000 | 1.1401441011333333 | 0.0 | 432.6666666666667 | 0.0 | 190.0 | 0.0 | 21433.333333333332 | 0.25 | 0.0 | 0.0014666666666666667 |
| maze-32-32-4 | 50 | lacam_star | 3 | 1.000000 | 1.1470132688133334 | 0.006869167680000121 | 6778.333333333333 | 6345.666666666666 | 3106.4385666666667 | 2916.4385666666667 | None | None | None | 0.0 |
| maze-32-32-4 | 50 | lacam_star_ltm | 3 | 1.000000 | 1.1401441011333333 | None | 432.6666666666667 | None | 190.0 | None | 21433.333333333332 | None | None | 0.0 |
| maze-32-32-4 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.1328595356366666 | -0.007284565496666673 | 433.3333333333333 | 0.6666666666666288 | 193.0 | 3.0 | 21515.666666666668 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 50 | repair3_safe_runtime | 3 | 1.000000 | 1.15399561856 | 0.013851517426666682 | 442.0 | 9.333333333333314 | 192.66666666666666 | 2.666666666666657 | 21900.0 | 0.25 | 0.75 | 0.3461 |
| maze-32-32-4 | 50 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.1545778601899999 | 0.01443375905666655 | 440.3333333333333 | 7.666666666666629 | 190.66666666666666 | 0.6666666666666572 | 21816.666666666668 | 0.25 | 0.75 | 0.3358 |
| maze-32-32-4 | 50 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.1401441011333333 | 0.0 | 432.6666666666667 | 0.0 | 194.33333333333334 | 4.333333333333343 | 21433.333333333332 | 0.25 | 0.0 | 0.0013333333333333333 |
| maze-32-32-4 | 50 | repair5e2_guarded_oracle_aligned_selector | 3 | 1.000000 | 1.1401441011333333 | 0.0 | 432.6666666666667 | 0.0 | 189.66666666666666 | -0.3333333333333428 | 21433.333333333332 | 0.25 | 0.0 | 0.37506666666666666 |
| maze-32-32-4 | 50 | repair5e2_guarded_oracle_aligned_selector_force_additive_parity | 3 | 1.000000 | 1.1401441011333333 | 0.0 | 432.6666666666667 | 0.0 | 191.0 | 1.0 | 21433.333333333332 | 0.25 | 0.0 | 0.0013666666666666666 |
| maze-32-32-4 | 50 | repair5e_caseb_ood_guard_distilled | 3 | 1.000000 | 1.1401441011333333 | 0.0 | 432.6666666666667 | 0.0 | 190.66666666666666 | 0.6666666666666572 | 21433.333333333332 | 0.5714285714285714 | 0.0 | 0.35256666666666664 |
| maze-32-32-4 | 50 | repair5e_caseb_ood_guard_force_additive_parity | 3 | 1.000000 | 1.1401441011333333 | 0.0 | 432.6666666666667 | 0.0 | 194.33333333333334 | 4.333333333333343 | 21433.333333333332 | 0.25 | 0.0 | 0.0017000000000000001 |
| maze-32-32-4 | 100 | always_additive_defer | 3 | 1.000000 | 1.2851182965933334 | 0.0 | 482.3333333333333 | 0.0 | 398.3333333333333 | 0.6666666666666288 | 48214.666666666664 | 0.25 | 0.0 | 0.0017666666666666666 |
| maze-32-32-4 | 100 | lacam_star | 3 | 1.000000 | 1.31428648418 | 0.029168187586666505 | 10873.666666666666 | 10391.333333333332 | 3169.099366666667 | 2771.4327000000003 | None | None | None | 0.0 |
| maze-32-32-4 | 100 | lacam_star_ltm | 3 | 1.000000 | 1.2851182965933334 | None | 482.3333333333333 | None | 397.6666666666667 | None | 48214.666666666664 | None | None | 0.0 |
| maze-32-32-4 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.26637622155 | -0.01874207504333336 | 465.3333333333333 | -17.0 | 399.0 | 1.3333333333333144 | 46156.0 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 100 | repair3_safe_runtime | 3 | 1.000000 | 1.2689469156366666 | -0.016171380956666814 | 463.6666666666667 | -18.66666666666663 | 401.0 | 3.3333333333333144 | 46055.666666666664 | 0.25 | 0.75 | 0.34296666666666664 |
| maze-32-32-4 | 100 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.2848718756066666 | -0.00024642098666682877 | 466.3333333333333 | -16.0 | 389.6666666666667 | -8.0 | 46459.0 | 0.25 | 0.75 | 0.3369 |
| maze-32-32-4 | 100 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.2851182965933334 | 0.0 | 482.3333333333333 | 0.0 | 398.0 | 0.3333333333333144 | 48214.666666666664 | 0.25 | 0.0 | 0.0012666666666666666 |
| maze-32-32-4 | 100 | repair5e2_guarded_oracle_aligned_selector | 3 | 1.000000 | 1.2689469156366666 | -0.016171380956666814 | 463.6666666666667 | -18.66666666666663 | 394.3333333333333 | -3.3333333333333712 | 46055.666666666664 | 0.25 | 0.75 | 0.34313333333333335 |
| maze-32-32-4 | 100 | repair5e2_guarded_oracle_aligned_selector_force_additive_parity | 3 | 1.000000 | 1.2851182965933334 | 0.0 | 482.3333333333333 | 0.0 | 396.3333333333333 | -1.3333333333333712 | 48214.666666666664 | 0.25 | 0.0 | 0.0013333333333333333 |
| maze-32-32-4 | 100 | repair5e_caseb_ood_guard_distilled | 3 | 1.000000 | 1.2851182965933334 | 0.0 | 482.3333333333333 | 0.0 | 393.6666666666667 | -4.0 | 48214.666666666664 | 0.5714285714285714 | 0.0 | 0.3461 |
| maze-32-32-4 | 100 | repair5e_caseb_ood_guard_force_additive_parity | 3 | 1.000000 | 1.2851182965933334 | 0.0 | 482.3333333333333 | 0.0 | 393.3333333333333 | -4.333333333333371 | 48214.666666666664 | 0.25 | 0.0 | 0.0012333333333333332 |
| random-32-32-20 | 50 | always_additive_defer | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 279.0 | 0.0 | 161.33333333333334 | -1.0 | 22213.0 | 0.25 | 0.0 | 0.0012666666666666666 |
| random-32-32-20 | 50 | lacam_star | 3 | 1.000000 | 1.1221591878866668 | 0.004319551673333422 | 16946.666666666668 | 16667.666666666668 | 3260.3975 | 3098.0641666666666 | None | None | None | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 3 | 1.000000 | 1.1178396362133334 | None | 279.0 | None | 162.33333333333334 | None | 22213.0 | None | None | 0.0 |
| random-32-32-20 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 201.66666666666666 | -77.33333333333334 | 161.0 | -1.3333333333333428 | 9882.0 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 50 | repair3_safe_runtime | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 252.0 | -27.0 | 162.33333333333334 | 0.0 | 17357.333333333332 | 0.25 | 0.75 | 0.35346666666666665 |
| random-32-32-20 | 50 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 252.0 | -27.0 | 161.66666666666666 | -0.6666666666666856 | 17357.333333333332 | 0.25 | 0.75 | 0.35656666666666664 |
| random-32-32-20 | 50 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 279.0 | 0.0 | 159.0 | -3.333333333333343 | 22213.0 | 0.25 | 0.0 | 0.0014 |
| random-32-32-20 | 50 | repair5e2_guarded_oracle_aligned_selector | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 272.0 | -7.0 | 158.66666666666666 | -3.6666666666666856 | 22249.666666666668 | 0.25 | 0.75 | 0.3448 |
| random-32-32-20 | 50 | repair5e2_guarded_oracle_aligned_selector_force_additive_parity | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 279.0 | 0.0 | 157.66666666666666 | -4.666666666666686 | 22213.0 | 0.25 | 0.0 | 0.0014666666666666667 |
| random-32-32-20 | 50 | repair5e_caseb_ood_guard_distilled | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 279.0 | 0.0 | 163.66666666666666 | 1.3333333333333144 | 22213.0 | 0.5714285714285714 | 0.0 | 0.33623333333333333 |
| random-32-32-20 | 50 | repair5e_caseb_ood_guard_force_additive_parity | 3 | 1.000000 | 1.1178396362133334 | 0.0 | 279.0 | 0.0 | 160.33333333333334 | -2.0 | 22213.0 | 0.25 | 0.0 | 0.0017666666666666666 |
| random-32-32-20 | 100 | always_additive_defer | 3 | 1.000000 | 1.2777344629866667 | 0.0 | 223.66666666666666 | 0.0 | 323.0 | -2.6666666666666856 | 22157.666666666668 | 0.25 | 0.0 | 0.0015 |
| random-32-32-20 | 100 | lacam_star | 3 | 1.000000 | 1.27971949887 | 0.0019850358833333193 | 7183.0 | 6959.333333333333 | 3128.7437666666665 | 2803.0771 | None | None | None | 0.0 |
| random-32-32-20 | 100 | lacam_star_ltm | 3 | 1.000000 | 1.2777344629866667 | None | 223.66666666666666 | None | 325.6666666666667 | None | 22157.666666666668 | None | None | 0.0 |
| random-32-32-20 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.2429697170766667 | -0.034764745910000006 | 271.3333333333333 | 47.66666666666666 | 323.0 | -2.6666666666666856 | 36495.0 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 100 | repair3_safe_runtime | 3 | 1.000000 | 1.26817218132 | -0.009562281666666728 | 310.0 | 86.33333333333334 | 326.3333333333333 | 0.6666666666666288 | 47631.666666666664 | 0.25 | 0.75 | 0.35303333333333337 |
| random-32-32-20 | 100 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.2791087185966665 | 0.0013742556099998193 | 238.33333333333334 | 14.666666666666686 | 327.0 | 1.3333333333333144 | 25228.0 | 0.25 | 0.75 | 0.3546 |
| random-32-32-20 | 100 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.2777344629866667 | 0.0 | 223.66666666666666 | 0.0 | 323.6666666666667 | -2.0 | 22157.666666666668 | 0.25 | 0.0 | 0.0014333333333333333 |
| random-32-32-20 | 100 | repair5e2_guarded_oracle_aligned_selector | 3 | 1.000000 | 1.2593339236166667 | -0.01840053936999997 | 237.33333333333334 | 13.666666666666686 | 321.0 | -4.666666666666686 | 27849.0 | 0.25 | 0.75 | 0.35313333333333335 |
| random-32-32-20 | 100 | repair5e2_guarded_oracle_aligned_selector_force_additive_parity | 3 | 1.000000 | 1.2777344629866667 | 0.0 | 223.66666666666666 | 0.0 | 330.0 | 4.333333333333314 | 22157.666666666668 | 0.25 | 0.0 | 0.0014 |
| random-32-32-20 | 100 | repair5e_caseb_ood_guard_distilled | 3 | 1.000000 | 1.2777344629866667 | 0.0 | 223.66666666666666 | 0.0 | 324.6666666666667 | -1.0 | 22157.666666666668 | 0.5714285714285714 | 0.0 | 0.36186666666666667 |
| random-32-32-20 | 100 | repair5e_caseb_ood_guard_force_additive_parity | 3 | 1.000000 | 1.2777344629866667 | 0.0 | 223.66666666666666 | 0.0 | 329.3333333333333 | 3.6666666666666288 | 22157.666666666668 | 0.25 | 0.0 | 0.0013333333333333333 |
| warehouse-10-20-10-2-1 | 50 | always_additive_defer | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.6666666666667 | 0.0 | 1315.3333333333333 | -7.6666666666667425 | 20228.666666666668 | 0.3333333333333333 | 0.0 | 0.0012333333333333332 |
| warehouse-10-20-10-2-1 | 50 | lacam_star | 3 | 1.000000 | 1.0596392266699999 | -0.01780021828666678 | 7536.666666666667 | 7129.0 | 3091.7153000000003 | 1768.7153000000003 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 3 | 1.000000 | 1.0774394449566667 | None | 407.6666666666667 | None | 1323.0 | None | 20228.666666666668 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.3333333333333 | -0.33333333333337123 | 1309.0 | -14.0 | 20228.666666666668 | 0.375 | 0.625 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair3_safe_runtime | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.6666666666667 | 0.0 | 1302.3333333333333 | -20.666666666666742 | 20228.666666666668 | 0.3333333333333333 | 0.6666666666666666 | 0.28883333333333333 |
| warehouse-10-20-10-2-1 | 50 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.6666666666667 | 0.0 | 1308.6666666666667 | -14.333333333333258 | 20228.666666666668 | 0.3333333333333333 | 0.6666666666666666 | 0.26239999999999997 |
| warehouse-10-20-10-2-1 | 50 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.6666666666667 | 0.0 | 1326.3333333333333 | 3.3333333333332575 | 20228.666666666668 | 0.3333333333333333 | 0.0 | 0.0013666666666666666 |
| warehouse-10-20-10-2-1 | 50 | repair5e2_guarded_oracle_aligned_selector | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.6666666666667 | 0.0 | 1322.6666666666667 | -0.33333333333325754 | 20228.666666666668 | 0.5714285714285714 | 0.0 | 0.2797 |
| warehouse-10-20-10-2-1 | 50 | repair5e2_guarded_oracle_aligned_selector_force_additive_parity | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.6666666666667 | 0.0 | 1321.6666666666667 | -1.3333333333332575 | 20228.666666666668 | 0.3333333333333333 | 0.0 | 0.0011666666666666665 |
| warehouse-10-20-10-2-1 | 50 | repair5e_caseb_ood_guard_distilled | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.6666666666667 | 0.0 | 1290.3333333333333 | -32.66666666666674 | 20228.666666666668 | 0.6 | 0.0 | 0.3107666666666667 |
| warehouse-10-20-10-2-1 | 50 | repair5e_caseb_ood_guard_force_additive_parity | 3 | 1.000000 | 1.0774394449566667 | 0.0 | 407.6666666666667 | 0.0 | 1292.0 | -31.0 | 20228.666666666668 | 0.3333333333333333 | 0.0 | 0.0011666666666666665 |
| warehouse-10-20-10-2-1 | 100 | always_additive_defer | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.33333333333334 | -0.3333333333333144 | 2757.3333333333335 | 87.66666666666697 | 19662.333333333332 | 0.6 | 0.0 | 0.0006333333333333334 |
| warehouse-10-20-10-2-1 | 100 | lacam_star | 3 | 1.000000 | 1.1424659003833333 | 0.002748407043333234 | 3787.0 | 3588.3333333333335 | 3049.3961 | 379.7294333333334 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 3 | 1.000000 | 1.13971749334 | None | 198.66666666666666 | None | 2669.6666666666665 | None | 19662.333333333332 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2547.6666666666665 | -122.0 | 19662.333333333332 | 0.5 | 0.5 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair3_safe_runtime | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2579.6666666666665 | -90.0 | 19662.333333333332 | 0.5 | 0.5 | 0.20913333333333334 |
| warehouse-10-20-10-2-1 | 100 | repair5d_composite_diagnostic_distilled | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2627.6666666666665 | -42.0 | 19662.333333333332 | 0.5 | 0.5 | 0.17943333333333333 |
| warehouse-10-20-10-2-1 | 100 | repair5d_force_additive_defer_parity | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2663.6666666666665 | -6.0 | 19662.333333333332 | 0.5 | 0.0 | 0.0007333333333333333 |
| warehouse-10-20-10-2-1 | 100 | repair5e2_guarded_oracle_aligned_selector | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2584.0 | -85.66666666666652 | 19662.333333333332 | 0.6666666666666666 | 0.0 | 0.19113333333333332 |
| warehouse-10-20-10-2-1 | 100 | repair5e2_guarded_oracle_aligned_selector_force_additive_parity | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2584.0 | -85.66666666666652 | 19662.333333333332 | 0.5 | 0.0 | 0.0006666666666666666 |
| warehouse-10-20-10-2-1 | 100 | repair5e_caseb_ood_guard_distilled | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2621.0 | -48.666666666666515 | 19662.333333333332 | 0.6666666666666666 | 0.0 | 0.15783333333333333 |
| warehouse-10-20-10-2-1 | 100 | repair5e_caseb_ood_guard_force_additive_parity | 3 | 1.000000 | 1.13971749334 | 0.0 | 198.66666666666666 | 0.0 | 2602.3333333333335 | -67.33333333333303 | 19662.333333333332 | 0.5 | 0.0 | 0.0009 |

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
    "repair5e2_guarded_oracle_aligned_selector": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 3
    },
    "repair5e2_guarded_oracle_aligned_selector_force_additive_parity": {
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
  "paired_rows": 180,
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

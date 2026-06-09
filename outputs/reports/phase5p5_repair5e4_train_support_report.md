# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-06-01 10:02:36

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e4_train_support\phase5p5_repair5e4_train_support.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e4_train_support\phase5p5_repair5e4_train_support_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e4_train_support\phase5p5_repair5e4_train_support_commands.jsonl`

## Provenance

- git branch: `phase4f5p5-stable-attention-lau`
- git commit: `48b5c6d`
- git dirty state: `tracked-dirty_untracked-present`
- clean tracked worktree: `False`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agent_counts: `[50, 100]`
- instances_per_setting: `3`
- instance_ids: `[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`
- methods: `['lacam_star_ltm', 'always_additive_defer', 'oracle_teacher_forced_best_safe_update_static_proxy']`
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
- `repair5e4_closed_loop_utility_selector_runtime`: `missing_runtime_dir_or_required_files`
- `repair5e4_closed_loop_utility_selector_shuffled_labels_runtime`: `missing_runtime_dir_or_required_files`
- `repair5e4_calibrated_guard_only_on_e3_split_runtime`: `missing_runtime_dir_or_required_files`

## Group Summary

| map | agents | method | runs | success | ratio | d ratio | expanded | d expanded | TTFS ms | d TTFS | pibt | fallback | non-additive | overhead ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| maze-32-32-4 | 50 | always_additive_defer | 10 | 1.000000 | 1.160701662635 | 0.0 | 410.8 | 0.0 | 193.7 | -0.30000000000001137 | 20394.6 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.160701662635 | None | 410.8 | None | 194.0 | None | 20394.6 | None | None | 0.0 |
| maze-32-32-4 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.144785063932 | -0.015916598702999885 | 404.2 | -6.600000000000023 | 194.4 | 0.4000000000000057 | 20079.8 | 0.25 | 0.75 | 0.0 |
| maze-32-32-4 | 100 | always_additive_defer | 10 | 1.000000 | 1.2633818951140001 | 0.0 | 548.8 | 0.0 | 400.9 | -3.5 | 72931.3 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.2633818951140001 | None | 548.8 | None | 404.4 | None | 72931.3 | None | None | 0.0 |
| maze-32-32-4 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.245836564518 | -0.017545330596000053 | 516.8 | -32.0 | 405.4 | 1.0 | 64695.7 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 50 | always_additive_defer | 10 | 1.000000 | 1.126452295887 | 0.0 | 240.5 | 0.0 | 161.9 | -0.5 | 14387.2 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.126452295887 | None | 240.5 | None | 162.4 | None | 14387.2 | None | None | 0.0 |
| random-32-32-20 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.123893240769 | -0.00255905511799992 | 215.1 | -25.400000000000006 | 161.5 | -0.9000000000000057 | 10749.9 | 0.25 | 0.75 | 0.0 |
| random-32-32-20 | 100 | always_additive_defer | 10 | 1.000000 | 1.262574747306 | 0.0 | 266.8 | 0.0 | 325.5 | -1.8999999999999773 | 33290.1 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.262574747306 | None | 266.8 | None | 327.4 | None | 33290.1 | None | None | 0.0 |
| random-32-32-20 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.2355786204919998 | -0.02699612681400021 | 278.5 | 11.699999999999989 | 327.1 | -0.2999999999999545 | 37664.3 | 0.25 | 0.75 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | always_additive_defer | 10 | 1.000000 | 1.088208780176 | 0.0 | 405.5 | -0.10000000000002274 | 1343.9 | -2.2999999999999545 | 20126.8 | 0.3448275862068966 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.088208780176 | None | 405.6 | None | 1346.2 | None | 20126.8 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.088208780176 | 0.0 | 405.0 | -0.6000000000000227 | 1354.5 | 8.299999999999955 | 20126.8 | 0.4166666666666667 | 0.5833333333333334 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | always_additive_defer | 10 | 0.900000 | 1.1513321067766666 | -0.004135967715333422 | 201.1 | -6.400000000000006 | 2713.6666666666665 | 1.8666666666663332 | 19925.5 | 0.5263157894736842 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.155468074492 | None | 207.5 | None | 2711.8 | None | 20555.5 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | oracle_teacher_forced_best_safe_update_static_proxy | 10 | 1.000000 | 1.155468074492 | 0.0 | 207.4 | -0.09999999999999432 | 2657.1 | -54.70000000000027 | 20555.5 | 0.5263157894736842 | 0.47368421052631576 | 0.0 |

## Stop Condition Snapshot

{
  "method_flags": {
    "always_additive_defer": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 1,
      "zero_nonadditive_groups": 6
    },
    "oracle_teacher_forced_best_safe_update_static_proxy": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    }
  },
  "oracle_replay_executed": true,
  "oracle_replay_scope": "static_rule_proxy",
  "paired_rows": 120,
  "repair5c_composite_closed_loop_executed": false,
  "repair5d_composite_closed_loop_executed": false,
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

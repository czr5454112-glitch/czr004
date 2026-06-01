# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-06-01 09:32:56

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e4_train_support_smoke\phase5p5_repair5e4_train_support_smoke.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e4_train_support_smoke\phase5p5_repair5e4_train_support_smoke_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e4_train_support_smoke\phase5p5_repair5e4_train_support_smoke_commands.jsonl`

## Provenance

- git branch: `phase4f5p5-stable-attention-lau`
- git commit: `48b5c6d`
- git dirty state: `tracked-dirty_untracked-present`
- clean tracked worktree: `False`

## Scope

- maps: `['random-32-32-20']`
- agent_counts: `[50]`
- instances_per_setting: `3`
- instance_ids: `[1]`
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
| random-32-32-20 | 50 | always_additive_defer | 1 | 1.000000 | 1.13415710503 | 0.0 | 328.0 | 0.0 | 170.0 | 3.0 | 28657.0 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 1 | 1.000000 | 1.13415710503 | None | 328.0 | None | 167.0 | None | 28657.0 | None | None | 0.0 |
| random-32-32-20 | 50 | oracle_teacher_forced_best_safe_update_static_proxy | 1 | 1.000000 | 1.13415710503 | 0.0 | 221.0 | -107.0 | 159.0 | -8.0 | 10846.0 | 0.25 | 0.75 | 0.0 |

## Stop Condition Snapshot

{
  "method_flags": {
    "always_additive_defer": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 1
    },
    "oracle_teacher_forced_best_safe_update_static_proxy": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    }
  },
  "oracle_replay_executed": true,
  "oracle_replay_scope": "static_rule_proxy",
  "paired_rows": 2,
  "repair5c_composite_closed_loop_executed": false,
  "repair5d_composite_closed_loop_executed": false,
  "strict_safety_mask_blocks_all_learned_choices": false
}

## Decision Table Interpretation

{
  "case": "C",
  "oracle_positive": false,
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "recommended_action": "stop_offline_gate_optimization_and_redesign_labels_or_output_space",
  "repair5d_positive": false
}

# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-05-31 17:55:37

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e2_runtime_feature_ood\phase5p5_repair5e2_runtime_feature_ood.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e2_runtime_feature_ood\phase5p5_repair5e2_runtime_feature_ood_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e2_runtime_feature_ood\phase5p5_repair5e2_runtime_feature_ood_commands.jsonl`

## Scope

- maps: `['random-32-32-20']`
- agent_counts: `[50]`
- instances_per_setting: `1`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`
- methods: `['lacam_star', 'lacam_star_ltm', 'always_additive_defer', 'repair3_safe_runtime', 'repair5d_composite_diagnostic_distilled', 'repair5d_force_additive_defer_parity', 'repair5e_caseb_ood_guard_distilled', 'repair5e_caseb_ood_guard_force_additive_parity']`
- support_methods: `[]`

## Runtime Availability

- `repair5d_native_composite_export`: `not_feasible_current_cxx_runtime_accepts_single_mlp_runtime_only_distilled_bridge_used`
- `oracle_teacher_forced_best_safe_update`: `not_executed_pass_include_oracle_static_probe_for_static_upper_bound_proxy`
- `repair3_runtime_export`: `existing_runtime_dir`
- `repair5d_spec`: `available`
- `repair5d_runtime_distill`: `available`
- `repair5e_ood_guard_runtime`: `available`
- `repair5e2_guarded_oracle_aligned_selector_runtime`: `available`

## Group Summary

| map | agents | method | runs | success | ratio | d ratio | expanded | d expanded | TTFS ms | d TTFS | pibt | fallback | non-additive | overhead ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| random-32-32-20 | 50 | always_additive_defer | 1 | 1.000000 | 1.13415710503 | 0.0 | 328.0 | 0.0 | 169.0 | -2.0 | 28657.0 | 0.25 | 0.0 | 0.0015 |
| random-32-32-20 | 50 | lacam_star | 1 | 1.000000 | 1.15269196823 | 0.018534863200000196 | 21574.0 | 21246.0 | 3302.3539 | 3131.3539 | None | None | None | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 1 | 1.000000 | 1.13415710503 | None | 328.0 | None | 171.0 | None | 28657.0 | None | None | 0.0 |
| random-32-32-20 | 50 | repair3_safe_runtime | 1 | 1.000000 | 1.13415710503 | 0.0 | 358.0 | 30.0 | 175.0 | 4.0 | 32327.0 | 0.25 | 0.75 | 0.3554 |
| random-32-32-20 | 50 | repair5d_composite_diagnostic_distilled | 1 | 1.000000 | 1.13415710503 | 0.0 | 358.0 | 30.0 | 170.0 | -1.0 | 32327.0 | 0.25 | 0.75 | 0.3867 |
| random-32-32-20 | 50 | repair5d_force_additive_defer_parity | 1 | 1.000000 | 1.13415710503 | 0.0 | 328.0 | 0.0 | 162.0 | -9.0 | 28657.0 | 0.25 | 0.0 | 0.0013 |
| random-32-32-20 | 50 | repair5e_caseb_ood_guard_distilled | 1 | 1.000000 | 1.13415710503 | 0.0 | 328.0 | 0.0 | 165.0 | -6.0 | 28657.0 | 0.5714285714285714 | 0.0 | 0.3676 |
| random-32-32-20 | 50 | repair5e_caseb_ood_guard_force_additive_parity | 1 | 1.000000 | 1.13415710503 | 0.0 | 328.0 | 0.0 | 161.0 | -10.0 | 28657.0 | 0.25 | 0.0 | 0.0014 |

## Stop Condition Snapshot

{
  "method_flags": {
    "always_additive_defer": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 1
    },
    "lacam_star": {
      "ratio_worse_than_ltm_groups": 1,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair3_safe_runtime": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair5d_composite_diagnostic_distilled": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair5d_force_additive_defer_parity": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 1
    },
    "repair5e_caseb_ood_guard_distilled": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 1
    },
    "repair5e_caseb_ood_guard_force_additive_parity": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 1
    }
  },
  "oracle_replay_executed": false,
  "oracle_replay_scope": "not_executed",
  "paired_rows": 7,
  "repair5c_composite_closed_loop_executed": false,
  "repair5d_composite_closed_loop_executed": true,
  "strict_safety_mask_blocks_all_learned_choices": false
}

## Decision Table Interpretation

{
  "case": "C",
  "oracle_positive": false,
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "recommended_action": "stop_offline_gate_optimization_and_redesign_labels_or_output_space",
  "repair5d_positive": true
}

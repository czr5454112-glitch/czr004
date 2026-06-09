# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-06-01 12:52:24

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_selector_smoke\phase5p5_repair5e5_selector_smoke.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_selector_smoke\phase5p5_repair5e5_selector_smoke_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e5_selector_smoke\phase5p5_repair5e5_selector_smoke_commands.jsonl`

## Provenance

- git branch: `phase4f5p5-stable-attention-lau`
- git commit: `db0f494`
- git dirty state: `tracked-dirty_untracked-present`
- clean tracked worktree: `False`

## Scope

- maps: `['random-32-32-20']`
- agent_counts: `[50]`
- instances_per_setting: `3`
- instance_ids: `[21]`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`
- methods: `['lacam_star_ltm', 'repair5e5_crossfold_utility_reranker', 'repair5e5_crossfold_utility_reranker_force_additive_parity', 'repair5e5_crossfold_utility_reranker_recovery_disabled_parity', 'repair5e5_crossfold_utility_reranker_no_ood_guard_diagnostic', 'repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic', 'repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic', 'repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic']`
- support_methods: `[]`

## Runtime Availability

- `repair5d_native_composite_export`: `not_feasible_current_cxx_runtime_accepts_single_mlp_runtime_only_distilled_bridge_used`
- `oracle_teacher_forced_best_safe_update`: `not_executed_pass_include_oracle_static_probe_for_static_upper_bound_proxy`
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
| random-32-32-20 | 50 | lacam_star_ltm | 1 | 1.000000 | 1.1421686747 | None | 308.0 | None | 163.0 | None | 30012.0 | None | None | 0.0 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker | 1 | 1.000000 | 1.1421686747 | 0.0 | 323.0 | 15.0 | 164.0 | 1.0 | 29911.0 | 0.25 | 0.75 | 0.4329 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_force_additive_parity | 1 | 1.000000 | 1.1421686747 | 0.0 | 308.0 | 0.0 | 168.0 | 5.0 | 30012.0 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic | 1 | 1.000000 | 1.1421686747 | 0.0 | 323.0 | 15.0 | 166.0 | 3.0 | 29911.0 | 0.25 | 0.75 | 0.3981 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_no_ood_guard_diagnostic | 1 | 1.000000 | 1.1421686747 | 0.0 | 323.0 | 15.0 | 161.0 | -2.0 | 29911.0 | 0.25 | 0.75 | 0.4027 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_recovery_disabled_parity | 1 | 1.000000 | 1.1421686747 | 0.0 | 308.0 | 0.0 | 165.0 | 2.0 | 30012.0 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic | 1 | 1.000000 | 1.1421686747 | 0.0 | 323.0 | 15.0 | 163.0 | 0.0 | 29911.0 | 0.25 | 0.75 | 0.5145 |
| random-32-32-20 | 50 | repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic | 1 | 1.000000 | 1.1421686747 | 0.0 | 300.0 | -8.0 | 164.0 | 1.0 | 28418.0 | 0.25 | 0.75 | 0.4158 |

## Stop Condition Snapshot

{
  "method_flags": {
    "repair5e5_crossfold_utility_reranker": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair5e5_crossfold_utility_reranker_force_additive_parity": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 1
    },
    "repair5e5_crossfold_utility_reranker_loose_threshold_diagnostic": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair5e5_crossfold_utility_reranker_no_ood_guard_diagnostic": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair5e5_crossfold_utility_reranker_recovery_disabled_parity": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 1
    },
    "repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair5e5_crossfold_utility_reranker_strict_threshold_diagnostic": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    }
  },
  "oracle_replay_executed": false,
  "oracle_replay_scope": "not_executed",
  "paired_rows": 7,
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
  "recommended_action": "do_not_promote_repair5e5_consider_repair5f_side_branch_after_diagnostics",
  "repair5e5_crossfold_utility_reranker_positive": false
}

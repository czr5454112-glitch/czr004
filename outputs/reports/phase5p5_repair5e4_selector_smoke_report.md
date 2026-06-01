# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-06-01 10:05:33

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e4_selector_smoke\phase5p5_repair5e4_selector_smoke.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e4_selector_smoke\phase5p5_repair5e4_selector_smoke_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e4_selector_smoke\phase5p5_repair5e4_selector_smoke_commands.jsonl`

## Provenance

- git branch: `phase4f5p5-stable-attention-lau`
- git commit: `48b5c6d`
- git dirty state: `tracked-dirty_untracked-present`
- clean tracked worktree: `False`

## Scope

- maps: `['random-32-32-20']`
- agent_counts: `[50]`
- instances_per_setting: `3`
- instance_ids: `[21]`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`
- methods: `['lacam_star_ltm', 'repair5e4_closed_loop_utility_selector', 'repair5e4_closed_loop_utility_selector_force_additive_parity']`
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

## Group Summary

| map | agents | method | runs | success | ratio | d ratio | expanded | d expanded | TTFS ms | d TTFS | pibt | fallback | non-additive | overhead ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| random-32-32-20 | 50 | lacam_star_ltm | 1 | 1.000000 | 1.1421686747 | None | 308.0 | None | 172.0 | None | 30012.0 | None | None | 0.0 |
| random-32-32-20 | 50 | repair5e4_closed_loop_utility_selector | 1 | 1.000000 | 1.1421686747 | 0.0 | 206.0 | -102.0 | 166.0 | -6.0 | 10579.0 | 0.25 | 0.75 | 2.3295 |
| random-32-32-20 | 50 | repair5e4_closed_loop_utility_selector_force_additive_parity | 1 | 1.000000 | 1.1421686747 | 0.0 | 308.0 | 0.0 | 172.0 | 0.0 | 30012.0 | 0.25 | 0.0 | 0.0 |

## Stop Condition Snapshot

{
  "method_flags": {
    "repair5e4_closed_loop_utility_selector": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    },
    "repair5e4_closed_loop_utility_selector_force_additive_parity": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 1
    }
  },
  "oracle_replay_executed": false,
  "oracle_replay_scope": "not_executed",
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
  "recommended_action": "do_not_promote_repair5e4_rebuild_closed_loop_evidence",
  "repair5e4_closed_loop_utility_selector_positive": false
}

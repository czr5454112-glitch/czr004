# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-06-01 10:55:54

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e4_ablation\phase5p5_repair5e4_ablation.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e4_ablation\phase5p5_repair5e4_ablation_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e4_ablation\phase5p5_repair5e4_ablation_commands.jsonl`

## Provenance

- git branch: `phase4f5p5-stable-attention-lau`
- git commit: `48b5c6d`
- git dirty state: `tracked-dirty_untracked-present`
- clean tracked worktree: `False`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agent_counts: `[50, 100]`
- instances_per_setting: `3`
- instance_ids: `[11, 12, 13, 14, 15, 16, 17, 18, 19, 20]`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`
- methods: `['lacam_star_ltm', 'repair5e4_calibrated_guard_only_on_e3_split', 'repair5e4_closed_loop_utility_selector', 'repair5e4_closed_loop_utility_selector_force_additive_parity', 'repair5e4_closed_loop_utility_selector_recovery_disabled_parity', 'repair5e4_closed_loop_utility_selector_no_ood_guard_diagnostic', 'repair5e4_closed_loop_utility_selector_shuffled_labels_diagnostic']`
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
| maze-32-32-4 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.1398036303879 | None | 438.3 | None | 182.6 | None | 21738.9 | None | None | 0.0 |
| maze-32-32-4 | 50 | repair5e4_calibrated_guard_only_on_e3_split | 10 | 1.000000 | 1.1398036303879 | 0.0 | 438.3 | 0.0 | 183.5 | 0.9000000000000057 | 21738.9 | 0.25 | 0.0 | 0.43146 |
| maze-32-32-4 | 50 | repair5e4_closed_loop_utility_selector | 10 | 1.000000 | 1.1398036303879 | 0.0 | 438.3 | 0.0 | 182.4 | -0.19999999999998863 | 21738.9 | 0.25 | 0.0 | 0.43701 |
| maze-32-32-4 | 50 | repair5e4_closed_loop_utility_selector_force_additive_parity | 10 | 1.000000 | 1.1398036303879 | 0.0 | 438.3 | 0.0 | 183.6 | 1.0 | 21738.9 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | repair5e4_closed_loop_utility_selector_no_ood_guard_diagnostic | 10 | 1.000000 | 1.1398036303879 | 0.0 | 438.3 | 0.0 | 183.1 | 0.5 | 21738.9 | 0.25 | 0.0 | 0.453 |
| maze-32-32-4 | 50 | repair5e4_closed_loop_utility_selector_recovery_disabled_parity | 10 | 1.000000 | 1.1398036303879 | 0.0 | 438.3 | 0.0 | 182.6 | 0.0 | 21738.9 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 50 | repair5e4_closed_loop_utility_selector_shuffled_labels_diagnostic | 10 | 1.000000 | 1.1398036303879 | 0.0 | 438.3 | 0.0 | 183.9 | 1.3000000000000114 | 21738.9 | 0.25 | 0.0 | 0.4456 |
| maze-32-32-4 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.2492997628640001 | None | 566.0 | None | 385.0 | None | 71451.8 | None | None | 0.0 |
| maze-32-32-4 | 100 | repair5e4_calibrated_guard_only_on_e3_split | 10 | 1.000000 | 1.245093510612 | -0.004206252252000109 | 570.3 | 4.2999999999999545 | 386.1 | 1.1000000000000227 | 71638.2 | 0.25 | 0.75 | 0.42123 |
| maze-32-32-4 | 100 | repair5e4_closed_loop_utility_selector | 10 | 1.000000 | 1.2492997628640001 | 0.0 | 566.0 | 0.0 | 386.3 | 1.3000000000000114 | 71451.8 | 0.25 | 0.0 | 0.45273 |
| maze-32-32-4 | 100 | repair5e4_closed_loop_utility_selector_force_additive_parity | 10 | 1.000000 | 1.2492997628640001 | 0.0 | 566.0 | 0.0 | 385.1 | 0.10000000000002274 | 71451.8 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | repair5e4_closed_loop_utility_selector_no_ood_guard_diagnostic | 10 | 1.000000 | 1.2492997628640001 | 0.0 | 566.0 | 0.0 | 385.0 | 0.0 | 71451.8 | 0.25 | 0.0 | 0.44321 |
| maze-32-32-4 | 100 | repair5e4_closed_loop_utility_selector_recovery_disabled_parity | 10 | 1.000000 | 1.2492997628640001 | 0.0 | 566.0 | 0.0 | 385.0 | 0.0 | 71451.8 | 0.25 | 0.0 | 0.0 |
| maze-32-32-4 | 100 | repair5e4_closed_loop_utility_selector_shuffled_labels_diagnostic | 10 | 1.000000 | 1.2492997628640001 | 0.0 | 566.0 | 0.0 | 386.6 | 1.6000000000000227 | 71451.8 | 0.25 | 0.0 | 0.44844 |
| random-32-32-20 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.134427121036 | None | 223.3 | None | 158.9 | None | 11440.0 | None | None | 0.0 |
| random-32-32-20 | 50 | repair5e4_calibrated_guard_only_on_e3_split | 10 | 1.000000 | 1.129702542965 | -0.0047245780709999075 | 229.9 | 6.599999999999994 | 158.4 | -0.5 | 12478.7 | 0.25 | 0.75 | 0.41855 |
| random-32-32-20 | 50 | repair5e4_closed_loop_utility_selector | 10 | 1.000000 | 1.127065788059 | -0.007361332976999924 | 223.4 | 0.09999999999999432 | 158.8 | -0.09999999999999432 | 11643.5 | 0.25 | 0.75 | 0.42174 |
| random-32-32-20 | 50 | repair5e4_closed_loop_utility_selector_force_additive_parity | 10 | 1.000000 | 1.134427121036 | 0.0 | 223.3 | 0.0 | 157.9 | -1.0 | 11440.0 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | repair5e4_closed_loop_utility_selector_no_ood_guard_diagnostic | 10 | 1.000000 | 1.127065788059 | -0.007361332976999924 | 223.4 | 0.09999999999999432 | 157.8 | -1.0999999999999943 | 11643.5 | 0.25 | 0.75 | 0.46317 |
| random-32-32-20 | 50 | repair5e4_closed_loop_utility_selector_recovery_disabled_parity | 10 | 1.000000 | 1.134427121036 | 0.0 | 223.3 | 0.0 | 158.5 | -0.4000000000000057 | 11440.0 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 50 | repair5e4_closed_loop_utility_selector_shuffled_labels_diagnostic | 10 | 1.000000 | 1.129896838287 | -0.004530282748999914 | 223.2 | -0.10000000000002274 | 158.0 | -0.9000000000000057 | 11623.9 | 0.25 | 0.75 | 0.4233 |
| random-32-32-20 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.267150755212 | None | 268.2 | None | 317.1 | None | 32135.3 | None | None | 0.0 |
| random-32-32-20 | 100 | repair5e4_calibrated_guard_only_on_e3_split | 10 | 1.000000 | 1.268575825252 | 0.0014250700400000316 | 268.8 | 0.6000000000000227 | 317.4 | 0.2999999999999545 | 31742.0 | 0.25 | 0.75 | 0.47929 |
| random-32-32-20 | 100 | repair5e4_closed_loop_utility_selector | 10 | 1.000000 | 1.269562964201 | 0.0024122089889999643 | 261.7 | -6.5 | 316.2 | -0.9000000000000341 | 30142.8 | 0.25 | 0.75 | 0.41096 |
| random-32-32-20 | 100 | repair5e4_closed_loop_utility_selector_force_additive_parity | 10 | 1.000000 | 1.267150755212 | 0.0 | 268.2 | 0.0 | 317.5 | 0.39999999999997726 | 32135.3 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | repair5e4_closed_loop_utility_selector_no_ood_guard_diagnostic | 10 | 1.000000 | 1.269562964201 | 0.0024122089889999643 | 261.7 | -6.5 | 317.3 | 0.19999999999998863 | 30142.8 | 0.25 | 0.75 | 0.44673999999999997 |
| random-32-32-20 | 100 | repair5e4_closed_loop_utility_selector_recovery_disabled_parity | 10 | 1.000000 | 1.267150755212 | 0.0 | 268.2 | 0.0 | 317.7 | 0.5999999999999659 | 32135.3 | 0.25 | 0.0 | 0.0 |
| random-32-32-20 | 100 | repair5e4_closed_loop_utility_selector_shuffled_labels_diagnostic | 10 | 1.000000 | 1.269562964201 | 0.0024122089889999643 | 261.7 | -6.5 | 317.5 | 0.39999999999997726 | 30142.8 | 0.25 | 0.75 | 0.42972 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.082185273507 | None | 380.4 | None | 1217.8 | None | 18872.1 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5e4_calibrated_guard_only_on_e3_split | 10 | 1.000000 | 1.082185273507 | 0.0 | 381.5 | 1.1000000000000227 | 1222.7 | 4.900000000000091 | 18927.1 | 0.3448275862068966 | 0.0 | 0.31069 |
| warehouse-10-20-10-2-1 | 50 | repair5e4_closed_loop_utility_selector | 10 | 1.000000 | 1.082185273507 | 0.0 | 381.6 | 1.2000000000000455 | 1225.8 | 8.0 | 18927.1 | 0.3333333333333333 | 0.0 | 0.37312 |
| warehouse-10-20-10-2-1 | 50 | repair5e4_closed_loop_utility_selector_force_additive_parity | 10 | 1.000000 | 1.082185273507 | 0.0 | 381.5 | 1.1000000000000227 | 1227.2 | 9.400000000000091 | 18927.1 | 0.3448275862068966 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5e4_closed_loop_utility_selector_no_ood_guard_diagnostic | 10 | 1.000000 | 1.082185273507 | 0.0 | 381.6 | 1.2000000000000455 | 1176.0 | -41.799999999999955 | 18927.1 | 0.3333333333333333 | 0.0 | 0.37217 |
| warehouse-10-20-10-2-1 | 50 | repair5e4_closed_loop_utility_selector_recovery_disabled_parity | 10 | 1.000000 | 1.082185273507 | 0.0 | 381.6 | 1.2000000000000455 | 1211.5 | -6.2999999999999545 | 18927.1 | 0.3333333333333333 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5e4_closed_loop_utility_selector_shuffled_labels_diagnostic | 10 | 1.000000 | 1.082185273507 | 0.0 | 381.6 | 1.2000000000000455 | 1179.6 | -38.200000000000045 | 18927.1 | 0.3333333333333333 | 0.0 | 0.40265 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.178282383689 | None | 211.3 | None | 2355.7 | None | 20922.3 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5e4_calibrated_guard_only_on_e3_split | 10 | 1.000000 | 1.178282383689 | 0.0 | 211.3 | 0.0 | 2336.5 | -19.199999999999818 | 20922.3 | 0.5 | 0.0 | 0.21598 |
| warehouse-10-20-10-2-1 | 100 | repair5e4_closed_loop_utility_selector | 10 | 1.000000 | 1.178282383689 | 0.0 | 211.3 | 0.0 | 2336.8 | -18.899999999999636 | 20922.3 | 0.5 | 0.0 | 0.24152 |
| warehouse-10-20-10-2-1 | 100 | repair5e4_closed_loop_utility_selector_force_additive_parity | 10 | 1.000000 | 1.178282383689 | 0.0 | 211.3 | 0.0 | 2323.0 | -32.69999999999982 | 20922.3 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5e4_closed_loop_utility_selector_no_ood_guard_diagnostic | 10 | 1.000000 | 1.178282383689 | 0.0 | 211.3 | 0.0 | 2329.8 | -25.899999999999636 | 20922.3 | 0.5 | 0.0 | 0.25095 |
| warehouse-10-20-10-2-1 | 100 | repair5e4_closed_loop_utility_selector_recovery_disabled_parity | 10 | 1.000000 | 1.178282383689 | 0.0 | 211.3 | 0.0 | 2345.1 | -10.599999999999909 | 20922.3 | 0.5 | 0.0 | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5e4_closed_loop_utility_selector_shuffled_labels_diagnostic | 10 | 1.000000 | 1.178282383689 | 0.0 | 211.3 | 0.0 | 2329.3 | -26.399999999999636 | 20922.3 | 0.5 | 0.0 | 0.23444 |

## Stop Condition Snapshot

{
  "method_flags": {
    "repair5e4_calibrated_guard_only_on_e3_split": {
      "ratio_worse_than_ltm_groups": 1,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 3
    },
    "repair5e4_closed_loop_utility_selector": {
      "ratio_worse_than_ltm_groups": 1,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 4
    },
    "repair5e4_closed_loop_utility_selector_force_additive_parity": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "repair5e4_closed_loop_utility_selector_no_ood_guard_diagnostic": {
      "ratio_worse_than_ltm_groups": 1,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 4
    },
    "repair5e4_closed_loop_utility_selector_recovery_disabled_parity": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "repair5e4_closed_loop_utility_selector_shuffled_labels_diagnostic": {
      "ratio_worse_than_ltm_groups": 1,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 4
    }
  },
  "oracle_replay_executed": false,
  "oracle_replay_scope": "not_executed",
  "paired_rows": 360,
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

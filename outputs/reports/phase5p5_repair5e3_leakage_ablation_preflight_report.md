# Phase5.5 Repair5E LAUR Diagnostic Preflight Report

Date: 2026-05-31 20:19:14

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e3_leakage_ablation\phase5p5_repair5e3_leakage_ablation.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e3_leakage_ablation\phase5p5_repair5e3_leakage_ablation_laur_updates.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5e3_leakage_ablation\phase5p5_repair5e3_leakage_ablation_commands.jsonl`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agent_counts: `[50, 100]`
- instances_per_setting: `10`
- instance_ids: `[4, 5, 6, 7, 8, 9, 10, 11, 12, 13]`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`
- methods: `['lacam_star_ltm', 'always_additive_defer', 'repair5e2_guarded_oracle_aligned_selector', 'repair5e3_e2_recovery_disabled_parity', 'repair5e3_e2_recovery_shuffled_support_diagnostic']`
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

## Group Summary

| map | agents | method | runs | success | ratio | d ratio | expanded | d expanded | TTFS ms | d TTFS | pibt | fallback | non-additive | overhead ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| maze-32-32-4 | 50 | always_additive_defer | 10 | 1.000000 | 1.179648373932 | 0.0 | 418.6 | 0.0 | 184.7 | -4.0 | 20784.6 | 0.25 | 0.0 | 0.00134 |
| maze-32-32-4 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.179648373932 | None | 418.6 | None | 188.7 | None | 20784.6 | None | None | 0.0 |
| maze-32-32-4 | 50 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.179648373932 | 0.0 | 418.6 | 0.0 | 185.8 | -2.8999999999999773 | 20784.6 | 0.25 | 0.0 | 0.35765 |
| maze-32-32-4 | 50 | repair5e3_e2_recovery_disabled_parity | 10 | 1.000000 | 1.179648373932 | 0.0 | 418.6 | 0.0 | 187.8 | -0.8999999999999773 | 20784.6 | 0.25 | 0.0 | 0.00142 |
| maze-32-32-4 | 50 | repair5e3_e2_recovery_shuffled_support_diagnostic | 10 | 1.000000 | 1.179648373932 | 0.0 | 418.6 | 0.0 | 184.2 | -4.5 | 20784.6 | 0.5714285714285714 | 0.0 | 0.34192 |
| maze-32-32-4 | 100 | always_additive_defer | 10 | 1.000000 | 1.274641298306 | 0.0 | 570.7 | 0.0 | 389.4 | 0.6999999999999886 | 76626.8 | 0.25 | 0.0 | 0.00163 |
| maze-32-32-4 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.274641298306 | None | 570.7 | None | 388.7 | None | 76626.8 | None | None | 0.0 |
| maze-32-32-4 | 100 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.277044530069 | 0.0024032317630000577 | 538.9 | -31.800000000000068 | 388.5 | -0.19999999999998863 | 64830.1 | 0.25 | 0.75 | 0.38268 |
| maze-32-32-4 | 100 | repair5e3_e2_recovery_disabled_parity | 10 | 1.000000 | 1.274641298306 | 0.0 | 570.7 | 0.0 | 390.3 | 1.6000000000000227 | 76626.8 | 0.25 | 0.0 | 0.0015 |
| maze-32-32-4 | 100 | repair5e3_e2_recovery_shuffled_support_diagnostic | 10 | 1.000000 | 1.274641298306 | 0.0 | 570.7 | 0.0 | 388.4 | -0.30000000000001137 | 76626.8 | 0.5714285714285714 | 0.0 | 0.34399 |
| random-32-32-20 | 50 | always_additive_defer | 10 | 1.000000 | 1.136125751546 | 0.0 | 225.7 | 0.0 | 165.4 | 1.5 | 11107.4 | 0.25 | 0.0 | 0.00133 |
| random-32-32-20 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.136125751546 | None | 225.7 | None | 163.9 | None | 11107.4 | None | None | 0.0 |
| random-32-32-20 | 50 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.136125751546 | 0.0 | 227.4 | 1.700000000000017 | 162.3 | -1.5999999999999943 | 11466.5 | 0.25 | 0.75 | 0.36113 |
| random-32-32-20 | 50 | repair5e3_e2_recovery_disabled_parity | 10 | 1.000000 | 1.136125751546 | 0.0 | 225.7 | 0.0 | 163.5 | -0.4000000000000057 | 11107.4 | 0.25 | 0.0 | 0.00154 |
| random-32-32-20 | 50 | repair5e3_e2_recovery_shuffled_support_diagnostic | 10 | 1.000000 | 1.136125751546 | 0.0 | 225.7 | 0.0 | 161.2 | -2.700000000000017 | 11107.4 | 0.5714285714285714 | 0.0 | 0.34932 |
| random-32-32-20 | 100 | always_additive_defer | 10 | 1.000000 | 1.26309792983 | 0.0 | 282.5 | 0.0 | 322.4 | -7.800000000000011 | 36713.9 | 0.25 | 0.0 | 0.00137 |
| random-32-32-20 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.26309792983 | None | 282.5 | None | 330.2 | None | 36713.9 | None | None | 0.0 |
| random-32-32-20 | 100 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.270130312873 | 0.007032383042999912 | 286.0 | 3.5 | 323.6 | -6.599999999999966 | 38181.5 | 0.25 | 0.75 | 0.34772 |
| random-32-32-20 | 100 | repair5e3_e2_recovery_disabled_parity | 10 | 1.000000 | 1.26309792983 | 0.0 | 282.5 | 0.0 | 328.3 | -1.8999999999999773 | 36713.9 | 0.25 | 0.0 | 0.00147 |
| random-32-32-20 | 100 | repair5e3_e2_recovery_shuffled_support_diagnostic | 10 | 1.000000 | 1.26309792983 | 0.0 | 282.5 | 0.0 | 324.8 | -5.399999999999977 | 36713.9 | 0.5714285714285714 | 0.0 | 0.34723 |
| warehouse-10-20-10-2-1 | 50 | always_additive_defer | 10 | 1.000000 | 1.084755136352 | 0.0 | 393.6 | 0.0 | 1298.0 | -1.0 | 19527.8 | 0.3333333333333333 | 0.0 | 0.02418 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 10 | 1.000000 | 1.084755136352 | None | 393.6 | None | 1299.0 | None | 19527.8 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.084755136352 | 0.0 | 393.6 | 0.0 | 1277.8 | -21.200000000000045 | 19527.8 | 0.5 | 0.0 | 0.29131 |
| warehouse-10-20-10-2-1 | 50 | repair5e3_e2_recovery_disabled_parity | 10 | 1.000000 | 1.084755136352 | 0.0 | 393.6 | 0.0 | 1239.2 | -59.799999999999955 | 19527.8 | 0.3333333333333333 | 0.0 | 0.00127 |
| warehouse-10-20-10-2-1 | 50 | repair5e3_e2_recovery_shuffled_support_diagnostic | 10 | 1.000000 | 1.084755136352 | 0.0 | 393.5 | -0.10000000000002274 | 1255.8 | -43.200000000000045 | 19527.8 | 0.6041666666666666 | 0.0 | 0.2762 |
| warehouse-10-20-10-2-1 | 100 | always_additive_defer | 10 | 1.000000 | 1.164186801731 | 0.0 | 207.1 | 0.0 | 2524.5 | 31.199999999999818 | 20514.3 | 0.5 | 0.0 | 0.00071 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 10 | 1.000000 | 1.164186801731 | None | 207.1 | None | 2493.3 | None | 20514.3 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair5e2_guarded_oracle_aligned_selector | 10 | 1.000000 | 1.164186801731 | 0.0 | 207.1 | 0.0 | 2483.0 | -10.300000000000182 | 20514.3 | 0.6666666666666666 | 0.0 | 0.15724 |
| warehouse-10-20-10-2-1 | 100 | repair5e3_e2_recovery_disabled_parity | 10 | 1.000000 | 1.164186801731 | 0.0 | 207.1 | 0.0 | 2500.1 | 6.799999999999727 | 20514.3 | 0.5 | 0.0 | 0.00069 |
| warehouse-10-20-10-2-1 | 100 | repair5e3_e2_recovery_shuffled_support_diagnostic | 10 | 1.000000 | 1.164186801731 | 0.0 | 207.1 | 0.0 | 2515.6 | 22.299999999999727 | 20514.3 | 0.6666666666666666 | 0.0 | 0.16268 |

## Stop Condition Snapshot

{
  "method_flags": {
    "always_additive_defer": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "repair5e2_guarded_oracle_aligned_selector": {
      "ratio_worse_than_ltm_groups": 2,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 3
    },
    "repair5e3_e2_recovery_disabled_parity": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    },
    "repair5e3_e2_recovery_shuffled_support_diagnostic": {
      "ratio_worse_than_ltm_groups": 0,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 6
    }
  },
  "oracle_replay_executed": false,
  "oracle_replay_scope": "not_executed",
  "paired_rows": 240,
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

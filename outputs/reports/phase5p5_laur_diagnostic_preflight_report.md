# Phase5.5 LAUR Diagnostic Preflight Report

Date: 2026-05-31 13:22:31

## Boundary

This is diagnostic-only closed-loop evidence. It does not permit Phase5.5 runtime promotion, does not permit Phase6, and does not change solver semantics.

- Phase5.5 allowed: `False`
- Phase6 allowed: `False`
- raw JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_laur_diagnostic_preflight\phase5p5_laur_diagnostic_preflight_20260531_131839.jsonl`
- command log: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_laur_diagnostic_preflight\phase5p5_laur_diagnostic_preflight_20260531_131839_commands.jsonl`

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agent_counts: `[50, 100]`
- instances_per_setting: `3`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`
- methods: `['lacam_star', 'lacam_star_ltm', 'always_additive_defer', 'repair3_safe_runtime']`

## Runtime Availability

- `repair5c_top3_per_rule_safety_utility_composite`: `not_executed_attention_native_composite_has_no_cxx_runtime_export`
- `oracle_replay_or_teacher_forced_update_choices`: `not_feasible_no_closed_loop_teacher_force_hook`
- `repair3_runtime_export`: `existing_runtime_dir`

## Group Summary

| map | agents | method | runs | success | ratio | expanded | TTFS ms | pibt | fallback | non-additive | overhead ms |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| maze-32-32-4 | 50 | always_additive_defer | 3 | 1.000000 | 1.1401441011333333 | 432.6666666666667 | 191.66666666666666 | 21433.333333333332 | 0.25 | 0.0 | 0.0014333333333333333 |
| maze-32-32-4 | 50 | lacam_star | 3 | 1.000000 | 1.1470132688133334 | 6599.666666666667 | 3102.4275 | None | None | None | 0.0 |
| maze-32-32-4 | 50 | lacam_star_ltm | 3 | 1.000000 | 1.1401441011333333 | 432.6666666666667 | 191.66666666666666 | 21433.333333333332 | None | None | 0.0 |
| maze-32-32-4 | 50 | repair3_safe_runtime | 3 | 1.000000 | 1.15399561856 | 442.0 | 195.0 | 21900.0 | 0.25 | 0.75 | 0.3052666666666667 |
| maze-32-32-4 | 100 | always_additive_defer | 3 | 1.000000 | 1.2851182965933334 | 482.3333333333333 | 396.3333333333333 | 48214.666666666664 | 0.25 | 0.0 | 0.0014333333333333333 |
| maze-32-32-4 | 100 | lacam_star | 3 | 1.000000 | 1.31428648418 | 11516.333333333334 | 3148.0506 | None | None | None | 0.0 |
| maze-32-32-4 | 100 | lacam_star_ltm | 3 | 1.000000 | 1.2851182965933334 | 482.3333333333333 | 393.3333333333333 | 48214.666666666664 | None | None | 0.0 |
| maze-32-32-4 | 100 | repair3_safe_runtime | 3 | 1.000000 | 1.2689469156366666 | 463.6666666666667 | 397.3333333333333 | 46055.666666666664 | 0.25 | 0.75 | 0.3364333333333333 |
| random-32-32-20 | 50 | always_additive_defer | 3 | 1.000000 | 1.1178396362133334 | 279.0 | 156.0 | 22213.0 | 0.25 | 0.0 | 0.0017666666666666666 |
| random-32-32-20 | 50 | lacam_star | 3 | 1.000000 | 1.1221591878866668 | 17883.333333333332 | 3254.395466666667 | None | None | None | 0.0 |
| random-32-32-20 | 50 | lacam_star_ltm | 3 | 1.000000 | 1.1178396362133334 | 279.0 | 156.0 | 22213.0 | None | None | 0.0 |
| random-32-32-20 | 50 | repair3_safe_runtime | 3 | 1.000000 | 1.1178396362133334 | 252.0 | 156.0 | 17357.333333333332 | 0.25 | 0.75 | 0.31893333333333335 |
| random-32-32-20 | 100 | always_additive_defer | 3 | 1.000000 | 1.2777344629866667 | 223.66666666666666 | 311.6666666666667 | 22157.666666666668 | 0.25 | 0.0 | 0.0015333333333333334 |
| random-32-32-20 | 100 | lacam_star | 3 | 1.000000 | 1.27971949887 | 8017.0 | 3098.6289 | None | None | None | 0.0 |
| random-32-32-20 | 100 | lacam_star_ltm | 3 | 1.000000 | 1.2777344629866667 | 223.66666666666666 | 311.6666666666667 | 22157.666666666668 | None | None | 0.0 |
| random-32-32-20 | 100 | repair3_safe_runtime | 3 | 1.000000 | 1.26817218132 | 310.0 | 312.6666666666667 | 47631.666666666664 | 0.25 | 0.75 | 0.30806666666666666 |
| warehouse-10-20-10-2-1 | 50 | always_additive_defer | 3 | 1.000000 | 1.0774394449566667 | 407.6666666666667 | 1216.6666666666667 | 20228.666666666668 | 0.3333333333333333 | 0.0 | 0.001 |
| warehouse-10-20-10-2-1 | 50 | lacam_star | 3 | 1.000000 | 1.0596392266699999 | 7998.0 | 3089.7941333333333 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | lacam_star_ltm | 3 | 1.000000 | 1.0774394449566667 | 407.6666666666667 | 1209.3333333333333 | 20228.666666666668 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 50 | repair3_safe_runtime | 3 | 1.000000 | 1.0774394449566667 | 407.6666666666667 | 1214.6666666666667 | 20228.666666666668 | 0.3333333333333333 | 0.6666666666666666 | 0.27563333333333334 |
| warehouse-10-20-10-2-1 | 100 | always_additive_defer | 3 | 1.000000 | 1.13971749334 | 198.66666666666666 | 2397.6666666666665 | 19662.333333333332 | 0.5 | 0.0 | 0.0006666666666666666 |
| warehouse-10-20-10-2-1 | 100 | lacam_star | 3 | 1.000000 | 1.1424659003833333 | 3856.0 | 3052.8898666666664 | None | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | lacam_star_ltm | 3 | 1.000000 | 1.13971749334 | 198.66666666666666 | 2404.3333333333335 | 19662.333333333332 | None | None | 0.0 |
| warehouse-10-20-10-2-1 | 100 | repair3_safe_runtime | 3 | 1.000000 | 1.13971749334 | 198.66666666666666 | 2379.6666666666665 | 19662.333333333332 | 0.5 | 0.5 | 0.15096666666666667 |

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
    "repair3_safe_runtime": {
      "ratio_worse_than_ltm_groups": 1,
      "success_worse_than_ltm_groups": 0,
      "zero_nonadditive_groups": 0
    }
  },
  "oracle_replay_executed": false,
  "paired_rows": 54,
  "repair5c_composite_closed_loop_executed": false,
  "strict_safety_mask_blocks_all_learned_choices": false
}

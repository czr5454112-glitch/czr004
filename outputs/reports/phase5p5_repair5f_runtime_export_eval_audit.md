# Phase5.5 Repair5F.3 Runtime Export Evaluation Audit

This audit is diagnostic-only.

## Coverage

- raw_rows_before_dedupe: `300`
- raw_rows_after_dedupe: `300`
- expected_rows: `300`
- missing_rows: `0`
- schema_errors: `0`

## Gate Snapshot

- `force_additive_parity_exact`: `False`
- `exact_additive_candidate_parity_exact`: `False`
- `support_final_leakage_false`: `True`
- `runtime_selector_better_gt_worse`: `True`
- `runtime_selector_mean_delta_lt_0`: `True`
- `runtime_selector_ratio_worse_groups_le_1`: `True`
- `runtime_selector_success_worse_groups_eq_0`: `True`
- `runtime_selector_beats_random_diagnostic`: `True`
- `runtime_selector_beats_shuffled_utility_diagnostic`: `True`
- `runtime_selector_improves_over_e5_real_selector`: `True`
- `runtime_selector_does_not_collapse_to_additive_parity`: `True`
- `phase5p5_allowed_false`: `True`
- `phase6_allowed_false`: `True`

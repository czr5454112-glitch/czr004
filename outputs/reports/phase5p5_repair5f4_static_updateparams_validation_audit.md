# Phase5.5 Repair5F.4 Validation Audit

Diagnostic-only audit for row coverage, schema, parity, and static equality.

- expected_rows: `1800`
- raw_rows_before_dedupe: `1800`
- raw_rows_after_dedupe: `1800`
- missing_rows: `0`
- schema_errors: `0`
- selector_static_mismatch_count: `3`

## Mandatory Gates

- `full_expected_rows`: `True`
- `schema_errors_eq_0`: `True`
- `missing_rows_eq_0`: `True`
- `support_validation_overlap_count_eq_0`: `True`
- `f2f3_holdout_validation_overlap_count_eq_0`: `True`
- `force_additive_parity_exact`: `True`
- `exact_additive_candidate_parity_exact`: `True`
- `laur_disable_parity_exact`: `True`
- `laur_force_additive_direct_parity_exact`: `True`
- `selector_static_runtime_metrics_equal`: `True`
- `selector_selected_c100_b100_w075_d090_all_cases`: `True`
- `main_static_better_gt_worse`: `False`
- `main_static_mean_delta_ratio_vs_ltm_lt_0`: `False`
- `main_static_bootstrap_ci_upper_le_0`: `False`
- `main_static_ratio_worse_than_ltm_groups_le_1`: `False`
- `main_static_success_worse_than_ltm_groups_eq_0`: `True`
- `main_static_beats_deterministic_random_candidate_diagnostic`: `False`
- `phase5p5_allowed_false`: `True`
- `phase6_allowed_false`: `True`

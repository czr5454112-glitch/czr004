# Phase5.5 Repair5G.5.11 Confidence Targets v5 Analysis

- decision: `confidence_targets_v5_failed_continue_label_design`
- measured_confidence_contexts: `60`
- primary_1000_2000_stable_contexts: `60`
- head_b_training_rows: `60`
- label_counts: `{'stable_high_confidence_parameter_candidate': 52, 'stable_static': 8}`
- stable_static_or_abstain: `8`
- no_solution_or_budget_abstain_count: `0`
- gates: `{'measured_confidence_contexts_ge_60': True, 'primary_1000_2000_stable_contexts_ge_40': True, 'head_b_training_rows_ge_40': True, 'stable_high_confidence_parameter_candidate_ge_10': True, 'stable_static_or_abstain_ge_10': False, 'no_solution_or_budget_abstain_count_gt_0': False, 'abstain_to_static_searched_and_reported': True, 'observed_ids_only': True, 'ids_166_205_untouched': True}`

The target gate requires both nonstatic positives and static/abstention or no-solution/budget-abstention coverage before feature v3 or policy training is allowed.

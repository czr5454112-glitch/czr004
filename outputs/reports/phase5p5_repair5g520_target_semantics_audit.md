# Phase5.5 Repair5G.5.20 Target Metric Semantics Audit

- decision: `static_harm_semantics_bug_fixed_continue_corrected_targets`
- target_rows: `1320`
- static_flow_shield_old_harmful_vs_static_count: `20`
- static_flow_shield_solution_quality_harmful_count: `0`
- static_flow_shield_no_solution_or_nonfinite_count: `23`
- contexts_with_no_solution_or_nonfinite: `35`
- finite_number_inf_conversion_created_static_harm_labels: `True`

The old G5.19 harmful label used `finite_number(..., math.inf)` and then compared the result to the margin. That made no-solution/nonfinite static rows look like solution-quality harm. G5.20 keeps total risk visible, but it reports `solution_quality_harmful_vs_static`, `no_solution_or_infeasible`, and `budget_missing_or_nonfinite` separately.

Metric shifts: `[{'policy': 'static_flow_shield', 'old_harmful_vs_static_rate': '0.3333333333333333', 'old_false_positive_count': '20', 'corrected_solution_quality_harmful_rate': 0.0, 'corrected_no_solution_rate': 0.38333333333333336, 'corrected_total_harmful_rate': 0.38333333333333336, 'corrected_false_positive_count': 23, 'corrected_mean_solution_quality_delta_vs_static': 0.0}, {'policy': 'no_new_candidate_ablation', 'old_harmful_vs_static_rate': '0.3333333333333333', 'old_false_positive_count': '20', 'corrected_solution_quality_harmful_rate': 0.0, 'corrected_no_solution_rate': 0.38333333333333336, 'corrected_total_harmful_rate': 0.38333333333333336, 'corrected_false_positive_count': 23, 'corrected_mean_solution_quality_delta_vs_static': -0.00046251217149999996}, {'policy': 'old14_only_ranker', 'old_harmful_vs_static_rate': '0.3333333333333333', 'old_false_positive_count': '20', 'corrected_solution_quality_harmful_rate': 0.0, 'corrected_no_solution_rate': 0.38333333333333336, 'corrected_total_harmful_rate': 0.38333333333333336, 'corrected_false_positive_count': 23, 'corrected_mean_solution_quality_delta_vs_static': -0.00046251217149999996}]`

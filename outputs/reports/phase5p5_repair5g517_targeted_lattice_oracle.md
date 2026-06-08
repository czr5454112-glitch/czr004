# Phase5.5 Repair5G.5.17 Targeted Lattice Oracle

- decision: `targeted_repair_lattice_no_oracle_gain_continue_lattice_design`
- context_budget_pairs: `40`
- complete_context_budget_pairs: `40`
- old_candidate_count: `14`
- new_candidate_count: `24`
- repair_candidate_count: `10`
- new_repair_candidate_win_count: `0`
- mean_new_oracle_gap_vs_old_oracle: `0.0`
- harmful_false_positive_target_contexts_improved: `0`
- static_boundary_contexts_no_worse_reported: `False`
- additive_weak_context_budget_rows: `36`
- gates: `{'targeted_probe_integrity_passed': True, 'new_repair_candidate_win_count_gt_0': False, 'mean_new_oracle_gap_vs_old_oracle_lt_0': False, 'harmful_false_positive_target_contexts_improved_gt_0': False, 'static_boundary_contexts_no_worse_reported': False, 'additive_remains_weak_reported': True, 'candidate_recognized_all': True, 'complete_context_budget_pairs_eq_40': True, 'observed_ids_only': True, 'ids_166_205_untouched': True}`

Negative `mean_new_oracle_gap_vs_old_oracle` means the 24-candidate oracle improved over the old 14-candidate oracle. If this gate does not pass, G5.17 stops at lattice design rather than training a learned policy on unsupported candidate-space evidence.

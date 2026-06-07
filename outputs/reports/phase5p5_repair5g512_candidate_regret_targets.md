# Phase5.5 Repair5G.5.12 Candidate Regret Target Analysis

- decision: `candidate_regret_targets_passed_continue_feature_v3`
- candidate_level_rows: `840`
- contexts: `60`
- candidates: `14`
- label_counts: `{'additive_bad_baseline': 60, 'c_only_ablation_candidate': 60, 'harmful_parameter_candidate': 266, 'helpful_parameter_candidate': 193, 'neutral_parameter_candidate': 141, 'static_fallback_candidate': 120}`
- split_counts: `{'dev': 420, 'train': 420}`
- static_alias_duplicate_contexts: `60`
- gates: `{'candidate_level_rows_ge_840': True, 'contexts_eq_60': True, 'candidates_eq_14': True, 'helpful_count_gt_0': True, 'harmful_count_gt_0': True, 'neutral_or_static_count_gt_0': True, 'additive_bad_count_gt_0': True, 'static_alias_duplicate_contexts_reported': True, 'observed_ids_only': True, 'ids_166_205_untouched': True}`

## Best Mean-Delta Candidates

- `repair5g59_slow_decay_high_shield`: mean_delta_vs_static=-0.008626, mean_rank=5.017, oracle_wins=23
- `repair5g59_wait_conservative`: mean_delta_vs_static=-0.004243, mean_rank=5.650, oracle_wins=7
- `repair5g59_block_heavy_flow_guard`: mean_delta_vs_static=-0.002689, mean_rank=5.217, oracle_wins=6
- `repair5g59_high_beta_cap_safe`: mean_delta_vs_static=-0.000353, mean_rank=5.683, oracle_wins=5
- `repair5g59_flow_decay`: mean_delta_vs_static=0.000000, mean_rank=4.900, oracle_wins=5

The candidate-level table exposes helpful and harmful hard negatives inside the same context. This is the training signal that the G5.11 context-level oracle-class target compressed away.

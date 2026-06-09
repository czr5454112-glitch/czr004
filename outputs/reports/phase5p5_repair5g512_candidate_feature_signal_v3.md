# Phase5.5 Repair5G.5.12 Candidate Feature Signal v3

- decision: `feature_v3_passed_continue_candidate_ranker`
- rows: `840`
- contexts: `60`
- candidates: `14`
- feature_count: `42`
- forbidden_feature_count: `0`
- split_counts: `{'dev': 420, 'train': 420}`
- feature_signal_limited: `true`
- missing_runtime_context_features_reported: `true`
- gates: `{'perf_safe_candidate_rows_ge_840': True, 'forbidden_feature_count_eq_0': True, 'candidate_param_features_present': True, 'interaction_features_present': True, 'train_dev_split_seed_based': True, 'grouped_context_ids_preserved': True}`

## Top Absolute Correlations

- `feature_candidate_alpha_flow_progress`: corr=-0.5305
- `feature_candidate_is_goal_aware_dual_channel`: corr=-0.5138
- `feature_candidate_max_flow_shield`: corr=-0.5051
- `feature_candidate_flow_shield_beta`: corr=-0.4767
- `feature_interaction_agents_x_max_flow_shield`: corr=-0.3840
- `feature_interaction_agents_x_alpha_flow_progress`: corr=-0.3827
- `feature_candidate_is_c_only_f_disabled`: corr=0.3751
- `feature_interaction_agents_x_flow_shield_beta`: corr=-0.3688
- `feature_interaction_trace_per_agent_x_max_flow_shield`: corr=-0.3561
- `feature_interaction_trace_per_agent_x_flow_shield_beta`: corr=-0.3406
- `feature_candidate_is_additive_fallback`: corr=0.3230
- `feature_interaction_trace_events_x_max_flow_shield`: corr=-0.2963

These correlations are diagnostics only. The performance-safe feature set remains leakage-clean, but context signal is limited because rich pre-choice trace aggregates are not present in the tracked G5.11 artifacts.

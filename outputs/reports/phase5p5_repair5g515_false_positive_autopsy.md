# Phase5.5 Repair5G.5.15 False-Positive Autopsy

- decision: `false_positive_autopsy_completed_continue_safety_update`
- harmful_targets_confirmed: `2`
- primary_policy_name: `pairwise_context_ranker`
- runtime_claim_allowed: `false`

### maze-32-32-4|a50|s151

- selected_candidate: `repair5g59_slow_decay_high_shield`
- oracle_candidate: `repair5g59_wait_aggressive`
- static_score_primary: `1.13839056894`
- selected_score_primary: `1.17426960533`
- oracle_score_primary: `1.13172731932`
- actual_mean_delta_vs_static: `0.03587903639`
- g514_predicted_risk: `0.05718298442787295`
- g514_predicted_margin: `0.012734875881538998`
- g515_primary_policy: `pairwise_context_ranker`
- g515_selected_candidate: `repair5g59_static_flow_shield`
- g515_predicted_risk: `0.1458061882433751`
- g515_predicted_margin: `0.015344219100426382`
- rich_features: `{'feature_rich_blocked_per_committed': '0.088', 'feature_rich_blocked_per_agent': '8.36', 'feature_rich_wait_per_committed': '0.039789473684', 'feature_rich_wait_event_count': '189.0', 'feature_rich_progress_ratio': '0.484842105263', 'feature_rich_c_flow_update_ratio': '0.0', 'feature_rich_cost_span': '0.0', 'feature_rich_cost_max': '2.0'}`
- risk_underprediction_reason: `selected candidate was actually harmful while predicted risk stayed below the gate threshold`
- gate_that_should_have_abstained: `harmful_risk_upper_bound_or_context_uncertainty_gate`

### random-32-32-20|a50|s151

- selected_candidate: `repair5g59_slow_decay_high_shield`
- oracle_candidate: `repair5g59_commit_heavy_flow_guard`
- static_score_primary: `1.15621788284`
- selected_score_primary: `1.16855087359`
- oracle_score_primary: `1.13771839671`
- actual_mean_delta_vs_static: `0.01233299075`
- g514_predicted_risk: `0.01907132272283718`
- g514_predicted_margin: `0.014152686926250456`
- g515_primary_policy: `pairwise_context_ranker`
- g515_selected_candidate: `repair5g59_slow_decay_high_shield`
- g515_predicted_risk: `0.0`
- g515_predicted_margin: `0.016681768482697423`
- rich_features: `{'feature_rich_blocked_per_committed': '0.105238095238', 'feature_rich_blocked_per_agent': '4.42', 'feature_rich_wait_per_committed': '0.051428571429', 'feature_rich_wait_event_count': '108.0', 'feature_rich_progress_ratio': '0.55', 'feature_rich_c_flow_update_ratio': '0.0', 'feature_rich_cost_span': '0.0', 'feature_rich_cost_max': '2.0'}`
- risk_underprediction_reason: `selected candidate was actually harmful while predicted risk stayed below the gate threshold`
- gate_that_should_have_abstained: `harmful_risk_upper_bound_or_context_uncertainty_gate`

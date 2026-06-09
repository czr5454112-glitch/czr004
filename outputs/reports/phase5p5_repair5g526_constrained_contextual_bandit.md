# Repair5G.5.26 Constrained Contextual Bandit

- schema_version: `phase5p5_repair5g526_constrained_contextual_bandit_summary_v1`
- decision: `constrained_contextual_bandit_evaluated`
- policies_present: `['conservative_policy_improvement_over_g525_best', 'epsilon_constrained_utility_maximization', 'lagrangian_ridge_policy', 'random_action_control', 'risk_constrained_contextual_bandit', 'shuffled_reward_control', 'topk_action_set_restricted_policy']`
- candidate_budget_rows: `5280`
- context_budget_decision_rows: `840`
- bootstrap_rows: `2100`
- best_policy: `conservative_policy_improvement_over_g525_best`
- best_policy_summary: `{'row_type': 'model_aggregate', 'model': 'conservative_policy_improvement_over_g525_best', 'policy': 'conservative_policy_improvement_over_g525_best', 'eval_scope': 'seed_oof', 'fold_id': 'all', 'context_budget_pairs': 120, 'top1_safe_oracle_capture_rate': 0.06666666666666667, 'top3_safe_oracle_capture_rate': 0.15833333333333333, 'top5_safe_oracle_capture_rate': 0.225, 'region_top1_capture_rate': 0.38333333333333336, 'region_top2_capture_rate': 0.38333333333333336, 'selected_policy_utility': -0.011588397798488371, 'safe_policy_sim_utility': -0.011588397798488371, 'candidate_induced_no_solution_count': 0, 'budget_sensitive_failure_count': 9, 'static_recovery_capture_count': 8, 'fallback_rate': 0.3416666666666667, 'safe_positive_selected_count': 41, 'avoidable_risk_ece': 0.03463409509130652, 'phase5p5_allowed': False, 'phase6_allowed': False, 'runtime_claim_allowed': False, 'learned_runtime_policy_validated': False, 'aaai_ready': False}`
- constraints: `{'candidate_induced_no_solution_count_le_baseline': 6, 'budget_sensitive_failure_count_reported': True, 'fallback_allowed': True}`
- main_gates: `{'candidate_induced_no_solution_count_le_g525': True, 'selected_policy_utility_beats_g525_best': True, 'controls_do_not_match': True, 'fallback_allowed': True}`
- offline_direct_counterfactual_lookup: `True`
- phase5p5_allowed: `False`
- phase6_allowed: `False`
- runtime_claim_allowed: `False`
- learned_runtime_policy_validated: `False`
- aaai_ready: `False`

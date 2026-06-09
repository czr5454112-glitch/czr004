# Repair5G.5.27 Decision Arbitration Audit

- schema_version: `phase5p5_repair5g527_decision_arbitration_audit_summary_v1`
- decision: `metric_alignment_verified_continue_teacher_audit`
- why_bandit_not_final_best_policy: `G5.26 final best_policy was chosen from the runtime-safe top-k policy suite; the bandit suite used direct counterfactual lookup and was only a teacher candidate.`
- g526_final_decision: `g526_full_coverage_rank_effect_not_confirmed_return_trace_design`
- g526_topk_best_policy: `agent_density_specialist_baseline`
- g526_bandit_best_policy: `conservative_policy_improvement_over_g525_best`
- selected_policy_utility_lower_is_better: `True`
- bandit_uses_oracle_counterfactual_at_selection_time: `True`
- bandit_result_correctly_conservative_not_runtime_safe: `True`
- final_offline_policy_value_metrics: `['selected_policy_utility', 'candidate_induced_no_solution_count', 'budget_sensitive_failure_count', 'fallback_rate', 'static_recovery_capture_count', 'calibration', 'safe_oracle_topk_capture_as_recall_only']`
- correct_g527_primary_gate: `distilled_runtime_safe_policy_value_with_zero_or_teacher_no_solution_and_heldout_controls`
- g526_bandit_best_policy_summary: `{'aaai_ready': False, 'avoidable_risk_ece': 0.03463409509130652, 'budget_sensitive_failure_count': 9, 'candidate_induced_no_solution_count': 0, 'context_budget_pairs': 120, 'eval_scope': 'seed_oof', 'fallback_rate': 0.3416666666666667, 'fold_id': 'all', 'learned_runtime_policy_validated': False, 'model': 'conservative_policy_improvement_over_g525_best', 'phase5p5_allowed': False, 'phase6_allowed': False, 'policy': 'conservative_policy_improvement_over_g525_best', 'region_top1_capture_rate': 0.38333333333333336, 'region_top2_capture_rate': 0.38333333333333336, 'row_type': 'model_aggregate', 'runtime_claim_allowed': False, 'safe_policy_sim_utility': -0.011588397798488371, 'safe_positive_selected_count': 41, 'selected_policy_utility': -0.011588397798488371, 'static_recovery_capture_count': 8, 'top1_safe_oracle_capture_rate': 0.06666666666666667, 'top3_safe_oracle_capture_rate': 0.15833333333333333, 'top5_safe_oracle_capture_rate': 0.225}`
- blocker: `False`
- phase5p5_allowed: `False`
- phase6_allowed: `False`
- runtime_claim_allowed: `False`
- learned_runtime_policy_validated: `False`
- aaai_ready: `False`

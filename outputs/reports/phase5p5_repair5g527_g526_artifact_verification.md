# Repair5G.5.27 G5.26 Artifact Verification

- schema_version: `phase5p5_repair5g527_g526_artifact_verification_summary_v1`
- decision: `g526_artifacts_verified_continue_g527`
- gates: `{'g526_decision_expected': True, 'trace_context_budget_pairs_eq_120': True, 'trace_candidate_budget_rows_eq_5280': True, 'trace_raw_sha_verified': True, 'feature_forbidden_count_eq_0': True, 'topk_top3_gate_failed': True, 'topk_region_top2_gate_failed': True, 'topk_controls_gate_failed': True, 'topk_heldout_family_gate_failed': True, 'bandit_best_policy_expected': True, 'bandit_utility_beats_g525_best': True, 'bandit_candidate_induced_zero': True, 'bandit_fallback_allowed': True, 'bandit_controls_do_not_match': True, 'neural_diagnostic_not_positive': True, 'edge_update_residual_proxy_only': True, 'external_lacam2_untouched': True, 'ids_166_205_untouched': True, 'claims_closed': True, 'worklog_entry_before_optional_probe': True, 'teacher_rows_eq_5280': True}`
- g526_decision: `g526_full_coverage_rank_effect_not_confirmed_return_trace_design`
- g526_best_topk_policy: `agent_density_specialist_baseline`
- g526_best_bandit_policy: `conservative_policy_improvement_over_g525_best`
- g526_bandit_best_policy_summary: `{'aaai_ready': False, 'avoidable_risk_ece': 0.03463409509130652, 'budget_sensitive_failure_count': 9, 'candidate_induced_no_solution_count': 0, 'context_budget_pairs': 120, 'eval_scope': 'seed_oof', 'fallback_rate': 0.3416666666666667, 'fold_id': 'all', 'learned_runtime_policy_validated': False, 'model': 'conservative_policy_improvement_over_g525_best', 'phase5p5_allowed': False, 'phase6_allowed': False, 'policy': 'conservative_policy_improvement_over_g525_best', 'region_top1_capture_rate': 0.38333333333333336, 'region_top2_capture_rate': 0.38333333333333336, 'row_type': 'model_aggregate', 'runtime_claim_allowed': False, 'safe_policy_sim_utility': -0.011588397798488371, 'safe_positive_selected_count': 41, 'selected_policy_utility': -0.011588397798488371, 'static_recovery_capture_count': 8, 'top1_safe_oracle_capture_rate': 0.06666666666666667, 'top3_safe_oracle_capture_rate': 0.15833333333333333, 'top5_safe_oracle_capture_rate': 0.225}`
- external_lacam2_solver_status: ``
- phase5p5_allowed: `False`
- phase6_allowed: `False`
- runtime_claim_allowed: `False`
- learned_runtime_policy_validated: `False`
- aaai_ready: `False`

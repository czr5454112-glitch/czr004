# Repair5G.5.26 Policy Gap and Trace Needs

- schema_version: `phase5p5_repair5g526_policy_gap_and_trace_needs_summary_v1`
- decision: `policy_gap_and_trace_needs_analyzed`
- best_policy: `agent_density_specialist_baseline`
- best_policy_summary: `{'aaai_ready': False, 'avoidable_risk_ece': 0.013806886487239711, 'budget_sensitive_failure_count': 6, 'candidate_induced_no_solution_count': 6, 'context_budget_pairs': 120, 'eval_scope': 'seed_oof', 'fallback_rate': 0.0, 'fold_id': 'all', 'learned_runtime_policy_validated': False, 'model': 'agent_density_specialist_baseline', 'phase5p5_allowed': False, 'phase6_allowed': False, 'policy': 'agent_density_specialist_baseline', 'region_top1_capture_rate': 0.0, 'region_top2_capture_rate': 0.1, 'row_type': 'model_aggregate', 'runtime_claim_allowed': False, 'safe_policy_sim_utility': 0.036406463637500004, 'safe_positive_selected_count': 5, 'selected_policy_utility': 0.036406463637500004, 'static_recovery_capture_count': 3, 'top1_safe_oracle_capture_rate': 0.0, 'top3_safe_oracle_capture_rate': 0.0, 'top5_safe_oracle_capture_rate': 0.05}`
- topk_policy_gates: `{'avoidable_risk_ece_le_g525': True, 'candidate_induced_no_solution_count_le_g525': True, 'controls_do_not_match': False, 'forbidden_feature_count_eq_0': True, 'leave_one_map_family_does_not_collapse': False, 'region_top2_capture_rate_ge_0p50': False, 'selected_policy_utility_beats_g525_best': False, 'top3_safe_oracle_capture_rate_ge_0p25': False}`
- ranker_good_selector_blocked: `False`
- fallback_dominated_best_policy: `False`
- neural_best_model: `mlp_region_then_candidate`
- bandit_best_policy: `conservative_policy_improvement_over_g525_best`
- edge_update_teacher_proxy_only: `True`
- failure_context_budget_pairs: `120`
- trace_needs: `[{'priority': 1, 'trace_need': 'exact_priority_block_subreason', 'status': 'explicitly_unavailable', 'why': 'Risk calibration still cannot separate priority-block subcauses.', 'phase5p5_allowed': False, 'phase6_allowed': False, 'runtime_claim_allowed': False, 'learned_runtime_policy_validated': False, 'aaai_ready': False}, {'priority': 2, 'trace_need': 'all_failed_candidate_reasons_when_pibt_returns_false', 'status': 'explicitly_unavailable', 'why': 'Top-k selector needs failed-action distribution without adding UpdateLTM events.', 'phase5p5_allowed': False, 'phase6_allowed': False, 'runtime_claim_allowed': False, 'learned_runtime_policy_validated': False, 'aaai_ready': False}, {'priority': 3, 'trace_need': 'exact_counterfactual_edge_labels', 'status': 'proxy_only', 'why': 'Goal-aware update residuals remain diagnostic-only when exact labels are absent.', 'phase5p5_allowed': False, 'phase6_allowed': False, 'runtime_claim_allowed': False, 'learned_runtime_policy_validated': False, 'aaai_ready': False}]`
- phase5p5_allowed: `False`
- phase6_allowed: `False`
- runtime_claim_allowed: `False`
- learned_runtime_policy_validated: `False`
- aaai_ready: `False`

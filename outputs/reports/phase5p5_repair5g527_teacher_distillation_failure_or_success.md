# Repair5G.5.27 Teacher Distillation Failure Or Success

- schema_version: `phase5p5_repair5g527_teacher_distillation_failure_or_success_summary_v1`
- decision: `teacher_distillation_synthesis_completed`
- decision_hint: `g527_bandit_teacher_valid_but_distillation_blocked_need_exact_failure_audit`
- answers: `{'conservative_bandit_teacher_valid_non_leaky': True, 'can_be_distilled_into_runtime_safe_features': False, 'distilled_policy_beats_g525_by_lookup': False, 'keeps_candidate_induced_no_solution_at_teacher': False, 'generalizes_to_heldout_map_families': False, 'remains_safe_on_warehouse': False, 'calibration_improves': False, 'exact_failure_audit_logging_still_needed': True, 'next_step': 'exact_failure_audit_or_more_trace_logging'}`
- positive_decision_gates: `{'bandit_teacher_valid_non_leaky_as_teacher': True, 'distilled_policy_uses_runtime_safe_features_only': True, 'selected_policy_utility_lt_g525_best': False, 'candidate_induced_no_solution_count_le_teacher': False, 'safe_positive_selected_count_ge_25': False, 'heldout_family_no_collapse': False, 'controls_do_not_match': False, 'forbidden_feature_count_eq_0': True, 'claims_remain_closed': True}`
- counterfactual_policy_exists_runtime_safe_features_still_insufficient: `True`
- phase5p5_allowed: `False`
- phase6_allowed: `False`
- runtime_claim_allowed: `False`
- learned_runtime_policy_validated: `False`
- aaai_ready: `False`

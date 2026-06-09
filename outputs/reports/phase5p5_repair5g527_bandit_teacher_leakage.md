# Repair5G.5.27 Bandit Teacher Leakage Audit

- schema_version: `phase5p5_repair5g527_bandit_teacher_leakage_summary_v1`
- decision: `bandit_valid_teacher_not_runtime_policy_continue_distillation`
- bandit_is_valid_teacher: `True`
- bandit_is_runtime_policy: `False`
- distillation_allowed: `True`
- bandit_chooses_actions_using_measured_context_budget_candidate_outcomes: `True`
- directly_uses_target_score_delta_oracle_or_risk_labels: `True`
- selection_time_label_classes: `{'counterfactual_outcome': 2, 'oracle_label': 5}`
- supervised_labels_distillable: `['target_bandit_selected_candidate', 'target_bandit_selected_region', 'target_bandit_action_class', 'target_bandit_should_fallback_static', 'target_bandit_selected_policy_utility_bucket']`
- field_audit_rows: `191`
- phase5p5_allowed: `False`
- phase6_allowed: `False`
- runtime_claim_allowed: `False`
- learned_runtime_policy_validated: `False`
- aaai_ready: `False`

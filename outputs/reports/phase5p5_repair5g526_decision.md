# Repair5G.5.26 Final Decision

- decision: `g526_full_coverage_rank_effect_not_confirmed_return_trace_design`
- best_policy: `agent_density_specialist_baseline`
- best_policy_summary: `{'aaai_ready': False, 'avoidable_risk_ece': 0.013806886487239711, 'budget_sensitive_failure_count': 6, 'candidate_induced_no_solution_count': 6, 'context_budget_pairs': 120, 'eval_scope': 'seed_oof', 'fallback_rate': 0.0, 'fold_id': 'all', 'learned_runtime_policy_validated': False, 'model': 'agent_density_specialist_baseline', 'phase5p5_allowed': False, 'phase6_allowed': False, 'policy': 'agent_density_specialist_baseline', 'region_top1_capture_rate': 0.0, 'region_top2_capture_rate': 0.1, 'row_type': 'model_aggregate', 'runtime_claim_allowed': False, 'safe_policy_sim_utility': 0.036406463637500004, 'safe_positive_selected_count': 5, 'selected_policy_utility': 0.036406463637500004, 'static_recovery_capture_count': 3, 'top1_safe_oracle_capture_rate': 0.0, 'top3_safe_oracle_capture_rate': 0.0, 'top5_safe_oracle_capture_rate': 0.05}`
- positive_learning_gates: `{'full_coverage_context_budget_pairs_eq_120': True, 'candidate_budget_rows_ge_3600': True, 'raw_log_sha256_verified': True, 'forbidden_feature_count_eq_0': True, 'top3_safe_oracle_capture_rate_ge_0p25': False, 'selected_policy_utility_beats_g525_best': False, 'candidate_induced_no_solution_count_le_g525': True, 'region_top2_capture_rate_ge_0p50': False, 'controls_do_not_match': False, 'leave_one_map_family_does_not_collapse': False, 'claims_remain_closed': True}`
- edge_update_teacher_proxy_only: `True`
- next_step: `policy_gap_and_trace_needs_analyzed`

Closed claims remain:

```text
phase5p5_allowed=false
phase6_allowed=false
runtime_claim_allowed=false
learned_runtime_policy_validated=false
aaai_ready=false
```

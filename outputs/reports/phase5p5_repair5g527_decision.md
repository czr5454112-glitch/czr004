# Repair5G.5.27 Final Decision

- decision: `g527_bandit_teacher_valid_but_distillation_blocked_need_exact_failure_audit`
- best_distilled_model: `bandit_teacher_candidate_ranker`
- best_calibrated_policy: `old14_g518_fallback_selector`
- best_offline_rl_method: `direct_conservative_policy_improvement_teacher`
- bandit_teacher_valid_non_leaky_as_teacher: `True`
- distilled_policy_uses_runtime_safe_features_only: `True`
- next_step: `exact_failure_audit_or_more_trace_logging`

Closed claims remain:

```text
phase5p5_allowed=false
phase6_allowed=false
runtime_claim_allowed=false
learned_runtime_policy_validated=false
aaai_ready=false
```

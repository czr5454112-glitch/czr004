# Repair5G.5.23 G5.22 Signal Contradiction

G5.22 had a valid candidate-space oracle signal, but the learnable package was non-promotable.

- candidate_space_oracle_gain: `-0.020237024125000037`
- safe_g522_win_contexts: `19`
- safe_g522_win_budget_pairs: `38`
- surrogate_top3_capture: `0.0`
- safe_policy_sim_utility_beats_baseline: `False`
- teacher_forbidden_feature_count: `8`
- surrogate_forbidden_feature_count: `4`
- missing_full_primary_contexts: `39`
- hard_blocker_non_promotable_teacher_or_surrogate: `True`

The leaked `feature_*` fields are renamed to target/audit/outcome/oracle namespaces in G5.23.

# Phase5.5 Repair5G.5.9 Abstention-Aware Offline Policy Train

- decision: `abstention_aware_policy_trained_requires_eval`
- train_rows: `30`
- head_a_classes: `["longer_budget_needed", "no_solution_abstain", "static_fallback", "trainable_expert_selection"]`
- head_b_train_rows: `20`
- head_b_classes: `["repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75", "repair5g2_best_frozen_static_candidate"]`

Head A trains feasibility/abstention routing; Head B trains expert selection only on stable eligible contexts.

# Phase5.5 Repair5G.5.15 Final Interpretation

- conclusion: `G5.15 is not a direction failure; it shows the interaction ranker is safe-ish but not stronger than reproduced v4 under strict risk-adjusted utility.`
- decision: `interaction_ranker_no_better_than_v4_continue_feature_design`
- primary_policy_name: `pairwise_context_ranker`
- mean_delta_vs_static: `-0.009366233488`
- harmful_vs_static_rate: `0.03333333333333333`
- coverage: `0.23333333333333334`
- risk_adjusted_utility_lambda_0p10: `-0.006032900154666666`
- missed_helpful_contexts: `39`
- harmful_false_positive_contexts: `2`
- high_uncertainty_contexts: `37`
- interpretation: `The rich-by-candidate interaction matrix and pairwise ranker reduced harmful false positives, but the policy still fails to convert enough oracle gap into safe opportunity capture. The next local round should focus on error-bank augmentation, targeted lattice repair, and pessimistic safety bounds rather than runtime export.`
- phase5p5_allowed: `false`
- phase6_allowed: `false`
- aaai_ready: `false`
- runtime_claim_allowed: `false`
- learned_runtime_policy_validated: `false`

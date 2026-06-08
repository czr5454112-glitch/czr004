# Phase5.5 Repair5G.5.19 Decision

- decision: `ranker_ignores_new_candidates_continue_candidate_policy_design`
- best_policy: `no_new_candidate_ablation`
- best_mean_delta_vs_static: `-0.000462512171`
- best_mean_delta_vs_additive: `-0.100924657693`
- best_harmful_vs_static_rate: `0.333333333333`
- best_new_candidate_selection_count: `0`
- local_pc_sufficient: `true`
- second_wave_lattice_run: `false`

## Required Answers

1. Did G5.18 candidate-space positive evidence survive target reconstruction?
   `True`. Target reconstruction produced `1320` candidate rows and `32` new-candidate winning budget pairs.

2. Which new candidates are useful by mean, oracle wins, and risk?
   Mean: `repair5g518_grid_c0p90_b1p50_f1p00_w0p45_dc0p95_df1p00_beta0p45_max0p75_c0`. Oracle wins: `repair5g518_grid_c1p25_b1p25_f1p00_w0p50_dc0p95_df1p00_beta0p35_max0p75_c0`. Risk-adjusted: `repair5g518_grid_c0p90_b1p50_f1p00_w0p45_dc0p95_df1p00_beta0p45_max0p75_c0`. Low harmful rate: `repair5g518_grid_c0p90_b1p50_f1p00_w0p45_dc0p95_df1p00_beta0p45_max0p75_c0`.

3. Can a runtime-safe offline ranker select the 22-candidate lattice safely?
   Current diagnostic decision: `ranker_ignores_new_candidates_continue_candidate_policy_design`. The best policy hard gates are `{'beats_best_single_train_candidate_0p10_or_reports_fixed_better': True, 'beats_no_new_candidate_ablation_0p10': False, 'beats_old14_only_ranker_0p10': False, 'beats_train_only_map_agent_prior_0p10': True, 'false_positive_count_le_static_baseline': True, 'harmful_vs_static_rate_le_0p05': False, 'harmful_vs_static_rate_prefer_le_0p0333333333': False, 'mean_delta_vs_additive_lt_0': True, 'mean_delta_vs_static_lt_0': True, 'new_candidate_selection_harmful_rate_le_0p05': True, 'new_candidate_selection_helpful_count_gt_0': False, 'oracle_new22_regret_lt_old14_only_regret': False, 'rau_0p05_improves_over_reproduced': True, 'rau_0p10_improves_over_reproduced': True, 'selects_at_least_one_new_candidate_oof': False}`.

4. Does the ranker use new candidates or fall back to old14/static?
   Best policy new-candidate selections: `0`, helpful: `0`, harmful: `0`.

5. Does it beat G5.15/G5.18 reproduced baselines and train-only priors?
   RAU baseline gates: 0.05=`True`, 0.10=`True`; train-prior gate=`True`.

6. What remains before runtime/Phase5.5?
   Runtime integration, Phase5.5, Phase6, learned runtime policy validation, and AAAI claims remain closed. A future round must either improve candidate-policy safety/calibration or use the autopsy to design a sparse second-wave lattice.

7. Is local PC still sufficient?
   `true`. G5.19 used offline tables and local deterministic Python diagnostics; no solver continuation was required.

## Claim Boundaries

- phase5p5_allowed: `False`
- phase6_allowed: `False`
- runtime_claim_allowed: `False`
- learned_runtime_policy_validated: `False`
- aaai_ready: `False`

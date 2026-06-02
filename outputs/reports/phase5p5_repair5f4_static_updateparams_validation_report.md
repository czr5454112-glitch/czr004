# Phase5.5 Repair5F.4 Static UpdateParams Larger Validation

Diagnostic-only. Phase5.5 and Phase6 remain forbidden.

## Scope

- maps: `['random-32-32-20', 'maze-32-32-4', 'warehouse-10-20-10-2-1']`
- agent_counts: `[50, 100]`
- instance_ids: `[26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45]`
- time_limit_sec: `3.0`
- ltm_max_iterations: `4`
- scenario_dir: `outputs\tmp\phase5p5_repair5f4_static_updateparams_validation_scenarios`

## Method Summary

| method | rows | better | equal | worse | mean delta | 95% CI | selected candidates |
|---|---:|---:|---:|---:|---:|---|---|
| `always_additive_defer` | 120 | 0 | 120 | 0 | 0.0 | `[0.0, 0.0]` | `{'additive_ltm': 120}` |
| `repair5f_candidate_additive_ltm` | 120 | 0 | 120 | 0 | 0.0 | `[0.0, 0.0]` | `{'additive_ltm': 120}` |
| `repair5f_bounded_updateparam_selector_force_additive_parity` | 120 | 0 | 120 | 0 | 0.0 | `[0.0, 0.0]` | `{'additive_ltm': 120}` |
| `laur_disable` | 120 | 0 | 120 | 0 | 0.0 | `[0.0, 0.0]` | `{'additive_ltm': 120}` |
| `laur_force_additive_direct` | 120 | 0 | 120 | 0 | 0.0 | `[0.0, 0.0]` | `{'additive_ltm': 120}` |
| `repair5f_bounded_updateparam_selector_runtime` | 120 | 25 | 68 | 27 | 4.51908770666587e-05 | `[-0.0025560447310666867, 0.0028071292053666623]` | `{'c100_b100_w075_d090': 120}` |
| `repair5f_static_c100_b100_w075_d090` | 120 | 25 | 68 | 27 | 4.51908770666587e-05 | `[-0.0025432106323166875, 0.002837331297599984]` | `{'c100_b100_w075_d090': 120}` |
| `repair5f_static_c100_b100_w075_d100` | 120 | 25 | 72 | 23 | -0.0008398811590833434 | `[-0.003726480852241675, 0.0019252080707499915]` | `{'c100_b100_w075_d100': 120}` |
| `repair5f_static_c100_b100_w100_d090` | 120 | 23 | 74 | 23 | -0.0003064312557916717 | `[-0.002416714180141673, 0.0017771325306166707]` | `{'c100_b100_w100_d090': 120}` |
| `repair5f_static_c100_b100_w100_d095` | 120 | 25 | 74 | 21 | 0.00012301019519166494 | `[-0.0016732348852583317, 0.0019957017529083306]` | `{'c100_b100_w100_d095': 120}` |
| `repair5f_static_c100_b100_w075_d095` | 120 | 22 | 76 | 22 | -0.0008186365335416705 | `[-0.0032230211399333353, 0.0015721887182416608]` | `{'c100_b100_w075_d095': 120}` |
| `repair5f_f4_deterministic_random_candidate_diagnostic` | 120 | 22 | 71 | 27 | -0.0007488671398916735 | `[-0.002941564295233338, 0.001404379896158329]` | `{'additive_ltm': 1, 'c050_b100_w100_d100': 1, 'c075_b075_w125_d095': 1, 'c075_b100_w075_d100': 2, 'c075_b100_w100_d090': 2, 'c075_b100_w100_d095': 2, 'c075_b100_w100_d100': 1, 'c075_b100_w125_d090': 3, 'c075_b100_w125_d100': 2, 'c075_b125_w100_d090': 5, 'c075_b125_w100_d100': 3, 'c075_b125_w125_d095': 5, 'c100_b050_w100_d100': 3, 'c100_b075_w075_d100': 4, 'c100_b075_w100_d090': 3, 'c100_b075_w100_d095': 2, 'c100_b075_w100_d100': 3, 'c100_b075_w125_d090': 4, 'c100_b075_w125_d100': 6, 'c100_b100_w050_d100': 3, 'c100_b100_w075_d090': 2, 'c100_b100_w075_d100': 4, 'c100_b100_w100_d090': 3, 'c100_b100_w100_d095': 4, 'c100_b100_w125_d095': 1, 'c100_b100_w125_d100': 4, 'c100_b100_w150_d100': 4, 'c100_b125_w075_d100': 3, 'c100_b125_w100_d090': 1, 'c100_b125_w100_d095': 3, 'c100_b125_w100_d100': 3, 'c100_b125_w125_d100': 2, 'c100_b150_w100_d100': 4, 'c125_b075_w100_d090': 4, 'c125_b075_w100_d100': 1, 'c125_b075_w125_d095': 3, 'c125_b100_w100_d090': 4, 'c125_b100_w100_d095': 4, 'c125_b100_w100_d100': 4, 'c125_b100_w125_d100': 1, 'c125_b125_w075_d095': 3, 'c125_b125_w100_d100': 2}` |
| `repair5e5_crossfold_utility_reranker` | 120 | 13 | 92 | 15 | 0.0004546577450916643 | `[-0.0009329245022416675, 0.0017554574755666668]` | `{'additive_ltm': 60, 'block_heavy': 47, 'wait_heavy': 13}` |
| `repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic` | 120 | 15 | 92 | 13 | -0.00044926312444166876 | `[-0.0017852650342083268, 0.0008214788864166581]` | `{'additive_ltm': 60, 'decay_095': 12, 'wait_light': 48}` |

## Main Static Rule

- locked candidate: `c100_b100_w075_d090`
- better / equal / worse: `25 / 68 / 27`
- mean_delta_ratio_vs_ltm: `4.51908770666587e-05`
- median_delta_ratio_vs_ltm: `0.0`
- bootstrap_95ci_mean_delta_ratio_vs_ltm: `[-0.0025432106323166875, 0.002837331297599984]`
- bootstrap_probability_mean_delta_lt_0: `0.5005`
- worst_group: `{'map': 'maze-32-32-4', 'agents': 100, 'rows': 20, 'mean_delta_ratio_vs_ltm': 0.0013037860594999674, 'better': 10, 'equal': 0, 'worse': 10}`

## Component Ablation

| ablation | mechanism | rows | full mean | ablation mean | full mean beats/ties |
|---|---|---:|---:|---:|---|
| `repair5f_static_c100_b100_w075_d100` | wait-spillover reduction only | 120 | 4.51908770666587e-05 | -0.0008398811590833434 | False |
| `repair5f_static_c100_b100_w100_d090` | decay 0.90 only | 120 | 4.51908770666587e-05 | -0.0003064312557916717 | False |
| `repair5f_static_c100_b100_w100_d095` | mild decay 0.95 only | 120 | 4.51908770666587e-05 | 0.00012301019519166494 | True |
| `repair5f_static_c100_b100_w075_d095` | wait reduction + mild decay | 120 | 4.51908770666587e-05 | -0.0008186365335416705 | False |

## Gates

- `full_expected_rows`: `True`
- `schema_errors_eq_0`: `True`
- `missing_rows_eq_0`: `True`
- `support_validation_overlap_count_eq_0`: `True`
- `f2f3_holdout_validation_overlap_count_eq_0`: `True`
- `force_additive_parity_exact`: `True`
- `exact_additive_candidate_parity_exact`: `True`
- `laur_disable_parity_exact`: `True`
- `laur_force_additive_direct_parity_exact`: `True`
- `selector_static_runtime_metrics_equal`: `True`
- `selector_selected_c100_b100_w075_d090_all_cases`: `True`
- `main_static_better_gt_worse`: `False`
- `main_static_mean_delta_ratio_vs_ltm_lt_0`: `False`
- `main_static_bootstrap_ci_upper_le_0`: `False`
- `main_static_ratio_worse_than_ltm_groups_le_1`: `False`
- `main_static_success_worse_than_ltm_groups_eq_0`: `True`
- `main_static_beats_deterministic_random_candidate_diagnostic`: `False`
- `phase5p5_allowed_false`: `True`
- `phase6_allowed_false`: `True`

## Interpretation

F4-A does not pass all mandatory gates. Treat the result as diagnostic only; do not promote or retune from F4 outcomes.

# Phase4F Repair5D Composite Grid

Date: 2026-05-31 13:18:26

This is no-retraining diagnostic evidence only. Phase5.5 and Phase6 remain forbidden.

## Top Modes

| rank | mode | samples | delta | regret | selected harmful | recall | precision | high-margin | defer/additive | score |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | rank_model_top5_safety_model_per_rule_utility_rerank | 762 | 0.008891 | 0.021851 | 0.005249 | 0.801068 | 0.300451 | 0.419355 | 0.291339 | 0.008008 |
| 2 | rank_model_top5_utility_regret_min_selected_harmful_constraint | 762 | 0.008891 | 0.021851 | 0.005249 | 0.801068 | 0.300451 | 0.419355 | 0.291339 | 0.008008 |
| 3 | rank_model_top5_safety_model_per_rule_utility_rerank | 762 | 0.008758 | 0.021748 | 0.007874 | 0.783712 | 0.289591 | 0.416129 | 0.286089 | 0.006482 |
| 4 | rank_model_top5_utility_regret_min_selected_harmful_constraint | 762 | 0.008758 | 0.021748 | 0.007874 | 0.783712 | 0.289591 | 0.416129 | 0.286089 | 0.006482 |
| 5 | rank_model_top5_safety_model_per_rule_utility_rerank | 762 | 0.008625 | 0.021810 | 0.006562 | 0.783712 | 0.289591 | 0.409677 | 0.325459 | 0.005964 |
| 6 | rank_model_top5_utility_regret_min_selected_harmful_constraint | 762 | 0.008625 | 0.021810 | 0.006562 | 0.783712 | 0.289591 | 0.409677 | 0.325459 | 0.005964 |
| 7 | rank_model_top5_safety_model_per_rule_utility_rerank | 762 | 0.007367 | 0.022286 | 0.007874 | 0.801068 | 0.300451 | 0.409677 | 0.334646 | 0.005566 |
| 8 | rank_model_top5_utility_regret_min_selected_harmful_constraint | 762 | 0.007367 | 0.022286 | 0.007874 | 0.801068 | 0.300451 | 0.409677 | 0.334646 | 0.005566 |
| 9 | rank_model_top3_safety_model_per_rule_utility_rerank | 762 | 0.009003 | 0.022927 | 0.007874 | 0.783712 | 0.289591 | 0.390323 | 0.334646 | 0.004257 |
| 10 | rank_model_top3_safety_model_per_rule_utility_rerank | 762 | 0.006642 | 0.022978 | 0.007874 | 0.801068 | 0.300451 | 0.400000 | 0.330709 | 0.003664 |
| 11 | rank_model_top3_safety_model_per_rule_utility_rerank | 762 | 0.007676 | 0.022791 | 0.007874 | 0.783712 | 0.289591 | 0.387097 | 0.330709 | 0.002905 |
| 12 | rank_model_top3_safety_model_per_rule_utility_rerank | 762 | 0.006506 | 0.023283 | 0.011811 | 0.801068 | 0.300451 | 0.393548 | 0.335958 | 0.002900 |
| 13 | rank_model_top3_anti_decision_margin_safety_model_per_family | 762 | 0.002113 | 0.028155 | 0.020997 | 0.814419 | 0.299754 | 0.303226 | 0.590551 | -0.020867 |
| 14 | rank_model_top3_learned_defer_penalty_per_rule_safety | 762 | 0.001513 | 0.028778 | 0.020997 | 0.801068 | 0.300451 | 0.264516 | 0.657480 | -0.024013 |
| 15 | rank_model_top3_learned_defer_penalty_per_rule_safety | 762 | 0.003951 | 0.028700 | 0.022310 | 0.783712 | 0.289591 | 0.258065 | 0.661417 | -0.036277 |
| 16 | rank_model_top3_anti_decision_margin_safety_model_per_family | 762 | 0.004557 | 0.028160 | 0.023622 | 0.797063 | 0.289104 | 0.306452 | 0.586614 | -0.045192 |
| 17 | rank_model_top3_anti_decision_margin_safety_model_per_family | 762 | 0.002276 | 0.028093 | 0.023622 | 0.814419 | 0.299754 | 0.316129 | 0.591864 | -0.046243 |
| 18 | rank_model_top3_learned_defer_penalty_per_rule_safety | 762 | 0.001672 | 0.028697 | 0.023622 | 0.801068 | 0.300451 | 0.270968 | 0.662730 | -0.049697 |
| 19 | rank_model_top3_safety_model_per_rule_utility_rerank | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | -0.055000 |
| 20 | rank_model_top3_safety_model_per_rule_utility_rerank | 0 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | -0.055000 |

## Interpretation

The ranking favors positive selected-vs-additive delta, low regret, high high-margin capture, and selected harmful rate at or below 0.01-0.02. This report does not lower the final safety gate.

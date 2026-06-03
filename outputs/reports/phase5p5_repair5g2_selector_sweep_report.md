# Phase5.5 Repair5G.2 Selector Sweep

Selector tuning used only support IDs 1..25 and development-validation IDs 26..45. It does not permit Phase5.5 or Phase6.

## Selected Dev Protocol

- `selector_type`: `map_agent_group_static_selector`
- `fold`: `train_1_25_validate_26_45`
- `rows`: `120`
- `better`: `65`
- `equal`: `45`
- `worse`: `10`
- `mean_delta_ratio_vs_ltm`: `-0.014155347174674999`
- `median_delta_ratio_vs_ltm`: `-0.005279456539499905`
- `bootstrap_probability_mean_delta_lt_0`: `1.0`
- `bootstrap_ci_low`: `-0.019766175396675002`
- `bootstrap_ci_high`: `-0.008207305995033325`
- `ratio_worse_than_ltm_groups`: `1`
- `success_worse_than_ltm_groups`: `0`

## Gates

- `selector_better_gt_worse`: `True`
- `selector_mean_delta_ratio_vs_ltm_lt_neg_0p003`: `True`
- `selector_bootstrap_probability_mean_delta_lt_0_ge_0p95`: `True`
- `selector_ratio_worse_than_ltm_groups_le_1`: `True`
- `selector_success_worse_than_ltm_groups_eq_0`: `True`
- `selector_beats_random_diagnostic`: `True`
- `selector_beats_shuffled_diagnostic`: `True`
- `selector_uses_no_forbidden_features`: `True`
- `phase5p5_allowed`: `False`
- `phase6_allowed`: `False`
- `development_gates_passed`: `True`

## Interpretation

Development gates passed. The frozen selector spec was written before any final IDs were evaluated.

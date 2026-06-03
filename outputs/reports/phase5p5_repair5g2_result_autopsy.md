# Phase5.5 Repair5G.2 Result Autopsy

Diagnostic-only. `phase5p5_allowed=false` and `phase6_allowed=false` remain closed.

## Answer

G2 is mainly a representation win with selector value still unclear. Flow-shielded dual-channel UpdateLTM is much stronger than scalar/C-equivalent baselines, while the frozen selector is effectively tied with the best static flow-shield candidate.

## Selector vs Static

- `selector_mean_delta_ratio_vs_ltm`: `-0.020112979571774988`
- `static_mean_delta_ratio_vs_ltm`: `-0.020043939351749987`
- `selector_minus_static_mean`: `-6.904022002500107e-05`
- `classification`: `tied_within_0p001`
- `selector_wins_cases`: `18`
- `static_wins_cases`: `23`
- `ties_cases`: `79`
- `selector_avoids_harm_cases`: `3`
- `selector_missed_gain_cases`: `20`

## Representation Evidence

- `best_flow_shield_method`: `repair5g2_frozen_static_or_selector`
- `best_flow_shield_mean_delta_ratio_vs_ltm`: `-0.020112979571774988`
- `best_c_equiv_or_scalar_method`: `repair5g2_c_equiv_best_frozen_baseline`
- `best_c_equiv_or_scalar_mean_delta_ratio_vs_ltm`: `-0.0022770787914083196`
- `flow_minus_c_gap`: `0.01783590078036667`

## Diagnostics

- `repair5g2_random_candidate_diagnostic`: rows `120`, mean delta `-0.01329058551464166`
- `repair5g2_shuffled_goal_progress_diagnostic`: rows `120`, mean delta `-0.01761917499324165`
- `repair5g2_shuffled_flow_shield_diagnostic`: rows `120`, mean delta `-0.019850973894158318`

## Risk Notes

- Warehouse is mostly no-op/fallback, so random and maze carry most G2 benefit.
- Shuffled flow-shield diagnostic is close to the selector, so selector intelligence should not be overclaimed.
- IDs 46..65 are observed and can be used only as later training data, not untouched final evidence.

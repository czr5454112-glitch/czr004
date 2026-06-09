# Phase5.5 Repair5G.5.9 G5.8 Offline Eval Autopsy

- eval_rows: `20`
- harmful_rows: `3`
- helpful_rows: `5`
- train_rows/dev_rows: `20` / `20`
- classes: `["repair5g1_shield_c100_b125_w075_d100_beta0p35_max0p75", "repair5g2_best_frozen_static_candidate"]`
- diagnosis: `{"candidate_space_too_narrow": true, "control_implementation_bug": true, "feature_signal_insufficient": true, "insufficient_train_dev_rows": true, "label_noise_or_budget_sensitivity": true, "model_overfit_or_calibration": true}`

The G5.8 model had weak positive mean score movement, but the autopsy confirms poor high-confidence calibration, too few train/dev rows, a two-candidate action space, and a naming mismatch in the negative-control gates.

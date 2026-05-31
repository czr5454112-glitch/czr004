# Phase5.5 Repair5E.1 OOD Guard Diagnostic Repair

This targeted repair implements Option 3 from the Case-B transfer analysis: an OOD/defer guard around the existing Repair5D composite distill bridge.

## Boundary

- diagnostic-only: `true`
- Phase5.5 allowed: `false`
- Phase6 allowed: `false`
- solver semantic changes: `false`
- candidate runtime: `artifacts\models\laur_ltm\repair5d_composite_distilled_ood_guard`
- source runtime: `artifacts\models\laur_ltm\repair5d_composite_distilled`
- guard CLI: `--laur-ood-z-threshold 5.0`

## Behavior

The runtime computes z-scores using the distill model's frozen `mean.csv` and `std.csv`. If the maximum absolute runtime feature z-score is at or above the threshold, the diagnostic candidate defers to `additive_ltm` for that update.

Every learned update is logged with OOD metrics: `feature_max_abs_z`, `feature_mean_abs_z`, `feature_outside_3sigma_count`, `feature_outside_5sigma_count`, `ood_guard_triggered`, and `ood_z_threshold`.

This is not a production runtime claim and does not unlock Phase5.5 or Phase6.

# Phase5.5 Repair5G.5.8 Protocol Overview

Repair5G.5.8 expands the observed-ID confidence label bank from the G5.7 diagnostic result.

The protocol is:

1. Verify required G5.7 artifacts.
2. Run a targeted observed-ID primary-pair expansion on IDs `151..155`.
3. Merge that slice with the existing G5.7 `146..150` budget-tier evidence.
4. Treat `1000/2000 ms` as the primary stability pair.
5. Treat `250 ms` as stress-only and `500 ms` as optional bonus evidence.
6. Construct confidence-weighted targets over margins `0.0025`, `0.005`, and `0.010`.
7. Select the training threshold before optional offline G6 training.
8. Classify warehouse/no-solution contexts explicitly as abstention, longer-budget, static-default, candidate-space-gap, or later specialist examples.
9. Build two G6 matrices: `perf_safe_only` and diagnostic-only `audit_plus_perf`.
10. Train and evaluate the tiny offline safe-mixture model only if all confidence, warehouse, and feature gates pass.

The protocol keeps these closures:

- `ids_166_205_untouched = true`
- `phase5p5_allowed = false`
- `phase6_allowed = false`
- `aaai_ready = false`
- `runtime_claim_allowed = false`

No C++ runtime integration is part of this wave.

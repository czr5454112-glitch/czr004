# Phase5.5 Repair5F Runtime vs Table Audit

This audit is diagnostic-only and does not permit Phase5.5 or Phase6.

## Checks

- runtime_selected_candidate_matches_table_policy: `True`
- runtime_updateparams_match_artifact: `True`
- force_additive_parity_exact: `True`
- exact_additive_candidate_parity_exact: `True`
- laur_disable_parity_exact: `True`
- laur_force_additive_direct_parity_exact: `True`
- phase5p5_allowed: `False`
- phase6_allowed: `False`
- mismatch_count: `0`
- outcome_mismatch_count: `0`

## Interpretation

The runtime selector applied the same candidate and bounded UpdateParams as the F2 table policy. Any remaining SoL or ratio differences should be treated as runtime timing or deterministic rerun differences, not context-adaptive policy evidence.

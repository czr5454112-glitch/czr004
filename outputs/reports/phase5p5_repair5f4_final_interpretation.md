# Phase5.5 Repair5F.4 Final Interpretation

Repair5F.4-A was a clean diagnostic failure, not an engineering failure.

Coverage, freshness, and additive parity controls passed:

- expected_rows: `1800`
- raw_rows_after_dedupe: `1800`
- missing_rows: `0`
- schema_errors: `0`
- force_additive_parity_exact: `true`
- exact_additive_candidate_parity_exact: `true`
- laur_disable_parity_exact: `true`
- laur_force_additive_direct_parity_exact: `true`
- support_validation_overlap_count: `0`
- f2f3_holdout_validation_overlap_count: `0`

The locked support-trained static bounded UpdateParams rule
`c100_b100_w075_d090` did not generalize on fresh IDs 26..45:

- better / equal / worse: `25 / 68 / 27`
- mean_delta_ratio_vs_ltm: `0.0000451908770666587`
- bootstrap_95ci_mean_delta_ratio_vs_ltm: `[-0.0025432106323166875, 0.002837331297599984]`

The locked rule also failed to beat the deterministic random candidate
diagnostic on mean delta. Component ablations suggest that decay `0.90` and
global static selection are plausible failure sources, but those observations
are diagnostic-only and must not be retuned into a claim from F4 outcomes.

Do not promote Repair5F.4-A. Do not claim Phase5.5 or Phase6. Do not run F4-B
time-budget stress validation for the locked rule.

The correct next step is Repair5F.4.1: failure decomposition and full-lattice
oracle diagnosis to determine whether bounded UpdateParams still has robust
fresh-ID headroom, or whether this branch should stop or pivot to a new
support/validation-trained selector with a new untouched final holdout.

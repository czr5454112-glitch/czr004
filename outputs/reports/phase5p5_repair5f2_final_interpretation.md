# Phase5.5 Repair5F.2 Final Interpretation

Repair5F.2 is a diagnostic-only table-level result. It does not permit Phase5.5 or Phase6.

## Boundary

- diagnostic_only: `true`
- final_holdout_used_for_tuning: `false`
- phase5p5_allowed: `false`
- phase6_allowed: `false`
- solver_semantic_changes: `false`

## Result

Repair5F.2 passed the predeclared table-level selector gates:

```text
repair5f_support_trained_selector_simulation:
  better / equal / worse = 6 / 19 / 5
  mean_delta_ratio_vs_ltm = -0.0027415721339999993
  ratio_worse_than_ltm_groups = 1
  success_worse_than_ltm_groups = 0
```

The selector was support-only tuned:

```text
support IDs = 1..20
final holdout IDs = 21..25
support_final_overlap_count = 0
final_holdout_used_for_tuning = false
```

The selected policy chose one candidate on every final holdout case:

```text
c100_b100_w075_d090: 30 / 30

alpha_commit = 1.00
alpha_block = 1.00
alpha_wait_spillover = 0.75
rho_decay = 0.90
```

## Interpretation

The current evidence is best viewed as a support-trained static bounded UpdateParams rule. It is a data-driven replacement candidate for the coarse additive UpdateLTM update, but it is not evidence for context-adaptive UpdateParams selection.

Runtime export is allowed only as a scoped diagnostic follow-up. Any runtime report must include a static-candidate ablation against `repair5f_static_c100_b100_w075_d090`. If the runtime selector equals the static candidate, the result must be named as a support-trained static bounded UpdateParams replacement, not a context-adaptive selector.

The E5 shuffled-label comparator remains an important caution:

```text
repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic:
  better / equal / worse = 7 / 20 / 3
  mean_delta_ratio_vs_ltm = -0.0039024738501666654
```

Therefore, do not claim a broad learned-utility victory from the F2 table result alone.

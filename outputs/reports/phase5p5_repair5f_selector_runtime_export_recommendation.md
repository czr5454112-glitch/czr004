# Repair5F.2 Runtime Export Recommendation

This follow-up report is created because the table-level selector simulation passed. It recommends a scoped runtime-export task, but no runtime artifact is exported here.

## Boundary

- runtime_export_created: `false`
- diagnostic_only: `true`
- phase5p5_allowed: `false`
- phase6_allowed: `false`
- solver_semantic_changes: `false`

## Evidence To Carry Forward

- selector method: `repair5f_support_trained_selector_simulation`
- selected candidate distribution: `{'c100_b100_w075_d090': 30}`
- better / equal / worse: `6 / 19 / 5`
- mean_delta_ratio_vs_ltm: `-0.0027415721339999993`
- ratio_worse_than_ltm_groups: `1`
- success_worse_than_ltm_groups: `0`
- support_final_overlap_count: `0`

## Recommended Next Task

Create `scripts/create_repair5f_updateparam_selector_runtime.py` and `artifacts/models/laur_ltm/repair5f_bounded_updateparam_selector/` in a separate scoped step. The first runtime should select one bounded candidate at the first eligible post-first-solution update, lock that candidate for the run, log the selected UpdateParams, and preserve exact additive fallback.

## Required Runtime Gates

- force-additive parity exact
- exact additive candidate parity exact
- runtime selector reproduces the table-level decision policy
- actual runtime better > worse
- actual runtime mean_delta_ratio_vs_ltm < 0
- actual runtime ratio_worse_than_ltm_groups <= 1
- actual runtime success_worse_than_ltm_groups = 0
- random/shuffled diagnostics remain weaker

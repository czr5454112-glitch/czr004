# Phase5.5 Repair5G.5.6 Protocol Overview

G5.6 is an observed-ID diagnostic protocol for deciding whether offline G6 safe-mixture training is allowed.

Protocol steps:

1. Complete same-context counterfactual labels toward `context_count >= 120`, complete map/agent coverage, and report iteration coverage including later iterations.
2. Classify warehouse probe failures instead of dropping NaN/blank gaps.
3. Expand probe-budget stability over `250/500/1000/2000 ms` and require at least `30` training-eligible stable contexts.
4. Split G6 features into `perf_safe_only` and `audit_only`; `cost_min`, `cost_max`, `cost_span`, and `cost_bounds_respected` are audit-only.
5. Construct safe-mixture targets with static abstention, harmful-candidate labels, and budget-stability flags.
6. Train/evaluate the optional offline G6 prototype only if P1-P5 gates all pass.
7. Write a final decision while keeping Phase5.5, Phase6, AAAI-ready, and fresh-ID usage closed.

Current G5.6 decision from available evidence:

- decision: `probe_budget_instability_blocks_training`
- context_count: `140`
- label_rows: `980`
- later_iteration_context_count: `20`
- measured_budget_stability_contexts: `30`
- training_eligible_stable_contexts: `4`
- offline_training_run: `false`

The scaled-label target is now met on observed IDs, and later-iteration labels exist. The blocker moved to budget stability: only `4` contexts are training-eligible stable under the expanded budget grid, below the required `30`. The next valid action is more observed-ID budget-stability/label collection or feature/probe design, not G6 training. Do not run IDs `166..205`, do not train a runtime model, and do not claim learned-runtime performance from the current artifacts.

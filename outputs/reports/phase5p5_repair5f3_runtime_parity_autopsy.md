# Repair5F.3 Runtime Parity Autopsy

Diagnostic-only. Phase5.5 and Phase6 remain forbidden.

## Core Parity

- `always_additive_defer`: present `True`, core parity `False`
- `repair5f_candidate_additive_ltm`: present `True`, core parity `False`
- `repair5f_bounded_updateparam_selector_force_additive_parity`: present `True`, core parity `False`
- `laur_disable`: present `False`, core parity `False`
- `laur_force_additive_direct`: present `False`, core parity `False`

## Classification Counts

- finite/nonfinite ratio mismatch: `3`
- lower_bound mismatch: `3`
- makespan mismatch: `3`
- runtime artifact loaded when it should have been bypassed: `90`
- success mismatch: `6`
- sum_of_loss mismatch: `3`
- time-budget / nondeterministic rerun difference: `19`
- update log / feature extraction executed in a parity path: `30`
- wrapper/method alias mismatch: `303`

## Core Mismatch Cases

| method | map | agents | seed | classifications |
|---|---|---:|---:|---|
| `always_additive_defer` | warehouse-10-20-10-2-1 | 100 | 21 | `finite/nonfinite ratio mismatch, lower_bound mismatch, makespan mismatch, runtime artifact loaded when it should have been bypassed, success mismatch, sum_of_loss mismatch, time-budget / nondeterministic rerun difference, wrapper/method alias mismatch` |
| `repair5f_candidate_additive_ltm` | warehouse-10-20-10-2-1 | 100 | 21 | `finite/nonfinite ratio mismatch, lower_bound mismatch, makespan mismatch, runtime artifact loaded when it should have been bypassed, success mismatch, sum_of_loss mismatch, time-budget / nondeterministic rerun difference, update log / feature extraction executed in a parity path, wrapper/method alias mismatch` |
| `repair5f_bounded_updateparam_selector_force_additive_parity` | warehouse-10-20-10-2-1 | 100 | 21 | `finite/nonfinite ratio mismatch, lower_bound mismatch, makespan mismatch, runtime artifact loaded when it should have been bypassed, success mismatch, sum_of_loss mismatch, time-budget / nondeterministic rerun difference, wrapper/method alias mismatch` |

## Runtime-vs-Table Snapshot

- runtime_selected_candidate_matches_table_policy: `True`
- runtime_updateparams_match_artifact: `True`
- mismatch_count: `0`
- force_additive_parity_exact: `False`
- exact_additive_candidate_parity_exact: `False`

## Interpretation

F3 remains useful positive runtime evidence for a support-trained static bounded UpdateParams rule, but the additive controls are not closed in this input run. The next step is a parity wrapper fix and a same-scope closure rerun, not larger validation.

# Repair5F.3 Runtime Parity Reproducer

Diagnostic-only. This reruns only parity mismatch cases plus one control case.

## Scope

- repeats: `3`
- cases: `[{'map': 'maze-32-32-4', 'agents': 50, 'seed': 21}, {'map': 'warehouse-10-20-10-2-1', 'agents': 100, 'seed': 21}]`
- methods: `['lacam_star_ltm', 'always_additive_defer', 'repair5f_candidate_additive_ltm', 'repair5f_bounded_updateparam_selector_force_additive_parity', 'laur_disable', 'laur_force_additive_direct']`

## Parity

| method | rows | outcome exact | effort exact | better | equal | worse |
|---|---:|---|---|---:|---:|---:|
| `always_additive_defer` | 6 | True | True | 0 | 6 | 0 |
| `repair5f_candidate_additive_ltm` | 6 | True | True | 0 | 6 | 0 |
| `repair5f_bounded_updateparam_selector_force_additive_parity` | 6 | True | True | 0 | 6 | 0 |
| `laur_disable` | 6 | True | True | 0 | 6 | 0 |
| `laur_force_additive_direct` | 6 | True | True | 0 | 6 | 0 |

## Interpretation

All replayed parity controls match plain LaCAM*+LTM on outcome fields.
No Phase5.5 or Phase6 permission is granted by this reproducer.

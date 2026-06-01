# Phase5.5 Repair5F F1 Decision

This is a diagnostic-only decision note. It does not permit Phase5.5 or Phase6.

## Decision

Repair5F F1 found strong bounded `UpdateParams` oracle headroom, but the run is
safety-blocked until force-additive parity is exact.

No selector/runtime artifact was exported.

## Evidence

- Full raw coverage after dedupe: `1530 / 1530` unique rows.
- Duplicate raw rows dropped: `245`.
- Missing rows: `0`.
- Audit: report, summary, raw JSONL, and derived CSVs are internally consistent.

## Oracle Result

| method | better | equal | worse | mean delta ratio vs LTM | ratio worse groups | success worse groups |
|---|---:|---:|---:|---:|---:|---:|
| `repair5f_candidate_lattice_oracle_static_proxy` | 17 | 13 | 0 | -0.018311948514033324 | 0 | 0 |

## Diagnostics

| method | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|
| `repair5f_bounded_updateparam_selector_random_candidate_diagnostic` | 6 | 17 | 7 | 0.00297909950036667 |
| `repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic` | 4 | 17 | 9 | 0.002559801023448285 |

## Safety Blocker

- `exact_additive_candidate_parity_exact=true`.
- `force_additive_parity_exact=false`.
- `safety_gates_passed=false`.
- `candidate_lattice_oracle_metric_gate_passed=true`.
- `phase5p5_allowed=false`.
- `phase6_allowed=false`.

The exact additive bounded candidate matched `LaCAM*+LTM`, so the bounded
lattice evidence remains useful. The legacy force-additive control must be
autopsied and fixed before any selector/runtime export.

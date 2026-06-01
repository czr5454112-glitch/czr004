# Phase5.5 Repair5F Force-Additive Parity Autopsy

This report is diagnostic-only and does not permit Phase5.5 or Phase6.

## Result

- force_additive_parity_exact: `False`
- canonical_exact_additive_candidate_parity_exact: `True`
- mismatch_case_count: `1`
- mismatch_maps: `['warehouse-10-20-10-2-1']`
- duplicate_raw_rows_dropped: `245`
- duplicate_rows_touch_mismatch: `0`

## Mismatch Cases

| map | agents | seed | force exact | canonical exact |
|---|---:|---:|---|---|
| warehouse-10-20-10-2-1 | 50 | 25 | False | True |

## Control Rows

| method | success | SoL | LB | ratio | makespan | expanded | solutions | ltm iters | update mode | force | post-first | selected rules | fallback |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---:|
| lacam_star_ltm | True | 4780 | 4467 | 1.07006939781 | 211 | 423 | 1 | 3 | disabled | False | True | `{}` | 0 |
| always_additive_defer | True | 4989 | 4467 | 1.11685695097 | 209 | 211 | 1 | 2 | force_additive | True | True | `{"additive_ltm": 1}` | 1 |
| repair5f_candidate_additive_ltm | True | 4780 | 4467 | 1.07006939781 | 211 | 422 | 1 | 2 | runtime | False | True | `{"additive_ltm": 1}` | 1 |

## Interpretation

The mismatch is isolated to the legacy force-additive control. The exact additive bounded candidate matches LaCAM*+LTM on every full-holdout case. The divergent legacy row also ran fewer high-level/low-level iterations on the mismatch case, which points to wall-clock-sensitive runtime wrapper overhead rather than a different additive UpdateParams value.

The strict gate should be closed by making `--laur-force-additive` use the canonical additive LTM update path directly, without LAUR feature extraction or runtime prediction work. This is a bug fix to preserve the original parity gate, not a replacement or weakening of the gate.

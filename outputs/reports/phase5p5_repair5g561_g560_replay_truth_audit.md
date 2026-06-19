# Repair5G.5.61 G5.60 Replay Truth Audit

Decision: `g561_g560_replay_invalid_materialization_not_actor_failure`

The committed G5.60 replay cannot be read as a clean actor result: generated rows were not all recognized/materialized, and replay identity was not preserved in the result/pair tables.

- Solver rows audited: `600`
- Actor rows audited: `300`
- Exact actor materializations: `165`
- Strict exact materialization rate: `0.550000`
- Actor rows missing replay identity in raw results: `300`
- Actor rows missing scenario SHA in raw results: `300`

## Materialization Classes

- fallback_additive_executed: `135`
- valid_exact_materialization: `165`

## Recomputed Summaries

- Historical committed pairs: `300`, regressions `25`, mean delta `0.11486412997058826`
- Evaluation-UID recovered pairs: `300`, regressions `25`, mean delta `0.11486412997058822`
- Recognized rows only: `165`, regressions `0`, mean delta `-0.01112573317310974`
- Exact materialization only: `165`, regressions `0`, mean delta `-0.01112573317310974`

Non-materialized rows are excluded from scientific actor-performance interpretation. All promotion/runtime claims remain closed.

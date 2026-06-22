# G5.67 Direct-Exact Timeout Reproducer

Date: 2026-06-22 Asia/Shanghai

Commit under repair: `407cd6202c5f169ce0f6cfa98e9c3994b21ce6a6`

## Decision

`direct_exact_reproducer_completed`

This is STOP 1 evidence only. It does not authorize Stage-2A, Gate-3A, Gate-3B, or the full campaign.

## Compared Runs

- A: old `cae91e4c` static-flow outer solve plus additive counterfactual probe requested at 30000 ms.
- B: current `407cd620` direct additive exact row, no counterfactual probe.
- C: current `407cd620` static-flow outer plus additive diagnostic probe requested at 3000 ms and clipped to parent deadline.

## Results

| Context | A old outer+probe | B direct exact | C clipped probe |
|---|---:|---:|---:|
| tunnel-24x24 a64 | hard timeout at 76.20s | no hard timeout, 38.35s | no hard timeout, 41.79s |
| cross-32x32 a256 | no hard timeout, 54.54s | no hard timeout, 37.47s | no hard timeout, 36.62s |
| connector-48x48 a256 | hard timeout at 75.85s | no hard timeout, 36.70s | no hard timeout, 37.39s |

Summary:

- Old outer+probe hard timeouts: `2/3`
- Direct exact hard timeouts: `0/3`
- Current clipped diagnostic probe hard timeouts: `0/3`
- Maximum direct exact wall time: `38.352189s`
- Maximum old outer+probe wall time: `76.195668s`

## Evidence Files

- Summary JSON: `outputs/reports/phase5p5_repair5g567_direct_exact_reproducer_summary.json`
- Table: `outputs/tables/phase5p5_repair5g567_direct_exact_reproducer.csv`
- Raw JSONL directory: `outputs/reports/phase5p5_repair5g567_direct_exact_reproducer/`

## Interpretation

The old timeout signature is reproduced by the nested static-flow outer plus counterfactual probe path. Direct exact additive rows on the same tail contexts do not hit the process hard timeout. This supports GPT Pro's diagnosis: the r5 timeout evidence must not be interpreted as direct additive/static/g556/A5 primary-row timeout evidence.

Gate-3B and the full campaign remain locked.

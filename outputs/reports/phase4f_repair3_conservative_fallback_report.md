# Phase4F Repair3 Conservative Fallback Report

Date: 2026-05-27

## Summary

Repair3 already has a seed-61 local Phase4F offline candidate pass. The remaining risk is seed sensitivity in validation mean selected delta: seeds `103` and `107` keep exact-rule top1/top3 and safety above gate, but their raw validation mean selected delta is slightly negative.

This diagnostic checks whether the existing safety head can act as a conservative additive fallback gate without changing the Phase4F exact-rule ranking gate.

## Policy Checked

The checked policy is:

```text
if harmful_update_probability >= 0.30:
    execute additive/neutral fallback
else:
    execute predicted update rule
```

This is diagnostic evidence only. It does not lower the Phase4F gate, does not change labels, and does not perform Phase5 runtime integration.

## Threshold 0.30 Evidence

At threshold `0.30`, all three Repair3 seeds satisfy train and validation safety precision/recall requirements, and validation mean delta after fallback is positive.

| seed | split | recall | precision | fallback rate | mean delta before fallback | mean delta after fallback |
|---:|---|---:|---:|---:|---:|---:|
| 61 | train | 0.9203 | 0.6086 | 0.7506 | 0.0276 | 0.0059 |
| 61 | validation | 0.8092 | 0.4795 | 0.6362 | 0.0081 | 0.0064 |
| 103 | train | 0.9203 | 0.6026 | 0.7581 | 0.0292 | 0.0063 |
| 103 | validation | 0.8150 | 0.4747 | 0.6471 | -0.0010 | 0.0031 |
| 107 | train | 0.9258 | 0.6085 | 0.7553 | 0.0292 | 0.0060 |
| 107 | validation | 0.8439 | 0.4725 | 0.6732 | -0.0012 | 0.0014 |

## Interpretation

The common threshold `0.30` is a useful Phase5 safety-fallback candidate because it turns the seed-sensitive validation mean delta positive for all checked Repair3 seeds while keeping:

- validation harmful recall above `0.80`
- validation harmful precision above `0.30`
- the original exact-rule top1/top3 evaluation unchanged

The cost is high fallback rate (`0.64` to `0.67` on validation), so this should be treated as a conservative first runtime setting rather than an optimized performance setting.

## Generated Diagnostics

- seed 61 report: `outputs/reports/phase4f_repair3_stable_tie001_diagnostics.md`
- seed 103 report: `outputs/reports/phase4f_repair3_stable_tie001_s103_diagnostics.md`
- seed 107 report: `outputs/reports/phase4f_repair3_stable_tie001_s107_diagnostics.md`
- safety sweep tables:
  - `outputs/tables/phase4f_repair3_stable_tie001_diagnostics/phase4f_laur_safety_threshold_sweep.csv`
  - `outputs/tables/phase4f_repair3_stable_tie001_s103_diagnostics/phase4f_laur_safety_threshold_sweep.csv`
  - `outputs/tables/phase4f_repair3_stable_tie001_s107_diagnostics/phase4f_laur_safety_threshold_sweep.csv`

## Decision

Keep the Phase4F status as stable-target offline candidate pass. If Phase5 is started, use `0.30` as the first conservative safety fallback threshold candidate and require parity/fallback runtime smoke before making any learned-runtime performance claim.

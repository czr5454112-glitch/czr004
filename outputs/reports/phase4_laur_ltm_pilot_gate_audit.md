# Phase4F LAU-LTM Pilot Gate Audit

Date: 2026-05-26

## Source

- batch report: `outputs/reports/phase4_laur_ltm_pilot_batch_report.md`
- offline eval: `outputs/reports/phase4_laur_ltm_offline_eval_pilot_summary.json`
- server note: `outputs/reports/phase4_laur_ltm_pilot_server_note.md`

## Corrected Phase4F Gate

| Criterion | Threshold | Pilot value | Pass |
| --- | ---: | ---: | --- |
| validation non-neutral checkpoints | 50 | 58 | yes |
| validation rule top-1 accuracy | 0.35 | 0.1375 | no |
| validation rule top-3 accuracy | 0.70 | 0.4875 | no |
| validation harmful update recall | 0.80 | 0.0714286 | no |
| validation harmful update precision | 0.30 | 0.4 | yes |
| predicted-rule validation mean delta ratio | 0.0 | 0.00205681 | yes |
| neutral-additive behavior documented | required | 0.1125 rate | yes |

## Decision

The pilot passed the operational/data-coverage gate but failed the Phase4F
performance gate. It is not valid evidence for entering Phase5 learned runtime.

Allowed next steps:

- run a larger Phase4 data/diagnostic experiment;
- inspect held-out map failure cases and label imbalance;
- enter Phase5 only for force-additive or oracle-rule integration smoke, not for
  learned MLP runtime claims.

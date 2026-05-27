# Phase4F Repair4 Stable-Attention Final Gate Report

## Decision

Phase5.5 runtime is not allowed for the Repair4 stable-attention models in this run.

Reason: SetRuleTransformer and EdgeTraceTransformer both satisfy the ranking/delta side of the Phase4F gate, but the per-rule harmful safety head does not meet the required precision/recall tradeoff without lowering recall below the gate.

## Dataset Audit

| item | value |
|---|---:|
| passed | True |
| sample_count | 2985 |
| schema_error_count | 0 |
| split_leakage_error_count | 0 |
| edge_truncation_rate | 0.0 |
| trace_truncation_rate | 0.0 |
| rule_vocab_count | 8 |
| train rows | 2526 |
| validation rows | 459 |

## Repair3 MLP Baseline

| model | top1 | top3 | harmful recall | harmful precision | mean delta |
|---|---:|---:|---:|---:|---:|
| Repair3 stable-target MLP seed61 | 0.389978 | 0.769063 | 0.942197 | 0.390887 | 0.008131 |

## SetRuleTransformer V1

| seed | top1 | top3 | harmful recall | harmful precision | mean delta | fallback | Phase4F | runtime |
|---:|---:|---:|---:|---:|---:|---:|---|---|
| 61 | 0.383442 | 0.721133 | 0.967963 | 0.209510 | 0.002594 | 0.762527 | False | False |
| 103 | 0.392157 | 0.742919 | 0.954233 | 0.203912 | 0.000575 | 0.749455 | False | False |
| 107 | 0.396514 | 0.758170 | 0.986270 | 0.184503 | 0.002494 | 0.819172 | False | False |

Extended threshold sweep over thresholds 0.35-0.90 found no all-seed Phase4F pass. The precision/recall tradeoff is the limiting item.

| threshold | min recall | min precision | min delta | avg top3 | all Phase4F |
|---:|---:|---:|---:|---:|---|
| 0.35 | 0.885584 | 0.230293 | -0.001410 | 0.740741 | False |
| 0.40 | 0.837529 | 0.235156 | -0.001400 | 0.740741 | False |
| 0.45 | 0.798627 | 0.245736 | -0.000622 | 0.740741 | False |
| 0.50 | 0.734554 | 0.250859 | -0.000558 | 0.740741 | False |
| 0.55 | 0.608696 | 0.264412 | -0.007189 | 0.740741 | False |
| 0.60 | 0.471396 | 0.280073 | -0.000469 | 0.740741 | False |
| 0.70 | 0.192220 | 0.320669 | 0.004008 | 0.740741 | False |
| 0.80 | 0.057208 | 0.398148 | 0.001945 | 0.740741 | False |
| 0.90 | 0.000000 | 0.000000 | 0.001945 | 0.740741 | False |

## EdgeTraceTransformer V3

| variant | threshold | top1 | top3 | harmful recall | harmful precision | mean delta | fallback | Phase4F | runtime |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| edge_trace_seed61 | 0.10 | 0.394336 | 0.749455 | 0.958810 | 0.217889 | 0.003256 | 0.677560 | False | False |
| edge_trace_gate_select_seed61 | 0.50 | 0.400871 | 0.749455 | 0.782609 | 0.287154 | 0.005734 | 0.575163 | False | False |

EdgeTrace improves top3 to the Repair3-comparable boundary and improves selected delta, but it still misses safety. At threshold 0.50 it reaches precision 0.287154 and recall 0.782609; at threshold 0.60 precision passes but recall falls to 0.610984.

## Conclusion

Do not integrate the advanced stable-attention model into Phase5.5 runtime. Keep the Repair3 stable-target MLP/conservative fallback path as the current offline-pass baseline, and treat Repair4 stable-attention as a negative/diagnostic result: stronger ranking signal, insufficient per-rule safety calibration.

Primary evidence files:

- `outputs/reports/phase4f_repair4_stable_attention_final_gate_summary.json`
- `outputs/reports/phase4f_repair4_stable_attention_seed_aggregate_summary.json`
- `outputs/reports/phase4f_repair4_stable_attention_extended_threshold_sweep_summary.json`
- `outputs/reports/phase4f_repair4_stable_edge_trace_summary_seed61.json`
- `outputs/reports/phase4f_repair4_stable_edge_trace_gate_select_summary_seed61.json`


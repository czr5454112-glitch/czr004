# Phase5.5 Repair5G.5.18 Probe Batches

- decision: `g518_candidate_space_improved_continue_full_primary`
- batch_count: `3`
- candidate_space_gate_passed_batches: `['A', 'B', 'C']`
- integrity_failed_batches: `[]`

## Batch Results

- Batch `A`: decision `g518_batch_candidate_space_improved_continue_full_primary`, wins `4`, mean gap `-0.00020502306599996524`, gate `True`
- Batch `B`: decision `g518_batch_candidate_space_improved_continue_full_primary`, wins `2`, mean gap `-0.002255253715999972`, gate `True`
- Batch `C`: decision `g518_batch_candidate_space_improved_continue_full_primary`, wins `2`, mean gap `-0.0013326499239999733`, gate `True`

If no batch passes the candidate-space gate, full-primary expansion and ranker training remain intentionally skipped.

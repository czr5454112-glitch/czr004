# G5.28 Teacher Consistency Audit

- decision: `teacher_consistency_verified_continue_exact_failure_audit`
- reconstructed non-empty utility mean: `-0.011588397798`
- zero-filled diagnostic mean: `-0.008305018422`
- candidate-induced no-solution count: `0`
- safe-positive selected count: `41`
- fallback rate: `0.3416666666666667`
- join mismatches: `0`

The offline-RL direct-teacher summary mismatch is a reporting/aggregation bug: that row reused the failed distillation aggregate (`0.039188132663`, 8 induced failures) instead of the reconstructed conservative teacher aggregate (`-0.011588397798`, 0 induced failures).

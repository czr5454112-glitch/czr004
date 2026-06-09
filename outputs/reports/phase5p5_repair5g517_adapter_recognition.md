# Phase5.5 Repair5G.5.17 Adapter Recognition

- decision: `adapter_recognition_passed_continue_local_probe`
- candidate_count: `10`
- recognized_candidate_count: `10`
- exact_parameter_tuple_count: `10`
- gates: `{'candidate_count_eq_10': True, 'all_candidates_present': True, 'all_parameter_tuples_exact': True, 'no_extra_repair5g516_adapter_candidates': True, 'comment_block_present': True}`

## Candidate Mappings

- `repair5g516_slow_decay_safer_beta025_cap050`: recognized=`True`, exact=`True`
- `repair5g516_slow_decay_safer_beta020_cap045`: recognized=`True`, exact=`True`
- `repair5g516_slow_decay_safer_beta015_cap040`: recognized=`True`, exact=`True`
- `repair5g516_wait_aggressive_low_cap`: recognized=`True`, exact=`True`
- `repair5g516_wait_conservative_mid_cap`: recognized=`True`, exact=`True`
- `repair5g516_wait_aggressive_fast_flow_decay`: recognized=`True`, exact=`True`
- `repair5g516_commit_heavy_low_beta`: recognized=`True`, exact=`True`
- `repair5g516_commit_heavy_static_guard`: recognized=`True`, exact=`True`
- `repair5g516_static_boundary_light_flow`: recognized=`True`, exact=`True`
- `repair5g516_static_boundary_c_only`: recognized=`True`, exact=`True`

This check only verifies project-owned adapter recognition in `cpp/tools/phase1a_batch.cpp`; it does not modify or inspect reserved scenario IDs.

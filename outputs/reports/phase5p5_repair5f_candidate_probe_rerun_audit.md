# Phase5.5 Repair5F Candidate Probe Rerun Audit

Verification date: 2026-06-01

This audit checks the Repair5F.1 post-fix rerun outputs.

## Source Files

- Report: `outputs/reports/phase5p5_repair5f_candidate_probe_rerun_report.md`
- Summary: `outputs/reports/phase5p5_repair5f_candidate_probe_rerun_summary.json`
- Raw probe JSONL: `outputs/logs/phase5p5_repair5f_candidate_probe_rerun/phase5p5_repair5f_candidate_probe_rerun.jsonl`
- Command log JSONL: `outputs/logs/phase5p5_repair5f_candidate_probe_rerun/phase5p5_repair5f_candidate_probe_rerun_commands.jsonl`
- LAUR update log JSONL: `outputs/logs/phase5p5_repair5f_candidate_probe_rerun/phase5p5_repair5f_candidate_probe_rerun_laur_updates.jsonl`

## Raw Coverage

- Raw rows before dedupe: `1530`
- Raw rows after dedupe: `1530`
- Expected unique rows: `1530`
- Missing rows: `0`
- Duplicate raw rows dropped: `0`
- Long CSV rows: `1410`
- Wide CSV rows: `30`

## Raw Log Hashes

- `phase5p5_repair5f_candidate_probe_rerun.jsonl`: `6905992A9FA86AB83543A0DD56592EB50869892B681FC4F2A1623A76A7FB632F`
- `phase5p5_repair5f_candidate_probe_rerun_commands.jsonl`: `2E2F77047C132683F3485F241EB7944CAE9A6D9B5795AB5191D1B1BA8DB3928E`
- `phase5p5_repair5f_candidate_probe_rerun_laur_updates.jsonl`: `A966F921D67CE03D70C855E0DF6D340A3D3FC6A69AB8DD2222B0B807CB1D1F95`

## Gate Check

- `force_additive_parity_exact`: `true`
- `exact_additive_candidate_parity_exact`: `true`
- `safety_gates_passed`: `true`
- `support_eval_leakage`: `false`
- `full_raw_probe_coverage`: `true`
- `full_f1_scope_evaluated`: `true`
- `candidate_lattice_oracle_metric_gate_passed`: `true`
- `candidate_lattice_oracle_gate_passed`: `true`
- `phase5p5_allowed`: `false`
- `phase6_allowed`: `false`

## Paired Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 30 | 0 | 30 | 0 | 0.0 |
| `repair5f_candidate_additive_ltm` | 30 | 0 | 30 | 0 | 0.0 |
| `repair5f_candidate_lattice_oracle_static_proxy` | 30 | 17 | 13 | 0 | -0.018311948514033324 |
| `repair5f_bounded_updateparam_selector_random_candidate_diagnostic` | 30 | 6 | 18 | 6 | 0.001419514395033339 |
| `repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic` | 30 | 4 | 19 | 7 | 0.0009148892173333441 |
| `repair5e5_crossfold_utility_reranker` | 30 | 4 | 22 | 4 | -0.0009245170596666741 |
| `repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic` | 30 | 7 | 20 | 3 | -0.0039024738501666654 |

## Conclusion

The Repair5F.1 post-fix rerun closes both strict parity controls and preserves
the strong bounded-lattice oracle result. Random and shuffled Repair5F
diagnostics remain weaker than the oracle. This is still diagnostic-only:
`phase5p5_allowed=false`, `phase6_allowed=false`, and no selector/runtime
artifact has been exported.

# Phase5.5 Repair5F Candidate Probe Audit

Verification date: 2026-06-01

This audit checks whether the committed Repair5F candidate probe report is
consistent with the local raw probe JSONL and derived CSV tables.

## Source Files

- Report: `outputs/reports/phase5p5_repair5f_candidate_probe_report.md`
- Summary: `outputs/reports/phase5p5_repair5f_candidate_probe_summary.json`
- Raw probe JSONL: `outputs/logs/phase5p5_repair5f_candidate_probe/phase5p5_repair5f_candidate_probe.jsonl`
- Command log JSONL: `outputs/logs/phase5p5_repair5f_candidate_probe/phase5p5_repair5f_candidate_probe_commands.jsonl`
- LAUR update log JSONL: `outputs/logs/phase5p5_repair5f_candidate_probe/phase5p5_repair5f_candidate_probe_laur_updates.jsonl`

The raw logs are local diagnostic logs under `outputs/logs`. The committed
report and summary record the deduped results derived from those logs.

## Raw Coverage Check

- Raw rows before dedupe: `1775`
- Raw rows after dedupe by `(map, agents, seed, method)`: `1530`
- Duplicate raw rows dropped: `245`
- Expected unique rows: `1530`
- Missing unique rows: `0`
- Method count per case: `51`
- Maps: `maze-32-32-4`, `random-32-32-20`, `warehouse-10-20-10-2-1`
- Agent counts: `50`, `100`
- Seeds: `21`, `22`, `23`, `24`, `25`
- Bad `(map, agents, seed)` group counts: `0`
- Summary coverage fields match recomputed raw coverage: `true`
- Summary schema errors: `0`

## Derived Table Check

- Long CSV rows: `1410`
- Wide CSV rows: `30`

The long table row count equals `30` final-holdout cases times `47`
Repair5F bounded candidates.

## Provenance Check

- Deduped raw rows report `git_commit = a9af4a6`: `1530 / 1530`
- Deduped raw rows report `dirty = tracked-dirty_untracked-present`: `1530 / 1530`
- Current report-containing commit after final decision: `e3e045a`

The raw diagnostic data was generated before the final report commit, so the
raw-row commit field points at the pre-report code commit. This is expected and
is recorded as diagnostic dirty provenance, not promotion-grade clean
provenance.

## Raw Log Hashes

- `phase5p5_repair5f_candidate_probe.jsonl`: `425b74418036f925c41e82e71c6eb38b6bc55a5292cb35ecf49a8ff9c3c152e2`
- `phase5p5_repair5f_candidate_probe_commands.jsonl`: `ef9dd883d6b8504c7bee40d8823f95345d32f362ae4053293c4fb9b2797e6344`
- `phase5p5_repair5f_candidate_probe_laur_updates.jsonl`: `f3e4b219e9de8731248a1450b392c52fc07a4f5d688c59ee23cea03321187485`

## Independent Paired-Stats Recompute

The following statistics were independently recomputed from the deduped raw
rows and match `phase5p5_repair5f_candidate_probe_summary.json`.

| method | rows | better | equal | worse | mean delta ratio vs LTM | summary match |
|---|---:|---:|---:|---:|---:|---|
| always_additive_defer | 30 | 0 | 29 | 1 | 0.0015595851053333313 | true |
| repair5e5_crossfold_utility_reranker | 30 | 4 | 22 | 4 | -0.0009245170596666741 | true |
| repair5e5_crossfold_utility_reranker_shuffled_labels_diagnostic | 30 | 7 | 19 | 4 | -0.0023428887448333343 | true |
| repair5f_bounded_updateparam_selector_random_candidate_diagnostic | 30 | 6 | 17 | 7 | 0.00297909950036667 | true |
| repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic | 30 | 4 | 17 | 9 | 0.002559801023448285 | true |
| repair5f_candidate_lattice_oracle_static_proxy | 30 | 17 | 13 | 0 | -0.018311948514033324 | true |

## Gate Check

- `full_raw_probe_coverage`: `true`
- `full_f1_scope_evaluated`: `true`
- `candidate_lattice_oracle_metric_gate_passed`: `true`
- `force_additive_parity_exact`: `false`
- `exact_additive_candidate_parity_exact`: `true`
- `safety_gates_passed`: `false`
- `candidate_lattice_oracle_gate_passed`: `false`
- `phase5p5_allowed`: `false`
- `phase6_allowed`: `false`
- `solver_semantic_changes`: `false`
- `support_eval_leakage`: `false`

## Conclusion

The report data is internally consistent with the local raw diagnostic logs and
derived tables. The strong oracle headroom result is real within this diagnostic
run, but the final decision remains safety-blocked because the strict
force-additive defer parity control is not exact on the full holdout. No
selector/runtime artifact should be promoted from this report.

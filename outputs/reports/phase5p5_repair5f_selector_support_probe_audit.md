# Phase5.5 Repair5F Candidate Probe Audit

Verification date: 2026-06-02

This audit is diagnostic-only and does not permit Phase5.5 or Phase6.

## Source Files

- Report: `C:\PROGRAMING\czr004\outputs\reports\phase5p5_repair5f_selector_support_probe_report.md`
- Summary: `C:\PROGRAMING\czr004\outputs\reports\phase5p5_repair5f_selector_support_probe_summary.json`
- Raw probe JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5f_selector_support_probe\phase5p5_repair5f_selector_support_probe.jsonl`
- Command log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5f_selector_support_probe\phase5p5_repair5f_selector_support_probe_commands.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5f_selector_support_probe\phase5p5_repair5f_selector_support_probe_laur_updates.jsonl`
- Long CSV: `C:\PROGRAMING\czr004\outputs\tables\phase5p5_repair5f_selector_support_utility_long.csv`
- Wide CSV: `C:\PROGRAMING\czr004\outputs\tables\phase5p5_repair5f_selector_support_utility_wide.csv`

## Raw Coverage

- Raw rows before dedupe: `5889`
- Raw rows after dedupe: `5880`
- Expected unique rows: `5880`
- Missing rows: `0`
- Duplicate raw rows dropped: `9`
- Expected candidate rows: `5640`
- Missing candidate rows: `0`
- Schema errors: `0`
- Long CSV rows: `5640`
- Wide CSV rows: `120`

## Raw Log Hashes

- `phase5p5_repair5f_selector_support_probe.jsonl`: `E85DBA2BEA32061E2C4EE86CD1CA602AB845450D99E7F59121C4136F62D41578`
- `phase5p5_repair5f_selector_support_probe_commands.jsonl`: `620A26641132565AD11E7824E5165CDDE029BFD27EF961104E5FA5C88656199F`
- `phase5p5_repair5f_selector_support_probe_laur_updates.jsonl`: `E2A1CC4A1EC75DB5D67CE3DAABB19BF451CE068D186BE31206092FF4062935A5`

## Gate Check

- `force_additive_parity_exact`: `True`
- `exact_additive_candidate_parity_exact`: `True`
- `safety_gates_passed`: `True`
- `support_eval_leakage`: `False`
- `support_final_overlap_count`: `0`
- `full_raw_probe_coverage`: `True`
- `phase5p5_allowed`: `False`
- `phase6_allowed`: `False`

## Paired Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 120 | 0 | 108 | 0 | 0.0 |
| `repair5f_candidate_additive_ltm` | 120 | 0 | 108 | 0 | 0.0 |
| `repair5f_candidate_lattice_oracle_static_proxy` | 120 | 72 | 40 | 0 | -0.023707208752555563 |
| `repair5f_bounded_updateparam_selector_random_candidate_diagnostic` | 120 | 29 | 53 | 26 | -0.0009960441101553538 |
| `repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic` | 120 | 21 | 58 | 29 | 0.0016592289544672847 |

## Conclusion

Candidate coverage and schema checks are complete for the requested probe scope. This remains selector-training evidence only unless a later leakage-safe selector simulation passes.

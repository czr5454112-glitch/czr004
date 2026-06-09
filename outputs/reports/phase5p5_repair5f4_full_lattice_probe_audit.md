# Phase5.5 Repair5F Candidate Probe Audit

Verification date: 2026-06-02

This audit is diagnostic-only and does not permit Phase5.5 or Phase6.

## Source Files

- Report: `C:\PROGRAMING\czr004\outputs\reports\phase5p5_repair5f4_full_lattice_probe_report.md`
- Summary: `C:\PROGRAMING\czr004\outputs\reports\phase5p5_repair5f4_full_lattice_probe_summary.json`
- Raw probe JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5f4_full_lattice_probe\phase5p5_repair5f4_full_lattice_probe.jsonl`
- Command log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5f4_full_lattice_probe\phase5p5_repair5f4_full_lattice_probe_commands.jsonl`
- LAUR update log JSONL: `C:\PROGRAMING\czr004\outputs\logs\phase5p5_repair5f4_full_lattice_probe\phase5p5_repair5f4_full_lattice_probe_laur_updates.jsonl`
- Long CSV: `C:\PROGRAMING\czr004\outputs\tables\phase5p5_repair5f4_full_lattice_utility_long.csv`
- Wide CSV: `C:\PROGRAMING\czr004\outputs\tables\phase5p5_repair5f4_full_lattice_utility_wide.csv`

## Raw Coverage

- Raw rows before dedupe: `5880`
- Raw rows after dedupe: `5880`
- Expected unique rows: `5880`
- Missing rows: `0`
- Duplicate raw rows dropped: `0`
- Expected candidate rows: `5640`
- Missing candidate rows: `0`
- Schema errors: `0`
- Long CSV rows: `5640`
- Wide CSV rows: `120`

## Raw Log Hashes

- `phase5p5_repair5f4_full_lattice_probe.jsonl`: `E49160ACD07D49CA2167398FA73EB2415B83211E27C9BC27B6EFBA47D690E75C`
- `phase5p5_repair5f4_full_lattice_probe_commands.jsonl`: `32FA3030F29C98FF45BB8AA98F720F52C4F2DDAA557E3AFF3EF68A27D02A9E87`
- `phase5p5_repair5f4_full_lattice_probe_laur_updates.jsonl`: `8B87AA154B0463E7A6AD6F05D499C4FCA93A01306A197FDFACF69B5C3EF7F1CF`

## Gate Check

- `force_additive_parity_exact`: `False`
- `exact_additive_candidate_parity_exact`: `False`
- `laur_disable_parity_exact`: `True`
- `laur_force_additive_direct_parity_exact`: `True`
- `safety_gates_passed`: `False`
- `support_validation_overlap_count`: `0`
- `f2f3_holdout_validation_overlap_count`: `0`
- `support_eval_leakage`: `False`
- `support_final_overlap_count`: `0`
- `full_raw_probe_coverage`: `True`
- `phase5p5_allowed`: `False`
- `phase6_allowed`: `False`

## Paired Stats

| method | rows | better | equal | worse | mean delta ratio vs LTM |
|---|---:|---:|---:|---:|---:|
| `always_additive_defer` | 120 | 1 | 116 | 1 | -0.0006178560394871787 |
| `repair5f_candidate_additive_ltm` | 120 | 1 | 114 | 3 | 5.8133651465517986e-05 |
| `repair5f_candidate_lattice_oracle_static_proxy` | 120 | 69 | 51 | 0 | -0.0176832772359661 |
| `repair5f_bounded_updateparam_selector_random_candidate_diagnostic` | 120 | 30 | 64 | 24 | -0.0012279542748290715 |
| `repair5f_bounded_updateparam_selector_shuffled_utility_diagnostic` | 120 | 22 | 66 | 31 | 0.000991081857249996 |

## Conclusion

Candidate coverage and schema checks are complete for the requested probe scope. This remains selector-training evidence only unless a later leakage-safe selector simulation passes.

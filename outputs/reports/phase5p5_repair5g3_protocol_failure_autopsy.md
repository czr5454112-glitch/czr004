# Phase5.5 Repair5G.3 Protocol Failure Autopsy

G3 remains a protocol failure until the sequential reproducer and parity policy are accepted.

## Findings

- Broad pair-level strict mismatches: `76`
- Strict mismatch classifications: `{'returncode2_no_solution_equivalent': 106, 'time_budget_sensitivity': 8}`
- True semantic parity mismatches: `0`
- Return-code-2/no-solution-equivalent commands: `704`
- Solver crash count: `0`
- Bool-as-int gate type violations: `0`
- Duplicate raw solver rows on resume: `0`

## Interpretation

The committed G3 artifacts show strict exact parity failures, but this autopsy classifies them as non-semantic boundary effects; no true semantic parity mismatch was found in the raw rows.

## Next Step

Run the sequential control-only reproducer and then write a formal parity policy before any G4 clean validation.

## Inputs

- `determinism_summary_json`: `outputs\reports\phase5p5_repair5g3_determinism_repeat_summary.json`
- `broader_summary_json`: `outputs\reports\phase5p5_repair5g3_broader_validation_summary.json`
- `broader_audit_md`: `outputs\reports\phase5p5_repair5g3_broader_validation_audit.md`
- `broader_jsonl`: `outputs\logs\phase5p5_repair5g3_broader_validation\phase5p5_repair5g3_broader_validation.jsonl`
- `broader_command_log`: `outputs\logs\phase5p5_repair5g3_broader_validation\phase5p5_repair5g3_broader_validation_commands.jsonl`
- `determinism_jsonl`: `outputs\logs\phase5p5_repair5g3_determinism_repeat\phase5p5_repair5g3_determinism_repeat.jsonl`
- `determinism_command_log`: `outputs\logs\phase5p5_repair5g3_determinism_repeat\phase5p5_repair5g3_determinism_repeat_commands.jsonl`

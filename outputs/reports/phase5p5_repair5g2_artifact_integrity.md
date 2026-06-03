# Phase5.5 Repair5G.2 Artifact Integrity

Diagnostic-only artifact integrity audit for Repair5G.2.

## Gates

- `required_inputs_exist`: `True`
- `final_tables_and_summary_agree`: `True`
- `raw_logs_available`: `True`
- `raw_logs_if_present_manifested`: `True`
- `final_ids_exact_46_65`: `True`
- `final_ids_used_for_tuning_false`: `True`
- `frozen_selector_spec_exists`: `True`
- `frozen_selector_mtime_before_final_summary_mtime`: `True`
- `script_runtime_commit_recorded`: `True`
- `artifact_commit_recorded`: `True`
- `true_semantic_parity_mismatch_count_zero`: `True`
- `phase5p5_allowed`: `False`
- `phase6_allowed`: `False`
- `integrity_passed`: `True`

## Inputs

- `outputs\reports\phase5p5_repair5g2_decision.md` exists: `True`
- `outputs\reports\phase5p5_repair5g2_protocol_overview.md` exists: `True`
- `outputs\reports\phase5p5_repair5g2_frozen_selector_spec.json` exists: `True`
- `outputs\reports\phase5p5_repair5g2_selector_sweep_summary.json` exists: `True`
- `outputs\reports\phase5p5_repair5g2_fresh_final_eval_summary.json` exists: `True`
- `outputs\tables\phase5p5_repair5g2_fresh_final_eval_summary.csv` exists: `True`
- `outputs\tables\phase5p5_repair5g2_fresh_final_eval_by_map_agent.csv` exists: `True`
- `outputs\tables\phase5p5_repair5g2_fresh_final_eval_paired.csv` exists: `True`

## Raw Logs

- raw_logs_available: `True`
- raw_log_files: `['outputs\\logs\\phase5p5_repair5g2_support_probe\\phase5p5_repair5g2_support_probe.jsonl', 'outputs\\logs\\phase5p5_repair5g2_support_probe\\phase5p5_repair5g2_support_probe_commands.jsonl', 'outputs\\logs\\phase5p5_repair5g2_support_probe\\phase5p5_repair5g2_support_probe_ltm_updates.jsonl', 'outputs\\logs\\phase5p5_repair5g2_fresh_final_eval\\phase5p5_repair5g2_fresh_final_eval.jsonl', 'outputs\\logs\\phase5p5_repair5g2_fresh_final_eval\\phase5p5_repair5g2_fresh_final_eval_commands.jsonl', 'outputs\\logs\\phase5p5_repair5g2_fresh_final_eval\\phase5p5_repair5g2_fresh_final_eval_ltm_updates.jsonl']`
- raw log manifest: `outputs\tables\phase5p5_repair5g2_raw_log_manifest.csv`

## Notes

- All required committed G2 artifacts are internally consistent.

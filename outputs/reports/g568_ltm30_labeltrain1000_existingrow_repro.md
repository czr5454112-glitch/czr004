# G5.68 LTM30 Existing-Row Repro

- git HEAD: `4b786766da4625b315c281c1b89e7ffd6cbfa591`
- git branch: `codex/repair5g567-large-scale-tail-safe`
- git status short: `?? outputs/reports/g567_gate3b_fixed_global_theta_pilot_status.json
?? outputs/reports/g567_gate3b_fixed_global_theta_pilot_summary.json
?? outputs/reports/g567_gate3b_fixed_global_theta_replay_scenario_generation.json
?? outputs/reports/g567_gate3b_old_vs_new_signal_causal_diagnosis.md
?? outputs/reports/g567_gate3b_same_context_oracle_audit.md
?? outputs/tables/g567_gate3b_candidate_family_taxonomy_fixed.csv
?? outputs/tables/g567_gate3b_fixed_global_theta_offline_candidates.csv
?? outputs/tables/g567_gate3b_fixed_global_theta_replay_contexts.csv
?? outputs/tables/g567_gate3b_fixed_global_theta_replay_plan.csv
?? outputs/tables/g567_gate3b_fixed_global_theta_replay_registry.csv
?? outputs/tables/g567_gate3b_fixed_global_theta_replay_results.csv
?? outputs/tables/g567_gate3b_fixed_global_theta_training_metrics.csv
?? outputs/tables/g567_gate3b_labelv53_vs_labelv54_same_rows_audit.csv
?? outputs/tables/g567_gate3b_old_signal_rebased_to_gate3b_units.csv
?? outputs/tables/g567_gate3b_same_context_oracle_by_context.csv
?? outputs/tables/g567_gate3b_target_vs_oracle_vs_actor_by_context.csv
?? scripts/run_g568_ltm30_gate3b_existing_rows.py
?? scripts/run_repair5g565_gate3b_same_context_ab.py
?? scripts/run_repair5g567_gate3b_short_budget_validation.py
?? scripts/server_start_repair5g565_gate3b_ab_reuse.sh`
- external/lacam2/lacam2 changed files: `none`
- primary actor path: `/root/shared-nvme/g567_gate3b_bounded_2d334c79_tmux_r13_pool20000/models/gcst/phase5p5_repair5g567_a5_hierarchical_od_perceiver_actor_seed568.pt`
- primary actor sha256: `5dff8bd987e051c76e8174d59f7a00373b5b52c8c36ebef49b6d8d5eafbf7d9b`
- methods: `['ltm_30s', 'static_flow_30s', 'gate3b_actor_30s']`
- method aliases: LTM `repair5g59_additive_fallback`, static-flow `repair5g59_static_flow_shield`, actor generated continuous theta
- selected contexts: `1000`
- planned rows: `3000`
- internal/hard timeout: `30.0` / `60.0` seconds

Validation checklist:

- plan-only files written before solver execution
- selected rows came from existing Gate-3B manifest
- LABEL_TRAIN backfill used: `False`
- no 3000-agent primary rows
- no solver semantic patching
- no training or fine-tuning
